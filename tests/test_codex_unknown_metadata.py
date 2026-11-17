"""Conservative Codex listing estimates when invocation metadata is unread."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import hygiene, loader

DOC = "---\nname: {name}\ndescription: {description}\n---\nBody\n"


class CodexUnknownMetadataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name).resolve()
        self.root = self.home / ".agents" / "skills"
        self.root.mkdir(parents=True)
        env = patch.dict(os.environ, {"CODEX_HOME": ""})
        env.start()
        self.addCleanup(env.stop)

    def skill(self, name: str, description: str = "Use when testing.") -> Path:
        folder = self.root / name
        folder.mkdir()
        (folder / "SKILL.md").write_text(
            DOC.format(name=name, description=description), encoding="utf-8")
        return folder

    @staticmethod
    def metadata(folder: Path, contents: str) -> Path:
        agents = folder / "agents"
        agents.mkdir(exist_ok=True)
        path = agents / "openai.yaml"
        path.write_text(contents, encoding="utf-8")
        return path

    def report(self):
        records = loader.scan_dir(self.root, annotate_paths=True)
        for record in records:
            record["scope"] = "agents"
        return hygiene.hygiene_report(records, scope="agents", home=self.home, window="gpt-5")

    def test_linked_fifo_large_bad_encoding_and_unrecognized_are_unknown(self):
        linked = self.skill("linked")
        linked_target = self.home / "elsewhere.yaml"
        linked_target.write_text("policy:\n  allow_implicit_invocation: false\n", encoding="utf-8")
        (linked / "agents").mkdir()
        (linked / "agents" / "openai.yaml").symlink_to(linked_target)

        fifo = self.skill("fifo")
        (fifo / "agents").mkdir()
        if hasattr(os, "mkfifo"):
            os.mkfifo(fifo / "agents" / "openai.yaml")
        else:
            self.skipTest("needs POSIX FIFOs")

        large = self.skill("large")
        self.metadata(large, "policy:\n  allow_implicit_invocation: true\n" + "#" * (70 * 1024))
        bad_encoding = self.skill("bad-encoding")
        bad = self.metadata(bad_encoding, "")
        bad.write_bytes(b"policy:\n  allow_implicit_invocation: \xff\n")
        unrecognized = self.skill("unrecognized")
        self.metadata(unrecognized, 'policy:\n  allow_implicit_invocation: "false"\n')

        section = self.report()["codex_listing"]
        unknown = section["unknown_metadata"]
        self.assertEqual(unknown["total"], 5)
        self.assertEqual(unknown["reasons"], {
            "linked": 1, "non_regular": 1, "oversized": 1, "undecodable": 1,
            "unrecognized_value": 1, "unreadable": 0})
        self.assertEqual(section["excluded"]["unknown_metadata"], 5)
        self.assertEqual(section["listed_skills"], 0)
        self.assertEqual(section["instances_observed"], 5)
        self.assertEqual(section["status"], "unknown")
        self.assertIsNone(section["tokens_to_free"])
        self.assertFalse(any(f["category"] == "codex-listing-budget"
                             for f in self.report()["findings"]))

    def test_missing_true_and_false_metadata_keep_known_behavior_and_accounting(self):
        self.skill("missing")
        true = self.skill("true")
        self.metadata(true, "policy:\n  allow_implicit_invocation: true\n")
        false = self.skill("false")
        self.metadata(false, "policy:\n  allow_implicit_invocation: false\n")

        section = self.report()["codex_listing"]
        self.assertEqual(section["listed_skills"], 2)
        self.assertEqual(section["excluded"]["explicit_only"], 1)
        self.assertEqual(section["unknown_metadata"]["total"], 0)
        self.assertEqual(section["unknown_metadata"]["missing_metadata_default_listed"], 1)
        self.assertEqual(section["instances_observed"], 3)
        self.assertEqual(section["status"], "within_budget")

    def test_unknown_names_are_bounded_and_invalid_settings_stay_separate(self):
        for index in range(55):
            folder = self.skill(f"unknown-{index:02d}")
            self.metadata(folder, 'policy: {allow_implicit_invocation: "maybe"}\n')
        config = self.home / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_text('[skills]\nmax_context_tokens = "bad"\n', encoding="utf-8")

        section = self.report()["codex_listing"]
        self.assertEqual(section["unknown_metadata"]["total"], 55)
        self.assertEqual(len(section["unknown_metadata"]["names"]), 50)
        self.assertTrue(all(len(name) <= 128 for name in section["unknown_metadata"]["names"]))
        self.assertEqual(section["unknown_metadata"]["omitted"], 5)
        self.assertEqual(section["unknown_metadata"]["reasons"]["unrecognized_value"], 55)
        self.assertEqual(section["budget"]["config_status"], "invalid")
        self.assertIsNone(section["budget"]["budget_tokens"])
        self.assertIsNone(section["tokens_to_free"])

    def test_unknown_metadata_contents_are_never_returned(self):
        folder = self.skill("secret-name")
        self.metadata(folder, "private: do not expose this text\npolicy: {allow_implicit_invocation: maybe}\n")
        section = self.report()["codex_listing"]
        rendered = repr(section)
        self.assertNotIn("do not expose", rendered)
        self.assertEqual(section["unknown_metadata"]["names"], ["secret-name"])


if __name__ == "__main__":
    unittest.main()
