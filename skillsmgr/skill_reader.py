"""Current document and supporting-file facts for one selected skill."""

from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

from . import paths, scopes
from .documents import DISABLED_DOCUMENT, document_path
from .errors import SkillNotFound, StoreError
from .file_reads import FileTooLarge, file_revision, read_regular_file_with_stat
from .frontmatter import MAX_DOCUMENT_CHARS, FrontmatterError, parse_frontmatter
from .hygiene import claude_skill_listing
from .risk import risk_file_listing


def _read_document(folder: Path, document: Path) -> tuple[bytes, os.stat_result]:
    """Bound the read and keep it tied to the selected directory and file."""
    before = document.lstat()
    raw, opened = read_regular_file_with_stat(
        document, 4 * MAX_DOCUMENT_CHARS + 3, follow_symlinks=False
    )
    if file_revision(before) != file_revision(opened) or folder.resolve(strict=True) != folder:
        raise OSError("skill folder or document moved")
    return raw, opened


def _supporting_files(folder: Path) -> tuple[list[dict], bool]:
    entries = risk_file_listing(folder)
    files = [
        {"path": row["path"], "lines": _line_count(row.get("contents"))}
        for row in entries if not row.get("truncated")
    ]
    return sorted(files, key=lambda row: row["path"]), any(row.get("truncated") for row in entries)


def _line_count(text: str | None) -> int | None:
    if text is None:
        return None
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.count("\n") + int(bool(normalized) and not normalized.endswith("\n"))


def read_skill_view(scope: str, name: str, target_path: str) -> dict:
    """Return literal UTF-8 and the rendered-source body from the same read."""
    folder = scopes.reader_directory(scope, name, target_path)
    try:
        document = document_path(folder)
        if document is None:
            raise SkillNotFound("The selected skill folder has no readable skill document.")
        folder_info = folder.stat(follow_symlinks=False)
        raw, opened = _read_document(folder, document)
        text = raw.decode("utf-8")
    except FileTooLarge:
        raise StoreError("This skill document exceeds the reader size limit.") from None
    except (OSError, RuntimeError, ValueError):
        raise StoreError("The selected skill document could not be read as a regular UTF-8 file.") from None
    try:
        fields, body = parse_frontmatter(text)
    except FrontmatterError:
        fields, body = None, text
    files, incomplete = _supporting_files(folder)
    if scopes.reader_directory(scope, name, target_path) != folder:
        raise SkillNotFound("The selected skill folder moved. Refresh files to find it.")
    _verify_selection(folder_info, document, opened)
    listing = None
    if scope == "claude-code" and fields is not None:
        listing = claude_skill_listing(name, fields, disabled=document.name == DISABLED_DOCUMENT, home=paths.home_dir())
    return {
        "path": str(folder),
        "filename": document.name,
        "content_hash": sha256(raw).hexdigest(),
        "raw": text,
        "body": body,
        "lines": _line_count(text),
        "files": files,
        "files_incomplete": incomplete,
        "claude_listing": listing,
    }


def _verify_selection(folder_info: os.stat_result, document: Path, opened: os.stat_result) -> None:
    folder = document.parent
    try:
        if (os.path.samestat(folder_info, folder.stat(follow_symlinks=False))
                and document_path(folder) == document
                and file_revision(document.lstat()) == file_revision(opened)):
            return
    except OSError:
        pass
    raise SkillNotFound("The selected skill folder or document changed. Refresh files to find it.")
