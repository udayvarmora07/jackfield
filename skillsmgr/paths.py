"""Centralized path resolution for Jackfield.

Resolution order for the data base directory:
  1. $JACKFIELD_DATA       (explicit override, used by tests and power users)
     $SKILLS_MANAGER_DATA  (the same override under its pre-rename name)
  2. $XDG_DATA_HOME        (XDG convention)
  3. ~/.local/share        (default on Linux)

A manager subdirectory is always appended to the resolved base: ``jackfield``
for new installs. A library created before the rename lives in
``skills-manager`` and is kept where it is (never moved), so an existing
``skills-manager`` directory is used whenever no ``jackfield`` one exists.
"""

from __future__ import annotations

import os
from pathlib import Path

from .path_safety import mkdir_private, tighten_private_root, trusted_root


def home_dir() -> Path:
    """Return the user's home directory, treating an empty ``$HOME`` as unset.

    SCOPE-17: ``HOME=""`` makes ``Path.home()`` return ``/``, so every agent
    scope became ``/.claude/skills``, ``/.codex/skills``, … -- roots this tool
    both reads *and writes*.  An empty or whitespace-only value is a broken
    environment, not a request to use the filesystem root, so it falls back to
    the passwd entry the same way an unset variable does.
    """
    raw = os.environ.get("HOME")
    if raw is not None and raw.strip():
        return Path(raw).expanduser()
    try:
        import pwd

        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (ImportError, KeyError, OSError):  # pragma: no cover - non-POSIX
        return Path.home()


def _absolute(base: Path) -> Path:
    """Anchor a possibly-relative root so its meaning cannot drift with the CWD.

    SCOPE-17: a relative ``JACKFIELD_DATA``/``XDG_DATA_HOME`` resolved
    against whatever directory the process happened to start in, so the same
    environment pointed at different data depending on where the tool was run.
    """
    return base if base.is_absolute() else (Path.cwd() / base)


DATA_ENV = "JACKFIELD_DATA"
LEGACY_DATA_ENV = "SKILLS_MANAGER_DATA"
MANAGER_DIR = "jackfield"
LEGACY_MANAGER_DIR = "skills-manager"


def data_override() -> str | None:
    """The explicit data-base override, preferring the current variable name."""
    for name in (DATA_ENV, LEGACY_DATA_ENV):
        value = os.environ.get(name)
        if value and value.strip():
            return value
    return None


def _manager_dir(base: Path) -> Path:
    """Pick the manager subdirectory under ``base`` without moving any data.

    ``jackfield`` wins when it exists; otherwise a pre-rename ``skills-manager``
    library is used in place; otherwise a new install gets ``jackfield``.
    Whatever is chosen still goes through ``trusted_root``, which resolves a
    symlink and validates its target exactly as it did before the rename.
    """
    current, legacy = base / MANAGER_DIR, base / LEGACY_MANAGER_DIR
    if not os.path.lexists(current) and os.path.lexists(legacy):
        return legacy
    return current


def data_dir() -> Path:
    """Return the validated root data directory, creating it if needed."""
    override = data_override()
    if override:
        base = _absolute(Path(override).expanduser())
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg and xdg.strip():
            base = _absolute(Path(xdg).expanduser())
        else:
            base = home_dir() / ".local" / "share"
    # Validate the selected base itself before appending the manager-owned
    # subtree.  This rejects broad/shared overrides such as ``/`` or ``/tmp``
    # even when the final manager directory does not exist yet.
    selected = trusted_root(base)
    manager = _manager_dir(selected)
    try:
        return trusted_root(manager)
    except ValueError as exc:
        # A root created before the ownership control landed is group/world-
        # writable, so every subcommand fails with no way back.  Tighten it when
        # it is recognisably ours and owned by us; the repair only ever reduces
        # access, and anything else falls through to the refusal below.
        repaired = tighten_private_root(manager)
        if repaired is not None:
            return trusted_root(repaired)
        raise ValueError(
            f"{exc}\n"
            f"  fix: this directory is only readable and writable by your user.\n"
            f"       run: chmod 700 {manager}\n"
            f"  or point the manager somewhere private, e.g.:\n"
            f"       export JACKFIELD_DATA=$HOME/.local/share/jackfield"
        ) from None


def skills_dir() -> Path:
    """Directory holding one subdirectory per installed skill."""
    return data_dir() / "skills"


def trash_dir() -> Path:
    """Directory holding soft-deleted skills as <name>-<timestamp> subdirs."""
    return data_dir() / "trash"


def templates_dir() -> Path:
    """Directory holding skill templates (plain .md files)."""
    return data_dir() / "templates"


def backups_dir() -> Path:
    """Directory holding exported/backup archives."""
    return data_dir() / "backups"


def db_path() -> Path:
    """Path of the SQLite index database."""
    return data_dir() / "skills-manager.db"


def ensure_dirs() -> None:
    """Create all data directories if they do not exist."""
    for path in (data_dir(), skills_dir(), trash_dir(), templates_dir(), backups_dir()):
        mkdir_private(path)
