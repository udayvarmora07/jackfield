# Redesign Build Spec — Jackfield design system v13 and the new UI

**Version 1.0.0**

**AI manifest**: Entry point for building the approved redesign ("Paper", one
table of truth) into `skillsmgr/webui/`. Written 2026-11-27 from the design
system artifact v13, the canvas v58 (copied byte-for-byte to `designs/final/`),
`requirements.md`, `ux-brief.md`, `design-brief.md`, `ui-progress.md` and the
2026-11-26 handoff package, checked against the current code. The detailed
spec lives in @docs/redesign-build/README.md and its nine numbered files. Read
this page first, then only the file your task needs.

## What this is

**[SPEC]** The redesign is approved and not built. `main` ships the earlier v2
interface (bone ground `#f2f3f1`, teal `#0d6a63`, six pages: Home, Skills, Sync
map, Inbox, Recovery, Tools) with Agent tracking added to it (`78cc21b`, option A,
"fit shipped UI"). This spec turns the approved design into a phased build that
keeps every locked rule in `AGENTS.md` and ends with the old look and the old
page structure gone.

**[SPEC]** The outcome, in one line: **one Skills table** where skills are rows,
tracked agents are columns and every square says in one plain word whether that
agent has the skill, whether it is on and whether it is the same copy, plus one
search (`/`, Ctrl+K), one quiet "Needs attention" count, one trash and an
Advanced area for everything else.

## Sources of truth, highest first

| # | Source | Holds | Where |
|---|---|---|---|
| 1 | Design system **v13** (artifact) | Tokens, type, components (`sm-*`), status vocabulary, voice, icon and logo rules | `design/tokens.json` and the Phase 0 component export. [Claude design system](https://claude.ai/artifact/27HHwcNGwDAZ2cne6xW4ei#shadows) |
| 2 | Approved boards, canvas **v58** | Layout, copy, states and behaviour of every screen | `designs/final/light/` and `designs/final/dark/` (25 + 25 `.dc.html`). The export README records four boards with normalized sample home paths. [Claude UI and UX canvas](https://claude.ai/artifact/2bRpEoQ192WY2Tp7dYsXdq#page-dcb81aee8d83) |
| 3 | Briefs | Flows F1–F9, T1–T9, screen inventory S1–S19, the tracking backend contract | `ux-brief.md`, `design-brief.md`, `requirements.md`, `ui-progress.md` (repository root; the last two committed 2026-11-27, Q8) |
| 4 | This spec | How to build it here: files, routes, data, phases, tests | `docs/redesign-build/` |
| 5 | Handoff package 2026-11-26 | Decisions log and history | `handoff/` (untracked). **Stale where it disagrees with 1–2**: it describes DS v11, 14 screens and "Skills Manager" |

**[NOTE]** Where an Agent tracking board (`ATA-*`/`ATD-*`) changes a main screen
(S1, S9, S10, S11), the Agent tracking board is the current one
(`designs/final/README.md`).

## Reading order

| Step | File | Read when |
|---|---|---|
| 1 | @docs/redesign-build/01-sources-and-decisions.md | Before any work: what is settled, what is stale, the decisions this spec makes and the ones it needs from the maintainer |
| 2 | @docs/redesign-build/02-design-system.md | Tokens, fonts, icons, agent marks, logo, status vocabulary, the token pipeline and gates |
| 3 | @docs/redesign-build/03-components.md | Building or reviewing any `sm-*` component |
| 4 | @docs/redesign-build/04-frontend-architecture.md | Files, load order, routes, state, the square-status rules, Undo, change detection, keyboard, performance |
| 5 | @docs/redesign-build/05-screens.md | Building one screen: route, board, layout, states, actions and acceptance |
| 6 | @docs/redesign-build/06-backend-and-api.md | Wiring a screen to data; what exists and what is missing |
| 7 | @docs/redesign-build/07-build-plan.md | Choosing the next task; phases, order, sizes and exit criteria |
| 8 | @docs/redesign-build/08-testing-and-acceptance.md | Proving a phase is done |
| 9 | @docs/redesign-build/09-open-questions-and-risks.md | Before a decision that is not settled here |

## Locked rules this build keeps

**[SPEC]** From `AGENTS.md`, unchanged: the filesystem is the source of truth;
SQLite schema and `SCHEMA_VERSION` unchanged; CLI stdlib-only; web UI stdlib
backend, **no build step**, no new runtime dependencies, Vue vendored, binds
127.0.0.1; no new CLI commands or Store methods without approval. The redesign
is a frontend rebuild. Its plan needs **no new backend routes** (see
@docs/redesign-build/06-backend-and-api.md); anything that turns out to need one
stops and asks first.

## Phases at a glance

| Phase | Delivers | Exit |
|---|---|---|
| 0 Foundations | Tokens from DS v13, `tokens.css` + `system.css`, fonts with OFL, logo, agent marks, gates rewritten, old token names aliased so the **whole app changes look in one commit** | All gates green; every page renders in the new palette |
| 1 Shell | Header, four places, phone tab bar, router with legacy redirects, search (S12), Undo bar, banners, theme, Not found (S13) | Every old link lands on its new home |
| 2 Hero | Skills table S1 + side panel S2, all square states, first launch (A16), states board (A03), side-panel states (A15), project picker, column header menu | Benchmark F2 in under 2 minutes, no wrong status |
| 3 Everyday jobs | Skill page S3, Editor S4, New skill S5, Why isn't it running S6 | F1, F4, F5, F6 pass in e2e |
| 4 Upkeep | Needs attention S7, Trash & backups S8 | F7, F8 pass; Sync map and Inbox routes retired |
| 5 Advanced | Advanced S9, tool page template S10 for every tool, Settings S11, What to track S14–S19 restyled | No tool lost; T1–T9 pass |
| 6 Phone | 390 px layouts, sheets, one-agent table | Phone e2e and touch targets |
| 7 Removal and docs | Old CSS, templates and code paths deleted; `DESIGN.md`, `docs/08-web-ui.md` rewritten | No dead selectors, no undeclared tokens |
| 8 Acceptance | Full ladder, a11y, visual check against boards, maintainer's 20-minute test, `/ux-review` | Definition of done met |

Details, sizes and dependencies: @docs/redesign-build/07-build-plan.md.

## Definition of done (whole build)

**[SPEC]** The build is done when all of these hold on the current tree:

1. Every screen in @docs/redesign-build/05-screens.md matches its light and dark
   board in layout, copy and states, and its acceptance list passes.
2. No square ever shows On, and no connection shows Connected, unless it was
   checked (the rules in @docs/redesign-build/04-frontend-architecture.md).
3. Every change to another agent's files shows a preview first and ends in the
   Undo bar.
4. Benchmarks pass in e2e: turn off `code-review` in Codex; stop tracking
   Cursor; add agent "Kilo" at `~/.kilo/skills`.
5. WCAG 2.2 AA in both themes; keyboard-only use of every flow; 1,000 skills
   usable; 390 px works.
6. The full test ladder passes on Python 3.11–3.14, both smokes, every gate,
   CI on ubuntu, macOS and Windows, and the browser e2e job.
7. The old palette, the six old page names and their routes are gone from the
   product (legacy hash routes redirect).
8. `DESIGN.md`, `docs/08-web-ui.md`, `task.md` and the progress log describe
   what shipped.
