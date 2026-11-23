"""Configured-model previews must match the inputs that will be sent."""
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let calls=[], release;
const ctx={window:{SkillManagerDomain:{api:(url,opts)=>{calls.push({url,body:JSON.parse(opts.body)});return new Promise(r=>release=r);}}},console};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const c=ctx.window.SkillsV2AiCenter;
const h=Object.assign(c.data(),{settings:{provider:'stub',model:'fixture',base_url:'fixture'},scope:'codex',evalName:'one',improveName:'one',chosen:['one']});
for(const [n,f] of Object.entries(c.methods))h[n]=f.bind(h);
for(const [n,f] of Object.entries(c.computed))Object.defineProperty(h,n,{get:f.bind(h)});
h.load=()=>{};
h.records=[{scope:'codex',name:'valid'},{scope:'codex',name:'.system',addressable:false},{scope:'codex',name:'broken',malformed:true},{scope:'codex',name:'manual',frontmatter_extensions:{'disable-model-invocation':true}},{scope:'other',name:'elsewhere'},{scope:'codex',name:'valid'}];
assert.deepStrictEqual(Array.from(h.pickable),['valid']);
(async()=>{
 for(const [page,estimate,run,field,body,change] of [
  ['ai-trigger','estimateTrigger','runTrigger','estimate','triggerBody',()=>h.chosen.push('two')],
  ['ai-evals','estimateEvals','runEvals','evalEstimate','evalBody',()=>h.evalMax++],
  ['ai-budget','estimateBudget','runBudget','budgetEstimate','budgetBody',()=>h.budgetMax++],
  ['ai-overlap','estimateOverlap','runOverlap','overlapEstimate','overlapBody',()=>h.pairs.push(['one','two'])],
  ['ai-improve','estimateImprove','runImprove','improveEstimate','improveBody',()=>h.improveName=h.improveName==='one'?'two':'one'],
  ['ai-conflicts','estimateConflictJudge','runConflictJudge','conflictsEstimate','conflictEstimateBody',()=>h.conflictsVotes++],
 ]) {
  h.page=page; let pending=h[estimate](); assert.strictEqual(calls.at(-1).body.estimate,true);
  release({run:{},egress:[]}); await pending; assert(h.previewCurrent(field,h[body](true)));
  const count=calls.length; change(); assert(!h.previewCurrent(field,h[body](true)));
  await h[run](); assert.strictEqual(calls.length,count);
  pending=h[estimate](); change(); release({run:{},egress:[]}); await pending;
  assert.strictEqual(h[field],null, page+' accepted a stale preview response');
 }
})().catch(e=>{console.error(e);process.exitCode=1});
"""

@unittest.skipUnless(shutil.which("node"), "node is required")
class AiPreviewInputTests(unittest.TestCase):
    def test_changed_inputs_cannot_use_a_stale_preview(self):
        script = Path(__file__).resolve().parent.parent / "skillsmgr/webui/ai-center.js"
        subprocess.run(["node", "-e", SCRIPT, str(script)], check=True, capture_output=True, text=True)
