"""Behavior contracts for the shell router and shared command search."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


def run_js(body):
    script = r"""
const fs=require('fs'),vm=require('vm');
const ctx={window:{Jackfield:{},SkillsV2Model:{toolIds:['install','settings'],toolItems:[]}}, URLSearchParams,
  location:{hash:''},history:{state:null,replaceState(_s,_t,href){ctx.location.hash=href}}};
vm.createContext(ctx);
for(const f of ['router.js','palette.js']) vm.runInContext(fs.readFileSync('skillsmgr/webui/'+f,'utf8'),ctx);
const R=ctx.window.Jackfield.router,P=ctx.window.Jackfield.palette;
""" + body
    result = subprocess.run(['node', '-e', script], cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


@unittest.skipUnless(shutil.which('node'), 'node is required')
class ShellRouteTests(unittest.TestCase):
    def test_architecture_route_tables_match_the_router(self):
        spec = (ROOT / 'docs/redesign-build/04-frontend-architecture.md').read_text(encoding='utf-8')
        canonical, legacy = spec.split('## Routes\n', 1)[1].split('**[SPEC]** Legacy redirects', 1)

        def example(href):
            return href.replace('<name>', 'edit').replace('<tool-id>', 'install').replace('<id>', 'install')

        patterns = re.findall(r'^\| `(#/[^\x60]*)` \| ', canonical, re.M)
        canonical_hrefs = [example(href) for href in patterns]
        aliases = [[example(old), example(new)] for old, new in re.findall(
            r'^\| `(#/[^\x60]*)`(?:, [^|]+)? \| `(#/[^\x60]*)` \|', legacy.split('## State')[0], re.M)]
        result = run_js(f"""
const canonical={json.dumps(canonical_hrefs)}.map(href=>R.parseRoute(href));
const legacy={json.dumps(aliases)}.map(([old, expected])=>[R.parseRoute(old).href,expected]);
console.log(JSON.stringify({{canonical,legacy}}));""")
        self.assertGreaterEqual(len(canonical_hrefs), 11)
        self.assertGreaterEqual(len(aliases), 8)
        self.assertTrue(all(route['page'] != 'missing' for route in result['canonical']))
        self.assertEqual([route['href'] for route in result['canonical']], canonical_hrefs)
        for actual, expected in result['legacy']:
            self.assertEqual(actual, expected)

    def test_aliases_replace_and_preserve_query(self):
        rows = run_js("""
const cases=['','#/home','#/map','#/inbox','#/recovery','#/tools','#/tools/settings',
 '#/tools/install','#/skill/a%20b/edit?view=file'];
const rows=cases.map(hash=>{ctx.location.hash=hash;const route=R.current();R.replace(route.href);return {route,hash:ctx.location.hash}});
console.log(JSON.stringify(rows));""")
        expected = ['#/skills', '#/skills', '#/skills', '#/attention', '#/trash', '#/advanced',
                    '#/settings', '#/advanced/install', '#/skills/a%20b/edit?view=file']
        self.assertEqual([r['hash'] for r in rows], expected)
        self.assertEqual(rows[-1]['route']['name'], 'a b')
        self.assertTrue(rows[-1]['route']['file'])

    def test_url_state_and_malformed_names(self):
        result = run_js("""
const hashes=['#/skills?view=agents&q=a+b&agent=codex&only=problems&sel=one',
 '#/skills?view=map','#/skills/%','#/skills/%2F','#/skills/%5c','#/skills/..',
 '#/skills/%00','#/skills/one/edit/extra','#/advanced/unknown'];
console.log(JSON.stringify(hashes.map(h=>R.parseRoute(h))));""")
        self.assertEqual({k: result[0][k] for k in ('page','search','agent','only','selected')},
                         {'page':'skills','search':'a b','agent':'codex','only':'problems','selected':'one'})
        self.assertEqual(result[0]['href'], '#/skills?q=a+b&agent=codex&only=problems&sel=one')
        self.assertIsNone(result[0]['view'])
        self.assertEqual(result[1]['page'], 'skills')
        self.assertEqual(result[1]['href'], '#/skills')
        self.assertTrue(all(route['page'] == 'missing' for route in result[2:]))
        retired = run_js("""
const views=['shelf','instances','unknown'];
console.log(JSON.stringify(views.map(view=>R.parseRoute('#/skills?view='+view+'&q=a%20b'))));""")
        for route in retired:
            self.assertEqual(route['page'], 'skills')
            self.assertIsNone(route['view'])
            self.assertEqual(route['search'], 'a b')
            self.assertEqual(route['href'], '#/skills?q=a+b')

    def test_palette_search_respects_disabled_tools_and_encodes_names(self):
        result = run_js("""
const skills=[{name:'alpha beta',description:'Writer',category:'text',tools:[{scope:'codex'}]}];
const tools=[{id:'install',commandLabel:'Install a skill',name:'Install',text:'Add'},
{id:'hidden',commandLabel:'Hidden command',name:'Hidden',text:'Hidden'}];
const search=q=>P.search(q,skills,x=>x,tools,id=>id!=='hidden');
console.log(JSON.stringify({skill:search('alpha'),hidden:search('hidden'),install:search('install'),
 guess:P.closeName('alpah', [{name:'alpha',description:''}])}));""")
        self.assertEqual(result['skill'][0]['items'][0]['path'], '#/skills/alpha%20beta')
        self.assertEqual(result['skill'][0]['items'][1]['path'], '#/skills?q=alpha')
        self.assertEqual(result['hidden'], [])
        self.assertTrue(any(item['path'] == '#/advanced/install' for group in result['install'] for item in group['items']))
        self.assertEqual(result['guess']['name'], 'alpha')

    def test_app_has_no_branches_for_retired_skills_views(self):
        webui = ROOT / 'skillsmgr' / 'webui'
        for name in ('app.js', 'index.html'):
            with self.subTest(name=name):
                source = (webui / name).read_text(encoding='utf-8')
                self.assertNotRegex(source, r'\b(?:route\.view|libraryView)\b')
