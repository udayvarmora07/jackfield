"""Exercise shipped v2 operation guards under Node, with no real user data."""

import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "skillsmgr" / "webui" / "v2"
HARNESS = r"""
const fs=require('fs'),vm=require('vm');
let calls=[],events=[],handler=async()=>({});
const api=async(url,opts={})=>{calls.push({url,opts});return handler(url,opts)};
class Form { constructor(){this.parts=[]} append(...part){this.parts.push(part)} }
const ctx={window:{SkillManagerDomain:{api,esc:s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),observeRecord:()=>({linkEscape:false})}},console,
 localStorage:{getItem:()=>null,setItem:()=>{}},matchMedia:()=>({matches:false}),
 FormData:Form,confirm:()=>true,navigator:{clipboard:{writeText:async()=>{}},locks:{request:async(name,options,fn)=>fn()}},location:{hash:''},
 Vue:{createApp(def){ctx.appDef=def;return {component(){return this},mount(){}}},markRaw:v=>v}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(V2+'/model.js','utf8'),ctx);
for(const name of ['library-tools.js','tool-center.js'])vm.runInContext(fs.readFileSync(V2+'/'+name,'utf8'),ctx);
function mount(component,props={}){
 const h=Object.assign(component.data(),{records:[],scopes:[],names:[],agentFilter:'all',catalog:{},page:'tools',alive:true,target:null},props);
 h.$emit=(...args)=>events.push(args);h.$nextTick=fn=>Promise.resolve().then(fn);
 h.$refs={review:{showModal(){},close(){}}};
 for(const [name,fn] of Object.entries(component.methods))h[name]=fn.bind(h);
 for(const [name,fn] of Object.entries(component.computed))Object.defineProperty(h,name,{get:()=>fn.call(h),configurable:true});
 return h;
}
const tick=()=>new Promise(r=>setImmediate(r));
"""


def run_node(body):
    script = "const V2=" + json.dumps(str(V2)) + ";" + HARNESS + "\n(async()=>{" + body + "})().then(v=>console.log(JSON.stringify(v))).catch(e=>{console.error(e);process.exit(1)});"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, encoding="utf-8", capture_output=True, check=True)
    return json.loads(result.stdout)


@unittest.skipUnless(shutil.which("node"), "Node is required for frontend behavior checks")
class ToolBehaviorTests(unittest.TestCase):
    def test_history_collapses_runs_of_one_action_in_one_minute(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'recovery-extra'});
          h.history=[
            {id:1,name:'a',action:'create',at:'2026-11-20T10:09:05Z'},
            {id:2,name:'b',action:'create',at:'2026-11-20T10:09:40Z'},
            {id:3,name:'c',action:'edit',at:'2026-11-20T10:09:41Z'},
            {id:4,name:'d',action:'create',at:'2026-11-20T10:09:42Z'},
            {id:5,name:'e',action:'create',at:'2026-11-20T10:10:01Z'},
            {id:6,name:'f',action:'',at:'2026-11-20T10:10:02Z'},
            {id:7,name:'g',action:'',at:'2026-11-20T10:10:03Z'}];
          const groups=h.historyGroups.map(g=>g.rows.map(r=>r.name).join(''));
          h.history=[];const empty=h.historyGroups.length;
          h.history=null;const none=h.historyGroups.length;
          return {groups,empty,none};
        """)
        # Only consecutive rows with the same action in the same minute merge;
        # an interleaved action, a new minute or a missing action splits them.
        self.assertEqual(out["groups"], ["ab", "c", "d", "e", "f", "g"])
        self.assertEqual(out["empty"], 0)
        self.assertEqual(out["none"], 0)

    def test_document_baseline_requires_explicit_save_and_stores_only_hashes(self):
        out = run_node(r"""
          const memory=new Map();let writes=0;
          ctx.localStorage={getItem:k=>memory.get(k)||null,setItem:(k,v)=>{writes++;memory.set(k,v)},removeItem:k=>memory.delete(k)};
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});
          const envelope={data_dir:'/private/store',hygiene:{summary:{},degraded:[],document_fingerprints:{version:1,status:'observed',coverage:'Primary document text only',context_id:'a'.repeat(64),omitted:0,
            instances:[{id:'b'.repeat(64),content_hash:'c'.repeat(64),name:'private-name',scope:'codex'}]}}};
          handler=async()=>envelope;await h.loadQuality();const before=writes;
          await h.saveDocumentBaseline();const raw=[...memory.values()][0];
          const h2=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});await h2.loadQuality();
          return {before,writes,raw,status:h2.documentComparison.status,count:h2.documentComparison.compared_count};
        """)
        self.assertEqual(out['before'], 0)
        self.assertEqual(out['writes'], 1)
        self.assertEqual(out['status'], 'compared')
        self.assertEqual(out['count'], 1)
        for forbidden in ('private', 'codex', 'data_dir', 'body', 'description'):
            self.assertNotIn(forbidden, out['raw'])

    def test_failed_or_stale_scans_cannot_save_or_replace_document_baseline(self):
        out = run_node(r"""
          let writes=0;ctx.localStorage={getItem:()=>null,setItem:()=>writes++};
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});
          let resolve;handler=()=>new Promise(r=>resolve=r);const request=h.loadQuality();
          h.changeProject('/new-context');
          resolve({hygiene:{document_fingerprints:{version:1,status:'observed',coverage:'Primary document text only',context_id:'a'.repeat(64),omitted:0,instances:[]}}});await request;
          await h.saveDocumentBaseline();const stale=writes;
          handler=async()=>{throw Error('Scan failed')};await h.loadQuality();await h.saveDocumentBaseline();
          return {stale,writes,quality:h.quality};
        """)
        self.assertEqual(out['stale'], 0)
        self.assertEqual(out['writes'], 0)
        self.assertIsNone(out['quality'])

    def test_storage_change_and_quota_failure_preserve_existing_baseline(self):
        out = run_node(r"""
          const B=ctx.window.SkillsV2Model.documentBaseline;
          const envelope={hygiene:{summary:{},degraded:[],document_fingerprints:{version:1,status:'observed',coverage:'Primary document text only',context_id:'a'.repeat(64),omitted:0,
            instances:[{id:'b'.repeat(64),content_hash:'c'.repeat(64),name:'one',scope:'global'}]}}};
          const original=JSON.stringify(B.merge(B.snapshot(envelope),null,'2026-11-17T12:00:00.000Z'));
          let raw=original,writes=0,quota=false;
          ctx.localStorage={getItem:()=>raw,setItem:(k,v)=>{if(quota)throw Error('quota');writes++;raw=v},removeItem:()=>{raw=null}};
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});handler=async()=>envelope;await h.loadQuality();
          raw=original+' ';await h.saveDocumentBaseline();const concurrent={writes,error:h.baselineError};
          const external=raw;h.loadDocumentBaseline();quota=true;await h.saveDocumentBaseline();
          return {concurrent,writes,preserved:raw===external,error:h.baselineError};
        """)
        self.assertEqual(out['concurrent']['writes'], 0)
        self.assertIn('changed', out['concurrent']['error'].lower())
        self.assertEqual(out['writes'], 0)
        self.assertTrue(out['preserved'])
        self.assertTrue(out['error'])

    def test_partial_and_other_context_scans_do_not_overwrite_saved_baseline(self):
        out = run_node(r"""
          let raw=null,writes=0;ctx.localStorage={getItem:()=>raw,setItem:(k,v)=>{writes++;raw=v},removeItem:()=>{raw=null}};
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});
          let envelope={hygiene:{summary:{},degraded:[],document_fingerprints:{version:1,status:'observed',coverage:'Primary document text only',context_id:'a'.repeat(64),omitted:0,instances:[]}}};
          handler=async()=>envelope;await h.loadQuality();await h.saveDocumentBaseline();const original=raw;
          envelope.hygiene.degraded=[{section:'scope-scan'}];await h.loadQuality();await h.saveDocumentBaseline();const partialPreserved=raw===original;
          envelope=JSON.parse(JSON.stringify(envelope));envelope.hygiene.degraded=[];envelope.hygiene.document_fingerprints.context_id='d'.repeat(64);
          await h.loadQuality();await h.saveDocumentBaseline();const otherPreserved=raw===original;
          h.loadDocumentBaseline();await h.saveDocumentBaseline(true);return {partialPreserved,otherPreserved,writes,context:JSON.parse(raw).context_id};
        """)
        self.assertTrue(out['partialPreserved'])
        self.assertTrue(out['otherPreserved'])
        self.assertEqual(out['writes'], 2)
        self.assertEqual(out['context'], 'd' * 64)

    def test_corrupt_baseline_needs_explicit_forget_and_storage_read_failure_is_clean(self):
        out = run_node(r"""
          let raw='{broken',writes=0;
          ctx.localStorage={getItem:()=>raw,setItem:()=>writes++,removeItem:()=>{raw=null}};
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});
          handler=async()=>({hygiene:{summary:{},degraded:[],document_fingerprints:{version:1,status:'observed',coverage:'Primary document text only',context_id:'a'.repeat(64),omitted:0,instances:[]}}});
          await h.loadQuality();await h.saveDocumentBaseline();const invalid={raw,writes,error:h.baselineError};
          await h.forgetDocumentBaseline();const forgotten=raw;
          ctx.localStorage.getItem=()=>{throw Error('disabled')};h.loadDocumentBaseline();
          return {invalid,forgotten,error:h.baselineError};
        """)
        self.assertEqual(out['invalid']['raw'], '{broken')
        self.assertEqual(out['invalid']['writes'], 0)
        self.assertTrue(out['invalid']['error'])
        self.assertIsNone(out['forgotten'])
        self.assertTrue(out['error'])

    def test_baseline_writes_share_a_lock_and_reject_stale_tabs_and_scans(self):
        out = run_node(r"""
          let raw=null;ctx.localStorage={getItem:()=>raw,setItem:(k,v)=>{raw=v},removeItem:()=>{raw=null}};
          const queued=[];ctx.navigator.locks={request:(name,opts,fn)=>new Promise((resolve,reject)=>queued.push({name,run:async()=>{try{resolve(await fn())}catch(e){reject(e)}}}))};
          const report=i=>({hygiene:{summary:{},degraded:[],document_fingerprints:{version:1,status:'observed',coverage:'Primary text',context_id:'a'.repeat(64),omitted:0,
            instances:[{id:i.repeat(64),content_hash:'c'.repeat(64),name:'one',scope:'global'}]}}});
          const a=mount(ctx.window.SkillsV2ToolCenter,{page:'quality',qualityEnvelope:report('b')});
          const b=mount(ctx.window.SkillsV2ToolCenter,{page:'quality',qualityEnvelope:report('d')});
          a.loadDocumentBaseline();b.loadDocumentBaseline();
          const first=a.saveDocumentBaseline(),second=b.saveDocumentBaseline();
          await queued.shift().run();await first;await queued.shift().run();await second;
          const refused=b.baselineError,firstIDs=JSON.parse(raw).instances.map(x=>x[0]);
          b.loadDocumentBaseline();const retry=b.saveDocumentBaseline();await queued.shift().run();await retry;
          const union=JSON.parse(raw).instances.map(x=>x[0]);
          const stale=a.saveDocumentBaseline();a.changeProject('/new');await queued.shift().run();await stale;
          a.loadDocumentBaseline();const forgotten=a.forgetDocumentBaseline();const lockName=queued[0].name;await queued.shift().run();await forgotten;
          return {refused,firstIDs,union,lockName,raw};
        """)
        self.assertIn('changed', out['refused'].lower())
        self.assertEqual(out['firstIDs'], ['b' * 64])
        self.assertEqual(out['union'], ['b' * 64, 'd' * 64])
        self.assertEqual(out['lockName'], 'skillsmgr-document-baseline-v1')
        self.assertIsNone(out['raw'])

    def test_browser_without_locks_cannot_write_or_forget_the_saved_baseline(self):
        out = run_node(r"""
          let writes=0;ctx.localStorage={getItem:()=>null,setItem:()=>writes++,removeItem:()=>writes++};
          delete ctx.navigator.locks;
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});
          handler=async()=>({hygiene:{summary:{},degraded:[],document_fingerprints:{version:1,status:'observed',coverage:'Primary text',context_id:'a'.repeat(64),omitted:0,instances:[]}}});
          await h.loadQuality();await h.saveDocumentBaseline();await h.forgetDocumentBaseline();
          return {writes,error:h.baselineError,canSave:h.canSaveDocumentBaseline};
        """)
        self.assertEqual(out['writes'], 0)
        self.assertFalse(out['canSave'])
        self.assertIn('coordinate', out['error'].lower())

    def test_tool_catalog_drives_routes_listing_and_command_choices(self):
        out = run_node(r"""
          ctx.Vue={createApp(def){ctx.appDef=def;return {component(){return this},mount(){}}},markRaw:v=>v};
          vm.runInContext(fs.readFileSync(V2+'/app.js','utf8'),ctx);
          const M=ctx.window.SkillsV2Model, route=()=>ctx.appDef.data().route;
          const routes=[];
          for(const id of M.toolIds){ctx.location.hash='#/tools/'+id;routes.push(route().tool)}
          ctx.location.hash='#/tools/unknown';const unknown=route().tool;
          ctx.location.hash='#/tools';const base=route().tool;
          const choices=ctx.appDef.computed.commandChoices.call({commandQuery:''});
          const groups=ctx.window.SkillsV2ToolCenter.computed.toolGroups.call({});
          return {routes,ids:M.toolIds,unknown,base,groups,choices};
        """)
        self.assertEqual(out["routes"], out["ids"])
        self.assertEqual(out["unknown"], "tools")
        self.assertEqual(out["base"], "tools")
        self.assertEqual([item["id"] for group in out["groups"] for item in group["items"]], out["ids"])
        self.assertNotIn("#/tools/source-update", [item.get("path") for item in out["choices"]])
        self.assertIn({"label": "Quality and validation", "path": "#/tools/quality"}, out["choices"])

    def test_shared_name_guard_covers_lengths_and_malformed_library_records(self):
        out = run_node(r"""
          const valid=ctx.window.SkillsV2Model.validName;
          const c=ctx.window.SkillsV2LibraryTools;
          const h=mount(c,{scopes:[{id:'codex',writable:true}]});
          return {valid64:valid('a'.repeat(64)),valid65:valid('a'.repeat(65)),validName:valid('valid-name'),
            malformed:[{name:'Bad Name'},{name:'UPPER'},{name:'bad--name'},{name:'.'},{name:'a/b'}].map(r=>h.selectable(r)),
            accepted:h.selectable({name:'valid-name',scope:'codex'})};
        """)
        self.assertTrue(out["valid64"])
        self.assertFalse(out["valid65"])
        self.assertTrue(out["validName"])
        self.assertEqual(out["malformed"], [False] * 5)
        self.assertTrue(out["accepted"])

    def test_independent_report_reads_do_not_discard_each_others_results(self):
        out = run_node(r"""
          const resolve={};handler=url=>new Promise(r=>resolve[url]=r);
          const h=mount(ctx.window.SkillsV2ToolCenter);
          const a=h.read('/quality','quality'),b=h.read('/stats','report');
          resolve['/stats']({total:3});await b;resolve['/quality']({findings:['evidence']});await a;
          return {quality:h.quality,report:h.report};
        """)
        self.assertEqual(out["quality"], {"findings": ["evidence"]})
        self.assertEqual(out["report"], {"total": 3})

    def test_batch_execution_uses_reviewed_targets_and_options_after_ui_changes(self):
        out = run_node(r"""
          const a={name:'one',scope:'codex',path:'/skills/one',physical_path:'/skills/one',addressable:true};
          const b={name:'two',scope:'codex',path:'/skills/two',physical_path:'/skills/two',addressable:true};
          const h=mount(ctx.window.SkillsV2LibraryTools,{records:[a,b],names:['one','two'],scopes:[{id:'codex',writable:true}]});
          h.selected=[h.key(a)];h.operation='sync';h.frozen=[{name:a.name,scope:a.scope,path:a.path,physical_path:a.physical_path}];h.targets=['claude-code'];h.force=false;
          handler=async url=>url.endsWith('/preview')?{plan_id:'reviewed',target_count:1}:{ok:true,results:[]};
          await h.preview();h.selected=[h.key(b)];h.targets=['other-scope'];h.force=true;await h.execute();
          return calls.map(c=>JSON.parse(c.opts.body));
        """)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[1], {**out[0], "plan_id": "reviewed"})
        self.assertEqual(out[1]["targets"][0]["name"], "one")
        self.assertEqual(out[1]["to_scopes"], ["claude-code"])
        self.assertFalse(out[1]["force"])

    def test_failed_workspace_lookup_clears_previous_project_evidence(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{project:'/new-project',workspace:{project:{path:'/old-project'}}});
          handler=async()=>{throw Error('Project unavailable')};h.loadWorkspace();await tick();
          return {workspace:h.workspace,error:h.error};
        """)
        self.assertIsNone(out["workspace"])
        self.assertEqual(out["error"], "Project unavailable")

    def test_quality_project_query_is_encoded_and_clear_restores_no_project(self):
        out = run_node(r"""
          handler=async()=>({hygiene:{findings:[]}});
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality'});
          h.changeProject('/allowed/project & one');await h.loadQuality();
          const report=h.quality;
          h.changeProject('');const cleared=h.quality;await h.loadQuality();
          return {urls:calls.map(c=>c.url),report,cleared};
        """)
        self.assertIn('&project=%2Fallowed%2Fproject%20%26%20one', out['urls'][0])
        self.assertEqual(out['urls'][1], '/api/doctor?scope=all&hygiene=1')
        self.assertEqual(out['report'], {'findings': []})
        self.assertIsNone(out['cleared'])

    def test_project_change_retires_in_flight_reports_and_errors(self):
        out = run_node(r"""
          const pending=[];handler=url=>new Promise((resolve,reject)=>pending.push({resolve,reject}));
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'quality',project:'/old',consumer:'codex',
            quality:{old:true},workspace:{old:true},report:{old:true}});
          const a=h.loadQuality(),b=h.loadWorkspace(),c=h.explain();
          h.changeProject('/new');
          pending[0].resolve({hygiene:{stale:true}});pending[1].resolve({project:{path:'/old'}});pending[2].reject(Error('old error'));
          await Promise.all([a,b,c]);
          return {quality:h.quality,workspace:h.workspace,report:h.report,error:h.error,loading:h.loading};
        """)
        for field in ('quality', 'workspace', 'report'):
            self.assertIsNone(out[field])
        self.assertEqual(out['error'], '')
        self.assertEqual(out['loading'], {})

    def test_workspace_roots_remain_available_after_a_refused_project(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter);
          handler=async()=>({managed_roots:['/allowed'],project:{status:'not-requested'}});
          await h.loadWorkspace();
          h.changeProject('/outside');handler=async()=>{throw Error('Outside allowed folders')};
          await h.loadWorkspace();
          return {roots:h.projectRoots,workspace:h.workspace,error:h.error};
        """)
        self.assertEqual(out['roots'], ['/allowed'])
        self.assertIsNone(out['workspace'])
        self.assertEqual(out['error'], 'Outside allowed folders')

    def test_accepted_workspace_is_not_shown_as_a_warning(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{workspace:{project:{status:'accepted'}}});
          return {tone:h.projectTone};
        """)
        self.assertEqual(out['tone'], 'ok')

    def test_failed_validation_cannot_relabel_old_statistics_as_validation(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{validationName:'one',report:{all_total:4},reportKind:'stats'});
          handler=async()=>{throw Error('Validation unavailable')};await h.validateNamed();
          return {report:h.report,kind:h.reportKind,error:h.error};
        """)
        self.assertIsNone(out["report"])
        self.assertEqual(out["kind"], "validate")
        self.assertEqual(out["error"], "Validation unavailable")

    def test_runner_failure_requests_refresh_without_claiming_completed_refresh(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{source:'owner/repository'});h.runnerPreview=h.runnerSignature;
          handler=async()=>{throw Error('Runner timed out')};await h.runRunner(true);
          return {events,error:h.error,preview:h.runnerPreview,calls:calls.length};
        """)
        self.assertEqual(out["calls"], 1)
        self.assertIn(["changed"], out["events"])
        self.assertIn("refresh was requested", out["error"])
        self.assertNotIn("has been refreshed", out["error"])
        self.assertEqual(out["preview"], "")

    def test_review_completing_after_target_change_is_cancelled(self):
        out = run_node(r"""
          let resolveReview;handler=(url)=>url.endsWith('/reviews')?new Promise(r=>resolveReview=r):Promise.resolve({cancelled:true});
          const a={name:'one',scope:'codex',physical_path:'/skills/one'};
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'source-update',target:a,files:[{name:'SKILL.md'}]});
          const pending=h.prepareSource();await tick();h.target={name:'two',scope:'codex',physical_path:'/skills/two'};
          resolveReview({review_id:'private-review',review_state:'pending'});await pending;
          return {review:h.sourceReview,calls:calls.map(c=>[c.url,c.opts.method]),error:h.error};
        """)
        self.assertIsNone(out["review"])
        self.assertIn(["/api/source-updates/reviews/private-review", "DELETE"], out["calls"])
        self.assertIn("Target changed", out["error"])

    def test_folder_import_requires_review_and_informed_confirmation(self):
        out = run_node(r"""
          const file={name:'SKILL.md',webkitRelativePath:'new-skill/SKILL.md',size:10,text:async()=> '# Instructions'};
          const h=mount(ctx.window.SkillsV2ToolCenter,{files:[file]});handler=async()=>({imported:['new-skill'],skipped:[]});
          await h.uploadFolder();const before=calls.length;await h.reviewFolder();await h.uploadFolder();const unconfirmed=calls.length;
          h.folderTrust=true;await h.uploadFolder();
          return {before,unconfirmed,after:calls.length,url:calls[0]?.url,reviewed:h.folderDocuments[0].previewed};
        """)
        self.assertEqual((out["before"], out["unconfirmed"], out["after"]), (0, 0, 1))
        self.assertEqual(out["url"], "/api/import")
        self.assertTrue(out["reviewed"])

    def test_folder_selection_change_cannot_reuse_pending_or_completed_review(self):
        out = run_node(r"""
          let resolveText;const old={name:'SKILL.md',webkitRelativePath:'old/SKILL.md',size:10,text:()=>new Promise(r=>resolveText=r)};
          const next={name:'SKILL.md',webkitRelativePath:'new/SKILL.md',size:10,text:async()=> '# New'};
          const h=mount(ctx.window.SkillsV2ToolCenter,{files:[old]});
          const pending=h.reviewFolder();await tick();h.files=[next];resolveText('# Old');await pending;
          h.folderTrust=true;await h.uploadFolder();const staleCalls=calls.length,staleApproved=h.folderReviewed;
          await h.reviewFolder();h.folderTrust=true;h.files=[old];await h.uploadFolder();
          return {staleCalls,staleApproved,after:calls.length};
        """)
        self.assertFalse(out["staleApproved"])
        self.assertEqual(out["staleCalls"], 0)
        self.assertEqual(out["after"], 0)

    def test_exact_copy_editor_uses_its_description_and_only_its_scope(self):
        out = run_node(r"""
          let component;
          ctx.location={hash:''};ctx.Vue={createApp:c=>{component=c;return {component(){},mount(){}}},markRaw:v=>v};
          ctx.window.SkillsV2Model={stripFrontmatter:v=>v};
          Object.assign(ctx.window.SkillManagerDomain,{formatCompat:v=>v||'',formatTools:v=>v||''});
          vm.runInContext(fs.readFileSync(V2+'/app.js','utf8'),ctx);
          const h={skill:{name:'divergent',description:'Primary description'},route:{page:'skill'},refCopy:{name:'divergent',scope:'codex',hash:'h1',description:'Selected copy description',body:'# Selected',bodyLoaded:true,record:{}},readCopyPath:'/codex/divergent',editTargets:[{scope:'codex'},{scope:'claude-code'}],$nextTick:()=>{},bodies:{},bodyErrors:{},ensureBodies:async()=>{},bodyKey:component.methods.bodyKey,bodyOf:component.methods.bodyOf,bodyReady:component.methods.bodyReady,bodyErrorOf:component.methods.bodyErrorOf,bodyFetchable:component.methods.bodyFetchable,toast:()=>{}};
          await component.methods.startEdit.call(h);return h.edit;
        """)
        self.assertEqual(out["desc"], "Selected copy description")
        self.assertEqual(out["baseDesc"], "Selected copy description")
        self.assertEqual(out["targets"], ["codex"])

    def test_body_only_editor_save_omits_unchanged_optional_metadata(self):
        out = run_node(r"""
          let component;
          ctx.location={hash:''};ctx.Vue={createApp:c=>{component=c;return {component(){},mount(){}}},markRaw:v=>v};
          ctx.window.SkillsV2Model={plural:(n,s)=>s};
          vm.runInContext(fs.readFileSync(V2+'/app.js','utf8'),ctx);
          const metadata={category:'',version:'',license:'',compatibility:'',allowed_tools:''};
          const h={edit:{name:'one',desc:'Unchanged',baseDesc:'Unchanged',body:'# Changed',baseBody:'# Original',metadata,baseMetadata:{...metadata},targets:['global']},editError:'',busy:false,editDirty:true,snapshotIds:async()=>[],refresh:async()=>{},toast:()=>{}};
          await component.methods.saveEdit.call(h);return JSON.parse(calls[0].opts.body);
        """)
        self.assertEqual(out, {"body": "# Changed"})

    def test_source_apply_requires_positive_validation_evidence(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{trust:true,sourceTarget:{name:'one',scope:'codex',path:'/skills/one'},sourceReview:{review_id:'r',review_state:'pending',validation:{},comparison:{changed_files:[{path:'SKILL.md'}]}}});
          await h.applySource();return calls.length;
        """)
        self.assertEqual(out, 0)

    def test_profile_enable_preserves_exact_divergent_copies_without_syncing(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{profilePreview:{members:[{name:'one',state:'divergent',instances:[{scope:'codex',physical_path:'/c/one'},{scope:'claude-code',physical_path:'/a/one'}]},{name:'missing',state:'missing',instances:[]}]}});
          handler=async()=>({plan_id:'p'});await h.previewPlan();return JSON.parse(calls[0].opts.body);
        """)
        self.assertEqual(out["operation"], "enable")
        self.assertEqual(len(out["targets"]), 2)
        self.assertEqual(out["to_scopes"], [])
        self.assertFalse(out["force"])


@unittest.skipUnless(shutil.which("node"), "Node is required for frontend behavior checks")
class ClaudeListingCardTests(unittest.TestCase):
    """The Quality page's "What Claude Code sees" card is read-only evidence."""

    def test_verdict_is_a_worded_pill_for_each_status(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter);
          return ['within_budget','over_budget_estimate','unknown','surprising'].map(s=>h.listingVerdict({status:s}));
        """)
        self.assertEqual(out[0], {"text": "Fits the listing budget", "tone": "ok"})
        self.assertEqual(out[1], {"text": "Over the listing budget (estimate)", "tone": "warn"})
        self.assertEqual(out[2], {"text": "Can't tell — a settings file couldn't be read", "tone": "off"})
        # An unrecognised status must never read as a green "fits".
        self.assertEqual(out[3], {"text": "Budget status not recognised", "tone": "off"})

    def test_the_snippet_is_valid_json_for_any_skill_name(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter);
          return JSON.parse('{'+h.listingSnippet('we"ird\\name')+'}');
        """)
        self.assertEqual(out, {"skillOverrides": {'we"ird\\name': "name-only"}})

    def test_meter_measures_the_listing_against_its_budget(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter);
          const over={status:'over_budget_estimate',listing_chars:77516,budget:{budget_chars_estimate:40000}};
          const fits={status:'within_budget',listing_chars:10000,budget:{budget_chars_estimate:40000}};
          const none={status:'within_budget',listing_chars:10,budget:{budget_chars_estimate:0}};
          return {over:{pct:h.listingPct(over),fill:h.listingFill(over),over:h.listingOver(over)},
                  fits:{pct:h.listingPct(fits),fill:h.listingFill(fits),over:h.listingOver(fits)},
                  none:{pct:h.listingPct(none),fill:h.listingFill(none)}};
        """)
        self.assertEqual(out["over"]["pct"], 193.8)
        self.assertEqual(out["over"]["fill"], "100%")
        self.assertTrue(out["over"]["over"])
        self.assertEqual(out["fits"]["pct"], 25.0)
        self.assertEqual(out["fits"]["fill"], "25%")
        self.assertFalse(out["fits"]["over"])
        self.assertEqual(out["none"]["pct"], 0)
        self.assertEqual(out["none"]["fill"], "1.5%")

    def test_the_listing_and_its_partial_reasons_come_from_the_report(self):
        out = run_node(r"""
          const section={instances_observed:3,listed_skills:3,confidence:'partial',
            partial_reasons:['project settings were not read (no project root), so a project skillOverrides entry could change this estimate'],
            status:'within_budget',listing_chars:10,budget:{budget_chars_estimate:1000,assumption:'estimated from 1% of the window'}};
          const h=mount(ctx.window.SkillsV2ToolCenter,{quality:{claude_listing:section}});
          return {card:h.claudeListing,confidence:h.claudeListing.confidence,reasons:h.claudeListing.partial_reasons};
        """)
        self.assertTrue(out["card"])
        self.assertEqual(out["confidence"], "partial")
        self.assertEqual(len(out["reasons"]), 1)

    def test_a_candidate_renders_the_exact_settings_fragment(self):
        out = run_node("const h=mount(ctx.window.SkillsV2ToolCenter);return h.listingSnippet('alpha-skill');")
        self.assertEqual(out, '"skillOverrides": { "alpha-skill": "name-only" }')

    def test_a_missing_section_or_no_instances_shows_no_card(self):
        out = run_node(r"""
          const missing=mount(ctx.window.SkillsV2ToolCenter,{quality:{}});
          const zero=mount(ctx.window.SkillsV2ToolCenter,{quality:{claude_listing:{instances_observed:0}}});
          const present=mount(ctx.window.SkillsV2ToolCenter,{quality:{claude_listing:{instances_observed:2,status:'within_budget'}}});
          return {missing:missing.claudeListing,zero:zero.claudeListing,present:!!present.claudeListing};
        """)
        self.assertIsNone(out["missing"])
        self.assertIsNone(out["zero"])
        self.assertTrue(out["present"])

    def test_excluded_keys_read_as_words_not_api_slugs(self):
        out = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter);
          return ['disabled','skillOverrides_off','unreadable','name_only','skillOverrides_user_invocable_only','disable_model_invocation','something_new']
            .map(k=>h.listingExcludedLabel(k));
        """)
        self.assertEqual(out, ["Turned off on disk", "Off in settings", "Could not be read",
                               "Name only", "User-invocable only", "Model invocation disabled",
                               "Something new"])

    def test_the_card_adds_no_html_sink_and_binds_every_piece_as_text(self):
        source = (V2 / "tool-center.js").read_text(encoding="utf-8")
        self.assertNotIn("v-html", source)
        for binding in ("claudeListing.partial_reasons", 'pill off">Partial',
                        "Ranked by description size only. Claude Code drops descriptions starting with the skills you use least, which this tool can't see.",
                        "listingSnippet(c.name)", "copyListingSnippet(c.name)",
                        "Free about", "No Claude Code skills were observed"):
            self.assertIn(binding, source)
