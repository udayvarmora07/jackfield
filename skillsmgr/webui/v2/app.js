/* Skills Manager v2 — Vue 3 application (no build step).
 * Same transport, same backend and same observed-state vocabulary as the
 * classic interface; only the presentation and the workflow framing differ. */
"use strict";

const Domain = window.SkillManagerDomain;
const Model = window.SkillsV2Model;
if (!Domain || !Model) {
  const failure = document.createElement("div");
  failure.setAttribute("role", "alert");
  failure.style.cssText = "margin:2rem;padding:1rem;border:1px solid #b42318;border-radius:8px;font:15px/1.5 system-ui,sans-serif;color:#b42318;background:#fff;";
  failure.textContent = "Skills Manager could not start: a script did not load. Reload the page; if it persists, the installed files are incomplete.";
  document.body.appendChild(failure);
  throw new Error("v2 scripts missing");
}

const { api } = Domain;
const { createApp, markRaw } = Vue;
const { plural, join, words, titleCase, shortPath, BROKEN_WHY, documentPreview, renderDoc, stripFrontmatter, validName, toolIds, toolItems } = Model;

/* ---------- Icons (constant, trusted markup) ---------- */
const PATHS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
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
const FALLBACK_AGENT = { id: "", name: "Unknown", color: "#55585f", initials: "?", path: "" };
const MAP_STATES = {
  on: { icon: "ok", label: "Enabled on disk" },
  warn: { icon: "warn", label: "Copies differ" },
  bad: { icon: "bad", label: "Can't be read" },
  off: { icon: "off", label: "Turned off on disk" },
  link: { icon: "share", label: "Linked copy" },
  missing: { icon: "dash", label: "No copy listed" },
};

function parseRoute() {
  const h = location.hash.replace(/^#\/?/, "");
  const [p, ...rest] = h.split("/");
  if (p === "skill" && rest.length) { try { return { page: "skill", name: decodeURIComponent(rest.join("/")) }; } catch (e) { return { page: "skills" }; } }
  if (p === "tools") return { page: "tools", tool: toolIds.includes(rest[0]) ? rest[0] : "tools" };
  return ["skills", "map", "inbox", "recovery"].includes(p) ? { page: p } : { page: "home" };
}
const TITLES = { home: "Home", skills: "Skills", map: "Sync map", inbox: "Inbox", recovery: "Recovery", tools: "Tools" };
const THEMES = ["system", "light", "dark"];
function savedPreference(key, choices, fallback) {try{const value=localStorage.getItem(key);return choices.includes(value)?value:fallback;}catch(e){return fallback;}}

const app = createApp({
  data() {
    return { refreshGen: 0, historyGen: 0, catalogGen: 0, trashGen: 0, agentTrashGen: 0,
      route: parseRoute(), m: null, loading: true, loadError: "", history: [], busy: false,
      records: [], scopes: [], catalog: {tags:{}, profiles:{}}, catalogError: "", tagFilter: "", libraryView: savedPreference("skillsmgr-v2-library-view",["shelf","instances"],"shelf"), density: savedPreference("skillsmgr-v2-density",["comfortable","compact"],"comfortable"), toolTarget: null, sourceReviewHandoff: null, readCopyPath: "", readCopyScope: "", readCopyName: "",
      historyError: "", skillHistoryError: "", trashError: "", trashLoading: false, importFull: false, importResult: null, createTemplates: [], commandQuery: "",
      exportPending: false, exportError: "",
      query: "", filter: "all", agentFilter: "all", extra: {}, sortBy: "name",
      front: null, skipped: [], dismissed: [], done: 0, srcChoice: "", inboxComparisonScope: "",
      bodies: {}, bodyInflight: {}, bodyErrors: {},
      treeQuery: "", edit: null, highlight: true, compareWith: "",
      mapSelId: "", mapPicked: [], peek: null,
      mapQuery: "", mapReviewOnly: false, mapPage: 0, mapSkillName: "", mapOrigin: null,
      trash: [], agentTrash: [], agentTrashErrors: [], agentTrashLoading: false, importFile: null, importReject: "", importError: "", dropDepth: 0, importForce: false,
      theme: savedPreference("skillsmgr-theme",THEMES,"system"),formatLocale:savedPreference("skillsmgr-locale",["system","en-US","en-GB","en-IN"],"system"),
      dialog: null, toasts: [], live: "", toastSeq: 0, skillHistory: [], opener: null,
    };
  },
  computed: {
    inboxCount() { return this.m ? this.queue.length : 0; },
    inboxLabel() { return this.inboxCount ? "Inbox, " + plural(this.inboxCount, "item") : "Inbox"; },
    agentInfos() { return this.m ? this.m.infos.filter((i) => !i.agent.library) : []; },
    sharedSkills() { return this.m ? [...this.m.skills].sort((a, b) => b.tools.length - a.tools.length || a.name.localeCompare(b.name)).slice(0, 3) : []; },
    /* Categories only help when the skills actually carry them; otherwise the
     * shelf falls back to an alphabet, which is what people can scan. */
    grouping() { return this.m && new Set(this.m.skills.map((s) => s.category).filter(Boolean)).size > 1 ? "category" : "letter"; },
    filterChoices() {
      const sk = this.m ? this.m.skills : [];
      return [
        { id: "all", label: "All", n: sk.filter((s) => s.status.key !== "note").length },
        { id: "care", label: "Needs care", n: this.careCount },
        { id: "off", label: "Turned off", n: sk.filter((s) => s.status.key === "off").length },
      ];
    },
    shelfTotal() { return this.m ? this.m.skills.filter((s) => s.status.key !== "note").length : 0; },
    careCount() { return this.m ? this.m.skills.filter((s) => s.status.key === "warn" || s.status.key === "bad").length : 0; },
    catalogTags() { return [...new Set(Object.values(this.catalog.tags || {}).flat())].sort(); },
    visibleNames() { return this.visible.map(s => s.name); },
    commandChoices() {const items=[{label:"New skill",action:"create"},{label:"Refresh files",action:"refresh"},{label:"Skills",path:"#/skills"},...toolItems.filter((item)=>item.commandLabel).map((item)=>({label:item.commandLabel,path:"#/tools/"+item.id})),{label:"Recovery and history",path:"#/recovery"}];return items.filter(item=>item.label.toLowerCase().includes(this.commandQuery.toLowerCase()));},
    visible() {
      if (!this.m) return [];
      const q = this.query.trim().toLowerCase();
      return this.m.skills.filter((s) => {
        const k = s.status.key;
        if (k === "note") return false; /* not a skill: listed in the Inbox only */
        if (this.filter === "care" && k !== "warn" && k !== "bad") return false;
        if (this.filter === "off" && k !== "off") return false;
        if (this.agentFilter !== "all" && !s.copies.some((c) => c.scope === this.agentFilter)) return false;
        const tags = (this.catalog.tags || {})[s.name] || [];
        if (this.tagFilter === "__untagged" && tags.length) return false;
        if (this.tagFilter && this.tagFilter !== "__untagged" && !tags.includes(this.tagFilter)) return false;
        return !q || `${s.name} ${s.description} ${s.category}`.toLowerCase().includes(q);
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
    skill() { return this.m && this.route.page === "skill" ? this.m.byName.get(this.route.name) || null : null; },
    treeAll() {
      if (!this.m) return [];
      const q = this.treeQuery.trim().toLowerCase();
      return q ? this.m.skills.filter((s) => s.name.toLowerCase().includes(q)) : this.m.skills;
    },
    treeList() {
      const list = this.treeAll.slice(0, 200);
      if (this.skill && !list.includes(this.skill) && !this.treeQuery) list.unshift(this.skill);
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
      if (this.readCopyName === s.name && this.readCopyScope) {
        return s.copies.find(c => c.scope === this.readCopyScope && c.path === this.readCopyPath) || null;
      }
      return s.ref.holders[0] || s.primary;
    },
    docHtml() {
      const s = this.skill;
      if (!s) return "";
      const text = stripFrontmatter(this.bodyOf(this.refCopy));
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
      const copy = this.refCopy;
      return !!this.skill && this.bodyFetchable(copy) && !this.bodyReady(copy) && !this.bodyErrorOf(copy);
    },
    docWhy() {
      const c = this.refCopy;
      if (!c && this.readCopyName === this.skill?.name && this.readCopyScope) {
        return { title: "Selected copy is no longer listed", text: "Refresh files or choose another copy from Exact instances.", missing: true };
      }
      if (!c || this.bodyFetchable(c)) return null;
      const why = BROKEN_WHY[c.kind];
      return why ? { title: why[0], text: why[1] } : { title: "Not readable here", text: "" };
    },
    docError() { return this.bodyErrorOf(this.refCopy); },
    editable() { return !!this.skill && this.skill.copies.some((c) => c.state !== "broken" && !c.readOnly); },
    canEdit() { return !!this.skill && this.editable && this.bodyFetchable(this.refCopy) && !(this.refCopy && this.refCopy.readOnly); },
    editWhy() { const c = this.refCopy; if (c && c.readOnly) return this.readOnlyWhy(c); return this.docWhy ? `${this.docWhy.title}. ${this.docWhy.text}` : ""; },
    editTargets() { return this.skill ? this.skill.copies.filter((c) => c.state !== "broken" && !c.readOnly) : []; },
    editError() {
      if (!this.edit) return "";
      if (!this.edit.desc.trim()) return "Add a short description so agents know when to use this skill.";
      if (this.edit.desc.length > 1024) return "Keep the description under 1024 characters.";
      return "";
    },
    editDirty() { return !!this.edit && (this.edit.desc !== this.edit.baseDesc || this.edit.body !== this.edit.baseBody || JSON.stringify(this.edit.metadata)!==JSON.stringify(this.edit.baseMetadata)); },
    shareTargets() {
      if (!this.skill || !this.m) return [];
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
    queue() {
      if (!this.m) return [];
      const all = this.m.problems.filter((p) => !this.dismissed.includes(p.id));
      const rest = all.filter((p) => !this.skipped.includes(p.id));
      const sk = this.skipped.map((id) => all.find((p) => p.id === id)).filter(Boolean);
      const list = [...rest, ...sk];
      const i = list.findIndex((p) => p.id === this.front);
      if (i > 0) list.unshift(...list.splice(i, 1));
      return list;
    },
    cur() { return this.queue[0] || null; },
    curSkill() { return this.cur && this.cur.skill && this.m ? this.m.byName.get(this.cur.skill) : null; },
    curSyncCopies() { return this.cur?.key === "warn" ? (this.curSkill?.copies || []) : []; },
    curSyncSource() {
      const sources = this.curSyncCopies.filter((c) => c.scope === this.srcChoice);
      return sources.length === 1 && sources[0].hash ? sources[0] : null;
    },
    curSyncTargets() {
      if (!this.curSyncSource) return [];
      const counts = new Map();
      for (const copy of this.curSyncCopies) counts.set(copy.scope, (counts.get(copy.scope) || 0) + 1);
      return this.curSyncCopies.filter((c) => counts.get(c.scope) === 1 && !c.readOnly && this.agentOf(c.scope).writable &&
        c.state !== "broken" && c.hash && c.hash !== this.curSyncSource.hash);
    },
    curSyncLabel() {
      if (!this.curSyncSource) return "Choose a source copy";
      if (!this.curSyncTargets.length) return "No writable targets";
      const target = this.curSyncTargets.length === 1 ? this.agentOf(this.curSyncTargets[0].scope).name : `${this.curSyncTargets.length} copies`;
      return `Sync ${target} from ${this.agentOf(this.curSyncSource.scope).name}`;
    },
    inboxComparePair() {
      const target = this.curSyncTargets.find((c) => c.scope === this.inboxComparisonScope) || this.curSyncTargets[0];
      return target && this.curSyncSource ? [target, this.curSyncSource] : null;
    },
    inboxComparisonEvidence() { return this.comparisonEvidence(this.inboxComparePair); },
    curBig() {
      if (!this.cur || this.cur.key !== "info" || !this.m) return [];
      const inf = this.m.info(this.cur.agent);
      return inf ? [...inf.on].sort((a, b) => b.tokens - a.tokens).slice(0, 4) : [];
    },
    themeLabel() { return { system: "follows your computer", light: "light", dark: "dark" }[this.theme]; },
    themeIcon() { return PATHS[{ system: "auto", light: "sun", dark: "moon" }[this.theme]]; },
    createTargets() { return this.m ? this.m.agents.filter((x) => x.writable) : []; },
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
    progressBars() { return Math.min(this.done + this.queue.length, 12); },
  },
  watch: {
    libraryView(value) {try{localStorage.setItem("skillsmgr-v2-library-view",value);}catch(e){}},
    density(value) {try{localStorage.setItem("skillsmgr-v2-density",value);}catch(e){}},
    cur: { immediate: true, handler(c) { this.srcChoice = c && c.key === "warn" && this.m && this.m.byName.get(c.skill) ? (this.m.byName.get(c.skill).ref.ambiguous ? "" : (this.m.byName.get(c.skill).ref.holders[0] || {}).scope || "") : ""; if (c && c.key === "warn" && this.curSkill) this.ensureBodies(this.curSkill.copies); } },
    "cur.id"() { this.inboxComparisonScope = ""; },
    "route.name"() { this.compareWith = ""; this.loadSkillHistory(); this.primeBodies(); },
    "route.page"(page) { if (page !== "map") this.mapOrigin = null; },
    skill(s) { if (!s && this.edit) this.edit = null; if (s) this.ensureBodies(s.copies); },
    mapQuery() { this.resetMapPage(); },
    mapReviewOnly() { this.resetMapPage(); },
  },
  methods: {
    enc: encodeURIComponent, plural, join, words, titleCase, shortPath, renderDoc,
    fmt(n) {return Domain.numberFormatter(this.formatLocale==="system"?undefined:this.formatLocale).format(Number(n));},
    /* The informative end of a long folder path ("…/.claude/skills"); the full
     * path stays in the element's title. A leading ellipsis cut the useful part. */
    shortPath(path) {const text=String(path||"");const parts=text.split(/[\\/]/).filter(Boolean);return text.length<=28||parts.length<=2?text:"…/"+parts.slice(-2).join("/");},
    fmtDate(value, timeStyle = "short") {const date=new Date(value);return Number.isNaN(date.getTime())?String(value||"Date unavailable"):Domain.dateFormatter(this.formatLocale==="system"?undefined:this.formatLocale,{dateStyle:"medium",timeStyle}).format(date);},
    preferencesChanged() {this.theme=savedPreference("skillsmgr-theme",THEMES,"system");this.formatLocale=savedPreference("skillsmgr-locale",["system","en-US","en-GB","en-IN"],"system");document.documentElement.dataset.textSize=savedPreference("skillsmgr-text-size",["standard","large"],"standard");this.applyTheme(); },
    skillTags(name) {return (this.catalog.tags || {})[name] || [];},
    openSource(record) { this.toolTarget=markRaw(record);location.hash="#/tools/source-update"; },
    openSkillTool(tool) { if (this.refCopy) { this.toolTarget = markRaw(this.refCopy.record); location.hash = "#/tools/" + tool; } },
    openConciseReview(handoff) { if(!handoff||!handoff.target||!handoff.reviewId)return;this.toolTarget=markRaw(handoff.target);this.sourceReviewHandoff={...handoff,target:this.toolTarget};location.hash="#/tools/source-update"; },
    sourceReviewConsumed(reviewId) { if(this.sourceReviewHandoff&&this.sourceReviewHandoff.reviewId===reviewId)this.sourceReviewHandoff=null; },
    inspectRecord(record) { this.query=record.name;this.filter="all";this.tagFilter="";this.agentFilter=record.scope||"all";this.libraryView="instances";location.hash="#/skills"; },
    openRecord(record) {this.toolTarget=markRaw(record);this.readCopyPath=record.physical_path||record.path||"";this.readCopyScope=record.scope||"";this.readCopyName=record.name||"";location.hash="#/skill/"+encodeURIComponent(record.name);},
    openCommands() {this.commandQuery="";this.openDialog({title:"Find a tool or action",commands:true,cancel:"Close"}); },
    commandGo(item) {if(this.busy)return;const opener=this.opener;this.closeDialog();if(item.action==="create"){this.openCreate();this.opener=opener;}else if(item.action==="refresh")this.refresh();else location.hash=item.path;},
    agentOf(id) { return (this.m && this.m.agent(id)) || { ...FALLBACK_AGENT, name: id || "Unknown" }; },

    /* ----- loading ----- */
    async refresh() {
      /* Overlapping refreshes (Refresh files, tab focus, Undo, tool changes)
       * must not let an older, slower response overwrite a newer one. */
      const gen = ++this.refreshGen;
      this.loading = true; this.loadError = "";
      try {
        const [scopes, records, history] = await Promise.all([
          api("/api/scopes"), api("/api/skills?scope=all&body=0"),
          api("/api/history?limit=8").then(rows => ({rows, error: ""}),
            e => ({rows: [], error: this.friendly(e.message)})),
        ]);
        if (gen !== this.refreshGen) return;
        this.scopes=markRaw(scopes);this.records=markRaw(records);
        this.m = markRaw(Model.build(records, scopes, { suggested: 100 }));
        /* A reload produces fresh copies, so nothing is carried over from the
         * previous list: a body is re-read only where a view needs one. */
        this.bodies = {}; this.bodyInflight = {}; this.bodyErrors = {};
        this.history = Array.isArray(history.rows) ? history.rows : history.rows?.history || [];
        this.historyError = history.error;
        this.loadTrash();
        if (this.route.page === "recovery") this.loadAgentTrash();
        this.loadCatalog();
        this.primeBodies();
        this.loadSkillHistory();
      } catch (e) {
        if (gen === this.refreshGen) this.loadError = this.friendly(e.message || "The skills could not be read.");
      } finally { if (gen === this.refreshGen) this.loading = false; }
    },
    async loadSkillHistory() {
      const gen = ++this.historyGen;
      this.skillHistory = [];this.skillHistoryError="";
      if (this.route.page !== "skill") return;
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
            const path = record?.physical_path || record?.path;
            if (path && c.path && path !== c.path) throw new Error("The copy moved. Refresh files to find its current folder.");
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
      if (page === "skill" && this.skill) return this.ensureBodies(this.skill.copies);
      if (page === "inbox" && this.curSkill) return this.ensureBodies(this.curSkill.copies);
      if (page === "map") return this.ensureBodies(this.mapComparePair);
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
      const copy = this.refCopy;
      await this.ensureBodies(copy);
      if (this.refCopy === copy && this.bodyReady(copy)) this.$refs.readerIdentity?.focus();
    },

    /* ----- search / filter ----- */
    searchInput(v) { this.query = v; if (this.route.page !== "skills" && v.trim()) location.hash = "#/skills"; this.extra = {}; },
    searchSubmit() { if (this.route.page !== "skills") location.hash = "#/skills"; },
    capReset() { this.extra = {}; },
    showMore(id) { this.extra = { ...this.extra, [id]: (this.extra[id] || 0) + 96 }; },
    clearFilters() { this.query = ""; this.filter = "all"; this.agentFilter = "all"; this.tagFilter="";this.extra = {}; this.$nextTick(() => { const q = document.getElementById("q"); if (q) q.focus(); }); },
    pickAgent(id, query = "") { this.agentFilter = id; this.filter = "all"; this.query = query; this.extra = {}; },
    findInMap() { this.mapQuery = this.query.trim(); location.hash = "#/map"; },
    skipToContent() { const h = document.getElementById("h1") || this.$refs.main; if (h) h.focus(); },
    focusH1() { this.$nextTick(() => { const h = document.getElementById("h1"); if (h) h.focus({ preventScroll: true }); }); },

    /* ----- toasts & dialogs ----- */
    friendly(msg) {
      let s = String(msg || "Something went wrong.");
      if (/invalid archive|not a gzip|ReadError|zipfile/i.test(s)) return "That file is not a backup archive. Choose a .tar.gz, .tar or .zip file made by Skills Manager.";
      if (/not valid UTF-8/i.test(s)) return "One of the copies is not saved as UTF-8 text. Keep a copy of the original file, then open it in a text editor and save it as UTF-8 before editing it here.";
      if (/traceback|(?:UnicodeDecode|Recursion|Permission|FileNotFound|Operational)Error|\[Errno \d+\]/i.test(s)) return "The operation could not be completed. Refresh and try again; check that the skill files are readable and writable.";
      return s.replace(/(?:\/[^\s'":]+)+\/([^\s'":/]+)/g, "$1").replace(/\s*\(byte 0x[0-9a-f]+ at offset \d+\)/i, "");
    },
    toast(text, opts = {}) {
      if (opts.err) text = this.friendly(text);
      const t = { id: ++this.toastSeq, text, err: !!opts.err, undo: opts.undo || null, onUndo: opts.onUndo || null, undoText: opts.undoText || "Undone" };
      this.toasts.push(t); this.live = text + (t.undo ? " Undo is available." : "");
      this.armToast(t, t.undo ? 20000 : (t.err ? 7000 : 4000));
    },
    /* WCAG 2.2.1: a toast with an action never times out while the reader is
     * on it; it waits until focus and pointer leave, then gets its time again. */
    armToast(t, ms) {
      clearTimeout(t.timer);
      t.ms = ms;
      t.timer = setTimeout(() => { if (!t.held) this.toasts = this.toasts.filter((x) => x.id !== t.id); }, ms);
    },
    holdToast(t, held) {
      t.held = held;
      if (!held) this.armToast(t, Math.max(t.ms || 4000, 6000));
    },
    async runUndo(t) {
      this.toasts = this.toasts.filter((x) => x.id !== t.id);
      this.busy = true;
      try { await t.undo(); await this.refresh(); if (t.onUndo) t.onUndo(); this.toast(t.undoText); } catch (e) { await this.refresh(); if (t.onUndo) t.onUndo(); this.toast("Couldn't undo: " + e.message, { err: true }); } finally { this.busy = false; }
    },
    openDialog(d) { this.opener = document.activeElement; this.dialog = { cancel: "Cancel", ...d }; this.$nextTick(() => { const d = this.$refs.dlg; const b = d && (d.querySelector("input:not(.sr-only), select, textarea") || d.querySelector("button:not(.sr-only)")); if (b) b.focus(); }); },
    closeDialog() { if(this.busy)return;if(this.dialog?.aiEdit)this.retireAiEdit(this.dialog.aiEdit.result);this.dialog = null; this.$nextTick(() => { if (this.opener && this.opener.isConnected) this.opener.focus(); }); },
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
      const f = [...this.$refs.dlg.querySelectorAll("button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], summary")].filter(el=>el.tabIndex!==-1&&el.offsetParent!==null);
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

    async syncDiffering() {
      const s = this.skill;
      if (!s || s.ref.ambiguous) return;
      const from = s.ref.holders[0].scope;
      await this.runSync(s.name, from, s.differing.filter((c) => !c.readOnly).map((c) => c.scope), `${s.name} now matches in`);
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
          (r.manualRecovery ? " Text Undo is unavailable. Check Recovery or your backup." : ""),
        { err: !r.synced.length, undo: r.synced.length ? undo : null, onUndo,
          undoText: "Undone. Text and on/off state restored. Supporting files are unchanged." });
        return r.synced.length ? r : null;
      } catch (e) { this.toast(e.message, { err: true }); return null; } finally { this.busy = false; }
    },
    /* A followed link (SCOPE-2) is read-only: it belongs to the agent whose
     * folder it lives in, and a write here would land in that other copy. */
    readOnlyWhy(c) { const from = c && c.linkFrom ? shortPath(c.linkFrom) : "another folder"; return `This is a link into ${from}; change it in that agent's copy.`; },
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
      if (p) this.fixBad(p);
    },
    fixBad(p, undoHook) {
      if (p.fixable) return this.runSync(p.skill, p.source, p.agents, `${p.skill} was replaced in`, undoHook);
      const s = this.m.byName.get(p.skill);
      this.openDialog({ title: p.title, lines: [p.text], how: p.how, paths: s.broken.map((c) => shortPath(c.path)), cancel: "Close" });
      return null;
    },
    openShare() {
      if (!this.refCopy) return;
      const s = this.skill, from = this.refCopy.scope;
      this.openDialog({
        title: `Add “${s.name}” to another agent`, lines: ["Choose where to copy it. The copy comes from " + this.agentOf(from).name + ". Whether it is on or off, and its supporting files, are copied too."],
        picks: this.shareTargets.map((a) => ({ id: a.id, label: a.name, path: a.path })), chosen: this.shareTargets.length === 1 ? [this.shareTargets[0].id] : [], confirm: "Add",
        onConfirm: (d) => this.runSync(s.name, from, d.chosen, `${s.name} was added to`),
      });
    },
    openTrash() {
      const s = this.skill;
      this.openDialog({
        title: `Move “${s.name}” to the trash?`, danger: true, confirm: "Move to trash",
        lines: ["Choose the places to remove it from. Each agent keeps its own trash folder, and every copy you remove here can be restored from Recovery or with Undo."],
      picks: s.copies.filter(c => !c.readOnly).map((c) => ({ id: c.scope, label: this.agentOf(c.scope).name, path: shortPath(c.path) })), chosen: s.copies.filter(c => !c.readOnly).length === 1 ? [s.copies.find(c => !c.readOnly).scope] : [],
        onConfirm: async (d) => {
          this.busy = true;
          try {
            const trashed = [];
            for (const sc of d.chosen) {
              const r = await api(`/api/skills/${encodeURIComponent(s.name)}?scope=${encodeURIComponent(sc)}&purge=0`, { method: "DELETE" });
              if (r && r.trash_path) trashed.push({ scope: sc, trash_path: r.trash_path });
            }
            await this.refresh();
            const undo = trashed.length ? async () => { for (const t of trashed) await this.restoreTrashed(s.name, t.scope, t.trash_path); } : null;
            this.toast(`${s.name} moved to the trash in ${join(d.chosen.map((id) => this.agentOf(id).name))}.`, { undo });
            if (!this.m.byName.get(s.name)) location.hash = "#/skills";
          } catch (e) { this.toast(e.message, { err: true }); await this.refresh(); } finally { this.busy = false; }
        },
      });
    },
    openPermanentDelete() {const skill=this.skill;if(!skill)return;this.openDialog({title:`Permanently delete “${skill.name}”?`,danger:true,confirm:"Delete permanently",lines:["This removes the selected copies without moving them to trash. There is no Undo or trash restore for this action."],picks:skill.copies.filter(c=>!c.readOnly&&c.record.addressable!==false&&c.state!=="link"&&this.agentOf(c.scope).writable).map(c=>({id:c.scope,label:this.agentOf(c.scope).name,path:shortPath(c.path)})),chosen:[],onConfirm:async d=>{this.busy=true;try{for(const scope of d.chosen)await api(`/api/skills/${encodeURIComponent(skill.name)}?scope=${encodeURIComponent(scope)}&purge=1`,{method:"DELETE"});await this.refresh();this.toast("Selected copies permanently deleted.");if(!this.m.byName.get(skill.name))location.hash="#/skills";}catch(e){await this.refresh();this.toast(e.message,{err:true});}finally{this.busy=false;}}});},

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
            await this.saveAuthorCases(d, f.name.trim());
            await this.refresh();
            this.toast(`${f.name.trim()} created in ${this.agentOf(f.scope).name}.`);
            location.hash = "#/skill/" + encodeURIComponent(f.name.trim());
          } catch (e) { d.error=this.friendly(e.message);this.live=d.error; } finally { this.busy = false; }
        },
      });
      const dialog=this.dialog;
      api("/api/templates").then(r=>{if(this.dialog===dialog)this.createTemplates=r.templates||[];}).catch(e=>{if(this.dialog===dialog)dialog.error="Templates unavailable: "+this.friendly(e.message);});
    },
    useDraft(draft) {
      if (!draft || typeof draft !== "object") return;
      this.openCreate({
        scope: draft.scope, name: draft.name, description: draft.description, body: draft.body,
        category: draft.category, version: draft.version, license: draft.license,
        compatibility: draft.compatibility, allowed_tools: draft.allowed_tools,
      });
    },
    async loadCreateTemplate() {const d=this.dialog;if(!d?.form?.template)return;const name=d.form.template;d.templateLoading=true;try{const t=await api("/api/templates/"+encodeURIComponent(name));if(this.dialog===d&&d.form.template===name)d.form.body=stripFrontmatter(t.body||"");}catch(e){if(this.dialog===d)d.error=this.friendly(e.message);}finally{if(this.dialog===d)d.templateLoading=false;}},
    async loadTrash() {
      const gen = ++this.trashGen;
      this.trashLoading = true;
      try {
        const rows = await api("/api/trash");
        if (gen !== this.trashGen) return;
        this.trash = rows; this.trashError = "";
      } catch (e) { if (gen === this.trashGen) this.trashError = this.friendly(e.message); }
      finally { if (gen === this.trashGen) this.trashLoading = false; }
    },
    async restoreTrash(t) {
      if (this.busy) return;
      this.busy = true;
      try { await this.restoreTrashed(t.name, "global", t.trash_path); await this.refresh(); this.toast(`${t.name} restored to your library.`); }
      catch (e) { this.toast(e.message, { err: true }); } finally { this.busy = false; }
    },
    /* Both Recovery rows and Undo address the listed trash entry. */
    async restoreTrashed(name, scope, trashPath) {
      const url = `/api/trash/${encodeURIComponent(name)}?scope=${encodeURIComponent(scope || "global")}`;
      await api(url, { method: "POST", body: trashPath ? JSON.stringify({ trash_path: trashPath }) : undefined });
    },
    async loadAgentTrash() {
      const gen = ++this.agentTrashGen;
      const agents = (this.m ? this.m.agents : []).filter((a) => !a.library && a.writable);
      this.agentTrashLoading = true;
      const rows = [], errors = [];
      await Promise.all(agents.map(async (a) => {
        try {
          const list = await api("/api/trash?scope=" + encodeURIComponent(a.id));
          for (const row of Array.isArray(list) ? list : []) rows.push({ ...row, scopeLabel: a.name });
        } catch (e) { errors.push({ scope: a.id, message: this.friendly(e.message) }); }
      }));
      if (gen !== this.agentTrashGen) return;
      rows.sort((a, b) => String(b.trashed_at).localeCompare(String(a.trashed_at)) || a.name.localeCompare(b.name));
      const counts = new Map(), positions = new Map();
      const keyOf = (row) => JSON.stringify([row.scope, row.name]);
      for (const row of rows) {
        const key = keyOf(row);
        counts.set(key, (counts.get(key) || 0) + 1);
      }
      for (const row of rows) {
        const key = keyOf(row), position = (positions.get(key) || 0) + 1;
        positions.set(key, position);
        if (counts.get(key) > 1) row.copyLabel = `copy ${position} of ${counts.get(key)}`;
      }
      this.agentTrash = rows; this.agentTrashErrors = errors; this.agentTrashLoading = false;
    },
    async retryAgentTrash() {
      if (this.agentTrashLoading) return;
      await this.loadAgentTrash();
      if (!this.agentTrashErrors.length) this.$refs.agentTrashHeading?.focus();
    },
    agentRestoreLabel(row) {
      const target = `Review restore for ${row.name} in ${row.scopeLabel}`;
      return row.copyLabel ? `${target}, ${row.copyLabel}` : target;
    },
    reviewAgentTrash(row) {
      this.openDialog({
        title: `Restore ${row.name}?`,
        recovery: row,
        confirm: "Restore folder",
        error: "",
      });
    },
    async restoreAgentTrash(t) {
      if (this.busy) return;
      const dialog = this.dialog;
      this.busy = true;
      try {
        await this.restoreTrashed(t.name, t.scope, t.trash_path);
        this.dialog = null;
        await this.refresh();
        this.toast(`${t.name} restored to ${t.scopeLabel}.`);
        this.$refs.agentTrashHeading?.focus();
      } catch (e) {
        if (this.dialog === dialog) {
          dialog.error = this.friendly(e.message);
          this.$nextTick(() => this.$refs.restoreError?.focus());
        }
      } finally { this.busy = false; }
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
      this.openDialog({ title: "Empty the trash?", danger: true, confirm: "Delete permanently", lines: [`${plural(this.trash.length, "skill")} will be deleted permanently. This cannot be undone.`],
        onConfirm: async () => { this.busy = true; try { await api("/api/trash/purge", { method: "POST" }); await this.loadTrash(); this.toast("The trash was emptied."); } catch (e) { this.toast(e.message, { err: true }); } finally { this.busy = false; } } });
    },
    async exportBackup(full) {
      if (this.busy) return;
      this.busy = true; this.exportPending = true; this.exportError = "";
      try {
        const { blob, filename } = await Domain.apiBlob("/api/export" + (full ? "?full=1" : ""));
        const url = URL.createObjectURL(blob), a = document.createElement("a");
        a.href = url; a.download = filename || "skills-backup.tar.gz"; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 2000);
        this.toast("Backup download started.");
      } catch (e) {
        this.exportError = Domain.archiveDownloadError(e);
        if (this.route.page !== "recovery") this.toast(this.exportError, { err: true });
      } finally { this.busy = false; this.exportPending = false; }
    },
    /* The picker filters by `accept`; a dropped file is not, so check its name.
     * The server still decides whether the bytes are a real archive. */
    pickImport(list) {
      if (this.busy) return;
      const file = (list && list[0]) || null;
      if (file && !/\.(tar\.gz|tgz|tar|zip)$/i.test(file.name)) { this.importFile = null; this.importReject = `${file.name} is not a backup file. Choose a .tar.gz, .tgz, .tar or .zip file.`; return; }
      this.importReject = ""; this.importFile = file;
    },
    archiveImportSummary(result) { return Domain.archiveImportSummary(result); },
    async doImport() {
      const f = this.importFile; if (!f || this.busy) return;
      this.busy = true; this.importResult = null; this.importError = "";
      try {
        const r = await api(`/api/import?filename=${encodeURIComponent(f.name)}&force=${this.importForce ? 1 : 0}&full=${this.importFull ? 1 : 0}`, { method: "PUT", body: f });
        this.importResult = r;
        this.live = this.archiveImportSummary(r);
        this.importFile = null;
        const input = document.getElementById("imp-file"); if (input) input.value = "";
        await this.refresh();
      } catch (e) { this.importError = this.friendly(e.message); } finally { this.busy = false; }
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
        [["/"], "Find a skill"], [["?"], "Show this list"], [["Esc"], "Close a dialog"],
        [["Ctrl/Cmd", "K"], "Find tools and actions"],
        [["Ctrl", "S"], "Save while editing"], [["Enter"], "Fix the item in the Inbox"], [["S"], "Skip it for now"],
      ] });
    },

    /* ----- editing ----- */
    async startEdit() {
      const s = this.skill, c = this.refCopy;
      if (!s || !c || !this.bodyFetchable(c)) return;
      /* The editor must never open on a body that has not loaded: read it
       * first, and abandon silently if the reader navigated away meanwhile.
       * A periodic re-read replaces `skill` with an equal-named object, so the
       * identity that matters is the name and the route, not the object. */
      await this.ensureBodies([c]);
      if (!this.skill || this.skill.name !== s.name || this.route.page !== "skill") return;
      if (!this.bodyReady(c)) { this.toast(this.bodyErrorOf(c) || "The document could not be read. Try again.", { err: true }); return; }
      const body = stripFrontmatter(this.bodyOf(c).replace(/^\uFEFF/, ""));
      const metadata={category:c.record.category||"",version:c.record.version||"",license:c.record.license||"",compatibility:Domain.formatCompat(c.record.compatibility),allowed_tools:Domain.formatTools(c.record.allowed_tools)};
      this.edit = { name: s.name, desc: c.description, baseDesc: c.description, body, baseBody: body, metadata,baseMetadata:{...metadata},tab: "write", targets: this.readCopyPath ? [c.scope] : this.editTargets.map((x) => x.scope), copy: { path: c.path, scope: c.scope, hash: c.hash } };
      this.$nextTick(() => { this.growArea(); const d = document.getElementById("ed-desc"); if (d) d.focus(); });
    },
    openAiDiagnosis() {
      if (this.refCopy) this.openDialog({ title: "Why didn’t this skill run?", diagnosis: this.refCopy });
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
        e.copy.hash = this.skill?.copies.find(c => c.path === a.target.path && c.scope === a.target.scope)?.hash || "";
        this.toast(committed.warning || "AI edit saved. The previous folder is available in Recovery.");
        this.$nextTick(() => { this.growArea(); this.$refs.edbody?.focus(); });
      } catch (error) { a.error = this.friendly(error.message); }
      finally { this.busy = false; }
    },
    async cancelEdit() {
      if (this.editDirty) return this.openDialog({ title: "Discard your changes?", lines: [`You have unsaved changes to “${this.edit.name}”.`], cancel: "Keep editing", confirm: "Discard changes", danger: true, onConfirm: () => { this.edit = null; } });
      this.edit = null; return null;
    },
    async saveEdit() {
      /* Same guard as the Save button: Ctrl/Cmd+S must not save to zero
       * targets (which discarded the edit), save nothing, or save twice. */
      const e = this.edit; if (!e || this.editError || this.busy || !e.targets.length || !this.editDirty) return;
      this.busy = true; const saved = [];
      try {
        const fields = {};
        if(e.desc!==e.baseDesc)fields.description=e.desc;
        if(e.body!==e.baseBody)fields.body=e.body;
        for(const key of Object.keys(e.metadata))if(e.metadata[key]!==e.baseMetadata[key])fields[key]=e.metadata[key];
        const snaps = {};
        for (const sc of e.targets) snaps[sc] = new Set(await this.snapshotIds(e.name, sc));
        for (const sc of e.targets) {
          await api(`/api/skills/${encodeURIComponent(e.name)}?scope=${encodeURIComponent(sc)}`, { method: "PATCH", body: JSON.stringify(fields) });
          const fresh = (await this.snapshotIds(e.name, sc)).find((id) => !snaps[sc].has(id));
          if (fresh) saved.push([sc, fresh]);
        }
        this.edit = null;
        await this.refresh();
        const undo = saved.length ? async () => { for (const [sc, snap] of saved) await api(`/api/trash/${encodeURIComponent(e.name)}?snapshot=${encodeURIComponent(snap)}&scope=${encodeURIComponent(sc)}`, { method: "POST" }); } : null;
        this.toast(`${e.name} saved to ${plural(e.targets.length, "place")}.`, { undo });
      } catch (err) { this.toast(err.message, { err: true }); await this.refresh(); } finally { this.busy = false; }
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

    /* ----- inbox ----- */
    openInboxFor(skillName) {
      const issue = this.queue.find((p) => p.skill === skillName && p.key === "warn");
      if (issue) this.front = issue.id;
      location.hash = "#/inbox";
    },
    async fixCurrent() {
      const p = this.cur; if (!p || this.busy) return null;
      if (p.key === "warn" && !this.curSyncTargets.length) return null;
      /* Undo of a fix puts the item back in the queue, since the file is back. */
      const back = () => { if (!this.m.problems.some((item) => item.id === p.id)) return; this.dismissed = this.dismissed.filter((id) => id !== p.id); this.done = Math.max(0, this.done - 1); };
      let ok = false;
      if (p.key === "warn") {
        const tos = this.curSyncTargets.map((c) => c.scope);
        ok = !!(await this.runSync(p.skill, this.curSyncSource.scope, tos, `${p.skill} now matches in`, back));
      } else if (p.key === "bad") {
        if (!p.fixable) return this.fixBad(p);
        ok = !!(await this.fixBad(p, back));
      } else {
        /* A note acknowledged is not a fix: it leaves the queue without counting. */
        this.dismissed.push(p.id); this.skipped = this.skipped.filter((id) => id !== p.id); if (this.front === p.id) this.front = null;
        this.toast("Hidden until you reload."); return null;
      }
      if (ok) { this.dismissed.push(p.id); this.skipped = this.skipped.filter((id) => id !== p.id); if (this.front === p.id) this.front = null; this.done++; }
      return null;
    },
    updateTabsClip() {
      const el = this.$refs.tabs; if (!el) return;
      el.classList.toggle("is-clipped", el.scrollWidth - el.clientWidth - el.scrollLeft > 1);
    },
    skipCurrent() { if (!this.cur) return; const id = this.cur.id; this.skipped = [...this.skipped.filter((x) => x !== id), id]; this.front = null; this.focusH1(); },
  },
  mounted() {
    this.refresh();
    if (window.ResizeObserver && this.$refs.tabs) {
      this.tabsObserver = new ResizeObserver(() => this.updateTabsClip());
      this.tabsObserver.observe(this.$refs.tabs);
    }
    this.updateTabsClip();
    window.addEventListener("hashchange", () => {
      const next = parseRoute();
      if (this.edit && this.editDirty && !(next.page === "skill" && next.name === this.edit.name)) {
        const target = location.hash;
        location.hash = "#/skill/" + encodeURIComponent(this.edit.name);
        return this.openDialog({ title: "Discard your changes?", lines: [`You have unsaved changes to “${this.edit.name}”.`], cancel: "Keep editing", confirm: "Discard changes", danger: true,
          onConfirm: () => { this.edit = null; location.hash = target; } });
      }
      this.route = next; if (next.page !== "skill") this.edit = null;
      this.primeBodies();
      if (next.page === "recovery") this.loadAgentTrash();
      document.title = (next.page === "skill" ? next.name : TITLES[next.page]) + " · Skills Manager";
      window.scrollTo(0, 0); this.focusH1();
    });
    window.addEventListener("beforeunload", (e) => { if (this.editDirty) { e.preventDefault(); e.returnValue = ""; } });
    document.addEventListener("keydown", (e) => {
      const t = e.target, typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if(document.querySelector("dialog[open]"))return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==="k" && !this.dialog && !document.querySelector("dialog[open]")) {e.preventDefault();this.openCommands();}
      if (e.key === "?" && !typing && !this.dialog) { e.preventDefault(); this.openHelp(); }
      if (e.key === "/" && !typing && !this.dialog && !e.ctrlKey && !e.metaKey) { e.preventDefault(); this.$refs.gsearch.focus(); }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s" && this.edit) { e.preventDefault(); if (!this.dialog) this.saveEdit(); }
      if (this.route.page === "inbox" && this.cur && !typing && !this.dialog && !e.ctrlKey && !e.metaKey && !e.altKey) {
        /* Shortcuts never fire from a link, button or field: Enter on "Open
         * skill" must open the skill, not run the fix (screen-reader E2E SR-1). */
        const onControl = t && t.closest && t.closest("a, button, input, select, textarea, summary, [role=button], [contenteditable]");
        const inScope = !t || t === document.body || (t.closest && t.closest("#main"));
        if (!onControl && inScope) {
          if (e.key === "s" || e.key === "S") { e.preventDefault(); this.skipCurrent(); }
          else if (e.key === "Enter") { e.preventDefault(); this.fixCurrent(); }
        }
      }
    });
    document.title = (this.route.page === "skill" ? this.route.name : TITLES[this.route.page]) + " · Skills Manager";
    window.addEventListener("storage",event=>{if(["skillsmgr-theme","skillsmgr-text-size","skillsmgr-locale"].includes(event.key))this.preferencesChanged();});
    this.loadSkillHistory();
    this.applyTheme();
    /* The filesystem is the source of truth and other tools edit it, so re-read
     * it whenever the tab comes back into view (at most every 15 s, never
     * while an edit is open so a refresh cannot disturb unsaved work). */
    let lastLoad = Date.now();
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "visible" || this.edit || this.busy || Date.now() - lastLoad < 15000) return;
      lastLoad = Date.now(); this.refresh();
    });
    if (window.matchMedia) {
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
  /* A real agent mark when one is vendored (model.js AGENT_ICONS), otherwise
   * the initials badge. Both are decorative: the agent name is always shown. */
  template: '<span v-if="agent.icon" :class="[\'logo\', \'mark-tile\', size]" aria-hidden="true">'
    + '<svg :viewBox="agent.icon.vb"><path v-for="(p, i) in agent.icon.paths" :key="i" :d="p.d" :style="{ fill: p.fill || \'currentColor\' }" :fill-rule="p.evenodd ? \'evenodd\' : null"></path></svg></span>'
    + '<span v-else :class="[\'logo\', size]" :style="{ background: agent.color }" aria-hidden="true">{{ agent.initials }}</span>',
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
        const statuses = { within_budget: "Within estimate", over_budget_estimate: "Over estimated budget", no_instances: "No model-visible entries" };
        const unknown = !Object.prototype.hasOwnProperty.call(statuses, section.status);
        const metadataUnknown = Number((section.unknown_metadata || {}).total || 0) > 0;
        const status = unknown ? (metadataUnknown ? "Listing unknown: invocation metadata unreadable" : "Budget unknown") : statuses[section.status];
        return [{ key, label, unit, used: unit === "chars" ? section.listing_chars : section.listing_tokens_estimate,
          budget: unknown && !metadataUnknown ? null : unit === "chars" ? budget.budget_chars_estimate : budget.budget_tokens,
          subtotal: metadataUnknown,
          basis: budget.basis || "Budget basis unavailable",
          cuts: (section.entries || []).filter((e) => Number(e.cut_chars) > 0)
            .sort((a, b) => Number(b.cut_chars) - Number(a.cut_chars) || String(a.name).localeCompare(String(b.name))).slice(0, 20),
          thin: (section.entries || []).filter((e) => e.thin).map((e) => e.name).sort(),
          status: status + (section.confidence === "partial" ? " · partial evidence" : "") }];
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
        <h3>{{ section.label }}</h3>
        <p class="num"><template v-if="section.subtotal">Known subtotal: </template>~{{ fmtN(section.used) }} {{ section.unit }}<template v-if="section.budget != null"> of ~{{ fmtN(section.budget) }}</template></p>
        <p class="sub">{{ section.status }}</p><p class="sub">{{ section.basis }}</p>
        <details v-if="section.cuts.length" class="listing-cuts"><summary>{{ section.cuts.length }} description{{ section.cuts.length === 1 ? "" : "s" }} cut before the model sees {{ section.cuts.length === 1 ? "it" : "them" }}</summary>
          <ul><li v-for="e in section.cuts" :key="e.name"><span class="mono">{{ e.name }}</span> loses {{ fmtN(e.cut_chars) }} of {{ fmtN(e.description_chars) }} characters</li></ul></details>
        <details v-if="section.thin.length" class="listing-cuts"><summary>{{ section.thin.length }} description{{ section.thin.length === 1 ? " is" : "s are" }} too short to route on</summary>
          <p class="sub">Under 20 characters, the model has almost nothing to choose {{ section.thin.length === 1 ? "this skill" : "these skills" }} by.</p>
          <ul><li v-for="n in section.thin.slice(0, 20)" :key="n"><span class="mono">{{ n }}</span></li></ul></details>
      </div>
      <p class="sub" v-if="!sections.length">No Claude Code or Codex listing instances observed.</p>
      <a class="see-all" href="#/tools/quality">Review listing evidence <ic name="arrow" cls="i-s"></ic></a>
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

app.mount("#app");
