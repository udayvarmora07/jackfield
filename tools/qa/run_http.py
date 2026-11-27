#!/usr/bin/env python3
"""Run Hurl HTTP contracts against an isolated, disposable Jackfield."""

from __future__ import annotations

import argparse
from contextlib import chdir
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from skillsmgr import paths  # noqa: E402
from skillsmgr.launcher_security import trusted_executable  # noqa: E402
from skillsmgr.store import Store  # noqa: E402
from skillsmgr.webapp import WebAppServer  # noqa: E402


def _seed_project(project: Path) -> None:
    for folder, name in ((".gemini/skills/gemini-fixture", "gemini-fixture"),
                         (".commandcode/skills/team/command-fixture", "command-fixture")):
        skill = project / folder
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Synthetic QA skill.\n---\n\nFixture.\n",
            encoding="utf-8",
        )
    (project / ".gemini/skills/SKILL.md").write_text(
        "---\nname: direct-fixture\ndescription: Synthetic standalone QA skill.\n---\n",
        encoding="utf-8",
    )


def _exercise(hurl: Path, root: Path, report: Path) -> int:
    project = root / "project"
    fixture_home = root / "agent-settings"
    fixture_home.mkdir()
    _seed_project(project)
    with chdir(project), patch.object(paths, "home_dir", return_value=fixture_home):
        store = Store(data_dir=root / "manager")
        store.init_db()
        store.create("library-fixture", "Synthetic library skill.", body="Synthetic body.")
        store.create("toggle-fixture", "Synthetic toggle skill.")
        store.create("recovery-fixture", "Synthetic skill to keep in trash.")
        store.create("purge", "Synthetic skill to recover.", body="Recovered fixture.")
        server = WebAppServer(store, host="127.0.0.1", port=0, extra_allowed_roots=[project])
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        print("The localhost binding is the unauthenticated test server's only security boundary.", flush=True)
        try:
            arguments = [
                str(hurl), "--test", "--noproxy", "*", "--no-color",
                "--variable", f"base=http://127.0.0.1:{server.port}",
                "--variable", f"project={project}",
                "--report-junit", str(report),
                *(str(file) for file in sorted(HERE.glob("*.hurl"))),
            ]
            return subprocess.run(arguments, cwd=project, timeout=90).returncode
        finally:
            server.shutdown()
            thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hurl", default="hurl", help="Hurl executable or name on PATH")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    executable = trusted_executable(args.hurl)
    if executable is None:
        parser.error("a trusted installed Hurl executable is required")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix="http-", dir=output))
    report = evidence / "junit.xml"
    with tempfile.TemporaryDirectory(prefix="skillsmgr-http-") as temporary:
        result = _exercise(Path(executable).resolve(), Path(os.path.realpath(temporary)), report)
    if not report.is_file():
        print("Hurl did not produce a JUnit report.", file=sys.stderr)
        return result or 1
    print(f"JUnit report: {report}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
