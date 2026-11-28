/* The skill checklist keeps filesystem observations and discovery evidence scoped to each place. */
"use strict";

(() => {
  const Jack = window.Jackfield;
  const Domain = window.SkillManagerDomain;
  const consumers = new Set(["claude-code", "codex", "cursor", "opencode", "gemini", "commandcode"]);
  const sourceStatuses = new Set(["ok", "missing", "unobserved"]);
  const blocks = new Set(["off", "disabled", "deny"]);
  const permits = new Set(["on", "enabled", "allow", "ask"]);
  const rows = [
    { id: "found", label: "Found", help: "There is a skill folder with a skill file." },
    { id: "readable", label: "Readable", help: "The file is plain text with a name and description." },
    { id: "on", label: "Switched on", help: "The skill file is switched on in this folder." },
    { id: "settings", label: "Settings allow it", help: "The settings we can read do not turn the skill off." },
    { id: "loaded", label: "Actually loaded", help: "The agent really picked it up." },
  ];
  const legend = [
    { state: "ok", word: "Checked and fine" }, { state: "fail", word: "Fails here" },
    { state: "unknown", word: "Unknown" }, { state: "skip", word: "Not checked yet" },
  ];
  const unknown = { state: "unknown", word: "Unknown" };
  const skipped = { state: "skip", word: "—" };
  const ok = (word) => ({ state: "ok", word });
  const fail = (word, path = "") => ({ state: "fail", word, path });

  function placesIn(scopes) {
    return scopes.filter((scope) => scope.exists !== false && ["agent", "project"].includes(scope.kind));
  }

  function discoveryQuery(scope, project, name) {
    if (!consumers.has(scope.consumer)) return "";
    const query = new URLSearchParams({ explain: scope.consumer, skill: name });
    if (scope.kind === "project" && project) query.set("project", project);
    return `/api/doctor?${query}`;
  }

  function settingsCell(record, scope) {
    const state = record.native_state;
    const sources = state?.sources;
    // Native settings are observed in the server's startup context. The selected
    // project's settings may differ and the doctor route only checks discovery.
    if (scope.kind === "project" || state?.consumer !== scope.consumer || !Array.isArray(sources) || !sources.length) return unknown;
    if (sources.some((source) => !sourceStatuses.has(source?.status) || source.invalid_entries)) return unknown;
    const declarations = sources.filter((source) => source.status === "ok" && source.declared);
    if (declarations.some((source) => String(source.source).startsWith("project"))) return unknown;
    const denied = declarations.filter((source) => blocks.has(source.declared));
    const allowed = declarations.some((source) => permits.has(source.declared));
    if (scope.consumer === "opencode" && denied.length && allowed) return unknown;
    const observed = state.observed_setting;
    if (blocks.has(observed) || (!observed && denied.length)) {
      const source = denied.length === 1 ? denied[0].source : "";
      const path = scope.consumer === "claude-code" && source === "user" ? "~/.claude/settings.json" : "";
      return fail("Turned off", path);
    }
    if (denied.length && !permits.has(observed)) return unknown;
    return sources.some((source) => source.status === "ok" || source.status === "missing") ? ok("No block seen") : unknown;
  }

  function copyChecks(record, scope) {
    const observed = Domain.observeRecord(record);
    const found = record.document_missing ? fail("No skill file") : observed.linkEscape ? unknown : ok("Yes");
    let readable = unknown;
    if (!observed.linkEscape && !observed.notAddressable) {
      readable = observed.malformedDocument ? fail("Can’t read") : record.content_hash ? ok("Yes") : unknown;
    }
    const switched = observed.isDisabled ? fail("Off") : record.disabled === false || record.disabled === 0 ? ok("On") : unknown;
    return [found, readable, switched, settingsCell(record, scope)];
  }

  function mergedCell(copies, step) {
    const first = copies[0][step];
    if (copies.some((checks) => checks[step].state !== first.state || checks[step].word !== first.word)) return unknown;
    return copies.every((checks) => checks[step].path === first.path) ? first : { ...first, path: "" };
  }

  function doctorFound(report, name, scope) {
    // A reported name, a winner, or a redacted root alone does not identify a
    // particular tracked place. Accept only an observation of this exact root.
    if (report?.consumer !== scope.consumer || report.skill !== name || !scope.path) return false;
    return Array.isArray(report.tiers) && report.tiers.some((tier) => (tier.roots || []).includes(scope.path) &&
      [...(tier.instances || []), ...(tier.skipped || [])].some((copy) =>
        copy.name === name && copy.root === scope.path && typeof copy.path === "string" &&
        (copy.path.startsWith(scope.path + "/") || copy.path.startsWith(scope.path + "\\")) &&
        (!copy.scope || copy.scope === scope.id)));
  }

  function placeChecks(copies, scope, report, name) {
    if (!copies.length) {
      const observed = scope.exists && scope.availability === "writable";
      const missing = observed && !doctorFound(report, name, scope);
      return [missing ? fail("No copy here") : unknown, skipped, skipped, skipped, unknown];
    }
    const checked = copies.map((copy) => copyChecks(copy, scope));
    const checks = [];
    for (let step = 0; step < rows.length - 1; step++) {
      const previous = checks.at(-1)?.state;
      checks.push(previous === "fail" || previous === "skip" ? skipped : mergedCell(checked, step));
    }
    return [...checks, unknown];
  }

  function checkedPlaces(name, scopes, records, project, reports) {
    const byScope = new Map();
    for (const record of records) {
      if (record.name !== name) continue;
      if (!byScope.has(record.scope)) byScope.set(record.scope, []);
      byScope.get(record.scope).push(record);
    }
    return placesIn(scopes).map((scope) => {
      const agent = window.SkillsV2Model.agentMark(scope.id, scope.label);
      const label = scope.id === "agents" ? "Shared skills folder" : scope.label || agent.name;
      const report = reports.get(discoveryQuery(scope, project, name));
      return { ...agent, id: scope.id, name: label, path: scope.path,
        hasCopies: (byScope.get(scope.id) || []).length > 0,
        checks: placeChecks(byScope.get(scope.id) || [], scope, report, name) };
    });
  }

  function nextStep(places) {
    // A missing copy in another place does not explain a problem with a copy
    // that exists. Keep each place's first failing check, but show real copy
    // failures before optional availability in another place.
    const ordered = [...places].sort((a, b) =>
      Number(a.checks[0].word === "No copy here") - Number(b.checks[0].word === "No copy here"));
    for (const place of ordered) {
      if (place.checks[0].word === "No copy here" && places.some((item) => item.hasCopies)) continue;
      const failed = place.checks.findIndex((cell) => cell.state === "fail");
      if (failed === -1) continue;
      const { path, word } = place.checks[failed];
      const suggestions = [
        { title: word === "No skill file" ? "The skill file is missing in " + place.name : "There’s no copy in " + place.name,
          text: word === "No copy here" ? "This only matters if you want to use the skill in this place. Open the skill page to add a copy." : "Open the skill page to see where a copy is available, then add it to this place." },
        { title: place.name + "’s copy can’t be read", text: "Open the skill page to compare copies and see how to repair the file." },
        { title: "The file is switched off in " + place.name, text: "Open the skill page and use the square for this place to turn it on." },
        { title: place.name + "’s own settings turn this skill off",
          text: "The file is readable and switched on. Review the setting that turns it off, then check again." },
      ];
      return { ...suggestions[failed], place, path, skillLink: failed < 3 };
    }
    return null;
  }

  Jack.register((app) => {
    app.component("jf-why-screen", {
      props: { name: String, scopes: Array, records: Array, project: String, busy: Boolean, error: String, readerHref: String },
      emits: ["refresh"],
      data: () => ({ rows, legend, reports: new Map(), generation: 0, checking: false,
        waitingForInventory: false, checked: false, discoveryError: false, copyStatus: "" }),
      computed: {
        observations() { return { name: this.name, scopes: this.scopes, records: this.records, project: this.project }; },
        places() { return checkedPlaces(this.name, this.scopes, this.records, this.project, this.reports); },
        next() { return this.error ? null : nextStep(this.places); },
        href() { return this.readerHref || Jack.router.skillHref(this.name); },
        pending() { return this.busy || this.checking || this.waitingForInventory; },
        status() {
          if (this.pending) return "Checking the skill folders…";
          if (this.error) return "The skill folders couldn’t be read again.";
          if (this.discoveryError) return "Some discovery checks couldn’t be completed.";
          if (this.checked && this.places.length) return "Checked just now.";
          return "";
        },
      },
      watch: {
        observations(next, previous) {
          if (next.records !== previous.records) this.waitingForInventory = false;
          this.checkDiscovery();
        },
        busy(value) {
          if (!value) this.waitingForInventory = false;
        },
      },
      mounted() {
        this.$refs.heading?.focus({ preventScroll: true });
        this.checkDiscovery();
      },
      beforeUnmount() { this.generation++; },
      methods: {
        checkAgain() {
          if (this.pending) return;
          this.waitingForInventory = true;
          this.copyStatus = "";
          this.$emit("refresh");
        },
        async checkDiscovery() {
          const generation = ++this.generation;
          const queries = new Set(placesIn(this.scopes).map((scope) => discoveryQuery(scope, this.project, this.name)).filter(Boolean));
          this.checking = true;
          this.checked = false;
          this.copyStatus = "";
          const results = await Promise.allSettled([...queries].map(async (query) => [query, (await Domain.api(query)).explain]));
          if (generation !== this.generation) return;
          const reports = new Map(results.filter((result) => result.status === "fulfilled").map((result) => result.value));
          this.reports = reports;
          this.discoveryError = results.some((result) => result.status === "rejected" || !result.value[1] ||
            ["unknown-consumer", "missing-project", "project-outside-managed-roots"].includes(result.value[1].resolution));
          this.checking = false;
          this.checked = true;
        },
        async copySettingsPath() {
          const path = this.next?.path;
          if (!path || this.pending) return;
          const generation = this.generation;
          try {
            await navigator.clipboard.writeText(path);
            if (generation === this.generation) this.copyStatus = "Settings path copied.";
          } catch {
            if (generation === this.generation) this.copyStatus = "Select the settings path above to copy it.";
          }
        },
      },
      template: `<div class="jf-why-screen">
        <header class="jf-why-heading">
          <nav class="jf-why-breadcrumb" aria-label="Breadcrumb">
            <a href="#/skills">Skills</a><span aria-hidden="true">/</span>
            <a :href="href" translate="no">{{ name }}</a><span aria-hidden="true">/</span>
            <span aria-current="page">Why isn’t it running?</span>
          </nav>
          <h1 id="h1" ref="heading" tabindex="-1">Why isn’t {{ name }} running?</h1>
          <p>We check each place from top to bottom. If a step fails, fix it first and check again.</p>
        </header>
        <section v-if="next" class="jf-why-next" aria-labelledby="jf-why-next-title">
          <span class="jf-agent-mark sm-ag" :data-a="next.place.mark" aria-hidden="true">{{ next.place.initials }}</span>
          <div class="jf-why-next-copy">
            <h2 id="jf-why-next-title">{{ next.title }}</h2>
            <p>{{ next.text }}</p>
            <code v-if="next.path" class="sm-mono" translate="no">{{ next.path }}</code>
            <p v-if="copyStatus" role="status">{{ copyStatus }}</p>
          </div>
          <div class="jf-why-actions">
            <button v-if="next.path" type="button" class="sm-btn sm-btn--accent" :disabled="pending" @click="copySettingsPath">Copy settings path</button>
            <a v-else-if="next.skillLink" :href="href" class="sm-btn sm-btn--accent">Open skill page</a>
            <button type="button" class="sm-btn" :class="{ 'sm-btn--accent': !next.path && !next.skillLink }" :disabled="pending" @click="checkAgain"><ic name="refresh"></ic>Check again</button>
          </div>
        </section>
        <div v-else class="jf-why-no-failure">
          <p>{{ error ? 'The latest results are unavailable.' : places.length ? 'We found no failed checks in the copies we could read. Missing copies matter only if you want to use the skill in those places.' : 'There are no tracked places to check.' }}</p>
          <a v-if="!error && places.some(place => place.checks[0].word === 'No copy here')" :href="href" class="sm-btn">Open skill page</a>
          <button type="button" class="sm-btn" :disabled="pending" @click="checkAgain"><ic name="refresh"></ic>Check again</button>
        </div>
        <div v-if="places.length" class="jf-why-grid-wrap" tabindex="0" role="region" aria-label="Checks in each place" :aria-busy="pending">
          <table class="jf-why-grid">
            <thead><tr>
              <th scope="col"><span class="sm-cap">Check</span></th>
              <th v-for="place in places" :key="place.id" scope="col"><jf-agent :agent="place"></jf-agent></th>
            </tr></thead>
            <tbody><tr v-for="(row, index) in rows" :key="row.id">
              <th scope="row"><b>{{ row.label }}</b><small>{{ row.help }}</small></th>
              <td v-for="place in places" :key="place.id">
                <span :class="['sm-chk', 'is-' + place.checks[index].state]">
                  <span class="sm-chk__ic" aria-hidden="true">{{ place.checks[index].state === 'unknown' ? '?' : '' }}</span>
                  <span v-if="place.checks[index].state === 'skip'" class="sm-sr">Not checked yet</span>
                  <span :aria-hidden="place.checks[index].state === 'skip' ? 'true' : null">{{ place.checks[index].word }}</span>
                </span>
              </td>
            </tr></tbody>
          </table>
        </div>
        <div v-if="places.length" class="jf-why-legend" aria-label="Check results legend">
          <span v-for="cell in legend" :key="cell.state" :class="['sm-chk', 'is-' + cell.state]">
            <span class="sm-chk__ic" aria-hidden="true">{{ cell.state === 'unknown' ? '?' : '' }}</span>{{ cell.word }}
          </span>
        </div>
        <section class="jf-why-unknown" aria-labelledby="jf-why-unknown-title">
          <h2 id="jf-why-unknown-title">Why “Actually loaded” says Unknown</h2>
          <p>Agents don’t tell other programs which skills they loaded. To check, ask the agent: “Which skills can you use right now?”</p>
        </section>
        <p class="jf-why-status sm-hint" role="status">{{ status }}</p>
      </div>`,
    });
  });
})();
