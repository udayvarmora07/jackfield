"""Real PATCH roundtrips for fields exposed by the v2 editor."""

import json
import sqlite3
import threading
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from skillsmgr import editor_copy, scopes
from skillsmgr.frontmatter import dump_frontmatter, parse_frontmatter
from skillsmgr.webapp import WebAppServer
from tests.test_web_scopes import ScopedHomeTestCase


class EditFieldsTests(ScopedHomeTestCase):
    def setUp(self):
        super().setUp()
        self.store = scopes._global_store()
        self.server = WebAppServer(self.store, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.httpd.server_close()

    def request(self, method, path, fields):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.server.port}{path}",
            method=method, data=json.dumps(fields).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def patch(self, scope, fields):
        return self.request("PATCH", f"/api/skills/editable?scope={scope}", fields)

    def seed(self, scope):
        fields = dict(license="MIT", category="quality", version="1", compatibility="Python", allowed_tools="Read", body="# Original")
        if scope == "global":
            self.store.create("editable", "Keep description", **fields)
            return self.store.skills_dir / "editable" / "SKILL.md"
        scopes.create_skill(scope, "editable", "Keep description", **fields)
        return Path(self._tmp.name) / ".codex" / "skills" / "editable" / "SKILL.md"

    def copy_edit(self, scope, document, destinations, **fields):
        expected = {"path": str(document.parent.resolve()), "content_hash": sha256(document.read_bytes()).hexdigest()}
        roots = {sid: str(root.resolve()) for sid, root in destinations.items()}
        return self.request("POST", "/api/sync", {
            "name": "editable", "from_scope": scope, "to_scopes": list(destinations),
            "edit": {**fields, "expected": expected, "destinations": roots},
        })

    def test_edited_copy_preserves_source_and_indexes_the_library(self):
        source = self.seed("codex")
        original = source.read_bytes()
        (source.parent / "guide.md").write_bytes(b"Supporting text\n")
        status, data = self.copy_edit("codex", source, {"global": self.store.skills_dir}, body="# Edited")
        self.assertEqual(status, 200)
        self.assertEqual(data["synced"], ["global"])
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(self.store.get("editable")["body"].strip(), "# Edited")
        receipt = data["installed"]["global"]
        installed = Path(receipt["path"])
        self.assertEqual((installed / "guide.md").read_bytes(), b"Supporting text\n")
        route = "/api/skills/editable?scope=global"
        self.assertEqual(self.request("DELETE", route, {})[0], 400)
        self.assertTrue(installed.is_dir())
        (installed / "guide.md").write_bytes(b"Later change\n")
        self.assertEqual(self.request("DELETE", route, {"expected": receipt})[0], 400)
        self.assertTrue(installed.exists())
        (installed / "guide.md").write_bytes(b"Supporting text\n")
        status, result = self.request("DELETE", route, {"expected": receipt})
        self.assertEqual(status, 200)
        self.assertEqual((Path(result["trash_path"]) / "guide.md").read_bytes(), b"Supporting text\n")
        self.assertFalse(installed.exists())

    def test_edited_copy_refuses_a_retargeted_scope_and_keeps_other_results(self):
        source = self.seed("global")
        home = Path(self._tmp.name)
        codex_root = home / ".codex" / "skills"
        claude_root = home / ".claude" / "skills"
        codex_root.mkdir(parents=True)
        claude_root.mkdir(parents=True)
        _, observed = self.request("GET", "/api/scopes", {})
        self.assertEqual(
            next(place["physical_root"] for place in observed if place["id"] == "codex"),
            str(codex_root.resolve()),
        )
        status, result = self.copy_edit(
            "global", source, {"codex": home / "old-root", "claude-code": claude_root}, body="# Moved",
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["synced"], ["claude-code"])
        self.assertEqual([item["scope"] for item in result["skipped"]], ["codex"])
        self.assertFalse((codex_root / "editable").exists())
        self.assertTrue((claude_root / "editable" / "SKILL.md").is_file())

    def test_edited_copy_leaves_an_empty_folder_that_appears_at_publication(self):
        source = self.seed("global")
        codex_root = Path(self._tmp.name) / ".codex" / "skills"
        codex_root.mkdir(parents=True)
        publish = editor_copy.rename_new_directory

        def occupied_at_publish(stage, target):
            target.mkdir()
            publish(stage, target)

        with patch("skillsmgr.editor_copy.rename_new_directory", side_effect=occupied_at_publish):
            status, result = self.copy_edit("global", source, {"codex": codex_root}, body="# Edited")
        self.assertEqual(status, 200)
        self.assertEqual(result["synced"], [])
        self.assertEqual(result["skipped"][0]["scope"], "codex")
        self.assertEqual(list(codex_root.iterdir()), [codex_root.resolve() / "editable"])
        self.assertEqual(list((codex_root / "editable").iterdir()), [])

    def test_edited_copy_undo_reports_trash_path_if_index_update_fails(self):
        source = self.seed("codex")
        status, data = self.copy_edit("codex", source, {"global": self.store.skills_dir}, body="# Edited")
        self.assertEqual(status, 200)
        receipt = data["installed"]["global"]
        with patch.object(scopes.Store, "_history", side_effect=sqlite3.OperationalError("fixture failure")):
            status, result = self.request("DELETE", "/api/skills/editable?scope=global", {"expected": receipt})
        self.assertEqual(status, 200)
        self.assertIn("moved to Trash", result["warning"])
        self.assertTrue((Path(result["trash_path"]) / "SKILL.md").is_file())
        self.assertFalse(Path(receipt["path"]).exists())

    def test_edited_copy_keeps_undo_receipt_if_staging_cleanup_fails(self):
        source = self.seed("codex")
        with patch("shutil.rmtree", side_effect=PermissionError("fixture cleanup failure")):
            status, data = self.copy_edit("codex", source, {"global": self.store.skills_dir}, body="# Edited")
        self.assertEqual(status, 200)
        self.assertEqual(data["synced"], ["global"])
        self.assertEqual(data["skipped"], [])
        receipt = data["installed"]["global"]
        self.assertTrue(Path(receipt["path"]).is_dir())
        status, _ = self.request("DELETE", "/api/skills/editable?scope=global", {"expected": receipt})
        self.assertEqual(status, 200)
        self.assertFalse(Path(receipt["path"]).exists())

    def test_explicit_empty_optional_fields_and_body_are_persisted(self):
        for scope in ("global", "codex"):
            with self.subTest(scope=scope):
                path = self.seed(scope)
                status, _ = self.patch(scope, dict.fromkeys(("license", "category", "version", "compatibility", "allowed_tools", "body"), ""))
                self.assertEqual(status, 200)
                data, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(data["description"], "Keep description")
                self.assertEqual(data["metadata"]["category"], "")
                for key in ("license", "version", "compatibility", "allowed-tools"):
                    self.assertEqual(data[key], "")
                self.assertEqual(body.strip(), "")

    def test_omitted_fields_survive_and_empty_description_is_rejected(self):
        path = self.seed("global")
        self.assertEqual(self.patch("global", {"body": "# Changed"})[0], 200)
        data, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        self.assertEqual(data["license"], "MIT")
        before = path.read_bytes()
        status, result = self.patch("global", {"description": "", "body": "Must not write"})
        self.assertEqual(status, 400)
        self.assertIn("description", result["error"])
        self.assertEqual(path.read_bytes(), before)

    def test_body_only_patch_preserves_non_mapping_legacy_metadata(self):
        for scope in ("global", "codex"):
            with self.subTest(scope=scope):
                path = self.seed(scope)
                data, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                data["metadata"] = "legacy metadata value"
                path.write_text(dump_frontmatter(data) + body, encoding="utf-8")
                self.assertEqual(self.patch(scope, {"body": "# Changed"})[0], 200)
                current, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(current, data)

    def test_guarded_edit_and_snapshot_rollback_require_current_file(self):
        for scope in ("global", "codex"):
            with self.subTest(scope=scope):
                document = self.seed(scope)
                original = document.read_bytes()
                expected = {"path": str(document.parent.resolve()), "content_hash": sha256(original).hexdigest()}
                status, result = self.patch(scope, {"body": "# Edited", "expected": expected})
                self.assertEqual(status, 200)
                edited = document.read_bytes()
                self.assertEqual(result["content_hash"], sha256(edited).hexdigest())
                status, _ = self.patch(scope, {"body": "must not write", "expected": expected})
                self.assertEqual(status, 400)
                self.assertEqual(document.read_bytes(), edited)

                route = f"/api/trash/editable?snapshot={result['snapshot']}&scope={scope}"
                current = {**expected, "content_hash": result["content_hash"]}
                document.write_bytes(edited + b"External change.\n")
                status, _ = self.request("POST", route, {"expected": current})
                self.assertEqual(status, 400)
                self.assertTrue(document.read_bytes().endswith(b"External change.\n"))
                document.write_bytes(edited)
                status, _ = self.request("POST", route, {"expected": current})
                self.assertEqual(status, 200)
                self.assertEqual(document.read_bytes(), original)

    def test_create_preview_matches_written_bytes_and_bad_flag_cannot_create(self):
        fields = {"name": "previewed", "description": "Use this: café. # note\nAnother line.",
                  "body": "# Preview\r\n\r\nText", "license": "on", "allowed_tools": "Read "}
        status, preview = self.request("POST", "/api/skills?preview=1", fields)
        self.assertEqual(status, 200)
        global_file = self.store.skills_dir / "previewed" / "SKILL.md"
        self.assertFalse(global_file.exists())
        for query in ("preview=", "preview=0", "preview=1&preview=0"):
            status, _ = self.request("POST", f"/api/skills?{query}", fields)
            self.assertEqual(status, 400, query)
            self.assertFalse(global_file.exists())
        for scope in ("global", "codex"):
            status, result = self.request("POST", f"/api/skills?scope={scope}", fields)
            self.assertEqual(status, 201)
            self.assertEqual((Path(result["path"]) / "SKILL.md").read_bytes(), preview["content"].encode("utf-8"))
