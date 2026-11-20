"""CLI entry points for opt-in usage and exact project previews."""

from .cli_output import print_json, sanitize_text


def _preview_output(result, *, json_output):
    if json_output:
        print_json(result)
        return
    if result.get("note"):
        print(sanitize_text(result["note"]))
    for line in result.get("diff", "").split("\n"):
        if line:
            print(sanitize_text(line))
    if result.get("diff_suppressed"):
        print(sanitize_text(result["diff_note"]))
        for change in result["changes"]:
            print(sanitize_text(change["operation"]), sanitize_text(change["skill"]))
    for key in ("argv", "patch"):
        if key in result:
            print_json({key: result[key]})
    if result.get("status") == "no-op" or result.get("changed") is False:
        print("No change needed.")
    if result.get("status") not in ("launch-only", "manual-patch"):
        print("Plan ID", result.get("plan_id", result.get("plan_hash")))


def _usage(args, store):
    from . import usage

    if args.usage_action == "enable":
        result = usage.enable(store.data_dir, args.agent)
        if args.json:
            print_json(result)
        else:
            print("Consent saved for", ", ".join(result["agents"]))
        return
    if args.usage_action == "disable":
        result = usage.disable(store.data_dir, args.agent, purge=args.purge)
        if args.json:
            print_json(result)
        elif result["purged"]:
            print("Consent revoked and cached counts erased.")
        else:
            print("Remaining consent", ", ".join(result["agents"]) or "none")
        return
    result = usage.report(store.data_dir, args.agent, days=args.days, refresh=args.refresh)
    if args.json:
        print_json(result)
        return
    for agent, evidence in result["coverage"].items():
        print(sanitize_text(agent), sanitize_text(evidence["status"]))
    for row in result["counts"]:
        print(sanitize_text(row["agent"]), sanitize_text(row["name"]),
              f'{row["explicit"]} explicit, {row["inferred"]} inferred')
    if not result["counts"]:
        print("No usage events in this report.")


def _lock_verify(args, _store):
    from .project_lock_commands import verify_project_lock

    result = verify_project_lock(args.project)
    if args.json:
        print_json(result)
    else:
        print("Lock verified." if result["verified"] else "Lock verification failed.")
        if result.get("reason"):
            print(sanitize_text(result["reason"]))
        for row in result["entries"]:
            print(sanitize_text(row["name"]), sanitize_text(row["hash_status"]))
    return 0 if result["verified"] else 1


def _lock_write(args, store):
    from .project_lock_commands import apply_project_lock_write, preview_project_lock_write

    sources = {}
    for value in args.source:
        name, separator, path = value.partition("=")
        if not separator or not name or not path or name in sources:
            raise ValueError("--source requires one NAME=PATH per selected skill")
        sources[name] = path
    if not args.plan_id:
        result = preview_project_lock_write(args.project, args.names, local_sources=sources)
        _preview_output(result, json_output=args.json)
        return
    result = apply_project_lock_write(args.project, args.names, args.plan_id,
                                      data_dir=store.data_dir, local_sources=sources)
    if args.json:
        print_json(result)
    else:
        print("Lockfile saved." if result["changed"] else "No change needed.")


def _lock_undo(args, store):
    from .project_lock_commands import undo_project_lock_write

    result = undo_project_lock_write(args.project, args.plan_id, data_dir=store.data_dir)
    if args.json:
        print_json(result)
    else:
        print("Lockfile restored.")


def _native(args, store):
    from .native_profiles import apply_native, preview_native, undo_native

    if args.native_action == "undo":
        result = undo_native(args.backup_id, store.data_dir)
    else:
        project = args.project.expanduser().absolute()
        off = _native_off(args, store)
        if args.native_action == "preview":
            result = preview_native(project, args.agent, off)
            if args.profile:
                result["profile"] = args.profile
            _preview_output(result, json_output=args.json)
            return
        result = apply_native(project, args.agent, off, args.plan_id, store.data_dir)
    if args.json:
        print_json(result)
    elif result["status"] == "no-op":
        print("No change needed.")
    elif result["status"] == "applied":
        print("Project settings saved. Backup ID", result["backup_id"])
    else:
        print("Project settings restored.")


def _native_off(args, store):
    from .catalog import load_catalog

    if args.profile is None:
        return args.off
    profile = load_catalog(store.data_dir)["profiles"].get(args.profile)
    if profile is None:
        raise ValueError("saved profile was not found")
    off = profile.get("native", {}).get("off", [])
    if not off:
        raise ValueError("saved profile has no native off list")
    return off


def _candidate_rows(records):
    from .validator import validate_skill_name

    for record in records:
        try:
            validate_skill_name(record["name"])
        except ValueError:
            continue
        yield {"scope": record["scope"], "name": record["name"]}


def _candidates(args, store):
    from . import lifecycle, scopes, usage

    usage_report = usage.report(store.data_dir, days=args.days)
    selected = scopes._merged_scope_ids() if args.scope == "all" else [args.scope]
    records = (record for scope in selected for record in scopes.scan_scope(scope, collector=[]))
    result = lifecycle.candidate_report(
        _candidate_rows(records), usage_report, data_dir=store.data_dir, days=args.days,
    )
    if args.json:
        print_json(result)
        return
    for row in result["skills"]:
        print(sanitize_text(row["scope"]), sanitize_text(row["name"]), row["state"],
              "(pinned)" if row["pinned"] else "")
    if result["truncated"]:
        print(f'Showing the first {result["limit"]} skills.')
    print("Archive eligibility requires complete coverage. Current reports show partial evidence.")


def _pin(args, store):
    from . import lifecycle, scopes

    if args.scope != "global" and scopes.scope_by_id(args.scope) is None:
        raise ValueError("choose one known skill scope")
    pinned = args.archive_action == "pin"
    note = getattr(args, "note", "")
    if args.plan_id:
        result = lifecycle.apply_pin_change(store.data_dir, args.scope, args.name, pinned, args.plan_id, note=note)
        if args.json:
            print_json(result)
        else:
            print("Pin state saved." if result["changed"] else "No change needed.")
        return
    result = lifecycle.preview_pin_change(store.data_dir, args.scope, args.name, pinned, note=note)
    if not args.json and result["changed"]:
        print("Pin" if pinned else "Unpin", sanitize_text(args.name), "in", sanitize_text(args.scope))
    _preview_output(result, json_output=args.json)


def _undo_pin(args, store):
    from .lifecycle import undo_pin_change

    result = undo_pin_change(store.data_dir, args.plan_id)
    if args.json:
        print_json(result)
    else:
        print("Previous pin state restored.")
