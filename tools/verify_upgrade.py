#!/usr/bin/env python3
"""Rehearse a published-to-candidate upgrade on disposable skills."""

from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener

from check_package_data import _create_install_venv
from .verify_published import PROJECT, VerificationError, _NoRedirect, _read

# Oldest tested upgrade baseline for the 1.1 series. PyPI 1.0.2, 2026-11-21.
# It predates the Jackfield rename, so its library lives in ``<base>/skills-manager``.
BASELINE_VERSION = "1.0.2"
BASELINE_NAME = f"skill_control_plane-{BASELINE_VERSION}-py3-none-any.whl"
BASELINE_URL = (
    "https://files.pythonhosted.org/packages/3a/f4/"
    "5a629ca1a0b5541cb14608a8dca5cdc7d3de56e3b60196ab1952429e434e/"
    + BASELINE_NAME
)
BASELINE_SHA256 = "db2c07bb51a98e9993228ac551376a590a68eaedb478789c087674246e188a83"
BASELINE_SIZE = 380_909
DOWNLOAD_ATTEMPTS = 3
ACTIVE = "active-fixture"
DISABLED = "disabled-fixture"
TRASHED = "trashed-fixture"
TEMPLATE = "upgrade-fixture"


def _download_baseline() -> bytes:
    opener = build_opener(_NoRedirect())
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            return _read(BASELINE_URL, BASELINE_SIZE, opener)
        except HTTPError as exc:
            exc.close()
            message = f"baseline download failed with HTTP {exc.code}"
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                raise VerificationError(message) from exc
        except (URLError, TimeoutError, HTTPException) as exc:
            message = f"baseline download failed: {exc}"
        if attempt + 1 < DOWNLOAD_ATTEMPTS:
            time.sleep(attempt + 1)
    raise VerificationError(message)


def _baseline_bytes(local_wheel: Path | None) -> bytes:
    if local_wheel is None:
        payload = _download_baseline()
    else:
        with local_wheel.open("rb") as stream:
            payload = stream.read(BASELINE_SIZE + 1)
    if len(payload) != BASELINE_SIZE or hashlib.sha256(payload).hexdigest() != BASELINE_SHA256:
        raise VerificationError("the baseline wheel does not match the pinned PyPI artifact")
    return payload


def _candidate_wheel(dist_dir: Path) -> tuple[Path, str]:
    wheels = list(dist_dir.resolve().glob("*.whl"))
    if len(wheels) != 1 or not wheels[0].name.startswith("skill_control_plane-"):
        raise VerificationError("expected exactly one Jackfield wheel in the artifact directory")
    version = wheels[0].name.split("-", 2)[1]
    if version == BASELINE_VERSION:
        raise VerificationError("the candidate wheel must differ from the baseline release")
    return wheels[0], version


def _run(python: Path, root: Path, env: dict, *args: str) -> str:
    result = subprocess.run(
        [str(python), "-I", "-X", "utf8", *args], cwd=root, env=env,
        capture_output=True, timeout=60,
    )
    if result.returncode:
        details = (result.stderr or result.stdout).decode("utf-8", "replace").strip()
        raise VerificationError(f"command failed ({result.returncode}): {' '.join(args)}\n{details}")
    return result.stdout.decode("utf-8")


def _install(python: Path, root: Path, env: dict, wheel: Path, version: str) -> None:
    _run(python, root, env, "-m", "pip", "--isolated", "--disable-pip-version-check",
         "install", "--no-index", "--no-deps", "--force-reinstall", str(wheel))
    actual = _run(python, root, env, "-c",
                  f"from importlib.metadata import version; print(version({PROJECT!r}))").strip()
    if actual != version:
        raise VerificationError(f"installed {actual!r} where {version!r} was expected")


def _cli(python: Path, root: Path, env: dict, data: Path, *args: str) -> str:
    return _run(python, root, env, "-m", "skillsmgr", "--data-dir", str(data), *args)


def _seed(python: Path, root: Path, env: dict, data: Path, archive: Path) -> None:
    for name in (ACTIVE, DISABLED, TRASHED):
        _cli(python, root, env, data, "create", name, "-d", f"{name} description",
             "--body", f"{name} body")
        asset = _library(data) / "skills" / name / "references" / "fixture.bin"
        asset.parent.mkdir()
        asset.write_bytes(name.encode("ascii") + b"\x00\xff\r\n")
    _cli(python, root, env, data, "disable", DISABLED)
    _cli(python, root, env, data, "remove", TRASHED, "--trash")
    _cli(python, root, env, data, "templates", "new", TEMPLATE, "--body", "Synthetic template.")
    _cli(python, root, env, data, "export", "--full", "--dest", str(archive))
    if not archive.is_file():
        raise VerificationError("the baseline export did not create an archive")


def _library(data: Path) -> Path:
    """The manager directory under ``data``: ``jackfield``, or the pre-rename one kept in place."""
    current = data / "jackfield"
    return current if current.exists() or not (data / "skills-manager").exists() else data / "skills-manager"


def _contents(data: Path) -> dict[str, bytes]:
    library = _library(data)
    return {item.relative_to(library).as_posix(): item.read_bytes()
            for folder in ("skills", "trash", "templates")
            for item in (library / folder).rglob("*") if item.is_file()}


def _check_library(python: Path, root: Path, env: dict, data: Path, expected: dict) -> None:
    try:
        rows = {row["name"]: bool(row["disabled"])
                for row in json.loads(_cli(python, root, env, data, "list", "--json"))}
        trashed = {row["name"] for row in json.loads(_cli(python, root, env, data, "trash", "list", "--json"))}
        templates = json.loads(_cli(python, root, env, data, "templates", "list", "--json"))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise VerificationError("listing returned invalid library, trash, or template records") from exc
    if rows != {ACTIVE: False, DISABLED: True} or trashed != {TRASHED} or templates != [TEMPLATE]:
        raise VerificationError("the active, disabled, trashed, or template state changed")
    if expected != _contents(data):
        raise VerificationError("the library documents, supporting files, or template bytes changed")


def verify_upgrade(dist_dir: Path, local_wheel: Path | None = None) -> None:
    candidate, version = _candidate_wheel(dist_dir)
    baseline = _baseline_bytes(local_wheel)
    env = os.environ.copy()
    env["PIP_CONFIG_FILE"] = os.devnull
    with tempfile.TemporaryDirectory(prefix="skillsmgr-upgrade-") as temporary:
        root = Path(temporary).resolve()
        old_wheel = root / BASELINE_NAME
        old_wheel.write_bytes(baseline)
        python = _create_install_venv(root / "venv", env=env)
        data, restored, archive = root / "existing", root / "restored", root / "before.tar.gz"
        data.mkdir(mode=0o700)
        restored.mkdir(mode=0o700)
        _install(python, root, env, old_wheel, BASELINE_VERSION)
        _seed(python, root, env, data, archive)
        expected = _contents(data)
        if len(expected) != 7:
            raise VerificationError("the baseline fixture is missing a document, supporting file, or template")
        _install(python, root, env, candidate, version)
        _check_library(python, root, env, data, expected)
        if (data / "jackfield").exists():
            raise VerificationError("the upgrade created a new library instead of keeping the existing one in place")
        _cli(python, root, env, restored, "import", str(archive), "--full")
        _check_library(python, root, env, restored, expected)
        print(f"PASS: {BASELINE_VERSION} to {version} preserved an existing library and restored its full backup")
        _install(python, root, env, old_wheel, BASELINE_VERSION)
        _check_library(python, root, env, data, expected)
        print(f"PASS: {BASELINE_VERSION} reopened the original library after reinstall")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--baseline-wheel", type=Path, help="local copy of the pinned public wheel")
    args = parser.parse_args(argv)
    try:
        verify_upgrade(args.dist_dir, args.baseline_wheel)
    except (OSError, RuntimeError, ValueError, HTTPException, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
