"""Hermetic regression corpus for the tar import/export contract."""

import io
import json
import os
import sqlite3
import tarfile
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import mock

from skillsmgr import __version__
from skillsmgr import archive as archive_mod
from skillsmgr.archive import (
    MAX_ARCHIVE_COMPRESSION_RATIO,
    MAX_ARCHIVE_MEMBER_BYTES,
    MAX_ARCHIVE_MEMBERS,
    MAX_ARCHIVE_NESTING,
    MAX_ARCHIVE_PATH_LENGTH,
    MAX_ZIP_ARCHIVE_MEMBERS,
    normalize_member_name,
)
from skillsmgr.atomic_io import tree_content_hash
from skillsmgr.sidecar_binding import PROVENANCE_FILENAME, SOURCE_LOCK_FILENAME
from skillsmgr.store import Store, StoreError


_CREATED = "2026-09-08T00:00:00Z"


def _document(name: str, body: str | None = None) -> bytes:
    body = body or f"# {name}\n\nImported body.\n"
    return (
        f"---\nname: {name}\ndescription: Use this skill for archive tests.\n---\n"
        f"{body}"
    ).encode("utf-8")


def _manifest(*names: str) -> bytes:
    return json.dumps(
        {
            "app": "skills-mgr",
            "version": __version__,
            "created": _CREATED,
            "skills": [{"name": name} for name in names],
        }
    ).encode("utf-8")


def _write_tar(path: Path, members: list[tuple[str, bytes | None, int | None]], *, names=()) -> None:
    """Write a deliberately small tar corpus, preserving duplicate/type entries."""
    with tarfile.open(path, "w:gz") as archive:
        manifest = _manifest(*names)
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest)
        archive.addfile(info, io.BytesIO(manifest))
        for name, payload, member_type in members:
            info = tarfile.TarInfo(name)
            if member_type is not None:
                info.type = member_type
                archive.addfile(info)
            else:
                payload = payload or b""
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))


def _write_zip(path: Path, members: list[tuple[str, bytes]], *, names=(), symlinks=()) -> None:
    """Write a ZIP corpus, optionally preserving duplicate and symlink entries."""
    symlinks = set(symlinks)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", _manifest(*names))
        for name, payload in members:
            info = zipfile.ZipInfo(name)
            if name in symlinks:
                info.external_attr = (0o120777 << 16) | 0x10
            archive.writestr(info, payload)


class ArchiveContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _store(self, name: str = "manager") -> Store:
        store = Store(data_dir=self.root / name)
        store.init_db()
        return store

    def test_valid_tar_round_trip(self):
        source = self._store("source")
        source.create("demo", "Archive demo", body="round-trip body")
        archive = source.export(self.root / "round-trip.tar.gz")

        target = self._store("target")
        result = target.import_(archive)

        self.assertEqual(result["imported"], ["demo"])
        self.assertEqual(target.get("demo")["description"], "Archive demo")
        self.assertIn("round-trip body", target.get("demo")["body"])

    def test_explicit_export_of_a_fresh_library_does_not_create_store_state(self):
        source = Store(data_dir=self.root / "fresh")
        archive = source.export(self.root / "download.tar.gz", full=True)
        self.assertFalse(source.data_dir.exists())
        with tarfile.open(archive) as packed:
            self.assertEqual(packed.getnames(), ["catalog/metadata.json", "manifest.json"])

    def test_backup_keeps_previous_archive_if_a_document_disappears_after_inventory(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        skill = source.skills_dir / "demo"
        (skill / "reference.txt").write_bytes(b"keep this")
        default_path = source.export(self.root / "previous.tar.gz")
        previous_bytes = default_path.read_bytes()
        scan = source._scan_dir

        def move_after_scan(path):
            rows = scan(path)
            (skill / "SKILL.md").rename(self.root / "retired-document.md")
            return rows

        with mock.patch.object(source, "_scan_dir", side_effect=move_after_scan):
            with self.assertRaisesRegex(StoreError, "no regular skill document was read"):
                source.export(default_path)

        self.assertEqual(default_path.read_bytes(), previous_bytes)
        self.assertEqual(list(self.root.glob("*.skillsmgr-export")), [])
        target = self._store("target")
        self.assertEqual(target.import_(default_path)["imported"], ["demo"])
        self.assertEqual((target.skills_dir / "demo" / "reference.txt").read_bytes(), b"keep this")

    def test_full_backup_does_not_publish_a_skill_moved_to_trash_mid_export(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        destination = source.export(self.root / "previous.tar.gz", full=True)
        previous = destination.read_bytes()
        write_tree = archive_mod.ExportWriter.add_tree

        def move_after_capture(writer, prefix, path, **options):
            digest = write_tree(writer, prefix, path, **options)
            if prefix == "skills/demo":
                source.remove("demo")
            return digest

        with mock.patch.object(archive_mod.ExportWriter, "add_tree", move_after_capture):
            with self.assertRaisesRegex(StoreError, "backup source changed.*retry"):
                source.export(destination, full=True)
        self.assertEqual(destination.read_bytes(), previous)
        self.assertEqual(list(self.root.glob(".*.skillsmgr-export")), [])

        source.export(destination, full=True)
        target = self._store("target")
        restored = target.import_(destination, full=True)
        self.assertEqual(restored["imported"], [])
        self.assertEqual([row["name"] for row in target.trash_list()], ["demo"])

    def test_full_backup_does_not_omit_a_skill_restored_after_inventory(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        source.remove("demo")
        destination = self.root / "destination.tar.gz"
        scan = source._scan_dir
        revision = archive_mod._export_revision

        def restore_after_inventory(path):
            rows = scan(path)
            source.restore("demo")
            return rows

        def coarse_metadata(info):
            # Simulate an unchanged fingerprint on coarse-timestamp filesystems.
            return revision(info)[:3]

        with mock.patch.object(source, "_scan_dir", side_effect=restore_after_inventory), \
             mock.patch.object(archive_mod, "_export_revision", side_effect=coarse_metadata):
            with self.assertRaisesRegex(StoreError, "backup source changed.*retry"):
                source.export(destination, full=True)
        self.assertFalse(destination.exists())
        self.assertTrue((source.skills_dir / "demo" / "SKILL.md").is_file())

    def test_backup_keeps_previous_copy_after_a_supporting_file_changes_mid_export(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        companion = source.skills_dir / "demo" / "references" / "notes.txt"
        companion.parent.mkdir()
        companion.write_bytes(b"original")
        destination = source.export(self.root / "previous.tar.gz")
        previous = destination.read_bytes()
        write_tree = archive_mod.ExportWriter.add_tree

        for change in (lambda: companion.write_bytes(b"changed supporting file"),
                       lambda: companion.with_name("new.txt").write_bytes(b"late file")):
            with self.subTest(change=change):
                def change_after_capture(writer, *args, **options):
                    digest = write_tree(writer, *args, **options)
                    change()
                    return digest

                with mock.patch.object(archive_mod.ExportWriter, "add_tree", change_after_capture):
                    with self.assertRaisesRegex(StoreError, "backup source changed.*retry"):
                        source.export(destination)
                self.assertEqual(destination.read_bytes(), previous)

    def test_backup_refuses_unreadable_supporting_directories(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        references = source.skills_dir / "demo" / "references"
        references.mkdir()
        (references / "notes.txt").write_bytes(b"supporting content")
        scandir = os.scandir

        for full in (False, True):
            destination = source.export(self.root / "previous.tar.gz", full=full)
            previous = destination.read_bytes()
            for failing_scans in ((1,), (2,), (1, 2)):
                with self.subTest(full=full, failing_scans=failing_scans):
                    scans = 0

                    def scan_directory(path):
                        nonlocal scans
                        if Path(path) == references:
                            scans += 1
                            if scans in failing_scans:
                                raise PermissionError(13, "Permission denied", str(path))
                        return scandir(path)

                    with mock.patch.object(os, "scandir", side_effect=scan_directory):
                        with self.assertRaisesRegex(StoreError, "could not read backup source.*references"):
                            source.export(destination, full=full)
                    self.assertEqual(scans, failing_scans[0])
                    self.assertEqual(destination.read_bytes(), previous)
                    self.assertEqual(list(self.root.glob(".*.skillsmgr-export")), [])

    def test_export_checks_active_document_bytes_and_accepts_disabled_crlf_documents(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        source.disable("demo")
        skill = source.skills_dir / "demo"
        document = skill / "SKILL.md.disabled"
        original = _document("demo").replace(b"\n", b"\r\n")
        document.write_bytes(original)
        saved = source.export(self.root / "verified.tar.gz")

        for payload, reason in ((b"\xff", "invalid skill document"),
                                (_document("different"), "does not match manifest name")):
            with self.subTest(reason=reason):
                document.write_bytes(payload)
                with self.assertRaisesRegex(StoreError, reason):
                    source.export(saved)
        document.write_bytes(original)
        (skill / "SKILL.md").write_bytes(original)
        with self.assertRaisesRegex(StoreError, "both enabled and disabled"):
            source.export(saved)

        target = self._store("target")
        self.assertEqual(target.import_(saved)["imported"], ["demo"])
        self.assertEqual((target.skills_dir / "demo" / document.name).read_bytes(), original)

    def test_full_export_will_not_list_a_trash_entry_without_materialized_members(self):
        source = self._store("source")
        (source.trash_dir / "demo-2026-09-08_12-00-00Z").mkdir()
        target = self.root / "empty-trash.tar.gz"
        with self.assertRaisesRegex(StoreError, "cannot back up empty archive entry"):
            source.export(target, full=True)
        self.assertFalse(target.exists())

    def test_backup_destination_cannot_replace_files_from_the_library(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        document = source.skills_dir / "demo" / "SKILL.md"
        template = source.templates_dir / "template.md"
        template.write_bytes(b"template")
        inputs = {path: path.read_bytes() for path in (document, template, source.db_path)}
        future_snapshot = source.data_dir / "snapshots" / "bad.tar.gz"
        for path in (*inputs, future_snapshot):
            with self.subTest(path=path):
                with self.assertRaisesRegex(StoreError, "destination would overwrite managed data"):
                    source.backup(path, full=True)
        self.assertEqual({path: path.read_bytes() for path in inputs}, inputs)
        self.assertFalse(future_snapshot.parent.exists())

    def test_backup_destination_checks_a_linked_parent_before_creating_files(self):
        source = self._store("source")
        alias = self.root / "linked-folder"
        try:
            alias.symlink_to(source.skills_dir, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        with self.assertRaisesRegex(StoreError, "destination would overwrite managed data"):
            source.backup(alias / "new-directory" / "backup.tar.gz")
        self.assertFalse((source.skills_dir / "new-directory").exists())

    def test_backup_destination_cannot_replace_lifecycle_and_project_state(self):
        source = self._store("source")
        relative = ("pins.json", "usage/consent.json", "pin-backups/receipt.json",
                    "native-backups/receipt.json", "project-lock-backups/receipt.json")
        existing = {source.data_dir / name: name.encode("ascii") for name in relative}
        for path, previous in existing.items():
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(previous)
        future = source.data_dir / "usage" / "new-directory" / "backup.tar.gz"
        for path in (*existing, future):
            with self.subTest(path=path):
                with self.assertRaisesRegex(StoreError, "destination would overwrite managed data"):
                    source.backup(path, full=True)
        self.assertEqual({path: path.read_bytes() for path in existing}, existing)
        self.assertFalse(future.parent.exists())

    def test_backup_destination_keeps_legacy_archives_and_the_backups_directory_usable(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        paths = (source.data_dir / "existing.tar.gz", source.backups_dir / "manual" / "selected")
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(source.backup(path), path)
                self.assertEqual(source.backup(path), path)
                self.assertTrue(tarfile.is_tarfile(path))

    def test_backup_directory_link_must_not_target_another_managed_subdirectory(self):
        source = self._store("source")
        usage = source.data_dir / "usage"
        usage.mkdir()
        source.backups_dir.rmdir()
        try:
            source.backups_dir.symlink_to(usage, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        for dest in (None, source.backups_dir / "test.tar.gz"):
            with self.subTest(dest=dest):
                with self.assertRaisesRegex(StoreError, "destination would overwrite managed data"):
                    source.backup(dest)
        self.assertEqual(list(usage.iterdir()), [])

    def test_backup_uses_checked_destination_if_linked_parent_moves_during_scan(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        chosen = self.root / "chosen"
        chosen.mkdir()
        alias = self.root / "alias"
        try:
            alias.symlink_to(chosen, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(source.backup(alias / "normal.tar.gz"), alias / "normal.tar.gz")
        state = source.data_dir / "pins.json"
        state.write_bytes(b"original state")
        scan = source._scan_dir

        def retarget(path):
            alias.unlink()
            alias.symlink_to(source.data_dir, target_is_directory=True)
            return scan(path)

        with mock.patch.object(source, "_scan_dir", side_effect=retarget):
            result = source.backup(alias / "pins.json")
        self.assertEqual(state.read_bytes(), b"original state")
        self.assertEqual(result, chosen.resolve() / "pins.json")
        self.assertTrue(tarfile.is_tarfile(result))

    def test_json_decoder_recursion_error_is_reported_during_import_preflight(self):
        source = self._store("source")
        source.create("demo", "Archive demo")
        packed = source.export(self.root / "full.tar.gz", full=True)
        decoder = json.loads
        target = self._store("target")
        for metadata, reason in (("skills", "invalid archive manifest"),
                                 ("profiles", "could not prepare archive catalog")):
            def fail_at_metadata(text, *args, **kwargs):
                if f'"{metadata}"' in text:
                    raise RecursionError("decoder nesting limit")
                return decoder(text, *args, **kwargs)

            with self.subTest(metadata=metadata):
                with mock.patch("json.loads", side_effect=fail_at_metadata):
                    with self.assertRaisesRegex(StoreError, reason):
                        target.import_(packed, full=True)
                self.assertEqual(target.list(), [])

    def test_absolute_and_traversal_members_are_rejected_before_extraction(self):
        victim = self.root / "victim.txt"
        victim.write_text("keep", encoding="utf-8")
        cases = {
            "absolute": "/victim.txt",
            "traversal": "skills/demo/../../victim.txt",
            "backslash": "skills\\demo\\escape.txt",
        }
        for label, member_name in cases.items():
            with self.subTest(label=label):
                archive = self.root / f"{label}.tar.gz"
                _write_tar(archive, [(member_name, b"escape", None)])
                with self.assertRaises(StoreError):
                    self._store(label).import_(archive, force=True)
                self.assertEqual(victim.read_text(encoding="utf-8"), "keep")

    def test_duplicate_members_are_rejected(self):
        archive = self.root / "duplicate.tar.gz"
        _write_tar(
            archive,
            [
                ("skills/demo/SKILL.md", _document("demo"), None),
                ("skills/demo/SKILL.md", _document("demo"), None),
            ],
        )

        with self.assertRaisesRegex(StoreError, "duplicate"):
            self._store().import_(archive)

    def test_symlink_hardlink_fifo_and_device_members_are_rejected(self):
        special_members = [
            ("symlink", getattr(tarfile, "SYMTYPE", None), "outside"),
            ("hardlink", getattr(tarfile, "LNKTYPE", None), "SKILL.md"),
            ("fifo", getattr(tarfile, "FIFOTYPE", None), None),
            ("character-device", getattr(tarfile, "CHRTYPE", None), None),
            ("block-device", getattr(tarfile, "BLKTYPE", None), None),
        ]
        for label, member_type, linkname in special_members:
            if member_type is None:  # pragma: no cover - platform tarfile guard
                continue
            with self.subTest(member_type=label):
                archive = self.root / f"{label}.tar.gz"
                _write_tar(archive, [(f"skills/demo/{label}", linkname.encode() if linkname else None, member_type)])
                with self.assertRaisesRegex(StoreError, "unsupported archive member type"):
                    self._store(label).import_(archive)

    def test_member_size_limit_is_rejected(self):
        archive = self.root / "member-size.tar.gz"
        payload = b"x" * (MAX_ARCHIVE_MEMBER_BYTES + 1)
        _write_tar(archive, [("skills/demo/payload.bin", payload, None)])

        with self.assertRaisesRegex(StoreError, "member exceeds"):
            self._store().import_(archive)

    def test_expanded_size_limit_is_rejected(self):
        archive = self.root / "expanded-size.tar.gz"
        payload = b"x" * MAX_ARCHIVE_MEMBER_BYTES
        _write_tar(
            archive,
            [
                ("skills/demo/one.bin", payload, None),
                ("skills/demo/two.bin", payload, None),
            ],
        )

        with self.assertRaisesRegex(StoreError, "expanded size"):
            self._store().import_(archive)

    def test_member_count_limit_is_rejected(self):
        archive = self.root / "member-count.tar.gz"
        members = [
            (f"skills/demo/file-{index}.txt", b"x", None)
            for index in range(MAX_ARCHIVE_MEMBERS)
        ]
        _write_tar(archive, members)

        with self.assertRaisesRegex(StoreError, "too many members"):
            self._store().import_(archive)

    def test_zip_retains_its_separate_member_count_limit(self):
        archive = self.root / "zip-count.zip"
        _write_zip(archive, [
            (f"skills/demo/file-{index}.txt", b"x") for index in range(MAX_ZIP_ARCHIVE_MEMBERS)
        ])
        with self.assertRaisesRegex(StoreError, f"max {MAX_ZIP_ARCHIVE_MEMBERS}"):
            self._store().import_(archive)

    def test_tar_counts_directories_without_explicit_headers(self):
        archive = self.root / "implicit-directories.tar.gz"
        _write_tar(archive, [
            ("skills/demo/SKILL.md", _document("demo"), None),
            ("skills/demo/references/one/file.txt", b"first", None),
            ("skills/demo/references/two/file.txt", b"second", None),
        ], names=("demo",))
        target = self._store()
        with mock.patch("skillsmgr.archive.MAX_ARCHIVE_DIRECTORIES", 4):
            with self.assertRaisesRegex(StoreError, "too many directories"):
                target.import_(archive)
        self.assertEqual(target.list(), [])

        self.assertEqual(target.import_(archive)["imported"], ["demo"])

    def test_tar_and_zip_refuse_file_directory_conflicts_in_both_orders(self):
        names = ("skills/demo/references", "skills/demo/references/example.md")
        target = self._store()
        for label, writer in (("tar.gz", _write_tar), ("zip", _write_zip)):
            for order in (names, names[::-1]):
                with self.subTest(format=label, order=order):
                    packed = self.root / f"conflict.{label}"
                    members = [(name, b"fixture") for name in order]
                    members.append(("skills/demo/SKILL.md", _document("demo")))
                    if label == "tar.gz":
                        members = [(*member, None) for member in members]
                    writer(packed, members, names=("demo",))
                    with self.assertRaisesRegex(StoreError, "both a file and a directory"):
                        target.import_(packed)
        self.assertEqual(target.list(), [])

    def test_windows_member_names_reject_device_names_and_invalid_components(self):
        invalid = ("CON.txt", "COM².md", "notes:other.txt", "trailing.md ", "trailing.")
        with mock.patch("skillsmgr.archive._WINDOWS_PATHS", True):
            for filename in invalid:
                with self.subTest(filename=filename):
                    with self.assertRaisesRegex(StoreError, "unsafe archive member"):
                        normalize_member_name(f"skills/demo/references/{filename}")
            self.assertEqual(normalize_member_name("skills/demo/references/ordinary.md"),
                             "skills/demo/references/ordinary.md")
        with mock.patch("skillsmgr.archive._WINDOWS_PATHS", False):
            self.assertEqual(normalize_member_name("skills/demo/references/local:notes.md"),
                             "skills/demo/references/local:notes.md")

    def test_tar_and_zip_refuse_windows_case_aliases_before_installing(self):
        pairs = (
            ("references/Notes.md", "references/notes.md", "duplicate archive member"),
            ("Examples/one.md", "examples/two.md", "directory aliases"),
        )
        target = self._store()
        with mock.patch("skillsmgr.archive._WINDOWS_PATHS", True):
            for label, writer in (("tar.gz", _write_tar), ("zip", _write_zip)):
                for first, second, error in pairs:
                    with self.subTest(format=label, first=first):
                        packed = self.root / f"case-alias.{label}"
                        members = [(f"skills/demo/{name}", b"fixture") for name in (first, second)]
                        members.append(("skills/demo/SKILL.md", _document("demo")))
                        if label == "tar.gz":
                            members = [(*member, None) for member in members]
                        writer(packed, members, names=("demo",))
                        with self.assertRaisesRegex(StoreError, error):
                            target.import_(packed)
        self.assertEqual(target.list(), [])

    def test_full_backup_round_trips_more_than_the_old_member_cap(self):
        source = self._store("large-source")
        source.create("demo", "Large synthetic skill")
        references = source.skills_dir / "demo" / "references"
        references.mkdir()
        expected = {f"{index:03d}.txt": f"reference {index}".encode() for index in range(250)}
        for name, contents in expected.items():
            (references / name).write_bytes(contents)

        exported = source.backup(self.root / "large.tar.gz", full=True)
        target = self._store()
        self.assertEqual(target.import_(exported, full=True)["imported"], ["demo"])
        restored = target.skills_dir / "demo" / "references"
        self.assertEqual({file.name: file.read_bytes() for file in restored.iterdir()}, expected)

    def test_unimportable_export_retains_previous_destination(self):
        store = self._store()
        store.create("demo", "Backup budget fixture")
        (store.skills_dir / "demo" / "compressible.bin").write_bytes(b"\0" * 16_384)
        destination = self.root / "previous.tar.gz"
        destination.write_bytes(b"previous backup")
        for setting, value, error in (
            ("MAX_ARCHIVE_MEMBERS", 2, "too many members"),
            ("MAX_ARCHIVE_COMPRESSION_RATIO", 1, "compression ratio"),
        ):
            with self.subTest(setting=setting):
                with mock.patch(f"skillsmgr.archive.{setting}", value):
                    with self.assertRaisesRegex(StoreError, error):
                        store.backup(destination)
                self.assertEqual(destination.read_bytes(), b"previous backup")
                self.assertEqual(list(self.root.glob("*.skillsmgr-export")), [])

    def test_simultaneous_default_backups_in_one_second_publish_distinct_files(self):
        from skillsmgr import archive as archive_mod

        store = self._store()
        store.create("demo", "Concurrent default backup fixture")
        ready = Barrier(2)
        verify_export = archive_mod.verify_export

        def verify_together(path):
            verify_export(path)
            ready.wait(timeout=10)

        with (
            mock.patch("skillsmgr.store.stamp", return_value="2026-11-20_12-00-00Z"),
            mock.patch.object(archive_mod, "verify_export", side_effect=verify_together),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            backups = [executor.submit(store.backup) for _ in range(2)]
            paths = [backup.result(timeout=15) for backup in backups]

        self.assertEqual({path.name for path in paths}, {
            "export-2026-11-20_12-00-00Z.tar.gz",
            "export-2026-11-20_12-00-00Z-1.tar.gz",
        })
        for path in paths:
            verify_export(path)

    def test_default_backup_treats_dangling_link_as_an_occupied_name(self):
        store = self._store()
        target = self.root / "missing.tar.gz"
        link = store.backups_dir / "export-2026-11-20_12-00-00Z.tar.gz"
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")

        with mock.patch("skillsmgr.store.stamp", return_value="2026-11-20_12-00-00Z"):
            created = store.backup()
        self.assertEqual(created.name, "export-2026-11-20_12-00-00Z-1.tar.gz")
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_export_omits_manager_sidecars_and_keeps_hash_of_original_skill_bytes(self):
        source = self._store("evidence-source")
        source.create("demo", "Export without install evidence")
        skill = source.skills_dir / "demo"
        references = skill / "references"
        references.mkdir()
        (skill / PROVENANCE_FILENAME).write_bytes(b"{}")
        (references / SOURCE_LOCK_FILENAME).write_bytes(b"{}")
        (references / "ordinary.txt").write_bytes(b"supporting file")
        expected = (skill / "SKILL.md").read_bytes()

        exported = source.export(self.root / "portable.tar.gz")
        with tarfile.open(exported) as packed:
            self.assertTrue(all(Path(name).name not in (PROVENANCE_FILENAME, SOURCE_LOCK_FILENAME)
                                for name in packed.getnames()))
        target = self._store()
        self.assertEqual(target.import_(exported)["imported"], ["demo"])
        installed = target.skills_dir / "demo"
        self.assertEqual((installed / "SKILL.md").read_bytes(), expected)
        self.assertEqual((installed / "references" / "ordinary.txt").read_bytes(), b"supporting file")
        self.assertTrue((skill / PROVENANCE_FILENAME).is_file())
        self.assertTrue((references / SOURCE_LOCK_FILENAME).is_file())

    def test_legacy_full_tree_hash_accepts_exact_original_but_never_installs_sidecar(self):
        source = self.root / "legacy"
        (source / "references").mkdir(parents=True)
        document = _document("demo")
        (source / "SKILL.md").write_bytes(document)
        (source / "references" / SOURCE_LOCK_FILENAME).write_bytes(b"{}")
        (source / "references" / "check.txt").write_bytes(b"original")
        manifest = json.loads(_manifest("demo"))
        manifest["full"] = True
        manifest["skills"][0]["content_hash"] = tree_content_hash(source, separator="\\")
        target = self._store()

        for contents in (b"modified", b"original"):
            with self.subTest(contents=contents):
                packed = self.root / "legacy.zip"
                with zipfile.ZipFile(packed, "w") as archive:
                    archive.writestr("manifest.json", json.dumps(manifest))
                    archive.writestr("skills/demo/SKILL.md", document)
                    archive.writestr(f"skills/demo/references/{SOURCE_LOCK_FILENAME}", b"{}")
                    archive.writestr("skills/demo/references/check.txt", contents)
                if contents == b"modified":
                    with self.assertRaisesRegex(StoreError, "content hash mismatch"):
                        target.import_(packed, full=True)
                    receipt = target.import_(packed)
                    self.assertEqual(receipt["imported"], [])
                    self.assertIn("content hash mismatch", receipt["skipped"][0])
                else:
                    receipt = target.import_(packed, full=True)
                    self.assertEqual(receipt["imported"], ["demo"])
                    self.assertEqual((target.skills_dir / "demo" / "references" / "check.txt").read_bytes(), contents)
                    self.assertFalse((target.skills_dir / "demo" / "references" / SOURCE_LOCK_FILENAME).exists())

    def test_backup_records_hardlinked_companions_as_regular_files(self):
        source = self._store("links-source")
        source.create("demo", "Restore both hardlinked file names")
        skill = source.skills_dir / "demo"
        (skill / "first.bin").write_bytes(b"\x00\xff\xfe")
        try:
            os.link(skill / "first.bin", skill / "second.bin")
        except OSError as exc:
            self.skipTest(f"hard-link creation is unavailable: {exc}")
        exported = source.backup(self.root / "links.tar.gz")
        with tarfile.open(exported) as packed:
            self.assertTrue(packed.getmember("skills/demo/second.bin").isreg())
        target = self._store()
        self.assertEqual(target.import_(exported)["imported"], ["demo"])
        for name in ("first.bin", "second.bin"):
            self.assertEqual((target.skills_dir / "demo" / name).read_bytes(), b"\x00\xff\xfe")

    def test_member_path_length_limit_is_rejected(self):
        archive = self.root / "path-length.tar.gz"
        long_name = "skills/demo/" + ("x" * MAX_ARCHIVE_PATH_LENGTH)
        _write_tar(archive, [(long_name, b"x", None)])

        with self.assertRaisesRegex(StoreError, "path is too long"):
            self._store().import_(archive)

    def test_member_depth_limit_is_rejected(self):
        archive = self.root / "depth.tar.gz"
        nested = "/".join(f"d{index}" for index in range(MAX_ARCHIVE_NESTING))
        _write_tar(archive, [(f"skills/demo/{nested}/file.txt", b"x", None)])

        with self.assertRaisesRegex(StoreError, "nested too deeply"):
            self._store().import_(archive)

    def test_compression_ratio_limit_is_rejected(self):
        archive = self.root / "ratio.tar.gz"
        _write_tar(
            archive,
            [("skills/demo/repetitive.bin", b"0" * MAX_ARCHIVE_MEMBER_BYTES, None)],
        )

        with self.assertRaisesRegex(StoreError, "compression ratio"):
            self._store().import_(archive)
        self.assertGreater(MAX_ARCHIVE_COMPRESSION_RATIO, 0)

    def test_strict_manifest_rejects_missing_and_undeclared_skills(self):
        missing = self.root / "missing.tar.gz"
        _write_tar(missing, [], names=("declared",))
        with self.assertRaisesRegex(StoreError, "missing"):
            self._store("missing-target").import_(missing)

        extra = self.root / "extra.tar.gz"
        _write_tar(
            extra,
            [
                ("skills/declared/SKILL.md", _document("declared"), None),
                ("skills/extra/SKILL.md", _document("extra"), None),
            ],
            names=("declared",),
        )
        with self.assertRaisesRegex(StoreError, "missing from manifest"):
            self._store("extra-target").import_(extra)

    def test_manifestless_skill_list_falls_back_to_archive_directories(self):
        archive = self.root / "manifestless.tar.gz"
        _write_tar(
            archive,
            [("skills/loose/SKILL.md", _document("loose"), None)],
            names=(),
        )

        target = self._store()
        result = target.import_(archive)

        self.assertEqual(result["imported"], ["loose"])
        self.assertEqual(target.get("loose")["description"], "Use this skill for archive tests.")

    def test_zip_archive_round_trip(self):
        source = self._store("zip-source")
        source.create("zip-demo", "ZIP demo", body="zip round-trip body")
        archive = source.export(self.root / "zip-round-trip.tar.gz")
        zip_archive = self.root / "zip-round-trip.zip"
        with zipfile.ZipFile(zip_archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            with tarfile.open(archive, "r:gz") as tar:
                for member in tar.getmembers():
                    payload = tar.extractfile(member).read() if member.isreg() else b""
                    zipped.writestr(member.name, payload)
        target = self._store("zip-target")
        result = target.import_(zip_archive)
        self.assertEqual(result["imported"], ["zip-demo"])
        self.assertIn("zip round-trip body", target.get("zip-demo")["body"])

    def test_zip_traversal_absolute_windows_and_symlink_members_rejected_before_extraction(self):
        victim = self.root / "victim.txt"
        victim.write_text("keep", encoding="utf-8")
        cases = {
            "traversal": "skills/demo/../../victim.txt",
            "absolute": "/victim.txt",
            "backslash": "skills\\demo\\escape.txt",
            "drive": "C:/victim.txt",
            "symlink": "skills/demo/link",
        }
        for label, member_name in cases.items():
            with self.subTest(label=label):
                archive = self.root / f"{label}.zip"
                _write_zip(archive, [(member_name, b"escape")], symlinks={member_name} if label == "symlink" else ())
                try:
                    self._store(label).import_(archive, force=True)
                except StoreError:
                    pass
                else:
                    # Windows: zipfile normalizes "\\" to "/" inside ZipInfo on
                    # both write and read, so this member can no longer smuggle a
                    # separator past name validation; the import must then stay
                    # contained and simply find no skill document.
                    self.assertEqual(label, "backslash")
                    self.assertEqual(os.name, "nt", "only Windows may accept the backslash member")
                # The invariant that matters on every host: nothing escaped.
                self.assertEqual(victim.read_text(encoding="utf-8"), "keep")

    def test_zip_per_member_compression_ratio_is_enforced(self):
        # A stored, incompressible member must not mask a later highly
        # compressible one: the ratio budget is a per-member invariant.
        archive = self.root / "ratio-mask.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", _manifest("demo"))
            zipped.writestr(
                zipfile.ZipInfo("skills/demo/padding.bin"),
                bytes(range(256)) * 3907,
                compress_type=zipfile.ZIP_STORED,
            )
            zipped.writestr(
                zipfile.ZipInfo("skills/demo/bomb.bin"),
                b"\x00" * (8 * 1024 * 1024),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            zipped.writestr("skills/demo/SKILL.md", _document("demo"))

        with self.assertRaisesRegex(StoreError, "compression ratio"):
            self._store().import_(archive)

    def test_zip_slash_directory_without_unix_directory_bits_is_accepted(self):
        # Many ZIP writers emit "skills/demo/" with no Unix/DOS directory bit;
        # the trailing slash is the portable marker.
        archive = self.root / "plain-dirs.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", _manifest("demo"))
            for name in ("skills/", "skills/demo/"):
                info = zipfile.ZipInfo(name)
                info.external_attr = 0
                zipped.writestr(info, b"")
            zipped.writestr("skills/demo/SKILL.md", _document("demo"))

        result = self._store().import_(archive)
        self.assertEqual(result["imported"], ["demo"])

    def test_zip_duplicate_members_are_rejected(self):
        archive = self.root / "duplicate.zip"
        _write_zip(
            archive,
            [("skills/demo/SKILL.md", _document("demo")), ("skills/demo/SKILL.md", _document("demo"))],
            names=("demo",),
        )
        with self.assertRaisesRegex(StoreError, "duplicate"):
            self._store().import_(archive)

    def test_zip_content_is_rejected_even_with_tar_filename(self):
        archive = self.root / "actually-a-tar.tar.gz"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", _manifest().decode("utf-8"))

        result = self._store().import_(archive)
        self.assertEqual(result["imported"], [])

    def test_malformed_zip_metadata_is_a_clean_store_error(self):
        archive = self.root / "bad-metadata.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", _manifest().decode("utf-8"))
        raw = bytearray(archive.read_bytes())
        central = raw.find(b"PK\x01\x02")
        self.assertGreaterEqual(central, 0)
        raw[central + 6 : central + 8] = b"\xff\xff"
        archive.write_bytes(raw)
        with self.assertRaisesRegex(StoreError, "invalid archive"):
            self._store().import_(archive)

    def test_zip_full_manifest_types_are_rejected_before_skill_commit(self):
        archive = self.root / "bad-full.zip"
        manifest = {
            "app": "skills-mgr",
            "version": __version__,
            "created": _CREATED,
            "full": True,
            "skills": [{"name": "demo"}],
            "trash": 123,
            "templates": [],
        }
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", json.dumps(manifest))
            zipped.writestr("skills/demo/SKILL.md", _document("demo", "new"))
        target = self._store()
        target.create("demo", "Original", body="old")
        with self.assertRaisesRegex(StoreError, "trash"):
            target.import_(archive, force=True, full=True)
        self.assertIn("old", target.get("demo")["body"])

    def test_new_skill_commit_failure_removes_destination(self):
        source = self._store("source-new")
        source.create("new-skill", "New skill", body="new body")
        archive = source.export(self.root / "new-failure.tar.gz")
        target = self._store("target-new")
        with mock.patch.object(target, "_upsert_row", side_effect=StoreError("injected index failure")):
            result = target.import_(archive, force=True)
        self.assertEqual(result["imported"], [])
        self.assertTrue(result["skipped"])
        self.assertFalse((target.skills_dir / "new-skill").exists())
        self.assertEqual(target.list(), [])

    def test_failed_stage_copy_preserves_existing_skill(self):
        # Regression: staging runs before the original destination is moved
        # aside, so a failed staging copy must never delete the user's skill.
        source = self._store("stage-fail-source")
        source.create("demo", "Replacement", body="new body")
        archive = source.export(self.root / "stage-fail.tar.gz")
        target = self._store("stage-fail-target")
        target.create("demo", "Original", body="old body")

        def partial_copy(src, dst, **kwargs):
            Path(dst).mkdir(parents=True, exist_ok=True)
            (Path(dst) / "partial").write_text("torn", encoding="utf-8")
            raise OSError(5, "Input/output error")

        with mock.patch("skillsmgr.archive.shutil.copytree", side_effect=partial_copy):
            result = target.import_(archive, force=True)

        self.assertEqual(result["imported"], [])
        self.assertTrue(any("demo" in item for item in result["skipped"]))
        self.assertTrue((target.skills_dir / "demo" / "SKILL.md").is_file())
        self.assertEqual(target.get("demo")["description"], "Original")
        self.assertEqual(target.get("demo")["body"], "old body\n")

    def test_full_import_copy_failure_is_clean_and_preserves_previous_state(self):
        source = self._store("full-fail-source")
        source.create("keep", "Keep", body="keep body")
        source.create("goner", "Gone", body="gone body")
        source.remove("goner")
        (source.templates_dir / "one.md").write_text("# One\n", encoding="utf-8")
        (source.templates_dir / "two.md").write_text("# Two\n", encoding="utf-8")
        archive = source.export(self.root / "full-fail.tar.gz", full=True)

        target = self._store("full-fail-target")
        target.create("keep", "Original skill", body="original body")
        live = target.skills_dir / "keep"
        (live / "local.bin").write_bytes(b"keep the original file")
        history = target.history("keep")
        (target.templates_dir / "one.md").write_text("# Original one\n", encoding="utf-8")
        real_copyfile = __import__("shutil").copyfile
        calls = {"n": 0}

        def fail_second_template(src, dst, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError(28, "No space left on device")
            return real_copyfile(src, dst, **kwargs)

        with mock.patch("skillsmgr.archive.shutil.copyfile", side_effect=fail_second_template):
            with self.assertRaisesRegex(StoreError, "full archive payload"):
                target.import_(archive, force=True, full=True)

        self.assertEqual(
            (target.templates_dir / "one.md").read_text(encoding="utf-8"),
            "# Original one\n",
        )
        self.assertFalse((target.templates_dir / "two.md").exists())
        self.assertEqual(list(target.templates_dir.glob(".skillsmgr-backup.*")), [])
        self.assertEqual(target.get("keep")["body"], "original body\n")
        self.assertEqual((live / "local.bin").read_bytes(), b"keep the original file")
        self.assertEqual(target.history("keep"), history)
        self.assertEqual(target.trash_list(), [])

        retry = target.import_(archive, force=True, full=True)
        self.assertEqual(retry["imported"], ["keep"])
        self.assertEqual(retry["restored_templates"], ["one.md", "two.md"])
        self.assertEqual(target.get("keep")["body"], "keep body\n")

    def test_full_import_failed_template_publish_restores_original_and_removes_new_file(self):
        source = self._store("full-publish-source")
        (source.templates_dir / "a-new.md").write_bytes(b"new template")
        (source.templates_dir / "z-existing.md").write_bytes(b"new bytes")
        archive = source.export(self.root / "full-publish.tar.gz", full=True)
        target = self._store("full-publish-target")
        original = target.templates_dir / "z-existing.md"
        original.write_bytes(b"original bytes")
        real_replace = os.replace

        def fail_publication(staged, dest):
            if Path(staged).name == "new" and dest == original:
                raise OSError("injected publication failure")
            return real_replace(staged, dest)

        with mock.patch("skillsmgr.archive.os.replace", side_effect=fail_publication):
            with self.assertRaisesRegex(StoreError, "injected publication failure"):
                target.import_(archive, full=True, force=True)

        self.assertEqual(original.read_bytes(), b"original bytes")
        self.assertEqual(list(target.templates_dir.iterdir()), [original])
        result = target.import_(archive, full=True, force=True)
        self.assertEqual(result["restored_templates"], ["a-new.md", "z-existing.md"])
        self.assertEqual(original.read_bytes(), b"new bytes")
        self.assertEqual(list(target.templates_dir.glob(".skillsmgr-backup.*")), [])

    def test_full_payload_interrupt_after_rename_restores_previous_directory(self):
        from skillsmgr import archive as archive_mod

        source = self.root / "incoming"
        source.mkdir()
        (source / "new-file").write_bytes(b"new")
        dest = self.root / "trash-copy"
        dest.mkdir()
        (dest / "old-file").write_bytes(b"old")

        for interrupted_move in (1, 2):
            with self.subTest(interrupted_move=interrupted_move):
                calls = 0

                def interrupted(src, target):
                    nonlocal calls
                    calls += 1
                    os.replace(src, target)
                    if calls == interrupted_move:
                        raise KeyboardInterrupt

                with self.assertRaises(KeyboardInterrupt):
                    archive_mod.restore_full_payload(
                        [("trash", dest.name, source, dest)], replace=True, move=interrupted
                    )
                self.assertEqual({path.name for path in dest.iterdir()}, {"old-file"})
                self.assertEqual((dest / "old-file").read_bytes(), b"old")
                self.assertEqual(list(self.root.glob(".skillsmgr-backup.*")), [])

    def test_full_payload_restore_failure_reports_original_error_and_keeps_backup(self):
        # P0 trust gate: a rollback diagnostic must never raise the missing
        # ``_diagnose`` NameError or erase the only recoverable old payload.
        from skillsmgr import archive as archive_mod

        source_root = self.root / "payload-source"
        source_root.mkdir()
        first_source = source_root / "one.md"
        second_source = source_root / "two.md"
        first_source.write_bytes(b"new one")
        second_source.write_bytes(b"new two")
        destination_root = self.root / "payload-destination"
        destination_root.mkdir()
        first_dest = destination_root / "one.md"
        second_dest = destination_root / "two.md"
        first_dest.write_bytes(b"old one")
        unrelated = destination_root / "unrelated.txt"
        unrelated.write_bytes(b"keep")

        def failing_move(source, destination):
            if source.name == "new" and destination == second_dest:
                raise OSError("injected later install failure")
            if source.name == "old" and destination == first_dest:
                raise OSError("injected rollback restore failure")
            return os.replace(source, destination)

        entries = [
            ("templates", "one.md", first_source, first_dest),
            ("templates", "two.md", second_source, second_dest),
        ]
        with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaisesRegex(archive_mod.ArchiveError, "injected later install failure"):
                archive_mod.restore_full_payload(entries, replace=True, move=failing_move)
            diagnostic = stderr.getvalue()

        backup, = destination_root.glob(".skillsmgr-backup.*/old")
        self.assertIn("full-import rollback failed", diagnostic)
        self.assertIn(str(backup.parent), diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), b"old one")
        self.assertEqual(unrelated.read_bytes(), b"keep")
        archive_mod.restore_full_payload(entries, replace=True)
        self.assertEqual(first_dest.read_bytes(), b"new one")
        self.assertEqual(backup.read_bytes(), b"old one")

    def test_full_import_missing_catalog_file_fails_before_replacing_skill(self):
        archive = self.root / "catalog-directory.zip"
        manifest = {**json.loads(_manifest("demo")), "full": True, "catalog": True}
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", json.dumps(manifest))
            zipped.writestr("catalog/", b"")
            zipped.writestr("skills/demo/SKILL.md", _document("demo", "new"))
        target = self._store()
        target.create("demo", "Original", body="old")

        with self.assertRaisesRegex(StoreError, "catalog metadata is missing"):
            target.import_(archive, full=True, force=True)
        self.assertIn("old", target.get("demo")["body"])

    def test_full_import_checks_all_recorded_skill_hashes_before_restoring(self):
        from skillsmgr.catalog import catalog_path, update_tags

        target = self._store()
        target.create("good", "Installed skill", body="keep original")
        template = target.templates_dir / "one.md"
        template.write_bytes(b"original template")
        update_tags(target.data_dir, ["good"], "replace", ["local"])
        original_document = target.skills_dir / "good" / "SKILL.md"
        observed = {file: file.read_bytes() for file in (original_document, template, catalog_path(target.data_dir))}
        previous_history = target.history()
        trash = "trashed-2026-09-08_12-00-00Z"
        packed = self.root / "corrupt-migration.zip"
        for expected, reason in (("0" * 64, "content hash mismatch"), ("", "invalid content hash")):
            with self.subTest(expected=expected):
                manifest = {**json.loads(_manifest("good", "bad")), "full": True,
                            "templates": [template.name], "catalog": True, "trash": [trash]}
                manifest["skills"][1]["content_hash"] = expected
                with zipfile.ZipFile(packed, "w") as zipped:
                    zipped.writestr("manifest.json", json.dumps(manifest))
                    zipped.writestr("skills/good/SKILL.md", _document("good", "replace original"))
                    zipped.writestr("skills/bad/SKILL.md", _document("bad"))
                    zipped.writestr("catalog/metadata.json", json.dumps({"version": 1, "tags": {}, "profiles": {}}))
                    zipped.writestr("templates/one.md", b"replacement template")
                    zipped.writestr(f"trash/{trash}/SKILL.md", _document("trashed"))
                with self.assertRaisesRegex(StoreError, reason):
                    target.import_(packed, full=True, force=True)
                self.assertEqual({file: file.read_bytes() for file in observed}, observed)
                self.assertEqual(target.history(), previous_history)
                self.assertEqual(target.trash_list(), [])
                self.assertFalse((target.skills_dir / "bad").exists())

    def test_full_import_restores_catalog_file_without_replacing_its_directory(self):
        from skillsmgr.catalog import catalog_path, load_catalog, update_tags

        source = self._store("catalog-file-source")
        update_tags(source.data_dir, ["demo"], "replace", ["imported"])
        archive = source.export(self.root / "catalog-file.tar.gz", full=True)
        target = self._store("catalog-file-target")
        companion = catalog_path(target.data_dir).parent / "keep.bin"
        companion.parent.mkdir()
        companion.write_bytes(b"keep this")

        self.assertTrue(target.import_(archive, full=True)["restored_catalog"])
        update_tags(target.data_dir, ["demo"], "replace", ["local"])
        skipped = target.import_(archive, full=True)
        self.assertFalse(skipped["restored_catalog"])
        self.assertIn("catalog/metadata.json", skipped["skipped_full"])
        self.assertEqual(load_catalog(target.data_dir)["tags"], {"demo": ["local"]})
        self.assertTrue(target.import_(archive, full=True, force=True)["restored_catalog"])
        self.assertEqual(load_catalog(target.data_dir)["tags"], {"demo": ["imported"]})
        self.assertEqual(companion.read_bytes(), b"keep this")

    def test_full_import_force_refuses_to_replace_a_template_directory_or_link(self):
        source = self._store("wrong-type-source")
        source.create("demo", "Imported skill")
        (source.templates_dir / "one.md").write_bytes(b"imported file")
        archive = source.export(self.root / "wrong-type.tar.gz", full=True)
        target = self._store("wrong-type-target")
        target.create("demo", "Keep the installed skill")
        dest = target.templates_dir / "one.md"
        dest.mkdir()
        protected = dest / "keep.txt"
        protected.write_bytes(b"local directory")

        with self.assertRaisesRegex(StoreError, "cannot replace full archive destination"):
            target.import_(archive, full=True, force=True)
        self.assertEqual(protected.read_bytes(), b"local directory")
        self.assertEqual(target.get("demo")["description"], "Keep the installed skill")

        alias_target = target.templates_dir / "kept.md"
        alias_target.write_bytes(b"local template")
        protected.unlink()
        dest.rmdir()
        try:
            dest.symlink_to(alias_target)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        with self.assertRaisesRegex(StoreError, "cannot replace full archive destination"):
            target.import_(archive, full=True, force=True)
        self.assertTrue(dest.is_symlink())
        self.assertEqual(alias_target.read_bytes(), b"local template")
        self.assertEqual(target.get("demo")["description"], "Keep the installed skill")

    def test_full_import_refuses_a_catalog_directory_replaced_with_a_file(self):
        source = self._store("catalog-parent-source")
        source.create("demo", "Imported skill")
        packed = source.export(self.root / "catalog-parent.tar.gz", full=True)
        target = self._store("catalog-parent-target")
        target.create("demo", "Local skill")
        catalog = target.data_dir / "catalog"
        catalog.write_bytes(b"private catalog data")

        with self.assertRaisesRegex(StoreError, "catalog destination must be an unlinked directory"):
            target.import_(packed, full=True, force=True)
        self.assertEqual(target.get("demo")["description"], "Local skill")
        self.assertEqual(catalog.read_bytes(), b"private catalog data")

    def test_full_import_index_error_reverts_trash_and_template_payloads(self):
        source = self._store("full-index-fail-source")
        source.create("new-skill", "New skill should wait")
        source.create("goner", "Gone")
        source.remove("goner")
        (source.templates_dir / "one.md").write_bytes(b"replacement")
        archive = source.export(self.root / "full-index-fail.tar.gz", full=True)
        target = self._store("full-index-fail-target")
        template = target.templates_dir / "one.md"
        template.write_bytes(b"original")
        connect = target._connect

        def refusing_write():
            conn = connect()

            def authorize(action, table, *_):
                if action == sqlite3.SQLITE_UPDATE and table == "skills":
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            conn.set_authorizer(authorize)
            return conn

        with mock.patch.object(target, "_connect", side_effect=refusing_write):
            with self.assertRaisesRegex(StoreError, "reconciling imported trash failed"):
                target.import_(archive, full=True, force=True)

        self.assertEqual(target.trash_list(), [])
        self.assertEqual(target.stats()["trashed"], 0)
        self.assertEqual(template.read_bytes(), b"original")
        self.assertEqual(list(target.data_dir.rglob(".skillsmgr-backup.*")), [])
        self.assertFalse((target.skills_dir / "new-skill").exists())
        self.assertEqual(target.history("new-skill"), [])

    def test_full_import_rejects_malformed_full_metadata_before_mutation(self):
        archive = self.root / "bad-full-metadata.zip"
        manifest = {
            "app": "skills-mgr",
            "version": __version__,
            "created": _CREATED,
            "full": "yes",
            "skills": [{"name": "demo"}],
            "trash": ["../escape"],
            "templates": [],
        }
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", json.dumps(manifest))
            zipped.writestr("skills/demo/SKILL.md", _document("demo", "new"))
        target = self._store()
        target.create("demo", "Original", body="old")
        with self.assertRaisesRegex(StoreError, "full must be a boolean"):
            target.import_(archive, force=True, full=True)
        self.assertIn("old", target.get("demo")["body"])

    def test_full_import_records_restored_trash_in_the_index(self):
        source = self._store("full-index-source")
        source.create("keep", "Keep")
        source.create("goner", "Gone")
        source.remove("goner")
        archive = source.export(self.root / "full-index.tar.gz", full=True)

        target = self._store("full-index-target")
        result = target.import_(archive, full=True)

        self.assertEqual(len(result["restored_trash"]), 1)
        self.assertEqual(len(target.trash_list()), 1)
        self.assertEqual(target.stats()["trashed"], 1)
        self.assertTrue(target.doctor()["ok"])

    def test_full_import_recovers_active_and_trashed_copies_of_the_same_skill(self):
        source = self._store("full-shared-source")
        source.create("demo", "Archived copy", body="earlier")
        source.remove("demo")
        source.create("demo", "Active copy", body="later")
        archive = source.export(self.root / "full-shared-name.tar.gz", full=True)

        target = self._store("full-shared-target")
        result = target.import_(archive, full=True)
        self.assertEqual(result["imported"], ["demo"])
        self.assertEqual(len(result["restored_trash"]), 1)
        trash = target.trash_dir / result["restored_trash"][0] / "SKILL.md"
        self.assertIn(b"earlier", trash.read_bytes())
        self.assertEqual(target.get("demo")["body"], "later\n")
        self.assertEqual(target.stats()["trashed"], 0)
        self.assertTrue(target.doctor()["ok"])

    def test_full_import_refuses_duplicate_payload_labels_before_replacing_skills(self):
        archive = self.root / "duplicates.zip"
        manifest = json.loads(_manifest("demo"))
        manifest.update(full=True, templates=["fixture.md", "fixture.md"])
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("manifest.json", json.dumps(manifest))
            zipped.writestr("templates/fixture.md", "fixture")
            zipped.writestr("skills/demo/SKILL.md", _document("demo", "new"))
        target = self._store()
        target.create("demo", "Original", body="old")

        with self.assertRaisesRegex(StoreError, "duplicate templates entry"):
            target.import_(archive, force=True, full=True)
        self.assertEqual(target.get("demo")["body"], "old\n")
        self.assertFalse((target.templates_dir / "fixture.md").exists())

    def test_failed_per_skill_commit_restores_destination_and_reports_result(self):
        source = self._store("source")
        source.create("first", "New first", body="new first body")
        source.create("second", "New second", body="new second body")
        archive = source.export(self.root / "commit-failure.tar.gz")

        target = self._store("target")
        target.create("first", "Old first", body="old first body")
        target.create("second", "Old second", body="old second body")
        real_upsert = target._upsert_row

        def fail_second(conn, name, entry):
            if name == "second":
                raise StoreError("injected per-skill commit failure")
            return real_upsert(conn, name, entry)

        with mock.patch.object(target, "_upsert_row", side_effect=fail_second):
            result = target.import_(archive, force=True)

        self.assertEqual(result["imported"], ["first"])
        self.assertEqual(len(result["skipped"]), 1)
        self.assertIn("second", result["skipped"][0])
        self.assertIn("injected per-skill commit failure", result["skipped"][0])
        self.assertEqual(target.get("first")["description"], "New first")
        self.assertEqual(target.get("second")["description"], "Old second")
        self.assertIn("old second body", target.get("second")["body"])
        self.assertFalse((target.skills_dir / "second.skillsmgr-stage").exists())

    def test_import_history_write_failure_rolls_back_skill_files_and_index_row(self):
        source = self._store("history-fail-source")
        source.create("demo", "Replacement", body="new")
        packed = source.export(self.root / "history-fail.tar.gz")
        target = self._store("history-fail-target")
        target.create("demo", "Original", body="old")
        target.disable("demo")
        live = target.skills_dir / "demo"
        (live / "original.bin").write_bytes(b"\x00\xff")
        original = (live / "SKILL.md.disabled").read_bytes()
        history = target.history("demo")
        connect = target._connect

        def refusing_history_write():
            conn = connect()

            def authorize(action, table, *_):
                if action == sqlite3.SQLITE_INSERT and table == "history":
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            conn.set_authorizer(authorize)
            return conn

        with mock.patch.object(target, "_connect", side_effect=refusing_history_write):
            outcome = target.import_(packed, force=True)

        self.assertEqual(outcome["imported"], [])
        self.assertIn("could not record history", outcome["skipped"][0])
        self.assertEqual((live / "SKILL.md.disabled").read_bytes(), original)
        self.assertEqual((live / "original.bin").read_bytes(), b"\x00\xff")
        indexed, = target.list()
        self.assertEqual(indexed["description"], "Original")
        self.assertTrue(indexed["disabled"])
        self.assertEqual(target.history("demo"), history)
        self.assertTrue(target.doctor()["ok"])

        self.assertEqual(target.import_(packed, force=True)["imported"], ["demo"])
        self.assertEqual(target.get("demo")["description"], "Replacement")
        self.assertEqual(target.history("demo", limit=1)[0]["action"], "import")

    def test_failed_skill_rollback_retains_original_through_resync_and_retry(self):
        source = self._store("retained-source")
        source.create("demo", "Replacement")
        archive = source.export(self.root / "retained.tar.gz")
        target = self._store("retained-target")
        target.create("demo", "Original", body="old body")
        destination = target.skills_dir / "demo"
        companion_name = "local.skillsmgr-stage"
        (destination / companion_name).write_bytes(b"only copy")
        original = (destination / "SKILL.md").read_bytes()
        real_replace = os.replace

        def blocked(src, dest):
            if dest == destination and Path(src).name in ("new", "old"):
                raise OSError("injected replacement and rollback failure")
            return real_replace(src, dest)

        with mock.patch("skillsmgr.archive.os.replace", side_effect=blocked):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                result = target.import_(archive, force=True)
        retained, = target.skills_dir.glob(".skillsmgr-backup.*/old")
        self.assertEqual(result["imported"], [])
        self.assertIn(str(retained.parent), result["skipped"][0])
        self.assertIn(str(retained.parent), stderr.getvalue())
        self.assertFalse(destination.exists())
        os.utime(retained / companion_name, (1, 1))
        target.resync()
        self.assertEqual(target.import_(archive, force=True)["imported"], ["demo"])
        self.assertEqual(target.get("demo")["description"], "Replacement")
        self.assertEqual((retained / "SKILL.md").read_bytes(), original)
        self.assertEqual((retained / companion_name).read_bytes(), b"only copy")

    def test_force_import_leaves_a_linked_alias_and_its_target_unchanged(self):
        source = self._store("alias-source")
        source.create("alias", "Replacement")
        archive = source.export(self.root / "alias.tar.gz")
        target = self._store("alias-target")
        target.create("owner", "Keep this skill")
        alias = target.skills_dir / "alias"
        try:
            alias.symlink_to(target.skills_dir / "owner", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")

        result = target.import_(archive, force=True)
        self.assertEqual(result["imported"], [])
        self.assertIn("unlinked skill directory", result["skipped"][0])
        self.assertTrue(alias.is_symlink())
        self.assertEqual(target.get("owner")["description"], "Keep this skill")

    def test_import_waits_for_the_destination_skill_lock(self):
        # STORE-4: import_ must take the same per-skill lock as create/edit, or
        # a force-import displaces and replaces a document while a concurrent
        # edit() is mid-write -- silently discarding a committed edit while
        # doctor() still reports healthy.
        import threading

        from skillsmgr.atomic_io import mutation_lock

        source = self._store("source")
        source.create("shared", "Archive version", body="archive body")
        archive = source.export(self.root / "lock.tar.gz")

        target = self._store("target")
        target.create("shared", "Edited version", body="edited body")

        lock = mutation_lock(target.skills_dir / "shared" / "SKILL.md")
        lock.acquire()
        try:
            done = threading.Event()

            def run_import():
                target.import_(archive, force=True)
                done.set()

            worker = threading.Thread(target=run_import)
            worker.start()
            # The importer must block on the lock we hold, not race past it.
            self.assertFalse(done.wait(0.5), "import ignored the per-skill lock")
        finally:
            lock.release()
        worker.join(timeout=10)
        self.assertTrue(done.is_set(), "import never completed after the lock was released")
        self.assertEqual(target.get("shared")["description"], "Archive version")

    def test_interrupt_during_commit_move_keeps_the_displaced_original(self):
        # STORE-1: the window in which the user's original lives in the
        # staging ``.backup`` directory must survive an interrupt. The
        # rollback used to be ``except Exception``, so a KeyboardInterrupt
        # escaped it and the caller's staged-root cleanup deleted the only
        # remaining copy of the skill.
        from skillsmgr import archive as archive_mod

        source = self._store("source")
        source.create("keepme", "Archived copy", body="archived body")
        archive = source.export(self.root / "interrupt.tar.gz")

        target = self._store("target")
        target.create("keepme", "Original copy", body="original body")
        destination = target.skills_dir / "keepme"

        real_move = archive_mod.os.replace
        calls: list[tuple[str, str]] = []

        def interrupting_move(src, dst, *args, **kwargs):
            calls.append((str(src), str(dst)))
            # 1st move: original -> backup.  2nd move: staged -> destination
            # (the point at which the original exists only in ``backup``).
            if len(calls) == 2:
                raise KeyboardInterrupt("injected interrupt during commit")
            return real_move(src, dst, *args, **kwargs)

        with mock.patch.object(archive_mod.os, "replace", interrupting_move):
            with self.assertRaises(KeyboardInterrupt):
                target.import_(archive, force=True)

        self.assertGreaterEqual(len(calls), 2, calls)
        self.assertTrue(destination.is_dir(), "the skill directory was destroyed")
        self.assertEqual(target.get("keepme")["description"], "Original copy")
        self.assertIn("original body", target.get("keepme")["body"])


if __name__ == "__main__":
    unittest.main()
