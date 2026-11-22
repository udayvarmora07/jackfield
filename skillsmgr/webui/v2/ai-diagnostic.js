/* Discovery, simulation, and selected local trace evidence for one skill. */
(function () {
  "use strict";
  const api = window.SkillManagerDomain.api;
  const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body) });
  const enc = encodeURIComponent;
  const TRACE_LIMIT = 512 * 1024;
  const OPEN_CODE_EVENTS = new Set(["step_start", "step_finish", "text", "tool_use", "reasoning"]);

  function openCodeTrace(value) {
    const lines = value.trim().split(/\r?\n/).filter(line => line.trim());
    if (!value.trim() || lines.length > 2000) throw new Error("Use a complete OpenCode JSON run with up to 2,000 events.");
    const events = lines.map(line => JSON.parse(line));
    const sessions = new Set(events.map(event => event?.sessionID));
    const last = events.at(-1);
    if (sessions.size !== 1 || ![...sessions].every(id => typeof id === "string" && id) ||
        events[0]?.type !== "step_start" || events.some(event => !OPEN_CODE_EVENTS.has(event?.type)) ||
        last?.type !== "step_finish" || last.part?.reason !== "stop") {
      throw new Error("This trace does not show one completed OpenCode session.");
    }
    const skillEvents = events.filter(event => event.type === "tool_use" && event.part?.tool === "skill");
    if (skillEvents.some(event => event.part.state?.status !== "completed" ||
        !window.SkillsV2Model.validName(event.part.state?.input?.id))) {
      throw new Error("A skill event is incomplete or uses an unsupported format.");
    }
    return [...new Set(skillEvents.map(event => event.part.state.input.id))];
  }

  window.SkillsV2AiDiagnostic = {
    props: { copy: Object, records: Array, editable: Boolean },
    emits: ["repair"],
    data() { return { agents: [], consumer: this.copy.record.consumer || "", project: "", report: null,
      prompt: "", wanted: true, estimate: null, result: null, key: "", busy: false, error: "",
      trace: null, traceError: "", traceSequence: 0, saved: "" }; },
    computed: {
      inputKey() { return JSON.stringify([this.prompt.trim(), this.wanted]); },
      entry() { return this.report?.skills?.[this.copy.name]; },
      duplicates() { return this.records.filter(row => row.name === this.copy.name && row.scope === this.copy.scope).length; },
      choices() { return Object.entries(this.result?.prompts?.[0]?.choices || {}); },
    },
    async mounted() {
      try {
        const response = await api("/api/workspaces");
        this.agents = response.adapters || [];
        if (!this.agents.some(agent => agent.id === this.consumer) && this.agents.some(agent => agent.id === this.copy.scope)) this.consumer = this.copy.scope;
      } catch (error) { this.error = error.message; }
    },
    methods: {
      async inspect() {
        if (this.busy || !this.consumer) return;
        this.busy = true; this.error = ""; this.report = null;
        try {
          const url = `/api/doctor?explain=${enc(this.consumer)}&skill=${enc(this.copy.name)}${this.project.trim() ? "&project=" + enc(this.project.trim()) : ""}`;
          this.report = (await api(url)).explain;
        } catch (error) { this.error = error.message; }
        finally { this.busy = false; }
      },
      promptRows() { return [{ text: this.prompt.trim(), expected: this.wanted ? this.copy.name : null }]; },
      async simulate(estimate) {
        if (this.busy || !this.prompt.trim() || (!estimate && this.key !== this.inputKey)) return;
        this.busy = true; this.error = ""; this.result = null; this.saved = "";
        const key = this.inputKey;
        try {
          const answer = await post("/api/ai/trigger-test", { scope: this.copy.scope, prompts: this.promptRows(), repeats: 3, estimate });
          if (key !== this.inputKey) return;
          if (estimate) { this.estimate = answer; this.key = key; }
          else this.result = answer;
        } catch (error) { this.error = error.message; }
        finally { this.busy = false; }
      },
      async saveCase() {
        if (this.busy || !this.result || this.key !== this.inputKey) return;
        this.busy = true; this.error = "";
        try {
          await post("/api/ai/prompt-sets", { scope: this.copy.scope, prompts: this.promptRows() });
          this.saved = "Saved to this scope’s regression prompts.";
        } catch (error) { this.error = error.message; }
        finally { this.busy = false; }
      },
      async readTrace(event) {
        const sequence = ++this.traceSequence;
        const file = event.target.files?.[0];
        this.trace = null; this.traceError = "";
        if (!file) return;
        try {
          if (file.size > TRACE_LIMIT) throw new Error("Choose a trace at most 512 KB.");
          const names = openCodeTrace(await file.text());
          if (sequence === this.traceSequence) this.trace = names;
        } catch (error) {
          if (sequence === this.traceSequence) this.traceError = error instanceof SyntaxError ? "The trace is not valid JSONL." : error.message;
        }
      },
    },
    template: `<div>
      <p><strong>{{ copy.name }}</strong> · {{ copy.scope }} <code>{{ copy.path }}</code></p>
      <p class="tp-fine" v-if="copy.record.disabled">This copy is disabled on disk.</p>
      <p class="tp-fine" v-if="copy.record.frontmatter_extensions?.['disable-model-invocation'] === true">Its frontmatter declares manual invocation.</p>
      <p class="tp-fine" v-if="duplicates > 1">{{ duplicates }} copies share this name in the selected scope. Simulation resolves names.</p>
      <h3>Discovery on disk</h3>
      <label class="tp-field">Agent<select class="field" v-model="consumer" :disabled="busy" @change="report=null"><option value="">Choose an agent</option><option v-for="agent in agents" :key="agent.id" :value="agent.id">{{ agent.label }}</option></select></label>
      <label class="tp-field">Project path (optional)<input class="field" maxlength="4096" v-model="project" :disabled="busy" @input="report=null"></label>
      <button type="button" class="btn btn-line btn-sm" :disabled="busy || !consumer" @click="inspect()">Check discovery</button>
      <div v-if="report" class="ai-confirm">
        <p>{{ entry?.reason || report.reason || (report.resolution === 'project-outside-managed-roots' ? 'This project is outside the allowed folders.' : 'No instance was reported by the documented rules.') }}</p>
        <p v-if="entry?.winner?.path">Suggested copy <code>{{ entry.winner.path }}</code></p>
        <p v-for="(note, i) in report.warnings" :key="i" class="tp-fine">{{ note }}</p>
      </div>
      <h3>Simulate a request</h3>
      <label class="tp-field">Request<textarea class="field instance-create-body" rows="3" maxlength="600" :disabled="busy" v-model="prompt"></textarea></label>
      <label class="tp-check"><input type="checkbox" :disabled="busy" v-model="wanted"> This request should select {{ copy.name }}</label>
      <button type="button" class="btn btn-line btn-sm" :disabled="busy || !prompt.trim()" @click="simulate(true)">Preview simulation</button>
      <div v-if="estimate && key === inputKey && !result" class="ai-confirm">
        <p v-for="(line,i) in estimate.egress" :key="i">{{ line }}</p><button type="button" class="btn btn-ink btn-sm" :disabled="busy" @click="simulate(false)">Send and simulate</button>
      </div>
      <div v-if="result && key === inputKey" class="ai-confirm">
        <p>Simulated {{ result.repeats }} times with {{ result.run.model }}. This scope supplied {{ result.listed }} skill descriptions.</p>
        <ul v-if="choices.length"><li v-for="[name, count] in choices" :key="name">{{ name === '(none)' ? 'No skill' : name }} · {{ count }}</li></ul>
        <p v-else>There were no conclusive choices.</p>
        <p v-if="result.invalid_answers || result.missing_answers">Incomplete or invalid answers were reported.</p>
        <button type="button" class="btn btn-line btn-sm" :disabled="busy || !!saved" @click="saveCase()">Save regression case</button>
        <p v-if="saved" role="status">{{ saved }}</p>
      </div>
      <p v-if="busy" role="status">Checking…</p><p v-if="error" class="state-note err" role="alert">{{ error }}</p>
      <button type="button" class="btn btn-line btn-sm" v-if="editable" :disabled="!prompt.trim() || busy" @click="$emit('repair', prompt.trim())">Edit skill using this request</button>
      <details class="tp-more">
        <summary>Observed invocation from an OpenCode trace</summary>
        <p class="tp-fine">Select OpenCode 2.3.2 JSONL from one completed run. The file is read in this browser.</p>
        <input aria-label="OpenCode JSONL trace" type="file" accept=".jsonl,.json,.txt" @change="readTrace($event)">
        <p v-if="traceError" class="state-note err" role="alert">{{ traceError }} Invocation is unknown.</p>
        <p v-else-if="trace" role="status">{{ trace.includes(copy.name) ? 'A completed skill load named ' + copy.name + ' was recorded.' : 'No completed load of ' + copy.name + ' was recorded.' }} This trace identifies skills by name.</p>
      </details>
    </div>`,
  };
})();
