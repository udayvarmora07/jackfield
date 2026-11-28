/* Shared app state, registration and existing read/Undo workflows. */
"use strict";

(function () {
  const { api } = window.SkillManagerDomain;
  const Model = window.SkillsV2Model;
  const { markRaw } = Vue;
  const registrations = [];
  const postPlan = (path, body) => api("/api/batch/" + path, { method: "POST", body: JSON.stringify(body) });
  const targetOf = (copy) => ({ name: copy.name, scope: copy.scope, physical_path: copy.path });
  const keyOf = (name, scope) => JSON.stringify([name, scope]);
  const recordPath = (row) => row.physical_path || row.path;

  function inventoryChanges(previous, next) {
    const fingerprints = (rows) => {
      const found = new Map();
      for (const row of rows) {
        const values = found.get(row.name) || [];
        values.push(JSON.stringify([row.scope, recordPath(row), row.content_hash, row.disabled, row.instance_state]));
        found.set(row.name, values);
      }
      return new Map([...found].map(([name, values]) => [name, values.sort().join("\n")]));
    };
    const before = fingerprints(previous), after = fingerprints(next);
    return [...new Set([...before.keys(), ...after.keys()])].filter((name) => before.get(name) !== after.get(name));
  }

  function matchesEvidence(evidence, copy) {
    return evidence && recordPath(evidence) === copy.path &&
      String(evidence.content_hash || "") === String(copy.record.content_hash || "") &&
      !!evidence.disabled === !!copy.record.disabled;
  }

  async function makePlan(operation, copies, toScopes = [], force = false) {
    const input = { operation, targets: copies.map(targetOf), to_scopes: toScopes, force };
    const plan = await postPlan("preview", input);
    if (!plan.plan_id || plan.targets.length !== copies.length ||
        !copies.every((copy, index) => matchesEvidence(plan.targets[index], copy))) {
      throw new Error("A copy changed since the table loaded. Refresh and review it again.");
    }
    return { input, plan, execute: () => postPlan("execute", { ...input, plan_id: plan.plan_id }) };
  }

  const planResult = (result) => result.results || [];
  const assertResult = (result) => {
    const failure = planResult(result).find((item) => item.status !== "ok");
    if (failure) throw new Error(failure.error || "Jackfield could not finish the change.");
  };
  function unconfirmed(message, cause) {
    return Object.assign(new Error(message, { cause }), { verify: true });
  }

  async function changeToggle(copy, enable) {
    const plan = await makePlan(enable ? "enable" : "disable", [copy]);
    try { assertResult(await plan.execute()); }
    catch (error) { throw unconfirmed("The file state could not be confirmed. Refresh files to check it.", error); }
    return async () => {
      const inverse = { ...copy, record: { ...copy.record, disabled: !enable } };
      const undo = await makePlan(enable ? "disable" : "enable", [inverse]);
      assertResult(await undo.execute());
    };
  }

  function syncPairs(sources, scopes) {
    return sources.flatMap((source) => scopes.map((scope) => ({ source, scope, key: keyOf(source.name, scope) })));
  }

  function checkedDestinations(plan, originals) {
    const destinations = plan.targets.flatMap((source) =>
      source.destinations.map((row) => [keyOf(source.name, row.scope), row]));
    const evidence = new Map(destinations);
    if (destinations.length !== originals.length || evidence.size !== originals.length ||
        originals.some((copy) => !matchesEvidence(evidence.get(keyOf(copy.name, copy.scope)), copy))) {
      throw new Error("A destination changed since the table loaded. Refresh and review it again.");
    }
    return evidence;
  }

  async function restorePrior(app, entry) {
    await app.restoreTrashed(entry.name, entry.scope, entry.trash_path);
  }

  async function restoreAvailable(app, entries) {
    const outcomes = await Promise.allSettled(entries.map((entry) => restorePrior(app, entry)));
    return outcomes.filter((result) => result.status === "rejected").length;
  }

  async function copyTrees(app, change) {
    const { sources, scopes, originals } = change;
    const checked = await makePlan("sync", sources, scopes, true);
    const initial = checkedDestinations(checked.plan, originals);
    const recovery = new Map();
    let copiesMade = [], executeStarted = false;
    try {
      if (originals.length) {
        const remove = await makePlan("remove", originals);
        if (remove.plan.targets.some((row) => initial.get(keyOf(row.name, row.scope))?.tree_hash !== row.tree_hash)) {
          throw new Error("A destination changed during the preview. Refresh and review it again.");
        }
        executeStarted = true;
        const result = await remove.execute();
        for (const row of planResult(result)) {
          if (row.trash_path) recovery.set(keyOf(row.name, row.scope), row);
        }
        assertResult(result);
        if (recovery.size !== originals.length) throw new Error("The previous copies could not all be verified in Trash.");
      }
      const install = await makePlan("sync", sources, scopes);
      checkedDestinations(install.plan, []);
      const sourceTrees = new Map(checked.plan.targets.map((row) => [row.name, row.tree_hash]));
      if (install.plan.targets.some((row) => sourceTrees.get(row.name) !== row.tree_hash)) {
        throw new Error("A source changed during the preview. Refresh and review it again.");
      }
      executeStarted = true;
      const response = await install.execute();
      const observed = new Set(planResult(response).flatMap((row) => (row.synced || []).map((scope) => keyOf(row.name, scope))));
      copiesMade = syncPairs(sources, scopes).filter((pair) => observed.has(pair.key));
      if (!copiesMade.length) throw new Error(planResult(response).find((row) => row.error)?.error || "The server did not confirm a copy.");
      const unsuccessful = [...recovery].filter(([key]) => !observed.has(key)).map(([, row]) => row);
      const unavailable = await restoreAvailable(app, unsuccessful);
      return { copiesMade, recovery, sourceTrees,
        skipped: sources.length * scopes.length - copiesMade.length, unavailable };
    } catch (error) {
      if (copiesMade.length) throw error;
      const failed = await restoreAvailable(app, [...recovery.values()]);
      if (failed || executeStarted) throw unconfirmed("Jackfield couldn’t confirm which folders changed. Refresh files and check Trash for previous copies.", error);
      throw error;
    }
  }

  async function recordCopyUndo(app, result) {
    const installed = result.copiesMade.map(({ source, scope }) => {
      const copies = app.m.byName.get(source.name)?.squareCopies.filter((copy) => copy.scope === scope);
      return copies?.length === 1 ? copies[0] : null;
    });
    if (installed.some((copy) => !copy)) return null;
    const removal = await makePlan("remove", installed);
    if (removal.plan.targets.some((row) => row.tree_hash !== result.sourceTrees.get(row.name))) return null;
    return async () => {
      let removed;
      try { removed = await removal.execute(); }
      catch (error) { throw unconfirmed("The Undo outcome could not be confirmed. Refresh files and check Trash.", error); }
      const failures = [];
      for (const row of planResult(removed)) {
        if (row.status !== "ok") { failures.push(row.error); continue; }
        const prior = result.recovery.get(keyOf(row.name, row.scope));
        if (!prior) continue;
        try { await restorePrior(app, prior); }
        catch (error) {
          failures.push(error.message);
          await restoreAvailable(app, row.trash_path ? [row] : []);
        }
      }
      if (failures.length) throw new Error(failures.filter(Boolean).join(". ") || "Some copies could not be restored.");
    };
  }

  window.Jackfield = {
    register: (register) => registrations.push(register),
    install: (app) => registrations.forEach((register) => register(app)),
    // Vue makes this contribution reactive as part of the one root data object.
    createState: () => ({
      refreshGen: 0, m: null, loading: true, loadError: "", history: [], historyError: "", checkedAt: 0,
      records: [], scopes: [], busy: false, toasts: [], live: "", toastSeq: 0, screenVisit: 0,
      tableWorking: [], tableError: null, diskChanges: [], changedRows: [], highlightsTimer: null,
    }),
    stateActions: {
      async refresh({ observe = false, showChanges = false } = {}) {
        /* Overlapping refreshes (Refresh files, tab focus, Undo, tool changes)
         * must not let an older, slower response overwrite a newer one. */
        const gen = ++this.refreshGen;
        this.loading = true; this.loadError = "";
        try {
          const [scopes, records, history] = await Promise.all([
            api("/api/scopes"), api("/api/skills?scope=all&body=0"),
            api("/api/history?limit=8").then(rows => ({rows, error: ""}),
              e => ({rows: [], error: this.friendly(e.message)})),
          ]);
          if (gen !== this.refreshGen) return;
          const changed = this.m && this.route.page === "skills" && (observe || showChanges)
            ? inventoryChanges(this.records, records) : [];
          if (observe && changed.length) { this.diskChanges = changed; return; }
          if (observe && this.diskChanges.length) return;
          if (!observe) this.diskChanges = [];
          if (showChanges && changed.length) {
            clearTimeout(this.highlightsTimer);
            this.changedRows = changed;
            this.highlightsTimer = setTimeout(() => { this.changedRows = []; }, 3500);
          }
          this.scopes=markRaw(scopes);this.records=markRaw(records);
          this.m = markRaw(Model.build(records, scopes, { suggested: 100 }));
          this.checkedAt = Date.now();
          /* What to track only decorates the pages (the server already filters).
           * Its report counts every agent folder, so it starts after the skills
           * have arrived instead of competing with them, and nothing waits on it. */
          this.loadTracking();
          /* A reload produces fresh copies, so nothing is carried over from the
           * previous list: a body is re-read only where a view needs one. */
          this.bodies = {}; this.bodyInflight = {}; this.bodyErrors = {};
          this.history = Array.isArray(history.rows) ? history.rows : history.rows?.history || [];
          this.historyError = history.error;
          this.loadTrash();
          if (this.route.page === "recovery") this.loadAgentTrash();
          this.loadCatalog();
          this.primeBodies();
          this.loadSkillHistory();
          this.showRouteScreen();
        } catch (e) {
          if (gen === this.refreshGen) {
            this.loadError = this.friendly(e.message || "The skills could not be read.");
            // Advanced reads its tool switches independently of the Skills inventory.
            if (!this.tracking) this.loadTracking();
          }
        } finally { if (gen === this.refreshGen) this.loading = false; }
      },
      async change(kind, target) {
        if (this.busy) return;
        const visit = this.screenVisit;
        this.busy = true;
        this.tableError = null;
        this.tableWorking = target.keys;
        let result, undo, wrote = false;
        try {
          if (kind === "toggle") undo = await changeToggle(target.copy, target.enable);
          else result = await copyTrees(this, target);
          wrote = true;
          await this.refresh();
          if (this.loadError) throw new Error("The write finished, but the new state could not be read. Refresh files to check it.");
          if (kind === "toggle") {
            const match = this.m.byName.get(target.copy.name)?.copies.find((copy) => copy.path === target.copy.path && copy.scope === target.copy.scope);
            if (!match || !!match.record.disabled === target.enable) throw new Error("The new file state could not be confirmed. Refresh files to check it.");
          } else {
            if (result.copiesMade.some(({ source, scope }) => !this.m.byName.get(source.name)?.squareCopies.some(
              (copy) => copy.scope === scope && copy.hash === source.hash && copy.state === source.state))) {
              throw new Error("A copied folder could not be confirmed. Refresh files to check the result.");
            }
            try { undo = await recordCopyUndo(this, result); } catch { undo = null; }
          }
          let message = target.onVerified?.() || target.message;
          if (result?.skipped) message = `${result.copiesMade.length} copies changed. ${result.skipped} could not be changed.`;
          if (result && !undo) message += " Undo isn’t available for these copies.";
          if (result?.unavailable || (result && !undo && target.originals.length)) message += " Check Trash for previous copies.";
          if (visit === this.screenVisit) {
            const selected = this.tableSelection;
            if (selected && this.tableSheetOpen && target.keys.includes(selected.name + ":" + selected.agent)) {
              if (this.route.page === "skill") this.closeReaderSquare();
              else this.tableClose();
            }
            this.toast(message, { undo, onUndo: target.onUndo, err: !!result?.skipped });
          } else if (result?.skipped || result?.unavailable) {
            this.toast(message, { err: true });
          }
        } catch (error) {
          await this.refresh();
          if (visit !== this.screenVisit) {
            this.toast(error.message, { err: true });
            return;
          }
          this.tableError = { key: target.keys[0], reason: this.friendly(error.message),
            details: error.cause ? this.friendly(error.cause.message) : "", verify: wrote || !!error.verify };
          if (target.onError?.(this.tableError)) return;
          this.live = this.tableError.reason;
          const selected = this.tableSelection;
          if (!selected || selected.name + ":" + selected.agent !== this.tableError.key) {
            this.toast(this.tableError.reason, { err: true });
          }
        } finally {
          this.tableWorking = [];
          this.busy = false;
        }
      },
      toast(text, opts = {}) {
        if (opts.err) text = this.friendly(text);
        const t = { id: ++this.toastSeq, text, err: !!opts.err, undo: opts.undo || null,
          keepAt: opts.keepAt || opts.undoAt, trackingUndo: !!opts.trackingUndo,
          onUndo: opts.onUndo || null, undoText: opts.undoText || "Undone" };
        if (t.undo) {
          this.toasts.filter((note) => note.undo).forEach((note) => clearTimeout(note.timer));
          this.toasts = this.toasts.filter((note) => !note.undo);
        }
        this.toasts.push(t); this.live = text + (t.undo ? " Undo is available." : "");
        if (!t.undo) this.armToast(t, t.err ? 7000 : 4000);
      },
      armToast(t, ms) {
        clearTimeout(t.timer);
        t.ms = ms;
        t.timer = setTimeout(() => { if (!t.held) this.toasts = this.toasts.filter((x) => x.id !== t.id); }, ms);
      },
      holdToast(t, held) {
        t.held = held;
        if (!held && !t.undo) this.armToast(t, Math.max(t.ms || 4000, 6000));
      },
      dismissToast(t) {
        clearTimeout(t.timer);
        this.toasts = this.toasts.filter((note) => note.id !== t.id);
      },
      leaveScreen(href) {
        this.screenVisit++;
        this.live = "";
        for (const note of this.toasts) {
          if (note.keepAt === href) {
            note.keepAt = null;
            this.live = note.text + (note.undo ? " Undo is available." : "");
          } else this.dismissToast(note);
        }
      },
      async runUndo(t) {
        if (this.busy) return;
        const visit = this.screenVisit;
        this.dismissToast(t);
        this.busy = true;
        try {
          await t.undo();
          await this.refresh();
          t.onUndo?.();
          if (visit === this.screenVisit) this.toast(t.undoText);
        } catch (e) {
          await this.refresh();
          t.onUndo?.();
          this.toast("Couldn't undo: " + e.message, { err: true });
        } finally { this.busy = false; }
      },
    },
  };
})();
