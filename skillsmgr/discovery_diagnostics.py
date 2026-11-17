"""Bounded observations of personal skill folders, independent of native loading."""

import os
import stat
from pathlib import Path

from .paths import home_dir

MAX_ENTRIES = 4096
MAX_GROUPS = 50
MAX_SKILLS = 50
MAX_NAME = 128
SOURCE = "~/.claude/skills"
_DIR_FLAGS = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
              getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))


def _supports_safe_scan():
    return (hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
            and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd
            and os.stat in os.supports_follow_symlinks and os.scandir in os.supports_fd)


def _open_root(home):
    """Open each path component without following links."""
    path = Path(os.path.abspath(os.fspath(home))) / ".claude" / "skills"
    fd = os.open(os.path.sep, _DIR_FLAGS)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _safe_name(name, observation):
    if len(name) > MAX_NAME:
        observation["partial"] = True
    return "".join(c if c.isprintable() else "\ufffd" for c in name[:MAX_NAME])


def _document(fd, name, observation):
    try:
        mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
    except FileNotFoundError:
        return False
    except OSError:
        observation["partial"] = True
        return None
    if not stat.S_ISREG(mode):
        observation["partial"] = True
        return None
    return True


def _has_primary(fd, observation):
    # Check both even when the first exists, so unsafe evidence isn't hidden.
    enabled = _document(fd, "SKILL.md", observation)
    disabled = _document(fd, "SKILL.md.disabled", observation)
    if enabled is True or disabled is True:
        return True
    if enabled is None or disabled is None:
        return None
    return False


def _plugin_root(fd, observation):
    try:
        plugin_fd = os.open(".claude-plugin", _DIR_FLAGS, dir_fd=fd)
    except FileNotFoundError:
        return False
    except OSError:
        observation["partial"] = True
        return None
    try:
        return _document(plugin_fd, "plugin.json", observation)
    finally:
        os.close(plugin_fd)


def _entries(fd, observation, budget):
    if budget[0] <= 0:
        observation["partial"] = True
        return
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                budget[0] -= 1
                yield entry.name
                if budget[0] <= 0:
                    observation["partial"] = True
                    return
    except OSError:
        observation["partial"] = True


def _open_child(fd, name, observation):
    try:
        mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
        if stat.S_ISLNK(mode):
            observation["partial"] = True
            return None
        if not stat.S_ISDIR(mode):
            return None
        return os.open(name, _DIR_FLAGS, dir_fd=fd)
    except OSError:
        observation["partial"] = True
        return None


def _group(fd, name, observation, budget):
    if _has_primary(fd, observation) is not False:
        return
    if _plugin_root(fd, observation) is not False:
        return
    skills = []
    for child in _entries(fd, observation, budget):
        child_fd = _open_child(fd, child, observation)
        if child_fd is None:
            continue
        try:
            if _has_primary(child_fd, observation) is True:
                if len(skills) < MAX_SKILLS:
                    skills.append(_safe_name(child, observation))
                else:
                    observation["partial"] = True
        finally:
            os.close(child_fd)
    if skills:
        if len(observation["groups"]) < MAX_GROUPS:
            observation["groups"].append({"name": _safe_name(name, observation), "skills": sorted(skills)})
        else:
            observation["partial"] = True


def observe_grouped_personal_skills(home=None):
    """Observe two-level personal folders; this does not establish runtime loading."""
    result = {"source": SOURCE, "state": "observed", "runtime_state": "unknown",
              "partial": False, "groups": []}
    if not _supports_safe_scan():
        result["state"] = "unavailable"
        result["partial"] = True
        return result
    try:
        fd = _open_root(home_dir() if home is None else home)
    except FileNotFoundError:
        result["state"] = "missing"
        return result
    except (OSError, RuntimeError, ValueError):
        result["state"] = "unavailable"
        result["partial"] = True
        return result
    budget = [MAX_ENTRIES]
    try:
        for name in _entries(fd, result, budget):
            if name == "synced":
                continue
            group_fd = _open_child(fd, name, result)
            if group_fd is None:
                continue
            try:
                _group(group_fd, name, result, budget)
            finally:
                os.close(group_fd)
    finally:
        os.close(fd)
    result["groups"].sort(key=lambda group: group["name"])
    return result
