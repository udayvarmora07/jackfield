/* Reusable, presentation-only pieces for the Skills table. */
"use strict";

window.Jackfield.register((app) => {
  const labels = {
    on: "On", off: "Off", settings: "Off in settings", set: "Off in settings",
    missing: "Not here", none: "Not here", different: "Different", diff: "Different",
    unreadable: "Can't read", bad: "Can't read", unknown: "Unknown", working: "Working…",
    "version-1": "Version 1", "version-2": "Version 2",
  };
  app.component("jf-status", {
    props: ["status", "label"],
    computed: { text() { return this.label || labels[this.status] || this.status || "Unknown"; } },
    template: `<span class="jf-status" :class="'jf-status--' + (status || 'unknown')"><span class="jf-status-mark" aria-hidden="true"></span>{{ text }}</span>`,
  });
  app.component("jf-square", {
    props: ["status", "label", "accessibleLabel", "selected", "disabled"],
    emits: ["select"],
    computed: { text() { return this.label || labels[this.status] || this.status || "Unknown"; } },
    template: `<button type="button" class="jf-square sm-square" :class="['jf-square--' + (status || 'unknown'), { 'is-selected': selected }]" :disabled="disabled" :aria-label="accessibleLabel || text" :aria-pressed="!!selected" :aria-busy="status === 'working' ? 'true' : undefined" @click="$emit('select', $event)"><jf-status :status="status" :label="text"></jf-status></button>`,
  });
  app.component("jf-agent", {
    props: ["agent"],
    template: `<span class="jf-agent"><span class="jf-agent-mark sm-ag" :data-a="agent && agent.mark" aria-hidden="true">{{ agent && agent.initials }}</span><span class="jf-agent-text"><span class="jf-agent-name">{{ agent && (agent.name || agent.agent) }}</span><span v-if="agent && agent.path" class="jf-agent-path">{{ agent.path }}</span></span></span>`,
  });
  app.component("jf-pills", {
    props: ["now", "after", "nowStatus", "afterStatus", "working", "failed"],
    template: `<div class="jf-pills"><span class="jf-pill"><jf-status :status="nowStatus" :label="failed ? 'Still ' + now : now"></jf-status></span><span class="jf-pills-arrow" :aria-label="working ? 'changing' : 'becomes'" role="img">{{ working ? '◌' : '→' }}</span><span v-if="after" class="jf-pill jf-pill-after" :class="{ 'is-working': working, 'is-failed': failed }"><jf-status :status="afterStatus" :label="after"></jf-status></span></div>`,
  });
  app.component("jf-attention-banner", {
    props: ["count", "pressed"], emits: ["toggle"],
    template: `<div v-if="count > 0" class="jf-attention-banner sm-banner">
      <div><strong class="sm-banner__title"><ic name="warn"></ic>{{ count }} {{ count === 1 ? 'skill needs' : 'skills need' }} your attention</strong><p class="sm-banner__detail">Review copies that differ or can’t be read.</p></div>
      <button type="button" class="sm-btn" :aria-pressed="!!pressed" @click="$emit('toggle')">Show only these</button>
      <a class="sm-btn sm-btn--dark jf-attention-desktop" href="#/attention">Fix one by one</a>
      <a class="jf-attention-phone" href="#/attention">Review</a>
    </div>`,
  });
});
