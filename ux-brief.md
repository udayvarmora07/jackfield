# Jackfield UI — UX brief

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
- Top bar: Jackfield · **Skills** · **Needs attention (n)** · **Trash & backups** · **Advanced**.
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

---

# Feature: Agent tracking (added 2026-11-26)

Phase 2 output for the feature section of the same name in `requirements.md`. Written 2026-11-26.
Everything above still holds; this adds to it. "B1…B11" are that section's signed-off
assumptions. Screens continue the numbering above (S14 onward). Structure, flow and content
only, no visuals. **Status: concept, flows, screen inventory and backend contract approved by
the maintainer on 2026-11-26 ("Approve all").**

## Problem (from requirements)

Developers who use some, but not all, of the AI coding agents Jackfield knows need to choose
which agents, project folders and tool groups the app shows, and to add agents it doesn't know
yet. Today every agent found is shown with no say, and a new agent can't be added. Primary user:
the same developer (2–4 agents, 50–200 skills) with more agents installed than they use, on an
occasional, deliberate visit. Worry: that "stop tracking" deletes something.

Benchmark tasks (B8): **stop tracking Cursor** and **add the custom agent "Kilo" at
`~/.kilo/skills`**, each in under a minute without docs.

## Solution concepts (Develop)

### Concept 1 · "Shape it where you see it": manage it from the table (partly kept)

- **Idea:** no new page. Each agent column header gets a menu (Stop tracking, Details, Rename);
  a "+" column adds an agent; the project picker adds folders; each Advanced group header gets a
  switch.
- **Mental model:** "The table is my setup; I change its columns right there."
- **Journey:** Cursor header ▾ → Stop tracking → "12 skills only in Cursor will leave the table.
  Nothing on disk changes." → confirm → column gone, Undo (~10 s).
- **Optimizes for:** speed; nothing new to find. **Sacrifices:** no overview of untracked agents
  (they're invisible, so getting one back hides behind "+"); rare, consequential actions sit next
  to everyday squares; tool groups live elsewhere; header menus are awkward on phone.
- **Why it lost as the whole answer:** fails "one place for each thing" and makes untracked agents
  hard to find again. **Kept:** its entry points, as shortcuts to the page.

### Concept 2 · "Agents hub": a new top-level destination (rejected)

- **Idea:** a new "Agents" top-bar item, like an integrations gallery: a card per known agent, an
  "Add other agent" card, each card opening its own agent page; Projects and Tool groups as tabs.
- **Mental model:** "Agents are integrations I connect and configure."
- **Journey:** Agents → Cursor card → Cursor page → Stop tracking → confirm → back, Undo (~20 s).
- **Optimizes for:** per-agent depth (job 5), room to grow. **Sacrifices:** calm (a fifth
  top-level item for an occasional visit; the phone tab bar holds four); most screens to build;
  the top job one level deeper.
- **Why it lost:** "integrations" implies the app installs or connects agents, which it doesn't,
  and invites won't-haves such as uploaded logos. Folded Details covers job 5 more cheaply.

### Concept 3 · "One 'What to track' page": one settings list (chosen as the core)

- **Idea:** one page under Settings with three short sections of checkbox rows (the same pattern
  as "Save to" and "Add it to"): Agents, Project folders, Tool groups. Agent rows fold open for
  Details. Changes save as they're made, with Undo; stopping tracking asks first.
- **Mental model:** "A list of what the app watches. I tick what I use."
- **Journey:** Advanced → Settings → What to track → untick Cursor → confirm → row says "Not
  tracked", Undo (~20 s). Add Kilo: Add other agent → name + folder, checked live → Add (~40 s).
- **Optimizes for:** one place for everything (including untracked agents), calm, familiar
  pattern, phone, lowest build. **Sacrifices:** discoverability from the table.

### Comparison

| Criterion (from requirements) | 1 · Table | 2 · Hub | 3 · One page |
|---|---|---|---|
| Stop tracking < 1 min, no docs | ✅ fastest | ✅ | ✅ |
| Add custom agent < 1 min | ⚠️ cramped in a menu | ✅ | ✅ |
| Untracked agents findable again | ❌ hidden | ✅ | ✅ |
| Project folder list | ⚠️ toolbar only | ✅ tab | ✅ section |
| Tool groups (job 4) | ⚠️ elsewhere | ✅ tab | ✅ section |
| Per-agent settings (job 5) | ⚠️ menu | ✅ deepest | ✅ folded Details |
| Calm, occasional, out of the way | ⚠️ busy headers | ❌ new top-level item | ✅ |
| "One place for each thing" | ❌ scattered | ✅ | ✅ |
| Safe against accidental untrack | ⚠️ | ✅ | ✅ |
| Phone width | ⚠️ | ⚠️ another tab | ✅ a list |
| Build effort | Medium | Highest | Lowest |
| Day 1 vs. day 100 | Good / good | Good / heavy | Quiet / good |
| Discoverable | ✅ | ✅ | ⚠️ |

### Decision

The maintainer chose the **hybrid (3 + 1)** on 2026-11-26: Concept 3's page is the single home
for every choice; Concept 1's entry points on the table (column header menu, project picker,
"Found Gemini" notice, "no agents" empty state, Ctrl+K) are shortcuts that run the same actions or
lead to the page. They never add a second place where choices live.

## User journey map (feature)

| Stage | User goal | Actions | Thoughts and feelings | Pain points today | Opportunities |
|---|---|---|---|---|---|
| 1. Day one | "Does it see my stuff?" | Open the app | "Please just work" | — | Every agent found is tracked; no setup step (A6, B10) |
| 2. Noticing | "Why is Cursor here? I never use it." | Scan a wide table | Mild clutter, slight suspicion | No say at all | Column header menu offers "Stop tracking Cursor…" right where the annoyance is |
| 3. Choosing | Narrow to what I use | Untick, read what leaves, confirm | "Will this delete anything?" | — | Every confirm says "Nothing on disk changes"; Undo after |
| 4. Extending | Add a new agent or a repo | Add other agent / Add project folder | "Did I get the path right?" | Impossible today | Live plain-word checks and a preview ("9 skills found") before Add |
| 5. Living with it | Keep it right as tools change | React to "Found Gemini. Track it?", switch projects, switch tool groups | Calm, in control | — | One quiet notice at most; project picker in the toolbar |

## User flows

### T1 · Stop tracking an agent (job 1, benchmark)
1. On What to track, untick Cursor. (Or: Skills table → Cursor column header ▾ → "Stop tracking
   Cursor…".)
2. Confirm states what leaves: "The Cursor column and its counts leave the table. **12 skills
   live only in Cursor** and will no longer show. Nothing on disk changes." "See the 12 skills"
   folds open the names.
3. "Stop tracking Cursor" → saved → row says "Not tracked"; message "Stopped tracking Cursor.
   Nothing on disk changed." with Undo.
- No skills only there: same confirm, "Every skill in Cursor also lives in another agent."
- Count unknown (folder unreadable): "Cursor's folder can't be read, so we can't count its
  skills." Confirm still allowed.
- Last tracked agent: checkbox disabled, reason beside it: "At least one agent stays tracked."
  (B3). The column header menu shows the item disabled with the same reason.
- Save fails or settings changed in another window: the row returns to Tracked, the message says
  why next to the row ("These settings changed in another window. Reload to see them.").
- Undo: tracks it again; the column returns.

### T2 · Start tracking a known agent (job 1)
1. On What to track, tick an untracked agent ("Gemini · Found · 14 skills · Not tracked").
2. Saved at once (adding never hides anything) → column appears; message with Undo.
- Not found on this computer: row says "Not found: nothing to show yet". Ticking is allowed; it
  appears in the table once its folder exists, and is never shown as working before that.

### T3 · Add a custom agent (job 2, benchmark)
1. What to track → "Add other agent".
2. Name ("Kilo"): live rule, 1–40 characters, not already used by another agent (any case).
3. Folder (`~/.kilo/skills`): checked live in plain words. Missing ("This folder doesn't exist.
   Check the path, or create it first."); not a folder; not readable; outside the home folder
   ("Pick a folder inside your home folder."); already tracked ("That's Claude Code's folder.
   It's already tracked."). Links that resolve outside home count as outside.
4. Optional: "Folder inside projects" (`.kilo/skills`), so project folders count for it.
5. Preview line: "Kilo · 9 skills found in ~/.kilo/skills".
6. Add → row appears ticked with a neutral mark (B4); new column at the end of the table;
   message with Undo (Undo removes the entry; the folder is untouched).
- Cancel with typed text: "Discard this agent?"

### T4 · Change an agent's settings (job 5)
1. On What to track, open an agent row's Details.
2. Known agent: the folders the app reads, in plain words with paths under Details; what else it
   reads ("Also reads Claude Code's folder", marked Not tracked if so); switch "Count project
   folders for Cursor". Name and mark are fixed.
3. Custom agent: Edit (same dialog as T3, prefilled, same live checks) and Remove (same confirm
   pattern as T1, worded "Remove Kilo").
- Custom agent's folder disappears later: row status "Folder missing: not shown in the table";
  never shown as working. Edit offers a new path.

### T5 · Project folders (job 3)
1. What to track → Project folders → "Add project folder" → path with live checks (inside home,
   exists, readable, not already listed) → preview "Found .claude/skills and .agents/skills · 6
   skills" or "No skill folders here yet" (allowed) → Add; "Show it in the table now" ticked.
2. Switch in the Skills table toolbar: "Project: api ▾" lists the folders (current one ticked,
   "None" at the top), plus "Add project folder…" and "Manage project folders".
3. Remove: immediate, with "Removed ~/work/api from the list. Its files are unchanged." and Undo
   (B9).
- Day one: the folder the app was started in is added automatically if it holds skill folders
  (today's behaviour, A6).
- Moved or deleted: row says "Folder not found"; the picker greys it out. If it was showing, the
  table says "~/work/api can't be found" with Choose another and Remove.

### T6 · Switch a tool group off (job 4)
1. What to track → Tool groups → switch off AI assist ("Write, test, shorten and check skills
   with your AI service").
2. Applied at once → gone from Advanced, search and Settings (its connection section); message
   "AI assist is off. Its settings are kept." with Undo (B10).
- A tool of that group is open (or a bookmarked link): the tool page says "AI assist is switched
  off" with one action, "Turn it on".
- All three off: Advanced shows only Settings plus one line: "Tool groups are switched off. Turn
  them on in What to track."

### T7 · A new agent is found later
1. The user has never changed the agent list → it's tracked automatically, no notice.
2. The user has chosen before → one quiet notice on the Skills page: "Found Gemini (14 skills).
   Track it?" with Track and Not now.
3. Track → column appears, Undo. Not now → never asked again for Gemini; it stays on the page as
   Not tracked.

### T8 · Broken or hand-edited settings file (B6)
1. The app tracks every agent found and shows all tool groups.
2. Skills page notice (once) and a banner on What to track: "Your tracking settings couldn't be
   read, so everything found is shown." Details gives the file path and the reason.
3. Actions: Reset to everything found. The broken file is kept as a copy beside it before the
   first new save, so hand edits are never lost.

### T9 · No agents tracked (B3)
- Reachable only by hand-editing the file, or when every tracked folder disappears. The table
  shows its "no agents" empty state: "No agents are tracked." with "Choose agents" leading to
  What to track.

## Information architecture (feature)

- **Home:** What to track (S14), its own address `/settings/tracking`, under Advanced → Settings.
  The Settings page gets a first row "What to track · 4 agents, 2 project folders, 3 tool
  groups" leading to it. It belongs to no tool group, so it can never be switched off.
- **Doorways (shortcuts, never a second home):**
  - Skills table column header menu: "Stop tracking Cursor…" (runs T1's confirm), "Cursor details"
    and "Manage agents" (both open S14, Details opened for Cursor).
  - Project picker in the table toolbar (S19): switch, "Add project folder…", "Manage project
    folders".
  - "Found Gemini. Track it?" notice; the "no agents" empty state; Ctrl+K ("track", "agents",
    "project folder", "tool groups").
  - Phone: the "Showing: Codex ▾" picker gets "Manage agents" at the bottom.
- **Everywhere else, untracked means absent:** Skills table, counts, Needs attention, Save to (S4),
  Add it to (S5), search (S12), Trash origin filter, Advanced tools that list agents. Switched-off
  groups are absent from Advanced (S9), search and Settings (S11).

## Screen inventory (feature, journey order)

| # | Screen | Job | Primary action | Content priority | States | Obvious at a glance | Type |
|---|---|---|---|---|---|---|---|
| S14 | **What to track** | All 5 | Tick or untick an agent | Summary ("Tracking 4 of 6 agents · 2 project folders"); **Agents**: rows (checkbox, mark, name, plain status, skill count, Details fold), Shared folder row (automatic, says which tracked agents read it), "Add other agent"; **Project folders**: rows (path, status, "Showing in the table"), Add, Remove; **Tool groups**: three switches with one sentence each | First time ("Every agent found is tracked. Untick any you don't use."); returning; loading placeholders; saving per row; save failed (row reverts, reason beside it); changed in another window; broken file banner; last agent (disabled + reason); not found; folder missing; phone single column | What's tracked, what isn't, and that unticking is safe | Key · **Hero** |
| S15 | Stop tracking / Remove confirm | 1, 2 | "Stop tracking Cursor" (or "Remove Kilo") | What leaves (column, counts, N skills only here, foldable names); "Nothing on disk changes. You can track it again any time."; Cancel | Counting; 0 only here; count unknown (unreadable); from the page or the column header | Exactly what disappears, and that files stay | Key |
| S16 | Add other agent / Edit agent | 2, 5 | Add agent (Save) | Name; folder; optional folder inside projects; live check under each field; preview line ("9 skills found") | Checking; ok; missing; not a folder; not readable; outside home; already tracked by X; name taken; saving; failed; added + Undo; discard guard | Whether the folder is right before adding | Key |
| S17 | Agent details (fold-out in an S14 row) | 5 | — (switch saves at once) | Folders read (plain, paths under Details); also reads; "Count project folders" switch; skill count; custom: Edit, Remove | Folder missing; reads an untracked agent's folder | Which folders this agent means | Supporting |
| S18 | Add project folder | 3 | Add folder | Path; live check; preview of skill folders found; "Show it in the table now" | Checking; ok; no skill folders yet (allowed); missing; outside home; already listed; failed | That it's the right repo | Supporting |
| S19 | Project picker (S1 toolbar) | 3 | Switch project | "None", folders (current ticked, missing greyed), Add project folder…, Manage project folders | Empty list (picker hidden, Ctrl+K and S14 still offer Add); showing folder missing | Which project the table shows | Supporting |
| S1+ | Skills table: changes | 1, 3 | (unchanged) | Column header menu; "Found Gemini. Track it?" notice; project picker; "No agents are tracked" empty state; untracked agents absent | Notice shown / dismissed; broken-file notice (once) | Only tracked agents appear | Key (existing) |
| S9+/S10+/S11+ | Advanced, tool page, Settings: changes | 4 | — | Off groups absent; all-off line; tool page "switched off" state with Turn it on; Settings first row to S14; AI section hidden when AI assist is off | — | What's off and where to turn it on | Supporting (existing) |

## Hero screen (feature)

**S14 · What to track with its confirm (S15).** Every core job happens here, and it carries the
feature's biggest worry ("will this delete anything?"). Its row pattern, plain statuses and the
"Nothing on disk changes" confirm set the language for the dialogs (S16, S18) and the table
shortcuts.

## UX principles (feature, added to the five above)

1. **Tracking is a view, never a change on disk.** Every confirm and message says so.
2. **Say what leaves before it leaves; Undo after.** Adding needs no confirm; hiding does.
3. **One home, many doorways.** S14 is the only place choices live; table entries are shortcuts
   to the same actions.
4. **Agents in plain words, folders under Details.** People pick "Cursor", not `~/.cursor/skills`.
5. **Quiet and occasional.** No setup step; at most one notice about a new agent, ever.

**Voice:** "Stopped tracking Cursor. Nothing on disk changed." · "12 skills live only in Cursor
and will no longer show." · "That's Claude Code's folder. It's already tracked." · "AI assist is
off. Its settings are kept." · Never "scope", "consumer", "untrack" or raw error codes in the main
text.

## Backend contract (for the maintainer's sign-off)

Approved in principle on 2026-11-26; **the exact list below, including the six decisions at its
end, was signed off by the maintainer on 2026-11-26.** It
keeps every locked rule: no new CLI command or Store method, no SQLite or `SCHEMA_VERSION` change,
no new dependency, stdlib only, filesystem stays the truth (the file only says what to show).

**New settings file:** `<data>/tracking.json` (`<data>` = the manager root, e.g.
`~/.local/share/skills-manager/`), written atomically with mode 0600, like `<data>/ai/settings.json`.
Hand-readable; paths stored home-relative (`~/…`). Missing file = "track everything found".

```json
{
  "version": 1,
  "revision": 7,
  "agents": {
    "chosen": true,
    "tracked": ["claude-code", "codex", "custom-kilo"],
    "seen": ["claude-code", "codex", "cursor", "opencode", "gemini", "commandcode"],
    "count_projects": {"cursor": false}
  },
  "custom_agents": [
    {"id": "custom-kilo", "name": "Kilo", "folder": "~/.kilo/skills", "project_folder": ".kilo/skills"}
  ],
  "projects": {"folders": ["~/work/api", "~/work/web"], "showing": "~/work/api"},
  "tool_groups": {"add-skills": true, "check-setup": true, "ai-assist": true}
}
```

- `chosen: false` until the user's first change: new agents are tracked automatically. After that,
  a found known agent in neither `tracked` nor `seen` raises the T7 notice; "Not now" adds it to
  `seen`.
- The Shared folder (`agents`) isn't in `tracked`: it's shown while any tracked agent reads it.
- `revision` guards against two windows overwriting each other.

**New backend calls (web only, B1):**

| Call | Does | Writes? |
|---|---|---|
| `GET /api/tracking` | Saved settings (or defaults) plus a live report: file state (`ok` / `default` / `broken` + reason); per agent: name, known or custom, tracked, found, folder status, skill count, skills only here (count + first 50 names), folders read, also-reads; Shared folder shown + read by; per project: status, skill folders found, count; tool groups; newly found agents | No |
| `PUT /api/tracking` | Replace the whole settings document. Body carries the `revision` it read; stale → 409 "changed in another window". Every rule re-checked server-side (home folder, exists, not already tracked, unique names, at least one tracked agent); a broken existing file is copied aside before the first save. Undo = PUT the previous document. Returns the GET payload | `tracking.json` only |
| `POST /api/tracking/check-folder` | Live folder check for S16/S18: `{path, purpose: "agent" or "project", ignore_id}` → problems in plain words (missing, not a folder, not readable, outside home, already tracked by X, already listed) and a preview (skill count, skill folders found) | No |

**Existing calls that change:** the tracked set and showing project filter everything server-side,
so an untracked agent is never read for display and never written to: `/api/scopes`, `/api/stats`,
`/api/skills`, `/api/search`, Needs attention checks, `/api/workspaces`, batch preview/execute,
and the skill read/write/toggle/sync/new routes (which reject an untracked agent with a plain
error, and accept a custom agent's id). Project scopes come from `projects.showing` instead of
only the start-up folder.

**Where it lives:** a new module (e.g. `skillsmgr/tracking.py`) used only by the web app; the
scope list gains an optional overlay for the web app, so the CLI and `--scope` stay unchanged
(B1).

**Security note:** like every route, these are protected only by the 127.0.0.1 binding; any local
process can call `check-folder` to learn whether a path inside the home folder exists. It never
reads file contents beyond counting skill folders.

**Decisions this contract makes (all confirmed 2026-11-26):**
1. The file name and place: `<data>/tracking.json`.
2. The three new calls above, and no others.
3. Filtering happens on the server, not only in the browser (needed for "never read, never
   written").
4. The Shared folder is an automatic row, not a checkbox, so the page has 6 agent checkboxes. B11's
   "today's 7" counts the Shared folder; confirmed as 6 checkboxes + 1 automatic row.
5. A tracked agent that reads an untracked agent's folder (Cursor reads `~/.claude/skills` and
   `~/.codex/skills`) doesn't bring that folder back. Its Details say "Also reads Claude Code's
   folder (not tracked)".
6. A custom agent needs an existing folder; a known agent can be tracked before its folder exists
   and appears once it does.

## Traceability (feature)

| Requirement | Served by |
|---|---|
| Choose agents in plain words; folders under Details | S14, S17; principle 4 |
| Not tracked = ignored completely | IA "untracked means absent"; backend filtering; T1 |
| Say what leaves, then Undo | S15; T1; principle 2 |
| Known list + custom agents | S14, S16; T2, T3 |
| Project folders, one at a time | S14, S18, S19; T5 |
| Feature groups off, settings kept | S14, S9+/S10+/S11+; T6 |
| Folder rules, checked live | S16, S18; `check-folder`; T3, T5 |
| Any time, never a setup step | T2 day one; journey stage 1 |
| New agents found later | T7; `seen` |
| Marks for Cursor, Gemini, Command Code (B5) | Phase 3 deliverable |
| Broken settings file (B6) | T8 |
| Last tracked agent (B3) | T1, T9 |
| Phone, light/dark, WCAG 2.2 AA (B7) | Phase 3; S14 phone state |
| Under a minute (B8) | Benchmarks: T1 ~20 s from the page, ~10 s from the header; T3 ~40 s |

**Flags**
- Job 5 asks for "its name and mark". With B4 (neutral icon, no uploads), only a custom agent's
  name is editable; known agents' names and marks are fixed. Choosing between neutral marks would
  be new scope.
- The page name "What to track" is a copy choice; the maintainer can rename it at review.

## Approval (feature)

Hybrid concept (3 + 1), flows T1–T9, screen inventory S14–S19 and the backend contract with its
six decisions approved by the maintainer on 2026-11-26.
