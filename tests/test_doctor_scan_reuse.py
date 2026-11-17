"""Single-scope Doctor and hygiene share only one diagnostic observation."""

import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from skillsmgr import doctor, loader, scopes


class DoctorScanReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scope_root = self.root / 'skills'
        self.scope_root.mkdir()
        self.scope = scopes.Scope('test', 'Test', self.scope_root, 'agent', True)
        self.store = SimpleNamespace(data_dir=self.root)
        self.env = mock.patch.dict(os.environ, {'HOME': str(self.root), 'CODEX_HOME': str(self.root / 'codex'),
                                               'XDG_STATE_HOME': str(self.root / 'state')})
        self.env.start()
        self.addCleanup(self.env.stop)
        for name, value in [('known_scopes', [self.scope]), ('scope_by_id', self.scope)]:
            patch = mock.patch.object(scopes, name, return_value=value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(scopes, '_peer_link_roots', return_value=())
        patch.start()
        self.addCleanup(patch.stop)

    def skill(self, name, doc='SKILL.md', contents='---\nname: demo\ndescription: Example skill\n---\nBody\n'):
        folder = self.scope_root / name
        folder.mkdir()
        (folder / doc).write_text(contents)
        return folder

    def test_one_scan_husks_excluded_and_fresh_on_next_request(self):
        self.skill('good')
        self.skill('off', 'SKILL.md.disabled')
        self.skill('bad', contents='---\ninvalid\n')
        (self.scope_root / 'husk').mkdir()
        with mock.patch.object(scopes, 'scan_scope', wraps=scopes.scan_scope) as scan, \
             mock.patch.object(loader, 'load_skill', wraps=loader.load_skill) as load:
            result = doctor.doctor_report(self.store, 'test', hygiene=True)
            self.assertEqual(scan.call_count, 1)
            self.assertIsNotNone(scan.call_args.kwargs.get('collector'))
            self.assertEqual(load.call_count, 4)
            self.assertEqual(result['skills_on_disk'], 4)
            self.assertIn('husk', result['malformed_documents'])
            self.assertEqual(result['hygiene']['summary']['observed_records'], 3)
            self.skill('added')
            self.assertEqual(doctor.doctor_report(self.store, 'test', hygiene=True)['skills_on_disk'], 5)
            self.assertEqual(scan.call_count, 2)

    def test_collector_failure_is_carried_to_hygiene(self):
        with mock.patch.object(Path, 'iterdir', side_effect=PermissionError('private')):
            result = doctor.doctor_report(self.store, 'test', hygiene=True)
        self.assertTrue(result['hygiene']['summary']['partial'])
        self.assertTrue(any(event.get('scope') == 'test' for event in result['hygiene']['degraded']))

    def test_matches_standalone_observations_for_disabled_and_conflicts(self):
        folder = self.skill('conflict')
        (folder / 'SKILL.md.disabled').write_text('disabled')
        self.skill('off', 'SKILL.md.disabled')
        self.skill('invalid', contents='---\ninvalid\n')
        (self.scope_root / 'husk').mkdir()
        with mock.patch.object(doctor, 'hygiene_report', wraps=doctor.hygiene_report) as report:
            expected_doctor = doctor.scope_doctor_report('test')
            doctor.hygiene_evidence(self.store, 'test')
            expected_rows = report.call_args.args[0]
            actual = doctor.doctor_report(self.store, 'test', hygiene=True)
            actual_rows = report.call_args.args[0]
        self.assertEqual({key: actual[key] for key in expected_doctor}, expected_doctor)
        fields = ('name', 'disabled', 'malformed', 'document_missing', 'document_conflict',
                  'instance_state', 'instance_states', 'path')
        self.assertEqual([{k: row.get(k) for k in fields} for row in actual_rows],
                         [{k: row.get(k) for k in fields} for row in expected_rows])

    def test_missing_and_non_directory_root(self):
        self.scope_root.rmdir()
        self.assertEqual(doctor.doctor_report(self.store, 'test', hygiene=True)['skills_on_disk'], 0)
        self.scope_root.write_text('not a directory')
        result = doctor.doctor_report(self.store, 'test', hygiene=True)
        self.assertFalse(result['ok'])
        self.assertTrue(result['hygiene']['summary']['partial'])

    def test_undecodable_and_managed_peer_link_match_standalone(self):
        bad = self.skill('undecodable')
        (bad / 'SKILL.md').write_bytes(b'\xff')
        peer = self.root / 'peer'
        peer.mkdir()
        target = peer / 'linked'
        target.mkdir()
        (target / 'SKILL.md').write_text('---\nname: linked\ndescription: Link\n---\nBody\n')
        try:
            (self.scope_root / 'linked').symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('directory symlink unavailable')
        with mock.patch.object(scopes, '_peer_link_roots', return_value=(peer,)), \
             mock.patch.object(doctor, 'hygiene_report', wraps=doctor.hygiene_report) as report:
            expected = doctor.scope_doctor_report('test')
            doctor.hygiene_evidence(self.store, 'test')
            old_rows = report.call_args.args[0]
            actual = doctor.doctor_report(self.store, 'test', hygiene=True)
            rows = report.call_args.args[0]
        self.assertEqual({key: actual[key] for key in expected}, expected)
        fields = ('name', 'decode_error', 'link_followed', 'linked_to', 'read_only')
        self.assertEqual([{k: row.get(k) for k in fields} for row in rows],
                         [{k: row.get(k) for k in fields} for row in old_rows])

    def test_husk_does_not_mark_same_named_peer_as_duplicate_in_hygiene(self):
        (self.scope_root / 'dupe').mkdir()
        peer = self.root / 'peer'
        target = peer / 'dupe'
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('---\nname: dupe\ndescription: Link\n---\nBody\n')
        try:
            (self.scope_root / 'alias').symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('directory symlink unavailable')
        with mock.patch.object(scopes, '_peer_link_roots', return_value=(peer,)), \
             mock.patch.object(doctor, 'hygiene_report', wraps=doctor.hygiene_report) as report:
            doctor.hygiene_evidence(self.store, 'test')
            expected = report.call_args.args[0][0]['instance_states'][:]
            doctor.doctor_report(self.store, 'test', hygiene=True)
            observed = report.call_args.args[0][0]['instance_states']
        self.assertEqual(observed, expected)
        self.assertNotIn('duplicated', observed)

    def _check_recursive_document_directory(self, linked):
        self.scope = scopes.Scope('test', 'Test', self.scope_root, 'agent', True, recursive=True)
        example = self.scope_root / 'example'
        example.mkdir()
        document = example / 'SKILL.md'
        if linked:
            target = self.root / 'target'
            target.mkdir()
            try:
                document.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlink unavailable')
        else:
            document.mkdir()
        original_scan = scopes.scan_scope

        def instrumented_scan(*args, **kwargs):
            rows = original_scan(*args, **kwargs)
            if kwargs.get('include_husks') and kwargs.get('collector') is not None:
                kwargs['collector'].append({'section': 'scope-scan', 'reason': 'test scan problem'})
            return rows

        with mock.patch.object(scopes, 'known_scopes', return_value=[self.scope]), \
             mock.patch.object(scopes, 'scope_by_id', return_value=self.scope), \
             mock.patch.object(scopes, 'scan_scope', side_effect=instrumented_scan), \
             mock.patch.object(doctor, 'hygiene_report', wraps=doctor.hygiene_report) as report:
            expected = doctor.scope_doctor_report('test')
            separate = doctor.hygiene_evidence(self.store, 'test')
            old_rows = report.call_args.args[0]
            combined = doctor.doctor_report(self.store, 'test', hygiene=True)
            rows = report.call_args.args[0]
        self.assertEqual(expected['malformed_documents'], ['example'])
        self.assertEqual({key: combined[key] for key in expected}, expected)
        self.assertEqual(old_rows, rows)
        self.assertEqual(separate['summary']['observed_records'], 0)
        self.assertEqual(combined['hygiene']['summary']['observed_records'], 0)
        self.assertTrue(any(event['reason'] == 'test scan problem' for event in combined['hygiene']['degraded']))
        self.assertNotIn(loader.DOCTOR_RESCAN_EVENT, str(combined))
        self.assertNotIn(loader.DOCTOR_RESCAN_EVENT, str(separate))

    def test_recursive_document_directory_preserves_separate_views(self):
        self._check_recursive_document_directory(False)

    def test_recursive_linked_document_directory_preserves_separate_views(self):
        self._check_recursive_document_directory(True)


if __name__ == '__main__':
    unittest.main()
