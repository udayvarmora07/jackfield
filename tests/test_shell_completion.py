"""Static completion must match the actual parser and never execute input."""
import argparse
import contextlib
import io
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from skillsmgr.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skillsmgr" / "completions"


def grammar(parser, path=""):
    candidates, values = [], []
    for action in parser._actions:
        if action.help == argparse.SUPPRESS:
            continue
        candidates.extend(action.option_strings)
        if action.option_strings and action.nargs != 0:
            values.extend(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            candidates.extend(action.choices)
    yield path, set(candidates), set(values)
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                yield from grammar(child, f"{path}/{name}" if path else name)


class ShellCompletionTests(unittest.TestCase):
    def test_both_static_grammars_match_all_parser_paths(self):
        expected = {path: (words, values) for path, words, values in grammar(build_parser())}
        for filename in ("skills-mgr.bash", "_skills-mgr"):
            text = (SCRIPTS / filename).read_text()
            rows = re.findall(r"^        '([^']*)'\) candidates='([^']*)'; value_options='([^']*)' ;;$", text, re.M)
            actual = {path: (set(words.split()), set(values.split())) for path, words, values in rows}
            self.assertEqual(len(rows), len(actual), filename)
            self.assertEqual(actual, expected, filename)

    def test_parser_enables_supported_suggestions_without_dispatch(self):
        parser = build_parser()
        def inspect(p):
            if hasattr(p, "suggest_on_error"):
                self.assertTrue(p.suggest_on_error)
            for action in p._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for sub in action.choices.values():
                        inspect(sub)
        inspect(parser)
        for args in (["lst"], ["trash", "lst"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                parser.parse_args(args)
            self.assertEqual(exc.exception.code, 2)

    def test_supported_suggestions_are_in_root_and_nested_errors(self):
        parser = build_parser()
        if not hasattr(parser, "suggest_on_error"):
            self.skipTest("argparse suggestions unavailable")
        for args in (["lis"], ["trash", "lis"]):
            error = io.StringIO()
            with self.subTest(args=args), contextlib.redirect_stderr(error), self.assertRaises(SystemExit) as exc:
                parser.parse_args(args)
            self.assertEqual(exc.exception.code, 2)
            self.assertIn("maybe you meant 'list'", error.getvalue())

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_bash_real_completion_and_untrusted_word(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "executed"
            code = r'''source "$1"
COMP_WORDS=(skills-mgr trash ""); COMP_CWORD=2; _skills_mgr_complete
printf '%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(skills-mgr list --scope ""); COMP_CWORD=3; _skills_mgr_complete
printf 'scope:%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(skills-mgr install --scope ""); COMP_CWORD=3; _skills_mgr_complete
printf 'install:%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(skills-mgr sync --to ""); COMP_CWORD=3; _skills_mgr_complete
printf 'target:%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(skills-mgr install --runner ""); COMP_CWORD=3; _skills_mgr_complete
printf 'runner:%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(skills-mgr install --view ""); COMP_CWORD=3; _skills_mgr_complete
printf 'view:%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(skills-mgr "$(touch "$2")"); COMP_CWORD=1; _skills_mgr_complete
'''
            # Build the malicious word without the shell parsing it as syntax.
            code = code.replace('"$(touch "$2")"', "'$(touch ' \"$2\" ')'")
            result = subprocess.run(["bash", "-c", code, "bash", str(SCRIPTS / "skills-mgr.bash"), str(marker)], capture_output=True, text=True, check=True)
            self.assertIn("restore", result.stdout.splitlines())
            self.assertIn("scope:agents", result.stdout.splitlines())
            lines = result.stdout.splitlines()
            self.assertEqual({line for line in lines if line.startswith("install:")}, {"install:global", "install:project"})
            self.assertNotIn("target:all", lines)
            self.assertEqual({line for line in lines if line.startswith("runner:")}, {"runner:npx", "runner:pnpm", "runner:yarn", "runner:bunx"})
            self.assertEqual({line for line in lines if line.startswith("view:")}, {"view:all-time", "view:trending", "view:hot"})
            self.assertFalse(marker.exists())

    @unittest.skipUnless(shutil.which("zsh"), "zsh unavailable")
    def test_zsh_real_completion_and_untrusted_word(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "executed"
            code = r'''set -e
expected_shell_path=$PATH
compdef() { :; }
compadd() { [[ $PATH == "$expected_shell_path" ]]; shift; printf '%s\n' "$@"; }
source "$1"
words=(skills-mgr trash ''); CURRENT=3; _skills_mgr_complete
words=(skills-mgr list --scope ''); CURRENT=4; _skills_mgr_complete
words=(skills-mgr '$(touch '"$2"')'); CURRENT=2; _skills_mgr_complete
'''
            result = subprocess.run(["zsh", "-c", code, "zsh", str(SCRIPTS / "_skills-mgr"), str(marker)], capture_output=True, text=True, check=True)
            self.assertIn("restore", result.stdout.splitlines())
            self.assertIn("agents", result.stdout.splitlines())
            self.assertFalse(marker.exists())

    def test_script_members_are_nonempty(self):
        for name in ("skills-mgr.bash", "_skills-mgr"):
            self.assertGreater((SCRIPTS / name).stat().st_size, 0)
            self.assertNotRegex((SCRIPTS / name).read_text(), r"\blocal\s+path=")
