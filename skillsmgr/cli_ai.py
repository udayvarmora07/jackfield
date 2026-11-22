"""AI CLI: trigger evidence (A14), ablate and retire, and contradiction checks."""
from __future__ import annotations

from pathlib import Path

from . import ai_ablate, ai_conflicts, ai_skills
from .ai import AiError
from .cli_output import err, print_json, sanitize_text


def validate_args(parser, args):
    if getattr(args, "fail_on_regression", False) and not getattr(args, "run", False):
        parser.error("--fail-on-regression requires --run")
    if getattr(args, "ai_command", None) == "conflicts" and args.run and not args.judge:
        parser.error("--run requires --judge")


def _baseline(data_dir, scope, run_id):
    if run_id:
        return run_id, ai_skills.read_run(data_dir, run_id)
    files = sorted(ai_skills._runs_dir(data_dir).glob("trigger-test-*.json"),
                   key=lambda path: (ai_skills._run_mtime(path), path.name), reverse=True)
    for path in files[:ai_skills.KEEP_RUNS]:
        previous = ai_skills.read_run(data_dir, path.stem)
        if previous.get("scope") == scope and previous.get("prompt_source") == "saved":
            return path.stem, previous
    return None, None


def _signature(result):
    provenance, run = result["provenance"], result["run"]
    return (result["scope"], result["seed"], result["repeats"], provenance["version"],
            provenance["router"], provenance["prompt_sha256"], provenance["endpoint_sha256"],
            run["provider"], run["model"])


def _listing_names(result):
    listing = result["listing_snapshot"]
    if not isinstance(listing, list) or not listing or len(listing) > ai_skills.MAX_LISTED:
        raise ValueError("invalid listing snapshot")
    names = set()
    for entry in listing:
        name, description = entry["name"], entry["description"]
        if not isinstance(name, str) or not isinstance(description, str) or name in names:
            raise ValueError("invalid listing entry")
        names.add(name)
    if ai_skills._fingerprint(listing) != result["provenance"]["listing_sha256"]:
        raise ValueError("listing fingerprint does not match evidence")
    return names


def _prompt_counts(row, names, repeats):
    expected, choices = row["expected"], row["choices"]
    if expected is not None and expected not in names:
        raise ValueError("expected skill absent from listing")
    if not isinstance(row["text"], str) or not row["text"]:
        raise ValueError("invalid prompt text")
    if not isinstance(choices, dict) or not choices:
        raise ValueError("missing choices")
    if type(row["answered"]) is not int or row["answered"] != repeats:
        raise ValueError("incomplete prompt")
    for choice, count in choices.items():
        if choice not in names | {ai_skills.NONE} or type(count) is not int or count < 1:
            raise ValueError("invalid choice count")
    if sum(choices.values()) != repeats:
        raise ValueError("inconsistent answer counts")
    return expected, choices.get(expected or ai_skills.NONE, 0)


def _metrics(result):
    """Recompute counts from complete observations instead of trusting rates."""
    if result["kind"] != "trigger-test" or result.get("status") not in (None, "complete"):
        raise ValueError("not a completed trigger test")
    if result["run"]["estimate_only"] is not False or result.get("prompt_source") != "saved":
        raise ValueError("not a saved-prompt measurement")
    for field in ("invalid_answers", "missing_answers"):
        if type(result[field]) is not int or result[field] != 0:
            raise ValueError("incomplete routing evidence")
    repeats = ai_skills._repeats(result["repeats"])
    ai_skills._trigger_seed(result["seed"])
    names = _listing_names(result)
    rows = result["prompts"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= ai_skills.MAX_PROMPTS:
        raise ValueError("missing prompt observations")
    metrics = {}
    for row in rows:
        expected, hits = _prompt_counts(row, names, repeats)
        metric = metrics.setdefault(expected, {"hits": 0, "answers": 0})
        metric["hits"] += hits
        metric["answers"] += repeats
    fingerprint = ai_skills._fingerprint([[p["text"], p["expected"]] for p in rows])
    if fingerprint != result["provenance"]["prompt_sha256"]:
        raise ValueError("prompt fingerprint does not match evidence")
    return metrics


def _validate_baseline(previous, current):
    try:
        if _signature(previous) != _signature(current):
            raise ValueError("prompts, scope, model, endpoint, seed or repeats differ")
        if previous["provenance"]["version"] != 1 or previous["provenance"]["router"] != "trigger-test-v1":
            raise ValueError("unsupported routing evidence version")
        return _metrics(previous)
    except (KeyError, TypeError, ValueError, AiError) as exc:
        raise AiError(f"baseline is not comparable: {exc}", "ai-baseline-incomparable") from None


def _compare(previous, result, run_id):
    if previous is None:
        return {"status": "missing", "baseline_run_id": None}
    try:
        before = _validate_baseline(previous, result)
    except AiError as exc:
        return {"status": "incomparable", "baseline_run_id": run_id, "reason": str(exc)}
    if result["run"]["estimate_only"]:
        return {"status": "not-run", "baseline_run_id": run_id}
    after = _metrics(result)
    metrics = [{"expected": name, "before": before[name], "after": counts,
                "regressed": counts["hits"] < before[name]["hits"]}
               for name, counts in sorted(after.items(), key=lambda item: item[0] or "~")]
    return {"status": "compared", "baseline_run_id": run_id, "metrics": metrics,
            "regressed": any(m["regressed"] for m in metrics),
            "listing_changed": previous["provenance"]["listing_sha256"] != result["provenance"]["listing_sha256"],
            "advisory": "An observed sample decrease; provider output varies. This is not a statistical significance test."}


def _execute(args, data_dir):
    payload = {"scope": args.scope, "saved": True, "strict_saved": True,
               "compare_previous": False, "repeats": args.repeats, "seed": args.seed,
               "estimate": not args.run}
    baseline_id, previous = _baseline(data_dir, args.scope, args.baseline)
    def preflight(result):
        if args.fail_on_regression:
            if previous is None:
                raise AiError("no saved baseline; run once without --fail-on-regression first", "ai-baseline-missing")
            _validate_baseline(previous, result)
    result = ai_skills.trigger_test(data_dir, payload, preflight=preflight)
    if args.run:
        try:
            _metrics(result)
        except (KeyError, TypeError, ValueError, AiError):
            return {"status": "incomplete", "result": result,
                    "comparison": {"status": "incomparable", "baseline_run_id": baseline_id}}, 1
    comparison = _compare(previous, result, baseline_id)
    failed = args.fail_on_regression and (comparison["status"] != "compared" or comparison.get("regressed"))
    status = "regression" if comparison.get("regressed") else "completed" if args.run else "estimate"
    if failed and comparison["status"] != "compared":
        status = "incomparable"
    return {"status": status, "result": result, "comparison": comparison}, int(bool(failed))


def _human_report(report):
    print("AI trigger test: " + sanitize_text(report["status"]))
    if "error" in report:
        err(sanitize_text(report["error"]["message"]))
        return
    result = report["result"]
    for line in result["egress"]:
        print(sanitize_text(line))
    print(sanitize_text(result["run"]["advisory"]))
    print(f"Model: {sanitize_text(result['run']['model'])}; seed: {result['seed']}; repeats: {result['repeats']}")
    print("Comparison: " + sanitize_text(report["comparison"]["status"]))
    if result.get("run_id"):
        print("Saved run: " + sanitize_text(result["run_id"]))


def _execute_ablate(args, store):
    payload = {"name": args.name, "section": args.section, "trials": args.trials, "max_cases": args.max_cases,
               "placebo": args.placebo}
    estimate = ai_ablate.ablate(store, {**payload, "estimate": True})
    if not args.run:
        return {"status": "estimate", "result": estimate}, 0
    result = ai_ablate.ablate(store, {**payload, "plan": estimate["plan"]})
    return {"status": result["status"], "result": result}, 0


def _human_ablate(report):
    print("AI ablate: " + sanitize_text(report["status"]))
    if "error" in report:
        err(sanitize_text(report["error"]["message"]))
        return
    result = report["result"]
    for row in result["sections"]:
        print(f"  [{row['index']}] {'#' * row['level']} {sanitize_text(row['heading'])} (~{row['tokens']} tokens)")
    target = "whole skill" if result["section"] is None else "section " + sanitize_text(result["section"]["heading"])
    print(f"Testing: {target}; {result['calls_planned']} model calls; would save ~{result['saves_tokens']} tokens")
    for line in result["egress"]:
        print(sanitize_text(line))
    if "decision" in result:
        stats = result["statistics"]
        print(f"Decision: {result['decision']} -- {sanitize_text(result['reason'])}")
        print(f"Lift with it: {stats['lift']} (interval {stats['interval']}, {stats['paired_cases']} requests, "
              f"{stats['trials']} trials)")
        placebo = result.get("placebo_statistics")
        if placebo:
            print(f"Against same-length filler: lift {placebo['lift']} (interval {placebo['interval']}), "
                  f"{placebo['verdict']}")
        if stats.get("min_detectable") is not None:
            print(f"Smallest difference this run could reliably show: ~{round(stats['min_detectable'] * 100)} points")
        if result.get("coverage_warning"):
            err(sanitize_text(result["coverage_warning"]))
    proposal = result.get("proposal") or {}
    if proposal.get("kind") == "remove-section":
        review_id = sanitize_text(proposal["review"]["review_id"])
        print(f"Staged removal for review: {review_id}")
        print(f"  review the diff in the web UI, or apply: skills-mgr update apply "
              f"{sanitize_text(result['name'])} {review_id} --yes")
    for step in proposal.get("ladder", []):
        print(f"  {step['step']}: {sanitize_text(step['action'])}")
    if result.get("proposal_error"):
        err(sanitize_text(result["proposal_error"]))
    if result.get("run_id"):
        print("Saved run: " + sanitize_text(result["run_id"]))


def _execute_conflicts(args, store):
    payload = {"scope": args.scope, "project": str(Path(args.project).expanduser()) if args.project else None}
    if not args.judge:
        return {"status": "candidates", "result": ai_conflicts.check(store.data_dir, payload)}, 0
    payload.update({"judge": True, "max_pairs": args.max_pairs})
    estimate = ai_conflicts.check(store.data_dir, {**payload, "estimate": True})
    if not args.run or "plan" not in estimate:
        return {"status": estimate.get("status", "estimate"), "result": estimate}, 0
    result = ai_conflicts.check(store.data_dir, {**payload, "plan": estimate["plan"]})
    return {"status": result["status"], "result": result}, 0


def _human_side(side):
    return f"{sanitize_text(side['source'])}:{side['line']}: {sanitize_text(side['quote'])}"


def _human_conflicts(report):
    print("AI conflicts: " + sanitize_text(report["status"]))
    if "error" in report:
        err(sanitize_text(report["error"]["message"]))
        return
    result = report["result"]
    print(f"Read {len(result['sources'])} sources; {len(result['candidates'])} candidate pairs (heuristic)")
    for line in result.get("inputs_limited", []):
        err(sanitize_text(line))
    for line in result.get("egress", []):
        print(sanitize_text(line))
    shown = result["conflicts"] if "conflicts" in result else result["candidates"][:20]
    for pair in shown:
        judge = pair.get("judge")
        label = f"AI: {judge['verdict']} -- {sanitize_text(judge['why'])}" if judge else sanitize_text(pair["detail"])
        print(f"- {pair['kind']}: {label}")
        print("    " + _human_side(pair["a"]))
        print("    " + _human_side(pair["b"]))
    for row in result.get("density", []):
        flag = " (dense)" if row["dense"] else ""
        print(f"  {sanitize_text(row['source'])}: {row['directives']}{'+' if row['capped'] else ''} directive lines{flag}")
    for row in result.get("stale_references", []):
        print(f"- stale: {sanitize_text(row['reference'])}: {sanitize_text(row['reason'])} "
              f"({sanitize_text(row['source'])}:{row['line']})")
    print(sanitize_text(result["limits"]))


_COMMANDS = {"trigger-test": (lambda args, store: _execute(args, store.data_dir), _human_report),
             "ablate": (_execute_ablate, _human_ablate),
             "conflicts": (_execute_conflicts, _human_conflicts)}


def cmd_ai(args, store) -> int:
    command = getattr(args, "ai_command", None) or "trigger-test"
    execute, human = _COMMANDS[command]
    try:
        report, code = execute(args, store)
    except AiError as exc:
        report, code = {"status": "error", "error": {"code": exc.code, "message": str(exc)}}, 1
    except (OSError, ValueError, TypeError, RecursionError):
        report, code = {"status": "error", "error": {"code": "ai-input", "message": "cannot read AI input or run evidence; check saved files"}}, 1
    report = {"schema_version": 1, "command": "ai " + command, **report}
    if args.json:
        print_json(report)
    else:
        human(report)
    return code
