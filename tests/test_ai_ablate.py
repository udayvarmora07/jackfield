"""Ablate and retire (docs/60 G1) with a synthetic model."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import ai, ai_ablate, ai_skills, context, source_update, trial_stats
from skillsmgr.store import Store

_CONFIG = {'provider': 'custom', 'label': 'Fake', 'model': 'primary-model', 'local': True,
           'base_url': 'http://127.0.0.1:9/v1', 'max_run_tokens': 10 ** 9, 'max_day_tokens': 10 ** 9}

_BODY = ('Intro line.\n\n'
         '## Magic word\nWhen asked, the magic word is PINEAPPLE.\n\n'
         '### Spelling\nAlways in capitals.\n\n'
         '```\n## not a heading\n```\n\n'
         '## Style\nBe friendly.\n')


def _answer(system):
    return 'The answer is PINEAPPLE.' if 'magic word is PINEAPPLE' in system else 'I do not know.'


class SectionTests(unittest.TestCase):
    def test_sections_split_only_on_markdown_line_endings(self):
        body = 'Preamble\f## Inline text\r\n## First\rBody\n## Second\n'
        rows = ai_ablate.sections(body)
        self.assertEqual([(row['heading'], row['line']) for row in rows],
                         [('First', 2), ('Second', 4)])
        self.assertEqual(ai_ablate._without(body, rows[0]),
                         'Preamble\f## Inline text\r\n## Second\n')

    def test_sections_nest_ignore_fences_and_carry_offsets(self):
        rows = ai_ablate.sections(_BODY)
        self.assertEqual([(r['heading'], r['level']) for r in rows],
                         [('Magic word', 2), ('Spelling', 3), ('Style', 2)])
        magic = rows[0]
        self.assertTrue(_BODY[magic['start']:magic['end']].startswith('## Magic word'))
        self.assertIn('### Spelling', _BODY[magic['start']:magic['end']])
        self.assertIn('## not a heading', _BODY[magic['start']:magic['end']])
        self.assertEqual(ai_ablate._without(_BODY, rows[2]),
                         _BODY[:rows[2]['start']])
        self.assertEqual(ai_ablate.sections('No headings here.\n'), [])

    def test_decision_needs_evidence_and_biases_ties_to_removal(self):
        def stats(cases, interval, observations=12):
            return {'paired_cases': cases, 'observations': observations, 'interval': interval}
        self.assertEqual(ai_ablate.decide(stats(2, [0.0, 0.0]))[0], 'not-enough-evidence')
        self.assertEqual(ai_ablate.decide(stats(4, [0.0, 0.0], observations=3))[0], 'not-enough-evidence')
        self.assertEqual(ai_ablate.decide(stats(4, None))[0], 'not-enough-evidence')
        self.assertEqual(ai_ablate.decide(stats(4, [0.0, 0.0]))[0], 'remove')
        self.assertEqual(ai_ablate.decide(stats(4, [-0.5, ai_ablate.MARGIN]))[0], 'remove')
        self.assertEqual(ai_ablate.decide(stats(4, [0.2, 0.9]))[0], 'keep')
        self.assertEqual(ai_ablate.decide(stats(4, [-0.1, 0.4]))[0], 'uncertain')
        # A small but certain benefit is kept even though it is under the margin.
        self.assertEqual(ai_ablate.decide(stats(4, [0.03, 0.08]))[0], 'keep')

    def test_flaky_checks_are_not_evidence_that_text_matters(self):
        def row(variant, trial, passed):
            return {'case': 1, 'variant': variant, 'trial': trial, 'assertions': [passed]}
        flaky = [row('full', 1, True), row('full', 2, False), row('ablated', 1, True), row('ablated', 2, False)]
        self.assertFalse(ai_ablate._discriminates(flaky))
        real = [row('full', 1, True), row('full', 2, True), row('ablated', 1, False), row('ablated', 2, True)]
        self.assertTrue(ai_ablate._discriminates(real))


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class AblateTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name) / 'data'
        self.store = Store(self.data)
        self.addCleanup(context.set_active_store, None)
        self.store.create('magic', 'Use magic when asked for the magic word.', body=_BODY)
        self.skill = self.store.skills_dir / 'magic'
        self.write_cases('PINEAPPLE', 4)
        self.sent = []

        def send(run, system, user, prefix, max_output, json_output, estimate):
            run.calls += 1
            run.output_tokens += 5
            run.last_truncated = False
            self.sent.append(system)
            return _answer(system)
        for patcher in (patch.object(ai, 'resolve_config', side_effect=lambda *_: dict(_CONFIG)),
                        patch.object(ai.AiRun, '_send', autospec=True, side_effect=send)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_cases(self, expected, count, hard=True):
        # A "hard" case fails with and without the skill, so the cases are not
        # all at the ceiling and a "no difference" result is a real tie.
        cases = {'skill_name': 'magic', 'evals': [
            {'id': n, 'prompt': f'What is the magic word? ({n})', 'expected_output': expected,
             'assertions': [{'type': 'contains', 'value': expected}]} for n in range(1, count + 1)]
            + ([{'id': 99, 'prompt': 'Name the fruit.', 'expected_output': 'BANANA',
                 'assertions': [{'type': 'contains', 'value': 'BANANA'}]}] if hard else [])}
        directory = self.skill / 'evals'
        directory.mkdir(exist_ok=True)
        (directory / 'evals.json').write_text(json.dumps(cases), encoding='utf-8')

    def run_ablation(self, **payload):
        payload = {'name': 'magic', **payload}
        estimate = ai_ablate.ablate(self.store, {**payload, 'estimate': True})
        self.assertEqual(self.sent, [])
        return ai_ablate.ablate(self.store, {**payload, 'plan': estimate['plan']})

    def test_useless_section_is_staged_for_removal_and_nothing_is_written(self):
        document = self.skill / 'SKILL.md'
        before = document.read_bytes()
        result = self.run_ablation(section=2, trials=2)
        self.assertEqual(result['decision'], 'remove')
        self.assertEqual(result['statistics']['interval'], [0.0, 0.0])
        self.assertIn('may not test what it does', result['coverage_warning'])
        self.assertEqual(len(self.sent), 5 * 2 * 2)
        proposal = result['proposal']
        self.assertEqual(proposal['kind'], 'remove-section')
        self.assertNotIn('## Style', proposal['proposed'])
        self.assertIn('## Magic word', proposal['proposed'])
        self.assertEqual(proposal['provenance']['feature'], 'ablate')
        self.assertEqual(document.read_bytes(), before)
        review = source_update.read_update_review(self.data, proposal['review']['review_id'])
        self.assertEqual(review['review_state'], 'pending')
        source_update.commit_update_review(self.data, review['review_id'], name='magic', scope='global',
                                           approve=True)
        self.assertNotIn('## Style', document.read_text(encoding='utf-8'))
        self.assertIn('PINEAPPLE', document.read_text(encoding='utf-8'))

    def test_useful_section_is_kept_and_nothing_is_staged(self):
        result = self.run_ablation(section=0)
        self.assertEqual(result['decision'], 'keep')
        self.assertEqual(result['statistics']['lift'], 0.8)  # 4 of 5 cases need the section
        self.assertNotIn('coverage_warning', result)
        self.assertNotIn('proposal', result)
        self.assertEqual(result['cases'][0]['full']['passed'], 1)
        self.assertEqual(result['cases'][0]['ablated']['passed'], 0)

    def test_whole_skill_the_model_no_longer_needs_gets_the_demotion_ladder(self):
        self.write_cases('.', 4)
        result = self.run_ablation()
        self.assertEqual((result['target'], result['decision']), ('skill', 'remove'))
        self.assertEqual([step['step'] for step in result['proposal']['ladder']],
                         ['slash-only', 'disable', 'archive'])
        self.assertIn('jackfield disable magic', [s['action'] for s in result['proposal']['ladder']])
        self.assertNotIn('review', result['proposal'])
        self.assertTrue(any(system == ai_ablate._system('') for system in self.sent))

    def test_useful_whole_skill_is_kept(self):
        self.assertEqual(self.run_ablation()['decision'], 'keep')

    def test_partial_run_never_proposes_removal(self):
        original = ai.AiRun._send.side_effect

        def lose_one(run, *args):
            text = original(run, *args)
            return '' if len(self.sent) == 1 else text
        ai.AiRun._send.side_effect = lose_one
        result = self.run_ablation(section=2, trials=2)
        self.assertEqual((result['status'], result['decision']), ('partial', 'uncertain'))
        self.assertNotIn('proposal', result)

    def test_placebo_swaps_the_section_for_same_length_filler(self):
        result = self.run_ablation(section=0, placebo=True)
        self.assertEqual(result['variants'], ['full', 'ablated', 'placebo'])
        self.assertEqual(len(self.sent), 5 * 3)
        placebo = [system for system in self.sent if 'neutral filler' in system]
        self.assertEqual(len(placebo), 5)
        full = [system for system in self.sent if 'magic word is PINEAPPLE' in system][0]
        self.assertEqual(len(placebo[0]), len(full))
        self.assertEqual(result['placebo_statistics']['lift'], 0.8)
        self.assertIn('placebo', result['cases'][0])
        self.assertIn('same-length filler', result['egress'][0])
        saved = ai_skills.read_run(self.data, result['run_id'])
        self.assertEqual(set(saved['cases'][0]), {'case', 'full', 'ablated', 'placebo'})

    def test_a_repeat_run_points_to_the_previous_verdict_and_model(self):
        first = self.run_ablation(section=0)
        self.assertIsNone(first['previous'])
        _CONFIG['model'] = 'other-model'
        self.addCleanup(_CONFIG.__setitem__, 'model', 'primary-model')
        self.sent.clear()
        second = self.run_ablation(section=0)
        self.assertEqual(second['previous'], {'run_id': first['run_id'], 'decision': 'keep', 'model': 'primary-model',
                                              'same_model': False, 'same_revision': True})
        self.sent.clear()
        self.assertIsNone(self.run_ablation(section=2)['previous'])  # a different section

    def test_damaged_earlier_runs_are_skipped_not_fatal(self):
        first = self.run_ablation(section=0)
        self.sent.clear()
        runs = self.data / 'ai' / 'runs'
        runs.mkdir(parents=True, exist_ok=True)
        for n, body in enumerate(({'name': 'magic', 'decision': 'keep', 'run': 'oops', 'section': {'heading': 'Magic word'}},
                                  {'name': 'magic', 'decision': '\x1b[2Jevil', 'section': {'heading': 'Magic word'}},
                                  {'name': 'magic', 'decision': 'keep', 'section': 'not-a-dict'})):
            (runs / f'ablate-20990101T00000{n}Z-0000000{n}.json').write_text(json.dumps(body), encoding='utf-8')
        result = self.run_ablation(section=0)
        self.assertEqual(result['previous']['run_id'], first['run_id'])
        self.assertNotIn('evil', json.dumps(result['previous']))

    def test_a_previous_section_must_match_the_index_and_revision(self):
        self.store.edit('magic', body=_BODY.replace('## Style', '## Magic word'))
        first = self.run_ablation(section=0)
        self.sent.clear()
        self.assertIsNone(self.run_ablation(section=2)['previous'])
        self.sent.clear()
        self.assertEqual(self.run_ablation(section=0)['previous']['run_id'], first['run_id'])
        self.sent.clear()
        self.store.edit('magic', body=_BODY + '\nUpdated style.\n')
        self.assertIsNone(self.run_ablation(section=0)['previous'])

    def test_placebo_choice_is_bound_to_the_preview(self):
        estimate = ai_ablate.ablate(self.store, {'name': 'magic', 'section': 0, 'estimate': True})
        with self.assertRaises(ai.AiError) as failure:
            ai_ablate.ablate(self.store, {'name': 'magic', 'section': 0, 'placebo': True, 'plan': estimate['plan']})
        self.assertEqual(failure.exception.status, 409)
        with self.assertRaises(ai.AiError):
            ai_ablate.ablate(self.store, {'name': 'magic', 'placebo': 'yes', 'estimate': True})
        self.assertEqual(self.sent, [])

    def test_cases_at_the_ceiling_cannot_justify_removal(self):
        self.write_cases('PINEAPPLE', 4, hard=False)
        result = self.run_ablation(section=2)
        self.assertEqual(result['decision'], 'untested')
        self.assertIn('cannot show', result['reason'])
        self.assertNotIn('proposal', result)

    def test_too_few_cases_propose_nothing(self):
        self.write_cases('.', trial_stats.MIN_CASES - 1, hard=False)
        result = self.run_ablation(section=2, trials=5)
        self.assertEqual(result['decision'], 'not-enough-evidence')
        self.assertNotIn('proposal', result)

    def test_evidence_keeps_counts_not_outputs(self):
        result = self.run_ablation(section=0)
        self.assertIn('PINEAPPLE', result['cases'][0]['full']['first_output'])
        saved = ai_skills.read_run(self.data, result['run_id'])
        text = json.dumps(saved)
        self.assertNotIn('PINEAPPLE', text.replace('the magic word', ''))
        self.assertNotIn('first_output', text)
        self.assertEqual(saved['cases'][0]['full'], {'passed': 1, 'graded': 1, 'answers': 1})

    def test_changed_inputs_after_preview_are_refused(self):
        estimate = ai_ablate.ablate(self.store, {'name': 'magic', 'section': 2, 'estimate': True})
        for change in ({'section': 0}, {'trials': 2}):
            with self.subTest(change=change), self.assertRaises(ai.AiError) as failure:
                ai_ablate.ablate(self.store, {'name': 'magic', 'section': 2, 'plan': estimate['plan'], **change})
            self.assertEqual(failure.exception.status, 409)
        (self.skill / 'SKILL.md').write_text((self.skill / 'SKILL.md').read_text() + 'More.\n')
        with self.assertRaises(ai.AiError):
            ai_ablate.ablate(self.store, {'name': 'magic', 'section': 2, 'plan': estimate['plan']})
        self.assertEqual(self.sent, [])

    def test_bad_input_is_refused_before_any_send(self):
        for payload in ({'section': 9}, {'section': '1'}, {'section': True}, {'trials': 0},
                        {'trials': 6}, {'name': '../magic'}, {'name': 'missing'}):
            with self.subTest(payload=payload), self.assertRaises(Exception):
                ai_ablate.ablate(self.store, {'name': 'magic', 'estimate': True, **payload})
        self.store.disable('magic')
        with self.assertRaises(ai.AiError):
            ai_ablate.ablate(self.store, {'name': 'magic', 'estimate': True})
        self.assertEqual(self.sent, [])

    def test_skill_changed_during_the_run_reports_instead_of_staging(self):
        document = self.skill / 'SKILL.md'
        original = ai.AiRun._send.side_effect

        def send_and_edit(run, *args):
            if len(self.sent) == 3:
                document.write_text(document.read_text() + 'Edited meanwhile.\n')
            return original(run, *args)
        ai.AiRun._send.side_effect = send_and_edit
        result = self.run_ablation(section=2)
        self.assertEqual(result['decision'], 'remove')
        self.assertNotIn('proposal', result)
        self.assertIn('changed', result['proposal_error'])
        self.assertIn('Edited meanwhile.', document.read_text())



@unittest.skipUnless(os.name == 'posix' and getattr(os, 'O_NOFOLLOW', 0)
                     and os.scandir in os.supports_fd, 'descriptor capture unavailable')
class AblateCliTests(unittest.TestCase):
    def setUp(self):
        import contextlib
        import io
        self.contextlib, self.io = contextlib, io
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name) / 'base'
        self.base.mkdir(mode=0o700)
        store = Store(self.base / 'skills-manager')
        self.addCleanup(context.set_active_store, None)
        store.create('magic', 'Use magic when asked for the magic word.', body=_BODY)
        cases = {'skill_name': 'magic', 'evals': [
            {'id': n, 'prompt': f'Word? ({n})', 'expected_output': 'x',
             'assertions': [{'type': 'contains', 'value': 'PINEAPPLE'}]} for n in range(1, 5)]
            + [{'id': 9, 'prompt': 'Fruit?', 'expected_output': 'x',
                'assertions': [{'type': 'contains', 'value': 'BANANA'}]}]}
        (store.skills_dir / 'magic/evals').mkdir()
        (store.skills_dir / 'magic/evals/evals.json').write_text(json.dumps(cases), encoding='utf-8')
        self.sent = []

        def send(run, system, *_args):
            run.calls += 1
            run.last_truncated = False
            self.sent.append(system)
            return _answer(system)
        for patcher in (patch.object(ai, 'resolve_config', side_effect=lambda *_: dict(_CONFIG)),
                        patch.object(ai.AiRun, '_send', autospec=True, side_effect=send)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def invoke(self, *flags):
        from skillsmgr import cli
        out, err = self.io.StringIO(), self.io.StringIO()
        with self.contextlib.redirect_stdout(out), self.contextlib.redirect_stderr(err):
            code = cli.main(['--data-dir', str(self.base), 'ai', 'ablate', 'magic', *flags])
        return code, out.getvalue(), err.getvalue()

    def test_without_run_nothing_is_sent_and_sections_are_listed(self):
        code, out, _ = self.invoke('--section', '2')
        self.assertEqual((code, self.sent), (0, []))
        self.assertIn('[0] ## Magic word', out)
        self.assertIn('Testing: section Style', out)

    def test_run_prints_decision_and_staged_review(self):
        code, out, _ = self.invoke('--section', '2', '--trials', '1', '--run')
        self.assertEqual(code, 0)
        self.assertIn('Decision: remove', out)
        self.assertIn('jackfield update apply magic ', out)
        code, out, _ = self.invoke('--trials', '1', '--run', '--json')
        report = json.loads(out)
        self.assertEqual((report['command'], report['result']['decision']), ('ai ablate', 'keep'))

    def test_bad_section_is_a_clean_error(self):
        code, out, err = self.invoke('--section', '7', '--json')
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)['error']['code'], 'ai-input')


if __name__ == '__main__':
    unittest.main()
