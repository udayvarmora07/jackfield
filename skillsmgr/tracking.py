"""What the web app tracks: agents, project folders and tool groups (B1).

``<data>/tracking.json`` says what the web UI *shows*; it never changes a skill
on disk.  The filesystem stays the truth: a tracked agent whose folder is gone
simply has nothing to show, and an untracked one is left alone completely.

Only the web app uses this module.  It binds a :class:`Overlay` per server (see
``skillsmgr.context.SCOPE_OVERLAY``); ``scopes.known_scopes`` then returns the
tracked view.  The CLI binds nothing, so ``--scope`` and every command keep
seeing every scope.

Document (hand-readable, paths stored home-relative)::

    {"version": 1, "revision": 7,
     "agents": {"chosen": true, "tracked": [...], "seen": [...],
                "count_projects": {"cursor": false}},
     "custom_agents": [{"id": "custom-kilo", "name": "Kilo",
                        "folder": "~/.kilo/skills", "project_folder": ".kilo/skills"}],
     "projects": {"folders": ["~/work/api"], "showing": "~/work/api"},
     "tool_groups": {"add-skills": true, "check-setup": true, "ai-assist": true}}

Missing file: track everything found.  Broken file: track everything found,
say so, and copy the file aside before the first new save.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import stat
from pathlib import Path

from . import effective, paths, scopes
from .atomic_io import atomic_write_text, mutation_lock
from .clock import stamp
from .context import active_store
from .documents import DOCUMENT_NAMES
from .errors import StoreError
from .root_discovery import project_scope_specs

FILE_NAME = "tracking.json"
VERSION = 1
TOOL_GROUPS = ("add-skills", "check-setup", "ai-assist")
TOOL_GROUP_LABELS = {"add-skills": "Add skills", "check-setup": "Check setup", "ai-assist": "AI assist"}
SHARED_ID = "agents"
SHARED_LABEL = "Shared folder"
MAX_FILE_BYTES = 256 * 1024
MAX_CUSTOM_AGENTS = 50
MAX_PROJECT_FOLDERS = 100
MAX_PATH_CHARS = 1024
MAX_NAME_CHARS = 40
ONLY_HERE_NAMES = 50
_COUNT_DIR_LIMIT = 20_000
_CUSTOM_ID_RE = re.compile(r"^custom-[a-z0-9](?:[a-z0-9-]{0,62})$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class TrackingConflict(StoreError):
    """The settings changed in another window since the client read them."""

    status = 409


def _home() -> Path:
    return paths.home_dir()


def _real(path: Path) -> Path:
    try:
        return Path(os.path.realpath(path))
    except (OSError, ValueError):
        return Path(os.path.abspath(path))


def _inside_home(path: Path) -> bool:
    home = _real(_home())
    real = _real(path)
    return real == home or home in real.parents


def display_path(path: Path) -> str:
    """``~/…`` for a path inside the home folder, else the absolute path."""
    absolute = Path(os.path.abspath(path))
    home = Path(os.path.abspath(_home()))
    try:
        rel = absolute.relative_to(home)
    except ValueError:
        return str(absolute)
    return "~" if not rel.parts else "~/" + rel.as_posix()


def expand_path(value: str) -> Path:
    """Expand a stored or typed path (``~``, ``~/…`` or absolute)."""
    text = value.strip()
    if text == "~" or text.startswith("~/") or text.startswith("~\\"):
        return Path(os.path.abspath(_home() / text[2:])) if len(text) > 1 else Path(os.path.abspath(_home()))
    return Path(os.path.abspath(Path(text)))


# -- agents known to the app ------------------------------------------------


def known_agents() -> list[scopes.Scope]:
    """The built-in agent roots, in table order (no global, no shared folder)."""
    return [s for s in scopes.builtin_agent_scopes() if s.kind == "agent" and s.id != SHARED_ID]


def _scope_labels() -> dict[str, str]:
    labels = {s.id: s.label for s in scopes.builtin_agent_scopes()}
    labels[SHARED_ID] = SHARED_LABEL
    return labels


def _reads(agent_id: str) -> list[str]:
    """Built-in personal roots this agent reads, its own first."""
    spec = effective.CONSUMERS.get(agent_id) or {}
    found: list[str] = []
    for tier in spec.get("tiers", ()):
        for root in tier.get("roots", ()):
            sid = root.get("scope")
            if sid and sid not in found:
                found.append(sid)
    if agent_id in found:
        found.remove(agent_id)
    return [agent_id] + found


def reads_shared(agent_id: str) -> bool:
    return SHARED_ID in _reads(agent_id)


# -- the document -----------------------------------------------------------


def settings_path(data_dir: Path) -> Path:
    return Path(data_dir) / FILE_NAME


def _startup_project() -> Path | None:
    """The folder the app was started in, when it holds a project skill folder.

    A candidate that *is* a built-in root (starting in the home folder makes
    ``./.claude/skills`` Claude Code's own folder) doesn't count, so the home
    folder is never listed as a project.
    """
    cwd = scopes._cwd()
    built_in = {_real(s.base) for s in scopes.builtin_agent_scopes()}
    for _label, rel, _recursive, _consumer in project_scope_specs():
        try:
            candidate = cwd / rel
            if candidate.is_dir() and _real(candidate) not in built_in:
                return cwd
        except OSError:
            continue
    return None


def default_document() -> dict:
    """Track everything found; the start-up folder is the one project (A6)."""
    start = _startup_project()
    folder = display_path(start) if start is not None else None
    return {
        "version": VERSION,
        "revision": 0,
        "agents": {"chosen": False, "tracked": [], "seen": [], "count_projects": {}},
        "custom_agents": [],
        "projects": {"folders": [folder] if folder else [], "showing": folder},
        "tool_groups": {group: True for group in TOOL_GROUPS},
    }


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise StoreError(message)


def _string_list(value, label: str, limit: int) -> list[str]:
    _need(isinstance(value, list), f"{label} must be a list")
    _need(len(value) <= limit, f"{label} holds too many entries")
    out: list[str] = []
    for item in value:
        _need(isinstance(item, str) and item.strip() and len(item) <= MAX_PATH_CHARS,
              f"{label} entries must be non-empty text")
        text = item.strip()
        if text not in out:
            out.append(text)
    return out


def _normalize_custom(raw) -> dict:
    _need(isinstance(raw, dict), "each custom agent must be an object")
    sid = raw.get("id")
    _need(isinstance(sid, str) and bool(_CUSTOM_ID_RE.match(sid)),
          "a custom agent id must look like custom-name")
    name = raw.get("name")
    _need(isinstance(name, str), "a custom agent needs a name")
    name = " ".join(name.split())
    _need(1 <= len(name) <= MAX_NAME_CHARS, f"Use 1 to {MAX_NAME_CHARS} characters for the name.")
    _need(not _CONTROL_RE.search(name), "The name can't hold control characters.")
    folder = raw.get("folder")
    _need(isinstance(folder, str) and folder.strip() and len(folder) <= MAX_PATH_CHARS,
          "a custom agent needs a folder")
    _need(not _CONTROL_RE.search(folder), "The folder can't hold control characters.")
    project_folder = raw.get("project_folder")
    if project_folder in (None, ""):
        project_folder = None
    else:
        _need(isinstance(project_folder, str) and len(project_folder) <= MAX_PATH_CHARS,
              "the folder inside projects must be text")
        project_folder = project_folder.strip().replace("\\", "/").strip("/")
        parts = [part for part in project_folder.split("/") if part not in ("", ".")]
        _need(bool(parts) and ".." not in parts and not project_folder.startswith("~")
              and not os.path.isabs(project_folder) and not _CONTROL_RE.search(project_folder),
              "The folder inside projects must be a relative path such as .kilo/skills.")
        project_folder = "/".join(parts)
    return {"id": sid, "name": name, "folder": display_path(expand_path(folder)),
            "project_folder": project_folder}


def normalize(raw, *, strict: bool) -> dict:
    """Return a clean document, or raise ``StoreError`` with a plain reason.

    ``strict`` (a save) refuses ids the app doesn't know; a hand-edited file
    being *read* drops them instead, so one stale id doesn't break the page.
    """
    _need(isinstance(raw, dict), "the settings must be a JSON object")
    _need(raw.get("version", VERSION) == VERSION, "the settings were written by another version")
    revision = raw.get("revision", 0)
    _need(isinstance(revision, int) and not isinstance(revision, bool) and revision >= 0,
          "revision must be a whole number")
    agents = raw.get("agents", {})
    _need(isinstance(agents, dict), "agents must be an object")
    chosen = agents.get("chosen", False)
    _need(isinstance(chosen, bool), "agents.chosen must be true or false")
    customs_raw = raw.get("custom_agents", [])
    _need(isinstance(customs_raw, list) and len(customs_raw) <= MAX_CUSTOM_AGENTS,
          "custom_agents must be a list")
    customs = [_normalize_custom(item) for item in customs_raw]
    ids = [c["id"] for c in customs]
    _need(len(set(ids)) == len(ids), "two custom agents share an id")
    valid = {a.id for a in known_agents()} | set(ids)

    def ids_in(value, label):
        items = _string_list(value, label, MAX_CUSTOM_AGENTS + 20)
        unknown = [item for item in items if item not in valid]
        if strict and unknown:
            raise StoreError(f"{label} names an agent the app doesn't know: {unknown[0]}")
        return [item for item in items if item in valid]

    tracked = ids_in(agents.get("tracked", []), "agents.tracked")
    seen = _string_list(agents.get("seen", []), "agents.seen", MAX_CUSTOM_AGENTS + 20)
    seen = [item for item in seen if item in valid]
    counts_raw = agents.get("count_projects", {})
    _need(isinstance(counts_raw, dict), "agents.count_projects must be an object")
    counts: dict[str, bool] = {}
    for key, value in counts_raw.items():
        _need(isinstance(value, bool), "agents.count_projects values must be true or false")
        if key in valid:
            counts[key] = value
        elif strict:
            raise StoreError(f"agents.count_projects names an agent the app doesn't know: {key}")
    projects = raw.get("projects", {})
    _need(isinstance(projects, dict), "projects must be an object")
    folders = [display_path(expand_path(item)) for item in
               _string_list(projects.get("folders", []), "projects.folders", MAX_PROJECT_FOLDERS)]
    folders = list(dict.fromkeys(folders))
    showing = projects.get("showing")
    if showing is not None:
        _need(isinstance(showing, str) and showing.strip(), "projects.showing must be a folder or null")
        showing = display_path(expand_path(showing))
        if showing not in folders:
            _need(not strict, "The folder shown in the table must be in the list of project folders.")
            showing = None
    groups_raw = raw.get("tool_groups", {})
    _need(isinstance(groups_raw, dict), "tool_groups must be an object")
    groups = {}
    for group in TOOL_GROUPS:
        value = groups_raw.get(group, True)
        _need(isinstance(value, bool), f"tool_groups.{group} must be true or false")
        groups[group] = value
    if strict:
        extra = set(groups_raw) - set(TOOL_GROUPS)
        _need(not extra, f"tool_groups names a group the app doesn't know: {sorted(extra)[0] if extra else ''}")
    return {
        "version": VERSION,
        "revision": revision,
        "agents": {"chosen": chosen, "tracked": tracked, "seen": seen, "count_projects": counts},
        "custom_agents": customs,
        "projects": {"folders": folders, "showing": showing},
        "tool_groups": groups,
    }


def load(data_dir: Path) -> tuple[dict, str, str | None]:
    """Return ``(document, state, reason)``; state is ok, default or broken."""
    path = settings_path(data_dir)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return default_document(), "default", None
    except OSError as exc:
        return default_document(), "broken", f"It couldn't be opened ({exc.strerror or exc})."
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return default_document(), "broken", "It isn't a regular file."
    if info.st_size > MAX_FILE_BYTES:
        return default_document(), "broken", "It is larger than a settings file can be."
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return default_document(), "broken", f"It couldn't be read ({getattr(exc, 'strerror', None) or exc})."
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        return default_document(), "broken", f"It isn't valid JSON (line {getattr(exc, 'lineno', '?')})."
    try:
        return normalize(parsed, strict=False), "ok", None
    except StoreError as exc:
        return default_document(), "broken", str(exc)


# -- the view the scope list uses ------------------------------------------


def custom_folder_safe(folder: Path) -> bool:
    """Inside home and not a built-in agent root or the manager's library."""
    if not _inside_home(folder):
        return False
    real = _real(folder)
    if real == _real(_home()):
        return False
    if any(_real(s.base) == real for s in scopes.builtin_agent_scopes()):
        return False
    store = active_store()
    return store is None or _real(Path(store.skills_dir)) != real


class TrackingView:
    """What one document means for the scope list (duck-typed by ``scopes``)."""

    def __init__(self, document: dict, state: str):
        self.document = document
        self.state = state
        agents = document["agents"]
        known = [a.id for a in known_agents()]
        # Broken files keep no custom agents: they live in the file we can't read.
        customs = document["custom_agents"] if state == "ok" else []
        self.customs = customs
        custom_ids = [c["id"] for c in customs]
        if state != "ok" or not agents["chosen"]:
            self.tracked = set(known) | set(custom_ids)
        else:
            self.tracked = set(agents["tracked"])
        self.count = dict(agents["count_projects"]) if state == "ok" else {}
        self.shared = any(reads_shared(a) for a in known if a in self.tracked)
        showing = document["projects"]["showing"] if state == "ok" else None
        if state != "ok":
            start = _startup_project()
            showing = display_path(start) if start is not None else None
        self.showing = showing
        self._labels = _scope_labels()

    # scopes.known_scopes interface
    def shows(self, scope_id: str) -> bool:
        if scope_id == SHARED_ID:
            return self.shared
        return scope_id in self.tracked

    def custom_scopes(self) -> list[tuple[str, str, Path]]:
        """Tracked custom agents whose folder is still a safe place to write.

        A hand-edited file is never trusted with a write target: a folder that
        now resolves outside the home folder, or onto a built-in root or the
        library, is left out of the view instead of becoming writable.
        """
        return [(c["id"], c["name"], expand_path(c["folder"])) for c in self.customs
                if c["id"] in self.tracked and custom_folder_safe(expand_path(c["folder"]))]

    def custom_project_specs(self) -> list[tuple[str, str, bool, str]]:
        return [(f"Project {c['id']}", c["project_folder"], False, c["id"])
                for c in self.customs if c.get("project_folder") and c["id"] in self.tracked]

    def project(self) -> Path | None:
        if not self.showing:
            return None
        folder = expand_path(self.showing)
        # Same rule as a save: inside home, or the folder the app started in.
        if _inside_home(folder) or _real(folder) == _real(scopes._cwd()):
            return folder
        return None

    def counts_project(self, consumer: str | None) -> bool:
        if consumer is None:
            return True
        if consumer == "shared-agent-skills":
            return any(self.count.get(a, True) for a in self.tracked if reads_shared(a))
        return consumer in self.tracked and self.count.get(consumer, True)

    def untracked_message(self, scope_id: str) -> str | None:
        label = self._labels.get(scope_id)
        if label is None:
            custom = next((c for c in self.document["custom_agents"] if c["id"] == scope_id), None)
            label = custom["name"] if custom else None
        if label is None:
            return None
        if scope_id == SHARED_ID:
            return "The Shared folder isn't shown: none of the tracked agents read it."
        return f"{label} isn't tracked. Track it in What to track to see or change its skills."


class Overlay:
    """One server's tracking overlay, re-read whenever the file changes."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._cache: tuple | None = None

    def _signature(self):
        try:
            info = settings_path(self.data_dir).lstat()
        except OSError:
            info = None
        key = (info.st_mtime_ns, info.st_size, info.st_ino) if info else None
        return key, str(scopes._cwd()), str(_home())

    def view(self) -> TrackingView:
        signature = self._signature()
        cached = self._cache
        if cached is not None and cached[0] == signature:
            return cached[1]
        document, state, _reason = load(self.data_dir)
        view = TrackingView(document, state)
        self._cache = (signature, view)
        return view


# -- counting (never reads a document's text) -------------------------------


def _has_document(directory: Path) -> bool:
    for name in DOCUMENT_NAMES:
        try:
            if (directory / name).is_file():
                return True
        except OSError:
            continue
    return False


def count_skill_folders(root: Path, *, recursive: bool) -> tuple[str, list[str] | None]:
    """``(status, names)`` for the skill folders under ``root``.

    Only directory entries and document *existence* are checked; no file is
    opened.  Status is ok, missing, not-a-folder or unreadable (names None).
    """
    try:
        info = root.stat()
    except FileNotFoundError:
        return "missing", None
    except OSError:
        return "unreadable", None
    if not stat.S_ISDIR(info.st_mode):
        return "not-a-folder", None
    if not os.access(root, os.R_OK | os.X_OK):
        return "unreadable", None
    names: list[str] = []
    try:
        children = sorted(root.iterdir())
    except OSError:
        return "unreadable", None
    if not recursive:
        for child in children:
            try:
                if child.is_dir() and _has_document(child):
                    names.append(child.name)
            except OSError:
                continue
        return "ok", names
    visited = 0
    for current, dirs, _files in os.walk(root, followlinks=False):
        here = Path(current)
        visited += 1
        if visited > _COUNT_DIR_LIMIT:
            break
        if here != root and _has_document(here):
            names.append(here.name)
            dirs[:] = []
            continue
        # A linked skill folder at any depth counts; walking stops at it.
        kept = []
        for entry in sorted(dirs):
            child = here / entry
            if child.is_symlink():
                if child.is_dir() and _has_document(child):
                    names.append(entry)
            else:
                kept.append(entry)
        dirs[:] = kept
    return "ok", names


def _scope_names(scope: scopes.Scope) -> tuple[str, list[str] | None]:
    """Names in a scope as the table counts them (tracked roots only)."""
    try:
        if not scope.base.is_dir():
            return count_skill_folders(scope.base, recursive=scope.recursive)
        if not os.access(scope.base, os.R_OK | os.X_OK):
            return "unreadable", None
        rows = scopes._scan_agent_root(scope, link_roots=scopes._peer_link_roots(scope))
    except OSError:
        return "unreadable", None
    return "ok", [str(row.get("name")) for row in rows]


# -- the live report (GET /api/tracking) -----------------------------------


def _folders_read(agent_id: str, tracked: set[str], shared_shown: bool) -> list[dict]:
    labels = _scope_labels()
    by_id = {s.id: s for s in scopes.builtin_agent_scopes()}
    out = []
    for sid in _reads(agent_id):
        scope = by_id.get(sid)
        if scope is None:
            continue
        shown = shared_shown if sid == SHARED_ID else sid in tracked
        out.append({"id": sid, "name": labels.get(sid, sid), "path": display_path(scope.base),
                    "own": sid == agent_id, "tracked": shown})
    return out


def _project_report(folder: str, showing: str | None, custom_specs: list) -> dict:
    path = expand_path(folder)
    status, _ = count_skill_folders(path, recursive=False)
    found: list[str] = []
    total = 0
    if status == "ok":
        for _label, rel, recursive, _consumer in list(project_scope_specs()) + custom_specs:
            sub_status, names = count_skill_folders(path / rel, recursive=recursive)
            if sub_status == "ok":
                found.append(rel)
                total += len(names or [])
    return {"path": folder, "showing": folder == showing, "status": status,
            "skill_folders": found, "skill_count": total if status == "ok" else None}


def report(data_dir: Path, store_skills_dir: Path) -> dict:
    """Saved settings (or defaults) plus what is on disk right now."""
    document, state, reason = load(data_dir)
    view = TrackingView(document, state)
    agents_doc = document["agents"]
    view_scopes = [s for s in _view_scopes(view)]
    names_by_scope: dict[str, list[str] | None] = {}
    status_by_scope: dict[str, str] = {}
    for scope in view_scopes:
        status_by_scope[scope.id], names_by_scope[scope.id] = _scope_names(scope)
    global_status, global_names = count_skill_folders(Path(store_skills_dir), recursive=False)
    names_by_scope["global"] = global_names or []

    def only_here(scope_id: str) -> dict | None:
        mine = names_by_scope.get(scope_id)
        if mine is None:
            return None
        elsewhere: set[str] = set()
        for other, names in names_by_scope.items():
            if other != scope_id and names:
                elsewhere.update(names)
        lonely = sorted({name for name in mine if name not in elsewhere}, key=str.lower)
        return {"count": len(lonely), "names": lonely[:ONLY_HERE_NAMES]}

    agents: list[dict] = []
    for agent in known_agents():
        tracked = agent.id in view.tracked
        if tracked:
            status, names = status_by_scope.get(agent.id), names_by_scope.get(agent.id)
            if status is None:
                status, names = count_skill_folders(agent.base, recursive=agent.recursive)
        else:
            status, names = count_skill_folders(agent.base, recursive=agent.recursive)
        reads = _folders_read(agent.id, view.tracked, view.shared)
        agents.append({
            "id": agent.id, "name": agent.label, "kind": "known", "tracked": tracked,
            "found": status == "ok", "folder": display_path(agent.base), "folder_status": status,
            "skill_count": len(names) if names is not None else None,
            "only_here": only_here(agent.id) if tracked else None,
            "folders_read": reads,
            "also_reads": [r for r in reads if not r["own"] and r["id"] != SHARED_ID],
            "reads_shared": reads_shared(agent.id),
            "count_projects": view.count.get(agent.id, True),
            "has_project_folder": any(c == agent.id for _l, _r, _rec, c in project_scope_specs()),
            "project_folder": None,
        })
    for custom in view.customs:
        base = expand_path(custom["folder"])
        tracked = custom["id"] in view.tracked
        status, names = (status_by_scope.get(custom["id"]), names_by_scope.get(custom["id"])) if tracked else (None, None)
        if not custom_folder_safe(base):
            status, names = "outside-home", None
        elif status is None:
            status, names = count_skill_folders(base, recursive=False)
        agents.append({
            "id": custom["id"], "name": custom["name"], "kind": "custom", "tracked": tracked,
            "found": status == "ok", "folder": custom["folder"], "folder_status": status,
            "skill_count": len(names) if names is not None else None,
            "only_here": only_here(custom["id"]) if tracked and status == "ok" else None,
            "folders_read": [{"id": custom["id"], "name": custom["name"], "path": custom["folder"],
                              "own": True, "tracked": tracked}],
            "also_reads": [], "reads_shared": False,
            "count_projects": view.count.get(custom["id"], True),
            "has_project_folder": bool(custom.get("project_folder")),
            "project_folder": custom.get("project_folder"),
        })
    shared_scope = next(s for s in scopes.builtin_agent_scopes() if s.id == SHARED_ID)
    shared_status, shared_names = (status_by_scope.get(SHARED_ID), names_by_scope.get(SHARED_ID))
    if shared_status is None:
        shared_status, shared_names = count_skill_folders(shared_scope.base, recursive=True)
    shared = {
        "id": SHARED_ID, "name": SHARED_LABEL, "shown": view.shared,
        "read_by": [a.id for a in known_agents() if a.id in view.tracked and reads_shared(a.id)],
        "folder": display_path(shared_scope.base), "folder_status": shared_status,
        "found": shared_status == "ok",
        "skill_count": len(shared_names) if shared_names is not None else None,
        "only_here": only_here(SHARED_ID) if view.shared else None,
    }
    folders = document["projects"]["folders"] if state == "ok" else ([view.showing] if view.showing else [])
    custom_specs = [(f"Project {c['id']}", c["project_folder"], False, c["id"])
                    for c in view.customs if c.get("project_folder")]
    projects = [_project_report(folder, view.showing, custom_specs) for folder in folders]
    newly = []
    if state == "ok" and agents_doc["chosen"]:
        seen = set(agents_doc["seen"]) | set(agents_doc["tracked"])
        for row in agents:
            if row["kind"] == "known" and not row["tracked"] and row["found"] and row["id"] not in seen:
                newly.append({"id": row["id"], "name": row["name"], "skill_count": row["skill_count"]})
    copies = sorted(p.name for p in Path(data_dir).glob("tracking.broken-*.json"))
    return {
        "file": {"state": state, "reason": reason, "path": str(settings_path(data_dir)),
                 "copies": copies[-5:]},
        "settings": document,
        "revision": document["revision"] if state == "ok" else 0,
        "tracked": sorted(view.tracked),
        "agents": agents,
        "shared": shared,
        "projects": projects,
        "showing": view.showing,
        "startup_folder": display_path(scopes._cwd()),
        "tool_groups": dict(document["tool_groups"]) if state == "ok" else {g: True for g in TOOL_GROUPS},
        "newly_found": newly,
        "summary": {
            "agents_tracked": sum(1 for a in agents if a["tracked"]),
            "agents_total": len(agents),
            "project_folders": len(projects),
            "tool_groups_on": sum(1 for g in TOOL_GROUPS
                                  if (document["tool_groups"] if state == "ok" else {}).get(g, True)),
        },
    }


def _view_scopes(view: TrackingView) -> list[scopes.Scope]:
    """The scope list this view produces (same rules as ``known_scopes``)."""
    from .context import bound_scope_overlay

    class _Fixed:
        def view(self):
            return view

    with bound_scope_overlay(_Fixed()):
        return [s for s in scopes._unique_physical_scopes(scopes.known_scopes()) if s.id != "global"]


# -- live folder check (POST /api/tracking/check-folder) --------------------


def _problem(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _owner_of(real: Path, document: dict, ignore_id: str | None) -> tuple[str, str] | None:
    """Which agent root (built-in, shared, custom, library) is this folder."""
    for scope in scopes.builtin_agent_scopes():
        if _real(scope.base) == real:
            return scope.id, (SHARED_LABEL if scope.id == SHARED_ID else scope.label)
    for custom in document["custom_agents"]:
        if custom["id"] != ignore_id and _real(expand_path(custom["folder"])) == real:
            return custom["id"], custom["name"]
    return None


def _suggest_name(path: Path) -> str:
    parts = [p for p in path.parts if p not in ("", os.sep)]
    if not parts:
        return ""
    candidate = parts[-1]
    if candidate.lower() == "skills" and len(parts) > 1:
        candidate = parts[-2]
    candidate = candidate.lstrip(".").replace("-", " ").replace("_", " ").strip()
    return candidate[:1].upper() + candidate[1:MAX_NAME_CHARS] if candidate else ""


def _folder_problems(path: Path) -> tuple[list[dict], str]:
    """Shared plain-word checks: inside home, exists, a folder, readable."""
    if not _inside_home(path):
        return [_problem("outside-home", "Pick a folder inside your home folder.")], "outside-home"
    status, _ = count_skill_folders(path, recursive=False)
    if status == "missing":
        return [_problem("missing", "This folder doesn't exist. Check the path, or create it first.")], status
    if status == "not-a-folder":
        return [_problem("not-a-folder", "That's a file, not a folder.")], status
    if status == "unreadable":
        return [_problem("unreadable", "This folder can't be read. Check its permissions.")], status
    return [], status


def _agent_folder_problems(path: Path, document: dict, view: TrackingView, ignore_id: str | None,
                           library: Path) -> list[dict]:
    problems, _status = _folder_problems(path)
    if problems:
        return problems
    real = _real(path)
    if real == _real(library):
        return [_problem("library", "That's Skills Manager's own library. Pick an agent's folder.")]
    owner = _owner_of(real, document, ignore_id)
    if owner is not None:
        sid, label = owner
        if sid == SHARED_ID:
            return [_problem("already-tracked", "That's the Shared folder. It's shown whenever a tracked agent reads it.")]
        if sid in view.tracked:
            return [_problem("already-tracked", f"That's {label}'s folder. It's already tracked.")]
        return [_problem("already-tracked", f"That's {label}'s folder. Track {label} instead of adding it again.")]
    return []


def _project_folder_problems(path: Path, document: dict, ignore: str | None) -> list[dict]:
    if _real(path) == _real(scopes._cwd()) and path.is_dir():
        problems = []
    else:
        problems, _status = _folder_problems(path)
    if problems:
        return problems
    shown = display_path(path)
    listed = [f for f in document["projects"]["folders"] if f != ignore]
    if any(_real(expand_path(f)) == _real(path) for f in listed) or shown in listed:
        return [_problem("already-listed", "This folder is already in your list.")]
    return []


def check_folder(data_dir: Path, store_skills_dir: Path, data: dict) -> dict:
    """Live, read-only check of one typed folder (S16 / S18)."""
    raw = data.get("path")
    purpose = data.get("purpose", "agent")
    ignore = data.get("ignore_id")
    if purpose not in ("agent", "project"):
        raise StoreError("purpose must be agent or project")
    if ignore is not None and not isinstance(ignore, str):
        raise StoreError("ignore_id must be text")
    if not isinstance(raw, str):
        raise StoreError("path must be text")
    text = raw.strip()
    result = {"path": raw, "purpose": purpose, "display": None, "ok": False, "problems": [], "preview": None}
    if not text:
        result["problems"] = [_problem("empty", "Type or paste a folder path.")]
        return result
    if len(text) > MAX_PATH_CHARS or _CONTROL_RE.search(text):
        result["problems"] = [_problem("invalid", "That doesn't look like a folder path.")]
        return result
    if not (text.startswith("~") or os.path.isabs(text)):
        result["problems"] = [_problem("relative", "Use a full path, such as ~/.kilo/skills.")]
        return result
    path = expand_path(text)
    result["display"] = display_path(path)
    document, state, _reason = load(data_dir)
    view = TrackingView(document, state)
    if purpose == "agent":
        problems = _agent_folder_problems(path, document, view, ignore, Path(store_skills_dir))
        if not problems:
            _status, names = count_skill_folders(path, recursive=False)
            result["preview"] = {"skill_count": len(names or []), "suggested_name": _suggest_name(path)}
    else:
        problems = _project_folder_problems(path, document, ignore)
        if not problems:
            customs = [(f"Project {c['id']}", c["project_folder"], False, c["id"])
                       for c in document["custom_agents"] if c.get("project_folder")]
            report_row = _project_report(display_path(path), None, customs)
            result["preview"] = {"skill_folders": report_row["skill_folders"],
                                 "skill_count": report_row["skill_count"] or 0}
    result["problems"] = problems
    result["ok"] = not problems
    return result


# -- saving (PUT /api/tracking) ---------------------------------------------


def _validate_against(new: dict, current: dict, current_state: str, store_skills_dir: Path) -> None:
    """Every rule the page enforces, re-checked here before anything is written."""
    known_labels = {a.label.lower(): a.label for a in known_agents()}
    known_labels.update({SHARED_LABEL.lower(): SHARED_LABEL, "global": "Global"})
    old_customs = {c["id"]: c for c in (current["custom_agents"] if current_state == "ok" else [])}
    names: dict[str, str] = {}
    real_folders: dict[Path, str] = {}
    view = TrackingView(new, "ok")
    for custom in new["custom_agents"]:
        lowered = custom["name"].lower()
        if lowered in known_labels:
            raise StoreError(f"The name {custom['name']} is already used by {known_labels[lowered]}.")
        if lowered in names:
            raise StoreError(f"The name {custom['name']} is already used by another agent.")
        names[lowered] = custom["id"]
        path = expand_path(custom["folder"])
        before = old_customs.get(custom["id"])
        changed = before is None or before["folder"] != custom["folder"]
        if changed:
            problems = _agent_folder_problems(path, {**new, "custom_agents": [
                c for c in new["custom_agents"] if c["id"] != custom["id"]]}, view, custom["id"],
                Path(store_skills_dir))
            if problems:
                raise StoreError(f"{custom['name']}: {problems[0]['message']}")
        elif not _inside_home(path):
            raise StoreError(f"{custom['name']}: Pick a folder inside your home folder.")
        real = _real(path)
        if real in real_folders:
            raise StoreError(f"{custom['name']} uses the same folder as {real_folders[real]}.")
        real_folders[real] = custom["name"]
    agents = new["agents"]
    if agents["chosen"]:
        if not agents["tracked"]:
            raise StoreError("At least one agent stays tracked.")
    old_folders = set(current["projects"]["folders"]) if current_state == "ok" else set()
    start = scopes._cwd()
    for folder in new["projects"]["folders"]:
        path = expand_path(folder)
        is_start = _real(path) == _real(start)
        if folder in old_folders:
            if not is_start and not _inside_home(path):
                raise StoreError(f"{folder}: Pick a folder inside your home folder.")
            continue
        if is_start and path.is_dir():
            continue
        problems, _status = _folder_problems(path)
        if problems:
            raise StoreError(f"{folder}: {problems[0]['message']}")
    reals = [_real(expand_path(f)) for f in new["projects"]["folders"]]
    if len(set(reals)) != len(reals):
        raise StoreError("This folder is already in your list.")


def _copy_broken_aside(path: Path) -> Path | None:
    """Keep a hand-edited file we couldn't read before replacing it (T8)."""
    if not path.exists() and not path.is_symlink():
        return None
    target = path.with_name(f"tracking.broken-{stamp()}.json")
    counter = 1
    while target.exists():
        counter += 1
        target = path.with_name(f"tracking.broken-{stamp()}-{counter}.json")
    if path.is_symlink() or not path.is_file():
        # Never follow a link or copy a device: move the entry itself aside.
        os.replace(path, target)
    else:
        shutil.copyfile(path, target)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def save(data_dir: Path, store_skills_dir: Path, body: dict) -> dict:
    """Replace the whole document; refuse a stale ``revision`` with 409."""
    if not isinstance(body, dict):
        raise StoreError("the settings must be a JSON object")
    expected = body.get("revision")
    if not isinstance(expected, int) or isinstance(expected, bool):
        raise StoreError("revision must be the whole number you read")
    new = normalize(copy.deepcopy(body), strict=True)
    path = settings_path(data_dir)
    with mutation_lock(path):
        current, state, _reason = load(data_dir)
        current_revision = current["revision"] if state == "ok" else 0
        if expected != current_revision:
            raise TrackingConflict("These settings changed in another window. Reload to see them.")
        _validate_against(new, current, state, store_skills_dir)
        first_choice = new["agents"]["chosen"] and not (state == "ok" and current["agents"]["chosen"])
        if first_choice:
            # Every agent on the page when the user first chose has been seen;
            # only one found after this raises the "Found Gemini" notice (T7).
            seen = new["agents"]["seen"]
            for agent in known_agents():
                if agent.id not in seen and count_skill_folders(agent.base, recursive=False)[0] == "ok":
                    seen.append(agent.id)
        if state == "broken":
            _copy_broken_aside(path)
        new["revision"] = current_revision + 1
        atomic_write_text(path, json.dumps(new, indent=2) + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return report(data_dir, store_skills_dir)


def adapters_filter(view: TrackingView):
    """Drop adapter records for built-in agents the user doesn't track."""
    known = {a.id for a in known_agents()}

    def keep(record: dict) -> bool:
        rid = record.get("id")
        return rid not in known or rid in view.tracked

    return keep


def tool_group_on(view: TrackingView, group: str) -> bool:
    if view.state != "ok":
        return True
    return bool(view.document["tool_groups"].get(group, True))
