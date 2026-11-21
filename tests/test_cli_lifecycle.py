"""Installed command paths for usage, lifecycle, and reviewed project changes."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

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

    def command(self, *args, code=0, cwd=None, json_output=True):
        fixture_home = self.root / "home"
        environment = dict(os.environ, HOME=str(fixture_home), CODEX_HOME=str(fixture_home / ".codex"),
                           CLAUDE_CONFIG_DIR=str(fixture_home / ".claude"),
                           XDG_CONFIG_HOME=str(fixture_home / ".config"))
        if cwd is not None:
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        output_flags = ["--json"] if json_output else []
        result = subprocess.run(
            [sys.executable, "-m", "skillsmgr", "--data-dir", str(self.data_base),
             *map(str, args), *output_flags],
            text=True, capture_output=True, timeout=15, env=environment, cwd=cwd,
        )
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        self.assertFalse((self.data / "skills-manager.db").exists())
        return json.loads(result.stdout) if json_output and result.stdout else result.stdout or result.stderr

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
        (self.root / "home" / ".agents" / "skills").mkdir(parents=True)
        combined = self.command("archive", "candidates", "--scope", "all")
        self.assertIn(review["skills"][0], combined["skills"])
        readiness = combined["archive_readiness"]
        self.assertEqual(readiness["consumer_mapping"], "partial")
        self.assertEqual(readiness["usage_continuity"], "unverified")
        self.assertEqual(readiness["edit_install_continuity"], "unverified")
        self.assertIn({"consumer": "codex", "transcript_scan": "no-consent"},
                      readiness["documented_scope_consumers"]["agents"])
        self.assertIn({"consumer": "cursor", "transcript_scan": "no-reader"},
                      readiness["documented_scope_consumers"]["agents"])
        self.assertEqual(readiness["documented_scope_consumers"]["global"], [])
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

    def test_candidates_distinguish_empty_missing_and_broken_inventory_roots(self):
        home = self.root / "home"
        (home / ".agents" / "skills").mkdir(parents=True)
        broken = home / ".codex" / "skills"
        broken.parent.mkdir(parents=True)
        broken.write_text("this is a file", encoding="utf-8")
        report = self.command("archive", "candidates", "--scope", "all", cwd=self.project)
        self.assertEqual(report["skills"], [])
        inventory = report["inventory"]
        self.assertEqual(inventory["agents"]["status"], "scanned")
        self.assertEqual(inventory["gemini"]["status"], "missing")
        self.assertEqual(inventory["codex"]["status"], "partial")
        self.assertEqual([event["reason"] for event in inventory["codex"]["diagnostics"]],
                         ["scope root is not a directory"])
        self.assertNotIn(str(self.root), json.dumps(inventory))

    def test_candidates_list_documented_readers_for_project_scope(self):
        skill = self.project / ".agents" / "skills" / "example"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: example\ndescription: Example.\n---\n", encoding="utf-8")
        report = self.command("archive", "candidates", "--scope", "project-agents", cwd=self.project)
        self.assertEqual([row["name"] for row in report["skills"]], ["example"])
        readers = report["archive_readiness"]["documented_scope_consumers"]["project-agents"]
        self.assertIn({"consumer": "codex", "transcript_scan": "no-consent"}, readers)
        self.assertIn({"consumer": "commandcode", "transcript_scan": "no-consent"}, readers)
        self.assertEqual(report["archive_readiness"]["consumer_mapping"], "partial")

    def test_standalone_gemini_document_marks_managed_inventory_partial(self):
        original = "---\nname: root-skill\ndescription: Example.\n---\n"
        for scope, relative in (("project-gemini", ".gemini/skills"), ("project-agents", ".agents/skills")):
            with self.subTest(scope=scope):
                root = self.project / relative
                root.mkdir(parents=True)
                document = root / "SKILL.md"
                document.write_text(original, encoding="utf-8")

                report = self.command("archive", "candidates", "--scope", scope, cwd=self.project)
                inventory = report["inventory"][scope]
                self.assertEqual(inventory["status"], "partial")
                self.assertEqual([event["reason"] for event in inventory["diagnostics"]],
                                 ["standalone Gemini SKILL.md is outside the managed skill inventory"])
                self.assertEqual(report["skills"], [])
                self.assertEqual(document.read_text(encoding="utf-8"), original)

    def test_candidates_discover_gemini_and_grouped_commandcode_skills(self):
        for location, name in (
            (".gemini/skills/gemini-demo", "gemini-demo"),
            (".gemini/skills/group/too-deep", "too-deep"),
            (".commandcode/skills/group/command-demo", "command-demo"),
            (".commandcode/skills/group/command-demo/references/fixture", "fixture"),
        ):
            folder = self.project / location
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Example.\n---\n", encoding="utf-8")

        report = self.command("archive", "candidates", "--scope", "all", cwd=self.project)
        self.assertEqual({(row["scope"], row["name"]) for row in report["skills"]}, {
            ("project-gemini", "gemini-demo"), ("project-commandcode", "command-demo"),
        })
        readiness = report["archive_readiness"]
        for scope, consumer in (("project-gemini", "gemini"), ("project-commandcode", "commandcode")):
            self.assertEqual(report["inventory"][scope]["status"], "scanned")
            self.assertIn({"consumer": consumer, "transcript_scan": "no-consent"},
                          readiness["documented_scope_consumers"][scope])

    def test_candidates_report_one_inventory_for_a_shared_physical_root(self):
        home = self.root / "home"
        shared = home / ".claude" / "skills"
        skill = shared / "example"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: example\ndescription: Example.\n---\n", encoding="utf-8")
        alias = home / ".codex" / "skills"
        alias.parent.mkdir()
        try:
            alias.symlink_to(shared, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        report = self.command("archive", "candidates", "--scope", "all", cwd=self.project)
        self.assertEqual([(row["scope"], row["name"]) for row in report["skills"]], [("claude-code", "example")])
        self.assertEqual(report["inventory"]["codex"], {
            "status": "shared-root", "diagnostics": [], "canonical_scope": "claude-code",
        })
        readers = report["archive_readiness"]["documented_scope_consumers"]
        self.assertEqual(readers["claude-code"], readers["codex"])
        self.assertIn({"consumer": "claude-code", "transcript_scan": "no-consent"}, readers["codex"])
        rendered = self.command("archive", "candidates", "--scope", "all", cwd=self.project, json_output=False)
        self.assertIn("codex inventory shared-root with claude-code", rendered)

    def test_candidates_scan_shared_roots_with_different_discovery_rules(self):
        home = self.root / "home"
        shared = home / ".claude" / "skills"
        for relative in ("flat", "team/demo", "another/demo"):
            skill = shared / relative
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {skill.name}\ndescription: Example.\n---\n", encoding="utf-8",
            )
        alias = home / ".commandcode" / "skills"
        alias.parent.mkdir()
        try:
            alias.symlink_to(shared, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        report = self.command("archive", "candidates", "--scope", "all", cwd=self.project)
        self.assertEqual({(row["scope"], row["name"], row["relative_path"]) for row in report["skills"]}, {
            ("claude-code", "flat", "flat"), ("commandcode", "flat", "flat"),
            ("commandcode", "demo", "team/demo"), ("commandcode", "demo", "another/demo"),
        })
        self.assertEqual(report["inventory"]["commandcode"]["status"], "scanned")
        readers = report["archive_readiness"]["documented_scope_consumers"]
        self.assertEqual(readers["claude-code"], readers["commandcode"])
        self.assertIn({"consumer": "commandcode", "transcript_scan": "no-consent"}, readers["claude-code"])
        rendered = self.command("archive", "candidates", "--scope", "commandcode", cwd=self.project, json_output=False)
        self.assertIn("folder team/demo", rendered)
        self.assertIn("folder another/demo", rendered)

    def test_candidates_include_pins_from_equivalent_shared_scopes(self):
        home = self.root / "home"
        root = home / ".claude" / "skills"
        skill = root / "example"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: example\ndescription: Example.\n---\n", encoding="utf-8")
        alias = home / ".codex" / "skills"
        alias.parent.mkdir()
        try:
            alias.symlink_to(root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")

        args = ("archive", "pin", "example", "--scope", "codex")
        plan = self.command(*args)
        self.command(*args, "--plan-id", plan["plan_hash"])

        review = ("archive", "candidates", "--scope", "all")
        row, = self.command(*review, cwd=self.project)["skills"]
        self.assertEqual(row["scope"], "claude-code")
        self.assertTrue(row["pinned"])
        self.assertEqual(row["pinned_scopes"], ["codex"])
        rendered = self.command(*review, cwd=self.project, json_output=False)
        self.assertIn("(pinned via codex)", rendered)

        alias.rename(alias.with_name("previous-skills"))
        alias.mkdir()
        row, = self.command(*review, cwd=self.project)["skills"]
        self.assertFalse(row["pinned"])
        self.assertEqual(row["pinned_scopes"], [])

    def test_candidates_marks_inventory_partial_when_a_skill_name_is_unaddressable(self):
        skill = self.root / "home" / ".claude" / "skills" / "UpperCase"
        skill.mkdir(parents=True)
        empty = self.command("archive", "candidates", "--scope", "claude-code")
        self.assertEqual(empty["inventory"]["claude-code"]["status"], "scanned")
        (skill / "SKILL.md").write_text("---\nname: unsafe-name\ndescription: Example.\n---\n", encoding="utf-8")
        report = self.command("archive", "candidates", "--scope", "claude-code")
        self.assertEqual(report["skills"], [])
        inventory = report["inventory"]["claude-code"]
        self.assertEqual(inventory["status"], "partial")
        self.assertIn("one or more skill names are outside the managed inventory",
                      [row["reason"] for row in inventory["diagnostics"]])

    def test_candidates_include_a_project_alias_with_its_own_discovery_rules(self):
        shared = self.project / ".claude" / "skills"
        skill = shared / "team" / "demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: demo\ndescription: Example.\n---\n", encoding="utf-8")
        alias = self.project / ".commandcode" / "skills"
        alias.parent.mkdir()
        try:
            alias.symlink_to(shared, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        report = self.command("archive", "candidates", "--scope", "all", cwd=self.project)
        self.assertEqual([(row["scope"], row["relative_path"]) for row in report["skills"]],
                         [("project-commandcode", "team/demo")])
        self.assertEqual(report["inventory"]["project-claude"]["status"], "scanned")
        selected = self.command("archive", "candidates", "--scope", "project-commandcode", cwd=self.project)
        self.assertEqual(report["skills"], selected["skills"])

    def test_candidates_do_not_claim_later_scopes_were_scanned_when_truncated(self):
        from skillsmgr import cli, lifecycle, scopes

        self.data_base.mkdir(mode=0o700)
        self.data.mkdir(mode=0o700)
        root = self.data / "skills"
        other = self.project / "skills"
        other.mkdir()
        for name in ("one", "two"):
            skill = root / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Example.\n---\n", encoding="utf-8")
        descriptors = [scopes.Scope("global", "Global", root, "global", True),
                       scopes.Scope("agents", "Agents", other, "agent", True)]
        output = StringIO()
        with patch.object(lifecycle, "MAX_SKILLS", 1), patch.object(scopes, "known_scopes", return_value=descriptors), \
                redirect_stdout(output):
            self.assertEqual(cli.main(["--data-dir", str(self.data_base), "archive", "candidates", "--scope", "all", "--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["truncated"])
        self.assertEqual(report["inventory"]["global"]["status"], "scanned")
        self.assertEqual(report["inventory"]["agents"]["status"], "not-scanned")

    def test_candidates_repeat_a_partial_scopes_scan_for_an_equivalent_alias(self):
        from skillsmgr import cli_lifecycle, scopes

        root = self.project / "skills"
        root.mkdir()
        descriptors = [scopes.Scope(scope, scope, root, "agent", True) for scope in ("claude-code", "codex")]
        inventory = {descriptor.id: {"status": "not-scanned", "diagnostics": []} for descriptor in descriptors}

        def scan(descriptor, *, collector):
            if descriptor.id == "claude-code":
                collector.append({"section": "scope-scan", "reason": "transient failure"})
            return []

        observed = {}
        self.assertEqual(list(cli_lifecycle._candidate_inventory(descriptors, inventory, observed, scan)), [])
        self.assertEqual([inventory[scope]["status"] for scope in ("claude-code", "codex")], ["partial", "scanned"])
        self.assertEqual(observed, {"claude-code": root, "codex": root})

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
