#!/usr/bin/env python3
"""Compare public PyPI downloads to the two artifacts from the release build."""

from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

PROJECT = "skill-control-plane"
METADATA_LIMIT = 512 * 1024
ARTIFACT_LIMIT = 64 * 1024 * 1024
ATTEMPTS = 5


class VerificationError(ValueError):
    """The release could not be verified."""


class PublicationPending(VerificationError):
    """PyPI has yet to list every expected file."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read(url, limit, opener):
    with opener.open(url, timeout=15) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise VerificationError("PyPI response exceeds the expected size")
    return payload


def _local_artifacts(directory):
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise VerificationError("expected exactly one built wheel and one built source distribution")
    result = {}
    for path in (*wheels, *sdists):
        size = path.stat().st_size
        if not 0 < size <= ARTIFACT_LIMIT:
            raise VerificationError("built artifact size is outside the verification limit")
        with path.open("rb") as artifact:
            digest = hashlib.file_digest(artifact, "sha256").hexdigest()
        result[path.name] = size, digest
    return result


def _release_files(version, expected, opener):
    payload = _read(f"https://pypi.org/pypi/{PROJECT}/{quote(version, safe='')}/json", METADATA_LIMIT, opener)
    try:
        obj = json.loads(payload)
    except (ValueError, RecursionError) as exc:
        raise VerificationError("invalid PyPI release metadata") from exc
    if not isinstance(obj, dict) or not isinstance(obj.get("urls"), list):
        raise VerificationError("PyPI release metadata lacks an artifact list")
    files = {}
    for row in obj["urls"]:
        name = row.get("filename") if isinstance(row, dict) else None
        if not isinstance(name, str) or name not in expected or name in files:
            raise VerificationError("PyPI lists an unexpected or duplicate artifact")
        files[name] = row
    return files


def verify_release(directory: Path, version: str, *, opener=None) -> tuple[str, ...]:
    """Check metadata and downloaded bytes against the workflow's local artifacts."""
    if not re.fullmatch(r"[0-9][A-Za-z0-9.!+-]{0,63}", version):
        raise VerificationError("invalid PyPI release version")
    expected = _local_artifacts(directory)
    opener = opener if opener is not None else build_opener(_NoRedirect())
    files = _release_files(version, expected, opener)
    if files.keys() != expected.keys():
        raise PublicationPending("PyPI has not yet listed all expected release files")
    for name, (size, digest) in expected.items():
        entry = files[name]
        if entry.get("yanked") is True:
            raise VerificationError(f"PyPI has yanked {name}")
        published_hash = entry.get("digests")
        if (not isinstance(published_hash, dict) or published_hash.get("sha256") != digest
                or entry.get("size") != size):
            raise VerificationError(f"PyPI metadata differs from the tested artifact {name}")
        url = entry.get("url")
        parsed = urlsplit(url) if isinstance(url, str) else None
        if parsed is None or parsed.scheme != "https" or parsed.netloc != "files.pythonhosted.org":
            raise VerificationError("PyPI returned an unexpected download host")
        actual = _read(url, size, opener)
        if len(actual) != size or hashlib.sha256(actual).hexdigest() != digest:
            raise VerificationError(f"PyPI download differs from the tested artifact {name}")
    return tuple(expected)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args(argv)
    for attempt in range(ATTEMPTS):
        try:
            names = verify_release(args.dist_dir, args.version)
        except HTTPError as exc:
            retry = exc.code in {404, 429, 500, 502, 503, 504}
            message = f"PyPI request failed with HTTP {exc.code}"
            exc.close()
        except (PublicationPending, URLError, TimeoutError) as exc:
            retry, message = True, str(exc)
        except (OSError, ValueError, HTTPException) as exc:
            retry, message = False, str(exc)
        else:
            for name in names:
                print(f"PASS: PyPI download matches tested artifact {name}")
            return 0
        if not retry or attempt + 1 == ATTEMPTS:
            print(f"FAIL: {message}", file=sys.stderr)
            return 1
        time.sleep(5)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
