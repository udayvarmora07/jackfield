# Screens

**Version 1.0.0**

**AI manifest**: Every screen of the redesign: route, boards (light / dark),
what it replaces, content in order, states, actions with the API they call, and
acceptance. Exact copy is in the boards (`designs/final/<light|dark>/*.dc.html`:
the visible text is in the template, and the data and per-state wording are in
the board's script, e.g. A01's `panelFor()` and `verdict()`); quote them, don't
paraphrase. Data and API detail: @docs/redesign-build/06-backend-and-api.md.
Status rules: @docs/redesign-build/04-frontend-architecture.md.

## How to read a board

**[SPEC]** Open a board in the canvas's Play mode, or read the file: the
`<x-dc>` template shows layout and static copy, `{{ … }}` holes are filled by
the script's data (`AGENTS`, `ROWS`, `LABEL`, `panelFor`, …). Boards load Google
Fonts and use local token names (`--acc`, `--line2`): never copy either (map
names with the table in @docs/redesign-build/02-design-system.md). Each board
has a dark twin (A→D, ATA→ATD) with the same content.

## Shell (every screen)

**[SPEC]** Header (`jf-nav`), optional global notice row, main outlet, one Undo
bar, one sheet host. Every page has exactly one `title-page` title in a title
row that holds its one main action; pages below Skills or Advanced show a
breadcrumb. Reading width under ~760px for text pages. Messages never follow
the user to another page.

---

## S1 · Skills table (hero)

- **Route:** `#/skills` · **Boards:** A01/D01 (hero), **ATA-01/ATD-01 (current,
  with tracking doorways)**, A03/D03 (states), A16/D16 (first launch) ·
  **Replaces:** Home, Skills shelf, Sync map.
- **Content, top to bottom:** title row "Skills" + "142 skills in 5 places" +
  New skill (default, `control-page`); notices (tracking file broken; showing
  project missing; "Found Gemini (14 skills). Track it?"); AttentionBanner (only
  if count > 0); toolbar: filter field ("Filter by name or what it does", `/`
  hint), "All places" focus menu, sort ("A to Z"), project picker ("Project:
  api ▾", S19), "Showing N of M"; table: skill column (name 14/600, one-line
  description 13 `mute`, row verdict 12/500) + one column per tracked agent
  (tile, name, folder path; header menu ▾); squares; "Show 50 more"; keyboard
  hint line; side panel (S2) pinned at the right.
- **Column header menu (ATA-01):** "Stop tracking Cursor…" (opens the S15
  confirm in the panel), "Cursor details" and "Manage agents" (open S14 with
  Details open). Disabled on the last tracked agent with "At least one agent
  stays tracked." The Shared folder column says "Shown while Claude Code and
  Codex read it. It has no switch of its own."
- **States:** first launch (A16 scanning "Looking for your agents…", then A03
  "Found 3 agents and 142 skills" with per-agent counts and the one tip "Click
  any square in the table to turn a skill on or off for that agent." + "Show my
  skills"); loading placeholders ("Reading skill folders…"); no agents found
  ("No agent skills found yet" + where we looked + Add a folder / Look again);
  no agents tracked ("No agents are tracked." + Choose agents); no skills; no
  results ("No skills match this filter." + Clear filters + close names);
  files changed (notice + Refresh, changed rows marked then fading);
  1,000 rows ("Show 50 more"); Only problems (`Show only these` pressed).
- **Actions → API:** load `GET /api/skills?scope=all&body=0`, `GET /api/scopes`,
  `GET /api/tracking`; Track (notice) `PUT /api/tracking`; everything else
  happens in S2.
- **Acceptance:** benchmark F2 (find `code-review`, turn it off in Codex only) in
  under 2 minutes for a newcomer, by keyboard and by mouse; every square word
  follows the status rules; untracked agents never appear; filter and Only
  problems keep the selected square when it is still shown; both themes; 1,000
  fixture skills usable.

## S2 · Square side panel

- **Boards:** A01 (On, Off, Off in settings, Not here, Different, Can't read via
  `panelFor`), **A15/D15** (Evenly split, Unknown, Working, Failed), ATA-01
  (stop-tracking confirm), A02 (phone sheet).
- **Fixed order:** agent → skill (`title-panel`) → folder path → one sentence →
  Now → After pills → primary → "What happens" → Other places (each with its
  StatusMark) → Open skill · Why isn't it running?

| Square | Sentence | Now → After | Primary (key) | What happens | API |
|---|---|---|---|---|---|
| On | "Codex can use this skill." | On → Off | Turn off in Codex (Space) | "The file is renamed so Codex skips it. Nothing is deleted, and you can undo it." | `POST /api/skills/<n>/disable?scope=` |
| Off | "Codex skips this skill." | Off → On | Turn on in Codex (Space) | "The file is renamed back…" | `POST …/enable?scope=` |
| Off in settings | "The file is on, but Claude Code's own settings switch this skill off." | Off in settings → On | Open the settings file (Enter) | "Jackfield never changes agent settings files. Remove the line that turns it off, then refresh." | none (opens S6 / shows the path) |
| Not here | "Codex doesn't have this skill yet." | Not here → On | Add to Codex (Space) | "A copy is made from Claude Code (12 lines, 1 extra file). You can undo it." | `POST /api/sync {name, from_scope, to_scopes:[codex]}` |
| Different | "Codex has its own version. The other places share one." | Different → Same copy | Compare the two versions (Enter) | "You choose which version wins. Nothing changes until you confirm." | Compare view, then `POST /api/sync {…, force:true}` (replaced copy → Trash via `replaced_to_trash`) |
| Can't read | "The file in Codex is damaged, so Codex may not load it." | Can't read → Readable | Preview a replacement (Enter) | "The replacement comes from Claude Code. The damaged file goes to Trash, so you can get it back." | `POST /api/sync {…, force:true}` |
| Evenly split | "This skill has two versions, two places each. Pick the one to keep." | per camp: 2 versions → Same copy in 4 | per camp "Keep version N" → confirm "Make all 4 match" | "Codex and OpenCode get version 1. Their copies go to Trash, so you can get them back." | `POST /api/sync {…, force:true}` per losing place |
| Unknown | the last steps can't be confirmed | — | Look again | ChecksGrid rows with ? | re-read |
| Working | "Turning off in Codex…" | Now, dimmed After, ring | disabled "Working…" `aria-busy` | — | — |
| Failed | `title-banner` in `bad` "Couldn't turn it off" | "Still On → ~~Off~~" | Try again; default "Open the folder" | one plain reason; "Technical details" folded | — |

- **Several rows at once (F3):** tick rows → "Make these match in Codex" →
  preview list → confirm → one Undo: `POST /api/batch/preview` then
  `POST /api/batch/execute`.
- Replacement copies the source's file state. The preview names the target
  copies whose files will be switched on or off. The batch list includes the
  resulting file state for each addition or change.
- **Acceptance:** no square changes before the disk does; a failure leaves the
  true word; focus moves to the panel heading when opened from the keyboard and
  back to the square on Esc; Evenly split preselects nothing and the confirm
  stays disabled with "Choose a version first"; every write ends in the Undo bar
  and Undo restores the exact previous state.

## S3 · Skill page

- **Route:** `#/skills/<name>` · **Boards:** A04/D04 · **Replaces:** skill reader.
- **Content:** breadcrumb Skills / name; title = skill name; Read / File text
  switch; "Why isn't it running?" and Edit (accent) in the title row, pinned
  while scrolling; description; the agent row (the same squares as S1, same
  panel, hint "Click a square to see what it means and change it — the same
  squares as in the Skills table."); the document (`sm-doc`) or File text
  ("Exactly what is in SKILL.md in Claude Code, including the header the agent
  reads."); Details: Files (name + lines), Size ("Uses about 2% of Claude's
  skill list space."), History (from `/api/history`); Move to Trash (quiet).
- **States:** copies differ (choose which copy to read; default the majority);
  can't read (page opens, explains, offers the fix); switched off; not found
  (→ S13); loading.
- **API:** `GET /api/skills/<n>?scope=&view=reader&target_path=`,
  `GET /api/history?name=&limit=20`,
  `DELETE /api/skills/<n>?scope=&purge=0` (Move to Trash; Undo = restore).
- **Acceptance:** F1 (search → Enter → this page); File text is byte-exact;
  Markdown raw HTML stays inert.

**[NOTE]** Both views read the current on-disk document from the selected
folder, including same-name copies in one recursive scope. Details reports
the main document’s line count and counts for supporting files read during
the bounded traversal. The personal Claude Code listing-space estimate uses
observed user settings. It shares the Details panel with the whole-file token
estimate, library events and available file snapshots.

## S4 · Editor

- **Route:** `#/skills/<name>/edit` · **Boards:** A05/D05 · **Replaces:** editor.
- **Content:** breadcrumb …/Edit; title "Editing <name>" + "Unsaved changes" +
  Cancel + Save (accent, "Save to 3 places"); Description (hint "Agents read this
  to decide when to use the skill. One or two plain sentences." + size line);
  Content (Write / Preview, `sm-textarea--file`); **Save to** place rows: "Every
  ticked place gets this exact version." A place holding a different copy is
  unticked by default and marked ("Codex has a different version; saving here
  replaces it"); leave guard "Leave without saving?" with "Keep editing" as the
  accent.
- **States:** unsaved; invalid (why, Save disabled with the reason); saving;
  saved + Undo; changed on disk ("This skill was changed outside the app. Compare
  before saving?"); phone sticky Save.
- **API:** `PATCH /api/skills/<n>?scope=` per ticked place; places that need the
  new copy and do not hold it → `POST /api/sync`. Undo: restore each place's
  previous snapshot (`POST /api/trash/<n>?snapshot=&scope=`), as today.
- **Acceptance:** F5; reload keeps the editor; nothing outside the ticked places
  changes; Ctrl/Cmd+S saves only when valid.

**[NOTE]** The current editor saves to existing unambiguous writable copies.
Changed destinations are refused using the expected path and hash under the
write lock. Saving directly to a missing place remains open. Use the Skill
page to add the copy before editing it. Different copies keep their own extra
frontmatter fields and supporting files, as ordinary PATCH does.

## S5 · New skill

- **Route:** `#/new` · **Boards:** A06/D06 · **Replaces:** New skill dialog.
- **Content:** Name ("The folder name every agent sees, like explain-code.") with
  live rules and one-click fixes; "What it does and when to use it"; **Add it to**
  place rows ("Pick one or more. Each folder gets its own copy."); Start from
  (Blank / Step by step / Checklist, with icons); live preview "What will be
  created" ("Nothing is written until you press Create.": In the Skills table,
  New files, "SKILL.md will start like this"); Cancel + "Create in 2 places".
- **States:** invalid; exists ("code-review already exists in Claude Code and
  Codex. Open it?"); creating; created → S3 opens; discard guard.
- **API:** `GET /api/templates`, `GET /api/templates/<id>`,
  `POST /api/skills?scope=` per chosen place.
- **Acceptance:** F4; the preview equals the created files.

## S6 · Why isn't it running?

- **Route:** `#/skills/<name>/why` · **Boards:** A07/D07 · **Replaces:** the
  explain tool for one skill.
- **Content:** breadcrumb; title "Why isn't <name> running?"; one sentence on how
  checks work; the first failure as one card with one next step and one action
  ("Open the settings file", "Check again"); ChecksGrid (Found, Readable,
  Switched on, Settings allow it, Actually loaded) per tracked place with
  legend; the fixed explanation of why "Actually loaded" is Unknown.
- **API:** `GET /api/doctor?explain=<consumer>&skill=<n>[&project=]` per place
  (exists in `ai-diagnostic.js`), plus the list data.
- **Acceptance:** every Unknown is a real Unknown; the next step matches the
  first failing check.

**[NOTE]** The browser can copy the confirmed Claude user settings path. For
the other settings sources the screen offers a recheck and explains the block.

## S7 · Needs attention

- **Route:** `#/attention` · **Boards:** A08/D08 · **Replaces:** Inbox.
- **Content:** title; list (To fix · Skipped · Fixed groups) and detail of the
  selected item: title ("Codex has a different copy of
  debugging-and-error-recovery"), line, the fix choices ("Use the shared version
  in Codex" / "Use Codex's version everywhere" for Different; "Replace with the
  readable copy" for Can't read), "What happens", Skip for now, Open skill; hint
  "J K next and previous · F fix".
- **States:** empty ("Nothing left to fix" + what was checked + "Last checked
  just now." + Check again); not fixable in the app (says so, shows the manual
  step); skipped; fixed + Undo.
- **API:** derived `attentionItems`; fixes call `POST /api/sync {force:true}`;
  Check again re-reads.
- **Acceptance:** F7; the header count equals the list's To fix count.

## S8 · Trash & backups

- **Route:** `#/trash` · **Boards:** A09/D09 · **Replaces:** Recovery.
- **Content:** title + "Nothing Jackfield removes is gone for good until you
  empty the trash."; Trash · N (one list with origin place, Restore per row,
  Empty trash… quiet); Recent changes (Today and yesterday, from history, each
  undoable where the backend allows); Backups: Download a backup (size, last
  one) and Load a backup ("You'll see what would change in each place before
  anything is written.").
- **States:** empty trash; restore blocked (replace or keep both?); bad backup
  (one message); load results with reasons.
- **API:** `GET /api/trash` (+ `?scope=`), `POST /api/trash/<n>` (restore),
  `POST /api/trash/purge`, `GET /api/history`, `GET /api/export[?full=1]`,
  `PUT /api/import?filename=&force=&full=`.
- **Acceptance:** Empty trash says it cannot be undone before acting; every
  restore re-reads and shows the restored square.

## S9 · Advanced

- **Route:** `#/advanced` · **Boards:** A10/D10, **ATA-03/ATD-03 (current)** ·
  **Replaces:** Tools hub.
- **Content:** title + "Tools you won't need every day, grouped by what you want
  to do."; four goal groups, each a heading + one sentence + tool rows (name +
  one sentence): Add skills; Check my setup; AI assist ("Uses your own AI
  service. You see what's sent first, every time."); Settings (Settings, What to
  track). Switched-off groups are absent; all off shows "Tool groups are
  switched off. Turn them on in What to track."
- **Every existing tool keeps a home** (BD-10). Proposed mapping, needs the
  maintainer's OK (open question Q2):

| Group | Board rows | Existing tools placed there |
|---|---|---|
| Add skills | Install, Templates, Profiles | `install`, `templates`, `profiles`, `source-update` (Update from folder) |
| Check my setup | Quality, Where agents look, Doctor | `quality`, `workspaces` (Where agents look), Doctor (`/api/doctor?scope=all&hygiene=1` report) |
| AI assist | Connection; Write; Test; Shorten; Find conflicts | Connection `ai-settings`; Write `ai-draft`, `ai-improve`, `ai-profile`, `ai-port`, `ai-ask`; Test `ai-trigger`, `ai-evals`, `ai-ablate`; Shorten `ai-concise`, `ai-budget`; Find conflicts `ai-conflicts`, `ai-overlap`, `ai-explain` |
| Settings | Settings, What to track | `settings`, tracking |

## S10 · Tool page (template)

- **Route:** `#/advanced/<tool-id>` · **Boards:** A11/D11, ATA-09/ATD-09 (tool
  group switched off).
- **Template:** breadcrumb Advanced / group / tool; title; one paragraph "what it
  does"; numbered steps (1 Choose…, 2 What will be sent — for AI tools: exactly
  the text that leaves, "To", "Size" estimate —, 3 Result); the result in plain
  words (Compare for text proposals); "Details: the full reply" folded; errors
  next to the button that caused them ("Couldn't reach your AI service. Check
  the address in AI settings, then try again."); the action names its target
  ("Use it for code-review") and states its reach ("Saves to the 4 places that
  share code-review. You can undo it.").
- **States:** not set up (what's missing + link); running; error beside its
  button; no findings (what was checked); group switched off ("AI assist is
  switched off" + Turn it on + Open What to track).
- **Acceptance:** each of the 21 tools renders inside the template with its
  existing calls unchanged; no AI call is sent without the "What will be sent"
  step shown.

## S11 · Settings

- **Route:** `#/settings` · **Boards:** A12/D12, **ATA-04/ATD-04 (current)**.
- **Content:** title + "Changes save as soon as you make them."; first row "What
  to track · 4 agents, 2 project folders, 3 tool groups" → S14; Look (Theme:
  Light / Dark / Match my computer; Text size; Dates: 24 Nov 2026 / Nov 24, 2026
  / 2026-11-24, with "Saved"); AI connection (Address, Model, Status "We only say
  it works after a test answers.", Test the connection) — hidden when AI assist
  is off; Upkeep (Re-read all skill folders; "Where Jackfield keeps its own
  data" + Copy the path).
- **API:** `GET /api/ai/settings` and `POST /api/ai/settings` (save, `clear_key`), `POST /api/ai/test-connection`, Re-read =
  the existing refresh/rescan action.
- **Acceptance:** never "Connected" without a successful test in this session.

## S12 · Search and command palette

- **Opens with:** `/` (header field) and Ctrl/Cmd+K (palette) · **Boards:**
  A13/D13 · **Replaces:** header search + palette.
- **Content:** one field "Search skills, actions and pages"; groups: Skills
  (name, description, which agents have it), Actions (New skill, Refresh files,
  tracking actions, tools), Pages (the four places, Settings, What to track);
  no match: "Nothing matches "…"." + "We searched skill names, descriptions,
  actions and pages." + Did you mean; hint line "↑ ↓ move Enter open Esc close
  Open anywhere with / or Ctrl K".
- **Acceptance:** Enter goes where the highlighted row says; switched-off tools
  and untracked agents never appear.

## S13 · Not found

- **Boards:** A14/D14. "Page not found" or "There's no skill called
  test-drivn-development" + "It may have been renamed, removed, or the link has
  a typo. We looked in all 5 places." + the address + Did you mean + Go to
  Skills (accent) + Look in Trash + "Removed skills stay in Trash until you empty
  it."

## S14–S19 · What to track and its doorways

- **Routes:** `#/settings/tracking[/add-agent|/add-project|/agent/<id>]` ·
  **Boards:** ATA-05/ATD-05 (page), ATA-06/ATD-06 (phone), ATA-07/ATD-07 (Add
  other agent), ATA-08/ATD-08 (Add project folder), ATA-01 (S1 doorways) ·
  **Exists today** in the old look (`78cc21b`, option A); this build restyles it
  onto the system and moves its doorways to their designed places.
- **S14 content:** breadcrumb Advanced / Settings / What to track; "Choose what
  Jackfield shows. This only changes what you see here. Nothing on disk
  changes."; notices (first time, broken file + Reset to everything found,
  changed in another window + Reload); ListGrid Agents (Agent · Skills · Only
  here; "Only here" definition; Shared folder Automatic row; Add other agent;
  "Space ticks the focused agent"); Project folders (radio "Showing in the
  table", Remove, Add project folder, "Removing one never touches its files.");
  Tool groups (three switches, "Its settings are kept…"); side panel with
  TablePreview "The Skills table, as it will look" and the agent peek (Folder, In
  projects, Skills, Also reads, Count project folders for X, Edit).
- **S15 confirm** in the panel (sheet on phone): "Stop tracking Cursor?" →
  TablePreview with the leaving column → "142 skills → 130 skills" → "12 skills
  live only in Cursor and will no longer show." → See the 12 skills → Stop
  tracking Cursor (primary) → Keep tracking → "Nothing on disk changes. You can
  track it again any time."
- **S16 / S18 forms:** live checks per field in plain words (missing, not a
  folder, not readable, outside home, already tracked by X, name taken) and the
  preview line ("Kilo · 9 skills found in ~/.kilo/skills").
- **S19 project picker:** None, folders (current ticked, missing greyed with
  reason), Add project folder…, Manage project folders.
- **API:** `GET /api/tracking`, `PUT /api/tracking` (revision; 409 → "These
  settings changed in another window. Reload to see them."),
  `POST /api/tracking/check-folder`.
- **Acceptance:** T1–T9; benchmarks "stop tracking Cursor" and "add Kilo" each
  under a minute without docs; the last agent cannot be unticked.

## Phone (all screens)

- **Boards:** A02/D02, ATA-02/ATD-02, ATA-06/ATD-06; the rest follow the
  breakpoints in @docs/redesign-build/04-frontend-architecture.md.
- **Skills on phone:** "142 in 5 places", attention line with Review, "Showing
  Codex ▾" (with Manage agents at the bottom), one status per row, tapping opens
  the sheet with the same panel content; bottom tabs Skills · Attention · Trash ·
  Advanced; search and New skill as header icon buttons.
- **Acceptance:** 390 px wide, main content visible on the first screen, every
  target ≥ 44px, no horizontal scroll except the File text view.
