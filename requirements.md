# Skills Manager UI — Requirements

Phase 1 output of the `/uxui-workflow` (requirements → UX → UI). Written 2026-11-24.
Scope: the local web UI of Skills Manager (`python3 -m skillsmgr webui`), not the CLI.

## Summary

Skills Manager is a local web app that lets developers see and manage the AI coding-agent
skills spread across Claude Code, Codex, OpenCode, the shared `~/.agents` folder and project
folders. The product already has many features, but a full test on 2026-11-24 showed that its
screens sometimes show a wrong or hidden status, use engineer language, and spread one job over
several pages. This work makes the UI trustworthy and clear first, then makes it look great, so
the maintainer and other developers can manage their skills confidently — and so the project is
ready to be shared publicly once it is complete.

## Problem framing

### Problem statement

Developers who use several AI coding agents need one place to see, fix and keep their skills in
step across all those agents, because their skills are scattered in hidden folders and quietly
drift apart, and the current UI sometimes shows a wrong or confusing status, so they don't trust
it enough to change files.

### Primary user snapshot

- **Who:** a developer using 2–4 AI coding agents with 50–200 skills — some self-written, some
  installed, some created by an agent.
- **Context:** at their desk, in the middle of coding. Arrives with a specific question, wants a
  fast answer, then goes back to their code.
- **Jobs:** find and read a skill; turn a skill on or off for an agent; copy or sync a skill
  between agents; create or edit a skill.
- **Frustrations:** skills hide in different folders; copies drift apart; unclear which agent
  really uses which skill; tool screens full of words like "scope", "baseline", "listing budget".
- **Worries:** breaking another agent's setup; losing work through a silent overwrite; private
  skill text leaking to an AI service.
- **Secondary user:** a developer who just found the project on GitHub and needs to understand
  what it does within about 10 seconds.

### Key scenarios

1. **"Why didn't my skill run?"** Claude Code ignored a skill. The user opens the app and sees at
   once that it is turned off in Claude's settings, turns it back on, and moves on.
2. **"Make Codex match."** The user improved a skill in Claude Code. The app shows Codex's copy
   differs and exactly what will change; they apply it, with Undo available.
3. **"Too many skills."** With 150 skills the agents feel slow. The user finds large, duplicated or
   rarely needed skills and turns some off for one agent only.
4. **"A new skill."** The user writes a skill, picks which agents get it, saves — and is sure no
   other copy was overwritten.
5. **"First launch."** A new developer installs it from GitHub and opens it. Their agents and
   skills are already found and shown, with one short hint about what to do next.

### How might we

1. How might we make every status on screen something people can trust at a glance?
2. How might we let people change one agent's skills without fear of breaking another's?
3. How might we explain each agent's behaviour in plain words, with technical detail only on request?
4. How might we keep everyday jobs fast while the powerful tools stay within reach?
5. How might we make the first 10 seconds show the app's value, with no setup?

## Problem

- **Pain:** trust and clarity, then looks. The maintainer's first feeling was "it could look much
  better" (no specific complaint). A full test of every page, tool, dialog and component on
  2026-11-24 (five isolated sandboxes, AI browser agents, automated accessibility scan) found
  about 100 problems, 0 crashes, 0 console errors and 0 automated accessibility violations. The
  problems fall into seven patterns:
  1. **Status that is wrong or hidden** — a skill turned off in Claude's settings shows green with
     every switch on; AI settings shows "Connected" next to "Connection refused"; "Turned off 0"
     while two skills have turned-off copies; Contradiction check reports 0 for "use tabs" vs
     "use spaces"; History says "No recorded changes" after a save.
  2. **Risky actions without a preview** — "Save to 4 places" silently overwrites a different Codex
     copy; "Make Codex's copy match" and "Replace matching entries" act at once.
  3. **One job spread over many places** — up to 5 search boxes; "Needs care / need review / Needs a
     look / Inbox" for one idea; "Trash" vs "Agent trash"; "Sync map" vs "Map"; command-palette
     names that differ from page titles.
  4. **Engineer language** — "agent scopes", "Shelf / Exact instances", "reading window", "listing
     budget", "ablate", raw errors such as `[Errno 111]` and regular expressions, mixed units
     (tokens, characters, words).
  5. **Feedback in the wrong place or missing** — errors appear at the top while the user clicks
     lower down; toasts stay across pages; Refresh/Rebuild give no success message; raw JSON results.
  6. **Wasted space and overload** — one heading per letter on Skills (about 5 of 24 skills above
     the fold; none on a phone); long raw paths in dialogs; 14 AI tools in one flat list.
  7. **Plain, admin-panel look** — consistent building blocks and good dark mode, but every page is
     the same white boxes, heavy monospace, competing red/orange/green badges.
- **How people cope today:** open hidden folders by hand, use each agent's own CLI, or trust the UI
  and occasionally overwrite or miss something.
- **Why now:** no human has tested the UI by hand (all QA so far was done by AI agents), and the
  maintainer plans to market the project once it is complete and good.
- Evidence (screenshots, per-area reports) from the 2026-11-24 test was kept in the session
  scratchpad, outside the repository; the findings above are the durable summary.

## Goals and success metrics

1. A new developer can find a skill and turn it off for one agent in **under 2 minutes, without
   reading docs**.
2. **The screen never shows a wrong status** — every status on screen matches the files and
   settings on disk, or clearly says it is unknown.
3. After 1 and 2: polished enough to show publicly (GitHub, demo video) for marketing.
- Business model: free, open-source developer tool; no revenue goal for this version.

## Users

### Primary user

The maintainer and other developers who use several AI coding agents — a mix of beginners (one
agent, first skills) and experts (every agent, many scopes). Design for both: simple by default,
details on request.

### Secondary users

A developer who just found the project on GitHub and is trying it for the first time.

### Roles and permissions

Single user on their own computer. No accounts, no roles, no sign-in. The app can only touch
folders on that computer that belong to the user.

### Context of use

At a desk, mid-task, usually a laptop or desktop screen (1280–1920 px wide), sometimes a narrow
window; light or dark theme. Keyboard-heavy users. Short focused visits with a specific question.

## Core jobs (ranked)

1. Find and read a skill.
2. Turn a skill on or off for an agent.
3. Copy or sync a skill between agents.
4. Create or edit a skill.

Less frequent but kept: check quality, back up and restore, install skills, AI-assisted tools.

## Scope

### Must have

- Fix the high-risk problems found on 2026-11-24 first (wrong status, silent overwrite, broken or
  unusable tool features, off-screen errors).
- Every status on screen is true, or explicitly says "unknown".
- Before changing another agent's files: show what will change, then offer Undo afterwards.
- Plain words by default, with a "Details" option for technical facts.
- The four everyday jobs are fast and clear on desktop and usable at phone width.
- Works well with 50–200 skills and still usable at 1,000.
- Nothing leaves the computer without a preview of exactly what is sent and where.
- WCAG 2.2 AA; light and dark themes.

### Should have

- A polished first launch: the user's agents and skills found automatically, with one short hint.
- Advanced tools (14 AI tools, Quality, Workspaces, Doctor) kept but grouped in one "Advanced" area.
- When files change on disk while the app is open, say so and offer Refresh.
- A visual refresh that feels calm, clear and trustworthy (references below).

### Won't have (this version)

- Accounts, sync between computers, cloud hosting, or access from other machines.
- Languages other than English.
- New CLI commands or Store methods, or database schema changes, without separate approval.
- A build step or new runtime dependencies.

## Content and data

- Skills come from three places: the user, AI agents, and installs from registries or folders.
- The files on disk are always the source of truth; the SQLite index can be rebuilt and is never
  trusted over the files. The app never invents information.
- Sensitive content: skills may hold internal rules, server names or other private text. AI tools
  may send skill text to an outside model only after a preview the user approves.
- Edited by: the user in the app, the user in any editor, and the agents themselves — sometimes at
  the same time.

## Platform and integrations

- Local web app served by the Python stdlib backend on `127.0.0.1` (the localhost binding is the
  only security boundary); opened in any modern browser.
- Desktop first, must work at phone width; light and dark.
- Reads and writes the skill folders of Claude Code, Codex, OpenCode, Cursor, Gemini, Command
  Code, the shared `~/.agents` folder and project folders; reads each agent's settings files.
- Optional AI providers chosen by the user (Anthropic, OpenAI-compatible, local models).
- Works offline except for registry installs and AI tools.

## Constraints

- Locked technical rules (from `AGENTS.md`): filesystem stays the source of truth; SQLite schema
  and `SCHEMA_VERSION` unchanged; CLI stdlib-only; web UI with a stdlib backend, no build step, no
  new runtime dependencies, Vue vendored in the repository, binds 127.0.0.1 by default; no new
  CLI commands or Store methods without approval.
- The look and layout are fully open to change. The current `DESIGN.md` is a starting point, not
  a rule.
- Timeline and budget: not fixed; work in order — bugs first, then everyday jobs, then all other pages.

## Brand and tone

- Personality: calm, clear, trustworthy.
- Must never feel: scary to click, like a cluttered admin panel, full of engineer words, toy-like.
- References (liked): Linear, Vercel, Obsidian, Notion (maintainer); Raycast, GitHub (suggested,
  approved). Disliked: none named.
- Competitors: each agent's own CLI and settings files; hand-managing hidden folders; registry
  sites such as skills.sh.

## Lifecycle

- **Install and first launch:** installed from the package; on first open, agents and skills are
  found automatically and shown with one short hint.
- **Returning use:** short, focused visits; the app shows anything that needs attention without
  shouting.
- **Notifications:** none outside the app. Inside the app, problems are counted in one place.
- **Data removal:** trash with restore, permanent delete only with a clear warning; backups can be
  downloaded and loaded.
- **Updates:** new app versions may change the UI; no in-app notes required for this version.

## Edge cases and states

- Empty: no agents found, no skills, no matches for a search or filter combination.
- Errors: unreadable files (bad encoding, broken frontmatter), disabled copies, copies that differ
  (majority vs. split evenly), missing settings files, unreachable AI provider, rejected folders.
- Limits: 1,000+ skills; very long names, descriptions and paths; long Markdown with wide tables.
- Conflicts: files changed on disk while the app is open; the same skill edited in two places;
  restoring into a folder that is already occupied.
- Unknowns: when the app cannot verify whether an agent really loads a skill, it says "unknown"
  instead of implying success.
- Small screens: phone width with the main content visible on the first screen.

## Assumptions (signed off)

All signed off by the maintainer on 2026-11-24 ("all okay").

- A1. Trust and clarity first, then looks.
- A2. Personality calm, clear, trustworthy; references Linear, Vercel, Obsidian, Notion, Raycast, GitHub.
- A3. Must never feel scary to click, cluttered, jargon-heavy or toy-like.
- A4. Plain words by default; "Details" for experts.
- A5. Users: maintainer plus other developers, mixed experience; design for both.
- A6. First launch shows agents and skills found automatically, with one hint.
- A7. Success: under-2-minute everyday task without docs; no wrong status; then marketing polish.
- A8. Locked technical rules stay; look and layout are open; `DESIGN.md` is a starting point.
- A9. Everyday jobs ranked: find and read; turn on/off per agent; copy or sync; create or edit.
- A10. Order: bugs, then everyday jobs, then all other pages.
- A11. Advanced tools kept but grouped in one "Advanced" area.
- A12. Marketing after completion; a polished first launch is a should-have.
- A13. Desktop first (1280–1920 px), works at phone width, light and dark.
- A14. Testing by AI agents and automated checks; before release the maintainer personally tries 5
  everyday tasks for about 20 minutes.
- A15. Typical user has 50–200 skills; must still work well at 1,000.
- A16. Before changing another agent's files: preview, then Undo.
- A17. Detect files changed on disk and offer Refresh.
- A18. Nothing leaves the computer without a preview of what is sent and where.
- A19. English only.
- A20. WCAG 2.2 AA.
- A21. Skills come from the user, agents, and installs; files on disk are the truth.

## Open questions

- None blocking. Optional: websites whose look the maintainer dislikes.

## Decision log

| Decision | Options considered | Chosen | Why |
|---|---|---|---|
| What to fix first | Looks first; trust and clarity first; both together | Trust and clarity, then looks | The full test showed wrong statuses and silent overwrites hurt more than a plain look |
| Evidence source | AI walkthrough; maintainer's 20-min test; both; opinion only | AI agents with real QA tools now, maintainer's short test before release | No human had tested by hand; the agents give concrete evidence at no cost to the maintainer |
| Who to design for | Maintainer; new GitHub developer; both | Both | Maintainer is user #1; marketing later brings new developers |
| Success measure | Daily use over CLI; under-2-minute task; public polish | Under-2-minute task + no wrong status, then polish | Measurable and covers both user types |
| Scope order | Every page; everyday jobs first; bugs only | Bugs → everyday jobs → all pages | Lowest risk first; each step useful alone |
| Constraints | Keep all; keep tech, open look; all open | Keep tech rules, open look | Tech rules protect the project; the look is what needs work |
| Personality | Calm/clear/trustworthy; fast/techy; friendly/playful | Calm, clear, trustworthy | People must feel safe before a tool changes their agents' setup |
| Technical words | Plain by default + details; keep technical | Plain by default + details | Works for beginners and experts |
| Advanced tools | Group in "Advanced"; remove some; keep as is | Group in one "Advanced" area | Nothing lost, everyday pages lighter |
| First launch | Auto-found agents + hint; guided tour; empty page | Auto-found agents + one hint | Shows value in 10 seconds with no setup |
| Changes to other agents' files | Preview + Undo; Undo only; confirm every time | Preview, then Undo | Removes silent overwrites without nagging |
| Files changed on disk | Detect and offer Refresh; manual only | Detect and offer Refresh | Otherwise the screen shows old, untrue information |
| Data sent to AI | Always preview; as now | Always preview | Skills can hold private text |
| Language | English only; plan for more | English only | Simpler; revisit after marketing |
| Accessibility | WCAG 2.2 AA; best effort | WCAG 2.2 AA | Automated scan already passes; low cost to keep |
| Where requirements live | Project root file; chat only | `requirements.md` in project root | Lets phase 2 and later sessions resume automatically |

---

# Feature: Agent tracking (added 2026-11-26)

Phase 1 output for one feature added after the main redesign was approved (2026-11-25). It
came from the maintainer during the handoff ("we need a page like which agents you need to track
and all other features you want, and in future users can update or add agents"). Everything above
still holds; this section adds to it. Assumptions here are numbered B1… to keep them apart from
A1–A21.

## Summary

A place where people choose which coding agents, project folders and tool groups Skills Manager
shows, and add agents the app doesn't know yet. Today the agent list is fixed in code (Claude
Code, Codex, Cursor, OpenCode, Gemini, Command Code, the shared `~/.agents` folder, plus the
manager's own store), and project folders come only from the folder the app was started in. Users
can't hide an agent they don't use or add a new one.

## Problem framing

### Problem statement

Developers who use some, but not all, of the AI coding agents Skills Manager knows need a way to
choose which agents, project folders and tools the app shows, and to add agents it doesn't know
yet. Today the app shows every agent it can find the same way, with no say. So the table, counts
and choices fill with agents the user never uses, and a new agent can't be added at all.

### Primary user snapshot

- **Who:** the same developer as above (2–4 agents, 50–200 skills), who has usually installed more
  agents than they actively use.
- **Context:** an occasional, deliberate visit, not mid-coding: on day one, after installing a new
  agent, or when the table feels too wide.
- **Jobs:** stop tracking an agent; start tracking one the app found; add an agent the app doesn't
  know (a name and a folder); keep a list of project folders; switch off tool groups they never
  use.
- **Worries:** that "stop tracking" deletes something; losing sight of skills that exist only in
  that agent; pointing the app at a wrong or risky folder.

### Key scenarios

1. **"I don't use Cursor."** The user stops tracking Cursor. The app says 12 skills live only there
   and will leave the table, and that nothing on disk changes. They confirm. The column, its counts
   and its Save-to row disappear, with Undo.
2. **"A new agent came out."** The user adds "Kilo" with its folder `~/.kilo/skills`. Live checks
   confirm the folder exists and isn't already tracked. A new column appears with a neutral mark.
3. **"I work in three repos."** The user adds three project folders. The table shows one at a time
   and switches between them.
4. **"I never use AI tools."** The user switches off AI assist. It disappears from Advanced, search
   and Settings, and its connection settings are kept for later.
5. **"I installed Gemini last week."** The user has chosen their agents before, so one quiet notice
   asks: "Found Gemini. Track it?"

### How might we

1. How might we let people narrow the app to the agents they use, without fear of losing anything?
2. How might we make adding an unknown agent feel as safe as choosing a known one?
3. How might we handle many project folders without widening the table?
4. How might we keep this a quiet, occasional place that never gets in the way of everyday jobs?

## Goals and success metrics

1. A user can stop tracking an agent, or add a custom one, in **under a minute without docs**.
2. **An untracked agent never appears anywhere:** not in the table, counts, Needs attention, Save
   to, Add it to or search.
3. Stopping tracking or removing a project **never changes a file on disk**.

## Core jobs (ranked)

1. Stop or start tracking an agent the app knows.
2. Add a custom agent: a name and a folder.
3. Keep a list of project folders and switch between them.
4. Switch Advanced tool groups on or off.
5. Adjust per-agent settings: its folder(s), whether project folders count for it, its name and
   mark.

## Scope

### Must have

- People choose **agents**, in plain words; the app works out which folders that means. Folders
  appear under Details. The Shared folder appears while any tracked agent reads it.
- **Not tracked = ignored completely:** no column, no counts, no problems in Needs attention, never
  offered in Save to or Add it to, never read for display and never written to. Files on disk stay
  as they are.
- Before stopping tracking, say what leaves the view ("12 skills only in Cursor will leave the
  table. Nothing on disk changes."), then offer Undo.
- **Known list plus custom agents:** pick from the agents the app knows, or add "Other agent" with a
  name and a folder.
- **Project folders:** a list of several; the table shows one at a time.
- **Feature groups:** each Advanced group (Add skills, Check my setup, AI assist) can be switched
  off. Off hides it from Advanced, search and Settings; its saved settings are kept. Everyday pages
  (Skills, Needs attention, Trash & backups) always stay.
- **Folder rules:** custom agents and projects may point only inside the user's home folder,
  checked live in plain words (missing, not readable, already tracked by another agent).
- The choice is made **any time**, never as a setup step: first launch tracks every agent it finds
  (A6 unchanged).
- **New agents found later:** if the user never changed the list, they are tracked automatically;
  once the user has chosen, one quiet notice asks "Found Gemini. Track it?".

### Should have

- Marks for the known agents that don't have one yet (Cursor, Gemini, Command Code).

### Won't have (this version)

- CLI changes: the tracked list affects the web UI only; `--scope` keeps working.
- New known agents beyond today's 7 (Cline, Kiro, Amp and others need their folders researched
  first).
- Uploaded logos for custom agents.
- Removing settings when a feature group is switched off.
- Switching off everyday pages or single tools (the ~20 tools are switched by group only).

## Content and data

- One settings file in the data folder (`<data>/skills-manager/`) holds the tracked agents, custom
  agents, project folders and feature groups. People can read and edit it by hand.
- The skill folders stay the source of truth; the settings file only says which of them to show.
- Folder paths are the only sensitive data here, and they never leave the computer.

## Constraints

- All locked rules in `AGENTS.md` apply. Saving these choices needs a **new settings file and new
  backend calls**. The maintainer approved this **in principle** on 2026-11-26. The design brief
  will list the exact new setting and calls, and the maintainer signs those off before the build.
- The look follows the approved design system (v11).

## Lifecycle

- **Day one:** every agent found is tracked; no extra step.
- **Day 100:** occasional visits to untrack, add a custom agent or a project, or after a notice
  about a newly found agent.
- **Undo** after every change on this page.

## Edge cases and states

- Stopping tracking an agent whose skills exist only there (say what leaves the view, then Undo).
- The last tracked agent (at least one stays tracked; with none, the table shows "no agents" with a
  way back).
- A custom folder that is missing, not readable, outside the home folder, or already tracked.
- A custom agent whose folder disappears later (status says so; never shown as working).
- Two custom agents with the same name.
- A project folder that is moved or deleted.
- A broken or hand-edited settings file (fall back to "track everything found" and say so).
- A feature group switched off while one of its tools is open.
- A newly found agent, before and after the user has made a choice.
- Phone width, light and dark, keyboard only.

## Assumptions (signed off)

All signed off by the maintainer on 2026-11-26 ("All okay").

- B1. The CLI is unchanged in this version; the tracked list affects the web UI only.
- B2. The manager's own store ("Global") isn't a user-facing agent and isn't on this list.
- B3. At least one agent stays tracked; with none, the table shows its "no agents" empty state.
- B4. A custom agent gets a neutral icon; no uploaded logos.
- B5. This work includes marks for Cursor, Gemini and Command Code.
- B6. Choices live in one hand-readable settings file in the data folder; if it is broken, the app
  tracks everything found and says so.
- B7. Works at phone width (390px), in light and dark, to WCAG 2.2 AA.
- B8. Success: untrack or add a custom agent in under a minute without docs; an untracked agent
  never appears anywhere.
- B9. Removing a project folder from the list never touches its files.
- B10. Every feature group starts switched on.
- B11. The known list is today's 7 agents; adding more known agents is a separate change.

## Open questions

- None blocking. The exact new setting and backend calls are listed in the design brief for the
  maintainer's sign-off before the build.

## Decision log

| Decision | Options considered | Chosen | Why |
|---|---|---|---|
| What "not tracked" means | Ignored completely; hidden column only; show/hide/ignore | Ignored completely | Simplest to understand and calmest; files untouched |
| What users can add | Known list + custom; known only; any folder | Known list + custom agents | New coding agents appear often |
| "All other features you want" | Per-agent settings; feature on/off; just agents | Per-agent settings and feature on/off | Maintainer's choice of both |
| When the choice is made | Any time; confirm at first launch; required setup | Any time; first launch tracks all found | Keeps A6: value in 10 seconds, no setup |
| What the user picks | Agents; folders | Agents (app works out the folders) | Plain words first; folders under Details |
| Project folders | A list, one at a time; columns; as today | A list, shown one at a time | Scales without widening the table |
| What can be switched off | Advanced groups; each tool; everything | Advanced groups | Everyday pages always stay; short list |
| Backend changes | Approve in principle; decide later; browser only | Approve in principle; exact list signed off before build | Design stays buildable; files on disk stay the truth |
| Untracking with unique skills | Say what disappears + Undo; block; no warning | Say what disappears, then Undo | "Show before you change, Undo after" |
| Newly found agents | Depends on history; always ask; always add | Auto-track until the user has chosen, then ask once | Day one stays automatic; a curated list isn't overridden |
| Allowed folders | Inside home, checked live; any folder | Inside home, checked live | The app touches only the user's folders |
| Feature group off | Hidden, settings kept; settings removed | Hidden, settings kept | Turning it back on restores everything |
