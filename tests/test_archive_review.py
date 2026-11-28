"""Checked archive previews bind the payload and the observed destinations."""
import tempfile
import json
import threading
import urllib.request
import urllib.error
import unittest
from pathlib import Path

from skillsmgr.store import Store, StoreError
from skillsmgr.webapp import WebAppServer


class ArchiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = Store(data_dir=self.root / 'source')
        self.source.create('demo', 'Archive test', body='original')
        self.archive = self.source.export(self.root / 'skills.tar.gz', full=True)
        self.target = Store(data_dir=self.root / 'target')
        self.target.init_db()

    def test_preview_and_checked_apply(self):
        before = list(self.target.skills_dir.iterdir())
        plan = self.target.import_(self.archive, preview=True)
        self.assertEqual(plan['entries'], [{'name': 'demo', 'place': 'library', 'action': 'add'}])
        self.assertEqual(before, list(self.target.skills_dir.iterdir()))
        result = self.target.import_(self.archive, plan_id=plan['plan_id'])
        self.assertEqual(result['imported'], ['demo'])
        collision = self.target.import_(self.archive, preview=True)
        self.assertEqual(collision['entries'][0]['action'], 'skip')
        forced = self.target.import_(self.archive, force=True, preview=True)
        self.assertEqual(forced['entries'][0]['action'], 'replace')

    def test_changed_target_or_options_refuse_before_writing(self):
        plan = self.target.import_(self.archive, preview=True)
        self.target.create('demo', 'Existing', body='keep me')
        with self.assertRaises(StoreError):
            self.target.import_(self.archive, plan_id=plan['plan_id'])
        self.assertIn('keep me', self.target.get('demo')['body'])
        plan = self.target.import_(self.archive, force=True, preview=True)
        with self.assertRaises(StoreError):
            self.target.import_(self.archive, force=False, plan_id=plan['plan_id'])
        self.assertIn('keep me', self.target.get('demo')['body'])

    def test_full_mode_bound_to_plan(self):
        plan = self.target.import_(self.archive, full=True, preview=True)
        with self.assertRaises(StoreError):
            self.target.import_(self.archive, full=False, plan_id=plan['plan_id'])
        result = self.target.import_(self.archive, full=True, plan_id=plan['plan_id'])
        self.assertEqual(result['imported'], ['demo'])

    def test_rest_preview_and_checked_apply(self):
        server = WebAppServer(self.target, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            data = self.archive.read_bytes()
            def put(query):
                request = urllib.request.Request(server.url + "api/import?filename=skills.TAR.GZ&" + query,
                                                 data=data, method="PUT")
                with urllib.request.urlopen(request) as response:
                    return json.load(response)
            plan = put("preview=1")
            self.assertEqual(plan["entries"][0]["action"], "add")
            self.assertFalse((self.target.skills_dir / "demo").exists())
            self.assertEqual(put("plan_id=" + plan["plan_id"])["imported"], ["demo"])
            with self.assertRaises(urllib.error.HTTPError):
                put("plan_id=" + plan["plan_id"])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.httpd.server_close()

    def test_preview_does_not_create_fresh_data_root(self):
        fresh_root = self.root / "not-created"
        fresh = Store(data_dir=fresh_root)
        fresh.import_(self.archive, preview=True)
        self.assertFalse(fresh_root.exists())

    def test_checked_add_refuses_an_entry_appearing_after_review(self):
        from unittest import mock
        from skillsmgr import archive
        plan = self.target.import_(self.archive, force=True, preview=True)
        original = archive._stage_replacement
        def appear(source, dest, **kwargs):
            staged = original(source, dest, **kwargs)
            dest.mkdir()
            (dest / 'keep').write_text('keep')
            return staged
        with mock.patch.object(archive, '_stage_replacement', side_effect=appear):
            result = self.target.import_(self.archive, force=True, plan_id=plan['plan_id'])
        self.assertEqual(result['imported'], [])
        self.assertEqual((self.target.skills_dir / 'demo' / 'keep').read_text(), 'keep')

    def test_checked_skip_stays_skipped_if_destination_disappears(self):
        from unittest import mock
        import shutil
        self.target.create('demo', 'Existing')
        plan = self.target.import_(self.archive, preview=True)
        init = self.target._init_db
        def disappear():
            init()
            shutil.rmtree(self.target.skills_dir / 'demo')
        with mock.patch.object(self.target, '_init_db', side_effect=disappear):
            result = self.target.import_(self.archive, plan_id=plan['plan_id'])
        self.assertEqual(result['imported'], [])
        self.assertFalse((self.target.skills_dir / 'demo').exists())

    def test_restore_refuses_live_and_dangling_links(self):
        import os
        self.target.create('demo', 'Existing')
        trash = self.target.remove('demo')['trash_path']
        for target in (self.root / 'outside', self.root / 'missing'):
            if target.name == 'outside':
                target.mkdir()
                (target / 'keep').write_text('keep')
            link = self.target.skills_dir / 'demo'
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlink unavailable')
            with self.assertRaises(StoreError):
                self.target.restore('demo', trash_path=trash)
            self.assertTrue(os.path.lexists(link))
            self.assertTrue(Path(trash).exists())
            link.unlink()
        self.assertEqual((self.root / 'outside' / 'keep').read_text(), 'keep')

    def test_full_checked_add_does_not_replace_appearing_trash(self):
        from unittest import mock
        from skillsmgr import archive
        self.source.create('discard', 'Trash fixture')
        self.source.remove('discard')
        full = self.source.export(self.root / 'with-trash.tar.gz', full=True)
        plan = self.target.import_(full, force=True, full=True, preview=True)
        original = archive._stage_replacement
        def appear(source, dest, **kwargs):
            staged = original(source, dest, **kwargs)
            if dest.parent == self.target.trash_dir:
                dest.mkdir()
                (dest / 'keep').write_text('keep')
            return staged
        with mock.patch.object(archive, '_stage_replacement', side_effect=appear):
            with self.assertRaises(StoreError):
                self.target.import_(full, force=True, full=True, plan_id=plan['plan_id'])
        self.assertEqual(next(self.target.trash_dir.glob('*/keep')).read_text(), 'keep')

    def test_checked_add_publish_is_exclusive_after_last_check(self):
        from unittest import mock
        from skillsmgr import archive
        plan = self.target.import_(self.archive, force=True, preview=True)
        original = archive._publish_new
        def appear(source, dest):
            dest.mkdir()
            (dest / 'keep').write_text('keep')
            return original(source, dest)
        with mock.patch.object(archive, '_publish_new', side_effect=appear):
            result = self.target.import_(self.archive, force=True, plan_id=plan['plan_id'])
        self.assertEqual(result['imported'], [])
        self.assertEqual((self.target.skills_dir / 'demo' / 'keep').read_text(), 'keep')

    def test_file_add_is_withdrawn_when_stage_unlink_fails(self):
        from unittest import mock
        plan = self.target.import_(self.archive, full=True, preview=True)
        unlink = Path.unlink
        def fail_stage(path, *args, **kwargs):
            if path.name == 'new' and path.is_file():
                raise OSError('fixture stage cleanup failure')
            return unlink(path, *args, **kwargs)
        with mock.patch.object(Path, 'unlink', fail_stage):
            with self.assertRaises(StoreError):
                self.target.import_(self.archive, full=True, plan_id=plan['plan_id'])
        self.assertFalse((self.target.data_dir / 'catalog' / 'metadata.json').exists())
        self.assertFalse((self.target.skills_dir / 'demo').exists())

    def test_review_uses_same_bytes_for_extraction_and_hash(self):
        from unittest import mock
        from skillsmgr import store
        extract = store._extract_import_archive
        other = self.source.export(self.root / 'other.tar.gz')
        def change_original(snapshot, destination):
            self.archive.write_bytes(other.read_bytes())
            return extract(snapshot, destination)
        original = self.archive.read_bytes()
        with mock.patch.object(store, '_extract_import_archive', side_effect=change_original):
            plan = self.target.import_(self.archive, full=True, preview=True)
        with self.assertRaises(StoreError):
            self.target.import_(self.archive, full=True, plan_id=plan['plan_id'])
        self.archive.write_bytes(original)
        self.assertEqual(self.target.import_(self.archive, full=True, plan_id=plan['plan_id'])['imported'], ['demo'])

    def test_restore_does_not_replace_appearing_empty_folder(self):
        from unittest import mock
        from skillsmgr import atomic_io
        self.target.create('demo', 'Existing')
        trashed = self.target.remove('demo')['trash_path']
        rename = atomic_io.rename_new_directory
        def appear(source, destination):
            destination.mkdir()
            return rename(source, destination)
        with mock.patch.object(atomic_io, 'rename_new_directory', side_effect=appear):
            with self.assertRaises(StoreError):
                self.target.restore('demo', trash_path=trashed)
        self.assertTrue((self.target.skills_dir / 'demo').is_dir())
        self.assertTrue(Path(trashed).is_dir())
