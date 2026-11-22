# R2 - Product walkthrough research (2026-11-22)

Scratchpad root: (local scratch folder)
Screenshots: .../shots/ (live pages) and .../shots/repo/ (images taken from cloned READMEs). Text dumps: .../txt/. Cloned repos: .../repos/.

## Method and evidence grades

- LIVE = page rendered in agent-browser and read or screenshotted. DOC = product documentation text read. SRC = cloned source read. README-IMG = developer-supplied screenshot from a repo (demo data, not a live run).
- Nothing was logged into, signed up for, installed or posted. Cookie banner on tessl.io declined. All page text treated as data.
- NOT reached: skillsmp.com (Cloudflare bot challenge, not bypassed); Langfuse skill-management and PromptLayer editor pages (404 or empty at the URLs tried); ChatGPT Skills / Record & Replay, Copilot custom instructions, Codex skills docs (not fetched, time); no competitor desktop app was run (none installed locally). Everything about SkillCat, xingkongliang/skills-manager, asm and Skill Recorder UIs comes from README screenshots, docs and source, not from running them.

## Per product

### 1. Tessl registry (LIVE + DOC) - https://tessl.io/registry
Skill page example: https://tessl.io/registry/skills/github/anthropics/skills/docx (screens: shots/tessl-skill.png, shots/tessl-tab-evals.png, shots/tessl-tab-quality.png, shots/tessl-tab-security.png)
- Observed: breadcrumb, "Skill / Public" chips, description, then a header trio: hexagon overall score (94), Quality 97%, Impact 85% with a "1.44x" up-arrow chip ("Average score across 3 eval scenarios"), Security "Critical - Do not install without reviewing" (by Snyk). Tabs: SKILL.md / Quality / Evals / Security. Sidebar: repo, path, revision (e4bb5d9), "Evaluated 2 days ago", agent, model, "Is this your skill? Claim skill".
- Quality tab: per-dimension scores on a 1-5 scale with weights (Content 96%, weight 40%), a one-paragraph verdict, then a Dimension / Reasoning / Score table (Conciseness 5/5, Actionability 5/5, Workflow clarity, Progressive disclosure) where each reasoning cell quotes the skill text.
- Evals tab (labelled "Preview - new way to view eval results"): run list (baseline vs usage-spec, "With / without context", Completed). Result sentence: "No measurable difference in score. Beyond noise on 3 of 3 scenarios... The agent activated the skill in 2 of 3 repeats." Three metric cards (Score, Time per solve, Tokens per solve), each with a question as its title ("Does the skill make a difference?", "Is the skill adding bloat, or saving tokens?"), a verdict word ("Unchanged"), and "+26 pts - noise". Footnote: "The grey band is one pooled standard deviation around Without skill. A change inside it is noise." Activation panel ("Did the agent actually use the skill? 67%, 2 of 3 repeats"), by-scenario table with Change and Activated columns ("Not used" shown), Setup panel (same for every variant: skill@version, model, agent, starting files, "Activation: Forced", "3 scenarios, 1 attempt each", "0 of 6 solutions reused from earlier runs").
- Security tab: finding list with codes (E004, W011), severity, "What this means", "Why it was flagged", "Report incorrect finding" link, audited date.
- Docs (DOC): `tessl review run` gives 0-100 with description and content dimensions and bands (>90 good, 70-89 ok, <70 needs work); `tessl review fix` loops improve-and-review to 90% or 3 rounds, asks before applying in a terminal, applies nothing in CI without --yes; `tessl scenario generate` (default 3 scenarios, only feasibility-checked ones saved); `tessl eval run` runs each scenario with and without the skill, `--runs 3` to average; `tessl eval compare`; install policy with warn and block severities, Passed/Advisory/Risky/Critical labels, "no override" on block; Org "Context" and "Findings" pages classify first-party vs matched third-party skills; custom review rubric enforced in CI.
- Standout: question-as-title metric cards; noise band with an explicit "Unchanged" verdict; "Not measured" kept distinct from zero; "Forced" activation disclosed; every score has quoted evidence; "Report incorrect finding".
- Anti-patterns observed: headline contradicts itself (94 score and "1.44x" in the header and registry cards, but the eval page says "No measurable difference"; 1.44x comes from a single attempt per scenario, n=3). Security "Critical" with an E004 "prompt injection detected" label while its own explanation calls the skill "a legitimate docx editing toolkit... without malicious intent". The severity label and the narrative disagree, and a Critical badge on a flagship Anthropic skill trains users to ignore badges. Registry homepage "UPLIFT UP TO 2.0X" marketing numbers sit next to the per-skill truth.

### 2. skills.sh (Vercel) (LIVE) - https://skills.sh, /audits, /anthropics/skills/frontend-design (shots/skills-sh*.png)
- Observed: ASCII-art hero, "npx skills" try-it box, leaderboard with All Time (1,502,397) / Trending (24h) / Hot tabs, columns rank, skill, 8W ACTIVITY sparkline, INSTALLS. Packs, Topics, Official, Audits nav. /audits: table of skill vs three scanners (Gen Agent Trust Hub: SAFE; Socket: "0 ALERTS"; Snyk: LOW / MED / HIGH / CRITICAL RISK) as colored pills with 3-bar glyphs; PENDING shown for unscanned. Detail page: Install tab with Command / Prompt toggle (copy an install command, or copy a prompt to paste to an agent), a short AI-written SUMMARY (4 bullets), rendered SKILL.md, "related skills", sidebar facts (installs 1.2M, repo, stars 198.4K, first seen, per-scanner PASS).
- Standout: three independent scanners side by side without merging into one grade; PENDING as a real state; install-as-prompt; summary above the raw SKILL.md; sparkline of activity.
- Anti-pattern: three scanners disagree on the same skill (Snyk MED RISK while the others say SAFE) with no explanation or "why" drill-down on the list.

### 3. Anthropic skill-creator (SRC, local copy) - ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/
- Observed in source: the loop is draft, run with/without skill, grade assertions, aggregate benchmark (pass rate, time, tokens, mean +/- stddev, delta), analyst pass, launch viewer. Viewer has two tabs. Outputs: one test case at a time with Prompt, Output, collapsed Previous Output (iteration 2+), collapsed Formal Grades, auto-saving Feedback box, Previous Feedback; prev/next with arrow keys; "Submit All Reviews" writes feedback.json. Benchmark tab: stats per configuration with analyst observations. Empty feedback is read as "looks fine". Blind comparator and analyzer agents exist for A/B between versions. Description optimizer: generates 20 trigger queries (8-10 should-trigger, 8-10 near-miss should-not-trigger), shows them in an editable HTML review page (toggle should_trigger, add/remove, Export Eval Set), then optimizes the description.
- Standout: human feedback tied to a case and iteration; near-miss negatives; editable eval set before spending tokens; "previous iteration" side-by-side.
- Anti-pattern (DOC, per the research doc): reports 0% trigger recall and optimizes anyway (anthropics/skills#1721).

### 4. SkillCat (README-IMG + SRC) - https://github.com/Konata9/skillcat (shots/repo/skillcat-*.png)
- Observed in screenshots: left nav Skills / Issues & scores / Usage log / Skills market; scope sidebar (Global, pinned projects with star); skill list with filter box "Filter by name / description / trigger / source", status pills ("dangling", "manual"); detail pane with Details | Suggestions tabs, trigger profile (positive triggers as chips tagged by source: when_to_use, body, name), links state (symlink / missing / copy / dangling), body. Issues view: "Evaluation overview - Average score 72 - Generated 1 hour ago - gpt-4o", findings tabbed All / Errors / Warnings / Info, each finding tagged Deterministic or Heuristic with a Similarity %, Details, Suggestion (a literal command), Evidence, Related skills. Buttons "Rescan", "Evaluate skills", "Review candidates".
- SRC: scoring prompt batches up to 6 skills, grades A (90+) B C D, max 2 sentences, max 3 strengths/issues; duplicate/conflict candidates are pre-filtered deterministically (trigger overlap >= 0.2 or body similarity >= 0.15, max 24 pairs) and the model only judges them (confirmed / false-positive / uncertain). Catalog ids (s1, s45) are mapped back to names. Saved results carry a signature of model + content hash, and the UI shows "evaluation stale" when either changes. "Test connection" sends a max_tokens=1 ping. Optimization suggestions are read-only (title, severity, rationale, before, after), persisted until the user regenerates (avoids repeat token spend); a same-named user skill is never used as the rubric (injection guard). Streams step events (prepare, scoring, pairs, judging, summary) into a progress log.
- Standout: Deterministic vs Heuristic vs AI label on every finding; stale-evaluation banner; prefilter then judge; evidence field; command in the suggestion.
- Anti-pattern: no apply path (suggestions are read-only), so the last step is manual copy.

### 5. skilljack-evals (SRC/README) - https://github.com/olaservo/skilljack-evals
- Observed in README/source: task packages with deterministic checks (contains, regex, files_exist, tool_calls), optional verifier script, optional LLM assertions. Metrics: resolution rate with 95% binomial CI, pass@k, skill lift (with minus baseline) per task and macro, skill invocation rate. Paired baseline runs by default. CI thresholds; lift gate "fails closed" if no baseline ran. Judge is diagnostic only and never changes reward; failure categories: discovery_failure, false_positive, instruction_ambiguity, missing_guidance, agent_error. `--nudge off|name|description|full` separates "can't discover" from "can't follow". `--blind-compare` anonymizes outputs for A/B of two skill versions. Content-addressed cache keyed on skill hash so editing a skill invalidates only its entries. Oracle gate proves a task is solvable before trusting it. Candid "Security model" section (CLI runners run with all permissions).
- Standout: deterministic reward is authoritative, judge never gates; failure-category attribution; fail-closed gate; cache keyed on content.

### 6. Cisco skill-scanner (SRC/README) - https://github.com/cisco-ai-defense/skill-scanner
- Observed: engines (YAML+YARA, AST dataflow, optional LLM judge, cloud), presets strict / balanced / low-noise / quiet / permissive, output summary / table / markdown / json / sarif / html (self-contained, collapsible correlation groups). Publishes measured numbers per preset: rules alone catch 7.7% of malicious skills at 4.0% FPR; with the judge 66.7% reach review at MEDIUM+ (15.4% FPR). Recommended-settings table maps a goal ("smaller review queue", "lowest false-positive rate", "nothing leaves the machine") to a command and its recall/FPR/F1. Prominent "best-effort, no findings does not mean safe" banner.
- Standout: choose a preset by goal with its measured error rates beside it; honest "no findings is not safe" copy; local-model option for privacy.

### 7. asm / agent-skill-manager (README + screenshots) - https://github.com/luongnv89/asm (shots/repo/asm-eval-skill.png, asm-audit.png)
- Observed in README: `asm stats --tokens` splits resident cost (descriptions, paid every message) from body cost (paid when fired), per tool and scope, with a "heaviest resident descriptions" list and median. `asm audit residency` ranks skills that do not earn residency and pairs each with the right demotion command for how it is installed; reports only, never acts; lists unavailable signals (trigger collision, last-used) as "unavailable" instead of dropping them. Demotion ladder: installed, saved, disabled, reference (`asm get` prints body once, zero residency). `asm audit overlap` finds different-name skills doing the same job. `asm eval`, pre-install security scan, `--json` everywhere.
- Standout: demotion ladder instead of binary keep/delete; "signals we wish we had" shown as unavailable; nothing changes without the user running the suggested command.

### 8. Claude Code skills and /doctor (DOC, LIVE page read) - https://code.claude.com/docs/en/skills
- Observed in docs: /doctor "reports findings first and asks for confirmation before changing anything"; extensions section compares unused skills/MCP/plugins to context cost; CLAUDE.md section offers to migrate always-loaded guidance into on-demand skills; `/doctor prompt-audit` checks CLAUDE.md, skills and config for outdated or conflicting instructions; `/skills` menu (per skills-janitor README: sort by token count with `t`, hide with Space); skillOverrides entries "off"; `/run-skill-generator` and `/verify` write a recipe skill after a successful run (skill drafted from real work); live watching of .claude/skills during a session.
- Standout: report-then-confirm; cost-vs-usage; draft a skill from a verified successful run.
- Note: skills-janitor README (v1.8) says Claude Code now covers context-cost and unused-skill detection natively, so a manager's differentiator is cross-agent view, duplicates, security and apply/undo.

### 9. Cursor (DOC, LIVE page read) - https://cursor.com/docs/context/skills
- Observed: built-in slash skills that author configuration: /create-rule, /create-skill, /create-hook, /create-subagent, /migrate-to-skills ("Converts eligible dynamic rules and slash commands into Agent Skills"). Customize sidebar > Skills lists discovered skills next to rules in an "Agent Decides" section. Skills can be invoked manually with `/` and attach to one message, or kept on for a session via Custom Mode. Nested .cursor/skills folders discovered in monorepos. Settings toggle "Sync Skills for Cloud Agents".
- Standout: conversion of one format to another as a named, discoverable command; "Agent Decides" label explains activation mode in plain words.

### 10. Kiro steering (DOC, LIVE) - https://kiro.dev/docs/steering/
- Observed: capability matrix (IDE / CLI / Web / Mobile) shows "Generate foundation files via UI" is IDE-only. "Generate Steering Docs" button, or + then "Foundation steering files", creates three files in .kiro/steering/ (product, tech, structure) that load in every interaction. Custom steering: pick scope (workspace or global), pick filename, write markdown. Custom agents do NOT inherit steering automatically; it must be listed in resources.
- Standout: one-click generate-from-codebase with a fixed three-file output; explicit scope picker at creation.
- Anti-pattern: silent non-inheritance in custom agents is documented only in prose.

### 11. Windsurf / Devin Desktop customize page (DOC, LIVE) - https://docs.windsurf.com/windsurf/cascade/memories (redirects into Devin docs)
- Observed: "The Customize page has tabs for Plugins, Skills, MCPs, Hooks, Rules, Subagents. Each tab lists what the agent has loaded, along with what your repository, organization and account offer." A table maps each customization to "What it does / How it's activated / When to use it". Scope selector ("Install MCPs for: This computer").
- Standout: "what this session actually loaded" next to "what is available" in one list; activation-mode column.

### 12. Cline rules (DOC, LIVE) - https://docs.cline.bot/customization/cline-rules
- Observed: Rules panel (scale icon by the model selector) lists every detected rule type (.clinerules, .cursorrules, .windsurfrules, AGENTS.md) with a per-rule toggle; conditional rules with `paths` globs; two levels of control (manual toggle plus condition). Docs include "Test your patterns: create a simple test rule" and a troubleshooting checklist ("verify the rule is toggled on").
- Standout: foreign formats auto-detected and togglable without conversion; manual toggle plus automatic condition.

### 13. Promptfoo web viewer (DOC, LIVE) - https://www.promptfoo.dev/docs/usage/web-ui/
- Observed: display-mode filter All / Failures / Passes / Errors / Different / Highlights; text or regex search; metric/metadata filters; per-cell hover actions Details, Pass (score 1.0), Fail (0.0), Custom score, Comment, Highlight; ratings and comments persist and export; Compare diffs two evals (green added, red removed); "Edit and re-run"; export as YAML, failed-only, CSV/JSON, DPO JSON, Human Eval YAML; charts for pass rate and score distribution.
- Standout: human override of an automatic grade is first-class, stored and exportable; "Different" filter for regressions between runs.

### 14. Langfuse, PromptLayer, LangSmith prompt management (DOC)
- Langfuse (https://langfuse.com/docs/prompt-management/overview): versions plus labels for environments, prompts linked to traces so performance is analysed per version, client-side cache, nav now reads "Prompt & Skill Management" (a skills page was not found at the URLs tried).
- PromptLayer (https://docs.promptlayer.com/features/prompt-registry/overview): save new version with commit message, release labels (prod, staging) with approval flows for protected labels, open in Playground and "save changes back as a new version", AI prompt writer and version diffs named in next-steps (page itself not read).
- LangSmith (https://docs.smith.langchain.com/prompt_engineering/how_to_guides): Playground with "Chat in the Playground to generate tools, create output schemas, and optimize your prompts with AI assistance"; model config saved with the prompt version; "Used in Evaluators" filter separates judge prompts from normal prompts.
- Standout: labels rather than "latest"; commit message on every version; judge prompts kept in their own filtered bucket.

### 15. Aitmpl / Claude Code Templates (LIVE) - https://www.aitmpl.com (shots/aitmpl.png)
- Observed: sidebar counts (Skills 945, Agents 423, Commands 288, Settings 87, Hooks 64, MCPs 143, Mods 51, Plugins 37), "My Components", Trending, Leaderboard, Jobs, Certifications, ASCII hero with an animated download counter, Ctrl+K search. No AI feature visible on the landing page; breadth catalogue only.
- Anti-pattern: raw counts and a vanity counter with no quality or trust signal on the first screen.

### 16. Smithery (LIVE) - https://smithery.ai (shots/smithery.png)
- Observed: banner "MCP Proxy and managed identity shut down on October 31", cards with one-line descriptions, many "auth and credentials handled for you" blurbs. Cards carry no scores or evidence.

### 17. SkillsMP (not reached) - https://skillsmp.com
- Cloudflare "Performing security verification" interstitial in the headless browser (shots/skillsmp.png). Not bypassed. No observations.

### 18. New products found
- xingkongliang/skills-manager (7.7k stars, desktop app, README-IMG shots/repo is not copied; see repos/skills-manager/assets/demo/): Dashboard, Library (grid/list toggle, All / Enabled / Available, tag chips including "Untagged", per-skill on/off toggle, per-agent icon strip, "Update All (4)", "Check All", "Unbacked changes" button), Install Skills, Backup page (Git-backed snapshots; restore first saves current state as its own snapshot; conflicting edits across devices keep local version and surface under "Needs attention"), compare local content with upstream. No AI features claimed.
- jiweiyeah/Skills-Manager (1k stars): symlink sync to 32 tools; only AI feature is LLM translation of skill content; roadmap item "AI chat to test skills in app".
- khendzel/skills-janitor (140 stars; Product Hunt page blocked in headless): `/janitor-swipe` TUI "swipe keep / delete / skip" sorted most-likely-waste first, report, value (honest token costs), security scan, discover with pre-install check. Now in maintenance mode because Claude Code covers core cost and usage natively.
- microsoft/skill-recorder (5.9k stars; README-IMG shots at repos/skill-recorder/docs/images/library.png): record a work session, Analyze produces "What you did" (an intent sentence) plus numbered steps, each editable in place, reorderable ("saved automatically"), then Create... a Skill or scheduled Automation. "Review SKILL.md" is an optional read-only preview that writes no files and is reused exactly on Add/Export; editing the plan discards the preview. Candid note: review is visibility, not a security guarantee.
- microsoft/SkillOpt (19k stars, paper): trains a skill document with bounded add/delete/replace edits, a textual learning-rate budget, a rejected-edit buffer, and acceptance only when a held-out validation score strictly improves; SkillOpt-Sleep does nightly offline harvest, mine, replay behind a held-out gate.
- microsoft/apm: manifest (apm.yml), lockfile with commit and per-file SHA-256, org policy; governance model rather than UI.

## Cross-product UX patterns (24)

1. Question as the title of each metric card ("Does the skill make a difference?") plus a one-word verdict. Seen: Tessl Evals tab.
2. Noise band and an explicit "Unchanged / within noise" verdict instead of a bare delta. Tessl; also Promptfoo "Different" filter.
3. "Not measured" and "Not used" as states distinct from zero. Tessl activation panel; asm "unavailable" signals; skills.sh PENDING.
4. Disclose the setup that makes a result comparable (model, agent, forced vs natural activation, attempts, reused results). Tessl Setup panel; skilljack-evals nudge levels.
5. Header numbers must not contradict the detail page. Anti-pattern: Tessl 1.44x headline vs "no measurable difference". Show n beside any multiplier.
6. Every score carries quoted evidence per dimension. Tessl Quality tab; SkillCat Evidence field.
7. Tag each finding with its source kind: Deterministic, Heuristic, AI. SkillCat.
8. Stale-result banner keyed on model plus content hash; do not silently reuse old AI output. SkillCat.
9. Persist AI suggestions until the user explicitly regenerates, to avoid repeat spend. SkillCat optimizer.json.
10. Deterministic pre-filter picks candidate pairs, the model only judges them (confirmed / false positive / uncertain). SkillCat; asm overlap.
11. Report first, ask, then apply; ask before changes in a terminal and refuse to apply in CI without a flag. Claude /doctor; `tessl review fix`.
12. Reports that name the exact command to run, tailored to how the skill is installed. asm residency; SkillCat suggestion text.
13. Demotion ladder (installed, saved, disabled, reference) instead of keep/delete. asm.
14. Resident cost vs on-demand body cost shown separately, with heaviest items listed. asm stats --tokens; Claude /doctor extensions section.
15. Several independent security scanners side by side, with PENDING and per-scanner reasons, not one merged grade. skills.sh audits; Tessl Snyk tab with "Report incorrect finding".
16. Choose a scan or strictness preset by goal, with measured recall and false-positive rate beside it, and a "no findings is not safe" banner. Cisco skill-scanner.
17. Severity label must match its narrative; avoid a Critical badge whose own explanation says "legitimate, no malicious intent". Anti-pattern: Tessl docx.
18. Draft from real work with a reviewable intent-plus-steps stage before generation: editable numbered steps, then Create. Skill Recorder; Claude /run-skill-generator and /verify.
19. Optional read-only "Review SKILL.md" preview that writes nothing and is reused exactly on Add/Export; any edit to the plan discards it. Skill Recorder.
20. Convert one format into another as a named command. Cursor /migrate-to-skills; Cline auto-detects .cursorrules, .windsurfrules and AGENTS.md; Claude /doctor offers to migrate CLAUDE.md content into skills.
21. One-click generate foundation files with a fixed set of outputs. Kiro "Generate Steering Docs" (product, tech, structure).
22. Show what a session actually loaded next to what is available, with an activation-mode column or section name ("Agent Decides"). Devin/Windsurf Customize page; Cursor Customize > Skills; Cline Rules panel with toggles.
23. Human feedback per case with auto-save, previous-iteration feedback and prior output collapsed beneath; empty feedback means fine. Skill-creator viewer. Plus override a grade with pass/fail/score and a comment, stored and exportable. Promptfoo.
24. Near-miss negatives and an editable eval set before any tokens are spent. Skill-creator description optimizer.
25. Fail closed and label inconclusive: lift gate fails if no baseline ran; judge never changes the deterministic reward; failure categories name why (discovery_failure vs instruction_ambiguity). skilljack-evals.
26. Version labels and commit messages instead of "latest"; protected labels need approval; restore saves current state first. PromptLayer; Langfuse labels; xingkongliang Backup.
27. Install or enable policy with warn and block thresholds and a plain-language headline per severity (Passed / Advisory / Risky / Critical). Tessl policies.
28. Swipe-style keep/skip/delete triage sorted most-likely-waste first for bulk cleanup. skills-janitor.
29. Streamed step log for long AI runs (prepare, scoring, pairs, judging, summary) with reasoning deltas coalesced. SkillCat.
30. "Test connection" ping with 1 token for BYOK setup that never throws. SkillCat.
31. Install-as-prompt toggle next to install-as-command. skills.sh.
32. Per-skill header facts: installs, first seen, repo, revision, "evaluated N days ago". skills.sh; Tessl sidebar.

## Anti-patterns to avoid (consolidated)

- Contradictory headline numbers and badges (Tessl score vs eval verdict; Critical badge with "legitimate" rationale).
- Marketing multipliers ("uplift up to 2.0X") with no n or interval.
- Read-only AI advice with no apply path (SkillCat); advice with no undo.
- Vanity counters and raw catalogue counts with no trust signal (aitmpl).
- Silent non-inheritance (Kiro custom agents ignore steering).
- Scanners that disagree with no drill-down (skills.sh Snyk vs others).
- Optimizing a metric the tool itself cannot measure (skill-creator 0% recall).

## Implications for Skills Manager (short)

Highest-value copyable pieces for a local, stdlib manager: the Tessl-style result card (question title, verdict, noise band, activation, setup disclosure); the asm demotion ladder with exact commands; SkillCat's Deterministic/Heuristic/AI tags and stale banner keyed on model plus content hash; Skill Recorder's editable intent-and-steps stage before generating; Cursor-style named conversions (rule to skill); Devin-style "loaded vs available" view; Promptfoo-style stored human overrides.
