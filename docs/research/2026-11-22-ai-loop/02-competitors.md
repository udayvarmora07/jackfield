# AI features in skill / rule / prompt tooling: competitor scan (2026-11-22)

Method: WebSearch, WebFetch, `gh api` READMEs and issue lists. Read-only, nothing installed or signed up for. Fetched text was treated as untrusted data. Many search results were mirrors or blog posts, so anything not read from a primary page is marked [?].

Legend: Y = ships, p = partial or via a bundled skill/agent, - = not seen, ? = could not verify.

## 1. Feature x product matrix

Columns: Cr-B create from brief, Cr-X create from example/transcript/demo, Cr-C create from codebase, Edit inline AI edit, Diff review before apply, TestG test/eval generation, Eval run/score, Opt optimization loop, Sec security review, Disc recommendation/discovery, Upd auto-update, Port translation/porting, Docs doc generation, Ana analytics, Team team review/governance.

| Product | Cr-B | Cr-X | Cr-C | Edit | Diff | TestG | Eval | Opt | Sec | Disc | Upd | Port | Docs | Ana | Team |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic skill-creator + Claude.ai "Create with Claude" | Y | p (from convo) | - | Y | p | Y | Y (with vs baseline, variance, viewer) | Y (description improver) | - | - | - | - | - | Y (benchmark) | - |
| ChatGPT Skills / Codex $skill-creator / Record & Replay | Y | Y (screen demo) | - | p | - | - | - | - | Y (upload scan: Needs Review/Blocked) | p | - | Y (Agent Skills portable) | - | Y (admin usage) | Y (share, admin) |
| Cursor (/create-rule, /create-skill, /migrate-to-skills) | Y | p | - | - | - | - | - | - | - | - | - | Y (rules to skills) | - | - | - |
| GitHub Copilot (/init, coding agent writes instructions) | Y | - | Y | - | p (PR) | - | - | - | - | - | - | - | - | - | p |
| Kiro (Generate Steering Docs, Skills, Powers) | - | - | Y | - | - | - | - | - | - | p (Powers) | - | - | Y | - | - |
| Cline (/newrule, Memory Bank) | Y | Y (from conversation) | p | - | - | - | - | - | - | - | - | - | - | - | - |
| Windsurf (auto Memories, rules, skills) | p | Y (auto memories) | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Warp (/init, /add-rule, Drive) | Y | - | Y | - | - | - | - | - | - | - | - | - | - | - | Y (Drive) |
| Continue (Hub rules, `.continue/checks`) | p | - | - | - | Y (check returns suggested diff) | - | Y (checks as PR status) | - | - | p (Hub) | - | - | - | - | Y |
| Raycast (AI Commands, Agents, Skills) | - | - | - | - | - | - | - | - | - | - | - | - | - | - | p |
| Gemini CLI skills | p | - | - | - | - | - | - | - | p (consent prompt on activation) | - | - | - | - | - | - |
| uberSKILLS | Y | - | - | Y | - | Y (sandbox) | p (multi-model run + metrics) | - | - | - | - | p (deploy to 8 tools) | - | p | - |
| SkillCat (Konata9) | - | - | - | - | p (read-only before/after) | - | Y (A-D scoring, pair judge) | p | Y (rules) | Y (skills.sh) | Y | - | - | Y (runtime firing log) | - |
| Skiller (beautyfree) | - | - | - | - | - | - | - | - | - | Y | p | - | - | - | - |
| Agent Skills Manager (umutbozdag) | - | - | - | - | - | - | - | - | - | p | - | - | - | - | - |
| Skill Dock, AgentSkillsManager (VS Code) | - | - | - | - | - | - | - | - | - | Y | - | - | - | - | - |
| grimoire (kraitsura) | - | - | - | - | - | - | Y (prompt tests, A/B, cost estimate) | - | - | - | - | - | - | - | - |
| vercel-labs/skills CLI + skills.sh | - | - | - | - | - | - | - | - | Y (3 audits shown pre-install) | Y (find, leaderboard) | Y (check, update, lock) | Y (many agents) | - | Y (telemetry) | - |
| skillsmp | - | - | - | - | - | - | - | - | - | Y (search) | - | - | - | - | - |
| Tessl (registry, `skill review`, skill-optimizer) | Y (generates eval scenarios) | - | - | - | Y (before/after score) | Y | Y (with vs without skill) | Y | Y (Snyk score) | Y | Y | - | - | p | Y (governance) |
| Microsoft APM | - | - | - | - | - | - | - | - | Y (hidden-Unicode scan, policy) | p | Y (lockfile) | Y (per-harness output) | - | - | Y (org policy, audit --ci) |
| Cisco skill-scanner | - | - | - | - | - | - | Y (measured recall/FPR) | - | Y (static, dataflow, LLM judge, meta) | - | - | - | - | - | p (SARIF, CI) |
| NVIDIA SkillSpector | - | - | - | - | - | - | - | - | Y (71 patterns, LLM optional) | - | - | - | - | - | Y (signed catalog) |
| Snyk agent-scan | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | Y (Evo platform) |
| skilljack-evals | - | - | - | - | - | p | Y (k trials, skill lift, anti-trigger) | Y (authoring loop) | - | - | - | - | - | Y | Y (CI gate) |
| claude-code-templates / aitmpl | - | - | - | - | p (preview files before install) | - | - | - | p (SkillSpector on PRs) | Y | p (stale-upstream issues) | - | - | Y (`--analytics`) | - |
| Promptfoo | p | - | - | - | - | Y | Y | - | Y (red team) | - | - | - | - | - | Y |
| LangSmith (Polly/Chat, Hub) | Y | - | - | Y | p | Y | Y | Y | - | Y (Hub) | - | - | - | Y | Y |
| PromptLayer | - | - | - | p | Y (diffs) | p | Y | - | - | - | - | - | - | Y | Y |
| Langfuse | - | - | - | - | p | - | Y (LLM-judge, experiments) | - | - | - | - | - | - | Y | Y |
| Humanloop | defunct (shut down 2025-09-08) | | | | | | | | | | | | | | |
| GEPA / DSPy | - | - | - | - | - | - | Y | Y (reflective evolution) | - | - | - | - | - | - | - |
| Smithery / official MCP registry | - | - | - | - | - | - | - | - | Y (MCP-Scan on listing [?]) | Y | p | - | - | - | - |

## 2. Per-product notes

### Authoring tools with first-party AI

**Anthropic skill-creator** (`anthropics/skills`, `skills/skill-creator`). Verified from the SKILL.md. It interviews the user, drafts SKILL.md, then writes `evals/evals.json`. It spawns paired with-skill and baseline subagent runs per case, and the baseline is the old snapshot when improving a skill. Assertions are graded by a grader agent (`agents/grader.md`) into `grading.json`. `aggregate_benchmark` produces mean +/- stddev and deltas. An analyst pass flags non-discriminating assertions and flaky evals. A browser `eval-viewer` shows outputs and metrics. A separate script optimizes the description for trigger accuracy. It tells authors to make descriptions "pushy" because Claude undertriggers. UX is agentic and conversational. There is no preview of what is written beyond the viewer. Cost is your Claude usage. Claude.ai "Create with Claude" opens a chat with a pre-filled prompt and packages a skill file (https://support.claude.com/en/articles/12599426-how-to-create-a-skill-with-claude-through-conversation). Sources: https://github.com/anthropics/skills, https://tessl.io/registry/skills/github/anthropics/skills/skill-creator.

**ChatGPT Skills, Codex `$skill-creator`, Record & Replay**. OpenAI help center plus Codex docs (read). Three creation routes: chat, a Skills editor, or file upload. `$skill-creator` asks what the skill does, when it should trigger and whether it needs scripts, and defaults to instruction-only. Record & Replay (macOS, Computer Use required, not in EEA, UK or CH at launch) watches a demo and drafts when-to-use, inputs, steps and verification (https://learn.chatgpt.com/docs/extend/record-and-replay). Uploads are scanned and can be marked "Needs Review" or "Blocked". Enterprise admins control upload, share and install, and can see owners and usage. `agents/openai.yaml` `allow_implicit_invocation: false` stops implicit use. The skill list gets about 2% of the context window by default. No built-in test tool and no review workflow were found. Sources: https://help.openai.com/en/articles/20001066-skills-in-chatgpt, https://learn.chatgpt.com/docs/build-skills.

**uberSKILLS** (https://github.com/uberskillsdev/uberskills, MIT, 21 stars, last push 2026-04). Local Next.js app with SQLite. Create from a plain-English description, structured editor with validation and auto-save, a multi-model test sandbox through OpenRouter (BYOK, key encrypted at rest) with streaming and metrics, version history with compare, one-click deploy to 8 agents, bulk import. It has no diff-reviewed AI edit, no trigger testing and no security scan [?]. Its fixed issues ("trigger field required blocks import of all Claude Code skills", Windows `spawn sh ENOENT`) show format-strictness and portability pain.

**SkillCat** (https://github.com/Konata9/skillcat, MIT, 3 stars, last push 2026-10-18). The closest peer to this manager. Desktop Electron app, macOS and Windows. Reads are local. Writes are delegated to the official `skills` CLI. AI is optional and BYOK, with presets for Claude, ChatGPT, Gemini, DeepSeek, Qwen, GLM, Kimi, MiniMax and Ollama (local, no key). Features: per-skill A-D scoring in batches of up to 6 skills (about 12k chars per batch); pair judge for duplicate/conflict candidates (pre-filtered by trigger overlap >= 0.2 or body similarity >= 0.15, max 24 pairs) with verdicts confirmed / false-positive / uncertain; read-only before/after rewrite suggestions grounded in a bundled `skill-optimizer` rubric; trigger profiling with manual sidecar annotations that do not touch skill files; an optional agent bridge (OpenCode only) that logs which skills actually fire and the trigger phrase; skills.sh leaderboard and search; evaluation staleness via a signature of model + per-skill content hash; JSON repair for truncated model output; a "Test connection" max_tokens=1 ping. Docs are in Chinese (docs/ai-evaluation.md). No apply path for AI suggestions (read-only by design).

**Skiller** (https://github.com/beautyfree/skiller, 57 stars). Desktop manager for 49 agents. Install once and propagate, per-agent copy or wipe, project-scoped skills, edit, browse skills.sh and ClawHub. No AI features in the README.

**Agent Skills Manager** (https://github.com/umutbozdag/agent-skills-manager, 44 stars). Dashboard across 11 tools (skills and rules): CodeMirror editor, enable/disable via `SKILL.md.disabled` (the same trick this manager uses), install from Git, a companion `manage-skills` skill. No AI features.

**Skill Dock** (https://github.com/yen0304/Skill-Dock, VS Code/Cursor). Library CRUD, marketplace from Anthropic/OpenAI/Copilot/HF/Vercel sources via the GitHub trees API (no clone), skills.sh search. No AI features.

**AgentSkillsManager** (https://github.com/lasoons/AgentSkillsManager, 90 stars). VS Code extension, 58k-skill cloud catalog from claude-plugins.dev. No AI features and no security checks described.

**grimoire** (https://github.com/kraitsura/grimoire, 4 stars). Versioned prompt store, skills injection, prompt tests across providers with cost estimates and A/B. Estimates cost before running, a pattern worth copying.

### Rule/instruction generators in agent IDEs

**Cursor**. `/create-rule`, `/create-skill`, and a built-in `/migrate-to-skills` (2.4+) that converts eligible dynamic rules and slash commands into skills. Manual guidance: ask the Agent to turn a rule into a skill, review, then delete the original. A 2.3.8 forum report says adding a rule produced a skill [?]. Sources: https://cursor.com/docs/skills, https://dev.to/sriram7/how-to-migrate-from-cursor-rules-to-agent-skills-1cl7.

**GitHub Copilot**. `/init` in VS Code Chat scans the workspace and writes `copilot-instructions.md`. The coding agent on github.com can generate it as a PR. Path-scoped `.instructions.md` with `applyTo`. Source: https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions.

**Kiro**. "Generate Steering Docs" (IDE only, not CLI) creates product.md, structure.md and tech.md from the codebase. Skills live in `.kiro/skills`. Powers bundle MCP, steering and hooks. Source: https://kiro.dev/docs/steering/.

**Cline**. `/newrule` writes a rule from your description or the conversation into `.clinerules/`. The Memory Bank is a set of project markdown files that Cline reads and updates. Skills in `.cline/skills/` [?]. Sources: https://docs.cline.bot/features/slash-commands/new-rule, https://docs.cline.bot/features/memory-bank.md.

**Windsurf (now under Devin docs)**. Cascade auto-generates Memories, stored locally in `~/.codeium/windsurf/memories`, workspace-scoped. For durability it recommends promoting a memory to a Rule or AGENTS.md. Skills are SKILL.md in `.windsurf/skills`. Source: https://docs.windsurf.com/windsurf/cascade/memories.md.

**Warp**. Rules via `/add-rule` (global) and `/init` (project AGENTS.md, older WARP.md). Skills in `.agents/skills`. Prompts are parameterized and run from the command palette. Warp Drive syncs rules and prompts for teams, but skills are files, not synced. Source: https://docs.warp.dev/agents/capabilities/rules/.

**Continue**. Hub rule blocks, local `.continue/rules`, and `.continue/checks/*.md`: markdown agents that run on each PR as GitHub status checks and return green or red with a suggested diff. This is "evals as PR status" for rules. Source: https://docs.continue.dev/mission-control/beyond-checks.

**Raycast**. AI Commands (single-shot prompts), Agents (formerly Presets), and Skills that scan `~/.claude/skills` and `~/.config/raycast/skills` and pull in relevant ones. AI Commands cannot use skills. No generator found. Source: https://manual.raycast.com/ai/skills.

**Gemini CLI**. `gemini skills install <git|dir> --scope`, `--consent` to skip the security confirmation, `/skills link`, enable/disable, reload. On activation the user sees a consent prompt with the skill name, purpose and directory. Source: https://geminicli.com/docs/cli/skills/.

### Registries, package managers, scanners

**vercel-labs/skills + skills.sh** (https://github.com/vercel-labs/skills, 40k stars, 795 open issues, active 2026-11-17). `find`, `add`, `check`, `update`, `skills-lock.json` v2 with per-skill `computedHash` and git commit pinning, `--frozen-lockfile`. skills.sh runs three audits per skill (Gen Agent Trust Hub, Socket, Snyk; Pass/Warn/Fail) and `skills@1.4.0+` shows them before install (https://vercel.com/changelog/automated-security-audits-now-available-for-skills-sh). Complaints visible in issues: lock written concurrently loses entries, symlinked lock replaced by a regular file, test fixtures publicly installable, stale audits after content refresh ("Re-audit request"), many delist requests for removed skills. Telemetry is on unless disabled.

**skillsmp** (https://skillsmp.com/about). Search over about 21k-800k+ indexed public SKILL.md files, with claims varying by source [?]. Critics say there is no quality filter beyond star counts. Third-party pages report Fail or medium-risk audits for some of its own listed skills.

**Tessl** (https://tessl.io/registry, https://docs.tessl.io/). Registry with `tessl skill review` (scores Completeness, Actionability, Conciseness, Robustness; before/after report), eval scenarios run with and without the skill, a `skill-optimizer` tile that reviews, generates scenarios, runs evals, compares models, diagnoses and re-runs until scores improve, Snyk security scoring, a governance layer, and a Tessl Agent in open beta. The optimizer's own registry page shows only about 1.14x average on its evals, so modest gains. Pricing not found [?].

**Microsoft APM** (https://github.com/microsoft/apm, 4.4k stars, 202 open issues). `apm.yml` plus `apm.lock.yaml` (commit + SHA-256 per file), `apm install --frozen`, `apm audit` for drift and `apm audit --ci`, hidden-Unicode scanning on every install that blocks critical findings (intent is not analyzed), CycloneDX/SPDX export, `apm-policy.yml` org allow-lists (warn first, then block), per-harness compilation. No generative AI. Open issues show real-world friction: uninstall removes an instruction another bundle still owns, `pack` silently drops root skills, a failed install still changes the lockfile.

**Cisco skill-scanner** (https://github.com/cisco-ai-defense/skill-scanner, 2.7k stars). YARA and YAML patterns, AST and dataflow, optional LLM judge, optional meta-analyzer second pass, a CEL decision layer, presets (`balanced`, `low-noise`, `quiet`) with published recall/FPR/F1 (LLM judge about 66.7% recall at 15.4% FPR; rules alone about 8% recall), SARIF, GitHub Action, pre-commit hook, local-model and Bedrock options, with the claim "Nothing leaves the machine" when the judge is local. Issues: CJK text flagged as "vague", an `--adjudicate` verdict cut off at the 200-token cap when a thinking model is used (relevant to this manager's token caps), the Windows exe is unsigned.

**NVIDIA SkillSpector** (https://github.com/NVIDIA/SkillSpector, 27k stars). 71 patterns in 17 categories, static plus optional LLM (`--no-llm`), OSV.dev live CVE lookups, SARIF, Docker, OpenCode and Pi extensions, fail-closed resource bounds, part of a signed "NVIDIA Verified Skills" pipeline. Cites research that 26.1% of 31k skills contain a vulnerability.

**Snyk agent-scan** (https://github.com/snyk/agent-scan, 3.3k stars). Auto-discovers agents, MCP servers and skills on the machine and scans them. Output is explicitly experimental. Whether skill content is sent to Snyk services [?], so verify before recommending.

**skilljack-evals** (https://github.com/olaservo/skilljack-evals, 8 stars). Task packages with deterministic verifiers, a paired no-skill baseline, k trials per condition, skill-lift thresholds, anti-trigger tasks (`expect_skill_invocation: false`), an oracle gate in `validate`, free "lite" checks, result caching, opt-in LLM-judge diagnostics that never gate the result, and CI mode with `summary.json`. Runners: Claude Agent SDK, Claude Code, Codex.

**claude-code-templates / aitmpl** (https://github.com/davila7/claude-code-templates, 34k stars, 551 open issues). Registry and CLI for agents, commands, skills, hooks, MCP. Previews each file a component writes before install, merges config instead of overwriting, has `--analytics` (local dashboard on :3333) and `--health-check`, and runs SkillSpector on contributions. Bot-style issues like "External skills have newer upstream commits" show auto drift detection.

**Smithery and MCP registries**. Smithery lists servers scanned by Invariant's MCP-Scan (per Invariant's own announcement [?]). The official MCP registry is a preview metadata layer that downstream marketplaces consume. Sources: https://invariantlabs.ai/blog/smithery-mcp-scan, https://modelcontextprotocol.io/registry/about.

### Prompt-ops platforms (adjacent)

**Promptfoo** (https://github.com/promptfoo/promptfoo). Open source evals and red teaming in CI. OpenAI announced acquiring it on 2026-03-09 and said open source continues. Pricing not verified.

**LangSmith**. Polly (now "Chat" in some docs) edits prompts in the Playground from instructions, explains shared Hub prompts, generates tools and output schemas. Public Hub prompts are unverified. Source: https://docs.langchain.com/langsmith/polly.

**PromptLayer**. Immutable versions with commit messages and diffs, labels like "production" without redeploy, a visual CMS for non-engineers, evals that auto-run on each new version. Pricing: Free, Pro $49/mo, Team $500/mo. Competitor-written comparisons say it lacks CI-gating enforcement [?]. Source: https://promptlayer.com/pricing.

**Langfuse**. Prompt versions and labels, side-by-side Playground, prompt experiments on datasets, LLM-as-judge evaluators (numeric, boolean and categorical scores, versioned via API), and a May 2026 "calibration skill" reporting judge accuracy, F1, precision, recall and cost. Source: https://langfuse.com/blog/2026-05-31-langfuse-may-update.

**Humanloop**. Shut down 2025-09-08 after Anthropic hired its team. A cautionary tale about depending on a hosted prompt-management vendor. Source: https://techcrunch.com/2025/08/13/anthropic-nabs-humanloop-team-as-competition-for-enterprise-ai-talent-heats-up.

**GEPA / DSPy** (https://github.com/gepa-ai/gepa). `optimize_anything` evolves any text artifact from a score plus diagnostic side information. GEPA ships as an Agent Skill and plugin for Claude Code. "gskill" evolves per-repo skills using SWE-smith generated tasks. An arXiv paper (2610.37201) critiques generalist skill optimizers [?].

## 3. Reported pain points (primary evidence where cited)

- Skills not triggering because of the shared description budget (about 15k chars by default on Claude Code 2.0.70, descriptions silently dropped, least-used first). Sources: https://blog.fsck.com/2025/12/17/claude-code-skills-not-triggering, https://dev.to/rulestack/too-many-claude-code-skills-how-the-listing-budget-decides-which-descriptions-claude-sees-4a6m. This manager already has a listing-budget fitter and a why-didn't-it-run diagnosis.
- Registry quality and trust: no quality filter at skillsmp; stale audits and delisting churn at skills.sh; 26.1% vulnerability rate cited by Cisco and NVIDIA.
- Scanner false positives and truncation (Cisco CJK and 200-token verdict issues); Snyk marks its output experimental.
- Concurrency and lockfile bugs in both vercel-labs/skills and APM.
- Vendor risk (Humanloop) pushes people toward local, filesystem-first tools.
- uberSKILLS author describes manual SKILL.md management as painful (https://hackernoon.com/lite/i-built-a-visual-workbench-because-managing-claude-code-skills-was-driving-me-crazy). This is a vendor/author blog, not an independent review.
- No independent user reviews or app-store style ratings were found for any desktop skills manager.

## 4. Trust and safety patterns seen

- Read-only suggestions (SkillCat), before/after score (Tessl), suggested-diff checks (Continue).
- Consent prompt per activation (Gemini CLI), per-file install preview (aitmpl), `--consent` flag to skip.
- Pre-install audit badges (skills.sh), upload scan with Needs Review / Blocked (ChatGPT).
- Warn-then-block policy rollout (APM), measured precision/recall presets (Cisco), fail-closed resource bounds (SkillSpector).
- Local-model option so nothing leaves the machine (Cisco, SkillCat via Ollama).
- LLM judge never gates results (skilljack-evals) so an unreliable judge cannot block a pipeline.
- Staleness signature on saved AI results (SkillCat: model + content hash).

## 5. Features others ship that this manager does not yet have

The manager already has: BYOK with token caps, trigger simulation, verified description rewrite, overlap judge, listing-budget fitter, install/update review briefing, finding explainer, regression prompt packs, with/without-skill evals, ask-your-library, porting notes, draft from brief, project profile suggestions, conciseness splitter, CI trigger mode, AI edit with reviewed diff and snapshot, current-vs-proposed comparison incl. second model, why-didn't-it-run diagnosis, sync-diff explanations. Where I could not tell whether it has a feature, it is marked [?].

Ranked by fit with a local, filesystem-first, review-before-apply manager:

1. **Draft from a transcript or session log.** Codex Record & Replay drafts from a screen demo; Cline `/newrule` and Windsurf Memories derive rules from conversations. A local equivalent: propose a skill from a pasted or selected Claude Code / Codex session transcript or repeated corrections, shown as a reviewed diff. Needs a redaction preview because transcripts hold secrets.
2. **Draft from the codebase (steering generation).** Kiro, Copilot `/init` and Warp `/init` generate project instructions from the repo. The manager has "project profile suggestions" [?: whether it can generate an AGENTS.md/CLAUDE.md draft from the profile].
3. **Variance-aware benchmarking.** Anthropic skill-creator and skilljack-evals run k trials per condition and report mean +/- stddev, skill lift and thresholds. A single with/without run can mislead [?: whether the manager runs repeated trials].
4. **Eval-quality analysis.** Anthropic's analyst pass flags non-discriminating assertions and flaky evals; skilljack has an oracle gate and anti-trigger tasks; Langfuse reports judge calibration (accuracy, F1). A "judge agreement with my labels" check would give the existing LLM judges a measured trust signal.
5. **Closed optimization loop with held-out cases.** Tessl skill-optimizer, GEPA/gskill, Anthropic's description improver (train/test split) iterate until a score improves. The manager's rewrite is verified once [?: whether it iterates]. A bounded loop with a spend cap, a held-out set, and a stop rule would be the natural extension. Tessl's own average gain (about 1.14x) suggests setting modest expectations.
6. **Multi-model test matrix.** uberSKILLS and Tessl compare one skill across several models. The manager compares current vs proposed with a second model, but a per-model grid of the same skill (cost, pass rate) is a different view [?].
7. **Real activation telemetry.** SkillCat's agent bridge logs which skills actually fired and the trigger phrase; aitmpl has analytics. The manager simulates triggers and diagnoses misses, but observed fire rates from real sessions [?] would close the loop. Read local transcript files rather than installing a bridge.
8. **Hybrid security scanning with measured presets.** Cisco and SkillSpector combine static rules, dataflow and an LLM judge, publish recall/FPR, and emit SARIF. APM scans hidden Unicode. The manager has a finding explainer and an install review briefing [?: which deterministic checks exist]. Candidates: hidden-Unicode and bidi detection, SARIF export for CI, a local-model-only judge mode, optional OSV lookups for bundled scripts, and a "scan before adopt" gate. Beware CJK false positives and verdict truncation under token caps.
9. **Lockfile with per-file hashes, frozen restore, drift audit, SBOM.** vercel-labs/skills and APM both do this. Relevant to the manager's sync and update flow [?: its current integrity model].
10. **Org policy and team governance.** APM `apm-policy.yml` (warn then block), ChatGPT admin share/upload/install controls with "Needs Review" states, Continue checks as PR gates. For a single-user local tool this is lower priority, but a shareable policy file plus a CI check is cheap.
11. **Cross-format conversion beyond notes.** Cursor `/migrate-to-skills` and APM per-harness compilation actually write the target format. The manager has porting notes; an applied conversion of rules, commands or Copilot instructions into SKILL.md with a reviewed diff is a gap [?].
12. **Remote discovery with AI ranking.** skills.sh leaderboards, `find-skills`, SkillCat's remote search, and 58k-skill catalogs exist, and Tessl scores listings. The manager's recommendation is project-profile based [?: whether it searches remote registries]. If added, show audit status and require the install review briefing before anything lands.
13. **Per-skill quality grade and batch scoring with staleness.** SkillCat grades every skill A-D, and Tessl scores four dimensions. A cached library-wide scorecard, invalidated by a model + content-hash signature, would make the ask-your-library view actionable.
14. **Sidecar annotations.** SkillCat lets you annotate trigger profiles without touching skill files. Useful for a filesystem-source-of-truth design.
15. **Pre-run cost estimate.** grimoire estimates cost before testing. The manager has token caps; a pre-flight estimate with the redaction/what-is-sent preview is a cheap trust feature.
16. **Invocation-policy suggestions.** Codex `allow_implicit_invocation: false` and Claude Code `skillOverrides` name-only mode are levers the listing-budget fitter could recommend and apply per agent [?: which it already uses].
17. **Eval datasets generated from the skill.** Tessl generates eval scenarios from a skill. The manager has regression prompt packs [?: whether generation covers negative/anti-trigger cases].
18. **Prompt labels ("production") on versions.** PromptLayer labels a version without redeploy. The manager has snapshots; named release labels per skill are a possible gap [?].

Not worth copying for this product: hosted registries and accounts (Humanloop shutdown risk), screen recording (platform-specific and privacy-heavy), red-teaming (Promptfoo scope is LLM apps, not skills).

## 6. Caveats

- Several facts come from search snippets or vendor-written comparisons: PromptLayer vs Braintrust claims, Snyk agent-scan data handling, skillsmp catalog size, Tessl pricing, Smithery scan coverage, Cline `.cline/skills`. All are marked [?].
- GitHub star counts and issue counts are as of 2026-11-22 from `gh api`.
- No user-review sites (G2, app stores) were found for the desktop skills managers. Praise and complaints come from issues and blog posts only.
