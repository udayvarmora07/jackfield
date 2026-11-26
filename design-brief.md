# Skills Manager UI — Design brief

Self-contained handoff for phase 3 (UI) of the `/uxui-workflow`. Written 2026-11-24.
Full detail lives in `requirements.md` and `ux-brief.md`; this brief stands on its own.

## The product

Skills Manager is a local web app (Python stdlib backend on `127.0.0.1`, Vue vendored in the
repository, no build step) that shows and manages the skills of AI coding agents — Claude Code,
Codex, OpenCode, Cursor, Gemini, Command Code, the shared `~/.agents` folder and project folders —
in one place. The files on disk are always the truth. The current UI works (no crashes, no
accessibility violations) but a full test found about 100 problems: statuses that are wrong or
hidden, risky actions without a preview, one job spread over many pages, engineer language, and a
plain admin-panel look. This redesign fixes trust and clarity first, then makes it look great.

**Problem statement:** developers who use several AI coding agents need one place to see, fix and
keep their skills in step across all those agents, because their skills are scattered in hidden
folders and quietly drift apart, and the current UI sometimes shows a wrong or confusing status,
so they don't trust it enough to change files.

## Primary user and context

- A developer using 2–4 AI coding agents with 50–200 skills (must still work at 1,000); mix of
  beginners and experts. Secondary: a developer trying it for the first time from GitHub.
- At a desk, mid-coding, laptop or desktop (1280–1920 px), sometimes a narrow window; light or
  dark theme; keyboard-heavy. Short visits with one specific question.
- Worries: breaking another agent's setup, silent overwrites, private skill text leaking to AI.

## Chosen concept: "One table of truth" (hybrid)

**Mental model:** "My setup is a grid. Skills are rows, agents are columns, and each square tells
me — in one plain word — whether this agent has this skill, whether it's on, and whether it's the
same copy as the others."

Plus: one global search (`/` and Ctrl+K) to jump to any skill, action or page; and one quiet
"Needs attention" count with a one-at-a-time fixer instead of warnings everywhere.

## Core flows (condensed)

1. **Find and read:** `/` or Ctrl+K → type → Enter → skill page. No results → Clear filters +
   close-name suggestions.
2. **Turn on/off for one agent (success test, under 2 min for a newcomer):** click the agent's
   square → side panel states it in one sentence → Turn off → square updates only after it really
   changed → Undo. If the agent's own settings turn it off, the square says "Off in Codex
   settings", never green.
3. **Copy or sync:** click an empty square → "Add here" with a preview of what is copied → Undo.
   "Different" square → side-by-side versions → choose which copy wins → preview → Make match →
   Undo. Evenly split: the user picks; nothing preselected. Several rows at once with one Undo.
4. **Create:** New skill → name with live plain-word rules → multi-line description → pick several
   agents → Create → skill page opens.
5. **Edit:** Edit (address becomes `…/edit`) → "Save to" lists agents; an agent holding a
   different copy is unticked by default and marked → Save → Undo. Unsaved-changes guard.
6. **Why isn't it running?** Per-agent checklist: found / readable / on / settings allow / actually
   loaded = "unknown". Each failure has one next step.
7. **Needs attention:** count in the top bar → one item at a time with what, which agent, fix
   preview → Fix / Skip / Open skill → Undo. Empty state says what was checked.
8. **Files changed on disk:** quiet banner "Skills changed on disk (2). Refresh."
9. **First launch:** "Looking for your agents…" → "Found 3 agents and 142 skills" → table → one
   hint: "Click any square to turn a skill on or off for that agent."

## Navigation model

- **Global top bar:** Skills Manager · Skills · Needs attention (n) · Trash & backups · Advanced;
  right side: one search (`/`, Ctrl+K), theme, help. Global "changed on disk" banner. One Undo
  area for the latest change; messages close themselves and never follow the user across pages.
- **Contextual:** the table's side panel (acts on one square); the skill page (read, edit,
  why-isn't-it-running, trash/delete).
- **Advanced** is grouped by goal: Add skills (Install, Templates, Profiles); Check my setup
  (Quality, Where agents look, Doctor); AI assist (Connection; Write, Test, Shorten, Find
  conflicts); Settings. About 20 tool pages share one page template.
- **Phone:** bottom tab bar with the same four items; the table shows one agent at a time
  ("Showing: Codex ▾"); tapping a row opens the skill page.

## Screen inventory (journey order)

| # | Screen | Primary action | Content priority | Type |
|---|---|---|---|---|
| S1 | **Skills table** | Click a square to act | Attention count (if >0); search, "Only problems", agent focus; rows: name + one-line description + one plain word per agent (On / Off / Different / Can't read / –); total | Key · **Hero** |
| S2 | Square side panel | Turn off / Turn on / Add here / Make match / Fix (per state) | One-sentence status; preview of the change; action; folded details | Key |
| S3 | Skill page | Edit | Name, description; agent row; readable document; details (files, size, history) | Key |
| S4 | Editor | Save | Description; content (Write / Preview); "Save to" with different-copy warnings | Key |
| S5 | New skill | Create | Name (live rules); description; agents (several); template | Key |
| S6 | Why isn't it running? | Follow the next step | Per-agent checklist incl. "unknown" | Supporting |
| S7 | Needs attention | Fix (with preview) | Count to go; current item; remaining list | Key |
| S8 | Trash & backups | Restore | One trash list with origin; undoable recent changes; backup download/load | Supporting |
| S9 | Advanced | Open a tool | Goal groups, one sentence each | Supporting |
| S10 | Advanced tool page (template) | One per tool | What it does; what it reads/sends (AI: preview + cost); inputs; plain result; folded raw details; errors next to their button | Supporting |
| S11 | Settings | — (saves immediately) | Theme, text size, region, AI connection (never "Connected" on failure), maintenance | Supporting |
| S12 | Search / command palette | Go to result | Skills, then actions, then pages | Supporting |
| S13 | Not found | Go to Skills | Plain message, link to Trash for missing skills | Supporting |

**States the S1 design must cover:** first launch (scanning → summary + hint), loading
placeholders, no agents found, no skills, no results, files-changed banner, 1,000 rows, phone
one-agent view. **Square states (S1/S2):** On, Off, Off in agent settings, Missing (–), Different,
Evenly split, Can't read, Unknown, working, failed, done + Undo.

## Hero screen to design first

**S1 · Skills table with its side panel (S2).** It carries the success task and the first 10
seconds of value, it is where trust is won or lost, and it is what makes the product unique (all
agents side by side). It sets the design language for everything else.

## UX principles

1. **Tell the truth, or say "unknown".** No green unless checked; every status names its agent.
2. **Show before you change, offer Undo after.** Never touch another agent's files silently.
3. **One place for each thing.** One search, one problem list, one trash, one name per idea.
4. **Plain words first, details on request.** Raw paths, numbers and codes live under "Details".
5. **Calm by default.** Problems are counted in one place and shown where they matter.

**Voice:** short, plain, specific — what happened, to which skill, in which agent, what to do
next. "Codex has a different copy of code-review." "Couldn't reach your AI service. Check the
address in AI settings." "Uses about 3% of Claude's skill list space." Never raw error codes,
regular expressions, internal scope ids or `<redacted>` in the main text.

## Brand and tone

- **Personality:** calm, clear, trustworthy.
- **Must never feel:** scary to click, like a cluttered admin panel, full of engineer words, toy-like.
- **References (liked):** Linear, Vercel, Obsidian, Notion, Raycast, GitHub. Disliked: none named.
- **Competitors:** each agent's own CLI and settings files; hand-managing hidden folders; registry
  sites such as skills.sh. Differentiator: all agents side by side, with statuses you can trust.
- **Existing assets:** a logo mark (grid of squares, `skillsmgr/webui/logo.svg`) and agent icons
  for Claude Code, Codex, OpenCode and others. The current `DESIGN.md` (cool bone ground, IBM Plex
  Sans + Plex Mono for identifiers, one teal accent, cool dark palette) is a **starting point, not
  a rule** — the look is open to change. Its building blocks (one shared set of type sizes,
  colours, radii; 7 button styles) are consistent; the weaknesses are page layout, heavy monospace,
  identical white boxes and competing red/orange/green badges.

## Platform, breakpoints, accessibility

- Local web app in any modern browser; English only.
- Desktop first: design at 1440 px, check 1280 and 1920; must work at 390 px phone width (main
  content visible on the first screen); also narrow desktop windows.
- Light and dark themes, both first-class.
- WCAG 2.2 AA: keyboard reachable with visible focus, contrast, screen-reader labels; colour never
  the only signal (every square has a word, not just a colour or dot).
- Technical constraints for the build: no build step, no new runtime dependencies, Vue vendored,
  stdlib backend, SQLite schema unchanged, no new CLI commands or Store methods without approval.

## Must have vs. won't have

**Must have:** true statuses (or "unknown"); preview before changing another agent's files and Undo
after; plain words with details on request; fast, clear everyday jobs on desktop and usable on
phone; 50–200 skills smooth, 1,000 usable; nothing sent to an AI service without a preview; WCAG
2.2 AA; light and dark.

**Should have:** polished first launch; advanced tools grouped in Advanced; changed-on-disk
detection and Refresh; a calm, trustworthy visual refresh.

**Won't have (this version):** accounts, cross-computer sync, cloud hosting or remote access; other
languages; new CLI commands, Store methods or database changes without approval; a build step or
new runtime dependencies; a dedicated "clean-up helper" (not in requirements); detailed redesign of
Profiles and Templates beyond the shared tool-page template. Do not invent features beyond this
brief.

---

# Feature: Agent tracking — design brief (added 2026-11-26)

Self-contained handoff for phase 3 of this feature. Full detail: the feature sections of
`requirements.md` and `ux-brief.md`. **Status: approved by the maintainer on 2026-11-26 (concept, flows,
screens and backend contract).**

## The feature

A place to choose which coding agents, project folders and Advanced tool groups Skills Manager
shows, and to add agents it doesn't know yet (a name and a folder). Today the agent list is fixed
in code and project folders come only from the folder the app was started in.

**Problem statement:** developers who use some, but not all, of the agents Skills Manager knows
need to choose what the app shows and to add agents it doesn't know, because today every agent
found fills the table, counts and choices, and a new agent can't be added at all.

## Primary user and context

The same developer as above (2–4 agents, 50–200 skills) with more agents installed than they use.
An occasional, deliberate visit: day one, after installing a new agent, or when the table feels
too wide. Worries: that "stop tracking" deletes something; losing sight of skills only in that
agent; pointing the app at a wrong folder.

## Chosen concept: one "What to track" page, with doorways from the table

**Mental model:** "A list of what the app watches. I tick what I use." One page holds every
choice; the Skills table offers shortcuts (column header menu, project picker, a one-time "Found
Gemini" notice, the "no agents" empty state, Ctrl+K) that run the same actions. "Not tracked"
means ignored completely; files on disk never change.

## Core flows (condensed)

1. **Stop tracking (benchmark, < 1 min):** untick Cursor (or column header ▾ → "Stop tracking
   Cursor…") → confirm: "The Cursor column and its counts leave the table. 12 skills live only in
   Cursor and will no longer show. Nothing on disk changes." → Stop tracking → Undo. The last
   tracked agent can't be unticked ("At least one agent stays tracked").
2. **Track a known agent:** tick → saved at once, column appears, Undo. Not found yet: allowed;
   shows once its folder exists.
3. **Add other agent (benchmark, < 1 min):** name + folder (+ optional folder inside projects),
   checked live in plain words (missing, not a folder, not readable, outside home, already
   tracked by X, name taken) → preview "Kilo · 9 skills found" → Add → neutral mark, new column,
   Undo.
4. **Agent details (fold-out):** folders read, "Also reads Claude Code's folder", "Count project
   folders" switch; custom agents: Edit, Remove (confirm like 1).
5. **Project folders:** Add (live check + preview of skill folders found) → switch in the table
   toolbar "Project: api ▾" (None, folders, Add…, Manage…) → Remove is immediate with "Its files
   are unchanged" + Undo. Missing folders greyed, never shown as working.
6. **Tool groups:** switch off AI assist → gone from Advanced, search and Settings, "Its settings
   are kept" + Undo. An open tool of that group says "switched off" with Turn it on.
7. **Newly found agent:** auto-tracked until the user first changes the list; after that one
   quiet notice on Skills: "Found Gemini (14 skills). Track it?" Track / Not now (never asked
   again).
8. **Broken settings file:** everything found is shown; one notice plus a banner on the page
   with Reset (the broken file is kept as a copy).

## Navigation and screen inventory (journey order)

Home: **What to track**, `/settings/tracking`, under Advanced → Settings (Settings' first row
leads to it: "What to track · 4 agents, 2 project folders, 3 tool groups"). It can't be switched
off. Untracked agents and off groups are absent everywhere else.

| # | Screen | Primary action | Content priority | Type |
|---|---|---|---|---|
| S14 | **What to track** | Tick/untick an agent | Summary line; Agents (checkbox rows: mark, name, plain status, skill count, Details fold; automatic Shared folder row; Add other agent); Project folders (rows with status and "Showing in the table"; Add; Remove); Tool groups (3 switches, one sentence each) | Key · **Hero** |
| S15 | Stop tracking / Remove confirm | Stop tracking Cursor | What leaves; skills only here (foldable names); "Nothing on disk changes" | Key |
| S16 | Add other agent / Edit agent | Add agent | Name; folder; folder inside projects; live checks per field; preview line | Key |
| S17 | Agent details (row fold-out) | — (saves at once) | Folders read; also reads; Count project folders; custom: Edit, Remove | Supporting |
| S18 | Add project folder | Add folder | Path; live check; skill folders found; "Show it in the table now" | Supporting |
| S19 | Project picker (table toolbar) | Switch project | None; folders (current ticked, missing greyed); Add…; Manage… | Supporting |
| S1+ | Skills table changes | — | Column header menu; Found-agent notice; "No agents are tracked" empty state with Choose agents | Key (existing) |
| S9+/S10+/S11+ | Advanced / tool page / Settings changes | — | Off groups absent; all-off line; tool "switched off" state; Settings first row | Supporting (existing) |

**States S14 must cover:** first time ("Every agent found is tracked. Untick any you don't
use."); returning; loading; saving a row; save failed (row reverts, reason beside it); changed in
another window; broken-file banner; last agent (disabled + reason); not found; folder missing;
phone single column; keyboard only.

## Hero screen to design first

**S14 · What to track with its confirm S15.** Every core job happens here, and it carries the
feature's biggest worry. Its rows, plain statuses and the "Nothing on disk changes" confirm set
the language for S16, S18 and the table shortcuts. Reuse the approved checkbox-row pattern
("Save to", "Add it to").

## UX principles (in addition to the five above)

1. **Tracking is a view, never a change on disk.** Every confirm and message says so.
2. **Say what leaves before it leaves; Undo after.** Adding needs no confirm; hiding does.
3. **One home, many doorways.** Choices live only on S14; table entries are shortcuts.
4. **Agents in plain words, folders under Details.**
5. **Quiet and occasional.** No setup step; at most one notice per new agent.

**Voice:** "Stopped tracking Cursor. Nothing on disk changed." · "That's Claude Code's folder.
It's already tracked." · "AI assist is off. Its settings are kept." Never "scope", "untrack" or
raw error codes in the main text.

## Brand, platform, accessibility

Unchanged from the main brief above, and the look follows the approved **design system v11**
(https://claude.ai/artifact/27HHwcNGwDAZ2cne6xW4ei): warm-neutral greys, one blue accent, IBM
Plex Sans/Mono, one-colour agent marks, checkbox rows for choosing places. Desktop first at 1440
(check 1280, 1920), works at 390 px; light and dark both first-class; WCAG 2.2 AA (keyboard,
visible focus, contrast, screen-reader labels, colour never the only signal). Screens go on the
existing canvas https://claude.ai/artifact/2bRpEoQ192WY2Tp7dYsXdq.

**Marks (B5):** draw one-colour marks for **Cursor, Gemini and Command Code**, matching the
existing marks for Claude and OpenCode (neutral icons stay for Codex, Shared folder and This
project). Custom agents get one neutral mark (B4).

## Backend the design relies on (signed off 2026-11-26)

New file `<data>/tracking.json` (tracked agents, custom agents, project folders + showing,
tool groups, a `chosen` flag, `seen` list, `revision`); new calls `GET /api/tracking`,
`PUT /api/tracking` (whole document, revision-checked; Undo = PUT the previous one) and
`POST /api/tracking/check-folder` (read-only live check + preview). Existing routes filter by the
tracked set on the server. Full contract in `ux-brief.md`. The design must not depend on anything
beyond it: for example, skills-only-here names come from `GET /api/tracking`.

## Must have vs. won't have

**Must have:** choose agents in plain words; not tracked = absent everywhere; say what leaves,
then Undo; known list + custom agents; project folders shown one at a time; tool groups off with
settings kept; live plain-word folder checks inside home; any time, never a setup step; the
new-agent notice; at least one agent tracked; broken-file fallback; phone, light and dark, AA.

**Should have:** marks for Cursor, Gemini and Command Code.

**Won't have:** CLI changes (`--scope` unchanged); new known agents beyond today's (Cline, Kiro,
Amp…); uploaded logos or a choice of marks for custom agents; removing settings when a group is
switched off; switching off everyday pages or single tools; a setup wizard; a new top-level
navigation item. Don't invent features beyond this brief.
