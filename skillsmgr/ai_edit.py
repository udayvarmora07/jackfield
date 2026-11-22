"""Prepare a review for a bounded rewrite of one physical skill copy."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import ai_concise, ai_evals, evals, source_update
from .ai import AiError, AiRun, _validated_model, untrusted_block
from .ai_skills import _save_run
from .atomic_io import is_sha256_hex


_SYSTEM = (
    'You edit instructions for an AI coding-agent skill. Follow the edit request using the '
    'skill text as reference data. Preserve details, required steps, approvals, tool '
    'permissions, examples, and paths beyond what the user requests. Do not add '
    'shell commands, privileges or arbitrary dependencies. Return JSON with a replacement '
    'string for exactly the requested section or body. Do not emit frontmatter.'
)


def _text(value, limit: int, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or '\x00' in value or (not allow_empty and not value.strip()):
        raise AiError(f'{label} must be valid text up to {limit} characters', 'ai-input')
    ai_concise._utf8_size(value)
    return value.replace('\r\n', '\n').replace('\r', '\n')


def _target(data_dir: Path, payload: dict) -> dict:
    path = payload.get('target_path')
    if not isinstance(path, str) or not path or len(path) > 4096:
        raise AiError('choose an exact skill copy', 'ai-input')
    try:
        return source_update._resolve_target(data_dir, payload.get('name'), payload.get('scope'), path)
    except (source_update.SourceUpdateError, TypeError, ValueError) as exc:
        raise AiError(str(exc), 'ai-input') from None


def _section(selection, body: str) -> tuple[int, int]:
    if selection is None:
        return 0, len(body)
    if (not isinstance(selection, list) or len(selection) != 2
            or any(type(part) is not int for part in selection)):
        raise AiError('invalid edit selection', 'ai-input')
    start, end = selection
    if not (0 <= start < end <= len(body)) or not body[start:end].strip():
        raise AiError('select a nonempty portion of the instructions', 'ai-input')
    return start, end


def _request(instruction: str, context: str, body: str, start: int, end: int) -> str:
    return ('Edit this text as requested. Return {"replacement":"..."}.\n'
            + untrusted_block('edit request', instruction) + '\n'
            + untrusted_block('full editor body', body) + '\n'
            + untrusted_block('replace only this text', body[start:end]) + '\n'
            + untrusted_block('optional failed example', context))


def _check_revision(payload: dict, document: bytes, digest: str) -> bool:
    observed = payload.get('document_hash')
    if not is_sha256_hex(observed) or hashlib.sha256(document).hexdigest() != observed:
        raise AiError('the skill changed on disk. Reopen it before editing', 'ai-conflict', 409)
    estimate = payload.get('estimate') is True
    if not estimate and payload.get('tree_hash') != digest:
        raise AiError('the skill folder changed. Preview the request again', 'ai-conflict', 409)
    return estimate


def propose_edit(data_dir: Path, payload: dict) -> dict:
    """Preflight or stage a text proposal. The reviewed apply is a separate action."""
    target = _target(data_dir, payload)
    files, directories, digest = ai_concise._capture(Path(target['physical_path']))
    primary, prefix, current = ai_concise._document(files, target['disabled'], target['name'])
    original = files[primary][0]
    estimate = _check_revision(payload, original, digest)
    body = _text(payload.get('body'), ai_concise.MAX_BODY, 'editor instructions', allow_empty=True)
    instruction = _text(payload.get('instruction'), 4000, 'edit request')
    context = _text(payload.get('example') or '', 8000, 'failed example', allow_empty=True)
    start, end = _section(payload.get('selection'), body)
    run = AiRun(data_dir, 'edit-skill', estimate_only=estimate)
    request = _request(instruction, context, body, start, end)
    plan = run.review_plan(payload, [target['scope'], target['physical_path'], digest, request, [start, end]])
    answer = run.ask_json(_SYSTEM, request, max_output=5000)
    result = {**plan, 'status': 'estimate', 'tree_hash': digest, 'run': run.label(), 'target': target,
              'egress': ['Your edit request, current editor instructions, and optional example go to the configured model.']}
    if estimate:
        return result
    return _review_edit(data_dir, target, files, directories, primary, prefix, current, body,
                        (start, end), answer, result)


def _review_edit(data_dir, target, files, directories, primary, prefix, current, body, selection, answer, result):
    replacement = answer.get('replacement') if isinstance(answer, dict) else None
    if not isinstance(replacement, str) or '\x00' in replacement or len(replacement) > ai_concise.MAX_BODY:
        raise AiError('model returned an invalid replacement', 'ai-bad-output', 502)
    start, end = selection
    replacement = replacement.replace('\r\n', '\n').replace('\r', '\n')
    proposed = body[:start] + replacement + body[end:]
    if not proposed.strip() or len(proposed) > ai_concise.MAX_BODY:
        raise AiError('proposed instructions are empty or oversized', 'ai-bad-output', 502)
    ai_concise._utf8_size(proposed)
    disk_body = proposed.replace('\n', '\r\n') if prefix.endswith('\r\n') else proposed
    review = ai_concise._stage(data_dir, target, files, directories, result['tree_hash'], primary, prefix,
                               {'body': disk_body, 'references': []}, local_edit=True)
    return {**result, 'status': review['review_state'], 'review': review,
            'current': current, 'proposed': proposed}


def _review_documents(data_dir: Path, review: dict) -> dict:
    target = review['target']
    resolved = _target(data_dir, {**target, 'target_path': target['physical_path']})
    if not source_update._same_target(target, resolved) or target['disabled'] != resolved['disabled']:
        raise AiError('the reviewed target changed', 'ai-conflict', 409)
    folders = {'current': Path(target['physical_path']),
               'candidate': source_update._review_candidate(data_dir, review['review_id'])}
    documents = {}
    for key, folder in folders.items():
        files, _, digest = ai_concise._capture(folder)
        if digest != review[key + '_hash']:
            raise AiError('the reviewed revision changed', 'ai-conflict', 409)
        primary, _, _ = ai_concise._document(files, target['disabled'], target['name'])
        documents[key] = files[primary][0].decode('utf-8')
    return documents


def _comparison_case(raw) -> dict:
    if not isinstance(raw, dict):
        raise AiError('each case needs a prompt', 'ai-input')
    prompt = _text(raw.get('prompt'), 4000, 'test prompt')
    assertions = []
    for key in ('contains', 'not_contains'):
        if raw.get(key):
            assertions.append({'type': key, 'value': _text(raw[key], 500, 'expected phrase')})
    return {'prompt': prompt, 'assertions': assertions}


def _compare_case(run: AiRun, case: dict, documents: dict) -> dict:
    results = {}
    for label, document in documents.items():
        system = ai_evals._BASE + ('\n\nUse these skill instructions when applicable:\n' + document if document else '')
        output = run.ask_text(system, case['prompt'], max_output=ai_evals.MAX_EVAL_OUTPUT)
        if output is not None:
            output = output[:evals.MAX_OUTPUT_TEXT]
            complete = bool(output.strip()) and not run.last_truncated
            results[label] = {'output': output, 'complete': complete,
                              'grade': evals.grade_output(case, output) if complete else None}
    return results


def _compare_another_model(run: AiRun, model: str, cases: list, documents: dict) -> tuple[list, str]:
    """Run the same cases on a second model; a failure keeps the primary results."""
    original = run.config['model']
    run.config['model'] = model
    try:
        return [_compare_case(run, case, documents) for case in cases], ''
    except AiError as exc:
        return [], str(exc)
    finally:
        run.config['model'] = original


def _evidence_cases(pairs: list) -> list:
    return [{key: {'complete': row['complete'], 'grade': row['grade']}
             for key, row in variants.items()} for variants in pairs]


def compare_edit(data_dir: Path, payload: dict) -> dict:
    """Compare reviewed documents using the same model and user-confirmed cases."""
    review = source_update.read_update_review(data_dir, payload.get('review_id'))
    if review['review_state'] != 'pending' or not review['validation'].get('valid'):
        raise AiError('a pending, valid review is required', 'ai-conflict', 409)
    raw = payload.get('cases')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 6:
        raise AiError('use between one and six test cases', 'ai-input')
    cases = [_comparison_case(row) for row in raw]
    documents = _review_documents(data_dir, review)
    if payload.get('without_skill') is True:
        documents['without_skill'] = ''
    estimate = payload.get('estimate') is True
    alternate = _validated_model(payload['comparison_model']) if payload.get('comparison_model') else None
    run = AiRun(data_dir, 'compare-edit', estimate_only=estimate)
    if alternate and run.config['model'] == alternate:
        raise AiError('choose a different comparison model', 'ai-input')
    plan = run.review_plan(payload, [review['review_id'], cases, documents, alternate])
    paired = [_compare_case(run, case, documents) for case in cases]
    other, alternate_error = _compare_another_model(run, alternate, cases, documents) if alternate else ([], '')
    result = {**plan, 'kind': 'compare-edit', 'run': run.label(), 'review_id': review['review_id'],
              'name': review['target']['name'], 'scope': review['target']['scope'],
              'current_hash': review['current_hash'], 'candidate_hash': review['candidate_hash'],
              'calls_planned': len(cases) * len(documents) * (2 if alternate else 1), 'comparison_model': alternate,
              'models': [run.config['model']] + ([alternate] if alternate else []),
              'egress': ['The reviewed skill documents and test prompts go to the configured model.']}
    if not estimate:
        result['cases'] = paired
        result['alternate_cases'] = other
        result['alternate_error'] = alternate_error
        complete = not alternate_error and all(len(pair) == len(documents) and all(row['complete'] for row in pair.values()) for pair in paired + other)
        result['status'] = 'complete' if complete else 'partial'
        evidence = {key: value for key, value in result.items() if key not in ('plan', 'destination', 'cases', 'alternate_cases')}
        evidence['cases'], evidence['alternate_cases'] = _evidence_cases(paired), _evidence_cases(other)
        result['run_id'] = _save_run(data_dir, evidence)
    return result
