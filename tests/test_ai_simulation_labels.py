"""Routing UI preserves the simulation boundary before and after a run."""
import shutil
import unittest

from tests.test_v2_tool_behaviors import run_node


@unittest.skipUnless(shutil.which('node'), 'Node is required')
class SimulationLabelTests(unittest.TestCase):
    def test_trigger_and_budget_views_keep_native_runtime_limit_visible(self):
        result = run_node(r"""
          vm.runInContext(fs.readFileSync(V2+'/ai-center.js','utf8'),ctx);
          const component=ctx.window.SkillsV2AiCenter;
          const h=mount(component);
          const template=component.template;
          const trigger=template.split("page==='ai-trigger'")[1].split("page==='ai-")[0];
          const budget=template.split("page==='ai-budget'")[1].split("page==='ai-")[0];
          return {notice:h.routingNotice,trigger,budget,
            verdict:h.verdictLabel('fires'),never:h.verdictLabel('never-fires'),
            descriptions:ctx.window.SkillsV2Model.toolItems.filter(t=>['ai-trigger','ai-budget'].includes(t.id)).map(t=>t.text)};
        """)
        self.assertIn('Model simulation only', result['notice'])
        self.assertIn('does not run', result['notice'])
        for view in ('trigger', 'budget'):
            self.assertGreaterEqual(result[view].count('{{routingNotice}}'), 2)
        self.assertIn('simulation', result['verdict'])
        self.assertIn('simulation', result['never'])
        self.assertNotIn('All fire', result['trigger'])
        self.assertNotIn('Safe versions', result['budget'])
        self.assertTrue(all('simulat' in value.lower() for value in result['descriptions']))

    def test_home_keeps_known_codex_budget_separate_from_unknown_metadata_listing(self):
        result = run_node(r"""
          const components={};ctx.Vue={createApp(def){return {component(name,definition){components[name]=definition;return this},mount(){}}},markRaw:v=>v};
          loadJackfield(ctx, V2+'/app.js');
          const component=components['listing-budgets'];
          const h=mount(component,{report:{codex_listing:{instances_observed:2,status:'unknown',confidence:'partial',
            listing_tokens_estimate:44,budget:{budget_tokens:8000,basis:'User cap'},unknown_metadata:{total:1}}}});
          return h.sections[0];
        """)
        self.assertEqual(result['used'], 44)
        self.assertEqual(result['budget'], 8000)
        self.assertTrue(result['subtotal'])
        self.assertIn('Listing unknown', result['status'])
        self.assertNotIn('Budget unknown', result['status'])
