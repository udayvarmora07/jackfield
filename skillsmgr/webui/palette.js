/* Search data and close-name matching for the shared palette and Not found. */
"use strict";

(function () {
  const jack = window.Jackfield;
  const { routeHref, skillHref, toolHref } = jack.router;
  const places = [
    { label: "Skills", path: "#/skills", text: "Find your skills and see where they live", icon: "list" },
    { label: "Needs attention", path: "#/attention", text: "Review differences and unreadable copies", icon: "warn" },
    { label: "Trash & backups", path: "#/trash", text: "Restore removed skills and manage backups", icon: "trash" },
    { label: "Advanced", path: "#/advanced", text: "Install, Quality, AI assist and more", icon: "tools" },
  ];
  const pages = [...places,
    { label: "Settings", path: "#/settings", text: "Theme, text size and maintenance", icon: "tools" },
    { label: "What to track", path: "#/settings/tracking", text: "Manage agents and project folders", icon: "tools" },
  ];
  const actions = [
    { label: "New skill", path: "#/new", text: "Create a skill in one or more places", icon: "plus" },
    { label: "Fix problems one by one", path: "#/attention", text: "Review skills that need attention", icon: "warn" },
    { label: "Show only skills with problems", path: "#/skills?only=problems", text: "Filter the Skills list", icon: "list" },
    { label: "Download a backup", action: "backup", text: "Save your skills in one file", icon: "arrow" },
    { label: "Switch theme", action: "theme", text: "Choose light, dark or match your computer", icon: "moon" },
    { label: "Refresh files", action: "refresh", text: "Read the skill folders again", icon: "arrow" },
    { label: "Add other agent", path: "#/settings/tracking/add-agent", text: "Track another agent's skills", icon: "plus" },
    { label: "Add project folder", path: "#/settings/tracking/add-project", text: "Track skills in a project", icon: "plus" },
  ];

  const normalize = (text) => String(text || "").trim().toLowerCase();
  const matches = (text, words) => words.every((word) => text.includes(word));
  const wordsOf = (query) => normalize(query).split(/\s+/).filter(Boolean);
  const namesOfAgents = (skill, agentName) => skill.tools.map((copy) => agentName(copy.scope)).join(", ");
  const skillMatches = (skill, words, agents) =>
    matches(normalize([skill.name, skill.description, skill.category, agents].join(" ")), words);

  function closeName(value, skills) {
    const query = normalize(value);
    if (!query || query.length > 100) return null;
    const limit = query.length < 5 ? 1 : query.length < 10 ? 2 : 3;
    let best = limit + 1, guess = null;
    for (const skill of skills) {
      const candidates = query.includes("-") ? [skill.name] : [skill.name, ...skill.name.split("-")];
      for (const candidate of candidates) {
        if (Math.abs(candidate.length - query.length) >= best) continue;
        const distance = editDistance(query, candidate, best - 1);
        if (distance < best) { best = distance; guess = skill; }
      }
      if (best === 0) break;
    }
    return guess;
  }

  function editDistance(left, right, limit) {
    let row = Array.from({length: right.length + 1}, (_, n) => n);
    for (let i = 1; i <= left.length; i++) {
      const next = [i];
      let min = i;
      for (let n = 1; n <= right.length; n++) {
        const value = Math.min(row[n] + 1, next[n - 1] + 1,
          row[n - 1] + (left[i - 1] === right[n - 1] ? 0 : 1));
        next[n] = value;
        min = Math.min(min, value);
      }
      if (min > limit) return limit + 1;
      row = next;
    }
    return row[right.length];
  }

  function skillMatch(skill, words, agentName) {
    const agents = namesOfAgents(skill, agentName);
    if (!skillMatches(skill, words, agents)) return null;
    return { label: skill.name, path: skillHref(skill.name), text: [skill.description, agents].filter(Boolean).join(" · "), icon: "list" };
  }

  function search(value, skills, agentName, tools, toolEnabled) {
    const query = normalize(value).slice(0, 200);
    const words = wordsOf(query);
    const found = skills.map((skill) => skillMatch(skill, words, agentName)).filter(Boolean);
    found.sort((left, right) => Number(right.label.startsWith(query)) - Number(left.label.startsWith(query)));
    const toolActions = tools.filter((tool) => tool.commandLabel && toolEnabled(tool.id)).map((tool) => ({
      label: tool.commandLabel, text: tool.name + " · " + tool.text, path: toolHref(tool.id), icon: "tools",
    }));
    const hit = (item) => matches(normalize(item.label + " " + item.text), words);
    const actionsFound = [...actions, ...toolActions].filter(hit);
    const pageHits = pages.filter(hit);
    const groups = [
      { title: "Skills", items: found.slice(0, 5) },
      { title: "Actions", items: actionsFound.slice(0, query ? 12 : 5) },
      { title: "Pages", items: pageHits },
    ];
    if (query && found.length) {
      const text = String(value || "").trim().slice(0, 200);
      groups[0].items.push({
        label: found.length === 1 ? "Show 1 match in Skills" : "Show all " + found.length + " matches in Skills",
        path: routeHref("skills", { q: text }), icon: "search",
      });
    }
    return groups.filter((group) => group.items.length);
  }

  jack.palette = { places, search, closeName, wordsOf,
    matchesSkill: (skill, words, agentName) => skillMatches(skill, words, namesOfAgents(skill, agentName)) };
})();
