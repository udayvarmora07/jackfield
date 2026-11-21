"""Archive inspection, safe extraction, and staged skill commit helpers."""

from __future__ import annotations

import bz2
import contextlib
import gzip
import hashlib
import io
from itertools import zip_longest
import lzma
import ntpath
import os
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile
import zlib
from collections.abc import Iterator
from pathlib import Path

from . import __version__
from . import path_safety
from .errors import StoreError
from .sidecar_binding import MANAGER_SIDECARS
from .atomic_io import is_sha256_hex, strict_regular_tree_files, tree_content_hash, tree_hash_matches
from .diagnostics import diagnose as _diagnose
from .documents import ACTIVE_DOCUMENT, DISABLED_DOCUMENT, DOCUMENT_NAMES
from .file_reads import read_regular_file_with_stat
from .frontmatter import FrontmatterError, parse_frontmatter
from .validator import validate_skill_name


class ArchiveError(StoreError):
    """Raised for archive validation or extraction failures (a ``StoreError``)."""


class BackupSourceChanged(ArchiveError):
    """The staged export observed concurrent source changes and can be retried."""

    status = 409
    code = "backup_source_changed"


MAX_ARCHIVE_COMPRESSED_BYTES = 25 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 12_000
MAX_ARCHIVE_DIRECTORIES = 12_000
MAX_ZIP_ARCHIVE_MEMBERS = 200
MAX_ARCHIVE_PATH_LENGTH = 512
MAX_ARCHIVE_NESTING = 16
MAX_ARCHIVE_COMPRESSION_RATIO = 1000
_WINDOWS_PATHS = os.name == "nt"
_WINDOWS_DEVICE_NAMES = frozenset({"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{prefix}{digit}" for prefix in ("COM", "LPT") for digit in "123456789¹²³"
})
_WINDOWS_RESERVED_CHARACTERS = frozenset('<>:"|?*')
# Hard ceiling on how far into the *decompressed* tar stream any read may
# reach.  The expanded-size budget counts member payloads only; headers,
# PAX/GNU long-name records and 512-byte padding ride on top of it. Keep a
# separate cap on that overhead as well as the individual payload budgets.
MAX_ARCHIVE_DECOMPRESSED_BYTES = MAX_ARCHIVE_EXPANDED_BYTES + 24 * 1024 * 1024

_TAR_DECOMPRESSION_ERRORS = (
    tarfile.TarError,
    OSError,
    EOFError,
    zlib.error,
    lzma.LZMAError,
    RecursionError,
    ValueError,
)


# Manager-owned evidence files.  They describe *this* install (registry
# provenance, source-lock identity) and are unauthenticated, so a copy that
# arrives from outside — an added folder, an archive, an upload — is never
# trusted: a forged provenance file once made ``Store.get`` report
# ``hash_verified: true`` for a skill that was never fetched (R2/S2).


def ignore_manager_sidecars(_directory: str, names: list[str]) -> set[str]:
    """``shutil.copytree`` ignore callable that drops manager sidecars at any depth."""
    return {name for name in names if name in MANAGER_SIDECARS}


def strip_manager_sidecars(root: Path) -> list[str]:
    """Remove every manager sidecar below *root*; return the relative paths removed.

    Symlinks are unlinked, never followed.  A sidecar name used by a directory
    is removed as a tree, because nothing legitimate is stored under it.
    """
    return _strip_sidecars(root, _sidecar_paths(root))


def _sidecar_paths(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.name in MANAGER_SIDECARS]


def _strip_sidecars(root: Path, candidates: list[Path]) -> list[str]:
    removed: list[str] = []
    try:
        for path in sorted(candidates, key=lambda item: len(item.parts), reverse=True):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(path.relative_to(root).as_posix())
    except OSError as exc:
        raise ArchiveError(f"could not remove manager evidence from intake: {exc}") from exc
    return removed


def sanitize_import_tree(root: Path, skills: list[dict]) -> None:
    """Drop manager sidecars and normalize valid legacy hashes that included them."""
    sidecars = _sidecar_paths(root)
    affected: set[str] = set()
    for path in sidecars:
        parts = path.relative_to(root).parts
        if len(parts) >= 3 and parts[0] == "skills":
            affected.add(parts[1])
    for entry in skills:
        name, expected = entry["name"], entry.get("content_hash")
        source = root / "skills" / name
        if name in affected and expected and tree_hash_matches(source, expected):
            entry["content_hash"] = tree_content_hash(source, exclude=MANAGER_SIDECARS)
    _strip_sidecars(root, sidecars)


def normalize_member_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ArchiveError(f"unsafe archive member: {name!r}")
    # Reject Windows separators on every host so a tar authored on Windows
    # cannot smuggle a nested path past the "/" split below (tar member
    # names are "/"-separated per POSIX; "\" must never become a separator).
    if name.startswith(("/", "\\")) or "\\" in name:
        raise ArchiveError(f"unsafe archive member: {name!r}")
    # Reject drive-letter prefixes ("C:...", including slash variants) on
    # every host so extraction stays inside the managed root on Windows too;
    # pathlib treats "C:..." as relative on POSIX while Windows resolves it
    # against the current drive.
    if re.fullmatch(r"[A-Za-z]:.*", name):
        raise ArchiveError(f"unsafe archive member: {name!r}")
    normalized = name.rstrip("/")
    parts = normalized.split("/") if normalized else []
    if not parts or any(_unsupported_member_component(part) for part in parts):
        raise ArchiveError(f"unsafe archive member: {name!r}")
    return "/".join(parts)


def _unsupported_member_component(part: str) -> bool:
    if part in ("", ".", ".."):
        return True
    if not _WINDOWS_PATHS:
        return False
    return (
        part.endswith((" ", "."))
        or part.split(".", 1)[0].rstrip(" ").upper() in _WINDOWS_DEVICE_NAMES
        or any(char in _WINDOWS_RESERVED_CHARACTERS or ord(char) < 32 for char in part)
    )


def _member_path_key(name: str) -> str:
    return ntpath.normcase(name) if _WINDOWS_PATHS else name


def _validate_archive_limits(
    name: str,
    file_size: int,
    compressed_size: int,
    seen: set[str],
    expanded_size: int,
    *,
    max_members: int,
) -> tuple[str, int]:
    if len(name) > MAX_ARCHIVE_PATH_LENGTH:
        raise ArchiveError(f"archive member path is too long: {name!r}")
    normalized = normalize_member_name(name)
    if len(normalized.split("/")) > MAX_ARCHIVE_NESTING:
        raise ArchiveError(f"archive member path is nested too deeply: {name!r}")
    key = _member_path_key(normalized)
    if key in seen:
        raise ArchiveError(f"duplicate archive member: {normalized!r}")
    seen.add(key)
    if len(seen) > max_members:
        raise ArchiveError(f"archive has too many members (max {max_members})")
    if file_size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ArchiveError(f"archive member exceeds {MAX_ARCHIVE_MEMBER_BYTES} bytes: {normalized!r}")
    expanded_size += file_size
    if expanded_size > MAX_ARCHIVE_EXPANDED_BYTES:
        raise ArchiveError(f"archive expanded size exceeds {MAX_ARCHIVE_EXPANDED_BYTES} bytes")
    if expanded_size > max(compressed_size, 1) * MAX_ARCHIVE_COMPRESSION_RATIO:
        raise ArchiveError(f"archive compression ratio exceeds {MAX_ARCHIVE_COMPRESSION_RATIO}:1")
    return normalized, expanded_size


def _zip_member_is_dir(member: zipfile.ZipInfo) -> bool:
    """Use the trailing slash as the portable directory marker.

    ZIP writers vary widely in ``external_attr`` defaults.  A missing DOS/Unix
    directory bit is therefore tolerated for a slash-terminated name, while a
    positive directory bit on a non-directory name is rejected as contradictory.
    Special Unix types are rejected by the caller.
    """
    dos_dir = bool(member.external_attr & 0x10)
    name_dir = member.filename.endswith("/")
    mode = (member.external_attr >> 16) & 0o170000
    unix_dir = mode == 0o040000
    if not name_dir and (dos_dir or unix_dir):
        raise ArchiveError(f"inconsistent ZIP directory metadata: {member.filename!r}")
    return name_dir


def _validate_archive_layout(normalized: str, is_dir: bool, is_file: bool) -> None:
    if normalized in {"manifest.json", "catalog/metadata.json"}:
        if not is_file:
            raise ArchiveError(f"{normalized} must be a regular file")
        return
    parts = normalized.split("/")
    if parts[0] in {"skills", "trash", "catalog"}:
        if len(parts) == 1:
            if not is_dir:
                raise ArchiveError(f"archive root entry must be a directory: {normalized!r}")
        elif parts[0] == "catalog" and len(parts) == 2 and parts[1] != "metadata.json":
            raise ArchiveError(f"unexpected catalog archive entry: {normalized!r}")
        elif len(parts) == 2 and not is_dir and parts[0] != "catalog":
            label = "skill" if parts[0] == "skills" else "trash"
            raise ArchiveError(f"{label} archive entry must be a directory: {normalized!r}")
        elif parts[0] == "catalog" and len(parts) == 2 and not is_file:
            raise ArchiveError(f"catalog archive entry must be a regular file: {normalized!r}")
    elif parts[0] == "templates" and len(parts) == 2 and parts[1].endswith(".md"):
        if not is_file:
            raise ArchiveError(f"template archive entry must be a regular file: {normalized!r}")
    else:
        raise ArchiveError(f"unexpected archive layout: {normalized!r}")


class _ArchivePaths:
    """Track explicit and implicit paths before anything is extracted."""

    def __init__(self) -> None:
        self.files: set[str] = set()
        self.directories: dict[str, str] = {}

    def add(self, name: str, *, is_directory: bool) -> None:
        if is_directory:
            self._add_directories(name)
            return
        key = _member_path_key(name)
        if key in self.directories:
            raise ArchiveError(f"archive path is both a file and a directory: {name!r}")
        self.files.add(key)
        self._add_directories(name.rpartition("/")[0])

    def _add_directories(self, directory: str) -> None:
        while directory:
            key = _member_path_key(directory)
            previous = self.directories.get(key)
            if previous is not None:
                if previous != directory:
                    raise ArchiveError(f"archive directory aliases {previous!r}: {directory!r}")
                return
            if key in self.files:
                raise ArchiveError(f"archive path is both a file and a directory: {directory!r}")
            self.directories[key] = directory
            if len(self.directories) > MAX_ARCHIVE_DIRECTORIES:
                raise ArchiveError(f"archive has too many directories (max {MAX_ARCHIVE_DIRECTORIES})")
            directory = directory.rpartition("/")[0]


class _BoundedReader:
    """A seekable view of a decompressed stream that refuses to read past a cap.

    Walking member data on a compressed stream means decompressing it.
    Checking the *position* before delegating bounds each read or seek.
    ``_BoundedTarInfo`` also checks entire metadata payloads up front, so
    chunked tarfile reads cannot accumulate the budget before rejection.
    """

    def __init__(self, raw, limit: int):
        self._raw = raw
        self._limit = limit

    def _check(self, end: int) -> None:
        if end > self._limit:
            raise ArchiveError(f"archive decompressed size exceeds {self._limit} bytes")

    def read(self, size: int = -1) -> bytes:
        position = self._raw.tell()
        if size is None or size < 0:
            # Unbounded read: ask for one byte past the cap so overflow is seen.
            size = max(self._limit - position + 1, 0)
        else:
            self._check(position + size)
        data = self._raw.read(size)
        self._check(position + len(data))
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._check(offset)
        elif whence == 1:
            self._check(self._raw.tell() + offset)
        else:  # pragma: no cover - tarfile never seeks from the end
            raise ArchiveError("unsupported archive seek")
        return self._raw.seek(offset, whence)

    def tell(self) -> int:
        return self._raw.tell()

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        self._raw.close()


class _BoundedTarInfo(tarfile.TarInfo):
    """Check extension sizes before tarfile accumulates their payloads.

    Newer tarfile versions read PAX/GNU metadata in chunks, so bounding each
    read alone allows the stream budget to accumulate in memory before the
    final read is refused.  ``_proc_member`` is tarfile's subclass dispatch
    hook, including for recursively processed extension headers.
    """

    def _proc_member(self, tar):
        if self.type in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.SOLARIS_XHDTYPE,
                         tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK):
            tar.fileobj._check(tar.fileobj.tell() + self._block(self.size))
        return super()._proc_member(tar)


def _open_decompressed(path: Path):
    with path.open("rb") as probe:
        magic = probe.read(6)
    if magic.startswith(b"\x1f\x8b"):
        return gzip.open(path, "rb")
    if magic.startswith(b"BZh"):
        return bz2.open(path, "rb")
    if magic.startswith(b"\xfd7zXZ\x00"):
        return lzma.open(path, "rb")
    return path.open("rb")


@contextlib.contextmanager
def open_tar(path: Path):
    """Open a tar archive (plain, gzip, bzip2 or xz) behind a decompression cap.

    Yields a ``tarfile.TarFile`` reading through ``_BoundedReader``.  Every
    decompressor or tar-format failure becomes ``ArchiveError``, so a hostile
    or truncated stream can never escape as a raw ``OSError``/``LZMAError``.
    """
    compressed_size = path.stat().st_size
    if compressed_size > MAX_ARCHIVE_COMPRESSED_BYTES:
        raise ArchiveError(f"archive compressed size exceeds {MAX_ARCHIVE_COMPRESSED_BYTES} bytes")
    try:
        raw = _open_decompressed(path)
    except _TAR_DECOMPRESSION_ERRORS as exc:
        raise ArchiveError(f"invalid archive: {exc}") from exc
    reader = _BoundedReader(raw, MAX_ARCHIVE_DECOMPRESSED_BYTES)
    try:
        try:
            tar = tarfile.open(fileobj=reader, mode="r:", tarinfo=_BoundedTarInfo)  # type: ignore[arg-type]
        except _TAR_DECOMPRESSION_ERRORS as exc:
            raise ArchiveError(f"invalid archive: {exc}") from exc
        with tar:
            try:
                yield tar
            except ArchiveError:
                raise
            except _TAR_DECOMPRESSION_ERRORS as exc:
                raise ArchiveError(f"invalid archive: {exc}") from exc
    finally:
        reader.close()


def _iter_tar_members(tar: tarfile.TarFile):
    """Yield members one header at a time, never materialising the full list.

    ``tar.getmembers()`` reads every header before a single cap applies, so a
    13 KB bz2 of repeated headers once reached 373 MB RSS and 49 s (R1/S1).
    The caller validates each member *before* asking for the next, so the
    member-count, per-member and expanded-size caps stop the walk early.
    """
    while True:
        try:
            member = tar.next()
        except ArchiveError:
            raise
        except _TAR_DECOMPRESSION_ERRORS as exc:
            raise ArchiveError(f"invalid archive: {exc}") from exc
        if member is None:
            return
        yield member


def validate_members(tar: tarfile.TarFile, compressed_size: int) -> list[tuple[tarfile.TarInfo, str]]:
    if compressed_size > MAX_ARCHIVE_COMPRESSED_BYTES:
        raise ArchiveError(f"archive compressed size exceeds {MAX_ARCHIVE_COMPRESSED_BYTES} bytes")
    members: list[tuple[tarfile.TarInfo, str]] = []
    seen: set[str] = set()
    paths = _ArchivePaths()
    expanded_size = 0
    manifest_count = 0
    for member in _iter_tar_members(tar):
        if not (member.isdir() or member.isreg()):
            raise ArchiveError(f"unsupported archive member type: {member.name!r}")
        normalized, expanded_size = _validate_archive_limits(
            member.name, member.size if member.isreg() else 0, compressed_size, seen, expanded_size,
            max_members=MAX_ARCHIVE_MEMBERS,
        )
        _validate_archive_layout(normalized, member.isdir(), member.isreg())
        paths.add(normalized, is_directory=member.isdir())
        if normalized == "manifest.json":
            manifest_count += 1
        members.append((member, normalized))
    if manifest_count != 1:
        raise ArchiveError("archive must contain exactly one manifest.json")
    return members


def _export_revision(info: os.stat_result) -> tuple[int, ...]:
    # Windows can infer executable bits from the filename for a path stat.
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _export_source_changed(path: Path) -> BackupSourceChanged:
    return BackupSourceChanged(f"backup source changed during export: {path}; retry after changes finish")


def _export_file_revision(path: Path) -> tuple[int, ...] | None:
    try:
        return _export_revision(path.lstat())
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ArchiveError(f"could not inspect backup source: {path}") from exc


_ExportRootRevision = tuple[tuple[int, ...], frozenset[str] | None] | None


def _export_root_revision(path: Path) -> _ExportRootRevision:
    try:
        metadata = path.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ArchiveError(f"could not inspect backup source: {path}") from exc
    try:
        # Directory timestamps can be coarse. Compare actual member names so
        # moving a skill within one clock tick is still observable.
        names = frozenset(child.name for child in path.iterdir()) if stat.S_ISDIR(metadata.st_mode) else None
    except FileNotFoundError as exc:
        raise _export_source_changed(path) from exc
    except OSError as exc:
        raise ArchiveError(f"could not list backup source: {path}") from exc
    return _export_revision(metadata), names


def export_root_revisions(paths: tuple[Path, ...]) -> dict[Path, _ExportRootRevision]:
    """Observe the roots before listing them, including roots that are absent."""
    return {path: _export_root_revision(path) for path in paths}


def _export_tree_files(root: Path) -> Iterator[Path]:
    try:
        yield from strict_regular_tree_files(root, exclude=MANAGER_SIDECARS)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise _export_source_changed(Path(exc.filename or root)) from exc
    except OSError as exc:
        raise ArchiveError(f"could not read backup source: {exc.filename or root}") from exc


class ExportWriter:
    """Write bounded regular files and hash exactly the bytes in the archive."""

    def __init__(self, tar: tarfile.TarFile) -> None:
        self.tar = tar
        self.seen: set[str] = set()
        self.paths = _ArchivePaths()
        self.expanded_size = 0
        self._source_files: dict[Path, tuple[int, ...]] = {}
        self._source_trees: dict[Path, tuple[Path, ...]] = {}

    def _header(self, name: str, size: int) -> tarfile.TarInfo:
        # The finished gzip stream has the exact compressed size. Until it
        # closes, use the ceiling and enforce the other budgets before reading.
        normalized, self.expanded_size = _validate_archive_limits(
            name, size, MAX_ARCHIVE_COMPRESSED_BYTES, self.seen, self.expanded_size,
            max_members=MAX_ARCHIVE_MEMBERS,
        )
        _validate_archive_layout(normalized, False, True)
        self.paths.add(normalized, is_directory=False)
        info = tarfile.TarInfo(normalized)
        info.size = size
        return info

    def add_bytes(self, name: str, payload: bytes) -> None:
        self.tar.addfile(self._header(name, len(payload)), io.BytesIO(payload))

    def add_file(self, name: str, source: Path) -> bytes:
        try:
            metadata = source.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ArchiveError(f"archive source is not a regular file: {name!r}")
            info = self._header(name, metadata.st_size)
            data, opened = read_regular_file_with_stat(source, info.size, follow_symlinks=False)
        except (OSError, ValueError) as exc:
            raise ArchiveError(f"could not read archive source {name!r}: {exc}") from exc
        revision = _export_revision(metadata)
        if len(data) != info.size or _export_revision(opened) != revision:
            raise _export_source_changed(source)
        self._source_files[source] = revision
        info.mode = metadata.st_mode & 0o777
        info.mtime = int(metadata.st_mtime)
        self.tar.addfile(info, io.BytesIO(data))
        return data

    def add_tree(self, prefix: str, root: Path, *, skill_name: str | None = None) -> str:
        digest = hashlib.sha256()
        first_member = len(self.seen)
        primary_names = {_member_path_key(name) for name in DOCUMENT_NAMES}
        document_written = False
        captured: list[Path] = []
        for source in _export_tree_files(root):
            relative = source.relative_to(root).as_posix()
            data = self.add_file(f"{prefix}/{relative}", source)
            captured.append(source)
            if skill_name is not None and _member_path_key(relative) in primary_names:
                if document_written:
                    raise ArchiveError(f"skill directory contains both enabled and disabled documents: {skill_name!r}")
                _validate_skill_document(data, skill_name)
                document_written = True
            digest.update(relative.encode("utf-8"))
            digest.update(data)
        if skill_name is not None and not document_written:
            raise ArchiveError(f"cannot back up skill {skill_name!r}: no regular skill document was read")
        if len(self.seen) == first_member:
            raise ArchiveError(f"cannot back up empty archive entry: {prefix!r}")
        self._source_trees[root] = tuple(captured)
        return digest.hexdigest()

    def verify_sources(self, roots: dict[Path, _ExportRootRevision]) -> None:
        """Refuse observed changes before publishing the staged archive."""
        for root, captured in self._source_trees.items():
            current = _export_tree_files(root)
            if any(previous != actual for previous, actual in zip_longest(captured, current)):
                raise _export_source_changed(root)
        for source, revision in self._source_files.items():
            if _export_file_revision(source) != revision:
                raise _export_source_changed(source)
        for path, revision in export_root_revisions(tuple(roots)).items():
            if revision != roots[path]:
                raise _export_source_changed(path)


def verify_export(path: Path) -> None:
    """Check the compressed size, ratio and decompression overhead before publishing."""
    with open_tar(path) as tar:
        validate_members(tar, path.stat().st_size)


def _validate_manifest_payload_labels(manifest: dict, field: str) -> None:
    labels = manifest.get(field)
    if labels is None:
        return
    if not isinstance(labels, list):
        raise ArchiveError(f"invalid archive manifest: {field} must be a list")
    seen: set[str] = set()
    for label in labels:
        if (
            not isinstance(label, str)
            or not label
            or label.startswith(".")
            or "\\" in label
            or Path(label).name != label
        ):
            raise ArchiveError(f"invalid archive manifest: {field} entry is not a plain name: {label!r}")
        key = _member_path_key(label)
        if key in seen:
            raise ArchiveError(f"invalid archive manifest: duplicate {field} entry: {label!r}")
        seen.add(key)


def validate_manifest(manifest: object) -> list[dict]:
    if not isinstance(manifest, dict):
        raise ArchiveError("invalid archive manifest: expected an object")
    if manifest.get("app") != "skills-mgr":
        raise ArchiveError("invalid archive manifest: unsupported app")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ArchiveError("invalid archive manifest: version must be semantic")
    if version.split(".", 1)[0] != __version__.split(".", 1)[0]:
        raise ArchiveError(f"unsupported archive manifest major version: {version}")
    created = manifest.get("created")
    if not isinstance(created, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created):
        raise ArchiveError("invalid archive manifest: created timestamp")
    skills = manifest.get("skills")
    if not isinstance(skills, list):
        raise ArchiveError("invalid archive manifest: skills must be a list")
    full_flag = manifest.get("full")
    if full_flag is not None and not isinstance(full_flag, bool):
        raise ArchiveError("invalid archive manifest: full must be a boolean")
    catalog_flag = manifest.get("catalog")
    if catalog_flag is not None and not isinstance(catalog_flag, bool):
        raise ArchiveError("invalid archive manifest: catalog must be a boolean")
    for field in ("trash", "templates"):
        _validate_manifest_payload_labels(manifest, field)
    validated: list[dict] = []
    names: set[str] = set()
    for entry in skills:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ArchiveError("invalid archive manifest: each skill needs a name")
        try:
            name = validate_skill_name(entry["name"])
        except ValueError as exc:
            raise ArchiveError(f"invalid archive manifest skill name: {entry['name']!r}") from exc
        if name in names:
            raise ArchiveError(f"duplicate skill in archive manifest: {name!r}")
        names.add(name)
        validated.append(dict(entry, name=name))
    return validated


def validate_zip_members(
    archive: zipfile.ZipFile, compressed_size: int
) -> list[tuple[zipfile.ZipInfo, str]]:
    """Validate ZIP members without trusting ``extractall`` path handling."""
    if compressed_size > MAX_ARCHIVE_COMPRESSED_BYTES:
        raise ArchiveError(f"archive compressed size exceeds {MAX_ARCHIVE_COMPRESSED_BYTES} bytes")
    members: list[tuple[zipfile.ZipInfo, str]] = []
    seen: set[str] = set()
    paths = _ArchivePaths()
    members_info = archive.infolist()
    if any(member.compress_size < 0 or member.file_size < 0 for member in members_info):
        raise ArchiveError("invalid ZIP member size")
    compressed_total = sum(member.compress_size for member in members_info if not member.is_dir())
    expanded_size = 0
    manifest_count = 0
    for member in members_info:
        mode = (member.external_attr >> 16) & 0o170000
        is_dir = _zip_member_is_dir(member)
        if mode == 0o120000 or (mode not in (0, 0o040000, 0o100000) and not is_dir):
            raise ArchiveError(f"unsupported archive member type: {member.filename!r}")
        # A per-member ratio keeps a stored, incompressible member from
        # masking a later bomb; the cumulative total is checked below too.
        if not is_dir and member.file_size > max(member.compress_size, 1) * MAX_ARCHIVE_COMPRESSION_RATIO:
            raise ArchiveError(f"archive compression ratio exceeds {MAX_ARCHIVE_COMPRESSION_RATIO}:1")
        normalized, expanded_size = _validate_archive_limits(
            member.filename,
            member.file_size if not is_dir else 0,
            compressed_total,
            seen,
            expanded_size,
            max_members=MAX_ZIP_ARCHIVE_MEMBERS,
        )
        _validate_archive_layout(normalized, is_dir, not is_dir)
        paths.add(normalized, is_directory=is_dir)
        if normalized == "manifest.json":
            manifest_count += 1
        members.append((member, normalized))
    if manifest_count != 1:
        raise ArchiveError("archive must contain exactly one manifest.json")
    if expanded_size > max(compressed_total, 1) * MAX_ARCHIVE_COMPRESSION_RATIO:
        raise ArchiveError(f"archive compression ratio exceeds {MAX_ARCHIVE_COMPRESSION_RATIO}:1")
    return members


def extract_zip_members(
    archive: zipfile.ZipFile,
    dest: Path,
    members: list[tuple[zipfile.ZipInfo, str]],
) -> None:
    """Extract validated ZIP regular files into a private destination."""
    expanded_written = 0
    for member, normalized in members:
        target = path_safety.contained_path(dest, *normalized.split("/"))
        if _zip_member_is_dir(member):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with archive.open(member, "r") as source, target.open("wb") as output:
                while True:
                    chunk = source.read(min(1024 * 1024, MAX_ARCHIVE_MEMBER_BYTES - written + 1))
                    if not chunk:
                        break
                    written += len(chunk)
                    expanded_written += len(chunk)
                    if written > MAX_ARCHIVE_MEMBER_BYTES:
                        raise ArchiveError(f"archive member exceeds {MAX_ARCHIVE_MEMBER_BYTES} bytes: {normalized!r}")
                    if expanded_written > MAX_ARCHIVE_EXPANDED_BYTES:
                        raise ArchiveError(f"archive expanded size exceeds {MAX_ARCHIVE_EXPANDED_BYTES} bytes")
                    output.write(chunk)
            if written != member.file_size:
                raise ArchiveError(f"ZIP member size mismatch: {normalized!r}")
        except ArchiveError:
            raise
        except (OSError, RuntimeError, zipfile.BadZipFile, zlib.error, NotImplementedError, UnicodeError) as exc:
            raise ArchiveError(f"invalid archive extraction: {exc}") from exc


def extract_members(tar: tarfile.TarFile, dest: Path, members: list[tuple[tarfile.TarInfo, str]]) -> None:
    tar_members = [member for member, _ in members]
    data_filter = getattr(tarfile, "data_filter", None)
    if callable(data_filter):
        try:
            tar.extractall(  # nosec B202 - every member passed path/type/size/layout validation above.
                dest, members=tar_members, filter=data_filter
            )
        except (OSError, tarfile.TarError, ValueError) as exc:
            raise ArchiveError(f"invalid archive extraction: {exc}") from exc
        return
    for member, normalized in members:
        target = path_safety.contained_path(dest, *normalized.split("/"))
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        source = tar.extractfile(member)
        if source is None:
            raise ArchiveError(f"archive member has no readable payload: {normalized!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
        except OSError as exc:
            raise ArchiveError(f"invalid archive extraction: {exc}") from exc


def has_skill_document(source: Path) -> bool:
    enabled = (source / ACTIVE_DOCUMENT).is_file()
    disabled = (source / DISABLED_DOCUMENT).is_file()
    if enabled and disabled:
        raise ArchiveError(f"skill directory contains both enabled and disabled documents: {source.name!r}")
    return enabled or disabled


def validate_imported_skill(source: Path, name: str) -> None:
    document = source / (ACTIVE_DOCUMENT if (source / ACTIVE_DOCUMENT).is_file() else DISABLED_DOCUMENT)
    try:
        payload = document.read_bytes()
    except OSError as exc:
        raise ArchiveError(f"invalid skill document for {name!r}: {exc}") from exc
    _validate_skill_document(payload, name)


def _validate_skill_document(payload: bytes, name: str) -> None:
    try:
        text = payload.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        data, _ = parse_frontmatter(text)
    except (UnicodeError, FrontmatterError) as exc:
        raise ArchiveError(f"invalid skill document for {name!r}: {exc}") from exc
    if data.get("name") is not None and data.get("name") != name:
        raise ArchiveError(f"skill document name {data.get('name')!r} does not match manifest name {name!r}")


def verify_full_skill_hashes(planned: list[tuple[str, Path, dict]]) -> None:
    """Verify the checksums a full archive supplies before restoring any data."""
    for name, source, entry in planned:
        if "content_hash" not in entry:
            continue  # Full backups from older versions may omit the checksum.
        expected = entry["content_hash"]
        if not is_sha256_hex(expected):
            raise ArchiveError(f"invalid content hash for '{name}'")
        try:
            verified = tree_hash_matches(source, expected)
        except OSError as exc:
            raise ArchiveError(f"could not verify archived skill '{name}': {exc}") from exc
        if not verified:
            raise ArchiveError(f"content hash mismatch for '{name}'")


def commit_staged_skill(
    source: Path,
    dest: Path,
    expected_hash: str | None,
    *,
    replace: bool,
    upsert,
) -> tuple[bool, str | None]:
    """Install under the caller's destination lock and retain blocked rollbacks."""
    dest_exists = os.path.lexists(dest)
    if dest_exists:
        if not replace:
            return False, None
        if not _compatible_destination(source, dest):
            return False, "the destination must be an unlinked skill directory"

    transaction = None
    try:
        transaction = _stage_replacement(source, dest, copytree=shutil.copytree, copyfile=shutil.copyfile, rmtree=shutil.rmtree)
        if expected_hash and not tree_hash_matches(transaction / "new", expected_hash):
            raise ArchiveError(f"content hash mismatch for '{dest.name}'")
        _publish_replacement(dest, transaction, dest_exists, move=os.replace)
        if expected_hash and not tree_hash_matches(dest, expected_hash):
            raise ArchiveError(f"committed content hash mismatch for '{dest.name}'")
        upsert(dest.name)
    except BaseException as exc:
        retained = _rollback_replacements(
            [(dest, transaction)] if transaction is not None else [],
            operation="skill import", move=os.replace, rmtree=shutil.rmtree,
        )
        if not isinstance(exc, Exception):
            raise
        if retained:
            return False, f"{exc}. Recovery files retained at {retained[0]}"
        return False, str(exc)
    shutil.rmtree(transaction, ignore_errors=True)
    return True, None


def _stage_replacement(source: Path, dest: Path, *, copytree, copyfile, rmtree) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    transaction = Path(tempfile.mkdtemp(prefix=".skillsmgr-backup.", dir=dest.parent))
    try:
        if source.is_dir():
            copytree(source, transaction / "new")
        else:
            copyfile(source, transaction / "new")
    except BaseException:
        rmtree(transaction, ignore_errors=True)
        raise
    return transaction


def _compatible_destination(source: Path, dest: Path) -> bool:
    return not dest.is_symlink() and (dest.is_dir() if source.is_dir() else dest.is_file())


def check_full_destination(source: Path, dest: Path, *, replace: bool) -> bool:
    """Return whether the exact destination exists and can be replaced if requested."""
    exists = os.path.lexists(dest)
    if exists and replace and not _compatible_destination(source, dest):
        raise ArchiveError(f"cannot replace full archive destination {dest}: expected an unlinked entry of the same type")
    return exists


def _publish_replacement(dest: Path, transaction: Path, dest_exists: bool, *, move) -> None:
    if dest_exists:
        move(dest, transaction / "old")
    move(transaction / "new", dest)


def _rollback_replacements(
    installed: list[tuple[Path, Path]], *, operation: str, move, rmtree
) -> list[Path]:
    """Undo completed renames, including a rename interrupted on return."""
    retained: list[Path] = []
    for dest, transaction in reversed(installed):
        stage, backup = transaction / "new", transaction / "old"
        try:
            if not os.path.lexists(stage) and os.path.lexists(dest):
                move(dest, stage)
            if os.path.lexists(backup):
                move(backup, dest)
        except BaseException as exc:
            retained.append(transaction)
            _diagnose(f"{operation} rollback failed for {dest}. Inspect {transaction}", exc)
        else:
            rmtree(transaction, ignore_errors=True)
    return retained


def restore_full_payload(
    entries: list[tuple[str, str, Path, Path]],
    *,
    replace: bool,
    reconcile_trash=None,
    move=None,
    rmtree=None,
    copytree=None,
    copyfile=None,
) -> tuple[list[str], list[str], list[str], bool]:
    """Install validated full-import payloads as one all-or-nothing transaction.

    ``entries`` are ``(kind, label, source, dest)`` tuples that were validated
    before any mutation. Each payload is staged on the destination filesystem,
    the previous entry is moved aside, and the staged copy is moved into place;
    any failure during installation or reconciliation rolls back the swaps. A blocked
    rollback leaves the original in its private transaction directory and
    reports the directory in diagnostics.
    """
    move = move or os.replace
    rmtree = rmtree or shutil.rmtree
    copytree = copytree or shutil.copytree
    copyfile = copyfile or shutil.copyfile
    restored: dict[str, list[str]] = {"trash": [], "templates": [], "catalog": []}
    skipped: list[str] = []
    installed: list[tuple[Path, Path]] = []
    try:
        for kind, label, source, dest in entries:
            dest_exists = check_full_destination(source, dest, replace=replace)
            if dest_exists and not replace:
                skipped.append(f"{kind}/{label}")
                continue
            transaction = _stage_replacement(source, dest, copytree=copytree, copyfile=copyfile, rmtree=rmtree)
            installed.append((dest, transaction))
            _publish_replacement(dest, transaction, dest_exists, move=move)
            restored[kind].append(label)
        if reconcile_trash is not None:
            reconcile_trash(restored["trash"])
    except BaseException as exc:
        _rollback_replacements(installed, operation="full-import", move=move, rmtree=rmtree)
        if isinstance(exc, OSError):
            raise ArchiveError(f"could not restore full archive payload: {exc}") from exc
        raise
    for _, transaction in installed:
        rmtree(transaction, ignore_errors=True)
    return restored["trash"], restored["templates"], skipped, bool(restored["catalog"])
