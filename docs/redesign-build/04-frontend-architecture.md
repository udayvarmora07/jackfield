# Frontend Architecture

**Version 1.0.0**

**AI manifest**: How the redesign is structured in `skillsmgr/webui/` without a
build step: files and load order, routes and legacy redirects, shared state,
the rules that turn API data into square words, Undo, change detection,
keyboard model, performance at 1,000 skills, theming and breakpoints. Current
code facts were read on 2026-11-27 (`app.js` 124 KB, `index.html` 92 KB,
`model.js` 41 KB, `tool-center.js` 108 KB, `ai-center.js` 139 KB).

## Constraints that shape the code

**[SPEC]**

- Vue 3.5.13 global build (runtime + compiler), vendored and sha256-pinned
  (SEC-9). Templates compile in the browser; CSP keeps `script-src 'self'
  'unsafe-eval'` (SEC-4, already documented). No `.vue` files and no SFC loader:
  a runtime loader would be a new dependency.
- Plain `<script>` files, no modules, no bundler. Each file attaches to one
  global namespace (`window.Jackfield`) or registers components on the app.
- Files stay **flat in `skillsmgr/webui/`**: `pyproject.toml` ships `webui/*`
  (one level) and `check_package_data.py` asserts the exact member set.
- `check_complexity.py` ratchets function complexity (new functions ≤ 15).
  Keep template logic in small computed properties and methods.
- `domain.js` (transport, formatting, frontmatter, Markdown) loads before
  everything that uses it; it stays the only place that calls `fetch`.

## Files

**[SPEC]** Target layout at the end of phase 7 (sizes are budgets, not limits):

| File | Holds | Replaces |
|---|---|---|
| `index.html` | `<head>`, the root `<div id="app" class="sm-root">`, the shell markup only (header, main outlet, Undo bar, sheet host) | the 92 KB in-DOM template |
| `tokens.css`, `system.css`, `layout.css` | Tokens, components, page layout | `styles.css`, `tools.css` |
| `preferences.js` | Theme, text size, date format before first paint (exists; keep) | — |
| `domain.js` | Transport, formatting, Markdown (exists; keep) | — |
| `model.js` | Pure functions: agents, copies, grouping, reference, `squareStatus`, `rowVerdict`, `attentionItems` (exists; extend) | — |
| `state.js` | One `Vue.reactive` app state + actions that call `domain.js` (load, refresh, toggle, sync, create, save, trash, restore, tracking) | state and workflows spread through `app.js` |
| `router.js` | `parseRoute`, `routeHref`, legacy redirects, title per route | `parseRoute` in `app.js` |
| `ui-core.js` | `jf-agent`, `jf-status`, `jf-placeholder`, `jf-empty`, `jf-notice`, `jf-title-row`, `jf-menu`, `jf-sheet`, `ic` | parts of `app.js` |
| `ui-table.js` | `jf-square`, `jf-side-panel`, `jf-pills`, `jf-camp`, `jf-attention-banner`, `jf-table-preview` | — |
| `ui-forms.js` | `jf-place-rows`, `jf-live-rules`, unsaved-changes guard | — |
| `ui-doc.js` | `jf-document`, `jf-checks-grid`, `jf-compare`, `jf-choose-version` | parts of `app.js`, `ai-diagnostic.js` |
| `screen-skills.js` | S1 + S2, first launch, states, project picker, column header menu | Home, Skills shelf, Sync map |
| `screen-skill.js` | S3, S4, S6 | Skill reader, editor, explain |
| `screen-new.js` | S5 | New skill dialog |
| `screen-attention.js` | S7 | Inbox |
| `screen-trash.js` | S8 | Recovery |
| `screen-advanced.js` | S9, the S10 shell, S11 | Tools hub, settings tool |
| `screen-tracking.js` | S14–S19 (moves today's tracking mixin out of `app.js`) | tracking page |
| `palette.js` | S12 search and command palette | header search + palette in `app.js` |
| `tool-center.js`, `ai-center.js`, `library-tools.js`, `ai-diagnostic.js` | Each tool's **body** (inputs, calls, results), rendered inside the S10 shell | their own page chrome |
| `app.js` | `createApp`, mounts the shell, registers routes → screen components | everything else it does today |

**[SPEC]** Load order: `preferences.js` (in `<head>`) → vendor Vue →
markdown-it → `domain.js` → `model.js` → `state.js` → `router.js` → `ui-*.js` →
`screen-*.js` → `palette.js` → tool bodies → `app.js`. A component file only
calls `Jackfield.register(app => app.component(…))`; `app.js` runs the
registrations after `createApp`, so order inside the `ui-`/`screen-` group does
not matter.

## Routes

**[SPEC]** Hash routes (BD-3). `router.js` is the only code that reads or writes
`location.hash`.

| Route | Screen | Notes |
|---|---|---|
| `#/skills` | S1 Skills table | Query: `?q=`, `?only=problems`, `?agent=<id>` (phone focus), `?sel=<name>:<agent>` (selected square) — so reload keeps the panel |
| `#/skills/<name>` | S3 Skill page | `?view=file` for File text |
| `#/skills/<name>/edit` | S4 Editor | Reload keeps the editor (F5) |
| `#/skills/<name>/why` | S6 Why isn't it running? | |
| `#/new` | S5 New skill | `?template=<id>` |
| `#/attention` | S7 Needs attention | `?item=<id>` |
| `#/trash` | S8 Trash & backups | |
| `#/advanced` | S9 Advanced | |
| `#/advanced/<tool-id>` | S10 tool page | Tool ids unchanged (`install`, `quality`, `ai-concise`, …) |
| `#/settings` | S11 Settings | |
| `#/settings/tracking` | S14 What to track | `/add-agent`, `/add-project`, `/agent/<id>` exist today; keep |
| anything else, or a missing skill | S13 Not found | Missing skill: "There's no skill called …" + close-name suggestions |

**[SPEC]** Legacy redirects (replace, do not push, history):

| Old | New |
|---|---|
| `#/home`, `#/`, empty | `#/skills` |
| `#/map` | `#/skills` |
| `#/inbox` | `#/attention` |
| `#/recovery` | `#/trash` |
| `#/tools` | `#/advanced` |
| `#/tools/settings` | `#/settings` |
| `#/tools/<id>` | `#/advanced/<id>` |
| `#/skill/<name>` | `#/skills/<name>` |

**[NOTE]** A skill can legally be named `new`, `edit` or `why`. `#/new` is
top-level, and `#/skills/<name>/<sub>` only treats the **third** segment as a
sub-page, so `#/skills/new` is the skill called "new".

## State

**[SPEC]** `state.js` exports one reactive object and actions. Screens read it
and call actions; they never call `fetch` directly.

| Key | Source | Refreshed |
|---|---|---|
| `skills` (copies) | `GET /api/skills?scope=all&body=0` | load, Refresh, after every write, on change detection |
| `scopes` | `GET /api/scopes` | load, after tracking changes |
| `tracking` | `GET /api/tracking` | load, after `PUT /api/tracking` |
| `bodies` | `GET /api/skills/<name>?scope=…` via the existing `ensureBodies` cache | on demand |
| `history` | `GET /api/history?limit=…` | S3 details, S8 recent changes |
| `trash` | `GET /api/trash` | S8 |
| `undo` | the last change's inverse action (BD-7) | per change |
| `busy` | per-square `Set` of `name:agent` keys being changed | per change |
| `prefs` | `preferences.js` (theme, text size, dates) | on change |

Derived (pure, in `model.js`): `agents` (tracked columns in display order),
`rows` (one per skill name), `squareStatus`, `rowVerdict`, `attentionItems`,
`attentionCount`.

## Square status rules

**[SPEC]** One pure function, `squareStatus(row, agent)`, returns one key. It is
the product promise, so it is tested from one shared case table,
`tests/fixtures/square-status-cases.json` (input copies + expected key per
square): the browser e2e job loads `model.js` in the page and asserts every
case, and `tests/test_square_status_cases.py` (stdlib) asserts the table covers
every key and every precedence pair below. Evaluate in this order; the first
match wins:

| # | Key | When |
|---|---|---|
| 1 | `working` | `busy` holds this square |
| 2 | `missing` (Not here) | No copy of this skill in this agent's folders |
| 3 | `unreadable` (Can't read) | The copy exists but cannot be read as text: broken link, unaddressable name, invalid UTF-8, read error (today's `BROKEN_WHY` cases) |
| 4 | `version-1` / `version-2` | The readable copies split evenly between two `content_hash` values (no majority) and this copy holds the first / second |
| 5 | `different` | A majority `content_hash` exists among readable copies in tracked places and this copy differs from it |
| 6 | `off` | The file is switched off by Jackfield (`SKILL.md.disabled`) |
| 7 | `settings` (Off in settings) | Switched on, and a settings source Jackfield read for this agent declares it disabled (`native_state.sources[].declared == "disabled"`, or Claude Code's `observed_setting`) |
| 8 | `unknown` | Switched on, but a settings source for this agent exists and could not be read or parsed (`status` not `ok`/`missing`/`unobserved`) |
| 9 | `on` | Everything above was checked and passed |

**[SPEC]** Consequences that must hold:

- A copy that is both off **and** different shows `different` (content truth
  first); its panel says it is also switched off. Same for Version 1/2.
- `native_state.effective_state` is always `unknown` and "Actually loaded" is
  never claimed; that is S6's last check, not a square word.
- **Agents with no settings reader** (Cursor, custom agents): rule 7 and 8
  cannot fire, so they show **On** when rules 1–6 pass (decided 2026-11-27,
  Q1). The panel's details say "Cursor's own settings aren't checked" and S6
  shows "Settings allow it" as Unknown for them. Keep the choice in one named
  constant so it stays easy to change.
- Only **tracked** agents and the **showing** project are columns; the server
  already filters (`tracking.py` overlay), and the client never re-adds them.

**[SPEC]** `rowVerdict(row)` (the line under each skill name) follows A01's
`verdict()`: first Can't read ("Codex's file can't be read"), then Different
("Codex has a different copy"), then settings ("Off in Claude Code settings"),
then "Off everywhere", "On in 3, off in 1", else "Same copy in 4 places".

**[SPEC]** `attentionItems` = every Can't read square + every Different square +
every evenly split skill (one item per skill). This matches A01 ("3 skills need
your attention": two Different, one Can't read). Off in settings is shown on its
square and checked in S7's empty-state sentence but is not an item (decided
2026-11-27, Q4).

## Change, preview, Undo

**[SPEC]** Every write follows the same sequence, implemented once in
`state.js` `change(kind, target)`:

1. **Preview** in the side panel or page: Now → After, "What happens", the
   exact places. Nothing written yet.
2. **Act**: square(s) go `working`; call the existing route.
3. **Confirm on disk**: re-read the affected copies (`GET /api/skills?…` or the
   route's response) and only then show the new word.
4. **Undo bar**: past-tense sentence + Undo that runs the inverse (BD-7:
   toggle back, restore from Trash, PUT the previous tracking document, restore
   the replaced copy from Trash). Undo also re-reads before showing its result.
5. **Failure**: the square returns to its true word; the panel shows Failed
   with the reason in plain words and "Technical details" folded.

**[SPEC]** A change that cannot be undone (Empty trash, delete forever) says so
in its confirm before acting and never shows an Undo bar.

## Change detection ("files changed on disk")

**[SPEC]** Today the app re-reads on `visibilitychange` (at most every 15 s,
never while editing). Keep that and add: on each re-read, compare
`(scope, name, content_hash, enabled)` tuples with the previous list; if any
differ and the user did not cause them, show the S1 notice "2 skills changed on
disk since this page loaded. Refresh" instead of silently swapping rows. Refresh
applies the new list and marks changed rows for a few seconds. In the editor the
same signal becomes "This skill was changed outside the app. Compare before
saving?". No new endpoint: the list call already returns `content_hash`. A
background interval (e.g. 60 s while visible) is optional and must use
`body=0`.

## Keyboard model

**[SPEC]**

| Where | Keys |
|---|---|
| Anywhere | `/` focus search; Ctrl/Cmd+K palette; Esc closes the top overlay |
| Skills table | APG data-grid model: one tab stop into the grid, roving `tabindex`; ↑ ↓ ← → move between squares (and to the skill-name cell at column 0); Home / End row start/end; Space runs the panel's primary when it is a toggle or add; Enter opens the skill (on a name) or focuses the panel's primary (on a square) |
| Side panel | Tab order follows the fixed panel order; Esc returns focus to the square |
| Needs attention | J / K next and previous item; F fix (A08 hint line) |
| Palette | ↑ ↓ move, Enter open, Esc close (A13 hint line) |
| Editor | Ctrl/Cmd+S save to the ticked places (only when valid) |

**[NOTE]** The squares are buttons inside grid cells; arrow keys move between
them and are not used inside them, which keeps the APG grid pattern simple.

## Performance

**[SPEC]**

- First paint uses `body=0`; bodies load lazily (existing `ensureBodies`).
- The table renders 50 rows, then "Show 50 more" (approved in round 3); filter
  and "Only problems" work on the whole list. 1,000 skills × 8 columns = 8,000
  squares at most when fully expanded; each square is one button with no
  per-square watchers (compute rows once per list change, `markRaw` records).
- Placeholders appear only after 300 ms, so fast loads never flash.
- Budgets checked by `tests/test_performance_frontend.py` and the e2e job:
  table interactive under 1.5 s with 1,000 fixture skills on CI hardware; a
  square toggle round-trip under 300 ms with the local server.

## Theming and text size

**[SPEC]** `preferences.js` sets `data-theme="light|dark"` on `<html>` before
first paint (system preference when the setting is "Match my computer") and a
text-size class. `tokens.css` defines light on `:root` and dark on
`[data-theme="dark"]`. Inline both logo cuts and let the theme pick. Every
screen is built and checked in both themes in the same change.

## Breakpoints

**[SPEC]**

| Width | Layout |
|---|---|
| ≥ 1280 (design 1440, check 1920) | Header 60px, page margins `space-10`, table + pinned 392px side panel, gap `space-6` |
| 900–1279 | Same, narrower table; the side panel stays beside the table |
| < 900 | Side panel content opens as a Sheet |
| ≤ 640 | ListGrid folds number columns into the status line |
| ≤ 600 (phone, design 390) | 56px header, bottom tab bar, the table shows one agent ("Showing: Codex ▾"), tapping a row opens the skill page, every target ≥ 44px |

**[NOTE]** The DS gives 900px (Sheet) and 640px (ListGrid). The phone cut-over
at 600px is this spec's choice; adjust only if a phone board breaks at a real
device width between 600 and 900.
