/* Skills Manager v2 — pure data model (no DOM, no network).
 *
 * Turns the API's observations into the vocabulary the new interface speaks:
 * agents, skills, copies, status, problems. Nothing here asserts more than the
 * filesystem reported: there is no "newest" version (the tool has no version
 * order), so a skill whose copies differ is "Copies differ" and the reference
 * copy is the one most places hold, never an elected winner.
 */
"use strict";

(function () {
  const D = window.SkillManagerDomain;

  /* ---------- Small helpers ---------- */
  const esc = D.esc;
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;
  const join = (a) => (a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]);
  const words = (tokens) => Math.round((tokens * 0.75) / 10) * 10;

  /* ---------- Agents ---------- */
  /* Badge fills carry white initials, so each clears 4.5:1 (WCAG AA) on #fff. */
  const BRAND = {
    "claude-code": ["CC", "#b85a3a"], codex: ["CX", "#2f6f5e"], cursor: ["CU", "#1b1d22"],
    gemini: ["GE", "#2f6fd6"], opencode: ["OC", "#b04a7a"], commandcode: ["CM", "#7a5ad6"],
    agents: ["SF", "#55585f"], global: ["LB", "#55585f"],
  };
  const PALETTE = ["#b85a3a", "#2f6f5e", "#2f6fd6", "#b04a7a", "#7a5ad6", "#a2510a", "#0e7490", "#1c7a47"];
  /* Real agent marks, path data verbatim from the named open sources
   * (licence beside each). Marks remain their owners' trademarks and only
   * identify the agent (nominative use). A path without `fill` takes the
   * theme ink colour; `fill` may name a CSS custom property. */
  const AGENT_ICONS = {
    "claude-code": { vb: "0 0 24 24", paths: [{ d: "M21 10.5h3v3h-3v3h-1.5v3H18v-3h-1.5v3H15v-3H9v3H7.5v-3H6v3H4.5v-3H3v-3H0v-3h3v-6h18Zm-15 0h1.5v-3H6Zm10.5 0H18v-3h-1.5z", fill: "#d97757" }] }, // Simple Icons claudecode, CC0-1.0
    "codex": { vb: "0 0 24 24", paths: [{ d: "M8.086.457a6.105 6.105 0 013.046-.415c1.333.153 2.521.72 3.564 1.7a.117.117 0 00.107.029c1.408-.346 2.762-.224 4.061.366l.063.03.154.076c1.357.703 2.33 1.77 2.918 3.198.278.679.418 1.388.421 2.126a5.655 5.655 0 01-.18 1.631.167.167 0 00.04.155 5.982 5.982 0 011.578 2.891c.385 1.901-.01 3.615-1.183 5.14l-.182.22a6.063 6.063 0 01-2.934 1.851.162.162 0 00-.108.102c-.255.736-.511 1.364-.987 1.992-1.199 1.582-2.962 2.462-4.948 2.451-1.583-.008-2.986-.587-4.21-1.736a.145.145 0 00-.14-.032c-.518.167-1.04.191-1.604.185a5.924 5.924 0 01-2.595-.622 6.058 6.058 0 01-2.146-1.781c-.203-.269-.404-.522-.551-.821a7.74 7.74 0 01-.495-1.283 6.11 6.11 0 01-.017-3.064.166.166 0 00.008-.074.115.115 0 00-.037-.064 5.958 5.958 0 01-1.38-2.202 5.196 5.196 0 01-.333-1.589 6.915 6.915 0 01.188-2.132c.45-1.484 1.309-2.648 2.577-3.493.282-.188.55-.334.802-.438.286-.12.573-.22.861-.304a.129.129 0 00.087-.087A6.016 6.016 0 015.635 2.31C6.315 1.464 7.132.846 8.086.457zm-.804 7.85a.848.848 0 00-1.473.842l1.694 2.965-1.688 2.848a.849.849 0 001.46.864l1.94-3.272a.849.849 0 00.007-.854l-1.94-3.393zm5.446 6.24a.849.849 0 000 1.695h4.848a.849.849 0 000-1.696h-4.848z", evenodd: true }] }, // theSVG codex-openai, MIT
    "cursor": { vb: "0 0 24 24", paths: [{ d: "M11.503.131 1.891 5.678a.84.84 0 0 0-.42.726v11.188c0 .3.162.575.42.724l9.609 5.55a1 1 0 0 0 .998 0l9.61-5.55a.84.84 0 0 0 .42-.724V6.404a.84.84 0 0 0-.42-.726L12.497.131a1.01 1.01 0 0 0-.996 0M2.657 6.338h18.55c.263 0 .43.287.297.515L12.23 22.918c-.062.107-.229.064-.229-.06V12.335a.59.59 0 0 0-.295-.51l-9.11-5.257c-.109-.063-.064-.23.061-.23" }] }, // Simple Icons cursor, CC0-1.0
    "gemini": { vb: "0 0 24 24", paths: [{ d: "M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24 12q-2.49 0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 12 0q0 2.49-.96 4.68-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49 0 4.68.96 2.19.93 3.81 2.55t2.55 3.81", fill: "#8e75b2" }] }, // Simple Icons googlegemini, CC0-1.0
    "opencode": { vb: "0 0 24 24", paths: [{ d: "M22 24H2V0h20zM17 4.8H7v14.4h10z" }] }, // Simple Icons opencode, CC0-1.0
    "commandcode": { vb: "44 44 136 136", paths: [{ d: "M113.14 45.8721H110.465C93.6901 45.8721 81.6998 45.8845 72.5877 47.1096C63.6446 48.312 58.3583 50.5847 54.4715 54.4715C50.5847 58.3583 48.312 63.6446 47.1096 72.5877C45.8845 81.6998 45.8721 93.6901 45.8721 110.465V113.14C45.8721 129.915 45.8845 141.905 47.1096 151.017C48.312 159.96 50.5847 165.246 54.4715 169.133C58.3583 173.02 63.6446 175.293 72.5877 176.495C81.6998 177.72 93.6901 177.733 110.465 177.733H113.14C129.915 177.733 141.905 177.72 151.017 176.495C159.96 175.293 165.246 173.02 169.133 169.133C173.02 165.246 175.293 159.96 176.495 151.017C177.72 141.905 177.733 129.915 177.733 113.14V110.465C177.733 93.6901 177.72 81.6998 176.495 72.5877C175.293 63.6446 173.02 58.3583 169.133 54.4715C165.246 50.5847 159.96 48.312 151.017 47.1096C141.905 45.8845 129.915 45.8721 113.14 45.8721ZM50.3193 50.3193C40 60.6387 40 77.2474 40 110.465V113.14C40 146.357 40 162.966 50.3193 173.285C60.6387 183.605 77.2474 183.605 110.465 183.605H113.14C146.357 183.605 162.966 183.605 173.285 173.285C183.605 162.966 183.605 146.357 183.605 113.14V110.465C183.605 77.2474 183.605 60.6387 173.285 50.3193C162.966 40 146.357 40 113.14 40H110.465C77.2474 40 60.6387 40 50.3193 50.3193Z", evenodd: true }, { d: "M138.805 67.6163C129.329 67.6163 121.621 75.3243 121.621 84.7997V92.1641H101.983V84.7997C101.983 75.3243 94.2752 67.6163 84.7997 67.6163C75.3243 67.6163 67.6163 75.3243 67.6163 84.7997C67.6163 94.2752 75.3243 101.983 84.7997 101.983H92.1641V121.621H84.7997C75.3243 121.621 67.6163 129.329 67.6163 138.805C67.6163 148.28 75.3243 155.988 84.7997 155.988C94.2752 155.988 101.983 148.28 101.983 138.805V131.441H121.621V138.805C121.621 148.28 129.329 155.988 138.805 155.988C148.28 155.988 155.988 148.28 155.988 138.805C155.988 129.329 148.28 121.621 138.805 121.621H131.441V101.983H138.805C148.28 101.983 155.988 94.2752 155.988 84.7997C155.988 75.3243 148.28 67.6163 138.805 67.6163ZM131.441 92.1641V84.7997C131.441 80.7248 134.73 77.4354 138.805 77.4354C142.88 77.4354 146.169 80.7248 146.169 84.7997C146.169 88.8747 142.88 92.1641 138.805 92.1641H131.441ZM84.7997 92.1641C80.7248 92.1641 77.4354 88.8747 77.4354 84.7997C77.4354 80.7248 80.7248 77.4354 84.7997 77.4354C88.8747 77.4354 92.1641 80.7248 92.1641 84.7997V92.1641H84.7997ZM101.983 121.621V101.983H121.621V121.621H101.983ZM138.805 146.169C134.73 146.169 131.441 142.88 131.441 138.805V131.441H138.805C142.88 131.441 146.169 134.73 146.169 138.805C146.169 142.88 142.88 146.169 138.805 146.169ZM84.7997 146.169C80.7248 146.169 77.4354 142.88 77.4354 138.805C77.4354 134.73 80.7248 131.441 84.7997 131.441H92.1641V138.805C92.1641 142.88 88.8747 146.169 84.7997 146.169Z" }] }, // Agent Skills repo docs/images/logos/command-code, Apache-2.0
    "agents": { vb: "0 0 32 32", paths: [{ d: "M16 0.5L29.4234 8.25V23.75L16 31.5L2.57661 23.75V8.25L16 0.5Z" }] }, // Agent Skills repo docs/favicon.svg, Apache-2.0
    "global": { vb: "0 0 32 32", paths: [{ d: "M0 2h8v8h-8Z M10 2h8v8h-8Z M20 2h8v8h-8Z M4 12h8v8h-8Z M14 12h8v8h-8Z M0 22h8v8h-8Z M10 22h8v8h-8Z M20 22h8v8h-8Z" }, { d: "M24 12h8v8h-8Z", fill: "var(--brand)" }] }, // Skills Manager's own mark, MIT
  };
  function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }
  function initialsOf(label) {
    const parts = String(label || "?").split(/[\s_-]+/).filter(Boolean);
    return ((parts[0] || "?")[0] + (parts[1] ? parts[1][0] : (parts[0] || "?")[1] || "")).toUpperCase();
  }
  /* The reading window the share is measured against. The tool cannot know the
   * model behind an agent, so this is a stated assumption, not an observation. */
  const WINDOW_BY_CONSUMER = { codex: 400000, "claude-code": 1000000, gemini: 1000000 };
  const DEFAULT_WINDOW = 1000000;

  function shortPath(p) {
    const home = String(p || "").match(/^\/home\/[^/]+|^\/Users\/[^/]+/);
    return home ? "~" + p.slice(home[0].length) : p;
  }

  function buildAgents(scopes) {
    const out = [];
    for (const s of Array.isArray(scopes) ? scopes : []) {
      const kind = String(s.kind || "");
      if (s.exists === false || (kind !== "agent" && kind !== "global" && kind !== "project")) continue;
      const brand = BRAND[s.id] || [initialsOf(s.label || s.id), PALETTE[hash(String(s.id)) % PALETTE.length]];
      out.push({
        id: s.id, name: kind === "global" ? "Your library" : s.id === "agents" ? "Shared skills folder" : (s.label || s.id), kind,
        initials: brand[0], color: brand[1], icon: AGENT_ICONS[s.id] || null, path: shortPath(s.path || ""),
        limit: WINDOW_BY_CONSUMER[s.consumer || s.id] || DEFAULT_WINDOW,
        library: kind === "global", writable: s.writable !== false && s.availability !== "read-only",
      });
    }
    return out;
  }

  /* ---------- Copies and skills ---------- */
  const BROKEN_WHY = {
    linked: ["Linked outside its folder", "This is a shortcut to a folder outside the agent's skills folder. The app does not follow it, so a write could never land somewhere unexpected.", "Copy the real folder into the skills folder instead of linking it."],
    unaddressable: ["Unusual folder name", "The app cannot address this entry using its supported skill names. Agent loading is not checked.", "Rename the folder to lowercase words joined by hyphens."],
    invalid: ["Damaged file", "The app cannot parse this skill's document. Agent loading is not checked.", "Replace it with a working copy, or repair the first lines by hand."],
    undecodable: ["Not readable text", "The file is not saved as UTF-8 text. This screen offers manual repair because text Undo cannot restore its original bytes.", "Keep a copy of the original file, then open it in a text editor and save it as UTF-8."],
    malformed: ["Damaged file", "The app cannot parse this skill's document. Agent loading is not checked.", "Replace it with a working copy, or repair the first lines by hand."],
  };

  function copyOf(record) {
    /* observedStateFor() ranks `invalid` above `linked`, but the classic Library
     * badges a refused symlink first (observedStateKeys); follow that reading so
     * the two interfaces never disagree about the same record. */
    const obs = D.observeRecord(record);
    const undecodable = /utf-?8|codec|decode/i.test(String(record.decode_error || ""));
    const state = obs.linkEscape ? "linked" : obs.notAddressable ? "unaddressable" : undecodable ? "undecodable" : D.observedStateFor(record);
    /* A refused symlink is not a damaged skill. This tool will not follow it;
     * the target and agent loading remain unobserved. */
    const broken = state === "invalid" || state === "malformed" || state === "unaddressable" || state === "undecodable";
    const linked = state === "linked";
    /* SCOPE-2: a link into another managed scope root is read read-only. It is
     * a readable copy in another managed root; effective loading is unknown. It is
     * not the agent's own copy, so nothing here may toggle or edit it. */
    const readOnly = !!obs.linkFollowed;
    /* The list request omits document bodies, so an absent `body` key means
     * "not loaded yet", never "empty document". Keep the two apart. */
    const bodyLoaded = Object.prototype.hasOwnProperty.call(record, "body") && typeof record.body === "string";
    return {
      name: String(record.name || ""),
      scope: record.scope, label: record.scope_label || record.scope,
      state: broken ? "broken" : linked ? "link" : state === "disabled" ? "off" : "on",
      kind: broken || linked ? state : "", hash: broken || linked ? "" : String(record.content_hash || ""),
      tokens: record.tokens || 0, path: record.physical_path || record.path || "",
      /* Where a followed link's document actually lives, and the fact that it
       * must not be written through this scope. */
      readOnly, linkFrom: readOnly ? String(record.link_target_root || "") : "",
      linkedTo: readOnly ? String(record.linked_to || "") : "",
      body: bodyLoaded ? record.body : "", bodyLoaded,
      description: record.description || "", record,
    };
  }

  /* Reference = the content most readable copies hold. A tie is reported as
   * ambiguous so the interface asks instead of guessing. Physical aliases are
   * separate scope views, but one physical document gets one vote. */
  function reference(copies, agentOrder) {
    const physical = new Map();
    for (const copy of copies) {
      if (copy.state === "broken" || !copy.hash) continue;
      const key = String(copy.path || copy.record.physical_path || copy.record.path || copy.scope);
      const existing = physical.get(key);
      if (!existing || (existing.readOnly && !copy.readOnly) ||
          (existing.readOnly === copy.readOnly && agentOrder(copy.scope) < agentOrder(existing.scope))) {
        physical.set(key, copy);
      }
    }
    const readable = [...physical.values()];
    const tally = new Map();
    for (const c of readable) tally.set(c.hash, (tally.get(c.hash) || []).concat(c));
    const groups = [...tally.values()].sort((a, b) => b.length - a.length || agentOrder(a[0].scope) - agentOrder(b[0].scope));
    if (!groups.length) return { hash: "", holders: [], ambiguous: false, groups: [] };
    const ambiguous = groups.length > 1 && groups[0].length === groups[1].length;
    return { hash: groups[0][0].hash, holders: groups[0], ambiguous, groups };
  }

  /* A dot-prefixed or file-like entry (".system", "README.md") in a skills folder
   * is not a skill; agents ignore it, so it is a note, never an error. */
  const NOT_A_SKILL = /^\.|\.[A-Za-z0-9]{1,5}$/;

  const STATUS = {
    bad: { key: "bad", label: "Can't be read", icon: "bad", rank: 0 },
    warn: { key: "warn", label: "Copies differ", icon: "warn", rank: 1 },
    ok: { key: "ok", label: "Working", icon: "ok", rank: 2 },
    linked: { key: "linked", label: "Linked elsewhere", icon: "info", rank: 2 },
    note: { key: "note", label: "Not a skill", icon: "info", rank: 2 },
    off: { key: "off", label: "Turned off", icon: "off", rank: 3 },
  };

  function buildSkills(records, agents) {
    const order = new Map(agents.map((a, i) => [a.id, i]));
    const rank = (id) => (order.has(id) ? order.get(id) : 99);
    const byName = new Map();
    const seen = new Map();
    for (const r of Array.isArray(records) ? records : []) {
      const name = String(r.name || "");
      if (!name) continue;
      const key = name + "\u0000" + String(r.physical_path || r.path || r.scope);
      const copy = copyOf(r);
      const previous = seen.get(key) || [];
      const sameScope = previous.find((item) => item.copy.scope === copy.scope);
      if (sameScope) {
        if (sameScope.copy.readOnly && !copy.readOnly) {
          byName.get(name)[sameScope.index] = copy;
          sameScope.copy = copy;
        }
        continue;
      }
      /* Preserve one followed link row per agent so that agent-specific views
       * reflect what that consumer loads. Ordinary duplicate-root observations
       * still collapse, and a real row is retained beside any link aliases. */
      if (previous.length && !copy.readOnly && previous.some((item) => !item.copy.readOnly)) continue;
      if (!byName.has(name)) byName.set(name, []);
      const copies = byName.get(name);
      previous.push({ index: copies.length, copy });
      seen.set(key, previous);
      copies.push(copy);
    }
    const skills = [];
    for (const [name, copies] of byName) {
      copies.sort((a, b) => rank(a.scope) - rank(b.scope));
      const ref = reference(copies, rank);
      const fileLike = NOT_A_SKILL.test(name) && copies.every((c) => c.state === "broken" && D.observeRecord(c.record).notAddressable);
      const status = fileLike ? STATUS.note : copies.some((c) => c.state === "broken") ? STATUS.bad
        : !copies.some((c) => c.state === "on" || c.state === "link") ? STATUS.off
        : ref.groups.length > 1 ? STATUS.warn
        : copies.some((c) => c.state === "link") ? STATUS.linked : STATUS.ok;
      /* Name each distinct text: A is the one most places hold. This answers the
       * question users ask most, "which copy does each agent have". */
      const versionByHash = new Map();
      ref.groups.forEach((g, i) => {
        const version = String.fromCharCode(65 + Math.min(i, 25));
        versionByHash.set(g[0].hash, version);
        for (const c of g) c.version = version;
      });
      for (const c of copies) if (!c.version && versionByHash.has(c.hash)) c.version = versionByHash.get(c.hash);
      const pick = (ref.holders[0] || copies.find((c) => c.state !== "broken" && !c.readOnly) || copies[0]);
      const category = (copies.map((c) => c.record.category).find((c) => c && c !== "uncategorized")) || "";
      skills.push({
        name, copies, status, ref, category,
        description: (pick.description || copies.map((c) => c.description).find(Boolean) || ""),
        tokens: pick.tokens || 0, primary: pick,
        differing: ref.hash ? copies.filter((c) => c.state !== "broken" && c.hash && c.hash !== ref.hash) : [],
        broken: copies.filter((c) => c.state === "broken"),
        tools: copies.filter((c) => !agents.find((a) => a.id === c.scope && a.library)),
      });
    }
    skills.sort((a, b) => a.name.localeCompare(b.name));
    return skills;
  }

  /* ---------- Per-agent summary ---------- */
  function agentInfo(agent, skills, suggested) {
    const mine = skills.filter((s) => s.status !== STATUS.note && s.copies.some((c) => c.scope === agent.id));
    const copyIn = (s) => s.copies.find((c) => c.scope === agent.id);
    const on = mine.filter((s) => copyIn(s).state === "on");
    const tokens = on.reduce((n, s) => n + (copyIn(s).tokens || 0), 0);
    const differing = mine.filter((s) => s.differing.some((c) => c.scope === agent.id));
    const broken = mine.filter((s) => copyIn(s).state === "broken" && s.status === STATUS.bad);
    const pct = agent.limit ? Math.round((tokens / agent.limit) * 1000) / 10 : 0;
    const links = mine.filter((s) => copyIn(s).state === "link");
    const key = broken.length ? "bad" : differing.length ? "warn" : "ok";
    return { id: agent.id, agent, mine, on, tokens, differing, broken, links, pct, key, over: pct > suggested };
  }

  /* ---------- Problems (the Inbox) ---------- */
  function problems(skills, agents, infos, suggested) {
    const name = (id) => (agents.find((a) => a.id === id) || { name: id }).name;
    const out = [];
    for (const s of skills) {
      if (s.status === STATUS.note) {
        out.push({ id: "note:" + s.name, key: "info", skill: s.name, agents: s.broken.map((c) => c.scope), noteOnly: true,
          title: `“${s.name}” looks like a file or system folder, not a skill`, short: "Not a skill",
          text: "Agents ignore entries like this, so nothing is broken. You can leave it where it is.", action: "Got it" });
      } else if (s.status.key === "bad") {
        const repairable = (c) => c.kind === "invalid" || c.kind === "malformed";
        const b = s.broken.find((c) => !repairable(c)) || s.broken[0];
        const why = BROKEN_WHY[b.kind] || BROKEN_WHY.invalid;
        const good = s.copies.find((c) => !c.readOnly && c.hash && (c.state === "on" || c.state === "off"))
          || s.copies.find((c) => c.hash && (c.state === "on" || c.state === "off"));
        const fixable = !!good && s.broken.every(repairable);
        const sole = !good;
        out.push({
          id: "bad:" + s.name, key: "bad", skill: s.name, agents: s.broken.map((c) => c.scope), kind: b.kind,
          title: sole ? `No agent can read “${s.name}”` : `${name(b.scope)} can't read “${s.name}”`,
          short: why[0], text: why[1], how: why[2],
          /* Only a damaged document can be replaced from a working copy; the
           * other kinds need a change on disk the app does not make. */
          fixable, source: good ? good.scope : "",
          action: fixable ? `Replace with ${name(good.scope)}'s copy` : "Show me how",
        });
      } else if (s.status.key === "warn") {
        const targets = s.differing.filter((c) => !c.readOnly).map((c) => c.scope);
        const names = targets.map(name);
        out.push({
          id: "warn:" + s.name, key: "warn", skill: s.name, agents: targets, ambiguous: s.ref.ambiguous,
          title: `${join(names)} ${names.length === 1 ? "has a different copy" : "have different copies"} of “${s.name}”`,
          short: "Copies differ",
          text: `Your agents hold different versions of this skill, so they may behave differently until the copies match.`,
          action: `Make ${names.length === 1 ? names[0] + "'s copy" : names.length + " copies"} match`,
        });
      }
    }
    for (const inf of infos) {
      if (inf.agent.library || !inf.over || !inf.on.length) continue;
      out.push({
        id: "space:" + inf.id, key: "info", agent: inf.id, space: true,
        title: `${inf.agent.name}'s skills would fill ${inf.pct}% of a reading window`,
        short: "Suggestion",
        text: `If every skill were read in full, that leaves little room for your code. Turning off skills you rarely use in ${inf.agent.name} frees space.`,
        action: "Done",
      });
    }
    for (const inf of infos) {
      if (inf.agent.library || !inf.links.length) continue;
      out.push({
        id: "link:" + inf.id, key: "info", agent: inf.id, linkAgent: true,
        title: `${inf.agent.name} has ${plural(inf.links.length, "skill")} linked from outside its folder`,
        short: "For your information",
        text: "These are shortcuts to folders elsewhere. This app does not follow them, so their contents and agent loading are unobserved; it cannot compare or edit them.",
        action: "Got it",
      });
    }
    const rank = { bad: 0, warn: 1, info: 2 };
    return out.sort((a, b) => rank[a.key] - rank[b.key] || a.title.localeCompare(b.title));
  }

  function build(records, scopes, opts) {
    const suggested = (opts && opts.suggested) || 100;
    const agents = buildAgents(scopes);
    const skills = buildSkills(records, agents);
    const infos = agents.map((a) => agentInfo(a, skills, suggested));
    const real = infos.filter((i) => !i.agent.library && i.mine.length);
    return {
      agents, skills, infos, suggested,
      rooms: real, problems: problems(skills, agents, infos, suggested),
      byName: new Map(skills.map((s) => [s.name, s])),
      agent: (id) => agents.find((a) => a.id === id),
      info: (id) => infos.find((i) => i.id === id),
    };
  }

  /* ---------- Line diff (LCS) ---------- */
  const MAX_DIFF_CELLS = 4000000;
  function diffLines(a, b, includeEmpty = false) {
    const n = a.length, m = b.length;
    if (n * m > MAX_DIFF_CELLS) { return [...a.map((x) => ({ t: "del", x })), ...b.map((x) => ({ t: "add", x }))].filter((l) => l.x.trim()); }
    const dp = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
    for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    const out = []; let i = 0, j = 0;
    while (i < n && j < m) {
      if (a[i] === b[j]) { out.push({ t: "same", x: a[i] }); i++; j++; }
      else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ t: "del", x: a[i++] });
      else out.push({ t: "add", x: b[j++] });
    }
    while (i < n) out.push({ t: "del", x: a[i++] });
    while (j < m) out.push({ t: "add", x: b[j++] });
    return includeEmpty ? out : out.filter((l) => l.x.trim());
  }
  const plainLine = (l) => String(l).replace(/^#{1,3}\s+/, "").replace(/^[-*]\s+/, "").replace(/^>\s?/, "").replace(/\*\*(.+?)\*\*/g, "$1");
  /* Only changed lines, plus one line of context before each change. */
  function changes(fromBody, toBody) {
    const d = diffLines(String(fromBody).split("\n"), String(toBody).split("\n"));
    return d.filter((l, i) => l.t !== "same" || (d[i + 1] && d[i + 1].t !== "same" && (!d[i - 1] || d[i - 1].t === "same")));
  }

  /* Preserve Markdown, whitespace and document line numbers. A replacement
   * occupies one row in split view, with its deletion first in unified view. */
  function documentPreview(before, after, limit = 48) {
    if (before === after) return { status: "same" };
    const a = before.split(/\r?\n/), b = after.split(/\r?\n/);
    const oversizedLine = (line) => line.length > 4096;
    if (a.length * b.length > MAX_DIFF_CELLS || a.some(oversizedLine) || b.some(oversizedLine)) return { status: "too-large" };
    const diff = diffLines(a, b, true);
    const rows = [], removed = [], added = [];
    let oldLine = 0, newLine = 0, total = 0;
    const append = (row) => {
      total++;
      if (rows.length < limit) rows.push(row);
    };
    const flush = () => {
      for (let i = 0; i < Math.max(removed.length, added.length); i++) {
        append({ before: removed[i], after: added[i] });
      }
      removed.length = 0;
      added.length = 0;
    };
    for (const [i, line] of diff.entries()) {
      if (line.t === "del") removed.push({ number: ++oldLine, text: line.x, kind: "del" });
      else if (line.t === "add") added.push({ number: ++newLine, text: line.x, kind: "add" });
      else {
        flush();
        oldLine++;
        newLine++;
        if (line.x.trim() && diff[i + 1] && diff[i + 1].t !== "same") {
          append({ before: { number: oldLine, text: line.x, kind: "same" },
            after: { number: newLine, text: line.x, kind: "same" }, context: true });
        }
      }
    }
    flush();
    return total ? { status: "changes", rows, omitted: total - rows.length } : { status: "line-endings" };
  }

  /* ---------- Escaped Markdown (with optional highlighted lines) ---------- */
  function stripFrontmatter(text) {
    const m = String(text).match(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/);
    return m ? String(text).slice(m[0].length) : String(text);
  }
  function renderDoc(src, marks) {
    const set = marks || new Set();
    /* Links are shown as text plus their address, never as live anchors: a
     * skill body is untrusted, and a reader should see where a link points. */
    const inline = (t) => esc(t)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>")
      /* One level of balanced parentheses, so `…/Foo_(bar)` is not cut short. */
      .replace(/\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)/g, "$1 <code>$2</code>");
    const wrap = (raw, html) => (set.has(raw.trim()) ? `<mark>${html}</mark>` : html);
    const out = []; let list = null; let fence = false;
    const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
    for (const line of String(src).split("\n")) {
      let m;
      if (/^```/.test(line)) { close(); out.push(fence ? "</pre>" : "<pre>"); fence = !fence; }
      else if (fence) out.push(esc(line) + "\n");
      else if ((m = line.match(/^#{1,3}\s+(.*)/))) { close(); out.push(`<h2>${inline(m[1])}</h2>`); }
      else if ((m = line.match(/^\d+\.\s+(.*)/))) { if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push(`<li>${wrap(line, inline(m[1]))}</li>`); }
      else if ((m = line.match(/^[-*]\s+(.*)/))) { if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push(`<li>${wrap(line, inline(m[1]))}</li>`); }
      else if ((m = line.match(/^>\s?(.*)/))) { close(); out.push(`<blockquote>${wrap(line, inline(m[1]))}</blockquote>`); }
      else if (line.trim()) { close(); out.push(`<p>${wrap(line, inline(line))}</p>`); }
      else close();
    }
    close();
    if (fence) out.push("</pre>");
    return out.join("");
  }

  const ACRONYMS = { sql: "SQL", api: "API", pr: "PR", k8s: "K8s", a11y: "Accessibility", ui: "UI", ux: "UX", css: "CSS", ci: "CI", cd: "CD", aws: "AWS" };
  /* The canonical skill-name rule, as the backend enforces it. */
  const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
  const validName = (n) => typeof n === "string" && n.length <= 64 && NAME_RE.test(n);

  /* Match observed facade copies to the existing documented root inventory.
   * No filesystem walk, precedence winner, or runtime invocation is inferred. */
  function consumerDiscovery(name, records, scopes, adapters) {
    const normalize = (value) => String(value || "").replace(/\\/g, "/").replace(/\/+$/, "");
    const scopeRows = Array.isArray(scopes) ? scopes : [];
    const input = Array.isArray(records) ? records : [];
    const consumers = Array.isArray(adapters) ? adapters : [];
    const copies = input.slice(0, 10000).filter((r) => r && r.name === name);
    const partial = input.length > 10000 || scopeRows.length > 128 || consumers.length > 32;
    const rows = consumers.slice(0, 32).map((adapter) => {
      const roots = Array.isArray(adapter.candidate_roots) ? adapter.candidate_roots.slice(0, 64) : [];
      const match = (s, root) => {
        const path = normalize(s.path), rel = normalize(root.home_path || root.relative_path);
        if (root.scope) return s.id === root.scope;
        if (root.absolute_path) return path === normalize(root.absolute_path);
        if (root.home_path) return s.kind === "agent" && !!rel && path.endsWith("/" + rel);
        return !!root.relative_path && s.kind === "project" && !!rel && path.endsWith("/" + rel);
      };
      const scopeMappingUnknown = roots.some((root) => root.scope && !scopeRows.slice(0, 128).some((scope) => scope.id === root.scope));
      const within = (copy, scope, root) => {
        const base = normalize(scope.path), path = normalize(copy.path || copy.physical_path);
        if (!base || !path.startsWith(base + "/")) return false;
        const relative = path.slice(base.length + 1).split("/");
        if (relative.some((part) => !part || part === "." || part === "..")) return false;
        return relative.length === 1 || !!root.recursive || !!root.nested;
      };
      const held = copies.filter((copy) => scopeRows.slice(0, 128).some((scope) =>
        scope.id === copy.scope && roots.some((root) => match(scope, root) && within(copy, scope, root))));
      const unique = new Map();
      for (const copy of held) {
        const key = String(copy.physical_path || copy.path || copy.scope);
        if (!unique.has(key)) unique.set(key, copy);
      }
      const observed = [...unique.values()];
      const declarations = new Set();
      for (const copy of held) {
        if (copy.consumer !== adapter.id) continue;
        const sources = copy.native_state && copy.native_state.sources;
        for (const source of Array.isArray(sources) ? sources.slice(0, 32) : []) {
          if (typeof source.declared === "string") declarations.add(source.declared.slice(0, 128));
        }
      }
      return { id: String(adapter.id || "").slice(0, 128), label: String(adapter.label || adapter.id || "").slice(0, 128),
        observed: observed.length, disabled: observed.filter((copy) => copy.disabled).length,
        unreadable: observed.filter((copy) => copy.malformed || copy.document_missing || copy.link_escape || copy.decode_error).length,
        declarations: [...declarations].sort(), source: typeof (adapter.precedence || {}).evidence === "string" && /^https:\/\//.test(adapter.precedence.evidence) ? adapter.precedence.evidence : "",
        order: String((adapter.precedence || {}).status || "unknown"),
        scope_mapping_unknown: scopeMappingUnknown,
        partial: partial || scopeMappingUnknown || (Array.isArray(adapter.candidate_roots) && adapter.candidate_roots.length > 64),
      };
    });
    return { rows, partial: partial || rows.some((row) => row.partial), instances_observed: copies.length };
  }

  const toolGroups = [
    { key: "add", label: "Add and organize", items: [
      { id: "install", name: "Install", text: "Bring skills in from the skills.sh registry, a package command or a local folder.", commandLabel: "Install" },
      { id: "profiles", name: "Profiles", text: "Save named sets of skills and switch them on together.", commandLabel: "Profiles" },
      { id: "templates", name: "Templates", text: "Keep starting documents for new skills.", commandLabel: "Templates" },
    ] },
    { key: "inspect", label: "Inspect and maintain", items: [
      { id: "quality", name: "Quality", text: "Find broken documents, weak descriptions and copies that drifted apart.", commandLabel: "Quality and validation" },
      { id: "workspaces", name: "Workspaces", text: "See where each agent looks for skills and what a project adds.", commandLabel: "Workspaces" },
      { id: "source-update", name: "Update from folder", text: "Replace one exact copy with a newer folder, after a full review." },
      { id: "settings", name: "Settings", text: "Theme, text size, number format and index maintenance.", commandLabel: "Settings and index maintenance" },
    ] },
    { key: "ai", label: "AI assist (your own key)", items: [
      { id: "ai-ask", name: "Ask your library", text: "Ask which of your skills fits a task, in plain words. Only names and descriptions are sent.", commandLabel: "AI ask your library" },
      { id: "ai-draft", name: "Draft a skill", text: "Turn a brief into a skill, then validate and test it against the skills already in a scope.", commandLabel: "Draft a skill" },
      { id: "ai-concise", name: "Shorten a skill", text: "Propose a concise primary document and new references, then review the exact folder update.", commandLabel: "Shorten a skill" },
      { id: "ai-profile", name: "Suggest a profile", text: "Use project metadata to suggest an editable profile from existing skills.", commandLabel: "Suggest a profile" },
      { id: "ai-trigger", name: "Trigger test", text: "Simulate which skill your configured model selects from names and descriptions.", commandLabel: "AI trigger test" },
      { id: "ai-improve", name: "Improve a description", text: "Get rewrites that are re-tested and recommended only when they measurably help.", commandLabel: "AI improve description" },
      { id: "ai-budget", name: "Fit the listing budget", text: "Propose shorter descriptions and compare their simulated selection rates.", commandLabel: "AI fit listing budget" },
      { id: "ai-evals", name: "Does it help?", text: "Run a skill's eval cases with and without it, graded by its own assertions.", commandLabel: "AI eval runner" },
      { id: "ai-ablate", name: "Does it earn its place?", text: "Test a skill or one section by removing it; removal is proposed when results are not worse.", commandLabel: "AI ablate and retire" },
      { id: "ai-conflicts", name: "Contradiction check", text: "Find lines in CLAUDE.md and AGENTS.md that may disagree with each other or your skills.", commandLabel: "Contradiction check" },
      { id: "ai-overlap", name: "Overlap check", text: "Find skills that compete for the same requests or give conflicting instructions.", commandLabel: "AI overlap check" },
      { id: "ai-explain", name: "Explain risk findings", text: "Scan an installed skill for risky patterns, then get a second opinion that can only demote a finding.", commandLabel: "AI explain risk findings" },
      { id: "ai-port", name: "Porting notes", text: "See what changes when another agent reads a skill, from documented facts.", commandLabel: "AI porting notes" },
      { id: "ai-settings", name: "AI settings", text: "Connect Anthropic, an OpenAI-compatible service or a local model, and set spending caps.", commandLabel: "AI settings" },
    ] },
  ].map((group) => Object.freeze({ ...group, items: Object.freeze(group.items.map((item) => Object.freeze(item))) }));
  const toolItems = Object.freeze(toolGroups.flatMap((group) => group.items));
  const toolIds = Object.freeze(toolItems.map((item) => item.id));

  const titleCase = (n) => String(n).split("-").map((w, i) => ACRONYMS[w.toLowerCase()] || (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w)).join(" ");

  /* Saved browser baselines compare observed primary documents only. Absence
   * from either scan is not proof of deletion, health, or package contents. */
  const documentBaseline = (() => {
    const maxInstances = 10000, maxChars = 2 * 1024 * 1024;
    const hex = (v) => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
    const fail = (message) => { throw new Error(message); };
    const object = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
    const keys = (v, expected) => object(v) && Object.keys(v).sort().join(",") === expected.slice().sort().join(",");
    function read(raw) {
      if (raw == null || raw === "") return null;
      if (typeof raw !== "string" || raw.length > maxChars) fail("Saved document baseline is invalid or too large.");
      let value;
      try { value = JSON.parse(raw); } catch (_) { fail("Saved document baseline is invalid."); }
      if (!keys(value, ["version", "context_id", "captured_at", "instances"]) || value.version !== 1 || !hex(value.context_id) ||
          typeof value.captured_at !== "string" || !Array.isArray(value.instances) || value.instances.length > maxInstances) fail("Saved document baseline is invalid.");
      const date = new Date(value.captured_at);
      if (!Number.isFinite(date.getTime()) || date.toISOString() !== value.captured_at) fail("Saved document baseline has an invalid date.");
      const seen = new Set();
      for (const pair of value.instances) {
        if (!Array.isArray(pair) || pair.length !== 2 || !hex(pair[0]) || !hex(pair[1]) || seen.has(pair[0])) fail("Saved document baseline has invalid document fingerprints.");
        seen.add(pair[0]);
      }
      return value;
    }
    function current(value) {
      if (!object(value) || !hex(value.context_id) || typeof value.partial !== "boolean" || !Array.isArray(value.instances) || value.instances.length > maxInstances) fail("Document scan is invalid.");
      const seen = new Set();
      const instances = value.instances.map((row) => {
        if (!object(row) || !hex(row.id) || !hex(row.content_hash) || typeof row.name !== "string" || row.name.length > 512 || typeof row.scope !== "string" || row.scope.length > 512 || seen.has(row.id)) fail("Document scan has invalid fingerprints.");
        seen.add(row.id);
        return { id: row.id, content_hash: row.content_hash, name: row.name, scope: row.scope };
      });
      return { context_id: value.context_id, instances, partial: value.partial };
    }
    function snapshot(envelope) {
      const hygiene = envelope && envelope.hygiene;
      const section = hygiene && hygiene.document_fingerprints;
      if (!section) fail("Document fingerprint evidence is unavailable.");
      if (!object(section) || section.version !== 1 || !["observed", "partial"].includes(section.status) || typeof section.coverage !== "string" || !Number.isSafeInteger(section.omitted) || section.omitted < 0 ||
          (hygiene.degraded != null && !Array.isArray(hygiene.degraded)) || (envelope.degraded != null && !Array.isArray(envelope.degraded)) ||
          (hygiene.summary != null && !object(hygiene.summary))) fail("Document fingerprint evidence is invalid.");
      return current({ context_id: section.context_id, instances: section.instances,
        partial: section.status !== "observed" || section.omitted > 0 || !!(hygiene.degraded || []).length || !!(hygiene.summary || {}).partial || !!(envelope.degraded || []).length });
    }
    function checkedBaseline(value) {
      if (value == null) return null;
      let raw;
      try { raw = JSON.stringify(value); } catch (_) { fail("Saved document baseline is invalid."); }
      return read(raw);
    }
    function compare(scan, baseline) {
      scan = current(scan); baseline = checkedBaseline(baseline);
      const result = { status: !baseline ? "missing" : baseline.context_id !== scan.context_id ? "other-context" : "compared", changed: [], changed_count: 0, compared_count: 0, unobserved_count: 0, partial: scan.partial };
      if (result.status !== "compared") return result;
      const previous = new Map(baseline.instances), observed = new Set();
      for (const row of scan.instances) {
        if (!previous.has(row.id)) continue;
        observed.add(row.id); result.compared_count++;
        if (previous.get(row.id) !== row.content_hash) {
          result.changed_count++;
          if (result.changed.length < 100) result.changed.push(row);
        }
      }
      result.unobserved_count = previous.size - observed.size;
      return result;
    }
    function merge(scan, baseline, capturedAt) {
      scan = current(scan); baseline = checkedBaseline(baseline);
      if (scan.partial) fail("Cannot save a partial document scan.");
      if (baseline && baseline.context_id !== scan.context_id) fail("Saved document baseline belongs to another context.");
      const entries = new Map(baseline ? baseline.instances : []);
      for (const row of scan.instances) entries.set(row.id, row.content_hash);
      if (entries.size > maxInstances) fail("Saved document baseline has too many documents.");
      const value = { version: 1, context_id: scan.context_id, captured_at: capturedAt, instances: [...entries].sort((a, b) => a[0].localeCompare(b[0])) };
      return read(JSON.stringify(value));
    }
    return Object.freeze({ maxInstances, maxChars, read, snapshot, compare, merge });
  })();

  window.SkillsV2Model = Object.freeze({
    plural, join, words, titleCase, shortPath, build, STATUS, BROKEN_WHY, validName,
    toolGroups: Object.freeze(toolGroups), toolItems, toolIds,
    diffLines, changes, documentPreview, plainLine, renderDoc, stripFrontmatter, documentBaseline, consumerDiscovery,
  });
})();
