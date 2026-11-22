"""Round 2: Codex's skill-listing budget and OpenCode's tool-output truncation.

openai/codex#19679: Codex reserves 2% of the model's context window for the
skill listing (8,000 characters when the window is unknown) and truncates
descriptions beyond it.  Each listed line is ``- name: description (file:
path)``, descriptions are capped at 1,024 characters, and a line costs
``ceil(bytes / 4)`` tokens (codex-rs/ext/skills/src/render.rs).

sst/opencode#62718: OpenCode keeps only the first 2,000 lines / 50 KiB of a
tool result, so the tail of a larger SKILL.md never reaches the model.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import hygiene, loader

DOC = "---\nname: {n}\ndescription: {d}\n---\n{b}\n"


class _Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name).resolve()
        self.root = self.home / ".agents" / "skills"
        self.root.mkdir(parents=True)
        env = patch.dict(os.environ, {"CODEX_HOME": ""})
        env.start()
        self.addCleanup(env.stop)

    def skill(self, name: str, description: str, body: str = "Body") -> Path:
        folder = self.root / name
        folder.mkdir()
        (folder / "SKILL.md").write_text(DOC.format(n=name, d=description, b=body), encoding="utf-8")
        return folder

    def report(self, scope: str = "agents", window: str = "gpt-5"):
        records = loader.scan_dir(self.root, annotate_paths=True)
        for record in records:
            record["scope"] = scope
        return hygiene.hygiene_report(records, scope=scope, home=self.home, window=window)

    def findings(self, report, category):
        return [f for f in report["findings"] if f["category"] == category]


class CodexListingTests(_Fixture):
    def test_over_budget_library_gets_estimate_and_one_finding(self):
        for i in range(40):
            self.skill(f"skill-{i:02d}", "Use when " + "x" * 990)
        report = self.report()
        section = report["codex_listing"]
        self.assertEqual(section["listed_skills"], 40)
        self.assertEqual(section["budget"]["budget_tokens"], 8000)  # 2% of 400,000
        self.assertGreater(section["listing_tokens_estimate"], 8000)
        self.assertEqual(section["status"], "over_budget_estimate")
        self.assertEqual(section["tokens_to_free"], section["listing_tokens_estimate"] - 8000)
        found = self.findings(report, "codex-listing-budget")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "info")

    def test_line_cost_follows_codex_render_rule(self):
        folder = self.skill("one", "Use when testing.")
        report = self.report()
        line = f"- one: Use when testing. (file: {folder / 'SKILL.md'})\n"
        expected = -(-len(line.encode("utf-8")) // 4)
        self.assertEqual(report["codex_listing"]["listing_tokens_estimate"], expected)
        self.assertEqual(report["codex_listing"]["status"], "within_budget")
        self.assertFalse(self.findings(report, "codex-listing-budget"))

    def test_long_descriptions_are_capped_at_1024_characters(self):
        self.skill("long", "Use when " + "y" * 3000)
        section = self.report()["codex_listing"]
        self.assertEqual(section["truncated_descriptions"]["count"], 1)
        self.assertLess(section["listing_tokens_estimate"], 400)
        entry = section["entries"][0]
        # Codex keeps 1,021 characters and appends "..." (1,024 in all).
        self.assertEqual((entry["description_chars"], entry["delivered_description_chars"], entry["cut_chars"]),
                         (3009, 1021, 3009 - 1021))
        self.assertEqual(entry["tokens"], section["listing_tokens_estimate"])

    def test_entries_rank_the_largest_cuts_first(self):
        for i in range(105):
            self.skill(f"a{i:03d}", "Use when short.")
        self.skill("zz-long", "Use when " + "z" * 2000)
        entries = self.report()["codex_listing"]["entries"]
        self.assertEqual(len(entries), 100)
        self.assertEqual(entries[0]["name"], "zz-long")

    def test_short_descriptions_are_delivered_whole(self):
        self.skill("short", "Use when testing.")
        entry = self.report()["codex_listing"]["entries"][0]
        self.assertEqual((entry["cut_chars"], entry["over_cap"]), (0, False))
        self.assertEqual(entry["delivered_description_chars"], len("Use when testing."))

    def test_disabled_and_config_disabled_skills_are_not_listed(self):
        self.skill("kept", "Use when kept.")
        off = self.skill("filed-off", "Use when off.")
        (off / "SKILL.md").rename(off / "SKILL.md.disabled")
        self.skill("config-off", "Use when config off.")
        (self.home / ".codex").mkdir()
        (self.home / ".codex" / "config.toml").write_text(
            '[[skills.config]]\nname = "config-off"\nenabled = false\n', encoding="utf-8")
        section = self.report()["codex_listing"]
        self.assertEqual(section["listed_skills"], 1)
        self.assertEqual(section["excluded"]["disabled"], 1)
        self.assertEqual(section["excluded"]["config_disabled"], 1)

    def test_non_gpt_window_falls_back_to_a_stated_codex_window(self):
        self.skill("one", "Use when testing.")
        budget = self.report(window="claude")["codex_listing"]["budget"]
        self.assertEqual(budget["window"], "gpt-5.6")
        self.assertEqual(budget["budget_tokens"], 21000)
        self.assertIn("assumed", budget["basis"])

    def test_scopes_codex_does_not_read_observe_nothing(self):
        self.skill("one", "Use when testing.")
        section = self.report(scope="claude-code")["codex_listing"]
        self.assertEqual(section["instances_observed"], 0)
        self.assertEqual(section["status"], "no_instances")


class OpenCodeTruncationTests(_Fixture):
    def test_large_document_in_a_root_opencode_reads_is_flagged(self):
        self.skill("big", "Use when big.", body="line\n" * 2100)
        self.skill("small", "Use when small.")
        found = self.findings(self.report(), "opencode-output-truncation")
        self.assertEqual([f["instances"][0]["name"] for f in found], ["big"])
        self.assertEqual(found[0]["severity"], "warning")
        self.assertGreater(found[0]["evidence"]["document_lines"], 2000)

    def test_bytes_over_50_kib_are_flagged_even_with_few_lines(self):
        self.skill("wide", "Use when wide.", body="z" * (50 * 1024 + 10))
        found = self.findings(self.report(), "opencode-output-truncation")
        self.assertEqual(len(found), 1)
        self.assertGreater(found[0]["evidence"]["document_bytes"], 50 * 1024)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "needs FIFOs")
    def test_a_fifo_document_is_never_opened_for_a_blocking_read(self):
        from skillsmgr.hygiene import _document_size
        fifo = self.home / "pipe"
        os.mkfifo(fifo)
        self.assertIsNone(_document_size(fifo))

    def test_a_scope_opencode_does_not_read_is_not_flagged(self):
        self.skill("big", "Use when big.", body="line\n" * 2100)
        self.assertFalse(self.findings(self.report(scope="gemini"), "opencode-output-truncation"))


class CodexListingTextTests(unittest.TestCase):
    def test_terminal_line_states_tokens_budget_and_is_silent_without_instances(self):
        import contextlib
        import io

        from skillsmgr import cli_handlers
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_handlers._render_codex_listing_text({"status": "over_budget_estimate", "listed_skills": 40,
                                                     "listing_tokens_estimate": 10600,
                                                     "budget": {"budget_tokens": 8000}})
            cli_handlers._render_codex_listing_text({"status": "no_instances"})
        self.assertEqual(out.getvalue().count("\n"), 1)
        self.assertIn("~10,600 tokens vs 8,000 budget", out.getvalue())

    def test_cut_descriptions_are_listed_largest_first_and_bounded(self):
        import contextlib
        import io

        from skillsmgr import cli_handlers
        entries = [{"name": f"s{i}", "description_chars": 2000, "cut_chars": 100 * i} for i in range(8)]
        entries.append({"name": "evil\x1b[2J", "description_chars": 3000, "cut_chars": 2000})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_handlers._render_codex_listing_text({"status": "within_budget", "listed_skills": 9,
                                                     "listing_tokens_estimate": 10, "entries": entries,
                                                     "budget": {"budget_tokens": 8000}})
        lines = out.getvalue().splitlines()
        cuts = [line for line in lines if line.startswith("    cut: ")]
        self.assertEqual(len(cuts), 6)
        self.assertIn("loses 2,000 of 3,000", cuts[0])
        self.assertNotIn("\x1b", out.getvalue())
        self.assertIn("s7 loses 700", cuts[1])
        self.assertEqual(cuts[-1], "    cut: 3 more (see --json)")


if __name__ == "__main__":
    unittest.main()
