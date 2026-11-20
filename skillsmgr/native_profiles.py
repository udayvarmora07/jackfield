"""Reviewable, narrowly scoped native project settings writes.

Only strict JSON that round-trips exactly is writable. Foreign applications do
not share our lock, so a small race remains between the final check and replace.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path

from .atomic_io import mutation_lock
from .native_state import MAX_CONFIG_BYTES, _glob_match, _unique_object
from .project_config import _open_project
from .validator import validate_skill_name

_TARGETS = {
    'claude-code': ('.claude', 'settings.local.json'),
    'gemini': ('.gemini', 'settings.json'),
    'opencode': (None, 'opencode.json'),
}
_NOTES = {
    'claude-code': 'Plugin skills are not affected; declaration is not effective state.',
    'gemini': 'User-level disables cannot be undone here; untrusted workspaces may ignore settings.',
    'opencode': 'Other config layers and per-agent rules are not observed.',
}


class NativeProfileError(ValueError):
    """Unsafe or stale native settings request."""


def _canonical_project(project: Path) -> Path:
    value = os.fspath(project)
    if not os.path.isabs(value) or os.path.normpath(value) != value:
        raise NativeProfileError('Project must be a normalized absolute path.')
    return Path(value)


def _parent(project: Path, agent: str) -> int:
    if agent not in _TARGETS:
        raise NativeProfileError('Native project writing is unsupported for this agent.')
    if not all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'fchmod')):
        raise NativeProfileError('Safe native writes are unavailable on this platform.')
    fd = _open_project(project)
    folder = _TARGETS[agent][0]
    if folder is not None:
        try:
            child = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        finally:
            os.close(fd)
        fd = child
    if agent == 'opencode':
        try:
            for other in ('opencode.jsonc', '.opencode'):
                try:
                    os.stat(other, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise NativeProfileError('Additional OpenCode project settings require manual review.')
        except BaseException:
            os.close(fd)
            raise
    return fd


def _read(fd: int, name: str) -> tuple[bytes | None, int | None]:
    try:
        target = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0), dir_fd=fd)
    except FileNotFoundError:
        return None, None
    try:
        info = os.fstat(target)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CONFIG_BYTES:
            raise NativeProfileError('Settings file is not regular or exceeds 1 MiB.')
        chunks = []
        remaining = MAX_CONFIG_BYTES + 1
        while remaining:
            chunk = os.read(target, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b''.join(chunks)
        if len(data) > MAX_CONFIG_BYTES:
            raise NativeProfileError('Settings file exceeds 1 MiB.')
        return data, stat.S_IMODE(info.st_mode)
    finally:
        os.close(target)


def _format(data: bytes | None) -> tuple[dict, tuple]:
    if data is None:
        return {}, (2, False, False, True)
    try:
        text = data.decode('utf-8')
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(value, dict):
            raise ValueError()
        for indent in (None, 1, 2, 3, 4, 8, '\t'):
            for ascii_only in (False, True):
                for compact in (False, True):
                    for newline in (False, True):
                        style = (indent, ascii_only, compact, newline)
                        if _encode(value, style) == data:
                            return value, style
    except (ValueError, UnicodeError, RecursionError):
        pass
    raise NativeProfileError('Settings are not strict JSON that round-trips byte for byte.')


def _encode(value: dict, style: tuple) -> bytes:
    indent, ascii_only, compact, newline = style
    text = json.dumps(value, indent=indent, ensure_ascii=ascii_only,
                      separators=(',', ':') if compact else None, allow_nan=False)
    return (text + ('\n' if newline else '')).encode('utf-8')


def _change(config: dict, agent: str, off: list[str]) -> None:
    if not off:
        return
    if agent == 'claude-code':
        rules = config.setdefault('skillOverrides', {})
        if not isinstance(rules, dict) or any(not isinstance(v, str) or v not in ('on', 'off', 'name-only', 'user-invocable-only') for v in rules.values()):
            raise NativeProfileError('Unexpected skillOverrides value.')
        for name in off:
            rules[name] = 'off'
    elif agent == 'gemini':
        skills = config.setdefault('skills', {})
        if not isinstance(skills, dict):
            raise NativeProfileError('Unexpected skills value.')
        disabled = skills.setdefault('disabled', [])
        if not isinstance(disabled, list) or any(not isinstance(n, str) for n in disabled):
            raise NativeProfileError('Unexpected skills.disabled value.')
        for name in off:
            if name not in disabled:
                disabled.append(name)
        if len(disabled) > 1000:
            raise NativeProfileError('Too many Gemini disabled skills.')
    else:
        if 'permissions' in config and 'permission' not in config:
            rules = config['permissions']
            if (not isinstance(rules, list) or len(rules) > 256
                    or any(not isinstance(rule, dict) or not isinstance(rule.get('action'), str)
                           or (rule['action'] == 'skill' and
                               (not isinstance(rule.get('resource'), str)
                                or len(rule['resource']) > 512
                                or rule.get('effect') not in ('allow', 'ask', 'deny')))
                           for rule in rules)):
                raise NativeProfileError('Unexpected permissions value.')
            for name in off:
                rule = {'action': 'skill', 'resource': name, 'effect': 'deny'}
                matching = [r for r in rules if r.get('action') == 'skill' and isinstance(r.get('resource'), str) and _glob_match(r['resource'], name)]
                if not matching or matching[-1].get('effect') != 'deny':
                    rules.append(rule)
            if len(rules) > 256:
                raise NativeProfileError('Too many OpenCode permission rules.')
        elif 'permission' in config and 'permissions' not in config:
            permission = config['permission']
            if not isinstance(permission, dict) or not isinstance(permission.get('skill'), dict):
                raise NativeProfileError('Unknown OpenCode skill permission dialect.')
            rules = permission['skill']
            if any(not isinstance(v, str) or v not in ('allow', 'ask', 'deny') for v in rules.values()):
                raise NativeProfileError('Unexpected OpenCode skill rule.')
            for name in off:
                rules.pop(name, None)
                rules[name] = 'deny'
            if len(rules) > 256:
                raise NativeProfileError('Too many OpenCode permission rules.')
        else:
            raise NativeProfileError('Unknown or mixed OpenCode dialect.')


def _digest(data: bytes | None) -> str:
    return 'missing' if data is None else hashlib.sha256(data).hexdigest()



def _handoff(project: Path, agent: str, names: list[str]) -> dict:
    """Describe a session override or manual edit, never write native settings."""
    try:
        if project.resolve(strict=True) != project or not project.is_dir():
            raise OSError("expected a plain project directory")
    except (OSError, RuntimeError) as exc:
        raise NativeProfileError('Project path is unavailable or unsafe.') from exc
    inputs = {'project': str(project), 'agent': agent, 'off': names}
    plan_id = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if agent == 'codex':
        rules = ', '.join('{name = ' + json.dumps(name) + ', enabled = false}' for name in names)
        return {**inputs, 'plan_id': plan_id, 'status': 'launch-only',
                'argv': ['codex', '-c', 'skills.config=[' + rules + ']'],
                'note': 'Use these arguments when launching Codex for this project; no settings file is written.'}
    return {**inputs, 'plan_id': plan_id, 'status': 'manual-patch',
            'path': str(project / '.commandcode/settings.local.json'),
            'patch': {'key': 'disabledSkills', 'operation': 'add names after reviewing existing layers',
                      'names': names},
            'note': 'Layer merge behavior is unverified; review existing user and project settings before editing.'}


def _review_diff(before: bytes | None, after: bytes, names: list[str]) -> tuple[str, bool]:
    """Return a zero-context diff only if every changed line is target-only.

    A compact JSON line or a reordered container can carry arbitrary unrelated
    values. Fail closed when a line cannot be proven to contain just structure
    or the requested edit. Hashes still bind the full preimage and postimage.
    """
    old = '' if before is None else before.decode('utf-8')
    lines = list(difflib.unified_diff(old.splitlines(True), after.decode('utf-8').splitlines(True),
                                     fromfile='before', tofile='after', n=0))
    allowed = {'{', '}', '[', ']', '{}', '[]',
               '"skillOverrides": {', '"skills": {', '"disabled": [',
               '"permission": {', '"skill": {', '"permissions": [',
               '"action": "skill"', '"effect": "deny"'}
    for name in names:
        quoted = json.dumps(name)
        allowed.update({quoted, '"resource": ' + quoted})
        allowed.update(quoted + ': ' + json.dumps(value) for value in
                       ('on', 'off', 'name-only', 'user-invocable-only', 'allow', 'ask', 'deny'))
    for index, line in enumerate(lines):
        if index < 2 or line.startswith('@@'):
            continue
        if line.startswith(('+', '-')) and line[1:].strip().removesuffix(',') in allowed:
            continue
        return '', True
    return ''.join(lines), False

def preview_native(project: Path, agent: str, off: list[str]) -> dict:
    """Return an exact-byte preview; no directories or files are created."""
    project = _canonical_project(project)
    if not isinstance(off, list) or len(off) > 1000:
        raise NativeProfileError('Expected at most 1000 skill names.')
    names = sorted(set(validate_skill_name(name) for name in off))
    if not names:
        raise NativeProfileError('At least one skill name is required.')
    if agent in ('codex', 'commandcode'):
        return _handoff(project, agent, names)
    try:
        fd = _parent(project, agent)
        try:
            before, mode = _read(fd, _TARGETS[agent][1])
        finally:
            os.close(fd)
    except OSError as exc:
        raise NativeProfileError('Project settings path is unavailable or unsafe.') from exc
    config, style = _format(before)
    _change(config, agent, names)
    after = before if not names and before is not None else _encode(config, style)
    if len(after) > MAX_CONFIG_BYTES:
        raise NativeProfileError('Result exceeds 1 MiB.')
    target = project.joinpath(*filter(None, _TARGETS[agent]))
    inputs = {'project': str(project), 'agent': agent, 'off': names,
              'pre_hash': _digest(before), 'post_hash': _digest(after), 'mode': mode}
    plan = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    diff, suppressed = _review_diff(before, after, names)
    return {**inputs, 'plan_id': plan, 'path': str(target),
            'status': 'no-op' if before == after else 'will-change', 'note': _NOTES[agent],
            'changes': [{'skill': name, 'operation': 'ensure off'} for name in names],
            'diff': diff, 'diff_suppressed': suppressed,
            'diff_note': 'Full diff suppressed because changed lines may contain unrelated settings.' if suppressed else None}


def _backup_dir(data_dir: Path) -> int:
    root = _open_project(_canonical_project(data_dir))
    try:
        try:
            os.mkdir('native-backups', 0o700, dir_fd=root)
        except FileExistsError:
            pass
        fd = os.open('native-backups', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        info = os.fstat(fd)
        if info.st_mode & 0o077 or (hasattr(os, 'getuid') and info.st_uid != os.getuid()):
            os.close(fd)
            raise NativeProfileError('Native backup directory is not private.')
        return fd
    finally:
        os.close(root)


def _write_new(fd: int, name: str, data: bytes, mode: int) -> None:
    file_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=fd)
    try:
        os.fchmod(file_fd, mode)
        with os.fdopen(file_fd, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(file_fd)
    finally:
        os.close(file_fd)


def _replace(fd: int, name: str, data: bytes, mode: int, expected: str, expected_mode: int | None) -> None:
    temporary = '.skills-manager-' + secrets.token_hex(16)
    try:
        _write_new(fd, temporary, data, mode)
        current, current_mode = _read(fd, name)
        if _digest(current) != expected or current_mode != expected_mode:
            raise NativeProfileError('Settings changed since preview; nothing replaced.')
        os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass


def apply_native(project: Path, agent: str, off: list[str], plan_id: str, data_dir: Path) -> dict:
    """Recompute the preview, then back up and apply if its exact plan still matches."""
    if agent in ('codex', 'commandcode'):
        raise NativeProfileError('This agent supports a read-only handoff only; apply is unavailable.')
    data_dir = _canonical_project(data_dir)
    with mutation_lock(data_dir / 'native-profiles'):
        plan = preview_native(project, agent, off)
        if not isinstance(plan_id, str) or not secrets.compare_digest(plan['plan_id'], plan_id):
            raise NativeProfileError('Native settings plan is stale.')
        if plan['status'] == 'no-op':
            return {'status': 'no-op', 'plan_id': plan_id}
        fd = _parent(Path(plan['project']), agent)
        try:
            before, mode = _read(fd, _TARGETS[agent][1])
            if _digest(before) != plan['pre_hash'] or mode != plan['mode']:
                raise NativeProfileError('Settings changed since preview.')
            config, style = _format(before)
            _change(config, agent, plan['off'])
            after = _encode(config, style)
            if _digest(after) != plan['post_hash']:
                raise NativeProfileError('Native settings plan is stale.')
            backup_id = secrets.token_hex(16)
            record = {'version': 1, 'state': 'prepared', 'project': plan['project'], 'agent': agent, 'mode': mode,
                      'pre_hash': plan['pre_hash'], 'post_hash': plan['post_hash'],
                      'preimage': None if before is None else base64.b64encode(before).decode('ascii')}
            payload = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
            backups = _backup_dir(data_dir)
            try:
                _write_new(backups, backup_id + '.json', payload, 0o600)
                os.fsync(backups)
            finally:
                os.close(backups)
            try:
                _replace(fd, _TARGETS[agent][1], after, mode if mode is not None else 0o600,
                         plan['pre_hash'], mode)
                current, _ = _read(fd, _TARGETS[agent][1])
            except (OSError, NativeProfileError) as exc:
                raise NativeProfileError(f'Apply failed; backup {backup_id} was retained; settings may have changed.') from exc
            if _digest(current) != plan['post_hash']:
                raise NativeProfileError(f'Post-write verification failed; backup {backup_id} was retained.')
            record['state'] = 'applied'
            payload = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
            backups = _backup_dir(data_dir)
            temporary = '.' + backup_id + '.tmp'
            try:
                _write_new(backups, temporary, payload, 0o600)
                os.replace(temporary, backup_id + '.json', src_dir_fd=backups, dst_dir_fd=backups)
                os.fsync(backups)
            except OSError as exc:
                raise NativeProfileError(f'Backup {backup_id} finalization failed; settings may have changed.') from exc
            finally:
                try:
                    os.unlink(temporary, dir_fd=backups)
                except FileNotFoundError:
                    pass
                os.close(backups)
            return {'status': 'applied', 'backup_id': backup_id, 'plan_id': plan_id}
        finally:
            os.close(fd)


def undo_native(backup_id: str, data_dir: Path) -> dict:
    """Restore a private preimage only when the current postimage still matches."""
    if not isinstance(backup_id, str) or len(backup_id) != 32 or any(c not in '0123456789abcdef' for c in backup_id):
        raise NativeProfileError('Invalid backup id.')
    data_dir = _canonical_project(data_dir)
    with mutation_lock(data_dir / 'native-profiles'):
        backups = _backup_dir(data_dir)
        try:
            # Encoded preimages can be larger than the config byte limit.
            raw_fd = os.open(backup_id + '.json', os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0), dir_fd=backups)
            try:
                info = os.fstat(raw_fd)
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 2 * MAX_CONFIG_BYTES:
                    raise NativeProfileError('Unsafe backup record.')
                with os.fdopen(raw_fd, 'rb', closefd=False) as stream:
                    raw = stream.read(2 * MAX_CONFIG_BYTES + 1)
                if len(raw) > 2 * MAX_CONFIG_BYTES:
                    raise NativeProfileError('Unsafe backup record.')
            finally:
                os.close(raw_fd)
        finally:
            os.close(backups)
        try:
            record = json.loads(raw, object_pairs_hook=_unique_object)
            if record['version'] != 1 or record['state'] != 'applied' or record['agent'] not in _TARGETS:
                raise ValueError()
            before = None if record['preimage'] is None else base64.b64decode(record['preimage'], validate=True)
            if _digest(before) != record['pre_hash'] or (before is not None and len(before) > MAX_CONFIG_BYTES):
                raise ValueError()
            mode = record['mode']
            if (before is None and mode is not None) or (before is not None and (type(mode) is not int or not 0 <= mode <= 0o7777)):
                raise ValueError()
            project = _canonical_project(record['project'])
            post_hash = record['post_hash']
            if not isinstance(post_hash, str) or len(post_hash) != 64:
                raise ValueError()
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise NativeProfileError('Invalid backup record.') from exc
        fd = _parent(project, record['agent'])
        try:
            name = _TARGETS[record['agent']][1]
            current, current_mode = _read(fd, name)
            if _digest(current) != post_hash or current_mode != (mode if mode is not None else 0o600):
                raise NativeProfileError('Settings changed after apply; undo refused.')
            if before is None:
                # Recheck immediately before unlinking the new file.
                check, checked_mode = _read(fd, name)
                if _digest(check) != post_hash or checked_mode != current_mode:
                    raise NativeProfileError('Settings changed after apply; undo refused.')
                os.unlink(name, dir_fd=fd)
                os.fsync(fd)
            else:
                _replace(fd, name, before, mode, post_hash, current_mode)
            return {'status': 'undone', 'backup_id': backup_id}
        finally:
            os.close(fd)
