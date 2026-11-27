# Components

**Version 1.0.0**

**AI manifest**: The 18 design-system components (`sm-*` classes in
`system.css`, copied from DS v13 `components/bundle.css`) and the 7 product
compositions built from them. For each: anatomy, states, accessibility rules,
the screens that use it and the Vue component (or plain markup) that renders
it. The DS component READMEs on the artifact are the long form; this file is
what the build needs. Tokens are in @docs/redesign-build/02-design-system.md.

## Rules for every component

**[SPEC]**

- Read only token custom properties; no hex, no local `--x` copies of tokens.
- One primary button per screen. Focus ring: 2px `accent` on every button, link
  and field, never removed.
- A disabled control says why next to it, in words.
- Anything that opens over the page (sheet, confirm, palette, menu) moves focus
  to its heading or first field, closes with Esc, and returns focus to what
  opened it.
- Simple, stateless pieces stay plain markup with classes (Button, Field, Tag,
  Keycap). Pieces with state or keyboard logic are Vue components registered in
  `ui-*.js` files (BD-4), named `jf-<name>` in templates.

## Design-system components

| Component | Classes | Vue | Used by |
|---|---|---|---|
| Button | `sm-btn` + `--primary` `--accent` `--dark` `--quiet` `--icon` `--page` | markup | all |
| Field | `sm-field`, `sm-label`, `sm-hint`, `sm-textarea[--file]`, `sm-checkbox`, `sm-radio`, `sm-rule is-ok/is-fail`, `sm-sr` | markup; `jf-place-rows` for place rows | S1, S4, S5, S11, S16, S18 |
| Keycap + agent tile | `sm-kbd`; `sm-ag[data-a]`, `agm[data-a]` | `jf-agent` (tile or bare) | all |
| StatusMark | `sm-status is-*` + `sm-mk` | `jf-status` | S1, S2, S3, S7 |
| Square | `sm-square` (+ `aria-pressed`, `is-working`, `is-camp`) | `jf-square` | S1, S3 |
| AttentionBanner | `sm-banner`, `__title`, `__detail` | `jf-attention-banner` | S1 |
| SidePanel | `sm-panel`, `__name`, `__path`, `__line`, `__what`; `sm-pill`; `sm-camp`; `sm-ring` | `jf-side-panel` | S1, S3, S14 |
| UndoBar | `sm-undo`, `__x` | `jf-undo-bar` (one instance in the shell) | all |
| Navigation | `sm-nav`, `__link`, `__count`; `sm-logo`; `sm-tabs`, `sm-tab` | `jf-nav` | shell |
| Segmented | `sm-seg` | markup | S3, S4, S11 |
| Chip + Tag | `sm-chip`, `__box`; `sm-tag`, `sm-tag--quiet` | markup | S1 filters, S14 rows |
| Document | `sm-doc`; `sm-filetext` | `jf-document` | S3, S4 preview, S5 preview |
| ChecksGrid | `sm-chk is-ok/is-fail/is-unknown/is-skip`, `__ic` | `jf-checks-grid` | S6, S2 Unknown state |
| Compare | `sm-compare`, `__side[--new]`; `sm-choice`, `__snip` | `jf-compare`, `jf-choose-version` | S2 Different, S7, S10 AI results |
| ListGrid | `sm-list`, `__head`, `__count`, `__colhead`, `__cols`, `__row`, `__name`, `__status`, `__num`, `__btn`, `__foot` | `jf-list-grid` | S14 |
| TablePreview | `sm-preview`, `__corner`, `__hd`, `__name`, `__cell`, `__dot`, `__dash` | `jf-table-preview` | S14/S15 |
| Sheet | `sm-sheet`, `sm-sheet-scrim`, `sm-sheet__grab` | `jf-sheet` (wraps SidePanel content below 900px) | S2 phone, S14 phone |
| Placeholder | `sm-skel` | `jf-placeholder` | every loading state |

### Button

**[SPEC]** Six kinds. **Primary**: the side panel's one action, full width,
`control-lg`, may carry its keycap ("Space"). **Accent**: the compact primary
for a title row, card or footer ("Edit", "Save to 3 places", "Create in 2
places"); never on a screen that already shows a side-panel primary.
**Default**: outlined secondary; `aria-pressed` for toggles ("Show only these").
**Dark**: one strong secondary per area ("Fix one by one"). **Quiet**: rare or
risky ("Move to Trash", "Empty trash…"). **Icon**: `aria-label` always, 34px
desktop, 44px phone. Heights: title row/footer `control-page` 38px
(`sm-btn--page`); cards, panels, rows, toolbars `control` 36px. Confirms: a
change that only alters what is shown and has Undo makes the action primary
and the way back default ("Stop tracking Cursor" / "Keep tracking"); a dialog
guarding unsaved work makes the safe choice the accent ("Keep editing").

### Field

**[SPEC]** Single line: input inside its `label.sm-field` with an `sm-sr` name;
placeholders are examples, never the only label. Form label + one hint linked by
`aria-describedby`. Multi-line `sm-textarea` with a count when there is a limit.
File text `sm-textarea--file` (mono, spellcheck off). **Place rows** are the only
way to choose places (Editor "Save to", New skill "Add it to"): native checkbox,
agent tile, name, one line under it (folder or what happens there), stacked
vertically. Radio rows for one choice ("Showing in the table"); a choice that
cannot be made says why and is disabled. Live rules update as you type with a
hidden "Done:"/"Not yet:" prefix and a one-click fix when there is one. Errors
appear under the field in words.

### StatusMark and Square

**[SPEC]** `jf-status` takes a status key and renders mark + word; the mark is
`aria-hidden`. `jf-square` is a real `<button class="sm-square">`, at least
64px tall, `aria-label="<skill> in <agent>: <word>"`, `aria-pressed` when
selected (`accent-soft` fill, `accent` inset outline). It never shows a new
status until the change is confirmed on disk; while changing it is
`is-working` + `aria-busy="true"` and the other squares stay usable. Evenly
split squares read Version 1 / Version 2; hovering or focusing a version card
in the panel marks its squares `is-camp`. Keyboard: see the grid model in
@docs/redesign-build/04-frontend-architecture.md.

### AttentionBanner

**[SPEC]** Only when the count is above zero; at most one per page. 18px warning
triangle + `title-banner` in `warn` ("3 skills need your attention"), one detail
sentence naming agents and skills, "Show only these" (toggle) and "Fix one by
one" (dark, opens S7).

### SidePanel

**[SPEC]** Fixed order: agent tile + name → skill name (`title-panel`) → folder
(`path`) → one sentence (`body-lg`) → Now → After pills → primary button →
"What happens" (`mute`) → Other places (tile, name, StatusMark each) → links
(Open skill, Why isn't it running?). Up to 392px, pinned while the table
scrolls, `shadow-panel`. Below 900px the same content opens in `jf-sheet`. For a
status Jackfield cannot fix (Off in settings) the primary opens the place to fix
it and says so. States and their copy: **On, Off, Off in settings, Not here,
Different, Can't read** (A01 `panelFor`), **Evenly split, Unknown, Working,
Failed** (A15), and **as a confirm** on What to track (ATA-05). Each is listed
with its exact elements in @docs/redesign-build/05-screens.md.

### UndoBar

**[SPEC]** One inverted bar at the bottom centre (`toast`/`on-toast`,
`shadow-toast`, `role="status"`): past-tense sentence naming skill and agent,
Undo, dismiss. An available Undo has no time limit. Stays on the page where the change happened, never follows
navigation; a newer change replaces it. If a change cannot be undone, say so
**before** acting, never here.

### Navigation

**[SPEC]** Desktop `sm-nav` (60px): Jackfield lockup linking to Skills
(`aria-label="Jackfield"`), four links (current one underlined in `ink`,
`aria-current="page"`), attention count in `warn`, search box with "/" keycap,
theme and help icon buttons. Phone: 56px header with the lockup, search and New
skill as icon buttons; `sm-tabs` bottom bar with four 44px+ tabs, stroke icon +
label. Never a fifth place.

### Segmented

**[SPEC]** Two or three views of one thing (Read / File text; Write / Preview;
Light / Dark / Match my computer). `role="group"` + `aria-label`, current one
`aria-pressed="true"`. Switches views only, so no Undo.

### Chip and Tag

**[SPEC]** Chips are filter-like toggles (`aria-pressed`, tick box, optional
14px mark), grouped with a visible label. **Not** for choosing places. Tags label
a row that is not a control: `New` (`accent-soft`/`accent`) and quiet facts
(`Custom`, `Automatic`); at most two per row.

### Document

**[SPEC]** Rendered `sm-doc`: Markdown through the existing vendored
markdown-it renderer in `domain.js` (raw HTML stays inert, locked rule), `doc`
body, `title-doc` headings, under ~760px; the file's own top heading is not
repeated under the page title. File text `<pre class="sm-filetext">`: every
character of SKILL.md including the header.

### ChecksGrid

**[SPEC]** Checks down the side, places across: Found → Readable → Switched on
→ Settings allow it → Actually loaded. Cells `is-ok` (tick), `is-fail` (cross,
word in `bad` 600), `is-unknown` (dashed ring with "?"), `is-skip` (empty ring,
after a failure). Above the grid, the first failure becomes one next step with
one action. Legend always shown. "Actually loaded" is always Unknown (agents do
not report it).

### Compare

**[SPEC]** Now / Suggested side by side for proposed text (AI results); the
action names the target and ends in Undo. Choose a version: `sm-choice` buttons
with where each is used and what happens to the other, a few differing lines,
**nothing preselected**, action disabled with "Choose a version first". The
losing copy always goes to Trash.

### ListGrid, TablePreview, Sheet, Placeholder

**[SPEC]**

- **ListGrid** (S14): one card per section with head, count, optional
  definition of a number column, column head, rows (checkbox/radio, tile, name
  + status line, right-aligned tabular numbers, quiet Details), foot with the
  add button and its reassurance line. Rows ≥ 56px. `is-untracked`, `is-hot`,
  `is-pending` ("Waiting for you to confirm"; the checkbox keeps its old value).
  ≤ 640px: number columns fold into the status line. Numbers have hidden words.
- **TablePreview**: a few real rows drawn small in the panel, `aria-hidden`, with
  an `sm-sr` sentence beside it; `is-leaving` (hatched column), `is-gone` (struck
  rows), `is-hl` (lit column). Columns set inline
  `grid-template-columns: minmax(0,1fr) repeat(N, 34px)`.
- **Sheet**: below 900px, every panel opens as a bottom sheet over a scrim,
  `role="dialog"`, `aria-modal="true"`, ≤ 86% tall, grab bar, full-width
  buttons ≥ 44px.
- **Placeholder**: still blocks in `raise` sized like their text, rows keep
  their grid; `role="status"` with a plain label; shown only after ~300ms; no
  shimmer.

## Product compositions (not in the DS, built from it)

| Composition | Built from | Where | Notes |
|---|---|---|---|
| `jf-title-row` | `title-page` + one Accent/Default action + optional breadcrumb | every page | Breadcrumb `aria-label="Breadcrumb"` on pages below Skills or Advanced ("Skills / test-driven-development / Edit"); pinned on long pages (S3, S4) |
| `jf-notice` | `accent-soft` banner, body text, one action, dismiss | S1 files-changed, first-launch tip, "Found Gemini" notice, broken tracking file | Never more than one notice and one attention banner at once |
| `jf-menu` | menu button + `role="menu"` list | S1 column header menu, project picker S19, phone "Showing: Codex ▾" | Arrow keys, Esc, disabled items say why |
| `jf-palette` | Field + grouped results + keycap hints | S12 | Skills, then actions, then pages |
| `jf-pills` | `sm-pill` Now → After | S2, S15 | After struck through on Failed; dimmed on Working |
| `jf-camp` | `sm-camp` card | S2 Evenly split | One per version, "Keep version N" |
| `jf-empty` | `title-banner` + one sentence + one action | every empty state | Says what was checked and when |
