"""Paired statistics for repeated AI eval trials.

Pure and stdlib-only. Each observation is one graded model output for one case,
one variant (for example ``with_skill``) and one trial. The summary compares a
treatment variant with a baseline variant case by case. It reports the mean
paired lift in case pass rate with a percentile bootstrap interval that
resamples cases and, within each case, trials. A fixed seed makes the interval
a pure function of the observations.

A result is "inconclusive" when the interval includes zero, when fewer than
three requests were graded (repeats of one request say nothing about others),
or when there are too few graded paired observations. The interval describes
the supplied requests only. Ungraded or incomplete
outputs are excluded and counted, never treated as failures.
"""
from __future__ import annotations

import random

CONFIDENCE = 0.95
RESAMPLES = 2000
MIN_OBSERVATIONS = 4
MIN_CASES = 3
TOKEN_RATIO = 1.25
TOKEN_MIN_DELTA = 50
_SEED = 20261122


def _outcomes(rows: list, variant: str) -> dict:
    """Map case -> list of 1.0/0.0 outcomes for one variant (graded rows only)."""
    found: dict = {}
    for row in rows:
        if row.get('variant') == variant and row.get('passed') is not None:
            found.setdefault(row.get('case'), []).append(1.0 if row['passed'] else 0.0)
    return found


def _mean(values: list) -> float:
    return sum(values) / len(values)


def _bootstrap(pairs: list, rng: random.Random) -> tuple[float, float]:
    estimates = []
    for _ in range(RESAMPLES):
        total = 0.0
        for _case in range(len(pairs)):
            treated, base = pairs[rng.randrange(len(pairs))]
            total += (_mean([treated[rng.randrange(len(treated))] for _ in treated])
                      - _mean([base[rng.randrange(len(base))] for _ in base]))
        estimates.append(total / len(pairs))
    estimates.sort()
    tail = (1 - CONFIDENCE) / 2
    low = estimates[int(tail * (RESAMPLES - 1))]
    high = estimates[int((1 - tail) * (RESAMPLES - 1))]
    return round(low, 4), round(high, 4)


def _verdict(cases: int, observations: int, interval) -> tuple[str, str]:
    if observations == 0:
        return 'ungraded', 'no case has graded outputs for both variants'
    if cases < MIN_CASES:
        return 'inconclusive', f'fewer than {MIN_CASES} graded requests; repeats alone cannot show a general effect'
    if observations < MIN_OBSERVATIONS:
        return 'inconclusive', f'fewer than {MIN_OBSERVATIONS} graded paired observations'
    low, high = interval
    if low > 0:
        return 'helps', 'the whole interval is above zero for these requests'
    if high < 0:
        return 'hurts', 'the whole interval is below zero for these requests'
    return 'inconclusive', 'the interval includes zero'


def _tokens(rows: list, treatment: str, baseline: str) -> dict:
    means = {}
    for variant in (treatment, baseline):
        counts = [row['tokens'] for row in rows
                  if row.get('variant') == variant and isinstance(row.get('tokens'), int)]
        means[variant] = round(_mean(counts), 1) if counts else None
    treated, base = means[treatment], means[baseline]
    known = treated is not None and base is not None
    ratio = round(treated / base, 3) if known and base > 0 else None
    regression = bool(known and treated - base >= TOKEN_MIN_DELTA and (ratio is None or ratio >= TOKEN_RATIO))
    return {'mean_output_tokens': means, 'ratio': ratio, 'regression': regression}


def non_discriminating(rows: list) -> list:
    """Assertions with one result across every variant and trial of a case.

    Such an assertion cannot tell the variants apart. It is reported only when
    at least two variants were graded for that case.
    """
    seen: dict = {}
    for row in rows:
        results = row.get('assertions')
        if not isinstance(results, list):
            continue
        for index, passed in enumerate(results):
            entry = seen.setdefault((row.get('case'), index), {'variants': set(), 'values': set()})
            entry['variants'].add(row.get('variant'))
            entry['values'].add(bool(passed))
    flagged = []
    for (case, index), entry in seen.items():
        if len(entry['variants']) > 1 and len(entry['values']) == 1:
            flagged.append({'case': case, 'assertion': index,
                            'always': 'passes' if True in entry['values'] else 'fails'})
    return sorted(flagged, key=lambda item: (str(item['case']), item['assertion']))


def summarize(rows: list, treatment: str, baseline: str) -> dict:
    """Compare ``treatment`` with ``baseline`` over paired cases.

    ``rows`` items carry ``case``, ``variant``, ``trial``, ``passed`` (``True``,
    ``False`` or ``None`` when ungraded or incomplete), optional ``tokens`` and
    optional ``assertions`` (a list of booleans).
    """
    treated, base = _outcomes(rows, treatment), _outcomes(rows, baseline)
    cases = [case for case in treated if case in base]
    pairs = [(treated[case], base[case]) for case in cases]
    observations = sum(min(len(t), len(b)) for t, b in pairs)
    relevant = [row for row in rows if row.get('variant') in (treatment, baseline)]
    result = {
        'treatment': treatment, 'baseline': baseline, 'paired_cases': len(cases),
        'trials': max((row.get('trial', 1) for row in relevant), default=0),
        'observations': observations,
        'excluded': sum(1 for row in relevant if row.get('passed') is None),
        'pass_rate': {treatment: None, baseline: None}, 'lift': None, 'interval': None,
        'confidence': CONFIDENCE,
        'tokens': _tokens(relevant, treatment, baseline),
        'non_discriminating': non_discriminating(relevant),
        'meaning': 'lift is the mean over paired cases of the treatment pass rate minus the baseline pass rate',
    }
    if pairs:
        result['pass_rate'] = {treatment: round(_mean([_mean(t) for t, _ in pairs]), 4),
                               baseline: round(_mean([_mean(b) for _, b in pairs]), 4)}
        result['lift'] = round(_mean([_mean(t) - _mean(b) for t, b in pairs]), 4)
        result['interval'] = list(_bootstrap(pairs, random.Random(_SEED)))
    result['verdict'], result['reason'] = _verdict(len(cases), observations, result['interval'])
    return result
