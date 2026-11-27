#!/usr/bin/env python3
"""Dev-only Chromium smoke harness for the local Jackfield UI.

This intentionally uses the system Chrome DevTools Protocol instead of adding
runtime or test dependencies. It starts a hermetic web server, launches
headless Chrome with a temporary profile, captures console/runtime/network
failures, and checks the supported viewport matrix. It is a developer check,
not part of the product CLI. Requirements: system Chrome/Chromium and Node >= 22
(the CDP client uses the global WebSocket, which older Node releases do not
provide).
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from threading import Thread
from contextlib import contextmanager

from skillsmgr.launcher_security import trusted_executable
from skillsmgr.store import Store
from skillsmgr.webapp import WebAppServer

ROOT = Path(__file__).resolve().parent
VIEWPORTS = ((320, 700), (400, 800), (640, 900), (900, 800), (1280, 900), (1440, 900))


def _executable_diagnostics(name: str) -> str:
    """Explain why no trusted PATH match exists for *name*.

    ``trusted_executable`` fails closed and returns ``None`` without saying
    which check rejected the candidate, so a CI runner that fails this way
    looks identical to a machine with nothing installed.
    """
    lines: list[str] = []
    resolved_which = shutil.which(name)
    if not resolved_which:
        lines.append(f"which({name}) found nothing on PATH")
        return "; ".join(lines)
    candidate = Path(resolved_which)
    try:
        info = candidate.stat()
        lines.append(f"which({name}) -> {candidate} (uid={info.st_uid}, mode={oct(info.st_mode & 0o777)})")
    except OSError as exc:
        lines.append(f"which({name}) -> {candidate} is not stat-able: {exc}")
        return "; ".join(lines)
    if os.name != "nt":
        if info.st_uid not in {os.getuid(), 0}:
            lines.append(f"rejected: uid {info.st_uid} is not this user or root")
        elif info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            lines.append("rejected: the file is group/world writable")
        for parent in candidate.resolve().parents:
            try:
                parent_info = parent.stat()
            except OSError:
                lines.append(f"rejected: {parent} is not stat-able")
                break
            if parent_info.st_uid not in {os.getuid(), 0}:
                lines.append(f"rejected: {parent} is owned by uid {parent_info.st_uid}")
                break
            if parent_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH) and not parent_info.st_mode & stat.S_ISVTX:
                lines.append(
                    f"rejected: {parent} is group/world writable "
                    f"(mode {oct(parent_info.st_mode & 0o777)})"
                )
                break
    return "; ".join(lines)


def _chrome() -> str:
    for name in ("google-chrome", "chromium", "chromium-browser"):
        path = trusted_executable(name, which=shutil.which)
        if path:
            return path
    detail = "; ".join(_executable_diagnostics(n) for n in ("google-chrome", "chromium"))
    raise RuntimeError(f"Chrome/Chromium is required for browser_harness.py ({detail})")


def _node() -> str:
    """Return a trusted Node executable for the small CDP client."""
    path = trusted_executable("node", which=shutil.which)
    if path:
        return path
    raise RuntimeError(
        f"a trusted Node executable is required for browser_harness.py "
        f"({_executable_diagnostics('node')})"
    )


def _chrome_stderr(log) -> str:
    """Return Chrome's own explanation of a startup failure.

    A crash dump is thousands of lines long and buries the one line that says
    why, so prefer the diagnostic lines (CHECK failures, fatal messages, and
    zygote/sandbox/namespace complaints) and fall back to the tail of the log.
    """
    try:
        log.flush()
        log.seek(0)
        text = log.read()
    except (OSError, ValueError):
        return ""
    text = text.strip()
    if not text:
        return ""
    interesting = [
        line.strip()
        for line in text.splitlines()
        if re.search(
            r"CHECK failed|FATAL|zygote|sandbox|namespace|No usable|"
            r"Failed to create|permission denied|Permission denied|"
            r"not permitted|Operation not permitted",
            line,
        )
    ]
    # Drop the stack frames that follow the message so the cause is readable.
    trimmed: list[str] = []
    for line in interesting:
        if line.startswith("#"):
            break
        trimmed.append(line)
    detail = "\n".join(trimmed) if trimmed else text[-2000:]
    return detail[:2000]


def _devtools_port(process: subprocess.Popen[str], profile: Path, timeout: float = 30.0,
                   log=None) -> int:
    """Return the DevTools port Chrome actually bound.

    Chrome writes the port it bound to ``DevToolsActivePort`` inside its
    profile directory. Letting the OS choose the port (``--remote-debugging-
    port=0``) and reading that file keeps the probe working when 9222 is taken
    and gives a cold runner more than a few seconds to start Chrome.
    """
    port_file = profile / "DevToolsActivePort"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = _chrome_stderr(log) if log is not None else ""
            raise RuntimeError(
                "Chrome exited before DevTools became available"
                + (f"; chrome stderr:\n{detail}" if detail else "")
            )
        try:
            port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        except (OSError, ValueError, IndexError):
            time.sleep(0.05)
            continue
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.5) as response:
                if response.status == 200:
                    return port
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.05)
    detail = _chrome_stderr(log) if log is not None else ""
    raise RuntimeError(
        "Chrome DevTools endpoint did not start"
        + (f"; chrome stderr:\n{detail}" if detail else "")
    )


def _run_probe(
    url: str, width: int, height: int, port: int,
    screenshot: Path | None = None, scenario: str = "populated",
) -> dict:
    """Use Chrome's remote debugging endpoint through a tiny Node CDP client."""
    script = r"""
const http = require('http');
if (typeof globalThis.WebSocket !== 'function') {
  console.error('browser_harness.py needs Node >= 22 for the global WebSocket used by the CDP client');
  process.exit(2);
}
const WebSocket = globalThis.WebSocket;
const url = process.argv[1], width = Number(process.argv[2]), height = Number(process.argv[3]), port = Number(process.argv[4]), screenshot = process.argv[5] || '', scenario = process.argv[6] || 'populated';
const navigationStarted = Date.now();
function getJson(path) { return new Promise((resolve, reject) => { const req=http.request('http://127.0.0.1:' + port + path, {method:'PUT'}, r => { let b=''; r.on('data', x=>b+=x); r.on('end',()=>resolve(JSON.parse(b))); }); req.on('error',reject); req.end(); }); }
(async () => {
  // Navigate after attaching CDP and installing the scenario hooks.
  const tabs = await getJson('/json/new?about%3Ablank');
  const ws = new WebSocket(tabs.webSocketDebuggerUrl);
  let id = 0, pending = new Map(), errors = [], warnings = [], failed = [];
  ws.onmessage = event => { const m = JSON.parse(event.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } else if (m.method === 'Runtime.consoleAPICalled') { const t=m.params.type; const text=(m.params.args||[]).map(a=>a.value||a.description||'').join(' '); (t==='error'?errors:warnings).push(text); } else if (m.method === 'Runtime.exceptionThrown') { const d=m.params.exceptionDetails; errors.push(d.exception && (d.exception.description || d.exception.value) || d.text || 'runtime exception'); } else if (m.method === 'Network.loadingFailed') failed.push(m.params.errorText); };
  const send = (method, params={}) => new Promise(resolve => { const n=++id; pending.set(n, resolve); ws.send(JSON.stringify({id:n,method,params})); });
  await new Promise(resolve => ws.onopen=resolve);
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', {width,height,deviceScaleFactor:1,mobile:false});
  if (scenario === 'scope-failure' || scenario === 'inventory-failure' || scenario === 'unavailable-root') {
    const failedRoute = scenario === 'scope-failure' ? '/api/scopes' : '/api/skills?scope=all';
    const preload = scenario === 'unavailable-root'
      ? `(() => { const original=window.fetch; window.fetch=function(input,init){ const target=typeof input==='string'?input:(input && input.url)||''; return original.call(this,input,init).then(response=>{ if(!target.includes('/api/scopes')) return response; return response.clone().json().then(scopes=>{ scopes.push({id:'unavailable-fixture',label:'Unavailable fixture',path:'/private/unavailable-root',kind:'agent',writable:false,availability:'unsupported',recursive:false,supported:false,exists:true,count:0,tokens:0}); return new Response(JSON.stringify(scopes),{status:response.status,headers:{'Content-Type':'application/json'}}); }); }); }; })();`
      : `(() => { const original=window.fetch; window.fetch=function(input,init){ const target=typeof input==='string'?input:(input && input.url)||''; if(target.includes(${JSON.stringify(failedRoute)})) return Promise.reject(new Error('synthetic first-scan failure')); return original.call(this,input,init); }; })();`;
    await send('Page.addScriptToEvaluateOnNewDocument', {source:preload});
  }
  await send('Page.navigate',{url});
  const evalValue = async (expression) => { const r = await send('Runtime.evaluate', {expression, returnByValue:true}); return r.result && r.result.result && r.result.result.value; };
  const pause = (ms) => new Promise(r=>setTimeout(r,ms));
  // Ready = the app has mounted, the page heading is no longer the loading
  // heading, and one representative block (agent cards, an empty-state note or
  // an error alert) is on screen. Then the visible text must hold still for two
  // consecutive checks (stableChecks), so a half-rendered frame never passes.
  const readyExpression = `(() => {
    const app = document.querySelector('#app');
    const heading = document.querySelector('#h1');
    const text = heading ? heading.innerText.trim() : '';
    const rooms = document.querySelectorAll('.room').length;
    const note = document.querySelector('.state-note');
    const emptyHome = document.querySelector('.room-empty');
    const alert = document.querySelector('[role="alert"]');
    const representative = rooms > 0 || !!note || !!emptyHome || !!alert;
    return {ready: !!app && !app.hasAttribute('v-cloak') && !!text && !/^Looking at/.test(text) && representative,
      rooms, emptyHome: emptyHome ? emptyHome.innerText.slice(0, 200) : '', alert: alert ? alert.innerText.slice(0, 200) : '',
      looks: document.querySelectorAll('.look').length, marker: (document.querySelector('#main') || document.body).innerText.slice(0, 400)};
  })()`;
  let previousMarker = null, stableChecks = 0, ready = false, lastState = null;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const state = await evalValue(readyExpression);
    lastState = state;
    if (state && state.ready && state.marker === previousMarker) stableChecks += 1;
    else stableChecks = 0;
    previousMarker = state ? state.marker : null;
    if (state && state.ready && stableChecks >= 2) { ready = true; break; }
    await pause(100);
  }
  if (!ready) throw new Error('The interface did not reach a stable rendered state: ' + JSON.stringify({lastState, errors, failed}));
  const firstUsefulMs = Date.now() - navigationStarted;
  const home = lastState;
  // Scenario expectations: populated shows agent cards and a Needs-a-look
  // queue (the malformed-observed fixture); empty says so in words; a failed
  // first scan shows an alert instead of a blank or crashed page.
  if (scenario === 'populated' && !(home.rooms > 0 && home.looks > 0)) errors.push('Populated home did not show agent cards and the Needs-a-look queue: ' + JSON.stringify(home));
  if (scenario === 'empty' && !(home.rooms === 0 && /No agent skill folders/.test(home.emptyHome))) errors.push('Empty home did not explain that no agent folders were found: ' + JSON.stringify(home));
  if ((scenario === 'scope-failure' || scenario === 'inventory-failure') && !home.alert) errors.push('A failed first scan did not surface an alert: ' + JSON.stringify(home));
  if (scenario === 'unavailable-root' && home.alert) errors.push('An unavailable agent root broke the first render: ' + JSON.stringify(home));

  // Command palette (Ctrl/Cmd K): opens focused and populated, arrow keys move
  // the highlighted option while focus stays in the field, typing filters by
  // synonyms, Enter opens the page and Escape-free navigation closes it.
  await evalValue(`(() => { document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true})); return true; })()`);
  let commandReady = false, commandState = null;
  for (let attempt = 0; attempt < 30; attempt += 1) {
    commandState = await evalValue(`(() => { const input=document.querySelector('#command-q'); return {dialog:!!document.querySelector('.dlg .palette'), focused:document.activeElement === input, results:document.querySelectorAll('#command-list [role="option"]').length, active:input ? input.getAttribute('aria-activedescendant') : ''}; })()`);
    if (commandState && commandState.dialog && commandState.focused && commandState.results > 0) { commandReady = true; break; }
    await pause(50);
  }
  if (!commandReady) errors.push('Ctrl+K did not open a focused, populated command palette: ' + JSON.stringify(commandState));
  else {
    await evalValue(`(() => { document.querySelector('#command-q').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true})); return true; })()`);
    await pause(60);
    const moved = await evalValue(`(() => { const input=document.querySelector('#command-q'); return {active:input.getAttribute('aria-activedescendant'), focused:document.activeElement === input, tabbable:document.querySelectorAll('#command-list [role="option"]:not([tabindex="-1"])').length}; })()`);
    if (!moved || moved.active !== 'cmd-1' || !moved.focused) errors.push('ArrowDown in the palette did not move the highlighted option while keeping focus in the field: ' + JSON.stringify(moved));
    if (moved && moved.tabbable) errors.push('Palette options are in the tab order');
    await evalValue(`(() => { const input=document.querySelector('#command-q'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(input,'trash'); input.dispatchEvent(new Event('input',{bubbles:true})); return true; })()`);
    await pause(80);
    const filtered = await evalValue(`(() => [...document.querySelectorAll('#command-list [role="option"]')].map(o => o.innerText.trim()))()`);
    if (!filtered || !filtered.some(label => /Recovery/.test(label))) errors.push('Palette synonyms did not find Recovery for "trash": ' + JSON.stringify(filtered));
    await evalValue(`(() => { document.querySelector('#command-q').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); return true; })()`);
    let landed = null;
    // After a failed first scan every page states the failure instead of its own content.
    const expectedHeading = (scenario === 'scope-failure' || scenario === 'inventory-failure') ? /^(Recovery|Couldn.t read your skills)$/ : /^Recovery$/;
    for (let attempt = 0; attempt < 30; attempt += 1) {
      landed = await evalValue(`(() => ({hash:location.hash, heading:document.querySelector('#h1') ? document.querySelector('#h1').innerText.trim() : '', dialog:!!document.querySelector('.dlg .palette')}))()`);
      if (landed && landed.hash === '#/recovery' && expectedHeading.test(landed.heading) && !landed.dialog) break;
      await pause(50);
    }
    if (!landed || landed.hash !== '#/recovery' || !expectedHeading.test(landed.heading) || landed.dialog) errors.push('Enter in the palette did not open Recovery and close the palette: ' + JSON.stringify(landed));
  }

  // Header search never navigates while typing; it lists matches and Escape
  // closes the list. (The empty fixture has no skills, so it lists none.)
  const searchState = await evalValue(`(() => { const input=document.querySelector('#gq'); if (!input || input.offsetParent === null) return {visible:false}; const before=location.hash; input.focus(); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(input,'probe'); input.dispatchEvent(new Event('input',{bubbles:true})); return {visible:true, before}; })()`);
  if (searchState && searchState.visible) {
    await pause(80);
    const listed = await evalValue(`(() => ({hash:location.hash, open:!!document.querySelector('.gq-pop'), matches:document.querySelectorAll('.gq-pop [role="option"]').length}))()`);
    if (!listed || listed.hash !== searchState.before || !listed.open) errors.push('Typing in the header search navigated or showed no result list: ' + JSON.stringify(listed));
    if (scenario === 'populated' && listed && !listed.matches) errors.push('Header search listed no match for a fixture skill');
    await evalValue(`(() => { document.querySelector('#gq').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); return true; })()`);
    await pause(60);
    const closed = await evalValue(`(() => !document.querySelector('.gq-pop'))()`);
    if (!closed) errors.push('Escape did not close the header search results');
  }

  // Quality renders bounded evidence (findings are paged) without overflow.
  await evalValue(`(() => { location.hash = '#/tools/quality'; return true; })()`);
  let qualityState = null, qualityReady = false;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    qualityState = await evalValue(`(() => ({heading:document.querySelector('#h1') ? document.querySelector('#h1').innerText.trim() : '', findings:document.querySelectorAll('.tp-findings > li').length, settled:!!document.querySelector('#tp-findings, .tp-empty, [role="alert"]'), overflow:document.documentElement.scrollWidth>window.innerWidth}))()`);
    if (qualityState && qualityState.heading === 'Quality' && qualityState.settled && !qualityState.overflow) { qualityReady = true; break; }
    await pause(100);
  }
  if (!qualityReady) errors.push('Quality did not render bounded evidence without overflow: ' + JSON.stringify(qualityState));
  if (qualityState && qualityState.findings > 50) errors.push('Quality rendered more than one page (50) of findings at once');
  await evalValue(`(() => { location.hash = '#/home'; return true; })()`);
  await pause(150);
  if (screenshot) {
    const capture = await send('Page.captureScreenshot', {format:'png', captureBeyondViewport:true});
    require('fs').writeFileSync(screenshot, Buffer.from(capture.result.data, 'base64'));
  }
  const value = await send('Runtime.evaluate',{expression:'JSON.stringify({title:document.title,modalCount:document.querySelectorAll("[role=dialog]").length,overflow:document.documentElement.scrollWidth>window.innerWidth})',returnByValue:true});
  ws.close(); console.log(JSON.stringify({width,height,scenario,document:JSON.parse(value.result.result.value),firstScan:{first_useful_ms:firstUsefulMs,rooms:home.rooms,needs_a_look:home.looks,alert:home.alert},errors,warnings,failed}));
})().catch(e=>{ console.error(e.stack||String(e)); process.exit(1); });
"""
    screenshot_arg = str(screenshot) if screenshot is not None else ""
    result = subprocess.run([_node(), "-e", script, url, str(width), str(height), str(port), screenshot_arg, scenario], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _stop_process(process: subprocess.Popen[str], label: str, timeout: float = 20.0) -> None:
    """Terminate a child and reap it, without ever raising from cleanup.

    The harness used to do `chrome.terminate(); chrome.wait(timeout=5)` in its
    `finally` block. On a busy shared runner Chrome routinely needs longer than
    five seconds to exit after SIGTERM, and `Popen.wait` raises
    `TimeoutExpired` when it does — from a cleanup path, which then *replaced
    the real result*. A run that had passed every probe was reported as a
    failure on 2026-10-06 for exactly this reason, and the traceback pointed
    at the harness rather than at the product.

    Cleanup must not be able to fail a run. Escalate TERM -> KILL, wait
    generously, and swallow anything that is still wrong, because a browser
    that will not die is worth a warning and not worth a red build.
    """
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception:  # pragma: no cover - defensive
        return
    try:
        process.kill()
        process.wait(timeout=timeout)
    except Exception:  # pragma: no cover - the process is already gone or unkillable
        print(f"warning: could not reap {label}", file=sys.stderr)


def _launch_chrome(profile: Path, log, attempts: int = 3, timeout: float = 30.0):
    """Start Chrome and wait for its DevTools endpoint, retrying on failure.

    Chrome intermittently fails to bring the endpoint up on a shared CI
    runner — the observed symptom is a dbus parse error followed by
    "Chrome DevTools endpoint did not start" 30 seconds later. The job passed
    on the next run with byte-identical code, which makes it an environment
    flake rather than a product fault.

    A gate that fails at random is not a gate; it is a coin flip that people
    learn to re-run. One retry costs a few seconds and turns a known flake
    into a non-event, and the escalation to three attempts keeps a genuinely
    broken browser broken rather than papering over it.
    """
    command = [
        _chrome(), "--headless=new", "--disable-gpu", "--disable-dev-shm-usage",
        "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0",
        "--user-data-dir=" + str(profile), "about:blank",
    ]
    last = None
    for attempt in range(1, attempts + 1):
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=log, text=True)
        try:
            return process, _devtools_port(process, profile, log=log, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - any launch failure is retryable
            last = exc
            _stop_process(process, "chrome (failed launch)")
            log.write(f"\n--- chrome launch attempt {attempt} failed: {exc}\n")
            log.flush()
            if attempt < attempts:
                time.sleep(2.0)
    raise RuntimeError(f"chrome did not expose DevTools after {attempts} attempts: {last}")


@contextmanager
def _browser_workspace():
    directory = tempfile.TemporaryDirectory(prefix="skillsmgr-browser-")
    try:
        yield directory.name
    finally:
        # A Chrome descendant can finish writing its private profile just
        # after the parent exits. Retry only transient directory races.
        for attempt in range(6):
            try:
                directory.cleanup()
                break
            except OSError as exc:
                if exc.errno not in {errno.ENOTEMPTY, errno.EEXIST} or attempt == 5:
                    raise
                time.sleep(0.1 * (attempt + 1))


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-profile", action="store_true")
    parser.add_argument(
        "--screenshots-dir",
        type=Path,
        help="also save one PNG per viewport in this developer-selected directory",
    )
    args = parser.parse_args()
    screenshot_dir = None
    if args.screenshots_dir is not None:
        screenshot_dir = args.screenshots_dir.expanduser().resolve()
        screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(screenshot_dir, 0o700)
    with _browser_workspace() as directory:
        root = Path(directory)
        home = root / "home"
        data_dir = root / "data"
        home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(home)
        os.environ["XDG_DATA_HOME"] = str(home / ".local" / "share")
        os.environ["JACKFIELD_DATA"] = os.environ["SKILLS_MANAGER_DATA"] = str(data_dir)
        store = Store(data_dir)
        store.init_db()
        store.create("browser-probe", "A browser harness fixture skill", body="# Browser probe\n\nA healthy active fixture.\n")
        store.create("disabled-probe", "A disabled fixture skill")
        store.disable("disabled-probe")
        store.create("recoverable-probe", "A recoverable fixture skill")
        store.remove("recoverable-probe")
        store.create("long-context-skill-name-for-responsive-proof", "A deliberately long description that checks wrapping and reflow without hiding the action text on narrow screens.", body="# Long context\n\nThis fixture keeps the overview and Library honest at narrow widths.\n")
        # Scope fixtures use the existing filesystem adapter so aggregate
        # observations exercise the same path as a real installation.
        from skillsmgr import scopes

        from skillsmgr.context import bound_store

        with bound_store(store):
            scopes.create_skill("agents", "browser-probe", "A divergent agent copy of the browser probe", body="# Browser probe\n\nDivergent copy.\n")
            scope = next((item for item in scopes.known_scopes() if item.id == "agents"), None)
        if scope:
            malformed = scope.base / "malformed-observed"
            malformed.mkdir(parents=True, exist_ok=True)
            (malformed / "SKILL.md").write_text("---\nname: [broken\n---\n", encoding="utf-8")
            unaddressable = scope.base / "not addressable"
            unaddressable.mkdir(parents=True, exist_ok=True)
            (unaddressable / "SKILL.md").write_text("---\nname: not-addressable\ndescription: observed\n---\n", encoding="utf-8")
        server = WebAppServer(store, port=0)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        profile = Path(directory) / "chrome"
        # Chrome's stderr is captured rather than discarded.  When the browser
        # cannot start, "Chrome exited before DevTools became available" on its
        # own does not say why -- and this job had been skipped long enough that
        # its first real execution failed without a diagnosable cause.  The
        # sandbox stays enabled (SEC-15); only the reporting changes.
        chrome_log = open(Path(directory) / "chrome.stderr.log", "w+", encoding="utf-8")
        chrome, port = _launch_chrome(profile, chrome_log)
        try:
            results = [
                _run_probe(
                    server.url,
                    width,
                    height,
                    port,
                    screenshot_dir / f"viewport-{width}x{height}.png" if screenshot_dir else None,
                )
                for width, height in VIEWPORTS
            ]
            scenario_results = {
                scenario: _run_probe(server.url, 1280, 900, port, scenario=scenario)
                for scenario in ("scope-failure", "inventory-failure", "unavailable-root")
            }

            # Repoint HOME and the manager data directory to a separate empty
            # fixture so the empty-state browser path is observed end to end.
            empty_home = root / "empty-home"
            empty_data = root / "empty-data"
            empty_home.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(empty_home)
            os.environ["XDG_DATA_HOME"] = str(empty_home / ".local" / "share")
            os.environ["JACKFIELD_DATA"] = os.environ["SKILLS_MANAGER_DATA"] = str(empty_data)
            empty_store = Store(empty_data)
            empty_store.init_db()
            empty_server = WebAppServer(empty_store, port=0)
            empty_thread = Thread(target=empty_server.serve_forever, daemon=True)
            empty_thread.start()
            try:
                scenario_results["empty"] = _run_probe(
                    empty_server.url, 1280, 900, port, scenario="empty"
                )
            finally:
                empty_server.shutdown()
                empty_thread.join(timeout=5)

            all_results = [*results, *scenario_results.values()]
            failures = [r for r in all_results if r["errors"] or r["failed"] or r["document"]["overflow"]]
            print(json.dumps({"viewports": results, "scenarios": scenario_results, "passed": not failures}, indent=2))
            return 1 if failures else 0
        finally:
            _stop_process(chrome, "chrome")
            chrome_log.close()
            server.shutdown()
            server_thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(run())
