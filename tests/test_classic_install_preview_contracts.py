"""Install preview and workspace contracts for the active interface."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from skillsmgr.store import Store
from skillsmgr.webapp import WebAppServer
from test_v2_tool_behaviors import run_node

ROOT = Path(__file__).resolve().parent.parent
TOOL_CENTER = ROOT / "skillsmgr" / "webui" / "tool-center.js"


@unittest.skipUnless(shutil.which("node"), "Node is required for frontend behavior checks")
class ActiveInstallPreviewTests(unittest.TestCase):
    def test_runner_requires_matching_preview_before_run(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{source:'owner/repo'});
          handler=async()=>({command:'npx skills add owner/repo -g'});
          await h.runRunner(true);const before=calls.length;
          await h.runRunner(false);const preview=h.runnerPreview;
          h.source='other/repo';await h.runRunner(true);const changed=calls.length;
          h.source='owner/repo';await h.runRunner(true);
          return {before,changed,calls:calls.map(c=>({url:c.url,body:JSON.parse(c.opts.body)})),preview,after:h.runnerPreview,busy:h.busy};
        """)
        self.assertEqual(out["before"], 0)
        self.assertEqual(out["changed"], 2)
        self.assertTrue(out["preview"])
        self.assertEqual([c["url"] for c in out["calls"]], ["/api/install", "/api/install", "/api/install"])
        self.assertFalse(out["calls"][0]["body"]["run"])
        self.assertTrue(out["calls"][1]["body"]["preview"])
        self.assertTrue(out["calls"][2]["body"]["run"])
        self.assertEqual(out["calls"][0]["body"]["source"], "owner/repo")
        self.assertEqual(out["after"], "")
        self.assertFalse(out["busy"])

    def test_failed_preview_never_authorizes_run(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{source:'owner/repo'});
          handler=async()=>{throw Error('network down')};
          await h.runRunner(false);await h.runRunner(true);
          return {count:calls.length,preview:h.runnerPreview,error:h.error,busy:h.busy};
        """)
        self.assertEqual(out, {"count": 1, "preview": "", "error": "network down", "busy": False})

    def test_bridge_evidence_is_separate_from_actual_command_and_optional(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{source:'owner/repo/skill',tab:'runner'});
          handler=async(_url,opts)=>JSON.parse(opts.body).preview
            ? {command:'different bridge command',registry:{may_install:false,eligibility_status:'unverified-offline',blockers:['unverified'],audit_links:[]}}
            : {command:'actual runner command'};
          await h.runRunner(false);const before={command:h.result.command,plan:h.runnerPlan};
          handler=async(_url,opts)=>{if(JSON.parse(opts.body).preview)throw Error('unsupported');return {command:'general command'}};
          await h.runRunner(false);
          return {before,command:h.result.command,preview:!!h.runnerPreview,plan:h.runnerPlan,error:h.runnerPlanError};
        """)
        self.assertEqual(out['before']['command'], 'actual runner command')
        self.assertEqual(out['before']['plan']['blockers'], ['unverified'])
        self.assertFalse(out['before']['plan']['may_install'])
        self.assertEqual((out['command'],out['preview'],out['plan'],out['error']), ('general command',True,None,'unsupported'))

    def test_repreview_failure_clears_previous_authorization(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{source:'owner/repo',tab:'runner'});
          handler=async()=>({command:'command',registry:{blockers:['unverified'],may_install:false}});
          await h.runRunner(false);
          handler=async()=>{throw Error('failed again')};
          await h.runRunner(false);await h.runRunner(true);
          return {count:calls.length,preview:h.runnerPreview,error:h.error,result:h.result};
        """)
        self.assertEqual(out, {'count':3,'preview':'','error':'failed again','result':None})

    def test_tab_change_discards_pending_preview_and_audit_links_are_restricted(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{source:'owner/repo',tab:'runner'});
          let finish;handler=()=>new Promise(r=>finish=r);
          const pending=h.runRunner(false);h.switchInstallTab('registry');finish({command:'old'});
          await tick();finish({registry:{blockers:[]}});await pending;
          return {preview:h.runnerPreview,result:h.result,plan:h.runnerPlan,
            good:h.safeAuditLink({url:'https://skills.sh/a/b/c/security/socket'}),
            bad:['http://skills.sh/a/b/c/security/socket','https://evil.test/a/b/c/security/socket','https://skills.sh.evil.test/a/b/c/security/socket'].map(url=>h.safeAuditLink({url}))};
        """)
        self.assertEqual(out, {'preview':'','result':None,'plan':None,'good':True,'bad':[False,False,False]})

    def test_workspace_enter_does_not_duplicate_inflight_request(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'workspaces'});
          let finish;handler=()=>new Promise(r=>finish=r);
          const first=h.loadWorkspace();await h.loadWorkspace();finish({managed_roots:[]});await first;
          return {count:calls.length,workspace:h.workspace,loading:h.loading.workspace};
        """)
        self.assertEqual(out, {'count':1,'workspace':{'managed_roots':[]},'loading':False})

    def test_workspace_picker_submits_on_enter_and_guards_loading(self):
        source = TOOL_CENTER.read_text(encoding="utf-8")
        self.assertIn('<form class="tp-project card tp-panel" @submit.prevent="${action}">', source)
        self.assertIn("${projectPicker('loadWorkspace')}", source)
        self.assertIn(':disabled="loading.qualityEnvelope||loading.workspace"', source)


class InstallPreviewRouteTests(unittest.TestCase):
    """The backend preview contract remains available to API clients."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._saved = {k: os.environ.get(k) for k in ("SKILLS_MANAGER_DATA", "HOME")}
        self.addCleanup(self._restore)
        home = Path(self._tmp.name) / "home"
        home.mkdir(mode=0o700)
        os.environ["HOME"] = str(home)
        os.environ["SKILLS_MANAGER_DATA"] = str(Path(self._tmp.name) / "data")
        self.store = Store()
        self.store.init_db()
        self.server = WebAppServer(self.store, port=0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)

    def _restore(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def post(self, path, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.server.port}{path}",
            data=json.dumps(payload).encode(),
            headers={
                "Host": f"127.0.0.1:{self.server.port}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_preview_payload_returns_blockers_and_may_install(self):
        payload = {
            "source": "owner/repo",
            "runner": "npx",
            "scope": "global",
            "copy": False,
            "list_only": False,
            "preview": True,
        }
        status, data = self.post("/api/install", payload)
        self.assertEqual(status, 200)
        self.assertIs(data["executed"], False)
        self.assertIn("npx skills add owner/repo -g", data["command"])
        plan = data["registry"]
        self.assertIn("blockers", plan)
        self.assertIsInstance(plan["blockers"], list)
        self.assertIn("may_install", plan)
        self.assertIsInstance(plan["may_install"], bool)
        self.assertIn("audit_links", plan)
        self.assertIsInstance(plan["audit_links"], list)


if __name__ == "__main__":
    unittest.main()
