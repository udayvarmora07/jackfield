"""Offline failure checks for the published-to-candidate release rehearsal."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import verify_upgrade as upgrade


class VerifyUpgradeTests(unittest.TestCase):
    def test_download_is_size_bounded_and_rejects_a_same_length_wrong_hash(self):
        wheel = b"synthetic-wheel"
        checksum = hashlib.sha256(wheel).hexdigest()
        with patch.multiple(upgrade, BASELINE_SIZE=len(wheel), BASELINE_SHA256=checksum), \
                patch.object(upgrade, "_read", return_value=wheel) as download:
            self.assertEqual(upgrade._baseline_bytes(None), wheel)
            self.assertEqual(download.call_args.args[:2], (upgrade.BASELINE_URL, len(wheel)))
            download.return_value = b"x" * len(wheel)
            with self.assertRaisesRegex(upgrade.VerificationError, "pinned PyPI artifact"):
                upgrade._baseline_bytes(None)
            self.assertEqual(download.call_count, 2)

    def test_transient_download_timeout_retries_without_bypassing_verification(self):
        wheel = b"synthetic-wheel"
        checksum = hashlib.sha256(wheel).hexdigest()
        with patch.multiple(upgrade, BASELINE_SIZE=len(wheel), BASELINE_SHA256=checksum), \
                patch.object(upgrade, "_read", side_effect=[TimeoutError("stalled"), wheel]) as download, \
                patch.object(upgrade.time, "sleep") as backoff:
            self.assertEqual(upgrade._baseline_bytes(None), wheel)
            self.assertEqual(download.call_count, 2)
            backoff.assert_called_once_with(1)

    def test_offline_baseline_keeps_the_same_hash_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / upgrade.BASELINE_NAME
            path.write_bytes(b"wrong")
            with patch.object(upgrade, "_read") as download:
                with self.assertRaisesRegex(upgrade.VerificationError, "pinned PyPI artifact"):
                    upgrade._baseline_bytes(path)
                download.assert_not_called()

    def test_candidate_selection_requires_one_distinct_wheel(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            baseline = dist / upgrade.BASELINE_NAME
            baseline.touch()
            with self.assertRaisesRegex(upgrade.VerificationError, "differ from the baseline"):
                upgrade._candidate_wheel(dist)
            candidate = dist / "skill_control_plane-1.1.0-py3-none-any.whl"
            candidate.touch()
            with self.assertRaisesRegex(upgrade.VerificationError, "exactly one"):
                upgrade._candidate_wheel(dist)
            baseline.unlink()
            self.assertEqual(upgrade._candidate_wheel(dist), (candidate.resolve(), "1.1.0"))
