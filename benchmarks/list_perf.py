#!/usr/bin/env python3
"""Benchmark ``GET /api/skills?scope=all&body=0`` on a disposable fixture.

Method (same spirit as docs/50-rust-size-and-performance-assessment-2026-11-17.md):

* a synthetic library lives under one disposable root with its own ``HOME`` and
  ``SKILLS_MANAGER_DATA`` -- no personal skill and no real home is ever read;
* ``build`` writes a deterministic fixture (fixed content and mtimes), so a
  *before* and an *after* source tree can be run against the very same bytes;
* ``time`` starts the real HTTP server in-process, warms it once, then takes
  ``--repeat`` timed full-response GETs and prints one JSON summary;
* ``dump`` writes the parsed JSON response, sorted, for an equivalence diff;
* ``profile`` runs the request handler's work under ``cProfile``.

Usage (run from a source tree; ``PYTHONPATH`` selects which tree is measured)::

    python3 benchmarks/list_perf.py build  ROOT --skills 1000
    PYTHONPATH=<tree> python3 benchmarks/list_perf.py time ROOT --repeat 9
    PYTHONPATH=<tree> python3 benchmarks/list_perf.py dump ROOT OUT.json
    PYTHONPATH=<tree> python3 benchmarks/list_perf.py profile ROOT

The fixture is *not* a user-experience measurement: it is warm-cache, local,
and its documents are far smaller than a real library's.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import statistics
import sys
import time
from pathlib import Path

# (scope id, directory below HOME or the data root, recursive)
_AGENT_ROOTS = [
    ("claude-code", ".claude/skills"),
    ("codex", ".codex/skills"),
    ("cursor", ".cursor/skills"),
    ("opencode", ".config/opencode/skills"),
    ("gemini", ".gemini/skills"),
    ("commandcode", ".commandcode/skills"),
    ("agents", ".agents/skills"),
]
_FIXED_MTIME = 1_760_000_000


def _document(index: int, name: str) -> str:
    desc = (
        f"Synthetic skill number {index} used to benchmark the list endpoint. "
        "Use it when the user asks about fixtures, benchmarks or timing; it does nothing else."
    )
    body = "\n".join(
        f"## Step {n}\n\nParagraph {n} of skill {index}: lorem ipsum dolor sit amet, "
        "consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore."
        for n in range(1, 9)
    )
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {desc}\n"
        "version: 1.0.0\n"
        "license: MIT\n"
        "allowed-tools: Read, Grep\n"
        "metadata:\n"
        f"  category: bench-{index % 7}\n"
        "  tags: [bench, synthetic]\n"
        "---\n\n"
        f"# {name}\n\n{body}\n"
    )


def build(root: Path, skills: int) -> None:
    """Write ``skills`` records spread over global + seven agent roots.

    Roughly a third of the names recur in a second scope, as real libraries
    mirror skills between agents, so duplicate/instance-state work is exercised.
    """
    home, data = root / "home", root / "data"
    targets = [data / "skills"] + [home / rel for _, rel in _AGENT_ROOTS]
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
    (root / "cwd").mkdir(parents=True, exist_ok=True)
    for index in range(skills):
        name = f"bench-skill-{index % max(1, (skills * 2) // 3):05d}"
        target = targets[index % len(targets)]
        directory = target / name
        directory.mkdir(parents=True, exist_ok=True)
        doc = directory / "SKILL.md"
        doc.write_text(_document(index, name), encoding="utf-8")
        os.utime(doc, (_FIXED_MTIME, _FIXED_MTIME))
        os.utime(directory, (_FIXED_MTIME, _FIXED_MTIME))
    print(f"built {skills} records under {root}")


def _environ(root: Path) -> None:
    """Point every path this process resolves at the fixture, before imports."""
    os.environ["HOME"] = str(root / "home")
    os.environ["SKILLS_MANAGER_DATA"] = str(root / "data")
    os.environ["XDG_DATA_HOME"] = str(root / "xdg")
    os.environ["XDG_CONFIG_HOME"] = str(root / "xdg-config")
    os.environ["CODEX_HOME"] = str(root / "home" / ".codex")
    os.chdir(root / "cwd")


def _server(root: Path):
    from skillsmgr.store import Store
    from skillsmgr.webapp import WebAppServer
    import threading

    store = Store(data_dir=str(root / "data"))
    store.init_db()
    store.resync()  # the global scope lists the index, which a fresh fixture lacks
    server = WebAppServer(store, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return store, server


def _get(server, path: str, headers: dict | None = None) -> tuple[bytes, dict]:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=120)
    try:
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        body = resp.read()
        assert resp.status == 200, (resp.status, body[:200])
        return body, dict(resp.getheaders())
    finally:
        conn.close()


PATH = "/api/skills?scope=all&body=0"


def cmd_time(root: Path, repeat: int, extra_headers: dict | None = None) -> None:
    _environ(root)
    _store, server = _server(root)
    _get(server, PATH, extra_headers)  # warm: imports, index, page cache
    samples = []
    size = 0
    for _ in range(repeat):
        start = time.perf_counter()
        body, _headers = _get(server, PATH, extra_headers)
        samples.append((time.perf_counter() - start) * 1000)
        size = len(body)
    rows = json.loads(_get(server, PATH)[0])
    print(json.dumps({
        "records": len(rows),
        "bytes_on_wire": size,
        "repeat": repeat,
        "median_ms": round(statistics.median(samples), 1),
        "min_ms": round(min(samples), 1),
        "max_ms": round(max(samples), 1),
        "samples_ms": [round(s, 1) for s in samples],
    }))
    server.shutdown()


def cmd_dump(root: Path, out: Path) -> None:
    _environ(root)
    _store, server = _server(root)
    body, _ = _get(server, PATH)
    rows = json.loads(body)
    for row in rows:  # a wall-clock stamp, different on every request by design
        if isinstance(row.get("observed_at"), str):
            row["observed_at"] = "<now>"
    out.write_text(json.dumps(rows, sort_keys=True, indent=0), encoding="utf-8")
    print(f"{len(rows)} records, {len(body)} bytes -> {out}")
    server.shutdown()


def cmd_profile(root: Path, top: int) -> None:
    import cProfile
    import pstats

    _environ(root)
    store, server = _server(root)
    from skillsmgr import scopes
    from skillsmgr.web_serialization import json_bytes
    from skillsmgr import webapp

    def work():
        rows = scopes.list_all()
        webapp._enrich_rows_with_catalog(store, rows)
        page, _total = webapp._list_page(rows, {"body": ["0"]})
        return json_bytes(page)

    work()
    profiler = cProfile.Profile()
    profiler.enable()
    work()
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative").print_stats(top)
    stats.sort_stats("tottime").print_stats(top)
    server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("build", "time", "dump", "profile"):
        p = sub.add_parser(name)
        p.add_argument("root", type=Path)
    sub.choices["build"].add_argument("--skills", type=int, default=1000)
    sub.choices["time"].add_argument("--repeat", type=int, default=9)
    sub.choices["time"].add_argument("--gzip", action="store_true")
    sub.choices["dump"].add_argument("out", type=Path)
    sub.choices["profile"].add_argument("--top", type=int, default=30)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.cmd == "build":
        build(root, args.skills)
    elif args.cmd == "time":
        cmd_time(root, args.repeat, {"Accept-Encoding": "gzip"} if args.gzip else None)
    elif args.cmd == "dump":
        cmd_dump(root, args.out)
    else:
        cmd_profile(root, args.top)


if __name__ == "__main__":
    sys.exit(main())
