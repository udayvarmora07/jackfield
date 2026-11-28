# Skills Manager UI — UX brief

Phase 2 output of the `/uxui-workflow`. Written 2026-11-24. Input: `requirements.md`.
Structure, flow and content only — no visuals. "A1…A21" refer to the signed-off assumptions in
`requirements.md`.

## Problem (from requirements)

Developers who use several AI coding agents need one place to see, fix and keep their skills in
step across all those agents, because their skills are scattered in hidden folders and quietly
drift apart, and the current UI sometimes shows a wrong or confusing status, so they don't trust
it enough to change files. Primary user: a developer with 2–4 agents and 50–200 skills, mid-coding,
arriving with a specific question.

Benchmark task used to compare concepts (the success metric, A7): **find the skill `code-review`
and turn it off for Codex only.**

## Solution concepts (Develop)

### Concept 1 · "Just ask" — search-first (rejected)

- **Idea:** the app is one big search box; type what you want, land on the answer.
- **Mental model:** "I have a question about a skill, so I type it" (Raycast, Linear Ctrl+K).
- **Journey:** open → cursor in search, recent skills below → type "code rev" → Enter → skill page
  with one row per agent and a switch → switch off Codex → note with Undo (~10 s).
- **Optimizes for:** speed for people who know what they want; "Why didn't it run?"; fewer pages.
- **Sacrifices:** overview; beginners don't know what to type; drift stays hidden until searched.
- **Risks:** weak first 10 seconds (empty box); cleanup of 150 skills is hard by search alone.
- **Why it lost:** fails time-to-value and the cleanup scenario. Its best part — a global search —
  is kept in the hybrid.

### Concept 2 · "One table of truth" — grid-first (chosen as the core)

- **Idea:** the main screen is one table: skills are rows, agents are columns, every square tells
  the truth in plain words.
- **Mental model:** "My setup is a grid; each square answers: does this agent have this skill, is
  it on, is it the same copy?" (Notion databases, Linear lists).
- **Journey:** open → table of all skills × agents → type "code" in the filter → find
  `code-review` → click the Codex square → side panel "code-review in Codex: On. Turn it off?" →
  Turn off → square shows Off, Undo offered (~15 s).
- **Optimizes for:** overview, drift visible, copy to another agent (click an empty square),
  cleanup, first-launch value, uniqueness.
- **Sacrifices:** reading/editing depth (separate skill page); phone needs a narrow layout; needs
  good filters at 200+ rows.
- **Risks:** can feel dense; each square must stay one word plus an icon.

### Concept 3 · "Health check" — to-do-first (rejected)

- **Idea:** the app checks the setup and lists what needs attention; the Inbox is the front door.
- **Mental model:** "The app is my assistant and tells me what's wrong" (car dashboard light).
- **Journey:** open → "All good" or "3 things need you" → go to Library → search → open skill →
  switch off Codex → back (~20 s).
- **Optimizes for:** trust, first-launch summary, cleanup, peace of mind.
- **Sacrifices:** speed of everyday jobs (one level deeper).
- **Risks:** nagging (breaks "calm"); any wrong check destroys trust in the whole app.
- **Why it lost:** slowest for the everyday jobs and the success task. Its best part — one quiet
  attention count with a one-at-a-time fixer — is kept in the hybrid.

### Comparison

| Criterion (from requirements) | 1 · Just ask | 2 · Table of truth | 3 · Health check |
|---|---|---|---|
| Value in the first 10 seconds | ⚠️ empty search box | ✅ whole setup appears | ✅ summary |
| Speed of the success task | ✅ fastest | ✅ fast | ⚠️ slowest |
| Find and read | ✅ | ✅ | ⚠️ deeper |
| Turn on/off per agent | ✅ | ✅ | ⚠️ deeper |
| Copy or sync between agents | ⚠️ skill page only | ✅ empty square | ⚠️ only when flagged |
| Create or edit | ✅ | ✅ | ⚠️ |
| "Status never wrong" visible | ⚠️ per skill | ✅ all at once | ✅ but fragile |
| Quick visits mid-coding | ✅ | ✅ | ⚠️ |
| Phone width | ✅ | ⚠️ needs narrow version | ✅ |
| 200–1,000 skills | ✅ | ✅ with filters | ✅ |
| Calm, not nagging | ✅ | ✅ | ⚠️ |
| Build effort given existing code | Medium | Lowest | Medium |
| Day 1 vs. day 100 | Weak / great | Great / great | Great / tiring |
| Differentiation | Common | Unique | Common |

### Decision

The maintainer chose the **hybrid**: Concept 2 as the heart, plus Concept 1's global search
(`/` and Ctrl+K) and Concept 3's single quiet "Needs attention" count with a one-at-a-time fixer.
Home, Skills and Sync map merge into one Skills table; Inbox becomes Needs attention; Recovery
becomes Trash & backups; Tools becomes Advanced.

## User journey map

| Stage | User goal | Actions | Thoughts and feelings | Pain points today | Opportunities |
|---|---|---|---|---|---|
| 1. Discover | "Is this worth trying?" | Read the GitHub page | Curious, busy | Hard to picture the product | One clear screenshot of the table |
| 2. First launch | "Does it see my stuff?" | Install, open | "Please just work" | Six pages and jargon at once | Agents and skills found automatically, one hint (A6) |
| 3. First useful action | Answer one real question | Search, read, switch off | "Handy" or "is that true?" | Wrong statuses break trust | Every square true or "unknown" (A7) |
| 4. Regular use | Quick answers mid-coding | Ctrl+K, act, leave | Wants it done in under a minute | Five search boxes, many pages | One search, one main screen |
| 5. Habit and upkeep | Keep the setup clean | Fix attention items, clean up, back up, Advanced | Calm, in control | Tool overload | Quiet attention count; tools grouped in Advanced (A11) |

## User flows

### F1 · Find and read a skill (job 1)
1. Press `/` or Ctrl+K anywhere, or type in the table filter.
2. Type part of a name or description.
3. Results show name, one-line description, which agents have it.
4. Enter opens the skill page with the readable document.
- Alternative: scan the table and click the skill name.
- No results: "No skills match 'revew'" with Clear filters and close-name suggestions.
- Can't read the file: the page still opens, explains the problem plainly, offers the fix.

### F2 · Turn a skill on or off for one agent (job 2, success test)
1. In the table, click the agent's square ("On").
2. Side panel: "code-review in Codex is On."
3. Turn off → square shows "Off" → note with Undo.
- Agent settings already turn it off: the square says "Off in Codex settings", never green "On";
  the panel explains where that setting lives, that the app does not change agent settings files,
  and offers to open the settings file (A1, A7).
- Can't change the file: the panel says why and what to do; the screen changes only after the
  change really happened.

### F3 · Copy or sync between agents (job 3)
- Add where missing: click the empty square → "Add code-review to OpenCode? Copied from Claude
  Code (12 lines, 1 extra file)" → Add → Undo (A16).
- Copies differ: square says "Different" → panel shows both versions with changes marked → choose
  which copy wins → "Make Codex match" → preview of what will be replaced → confirm → Undo.
- Evenly split (2 vs 2): the app doesn't guess; the user picks the source; nothing preselected.
- Several at once: tick rows → "Make these match in Codex" → preview the list → confirm → one Undo.
- Target occupied or failure: the message names the skill and agent; nothing is half-done.

### F4 · Create a skill (job 4)
1. New skill (button or Ctrl+K).
2. Name with live rules in plain words ("use lowercase and dashes, like code-review").
3. Description (multi-line); optional template.
4. Choose agents (several allowed).
5. Create → skill page opens; the row appears in the table.
- Name exists: "code-review already exists in Claude Code and Codex. Open it?"
- Cancel with typed text: "Discard this new skill?"

### F5 · Edit a skill (job 4)
1. Edit on the skill page; the address becomes `…/edit` so reload keeps the editor.
2. Change text; "Unsaved changes" shown.
3. "Save to" lists every agent. An agent with a different copy is unticked by default and marked
   "Codex has a different version; saving here replaces it (preview)".
4. Save → Undo.
- Leaving with unsaved changes: "Discard your changes?"
- File changed on disk while editing: "This skill was changed outside the app. Compare before saving?" (A17)

### F6 · "Why isn't it running?" (scenario 1)
1. On the skill page, "Why isn't it running?"
2. Per-agent checklist in plain words: file found; file readable; switched on; agent settings
   allow it; agent actually loads it — **unknown, the app can't see inside the agent**.
3. Each failed check has one clear next step.

### F7 · Fix "Needs attention" items (scenarios 2, 3)
1. Header count "Needs attention · 3" → filters the table to problem rows or opens the fixer.
2. Each item: what's wrong, which agent, the suggested fix, a preview.
3. Fix / Skip / Open skill → Undo after each fix.
- Not fixable in the app (unreadable bytes): says so honestly, shows what to do by hand.
- Empty: "Everything checks out", with what was checked and when.

### F8 · Files changed on disk (A17)
1. Quiet banner: "Skills changed on disk (2). Refresh."
2. Refresh → changed rows briefly highlighted.
- In the editor: see F5.

### F9 · First launch (scenario 5, A6)
1. Open → "Looking for your agents…"
2. "Found 3 agents and 142 skills" with the table filled.
3. One hint: "Click any square to turn a skill on or off for that agent."
- No agents found: where it looked, in plain words, and how to add a folder.

## Information architecture

**Global (every screen)**
- Top bar: Skills Manager · **Skills** · **Needs attention (n)** · **Trash & backups** · **Advanced**.
- Right: one search (`/`, Ctrl+K) for skills, actions and pages; theme; help.
- Global banner when files change on disk.
- One Undo area for the latest change; messages close themselves and never follow the user to
  another page.

**Contextual**
- Table side panel: acts on one square.
- Skill page: read, edit, "Why isn't it running?", more actions (trash, delete forever).

**Merged or renamed from today**
- Home + Sync map → Skills table. Inbox → Needs attention. Recovery → Trash & backups (one trash
  list). Tools → Advanced.

**Advanced, grouped by goal**
- Add skills: Install, Templates, Profiles.
- Check my setup: Quality, Where agents look (today's Workspaces), Doctor.
- AI assist: Connection; tools grouped as Write, Test, Shorten, Find conflicts.
- Settings.

**Phone**
- Bottom tab bar with the same four items. The table shows one agent at a time ("Showing:
  Codex ▾"); each row shows that agent's status; tapping a row opens the skill page.

## Screen inventory (journey order)

| # | Screen | Job | Primary action | Content priority | States | Obvious at a glance | Type |
|---|---|---|---|---|---|---|---|
| S1 | Skills table | All 4 jobs, overview | Click a square to act | Attention count (only if >0); search, "Only problems", agent focus; rows: name, one-line description, one plain word per agent square (On / Off / Different / Can't read / –); total | First launch (scanning → summary + hint); loading placeholders; no agents; no skills; no results (Clear filters); files changed banner; 1,000 rows; phone one-agent view | Which agents have which skill, on or off, same or broken | Key · **Hero** |
| S2 | Square side panel | On/off, copy, make match | Per state: Turn off / Turn on / Add here / Make match / Fix | One-sentence status; what will change (preview); action; folded details | On; Off; Off in agent settings; Missing; Different; Evenly split; Can't read; Unknown; working; failed; done + Undo | What will happen before clicking | Key |
| S3 | Skill page | Find and read | Edit | Name, description; agent row (same statuses); document; details (files, size, history) | Copies differ (choose which to read); can't read; switched off; not found; loading | Working everywhere? What does it say? | Key |
| S4 | Editor | Edit | Save | Description; content (Write/Preview); "Save to" with different-copy warnings | Unsaved; invalid (why); saving; saved + Undo; changed on disk; phone sticky Save | Where it saves and what it replaces | Key |
| S5 | New skill | Create | Create | Name (live rules); description (multi-line); agents (several); template | Invalid (why); exists (Open it?); creating; created | Where it will be created | Key |
| S6 | Why isn't it running? | Read, trust | Follow the next step | Per agent: found / readable / on / settings allow / loaded (unknown) | All good; failures; unknown parts | Which check fails and what to do | Supporting |
| S7 | Needs attention | Fix problems | Fix (with preview) | Count to go; current item (what, agent, fix, preview); remaining list | Empty (what was checked); not fixable in app; skipped; fixed + Undo | What's wrong and that fixing is safe | Key |
| S8 | Trash & backups | Recover | Restore | One trash list (with origin); recent undoable changes; backup download/load | Empty; restore blocked (replace or keep both?); bad backup (one message); load results with reasons | Nothing is lost; how to get it back | Supporting |
| S9 | Advanced | Less frequent tools | Open a tool | Groups by goal, one sentence each | Search no match | Where each tool lives | Supporting |
| S10 | Advanced tool page (one template, ~20 tools) | Quality, install, AI… | One per tool | What it does; what it reads/sends (AI: preview + cost); inputs; plain result; folded raw details | Not set up (what's missing + link); running; error next to its button; no findings (what was checked) | What it will do; what the result means | Supporting |
| S11 | Settings | Comfort, maintenance | — (saves immediately) | Theme, text size, region, AI connection, maintenance | Saved; failed; AI not connected / connected / failed (never "Connected" on failure) | Current state is true | Supporting |
| S12 | Search / command palette | Speed | Go to result | Skills, then actions, then pages | No match (filter or New skill) | Where Enter goes | Supporting |
| S13 | Not found | Recovery from bad links | Go to Skills | "This page doesn't exist" / "Skill not found" (link to Trash) | — | Lost, and how to get back | Supporting |

## Hero screen

**S1 · Skills table with its side panel (S2).** It carries the success task, the first 10
seconds of value, and the "status is never wrong" promise; it is the unique part of the product
(all agents side by side). Its statuses, density and calm set the design language for every other
screen.

## UX principles

1. **Tell the truth, or say "unknown".** No green unless checked; every status names its agent.
2. **Show before you change, offer Undo after.** Never touch another agent's files silently.
3. **One place for each thing.** One search, one problem list, one trash, one name per idea.
4. **Plain words first, details on request.** Raw paths, numbers and codes live under "Details".
5. **Calm by default.** Problems are counted in one place and shown where they matter.

**Voice and tone:** short, plain, specific. Always say what happened, to which skill, in which
agent, and what to do next.
- "Codex has a different copy of code-review." — not "Document differs from the reference in scope codex."
- "Couldn't reach your AI service. Check the address in AI settings." — not "[Errno 111] Connection refused".
- "Uses about 3% of Claude's skill list space." — not "~9,373 characters of ~40,000 listing budget".

## Traceability

| Requirement | Served by |
|---|---|
| Status never wrong (A7, must-have) | S1, S2, S6, S11; principle 1 |
| Preview then Undo (A16) | S2, S4, S7; F3, F5 |
| Plain words, details on request (A4) | Voice rules; S2/S10 folded details |
| Four everyday jobs (A9) | F1–F5; S1–S5 |
| 50–200 skills, works at 1,000 (A15) | S1 states (filters, paging) |
| Nothing leaves without preview (A18) | S10 (AI tools) |
| Files changed on disk (A17) | F8; global banner; S4 |
| First launch (A6) | F9; S1 first-launch state |
| Advanced tools grouped (A11) | S9, S10 |
| Desktop first, phone works, light/dark, WCAG 2.2 AA (A13, A20) | IA phone model; phase 3 |
| Bugs first (A10) | Every High finding in `requirements.md` maps to a state above (wrong status → S1/S2/S11; silent overwrite → S4; off-screen errors → S10; template edit/delete → S10; broken install → S10) |

**Flags**
- Profiles and Templates are kept in Advanced (A11) but no scenario uses them; not designed in detail.
- "Too many skills" cleanup (scenario 3) is served by table sorting and agent filters only. A
  dedicated clean-up helper would be a new feature and must be added to `requirements.md` first.

## Approval

Concept (hybrid), flows and screen inventory approved by the maintainer on 2026-11-24.
