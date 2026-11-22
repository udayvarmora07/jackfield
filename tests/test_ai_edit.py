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
            model.return_value.ask_text.side_effect = lambda system, *_a, **_k: (
                'New response private' if 'Updated line' in system
                else 'Old response' if 'Change this' in system else 'Bare response')
            model.return_value.output_tokens = 0
            model.return_value.last_truncated = False
            model.return_value.label.return_value = {'model': 'fake'}
            model.return_value.config = {'model': 'fake'}
            payload = {'review_id': prepared['review']['review_id'], 'without_skill': True,
                       'cases': [{'prompt': 'Private test request', 'contains': 'New'}]}
            result = ai_edit.compare_edit(self.data, payload)
        variants = result['cases'][0]
        self.assertEqual({key: variants[key]['grade']['passed'] for key in variants},
                         {'current': 0, 'candidate': 1, 'without_skill': 0})
        self.assertEqual(result['statistics']['candidate_vs_current']['verdict'], 'inconclusive')
        self.assertIn('candidate_vs_without_skill', result['statistics'])
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

    def test_repeated_trials_report_statistics_and_bind_the_count(self):
        prepared = self.prepare()
        payload = {'review_id': prepared['review']['review_id'], 'trials': 3,
                   'cases': [{'prompt': 'Private request', 'contains': 'Updated'}]}
        calls = []

        def send(run, system, *_args, **_kwargs):
            if run.estimate_only:
                return None
            calls.append(system)
            return 'Updated private output' if 'Updated line' in system else 'Plain'

        with patch.object(ai.AiRun, 'ask_text', autospec=True, side_effect=send):
            estimate = ai_edit.compare_edit(self.data, {**payload, 'estimate': True})
            self.assertEqual(estimate['calls_planned'], 6)
            with self.assertRaises(ai.AiError) as changed:
                ai_edit.compare_edit(self.data, {**payload, 'trials': 2, 'plan': estimate['plan']})
            self.assertEqual(changed.exception.status, 409)
            result = ai_edit.compare_edit(self.data, {**payload, 'plan': estimate['plan']})
        self.assertEqual(len(calls), 6)
        self.assertEqual(result['status'], 'complete')
        candidate = result['cases'][0]['candidate']
        self.assertEqual([t['passed'] for t in candidate['trials']], [True, True, True])
        stats = result['statistics']['candidate_vs_current']
        self.assertEqual((stats['trials'], stats['observations'], stats['lift']), (3, 3, 1.0))
        self.assertEqual(stats['verdict'], 'inconclusive')
        receipt = (self.data / 'ai' / 'runs' / (result['run_id'] + '.json')).read_text()
        self.assertIn('candidate_vs_current', receipt)
        self.assertNotIn('Private request', receipt)
        self.assertNotIn('private output', receipt)

    def test_trial_count_is_validated(self):
        prepared = self.prepare()
        for bad in (0, 6, True, '3', 2.0):
            with self.subTest(bad=bad), self.assertRaises(ai.AiError):
                ai_edit.compare_edit(self.data, {'review_id': prepared['review']['review_id'], 'trials': bad,
                                                 'estimate': True, 'cases': [{'prompt': 'Request'}]})

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


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class HunkSelectionTests(EditFixture):
    """Keep only some AI changes; the result is a fresh review with provenance."""

    def setUp(self):
        super().setUp()
        self.body = 'One.\nTwo.\nThree.\nFour.\n'
        store = Store(self.data)
        store.edit('example', body=self.body)
        self.original = self.document.read_bytes()
        self.input.update({'document_hash': hashlib.sha256(self.original).hexdigest(), 'body': self.body,
                           'selection': None, 'instruction': 'Rewrite two and four.'})

    def propose(self):
        with patch.object(ai_edit, 'AiRun') as run:
            fake = run.return_value
            fake.ask_json.return_value = {'replacement': 'One.\nTWO!\nThree.\nFOUR!\n'}
            fake.config = {'model': 'fake-model', 'label': 'Fake', 'local': True}
            estimate = ai_edit.propose_edit(self.data, {**self.input, 'estimate': True})
            return ai_edit.propose_edit(self.data, {**self.input, 'tree_hash': estimate['tree_hash']})

    def test_two_hunks_are_reported_with_provenance(self):
        result = self.propose()
        self.assertEqual([(h['line'], h['removed'], h['added']) for h in result['hunks']],
                         [(2, 'Two.\n', 'TWO!\n'), (4, 'Four.\n', 'FOUR!\n')])
        self.assertEqual(result['review']['provenance']['model'], 'fake-model')
        self.assertEqual(result['review']['provenance']['request'], 'Rewrite two and four.')

    def test_partial_selection_restages_and_retires_the_full_proposal(self):
        result = self.propose()
        first = result['hunks'][0]['id']
        selected = ai_edit.select_hunks(self.data, {'review_id': result['review']['review_id'],
                                                    'body': self.body, 'accepted': [first]})
        self.assertEqual(selected['proposed'], 'One.\nTWO!\nThree.\nFour.\n')
        self.assertEqual(selected['provenance']['accepted_hunks'], 1)
        self.assertEqual(selected['provenance']['total_hunks'], 2)
        old = source_update.read_update_review(self.data, result['review']['review_id'])
        self.assertEqual(old['review_state'], 'cancelled')
        self.assertEqual(self.document.read_bytes(), self.original)
        committed = source_update.commit_update_review(self.data, selected['review']['review_id'],
                                                       name='example', scope='global', approve=True)
        self.assertTrue(self.document.read_text().endswith('One.\nTWO!\nThree.\nFour.\n'))
        snapshots = source_update.list_update_snapshots(self.data, 'example', 'global',
                                                        target_path=str(self.target))
        labelled = [s for s in snapshots if s['snapshot_id'] == committed['snapshot_id']]
        self.assertEqual(labelled[0]['provenance']['feature'], 'edit-skill')
        self.assertEqual(labelled[0]['provenance']['accepted_hunks'], 1)

    def test_failed_replacement_cancels_the_new_review_and_keeps_the_old(self):
        result = self.propose()
        review_id = result['review']['review_id']
        first = result['hunks'][0]['id']
        created = []
        real_stage = ai_edit.ai_concise._stage

        def stage(*args, **kwargs):
            staged = real_stage(*args, **kwargs)
            created.append(staged['review_id'])
            return staged

        with patch.object(ai_edit.ai_concise, '_stage', side_effect=stage), \
                patch.object(ai_edit.source_update, 'cancel_update_review',
                             wraps=source_update.cancel_update_review) as cancel:
            cancel.side_effect = [source_update.SourceUpdateError('review-not-pending', 'gone'), None]
            with self.assertRaises(ai.AiError) as failure:
                ai_edit.select_hunks(self.data, {'review_id': review_id, 'body': self.body, 'accepted': [first]})
        self.assertEqual(failure.exception.status, 409)
        self.assertEqual([call.args[1] for call in cancel.call_args_list], [review_id, created[0]])

    def test_unreviewable_selection_keeps_the_full_proposal(self):
        result = self.propose()
        review_id = result['review']['review_id']
        with patch.object(ai_edit.ai_concise, '_stage', return_value={'review_state': 'blocked', 'review_id': None}):
            with self.assertRaises(ai.AiError):
                ai_edit.select_hunks(self.data, {'review_id': review_id, 'body': self.body,
                                                 'accepted': [result['hunks'][0]['id']]})
        self.assertEqual(source_update.read_update_review(self.data, review_id)['review_state'], 'pending')

    def test_selection_rejects_all_none_unknown_and_stale(self):
        result = self.propose()
        review_id = result['review']['review_id']
        ids = [h['id'] for h in result['hunks']]
        for accepted in ([], ids, ['0' * 16], [ids[0], ids[0]], 'x'):
            with self.subTest(accepted=accepted), self.assertRaises(ai.AiError):
                ai_edit.select_hunks(self.data, {'review_id': review_id, 'body': self.body, 'accepted': accepted})
        with self.assertRaises(ai.AiError):
            ai_edit.select_hunks(self.data, {'review_id': review_id, 'body': 'Different\n', 'accepted': ids[:1]})
        (self.target / 'example.txt').write_text('changed', encoding='utf-8')
        with self.assertRaises(ai.AiError) as stale:
            ai_edit.select_hunks(self.data, {'review_id': review_id, 'body': self.body, 'accepted': ids[:1]})
        self.assertEqual(stale.exception.status, 409)
        self.assertEqual(source_update.read_update_review(self.data, review_id)['review_state'], 'pending')


class HunkBoundTests(unittest.TestCase):
    def test_large_repetitive_bodies_diff_quickly_as_one_hunk(self):
        import time
        before = 'x\n' * 2000
        after = ''.join('y\n' if i % 2 else 'x\n' for i in range(2000))
        started = time.monotonic()
        hunks = ai_edit._hunks(before, after)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(ai_edit._merge(before, after, hunks, {hunks[0]['id']}), after)
        self.assertEqual(ai_edit._merge(before, after, hunks, set()), before)

    def test_common_ends_are_not_reported(self):
        hunks = ai_edit._hunks('a\nb\nc\nd\n', 'a\nB\nc\nd\n')
        self.assertEqual([(h['line'], h['removed'], h['added']) for h in hunks], [(2, 'b\n', 'B\n')])
        self.assertEqual(ai_edit._hunks('same\n', 'same\n'), [])
