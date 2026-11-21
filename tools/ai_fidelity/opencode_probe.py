#!/usr/bin/env python3
"""Verify OpenCode 2.3.2 skill observations against a loopback-only fake provider."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from threading import Thread

from . import run as fidelity

VERSION = "opencode v2.3.2"
SKILL = "unit-fixture"
DESCRIPTION = "Use this skill to verify a synthetic measurement."
BODY_MARKER = "fixture-instruction-29bdbf"
MODEL = "fixture-model"
MAX_REQUESTS = 6
MAX_BODY = 512 * 1024
_BLOCK = re.compile(r"<available_skills>(.*?)</available_skills>", re.DOTALL)
_ENTRY = re.compile(r"<skill>\s*<id>([^<]+)</id>\s*<name>([^<]+)</name>"
                    r"\s*<description>([^<]+)</description>\s*</skill>")
_STUDY = Path(__file__).resolve().parent / "evidence" / "2026-11-17"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str


@dataclass(frozen=True)
class Case:
    prompt: str
    choice: str | None
    skills: tuple[Skill, ...]

    @property
    def listing(self):
        return tuple(sorted((row.name, row.name, row.description) for row in self.skills))


_SIMPLE = Case("Verify a synthetic measurement.", SKILL, (Skill(SKILL, DESCRIPTION, BODY_MARKER),))


def require_loopback_namespace():
    """Refuse to start on a Linux network with an interface besides loopback."""
    interfaces = Path("/proc/net/dev").read_text().splitlines()[2:]
    if [line.split(":", 1)[0].strip() for line in interfaces] != ["lo"]:
        raise fidelity.FidelityError("run in a network namespace containing only loopback")


def write_fixture(project, url, case):
    permissions = [{"action": "*", "resource": "*", "effect": "deny"}]
    for row in case.skills:
        skill_dir = project / ".opencode" / "skills" / row.name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {row.name}\ndescription: {json.dumps(row.description)}\n---\n\n{row.body}\n", encoding="utf-8"
        )
        permissions.append({"action": "skill", "resource": row.name, "effect": "allow"})
    config = {
        "providers": {"fixture": {
            "name": "Fixture",
            "env": ["FIXTURE_API_KEY"],
            "package": "@opencode/ai/providers/openai-compatible",
            "settings": {"baseURL": url, "timeout": 5000},
            "models": {MODEL: {"name": "Fixture model"}},
        }},
        "permissions": permissions,
    }
    (project / "opencode.json").write_text(json.dumps(config), encoding="utf-8")


def _message_text(message):
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))


def _listing_rows(block):
    rows = []
    end = 0
    for entry in _ENTRY.finditer(block):
        if block[end:entry.start()].strip():
            raise ValueError("unexpected listing shape")
        rows.append(entry.groups())
        end = entry.end()
    if not rows or block[end:].strip() or len({row[0] for row in rows}) != len(rows):
        raise ValueError("unexpected listing shape")
    return tuple(rows)


def _wire_listing(messages):
    """Read every fixture entry from a single model-facing listing."""
    listing = None
    for message in messages:
        if message.get("role") not in {"developer", "system"}:
            continue
        for block in _BLOCK.findall(_message_text(message)):
            if listing is not None:
                raise ValueError("unexpected listing shape")
            listing = _listing_rows(block)
    return listing


def _delta(request, case):
    messages = request["messages"]
    tools = [entry["function"]["name"] for entry in request.get("tools") or []]
    listing = _wire_listing(messages)
    tool_results = [json.dumps(message["content"]) for message in messages if message.get("role") == "tool"]
    expected_body = next((row.body for row in case.skills if row.name == case.choice), None)
    if tool_results and (len(tool_results) != 1 or expected_body is None or expected_body not in tool_results[0]):
        raise ValueError("unexpected tool result")
    received_body = bool(tool_results)
    if listing is not None and tuple(sorted(listing)) != case.listing:
        raise ValueError("unexpected model-facing listing")
    if "skill" in tools:
        if listing is None:
            raise ValueError("skill tool advertised without a listing")
        final_prompt = next((_message_text(message) for message in reversed(messages)
                             if message.get("role") == "user"), "")
        if final_prompt != case.prompt:
            raise ValueError("saved prompt did not reach model unchanged")
    call_skill = case.choice is not None and "skill" in tools and not received_body
    observation = {"listing": listing, "received_body": received_body, "called_skill": call_skill}
    if call_skill:
        delta = {"tool_calls": [{"index": 0, "id": "call_fixture", "type": "function",
                                "function": {"name": "skill", "arguments": json.dumps({"id": case.choice})}}]}
        return delta, "tool_calls", observation
    return {"content": "Fixture response."}, "stop", observation


class FixtureProvider(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def log_message(self, *_args):
        pass

    def do_POST(self):
        self.server.calls += 1
        if self.server.calls > MAX_REQUESTS:
            self.send_error(400)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path != "/v1/chat/completions" or not 0 < length <= MAX_BODY:
                raise ValueError
            request = json.loads(self.rfile.read(length))
            if request.get("model") != MODEL or request.get("stream") is not True:
                raise ValueError
            delta, status, observation = _delta(request, self.server.case)
        except (OSError, ValueError, AttributeError, KeyError, TypeError, RecursionError):
            self.send_error(400)
            return
        self.server.observations.append(observation)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for item, reason in (({"role": "assistant", **delta}, None), ({}, status)):
            event = {"id": "fixture", "model": MODEL, "object": "chat.completion.chunk", "created": 0,
                     "choices": [{"index": 0, "delta": item, "finish_reason": reason}]}
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("ascii"))
        self.wfile.write(b"data: [DONE]\n\n")


def _run_cli(binary, args, project, env):
    with subprocess.Popen([str(binary), *args], cwd=project, env=env, start_new_session=True,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            raw, error = fidelity._drain(process, 30)
            if error or process.returncode != 0:
                raise fidelity.FidelityError("OpenCode failed or exceeded probe limits")
            return raw
        finally:
            fidelity._stop(process)


def _completed_skill_count(raw, chosen=SKILL):
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    completed = 0
    for event in events:
        if event["type"] == "error":
            raise fidelity.FidelityError("OpenCode reported an error")
        if event["type"] != "tool_use":
            continue
        part = event["part"]
        state = part["state"]
        if part["tool"] != "skill" or state["status"] != "completed" or state["input"]["id"] != chosen:
            raise fidelity.FidelityError("unexpected tool outcome")
        completed += 1
    if (completed != int(chosen is not None) or not events
            or events[-1]["type"] != "step_finish" or events[-1]["part"]["reason"] != "stop"):
        raise fidelity.FidelityError("unexpected number of completed skill calls or missing finished response")
    return completed


def probe(binary, root, case=_SIMPLE):
    project = root / "project"
    home = root / "home"
    home.mkdir()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_DATA_HOME": str(home / ".local/share"), "XDG_CACHE_HOME": str(home / ".cache"),
           "XDG_STATE_HOME": str(home / ".local/state"), "FIXTURE_API_KEY": "synthetic-placeholder"}
    with HTTPServer(("127.0.0.1", 0), FixtureProvider) as server:
        server.calls, server.observations = 0, []
        server.case = case
        write_fixture(project, f"http://127.0.0.1:{server.server_port}/v1", case)
        if _run_cli(binary, ["--version"], project, env).decode().strip() != VERSION:
            raise fidelity.FidelityError("probe requires OpenCode 2.3.2")
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            raw = _run_cli(binary, ["run", "--standalone", "--format", "json", "--model", f"fixture/{MODEL}",
                                    "--", case.prompt], project, env)
        finally:
            server.shutdown()
            thread.join()
    if not 1 <= server.calls <= MAX_REQUESTS or len(server.observations) != server.calls:
        raise fidelity.FidelityError("unexpected request count or rejected stub request")
    listings = [row["listing"] for row in server.observations if row["listing"] is not None]
    if not listings or any(tuple(sorted(listing)) != case.listing for listing in listings):
        raise fidelity.FidelityError("model-facing listing did not match the fixture")
    calls = [index for index, row in enumerate(server.observations) if row["called_skill"]]
    results = [index for index, row in enumerate(server.observations) if row["received_body"]]
    expected = int(case.choice is not None)
    if len(calls) != expected or len(results) != expected or (calls and calls[0] >= results[0]):
        raise fidelity.FidelityError("unexpected order or number of tool exchanges")
    return {"opencode": VERSION, "provider": "loopback-stub", "requests": server.calls,
            "listing_requests": len(listings), "tool_result_requests": len(results),
            "listing_sha256": hashlib.sha256(json.dumps(listings[0]).encode("ascii")).hexdigest(),
            "completed_skill_calls": _completed_skill_count(raw, case.choice)}


def _fixture_skill(entry):
    row = Skill(**entry)
    fidelity._key({"text": row.body, "expected": row.name})
    if (not isinstance(row.name, str) or not isinstance(row.description, str)
            or not 1 <= len(row.description) <= 1024 or "<" in row.description):
        raise fidelity.FidelityError("saved fixture skill is invalid")
    return row


def _load_replay(root):
    manifest, _ = fidelity._read_json(str(root / "sha256.json"))

    def load(name):
        document, digest = fidelity._read_json(str(root / name))
        if manifest.get(name) != digest:
            raise fidelity.FidelityError("saved study checksum does not match")
        return document

    prompts = load("deepseek-prompts.json")
    simulation = load("deepseek-simulation.json")
    fixture = load("deepseek-fixture.json")
    joined, meta = fidelity._joined(prompts, simulation)
    if len(joined) > fidelity.MAX_CASES or fixture.get("model") != meta["model"]:
        raise fidelity.FidelityError("unexpected replay case count or model")
    skills = tuple(sorted((_fixture_skill(entry) for entry in fixture["entries"]), key=lambda row: row.name))
    expected = {row.name for row in skills}
    if len(expected) != len(skills):
        raise fidelity.FidelityError("saved fixture skills are invalid")
    listing = [{"name": row.name, "description": row.description} for row in skills]
    if simulation.get("listing_snapshot") != listing:
        raise fidelity.FidelityError("fixture and simulator listing snapshot differ")
    if any(row["expected"] is not None and row["expected"] not in expected for row in joined):
        raise fidelity.FidelityError("saved prompt expects a skill outside the listing")
    return joined, skills, meta


def replay_published_study(binary, root, evidence=_STUDY):
    joined, skills, meta = _load_replay(evidence)
    rows = []
    for number, row in enumerate(joined, 1):
        case_root = root / f"case-{number:02d}"
        case_root.mkdir(mode=0o700)
        try:
            result = probe(binary, case_root, Case(row["text"], row["expected"], skills))
        except (fidelity.FidelityError, OSError, ValueError, KeyError, IndexError, TypeError) as error:
            raise fidelity.FidelityError(f"saved case {number} did not reproduce the expected exchange") from error
        rows.append({"prompt_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
                     "scripted_choice": row["expected"], **result})
    return {"kind": "offline-opencode-replay", "simulation_model": meta["model"],
            "simulation_listing_sha256": meta["listing_sha256"], "listing_entries": len(skills),
            "provider": "loopback-stub", "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opencode", required=True, type=Path, help="path to the trusted OpenCode 2.3.2 binary")
    parser.add_argument("--replay-published-study", action="store_true",
                        help="check the saved 12-prompt corpus using only scripted outcomes")
    args = parser.parse_args()
    try:
        require_loopback_namespace()
        with tempfile.TemporaryDirectory(prefix="sm-opencode-probe-") as temporary:
            runner = replay_published_study if args.replay_published_study else probe
            report = runner(args.opencode.resolve(strict=True), Path(temporary))
    except fidelity.FidelityError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, IndexError, TypeError, RecursionError):
        print("OpenCode probe failed with inaccessible or invalid evidence", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
