"""Reviewed, reversible moves for one exact manager-library skill."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import stat
from pathlib import Path, PurePosixPath

from . import lifecycle
from .atomic_io import atomic_write_text, is_sha256_hex, mutation_lock
from .clock import now_iso
from .documents import ACTIVE_DOCUMENT, DISABLED_DOCUMENT
from .errors import SkillNotFound, StoreError
from .file_reads import read_regular_file
from .review_artifacts import is_plan_token, is_valid_review_id, issue_plan_token, matches_plan_token
from .store import _skill_and_index_locks

MAX_ENTRIES = 10_000
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TREE_BYTES = 256 * 1024 * 1024
MAX_RECEIPT_BYTES = 4096
RECEIPT = "ARCHIVE.json"
TREE = "skill"
INDEX_WARNING = "The move completed on disk. Run jackfield db resync to repair the index."


def _encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_encode(value).encode("ascii")).hexdigest()


def _metadata(path):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise StoreError("archive requires plain paths and does not move links")
    return info


def _directory(path, *, private=False):
    info = _metadata(path)
    if not stat.S_ISDIR(info.st_mode) or path.resolve(strict=True) != path:
        raise StoreError("archive requires an unlinked directory")
    if private and os.name == "posix" and info.st_mode & 0o077:
        raise StoreError("archive directories must be private")
    return info


def _revision(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _children(directory, remaining):
    with os.scandir(directory) as entries:
        children = [Path(entry.path) for entry in itertools.islice(entries, remaining + 1)]
    if len(children) > remaining:
        raise StoreError(f"archive folder exceeds {MAX_ENTRIES} entries")
    return children


def _file_record(path, info, remaining):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise StoreError("archive requires regular files without hard links")
    if info.st_size > remaining:
        raise StoreError("archive folder exceeds a file or total byte limit")
    raw = read_regular_file(path, remaining, follow_symlinks=False)
    if len(raw) != info.st_size or _revision(_metadata(path)) != _revision(info):
        raise StoreError("archive folder changed during review")
    return len(raw), hashlib.sha256(raw).hexdigest()


def _snapshot(root):
    """Bind exact paths and bytes, including empty directories and companions."""
    device = _directory(root).st_dev
    pending = [root]
    records = {}
    revisions = {}
    used_bytes = 0
    while pending:
        path = pending.pop()
        if path.resolve(strict=True) != path:
            raise StoreError("archive folder contains an indirect path")
        info = _metadata(path)
        if info.st_dev != device:
            raise StoreError("archive folder contains a mounted filesystem")
        relative = path.relative_to(root).as_posix()
        revisions[relative] = _revision(info)
        if stat.S_ISDIR(info.st_mode):
            records[relative] = ("directory", stat.S_IMODE(info.st_mode))
            pending.extend(_children(path, MAX_ENTRIES - len(revisions) - len(pending)))
        else:
            size, digest = _file_record(path, info, min(MAX_FILE_BYTES, MAX_TREE_BYTES - used_bytes))
            records[relative] = ("file", stat.S_IMODE(info.st_mode), size, digest)
            used_bytes += size
    documents = [records.get(document) for document in (ACTIVE_DOCUMENT, DISABLED_DOCUMENT)]
    documents = [document for document in documents if document is not None]
    if len(documents) != 1 or documents[0][0] != "file":
        raise StoreError("archive requires exactly one regular primary skill document")
    for relative, revision in revisions.items():
        if _revision(_metadata(root / relative)) != revision:
            raise StoreError("archive folder changed during review")
    return _digest(records), _digest(revisions)


def _archive_base(root, *, create=False):
    base = root
    for component in ("archive", "global"):
        base = base / component
        if create:
            base.mkdir(mode=0o700, exist_ok=True)
        try:
            _directory(base, private=True)
        except FileNotFoundError:
            if create:
                raise
    return base


def _binding(root, source):
    name = source.name
    try:
        _directory(source.parent)
        tree_hash, revision = _snapshot(source)
    except FileNotFoundError as exc:
        if not os.path.lexists(source):
            raise SkillNotFound(f"library skill '{name}' is not installed") from exc
        raise
    _, pins = lifecycle._load(root)
    if lifecycle._key("global", name) in pins["pins"]:
        raise StoreError(f"library skill '{name}' is pinned")
    return tree_hash, revision


def _plan_binding(source, tree_hash, revision):
    return _digest(["explicit-library-archive", str(source), tree_hash, revision])


def _preview_result(source, base, tree_hash, plan_id):
    archive_id = plan_id[:32]
    return {"status": "preview", "name": source.name, "source": str(source),
            "path": str(base / archive_id / TREE), "tree_sha256": tree_hash,
            "archive_id": archive_id, "plan_id": plan_id}


def _source(root, name):
    lifecycle._key("global", name)
    return root / "skills" / name


def preview_archive(store, name):
    try:
        root = lifecycle._root(store.data_dir)
        source = _source(root, name)
        base = _archive_base(root)
        tree_hash, revision = _binding(root, source)
        plan_id = issue_plan_token(_plan_binding(source.as_posix(), tree_hash, revision))
        return _preview_result(source, base, tree_hash, plan_id)
    except (OSError, ValueError, RuntimeError) as exc:
        raise StoreError("unable to inspect the archive source safely") from exc


def _checked_move(source, destination, expected):
    source_info = _directory(source)
    if _directory(destination.parent).st_dev != source_info.st_dev:
        raise StoreError("archive and library must be on the same filesystem")
    if os.path.lexists(destination):
        raise StoreError("archive move destination is occupied")
    os.rename(source, destination)
    try:
        actual, _ = _snapshot(destination)
        if actual == expected:
            return
    except (OSError, StoreError, ValueError, RuntimeError):
        pass
    raise StoreError(f"move completed at {str(destination)!r}, but the folder could not be verified")


def _reconcile(store, result, action, name):
    try:
        store.init_db()
        action(name)
    except (OSError, StoreError):
        result["index_warning"] = INDEX_WARNING
    return result


def apply_archive(store, name, plan_id):
    if not is_plan_token(plan_id):
        raise StoreError("invalid archive plan ID")
    try:
        root = lifecycle._root(store.data_dir)
        source = _source(root, name)
        with _skill_and_index_locks(source.parent, source), mutation_lock(root / "pins.json"):
            return _apply_locked(store, root, source, plan_id)
    except (OSError, ValueError, RuntimeError) as exc:
        raise StoreError("could not move the library skill safely") from exc


def _apply_locked(store, root, source, plan_id):
    base = _archive_base(root)
    archive_id = plan_id[:32]
    if os.path.lexists(base / archive_id):
        raise StoreError("archive plan was already used")
    tree_hash, revision = _binding(root, source)
    if not matches_plan_token(plan_id, _plan_binding(source.as_posix(), tree_hash, revision)):
        raise StoreError("archive preview is stale; preview again")
    receipt = {"version": 1, "archive_id": archive_id, "name": source.name,
               "source": source.as_posix(), "plan_id": plan_id, "revision": revision,
               "tree_sha256": tree_hash, "archived_at": now_iso()}
    encoded = _encode(receipt) + "\n"
    if len(encoded) > MAX_RECEIPT_BYTES:
        raise StoreError("archive source path exceeds the receipt size limit")
    entry = _archive_base(root, create=True) / archive_id
    entry.mkdir(mode=0o700)
    atomic_write_text(entry / RECEIPT, encoded)
    if _binding(root, source) != (tree_hash, revision):
        raise StoreError("archive source changed after review")
    _checked_move(source, entry / TREE, tree_hash)
    result = _preview_result(source, base, tree_hash, plan_id)
    result["status"] = "archived"
    return _reconcile(store, result, store._drop_index_row, source.name)


def _receipt_matches(receipt, archive_id):
    return (isinstance(receipt, dict) and type(receipt.get("version")) is int
            and receipt["version"] == 1 and receipt.get("archive_id") == archive_id
            and is_sha256_hex(receipt.get("tree_sha256")) and is_sha256_hex(receipt.get("revision"))
            and isinstance(receipt.get("source"), str) and is_plan_token(receipt.get("plan_id"))
            and receipt["plan_id"][:32] == archive_id
            and PurePosixPath(receipt["source"]).name == receipt.get("name")
            and matches_plan_token(receipt["plan_id"], _plan_binding(
                receipt["source"], receipt["tree_sha256"], receipt["revision"])))


def _read_receipt(entry):
    try:
        _directory(entry, private=True)
        path = entry / RECEIPT
        if not stat.S_ISREG(_metadata(path).st_mode):
            raise ValueError
        receipt = json.loads(read_regular_file(path, MAX_RECEIPT_BYTES, follow_symlinks=False),
                             object_pairs_hook=lifecycle._unique_object)
        if not _receipt_matches(receipt, entry.name):
            raise ValueError
        lifecycle._key("global", receipt.get("name"))
        return receipt
    except (OSError, ValueError, StoreError, RecursionError) as exc:
        raise StoreError("invalid or missing archive receipt") from exc


def restore_archive(store, archive_id):
    if not is_valid_review_id(archive_id):
        raise StoreError("invalid archive ID")
    try:
        root = lifecycle._root(store.data_dir)
        entry = _archive_base(root) / archive_id
        receipt = _read_receipt(entry)
        destination = _source(root, receipt["name"])
        with _skill_and_index_locks(destination.parent, destination):
            return _restore_locked(store, entry, receipt, destination)
    except (OSError, ValueError, RuntimeError) as exc:
        raise StoreError("could not restore the archive safely") from exc


def _restore_locked(store, entry, receipt, destination):
    if _read_receipt(entry) != receipt:
        raise StoreError("archive receipt changed during restore")
    source = entry / TREE
    if not os.path.lexists(source):
        raise StoreError("archive has no skill folder to restore")
    if os.path.lexists(destination):
        raise StoreError("archive restore destination is occupied")
    expected = receipt["tree_sha256"]
    actual, _ = _snapshot(source)
    if actual != expected:
        raise StoreError("archived skill differs from its receipt")
    _checked_move(source, destination, expected)
    result = {"status": "restored", "archive_id": entry.name,
              "name": destination.name, "path": str(destination)}
    return _reconcile(store, result, store._upsert_entry, destination.name)
