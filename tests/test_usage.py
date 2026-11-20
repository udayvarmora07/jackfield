"""Synthetic-only privacy and contract tests for transcript usage counts."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import usage


def _line(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode() + b"\n"


class UsageTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(usage, "_utc_now", return_value=datetime(2026, 11, 20, tzinfo=timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "manager"
        self.home = self.root / "home"
        (self.home / ".claude" / "projects" / "project").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _transcript(self, records):
        path = self.home / ".claude" / "projects" / "project" / "session.jsonl"
        path.write_bytes(b"".join(_line(row) for row in records))
        return path

    def _skill_record(self, ident="tool-1", skill="backend-api-design", message="PRIVATE-CANARY"):
        return {
            "timestamp": "2026-11-19T12:30:00Z",
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": ident, "name": "Skill",
                 "input": {"skill": skill, "args": message}},
            ]},
            "text": message,
        }

    def test_no_consent_never_reads_root_and_report_is_unknown(self):
        self._transcript([self._skill_record()])
        result = usage.report(self.data, home=self.home, refresh=True)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "no-consent")
        # Asking for a named agent remains a clear no-consent state.
        result = usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "no-consent")
        self.assertFalse((self.data / "usage").exists())

    def test_consent_scan_extracts_only_counts_and_private_cache(self):
        self._transcript([
            self._skill_record(),
            self._skill_record("tool-1"),  # duplicate event id
            {"timestamp": "2026-11-19T12:31:00Z", "message": {"content": [
                {"type": "tool_result", "name": "Skill", "content": "fake listing"},
                {"type": "text", "text": "backend-api-design was mentioned"},
                {"type": "attachment", "attachment": {"type": "invoked_skills", "name": "fake-skill"}},
            ]}},
        ])
        state = usage.enable(self.data, ["claude-code"], home=self.home)
        self.assertEqual(state["agents"], ["claude-code"])
        result = usage.report(self.data, home=self.home, refresh=True)
        self.assertEqual(len(result["counts"]), 1)
        self.assertEqual(result["counts"][0]["explicit"], 1)
        self.assertEqual(result["counts"][0]["inferred"], 0)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "available")
        payloads = list((self.data / "usage").glob("*.json"))
        self.assertTrue(payloads)
        for path in payloads:
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertNotIn(b"PRIVATE-CANARY", path.read_bytes())
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE((self.data / "usage").stat().st_mode), 0o700)

    def test_report_without_refresh_uses_cache_without_opening_transcript(self):
        path = self._transcript([self._skill_record()])
        usage.enable(self.data, ["claude-code"], home=self.home)
        initial = usage.report(self.data, home=self.home)
        self.assertEqual(initial["coverage"]["claude-code"]["status"], "not-scanned")
        usage.report(self.data, home=self.home, refresh=True)
        cache = self.data / "usage" / "counts.json"
        before = cache.read_bytes()
        path.unlink()
        cached = usage.report(self.data, home=self.home)
        self.assertEqual(cached["counts"][0]["explicit"], 1)
        self.assertEqual(cache.read_bytes(), before)

    def test_append_reads_new_events_and_deduplicates_ids(self):
        path = self._transcript([self._skill_record()])
        usage.enable(self.data, ["claude-code"], home=self.home)
        usage.report(self.data, home=self.home, refresh=True)
        with path.open("ab") as handle:
            handle.write(_line(self._skill_record("tool-2")))
        result = usage.report(self.data, home=self.home, refresh=True)
        self.assertEqual(result["counts"][0]["explicit"], 2)

    def test_agent_disable_retains_other_agent_consent_and_purge_removes_cache(self):
        usage.enable(self.data, ["claude-code", "codex"], home=self.home)
        state = usage.disable(self.data, ["claude-code"])
        self.assertEqual(state["agents"], ["codex"])
        usage.disable(self.data, purge=True)
        self.assertFalse((self.data / "usage").exists())

    def test_enable_merges_consent_and_scoped_disable_hides_revoked_counts(self):
        self._transcript([self._skill_record()])
        usage.enable(self.data, ["claude-code"], home=self.home)
        usage.enable(self.data, ["codex"], home=self.home)
        self.assertEqual(usage.consent_state(self.data)["agents"], ["claude-code", "codex"])
        usage.report(self.data, home=self.home, refresh=True)
        usage.disable(self.data, ["claude-code"])
        result = usage.report(self.data, ["claude-code"], home=self.home)
        self.assertEqual(result["counts"], [])
        with self.assertRaises(usage.UsageError):
            usage.disable(self.data, ["claude-code"], purge=True)

    def test_changed_configured_root_requires_fresh_consent(self):
        self._transcript([self._skill_record()])
        usage.enable(self.data, ["claude-code"], home=self.home)
        usage.report(self.data, home=self.home, refresh=True)
        other_home = self.root / "other-home"
        (other_home / ".claude" / "projects").mkdir(parents=True)
        result = usage.report(self.data, ["claude-code"], home=other_home, refresh=True)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "configuration-changed")
        self.assertEqual(result["counts"], [])
        usage.enable(self.data, ["claude-code"], home=other_home)
        result = usage.report(self.data, ["claude-code"], home=other_home, refresh=True)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "available")
        self.assertEqual(result["counts"], [])

    def test_revoke_then_rebind_root_clears_previous_roots_cached_counts(self):
        self._transcript([self._skill_record(skill="old-skill")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
        usage.disable(self.data, ["claude-code"])

        new_home = self.root / "moved-home"
        new_dir = new_home / ".claude" / "projects" / "project"
        new_dir.mkdir(parents=True)
        new_transcript = new_dir / "session.jsonl"
        new_transcript.write_bytes(_line(self._skill_record("new-tool", "new-skill")))
        usage.enable(self.data, ["claude-code"], home=new_home)
        result = usage.report(self.data, ["claude-code"], home=new_home, refresh=True)
        self.assertEqual([(row["name"], row["explicit"]) for row in result["counts"]], [("new-skill", 1)])

    def test_cache_limit_refuses_oversize_refresh_without_replacing_previous_counts(self):
        path = self._transcript([self._skill_record()])
        usage.enable(self.data, ["claude-code"], home=self.home)
        usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
        cache = self.data / "usage" / "counts.json"
        previous = cache.read_bytes()
        with path.open("ab") as handle:
            handle.write(_line(self._skill_record("tool-2")))
        original_limit = usage.MAX_CACHE_BYTES
        usage.MAX_CACHE_BYTES = len(previous) + 10
        try:
            with self.assertRaises(usage.UsageError):
                usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
            self.assertEqual(cache.read_bytes(), previous)
        finally:
            usage.MAX_CACHE_BYTES = original_limit
        result = usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
        self.assertEqual(result["counts"][0]["explicit"], 2)

    def test_corrupt_cache_reports_unknown_and_does_not_crash(self):
        usage.enable(self.data, ["claude-code"], home=self.home)
        cache = self.data / "usage" / "counts.json"
        cache.write_text("{broken", encoding="utf-8")
        result = usage.report(self.data, ["claude-code"], home=self.home)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "cache-invalid")

    def test_opencode_read_only_rows_and_incremental_watermark(self):
        database = self.home / ".local" / "share" / "opencode" / "opencode.db"
        database.parent.mkdir(parents=True)
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute("CREATE TABLE part (data TEXT NOT NULL)")
            row = {"type": "tool", "tool": "skill", "callID": "call-1",
                   "timestamp": "2026-11-19T12:30:00Z",
                   "state": {"input": {"name": "backend-api-design"}}}
            conn.execute("INSERT INTO part(data) VALUES (?)", (json.dumps(row, separators=(",", ":")),))
        usage.enable(self.data, ["opencode"], home=self.home)
        first = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
        self.assertEqual(first["counts"][0]["explicit"], 1)
        with closing(sqlite3.connect(database)) as conn, conn:
            row["callID"] = "call-2"
            conn.execute("INSERT INTO part(data) VALUES (?)", (json.dumps(row, separators=(",", ":")),))
        second = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
        self.assertEqual(second["counts"][0]["explicit"], 2)

    def test_codex_response_item_envelopes_and_known_skill_reads(self):
        root = self.home / ".codex" / "sessions" / "2026" / "11" / "20"
        root.mkdir(parents=True)
        skill_path = self.home / ".agents" / "skills" / "codex-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        fragment = {
            "timestamp": "2026-11-19T12:30:00Z", "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": [
                {"type": "input_text", "id": "fragment-1",
                 "text": f"<skill>\n<name>codex-skill</name>\n<path>{skill_path}</path>\nprivate body\n</skill>"},
            ]},
        }
        exec_call = {
            "timestamp": "2026-11-19T12:31:00Z", "type": "response_item",
            "payload": {"type": "function_call", "name": "exec_command", "call_id": "exec-1",
                        "arguments": json.dumps({"cmd": f"cat {skill_path}"})},
        }
        (root / "rollout-test.jsonl").write_bytes(_line(fragment) + _line(exec_call))
        usage.enable(self.data, ["codex"], home=self.home)
        result = usage.report(self.data, ["codex"], home=self.home, refresh=True)
        self.assertEqual(result["counts"][0]["name"], "codex-skill")
        self.assertEqual(result["counts"][0]["explicit"], 1)
        self.assertEqual(result["counts"][0]["inferred"], 1)

    def test_gemini_top_level_arrays_and_legacy_json_conversation(self):
        chat_root = self.home / ".gemini" / "tmp" / "project" / "chats"
        chat_root.mkdir(parents=True)
        message = {"id": "gemini-1", "timestamp": "2026-11-19T12:30:00Z", "type": "gemini",
                   "toolCalls": [{"id": "tool-1", "name": "activate_skill",
                                  "args": {"name": "gemini-array-skill"}}]}
        (chat_root / "session-array.jsonl").write_bytes(_line([message]))
        conversation = {"messages": [
            {"id": "gemini-2", "timestamp": "2026-11-19T12:31:00Z", "type": "gemini",
             "toolCalls": [{"id": "tool-2", "name": "activate_skill",
                            "args": {"name": "gemini-json-skill"}}]},
        ]}
        (chat_root / "session-legacy.json").write_text(json.dumps(conversation, indent=2), encoding="utf-8")
        usage.enable(self.data, ["gemini"], home=self.home)
        result = usage.report(self.data, ["gemini"], home=self.home, refresh=True)
        self.assertEqual({row["name"]: row["explicit"] for row in result["counts"]},
                         {"gemini-array-skill": 1, "gemini-json-skill": 1})

    def test_unknown_and_malformed_events_do_not_count(self):
        self._transcript([
            {"timestamp": "2026-11-19T12:30:00Z", "message": {"content": [
                {"type": "tool_use", "id": "listing", "name": "SkillListing", "input": {"skill": "valid-name"}},
                {"type": "tool_use", "id": "bad", "name": "Skill", "input": {"skill": "../../escape"}},
            ]}},
            {"version": "future-shape", "payload": {"name": "valid-name"}},
        ])
        usage.enable(self.data, ["claude-code"], home=self.home)
        result = usage.report(self.data, home=self.home, refresh=True)
        self.assertEqual(result["counts"], [])


if __name__ == "__main__":
    unittest.main()
