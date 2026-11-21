#!/usr/bin/env python3
"""Print failing features and assertion messages from local JUnit reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from xml.etree import ElementTree

MAX_REPORT = 8 * 1024 * 1024


def _report(path: Path, *, keploy: bool):
    with path.open("rb") as stream:
        payload = stream.read(MAX_REPORT + 1)
    if len(payload) > MAX_REPORT:
        raise ValueError("JUnit report exceeds the read limit")
    if b"<!DOCTYPE" in payload or b"<!ENTITY" in payload:
        raise ValueError("JUnit report declarations are unsupported")
    text = payload.decode("utf-8")
    if keploy:
        # v3.7.13 can log before its report command redirects logs to stderr.
        first_line, _, remainder = text.partition("\n")
        if (first_line.startswith("🐰 Keploy:")
                and "\tcgroup v2 (unified hierarchy) not detected;" in first_line
                and remainder.startswith("<?xml ")):
            text = remainder
    document = ElementTree.fromstring(text)
    if document.tag not in ("testsuite", "testsuites"):
        raise ValueError("expected a JUnit testsuite or testsuites element")
    return list(document.iter("testcase"))


def _single_line(value: str) -> str:
    return "".join(character if character.isprintable() else " " for character in value)[:300]


def _message(finding) -> str:
    lines = [line.strip() for line in (finding.text or "").splitlines() if line.strip()]
    # Hurl includes the values below its source excerpt in the failure text.
    details = []
    for line in lines:
        detail = line.removeprefix("|").lstrip()
        if line.startswith("|") and detail.startswith(("actual:", "expected:")):
            details.append(detail)
            if len(details) == 2:
                break
    primary = finding.get("message")
    if primary:
        lines = [primary, *(line for line in lines[:2] if line != primary)]
    return " ".join(lines[:2] + details)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keploy", action="store_true", help="accept Keploy's cgroup startup warning before XML")
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    status = 0
    for path in args.reports:
        try:
            rows = _report(path, keploy=args.keploy)
            if not rows:
                raise ValueError("JUnit report contains no test cases")
        except (OSError, ValueError, ElementTree.ParseError) as error:
            print(f"{_single_line(path.name)}: {_single_line(str(error))}", file=sys.stderr)
            status = 1
            continue
        failed = 0
        for row in rows:
            findings = [item for item in row if item.tag in ("failure", "error")]
            if not findings:
                continue
            failed += 1
            feature = row.get("classname") or row.get("file") or ""
            name = row.get("name", "unnamed")
            label = " / ".join(_single_line(part) for part in (feature, name) if part)
            for finding in findings:
                print(f"{label}: {_single_line(_message(finding))}")
        print(f"{_single_line(path.name)}: {len(rows)} test cases, {failed} failed")
        status |= bool(failed)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
