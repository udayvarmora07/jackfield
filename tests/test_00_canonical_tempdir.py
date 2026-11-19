"""Make the suite's temporary root canonical (symlink-free) before any test runs.

macOS keeps ``$TMPDIR`` under ``/var/folders`` and ``/var`` is a symlink to
``/private/var``.  The manager resolves its data roots, refuses symlinked
staging ancestors and reports resolved paths, so a test that builds its
fixtures under an unresolved temp directory and compares paths textually fails
on macOS for a reason that has nothing to do with the code under test.  The
product itself is also covered: ``skillsmgr.path_safety.canonical_mkdtemp``
exists so real uploads and registry fetches do not trip on the same symlink.

``unittest discover -s tests`` imports test modules in sorted order and imports
them all before running any test, so this module -- named to sort first -- sets
``tempfile.tempdir`` once for the whole run (CI and ``python -m unittest
discover -s tests``).  Running a single module directly bypasses it; on macOS
run ``TMPDIR=$(python3 -c 'import os,tempfile;print(os.path.realpath(tempfile.gettempdir()))')``
first, or run through discovery with ``-p``.
"""

from __future__ import annotations

import os
import tempfile
import unittest

tempfile.tempdir = os.path.realpath(tempfile.gettempdir())


class CanonicalTempdirTests(unittest.TestCase):
    def test_the_suite_temp_root_has_no_symlink_in_it(self):
        with tempfile.TemporaryDirectory() as made:
            self.assertEqual(made, os.path.realpath(made))


if __name__ == "__main__":
    unittest.main()
