"""Bounded local operations on Vercel project skill lockfiles."""

import base64
import difflib
import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from . import lockfiles
from .atomic_io import atomic_write_text
from .file_reads import read_regular_file
from .path_safety import mkdir_private, trusted_root
from .review_artifacts import is_plan_token, issue_plan_token, matches_plan_token


def _has_contained_document(skill: Path) -> bool:
    try:
        document = (skill / "SKILL.md").resolve(strict=True)
        return document.is_relative_to(skill.resolve(strict=True)) and document.is_file()
    except (OSError, RuntimeError):
        return False


def verify_project_lock(project_root: str | Path) -> dict:
    """Return lock evidence and whether all entries were verified, without writes."""
    project = Path(project_root).expanduser()
    lock = lockfiles.read_lock(project / lockfiles.PROJECT_LOCK_FILENAME, kind="project")
    token = lockfiles._REQUEST_BUDGET.set(lockfiles._RequestBudget())
    try:
        result = lockfiles._evaluated_lock(
            lock, project / ".agents" / "skills",
            "portable" if lock.get("version") == 2 else "computed",
        )
    finally:
        lockfiles._REQUEST_BUDGET.reset(token)
    for row, entry in zip(result["entries"], lock["entries"]):
        skill = project / ".agents" / "skills" / entry["installed_name"]
        if row["present"] and not _has_contained_document(skill):
            row["present"] = False
            row["hash_status"] = "missing"
            row["hash_reason"] = "the installed skill has no SKILL.md"
    result["counts"] = lockfiles._counts(result["entries"])
    result["verified"] = (
        result["state"] == "ok" and not result["omitted"] and
        not result["name_collisions"] and
        all(row["hash_status"] == "match" for row in result["entries"])
    )
    return result

# The vendor's companion file is an exclusive create; we deliberately never
# break stale files because another process could still own them.
def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_document(project):
    path = project / lockfiles.PROJECT_LOCK_FILENAME
    try:
        raw = read_regular_file(path, lockfiles.MAX_LOCK_BYTES, follow_symlinks=False)
    except FileNotFoundError:
        return None, {"version": 2, "skills": {}}
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=lockfiles._unique_lock_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise lockfiles.LockfileError("invalid lockfile JSON") from exc
    if (not isinstance(document, dict) or type(document.get("version")) is not int or
            document.get("version") not in (1, 2)):
        raise lockfiles.LockfileError("unsupported project lockfile version")
    if isinstance(document.get("version"), bool) or not isinstance(document.get("skills"), dict):
        raise lockfiles.LockfileError("invalid project lockfile structure")
    if len(document["skills"]) > lockfiles.MAX_LOCK_ENTRIES:
        raise lockfiles.LockfileTooLarge("too many project lock entries")
    if any(not isinstance(entry, dict) for entry in document["skills"].values()):
        raise lockfiles.LockfileError("invalid project lock entry")
    return raw, document


def _local_source(project, source, skill_hash, *, allow_absolute=False):
    if not isinstance(source, str) or not source or (os.path.isabs(source) and not allow_absolute):
        raise lockfiles.LockfileError("local source must be project-relative")
    target = (project / source).resolve(strict=True)
    if not target.is_relative_to(project) or not target.is_dir():
        raise lockfiles.LockfileError("local source must be a directory inside the project")
    if lockfiles.portable_folder_hash(target) != skill_hash:
        raise lockfiles.LockfileError("local source differs from installed skill")
    relative = target.relative_to(project).as_posix()
    return "." if relative == "." else "./" + relative


def _update_entry(project, document, name, local_sources):
    if not isinstance(name, str) or not name or len(name) > 128 or lockfiles.sanitize_name(name) != name:
        raise lockfiles.LockfileError("skill name must be a canonical installed name")
    skill = project / ".agents" / "skills" / name
    if skill.is_symlink() or skill.parent.is_symlink() or skill.parent.parent.is_symlink():
        raise lockfiles.LockfileError("symlinked installed skill or parent")
    if not _has_contained_document(skill):
        raise lockfiles.LockfileError("installed skill has no SKILL.md")
    entry = document["skills"].get(name)
    if entry is None:
        if name not in local_sources:
            raise lockfiles.LockfileError("new skill requires a project-relative local source")
        entry = {"sourceType": "local"}
        document["skills"][name] = entry
    if not isinstance(entry.get("source"), str) and name not in local_sources:
        raise lockfiles.LockfileError("skill has no recorded source")
    if document["version"] == 1:
        # ICU localeCompare cannot be reproduced portably with stdlib Python.
        raise lockfiles.LockfileError("writing version 1 locks requires vendor migration first")
    computed = lockfiles.portable_folder_hash(skill)
    if name in local_sources:
        entry["source"] = _local_source(project, local_sources[name], computed)
        entry["sourceType"] = "local"
        entry.pop("commit", None)
    elif entry.get("sourceType") == "local":
        entry["source"] = _local_source(project, entry["source"], computed, allow_absolute=True)
    if entry.get("computedHash") != computed:
        entry.pop("commit", None)
    entry["computedHash"] = computed


def _write_plan(project_root, names, local_sources):
    project = Path(project_root).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise lockfiles.LockfileError("project is not a directory")
    names = list(names)
    if not names or len(names) > lockfiles.MAX_LOCK_ENTRIES or len(set(names)) != len(names):
        raise lockfiles.LockfileError("supply distinct skill names within the entry limit")
    sources = dict(local_sources or {})
    if set(sources) - set(names):
        raise lockfiles.LockfileError("local sources must name selected skills")
    before, document = _read_document(project)
    original = json.dumps(document, ensure_ascii=False, indent=2)
    token = lockfiles._REQUEST_BUDGET.set(lockfiles._RequestBudget())
    try:
        for name in names:
            _update_entry(project, document, name, sources)
    finally:
        lockfiles._REQUEST_BUDGET.reset(token)
    updated = json.dumps(document, ensure_ascii=False, indent=2)
    after = before if before is not None and original == updated else (updated + "\n").encode("utf-8")
    if len(after) > lockfiles.MAX_LOCK_BYTES:
        raise lockfiles.LockfileTooLarge("resulting lockfile is too large")
    mode = None if before is None else stat.S_IMODE((project / lockfiles.PROJECT_LOCK_FILENAME).stat().st_mode)
    plan = {"project": str(project), "before": None if before is None else _digest(before), "mode": mode,
            "after": _digest(after), "names": sorted(names), "sources": sources}
    plan_hash = _digest(json.dumps(plan, sort_keys=True, ensure_ascii=True).encode("ascii"))
    return project, before, after, plan_hash, mode


def _review_entries(data, names):
    """Display selected managed fields without echoing arbitrary lockfile data."""
    skills = json.loads(data)["skills"] if data is not None else {}
    selected = {}
    for name in sorted(names):
        if name not in skills:
            continue
        entry = skills[name]
        source = entry.get("source")
        if entry.get("sourceType") == "local":
            label = source if isinstance(source, str) and (source == "." or source.startswith("./")) else "(local source)"
        else:
            label = "(recorded source)" if source else "(no source)"
        row = {"source": label}
        for key in ("computedHash", "commit"):
            if key in entry:
                value = entry[key]
                row[key] = (value if isinstance(value, str) and len(value) in (40, 64)
                            and all(char in "0123456789abcdefABCDEF" for char in value)
                            else "(unrecognized value)")
        selected[name] = row
    return (json.dumps(selected, ensure_ascii=True, indent=2) + "\n").splitlines(keepends=True)


def preview_project_lock_write(project_root: str | Path, names: list[str], *, local_sources: dict[str, str] | None = None) -> dict:
    project, before, after, binding, _mode = _write_plan(project_root, names, local_sources)
    diff = "".join(difflib.unified_diff(
        _review_entries(before, names), _review_entries(after, names),
        fromfile="selected entries (before)", tofile="selected entries (after)", n=0))
    return {"project": str(project), "plan_hash": issue_plan_token(binding), "diff": diff,
            "changed": before != after,
            "note": "Preview shows managed fields on selected entries. The plan binds the full lockfile."}


@contextmanager
def _vendor_mutex(path):
    mutex = Path(str(path) + ".lock")
    try:
        fd = os.open(mutex, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise lockfiles.LockfileError("project lock is busy") from exc
    identity = os.fstat(fd)
    def check():
        try:
            current = mutex.lstat()
        except FileNotFoundError as exc:
            raise lockfiles.LockfileError("project lock was lost") from exc
        if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise lockfiles.LockfileError("project lock was replaced")
    try:
        yield check
    finally:
        os.close(fd)
        try:
            current = mutex.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                mutex.unlink()
        except FileNotFoundError:
            pass


def _atomic_bytes(path, content, mode, before_replace):
    fd, name = tempfile.mkstemp(prefix=".skills-lock-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            if hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), mode)
            else:  # Windows has no fchmod.
                os.chmod(name, mode)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        before_replace()
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _receipt_dir(data_dir):
    root = trusted_root(Path(data_dir))
    mkdir_private(root)
    folder = root / "project-lock-backups"
    if folder.is_symlink():
        raise lockfiles.LockfileError("backup directory is a symlink")
    mkdir_private(folder)
    trusted_root(folder, label="project lock backup directory")
    if os.name == "posix" and (root.stat().st_mode & 0o077 or folder.stat().st_mode & 0o077):
        raise lockfiles.LockfileError("project lock backup directories must be private")
    return folder


def _read_current(path):
    try:
        return read_regular_file(path, lockfiles.MAX_LOCK_BYTES, follow_symlinks=False)
    except FileNotFoundError:
        return None


def apply_project_lock_write(project_root: str | Path, names: list[str], plan_hash: str, *, data_dir: str | Path, local_sources: dict[str, str] | None = None) -> dict:
    project, before, after, binding, expected_mode = _write_plan(project_root, names, local_sources)
    if not matches_plan_token(plan_hash, binding):
        raise lockfiles.LockfileError("preview is stale; run preview again")
    path = project / lockfiles.PROJECT_LOCK_FILENAME
    with _vendor_mutex(path) as check_lock:
        if _read_current(path) != before:
            raise lockfiles.LockfileError("lockfile changed after preview")
        mode = stat.S_IMODE(path.stat().st_mode) if before is not None else 0o644
        if before is not None and mode != expected_mode:
            raise lockfiles.LockfileError("lockfile permissions changed after preview")
        if before == after:
            return {"project": str(project), "plan_hash": plan_hash, "changed": False}
        receipt = {"project": str(project), "before": None if before is None else base64.b64encode(before).decode("ascii"),
                   "after": _digest(after), "mode": mode, "state": "prepared"}
        receipt_path = _receipt_dir(data_dir) / (plan_hash + ".json")
        receipt_bytes = json.dumps(receipt, sort_keys=True).encode("utf-8")
        try:
            fd = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError as exc:
            saved = read_regular_file(receipt_path, lockfiles.MAX_LOCK_BYTES * 2, follow_symlinks=False)
            if saved != receipt_bytes:
                raise lockfiles.LockfileError("preview receipt already exists with different contents") from exc
        else:
            with os.fdopen(fd, "wb") as handle:
                handle.write(receipt_bytes)
                handle.flush()
                os.fsync(handle.fileno())
        def check_preimage():
            check_lock()
            if _read_current(path) != before:
                raise lockfiles.LockfileError("lockfile changed before replacement")
            if before is not None and stat.S_IMODE(path.stat().st_mode) != mode:
                raise lockfiles.LockfileError("lockfile permissions changed before replacement")
        _atomic_bytes(path, after, mode, check_preimage)
        receipt["state"] = "applied"
        atomic_write_text(receipt_path, json.dumps(receipt, sort_keys=True))
    return {"project": str(project), "plan_hash": plan_hash, "changed": True}


def undo_project_lock_write(project_root: str | Path, plan_hash: str, *, data_dir: str | Path) -> dict:
    if not is_plan_token(plan_hash):
        raise lockfiles.LockfileError("invalid preview hash")
    project = Path(project_root).expanduser().resolve(strict=True)
    receipt_path = _receipt_dir(data_dir) / (plan_hash + ".json")
    raw = read_regular_file(receipt_path, lockfiles.MAX_LOCK_BYTES * 2, follow_symlinks=False)
    receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=lockfiles._unique_lock_object)
    if receipt.get("project") != str(project):
        raise lockfiles.LockfileError("receipt belongs to another project")
    if receipt.get("state") != "applied":
        raise lockfiles.LockfileError("write was not confirmed as applied")
    before = None if receipt["before"] is None else base64.b64decode(receipt["before"], validate=True)
    path = project / lockfiles.PROJECT_LOCK_FILENAME
    with _vendor_mutex(path) as check_lock:
        current = _read_current(path)
        if current is None or _digest(current) != receipt["after"]:
            raise lockfiles.LockfileError("lockfile changed after write; undo refused")
        if stat.S_IMODE(path.stat().st_mode) != receipt["mode"]:
            raise lockfiles.LockfileError("lockfile permissions changed after write; undo refused")
        if before is None:
            check_lock()
            if _read_current(path) != current:
                raise lockfiles.LockfileError("lockfile changed before undo")
            if stat.S_IMODE(path.stat().st_mode) != receipt["mode"]:
                raise lockfiles.LockfileError("lockfile permissions changed before undo")
            path.unlink()
        else:
            def check_postimage():
                check_lock()
                if _read_current(path) != current:
                    raise lockfiles.LockfileError("lockfile changed before undo")
                if stat.S_IMODE(path.stat().st_mode) != receipt["mode"]:
                    raise lockfiles.LockfileError("lockfile permissions changed before undo")
            _atomic_bytes(path, before, receipt["mode"], check_postimage)
        receipt["state"] = "undone"
        atomic_write_text(receipt_path, json.dumps(receipt, sort_keys=True))
    return {"project": str(project), "plan_hash": plan_hash, "restored": True}
