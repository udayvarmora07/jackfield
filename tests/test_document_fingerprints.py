import hashlib
import tempfile
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from skillsmgr import doctor, hygiene


class DocumentFingerprintsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def skill(self, parent, name, content='hello'):
        path = parent / name
        path.mkdir(parents=True)
        (path / 'SKILL.md').write_text(
            f'---\nname: {name}\ndescription: Test skill.\n---\n{content}\n', encoding='utf-8')
        return {'name': name, 'path': str(path), 'scope': 'global'}

    def report(self, records, **kwargs):
        return hygiene.hygiene_report(records, scope='global', home=self.root, **kwargs)['document_fingerprints']

    def test_hash_changes_aliases_and_same_name(self):
        first = self.skill(self.root, 'same')
        other = self.skill(self.root / 'nested', 'same')
        alias = self.root / 'alias'
        alias.symlink_to(self.root / 'same', target_is_directory=True)
        rows = [first, dict(first, path=str(alias), scope='agents'), other]
        before = self.report(rows)
        self.assertEqual(len(before['instances']), 2)
        self.assertEqual(before, self.report(list(reversed(rows))))
        original = {x['id']: x['content_hash'] for x in before['instances']}
        (self.root / 'same' / 'SKILL.md').write_text('changed', encoding='utf-8')
        after = self.report(rows)
        updated = {x['id']: x['content_hash'] for x in after['instances']}
        self.assertEqual(set(original), set(updated))
        self.assertEqual(sum(original[key] != updated[key] for key in original), 1)
        self.assertEqual(set(self.root.iterdir()), {self.root / 'same', self.root / 'nested', alias})
        self.assertNotIn('context_id', before)

    def test_invalid_rows_and_malformed_readable(self):
        good = self.skill(self.root, 'good')
        malformed = self.skill(self.root, 'malformed')
        (self.root / 'malformed' / 'SKILL.md').write_text('bad frontmatter', encoding='utf-8')
        missing = self.root / 'missing'
        missing.mkdir()
        conflict = self.skill(self.root, 'conflict')
        (self.root / 'conflict' / 'SKILL.md.disabled').write_text('other', encoding='utf-8')
        invalid = self.skill(self.root, 'invalid')
        invalid.update(body='x', content_hash='F' * 64)
        undecodable = self.skill(self.root, 'undecodable')
        (self.root / 'undecodable' / 'SKILL.md').write_bytes(b'\xff')
        report = self.report([good, malformed, {'name': 'missing', 'path': str(missing)}, conflict, invalid, undecodable])
        self.assertEqual({r['name'] for r in report['instances']}, {'good', 'malformed'})
        self.assertEqual(report['omitted'], 4)
        self.assertEqual(report['status'], 'partial')

    def test_refused_link_missing_identity_and_cap(self):
        one = self.skill(self.root, 'one')
        two = self.skill(self.root, 'two')
        report = self.report([one, two], max_instances=1)
        self.assertEqual(len(report['instances']), 1)
        self.assertEqual(report['omitted'], 1)
        self.assertEqual(report['status'], 'partial')
        digest = hashlib.sha256(b'foo').hexdigest()
        prepared = [dict(one, content_hash=digest, link_escape=True), {'name': 'none', 'content_hash': digest}]
        report = hygiene._document_fingerprints(prepared, [])
        self.assertEqual(report['instances'], [])
        self.assertEqual(report['omitted'], 2)

    def test_doctor_context_alias_and_acquisition_degradation(self):
        data = self.root / 'data'
        data.mkdir()
        alias = self.root / 'data-alias'
        alias.symlink_to(data, target_is_directory=True)
        store = SimpleNamespace(data_dir=data)
        with mock.patch.object(doctor, '_hygiene_records', return_value=([], [])):
            first = doctor.hygiene_evidence(store, 'global', project_root=self.root)
            alias_report = doctor.hygiene_evidence(SimpleNamespace(data_dir=alias), 'global', project_root=self.root)
            other = doctor.hygiene_evidence(store, 'agents', project_root=self.root)
        a = first['document_fingerprints']
        self.assertEqual(a['context_id'], alias_report['document_fingerprints']['context_id'])
        self.assertNotEqual(a['context_id'], other['document_fingerprints']['context_id'])
        with mock.patch.object(doctor, '_hygiene_records', return_value=([], [{'section': 'scope-scan'}])):
            report = doctor.hygiene_evidence(store, 'global')
        self.assertTrue(report['summary']['partial'])
        self.assertEqual(report['document_fingerprints']['status'], 'partial')

    @unittest.skipIf(
        sys.platform == "win32" and sys.version_info >= (3, 14),
        "Python 3.14 on Windows resolves a path containing NUL without raising ValueError, "
        "which is the failure this test provokes",
    )
    def test_context_resolution_error_does_not_crash(self):
        store = SimpleNamespace(data_dir='bad\x00path')
        with mock.patch.object(doctor, '_hygiene_records', return_value=([], [])):
            report = doctor.hygiene_evidence(store, 'global')
        self.assertEqual(report['document_fingerprints']['status'], 'partial')
        self.assertNotIn('context_id', report['document_fingerprints'])
        self.assertTrue(report['summary']['partial'])


if __name__ == '__main__':
    unittest.main()
