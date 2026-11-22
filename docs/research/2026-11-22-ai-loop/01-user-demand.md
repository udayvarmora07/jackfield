# Demand research: AI-assisted skill management (as of 2026-11-22)

Method: gh issue search (anthropics/claude-code, anthropics/skills, openai/codex, anomalyco/opencode, google-gemini/gemini-cli, vercel-labs/skills), HN Algolia, web search, selected page fetches. Reddit threads were NOT directly retrievable (search returned blogs, not threads); Reddit-sourced claims are marked [?].
Caveat on the corpus: GitHub issue reaction counts for skill topics are LOW everywhere (single digits to ~11). Demand is visible mostly as blogs, Show HNs, Product Hunt and tooling, not as upvoted issues. Strength labels reflect that.

## Ranked demand themes

### 1. Skill-library hygiene: usage visibility, dead-skill detection, de-dup, context cost  — strong — mostly NEW as an *analytics/retire* theme (overlap/budget already known)
- Product Hunt "Skills Janitor" (launched 2026-04-13, 234 points): maker actively used 4 of 35 skills, 8 near-duplicate pairs; commenters asked for overlap %, pre-install "do I already have this" check, scheduled auto-clean, reading local logs for usage. https://www.producthunt.com/products/skills-janitor
- Cursor forum, "Skills adoption analytics endpoint" (2026-02-12, ~4 replies): teams "have no visibility" whether custom skills are used; want invocation source (slash/auto/MCP). Replies say skill-use events are hard to emit reliably. https://forum.cursor.com/t/feature-request-skills-adoption-analytics-endpoint/151688
- Cursor forum (2026-01-23): users cannot see which skill ran; the "Explored..." line collapses; asks for per-response skill summary. https://forum.cursor.com/t/visibility-of-agent-skills-usage-execution-logs-in-chat-context/149685
- dev.to "15 days of skill sprawl" (2026-02, edited 07-01): 33 skills disabled with disable-model-invocation; learned skills regrew 14 to 40 within days; author judged no existing audit tool ready, manual audit best. https://dev.to/shimo4228/15-days-of-skill-sprawl-in-claude-code-lessons-from-3-audits-27em
- vercel-labs/skills #2499 (2026-10-14, +2): users installing big collections want to flip third-party skills to slash-only without hand-editing; 'skills add' flag requested. https://github.com/vercel-labs/skills/issues/2499
- claude-code #98220 (2026-09-29, +11, highest reactions of any skill request found): can't disable single skills inside a plugin (e.g. aws-core ships 19); only whole-plugin disable. https://github.com/anthropics/claude-code/issues/98220
- Gemini CLI #30155 (2026-11-05): add skill_name to telemetry (usage measurement). https://github.com/google-gemini/gemini-cli/issues/30155
Ask: AI proposes "keep / slash-only / merge / retire" per skill, grounded in real invocation logs, with undo.

### 2. Staleness after MODEL upgrades (re-tune skills for new model) — strong — NEW
- dev.to (June 2026): 13 of 31 production skills flagged after Claude Fable 5 release for over-prescriptive MUST/NEVER, numbered procedures; one instruction silently triggered a costlier fallback; degradation is silent; author sells a scanner with a --fix-with-claude rewrite. https://dev.to/whoffagents/claude-fable-5-dropped-this-morning-by-noon-13-of-my-31-production-skills-were-quietly-obsolete-2bkl
- Substack (2026-08-06): skills written for older models hurt on Opus 5/Sonnet 5/Fable 5; advice: shorten, drop scaffolding, A/B old vs rewritten in fresh sessions. https://aiblewmymind.substack.com/p/fix-claude-skills-opus-5-sonnet-5-fable-5
- philippdubach.com (2026-11-07), HN 8 pts: deleted all skills; cites SWE-Skills-Bench (most public skills no significant effect; token overhead up to +451%), SkillsBench counter-evidence (curated +16pp). https://philippdubach.com/posts/i-just-deleted-all-my-agent-skills/ , https://arxiv.org/abs/2603.15401
- HN "Ask HN: How do you evaluate the skills your AI agents use?" (2026-11-09, 26 pts, 8 comments): answers = with/without runs on own prompts; agent self-eval. https://news.ycombinator.com/item?id=50426070
Ask: "does this skill still earn its tokens on model X?" (with/without A/B, cost delta) and a lean-rewrite proposal. Overlaps known "eval with/without" but the model-upgrade trigger and "retire it" outcome are new.

### 3. Skills from experience: session transcript / git history / correction → skill, and agent self-improvement — strong supply, mixed demand — NEW (partially)
- Many community tools exist: skillify (kk-r), skilldistill (PyPI), extract-skill-from-conversation, distill-skill, improve-skill, dev.to "generate Claude Code skills from your git history". https://github.com/kk-r/skillify-skill , https://pypi.org/project/skilldistill/0.1.0/ , https://dev.to/ohugonnot/generate-claude-code-skills-from-your-git-history-2lna
- Self-improvement skills log corrections then promote to CLAUDE.md/skill, with explicit user approval as a common design (pskoett, trtmn). https://skills.sh/trtmn/agent-skills/self-improvement
- WARNING evidence: continuous-learning pipeline recorded 10,557 observations, produced 0 skills (shimo4228, link in theme 1). SkillsBench: self-generated skills give negligible/negative benefit; ETH-Zurich-cited claim that LLM-generated context files cut success ~3% and raised cost >20% [?, secondary source]. https://arxiv.org/html/2602.12670v1
- Microsoft SkillOpt, HN 49836602 (2026-09-24, 11 pts): training loop to optimize skills; commenters skeptical of unmeasured gains. https://news.ycombinator.com/item?id=49836602
Ask: draft-from-transcript is wanted, but only with human review plus measured benefit; unreviewed auto-promotion is distrusted.

### 4. Install-time fit: "do I already have this / what should I install for THIS project / who wins on conflict" — moderate — partially known (third-party review known); recommendation/precheck NEW
- Skills Janitor comments (above): precheck before install.
- Marketplace scale: SkillsMP 364k+, skills.sh 100k+ skills, mixed quality [vendor blog]; HN "Craigslist for agent skills" (2026-09-17, 28 pts, 18 comments) top replies: "why buy a markdown file when my LLM can draft one" -> demand for project-specific generation over catalog browsing. https://news.ycombinator.com/item?id=49743459
- vercel-labs/skills #2355 (2026-10-01): a user's `skills add --all -y` put 37 skills in a random project dir; wants scope/link-mode/target always prompted. https://github.com/vercel-labs/skills/issues/2355
- No tool found that reads a project's stack and recommends skills. [?] only one search.

### 5. Updates, versioning, provenance, rug-pull diffs — moderate — partly known (updates overwriting local changes, explaining sync diffs); changelog/provenance/semantic-diff NEW
- vercel-labs/skills #2678 (2026-11-05) update all from a source; #2227 (2026-09-13, 3 comments) update skips when multiple paths match; #2406 same-skill-under-many-agent-folders always ambiguous; #2323 RFC (2026-09-28) install skills shipped in npm packages so skill updates with library. https://github.com/vercel-labs/skills/issues/2323
- Show HN ClawVet (2026-11-21, 8 pts): offline AST scanner and "rug-pull diff" for skills. https://news.ycombinator.com/item?id=50587571
- dev.to "skills have a version control problem" (2026-03/04): can't tell which copy is current across chat uploads, Codex, Obsidian; frontmatter differences between platforms. https://dev.to/snapsynapse/your-ai-agent-skills-have-a-version-control-problem-5g1g
- Dependencies between skills: no native field; third-party `depends` convention only. Demand evidence weak. [?]

### 6. Cross-surface sync: account skills vs local, Cowork/desktop, web — moderate — NEW (sync of authoring, not porting)
- claude-code #93163 (2026-09-09, +8): no programmatic upload to claude.ai; Cowork re-zip every change. https://github.com/anthropics/claude-code/issues/93163
- claude-code #96397 (2026-09-23): account skills read-only outside claude.ai; edits to synced copies not saved. https://github.com/anthropics/claude-code/issues/96397
- claude-code #107421 (2026-11-05, closed): load from ~/.agents/skills. https://github.com/anthropics/claude-code/issues/107421
- opencode #50638 (2026-09-22, +7): desktop slash list doesn't show skills. https://github.com/anomalyco/opencode/issues/50638
Ask for AI: "tell me where this skill is, which copy is live, and push it".

### 7. Authoring-tool reliability: creator/eval tooling itself is mistrusted — moderate — NEW (affects AI-feature design)
- anthropics/skills #1721 (2026-09-03): skill-creator trigger eval reports 0% recall for every skill and "optimizes" anyway; silent. #1706: parallel eval workers share one commands dir, corrupting rates. #2220 (2026-11-14): skill-creator SKILL.md is 33 KB, risks truncation. #1982: eval viewer script-injection risk. https://github.com/anthropics/skills/issues/1721 , /1706 , /2220 , /1982
- HN Show HN linter (2026-09-17, 3 pts): 69% of 216 public skills "won't reliably trigger"; 57% of subagents declare no tools. https://news.ycombinator.com/item?id=49744398
Lesson: an AI optimizer that reports success from a broken measurement is the known failure; show raw evidence.

### 8. Convert between artifact types (command/subagent/skill/CLAUDE.md/AGENTS.md) — weak/moderate — NEW
- Only community converters found: migrate-to-skills, claude-command-converter, CLAUDE.md→AGENTS.md skill, Claude→Codex config. Commands merged into skills (command→skill = disable-model-invocation; subagent→skill = context: fork) [secondary source]. https://skills.sh/carsten-j/agent-resources/migrate-to-skills
- No issue with reactions found. No MCP→skill conversion demand found.

### 9. Team sharing, review, approval — moderate (enterprise), weak (individual dev) — partly known
- Anthropic enterprise guide: security review checklist, eval suite before approval, author != reviewer. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise
- Vendor/security blogs on inventory, owner, approval status (nhimg, Backslash, Aurascape; PayPal "agent skills at enterprise scale"). Vendor-driven [?]; low grassroots signal.
- HN Show HN "Skills Hub desktop app" (2026-10-12, 10 pts) and "Skillset" (11-15) show manager-app interest but little discussion.

### 10. Scripts inside skills — weak
- Only guidance (PEP 723 / uv run; "add script when you see the agent rebuild the same step"). No complaints or requests about generating/testing helper scripts found; CI testing of skill scripts not covered by anything found. https://agentskills.io/skill-creation/using-scripts

### 11. Cost/privacy/local-model preference for AI features — weak, but implicit
- Token cost is a major driver of themes 1-2. No explicit demand for "local model for skill management" found; offline-first scanners (lintai) and a skill that claimed offline but fell back to remote show privacy claims get audited. [?]
- Anthropic usage-limit complaints (claude-code #105125, 2026-10-26, +5 reactions) suggest users are sensitive to extra token spend [not skill-specific].

### Not found / weak
- Localization, accessibility of skills: nothing.
- Natural-language bulk ops: only tools like skill-organizer / organize-skills (bulk rename, archive); no explicit requests.
- Hooks: raised as the deterministic alternative to skills that fire ~50-80% [secondary]; no manager-specific request.

## Gaps where people asked but no tool answers
1. Real per-skill invocation analytics across agents (Cursor requests; no cross-agent standard; Claude org endpoint is enterprise-only). Local-log readers exist but are partial.
2. A trustworthy "keep/retire/slash-only" decision grounded in measured benefit and cost on the current model (people hand-audit; sprawl regrows within days).
3. Plugin-level skill granularity: disable individual skills in a plugin (#98220).
4. Project-aware recommendation: stack -> skills to install, with duplicate precheck.
5. Authoring sync from local to claude.ai / Cowork and account skills edit-in-place (#93163, #96397).
6. Model-upgrade re-tuning: detect over-prescriptive skills and propose a leaner version verified against the old one.
7. Semantic diff / rug-pull review for upstream skill updates (only a Show HN scanner).
8. Safe auto-promotion of corrections to skills: pipelines produced zero skills in practice.
9. Testing a skill's bundled scripts in CI.

## Confidence notes
- Verified by fetch: Cursor forum threads, Skills Janitor PH page, HN threads, shimo4228, whoffagents, philippdubach, substack, GitHub issues. Reaction counts exact where stated (+N = GitHub reactions).
- Not verified: Reddit threads (none retrieved); "861 upvote" Reddit claim in one post [?]; ETH Zurich figures [?]; SWE-Skills-Bench 92/98 vs 39/49 version discrepancy [?]; Anthropic "plugin-evals" doc mentioned in HN comment [?].
- Several fetched posts have no year printed (dev.to Mar/Apr; whoffagents June): treated as 2026 on context.
