"""Lifecycle reporting stays conservative and pins remain reversible."""
import base64
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(rows[0]["reason"], "recent cached usage for the same name")
        self.assertEqual(rows[1]["reason"], "recent document modification")
        self.assertEqual(self.report([{"name": "a"}])["skills"][0]["state"], "unknown")

    def test_unknown_even_when_claimed_coverage_is_full(self):
        usage = {"consented": ["codex"], "coverage": {"codex": {
            "status": "available", "coverage_window_start": "2025-01-01"}}, "counts": []}
        row = self.report([{"name": "a", "agents": ["codex"], "last_edit": "2020-01-01"}], usage)["skills"][0]
        self.assertEqual(row["state"], "unknown")

    def test_observations_share_the_requested_utc_day_window(self):
        skills = [{"name": "today", "last_edit": "2026-11-20T00:00:00Z"},
                  {"name": "yesterday", "last_edit": "2026-11-19T23:59:59Z"},
                  {"name": "future", "last_edit": "2026-11-21T00:00:00Z"},
                  {"name": "usage-today"}, {"name": "usage-yesterday"}, {"name": "usage-future"}]
        usage = {"counts": [{"name": f"usage-{name}", "agent": "codex", "by_day": {day: 1}}
                            for name, day in (("today", "2026-11-20"), ("yesterday", "2026-11-19"),
                                              ("future", "2026-11-21"))]}
        report = lifecycle.candidate_report(skills, usage, data_dir=self.data, days=1, now=self.now)
        self.assertEqual(report["cutoff"], "2026-11-20")
        self.assertEqual([row["state"] for row in report["skills"]],
                         ["in-use", "unknown", "unknown", "in-use", "unknown", "unknown"])

    def test_ten_thousand_cap_and_truncation(self):
        rows = ({"name": f"s{i}"} for i in range(10_001))
        report = self.report(rows)
        self.assertEqual(len(report["skills"]), 10_000)
        self.assertTrue(report["truncated"])
        self.assertTrue(all(row["state"] == "unknown" for row in report["skills"]))

    def test_timestamp_offsets_are_normalized_before_utc_calendar_comparison(self):
        rows = [{"name": "previous", "last_edit": "2026-11-20T00:15:00+01:00"},
                {"name": "current", "last_edit": "2026-11-19T23:45:00-01:00"}]
        report = lifecycle.candidate_report(rows, {}, data_dir=self.data, days=1, now=self.now)
        self.assertEqual([row["state"] for row in report["skills"]], ["unknown", "in-use"])

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

    def test_pin_undo_recovers_a_replacement_that_completed_before_interrupt(self):
        pin = lifecycle.preview_pin_change(self.data, "global", "demo", True)
        write = lifecycle._write

        def interrupted_after_replace(path, data, **kwargs):
            write(path, data, **kwargs)
            if path.name == "pins.json":
                raise KeyboardInterrupt

        with patch.object(lifecycle, "_write", side_effect=interrupted_after_replace):
            with self.assertRaises(KeyboardInterrupt):
                lifecycle.apply_pin_change(self.data, "global", "demo", True, pin["plan_hash"])

        self.assertTrue(self.report([{"name": "demo"}])["skills"][0]["pinned"])
        self.assertTrue(lifecycle.undo_pin_change(self.data, pin["plan_hash"])["restored"])
        self.assertFalse((self.data / "pins.json").exists())

    def test_interrupted_unpin_cannot_undo_a_later_unpin_of_the_same_skill(self):
        pin = lifecycle.preview_pin_change(self.data, "global", "demo", True)
        lifecycle.apply_pin_change(self.data, "global", "demo", True, pin["plan_hash"])
        original = (self.data / "pins.json").read_bytes()
        first = lifecycle.preview_pin_change(self.data, "global", "demo", False)
        write = lifecycle._write

        def abort_replacement(path, data, **kwargs):
            if path.name == "pins.json":
                raise OSError("injected write failure")
            write(path, data, **kwargs)

        with patch.object(lifecycle, "_write", side_effect=abort_replacement):
            with self.assertRaisesRegex(OSError, "injected write failure"):
                lifecycle.apply_pin_change(self.data, "global", "demo", False, first["plan_hash"])
        self.assertEqual((self.data / "pins.json").read_bytes(), original)
        with self.assertRaisesRegex(StoreError, "undo refused"):
            lifecycle.undo_pin_change(self.data, first["plan_hash"])

        second = lifecycle.preview_pin_change(self.data, "global", "demo", False)
        lifecycle.apply_pin_change(self.data, "global", "demo", False, second["plan_hash"])
        with self.assertRaisesRegex(StoreError, "undo refused"):
            lifecycle.undo_pin_change(self.data, first["plan_hash"])
        self.assertTrue(lifecycle.undo_pin_change(self.data, second["plan_hash"])["restored"])
        self.assertEqual((self.data / "pins.json").read_bytes(), original)

    def test_undo_receipt_legacy_compatibility_and_preimage_validation(self):
        initial = lifecycle.preview_pin_change(self.data, "global", "demo", True)
        lifecycle.apply_pin_change(self.data, "global", "demo", True, initial["plan_hash"])
        path = self.data / "pins.json"
        original = path.read_bytes()
        change = lifecycle.preview_pin_change(self.data, "global", "demo", False)
        lifecycle.apply_pin_change(self.data, "global", "demo", False, change["plan_hash"])
        receipt_path = self.data / "pin-backups" / (change["plan_hash"] + ".json")
        receipt = json.loads(receipt_path.read_text())
        path_after = path.read_bytes()
        tampered = {**receipt, "before": base64.b64encode(b'{"version":1,"pins":{}}').decode("ascii")}
        receipt_path.write_text(json.dumps(tampered))
        with self.assertRaisesRegex(StoreError, "invalid or missing pin undo receipt"):
            lifecycle.undo_pin_change(self.data, change["plan_hash"])
        self.assertEqual(path.read_bytes(), path_after)

        # Simulate the receipt and pins metadata emitted by the previous writer.
        legacy_doc = json.loads(path_after)
        del legacy_doc["last_pin_plan"]
        legacy_after = json.dumps(legacy_doc).encode("utf-8")
        path.write_bytes(legacy_after)
        receipt.update(state="applied", after=lifecycle._hash(legacy_after))
        del receipt["before_hash"]
        receipt_path.write_text(json.dumps(receipt))
        self.assertTrue(lifecycle.undo_pin_change(self.data, change["plan_hash"])["restored"])
        self.assertEqual(path.read_bytes(), original)

    def test_undo_succeeds_when_receipt_update_fails_after_restore(self):
        change = lifecycle.preview_pin_change(self.data, "global", "demo", True)
        lifecycle.apply_pin_change(self.data, "global", "demo", True, change["plan_hash"])
        with (
            patch.object(lifecycle, "_write", side_effect=OSError("receipt update failed")),
            patch("sys.stderr", new_callable=io.StringIO) as logs,
        ):
            self.assertTrue(lifecycle.undo_pin_change(self.data, change["plan_hash"])["restored"])
        self.assertFalse((self.data / "pins.json").exists())
        self.assertIn("pins restored", logs.getvalue())
        with self.assertRaisesRegex(StoreError, "undo refused"):
            lifecycle.undo_pin_change(self.data, change["plan_hash"])

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
