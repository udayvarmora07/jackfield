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
