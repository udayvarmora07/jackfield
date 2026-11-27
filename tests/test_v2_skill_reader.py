"""HTTP contract for the Skill page's exact filesystem reader."""

import json
import threading
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

from skillsmgr import scopes
from skillsmgr.webapp import WebAppServer
from tests.test_web_scopes import ScopedHomeTestCase


class SkillReaderTests(ScopedHomeTestCase):
    def setUp(self):
        super().setUp()
        self.store = scopes._global_store()
        self.server = WebAppServer(self.store, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.httpd.server_close)
        self.addCleanup(self.thread.join, 5)
        self.addCleanup(self.server.shutdown)

    def get(self, name, **query):
        url = f"http://127.0.0.1:{self.server.port}/api/skills/{name}?{urlencode(query, doseq=True)}"
        try:
            reply = urllib.request.urlopen(url, timeout=5)
        except urllib.error.HTTPError as error:
            reply = error
        with reply:
            return reply.status, json.loads(reply.read())

    def read(self, name, folder, scope="global"):
        return self.get(name, view="reader", scope=scope, target_path=str(folder))

    def test_library_render_and_file_text_come_from_the_same_current_bytes(self):
        self.store.create("live-body", "Description at creation", body="Indexed text")
        folder = (self.store.skills_dir / "live-body").resolve()
        raw = b"\xef\xbb\xbf---\r\nname: live-body\r\ndescription: On disk\r\n---\r\n# Live text\r\n"
        (folder / "SKILL.md").write_bytes(raw)
        self.assertEqual(self.get("live-body")[1]["body"].strip(), "Indexed text")
        status, result = self.read("live-body", folder)
        self.assertEqual(status, 200)
        self.assertEqual(result["path"], str(folder))
        self.assertEqual(result["content_hash"], sha256(raw).hexdigest())
        self.assertEqual(result["raw"].encode("utf-8"), raw)
        self.assertEqual(result["body"].strip(), "# Live text")
        self.assertEqual(result["lines"], 5)
        self.assertEqual(result["files"], [])

    def test_exact_disabled_copy_has_its_own_files_and_counts(self):
        root = scopes.scope_by_id("opencode").base
        name = "nested-reader"
        for group, filename, body in (("one", "SKILL.md", "First"), ("two", "SKILL.md.disabled", "Second")):
            folder = root / group / name
            folder.mkdir(parents=True)
            (folder / filename).write_bytes(f"---\nname: {name}\ndescription: Test fixture\n---\n{body}\n".encode())
        folder = root / "two" / name
        (folder / "references").mkdir()
        (folder / "references" / "detail.md").write_bytes(b"First\rSecond\r\nThird")
        (folder / "picture.png").write_bytes(b"\x00\xff")
        status, result = self.read(name, folder, "opencode")
        self.assertEqual(status, 200)
        self.assertEqual(result["filename"], "SKILL.md.disabled")
        self.assertEqual(result["body"].strip(), "Second")
        self.assertEqual(result["files"], [
            {"path": "picture.png", "lines": None},
            {"path": "references/detail.md", "lines": 3},
        ])
        self.assertFalse(result["files_incomplete"])
        self.assertEqual(self.read(name, root / "one" / name, "opencode")[1]["files"], [])

    def test_missing_repeated_and_outside_path_return_clean_errors(self):
        self.store.create("visible", "Description")
        selected = self.store.skills_dir / "visible"
        foreign = Path(self._tmp.name) / "outside" / "visible"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("Outside scope", encoding="utf-8")
        self.assertEqual(self.get("visible", view="reader")[0], 400)
        self.assertEqual(self.get("visible", view="reader", target_path=[str(selected), str(foreign)])[0], 400)
        for target in (foreign, selected / ".." / "visible"):
            status, result = self.read("visible", target)
            self.assertEqual(status, 404)
            self.assertNotIn("Outside scope", str(result))

    def test_reader_refuses_a_linked_document(self):
        self.store.create("linked-reader", "Description")
        folder = self.store.skills_dir / "linked-reader"
        original = folder / "SKILL.md"
        target = Path(self._tmp.name) / "private.txt"
        target.write_bytes(b"private contents")
        original.unlink()
        try:
            original.symlink_to(target)
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        status, result = self.read("linked-reader", folder)
        self.assertEqual(status, 400)
        self.assertNotIn("private contents", str(result))
