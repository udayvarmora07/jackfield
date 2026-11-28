/* One owner for browser hash routes and their compatibility redirects. */
"use strict";

(function () {
  const app = window.Jackfield;
  const legacy = new Map([
    ["", "skills"], ["home", "skills"], ["map", "skills"], ["inbox", "attention"],
    ["recovery", "trash"], ["tools", "advanced"], ["tools/settings", "settings"], ["advanced/settings", "settings"],
  ]);
  const titles = {
    skills: "Skills", home: "Agents overview", map: "Sync map", inbox: "Needs attention",
    recovery: "Trash & backups", tools: "Advanced", tracking: "What to track", missing: "Page not found",
  };

  function partsOf(hash) {
    const text = String(hash || "").replace(/^#\/?/, "");
    const split = text.indexOf("?");
    const path = split < 0 ? text : text.slice(0, split);
    const query = split < 0 ? "" : text.slice(split);
    return { path, query };
  }

  function canonicalPath(path) {
    if (legacy.has(path)) return legacy.get(path);
    if (path.startsWith("skill/")) return "skills/" + path.slice(6);
    if (path.startsWith("tools/")) return "advanced/" + path.slice(6);
    return path;
  }

  function segment(part) {
    try {
      const value = decodeURIComponent(part || "");
      return !value || value.length > 256 || /[\/\\\x00-\x1f\x7f]/.test(value) ||
        value === "." || value === ".." ? "" : value;
    } catch { return ""; }
  }

  function trackingRoute(parts) {
    const form = parts[2];
    if (parts.length === 2) return { page: "tracking", name: "" };
    if (parts.length === 3 && ["add-agent", "add-project"].includes(form)) {
      return { page: "tracking", name: form };
    }
    if (parts.length === 4 && form === "agent" && /^custom-[a-z0-9-]+$/.test(parts[3])) {
      return { page: "tracking", name: "agent:" + parts[3] };
    }
    return { page: "missing" };
  }

  function match(path, query, toolIds) {
    const parts = path.split("/");
    if (parts[0] === "settings" && parts[1] === "tracking") return trackingRoute(parts);
    if (parts[0] === "skills" && parts.length > 1) {
      const name = segment(parts[1]);
      const screen = parts[2] || "";
      if (name && (parts.length === 2 || (parts.length === 3 && ["edit", "why"].includes(screen)))) {
        return { page: "skill", name, screen, file: query.get("view") === "file",
          copyScope: query.get("scope"), copyPath: query.get("copy"), selected: screen ? null : query.get("sel") };
      }
      return { page: "missing" };
    }
    if (parts[0] === "advanced" && parts.length === 2 && toolIds.includes(parts[1])) {
      return { page: "tools", tool: parts[1] };
    }
    switch (path) {
      case "skills": {
        const view = query.get("view");
        return { page: "skills", view, search: query.get("q"), agent: query.get("agent"), only: query.get("only"), selected: query.get("sel") };
      }
      case "new": return { page: "skills", screen: "new", template: query.get("template") };
      case "attention": return { page: "inbox", item: query.get("item") };
      case "trash": return { page: "recovery" };
      case "advanced": return { page: "tools", tool: "tools" };
      case "settings": return { page: "tools", tool: "settings" };
      default: return { page: "missing" };
    }
  }

  function parseRoute(hash, toolIds = window.SkillsV2Model.toolIds) {
    const { path, query } = partsOf(hash);
    const canonical = canonicalPath(path);
    const params = new URLSearchParams(query);
    // Retired Skills views are replaced by the table. Keep its other filters.
    if (canonical === "skills" && params.has("view")) {
      params.delete("view");
      const remaining = params.toString();
      const href = "#/skills" + (remaining ? "?" + remaining : "");
      return { ...match(canonical, params, toolIds), href };
    }
    const href = "#/" + canonical + query;
    return { ...match(canonical, params, toolIds), href };
  }

  const current = () => parseRoute(location.hash);
  const routeHref = (path, query = {}) => {
    const href = "#/" + path;
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value != null && value !== "") params.set(key, value);
    }
    return params.size ? href + "?" + params : href;
  };
  const skillHref = (name, screen = "", query) =>
    routeHref("skills/" + encodeURIComponent(name) + (screen ? "/" + screen : ""), query);
  const toolHref = (id) => routeHref(id === "settings" ? "settings" : "advanced/" + encodeURIComponent(id));
  const replace = (href) => {
    if (href !== location.hash) history.replaceState(history.state, "", href);
  };
  const allowedHash = (href) => typeof href === "string" && href.startsWith("#/") && !href.startsWith("#//");
  const go = (href) => { if (allowedHash(href)) location.hash = parseRoute(href).href; };

  function title(route) {
    if (route.page === "skill") {
      if (route.screen === "edit") return "Edit " + route.name;
      if (route.screen === "why") return "Why isn’t " + route.name + " running?";
      return route.name;
    }
    if (route.screen === "new") return "New skill";
    if (route.page === "tools" && route.tool !== "tools") {
      return window.SkillsV2Model.toolItems.find((tool) => tool.id === route.tool)?.name || titles.tools;
    }
    return titles[route.page];
  }

  app.router = { parseRoute, current, routeHref, skillHref, toolHref, replace, go, title,
    onChange: (handler) => window.addEventListener("hashchange", () => handler(current())) };
})();
