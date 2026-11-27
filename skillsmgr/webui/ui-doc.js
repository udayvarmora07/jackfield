/* The selected square's panel receives observations and emits intent only. */
"use strict";

window.Jackfield.register((app) => {
  app.component("jf-side-panel", {
    props: ["panel", "focusHeading", "modal"],
    emits: ["primary", "close", "choose-camp", "confirm", "look-again", "open-folder", "open-skill", "why", "cancel-preview"],
    mounted() { if (this.focusHeading || this.modal) this.focusTitle(); },
    watch: {
      focusHeading(value) { if (value) this.focusTitle(); },
      modal(value) { if (value) this.focusTitle(); },
    },
    methods: {
      focusTitle() { this.$nextTick(() => this.$refs.heading?.focus()); },
      panelKeys(event) {
        if (event.key === "Escape") {
          event.stopPropagation();
          this.$emit("close");
        } else if (event.key === "Tab" && this.modal) {
          const buttons = [...this.$el.querySelectorAll("button:not(:disabled), summary, [tabindex='0']")].filter((control) =>
            control.getClientRects().length && (control.tagName === "SUMMARY" || !control.closest("details:not([open])")));
          const first = buttons[0], last = buttons.at(-1);
          if (event.shiftKey && (document.activeElement === first || document.activeElement === this.$refs.heading)) {
            event.preventDefault(); last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first?.focus();
          }
        }
      },
    },
    template: `<aside v-if="panel" class="jf-panel" :role="modal ? 'dialog' : null"
        :aria-modal="modal ? 'true' : undefined" aria-labelledby="jf-panel-title" @keydown="panelKeys">
      <div class="jf-panel-top">
        <jf-agent :agent="{name: panel.agent, mark: panel.mark, initials: panel.initials}"></jf-agent>
        <button type="button" class="jf-panel-close" aria-label="Close panel" @click="$emit('close')">×</button>
      </div>
      <h2 id="jf-panel-title" ref="heading" class="jf-panel-title" tabindex="-1">{{ panel.skill }}</h2>
      <p v-if="!modal" class="jf-panel-path" translate="no">{{ panel.path }}</p>
      <p v-if="panel.line" class="jf-panel-line">{{ panel.line }}</p>
      <template v-if="panel.state === 'split'">
        <div class="jf-panel-camps">
          <div v-for="camp in panel.camps" :key="camp.id" class="jf-panel-camp">
            <strong>{{ camp.title }}</strong><p>{{ camp.detail }}</p>
            <button type="button" :aria-pressed="panel.selectedCamp === camp.id" @click="$emit('choose-camp', camp.id)">{{ camp.action }}</button>
          </div>
        </div>
        <p v-if="panel.preview" class="jf-panel-preview">{{ panel.preview }}</p>
        <button type="button" class="jf-panel-primary" :disabled="panel.selectedCamp == null || panel.primaryDisabled"
          @click="$emit('confirm')">{{ panel.primary }}</button>
        <p v-if="panel.selectedCamp == null" class="jf-panel-hint">Choose a version first</p>
      </template>
      <template v-else-if="panel.state === 'unknown'">
        <div class="jf-panel-checks">
          <div v-for="check in panel.checks" :key="check.label" class="jf-panel-check">
            <span>{{ check.label }}</span><jf-status :status="check.status" :label="check.detail"></jf-status>
          </div>
        </div>
        <button type="button" class="jf-panel-primary" @click="$emit('look-again')">Look again</button>
        <p v-if="panel.what" class="jf-panel-hint">{{ panel.what }}</p>
      </template>
      <template v-else-if="panel.state === 'preview'">
        <p v-if="panel.comparison.length" class="jf-panel-hint">This preview shows the instruction text. A replacement copies the whole folder.</p>
        <details v-for="version in panel.comparison" :key="version.id" class="jf-panel-details">
          <summary>{{ version.name }}’s instructions</summary>
          <pre class="jf-panel-excerpt" tabindex="0" role="region" :aria-label="version.name + ' instructions'">{{ version.text }}</pre>
        </details>
        <div v-if="panel.versionChoices.length" class="jf-panel-choice" aria-label="Version to keep" role="group">
          <button v-for="choice in panel.versionChoices" :key="choice.id" type="button" class="sm-btn"
            :aria-pressed="panel.selectedVersion === choice.id" @click="$emit('choose-camp', choice.id)">{{ choice.label }}</button>
        </div>
        <p class="jf-panel-preview">{{ panel.preview }}</p>
        <jf-pills :now="panel.now" :after="panel.after" :now-status="panel.nowStatus" :after-status="panel.afterStatus"></jf-pills>
        <button type="button" class="jf-panel-primary" :disabled="panel.primaryDisabled" @click="$emit('confirm')">{{ panel.primary }}</button>
        <button type="button" class="jf-panel-secondary" @click="$emit('cancel-preview')">Back</button>
      </template>
      <template v-else>
        <p v-if="panel.state === 'failed'" class="jf-panel-error" role="alert">{{ panel.failureTitle || 'Couldn’t complete the change' }}</p>
        <jf-pills :now="panel.now" :after="panel.after" :now-status="panel.nowStatus" :after-status="panel.afterStatus"
          :working="panel.state === 'working'" :failed="panel.state === 'failed'"></jf-pills>
        <p v-if="panel.state === 'failed' && panel.reason" class="jf-panel-reason">{{ panel.reason }}</p>
        <button type="button" class="jf-panel-primary" :disabled="panel.state === 'working' || panel.primaryDisabled"
          :aria-busy="panel.state === 'working' ? 'true' : undefined" @click="$emit('primary')">
          {{ panel.state === 'working' ? 'Working…' : panel.state === 'failed' ? (panel.verify ? 'Refresh files' : 'Try again') : panel.primary }}
          <kbd v-if="panel.key && !panel.state" class="jf-panel-key" aria-hidden="true">{{ panel.key }}</kbd>
        </button>
        <button v-if="panel.state === 'failed'" type="button" class="jf-panel-secondary" @click="$emit('open-folder')">Copy folder path</button>
        <details v-if="panel.state === 'failed' && panel.details" class="jf-panel-details"><summary>Technical details</summary><p>{{ panel.details }}</p></details>
        <div v-if="panel.what && panel.state !== 'failed'" class="jf-panel-what"><strong>What happens</strong><p>{{ panel.what }}</p></div>
      </template>
      <div v-if="!modal && panel.others?.length" class="jf-panel-others">
        <h3>Other places</h3><div v-for="other in panel.others" :key="other.id" class="jf-panel-other">
          <jf-agent :agent="other"></jf-agent><jf-status :status="other.status" :label="other.label"></jf-status>
        </div>
      </div>
      <div class="jf-panel-links">
        <button type="button" @click="$emit('open-skill')">Open skill</button>
        <button type="button" @click="$emit('why')">Why isn’t it running?</button>
      </div>
      <details v-if="modal && panel.others?.length" class="jf-panel-others jf-panel-others-mobile">
        <summary>Other places</summary>
        <div v-for="other in panel.others" :key="other.id" class="jf-panel-other">
          <jf-agent :agent="other"></jf-agent><jf-status :status="other.status" :label="other.label"></jf-status>
        </div>
      </details>
    </aside>`,
  });
});
