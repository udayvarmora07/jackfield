"""Deterministic contradiction candidates (docs/60 G2).

Reads instruction lines from skills in one scope and from the always-loaded
instruction files (CLAUDE.md, AGENTS.md, GEMINI.md at user level and, when a
project is given, in that project) and pairs lines from *different* sources
that may disagree:

* ``choice`` -- both lines pick an option from the same exclusive set (a
  JavaScript package manager, a Python package tool, tabs or spaces, ...) and
  pick different ones, or one line uses what the other forbids.
* ``polarity`` -- both lines are strong directives about the same words, one
  affirmative and one negated ("Always commit ..." against "Never commit ...").

Every pair involves at least one always-loaded instruction file; two skills
that disagree are left to the overlap judge (``ai_overlap``).

These are heuristic candidates, labelled as such; ``ai_conflicts`` can ask a
model to judge them. Every quote is the source line verbatim (surrounding
whitespace trimmed), so a reported conflict can always be found in the file.
Imports such as ``@AGENTS.md`` are not followed; each file is read on its own.
No agent documents which instruction wins when two disagree, so precedence is
reported as unknown rather than guessed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from . import file_reads, frontmatter, paths, scopes
from .errors import StoreError

MAX_FILE_BYTES = 256 * 1024
MAX_RULES_PER_SOURCE = 300
MAX_SOURCES = 400
MAX_CANDIDATES = 200
MAX_FACET_LINES = 2000
MAX_QUOTE = 400
_COMMON_TOKEN = 40

USER_FILES = (("claude-code", ".claude/CLAUDE.md"), ("codex", ".codex/AGENTS.md"),
              ("gemini", ".gemini/GEMINI.md"))
PROJECT_FILES = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md", "GEMINI.md")

_LAYERS = {
    "user": "user instructions, loaded in every session of that agent",
    "project": "project instructions, loaded in every session in this project",
    "skill": "skill, loaded only when the agent uses it",
}

_LINES = re.compile(r"\r\n|\n|\r")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_DIRECTIVE = re.compile(
    r"\b(always|never|must|mustn't|should|shouldn't|do not|don't|avoid|prefer|only|required|"
    r"forbidden|ensure|make sure|use|run|install|instead of|rather than)\b", re.I)
_IMPERATIVE = re.compile(r"^(?:indent|format|write|keep|put|add|set|commit|push|build|test|lint|"
                         r"install|run|use|prefer|call|name)\b", re.I)
_STRONG = re.compile(r"\b(always|never|must|mustn't|do not|don't|required|forbidden|avoid)\b", re.I)
_NEGATION = re.compile(r"\b(never|not|don't|dont|avoid|no|without|instead of|rather than|mustn't|"
                       r"shouldn't|stop|forbid\w*|disallow\w*)\b", re.I)
_CLAUSE = re.compile(r"[;.:!?()]|,\s|\s+but\s+|\s+however\s+", re.I)
_WORD = re.compile(r"[a-z][a-z0-9+#-]{2,}")
_STOP = frozenset("""the and for with that this from into when then than your you are use using used
run any all its it's not never always must should don't avoid prefer only make sure ensure each
every can will have has been was were but also more most other such some what which who how why
where there here they them their our ours via per one two may might could would instead rather
over under before after about like just very need needs file files code skill skills agent agents
do does done doing get set""".split())

FACETS = {
    "JavaScript package manager": {"npm": r"\bnpm\b", "pnpm": r"\bpnpm\b", "yarn": r"\byarn\b",
                                   "bun": r"\bbun\b"},
    "Python package tool": {"pip": r"\bpip3?\b", "poetry": r"\bpoetry\b", "uv": r"\buv\b",
                            "pipenv": r"\bpipenv\b", "conda": r"\bconda\b"},
    "indentation": {"tabs": r"\btabs\b", "spaces": r"\bspaces\b"},
    "indent width": {"2 spaces": r"\b(?:2|two)[- ]spaces?\b", "4 spaces": r"\b(?:4|four)[- ]spaces?\b"},
    "string quotes": {"single quotes": r"\bsingle[- ]quot", "double quotes": r"\bdouble[- ]quot"},
    "JavaScript test runner": {"jest": r"\bjest\b", "vitest": r"\bvitest\b", "mocha": r"\bmocha\b"},
    "Python test runner": {"pytest": r"\bpytest\b", "unittest": r"\bunittest\b"},
    "JavaScript formatter": {"prettier": r"\bprettier\b", "biome": r"\bbiome\b"},
    "git integration": {"rebase": r"\brebas(?:e|ing)\b", "merge commits": r"\bmerge commits?\b",
                        "squash": r"\bsquash(?:ing)?\b"},
}
_FACET_RE = {facet: {option: re.compile(pattern, re.I) for option, pattern in options.items()}
             for facet, options in FACETS.items()}
# Bare imperative "use tabs" or "use spaces" is an indentation preference.
# Mentions such as "Open the browser tabs view" still need indent context.
_FACET_CONTEXT = {"indentation": re.compile(
    r"\bindent|^(?:(?:always|never|only|do not|don't)\s+)?(?:use|prefer)\s+(?:tabs|spaces)\s*[.!]?\s*$",
    re.I),
                  "indent width": re.compile(r"\bindent", re.I)}


def _home_label(path: Path, home: Path | None) -> str:
    if home is not None and path.is_relative_to(home):
        relative = path.relative_to(home)
        return "~/" + relative.as_posix() if relative.parts else "~"
    return str(path)


def _quote(line: str) -> str:
    return line.strip()[:MAX_QUOTE]


def _is_rule(text: str) -> bool:
    """A directive, or any line that names an option from an exclusive set."""
    return bool(_DIRECTIVE.search(text)) or any(
        pattern.search(text) for options in _FACET_RE.values() for pattern in options.values())


def rules(text: str) -> list[dict]:
    """Directive lines outside code fences, with 1-based line numbers."""
    found, fence = [], None
    for number, line in enumerate(_LINES.split(text), 1):
        opened = _FENCE.match(line)
        if opened:
            marker, tail = opened.groups()
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not tail.strip(" \t"):
                fence = None
            continue
        stripped = line.strip()
        if (fence is not None or not stripped or stripped.startswith(("#", "|", ">", "<!--"))
                or not 8 <= len(stripped) <= MAX_QUOTE or not _is_rule(stripped)):
            continue
        found.append({"line": number, "quote": _quote(line), "text": _BULLET.sub("", stripped)})
        if len(found) >= MAX_RULES_PER_SOURCE:
            break
    return found


def stances(text: str) -> dict:
    """Per facet: options a line uses (positive) and forbids (negative)."""
    out = {}
    facets = {facet: options for facet, options in _FACET_RE.items()
              if facet not in _FACET_CONTEXT or _FACET_CONTEXT[facet].search(text)}
    for clause in _CLAUSE.split(text):
        if not clause or not clause.strip():
            continue
        for facet, options in facets.items():
            for option, pattern in options.items():
                match = pattern.search(clause)
                if not match:
                    continue
                negative = bool(_NEGATION.search(clause[:match.start()]))
                entry = out.setdefault(facet, {"positive": set(), "negative": set()})
                entry["negative" if negative else "positive"].add(option)
    for entry in out.values():
        entry["positive"] -= entry["negative"]
    return out


def _tokens(text: str) -> frozenset:
    return frozenset(word for word in _WORD.findall(text.lower()) if word not in _STOP)


def _instruction_sources(project: Path | None, home: Path | None) -> tuple[list, list]:
    sources, unreadable = [], []
    files = [(agent, "user", home / relative) for agent, relative in USER_FILES] if home else []
    if project is not None:
        files += [("project", "project", project / relative) for relative in PROJECT_FILES]
    for agent, layer, path in files:
        if not path.exists():
            continue
        try:
            if layer == "project" and not path.resolve().is_relative_to(project):
                raise ValueError("links outside the project")
            text = file_reads.read_regular_file(path, MAX_FILE_BYTES).decode("utf-8")
        except (OSError, ValueError, UnicodeError, RuntimeError):
            unreadable.append(_home_label(path, home))
            continue
        sources.append({"kind": "instructions", "layer": layer, "agent": agent,
                        "label": _home_label(path, home), "text": text})
    return sources, unreadable


def _document_body(folder: Path) -> str | None:
    """A skill's instructions with frontmatter lines blanked, so line numbers match the file."""
    try:
        raw = file_reads.read_regular_file(folder / "SKILL.md", MAX_FILE_BYTES, follow_symlinks=False)
        text = _LINES.sub("\n", raw.decode("utf-8"))
        body = frontmatter.parse_frontmatter(text)[1]
    except (OSError, ValueError, UnicodeError, frontmatter.FrontmatterError):
        return None
    if not body or not text.endswith(body):
        return body
    return "\n" * text[:len(text) - len(body)].count("\n") + body


def _skill_sources(scope: str, home: Path | None) -> list:
    try:
        records = scopes.scan_scope(scope)
    except (StoreError, OSError, ValueError) as exc:
        raise StoreError(f"cannot read scope {scope!r}: {exc}") from None
    sources, seen = [], set()
    for record in records:
        name, body = record.get("name"), None
        where = record.get("physical_path") or record.get("path") or ""
        if where:
            body = _document_body(Path(str(where)))
        if record.get("disabled") or not isinstance(name, str) or not isinstance(body, str) or name in seen:
            continue
        seen.add(name)
        sources.append({"kind": "skill", "layer": "skill", "agent": scope, "name": name,
                        "label": f"skill {name} ({scope})",
                        "path": _home_label(Path(str(where)), home) if where else "", "text": body})
    return sources


def _side(source: dict, rule: dict) -> dict:
    side = {"source": source["label"], "layer": source["layer"], "line": rule["line"], "quote": rule["quote"]}
    if source["kind"] == "skill":
        side["skill"] = source["name"]
    return side


def _choice_conflict(a: dict, b: dict) -> tuple[str, str] | None:
    for facet in sorted(set(a) & set(b)):
        sa, sb = a[facet], b[facet]
        for mine, theirs in ((sa, sb), (sb, sa)):
            clash = sorted(mine["positive"] & theirs["negative"])
            if clash:
                return facet, f"one uses {clash[0]}; the other rules it out"
        only_a, only_b = sa["positive"] - sb["positive"], sb["positive"] - sa["positive"]
        if only_a and only_b and not (sa["positive"] & sb["positive"]):
            return facet, f"one picks {sorted(only_a)[0]}; the other picks {sorted(only_b)[0]}"
    return None


def _candidate_id(kind: str, first: dict, second: dict) -> str:
    raw = "\n".join([kind, first["source"], first["quote"], second["source"], second["quote"]])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _pair(kind, facet, detail, first, second, score) -> dict:
    a, b = sorted((first, second), key=lambda side: (side["source"], side["line"]))
    return {"id": _candidate_id(kind, a, b), "kind": kind, "facet": facet, "detail": detail,
            "basis": "heuristic", "score": round(score, 3), "a": a, "b": b, "precedence": "unknown",
            "layers": [_LAYERS[a["layer"]], _LAYERS[b["layer"]]]}


def _prepared(sources: list, limits: list) -> list:
    items = []
    for index, source in enumerate(sources):
        found = rules(source["text"])
        if len(found) >= MAX_RULES_PER_SOURCE:
            limits.append(f"{source['label']}: only the first {MAX_RULES_PER_SOURCE} instruction lines were read")
        for rule in found:
            items.append({"source": index, "always": source["kind"] == "instructions",
                          "side": _side(source, rule), "stances": stances(rule["text"]),
                          "directive": bool(_DIRECTIVE.search(rule["text"]) or _IMPERATIVE.match(rule["text"])
                                            or "`" in rule["text"]),
                          "tokens": _tokens(rule["text"]), "strong": bool(_STRONG.search(rule["text"])),
                          "negated": bool(_NEGATION.search(rule["text"]))})
    return items


def _comparable(a: dict, b: dict) -> bool:
    """Different sources, at least one of them always loaded.

    Two skills that disagree are the overlap judge's job (``ai_overlap``):
    most skills apply to different tasks, so skill-against-skill word clashes
    are overwhelmingly noise.
    """
    return a["source"] != b["source"] and (a["always"] or b["always"])


def _choice_pairs(items: list, limits: list) -> list:
    """Directive lines that pick different options, one side always an instruction file.

    Only always-loaded lines start a comparison, so the work is bounded by the
    few instruction files rather than growing with the square of the library.
    """
    by_facet: dict = {}
    for position, item in enumerate(items):
        if item["directive"]:
            for facet in item["stances"]:
                by_facet.setdefault(facet, []).append(position)
    found = {}
    for facet, positions in by_facet.items():
        if len(positions) > MAX_FACET_LINES:
            limits.append(f"{facet}: only the first {MAX_FACET_LINES} lines naming an option were compared")
            positions = positions[:MAX_FACET_LINES]
        for left in (position for position in positions if items[position]["always"]):
            for right in positions:
                a, b = items[left], items[right]
                if right == left or (b["always"] and right < left) or a["source"] == b["source"]:
                    continue
                clash = _choice_conflict({facet: a["stances"][facet]}, {facet: b["stances"][facet]})
                if clash:
                    pair = _pair("choice", clash[0], clash[1], a["side"], b["side"], 1.0)
                    found.setdefault(pair["id"], pair)
    return list(found.values())


def _polarity_pairs(items: list, limits: list) -> list:
    """Strong lines with opposite polarity sharing words; one side always an instruction file.

    Only instruction-file lines are indexed, and every strong line probes that
    index, so a word common across many skills cannot hide a comparison.
    """
    index: dict = {}
    for position, item in enumerate(items):
        if item["always"] and item["strong"]:
            for token in item["tokens"]:
                index.setdefault(token, []).append(position)
    common = {token for token, positions in index.items() if len(positions) > _COMMON_TOKEN}
    if common:
        limits.append(f"{len(common)} words appear on more than {_COMMON_TOKEN} instruction lines and are not used to pair lines")
    found = {}
    for right, b in enumerate(items):
        if not b["strong"]:
            continue
        partners = {left for token in b["tokens"] - common for left in index.get(token, ())}
        for left in sorted(partners):
            a = items[left]
            if left == right or (b["always"] and right < left) or not _comparable(a, b) or a["negated"] == b["negated"]:
                continue
            shared = a["tokens"] & b["tokens"]
            score = len(shared) / len(a["tokens"] | b["tokens"])
            if len(shared) < 2 or score < 0.3:
                continue
            detail = "one says to do it, the other not to (shared words: " + ", ".join(sorted(shared)[:5]) + ")"
            pair = _pair("polarity", None, detail, a["side"], b["side"], score)
            found.setdefault(pair["id"], pair)
    return list(found.values())


def candidates(sources: list, limits: list | None = None) -> tuple[list, bool]:
    """Ranked candidate pairs and whether the list was cut at ``MAX_CANDIDATES``.

    Inputs dropped by the other bounds are described in ``limits``.
    """
    limits = [] if limits is None else limits
    items = _prepared(sources, limits)
    pairs = _choice_pairs(items, limits) + _polarity_pairs(items, limits)
    pairs.sort(key=lambda pair: (pair["kind"] != "choice", -pair["score"], pair["a"]["source"],
                                 pair["a"]["line"], pair["b"]["source"], pair["b"]["line"]))
    return pairs[:MAX_CANDIDATES], len(pairs) > MAX_CANDIDATES


# IFScale (arXiv 2507.11538): compliance falls as instructions accumulate, and
# the bias towards early instructions peaks around 150-200 of them.
DENSE_DIRECTIVES = 150
MAX_STALE = 200
_CODE_SPAN = re.compile(r"`([^`\n]{2,200})`")
_PATH_REF = re.compile(r"^@?(?:\./)?([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+/?|[A-Za-z0-9_-]+\.(?:md|py|js|ts|json|toml|ya?ml|sh|txt))$")
_SCRIPT_REF = re.compile(r"^(npm|pnpm|yarn|bun)\s+(?:run\s+)?([A-Za-z0-9:_-]+)")
_MAKE_REF = re.compile(r"^make\s+([A-Za-z0-9_.-]+)")
_PY_REF = re.compile(r"^python3?\s+([A-Za-z0-9_./-]+\.py)\b")
_PACKAGE_BUILTINS = frozenset("install i ci add remove rm uninstall exec x dlx create init update up outdated "
                              "publish link unlink audit view info why list ls config login version help".split())


# A stated reason ("because", "so that", ...). 74.0% of directives in studied
# instruction files give none (arXiv 2610.31715), which later blocks deletion.
_REASON = re.compile(r"\b(because|so that|to avoid|to prevent|otherwise|in order to|why:|reason:)", re.I)
_MARKUP = re.compile(r"^(?:\d+[.)]\s+|[*_`]+)+")


# Wording that agents follow less often than plain prescriptive rules
# (arXiv 2611.04367): "if/when ..., do ..." and "never/don't ...". The ranking
# differs between models, so these are counts, not errors.
_CONDITIONAL = re.compile(r"^(?:if|when|whenever|unless)\b", re.I)
_PROHIBITIVE = re.compile(r"^(?:never|don't|do not|must not|mustn't|should not|shouldn't|avoid|no)\b", re.I)


def _plain(text: str) -> str:
    """A rule without leading numbering or emphasis markers, for wording checks."""
    return _MARKUP.sub("", text)


def density(sources: list) -> list:
    """Directive lines per always-loaded file, with reason and wording counts."""
    rows = []
    for source in sources:
        if source["kind"] == "instructions":
            found = rules(source["text"])
            count = len(found)
            rows.append({"source": source["label"], "directives": count,
                         "with_reason": sum(1 for rule in found if _REASON.search(rule["text"])),
                         "conditional": sum(1 for rule in found if _CONDITIONAL.match(_plain(rule["text"]))),
                         "prohibitive": sum(1 for rule in found if _PROHIBITIVE.match(_plain(rule["text"]))),
                         "capped": count >= MAX_RULES_PER_SOURCE, "dense": count > DENSE_DIRECTIVES})
    return rows


def _inside(project: Path, relative: str) -> Path | None:
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(set(part) == {"."} for part in parts):
        return None
    try:
        target = (project / relative).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    return target if target.is_relative_to(project) else None


def _package_scripts(project: Path) -> dict | None:
    try:
        data = json.loads(file_reads.read_regular_file(project / "package.json", MAX_FILE_BYTES, follow_symlinks=False).decode("utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return scripts if isinstance(scripts, dict) else {}


def _make_targets(project: Path) -> set | None:
    try:
        text = file_reads.read_regular_file(project / "Makefile", MAX_FILE_BYTES, follow_symlinks=False).decode("utf-8")
    except (OSError, ValueError, UnicodeError):
        return None
    return set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", text, re.M))


_SKIP_DIRS = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox"})
MAX_WALK = 50_000


def _file_names(project: Path) -> set | None:
    """File and folder names in the project, or ``None`` when the tree is too large to judge."""
    names, seen = set(), 0
    for _root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        names.update(dirs)
        names.update(files)
        seen += len(files) + len(dirs)
        if seen > MAX_WALK:
            return None
    return names


def _stale_reason(project: Path, span: str, facts: dict) -> str | None:
    span = span.strip()
    script = _SCRIPT_REF.match(span)
    if script and script.group(2) not in _PACKAGE_BUILTINS:
        scripts = facts.setdefault("scripts", _package_scripts(project))
        if scripts is None:
            return "the project has no readable package.json"
        return None if script.group(2) in scripts else f"package.json has no {script.group(2)!r} script"
    make = _MAKE_REF.match(span)
    if make:
        targets = facts.setdefault("make", _make_targets(project))
        if targets is None:
            return "the project has no readable Makefile"
        return None if make.group(1) in targets else f"the Makefile has no {make.group(1)!r} target"
    python = _PY_REF.match(span)
    path = python.group(1) if python else (_PATH_REF.match(span).group(1) if _PATH_REF.match(span) else None)
    if path is None:
        return None
    if "/" not in path.rstrip("/"):
        names = facts.setdefault("names", _file_names(project))
        return None if names is None or path in names else "no file with this name in the project"
    target = _inside(project, path.rstrip("/"))
    if target is None or target.exists():
        return None
    return "not found in the project"


def stale_references(sources: list, project: Path | None) -> list:
    """Code spans in project instruction files naming paths, scripts or targets that do not exist.

    A stale command costs an agent extra tool calls and never raises an error
    (arXiv 2611.09802). Only spans that resolve inside the project are checked,
    so the report never reveals whether files outside it exist.
    """
    if project is None:
        return []
    found, facts = [], {}
    for source in sources:
        if source.get("layer") != "project":
            continue
        for number, line in enumerate(_LINES.split(source["text"]), 1):
            for span in _CODE_SPAN.findall(line):
                reason = _stale_reason(project, span, facts)
                if reason:
                    found.append({"source": source["label"], "line": number, "quote": _quote(line),
                                  "reference": span.strip()[:200], "reason": reason, "basis": "deterministic"})
                if len(found) >= MAX_STALE:
                    return found
    return found


def check(scope: str = "global", project: Path | None = None, *, home: Path | None = None) -> dict:
    """The deterministic report: sources read and ranked candidate pairs."""
    if not isinstance(scope, str) or not scope or scope == "all":
        raise StoreError("choose one skill scope to check")
    if home is None:
        try:
            home = paths.home_dir().resolve()
        except (OSError, RuntimeError):
            home = None
    project = Path(project).resolve() if project is not None else None
    instructions, unreadable = _instruction_sources(project, home)
    sources, limits = instructions + _skill_sources(scope, home), []
    if len(sources) > MAX_SOURCES:
        limits.append(f"only the first {MAX_SOURCES} of {len(sources)} sources were read")
        sources = sources[:MAX_SOURCES]
    pairs, truncated = candidates(sources, limits)
    return {
        "kind": "conflicts", "scope": scope, "project": _home_label(project, home) if project else None,
        "sources": [{key: source[key] for key in ("kind", "layer", "label") if key in source}
                    for source in sources],
        "unreadable": unreadable, "candidates": pairs, "candidates_truncated": truncated,
        "density": density(sources), "dense_threshold": DENSE_DIRECTIVES,
        "stale_references": stale_references(sources, project),
        "inputs_limited": limits[:20],
        "basis": "heuristic",
        "limits": ("Candidates come from word patterns, not understanding; many are compatible in "
                   "context. File imports such as @AGENTS.md are not followed. No agent documents "
                   "which instruction wins when two disagree, so precedence is unknown."),
        "writes_nothing": True,
    }
