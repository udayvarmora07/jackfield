"""A reader racing a document replace on Windows retries PermissionError.

task.md residual: on Windows a document being replaced is briefly "delete
pending" and open/stat raise PermissionError, so a healthy skill was reported
unreadable (a transient 404 under concurrent writes).  The Windows branch is
exercised here on every OS by patching the platform flag.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skillsmgr import documents, loader


class WindowsReadRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.skill = Path(tmp.name) / "alpha"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: Use when testing.\n---\nbody\n", encoding="utf-8"
        )
        self.real_read = loader.read_skill_text

    def _flaky(self, failures: int, error=PermissionError):
        calls = {"n": 0}

        def read(path):
            calls["n"] += 1
            if calls["n"] <= failures:
                raise error(13, "The process cannot access the file")
            return self.real_read(path)

        return read, calls

    def _probe(self, windows: bool, read):
        with mock.patch.object(documents, "IS_WINDOWS", windows), \
                mock.patch.object(documents, "WINDOWS_READ_DELAY", 0), \
                mock.patch.object(loader, "read_skill_text", read):
            return loader._probe_document(self.skill)

    def test_windows_rides_out_a_momentary_permission_error(self):
        read, calls = self._flaky(3)
        text, disabled, error, _ = self._probe(True, read)
        self.assertIsNone(error)
        self.assertIn("name: alpha", text)
        self.assertEqual(calls["n"], 4)

    def test_windows_gives_up_after_the_bound_and_reports_unreadable(self):
        read, calls = self._flaky(1000)
        text, _, error, _ = self._probe(True, read)
        self.assertIsNone(text)
        self.assertIn("cannot be read", error)
        self.assertEqual(calls["n"], documents.WINDOWS_READ_ATTEMPTS)

    def test_other_errors_and_posix_are_not_retried(self):
        read, calls = self._flaky(1000, error=IsADirectoryError)
        self.assertIn("cannot be read", self._probe(True, read)[2])
        self.assertEqual(calls["n"], 1)
        read, calls = self._flaky(1000)
        self.assertIn("cannot be read", self._probe(False, read)[2])
        self.assertEqual(calls["n"], 1)

    def test_an_absent_document_is_never_retried(self):
        (self.skill / "SKILL.md").unlink()
        with mock.patch.object(documents, "IS_WINDOWS", True), \
                mock.patch.object(loader.time, "sleep") as sleep:
            self.assertEqual(loader._probe_document(self.skill), (None, 0, None, False))
        sleep.assert_not_called()


    def test_raw_document_reads_ride_out_a_momentarily_invisible_document(self):
        # The raw route (GET /api/skills/<name>/raw) reads through
        # documents.document_text: a delete-pending document makes is_file()
        # False, which answered a healthy skill with a 404.
        real_is_file = Path.is_file
        calls = {"n": 0}

        def is_file(path):
            if path.name == "SKILL.md":
                calls["n"] += 1
                if calls["n"] <= 2:
                    return False
            return real_is_file(path)

        with mock.patch.object(documents, "IS_WINDOWS", True), \
                mock.patch.object(documents, "WINDOWS_READ_DELAY", 0), \
                mock.patch.object(Path, "is_file", is_file):
            self.assertIn("name: alpha", documents.document_text(self.skill))
        with mock.patch.object(documents, "IS_WINDOWS", False), \
                mock.patch.object(Path, "is_file", lambda p: False):
            self.assertEqual(documents.document_text(self.skill), "")


if __name__ == "__main__":
    unittest.main()
