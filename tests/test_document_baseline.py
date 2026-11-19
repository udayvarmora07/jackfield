"""Browser baseline contracts, executed against the shipped pure JS model."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / 'skillsmgr/webui/v2/model.js'
HARNESS = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={window:{SkillManagerDomain:{esc:String}}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const b=ctx.window.SkillsV2Model.documentBaseline;
const id=n=>n.toString(16).padStart(64,'0');
const row=(i,h=i,name='same')=>({id:id(i),content_hash:id(h),name,scope:'agents'});
const envelope=(rows=[],extra={})=>({hygiene:{document_fingerprints:{version:1,status:'observed',coverage:'configured scopes',context_id:id(123),omitted:0,instances:rows,...extra},summary:{partial:false},degraded:[]},degraded:[]});
const stamp='2026-11-17T00:00:00.000Z';
'''

@unittest.skipUnless(shutil.which('node'), 'Node is required')
class DocumentBaselineTests(unittest.TestCase):
    def run_js(self, body):
        subprocess.run(['node', '-e', HARNESS + body, str(MODEL)], cwd=ROOT,
                       check=True, text=True, capture_output=True)

    def test_empty_and_privacy_roundtrip(self):
        self.run_js(r'''
assert.strictEqual(b.read(null),null);assert.strictEqual(b.read(''),null);
const scan=b.snapshot(envelope([row(1,2,'private skill')]));
const saved=b.merge(scan,null,stamp), raw=JSON.stringify(saved);
assert.deepStrictEqual(Object.keys(saved).sort(),['captured_at','context_id','instances','version']);
assert(!raw.includes('private skill'));assert(!raw.includes('agents'));
assert.strictEqual(b.read(raw).instances.length,1);
assert.strictEqual(b.compare(b.snapshot(envelope()),null).status,'missing');
assert(Object.isFrozen(b));
''')

    def test_comparison_union_and_context(self):
        self.run_js(r'''
const first=b.snapshot(envelope([row(1),row(2)]));const baseline=b.merge(first,null,stamp);
const second=b.snapshot(envelope([row(1,9),row(3,3)]));const out=b.compare(second,baseline);
assert.equal(out.status,'compared');assert.equal(out.changed_count,1);assert.equal(out.compared_count,1);assert.equal(out.unobserved_count,1);assert.equal(out.changed[0].id,id(1));
const merged=b.merge(second,baseline,stamp);assert.equal(merged.instances.length,3);assert.equal(new Map(merged.instances).get(id(2)),id(2));
const other=b.snapshot(envelope([row(1)],{context_id:id(124)}));assert.equal(b.compare(other,baseline).status,'other-context');assert.throws(()=>b.merge(other,baseline,stamp));
assert.equal(b.compare(b.snapshot(envelope([row(1),row(2)])),baseline).changed_count,0);
''')

    def test_rejects_tampering_and_partial_scans(self):
        self.run_js(r'''
const scan=b.snapshot(envelope([row(1)]));const saved=b.merge(scan,null,stamp);
for(const bad of ['{', 'x'.repeat(b.maxChars+1), JSON.stringify({...saved,body:'secret'}), JSON.stringify({...saved,captured_at:'yesterday'}), JSON.stringify({...saved,instances:[[id(1),id(1)],[id(1),id(2)]]}), JSON.stringify({...saved,context_id:'x'}), JSON.stringify({...saved,version:2})]) assert.throws(()=>b.read(bad));
assert.throws(()=>b.snapshot({hygiene:{}}));assert.throws(()=>b.snapshot(envelope([row(1),row(1)])));
for(const report of [envelope([row(1)],{status:'partial'}),envelope([row(1)],{omitted:1}),{...envelope(),degraded:[{}]}, {hygiene:{...envelope().hygiene,degraded:[{}]}}, {hygiene:{...envelope().hygiene,summary:{partial:true}}}]) {
 const partial=b.snapshot(report);assert(partial.partial);assert.throws(()=>b.merge(partial,saved,stamp));assert(b.compare(partial,saved).partial);
}
assert.throws(()=>b.merge(scan,null,'bad date'));
''')

    def test_limits_and_display_cap(self):
        self.run_js(r'''
const rows=Array.from({length:10000},(_,i)=>row(i+1));
const first=b.snapshot(envelope(rows));const saved=b.merge(first,null,stamp);assert.equal(saved.instances.length,10000);
const changed=b.snapshot(envelope(rows.map(r=>({...r,content_hash:id(20000)}))));const result=b.compare(changed,saved);
assert.equal(result.changed_count,10000);assert.equal(result.changed.length,100);
assert.throws(()=>b.snapshot(envelope([...rows,row(10001)])));
assert.throws(()=>b.merge(b.snapshot(envelope([row(10001)])),saved,stamp));
''')

    def test_invalid_current_evidence_cannot_be_persisted(self):
        self.run_js(r'''
for(const report of [envelope([row(1)],{version:2}), envelope([row(1)],{status:'complete'}),
 envelope([row(1)],{omitted:-1}),envelope([row(1)],{context_id:'bad'}),
 envelope([{...row(1),content_hash:'bad'}]),envelope([{...row(1),name:{}}]),
 {hygiene:{...envelope().hygiene,degraded:{}}}, {...envelope(),degraded:{}},
 {hygiene:{...envelope().hygiene,summary:[]}}]) assert.throws(()=>b.snapshot(report));
const first=b.snapshot(envelope([row(1)])),saved=b.merge(first,null,stamp);
const empty=b.snapshot(envelope());assert.equal(b.merge(empty,saved,stamp).instances.length,1);
const partial=b.snapshot(envelope([row(1,2)],{status:'partial',omitted:1}));
const result=b.compare(partial,saved);assert(result.partial);assert.equal(result.changed_count,1);
assert.equal(result.compared_count,1);assert.throws(()=>b.merge(partial,saved,stamp));
''')
