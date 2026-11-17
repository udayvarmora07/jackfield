"""Discovery rows describe observed folder matches, never native activation."""
import unittest
import shutil

from tests.test_v2_tool_behaviors import run_node


@unittest.skipUnless(shutil.which('node'), 'Node is required')
class ConsumerDiscoveryTests(unittest.TestCase):
    def test_shared_folder_matches_multiple_consumers_without_a_loading_verdict(self):
        result = run_node(r"""
          const f=ctx.window.SkillsV2Model.consumerDiscovery;
          const record={name:'demo',scope:'agents',physical_path:'/h/.agents/skills/demo',disabled:false};
          const roots=[{id:'agents',kind:'agent',path:'/h/.agents/skills'}];
          const adapter=(id,scope)=>({id,label:id,candidate_roots:[{scope}],precedence:{status:'unknown',evidence:'https://example.test/skills'}});
          return f('demo',[record],roots,[adapter('codex','agents'),adapter('zed','agents'),adapter('claude-code','claude-code')]);
        """)
        self.assertEqual([row['observed'] for row in result['rows']], [1, 1, 0])
        self.assertTrue(all(row['declarations'] == [] for row in result['rows']))
        self.assertNotIn('effective', result['rows'][0])

    def test_compatibility_and_project_roots_keep_exact_scope_boundaries(self):
        result = run_node(r"""
          const scopes=[{id:'codex',kind:'agent',path:'/h/.codex/skills'},
            {id:'project',kind:'project',path:'/p/.codex/skills'},
            {id:'unrelated',kind:'agent',path:'/h/.codex/skills-backup'}];
          const records=scopes.map(s=>({name:'demo',scope:s.id,path:s.path+'/demo'}));
          const adapters=[{id:'cursor',candidate_roots:[{home_path:'.codex/skills'}]},
            {id:'project-reader',candidate_roots:[{relative_path:'.codex/skills'}]}];
          return ctx.window.SkillsV2Model.consumerDiscovery('demo',records,scopes,adapters);
        """)
        self.assertEqual([row['observed'] for row in result['rows']], [1, 1])

    def test_physical_aliases_deduplicate_counts_and_native_evidence_is_consumer_specific(self):
        result = run_node(r"""
          const records=[{name:'demo',scope:'one',consumer:'first',physical_path:'/shared/demo',disabled:true,native_state:{sources:[{declared:'off'}]}},
            {name:'demo',scope:'two',consumer:'second',physical_path:'/shared/demo',native_state:{sources:[{declared:'deny'}]}},
            {name:'demo',scope:'two',consumer:'second',physical_path:'/other/demo',malformed:true}];
          records[0].path='/one/demo';records[1].path='/two/demo';records[2].path='/two/second-copy';
          const scopes=[{id:'one',path:'/one'},{id:'two',path:'/two'}];
          const adapters=['first','second'].map(id=>({id,candidate_roots:[{scope:'one'},{scope:'two'}]}));
          return ctx.window.SkillsV2Model.consumerDiscovery('demo',records,scopes,adapters);
        """)
        self.assertEqual([row['observed'] for row in result['rows']], [2, 2])
        self.assertEqual(result['rows'][0]['declarations'], ['off'])
        self.assertEqual(result['rows'][1]['declarations'], ['deny'])
        self.assertEqual(result['rows'][1]['unreadable'], 1)

    def test_unknown_inputs_bounds_and_untrusted_source_scheme(self):
        result = run_node(r"""
          const f=ctx.window.SkillsV2Model.consumerDiscovery;
          const many=Array.from({length:33},(_,i)=>({id:String(i),candidate_roots:Array.from({length:65},()=>({path_known:false})),precedence:{evidence:'javascript:alert(1)'}}));
          return {empty:f('demo',null,null,null),large:f('demo',Array(10001).fill({name:'demo',scope:'none'}),[],many),
            beyond:f('last',[...Array(10000).fill({name:'other'}),{name:'last'}],[],[])};
        """)
        self.assertEqual(result['empty']['rows'], [])
        self.assertEqual(len(result['large']['rows']), 32)
        self.assertTrue(result['large']['partial'])
        self.assertEqual(result['large']['instances_observed'], 10000)
        self.assertTrue(all(row['source'] == '' for row in result['large']['rows']))
        self.assertTrue(result['beyond']['partial'])
        self.assertEqual(result['beyond']['instances_observed'], 0)

    def test_workspaces_component_uses_current_inventory_and_clears_stale_catalog(self):
        result = run_node(r"""
          const h=mount(ctx.window.SkillsV2ToolCenter,{page:'workspaces',discoveryName:'demo',
            records:[{name:'demo',scope:'agents',path:'/shared/demo'}],scopes:[{id:'agents',path:'/shared'}],
            workspace:{adapters:[{id:'codex',candidate_roots:[{scope:'agents'}]}]}});
          const before=h.discoveryEvidence.rows[0].observed;
          h.changeProject('/new');return {before,after:h.discoveryEvidence.rows};
        """)
        self.assertEqual(result['before'], 1)
        self.assertEqual(result['after'], [])

    def test_flat_roots_do_not_match_nested_instances_or_sibling_prefixes(self):
        result = run_node(r"""
          const records=[{name:'demo',scope:'agents',path:'/h/.agents/skills/group/demo'},
            {name:'demo',scope:'agents',path:'/h/.agents/skills-backup/demo'},
            {name:'demo',scope:'agents',path:'/h/.agents/skills/../outside/demo'}];
          const scopes=[{id:'agents',kind:'agent',path:'/h/.agents/skills'}];
          const adapters=[{id:'flat',candidate_roots:[{scope:'agents'}]},
            {id:'recursive',candidate_roots:[{scope:'agents',recursive:true}]}];
          return ctx.window.SkillsV2Model.consumerDiscovery('demo',records,scopes,adapters);
        """)
        self.assertEqual([row['observed'] for row in result['rows']], [0, 1])

    def test_scope_alias_suppressed_by_inventory_is_unverified_instead_of_absent(self):
        result = run_node(r"""
          const scopes=[{id:'claude-code',kind:'agent',path:'/home/user/.claude/skills'}];
          const records=[{name:'demo',scope:'claude-code',path:'/home/user/.claude/skills/demo'}];
          const adapters=[{id:'codex',candidate_roots:[{scope:'agents'}]}];
          return ctx.window.SkillsV2Model.consumerDiscovery('demo',records,scopes,adapters);
        """)
        self.assertTrue(result['partial'])
        self.assertTrue(result['rows'][0]['scope_mapping_unknown'])
        self.assertEqual(result['rows'][0]['observed'], 0)
