"""Typo hints for CLI commands and library skill names (2026-11-19)."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillsmgr import cli  # noqa: E402


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as exc:  # argparse usage errors
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CommandTypoTests(unittest.TestCase):
    def test_a_mistyped_command_names_the_closest_one(self):
        code, _, err = _run(["lst"])
        self.assertEqual(code, 2)
        self.assertIn("'list'", err.splitlines()[-1])

    def test_a_command_with_no_close_match_gets_no_guess(self):
        code, _, err = _run(["qqqqqqqq"])
        self.assertEqual(code, 2)
        self.assertNotIn("did you mean", err)


class SkillNameHintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # ``--data-dir`` is the base; the CLI keeps its library beneath it.
        self.data = Path(self.tmp.name) / "data"
        code, _, err = _run(["--data-dir", str(self.data), "create", "pdf-tools",
                             "-d", "Use when handling PDF files"])
        self.assertEqual(code, 0, err)
        skills = next(self.data.rglob("pdf-tools")).parent
        # A hostile folder name must never be echoed to the terminal.
        (skills / "pdf-tool\x1b[31m").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_near_miss_suggests_the_library_skill(self):
        code, _, err = _run(["--data-dir", str(self.data), "view", "pdf-tool"])
        self.assertEqual(code, 1)
        self.assertIn("did you mean 'pdf-tools'?", err)
        self.assertNotIn("\x1b", err)

    def test_no_close_name_keeps_the_plain_error(self):
        code, _, err = _run(["--data-dir", str(self.data), "view", "zzzz"])
        self.assertEqual(code, 1)
        self.assertIn("is not installed", err)
        self.assertNotIn("did you mean", err)


if __name__ == "__main__":
    unittest.main()
