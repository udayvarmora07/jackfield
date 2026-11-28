"""Contracts for the web interface (``skillsmgr/webui``).

The v2 interface is the prototype-final design wired to the real API. It adds
presentation and workflow framing only: the same endpoints, the same observed
state vocabulary, and no new CLI command, Store method, schema or dependency.

Every behavioural check runs the *checked-in* ``model.js`` under Node with the
real ``domain.js``, so it fails when the sources drift rather than when a mock
goes stale.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "skillsmgr" / "webui"
DOMAIN_JS = ROOT / "skillsmgr" / "webui" / "domain.js"


def _node(body: str):
    """Load domain.js and model.js into a Node vm and return ``body``'s JSON."""
    script = (
        "const vm=require('vm'),fs=require('fs');"
        "const loadJackfield=require('./tests/fixtures/load_jackfield.cjs');"
        "const ctx={window:{},console,Blob,FormData,URLSearchParams,location:{hash:''},localStorage:{getItem(){return null;}}};ctx.window.window=ctx.window;vm.createContext(ctx);"
        "vm.runInContext(fs.readFileSync('skillsmgr/webui/static/vendor/markdown-it.umd.min.js','utf8'),ctx);"
        f"vm.runInContext(fs.readFileSync({json.dumps(str(DOMAIN_JS))},'utf8'),ctx);"
        f"vm.runInContext(fs.readFileSync({json.dumps(str(V2 / 'model.js'))},'utf8'),ctx);"
        "const M=ctx.window.SkillsV2Model;"
        f"const out=(function(){{{body}}})();"
        "Promise.resolve(out).then(value=>console.log(JSON.stringify(value)))"
        ".catch(error=>{console.error(error);process.exit(1);});"
    )
    res = subprocess.run(["node", "-e", script], capture_output=True, encoding="utf-8", check=True, cwd=str(ROOT))
    return json.loads(res.stdout)


NODE = shutil.which("node") is not None
HELPERS = r"""
const scopes=[
 {id:'claude-code',label:'Claude Code',kind:'agent',exists:true,writable:true,consumer:'claude-code',path:'/h/.claude/skills'},
 {id:'codex',label:'Codex',kind:'agent',exists:true,writable:true,consumer:'codex',path:'/h/.codex/skills'},
 {id:'opencode',label:'OpenCode',kind:'agent',exists:true,writable:true,consumer:'opencode',path:'/h/.config/opencode/skills'}];
let n=0;
const rec=(name,scope,over)=>Object.assign({name,scope,scope_label:scope,description:'d',category:'uncategorized',
 body:'b',tokens:100,content_hash:'h1',physical_path:'/p/'+scope+'/'+name,path:'/p/'+scope+'/'+name,
 instance_states:['active'],disabled:0,malformed:false,addressable:true,decode_error:''},over||{});
"""

# The lazy-body methods an app.js context needs; bound from the real component so
# a test exercises the shipped implementation rather than a copy of it.
BODY_CONTEXT_JS = (
    "const BODY_METHODS=['bodyKey','bodyReady','bodyOf','bodyErrorOf','applyBody','bodyFetchable',"
    "'bodyPairKey','modelCopies','bodyPairs','bodyDuplicated','pairCopies','bodiesByPath','duplicateBodyMap',"
    "'namedBody','ensureBodies','readerRouteOptions','showSkillView'];"
    "const bodyContext=(M,extra)=>{"
    "const context=Object.assign({},extra||{});"
    "if(!context.bodies)context.bodies={};"
    "if(!context.bodyInflight)context.bodyInflight={};"
    "if(!context.bodyErrors)context.bodyErrors={};"
    "if(!context.friendly)context.friendly=M.friendly;"
    "if(!context.updatePageTitle)context.updatePageTitle=()=>{};"
    "if(context.route?.page==='skill')Object.assign(context.route,{name:context.skill.name,href:'#/skills/'+context.skill.name});"
    "for(const key of BODY_METHODS)if(context[key]===undefined)context[key]=M[key];"
    "return context;};"
)


@unittest.skipUnless(NODE, "node is required")
class ModelStatusTests(unittest.TestCase):
    def _status(self, records_js: str):
        return _node(HELPERS + f"const m=M.build({records_js},scopes);"
                     "return Object.fromEntries(m.skills.map(s=>[s.name,s.status.label]));")

    def test_matching_copies_are_working(self):
        out = self._status("[rec('a','claude-code'),rec('a','codex')]")
        self.assertEqual(out, {"a": "Working"})

    def test_differing_copies_are_named_without_claiming_an_older_one(self):
        out = self._status("[rec('a','claude-code'),rec('a','codex',{content_hash:'h2'})]")
        self.assertEqual(out, {"a": "Copies differ"})

    def test_a_refused_symlink_is_not_a_damaged_skill(self):
        # The agent reads a linked skill fine; this tool just will not follow it.
        out = self._status(
            "[rec('a','claude-code',{malformed:true,instance_states:['invalid'],"
            "decode_error:'skill path escapes managed root'})]")
        self.assertEqual(out, {"a": "Linked elsewhere"})

    def test_a_damaged_document_cannot_be_read(self):
        out = self._status(
            "[rec('a','codex',{malformed:true,instance_states:['invalid'],decode_error:'bad frontmatter'})]")
        self.assertEqual(out, {"a": "Can't be read"})

    def test_system_files_in_a_skills_folder_are_not_skills(self):
        out = self._status(
            "[rec('README.md','codex',{malformed:true,addressable:false,instance_states:['invalid','unaddressable']}),"
            "rec('.system','codex',{malformed:true,addressable:false,instance_states:['invalid','unaddressable']})]")
        self.assertEqual(out, {"README.md": "Not a skill", ".system": "Not a skill"})

    def test_partial_disable_is_found_without_changing_the_skill_status(self):
        result = _node("""
          const skill = {copies: [{scope: 'claude-code', state: 'on'}, {scope: 'codex', state: 'off'}]};
          return [M.hasOffCopy(skill), M.hasOffCopy(skill, 'codex'), M.hasOffCopy(skill, 'claude-code'),
                  M.hasOffCopy({copies: []})];
        """)
        self.assertEqual(result, [True, True, False, False])

    def test_disabled_everywhere_is_turned_off(self):
        out = self._status(
            "[rec('a','codex',{disabled:1,instance_states:['disabled']}),"
            "rec('a','claude-code',{disabled:1,instance_states:['disabled']})]")
        self.assertEqual(out, {"a": "Turned off"})

    def test_native_off_evidence_stays_separate_from_file_enabled_state(self):
        out = _node(HELPERS + """
        const native={effective_state:'unknown',partial:true,sources:[{source:'user',status:'ok',declared:'off'}]};
        const c=M.build([rec('a','claude-code',{native_state:native})],scopes).skills[0].copies[0];
        return {state:c.state,native:c.record.native_state};""")
        self.assertEqual(out["state"], "on")
        self.assertEqual(out["native"]["effective_state"], "unknown")
        self.assertEqual(out["native"]["sources"][0]["declared"], "off")

    def test_aliases_of_one_physical_document_count_once(self):
        out = _node(HELPERS + "const r=[rec('a','claude-code'),rec('a','claude-code')];"
                    "const m=M.build(r,scopes);return m.skills[0].copies.length;")
        self.assertEqual(out, 1)


@unittest.skipUnless(NODE, "node is required")
class ModelProblemTests(unittest.TestCase):
    def test_reference_is_the_majority_and_a_tie_is_ambiguous(self):
        out = _node(HELPERS + """
        const maj=M.build([rec('a','claude-code'),rec('a','codex',{content_hash:'h2'}),rec('a','opencode')],scopes).skills[0];
        const tie=M.build([rec('a','claude-code'),rec('a','codex',{content_hash:'h2'})],scopes).skills[0];
        return {majority:maj.ref.holders.map(c=>c.scope), majAmbig:maj.ref.ambiguous,
                differing:maj.differing.map(c=>c.scope), tieAmbig:tie.ref.ambiguous};""")
        self.assertEqual(out["majority"], ["claude-code", "opencode"])
        self.assertFalse(out["majAmbig"])
        self.assertEqual(out["differing"], ["codex"])
        self.assertTrue(out["tieAmbig"])

    def test_only_a_damaged_document_with_a_working_copy_is_auto_fixable(self):
        out = _node(HELPERS + """
        const m=M.build([
          rec('dmg','claude-code'),
          rec('dmg','codex',{malformed:true,instance_states:['invalid'],decode_error:'bad'}),
          rec('lnk','claude-code'),
          rec('lnk','codex',{malformed:true,instance_states:['invalid'],decode_error:'escapes managed root'}),
          rec('badname','codex',{addressable:false,instance_states:['unaddressable'],malformed:true}),
          rec('badname','claude-code')],scopes);
        return m.problems.map(p=>({id:p.id,fixable:!!p.fixable,key:p.key}));""")
        by = {p["id"]: p for p in out}
        self.assertTrue(by["bad:dmg"]["fixable"])
        self.assertNotIn("bad:lnk", by)  # a link is a notice, never an error
        self.assertFalse(by["bad:badname"]["fixable"])  # needs a rename on disk
        self.assertTrue(any(p["id"].startswith("link:") for p in out))

    def test_each_distinct_text_gets_a_letter_and_a_is_the_majority(self):
        out = _node(HELPERS + """
        const s=M.build([rec('a','claude-code'),rec('a','codex',{content_hash:'h2'}),rec('a','opencode')],scopes).skills[0];
        return Object.fromEntries(s.copies.map(c=>[c.scope,c.version]));""")
        self.assertEqual(out, {"claude-code": "A", "codex": "B", "opencode": "A"})

    def test_an_undecodable_copy_is_never_offered_an_automatic_overwrite(self):
        # E2E D1: force sync can preserve binary snapshots, but this screen's
        # text Undo cannot restore them. Keep manual guidance here.
        out = _node(HELPERS + """
        const m=M.build([rec('u','claude-code'),
          rec('u','codex',{malformed:true,instance_states:['invalid'],decode_error:"'utf-8' codec can't decode byte 0xff"})],scopes);
        const p=m.problems.find(x=>x.id==='bad:u'); return {fixable:p.fixable, action:p.action, short:p.short};""")
        self.assertFalse(out["fixable"])
        self.assertEqual(out["action"], "Show me how")
        self.assertEqual(out["short"], "Not readable text")

    def test_mixed_damaged_targets_do_not_offer_text_undo_for_binary_bytes(self):
        out = _node(HELPERS + """
        const m=M.build([rec('u','claude-code',{malformed:true,instance_states:['invalid'],decode_error:'bad frontmatter'}),
          rec('u','codex',{malformed:true,instance_states:['invalid'],decode_error:'not valid UTF-8'}),
          rec('u','opencode')],scopes);
        const p=m.problems.find(x=>x.id==='bad:u');return {fixable:p.fixable,short:p.short};""")
        self.assertFalse(out["fixable"])
        self.assertEqual(out["short"], "Not readable text")

    def test_a_refused_link_cannot_be_the_source_of_a_repair(self):
        out = _node(HELPERS + """
        const m=M.build([rec('u','claude-code',{malformed:true,instance_states:['invalid'],decode_error:'bad frontmatter'}),
          rec('u','codex',{malformed:true,instance_states:['invalid'],decode_error:'skill path escapes managed root'})],scopes);
        return m.problems.find(x=>x.id==='bad:u').fixable;""")
        self.assertFalse(out)

    def test_problems_are_ordered_serious_first(self):
        out = _node(HELPERS + """
        const m=M.build([rec('a','claude-code'),rec('a','codex',{content_hash:'h2'}),
          rec('z','codex',{malformed:true,instance_states:['invalid'],decode_error:'bad'}),rec('z','claude-code')],scopes);
        return m.problems.map(p=>p.key);""")
        self.assertEqual(out, sorted(out, key={"bad": 0, "warn": 1, "info": 2}.get))
        self.assertEqual(out[0], "bad")

    def test_an_unreachable_agent_folder_is_not_listed(self):
        out = _node(HELPERS + "const m=M.build([],scopes.concat([{id:'cursor',label:'Cursor',kind:'agent',exists:false}]));"
                    "return m.agents.map(a=>a.id);")
        self.assertNotIn("cursor", out)


class AgentIconTests(unittest.TestCase):
    """Approved marks are local SVG masks. The fallback keeps readable initials."""

    @unittest.skipUnless(NODE, "node is required")
    def test_scope_ids_map_to_well_formed_local_svg_masks(self):
        from urllib.parse import unquote
        from xml.etree import ElementTree

        ids = ["claude-code", "codex", "cursor", "gemini", "opencode", "commandcode",
               "agents", "project-agents", "custom-kilo", "global", "unknown"]
        marks = _node("return " + json.dumps(ids) + ".map(id=>M.agentMark(id).mark);")
        self.assertEqual(marks, ["CC", "CX", "Cursor", "Gemini", "OC", "Command Code",
                                 "SH", "PJ", "Custom agent", None, None])
        sheet = (V2 / "system.css").read_text(encoding="utf-8")
        for mark in filter(None, marks):
            match = re.search(r'\[data-a="' + re.escape(mark) +
                              r'"\]\{--agi:url\("data:image/svg\+xml,([^"]+)"', sheet)
            self.assertIsNotNone(match, mark)
            svg = ElementTree.fromstring(unquote(match[1]))
            self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertEqual(len(svg.get("viewBox").split()), 4)
            self.assertTrue(all(element.tag.rsplit("}", 1)[-1] in {"svg", "g", "path", "rect", "circle"}
                                for element in svg.iter()), mark)

    def test_agents_without_a_mark_keep_the_initials_badge(self):
        app = (V2 / "app.js").read_text(encoding="utf-8")
        self.assertIn('v-if="agent.mark"', app)
        self.assertIn('v-else>{{ agent.initials }}', app)

    def test_initials_are_readable_in_both_themes(self):
        from check_design_tokens import contrast
        from tools.gen_tokens import SOURCE, token_values

        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        for theme in ("light", "dark"):
            palette = token_values(source, theme)
            self.assertGreaterEqual(contrast(palette["ink-2"], palette["raise"]), 4.5)


class BrandMarkTests(unittest.TestCase):
    def test_logo_and_small_favicon_are_well_formed(self):
        # A malformed SVG (e.g. "--" inside an XML comment) decodes to a 0x0
        # image with no console error, so parse it as XML here.
        import xml.etree.ElementTree as ElementTree
        root = ElementTree.parse(V2 / "logo.svg").getroot()
        self.assertEqual(root.get("viewBox"), "0 0 32 32")
        favicon = ElementTree.parse(V2 / "favicon.svg").getroot()
        self.assertEqual(favicon.get("viewBox"), "0 0 256 256")
        self.assertEqual(len(favicon.findall(".//{*}path")), 4)
        self.assertIn('<link rel="icon" href="favicon.svg" type="image/svg+xml">',
                      (V2 / "index.html").read_text(encoding="utf-8"))


class RenderSafetyTests(unittest.TestCase):
    PAYLOADS = [
        "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "**<b onmouseover=x>** y",
        "[x](javascript:alert(1))", "`<svg onload=alert(1)>`", "```\n<iframe src=//evil></iframe>\n```",
        "> <a href=\"javascript:1\">k</a>", "- <style>*{}</style>", "# \"><script>1</script>",
    ]

    def test_hostile_skill_text_is_escaped_to_inert_text(self):
        out = _node(HELPERS + f"const P={json.dumps(self.PAYLOADS)};return P.map(p=>M.renderDoc(p, new Set()));")
        for html in out:
            tags = set(re.findall(r"<\s*/?\s*([a-zA-Z0-9]+)", html))
            self.assertLessEqual(tags, {"p", "h1", "ul", "ol", "li", "blockquote", "strong", "em", "code", "pre", "mark"},
                                 f"unexpected tag in {html!r}")
            self.assertNotRegex(html, r"<[^>]+\son\w+\s*=")  # no live event-handler attribute

    def test_links_and_italics_render_as_safe_text(self):
        out = _node(HELPERS + "return M.renderDoc('see [docs](https://x.test/a) and *this*', new Set());")
        self.assertNotIn("<a", out)
        self.assertIn("<code>https://x.test/a</code>", out)
        self.assertIn("<em>this</em>", out)

    def test_a_link_address_with_parentheses_is_shown_whole(self):
        out = _node(HELPERS + "return M.renderDoc('see [wiki](https://x.test/Foo_(bar)) now', new Set());")
        self.assertIn("<code>https://x.test/Foo_(bar)</code> now", out)
        self.assertNotIn("<a", out)

    def test_a_marked_line_is_highlighted_and_nothing_else(self):
        out = _node(HELPERS + "return M.renderDoc('one\\n\\ntwo', new Set(['two']));")
        self.assertIn("<mark>", out)
        self.assertEqual(out.count("<mark>"), 1)

    def test_markdown_structure_and_changed_table_row(self):
        doc = (
            "## Steps\r\n\r\n- [x] Ready\r\n\r\n  3. Nested\r\n\r\n"
            "Name | Result\r\n:--- | ---:\r\n"
            "`a\\|b` | **passed**\r\n"
            "other | ~~skipped~~\r\n\r\n"
            "> one line\r\n> continued\r\n\r\n"
            "---\r\n\r\n"
            "~~~sh\r\nprintf '<point>'\r\n~~~"
        )
        row = "`a\\|b` | **passed**"
        html = _node(HELPERS + f"return M.renderDoc({json.dumps(doc)}, new Set([{json.dumps(row)}]));")
        self.assertIn("<h2>Steps</h2>", html)
        self.assertIn('type="checkbox" disabled checked', html)
        self.assertIn('<ol start="3">', html)
        self.assertIn('<th scope="col" class="md-align-right">Result</th>', html)
        self.assertIn('<tr class="md-marked">', html)
        self.assertEqual(html.count("md-marked"), 1)
        self.assertIn("<code>a|b</code>", html)
        self.assertIn("<strong>passed</strong>", html)
        self.assertIn("<s>skipped</s>", html)
        self.assertIn("<p>one line\ncontinued</p>", html)
        self.assertIn("<hr>", html)
        self.assertIn('class="language-sh">printf \'&lt;point&gt;\'', html)

    def test_images_and_large_documents_stay_inert(self):
        html = _node(HELPERS + """return {
          image: M.renderDoc('![<look>](https://example.test/pixel.png)'),
          large: M.renderDoc('x'.repeat(512 * 1024) + '<img src=x>'),
        };""")
        self.assertIn("&lt;look&gt;", html["image"])
        self.assertNotIn("<img", html["image"])
        self.assertNotIn("pixel.png", html["image"])
        self.assertIn("too large for formatted preview", html["large"])
        self.assertIn("&lt;img src=x&gt;", html["large"])

    def test_diff_reports_only_changes_and_survives_large_inputs(self):
        out = _node(HELPERS + """
        const small=M.changes('a\\nb\\nc','a\\nx\\nc').map(l=>l.t+':'+l.x);
        const big=Array.from({length:3000},(_,i)=>'line '+i).join('\\n');
        const t0=Date.now();const d=M.diffLines(big.split('\\n'),big.split('\\n').reverse());
        return {small, bigLines:d.length, ms:Date.now()-t0};""")
        self.assertIn("del:b", out["small"])
        self.assertIn("add:x", out["small"])
        self.assertLess(out["ms"], 5000)  # the cell budget degrades to a plain replace, never a hang

    def test_document_preview_preserves_source_lines_and_bounds_large_diffs(self):
        out = _node(HELPERS + r"""
        const a = '---\ndescription: before\n---\n# Heading\n\n-  Keep Markdown';
        const b = '---\ndescription: after\n---\n# Heading\n-  Keep Markdown';
        return { preview:M.documentPreview(a,b), capped:M.documentPreview(a,b,2),
          same:M.documentPreview('', ''), endings:M.documentPreview('a\r\nb', 'a\nb'),
          large:M.documentPreview('a\n'.repeat(2000),'b\n'.repeat(2000)),
          longLine:M.documentPreview('', 'x'.repeat(4097)) };""")
        rows = out["preview"]["rows"]
        self.assertEqual(rows[1]["before"], {"number": 2, "text": "description: before", "kind": "del"})
        self.assertEqual(rows[1]["after"], {"number": 2, "text": "description: after", "kind": "add"})
        self.assertEqual(rows[-1]["before"], {"number": 5, "text": "", "kind": "del"})
        self.assertEqual(out["capped"]["omitted"], 2)
        self.assertEqual(out["same"]["status"], "same")
        self.assertEqual(out["endings"]["status"], "line-endings")
        self.assertEqual(out["large"]["status"], "too-large")
        self.assertEqual(out["longLine"]["status"], "too-large")


@unittest.skipUnless(NODE, "node is required")
class ErrorPresentationTests(unittest.TestCase):
    def test_library_errors_are_actionable_and_private_paths_are_removed(self):
        source = json.dumps(str(V2 / "app.js"))
        out = _node(f"""
        ctx.Vue={{createApp(options){{ctx.options=options;return {{component(){{}},mount(){{}}}};}},markRaw:x=>x}};
        loadJackfield(ctx, {source});
        return ['Traceback /home/private/secret', 'PermissionError: [Errno 13] /home/private/file',
          'invalid archive: ReadError /tmp/private/upload', "skill '/home/private/demo' changed since review"]
          .map(message=>ctx.options.methods.friendly(message));""")
        for text in out:
            self.assertNotRegex(text, r"/home/|/tmp/|Traceback|PermissionError|ReadError|Errno")
        self.assertIn("backup archive", out[2])
        self.assertIn("changed since review", out[3])


@unittest.skipUnless(NODE, "node is required")
class SyncUndoTests(unittest.TestCase):
    def test_sync_undo_requires_complete_unambiguous_snapshot_coverage(self):
        source = json.dumps(str(V2 / "app.js"))
        out = _node(f"""
        let mode='',posts=0;
        ctx.window.SkillManagerDomain={{...ctx.window.SkillManagerDomain,api:async(url,options={{}})=>{{
          if(options.method==='POST'){{posts++;return {{synced:['codex','opencode']}};}}
          if(url.includes('scope=opencode') && mode==='missing-prior') throw new Error('missing');
          return {{disabled:1,decode_error:mode==='binary'?'not valid UTF-8':''}};
        }}}};
        ctx.Vue={{createApp(options){{ctx.options=options;return {{component(){{}},mount(){{}}}};}},markRaw:x=>x}};
        loadJackfield(ctx, {source});
        return (async()=>{{
          const results=[];
          for(mode of ['normal','new-target','missing-prior','post-failure','before-failure','stale','ambiguous','binary']){{
            const counts={{}};posts=0;
            const context={{snapshotIds:async(_name,scope)=>{{
              const call=counts[scope]=(counts[scope]||0)+1;
              if(mode==='before-failure' && call===1) throw new Error('read failed');
              if(mode==='post-failure' && scope==='opencode' && call===2) throw new Error('read failed');
              if(call===1 || (scope==='opencode' && (mode==='new-target' || mode==='stale'))) return ['old'];
              return mode==='ambiguous'?['old','new','another']:['old','new'];
            }}}};
            try{{const result=await ctx.options.methods.doSync.call(context,'sample','claude-code',['codex','opencode']);
              results.push({{mode,posts,undo:!!ctx.options.methods.undoFor.call({{}},'sample',[result])}});
            }}catch(e){{results.push({{mode,posts,error:e.message}});}}
          }}
          return results;
        }})();""")
        self.assertTrue(out[0]["undo"])
        for result in out[1:]:
            with self.subTest(mode=result["mode"]):
                if result["mode"] == "before-failure":
                    self.assertEqual(result["posts"], 0)
                    self.assertEqual(result["error"], "read failed")
                else:
                    self.assertFalse(result["undo"])
                    self.assertEqual(result["posts"], 1)

    def _restore(self, initially_disabled, was_disabled, fail_restore=False):
        source = json.dumps(str(V2 / "app.js"))
        return _node(f"""
        const calls=[];let disabled={json.dumps(initially_disabled)};
        ctx.window.SkillManagerDomain={{...ctx.window.SkillManagerDomain,api:async(url,options={{}})=>{{
          calls.push([options.method||'GET',url]);
          if(url.includes('/enable?')) disabled=false;
          else if(url.includes('/disable?')) disabled=true;
          else if(url.includes('/api/trash/') && {json.dumps(fail_restore)}) throw new Error('restore failed');
          return {{disabled}};
        }}}};
        ctx.Vue={{createApp(options){{ctx.options=options;return {{component(){{}},mount(){{}}}};}},markRaw:x=>x}};
        loadJackfield(ctx, {source});
        return (async()=>{{
          let error='';
          try{{await ctx.options.methods.restoreSyncText('sample','codex','snapshot-1',{json.dumps(was_disabled)});}}
          catch(e){{error=e.message;}}
          return {{disabled,calls,error}};
        }})();""")

    def test_undo_restores_disabled_target_state_after_enabled_source_sync(self):
        out = self._restore(False, True)
        self.assertTrue(out["disabled"])
        self.assertEqual(out["error"], "")
        self.assertIn("/disable?", out["calls"][-1][1])

    def test_undo_temporarily_enables_a_disabled_copy_for_text_restore(self):
        out = self._restore(True, False)
        self.assertFalse(out["disabled"])
        self.assertIn("/enable?", out["calls"][1][1])
        self.assertIn("/api/trash/", out["calls"][2][1])

    def test_failed_undo_restores_state_before_undo_attempt(self):
        out = self._restore(True, False, fail_restore=True)
        self.assertTrue(out["disabled"])
        self.assertEqual(out["error"], "restore failed")
        self.assertIn("/disable?", out["calls"][-1][1])


@unittest.skipUnless(NODE, "node is required")
class BodyLazyLoadTests(unittest.TestCase):
    """The list omits document bodies; a body is read only where one is needed."""

    APP = json.dumps(str(V2 / "app.js"))

    def _app(self, body: str):
        return _node(
            "ctx.Vue={createApp(options){ctx.options=options;return {component(){},mount(){}};},markRaw:x=>x};"
            f"loadJackfield(ctx, {self.APP});"
            + BODY_CONTEXT_JS +
            f"return (async()=>{{{body}}})();")

    def test_a_copy_without_a_body_is_not_an_empty_document(self):
        out = _node(HELPERS + """
        const strip=(r)=>{const c={...r};delete c.body;return c;};
        const full=M.build([rec('a','claude-code')],scopes).skills[0].copies[0];
        const lite=M.build([strip(rec('a','claude-code'))],scopes).skills[0].copies[0];
        const same=M.build([strip(rec('a','claude-code')),strip(rec('a','codex'))],scopes).skills[0].status.label;
        const diff=M.build([strip(rec('a','claude-code')),strip(rec('a','codex',{content_hash:'h2'}))],scopes).skills[0].status.label;
        return {full:{loaded:full.bodyLoaded,body:full.body},lite:{loaded:lite.bodyLoaded,body:lite.body,hash:lite.hash},same,diff};""")
        self.assertTrue(out["full"]["loaded"])
        self.assertEqual(out["full"]["body"], "b")
        self.assertFalse(out["lite"]["loaded"])
        self.assertEqual(out["lite"]["body"], "")
        self.assertEqual(out["lite"]["hash"], "h1")
        # Grouping stays keyed on content_hash, never on body presence.
        self.assertEqual(out["same"], "Working")
        self.assertEqual(out["diff"], "Copies differ")

    def test_one_request_serves_two_concurrent_callers_and_a_changed_hash_refetches(self):
        out = self._app_with_api("""
        const M=ctx.options.methods;
        const context=bodyContext(M,{});
        const copy={name:'a',scope:'codex',hash:'h1',body:'',bodyLoaded:false};
        await Promise.all([M.ensureBodies.call(context,[copy]),M.ensureBodies.call(context,[copy])]);
        const first={calls:calls.slice(),body:copy.body,loaded:copy.bodyLoaded,keyed:context.bodies[M.bodyKey.call(context,copy)]};
        copy.hash='h2';copy.bodyLoaded=false;
        await M.ensureBodies.call(context,[copy]);
        return {first,calls:calls.slice(),second:copy.body};""")
        self.assertEqual(len(out["first"]["calls"]), 1)
        self.assertIn("/api/skills/a?scope=codex", out["first"]["calls"][0])
        self.assertEqual(out["first"]["body"], "DOC 1")
        self.assertTrue(out["first"]["loaded"])
        self.assertEqual(out["first"]["keyed"], "DOC 1")
        self.assertEqual(len(out["calls"]), 2)  # a changed content_hash refetches
        self.assertEqual(out["second"], "DOC 2")

    def _app_with_api(self, body: str):
        return _node(
            "let calls=[];"
            "ctx.window.SkillManagerDomain={...ctx.window.SkillManagerDomain,"
            "api:async(url)=>{calls.push(url);return {name:'a',scope:'codex',body:'DOC '+(calls.length)};}};"
            "ctx.Vue={createApp(options){ctx.options=options;return {component(){},mount(){}};},markRaw:x=>x};"
            f"loadJackfield(ctx, {self.APP});"
            + BODY_CONTEXT_JS +
            f"return (async()=>{{{body}}})();")

    def _app_with_stub(self, api_js: str, body: str):
        """Run ``body`` against app.js whose ``api`` is the caller's stub."""
        return _node(
            "let calls=[];"
            "ctx.window.SkillManagerDomain={...ctx.window.SkillManagerDomain,"
            "api:async(url,options)=>{calls.push(url);" + api_js + "}};"
            "ctx.Vue={createApp(options){ctx.options=options;return {component(){},mount(){}};},markRaw:x=>x};"
            f"loadJackfield(ctx, {self.APP});"
            + BODY_CONTEXT_JS +
            f"return (async()=>{{{body}}})();")

    def test_opening_the_editor_waits_for_the_document(self):
        out = self._app("""
        const M=ctx.options.methods;
        const strip=(r)=>{const c={...r};delete c.body;return c;};
        const copy=Object.assign(strip({name:'a',scope:'codex',description:'d',content_hash:'h1',tokens:5,
          record:{category:'c',version:'',license:'',compatibility:'',allowed_tools:''}}),{body:'# Body\\n',bodyLoaded:false});
        const skill={name:'a',copies:[copy]};
        const editPlaces=new Map([['codex',{scope:'codex',copy,evidence:'original'}]]);
        const context=bodyContext(M,{skill,refCopy:copy,route:{page:'skill'},edit:null,readCopyPath:'',editPlaces,
          toast(){},$nextTick(){},
          ensureBodies:async function(cs){cs[0].body='# Body\\n';cs[0].bodyLoaded=true;this.bodies[this.bodyKey(cs[0])]='# Body\\n';}});
        await M.startEdit.call(context);
        return {body:context.edit&&context.edit.body,name:context.edit&&context.edit.name};""")
        self.assertEqual(out["name"], "a")  # never opens on an unloaded body
        self.assertEqual(out["body"], "# Body\n")

    def test_navigating_away_during_the_fetch_does_not_open_the_editor(self):
        out = self._app("""
        const M=ctx.options.methods;
        const copy={name:'a',scope:'codex',hash:'h1',body:'',bodyLoaded:false,description:'d',record:{}};
        const skill={name:'a',copies:[copy]};
        const context=bodyContext(M,{skill,refCopy:copy,route:{page:'skill'},edit:null,readCopyPath:'',
          toast(){},$nextTick(){},
          ensureBodies:async function(){this.skill={name:'b',copies:[]};this.route={page:'skills'};}});
        await M.startEdit.call(context);
        return context.edit;""")
        self.assertIsNone(out)

    def test_editor_does_not_open_when_the_document_cannot_be_read(self):
        out = self._app("""
        const M=ctx.options.methods;
        const copy={name:'a',scope:'codex',hash:'h1',body:'',bodyLoaded:false,description:'d',record:{}};
        const skill={name:'a',copies:[copy]};
        let toastText='';
        const context=bodyContext(M,{skill,refCopy:copy,route:{page:'skill'},edit:null,readCopyPath:'',
          toast(t){toastText=t;},$nextTick(){},
          ensureBodies:async function(){this.bodyErrors[this.bodyKey(copy)]='The document could not be read.';}});
        await M.startEdit.call(context);
        return {edit:context.edit,toast:toastText};""")
        self.assertIsNone(out["edit"])
        self.assertIn("could not be read", out["toast"])

    def test_partial_editor_additions_leave_the_source_available_for_retry(self):
        out = self._app_with_stub(
            "if(url==='/api/sync'){const request=JSON.parse(options.body);"
            "if(request.from_scope!=='claude-code'||request.edit.expected.content_hash!=='h1'||"
            "request.edit.destinations.codex!=='/physical/codex'||"
            "request.edit.destinations.opencode!=='/h/.config/opencode/skills'||"
            "request.edit.body!=='Edited'||request.to_scopes.join()!=='codex,opencode')throw Error('wrong sync');"
            "return {synced:['codex'],skipped:[{scope:'opencode',reason:'occupied'}],"
            "installed:{codex:{path:'/p/codex/a',tree_hash:'whole-folder'}}};}"
            "if(url==='/api/skills/a?scope=codex'&&options?.method==='DELETE'&&"
            "JSON.parse(options.body).expected.tree_hash==='whole-folder')return {};"
            "throw Error('unexpected request '+url);", HELPERS + """
        const methods=ctx.options.methods, observed=scopes.map(scope=>({...scope,availability:'writable'}));
        observed[1].physical_root='/physical/codex';
        const model=M.build([rec('a','claude-code')],observed), skill=model.skills[0], copy=skill.copies[0];
        let undo, message;
        const context=bodyContext(methods,{m:model,skill,scopes:observed,editTargets:[copy],shortPath:path=>path,
          editError:'',editDirty:true,agentOf:id=>model.agent(id),busy:false,refresh:async()=>{},
          checkEditTarget:async()=>{},toast(text,options){message=text;undo=options.undo;}});
        for(const name of ['editPlaceChanged','editFields','saveNewEditCopies','reportEditResult'])context[name]=methods[name];
        context.editPlaces=ctx.options.computed.editPlaces.call(context);
        const places=[...context.editPlaces.values()];
        const draft={name:'a',copy,desc:'d',baseDesc:'d',body:'Edited',baseBody:'b',metadata:{},baseMetadata:{},places,
          targets:places.map(({scope})=>scope),initialTargets:Object.fromEntries(places.map(({scope,evidence})=>[scope,evidence]))};
        context.edit=draft;
        context.editTargetChanged=ctx.options.computed.editTargetChanged.call(context);
        await methods.saveEdit.call(context);
        await undo();
        return {calls,targets:draft.targets,body:context.edit.body,message,busy:context.busy};""")
        self.assertEqual(out["calls"], ["/api/sync", "/api/skills/a?scope=codex"])
        self.assertEqual(out["targets"], ["claude-code", "opencode"])
        self.assertEqual(out["body"], "Edited")
        self.assertIn("saved to 1 place", out["message"])
        self.assertIn("OpenCode", out["message"])
        self.assertFalse(out["busy"])

    def test_a_linked_copy_is_explained_instead_of_loading_forever(self):
        # A copy this tool refuses to follow is never requested, so waiting for
        # its body would keep "Loading document…" on screen forever.
        out = self._app_with_stub(
            "throw new Error('a linked copy must not be requested: '+url);", """
        const M=ctx.options.methods;
        const copy={name:'a',scope:'codex',state:'link',kind:'linked',hash:'',path:'/p/codex/a',
          body:'',bodyLoaded:false,description:'d',record:{addressable:true}};
        const base=bodyContext(M,{skill:{name:'a',copies:[copy]},refCopy:copy,m:null,editable:true});
        const pending=ctx.options.computed.docPending.call(base);
        const why=ctx.options.computed.docWhy.call(base);
        const context=bodyContext(M,{skill:base.skill,refCopy:copy,m:null,editable:true,docWhy:why});
        const canEdit=ctx.options.computed.canEdit.call(context);
        const editWhy=ctx.options.computed.editWhy.call(context);
        await M.ensureBodies.call(context,[copy]);
        return {pending,why,canEdit,editWhy,calls,loaded:copy.bodyLoaded,body:copy.body};""")
        self.assertFalse(out["pending"])
        self.assertEqual(out["why"]["title"], "Linked outside its folder")
        self.assertIn("does not follow", out["why"]["text"])
        self.assertFalse(out["canEdit"])
        self.assertIn("Linked outside its folder", out["editWhy"])
        self.assertEqual(out["calls"], [])
        self.assertFalse(out["loaded"])
        self.assertEqual(out["body"], "")

    def test_an_unaddressable_copy_is_explained_instead_of_loading_forever(self):
        out = self._app_with_stub(
            "throw new Error('an unaddressable copy must not be requested: '+url);", """
        const M=ctx.options.methods;
        const copy={name:'Bad Name',scope:'codex',state:'broken',kind:'unaddressable',hash:'',
          path:'/p/codex/Bad Name',body:'',bodyLoaded:false,description:'d',record:{addressable:false}};
        const context=bodyContext(M,{skill:{name:'Bad Name',copies:[copy]},refCopy:copy,m:null,editable:false});
        const pending=ctx.options.computed.docPending.call(context);
        const why=ctx.options.computed.docWhy.call(context);
        await M.ensureBodies.call(context,[copy]);
        return {pending,why,calls,loaded:copy.bodyLoaded,canEdit:ctx.options.computed.canEdit.call(context)};""")
        self.assertFalse(out["pending"])
        self.assertEqual(out["why"]["title"], "Unusual folder name")
        self.assertFalse(out["canEdit"])
        self.assertEqual(out["calls"], [])
        self.assertFalse(out["loaded"])

    def test_a_readable_copy_still_waits_for_its_document(self):
        out = self._app("""
        const M=ctx.options.methods;
        const copy={name:'a',scope:'codex',hash:'h1',body:'',bodyLoaded:false,record:{}};
        const context=bodyContext(M,{skill:{name:'a',copies:[copy]},refCopy:copy,m:null});
        return {pending:ctx.options.computed.docPending.call(context),why:ctx.options.computed.docWhy.call(context)};""")
        self.assertTrue(out["pending"])
        self.assertIsNone(out["why"])

    def _duplicates(self, rows: str, records: str):
        return self._app_with_stub(rows, HELPERS + f"""
        const strip=(r)=>{{const c={{...r}};delete c.body;return c;}};
        const m=M.build(({records}).map(strip),scopes);
        const A=ctx.options.methods;
        const copies=m.skills[0].copies;
        const context=bodyContext(A,{{m}});
        await A.ensureBodies.call(context,copies);
        return {{calls,bodies:Object.fromEntries(copies.map(c=>[c.path,c.body])),
          loaded:Object.fromEntries(copies.map(c=>[c.path,c.bodyLoaded])),
          errors:Object.fromEntries(copies.map(c=>[c.path,context.bodyErrors[A.bodyKey(c)]||'']))}};""")

    def test_two_copies_of_one_name_in_one_scope_read_their_own_bodies(self):
        # The list route is name-addressed, so a name read would serve one
        # document to both copies and a diff would compare a body with itself.
        out = self._duplicates(
            "if(url.indexOf('/api/skills?')===0)return ["
            "{name:'a',scope:'opencode',physical_path:'/p/one/a',body:'ONE'},"
            "{name:'a',scope:'opencode',physical_path:'/p/two/a',body:'TWO'}];"
            "throw new Error('unexpected '+url);",
            "[rec('a','opencode',{content_hash:'h1',physical_path:'/p/one/a',path:'/p/one/a'}),"
            "rec('a','opencode',{content_hash:'h2',physical_path:'/p/two/a',path:'/p/two/a'})]")
        self.assertEqual(len(out["calls"]), 1)
        self.assertIn("/api/skills?scope=opencode&q=a", out["calls"][0])
        self.assertEqual(out["bodies"], {"/p/one/a": "ONE", "/p/two/a": "TWO"})
        self.assertEqual(out["loaded"], {"/p/one/a": True, "/p/two/a": True})
        self.assertEqual(out["errors"], {"/p/one/a": "", "/p/two/a": ""})

    def test_an_unmatched_duplicate_copy_keeps_an_error_instead_of_a_guess(self):
        out = self._duplicates(
            "if(url.indexOf('/api/skills?')===0)return ["
            "{name:'a',scope:'opencode',physical_path:'/p/one/a',body:'ONE'}];"
            "throw new Error('unexpected '+url);",
            "[rec('a','opencode',{content_hash:'h1',physical_path:'/p/one/a',path:'/p/one/a'}),"
            "rec('a','opencode',{content_hash:'h2',physical_path:'/p/two/a',path:'/p/two/a'})]")
        self.assertEqual(out["bodies"], {"/p/one/a": "ONE", "/p/two/a": ""})
        self.assertEqual(out["loaded"], {"/p/one/a": True, "/p/two/a": False})
        self.assertEqual(out["errors"]["/p/one/a"], "")
        self.assertIn("could not be matched to a single document", out["errors"]["/p/two/a"])

    def test_a_unique_copy_keeps_the_name_addressed_read(self):
        out = self._duplicates(
            "if(url.indexOf('/api/skills?')===0)return ["
            "{name:'a',scope:'opencode',physical_path:'/p/one/a',body:'ONE'},"
            "{name:'a',scope:'opencode',physical_path:'/p/two/a',body:'TWO'}];"
            "if(url.indexOf('/api/skills/a?scope=codex')===0)return {name:'a',scope:'codex',body:'CX'};"
            "throw new Error('unexpected '+url);",
            "[rec('a','opencode',{content_hash:'h1',physical_path:'/p/one/a',path:'/p/one/a'}),"
            "rec('a','opencode',{content_hash:'h2',physical_path:'/p/two/a',path:'/p/two/a'}),"
            "rec('a','codex',{content_hash:'h3',physical_path:'/p/codex/a',path:'/p/codex/a'})]")
        self.assertEqual(len([u for u in out["calls"] if u.startswith("/api/skills?")]), 1)
        self.assertIn("/api/skills/a?scope=codex", out["calls"])
        self.assertEqual(out["bodies"], {"/p/one/a": "ONE", "/p/two/a": "TWO", "/p/codex/a": "CX"})

    def test_the_editor_survives_an_equal_named_refresh_but_not_a_different_skill(self):
        # A periodic re-read replaces `skill` with a new object for the same
        # name; comparing objects would silently drop the editor.
        out = self._app("""
        const M=ctx.options.methods;
        const run=async(nextSkill)=>{
          const copy={name:'a',scope:'codex',hash:'h1',body:'',bodyLoaded:false,description:'d',record:{}};
          const context=bodyContext(M,{skill:{name:'a',copies:[copy]},refCopy:copy,route:{page:'skill'},edit:null,
            readCopyPath:'',editPlaces:new Map([['codex',{scope:'codex',copy,evidence:'original'}]]),toast(){},$nextTick(){},
            ensureBodies:async function(cs){cs[0].body='# Body\\n';cs[0].bodyLoaded=true;this.skill=nextSkill();}});
          await M.startEdit.call(context);
          return {name:context.edit&&context.edit.name,body:context.edit&&context.edit.body};
        };
        return {same:await run(()=>({name:'a',copies:[]})),other:await run(()=>({name:'b',copies:[]}))};""")
        self.assertEqual(out["same"]["name"], "a")
        self.assertEqual(out["same"]["body"], "# Body\n")
        self.assertIsNone(out["other"]["name"])

    def test_no_reactive_body_check_uses_an_untracked_own_property_test(self):
        app = (V2 / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("hasOwnProperty.call(this.bodies", app)
        self.assertIn("in this.bodies", app)

    def test_a_toggle_toast_states_the_token_effect_and_omits_an_unknown_count(self):
        out = self._app_with_api("""
        const M=ctx.options.methods;
        let toastText='';
        const context={skill:{name:'alpha'},busy:false,fmt:(n)=>Number(n).toLocaleString('en-US'),
          agentOf:()=>({name:'Codex'}),toast(t){toastText=t;},refresh:async()=>{},tokenClause:M.tokenClause};
        const messages={};
        await M.toggleCopy.call(context,{scope:'codex',state:'on',tokens:1240});messages.off=toastText;
        await M.toggleCopy.call(context,{scope:'codex',state:'off',tokens:1240});messages.on=toastText;
        await M.toggleCopy.call(context,{scope:'codex',state:'on',tokens:0});messages.zero=toastText;
        const many={skill:{name:'alpha',copies:[{scope:'codex',state:'off',tokens:1000},{scope:'gemini',state:'off',tokens:240}]},
          busy:false,fmt:context.fmt,agentOf:()=>({name:'Codex'}),toast(t){toastText=t;},refresh:async()=>{},
          tokenClause:M.tokenClause,plural:M.plural};
        await M.allOn.call(many);messages.all=toastText;
        return messages;""")
        self.assertIn("turned off in Codex.", out["off"])
        self.assertIn("frees about 1,240 tokens of that agent's budget", out["off"])
        self.assertIn("uses about 1,240 tokens", out["on"])
        self.assertNotIn("token", out["zero"])
        self.assertIn("turned on everywhere.", out["all"])
        self.assertIn("uses about 1,240 tokens across 2 agents", out["all"])
        for text in out.values():
            self.assertNotIn(". —", text, "a token clause must not follow a full stop with a dash")

    def test_shelf_card_name_is_its_visible_text_starting_with_the_skill(self):
        # axe label-content-name-mismatch (WCAG 2.5.3): the card's aria-label
        # left out visible text ("Off everywhere", tags).  The card now has no
        # aria-label, and the name block precedes the status row in the DOM.
        html = (V2 / "index.html").read_text(encoding="utf-8")
        card = re.search(r'<a v-for="s in g\.shown"[^>]*>(.*?)</a>', html, re.S)
        self.assertIsNotNone(card)
        self.assertNotIn("aria-label", card.group(0).split(">", 1)[0])
        body = card.group(1)
        self.assertLess(body.index('class="sk-b"'), body.index('class="sk-top"'))
        css = (V2 / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.sk-top \{ order: -1;")
        # A library-only skill is never "In 0 tools".
        self.assertIn("'Only in your library'", body)

    def test_shelf_density_is_a_remembered_two_way_choice(self):
        app = (V2 / "app.js").read_text(encoding="utf-8")
        html = (V2 / "index.html").read_text(encoding="utf-8")
        css = (V2 / "styles.css").read_text(encoding="utf-8")
        self.assertIn('density: savedPreference("skillsmgr-v2-density",["comfortable","compact"],"comfortable")', app)
        self.assertIn('density(value) {try{localStorage.setItem("skillsmgr-v2-density",value);}catch(e){}}', app)
        self.assertIn('aria-label="Card density"', html)
        self.assertIn("""<div :class="['shelf', { compact: density === 'compact' }]">""", html)
        # Compact keeps the card's text edge aligned with its status row (16px).
        self.assertIn(".shelf.compact .sk-b { padding: 2px 16px 12px; }", css)
        self.assertIn(".sk-top { order: -1; display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 14px 16px 0;", css)

    def test_shelf_letter_headers_stick_below_the_top_bar(self):
        css = (V2 / "styles.css").read_text(encoding="utf-8")
        top = re.search(r"\.top \{ position: sticky; top: 0; z-index: (\d+); height: (\d+)px;", css)
        sticky = re.search(r"\.cat > \.cat-h \{ position: sticky; top: (\d+)px; z-index: (\d+); background: var\(--bg\)", css)
        self.assertIsNotNone(top)
        self.assertIsNotNone(sticky)
        self.assertEqual(sticky.group(1), top.group(2))  # flush under the bar
        self.assertLess(int(sticky.group(2)), int(top.group(1)))  # never above it

    def test_every_ai_tool_has_its_own_heading_while_ai_is_off(self):
        # The unconfigured fallback heading map once lacked "ai-concise", so
        # that page alone was titled "AI assist" until a model was connected.
        model = (V2 / "model.js").read_text(encoding="utf-8")
        center = (V2 / "ai-center.js").read_text(encoding="utf-8")
        ids = set(re.findall(r'id: "(ai-[a-z-]+)"', model)) - {"ai-settings"}
        self.assertTrue(ids)
        heading_map = re.search(r"<h1[^>]*>\{\{ (\{[^}]*\})\[page\]", center).group(1)
        self.assertEqual(ids - set(re.findall(r"'(ai-[a-z-]+)':", heading_map)), set())

    def test_a_dropped_backup_must_look_like_an_archive(self):
        out = self._app_with_api("""
        const M=ctx.options.methods;const c={importFile:null,importReject:'',clearImportReview:M.clearImportReview};
        const r={};
        M.pickImport.call(c,[{name:'notes.txt'}]);r.bad=[c.importFile,c.importReject];
        M.pickImport.call(c,[{name:'Backup.TAR.GZ'}]);r.good=[c.importFile&&c.importFile.name,c.importReject];
        M.pickImport.call(c,[]);r.none=[c.importFile,c.importReject];
        return r;""")
        self.assertIsNone(out["bad"][0])
        self.assertIn("not a backup file", out["bad"][1])
        self.assertEqual(out["good"], ["Backup.TAR.GZ", ""])  # case-insensitive
        self.assertEqual(out["none"], [None, ""])
        screen = (V2 / "screen-trash.js").read_text(encoding="utf-8")
        self.assertRegex(screen, r'id="imp-file"[^>]*type="file"')
        self.assertIn('@click="$refs.file.click()"', screen)
        self.assertIn('@drop.prevent="dropFiles"', screen)

    def test_startup_list_request_omits_document_bodies(self):
        state = (V2 / "state.js").read_text(encoding="utf-8")
        self.assertIn('api("/api/skills?scope=all&body=0")', state)

    def test_archive_receipt_keeps_server_details_and_blocks_file_changes_during_upload(self):
        out = self._app_with_stub("""
        if(url.includes('preview=1')) return {plan_id:'reviewed',entries:[{name:'good',action:'add',place:'library'}]};
        if(!url.includes('plan_id=reviewed')) throw new Error('A reviewed plan is required');
        return {imported:['good'], skipped:['failed: Recovery files retained at /fixture/backup'],
          skipped_full:['templates/existing.md'], restored_trash:['copy'],
          restored_templates:['one.md','two.md'], restored_catalog:true};""", """
        const methods=ctx.options.methods;
        const file={name:'receipt.tar.gz'};
        ctx.document={getElementById(){return null;}};
        const c={importFile:file,importFull:true,importForce:true,busy:false,
          archiveImportRequest:methods.archiveImportRequest,clearImportReview:methods.clearImportReview,
          refresh:async()=>{},friendly:message=>message,archiveImportSummary:methods.archiveImportSummary};
        await methods.doImport.call(c);
        const callsBeforePreview=calls.length;
        await methods.previewImport.call(c);
        const ongoing=methods.doImport.call(c);
        methods.pickImport.call(c,[{name:'different.zip'}]);
        const unchanged=c.importFile===file;
        await methods.doImport.call(c);
        await ongoing;
        return {result:c.importResult, summary:methods.archiveImportSummary(c.importResult),
          unchanged,busy:c.busy,file:c.importFile,announced:c.live,calls,callsBeforePreview};""")
        self.assertTrue(out["unchanged"])
        self.assertFalse(out["busy"])
        self.assertIsNone(out["file"])
        self.assertEqual(out["callsBeforePreview"], 0)
        self.assertEqual(out["calls"], ["/api/import?filename=receipt.tar.gz&force=1&full=1&preview=1",
                                       "/api/import?filename=receipt.tar.gz&force=1&full=1&plan_id=reviewed"])
        self.assertEqual(out["summary"], "1 skill imported. Restored 1 trash entry, 2 templates, catalog metadata. 2 skipped.")
        self.assertEqual(out["announced"], out["summary"])
        self.assertEqual(out["result"]["skipped"], ["failed: Recovery files retained at /fixture/backup"])


@unittest.skipUnless(NODE, "node is required")
class TransportTests(unittest.TestCase):
    """R9: mutating requests declare JSON; forms and files keep their own type."""

    def test_content_type_is_added_only_where_it_belongs(self):
        out = _node("""
        const D = ctx.window.SkillManagerDomain, ct = (o) => (o.headers || {})["Content-Type"] || null;
        return {
          get: ct(D.withJsonType({})),
          bodylessPost: ct(D.withJsonType({ method: "POST" })),
          del: ct(D.withJsonType({ method: "DELETE" })),
          kept: ct(D.withJsonType({ method: "POST", headers: { "content-type": "text/x" } })) ,
          keptLower: D.withJsonType({ method: "POST", headers: { "content-type": "text/x" } }).headers["content-type"],
          blob: ct(D.withJsonType({ method: "PUT", body: new Blob(["x"]) })),
          form: ct(D.withJsonType({ method: "POST", body: new FormData() })),
        };""")
        self.assertIsNone(out["get"])
        self.assertEqual(out["bodylessPost"], "application/json")
        self.assertEqual(out["del"], "application/json")
        self.assertIsNone(out["kept"])
        self.assertEqual(out["keptLower"], "text/x")
        self.assertIsNone(out["blob"])
        self.assertIsNone(out["form"])


class InterfaceSourceTests(unittest.TestCase):
    def setUp(self):
        self.html = (V2 / "index.html").read_text(encoding="utf-8")
        self.css = (V2 / "styles.css").read_text(encoding="utf-8")
        self.app = (V2 / "app.js").read_text(encoding="utf-8")

    def test_no_inline_script_and_no_external_resource(self):
        self.assertNotRegex(self.html, r"<script(?![^>]*\bsrc=)[^>]*>")
        for text in (self.html, self.css, self.app, *((V2 / f).read_text(encoding="utf-8")
                      for f in ("tokens.css", "system.css", "layout.css", "tools.css"))):
            self.assertNotRegex(text, r"https?://(?!www\.w3\.org)", "no runtime fetch from another origin")

    def test_html_is_injected_only_from_the_escaped_renderer_or_constant_icons(self):
        sites = re.findall(r'v-html="([^"]+)"', self.html + self.app)
        self.assertEqual(sorted(set(sites)), ["docHtml", "path", "renderDoc(edit.body)", "themeIcon"])

    def test_every_asset_it_references_exists(self):
        for src in re.findall(r'\s(?:src|href)="([^"#]+)"', self.html):
            if src.startswith(("/", "http", "#", "data:")):
                continue
            self.assertTrue((V2 / src).resolve().exists(), f"missing {src}")
        for rel in re.findall(r'url\("([^")]+\.woff2)"\)', (V2 / "tokens.css").read_text(encoding="utf-8")):
            self.assertTrue((V2 / rel).exists(), f"missing font {rel}")

    def test_tooling_uses_only_the_documented_api_families(self):
        modules = self.app + "".join((V2 / name).read_text(encoding="utf-8")
                                     for name in ("state.js", "library-tools.js", "tool-center.js"))
        called = set(re.findall(r"[\"'`](/api/[a-z-]+)", modules))
        self.assertLessEqual(called, {"/api/scopes", "/api/skills", "/api/history", "/api/sync", "/api/trash", "/api/import", "/api/export", "/api/catalog", "/api/templates", "/api/batch", "/api/install", "/api/doctor", "/api/stats", "/api/tokens", "/api/workspaces", "/api/source-updates", "/api/validate", "/api/ai", "/api/tracking"})
        self.assertIn("/api/templates", called)
        self.assertIn("/api/batch", called)

    def test_both_themes_meet_contrast_for_text_and_controls(self):
        from check_design_tokens import contrast

        sheet = (V2 / "tokens.css").read_text(encoding="utf-8")
        light_sheet, dark_sheet = sheet.split(':root[data-theme="dark"] {', 1)
        colour = re.compile(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6});")
        light = dict(colour.findall(light_sheet))
        dark = {**light, **dict(colour.findall(dark_sheet))}
        aliases = dict(re.findall(r"(--[a-z0-9-]+):\s*var\((--[a-z0-9-]+)\);", self.css))
        pairs = [
            (fg, bg, 4.5)
            for fg in ("--ink", "--ink-2", "--muted")
            for bg in ("--bg", "--surface", "--sunken", "--paper", "--tree-bg")
        ]
        pairs += [("--ok", "--ok-bg", 4.5), ("--warn", "--warn-bg", 4.5),
                  ("--bad", "--bad-bg", 4.5), ("--off", "--off-bg", 4.5),
                  ("--line-strong", "--surface", 3.0)]
        for theme, tokens in (("light", light), ("dark", dark)):
            for foreground, background, minimum in pairs:
                with self.subTest(theme=theme, foreground=foreground, background=background):
                    self.assertGreaterEqual(contrast(tokens[aliases.get(foreground, foreground)],
                                                     tokens[aliases.get(background, background)]),
                                            minimum)

    def test_phone_navigation_reaches_every_page(self):
        nav = self.html[self.html.index('class="bottomnav sm-tabs jf-phone"'):]
        nav = nav[: nav.index("</nav>")]
        self.assertIn('v-for="place in places"', nav)
        self.assertIn(':href="place.path"', nav)
        palette = (V2 / "palette.js").read_text(encoding="utf-8")
        for page in ("skills", "attention", "trash", "advanced"):
            self.assertIn(f'path: "#/{page}"', palette)

    def test_reduced_motion_is_honoured(self):
        self.assertIn("prefers-reduced-motion", self.css)

    def test_every_dialog_and_nav_target_is_reachable(self):
        self.assertIn('v-for="place in places"', self.html)
        self.assertIn(':href="place.path"', self.html)
        self.assertIn('href="#/skills?view=agents"', self.html)
        self.assertIn('href="#/skills?view=map"', self.html)
        self.assertIn('<jf-sheet labelled-by="dlg-t"', self.html)
        self.assertIn('role="dialog" aria-modal="true"', (V2 / "ui-core.js").read_text(encoding="utf-8"))



class ServedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os

        from skillsmgr.store import Store
        from skillsmgr.webapp import WebAppServer

        # Isolate HOME as well as the data root: scope-aware routes read the
        # real agent folders otherwise (see test_web_client_contracts).
        cls._old = {k: os.environ.get(k) for k in ("HOME", "SKILLS_MANAGER_DATA")}
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = cls.tmp.name
        data = Path(cls.tmp.name) / "data"
        data.mkdir(mode=0o700)
        os.environ["SKILLS_MANAGER_DATA"] = str(data)
        cls.store = Store()
        cls.store.init_db()
        cls.server = WebAppServer(cls.store, port=0)
        cls.port = cls.server.httpd.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        import os

        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.httpd.server_close()
        cls.tmp.cleanup()
        for key, value in cls._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _get(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Content-Type", ""), exc.read()

    def test_body_zero_list_projection_keeps_identity_and_size_fields(self):
        import os

        # A global Store row never carries a body; an agent-scope row does, so
        # this uses a scope instance to prove the flag actually removes one.
        folder = Path(os.environ["HOME"]) / ".claude" / "skills" / "payload-instance"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(
            "---\nname: payload-instance\ndescription: Prove the list projection.\n---\n\n# Body\n\nText.\n",
            encoding="utf-8")
        try:
            status, _, raw = self._get("/api/skills?scope=all&body=1")
            self.assertEqual(status, 200)
            full = next(r for r in json.loads(raw) if r.get("name") == "payload-instance")
            self.assertIn("body", full)
            status, _, raw = self._get("/api/skills?scope=all&body=0")
            self.assertEqual(status, 200)
            row = next(r for r in json.loads(raw) if r.get("name") == "payload-instance")
            self.assertNotIn("body", row)
            self.assertIn("content_hash", row)
            self.assertIn("tokens", row)
        finally:
            shutil.rmtree(folder.parent, ignore_errors=True)

    def test_the_interface_and_its_assets_are_served(self):
        for path, kind in (("/", "text/html"), ("/app.js", "javascript"), ("/model.js", "javascript"),
                           ("/state.js", "javascript"), ("/router.js", "javascript"),
                           ("/palette.js", "javascript"), ("/ui-core.js", "javascript"),
                           ("/screen-not-found.js", "javascript"),
                           ("/styles.css", "text/css"), ("/tokens.css", "text/css"),
                           ("/system.css", "text/css"), ("/layout.css", "text/css"),
                           ("/library-tools.js", "javascript"),
                           ("/tool-center.js", "javascript"), ("/ai-center.js", "javascript"),
                           ("/ai-diagnostic.js", "javascript"), ("/tools.css", "text/css"),
                           ("/domain.js", "javascript"), ("/preferences.js", "javascript"),
                           ("/logo.svg", "image/svg+xml"), ("/favicon.svg", "image/svg+xml"),
                           ("/static/fonts/IBMPlexSans-400-latin.woff2", "font/woff2"),
                           # Asset links saved while the interface lived at /v2/.
                           ("/v2/app.js", "javascript")):
            status, ctype, body = self._get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(kind, ctype, path)
            self.assertTrue(body, path)

    def test_traversal_out_of_the_interface_directory_is_refused(self):
        for path in ("/../../pyproject.toml", "/%2e%2e/%2e%2e/pyproject.toml", "/..%2f..%2fpyproject.toml",
                     "/v2/../../pyproject.toml", "/v2/%2e%2e/%2e%2e/pyproject.toml", "/v2/..%2f..%2fpyproject.toml"):
            status, _, body = self._get(path)
            self.assertEqual(status, 404, path)
            self.assertNotIn(b"[project]", body)

    def test_the_interface_is_served_at_the_root_and_the_classic_one_is_gone(self):
        status, _, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b'src="model.js"', body)
        self.assertNotIn(b"/classic/", body)
        for retired in ("index.html.orig", "classic/app.js", "classic/styles.css"):
            with self.subTest(path=retired):
                self.assertEqual(self._get("/" + retired)[0], 404)

    def test_retired_entry_points_redirect_with_a_status_every_supported_urllib_follows(self):
        """Python 3.10's ``HTTPRedirectHandler`` follows 301/302/303/307 only.

        A 308 at an entry point made every urllib client on 3.10 raise
        ``HTTPError`` instead of reaching the UI (CI ``unit (py3.10)`` on
        ``61355a2``). ``/`` itself is served directly, with no redirect.
        """
        import http.client

        followed_by_py310 = {301, 302, 303, 307}
        for path in ("/index.html", "/v2", "/v2/", "/classic", "/classic/"):
            with self.subTest(path=path):
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                try:
                    connection.request("GET", path)
                    response = connection.getresponse()
                    response.read()
                    self.assertIn(response.status, followed_by_py310)
                    self.assertNotIn("immutable", response.getheader("Cache-Control") or "")
                finally:
                    connection.close()

    def test_entry_redirects_keep_queries_and_use_only_fixed_local_paths(self):
        import http.client

        # Retired addresses (the interface's old /v2/ home and the removed
        # classic interface) open the interface at /, keeping the query string;
        # browsers carry the #fragment route across the redirect.
        for path, expected, status in (
                ("/index.html?x=1", "/?x=1", 307), ("/v2?x=1", "/?x=1", 307),
                ("/v2/?window=claude&x=1", "/?window=claude&x=1", 307), ("/v2/index.html", "/", 307),
                ("/classic?x=1", "/?x=1", 307), ("/classic/", "/", 307), ("/classic/index.html", "/", 307)):
            with self.subTest(path=path):
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                try:
                    connection.request("GET", path)
                    response = connection.getresponse()
                    self.assertEqual(response.status, status)
                    self.assertEqual(response.getheader("Location"), expected)
                    self.assertEqual(response.read(), b"")
                finally:
                    connection.close()


if __name__ == "__main__":
    unittest.main()


class LazyBodyReactivityContracts(unittest.TestCase):
    """The reader/editor readiness checks must be reactive.

    `Object.prototype.hasOwnProperty.call(reactiveObj, key)` is not tracked by
    Vue's proxy (no getOwnPropertyDescriptor trap), so a computed that used it
    never re-ran when a lazily fetched body arrived: the skill page's Edit
    button stayed disabled in a real browser while every unit test passed.
    """

    def test_body_accessors_use_a_tracked_membership_test(self):
        source = (ROOT / "skillsmgr" / "webui" / "app.js").read_text(encoding="utf-8")
        start = source.index("bodyReady(c)")
        end = source.index("bodyErrorOf(c)")
        accessors = source[start:end]
        self.assertNotIn("hasOwnProperty.call(this.bodies", accessors)
        self.assertIn("in this.bodies", accessors)

