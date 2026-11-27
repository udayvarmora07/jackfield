"""Shared frontend contracts: the domain seam, preferences bootstrap, the
Markdown renderer and the browser harness helpers.

Stdlib unittest only, no browser: each check reads the checked-in
``skillsmgr/webui`` sources. Interface behaviour is pinned in
``test_v2_interface_contracts`` and ``test_v2_tool_behaviors``.
"""

from __future__ import annotations

import re
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEBUI = ROOT / "skillsmgr" / "webui"
INDEX_HTML = ROOT / "skillsmgr" / "webui" / "index.html"
DOMAIN_JS = ROOT / "skillsmgr" / "webui" / "domain.js"
PREFERENCES_JS = ROOT / "skillsmgr" / "webui" / "preferences.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class FrontendSourceContractTests(unittest.TestCase):

    def test_chrome_launch_retries_before_giving_up(self):
        """A flaky runner must not turn this job into a coin flip.

        Chrome intermittently fails to expose its DevTools endpoint on a shared
        CI runner — dbus parse error, then "endpoint did not start" 30 seconds
        later. On 2026-10-08 the `browser smoke` job failed that way on
        `cd41db4` and passed on the identical tree one commit later. A gate
        that fails at random is not a gate.

        Driven for real against a browser that cannot exist, so the retry count
        is observed rather than read.
        """
        import importlib.util
        import io
        import subprocess
        import sys

        spec = importlib.util.spec_from_file_location(
            "browser_harness_launch", ROOT / "browser_harness.py"
        )
        harness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(harness)

        attempts = []
        real_popen = subprocess.Popen

        class _ImmediateExit(real_popen):  # type: ignore[misc]
            def __init__(self, cmd, *a, **kw):
                attempts.append(cmd)
                super().__init__([sys.executable, "-c", "raise SystemExit(3)"],
                                 *a, **kw)

        def fake_popen(cmd, *a, **kw):
            attempts.append(cmd)
            proc = real_popen([sys.executable, "-c", "raise SystemExit(3)"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc

        real_time = harness.time.sleep
        real_chrome = harness._chrome
        harness.subprocess.Popen = fake_popen
        harness.time.sleep = lambda *_: None
        # Resolving Chrome is not what this test is about; without a stub it
        # raised before the first launch on any machine without Chrome.
        harness._chrome = lambda: "/nonexistent/chrome"
        try:
            with self.assertRaises(RuntimeError):
                harness._launch_chrome(
                    ROOT / "profile-does-not-matter", io.StringIO(), attempts=3
                )
        finally:
            harness.subprocess.Popen = real_popen
            harness.time.sleep = real_time
            harness._chrome = real_chrome
        self.assertEqual(len(attempts), 3,
                         "a browser that cannot start must be retried, not "
                         "reported as a product failure on the first attempt")

    def test_harness_cleanup_cannot_fail_a_run(self):
        """A child that ignores SIGTERM must not turn a passing run red.

        The harness reaped Chrome with `chrome.terminate(); chrome.wait(timeout=5)`
        inside its `finally`. On a busy shared runner Chrome routinely needs
        longer than five seconds to exit after SIGTERM, `Popen.wait` raises
        `TimeoutExpired` when it does, and a raise from a cleanup path replaces
        the real result. The 2026-10-06 `browser smoke` job failed that way on
        a tree whose probes had all passed, and the traceback pointed at the
        harness rather than at the product.

        Exercised for real, against a child that deliberately ignores SIGTERM.
        """
        import importlib.util
        import subprocess
        import sys

        spec = importlib.util.spec_from_file_location(
            "browser_harness", ROOT / "browser_harness.py"
        )
        harness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(harness)

        # `signal.signal(SIGTERM, SIG_IGN)` makes the child deaf to terminate(),
        # which is exactly the condition that used to raise.
        script = (
            "import signal, sys, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "print('ready', flush=True); "
            "time.sleep(120)"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", script], stdout=subprocess.PIPE, text=True
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            # Must not raise, and must leave nothing running.
            harness._stop_process(child, "stubborn-child", timeout=1.0)
            self.assertIsNotNone(child.poll(), "child survived cleanup")
            # An already-dead child is a no-op, not an error.
            harness._stop_process(child, "already-dead", timeout=1.0)
        finally:
            if child.poll() is None:  # pragma: no cover - only on failure
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()

    def test_browser_workspace_retries_a_profile_cleanup_race(self):
        import errno
        from unittest import mock
        import browser_harness as harness

        original_cleanup = harness.tempfile.TemporaryDirectory.cleanup
        errors = [OSError(errno.ENOTEMPTY, "profile write raced with cleanup")]

        def cleanup(directory):
            if errors:
                raise errors.pop()
            return original_cleanup(directory)

        with mock.patch.object(harness.tempfile.TemporaryDirectory, "cleanup", cleanup):
            with harness._browser_workspace() as directory:
                self.assertTrue(Path(directory).is_dir())
        self.assertFalse(Path(directory).exists())
        self.assertEqual(errors, [])

    def test_browser_harness_is_hermetic_and_waits_for_a_stable_first_render(self):
        source = _read(ROOT / "browser_harness.py")
        self.assertIn('os.environ["HOME"]', source)
        self.assertIn('os.environ["SKILLS_MANAGER_DATA"]', source)
        self.assertIn("stableChecks", source)
        self.assertIn("1440, 900", source)
        self.assertIn("malformed-observed", source)
        self.assertIn("recoverable-probe", source)
        self.assertIn("first_useful_ms", source)
        self.assertIn('scenario="empty"', source)
        self.assertIn('("scope-failure", "inventory-failure", "unavailable-root")', source)
        self.assertIn("Unavailable fixture", source)
        # The probe drives the interface served at /, never a retired address.
        self.assertNotIn("classic/", source)
        self.assertIn("#command-q", source)
        self.assertIn("#command-list", source)
        self.assertIn("#/advanced/quality", source)


    def test_domain_format_compat_handles_arrays_before_objects(self):
        source = _read(DOMAIN_JS)
        array_branch = 'if (Array.isArray(v)) return v.join(", ");'
        object_branch = 'if (typeof v === "object") return Object.entries(v)'
        self.assertIn(array_branch, source)
        self.assertLess(source.index(array_branch), source.index(object_branch))


    def test_preference_bootstrap_resolves_saved_values_before_stylesheet(self):
        source = _read(PREFERENCES_JS) if PREFERENCES_JS.exists() else ""
        html = _read(INDEX_HTML)
        self.assertTrue(source, "preference bootstrap must exist")
        self.assertIn('<script src="preferences.js"></script>', html)
        self.assertLess(html.index('<script src="preferences.js"></script>'), html.index('<link rel="stylesheet" href="styles.css">'))
        self.assertIn('skillsmgr-theme', source)
        self.assertIn('skillsmgr-text-size', source)
        self.assertIn('(prefers-color-scheme: dark)', source)
        script = r'''
const fs = require('fs'), vm = require('vm');
function run(savedTheme, savedSize, matches, fail) {
  const root = {dataset:{}};
  const sandbox = {document:{documentElement:root}, window:{localStorage:{getItem(key){if (fail) throw new Error('storage'); return key === 'skillsmgr-theme' ? savedTheme : savedSize;}}, matchMedia(){if (fail) throw new Error('media'); return {matches};}}};
  vm.runInNewContext(fs.readFileSync('skillsmgr/webui/preferences.js', 'utf8'), sandbox);
  return root.dataset;
}
console.log(JSON.stringify([run('dark','large',false,false), run('system','bad',true,false), run('invalid','invalid',true,true)]));
'''
        result = subprocess.run(["node", "-e", script], capture_output=True, encoding="utf-8", check=True)
        values = json.loads(result.stdout)
        self.assertEqual(values[0], {"themePreference": "dark", "theme": "dark", "textSize": "large"})
        self.assertEqual(values[1], {"themePreference": "system", "theme": "dark", "textSize": "standard"})
        self.assertEqual(values[2], {"themePreference": "system", "theme": "light", "textSize": "standard"})


    def test_logical_library_groups_aliases_but_keeps_divergence(self):
        script = """
const fs = require('fs'), vm = require('vm');
const sandbox = {window: {}};
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const rows = [
  {name:'alpha', scope:'global', scope_label:'Global', physical_path:'/root/alpha', content_hash:'same'},
  {name:'alpha', scope:'agents', scope_label:'Agents', physical_path:'/root/alpha', content_hash:'same'},
  {name:'alpha', scope:'claude-code', scope_label:'Claude Code', physical_path:'/claude/alpha', content_hash:'different'}
];
console.log(JSON.stringify(sandbox.window.SkillManagerDomain.groupLogicalSkills(rows)));
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, encoding="utf-8", check=True)
        groups = json.loads(result.stdout)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["instanceCount"], 2)
        self.assertTrue(groups[0]["divergent"])
        self.assertEqual(len(groups[0]["badges"]), 2)
        self.assertIn("groupLogicalSkills", _read(DOMAIN_JS))

    def test_domain_identity_keeps_alias_consumers_and_observed_states(self):
        script = """
const fs = require('fs'), vm = require('vm');
const sandbox = {window: {}};
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const scopes = [
  {id:'global', label:'Global', kind:'global', consumer:'skills-manager'},
  {id:'agents', label:'Agents', kind:'agent', consumer:'shared-agent-skills'},
  {id:'project-agents', label:'Project .agents', kind:'project', consumer:'shared-agent-skills'},
  {id:'mystery', label:'Mystery', kind:'agent', consumer:null}
];
const rows = [
  {name:'alpha', scope:'global', scope_label:'Global', consumer:'skills-manager', physical_path:'/same/alpha', content_hash:'a'},
  {name:'alpha', scope:'agents', scope_label:'Agents', consumer:'shared-agent-skills', physical_path:'/same/alpha', content_hash:'b', disabled:true},
  {name:'alpha', scope:'project-agents', scope_label:'Project .agents', consumer:'shared-agent-skills', physical_path:'/project/alpha', content_hash:'c'},
  {name:'mystery', scope:'mystery', scope_label:'Mystery', consumer:null, addressable:false}
];
console.log(JSON.stringify(sandbox.window.SkillManagerDomain.groupLogicalSkills(rows, scopes)));
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, encoding="utf-8", check=True)
        groups = json.loads(result.stdout)
        alpha = groups[0]
        labels = [item["label"] for item in alpha["identities"]]
        self.assertTrue(any("Global" in label and "skills-manager" in label for label in labels))
        self.assertTrue(any("Agents agent" in label and "shared-agent-skills" in label for label in labels))
        self.assertTrue(any("Project .agents workspace" in label for label in labels))
        self.assertIn("Divergent", " ".join(item["stateLabel"] for item in alpha["identities"]))
        mystery = groups[1]
        self.assertIn("Unknown consumer", mystery["identities"][0]["label"])
        self.assertEqual(mystery["identities"][0]["stateLabel"], "Unaddressable")
        self.assertEqual(alpha["instanceCount"], 2, "alias rows still collapse to exact physical instances")


class MarkdownRendererEscapingTests(unittest.TestCase):
    """A7: execute the real renderer instead of trusting it by inspection.

    ``renderMarkdown`` renders attacker-authored ``SKILL.md`` bodies and is the
    single function that makes docs/08-web-ui.md locked rule 4 ("frontend never
    renders raw HTML") true.  Every other frontend test stubbed it out as a
    no-op, so a regression here would have failed nothing.  These tests load the
    checked-in ``domain.js`` into a Node ``vm`` and run real payloads through it.
    """

    #: Payloads that must never survive as live HTML. The link payloads use a
    #: scheme *with* ``//`` on purpose: the renderer's pattern requires it, so a
    #: bare ``javascript:alert(1)`` would never match and would prove nothing.
    PAYLOADS = [
        "<script>alert(1)</script>",
        '<img src=x onerror="alert(1)">',
        "<svg/onload=alert(1)>",
        "<iframe src=javascript:alert(1)></iframe>",
        "[click](javascript://alert(1))",
        "[x](JavaScript://alert(1))",
        "[x](data://text/html,<script>alert(1)</script>)",
        "[x](vbscript://msgbox(1))",
        "[x](file:///etc/passwd)",
        '<a href="#" onclick="alert(1)">x</a>',
        "<div onmouseover=alert(1)>hover</div>",
        "` <script>alert(1)</script> `",
        "**<img src=x onerror=alert(1)>**",
        "| a | b |\n|---|---|\n| <script>alert(1)</script> | x |",
        "> <script>alert(1)</script>",
        "- <script>alert(1)</script>",
        "\x00<script>alert(1)</script>",
        "[ok](https://example.com) and [no](javascript://x)",
    ]

    #: Every tag the renderer is allowed to emit. `div` is used for the table
    #: wrapper; the rest is block/inline Markdown.
    ALLOWED_TAGS = {
        "p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol",
        "li", "blockquote", "pre", "code", "a", "table", "thead",
        "tbody", "tr", "th", "td", "strong", "em", "hr", "div",
    }

    def test_rendered_markdown_never_contains_a_live_html_sink(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/static/vendor/markdown-it.umd.min.js', 'utf8'), sandbox);
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const render = sandbox.window.SkillManagerDomain.renderMarkdown;
const payloads = JSON.parse(process.argv[1]);
console.log(JSON.stringify(payloads.map(payload => render(payload))));
"""
        result = subprocess.run(
            ["node", "-e", script, json.dumps(self.PAYLOADS)],
            capture_output=True, encoding="utf-8", check=True, cwd=str(ROOT),
        )
        rendered = json.loads(result.stdout)
        self.assertEqual(len(rendered), len(self.PAYLOADS))

        for payload, html in zip(self.PAYLOADS, rendered):
            with self.subTest(payload=payload):
                # The invariant that matters: every '<' the renderer emits opens
                # one of its own known-safe tags. Escaped attacker text contains
                # no '<' at all, so it cannot appear here.
                tags = re.findall(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)", html)
                self.assertTrue(
                    set(tags) <= self.ALLOWED_TAGS,
                    f"unexpected tags {set(tags) - self.ALLOWED_TAGS} in {html!r}",
                )
                # No emitted tag may carry an event-handler attribute...
                for match in re.finditer(r"<([a-zA-Z][^>]*)>", html):
                    attributes = match.group(1)
                    self.assertNotRegex(
                        attributes, r"\son[a-z]+\s*=",
                        f"event handler survived in {attributes!r}",
                    )
                    self.assertNotIn(
                        "javascript:", attributes.lower(),
                        f"javascript: URL survived in {attributes!r}",
                    )
                # ...and no dangerous element name appears at all.
                lowered = html.lower()
                for element in ("<script", "<img", "<svg", "<iframe", "<object"):
                    self.assertNotIn(element, lowered)
                # Any attribute value the renderer emits is a fixed literal.
                for href in re.findall(r'href="([^"]*)"', html):
                    self.assertTrue(
                        href.startswith("https://") or href.startswith("http://"),
                        f"non-http link target survived: {href!r}",
                    )

    def test_escaped_payloads_stay_visible_as_text(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/static/vendor/markdown-it.umd.min.js', 'utf8'), sandbox);
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
console.log(JSON.stringify(sandbox.window.SkillManagerDomain.renderMarkdown(
  '<script>alert(1)</script>')));
"""
        result = subprocess.run(
            ["node", "-e", script], capture_output=True, encoding="utf-8", check=True,
            cwd=str(ROOT),
        )
        html = json.loads(result.stdout)
        # Escaped, not stripped: the reader still sees the text, inert.
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script", html.lower())

    def test_the_renderer_is_the_only_html_sink_and_is_reachable(self):
        """Pin the export list so a new raw-HTML sink becomes visible."""
        source = _read(DOMAIN_JS)
        # No raw HTML injection anywhere in the shipped frontend.
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML",
                     "document.write", "eval(", "new Function("):
            with self.subTest(sink=sink):
                for path in sorted(WEBUI.glob("*.js")) + [INDEX_HTML]:
                    self.assertNotIn(sink, _read(path), f"{sink} in {path.name}")
        # The closed set of v-html bindings is pinned by
        # test_v2_interface_contracts.test_html_is_injected_only_from_the_escaped_renderer_or_constant_icons.
        self.assertIn("renderMarkdown", source)
        self.assertIn("renderMarkdown,", source)   # exported on the frozen seam


if __name__ == "__main__":
    unittest.main()
