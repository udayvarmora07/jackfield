"""Project lock verification is read-only and fails closed on incomplete evidence."""

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skillsmgr import lockfiles, project_lock_commands


class VerifyProjectLockTests(unittest.TestCase):
    def test_matching_and_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello\n")
            lock = root / "skills-lock.json"
            lock.write_text(json.dumps({"version": 2, "skills": {"demo": {
                "source": "o/r", "computedHash": lockfiles.portable_folder_hash(skill)}}}))
            before = lock.read_bytes()
            self.assertTrue(project_lock_commands.verify_project_lock(root)["verified"])
            (skill / "SKILL.md").write_text("changed\n")
            self.assertFalse(project_lock_commands.verify_project_lock(root)["verified"])
            self.assertEqual(before, lock.read_bytes())

    def test_missing_invalid_and_incomplete_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(project_lock_commands.verify_project_lock(root)["verified"])
            path = root / "skills-lock.json"
            path.write_text('{"version": 99, "skills": {}}')
            self.assertFalse(project_lock_commands.verify_project_lock(root)["verified"])
            path.write_text('{"version": 2, "skills": {"missing": {}}, "skills": {}}')
            self.assertFalse(project_lock_commands.verify_project_lock(root)["verified"])
            path.write_text(json.dumps({"version": 2, "skills": {"a": {}, "b": {}}}))
            with mock.patch.object(lockfiles, "MAX_LOCK_ENTRIES", 1):
                self.assertFalse(project_lock_commands.verify_project_lock(root)["verified"])

    def test_empty_lock_verifies_and_missing_document_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / "skills-lock.json"
            lock.write_text('{"version": 2, "skills": {}}')
            self.assertTrue(project_lock_commands.verify_project_lock(root)["verified"])
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            lock.write_text(json.dumps({"version": 2, "skills": {"demo": {
                "computedHash": lockfiles.portable_folder_hash(skill)}}}))
            result = project_lock_commands.verify_project_lock(root)
            self.assertFalse(result["verified"])
            self.assertEqual(result["entries"][0]["hash_status"], "missing")

    def test_v1_verifies_using_legacy_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_bytes(b"hello\n")
            (root / "skills-lock.json").write_text(json.dumps({"version": 1, "skills": {
                "demo": {"computedHash": lockfiles.computed_folder_hash(skill)}}}))
            self.assertTrue(project_lock_commands.verify_project_lock(root)["verified"])


class WriteProjectLockTests(unittest.TestCase):
    def test_read_only_lock_can_be_previewed_but_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello")
            lock = root / "skills-lock.json"
            before = b'{"version":2,"skills":{"demo":{"source":"o/r"}}}'
            lock.write_bytes(before)
            lock.chmod(0o444)
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            try:
                plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
                self.assertTrue(plan["changed"])
                with self.assertRaisesRegex(lockfiles.LockfileError, "not writable"):
                    project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
                self.assertEqual(lock.read_bytes(), before)
                self.assertFalse((data / "project-lock-backups").exists())
                self.assertFalse((root / "skills-lock.json.lock").exists())
            finally:
                lock.chmod(0o600)

    def test_undo_respects_lost_write_access_without_a_mode_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello")
            lock = root / "skills-lock.json"
            before = b'{"version":2,"skills":{"demo":{"source":"o/r"}}}'
            lock.write_bytes(before)
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            plan_id = plan["plan_hash"]
            project_lock_commands.apply_project_lock_write(root, ["demo"], plan_id, data_dir=data)
            after = lock.read_bytes()
            receipt = data / "project-lock-backups" / (plan_id + ".json")
            original_receipt = receipt.read_bytes()
            access = os.access

            def deny_lock_write(path, mode):
                return False if path == lock and mode & os.W_OK else access(path, mode)

            with mock.patch.object(project_lock_commands.os, "access", side_effect=deny_lock_write):
                with self.assertRaisesRegex(lockfiles.LockfileError, "not writable"):
                    project_lock_commands.undo_project_lock_write(root, plan_id, data_dir=data)
            self.assertEqual(lock.read_bytes(), after)
            self.assertEqual(receipt.read_bytes(), original_receipt)
            project_lock_commands.undo_project_lock_write(root, plan_id, data_dir=data)
            self.assertEqual(lock.read_bytes(), before)

    def test_unpublished_receipt_refuses_a_later_matching_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello")
            lock = root / "skills-lock.json"
            lock.write_text('{"version":2,"skills":{"demo":{"source":"o/r"}}}')
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            after = project_lock_commands._write_plan(root, ["demo"], None)[2]
            with mock.patch.object(project_lock_commands.os, "replace", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
            receipt = data / "project-lock-backups" / (plan["plan_hash"] + ".json")
            self.assertTrue(receipt.is_file())
            lock.write_bytes(after)
            with self.assertRaisesRegex(lockfiles.LockfileError, "different file"):
                project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)
            self.assertEqual(lock.read_bytes(), after)

    def test_completed_rename_can_be_undone_after_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello")
            lock = root / "skills-lock.json"
            before = b'{"version":2,"skills":{"demo":{"source":"o/r"}}}'
            lock.write_bytes(before)
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            replace = os.replace

            def interrupt_after_replace(source, destination):
                replace(source, destination)
                if destination == lock:
                    raise KeyboardInterrupt

            with mock.patch.object(project_lock_commands.os, "replace", side_effect=interrupt_after_replace):
                with self.assertRaises(KeyboardInterrupt):
                    project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
            self.assertNotEqual(lock.read_bytes(), before)
            self.assertTrue(project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)["restored"])
            self.assertEqual(lock.read_bytes(), before)
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_permission_changes_invalidate_preview_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello")
            lock = root / "skills-lock.json"
            lock.write_text('{"version":2,"skills":{"demo":{"source":"o/r"}}}')
            lock.chmod(0o600)
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            lock.chmod(0o640)
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
            lock.chmod(0o600)
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)

    def test_preview_apply_undo_preserves_unselected_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello\n")
            lock = root / "skills-lock.json"
            before = b'{"version":2,"custom":7,"skills":{"demo":{"source":"a/b","computedHash":"old","commit":"old","custom":1},"other":{"source":"c/d"}}}\n'
            lock.write_bytes(before)
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            self.assertEqual(lock.read_bytes(), before)
            project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
            updated = json.loads(lock.read_bytes())
            self.assertEqual(updated["custom"], 7)
            self.assertEqual(updated["skills"]["other"], {"source": "c/d"})
            self.assertEqual(updated["skills"]["demo"]["custom"], 1)
            self.assertNotIn("commit", updated["skills"]["demo"])
            self.assertTrue(project_lock_commands.verify_project_lock(root)["entries"][0]["hash_status"] == "match")
            project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)
            self.assertEqual(lock.read_bytes(), before)

    def test_preview_hides_unrelated_data_and_keeps_identical_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello\n")
            lock = root / "skills-lock.json"
            document = {"version": 2, "private": "unrelated-fixture",
                        "skills": {"demo": {"source": "https://user:token-fixture@example.test/repo",
                                            "computedHash": lockfiles.portable_folder_hash(skill)}}}
            lock.write_text(json.dumps(document, separators=(",", ":")))
            self.assertFalse(project_lock_commands.preview_project_lock_write(root, ["demo"])["changed"])
            (skill / "SKILL.md").write_text("revised\n")
            preview = project_lock_commands.preview_project_lock_write(root, ["demo"])
            self.assertTrue(preview["changed"])
            self.assertIn("computedHash", preview["diff"])
            self.assertNotIn("token-fixture", preview["diff"])
            self.assertNotIn("unrelated-fixture", preview["diff"])

    def test_new_local_source_and_stale_or_busy_previews(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            source = root / "source"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("hello\n")
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("hello\n")
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            sources = {"demo": "source"}
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"], local_sources=sources)
            (root / "skills-lock.json.lock").write_text("")
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data, local_sources=sources)
            (root / "skills-lock.json.lock").unlink()
            project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data, local_sources=sources)
            self.assertEqual(json.loads((root / "skills-lock.json").read_text())["skills"]["demo"]["source"], "./source")
            (root / "skills-lock.json").write_text("changed")
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)

    def test_new_lock_undo_and_rejects_unverified_or_v1_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("x\n")
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.preview_project_lock_write(root, ["demo"])
            args = {"demo": ".agents/skills/demo"}
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"], local_sources=args)
            project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data, local_sources=args)
            lock = root / "skills-lock.json"
            receipt_path = data / "project-lock-backups" / (plan["plan_hash"] + ".json")
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["mode"], stat.S_IMODE(lock.stat().st_mode))
            if os.name == "nt":
                # Simulate an already-applied receipt from before the fix.
                receipt["mode"] = 0o644
                receipt_path.write_text(json.dumps(receipt))
            project_lock_commands.undo_project_lock_write(root, plan["plan_hash"], data_dir=data)
            self.assertFalse(lock.exists())
            lock.write_text('{"version":1,"skills":{"demo":{"source":"a/b"}}}')
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.preview_project_lock_write(root, ["demo"])

    def test_apply_refuses_changed_skill_since_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("old")
            lock = root / "skills-lock.json"
            lock.write_text('{"version":2,"skills":{"demo":{"source":"o/r"}}}')
            data = Path(tmp) / "data"
            data.mkdir(mode=0o700)
            plan = project_lock_commands.preview_project_lock_write(root, ["demo"])
            before = lock.read_bytes()
            (skill / "SKILL.md").write_text("new")
            with self.assertRaises(lockfiles.LockfileError):
                project_lock_commands.apply_project_lock_write(root, ["demo"], plan["plan_hash"], data_dir=data)
            self.assertEqual(lock.read_bytes(), before)
