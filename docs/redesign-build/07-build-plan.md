# Build Plan

**Version 1.0.0**

**AI manifest**: The redesign build as phases 0–8. Each phase lists its tasks
(with the files they touch), size, dependencies and exit criteria, and each
phase lands on `main` green before the next starts (BD-1). Sizes: S ≈ under
half a day, M ≈ one day, L ≈ two to three days of focused agent work including
tests. Screen detail: @docs/redesign-build/05-screens.md. Tests:
@docs/redesign-build/08-testing-and-acceptance.md.

## Working rules for every phase

**[SPEC]**

1. **One writer per file set.** `state.js`, `model.js`, `router.js`, `app.js`
   and `index.html` have one owner at a time. Screen files can run in parallel
   sessions (separate worktrees) only after phase 1, and only when each touches
   its own `screen-*.js` and adds its own actions to `state.js` in a separate,
   serialized commit.
2. **Each task ends green:** full unit suite on 3.11–3.14
   (memory: a green run on one interpreter proves nothing about the others),
   both smokes when their files changed, every gate, browser e2e locally, then
   CI.
3. **Contract tests move with the code.** The 12 test files that read the
   frontend today (listed in
   @docs/redesign-build/08-testing-and-acceptance.md) are rewritten for the new
   markup in the same commit that changes it. Never skip or delete a test to get
   to green; replace each assertion with its new-UI equivalent or record why it
   no longer applies.
4. **Both themes and the phone width in the same change** as the screen.
5. **Update `task.md` and `docs/06-progress-log.md`** after each task; run the
   hostile self-review in `AGENTS.md` against the diff before each commit.

## Phase 0 · Foundations (one change of look)

| # | Task | Files | Size |
|---|---|---|---|
| 0.1 | Re-check the 2026-11-24 High findings that are **not** UI-only on current `main` (History "No recorded changes" after a save; "Turned off 0" count; Contradiction check missing tabs vs spaces; AI "Connected" beside a refused connection). Fix the backend/model ones now; list the UI-only ones against the screen that fixes them | as found | M |
| 0.2 | Copy DS v13 `tokens.json` → `design/tokens.json` (name "Jackfield"); write `tools/gen_tokens.py`; generate `skillsmgr/webui/tokens.css` | new | S |
| 0.3 | Copy `bundle.css` → `skillsmgr/webui/system.css`; verify every agent-mark data URI and the `--ink-2, var(--ink2)` fallback; add `layout.css` skeleton | new | S |
| 0.4 | Alias every old custom property to its new token (`/* alias: remove in phase 7 */`) so all current screens switch palette at once; remove green (`ok`) as a meaning | `styles.css`, `tools.css` | M |
| 0.5 | Fonts: OFL licence file, Mono latin-ext `@font-face`, `unicode-range` everywhere | `tokens.css` (generated faces), `static/fonts/` | S |
| 0.6 | Logo: lockup in the header from `branding/jackfield/kit/svg/` (light + dark inline), favicon check | `index.html` | S |
| 0.7 | Agent marks from `system.css`; one scope-id → `data-a` table in `model.js`; retire `AGENT_ICONS` | `model.js`, `app.js` | S |
| 0.8 | Gates: rewrite `check_design_tokens.py` to read `design/tokens.json` + `tokens.css`; add `tests/test_css_token_references.py` (every `var()` resolves; no stray hex); extend `check_package_data.py` for new files and the licence; update `pyproject.toml` only if a glob is needed (it should not be: files are flat) | gates, tests | M |
| 0.9 | Rewrite `DESIGN.md` as a short guide from v13 (voice, status vocabulary, rules, where values live) with **no colour values** (Q3); update `docs/08-web-ui.md` "Design system" section | docs | S |

**Exit:** every page renders in the v13 palette and fonts in both themes; all
gates green; no undeclared `var()`; the old teal and bone appear nowhere.

## Phase 1 · Shell

| # | Task | Files | Size |
|---|---|---|---|
| 1.1 | `router.js`: routes and legacy redirects (table in 04); titles; Not found for unknown routes | `router.js`, `app.js` | M |
| 1.2 | `state.js` skeleton: move load/refresh/toast/undo out of `app.js`; `Jackfield.register` for components | `state.js`, `app.js` | L |
| 1.3 | `jf-nav` desktop header with four places, attention count, search field, theme, help; phone header + `sm-tabs` | `ui-core.js`, `index.html`, `layout.css` | M |
| 1.4 | `jf-undo-bar` (restyled toast; stays on its page; replaced by a newer change) | `ui-core.js` | S |
| 1.5 | `jf-notice`, `jf-title-row` + breadcrumb, `jf-empty`, `jf-placeholder`, `jf-sheet`, `jf-menu` | `ui-core.js` | M |
| 1.6 | S12 palette and header search (`palette.js`), fed by routes, actions and tools; switched-off groups excluded | `palette.js` | M |
| 1.7 | S13 Not found with Did you mean | `screen-*.js` | S |

**Exit:** every old hash lands on its new home; the old six-tab navigation is
gone; old pages still work inside the new shell (temporarily under their new
routes).

## Phase 2 · Hero: Skills table and side panel

| # | Task | Files | Size |
|---|---|---|---|
| 2.1 | `model.js`: `squareStatus`, `rowVerdict`, `attentionItems` + `tests/fixtures/square-status-cases.json` + both tests | `model.js`, tests | L |
| 2.2 | `jf-status`, `jf-square`, `jf-agent`, `jf-pills`, `jf-attention-banner` | `ui-table.js` | M |
| 2.3 | S1 table: toolbar, columns with header menu, rows, verdicts, Show 50 more, Only problems, grid keyboard model | `screen-skills.js`, `layout.css` | L |
| 2.4 | S2 panel: On, Off, Off in settings, Not here, Different (+ Compare / choose a version), Can't read; Working and Failed; Other places | `ui-table.js`, `ui-doc.js` | L |
| 2.5 | `state.change()` preview → act → confirm on disk → Undo, for toggle, add, make match, replace | `state.js` | M |
| 2.6 | Evenly split (camps, `is-camp` marking, confirm) and Unknown (ChecksGrid rows) | `ui-table.js` | M |
| 2.7 | States: first launch (A16 → A03 summary + tip), loading, no agents found, no agents tracked, no skills, no results, files changed + Refresh | `screen-skills.js` | M |
| 2.8 | Tracking doorways on S1: column header menu actions, S19 project picker, "Found Gemini" notice, broken-file notice, missing project notice | `screen-skills.js`, `screen-tracking.js` | M |
| 2.9 | Several rows at once: tick rows → batch preview → execute → one Undo | `screen-skills.js`, `state.js` | M |
| 2.10 | Retire Home and Sync map (routes redirect; their code deleted in phase 7) | `app.js`, `index.html` | S |

**Exit:** F2 benchmark passes in e2e by keyboard and mouse; the status case
table passes in the browser; 1,000 fixture skills stay usable; both themes.

## Phase 3 · Everyday jobs

| # | Task | Files | Size |
|---|---|---|---|
| 3.1 | S3 skill page: agent row (reuses `jf-square` + panel), Read / File text, details, sticky title row, Move to Trash | `screen-skill.js`, `ui-doc.js` | L |
| 3.2 | S4 editor: Save-to place rows with different-copy warning, Write / Preview, unsaved guard, changed-on-disk, Ctrl+S | `screen-skill.js`, `ui-forms.js` | L |
| 3.3 | S5 new skill: live name rules, place rows, templates, live preview, exists → Open it? | `screen-new.js`, `ui-forms.js` | M |
| 3.4 | S6 why isn't it running: ChecksGrid from `/api/doctor?explain=`, first failure → next step | `screen-skill.js`, `ui-doc.js` | M |

**Exit:** F1, F4, F5, F6 pass in e2e; reload keeps the editor.

## Phase 4 · Upkeep

| # | Task | Files | Size |
|---|---|---|---|
| 4.1 | S7 Needs attention: list and detail, fix choices, Skip, Fixed with Undo, J/K/F, empty state | `screen-attention.js` | L |
| 4.2 | S8 Trash & backups: one trash list with origin, restore, empty (no Undo, says so), recent changes, backup download and load with plan | `screen-trash.js` | M |
| 4.3 | Retire Inbox and Recovery | `app.js`, `index.html` | S |

**Exit:** F7, F8 pass; the header count equals S7's To fix count.

## Phase 5 · Advanced, Settings, What to track

| # | Task | Files | Size |
|---|---|---|---|
| 5.1 | S9 Advanced with the four goal groups and the agreed tool mapping (Q2) | `screen-advanced.js` | M |
| 5.2 | S10 template shell; move each of the 21 tools' bodies (plus the Doctor report page) into it (inputs, "What will be sent", result, folded raw reply, errors by their buttons); tool-off state | `screen-advanced.js`, `tool-center.js`, `ai-center.js`, `library-tools.js`, `ai-diagnostic.js` | L (split into 3–4 commits by group) |
| 5.3 | S11 Settings: What to track row, Look, AI connection (never Connected without a test), Upkeep | `screen-advanced.js` | M |
| 5.4 | S14–S19 restyle onto ListGrid, TablePreview, SidePanel confirm, Sheet; forms with live checks | `screen-tracking.js` | L |

**Exit:** no tool lost; T1–T9 pass; benchmarks "stop tracking Cursor" and
"add Kilo" pass in e2e.

## Phase 6 · Phone

| # | Task | Files | Size |
|---|---|---|---|
| 6.1 | One-agent table ("Showing: Codex ▾" + Manage agents), row → sheet, tab bar | `screen-skills.js`, `layout.css` | M |
| 6.2 | Every screen at 390 px: sticky Save, full-width sheet buttons, 44px targets | all screens | M |

**Exit:** phone e2e pass; no target under 44px; no horizontal scroll except
File text.

## Phase 7 · Removal and docs

| # | Task | Size |
|---|---|---|
| 7.1 | Delete old templates from `index.html`, dead code from `app.js`, `styles.css`, `tools.css`, alias lines, unused icons; gate fails on any `alias:` | M |
| 7.2 | `docs/08-web-ui.md` "The interface" rewritten for the four places; `DESIGN.md` final; `README.md` screenshots; `CHANGELOG.md` | M |
| 7.3 | `check_complexity.py` baseline update for removed functions (never raise the budget) | S |

**Exit:** no unused selectors (spot-checked with the e2e coverage run), no
undeclared tokens, docs gate green.

## Phase 8 · Acceptance

| # | Task | Size |
|---|---|---|
| 8.1 | Full ladder on 3.11–3.14, both smokes, all gates, CI on three OSes + e2e | S |
| 8.2 | Accessibility pass: keyboard-only through F1–F9 and T1–T9; screen reader spot checks (Orca on Linux, as in earlier release evidence); contrast from the gate | M |
| 8.3 | Visual check of every screen against its light and dark board at 1440 / 1280 / 1920 / 390 | M |
| 8.4 | Maintainer's own 20-minute test of five everyday tasks (requirements A14) | maintainer |
| 8.5 | `/ux-review`, then `/launch` (release gates in `task.md` still apply: PyPI as `jackfield`, trusted publisher) | — |

## Order and parallelism

**[SPEC]** Phases 0 → 1 → 2 are strictly sequential (shared files). After
phase 2, phases 3, 4 and 5 touch separate `screen-*.js` files and may run as
parallel sessions in their own worktrees, with `state.js` actions merged one at
a time. Phase 6 follows the screens it adapts; phase 7 starts only when every
old route redirects; phase 8 runs last on the merged tree.

## Size

**[NOTE]** Phases 0–7 hold 11 S + 22 M + 9 L tasks, about 45–55 working days
of focused agent effort with review (S ½, M 1, L 2–3 days). This is an estimate
from the task list, not a measured figure; phase 8 depends on the maintainer's
time.
