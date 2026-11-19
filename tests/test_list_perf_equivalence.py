"""Pins for the merged-list speed-ups: faster, never different.

``GET /api/skills?scope=all&body=0`` is the Home page's first request.  The
optimisations behind it (``docs/52-list-request-performance-2026-11-19.md``)
replace whole-path ``realpath`` walks, ``Path`` objects and padding in the JSON
text with cheaper spellings of the *same answers*.  Each test here asserts the
answer against its definition -- ``os.path.realpath``, ``json.loads`` of the
library's own rows -- so a shortcut that drifts from it fails, on a tree that
contains the awkward cases (links, dangling links, a symlinked scope root,
nested recursive roots, disabled and conflicting documents).
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path

from skillsmgr import context, path_safety, registry, scopes
from skillsmgr.catalog import enrich_rows
from skillsmgr.loader import load_skill
from skillsmgr.store import Store
from skillsmgr.validator import validate_skill_name
from skillsmgr.web_serialization import json_bytes
from skillsmgr.webapp import WebAppServer

_LIST = "/api/skills?scope=all&body=0"


def _doc(name: str) -> str:
    return f"---\nname: {name}\ndescription: A skill for the list pins.\n---\nbody of {name}\n"


class ListPerfCase(unittest.TestCase):
    """A fresh HOME and data root, seeded with the awkward cases."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self._old = {k: os.environ.get(k) for k in ("HOME", "SKILLS_MANAGER_DATA")}
        os.environ["HOME"] = str(self.home)
        os.environ["SKILLS_MANAGER_DATA"] = str(self.base / "data")
        self._cwd = os.getcwd()
        os.chdir(self.base)
        context.set_active_store(None)
        self.addCleanup(self._restore)
        self.store = Store(data_dir=self.base / "data")
        self.store.init_db()

    def _restore(self):
        os.chdir(self._cwd)
        context.set_active_store(None)
        for key, old in self._old.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old

    def skill(self, directory: Path, name: str, *, disabled: bool = False) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        filename = "SKILL.md.disabled" if disabled else "SKILL.md"
        (directory / filename).write_text(_doc(name), encoding="utf-8")
        return directory

    def seed(self) -> None:
        """Global rows, flat and recursive agent scopes and every awkward entry."""
        for name in ("alpha", "beta"):
            self.skill(self.store.skills_dir / name, name)
        self.store.resync()
        claude = self.home / ".claude" / "skills"
        for name in ("alpha", "gamma"):
            self.skill(claude / name, name)
        self.skill(claude / "parked", "parked", disabled=True)
        # A document pair: the conflict flag the probe reports.
        both = self.skill(claude / "both", "both")
        (both / "SKILL.md.disabled").write_text(_doc("both"), encoding="utf-8")
        # An in-root link to a real directory, and one that dangles.
        os.symlink(claude / "gamma", claude / "alias")
        os.symlink(self.base / "nowhere", claude / "dangling")
        # A link out of the root: reported as drift, never followed.
        outside = self.skill(self.base / "outside" / "escapee", "escapee")
        os.symlink(outside, claude / "escapee")
        # A scope root that is itself a symlink (a dotfiles layout).
        real_gemini = self.base / "dotfiles" / "gemini-skills"
        self.skill(real_gemini / "delta", "delta")
        (self.home / ".gemini").mkdir()
        os.symlink(real_gemini, self.home / ".gemini" / "skills")
        # A recursive root with nested directories.
        agents = self.home / ".agents" / "skills"
        self.skill(agents / "top", "top")
        self.skill(agents / "apps" / "web" / "nested", "nested")


class ResolvedPathEquivalenceTests(ListPerfCase):
    """The shortcut answers must equal ``os.path.realpath`` -- or defer to it."""

    def test_every_listed_row_reports_the_definition_of_its_physical_path(self):
        self.seed()
        rows = scopes.list_all()
        self.assertGreaterEqual(len(rows), 8)
        for row in rows:
            if row.get("path"):
                self.assertEqual(
                    os.path.realpath(row["path"]), row["physical_path"], row["name"]
                )

    def test_the_memoised_realpath_matches_realpath_for_awkward_spellings(self):
        self.seed()
        claude = self.home / ".claude" / "skills"
        spellings = [
            claude / "alpha",
            claude / "alias",  # in-root link: must resolve to its target
            claude / "dangling",  # dangling link: realpath keeps the target
            claude / "escapee",  # out-of-root link
            claude / "missing",  # absent entry
            claude / "alpha" / "SKILL.md",  # a file, not a directory
            claude / "alpha" / ".." / "gamma",
            claude / ".",
            self.home / ".gemini" / "skills" / "delta",  # via a symlinked root
            self.home / ".agents" / "skills" / "apps" / "web" / "nested",
        ]
        memo: dict[str, str] = {}
        for path in spellings:
            with self.subTest(path=str(path)):
                self.assertEqual(
                    os.path.realpath(path), scopes._memoized_realpath(str(path), memo)
                )
        # No memo at all is the unchanged call.
        self.assertEqual(
            os.path.realpath(claude / "alias"),
            scopes._memoized_realpath(str(claude / "alias"), None),
        )

    def test_a_memo_is_not_reused_across_scans(self):
        """The memo is per scan: a directory swapped for a link is seen next time."""
        self.seed()
        claude = self.home / ".claude" / "skills"
        first = {r["name"]: r["physical_path"] for r in scopes.scan_scope("claude-code")}
        self.assertEqual(str(claude / "gamma"), first["gamma"])
        shutil.rmtree(claude / "alpha")
        os.symlink(claude / "gamma", claude / "alpha")
        second = {r["name"]: r["physical_path"] for r in scopes.scan_scope("claude-code")}
        self.assertEqual(str(claude / "gamma"), second["alpha"])

    @unittest.skipUnless(os.name == "posix", "the lexical shortcut answers only on POSIX; elsewhere it defers to realpath by design")
    def test_the_lexical_shortcut_defers_whenever_it_could_differ(self):
        self.seed()
        claude = str(self.home / ".claude" / "skills")
        real = path_safety._lexical_below
        self.assertEqual(claude + "/alpha", real(claude, ("alpha",)))
        self.assertEqual(
            str(self.home / ".agents/skills/apps/web/nested"),
            real(str(self.home / ".agents/skills"), ("apps", "web", "nested")),
        )
        for parts in (
            ("alias",),  # a link
            ("dangling",),
            ("missing",),  # absent
            ("alpha", "SKILL.md", "x"),  # below a file
            ("..",),
            (".",),
            ("",),
            ("a/b",),
            ("alpha\0",),
        ):
            with self.subTest(parts=parts):
                self.assertIsNone(real(claude, parts))

    def test_contained_entry_keeps_the_named_entry_and_still_rejects_escapes(self):
        self.seed()
        root = self.home / ".claude" / "skills"
        resolved = root.resolve()
        named = path_safety.contained_entry_under(resolved, "alias")
        self.assertEqual(resolved / "alias", named)  # the link itself, not its target
        self.assertEqual(
            resolved / "alpha", path_safety.contained_entry_under(resolved, "alpha")
        )
        with self.assertRaises(ValueError):
            path_safety.contained_entry_under(resolved, "escapee")
        self.assertEqual(
            os.path.realpath(root / "alias"),
            str(path_safety.contained_path_under(resolved, "alias")),
        )

    def test_a_global_row_path_is_the_contained_path_of_its_name(self):
        self.seed()
        resolved = self.store.skills_dir.resolve()
        self.assertEqual(
            str(path_safety.safe_skill_path(self.store.skills_dir, "alpha")),
            scopes._global_row_path("alpha", resolved),
        )
        self.assertIsNone(scopes._global_row_path("Not_Canonical", resolved))


class ProbeAndValidatorTests(ListPerfCase):
    def test_the_conflict_flag_still_means_both_regular_files(self):
        claude = self.home / ".claude" / "skills"
        both = self.skill(claude / "both", "both")
        (both / "SKILL.md.disabled").write_text(_doc("both"), encoding="utf-8")
        self.assertTrue(load_skill(both)["document_conflict"])
        # A *directory* named like the other document is not a document.
        odd = self.skill(claude / "odd", "odd")
        (odd / "SKILL.md.disabled").mkdir()
        self.assertFalse(load_skill(odd)["document_conflict"])
        only = self.skill(claude / "only", "only")
        self.assertFalse(load_skill(only)["document_conflict"])

    def test_sidecar_probe_answers_none_without_a_path_and_expands_a_tilde(self):
        claude = self.home / ".claude" / "skills"
        plain = self.skill(claude / "plain", "plain")
        self.assertIsNone(registry.read_provenance(plain))
        self.assertIsNone(registry.read_provenance(str(plain)))
        self.assertIsNone(registry._locate_sidecar(plain))
        located = self.skill(claude / "with-sidecar", "with-sidecar")
        sidecar = located / registry.PROVENANCE_FILENAME
        sidecar.write_text("{}", encoding="utf-8")
        # Windows ``expanduser`` reads USERPROFILE and ignores HOME.
        with mock.patch.dict(os.environ, {"USERPROFILE": str(self.home)}):
            for spelling in (located, str(located), "~/.claude/skills/with-sidecar"):
                with self.subTest(spelling=str(spelling)):
                    found = registry._locate_sidecar(spelling)
                    self.assertIsNotNone(found)
                    self.assertEqual(sidecar, found[1])
            self.assertIsNone(registry._locate_sidecar("~/.claude/skills/plain"))

    def test_reserved_device_names_are_still_rejected(self):
        for name in ("con", "NUL", "aux", "prn", "com1", "COM9", "lpt1", "Lpt9"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    validate_skill_name(name)
        for name in ("com10", "console", "lpt0", "alpha-1"):
            with self.subTest(name=name):
                self.assertEqual(name, validate_skill_name(name))


class ListEndpointEquivalenceTests(ListPerfCase):
    """The response parses to exactly the library's rows, minus the body."""

    def setUp(self):
        super().setUp()
        self.seed()
        self.server = WebAppServer(self.store, "127.0.0.1", 0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.shutdown)

    def request(self, method: str, path: str):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=30)
        try:
            conn.request(method, path)
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    @staticmethod
    def _stable(rows: list[dict]) -> list[dict]:
        out = []
        for row in rows:
            row = dict(row)
            row.pop("body", None)
            row.pop("observed_at", None)  # a per-request wall-clock stamp
            out.append(row)
        return out

    def test_the_parsed_list_equals_the_librarys_rows_without_the_body(self):
        status, headers, raw = self.request("GET", _LIST)
        self.assertEqual(200, status)
        rows = scopes.list_all()
        enrich_rows(rows, data_dir=self.store.data_dir)
        expected = self._stable(json.loads(json.dumps(rows)))
        self.assertEqual(expected, self._stable(json.loads(raw)))
        self.assertEqual(str(len(expected)), headers["X-Total-Count"])
        self.assertNotIn("body", json.loads(raw)[0])

    def test_compact_spelling_parses_to_the_default_spelling(self):
        _, _, raw = self.request("GET", _LIST)
        parsed = json.loads(raw)
        self.assertEqual(json.dumps(parsed, separators=(",", ":")).encode(), raw)
        self.assertEqual(parsed, json.loads(json.dumps(parsed)))
        # Only list pages opt in; a single value keeps the established spelling.
        self.assertEqual(b'{"ok": true}', json_bytes({"ok": True}))
        self.assertEqual(b'{"ok":true}', json_bytes({"ok": True}, compact=True))

    def test_non_ascii_and_control_text_survive_the_compact_spelling(self):
        value = [{"d": "naïve — 日本語   \"q\" \\ \n"}]
        self.assertEqual(value, json.loads(json_bytes(value, compact=True)))

    def test_head_reports_the_length_of_the_get_body(self):
        _, get_headers, raw = self.request("GET", _LIST)
        status, head_headers, body = self.request("HEAD", _LIST)
        self.assertEqual(200, status)
        self.assertEqual(b"", body)
        self.assertEqual(str(len(raw)), get_headers["Content-Length"])
        self.assertEqual(get_headers["Content-Length"], head_headers["Content-Length"])
        self.assertEqual(get_headers["X-Total-Count"], head_headers["X-Total-Count"])

    def test_paging_still_applies_to_the_compact_list(self):
        status, headers, raw = self.request("GET", _LIST + "&limit=3")
        self.assertEqual(200, status)
        self.assertEqual(3, len(json.loads(raw)))
        self.assertGreater(int(headers["X-Total-Count"]), 3)


if __name__ == "__main__":
    unittest.main()
