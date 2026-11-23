"""AI Center keeps its buttons disabled until every request finishes (2026-11-19).

A single ``busy`` boolean was cleared by whichever guarded request finished
first, re-enabling paid model calls while another request was still running.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "skillsmgr" / "webui"

SCRIPT = r"""
const fs=require('fs'),vm=require('vm');
const ctx={window:{SkillManagerDomain:{api:async()=>({})}},console};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const c=ctx.window.SkillsV2AiCenter;
const h=Object.assign(c.data(),{});
for(const [n,f] of Object.entries(c.methods))h[n]=f.bind(h);
(async()=>{
  const seen=[];let releaseA,releaseB;
  const a=h.guard(()=>new Promise(r=>releaseA=r));
  const b=h.guard(()=>new Promise(r=>releaseB=r));
  seen.push(h.busy);
  releaseA('a');await a;seen.push(h.busy);
  releaseB('b');await b;seen.push(h.busy);
  console.log(JSON.stringify(seen));
})();
"""


@unittest.skipUnless(shutil.which("node"), "node is required for frontend behaviour tests")
class AiCenterBusyTests(unittest.TestCase):
    def test_busy_stays_true_until_every_guarded_request_finishes(self):
        out = subprocess.run(["node", "-e", SCRIPT, str(V2 / "ai-center.js")],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), [True, True, False])


if __name__ == "__main__":
    unittest.main()
