import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import discovery_diagnostics as diag


@unittest.skipUnless(diag._supports_safe_scan(), "safe directory descriptors unavailable")
class GroupedPersonalSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.root = self.home / '.claude' / 'skills'

    def skill(self, relative, doc='SKILL.md'):
        directory = self.root / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / doc).write_text('private content')
        return directory

    def observe(self):
        return diag.observe_grouped_personal_skills(self.home)

    def test_missing_empty_and_grouped(self):
        self.assertEqual(self.observe()['state'], 'missing')
        self.root.mkdir(parents=True)
        self.assertEqual(self.observe()['groups'], [])
        self.skill('group/one')
        self.skill('group/two', 'SKILL.md.disabled')
        self.skill('flat')
        before = sorted(str(p.relative_to(self.home)) for p in self.home.rglob('*'))
        result = self.observe()
        self.assertEqual(result, {'source': '~/.claude/skills', 'state': 'observed',
                                  'runtime_state': 'unknown', 'partial': False,
                                  'groups': [{'name': 'group', 'skills': ['one', 'two']}]})
        self.assertEqual(before, sorted(str(p.relative_to(self.home)) for p in self.home.rglob('*')))
        self.assertNotIn(str(self.home), repr(result))
        self.assertNotIn('private content', repr(result))

    def test_excluded_roots(self):
        self.skill('synced/nested')
        self.skill('actual-skill/references/example')
        self.skill('actual-skill')
        self.skill('plugin/nested')
        marker = self.root / 'plugin' / '.claude-plugin'
        marker.mkdir()
        (marker / 'plugin.json').write_text('{}')
        self.assertEqual(self.observe()['groups'], [])

    @unittest.skipUnless(hasattr(os, "symlink") and hasattr(os, "mkfifo"), "symlinks or FIFOs unavailable")
    def test_symlinks_and_nonregular_documents_are_not_followed(self):
        outside = self.home / 'outside'
        outside.mkdir()
        (outside / 'SKILL.md').write_text('external')
        self.root.mkdir(parents=True)
        (self.root / 'link').symlink_to(outside, target_is_directory=True)
        group = self.root / 'group'
        group.mkdir()
        (group / 'link').symlink_to(outside, target_is_directory=True)
        fifo = group / 'fifo'
        fifo.mkdir()
        os.mkfifo(fifo / 'SKILL.md')
        bad_group = self.root / 'bad'
        bad_group.mkdir()
        (bad_group / 'SKILL.md').symlink_to(outside / 'SKILL.md')
        self.skill('bad/nested')
        result = self.observe()
        self.assertTrue(result['partial'])
        self.assertEqual(result['groups'], [])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_root_symlink_and_wrong_type_unavailable(self):
        (self.home / '.claude').mkdir()
        (self.home / '.claude' / 'skills').symlink_to(self.home, target_is_directory=True)
        self.assertEqual(self.observe()['state'], 'unavailable')
        (self.home / '.claude' / 'skills').unlink()
        (self.home / '.claude' / 'skills').write_text('wrong type')
        self.assertEqual(self.observe()['state'], 'unavailable')

    def test_permission_error_and_bounded_entries(self):
        self.skill('group/one')
        with patch.object(diag, '_supports_safe_scan', return_value=True), \
                patch.object(diag.os, 'scandir', side_effect=PermissionError):
            result = self.observe()
        self.assertTrue(result['partial'])
        self.assertEqual(result['state'], 'observed')
        with patch.object(diag, 'MAX_ENTRIES', 1):
            result = self.observe()
        self.assertTrue(result['partial'])
        self.assertEqual(result['groups'], [])

    def test_report_limits_and_names(self):
        for index in range(4):
            self.skill(f'group/skill{index}')
            self.skill(f'group{index}/skill')
        with patch.object(diag, 'MAX_GROUPS', 2), patch.object(diag, 'MAX_SKILLS', 2):
            result = self.observe()
        self.assertTrue(result['partial'])
        self.assertLessEqual(len(result['groups']), 2)
        self.assertTrue(all(len(g['skills']) <= 2 for g in result['groups']))
        with patch.object(diag, 'MAX_NAME', 3):
            result = self.observe()
        self.assertTrue(result['partial'])
        self.assertTrue(all(len(g['name']) <= 3 for g in result['groups']))


class UnsupportedPlatformTests(unittest.TestCase):
    def test_unavailable_before_open(self):
        with patch.object(diag, '_supports_safe_scan', return_value=False), \
                patch.object(diag, '_open_root') as opened:
            result = diag.observe_grouped_personal_skills()
        opened.assert_not_called()
        self.assertEqual(result['state'], 'unavailable')
        self.assertTrue(result['partial'])

    def test_home_resolution_errors_are_unavailable(self):
        with patch.object(diag, '_supports_safe_scan', return_value=True), \
                patch.object(diag, 'home_dir', side_effect=RuntimeError):
            self.assertEqual(diag.observe_grouped_personal_skills()['state'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
