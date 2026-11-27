"""Agent tracking (web only, B1): ``<data>/tracking.json`` and its three routes.

Hermetic: HOME, $SKILLS_MANAGER_DATA and the working directory are a fresh
temp tree per test.  The contract under test is the signed-off one in
``ux-brief.md`` ("Feature: Agent tracking" -> Backend contract): tracking is a
view, never a change on disk; untracked agents are absent from every web route
and refused by every write; the CLI keeps seeing every scope.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from skillsmgr import context, scopes, tracking


def _skill(root: Path, name: str, description: str = "test skill") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nBody of {name}.\n", encoding="utf-8")
    return folder


class TrackingServerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name))
        self.home = self.root / "home"
        self.home.mkdir()
        self.work = self.home / "work"
        self.work.mkdir()
        saved = {key: os.environ.get(key) for key in ("HOME", "SKILLS_MANAGER_DATA")}
        os.environ["HOME"] = str(self.home)
        os.environ["SKILLS_MANAGER_DATA"] = str(self.root / "data")
        cwd = os.getcwd()
        os.chdir(self.work)

        def restore():
            os.chdir(cwd)
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            context.set_active_store(None)
        self.addCleanup(restore)
        for name in ("alpha", "beta"):
            _skill(self.home / ".claude/skills", name)
        for name in ("alpha", "cursor-only-1", "cursor-only-2"):
            _skill(self.home / ".cursor/skills", name)
        _skill(self.home / ".gemini/skills", "gem")
        _skill(self.home / ".kilo/skills", "kilo-one")
        from skillsmgr.webapp import WebAppServer

        self.store = scopes.Store()
        self.store.init_db()
        self.server = WebAppServer(self.store, port=0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.port}"

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json", "Origin": self.base}
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"null")

    def get(self, path):
        status, body = self.call("GET", path)
        self.assertEqual(status, 200, body)
        return body

    def put(self, document, expect=200):
        status, body = self.call("PUT", "/api/tracking", document)
        self.assertEqual(status, expect, body)
        return body

    def settings(self):
        report = self.get("/api/tracking")
        return report, json.loads(json.dumps(report["settings"]))

    def track_only(self, *ids):
        report, doc = self.settings()
        doc["agents"].update(chosen=True, tracked=list(ids))
        doc["revision"] = report["revision"]
        return self.put(doc)

    def scope_ids(self):
        return [row["id"] for row in self.get("/api/scopes")]

    def all_rows(self):
        body = self.get("/api/skills?scope=all&limit=500")
        rows = body["items"] if isinstance(body, dict) else body
        return sorted((row["scope"], row["name"]) for row in rows)


class TestDefaultsChangeNothing(TrackingServerCase):
    def test_missing_file_tracks_everything_found(self):
        report = self.get("/api/tracking")
        self.assertEqual(report["file"]["state"], "default")
        self.assertEqual(report["revision"], 0)
        self.assertFalse(report["settings"]["agents"]["chosen"])
        self.assertIn("cursor", report["tracked"])
        self.assertEqual(self.scope_ids(), [s["id"] for s in scopes.list_scopes()])
        cursor = next(a for a in report["agents"] if a["id"] == "cursor")
        self.assertEqual(cursor["skill_count"], 3)
        self.assertEqual(cursor["only_here"], {"count": 2, "names": ["cursor-only-1", "cursor-only-2"]})
        self.assertEqual(report["newly_found"], [])
        self.assertFalse((self.store.data_dir / "tracking.json").exists(), "a GET must never write")

    def test_also_reads_names_other_agents(self):
        report = self.get("/api/tracking")
        cursor = next(a for a in report["agents"] if a["id"] == "cursor")
        self.assertEqual([r["id"] for r in cursor["also_reads"]], ["claude-code", "codex"])
        self.assertTrue(cursor["reads_shared"])


class TestStopTracking(TrackingServerCase):
    def test_untracked_agent_is_absent_from_every_read(self):
        self.track_only("claude-code", "gemini")
        self.assertNotIn("cursor", self.scope_ids())
        self.assertNotIn("cursor", [s["id"] for s in self.get("/api/stats")["scopes"]])
        self.assertNotIn("cursor", {scope for scope, _ in self.all_rows()})
        found = self.get("/api/search?q=cursor-only&scope=all")
        self.assertEqual([r for r in found if r.get("scope") == "cursor"], [])
        workspaces = self.get("/api/workspaces")
        self.assertNotIn("cursor", [a["id"] for a in workspaces["adapters"]])
        self.assertIn("cline", [a["id"] for a in workspaces["adapters"]], "non-tracking adapters stay")

    def test_untracked_agent_is_refused_in_plain_words_and_never_written(self):
        self.track_only("claude-code")
        before = sorted(p.name for p in (self.home / ".cursor/skills").iterdir())
        status, body = self.call("GET", "/api/skills?scope=cursor")
        self.assertEqual(status, 400)
        self.assertIn("Cursor isn't tracked", body["error"])
        status, body = self.call("POST", "/api/skills?scope=cursor", {"name": "new-one", "description": "x"})
        self.assertEqual(status, 400, body)
        status, body = self.call("POST", "/api/skills/alpha/disable?scope=cursor")
        self.assertEqual(status, 400, body)
        status, body = self.call("POST", "/api/sync", {"name": "alpha", "from_scope": "claude-code",
                                                         "to_scopes": ["cursor"]})
        self.assertEqual(body["synced"], [], body)
        self.assertIn("Cursor isn't tracked", body["skipped"][0]["reason"])
        self.assertEqual(sorted(p.name for p in (self.home / ".cursor/skills").iterdir()), before)

    def test_cli_view_is_unchanged(self):
        self.track_only("claude-code")
        self.assertIn("cursor", [s.id for s in scopes.known_scopes()])
        self.assertIsNone(context.active_scope_overlay())

    def test_last_agent_stays_tracked(self):
        report, doc = self.settings()
        doc["agents"].update(chosen=True, tracked=[])
        status, body = self.call("PUT", "/api/tracking", doc)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "At least one agent stays tracked.")

    def test_undo_is_the_previous_document(self):
        report, before = self.settings()
        after = self.track_only("claude-code")
        before["revision"] = after["revision"]
        restored = self.put(before)
        self.assertIn("cursor", restored["tracked"])
        self.assertIn("cursor", self.scope_ids())

    def test_shared_folder_follows_its_readers(self):
        _skill(self.home / ".agents/skills", "shared-one")
        self.assertIn("agents", self.scope_ids())
        report = self.track_only("claude-code")
        self.assertFalse(report["shared"]["shown"])
        self.assertNotIn("agents", self.scope_ids())
        report = self.track_only("claude-code", "gemini")
        self.assertTrue(report["shared"]["shown"])
        self.assertEqual(report["shared"]["read_by"], ["gemini"])

    def test_link_into_untracked_agent_is_still_the_tracked_agents_skill(self):
        link = self.home / ".gemini/skills/beta"
        try:
            link.symlink_to(self.home / ".claude/skills/beta", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.track_only("gemini")
        rows = self.get("/api/skills?scope=gemini")
        rows = rows["items"] if isinstance(rows, dict) else rows
        beta = next(r for r in rows if r["name"] == "beta")
        self.assertNotEqual(beta.get("instance_state"), "link_escape")


class TestRevisionAndFile(TrackingServerCase):
    def test_stale_revision_is_409_and_writes_nothing(self):
        report, doc = self.settings()
        self.track_only("claude-code", "cursor")
        written = (self.store.data_dir / "tracking.json").read_bytes()
        doc["agents"].update(chosen=True, tracked=["gemini"])
        status, body = self.call("PUT", "/api/tracking", doc)
        self.assertEqual(status, 409)
        self.assertIn("changed in another window", body["error"])
        self.assertEqual((self.store.data_dir / "tracking.json").read_bytes(), written)

    @unittest.skipIf(os.name == "nt", "POSIX file modes")
    def test_file_is_private_and_home_relative(self):
        self.track_only("claude-code")
        path = self.store.data_dir / "tracking.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["projects"]["folders"], [])

    def test_broken_file_shows_everything_and_is_copied_aside(self):
        path = self.store.data_dir / "tracking.json"
        path.write_text('{"version": 1, "agents": {"tracked": "cursor"}}', encoding="utf-8")
        report = self.get("/api/tracking")
        self.assertEqual(report["file"]["state"], "broken")
        self.assertIn("must be a list", report["file"]["reason"])
        self.assertIn("cursor", report["tracked"])
        self.assertIn("cursor", self.scope_ids())
        doc = report["settings"]
        doc["agents"].update(chosen=True, tracked=["claude-code"])
        saved = self.put(doc)
        self.assertEqual(saved["file"]["state"], "ok")
        copies = list(self.store.data_dir.glob("tracking.broken-*.json"))
        self.assertEqual(len(copies), 1)
        self.assertIn('"tracked": "cursor"', copies[0].read_text(encoding="utf-8"))
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(copies[0].stat().st_mode), 0o600)

    def test_save_response_carries_its_own_committed_revision(self):
        report, doc = self.settings()
        doc["tool_groups"]["ai-assist"] = False
        make_report = tracking.report
        path = self.store.data_dir / "tracking.json"

        def report_after_another_save(data_dir, store_skills_dir, **options):
            later = json.loads(path.read_text(encoding="utf-8"))
            later["revision"] += 1
            later["tool_groups"]["add-skills"] = False
            path.write_text(json.dumps(later), encoding="utf-8")
            return make_report(data_dir, store_skills_dir, **options)

        with mock.patch.object(tracking, "report", side_effect=report_after_another_save):
            result = self.put(doc)
        self.assertEqual(result["revision"], report["revision"] + 1)
        self.assertTrue(result["settings"]["tool_groups"]["add-skills"])
        current = self.get("/api/tracking")
        self.assertEqual(current["revision"], result["revision"] + 1)
        self.assertFalse(current["settings"]["tool_groups"]["add-skills"])

    def test_journal_keeps_oversized_settings_when_replacement_write_fails(self):
        path = self.store.data_dir / "tracking.json"
        original = b"x" * (tracking.MAX_FILE_BYTES + 1)
        path.write_bytes(original)
        settings = tracking.default_document()
        with mock.patch.object(tracking, "atomic_write_text", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                tracking.save(self.store.data_dir, self.store.skills_dir, settings)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(path.parent.glob("tracking.broken-*.json")), [])

    def test_only_here_is_unknown_when_a_tracked_scan_is_partial(self):
        scope_names = tracking._scope_names

        def partial_scope_names(scope):
            if scope.id == "claude-code":
                return "ok", ["alpha"], False
            return scope_names(scope)

        with mock.patch.object(tracking, "_scope_names", side_effect=partial_scope_names):
            report = self.get("/api/tracking")
        cursor = next(agent for agent in report["agents"] if agent["id"] == "cursor")
        self.assertEqual(cursor["skill_count"], 3)
        self.assertIsNone(cursor["only_here"])

    def test_unknown_ids_are_refused_on_save(self):
        report, doc = self.settings()
        doc["agents"].update(chosen=True, tracked=["claude-code", "cline"])
        status, body = self.call("PUT", "/api/tracking", doc)
        self.assertEqual(status, 400)
        self.assertIn("doesn't know", body["error"])


class TestCustomAgents(TrackingServerCase):
    def add_kilo(self, **overrides):
        report, doc = self.settings()
        kilo = {"id": "custom-kilo", "name": "Kilo", "folder": "~/.kilo/skills", **overrides}
        doc["custom_agents"].append(kilo)
        doc["agents"].update(chosen=True, tracked=report["tracked"] + ["custom-kilo"])
        return self.call("PUT", "/api/tracking", doc)

    def test_add_custom_agent_shows_its_column_and_accepts_writes(self):
        status, report = self.add_kilo(project_folder=".kilo/skills")
        self.assertEqual(status, 200, report)
        kilo = next(a for a in report["agents"] if a["id"] == "custom-kilo")
        self.assertEqual((kilo["kind"], kilo["skill_count"], kilo["folder"]), ("custom", 1, "~/.kilo/skills"))
        self.assertIn("custom-kilo", self.scope_ids())
        self.assertIn(("custom-kilo", "kilo-one"), self.all_rows())
        status, body = self.call("POST", "/api/skills?scope=custom-kilo",
                                 {"name": "made-here", "description": "written to Kilo"})
        self.assertEqual(status, 201, body)
        self.assertTrue((self.home / ".kilo/skills/made-here/SKILL.md").is_file())

    def test_custom_agent_folder_rules(self):
        cases = {
            "~/.missing/skills": "doesn't exist",
            "~/.claude/skills": "That's Claude Code's folder. It's already tracked.",
            str(self.root): "inside your home folder",
        }
        for folder, message in cases.items():
            status, body = self.add_kilo(folder=folder)
            self.assertEqual(status, 400, folder)
            self.assertIn(message, body["error"])

    def test_name_taken_in_any_case(self):
        status, body = self.add_kilo(name="cursor")
        self.assertEqual(status, 400)
        self.assertIn("already used by Cursor", body["error"])

    def test_link_out_of_home_counts_as_outside(self):
        outside = self.root / "outside-skills"
        outside.mkdir()
        link = self.home / ".linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        status, body = self.add_kilo(folder="~/.linked")
        self.assertEqual(status, 400)
        self.assertIn("inside your home folder", body["error"])

    def test_missing_folder_later_does_not_block_other_saves(self):
        status, report = self.add_kilo()
        self.assertEqual(status, 200, report)
        for child in (self.home / ".kilo/skills").iterdir():
            (child / "SKILL.md").unlink()
            child.rmdir()
        (self.home / ".kilo/skills").rmdir()
        report = self.get("/api/tracking")
        kilo = next(a for a in report["agents"] if a["id"] == "custom-kilo")
        self.assertEqual(kilo["folder_status"], "missing")
        doc = report["settings"]
        doc["tool_groups"]["ai-assist"] = False
        self.put(doc)

    def test_hand_edited_unsafe_folders_never_become_writable(self):
        status, report = self.add_kilo()
        self.assertEqual(status, 200, report)
        path = self.store.data_dir / "tracking.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["custom_agents"][0]["folder"] = str(self.root)
        saved["projects"] = {"folders": [str(self.root)], "showing": str(self.root)}
        (self.root / ".claude/skills").mkdir(parents=True)
        path.write_text(json.dumps(saved), encoding="utf-8")
        ids = self.scope_ids()
        self.assertNotIn("custom-kilo", ids)
        self.assertNotIn("project-claude", ids)
        status, _body = self.call("POST", "/api/skills?scope=custom-kilo", {"name": "x", "description": "y"})
        self.assertEqual(status, 400)
        self.assertFalse((self.root / "x").exists())

    def test_broken_file_drops_custom_agents(self):
        self.add_kilo()
        (self.store.data_dir / "tracking.json").write_text("{", encoding="utf-8")
        self.assertNotIn("custom-kilo", self.scope_ids())


class TestProjectsAndNotices(TrackingServerCase):
    def test_showing_project_supplies_project_scopes(self):
        api = self.home / "work/api"
        _skill(api / ".claude/skills", "api-skill")
        _skill(api / ".cursor/skills", "api-cursor")
        report, doc = self.settings()
        doc["projects"] = {"folders": ["~/work/api"], "showing": "~/work/api"}
        report = self.put(doc)
        self.assertEqual(report["projects"][0]["skill_folders"], [".claude/skills", ".cursor/skills"])
        self.assertIn("project-claude", self.scope_ids())
        doc = report["settings"]
        doc["agents"].update(chosen=True, tracked=report["tracked"])
        doc["agents"]["count_projects"] = {"cursor": False}
        report = self.put(doc)
        self.assertNotIn("project-cursor", self.scope_ids())
        doc = report["settings"]
        doc["projects"]["showing"] = None
        self.put(doc)
        self.assertNotIn("project-claude", self.scope_ids())

    def test_project_folder_checks(self):
        (self.home / "work/web").mkdir()
        ok = self.call("POST", "/api/tracking/check-folder", {"path": "~/work/web", "purpose": "project"})[1]
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["preview"], {"skill_folders": [], "skill_count": 0})
        relative = self.call("POST", "/api/tracking/check-folder", {"path": "work/web", "purpose": "project"})[1]
        self.assertEqual(relative["problems"][0]["code"], "relative")
        report, doc = self.settings()
        doc["projects"]["folders"] = ["~/work/web"]
        self.put(doc)
        again = self.call("POST", "/api/tracking/check-folder", {"path": "~/work/web/", "purpose": "project"})[1]
        self.assertEqual(again["problems"][0]["code"], "already-listed")

    def test_agent_folder_check_previews_without_reading_documents(self):
        status, body = self.call("POST", "/api/tracking/check-folder", {"path": "~/.kilo/skills", "purpose": "agent"})
        self.assertEqual(status, 200)
        self.assertEqual(body["preview"], {"skill_count": 1, "suggested_name": "Kilo"})
        (self.home / ".kilo/skills/kilo-one/SKILL.md").chmod(0)
        try:
            body = self.call("POST", "/api/tracking/check-folder", {"path": "~/.kilo/skills", "purpose": "agent"})[1]
            self.assertEqual(body["preview"]["skill_count"], 1)
        finally:
            (self.home / ".kilo/skills/kilo-one/SKILL.md").chmod(0o644)
        untracked = self.track_only("claude-code")
        del untracked
        body = self.call("POST", "/api/tracking/check-folder", {"path": "~/.cursor/skills", "purpose": "agent"})[1]
        self.assertIn("Track Cursor instead", body["problems"][0]["message"])

    def test_new_agent_notice_until_seen(self):
        # Agents found when the user first chooses count as seen: no notice.
        report = self.track_only("claude-code")
        self.assertEqual(report["newly_found"], [])
        self.assertIn("gemini", report["settings"]["agents"]["seen"])
        # One found later (here: forgotten from seen) raises the notice once.
        report, doc = self.settings()
        doc["agents"]["seen"] = ["claude-code", "cursor"]
        report = self.put(doc)
        self.assertEqual([n["id"] for n in report["newly_found"]], ["gemini"])
        self.assertEqual(report["newly_found"][0]["skill_count"], 1)
        doc = report["settings"]
        doc["agents"]["seen"].append("gemini")
        self.assertEqual(self.put(doc)["newly_found"], [])


class TestStartupProject(unittest.TestCase):
    def test_home_folder_is_never_a_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(os.path.realpath(tmp))
            (home / ".claude/skills").mkdir(parents=True)
            saved, cwd = os.environ.get("HOME"), os.getcwd()
            os.environ["HOME"] = str(home)
            os.chdir(home)
            try:
                self.assertEqual(tracking.default_document()["projects"], {"folders": [], "showing": None})
            finally:
                os.chdir(cwd)
                if saved is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved


if __name__ == "__main__":
    unittest.main()
