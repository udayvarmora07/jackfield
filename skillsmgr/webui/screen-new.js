/* The creation form previews the same document the existing create API writes. */
"use strict";

window.Jackfield.register((app) => {
  const { api } = window.SkillManagerDomain;
  const { validName, shortPath, stripFrontmatter } = window.SkillsV2Model;
  const enc = encodeURIComponent;
  const layouts = [
    { title: "Blank", body: "# {name}\n" },
    { title: "Step by step", body: "# {name}\n\n## Steps\n\n1. \n" },
    { title: "Checklist", body: "# {name}\n\n## Checklist\n\n- [ ] \n" },
  ];
  const emptyForm = () => ({ name: "", description: "", body: layouts[0].body, template: "", layout: "Blank" });

  app.component("jf-new-skill", {
    props: { agents: Array, scopes: Array, records: Array, template: String, friendly: Function },
    emits: ["created", "refresh", "ai"],
    data: () => ({ form: emptyForm(), selected: [], baseline: "", templates: [], templateGeneration: 0,
      templateLoading: false, previewGeneration: 0, previewTimer: null, preview: null, previewError: "",
      writing: false, outcomes: new Map(), submitError: "", finished: false,
      starterBody: layouts[0].body, pendingStarter: null }),
    computed: {
      name() { return this.form.name.trim(); },
      dirty() { return !this.finished && !!this.baseline && this.draftKey() !== this.baseline; },
      fixedName() {
        return this.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64).replace(/-+$/, "");
      },
      rules() {
        return [
          { text: "Lowercase letters, numbers and hyphens", pass: /^[a-z0-9-]+$/.test(this.name) },
          { text: "Single hyphens between words", pass: /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(this.name) },
          { text: "64 characters or fewer", pass: !!this.name && this.name.length <= 64 },
        ];
      },
      descriptionLength() { return Array.from(this.form.description.trim()).length; },
      existing() { return new Set(this.records.filter((record) => record.name === this.name).map((record) => record.scope)); },
      results() { return this.outcomes.get(this.name) || new Map(); },
      places() {
        return this.agents.map((agent) => ({ ...agent, existing: this.existing.has(agent.id), outcome: this.results.get(agent.id),
          path: this.scopes.find((scope) => scope.id === agent.id)?.path || agent.path }));
      },
      targets() { return this.places.filter((place) => this.selected.includes(place.id) && !place.existing && !place.outcome); },
      payload() {
        if (!validName(this.name) || !this.descriptionLength || this.descriptionLength > 1024 || this.templateLoading) return null;
        return { name: this.name, description: this.form.description.trim(), body: this.form.body.replaceAll("{name}", this.name) };
      },
      payloadKey() { return this.payload ? JSON.stringify(this.payload) : ""; },
      ready() { return !this.writing && !this.pendingStarter && this.targets.length > 0 && this.preview?.key === this.payloadKey; },
      skillHref() { return window.Jackfield.router.skillHref(this.name); },
      canOpen() { return this.existing.size > 0 || [...this.results.values()].some((result) => result.created); },
    },
    watch: { payloadKey() { this.queuePreview(); } },
    mounted() {
      const first = this.agents.find((agent) => !agent.library) || this.agents[0];
      this.selected = first ? [first.id] : [];
      this.baseline = this.draftKey();
      this.$refs.name.focus();
      this.loadTemplates();
    },
    beforeUnmount() { this.previewGeneration++; this.templateGeneration++; clearTimeout(this.previewTimer); },
    methods: {
      draftKey() { return JSON.stringify([this.form, this.selected]); },
      finish() { this.finished = true; },
      cancel() { window.Jackfield.router.go("#/skills"); },
      async loadTemplates() {
        const generation = this.templateGeneration;
        const body = this.form.body;
        try {
          const result = await api("/api/templates");
          if (!this.$refs.name) return;
          this.templates = result.templates || [];
          if (generation === this.templateGeneration && this.template && this.templates.includes(this.template) && body === this.form.body) {
            const pristine = !this.dirty;
            this.form.template = this.template;
            await this.readTemplate(this.template, pristine);
          }
        } catch { if (generation === this.templateGeneration) this.submitError = "Stored templates couldn’t be read."; }
      },
      chooseStarter(starter) {
        this.templateGeneration++;
        this.templateLoading = false;
        if (starter.template === "") {
          this.form.template = "";
          this.pendingStarter = null;
          return;
        }
        if (this.form.body !== this.starterBody) {
          this.pendingStarter = starter;
          this.$nextTick(() => this.$refs.keepInstructions.focus());
        } else this.applyStarter(starter);
      },
      keepInstructions() {
        this.pendingStarter = null;
        this.$nextTick(() => this.$refs.body.focus());
      },
      applyStarter(starter) {
        this.pendingStarter = null;
        if (starter.template !== undefined) {
          this.readTemplate(starter.template);
          return;
        }
        this.templateGeneration++;
        this.templateLoading = false;
        Object.assign(this.form, { layout: starter.title, template: "", body: starter.body });
        this.starterBody = starter.body;
      },
      async readTemplate(name, setBaseline = false) {
        const generation = ++this.templateGeneration;
        const before = this.form.body, draft = this.draftKey();
        this.templateLoading = !!name;
        if (!name) return;
        try {
          const result = await api("/api/templates/" + enc(name));
          if (generation !== this.templateGeneration || before !== this.form.body) return;
          const pristine = setBaseline && draft === this.draftKey();
          this.form.template = name;
          this.form.layout = "";
          this.form.body = stripFrontmatter(result.body || "");
          this.starterBody = this.form.body;
          if (pristine) this.baseline = this.draftKey();
        } catch { if (generation === this.templateGeneration) this.submitError = "This template couldn’t be read."; }
        finally { if (generation === this.templateGeneration) this.templateLoading = false; }
      },
      queuePreview() {
        const generation = ++this.previewGeneration;
        clearTimeout(this.previewTimer);
        this.preview = null;
        this.previewError = "";
        const key = this.payloadKey;
        if (key) this.previewTimer = setTimeout(() => this.readPreview(generation, key), 180);
      },
      async readPreview(generation, key) {
        try {
          const result = await api("/api/skills?preview=1", { method: "POST", body: key });
          if (generation !== this.previewGeneration) return;
          if (typeof result?.content !== "string") throw new Error("The preview returned no file text.");
          this.preview = { key, content: result.content };
        } catch (error) { if (generation === this.previewGeneration) this.previewError = this.friendly(error.message); }
      },
      async create() {
        if (!this.ready) return;
        const name = this.name, body = this.payloadKey, targets = [...this.targets];
        const results = new Map(this.results);
        this.writing = true;
        this.submitError = "";
        try {
          for (const place of targets) {
            try {
              const created = await api("/api/skills?scope=" + enc(place.id), { method: "POST", body });
              if (created?.name !== name) throw new Error("The response couldn’t confirm the new file.");
              results.set(place.id, { created: true });
            } catch (error) { results.set(place.id, { error: this.friendly(error.message) }); }
            this.outcomes.set(name, new Map(results));
          }
        } finally { this.writing = false; }
        if (targets.every((place) => results.get(place.id)?.created)) {
          this.finish();
          this.$emit("created", { name, count: targets.length });
        } else {
          this.submitError = "Some places couldn’t be confirmed. Review the results below before trying those places again.";
          this.$emit("refresh");
        }
      },
      openSkill(event) {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        this.finish();
      },
    },
    template: `<div class="jf-skill-reader jf-create">
      <header class="jf-reader-heading"><div class="jf-reader-title">
        <nav aria-label="Breadcrumb"><a href="#/skills">Skills</a><span aria-hidden="true">/</span><span aria-current="page">New skill</span></nav>
        <h1 id="h1" tabindex="-1">New skill</h1>
      </div></header>
      <div class="jf-reader-body">
        <form id="jf-create-form" class="jf-reader-document" @submit.prevent="create">
          <fieldset :disabled="writing">
            <label class="sm-label" for="nf-name">Name</label>
            <p class="sm-hint" id="jf-create-name-hint">The folder name every agent sees, like <b>explain-code</b>.</p>
            <input class="field" ref="name" id="nf-name" v-model="form.name" autocomplete="off" spellcheck="false"
              :aria-invalid="name && !payload && !rules.every(rule => rule.pass) ? 'true' : null" aria-describedby="jf-create-name-hint jf-create-rules">
            <ul id="jf-create-rules" class="jf-create-rules"><li v-for="rule in rules" :key="rule.text">
              <ic :name="rule.pass ? 'check' : 'dash'"></ic><span v-if="name" class="sr-only">{{ rule.pass ? 'Pass: ' : 'Needs change: ' }}</span>{{ rule.text }}
            </li></ul>
            <button v-if="fixedName && fixedName !== name" type="button" class="sm-btn" @click="form.name = fixedName">Use {{ fixedName }}</button>
            <p v-if="canOpen" class="sm-hint" role="status">A copy is already present. <a :href="skillHref" @click="openSkill">Open it</a></p>
            <label class="sm-label" for="nf-desc">What it does and when to use it</label>
            <textarea class="sm-textarea" id="nf-desc" v-model="form.description" rows="3" aria-describedby="jf-create-count"></textarea>
            <p id="jf-create-count" class="sm-hint">{{ descriptionLength }} of 1,024 characters</p>
            <p class="sm-label" id="jf-create-places-title">Add it to</p>
            <div role="group" aria-labelledby="jf-create-places-title">
              <p class="sm-hint">Pick one or more. Each folder gets its own copy.</p>
              <label v-for="place in places" :key="place.id" class="jf-editor-place">
                <input type="checkbox" class="sm-check" v-model="selected" :value="place.id" :disabled="place.existing || !!place.outcome">
                <span><jf-agent :agent="{ ...place, path: shortPath(place.path) }" :title="place.path"></jf-agent><small v-if="place.outcome?.error">{{ place.outcome.error }}</small>
                  <small v-else-if="place.outcome?.created">Created</small><small v-else-if="place.existing">Already here</small></span>
              </label>
            </div>
            <p class="sm-label" id="jf-create-layouts-title">Start from</p>
            <div class="jf-create-layouts" role="group" aria-labelledby="jf-create-layouts-title">
              <button v-for="layout in layouts" :key="layout.title" class="sm-btn" type="button" :aria-pressed="form.layout === layout.title" @click="chooseStarter(layout)">{{ layout.title }}</button>
            </div>
            <label v-if="templates.length" class="jf-create-template">Stored template
              <select class="field" :value="form.template" @change="chooseStarter({ template: $event.target.value }); $event.target.value = form.template">
                <option value="">Choose a template</option><option v-for="name in templates" :key="name" :value="name">{{ name }}</option>
              </select>
            </label>
            <label class="sm-label" for="nf-body">Instructions</label>
            <div v-if="pendingStarter" class="jf-create-confirm" role="group" aria-label="Replace instructions?">
              <p>Replace your instructions with this starting text?</p>
              <button ref="keepInstructions" type="button" class="sm-btn sm-btn--accent" @click="keepInstructions">Keep editing</button>
              <button type="button" class="sm-btn" @click="applyStarter(pendingStarter)">Replace instructions</button>
            </div>
            <textarea class="sm-textarea sm-textarea--file" ref="body" id="nf-body" rows="8" v-model="form.body" :disabled="templateLoading"></textarea>
            <button type="button" class="sm-btn sm-btn--quiet" @click="$emit('ai', { name: form.name, description: form.description, body: form.body, scope: selected[0] })">Create with AI or add metadata</button>
          </fieldset>
        </form>
        <aside class="jf-reader-details jf-create-preview" aria-label="What will be created">
          <div><h2>What will be created</h2><p class="sm-hint">Nothing is written until you press Create.</p></div>
          <div v-if="name"><h3 class="sm-cap">In the Skills table</h3><p translate="no">{{ name }}</p></div>
          <div v-if="payload && targets.length"><h3 class="sm-cap">New files</h3><ul><li v-for="place in targets" :key="place.id"><code translate="no" :title="place.path">{{ shortPath(place.path) }}/{{ name }}/SKILL.md</code></li></ul></div>
          <div v-if="preview"><h3 class="sm-cap">SKILL.md</h3><pre class="sm-filetext" v-text="preview.content"></pre></div>
          <p v-else-if="previewError" class="state-note err" role="alert">{{ previewError }} <button type="button" class="sm-btn" @click="queuePreview">Retry preview</button></p>
          <p v-else class="sm-hint" role="status">{{ payloadKey ? 'Preparing file preview…' : 'Enter a valid name and description to see the file.' }}</p>
          <p v-if="submitError" class="state-note err" role="alert">{{ submitError }}</p>
          <div class="jf-create-layouts"><button type="button" class="sm-btn" :disabled="writing" @click="cancel">Cancel</button>
            <button class="sm-btn sm-btn--accent" type="submit" form="jf-create-form" :disabled="!ready">{{ writing ? 'Creating…' : targets.length ? 'Create in ' + targets.length + (targets.length === 1 ? ' place' : ' places') : 'Create' }}</button>
          </div>
        </aside>
      </div>
    </div>`,
    setup() { return { layouts, shortPath }; },
  });
});
