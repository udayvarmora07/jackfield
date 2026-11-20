"""Installed command paths for usage, lifecycle, and reviewed project changes."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from skillsmgr.catalog import save_profile
from skillsmgr.clock import iso


class LifecycleCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.data_base = self.root / "data"
        self.data = self.data_base / "skills-manager"
        self.project = self.root / "project"
        self.project.mkdir()

    def command(self, *args, code=0):
        fixture_home = self.root / "home"
        environment = dict(os.environ, HOME=str(fixture_home), CODEX_HOME=str(fixture_home / ".codex"),
                           XDG_CONFIG_HOME=str(fixture_home / ".config"))
        result = subprocess.run(
            [sys.executable, "-m", "skillsmgr", "--data-dir", str(self.data_base),
             *map(str, args), "--json"],
            text=True, capture_output=True, timeout=15, env=environment,
        )
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        self.assertFalse((self.data / "skills-manager.db").exists())
        return json.loads(result.stdout) if result.stdout else result.stderr

    def test_usage_without_consent_and_revocation(self):
        report = self.command("usage", "report", "--agent", "claude-code")
        self.assertEqual(report["coverage"]["claude-code"]["status"], "no-consent")
        self.assertFalse(self.data.exists())
        self.command("usage", "enable", "--agent", "claude-code")
        report = self.command("usage", "report", "--agent", "claude-code")
        self.assertEqual(report["coverage"]["claude-code"]["status"], "not-scanned")
        self.command("usage", "disable", "--agent", "claude-code")
        report = self.command("usage", "report", "--agent", "claude-code")
        self.assertEqual(report["coverage"]["claude-code"]["status"], "no-consent")

    def test_lock_preview_apply_drift_and_undo(self):
        skill = self.project / ".agents" / "skills" / "example"
        skill.mkdir(parents=True)
        document = skill / "SKILL.md"
        document.write_text("example\n", encoding="utf-8")
        source = "example=.agents/skills/example"
        write = ("lock", "write", "example", "--project", self.project, "--source", source)
        plan = self.command(*write, "--dry-run")
        self.assertFalse((self.project / "skills-lock.json").exists())
        self.assertFalse(self.data.exists())
        self.command(*write, "--plan-id", plan["plan_hash"])
        verify = ("lock", "verify", "--project", self.project)
        self.assertTrue(self.command(*verify)["verified"])
        document.write_text("changed\n", encoding="utf-8")
        self.assertFalse(self.command(*verify, code=1)["verified"])
        self.command("lock", "undo", "--project", self.project, "--plan-id", plan["plan_hash"])
        self.assertFalse((self.project / "skills-lock.json").exists())
        document.write_text("example\n", encoding="utf-8")
        again = self.command(*write, "--dry-run")
        self.assertNotEqual(again["plan_hash"], plan["plan_hash"])
        self.command(*write, "--plan-id", again["plan_hash"])
        self.command("lock", "undo", "--project", self.project, "--plan-id", plan["plan_hash"], code=1)
        self.assertTrue(self.command(*verify)["verified"])

    def test_codex_native_handoff_has_no_write_path(self):
        flags = ("--project", self.project, "--agent", "codex", "--off", "example")
        plan = self.command("native-profile", "preview", *flags)
        self.assertEqual(plan["status"], "launch-only")
        self.assertEqual(plan["argv"][:2], ["codex", "-c"])
        self.command("native-profile", "apply", *flags, "--plan-id", plan["plan_id"], code=1)
        self.assertFalse(list(self.project.iterdir()))
        self.assertFalse(self.data.exists())

    def test_saved_native_profile_handoff_and_stale_write(self):
        self.data_base.mkdir(mode=0o700)
        self.data.mkdir(mode=0o700)
        save_profile(self.data, "fixture", {"native": {"off": ["one", "two"]}})
        flags = ("--project", self.project, "--profile", "fixture")
        handoff = self.command("native-profile", "preview", "--agent", "codex", *flags)
        self.assertEqual(handoff["profile"], "fixture")
        self.assertEqual(handoff["off"], ["one", "two"])
        if os.name == "posix" and hasattr(os, "O_NOFOLLOW"):
            config = self.project / ".claude" / "settings.local.json"
            config.parent.mkdir()
            plan = self.command("native-profile", "preview", "--agent", "claude-code", *flags)
            save_profile(self.data, "fixture", {"native": {"off": ["three"]}})
            self.command("native-profile", "apply", "--agent", "claude-code", *flags,
                         "--plan-id", plan["plan_id"], code=1)
            self.assertFalse(config.exists())

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "guarded directory descriptors")
    def test_native_project_apply_and_undo(self):
        config = self.project / ".claude" / "settings.local.json"
        config.parent.mkdir()
        flags = ("--project", self.project, "--agent", "claude-code", "--off", "example")
        plan = self.command("native-profile", "preview", *flags)
        self.assertFalse(config.exists())
        applied = self.command("native-profile", "apply", *flags, "--plan-id", plan["plan_id"])
        self.assertEqual(json.loads(config.read_text())["skillOverrides"], {"example": "off"})
        self.command("native-profile", "undo", "--backup-id", applied["backup_id"])
        self.assertFalse(config.exists())

    def test_pin_and_candidates_discover_skill_without_index(self):
        document = self.data / "skills" / "example" / "SKILL.md"
        self.data_base.mkdir(mode=0o700)
        document.parent.mkdir(parents=True, mode=0o700)
        self.data.chmod(0o700)
        document.write_text("---\nname: example\ndescription: Example.\n---\n", encoding="utf-8")
        os.utime(document, (946684800, 946684800))
        review = self.command("archive", "candidates")
        self.assertEqual(review["skills"][0]["state"], "unknown")
        self.assertEqual(review["skills"][0]["last_edit"], "2000-01-01T00:00:00Z")
        combined = self.command("archive", "candidates", "--scope", "all")
        self.assertIn(review["skills"][0], combined["skills"])
        plan = self.command("archive", "pin", "example")
        self.assertFalse((self.data / "pins.json").exists())
        self.command("archive", "pin", "example", "--plan-id", plan["plan_hash"])
        self.assertTrue(self.command("archive", "candidates")["skills"][0]["pinned"])
        self.command("archive", "undo-pin", "--plan-id", plan["plan_hash"])
        self.assertTrue(document.is_file())
        self.assertFalse(self.command("archive", "candidates")["skills"][0]["pinned"])

    def test_candidates_report_recent_active_and_disabled_document_mtimes(self):
        self.data_base.mkdir(mode=0o700)
        self.data.mkdir(mode=0o700)
        recent = int(time.time()) - 60
        for name, filename in (("active", "SKILL.md"), ("disabled", "SKILL.md.disabled")):
            document = self.data / "skills" / name / filename
            document.parent.mkdir(parents=True)
            document.write_text(f"---\nname: {name}\ndescription: Example.\n---\n", encoding="utf-8")
            os.utime(document, (recent, recent))
        rows = self.command("archive", "candidates", "--days", 2)["skills"]
        self.assertEqual([(row["name"], row["state"], row["used_by"]) for row in rows],
                         [("active", "in-use", []), ("disabled", "in-use", [])])
        self.assertEqual([row["last_edit"] for row in rows], [iso(recent)] * 2)

    def test_candidates_skip_symlink_document_and_directory_mtimes(self):
        self.data_base.mkdir(mode=0o700)
        self.data.mkdir(mode=0o700)
        document = self.data / "skills" / "example" / "SKILL.md"
        document.parent.mkdir(parents=True)
        elsewhere = self.root / "elsewhere"
        elsewhere.write_text("---\nname: example\ndescription: Example.\n---\n", encoding="utf-8")
        target = document.parent.with_name("target")
        target.mkdir()
        (target / "SKILL.md").write_text("---\nname: target\ndescription: Example.\n---\n", encoding="utf-8")
        try:
            document.symlink_to(elsewhere)
            target.with_name("alias").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        rows = {row["name"]: row for row in self.command("archive", "candidates")["skills"]}
        self.assertIsNotNone(rows["target"]["last_edit"])
        for name in ("example", "alias"):
            self.assertIsNone(rows[name]["last_edit"])
            self.assertEqual(rows[name]["state"], "unknown")
