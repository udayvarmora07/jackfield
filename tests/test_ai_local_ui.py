"""Local scans and the optional model preview reject stale UI responses."""
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let calls=[],resolve;
const ctx={sessionStorage:{getItem:()=>null,removeItem:()=>{}},window:{SkillManagerDomain:{api:(url,opts)=>{calls.push(JSON.parse(opts.body));return new Promise(r=>resolve=r);}}},console};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const c=ctx.window.SkillsV2AiCenter,h=Object.assign(c.data(),{page:'ai-port',scope:'codex',portName:'example',portTarget:'codex',configured:false});
for(const [n,f] of Object.entries(c.methods))h[n]=f.bind(h);
(async()=>{
 let ticks=[]; h.$nextTick=fn=>ticks.push(fn); h.target={scope:'claude-code',name:'handoff'}; h.takeHandoff(); h.portName=''; ticks.shift()(); assert.strictEqual(h.portName,'handoff'); h.scope='codex'; h.portName='example'; h.target=null;
 let p=h.port('local'); assert.strictEqual(calls[0].local_only,true);
 h.portTarget='gemini'; resolve({name:'example',target:'codex',facts:[{}]}); await p; assert.strictEqual(h.ported,null);
 p=h.port('local'); resolve({name:'example',target:'gemini',facts:[{}]}); await p; assert.ok(h.ported);
 await h.port('estimate'); assert.strictEqual(calls.length,2);
 h.configured=true; p=h.port('estimate'); assert.strictEqual(calls[2].estimate,true); assert.strictEqual(calls[2].reviewed,true);
 resolve({scope:'codex',name:'example',target:'gemini',run:{}}); await p; assert.ok(h.portEstimate);
 h.portTarget='codex'; await h.port('send'); assert.strictEqual(calls.length,3);
 h.page='ai-explain'; h.explainName='example'; p=h.explain('local'); assert.strictEqual(calls[3].local_only,true);
 h.page='ai-port'; h.clearExplain(); resolve({name:'example',findings:[]}); await p; assert.strictEqual(h.explained,null);
})().catch(e=>{console.error(e);process.exitCode=1});
"""

@unittest.skipUnless(shutil.which("node"), "node is required")
class LocalUiTests(unittest.TestCase):
    def test_local_and_stale_responses(self):
        path = Path(__file__).resolve().parent.parent / "skillsmgr/webui/ai-center.js"
        subprocess.run(["node", "-e", SCRIPT, str(path)], check=True, capture_output=True, text=True)
