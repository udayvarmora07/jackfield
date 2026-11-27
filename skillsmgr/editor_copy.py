"""Publish the Editor's new copies and guard their removal with tree receipts."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from . import batch, scopes
from .atomic_io import EDIT_STAGE_PREFIX, atomic_write_text, rename_new_directory
from .diagnostics import diagnose
from .documents import ACTIVE_DOCUMENT, check_edit_target, reject_conflicting_documents
from .errors import StoreError
from .file_reads import read_regular_file
from .path_safety import mkdir_private
from .store import MAX_COMPATIBILITY, MAX_DESCRIPTION, _skill_and_index_locks
from .validator import validate_skill_name


@contextmanager
def _staging_directory(parent: Path):
    staging = tempfile.TemporaryDirectory(prefix=EDIT_STAGE_PREFIX, dir=parent)
    try:
        yield Path(staging.name)
    finally:
        # A cleanup failure must not hide a completed save or its Undo receipt.
        try:
            staging.cleanup()
        except OSError as exc:
            diagnose(f"could not clean up Editor staging at {staging.name}", exc)


def _scope(scope_id: str) -> scopes.Scope:
    scope = scopes.scope_by_id(scope_id)
    if scope is None:
        raise scopes.unknown_scope_error(scope_id)
    return scope


def _mutation_lock(scope: scopes.Scope, folder: Path):
    if scope.id == "global":
        return _skill_and_index_locks(scopes._global_store().skills_dir, folder)
    return scopes._scope_mutation_lock(folder)


def _active_source(scope: scopes.Scope, name: str, expected_path: str) -> Path:
    source = scopes.reader_directory(scope.id, name, expected_path)
    if source != Path(expected_path) or not source.is_relative_to(scope.base.resolve()):
        raise StoreError("The selected source folder changed. Refresh files before saving.")
    scopes._check_mutation_documents(source)
    reject_conflicting_documents(source, name, scope_id=scope.id)
    return source


def _prepare_source(scope: scopes.Scope, name: str, expected: tuple[str, str],
                    fields: dict[str, str], prepared: Path) -> str:
    source = _active_source(scope, name, expected[0])
    with _mutation_lock(scope, source):
        _active_source(scope, name, expected[0])
        original_tree = batch._batch_tree_hash(source)
        document = source / ACTIVE_DOCUMENT
        original = read_regular_file(document, 4 * 1024 * 1024, follow_symlinks=False).decode("utf-8")
        check_edit_target(document, original, expected)
        scopes._copy_skill_tree(source, prepared)
        if batch._batch_tree_hash(prepared) != original_tree or batch._batch_tree_hash(source) != original_tree:
            raise StoreError("The source files changed while copying. Refresh files before saving.")
    content, changed = scopes.edited_skill_text(original, name, scope.id, **fields)
    if changed:
        atomic_write_text(prepared / ACTIVE_DOCUMENT, content)
    return batch._batch_tree_hash(prepared)


def _missing_destination(scope: scopes.Scope, dest: Path) -> None:
    current_scope = _scope(scope.id)
    if dest.parent != current_scope.base.resolve() or scopes._availability(current_scope) != "writable":
        raise StoreError("The destination folder changed or is unavailable. Refresh files before saving.")
    if os.path.lexists(dest) or scopes.safe_scope_skill_path(current_scope, dest.name) != dest:
        raise StoreError("A copy or folder already exists here. Refresh files before saving.")


def _validate_library_fields(fields: dict[str, str]) -> None:
    if len(fields.get("description", "").strip()) > MAX_DESCRIPTION:
        raise StoreError(f"description exceeds {MAX_DESCRIPTION} characters")
    if len(fields.get("compatibility", "")) > MAX_COMPATIBILITY:
        raise StoreError(f"compatibility exceeds {MAX_COMPATIBILITY} characters")


def _install(scope: scopes.Scope, name: str, root: Path, prepared: Path, tree_hash: str) -> dict:
    dest = scope.base.resolve() / name
    if dest.parent != root:
        raise StoreError("The destination folder changed. Refresh files before saving.")
    _missing_destination(scope, dest)
    with _mutation_lock(scope, dest):
        _missing_destination(scope, dest)
        with _staging_directory(dest.parent) as staging:
            stage = staging / "copy.skillsmgr-stage"
            scopes._copy_skill_tree(prepared, stage)
            if batch._batch_tree_hash(stage) != tree_hash:
                raise StoreError("The staged copy could not be verified.")
            _missing_destination(scope, dest)
            rename_new_directory(stage, dest)
        receipt = {"path": str(dest), "tree_hash": tree_hash}
        if scope.id == "global":
            try:
                scopes._global_store()._upsert_entry(name)
            except (OSError, StoreError) as exc:
                diagnose("could not index an edited copy", exc)
                receipt["warning"] = "The file was saved. Rebuild the library index from Advanced."
        return receipt


def save_copies(name: str, from_scope: str, destinations: dict[str, Path], *,
                expected: tuple[str, str], fields: dict[str, str]) -> dict:
    validate_skill_name(name)
    if not destinations or len(destinations) > 500 or from_scope in destinations:
        raise StoreError("Choose one or more other places to receive the edited copy.")
    scope = _scope(from_scope)
    store = scopes._global_store()
    store._check_store_layout()
    installed = {}
    skipped = []
    try:
        mkdir_private(store.data_dir)
        with _staging_directory(store.data_dir) as staging:
            prepared = staging / name
            tree_hash = _prepare_source(scope, name, expected, fields, prepared)
            for target_id, root in destinations.items():
                try:
                    if target_id == "global":
                        _validate_library_fields(fields)
                    installed[target_id] = _install(_scope(target_id), name, root, prepared, tree_hash)
                except (OSError, ValueError, StoreError) as exc:
                    skipped.append({"scope": target_id, "reason": str(exc)})
    except (OSError, ValueError) as exc:
        raise StoreError(f"The edited copies could not be prepared: {exc}") from exc
    return {"name": name, "from_scope": from_scope, "synced": list(installed),
            "installed": installed, "skipped": skipped}


def undo_copy(scope_id: str, name: str, expected: tuple[str, str]) -> dict:
    validate_skill_name(name)
    scope = _scope(scope_id)
    dest = scope.base.resolve() / name
    path, tree_hash = expected
    try:
        with _mutation_lock(scope, dest):
            if dest != Path(path) or dest.parent != scope.base.resolve() or batch._batch_tree_hash(dest) != tree_hash:
                raise StoreError("This added copy changed on disk. It was kept in place.")
            if scope_id == "global":
                return scopes._global_store()._remove_unlocked(name, report_index_failure=True)
            trash = scopes._sync_trash_path(scope, scope_id, name)
            scopes._move_scoped_recovery(scope, scope_id, name, dest, trash, dest)
    except (OSError, ValueError) as exc:
        raise StoreError(f"Could not undo the new copy: {exc}") from exc
    return {"name": name, "scope": scope_id, "action": "trashed", "trash_path": str(trash)}
