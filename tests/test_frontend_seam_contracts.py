"""Frontend seam contracts: one source of truth per policy (docs/24 C2/G6).

``domain.js`` is the one owner of transport (``api``, request coalescing,
non-JSON transfers) and of the observed-state vocabulary. The interface loads
it before its own scripts and calls only what it exports.

Every check here runs the *checked-in* sources under Node, so it fails when the
sources drift rather than when a mock is out of date. Structural assertions are
made on parsed structure (key sets, call graphs, tag trees), never on
substring presence in rendered output.
"""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOMAIN_JS = ROOT / "skillsmgr" / "webui" / "domain.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _node(script: str) -> dict:
    """Run a Node script against the real sources and return parsed JSON."""
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True, encoding="utf-8", check=True, cwd=str(ROOT),
    )
    return json.loads(result.stdout)


class DomainSeamOwnershipTests(unittest.TestCase):
    """C2: transport and state policy belong to the domain seam, not the app."""

    def test_shell_registration_and_transports_load_in_dependency_order(self):
        webui = DOMAIN_JS.parent
        scripts = re.findall(r'<script src="([^"]+)"', _read(webui / "index.html"))
        seams = ("domain.js", "model.js", "state.js", "router.js", "ui-core.js",
                 "ui-table.js", "ui-doc.js", "screen-not-found.js", "screen-skills.js", "screen-attention.js",
                 "screen-trash.js", "screen-advanced.js", "palette.js", "app.js")
        self.assertEqual([name for name in scripts if name in seams], list(seams))
        for name in seams[2:]:
            source = _read(webui / name)
            self.assertNotRegex(source, r"\bfetch\s*\(", name)
            if name != "router.js":
                self.assertNotIn("location.hash", source, name)

    def test_domain_seam_exposes_the_transport_and_the_state_policy(self):
        exported = re.search(
            r"window\.SkillManagerDomain = Object\.freeze\(\{(.*?)\}\);",
            _read(DOMAIN_JS), re.S,
        )
        self.assertIsNotNone(exported, "domain seam export block not found")
        names = set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*,", exported.group(1), re.M))
        for required in ("api", "apiText", "apiBlob", "observeRecord",
                         "observedStateFor", "observedStateKeys", "OBSERVED_STATE_LABELS"):
            self.assertIn(required, names, f"{required} missing from the frozen seam")


class SingleStateVocabularyTests(unittest.TestCase):
    """C2: one classification, reachable from every surface that names a state."""

    #: Every state key the shared predicate can return, and the label each must
    #: have. A key with no label renders as a bare identifier in the UI.
    EXPECTED_LABELS = {
        "active": "Active", "disabled": "Disabled", "invalid": "Invalid",
        "malformed": "Malformed", "linked": "Linked outside root",
        "unaddressable": "Unaddressable", "divergent": "Divergent",
    }

    def test_every_state_the_backend_emits_has_a_label(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = { window: {}, document: {} };
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
console.log(JSON.stringify(sandbox.window.SkillManagerDomain.OBSERVED_STATE_LABELS));
"""
        labels = _node(script)
        self.assertEqual(labels, self.EXPECTED_LABELS)

    def test_invalid_is_reported_rather_than_silently_absent(self):
        """The backend's own vocabulary includes `invalid`.

        Before this change the app recognised `invalid` while the domain label
        map did not, so a state present in one surface could be missing from the
        other. Both must now name it.
        """
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = { window: {}, document: {} };
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const D = sandbox.window.SkillManagerDomain;
console.log(JSON.stringify({
  key: D.observedStateFor({instance_states: ['invalid']}),
  label: D.OBSERVED_STATE_LABELS[D.observedStateFor({instance_states: ['invalid']})],
  badgeKeys: D.observedStateKeys({instance_states: ['invalid']}),
}));
"""
        out = _node(script)
        self.assertEqual(out["key"], "invalid")
        self.assertEqual(out["label"], "Invalid")


    def test_quality_summary_buckets_stay_disjoint_and_total(self):
        """Every record lands in exactly one bucket — no silent disappearance."""
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = { window: {}, document: {} };
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const D = sandbox.window.SkillManagerDomain;
const records = [
  {name:'a'}, {name:'b', disabled:true}, {name:'c', malformed:true},
  {name:'d', instance_states:['invalid']}, {name:'e', addressable:false},
  {name:'f', instance_states:['unaddressable']}, {name:'g', decode_error:'x'},
];
const buckets = {};
for (const r of records) {
  const state = D.observedStateFor(r);
  buckets[state] = (buckets[state] || 0) + 1;
}
console.log(JSON.stringify({buckets, total: records.length}));
"""
        out = _node(script)
        self.assertEqual(sum(out["buckets"].values()), out["total"])
        self.assertEqual(out["buckets"].get("invalid"), 1)
        self.assertEqual(out["buckets"].get("malformed"), 2)   # flag + decode_error
        self.assertEqual(out["buckets"].get("unaddressable"), 2)
        self.assertEqual(out["buckets"].get("disabled"), 1)
        self.assertEqual(out["buckets"].get("active"), 1)



class RequestCoalescingTests(unittest.TestCase):
    """G6: identical in-flight reads fan in; completed reads are never cached."""

    def test_identical_concurrent_gets_share_one_request(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
let calls = 0;
const sandbox = {
  window: {},
  document: {},
  fetch: async () => { calls += 1; return {ok:true, status:200, headers:{get:()=>'application/json'}, json: async()=>({v: calls})}; },
  setTimeout, clearTimeout,
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const api = sandbox.window.SkillManagerDomain.api;
(async () => {
  const [a, b, c] = await Promise.all([api('/api/skills?scope=all'), api('/api/skills?scope=all'), api('/api/skills?scope=all')]);
  const afterFanIn = calls;
  // A later read must re-read: the filesystem stays the source of truth.
  const d = await api('/api/skills?scope=all');
  console.log(JSON.stringify({afterFanIn, afterSequential: calls, sameObject: a === b && b === c, laterValue: d.v}));
})();
"""
        out = _node(script)
        self.assertEqual(out["afterFanIn"], 1, "concurrent identical GETs were not coalesced")
        self.assertEqual(out["afterSequential"], 2, "a completed read must not be cached")
        self.assertTrue(out["sameObject"])

    def test_different_urls_are_not_coalesced(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
let calls = 0;
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout,
  fetch: async () => { calls += 1; return {ok:true, status:200, headers:{get:()=>'application/json'}, json: async()=>({v:calls})}; }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const api = sandbox.window.SkillManagerDomain.api;
(async () => {
  await Promise.all([api('/api/skills?scope=all'), api('/api/skills?scope=agents'), api('/api/trash')]);
  console.log(JSON.stringify({calls}));
})();
"""
        self.assertEqual(_node(script)["calls"], 3)

    def test_mutations_are_never_coalesced(self):
        """Two POSTs are two mutations; sharing one would drop an operation."""
        script = r"""
const fs = require('fs'), vm = require('vm');
let calls = 0;
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout,
  fetch: async () => { calls += 1; return {ok:true, status:200, headers:{get:()=>'application/json'}, json: async()=>({v:calls})}; }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const api = sandbox.window.SkillManagerDomain.api;
(async () => {
  const opts = {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'};
  await Promise.all([api('/api/skills/x/disable', opts), api('/api/skills/x/disable', opts)]);
  console.log(JSON.stringify({calls}));
})();
"""
        self.assertEqual(_node(script)["calls"], 2)

    def test_a_failed_read_is_not_left_in_the_in_flight_table(self):
        """A rejected read must not poison the next attempt."""
        script = r"""
const fs = require('fs'), vm = require('vm');
let calls = 0;
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout,
  fetch: async () => { calls += 1; const n = calls;
    return {ok:false, status:500, headers:{get:()=>'application/json'}, json: async()=>({error:'boom '+n})}; }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const api = sandbox.window.SkillManagerDomain.api;
(async () => {
  const errs = [];
  for (let i = 0; i < 2; i += 1) {
    try { await api('/api/skills?scope=all'); } catch (e) { errs.push(e.message); }
  }
  console.log(JSON.stringify({calls, errs}));
})();
"""
        out = _node(script)
        self.assertEqual(out["calls"], 2, "the failed read was cached and reused")
        self.assertEqual(out["errs"], ["boom 1", "boom 2"])



class TransportSeamBehaviourTests(unittest.TestCase):
    """The non-JSON transfers keep the seam's error contract."""

    def test_api_text_returns_the_body_and_throws_the_status(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
let status = 200;
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout,
  fetch: async () => ({ok: status < 400, status, headers:{get:()=>'text/plain'}, text: async()=> 'raw body'})};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const apiText = sandbox.window.SkillManagerDomain.apiText;
(async () => {
  const ok = await apiText('/api/skills/x/raw');
  let err = null;
  status = 503;
  try { await apiText('/api/skills/x/raw'); } catch (e) { err = e.message; }
  console.log(JSON.stringify({ok, err}));
})();
"""
        out = _node(script)
        self.assertEqual(out["ok"], "raw body")
        self.assertEqual(out["err"], "HTTP 503")

    def test_api_blob_carries_the_server_filename(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout,
  fetch: async () => ({ok:true, status:200, headers:{get:(h)=> h === 'Content-Disposition' ? 'attachment; filename="export.tar.gz"' : null}, blob: async()=>({bytes:7})})};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
sandbox.window.SkillManagerDomain.apiBlob('/api/export').then(r => console.log(JSON.stringify(r)));
"""
        out = _node(script)
        self.assertEqual(out["filename"], "export.tar.gz")
        self.assertEqual(out["blob"], {"bytes": 7})

    def test_api_blob_falls_back_when_no_disposition_is_sent(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout,
  fetch: async () => ({ok:true, status:200, headers:{get:()=>null}, blob: async()=>({bytes:1})})};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
sandbox.window.SkillManagerDomain.apiBlob('/api/export').then(r => console.log(JSON.stringify(r)));
"""
        self.assertEqual(_node(script)["filename"], "")

    def test_backup_download_errors_keep_the_coded_retry_message_and_ignore_malformed_json(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
let broken = false;
const sandbox = {window:{}, document:{}, setTimeout, clearTimeout, fetch: async () => ({
  ok:false, status:409, headers:{get:()=>'application/json'},
  json: async()=>{ if (broken) throw new SyntaxError('not JSON'); return {code:'backup_source_changed',error:'/private/path'}; },
  blob: async()=>{ throw new Error('error response must not be read as a file'); },
})};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const domain = sandbox.window.SkillManagerDomain;
async function failure() {
  try { await domain.apiBlob('/api/export'); }
  catch (error) { return [error.message, domain.archiveDownloadError(error)]; }
}
(async () => {
  const conflict = await failure();
  broken = true;
  console.log(JSON.stringify({conflict, malformed:await failure()}));
})();
"""
        result = _node(script)
        self.assertEqual(result["conflict"][0], "HTTP 409")
        self.assertIn("Wait for changes to finish", result["conflict"][1])
        self.assertNotIn("/private/path", result["conflict"][1])
        self.assertEqual(result["malformed"], ["HTTP 409", "The backup could not be downloaded."])



class MarkdownEscapingStillHoldsTests(unittest.TestCase):
    """The refactor must not weaken docs/08 locked rule 4."""

    def test_rendered_markdown_still_emits_only_its_own_tags(self):
        payloads = [
            "<script>alert(1)</script>",
            '<img src=x onerror="alert(1)">',
            "[x](javascript://alert(1))",
            "| a | b |\n|---|---|\n| <script>alert(1)</script> | x |",
            "**<svg/onload=alert(1)>**",
        ]
        script = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/static/vendor/markdown-it.umd.min.js', 'utf8'), sandbox);
vm.runInNewContext(fs.readFileSync('skillsmgr/webui/domain.js', 'utf8'), sandbox);
const render = sandbox.window.SkillManagerDomain.renderMarkdown;
console.log(JSON.stringify(JSON.parse(process.argv[1]).map(payload => render(payload))));
"""
        rendered = json.loads(subprocess.run(
            ["node", "-e", script, json.dumps(payloads)],
            capture_output=True, encoding="utf-8", check=True, cwd=str(ROOT),
        ).stdout)
        for payload, html in zip(payloads, rendered):
            with self.subTest(payload=payload):
                tags = set(re.findall(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)", html))
                self.assertLessEqual(tags, {"p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
                                            "ul", "ol", "li", "blockquote", "pre", "code",
                                            "a", "table", "thead", "tbody", "tr", "th", "td",
                                            "strong", "em", "hr", "div"}, tags)
                for match in re.finditer(r"<([a-zA-Z][^>]*)>", html):
                    self.assertNotRegex(match.group(1), r"\son[a-z]+\s*=")
                    self.assertNotIn("javascript:", match.group(1).lower())


if __name__ == "__main__":
    unittest.main()
