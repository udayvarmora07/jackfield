"""New observations share the existing report without becoming native state."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from skillsmgr import cli_handlers, hygiene


class CompatibilityReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()

    def test_project_declarations_are_reported_without_changing_listing(self):
        observed = {'state': 'observed', 'reason': 'Declared only.', 'include_instructions': False,
                    'rules': [{'selector': 'name', 'enabled': False}], 'total': 1,
                    'omitted': 0, 'schema_unknown': False}
        base = hygiene.hygiene_report([], scope='codex', home=self.home)
        with patch.object(hygiene.project_config, 'observe_project_skill_config', return_value=observed):
            report = hygiene.hygiene_report([], scope='codex', home=self.home, project_root=self.home)
        self.assertEqual(report['codex_listing'], base['codex_listing'])
        finding = next(f for f in report['findings'] if f['category'] == 'codex-project-skill-config')
        self.assertEqual(finding['evidence']['runtime_state'], 'unknown')
        self.assertFalse(finding['automatic_action'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_handlers._render_hygiene_text(report)
        self.assertIn('Codex project skill declarations', out.getvalue())
        self.assertIn('include_instructions=false; 1 rules declared', out.getvalue())

    def test_partial_group_evidence_does_not_invalidate_complete_document_coverage(self):
        grouped = {'state': 'observed', 'partial': True, 'runtime_state': 'unknown',
                   'source': '~/.claude/skills', 'groups': [{'name': 'group', 'skills': ['nested']}]}
        with patch.object(hygiene.discovery_diagnostics, 'observe_grouped_personal_skills', return_value=grouped):
            report = hygiene.hygiene_report([], scope='claude-code', home=self.home)
        self.assertEqual(report['summary']['physical_instances'], 0)
        self.assertEqual(report['claude_listing']['listed_skills'], 0)
        self.assertTrue(report['claude_grouped_folders']['partial'])
        self.assertTrue(any(s['signal'] == 'claude-grouped-personal-folders' for s in report['unavailable_signals']))
        self.assertEqual(report['document_fingerprints']['status'], 'observed')
        self.assertTrue(any(f['category'] == 'claude-grouped-personal-folders' for f in report['findings']))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_handlers._render_hygiene_text(report)
        self.assertIn('Claude personal group group: nested', out.getvalue())

    def test_unrelated_scope_does_not_inspect_extra_roots(self):
        with patch.object(hygiene.discovery_diagnostics, 'observe_grouped_personal_skills') as grouped, \
                patch.object(hygiene.project_config, 'observe_project_skill_config') as project:
            hygiene.hygiene_report([], scope='global', home=self.home)
        grouped.assert_not_called()
        project.assert_not_called()

    def test_collision_findings_are_redacted_and_source_declarations_remain_unresolved(self):
        folder = self.home / '.agents'
        folder.mkdir()
        (folder / '.skill-lock.json').write_text(json.dumps({'version': 3, 'skills': {
            'My Skill': {'skillPath': '../private-token/SKILL.md'}, 'my-skill': {}}}))
        report = hygiene.hygiene_report([], scope='global', home=self.home)
        found = [f for f in report['findings'] if f['category'].startswith('lockfile-')]
        self.assertEqual({f['category'] for f in found}, {'lockfile-name-collision', 'lockfile-source-path'})
        self.assertNotIn(str(self.home), json.dumps(found))
        self.assertNotIn('private-token', json.dumps(found))
        self.assertTrue(all(not f['automatic_action'] for f in found))

    def test_unavailable_project_declarations_do_not_invalidate_document_baselines(self):
        unknown = {'state': 'unavailable', 'reason': 'Unobserved config.', 'include_instructions': None,
                   'rules': [], 'total': 0, 'omitted': 0, 'schema_unknown': True}
        with patch.object(hygiene.project_config, 'observe_project_skill_config', return_value=unknown):
            report = hygiene.hygiene_report([], scope='codex', home=self.home, project_root=self.home)
        self.assertEqual(report['document_fingerprints']['status'], 'observed')
        self.assertTrue(any(s['signal'] == 'codex-project-config' for s in report['unavailable_signals']))
