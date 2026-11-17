import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from skillsmgr import doctor, loader, scopes
from skillsmgr.errors import SkillNotFound


class ScanDegradationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'skills'
        self.root.mkdir()

    def test_missing_and_inaccessible_roots(self):
        events = []
        self.assertEqual(loader.scan_dir(self.root / 'missing', collector=events), [])
        self.assertEqual(events, [])
        with mock.patch.object(Path, 'stat', side_effect=PermissionError('secret path')):
            self.assertEqual(loader.scan_dir(self.root, collector=events), [])
        self.assertTrue(events)
        self.assertNotIn('secret path', str(events))

    def test_late_iteration_failure_is_reported(self):
        def broken(_):
            yield self.root / 'a'
            raise PermissionError('secret')
        events = []
        with mock.patch.object(Path, 'iterdir', broken):
            loader.scan_dir(self.root, collector=events)
        self.assertTrue(events)
        self.assertNotIn('secret', str(events))

    def test_recursive_iteration_failure_is_reported(self):
        events = []
        def broken_walk(root, onerror, **kwargs):
            onerror(PermissionError('secret'))
            return iter(())
        with mock.patch.object(loader.os, 'walk', broken_walk):
            loader.scan_dir(self.root, recursive=True, collector=events)
        self.assertTrue(events)

    def test_candidate_failures_are_bounded(self):
        for n in range(150):
            child = self.root / str(n)
            child.mkdir()
            (child / 'SKILL.md').write_text('---\nname: candidate\ndescription: test\n---\n')
        for exc in (SkillNotFound('secret'), OSError('secret')):
            events = []
            with mock.patch.object(loader, 'load_skill', side_effect=exc):
                loader.scan_dir(self.root, collector=events)
            self.assertGreater(len(events), 0)
            self.assertLessEqual(len(events), 101)
            self.assertNotIn('secret', str(events))

    def test_ordinary_folders_are_not_degraded(self):
        folder = self.root / 'extras'
        folder.mkdir()
        (folder / 'README.md').write_text('Extra information')
        (folder / 'category').mkdir()
        events = []
        self.assertEqual(loader.scan_dir(self.root, collector=events), [])
        self.assertEqual(events, [])

    def test_regular_file_root_is_degraded(self):
        root = self.root / 'not-a-directory'
        root.write_text('file')
        events = []
        self.assertEqual(loader.scan_dir(root, collector=events), [])
        self.assertTrue(events)

    def test_symlink_to_regular_file_is_skipped(self):
        target = Path(self.tmp.name) / 'readme'
        target.write_text('not a skill')
        (self.root / 'readme-link').symlink_to(target)
        events = []
        self.assertEqual(loader.scan_dir(self.root, collector=events), [])
        self.assertEqual(events, [])

    def test_symlink_to_peer_skill_remains_readable(self):
        peer = Path(self.tmp.name) / 'peer'
        child = peer / 'skill'
        child.mkdir(parents=True)
        (child / 'SKILL.md').write_text('---\nname: skill\ndescription: Test\n---\n')
        (self.root / 'skill').symlink_to(child, target_is_directory=True)
        events = []
        records = loader.scan_dir(self.root, collector=events, link_roots=(peer,))
        self.assertEqual([row['name'] for row in records], ['skill'])
        self.assertFalse(records[0].get('link_escape'))
        self.assertEqual(events, [])

    def test_broken_symlink_is_skipped(self):
        (self.root / 'broken').symlink_to(self.root / 'missing')
        events = []
        self.assertEqual(loader.scan_dir(self.root, collector=events), [])
        self.assertEqual(events, [])

    def test_candidate_lstat_failure_is_reported(self):
        child = self.root / 'inaccessible'
        child.mkdir()
        original = Path.lstat
        def inaccessible(path):
            if path == child:
                raise PermissionError('private')
            return original(path)
        events = []
        with mock.patch.object(Path, 'lstat', inaccessible):
            self.assertEqual(loader.scan_dir(self.root, collector=events), [])
        self.assertTrue(events)
        self.assertNotIn('private', str(events))

    def test_document_disappearing_after_discovery_is_degraded(self):
        folder = self.root / 'disappearing'
        folder.mkdir()
        document = folder / 'SKILL.md'
        document.write_text('---\nname: disappearing\ndescription: test\n---\n')
        original = loader.load_skill
        def disappear(path, **kwargs):
            document.unlink()
            return original(path, **kwargs)
        events = []
        with mock.patch.object(loader, 'load_skill', side_effect=disappear):
            self.assertEqual(loader.scan_dir(self.root, collector=events), [])
        self.assertTrue(events)

    def test_scope_collector_and_empty_and_single_skill(self):
        scope = scopes.Scope('test', 'Test', self.root, 'agent', True)
        events = []
        with mock.patch.object(scopes, 'scope_by_id', return_value=scope), \
             mock.patch.object(scopes, '_peer_link_roots', return_value=()):
            self.assertEqual(scopes.scan_scope('test', collector=events), [])
            self.assertEqual(events, [])
            child = self.root / 'one'
            child.mkdir()
            (child / 'SKILL.md').write_text('---\nname: one\ndescription: One\n---\nBody\n')
            self.assertEqual(len(scopes.scan_scope('test', collector=events)), 1)
            self.assertEqual(events, [])
            with mock.patch.object(Path, 'iterdir', side_effect=PermissionError('private')):
                self.assertEqual(scopes.scan_scope('test', collector=events), [])
            self.assertTrue(events)

    def test_scope_failures_keep_attribution(self):
        other = self.root / 'other'
        other.mkdir()
        descriptors = [SimpleNamespace(id='global', base=self.root),
                       SimpleNamespace(id='other', base=other)]
        store = SimpleNamespace(skills_dir=self.root, data_dir=Path(self.tmp.name))
        def fail_scope(_id, *, collector):
            collector.append({'section': 'scope-scan', 'reason': 'scope directory enumeration failed'})
            return []
        with mock.patch.object(scopes, 'known_scopes', return_value=descriptors), \
             mock.patch.object(scopes, 'scan_scope', side_effect=fail_scope):
            _records, degraded = doctor._hygiene_records(store, 'all')
        self.assertEqual([event['scope'] for event in degraded], ['other'])

    def test_hygiene_scan_sets_baseline_partial_without_writes(self):
        store = SimpleNamespace(skills_dir=self.root, data_dir=Path(self.tmp.name))
        desc = SimpleNamespace(id='global', base=self.root)
        before = list(self.root.iterdir())
        with mock.patch.object(scopes, 'known_scopes', return_value=[desc]), \
             mock.patch.object(Path, 'iterdir', side_effect=PermissionError('secret')):
            result = doctor.hygiene_evidence(store, 'global')
        self.assertTrue(result['summary']['partial'])
        self.assertEqual(result['document_fingerprints']['status'], 'partial')
        self.assertEqual(list(self.root.iterdir()), before)
