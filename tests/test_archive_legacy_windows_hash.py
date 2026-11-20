"""An archive a Windows build exported before 2026-11-20 still imports.

Those builds wrote each skill's ``content_hash`` with the OS separator
(``references\\x.md``); current builds use ``/`` on every OS.  The bytes are
the same, so the legacy digest is accepted -- and only an exact match is.
"""
from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from skillsmgr.atomic_io import tree_content_hash, tree_hash_matches
from skillsmgr.store import Store


class LegacyWindowsHashTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        source = Store(self.root / "source" / "skills-manager")
        source.init_db()
        source.create("nested", "Use when testing nested files.", body="body")
        refs = source.skills_dir / "nested" / "references"
        refs.mkdir()
        (refs / "x.md").write_bytes(b"reference bytes")
        self.skill_dir = source.skills_dir / "nested"
        self.archive = source.export(self.root / "export.tar.gz")

    def _rewrite_hash(self, value: str) -> Path:
        out = self.root / "rewritten.tar.gz"
        with tarfile.open(self.archive, "r:gz") as src, tarfile.open(out, "w:gz") as dst:
            for member in src.getmembers():
                data = src.extractfile(member).read() if member.isfile() else None
                if member.name.endswith("manifest.json"):
                    manifest = json.loads(data)
                    for entry in manifest["skills"]:
                        entry["content_hash"] = value
                    data = json.dumps(manifest).encode("utf-8")
                    member.size = len(data)
                dst.addfile(member, io.BytesIO(data) if data is not None else None)
        return out

    def _fresh_store(self) -> Store:
        store = Store(self.root / "dest" / "skills-manager")
        store.init_db()
        return store

    def test_the_legacy_digest_differs_and_still_verifies(self):
        legacy = tree_content_hash(self.skill_dir, separator="\\")
        self.assertNotEqual(legacy, tree_content_hash(self.skill_dir))
        self.assertTrue(tree_hash_matches(self.skill_dir, legacy))

    def test_an_archive_with_the_legacy_digest_imports(self):
        legacy = tree_content_hash(self.skill_dir, separator="\\")
        result = self._fresh_store().import_(self._rewrite_hash(legacy))
        self.assertIn("nested", result.get("imported", []))

    def test_a_wrong_digest_is_still_refused(self):
        result = self._fresh_store().import_(self._rewrite_hash("0" * 64))
        self.assertEqual(result["imported"], [])
        self.assertEqual(result["skipped"], ["nested: content hash mismatch for 'nested'"])

    def test_only_the_two_separators_are_accepted(self):
        with self.assertRaises(ValueError):
            tree_content_hash(self.skill_dir, separator=":")


if __name__ == "__main__":
    unittest.main()
