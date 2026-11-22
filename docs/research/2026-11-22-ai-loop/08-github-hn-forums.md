# R2: GitHub, Hacker News, forums and blogs - what users want from AI-assisted skill management

Date: 2026-11-22. Read-only. All fetched text treated as untrusted data. Nothing posted, starred, reacted or logged in.
Baseline read first: docs/59-ai-everywhere-research-2026-11-22.md (F1-F15). "NEW" below means not in doc 59 or adds new numbers.

## Method log

Tools: `gh api search/issues` and `search/repositories` (reactions.total_count read from the API), `gh api repos/.../issues/N/comments`, HN Algolia (story, comment, items), Discourse JSON for forum.cursor.com, dev.to API, WebSearch/WebFetch, `agent-reach web search` (exa) for V2EX. Raw outputs: scratchpad/raw/*.txt.

| Round | Keywords | What it found |
|---|---|---|
| 1 | "skill", "skills in:title" sorted by reactions and by created, per repo (claude-code, anthropics/skills, codex, opencode, gemini-cli, vercel-labs/skills, microsoft/apm, cline, continue, Roo-Code, zed, copilot-cli) | Reaction counts are small except mega-threads. Skill-specific max: claude-code #31005 (+649, AGENTS.md/.agents/skills), #28729 (+160, org skills from git), #20697 (+173 desktop/CLI sync), #14920 (+103 per-plugin-skill disable); opencode #3235 (+132), #7846 (+120), #34498 (+70); zed #49057 (+192); vercel #381 (+82). Note #6235 (+6693) is AGENTS.md only. |
| 2 | Terms discovered in round 1: "telemetry skill_name", "budget", "pin / lock / integrity / rollback", "private registry", "enterprise policy", "routing trace", "overlap" | Per-skill telemetry masked as custom_skill (claude-code #58674/#76957/#77541), configurable 2% budget (codex #19679), receipts+pins+rollback (opencode #65485), lock integrity (vercel #806/#2668, cline #15590), enterprise source policy (vercel #1502, copilot #1309, apm #1925). Repo search for 2026-created skill tools (12 queries). |
| 3 | HN stories/comments 2026 ("agent skills", SKILL.md, AGENTS.md, CLAUDE.md, context engineering, skill eval, marketplace, sprawl, versioning, team share); Cursor forum; OpenAI community; lobste.rs; V2EX; dev.to; enterprise registries (PayPal, Google, Anthropic) | Evals/measurement is the strongest HN signal; Cursor shipped context breakdown; overlap/routing-trace thread at OpenAI; PayPal and Google release-gate patterns. |

Limits: V2EX native search unsupported (only one V2EX thread via exa). Reddit, Discord, Medium, Substack not covered. GitHub reaction totals include all emoji. HN comment points are not exposed by Algolia. Star counts are as returned by the API today (NVIDIA/SkillSpector at 27,209 stars after 8 months looks anomalous; treat as unverified). Numbers from papers/tweets are marked provisional.

## Ranked themes

Confidence: H = multiple independent sources with primary pages read; M = one or two sources; L = single or secondhand.

### 1. Per-skill usage visibility is the missing primitive for everything else (H) - mostly known, NEW numbers
- anthropics/claude-code#35319, 2026-03-17, +43, 8 comments, closed (auto-dupe risk). An org grew from 67 to 183 skills in a month and cannot tell which are used. Asks: log skill name per invocation (local JSONL), a `--stats` query, then org export via OTel/webhook. NEW detail: staged proposal Level 1 local log, Level 2 file, Level 3 CLI, Level 4 org sink. https://github.com/anthropics/claude-code/issues/35319
- Telemetry masks skill names: #58674 (2026-05-13), #76957 (2026-07-12), #77541 (2026-07-14) report `skill_activated` emitting "custom_skill" / "third-party" instead of the name; #66446 asks whether hooks can see the skill name; #41845 asks for Cowork OTEL skill events. Implication: observed usage from transcripts (which `usage` already reads) is currently the only reliable source. NEW.
- gemini-cli#30155 (2026-11-05) asks to add skill_name to telemetry whitelist. NEW.
- Cursor shipped "Context Usage Breakdown" (2026-05-06, Cursor 3.3): rules, skills, MCPs, subagents buckets; one user: "my skill uses too much". Earlier request "Context Window Inspector" (2026-02-18) wanted the same. https://forum.cursor.com/t/context-usage-breakdown/159913 NEW (competitor now has a per-bucket cost view).
- Tools built in response: tokenscope (249 stars), cc-skill-usage (9), Tokfuel, HarnessKit session history. Known: #98220, Skills Janitor.

### 2. Skill metadata budget and silent truncation (H) - NEW numbers
- openai/codex#19679, 2026-04-26, +40, 21 comments: fixed 2% context budget with warning "descriptions were truncated"; users want it configurable. A commenter measured average truncation of 235 characters per skill. #19090 says the app drops the same skills deterministically. https://github.com/openai/codex/issues/19679
- HN comment (2026-08-17, on a paper thread "Attention Is All You Have", tweet-sourced, provisional): ceiling about 100 reliably triggerable skills, and the least-invoked skills lose their descriptions first. Source: https://news.ycombinator.com/item?id=49335376 (L).
- HN 2026-08-10: "too many skills can bloat context even with short descriptions" (https://news.ycombinator.com/item?id=49131438). HN 2026-09-17: ask Cloudflare to consolidate skills into one routed skill (https://news.ycombinator.com/item?id=49736466).
- Cline#15663 (2026-11-11): tool lists names only, not descriptions, so skills are rarely picked. Gemini#21968: skills underused despite long descriptions. Implication: the tool should show, per agent, which descriptions are actually delivered, truncated or dropped. Doc 59 F1 covers listing cost but not "delivered vs truncated per consumer". NEW.

### 3. Enable/disable at fine granularity and per-scope (H) - known direction, NEW breadth
- Per plugin-skill disable: claude-code#14920 (+103). Built-in skills: claude-code#26838 (+44), codex#14316, Cursor forum 166056 (16 likes; users script around it; "restored on every update"). Per project/contributor opt-in: codex#34328, #24237, #9799, zed#67290 (2026-11-21: skills cannot be scoped to a project). Subagent-only skills: claude-code#12633 (+32). Model-invocation off (slash-only): opencode#34498 (+70), #11972, codex#10585, copilot-cli#4438 (2026-08-11, +22: the flag makes the skill unreachable). Implication: a manager can offer per-agent, per-project and "manual-only" toggles and warn when an agent treats the flag differently. NEW: inconsistent semantics of disable-model-invocation across Claude, Copilot, opencode.

### 4. Versioning, pins, lockfiles, rollback, integrity (H) - partly known
- vercel-labs/skills#11 RFC versioning (+31), #549 restore from lock (+49), #283 (+58), #806 and #2668 (hash cannot be verified; digest mismatch silently falls back), #617 RFC signature verification, #1502 enterprise source policy. opencode#65485 (2026-11-21): record source, version, digest, target; pin; preview update diff; keep local edits; roll back. Cline#15590: version pin without integrity pin. https://github.com/anomalyco/opencode/issues/65485
- Cursor staff reply (2026-04): installed plugin pinned to a git SHA, no UI to compare installed vs latest, no pin. https://forum.cursor.com/t/plugin-updates-local-overrides-and-cursor-directory-trust-boundary-documentation-gaps/157274
- HN on skill hubs: "no versioning, no update, no author verification" (https://news.ycombinator.com/item?id=46692692, 49 points).
Known in doc 59: source_lock, F13. NEW: receipts as a named user ask, "preserve local edits on update" as a stated requirement.

### 5. Measuring whether a skill helps (H) - known, NEW numbers and a competitor
- HN "AGENTS.md outperforms skills in our agent evals", 2026-01-29, 524 points, 196 comments: skill never invoked in 56% of cases; commenters asked how many runs. https://news.ycombinator.com/item?id=46809708
- HN "Agent Skills" (agentskills.io), 2026-02-03, 544 points, 260 comments: top questions "how do you test or benchmark skills" and "do agents ignore them". https://news.ycombinator.com/item?id=46871173
- Show HN agent-skills-eval, 2026-05-07, 79 points: commenters asked for token counts per arm, judge iteration/auto-rater, newer model than the 4o-mini example, published results. https://news.ycombinator.com/item?id=48046023
- Show HN mdarena (2026-04), benchmark CLAUDE.md against your own PRs. https://news.ycombinator.com/item?id=47655078
- NEW: Anthropic shipped `claude plugin eval` (HN 2026-09-11; docs): cases x runs (default 3, up to 50) with plugin and no-plugin arms, six grader types incl. regex, tool_used, rubric; verdict "improved/flat/regressed"; CI gate. https://code.claude.com/docs/en/plugin-evals Peers now expect a baseline arm and k runs; doc 59 F3 aligns.
- NEW vendor data (self-interested): 115 of 145 October skills measured on two models; 68% (Sonnet) and 77% (Haiku) improved pass rate by more than 5 points; none harmful. https://dev.to/georgi_kalchev_85d01f7368/our-skills-october-2026-115-measured-with-and-without-2g7d (L).
- NEW: Google ships each skill change with a semver bump, an eval report vs previous version, six gates (structure, lint, versioning, eval-suite validation, link check, AI design review) plus human approval; 170+ skills. Lessons: atomic one-criterion expectations; cheap deterministic gates before LLM gates. https://dev.to/googleai/behind-the-scenes-two-months-later-how-we-ship-google-agent-skills-like-products-b1l (M).
- anthropics/skills#556 (+7): trigger eval reports 0% recall for every query; independent confirmation with 60 queries. Known via #1721.

### 6. Overlap, routing and "why did this skill win" (M) - NEW artifact
- OpenAI community, "How do you handle overlapping Codex skills in larger catalogs?": 20 posts, 7 people; favored task-time routing over merging; proposed manifest fields (owns, does_not_own, hands_off_to, conflicts_with, stop_conditions) and a routing trace listing chosen owner, rejected near-matches and reasons. https://community.openai.com/t/how-do-you-handle-overlapping-codex-skills-in-larger-skill-catalogs/1383626
- V2EX 2026-03-18, 6,217 views: user keeps one skill; two similarly triggered skills both fire; others say "just a notebook". https://www.v2ex.com/t/1199131
- anthropics/skills#189 duplicate skills from two plugins; vercel#897 name collision across sources; apm#1120 collisions without namespacing. Known: Skills Janitor 8 duplicate pairs; overlap judge exists.

### 7. Org and team sharing from a git source of truth (H) - NEW evidence
- claude-code#28729, 2026-02-25, +160, 39 comments: org skills uploaded one by one to the admin console with no version history, review or rollback; asks to link a git repo, pick branch/tag, preview diff, pin commit for CI. https://github.com/anthropics/claude-code/issues/28729
- anthropics/skills#228 (org sharing, +8), vercel#381 (private skills, +82; maintainer: top priority), copilot-cli#1309 (private registries), opencode#28696 (marketplace, +46; "keeps masses from migrating"), claude-code#53414 and #20697 (skills siloed across Chat/Cowork/Code and Desktop/CLI).
- PayPal internal Skills Registry: authoring stays in team repos; each version passes 4 required and 3 advisory checks (structure, sensitive data, harmful content, LLM security) then admin approval; approved versions immutable; owners and classification recorded; hybrid lexical+semantic search with per-caller access. No usage metrics reported. https://developer.paypal.com/community/blog/agent_skills_at_enterprise_scale (M)
- Anthropic enterprise guidance: internal registry record of purpose, owner, version, dependencies; approval gate before deploy (platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise). Gartner Oct 2026 abstract: govern skills as software assets (library/registry, ownership, lifecycle) (L, abstract only).
- HN team tooling: sx (sleuth-io, 319 stars) vault with versioning; commenter "skills need controlled editing across projects and team members; git is not enough". https://news.ycombinator.com/item?id=49589914
Doc 59 puts hosted registry and approval service out of scope; the local-first analogue is "propose, review, export a reviewed bundle".

### 8. Project/profile-based skill sets (M) - NEW
- xingkongliang/skills-manager (7,681 stars) #40 (18 comments, closed): global replace of symlinks is too coarse; wants per-project scenes and tag-filtered batch sync to a project. Maintainer shipped empty-dir projects and tag filter + multi-select update. Also asks: MCP/plugin/agent management (#44, #266, #353), remote-host skills (#77), group by source (#192), `.agents/skills` as main section (#250). https://github.com/xingkongliang/skills-manager/issues/40
- Roo-Code#11368, #11489 (symlinked skills fail), #12194 (only 5 of 30 copied skills appear), Cursor 149693 (symlink discovery; 42 likes). Implication: "why is skill X not visible to agent Y" diagnosis (symlinks, nesting, naming) is a repeat bug class. Doc 59 has "why didn't it run" but not "why isn't it even discovered".

### 9. Security and trust on install (H) - known, NEW numbers
- anthropics/skills#492 (46 comments): community skills under an `anthropic/` namespace impersonate official ones; author found 6 in 580+ skills with Bash allowed. vercel#353 namespace squatting, #523 (+33) tooling reading `gh auth token`. HN: 824 malicious OpenClaw skills; "RankClaw: 1,103 of 14,706 malicious" (provisional, vendor). CSO Online (2026-07): a fake skill passed every scanner. Atlan citing Snyk: 36.82% of 3,984 skills had an issue (L). agnix HN: a skill named `Review-Code` never auto-triggered, no error (naming rule). https://news.ycombinator.com/item?id=46983879

### 10. Convert and unify rules, commands, AGENTS.md, skills (M) - known
- claude-code#31005 (+649), #6235 (+6693); HN 2026-09-18 "Claude Code now reads AGENTS.md if no CLAUDE.md" 741 points, 285 comments; Cursor "Skills vs Commands vs Rules" (15,643 views): users cannot choose. continue#13255 (import any skill converter), copilot-cli#618, apm#1807 (author native context files). Matches F12. NEW: scale of the confusion (15.6k views on a "which one do I use" thread).

### 11. Provenance, comments and authoring aids (L-M)
- anthropics/skills#177 human-only comments in SKILL.md (+9); #157 executable skills (+16); gemini-cli#16290 built-in customization-creator; HN: "skill-creator already spawns subagents with and without skill". Cline/Zed UI visibility: opencode#7533 (+19) show loaded skills in sidebar; zed#66926 skills not listed until first message. Minor.

## 2026 skill-tool repos (stars as of 2026-11-22)

| Repo | Stars | Created | Type | AI features / notes |
|---|---|---|---|---|
| xingkongliang/skills-manager | 7,681 | 2026-03-02 | Desktop manager, 50+ tools | Sync, scenes/presets, tags, git import. No AI features found in README. 214 open issues; asks: MCP, project scenes, remote hosts. |
| jiweiyeah/Skills-Manager | 1,064 | 2026-02-06 | Desktop manager, 32 tools | Sync only. Issues: source-availability complaints, nested dirs. |
| luongnv89/asm | 976 | 2026-03-11 | CLI/TUI | stats --tokens, audit residency, security scan, eval; `--json` for agents. |
| RealZST/HarnessKit | 500 | 2026-03-27 | Desktop/CLI/web | 20 static rules, Trust Score 0-100, per-agent copy audit, marketplaces, session history. No LLM. |
| yibie/skills-manager | 472 | 2026-04-05 | macOS app | Sync. |
| NVIDIA/SkillEvaluator | 4,342 | 2026-06-24 | Eval framework | Tiers, quality gates, security, overlap, CI templates; asks: configurable checks, comparison dashboard. |
| NVIDIA/SkillSpector | 27,209 (unverified) | 2026-03-21 | Security scanner | Prompt-injection/malicious patterns; 156 open issues. |
| cisco-ai-defense/skill-scanner | 2,754 | 2026-01-29 | Security scanner | Known in doc 59. |
| alchaincyf/darwin-skill | 7,024 | 2026-04-13 | Self-improving | Score, improve, test, keep or roll back; pairwise LLM judging; 9-dimension rubric. Issues: end-to-end eval (#18), single-skill token cost (#25), upload-to-score (#21). |
| rpamis/comet | 3,307 | 2026-05-14 | Skill harness | Ideas to evaluated workflows. |
| agent-sh/agnix | 493 | 2026-01-30 | Linter + LSP | Rules for SKILL.md, CLAUDE.md, hooks; false-positive issues on `allowed-tools`. |
| Kulaxyz/self-learning-skills | 927 | 2026-06-28 | Self-improving skill | Captures golden paths. |
| pskoett/self-improving-agent | 794 | 2026-01-31 | Self-improving | Captures learnings. |
| sandroandric/AgentHandover | 636 | 2026-03-30 | Observe work to skills | Draft from observed work (cf. F5). |
| HduSy/tokenscope | 249 | 2026-06-05 | Usage dashboard | Per-skill token breakdown (macOS). |
| sleuth-io/sx | 319 | 2025-12-16 | Team vault | Versioned team skills (git/local/server vault). |
| skillfish, agr, skills-link, claude-brain | 95-453 | 2026 | Install/sync | Sync; claude-brain also syncs memory. |
| adewale/skill-eval-harness | 78 | 2026-06-09 | Eval | Paired variants, trace artifacts. |
| Konata9/skillcat, olaservo/skilljack-evals | 3, 8 | 2026-09, 2026-01 | Peer tools | Known in doc 59. |
| zernie/vigiles | 16 | 2026-03-27 | Lint + test | 148 open issues. |
| lawrence3699/agent-skills-corpus | 4 | 2026-07-18 | Dataset | 55,698 public skills, deduped; usable for fixtures. |

Pattern: sync managers get the stars (7.7k, 1.1k) and ship no LLM features; eval/security/self-improving tools get attention but lack library-level management. No tool found combining sync, usage evidence, measured lift and reviewed apply.

## NEW vs known summary

NEW: skill-name telemetry masking; Codex 2% budget with measured truncation; delivered-vs-truncated descriptions; Cursor context breakdown; `claude plugin eval` baseline-arm design; Google and PayPal release-gate designs; routing-trace and manifest-field proposal; inconsistent disable-model-invocation semantics; project/tag-scoped sets (xingkongliang #40); receipts/pins/rollback with local edits preserved (opencode #65485); "not discovered" diagnosis (symlinks, nesting); 100-skill ceiling claim (provisional).
Known: Skills Janitor, #98220, sprawl audits, model-upgrade obsolescence, SWE-Skills-Bench, skill-creator 0% recall, SkillCat, skilljack-evals, Tessl, Cisco scanner.

## Feature ideas implied (for the maintainer's review; all are proposals)

1. **Delivered-description report per agent**: for each agent scope, show which skill descriptions fit in its budget (Codex 2%, Claude listing cap), which are truncated or dropped, by how many characters, and which are least-used. Deterministic first; AI only writes "shorten this description without losing triggers" as a reviewed diff. (Themes 2, 1)
2. **Observed-usage-first health view**: use transcript-derived invocation counts (since OTel names are masked) and label "unknown, not zero". Already F1; add the per-consumer note that telemetry may be unavailable. (1)
3. **Routing-trace explainer**: given a prompt, show which skills compete, the likely winner and rejected near-matches with reasons (extends "why didn't it run"); optionally a proposed `owns / does_not_own / hands_off_to` header written into a skill via reviewed edit. Marked as simulation. (6)
4. **Discovery diagnosis**: "why can't agent Y see skill X" checks symlink, depth, naming (e.g. uppercase/`Review-Code`), plugin namespace, disabled flag, per-agent semantics of `disable-model-invocation`. Mostly deterministic; AI explains. (3, 8, 9)
5. **Install/update receipts and pins**: record source, digest, target, local-edit flag; show update diff keeping local edits; one-click rollback. Fits existing source_lock and Recovery; the AI part is the semantic "what changed" (F13). (4)
6. **Project or tag-scoped sets**: "Frontend + common for this repo" as a reviewed batch preview; AI suggests which skills a project needs from its files (F11 variant), never applies silently. (8)
7. **Release gate pack (local analogue of Google/PayPal)**: before a skill change is accepted, run deterministic gates first (structure, secrets, link check, name rules), then optional LLM review, then measured with/without eval with k runs; output a one-page report to attach to a PR. Export only; no hosted service. (5, 7)
8. **Team bundle review**: export a reviewed, hash-pinned bundle for a team repo with owner, version, dependency list (Anthropic's registry record fields); import verifies digest. Keeps the "no hosted registry" boundary. (7, 4)
9. **Judge and baseline conventions**: show per-arm token counts, judge model, runs, flat/improved/regressed counts (matches `claude plugin eval` and the HN asks for tokens per arm). Strengthens F3. (5)
10. **Unify guidance files**: classify each AGENTS.md/CLAUDE.md section, rule, command as "always-on" vs "skill" with a converted draft (F12), because users cannot choose (15.6k-view thread). (10)
11. **Test corpus**: use lawrence3699/agent-skills-corpus (55,698 skills) as an offline fixture for overlap, truncation and 10,000-skill scale checks in slice 2. (5, 6)

Risks to keep: LLM-only security verdicts (scanner evasion write-ups, "word lists lose"); vendor-measured lift figures; tweet-sourced paper claims. Prefer evidence labels and "unknown".
