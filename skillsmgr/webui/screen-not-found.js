"use strict";

window.Jackfield.register((app) => {
  app.component("jf-not-found", {
    props: ["route", "places", "suggestion"],
    computed: {
      skillName() { return this.route.page === "skill" ? this.route.name : ""; },
      title() { return this.skillName ? "There’s no skill called " + this.skillName : "Page not found"; },
      address() { return this.route.href.slice(1, 400); },
      guessHref() { return this.suggestion ? window.Jackfield.router.skillHref(this.suggestion.name) : ""; },
    },
    template: "#jf-not-found-template",
  });
});
