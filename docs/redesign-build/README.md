# Redesign Build — file index

**Version 1.0.0**

**AI manifest**: Index of the redesign build spec. The overview, sources of
truth, phases and definition of done are in
@docs/61-redesign-build-spec-2026-11-27.md. Each file below answers one kind of
question; load only the one your task needs.

| File | Answers |
|---|---|
| @docs/redesign-build/01-sources-and-decisions.md | What is settled, what is stale, which decisions this spec makes, which it needs from the maintainer |
| @docs/redesign-build/02-design-system.md | Every token value, fonts, icons, agent marks, logo, status vocabulary, the token pipeline, `DESIGN.md` and the gates |
| @docs/redesign-build/03-components.md | The 18 `sm-*` components and 7 product compositions: anatomy, states, accessibility, which screens use them, the Vue component that renders each |
| @docs/redesign-build/04-frontend-architecture.md | Files and load order, routes and redirects, app state, the square-status rules, Undo, change detection, keyboard, performance, theming, breakpoints |
| @docs/redesign-build/05-screens.md | Every screen (S1–S19, side-panel states, first launch): route, boards, layout, states, actions, acceptance |
| @docs/redesign-build/06-backend-and-api.md | Which existing API serves each action, what the UI derives, and the gaps |
| @docs/redesign-build/07-build-plan.md | Phases 0–8 with tasks, files, sizes, dependencies and exit criteria |
| @docs/redesign-build/08-testing-and-acceptance.md | Test strategy, the contract tests to rewrite, e2e scenarios, visual and accessibility checks, per-screen definition of done |
| @docs/redesign-build/09-open-questions-and-risks.md | Open questions with a recommended answer and an owner; risks with mitigations |

**[NOTE]** Screen numbers (S1…S19), flows (F1…F9, T1…T9) and assumptions
(A1…A21, B1…B11) are the ones in `ux-brief.md` and `requirements.md`. Board
codes (A01…A16, ATA-01…09, and the dark D…/ATD… twins) are the files in
`designs/final/`.
