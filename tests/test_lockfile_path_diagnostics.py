"""Lock syntax and local name collisions do not resolve upstream source paths."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from skillsmgr import lockfiles


class LockfilePathDiagnosticsTests(unittest.TestCase):
    def evidence(self, entries):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name)
        (home / '.agents').mkdir()
        lock = home / '.agents' / '.skill-lock.json'
        lock.write_text(json.dumps({'version': 3, 'skills': entries}))
        before = lock.read_bytes()
        result = lockfiles.lockfile_evidence(home)
        self.assertEqual(lock.read_bytes(), before)
        self.assertFalse((home / '.agents' / 'skills').exists())
        return result['global']

    def test_colliding_declared_names_are_not_treated_as_distinct_installs(self):
        result = self.evidence({'My Skill': {}, 'my-skill': {}, 'other': {}})
        self.assertEqual(len(result['name_collisions']), 1)
        collision = result['name_collisions'][0]
        self.assertEqual(collision['names'], ['My Skill', 'my-skill'])
        self.assertTrue(collision['installed_path'].replace(os.sep, '/').endswith('/my-skill'))

    def test_distinct_names_and_no_entries_have_no_collision(self):
        self.assertEqual(self.evidence({})['name_collisions'], [])
        self.assertEqual(self.evidence({'one': {}, 'two': {}})['name_collisions'], [])

    def test_document_folder_and_root_declarations_remain_unresolved(self):
        for value, form in [('skills/demo/SKILL.md', 'document'), ('skills/demo', 'directory_or_other'),
                            ('SKILL.md', 'repository_root'), ('.', 'repository_root'), ('', 'repository_root')]:
            with self.subTest(value=value):
                row = self.evidence({'demo': {'skillPath': value}})['entries'][0]['source_path']
                self.assertEqual(row['form'], form)
                self.assertEqual(row['resolution'], 'unverified')

    def test_missing_and_invalid_path_types_do_not_become_valid_strings(self):
        self.assertEqual(self.evidence({'demo': {}})['entries'][0]['source_path']['state'], 'not_recorded')
        for value in (None, True, 1, [], {}):
            self.assertEqual(self.evidence({'demo': {'skillPath': value}})['entries'][0]['source_path']['state'], 'unrecognized')

    def test_untrusted_paths_are_not_read_or_echoed(self):
        value = '../private-secret/SKILL.md'
        row = self.evidence({'demo': {'skillPath': value}})['entries'][0]
        self.assertTrue(row['source_path']['parent_segments'])
        self.assertNotIn('private-secret', json.dumps(row))
        self.assertEqual(row['hash_status'], 'missing')

    def test_oversized_source_path_is_marked_without_echoing_it(self):
        row = self.evidence({'demo': {'skillPath': 'a' * (lockfiles.MAX_STRING + 1)}})['entries'][0]
        self.assertTrue(row['source_path']['truncated'])

    def test_display_name_truncation_does_not_create_a_false_folder_collision(self):
        one, two = 'a' * 128 + '-one', 'a' * 128 + '-two'
        result = self.evidence({one: {}, two: {}})
        self.assertEqual(result['name_collisions'], [])
        paths = {Path(row['installed_path']).name for row in result['entries']}
        self.assertEqual(paths, {one, two})

    @unittest.skipUnless(os.name == "posix", "deep path fixture uses POSIX paths")
    def test_display_path_truncation_does_not_create_a_false_collision(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        lock = root / 'lock.json'
        lock.write_text(json.dumps({'version': 3, 'skills': {'one': {}, 'two': {}}}))
        deep = root.joinpath(*['a' * 120 for _ in range(5)])
        deep.mkdir(parents=True)
        result = lockfiles._evaluated_lock(lockfiles.read_lock(lock), deep, 'tree')
        self.assertEqual(result['entries'][0]['installed_path'], result['entries'][1]['installed_path'])
        self.assertEqual(result['name_collisions'], [])
