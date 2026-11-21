"""Published-release verification uses the exact tested wheel and sdist."""

import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import check_package_data
from tools import verify_published


class PublishedArtifactsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dist = Path(temp.name)
        self.files = {"skill_control_plane-1.1.0-py3-none-any.whl": b"wheel",
                      "skill_control_plane-1.1.0.tar.gz": b"sdist"}
        self.rows = []
        for name, data in self.files.items():
            (self.dist / name).write_bytes(data)
            self.rows.append({"filename": name, "size": len(data),
                              "digests": {"sha256": hashlib.sha256(data).hexdigest()},
                              "url": "https://files.pythonhosted.org/packages/" + name})
        self.metadata_url = "https://pypi.org/pypi/skill-control-plane/1.1.0/json"
        self.opener = Mock()

    def prepare_responses(self):
        responses = {self.metadata_url: json.dumps({"urls": self.rows}).encode()}
        responses.update({row["url"]: self.files[row["filename"]] for row in self.rows})
        self.opener.open.side_effect = lambda url, timeout: io.BytesIO(responses[url])
        return responses

    def test_verifies_both_public_downloads(self):
        self.prepare_responses()
        self.assertEqual(verify_published.verify_release(self.dist, "1.1.0", opener=self.opener), tuple(self.files))
        self.assertEqual([call.args[0] for call in self.opener.open.call_args_list],
                         [self.metadata_url, *[row["url"] for row in self.rows]])

    def test_rejects_download_with_mismatched_bytes_even_if_metadata_matches(self):
        responses = self.prepare_responses()
        responses[self.rows[1]["url"]] = b"wrong"
        with self.assertRaisesRegex(verify_published.VerificationError, "download differs"):
            verify_published.verify_release(self.dist, "1.1.0", opener=self.opener)

    def test_refuses_unexpected_download_host(self):
        self.rows[0]["url"] = "https://example.invalid/other.whl"
        self.prepare_responses()
        with self.assertRaisesRegex(verify_published.VerificationError, "unexpected download host"):
            verify_published.verify_release(self.dist, "1.1.0", opener=self.opener)
        self.opener.open.assert_called_once_with(self.metadata_url, timeout=15)

    def test_refuses_a_yanked_release(self):
        self.rows[0]["yanked"] = True
        self.prepare_responses()
        with self.assertRaisesRegex(verify_published.VerificationError, "yanked"):
            verify_published.verify_release(self.dist, "1.1.0", opener=self.opener)

    def test_main_retries_a_pending_publication(self):
        pending = verify_published.PublicationPending("missing source distribution")
        with patch.object(verify_published, "verify_release", side_effect=[pending, tuple(self.files)]) as verify, \
                patch.object(verify_published.time, "sleep") as delay, redirect_stdout(io.StringIO()):
            status = verify_published.main(["--dist-dir", str(self.dist), "--version", "1.1.0"])
        self.assertEqual(status, 0)
        self.assertEqual(verify.call_count, 2)
        delay.assert_called_once_with(5)

    def test_retries_missing_release_file_but_fails_closed_on_digest_mismatch(self):
        self.rows.pop()
        self.prepare_responses()
        with self.assertRaises(verify_published.PublicationPending):
            verify_published.verify_release(self.dist, "1.1.0", opener=self.opener)
        self.opener.reset_mock()
        self.rows[0]["digests"]["sha256"] = "0" * 64
        second = next(iter(self.files.keys() - {self.rows[0]["filename"]}))
        self.rows.append({"filename": second, "url": "https://files.pythonhosted.org/packages/" + second})
        self.prepare_responses()
        with self.assertRaisesRegex(verify_published.VerificationError, "metadata differs"):
            verify_published.verify_release(self.dist, "1.1.0", opener=self.opener)
        self.opener.open.assert_called_once_with(self.metadata_url, timeout=15)


class InstalledBuildToolTests(unittest.TestCase):
    def test_sdist_bootstraps_from_a_local_hash_locked_wheelhouse(self):
        succeeded = Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(check_package_data.subprocess, "run", return_value=succeeded) as run:
            root = Path(temp)
            check_package_data.clean_install(root / "package.tar.gz", root, wheelhouse=root / "wheels")
        create, bootstrap, install, probe = [call.args[0] for call in run.call_args_list]
        self.assertIn("venv", create)
        self.assertIn("--require-hashes", bootstrap)
        self.assertIn("--no-index", bootstrap)
        self.assertIn("--only-binary=:all:", bootstrap)
        self.assertIn(str(root / "wheels"), bootstrap)
        self.assertIn("--no-build-isolation", install)
        self.assertIn("--no-index", install)
        self.assertIn("-I", probe)

    def test_bootstrap_uses_the_resolved_interpreter_in_isolated_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            interpreter = root / "python"
            interpreter.touch()
            launcher = root / "launcher"
            try:
                launcher.symlink_to(interpreter)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            environment = {"PIP_CONFIG_FILE": "/example/devnull"}
            with patch.object(check_package_data.sys, "executable", str(launcher)), \
                    patch.object(check_package_data.subprocess, "run", return_value=Mock(returncode=0)) as run:
                child = check_package_data._create_install_venv(root / "venv", env=environment)
            self.assertEqual(child, check_package_data._venv_python(root / "venv"))
            argv = run.call_args.args[0]
            self.assertEqual(argv[:6], [str(interpreter), "-I", "-X", "utf8", "-m", "venv"])
            self.assertEqual(run.call_args.kwargs["cwd"], root)
            self.assertEqual(run.call_args.kwargs["env"], environment)
