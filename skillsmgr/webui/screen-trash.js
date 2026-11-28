/* Trash and backup review receive observed state and emit intent to the app. */
"use strict";

window.Jackfield.register((app) => {
  const places = { library: "Your library", trash: "Library trash", templates: "Templates", catalog: "Catalog" };
  const actions = { add: "Add", replace: "Replace", skip: "Skip" };
  const PAGE_SIZE = 50;

  app.component("jf-trash-screen", {
    props: {
      rows: { type: Array, default: () => [] }, trashErrors: { type: Array, default: () => [] },
      trashLoading: Boolean, canEmpty: Boolean, libraryTrashError: Boolean, libraryTrashCount: Number, busy: Boolean, restored: Object,
      recent: { type: Array, default: () => [] }, historyError: String,
      exportPending: Boolean, exportError: String, lastDownload: String,
      importFileName: String, importForce: Boolean, importFull: Boolean, importPending: Boolean,
      importError: String, importPlan: Object, importResult: Object,
    },
    emits: ["restore", "retry-trash", "empty", "download", "pick-import", "set-force", "set-full",
      "preview", "apply", "cancel-preview", "retry-history"],
    data: () => ({ dropDepth: 0, trashLimit: PAGE_SIZE, recentLimit: PAGE_SIZE, places, actions }),
    computed: {
      disabled() { return this.busy || this.exportPending || this.importPending; },
      partial() { return this.trashLoading || this.trashErrors.length > 0; },
      emptyReason() {
        if (this.trashLoading) return "Wait until Trash has been read.";
        if (this.libraryTrashError) return "Library trash could not be read. Retry trash first.";
        if (!this.libraryTrashCount) return "Library trash is empty. Agent trash is not emptied here.";
        if (this.disabled) return "Wait for the current operation to finish.";
        return "";
      },
      hasPlanChanges() { return this.importPlan?.entries?.some((entry) => entry.action === "add" || entry.action === "replace"); },
      nextTrashCount() { return Math.min(PAGE_SIZE, this.rows.length - this.trashLimit); },
      nextRecentCount() { return Math.min(PAGE_SIZE, this.recent.length - this.recentLimit); },
    },
    watch: {
      importPlan(plan) {
        if (plan) this.$nextTick(() => this.$refs.planHeading?.focus());
      },
    },
    methods: {
      pickFiles(event) {
        if (!this.disabled && event.target.files.length) this.$emit("pick-import", event.target.files);
        event.target.value = "";
      },
      dropFiles(event) {
        this.dropDepth = 0;
        const files = event.dataTransfer.files;
        if (!this.disabled && files.length) this.$emit("pick-import", files);
      },
      cancelPlan() {
        this.$emit("cancel-preview");
        this.$nextTick(() => (this.$refs.previewButton || this.$refs.chooseFile)?.focus());
      },
      showMore(limit, list) {
        const offset = this[limit];
        this[limit] += PAGE_SIZE;
        this.$nextTick(() => this.$refs[list]?.children[offset]?.focus());
      },
    },
    template: `<div class="jf-trash-screen">
      <header class="jf-trash-heading">
        <h1 id="h1" tabindex="-1">Trash &amp; backups</h1>
        <p>Restore skill folders from Trash or back up your library.</p>
      </header>
      <div class="jf-trash-cards">
        <section class="jf-trash-card" aria-labelledby="rec-trash">
          <header class="jf-trash-card-header">
            <h2 id="rec-trash" tabindex="-1">Trash <span v-if="rows.length || !partial">· {{ rows.length }}{{ partial ? ' shown' : '' }}</span></h2>
            <button type="button" class="sm-btn sm-btn--quiet" :disabled="disabled || !canEmpty || trashLoading" :aria-describedby="emptyReason ? 'jf-empty-reason' : null" @click="$emit('empty')">
              <ic name="trash" cls="i-s"></ic>Empty library trash…
            </button>
          </header>
          <p v-if="emptyReason" id="jf-empty-reason" class="sm-hint jf-trash-message">{{ emptyReason }}</p>
          <div v-if="restored" class="jf-trash-message jf-trash-restored">
            <p role="status">{{ restored.message || ('Restored ' + restored.name + ' to ' + restored.scopeLabel + '.') }}</p>
            <jf-status v-if="restored.status" :status="restored.status"></jf-status>
            <a v-if="restored.href" :href="restored.href">Show restored copy</a>
          </div>
          <ul v-if="rows.length" ref="trashRows" class="jf-trash-rows" role="list">
            <li v-for="row in rows.slice(0, trashLimit)" :key="row.id" tabindex="-1" class="jf-trash-row jf-trash-entry">
              <span class="jf-trash-entry-name"><strong translate="no">{{ row.name }}</strong><span v-if="row.detail" class="sm-hint">{{ row.detail }}</span></span>
              <span class="jf-trash-entry-origin">
                <jf-agent v-if="row.agent" :agent="{ ...row.agent, name: 'From ' + row.scopeLabel, path: '' }"></jf-agent>
                <span v-else>From {{ row.scopeLabel }}</span>
              </span>
              <span class="sm-hint jf-trash-entry-time">{{ row.when }}</span>
              <button type="button" class="sm-btn jf-trash-entry-action" :disabled="disabled || trashLoading || row.canRestore === false"
                :aria-label="row.restoreLabel || ('Restore ' + row.name + ' in ' + row.scopeLabel)" @click="$emit('restore', row.id)">
                <ic name="undo" cls="i-s"></ic>Restore
              </button>
            </li>
          </ul>
          <p v-if="nextTrashCount > 0" class="jf-trash-message"><button type="button" class="sm-btn" @click="showMore('trashLimit', 'trashRows')">Show {{ nextTrashCount }} more {{ nextTrashCount === 1 ? 'trash item' : 'trash items' }}</button> <span class="sm-hint">Showing {{ trashLimit }} of {{ rows.length }}</span></p>
          <p v-if="trashLoading" class="jf-trash-message" role="status">Reading Trash…</p>
          <p v-else-if="!rows.length && !trashErrors.length" class="jf-trash-message">Trash is empty. Removed skills and copies replaced by a fix appear here.</p>
          <div v-if="trashErrors.length" class="jf-trash-error">
            <ul role="alert"><li v-for="entry in trashErrors" :key="entry.scope"><strong>{{ entry.label }}.</strong> {{ entry.message }}</li></ul>
            <button type="button" class="sm-btn" :disabled="disabled || trashLoading" @click="$emit('retry-trash')">Retry trash</button>
          </div>
          <p class="sm-hint jf-trash-note">Restore uses the original folder when Jackfield recorded it. Older copies return to the place’s usual skill folder.</p>
        </section>

        <section class="jf-trash-card" aria-labelledby="rec-history">
          <header class="jf-trash-card-header"><h2 id="rec-history" tabindex="-1">Recent changes</h2><span class="sm-hint">Today and yesterday</span></header>
          <ul v-if="recent.length" ref="recentRows" class="jf-trash-rows" role="list">
            <li v-for="event in recent.slice(0, recentLimit)" :key="event.id" tabindex="-1" class="jf-trash-row jf-trash-recent">
              <span>{{ event.text }}</span><span class="sm-hint">{{ event.when }}</span>
            </li>
          </ul>
          <p v-if="nextRecentCount > 0" class="jf-trash-message"><button type="button" class="sm-btn" @click="showMore('recentLimit', 'recentRows')">Show {{ nextRecentCount }} more {{ nextRecentCount === 1 ? 'change' : 'changes' }}</button> <span class="sm-hint">Showing {{ recentLimit }} of {{ recent.length }}</span></p>
          <div v-if="historyError" class="jf-trash-error">
            <p role="alert">{{ historyError }}</p>
            <button type="button" class="sm-btn" :disabled="disabled" @click="$emit('retry-history')">Retry recent changes</button>
          </div>
          <p v-else-if="!recent.length" class="jf-trash-message">No library changes recorded today or yesterday.</p>
        </section>

        <section class="jf-trash-card jf-trash-backups" aria-labelledby="rec-backup">
          <h2 id="rec-backup" tabindex="-1">Backups</h2>
          <p>A backup holds skills in your library. Skills stored in agent folders need a separate backup.</p>
          <div class="jf-trash-backup-options">
            <section class="jf-trash-backup-option" aria-labelledby="rec-download-title">
              <h3 id="rec-download-title">Download a backup</h3>
              <p v-if="lastDownload" class="sm-hint">{{ lastDownload }}</p>
              <p class="sm-hint">The full archive also includes library trash, templates, and catalog metadata.</p>
              <p v-if="exportPending" class="sm-hint" role="status">Preparing backup…</p>
              <p v-if="exportError" class="jf-trash-backup-error" role="alert">{{ exportError }}</p>
              <div class="jf-trash-backup-buttons">
                <button type="button" class="sm-btn sm-btn--accent" :disabled="disabled" @click="$emit('download', false)">
                  <ic name="arrow" cls="i-s jf-trash-download-icon"></ic>Download backup
                </button>
                <button type="button" class="sm-btn" :disabled="disabled" @click="$emit('download', true)">Download full archive</button>
              </div>
            </section>
            <section class="jf-trash-backup-option" :class="{ 'is-over': dropDepth > 0 }" aria-labelledby="rec-import"
              @dragenter.prevent="dropDepth++" @dragover.prevent @dragleave="dropDepth = Math.max(0, dropDepth - 1)" @drop.prevent="dropFiles">
              <h3 id="rec-import" tabindex="-1">Load a backup</h3>
              <p class="sm-hint">You’ll see what changes in the library before anything is written.</p>
              <p v-if="importFileName" class="jf-trash-file sm-hint" translate="no">{{ importFileName }}</p>
              <div class="jf-trash-backup-buttons">
                <input id="imp-file" ref="file" type="file" accept=".tar.gz,.tgz,.tar,.zip" :disabled="disabled" hidden @change="pickFiles">
                <button type="button" class="sm-btn" ref="chooseFile" :disabled="disabled" @click="$refs.file.click()">
                  <ic name="upload" cls="i-s"></ic>Choose a backup file…
                </button>
              </div>
            </section>
          </div>

          <div v-if="importFileName || importError || importResult" class="jf-trash-backup-review">
            <template v-if="importFileName">
              <div class="jf-trash-review-options">
                <label><input class="sm-checkbox" type="checkbox" :checked="importForce" :disabled="disabled" @change="$emit('set-force', $event.target.checked)">Replace matching entries</label>
                <label><input class="sm-checkbox" type="checkbox" :checked="importFull" :disabled="disabled" @change="$emit('set-full', $event.target.checked)">Include library trash, templates, and catalog metadata</label>
              </div>
              <p v-if="importPending" class="sm-hint" role="status">{{ importPlan ? 'Loading backup…' : 'Reading backup for preview…' }}</p>
              <button v-if="!importPlan" type="button" class="sm-btn jf-trash-preview-button" ref="previewButton" :disabled="disabled" @click="$emit('preview')">Preview backup</button>
              <section v-else aria-labelledby="jf-trash-plan-heading" class="jf-trash-plan">
                <h3 id="jf-trash-plan-heading" ref="planHeading" tabindex="-1">Backup preview</h3>
                <p v-if="!hasPlanChanges" class="sm-hint">No entries will change.</p>
                <ul v-if="importPlan.entries.length" class="jf-trash-plan-entries">
                  <li v-for="(entry, index) in importPlan.entries" :key="index">
                    <strong translate="no">{{ entry.name }}</strong>
                    <span>{{ actions[entry.action] }} · {{ places[entry.place] }}</span>
                    <span v-if="entry.reason" class="sm-hint">{{ entry.reason }}</span>
                  </li>
                </ul>
                <div class="jf-trash-backup-buttons">
                  <button type="button" class="sm-btn sm-btn--accent" :disabled="disabled || !hasPlanChanges" @click="$emit('apply')">Load backup</button>
                  <button type="button" class="sm-btn" :disabled="disabled" @click="cancelPlan">Cancel preview</button>
                </div>
              </section>
            </template>
            <p v-if="importError" class="jf-trash-backup-error" role="alert">{{ importError }}</p>
            <div v-if="importResult">
              <p role="status">{{ importResult.summary }}</p>
              <details v-if="importResult.reasons?.length"><summary>Skipped entries</summary>
                <ul><li v-for="(reason, index) in importResult.reasons" :key="index">{{ reason }}</li></ul>
              </details>
            </div>
          </div>
        </section>
        <slot></slot>
      </div>
    </div>`,
  });
});
