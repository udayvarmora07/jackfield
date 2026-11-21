"""Synthetic-only privacy and contract tests for transcript usage counts."""

from __future__ import annotations

from contextlib import closing, contextmanager
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
        environment = patch.dict(os.environ, {"XDG_DATA_HOME": "", "OPENCODE_DB": "opencode.db"})
        environment.start()
        self.addCleanup(environment.stop)
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

    def _command_transcript(self, number=1):
        directory = self.home / ".commandcode" / "projects" / "project"
        directory.mkdir(parents=True, exist_ok=True)
        row = self._skill_record(f"command-{number}")
        part = row["message"]["content"][0]
        part.update(name="activate_skill", input={"name": "run-checks"})
        (directory / f"session-{number}.jsonl").write_bytes(_line(row))

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

    def test_usage_report_includes_only_days_in_the_requested_utc_window(self):
        old = self._skill_record("old-id", "old-skill")
        old["timestamp"] = "2024-01-01T00:00:00Z"
        future = self._skill_record("future-id", "future-skill")
        future["timestamp"] = "2026-11-22T00:00:00Z"
        today = self._skill_record("today-id", "today-skill")
        today["timestamp"] = "2026-11-20T00:30:00Z"
        self._transcript([old, future, self._skill_record(), today])
        usage.enable(self.data, ["claude-code"], home=self.home)
        for refresh in (True, False):
            report = usage.report(self.data, days=1, refresh=refresh, home=self.home)
            self.assertEqual([(row["name"], row["first_seen"], row["last_seen"]) for row in report["counts"]],
                             [("today-skill", "2026-11-20", "2026-11-20")])
        cache = (self.data / "usage" / "counts.json").read_text()
        self.assertNotIn("old-skill", cache)
        self.assertNotIn("future-skill", cache)

    def test_capped_scan_can_resume_previously_uncounted_records(self):
        self._transcript([self._skill_record(), self._skill_record("tool-2")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_EVENTS", 1):
            first = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
            self.assertEqual(first["counts"][0]["explicit"], 1)
            self.assertEqual(first["coverage"]["claude-code"]["status"], "partial")
        for _ in range(2):
            current = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
            self.assertEqual(current["counts"][0]["explicit"], 2)

    def test_byte_budget_advances_through_a_file_across_refreshes(self):
        first = self._skill_record()
        self._transcript([first, self._skill_record("tool-2"), self._skill_record("tool-3")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        # Leave just enough budget to start the next line. It must be replayed
        # from its beginning on the following refresh.
        with patch.object(usage, "MAX_SCAN_BYTES", len(_line(first)) + 12):
            for count, status in [(1, "partial"), (2, "partial"), (3, "available"), (3, "available")]:
                report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                self.assertEqual([row["explicit"] for row in report["counts"]], [count])
                self.assertEqual(report["coverage"]["claude-code"]["status"], status)

    def test_file_byte_limit_caps_each_refresh_instead_of_skipping_the_file(self):
        first = self._skill_record()
        self._transcript([first, self._skill_record("tool-2"), self._skill_record("tool-3")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILE_BYTES", len(_line(first)) + 12):
            for count, status in [(1, "partial"), (2, "partial"), (3, "available")]:
                report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                self.assertEqual([row["explicit"] for row in report["counts"]], [count])
                self.assertEqual(report["coverage"]["claude-code"]["status"], status)

    def test_repeated_agent_selection_uses_only_one_refresh_budget(self):
        first = self._skill_record()
        self._transcript([first, self._skill_record("tool-2")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILE_BYTES", len(_line(first))):
            report = usage.report(self.data, ["claude-code", "claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [1])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "partial")

    def test_directories_do_not_consume_the_transcript_file_budget(self):
        self._transcript([self._skill_record()])
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILES", 1):
            report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [1])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "available")

    def test_file_budget_resumes_across_projects_and_wraps_without_duplicates(self):
        root = self.home / ".claude" / "projects"
        for index in range(5):
            project = root / f"private-project-{index}"
            project.mkdir()
            (project / "private-session.jsonl").write_bytes(_line(self._skill_record(f"tool-{index}")))
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILES", 2):
            for total, files_seen in [(2, 2), (4, 2), (5, 1), (5, 2)]:
                report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                self.assertEqual([row["explicit"] for row in report["counts"]], [total])
                self.assertEqual(report["coverage"]["claude-code"]["files_seen"], files_seen)
                self.assertEqual(report["coverage"]["claude-code"]["status"], "partial")
        cache = (self.data / "usage" / "counts.json").read_bytes()
        self.assertNotIn(b"private-project-", cache)
        self.assertNotIn(b"private-session.jsonl", cache)

    def test_busy_first_agent_cannot_starve_later_agents_on_repeated_refreshes(self):
        agents = ["claude-code", "commandcode"]
        first = self._skill_record(message="x" * 512)
        path = self._transcript([first])
        self._command_transcript()
        usage.enable(self.data, agents, home=self.home)
        with patch.object(usage, "MAX_SCAN_BYTES", len(_line(first))):
            report = usage.report(self.data, agents, refresh=True, home=self.home)
            self.assertEqual([row["agent"] for row in report["counts"]], ["claude-code"])
            with path.open("ab") as stream:
                stream.write(_line(self._skill_record("tool-2", message="x" * 512)))
            report = usage.report(self.data, agents, refresh=True, home=self.home)
        self.assertEqual([(row["agent"], row["explicit"]) for row in report["counts"]],
                         [("claude-code", 1), ("commandcode", 1)])
        self.assertEqual(list(report["coverage"]), agents)
        self.assertEqual(report["coverage"]["claude-code"]["status"], "partial")

    def test_budget_deferred_agent_retains_its_file_position(self):
        first = self._skill_record(message="x" * 512)
        self._transcript([first])
        self._command_transcript(1)
        self._command_transcript(2)
        agents = ["claude-code", "commandcode"]
        usage.enable(self.data, agents, home=self.home)
        with patch.object(usage, "MAX_FILES", 1):
            usage.report(self.data, ["commandcode"], refresh=True, home=self.home)
            with patch.object(usage, "MAX_SCAN_BYTES", len(_line(first))):
                report = usage.report(self.data, agents, refresh=True, home=self.home)
            self.assertEqual(report["coverage"]["commandcode"]["files_seen"], 0)
            report = usage.report(self.data, ["commandcode"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [2])

    def test_discovery_timeout_keeps_the_files_already_read(self):
        path = self._transcript([self._skill_record()])
        path.with_name("second.jsonl").write_bytes(_line(self._skill_record("tool-2")))
        usage.enable(self.data, ["claude-code"], home=self.home)
        scandir = os.scandir
        elapsed = 0.0

        def slow_entries(entries):
            nonlocal elapsed
            yield next(entries)
            elapsed = usage.MAX_SECONDS
            yield from entries

        @contextmanager
        def slow_scandir(directory):
            with scandir(directory) as entries:
                yield slow_entries(entries) if directory == path.parent else entries

        with patch.object(usage.time, "monotonic", side_effect=lambda: elapsed), \
                patch.object(usage.os, "scandir", side_effect=slow_scandir):
            report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [1])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "partial")
        for _ in range(2):
            report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [2])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "available")

    def test_file_cursor_wraps_if_the_transcript_set_shrinks(self):
        path = self._transcript([self._skill_record()])
        extra = path.with_name("second.jsonl")
        extra.write_bytes(_line(self._skill_record("tool-2")))
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILES", 1):
            first = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
            self.assertEqual([row["explicit"] for row in first["counts"]], [1])
            path.unlink()
            extra.write_bytes(_line(self._skill_record("tool-3")))
            for _ in range(2):
                report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [2])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "available")

    def test_capped_collection_keeps_only_bounded_watermarks_for_the_agent(self):
        path = self._transcript([self._skill_record()])
        for n in range(2, 5):
            path.with_name(f"session-{n}.jsonl").write_bytes(_line(self._skill_record(f"tool-{n}")))
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILES", 2), patch.object(usage, "MAX_AGENT_WATERMARKS", 3):
            for _ in range(3):
                report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [4])
        cache = json.loads((self.data / "usage" / "counts.json").read_bytes())
        self.assertEqual(len(cache["watermarks"]), 3)

    def test_skips_a_long_line_across_refreshes_without_parsing_its_suffix(self):
        first = self._skill_record()
        path = self._transcript([first])
        fake = _line(self._skill_record("skip-1", "fake-skill"))
        # Start the third window with a valid-looking JSON object that is
        # actually the tail of the line that exceeded the record cap.
        padding = 1024 - len(_line(first))
        with path.open("ab") as stream:
            stream.write(b" " * padding + fake + _line(self._skill_record("tool-2")))
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_FILE_BYTES", 512), patch.object(usage, "MAX_LINE_BYTES", 256):
            for count in (1, 1, 2, 2):
                report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                self.assertEqual([(row["name"], row["explicit"]) for row in report["counts"]],
                                 [("backend-api-design", count)])
                self.assertEqual(report["coverage"]["claude-code"]["status"], "partial")

    def test_events_before_deadline_are_preserved_when_reading_runs_out_of_time(self):
        last = self._skill_record("tool-2")
        self._transcript([self._skill_record(), last])
        usage.enable(self.data, ["claude-code"], home=self.home)
        last_line = _line(last)
        loads = json.loads
        elapsed = 0.0

        def timed_loads(raw):
            nonlocal elapsed
            if raw == last_line:
                elapsed = usage.MAX_SECONDS
            return loads(raw)

        with patch.object(usage.time, "monotonic", side_effect=lambda: elapsed), \
                patch.object(usage.json, "loads", side_effect=timed_loads):
            report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [1])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "partial")
        report = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual([row["explicit"] for row in report["counts"]], [2])
        self.assertEqual(report["coverage"]["claude-code"]["status"], "available")

    def test_oversized_line_remains_partial_when_file_is_unchanged(self):
        path = self._transcript([])
        path.write_bytes(b" " * 256 + b"\n")
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_LINE_BYTES", 256):
            for _ in range(2):
                result = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                self.assertEqual(result["coverage"]["claude-code"]["status"], "partial")

    def test_partial_append_resumes_with_only_enough_budget_for_the_tail(self):
        path = self._transcript([self._skill_record()])
        tail = _line(self._skill_record("tool-2"))
        with path.open("ab") as handle:
            handle.write(tail[:20])
        usage.enable(self.data, ["claude-code"], home=self.home)
        first = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
        self.assertEqual(first["coverage"]["claude-code"]["status"], "partial")
        self.assertEqual(first["counts"][0]["explicit"], 1)
        with path.open("ab") as handle:
            handle.write(tail[20:])
        with patch.object(usage, "MAX_SCAN_BYTES", len(tail) + 1):
            for _ in range(2):
                current = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                self.assertEqual(current["counts"][0]["explicit"], 2)
                self.assertEqual(current["coverage"]["claude-code"]["status"], "available")

    def test_skipped_record_remains_partial_after_budgeted_append(self):
        path = self._transcript([])
        path.write_bytes(b" " * 4500 + b"\n")
        usage.enable(self.data, ["claude-code"], home=self.home)
        with patch.object(usage, "MAX_LINE_BYTES", 256):
            first = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
            self.assertEqual(first["coverage"]["claude-code"]["status"], "partial")
            self.assertEqual(first["counts"], [])
            tail = _line(self._skill_record())
            with path.open("ab") as handle:
                handle.write(tail)
            with patch.object(usage, "MAX_SCAN_BYTES", len(tail) + 1):
                for _ in range(2):
                    current = usage.report(self.data, ["claude-code"], refresh=True, home=self.home)
                    self.assertEqual([row["explicit"] for row in current["counts"]], [1])
                    self.assertEqual(current["coverage"]["claude-code"]["status"], "partial")

    def test_older_text_watermark_is_rescanned_without_duplicate_counts(self):
        self._transcript([self._skill_record(), self._skill_record("tool-2")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        parse_events = usage._events

        def older_parser(*args, **kwargs):
            return [event for event in parse_events(*args, **kwargs) if event[-1] != "tool-2"]

        with patch.object(usage, "PARSER_VERSION", "usage-1"), \
                patch.object(usage, "_events", side_effect=older_parser):
            initial = usage.report(self.data, home=self.home, refresh=True)
        self.assertEqual(initial["counts"][0]["explicit"], 1)
        with patch.object(usage, "_WINDOWS", True):
            for _ in range(2):
                current = usage.report(self.data, home=self.home, refresh=True)
                self.assertEqual(current["counts"][0]["explicit"], 2)

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

    def test_cached_report_hides_counts_if_consent_changes_during_read(self):
        self._transcript([self._skill_record(skill="old-skill")])
        old = usage.enable(self.data, ["claude-code"], home=self.home)["roots"]
        usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
        other_home = self.root / "new-home"
        new = {"claude-code": str(other_home / ".claude" / "projects")}
        with patch.object(usage, "_load_consent", side_effect=[old, new]):
            result = usage.report(self.data, ["claude-code"], home=other_home)
        self.assertEqual(result["coverage"]["claude-code"]["status"], "cache-root-mismatch")
        self.assertEqual(result["counts"], [])

    def test_refresh_repairs_cache_from_a_different_root_without_reusing_counts(self):
        self._transcript([self._skill_record(skill="old-skill")])
        usage.enable(self.data, ["claude-code"], home=self.home)
        usage.report(self.data, ["claude-code"], home=self.home, refresh=True)
        other_home = self.root / "new-home"
        new_root = other_home / ".claude" / "projects"
        new_root.mkdir(parents=True)
        (new_root / "new.jsonl").write_bytes(_line(self._skill_record(skill="new-skill")))
        # Model a consent file restored separately from its aggregate cache.
        usage._write_json(self.data / "usage" / "consent.json",
                          {"version": 1, "roots": {"claude-code": str(new_root)}})
        cached = usage.report(self.data, ["claude-code"], home=other_home)
        self.assertEqual(cached["coverage"]["claude-code"]["status"], "cache-root-mismatch")
        self.assertEqual(cached["counts"], [])
        refreshed = usage.report(self.data, ["claude-code"], home=other_home, refresh=True)
        self.assertEqual([(r["name"], r["explicit"]) for r in refreshed["counts"]], [("new-skill", 1)])
        self.assertEqual(usage.report(self.data, ["claude-code"], home=other_home)["counts"], refreshed["counts"])

    def test_opencode_honors_xdg_and_database_overrides_with_fresh_consent(self):
        xdg = self.root / "private-xdg"
        database = xdg / "opencode" / "channel.db"
        database.parent.mkdir(parents=True)
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute("CREATE TABLE part (time_created INTEGER, data TEXT)")
            stamp = int(datetime(2026, 11, 19, tzinfo=timezone.utc).timestamp() * 1000)
            tool = {"type": "tool", "tool": "skill", "callID": "call-1",
                    "state": {"input": {"name": "open-custom"}}}
            conn.execute("INSERT INTO part VALUES (?, ?)", (stamp, json.dumps(tool)))
        usage.enable(self.data, ["opencode"], home=self.home)
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(xdg), "OPENCODE_DB": database.name}):
            result = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
            self.assertEqual(result["coverage"]["opencode"]["status"], "configuration-changed")
            self.assertEqual(result["counts"], [])
            state = usage.enable(self.data, ["opencode"], home=self.home)
            self.assertEqual(Path(state["roots"]["opencode"]), database)
            result = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
            self.assertEqual([row["name"] for row in result["counts"]], ["open-custom"])
        with patch.dict(os.environ, {"OPENCODE_DB": str(database), "XDG_DATA_HOME": "relative"}):
            result = usage.report(self.data, ["opencode"], home=self.home)
            self.assertEqual([row["name"] for row in result["counts"]], ["open-custom"])
        with patch.dict(os.environ, {"OPENCODE_DB": ":memory:"}), \
             patch.object(usage, "_scan_opencode") as scan:
            result = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
            self.assertEqual(result["coverage"]["opencode"]["status"], "source-unavailable")
            self.assertEqual(result["counts"], [])
            scan.assert_not_called()
            with self.assertRaisesRegex(usage.UsageError, "on-disk database"):
                usage.enable(self.data, ["opencode"], home=self.home)

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

    def test_malformed_coverage_keeps_valid_counts_and_other_scan_results(self):
        self._transcript([self._skill_record()])
        agents = ["claude-code", "codex"]
        usage.enable(self.data, agents, home=self.home)
        result = usage.report(self.data, agents, home=self.home, refresh=True)
        path = self.data / "usage" / "counts.json"
        cache = json.loads(path.read_bytes())
        original = cache["coverage"]["claude-code"]
        for broken in (None, {}, {**original, "status": "complete"},
                       {**original, "files_seen": -1},
                       {**original, "parser_versions": ["private-project/path"]}):
            with self.subTest(broken=broken):
                cache["coverage"]["claude-code"] = broken
                path.write_bytes(_line(cache))
                before = path.read_bytes()
                cached = usage.report(self.data, agents, home=self.home)
                self.assertEqual(cached["coverage"]["claude-code"]["status"], "cache-invalid")
                self.assertEqual(cached["coverage"]["codex"], result["coverage"]["codex"])
                self.assertEqual(cached["counts"], result["counts"])
                self.assertEqual(path.read_bytes(), before)

    def test_cached_coverage_projects_only_supported_fields_and_no_continuity(self):
        self._transcript([self._skill_record()])
        agents = ["claude-code"]
        usage.enable(self.data, agents, home=self.home)
        result = usage.report(self.data, agents, home=self.home, refresh=True)
        path = self.data / "usage" / "counts.json"
        cache = json.loads(path.read_bytes())
        cache["coverage"]["claude-code"].update(
            parser_versions=["usage-2"], coverage_window_start="2026-01-01",
            coverage_level="complete", parser_coverage="complete", transcript="PRIVATE-CANARY",
        )
        path.write_bytes(_line(cache))
        cached = usage.report(self.data, agents, home=self.home)
        expected = {**result["coverage"]["claude-code"], "parser_versions": ["usage-2"]}
        self.assertEqual(cached["coverage"]["claude-code"], expected)
        self.assertNotIn("PRIVATE-CANARY", json.dumps(cached))

    def test_saved_counts_require_canonical_days_and_supported_nonnegative_kinds(self):
        self._transcript([self._skill_record()])
        agents = ["claude-code"]
        usage.enable(self.data, agents, home=self.home)
        result = usage.report(self.data, agents, home=self.home, refresh=True)
        path = self.data / "usage" / "counts.json"
        cache = json.loads(path.read_bytes())
        item = cache["counts"]["claude-code\0backend-api-design"]
        item["by_day"] = {"2026-11-19": 1}  # The original cache used plain integers.
        path.write_bytes(_line(cache))
        self.assertEqual(usage.report(self.data, agents, home=self.home)["counts"], result["counts"])
        for bucket in ({"2026-11-19": -1}, {"2026-11-19": {"other": 1}},
                       {"2026-11-19T12:00:00Z": 1}):
            with self.subTest(bucket=bucket):
                item["by_day"] = bucket
                path.write_bytes(_line(cache))
                cached = usage.report(self.data, agents, home=self.home)
                self.assertEqual(cached["coverage"]["claude-code"]["status"], "cache-invalid")
                self.assertEqual(cached["counts"], [])
        refreshed = usage.report(self.data, agents, home=self.home, refresh=True)
        self.assertEqual(refreshed["counts"], result["counts"])

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

    def test_opencode_bounded_refresh_starts_with_the_latest_inserted_row(self):
        database = self.home / ".local" / "share" / "opencode" / "opencode.db"
        database.parent.mkdir(parents=True)
        row = {"type": "tool", "tool": "skill", "callID": "call-1",
               "timestamp": "2026-11-19T12:30:00Z", "state": {"input": {"name": "recent-skill"}}}
        latest = json.dumps(row)
        earlier = json.dumps(dict(row, callID="call-0", timestamp="2024-01-01T00:00:00Z"))
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute("CREATE TABLE part (data TEXT NOT NULL)")
            conn.executemany("INSERT INTO part VALUES (?)", [(earlier,), (latest,)])
        usage.enable(self.data, ["opencode"], home=self.home)
        with patch.object(usage, "MAX_SCAN_BYTES", len(latest)):
            for _ in range(2):
                report = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
                self.assertEqual([(item["name"], item["explicit"]) for item in report["counts"]],
                                 [("recent-skill", 1)])
                self.assertEqual(report["coverage"]["opencode"]["status"], "partial")

    def test_opencode_deadline_keeps_completed_events_from_a_stable_snapshot(self):
        database = self.home / ".local" / "share" / "opencode" / "opencode.db"
        database.parent.mkdir(parents=True)
        payload = {"type": "tool", "tool": "skill", "callID": "call-1",
                   "timestamp": "2026-11-19T12:30:00Z", "state": {"input": {"name": "run-checks"}}}
        rows = [(json.dumps(dict(payload, callID=f"call-{index}")),) for index in range(2)]
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute("CREATE TABLE part (data TEXT NOT NULL)")
            conn.executemany("INSERT INTO part VALUES (?)", rows)
        usage.enable(self.data, ["opencode"], home=self.home)
        loads = json.loads
        elapsed = 0.0
        parsed_rows = 0

        def timed_loads(raw):
            nonlocal elapsed, parsed_rows
            if raw in (rows[0][0], rows[1][0]):
                parsed_rows += 1
                if parsed_rows == 2:
                    elapsed = usage.MAX_SECONDS
            return loads(raw)

        with patch.object(usage.time, "monotonic", side_effect=lambda: elapsed), \
                patch.object(usage.json, "loads", side_effect=timed_loads):
            report = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
        self.assertEqual([item["explicit"] for item in report["counts"]], [1])
        self.assertEqual(report["coverage"]["opencode"]["status"], "partial")
        report = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
        self.assertEqual([item["explicit"] for item in report["counts"]], [2])

    def test_opencode_sqlite_interrupt_keeps_already_extracted_events(self):
        original_loads = json.loads
        stop_query = False

        def loads(raw):
            nonlocal stop_query
            stop_query = True
            return original_loads(raw)

        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("CREATE TABLE part (data TEXT NOT NULL)")
            for index in range(4):
                row = {"type": "tool", "tool": "skill", "callID": f"call-{index}",
                       "timestamp": "2026-11-19T12:30:00Z", "state": {"input": {"name": "run-checks"}}}
                conn.execute("INSERT INTO part VALUES (?)", (json.dumps(row),))
            conn.set_progress_handler(lambda: int(stop_query), 1)
            with patch.object(usage.json, "loads", side_effect=loads):
                events, partial, consumed = usage._read_opencode(conn, float("inf"), 4096)
        self.assertTrue(partial)
        self.assertGreater(consumed, 0)
        self.assertEqual(events, [("run-checks", "2026-11-19", "explicit", "call-3")])

    def test_opencode_v2_completed_skill_from_persisted_assistant_message(self):
        database = self.home / ".local" / "share" / "opencode" / "opencode.db"
        database.parent.mkdir(parents=True)
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute("CREATE TABLE session_message (id TEXT PRIMARY KEY, type TEXT, time_created INTEGER, data TEXT)")
            part = {"type": "tool", "name": "skill", "id": "call-1",
                    "state": {"status": "completed", "input": {"id": "run-checks"}}}
            running = {**part, "id": "call-2", "state": {"status": "running", "input": {"id": "skip-running"}}}
            row = json.dumps({"content": [running, part, part]})
            stamp = int(datetime(2026, 11, 19, tzinfo=timezone.utc).timestamp() * 1000)
            for row_type in ("assistant", "user"):
                conn.execute("INSERT INTO session_message VALUES (?, ?, ?, ?)", (row_type, row_type, stamp, row))
            explicit = json.dumps({"skill": "manual-check", "name": "manual-check", "text": "PRIVATE-ACTIVATION"})
            for row_type in ("skill", "synthetic"):
                conn.execute("INSERT INTO session_message VALUES (?, ?, ?, ?)", (row_type, row_type, stamp, explicit))
        usage.enable(self.data, ["opencode"], home=self.home)
        before = database.read_bytes()
        for _ in range(2):
            report = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
            self.assertEqual([(row["name"], row["explicit"]) for row in report["counts"]],
                             [("manual-check", 1), ("run-checks", 1)])
        self.assertNotIn(b"PRIVATE-ACTIVATION", (self.data / "usage" / "counts.json").read_bytes())
        self.assertEqual(database.read_bytes(), before)
        self.assertEqual(sorted(path.name for path in database.parent.iterdir()), [database.name])

    def test_opencode_waits_for_checkpoint_instead_of_ignoring_a_live_wal(self):
        database = self.home / ".local" / "share" / "opencode" / "opencode.db"
        database.parent.mkdir(parents=True)
        usage.enable(self.data, ["opencode"], home=self.home)
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE part (time_created INTEGER, data TEXT)")
            row = {"type": "tool", "tool": "skill", "callID": "call-1",
                   "state": {"input": {"name": "run-checks"}}}
            stamp = int(datetime(2026, 11, 19, tzinfo=timezone.utc).timestamp() * 1000)
            with conn:
                conn.execute("INSERT INTO part VALUES (?, ?)", (stamp, json.dumps(row)))
            report = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
            self.assertEqual(report["coverage"]["opencode"]["status"], "partial")
            self.assertEqual(report["counts"], [])
        report = usage.report(self.data, ["opencode"], home=self.home, refresh=True)
        self.assertEqual(report["coverage"]["opencode"]["status"], "available")
        self.assertEqual(report["counts"][0]["explicit"], 1)

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
                        "arguments": json.dumps({"cmd": f'cat "{skill_path}"'})},
        }
        path = root / "rollout-test.jsonl"
        first_batch = _line(fragment).replace(b"\n", b"\r\n")
        path.write_bytes(first_batch)
        usage.enable(self.data, ["codex"], home=self.home)
        usage.report(self.data, ["codex"], home=self.home, refresh=True)
        with path.open("ab") as transcript:
            transcript.write(_line(exec_call).replace(b"\n", b"\r\n"))
        result = usage.report(self.data, ["codex"], home=self.home, refresh=True)
        self.assertEqual(result["counts"][0]["name"], "codex-skill")
        self.assertEqual(result["counts"][0]["explicit"], 1)
        self.assertEqual(result["counts"][0]["inferred"], 1)

    def test_codex_windows_commands_keep_quoted_paths_and_backslashes(self):
        pathname = r"C:\Test Home\.agents\skills\codex-skill\SKILL.md"
        self.assertEqual(usage._codex_command_words(f'cat "{pathname}"', windows=True), ["cat", pathname])
        self.assertEqual(usage._codex_command_words(["cat", pathname], windows=True), ["cat", pathname])

    def test_codex_reports_multiple_reads_in_one_call_and_tolerates_unknown_items(self):
        root = self.home / ".codex" / "sessions"
        root.mkdir(parents=True)
        skills = self.home / ".agents" / "skills"
        first, second = (str(skills / name / "SKILL.md") for name in ("first-skill", "second-skill"))
        time = "2026-11-19T12:31:00Z"
        row = {"timestamp": time, "type": "response_item",
               "payload": {"type": "function_call", "name": "exec_command", "call_id": "exec-1",
                           "arguments": json.dumps({"cmd": ["cat", first, second, first]})}}
        malformed = {"timestamp": time, "message": {"role": "user", "content": [
            {"type": "input_text", "text": {"unknown": "SKILL.md"}}
        ]}}
        (root / "rollout.jsonl").write_bytes(_line(malformed) + _line(row) + _line(row))
        usage.enable(self.data, ["codex"], home=self.home)
        for _ in range(2):
            report = usage.report(self.data, ["codex"], home=self.home, refresh=True)
            self.assertEqual([(row["name"], row["inferred"]) for row in report["counts"]],
                             [("first-skill", 1), ("second-skill", 1)])

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
