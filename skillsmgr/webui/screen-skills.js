/* Skills table and keyboard navigation. Disk operations stay in the app. */
"use strict";

window.Jackfield.register((app) => {
  app.component("jf-skills-screen", {
    props: {
      rows: { type: Array, default: () => [] },
      agents: { type: Array, default: () => [] },
      panel: { default: null },
      selected: { default: null },
      loading: Boolean,
      trackingNotices: { type: Array, default: () => [] },
      firstLaunch: Boolean,
      route: { default: null },
      busy: Boolean,
      error: { default: null },
      loaded: Boolean,
      agentsFound: Boolean,
      projects: { type: Array, default: () => [] },
      showing: { default: null },
      changedRows: { type: Array, default: () => [] },
      attentionCount: Number,
      batchLimit: { type: Number, required: true },
    },
    emits: ["select", "primary", "open-skill", "close-panel", "manage-agents", "first-launch-done",
      "refresh", "view-change", "tracking-action", "choose-camp", "confirm", "look-again",
      "open-folder", "why", "cancel-preview", "batch"],
    data() {
      return { query: "", onlyAttention: false, limit: 50, place: "", sort: "name",
        focusRow: 0, focusCol: 0, menu: null, panelFocus: false, narrow: false,
        phonePlace: "", phoneTools: false, checked: [], batchPlace: "" };
    },
    computed: {
      filtered() {
        const words = this.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
        const result = this.rows.filter((row) => {
          if (this.onlyAttention && !row.attention) return false;
          const text = [row.name, row.description, row.category, row.presentIn].join(" ").toLowerCase();
          return words.every((word) => text.includes(word));
        });
        return result.sort((a, b) => this.compareRows(a, b));
      },
      visibleRows() { return this.filtered.slice(0, this.limit); },
      closeName() {
        if (!this.query || this.filtered.length) return null;
        const candidates = this.onlyAttention ? this.rows.filter((row) => row.attention) : this.rows;
        return window.Jackfield.palette.closeName(this.query, candidates);
      },
      currentAgent() {
        const place = this.place || (this.narrow ? this.selected?.agent || this.phonePlace : null);
        return this.agents.find((agent) => agent.id === place) || this.agents[0];
      },
      columns() {
        if (!this.narrow && !this.place) return this.agents;
        return this.currentAgent ? [this.currentAgent] : [];
      },
      batchAgent() {
        return this.agents.find((agent) => agent.id === this.batchPlace) || this.currentAgent;
      },
      sheet() { return this.narrow && !!this.panel; },
    },
    watch: {
      query() { this.resetGrid(); this.viewChange(); },
      onlyAttention() { this.resetGrid(); this.viewChange(); },
      place() { this.resetGrid(); this.viewChange(); },
      sort() { this.resetGrid(); },
      route: { immediate: true, handler(route) {
        if (!route) return;
        this.query = route.search || "";
        this.onlyAttention = route.only === "problems";
        this.place = route.agent || "";
        if (this.selected && this.filtered.findIndex((row) => row.name === this.selected.name) >= this.limit) this.extendToSelection();
      } },
      columns() { this.focusCol = Math.min(this.focusCol, this.columns.length); },
      visibleRows() { this.focusRow = Math.min(this.focusRow, Math.max(0, this.visibleRows.length - 1)); },
      filtered(rows) {
        const shown = new Set(rows.map((row) => row.name));
        this.checked = this.checked.filter((name) => shown.has(name));
        if (this.selected && !shown.has(this.selected.name)) this.$emit("close-panel");
      },
      selected(next, previous) {
        if (next) this.phonePlace = next.agent;
        if (!next && previous && this.narrow) {
          const index = this.visibleRows.findIndex((row) => row.name === previous.name);
          if (index >= 0) { this.focusRow = index; this.focusCol = 1; }
          this.focusCell();
        }
      },
    },
    mounted() {
      this.media = window.matchMedia("(max-width: 640px)");
      this.setViewport(this.media);
      this.media.addEventListener("change", this.setViewport);
      this.extendToSelection();
    },
    beforeUnmount() { this.media.removeEventListener("change", this.setViewport); },
    methods: {
      setViewport(media) { this.narrow = media.matches; },
      compareRows(a, b) {
        const alphabetical = a.name.localeCompare(b.name);
        if (this.sort === "size") return b.tokens - a.tokens || alphabetical;
        if (this.sort === "places") return b.places - a.places || alphabetical;
        return alphabetical;
      },
      viewChange() {
        const sel = this.route?.selected;
        this.$emit("view-change", { q: this.query, agent: this.place, only: this.onlyAttention ? "problems" : "", sel });
      },
      resetGrid() { this.limit = 50; this.focusRow = 0; this.focusCol = 0; this.extendToSelection(); },
      extendToSelection() {
        if (!this.selected) return;
        const index = this.filtered.findIndex((row) => row.name === this.selected.name);
        if (index >= this.limit) this.limit = Math.ceil((index + 1) / 50) * 50;
      },
      clearFilters() {
        this.onlyAttention = false;
        this.useFilter("");
      },
      useFilter(text) {
        this.query = text;
        if (this.narrow) this.phoneTools = true;
        this.$nextTick(() => this.$refs.filter?.focus());
      },
      cell(row, agent) { return row.cells[agent.id] || { status: "unknown", label: "Unknown" }; },
      selectedCell(row, agent) { return this.selected?.name === row.name && this.selected?.agent === agent.id; },
      choose(row, agent, focusPanel = false, primary = false) {
        this.panelFocus = false;
        if (focusPanel || this.narrow) this.$nextTick(() => { this.panelFocus = true; });
        this.$emit("select", { name: row.name, agent: agent.id, focusPanel, primary });
      },
      focusCell() {
        this.$nextTick(() => {
          const target = this.$el.querySelector('[data-grid-row="' + this.focusRow + '"][data-grid-col="' + this.focusCol + '"]');
          (target || this.$refs.filter)?.focus();
        });
      },
      keyGrid(event, row, agent, ri, ci) {
        if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) {
          event.preventDefault();
          if (this.narrow) this.phoneTools = true;
          this.$nextTick(() => this.$refs.filter?.focus());
          return;
        }
        const movement = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[event.key];
        if (movement || event.key === "Home" || event.key === "End") {
          event.preventDefault();
          if ((event.ctrlKey || event.metaKey) && ["Home", "End"].includes(event.key)) {
            this.focusRow = event.key === "Home" ? 0 : this.visibleRows.length - 1;
            this.focusCol = event.key === "Home" ? 0 : this.columns.length;
            this.focusCell();
            return;
          }
          this.moveGrid(event.key, movement, ri, ci);
          return;
        }
        if (!row) return;
        if (event.key === "Enter" && agent) {
          event.preventDefault(); this.choose(row, agent, true);
        } else if (event.key === " " && event.shiftKey) {
          event.preventDefault();
          if (!event.repeat) this.toggleRow(row.name);
        } else if (event.key === " " && agent && !event.ctrlKey && !event.metaKey && !event.altKey) {
          event.preventDefault();
          if (!event.repeat) this.choose(row, agent, false, this.cell(row, agent).actionable);
        }
      },
      moveGrid(key, movement, row, column) {
        const minRow = column > 0 && !this.narrow ? -1 : 0;
        this.focusRow = Math.max(minRow, Math.min(this.visibleRows.length - 1, row + (movement?.[0] || 0)));
        const minColumn = this.focusRow < 0 ? 1 : 0;
        const nextColumn = key === "Home" ? minColumn : key === "End" ? this.columns.length : column + (movement?.[1] || 0);
        this.focusCol = Math.max(minColumn, Math.min(this.columns.length, nextColumn));
        this.focusCell();
      },
      toggleRow(name) {
        this.checked = this.checked.includes(name) ? this.checked.filter((row) => row !== name) : [...this.checked, name];
      },
      closePanel() { this.$emit("close-panel"); this.panelFocus = false; this.focusCell(); },
      closeMenu(event) {
        this.menu = null;
        event.currentTarget.parentElement.querySelector("button")?.focus();
      },
      trackingAction(action, id) { this.menu = null; this.$emit("tracking-action", { action, id }); },
      selectPlace(event) {
        this.place = event.target.value;
        if (this.selected && this.place && this.selected.agent !== this.place) this.$emit("close-panel");
      },
    },
    template: `<section class="jf-skills-screen" aria-labelledby="h1">
      <div :inert="sheet">
        <div class="jf-skills-title-row">
          <div><h1 id="h1" tabindex="-1">Skills</h1><span v-if="loaded" class="jf-skills-subtitle">{{ rows.length }}{{ narrow ? '' : ' skills' }} in {{ agents.length }} places</span></div>
          <a class="sm-btn sm-btn--page" href="#/new"><ic name="plus" cls="i-s"></ic>New skill</a>
        </div>
        <div class="jf-skills-notices">
          <div v-for="notice in trackingNotices" :key="notice.key" class="jf-skills-notice" role="region" :aria-label="notice.title">
            <div><strong>{{ notice.title }}</strong><p v-if="notice.text">{{ notice.text }}</p></div>
            <button v-for="action in notice.actions" :key="action.action" type="button" class="sm-btn"
              @click="$emit('tracking-action', action)">{{ action.label }}</button>
          </div>
        </div>
        <div v-if="error" class="jf-skills-notice" role="alert">{{ error }}
          <button type="button" class="sm-btn" :disabled="loading" @click="$emit('refresh')">Try again</button>
        </div>
        <div v-if="!loaded && loading" class="jf-skills-empty" role="status">
          <h2>Looking for your agents…</h2><p>Reading skill folders…</p><jf-placeholder></jf-placeholder>
        </div>
        <section v-else-if="loaded && firstLaunch" class="jf-skills-empty jf-skills-welcome">
          <p>Welcome to Jackfield</p><h2>Found {{ agents.length }} agents and {{ rows.length }} skills</h2>
          <div v-for="agent in agents" :key="agent.id" class="jf-welcome-agent">
            <jf-agent :agent="{...agent, path: ''}"></jf-agent><span>{{ agent.count }} skills</span>
          </div>
          <p>Click any square in the table to turn a skill on or off for that agent.</p>
          <button type="button" class="sm-btn sm-btn--accent" @click="$emit('first-launch-done')">Show my skills</button>
        </section>
        <section v-else-if="loaded && !agents.length" class="jf-skills-empty">
          <h2>{{ agentsFound ? 'No agents are tracked.' : 'No agent skills found yet' }}</h2>
          <p>{{ agentsFound ? 'Choose the agents whose skills you want to see here.' : 'Jackfield looked for skill folders used by your coding agents.' }}</p>
          <button v-if="agentsFound" type="button" class="sm-btn" @click="$emit('manage-agents')">Choose agents</button>
          <template v-else><a href="#/settings/tracking/add-agent" class="sm-btn">Add a folder</a>
            <button type="button" class="sm-btn" @click="$emit('refresh')">Look again</button></template>
          <a v-if="rows.length" href="#/skills?view=instances">Show library skills</a>
        </section>
        <template v-else-if="loaded">
          <jf-attention-banner :count="attentionCount" :pressed="onlyAttention" @toggle="onlyAttention = !onlyAttention"></jf-attention-banner>
          <div v-if="narrow" class="jf-skills-toolbar jf-skills-phone-tools">
            <label class="jf-skills-phone-agent">Showing
              <select class="sm-btn" aria-label="Showing agent" :value="currentAgent?.id" @change="selectPlace">
                <option v-for="agent in agents" :key="agent.id" :value="agent.id">{{ agent.name }}</option>
              </select>
            </label>
            <a href="#/settings/tracking">Manage agents</a>
            <button type="button" class="sm-btn" :aria-expanded="phoneTools" aria-controls="jf-hero-table-tools" @click="phoneTools = !phoneTools">{{ query || onlyAttention ? 'Filters on' : 'Filter and sort' }}</button>
          </div>
          <div v-show="!narrow || phoneTools" id="jf-hero-table-tools" class="jf-skills-toolbar">
            <label class="jf-skills-filter"><span class="sr-only">Filter skills</span>
              <input ref="filter" v-model="query" placeholder="Filter by name or what it does" type="search"><kbd aria-hidden="true">/</kbd>
            </label>
            <label class="jf-skills-desktop-agent"><span class="sr-only">Place</span>
              <select class="sm-btn" :value="place" @change="selectPlace"><option value="">All places</option>
                <option v-for="agent in agents" :key="agent.id" :value="agent.id">{{ agent.name }}</option>
              </select>
            </label>
            <label><span class="sr-only">Sort</span><select class="sm-btn" v-model="sort">
              <option value="name">A to Z</option><option value="size">Largest first</option><option value="places">In most places</option>
            </select></label>
            <label v-if="projects.length"><span class="sr-only">Project folder</span>
              <select class="sm-btn" :value="showing || ''"
                @change="$emit('tracking-action', {action: 'show-project', path: $event.target.value})">
                <option value="">Project: None</option><option v-for="project in projects" :key="project.path" :value="project.path"
                  :disabled="project.status !== 'ok'">Project: {{ project.path.split('/').at(-1) }}</option>
              </select>
            </label>
            <span class="jf-grid-count" aria-live="polite">Showing {{ visibleRows.length }} of {{ filtered.length }}</span>
            <button type="button" class="sm-btn" :disabled="loading" @click="$emit('refresh')">{{ loading ? 'Refreshing…' : 'Refresh files' }}</button>
            <button v-if="narrow && attentionCount" type="button" class="sm-btn" :aria-pressed="onlyAttention" @click="onlyAttention = !onlyAttention">Show only these</button>
          </div>
          <div v-if="checked.length" class="jf-skills-toolbar">
            <span>{{ checked.length }} selected</span>
            <label><span class="sr-only">Destination</span><select class="sm-btn" v-model="batchPlace">
              <option value="">Current place</option>
              <option v-for="agent in agents" :key="agent.id" :value="agent.id">{{ agent.name }}</option>
            </select></label>
            <button type="button" class="sm-btn" :disabled="busy || !batchAgent || checked.length > batchLimit"
              @click="$emit('batch', {names: checked.slice(), agent: batchAgent.id})">Make these match in {{ batchAgent?.name }}</button>
            <button type="button" class="sm-btn sm-btn--quiet" @click="checked = []">Clear selection</button>
            <p v-if="checked.length > batchLimit" role="status">Select {{ batchLimit }} skills or fewer for one change.</p>
          </div>
        </template>
      </div>
      <div class="jf-skills-content" v-if="loaded && !firstLaunch && agents.length">
        <div class="jf-skills-table-wrap" :inert="sheet">
          <div v-if="!rows.length" class="jf-skills-empty"><h2>No skills yet</h2><p>Create a skill or add one from a folder.</p><a href="#/advanced/install">Add from source</a></div>
          <div v-else-if="!filtered.length" class="jf-skills-empty">
            <p>No skills match this filter.</p><button type="button" class="sm-btn" @click="clearFilters">Clear filters</button>
            <p v-if="closeName">Did you mean <button type="button" class="sm-btn" @click="useFilter(closeName.name)">{{ closeName.name }}</button>?</p>
          </div>
          <table v-else class="jf-grid" role="grid" aria-label="Skills table" :style="{ '--jf-grid-places': columns.length }"
            :aria-rowcount="filtered.length + (narrow ? 0 : 1)" :aria-colcount="columns.length + 1">
            <colgroup><col class="jf-grid-skill-column"><col v-for="agent in columns" :key="agent.id"></colgroup>
            <thead><tr><th scope="col">Skill</th>
              <th v-for="(agent, ai) in columns" :key="agent.id" scope="col" class="jf-grid-agent jf-grid-phone-current">
                <jf-agent :agent="agent" :title="agent.path"></jf-agent>
                <div class="jf-grid-menu">
                  <button type="button" :aria-label="agent.name + ' options'" :aria-expanded="menu === agent.id"
                    :tabindex="focusRow === -1 && focusCol === ai + 1 ? 0 : -1" data-grid-row="-1" :data-grid-col="ai + 1"
                    @focus="focusRow = -1; focusCol = ai + 1" @keydown="keyGrid($event, null, agent, -1, ai + 1)"
                    @click="menu = menu === agent.id ? null : agent.id">▾</button>
                  <div v-if="menu === agent.id" @keydown.esc.stop="closeMenu($event)"
                    @focusout="!$event.currentTarget.parentElement.contains($event.relatedTarget) && (menu = null)">
                    <p v-if="agent.kind === 'shared'">Shown while Claude Code and Codex read it. It has no switch of its own.</p>
                    <template v-else-if="agent.kind !== 'project'">
                      <button type="button" :disabled="!agent.canStop" @click="trackingAction('stop', agent.id)">Stop tracking {{ agent.name }}…</button>
                      <span v-if="!agent.canStop">At least one agent stays tracked.</span>
                      <button type="button" @click="trackingAction('details', agent.id)">{{ agent.name }} details</button>
                    </template>
                    <button type="button" @click="menu = null; $emit('manage-agents')">Manage agents</button>
                  </div>
                </div>
              </th>
            </tr></thead>
            <tbody><tr v-for="(row, ri) in visibleRows" :key="row.name" :aria-rowindex="ri + (narrow ? 1 : 2)"
              :aria-selected="checked.includes(row.name)" :class="{ 'is-changed': changedRows.includes(row.name) }">
              <th scope="row" class="jf-grid-skill">
                <input type="checkbox" tabindex="-1" v-model="checked" :value="row.name" :aria-label="'Select ' + row.name">
                <button type="button" :tabindex="focusRow === ri && focusCol === 0 ? 0 : -1" :data-grid-row="ri" data-grid-col="0"
                  :aria-keyshortcuts="'Shift+Space'" @focus="focusRow = ri; focusCol = 0" @keydown="keyGrid($event, row, null, ri, 0)"
                  @click="$emit('open-skill', row.name)">{{ row.name }}</button>
                <span class="jf-grid-description">{{ row.description }}</span><span class="jf-grid-verdict" :class="{ 'has-attention': row.attention }">{{ row.verdict }}</span>
              </th>
              <td v-for="(agent, ai) in columns" :key="agent.id" class="jf-grid-phone-current">
                <jf-square :status="cell(row, agent).status" :label="cell(row, agent).label"
                  :accessible-label="row.name + ' in ' + agent.name + ': ' + cell(row, agent).label" :selected="selectedCell(row, agent)"
                  :tabindex="focusRow === ri && focusCol === ai + 1 ? 0 : -1" :data-grid-row="ri" :data-grid-col="ai + 1"
                  @focus="focusRow = ri; focusCol = ai + 1" @keydown="keyGrid($event, row, agent, ri, ai + 1)"
                  @select="choose(row, agent)"></jf-square>
              </td>
            </tr></tbody>
          </table>
          <button v-if="visibleRows.length < filtered.length" type="button" class="jf-skills-more sm-btn" @click="limit += 50">Show 50 more</button>
          <p v-if="rows.length" class="jf-skills-hint">↑ ↓ ← → move between squares · Space turn on or off · Enter open · Shift+Space select row · / search</p>
          <footer class="jf-skills-footer"><a href="#/skills?view=instances">Exact instances</a> <a v-if="!narrow" href="#/settings/tracking">Manage agents</a></footer>
        </div>
        <div v-if="sheet" class="jf-panel-scrim" aria-hidden="true" @click.self="closePanel"></div>
        <jf-side-panel v-if="panel" :panel="panel" :modal="sheet" :focus-heading="panelFocus" @close="closePanel"
          @primary="$emit('primary')" @open-skill="$emit('open-skill', panel.skill)" @choose-camp="$emit('choose-camp', $event)"
          @confirm="$emit('confirm')" @look-again="$emit('look-again')" @open-folder="$emit('open-folder')"
          @why="$emit('why')" @cancel-preview="$emit('cancel-preview')"></jf-side-panel>
      </div>
    </section>`,
  });
});
