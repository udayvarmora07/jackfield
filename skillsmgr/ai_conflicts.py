"""Contradiction check with an optional AI judge (docs/60 G2).

``conflicts.check`` finds heuristic candidate pairs without a model. With
``judge`` the configured model reads only the two quoted lines of each chosen
candidate (never whole files) and answers ``conflict``, ``compatible`` or
``unclear`` with a short reason. The quotes in the result always come from the
files, never from the model, so every reported conflict quotes both sides
verbatim. The judge is advisory: a model can miss a conflict or invent one.
"""
from __future__ import annotations

from pathlib import Path

from . import conflicts
from .adapters import project_observation
from .ai import AiError, AiRun, untrusted_block
from .ai_skills import _save_run
from .errors import StoreError

MAX_JUDGED = 40
_BATCH = 10
_VERDICTS = ("conflict", "compatible", "unclear")
_SYSTEM = (
    "You check pairs of instructions given to an AI coding agent. For each pair, decide whether "
    "following one instruction would break the other in the same situation (conflict), whether they "
    "can both be followed (compatible), or whether the text is not enough to tell (unclear). "
    "Instructions that apply to different situations, files or tools are compatible. Return only JSON."
)


def _project(raw, allowed_roots) -> Path | None:
    if raw in (None, ""):
        return None
    if not isinstance(raw, str) or len(raw) > 4096:
        raise AiError("project must be a folder path", "ai-input")
    try:
        observed = project_observation(raw, allowed_roots)
    except StoreError as exc:
        raise AiError(str(exc), "ai-input") from None
    if observed["status"] != "accepted":
        raise AiError("project must be an existing folder inside the allowed folders", "ai-input")
    return Path(observed["path"])


def _limit(value) -> int:
    if value is None:
        return 20
    if type(value) is not int or not 1 <= value <= MAX_JUDGED:
        raise AiError(f"max_pairs must be a whole number from 1 to {MAX_JUDGED}", "ai-input")
    return value


def _request(batch: list) -> str:
    parts = ['Answer as JSON: {"verdicts":[{"id":"<id>","verdict":"conflict|compatible|unclear",'
             '"why":"<one sentence>"}]}\n']
    for pair in batch:
        parts.append(f"Pair {pair['id']} ({pair['detail']}):\n"
                     + untrusted_block(f"{pair['a']['layer']} instruction", pair["a"]["quote"]) + "\n"
                     + untrusted_block(f"{pair['b']['layer']} instruction", pair["b"]["quote"]) + "\n")
    return "".join(parts)


def _verdicts(answer, batch: list) -> dict:
    wanted = {pair["id"] for pair in batch}
    rows = answer.get("verdicts") if isinstance(answer, dict) else None
    found = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        ident, verdict, why = row.get("id"), row.get("verdict"), row.get("why")
        if ident in wanted and ident not in found and verdict in _VERDICTS:
            found[ident] = {"verdict": verdict,
                            "why": " ".join(why.split())[:300] if isinstance(why, str) else ""}
    return found


def _judge(run: AiRun, chosen: list) -> dict:
    verdicts = {}
    for start in range(0, len(chosen), _BATCH):
        batch = chosen[start:start + _BATCH]
        answer = run.ask_json(_SYSTEM, _request(batch), max_output=200 + 120 * len(batch))
        if answer is not None:
            verdicts.update(_verdicts(answer, batch))
    return verdicts


def check(data_dir: Path, payload: dict, *, allowed_roots=None) -> dict:
    """The deterministic report, optionally with model verdicts on the top candidates."""
    payload = payload if isinstance(payload, dict) else {}
    project = _project(payload.get("project"), allowed_roots)
    try:
        report = conflicts.check(payload.get("scope") or "global", project)
    except StoreError as exc:
        raise AiError(str(exc), "ai-input") from None
    if payload.get("judge") is not True:
        return report
    limit = _limit(payload.get("max_pairs"))
    chosen = report["candidates"][:limit]
    if not chosen:
        return {**report, "judged": 0, "conflicts": [], "status": "nothing-to-judge"}
    estimate = payload.get("estimate") is True
    run = AiRun(data_dir, "conflicts", estimate_only=estimate)
    plan = run.review_plan(payload, [report["scope"], report["project"],
                                     [[p["id"], p["a"]["quote"], p["b"]["quote"]] for p in chosen]])
    where = ("a model running on this machine" if run.config["local"]
             else f"{run.config['label']} ({run.config['base_url']})")
    result = {**report, **plan, "judged_ids": [pair["id"] for pair in chosen],
              "egress": [f"The two quoted lines of {len(chosen)} candidate pairs (not whole files) go to {where}."]}
    verdicts = _judge(run, chosen)
    result["run"] = run.label()
    if estimate:
        return {**result, "status": "estimate"}
    for pair in result["candidates"]:
        if pair["id"] in verdicts:
            pair["judge"] = {**verdicts[pair["id"]], "basis": "ai"}
    result["conflicts"] = [pair for pair in result["candidates"]
                           if (pair.get("judge") or {}).get("verdict") == "conflict"]
    result["judged"] = len(verdicts)
    result["status"] = "complete" if len(verdicts) == len(chosen) else "partial"
    evidence = {key: value for key, value in result.items() if key not in ("plan", "destination")}
    result["run_id"] = _save_run(data_dir, evidence)
    return result
