"""Contradiction candidates and the optional AI judge (docs/60 G2)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillsmgr import ai, ai_conflicts, ai_skills, conflicts, context

_CONFIG = {'provider': 'custom', 'label': 'Fake', 'model': 'primary-model', 'local': True,
           'base_url': 'http://127.0.0.1:9/v1', 'max_run_tokens': 10 ** 9, 'max_day_tokens': 10 ** 9}

USER_RULES = ('# Me\n'
              '- Use pnpm, never npm.\n'
              '- Always commit after each change.\n'
              '- Prefer small functions.\n')
PROJECT_RULES = ('# Project\n'
                 '- Indent with 4 spaces.\n'
                 '- Write docs in plain English.\n'
                 '```\n- Never commit after each change.\n```\n')


class ExtractionTests(unittest.TestCase):
    def test_stances_follow_clauses_and_negation(self):
        self.assertEqual(conflicts.stances('Use pnpm instead of npm')['JavaScript package manager'],
                         {'positive': {'pnpm'}, 'negative': {'npm'}})
        self.assertEqual(conflicts.stances('Never use npm; use pnpm.')['JavaScript package manager'],
                         {'positive': {'pnpm'}, 'negative': {'npm'}})
        self.assertEqual(conflicts.stances('Run `uv sync` first')['Python package tool']['positive'], {'uv'})
        self.assertEqual(conflicts.stances('Open the browser tabs view.'), {})

    def test_rules_skip_fences_headings_and_plain_prose(self):
        found = conflicts.rules('# Never a heading\nPlain prose line here.\n```\nnever inside\n```\n'
                                '  - Always run tests.  \n')
        self.assertEqual([(r['line'], r['quote']) for r in found], [(6, '- Always run tests.')])


class ConflictFixture(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name).resolve()
        self.home = base / 'home'
        self.project = base / 'project'
        self.data = base / 'data'
        for path in (self.home, self.project, self.data):
            path.mkdir(mode=0o700)
        old = {key: os.environ.get(key) for key in ('HOME', 'SKILLS_MANAGER_DATA')}
        os.environ['HOME'] = str(self.home)
        os.environ['SKILLS_MANAGER_DATA'] = str(self.data)
        context.set_active_store(None)

        def restore():
            context.set_active_store(None)
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.addCleanup(restore)
        (self.home / '.claude').mkdir()
        (self.home / '.claude/CLAUDE.md').write_text(USER_RULES, encoding='utf-8')
        (self.project / 'AGENTS.md').write_text(PROJECT_RULES, encoding='utf-8')
        self.skill('node-setup', '1. Run `npm install` before testing.\n')
        self.skill('tidy', '- Indent with tabs in every file.\n')
        self.skill('careful', '- Never commit after each change without asking.\n')
        self.skill('unrelated', '- Always explain the plan before editing.\n- Prefer small functions.\n')

    def skill(self, name, body):
        folder = self.home / '.claude/skills' / name
        folder.mkdir(parents=True)
        (folder / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: Use for {name}.\n---\n{body}',
                                         encoding='utf-8')

    def report(self, **payload):
        return ai_conflicts.check(self.data, {'scope': 'claude-code', 'project': str(self.project), **payload})

    @staticmethod
    def pair_names(report):
        return {frozenset((pair['a'].get('skill') or pair['a']['source'],
                           pair['b'].get('skill') or pair['b']['source'])) for pair in report['candidates']}


class CheckTests(ConflictFixture):
    def test_seeded_conflicts_are_found_and_unrelated_pairs_are_not(self):
        report = self.report()
        names = self.pair_names(report)
        self.assertIn(frozenset(('node-setup', '~/.claude/CLAUDE.md')), names)
        self.assertIn(frozenset(('careful', '~/.claude/CLAUDE.md')), names)
        self.assertTrue(any('tidy' in pair and any('AGENTS.md' in side for side in pair) for pair in names))
        self.assertFalse(any('unrelated' in pair for pair in names))
        self.assertEqual({p['kind'] for p in report['candidates']}, {'choice', 'polarity'})
        self.assertTrue(all(p['precedence'] == 'unknown' and p['basis'] == 'heuristic'
                            for p in report['candidates']))
        self.assertTrue(report['writes_nothing'])

    def test_skill_against_skill_and_bare_mentions_are_not_paired(self):
        self.skill('pnpm-fan', '- Always use pnpm for installs.\n')
        self.skill('yarn-fan', '- Always use yarn for installs.\n')
        (self.home / '.claude/CLAUDE.md').write_text('Runtimes we see: Node, Bun and Deno.\n', encoding='utf-8')
        names = self.pair_names(self.report())
        self.assertNotIn(frozenset(('pnpm-fan', 'yarn-fan')), names)
        self.assertFalse(any('pnpm-fan' in pair or 'yarn-fan' in pair for pair in names))

    def test_every_quote_is_verbatim_and_located(self):
        report = self.report()
        texts = {'~/.claude/CLAUDE.md': USER_RULES}
        for path in (self.home / '.claude/skills').iterdir():
            texts[f'skill {path.name} (claude-code)'] = (path / 'SKILL.md').read_text()
        texts[str(self.project / 'AGENTS.md')] = PROJECT_RULES
        for pair in report['candidates']:
            for side in (pair['a'], pair['b']):
                lines = texts[side['source']].splitlines()
                self.assertEqual(lines[side['line'] - 1].strip(), side['quote'])

    def test_library_skills_are_read_from_disk(self):
        from skillsmgr.store import Store
        store = Store(self.data)
        context.set_active_store(store)
        store.create('lib-node', 'Use for node.', body='Intro.\n\n- Run `npm ci` first.\n')
        report = self.report(scope='global')
        sides = [side for pair in report['candidates'] for side in (pair['a'], pair['b'])
                 if side.get('skill') == 'lib-node']
        self.assertTrue(sides)
        lines = (store.skills_dir / 'lib-node/SKILL.md').read_text().splitlines()
        self.assertEqual(lines[sides[0]['line'] - 1].strip(), sides[0]['quote'])

    def test_line_numbers_match_the_file_for_crlf_and_unicode_separators(self):
        folder = self.home / '.claude/skills/crlf-node'
        folder.mkdir(parents=True)
        (folder / 'SKILL.md').write_bytes(
            b'---\r\nname: crlf-node\r\ndescription: Use for node.\r\n---\r\nIntro\xe2\x80\xa8still intro.\r\n'
            b'- Run `npm ci` first.\r\n')
        sides = [side for p in self.report()['candidates'] for side in (p['a'], p['b'])
                 if side.get('skill') == 'crlf-node']
        self.assertEqual([side['line'] for side in sides], [6])
        self.assertEqual(sides[0]['quote'], '- Run `npm ci` first.')

    def test_long_lines_are_skipped_not_cut(self):
        long_line = '- Never use npm ' + 'because ' * 60 + 'unless asked.'
        self.assertGreater(len(long_line), conflicts.MAX_QUOTE)
        self.assertEqual(conflicts.rules(long_line + '\n'), [])

    def test_a_skill_document_that_links_elsewhere_is_not_read(self):
        outside = self.home / 'secret.md'
        outside.write_text('---\nname: linked\ndescription: x\n---\n- Run `npm i` secretly.\n', encoding='utf-8')
        folder = self.home / '.claude/skills/linked'
        folder.mkdir(parents=True)
        (folder / 'SKILL.md').symlink_to(outside)
        self.assertNotIn('secretly', json.dumps(self.report()))

    def test_a_word_common_across_skills_still_pairs_with_instructions(self):
        for n in range(45):
            self.skill(f'filler-{n}', f'- Always commit tidy history number {n}.\n')
        names = self.pair_names(self.report())
        self.assertIn(frozenset(('careful', '~/.claude/CLAUDE.md')), names)

    def test_dropped_inputs_are_reported(self):
        many = ''.join(f'- Always use pnpm in step {n}.\n' for n in range(conflicts.MAX_RULES_PER_SOURCE + 5))
        (self.home / '.claude/CLAUDE.md').write_text(many, encoding='utf-8')
        limited = self.report()['inputs_limited']
        self.assertTrue(any('first 300 instruction lines' in line for line in limited))

    def test_fenced_lines_are_not_rules(self):
        quotes = {side['quote'] for p in self.report()['candidates'] for side in (p['a'], p['b'])}
        self.assertNotIn('- Never commit after each change.', quotes)

    def test_project_links_outside_the_project_are_not_read(self):
        outside = self.home / 'outside.md'
        outside.write_text('- Use yarn always.\n', encoding='utf-8')
        (self.project / 'CLAUDE.md').symlink_to(outside)
        report = self.report()
        self.assertIn(str(self.project / 'CLAUDE.md'), report['unreadable'])
        self.assertNotIn('- Use yarn always.', json.dumps(report))

    def test_project_outside_allowed_roots_is_refused(self):
        with self.assertRaises(ai.AiError):
            ai_conflicts.check(self.data, {'scope': 'claude-code', 'project': str(self.project)},
                               allowed_roots=[self.data])
        with self.assertRaises(ai.AiError):
            ai_conflicts.check(self.data, {'scope': 'all'})

    def test_judge_keeps_file_quotes_and_drops_bad_verdicts(self):
        sent = []

        def ask(run, system, user, **_kwargs):
            sent.append(user)
            if run.estimate_only:
                return None
            ids = [line.split()[1] for line in user.splitlines() if line.startswith('Pair ')]
            return {'verdicts': [{'id': ids[0], 'verdict': 'conflict', 'why': 'npm vs pnpm',
                                  'quote': 'invented text'},
                                 {'id': ids[0], 'verdict': 'compatible', 'why': 'duplicate'},
                                 {'id': 'nope', 'verdict': 'conflict', 'why': 'unknown id'}]
                    + [{'id': ident, 'verdict': 'maybe'} for ident in ids[1:]]}
        with patch.object(ai, 'resolve_config', side_effect=lambda *_: dict(_CONFIG)), \
                patch.object(ai.AiRun, 'ask_json', autospec=True, side_effect=ask):
            estimate = self.report(judge=True, max_pairs=3, estimate=True)
            self.assertEqual(estimate['status'], 'estimate')
            self.assertIn('not whole files', estimate['egress'][0])
            result = self.report(judge=True, max_pairs=3, plan=estimate['plan'])
        self.assertEqual(len(result['conflicts']), 1)
        conflict = result['conflicts'][0]
        self.assertEqual(conflict['judge'], {'verdict': 'conflict', 'why': 'npm vs pnpm', 'basis': 'ai'})
        self.assertNotIn('invented text', json.dumps(result))
        self.assertEqual((result['judged'], result['status']), (1, 'partial'))
        self.assertNotIn(USER_RULES.splitlines()[3], ''.join(sent))  # unrelated line never sent
        saved = ai_skills.read_run(self.data, result['run_id'])
        self.assertEqual(saved['conflicts'][0]['id'], conflict['id'])

    def test_changed_files_after_preview_are_refused(self):
        with patch.object(ai, 'resolve_config', side_effect=lambda *_: dict(_CONFIG)), \
                patch.object(ai.AiRun, 'ask_json', return_value=None):
            estimate = self.report(judge=True, estimate=True)
            (self.home / '.claude/CLAUDE.md').write_text(USER_RULES + '- Use yarn always.\n', encoding='utf-8')
            with self.assertRaises(ai.AiError) as failure:
                self.report(judge=True, plan=estimate['plan'])
        self.assertEqual(failure.exception.status, 409)

    def test_judge_input_is_validated(self):
        for bad in (0, 41, '3', True):
            with self.subTest(bad=bad), self.assertRaises(ai.AiError):
                self.report(judge=True, max_pairs=bad, estimate=True)


if __name__ == '__main__':
    unittest.main()


class ConflictsCliTests(ConflictFixture):
    def invoke(self, *flags):
        import contextlib
        import io

        from skillsmgr import cli
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(['--data-dir', str(self.data), 'ai', 'conflicts', '--scope', 'claude-code',
                                 '--project', str(self.project), *flags])
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_candidates_need_no_model_and_quote_both_sides(self):
        with patch.object(ai, 'resolve_config', side_effect=AssertionError('no model')):
            code, out, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertIn('~/.claude/CLAUDE.md:2: - Use pnpm, never npm.', out)
        self.assertIn('1. Run `npm install` before testing.', out)

    def test_run_requires_judge(self):
        code, _, err = self.invoke('--run')
        self.assertEqual(code, 2)
        self.assertIn('--run requires --judge', err)

    def test_judge_estimate_sends_nothing(self):
        with patch.object(ai, 'resolve_config', side_effect=lambda *_: dict(_CONFIG)), \
                patch.object(ai.AiRun, '_send', side_effect=AssertionError('sent')):
            code, out, _ = self.invoke('--judge', '--json')
        report = json.loads(out)
        self.assertEqual((code, report['status'], report['command']), (0, 'estimate', 'ai conflicts'))
