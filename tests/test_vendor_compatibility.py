"""Read-only compatibility regressions from the docs/46 primary-source audit."""

import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

from skillsmgr import cli_handlers, effective, native_state
from tests.test_codex_listing_and_size import _Fixture
from tests.test_effective_explain_contracts import ExplainCase, tree_digest


class CursorCompatibilityTests(ExplainCase):
    def test_claude_and_codex_compatibility_copies_are_all_reported_without_a_winner(self):
        copies = {
            self.home_skill(".claude/skills"),
            self.home_skill(".codex/skills"),
            self.project_skill(".claude/skills"),
            self.project_skill(".codex/skills"),
        }
        before = tree_digest(self.base)
        report = self.explain("cursor")
        self.assertEqual(report["resolution"], "undocumented-precedence")
        entry = report["skills"]["deploy"]
        self.assertEqual({c["path"] for c in entry["candidates"]}, {str(p) for p in copies})
        self.assertIsNone(entry["winner"])
        self.assertEqual(tree_digest(self.base), before)

    def test_compatibility_home_paths_remain_redacted_at_the_http_boundary(self):
        self.home_skill(".claude/skills")
        self.home_skill(".codex/skills")
        project = self.project_skill(".codex/skills")
        report = effective.explain("cursor", self.project, allowed_root=self.project)
        self.assertTrue(report["paths_redacted"])
        self.assertNotIn(json.dumps(str(self.home))[1:-1], json.dumps(report))
        self.assertIn(json.dumps(str(project))[1:-1], json.dumps(report))
        self.assertEqual(len(report["skills"]["deploy"]["candidates"]), 3)

    def test_missing_compatibility_folders_are_not_created(self):
        before = tree_digest(self.base)
        report = self.explain("cursor")
        self.assertEqual(report["skills"], {})
        self.assertEqual(tree_digest(self.base), before)


class CodexConfiguredListingTests(_Fixture):
    def config(self, content):
        path = self.home / ".codex" / "config.toml"
        path.parent.mkdir(exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_configured_budget_replaces_two_percent_and_changes_the_warning(self):
        self.skill("one", "Use when testing.")
        config = self.config("[skills]\nmax_context_tokens = 1\n")
        before = config.read_bytes()
        section = self.report()["codex_listing"]
        self.assertEqual(section["budget"]["budget_tokens"], 1)
        self.assertEqual(section["status"], "over_budget_estimate")
        self.assertEqual(section["tokens_to_free"], section["listing_tokens_estimate"] - 1)
        self.assertIn("skills.max_context_tokens", section["budget"]["basis"])
        self.assertEqual(config.read_bytes(), before)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_handlers._render_codex_listing_text(section)
        self.assertIn("1 budget", out.getvalue())
        self.assertNotIn("2% rule", out.getvalue())

    def test_only_configured_budget_is_capped_at_ten_thousand(self):
        self.skill("one", "Use when testing.")
        self.config("[skills]\nmax_context_tokens = 20000\n")
        self.assertEqual(self.report(window="gpt-5.6")["codex_listing"]["budget"]["budget_tokens"], 10000)
        self.config("[skills]\n")
        self.assertEqual(self.report(window="gpt-5.6")["codex_listing"]["budget"]["budget_tokens"], 21000)

    def test_invalid_or_corrupt_config_is_unknown_instead_of_a_default_pass(self):
        self.skill("one", "Use when testing.")
        for content in ("broken [", "skills = false", "[skills]\nmax_context_tokens = 0",
                        "[skills]\nmax_context_tokens = -1", "[skills]\nmax_context_tokens = true",
                        '[skills]\nmax_context_tokens = "12"', "[skills]\nmax_context_tokens = 1.5",
                        f"[skills]\nmax_context_tokens = {2 * sys.maxsize + 2}"):
            with self.subTest(content=content):
                self.config(content)
                report = self.report()
                section = report["codex_listing"]
                self.assertEqual(section["status"], "unknown")
                self.assertIsNone(section["budget"]["budget_tokens"])
                self.assertIsNone(section["tokens_to_free"])
                self.assertFalse(self.findings(report, "codex-listing-budget"))
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    cli_handlers._render_codex_listing_text(section)
                self.assertIn("budget unknown", out.getvalue())
                self.assertNotIn("0 budget", out.getvalue())

    def test_codex_home_override_is_used_without_exposing_other_config_values(self):
        self.skill("one", "Use when testing.")
        self.config("[skills]\nmax_context_tokens = 10\n")
        other = self.home / "other-config"
        other.mkdir()
        (other / "config.toml").write_text('private = "do-not-expose"\n[skills]\nmax_context_tokens = 123\n')
        with patch.dict(os.environ, {"CODEX_HOME": str(other)}):
            section = self.report()["codex_listing"]
        self.assertEqual(section["budget"]["budget_tokens"], 123)
        self.assertNotIn("do-not-expose", json.dumps(section))

    def test_missing_config_keeps_default_and_does_not_create_a_directory(self):
        self.skill("one", "Use when testing.")
        self.assertEqual(self.report()["codex_listing"]["budget"]["budget_tokens"], 8000)
        self.assertFalse((self.home / ".codex").exists())

    def test_oversized_config_leaves_the_budget_unknown(self):
        self.skill("one", "Use when testing.")
        self.config("#" * (native_state.MAX_CONFIG_BYTES + 1))
        section = self.report()["codex_listing"]
        self.assertEqual(section["status"], "unknown")
        self.assertEqual(section["budget"]["config_status"], "unavailable")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "needs FIFOs")
    def test_fifo_config_is_not_opened_for_a_blocking_read(self):
        self.skill("one", "Use when testing.")
        path = self.home / ".codex" / "config.toml"
        path.parent.mkdir()
        os.mkfifo(path)
        section = self.report()["codex_listing"]
        self.assertEqual(section["status"], "unknown")
        self.assertIsNone(section["budget"]["budget_tokens"])
