"""Synthetic native settings observations; no host settings are touched."""
import json
import tempfile
import unittest
from pathlib import Path

from skillsmgr.native_state import observe_native_state


class NativeProfileReaders(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.project = self.root / 'project'
        self.home.mkdir()
        self.project.mkdir()

    def write(self, relative, text, home=False):
        path = (self.home if home else self.project) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def observe(self, agent, name='deploy'):
        return observe_native_state(agent, name, home=self.home, project=self.project)

    def test_opencode_jsonc_v2_and_legacy_precedence(self):
        self.write('.opencode/opencode.jsonc', '''{
          // comments and a string containing comment syntax
          "other": "https://example.test/*",
          "permission": {"skill": {"*": "deny"}},
          "permissions": [
            {"action":"skill", "resource":"dep*", "effect":"ask"},
            {"action":"skill", "resource":"deploy", "effect":"allow"},
          ],
        }''')
        result = self.observe('opencode')
        entry = next(x for x in result['sources'] if x['source'] == 'project-dotdir-jsonc')
        self.assertEqual(entry['declared'], 'allow')
        self.assertEqual(entry['matched_pattern'], 'deploy')
        self.assertEqual(result['effective_state'], 'unknown')
        self.assertTrue(result['partial'])

    def test_opencode_invalid_jsonc_and_v2_never_claim_a_declaration(self):
        for data in ('{"permissions": [], "permissions": []}',
                     '{/* unterminated',
                     json.dumps({'permissions': [{'action': 'skill', 'resource': '*', 'effect': 'maybe'}]})):
            with self.subTest(data=data):
                self.write('opencode.jsonc', data)
                entry = next(x for x in self.observe('opencode')['sources'] if x['source'] == 'project-jsonc')
                self.assertIn(entry['status'], ('invalid', 'unavailable'))
                self.assertNotIn('declared', entry)

    def test_commandcode_layers_are_separate_and_typed(self):
        self.write('.commandcode/settings.json', '{"disabledSkills":["deploy"]}', home=True)
        self.write('.commandcode/settings.json', '{"disabledSkills":[]}')
        self.write('.commandcode/settings.local.json', '{"disabledSkills":"deploy"}')
        result = self.observe('commandcode')
        self.assertEqual(result['sources'][0]['declared'], 'disabled')
        self.assertNotIn('declared', result['sources'][1])
        self.assertEqual(result['sources'][2]['status'], 'invalid')
        self.assertEqual(result['effective_state'], 'unknown')
        self.assertNotIn('observed_setting', result)


if __name__ == '__main__':
    unittest.main()
