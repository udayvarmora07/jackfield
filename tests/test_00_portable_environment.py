"""Normalise two platform differences before any test runs.

``unittest discover -s tests`` imports every test module, in sorted order,
before it runs a single test, so this module -- named to sort first -- sets up
the whole run (CI and ``python -m unittest discover -s tests``).  Running one
module directly bypasses it; on macOS or Windows run through discovery.

1. **A symlink-free temp root.**  macOS keeps ``$TMPDIR`` under ``/var/folders``
   and ``/var`` is a symlink to ``/private/var``; Windows runners hand out 8.3
   short names (``RUNNER~1``).  The manager resolves its data roots, refuses
   symlinked staging ancestors and reports resolved paths, so a test that builds
   fixtures under an unresolved temp directory and compares paths textually
   fails for a reason unrelated to the code under test.  The product itself is
   covered separately: ``skillsmgr.path_safety.canonical_mkdtemp`` exists so
   real uploads and registry fetches do not trip on the same symlink.

2. **POSIX newlines from ``Path.write_text``.**  On Windows ``write_text``
   translates ``"\\n"`` to ``"\\r\\n"``, so a fixture written through it differs
   byte-for-byte from the LF bytes the product writes (and hashes).  The suite
   has always been written against LF fixtures; this makes that explicit.  A
   test that cares about CRLF passes ``newline=`` or writes bytes, and is
   unaffected.

3. **Windows temp cleanup rides out a momentary sharing violation.** A file the
   suite has just closed can still be held for a moment by another process
   (Defender, the indexer), so ``TemporaryDirectory.cleanup`` raised
   ``WinError 32`` on lock files of unrelated tests at random (CI run
   44680042298, three tests, only Windows / Python 3.11). Cleanup now retries
   for up to 2 s; a handle the product genuinely leaks stays open longer than
   that and still fails the test.

4. **No inherited data override.**  ``JACKFIELD_DATA`` takes precedence over
   the pre-rename ``SKILLS_MANAGER_DATA`` that the suite sets to isolate each
   test, so a developer's own ``JACKFIELD_DATA`` would point tests at their real
   library.  It is cleared for the whole run; a test that needs it sets it.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

tempfile.tempdir = os.path.realpath(tempfile.gettempdir())
os.environ.pop("JACKFIELD_DATA", None)

if os.name == "nt":
    _original_write_text = Path.write_text

    def _lf_write_text(self, data, encoding=None, errors=None, newline=None):
        return _original_write_text(
            self, data, encoding=encoding, errors=errors,
            newline="\n" if newline is None else newline,
        )

    Path.write_text = _lf_write_text

    _original_cleanup = tempfile.TemporaryDirectory.cleanup
    _CLEANUP_ATTEMPTS = 20
    _CLEANUP_DELAY = 0.1

    def _patient_cleanup(self):
        for attempt in range(_CLEANUP_ATTEMPTS):
            try:
                return _original_cleanup(self)
            except PermissionError:
                if attempt == _CLEANUP_ATTEMPTS - 1:
                    raise
                time.sleep(_CLEANUP_DELAY)

    tempfile.TemporaryDirectory.cleanup = _patient_cleanup


class PortableEnvironmentTests(unittest.TestCase):
    def test_the_suite_temp_root_has_no_symlink_in_it(self):
        with tempfile.TemporaryDirectory() as made:
            self.assertEqual(made, os.path.realpath(made))

    def test_write_text_writes_lf_on_every_platform(self):
        with tempfile.TemporaryDirectory() as made:
            target = Path(made) / "lf.txt"
            target.write_text("a\nb\n", encoding="utf-8")
            self.assertEqual(target.read_bytes(), b"a\nb\n")

    @unittest.skipUnless(os.name == "nt", "Windows sharing violations only")
    def test_cleanup_waits_out_a_briefly_held_file(self):
        made = tempfile.TemporaryDirectory()
        held = open(Path(made.name) / "held.lock", "wb")
        threading.Timer(0.3, held.close).start()
        made.cleanup()  # would raise WinError 32 without the retry
        self.assertFalse(os.path.exists(made.name))


if __name__ == "__main__":
    unittest.main()
