"""Conservative lifecycle observations and previewed, reversible pins.

No archive operation is exposed here: transcript coverage and complete
consumer/edit evidence are not currently sufficient to establish staleness.
"""
from __future__ import annotations

import base64
import hashlib
import itertools
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .atomic_io import atomic_write_text, mutation_lock, register_lock_root
from .errors import StoreError
from .file_reads import read_regular_file
from .path_safety import mkdir_private, trusted_root
from .review_artifacts import is_plan_token, issue_plan_token, matches_plan_token
from .validator import validate_skill_name

MAX_SKILLS = 10_000
MAX_USAGE_ROWS = 100_000
MAX_PIN_BYTES = 2 * 1024 * 1024
MAX_NOTE = 500
_SCOPE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


def _key(scope, name):
    if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
        raise StoreError("invalid pin scope")
    try:
        validate_skill_name(name)
    except ValueError as exc:
        raise StoreError(str(exc)) from exc
    return f"{scope}/{name}"


def _root(data_dir, *, create=False):
    try:
        root = trusted_root(Path(data_dir))
        if create:
            mkdir_private(root)
        if root.exists() and os.name == "posix" and root.stat().st_mode & 0o077:
            raise StoreError("lifecycle data directory must be private")
        return root
    except (OSError, ValueError) as exc:
        raise StoreError("cannot access private lifecycle data directory") from exc


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("pins file has duplicate keys")
        result[key] = value
    return result


def _load(root):
    try:
        path = root / "pins.json"
        raw = read_regular_file(path, MAX_PIN_BYTES, follow_symlinks=False)
        if os.name == "posix" and path.lstat().st_mode & 0o077:
            raise StoreError("pins file must be private")
    except FileNotFoundError:
        return None, {"version": 1, "pins": {}}
    except (OSError, ValueError) as exc:
        raise StoreError("cannot read pins file safely") from exc
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as exc:
        raise StoreError("invalid pins file") from exc
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise StoreError("unsupported pins file")
    pins = data.get("pins")
    if not isinstance(pins, dict) or len(pins) > MAX_SKILLS:
        raise StoreError("invalid or oversized pins file")
    for key, value in pins.items():
        if not isinstance(key, str) or key.count("/") != 1 or not isinstance(value, dict):
            raise StoreError("invalid pin entry")
        _key(*key.split("/"))
        if not isinstance(value.get("note", ""), str):
            raise StoreError("invalid pin note")
    return raw, data


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _plan(root, scope, name, pinned, note):
    key = _key(scope, name)
    if type(pinned) is not bool:
        raise StoreError("pin state must be true or false")
    if not isinstance(note, str) or len(note) > MAX_NOTE or any(ord(c) < 32 or ord(c) == 127 for c in note):
        raise StoreError("pin note must be printable and at most 500 characters")
    before, doc = _load(root)
    previous = doc["pins"].get(key)
    action = {"path": str(root), "key": key, "pinned": pinned, "note": note,
              "preimage": None if before is None else _hash(before)}
    plan_hash = _hash(json.dumps(action, sort_keys=True, ensure_ascii=True).encode("ascii"))
    changed = (previous is None or previous.get("note", "") != note) if pinned else previous is not None
    return before, doc, previous, plan_hash, changed


def preview_pin_change(data_dir, scope, name, pinned, *, note=""):
    root = _root(data_dir)
    _, _, previous, binding, changed = _plan(root, scope, name, pinned, note)
    return {"scope": scope, "name": name, "pinned": pinned, "note": note,
            "previous": previous, "changed": changed, "plan_hash": issue_plan_token(binding)}


def _receipts(root):
    directory = root / "pin-backups"
    if directory.is_symlink():
        raise StoreError("pin backup directory is a symlink")
    mkdir_private(directory)
    if os.name == "posix" and directory.stat().st_mode & 0o077:
        raise StoreError("pin backup directory must be private")
    return directory


def _write(path, data, *, limit=MAX_PIN_BYTES):
    if len(data.encode("utf-8")) > limit:
        raise StoreError("pins file exceeds size limit")
    atomic_write_text(path, data)


def apply_pin_change(data_dir, scope, name, pinned, plan_hash, *, note=""):
    root = _root(data_dir, create=True)
    register_lock_root(root)
    path = root / "pins.json"
    with mutation_lock(path):
        before, doc, _, binding, changed = _plan(root, scope, name, pinned, note)
        if not matches_plan_token(plan_hash, binding):
            raise StoreError("pin preview is stale; preview again")
        if not changed:
            return {"changed": False, "plan_hash": plan_hash}
        key = _key(scope, name)
        if pinned:
            doc["pins"][key] = {"at": datetime.now(timezone.utc).isoformat(), "note": note}
        else:
            del doc["pins"][key]
        after = (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        if len(after) > MAX_PIN_BYTES or len(doc["pins"]) > MAX_SKILLS:
            raise StoreError("pins file exceeds size limit")
        receipt_path = _receipts(root) / (plan_hash + ".json")
        if receipt_path.exists() or receipt_path.is_symlink():
            raise StoreError("pin preview was already used")
        receipt = {"state": "prepared", "before": None if before is None else base64.b64encode(before).decode("ascii"),
                   "after": _hash(after), "scope": scope, "name": name}
        _write(receipt_path, json.dumps(receipt), limit=MAX_PIN_BYTES * 2)
        current, _ = _load(root)
        if current != before:
            raise StoreError("pins changed before replacement")
        _write(path, after.decode("utf-8"))
        receipt["state"] = "applied"
        _write(receipt_path, json.dumps(receipt), limit=MAX_PIN_BYTES * 2)
    return {"changed": True, "plan_hash": plan_hash}


def undo_pin_change(data_dir, plan_hash):
    if not is_plan_token(plan_hash):
        raise StoreError("invalid pin plan hash")
    root = _root(data_dir)
    register_lock_root(root)
    path = root / "pins.json"
    with mutation_lock(path):
        receipt_path = root / "pin-backups" / (plan_hash + ".json")
        if receipt_path.parent.is_symlink():
            raise StoreError("pin backup directory is a symlink")
        try:
            raw = read_regular_file(receipt_path, MAX_PIN_BYTES * 2, follow_symlinks=False)
            receipt = json.loads(raw, object_pairs_hook=_unique_object)
            if receipt["state"] != "applied":
                raise StoreError("pin change was not confirmed as applied")
            before = None if receipt["before"] is None else base64.b64decode(receipt["before"], validate=True)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise StoreError("invalid or missing pin undo receipt") from exc
        current, _ = _load(root)
        if current is None or _hash(current) != receipt.get("after"):
            raise StoreError("pins changed after this action; undo refused")
        if before is None:
            path.unlink()
        else:
            _write(path, before.decode("utf-8"))
        receipt["state"] = "undone"
        _write(receipt_path, json.dumps(receipt), limit=MAX_PIN_BYTES * 2)
    return {"restored": True, "plan_hash": plan_hash}


def _day(value):
    try:
        if not isinstance(value, str):
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _usage_index(report, cutoff, today):
    index = {}
    rows = report.get("counts", []) if isinstance(report, dict) else []
    if not isinstance(rows, list) or len(rows) > MAX_USAGE_ROWS:
        raise StoreError("invalid or oversized usage report")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        by_day = row.get("by_day")
        if not isinstance(by_day, dict) or len(by_day) > 400:
            continue
        for day, count in by_day.items():
            observed = _day(day)
            if observed is not None and cutoff <= observed <= today and type(count) is int and count > 0:
                index.setdefault(row["name"], set()).add(str(row.get("agent", "unknown")))
                break
    return index


def candidate_report(skills, usage_report, *, data_dir, days=90, now=None):
    if type(days) is not int or not 1 <= days <= 400:
        raise StoreError("days must be between 1 and 400")
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise StoreError("current time must include a timezone")
    today = now.astimezone(timezone.utc).date()
    cutoff = today - timedelta(days=days - 1)
    root = _root(data_dir)
    _, pins = _load(root)
    usage = _usage_index(usage_report, cutoff, today)
    selected = list(itertools.islice(iter(skills), MAX_SKILLS + 1))
    rows = []
    for skill in selected[:MAX_SKILLS]:
        if not isinstance(skill, dict):
            raise StoreError("invalid skill record")
        scope, name = skill.get("scope", "global"), skill.get("name")
        key = _key(scope, name)
        agents = sorted(usage.get(name, ()))
        edited = _day(skill.get("last_edit"))
        active = bool(agents) or (edited is not None and cutoff <= edited <= today)
        rows.append({"scope": scope, "name": name, "state": "in-use" if active else "unknown",
                     "pinned": key in pins["pins"], "last_edit": skill.get("last_edit"),
                     "used_by": agents, "reason": "recent activity" if active else
                     "complete consumer, usage and edit coverage is not established"})
    return {"days": days, "cutoff": cutoff.isoformat(), "skills": rows,
            "truncated": len(selected) > MAX_SKILLS, "limit": MAX_SKILLS}
