"""First-run guidance must stay read-only and keep JSON machine-readable."""

import contextlib
import io
import json
import os
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import cli, cli_handlers, cli_output, context, scopes
from skillsmgr.store import Store


class FirstRunGuidanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        env = patch.dict(os.environ, HOME=str(self.home),
                         SKILLS_MANAGER_DATA=str(self.root / "data"))
        env.start()
        self.addCleanup(env.stop)
        self.store = Store()
        token = context.ACTIVE_STORE.set(self.store)
        self.addCleanup(context.ACTIVE_STORE.reset, token)

    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["--no-color", *args])
        return code, out.getvalue(), err.getvalue()

    def test_empty_global_list_names_populated_agent_scopes_without_writing(self):
        scopes.create_skill("agents", "one", "Use this for testing")
        scopes.create_skill("claude-code", "two", "Use this for testing")
        before = sorted(str(p) for p in self.store.data_dir.rglob("*"))
        code, out, err = self.invoke(["list"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("--scope all", out)
        self.assertIn("agents: 1", out)
        self.assertIn("claude-code: 1", out)
        self.assertEqual(sorted(str(p) for p in self.store.data_dir.rglob("*")), before)
        self.assertFalse(self.store.db_path.exists())

    def test_json_and_filtered_lists_do_not_scan_other_scopes_for_a_hint(self):
        with patch.object(scopes, "list_scopes", side_effect=AssertionError("extra scan")):
            code, out, err = self.invoke(["list", "--json"])
            self.assertEqual((code, json.loads(out), err), (0, [], ""))
            self.assertEqual(self.invoke(["list", "--category", "absent"]),
                             (0, "no skills installed\n", ""))

    def test_empty_home_does_not_suggest_an_empty_aggregate(self):
        self.assertEqual(self.invoke(["list"]), (0, "no skills installed\n", ""))

    def test_unavailable_agent_summary_does_not_break_an_empty_global_list(self):
        with patch.object(scopes, "list_scopes", side_effect=OSError("unreadable folder")):
            code, text, err = self.invoke(["list"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("could not be checked", text)
        self.assertNotIn("unreadable folder", text)

    def test_fresh_doctor_is_healthy_without_creating_an_index(self):
        report = self.store.doctor()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["db_integrity"], "unindexed")
        self.assertEqual(report["repair"], [])
        code, out, err = self.invoke(["doctor"])
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("rebuild", out)
        self.assertIn("no skills", out)
        self.assertFalse(self.store.data_dir.exists())

    def test_missing_index_with_skill_or_trash_still_needs_repair(self):
        for relative in ("skills/demo/SKILL.md", "trash/demo-2026-11-13_00-00-00Z/SKILL.md"):
            with self.subTest(relative=relative):
                file = self.store.data_dir / relative
                file.parent.mkdir(parents=True, mode=0o700)
                file.write_text("---\nname: demo\ndescription: Demo\n---\nBody")
                report = self.store.doctor()
                self.assertFalse(report["ok"], report)
                self.assertTrue(report["repair"])
                file.unlink()
                file.parent.rmdir()

    def test_corrupt_empty_index_is_not_mistaken_for_a_fresh_install(self):
        self.store.data_dir.mkdir(mode=0o700, parents=True)
        self.store.db_path.write_bytes(b"broken index")
        before = self.store.db_path.read_bytes()
        report = self.store.doctor()
        self.assertFalse(report["ok"])
        self.assertTrue(report["repair"])
        self.assertEqual(self.store.db_path.read_bytes(), before)

    def test_dangling_index_link_is_not_mistaken_for_a_fresh_install(self):
        self.store.data_dir.mkdir(mode=0o700, parents=True)
        target = self.root / "missing-index"
        try:
            self.store.db_path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("host does not permit symlinks")
        report = self.store.doctor()
        self.assertFalse(report["ok"], report)
        self.assertTrue(report["repair"])
        self.assertTrue(self.store.db_path.is_symlink())
        self.assertFalse(target.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX permission remedy")
    def test_group_writable_data_base_has_a_quoted_exact_remedy(self):
        base = self.root / "my data's files"
        base.mkdir(mode=0o775)
        base.chmod(0o775)
        code, out, err = self.invoke(["--data-dir", str(base), "list"])
        self.assertEqual((code, out), (1, ""))
        self.assertIn("chmod 700 " + shlex.quote(str(base)), err)
        self.assertEqual(base.stat().st_mode & 0o777, 0o775)

    def test_scope_paths_are_shortened_in_text_and_absolute_in_json(self):
        scopes.create_skill("agents", "one", "Use this for testing")
        _, text, _ = self.invoke(["scopes"])
        self.assertIn("~/.agents/skills", text)
        self.assertNotIn(str(self.home), text)
        _, raw, _ = self.invoke(["scopes", "--json"])
        agent = next(row for row in json.loads(raw) if row["id"] == "agents")
        self.assertEqual(agent["path"], str(self.home / ".agents/skills"))
        _, text, _ = self.invoke(["doctor", "--scope", "all"])
        self.assertIn("~/.agents/skills", text)
        self.assertNotIn(str(self.home), text)
        code, text, err = self.invoke(["doctor", "--explain", "codex", "--project", str(self.home)])
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn(str(self.home), text)
        _, raw, _ = self.invoke(["doctor", "--explain", "codex", "--project", str(self.home), "--json"])
        self.assertIn(str(self.home), raw)

    def test_hygiene_paths_are_shortened_without_changing_the_report(self):
        scopes.create_skill("agents", "one", "Use this for testing")
        _, text, _ = self.invoke(["doctor", "--scope", "all", "--hygiene"])
        self.assertNotIn(str(self.home), text)
        _, raw, _ = self.invoke(["doctor", "--scope", "all", "--hygiene", "--json"])
        self.assertIn(str(self.home), raw)

    def test_path_shortening_preserves_sibling_prefixes_and_terminal_safety(self):
        with patch.object(cli_output, "home_dir", return_value=Path("/home/alice")):
            text = cli_output.home_display(
                "at /home/alice/a; '/home/alice/b' /home/alice-other/c "
                "https://host/home/alice/d \x1b[31m")
        self.assertEqual(text, "at ~/a; '~/b' /home/alice-other/c https://host/home/alice/d ?[31m")

    def test_missing_explain_project_shortens_and_sanitizes_stderr_only(self):
        project = self.home / "missing\x1b[31m"
        code, text, err = self.invoke(["doctor", "--explain", "codex", "--project", str(project)])
        self.assertEqual(code, 1)
        self.assertNotIn(str(self.home), text + err)
        self.assertNotIn("\x1b", text + err)
        self.assertIn("~/missing?[31m", err)
        _, raw, _ = self.invoke(["doctor", "--explain", "codex", "--project", str(project), "--json"])
        self.assertIn(str(project), json.loads(raw)["reason"])

    def test_divergence_follow_up_names_a_real_comparison_workflow(self):
        scopes.create_skill("agents", "demo", "Use this for one task", body="First")
        scopes.create_skill("claude-code", "demo", "Use this for another task", body="Second")
        _, raw, _ = self.invoke(["doctor", "--scope", "all", "--hygiene", "--json"])
        finding = next(f for f in json.loads(raw)["hygiene"]["findings"] if f["category"] == "divergent-name")
        self.assertIn("update preview", finding["recommendation"])
        self.assertIn("Sync map", finding["recommendation"])

    @unittest.skipUnless(os.name == "posix", "POSIX permission remedy")
    def test_sticky_shared_root_never_gets_a_chmod_recommendation(self):
        from skillsmgr.path_safety import trusted_root

        shared = self.root / "shared"
        shared.mkdir()
        shared.chmod(0o1777)
        with self.assertRaises(ValueError) as error:
            trusted_root(shared)
        self.assertNotIn("chmod", str(error.exception))

    @unittest.skipUnless(os.name == "posix", "POSIX paths and permissions")
    def test_permission_remedy_never_prints_a_hostile_path_as_terminal_controls(self):
        base = self.root / "unsafe\n\x1b[31m"
        base.mkdir()
        base.chmod(0o775)
        code, text, err = self.invoke(["--data-dir", str(base), "list"])
        self.assertEqual((code, text), (1, ""))
        self.assertNotIn("\x1b", err)
        self.assertEqual(len(err.splitlines()), 1)
        self.assertNotIn("run: chmod", err)
        self.assertIn("printable path", err)

    def test_unreadable_scope_reason_uses_a_short_home_path_in_text(self):
        from skillsmgr import doctor

        root = self.home / ".claude/skills"
        root.mkdir(parents=True)
        real_scandir = doctor.os.scandir
        def blocked(path):
            if Path(path) == root:
                raise PermissionError(13, "Permission denied", str(root))
            return real_scandir(path)
        with patch.object(doctor.os, "scandir", side_effect=blocked):
            code, text, err = self.invoke(["doctor", "--scope", "claude-code"])
        self.assertEqual((code, err), (1, ""))
        self.assertNotIn(str(self.home), text)
        self.assertIn("~/.claude/skills", text)

    def test_name_only_candidates_are_only_shown_near_a_known_budget(self):
        for chars, budget, expected in ((42, 40000, ""), (35999, 40000, ""),
                                        (36000, 40000, "1 name-only candidate"),
                                        (40001, 40000, "1 name-only candidate"),
                                        (50000, 0, "")):
            with self.subTest(chars=chars, budget=budget):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    cli_handlers._render_claude_listing_text({
                        "listing_chars": chars, "status": "unknown" if not budget else "within_budget",
                        "budget": {"budget_chars_estimate": budget},
                        "name_only_candidates": {"total": 1}})
                if expected:
                    self.assertIn(expected, out.getvalue())
                    self.assertNotIn("1 name-only candidates", out.getvalue())
                else:
                    self.assertNotIn("name-only candidate", out.getvalue())


if __name__ == "__main__":
    unittest.main()
