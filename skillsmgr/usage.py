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
import shlex
import shutil
import sqlite3
import stat
import time
from contextlib import closing
from pathlib import Path
from typing import Iterator, Sequence

from .atomic_io import atomic_write_text, mutation_lock, register_lock_root
from .file_reads import read_regular_file
from .path_safety import mkdir_private
from .review_artifacts import reject_symlink_ancestors
from . import paths as _paths

PARSER_VERSION = "usage-4"
RETENTION_DAYS = 400
MAX_LINE_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_SCAN_BYTES = 256 * 1024 * 1024
MAX_FILES = 10_000
MAX_WALK_ENTRIES = 100_000
MAX_AGENT_WATERMARKS = 20_000
MAX_SECONDS = 5.0
MAX_EVENTS = 100_000
MAX_CACHE_BYTES = 64 * 1024 * 1024
MAX_NAME_LEN = 64
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?::[a-z0-9]+(?:-[a-z0-9]+)*)?$")
_AGENTS = ("claude-code", "codex", "commandcode", "gemini", "opencode")
_ISO = re.compile(r"^\d{4}-\d\d-\d\d(?:T|$)")
_WINDOWS = os.name == "nt"
# Windows text-mode descriptors would translate CRLF and invalidate byte offsets.
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)


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


def _opencode_database(home: Path) -> Path | None:
    filename = os.environ.get("OPENCODE_DB", "opencode.db")
    if not filename or filename == ":memory:":
        return None
    path = Path(filename)
    if path.is_absolute():
        return Path(os.path.abspath(path))
    configured_data = os.environ.get("XDG_DATA_HOME")
    data = Path(configured_data) if configured_data else home / ".local" / "share"
    if not data.is_absolute():
        # A relative base could depend on the OpenCode process's CWD.
        return None
    return Path(os.path.abspath(data / "opencode" / path))


def _roots(home: Path | None = None) -> dict[str, Path]:
    """Resolve roots from agent conventions without opening any of them."""
    base = home or _paths.home_dir()
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(base / ".claude"))).expanduser()
    codex = Path(os.environ.get("CODEX_HOME", str(base / ".codex"))).expanduser()
    roots = {
        "claude-code": claude / "projects",
        "codex": codex / "sessions",
        "commandcode": base / ".commandcode" / "projects",
        "gemini": base / ".gemini" / "tmp",
    }
    if (database := _opencode_database(base)) is not None:
        roots["opencode"] = database
    return roots


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
    except (OSError, ValueError, RecursionError):
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


def _root_binding(root: str) -> str:
    return hashlib.sha256(os.fsencode(root)).hexdigest()


def _clear_agent_evidence(cache: dict, agent: str) -> None:
    prefix = agent + "\0"
    for field in ("counts", "seen", "watermarks"):
        records = cache[field]
        for key in list(records):
            if key.startswith(prefix):
                del records[key]
    cache["coverage"].pop(agent, None)
    cache.get("walk_positions", {}).pop(agent, None)


def _enable_unlocked(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
                     *, home: Path | None = None) -> dict:
    """Grant CLI consent for exact configured transcript roots, without reading them."""
    selected = list(_AGENTS if not agents else agents)
    if not selected or len(set(selected)) != len(selected) or any(a not in _AGENTS for a in selected):
        raise UsageError("choose one or more supported agents: " + ", ".join(_AGENTS))
    resolved = _roots(home)
    if any(agent not in resolved for agent in selected):
        raise UsageError("OpenCode has no unambiguous on-disk database in the current environment")
    roots = {agent: str(resolved[agent].absolute()) for agent in selected}
    directory = _usage_dir(data_dir)
    _ensure_private_usage_dir(directory, create=True, tighten=True)
    previous = _load_consent(directory)
    cache = _load_cache(directory)
    bindings = cache.setdefault("root_bindings", {})
    for agent, new_root in roots.items():
        binding = _root_binding(new_root)
        previous_binding = bindings.get(agent)
        data_exists = any(key.startswith(agent + "\0") for key in cache["counts"])
        changed = previous_binding != binding if previous_binding is not None else (
            previous.get(agent) != new_root or data_exists
        )
        if changed:
            _clear_agent_evidence(cache, agent)
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


def _is_cache_day(value):
    return isinstance(value, str) and _utc_day(value) == value


def _is_cached_count(value):
    return type(value) is int and 0 <= value < 2**63


def _valid_daily_count(value):
    # The first cache format stored only an integer explicit count.
    return _is_cached_count(value) or (
        isinstance(value, dict) and value.keys() <= {"explicit", "inferred"}
        and all(_is_cached_count(count) for count in value.values())
    )


def _load_cache(directory: Path) -> dict:
    path = directory / "counts.json"
    try:
        raw = read_regular_file(path, MAX_CACHE_BYTES, follow_symlinks=False)
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("cache must be an object")
    except FileNotFoundError:
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {}, "root_bindings": {}}
    except (OSError, ValueError, RecursionError):
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
    if any(not _is_cache_day(day) or not _valid_daily_count(daily)
           for item in obj["counts"].values() for day, daily in item["by_day"].items()):
        return {"version": 1, "counts": {}, "watermarks": {}, "seen": {}, "coverage": {},
                "cache_status": "invalid"}
    if any(not isinstance(key, str) or "\0" not in key
           or key.split("\0", 1)[0] not in _AGENTS
           or not re.fullmatch(r"[0-9a-f]{64}", key.split("\0", 1)[1])
           or not _is_cache_day(day)
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
    positions = obj.get("walk_positions")
    obj["walk_positions"] = {
        agent: offset for agent, offset in positions.items()
        if agent in _AGENTS and type(offset) is int and 0 < offset <= MAX_WALK_ENTRIES
    } if isinstance(positions, dict) else {}
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
                    if not isinstance(fragment, str):
                        continue
                    match = re.search(
                        r"^\s*<skill>\s*<name>([a-z0-9]+(?:-[a-z0-9]+)*)</name>\s*<path>([^<\r\n]{1,2048})</path>",
                        fragment,
                    )
                    if match:
                        name = _valid_name(match.group(1))
                        candidate = Path(match.group(2))
                        known_roots = _known_skill_roots(home)
                        ident = item.get("call_id") or item.get("id") or message.get("id") or row.get("id")
                        if (name and candidate.is_absolute()
                                and _known_skill_path(candidate, known_roots)
                                and isinstance(ident, str) and ident):
                            return name, day, "explicit", ident[:256]
                if item.get("type") == "exec" or item.get("kind") == "exec_command":
                    path = item.get("path")
                    if isinstance(path, str) and path.endswith("/SKILL.md"):
                        # Count only structured paths inside conventional skill roots.
                        candidate = Path(path)
                        known_roots = _known_skill_roots(home)
                        if not _known_skill_path(candidate, known_roots):
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


def _codex_command_words(command, *, windows: bool) -> list[str]:
    if isinstance(command, list):
        return [word for word in command if isinstance(word, str)]
    if not isinstance(command, str):
        return []
    try:
        words = shlex.split(command, posix=not windows)
    except ValueError:
        return []
    if windows:
        # Keep path separators. shlex's non-POSIX mode leaves outer quotes intact.
        return [word[1:-1] if word[:1] in {"'", '"'} and word[-1:] == word[:1] else word
                for word in words]
    return words


def _known_skill_path(candidate, roots):
    return (candidate.is_absolute() and candidate.name == "SKILL.md"
            and ".." not in candidate.parts
            and any(candidate.is_relative_to(root) for root in roots))


def _codex_exec_events(row: dict, payload: dict, *, home: Path | None = None) -> list[tuple[str, str, str, str]]:
    """Count only structured Codex exec calls that read a known skill file."""
    raw_args = payload.get("arguments")
    if not isinstance(raw_args, str):
        return []
    try:
        args = json.loads(raw_args)
    except (ValueError, RecursionError):
        return []
    command = (args.get("command") or args.get("cmd")) if isinstance(args, dict) else None
    words = _codex_command_words(command, windows=_WINDOWS)
    if not words or Path(words[0]).name not in {"cat", "head", "tail", "less", "more"}:
        return []
    call_id = payload.get("call_id")
    day = _utc_day(row.get("timestamp"))
    if not isinstance(call_id, str) or not call_id or day is None:
        return []
    roots = _known_skill_roots(home)
    events = []
    names = set()
    for word in words[1:]:
        candidate = Path(word)
        if not _known_skill_path(candidate, roots):
            continue
        name = _valid_name(candidate.parent.name)
        if name and name not in names:
            # Keep the first call's existing cache identity when replaying
            # older transcripts. Additional names share the call, not its ID.
            identity = call_id[:256] if not names else f"{call_id[:256]}\0{name}"
            events.append((name, day, "inferred", identity))
            names.add(name)
    return events


class _WalkProgress:
    def __init__(self):
        self.status = "available"
        self.limited = False


def _candidate_files(agent: str, root: Path, deadline: float, walk: _WalkProgress) -> Iterator[Path]:
    """Yield files as they are found so discovery shares the read deadline."""
    stack = [root]
    entries_seen = 0
    while stack:
        if time.monotonic() >= deadline:
            walk.status, walk.limited = "partial", True
            return
        directory = stack.pop()
        try:
            _check_transcript_path(directory)
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entries_seen >= MAX_WALK_ENTRIES or time.monotonic() >= deadline:
                        walk.status, walk.limited = "partial", True
                        return
                    entries_seen += 1
                    try:
                        if entry.is_symlink():
                            walk.status = "partial"
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.name.endswith((".jsonl", ".json")) and entry.is_file(follow_symlinks=False):
                            if agent == "gemini" or entry.name.endswith(".jsonl"):
                                yield Path(entry.path)
                            else:
                                walk.status = "partial"
                    except OSError:
                        walk.status = "partial"
        except FileNotFoundError:
            if directory == root:
                walk.status = "missing"
                return
            walk.status = "partial"
        except OSError:
            walk.status = "partial"


def _check_transcript_path(path):
    if ".." in path.parts:
        raise OSError("transcript path must not contain parent segments")
    reject_symlink_ancestors(path, OSError, symlink_message="transcript path contains a symlink",
                             inspect_message=None)


def _file_id(path: Path) -> str:
    return hashlib.sha256(os.fsencode(str(path))).hexdigest()


def _file_head(path: Path, before: os.stat_result) -> bytes:
    fd = os.open(path, _READ_FLAGS)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not _same_file_version(before, info):
            raise OSError("not the observed regular file")
        return os.read(fd, 4096)
    finally:
        os.close(fd)


def _same_file_version(before, opened):
    return (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) == (
        before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
    )


def _read_lines(path, before, offset, scan_left, deadline, visit, discarding):
    fd = os.open(path, _READ_FLAGS)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not _same_file_version(before, info):
            raise OSError("not the observed regular file")
        os.lseek(fd, offset, os.SEEK_SET)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            # Bound the bytes in this refresh even when the file's remaining
            # tail is too large. Process records as they arrive so a deadline
            # cannot discard a batch of already-read evidence.
            return _scan_lines(handle, offset, info.st_size, scan_left, deadline, visit, discarding)
    finally:
        os.close(fd)


def _scan_lines(handle, offset, file_size, scan_left, deadline, visit, discarding):
    new_offset = offset
    consumed = 0
    skipped = discarding
    quota = min(file_size - offset, scan_left, MAX_FILE_BYTES)
    try:
        while consumed < quota and time.monotonic() < deadline:
            if discarding:
                tail_bytes, complete = _drain_line(handle, quota - consumed, deadline)
                consumed += tail_bytes
                new_offset = offset + consumed
                discarding = not complete
                if discarding:
                    break
                continue
            line = handle.readline(min(MAX_LINE_BYTES + 1, quota - consumed))
            if not line:
                break
            consumed += len(line)
            if not line.endswith(b"\n"):
                if len(line) <= MAX_LINE_BYTES:
                    break
                # This record exceeds the line limit. Remember whether the
                # newline was reached so the next refresh skips its suffix.
                discarding = skipped = True
            else:
                processed = _visit_line(line, visit)
                if processed is False:
                    break
                skipped = skipped or processed is None
            new_offset = offset + consumed
    except OSError:
        return new_offset, consumed, True, skipped, discarding
    return new_offset, consumed, new_offset < file_size, skipped, discarding


def _drain_line(handle, remaining, deadline):
    total = 0
    while total < remaining and time.monotonic() < deadline:
        chunk = handle.readline(min(65536, remaining - total))
        if not chunk:
            break
        total += len(chunk)
        if chunk.endswith(b"\n"):
            return total, True
    return total, False


def _visit_line(line, visit):
    if len(line) > MAX_LINE_BYTES:
        return None
    if any(token in line for token in (
        b'"Skill"', b'activate_skill', b'"tool":"skill"', b'"tool": "skill"',
        b'"type":"skill"', b'<skill>', b'SKILL.md',
    )):
        try:
            obj = json.loads(line)
        except (ValueError, RecursionError):
            return None
        if isinstance(obj, (dict, list)):
            return visit(obj)
    return True


def _read_gemini_json(path, before, scan_left, visit):
    if before.st_size > MAX_FILE_BYTES or before.st_size > scan_left:
        raise OverflowError("bounded scan limit reached")
    raw = read_regular_file(path, min(MAX_FILE_BYTES, scan_left), follow_symlinks=False)
    if not _same_file_version(before, os.lstat(path)):
        return 0, len(raw), True, False
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        return 0, len(raw), True, False
    if not isinstance(obj, (dict, list)):
        return 0, len(raw), True, False
    processed = visit(obj)
    if processed is False:
        return 0, len(raw), True, False
    return len(raw), len(raw), False, processed is None


def _opencode_legacy_events(obj, stamp, _activation_id):
    if not isinstance(obj, dict) or obj.get("type") != "tool" or obj.get("tool") != "skill":
        return
    state = obj.get("state")
    if not isinstance(state, dict) or state.get("status") not in (None, "completed"):
        return
    inputs = state.get("input")
    name = _valid_name(inputs.get("name") if isinstance(inputs, dict) else None)
    timestamp = obj.get("time") or obj.get("createdAt") or obj.get("timestamp")
    if isinstance(timestamp, dict):
        timestamp = timestamp.get("start") or timestamp.get("created")
    day = _utc_day(timestamp) or _utc_day(stamp)
    ident = obj.get("callID")
    if name and day and isinstance(ident, str) and ident:
        yield name, day, "explicit", ident


def _opencode_session_events(obj, stamp, activation_id):
    if activation_id is not None:
        if isinstance(obj, dict) and isinstance(obj.get("skill"), str) and obj["skill"]:
            name = _valid_name(obj.get("name"))
            day = _utc_day(stamp)
            if name and day and isinstance(activation_id, str) and activation_id:
                yield name, day, "explicit", "activation\0" + activation_id
        return
    content = obj.get("content") if isinstance(obj, dict) else None
    if not isinstance(content, list):
        return
    for part in content:
        if not isinstance(part, dict) or part.get("type") != "tool" or part.get("name") != "skill":
            continue
        state = part.get("state")
        if not isinstance(state, dict) or state.get("status") != "completed":
            continue
        inputs = state.get("input")
        name = _valid_name(inputs.get("id") if isinstance(inputs, dict) else None)
        timing = part.get("time")
        day = _utc_day(timing.get("ran") if isinstance(timing, dict) else None) or _utc_day(stamp)
        ident = part.get("id")
        if name and day and isinstance(ident, str) and ident:
            yield name, day, "explicit", ident


def _opencode_query(conn, table):
    if table == "session_message":
        return ("""SELECT CASE WHEN length(CAST(data AS BLOB)) <= ? THEN data END, time_created,
                          CASE WHEN type = 'skill' THEN id END
                   FROM session_message
                   WHERE type = 'skill' OR (type = 'assistant' AND instr(data, '"skill"') > 0)
                   ORDER BY rowid DESC LIMIT ?""", _opencode_session_events)
    # Older fixtures and exports may have timestamps inside data only.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(part)")}
    stamp = "time_created" if "time_created" in columns else "NULL"
    return (f"""SELECT CASE WHEN length(CAST(data AS BLOB)) <= ? THEN data END, {stamp}, NULL
                FROM part WHERE instr(data, '"skill"') > 0 ORDER BY rowid DESC LIMIT ?""",  # nosec B608
            _opencode_legacy_events)


def _read_opencode(conn, deadline, scan_left):
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_schema WHERE type = 'table' AND name IN ('part', 'session_message')"
    )}
    if not tables:
        return [], True, 0
    events = []
    bytes_read = records = 0
    partial = False
    try:
        # Prefer the current format if a migrated database has both tables.
        for table in sorted(tables, reverse=True):
            query, extract = _opencode_query(conn, table)
            for raw, stamp, activation_id in conn.execute(query, (MAX_LINE_BYTES, MAX_EVENTS + 1)):
                if (records >= MAX_EVENTS or len(events) >= MAX_EVENTS
                        or time.monotonic() >= deadline or bytes_read >= scan_left):
                    return events, True, bytes_read
                records += 1
                if not isinstance(raw, str):
                    partial = True
                    continue
                bytes_read += len(raw.encode("utf-8"))
                if bytes_read > scan_left:
                    return events, True, bytes_read
                try:
                    obj = json.loads(raw)
                except (ValueError, RecursionError):
                    partial = True
                    continue
                for event in extract(obj, stamp, activation_id):
                    if len(events) >= MAX_EVENTS or time.monotonic() >= deadline:
                        return events, True, bytes_read
                    events.append(event)
    except sqlite3.OperationalError as exc:
        if getattr(exc, "sqlite_errorcode", None) != sqlite3.SQLITE_INTERRUPT:
            raise
        partial = True
    return events, partial, bytes_read


def _opencode_snapshot(path):
    _check_transcript_path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise OSError("not a regular database file")
    try:
        wal = path.with_name(path.name + "-wal").lstat()
    except FileNotFoundError:
        pass
    else:
        # Immutable SQLite ignores the WAL. Wait for a checkpoint instead of
        # opening read/write or reporting an incomplete live database as current.
        if not stat.S_ISREG(wal.st_mode) or wal.st_size > 32:
            raise OSError("OpenCode database has an uncheckpointed WAL")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _scan_opencode(path, counts, seen, deadline, scan_left, cutoff, today):
    """Read a checkpointed snapshot without creating SQLite sidecar files."""
    state = {"status": "partial", "files_seen": 0, "events": 0,
             "parser_versions": [PARSER_VERSION], "earliest_event": None}
    if time.monotonic() >= deadline or scan_left <= 0:
        return state, 0
    try:
        before = _opencode_snapshot(path)
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            events, partial, consumed = _read_opencode(conn, deadline, scan_left)
        if before != _opencode_snapshot(path):
            return state, consumed
    except FileNotFoundError:
        state["status"] = "missing"
        return state, 0
    except (sqlite3.Error, OSError, ValueError):
        return state, 0
    state["files_seen"] = 1
    # The deadline limits reading and extraction. Commit the bounded batch
    # only after confirming the snapshot was stable throughout the read.
    if not _record_events(events, "opencode", counts, seen, state, None, cutoff, today):
        partial = True
    state["status"] = "partial" if partial else "available"
    return state, consumed


def _add_event(counts: dict, agent: str, name: str, day: str, kind: str) -> None:
    key = agent + "\0" + name
    item = counts.setdefault(key, {"agent": agent, "name": name, "by_day": {}})
    daily = item["by_day"].setdefault(day, {"explicit": 0, "inferred": 0})
    if isinstance(daily, int):  # upgrade an early cache shape safely
        daily = item["by_day"][day] = {"explicit": daily, "inferred": 0}
    daily[kind] = daily.get(kind, 0) + 1


def _record_events(events, agent, counts, seen, state, deadline, cutoff, today):
    for name, day, kind, ident in events:
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if not cutoff <= day <= today:
            continue
        digest = agent + "\0" + hashlib.sha256(ident.encode("utf-8", "surrogatepass")).hexdigest()
        if digest in seen:
            continue
        if len(seen) >= MAX_EVENTS:
            return False
        _add_event(counts, agent, name, day, kind)
        seen[digest] = day
        state["events"] += 1
        state["earliest_event"] = min(state["earliest_event"] or day, day)
    return True


def _append_offset(old, info, head):
    offset = old.get("offset", 0)
    old_size = old.get("size")
    if type(offset) is not int or type(old_size) is not int or not 0 <= offset <= old_size <= info.st_size:
        return 0
    if not info.st_ino or old.get("inode") != info.st_ino:
        return 0
    # A short file's head grows when a new line is appended. Compare only the
    # bytes that existed when the previous watermark was saved.
    if old.get("head_hash") != hashlib.sha256(head[:old_size]).hexdigest():
        return 0
    if old_size == info.st_size and old.get("mtime_ns") != info.st_mtime_ns:
        return 0
    return offset


def _scan_text_file(agent, path, old, scan_left, deadline, visit):
    _check_transcript_path(path)
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode):
        raise OSError("not a regular transcript")
    if old.get("parser_version") != PARSER_VERSION:
        old = {}
    head = _file_head(path, before)
    head_hash = hashlib.sha256(head).hexdigest()
    offset = _append_offset(old, before, head)
    if (old.get("size") == before.st_size and old.get("mtime_ns") == before.st_mtime_ns
            and old.get("inode") == before.st_ino and old.get("head_hash") == head_hash
            and offset == before.st_size):
        return old, 0
    # Earlier partial watermarks did not distinguish skipped records from
    # retryable tails. Re-read them once so skips continue to be reported.
    if old.get("partial") and "skipped" not in old:
        offset = 0
    discarding = False
    if agent == "gemini" and path.suffix == ".json":
        new_offset, consumed, incomplete, skipped = _read_gemini_json(path, before, scan_left, visit)
    else:
        new_offset, consumed, incomplete, skipped, discarding = _read_lines(
            path, before, offset, scan_left, deadline, visit, offset > 0 and old.get("discarding") is True,
        )
        skipped = skipped or (offset > 0 and old.get("skipped") is True)
    watermark = {"size": before.st_size, "mtime_ns": before.st_mtime_ns, "inode": before.st_ino,
                 "offset": new_offset, "partial": incomplete or skipped, "skipped": skipped,
                 "discarding": discarding, "head_hash": head_hash, "parser_version": PARSER_VERSION}
    return watermark, consumed


def _prune_text_watermarks(watermarks, prefix, live_ids):
    owned = [key for key in watermarks if key.startswith(prefix)]
    if live_ids is not None:
        for key in owned:
            if key not in live_ids:
                del watermarks[key]
        return
    excess = len(owned) - MAX_AGENT_WATERMARKS
    if excess <= 0:
        return

    def priority(key):
        entry = watermarks[key]
        position, size = entry.get("offset"), entry.get("size")
        unfinished = (type(position) is int and type(size) is int and position < size
                      or entry.get("discarding") is True)
        modified = entry.get("mtime_ns")
        return unfinished, modified if type(modified) is int else 0

    for key in sorted(owned, key=priority)[:excess]:
        del watermarks[key]


def _scan_text_agent(agent: str, root: Path, cache: dict, counts: dict, seen: dict,
                     deadline: float, scan_left: int, cutoff, today, *,
                     home: Path | None = None) -> tuple[dict, int]:
    positions = cache.setdefault("walk_positions", {})
    start = positions.get(agent, 0)
    state = {"status": "partial" if start else "available", "files_seen": 0, "events": 0,
             "parser_versions": [PARSER_VERSION], "earliest_event": None}
    bytes_read = 0
    watermarks = cache["watermarks"]
    prefix = agent + "\0"
    live_ids = set()
    walk = _WalkProgress()
    next_position = start
    stopped = False

    def visit(row):
        # None marks a skipped record, False leaves the record to retry.
        try:
            events = _events(agent, row, home=home)
        except RecursionError:
            return None
        return _record_events(events, agent, counts, seen, state, deadline, cutoff, today)

    with closing(_candidate_files(agent, root, deadline, walk)) as files:
        for index, path in enumerate(files):
            if index < start:
                continue
            if (index - start >= MAX_FILES or bytes_read >= scan_left
                    or time.monotonic() >= deadline or state["events"] >= MAX_EVENTS):
                state["status"] = "partial"
                stopped = True
                break
            next_position = index + 1
            fid = prefix + _file_id(path)
            live_ids.add(fid)
            try:
                watermark, consumed = _scan_text_file(
                    agent, path, watermarks.get(fid, {}), scan_left - bytes_read, deadline, visit
                )
            except (OSError, ValueError, OverflowError):
                state["status"] = "partial"
                continue
            state["files_seen"] += 1
            watermarks[fid] = watermark
            bytes_read += consumed
            if watermark.get("partial"):
                state["status"] = "partial"
    if walk.status != "available":
        state["status"] = walk.status
    if (stopped or walk.limited) and next_position > start:
        positions[agent] = next_position
    else:
        positions.pop(agent, None)
    complete_walk = not start and not stopped and walk.status == "available"
    _prune_text_watermarks(watermarks, prefix, live_ids if complete_walk else None)
    return state, bytes_read


def _unavailable_coverage(status: str) -> dict:
    return {"status": status, "files_seen": 0, "events": 0, "parser_versions": [],
            "earliest_event": None, "coverage_window_start": None, "parser_coverage": "unavailable"}


def _describe_observation(state):
    state["coverage_level"] = "known-structured-events-only"
    state["parser_coverage"] = "partial-undocumented-format"
    state["coverage_window_start"] = None


def _cached_coverage(cache, agent):
    if cache.get("cache_status") == "invalid":
        return _unavailable_coverage("cache-invalid")
    if agent not in cache["coverage"]:
        return {"status": "not-scanned", "files_seen": 0, "events": 0,
                "parser_versions": [], "earliest_event": None}
    saved = cache["coverage"][agent]
    if not isinstance(saved, dict) or saved.get("status") not in ("available", "partial", "missing"):
        return _unavailable_coverage("cache-invalid")
    versions, earliest = saved.get("parser_versions"), saved.get("earliest_event")
    if (not _is_cached_count(saved.get("files_seen")) or not _is_cached_count(saved.get("events"))
            or (earliest is not None and not _is_cache_day(earliest))
            or not isinstance(versions, list)
            or any(not isinstance(version, str) or not re.fullmatch(r"usage-[0-9]{1,6}", version)
                   for version in versions)):
        return _unavailable_coverage("cache-invalid")
    state = {"status": saved["status"], "files_seen": saved["files_seen"], "events": saved["events"],
             "parser_versions": versions, "earliest_event": earliest}
    if state["status"] == "partial" and saved.get("cache_recovered_from_transcripts") is True:
        state["cache_recovered_from_transcripts"] = True
    _describe_observation(state)
    return state


def _report_unlocked(data_dir: Path | str | None = None, agents: Sequence[str] | None = None,
                     *, days: int = 90, refresh: bool = False, home: Path | None = None) -> dict:
    """Return skill counts and per-agent scan coverage, reading only consented roots."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 1 or days > 400:
        raise UsageError("days must be between 1 and 400")
    directory = _usage_dir(data_dir)
    exists = _ensure_private_usage_dir(directory)
    initial_consents = _load_consent(directory) if exists else {}
    cache = _load_cache(directory)
    consents = _load_consent(directory) if exists else {}
    requested = list(agents) if agents else list(_AGENTS)
    if any(agent not in _AGENTS for agent in requested):
        raise UsageError("unsupported agent requested")
    requested = list(dict.fromkeys(requested))
    configured_roots = {agent: str(root.absolute()) for agent, root in _roots(home).items()}
    active_agents = {agent for agent in requested if agent in consents and configured_roots.get(agent) == consents[agent]}
    bindings = cache.setdefault("root_bindings", {})
    mismatched = {agent for agent in active_agents if (
        initial_consents.get(agent) != consents[agent]
        or (agent in bindings and bindings[agent] != _root_binding(consents[agent]))
    )}
    if refresh:
        for agent in mismatched:
            _clear_agent_evidence(cache, agent)
        for agent in active_agents:
            bindings[agent] = _root_binding(consents[agent])
        mismatched.clear()
    reportable_agents = active_agents - mismatched
    counts, seen = cache["counts"], cache["seen"]
    now = _utc_now()
    today = now.date().isoformat()
    cutoff = (now.date() - _dt.timedelta(days=RETENTION_DAYS - 1)).isoformat()
    for key, item in list(counts.items()):
        retained = {day: n for day, n in item["by_day"].items() if cutoff <= day <= today}
        if retained:
            counts[key] = {"agent": item["agent"], "name": item["name"], "by_day": retained}
        else:
            del counts[key]
    seen = {key: day for key, day in seen.items() if cutoff <= day <= today}
    deadline = time.monotonic() + MAX_SECONDS
    bytes_left = MAX_SCAN_BYTES
    coverage = {}
    scan_order = requested
    active_order = [agent for agent in requested if agent in active_agents]
    next_agent = cache.get("next_scan_agent")
    if refresh and len(active_order) > 1 and next_agent in active_order:
        first = active_order.index(next_agent)
        active_order = active_order[first:] + active_order[:first]
        scan_order = active_order + [agent for agent in requested if agent not in active_agents]
    for agent in scan_order:
        if agent not in consents:
            coverage[agent] = _unavailable_coverage("no-consent")
            continue
        root = Path(consents[agent])
        if agent not in active_agents:
            status = "configuration-changed" if agent in configured_roots else "source-unavailable"
            coverage[agent] = _unavailable_coverage(status)
            continue
        if agent in mismatched:
            coverage[agent] = _unavailable_coverage("cache-root-mismatch")
            continue
        if not refresh:
            coverage[agent] = _cached_coverage(cache, agent)
            continue
        if bytes_left <= 0 or time.monotonic() >= deadline:
            # Leave the source's saved file position intact when another
            # agent consumed the shared budget before this one could start.
            state, consumed = _unavailable_coverage("partial"), 0
            state["parser_versions"] = [PARSER_VERSION]
        elif agent == "opencode":
            state, consumed = _scan_opencode(root, counts, seen, deadline, bytes_left, cutoff, today)
        else:
            state, consumed = _scan_text_agent(
                agent, root, cache, counts, seen, deadline, bytes_left, cutoff, today, home=home
            )
        bytes_left = max(0, bytes_left - consumed)
        _describe_observation(state)
        if cache.get("cache_status") == "invalid":
            state["status"] = "partial"
            state["cache_recovered_from_transcripts"] = True
        coverage[agent] = state
        cache["coverage"][agent] = state
    if refresh and len(active_order) > 1:
        if bytes_left <= 0 or time.monotonic() >= deadline:
            cache["next_scan_agent"] = active_order[1]
        else:
            cache.pop("next_scan_agent", None)
    # Only report aggregates for requested agents; never include IDs, paths, text, or arguments.
    min_day = (now.date() - _dt.timedelta(days=days - 1)).isoformat()
    rows = []
    for item in counts.values():
        if item["agent"] not in reportable_agents:
            continue
        by_day = {day: n for day, n in item.get("by_day", {}).items() if day >= min_day}
        if not by_day:
            continue
        explicit = sum((n.get("explicit", 0) if isinstance(n, dict) else n) for n in by_day.values())
        inferred = sum(n.get("inferred", 0) for n in by_day.values() if isinstance(n, dict))
        rows.append({"agent": item["agent"], "name": item["name"],
                     "explicit": explicit, "inferred": inferred,
                     "by_day": {day: sum(n.values()) if isinstance(n, dict) else n for day, n in by_day.items()},
                     "first_seen": min(by_day), "last_seen": max(by_day)})
    rows.sort(key=lambda row: (row["agent"], row["name"]))
    # Store counts by kind explicitly for correct day-bucket rollups.
    cache["counts"] = counts
    cache["seen"] = seen
    if consents and refresh:
        _ensure_private_usage_dir(directory, create=True)
        cache.pop("cache_status", None)
        _write_json(directory / "counts.json", cache)
    return {"consented": sorted(consents), "coverage": {agent: coverage[agent] for agent in requested}, "counts": rows,
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
