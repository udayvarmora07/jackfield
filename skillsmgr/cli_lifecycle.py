"""CLI entry points for opt-in usage and exact project previews."""

import stat
from pathlib import Path

from .cli_output import print_json, sanitize_text
from .clock import iso
from .documents import ACTIVE_DOCUMENT, DISABLED_DOCUMENT
from .errors import StoreError


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


def _candidate_mtime(record):
    if record.get("malformed") or record.get("read_only"):
        return None
    name = DISABLED_DOCUMENT if record["disabled"] else ACTIVE_DOCUMENT
    # The loader's provenance keeps the named entry, even when the global
    # scope row's path has already resolved an in-library directory alias.
    document = Path(record["provenance"]["path"]) / name
    try:
        # Use the chosen on-disk document. Skip links, including links in an
        # ancestor, and files that can no longer be inspected after scanning.
        if document.resolve(strict=True) != document:
            return None
        info = document.lstat()
        if stat.S_ISREG(info.st_mode):
            return iso(info.st_mtime)
    except (OSError, RuntimeError, ValueError, OverflowError):
        return None
    return None


def _candidate_rows(records, physical_root, named_root):
    from .validator import validate_skill_name

    for record in records:
        try:
            validate_skill_name(record["name"])
        except ValueError:
            continue
        # The peer-link record's provenance names the target. Keep the named
        # entry in this scope, as we do for in-scope links and ordinary skills.
        entry = record.get("path") if record.get("read_only") else record["provenance"]["path"]
        path = Path(entry) if entry else None
        relative = None
        if path is not None:
            for root in (physical_root, named_root):
                if path.is_relative_to(root):
                    relative = path.relative_to(root).as_posix()
                    break
        yield {"scope": record["scope"], "name": record["name"], "relative_path": relative,
               "last_edit": _candidate_mtime(record)}


def _note_standalone_document(descriptor, diagnostics):
    if descriptor.consumer not in ("gemini", "shared-agent-skills"):
        return
    try:
        (descriptor.base / ACTIVE_DOCUMENT).lstat()
    except FileNotFoundError:
        return
    except OSError:
        reason = "standalone Gemini SKILL.md could not be inspected"
    else:
        reason = "standalone Gemini SKILL.md is outside the managed skill inventory"
    diagnostics.append({"section": "scope-scan", "reason": reason})


def _scan_root_key(descriptor, physical_root):
    # The global scan has no peer-link allowances. Command Code stops its
    # recursive scan at a skill folder, whereas other recursive scans descend.
    return (physical_root, descriptor.id == "global", descriptor.recursive,
            descriptor.consumer == "commandcode")


def _root_fingerprint(info):
    return info.st_dev, info.st_ino, info.st_mtime_ns


def _root_still_matches(base, physical_root, fingerprint):
    try:
        return base.resolve(strict=True) == physical_root and _root_fingerprint(base.stat()) == fingerprint
    except (OSError, RuntimeError):
        return False


def _candidate_inventory(descriptors, inventory, observed_roots, scan_scope):
    completed_scans = {}
    for descriptor in descriptors:
        evidence = inventory[descriptor.id]
        diagnostics = evidence["diagnostics"]
        try:
            before = descriptor.base.stat()
            if not stat.S_ISDIR(before.st_mode):
                diagnostics.append({"section": "scope-scan", "reason": "scope root is not a directory"})
                evidence["status"] = "partial"
                continue
            physical_root = descriptor.base.resolve(strict=True)
        except FileNotFoundError:
            evidence["status"] = "missing"
            continue
        except (OSError, RuntimeError):
            diagnostics.append({"section": "scope-scan", "reason": "scope root could not be inspected"})
            evidence["status"] = "partial"
            continue
        _note_standalone_document(descriptor, diagnostics)
        key = _scan_root_key(descriptor, physical_root)
        fingerprint = _root_fingerprint(before)
        previous = completed_scans.get(key)
        if previous is not None and previous[1] == fingerprint and _root_still_matches(descriptor.base, physical_root, fingerprint):
            observed_roots[descriptor.id] = physical_root
            evidence.update(status="partial" if diagnostics else "shared-root", canonical_scope=previous[0])
            continue
        try:
            records = scan_scope(descriptor, collector=diagnostics)
        except (OSError, RuntimeError, StoreError):
            diagnostics.append({"section": "scope-scan", "reason": "scope scan failed"})
            evidence["status"] = "partial"
            continue
        if _root_still_matches(descriptor.base, physical_root, fingerprint):
            observed_roots[descriptor.id] = physical_root
        else:
            diagnostics.append({"section": "scope-scan", "reason": "scope root changed during scan"})
        if any(record.get("addressable") is False and not record.get("document_missing") for record in records):
            diagnostics.append({"section": "scope-scan", "reason": "one or more skill names are outside the managed inventory"})
        evidence["status"] = "partial" if diagnostics else "scanned"
        if evidence["status"] == "scanned":
            completed_scans[key] = (descriptor.id, fingerprint)
        yield from _candidate_rows(records, physical_root, descriptor.base)


def _scan_candidate_scope(descriptor, *, collector):
    from . import scopes

    if descriptor.id == "global":
        return scopes.scan_scope("global", collector=collector)
    return scopes._scan_agent_scope(descriptor, collector=collector)


def _candidates(args, store):
    from . import lifecycle, scopes, usage

    usage_report = usage.report(store.data_dir, days=args.days)
    descriptors = [scope for scope in scopes.known_scopes(include_project_aliases=True)
                   if args.scope in ("all", scope.id)]
    if not descriptors:
        raise StoreError(f"unknown scope {args.scope!r}")
    inventory = {scope.id: {"status": "not-scanned", "diagnostics": []} for scope in descriptors}
    observed_roots = {}
    workspace = scopes._cwd()
    project_paths = {scope.id: scope.base.relative_to(workspace).as_posix() for scope in descriptors
                     if scope.kind == "project" and scope.base.is_relative_to(workspace)}
    result = lifecycle.candidate_report(
        _candidate_inventory(descriptors, inventory, observed_roots, _scan_candidate_scope), usage_report,
        data_dir=store.data_dir, days=args.days,
    )
    readiness = lifecycle.archive_readiness(inventory, usage_report["coverage"],
                                            project_paths=project_paths, observed_roots=observed_roots)
    if args.json:
        result["archive_readiness"] = readiness
        result["inventory"] = inventory
        print_json(result)
        return
    for row in result["skills"]:
        parts = [sanitize_text(row["scope"]), sanitize_text(row["name"]), row["state"]]
        if row["relative_path"] and row["relative_path"] != row["name"]:
            parts.append("folder " + sanitize_text(row["relative_path"]))
        if row["pinned"]:
            parts.append("(pinned)")
        if row["last_edit"]:
            parts.append(f'document modified {row["last_edit"]}')
        if row["used_by"]:
            parts.append("same-name usage from " + sanitize_text(", ".join(row["used_by"])))
        print(*parts)
    if result["truncated"]:
        print(f'Showing the first {result["limit"]} skills.')
    for scope, evidence in inventory.items():
        if evidence["status"] != "scanned":
            description = evidence["status"]
            if "canonical_scope" in evidence:
                description += " with " + evidence["canonical_scope"]
            print(sanitize_text(scope), "inventory", sanitize_text(description))
        for diagnostic in evidence["diagnostics"]:
            print(" ", sanitize_text(diagnostic["reason"]))
    for scope, consumers in readiness["documented_scope_consumers"].items():
        if consumers:
            scans = ", ".join(f'{row["consumer"]} ({row["transcript_scan"]})' for row in consumers)
            print(f"{sanitize_text(scope)} documented readers {sanitize_text(scans)}")
    print("Archive eligibility requires a complete consumer map and continuous usage, edit and install evidence.")


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
