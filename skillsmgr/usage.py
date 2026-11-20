"""Opt-in, local-only skill-use counts from structured agent transcripts.

Transcript formats are private vendor details. Unknown or incomplete input is
reported as unknown coverage; it is never treated as evidence of no use.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import time
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

from .atomic_io import atomic_write_text, mutation_lock, register_lock_root
from .file_reads import read_regular_file
from .path_safety import mkdir_private
from . import paths as _paths

PARSER_VERSION = "usage-1"
RETENTION_DAYS = 400
MAX_LINE_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_SCAN_BYTES = 256 * 1024 * 1024
MAX_FILES = 10_000
MAX_SECONDS = 5.0
MAX_EVENTS = 100_000
MAX_CACHE_BYTES = 64 * 1024 * 1024
MAX_NAME_LEN = 64
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?::[a-z0-9]+(?:-[a-z0-9]+)*)?$")
_AGENTS = ("claude-code", "codex", "commandcode", "gemini", "opencode")
_ISO = re.compile(r"^\d{4}-\d\d-\d\d(?:T|$)")


class UsageError(ValueError):
    """A clean, user-displayable usage configuration or cache error."""


def _data_dir(data_dir: Path | str | None) -> Path:
    return Path(data_dir) if data_dir is not None else _paths.data_dir()


def _utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _utc_day(value: object) -> str | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            if not _ISO.match(value):
                return None
            parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        else:
            parsed = _dt.datetime.fromtimestamp(float(value) / (1000 if value > 10**11 else 1), _dt.timezone.utc)
        return parsed.astimezone(_dt.timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _roots(home: Path | None = None) -> dict[str, Path]:
    """Resolve roots from agent conventions without opening any of them."""
    base = home or _paths.home_dir()
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(base / ".claude"))).expanduser()
    codex = Path(os.environ.get("CODEX_HOME", str(base / ".codex"))).expanduser()
    return {
        "claude-code": claude / "projects",
        "codex": codex / "sessions",
        "commandcode": base / ".commandcode" / "projects",
        "gemini": base / ".gemini" / "tmp",
        "opencode": base / ".local" / "share" / "opencode" / "opencode.db",
    }


def _usage_dir(data_dir: Path | str | None) -> Path:
    return _data_dir(data_dir) / "usage"


def _ensure_private_usage_dir(directory: Path, *, create: bool = False, tighten: bool = False) -> bool:
    if create:
        mkdir_private(directory)
    try:
        info = os.lstat(directory)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise UsageError("usage data path must be a plain directory")
    getuid = getattr(os, "getuid", None)
    if getuid is not None and info.st_uid != getuid():
        raise UsageError("usage data directory is owned by another user")
    if os.name != "nt" and info.st_mode & 0o077:
        if tighten:
            os.chmod(directory, 0o700)
        else:
            raise UsageError("usage data directory permissions must be 0700")
    return True


def _read_json(path: Path, limit: int = 8 * 1024 * 1024) -> dict:
    try:
        raw = read_regular_file(path, limit, follow_symlinks=False)
        obj = json.loads(raw.decode("utf-8"))
        if isinstance(obj, dict):
            return obj
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        pass
    return {}


def _write_json(path: Path, value: dict) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if len(payload.encode("utf-8")) > MAX_CACHE_BYTES:
        raise UsageError("usage cache exceeds its size limit; existing counts were preserved")
    mkdir_private(path.parent)
    atomic_write_text(path, payload)


def _load_consent(directory: Path) -> dict:
    obj = _read_json(directory / "consent.json")
    roots = obj.get("roots")
    if obj.get("version") != 1 or not isinstance(roots, dict):
        return {}
    return {agent: root for agent, root in roots.items()
            if agent in _AGENTS and isinstance(root, str) and Path(root).is_absolute()}


def consent_state(data_dir: Path | str | None = None) -> dict:
    """Return consent metadata only; this function never opens transcript roots."""
    directory = _usage_dir(data_dir)
    roots = _load_consent(directory) if _ensure_private_usage_dir(directory) else {}
    return {"enabled": bool(roots), "agents": sorted(roots), "roots": roots}


def _enable_unlocked(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
                     *, home: Path | None = None) -> dict:
    """Grant CLI consent for exact configured transcript roots, without reading them."""
    selected = list(_AGENTS if not agents else agents)
    if not selected or len(set(selected)) != len(selected) or any(a not in _AGENTS for a in selected):
        raise UsageError("choose one or more supported agents: " + ", ".join(_AGENTS))
    resolved = _roots(home)
    roots = {agent: str(resolved[agent].absolute()) for agent in selected}
    directory = _usage_dir(data_dir)
    _ensure_private_usage_dir(directory, create=True, tighten=True)
    previous = _load_consent(directory)
    cache = _load_cache(directory)
    bindings = cache.setdefault("root_bindings", {})
    for agent, new_root in roots.items():
        binding = hashlib.sha256(new_root.encode("utf-8")).hexdigest()
        previous_binding = bindings.get(agent)
        data_exists = any(key.startswith(agent + "\0") for key in cache["counts"])
        changed = previous_binding != binding if previous_binding is not None else (
            previous.get(agent) != new_root or data_exists
        )
        if changed:
            prefix = agent + "\0"
            cache["counts"] = {key: value for key, value in cache["counts"].items()
                                if not key.startswith(prefix)}
            cache["seen"] = {key: value for key, value in cache["seen"].items()
                              if not key.startswith(prefix)}
            cache["watermarks"] = {key: value for key, value in cache["watermarks"].items()
                                    if not key.startswith(prefix)}
            cache["coverage"].pop(agent, None)
        bindings[agent] = binding
    roots = {**previous, **roots}
    cache.setdefault("version", 1)
    cache.setdefault("counts", {})
    cache.setdefault("watermarks", {})
    cache.setdefault("seen", {})
    cache.setdefault("coverage", {})
    _write_json(directory / "counts.json", cache)
    _write_json(directory / "consent.json", {"version": 1, "enabled_at": _utc_now().isoformat(), "roots": roots})
    return {"enabled": True, "agents": sorted(roots), "roots": roots}


def enable(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
           *, home: Path | None = None) -> dict:
    root = _data_dir(data_dir)
    register_lock_root(root)
    with mutation_lock(root / "usage-state"):
        return _enable_unlocked(root, agents, home=home)


def _disable_unlocked(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
                      *, purge: bool = False) -> dict:
    """Revoke consent for selected agents. Purge removes all cached counts."""
    directory = _usage_dir(data_dir)
    if purge:
        if agents is not None:
            raise UsageError("--purge cannot be combined with an agent selector")
        if _ensure_private_usage_dir(directory):
            shutil.rmtree(directory)
        return {"enabled": False, "purged": True}
    _ensure_private_usage_dir(directory)
    current = _load_consent(directory)
    if agents is None:
        current.clear()
    else:
        if any(agent not in _AGENTS for agent in agents):
            raise UsageError("unsupported agent requested")
        for agent in agents:
            current.pop(agent, None)
    path = directory / "consent.json"
    if current:
        _write_json(path, {"version": 1, "enabled_at": _utc_now().isoformat(), "roots": current})
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return {"enabled": bool(current), "agents": sorted(current), "purged": False}


def disable(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
            *, purge: bool = False) -> dict:
    root = _data_dir(data_dir)
    register_lock_root(root)
    with mutation_lock(root / "usage-state"):
        return _disable_unlocked(root, agents, purge=purge)


def _load_cache(directory: Path) -> dict:
    path = directory / "counts.json"
    try:
        raw = read_regular_file(path, MAX_CACHE_BYTES, follow_symlinks=False)
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("cache must be an object")
    except FileNotFoundError:
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {}, "root_bindings": {}}
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    if obj.get("version") != 1:
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    obj.setdefault("root_bindings", {})
    for key in ("counts", "watermarks", "seen", "coverage", "root_bindings"):
        if not isinstance(obj.get(key), dict):
            return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                    "cache_status": "invalid"}
    if any(not isinstance(key, str) or not isinstance(value, dict) or value.get("agent") not in _AGENTS
           or not isinstance(value.get("name"), str) or _valid_name(value.get("name")) is None
           or key != value.get("agent", "") + "\0" + value.get("name", "")
           or not isinstance(value.get("by_day"), dict) for key, value in obj["counts"].items()):
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    for value in obj["counts"].values():
        for day, daily in value["by_day"].items():
            if not isinstance(day, str) or _utc_day(day) is None:
                return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                        "cache_status": "invalid"}
            if isinstance(daily, int) and not isinstance(daily, bool):
                continue
            if not isinstance(daily, dict) or any(not isinstance(n, int) or isinstance(n, bool) or n < 0
                                                  for n in daily.values()):
                return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                        "cache_status": "invalid"}
    if any(not isinstance(key, str) or "\0" not in key
           or key.split("\0", 1)[0] not in _AGENTS
           or not re.fullmatch(r"[0-9a-f]{64}", key.split("\0", 1)[1])
           or not isinstance(day, str) or _utc_day(day) is None
           for key, day in obj["seen"].items()):
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    if any(agent not in _AGENTS or not isinstance(digest, str)
           or not re.fullmatch(r"[0-9a-f]{64}", digest)
           for agent, digest in obj["root_bindings"].items()):
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    if any(not isinstance(key, str) or "\0" not in key
           or key.split("\0", 1)[0] not in _AGENTS
           or not re.fullmatch(r"[0-9a-f]{64}", key.split("\0", 1)[1])
           or not isinstance(value, dict)
           for key, value in obj["watermarks"].items()):
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    return obj


def _valid_name(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > MAX_NAME_LEN + 7 or not _NAME.fullmatch(value):
        return None
    return value


def _known_skill_roots(home: Path | None = None) -> tuple[Path, ...]:
    base = home or _paths.home_dir()
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(base / ".claude"))).expanduser()
    codex = Path(os.environ.get("CODEX_HOME", str(base / ".codex"))).expanduser()
    return (base / ".agents" / "skills", claude / "skills", codex / "skills",
            base / ".gemini" / "skills", base / ".commandcode" / "skills",
            base / ".cursor" / "skills", base / ".opencode" / "skills")


def _event(agent: str, row: dict, *, home: Path | None = None) -> tuple[str, str, str, str] | None:
    """Extract a single event from known structured record shapes."""
    message = row.get("message")
    timestamp = (row.get("timestamp") or row.get("created_at") or row.get("time")
                 or (message.get("timestamp") if isinstance(message, dict) else None))
    day = _utc_day(timestamp)
    if day is None:
        return None
    if agent == "claude-code":
        if not isinstance(message, dict) or message.get("role") != "assistant":
            return None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            return None
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "tool_use" or part.get("name") != "Skill":
                continue
            inp = part.get("input")
            name = _valid_name(inp.get("skill") if isinstance(inp, dict) else None)
            ident = part.get("id")
            if name and isinstance(ident, str) and ident:
                return name, day, "explicit", ident[:256]
    elif agent == "commandcode":
        if not isinstance(message, dict) or message.get("role") != "assistant":
            return None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            return None
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "tool_use" or part.get("name") != "activate_skill":
                continue
            inp = part.get("input")
            name = _valid_name(inp.get("name") if isinstance(inp, dict) else None)
            ident = part.get("id")
            if name and isinstance(ident, str) and ident:
                return name, day, "explicit", ident[:256]
    elif agent == "codex":
        items = message.get("content") if isinstance(message, dict) else row.get("content")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") in ("text", "input_text") and isinstance(message, dict) and message.get("role") == "user":
                    fragment = item.get("text")
                    match = re.search(
                        r"^\s*<skill>\s*<name>([a-z0-9]+(?:-[a-z0-9]+)*)</name>\s*<path>([^<\r\n]{1,2048})</path>",
                        fragment or "",
                    )
                    if match:
                        name = _valid_name(match.group(1))
                        candidate = Path(match.group(2))
                        known_roots = _known_skill_roots(home)
                        ident = item.get("call_id") or item.get("id") or message.get("id") or row.get("id")
                        if (name and candidate.is_absolute()
                                and any(candidate.is_relative_to(root) for root in known_roots)
                                and isinstance(ident, str) and ident):
                            return name, day, "explicit", ident[:256]
                if item.get("type") == "exec" or item.get("kind") == "exec_command":
                    path = item.get("path")
                    if isinstance(path, str) and path.endswith("/SKILL.md"):
                        # Count only structured paths inside conventional skill roots.
                        candidate = Path(path)
                        known_roots = _known_skill_roots(home)
                        if not any(candidate.is_relative_to(root) for root in known_roots):
                            continue
                        match = re.search(r"/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md$", path)
                        name = _valid_name(match.group(1)) if match else None
                        ident = item.get("call_id") or item.get("id")
                        if name and isinstance(ident, str) and ident:
                            return name, day, "inferred", ident[:256]
    elif agent == "gemini":
        record = message if isinstance(message, dict) else row
        if record.get("type") != "gemini":
            return None
        calls = record.get("toolCalls")
        if isinstance(calls, list):
            for call in calls:
                if not isinstance(call, dict) or call.get("name") != "activate_skill":
                    continue
                args = call.get("args") or call.get("input")
                name = _valid_name(args.get("name") if isinstance(args, dict) else None)
                ident = call.get("id") or call.get("callId")
                if name and isinstance(ident, str) and ident:
                    return name, day, "explicit", ident[:256]
    return None


def _events(agent: str, row: dict, *, home: Path | None = None) -> list[tuple[str, str, str, str]]:
    """Extract all known structured skill calls in a transcript record."""
    if isinstance(row, list):
        return [event for item in row if isinstance(item, dict) for event in _events(agent, item, home=home)]
    if agent == "gemini" and isinstance(row, dict) and isinstance(row.get("messages"), list):
        return [event for item in row["messages"] if isinstance(item, dict)
                for event in _events(agent, item, home=home)]
    if agent == "codex" and isinstance(row, dict) and row.get("type") == "response_item":
        payload = row.get("payload")
        if not isinstance(payload, dict):
            return []
        if payload.get("type") == "message":
            normalized = dict(row, message=payload)
            normalized.pop("type", None)
            return _events(agent, normalized, home=home)
        if payload.get("type") == "function_call" and payload.get("name") == "exec_command":
            return _codex_exec_events(row, payload, home=home)
        return []
    message = row.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if agent in ("claude-code", "commandcode") and isinstance(content, list):
        events = []
        for part in content:
            if isinstance(part, dict):
                reduced = dict(row)
                reduced["message"] = dict(message, content=[part])
                found = _event(agent, reduced, home=home)
                if found:
                    events.append(found)
        return events
    if agent == "codex" and isinstance(content, list):
        events = []
        for item in content:
            if isinstance(item, dict):
                reduced = dict(row)
                reduced["message"] = dict(message, content=[item])
                found = _event(agent, reduced, home=home)
                if found:
                    events.append(found)
        return events
    calls = message.get("toolCalls") if isinstance(message, dict) else row.get("toolCalls")
    if agent == "gemini" and isinstance(calls, list):
        events = []
        for call in calls:
            if isinstance(call, dict):
                reduced = dict(row)
                reduced["message"] = dict(message, toolCalls=[call]) if isinstance(message, dict) else dict(row, toolCalls=[call])
                found = _event(agent, reduced, home=home)
                if found:
                    events.append(found)
        return events
    found = _event(agent, row, home=home)
    return [found] if found else []


def _codex_exec_events(row: dict, payload: dict, *, home: Path | None = None) -> list[tuple[str, str, str, str]]:
    """Count only structured Codex exec calls that read a known skill file."""
    raw_args = payload.get("arguments")
    if not isinstance(raw_args, str):
        return []
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        return []
    command = (args.get("command") or args.get("cmd")) if isinstance(args, dict) else None
    if isinstance(command, list):
        words = [word for word in command if isinstance(word, str)]
    elif isinstance(command, str):
        try:
            import shlex
            words = shlex.split(command)
        except ValueError:
            return []
    else:
        return []
    if not words or Path(words[0]).name not in {"cat", "head", "tail", "less", "more"}:
        return []
    call_id = payload.get("call_id")
    day = _utc_day(row.get("timestamp"))
    if not isinstance(call_id, str) or not call_id or day is None:
        return []
    roots = _known_skill_roots(home)
    events = []
    for word in words[1:]:
        candidate = Path(word)
        if not candidate.is_absolute() or candidate.name != "SKILL.md":
            continue
        if not any(candidate.is_relative_to(root) for root in roots):
            continue
        name = _valid_name(candidate.parent.name)
        if name:
            events.append((name, day, "inferred", call_id[:256]))
    return events


def _candidate_files(agent: str, root: Path, deadline: float) -> tuple[list[Path], str]:
    try:
        info = os.lstat(root)
    except FileNotFoundError:
        return [], "missing"
    except OSError:
        return [], "partial"
    if stat.S_ISLNK(info.st_mode):
        return [], "partial"
    if agent == "opencode":
        return ([root], "available") if stat.S_ISREG(info.st_mode) else ([], "partial")
    if not stat.S_ISDIR(info.st_mode):
        return [], "partial"
    files: list[Path] = []
    stack = [root]
    incomplete = False
    while stack:
        if len(files) + len(stack) >= MAX_FILES or time.monotonic() >= deadline:
            incomplete = True
            break
        directory = stack.pop()
        try:
            entries = []
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    if len(entries) >= MAX_FILES:
                        incomplete = True
                        break
                    entries.append(entry)
            entries.sort(key=lambda entry: entry.name)
        except OSError:
            incomplete = True
            continue
        for entry in entries:
            if len(files) + len(stack) >= MAX_FILES or time.monotonic() >= deadline:
                incomplete = True
                return files, "partial"
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError:
                incomplete = True
                continue
            if stat.S_ISLNK(mode):
                incomplete = True
                continue
            path = Path(entry.path)
            if stat.S_ISDIR(mode):
                stack.append(path)
            elif stat.S_ISREG(mode) and entry.name.endswith(".jsonl"):
                files.append(path)
            elif stat.S_ISREG(mode) and entry.name.endswith(".json"):
                if agent == "gemini":
                    files.append(path)
                else:
                    incomplete = True
    return files, "partial" if incomplete else "available"


def _file_id(path: Path) -> str:
    return hashlib.sha256(os.fsencode(str(path))).hexdigest()


def _head_hash(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError("not a regular file")
        return hashlib.sha256(os.read(fd, 4096)).hexdigest()
    finally:
        os.close(fd)


def _read_lines(path: Path, offset: int, per_file_left: int, scan_left: int) -> tuple[list[tuple[dict | list, int]], int, int, bool, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError("not a regular file")
        if info.st_size > MAX_FILE_BYTES or info.st_size > offset + min(per_file_left, scan_left):
            raise OverflowError("bounded scan limit reached")
        start = offset if offset <= info.st_size else 0
        os.lseek(fd, start, os.SEEK_SET)
        result = []
        consumed = 0
        new_offset = start
        incomplete = False
        oversized = False
        quota = min(per_file_left, scan_left, info.st_size - start)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            while consumed < quota:
                line_start = new_offset
                raw = handle.readline(min(MAX_LINE_BYTES + 1, quota - consumed))
                if not raw:
                    break
                consumed += len(raw)
                if not raw.endswith(b"\n"):
                    if len(raw) > MAX_LINE_BYTES:
                        oversized = True
                        # Drain an oversized record without retaining it. If the
                        # cap is reached first, leave its starting offset intact.
                        complete = False
                        while consumed < quota:
                            chunk = handle.readline(min(65536, quota - consumed))
                            if not chunk:
                                break
                            consumed += len(chunk)
                            if chunk.endswith(b"\n"):
                                complete = True
                                break
                        if not complete:
                            incomplete = True
                            new_offset = line_start
                            break
                        new_offset = start + consumed
                        continue
                    # The final record may be in the middle of an append. Keep
                    # it unconsumed so the next scan can finish it.
                    incomplete = True
                    new_offset = line_start
                    break
                new_offset = start + consumed
                if len(raw) <= MAX_LINE_BYTES and any(token in raw for token in (
                    b'"Skill"', b'activate_skill', b'"tool":"skill"',
                    b'"tool": "skill"', b'"type":"skill"', b'<skill>', b'SKILL.md')):
                    try:
                        obj = json.loads(raw)
                        if isinstance(obj, (dict, list)):
                            result.append((obj, new_offset))
                    except (json.JSONDecodeError, UnicodeError):
                        incomplete = True
        incomplete = incomplete or (start + consumed < info.st_size)
        return result, new_offset, consumed, incomplete or oversized, info
    finally:
        os.close(fd)


def _read_gemini_json(path: Path, scan_left: int) -> tuple[list[tuple[dict | list, int]], int, bool, os.stat_result]:
    before = os.lstat(path)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise OSError("not a regular file")
    if before.st_size > MAX_FILE_BYTES or before.st_size > scan_left:
        raise OverflowError("bounded scan limit reached")
    raw = read_regular_file(path, MAX_FILE_BYTES, follow_symlinks=False)
    after = os.lstat(path)
    if after.st_ino != before.st_ino or after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns:
        return [], len(raw), True, after
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return [], len(raw), True, after
    if not isinstance(obj, (dict, list)):
        return [], len(raw), True, after
    return [(obj, len(raw))], len(raw), False, after


def _scan_opencode(path: Path, cache: dict, counts: dict, seen: dict, deadline: float,
                   scan_left: int) -> tuple[dict, bool, int]:
    """Read the OpenCode part.data projection from a read-only SQLite URI."""
    state = {"status": "unknown", "files_seen": 0, "events": 0, "parser_versions": [], "earliest_event": None}
    if time.monotonic() >= deadline:
        return state, True, 0
    uri = "file:" + quote(str(path), safe="/") + "?mode=ro&immutable=1"
    conn = None
    try:
        before = os.lstat(path)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise OSError("not a regular database file")
        file_id = "opencode\0" + _file_id(path)
        old = cache["watermarks"].get(file_id, {})
        same_db = old.get("inode") == before.st_ino and before.st_size >= old.get("size", 0)
        if same_db and before.st_size == old.get("size") and before.st_mtime_ns != old.get("mtime_ns"):
            same_db = False
        after_rowid = old.get("rowid", 0) if same_db else 0
        if not isinstance(after_rowid, int) or after_rowid < 0:
            after_rowid = 0
        conn = sqlite3.connect(uri, uri=True, timeout=0.1)
        conn.execute("PRAGMA query_only=ON")
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        data_bytes = 0
        last_rowid = after_rowid
        # Small explicit projection and a literal prefilter; no table dump or writes.
        cursor = conn.execute(
            "SELECT rowid, data FROM part WHERE rowid > ? AND data LIKE '%\"tool\":\"skill\"%' ORDER BY rowid LIMIT ?",
            (after_rowid, MAX_EVENTS + 1),
        )
        for rowid, raw in cursor:
            if time.monotonic() >= deadline or data_bytes >= scan_left or state["events"] >= MAX_EVENTS:
                state["status"] = "partial"
                break
            encoded = raw.encode("utf-8", "replace") if isinstance(raw, str) else b""
            if data_bytes + len(encoded) > scan_left:
                state["status"] = "partial"
                break
            last_rowid = rowid
            data_bytes += len(encoded)
            if len(encoded) > MAX_LINE_BYTES:
                state["status"] = "partial"
                continue
            try:
                obj = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                state["status"] = "partial"
                continue
            tool = obj.get("tool") if isinstance(obj, dict) and obj.get("type") == "tool" else None
            state_data = obj.get("state") if isinstance(obj, dict) else None
            inp = state_data.get("input") if isinstance(state_data, dict) else None
            name = _valid_name(inp.get("name") if isinstance(inp, dict) else None)
            ident = obj.get("callID") if isinstance(obj, dict) else None
            # OpenCode timestamps may be top-level or nested. Unknown shapes remain no evidence.
            stamp = obj.get("time") or obj.get("createdAt") or obj.get("timestamp")
            if isinstance(stamp, dict):
                stamp = stamp.get("start") or stamp.get("created")
            day = _utc_day(stamp)
            if tool != "skill" or not name or day is None or not isinstance(ident, str):
                continue
            digest = "opencode\0" + hashlib.sha256(ident.encode()).hexdigest()
            if digest in seen:
                continue
            seen[digest] = day
            _add_event(counts, "opencode", name, day, "explicit")
            state["events"] += 1
            state["earliest_event"] = min(state["earliest_event"] or day, day)
        state["files_seen"] = 1
        after = os.lstat(path)
        if (stat.S_ISLNK(after.st_mode) or after.st_ino != before.st_ino
                or after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns):
            state["status"] = "partial"
        cache["watermarks"][file_id] = {"size": after.st_size, "mtime_ns": after.st_mtime_ns,
                                        "inode": after.st_ino, "rowid": last_rowid}
        state["parser_versions"] = [PARSER_VERSION]
        if state["status"] == "unknown":
            state["status"] = "available"
        return state, state["status"] != "available", data_bytes
    except (sqlite3.Error, OSError):
        state["status"] = "partial"
        return state, True, 0
    finally:
        if conn is not None:
            conn.close()


def _add_event(counts: dict, agent: str, name: str, day: str, kind: str) -> None:
    key = agent + "\0" + name
    item = counts.setdefault(key, {"agent": agent, "name": name, "explicit": 0, "inferred": 0, "first_seen": day, "last_seen": day, "by_day": {}})
    item[kind] = int(item.get(kind, 0)) + 1
    item["by_day"].setdefault(day, {"explicit": 0, "inferred": 0})
    if isinstance(item["by_day"][day], int):  # upgrade an early cache shape safely
        item["by_day"][day] = {"explicit": item["by_day"][day], "inferred": 0}
    item["by_day"][day][kind] = int(item["by_day"][day].get(kind, 0)) + 1
    item["first_seen"] = min(item.get("first_seen", day), day)
    item["last_seen"] = max(item.get("last_seen", day), day)


def _scan_text_agent(agent: str, root: Path, cache: dict, counts: dict, seen: dict,
                     deadline: float, scan_left: int, *, home: Path | None = None) -> tuple[dict, bool, int]:
    files, walk_status = _candidate_files(agent, root, deadline)
    state = {"status": walk_status, "files_seen": 0, "events": 0, "parser_versions": [PARSER_VERSION], "earliest_event": None}
    bytes_read = 0
    watermarks = cache["watermarks"]
    for path in files:
        if time.monotonic() >= deadline or state["files_seen"] >= MAX_FILES or state["events"] >= MAX_EVENTS:
            state["status"] = "partial"
            break
        fid = agent + "\0" + _file_id(path)
        try:
            before = os.lstat(path)
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
                state["status"] = "partial"
                continue
            old = watermarks.get(fid, {})
            head_hash = _head_hash(path)
            unchanged = (old.get("size") == before.st_size and old.get("mtime_ns") == before.st_mtime_ns
                         and old.get("inode") == getattr(before, "st_ino", None)
                         and old.get("head_hash") == head_hash
                         and old.get("offset", 0) >= before.st_size)
            state["files_seen"] += 1
            if unchanged:
                continue
            offset = old.get("offset", 0) if old.get("inode") == getattr(before, "st_ino", None) and before.st_size >= old.get("offset", 0) else 0
            if not isinstance(offset, int) or offset < 0:
                offset = 0
            if agent == "gemini" and path.suffix == ".json":
                rows, consumed, incomplete, opened = _read_gemini_json(path, scan_left - bytes_read)
                new_offset = opened.st_size
            else:
                rows, new_offset, consumed, incomplete, opened = _read_lines(
                    path, offset, MAX_FILE_BYTES, scan_left - bytes_read
                )
            bytes_read += consumed
            if opened.st_ino != before.st_ino or opened.st_size != before.st_size or opened.st_mtime_ns != before.st_mtime_ns:
                state["status"] = "partial"
                continue
            for row, end_offset in rows:
                for event in _events(agent, row, home=home):
                    name, day, kind, ident = event
                    digest = agent + "\0" + hashlib.sha256(ident.encode()).hexdigest()
                    if digest in seen:
                        continue
                    if len(seen) >= MAX_EVENTS:
                        state["status"] = "partial"
                        break
                    seen[digest] = day
                    _add_event(counts, agent, name, day, kind)
                    state["events"] += 1
                    state["earliest_event"] = min(state["earliest_event"] or day, day)
            watermarks[fid] = {"size": opened.st_size, "mtime_ns": opened.st_mtime_ns,
                               "inode": getattr(opened, "st_ino", None), "offset": new_offset,
                               "head_hash": head_hash}
            if incomplete or state["status"] == "partial":
                state["status"] = "partial"
            if bytes_read >= scan_left:
                state["status"] = "partial"
                break
        except (OSError, ValueError, OverflowError):
            state["status"] = "partial"
    return state, state["status"] != "available", bytes_read


def _report_unlocked(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
                     *, days: int = 90, refresh: bool = False, home: Path | None = None) -> dict:
    """Return skill counts and per-agent scan coverage, reading only consented roots."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 1 or days > 400:
        raise UsageError("days must be between 1 and 400")
    directory = _usage_dir(data_dir)
    exists = _ensure_private_usage_dir(directory)
    consents = _load_consent(directory) if exists else {}
    cache = _load_cache(directory)
    latest_consents = _load_consent(directory) if exists else {}
    if latest_consents != consents:
        consents = latest_consents
    counts, seen = cache["counts"], cache["seen"]
    requested = list(agents) if agents else list(_AGENTS)
    if any(agent not in _AGENTS for agent in requested):
        raise UsageError("unsupported agent requested")
    now = _utc_now()
    cutoff = (now.date() - _dt.timedelta(days=RETENTION_DAYS - 1)).isoformat()
    for item in counts.values():
        item["by_day"] = {day: counts_by_kind for day, counts_by_kind in item.get("by_day", {}).items()
                           if isinstance(day, str) and day >= cutoff}
    seen = {key: day for key, day in seen.items() if isinstance(day, str) and day >= cutoff}
    deadline = time.monotonic() + MAX_SECONDS
    bytes_left = MAX_SCAN_BYTES
    coverage = {}
    for agent in requested:
        if agent not in consents:
            coverage[agent] = {"status": "no-consent", "files_seen": 0, "events": 0,
                               "parser_versions": [], "earliest_event": None,
                               "coverage_window_start": None, "parser_coverage": "unavailable"}
            continue
        root = Path(consents[agent])
        root_state = _roots(home).get(agent)
        if root_state is not None and str(root_state.absolute()) != str(root):
            coverage[agent] = {"status": "configuration-changed", "files_seen": 0, "events": 0,
                               "parser_versions": [], "earliest_event": None,
                               "coverage_window_start": None, "parser_coverage": "unavailable"}
            continue
        if not refresh:
            coverage[agent] = cache.get("coverage", {}).get(agent, {
                "status": "not-scanned", "files_seen": 0, "events": 0,
                "parser_versions": [], "earliest_event": None,
            })
            if cache.get("cache_status") == "invalid":
                coverage[agent] = {"status": "cache-invalid", "files_seen": 0, "events": 0,
                                   "parser_versions": [], "earliest_event": None,
                                   "coverage_window_start": None, "parser_coverage": "unavailable"}
            continue
        if agent == "opencode":
            state, partial, consumed = _scan_opencode(root, cache, counts, seen, deadline, bytes_left)
        else:
            state, partial, consumed = _scan_text_agent(
                agent, root, cache, counts, seen, deadline, bytes_left, home=home
            )
        bytes_left = max(0, bytes_left - consumed)
        if partial:
            state["status"] = "partial"
        state["coverage_level"] = "known-structured-events-only"
        state["parser_coverage"] = "partial-undocumented-format"
        state["coverage_window_start"] = None
        if cache.get("cache_status") == "invalid":
            state["status"] = "partial"
            state["cache_recovered_from_transcripts"] = True
        coverage[agent] = state
        cache["coverage"][agent] = state
    # Only report aggregates for requested agents; never include IDs, paths, text, or arguments.
    min_day = (now.date() - _dt.timedelta(days=days - 1)).isoformat()
    rows = []
    active_agents = {agent for agent, root in consents.items()
                     if _roots(home).get(agent) is not None
                     and str(_roots(home)[agent].absolute()) == str(root)}
    for item in counts.values():
        if item.get("agent") not in requested or item.get("agent") not in active_agents:
            continue
        by_day = {day: n for day, n in item.get("by_day", {}).items() if day >= min_day}
        explicit = sum((n.get("explicit", 0) if isinstance(n, dict) else n) for n in by_day.values())
        inferred = sum(n.get("inferred", 0) for n in by_day.values() if isinstance(n, dict))
        rows.append({"agent": item["agent"], "name": item["name"],
                     "explicit": explicit, "inferred": inferred,
                     "by_day": {day: sum(n.values()) if isinstance(n, dict) else n for day, n in by_day.items()},
                     "first_seen": item.get("first_seen"), "last_seen": item.get("last_seen")})
    rows.sort(key=lambda row: (row["agent"], row["name"]))
    # Store counts by kind explicitly for correct day-bucket rollups.
    cache["counts"] = counts
    cache["seen"] = seen
    if consents and refresh:
        _ensure_private_usage_dir(directory, create=True)
        cache.pop("cache_status", None)
        _write_json(directory / "counts.json", cache)
    return {"consented": sorted(consents), "coverage": coverage, "counts": rows,
            "days": days, "parser_version": PARSER_VERSION}


def report(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
           *, days: int = 90, refresh: bool = False, home: Path | None = None) -> dict:
    if not refresh:
        return _report_unlocked(data_dir, agents, days=days, refresh=False, home=home)
    root = _data_dir(data_dir)
    register_lock_root(root)
    with mutation_lock(root / "usage-state"):
        return _report_unlocked(root, agents, days=days, refresh=True, home=home)


__all__ = ["UsageError", "enable", "disable", "report", "consent_state"]
