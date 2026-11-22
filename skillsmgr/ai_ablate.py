"""Ablate and retire (docs/60 G1): does this skill or section earn its place?

Replays a library skill's saved eval cases (``evals/evals.json``) twice per
trial: once with the whole skill (``full``) and once with one section removed,
or with no skill at all (``ablated``). The slice 1 paired statistics
(``trial_stats``) compare the two, and the decision is deliberately biased
towards subtraction: removal is proposed when the upper end of the interval
says removing it costs at most ``MARGIN`` of the pass rate on these requests.

* ``remove`` -- removal costs at most ``MARGIN`` (ties go to deletion).
* ``keep`` -- the whole interval is above zero: it helps on these requests.
* ``uncertain`` -- the interval is too wide to show removal is safe.
* ``not-enough-evidence`` -- fewer graded requests or observations than the
  statistics need; nothing is proposed.

A section ``remove`` stages an ordinary reviewed edit (the same review the AI
edit dialog uses), so nothing changes until the user saves it, and Recovery
keeps the previous copy. A whole-skill ``remove`` only proposes the demotion
ladder (slash-only, disabled, archived) with the exact action for each step;
nothing is written. The saved evidence holds pass counts, never outputs.
"""
from __future__ import annotations

import random
from pathlib import Path

from . import ai_concise, ai_evals, evals, source_update, trial_stats
from .ai import AiError, AiRun
from .ai_skills import _save_run
from .tokens import count_tokens

MARGIN = 0.10
MAX_TRIALS = 5
_REQUEST_SUMMARY = 200


def sections(body: str) -> list[dict]:
    """Headed sections of a skill body with character offsets.

    A section runs from its heading to the next heading of the same or a
    higher level, so it includes its own subsections. Headings inside code
    fences are ignored. Text before the first heading is not a section.
    """
    heads, fence, offset = [], None, 0
    for number, line in enumerate(body.splitlines(keepends=True), 1):
        bare = line.rstrip('\r\n')
        match = ai_concise._FENCE.match(bare)
        if match:
            marker, tail = match.groups()
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not tail.strip():
                fence = None
        elif fence is None:
            title = ai_concise._HEADING.match(bare)
            if title:
                heads.append((offset, len(title.group(1)), title.group(2).strip(), number))
        offset += len(line)
    rows = []
    for index, (start, level, heading, line) in enumerate(heads):
        end = next((other[0] for other in heads[index + 1:] if other[1] <= level), len(body))
        text = body[start:end]
        rows.append({'index': index, 'heading': heading[:200], 'level': level, 'line': line,
                     'start': start, 'end': end, 'chars': len(text), 'tokens': count_tokens(text)[0]})
    return rows


def _without(body: str, section: dict) -> str:
    """The body with one section removed, exactly: the text before and after it."""
    return body[:section['start']] + body[section['end']:]


def _trial_count(value) -> int:
    if value is None:
        return 1
    if type(value) is not int or not 1 <= value <= MAX_TRIALS:
        raise AiError(f'trials must be a whole number from 1 to {MAX_TRIALS}', 'ai-input')
    return value


def _chosen(listed: list, value):
    if value is None:
        return None
    if type(value) is not int or not 0 <= value < len(listed):
        raise AiError('choose one of the listed sections', 'ai-input')
    return listed[value]


def _library_skill(store, name) -> tuple[dict, dict, dict, str, str, str, str]:
    skill_dir = ai_evals._skill_dir(store, name)
    try:
        target = source_update._resolve_target(store.data_dir, name, 'global', skill_dir)
    except (source_update.SourceUpdateError, TypeError, ValueError) as exc:
        raise AiError(str(exc), 'ai-input') from None
    if target['disabled']:
        raise AiError('turn this skill on before testing it', 'ai-input')
    files, directories, digest = ai_concise._capture(Path(target['physical_path']))
    primary, prefix, body = ai_concise._document(files, False, name)
    return target, files, directories, digest, primary, prefix, body


def _system(document: str) -> str:
    if not document:
        return ai_evals._BASE
    return ai_evals._BASE + '\n\nFollow this skill whenever it applies:\n\n' + document


def _calls(run: AiRun, cases: list, prompts: dict, documents: dict, trials: int) -> list:
    """Every (trial, case, variant) call in a random order; one graded row per answer."""
    order = [(trial, case, label) for trial in range(1, trials + 1) for case in cases for label in documents]
    random.SystemRandom().shuffle(order)
    rows = []
    for trial, case, label in order:
        before = run.output_tokens
        output = run.ask_text(_system(documents[label]), prompts[case['id']], max_output=ai_evals.MAX_EVAL_OUTPUT)
        if output is None:
            continue
        output = output[:evals.MAX_OUTPUT_TEXT]
        complete = bool(output.strip()) and not run.last_truncated
        grade = evals.grade_output(case, output) if complete else None
        graded = bool(grade and grade['graded'])
        rows.append({'case': case['id'], 'variant': label, 'trial': trial,
                     'passed': grade['passed'] == grade['total'] if graded else None,
                     'tokens': run.output_tokens - before,
                     'assertions': [item['passed'] for item in grade['assertions']] if graded else None,
                     'output': output})
    return rows


def decide(stats: dict) -> tuple[str, str]:
    """Turn ``full`` vs ``ablated`` statistics into a removal decision."""
    if (stats['paired_cases'] < trial_stats.MIN_CASES
            or stats['observations'] < trial_stats.MIN_OBSERVATIONS or not stats['interval']):
        return 'not-enough-evidence', (
            f"needs at least {trial_stats.MIN_CASES} graded requests and {trial_stats.MIN_OBSERVATIONS} "
            'graded pairs; add eval cases with assertions or more trials')
    low, high = stats['interval']
    if low > 0:
        return 'keep', 'it helps on these requests: the whole interval is above zero'
    if high <= MARGIN:
        return 'remove', (f'removing it costs at most {round(high * 100)} points of pass rate on these '
                          f'requests (limit {round(MARGIN * 100)}); ties go to removal')
    return 'uncertain', 'the interval is too wide to show removal is safe; add cases or trials'


def _discriminates(rows: list) -> bool:
    """Whether any single check had a different pass rate with and without it.

    Rates, not single results: a check that flips between trials of the same
    variant is flaky, not evidence that the removed text matters.
    """
    seen: dict = {}
    for row in rows:
        for index, passed in enumerate(row['assertions'] or []):
            counts = seen.setdefault((row['case'], index), {}).setdefault(row['variant'], [0, 0])
            counts[0] += bool(passed)
            counts[1] += 1
    return any(len({round(hit / total, 6) for hit, total in variants.values()}) > 1
               for variants in seen.values() if len(variants) > 1)


def _per_case(rows: list, cases: list) -> list:
    out = []
    for case in cases:
        entry = {'case': case['id']}
        for label in ('full', 'ablated'):
            mine = sorted((row for row in rows if row['case'] == case['id'] and row['variant'] == label),
                          key=lambda row: row['trial'])
            graded = [row['passed'] for row in mine if row['passed'] is not None]
            entry[label] = {'passed': sum(graded), 'graded': len(graded), 'answers': len(mine),
                            'first_output': mine[0]['output'] if mine else None}
        out.append(entry)
    return out


def _ladder(name: str) -> list:
    return [
        {'step': 'slash-only', 'effect': 'Stays available as /' + name + ' but is no longer offered automatically.',
         'action': 'Edit the skill and add "disable-model-invocation: true" to its frontmatter.',
         'applies_to': 'Claude Code documents this field; other agents may ignore it.'},
        {'step': 'disable', 'effect': 'Kept in the library but loaded by no agent.',
         'action': f'skills-mgr disable {name}', 'applies_to': 'every agent this library feeds'},
        {'step': 'archive', 'effect': 'Moved out of the library; restorable from Archive.',
         'action': f'skills-mgr archive apply {name}', 'applies_to': 'every agent this library feeds'},
    ]


def _stage_removal(store, target, files, directories, digest, primary, prefix, body, proposed, run, section):
    provenance = {'feature': 'ablate', 'model': run.config['model'], 'provider': run.config['label'],
                  'local': bool(run.config['local']),
                  'request': f'Remove section "{section["heading"]}"'[:_REQUEST_SUMMARY],
                  'section': section['heading'][:40]}
    disk = proposed.replace('\n', '\r\n') if prefix.endswith('\r\n') else proposed
    review = ai_concise._stage(store.data_dir, target, files, directories, digest, primary, prefix,
                               {'body': disk, 'references': []}, local_edit=True, provenance=provenance)
    from .ai_edit import _public_hunks
    return {'review': review, 'current': body, 'proposed': proposed, 'provenance': provenance,
            'hunks': _public_hunks(body, proposed), 'tree_hash': digest, 'target': target}


def _documents(prefix: str, body: str, section) -> tuple[dict, str]:
    if section is None:
        return {'full': prefix + body, 'ablated': ''}, ''
    remaining = _without(body, section)
    return {'full': prefix + body, 'ablated': prefix + remaining}, remaining


def _egress(run: AiRun, name: str, count: int, trials: int, section) -> str:
    where = ('a model running on this machine' if run.config['local']
             else f"{run.config['label']} ({run.config['base_url']})")
    what = 'without the skill' if section is None else f'without the section "{section["heading"]}"'
    return (f"{name}'s SKILL.md and {count} eval prompts (with their input files) go to {where}, "
            f'{trials * 2} times per case: with the whole skill and {what}.')


def _evidence(result: dict) -> dict:
    kept = {key: value for key, value in result.items()
            if key not in ('plan', 'destination', 'cases', 'proposal', 'sections')}
    kept['cases'] = [{'case': row['case'], **{label: {k: row[label][k] for k in ('passed', 'graded', 'answers')}
                                              for label in ('full', 'ablated')}} for row in result['cases']]
    return kept


def ablate(store, payload: dict) -> dict:
    """Estimate or run one ablation; a section removal is staged for review."""
    payload = payload if isinstance(payload, dict) else {}
    name = payload.get('name')
    target, files, directories, digest, primary, prefix, body = _library_skill(store, name)
    listed = sections(body)
    section = _chosen(listed, payload.get('section'))
    trials = _trial_count(payload.get('trials'))
    skill_dir = Path(target['physical_path'])
    cases = ai_evals._cases(skill_dir, 10 if payload.get('max_cases') is None else payload['max_cases'])
    documents, remaining = _documents(prefix, body, section)
    prompts = {case['id']: ai_evals._case_prompt(skill_dir, case) for case in cases}
    estimate = payload.get('estimate') is True
    run = AiRun(store.data_dir, 'ablate', estimate_only=estimate)
    plan = run.review_plan(payload, [name, digest, None if section is None else
                                     [section['index'], section['start'], section['end']],
                                     [[case['id'], prompts[case['id']]] for case in cases], trials])
    removed = body[section['start']:section['end']] if section else prefix + body
    result = {**plan, 'kind': 'ablate', 'name': name, 'tree_hash': digest, 'sections': listed,
              'section': None if section is None else {k: section[k] for k in ('index', 'heading', 'line')},
              'target': 'section' if section else 'skill', 'trials': trials, 'cases_count': len(cases),
              'calls_planned': len(cases) * 2 * trials, 'margin': MARGIN,
              'saves_tokens': count_tokens(removed)[0],
              'egress': [_egress(run, name, len(cases), trials, section)]}
    rows = _calls(run, cases, prompts, documents, trials)
    if not estimate:
        if not rows:
            raise AiError('the model returned no eval outputs', 'ai-bad-output', 502)
        stats = trial_stats.summarize(rows, 'full', 'ablated')
        decision, reason = decide(stats)
        complete = len(rows) == len(cases) * 2 * trials and stats['excluded'] == 0
        result.update({'statistics': stats, 'decision': decision, 'reason': reason,
                       'cases': _per_case(rows, cases), 'status': 'complete' if complete else 'partial'})
        if decision == 'remove' and not complete:
            decision, reason = 'uncertain', 'some answers are missing, so removal is not proposed; run it again'
            result.update({'decision': decision, 'reason': reason})
        if decision == 'remove' and not _discriminates(rows):
            result['coverage_warning'] = (
                'No case passed differently with and without it, so these cases may not test what it '
                'does. Add a case that needs it before removing it.')
    result['run'] = run.label()
    if estimate:
        result['status'] = 'estimate'
        return result
    result['run_id'] = _save_run(store.data_dir, _evidence(result))
    if result['decision'] == 'remove' and section is None:
        result['proposal'] = {'kind': 'retire', 'ladder': _ladder(name)}
    elif result['decision'] == 'remove' and remaining.strip():
        try:
            result['proposal'] = {'kind': 'remove-section', **_stage_removal(
                store, target, files, directories, digest, primary, prefix, body, remaining, run, section)}
        except AiError as exc:
            result['proposal_error'] = str(exc)
    elif result['decision'] == 'remove':
        result['proposal_error'] = 'removing this section would leave the skill empty; retire the skill instead'
    return result
