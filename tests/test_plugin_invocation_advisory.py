"""Observed plugin intent must not become a native invocation verdict."""
from pathlib import Path
import tempfile
import unittest

from skillsmgr import hygiene, loader


class PluginInvocationAdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.plugin = self.home / 'plugin'
        self.manifest = self.plugin / '.claude-plugin' / 'plugin.json'
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text('{"name":"example"}')
        self.skill = self.plugin / 'skills' / 'demo'
        self.skill.mkdir(parents=True)

    def findings(self, extra='disable-model-invocation: true\n', disabled=False):
        for filename in ('SKILL.md', 'SKILL.md.disabled'):
            (self.skill / filename).unlink(missing_ok=True)
        doc = 'SKILL.md.disabled' if disabled else 'SKILL.md'
        (self.skill / doc).write_text('---\nname: demo\ndescription: Use when testing.\n' + extra + '---\nBody\n')
        record = loader.load_skill(self.skill)
        record.update(scope='agents', path=str(self.skill))
        result = hygiene._plugin_member_findings([record], self.home)
        return [item for item in result if item['category'] == 'plugin-invocation-policy']

    def test_true_intent_is_observed_with_a_version_scoped_report(self):
        found = self.findings()
        self.assertEqual(len(found), 1)
        row = found[0]
        self.assertEqual(row['severity'], 'info')
        self.assertEqual(row['evidence']['runtime_state'], 'unknown')
        self.assertIs(row['evidence']['disable_model_invocation'], True)
        self.assertIn('2.1.29', row['explanation'])
        self.assertIn('22345', row['evidence']['issue'])
        self.assertFalse(row['automatic_action'])
        self.assertNotIn(str(self.home), str(row['evidence']))

    def test_other_values_and_disabled_copies_do_not_raise_the_advisory(self):
        for extra in ('', 'disable-model-invocation: false\n',
                      'disable-model-invocation: "true"\n'):
            with self.subTest(extra=extra):
                self.assertFalse(self.findings(extra))
        self.assertFalse(self.findings(disabled=True))

    def test_missing_or_invalid_manifest_does_not_establish_plugin_policy(self):
        for data in ('{bad', '[]', '{"other":true}'):
            self.manifest.write_text(data)
            self.assertFalse(self.findings())
        self.manifest.unlink()
        self.assertFalse(self.findings())

    def test_nonregular_manifest_does_not_establish_plugin_policy(self):
        self.manifest.unlink()
        self.manifest.mkdir()
        self.assertFalse(self.findings())

    def test_unreadable_record_does_not_establish_frontmatter_intent(self):
        record = {'name': 'demo', 'path': str(self.skill), 'scope': 'agents',
                  'decode_error': 'unreadable', 'frontmatter_extensions': {'disable-model-invocation': True}}
        found = hygiene._plugin_member_findings([record], self.home)
        self.assertFalse([item for item in found if item['category'] == 'plugin-invocation-policy'])
