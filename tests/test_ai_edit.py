"""Exact-copy editing through source review, with a synthetic model."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import ai, ai_edit, context, source_update
from skillsmgr.sidecar_binding import PROVENANCE_FILENAME
from skillsmgr.store import Store


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class EditFixture(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name) / 'data'
        store = Store(self.data)
        store.create('example', 'Use when drafting example reports.', body='Keep this.\nChange this.\n')
        self.target = store.skills_dir / 'example'
        self.document = self.target / 'SKILL.md'
        self.original = self.document.read_bytes()
        (self.target / 'example.txt').write_text('Keep this companion', encoding='utf-8')
        (self.target / PROVENANCE_FILENAME).write_text('local provenance', encoding='utf-8')
        self.addCleanup(context.set_active_store, None)
        self.input = {'name': 'example', 'scope': 'global', 'target_path': str(self.target),
                      'document_hash': hashlib.sha256(self.original).hexdigest(),
                      'body': 'Keep this.\nChange this.\n', 'selection': [11, 23],
                      'instruction': 'Change the second sentence.'}

    def prepare(self):
        with patch.object(ai_edit, 'AiRun') as run:
            answer = run.return_value
            answer.ask_json.return_value = {'replacement': 'Updated line'}
            answer.label.return_value = {'model': 'fake'}
            estimate = ai_edit.propose_edit(self.data, {**self.input, 'estimate': True})
            return ai_edit.propose_edit(self.data, {**self.input, 'tree_hash': estimate['tree_hash']})


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class ReviewEditTests(EditFixture):

    def test_selected_text_review_preserves_companions_and_provenance(self):
        result = self.prepare()
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['proposed'], 'Keep this.\nUpdated line\n')
        self.assertEqual(self.document.read_bytes(), self.original)
        response = source_update.commit_update_review(self.data, result['review']['review_id'],
                                                        name='example', scope='global', approve=True)
        self.assertTrue(response['rollback_available'])
        self.assertTrue(self.document.read_bytes().endswith(b'Updated line\n'))
        self.assertEqual((self.target / 'example.txt').read_text(), 'Keep this companion')
        self.assertEqual((self.target / PROVENANCE_FILENAME).read_text(), 'local provenance')

    def test_stale_preflight_is_refused_before_model_constructor(self):
        (self.target / 'example.txt').write_text('Changed', encoding='utf-8')
        with patch.object(ai_edit, 'AiRun') as model, self.assertRaises(ai.AiError) as failure:
            ai_edit.propose_edit(self.data, {**self.input, 'tree_hash': '0' * 64})
        model.assert_not_called()
        self.assertEqual(failure.exception.status, 409)

    def test_compare_uses_reviewed_revisions_and_keeps_output_private(self):
        prepared = self.prepare()
        with patch.object(ai_edit, 'AiRun') as model:
            model.return_value.ask_text.side_effect = ['Old response', 'New response private', 'Bare response']
            model.return_value.last_truncated = False
            model.return_value.label.return_value = {'model': 'fake'}
            model.return_value.config = {'model': 'fake'}
            payload = {'review_id': prepared['review']['review_id'], 'without_skill': True,
                       'cases': [{'prompt': 'Private test request', 'contains': 'New'}]}
            result = ai_edit.compare_edit(self.data, payload)
        variants = result['cases'][0]
        self.assertEqual([variants[key]['grade']['passed'] for key in variants], [0, 1, 0])
        receipt = (self.data / 'ai' / 'runs' / (result['run_id'] + '.json')).read_text()
        self.assertNotIn('Private test request', receipt)
        self.assertNotIn('New response private', receipt)
        self.document.write_bytes(self.original + b'External change')
        with self.assertRaises(ai.AiError):
            ai_edit.compare_edit(self.data, {**payload, 'estimate': True})


_CONFIG = {'provider': 'custom', 'label': 'Fake', 'model': 'primary-model', 'local': True,
           'base_url': 'http://127.0.0.1:9/v1', 'max_run_tokens': 10 ** 9, 'max_day_tokens': 10 ** 9}


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class PlanBindingTests(EditFixture):
    """Use the real plan binding; only the provider configuration and sends are faked."""

    def setUp(self):
        super().setUp()
        for patcher in (patch.object(ai, 'resolve_config', side_effect=lambda *_: dict(_CONFIG)),
                        patch.object(ai.AiRun, 'ask_json', return_value={'replacement': 'Updated line'})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def real_prepare(self, payload):
        estimate = ai_edit.propose_edit(self.data, {**payload, 'estimate': True})
        return estimate, lambda extra: ai_edit.propose_edit(
            self.data, {**payload, 'tree_hash': estimate['tree_hash'], 'plan': estimate['plan'], **extra})

    def test_confirmed_send_with_other_selection_is_refused(self):
        # The same words twice: only the offsets distinguish the previewed occurrence.
        payload = {**self.input, 'body': 'Same line\nSame line\n', 'selection': [10, 19]}
        _, confirm = self.real_prepare(payload)
        with self.assertRaises(ai.AiError) as failure:
            confirm({'selection': [0, 9]})
        self.assertEqual(failure.exception.status, 409)
        self.assertEqual(confirm({})['proposed'], 'Same line\nUpdated line\n')

    def test_confirmed_send_with_other_model_is_refused(self):
        _, confirm = self.real_prepare(self.input)
        _CONFIG['model'] = 'changed-model'
        self.addCleanup(_CONFIG.__setitem__, 'model', 'primary-model')
        with self.assertRaises(ai.AiError) as failure:
            confirm({})
        self.assertEqual(failure.exception.status, 409)

    def test_null_example_counts_as_absent(self):
        estimate, _ = self.real_prepare({**self.input, 'example': None})
        self.assertEqual(estimate['status'], 'estimate')

    def test_failing_second_model_keeps_primary_results(self):
        prepared = self.prepare()
        payload = {'review_id': prepared['review']['review_id'], 'comparison_model': 'second-model',
                   'cases': [{'prompt': 'Request', 'contains': 'New'}]}

        def send(run, *_args, **_kwargs):
            if run.estimate_only:
                return None
            if run.config['model'] == 'second-model':
                raise ai.AiError('unknown model', 'ai-provider', 502)
            return 'New answer'

        with patch.object(ai.AiRun, 'ask_text', autospec=True, side_effect=send):
            estimate = ai_edit.compare_edit(self.data, {**payload, 'estimate': True})
            self.assertEqual(estimate['calls_planned'], 4)
            result = ai_edit.compare_edit(self.data, {**payload, 'plan': estimate['plan']})
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['models'], ['primary-model', 'second-model'])
        self.assertIn('unknown model', result['alternate_error'])
        self.assertEqual(result['cases'][0]['candidate']['grade']['passed'], 1)
        self.assertEqual(result['run']['model'], 'primary-model')

    def test_same_second_model_is_refused(self):
        prepared = self.prepare()
        with self.assertRaises(ai.AiError):
            ai_edit.compare_edit(self.data, {'review_id': prepared['review']['review_id'],
                                             'comparison_model': 'primary-model', 'estimate': True,
                                             'cases': [{'prompt': 'Request'}]})


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class CrlfEditTests(EditFixture):
    def setUp(self):
        super().setUp()
        self.document.write_bytes(self.original.replace(b'\n', b'\r\n'))
        self.original = self.document.read_bytes()
        self.input['document_hash'] = hashlib.sha256(self.original).hexdigest()

    def test_crlf_document_keeps_its_line_endings(self):
        result = self.prepare()
        source_update.commit_update_review(self.data, result['review']['review_id'],
                                           name='example', scope='global', approve=True)
        saved = self.document.read_bytes()
        self.assertTrue(saved.endswith(b'Updated line\r\n'))
        self.assertNotIn(b'\n', saved.replace(b'\r\n', b''))
