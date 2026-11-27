/* Shared app state, registration and existing read/Undo workflows. */
"use strict";

(function () {
  const { api } = window.SkillManagerDomain;
  const Model = window.SkillsV2Model;
  const { markRaw } = Vue;
  const registrations = [];

  window.Jackfield = {
    register: (register) => registrations.push(register),
    install: (app) => registrations.forEach((register) => register(app)),
    // Vue makes this contribution reactive as part of the one root data object.
    createState: () => ({
      refreshGen: 0, m: null, loading: true, loadError: "", history: [], historyError: "",
      records: [], scopes: [], busy: false, toasts: [], live: "", toastSeq: 0,
    }),
    stateActions: {
      async refresh() {
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
          this.scopes=markRaw(scopes);this.records=markRaw(records);
          this.m = markRaw(Model.build(records, scopes, { suggested: 100 }));
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
          if (gen === this.refreshGen) this.loadError = this.friendly(e.message || "The skills could not be read.");
        } finally { if (gen === this.refreshGen) this.loading = false; }
      },
      toast(text, opts = {}) {
        if (opts.err) text = this.friendly(text);
        const t = { id: ++this.toastSeq, text, err: !!opts.err, undo: opts.undo || null,
          undoAt: opts.undoAt, trackingUndo: !!opts.trackingUndo,
          onUndo: opts.onUndo || null, undoText: opts.undoText || "Undone" };
        if (t.undo) {
          this.toasts.filter((note) => note.undo).forEach((note) => clearTimeout(note.timer));
          this.toasts = this.toasts.filter((note) => !note.undo);
        }
        this.toasts.push(t); this.live = text + (t.undo ? " Undo is available." : "");
        this.armToast(t, t.undo ? 20000 : (t.err ? 7000 : 4000));
      },
      /* WCAG 2.2.1: a toast with an action never times out while the reader is
       * on it; it waits until focus and pointer leave, then gets its time again. */
      armToast(t, ms) {
        clearTimeout(t.timer);
        t.ms = ms;
        t.timer = setTimeout(() => { if (!t.held) this.toasts = this.toasts.filter((x) => x.id !== t.id); }, ms);
      },
      holdToast(t, held) {
        t.held = held;
        if (!held) this.armToast(t, Math.max(t.ms || 4000, 6000));
      },
      dismissToast(t) {
        clearTimeout(t.timer);
        this.toasts = this.toasts.filter((note) => note.id !== t.id);
      },
      leaveUndo(href) {
        for (const note of this.toasts.filter((item) => item.undo)) {
          if (note.undoAt === href) note.undoAt = null;
          else this.dismissToast(note);
        }
      },
      async runUndo(t) {
        if (this.busy) return;
        this.dismissToast(t);
        this.busy = true;
        try { await t.undo(); await this.refresh(); if (t.onUndo) t.onUndo(); this.toast(t.undoText); } catch (e) { await this.refresh(); if (t.onUndo) t.onUndo(); this.toast("Couldn't undo: " + e.message, { err: true }); } finally { this.busy = false; }
      },
    },
  };
})();
