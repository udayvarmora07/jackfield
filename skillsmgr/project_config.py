"""Bounded observations of one project's Codex skill declarations.

Declarations do not establish what a Codex session actually loads. Reading
requires POSIX no-follow directory opens and Linux's descriptor filesystem;
other platforms return unavailable instead of using an unsafe fallback.
"""

from __future__ import annotations

import os
from pathlib import Path
import tomllib

from .file_reads import read_regular_file

MAX_BYTES = 1024 * 1024
MAX_RULES = 50


class ProjectUnavailable(Exception):
    """The supplied project directory could not be safely opened."""


def _supported() -> bool:
    return (os.name == 'posix' and hasattr(os, 'O_NOFOLLOW')
            and hasattr(os, 'O_DIRECTORY') and Path('/proc/self/fd').is_dir())


def _result(state: str, reason: str) -> dict:
    return {"state": state, "reason": reason, "include_instructions": None,
            "rules": [], "total": 0, "omitted": 0, "schema_unknown": False}


def _open_project(project: Path) -> int:
    """Anchor every directory component without following links."""
    if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY")):
        raise OSError("safe directory traversal unavailable")
    expanded = Path(os.path.expanduser(os.fspath(project)))
    if '..' in expanded.parts:
        raise OSError('parent traversal is unavailable')
    path = Path(os.path.abspath(expanded))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_config(project: Path) -> bytes:
    """Open the config through pinned directories; reject final links too."""
    try:
        project_fd = _open_project(project)
    except OSError as exc:
        raise ProjectUnavailable from exc
    try:
        directory_fd = os.open('.codex', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=project_fd)
        try:
            # The proc descriptor keeps the checked directory pinned even if renamed.
            descriptor_path = Path('/proc/self/fd') / str(directory_fd) / 'config.toml'
            if not Path('/proc/self/fd').is_dir():
                raise OSError('safe descriptor path unavailable')
            return read_regular_file(descriptor_path, MAX_BYTES, follow_symlinks=False)
        finally:
            os.close(directory_fd)
    finally:
        os.close(project_fd)


def _rule(entry: object) -> dict | None:
    if not isinstance(entry, dict) or type(entry.get('enabled')) is not bool:
        return None
    selectors = [key for key in ('name', 'path') if key in entry]
    if len(selectors) != 1 or not isinstance(entry[selectors[0]], str) or not entry[selectors[0]]:
        return None
    return {'selector': selectors[0], 'enabled': entry['enabled']}


def _observe_skills(skills: object) -> dict:
    result = _result('absent', 'No project skill declarations observed.')
    if not isinstance(skills, dict):
        result['state'] = 'unavailable'
        result['reason'] = 'Project skill declarations have an unrecognised schema.'
        result['schema_unknown'] = True
        return result
    if 'include_instructions' in skills:
        if type(skills['include_instructions']) is bool:
            result['include_instructions'] = skills['include_instructions']
            result['state'] = 'observed'
        else:
            result['schema_unknown'] = True
    if 'config' in skills:
        rules = skills['config']
        if not isinstance(rules, list):
            result['schema_unknown'] = True
        else:
            result['total'] = len(rules)
            for entry in rules[:MAX_RULES]:
                rule = _rule(entry)
                if rule is None:
                    result['schema_unknown'] = True
                else:
                    result['rules'].append(rule)
            result['omitted'] = max(0, len(rules) - MAX_RULES)
            result['state'] = 'observed'
    if result['schema_unknown'] and result['state'] == 'absent':
        result['state'] = 'unavailable'
        result['reason'] = 'Project skill declarations have an unrecognised schema.'
    elif result['schema_unknown']:
        result['reason'] = 'Some project skill declarations have an unrecognised schema; session effect is unknown.'
    elif result['state'] == 'observed':
        result['reason'] = 'Project skill declarations observed; their session effect is unknown.'
    return result


def observe_project_skill_config(project: Path | None) -> dict:
    """Read only project/.codex/config.toml, with no effective-state verdict."""
    if project is None:
        return _result('unavailable', 'No project supplied.')
    if not _supported():
        return _result('unavailable', 'Safe project config reading is unavailable on this platform.')
    try:
        data = _read_config(Path(project))
    except FileNotFoundError:
        return _result('missing', 'Project config not found.')
    except (OSError, ValueError, ProjectUnavailable):
        return _result('unavailable', 'Project or config path unavailable or unsafe.')
    try:
        config = tomllib.loads(data.decode('utf-8'))
    except (UnicodeError, ValueError, RecursionError):
        return _result('unavailable', 'Project config could not be parsed.')
    if 'skills' not in config:
        return _result('absent', 'No project skill declarations observed.')
    return _observe_skills(config['skills'])
