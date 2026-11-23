/* AI assist pages (docs/39). Bring your own key; every model answer is shown as
 * text and labelled as an estimate. Nothing here writes a skill except the
 * explicit "Use this description" action, which goes through the ordinary
 * PATCH edit route (snapshot + Undo in Recovery). */
(function () {
  const api = window.SkillManagerDomain.api;
  const post = (url, body) => api(url, { method: "POST", body: JSON.stringify(body || {}) });
  const pct = (v) => (v == null ? "–" : Math.round(v * 100) + "%");
  const HANDOFF = "skillsmgr-ai-target";
  const ROUTING_NOTICE = "Model simulation only. This does not run the consumer's native skill-selection system or establish which skill it would actually load.";

  window.SkillsV2AiCenter = {
    props: { page: String, records: { type: Array, default: () => [] }, scopes: { type: Array, default: () => [] }, target: Object },
    emits: ["changed", "use-draft", "open-source-review", "open-record"],
    data() {
      return {
        settings: null, form: { provider: "", model: "", base_url: "", api_key: "", max_run_tokens: 300000, max_day_tokens: 2000000 },
        busy: false, inflight: 0, error: "", note: "", connection: null,
        scope: "", mode: "generate", chosen: [], filter: "", perSkill: 3, nearMisses: 2, promptText: "", repeats: 1,
        estimate: null, result: null,
        portName: "", portTarget: "codex", ported: null, portEstimate: null, portRequest: 0,
        explainName: "", explained: null, explainEstimate: null, explainRequest: 0,
        question: "", askScope: "all", asked: null, askEstimate: null, askKey: "",
        evalName: "", evalMax: 10, evalTrials: 3, evalResult: null, evalEstimate: null,
        ablateName: "", ablateSection: "", ablateTrials: 3, ablateMax: 10, ablatePlacebo: false, ablateSections: [], ablateEstimate: null, ablateEstimateKey: "",
        ablateResult: null, ablateRequest: 0, ablateReviewOwned: true,
        conflictsScope: "global", conflictsProject: "", conflictsMax: 20, conflictsVotes: 2, conflictsReport: null, conflictsEstimate: null, conflictsRequest: 0,
        savedCount: 0, savedPrompts: [], savedNote: "", savedError: "", savedBusy: false, savedRequest: 0,
        pastRuns: [], pastRun: null, historyError: "", historyBusy: false, historyRequest: 0,
        draftScope: "", draftName: "", draftBrief: "", draftEstimate: null, draftEstimateKey: "", draftResult: null,
        conciseScope: "", conciseName: "", conciseTargetKey: "", conciseEstimate: null, conciseEstimateKey: "", conciseResult: null, conciseRequest: 0, conciseReviewOwned: true, conciseOpening: false,
        profileProject: "", profileScope: "", profileEstimate: null, profileEstimateKey: "", profileResult: null, profileRequest: 0,
        profileName: "", profileDescription: "", profileSkills: [], profileSaving: false,
        budgetChars: "", budgetMax: 5, budget: null, budgetEstimate: null, appliedNames: [],
        overlapLimit: 6, pairA: "", pairB: "", pairs: [], overlap: null, overlapEstimate: null,
        improveName: "", candidates: 2, improve: null, improveEstimate: null, applied: "",
      };
    },
    computed: {
      routingNotice() { return ROUTING_NOTICE; },
      provider() { return ((this.settings && this.settings.providers) || []).find((p) => p.id === this.form.provider) || null; },
      configured() { return !!(this.settings && this.settings.configured); },
      agentScopes() {
        const counts = new Map();
        for (const r of this.records) if (!r.disabled) counts.set(r.scope, (counts.get(r.scope) || 0) + 1);
        return this.scopes.filter((s) => s.id !== "all" && counts.get(s.id)).map((s) => ({ id: s.id, label: s.id === "global" ? "Your library" : s.label || s.id, count: counts.get(s.id) }));
      },
      scopeSkills() {
        const seen = new Set(); const out = [];
        for (const r of this.records) if (r.scope === this.scope && !r.disabled && !seen.has(r.name)) { seen.add(r.name); out.push(r.name); }
        return out.sort();
      },
      pickable() { const q = this.filter.trim().toLowerCase(); return this.scopeSkills.filter((n) => !q || n.includes(q)); },
      parsedPrompts() {
        return this.promptText.split("\n").map((l) => l.trim()).filter(Boolean).map((line) => {
          const m = line.match(/^(.*?)\s*=>\s*([a-z0-9-]+|none)\s*$/);
          return m ? { text: m[1], expected: m[2] === "none" ? null : m[2] } : { text: line, expected: null };
        });
      },
      troubled() { return ((this.result && this.result.skills) || []).filter((s) => s.verdict !== "fires"); },
      usage() { return (this.settings && this.settings.usage) || null; },
      draftScopes() {
        return this.scopes.filter((s) => s.writable && s.availability !== "read-only")
          .map((s) => ({ id: s.id, label: s.id === "global" ? "Your library" : s.label || s.id, count: Number(s.count) || 0 }));
      },
      draftEstimateCurrent() { return !!this.draftEstimate && this.draftEstimateKey === this.draftInputKey(); },
      canUseDraft() {
        const draft = this.draftResult && this.draftResult.draft;
        return !!(this.draftResult && this.draftResult.status === "verified" && this.draftResult.validation
          && this.draftResult.validation.valid === true && draft
          && ["name", "description", "body"].every((key) => typeof draft[key] === "string"));
      },
      conciseScopes() { const ids = new Set(this.records.filter((r) => this.conciseWritable(r)).map((r) => r.scope)); return this.scopes.filter((s) => ids.has(s.id)).map((s) => ({ id: s.id, label: s.id === "global" ? "Your library" : s.label || s.id })); },
      conciseNames() { return [...new Set(this.records.filter((r) => r.scope === this.conciseScope && this.conciseWritable(r)).map((r) => r.name))].sort(); },
      conciseRecords() {
        const seen = new Set(); const out = [];
        for (const r of this.records) { if (r.scope !== this.conciseScope || r.name !== this.conciseName || !this.conciseWritable(r)) continue;
          const path = r.physical_path || r.path; const key = JSON.stringify([r.scope, r.name, path]);
          if (!seen.has(key)) { seen.add(key); out.push({ record: r, key, path }); }
        }
        return out;
      },
      conciseTarget() { return this.conciseRecords.find((x) => x.key === this.conciseTargetKey) || null; },
      conciseEstimateCurrent() { return !!this.conciseEstimate && this.conciseEstimateKey === this.conciseInputKey(); },
      canOpenConciseReview() { return !!(!this.conciseOpening && this.conciseResult && this.conciseResult.status === "review-required" && this.conciseResult.review && this.conciseResult.review.review_id && this.conciseTarget); },
      profileScopes() { return this.scopes.filter((s) => s.writable && s.availability !== "read-only").map((s) => ({ id: s.id, label: s.id === "global" ? "Your library" : s.label || s.id })); },
      profileEstimateCurrent() { return !!this.profileEstimate && this.profileEstimateKey === this.profileInputKey(); },
      profileNameValid() { return /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(this.profileName.trim()); },
      profileProposalValid() {
        const p = this.profileResult && this.profileResult.profile;
        const allExisting = new Set(this.records.filter((r) => r.scope === this.profileScope).map((r) => r.name));
        return !!(this.profileResult && this.profileResult.status === "suggested" && p && this.profileNameValid
          && this.profileDescription.length <= 500 && Array.isArray(this.profileSkills) && this.profileSkills.length > 0
          && this.profileSkills.every((name) => typeof name === "string" && allExisting.has(name)));
      },
      profileDroppedCount() { const value = this.profileResult && this.profileResult.dropped_names; return Array.isArray(value) ? value.length : Number(value) || 0; },
    },
    watch: {
      page: { immediate: true, handler(next, previous) { if (previous === "ai-port" || previous === "ai-explain") { this.clearPort(); this.clearExplain(); } if (previous === "ai-concise" && next !== "ai-concise") this.clearConciseProposal(); if (previous === "ai-profile" && next !== "ai-profile") this.clearProfileSuggestion(); if (previous === "ai-ablate" && next !== "ai-ablate") this.clearAblate(); this.error = ""; this.note = ""; this.load(); this.takeHandoff(); this.loadSaved(); } },
      explainName() { this.clearExplain(); },
      portName() { this.clearPort(); },
      portTarget() { this.clearPort(); },
      scope() { this.clearPort(); this.clearExplain(); this.portName = ""; this.explainName = ""; this.loadSaved(); this.budget = null; this.budgetEstimate = null; this.pairs = []; this.overlap = null; this.overlapEstimate = null; this.chosen = []; this.estimate = null; this.result = null; this.improve = null; this.improveEstimate = null; },
      draftScope() { this.clearDraftProposal(); },
      draftName() { this.clearDraftProposal(); },
      draftBrief() { this.clearDraftProposal(); },
      conciseScope() { this.conciseName = ""; this.conciseTargetKey = ""; this.clearConciseProposal(); },
      conciseName() { this.conciseTargetKey = ""; this.clearConciseProposal(); },
      conciseTargetKey() { this.clearConciseProposal(); },
      records() { if (this.page === "ai-concise" && this.conciseTargetKey && !this.conciseTarget) this.clearConciseProposal(); },
      profileProject() { this.clearProfileSuggestion(); },
      profileScope() { this.clearProfileSuggestion(); },
      profileScopes: { immediate: true, handler(list) { if (!list.some((s) => s.id === this.profileScope)) this.profileScope = (list[0] || {}).id || ""; } },
      conciseScopes: { immediate: true, handler(list) { if (!list.some((s) => s.id === this.conciseScope)) this.conciseScope = (list[0] || {}).id || ""; } },
      /* Default the agent pickers. "Your library" can be empty, which left the
       * Contradiction check's "Skills from" select blank; fall back to the
       * first agent folder that has skills. */
      agentScopes: { immediate: true, handler(list) { if (!this.scope && list.length) this.scope = (list.find((s) => s.id === "claude-code") || list[0]).id; if (list.length && !list.some((sc) => sc.id === this.conflictsScope)) this.conflictsScope = list[0].id; } },
      draftScopes: { immediate: true, handler(list) { if (!list.some((s) => s.id === this.draftScope)) this.draftScope = (list.find((s) => s.id === "global") || list[0] || {}).id || ""; } },
    },
    methods: {
      /* The page's one-line purpose, from the shared tool catalog, so a page
       * reached with AI off still says what it is for. */
      toolLede(id) { const item = (window.SkillsV2Model.toolItems || []).find((t) => t.id === id); return item ? item.text : ""; },
      pct,
      fmt(n) { return n == null ? "–" : Number(n).toLocaleString(); },
      relationTone(r) { return { "same-purpose": "bad", overlapping: "warn", uncertain: "note", distinct: "ok" }[r] || "off"; },
      relationLabel(r) { return { "same-purpose": "Same purpose", overlapping: "Overlapping", uncertain: "Uncertain: depends on order", distinct: "Distinct", unknown: "No clear answer" }[r] || r; },
      actionLabel(a) { return { merge: "Merge them", "narrow-descriptions": "Sharpen both descriptions", "keep-both": "Keep both as they are", review: "Answers disagreed: review yourself" }[a] || a; },
      budgetBody(estimate) { const b = { scope: this.scope, max_skills: Number(this.budgetMax), estimate }; if (String(this.budgetChars).trim()) b.budget_chars = Number(this.budgetChars); return b; },
      async estimateBudget() { this.budget = null; this.appliedNames = []; this.budgetEstimate = await this.guard(() => post("/api/ai/fit-budget", this.budgetBody(true))); },
      async runBudget() { const r = await this.guard(() => post("/api/ai/fit-budget", this.budgetBody(false))); if (r) { this.budget = r; this.budgetEstimate = null; this.load(); } },
      async applyShort(p) {
        if (!confirm("Replace the description of " + p.name + " in " + this.budget.scope + " with the shorter version? A snapshot of the current file is kept.")) return;
        const ok = await this.guard(() => api("/api/skills/" + encodeURIComponent(p.name) + "?scope=" + encodeURIComponent(this.budget.scope), { method: "PATCH", body: JSON.stringify({ description: p.proposed }) }));
        if (ok) { this.appliedNames.push(p.name); this.note = "Saved " + p.name + ". The previous version is in Recovery → history."; this.$emit("changed"); }
      },
      async localToolRequest(fn, current) {
        this.begin();
        try { return await fn(); } catch (e) { if (current()) this.error = (e && e.message) || String(e); return null; } finally { this.end(); }
      },
      clearPort() { this.portRequest++; this.ported = null; this.portEstimate = null; },
      clearExplain() { this.explainRequest++; this.explained = null; this.explainEstimate = null; },
      async port(step) {
        if (this.busy || this.page !== "ai-port" || !this.portName || (step !== "local" && !this.configured) || (step === "send" && (!this.portEstimate || this.portEstimate.scope !== this.scope || this.portEstimate.name !== this.portName || this.portEstimate.target !== this.portTarget))) return;
        const request = ++this.portRequest, key = JSON.stringify([this.scope, this.portName, this.portTarget]);
        const body = { scope: this.scope, name: this.portName, target: this.portTarget, local_only: step === "local", estimate: step === "estimate", reviewed: true, plan: step === "send" ? this.portEstimate.plan : undefined };
        this.portEstimate = null;
        const current = () => request === this.portRequest && this.page === "ai-port" && key === JSON.stringify([this.scope, this.portName, this.portTarget]);
        const r = await this.localToolRequest(() => post("/api/ai/porting-notes", body), current);
        if (!r || !current()) return;
        if (step === "estimate" && r.run) this.portEstimate = r;
        else { this.ported = r; if (step === "send") { this.portEstimate = null; this.load(); } }
      },
      async explain(step) {
        if (this.busy || this.page !== "ai-explain" || !this.explainName || (step !== "local" && !this.configured) || (step === "send" && (!this.explainEstimate || this.explainEstimate.scope !== this.scope || this.explainEstimate.name !== this.explainName))) return;
        const request = ++this.explainRequest, key = JSON.stringify([this.scope, this.explainName]);
        const body = { scope: this.scope, name: this.explainName, local_only: step === "local", estimate: step === "estimate", reviewed: true, plan: step === "send" ? this.explainEstimate.plan : undefined };
        this.explainEstimate = null;
        const current = () => request === this.explainRequest && this.page === "ai-explain" && key === JSON.stringify([this.scope, this.explainName]);
        const r = await this.localToolRequest(() => post("/api/ai/explain-findings", body), current);
        if (!r || !current()) return;
        if (step === "estimate" && r.run) this.explainEstimate = r;
        else { this.explained = r; if (step === "send") { this.explainEstimate = null; this.load(); } }
      },
      opinionFor(i) { return ((this.explained && this.explained.opinions) || []).find((o) => o.index === i) || null; },
      opinionLabel(o) { return { "likely-real": ["warn", "Likely a real concern"], "likely-false-positive": ["ok", "Likely a false positive"], unclear: ["off", "No clear opinion"] }[o] || ["off", o]; },
      askInputKey() { return JSON.stringify([this.question.trim(), this.askScope]); },
      async ask(estimate) {
        const key = this.askInputKey();
        if (this.busy || !this.question.trim() || (!estimate && this.askKey !== key)) return;
        this.asked = null;
        const result = await this.guard(() => post("/api/ai/ask", { question: this.question, scope: this.askScope,
          reviewed: true, estimate, plan: estimate ? undefined : this.askEstimate?.plan }));
        if (!result || key !== this.askInputKey() || this.page !== "ai-ask") return;
        if (estimate) { this.askEstimate = result; this.askKey = key; }
        else this.asked = result;
      },
      matchingCopies(match) {
        return this.records.filter(r => r.name === match.name && match.scopes.includes(r.scope) && !r.disabled).slice(0, 12);
      },
      skillHref(name) { return "#/skill/" + encodeURIComponent(name); },
      librarySkills() { return [...new Set(this.records.filter((r) => r.scope === "global").map((r) => r.name))].sort(); },
      ablateInputKey() { return JSON.stringify([this.ablateName, this.ablateSection, this.ablateTrials, this.ablateMax, this.ablatePlacebo]); },
      ablateBody(extra) {
        return { name: this.ablateName, section: this.ablateSection === "" ? null : Number(this.ablateSection),
          trials: Number(this.ablateTrials), max_cases: Number(this.ablateMax), placebo: !!this.ablatePlacebo, ...extra };
      },
      clearAblate() {
        this.ablateRequest++;
        const old = this.ablateResult;
        if (old && old.proposal && this.ablateReviewOwned) this.cancelConciseReview(old.proposal);
        this.ablateEstimate = null; this.ablateEstimateKey = ""; this.ablateResult = null; this.ablateReviewOwned = true;
      },
      async chooseAblateSkill() {
        this.clearAblate(); this.ablateSection = ""; this.ablateSections = [];
        if (!this.ablateName) return;
        const req = this.ablateRequest; const name = this.ablateName;
        const r = await this.guard(() => post("/api/ai/ablate", this.ablateBody({ section: null, estimate: true })));
        if (r && req === this.ablateRequest && name === this.ablateName) this.ablateSections = r.sections || [];
      },
      async estimateAblate() {
        this.clearAblate(); const req = this.ablateRequest; const key = this.ablateInputKey();
        const r = await this.guard(() => post("/api/ai/ablate", this.ablateBody({ estimate: true })));
        if (r && req === this.ablateRequest && key === this.ablateInputKey()) { this.ablateEstimate = r; this.ablateEstimateKey = key; }
      },
      async runAblate() {
        if (!this.ablateEstimate || this.ablateEstimateKey !== this.ablateInputKey()) return;
        const req = ++this.ablateRequest; const key = this.ablateInputKey();
        const r = await this.guard(() => post("/api/ai/ablate", this.ablateBody({ plan: this.ablateEstimate.plan })));
        if (!r) return;
        if (req !== this.ablateRequest || key !== this.ablateInputKey() || this.page !== "ai-ablate") { if (r.proposal) await this.cancelConciseReview(r.proposal); return; }
        this.ablateResult = r; this.ablateReviewOwned = true; this.ablateEstimate = null; this.ablateEstimateKey = ""; this.loadRuns();
      },
      openAblateReview() {
        const r = this.ablateResult; const review = r && r.proposal && r.proposal.review;
        const record = this.records.find((x) => x.scope === "global" && x.name === r.name);
        if (!review || !record) return;
        this.ablateReviewOwned = false;
        this.$emit("open-source-review", { target: record, reviewId: review.review_id });
      },
      ablateDecision(d) {
        return { remove: ["warn", "Little or no loss without it: removal proposed"], keep: ["ok", "It helps: keep it"],
          uncertain: ["off", "Uncertain: removal not shown to be safe"], untested: ["warn", "Untested: these cases cannot show its effect"], "not-enough-evidence": ["off", "Not enough evidence"] }[d] || ["off", d];
      },
      conflictsBody(extra) { return { scope: this.conflictsScope, project: this.conflictsProject.trim() || null, ...extra }; },
      async findConflicts() {
        const req = ++this.conflictsRequest; this.conflictsEstimate = null; this.conflictsReport = null;
        const r = await this.guard(() => post("/api/ai/conflicts", this.conflictsBody({})));
        if (req === this.conflictsRequest) this.conflictsReport = r;
      },
      async estimateConflictJudge() {
        const req = ++this.conflictsRequest;
        const r = await this.guard(() => post("/api/ai/conflicts", this.conflictsBody({ judge: true, max_pairs: Number(this.conflictsMax), votes: Number(this.conflictsVotes), estimate: true })));
        if (req === this.conflictsRequest) this.conflictsEstimate = r;
      },
      async runConflictJudge() {
        if (!this.conflictsEstimate || !this.conflictsEstimate.plan) return;
        const req = ++this.conflictsRequest;
        const r = await this.guard(() => post("/api/ai/conflicts", this.conflictsBody({ judge: true, max_pairs: Number(this.conflictsMax), votes: Number(this.conflictsVotes), plan: this.conflictsEstimate.plan })));
        if (r && req === this.conflictsRequest) { this.conflictsReport = r; this.conflictsEstimate = null; this.loadRuns(); }
      },
      conflictLabel(pair) {
        const j = pair.judge;
        if (!j) return ["off", pair.kind === "choice" ? "Possible clash (word pattern)" : "Possible clash (opposite wording)"];
        return { conflict: ["bad", "AI: conflict"], compatible: ["ok", "AI: compatible"], unclear: ["warn", "AI: unclear"] }[j.verdict] || ["off", j.verdict];
      },
      evalBody(estimate) { return { name: this.evalName, max_cases: Number(this.evalMax), trials: Number(this.evalTrials), estimate }; },
      async estimateEvals() { this.evalResult = null; this.evalEstimate = await this.guard(() => post("/api/ai/evals", this.evalBody(true))); },
      async runEvals() { const r = await this.guard(() => post("/api/ai/evals", this.evalBody(false))); if (r) { this.evalResult = r; this.evalEstimate = null; this.load(); } },
      evalVerdict(v) { return { helps: ["ok", "The skill helps"], "not-needed": ["warn", "Passes without the skill: it may no longer be needed"], "no-gain": ["warn", "No difference with the skill"], hurts: ["bad", "Worse with the skill"], ungraded: ["off", "No assertions to grade"] }[v] || ["off", v]; },
      addPair() { if (this.pairA && this.pairB && this.pairA !== this.pairB && this.pairs.length < 12) { this.pairs.push([this.pairA, this.pairB]); this.pairA = this.pairB = ""; } },
      overlapBody(estimate) { return { scope: this.scope, max_pairs: Number(this.overlapLimit), pairs: this.pairs, estimate }; },
      async estimateOverlap() { this.overlap = null; this.overlapEstimate = await this.guard(() => post("/api/ai/overlap-judge", this.overlapBody(true))); },
      async runOverlap() { const r = await this.guard(() => post("/api/ai/overlap-judge", this.overlapBody(false))); if (r) { this.overlap = r; this.overlapEstimate = null; this.load(); } },
      verdictTone(v) { return v === "fires" ? "ok" : v === "never-fires" ? "bad" : "warn"; },
      verdictLabel(v) { return { fires: "Selected in simulation", "never-fires": "Not selected in simulation", unreliable: "Mixed simulation results", unknown: "Unknown" }[v] || v; },
      skillLabel(n) { return n === "(none)" ? "no skill" : n; },
      choiceList(choices) { return Object.entries(choices || {}).sort((a, b) => b[1] - a[1]).map(([k, n]) => this.skillLabel(k) + (n > 1 ? " ×" + n : "")).join(", "); },
      draftInputKey() { return JSON.stringify([this.draftScope, this.draftName.trim(), this.draftBrief.trim()]); },
      clearDraftProposal() { this.draftEstimate = null; this.draftEstimateKey = ""; this.draftResult = null; },
      conciseWritable(r) { return !!(r && r.addressable !== false && (r.physical_path || r.path) && this.scopes.some((s) => s.id === r.scope && s.writable)); },
      conciseInputKey() { return JSON.stringify([this.conciseScope, this.conciseName, this.conciseTargetKey]); },
      async cancelConciseReview(result) {
        const review = result && result.review;
        if (!review || !review.review_id || review.review_state !== "pending") return;
        try { await api("/api/source-updates/reviews/" + encodeURIComponent(review.review_id), { method: "DELETE" }); }
        catch (e) { this.error = "Could not cancel an unused review: " + ((e && e.message) || String(e)); }
      },
      clearConciseProposal() {
        this.conciseRequest++;
        const old = this.conciseResult;
        if (old && this.conciseReviewOwned) this.cancelConciseReview(old);
        this.conciseEstimate = null; this.conciseEstimateKey = ""; this.conciseResult = null; this.conciseReviewOwned = true;
      },
      conciseBody(estimate) { const t = this.conciseTarget; return { scope: this.conciseScope, name: this.conciseName, target_path: t && t.path, estimate }; },
      async estimateConcise() {
        if (!this.conciseTarget) return;
        this.clearConciseProposal(); const req = ++this.conciseRequest; const key = this.conciseInputKey();
        const r = await this.guard(() => post("/api/ai/concise", this.conciseBody(true)));
        if (req !== this.conciseRequest || key !== this.conciseInputKey() || this.page !== "ai-concise" || !this.conciseTarget) return;
        if (r && r.status === "estimate") { this.conciseEstimate = r; this.conciseEstimateKey = key; }
      },
      async runConcise() {
        if (!this.conciseEstimateCurrent || !this.conciseTarget) return;
        const req = ++this.conciseRequest; const key = this.conciseInputKey(); this.conciseResult = null;
        const r = await this.guard(() => post("/api/ai/concise", this.conciseBody(false)));
        if (req !== this.conciseRequest || key !== this.conciseInputKey() || this.page !== "ai-concise" || !this.conciseTarget) { if (r) await this.cancelConciseReview(r); return; }
        if (r && ["review-required", "blocked", "no-change"].includes(r.status)) { this.conciseResult = r; this.conciseReviewOwned = true; this.conciseEstimate = null; this.conciseEstimateKey = ""; this.loadRuns(); }
      },
      openConciseReview() {
        if (!this.canOpenConciseReview) return;
        this.conciseOpening = true;
        this.conciseReviewOwned = false;
        this.$emit("open-source-review", { target: this.conciseTarget.record, reviewId: this.conciseResult.review.review_id });
      },
      profileInputKey() { return JSON.stringify([this.profileProject.trim(), this.profileScope]); },
      clearProfileSuggestion() {
        this.profileRequest++;
        this.profileEstimate = null; this.profileEstimateKey = ""; this.profileResult = null;
        this.profileName = ""; this.profileDescription = ""; this.profileSkills = [];
      },
      profileBody(estimate) { return { project: this.profileProject.trim(), scope: this.profileScope, estimate }; },
      async estimateProfile() {
        if (!this.profileProject.trim() || !this.profileScope) return;
        this.clearProfileSuggestion(); const request = ++this.profileRequest; const key = this.profileInputKey();
        this.begin();
        let result = null;
        try { result = await post("/api/ai/suggest-profile", this.profileBody(true)); }
        catch (e) { if (request === this.profileRequest && key === this.profileInputKey() && this.page === "ai-profile") this.error = (e && e.message) || String(e); }
        finally { this.end(); }
        if (request !== this.profileRequest || key !== this.profileInputKey() || this.page !== "ai-profile") return;
        if (result && result.status === "estimate") { this.profileEstimate = result; this.profileEstimateKey = key; }
        else if (result && result.status === "empty") this.profileResult = result;
      },
      async runProfileSuggestion() {
        if (!this.profileEstimateCurrent || !this.profileProject.trim() || !this.profileScope) return;
        const request = ++this.profileRequest; const key = this.profileInputKey();
        this.begin();
        let result = null;
        try { result = await post("/api/ai/suggest-profile", this.profileBody(false)); }
        catch (e) { if (request === this.profileRequest && key === this.profileInputKey() && this.page === "ai-profile") this.error = (e && e.message) || String(e); }
        finally { this.end(); }
        if (request !== this.profileRequest || key !== this.profileInputKey() || this.page !== "ai-profile") return;
        if (!result || !["suggested", "empty"].includes(result.status)) return;
        this.profileResult = result; this.profileEstimate = null; this.profileEstimateKey = "";
        if (result.status === "suggested" && result.profile) {
          const verified = [...new Set((Array.isArray(result.profile.skills) ? result.profile.skills : []).filter((name) => typeof name === "string" && this.records.some((r) => r.scope === this.profileScope && r.name === name)))];
          this.profileName = typeof result.profile.name === "string" ? result.profile.name : "";
          this.profileDescription = typeof result.profile.description === "string" ? result.profile.description : "";
          this.profileSkills = verified;
        }
        this.loadRuns();
      },
      toggleProfileSuggestionSkill(name, checked) {
        if (!this.profileSkills.includes(name) && checked) this.profileSkills = [...this.profileSkills, name];
        else if (!checked) this.profileSkills = this.profileSkills.filter((item) => item !== name);
      },
      async saveSuggestedProfile() {
        if (!this.profileProposalValid || this.profileSaving) return;
        const request = this.profileRequest; const key = this.profileInputKey(); const draftKey = JSON.stringify([this.profileName, this.profileDescription, this.profileSkills]); this.profileSaving = true; this.error = "";
        const unchanged = () => draftKey === JSON.stringify([this.profileName, this.profileDescription, this.profileSkills]);
        try {
          const catalog = await api("/api/catalog");
          if (request !== this.profileRequest || key !== this.profileInputKey() || this.page !== "ai-profile" || !unchanged() || !this.profileProposalValid) return;
          const name = this.profileName.trim(); const exists = Object.prototype.hasOwnProperty.call((catalog && catalog.profiles) || {}, name);
          const previous = exists ? catalog.profiles[name] : null;
          const clearing = previous?.native?.off?.length ? " This also clears its saved native off list." : "";
          const action = exists ? "Replace the saved profile named \"" + name + "\" with this suggestion?" + clearing : "Save the profile \"" + name + "\"?";
          if (!confirm(action)) return;
          if (request !== this.profileRequest || key !== this.profileInputKey() || this.page !== "ai-profile" || !unchanged() || !this.profileProposalValid) return;
          const saved = await post("/api/catalog/profiles", {
            name, description: this.profileDescription.trim(), skills: [...this.profileSkills],
            targets: [this.profileScope], native: {off: []}, expected_profile: previous,
          });
          if (request === this.profileRequest && key === this.profileInputKey() && this.page === "ai-profile") {
            this.note = (exists ? "Updated" : "Saved") + " profile \"" + name + "\". The suggestion did not apply any settings or change skill files.";
            this.$emit("changed", saved);
          }
        } catch (e) { if (request === this.profileRequest) this.error = (e && e.message) || String(e); }
        finally { this.profileSaving = false; }
      },
      draftBody(estimate) { return { scope: this.draftScope, brief: this.draftBrief.trim(), name: this.draftName.trim() || undefined, estimate }; },
      async estimateDraft() {
        if (!this.draftBrief.trim() || !this.draftScope) return;
        this.clearDraftProposal();
        const key = this.draftInputKey();
        const r = await this.guard(() => post("/api/ai/draft-skill", this.draftBody(true)));
        if (r && key === this.draftInputKey() && r.status === "estimate") { this.draftEstimate = r; this.draftEstimateKey = key; }
      },
      async runDraft() {
        if (!this.draftEstimateCurrent || !this.draftBrief.trim() || !this.draftScope) return;
        const key = this.draftInputKey();
        this.draftResult = null;
        const r = await this.guard(() => post("/api/ai/draft-skill", this.draftBody(false)));
        if (r && key === this.draftInputKey() && ["verified", "invalid", "unverified"].includes(r.status)) {
          this.draftResult = r; this.draftEstimate = null; this.draftEstimateKey = ""; this.loadRuns();
        }
      },
      useDraft() {
        if (!this.canUseDraft) return;
        const draft = this.draftResult.draft || {};
        if (!["name", "description", "body"].every((key) => typeof draft[key] === "string")) return;
        this.$emit("use-draft", {
          scope: this.draftResult.scope, name: draft.name, description: draft.description, body: draft.body,
          category: draft.category, version: draft.version, license: draft.license,
          compatibility: draft.compatibility, allowed_tools: draft.allowed_tools,
        });
      },
      stolenPromptText(prompt) {
        if (typeof prompt === "string") return prompt;
        if (!prompt || typeof prompt !== "object") return String(prompt == null ? "" : prompt);
        return typeof prompt.text === "string" ? prompt.text : JSON.stringify(prompt);
      },
      takeHandoff() {
        let t = null;
        try { t = JSON.parse(sessionStorage.getItem(HANDOFF) || "null"); sessionStorage.removeItem(HANDOFF); } catch (e) { t = null; }
        if (this.target && this.page === "ai-ask") {
          this.question = `Find skills related to ${this.target.name}. ${this.target.description || ''}`.slice(0, 500);
          this.askScope = "all";
        }
        if (this.target && this.page === "ai-port") {
          const target = this.target, scope = target.scope, name = target.name;
          this.scope = scope;
          this.$nextTick(() => {
            if (this.page === "ai-port" && this.target === target && this.scope === scope && target.scope === scope && target.name === name) this.portName = name;
          });
        }
        if (!t && this.target && this.page === "ai-improve") t = { scope: this.target.scope, name: this.target.name };
        if (t && t.scope) { this.scope = t.scope; this.$nextTick(() => { if (t.name) this.improveName = t.name; }); }
      },
      handoff(name) { try { sessionStorage.setItem(HANDOFF, JSON.stringify({ scope: this.scope, name })); } catch (e) { /* optional */ } location.hash = "#/tools/ai-improve"; },
      /* `busy` stays true until every overlapping request finishes: a single
       * boolean re-enabled the buttons (paid model calls) while another
       * request was still in flight. */
      begin() { this.inflight += 1; this.busy = true; this.error = ""; this.note = ""; },
      end() { this.inflight = Math.max(0, this.inflight - 1); if (!this.inflight) this.busy = false; },
      async guard(fn) {
        this.begin();
        try { return await fn(); } catch (e) { this.error = (e && e.message) || String(e); return null; } finally { this.end(); }
      },
      async load() {
        const s = await this.guard(() => api("/api/ai/settings"));
        if (!s) return;
        this.settings = s;
        this.form = { provider: s.provider || "", model: s.model || "", base_url: s.base_url || "", api_key: "", max_run_tokens: s.max_run_tokens, max_day_tokens: s.max_day_tokens };
        this.loadRuns();
      },
      pickProvider() {
        const p = this.provider; if (!p) return;
        this.form.base_url = p.default_base_url; this.form.model = (p.suggested_models || [])[0] || "";
      },
      async save() {
        const body = { provider: this.form.provider, model: this.form.model, max_run_tokens: Number(this.form.max_run_tokens), max_day_tokens: Number(this.form.max_day_tokens) };
        if (this.provider && (this.form.base_url || "") !== this.provider.default_base_url) body.base_url = this.form.base_url;
        if (this.form.provider === "custom") body.base_url = this.form.base_url;
        if (this.form.api_key) body.api_key = this.form.api_key;
        const s = await this.guard(() => post("/api/ai/settings", body));
        if (s) { this.settings = s; this.form.api_key = ""; this.note = "Saved."; this.connection = null; }
      },
      async clearKey() { const s = await this.guard(() => post("/api/ai/settings", { clear_key: true })); if (s) { this.settings = s; this.note = "Stored key removed."; } },
      async turnOff() { const s = await this.guard(() => post("/api/ai/settings", { provider: null })); if (s) { this.settings = s; this.load(); this.note = "AI features are off and the stored key is deleted."; } },
      async testConnection() {
        const r = await this.guard(() => post("/api/ai/test-connection", {}));
        if (!r) return;
        this.connection = r;
        /* Refresh the saved status only; reloading the form would wipe unsaved
         * edits, including a freshly typed API key. */
        const s = await this.guard(() => api("/api/ai/settings"));
        if (s) { this.settings = s; this.loadRuns(); }
      },
      async loadRuns() {
        const request = ++this.historyRequest;
        this.historyBusy = true; this.historyError = ""; this.pastRun = null;
        try { const r = await api("/api/ai/runs"); if (request === this.historyRequest) this.pastRuns = r.runs; }
        catch (e) { if (request === this.historyRequest) this.historyError = e.message || String(e); }
        finally { if (request === this.historyRequest) this.historyBusy = false; }
      },
      async openRun(id) {
        const request = ++this.historyRequest;
        this.historyBusy = true; this.historyError = ""; this.pastRun = null;
        try { const r = await api("/api/ai/runs/" + encodeURIComponent(id)); if (request === this.historyRequest) this.pastRun = r; }
        catch (e) { if (request === this.historyRequest) this.historyError = e.message || String(e); }
        finally { if (request === this.historyRequest) this.historyBusy = false; }
      },
      runText(run) { return JSON.stringify(run, null, 2); },
      async loadSaved() {
        const request = ++this.savedRequest; const scope = this.scope;
        this.savedPrompts = []; this.savedCount = 0; this.savedNote = ""; this.savedError = "";
        this.savedBusy = false;
        if (!scope) return;
        this.savedBusy = true;
        try { const r = await api("/api/ai/prompt-sets/" + encodeURIComponent(scope)); if (request === this.savedRequest) { this.savedPrompts = r.prompts; this.savedCount = r.prompts.length; } }
        catch (e) { if (request === this.savedRequest) this.savedError = e.message || String(e); }
        finally { if (request === this.savedRequest) this.savedBusy = false; }
      },
      async removePrompt(prompt) {
        if (this.savedBusy || !confirm("Remove this saved regression prompt?")) return;
        const scope = this.scope; const previous = this.savedPrompts;
        const request = ++this.savedRequest;
        let failure = "";
        this.savedBusy = true; this.savedError = ""; this.savedNote = "";
        const prompts = previous.filter((p) => p.text !== prompt.text || p.expected !== prompt.expected);
        try {
          const r = await post("/api/ai/prompt-sets", { scope, prompts, replace: true, expected_prompts: previous });
          if (request === this.savedRequest) { this.savedPrompts = r.prompts; this.savedCount = r.prompts.length; this.estimate = null; this.savedNote = "Prompt removed."; }
        } catch (e) {
          failure = e.message || String(e);
        } finally {
          if (request === this.savedRequest && failure) { await this.loadSaved(); if (scope === this.scope) this.savedError = failure; }
          else if (request === this.savedRequest) this.savedBusy = false;
          else if (scope === this.scope) await this.loadSaved();
        }
      },
      async saveTests() {
        if (this.savedBusy) return;
        ++this.savedRequest;
        const prompts = this.result.prompts.map((p) => ({ text: p.text, expected: p.expected }));
        const r = await this.guard(() => post("/api/ai/prompt-sets", { scope: this.result.scope, prompts }));
        if (r && r.scope === this.scope) { this.savedPrompts = r.prompts; this.savedCount = r.prompts.length; this.savedNote = "Saved. " + r.prompts.length + " regression prompts for this agent; re-run them after edits or a model change."; }
      },
      triggerBody(estimate) {
        const body = { scope: this.scope, repeats: Number(this.repeats), estimate };
        if (this.mode === "saved") body.saved = true;
        else if (this.mode === "generate") Object.assign(body, { generate_for: this.chosen, per_skill: Number(this.perSkill), near_misses: Number(this.nearMisses) });
        else body.prompts = this.parsedPrompts;
        return body;
      },
      async estimateTrigger() { this.result = null; this.estimate = await this.guard(() => post("/api/ai/trigger-test", this.triggerBody(true))); },
      async runTrigger() { const r = await this.guard(() => post("/api/ai/trigger-test", this.triggerBody(false))); if (r) { this.result = r; this.estimate = null; this.load(); } },
      improveBody(estimate) { return { scope: this.scope, name: this.improveName, candidates: Number(this.candidates), repeats: Number(this.repeats), estimate }; },
      async estimateImprove() { this.improve = null; this.applied = ""; this.improveEstimate = await this.guard(() => post("/api/ai/improve-description", this.improveBody(true))); },
      async runImprove() { const r = await this.guard(() => post("/api/ai/improve-description", this.improveBody(false))); if (r) { this.improve = r; this.improveEstimate = null; this.load(); } },
      async applyCandidate(c) {
        if (!confirm("Replace the description of " + this.improve.name + " in " + this.improve.scope + "? A snapshot of the current file is kept and you can restore it from Recovery.")) return;
        const ok = await this.guard(() => api("/api/skills/" + encodeURIComponent(this.improve.name) + "?scope=" + encodeURIComponent(this.improve.scope), { method: "PATCH", body: JSON.stringify({ description: c.description }) }));
        if (ok) { this.applied = c.description; this.note = "Description saved. The previous version is in Recovery → history."; this.$emit("changed"); }
      },
    },
    template: `
    <div class="ai-center">
      <p v-if="error" class="v2-tool-error" role="alert">{{ error }}</p>
      <p v-if="note" class="tp-fine" role="status">{{ note }}</p>
      <p v-if="busy" class="v2-tool-status" role="status"><span class="v2-dot" aria-hidden="true"></span>Working… model calls can take a minute.</p>

      <template v-if="page==='ai-settings'">
        <h1 class="h1" id="h1" tabindex="-1">AI settings</h1>
        <p class="lede">Connect your own model to test and improve how agents pick your skills. Off until you choose a provider.</p>
        <section class="card tp-panel" aria-labelledby="ai-conn-h">
          <header class="tp-panel-h"><h2 id="ai-conn-h">Model connection</h2>
            <span :class="['pill', configured ? 'ok' : 'off']">{{ configured ? 'Connected' : 'Off' }}</span></header>
          <div class="tp-set" v-if="settings">
            <div class="tp-set-row"><label for="ai-prov"><b>Provider</b><small>Anthropic, any OpenAI-compatible service, or a model running on this computer.</small></label>
              <select id="ai-prov" class="field" v-model="form.provider" @change="pickProvider()"><option value="">Choose…</option><option v-for="p in settings.providers" :key="p.id" :value="p.id">{{ p.label }}</option></select></div>
            <div class="tp-set-row" v-if="form.provider"><label for="ai-model"><b>Model</b><small>The exact model id your provider uses.</small></label>
              <span><input id="ai-model" class="field" v-model.trim="form.model" list="ai-models" autocomplete="off" spellcheck="false"><datalist id="ai-models"><option v-for="m in (provider && provider.suggested_models) || []" :key="m" :value="m"></option></datalist></span></div>
            <div class="tp-set-row" v-if="form.provider"><label for="ai-base"><b>Endpoint</b><small>Must be https, or http on this computer only.</small></label>
              <input id="ai-base" class="field tp-mono" v-model.trim="form.base_url" autocomplete="off" spellcheck="false"></div>
            <div class="tp-set-row" v-if="form.provider && (!provider || provider.needs_key || form.provider==='custom')"><label for="ai-key"><b>API key</b>
                <small v-if="settings.key_source==='settings' && settings.provider===form.provider">A key ending {{ settings.key_hint }} is stored. Leave blank to keep it.</small>
                <small v-else-if="settings.key_source && settings.key_source.startsWith('env:') && settings.provider===form.provider">Using {{ settings.key_source.slice(4) }} from the environment; it takes precedence.</small>
                <small v-else-if="provider && provider.env.length">Or set {{ provider.env.join(' / ') }} before starting the app, and leave this blank.</small></label>
              <input id="ai-key" class="field tp-mono" type="password" v-model="form.api_key" autocomplete="off" spellcheck="false" placeholder="Paste key"></div>
            <div class="tp-set-row"><label for="ai-run"><b>Cap per run</b><small>Input tokens one test may send. A run that would exceed it is refused before anything is sent.</small></label>
              <span class="ai-cap"><input id="ai-run" class="field num" type="number" min="1000" step="1000" v-model="form.max_run_tokens" aria-describedby="ai-run-v"><small id="ai-run-v" class="tp-fine">{{ fmt(form.max_run_tokens) }} tokens</small></span></div>
            <div class="tp-set-row"><label for="ai-day"><b>Cap per day</b><small>Today so far: {{ fmt(usage && usage.input_tokens) }} input tokens in {{ fmt(usage && usage.calls) }} calls.</small></label>
              <span class="ai-cap"><input id="ai-day" class="field num" type="number" min="1000" step="1000" v-model="form.max_day_tokens" aria-describedby="ai-day-v"><small id="ai-day-v" class="tp-fine">{{ fmt(form.max_day_tokens) }} tokens</small></span></div>
          </div>
          <div class="tp-acts"><button class="btn btn-ink" :disabled="busy || !form.provider || !form.model" @click="save()">Save</button>
            <button class="btn btn-line" :disabled="busy || !configured" @click="testConnection()">Test connection</button>
            <button class="btn btn-line" v-if="settings && settings.key_source==='settings'" :disabled="busy" @click="clearKey()">Remove stored key</button>
            <button class="btn btn-line" v-if="settings && settings.provider" :disabled="busy" @click="turnOff()">Turn AI off</button></div>
          <p v-if="connection" :class="['tp-fine']" role="status">{{ connection.ok ? 'Connection works' : 'The model answered, but not with the expected JSON; try a stronger model' }} · {{ connection.run.model }} · {{ fmt(connection.run.input_tokens) }} tokens in.</p>
        </section>
        <section class="card tp-panel" aria-labelledby="ai-priv-h">
          <h2 id="ai-priv-h">What leaves this computer</h2>
          <p class="ai-warn" role="note"><ic name="warn"></ic><span><b>This app has no login.</b> It relies on listening only on this computer, so any program you run can reach it and could spend this key up to your caps. Keep the caps low.</span></p>
          <ul class="tp-fine ai-list">
            <li>Nothing, until you run a test. Each test shows exactly what it will send and its token estimate first.</li>
            <li>The trigger test sends skill names, descriptions and test prompts. Improving a description also sends the start of that one skill's body.</li>
            <li>A local provider (Ollama, LM Studio) keeps everything on this computer.</li>
            <li>{{ settings ? settings.storage : '' }} It is never shown again, logged or exported.</li>
          </ul>
        </section>
      </template>

      <template v-else-if="!configured && settings && page !== 'ai-conflicts' && page !== 'ai-port' && page !== 'ai-explain'">
        <h1 class="h1" id="h1" tabindex="-1">{{ {'ai-concise':'Shorten a skill','ai-explain':'Explain risk findings','ai-port':'Porting notes','ai-ask':'Ask your library','ai-draft':'Draft a skill','ai-profile':'Suggest a profile','ai-trigger':'Trigger test','ai-improve':'Improve a description','ai-overlap':'Overlap check','ai-budget':'Fit the listing budget','ai-evals':'Does it help?','ai-ablate':'Does it earn its place?','ai-conflicts':'Contradiction check'}[page] || 'AI assist' }}</h1>
        <p class="lede">{{ toolLede(page) }}</p>
        <section class="card tp-panel ai-off" aria-labelledby="ai-off-h">
          <h2 id="ai-off-h">Connect a model to use this tool</h2>
          <ol class="ai-steps">
            <li><b>Connect a model</b><span>Your own Anthropic or OpenAI-compatible key, or a model running on this computer. Set spending caps at the same time.</span></li>
            <li><b>Check what would be sent</b><span>Every run first shows exactly what leaves this computer and its token estimate. Nothing is sent at this step.</span></li>
            <li><b>Send and review</b><span>Results are shown beside your own files; nothing is changed until you apply it.</span></li>
          </ol>
          <div class="tp-acts"><a class="btn btn-ink" href="#/tools/ai-settings">Open AI settings</a></div></section>
      </template>

      <template v-else-if="page==='ai-trigger'">
        <h1 class="h1" id="h1" tabindex="-1">Trigger test</h1>
        <p class="lede">Simulate which skill your configured model selects for a request, using an observed list of skill names and descriptions.</p>
        <p class="tp-fine ai-routing-note">{{routingNotice}}</p>
        <section class="card tp-panel" aria-labelledby="ai-tt-h">
          <h2 id="ai-tt-h">Set up</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-scope"><b>Agent</b><small>Whose skill list to test.</small></label>
              <select id="ai-scope" class="field" v-model="scope"><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }})</option></select></div>
            <div class="tp-set-row"><span><b>Test prompts</b><small>Let the model write realistic requests, or write your own.</small></span>
              <div class="seg" role="group" aria-label="Prompt source"><button type="button" :aria-pressed="mode==='generate'" @click="mode='generate'">Generate</button><button type="button" :aria-pressed="mode==='manual'" @click="mode='manual'">Write my own</button><button type="button" :aria-pressed="mode==='saved'" :disabled="!savedCount" @click="mode='saved'">Saved tests ({{ savedCount }})</button></div></div>
            <div class="tp-set-row"><label for="ai-rep"><b>Repeats</b><small>Answers vary; repeating shows how stable a choice is. The skill order is shuffled each time.</small></label>
              <select id="ai-rep" class="field" v-model.number="repeats"><option v-for="n in 5" :key="n" :value="n">{{ n }}</option></select></div>
          </div>
          <template v-if="mode==='generate'">
            <div class="ai-pick">
              <input class="field" v-model="filter" placeholder="Filter skills" aria-label="Filter skills">
              <p class="tp-fine">{{ chosen.length }} of at most 40 chosen. <button class="btn btn-line btn-sm" type="button" @click="chosen = pickable.slice(0, 40)">Choose shown</button> <button class="btn btn-line btn-sm" type="button" @click="chosen = []">Clear</button></p>
              <div class="ai-checks"><label v-for="n in pickable" :key="n"><input type="checkbox" :value="n" v-model="chosen" :disabled="!chosen.includes(n) && chosen.length>=40"> <span class="tp-mono">{{ n }}</span></label></div>
            </div>
            <div class="tp-set">
              <div class="tp-set-row"><label for="ai-per"><b>Prompts per skill</b></label><select id="ai-per" class="field" v-model.number="perSkill"><option v-for="n in 6" :key="n" :value="n">{{ n }}</option></select></div>
              <div class="tp-set-row"><label for="ai-nm"><b>Near-miss prompts</b><small>Requests that look related but should not load any chosen skill.</small></label><select id="ai-nm" class="field" v-model.number="nearMisses"><option v-for="n in [0,1,2,3,4,5,6,7,8,9,10]" :key="n" :value="n">{{ n }}</option></select></div>
            </div>
          </template>
          <p v-else-if="mode==='saved'" class="tp-fine">Re-runs the {{ savedCount }} saved prompts and compares each skill with the last saved-test run, so a description edit or a model change that breaks triggering shows up.</p>
          <template v-else>
            <label for="ai-prompts" class="tp-fine">One request per line. End a line with <code>=&gt; skill-name</code> for the skill it should load, or <code>=&gt; none</code>.</label>
            <textarea id="ai-prompts" class="field ai-text" v-model="promptText" rows="8" placeholder="fill in this tax form PDF => pdf-forms"></textarea>
          </template>
          <details class="tp-more">
            <summary>Saved regression prompts ({{ savedCount }})</summary>
            <p v-if="!savedPrompts.length && !savedBusy" class="tp-empty">No saved prompts for this agent.</p>
            <ul class="tp-rows"><li v-for="(p,i) in savedPrompts" :key="JSON.stringify([p.text,p.expected])" class="v2-tool-row">
              <span class="tp-row-main"><strong>{{ p.text }}</strong><small>Should load: {{ p.expected || 'none' }}</small></span>
              <button class="btn btn-line btn-sm" :disabled="busy || savedBusy" :aria-label="'Remove saved prompt ' + (i+1)" @click="removePrompt(p)">Remove</button>
            </li></ul>
            <button class="btn btn-line btn-sm" :disabled="busy || savedBusy" @click="loadSaved()">Refresh saved prompts</button>
          </details>
          <p v-if="savedBusy" class="tp-fine" role="status">Loading saved prompts…</p>
          <p v-if="savedError" class="v2-tool-error" role="alert">{{ savedError }}</p>
          <p v-if="savedNote" class="tp-fine" role="status">{{ savedNote }}</p>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !scope || (mode==='generate' ? !chosen.length : mode==='saved' ? !savedCount : !parsedPrompts.length)" @click="estimateTrigger()">Check what will be sent</button></div>
          <div v-if="estimate" class="ai-confirm" role="region" aria-label="Before sending">
            <p v-for="(line,i) in estimate.egress" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">At most about {{ fmt(estimate.run.estimated_input_tokens) }} tokens to {{ estimate.run.model }}<span v-if="estimate.over_cap.length">; {{ estimate.over_cap.length }} descriptions are longer than the agent's cap and are cut, as the agent would.</span></p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runTrigger()">Send and run test</button><button class="btn btn-line" :disabled="busy" @click="estimate=null">Cancel</button></div>
          </div>
        </section>

        <section v-if="result" class="card tp-panel" aria-labelledby="ai-res-h" aria-live="polite">
          <p class="tp-fine ai-routing-note">{{routingNotice}}</p>
          <header class="tp-panel-h"><div><h2 id="ai-res-h">Result</h2><p>{{ result.listed }} skills listed · {{ result.prompts.length }} prompts × {{ result.repeats }} · {{ result.run.model }}</p></div>
            <span :class="['pill', troubled.length ? 'warn' : 'ok']">{{ troubled.length ? troubled.length + ' need review' : 'All selected in simulation' }}</span></header>
          <div class="ai-stats"><div><b class="num">{{ pct(result.recall) }}</b><small>of prompts picked the right skill</small></div>
            <div v-if="result.false_trigger_rate!=null"><b class="num">{{ pct(result.false_trigger_rate) }}</b><small>of near-misses selected a skill in simulation</small></div>
            <div><b class="num">{{ fmt(result.run.input_tokens) }}</b><small>input tokens used<template v-if="result.run.cached_input_tokens">, {{ fmt(result.run.cached_input_tokens) }} read from the provider's cache</template><template v-if="result.run.retries"> · {{ fmt(result.run.retries) }} busy-provider {{ result.run.retries === 1 ? 'retry' : 'retries' }}</template></small></div></div>
          <div v-if="result.prompt_source==='saved'" class="ai-confirm">
            <p v-if="!result.compared_with" class="tp-fine">First saved-test run for this agent; the next one will be compared with it.</p>
            <p v-else-if="!result.changes.length" class="tp-fine">No skill changed since the last saved-test run.</p>
            <p v-for="c in result.changes" :key="c.name" class="tp-fine"><span :class="['pill', c.regressed ? 'bad' : 'ok']">{{ c.regressed ? 'Worse' : 'Better' }}</span> <span class="tp-mono">{{ c.name }}</span>: {{ pct(c.before) }} → {{ pct(c.after) }}</p>
          </div>
          <ul class="tp-rows">
            <li v-for="s in result.skills" :key="s.name" class="v2-tool-row">
              <span class="tp-row-main"><strong class="tp-mono">{{ s.name }}</strong><small>Won {{ pct(s.hit_rate) }} of its {{ s.prompts }} prompts<span v-if="s.lost_to.length">; lost to {{ s.lost_to.map(l => skillLabel(l.name) + ' ×' + l.count).join(', ') }}</span></small></span>
              <span class="ai-row-acts"><span :class="['pill', verdictTone(s.verdict)]">{{ verdictLabel(s.verdict) }}</span><button v-if="s.verdict!=='fires'" class="btn btn-line btn-sm" @click="handoff(s.name)">Improve</button></span>
            </li>
          </ul>
          <details class="tp-more"><summary>Every prompt and what was chosen</summary>
            <table class="ai-table"><thead><tr><th>Prompt</th><th>Should load</th><th>Chosen</th></tr></thead>
              <tbody><tr v-for="p in result.prompts" :key="p.id"><td>{{ p.text }}</td><td class="tp-mono">{{ p.expected || 'none' }}</td><td class="tp-mono">{{ choiceList(p.choices) }}</td></tr></tbody></table></details>
          <div class="tp-acts" v-if="result.prompt_source!=='saved'"><button class="btn btn-line btn-sm" :disabled="busy || savedBusy" @click="saveTests()">Save these prompts as regression tests</button></div>
          <p class="tp-fine">{{ result.run.advisory }} Invalid answers: {{ result.invalid_answers }}.</p>
        </section>
      </template>

      <template v-else-if="page==='ai-concise'">
        <h1 class="h1" id="h1" tabindex="-1">Shorten a skill</h1>
        <p class="lede">Ask for a shorter primary document. Any new reference files and the exact folder change go through the normal source-update review.</p>
        <section class="card tp-panel" aria-labelledby="ai-concise-form-h">
          <h2 id="ai-concise-form-h">Choose the exact skill copy</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-concise-scope"><b>Scope</b></label><select id="ai-concise-scope" class="field" v-model="conciseScope" :disabled="busy"><option value="">Choose…</option><option v-for="s in conciseScopes" :key="s.id" :value="s.id">{{s.label}}</option></select></div>
            <div class="tp-set-row"><label for="ai-concise-name"><b>Skill</b></label><select id="ai-concise-name" class="field" v-model="conciseName" :disabled="busy||!conciseScope"><option value="">Choose…</option><option v-for="n in conciseNames" :key="n" :value="n">{{n}}</option></select></div>
            <div class="tp-set-row"><label for="ai-concise-target"><b>Physical copy</b><small>Disabled copies are included. Choose a path when the same skill has multiple copies.</small></label><select id="ai-concise-target" class="field" v-model="conciseTargetKey" :disabled="busy||!conciseName"><option value="">Choose exact path…</option><option v-for="t in conciseRecords" :key="t.key" :value="t.key">{{t.path}}</option></select></div>
          </div>
          <p class="tp-fine">The selected skill document is sent to your configured model. The token comparison covers the primary document plus newly added references; it does not establish semantic equivalence.</p>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy||!conciseTarget" @click="estimateConcise()">Check what will be sent</button></div>
          <div v-if="conciseEstimateCurrent" class="ai-confirm" role="region" aria-label="Before sending the concise request">
            <p v-for="(line,i) in conciseEstimate.egress||[]" :key="i" class="tp-fine">{{line}}</p>
            <p class="tp-fine">About {{fmt(conciseEstimate.run&&conciseEstimate.run.estimated_input_tokens)}} input tokens to {{conciseEstimate.run&&conciseEstimate.run.model}}. No proposal has been generated yet.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy||!conciseEstimateCurrent" @click="runConcise()">Send and prepare proposal</button><button class="btn btn-line" :disabled="busy" @click="clearConciseProposal()">Cancel</button></div>
          </div>
        </section>
        <section v-if="conciseResult" class="card tp-panel" aria-live="polite" aria-labelledby="ai-concise-result-h">
          <header class="tp-panel-h"><div><h2 id="ai-concise-result-h">Conciseness proposal</h2><p>{{conciseResult.name}} · {{conciseResult.scope}} · {{conciseResult.run&&conciseResult.run.model}}</p></div><span :class="['pill',conciseResult.status==='review-required'?'warn':conciseResult.status==='no-change'?'off':'bad']">{{conciseResult.status==='review-required'?'Review required':conciseResult.status==='no-change'?'No change':'Blocked'}}</span></header>
          <div v-if="conciseResult.tokens" class="ai-stats"><div><b class="num">{{fmt(conciseResult.tokens.primary_before)}} → {{fmt(conciseResult.tokens.primary_after)}}</b><small>primary document tokens</small></div><div><b class="num">{{fmt(conciseResult.tokens.reference_added)}}</b><small>new reference tokens</small></div><div><b class="num">{{fmt(conciseResult.tokens.total_before)}} → {{fmt(conciseResult.tokens.total_after)}}</b><small>primary + new references</small></div></div>
          <p v-if="conciseResult.tokens&&conciseResult.tokens.primary_saved!=null" class="tp-fine">Primary document change: {{conciseResult.tokens.primary_saved>0?conciseResult.tokens.primary_saved+' tokens saved':conciseResult.tokens.primary_saved<0?Math.abs(conciseResult.tokens.primary_saved)+' tokens added':'no token change'}}. Overall: {{conciseResult.tokens.total_saved>0?conciseResult.tokens.total_saved+' tokens saved':conciseResult.tokens.total_saved<0?Math.abs(conciseResult.tokens.total_saved)+' tokens added':'no token savings'}} across the primary document and new references.</p>
          <p v-if="conciseResult.tokens&&conciseResult.tokens.total_saved<=0" class="tp-issue warn">This proposal does not reduce the combined token count.</p>
          <p v-if="conciseResult.tokens" class="tp-fine">{{conciseResult.tokens.method}}</p>
          <h3>Sections</h3><div v-if="(conciseResult.sections||[]).length" class="tp-rows"><div v-for="(s,i) in conciseResult.sections" :key="i" class="v2-tool-row"><span class="tp-row-main"><strong>{{s.heading}}</strong><small>Body line {{s.line}} · {{fmt(s.tokens)}} tokens</small></span></div></div><p v-else class="tp-empty">No section counts returned.</p>
          <section v-if="conciseResult.proposal" aria-label="Proposed text"><h3>Proposed SKILL.md body</h3><pre class="ai-run-text tp-mono">{{conciseResult.proposal.body||''}}</pre>
            <template v-if="(conciseResult.proposal.references||[]).length"><h3>New references</h3><details v-for="(ref,i) in conciseResult.proposal.references" :key="i" class="tp-more"><summary>{{ref.path}} · {{fmt(ref.tokens)}} tokens</summary><pre class="ai-run-text tp-mono">{{ref.text||''}}</pre></details></template>
          </section>
          <p v-if="conciseResult.status==='blocked'" class="tp-issue bad">The proposal is blocked by validation. Review the source and try again.</p><p v-else-if="conciseResult.status==='no-change'" class="tp-fine">The proposal produced no file changes.</p>
          <p v-if="conciseResult.run&&conciseResult.run.advisory" class="tp-fine">{{conciseResult.run.advisory}}</p>
          <div class="tp-acts"><button class="btn btn-ink" :disabled="busy||!canOpenConciseReview" @click="openConciseReview()">Open source-update review</button><span v-if="canOpenConciseReview" class="tp-fine">Nothing is applied here. Inspect the exact diff and approve it in Source update.</span></div>
        </section>
      </template>

      <template v-else-if="page==='ai-draft'">
        <h1 class="h1" id="h1" tabindex="-1">Draft a skill</h1>
        <p class="lede">Describe a task or workflow. The draft is checked and tested against the selected scope before it can fill the New skill form.</p>
        <section class="card tp-panel" aria-labelledby="ai-draft-h">
          <h2 id="ai-draft-h">Describe the skill</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-draft-scope"><b>Test against</b><small>Choose where this skill would be used. Empty writable scopes are included.</small></label>
              <select id="ai-draft-scope" class="field" v-model="draftScope" :disabled="busy"><option v-for="s in draftScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }} skills)</option></select></div>
            <div class="tp-set-row"><label for="ai-draft-name"><b>Skill name</b><small>Optional. Leave blank to let the model suggest one.</small></label><input id="ai-draft-name" class="field" v-model.trim="draftName" maxlength="64" autocomplete="off" spellcheck="false" :disabled="busy"></div>
          </div>
          <label class="tp-field" for="ai-draft-brief">What should the skill help an agent do?</label>
          <textarea id="ai-draft-brief" class="field ai-text" v-model="draftBrief" rows="7" maxlength="10000" placeholder="Describe the task, when the agent should use this skill, and any steps or constraints to follow." :disabled="busy"></textarea>
          <p class="tp-fine">The brief goes to your configured model. The app then validates the draft and checks its trigger against generated requests and near-misses.</p>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !draftScope || !draftBrief.trim()" @click="estimateDraft()">Check what will be sent</button></div>
          <div v-if="draftEstimateCurrent" class="ai-confirm" role="region" aria-label="Before sending the draft request">
            <p v-for="(line,i) in draftEstimate.egress || []" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">About {{ fmt(draftEstimate.run && draftEstimate.run.estimated_input_tokens) }} input tokens to {{ draftEstimate.run && draftEstimate.run.model }}. No draft has been generated yet.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runDraft()">Send and verify draft</button><button class="btn btn-line" :disabled="busy" @click="clearDraftProposal()">Cancel</button></div>
          </div>
        </section>
        <section v-if="draftResult" class="card tp-panel" aria-labelledby="ai-draft-result-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-draft-result-h">Draft result</h2><p>{{ draftResult.scope }} · {{ draftResult.run && draftResult.run.model }}</p></div>
            <span :class="['pill', draftResult.status === 'verified' && draftResult.validation && draftResult.validation.valid === true ? 'ok' : 'warn']">{{ draftResult.status === 'verified' ? 'Verified' : draftResult.status === 'unverified' ? 'Not verified' : 'Needs work' }}</span></header>
          <div v-if="draftResult.draft" class="ai-cand">
            <h3>{{ draftResult.draft.name || 'Unnamed draft' }}</h3>
            <p>{{ draftResult.draft.description }}</p>
            <details class="tp-more"><summary>Full SKILL.md draft</summary><pre class="ai-run-text tp-mono">{{ draftResult.draft.text || draftResult.draft.body || '' }}</pre></details>
          </div>
          <p v-else class="tp-fine">The model did not return a usable draft.</p>
          <section aria-labelledby="ai-draft-validation-h"><h3 id="ai-draft-validation-h">Validation</h3>
            <p v-if="draftResult.validation && draftResult.validation.valid" class="tp-fine">The draft passed document validation.</p>
            <p v-for="(issue,i) in (draftResult.validation && draftResult.validation.issues) || []" :key="i" :class="['tp-issue', issue.level === 'error' ? 'bad' : 'warn']">{{ issue.level || 'Issue' }} · {{ issue.key || 'draft' }}: {{ issue.message }}</p>
            <p v-if="draftResult.validation && !draftResult.validation.valid && !(draftResult.validation.issues || []).length" class="tp-issue bad">The draft did not pass validation; no issue details were returned.</p>
          </section>
          <section v-if="draftResult.verification" aria-labelledby="ai-draft-verification-h"><h3 id="ai-draft-verification-h">Trigger check</h3>
            <div class="ai-stats"><div><b class="num">{{ pct(draftResult.verification.draft_hit_rate) }}</b><small>generated requests that picked this draft</small></div>
              <div><b class="num">{{ pct(draftResult.verification.near_miss_false_trigger_rate) }}</b><small>near-misses that picked it</small></div>
              <div><b class="num">{{ fmt(draftResult.verification.existing_skills_sampled) }} / {{ fmt(draftResult.verification.existing_skills_total) }}</b><small>existing skills sampled / total</small></div></div>
            <p class="tp-fine">Missing answers: {{ fmt(draftResult.verification.missing_answers) }} · Invalid answers: {{ fmt(draftResult.verification.invalid_answers) }}</p>
            <h4>Existing skills whose requests the draft also won</h4>
            <p v-if="!(draftResult.verification.stolen || []).length" class="tp-empty">No stolen prompts were reported.</p>
            <ul v-else class="tp-rows"><li v-for="s in draftResult.verification.stolen" :key="s.name" class="v2-tool-row"><span class="tp-row-main"><strong class="tp-mono">{{ s.name }}</strong><small>{{ fmt(s.count) }} prompt(s)</small>
              <small v-for="(p,i) in (s.prompts || [])" :key="i">{{ stolenPromptText(p) }}</small></span></li></ul>
          </section>
          <p v-if="draftResult.run && draftResult.run.advisory" class="tp-fine">{{ draftResult.run.advisory }}</p>
          <div class="tp-acts"><button class="btn btn-ink" :disabled="busy || !canUseDraft" @click="useDraft()">Use this draft in New skill</button>
            <span v-if="!canUseDraft" class="tp-fine">This draft must pass validation and trigger checks before it can be used.</span></div>
        </section>
      </template>

      <template v-else-if="page==='ai-explain'">
        <h1 class="h1" id="h1" tabindex="-1">Explain risk findings</h1>
        <p class="lede">The pattern scanner runs first, without AI, over one installed skill. Your model then gives a second opinion on each finding. An opinion is shown beside its finding and never changes its severity; calling something a false positive needs a quote from the file.</p>
        <section class="card tp-panel" aria-labelledby="ai-ex-h">
          <h2 id="ai-ex-h">Choose a skill</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-scope6"><b>Agent</b></label><select id="ai-scope6" class="field" v-model="scope"><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }})</option></select></div>
            <div class="tp-set-row"><label for="ai-exn"><b>Skill</b></label><select id="ai-exn" class="field" v-model="explainName"><option value="">Choose…</option><option v-for="n in scopeSkills" :key="n" :value="n">{{ n }}</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !explainName" @click="explain('local')">Scan</button></div>
        </section>
        <section v-if="explained" class="card tp-panel" aria-labelledby="ai-exr-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-exr-h">{{ explained.name }}</h2><p>{{ explained.policy }}</p></div>
            <span :class="['pill', explained.clean ? 'ok' : 'warn']">{{ explained.clean ? 'No findings' : explained.findings_total + ' finding(s)' }}</span></header>
          <ul v-if="explained.findings.length" class="tp-rows"><li v-for="(f, i) in explained.findings" :key="i" class="v2-tool-row"><span class="tp-row-main">
            <strong>{{ f.severity }} · {{ f.kind }}: {{ f.why }}</strong><small class="tp-mono">{{ f.evidence }}</small>
            <small v-if="opinionFor(i)"><span :class="['pill', opinionLabel(opinionFor(i).opinion)[0]]">{{ opinionLabel(opinionFor(i).opinion)[1] }}</span> {{ opinionFor(i).why }}<template v-if="opinionFor(i).quote"> · quotes <span class="tp-mono">{{ opinionFor(i).file }}</span>: “{{ opinionFor(i).quote }}”</template></small></span></li></ul>
          <p v-if="explained.findings_total > explained.findings_shown" class="tp-fine">Showing the first {{ explained.findings_shown }} of {{ explained.findings_total }} findings.</p>
          <template v-if="!explained.clean && !explained.opinions">
            <p v-if="!configured" class="tp-fine">For an optional second opinion, <a href="#/tools/ai-settings">connect a model</a>.</p>
            <div v-else-if="!explainEstimate" class="tp-acts"><button class="btn btn-line" :disabled="busy" @click="explain('estimate')">Preview AI request</button></div>
            <template v-else><p v-for="(line,i) in (explainEstimate.egress||[])" :key="i" class="tp-fine">{{ line }} About {{ fmt(explainEstimate.run.estimated_input_tokens) }} tokens to {{ explainEstimate.run.model }} at <code>{{ explainEstimate.destination }}</code>.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="explain('send')">Send for a second opinion</button></div></template>
          </template>
          <p v-if="explained.uncited_demoted" class="tp-fine">{{ explained.uncited_demoted }} false-positive claim(s) without a matching quote were shown as “no clear opinion”.</p>
          <p v-if="explained.dropped_opinions" class="tp-fine">{{ explained.dropped_opinions }} opinion(s) about findings that do not exist were dropped.</p>
        </section>
      </template>

      <template v-else-if="page==='ai-port'">
        <h1 class="h1" id="h1" tabindex="-1">Porting notes</h1>
        <p class="lede">Before copying a skill to another agent: which of its settings that agent does not document, and which parts of its text assume a particular agent. The facts are found without AI; your model only explains them.</p>
        <section class="card tp-panel" aria-labelledby="ai-po-h">
          <h2 id="ai-po-h">Choose a skill and a target</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-scope5"><b>From</b></label><select id="ai-scope5" class="field" v-model="scope"><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }})</option></select></div>
            <div class="tp-set-row"><label for="ai-pon"><b>Skill</b></label><select id="ai-pon" class="field" v-model="portName"><option value="">Choose…</option><option v-for="n in scopeSkills" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-pot"><b>Target agent</b><small>Agents whose documented frontmatter keys are recorded.</small></label><select id="ai-pot" class="field" v-model="portTarget"><option v-for="c in (settings && settings.consumers) || []" :key="c.id" :value="c.id">{{ c.label }}</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !portName" @click="port('local')">Find the facts</button></div>
        </section>
        <section v-if="ported" class="card tp-panel" aria-labelledby="ai-por-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-por-h">{{ ported.name }} → {{ ported.target_label }}</h2><p v-if="ported.source">Key list from <span class="tp-mono">{{ ported.source }}</span></p></div>
            <span :class="['pill', ported.portable ? 'ok' : 'warn']">{{ ported.portable ? 'Nothing agent-specific found' : ported.facts.length + ' thing(s) to check' }}</span></header>
          <ul v-if="ported.facts.length" class="tp-rows"><li v-for="f in ported.facts" :key="f.id" class="v2-tool-row"><span class="tp-row-main"><strong>{{ f.kind==='frontmatter' ? 'Setting' : 'Text' }}: {{ f.detail }}</strong><small v-if="f.line" class="tp-mono">{{ f.line }}</small>
            <small v-for="n in (ported.notes||[]).filter(n => n.fact===f.id)" :key="n.fact + n.suggestion">{{ n.explanation }} <b>Suggestion:</b> {{ n.suggestion }}</small></span></li></ul>
          <template v-if="!ported.portable && !ported.notes">
            <p v-if="!configured" class="tp-fine">For optional explanations, <a href="#/tools/ai-settings">connect a model</a>.</p>
            <div v-else-if="!portEstimate" class="tp-acts"><button class="btn btn-line" :disabled="busy" @click="port('estimate')">Preview AI request</button></div>
            <template v-else><p v-for="(line,i) in (portEstimate.egress||[])" :key="i" class="tp-fine">{{ line }} About {{ fmt(portEstimate.run.estimated_input_tokens) }} tokens to {{ portEstimate.run.model }} at <code>{{ portEstimate.destination }}</code>.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="port('send')">Send and explain</button></div></template>
          </template>
          <p v-if="ported.summary" class="tp-fine">{{ ported.summary }}</p>
          <p v-if="ported.dropped_notes" class="tp-fine">{{ ported.dropped_notes }} note(s) about things not in the facts were dropped.</p>
        </section>
      </template>

      <template v-else-if="page==='ai-ask'">
        <h1 class="h1" id="h1" tabindex="-1">Ask your library</h1>
        <p class="lede">Describe a task in your own words and get the skills that fit it. Every suggested skill is checked against your real library.</p>
        <section class="card tp-panel" aria-labelledby="ai-ask-h">
          <h2 id="ai-ask-h" class="sr-only">Question</h2>
          <form class="tp-stack" @submit.prevent="ask(true)">
            <label for="ai-q" class="tp-fine">Question</label>
            <input id="ai-q" class="field" v-model="question" maxlength="500" placeholder="Which skill helps me write release notes?" autocomplete="off">
            <div class="tp-set"><div class="tp-set-row"><label for="ai-asks"><b>Search</b></label><select id="ai-asks" class="field" v-model="askScope"><option value="all">All agents</option><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }}</option></select></div></div>
            <p class="tp-fine">Sends your question with skill names and the first 300 characters of each description; never skill bodies. At most 300 skills, narrowed by matching words first.</p>
            <div class="tp-acts"><button class="btn btn-ink" type="submit" :disabled="busy || !question.trim()">Preview AI request</button></div>
          </form>
          <div class="ai-confirm" v-if="askEstimate && askKey === askInputKey() && !asked">
            <p>{{ askEstimate.egress[0] }}</p>
            <details class="tp-more"><summary>Skill shortlist</summary><p>{{ askEstimate.shortlist.join(', ') }}</p></details>
            <button type="button" class="btn btn-ink" :disabled="busy" @click="ask(false)">Ask with this shortlist</button>
          </div>
        </section>
        <section v-if="asked && askKey === askInputKey()" class="card tp-panel" aria-labelledby="ai-ans-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-ans-h">Answer</h2><p>Searched {{ asked.searched }} skills, sent {{ asked.sent }} · {{ asked.run.model }}</p></div></header>
          <p>{{ asked.answer }}</p>
          <p v-if="!asked.matches.length" class="tp-empty">No match suggested from the shortlist. <a class="tp-link" href="#/tools/install">Browse the registry</a></p>
          <ul class="tp-rows"><li v-for="m in asked.matches" :key="m.name" class="v2-tool-row">
            <span class="tp-row-main"><strong class="tp-mono">{{ m.name }}</strong><small>{{ m.why }}</small>
              <button v-for="copy in matchingCopies(m)" :key="copy.scope + ':' + (copy.physical_path || copy.path)" type="button" class="btn btn-line btn-sm" @click="$emit('open-record', copy)" :title="copy.physical_path || copy.path">Open {{ copy.scope }} copy</button></span></li></ul>
          <p v-if="asked.dropped_unknown" class="tp-fine">{{ asked.dropped_unknown }} suggestion(s) were dropped because no such skill exists.</p>
        </section>
      </template>

      <template v-else-if="page==='ai-profile'">
        <h1 class="h1" id="h1" tabindex="-1">Suggest a profile</h1>
        <p class="lede">Use repository structure to suggest a named set of existing skills. You can edit it before saving; this does not apply settings or change any skills.</p>
        <section class="card tp-panel" aria-labelledby="ai-profile-setup-h">
          <h2 id="ai-profile-setup-h">Choose project and scope</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-profile-project"><b>Project folder</b><small>Must be inside a managed project root. Only file extensions, known manifest names, and top-level directory names are summarized; project file contents and absolute paths are not sent to the model.</small></label><input id="ai-profile-project" class="field tp-mono" v-model.trim="profileProject" placeholder="/path/to/project" autocomplete="off" spellcheck="false" :disabled="busy||profileSaving"></div>
            <div class="tp-set-row"><label for="ai-profile-scope"><b>Skill scope</b><small>The proposed profile will target only this writable scope. Empty scopes are included.</small></label><select id="ai-profile-scope" class="field" v-model="profileScope" :disabled="busy||profileSaving"><option value="">Choose…</option><option v-for="s in profileScopes" :key="s.id" :value="s.id">{{s.label}}</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy||profileSaving||!profileProject.trim()||!profileScope" @click="estimateProfile()">Check what will be sent</button></div>
          <div v-if="profileEstimateCurrent" class="ai-confirm" role="region" aria-label="Before sending the profile request">
            <p v-for="(line,i) in profileEstimate.egress||[]" :key="i" class="tp-fine">{{line}}</p>
            <p class="tp-fine">Project path is used locally for a contained metadata scan. The model receives project signal names and counts plus skill names and descriptions from the selected scope, not project file contents or absolute paths.</p>
            <p class="tp-fine">About {{fmt(profileEstimate.run&&profileEstimate.run.estimated_input_tokens)}} input tokens to {{profileEstimate.run&&profileEstimate.run.model}}. No profile has been suggested yet.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy||!profileEstimateCurrent" @click="runProfileSuggestion()">Send and suggest profile</button><button class="btn btn-line" :disabled="busy" @click="clearProfileSuggestion()">Cancel</button></div>
          </div>
        </section>
        <section v-if="profileResult" class="card tp-panel" aria-live="polite" aria-labelledby="ai-profile-result-h">
          <header class="tp-panel-h"><div><h2 id="ai-profile-result-h">Profile suggestion</h2><p>{{profileScope}}<span v-if="profileResult.run"> · {{profileResult.run.model}}</span></p></div><span :class="['pill',profileResult.status==='suggested'?'ok':profileResult.status==='empty'?'off':'warn']">{{profileResult.status==='suggested'?'Suggested':profileResult.status==='empty'?'No skills found':'Estimate'}}</span></header>
          <section v-if="profileResult.signals" aria-label="Project metadata signals">
            <h3>Project signals</h3><p class="tp-fine">{{fmt(profileResult.signals.entries_scanned)}} entries scanned<span v-if="profileResult.signals.truncated"> · scan was truncated</span></p>
            <p class="tp-fine"><b>File extensions:</b> <template v-if="(profileResult.signals.extensions||[]).length"><span v-for="(entry,i) in profileResult.signals.extensions" :key="i">{{entry.extension||'(no extension)'}} ({{fmt(entry.count)}}){{i+1<(profileResult.signals.extensions||[]).length?', ':''}}</span></template><span v-else>none found</span></p>
            <p class="tp-fine"><b>Manifest names:</b> {{(profileResult.signals.manifests||[]).join(', ')||'none found'}}</p>
            <p class="tp-fine"><b>Top-level folders:</b> {{(profileResult.signals.top_level_dirs||[]).join(', ')||'none found'}}</p>
          </section>
          <p v-if="profileResult.status==='empty'" class="tp-empty">No existing skills were available in this scope, so the model was not asked to invent a profile.</p>
          <template v-if="profileResult.status==='suggested'&&profileResult.profile">
            <p class="tp-fine">{{profileDroppedCount}} unknown skill name(s) were dropped. Only existing skill names are included below.</p>
            <label class="tp-field" for="ai-profile-name">Profile name <input id="ai-profile-name" class="field" v-model.trim="profileName" maxlength="64" autocomplete="off" :disabled="profileSaving"></label>
            <label class="tp-field" for="ai-profile-description">Description <textarea id="ai-profile-description" class="field ai-text" v-model="profileDescription" maxlength="500" rows="3" :disabled="profileSaving"></textarea><small>{{profileDescription.length}} / 500 characters</small></label>
            <fieldset class="tp-pick"><legend>Verified existing skills <span class="tp-count">{{profileSkills.length}} selected</span></legend>
              <div class="tp-pick-list"><label v-for="name in (profileResult.profile.skills||[])" :key="name" class="tp-check"><input type="checkbox" :checked="profileSkills.includes(name)" :disabled="profileSaving" @change="toggleProfileSuggestionSkill(name,$event.target.checked)"><span class="tp-mono">{{name}}</span><small v-if="records.filter(r=>r.scope===profileScope&&r.name===name).every(r=>r.disabled)"> · disabled copy</small></label><p v-if="!(profileResult.profile.skills||[]).length" class="tp-empty">No verified existing skills were suggested.</p></div>
            </fieldset>
            <p v-if="!profileNameValid" class="tp-issue bad">Use 1–64 letters, digits, periods, underscores or hyphens; the first character must be a letter or digit.</p>
            <p v-if="profileDescription.length>500" class="tp-issue bad">Description is too long.</p>
            <p v-if="!profileSkills.length" class="tp-issue warn">Select at least one verified skill before saving.</p>
            <p v-if="profileResult.run&&profileResult.run.advisory" class="tp-fine">{{profileResult.run.advisory}}</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy||profileSaving||!profileProposalValid" @click="saveSuggestedProfile()">Save profile…</button><span class="tp-fine">Saving asks for confirmation. Existing profiles with the same name require a separate overwrite confirmation.</span></div>
          </template>
        </section>
      </template>

      <template v-else-if="page==='ai-evals'">
        <h1 class="h1" id="h1" tabindex="-1">Does it help?</h1>
        <p class="lede">Runs a skill's own <code>evals/evals.json</code> cases through your model twice, with and without the skill, and grades both with the cases' own assertions. Results are saved in the skill's eval workspace.</p>
        <section class="card tp-panel" aria-labelledby="ai-ev-h">
          <h2 id="ai-ev-h">Choose a skill</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-evn"><b>Skill</b><small>Skills in your library. Add cases in <code>evals/evals.json</code> inside the skill's folder first.</small></label><select id="ai-evn" class="field" v-model="evalName"><option value="">Choose…</option><option v-for="n in librarySkills()" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-evm"><b>Cases</b><small>At most this many, in file order.</small></label><select id="ai-evm" class="field" v-model.number="evalMax"><option v-for="n in [1,3,5,10,15,20]" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-evt"><b>Repeats</b><small>Model answers vary. Repeats show whether a difference holds up; each repeat is saved as its own iteration.</small></label><select id="ai-evt" class="field" v-model.number="evalTrials" @change="evalEstimate=null"><option :value="1">Once</option><option :value="3">3 times</option><option :value="5">5 times</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !evalName" @click="estimateEvals()">Check what will be sent</button></div>
          <div v-if="evalEstimate" class="ai-confirm" role="region" aria-label="Before sending">
            <p v-for="(line,i) in evalEstimate.egress" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">At most about {{ fmt(evalEstimate.run.estimated_input_tokens) }} tokens to {{ evalEstimate.run.model }}.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runEvals()">Send and run</button><button class="btn btn-line" :disabled="busy" @click="evalEstimate=null">Cancel</button></div>
          </div>
        </section>
        <section v-if="evalResult" class="card tp-panel" aria-labelledby="ai-evr-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-evr-h">{{ evalResult.name }} · {{ (evalResult.iterations || [evalResult.iteration]).length > 1 ? 'iterations ' + evalResult.iterations[0] + '–' + evalResult.iterations[evalResult.iterations.length - 1] : 'iteration ' + evalResult.iteration }}</h2><p>{{ evalResult.cases }} cases · {{ evalResult.run.model }} · {{ fmt(evalResult.run.input_tokens) }} input tokens</p></div>
            <span v-if="(evalResult.trials || 1) === 1" :class="['pill', evalVerdict(evalResult.verdict)[0]]">{{ evalVerdict(evalResult.verdict)[1] }}</span></header>
          <trial-stats v-if="evalResult.statistics" :stats="evalResult.statistics" title="With the skill compared with without it, across every repeat" :labels="{ with_skill: 'With the skill', without_skill: 'Without it' }"></trial-stats>
          <p v-if="(evalResult.trials || 1) > 1" class="tp-fine">The figures and table below show the first repeat.</p>
          <div class="ai-stats">
            <div><b class="num">{{ pct((evalResult.benchmark.variants.with_skill||{}).pass_rate) }}</b><small>cases passed with the skill</small></div>
            <div><b class="num">{{ pct((evalResult.benchmark.variants.without_skill||{}).pass_rate) }}</b><small>without it</small></div>
          </div>
          <table class="ai-table"><thead><tr><th>Case</th><th>With skill</th><th>Without</th></tr></thead>
            <tbody><tr v-for="c in [...new Set(evalResult.results.map(r => r.case))]" :key="c"><td class="tp-mono">{{ c }}</td>
              <td v-for="v in ['with_skill','without_skill']" :key="v">{{ (r => !r ? '–' : !r.graded ? 'Not graded' : r.passed + ' / ' + r.total + ' assertions')(evalResult.results.find(r => r.case===c && r.variant===v)) }}</td></tr></tbody></table>
          <p class="tp-fine">Graded only by the assertions in evals.json; ungraded cases: {{ evalResult.benchmark.ungraded_cases }}. {{ evalResult.run.advisory }}</p>
        </section>
      </template>

      <template v-else-if="page==='ai-ablate'">
        <h1 class="h1" id="h1" tabindex="-1">Does it earn its place?</h1>
        <p class="lede">Runs a skill's own <code>evals/evals.json</code> cases with the whole skill and without one section, or without the skill at all. If results are not worse without it, removal is proposed: ties go to removal. Nothing changes until you review and save.</p>
        <section class="card tp-panel" aria-labelledby="ai-ab-h">
          <h2 id="ai-ab-h">Choose what to test</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-abn"><b>Skill</b><small>A turned-on skill in your library with cases in <code>evals/evals.json</code>.</small></label><select id="ai-abn" class="field" v-model="ablateName" @change="chooseAblateSkill()"><option value="">Choose…</option><option v-for="n in librarySkills()" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-abs"><b>Remove</b><small>A section includes its subsections.</small></label><select id="ai-abs" class="field" v-model="ablateSection" @change="clearAblate()" :disabled="!ablateName"><option value="">The whole skill</option><option v-for="sec in ablateSections" :key="sec.index" :value="String(sec.index)">{{ '#'.repeat(sec.level) }} {{ sec.heading }} (~{{ fmt(sec.tokens) }} tokens)</option></select></div>
            <div class="tp-set-row"><label for="ai-abm"><b>Cases</b><small>At least 3 graded cases are needed for a decision.</small></label><select id="ai-abm" class="field" v-model.number="ablateMax" @change="clearAblate()"><option v-for="n in [3,5,10,15,20]" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-abp"><b>Same-length filler</b><small>Also run with neutral filler of the same length in its place, to tell "this text matters" from "any text this long matters". Adds a third of the calls.</small></label><input id="ai-abp" type="checkbox" v-model="ablatePlacebo" @change="clearAblate()"></div>
            <div class="tp-set-row"><label for="ai-abt"><b>Repeats</b><small>Model answers vary; repeats narrow the range.</small></label><select id="ai-abt" class="field" v-model.number="ablateTrials" @change="clearAblate()"><option :value="1">Once</option><option :value="3">3 times</option><option :value="5">5 times</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !ablateName" @click="estimateAblate()">Check what will be sent</button></div>
          <div v-if="ablateEstimate" class="ai-confirm" role="region" aria-label="Before sending">
            <p v-for="(line,i) in ablateEstimate.egress" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">{{ ablateEstimate.calls_planned }} model calls, at most about {{ fmt(ablateEstimate.run.estimated_input_tokens) }} tokens to {{ ablateEstimate.run.model }}. Removing it would save about {{ fmt(ablateEstimate.saves_tokens) }} tokens.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runAblate()">Send and run</button><button class="btn btn-line" :disabled="busy" @click="clearAblate()">Cancel</button></div>
          </div>
        </section>
        <section v-if="ablateResult" class="card tp-panel" aria-labelledby="ai-abr-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-abr-h">{{ ablateResult.name }} · {{ ablateResult.section ? ablateResult.section.heading : 'whole skill' }}</h2><p>{{ ablateResult.cases_count }} cases × {{ ablateResult.trials }} · {{ ablateResult.run.model }}<template v-if="ablateResult.status==='partial'"> · some answers missing</template></p></div>
            <span :class="['pill', ablateDecision(ablateResult.decision)[0]]">{{ ablateDecision(ablateResult.decision)[1] }}</span></header>
          <p class="tp-fine">{{ ablateResult.reason }}.</p>
          <p v-if="ablateResult.previous" :class="ablateResult.previous.same_model && ablateResult.previous.same_revision ? 'tp-fine' : 'tp-issue warn'">Last time: {{ ablateDecision(ablateResult.previous.decision)[1] }} with {{ ablateResult.previous.model }}<template v-if="!ablateResult.previous.same_model"> (a different model; skill effects often differ between models)</template><template v-if="!ablateResult.previous.same_revision"> on an earlier version of the skill</template>.</p>
          <p v-if="ablateResult.coverage_warning" class="tp-issue warn">{{ ablateResult.coverage_warning }}</p>
          <trial-stats v-if="ablateResult.statistics" :stats="ablateResult.statistics" title="With it compared with without it" :labels="{ full: 'With it', ablated: 'Without it' }"></trial-stats>
          <trial-stats v-if="ablateResult.placebo_statistics" :stats="ablateResult.placebo_statistics" title="With it compared with same-length filler" :labels="{ full: 'With it', placebo: 'Filler' }"></trial-stats>
          <table class="ai-table"><thead><tr><th>Case</th><th>With it</th><th>Without it</th><th v-if="ablateResult.variants && ablateResult.variants.includes('placebo')">Filler</th></tr></thead>
            <tbody><tr v-for="c in ablateResult.cases" :key="c.case"><td class="tp-mono">{{ c.case }}</td>
              <td v-for="v in (ablateResult.variants || ['full','ablated'])" :key="v">{{ c[v].graded ? c[v].passed + ' / ' + c[v].graded + ' passed' : 'Not graded' }}</td></tr></tbody></table>
          <template v-if="ablateResult.proposal && ablateResult.proposal.kind==='remove-section'">
            <p class="tp-fine">A removal of this section is staged. Review the exact change; the current copy is kept in Recovery when you save.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy || !ablateReviewOwned" @click="openAblateReview()">Review the removal…</button></div>
          </template>
          <template v-if="ablateResult.proposal && ablateResult.proposal.kind==='retire'">
            <h3>Step it down instead of deleting it</h3>
            <ol class="ai-list"><li v-for="step in ablateResult.proposal.ladder" :key="step.step"><b>{{ step.step }}</b>: {{ step.effect }} <span class="tp-mono">{{ step.action }}</span> <small>({{ step.applies_to }})</small></li></ol>
          </template>
          <p v-if="ablateResult.proposal_error" class="tp-issue warn">{{ ablateResult.proposal_error }}</p>
          <p class="tp-fine">Graded only by the assertions in evals.json, for these requests only. {{ ablateResult.run.advisory }}</p>
        </section>
      </template>

      <template v-else-if="page==='ai-conflicts'">
        <h1 class="h1" id="h1" tabindex="-1">Contradiction check</h1>
        <p class="lede">Finds lines in CLAUDE.md, AGENTS.md and GEMINI.md that may disagree with each other or with your skills. Finding candidates uses word patterns only and sends nothing. Optionally, your model judges the top pairs.</p>
        <section class="card tp-panel" aria-labelledby="ai-cf-h">
          <h2 id="ai-cf-h">Set up</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-cfs"><b>Skills from</b><small>Instruction files are compared with the skills in this agent folder.</small></label><select id="ai-cfs" class="field" v-model="conflictsScope" @change="conflictsReport=null; conflictsEstimate=null"><option v-for="sc in agentScopes" :key="sc.id" :value="sc.id">{{ sc.label }} ({{ sc.count }})</option></select></div>
            <div class="tp-set-row"><label for="ai-cfp"><b>Project folder</b><small>Optional. Also reads that project's CLAUDE.md, AGENTS.md and GEMINI.md. It must be inside the folders this app may read.</small></label><input id="ai-cfp" class="field" type="text" v-model="conflictsProject" @change="conflictsReport=null; conflictsEstimate=null" placeholder="/path/to/project"></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !conflictsScope" @click="findConflicts()">Find possible contradictions</button></div>
        </section>
        <section v-if="conflictsReport" class="card tp-panel" aria-labelledby="ai-cfr-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-cfr-h">{{ conflictsReport.candidates.length }} possible contradiction{{ conflictsReport.candidates.length===1?'':'s' }}</h2><p>{{ conflictsReport.sources.length }} sources read<template v-if="conflictsReport.unreadable.length"> · {{ conflictsReport.unreadable.length }} unreadable</template><template v-if="conflictsReport.candidates_truncated"> · list cut at {{ conflictsReport.candidates.length }}</template></p></div></header>
          <p v-if="conflictsReport.unreadable.length" class="tp-fine">Not read: <span class="tp-mono">{{ conflictsReport.unreadable.join(', ') }}</span></p>
          <p v-for="(line,i) in (conflictsReport.inputs_limited || [])" :key="'lim'+i" class="tp-issue warn">{{ line }}</p>
          <details v-if="(conflictsReport.density || []).length" class="listing-cuts"><summary>Directives per always-loaded file<template v-if="conflictsReport.density.some(d => d.dense)"> · {{ conflictsReport.density.filter(d => d.dense).length }} over {{ conflictsReport.dense_threshold }}</template></summary>
            <p class="tp-fine">Every directive in these files is read in every session. Research finds compliance falls as directives accumulate, with early ones favoured past about {{ conflictsReport.dense_threshold }}. Agents also followed "if…, do…" and "never…" wording less often than plain rules, though the effect differs by model.</p>
            <ul><li v-for="d in conflictsReport.density" :key="d.source"><span class="tp-mono">{{ d.source }}</span>: {{ d.directives }}{{ d.capped ? '+' : '' }} directive lines, {{ d.with_reason || 0 }} with a reason, {{ d.conditional || 0 }} conditional ("if…"), {{ d.prohibitive || 0 }} prohibitive ("never…")<span v-if="d.dense" class="pill warn">dense</span></li></ul></details>
          <template v-if="(conflictsReport.stale_references || []).length">
            <h3>{{ conflictsReport.stale_references.length }} stale reference{{ conflictsReport.stale_references.length === 1 ? '' : 's' }} in project instructions</h3>
            <p class="tp-fine">Checked against the project without a model. An agent that follows a stale path or command wastes tool calls and gets no error.</p>
            <ul class="ai-list"><li v-for="row in conflictsReport.stale_references" :key="row.source + row.line + row.reference"><span class="tp-mono">{{ row.reference }}</span>: {{ row.reason }} <small class="tp-mono">({{ row.source }}:{{ row.line }})</small></li></ul>
          </template>
          <p class="tp-fine">{{ conflictsReport.limits }}</p>
          <div v-if="configured && conflictsReport.candidates.length" class="tp-set">
            <div class="tp-set-row"><label for="ai-cfn"><b>Pairs to judge</b><small>Only the two quoted lines of each pair are sent, never whole files.</small></label><select id="ai-cfn" class="field" v-model.number="conflictsMax" @change="conflictsEstimate=null"><option v-for="n in [5,10,20,40]" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-cfv"><b>Votes per pair</b><small>Each pair is always asked in both orders. A third vote catches answers that flip between runs; every vote must agree.</small></label><select id="ai-cfv" class="field" v-model.number="conflictsVotes" @change="conflictsEstimate=null"><option :value="2">2 (both orders)</option><option :value="3">3 (both orders and a repeat)</option></select></div>
          </div>
          <div v-if="configured && conflictsReport.candidates.length && !conflictsEstimate" class="tp-acts"><button class="btn btn-line" :disabled="busy" @click="estimateConflictJudge()">Ask your model to judge…</button></div>
          <p v-else-if="!configured && conflictsReport.candidates.length" class="tp-fine">To have a model judge these pairs, <a href="#/tools/ai-settings">connect one in AI settings</a>.</p>
          <div v-if="conflictsEstimate && conflictsEstimate.status==='estimate'" class="ai-confirm" role="region" aria-label="Before sending">
            <p v-for="(line,i) in conflictsEstimate.egress" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">At most about {{ fmt(conflictsEstimate.run.estimated_input_tokens) }} tokens to {{ conflictsEstimate.run.model }}.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runConflictJudge()">Send and judge</button><button class="btn btn-line" :disabled="busy" @click="conflictsEstimate=null">Cancel</button></div>
          </div>
          <p v-if="conflictsReport.judged != null" class="tp-fine">{{ conflictsReport.judged }} pair{{ conflictsReport.judged===1?'':'s' }} judged; {{ conflictsReport.conflicts.length }} judged a conflict. {{ conflictsReport.run.advisory }}</p>
          <ul class="ai-list ai-conflicts">
            <li v-for="pair in conflictsReport.candidates" :key="pair.id">
              <p><span :class="['pill', conflictLabel(pair)[0]]">{{ conflictLabel(pair)[1] }}</span> <template v-if="pair.facet">{{ pair.facet }}: </template>{{ pair.judge ? pair.judge.why : pair.detail }}</p>
              <blockquote v-for="side in [pair.a, pair.b]" :key="side.source + side.line"><small class="tp-mono">{{ side.source }}:{{ side.line }} · {{ side.layer }}</small><br>{{ side.quote }}</blockquote>
              <p class="tp-fine">Which one wins is not documented by any agent; the model sees both.</p>
            </li>
          </ul>
        </section>
      </template>

      <template v-else-if="page==='ai-budget'">
        <h1 class="h1" id="h1" tabindex="-1">Fit the listing budget</h1>
        <p class="lede">Propose shorter descriptions to fit an estimated listing budget, then compare their simulated selection rates with the original descriptions.</p>
        <p class="tp-fine ai-routing-note">{{routingNotice}}</p>
        <section class="card tp-panel" aria-labelledby="ai-bu-h">
          <h2 id="ai-bu-h">Set up</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-scope4"><b>Agent</b></label><select id="ai-scope4" class="field" v-model="scope"><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }})</option></select></div>
            <div class="tp-set-row"><label for="ai-bch"><b>Budget in characters</b><small>Leave blank for Claude Code to use its measured estimate. Other agents need a number (Codex uses 2% of its context).</small></label><input id="ai-bch" class="field num" type="number" min="100" v-model="budgetChars" placeholder="Measured"></div>
            <div class="tp-set-row"><label for="ai-bmax"><b>Descriptions to shorten</b><small>Largest first.</small></label><select id="ai-bmax" class="field" v-model.number="budgetMax"><option v-for="n in 10" :key="n" :value="n">{{ n }}</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !scope" @click="estimateBudget()">Measure and check what will be sent</button></div>
          <div v-if="budgetEstimate" class="ai-confirm" role="region" aria-label="Before sending">
            <p class="tp-fine">Listing: {{ fmt(budgetEstimate.listing_chars) }} characters; budget: {{ fmt(budgetEstimate.budget_chars) }} ({{ budgetEstimate.source }}).</p>
            <p v-if="budgetEstimate.status==='within-budget'" class="tp-fine">Already within budget. Nothing to do and nothing will be sent.</p>
            <p v-else-if="budgetEstimate.status==='nothing-to-shorten'" class="tp-fine">{{ fmt(budgetEstimate.chars_to_free) }} characters over, but no description is long enough to shorten usefully. Consider turning some skills off or name-only instead.</p>
            <template v-else>
              <p class="tp-fine">{{ fmt(budgetEstimate.chars_to_free) }} characters over. Would shorten: <span class="tp-mono">{{ budgetEstimate.chosen.join(', ') }}</span>.</p>
              <p v-for="(line,i) in budgetEstimate.egress" :key="i" class="tp-fine">{{ line }}</p>
              <p class="tp-fine">At most about {{ fmt(budgetEstimate.run.estimated_input_tokens) }} tokens to {{ budgetEstimate.run.model }}.</p>
              <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runBudget()">Send, shorten and re-test</button><button class="btn btn-line" :disabled="busy" @click="budgetEstimate=null">Cancel</button></div>
            </template>
          </div>
        </section>
        <section v-if="budget && budget.proposals" class="card tp-panel" aria-labelledby="ai-bur-h" aria-live="polite">
          <p class="tp-fine ai-routing-note">{{routingNotice}}</p>
          <header class="tp-panel-h"><div><h2 id="ai-bur-h">Shorter descriptions</h2><p>Versions that passed the simulation free {{ fmt(budget.safe_savings) }} of {{ fmt(budget.chars_to_free) }} characters needed.</p></div>
            <span :class="['pill', budget.fits ? 'ok' : 'warn']">{{ budget.fits ? 'Would fit' : 'Still over' }}</span></header>
          <div v-for="p in budget.proposals" :key="p.name" class="ai-cand">
            <h3><span class="tp-mono">{{ p.name }}</span> <span :class="['pill', p.safe ? 'ok' : 'bad']">{{ p.safe ? 'Simulation retained' : 'Lower simulated selection' }}</span></h3>
            <p>{{ p.proposed }}</p>
            <p class="tp-fine">Saves {{ fmt(p.saves_chars) }} characters. Won {{ pct(p.recall_before) }} of its prompts before, {{ pct(p.recall_after) }} after.</p>
            <details class="tp-more"><summary>Current description</summary><p>{{ p.current }}</p></details>
            <div class="tp-acts"><button class="btn" :class="p.safe ? 'btn-ink' : 'btn-line'" :disabled="busy || appliedNames.includes(p.name)" @click="applyShort(p)">{{ appliedNames.includes(p.name) ? 'Saved' : 'Use shorter version' }}</button></div>
          </div>
          <p v-if="!budget.fits" class="tp-fine">Not enough to fit. Turning rarely used skills off, or name-only in Claude Code settings (see Quality → What Claude Code sees), frees more.</p>
          <p class="tp-fine">{{ budget.run.advisory }}</p>
        </section>
      </template>

      <template v-else-if="page==='ai-overlap'">
        <h1 class="h1" id="h1" tabindex="-1">Overlap check</h1>
        <p class="lede">Pairs of skills an agent could confuse, or whose instructions contradict each other. Each pair is judged twice with the order swapped, and quoted conflicts must appear word for word in the files.</p>
        <section class="card tp-panel" aria-labelledby="ai-ov-h">
          <h2 id="ai-ov-h">Set up</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-scope3"><b>Agent</b></label><select id="ai-scope3" class="field" v-model="scope"><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }})</option></select></div>
            <div class="tp-set-row"><label for="ai-ovn"><b>Pairs to judge</b><small>The most similar pairs are found without AI first; only these are sent.</small></label><select id="ai-ovn" class="field" v-model.number="overlapLimit"><option v-for="n in 12" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><span><b>Also compare</b><small>Optional: two skills you suspect overlap.</small></span>
              <span class="ai-row-acts"><select class="field" v-model="pairA" aria-label="First skill"><option value="">Skill…</option><option v-for="n in scopeSkills" :key="n" :value="n">{{ n }}</option></select><select class="field" v-model="pairB" aria-label="Second skill"><option value="">Skill…</option><option v-for="n in scopeSkills" :key="n" :value="n">{{ n }}</option></select><button class="btn btn-line btn-sm" type="button" :disabled="!pairA||!pairB||pairA===pairB" @click="addPair()">Add</button></span></div>
          </div>
          <p v-if="pairs.length" class="tp-fine">Chosen: <span v-for="(p,i) in pairs" :key="i" class="tp-mono">{{ p[0] }} + {{ p[1] }}<button class="btn btn-line btn-sm" type="button" @click="pairs.splice(i,1)" :aria-label="'Remove ' + p.join(' and ')">×</button> </span></p>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !scope" @click="estimateOverlap()">Find pairs and check what will be sent</button></div>
          <div v-if="overlapEstimate" class="ai-confirm" role="region" aria-label="Before sending">
            <p class="tp-fine">{{ overlapEstimate.candidates_found }} candidate pair{{ overlapEstimate.candidates_found===1?'':'s' }} found; {{ overlapEstimate.pairs_judged===1 ? 'this one' : 'the top ' + overlapEstimate.pairs_judged }} would be judged:</p>
            <ul class="tp-fine ai-list"><li v-for="p in overlapEstimate.pairs" :key="p.skills.join('+')"><span class="tp-mono">{{ p.skills.join(' + ') }}</span> ({{ p.sources.join(', ') }})</li></ul>
            <p v-for="(line,i) in overlapEstimate.egress" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">At most about {{ fmt(overlapEstimate.run.estimated_input_tokens) }} tokens to {{ overlapEstimate.run.model }}.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy || !overlapEstimate.pairs_judged" @click="runOverlap()">Send and judge</button><button class="btn btn-line" :disabled="busy" @click="overlapEstimate=null">Cancel</button></div>
          </div>
        </section>
        <section v-if="overlap" class="card tp-panel" aria-labelledby="ai-ovr-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-ovr-h">Judged pairs</h2><p>{{ overlap.pairs_judged }} pair{{ overlap.pairs_judged===1?'':'s' }} · {{ overlap.run.model }} · {{ fmt(overlap.run.input_tokens) }} input tokens</p></div></header>
          <p v-if="!overlap.judgements.length" class="tp-empty">No pairs were judged.</p>
          <div v-for="j in overlap.judgements" :key="j.skills.join('+')" class="ai-cand">
            <h3><span class="tp-mono">{{ j.skills[0] }}</span> + <span class="tp-mono">{{ j.skills[1] }}</span> <span :class="['pill', relationTone(j.relation)]">{{ relationLabel(j.relation) }}</span></h3>
            <p class="tp-fine">Found by {{ j.sources.join(', ') }}. Suggestion: {{ actionLabel(j.recommendation) }}<span v-if="j.router_confusion">; an agent could pick the wrong one</span>.</p>
            <p v-if="j.shared_requests.length" class="tp-fine">Requests both could claim: {{ j.shared_requests.join(' · ') }}</p>
            <div v-for="(c,i) in j.conflicts" :key="i" class="ai-conflict"><p><b>{{ j.skills[0] }}:</b> <q>{{ c.a_quote }}</q></p><p><b>{{ j.skills[1] }}:</b> <q>{{ c.b_quote }}</q></p><p class="tp-fine">{{ c.why }}</p></div>
            <p v-if="j.unverified_quotes" class="tp-fine">{{ j.unverified_quotes }} quoted conflict(s) were dropped because the text is not in the files.</p>
            <template v-for="n in j.skills" :key="n"><p v-if="j.boundaries[n]" class="tp-fine">Could add to <span class="tp-mono">{{ n }}</span>: “{{ j.boundaries[n] }}” <button class="btn btn-line btn-sm" @click="handoff(n)">Improve {{ n }}</button></p></template>
            <p v-if="j.merged_description" class="tp-fine">Merged description idea: {{ j.merged_description }}</p>
          </div>
          <p class="tp-fine">{{ overlap.run.advisory }}</p>
        </section>
      </template>

      <template v-else-if="page==='ai-improve'">
        <h1 class="h1" id="h1" tabindex="-1">Improve a description</h1>
        <p class="lede">Your model proposes new descriptions, then each one is re-tested against prompts it never saw. Only a measurable improvement is recommended.</p>
        <section class="card tp-panel" aria-labelledby="ai-im-h">
          <h2 id="ai-im-h">Choose a skill</h2>
          <div class="tp-set">
            <div class="tp-set-row"><label for="ai-scope2"><b>Agent</b></label><select id="ai-scope2" class="field" v-model="scope"><option v-for="s in agentScopes" :key="s.id" :value="s.id">{{ s.label }} ({{ s.count }})</option></select></div>
            <div class="tp-set-row"><label for="ai-name"><b>Skill</b></label><select id="ai-name" class="field" v-model="improveName"><option value="">Choose…</option><option v-for="n in scopeSkills" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-cand"><b>Proposals</b></label><select id="ai-cand" class="field" v-model.number="candidates"><option v-for="n in 3" :key="n" :value="n">{{ n }}</option></select></div>
            <div class="tp-set-row"><label for="ai-rep2"><b>Repeats</b></label><select id="ai-rep2" class="field" v-model.number="repeats"><option v-for="n in 5" :key="n" :value="n">{{ n }}</option></select></div>
          </div>
          <div class="tp-acts"><button class="btn btn-line" :disabled="busy || !improveName" @click="estimateImprove()">Check what will be sent</button></div>
          <div v-if="improveEstimate" class="ai-confirm" role="region" aria-label="Before sending">
            <p v-for="(line,i) in improveEstimate.egress" :key="i" class="tp-fine">{{ line }}</p>
            <p class="tp-fine">About {{ fmt(improveEstimate.run.estimated_input_tokens) }} tokens to {{ improveEstimate.run.model }}.</p>
            <div class="tp-acts"><button class="btn btn-ink" :disabled="busy" @click="runImprove()">Send and propose</button><button class="btn btn-line" :disabled="busy" @click="improveEstimate=null">Cancel</button></div>
          </div>
        </section>
        <section v-if="improve" class="card tp-panel" aria-labelledby="ai-cands-h" aria-live="polite">
          <header class="tp-panel-h"><div><h2 id="ai-cands-h">Proposals for {{ improve.name }}</h2><p>{{ improve.prompt_count }} test prompts, half held back from the model when it wrote these.</p></div>
            <span :class="['pill', improve.verdict==='improved' ? 'ok' : 'warn']">{{ improve.verdict==='improved' ? 'Better description found' : 'Nothing beat the current one' }}</span></header>
          <div class="ai-cand"><h3>Current</h3><p>{{ improve.current }}</p>
            <p class="tp-fine">Picked for {{ pct(improve.baseline.overall.recall) }} of its prompts ({{ pct(improve.baseline.holdout.recall) }} held-out); stayed out of {{ pct(improve.baseline.overall.near_miss_avoided) }} of the others.</p></div>
          <div v-for="(c,i) in improve.candidates" :key="i" class="ai-cand">
            <p v-if="i===0 && improve.selection_note" class="tp-fine">{{ improve.selection_note }}</p>
            <h3>Proposal {{ i+1 }} <span :class="['pill', c.recommended ? 'ok' : 'off']">{{ c.recommended ? 'Recommended' : 'Not better' }}</span></h3>
            <p>{{ c.description }}</p>
            <p class="tp-fine">Picked for {{ pct(c.overall.recall) }} ({{ pct(c.holdout.recall) }} held-out); stayed out of {{ pct(c.overall.near_miss_avoided) }} of the others. {{ c.chars }} characters. {{ c.rationale }}</p>
            <p v-if="c.overfit" class="tp-issue warn">It does {{ Math.round(c.gap * 100) }} points better on the prompts it was written from than on held-out prompts, so it may fit those examples more than new requests.</p>
            <div class="tp-acts"><button class="btn" :class="c.recommended ? 'btn-ink' : 'btn-line'" :disabled="busy || applied===c.description" @click="applyCandidate(c)">{{ applied===c.description ? 'Saved' : 'Use this description' }}</button></div>
          </div>
          <p class="tp-fine">{{ improve.run.advisory }} {{ fmt(improve.run.input_tokens) }} input tokens used.</p>
        </section>
      </template>

      <section class="card tp-panel" aria-labelledby="ai-history-h" v-if="configured || pastRuns.length || historyError">
        <header class="tp-panel-h"><h2 id="ai-history-h">Past runs</h2>
          <button class="btn btn-line btn-sm" :disabled="historyBusy" @click="loadRuns()">Refresh past runs</button></header>
        <p class="tp-fine">Latest 20 saved runs across AI tools.</p>
        <p v-if="historyError" class="v2-tool-error" role="alert">{{ historyError }}</p>
        <p v-if="historyBusy" class="tp-fine" role="status">Loading past runs…</p>
        <p v-else-if="!pastRuns.length" class="tp-empty">No saved runs yet.</p>
        <ul class="tp-rows"><li v-for="r in pastRuns" :key="r.run_id" class="v2-tool-row">
          <span class="tp-row-main"><strong>{{ r.kind }}<span v-if="r.status==='disconnected'" class="pill off ai-partial">Partial run</span></strong><small>{{ [r.started, r.model, r.scope, r.name].filter(Boolean).join(', ') }}</small></span>
          <button class="btn btn-line btn-sm" :disabled="historyBusy" :aria-label="'View run ' + r.run_id" @click="openRun(r.run_id)">View</button>
        </li></ul>
        <div v-if="pastRun" aria-live="polite"><h3>Saved run details</h3><p class="tp-fine">Saved model output, shown as text. Results are estimates.</p>
          <pre class="ai-run-text tp-mono" tabindex="0" aria-label="Saved run details">{{ runText(pastRun) }}</pre></div>
      </section>
    </div>`,
  };
  window.SkillsV2AiCopyBrief = {
    props: { rows: Array, fromLabel: String, toLabel: String },
    data() { return { estimate: null, result: null, key: "", busy: false, error: "" }; },
    computed: {
      excerpts() {
        const text = side => this.rows.map(row => row[side]?.text || "").join("\n").slice(0, 12000);
        return { before: text("before"), after: text("after") };
      },
      inputKey() { return JSON.stringify(this.excerpts); },
    },
    methods: {
      async brief(estimate) {
        const key = this.inputKey;
        if (this.busy || (!estimate && this.key !== key)) return;
        this.busy = true; this.error = ""; this.result = null;
        try {
          const result = await post("/api/ai/copy-diff", { ...this.excerpts, estimate,
            plan: estimate ? undefined : this.estimate?.plan });
          if (key !== this.inputKey) return;
          if (estimate) { this.estimate = result; this.key = key; }
          else this.result = result;
        } catch (error) { if (key === this.inputKey) this.error = error.message; }
        finally { this.busy = false; }
      },
    },
    template: `<details class="tp-more">
      <summary>Explain changes with AI</summary>
      <p class="tp-fine">Uses excerpts from the comparison above, up to 12,000 characters per copy.</p>
      <button type="button" class="btn btn-line btn-sm" :disabled="busy" @click="brief(true)">Preview AI request</button>
      <p v-if="busy" role="status">Preparing explanation…</p><p v-if="error" class="state-note err" role="alert">{{ error }}</p>
      <div v-if="estimate && key === inputKey && !result" class="ai-confirm">
        <p>{{ estimate.egress }} {{ estimate.run.model }} at <code>{{ estimate.destination }}</code>.</p>
        <button type="button" class="btn btn-ink btn-sm" :disabled="busy" @click="brief(false)">Explain changes</button>
      </div>
      <div v-if="result && key === inputKey" class="ai-confirm">
        <p v-if="!result.changes.length">The model returned no changes with a matching quote.</p>
        <p v-for="(change, i) in result.changes" :key="i">{{ change.text }} <b>{{ change.file === 'before' ? fromLabel : toLabel }}</b> <q>{{ change.quote }}</q></p>
        <p class="tp-fine">Review the underlying differences before syncing. {{ result.run.model }}</p>
      </div>
    </details>`,
  };

  /* Paired trial statistics (skillsmgr/trial_stats.py). "Inconclusive" is a
   * real answer: the interval includes zero or there were too few trials. */
  window.SkillsV2TrialStats = {
    props: { stats: Object, title: String, labels: Object, numbered: Boolean },
    computed: {
      verdict() { return { helps: ["ok", "Helps"], hurts: ["bad", "Worse"], inconclusive: ["warn", "Inconclusive"],
        ungraded: ["off", "Not graded"] }[this.stats.verdict] || ["off", this.stats.verdict]; },
    },
    methods: {
      signed(n) { const v = Math.round(n * 100); return (v > 0 ? "+" : "") + v + " pts"; },
      name(key) { return (this.labels && this.labels[key]) || key; },
      caseName(c) { return this.numbered ? "Request " + (c + 1) : "Case " + c; },
      tokens(key) { const v = this.stats.tokens.mean_output_tokens[key]; return v === null ? "unknown" : Math.round(v); },
    },
    template: `<div class="ai-confirm" role="group" :aria-label="title">
      <p><span :class="['pill', verdict[0]]">{{ verdict[1] }}</span> {{ title }}</p>
      <p v-if="stats.lift !== null" class="tp-fine">{{ name(stats.treatment) }} passed {{ Math.round(stats.pass_rate[stats.treatment] * 100) }}% and {{ name(stats.baseline) }} {{ Math.round(stats.pass_rate[stats.baseline] * 100) }}% of graded outputs. Difference {{ signed(stats.lift) }}, {{ Math.round(stats.confidence * 100) }}% interval {{ signed(stats.interval[0]) }} to {{ signed(stats.interval[1]) }}, over {{ stats.paired_cases }} {{ stats.paired_cases === 1 ? 'case' : 'cases' }} × {{ stats.trials }} {{ stats.trials === 1 ? 'trial' : 'trials' }}: {{ stats.reason }}.</p>
      <p v-else class="tp-fine">{{ stats.reason }}.</p>
      <p v-if="stats.min_detectable != null" class="tp-fine">With {{ stats.paired_cases }} {{ stats.paired_cases === 1 ? 'case' : 'cases' }}, only a true difference of about {{ Math.round(stats.min_detectable * 100) }} points or more would reliably show. More cases narrow this; more repeats help less.</p>
      <p v-if="stats.excluded" class="tp-fine">{{ stats.excluded }} incomplete or ungraded {{ stats.excluded === 1 ? 'output was' : 'outputs were' }} left out.</p>
      <p v-if="stats.tokens.regression" class="tp-issue warn">{{ name(stats.treatment) }} uses more output tokens: about {{ tokens(stats.treatment) }} against {{ tokens(stats.baseline) }} per answer.</p>
      <p v-for="f in stats.non_discriminating" :key="f.case + '-' + f.assertion" class="tp-issue warn">{{ caseName(f.case) }}, check {{ f.assertion + 1 }} always {{ f.always === 'passes' ? 'passes' : 'fails' }}, so it cannot tell the versions apart.</p>
    </div>`,
  };

  window.SkillsV2AiCompare = {
    props: { reviewId: String, example: String },
    data() { return { cases: [{ prompt: this.example || "", contains: "", not_contains: "" }], without: false, comparisonModel: "", trials: 3,
      busy: false, error: "", estimate: null, result: null, key: "" }; },
    computed: {
      inputKey() { return JSON.stringify([this.reviewId, this.cases, this.without, this.comparisonModel.trim(), this.trials]); },
      ready() { return this.cases.every(row => row.prompt.trim()); },
      modelResults() { const r = this.result; return r ? [{ model: r.run.model, cases: r.cases, statistics: r.statistics },
        ...(r.comparison_model && r.alternate_cases.length ? [{ model: r.comparison_model, cases: r.alternate_cases, statistics: r.alternate_statistics }] : [])] : []; },
    },
    methods: {
      addCase() { if (this.cases.length < 6) this.cases.push({ prompt: "", contains: "", not_contains: "" }); },
      async compare(estimate) {
        if (this.busy || !this.ready || (!estimate && this.key !== this.inputKey)) return;
        const key = this.inputKey;
        this.busy = true; this.error = ""; this.result = null;
        try {
          const result = await post("/api/ai/compare-edit", { review_id: this.reviewId, cases: this.cases,
            without_skill: this.without, comparison_model: this.comparisonModel.trim(), trials: this.trials,
            estimate, plan: estimate ? undefined : this.estimate?.plan });
          if (key !== this.inputKey) return;
          if (estimate) { this.estimate = result; this.key = key; }
          else this.result = result;
        } catch (error) { if (key === this.inputKey) this.error = error.message; }
        finally { this.busy = false; }
      },
      label(key) { return {current: "Current", candidate: "Proposed", without_skill: "Without skill"}[key] || key; },
      outcome(variant) {
        if (variant.trials.length > 1) {
          const graded = variant.trials.filter(t => t.passed !== null);
          return graded.length ? graded.filter(t => t.passed).length + "/" + graded.length + " trials passed" : "Review outputs";
        }
        return !variant.complete ? "Incomplete" : variant.grade.graded ? variant.grade.passed + "/" + variant.grade.total + " checks passed" : "Review output";
      },
      statRows(stats) { return Object.entries(stats || {}).map(([key, value]) => ({ key, value,
        title: key === "candidate_vs_current" ? "Proposed compared with current" : "Proposed compared with no skill" })); },
      async downloadEvidence() {
        const id = this.result?.run_id;
        if (!id || this.busy) return;
        this.busy = true; this.error = "";
        try {
          const evidence = await api(`/api/ai/runs/${encodeURIComponent(id)}`);
          const url = URL.createObjectURL(new Blob([JSON.stringify(evidence, null, 2) + "\n"], {type: "application/json"}));
          const link = document.createElement("a");
          link.href = url; link.download = id + ".json"; link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) { this.error = error.message; }
        finally { this.busy = false; }
      },
    },
    template: `<details class="tp-more">
      <summary>Compare outputs with AI</summary>
      <p class="tp-fine">Compare the same requests with each version supplied as instructions. Use the trigger test to check skill selection.</p>
      <fieldset class="instance-metadata" v-for="(row, i) in cases" :key="i" :disabled="busy">
        <legend>Test request {{ i + 1 }}</legend>
        <label class="tp-field">Request<textarea class="field instance-create-body" rows="2" maxlength="4000" v-model="row.prompt"></textarea></label>
        <label class="tp-field">Output should contain (optional)<input class="field" maxlength="500" v-model="row.contains"></label>
        <label class="tp-field">Output should exclude (optional)<input class="field" maxlength="500" v-model="row.not_contains"></label>
        <button type="button" class="btn btn-soft btn-sm" v-if="cases.length > 1" @click="cases.splice(i, 1)">Remove request {{ i + 1 }}</button>
      </fieldset>
      <label class="tp-check"><input type="checkbox" :disabled="busy" v-model="without"> Include an output without skill instructions</label>
      <label class="tp-field">Second model ID on the same provider (optional)<input class="field" maxlength="160" :disabled="busy" v-model="comparisonModel"></label>
      <label class="tp-field">Repeat each request<select class="field" :disabled="busy" v-model.number="trials"><option :value="1">Once</option><option :value="3">3 times</option><option :value="5">5 times</option></select></label>
      <p class="tp-fine">Model answers vary between runs. Repeats show whether a difference holds up; one run is reported as inconclusive.</p>
      <div class="tp-acts">
        <button type="button" class="btn btn-line btn-sm" :disabled="busy || cases.length >= 6" @click="addCase()">Add request</button>
        <button type="button" class="btn btn-line btn-sm" :disabled="busy || !ready" @click="compare(true)">Preview comparison</button>
      </div>
      <p v-if="busy" role="status">Preparing comparison…</p>
      <p v-if="error" class="state-note err" role="alert">{{ error }}</p>
      <div v-if="estimate && key === inputKey && !result" class="ai-confirm">
        <p>{{ estimate.egress[0] }} {{ estimate.calls_planned }} calls to {{ estimate.run.model }}<template v-if="estimate.comparison_model"> and {{ estimate.comparison_model }}</template> at <code>{{ estimate.destination }}</code>.</p>
        <button type="button" class="btn btn-ink btn-sm" :disabled="busy" @click="compare(false)">Run comparison</button>
      </div>
      <template v-if="result && key === inputKey">
        <p class="tp-fine">{{ result.run.model }} · evidence {{ result.run_id }}</p>
        <p v-if="result.alternate_error" class="tp-fine" role="status">{{ result.comparison_model }} did not finish: {{ result.alternate_error }} Results from {{ result.run.model }} are kept.</p>
        <button type="button" class="btn btn-line btn-sm" :disabled="busy" @click="downloadEvidence()">Download test evidence</button>
        <section v-for="group in modelResults" :key="group.model" class="ai-confirm">
          <h4>{{ group.model }}</h4>
          <trial-stats v-for="row in statRows(group.statistics)" :key="row.key" :stats="row.value" :title="row.title" numbered
            :labels="{ current: 'Current', candidate: 'Proposed', without_skill: 'Without skill' }"></trial-stats>
          <div v-for="(pair, i) in group.cases" :key="i"><p>Request {{ i + 1 }}</p>
            <details v-for="(variant, name) in pair" :key="name"><summary>{{ label(name) }} · {{ outcome(variant) }}</summary><pre class="ai-run-text">{{ variant.output }}</pre><p v-if="variant.trials.length > 1" class="tp-fine">Showing trial 1 of {{ variant.trials.length }}.</p></details>
          </div>
        </section>
      </template>
    </details>`,
  };
})();

/* "Explain with AI" inside an install or update review (docs/39 A5). Every
 * claim shown quotes the file it names; risk opinions never change findings. */
(function () {
  const api = window.SkillManagerDomain.api;
  const post = (url, body) => api(url, { method: "POST", body: JSON.stringify(body || {}) });
  window.SkillsV2AiBriefing = {
    props: { kind: String, reviewId: String },
    data() { return { configured: null, busy: false, error: "", estimate: null, brief: null }; },
    watch: { reviewId() { this.estimate = null; this.brief = null; this.error = ""; } },
    async mounted() { try { this.configured = !!(await api("/api/ai/settings")).configured; } catch (e) { this.configured = false; } },
    methods: {
      body(estimate) { return { kind: this.kind, review_id: this.reviewId, estimate }; },
      async run(estimate) {
        this.busy = true; this.error = "";
        try { const r = await post("/api/ai/review-briefing", this.body(estimate)); if (estimate) { this.estimate = r; this.brief = null; } else { this.brief = r; this.estimate = null; } }
        catch (e) { this.error = (e && e.message) || String(e); } finally { this.busy = false; }
      },
      matchLabel(m) { return { yes: "Description matches what it does", partly: "Description is partly accurate", no: "Description does not match what it does", unclear: "Could not tell" }[m] || m; },
      matchTone(m) { return { yes: "ok", partly: "warn", no: "bad" }[m] || "off"; },
      opinionLabel(o) { return { "likely-real": "Model thinks this is real", "likely-false-positive": "Model thinks this is a false alarm", unclear: "Model is unsure" }[o] || o; },
    },
    template: `
    <section v-if="reviewId" class="ai-brief" aria-label="AI briefing">
      <div class="tp-panel-h"><h3>Explain with AI <small class="tp-count">your own key · advisory</small></h3>
        <a v-if="configured===false" class="btn btn-line btn-sm" href="#/tools/ai-settings">Set up AI</a>
        <button v-else-if="!estimate && !brief" class="btn btn-line btn-sm" :disabled="busy || configured===null" @click="run(true)">Explain this change</button></div>
      <p v-if="error" class="v2-tool-error" role="alert">{{ error }}</p>
      <p v-if="busy" class="v2-tool-status" role="status"><span class="v2-dot" aria-hidden="true"></span>Working…</p>
      <div v-if="estimate" class="ai-confirm">
        <p v-for="(line,i) in estimate.egress" :key="i" class="tp-fine">{{ line }}</p>
        <p class="tp-fine">At most about {{ estimate.run.estimated_input_tokens.toLocaleString() }} tokens to {{ estimate.run.model }}.</p>
        <div class="tp-acts"><button class="btn btn-ink btn-sm" :disabled="busy" @click="run(false)">Send and explain</button><button class="btn btn-line btn-sm" :disabled="busy" @click="estimate=null">Cancel</button></div>
      </div>
      <div v-if="brief" aria-live="polite" class="ai-brief-body">
        <p>{{ brief.summary }}</p>
        <p><span :class="['pill', matchTone(brief.description_matches)]">{{ matchLabel(brief.description_matches) }}</span></p>
        <template v-if="brief.capabilities.length"><h4>What it can do</h4>
          <p v-for="(c,i) in brief.capabilities" :key="'c'+i" class="tp-fine"><b>{{ c.kind }}</b>: {{ c.text }} <span class="tp-mono">{{ c.file }}</span> <q class="tp-mono">{{ c.quote }}</q></p></template>
        <template v-if="brief.claims.length"><h4>Changes</h4>
          <p v-for="(c,i) in brief.claims" :key="'k'+i" class="tp-fine">{{ c.text }} <span class="tp-mono">{{ c.file }}</span> <q class="tp-mono">{{ c.quote }}</q></p></template>
        <template v-if="brief.mismatches.length"><h4>Not in the description</h4>
          <p v-for="(c,i) in brief.mismatches" :key="'m'+i" class="tp-fine">{{ c.text }} <span class="tp-mono">{{ c.file }}</span> <q class="tp-mono">{{ c.quote }}</q></p></template>
        <template v-if="brief.finding_opinions.length"><h4>Second opinion on risk findings</h4>
          <p v-for="o in brief.finding_opinions" :key="'o'+o.index" class="tp-fine">Finding {{ o.index + 1 }} ({{ o.finding_severity }} {{ o.finding_kind }}): {{ opinionLabel(o.opinion) }}. {{ o.why }}</p></template>
        <p class="tp-fine"><span v-if="brief.dropped_unquoted">{{ brief.dropped_unquoted }} claim(s) dropped because their quote is not in the files. </span>{{ brief.notes[0] }} {{ brief.run.model }}.</p>
      </div>
    </section>`,
  };
})();
