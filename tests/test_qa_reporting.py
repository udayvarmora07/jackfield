"""Developer QA summaries keep failed requests actionable and fail on bad input."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.qa import summarize


class TestQASummary(unittest.TestCase):
    def summarize(self, *reports):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["summarize", *map(str, reports)]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            return summarize.main(), output.getvalue(), errors.getvalue()

    def test_reports_the_failing_keploy_or_hurl_feature_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "reports.xml"
            output.write_text(
                '<testsuites><testsuite><testcase name="library.hurl"/>'
                '<testcase classname="skill-recovery" name="replay-toggle">'
                '<failure message="unexpected status">full report</failure>'
                '</testcase></testsuite></testsuites>', encoding="utf-8",
            )
            code, text, errors = self.summarize(output)
        self.assertEqual(code, 1)
        self.assertIn("skill-recovery / replay-toggle: unexpected status", text)
        self.assertIn("2 test cases, 1 failed", text)
        self.assertEqual(errors, "")

    def test_reports_hurl_assertion_values_after_the_source_excerpt(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "junit.xml"
            output.write_text(
                '<testsuites><testsuite><testcase name="recovery.hurl"><failure>'
                'Assert failure\n  --&gt; recovery.hurl:35:0\n   |\n'
                '35 | jsonpath "$[0].name" == "expected"\n'
                '   | actual:   string &lt;observed&gt;\n'
                '   | expected: string &lt;expected&gt;\n'
                '</failure></testcase></testsuite></testsuites>', encoding="utf-8",
            )
            code, text, errors = self.summarize(output)
        self.assertEqual(code, 1)
        self.assertIn("recovery.hurl: Assert failure --> recovery.hurl:35:0", text)
        self.assertIn("actual:   string <observed> expected: string <expected>", text)
        self.assertEqual(errors, "")

    def test_keploy_output_can_include_its_cgroup_warning_before_xml(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<testsuites><testsuite><testcase name="list-library"/></testsuite></testsuites>')
        warning = ('🐰 Keploy: timestamp \t\x1b[33mWARN\x1b[0m\t'
                   'cgroup v2 (unified hierarchy) not detected; details.\n')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "keploy.xml"
            output.write_text(warning + xml, encoding="utf-8")
            self.assertEqual(self.summarize(output)[0], 1)
            code, text, errors = self.summarize("--keploy", output)
            self.assertEqual(code, 0)
            self.assertIn("1 test cases, 0 failed", text)
            self.assertEqual(errors, "")
            for content in (warning + "unknown preamble\n" + xml, "unrelated warning\n" + xml):
                with self.subTest(content=content):
                    output.write_text(content, encoding="utf-8")
                    self.assertEqual(self.summarize("--keploy", output)[0], 1)

    def test_empty_invalid_and_declared_xml_reports_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "reports.xml"
            for content in ('<testsuites/>', 'not XML', '<!DOCTYPE testsuite><testsuite/>'):
                with self.subTest(content=content):
                    output.write_text(content, encoding="utf-8")
                    code, text, errors = self.summarize(output)
                    self.assertEqual(code, 1)
                    self.assertEqual(text, "")
                    self.assertIn("reports.xml:", errors)
