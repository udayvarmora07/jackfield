"""Contracts for the Skills Manager -> Jackfield rename (2026-11-26).

The public names changed; existing data and settings must keep working:

- a library in ``<base>/skills-manager`` is used in place and never moved;
- ``JACKFIELD_*`` variables win, the ``SKILLS_MANAGER_*`` ones are still read;
- ``--data-dir`` applies to one CLI command and does not leak into the process.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from skillsmgr import ai, cli, paths
from skillsmgr.registry import RegistryClient


class _Env(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("JACKFIELD_DATA", "SKILLS_MANAGER_DATA", "XDG_DATA_HOME"):
            os.environ.pop(name, None)


class DataRootSelectionTests(_Env):
    def test_a_fresh_base_gets_a_jackfield_root(self):
        os.environ["JACKFIELD_DATA"] = str(self.base)
        self.assertEqual(paths.data_dir(), self.base / "jackfield")
        self.assertFalse((self.base / "skills-manager").exists())

    def test_an_existing_skills_manager_library_is_used_in_place(self):
        legacy = self.base / "skills-manager"
        (legacy / "skills" / "demo").mkdir(parents=True, mode=0o700)
        legacy.chmod(0o700)
        (legacy / "skills").chmod(0o700)
        os.environ["SKILLS_MANAGER_DATA"] = str(self.base)
        self.assertEqual(paths.data_dir(), legacy)
        self.assertFalse((self.base / "jackfield").exists(), "nothing may be created beside the old library")
        self.assertTrue((legacy / "skills" / "demo").is_dir(), "the old library must not move")

    def test_a_jackfield_root_wins_when_both_exist(self):
        for name in ("skills-manager", "jackfield"):
            (self.base / name).mkdir(mode=0o700)
        os.environ["JACKFIELD_DATA"] = str(self.base)
        self.assertEqual(paths.data_dir(), self.base / "jackfield")

    def test_the_new_variable_wins_and_a_blank_one_falls_back(self):
        new, old = self.base / "new", self.base / "old"
        new.mkdir(mode=0o700)
        old.mkdir(mode=0o700)
        os.environ["JACKFIELD_DATA"] = str(new)
        os.environ["SKILLS_MANAGER_DATA"] = str(old)
        self.assertEqual(paths.data_dir(), new / "jackfield")
        os.environ["JACKFIELD_DATA"] = "  "
        self.assertEqual(paths.data_dir(), old / "jackfield")

    @unittest.skipUnless(os.name == "posix", "symlinks and permissions are POSIX here")
    def test_a_symlinked_legacy_root_is_validated_as_before_the_rename(self):
        safe = self.base / "moved-library"
        safe.mkdir(mode=0o700)
        (self.base / "skills-manager").symlink_to(safe, target_is_directory=True)
        os.environ["JACKFIELD_DATA"] = str(self.base)
        self.assertEqual(paths.data_dir(), safe.resolve())
        self.assertFalse((self.base / "jackfield").exists())
        safe.chmod(0o777)
        self.addCleanup(safe.chmod, 0o700)
        with self.assertRaises(ValueError):
            paths.data_dir()

    @unittest.skipUnless(os.name == "posix", "POSIX permission contract")
    def test_the_unsafe_root_hint_points_at_a_fresh_private_root(self):
        legacy = self.base / "skills-manager"
        legacy.mkdir(mode=0o700)
        (legacy / "not-ours.txt").write_text("x", encoding="utf-8")
        legacy.chmod(0o770)
        os.environ["JACKFIELD_DATA"] = str(self.base)
        with self.assertRaises(ValueError) as ctx:
            paths.data_dir()
        # Following the hint must not lead back to the same unsafe directory.
        self.assertIn("export JACKFIELD_DATA=$HOME/.local/share/jackfield", str(ctx.exception))


class CliDataDirScopeTests(_Env):
    def test_data_dir_does_not_leak_past_the_command(self):
        os.environ["JACKFIELD_DATA"] = str(self.base / "outer")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["--data-dir", str(self.base / "inner"), "list"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(os.environ.get("JACKFIELD_DATA"), str(self.base / "outer"))
        os.environ.pop("JACKFIELD_DATA")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            cli.main(["--data-dir", str(self.base / "inner"), "list"])
        self.assertNotIn("JACKFIELD_DATA", os.environ)

    def test_both_command_names_are_the_same_parser(self):
        self.assertEqual(cli.build_parser().prog, "jackfield")


class LegacyVariableTests(_Env):
    DEFAULT = {"base_url": "https://api.openai.com/v1"}
    CUSTOM = {"base_url": "https://models.example.test/v1"}

    def _allowed(self) -> bool:
        return ai._env_key_allowed(self.DEFAULT, self.CUSTOM)

    def test_ai_endpoint_opt_in_reads_both_names_and_honours_an_explicit_blank(self):
        self.assertFalse(self._allowed(), "no opt-in, no key to a custom endpoint")
        os.environ[ai.LEGACY_ENV_KEY_ENDPOINT_VAR] = self.CUSTOM["base_url"]
        self.assertTrue(self._allowed(), "the pre-rename variable is still read")
        os.environ[ai.ENV_KEY_ENDPOINT_VAR] = ""
        self.assertFalse(self._allowed(), "an explicitly blank new variable switches the opt-in off")
        os.environ[ai.ENV_KEY_ENDPOINT_VAR] = "https://other.example/v1"
        self.assertFalse(self._allowed(), "the new variable wins over the old one")

    def test_registry_token_falls_back_to_the_pre_rename_name(self):
        client = RegistryClient(self.base)
        os.environ.pop("VERCEL_OIDC_TOKEN", None)
        os.environ.pop("JACKFIELD_REGISTRY_TOKEN", None)
        os.environ["SKILLS_MANAGER_REGISTRY_TOKEN"] = "legacy-token"
        self.assertEqual(client._credential(), "legacy-token")
        os.environ["JACKFIELD_REGISTRY_TOKEN"] = "new-token"
        self.assertEqual(client._credential(), "new-token")


if __name__ == "__main__":
    unittest.main()
