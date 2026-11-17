"""Informational authoring hints stay bounded and inspect supplied text only."""

from __future__ import annotations

import copy
import subprocess
import sys
import unittest

from skillsmgr.authoring import _authoring_hint_findings
from skillsmgr.hygiene import hygiene_report


class AuthoringHintTests(unittest.TestCase):
    def test_reports_missing_example_validation_and_deep_reference(self):
        rows = [{
            "name": "thin-guide",
            "scope": "global",
            "body": "Use the local tool. See [details](references/setup/linux.md).",
        }]
        findings = _authoring_hint_findings(rows)
        self.assertEqual({item["evidence"]["hint"] for item in findings}, {
            "missing-example", "missing-validation-step", "deep-reference-nesting",
        })
        self.assertTrue(all(item["category"] == "authoring-smell" for item in findings))
        self.assertTrue(all(item["severity"] == "info" for item in findings))
        self.assertTrue(all(item["automatic_action"] is False for item in findings))

    def test_recognizes_examples_checks_and_one_level_references(self):
        rows = [{
            "name": "complete",
            "scope": "global",
            "body": """# Example
```sh
tool --help
```
Verify the output with `tool check`.
See [details](references/setup.md).
""",
        }]
        self.assertEqual(_authoring_hint_findings(rows), [])

    def test_common_e_g_abbreviation_counts_as_an_example(self):
        rows = [{"name": "example", "scope": "global", "body": "Use e.g., `tool --help` to inspect the command."}]
        hints = {item["evidence"]["hint"] for item in _authoring_hint_findings(rows)}
        self.assertNotIn("missing-example", hints)

    def test_reference_parent_segments_are_normalized_lexically(self):
        rows = [{
            "name": "shallow",
            "scope": "global",
            "body": "See [details](references/setup/../details.md).",
        }]
        hints = {item["evidence"]["hint"] for item in _authoring_hint_findings(rows)}
        self.assertNotIn("deep-reference-nesting", hints)

    def test_many_blank_lines_do_not_make_example_detection_pathological(self):
        # The watchdog catches regexes whose leading \s* rescans the remaining
        # newline run from every line start.
        code = (
            "from skillsmgr.authoring import _hint_names; "
            "_hint_names('\\n' * 180000 + 'ordinary instructions')"
        )
        subprocess.run([sys.executable, "-c", code], check=True, timeout=5)

    def test_skips_empty_nontext_and_malformed_bodies(self):
        rows = [
            {"name": "empty", "body": " \n\t"},
            {"name": "not-text", "body": object()},
            {"name": "broken", "body": "Do the thing", "malformed": True},
            {"name": "missing", "malformed": True},
        ]
        self.assertEqual(_authoring_hint_findings(rows), [])

    def test_group_cap_reports_total_and_omitted_instances(self):
        rows = [
            {"name": "same", "scope": "global", "path": f"/skills/{i:04}/SKILL.md", "body": "Do the work."}
            for i in range(600)
        ]
        findings = _authoring_hint_findings(rows)
        self.assertEqual(len(findings), 2)
        for finding in findings:
            self.assertEqual(finding["evidence"]["instances_total"], 600)
            self.assertEqual(finding["evidence"]["instances_omitted"], 500)
            self.assertTrue(finding["evidence"]["instances_truncated"])
            self.assertEqual(finding["evidence"]["instance_count_basis"], "observed analyzed instances")
            self.assertEqual(len(finding["instances"]), 100)

    def test_is_deterministic_order_independent_and_does_not_mutate_records(self):
        rows = [
            {"name": "z", "scope": "global", "body": "Do it.", "path": "/missing/z"},
            {"name": "a", "scope": "global", "body": "Do that.", "path": "/missing/a"},
        ]
        before = copy.deepcopy(rows)
        first = _authoring_hint_findings(rows)
        second = _authoring_hint_findings(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual(rows, before)

    def test_analysis_ignores_paths_and_symlink_targets(self):
        rows = [{
            "name": "local",
            "scope": "global",
            "body": "Use the tool.",
            "path": "/some/symlink/SKILL.md",
            "physical_path": "/elsewhere/target/SKILL.md",
        }]
        finding = _authoring_hint_findings(rows)[0]
        changed = dict(rows[0], path="https://example.invalid/anything", physical_path="/different")
        changed_findings = _authoring_hint_findings([changed])
        self.assertEqual(
            {item["evidence"]["hint"] for item in changed_findings},
            {item["evidence"]["hint"] for item in _authoring_hint_findings(rows)},
        )
        self.assertNotEqual(finding["instances"][0]["physical_path"], changed_findings[0]["instances"][0]["physical_path"])

    def test_recursive_same_name_copies_remain_distinguishable(self):
        rows = [
            {"name": "same", "scope": "global", "path": "/skills/a/SKILL.md", "body": "Do it."},
            {"name": "same", "scope": "global", "path": "/skills/nested/b/SKILL.md", "body": "Do it."},
        ]
        findings = _authoring_hint_findings(rows)
        example = next(item for item in findings if item["evidence"]["hint"] == "missing-example")
        self.assertEqual(example["evidence"]["instances_total"], 2)
        self.assertEqual(
            {instance["physical_path"] for instance in example["instances"]},
            {"/skills/a/SKILL.md", "/skills/nested/b/SKILL.md"},
        )
        self.assertEqual(len({item["id"] for item in findings}), len(findings))

    def test_known_path_and_scope_label_are_preserved(self):
        row = {"name": "local", "scope": "agents", "scope_label": "Agent skills", "body": "Do it.", "path": "/skills/local/SKILL.md"}
        finding = next(item for item in _authoring_hint_findings([row]) if item["evidence"]["hint"] == "missing-example")
        self.assertEqual(finding["instances"][0]["scope_label"], "Agent skills")
        self.assertEqual(finding["instances"][0]["physical_path"], "/skills/local/SKILL.md")

    def test_hygiene_includes_hints_as_info_without_changing_validation(self):
        row = {
            "name": "thin", "scope": "global", "description": "Use this skill when checking a task.",
            "body": "Use this skill.", "validation": {"issues": []},
        }
        report = hygiene_report([row], scope="global")
        hint = next(item for item in report["findings"] if item["category"] == "authoring-smell")
        self.assertEqual(hint["severity"], "info")
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["warnings"], 0)


if __name__ == "__main__":
    unittest.main()
