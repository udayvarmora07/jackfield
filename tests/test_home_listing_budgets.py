"""V2 Home renders existing listing evidence independently of inventory loading."""

import unittest

from tests.test_v2_interface_contracts import NODE, V2, _node


@unittest.skipUnless(NODE, "node is required")
class HomeListingBudgetTests(unittest.TestCase):
    def run_component(self, body):
        import json

        return _node("""
        ctx.components={};
        ctx.Vue={createApp(){return {component(name,options){ctx.components[name]=options;return this;},mount(){}};},markRaw:x=>x};
        const requests=[];
        ctx.window.SkillManagerDomain={...ctx.window.SkillManagerDomain,
          api:url=>new Promise((resolve,reject)=>requests.push({url,resolve,reject}))};
        """ + f"vm.runInContext(fs.readFileSync({json.dumps(str(V2 / 'app.js'))},'utf8'),ctx);" + """
        const C=ctx.components['listing-budgets'];
        if(!C)return {missing:true};
        const c={...C.data(),...C.methods};
        """ + body)

    def test_existing_report_is_read_without_blocking_or_mutating_inventory(self):
        result = self.run_component("""
        return (async()=>{
          const loading=c.load();
          const during=c.loading;
          requests[0].resolve({hygiene:{claude_listing:{consumer:'claude-code',instances_observed:1,listing_chars:42,
            budget:{budget_chars_estimate:40000},confidence:'partial',status:'within_budget'},
            codex_listing:{consumer:'codex',instances_observed:1,listing_tokens_estimate:20,
              budget:{budget_tokens:20000},status:'within_budget'}}});
          await loading;
          return {during,loading:c.loading,error:c.error,requests:requests.map(r=>r.url),
            sections:C.computed.sections.call(c)};
        })();""")
        self.assertFalse(result.get("missing"), result)
        self.assertTrue(result["during"])
        self.assertFalse(result["loading"])
        self.assertEqual(result["error"], "")
        self.assertEqual(result["requests"], ["/api/doctor?scope=all&hygiene=1"])
        self.assertEqual([s["label"] for s in result["sections"]], ["Claude Code", "Codex"])
        self.assertEqual(result["sections"][0]["used"], 42)
        self.assertEqual(result["sections"][0]["budget"], 40000)
        self.assertEqual(result["sections"][0]["status"], "Within estimate · partial evidence")

    def test_failed_read_can_retry_and_late_reads_never_replace_newer_evidence(self):
        result = self.run_component("""
        return (async()=>{
          const old=c.load(), newer=c.load();
          requests[1].resolve({hygiene:{claude_listing:{instances_observed:1,listing_chars:30,
            budget:{budget_chars_estimate:10},status:'over_budget_estimate'},
            codex_listing:{instances_observed:0,status:'no_instances'}}});
          await newer;
          requests[0].reject(new Error('private /home/secret'));
          await old;
          const retained=C.computed.sections.call(c)[0],oldError=c.error;
          const failed=c.load();requests[2].reject(new Error('private /home/secret'));await failed;
          const error=c.error;
          const retry=c.load();requests[3].resolve({hygiene:{
            claude_listing:{instances_observed:0,status:'no_instances'},
            codex_listing:{instances_observed:0,status:'no_instances'}}});await retry;
          return {retained,oldError,error,afterRetry:c.error,loading:c.loading,
            empty:C.computed.sections.call(c)};
        })();""")
        self.assertFalse(result.get("missing"), result)
        self.assertEqual(result["retained"]["used"], 30)
        self.assertIn("Over", result["retained"]["status"])
        self.assertEqual(result["oldError"], "")
        self.assertIn("Retry", result["error"])
        self.assertNotIn("/home", result["error"])
        self.assertEqual((result["afterRetry"], result["loading"], result["empty"]), ("", False, []))

    def test_unknown_budget_and_absent_instances_do_not_look_like_a_pass(self):
        result = self.run_component("""
        c.report={claude_listing:{instances_observed:1,listing_chars:42,
          budget:{budget_chars_estimate:40000},confidence:'partial',status:'unknown'},
          codex_listing:{instances_observed:0,status:'no_instances'}};
        return C.computed.sections.call(c);""")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["budget"])
        self.assertIn("unknown", result[0]["status"])

    def test_all_excluded_entries_and_unrecognized_status_are_not_within_budget(self):
        result = self.run_component("""
        c.report={codex_listing:{instances_observed:3,listed_skills:0,
          listing_tokens_estimate:0,status:'no_instances',budget:{budget_tokens:8000}},
          claude_listing:{instances_observed:1,status:'unexpected',budget:{budget_chars_estimate:10}}};
        return C.computed.sections.call(c).map(s=>s.status);""")
        self.assertEqual(result, ["Budget unknown", "No model-visible entries"])

    def test_numbers_follow_the_selected_display_locale(self):
        result = self.run_component("c.locale='en-IN';return c.fmtN(1234567);")
        self.assertEqual(result, "12,34,567")

    def test_unmounted_home_ignores_its_pending_result(self):
        result = self.run_component("""
        return (async()=>{const pending=c.load();C.beforeUnmount.call(c);
          requests[0].resolve({hygiene:{claude_listing:{instances_observed:1}}});
          await pending;return {report:c.report,error:c.error};})();""")
        self.assertEqual(result, {"report": None, "error": ""})

    def test_missing_report_sections_offer_retry_instead_of_claiming_no_instances(self):
        result = self.run_component("""
        return (async()=>{const pending=c.load();requests[0].resolve({hygiene:{}});
          await pending;return {error:c.error,report:c.report};})();""")
        self.assertTrue(result["error"])
        self.assertIsNone(result["report"])
