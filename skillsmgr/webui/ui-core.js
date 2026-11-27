/* Shared shell components. App-specific transitions are handled by app.js. */
"use strict";

window.Jackfield.register((app) => {
  app.component("jf-nav", {
    props: ["activePlace", "attention", "themeLabel", "themeIcon", "blocked"],
    emits: ["search", "theme", "help"],
    data: () => ({ places: window.Jackfield.palette.places }),
    template: "#jf-nav-template",
  });
  app.component("jf-sheet", {
    props: ["labelledBy"],
    template: '<div class="dlg" role="dialog" aria-modal="true" :aria-labelledby="labelledBy" tabindex="-1"><slot></slot></div>',
  });
  app.component("jf-undo-bar", {
    props: ["notes", "blocked", "busy"],
    emits: ["hold", "undo", "dismiss"],
    template: "#jf-undo-template",
  });
  app.component("jf-title-row", {
    props: ["title", "breadcrumb"],
    template: '<header class="jf-title-row"><p v-if="breadcrumb" class="sm-hint">{{ breadcrumb }}</p><h1 id="h1" tabindex="-1">{{ title }}</h1><slot></slot></header>',
  });
  app.component("jf-empty", {
    template: '<div class="jf-empty"><slot></slot></div>',
  });
  app.component("jf-notice", {
    props: { error: Boolean },
    template: '<div class="state-note" :class="{ err: error }" :role="error ? \'alert\' : \'status\'"><slot></slot></div>',
  });
  app.component("jf-placeholder", {
    data: () => ({ show: false, timer: null }),
    mounted() { this.timer = setTimeout(() => { this.show = true; }, 300); },
    beforeUnmount() { clearTimeout(this.timer); },
    template: '<div class="jf-placeholder rooms" aria-hidden="true"><div v-if="show" class="skeleton"></div><div v-if="show" class="skeleton"></div><div v-if="show" class="skeleton"></div></div>',
  });
  app.component("jf-menu", {
    props: ["label"],
    template: '<details class="jf-menu"><summary>{{ label }}</summary><div class="jf-menu-items"><slot></slot></div></details>',
  });
});
