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
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

tempfile.tempdir = os.path.realpath(tempfile.gettempdir())

if os.name == "nt":
    _original_write_text = Path.write_text

    def _lf_write_text(self, data, encoding=None, errors=None, newline=None):
        return _original_write_text(
            self, data, encoding=encoding, errors=errors,
            newline="\n" if newline is None else newline,
        )

    Path.write_text = _lf_write_text


class PortableEnvironmentTests(unittest.TestCase):
    def test_the_suite_temp_root_has_no_symlink_in_it(self):
        with tempfile.TemporaryDirectory() as made:
            self.assertEqual(made, os.path.realpath(made))

    def test_write_text_writes_lf_on_every_platform(self):
        with tempfile.TemporaryDirectory() as made:
            target = Path(made) / "lf.txt"
            target.write_text("a\nb\n", encoding="utf-8")
            self.assertEqual(target.read_bytes(), b"a\nb\n")


if __name__ == "__main__":
    unittest.main()
