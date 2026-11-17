"""Bounded informational authoring hints over already-supplied skill text."""

from __future__ import annotations

import hashlib
import json
import re

from .lockfiles import bounded_text


_MAX_AUTHORING_BODY_CHARS = 200_000
_MAX_GROUP_INSTANCES = 100
_EXAMPLE_RE = re.compile(
    r"(?im)^[ \t]*(?:#{1,6}[ \t]*)?(?:example|examples|usage example|worked example)\b|"
    r"\bfor example\b|\be\.g\.(?=$|[\s,;:)])|```[^\n]*\n[^`]{1,4000}```"
)
_VALIDATION_RE = re.compile(
    r"\b(?:verify|validate|test|check|confirm)\b|\bmake sure\b|\bassert\b",
    re.IGNORECASE,
)
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]\n]{0,512}\]\(\s*<?([^)>\s]{1,2048})")
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def _has_deep_reference(body: str) -> bool:
    for match in _MARKDOWN_LINK_RE.finditer(body):
        target = match.group(1).split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("/", "\\")) or _SCHEME_RE.match(target):
            continue
        parts = []
        for part in target.replace("\\", "/").split("/"):
            if part in ("", "."):
                continue
            if part == ".." and parts and parts[-1] != "..":
                parts.pop()
            else:
                parts.append(part)
        if parts and parts[0].casefold() == "references" and len(parts) > 2:
            return True
    return False


def _hint_names(body: str) -> list[str]:
    hints = []
    if not _EXAMPLE_RE.search(body):
        hints.append("missing-example")
    if not _VALIDATION_RE.search(body):
        hints.append("missing-validation-step")
    if _has_deep_reference(body):
        hints.append("deep-reference-nesting")
    return hints


def _instance(record: dict) -> dict:
    name = bounded_text(record.get("name", ""), 128)
    scope = bounded_text(record.get("scope", ""), 128)
    instance = {
        "name": name,
        "scope": scope,
        "scope_label": bounded_text(record.get("scope_label", scope), 128),
        "consumer": bounded_text(record.get("consumer", ""), 128),
        "disabled": bool(record.get("disabled")),
        "addressable": record.get("addressable") is not False,
        "malformed": bool(record.get("malformed")),
    }
    path = record.get("physical_path") or record.get("path")
    if path:
        instance["physical_path"] = bounded_text(path)
    else:
        instance["path"] = "path unavailable"
    return instance


def _finding(hint: str, records: list[dict]) -> dict:
    names = {
        "missing-example": ("may need an example", "No example-like section or code sample was detected."),
        "missing-validation-step": ("may need a validation step", "No common verification or validation instruction was detected."),
        "deep-reference-nesting": ("has deeply nested references", "A local Markdown link points more than one level below the references directory."),
    }
    title_suffix, explanation = names[hint]
    ordered = sorted(
        records,
        key=lambda record: (
            str(record.get("name", "")).casefold(),
            str(record.get("scope", "")).casefold(),
            str(record.get("physical_path") or record.get("path") or ""),
        ),
    )
    total = len(ordered)
    shown = ordered[:_MAX_GROUP_INSTANCES]
    identity = json.dumps(["authoring-smell", hint], ensure_ascii=False, separators=(",", ":"))
    finding_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    evidence = {
        "hint": hint,
        "instances_total": total,
        "instances_omitted": total - len(shown),
        "instances_truncated": total > len(shown),
        "instance_count_basis": "observed analyzed instances",
    }
    return {
        "id": finding_id,
        "category": "authoring-smell",
        "severity": "info",
        "confidence": "heuristic",
        "title": f"Skills {title_suffix}",
        "explanation": f"Among observed analyzed instances, {explanation.lower()} This static heuristic is advisory, not a validity failure.",
        "evidence": evidence,
        "instances": [_instance(record) for record in shown],
        "recommendation": "Review the listed instances and add only the examples, checks, or reference structure that fit each skill.",
        "automatic_action": False,
    }


def _authoring_hint_findings(records: list[dict]) -> list[dict]:
    """Return at most three grouped informational findings, without filesystem access."""
    grouped = {"missing-example": [], "missing-validation-step": [], "deep-reference-nesting": []}
    for record in records:
        if not isinstance(record, dict) or record.get("malformed"):
            continue
        body = record.get("body")
        if not isinstance(body, str) or not body.strip() or len(body) > _MAX_AUTHORING_BODY_CHARS:
            continue
        for hint in _hint_names(body):
            grouped[hint].append(record)
    return [_finding(hint, grouped[hint]) for hint in grouped if grouped[hint]]
