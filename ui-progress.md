# Skills Manager UI — UI progress

Phase 3 of the `/uxui-workflow` (the rule of three). A new conversation picks up here.

- **Canvas:** https://claude.ai/artifact/2bRpEoQ192WY2Tp7dYsXdq (private to the owner)
- **Design system:** https://claude.ai/artifact/27HHwcNGwDAZ2cne6xW4ei — "Skills Manager design
  system" (tokens light + dark, brand book, 9 components: Button, Field, Keycap, StatusMark, Square,
  AttentionBanner, SidePanel, UndoBar, Navigation; classes `sm-*` in `components/bundle.css`).
  Installed on the canvas as `project/ds/skills-manager/`.
- **Inputs:** `design-brief.md` (self-contained), `ux-brief.md`, `requirements.md`.
- **Hero screen:** S1 · Skills table with its side panel (S2).

## Status: phase 3 done again, every gap closed (2026-11-27)

- **Approved screens** now run 1–16 in light (`A01`…`A16`, y 14080) and dark (`D01`…`D16`, y
  15980), plus Agent tracking `ATA-01…09` / `ATD-01…09`. New: **15 · S2 side panel states**
  (B · Two camps) and **16 · S1 first launch**. Canvas version 58, now titled "Jackfield".
- **Jackfield name and mark** on all 50 approved boards: the horizontal lockup from
  `branding/jackfield/kit/svg/` (30px desktop, 29px phone; light and `-dark` cuts follow the
  theme), every "Skills Manager" in the copy → "Jackfield", data folder
  `~/.local/share/jackfield`. Round rows above stay as they were (the record).
- **Design system v13** (published 2026-11-27, design system versions 13–14), renamed "Jackfield
  design system": statuses Version 1 / Version 2 / Unknown / Working (StatusMark, Square,
  `bundle.css`), the SidePanel states Evenly split, Unknown, Working and Failed, the Jackfield
  lockup in Navigation and the Cover, and a Logos asset group (6 kit SVGs). Tokens unchanged, so
  the canvas's installed `tokens.json` is still current (its `name` field still says Skills
  Manager).
- **Exported** to `designs/final/light/` and `designs/final/dark/` (canvas sources, with a
  README index) for `/build`.
- Checked by script (template holes, `sc-if`/`sc-for` balance, every script runs, one logo per
  board except A03/D03, which have none). **Not rendered.**

## Gap check and round 6 (2026-11-27)

A check of every approved board against the screen inventory (S1–S19) found each screen drawn,
but three things missing:

1. **S2 side panel states** Evenly split, Unknown, Working and Failed (brief: "Square states")
   are on no board. **Done** (round 6, B · Two camps; approved screen 15).
2. **S1 first-launch scan** ("Looking for your agents…") is not on the main boards; A03 starts at
   "Found 3 agents and 142 skills". Supporting, one version. **Done** (approved screen 16).
3. **The Jackfield name and mark**: all 46 approved boards said "Skills Manager" with the old
   9-square mark. **Done** (design system v13 and the sweep above).

Not a gap: Profiles and Templates are on the won't-have list beyond the shared tool-page
template (`design-brief.md`).

### Round 6 · S2 side panel states · Variations (2026-11-27)

Canvas version 56, row "Round 6 · S2 side panel · Evenly split, Unknown, Working, Failed ·
Variations" at y 39400 (title y 39100). Each board is the approved A01 table and panel, cut to
five rows that show the new states, plus a gallery of the four panels side by side. Tweaks:
`dark`, `start` (split / unknown / working / failed), `outcome` (done / failed: what a change
does after Working…). Shared rules: a failed change keeps the square's true word (still On),
nothing preselected on an even split, Working… only in the square being changed. Proposed new
marks (not in the design system yet): Unknown "?", Working ring. Checked by script (template
holes, `sc-if` balance, the logic in all four start states); not rendered.

| | Artboard | Idea |
|---|---|---|
| A · Status first | `R6-S2-A-Status.dc.html` | One-sentence status as the headline; split is two radio cards, primary disabled ("Choose a version first") until one is picked; failed is a red-tinted box with Try again and Open the folder, raw error folded |
| B · Two camps | `R6-S2-B-Camps.dc.html` | Split squares say "Version 1" / "Version 2" (filled and hollow diamond); pointing at a version card marks its squares in the table; Keep version N, then a confirm step with Now → After; Unknown shows the 5-step check list; failed shows "Still On → Off" struck out |
| C · Ledger | `R6-S2-C-Ledger.dc.html` | Split is a compare table (places, lines, changed, extra files) with radios in the header and "1" / "2" tags on the squares; Working and Failed are a two-step list showing which step failed; Unknown is a three-line ledger |

**Picked (maintainer, 2026-11-27): B · Two camps** (frame marked "picked"). It is the only one
that shows in the table where each version lives before you choose. Not yet in the design
system: the "Version 1" / "Version 2" square words, the hollow diamond, the Unknown "?" mark and
the Working ring.

### Round 6 · Supporting: S1 first launch (2026-11-27)

`R6-S1-First-launch.dc.html`, row "Round 6 · Supporting (one version)" at y 41520 (title y
41220), canvas version 57. The table's loading placeholders sit dimmed behind a card that checks
each place in turn: Claude Code 58, Codex 41, OpenCode 43, Cursor and Gemini "Not on this
computer", Shared folder "No skills yet". "Only reading. Nothing on disk changes." while it scans.
Then "Found 3 agents and 142 skills" (A03's numbers), the one hint, Show my skills (to A01) and
"Choose what to track" (to ATA-05). Tweak `step`: play (auto-advances) / scanning / found.
Checked by script; not rendered.

## Feature: Agent tracking (added 2026-11-26)

Phase 3 for the feature in `design-brief.md` → "Feature: Agent tracking". Same canvas and design
system (v11); the three directions share its colours and type, so they differ in layout, density,
hierarchy and signature. Hero: **S14 What to track with its confirm S15**.

- **Canvas rows:** "Agent tracking · Round 1 · Directions" at y 24200 (title y 23900).
- **Marks added (B5):** Cursor and Gemini from simple-icons 16.26.0 (CC0; same one-colour mask
  rule as Claude and OpenCode); Command Code a neutral "command" icon (no logo source found);
  custom agents a neutral dashed square (B4). CSS keys `data-a="Cursor"`, `"Gemini"`,
  `"Command Code"`, `"Custom agent"`.
- **Build scripts:** `tools/` in the session scratchpad (`common.py` + one file per direction).
  Every artboard has tweaks `dark` and `mode` (returning / first-time / broken-file).

### Status: phase 3 done for Agent tracking (2026-11-26)

**Approved by the maintainer on 2026-11-26 ("Approve all"):** the feature's Approved screens rows
in light (`ATA-01`…`ATA-09`, y 35140) and dark (`ATD-01`…`ATD-09`, y 37120), canvas version 52.
These rows are the handoff reference for building the feature; the round rows above them are the
record of how each pick was made.

**S1+ picked (maintainer):** A · Menus in place (`AT-R5-S1-A-Menus.dc.html`, frame marked
"picked").

**S9+ / S10+ / S11+ (supporting, one version each; canvas version 52, row y 31800):**
`AT-R5-S9-Advanced.dc.html` (tweak `groups`: AI assist off / all off / all on; switched-off
groups are absent, the Settings card drops "AI connection", a "What to track" entry joins the
Settings group, all off shows "Tool groups are switched off. Turn them on in What to track.");
`AT-R5-S10-Tool-Off.dc.html` (the Shorten page; `state` switched-off is the default: "AI assist
is switched off", Turn it on (accent) + Open What to track, then "AI assist is on. Its settings
were kept." with Undo); `AT-R5-S11-Settings.dc.html` (first row "What to track · 5 agents, 3
project folders, 3 tool groups" leads to the page; tweak `aiAssist` hides the AI connection card
and says "2 of 3 tool groups"). The counts follow the hero's data (5 of 7 agents tracked,
api / web / blog), not the brief's example "4 agents, 2 project folders".

**Consistency pass:** the hero and its phone frame use v12 `sm-btn--primary` for the confirm
(was `sm-btn--accent`); their "Add other agent" / "Add project folder" are now links to S16 /
S18; the S1+ confirm label matches the hero (the agent's name only); the phone Skills table gets
"Manage agents" beside the Showing picker (a native select can't hold a menu item). Copy checked
for "scope", "untrack" and "consumer" in visible text: none. Numbers agree across screens
(Cursor 19 / 12 only here, 142 → 130, Gemini 14, ~/side/blog missing).

**Approved screens (feature):** two rows, "Agent tracking · Approved screens" at y 35140 (title
34840) and the dark row at y 37120 (title 36820), journey order: 1 Skills table (S1+), 2 phone
Skills table, 3 Advanced (S9+), 4 Settings (S11+), 5 What to track (S14 + S15 + S17), 6 its
phone frame, 7 Add other agent (S16), 8 Add project folder (S18), 9 tool page switched off
(S10+). Files `ATA-0n-*.dc.html` (light) and `ATD-0n-*.dc.html` (dark by default; links to
D-screens for the rest of the app). Prototype links: Settings → What to track → Add other agent /
Add project folder (and back); table column menus and the project picker → What to track / Add
project folder; Advanced → Settings / What to track / the tool page. Checked by script (template
holes, `sc-if` balance, scripts run, every link resolves); not rendered.

### Round 5 · S1+ Skills table changes · Variations (2026-11-26)

Canvas version 51, row "Agent tracking · Round 5 · S1+ Skills table changes · Variations" at
y 33220 (title y 32920). Each one is a copy of `A01-Skills.dc.html` with v12 styles added
(Cursor, Gemini, Custom agent marks; `sm-preview`, `sm-tag`, `sm-btn--primary`). Columns are
Claude Code, Codex, OpenCode, Cursor, Kilo, Shared folder and the project shown (api), so the
numbers match the hero (Cursor 19 skills, 12 only here; 142 → 130; Gemini 14 found). Tweaks:
`dark`, and `state`: found-gemini (the default) / returning / last-agent / no-agents /
broken-file / project-missing / no-project-folders. All three share: the confirm in the side
panel (S15, button `sm-btn--primary`, "Keep tracking", "Nothing on disk changes", Esc cancels,
focus to its heading and back); Undo messages; the broken-file banner (Kilo absent, because
custom agents live in the broken file); "~/side/blog can't be found" with Choose another and
Remove; the "No agents are tracked." empty state with "Choose agents"; Add project folder… →
S18, Manage… / details → What to track. Checked by script (template holes, JS, the logic in all
seven states); not rendered.

| | Artboard | Idea |
|---|---|---|
| A · Menus in place | `AT-R5-S1-A-Menus.dc.html` | A ▾ on each agent column header opens a menu ("19 skills · 12 live only here", Stop tracking Cursor…, Cursor details, Manage agents); the toolbar picker "Project: api ▾" is the same kind of menu; the Gemini notice is a quiet strip above the toolbar; the confirm shows the mini TablePreview, as in the hero |
| B · Preview in the table | `AT-R5-S1-B-Preview.dc.html` | Same menus, but the real table previews the change: pointing at "Stop tracking Cursor…" (and the open confirm) hatches the Cursor column and strikes out the rows only in Cursor, so the confirm drops the mini table; the Gemini notice sits on top of the table, and pointing at Track shows a dashed Gemini column with its new rows; the picker shows skill counts |
| C · Column panel | `AT-R5-S1-C-Panel.dc.html` | No pop-up menus: a column header is a button that selects the whole column, and the side panel shows that column (skills, only here, also reads, Stop tracking Cursor…, details, Manage agents); the project header and the toolbar picker open a "Which project to show" view with radio rows in the panel; the Gemini notice sits at the top of the panel |

**S16 picked (maintainer):** "B and C", combined on request as **B's own page + C's
folder-first form**: `AT-R5-S16-Winner.dc.html` (canvas x 4560 in the S16 row). Folder field
first; the name is filled in from the folder until the user types one; the skills found show under
the folder field; "Folder inside projects" sits under More options; the "What will be added" card
and Add Kilo (accent) as on the approved New skill page.

**S18 Add project folder** (supporting, one version): `AT-R5-S18-Project.dc.html`, row
"Agent tracking · Round 5 · Supporting screens" at y 31800 (title y 31500). Same layout as S16:
path with live check, "Show it in the table now", a card with the skill folders found ("None yet …
that's fine" for an empty repo) and "Its files are never touched". Tweak `state`: filled / empty /
no-skills / errors.

**Still to do in round 5:** S1+ Skills table changes (key: 3 variations; the S19 project picker
goes in its toolbar), then S9+ / S10+ / S11+ (supporting), a consistency pass, and the "Approved
screens" rows in light and dark with prototype links.

### Round 5 · S16 Add other agent · Variations (2026-11-26)


**Design system v12 published** (design system version 12, 2026-11-26) on the maintainer's
"Add all 9": the four marks; new components ListGrid, TablePreview, Sheet and Placeholder (README +
preview each); `bundle.css` section "Added for Agent tracking"; Field radio rows; Chip tags;
SidePanel confirm form; Button / README rule for confirms of reversible view changes. Tokens are
unchanged, so the canvas's installed `tokens.json` is still current. Round 5 artboards embed the
v12 classes (`sm-list`, `sm-preview`, `sm-tag`, `sm-sheet`, `sm-skel`).

**Round 5 order (design brief):** S14 + S15 done in the hero; S17 Details lives in the hero's
panel and sheet; next key screen S16, then S18, S19 (supporting), the Skills table changes (S1+)
and the Advanced / tool page / Settings changes, then "Approved screens" rows in light and dark.

Canvas row "Agent tracking · Round 5 · S16 Add other agent · Variations" at y 30120 (title y
29820). Each has tweaks `dark` and `state` (filled / empty / errors / failed / edit), live folder
and name checks, the discard guard ("Keep editing" is the accent) and Undo.

| | Artboard | Idea |
|---|---|---|
| A · In the side panel | `AT-R5-S16-A-Panel.dc.html` | The form opens in What to track's panel, folder first; a TablePreview shows the new column and its rows arriving; the list shows a pending "Being added" row |
| B · Its own page | `AT-R5-S16-B-Page.dc.html` | The approved New skill layout: form on the left, "What will be added" card on the right with the new column and every skill it brings |
| C · Folder first, in a dialog | `AT-R5-S16-C-Dialog.dc.html` | A dialog over the page: paste the folder, the app finds the skills and suggests the name; project folder under "More options" |

### Round 4 · System check (2026-11-26)


**Round 3 fixes:** all 10 applied on the maintainer's "Apply all 10" (canvas versions 44–45).
`AT-R3-Winner.dc.html` (1440, `mode` tweak now also has loading / save-failed /
changed-elsewhere) plus `AT-R3-Winner-Phone.dc.html` (the same page in a 390 × 844 frame, at x 1520
in the same row). Checked by script (markup, template holes, logic in all six modes); not rendered
or screenshotted.

**Round 4:** the canvas already uses design system v11, so no new system is made. New patterns
this screen introduced, proposed for v12 (nothing added yet):

1. Agent marks: Cursor, Gemini (simple-icons logos), Command Code (neutral command glyph), Custom
   agent (dashed square).
2. TablePreview: the mini table inside the SidePanel (mark headers, dot / dash cells, leaving
   column hatched, rows that leave struck out; hidden from assistive tech with a text summary).
3. ListGrid: tick, mark, name + status, number columns, quiet action; 56px rows; section head
   with a count; footer with the reassurance line.
4. Pending row + panel confirm behaviour: "Waiting for you to confirm"; focus to the confirm
   heading; Esc cancels; focus returns to the row.
5. Sheet: the phone bottom sheet carrying SidePanel content (layout rule exists; no component).
6. Radio rows: one choice from a list ("Showing in the table").
7. Label chips: New (accent-soft), Custom and Automatic (quiet).
8. Placeholder: skeleton rows and panel blocks for loading.
9. Rule: a confirm for a reversible view change makes the action the accent button; the
   unsaved-work rule (safe choice is the accent) stays for dialogs that can lose work.

### Round 3 · Critique and fix (2026-11-26)


Round 2 pick: **B2's panel (live mini table) + B3's grid list** (maintainer, 2026-11-26, as
recommended). Winner: `AT-R3-Winner.dc.html`, canvas row "Agent tracking · Round 3 · Winner,
critique and fixes" at y 28140 (title y 27840). Pointing at or tabbing to an agent row lights its
column in the mini table.

Critique (measured contrast: light text pairs 5.11:1 or higher, dark 6.93:1 or higher; mini-table
dash #9A9A93 on white 2.83:1):

| # | Severity | Issue | Proposed fix |
|---|---|---|---|
| 1 | High | Phone: the panel stacks under the long list, so the confirm opens off-screen | Under 900px: panel becomes a "Preview" fold under Agents; the confirm opens as the A02 bottom sheet |
| 2 | High | Keyboard and screen reader: focus stays on the checkbox and nothing announces the confirm | Focus moves to the confirm heading, announced; Esc = Keep tracking; focus returns to the checkbox |
| 3 | High | Pending state unclear: the checkbox still shows ticked while the confirm is open | Row status reads "Waiting for you to confirm"; a second untick replaces the pending confirm |
| 4 | Medium | Mini table uses role="table" without rows (invalid ARIA) | Mini table hidden from assistive tech; a plain-text summary of what leaves sits beside it |
| 5 | Medium | Mini-table dash 2.83:1 in light, below 3:1 for graphics, with no word | Draw the dash in `mute` (5.78:1) |
| 6 | Medium | "Only here" is ambiguous (only among tracked agents, so it changes) | One-line definition under the Agents heading and in the column's accessible name |
| 7 | Medium | Loading, save-failed and changed-in-another-window states not drawn | Add them to the `mode` tweak |
| 8 | Medium | Phone hides Only here and Details (grid columns), so Details is unreachable | Phone: status line carries "19 skills · 12 only here"; tapping the name opens Details in the sheet |
| 9 | Medium | Details / Remove buttons are 32px high | 44px at 640px and below, like the system's icon buttons |
| 10 | Low | "Nothing on disk changes" appears three times (intro, idle panel, confirm) | Drop it from the idle panel; keep intro and confirm |

### Round 2 · Variations of B (2026-11-26)


Canvas row "Agent tracking · Round 2 · Variations of B · Live preview" at y 26220 (title y 25920).
All three keep B's list + side panel; the panel turns into the confirm.

| | Artboard | Pushed | What changed |
|---|---|---|---|
| B1 · Hierarchy | `AT-R2-B1-Hierarchy.dc.html` | Focus on the main job | Agents card is the page; an "Only here" number column (12 of 19) is the one thing to read; Project folders and Tool groups sit as two small cards below; panel leads with a 40px skill count, and the confirm puts "142 → 130 skills" and the button first |
| B2 · Signature | `AT-R2-B2-Signature.dc.html` | A live miniature of the table | The panel shows a few real rows of the Skills table; pointing at an agent highlights its column; in the confirm the leaving column is hatched and rows that live only there are struck out |
| B3 · Craft | `AT-R2-B3-Craft.dc.html` | Type, spacing, rhythm | One 6-column grid (tick, mark, agent, Skills, Only here, Details) on 56px rows; section heads with counts; Now / After comparison box; Space-to-tick hint; footers carry each section's reassurance line |

### Round 1 · Directions — picked: B · Live preview (2026-11-26)

The maintainer chose B as recommended: the consequence of unticking is visible before anything
changes, and it reuses the approved side panel instead of a new dialog.

| | Artboard | Idea | Confirm (S15) |
|---|---|---|---|
| A · Settings list | `AT-R1-A-List.dc.html` | Three Settings-style cards (Agents, Project folders, Tool groups) in a 900px column; a live sentence on top: "Tracking Claude Code, Codex, … and Kilo." | Centred dialog |
| B · Live preview | `AT-R1-B-Preview.dc.html` | One list on the left; on the right the hero's side panel shows the Skills table's columns as tiles, with the total | In the side panel: Now → After totals, the leaving column dashed and struck through |
| C · Two lists | `AT-R1-C-Lists.dc.html` | Tabs (Agents / Project folders / Tool groups); agents move between "Tracked" and "Not tracked" tables with Skills and Only here columns | Inside the row |

## Main redesign: current round

### Icons pass 2: agent marks everywhere, standard action icons (2026-11-25)

Done on the maintainer's "Apply 1 and 2".

**Published:** canvas version 35 and design system version 10. Script: `tools/icons2.py` in the
session scratchpad.

**Agent marks**, keyed by place name, so no screen logic changed:
- A01 side panel "Other places".
- A02 phone sheet header.
- A03 first launch. Its blue dots were replaced, because they wrongly meant "On".
- A03 "Changed in Codex" / "New in OpenCode" pills.
- A04 history lines.
- A05 Save-to list.
- A06 "Add it to" chips.
- A08 attention list.

**Action and state icons:**
- Warning triangle on the attention banner (A01, A02).
- File icons in the A04 Files list.
- Bin on Move to Trash (A04) and Empty trash (A09).
- Download, upload and restore on A09.
- Refresh on Check again (A07) and Re-read now (A12).
- Plug on Test the connection, copy on Copy the path (A12).
- Sun / moon / monitor on the A12 theme switch.
- Alert / tick / info on the A12 connection status.
- File / ordered list / checklist on the A06 templates.
- Chevron on the A11 details toggle.

**Not iconised, on purpose:** everyday verbs, desktop nav, section headings, Recent changes rows
and the Not found page.

**Marks stay one colour.** Claude's brand orange #D97757 measures ΔE 8.1 from the Different
diamond #C06A00 and would read as a warning. OpenCode and Cursor are black marks anyway.

**Design system:**
- Iconography section rewritten: where icons go, where they do not, and the tile / inline-mark
  rules.
- Button, AttentionBanner, Chip, SidePanel and Segmented READMEs and previews updated.
- `bundle.css` gained the pass-2 rules.

**Checks:**
- All data-URI SVGs are valid.
- The text-size switch was kept icon-free; the selector was narrowed to the six named choices.
- A05, A06 and A11 had a missing-CSS / blank-square risk; fixed and re-rendered.
- Renders checked by eye: A01–A06, A08, A09, A11, A12, D01, D12 and the design-system
  components.
- The unslop scan finds 0 tells.

Known small effect: on New skill, the five place chips now wrap to a second line at 1440px.

### New skill "Add it to": chips → checkbox rows (2026-11-25, chosen by me at the maintainer's request)

**Measured:**
- The form column is 640px. Five chips with marks need 707px.
- All 8 places the app supports need about 1,050px, which makes 2–3 ragged rows.

**Options considered:**
- (a) Keep the wrap.
- (b) Tighten the chips: 669px still does not fit, and 8 places never will.
- (c) Drop the marks: undoes the request.
- (d) An equal-width grid.
- (e) Vertical checkbox rows, as in the Editor's "Save to". **Chosen.**

**Why (e):**
- One pattern for choosing places across the app.
- It scales to 8 places, and each row has room for the folder it will write to, or a per-place
  note (name taken, project-only).
- Native checkboxes announce clearly as "checkbox, checked".
- Vertical lists are easier to scan:
  [UK Parliament](https://designsystem.parliament.uk/forms/checkboxes/),
  [Visa](https://design.visa.com/components/checkbox/usage/).
- Chips suit short, filter-like sets that wrap to at most about two rows:
  [Material chips](https://m2.material.io/components/chips),
  [Cieden](https://cieden.com/book/atoms/checkbox/chip-components-or-checkboxes).

**Applied:**
- A06/D06 rows: tile, name, and the folder, e.g. `~/.codex/skills/explain-code`.
- Hint: "Each folder gets its own copy."
- Board height 1100 → 1240 (page measures 1231px).
- Design system version 11: Field "Place rows" and the Chip scope note.
- Canvas version 36.

### Icons replace text marks; agent marks in the tiles (2026-11-25)

Done on the maintainer's request.

**Published:** canvas version 34 (A/D screens, the C colour boards, and the T0–T3 pages) and
design system version 9. Script: `tools/icons.py` in the session scratchpad.

**Text glyphs replaced with inline SVG**, drawn as 2px strokes in `currentColor`:
- ✓ and ✕ in the check cells and the A07 legend: 4 glyphs plus the state map.
- "✓ Saved" in A12.
- ✕ / × close and dismiss buttons: 20 in the A/D screens. The A01 toast button also gets a label.
- ▾ on the filter buttons: 12.
- The "?" Help buttons become a help-circle icon: 26.
- Keyboard keys in keycaps stay as text.

**Agent tiles** (`ag` / `sm-ag` with `data-a`) show a one-colour mark (`ink-2`) through a CSS
mask, so they follow the theme:

| Place | Mark |
|---|---|
| Claude Code | Claude's own logo (simple-icons 16.36.0) |
| OpenCode | OpenCode's own logo (simple-icons 16.36.0) |
| Codex | A neutral terminal icon |
| Shared folder | A folder |
| This project | Code brackets |

The two-letter monogram stays in the markup as fallback text. OpenAI's logo is not in
simple-icons any more (removed at the brand's request), so Codex keeps the neutral icon until the
maintainer decides; the design-system README records this.

**Checks:**
- Every data-URI SVG parses as valid XML. One bug was found and fixed: a duplicate stroke-width
  made the tick and cross invisible.
- The A01, A07, D07, A12 and A09 renders and the design-system components were checked by eye.
- The unslop scan of the current design and design system finds 0 tells.

### AI-slop re-check after the font and colour changes (2026-11-25)

Scope: all 90 canvas boards plus the design system.

**Scanner (unslop-ui):**
- Current design (A01–A14, D01–D14 and the design system, 44 files): **0 findings**.
- Exploration boards: only T0 and T-Review are flagged, for Inter, which is there on purpose as
  the comparison.
- Old rounds (R1, R2, R5 variations, Main, Winner, Phone, States): Inter/Geist and older radii
  are flagged. They are the decision record, superseded by A/D, and left as they were.

**By-eye catalog on the current design:** none found of gradients, glows, emoji icons, accent
side stripes, hype copy, purple, uppercase labels or template card grids. The only motion is a
0.12s hover fade.

**Rendered check:** a local renderer (`tools/dcrender.py` in the session scratchpad) fills each
board's template and screenshots it in headless Chrome. All 28 screens look as designed.
Renderer artefacts, not design defects: empty textareas on A05 and A06, and the phone's agent
picker showing the last option.

Low, optional:
- A07, A12 and the ChecksGrid preview use the text glyphs ✓ / ✕ where the design system says
  icons are inline SVG. These are not emoji, so they are not a slop tell.
- A10 Advanced is a hub of icon + title + blurb rows in three cards. It is functional
  navigation, not the landing-page "three feature cards" pattern.

### Type exploration — picked: T1 IBM Plex Sans + Mono (2026-11-25)

The maintainer asked me to review all three in depth and choose. The board `T-Review.dc.html`
(canvas x 9600, y 21800) has a live side-by-side render, a scorecard and the verdict.

**Method:**
- Primary sources: IBM Plex concept pages, Braille Institute / Atkinson Next release coverage,
  Recursive docs.
- fontTools measurements on the Google-served latin files.
- Headless-Chrome renders at the real table sizes, inspected at 2x.

| Criterion | Inter | Plex | Atkinson | Recursive | Evidence |
|---|---|---|---|---|---|
| Small-size legibility | 5 | 4 | 3 | 4 | x-height at 13px: 7.10 / 6.71 / 6.45 / 6.92px; all hinted |
| Telling letters apart | 2 | 4 | 5 | 4 | Inter draws I and l the same; Atkinson slashes 0 in text |
| Fits the dense table | 4 | 5 | 5 | 3 | Width against Inter: −5 to −6% / −8% / +2 to +6% |
| Words and paths as one family | 3 | 5 | 4 | 5 | Plex superfamily; Recursive MONO axis |
| Fits "calm, clear, trustworthy" | 4 | 5 | 4 | 3 | Judgement |
| Not an AI default | 1 | 5 | 5 | 5 | unslop-ui scan |
| Proven in product UI | 5 | 5 | 4 | 3 | Plex is Carbon's UI font at 12–16px since 2017 |
| Weight to ship | 4 | 4 | 5 | 3 | Latin woff2: about 24 / 24 / 12.6 KB per weight; 142 KB for Recursive's variable file |
| **Total / 40** | 28 | **37** | 35 | 30 | |

**Decision:**
- **Pick: T1 IBM Plex.** No size or weight changes are needed.
- **Runner-up: T2 Atkinson.** It would need +0.5–1px because of its small x-height.
- **Recursive: not recommended.** It is wide, heavy, and its casual roots pull away from "calm".

**Rolled out on the maintainer's yes (2026-11-25).**

Design system, versions 6–7:
- `tokens.json` families now use IBM Plex Sans and IBM Plex Mono.
- Heading weight 650 → 600, because Plex ships static 600 and 700 weights.
- Heading tracking: title-page −0.02em, title-panel −0.015em, title-doc −0.01em.
- `bundle.css` uses `font-variant-numeric: tabular-nums` instead of Inter's `cv11` / `ss01`
  features.
- All 15 component previews load Plex.
- The README Typography section explains the choice; the Document guide reads 19/600.

Canvas, versions 31–32:
- A01–A14 and D01–D14 changed in 28 files: font links, sans and mono stacks, 44 headings
  650 → 600, and tabular numbers.
- The C0–C5 colour boards were regenerated with Plex.
- The canvas copy of the design-system tokens was refreshed (`copiedAt` 2026-11-25T17:05Z).
- T0 stays on Inter as the comparison.

Checks:
- The unslop-ui scan found 0 tells across 62 files (screens, colour boards, design system).
- Components rendered in headless Chrome with Plex look correct.
- The A and D boards were not opened on the canvas.

Fixed in passing (it had nothing to do with the font): on A01, D01 and the C and T boards built
from A01, the top-menu links rendered in accent blue. The cause was `.root a` beating `.navlink`.
The design system's `sm-nav__link` and `sm-tab` had the same problem. Both are now scoped under
the root. A04–A14 were already correct.

Still to do in the product (not design work): the app is offline-first and binds to 127.0.0.1,
so ship the Plex woff2 files with it (OFL allows that) instead of loading Google Fonts.

The AI-slop audit's one open finding was Inter as the only typeface, and the maintainer asked to
see 3 alternatives. Canvas row "Type exploration" (y 21800) shows the Skills table (today's layout
and colours) plus a specimen card per font. The card has the design-system type sizes, letters
people confuse, tabular numbers, weights and sources.

| # | Font | Idea | Checked |
|---|---|---|---|
| T0 | Inter + JetBrains Mono | Today, for comparison | Scanner flags it |
| T1 | IBM Plex Sans + Plex Mono | "Engineered": one family for words and paths | Digits tabular by default; scan clean |
| T2 | Atkinson Hyperlegible Next + Mono | "Legible first": I/l/1 and O/0 never confused | Has `tnum` (switched on); scan clean |
| T3 | Recursive (MONO axis 0/1, CASL 0) | "One voice for words and code" | Digits tabular by default; scan clean |

All load from Google Fonts (checked). Feature checks were done with fontTools on the Google-served
latin files. Not yet checked by eye on the canvas.

### Colour exploration — picked: C0 Today, with three small tunings (2026-11-25)

The maintainer asked for an in-depth review and a single answer. Scripts:
`tools/analyse.py` (WCAG, APCA, colour-blindness simulation, layering) and
`render/specs/grid-*.png` (normal and deuteranope renders) in the session scratchpad.

Weighted score, out of 65 (weights are my judgement; inputs are measured):

| Criterion (weight) | Today | Cobalt | Nordic | Graphite | Green light | Night |
|---|---|---|---|---|---|---|
| On signal survives colour blindness (3) | 5 | 5 | 2 | 5 | 1 | 2 |
| Text contrast, WCAG and APCA, light and dark (2) | 4 | 4 | 4 | 4 | 3 | 3 |
| Different mark at 3:1 or more (1) | 5 (3.96) | 4 | 2 | 2 | 4 | 2 |
| On mark salience (2) | 5 | 5 | 2 | 2 | 4 | 3 |
| Own identity, not a brand or default (2) | 3 | 1 (IBM) | 4 | 1 (Vercel) | 1 (GitHub) | 3 |
| Fits calm, clear, trustworthy and Plex (1) | 5 | 3 | 4 | 3 | 3 | 3 |
| Proven, cost of change (1) | 5 | 2 | 2 | 2 | 2 | 1 |
| Page and card layering (1) | 2 | 4 | 4 | 2 | 3 | 4 |
| **Total** | **56** | 48 | 38 | 38 | 31 | 34 |

What decided it:
- **Colour blindness (Machado 2009, deuteranope):** the blue On mark stays blue. Teal (Nordic,
  Night) turns grey. Green turns olive, colliding with the Different diamond (ΔE 5.0–5.5).
- **Brands:** Cobalt is exactly IBM blue 60, and with Plex it reads as IBM Carbon. Graphite is
  Vercel's #171717. Green light is GitHub's #1A7F37.

**Applied on the maintainer's yes (2026-11-25):**
- Design system version 8: tokens and contrast notes updated.
- Canvas version 33: all 28 A and D screens, the C0 Today boards, and the canvas copy of the
  design-system tokens.
- Value swaps across the screens: `--bg` 28, `text-faint` light 28, dark `mute` 26, dark
  `text-faint` 26, dark `accent` 28. The accent count includes two hard-coded fills in the
  dark phone and states boards.
- No old values remain.
- Weakest text pair is now 4.70:1 light and 5.63:1 dark (was 4.44); weakest state pair 5.44:1.
- Not checked by eye on the canvas.

The tunings:
- Light `text-faint` #72726B → **#6E6E67**: 4.70:1 on hover, up from 4.44.
- Light `bg` #FAFAF9 → **#F6F6F3**: page/card ΔL 1.5 → 2.8; every text pair still at 5.3:1 or more.
- Dark `mute` #A3A39C → **#B0B0A9**: APCA Lc 51 → 58.
- Dark `accent` #7EA2FF → **#8CAEFF**: Lc 52 → 58; on-accent 8.3:1.
- Dark `text-faint` #8E8E87 → **#9A9A93**: on hover 5.63:1.

Today's blue is ΔE 3.1 from Tailwind blue-700, close but not identical. The warm greys and Plex
keep it from reading as the default.

The maintainer asked for more colour options with the same layout and placement. The Skills table
is shown in 5 colour systems plus today's, each with a colour spec card. Canvas rows: "Colour
exploration" (y 17900: page + spec card) and "the same 6 in dark" (y 19800). Layout, type and
status shapes are unchanged; only the 21 colour tokens differ.

| # | Name | Idea | Sources |
|---|---|---|---|
| C0 | Today | Warm-neutral greys + blue `#2D58D0` (for comparison) | Design system v5 |
| C1 | Cobalt | Cool neutral greys + cobalt `#0F62FE`; closest to today | IBM Carbon (g10 / g100) |
| C2 | Nordic | Cool slate + frost teal; blue-grey dark | Nord (Arctic Ice Studio) |
| C3 | Graphite | Black/white; colour only for Different / Can't read | Vercel Geist (approach), Radix amber/red |
| C4 | Green light | Cool greys + go-green `#1A7F37` | GitHub Primer base scales |
| C5 | Night | Blue-black night + sea-glass teal; light theme derived | Tokyo Night (folke) |

**AI-slop audit (2026-11-25, unslop-ui scanner + by-eye catalog).** Scope: approved A01–A14,
dark D01–D14, the design system and the colour boards. Older round boards were not re-checked.
No gradients, glows, emoji icons, left-border cards, hype copy or decorative motion were found.
Fixed:
- The first set had three colour tells, so they were replaced. Paper (Flexoki) used a cream page,
  part of the 2026 "tasteful default". Forest (Radix sage/jade, Everforest) used sage greys and
  forest green. Midnight (Radix violet) used AI-purple. They became Cobalt, Green light and Night.
- Off-scale corner radii (8/10/12/7/4px, 82 places in A and D) were snapped to the design-system
  scale: 9/11/14/5px.
- Pills appear only on labels and counts (the `radius-pill` token) and are now marked
  `unslop-ignore`.

Open (maintainer decision): **Inter is the only typeface**, and the scanner's one remaining
finding (20 hits) is the generic default sans. It was the design system's choice, so it is not
changed.

All of the main text, accent, button, warning, error and Undo-bar pairs were measured at 4.5:1 or
higher in both themes (`tools/palettes.py` in the session scratchpad). Shape-only marks were held to
about today's level (2.2:1 or higher; every mark also has a word). The spec cards show the measured
values. Finding: today's own faint text on the hover tint (`#72726B` on `#F5F5F3`) measures
**4.44:1**, just under 4.5. Not changed; flagged for the pick.

**Phase 3 is done (2026-11-25).** Every screen in the brief's inventory is approved. The canvas ends
with the row "Approved screens — journey order" (y 14080), copies of each winner:

| # | Artboard | Screen | From |
|---|---|---|---|
| 1 | `A01-Skills.dc.html` | S1 Skills table + S2 side panel (hero) | `Winner-Skills.dc.html` |
| 2 | `A02-Skills-Phone.dc.html` | Skills table, phone | `Phone-Skills.dc.html` |
| 3 | `A03-Skills-States.dc.html` | Skills table states | `States-Skills.dc.html` |
| 4 | `A04-Skill-Page.dc.html` | S3 Skill page | `R5-S3-Winner.dc.html` |
| 5 | `A05-Editor.dc.html` | S4 Editor | `R5-S4-A-Card.dc.html` |
| 6 | `A06-New-Skill.dc.html` | S5 New skill | `R5-S5-B-Preview.dc.html` |
| 7 | `A07-Why-Not-Running.dc.html` | S6 Why isn't it running? | `R5-S6-Why.dc.html` |
| 8 | `A08-Needs-Attention.dc.html` | S7 Needs attention | `R5-S7-B-Inbox.dc.html` |
| 9 | `A09-Trash-Backups.dc.html` | S8 Trash & backups | `R5-S8-Trash.dc.html` |
| 10 | `A10-Advanced.dc.html` | S9 Advanced | `R5-S9-Advanced.dc.html` |
| 11 | `A11-Tool-Page.dc.html` | S10 Tool page template | `R5-S10-Tool.dc.html` |
| 12 | `A12-Settings.dc.html` | S11 Settings | `R5-S11-Settings.dc.html` |
| 13 | `A13-Search.dc.html` | S12 Search | `R5-S12-Search.dc.html` |
| 14 | `A14-Not-Found.dc.html` | S13 Not found | `R5-S13-NotFound.dc.html` |

Prototype links (Play mode): top navigation and logo on every desktop screen; Skills table ->
New skill, Fix one by one (Needs attention), side panel Open skill (Skill page) and Why isn't it
running?; Skill page -> Edit (Editor), Why isn't it running?; Editor and other breadcrumbs back;
Needs attention -> Open skill; Advanced -> Shorten (tool page) and Settings; tool page -> AI
settings; Not found -> Go to Skills, Look in Trash, Did you mean; phone sheet -> Open skill.
Not linked: the search palette (S12), buttons that act in place (they show Undo instead).

Dark theme row (2026-11-25, maintainer asked "dark theme for all pages"): "Approved screens —
dark theme" (y 15980), `D01`–`D14`, the same 14 screens in the same order, opening in dark and
linked to each other in Play. Desktop screens already had dark via the moon button (they now
start dark in this row; the moon switches back). Phone (`D02`) and states (`D03`) had no dark
before: they got the design system's dark values, and their fixed colours (logo, Undo bar,
refresh icon) were swapped for dark ones. The light originals `A02`/`A03` still have no theme
switch.

Design system updated with the round-5 patterns (maintainer said yes, 2026-11-25; design system
version 5):

- **New components (5):** Segmented (`sm-seg`: Read / File text, Write / Preview, theme), Chip
  (`sm-chip` + `sm-chip__box`: pick places), Document (`sm-doc`, `sm-filetext`), ChecksGrid
  (`sm-chk` with `is-ok` / `is-fail` / `is-unknown` / `is-skip`), Compare (`sm-compare`,
  `sm-compare__side--new`, `sm-choice`, `sm-choice__snip`).
- **Extended:** Button gained Accent (`sm-btn--accent`), Quiet (`sm-btn--quiet`) and the page size
  (`sm-btn--page`); Field gained `sm-label`, `sm-hint`, `sm-textarea` (+ `--file`),
  `sm-checkbox`, `sm-rule`.
- **Tokens:** size `control-page` 38px; type styles `title-doc` 19, `doc` 15/25.5, `file-text`
  13 mono.
- **README rules:** mono also for exact file content; Unknown has its own mark in checks; layout
  for non-table pages (breadcrumb, pinned title row, reading width); button heights (38 page,
  36 in cards, 46 panel primary); guard dialogs make the safe choice the accent button.
- The canvas's installed copy (`project/ds/skills-manager/tokens.json`) was refreshed from it.
- Naming note: the approved artboards use local class names for some of these (`tick`, `seg`,
  `choice`, `chk`); the system's names above are the ones to use when building.

### Earlier status notes

Round 3 · Critique and fix — done. All 10 fixes approved and applied on 2026-11-24:
`Winner-Skills.dc.html` (readable grey text, outlined New skill, working primary button with
Undo bar, pinned side panel, focus rings everywhere, 44 px icon buttons on phones, keyboard hint
line, "Show 50 more"), plus `Phone-Skills.dc.html` (390 px, one agent at a time, bottom sheet,
bottom tab bar) and `States-Skills.dc.html` (first launch, loading, no agents found, files
changed on disk).

Round 4 · Lock the system — done 2026-11-24 (link above).

Round 5 · Roll out — **done 2026-11-25**, in journey order from `design-brief.md`. Key screens get 3
variations each (S3 Skill page, S4 Editor, S5 New skill, S7 Needs attention; S2 side panel
states are already covered by the hero); supporting screens get one version each (S6 Why
isn't it running?, S8 Trash & backups, S9 Advanced, S10 tool page template, S11 Settings,
S12 Search, S13 Not found). Finish with an "Approved screens" row.

How round 5 artboards are built: the design system ships stylesheet classes only (no script
components), so each artboard inlines the system's exact tokens (light + dark, token names as in
`tokens.json`) and its `sm-*` classes from `components/bundle.css`. New patterns introduced in
round 5 (to offer for the system at the end): `sm-btn--accent` (compact filled primary, e.g.
Edit), `sm-btn--quiet` (text-only button, e.g. Move to Trash), `sm-chip` (agent + status chip),
`sm-doc` (rendered skill document, incl. mono code blocks).

### Round 5 · Supporting screens — approved by the maintainer (2026-11-25)

Canvas row "Round 5 · Supporting screens (one version each)" (y 12340), left to right:

| Screen | Artboard | What it shows |
|---|---|---|
| S6 Why isn't it running? | `R5-S6-Why.dc.html` | git-workflow: a checks × places grid (Found, Readable, Switched on, Settings allow it, Actually loaded = Unknown); the first failure (Claude Code's settings) as one next step: "Open the settings file", "Check again". |
| S8 Trash & backups | `R5-S8-Trash.dc.html` | One trash list with where each item came from and why it's there, Restore + Undo; recent changes with Undo; download / load backup (load previews first). |
| S9 Advanced | `R5-S9-Advanced.dc.html` | Four goal groups (Add skills, Check my setup, AI assist, Settings), one sentence per tool. |
| S10 Tool page template | `R5-S10-Tool.dc.html` | Shorten as the example: 1 choose, 2 exactly what is sent and to where, 3 result as Now / Suggested with "Use it", folded raw reply; the error sits next to its button. Tweak `state`: ready / result / error. |
| S11 Settings | `R5-S11-Settings.dc.html` | Look (theme, text size, dates), AI connection (status says it works only after a test answers; tweak `connection`), Upkeep (re-read folders, data folder path). Saves immediately. |
| S12 Search | `R5-S12-Search.dc.html` | Palette over the page: Skills, then Actions, then Pages; no results says what was searched and offers "Did you mean …?". |
| S13 Not found | `R5-S13-NotFound.dc.html` | "There's no skill called test-drivn-development", Did you mean, Go to Skills, Look in Trash. |

Consistency check (2026-11-25): one header everywhere (same nav, count 3, search pill, theme,
help); same tokens and status marks; page titles 30 px; title-row and page-footer buttons 38 px
like the hero's "New skill", buttons inside cards 36 px (`control`), panel primary 46 px
(`control-lg`). Fixed drift: S4 title was 26 px, S5 Create 42 px, S13 buttons 40 px, S12 search
wording now matches the header ("Search skills and actions"). Same sample data across screens
(test-driven-development differs in OpenCode, security-review unreadable in Codex, git-workflow
off in Claude Code settings).

### Round 5 · S7 Needs attention — picked: B · List and detail (2026-11-25)

The maintainer ranked B > C > A and chose B (I had recommended A). B lets you see every problem
and jump to any one; C's "Fix all…" batch stays a possible later addition.

Canvas row "Round 5 · S7 Needs attention · Variations" (y 10740). The 3 problems from the hero's
banner: security-review can't be read in Codex; debugging-and-error-recovery differs in Codex;
test-driven-development differs in OpenCode. Every option: what happened, which agent, Now →
After, Fix / Skip / Open skill, Undo; for a different copy the user picks which version wins
(nothing preselected, losing copy goes to Trash); the empty state says what was checked; the top
bar count updates.

| Option | Artboard | Idea |
|---|---|---|
| A · One at a time | `R5-S7-A-Focus.dc.html` | One big card, a progress bar ("1 of 3"), an "Up next" list underneath. |
| B · List and detail | `R5-S7-B-Inbox.dc.html` | Like an inbox: list on the left (To fix / Skipped / Fixed), the chosen problem on the right; J/K keys. |
| C · Grouped | `R5-S7-C-Groups.dc.html` | Problems grouped by kind with rows that open in place; "Fix all 2…" for different copies shows a preview and has one Undo. |

### Round 5 · S5 New skill — picked: B · Live preview (2026-11-25)

The maintainer chose B as recommended: creating a skill writes new files into agent folders, so
"show before you change" applies — the new row, file paths and SKILL.md start are visible before
anything is written.

Canvas row "Round 5 · S5 New skill · Variations" (y 9000). Demo skill name: explain-code. Every
option: live plain-word name rules (small letters, numbers and dashes; up to 64 characters; starts
and ends with a letter or number, no double dashes; not already used) with a one-click fix
("Use explain-code"), a description with a 1,024-character count, several places, a template
(Blank / Step by step / Checklist), "Create in N places" with Undo, and the reason Create is
disabled said in words.

| Option | Artboard | Idea |
|---|---|---|
| A · One form | `R5-S5-A-Form.dc.html` | One calm column: four questions top to bottom, full rule list under the name, places with their folder paths. |
| B · Live preview | `R5-S5-B-Preview.dc.html` | Form on the left; on the right "What will be created": the new row as it will look in the table, the new file paths and the first lines of SKILL.md. |
| C · Quick dialog | `R5-S5-C-Dialog.dc.html` | A dialog over the Skills table: same four answers, compact; one line shows the first name problem only. |

### Round 5 · S4 Editor — picked: A · Save-to card (2026-11-24)

The maintainer chose A as recommended: editing is an everyday job, so one step; the Save-to card
still says what happens in each place before saving.

Canvas row "Round 5 · S4 Editor · Variations" (y 7200). Same skill; the demo edit changes step 3
("…, then commit.") and adds one "Don't" line. Every option has: separate Description field,
Markdown content in mono (file text), "Save to" with OpenCode (different copy) unticked by
default and marked, "Save to N places" with Undo, and the "Leave without saving?" guard on Cancel.

| Option | Artboard | Idea |
|---|---|---|
| A · Save-to card | `R5-S4-A-Card.dc.html` | One page: form on the left with Write / Preview switch; a "Save to" card on the right with a note per place; Save in the bar that stays on screen. |
| B · Side by side | `R5-S4-B-Split.dc.html` | File text and live preview next to each other; a bottom bar with Save-to toggles and Save. |
| C · Review before save | `R5-S4-C-Review.dc.html` | Two steps: Write, then Review: a line-by-line "What changes" view and a Now → After per place before Save. |

### Round 5 · S3 Skill page — picked: B · Row on top + C's File text switch and sticky Edit bar (2026-11-24)

Winner artboard: `R5-S3-Winner.dc.html` (same row, x 4560). The maintainer asked me to choose
the best ("continue and choose the best"). Why: B keeps "one table of truth" consistent (the
same squares and side panel as the Skills table), so a user who lands from search can act
without going back; C's File text switch shows exactly what is on disk (trust), and its sticky
title bar keeps Edit in reach on long skills. A rejected as a second way of acting on agents;
C as a whole rejected because nothing in it is actionable and all details show up front.

Canvas row "Round 5 · S3 Skill page · Variations" (y 5300). Example skill:
`test-driven-development` (On in Claude Code, Codex, Shared folder; Different in OpenCode; Not
here in This project).

| Option | Artboard | Idea |
|---|---|---|
| A · Reader | `R5-S3-A-Reader.dc.html` | Reading first: one sentence plus five small agent chips; clicking a chip opens a one-line note with the action; quiet Details column on the right. |
| B · Row on top | `R5-S3-B-Row.dc.html` | The skill's row from the table, enlarged: five real squares; clicking one opens the same side panel as the table; Details card below it. |
| C · Fact sheet | `R5-S3-C-Facts.dc.html` | Evidence first: sticky title bar with Read / File text switch; "On this page" outline; Facts column with each place, its path, list-space meter, files, history. |

### Round 2 · Variations (done)

| Option | Artboard | What it pushes |
|---|---|---|
| A · Focus | `R2-A-Focus.dc.html` | Hierarchy: attention banner leads; rows stay quiet unless something is wrong; panel's status word and primary button are the biggest things on screen. |
| B · Inline answer | `R2-B-Inline.dc.html` | Signature: no side panel — the answer opens inside the table, right under the square you clicked, with a pointer; keyboard hints from Console. |
| C · Fine print | `R2-C-Craft.dc.html` | Craft: refined type and spacing, drawn status marks, agent monograms, "Now → After" preview, working light/dark switch. |

### Round 1 · Directions (done)

| Option | Artboard | Idea |
|---|---|---|
| A · Console | `Main.dc.html` | Dark, dense, keyboard-first (Linear/Raycast). Signature: key hints and a focus ring that moves square to square. |
| B · Paper | `R1-B-Paper.dc.html` | Light, airy, sentence-first (Notion/Obsidian). Signature: every row and the panel speak a plain-English verdict. |
| C · Tiles | `R1-C-Tiles.dc.html` | Bright, visual grid of real squares (echoes the logo). Signature: the status legend doubles as a filter. |

## Picks so far

| Round | Pick | Why |
|---|---|---|
| 1 · Directions | B · Paper | Closest to "trust and clarity first, in plain words": plain-sentence verdicts per row and a note-like panel; calmest of the three. Recommended and chosen 2026-11-24. |
| 2 · Variations | C · Fine print + A's attention banner | C's craft and "Now → After" preview make the trust promise visible and are marketing-ready; A's banner puts attention first as the brief orders. B's inline answer rejected: rows jumping breaks "calm" at 200 skills. Chosen 2026-11-24. |
| 5 · S3 Skill page | B · Row on top + C's File text switch and sticky Edit bar | Same squares and panel as the table (one way to act); File text shows the truth on disk. Chosen by me at the maintainer's request, 2026-11-24. |
| 5 · S4 Editor | A · Save-to card | One step for an everyday job; a note per place says what saving does there (OpenCode's own copy is left out unless ticked). Recommended and chosen 2026-11-24. |
| 5 · S5 New skill | B · Live preview | Shows the new table row, file paths and SKILL.md start before anything is written. Recommended and chosen 2026-11-25. |
| 5 · S7 Needs attention | B · List and detail | Maintainer's ranking B > C > A: see every problem at once and jump to any; Skipped and Fixed stay visible. Chosen 2026-11-25 (I had recommended A). |
| 5 · Supporting (S6, S8–S13) | One version each, approved as built | After a consistency pass (title size, button heights, search wording). Approved 2026-11-25. |
| 5 · Approved screens | Row of 14 in journey order with prototype links | Phase 3 finished 2026-11-25. |
