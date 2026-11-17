"""Read-only HTTP project context stays inside the operator's boundary."""

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

from skillsmgr import context
from skillsmgr.adapters import workspaces_payload
from skillsmgr.errors import StoreError
from skillsmgr.store import Store
from skillsmgr.webapp import WebAppServer, _doctor_payload


class ProjectContextTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / 'home'
        self.home.mkdir(mode=0o700)
        self.store = Store(self.root / 'data')
        self.store.init_db()
        context.set_active_store(self.store)
        self.project = self.store.data_dir / 'project'
        self.project.mkdir()
        self.addCleanup(context.set_active_store, None)
        patcher = mock.patch.dict(os.environ, {'HOME': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def query(self, project=None, roots=None):
        qs = {'scope': ['global'], 'hygiene': ['1']}
        if project is not None:
            qs['project'] = [str(project)]
        return _doctor_payload(self.store, qs, roots)

    def test_project_lock_and_claude_listing_use_selected_context(self):
        skill = self.project / '.claude/skills/project-fixture'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text(
            '---\nname: project-fixture\ndescription: Use for a synthetic project.\n---\nBody.\n'
        )
        (self.project / 'skills-lock.json').write_text('{"version":1,"skills":{}}')
        report = _doctor_payload(self.store, {
            'scope': ['all'], 'hygiene': ['1'], 'project': [str(self.project)]
        }, [self.store.data_dir])
        self.assertEqual(report['project']['path'], str(self.project))
        self.assertEqual(report['hygiene']['lockfiles']['project']['state'], 'ok')
        listing = report['hygiene']['claude_listing']
        self.assertEqual(listing['project_skills']['instances'], 1)
        self.assertNotIn('no project root', json.dumps(listing['partial_reasons']))

    def test_missing_context_retains_unavailable_project_evidence(self):
        report = self.query()
        self.assertEqual(report['hygiene']['lockfiles']['project']['state'], 'unavailable')

    def test_selected_project_listing_excludes_the_servers_working_project(self):
        other = self.store.data_dir / 'other-project'
        for project, name in ((other, 'other-skill'), (self.project, 'selected-skill')):
            skill = project / '.claude/skills' / name
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: Use for tests.\n---\n')
        with mock.patch('skillsmgr.scopes._cwd', return_value=other):
            report = _doctor_payload(self.store, {
                'scope': ['all'], 'hygiene': ['1'], 'project': [str(self.project)]
            }, [self.store.data_dir])
        listing = report['hygiene']['claude_listing']
        self.assertEqual([entry['name'] for entry in listing['entries']], ['selected-skill'])
        self.assertEqual(listing['project_skills']['instances'], 1)

    def test_outside_and_missing_projects_fail_before_any_doctor_scan(self):
        outside = self.root / 'outside-secret'
        outside.mkdir()
        for project in (outside, self.project / 'missing', self.project / '../../outside-secret', '\x00'):
            with self.subTest(project=project), mock.patch('skillsmgr.webapp.doctor.doctor_report') as doctor:
                with self.assertRaises(StoreError) as caught:
                    self.query(project, [self.store.data_dir])
                doctor.assert_not_called()
                self.assertNotIn('outside-secret', str(caught.exception))

    def test_default_http_boundary_is_the_store_even_without_explicit_roots(self):
        with self.assertRaises(StoreError):
            self.query(self.home)

    def test_explicit_operator_root_is_accepted_without_widening_the_default(self):
        outside = self.root / 'operator-project'
        outside.mkdir()
        report = self.query(outside, [self.store.data_dir, outside])
        self.assertEqual(report['project']['status'], 'accepted')
        self.assertEqual(report['project']['path'], str(outside))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlinks unavailable')
    def test_project_and_nested_directory_links_cannot_escape(self):
        outside = self.root / 'outside-secret'
        outside.mkdir()
        for rel in ('linked-project', '.claude', '.claude/skills', '.agents', '.agents/skills'):
            with self.subTest(rel=rel):
                link = self.project / rel
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside, target_is_directory=True)
                try:
                    with mock.patch('skillsmgr.webapp.doctor.doctor_report') as doctor:
                        with self.assertRaises(StoreError):
                            self.query(link if rel == 'linked-project' else self.project)
                        doctor.assert_not_called()
                finally:
                    link.unlink()

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlinks unavailable')
    def test_project_settings_links_cannot_read_outside_files(self):
        outside = self.root / 'private-settings.json'
        outside.write_text('{"skillListingMaxDescChars":987654}')
        for rel in ('.claude/settings.json', '.claude/settings.local.json', 'skills-lock.json', 'apm.yml'):
            with self.subTest(rel=rel):
                link = self.project / rel
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside)
                try:
                    with self.assertRaises(StoreError) as caught:
                        self.query(self.project)
                    self.assertNotIn('private-settings', str(caught.exception))
                finally:
                    link.unlink()

    def test_workspace_choices_are_only_the_supplied_roots_without_a_directory_walk(self):
        roots = [self.store.data_dir, self.project, self.project]
        with mock.patch.object(Path, 'iterdir', side_effect=AssertionError('must not enumerate')):
            payload = workspaces_payload(allowed_roots=roots)
        self.assertEqual(payload['managed_roots'], [str(self.store.data_dir), str(self.project)])
        self.assertEqual(payload['project']['status'], 'not-requested')

    def test_real_http_context_is_read_only_and_refusal_is_a_clean_400(self):
        (self.project / 'skills-lock.json').write_text('{"version":1,"skills":{}}')
        server = WebAppServer(self.store, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        before = {str(p): p.read_bytes() for p in self.store.data_dir.rglob('*') if p.is_file()}
        try:
            url = server.url + 'api/doctor?scope=global&hygiene=1&project='
            for _ in range(2):
                with urllib.request.urlopen(url + urllib.parse.quote(str(self.project)), timeout=5) as response:
                    report = json.load(response)
                self.assertEqual(report['project']['status'], 'accepted')
                self.assertEqual(report['hygiene']['lockfiles']['project']['state'], 'ok')
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(url + urllib.parse.quote(str(self.home)), timeout=5)
            self.assertEqual(caught.exception.code, 400)
            with caught.exception as response:
                body = response.read().decode()
            self.assertNotIn('Traceback', body)
            self.assertNotIn(str(self.home), body)
            self.assertEqual(before, {str(p): p.read_bytes() for p in self.store.data_dir.rglob('*') if p.is_file()})
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.httpd.server_close()
