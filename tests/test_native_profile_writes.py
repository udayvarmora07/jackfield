"""Native setting writers operate only on temporary project fixtures."""
import json
import os
import stat
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from skillsmgr.native_profiles import NativeProfileError, apply_native, preview_native, undo_native


@unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "guarded directory descriptors")
class NativeWrites(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / 'project'
        self.data = self.root / 'data'
        self.project.mkdir()
        self.data.mkdir(mode=0o700)
        (self.project / '.claude').mkdir()
        (self.project / '.gemini').mkdir()
        self.path = self.project / '.claude/settings.local.json'

    def preview(self, agent='claude-code', names=None):
        return preview_native(self.project, agent, names or ['deploy'])

    def apply(self, plan, agent='claude-code', names=None):
        return apply_native(self.project, agent, names or ['deploy'], plan['plan_id'], self.data)

    def test_apply_and_undo_preserve_exact_content_and_mode(self):
        original = b'{\n  "other": 42\n}\n'
        self.path.write_bytes(original)
        self.path.chmod(0o640)
        plan = self.preview()
        self.assertEqual(self.path.read_bytes(), original)
        applied = self.apply(plan)
        self.assertEqual(json.loads(self.path.read_text())['skillOverrides']['deploy'], 'off')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE((self.data / 'native-backups' / (applied['backup_id'] + '.json')).stat().st_mode), 0o600)
        undo_native(applied['backup_id'], self.data)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)

    def test_absent_file_undo_and_noop(self):
        result = self.apply(self.preview())
        self.assertEqual(self.preview()['status'], 'no-op')
        undo_native(result['backup_id'], self.data)
        self.assertFalse(self.path.exists())

    def test_stale_apply_and_undo_refuse(self):
        self.path.write_text('{}')
        plan = self.preview()
        self.path.write_text('{"other": 1}')
        with self.assertRaises(NativeProfileError):
            self.apply(plan)
        applied = self.apply(self.preview())
        self.path.write_text('{"other": 2}')
        with self.assertRaises(NativeProfileError):
            undo_native(applied['backup_id'], self.data)
        self.assertEqual(self.path.read_text(), '{"other": 2}')

    def test_completed_native_rename_can_be_undone_after_interruption(self):
        before = b'{"other": 42}\n'
        self.path.write_bytes(before)
        self.path.chmod(0o640)
        plan = self.preview()
        replace = os.replace

        def interrupt_after_replace(source, destination, **kwargs):
            replace(source, destination, **kwargs)
            if destination == self.path.name:
                raise KeyboardInterrupt

        with mock.patch("skillsmgr.native_profiles.os.replace", side_effect=interrupt_after_replace):
            with self.assertRaises(KeyboardInterrupt):
                self.apply(plan)
        receipt, = (self.data / "native-backups").glob("*.json")
        self.assertNotEqual(self.path.read_bytes(), before)
        self.assertEqual(undo_native(receipt.stem, self.data)["status"], "undone")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)

    def test_native_undo_refuses_a_byte_identical_replacement(self):
        self.path.write_text('{}')
        applied = self.apply(self.preview())
        output = self.path.read_bytes()
        info = self.path.stat()
        replacement = self.path.with_name('external.json')
        replacement.write_bytes(output)
        replacement.chmod(stat.S_IMODE(info.st_mode))
        os.utime(replacement, ns=(info.st_atime_ns, info.st_mtime_ns))
        os.replace(replacement, self.path)
        with self.assertRaisesRegex(NativeProfileError, 'file was replaced'):
            undo_native(applied['backup_id'], self.data)
        self.assertEqual(self.path.read_bytes(), output)

    def test_refuses_noncanonical_json_and_symlinks(self):
        for data in ('{ "other": 1 }', '{"x":1,"x":2}', '{/* comment */}'):
            self.path.write_text(data)
            with self.assertRaises(NativeProfileError):
                self.preview()
        self.path.unlink()
        victim = self.root / 'victim'
        victim.write_text('{}')
        self.path.symlink_to(victim)
        with self.assertRaises(NativeProfileError):
            self.preview()
        self.assertEqual(victim.read_text(), '{}')

    def test_gemini_and_opencode_dialects(self):
        gemini = self.project / '.gemini/settings.json'
        gemini.write_text('{}')
        plan = self.preview('gemini')
        self.apply(plan, 'gemini')
        self.assertEqual(json.loads(gemini.read_text())['skills']['disabled'], ['deploy'])
        opencode = self.project / 'opencode.json'
        for original in ('{"permission": {"skill": {}}}', '{"permissions": []}'):
            opencode.write_text(original)
            plan = self.preview('opencode', ['deploy', 'review'])
            self.apply(plan, 'opencode', ['deploy', 'review'])
            self.assertEqual(self.preview('opencode', ['deploy', 'review'])['status'], 'no-op')
        opencode.write_text('{}')
        with self.assertRaises(NativeProfileError):
            self.preview('opencode')

    def test_symlink_parent_and_changed_mode_are_refused(self):
        (self.project / '.claude').rmdir()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.project / '.claude').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(NativeProfileError):
            self.preview()
        (self.project / '.claude').unlink()
        (self.project / '.claude').mkdir()
        self.path.write_text('{}')
        self.path.chmod(0o640)
        applied = self.apply(self.preview())
        self.path.chmod(0o600)
        with self.assertRaises(NativeProfileError):
            undo_native(applied['backup_id'], self.data)

    def test_opencode_extra_settings_are_refused(self):
        (self.project / 'opencode.json').write_text('{"permissions": []}')
        (self.project / 'opencode.jsonc').write_text('{}')
        with self.assertRaises(NativeProfileError):
            self.preview('opencode')

    def test_preview_suppresses_compact_lines_with_unrelated_secrets(self):
        secret = 'unrelated-secret-7392'
        self.path.write_text(json.dumps({'credential': secret, 'skillOverrides': {}}))
        plan = self.preview()
        self.assertNotIn(secret, json.dumps(plan))
        self.assertEqual(plan['diff'], '')
        self.assertTrue(plan['diff_suppressed'])
        self.assertEqual(plan['changes'], [{'skill': 'deploy', 'operation': 'ensure off'}])
        self.apply(plan)
        self.assertEqual(json.loads(self.path.read_text())['credential'], secret)

    def test_preview_diff_has_no_unrelated_context(self):
        secret = 'unrelated-secret-1283'
        self.path.write_text(json.dumps({'credential': secret, 'skillOverrides': {'deploy': 'on'}}, indent=2) + '\n')
        plan = self.preview()
        self.assertNotIn(secret, json.dumps(plan))
        self.assertFalse(plan['diff_suppressed'])
        self.assertIn('deploy', plan['diff'])
        self.assertNotIn('credential', plan['diff'])

    def test_target_container_with_unrelated_value_is_suppressed(self):
        secret = 'unrelated-secret-4582'
        self.path.write_text(json.dumps({'skillOverrides': {secret: 'on'}}))
        plan = self.preview()
        self.assertTrue(plan['diff_suppressed'])
        self.assertNotIn(secret, json.dumps(plan))

    def test_recheck_refuses_concurrent_write_after_backup(self):
        self.path.write_text('{}')
        plan = self.preview()
        from skillsmgr import native_profiles
        original = native_profiles._write_new
        def mutate(fd, name, data, mode):
            info = original(fd, name, data, mode)
            if name.startswith('.skills-manager-'):
                self.path.write_text('{"other": 3}')
            return info
        with mock.patch.object(native_profiles, '_write_new', side_effect=mutate):
            with self.assertRaises(NativeProfileError):
                self.apply(plan)
        self.assertEqual(self.path.read_text(), '{"other": 3}')


class NativeHandoffs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.project = root / 'project'
        self.data = root / 'data'
        self.project.mkdir()
        self.data.mkdir(mode=0o700)

    def test_codex_argv_is_structured_and_apply_refuses(self):
        plan = preview_native(self.project, 'codex', ['review', 'deploy'])
        self.assertEqual(plan['status'], 'launch-only')
        self.assertEqual(plan['argv'], ['codex', '-c', 'skills.config=[{name = "deploy", enabled = false}, {name = "review", enabled = false}]'])
        parsed = tomllib.loads(plan['argv'][2])
        self.assertEqual(parsed['skills']['config'], [
            {'name': 'deploy', 'enabled': False}, {'name': 'review', 'enabled': False}])
        with self.assertRaises(NativeProfileError):
            apply_native(self.project, 'codex', ['review', 'deploy'], plan['plan_id'], self.data)
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(list(self.data.iterdir()), [])

    def test_commandcode_patch_and_apply_refuse(self):
        plan = preview_native(self.project, 'commandcode', ['deploy'])
        self.assertEqual(plan['status'], 'manual-patch')
        self.assertEqual(plan['patch']['key'], 'disabledSkills')
        self.assertEqual(plan['patch']['names'], ['deploy'])
        with self.assertRaises(NativeProfileError):
            apply_native(self.project, 'commandcode', ['deploy'], plan['plan_id'], self.data)
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(list(self.data.iterdir()), [])

    def test_handoff_rejects_unsafe_names(self):
        for agent in ('codex', 'commandcode'):
            for name in ('../escape', 'x"; echo bad', 'plugin:name'):
                with self.subTest(agent=agent, name=name):
                    with self.assertRaises(ValueError):
                        preview_native(self.project, agent, [name])


if __name__ == '__main__':
    unittest.main()
