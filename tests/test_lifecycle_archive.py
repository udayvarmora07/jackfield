"""Manual archive review, move, and recovery through disposable libraries."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from skillsmgr import lifecycle, lifecycle_archive as archive
from skillsmgr.errors import StoreError
from skillsmgr.store import Store


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.data = self.base / "skills-manager"
        self.data.mkdir(mode=0o700)
        self.store = Store(self.data)
        self.skill = self.store.skills_dir / "example"
        self.skill.mkdir(parents=True)
        self.document = self.skill / "SKILL.md.disabled"
        self.document.write_bytes(b"---\nname: example\ndescription: Example archive.\n---\nArchived text.\n")
        self.asset = self.skill / "references" / "sample.bin"
        self.asset.parent.mkdir()
        self.asset.write_bytes(b"\xff\x00\r\n")
        (self.skill / "empty").mkdir()

    def cli(self, *arguments, code=0):
        result = subprocess.run(
            [sys.executable, "-m", "skillsmgr", "--data-dir", str(self.base),
             "archive", *arguments, "--json"], capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, code, result.stderr)
        return json.loads(result.stdout)

    def archive(self):
        review = archive.preview_archive(self.store, "example")
        return archive.apply_archive(self.store, "example", review["plan_id"])

    def test_cli_preserves_the_complete_disabled_folder_and_reconciles_index(self):
        before = (self.document.read_bytes(), self.asset.read_bytes())
        review = self.cli("apply", "example")
        self.assertEqual(review["status"], "preview")
        self.assertFalse((self.data / "archive").exists())
        self.assertFalse(self.store.db_path.exists())

        moved = self.cli("apply", "example", "--plan-id", review["plan_id"])
        self.assertEqual(moved["status"], "archived")
        self.assertEqual(moved["path"], review["path"])
        self.assertFalse(self.skill.exists())
        self.store.purge_trash()
        self.assertTrue(Path(moved["path"]).is_dir())
        self.assertEqual(self.store.list(), [])

        restored = self.cli("restore", review["archive_id"])
        self.assertEqual(restored["status"], "restored")
        self.assertEqual((self.document.read_bytes(), self.asset.read_bytes()), before)
        self.assertTrue((self.skill / "empty").is_dir())
        self.assertTrue(self.store.get("example")["disabled"])
        self.assertFalse(Path(moved["path"]).exists())
        with self.assertRaisesRegex(StoreError, "already used"):
            archive.apply_archive(self.store, "example", review["plan_id"])

    def test_changed_companion_or_later_pin_invalidates_the_preview(self):
        plan = archive.preview_archive(self.store, "example")["plan_id"]
        self.asset.write_bytes(b"modified")
        with self.assertRaisesRegex(StoreError, "stale"):
            archive.apply_archive(self.store, "example", plan)
        again = archive.preview_archive(self.store, "example")["plan_id"]
        pin = lifecycle.preview_pin_change(self.data, "global", "example", True)
        lifecycle.apply_pin_change(self.data, "global", "example", True, pin["plan_hash"])
        with self.assertRaisesRegex(StoreError, "pinned"):
            archive.apply_archive(self.store, "example", again)
        self.assertTrue(self.document.is_file())
        self.assertFalse((self.data / "archive").exists())

    def test_competing_applies_leave_one_payload_and_one_receipt(self):
        plans = [archive.preview_archive(self.store, "example")["plan_id"] for _ in range(2)]

        def move(plan):
            try:
                return archive.apply_archive(self.store, "example", plan)
            except StoreError:
                return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            result, = [row for row in executor.map(move, plans) if row is not None]
        entries = list((self.data / "archive" / "global").iterdir())
        self.assertEqual([path.name for path in entries], [result["archive_id"]])
        self.assertFalse(self.skill.exists())
        self.assertTrue((Path(result["path"]) / self.document.name).is_file())

    def test_corrupt_and_occupied_restore_preserve_files(self):
        moved = self.archive()
        archived_asset = Path(moved["path"]) / "references" / "sample.bin"
        original = archived_asset.read_bytes()
        archived_asset.write_bytes(b"changed")
        with self.assertRaisesRegex(StoreError, "differs"):
            archive.restore_archive(self.store, moved["archive_id"])
        self.assertFalse(self.skill.exists())
        archived_asset.write_bytes(original)
        self.skill.mkdir()
        occupant = self.skill / "unrelated"
        occupant.write_bytes(b"do not touch")
        with self.assertRaisesRegex(StoreError, "occupied"):
            archive.restore_archive(self.store, moved["archive_id"])
        self.assertEqual(occupant.read_bytes(), b"do not touch")
        self.assertEqual(archived_asset.read_bytes(), original)

    def test_receipt_cannot_redirect_restore_to_another_library_name(self):
        moved = self.archive()
        receipt_path = Path(moved["path"]).parent / archive.RECEIPT
        receipt = json.loads(receipt_path.read_bytes())
        receipt["name"] = "unrelated"
        receipt["source"] = (self.store.skills_dir / "unrelated").as_posix()
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(StoreError, "invalid or missing archive receipt"):
            archive.restore_archive(self.store, moved["archive_id"])
        self.assertFalse((self.store.skills_dir / "unrelated").exists())
        self.assertTrue(Path(moved["path"]).is_dir())

    def test_blocks_indirect_paths_invalid_ids_and_oversized_trees(self):
        with self.assertRaisesRegex(StoreError, "invalid archive ID"):
            archive.restore_archive(self.store, "../example")
        with patch.object(archive, "MAX_ENTRIES", 2):
            with self.assertRaisesRegex(StoreError, "exceeds"):
                archive.preview_archive(self.store, "example")
        self.assertTrue(self.document.is_file())
        link = self.skill / "outside"
        try:
            link.symlink_to(self.base, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(StoreError, "indirect|links"):
            archive.preview_archive(self.store, "example")
        self.assertTrue(self.document.is_file())

    def test_failed_index_update_reports_committed_filesystem_state(self):
        with patch.object(self.store, "_drop_index_row", side_effect=StoreError("busy")):
            moved = self.archive()
        self.assertIn("db resync", moved["index_warning"])
        self.assertFalse(self.skill.exists())
        self.assertTrue(Path(moved["path"]).is_dir())
        archive.restore_archive(self.store, moved["archive_id"])
        self.assertTrue(self.document.is_file())

    def test_failed_rename_leaves_original_and_a_non_replayable_receipt(self):
        review = archive.preview_archive(self.store, "example")
        original = self.asset.read_bytes()
        with patch.object(os, "rename", side_effect=PermissionError("rename denied")):
            with self.assertRaisesRegex(StoreError, "could not move"):
                archive.apply_archive(self.store, "example", review["plan_id"])
        self.assertEqual(self.asset.read_bytes(), original)
        self.assertTrue((Path(review["path"]).parent / archive.RECEIPT).is_file())
        with self.assertRaisesRegex(StoreError, "no skill folder"):
            archive.restore_archive(self.store, review["archive_id"])
