"""Paired trial statistics: verdicts, intervals and flags."""
import random
import unittest

from skillsmgr import trial_stats


def _rows(outcomes: dict, tokens: dict | None = None) -> list:
    """outcomes: {(case, variant): [True/False/None, ...]} one entry per trial."""
    rows = []
    for (case, variant), results in outcomes.items():
        for trial, passed in enumerate(results, start=1):
            rows.append({'case': case, 'variant': variant, 'trial': trial, 'passed': passed,
                         'tokens': (tokens or {}).get(variant)})
    return rows


class SummaryTests(unittest.TestCase):
    def test_no_rows_is_ungraded(self):
        result = trial_stats.summarize([], 'with_skill', 'without_skill')
        self.assertEqual(result['verdict'], 'ungraded')
        self.assertIsNone(result['lift'])
        self.assertIsNone(result['interval'])

    def test_one_trial_one_case_is_inconclusive_even_when_it_looks_decisive(self):
        rows = _rows({('a', 'with_skill'): [True], ('a', 'without_skill'): [False]})
        result = trial_stats.summarize(rows, 'with_skill', 'without_skill')
        self.assertEqual(result['lift'], 1.0)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertIn('fewer than', result['reason'])

    def test_repeating_one_or_two_requests_is_never_conclusive(self):
        for cases in ('a', 'ab'):
            outcomes = {}
            for case in cases:
                outcomes[(case, 't')] = [True] * 5
                outcomes[(case, 'b')] = [False] * 5
            result = trial_stats.summarize(_rows(outcomes), 't', 'b')
            self.assertEqual(result['verdict'], 'inconclusive', cases)
            self.assertIn('fewer than 3 graded requests', result['reason'])

    def test_consistent_difference_over_enough_trials_helps(self):
        outcomes = {}
        for case in 'abcd':
            outcomes[(case, 'with_skill')] = [True, True, True]
            outcomes[(case, 'without_skill')] = [False, False, False]
        result = trial_stats.summarize(_rows(outcomes), 'with_skill', 'without_skill')
        self.assertEqual(result['verdict'], 'helps')
        self.assertEqual(result['interval'], [1.0, 1.0])
        self.assertEqual(result['observations'], 12)
        self.assertEqual(result['trials'], 3)

    def test_reversed_roles_hurt(self):
        outcomes = {}
        for case in 'abcd':
            outcomes[(case, 'candidate')] = [False, False]
            outcomes[(case, 'current')] = [True, True]
        self.assertEqual(trial_stats.summarize(_rows(outcomes), 'candidate', 'current')['verdict'], 'hurts')

    def test_mixed_results_include_zero(self):
        outcomes = {('a', 't'): [True, False, True], ('a', 'b'): [False, True, True],
                    ('b', 't'): [False, True, False], ('b', 'b'): [True, False, True]}
        result = trial_stats.summarize(_rows(outcomes), 't', 'b')
        self.assertEqual(result['verdict'], 'inconclusive')
        low, high = result['interval']
        self.assertLessEqual(low, 0)
        self.assertGreaterEqual(high, 0)

    def test_ungraded_and_unpaired_rows_are_excluded_not_failed(self):
        outcomes = {('a', 't'): [True, None], ('a', 'b'): [False, None], ('only-t', 't'): [True]}
        result = trial_stats.summarize(_rows(outcomes), 't', 'b')
        self.assertEqual(result['paired_cases'], 1)
        self.assertEqual(result['excluded'], 2)
        self.assertEqual(result['pass_rate'], {'t': 1.0, 'b': 0.0})

    def test_interval_is_deterministic(self):
        rng = random.Random(3)
        outcomes = {(c, v): [rng.random() < 0.6 for _ in range(3)] for c in range(6) for v in 'tb'}
        rows = _rows(outcomes)
        self.assertEqual(trial_stats.summarize(rows, 't', 'b'), trial_stats.summarize(rows, 't', 'b'))

    def test_interval_covers_a_known_lift(self):
        rng = random.Random(11)
        covered = 0
        for _ in range(60):
            probabilities = [rng.uniform(0.3, 0.9) for _ in range(8)]
            true_lift = 0.2
            outcomes = {}
            for case, p in enumerate(probabilities):
                outcomes[(case, 't')] = [rng.random() < p for _ in range(3)]
                outcomes[(case, 'b')] = [rng.random() < p - true_lift for _ in range(3)]
            low, high = trial_stats.summarize(_rows(outcomes), 't', 'b')['interval']
            covered += low <= true_lift <= high
        self.assertGreaterEqual(covered / 60, 0.85)


class PowerTests(unittest.TestCase):
    def test_min_detectable_shrinks_with_more_cases_and_has_a_floor(self):
        def run(n):
            outcomes = {}
            for case in range(n):
                outcomes[(case, 't')] = [True]
                outcomes[(case, 'b')] = [True]
            return trial_stats.summarize(_rows(outcomes), 't', 'b')['min_detectable']
        # Identical cases show no spread; the 0.5 floor keeps the estimate honest.
        self.assertAlmostEqual(run(4), 0.7)
        self.assertAlmostEqual(run(100), 0.14)
        self.assertIsNone(trial_stats.summarize([], 't', 'b')['min_detectable'])

    def test_trials_are_not_resampled_twice(self):
        # One case flips within trials but every case has the same mean difference,
        # so a cases-only bootstrap gives a zero-width interval.
        outcomes = {}
        for case in 'abcd':
            outcomes[(case, 't')] = [True, False]
            outcomes[(case, 'b')] = [False, False]
        self.assertEqual(trial_stats.summarize(_rows(outcomes), 't', 'b')['interval'], [0.5, 0.5])


class FlagTests(unittest.TestCase):
    def test_token_regression_needs_ratio_and_absolute_delta(self):
        outcomes = {('a', 't'): [True], ('a', 'b'): [True]}
        flagged = trial_stats.summarize(_rows(outcomes, {'t': 400, 'b': 200}), 't', 'b')['tokens']
        self.assertTrue(flagged['regression'])
        self.assertEqual(flagged['ratio'], 2.0)
        small = trial_stats.summarize(_rows(outcomes, {'t': 30, 'b': 10}), 't', 'b')['tokens']
        self.assertFalse(small['regression'])
        unknown = trial_stats.summarize(_rows(outcomes), 't', 'b')['tokens']
        self.assertFalse(unknown['regression'])
        self.assertIsNone(unknown['ratio'])

    def test_non_discriminating_assertions_are_flagged_per_case(self):
        rows = [
            {'case': 'a', 'variant': 't', 'trial': 1, 'passed': True, 'assertions': [True, True]},
            {'case': 'a', 'variant': 'b', 'trial': 1, 'passed': False, 'assertions': [True, False]},
            {'case': 'b', 'variant': 't', 'trial': 1, 'passed': False, 'assertions': [False]},
        ]
        self.assertEqual(trial_stats.non_discriminating(rows),
                         [{'case': 'a', 'assertion': 0, 'always': 'passes'}])


if __name__ == '__main__':
    unittest.main()
