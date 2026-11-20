#!/usr/bin/env python3
"""Verify OpenCode 2.3.2 skill observations against a loopback-only fake provider."""

from __future__ import annotations

import argparse
import hashlib
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
_ENTRY = re.compile(r"\s*<skill>\s*<id>([^<]+)</id>\s*<name>([^<]+)</name>"
                    r"\s*<description>([^<]+)</description>\s*</skill>\s*")


def require_loopback_namespace():
    """Refuse to start on a Linux network with an interface besides loopback."""
    interfaces = Path("/proc/net/dev").read_text().splitlines()[2:]
    if [line.split(":", 1)[0].strip() for line in interfaces] != ["lo"]:
        raise fidelity.FidelityError("run in a network namespace containing only loopback")


def write_fixture(project, url):
    skill_dir = project / ".opencode" / "skills" / SKILL
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {SKILL}\ndescription: {DESCRIPTION}\n---\n\n{BODY_MARKER}\n", encoding="utf-8"
    )
    config = {
        "providers": {"fixture": {
            "name": "Fixture",
            "env": ["FIXTURE_API_KEY"],
            "package": "@opencode/ai/providers/openai-compatible",
            "settings": {"baseURL": url, "timeout": 5000},
            "models": {MODEL: {"name": "Fixture model"}},
        }},
        "permissions": [{"action": "*", "resource": "*", "effect": "deny"},
                        {"action": "skill", "resource": SKILL, "effect": "allow"}],
    }
    (project / "opencode.json").write_text(json.dumps(config), encoding="utf-8")


def _wire_listing(messages):
    """Read the single-entry fixture listing from model-facing instructions."""
    listing = None
    for message in messages:
        if message.get("role") not in {"developer", "system"}:
            continue
        content = message.get("content", "")
        text = content if isinstance(content, str) else "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
        for block in re.findall(r"<available_skills>(.*?)</available_skills>", text, re.DOTALL):
            entry = _ENTRY.fullmatch(block)
            if listing is not None or entry is None:
                raise ValueError("unexpected listing shape")
            listing = entry.groups()
    return listing


def _delta(request):
    messages = request["messages"]
    tools = [entry["function"]["name"] for entry in request.get("tools") or []]
    listing = _wire_listing(messages)
    received_body = any(message.get("role") == "tool" and BODY_MARKER in json.dumps(message["content"])
                        for message in messages)
    call_skill = "skill" in tools and listing == (SKILL, SKILL, DESCRIPTION) and not received_body
    observation = {"listing": listing, "received_body": received_body, "called_skill": call_skill}
    if call_skill:
        delta = {"tool_calls": [{"index": 0, "id": "call_fixture", "type": "function",
                                "function": {"name": "skill", "arguments": json.dumps({"id": SKILL})}}]}
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
            delta, status, observation = _delta(request)
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


def _completed_skill_count(raw):
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    completed = 0
    for event in events:
        if event["type"] == "error":
            raise fidelity.FidelityError("OpenCode reported an error")
        if event["type"] != "tool_use":
            continue
        part = event["part"]
        state = part["state"]
        if part["tool"] != "skill" or state["status"] != "completed" or state["input"]["id"] != SKILL:
            raise fidelity.FidelityError("unexpected tool outcome")
        completed += 1
    if completed != 1 or not events or events[-1]["type"] != "step_finish" or events[-1]["part"]["reason"] != "stop":
        raise fidelity.FidelityError("expected one completed skill call and a finished response")
    return completed


def probe(binary, root):
    project = root / "project"
    home = root / "home"
    home.mkdir()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_DATA_HOME": str(home / ".local/share"), "XDG_CACHE_HOME": str(home / ".cache"),
           "XDG_STATE_HOME": str(home / ".local/state"), "FIXTURE_API_KEY": "synthetic-placeholder"}
    with HTTPServer(("127.0.0.1", 0), FixtureProvider) as server:
        server.calls, server.observations = 0, []
        write_fixture(project, f"http://127.0.0.1:{server.server_port}/v1")
        if _run_cli(binary, ["--version"], project, env).decode().strip() != VERSION:
            raise fidelity.FidelityError("probe requires OpenCode 2.3.2")
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            raw = _run_cli(binary, ["run", "--standalone", "--format", "json", "--model", f"fixture/{MODEL}",
                                    "Verify a synthetic measurement."], project, env)
        finally:
            server.shutdown()
            thread.join()
    if not 1 <= server.calls <= MAX_REQUESTS or len(server.observations) != server.calls:
        raise fidelity.FidelityError("unexpected request count or rejected stub request")
    listings = [row["listing"] for row in server.observations if row["listing"] is not None]
    if not listings or any(listing != (SKILL, SKILL, DESCRIPTION) for listing in listings):
        raise fidelity.FidelityError("model-facing listing did not match the fixture")
    calls = [index for index, row in enumerate(server.observations) if row["called_skill"]]
    results = [index for index, row in enumerate(server.observations) if row["received_body"]]
    if len(calls) != 1 or len(results) != 1 or calls[0] >= results[0]:
        raise fidelity.FidelityError("expected one skill request followed by one result")
    return {"opencode": VERSION, "provider": "loopback-stub", "requests": server.calls,
            "listing_requests": len(listings), "tool_result_requests": len(results),
            "listing_sha256": hashlib.sha256(json.dumps(listings[0]).encode("ascii")).hexdigest(),
            "completed_skill_calls": _completed_skill_count(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opencode", required=True, type=Path, help="path to the trusted OpenCode 2.3.2 binary")
    args = parser.parse_args()
    try:
        require_loopback_namespace()
        with tempfile.TemporaryDirectory(prefix="sm-opencode-probe-") as temporary:
            report = probe(args.opencode.resolve(strict=True), Path(temporary))
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
