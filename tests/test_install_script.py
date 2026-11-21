"""Contracts for the one-command installers (`install.sh`, `install.ps1`).

The shell installer is run for real under `/bin/sh` with a sandboxed PATH:
fake `uv`, `pipx` and `python3` executables record the arguments they were
given, so every branch is exercised offline and nothing touches the network
or the real home directory. A real install from this checkout is done by the
cross-platform CI job (`.github/workflows/ci.yml`, job `xplat`).
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "install.sh"
INSTALL_PS1 = ROOT / "install.ps1"
POWERSHELL = shutil.which(os.environ.get("SKILLSMGR_TEST_POWERSHELL", "pwsh"))

# The only host programs install.sh may rely on besides the fakes.
HOST_TOOLS = (
    "sh", "sed", "dirname", "mkdir", "rmdir", "ln", "readlink", "grep", "id", "rm", "cat", "cmp",
)
# Needed by the fakes below, not by install.sh.
FAKE_TOOLS = ("chmod",)

FAKE_UV = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_LOG"
case "$1 $2" in
    "tool list") cat "$FAKE_STATE/uv-tools" 2>/dev/null ;;
esac
exit 0
"""

FAKE_PIPX = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_LOG"
case "$1" in
    list) cat "$FAKE_STATE/pipx-list" 2>/dev/null ;;
esac
exit 0
"""

# A python3 that is "3.12": answers the version probe, creates a fake venv
# whose pip records its arguments, and publishes a launcher without replacing it.
FAKE_PYTHON = """#!/bin/sh
case "$1" in
    -c) exit 0 ;;
    -I) ln -s "$4" "$5"; exit $? ;;
    -m)
        if [ "$2" = venv ]; then
            mkdir -p "$3/bin"
            printf 'home = fake\\n' > "$3/pyvenv.cfg"
            cat > "$3/bin/python" <<'PY'
#!/bin/sh
printf 'pip %s\\n' "$*" >> "$FAKE_LOG"
case "$*" in *failed-install*) exit 23 ;; esac
dir=$(dirname "$0")
printf '#!/bin/sh\\necho "skills-mgr 9.9.9"\\n' > "$dir/skills-mgr"
chmod +x "$dir/skills-mgr"
PY
            chmod +x "$3/bin/python"
            printf 'venv %s\\n' "$3" >> "$FAKE_LOG"
            exit 0
        fi ;;
esac
exit 1
"""


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@unittest.skipUnless(os.name == "posix" and Path("/bin/sh").exists(), "POSIX shell required")
class InstallShTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.tmp / "sandbox-bin"
        self.bin.mkdir()
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.log = self.tmp / "calls.log"
        for tool in HOST_TOOLS + FAKE_TOOLS:
            found = shutil.which(tool)
            if found is None:
                self.skipTest(f"host tool {tool!r} not found")
            (self.bin / tool).symlink_to(found)

    def add_fake(self, name: str, body: str) -> None:
        _write_exe(self.bin / name, body)

    def run_sh(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess:
        env = {
            "PATH": str(self.bin),
            "HOME": str(self.home),
            "FAKE_LOG": str(self.log),
            "FAKE_STATE": str(self.state),
        }
        proc = subprocess.run(
            ["/bin/sh", str(INSTALL_SH), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            proc.returncode, expect, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        return proc

    def calls(self) -> list[str]:
        if not self.log.exists():
            return []
        return self.log.read_text(encoding="utf-8").splitlines()

    # --- method selection -------------------------------------------------

    def test_uv_is_preferred_and_gets_python_and_extras(self):
        self.add_fake("uv", FAKE_UV)
        self.add_fake("pipx", FAKE_PIPX)
        self.run_sh("--version", "1.0.2", "--with-tiktoken")
        self.assertIn(
            "tool install --force --python >=3.11 --with tiktoken skill-control-plane==1.0.2",
            self.calls(),
        )
        self.assertFalse(any(c.startswith("install") for c in self.calls()), "pipx must not run")

    def test_pipx_is_used_when_uv_is_absent(self):
        self.add_fake("pipx", FAKE_PIPX)
        self.add_fake("python3", FAKE_PYTHON)
        self.run_sh("--with-tiktoken")
        calls = self.calls()
        self.assertIn(
            f"install --force --python {self.bin / 'python3'} skill-control-plane", calls
        )
        self.assertIn("inject skill-control-plane tiktoken", calls)

    def test_venv_install_links_a_working_command(self):
        self.add_fake("python3", FAKE_PYTHON)
        out = self.run_sh("--source").stdout
        prefix = self.home / ".local/share/skill-control-plane/venv"
        link = self.home / ".local/bin/skills-mgr"
        self.assertIn(f"venv {prefix}", self.calls())
        self.assertTrue(
            any(c.startswith("pip -m pip install") and c.endswith("main.tar.gz") for c in self.calls()),
            self.calls(),
        )
        self.assertTrue(link.is_symlink())
        self.assertEqual(Path(os.readlink(link)), prefix / "bin/skills-mgr")
        self.assertIn("installed: skills-mgr 9.9.9", out)
        # PATH does not contain ~/.local/bin here, and the rc files stay untouched.
        self.assertIn('export PATH="', out)
        self.assertEqual(sorted(p.name for p in self.home.iterdir()), [".local"])

    def test_xdg_data_home_and_explicit_dirs_are_honoured(self):
        self.add_fake("python3", FAKE_PYTHON)
        prefix = self.tmp / "custom/env"
        bindir = self.tmp / "custom/bin"
        self.run_sh("--method", "venv", "--prefix", str(prefix), "--bin-dir", str(bindir))
        self.assertTrue((prefix / "pyvenv.cfg").exists())
        self.assertTrue((bindir / "skills-mgr").is_symlink())
        self.assertFalse((self.home / ".local").exists())

    def test_dry_run_changes_nothing(self):
        self.add_fake("python3", FAKE_PYTHON)
        out = self.run_sh("--dry-run").stdout
        self.assertIn("-m venv", out)
        self.assertIn("dry run: nothing was changed", out)
        self.assertEqual(self.calls(), [])
        self.assertEqual(list(self.home.iterdir()), [])

    # --- refusals ---------------------------------------------------------

    def test_no_python_and_no_uv_is_a_clear_error(self):
        proc = self.run_sh(expect=1)
        self.assertIn("no Python 3.11 or newer found", proc.stderr)
        self.assertIn("uv", proc.stderr)

    def test_bad_arguments_are_refused_before_anything_runs(self):
        self.add_fake("uv", FAKE_UV)
        for args, message in (
            (("--method", "brew"), "--method must be uv, pipx or venv"),
            (("--version", "1.0; rm -rf ~"), "invalid --version"),
            (("--version", "-e"), "invalid --version"),
            (("--source", "--version", "1.0.2"), "cannot be combined"),
            (("--from", "--editable"), "cannot start with '-'"),
            (("--frobnicate",), "unknown option"),
            (("--method",), "needs a value"),
        ):
            with self.subTest(args=args):
                proc = self.run_sh(*args, expect=1)
                self.assertIn(message, proc.stderr)
        self.assertEqual(self.calls(), [])

    def test_existing_non_venv_prefix_is_not_touched(self):
        self.add_fake("python3", FAKE_PYTHON)
        prefix = self.tmp / "precious"
        prefix.mkdir()
        (prefix / "keep.txt").write_text("mine", encoding="utf-8")
        proc = self.run_sh("--prefix", str(prefix), expect=1)
        self.assertIn("is not a virtual environment", proc.stderr)
        self.assertEqual([p.name for p in prefix.iterdir()], ["keep.txt"])

    def test_existing_regular_file_at_link_path_is_not_replaced(self):
        self.add_fake("python3", FAKE_PYTHON)
        bindir = self.home / ".local/bin"
        bindir.mkdir(parents=True)
        (bindir / "skills-mgr").write_text("someone else's", encoding="utf-8")
        proc = self.run_sh(expect=1)
        self.assertIn("is not a link", proc.stderr)
        self.assertEqual((bindir / "skills-mgr").read_text(encoding="utf-8"), "someone else's")
        self.assertEqual(self.calls(), [])

    def test_install_preserves_a_foreign_symlink_even_when_dangling(self):
        self.add_fake("python3", FAKE_PYTHON)
        bindir = self.home / ".local/bin"
        bindir.mkdir(parents=True)
        link = bindir / "skills-mgr"
        link.symlink_to(self.tmp / "another-tool")
        proc = self.run_sh(expect=1)
        self.assertIn("points to a different installation", proc.stderr)
        self.assertEqual(os.readlink(link), str(self.tmp / "another-tool"))
        self.assertEqual(self.calls(), [])

    def test_install_and_uninstall_leave_an_unowned_virtualenv_alone(self):
        self.add_fake("python3", FAKE_PYTHON)
        prefix = self.tmp / "unrelated"
        prefix.mkdir()
        (prefix / "pyvenv.cfg").write_text("home = unrelated\n", encoding="utf-8")
        (prefix / "keep.txt").write_text("keep me", encoding="utf-8")
        args = ("--method", "venv", "--prefix", str(prefix))
        self.assertIn("does not belong to Skills Manager", self.run_sh(*args, expect=1).stderr)
        self.assertIn("leaving", self.run_sh(*args, "--uninstall").stdout)
        self.assertEqual(sorted(p.name for p in prefix.iterdir()), ["keep.txt", "pyvenv.cfg"])
        self.assertEqual(self.calls(), [])

    # --- uninstall --------------------------------------------------------

    def test_uninstall_removes_venv_and_link_but_never_skill_data(self):
        self.add_fake("python3", FAKE_PYTHON)
        self.run_sh()
        data = self.home / ".local/share/skills-manager/skills/demo"
        data.mkdir(parents=True)
        (data / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
        out = self.run_sh("--uninstall").stdout
        self.assertIn("removed", out)
        self.assertFalse((self.home / ".local/share/skill-control-plane/venv").exists())
        self.assertFalse(os.path.lexists(self.home / ".local/bin/skills-mgr"))
        self.assertTrue((data / "SKILL.md").exists())

    def test_legacy_virtualenv_with_its_launcher_can_still_be_upgraded_and_removed(self):
        self.add_fake("python3", FAKE_PYTHON)
        prefix = self.home / ".local/share/skill-control-plane/venv"
        link = self.home / ".local/bin/skills-mgr"
        self.run_sh()
        (prefix / ".skills-manager-install").unlink(missing_ok=True)
        self.run_sh()
        self.assertTrue((prefix / ".skills-manager-install").is_file())
        (prefix / ".skills-manager-install").unlink()
        self.run_sh("--uninstall")
        self.assertFalse(prefix.exists())
        self.assertFalse(os.path.lexists(link))

    def test_marked_virtualenv_can_be_uninstalled_if_the_launcher_went_missing(self):
        self.add_fake("python3", FAKE_PYTHON)
        self.run_sh()
        prefix = self.home / ".local/share/skill-control-plane/venv"
        (self.home / ".local/bin/skills-mgr").unlink()
        self.run_sh("--uninstall")
        self.assertFalse(prefix.exists())

    def test_failed_dependency_install_can_be_retried_in_the_owned_prefix(self):
        self.add_fake("python3", FAKE_PYTHON)
        prefix = self.home / ".local/share/skill-control-plane/venv"
        launcher = self.home / ".local/bin/skills-mgr"
        self.run_sh("--from", "failed-install", expect=23)
        self.assertTrue((prefix / ".skills-manager-install").is_file())
        self.assertFalse(os.path.lexists(launcher))
        self.assertFalse(prefix.with_name("venv.skills-manager-lock").exists())
        self.run_sh()
        self.assertTrue(launcher.is_symlink())

    def test_locked_virtualenv_refuses_a_second_install_or_uninstall(self):
        self.add_fake("python3", FAKE_PYTHON)
        self.run_sh()
        prefix = self.home / ".local/share/skill-control-plane/venv"
        prefix.with_name("venv.skills-manager-lock").mkdir()
        previous = self.calls()
        for args in ((), ("--uninstall",)):
            with self.subTest(args=args):
                self.assertIn("could not lock", self.run_sh(*args, expect=1).stderr)
        self.assertTrue((prefix / ".skills-manager-install").is_file())
        self.assertEqual(self.calls(), previous)

    def test_linked_prefix_is_also_refused_with_a_trailing_slash(self):
        self.add_fake("python3", FAKE_PYTHON)
        self.run_sh()
        real = self.home / ".local/share/skill-control-plane/venv"
        alias = self.tmp / "alias"
        alias.symlink_to(real, target_is_directory=True)
        prefix = ("--method", "venv", "--prefix", str(alias) + "/")
        self.assertIn("is a link", self.run_sh(*prefix, expect=1).stderr)
        self.assertIn("leaving", self.run_sh(*prefix, "--uninstall").stdout)
        self.assertTrue(real.exists())
        self.assertTrue(alias.is_symlink())

    def test_uninstall_leaves_a_foreign_link_alone(self):
        bindir = self.home / ".local/bin"
        bindir.mkdir(parents=True)
        (bindir / "skills-mgr").symlink_to("/opt/elsewhere/skills-mgr")
        out = self.run_sh("--uninstall").stdout
        self.assertIn("leaving", out)
        self.assertTrue((bindir / "skills-mgr").is_symlink())

    def test_uninstall_uses_uv_and_pipx_only_when_they_hold_the_tool(self):
        self.add_fake("uv", FAKE_UV)
        self.add_fake("pipx", FAKE_PIPX)
        out = self.run_sh("--uninstall").stdout
        self.assertIn("nothing installed by this script was found", out)
        self.assertNotIn("tool uninstall skill-control-plane", self.calls())
        (self.state / "uv-tools").write_text("skill-control-plane v1.0.2\n- skills-mgr\n", encoding="utf-8")
        (self.state / "pipx-list").write_text("skill-control-plane 1.0.2\n", encoding="utf-8")
        self.run_sh("--uninstall")
        self.assertIn("tool uninstall skill-control-plane", self.calls())
        self.assertIn("uninstall skill-control-plane", self.calls())

    # --- structure --------------------------------------------------------

    def test_script_body_runs_only_from_its_last_line(self):
        # `curl | sh` on a cut-short download must not execute half a script.
        lines = [l for l in INSTALL_SH.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(lines[-1], 'main "$@"')

    def test_script_never_edits_shell_startup_files(self):
        text = INSTALL_SH.read_text(encoding="utf-8")
        for rc in (".bashrc", ".zshrc", ".profile", ".bash_profile"):
            self.assertNotIn(rc, text)
        self.assertNotIn("| sh", text.split("set -eu", 1)[1])

    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck not installed")
    def test_shellcheck_is_clean(self):
        proc = subprocess.run(
            ["shellcheck", "-s", "sh", str(INSTALL_SH)], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class InstallPs1Tests(unittest.TestCase):
    def test_powershell_installer_offers_the_same_options(self):
        text = INSTALL_PS1.read_text(encoding="utf-8")
        for option in ("$Method", "$Version", "$Source", "$From", "$WithTiktoken",
                       "$Prefix", "$DryRun", "$Uninstall"):
            self.assertIn(option, text)
        for method in ("'uv'", "'pipx'", "'venv'"):
            self.assertIn(method, text)

    def test_powershell_installer_never_changes_the_user_environment(self):
        text = INSTALL_PS1.read_text(encoding="utf-8")
        self.assertNotIn("SetEnvironmentVariable", text)
        self.assertNotIn("$PROFILE", text)
        self.assertNotIn("Invoke-Expression", text)


@unittest.skipUnless(POWERSHELL, "PowerShell not installed")
class PowerShellInstallerRuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.local_app_data = self.root / "fixture [parent]"
        self.prefix = self.local_app_data / "skill-control-plane" / "venv"

    def run_ps(self, *args, expect=0):
        proc = subprocess.run(
            [POWERSHELL, "-NoProfile", "-File", str(INSTALL_PS1), "-Method", "venv", *map(str, args)],
            env=dict(os.environ, LOCALAPPDATA=str(self.local_app_data), SKILLS_MGR_INSTALL_PREFIX=""),
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(proc.returncode, expect, proc.stdout + proc.stderr)
        return proc

    def test_powershell_dry_run(self):
        proc = self.run_ps("-DryRun")
        self.assertIn("dry run: nothing was changed", proc.stdout)
        self.assertFalse(self.local_app_data.exists())

    def test_unrelated_environment_entirely_preserved_on_install_and_uninstall(self):
        self.prefix.mkdir(parents=True)
        (self.prefix / "pyvenv.cfg").write_text("home = unrelated\n", encoding="utf-8")
        (self.prefix / "keep.txt").write_text("keep me", encoding="utf-8")
        self.assertIn("does not belong to Skills Manager", self.run_ps(expect=1).stderr)
        self.assertIn("leaving", self.run_ps("-Uninstall").stdout)
        self.assertEqual(sorted(path.name for path in self.prefix.iterdir()), ["keep.txt", "pyvenv.cfg"])

    def test_marked_partial_environment_can_be_removed_with_literal_paths(self):
        prefix = self.root / "venv [test]"
        prefix.mkdir()
        (prefix / ".skills-manager-install").write_bytes(b"skill-control-plane venv 1\n")
        (prefix / "partial-file").touch()
        neighbor = self.root / "venv t"
        neighbor.mkdir()
        result = self.run_ps("-Prefix", prefix, "-Uninstall", "-DryRun")
        self.assertIn("dry run: nothing was changed", result.stdout)
        self.assertTrue(prefix.is_dir())
        self.run_ps("-Prefix", prefix, "-Uninstall")
        self.assertFalse(prefix.exists())
        self.assertTrue(neighbor.is_dir())

    def test_shell_removes_old_dedicated_environment_with_product_metadata(self):
        scripts = self.prefix / "Scripts"
        scripts.mkdir(parents=True)
        (scripts / "skills-mgr.exe").touch()
        (self.prefix / "pyvenv.cfg").write_text("home = legacy\n", encoding="utf-8")
        dist = self.prefix / "Lib/site-packages/skill_control_plane-1.0.2.dist-info"
        dist.mkdir(parents=True)
        metadata = dist / "METADATA"
        metadata.write_text("Name: different-project\n\nName: skill-control-plane\n", encoding="utf-8")
        self.assertIn("leaving", self.run_ps("-Uninstall").stdout)
        self.assertTrue(self.prefix.exists())
        metadata.write_text("Name: skill-control-plane\n", encoding="utf-8")
        self.assertIn("removed", self.run_ps("-Uninstall").stdout)
        self.assertFalse(self.prefix.exists())

    def test_old_custom_environment_with_product_metadata_is_preserved(self):
        custom = self.prefix.with_name("custom")
        scripts = custom / "Scripts"
        scripts.mkdir(parents=True)
        (scripts / "skills-mgr.exe").touch()
        (custom / "pyvenv.cfg").touch()
        metadata = custom / "Lib/site-packages/skill_control_plane-1.0.2.dist-info/METADATA"
        metadata.parent.mkdir(parents=True)
        metadata.write_text("Name: skill-control-plane\n", encoding="utf-8")
        self.assertIn("leaving", self.run_ps("-Prefix", custom, "-Uninstall").stdout)
        self.assertTrue(metadata.is_file())

    def test_linked_venv_prefix_is_never_removed(self):
        self.prefix.parent.mkdir(parents=True)
        target = self.root / "other-env"
        target.mkdir()
        (target / ".skills-manager-install").write_bytes(b"skill-control-plane venv 1\n")
        try:
            self.prefix.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlinks unavailable")
        self.assertIn("leaving", self.run_ps("-Uninstall").stdout)
        self.assertIn("not an ordinary directory", self.run_ps(expect=1).stderr)
        self.assertTrue(self.prefix.is_symlink())
        self.assertTrue((target / ".skills-manager-install").is_file())

    def test_removing_owned_environment_does_not_remove_link_targets(self):
        self.prefix.mkdir(parents=True)
        (self.prefix / ".skills-manager-install").write_bytes(b"skill-control-plane venv 1\n")
        target = self.root / "external"
        target.mkdir()
        (target / "keep.txt").write_bytes(b"keep")
        try:
            (self.prefix / "linked-data").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlinks unavailable")
        self.run_ps("-Uninstall")
        self.assertFalse(self.prefix.exists())
        self.assertEqual((target / "keep.txt").read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
