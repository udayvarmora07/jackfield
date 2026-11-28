/* Needs attention receives reviewed observations and emits the user's choices. */
"use strict";

window.Jackfield.register((app) => {
  const PAGE_SIZE = 50;
  app.component("jf-attention", {
    props: {
      groups: { type: Array, default: () => [] }, detail: Object, loading: Boolean,
      error: [String, Object], checked: Object, count: Number, busy: Boolean,
    },
    emits: ["select", "choose", "fix", "skip", "recheck", "compare", "retry-comparison"],
    data: () => ({ groupLimits: {} }),
    computed: {
      visibleGroups() {
        return this.groups.map((group) => {
          const limit = this.groupLimits[group.id] || PAGE_SIZE;
          const items = group.items.slice(0, limit);
          const selected = group.items.findIndex((item) => item.id === this.detail?.id);
          if (selected >= limit) items.push(group.items[selected]);
          return { ...group, items, nextCount: Math.min(PAGE_SIZE, group.items.length - items.length) };
        });
      },
      countLabel() {
        if (this.count) return `${this.count} to go`;
        return this.groups.some((group) => group.title.startsWith("Skipped")) ? "0 to fix" : "All clear";
      },
      heading() {
        if (this.detail) return this.detail.title;
        if (this.error) return "Couldn’t check for problems";
        if (this.loading || !this.checked) return "Checking for problems…";
        return this.countLabel === "All clear" ? "Nothing left to fix" : "Select a problem";
      },
      disabled() { return this.busy || this.loading || !!this.error; },
      problem() {
        const status = this.detail?.status;
        if (status === "split") return { status: "different", label: "Two versions" };
        return { status, label: status === "unreadable" ? "Can’t read" : "Different" };
      },
      fixLabel() {
        if (this.busy) return "Working…";
        if (this.detail.needsChoice) return "Choose a version first";
        return this.detail.fixLabel || "Fix";
      },
      lastChecked() {
        if (!this.checked?.at) return "";
        const date = new Date(this.checked.at);
        if (Date.now() - date.getTime() < 60_000) return "Last checked just now.";
        return `Last checked ${date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}.`;
      },
    },
    methods: {
      showMore(group, event) {
        const offset = this.groupLimits[group] || PAGE_SIZE;
        const list = event.currentTarget.previousElementSibling;
        this.groupLimits[group] = offset + PAGE_SIZE;
        this.$nextTick(() => list.querySelectorAll("button")[offset]?.focus());
      },
    },
    template: `<div class="jf-attention">
      <header class="jf-attention-heading">
        <h1 id="h1" tabindex="-1">Needs attention</h1>
        <p v-if="checked && !loading && !error">{{ countLabel }}</p>
      </header>
      <div class="jf-attention-grid" :class="{ 'has-problems': groups.length > 0 }">
        <nav v-if="groups.length" class="jf-attention-list" aria-label="Problems">
          <div class="jf-attention-items">
            <section v-for="group in visibleGroups" :key="group.id" :aria-label="group.title">
              <h2 class="jf-attention-caption">{{ group.title }}</h2>
              <ul role="list">
                <li v-for="item in group.items" :key="item.id">
                  <button type="button" class="jf-attention-item" :data-attention-id="item.id"
                    :aria-current="detail?.id === item.id ? 'true' : null" :disabled="busy"
                    @click="$emit('select', item.id)">
                    <jf-status :status="item.status" :label="item.label"></jf-status>
                    <strong translate="no">{{ item.name }}</strong>
                    <jf-agent v-if="item.agent" :agent="item.agent"></jf-agent>
                  </button>
                </li>
              </ul>
              <button v-if="group.nextCount" type="button" class="sm-btn jf-attention-more"
                :aria-label="'Show more in ' + group.id" @click="showMore(group.id, $event)">Show {{ group.nextCount }} more</button>
            </section>
          </div>
          <p class="jf-attention-keys"><kbd class="sm-kbd">J</kbd> <kbd class="sm-kbd">K</kbd> next and previous · <kbd class="sm-kbd">F</kbd> fix</p>
        </nav>

        <section class="jf-attention-detail" aria-labelledby="attention-detail-heading" :aria-busy="loading || busy">
          <jf-agent v-if="detail?.agent" :agent="detail.agent"></jf-agent>
          <h2 id="attention-detail-heading" tabindex="-1">{{ heading }}</h2>
          <p v-if="detail?.line" class="jf-attention-intro">{{ detail.line }}</p>

          <div v-if="error" class="jf-attention-error">
            <p role="alert">{{ error.reason || error }}</p>
            <details v-if="error.details"><summary>Technical details</summary><p>{{ error.details }}</p></details>
            <button type="button" class="sm-btn" :disabled="loading || busy" @click="$emit('recheck')">Check again</button>
          </div>
          <p v-else-if="loading && detail" class="sm-hint" role="status">Checking the skill folders…</p>

          <template v-if="detail?.fixed">
            <p class="jf-attention-fixed"><jf-status status="on" label="Fixed"></jf-status></p>
            <a v-if="detail.skillHref" class="jf-attention-link" :href="detail.skillHref">Open skill</a>
          </template>
          <template v-else-if="detail">
            <p v-if="detail.manual" class="jf-attention-manual">{{ detail.manual }}</p>
            <template v-else>
              <fieldset v-if="detail.options?.length" class="jf-attention-versions">
                <legend class="jf-attention-caption">Which version should every place use?</legend>
                <div class="jf-attention-options">
                  <button v-for="option in detail.options" :key="option.id" type="button" class="sm-choice"
                    :aria-label="option.label" :aria-pressed="detail.selectedOption === option.id" :disabled="disabled"
                    @click="$emit('choose', option.id)">
                    <strong>{{ option.label }}</strong><span v-if="option.sub" class="sm-hint">{{ option.sub }}</span>
                    <code v-if="option.snippet" class="sm-choice__snip" translate="no">{{ option.snippet }}</code>
                  </button>
                </div>
              </fieldset>
              <jf-pills :now="problem.label" :now-status="problem.status"
                :after="detail.status === 'unreadable' ? 'Readable' : 'Same copy'" after-status="on"
                :working="busy" :failed="!!error"></jf-pills>
              <ul v-if="detail.targets?.length" class="jf-attention-targets" aria-label="Copies that will be overwritten">
                <li v-for="target in detail.targets" :key="target.path || target.label">
                  <strong>{{ target.label }}</strong><code v-if="target.path" translate="no">{{ target.path }}</code>
                </li>
              </ul>
              <label v-if="detail.comparePairs?.length > 1" class="jf-attention-compare-target">Compare target
                <select class="field" :value="detail.compareTarget" :disabled="disabled"
                  @change="$emit('compare', $event.target.value)">
                  <option v-for="pair in detail.comparePairs" :key="pair.id" :value="pair.id">{{ pair.label }}</option>
                </select>
              </label>
              <copy-comparison v-if="detail.comparisonEvidence" :evidence="detail.comparisonEvidence"
                from-label="Current target" to-label="Selected version" :reload="() => $emit('retry-comparison')"></copy-comparison>
              <div v-if="detail.readError" class="jf-attention-error">
                <p role="alert">{{ detail.readError }}</p>
                <button type="button" class="sm-btn" :disabled="disabled" @click="$emit('retry-comparison')">Try reading again</button>
              </div>
              <p v-else-if="detail.reading" class="sm-hint" role="status">Reading the replacement…</p>
              <button type="button" class="sm-btn sm-btn--primary jf-attention-fix" data-primary
                :disabled="disabled || !detail.canFix || detail.needsChoice" @click="$emit('fix')">{{ fixLabel }}</button>
            </template>

            <div class="jf-attention-actions">
              <button v-if="!detail.skipped" type="button" class="sm-btn" :disabled="disabled" @click="$emit('skip')">Skip for now</button>
              <a v-if="detail.skillHref" class="jf-attention-link" :href="detail.skillHref">Open skill</a>
            </div>
            <div v-if="detail.what" class="jf-attention-what sm-hint"><strong>What happens</strong><p>{{ detail.what }}</p></div>
          </template>

          <template v-else-if="checked && !loading && !error && countLabel === 'All clear'">
            <p class="jf-attention-intro">We checked {{ checked.skills }} {{ checked.skills === 1 ? 'skill' : 'skills' }} in
              {{ checked.places }} {{ checked.places === 1 ? 'place' : 'places' }} for files that can’t be read, copies that differ, and skills an agent’s settings turn off.</p>
            <p v-if="lastChecked" class="jf-attention-last sm-hint">{{ lastChecked }}</p>
            <button type="button" class="sm-btn" :disabled="busy" @click="$emit('recheck')">Check again</button>
          </template>
        </section>
      </div>
    </div>`,
  });
});
