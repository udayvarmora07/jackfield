import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from skillsmgr.project_config import MAX_BYTES, MAX_RULES, _supported, observe_project_skill_config


@unittest.skipUnless(_supported(), 'requires safe descriptor-based config reads')
class ProjectSkillConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        self.config_dir = self.root / '.codex'

    def write(self, text):
        self.config_dir.mkdir(exist_ok=True)
        (self.config_dir / 'config.toml').write_text(text, encoding='utf-8')

    def test_missing_and_absent(self):
        self.assertEqual(observe_project_skill_config(None)['state'], 'unavailable')
        self.assertEqual(observe_project_skill_config(self.root / 'no')['state'], 'unavailable')
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'missing')
        self.write('model = "x"\n')
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'absent')

    def test_declarations_are_redacted_and_do_not_mutate(self):
        self.write('[skills]\ninclude_instructions = false\n[[skills.config]]\nname = "secret"\nenabled = false\n')
        before = (self.config_dir / 'config.toml').read_bytes()
        user = Path(self.temp.name) / 'user-config'
        user.write_text('unchanged')
        result = observe_project_skill_config(self.root)
        self.assertEqual(result['state'], 'observed')
        self.assertIs(result['include_instructions'], False)
        self.assertEqual(result['rules'], [{'selector': 'name', 'enabled': False}])
        self.assertNotIn('secret', repr(result))
        self.assertNotIn('effective_state', result)
        self.assertEqual((self.config_dir / 'config.toml').read_bytes(), before)
        self.assertEqual(user.read_text(), 'unchanged')

    def test_bad_schema_and_malformed_toml(self):
        self.write('[skills]\ninclude_instructions = "false"\nconfig = 1\n')
        result = observe_project_skill_config(self.root)
        self.assertTrue(result['schema_unknown'])
        self.assertEqual(result['state'], 'unavailable')
        self.assertIn('unrecognised', result['reason'])
        self.assertIsNone(result['include_instructions'])
        self.write('skills = "unexpected"\n')
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'unavailable')
        self.write('[skills\n')
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'unavailable')

    def test_rule_bounds_and_bad_rule(self):
        self.write(''.join('[[skills.config]]\npath = "/secret"\nenabled = true\n' for _ in range(MAX_RULES + 2)))
        result = observe_project_skill_config(self.root)
        self.assertEqual((result['total'], len(result['rules']), result['omitted']), (MAX_RULES + 2, MAX_RULES, 2))
        self.assertNotIn('/secret', repr(result))
        self.write('[[skills.config]]\nname = "x"\npath = "y"\nenabled = false\n')
        self.assertTrue(observe_project_skill_config(self.root)['schema_unknown'])

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlink creation is unavailable')
    def test_links_are_unavailable(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (outside / 'config.toml').write_text('[skills]\ninclude_instructions = false')
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(observe_project_skill_config(alias)['state'], 'unavailable')
        self.config_dir.symlink_to(outside, target_is_directory=True)
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'unavailable')
        self.config_dir.unlink()
        self.config_dir.mkdir()
        config = self.config_dir / 'config.toml'
        config.symlink_to(outside / 'config.toml')
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'unavailable')

    def test_large_file_is_unavailable(self):
        self.config_dir.mkdir()
        config = self.config_dir / 'config.toml'
        config.write_bytes(b'x' * (MAX_BYTES + 1))
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'unavailable')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO creation is unavailable')
    def test_fifo_is_unavailable(self):
        self.config_dir.mkdir()
        os.mkfifo(self.config_dir / 'config.toml')
        self.assertEqual(observe_project_skill_config(self.root)['state'], 'unavailable')


class UnsupportedPlatformTests(unittest.TestCase):
    def test_returns_before_opening_files(self):
        with mock.patch('skillsmgr.project_config._supported', return_value=False), \
             mock.patch('skillsmgr.project_config.os.open') as open_file:
            result = observe_project_skill_config(Path('/project'))
        self.assertEqual(result['state'], 'unavailable')
        open_file.assert_not_called()


if __name__ == '__main__':
    unittest.main()
