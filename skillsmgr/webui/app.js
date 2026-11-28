/* Jackfield — Vue 3 application (no build step).
 * Every read and write goes through the documented REST API; the observed-state
 * vocabulary comes from domain.js, shared with the model layer. */
"use strict";

const Domain = window.SkillManagerDomain;
const Model = window.SkillsV2Model;
const Jack = window.Jackfield;
if (!Domain || !Model || !Jack?.router) {
  const failure = document.createElement("div");
  failure.setAttribute("role", "alert");
  failure.style.cssText = "margin:2rem;padding:1rem;border:1px solid #b42318;border-radius:8px;font:15px/1.5 system-ui,sans-serif;color:#b42318;background:#fff;";
  failure.textContent = "Jackfield could not start: a script did not load. Reload the page; if it persists, the installed files are incomplete.";
  document.body.appendChild(failure);
  throw new Error("v2 scripts missing");
}

const { api } = Domain;
const { createApp, markRaw } = Vue;
const Router = Jack.router;
const { plural, join, words, titleCase, shortPath, BROKEN_WHY, documentPreview, renderDoc, stripFrontmatter, validName, toolItems } = Model;

/* ---------- Icons (constant, trusted markup) ---------- */
const PATHS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3m6 0h4"/>',
  ok: '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  warn: '<path d="M12 3.5 2.8 19.5h18.4L12 3.5Z"/><path d="M12 10v4M12 17v.01"/>',
  bad: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
  off: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
  dash: '<path d="M7 12h10"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.01"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>',
  share: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  home: '<path d="m4 11 8-7 8 7"/><path d="M6 10v10h12V10"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
  map: '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z"/><path d="M9 3v15M15 6v15"/>',
  inbox: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5 5h14l1 8v6H4v-6Z"/>',
  tools: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  upload: '<path d="M12 15V4M8 8l4-4 4 4"/><path d="M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/>',
  auto: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
};

const CAP = 48;
const TABLE_BATCH_LIMIT = 500;
const FALLBACK_AGENT = { id: "", name: "Unknown", color: "#55585f", initials: "?", path: "" };
const MAP_STATES = {
  on: { icon: "ok", label: "Enabled on disk" },
  warn: { icon: "warn", label: "Copies differ" },
  bad: { icon: "bad", label: "Can't be read" },
  off: { icon: "off", label: "Turned off on disk" },
  link: { icon: "share", label: "Linked copy" },
  missing: { icon: "dash", label: "No copy listed" },
};

const THEMES = ["system", "light", "dark"];
function savedPreference(key, choices, fallback) {try{const value=localStorage.getItem(key);return choices.includes(value)?value:fallback;}catch(e){return fallback;}}


/* ---------- What to track (agent tracking) ----------
 * The server filters every route by tracking.json; this mixin only reads the
 * report, writes the whole document back (PUT /api/tracking, revision-checked)
 * and offers Undo by putting the previous document back. Nothing on disk
 * outside tracking.json ever changes from here. */
const TRACK_GROUPS = [
  { id: "add-skills", key: "add", name: "Add skills", text: "Install skills, make profiles and templates, or update a copy from a folder." },
  { id: "check-setup", key: "inspect", name: "Check my setup", text: "Run quality checks, see where agents look, and diagnose library problems." },
  { id: "ai-assist", key: "ai", name: "AI assist", text: "Write, test, shorten and check skills with your AI service." },
];
const TRACK_RESERVED = ["shared folder", "global", "your library"];
const trackClone = (value) => JSON.parse(JSON.stringify(value));
const trackSlug = (name) => String(name).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "agent";
/* Settings belongs to no tool group, so it can never be switched off. */
function toolEnabled(groupsOn, id) {
  if (id === "settings" || !groupsOn) return true;
  const group = Model.toolGroups.find((g) => g.items.some((item) => item.id === id));
  return !group || groupsOn[group.key] !== false;
}
const trackingMixin = {
  data() {
    return { tracking: null, trackingError: "", trackingNotes: {}, trackOpen: "", trackBrokenSeen: false,
      mapMenu: "", mapConfirm: "", projectMenu: false, trackForm: null, trackCheckSeq: 0, trackSeq: 0, trackFailSeq: 0, mapMenuPos: {} };
  },
  computed: {
    trackGroups() { return TRACK_GROUPS; },
    trackAgents() { return this.tracking ? this.tracking.agents : []; },
    trackTrackedCount() { return this.trackAgents.filter((a) => a.tracked).length; },
    trackSummary() {
      const t = this.tracking; if (!t) return "";
      const s = t.summary;
      return `Tracking ${s.agents_tracked} of ${plural(s.agents_total, "agent")} · ${plural(s.project_folders, "project folder")} · ${s.tool_groups_on} of 3 tool groups on`;
    },
    trackSettingsLine() {
      const t = this.tracking; if (!t) return "";
      const s = t.summary;
      return `${plural(s.agents_tracked, "agent")}, ${plural(s.project_folders, "project folder")}, ${s.tool_groups_on === 3 ? "3 tool groups" : s.tool_groups_on + " of 3 tool groups"}`;
    },
    toolGroupsOn() {
      const on = this.tracking ? this.tracking.tool_groups : {};
      return Object.fromEntries(TRACK_GROUPS.map((g) => [g.key, on[g.id] !== false]));
    },
    trackNoAgents() { return !!this.tracking && this.tracking.summary.agents_tracked === 0; },
    trackNewlyFound() { return this.tracking && this.tracking.newly_found.length ? this.tracking.newly_found[0] : null; },
    trackShowing() {
      const t = this.tracking; if (!t || !t.showing) return null;
      return t.projects.find((p) => p.path === t.showing) || { path: t.showing, status: "missing" };
    },
    trackShowingLabel() { const s = this.trackShowing; return s ? s.path.split("/").filter(Boolean).pop() : "None"; },
    trackFormAgent() { const f = this.trackForm; return f && f.kind === "agent" ? f : null; },
    trackFormProject() { const f = this.trackForm; return f && f.kind === "project" ? f : null; },
    trackNameError() {
      const f = this.trackFormAgent; if (!f || f.saving) return "";
      const name = f.name.trim().replace(/\s+/g, " ");
      if (!name) return f.nameTouched ? "Give the agent a name." : "";
      if (name.length > 40) return "Use 40 characters or fewer.";
      if (/[\u0000-\u001f\u007f]/.test(name)) return "Use letters, numbers and spaces.";
      const lower = name.toLowerCase();
      if (TRACK_RESERVED.includes(lower)) return `“${name}” is already used in the app. Choose another name.`;
      const taken = this.trackAgents.find((a) => a.id !== f.id && a.name.replace(/\s+/g, " ").toLowerCase() === lower);
      return taken ? `${taken.name} is already an agent. Choose another name.` : "";
    },
    trackFolderInsideError() {
      const f = this.trackFormAgent; if (!f || !f.projectFolder.trim()) return "";
      const v = f.projectFolder.trim();
      if (v.startsWith("/") || v.startsWith("~")) return "Use a folder inside the project, such as .kilo/skills.";
      if (v.split(/[\\/]/).includes("..")) return "Stay inside the project folder.";
      return "";
    },
    trackFormDirty() {
      const f = this.trackForm; if (!f) return false;
      if (f.kind === "project") return !!f.path.trim();
      return f.path.trim() !== f.basePath || f.name.trim() !== f.baseName || f.projectFolder.trim() !== f.baseProject;
    },
    trackFormReady() {
      const f = this.trackForm; if (!f || f.saving) return false;
      if (!f.check || f.check.path !== f.path || !f.check.ok) return false;
      if (f.kind === "agent") return !!f.name.trim() && !this.trackNameError && !this.trackFolderInsideError;
      return true;
    },
  },
  methods: {
    /* A pointer press outside an open column or project menu closes it. */
    watchTrackMenus() {
      document.addEventListener("mousedown", (e) => {
        if (!(e.target instanceof Element) || e.target.closest(".trk-colmenu, .trk-picker")) return;
        this.mapMenu = ""; this.projectMenu = false;
      });
      window.addEventListener("scroll", () => { if (this.mapMenu) this.mapMenu = ""; }, { passive: true });
      window.addEventListener("resize", () => { if (this.mapMenu) this.mapMenu = ""; });
    },
    async loadTracking() {
      /* A slower read must never replace a newer read or a save's answer. */
      const seq = ++this.trackSeq;
      try { const res = await api("/api/tracking"); if (seq !== this.trackSeq) return; this.tracking = markRaw(res); this.trackingError = ""; }
      catch (e) { if (seq === this.trackSeq) this.trackingError = this.friendly(e.message); return; }
      if (this.route.page === "tracking" && this.route.name && !this.trackForm) this.openTrackForm(this.route.name);
    },

    trackAgent(id) { return this.trackAgents.find((a) => a.id === id) || null; },
    trackingTrackable(id) { const a = this.trackAgent(id); return !!a && a.tracked; },
    /* The document to send: the saved settings, with the effective tracked set
     * written out the first time the user chooses (the server marks every
     * agent found at that moment as seen). */
    trackDocument() {
      const t = this.tracking;
      const doc = trackClone(t.settings);
      doc.revision = t.revision;
      if (t.file.state !== "ok") { doc.custom_agents = []; }
      if (!doc.agents.chosen) { doc.agents.chosen = true; doc.agents.tracked = [...t.tracked]; }
      return doc;
    },
    async putTracking(doc) {
      const res = await api("/api/tracking", { method: "PUT", body: JSON.stringify(doc) });
      this.trackSeq++;
      this.tracking = markRaw(res);
      return res;
    },
    /* One change, saved at once, with Undo. `rowId` places a failure next to
     * the row that caused it instead of a toast far away. */
    async saveTracking(change, { message, undoText, rowId = "", undo = true } = {}) {
      if (!this.tracking || this.busy) return false;
      const before = trackClone(this.tracking.settings);
      const doc = this.trackDocument();
      change(doc);
      this.busy = true;
      this.trackingNotes = { ...this.trackingNotes, [rowId || "_"]: "" };
      let saved;
      try {
        saved = await this.putTracking(doc);
        await this.refresh();
      } catch (e) {
        const text = this.friendly(e.message);
        await this.loadTracking();
        this.trackFailSeq++; // re-render switches and radios the browser already flipped
        if (rowId && this.route.page === "tracking") this.trackingNotes = { ...this.trackingNotes, [rowId]: text }; else this.toast(text, { err: true });
        return false;
      } finally { this.busy = false; }
      /* A filter on an agent that just left would hide every skill. */
      if (this.agentFilter !== "all" && !this.agentInfos.some((i) => i.id === this.agentFilter)) this.agentFilter = "all";
      /* Undo puts a whole earlier document back, so only the latest change may
       * offer it: an older Undo would also revert every change made since. */
      this.toasts.filter((note) => note.trackingUndo).forEach((note) => this.dismissToast(note));
      if (message) this.toast(message, undo ? { undoText: undoText || "Undone.", trackingUndo: true,
        undoAt: rowId === "_form" ? "#/settings/tracking" : null, undo: async () => {
        await this.putTracking({ ...before, revision: saved.revision });
      } } : {});
      return true;
    },
    trackStatus(a) {
      if (a.folder_status === "missing") return a.kind === "custom" ? "Folder missing: not shown in the table" : "Not found: nothing to show yet";
      if (a.folder_status === "not-a-folder") return "That path isn't a folder: not shown in the table";
      if (a.folder_status === "unreadable") return "Its folder can't be read";
      if (a.folder_status === "outside-home") return "Its folder is outside your home folder: not shown";
      const n = a.skill_count == null ? "" : " · " + plural(a.skill_count, "skill");
      return (a.tracked ? "Tracked" : "Found") + n + (a.tracked ? "" : " · Not tracked");
    },
    trackLastAgent(a) { return a.tracked && this.trackTrackedCount <= 1; },
    trackToggle(a, on) {
      if (on) {
        return this.saveTracking((doc) => { doc.agents.tracked = [...new Set([...doc.agents.tracked, a.id])]; },
          { rowId: a.id, message: `Tracking ${a.name}.`, undoText: `Stopped tracking ${a.name} again.` });
      }
      this.askStopTracking(a.id);
    },
    /* What leaves the table, worded once for the page dialog and the Sync map panel. */
    trackLeaving(id) {
      const a = this.trackAgent(id); if (!a) return null;
      const only = a.only_here;
      const lines = [`The ${a.name} column and its counts leave the table.`];
      let count = null;
      if (a.folder_status === "missing" || a.folder_status === "not-a-folder" || a.folder_status === "outside-home") lines.splice(0, 1, `${a.name} has nothing in the table now, so nothing leaves it.`);
      else if (a.folder_status !== "ok") lines.push(`${a.name}'s folder can't be read, so we can't count its skills.`);
      else if (!only) lines.push("Some skill folders couldn’t be fully read, so we can’t confirm how many skills will disappear.");
      else if (!only.count) { lines.push(`Every skill in ${a.name} also lives in another place that will stay visible.`); count = 0; }
      else { lines.push(`${plural(only.count, "skill lives", "skills live")} only in ${a.name} and will no longer show.`); count = only.count; }
      const custom = a.kind === "custom";
      /* The mini table preview (TablePreview): today's columns with their skill
       * counts, the leaving one marked. Shown only when a column really leaves. */
      const columns = this.agentInfos.map((inf) => ({ id: inf.id, name: inf.agent.name, count: inf.mine.length, leaving: inf.id === id }));
      return { agent: a, lines, count, columns: columns.some((c) => c.leaving) ? columns : [], names: only ? only.names : [], more: only ? Math.max(0, only.count - only.names.length) : 0,
        preview: count ? `Skills shown: ${this.fmt(this.shelfTotal)} → ${this.fmt(Math.max(0, this.shelfTotal - count))}` : "",
        safe: custom ? `Nothing on disk changes. ${a.folder} stays as it is.` : "Nothing on disk changes. You can track it again any time.",
        title: custom ? `Remove ${a.name}?` : `Stop tracking ${a.name}?`, confirm: custom ? `Remove ${a.name}` : `Stop tracking ${a.name}`, custom };
    },
    askStopTracking(id) {
      const leave = this.trackLeaving(id); if (!leave) return;
      if (this.trackLastAgent(leave.agent)) { this.trackingNotes = { ...this.trackingNotes, [id]: "At least one agent stays tracked." }; return; }
      this.openDialog({ title: leave.title, lines: leave.lines, columns: leave.columns, columnsAgent: leave.agent.name, cancel: leave.custom ? "Keep " + leave.agent.name : "Keep tracking", preview: leave.preview, names: leave.names, namesMore: leave.more,
        namesLabel: `See the ${plural(leave.count || 0, "skill")}`, safe: leave.safe, confirm: leave.confirm,
        onConfirm: () => this.stopTracking(id) });
    },
    stopTracking(id) {
      const a = this.trackAgent(id); if (!a) return;
      this.mapConfirm = "";
      if (a.kind === "custom") {
        /* The server checks a re-added folder again, so a folder that is gone
         * could not come back: no Undo is offered then. */
        return this.saveTracking((doc) => {
          doc.custom_agents = doc.custom_agents.filter((c) => c.id !== id);
          doc.agents.tracked = doc.agents.tracked.filter((x) => x !== id);
        }, { rowId: id, message: `Removed ${a.name}. Its folder is unchanged.`, undoText: `${a.name} is back.`, undo: a.folder_status === "ok" });
      }
      return this.saveTracking((doc) => { doc.agents.tracked = doc.agents.tracked.filter((x) => x !== id); },
        { rowId: id, message: `Stopped tracking ${a.name}. Nothing on disk changed.`, undoText: `Tracking ${a.name} again.` });
    },
    trackCountProjects(a, on) {
      return this.saveTracking((doc) => { doc.agents.count_projects = { ...doc.agents.count_projects, [a.id]: on }; },
        { rowId: a.id, message: on ? `Counting project folders for ${a.name}.` : `Not counting project folders for ${a.name}.` });
    },
    trackGroup(group, on) {
      return this.saveTracking((doc) => { doc.tool_groups = { ...doc.tool_groups, [group.id]: on }; },
        { rowId: group.id, message: on ? `${group.name} is on. Its settings were kept.` : `${group.name} is off. Its settings are kept.` });
    },
    trackGroupByKey(key, on) { const g = TRACK_GROUPS.find((x) => x.key === key); if (g) this.trackGroup(g, on); },
    trackShow(folder) {
      if (this.projectMenu) { this.projectMenu = false; this.$nextTick(() => this.$refs.projectBtn?.focus()); }
      return this.saveTracking((doc) => { doc.projects.showing = folder; },
        { message: folder ? `Showing ${folder} in the table.` : "No project folder is shown in the table." });
    },
    trackRemoveProject(folder) {
      const row = this.tracking && this.tracking.projects.find((p) => p.path === folder);
      return this.saveTracking((doc) => {
        doc.projects.folders = doc.projects.folders.filter((f) => f !== folder);
        if (doc.projects.showing === folder) doc.projects.showing = null;
      }, { rowId: folder, message: `Removed ${folder} from the list. Its files are unchanged.`, undoText: `${folder} is back in the list.`, undo: !!row && row.status === "ok" });
    },
    trackFoundTrack(found) {
      return this.saveTracking((doc) => { doc.agents.tracked = [...new Set([...doc.agents.tracked, found.id])]; doc.agents.seen = [...new Set([...doc.agents.seen, found.id])]; },
        { message: `Tracking ${found.name}.`, undoText: `Stopped tracking ${found.name} again.` });
    },
    trackFoundLater(found) {
      return this.saveTracking((doc) => { doc.agents.seen = [...new Set([...doc.agents.seen, found.id])]; },
        { message: `${found.name} stays on What to track as Not tracked.`, undo: false });
    },
    trackReset() {
      const t = this.tracking;
      return this.saveTracking((doc) => {
        doc.agents = { chosen: false, tracked: [], seen: [], count_projects: {} };
        doc.custom_agents = []; doc.tool_groups = { "add-skills": true, "check-setup": true, "ai-assist": true };
        doc.projects = { folders: t.projects.map((p) => p.path), showing: t.showing };
      }, { message: "Tracking everything found. The unreadable file was kept as a copy beside it.", undo: false });
    },
    trackDetails(id) { this.mapMenu = ""; this.trackOpen = id; Router.go("#/settings/tracking"); },
    /* ----- Sync map column menu and its panel confirm ----- */
    /* The table scrolls inside its own box, so the menu is placed on the
     * viewport (fixed) from its button, kept inside the window, and closed
     * when the table scrolls under it. */
    toggleMapMenu(id) {
      const b = document.getElementById("map-menu-btn-" + id)?.getBoundingClientRect();
      if (b) this.mapMenuPos = { top: Math.round(b.bottom + 4) + "px", left: Math.round(Math.max(8, Math.min(b.left, innerWidth - 268))) + "px" };
      this.mapMenu = this.mapMenu === id ? "" : id; if (this.mapMenu) this.$nextTick(() => document.querySelector(".map-menu [role^=menuitem]:not([disabled])")?.focus()); },
    mapMenuKeys(e) {
      if (e.key === "Escape") { const id = this.mapMenu; this.mapMenu = ""; this.$nextTick(() => document.getElementById("map-menu-btn-" + id)?.focus()); return; }
      if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
      e.preventDefault();
      const items = [...e.currentTarget.querySelectorAll("[role^=menuitem]:not([disabled])")];
      const i = items.indexOf(document.activeElement);
      const next = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : (i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items[next]?.focus();
    },
    mapAskStop(id, event) {
      this.mapMenu = "";
      const a = this.trackAgent(id);
      if (!a || this.trackLastAgent(a)) return;
      this.selectMap(id, event);
      this.mapOrigin = document.getElementById("map-menu-btn-" + id) || this.mapOrigin;
      this.mapConfirm = id;
      this.$nextTick(() => document.getElementById("map-confirm-h")?.focus());
    },
    /* WAI-ARIA menu button: Tab out of an open menu closes it. Only a real
     * focus target outside counts, so a click on an item is never lost. */
    trackMenuBlur(e) {
      const next = e.relatedTarget;
      if (next instanceof Element && !e.currentTarget.contains(next)) { this.mapMenu = ""; this.projectMenu = false; }
    },
    toggleProjectMenu() {
      this.projectMenu = !this.projectMenu;
      if (this.projectMenu) this.$nextTick(() => document.querySelector("#trk-project-menu [role^=menuitem]:not([disabled])")?.focus());
    },
    mapCancelStop() { const id = this.mapConfirm; this.mapConfirm = ""; this.$nextTick(() => document.getElementById("map-menu-btn-" + id)?.focus()); },
    /* ----- Add other agent / Edit agent / Add project folder ----- */
    openTrackForm(route) {
      const t = this.tracking;
      if (!route || !t) { this.trackForm = null; return; }
      if (route === "add-project") {
        this.trackForm = { kind: "project", path: "", check: null, checking: false, show: true, saving: false, error: "" };
        return;
      }
      const editing = route.startsWith("agent:") ? t.agents.find((a) => a.id === route.slice(6) && a.kind === "custom") : null;
      if (route.startsWith("agent:") && !editing) { this.trackForm = null; return; }
      this.trackForm = { kind: "agent", id: editing ? editing.id : "", path: editing ? editing.folder : "", basePath: editing ? editing.folder : "",
        name: editing ? editing.name : "", baseName: editing ? editing.name : "", nameTouched: !!editing,
        projectFolder: editing?.project_folder || "", baseProject: editing?.project_folder || "", more: !!editing?.project_folder,
        check: null, checking: false, saving: false, error: "" };
      if (editing) this.trackCheck();
    },
    trackPathInput(value) {
      const f = this.trackForm; if (!f) return;
      f.path = value; f.check = null; f.checking = false;
      this.trackCheckSeq++; // an answer for the earlier text must not land
      clearTimeout(this.trackCheckTimer);
      this.trackCheckTimer = setTimeout(() => this.trackCheck(), 250);
    },
    async trackCheck() {
      const f = this.trackForm; if (!f) return;
      const seq = ++this.trackCheckSeq, path = f.path;
      if (!path.trim()) { f.check = null; f.checking = false; return; }
      f.checking = true;
      try {
        const res = await api("/api/tracking/check-folder", { method: "POST",
          body: JSON.stringify({ path, purpose: f.kind, ignore_id: f.kind === "agent" ? (f.id || null) : null }) });
        if (seq !== this.trackCheckSeq || this.trackForm !== f) return;
        f.check = res;
        if (f.kind === "agent" && !f.nameTouched && res.preview?.suggested_name) f.name = res.preview.suggested_name;
      } catch (e) {
        if (seq === this.trackCheckSeq && this.trackForm === f) f.check = { path, ok: false, problems: [{ code: "failed", message: this.friendly(e.message) }] };
      } finally { if (seq === this.trackCheckSeq && this.trackForm === f) f.checking = false; }
    },
    trackFormCancel() {
      if (!this.trackFormDirty) { Router.go("#/settings/tracking"); return; }
      const agent = this.trackForm.kind === "agent";
      this.openDialog({ title: agent ? (this.trackForm.id ? "Discard your changes?" : "Discard this agent?") : "Discard this folder?",
        lines: ["What you typed here won't be saved."], cancel: "Keep editing", confirm: "Discard",
        onConfirm: () => { this.trackForm = null; Router.go("#/settings/tracking"); } });
    },
    async trackFormSave() {
      const f = this.trackForm;
      if (!this.trackFormReady) { if (f && f.kind === "agent") f.nameTouched = true; return; }
      const display = f.check.display || f.path.trim();
      f.saving = true; f.error = "";
      let ok;
      if (f.kind === "project") {
        ok = await this.saveTracking((doc) => {
          doc.projects.folders = [...doc.projects.folders.filter((x) => x !== display), display];
          if (f.show) doc.projects.showing = display;
        }, { rowId: "_form", message: `Added ${display}.` + (f.show ? " It's showing in the table." : ""), undoText: `${display} is no longer listed.` });
      } else {
        const name = f.name.trim().replace(/\s+/g, " "), inside = f.projectFolder.trim() || null;
        let id = f.id;
        if (!id) {
          const used = new Set(this.trackAgents.map((a) => a.id));
          const base = "custom-" + trackSlug(name);
          id = base; for (let i = 2; used.has(id); i++) id = base.slice(0, 60) + "-" + i;
        }
        ok = await this.saveTracking((doc) => {
          const entry = { id, name, folder: display, project_folder: inside };
          const at = doc.custom_agents.findIndex((c) => c.id === id);
          if (at >= 0) doc.custom_agents.splice(at, 1, entry); else doc.custom_agents.push(entry);
          doc.agents.tracked = [...new Set([...doc.agents.tracked, id])];
        }, f.id ? { rowId: "_form", message: `Saved ${name}.`, undoText: `${name}'s earlier settings are back.` }
                : { rowId: "_form", message: `Added ${name}. Its column is at the end of the table.`, undoText: `${name} was removed. Its folder is unchanged.` });
      }
      if (this.trackForm !== f) return;
      f.saving = false;
      if (ok) { this.trackForm = null; Router.go("#/settings/tracking"); }
      else f.error = this.trackingNotes._form || "Couldn't save. Try again.";
    },
  },
};

const TABLE_WORDS = {
  on: "On", off: "Off", settings: "Off in settings", missing: "Not here", different: "Different",
  unreadable: "Can't read", "version-1": "Version 1", "version-2": "Version 2",
  unknown: "Unknown", working: "Working…",
};
const tableKey = (name, id) => name + ":" + id;
const columnScopes = (column) => column.scopes || [column.id];
const oneColumnCopy = (row, column) => {
  const matches = row.squareCopies.filter((copy) => columnScopes(column).includes(copy.scope));
  return matches.length === 1 ? matches[0] : null;
};
const tableWritable = (copy) => copy && !copy.readOnly && !copy.record.read_only &&
  copy.record.addressable !== false && copy.state !== "link" && validName(copy.name);
const tableSource = (copy) => tableWritable(copy) && copy.state !== "broken" && !!copy.hash;
const copyFileState = (copy) => copy.record.disabled ? "off" : "on";
const changesFileState = (source, target) => !target || copyFileState(source) !== copyFileState(target);
const replacementEffect = (source, targets) => {
  const changed = targets.filter((target) => changesFileState(source, target));
  return changed.length ? ` The skill file will be switched ${copyFileState(source)} in ${join(changed.map((target) => target.label))}.` : "";
};
const sharedColumn = (agent) => agent.id === "agents";
const tableAddressable = (row, agent) =>
  agent.writable && columnScopes(agent).length === 1 &&
  row.squareCopies.filter((copy) => columnScopes(agent).includes(copy.scope)).length <= 1;

function tableChoice(row, agent, columns) {
  const status = Model.squareStatus(row, agent);
  const copy = oneColumnCopy(row, agent);
  const groups = Model.squareCamps(row, columns);
  const fallback = row.squareCopies.find((c) => c.scope === "global" && tableSource(c));
  const source = groups.length && (groups.length === 1 || groups[0].length > groups[1].length)
    ? groups[0].find(tableSource) : groups.length ? null : fallback;
  const writable = tableAddressable(row, agent);
  const toggle = writable && !sharedColumn(agent) && tableWritable(copy) && ["on", "off"].includes(status);
  const add = writable && status === "missing" && !!source;
  return { row, agent, status, copy, groups, source, writable, toggle, add };
}

function panelWords(selection) {
  const { status, agent, copy, source, toggle, add, writable } = selection;
  const { name } = agent;
  const result = { line: "", after: "", primary: "Open skill", what: "", key: "", afterStatus: null };
  if (toggle) {
    const on = status === "on";
    const copies = selection.row.squareCopies.map((item) => item === copy
      ? { ...item, state: on ? "off" : "on", record: { ...item.record, disabled: on } } : item);
    const after = Model.squareStatus({ ...selection.row, squareCopies: copies }, agent);
    return { line: on ? name + " can use this skill." : name + " skips this skill.",
      after: TABLE_WORDS[after], afterStatus: after,
      primary: (on ? "Turn off in " : "Turn on in ") + name, key: "Space",
      what: on ? "The file is renamed so the agent skips it. Nothing is deleted, and you can undo it."
        : "The file is renamed back so the agent can use it. You can undo it." };
  }
  if (add) {
    return { line: name + " doesn’t have this skill yet.", after: source.state === "off" ? "Off" : "On",
      afterStatus: source.state === "off" ? "off" : "on", primary: "Add to " + name, key: "Space",
      what: "A copy is made from " + source.label + " with its supporting files and on/off state. You can undo it." };
  }
  if (status === "settings") {
    const line = copy?.record.native_state?.consumer === "opencode"
      ? "The file is on, but an OpenCode permission rule denies this skill."
      : "The file is on, but " + name + "’s own settings switch this skill off.";
    return { ...result, line,
      after: "On", afterStatus: "on", primary: "Show the settings file", key: "Enter",
      what: "Jackfield never changes agent settings files. Remove the line that turns it off, then refresh." };
  }
  if (status === "different" && source && copy && writable && tableWritable(copy)) {
    return { ...result, line: name + " has its own version. The other places share one.",
      after: "Same copy", afterStatus: "on", primary: "Compare the two versions", key: "Enter",
      what: (copy.state === "off" ? "This copy is also switched off. " : "") +
        "You choose which version wins. Nothing changes until you confirm." };
  }
  if (status === "unreadable" && source && copy && writable && tableWritable(copy)) {
    return { ...result, line: "The file in " + name + " is damaged, so the agent may not load it.",
      after: "Readable", afterStatus: "on", primary: "Preview a replacement", key: "Enter",
      what: "The replacement comes from " + source.label + ". The damaged folder goes to Trash." };
  }
  const message = sharedColumn(agent) ? "The shared folder has no switch of its own."
    : !writable || (copy && !tableWritable(copy)) ? "This square can’t safely identify one writable folder."
    : status === "missing" ? "There is no single readable source to copy."
    : status === "unreadable" ? "This file could not be read."
    : "Open the skill to see the available copies.";
  return { ...result, line: message };
}

const tableMixin = {
  data() {
    return { tableMode: "", tableVersion: "", tableNarrow: false, tableStopAgent: "",
      tableFirstSeen: savedPreference("jackfield-first-table", ["yes", "no"], "no") === "yes" };
  },
  computed: {
    tableColumns() {
      if (!this.m) return [];
      return Model.tableAgents(this.m.agents).map((column) => ({
        ...column, kind: sharedColumn(column) ? "shared" : column.kind,
        count: columnScopes(column).reduce((sum, id) => sum + (this.m.info(id)?.mine.length || 0), 0),
        canStop: !!this.trackAgent(column.id)?.tracked && this.trackTrackedCount > 1,
      }));
    },
    tableProblems() { return Model.attentionItems(this.shelfSkills, this.tableColumns); },
    tableProblemNames() { return new Set(this.tableProblems.map((item) => item.name)); },
    tableAttentionDetail() {
      return this.tableProblems.slice(0, 3).map((item) => {
        if (item.type === "split") return `${item.name}: two versions`;
        return `${item.agent.name}: ${item.name} ${item.type === "unreadable" ? "can’t be read" : "differs"}`;
      }).join(" · ");
    },
    tableBatchLimit() { return TABLE_BATCH_LIMIT; },
    tableRows() {
      return this.shelfSkills.map((row) => ({
        name: row.name, description: row.description, category: row.category, tokens: row.tokens, places: row.tools.length,
        presentIn: row.tools.map((copy) => this.agentOf(copy.scope).name).join(" "),
        verdict: Model.rowVerdict(row, this.tableColumns), attention: this.tableProblemNames.has(row.name),
        cells: Object.fromEntries(this.tableColumns.map((agent) => {
          const key = tableKey(row.name, agent.id);
          const status = this.tableWorking.includes(key) ? "working" : Model.squareStatus(row, agent);
          const actionable = ["on", "off", "missing"].includes(status);
          return [agent.id, { status, label: TABLE_WORDS[status], actionable }];
        })),
      }));
    },
    tableSelected() {
      if (this.route.page === "skills" && this.route.view) return null;
      const value = this.route.selected || "";
      const index = value.lastIndexOf(":");
      if (index < 1) return null;
      const name = value.slice(0, index);
      if (this.route.page === "skill" && name !== this.route.name) return null;
      const row = this.m?.byName.get(name);
      const agent = this.tableColumns.find((column) => column.id === value.slice(index + 1));
      return row && agent ? tableChoice(row, agent, this.tableColumns) : null;
    },
    tableSelection() {
      return this.tableSelected ? { name: this.tableSelected.row.name, agent: this.tableSelected.agent.id } : null;
    },
    tableSheetOpen() { return this.tableNarrow && !!this.tablePanel; },
    tableCopiesToReplace() {
      const s = this.tableSelected;
      if (!s) return [];
      if (statusIsSplit(s.status)) {
        const chosen = s.groups[Number(this.tableVersion) - 1];
        return chosen ? s.groups.flat().filter((copy) => copy.hash !== chosen[0].hash) : [];
      }
      return this.tableVersion === "current" ? s.groups[0] || [] : s.copy ? [s.copy] : [];
    },
    tablePreviewSource() {
      const s = this.tableSelected;
      if (!s) return null;
      if (statusIsSplit(s.status)) return s.groups[Number(this.tableVersion) - 1]?.find(tableSource);
      return this.tableVersion === "current" ? s.copy : s.source;
    },
    tableComparisonCopies() {
      const s = this.tableSelected;
      if (!s) return [];
      if (this.tableMode === "split-compare" && statusIsSplit(s.status)) {
        return s.groups.map((group) => group.find((copy) => this.bodyFetchable(copy)) || group[0]);
      }
      if (this.tableMode === "preview" && s.source && s.copy && ["different", "unreadable"].includes(s.status)) {
        return s.status === "different" ? [s.source, s.copy] : [s.source];
      }
      return [];
    },
    tablePanel() {
      if (this.tableStopAgent) {
        const confirm = this.trackLeaving(this.tableStopAgent);
        if (confirm?.agent.tracked) return { state: "stop-tracking", skill: confirm.title, agent: confirm.agent.name,
          mark: Model.agentMark(confirm.agent.id, confirm.agent.name).mark, confirm,
          primaryDisabled: this.busy || this.trackLastAgent(confirm.agent) };
      }
      const s = this.tableSelected;
      if (!s) return null;
      const { row, agent, status, copy } = s, key = tableKey(row.name, agent.id);
      const panel = {
        agent: agent.name, mark: agent.mark, initials: agent.initials, skill: row.name,
        path: this.shortPath(copy?.path || agent.path), now: TABLE_WORDS[status], nowStatus: status,
        others: this.tableColumns.filter((other) => other.id !== agent.id).map((other) => ({
          ...other, path: "", status: Model.squareStatus(row, other),
        })),
        ...panelWords(s),
      };
      if (this.tableWorking.includes(key)) return { ...panel, state: "working", line: "Checking the changed files…" };
      if (this.tableError?.key === key) return { ...panel, state: "failed", ...this.tableError };
      return this.tableReviewPanel(panel, s);
    },
    tableNotices() {
      const result = [];
      if (this.diskChanges.length) result.push({ key: "disk", title: this.plural(this.diskChanges.length, "skill changed") +
        " on disk since this page loaded.", actions: [{ label: "Refresh", action: "refresh" }] });
      if (this.tracking?.file.state === "broken" && !this.trackBrokenSeen) result.push({
        key: "broken", title: "Your tracking settings couldn’t be read.", text: "Everything found is shown.",
        actions: [{ label: "Open What to track", action: "manage" }, { label: "Dismiss", action: "dismiss-broken" }],
      });
      if (this.trackShowing && this.trackShowing.status !== "ok") result.push({
        key: "project", title: this.trackShowing.path + " can’t be found",
        actions: [{ label: "Choose another", action: "manage" }, { label: "Remove", action: "remove-project", path: this.trackShowing.path }],
      });
      if (this.trackNewlyFound) result.push({
        key: "found", title: "Found " + this.trackNewlyFound.name + (this.trackNewlyFound.skill_count != null
          ? " (" + this.plural(this.trackNewlyFound.skill_count, "skill") + ")" : "") + ".", text: "Track it?",
        actions: [{ label: "Track", action: "track-found" }, { label: "Not now", action: "found-later" }],
      });
      return result;
    },
  },
  methods: {
    showTableFirst() {
      this.tableFirstSeen = true;
      try { localStorage.setItem("jackfield-first-table", "yes"); } catch { /* storage can be disabled */ }
    },
    tableView(options) {
      const route = this.route;
      if (route.page !== "skills" && route.page !== "skill") return;
      const href = route.page === "skill"
        ? Router.skillHref(route.name, "", { ...this.readerRouteOptions(), sel: options.sel })
        : Router.routeHref("skills", options);
      if (href === route.href) return;
      if (this.route.selected !== (options.sel || null)) {
        this.tableMode = ""; this.tableVersion = ""; this.tableError = null;
      }
      Router.replace(href);
      this.route = Router.parseRoute(href);
    },
    tableSelect(selection) {
      this.tableStopAgent = "";
      this.tableView({ ...this.tableRouteOptions(), sel: tableKey(selection.name, selection.agent) });
      if (selection.primary && (this.tableSelected?.toggle || this.tableSelected?.add)) this.tablePrimary();
    },
    tableRouteOptions() { const r = this.route; return { q: r.search, agent: r.agent, only: r.only, sel: r.selected }; },
    tableClose() {
      this.tableStopAgent = "";
      if (this.route.page === "skills" && this.tableSelected && !this.tableFirstSeen) this.showTableFirst();
      this.tableView({ ...this.tableRouteOptions(), sel: null });
    },
    tableReviewPanel(panel, s) {
      if (this.tableMode === "preview" && s.source && s.copy && ["different", "unreadable"].includes(s.status)) {
        const targets = this.tableCopiesToReplace, source = this.tablePreviewSource;
        const compare = s.status === "different";
        const required = this.tableComparisonCopies;
        const read = required.filter((copy) => this.bodyReady(copy))
          .map((copy) => ({ id: copy.scope, name: copy.label, text: this.bodyOf(copy) }));
        const comparisonPending = read.length < required.length;
        const comparisonFailure = required.some((copy) => this.bodyErrorOf(copy));
        return { ...panel, state: "preview", comparison: read, versionChoices: compare ? [
          { id: "reference", label: "Keep " + s.source.label + "’s version" },
          { id: "current", label: "Keep " + s.agent.name + "’s version" },
        ] : [], selectedVersion: this.tableVersion,
        preview: comparisonFailure ? "The instructions couldn’t be read. Go back and try again."
          : comparisonPending ? (compare ? "Reading the two versions…" : "Reading the replacement…")
          : targets.length && (!compare || this.tableVersion) ? "Replace copies in " + join(targets.map((copy) => copy.label)) +
          ". The current folders go to Trash." + replacementEffect(source, targets) : "Choose the version to keep.",
        primary: compare ? "Make copies match" : "Replace this copy",
        primaryDisabled: this.busy || comparisonPending || (compare && !this.tableVersion) || !source || !targets.length || !this.canReplaceTableCopies(targets) };
      }
      if (statusIsSplit(s.status)) {
        const comparison = this.tableComparisonCopies.map((copy, index) => ({
          id: String(index + 1), name: "Version " + (index + 1), text: this.bodyOf(copy),
          ready: this.bodyReady(copy), failed: !this.bodyFetchable(copy) || !!this.bodyErrorOf(copy),
        }));
        const targets = this.tableCopiesToReplace, source = this.tablePreviewSource;
        return { ...panel, state: "split", line: "This skill has two versions. Pick the one to keep.",
          primary: "Make all " + s.groups.flat().length + " match", selectedCamp: this.tableVersion || null,
          camps: s.groups.map((group, i) => ({ id: String(i + 1), title: "Version " + (i + 1),
            detail: join(group.map((copy) => copy.label + (copyFileState(copy) === "off" ? " (off)" : ""))),
            facts: this.plural(group.length, "copy", "copies"), action: "Keep version " + (i + 1) })),
          comparison, preview: targets.length ? join(targets.map((copy) => copy.label)) +
            " will get this version. Their current folders go to Trash." + (source ? replacementEffect(source, targets) : "") : "",
          primaryDisabled: this.busy || !source || comparison.some((version) => !version.ready) || !this.canReplaceTableCopies(targets) };
      }
      if (s.status === "unknown") {
        return { ...panel, state: "unknown", line: "The last steps can’t be confirmed.", checks: [
          { label: "Folder entry exists", status: s.copy ? "on" : "unknown", detail: s.copy ? "Found" : "Unknown" },
          { label: "Document can be read", status: s.copy?.hash ? "on" : "unknown", detail: s.copy?.hash ? "Readable" : "Unknown" },
          { label: "Agent’s settings allow it", status: "unknown", detail: "Unknown" },
          { label: "Actually loaded", status: "unknown", detail: "Unknown" },
        ], what: "Check the skill and the agent’s settings, then look again." };
      }
      if (s.status === "on" && ["cursor", "custom"].some((prefix) => s.agent.id.startsWith(prefix))) {
        panel.what += " " + s.agent.name + "’s own settings aren’t checked.";
      }
      return { ...panel, primaryDisabled: this.busy };
    },
    canReplaceTableCopies(copies) {
      return copies.length > 0 && copies.every((copy) => {
        const row = this.m.byName.get(copy.name), agent = this.m.agent(copy.scope);
        return tableWritable(copy) && agent?.writable && row.squareCopies.filter((c) => c.scope === copy.scope).length === 1;
      });
    },
    tablePrimary() {
      const s = this.tableSelected;
      if (!s || this.busy) return;
      if (this.tableError?.key === tableKey(s.row.name, s.agent.id)) {
        const verify = this.tableError.verify;
        this.tableError = null;
        if (verify) { this.refresh({ showChanges: true }); return; }
        if (statusIsSplit(s.status)) return;
      }
      if (s.toggle) {
        this.change("toggle", { copy: s.copy, enable: s.status === "off", keys: [tableKey(s.row.name, s.agent.id)],
          message: s.row.name + (s.status === "off" ? " turned on in " : " turned off in ") + s.agent.name + "." });
      } else if (s.add) {
        this.change("copy", { sources: [s.source], scopes: columnScopes(s.agent), originals: [],
          keys: [tableKey(s.row.name, s.agent.id)], message: s.row.name + " added to " + s.agent.name + "." });
      } else if (["different", "unreadable"].includes(s.status) && s.source && s.copy && s.writable && tableWritable(s.copy)) {
        this.tableMode = "preview";
        this.tableVersion = s.status === "unreadable" ? "reference" : "";
        this.ensureBodies(this.tableComparisonCopies);
      } else this.tableOpenSkill(s.status === "settings" ? "why" : "");
    },
    tableChooseCamp(id) {
      this.tableVersion = id;
    },
    tableCompareSplit() {
      const s = this.tableSelected;
      if (!s || !statusIsSplit(s.status)) return;
      this.tableMode = "split-compare";
      this.ensureBodies(this.tableComparisonCopies);
    },
    tableConfirm() {
      const s = this.tableSelected, source = this.tablePreviewSource, originals = this.tableCopiesToReplace;
      if (!s || !source || !this.canReplaceTableCopies(originals) || this.busy) return;
      if (this.tablePanel?.primaryDisabled) return;
      const scopes = originals.map((copy) => copy.scope);
      this.tableMode = ""; this.tableVersion = "";
      this.change("copy", { sources: [source], scopes, originals,
        keys: [tableKey(s.row.name, s.agent.id), ...scopes.map((id) => tableKey(s.row.name, id))],
        message: s.row.name + " now matches in " + join(originals.map((copy) => copy.label)) + "." });
    },
    tableOpenSkill(screen = "") {
      const s = this.tableSelected;
      if (!s) return;
      if (!screen && this.route.page === "skill") this.closeReaderSquare();
      else Router.go(Router.skillHref(s.row.name, screen, this.route.page === "skill" ? this.readerRouteOptions() : {}));
    },
    tableOpenNamed(name) { if (name) Router.go(Router.skillHref(name)); },
    tableCancelPreview() { this.tableMode = ""; this.tableVersion = ""; },
    tableFolder() {
      const s = this.tableSelected;
      if (!s) return;
      const folder = s.copy?.path || this.scopes.find((scope) => scope.id === s.agent.id)?.path;
      if (!folder) return;
      const copied = navigator.clipboard?.writeText(folder);
      if (copied) copied.then(() => this.toast("Folder path copied."),
        () => this.toast("Select and copy the displayed folder path.", { err: true }));
    },
    tableTracking({ action, id, path }) {
      if (action === "refresh") this.refresh({ showChanges: true });
      else if (action === "dismiss-broken") this.trackBrokenSeen = true;
      else if (action === "remove-project") this.trackRemoveProject(path);
      else if (action === "track-found") this.trackFoundTrack(this.trackNewlyFound);
      else if (action === "found-later") this.trackFoundLater(this.trackNewlyFound);
      else if (action === "stop") {
        this.tableClose();
        this.tableStopAgent = id;
      }
      else if (action === "details") this.trackDetails(id);
      else if (action === "show-project") this.trackShow(path || null);
      else Router.go("#/settings/tracking");
    },
    async tableConfirmStop() {
      const agent = this.trackAgent(this.tableStopAgent);
      if (!agent?.tracked || this.trackLastAgent(agent) || this.busy) return;
      if (await this.stopTracking(agent.id) && this.tableStopAgent === agent.id) this.tableClose();
    },
    tableBatch({ names, agent: id }) {
      const agent = this.tableColumns.find((column) => column.id === id);
      if (!agent || !agent.writable || columnScopes(agent).length !== 1 || this.busy) return;
      if (names.length > TABLE_BATCH_LIMIT) return;
      const choices = names.map((name) => this.m.byName.get(name)).filter(Boolean)
        .map((row) => tableChoice(row, agent, this.tableColumns))
        .filter((s) => s.source && s.writable && s.source.scope !== id &&
          (s.status === "missing" || (["different", "unreadable"].includes(s.status) && tableWritable(s.copy))));
      if (!choices.length) { this.toast("Choose rows with a missing or different copy in " + agent.name + ".", { err: true }); return; }
      const originals = choices.map((s) => s.copy).filter(Boolean);
      const effects = choices.filter((choice) => changesFileState(choice.source, choice.copy));
      this.openDialog({ title: "Make these match in " + agent.name + "?", names: choices.map((choice) =>
        choice.row.name + (changesFileState(choice.source, choice.copy) ? " — skill file will be " + copyFileState(choice.source) : "")),
        namesLabel: "See all " + choices.length + " skills", confirm: "Make these match",
        lines: [choices.length + " copies will match their reference versions. Existing folders go to Trash.",
          ...(effects.length ? ["The list shows the on/off state for " + this.plural(effects.length, "new or changed skill file") + "."] : []),
          ...(choices.length < names.length ? ["Only rows with an eligible reference and destination are included."] : [])],
        onConfirm: () => this.change("copy", { sources: choices.map((s) => s.source), originals, scopes: columnScopes(agent),
          keys: choices.map((s) => tableKey(s.row.name, id)), message: this.plural(choices.length, "copy", "copies") + " changed in " + agent.name + "." }) });
    },
  },
};
const statusIsSplit = (status) => status === "version-1" || status === "version-2";
const LAST_LIBRARY_DOWNLOAD = "jackfield-last-library-backup";

function savedLibraryDownload() {
  try {
    const record = JSON.parse(localStorage.getItem(LAST_LIBRARY_DOWNLOAD));
    if (Number.isFinite(record?.at) && record.at > 0 && Number.isFinite(new Date(record.at).getTime()) &&
        Number.isFinite(record.size) && record.size > 0) return record;
  } catch { /* Storage can be blocked or contain an obsolete value. */ }
  return null;
}

const trashKey = (scope, path) => JSON.stringify([scope, path]);

function historyLabel(entry) {
  const labels = { create: "Created", add: "Added", edit: "Edited", import: "Loaded",
    trash: "Moved to Trash", restore: "Restored", enable: "Turned on", disable: "Turned off",
    purge: "Deleted permanently" };
  if (entry.action.startsWith("restore --snapshot")) return "Restored a saved version of " + entry.name;
  return Object.hasOwn(labels, entry.action) ? labels[entry.action] + " · " + entry.name : "";
}

function attentionTitle(item) {
  if (item.type === "split") return item.name + " has two versions, evenly split";
  if (item.type === "unreadable") return item.agent.name + " can’t read its copy of " + item.name;
  return item.agent.name + " has a different copy of " + item.name;
}

function attentionOption(id, label, fixLabel, source, targets) {
  return { id, label, fixLabel, source, targets };
}

const attentionMixin = {
  data() {
    return { attentionSkipped: [], attentionFixed: [], attentionChoice: null, attentionCompare: "", attentionError: "" };
  },
  computed: {
    attentionItems() {
      return [...this.tableProblems].sort((a, b) => Number(b.type === "unreadable") - Number(a.type === "unreadable"));
    },
    attentionToFix() {
      const skipped = new Set(this.attentionSkipped);
      return this.attentionItems.filter((item) => !skipped.has(item.id));
    },
    attentionGroups() {
      const skippedIds = new Set(this.attentionSkipped);
      const skipped = this.attentionItems.filter((item) => skippedIds.has(item.id));
      const active = new Set(this.tableProblems.map((item) => item.id));
      const fixed = this.attentionFixed.filter((item) => !active.has(item.id));
      return [["To fix", this.attentionToFix], ["Skipped", skipped], ["Fixed", fixed]]
        .filter(([title, items]) => items.length || (title === "To fix" && skipped.length))
        .map(([title, items]) => ({ title: title + " · " + items.length, items: items.map((item) => ({
          id: item.id, name: item.name, agent: item.agent && { ...item.agent, path: "" },
          status: title === "Fixed" ? "on" : item.type === "split" ? "version-1" : item.type,
          label: title === "Fixed" ? "Fixed" : item.type === "split" ? "Two versions" : "",
        })) }));
    },
    attentionItem() {
      const id = this.route.item;
      const live = this.tableProblems.find((item) => item.id === id);
      if (live) return live;
      const historic = this.attentionFixed.find((item) => item.id === id);
      if (historic) return historic;
      const legacy = /^(warn|bad):(.+)$/.exec(id || "");
      if (legacy) {
        const item = this.tableProblems.find((item) => item.name === legacy[2] &&
          (legacy[1] === "bad" ? item.type === "unreadable" : item.type !== "unreadable"));
        if (item) return item;
      }
      return this.attentionToFix[0] || this.attentionItems[0] || null;
    },
    attentionItemIsFixed() {
      return !!this.attentionItem && this.attentionFixed.some(({ id }) => id === this.attentionItem.id) &&
        !this.tableProblems.some((item) => item.id === this.attentionItem.id);
    },
    attentionOptions() {
      const item = this.attentionItem;
      if (!item || this.attentionItemIsFixed) return [];
      const usable = (option) => tableSource(option.source) && this.canReplaceTableCopies(option.targets);
      const groups = Model.squareCamps(item.row, this.tableColumns);
      if (item.type === "split") {
        return groups.map((group, index) => {
          const version = "Version " + (index + 1);
          return attentionOption(String(index + 1), version, "Keep " + version.toLowerCase(),
            group.find(tableSource), groups.filter((other) => other !== group).flat());
        }).filter(usable);
      }
      const { copy, source, writable } = tableChoice(item.row, item.agent, this.tableColumns);
      if (!writable || !tableWritable(copy) || copy.record.decode_error) return [];
      if (item.type === "unreadable") {
        return [attentionOption("readable", "", "Replace with the readable copy", source, [copy])].filter(usable);
      }
      const name = item.agent.name;
      return [
        attentionOption("shared", "The shared version", "Use the shared version in " + name, source, [copy]),
        attentionOption("current", name + "’s version", "Use " + name + "’s version everywhere", copy,
          groups.flat().filter((other) => other.hash !== copy.hash)),
      ].filter(usable);
    },
    attentionOption() {
      const item = this.attentionItem;
      if (item?.type === "unreadable") return this.attentionOptions[0];
      const chosen = this.attentionChoice;
      if (!chosen || chosen.issue !== item?.id) return null;
      return this.attentionOptions.find((option) => this.attentionOptionKey(option) === chosen.key) || null;
    },
    attentionPair() {
      const option = this.attentionOption;
      if (!option || this.attentionItem.type === "unreadable") return null;
      const target = option.targets.find((copy) => copy.scope === this.attentionCompare) || option.targets[0];
      return [target, option.source];
    },
    attentionReads() {
      const sources = this.attentionOptions.map((option) => option.source);
      return this.attentionPair ? [...sources, this.attentionPair[0]] : sources;
    },
    attentionReadKey() {
      if (this.route.page !== "inbox") return "";
      return JSON.stringify([this.checkedAt, this.attentionReads.map((copy) => this.bodyKey(copy))]);
    },
    attentionChecked() {
      return this.checkedAt ? { skills: this.shelfSkills.length, places: this.tableColumns.length, at: this.checkedAt } : null;
    },
    attentionDetail() {
      const item = this.attentionItem;
      if (!item) return null;
      const fixed = this.attentionItemIsFixed;
      const option = this.attentionOption;
      const copy = item.agent && oneColumnCopy(item.row, item.agent);
      const agent = item.agent && { ...item.agent, path: "" };
      const options = this.attentionOptions.map(({ id, label, source, targets }) => ({
        id, label, sub: "Copies to replace in " + join(targets.map((target) => target.label)) + ".",
        snippet: this.bodyReady(source) ? stripFrontmatter(this.bodyOf(source)).trim().split("\n").slice(0, 3).join("\n") : "",
      }));
      const comparisons = this.attentionPair ? this.comparisonEvidence(this.attentionPair) : null;
      const canFix = !!option && (this.attentionPair || [option.source]).every((copy) => this.bodyReady(copy));
      const targets = (option?.targets || []).map((target) => ({ label: target.label, path: target.path }));
      const what = option ? "The current folders go to Trash. The replacement includes the supporting files." +
        replacementEffect(option.source, option.targets) : "Choose the version to keep. Jackfield moves the replaced folders to Trash.";
      const manual = fixed || options.length ? "" : copy?.record.decode_error
        ? "This file cannot be read as text. Open the skill for instructions to repair the file."
        : "Jackfield can’t safely identify the folders to replace. Open the skill to check the copies.";
      return { id: item.id, title: attentionTitle(item), status: fixed ? "on" : item.type,
        label: fixed ? "Fixed" : item.type === "split" ? "Two versions" : undefined,
        line: fixed ? "Jackfield checked the new copies." : this.attentionLine(item),
        agent, options: item.type === "unreadable" ? [] : options,
        selectedOption: option?.id, fixLabel: option?.fixLabel || "Choose a version first", what: manual || fixed ? "" : what,
        skillHref: Router.skillHref(item.name), fixed, skipped: this.attentionSkipped.includes(item.id),
        canFix, needsChoice: item.type !== "unreadable" && !option, manual, targets,
        readError: item.type === "unreadable" && option ? this.bodyErrorOf(option.source) : "",
        reading: item.type === "unreadable" && !!option && !this.bodyReady(option.source),
        comparePairs: this.attentionPair ? targets.map(({ label }, index) => ({ id: option.targets[index].scope, label })) : [],
        compareTarget: this.attentionPair?.[0].scope, comparisonEvidence: comparisons,
      };
    },
  },
  methods: {
    attentionOptionKey(option) {
      const evidence = (copy) => [this.bodyKey(copy), copyFileState(copy)];
      return JSON.stringify([option.id, evidence(option.source), option.targets.map(evidence)]);
    },
    attentionLine(item) {
      if (item.type === "split") return "Choose which version the tracked places should use.";
      if (item.type === "unreadable") return "The file in " + item.agent.name + " is damaged, so the agent may not load this skill.";
      return item.agent.name + " has its own version. Other places share a different copy.";
    },
    attentionSelect(id) {
      const href = Router.routeHref("attention", { item: id });
      Router.replace(href);
      this.route = Router.parseRoute(href);
      this.clearAttentionReview();
      this.$nextTick(() => (document.getElementById("attention-detail-heading") || document.getElementById("h1"))?.focus());
    },
    clearAttentionReview() {
      this.attentionChoice = null;
      this.attentionCompare = "";
      this.attentionError = "";
    },
    attentionChoose(id) {
      const option = this.attentionOptions.find((row) => row.id === id);
      if (!option || this.busy) return;
      this.attentionCompare = "";
      this.attentionChoice = { issue: this.attentionItem.id, key: this.attentionOptionKey(option) };
    },
    attentionMove(step) {
      const items = this.attentionGroups.flatMap((group) => group.items);
      const index = items.findIndex((item) => item.id === this.attentionItem?.id);
      const next = items[index + step];
      if (next) this.attentionSelect(next.id);
    },
    attentionSkip() {
      const item = this.attentionItem;
      if (!item || this.busy || this.attentionItemIsFixed || this.attentionSkipped.includes(item.id)) return;
      this.attentionSkipped = [...this.attentionSkipped, item.id];
      this.attentionSelect(this.attentionToFix[0]?.id || item.id);
    },
    attentionRecheck() {
      this.attentionError = "";
      return this.refresh();
    },
    attentionFix() {
      const item = this.attentionItem, option = this.attentionOption;
      if (!item || !option || this.busy || this.loading || this.loadError || !this.attentionDetail.canFix) return;
      const originals = option.targets;
      const issueIds = this.tableProblems.filter(({ name, id, agent }) =>
        name === item.name && (id === item.id || originals.some((copy) => agent && columnScopes(agent).includes(copy.scope))));
      const skipped = this.attentionSkipped;
      const selection = this.route.item;
      const visit = this.screenVisit;
      this.attentionError = "";
      return this.change("copy", { sources: [option.source], scopes: originals.map((copy) => copy.scope), originals,
        keys: originals.map((copy) => tableKey(copy.name, copy.scope)), message: "Fixed " + item.name + ".",
        onVerified: () => {
          const resolved = issueIds.filter((issue) => !this.tableProblems.some((live) => live.id === issue.id));
          const nowFixed = new Set(resolved.map(({ id }) => id));
          this.attentionFixed = [...this.attentionFixed.filter((row) => !nowFixed.has(row.id)), ...resolved];
          this.attentionSkipped = this.attentionSkipped.filter((id) => !nowFixed.has(id));
          if (visit === this.screenVisit && this.route.item === selection && nowFixed.has(item.id)) {
            this.attentionSelect(this.attentionToFix[0]?.id || this.attentionItems[0]?.id || null);
          }
          if (!nowFixed.has(item.id)) return "Copies changed. Check the remaining issues.";
        },
        onUndo: () => {
          const live = new Set(this.tableProblems.map(({ id }) => id));
          this.attentionFixed = this.attentionFixed.filter(({ id }) => !live.has(id));
          this.attentionSkipped = [...new Set([...this.attentionSkipped, ...skipped.filter((id) => live.has(id))])];
          if (visit === this.screenVisit && live.has(item.id)) this.attentionSelect(item.id);
        },
        onError: (failure) => {
          if (this.route.page !== "inbox") return false;
          this.attentionError = failure;
          return true;
        },
      });
    },
  },
};

const app = createApp({
  data() {
    return { ...Jack.createState(), ...trackingMixin.data(), ...tableMixin.data(), ...attentionMixin.data(), historyGen: 0, catalogGen: 0, trashGen: 0, agentTrashGen: 0,
      route: Router.current(), routeAction: "", catalog: {tags:{}, profiles:{}}, catalogError: "", tagFilter: "", libraryView: savedPreference("skillsmgr-v2-library-view",["shelf","instances"],"shelf"), density: savedPreference("skillsmgr-v2-density",["comfortable","compact"],"comfortable"), toolTarget: null, sourceReviewHandoff: null, readCopyPath: "", readCopyScope: "", readCopyName: "",
      skillHistoryError: "", trashError: "", trashLoading: false, importFull: false, importResult: null, createTemplates: [], commandQuery: "", commandActive: 0,
      exportPending: false, exportError: "", libraryDownload: savedLibraryDownload(),
      query: "", filter: "all", agentFilter: "all", extra: {}, sortBy: "name", advancedQuery: "",
      bodies: {}, bodyInflight: {}, bodyErrors: {},
      treeQuery: "", edit: null, highlight: true, compareWith: "", leadOpen: false,
      mapSelId: "", mapPicked: [], peek: null,
      mapQuery: "", mapReviewOnly: false, mapPage: 0, mapSkillName: "", mapOrigin: null,
      trash: [], agentTrash: [], agentTrashErrors: [], agentTrashLoading: false, restoredTrash: null,
      importFile: null, importReject: "", importError: "", importForce: false, importPlan: null, importPending: false,
      theme: savedPreference("skillsmgr-theme",THEMES,"system"),formatLocale:savedPreference("skillsmgr-locale",["system","en-US","en-GB","en-IN"],"system"),
      dialog: null, skillHistory: [], opener: null,
      readerResult: null, readerGeneration: 0,
      readerSnapshots: [], readerSnapshotsError: "", readerSnapshotsGeneration: 0,
    };
  },
  computed: {
    ...trackingMixin.computed,
    ...tableMixin.computed,
    ...attentionMixin.computed,
    mergedTrash() {
      const library = this.trash.map((row) => ({ ...row, scope: "global", scopeLabel: "Your library", canRestore: true }));
      const rows = [...library, ...this.agentTrash];
      const counts = new Map(), positions = new Map();
      const key = (row) => trashKey(row.scope, row.name);
      const observedDate = (row) => row.trashed_at || row.modified;
      rows.sort((a, b) => String(observedDate(b) || "").localeCompare(String(observedDate(a) || "")) ||
        a.name.localeCompare(b.name) || a.scope.localeCompare(b.scope));
      for (const row of rows) counts.set(key(row), (counts.get(key(row)) || 0) + 1);
      return rows.map((row) => {
        const position = (positions.get(key(row)) || 0) + 1;
        positions.set(key(row), position);
        const count = counts.get(key(row));
        const copyLabel = count > 1 ? `copy ${position} of ${count}` : "";
        return { ...row, copyLabel, id: trashKey(row.scope, row.trash_path),
          agent: { ...Model.agentMark(row.scope, row.scopeLabel), name: row.scopeLabel },
          detail: [copyLabel, row.size_bytes > 0 ? this.fmtSize(row.size_bytes) : ""].filter(Boolean).join(" · "),
          when: row.trashed_at ? this.fmtDate(row.trashed_at) : row.modified ? "Last changed " + this.fmtDate(row.modified) : "",
          restoreLabel: this.agentRestoreLabel({ ...row, copyLabel }),
        };
      });
    },
    mergedTrashErrors() {
      const library = this.trashError ? [{ scope: "global", label: "Your library", message: this.trashError }] : [];
      return library.concat(this.agentTrashErrors.map((error) => ({ ...error, label: this.agentOf(error.scope).name })));
    },
    recoveryRecent() {
      const today = new Date(), yesterday = new Date(today);
      today.setHours(0, 0, 0, 0);
      yesterday.setDate(today.getDate() - 1);
      yesterday.setHours(0, 0, 0, 0);
      return this.history.flatMap((entry, index) => {
        const date = new Date(entry.at);
        if (!Number.isFinite(date.getTime()) || date < yesterday || typeof entry.action !== "string") return [];
        const text = historyLabel(entry);
        return text ? [{ id: entry.id || index, text, when: date >= today ? "Today" : "Yesterday" }] : [];
      });
    },
    recoveryLastDownload() {
      return this.libraryDownload ? "Last download started " + this.fmtDate(this.libraryDownload.at) +
        " · " + this.fmtSize(this.libraryDownload.size) : "";
    },
    recoveryImportResult() {
      const result = this.importResult;
      return result ? { summary: this.archiveImportSummary(result),
        reasons: [...(result.skipped || []), ...(result.skipped_full || [])] } : null;
    },
    tableHero() { return this.route.page === "skills" && !this.route.view; },
    activePlace() {
      return { inbox: "#/attention", recovery: "#/trash", tools: "#/advanced", tracking: "#/advanced" }[this.route.page]
        || (this.route.page === "missing" ? "" : "#/skills");
    },
    missingSuggestion() {
      return this.route.page === "skill" && !this.skill ? Jack.palette.closeName(this.route.name, this.shelfSkills) : null;
    },
    paletteSuggestion() {
      return this.commandGroups.length ? null : Jack.palette.closeName(this.commandQuery, this.shelfSkills);
    },
    agentInfos() { return this.m ? this.m.infos.filter((i) => !i.agent.library) : []; },
    shelfSkills() { return this.m?.skills.filter((s) => s.status.key !== "note") || []; },
    sharedSkills() { return this.shelfSkills.filter((s) => s.tools.length > 1).sort((a, b) => b.tools.length - a.tools.length || a.name.localeCompare(b.name)).slice(0, 3); },
    /* Categories only help when the skills actually carry them; otherwise the
     * shelf falls back to an alphabet, which is what people can scan. */
    grouping() { return this.m && new Set(this.m.skills.map((s) => s.category).filter(Boolean)).size > 1 ? "category" : "letter"; },
    filterChoices() {
      const sk = this.m ? this.m.skills : [];
      return [
        { id: "all", label: "All", n: sk.filter((s) => s.status.key !== "note").length },
        { id: "care", label: "Needs care", n: this.careCount },
        { id: "off", label: "Turned off", n: this.shelfSkills.filter((s) => Model.hasOffCopy(s, this.agentFilter)).length },
      ];
    },
    shelfTotal() { return this.shelfSkills.length; },
    careCount() { return this.m ? this.m.skills.filter((s) => s.status.key === "warn" || s.status.key === "bad").length : 0; },
    catalogTags() { return [...new Set(Object.values(this.catalog.tags || {}).flat())].sort(); },
    visibleNames() { return this.visible.map(s => s.name); },
    commandGroups() {
      if (!this.dialog?.commands) return [];
      return Jack.palette.search(this.commandQuery, this.shelfSkills,
        (scope) => this.agentOf(scope).name, toolItems, (id) => toolEnabled(this.toolGroupsOn, id));
    },
    commandChoices() { return this.commandGroups.flatMap((group) => group.items); },
    visible() {
      const words = Jack.palette.wordsOf(this.query);
      return this.shelfSkills.filter((s) => {
        const k = s.status.key;
        if (this.filter === "care" && k !== "warn" && k !== "bad") return false;
        if (this.filter === "off" && !Model.hasOffCopy(s, this.agentFilter)) return false;
        if (this.agentFilter !== "all" && !s.copies.some((c) => c.scope === this.agentFilter)) return false;
        const tags = (this.catalog.tags || {})[s.name] || [];
        if (this.tagFilter === "__untagged" && tags.length) return false;
        if (this.tagFilter && this.tagFilter !== "__untagged" && !tags.includes(this.tagFilter)) return false;
        return !words.length || Jack.palette.matchesSkill(s, words, (scope) => this.agentOf(scope).name);
      });
    },
    groups() {
      if (this.sortBy !== "name") {
        const key = this.sortBy === "size" ? (s) => -s.tokens : (s) => -s.tools.length;
        const items = [...this.visible].sort((a, b) => key(a) - key(b) || a.name.localeCompare(b.name));
        const id = this.sortBy === "size" ? "Largest first" : "In the most tools";
        return items.length ? [{ id, key: "sorted", items, shown: items.slice(0, CAP + (this.extra[id] || 0)) }] : [];
      }
      const by = new Map();
      for (const s of this.visible) {
        const id = this.grouping === "category" ? (s.category || "Other") : (/[a-z]/i.test(s.name[0]) ? s.name[0].toUpperCase() : "#");
        if (!by.has(id)) by.set(id, []);
        by.get(id).push(s);
      }
      return [...by.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([id, items]) => ({
        id, key: id.replace(/\W/g, "") || "other", items, shown: items.slice(0, CAP + (this.extra[id] || 0)),
      }));
    },
    /* A description longer than about four reader lines is folded so the
     * document itself starts above the fold on a 768px-tall laptop. */
    leadLong() { return (this.refCopy?.description || this.skill?.description || "").length > 360; },
    skill() { return this.m && this.route.page === "skill" ? this.m.byName.get(this.route.name) || null : null; },
    treeAll() {
      const q = this.treeQuery.trim().toLowerCase();
      return q ? this.shelfSkills.filter((s) => s.name.toLowerCase().includes(q)) : this.shelfSkills;
    },
    treeList() {
      const list = this.treeAll.slice(0, 200);
      if (this.skill && this.skill.status.key !== "note" && !list.includes(this.skill) && !this.treeQuery) list.unshift(this.skill);
      return list;
    },
    treeHidden() { return Math.max(0, this.treeAll.length - 200); },
    readerCompareCopies() {
      const hash = this.refCopy?.hash;
      return hash ? this.skill.copies.filter((copy) => copy.hash && copy.hash !== hash) : [];
    },
    cmp() {
      return this.readerCompareCopies.find((c) => this.bodyKey(c) === this.compareWith) || this.readerCompareCopies[0] || null;
    },
    refCopy() {
      const s = this.skill;
      if (!s) return null;
      const { copyScope, copyPath } = this.route;
      if (copyScope && copyPath) {
        return s.copies.find((copy) => copy.scope === copyScope && copy.path === copyPath) || null;
      }
      if (this.readCopyName === s.name && this.readCopyScope) {
        return s.copies.find(c => c.scope === this.readCopyScope && c.path === this.readCopyPath) || null;
      }
      return s.ref.holders[0] || s.primary;
    },
    readerPlaces() {
      if (!this.skill) return [];
      return this.tableColumns.map((agent) => {
        const key = tableKey(this.skill.name, agent.id);
        const status = this.tableWorking.includes(key) ? "working" : Model.squareStatus(this.skill, agent, null, this.tableColumns);
        return { ...agent, path: this.shortPath(agent.path), status, label: TABLE_WORDS[status], selected: this.route.selected === key };
      });
    },
    readerVerdict() { return this.skill ? Model.rowVerdict(this.skill, this.tableColumns) : ""; },
    readerNativeCopies() { return this.skill?.copies.filter((copy) => copy.record.native_state) || []; },
    readerTrashCopies() {
      if (!this.skill) return [];
      const counts = new Map();
      for (const copy of this.skill.squareCopies) counts.set(copy.scope, (counts.get(copy.scope) || 0) + 1);
      return this.skill.copies.filter((copy) => tableWritable(copy) && this.agentOf(copy.scope).writable &&
        counts.get(copy.scope) === 1);
    },
    readerUniqueScope() {
      const c = this.refCopy;
      return !!c && this.skill.squareCopies.filter((copy) => copy.scope === c.scope).length === 1;
    },
    readerKey() {
      const copy = this.refCopy;
      return !this.route.screen && this.bodyFetchable(copy) && copy.path && copy.hash
        ? JSON.stringify([this.bodyKey(copy), copy.record.path, copy.record.disabled]) : "";
    },
    readerView() {
      return this.readerResult?.key === this.readerKey ? this.readerResult?.document : null;
    },
    readerError() {
      return this.readerResult?.key === this.readerKey ? this.readerResult?.error || "" : "";
    },
    readerFileName() {
      return this.readerView?.filename || (this.refCopy?.record.disabled ? "SKILL.md.disabled" : "SKILL.md");
    },
    readerSnapshotsKey() {
      const c = this.refCopy;
      return !this.route.screen && this.readerUniqueScope && this.bodyFetchable(c) && !c.readOnly
        ? this.bodyKey(c) : "";
    },
    docHtml() {
      const s = this.skill;
      if (!s) return "";
      const text = this.readerView?.body ?? stripFrontmatter(this.bodyOf(this.refCopy));
      let marks = new Set();
      if (this.cmp && this.highlight && this.bodyReady(this.cmp)) {
        const theirs = new Set(stripFrontmatter(this.bodyOf(this.cmp)).split("\n").map((l) => l.trim()));
        marks = new Set(text.split("\n").map((l) => l.trim()).filter((l) => l && !theirs.has(l)));
      }
      return renderDoc(text, marks);
    },
    /* A copy this tool never reads (a link it refuses to follow, or a folder
     * name it cannot address) is not "still loading": it is unreadable here,
     * and the reader says why instead of waiting forever. */
    docPending() {
      if (this.readerKey) return !this.readerView && !this.readerError;
      const copy = this.refCopy;
      return !!this.skill && this.bodyFetchable(copy) && !this.bodyReady(copy) && !this.bodyErrorOf(copy);
    },
    docWhy() {
      const c = this.refCopy;
      if (!c && (this.route.copyScope || (this.readCopyName === this.skill?.name && this.readCopyScope))) {
        return { title: "Selected copy is no longer listed", text: "Refresh files or choose another copy using Read copy.", missing: true };
      }
      if (!c || this.bodyFetchable(c)) return null;
      const why = BROKEN_WHY[c.kind];
      return why ? { title: why[0], text: why[1] } : { title: "Not readable here", text: "" };
    },
    docError() { return this.readerKey ? this.readerError : this.bodyErrorOf(this.refCopy); },
    editable() { return !!this.skill && this.skill.copies.some((c) => c.state !== "broken" && !c.readOnly); },
    canEdit() {
      return !!this.skill && this.editable && this.bodyFetchable(this.refCopy) && this.refCopy.state === "on" &&
        !this.refCopy.readOnly && this.readerUniqueScope;
    },
    editWhy() { const c = this.refCopy; if (c && c.readOnly) return this.readOnlyWhy(c); return this.docWhy ? `${this.docWhy.title}. ${this.docWhy.text}` : ""; },
    editTargets() { return this.readerTrashCopies.filter((copy) => copy.state === "on"); },
    editPlaces() {
      if (!this.skill) return new Map();
      const occupied = new Set(this.skill.squareCopies.map((copy) => copy.scope));
      const copies = new Map(this.editTargets.map((copy) => [copy.scope, copy]));
      const places = new Map();
      for (const { id: scope, path, physical_root, availability } of this.scopes) {
        const copy = copies.get(scope);
        const agent = this.m.agent(scope);
        if (!agent || (!copy && (!agent.writable || availability !== "writable" || occupied.has(scope)))) continue;
        const root = physical_root || path;
        const evidence = copy ? this.bodyKey(copy) : JSON.stringify([scope, root]);
        places.set(scope, { scope, copy, root, evidence, agent: { ...agent, path: this.shortPath(copy?.path || path) } });
      }
      return places;
    },
    editTargetChanged() {
      const draft = this.edit;
      if (!draft) return false;
      const source = this.editPlaces.get(draft.copy.scope)?.copy;
      const sourceChanged = !source || source.path !== draft.copy.path || source.hash !== draft.copy.hash;
      return draft.targets.some((scope) => this.editPlaceChanged(scope) ||
        (sourceChanged && !this.editPlaces.get(scope)?.copy));
    },
    editError() {
      if (!this.edit) return "";
      if (!this.edit.desc.trim()) return "Add a short description so agents know when to use this skill.";
      if (this.edit.desc.length > 1024) return "Keep the description under 1024 characters.";
      return "";
    },
    editDirty() { return !!this.edit && (this.edit.desc !== this.edit.baseDesc || this.edit.body !== this.edit.baseBody || JSON.stringify(this.edit.metadata)!==JSON.stringify(this.edit.baseMetadata)); },
    shareTargets() {
      if (!this.skill || !this.m || !this.readerUniqueScope || !tableSource(this.refCopy)) return [];
      const have = new Set(this.skill.copies.map((c) => c.scope));
      return this.m.agents.filter((a) => !a.library && a.writable && !have.has(a.id));
    },
    lengthPct() {
      const c = this.skill && this.skill.primary;
      const a = c && this.agentOf(c.scope);
      return a && a.limit ? Math.round((this.skill.tokens / a.limit) * 1000) / 10 : 0;
    },
    brokenText() { const b = this.skill && this.skill.broken[0]; return b ? (BROKEN_WHY[b.kind] || BROKEN_WHY.invalid)[1] : ""; },
    brokenAction() { const p = this.m && this.skill ? this.m.problems.find((x) => x.id === "bad:" + this.skill.name) : null; return p ? p.action : "Show me how"; },
    matchLabel() {
      const n = this.skill ? this.skill.differing.length : 0;
      return n === 1 ? `Make ${this.agentOf(this.skill.differing[0].scope).name}'s copy match` : `Make ${n} copies match`;
    },
    mapStates() { return MAP_STATES; },
    mapSkills() {
      if (!this.m) return [];
      const query = this.mapQuery.trim().toLowerCase();
      const scopes = new Set(this.agentInfos.map((inf) => inf.id));
      return this.m.skills.filter((s) => s.status.key !== "note" && s.name.toLowerCase().includes(query) &&
        (!this.mapReviewOnly || this.needsMapReview(s, scopes)));
    },
    mapPageIndex() { return Math.min(this.mapPage, Math.max(0, Math.ceil(this.mapSkills.length / CAP) - 1)); },
    mapStart() { return this.mapPageIndex * CAP; },
    mapEnd() { return Math.min(this.mapStart + CAP, this.mapSkills.length); },
    mapRows() {
      return this.mapSkills.slice(this.mapStart, this.mapEnd).map((skill) => ({
        skill, cells: this.agentInfos.map((inf) => this.mapCell(skill, inf.id)),
      }));
    },
    mapSel() {
      const infos = this.agentInfos;
      if (!infos.length) return null;
      return infos.find((i) => i.id === this.mapSelId) || infos.find((i) => i.key === "bad") || infos.find((i) => i.key === "warn") || infos[0];
    },
    mapSelected() {
      const inf = this.mapSel;
      return inf ? inf.differing.slice(0, 12).filter((s) =>
        this.mapPicked.includes(s.name) && this.mapSyncable(s, inf.id)) : [];
    },
    mapDetail() {
      const skill = this.mapSkillName && this.m && this.m.byName.get(this.mapSkillName);
      if (!skill || skill.status.key === "note" || !this.mapSel || this.mapSel.id !== this.mapSelId) return null;
      const cell = this.mapCell(skill, this.mapSel.id);
      return cell.state === "missing" ? null : { skill, ...cell };
    },
    mapComparePair() {
      const skill = this.mapSel?.differing.slice(0, 12).find((s) => s.name === this.peek);
      if (!skill || skill.ref.ambiguous) return null;
      const { copy } = this.mapCell(skill, this.mapSel.id);
      return copy && skill.ref.holders[0] ? [copy, skill.ref.holders[0]] : null;
    },
    mapComparisonEvidence() { return this.comparisonEvidence(this.mapComparePair); },
    queue() { return this.m?.problems || []; },
    themeLabel() { return { system: "follows your computer", light: "light", dark: "dark" }[this.theme]; },
    themeIcon() { return PATHS[{ system: "auto", light: "sun", dark: "moon" }[this.theme]]; },
    createTargets() {
      if (!this.m) return [];
      const targets = this.m.agents.filter((agent) => agent.writable);
      const library = this.scopes.find((scope) => scope.id === "global");
      if (library?.exists === false && library.writable !== false && library.availability !== "read-only") {
        targets.push({ ...Model.agentMark("global", "Your library"), id: "global",
          name: "Your library", library: true, path: library.path });
      }
      return targets;
    },
    formErrors() {
      const f = this.dialog && this.dialog.form;
      if (!f) return {};
      const e = {};
      const n = f.name.trim();
      if (n && !validName(n)) e.name = "Use lowercase letters, numbers and single hyphens, up to 64 characters.";
      else if (n && this.m && (this.m.byName.get(n) || { copies: [] }).copies.some((c) => c.scope === f.scope)) e.name = "A skill with this name already exists there.";
      if (f.desc.length > 1024) e.desc = "Keep the description under 1024 characters.";
      return e;
    },
    formInvalid() {
      const f = this.dialog && this.dialog.form;
      return !f || !f.name.trim() || !f.desc.trim() || !!this.formErrors.name || !!this.formErrors.desc;
    },
  },
  watch: {
    libraryView(value) {try{localStorage.setItem("skillsmgr-v2-library-view",value);}catch(e){}},
    density(value) {try{localStorage.setItem("skillsmgr-v2-density",value);}catch(e){}},
    attentionReadKey() { if (this.route.page === "inbox") this.ensureBodies(this.attentionReads); },
    "route.name"() { this.compareWith = ""; this.leadOpen = false; this.loadSkillHistory(); this.primeBodies(); },
    "route.page"(page) { if (page !== "map") this.mapOrigin = null; },
    readerKey() { this.loadReaderView(); },
    readerSnapshotsKey() { this.loadReaderSnapshots(); },
    skill(s) { if (!s && this.edit) this.edit = null; if (s) this.ensureBodies(s.copies); },
    mapQuery() { this.resetMapPage(); },
    mapReviewOnly() { this.resetMapPage(); },
  },
  methods: {
    ...Jack.stateActions,
    ...trackingMixin.methods,
    ...tableMixin.methods,
    ...attentionMixin.methods,
    enc: encodeURIComponent, agentMark: Model.agentMark, plural, join, words, titleCase, shortPath, renderDoc,
    fmt(n) {return Domain.numberFormatter(this.formatLocale==="system"?undefined:this.formatLocale).format(Number(n));},
    /* The informative end of a long folder path ("…/.claude/skills"); the full
     * path stays in the element's title. A leading ellipsis cut the useful part. */
    shortPath(path) {const text=String(path||"");const parts=text.split(/[\\/]/).filter(Boolean);return text.length<=28||parts.length<=2?text:"…/"+parts.slice(-2).join("/");},
    /* Sizes read in the unit a person would say: "12 KB", "3.9 MB". */
    fmtSize(bytes) {const n=Number(bytes)||0;if(n<1024*1024)return this.fmt(Math.max(1,Math.round(n/1024)))+" KB";return Domain.numberFormatter(this.formatLocale==="system"?undefined:this.formatLocale,{maximumFractionDigits:1}).format(n/1048576)+" MB";},
    fmtDate(value, timeStyle = "short") {const date=new Date(value);return Number.isNaN(date.getTime())?String(value||"Date unavailable"):Domain.dateFormatter(this.formatLocale==="system"?undefined:this.formatLocale,{dateStyle:"medium",timeStyle}).format(date);},
    preferencesChanged() {this.theme=savedPreference("skillsmgr-theme",THEMES,"system");this.formatLocale=savedPreference("skillsmgr-locale",["system","en-US","en-GB","en-IN"],"system");document.documentElement.dataset.textSize=savedPreference("skillsmgr-text-size",["standard","large"],"standard");this.applyTheme(); },
    skillTags(name) {return (this.catalog.tags || {})[name] || [];},
    openSource(record) { this.toolTarget=markRaw(record);Router.go(Router.toolHref("source-update")); },
    openSkillTool(tool) { if (this.refCopy) { this.toolTarget = markRaw(this.refCopy.record); Router.go(Router.toolHref(tool)); } },
    openConciseReview(handoff) { if(!handoff||!handoff.target||!handoff.reviewId)return;this.toolTarget=markRaw(handoff.target);this.sourceReviewHandoff={...handoff,target:this.toolTarget};Router.go(Router.toolHref("source-update")); },
    sourceReviewConsumed(reviewId) { if(this.sourceReviewHandoff&&this.sourceReviewHandoff.reviewId===reviewId)this.sourceReviewHandoff=null; },
    inspectRecord(record) { this.openRecord(record); },
    openRecord(record) {
      this.toolTarget = markRaw(record);
      const path = record.physical_path || record.path;
      Router.go(Router.skillHref(record.name, "", path ? { scope: record.scope, copy: path } : undefined));
    },
    goTo(href) { Router.go(href); },
    openCommands() {
      if (this.dialog || this.busy) return;
      this.commandQuery = ""; this.commandActive = 0;
      this.openDialog({ title: "Search skills, actions and pages", commands: true, cancel: "Close" });
    },
    commandInput(value) { this.commandQuery = value; this.commandActive = 0; },
    useCommandSuggestion(name) {
      this.commandInput(name);
      this.$nextTick(() => document.getElementById("command-q")?.focus());
    },
    commandKey(e) {
      const choices = this.commandChoices, length = choices.length;
      if (!length || e.isComposing) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        this.commandActive = (this.commandActive + (e.key === "ArrowDown" ? 1 : -1) + length) % length;
        this.$nextTick(() => document.getElementById("cmd-" + this.commandActive)?.scrollIntoView({ block: "nearest" }));
      } else if (e.key === "Enter") {
        e.preventDefault(); this.commandGo(choices[Math.min(this.commandActive, length - 1)]);
      }
    },
    commandGo(item) {
      if (!item || this.busy) return;
      this.closeDialog();
      if (item.action === "refresh") this.refresh();
      else if (item.action === "backup") this.exportBackup(false);
      else if (item.action === "theme") this.cycleTheme();
      else Router.go(item.path);
    },
    agentOf(id) { return (this.m && this.m.agent(id)) || { ...FALLBACK_AGENT, name: id || "Unknown" }; },
    readerCopyValue(copy) { return copy ? JSON.stringify([copy.scope, copy.path]) : ""; },
    readerRouteOptions() {
      const { file, copyScope, copyPath } = this.route;
      return { view: file ? "file" : "", scope: copyScope, copy: copyPath };
    },
    readerWhyHref() { return Router.skillHref(this.skill.name, "why", this.readerRouteOptions()); },
    readerHref() { return Router.skillHref(this.route.name, "", this.readerRouteOptions()); },
    chooseReaderCopy(value) {
      const chosen = this.skill.copies.find((copy) => this.readerCopyValue(copy) === value);
      if (!chosen) return;
      this.compareWith = "";
      this.leadOpen = false;
      const href = Router.skillHref(this.skill.name, "", { ...this.readerRouteOptions(), scope: chosen.scope,
        copy: chosen.path, sel: this.route.selected });
      Router.replace(href);
      this.route = Router.parseRoute(href);
    },
    showReaderFile(file) {
      const href = Router.skillHref(this.skill.name, "", { ...this.readerRouteOptions(), view: file ? "file" : "", sel: this.route.selected });
      Router.replace(href);
      this.route = Router.parseRoute(href);
    },
    closeReaderSquare() {
      const place = this.tableSelection?.agent;
      this.tableClose();
      this.$nextTick(() => {
        const opener = [...this.$refs.readerPlaces?.querySelectorAll("[data-place]") || []]
          .find((element) => element.dataset.place === place);
        opener?.querySelector("button")?.focus();
      });
    },

    async loadReaderView() {
      const gen = ++this.readerGeneration;
      const key = this.readerKey;
      this.readerResult = null;
      if (!key) return;
      const { name, scope, hash, path, record } = this.refCopy;
      const query = new URLSearchParams({ scope, view: "reader", target_path: record.path || path });
      try {
        const document = await api(`/api/skills/${encodeURIComponent(name)}?${query}`);
        if (document.path !== path || document.content_hash !== hash) {
          throw new Error("The file changed since it was checked. Refresh files and try again.");
        }
        if (gen === this.readerGeneration) this.readerResult = { key, document };
      } catch (error) {
        if (gen === this.readerGeneration) this.readerResult = { key, error: this.friendly(error.message) };
      }
    },
    async refreshReaderView() {
      const key = this.readerKey;
      await this.refresh();
      if (key && key === this.readerKey) await this.loadReaderView();
    },
    readerListingSpace(listing) {
      const percent = 100 * listing.entry_chars / listing.budget_chars;
      if (percent < 0.1) return "Less than 0.1% of the estimated skill list space.";
      return `About ${this.fmt(Number(percent.toFixed(1)))}% of the estimated skill list space.`;
    },

    async loadReaderSnapshots() {
      const gen = ++this.readerSnapshotsGeneration;
      this.readerSnapshots = [];
      this.readerSnapshotsError = "";
      if (!this.readerSnapshotsKey) return;
      const { name, scope } = this.refCopy;
      try {
        const snapshots = await this.snapshotIds(name, scope);
        if (gen === this.readerSnapshotsGeneration) this.readerSnapshots = snapshots;
      } catch (error) {
        if (gen === this.readerSnapshotsGeneration) this.readerSnapshotsError = this.friendly(error.message);
      }
    },

    /* ----- loading ----- */
    async loadSkillHistory() {
      const gen = ++this.historyGen;
      this.skillHistory = [];this.skillHistoryError="";
      if (this.route.page !== "skill" || this.route.screen) return;
      const name = this.route.name;
      try {
        const rows = await api("/api/history?limit=20&name=" + encodeURIComponent(name));
        if (gen === this.historyGen) this.skillHistory = (Array.isArray(rows) ? rows : []).slice(0, 3);
      } catch (e) { if (gen === this.historyGen) this.skillHistoryError=this.friendly(e.message); }
    },
    async loadCatalog() {
      const gen = ++this.catalogGen;
      try {
        const catalog = await api("/api/catalog");
        if (gen !== this.catalogGen) return;
        this.catalog = catalog; this.catalogError = "";
      } catch (e) { if (gen === this.catalogGen) this.catalogError = this.friendly(e.message); }
    },

    /* ----- documents (fetched only where a view needs one) -----
     * The list request omits document bodies; this fetches one lazily. The
     * cache key includes the observed content hash, so a changed document
     * always refetches, and two callers asking for the same copy share one
     * request. A body is never assumed loaded: `bodyLoaded` tells an empty
     * document from one that has not been read yet. */
    bodyKey(c) { return JSON.stringify([c?.scope, c?.name, c?.path, c?.hash]); },
    /* `key in` goes through the reactive proxy's tracked `has` trap;
     * Object.prototype.hasOwnProperty.call does not, so a computed that read
     * it never re-ran when the body arrived (Edit stayed disabled). */
    bodyReady(c) { if (!c) return false; return !!c.bodyLoaded || this.bodyKey(c) in this.bodies; },
    bodyOf(c) { if (!c) return ""; if (c.bodyLoaded) return c.body || ""; const key = this.bodyKey(c); return key in this.bodies ? this.bodies[key] : ""; },
    bodyErrorOf(c) { return c ? this.bodyErrors[this.bodyKey(c)] || "" : ""; },
    applyBody(c, body) { c.body = body; c.bodyLoaded = true; this.bodyErrors[this.bodyKey(c)] = ""; },
    /* The one predicate for "this tool can read this copy's document at all".
     * A linked entry is deliberately not followed and a folder name that is
     * not a valid skill name cannot be addressed, so neither is requested. */
    bodyFetchable(c) {
      return !!(c && c.name && c.scope && c.state !== "link" && (!c.record || c.record.addressable !== false));
    },
    /* A recursive scope can hold two instances of one name; a name-addressed
     * read would then serve one document to both copies. The pair key is what
     * those two share. */
    bodyPairKey(c) { return `${c && c.scope ? c.scope : ""}\u0000${(c && c.name) || ""}`; },
    modelCopies() { return this.m ? this.m.skills.reduce((all, s) => all.concat(s.copies), []) : []; },
    /* (scope, name) → the copies the current model holds for that pair. The
     * record's own `duplicated` state is not used: in the merged view it is
     * raised for one skill held by several agents, which is ordinary and is
     * still read exactly by name. */
    bodyPairs(copies) {
      const pairs = new Map();
      const add = (c) => {
        if (!c || !c.name || !c.scope) return;
        const key = this.bodyPairKey(c);
        const held = pairs.get(key);
        if (!held) pairs.set(key, [c]); else if (held.indexOf(c) < 0) held.push(c);
      };
      const pool = this.modelCopies();
      for (const c of (pool.length ? pool : (Array.isArray(copies) ? copies : [copies]))) add(c);
      return pairs;
    },
    bodyDuplicated(c, pairs) {
      const held = c && pairs ? pairs.get(this.bodyPairKey(c)) : null;
      return !!(held && held.length > 1);
    },
    pairCopies(c) {
      const mine = this.modelCopies().filter((x) => this.bodyPairKey(x) === this.bodyPairKey(c));
      return mine.length ? mine : [c];
    },
    /* Rows from one scoped list read, keyed by the physical path that tells
     * the copies apart. A name-addressed read cannot make that distinction. */
    bodiesByPath(c, rows) {
      const byPath = new Map();
      for (const r of rows) {
        if (!r || String(r.name) !== String(c.name)) continue;
        if (r.scope && c.scope && String(r.scope) !== String(c.scope)) continue;
        const path = r.physical_path || r.path || "";
        if (path && typeof r.body === "string") byPath.set(path, r.body);
      }
      return byPath;
    },
    duplicateBodyMap(c) {
      const flightKey = "list\u0000" + this.bodyPairKey(c);
      let request = this.bodyInflight[flightKey];
      if (!request) {
        request = api(`/api/skills?scope=${encodeURIComponent(c.scope)}&q=${encodeURIComponent(c.name)}`)
          .then((rows) => this.bodiesByPath(c, Array.isArray(rows) ? rows : []));
        this.bodyInflight[flightKey] = request;
        request.then((byPath) => {
          if (this.bodyInflight[flightKey] !== request) return;
          for (const sibling of this.pairCopies(c)) {
            const body = byPath.get(sibling.path);
            if (typeof body === "string") this.applyBody(sibling, body);
          }
        }).catch(() => { /* the caller reports the failure next to its own view */ })
          .finally(() => { if (this.bodyInflight[flightKey] === request) delete this.bodyInflight[flightKey]; });
      }
      return request;
    },
    namedBody(c) {
      const key = this.bodyKey(c);
      let request = this.bodyInflight[key];
      if (!request) {
        request = api(`/api/skills/${encodeURIComponent(c.name)}?scope=${encodeURIComponent(c.scope)}`)
          .then((record) => {
            const path = record?.link_followed ? record.linked_to : record?.physical_path || record?.path;
            if (path && c.path && path !== c.path) throw new Error("The copy moved. Refresh files to find its current folder.");
            if (record?.content_hash && c.hash && record.content_hash !== c.hash) throw new Error("The file changed. Refresh files to read the current version.");
            if (record?.decode_error || typeof record?.body !== "string") throw new Error("The document could not be read.");
            return record.body;
          });
        this.bodyInflight[key] = request;
        request.then((body) => {
          if (this.bodyInflight[key] === request) { this.bodies[key] = body; delete this.bodyErrors[key]; }
        })
          .catch(() => { /* the caller reports the failure next to its own view */ })
          .finally(() => { if (this.bodyInflight[key] === request) delete this.bodyInflight[key]; });
      }
      return request;
    },
    async ensureBodies(copies) {
      const list = (Array.isArray(copies) ? copies : [copies]).filter((c) => c && !c.bodyLoaded && this.bodyFetchable(c));
      if (!list.length) return;
      const cache = this.bodies;
      const pairs = this.bodyPairs(list);
      await Promise.all(list.map(async (c) => {
        const key = this.bodyKey(c);
        try {
          const body = this.bodyDuplicated(c, pairs) ? (await this.duplicateBodyMap(c)).get(c.path) : await this.namedBody(c);
          if (typeof body !== "string") throw new Error("This copy could not be matched to a single document.");
          if (cache === this.bodies) this.applyBody(c, body);
        } catch (e) {
          if (cache === this.bodies) this.bodyErrors[key] = this.friendly(e?.message || "The document could not be read.");
        }
      }));
    },
    primeBodies() {
      if (!this.m) return;
      const page = this.route && this.route.page;
      if (page === "skill" && this.skill && this.route.screen !== "why") return this.ensureBodies(this.skill.copies);
      if (page === "map") return this.ensureBodies(this.mapComparePair);
      if (this.tableHero && this.tableMode) return this.ensureBodies(this.tableComparisonCopies);
      return undefined;
    },
    comparisonEvidence(pair) {
      if (!pair) return null;
      const copies = pair.map((copy) => ({
        scope: this.agentOf(copy.scope).name,
        path: copy.path,
        error: this.bodyErrorOf(copy),
      }));
      const preview = pair.every((copy) => this.bodyReady(copy))
        ? documentPreview(this.bodyOf(pair[0]), this.bodyOf(pair[1])) : null;
      return { copies, preview };
    },
    async retryDocument() {
      if (this.readerKey) {
        await this.refreshReaderView();
        if (this.readerView) this.$refs.readerIdentity?.focus();
        return;
      }
      const copy = this.refCopy;
      await this.ensureBodies(copy);
      if (this.refCopy !== copy || !this.bodyReady(copy)) return;
      if (this.route.screen === "edit" && !this.edit) this.showRouteScreen();
      else this.$refs.readerIdentity?.focus();
    },

    /* ----- search / filter ----- */
    /* The Skills page filter: typing filters the shelf in place. */
    searchInput(v) { this.query = v; this.extra = {}; },
    capReset() { this.extra = {}; },
    showMore(id) { this.extra = { ...this.extra, [id]: (this.extra[id] || 0) + 96 }; },
    clearFilters() { this.query = ""; this.filter = "all"; this.agentFilter = "all"; this.tagFilter="";this.extra = {}; this.$nextTick(() => { const q = document.getElementById("q"); if (q) q.focus(); }); },
    pickAgent(id, query = "") { this.agentFilter = id; this.filter = "all"; this.tagFilter = ""; this.query = query; this.extra = {}; },
    findInMap() { Router.go(Router.routeHref("skills", { view: "map", q: this.query.trim() })); },
    skipToContent() { const h = document.getElementById("h1") || this.$refs.main; if (h) h.focus(); },
    focusH1() { this.$nextTick(() => { const h = document.getElementById("h1"); if (h) h.focus({ preventScroll: true }); }); },

    /* ----- toasts & dialogs ----- */
    friendly(msg) {
      let s = String(msg || "Something went wrong.");
      if (/invalid archive|not a gzip|ReadError|zipfile/i.test(s)) return "That file is not a backup archive. Choose a .tar.gz, .tar or .zip file made by Jackfield.";
      if (/not valid UTF-8/i.test(s)) return "One of the copies is not saved as UTF-8 text. Keep a copy of the original file, then open it in a text editor and save it as UTF-8 before editing it here.";
      if (/traceback|(?:UnicodeDecode|Recursion|Permission|FileNotFound|Operational)Error|\[Errno \d+\]/i.test(s)) return "The operation could not be completed. Refresh and try again; check that the skill files are readable and writable.";
      return s.replace(/(?:\/[^\s'":]+)+\/([^\s'":/]+)/g, "$1").replace(/\s*\(byte 0x[0-9a-f]+ at offset \d+\)/i, "");
    },
    openDialog(d) { this.opener = document.activeElement; this.dialog = { cancel: "Cancel", ...d }; this.$nextTick(() => { const d = (this.$refs.dlg?.$el || this.$refs.dlg); const b = d && (d.querySelector("input:not(.sr-only), select, textarea") || d.querySelector("button:not(.sr-only)")); if (b) b.focus(); }); },
    closeDialog(restoreFocus = true) {
      if (this.busy || !this.dialog) return;
      if (restoreFocus && this.dialog.createDiscard) return this.keepCreateDraft();
      if (restoreFocus && this.createDraftDirty()) return this.reviewCreateDiscard();
      this.dismissDialog(restoreFocus);
    },
    dismissDialog(restoreFocus) {
      const opener = this.opener, aiEdit = this.dialog.aiEdit;
      this.dialog = null;
      if (aiEdit) this.retireAiEdit(aiEdit.result);
      if (restoreFocus) this.$nextTick(() => { if (!this.dialog && opener?.isConnected) opener.focus(); });
    },
    createDraftDirty() {
      const d = this.dialog;
      if (!d?.formBaseline) return false;
      return !!(d.author.brief || d.author.context || d.author.revision ||
        Object.keys(d.form).some((key) => d.form[key] !== d.formBaseline[key]));
    },
    reviewCreateDiscard(href = "") {
      const prior = this.dialog.createDiscard;
      this.dialog.createDiscard = { href, focus: prior?.focus || document.activeElement?.id };
      this.$nextTick(() => this.$refs.keepCreateDraft?.focus());
    },
    keepCreateDraft() {
      const { focus } = this.dialog.createDiscard;
      this.dialog.createDiscard = null;
      this.$nextTick(() => (document.getElementById(focus) || document.getElementById("nf-name"))?.focus());
    },
    discardCreateDraft() {
      const { href } = this.dialog.createDiscard;
      this.dismissDialog(!href);
      if (href) Router.go(href);
    },
    async confirmDialog() {
      if(this.busy || this.dialog?.templateLoading)return;
      if (this.dialog && this.dialog.form && this.formInvalid) {
        const f = this.dialog.form;
        this.live = this.formErrors.name || this.formErrors.desc || (!f.name.trim() ? "Add a name." : "Add a description.");
        return;
      }
      const d = this.dialog;
      if (d?.recovery) return this.restoreAgentTrash(d.recovery);
      if (!d?.form) this.dialog = null;
      if (d?.onConfirm) await d.onConfirm(d);
      this.$nextTick(() => { if (!this.dialog && this.opener && this.opener.isConnected) this.opener.focus(); });
    },
    dialogKeys(e) {
      if (e.key === "Escape") { e.stopPropagation(); this.closeDialog(); return; }
      if (e.key !== "Tab") return;
      const f = [...(this.$refs.dlg?.$el || this.$refs.dlg).querySelectorAll("button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], summary")].filter(el=>el.tabIndex!==-1&&el.offsetParent!==null);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    },

    /* ----- writes (every one goes through the existing REST routes) ----- */
    async snapshotIds(name, scope) {
      const r = await api(`/api/history?name=${encodeURIComponent(name)}&scope=${encodeURIComponent(scope)}&snapshots=1`);
      if (!r || !Array.isArray(r.snapshots)) throw new Error("Recovery snapshots could not be read. Refresh and try again.");
      return r.snapshots;
    },
    /* Copy `from` over each target. The previous text of each target is
     * snapshotted by the backend, which is what makes Undo possible. */
    async doSync(name, from, tos) {
      const before = {}, prior = {};
      for (const t of tos) {
        before[t] = new Set(await this.snapshotIds(name, t));
        prior[t] = await api(`/api/skills/${encodeURIComponent(name)}?scope=${encodeURIComponent(t)}`).catch(() => null);
      }
      const res = await api("/api/sync", { method: "POST", body: JSON.stringify({ name, from_scope: from, to_scopes: tos, force: true }) });
      const synced = res.synced || [];
      const undo = []; let manualRecovery = false;
      for (const t of synced) {
        let after;
        try { after = await this.snapshotIds(name, t); } catch (e) { manualRecovery = true; continue; }
        const fresh = after.filter((id) => !before[t].has(id));
        if (fresh.length === 1 && prior[t] && !prior[t].decode_error) undo.push([t, fresh[0], !!prior[t].disabled]);
        else manualRecovery = true;
      }
      return { synced, skipped: res.skipped || [], undo, manualRecovery,
        replaced_to_trash: res.replaced_to_trash, retained_backup: res.retained_backup };
    },
    async restoreSyncText(name, scope, snapshot, wasDisabled) {
      const target = `/api/skills/${encodeURIComponent(name)}`;
      const query = `?scope=${encodeURIComponent(scope)}`;
      const current = await api(target + query), initiallyDisabled = !!current.disabled;
      let restored = false;
      try {
        if (initiallyDisabled) await api(target + "/enable" + query, { method: "POST" });
        await api(`/api/trash/${encodeURIComponent(name)}?snapshot=${encodeURIComponent(snapshot)}&scope=${encodeURIComponent(scope)}`, { method: "POST" });
        restored = true;
      } finally {
        const disabled = restored ? wasDisabled : initiallyDisabled;
        const latest = await api(target + query);
        if (!!latest.disabled !== disabled) await api(target + (disabled ? "/disable" : "/enable") + query, { method: "POST" });
      }
    },
    undoFor(name, entries) {
      if (entries.some((e) => e.manualRecovery)) return null;
      const list = entries.flatMap((e) => e.undo.map(([scope, snap, off]) => [e.name || name, scope, snap, off]));
      if (!list.length) return null;
      return async () => { for (const [n, scope, snap, off] of list) await this.restoreSyncText(n, scope, snap, off); };
    },
    skipText(skipped) { return skipped.length ? ` ${skipped.length} could not be changed: ${skipped.map((s) => this.friendly(s.reason)).slice(0, 2).join("; ")}.` : ""; },
    /* A copy's observed token count is what its agent would spend on it; say so
     * when a switch changes that, and stay silent when the count is unknown. */
    tokenClause(tokens, turning) {
      const n = Number(tokens) || 0;
      if (n <= 0) return "";
      // A sentence of its own: the toast already ends its first sentence with
      // a full stop, and "Codex. — frees" read as a typo.
      return turning === "off" ? ` That frees about ${this.fmt(n)} tokens of that agent's budget.` : ` It uses about ${this.fmt(n)} tokens.`;
    },

    reviewReaderChange(copy) {
      const place = copy && this.tableColumns.find((column) => columnScopes(column).includes(copy.scope));
      if (place) this.tableSelect({ name: this.skill.name, agent: place.id });
      else this.toast("This copy has no square in the Skills table. Choose it using Read copy.", { err: true });
    },
    syncDiffering() {
      const s = this.skill;
      if (!s || s.ref.ambiguous) return;
      this.reviewReaderChange(s.differing[0]);
    },
    async runSync(name, from, tos, label, onUndo) {
      if (this.busy) return null;
      this.busy = true;
      try {
        const r = await this.doSync(name, from, tos);
        const undo = this.undoFor(name, [r]);
        await this.refresh();
        const message = r.synced.length ? `${label} ${join(r.synced.map((id) => this.agentOf(id).name))}.` : "Nothing was changed.";
        this.toast(message + this.skipText(r.skipped) + Domain.syncRecoveryNotice([r]) +
          (r.manualRecovery ? " Text Undo is unavailable. Check Trash & backups or your backup." : ""),
        { err: !r.synced.length, undo: r.synced.length ? undo : null, onUndo,
          undoText: "Undone. Text and on/off state restored. Supporting files are unchanged." });
        return r.synced.length ? r : null;
      } catch (e) { this.toast(e.message, { err: true }); return null; } finally { this.busy = false; }
    },
    /* A followed link (SCOPE-2) is read-only: it belongs to the agent whose
     * folder it lives in, and a write here would land in that other copy. */
    readOnlyWhy(c) { const from = c && c.linkFrom ? this.shortPath(c.linkFrom) : "another folder"; return `This is a link into ${from}; change it in that agent's copy.`; },
    async toggleCopy(c) {
      if (c && c.readOnly) { this.toast(this.readOnlyWhy(c), { err: true }); return; }
      const name = this.skill.name, to = c.state === "on" ? "disable" : "enable";
      const clause = this.tokenClause(c.tokens, to === "disable" ? "off" : "on");
      this.busy = true;
      try {
        await api(`/api/skills/${encodeURIComponent(name)}/${to}?scope=${encodeURIComponent(c.scope)}`, { method: "POST" });
        await this.refresh();
        const back = to === "disable" ? "enable" : "disable";
        this.toast(`${name} turned ${to === "disable" ? "off" : "on"} in ${this.agentOf(c.scope).name}.${clause}`, { undo: async () => { await api(`/api/skills/${encodeURIComponent(name)}/${back}?scope=${encodeURIComponent(c.scope)}`, { method: "POST" }); } });
      } catch (e) { this.toast(e.message, { err: true }); await this.refresh(); } finally { this.busy = false; }
    },
    async allOn() {
      const s = this.skill; this.busy = true; const turned = [];
      const gained = s.copies.filter((x) => x.state === "off" && !x.readOnly).reduce((n, x) => n + (Number(x.tokens) || 0), 0);
      try {
        for (const c of s.copies.filter((x) => x.state === "off" && !x.readOnly)) { await api(`/api/skills/${encodeURIComponent(s.name)}/enable?scope=${encodeURIComponent(c.scope)}`, { method: "POST" }); turned.push(c.scope); }
        await this.refresh();
        const clause = gained > 0 ? ` That uses about ${this.fmt(gained)} tokens across ${plural(turned.length, "agent")}.` : "";
        this.toast(`${s.name} turned on everywhere.${clause}`, { undo: async () => { for (const sc of turned) await api(`/api/skills/${encodeURIComponent(s.name)}/disable?scope=${encodeURIComponent(sc)}`, { method: "POST" }); } });
      } catch (e) { this.toast(e.message, { err: true }); await this.refresh(); } finally { this.busy = false; }
    },
    async turnOffIn(s, scope) {
      this.busy = true; const name = s.name;
      const c = s.copies.find((x) => x.scope === scope);
      if (!c || c.readOnly) { this.busy = false; if (c) this.toast(this.readOnlyWhy(c), { err: true }); return; }
      const clause = this.tokenClause(c && c.tokens, "off");
      try {
        await api(`/api/skills/${encodeURIComponent(name)}/disable?scope=${encodeURIComponent(scope)}`, { method: "POST" });
        await this.refresh();
        this.toast(`${name} turned off in ${this.agentOf(scope).name}.${clause}`, { undo: async () => { await api(`/api/skills/${encodeURIComponent(name)}/enable?scope=${encodeURIComponent(scope)}`, { method: "POST" }); } });
      } catch (e) { this.toast(e.message, { err: true }); } finally { this.busy = false; }
    },
    fixSkillBad() {
      const p = this.m.problems.find((x) => x.id === "bad:" + this.skill.name);
      if (p?.fixable) this.reviewReaderChange(this.skill.broken[0]);
      else if (p) this.fixBad(p);
    },
    fixBad(p, undoHook) {
      if (p.fixable) return this.runSync(p.skill, p.source, p.agents, `${p.skill} was replaced in`, undoHook);
      const s = this.m.byName.get(p.skill);
      this.openDialog({ title: p.title, lines: [p.text], how: p.how, paths: s.broken.map((c) => shortPath(c.path)), cancel: "Close" });
      return null;
    },
    openShare() {
      if (!this.shareTargets.length) return;
      const s = this.skill, source = this.refCopy, from = source.scope;
      this.openDialog({
        title: `Add “${s.name}” to another agent`, lines: ["Choose where to copy it. The copy comes from " + this.agentOf(from).name + ". Whether it is on or off, and its supporting files, are copied too."],
        picks: this.shareTargets.map((a) => ({ id: a.id, label: a.name, path: a.path })), chosen: this.shareTargets.length === 1 ? [this.shareTargets[0].id] : [], confirm: "Add",
        onConfirm: (d) => this.change("copy", { sources: [source], scopes: d.chosen, originals: [],
          keys: d.chosen.map((id) => tableKey(s.name, id)),
          message: s.name + " added to " + join(d.chosen.map((id) => this.agentOf(id).name)) + "." }),
      });
    },
    openTrash() {
      const s = this.skill, copies = this.readerTrashCopies;
      if (!copies.length) return;
      this.openDialog({
        title: `Move “${s.name}” to the trash?`, danger: true, confirm: "Move to trash",
        lines: ["Choose the places to remove it from. Each agent keeps its own trash folder, and every copy you remove here can be restored from Trash & backups or with Undo."],
        picks: copies.map((copy) => ({ id: copy.scope, label: this.agentOf(copy.scope).name, path: shortPath(copy.path) })),
        chosen: copies.length === 1 ? [copies[0].scope] : [],
        onConfirm: async (d) => {
          this.busy = true;
          const trashed = [];
          let failure = "";
          try {
            for (const sc of d.chosen) {
              const r = await api(`/api/skills/${encodeURIComponent(s.name)}?scope=${encodeURIComponent(sc)}&purge=0`, { method: "DELETE" });
              if (!r?.trash_path) throw new Error("The trash entry could not be confirmed. Check Trash before retrying.");
              trashed.push({ scope: sc, trash_path: r.trash_path });
            }
          } catch (error) {
            failure = this.friendly(error.message);
          }
          try {
            await this.refresh();
            if (!trashed.length) { if (failure) this.toast(failure, { err: true }); return; }
            const undo = trashed.length ? async () => { for (const t of trashed) await this.restoreTrashed(s.name, t.scope, t.trash_path); } : null;
            const undoAt = this.route.page === "skill" && this.route.name === s.name &&
              !this.m.byName.get(s.name) ? "#/skills" : null;
            const places = join(trashed.map((item) => this.agentOf(item.scope).name));
            this.toast(`${s.name} moved to the trash in ${places}.${failure ? " " + failure : ""}`, { undo, undoAt, err: !!failure });
            if (undoAt) Router.go(undoAt);
          } finally { this.busy = false; }
        },
      });
    },
    openPermanentDelete() {const skill=this.skill;if(!skill)return;this.openDialog({title:`Permanently delete “${skill.name}”?`,danger:true,confirm:"Delete permanently",lines:["This removes the selected copies without moving them to trash. There is no Undo or trash restore for this action."],picks:skill.copies.filter(c=>!c.readOnly&&c.record.addressable!==false&&c.state!=="link"&&this.agentOf(c.scope).writable).map(c=>({id:c.scope,label:this.agentOf(c.scope).name,path:shortPath(c.path)})),chosen:[],onConfirm:async d=>{this.busy=true;try{for(const scope of d.chosen)await api(`/api/skills/${encodeURIComponent(skill.name)}?scope=${encodeURIComponent(scope)}&purge=1`,{method:"DELETE"});await this.refresh();this.toast("Selected copies permanently deleted.");if(!this.m.byName.get(skill.name))Router.go("#/skills");}catch(e){await this.refresh();this.toast(e.message,{err:true});}finally{this.busy=false;}}});},

    /* ----- create, recovery, theme, help ----- */
    authorInput(estimate) {
      const { form, author } = this.dialog;
      return { scope: form.scope, name: form.name.trim(), brief: author.brief.trim(),
        context: author.context, verify: false, estimate, plan: estimate ? undefined : author.estimate?.plan };
    },
    async requestAuthorDraft(estimate) {
      const d = this.dialog, a = d.author;
      if (!a.brief.trim() || a.pending) return;
      const key = JSON.stringify(this.authorInput(true));
      const revision = JSON.stringify(d.form);
      if (!estimate && key !== a.key) { a.estimate = null; a.error = "Preview the request again after changing its inputs."; return; }
      a.pending = true; a.error = ""; a.result = null;
      try {
        const result = await api("/api/ai/draft-skill", { method: "POST", body: JSON.stringify(this.authorInput(estimate)) });
        if (this.dialog !== d || key !== JSON.stringify(this.authorInput(true))) return;
        if (estimate) { a.estimate = result; a.key = key; }
        else { a.result = result; a.revision = revision; }
      } catch (error) { if (this.dialog === d) a.error = this.friendly(error.message); }
      finally { a.pending = false; }
    },
    useAuthorDraft() {
      const { form, author } = this.dialog;
      if (author.revision !== JSON.stringify(form) || author.key !== JSON.stringify(this.authorInput(true))) {
        author.error = "The form changed after drafting. Preview a fresh request."; return;
      }
      const draft = author.result.draft;
      Object.assign(form, { name: draft.name, desc: draft.description, body: draft.body });
      author.cases = author.result.cases || [];
      author.result = null; author.estimate = null; author.key = "";
    },
    async saveAuthorCases(d, name) {
      const prompts = d.author.cases.filter((row) => row.selected).map((row) => ({
        text: row.text, expected: row.should_trigger ? name : null,
      }));
      if (prompts.length) {
        try { await api("/api/ai/prompt-sets", { method: "POST", body: JSON.stringify({ scope: d.form.scope, prompts }) }); }
        catch (error) { this.toast("Skill created. Test cases could not be saved. " + this.friendly(error.message), { err: true }); }
      }
    },
    async newSkillCreated({ name, count }) {
      const origin = this.route.href;
      await this.refresh();
      this.toast(`${name} created in ${plural(count, "place")}.`);
      if (this.route.href === origin && this.m?.byName.has(name)) Router.go(Router.skillHref(name));
    },
    openCreate(prefill = {}) {
      const first = this.createTargets.find((x) => !x.library) || this.createTargets[0];
      const target = this.createTargets.find((x) => x.id === prefill.scope);
      this.openDialog({
        title: "New skill", form: { name: prefill.name || "", desc: prefill.description || "", scope: target ? target.id : first ? first.id : "global", category:prefill.category || "",version:prefill.version || "",license:prefill.license || "",compatibility:prefill.compatibility || "",allowed_tools:prefill.allowed_tools || "",body:typeof prefill.body === "string" ? prefill.body : "## When to use\n\nDescribe the situations where an agent should use this skill.\n\n## Steps\n\n1. \n",template:"" }, confirm: "Create skill",
        author: { brief: "", context: "", estimate: null, key: "", result: null, revision: "", cases: [], pending: false, error: "" },
        onConfirm: async (d) => {
          const f = d.form; this.busy = true;
          try {
            await api("/api/skills?scope=" + encodeURIComponent(f.scope), { method: "POST",
              body: JSON.stringify({ name: f.name.trim(), description: f.desc.trim(), category:f.category,version:f.version,license:f.license,compatibility:f.compatibility,allowed_tools:f.allowed_tools,body:f.body.replaceAll("{name}",f.name.trim()) }) });
            this.dialog=null;
            this.$refs.newSkill?.finish();
            await this.saveAuthorCases(d, f.name.trim());
            await this.refresh();
            this.toast(`${f.name.trim()} created in ${this.agentOf(f.scope).name}.`);
            Router.go(Router.skillHref(f.name.trim()));
          } catch (e) { d.error=this.friendly(e.message);this.live=d.error; } finally { this.busy = false; }
        },
      });
      const dialog = this.dialog;
      dialog.formBaseline = { ...dialog.form };
      api("/api/templates").then((result) => {
        if (this.dialog !== dialog) return;
        this.createTemplates = result.templates || [];
        if (prefill.template && this.createTemplates.includes(prefill.template) &&
            !dialog.form.template && dialog.form.body === dialog.formBaseline.body) {
          dialog.form.template = prefill.template;
          dialog.formBaseline.template = prefill.template;
          this.loadCreateTemplate(true);
        }
      }).catch((error) => { if (this.dialog === dialog) dialog.error = "Templates unavailable: " + this.friendly(error.message); });
    },
    useDraft(draft) {
      if (!draft || typeof draft !== "object") return;
      this.openCreate({
        scope: draft.scope, name: draft.name, description: draft.description, body: draft.body,
        category: draft.category, version: draft.version, license: draft.license,
        compatibility: draft.compatibility, allowed_tools: draft.allowed_tools,
      });
    },
    async loadCreateTemplate(initial = false) {
      const d = this.dialog;
      if (!d?.form) return;
      const { template: name, body } = d.form;
      const request = d.templateRead = (d.templateRead || 0) + 1;
      d.templateLoading = !!name;
      if (!name) return;
      const current = () => this.dialog === d && d.templateRead === request;
      try {
        const template = await api("/api/templates/" + encodeURIComponent(name));
        if (current() && d.form.body === body) {
          d.form.body = stripFrontmatter(template.body || "");
          if (initial) d.formBaseline.body = d.form.body;
        }
      } catch (error) {
        if (current()) d.error = this.friendly(error.message);
      } finally {
        if (current()) d.templateLoading = false;
      }
    },
    async loadTrash() {
      const gen = ++this.trashGen;
      this.trashLoading = true;
      try {
        const rows = await api("/api/trash");
        if (!Array.isArray(rows)) throw new Error("The library trash list could not be read.");
        if (gen !== this.trashGen) return;
        this.trash = rows; this.trashError = "";
      } catch (e) { if (gen === this.trashGen) this.trashError = this.friendly(e.message); }
      finally { if (gen === this.trashGen) this.trashLoading = false; }
    },
    /* Both Recovery rows and Undo address the listed trash entry. */
    restoreTrashed(name, scope, trashPath) {
      const url = `/api/trash/${encodeURIComponent(name)}?scope=${encodeURIComponent(scope || "global")}`;
      return api(url, { method: "POST", body: trashPath ? JSON.stringify({ trash_path: trashPath }) : undefined });
    },
    async loadAgentTrash() {
      const gen = ++this.agentTrashGen;
      const agents = (this.m ? this.m.agents : []).filter((a) => !a.library);
      this.agentTrashLoading = true;
      const rows = [], errors = [];
      await Promise.all(agents.map(async (a) => {
        try {
          const list = await api("/api/trash?scope=" + encodeURIComponent(a.id));
          if (!Array.isArray(list)) throw new Error("This trash list could not be read.");
          for (const row of list) rows.push({ ...row, scope: a.id, scopeLabel: a.name, canRestore: a.writable });
        } catch (e) { errors.push({ scope: a.id, message: this.friendly(e.message) }); }
      }));
      if (gen !== this.agentTrashGen) return;
      errors.sort((a, b) => a.scope.localeCompare(b.scope));
      this.agentTrash = rows; this.agentTrashErrors = errors; this.agentTrashLoading = false;
    },
    async retryTrash() {
      if (this.trashLoading || this.agentTrashLoading) return;
      await Promise.all([this.loadTrash(), this.loadAgentTrash()]);
      if (!this.mergedTrashErrors.length && this.route.page === "recovery") document.getElementById("rec-trash")?.focus();
    },
    agentRestoreLabel(row) {
      const target = `Review restore for ${row.name} in ${row.scopeLabel}`;
      return row.copyLabel ? `${target}, ${row.copyLabel}` : target;
    },
    reviewTrashRow(id) {
      const row = this.mergedTrash.find((item) => item.id === id);
      if (!row?.canRestore || !row.trash_path || this.busy) return;
      this.openDialog({
        title: `Restore ${row.name}?`,
        recovery: row,
        confirm: "Restore folder",
        error: "",
      });
    },
    async restoreAgentTrash(t) {
      if (this.busy) return;
      const dialog = this.dialog, visit = this.screenVisit;
      this.busy = true;
      try {
        const result = await this.restoreTrashed(t.name, t.scope, t.trash_path);
        if (this.dialog === dialog) this.dialog = null;
        await this.refresh();
        if (visit === this.screenVisit) {
          this.restoredTrash = this.confirmRestoredTrash(t, result);
          document.getElementById("rec-trash")?.focus();
        }
      } catch (e) {
        if (this.dialog === dialog) {
          dialog.error = this.friendly(e.message);
          this.$nextTick(() => this.$refs.restoreError?.focus());
        } else this.toast(e.message, { err: true });
      } finally { this.busy = false; }
    },
    confirmRestoredTrash(row, result) {
      const skill = this.loadError ? null : this.m?.byName.get(row.name);
      const path = result?.path;
      const copies = skill?.squareCopies.filter((copy) => copy.scope === row.scope && (!path || copy.path === path)) || [];
      if (copies.length !== 1) return { name: row.name, scopeLabel: row.scopeLabel, status: "unknown",
        message: "The restore finished. Refresh files to check the restored copy." };
      const [copy] = copies;
      const column = this.tableColumns.find((place) => columnScopes(place).includes(row.scope));
      const status = column ? Model.squareStatus(skill, column, null, this.tableColumns)
        : copy.state === "broken" ? "unreadable" : ["on", "off"].includes(copy.state) ? copy.state : "unknown";
      const href = Router.skillHref(row.name, "", { scope: row.scope, copy: copy.path,
        sel: column ? tableKey(row.name, column.id) : undefined });
      return { name: row.name, scopeLabel: row.scopeLabel, status, href, message: `${row.name} restored to ${row.scopeLabel}.` };
    },
    /* A reviewed batch removal reports the trash path of every copy it moved;
     * the toast keeps those exact paths so Undo restores each one it removed. */
    removedBatch(items) {
      const entries = (items || []).filter((i) => i && i.trash_path);
      if (!entries.length) return;
      this.toast(`${plural(entries.length, "copy", "copies")} moved to the trash.`, {
        undo: async () => { for (const e of entries) await this.restoreTrashed(e.name, e.scope, e.trash_path); },
      });
    },
    openPurge() {
      if (this.busy || this.trashLoading || this.trashError || !this.trash.length) return;
      this.openDialog({ title: "Empty library trash?", danger: true, confirm: "Delete permanently",
        lines: ["All copies in your library trash will be deleted permanently. This cannot be undone."],
        onConfirm: async () => {
          this.busy = true;
          try {
            await api("/api/trash/purge", { method: "POST" });
            await this.refresh();
            this.toast("Library trash emptied.");
          } catch (e) { this.toast(e.message, { err: true }); }
          finally { this.busy = false; }
        } });
    },
    async exportBackup(full) {
      if (this.busy) return;
      const visit = this.screenVisit;
      this.busy = true; this.exportPending = true; this.exportError = "";
      try {
        const { blob, filename } = await Domain.apiBlob("/api/export" + (full ? "?full=1" : ""));
        const url = URL.createObjectURL(blob), a = document.createElement("a");
        try {
          a.href = url; a.download = filename || "skills-backup.tar.gz"; document.body.appendChild(a); a.click();
        } finally {
          a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 2000);
        }
        if (blob.size > 0) {
          this.libraryDownload = { at: Date.now(), size: blob.size };
          try { localStorage.setItem(LAST_LIBRARY_DOWNLOAD, JSON.stringify(this.libraryDownload)); }
          catch { /* The current page can still show the observed download. */ }
        }
        if (visit === this.screenVisit) this.toast("Backup download started.");
      } catch (e) {
        const error = Domain.archiveDownloadError(e);
        if (visit === this.screenVisit && this.route.page === "recovery") this.exportError = error;
        else this.toast(error, { err: true });
      } finally { this.busy = false; this.exportPending = false; }
    },
    /* The picker filters by `accept`; a dropped file is not, so check its name.
     * The server still decides whether the bytes are a real archive. */
    pickImport(list) {
      if (this.busy) return;
      const file = (list && list[0]) || null;
      this.clearImportReview();
      if (file && !/\.(tar\.gz|tgz|tar|zip)$/i.test(file.name)) { this.importFile = null; this.importReject = `${file.name} is not a backup file. Choose a .tar.gz, .tgz, .tar or .zip file.`; return; }
      this.importReject = ""; this.importFile = file;
    },
    clearImportReview() {
      this.importPlan = null;
      this.importError = "";
      this.importResult = null;
    },
    changeImportOption(key, value) {
      if (this.busy) return;
      this[key] = value;
      this.clearImportReview();
    },
    archiveImportRequest(file, review) {
      const query = new URLSearchParams({
        filename: file.name, force: this.importForce ? "1" : "0", full: this.importFull ? "1" : "0", ...review,
      });
      return api("/api/import?" + query, { method: "PUT", body: file });
    },
    async previewImport() {
      const file = this.importFile, visit = this.screenVisit;
      if (!file || this.busy) return;
      this.clearImportReview();
      this.busy = true; this.importPending = true;
      try {
        const plan = await this.archiveImportRequest(file, { preview: "1" });
        if (visit !== this.screenVisit) return;
        if (!plan.plan_id || !Array.isArray(plan.entries)) throw new Error("Jackfield could not read the backup preview.");
        this.importPlan = plan;
      } catch (e) { if (visit === this.screenVisit) this.importError = this.friendly(e.message); }
      finally { this.busy = false; this.importPending = false; }
    },
    archiveImportSummary(result) { return Domain.archiveImportSummary(result); },
    async doImport() {
      const file = this.importFile, plan = this.importPlan, visit = this.screenVisit;
      if (!file || !plan?.entries.some((entry) => entry.action !== "skip") || this.busy) return;
      this.busy = true; this.importPending = true;
      this.importError = ""; this.importResult = null;
      try {
        const r = await this.archiveImportRequest(file, { plan_id: plan.plan_id });
        if (visit === this.screenVisit) {
          this.importPlan = null;
          this.importResult = r;
          this.live = this.archiveImportSummary(r);
          this.importFile = null;
          const input = document.getElementById("imp-file"); if (input) input.value = "";
        }
        await this.refresh();
      } catch (e) {
        if (visit === this.screenVisit) { this.importPlan = null; this.importError = this.friendly(e.message); }
        else this.toast(e.message, { err: true });
      }
      finally { this.busy = false; this.importPending = false; }
    },
    applyTheme() {
      const root = document.documentElement;
      const dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.themePreference = this.theme;
      root.dataset.theme = this.theme === "system" ? (dark ? "dark" : "light") : this.theme;
    },
    cycleTheme() {
      this.theme = THEMES[(THEMES.indexOf(this.theme) + 1) % THEMES.length];
      try { localStorage.setItem("skillsmgr-theme", this.theme); } catch (e) { /* storage may be blocked */ }
      this.applyTheme(); this.live = "Theme: " + this.themeLabel;
    },
    openHelp() {
      this.openDialog({ title: "Keyboard shortcuts", cancel: "Close", keys: [
        [["/"], "Search skills, actions and pages"], [["?"], "Show this list"], [["Esc"], "Close a dialog"],
        [["Ctrl/Cmd", "K"], "Open search"],
        [["Ctrl", "S"], "Save while editing"], [["J", "K"], "Next or previous issue in Needs attention"], [["F"], "Fix the reviewed issue"],
      ] });
    },

    /* ----- editing ----- */
    async startEdit() {
      const s = this.skill, c = this.refCopy, href = this.route.href;
      if (!s || !c || !this.bodyFetchable(c)) return;
      /* The editor must never open on a body that has not loaded: read it
       * first, and abandon silently if the reader navigated away meanwhile.
       * A periodic re-read replaces `skill` with an equal-named object, so the
       * identity that matters is the name and the route, not the object. */
      await this.ensureBodies([c]);
      if (this.route.href !== href || !this.skill || this.skill.name !== s.name || this.route.page !== "skill" ||
          !this.refCopy || this.refCopy.scope !== c.scope || this.refCopy.path !== c.path || this.refCopy.hash !== c.hash) return;
      if (!this.bodyReady(c)) { this.toast(this.bodyErrorOf(c) || "The document could not be read. Try again.", { err: true }); return; }
      const body = stripFrontmatter(this.bodyOf(c).replace(/^\uFEFF/, ""));
      const metadata={category:c.record.category||"",version:c.record.version||"",license:c.record.license||"",compatibility:Domain.formatCompat(c.record.compatibility),allowed_tools:Domain.formatTools(c.record.allowed_tools)};
      const exact = this.route.copyPath || (this.readCopyName === s.name && this.readCopyPath);
      const places = [...this.editPlaces.values()];
      this.edit = { name: s.name, desc: c.description, baseDesc: c.description, body, baseBody: body,
        metadata, baseMetadata: { ...metadata }, tab: "write", error: "",
        targets: exact ? [c.scope] : places.filter(({ copy }) => copy && copy.hash === c.hash).map(({ scope }) => scope),
        places, initialTargets: Object.fromEntries(places.map(({ scope, evidence }) => [scope, evidence])),
        copy: { path: c.path, scope: c.scope, hash: c.hash } };
      this.showSkillView("edit");
      this.$nextTick(() => { this.growArea(); const d = document.getElementById("ed-desc"); if (d) d.focus(); });
    },
    openAiDiagnosis() {
      if (!this.refCopy) return;
      this.openDialog({ title: "Why didn’t this skill run?", diagnosis: this.refCopy });
    },
    showSkillView(screen = "") {
      const href = Router.skillHref(this.route.name, screen, this.readerRouteOptions());
      const next = Router.parseRoute(href);
      this.resetScreenFeedback(next);
      this.route = next;
      this.routeAction = href;
      Router.replace(href);
      this.updatePageTitle();
    },
    async repairAiDiagnosis(prompt) {
      const dialog = this.dialog;
      await this.startEdit();
      await this.$nextTick();
      if (this.dialog === dialog && this.edit?.copy.path === dialog.diagnosis.path) this.openAiEdit(prompt);
    },
    openAiEdit(example = "") {
      const e = this.edit, area = this.$refs.edbody;
      if (!e?.copy.hash || !area || this.busy) return;
      const body = area.value;
      const start = area.selectionStart, end = area.selectionEnd;
      const selection = start < end ? [Array.from(body.slice(0, start)).length, Array.from(body.slice(0, end)).length] : null;
      this.openDialog({ title: "Edit with AI", aiEdit: {
        target: e.copy, name: e.name, body, selection, selectedText: selection ? body.slice(start, end) : "",
        instruction: "", example, estimate: null, key: "", result: null, keep: [], pending: false, error: "",
      } });
    },
    aiEditInput(estimate) {
      const a = this.dialog.aiEdit;
      return { name: a.name, scope: a.target.scope, target_path: a.target.path, document_hash: a.target.hash,
        body: a.body, selection: a.selection, instruction: a.instruction.trim(), example: a.example.trim(),
        tree_hash: estimate ? undefined : a.estimate?.tree_hash, plan: estimate ? undefined : a.estimate?.plan, estimate };
    },
    async retireAiEdit(result) {
      const review = result?.review;
      if (review?.review_state !== "pending") return;
      try { await api(`/api/source-updates/reviews/${encodeURIComponent(review.review_id)}`, { method: "DELETE" }); }
      catch (error) { this.toast(this.friendly(error.message), { err: true }); }
    },
    async requestAiEdit(estimate) {
      const d = this.dialog, a = d.aiEdit;
      if (a.pending || !a.instruction.trim()) return;
      const key = JSON.stringify(this.aiEditInput(true));
      if (!estimate && key !== a.key) return;
      a.pending = true; a.error = "";
      try {
        const previous = a.result;
        a.result = null;
        await this.retireAiEdit(previous);
        if (this.dialog !== d || key !== JSON.stringify(this.aiEditInput(true))) return;
        const result = await api("/api/ai/edit-skill", { method: "POST", body: JSON.stringify(this.aiEditInput(estimate)) });
        if (this.dialog !== d || key !== JSON.stringify(this.aiEditInput(true))) { await this.retireAiEdit(result); return; }
        if (estimate) { a.estimate = result; a.key = key; }
        else { a.result = result; a.keep = (result.hunks || []).map(h => h.id); }
      } catch (error) { if (this.dialog === d) a.error = this.friendly(error.message); }
      finally { a.pending = false; }
    },
    aiEditPartial(a) { const hunks = a?.result?.hunks || []; return hunks.length > 1 && a.keep.length !== hunks.length; },
    hunkText(h) {
      const lines = (text, mark) => text ? text.replace(/\n$/, "").split("\n").map(line => mark + line) : [];
      return [...lines(h.removed, "- "), ...lines(h.added, "+ ")].join("\n");
    },
    /* Keep only the checked hunks: the server restages a fresh review from them
     * (no model call) and cancels the full proposal, so the comparison, the
     * checks and the saved edit all describe exactly what is kept. */
    async selectAiHunks() {
      const d = this.dialog, a = d?.aiEdit, review = a?.result?.review;
      if (!a || a.pending || this.busy || !this.aiEditPartial(a) || !a.keep.length || review?.review_state !== "pending") return;
      a.pending = true; a.error = "";
      try {
        const result = await api("/api/ai/edit-select", { method: "POST",
          body: JSON.stringify({ review_id: review.review_id, body: a.body, accepted: [...a.keep] }) });
        if (this.dialog !== d) { await this.retireAiEdit(result); return; }
        a.result = { ...a.result, ...result };
        a.keep = (result.hunks || []).map(h => h.id);
      } catch (error) { if (this.dialog === d) a.error = this.friendly(error.message); }
      finally { a.pending = false; }
    },
    async applyAiEdit() {
      const d = this.dialog, a = d.aiEdit, e = this.edit, review = a.result?.review;
      if (!e || this.busy || a.pending || review?.review_state !== "pending" || !review.validation?.valid) return;
      if (this.aiEditPartial(a)) return;
      if (e.copy !== a.target || a.key !== JSON.stringify(this.aiEditInput(true))) return;
      this.busy = true; a.error = "";
      try {
        const committed = await api(`/api/source-updates/reviews/${encodeURIComponent(review.review_id)}/commit`, {
          method: "POST", body: JSON.stringify({ name: a.name, scope: a.target.scope, target_path: a.target.path, approve: true }),
        });
        this.dialog = null;
        e.body = e.baseBody = a.result.proposed;
        e.targets = [a.target.scope];
        await this.refresh();
        const installed = this.editTargets.find((copy) => copy.path === a.target.path && copy.scope === a.target.scope);
        e.copy.hash = installed?.hash || "";
        if (installed) e.initialTargets[installed.scope] = this.bodyKey(installed);
        this.toast(committed.warning || "AI edit saved. The previous folder is available in Trash & backups.");
        this.$nextTick(() => { this.growArea(); this.$refs.edbody?.focus(); });
      } catch (error) { a.error = this.friendly(error.message); }
      finally { this.busy = false; }
    },
    async cancelEdit() {
      if (this.editDirty) return this.openDialog({ title: "Discard your changes?", lines: [`You have unsaved changes to “${this.edit.name}”.`], cancel: "Keep editing", confirm: "Discard changes", danger: true, onConfirm: () => { this.edit = null; this.showSkillView(); } });
      this.edit = null; this.showSkillView(); return null;
    },
    editPlaceChanged(scope) {
      const place = this.editPlaces.get(scope);
      return !place || place.evidence !== this.edit.initialTargets[scope];
    },
    async checkEditTarget(draft, scope) {
      const record = await api(`/api/skills/${encodeURIComponent(draft.name)}?scope=${encodeURIComponent(scope)}`);
      const path = record?.physical_path || record?.path;
      const key = this.bodyKey({ name: draft.name, scope, path, hash: record?.content_hash });
      if (key !== draft.initialTargets[scope] || record.disabled || record.read_only || record.malformed) {
        throw new Error("This skill changed on disk in " + this.agentOf(scope).name + ". Your draft is still open.");
      }
    },
    editFields(draft, different) {
      const fields = {};
      if (different || draft.desc !== draft.baseDesc) fields.description = draft.desc;
      if (different || draft.body !== draft.baseBody) fields.body = draft.body;
      for (const key of Object.keys(draft.metadata)) {
        if (different || draft.metadata[key] !== draft.baseMetadata[key]) fields[key] = draft.metadata[key];
      }
      return fields;
    },
    async saveNewEditCopies(draft, places, { changed, saved, warnings }) {
      const { path, hash } = draft.copy;
      const destinations = Object.fromEntries(places.map(({ scope, root }) => [scope, root]));
      const edit = { ...this.editFields(draft, false), expected: { path, content_hash: hash }, destinations };
      const result = await api("/api/sync", { method: "POST", body: JSON.stringify({
        name: draft.name, from_scope: draft.copy.scope, to_scopes: places.map(({ scope }) => scope), edit,
      }) });
      const synced = new Set(result.synced);
      const failed = [];
      for (const { scope, agent } of places) {
        if (!synced.has(scope)) { failed.push(agent.name); continue; }
        changed.push(scope);
        const receipt = result.installed?.[scope];
        if (receipt?.path && receipt.tree_hash) saved.push({ scope, path: receipt.path, treeHash: receipt.tree_hash });
        if (receipt?.warning) warnings.push(this.friendly(receipt.warning));
      }
      if (failed.length) throw new Error(`Couldn’t add ${draft.name} in ${join(failed)}. Your draft is still open.`);
    },
    async saveEdit() {
      /* Same guard as the Save button: Ctrl/Cmd+S must not save to zero
       * targets (which discarded the edit), save nothing, or save twice. */
      const e = this.edit;
      if (!e || this.editError || this.busy || !e.targets.length || !this.editDirty || this.editTargetChanged) return;
      const additions = [...this.editPlaces.values()].filter(({ scope, copy }) => !copy && e.targets.includes(scope));
      const targets = this.editTargets.filter(({ scope }) => e.targets.includes(scope));
      if (additions.length + targets.length !== e.targets.length) return;
      const writes = targets.map((copy) => ({ scope: copy.scope, path: copy.path, hash: copy.hash,
        fields: this.editFields(e, copy.hash !== e.copy.hash) }));
      this.busy = true;
      e.error = "";
      const outcome = { saved: [], changed: [], warnings: [] };
      const { saved, changed } = outcome;
      try {
        await Promise.all(writes.map(({scope}) => this.checkEditTarget(e, scope)));
        // Keep the original source available for retry if an addition fails.
        if (additions.length) await this.saveNewEditCopies(e, additions, outcome);
        for (const { scope, path, hash, fields } of writes) {
          const url = `/api/skills/${encodeURIComponent(e.name)}?scope=${encodeURIComponent(scope)}`;
          const result = await api(url, { method: "PATCH", body: JSON.stringify({ ...fields, expected: { path, content_hash: hash } }) });
          if (result?.changed === false) continue;
          changed.push(scope);
          if (result?.snapshot && result.content_hash) {
            const evidence = this.bodyKey({ name: e.name, scope, path, hash: result.content_hash });
            saved.push({ scope, snapshot: result.snapshot, evidence, path, hash: result.content_hash });
          }
        }
        this.edit = null;
        this.showSkillView();
        this.reportEditResult(e, outcome);
      } catch (error) {
        e.targets = e.targets.filter((scope) => !changed.includes(scope));
        e.error = this.friendly(error.message);
        this.reportEditResult(e, outcome, e.error);
      } finally {
        await this.refresh();
        this.busy = false;
      }
    },
    reportEditResult(draft, { changed, saved, warnings }, error = "") {
      const initialTargets = Object.fromEntries(saved.map(({ scope, evidence }) => [scope, evidence]));
      const undo = saved.length ? async () => {
        const outcomes = await Promise.allSettled(saved.map(async ({ scope, snapshot, path, hash, treeHash }) => {
          const name = encodeURIComponent(draft.name), destination = encodeURIComponent(scope);
          if (treeHash) {
            const result = await api(`/api/skills/${name}?scope=${destination}`,
              { method: "DELETE", body: JSON.stringify({ expected: { path, tree_hash: treeHash } }) });
            return result?.warning;
          } else {
            await this.checkEditTarget({ name: draft.name, initialTargets }, scope);
            await api(`/api/trash/${name}?snapshot=${encodeURIComponent(snapshot)}&scope=${destination}`,
              { method: "POST", body: JSON.stringify({ expected: { path, content_hash: hash } }) });
          }
        }));
        const failed = saved.filter((_, index) => outcomes[index].status === "rejected");
        const warnings = outcomes.filter(({ status, value }) => status === "fulfilled" && value).map(({ value }) => value);
        if (failed.length) warnings.push(`Check ${join(failed.map(({ scope }) => this.agentOf(scope).name))} for changes.`);
        if (warnings.length) throw new Error(warnings.join(" "));
      } : null;
      const message = changed.length ? `${draft.name} saved to ${plural(changed.length, "place")}.` : error ? "" : "No file changed.";
      const recovery = changed.length !== saved.length ? " Undo is unavailable for some saved copies." : "";
      this.toast([message + recovery, ...warnings, error].filter(Boolean).join(" "), { undo, err: !!error });
    },
    growArea() { const a = this.$refs.edbody; if (a) { a.style.height = "auto"; a.style.height = Math.max(420, a.scrollHeight + 4) + "px"; } },
    insertText(prefix) {
      const a = this.$refs.edbody; if (!a) return;
      const at = a.selectionStart, ls = this.edit.body.lastIndexOf("\n", at - 1) + 1;
      this.edit.body = this.edit.body.slice(0, ls) + prefix + this.edit.body.slice(ls);
      this.$nextTick(() => { a.focus(); a.setSelectionRange(at + prefix.length, at + prefix.length); });
    },
    wrapText(mark) {
      const a = this.$refs.edbody; if (!a) return;
      const s = a.selectionStart, e2 = a.selectionEnd, b = this.edit.body;
      this.edit.body = b.slice(0, s) + mark + b.slice(s, e2) + mark + b.slice(e2);
      this.$nextTick(() => { a.focus(); a.setSelectionRange(s + mark.length, e2 + mark.length); });
    },

    /* ----- sync map ----- */
    mapComparison(skill, copy) {
      if (!copy.hash) return "";
      if (skill.ref.ambiguous) return "Copies differ (no majority)";
      return skill.ref.hash && copy.hash !== skill.ref.hash ? "Different copy" : "";
    },
    needsMapReview(skill, scopes) {
      const seen = new Set();
      for (const copy of skill.copies) {
        if (!scopes.has(copy.scope)) continue;
        if (seen.has(copy.scope) || copy.state === "broken" || copy.state === "link" || this.mapComparison(skill, copy)) return true;
        seen.add(copy.scope);
      }
      return false;
    },
    mapCell(skill, scope) {
      const copies = skill.copies.filter((copy) => copy.scope === scope);
      if (copies.length !== 1) {
        return copies.length ? { state: "warn", label: "Multiple copies listed" } : { state: "missing", label: MAP_STATES.missing.label };
      }
      const [copy] = copies;
      if (copy.state === "broken") return { state: "bad", label: MAP_STATES.bad.label, copy };
      if (copy.state === "link") return { state: "link", label: "Link target not inspected", copy };
      const comparison = this.mapComparison(skill, copy);
      const label = copy.state === "off" ? MAP_STATES.off.label : copy.readOnly ? "Linked copy (read-only)" : MAP_STATES.on.label;
      const state = comparison ? "warn" : copy.state === "off" ? "off" : copy.readOnly ? "link" : "on";
      const detail = comparison || (copy.hash && skill.ref.holders.length > 1 ? "Document text matches the reference" : "");
      return { state, label: detail ? `${label} · ${detail}` : label, copy };
    },
    tagFor(inf) {
      return inf.key === "bad" ? `${plural(inf.broken.length, "skill")} can't be read` : inf.key === "warn" ? `${plural(inf.differing.length, "copy", "copies")} ${inf.differing.length === 1 ? "differs" : "differ"}` : "No copy differences flagged";
    },
    selectMap(id, event, name = "") {
      if (id !== this.mapConfirm) this.mapConfirm = "";
      if (id !== this.mapSelId || name !== this.mapSkillName) {
        this.mapPicked = name ? [] : this.mapDefaults(id);
        this.peek = null;
      }
      this.mapSelId = id;
      this.mapSkillName = name;
      this.mapOrigin = event.currentTarget;
      this.$nextTick(() => this.$refs.mapHeading?.focus());
    },
    backToMap() {
      const target = this.mapOrigin?.isConnected ? this.mapOrigin : this.$refs.mapSearch;
      target?.focus();
    },
    resetMapPage() {
      this.mapPage = 0;
      if (this.$refs.matrix) this.$refs.matrix.scrollTop = 0;
    },
    moveMapPage(step) {
      this.mapPage = this.mapPageIndex + step;
      this.$refs.matrix.scrollTop = 0;
      this.$refs.matrix.focus();
    },
    mapSyncable(skill, scope) {
      const cell = this.mapCell(skill, scope);
      return this.agentOf(scope).writable && !!cell.copy && !cell.copy.readOnly && !skill.ref.ambiguous;
    },
    mapDefaults(id) {
      const info = this.m.info(id);
      return info ? info.differing.slice(0, 12).filter((s) => this.mapSyncable(s, id)).map((s) => s.name) : [];
    },
    togglePick(n) { this.mapPicked = this.mapPicked.includes(n) ? this.mapPicked.filter((x) => x !== n) : [...this.mapPicked, n]; },
    togglePeek(skill) {
      this.peek = this.peek === skill.name ? null : skill.name;
      if (this.peek) this.$nextTick(() => {
        document.querySelector("#map-comparison .copy-compare-head")?.scrollIntoView({ block: "nearest" });
      });
      return this.ensureBodies(this.mapComparePair);
    },
    brokenShort(s, scope) { const c = s.copies.find((x) => x.scope === scope); return (BROKEN_WHY[c && c.kind] || BROKEN_WHY.invalid)[0]; },
    async syncPicked() {
      const inf = this.mapSel;
      if (this.busy || !inf) return;
      const picked = this.mapSelected;
      if (!picked.length) return;
      const detailName = this.mapSkillName;
      const results = [];
      let failure = "";
      this.busy = true;
      try {
        for (const s of picked) {
          try {
            const result = await this.doSync(s.name, s.ref.holders[0].scope, [inf.id]);
            results.push({ ...result, name: s.name });
          } catch (e) {
            failure = ` Sync stopped at ${s.name}. ${this.friendly(e.message)}`;
            break;
          }
        }
        const undo = this.undoFor("", results);
        await this.refresh();
        if (this.mapSel?.id === inf.id && this.mapSkillName === detailName) this.mapPicked = [];
        const ok = results.filter((r) => r.synced.length).length;
        const summary = ok ? `${plural(ok, "skill")} now ${ok === 1 ? "matches" : "match"} in ${inf.agent.name}.` : "No skills were confirmed as synced.";
        const skipped = results.flatMap((r) => r.skipped);
        const recovery = results.some((r) => r.manualRecovery) ? " Use your backup or retained snapshots for recovery." : "";
        this.toast(summary + this.skipText(skipped) + failure + recovery + Domain.syncRecoveryNotice(results),
          { err: !!failure || !!skipped.length, undo,
            undoText: "Undone. Text and on/off state restored. Supporting files are unchanged." });
      } finally { this.busy = false; }
    },

    openInboxFor(skillName) {
      const issue = this.tableProblems.find((item) => item.name === skillName && item.type !== "unreadable");
      Router.go(Router.routeHref("attention", { item: issue?.id }));
    },
    reviewProblemHref(problem) {
      if (problem.noteOnly) return Router.skillHref(problem.skill);
      if (problem.key === "info") return Router.toolHref("quality");
      return Router.routeHref("attention", { item: problem.id });
    },
    applyRouteOptions(route, previous) {
      if (route.page === "skills") {
        if (route.view === "instances") this.libraryView = "instances";
        const hasFilters = (r) => r?.page === "skills" && [r.search, r.agent, r.only].some((value) => value != null);
        if (hasFilters(route) || hasFilters(previous)) {
          this.pickAgent(route.agent || "all", route.search || "");
          if (route.only === "problems") this.filter = "care";
        }
      } else if (route.page === "map" && route.search != null) {
        this.mapQuery = route.search;
      }
    },
    showRouteScreen() {
      const next = this.route;
      this.updatePageTitle();
      if (!this.m || this.routeAction === next.href) return;
      this.routeAction = next.href;
      if (next.screen === "edit" && this.canEdit && !this.edit) {
        this.openRouteEditor(next.href);
      }
    },
    async openRouteEditor(href) {
      try {
        await this.startEdit();
      } finally {
        if (this.route.href === href && this.routeAction === href && !this.edit) this.routeAction = "";
      }
    },
    updatePageTitle() {
      const missing = this.m && this.route.page === "skill" && !this.skill;
      document.title = (missing ? "Page not found" : Router.title(this.route)) + " · Jackfield";
    },
    needsRouteConfirmation(next) {
      const draft = this.$refs.newSkill;
      if (draft?.dirty) {
        return { title: "Discard this skill draft?", lines: ["The draft is still open."],
          cancel: "Keep editing", confirm: "Discard draft", onConfirm: () => { draft.finish(); Router.go(next.href); } };
      }
      if (this.editDirty && !(next.page === "skill" && next.name === this.edit.name && next.screen === "edit")) {
        return { title: "Discard your changes?", lines: ["You have unsaved changes to “" + this.edit.name + "”."],
          cancel: "Keep editing", confirm: "Discard changes", onConfirm: () => { this.edit = null; Router.go(next.href); } };
      }
      if (this.route.page === "tracking" && this.route.name && this.trackFormDirty &&
          !(next.page === "tracking" && next.name === this.route.name)) {
        return { title: "Discard what you typed?", lines: ["What you typed here won't be saved."],
          cancel: "Keep editing", confirm: "Discard", onConfirm: () => { this.trackForm = null; Router.go(next.href); } };
      }
      return null;
    },
    changeRoute(next) {
      if (next.href === this.route.href) { Router.replace(next.href); return; }
      if (this.$refs.newSkill?.writing || (this.busy && this.edit)) { Router.replace(this.route.href); return; }
      if (this.dialog?.form && (this.busy || this.createDraftDirty())) {
        Router.replace(this.route.href);
        if (!this.busy) this.reviewCreateDiscard(next.href);
        return;
      }
      const guard = this.needsRouteConfirmation(next);
      if (guard) { Router.replace(this.route.href); this.openDialog(guard); return; }
      Router.replace(next.href);
      this.closeDialog(false);
      if (next.screen !== "edit" || next.name !== this.route.name) this.edit = null;
      this.resetScreenFeedback(next);
      this.mapMenu = ""; this.projectMenu = false;
      this.tableStopAgent = "";
      this.tableMode = ""; this.tableVersion = ""; this.tableError = null;
      if (next.page !== "map") this.mapConfirm = "";
      const previous = this.route;
      if (next.page === "tracking" && (previous.page !== next.page || previous.name !== next.name)) {
        this.openTrackForm(next.name);
      }
      this.route = next;
      this.applyRouteOptions(next, previous);
      this.loadSkillHistory();
      this.primeBodies();
      if (next.page === "recovery") this.loadAgentTrash();
      window.scrollTo(0, 0);
      if (next.screen !== "new") this.focusH1();
      this.showRouteScreen();
    },
    resetScreenFeedback(next) {
      const previous = this.route;
      if (["page", "name", "screen", "tool", "view"].some((key) => next[key] !== previous[key])) {
        this.leaveScreen(next.href);
      }
      if (previous.page === "inbox" && next.page !== "inbox") this.clearAttentionReview();
      if (previous.page === "recovery" && next.page !== "recovery") {
        this.restoredTrash = null;
        this.importFile = null;
        this.importReject = "";
        this.exportError = "";
        this.clearImportReview();
      }
    },
  },
  mounted() {
    this.refresh();
    Router.replace(this.route.href);
    this.applyRouteOptions(this.route);
    Router.onChange((next) => this.changeRoute(next));
    window.addEventListener("beforeunload", (e) => {
      if (this.editDirty || this.trackFormDirty || this.createDraftDirty() || this.$refs.newSkill?.dirty || this.$refs.newSkill?.writing) {
        e.preventDefault(); e.returnValue = "";
      }
    });
    document.addEventListener("keydown", (e) => {
      const t = e.target, typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      const onControl = t && t.closest && t.closest("a, button, input, select, textarea, summary, [role=button], [contenteditable]");
      if (e.defaultPrevented || this.tableSheetOpen || document.querySelector("dialog[open]")) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==="k" && !this.dialog && !document.querySelector("dialog[open]")) {e.preventDefault();this.openCommands();}
      if (e.key === "?" && !typing && !onControl && !this.dialog) { e.preventDefault(); this.openHelp(); }
      if (e.key === "/" && !typing && !onControl && !this.dialog && !e.ctrlKey && !e.metaKey) { e.preventDefault(); this.openCommands(); }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s" && this.edit) { e.preventDefault(); if (!this.dialog) this.saveEdit(); }
      if (this.route.page === "inbox" && !typing && !onControl && !this.dialog &&
          !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey && !e.isComposing) {
        const key = e.key.toLowerCase();
        const inScope = !t || t === document.body || t.closest?.("#main");
        if (inScope && ["j", "k", "f"].includes(key)) {
          e.preventDefault();
          if (key !== "f") this.attentionMove(key === "j" ? 1 : -1);
          else if (!e.repeat) this.attentionFix();
        }
      }
    });
    this.updatePageTitle();
    this.watchTrackMenus();
    window.addEventListener("storage",event=>{if(["skillsmgr-theme","skillsmgr-text-size","skillsmgr-locale"].includes(event.key))this.preferencesChanged();});
    this.loadSkillHistory();
    this.applyTheme();
    /* The filesystem is the source of truth and other tools edit it, so re-read
     * it whenever the tab comes back into view (at most every 15 s, never
     * while an edit is open so a refresh cannot disturb unsaved work). */
    let lastLoad = Date.now();
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "visible" || this.edit || this.busy || Date.now() - lastLoad < 15000) return;
      lastLoad = Date.now(); this.refresh({ observe: this.route.page === "skills" && !this.route.view });
    });
    if (window.matchMedia) {
      const tablet = window.matchMedia("(width < 900px)");
      const setTableWidth = () => { this.tableNarrow = tablet.matches; };
      setTableWidth(); tablet.addEventListener("change", setTableWidth);
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const on = () => { if (this.theme === "system") this.applyTheme(); };
      if (mq.addEventListener) mq.addEventListener("change", on); else if (mq.addListener) mq.addListener(on);
    }
  },
  updated() { if (this.edit && this.edit.tab === "write") this.growArea(); },
});

app.component("ic", {
  props: { name: String, cls: { type: String, default: "" } },
  computed: { path() { return PATHS[this.name] || PATHS.info; } },
  template: '<svg :class="[\'i\', cls]" viewBox="0 0 24 24" aria-hidden="true" v-html="path"></svg>',
});
app.component("logo", {
  props: { agent: Object, size: { type: String, default: "" } },
  /* The visible agent name also labels the decorative mark or initials. */
  template: '<span :class="[\'logo\', size]" aria-hidden="true">'
    + '<span v-if="agent.mark" class="agm" :data-a="agent.mark"></span>'
    + '<span v-else>{{ agent.initials }}</span></span>',
});

app.component("listing-budgets", {
  props: { records: Array, locale: { type: String, default: "system" } },
  data() { return { report: null, loading: false, error: "", generation: 0 }; },
  computed: {
    sections() {
      return [["claude_listing", "Claude Code", "chars"], ["codex_listing", "Codex", "tokens"]].flatMap(([key, label, unit]) => {
        const section = this.report && this.report[key];
        if (!section || !section.instances_observed) return [];
        const budget = section.budget || {};
        const statuses = { within_budget: "Within the estimated budget", over_budget_estimate: "Over the estimated budget", no_instances: "No model-visible entries" };
        const unknown = !Object.prototype.hasOwnProperty.call(statuses, section.status);
        const metadataUnknown = Number((section.unknown_metadata || {}).total || 0) > 0;
        const status = unknown ? (metadataUnknown ? "Listing unknown: invocation metadata unreadable" : "Budget unknown") : statuses[section.status];
        return [{ key, label, unit, used: unit === "chars" ? section.listing_chars : section.listing_tokens_estimate,
          budget: unknown && !metadataUnknown ? null : unit === "chars" ? budget.budget_chars_estimate : budget.budget_tokens,
          subtotal: metadataUnknown,
          basis: budget.basis || "Budget basis unavailable",
          cuts: (section.largest_cuts || section.entries || []).filter((e) => Number(e.cut_chars) > 0)
            .sort((a, b) => Number(b.cut_chars) - Number(a.cut_chars) || String(a.name).localeCompare(String(b.name))).slice(0, 20),
          thin: (section.entries || []).filter((e) => e.thin).map((e) => e.name).sort(),
          status, partial: section.confidence === "partial", over: section.status === "over_budget_estimate",
          fill: !unknown && Number(unit === "chars" ? budget.budget_chars_estimate : budget.budget_tokens) > 0
            ? Math.min(100, Math.max(1.5, 80 * Number(unit === "chars" ? section.listing_chars : section.listing_tokens_estimate) / Number(unit === "chars" ? budget.budget_chars_estimate : budget.budget_tokens))) : null }];
      });
    },
  },
  watch: { records: { immediate: true, handler() { this.load(); } } },
  beforeUnmount() { this.generation++; },
  methods: {
    fmtN(value) { return Domain.numberFormatter(this.locale === "system" ? undefined : this.locale).format(Number(value || 0)); },
    async load() {
      const generation = ++this.generation;
      this.loading = true; this.error = ""; this.report = null;
      try {
        const envelope = await api("/api/doctor?scope=all&hygiene=1");
        if (generation !== this.generation) return;
        if (!envelope || !envelope.hygiene) throw new Error("No listing evidence returned");
        const { claude_listing, codex_listing } = envelope.hygiene;
        if (!claude_listing || !codex_listing) throw new Error("Incomplete listing evidence");
        this.report = markRaw({ claude_listing, codex_listing });
      } catch (e) {
        if (generation === this.generation) this.error = "Couldn't read listing estimates. Retry, or open Tools → Quality.";
      } finally {
        if (generation === this.generation) this.loading = false;
      }
    },
  },
  template: `<section class="card" aria-label="Skill listing budgets" :aria-busy="loading">
    <h2>Skill listing budgets</h2>
    <p class="sub">Names and descriptions shown to the model. Estimates; agent loading is not verified.</p>
    <p class="sub" v-if="loading" role="status">Reading listing estimates…</p>
    <p class="state-note err" v-else-if="error" role="alert">{{ error }} <button type="button" class="btn btn-line btn-sm" @click="load()">Retry listing estimates</button></p>
    <template v-else>
      <div class="listing-budget" v-for="section in sections" :key="section.key">
        <h3>{{ section.label }} <span v-if="section.over" class="pill warn lb-pill">Over</span></h3>
        <p class="num lb-num"><template v-if="section.subtotal">Known subtotal: </template>~{{ fmtN(section.used) }} {{ section.unit === "chars" ? "characters" : "tokens" }}<template v-if="section.budget != null"> of ~{{ fmtN(section.budget) }}</template></p>
        <div class="track" v-if="section.fill != null" role="img" :aria-label="section.status"><i :class="{ warn: section.over }" :style="{ width: section.fill + '%' }"></i><span class="lim" style="left:80%"></span></div>
        <p class="sub">{{ section.status }}{{ section.partial ? ", from partial evidence" : "" }}.</p>
        <details class="listing-cuts"><summary>How this is estimated</summary><p class="sub">{{ section.basis }}</p></details>
        <details v-if="section.cuts.length" class="listing-cuts"><summary>{{ section.cuts.length }} description{{ section.cuts.length === 1 ? "" : "s" }} cut before the model sees {{ section.cuts.length === 1 ? "it" : "them" }}</summary>
          <ul><li v-for="e in section.cuts" :key="e.name"><span class="mono">{{ e.name }}</span> loses {{ fmtN(e.cut_chars) }} of {{ fmtN(e.description_chars) }} characters</li></ul></details>
        <details v-if="section.thin.length" class="listing-cuts"><summary>{{ section.thin.length }} description{{ section.thin.length === 1 ? " is" : "s are" }} too short to route on</summary>
          <p class="sub">Under 20 characters, the model has almost nothing to choose {{ section.thin.length === 1 ? "this skill" : "these skills" }} by.</p>
          <ul><li v-for="n in section.thin.slice(0, 20)" :key="n"><span class="mono">{{ n }}</span></li></ul></details>
      </div>
      <p class="sub" v-if="!sections.length">No Claude Code or Codex listing instances observed.</p>
      <a class="see-all" href="#/advanced/quality">Review listing evidence <ic name="arrow" cls="i-s"></ic></a>
    </template>
  </section>`,
});

app.component("library-tools", window.SkillsV2LibraryTools);
app.component("copy-comparison", {
  props: {
    evidence: { type: Object, required: true },
    fromLabel: { type: String, required: true },
    toLabel: { type: String, required: true },
    reload: { type: Function, required: true },
  },
  data() { return { unified: false, retrying: false }; },
  computed: {
    errors() { return this.evidence.copies.filter((copy) => copy.error); },
    preview() { return this.evidence.preview; },
  },
  methods: {
    async retry() {
      if (this.retrying) return;
      this.retrying = true;
      try { await this.reload(); }
      finally {
        this.retrying = false;
        await this.$nextTick();
        if (document.activeElement === document.body) (this.$refs.retryButton || this.$refs.heading)?.focus();
      }
    },
  },
  template: `<section class="copy-compare" aria-label="Document comparison">
    <header class="copy-compare-head">
      <h3 tabindex="-1" ref="heading">Document comparison</h3>
      <button v-if="preview?.status === 'changes'" class="btn btn-line btn-sm compare-layout" type="button"
        :aria-pressed="unified" @click="unified = !unified">Unified view</button>
    </header>
    <dl class="compare-identities">
      <div v-for="(copy, index) in evidence.copies" :key="index">
        <dt>{{ index === 0 ? fromLabel : toLabel }}</dt>
        <dd><b>{{ copy.scope }}</b><code v-if="copy.path" translate="no">{{ copy.path }}</code></dd>
      </div>
    </dl>
    <p class="compare-coverage">Preview covers SKILL.md text. Supporting files haven’t been compared here.</p>
    <div v-if="errors.length" class="compare-error">
      <ul role="alert"><li v-for="copy in errors" :key="copy.scope"><b>{{ copy.scope }}.</b> {{ copy.error }}</li></ul>
      <button type="button" class="btn btn-line btn-sm" ref="retryButton" :disabled="retrying" @click="retry()">{{ retrying ? 'Reading…' : 'Retry comparison' }}</button>
    </div>
    <p v-else-if="!preview" class="compare-status" role="status">Reading both documents…</p>
    <p v-else-if="preview.status === 'too-large'" class="compare-status" role="status">These documents exceed the comparison preview limit. Open the individual copies to review their text.</p>
    <p v-else-if="preview.status === 'same'" class="compare-status" role="status">The returned document text matches.</p>
    <p v-else-if="preview.status === 'line-endings'" class="compare-status" role="status">Only line endings differ in the returned text.</p>
    <template v-else>
      <ul :class="['compare-lines', { unified }]" aria-label="Changed lines with context">
        <li v-for="(row, index) in preview.rows" :key="index" class="compare-row" :class="{ 'compare-context': row.context }">
          <template v-for="side in ['before', 'after']" :key="side">
            <div :class="['compare-line', side, row[side]?.kind || 'gap']" :aria-hidden="row[side] ? null : 'true'">
              <template v-if="row[side]">
                <span class="sr-only">{{ row[side].kind === 'del' ? 'Removed, original line ' : row[side].kind === 'add' ? 'Added, new line ' : 'Context, line ' }}</span>
                <span class="compare-number num">{{ row[side].number }}</span>
                <span class="compare-sign" aria-hidden="true">{{ row[side].kind === 'del' ? '−' : row[side].kind === 'add' ? '+' : '' }}</span>
                <code translate="no">{{ row[side].text }}</code>
              </template>
            </div>
          </template>
        </li>
      </ul>
      <p v-if="preview.omitted" class="compare-status">Showing the first {{ preview.rows.length }} rows. {{ preview.omitted }} more rows omitted.</p>
      <ai-copy-brief :rows="preview.rows" :from-label="fromLabel" :to-label="toLabel"></ai-copy-brief>
    </template>
  </section>`,
});
app.component("section-jumps", {
  props: { sections: { type: Array, required: true } },
  methods: {
    jumpTo(id) {
      // The page address already uses the fragment for routing.
      const heading = document.getElementById(id);
      if (!heading) return;
      heading.focus({ preventScroll: true });
      heading.scrollIntoView({ block: "start" });
    },
  },
  template: `<div class="section-jumps" role="group" aria-label="On this page">
    <span aria-hidden="true">On this page</span>
    <button v-for="[id, label] in sections" :key="id" type="button" class="btn btn-line btn-sm" @click="jumpTo(id)">{{ label }}</button>
  </div>`,
});
app.component("tool-center", window.SkillsV2ToolCenter);
app.component("ai-center", window.SkillsV2AiCenter);
app.component("ai-briefing", window.SkillsV2AiBriefing);
app.component("ai-compare", window.SkillsV2AiCompare);
app.component("trial-stats", window.SkillsV2TrialStats);
app.component("ai-copy-brief", window.SkillsV2AiCopyBrief);
app.component("ai-diagnostic", window.SkillsV2AiDiagnostic);

Jack.install(app);
app.mount("#app");
