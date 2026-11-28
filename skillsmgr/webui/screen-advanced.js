/* Advanced directory: the model owns placement; this view owns presentation. */
"use strict";

window.Jackfield.register((app) => {
  app.component("jf-advanced-screen", {
    props: {
      groupsOn: { type: Object, default: () => ({}) },
      query: { type: String, default: "" },
      trackingReady: { type: Boolean, default: true },
      trackingError: { type: String, default: "" },
    },
    emits: ["update:query", "retry-tracking"],
    computed: {
      allGroupsOff() { return this.trackingReady && !this.trackingError && ["add", "inspect", "ai"].every((key) => this.groupsOn[key] === false); },
      matchingGroups() {
        const terms = this.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
        return window.SkillsV2Model.advancedGroups
          .filter((group) => group.key === "settings" || (this.trackingReady && !this.trackingError && this.groupsOn[group.key] !== false))
          .map((group) => ({
            ...group,
            sections: group.sections.map((section) => ({
              ...section,
              items: section.items.filter((item) => {
                const text = [group.label, section.label, item.name, item.text, item.commandLabel].join(" ").toLowerCase();
                return terms.every((term) => text.includes(term));
              }),
            })).filter((section) => section.items.length),
          })).filter((group) => group.sections.length);
      },
      matchingCount() {
        return this.matchingGroups.reduce((total, group) => total + group.sections.reduce((n, section) => n + section.items.length, 0), 0);
      },
    },
    methods: {
      href(item) { return item.id === "tracking" ? "#/settings/tracking" : window.Jackfield.router.toolHref(item.id); },
      icon(item) {
        const icons = { install: "upload", templates: "list", profiles: "list", "source-update": "upload", quality: "check", workspaces: "map", doctor: "ok", settings: "tools", tracking: "list", "ai-settings": "tools" };
        return icons[item.id] || (item.id.startsWith("ai-") ? "pencil" : "tools");
      },
    },
    template: `<div class="jf-advanced">
      <header class="jf-advanced-heading">
        <h1 id="h1" tabindex="-1">Advanced</h1>
        <p>Tools you won’t need every day, grouped by what you want to do.</p>
      </header>
      <p v-if="trackingError" class="jf-advanced-off" role="alert"><ic name="info"></ic><span>{{ trackingError }} <button type="button" class="sm-btn" @click="$emit('retry-tracking')">Try again</button></span></p>
      <p v-else-if="!trackingReady" class="jf-advanced-off" role="status"><ic name="info"></ic><span>Reading tool group settings…</span></p>
      <p v-if="allGroupsOff" class="jf-advanced-off" role="status"><ic name="info"></ic><span>Tool groups are switched off. Turn them on in <a href="#/settings/tracking">What to track</a>.</span></p>
      <div class="jf-advanced-search" role="search" aria-label="Tool directory">
        <div class="jf-advanced-search-field"><ic name="search"></ic><label class="sr-only" for="tp-dir-query">Find a tool</label><input id="tp-dir-query" class="field" type="search" :value="query" @input="$emit('update:query', $event.target.value)" placeholder="Find a tool…" autocomplete="off"></div>
        <p role="status">{{ query.trim() ? matchingCount + (matchingCount === 1 ? ' matching tool' : ' matching tools') : '' }}</p>
      </div>
      <div class="jf-advanced-grid" :class="{ 'jf-advanced-grid-expanded': matchingGroups.length === 4 }">
        <section v-for="group in matchingGroups" :key="group.key" class="jf-advanced-group" :aria-labelledby="'advanced-group-' + group.key">
          <h2 :id="'advanced-group-' + group.key">{{ group.label }}</h2>
          <p class="jf-advanced-group-description">{{ group.text }}</p>
          <div v-for="(section, index) in group.sections" :key="section.label || index" class="jf-advanced-section">
            <h3 v-if="section.label">{{ section.label }}</h3>
            <a v-for="item in section.items" :key="item.id" class="jf-advanced-tool" :href="href(item)">
              <span class="jf-advanced-icon"><ic :name="icon(item)"></ic></span>
              <span><strong>{{ item.name }}</strong><small>{{ item.text }}</small></span>
            </a>
          </div>
        </section>
        <p v-if="!matchingCount" class="jf-advanced-empty">Try a tool name or a task, such as “profile” or “registry”.</p>
      </div>
    </div>`,
  });
});
