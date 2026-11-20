"""Lifecycle reporting stays conservative and pins remain reversible."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from skillsmgr import lifecycle
from skillsmgr.errors import StoreError


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"
        self.data.mkdir(mode=0o700)
        self.now = datetime(2026, 11, 20, tzinfo=timezone.utc)

    def report(self, skills, usage=None):
        return lifecycle.candidate_report(skills, usage or {}, data_dir=self.data, now=self.now)

    def test_empty_one_and_recent_evidence(self):
        self.assertEqual(self.report([])["skills"], [])
        rows = self.report([{"name": "a"}, {"name": "b", "scope": "agents", "last_edit": "2026-11-19"}], {
            "counts": [{"name": "a", "agent": "codex", "by_day": {"2026-11-19": 1}}],
            "coverage": {"codex": {"coverage_window_start": None}}, "consented": ["codex"]})["skills"]
        self.assertEqual([row["state"] for row in rows], ["in-use", "in-use"])
        self.assertEqual(rows[0]["used_by"], ["codex"])
        self.assertEqual(self.report([{"name": "a"}])["skills"][0]["state"], "unknown")

    def test_unknown_even_when_claimed_coverage_is_full(self):
        usage = {"consented": ["codex"], "coverage": {"codex": {
            "status": "available", "coverage_window_start": "2025-01-01"}}, "counts": []}
        row = self.report([{"name": "a", "agents": ["codex"], "last_edit": "2020-01-01"}], usage)["skills"][0]
        self.assertEqual(row["state"], "unknown")

    def test_ten_thousand_cap_and_truncation(self):
        rows = ({"name": f"s{i}"} for i in range(10_001))
        report = self.report(rows)
        self.assertEqual(len(report["skills"]), 10_000)
        self.assertTrue(report["truncated"])
        self.assertTrue(all(row["state"] == "unknown" for row in report["skills"]))

    def test_pin_preview_apply_stale_undo_and_replay(self):
        plan = lifecycle.preview_pin_change(self.data, "agents", "demo", True, note="keep")
        self.assertFalse((self.data / "pins.json").exists())
        lifecycle.apply_pin_change(self.data, "agents", "demo", True, plan["plan_hash"], note="keep")
        row = self.report([{"scope": "agents", "name": "demo"}])["skills"][0]
        self.assertTrue(row["pinned"])
        self.assertEqual(row["state"], "unknown")
        with self.assertRaises(StoreError):
            lifecycle.apply_pin_change(self.data, "agents", "demo", True, plan["plan_hash"], note="keep")
        lifecycle.undo_pin_change(self.data, plan["plan_hash"])
        self.assertFalse((self.data / "pins.json").exists())
        with self.assertRaises(StoreError):
            lifecycle.undo_pin_change(self.data, plan["plan_hash"])
        again = lifecycle.preview_pin_change(self.data, "agents", "demo", True, note="keep")
        self.assertNotEqual(again["plan_hash"], plan["plan_hash"])
        lifecycle.apply_pin_change(self.data, "agents", "demo", True, again["plan_hash"], note="keep")
        with self.assertRaises(StoreError):
            lifecycle.undo_pin_change(self.data, plan["plan_hash"])
        lifecycle.undo_pin_change(self.data, again["plan_hash"])

    def test_undo_refuses_changed_pins_and_prepared_receipt(self):
        plan = lifecycle.preview_pin_change(self.data, "global", "a", True)
        lifecycle.apply_pin_change(self.data, "global", "a", True, plan["plan_hash"])
        receipt_path = self.data / "pin-backups" / (plan["plan_hash"] + ".json")
        receipt = json.loads(receipt_path.read_text())
        receipt["state"] = "prepared"
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaises(StoreError):
            lifecycle.undo_pin_change(self.data, plan["plan_hash"])
        receipt["state"] = "applied"
        receipt_path.write_text(json.dumps(receipt))
        path = self.data / "pins.json"
        path.write_text('{"version": 1, "pins": {}}')
        with self.assertRaises(StoreError):
            lifecycle.undo_pin_change(self.data, plan["plan_hash"])
        self.assertEqual(json.loads(path.read_text())["pins"], {})

    def test_unpin_undo_restores_original_note(self):
        plan = lifecycle.preview_pin_change(self.data, "global", "a", True, note="keep")
        lifecycle.apply_pin_change(self.data, "global", "a", True, plan["plan_hash"], note="keep")
        before = (self.data / "pins.json").read_bytes()
        plan = lifecycle.preview_pin_change(self.data, "global", "a", False)
        lifecycle.apply_pin_change(self.data, "global", "a", False, plan["plan_hash"])
        lifecycle.undo_pin_change(self.data, plan["plan_hash"])
        self.assertEqual((self.data / "pins.json").read_bytes(), before)

    def test_symlink_or_corrupt_pins_never_treated_as_empty(self):
        path = self.data / "pins.json"
        path.write_text('{"version":1,"pins":{},"pins":{}}')
        with self.assertRaises(StoreError):
            self.report([{"name": "a"}])
        path.unlink()
        outside = Path(self.tmp.name) / "outside"
        outside.write_text('{}')
        try:
            path.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(StoreError):
            lifecycle.preview_pin_change(self.data, "global", "a", True)
        self.assertEqual(outside.read_text(), '{}')

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_private_modes(self):
        plan = lifecycle.preview_pin_change(self.data, "global", "a", True)
        lifecycle.apply_pin_change(self.data, "global", "a", True, plan["plan_hash"])
        self.assertEqual((self.data / "pins.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.data / "pin-backups").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.data / "pin-backups" / (plan["plan_hash"] + ".json")).stat().st_mode & 0o777, 0o600)
