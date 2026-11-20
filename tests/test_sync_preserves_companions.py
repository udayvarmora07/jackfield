"""A forced sync must not silently destroy files only the replaced copy had.

The text snapshot covers the skill document only. Companion files that
existed in the replaced copy and not (or differently) in the source go to
that scope's trash, where Recovery can restore them.
"""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skillsmgr import context
from skillsmgr import scopes


class SyncPreservesCompanionsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        patcher = mock.patch.dict(os.environ, {"HOME": tmp.name, "SKILLS_MANAGER_DATA": str(self.home / "data")})
        patcher.start()
        self.addCleanup(patcher.stop)
        store = scopes.Store()
        store.init_db()
        token = context.ACTIVE_STORE.set(store)
        self.addCleanup(context.ACTIVE_STORE.reset, token)
        self.source = Path(scopes.create_skill("agents", "demo", "source body")["path"])
        self.target = Path(scopes.create_skill("codex", "demo", "target body")["path"])

    def _trash_rows(self):
        return [row for row in scopes.scope_trash_list("codex") if row["name"] == "demo"]

    def test_target_only_file_goes_to_recovery(self):
        (self.target / "scripts").mkdir()
        (self.target / "scripts" / "run.sh").write_text("echo only here\n")
        result = scopes.sync_skill("demo", "agents", ["codex"], force=True)
        self.assertEqual(result["synced"], ["codex"])
        retired = Path(result["replaced_to_trash"]["codex"])
        self.assertEqual((retired / "scripts" / "run.sh").read_text(), "echo only here\n")
        self.assertIn("target body", (retired / "SKILL.md").read_text())
        self.assertFalse((self.target / "scripts").exists())
        self.assertEqual([row["trash_path"] for row in self._trash_rows()], [str(retired)])
        self.assertEqual(list(self.target.parent.glob(".demo.skillsmgr-*")), [])

    def test_changed_companion_goes_to_recovery(self):
        (self.source / "notes.md").write_text("source notes\n")
        (self.target / "notes.md").write_text("target notes\n")
        result = scopes.sync_skill("demo", "agents", ["codex"], force=True)
        retired = Path(result["replaced_to_trash"]["codex"])
        self.assertEqual((retired / "notes.md").read_text(), "target notes\n")
        self.assertEqual((self.target / "notes.md").read_text(), "source notes\n")

    def test_document_only_difference_leaves_no_trash_entry(self):
        (self.source / "notes.md").write_text("same\n")
        (self.target / "notes.md").write_text("same\n")
        result = scopes.sync_skill("demo", "agents", ["codex"], force=True)
        self.assertNotIn("replaced_to_trash", result)
        self.assertEqual(self._trash_rows(), [])
        self.assertEqual(list(self.target.parent.glob(".demo.skillsmgr-*")), [])

    def test_trash_failure_keeps_the_replaced_copy_for_review(self):
        (self.target / "only.txt").write_text("keep\n")
        with mock.patch.object(scopes, "move_trash_tree", side_effect=OSError("fixture refusal")):
            result = scopes.sync_skill("demo", "agents", ["codex"], force=True)
        self.assertNotIn("replaced_to_trash", result)
        kept = self.target.parent / ".demo.skillsmgr-backup"
        self.assertEqual(result["retained_backup"], {"codex": str(kept)})
        self.assertEqual((kept / "only.txt").read_text(), "keep\n")

    def test_source_edit_after_copy_does_not_make_old_files_discardable(self):
        (self.source / "notes.md").write_text("installed version\n")
        (self.target / "notes.md").write_text("target original\n")
        copy = scopes._copy_skill_tree

        def copy_then_edit(source, stage):
            copy(source, stage)
            (source / "notes.md").write_text("target original\n")

        with mock.patch.object(scopes, "_copy_skill_tree", side_effect=copy_then_edit):
            result = scopes.sync_skill("demo", "agents", ["codex"], force=True)
        retired = Path(result["replaced_to_trash"]["codex"])
        self.assertEqual((retired / "notes.md").read_text(), "target original\n")
        self.assertEqual((self.target / "notes.md").read_text(), "installed version\n")

    def test_empty_target_only_directory_goes_to_recovery(self):
        (self.target / "empty").mkdir()
        result = scopes.sync_skill("demo", "agents", ["codex"], force=True)
        retired = Path(result["replaced_to_trash"]["codex"])
        self.assertTrue((retired / "empty").is_dir())

    def test_global_target_uses_the_library_trash(self):
        store = context.ACTIVE_STORE.get()
        store.create("demo", "Library copy", body="library body")
        library = store.skills_dir / "demo"
        extra = library / "manual.skillsmgr-tmp"
        extra.write_text("library only\n")
        os.utime(extra, (1_700_000_000, 1_700_000_000))
        result = scopes.sync_skill("demo", "agents", ["global"], force=True)
        retired = Path(result["replaced_to_trash"]["global"])
        self.assertEqual((retired / extra.name).read_text(), "library only\n")
        listed = [row["trash_path"] for row in store.trash_list() if row["name"] == "demo"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(Path(listed[0]).name, retired.name)
        self.assertEqual(store.get("demo")["description"], "source body")

    def test_resync_keeps_a_global_backup_when_trash_move_fails(self):
        store = context.ACTIVE_STORE.get()
        store.create("demo", "Library copy", body="library body")
        library = store.skills_dir / "demo"
        marker = library / "manual.skillsmgr-tmp"
        marker.write_text("library only\n")
        for path in (marker, library):
            os.utime(path, (1_700_000_000, 1_700_000_000))
        with mock.patch.object(scopes, "move_trash_tree", side_effect=OSError("fixture refusal")):
            result = scopes.sync_skill("demo", "agents", ["global"], force=True)
        kept = Path(result["retained_backup"]["global"])
        self.assertEqual((kept / marker.name).read_text(), "library only\n")
        self.assertEqual(store.get("demo")["description"], "source body")

    def test_nested_recovery_restores_exact_original_path(self):
        nested = self.source.parent / "group" / "demo"
        nested.parent.mkdir()
        self.source.rename(nested)
        (nested / "only.txt").write_text("unique\n")
        result = scopes.sync_skill("demo", "codex", ["agents"], force=True)
        saved = result["replaced_to_trash"]["agents"]
        removed = scopes.remove_skill("agents", "demo")
        self.assertFalse(nested.exists())
        restored = scopes.restore_trashed("agents", "demo", saved)
        self.assertEqual(Path(restored["path"]), nested)
        self.assertEqual((nested / "only.txt").read_text(), "unique\n")
        self.assertTrue(Path(removed["trash_path"]).is_dir())
        self.assertFalse(Path(saved + ".origin.json").exists())

    def test_nested_remove_restore_and_legacy_fallback(self):
        nested = self.source.parent / "group" / "demo"
        nested.parent.mkdir()
        self.source.rename(nested)
        removed = scopes.remove_skill("agents", "demo")
        restored = scopes.restore_trashed("agents", "demo", removed["trash_path"])
        self.assertEqual(Path(restored["path"]), nested)
        removed = scopes.remove_skill("agents", "demo")
        Path(removed["trash_path"] + ".origin.json").unlink()  # A legacy entry.
        restored = scopes.restore_trashed("agents", "demo", removed["trash_path"])
        self.assertEqual(Path(restored["path"]), self.source)

    def test_corrupt_or_unsafe_explicit_origin_refuses_restore(self):
        removed = scopes.remove_skill("agents", "demo")
        sidecar = Path(removed["trash_path"] + ".origin.json")
        original = json.loads(sidecar.read_text())
        for relative in ("../demo", "/demo", "other", "group/../demo"):
            record = dict(original, relative=relative)
            sidecar.write_text(json.dumps(record))
            with self.subTest(relative=relative), self.assertRaises(scopes.StoreError):
                scopes.restore_trashed("agents", "demo", removed["trash_path"])
            self.assertTrue(Path(removed["trash_path"]).is_dir())
        sidecar.write_text('{"version":1,"version":1}')
        with self.assertRaises(scopes.StoreError):
            scopes.restore_trashed("agents", "demo", removed["trash_path"])

    def test_origin_with_symlink_parent_refuses_restore(self):
        nested = self.source.parent / "group" / "demo"
        nested.parent.mkdir()
        self.source.rename(nested)
        removed = scopes.remove_skill("agents", "demo")
        nested.parent.rename(self.source.parent / "real-group")
        try:
            nested.parent.symlink_to("real-group", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(scopes.StoreError):
            scopes.restore_trashed("agents", "demo", removed["trash_path"])
        self.assertTrue(Path(removed["trash_path"]).is_dir())


if __name__ == "__main__":
    unittest.main()
