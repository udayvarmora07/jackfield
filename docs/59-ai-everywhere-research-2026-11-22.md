# AI Across Every Skills Manager Feature

**Version 0.1.1**

**AI manifest**: Second research pass of 2026-11-22. It looks for AI features
beyond those shipped through `4da3fb7`, which are listed in
@docs/39-ai-features-research-and-catalogue-2026-11-09.md and
@docs/58-ai-authoring-and-skill-lifecycle-research-2026-11-22.md. It maps every
product surface to its current and proposed AI support, then ranks the new
proposals. Everything here is a proposal until it ships. Items that need
maintainer approval under `AGENTS.md` are listed in their own section.

**[NOTE]**

## Recommendation

Skills Manager already covers authoring well. It can draft, make reviewed edits
to one exact copy, compare versions, diagnose why a skill did not run, and
explain sync differences. The new evidence points at what happens **after** a
skill exists. Libraries grow faster than anyone audits them. Skills quietly
stop paying for themselves when the model changes. Evaluation tooling reports
confident numbers from noisy or broken measurements.

Build these five next, in order:

1. **Library health and retire assistant.** For each skill, recommend keep,
   slash-only, merge or archive. Ground each recommendation in observed usage,
   listing cost, overlap and measured lift, and apply it through the existing
   batch preview.
2. **Model-upgrade recheck.** When the configured model changes, ask "does this
   skill still earn its tokens?" Rerun saved cases with and without the skill on
   the new model, flag over-prescriptive instructions, and offer a leaner
   rewrite through Edit with AI.
3. **Honest test statistics.** Run repeated trials in random order, report
   paired lift with a confidence interval, and label a result "inconclusive"
   when it is. Flag token regressions and assertions that never discriminate.
4. **Accept or reject each change, with AI provenance in Recovery.** Every AI
   proposal (edit, shorten, rewrite, port, merge) gets per-hunk accept and
   reject. Recovery labels the model, the request and the evidence run behind
   each applied change.
5. **Draft from real work.** Start a skill from a consented transcript excerpt,
   a git range or selected project files, behind a redaction preview. The draft
   stays unproven until its measured lift is positive.

These five reuse infrastructure that already exists: `usage` transcript
aggregates, `archive`, batch preview, regression packs, `ai_evals`, source-update
reviews and Recovery snapshots. Each adds a missing piece of evidence or
control rather than another model call.

## How this was researched

**[NOTE]** Four parallel passes ran on 2026-11-22, each writing a sourced
report. All fetched text was treated as data. Nothing was posted, installed or
logged into.

| Pass | Model | Coverage | Limits |
|---|---|---|---|
| User demand | Sonnet 5.5 | GitHub issues (claude-code, skills, codex, opencode, gemini-cli, vercel-labs/skills), HN, Cursor forum, Product Hunt, dev blogs | Reddit threads could not be retrieved. Reaction counts on skill issues are low everywhere (highest +11). |
| Competitors | Sonnet 5.5 | About 35 products: skill managers, registries, scanners, IDE rule generators, prompt-ops platforms | No independent user reviews of any desktop skills manager exist; praise and complaints come from issues and author blogs |
| Literature | Sonnet 5.5 | arXiv 2025–2026, engineering blogs, eval practitioners | Abstracts only, no full texts. Numbers marked [abstract] were not checked against the full paper. |
| UX patterns | Haiku 5.5 | Cursor, Zed, Linear, Copilot, Raycast, Apple Writing Tools, Shape of AI, Microsoft HAX | Several design-guideline pages did not load. Pattern names from them are secondhand. |

Each claim a pass could not confirm from a primary page is marked [?] below.
Its "missing" items were then checked against this repository. Usage
aggregates from transcripts (`usage`), hidden-Unicode detection (`risk.py`,
`hygiene.py`), the AI off switch (`provider: null`) and per-file source locks
(`source_lock.py`) already exist. They are treated as foundations, not gaps.

## What is new since the earlier passes

1. **Sprawl is the dominant complaint, and it comes back.**
   - Skills Janitor (Product Hunt, 234 points) found its maker used 4 of 35
     skills and had 8 near-duplicate pairs. Commenters asked for a precheck
     before install and for scheduled cleanup.
     [link](https://www.producthunt.com/products/skills-janitor)
   - One three-audit write-up saw learned skills regrow from 14 to 40 within
     days and concluded that no audit tool was ready.
     [link](https://dev.to/shimo4228/15-days-of-skill-sprawl-in-claude-code-lessons-from-3-audits-27em)
   - claude-code [#98220](https://github.com/anthropics/claude-code/issues/98220)
     (+11, the most-reacted skill request found) asks to disable single skills
     inside a plugin.
   - Cursor users report that they cannot see which skill ran.
     [link](https://forum.cursor.com/t/visibility-of-agent-skills-usage-execution-logs-in-chat-context/149685)
2. **Model upgrades silently make skills obsolete.**
   - One author flagged 13 of 31 production skills after a model release for
     over-prescriptive MUST and NEVER rules and rigid numbered procedures.
     [link](https://dev.to/whoffagents/claude-fable-5-dropped-this-morning-by-noon-13-of-my-31-production-skills-were-quietly-obsolete-2bkl)
   - "I just deleted all my agent skills" (2026-11-07) cites SWE-Skills-Bench:
     most public skills had no significant effect, and token overhead rose by up
     to 451%. [link](https://philippdubach.com/posts/i-just-deleted-all-my-agent-skills/),
     [paper](https://arxiv.org/abs/2603.15401)
3. **Evaluation tooling is mistrusted, with reason.**
   - skill-creator reports 0% trigger recall for every skill and "optimizes"
     anyway ([anthropics/skills#1721](https://github.com/anthropics/skills/issues/1721)).
   - A single-author preprint measured 13.6% pairwise LLM-judge flips on repeat
     and estimated about 11 trials for a stable verdict [abstract, provisional].
     [link](https://arxiv.org/abs/2606.13685)
   - ACES used 947 paired with/without runs and reported lift with confidence
     intervals; 72.8% of pairs were positive [abstract].
     [link](https://arxiv.org/abs/2608.20614)
4. **Grounding decides whether generated skills help.**
   - SkillsBench: skills a model writes without evidence add roughly nothing,
     against about +16pp for curated ones [abstract].
     [link](https://arxiv.org/abs/2602.12670)
   - Induction from real trajectories, with verification, helps a lot: Agent
     Skill Induction reports +23.5% on WebArena
     ([link](https://arxiv.org/abs/2504.06821)), and SkillAxe reports 16% to 52%
     on SpreadsheetBench ([link](https://arxiv.org/abs/2606.10546)) [abstract].
   - One unattended learning pipeline logged 10,557 observations and produced
     zero skills (sprawl write-up above).
5. **Descriptions alone are weak routing signals.** SkillRouter measured a 37
   to 44pp routing-accuracy loss across about 80K skills when the body was
   hidden [abstract]. Overlap and fit checks should read full text, not only
   descriptions. [link](https://arxiv.org/abs/2603.22455)
6. **Self-editing agents write unsafe skills.**
   - In "Practice Makes Unsafe", all 21 agent/method combinations wrote unsafe
     skills. Adding write-time and retrieval-time checks cut new-session harm
     from 21.3% to 4.0% [abstract].
     [link](https://arxiv.org/abs/2608.12851)
   - A scan of 31,132 skills found 26.1% vulnerable, and skills with scripts
     were 2.12x more likely to be [abstract].
     [link](https://arxiv.org/abs/2601.10338)
   - Static and LLM detectors overlap little [?].
7. **Closest peer products.**
   - [SkillCat](https://github.com/Konata9/skillcat) is a local, BYOK manager.
     It grades skills A–D, judges duplicates, logs real activations and makes
     read-only rewrite suggestions, but has no apply path.
   - [skilljack-evals](https://github.com/olaservo/skilljack-evals) runs k
     trials per condition with lift thresholds and a CI gate.
   - [Tessl](https://docs.tessl.io/) scores skills and runs an optimizer loop.
     Its own registry shows only about 1.14x average gain [?].
   - [Cisco skill-scanner](https://github.com/cisco-ai-defense/skill-scanner)
     publishes recall and false-positive presets. Its issue tracker shows CJK
     false positives and verdicts cut off at a 200-token cap.

## Coverage map: every surface

"Today" lists AI that exists now. "Proposed" refers to the numbered features in
the next section. Plain deterministic improvements are left out.

| Surface (CLI / v2) | AI today | Proposed |
|---|---|---|
| Home / Next up | None | F1 health summary card; F4 pending AI proposals |
| Skills list, search (`list`, `search`, `/skills`) | Ask your library (shortlist preview) | F9 natural-language filter and bulk command bar; F8 scorecard column |
| Skill reader (`view`) | Why didn't it run, porting notes, shorten, explain findings | F8 grade with evidence; F2 "still worth it on this model?" |
| Create (`create`, New skill) | Create with AI, trigger cases | F5 draft from transcript, git range or files; F12 convert a rule, command or AGENTS.md section |
| Edit (`edit`, editor) | Edit with AI on selection or whole body, reviewed apply | F4 per-hunk accept; F7 bounded optimize loop; frontmatter suggestions (`allowed-tools`, `compatibility`) from body and scripts |
| Validate, Doctor, hygiene | Explain findings (demote-only) | F10 explain and propose a fix for a validation error as a reviewed diff |
| Tokens, stats, listing budget | Budget fitter | F1 per-skill cost vs usage vs lift |
| Evals, trigger test, regression packs | With/without evals, trigger simulation, saved packs, CI mode | F3 repeated trials, CI, inconclusive label; F6 judge calibration; generated near-miss and anti-trigger cases |
| Usage (`usage report`) | None (deterministic aggregates) | F1 keep / slash-only / merge / archive recommendations |
| Lifecycle (`archive`, `lock`, `native-profile`) | Profile suggestions | F1 retire through `archive`; F2 recheck after a model or agent version change |
| Install, registry (`install`) | Review briefing, explain findings | F11 "do I already have this?" and project-fit ranking of search results |
| Source updates (`update`) | Review briefing | F13 semantic "what changed in behavior" with re-approval when scripts change; three-way proposal when a common ancestor exists |
| Sync map, Inbox (`sync`) | Explain copy differences | F12 applied per-agent adaptation as a reviewed diff |
| Recovery, history, trash (`restore`, `trash`) | None | F10 "what would restoring or purging this change?"; F4 AI provenance labels |
| Batch preview / execute | None | F9 natural-language intent compiles to a normal batch preview, never to execution |
| Templates | None | Template from a selected set of similar skills (later) |
| Import, export, backup | None | None proposed. These are mechanical and low risk. |
| Catalog tags, profiles | Profile suggestions | Tag suggestions from body text (later) |
| Agent scopes, porting | Porting notes | F12 applied conversion |
| AI settings | Provider, caps, test connection | Visible "AI off / local / remote" state in the header; per-feature egress summary |
| Agent-authored changes (Inbox) | Sync explanations | F14 write-time gate for skills that agents create or modify |

## Ranked new features

**[NOTE]** Rank is evidence strength × fit with a filesystem-first,
review-before-apply tool × reuse of existing infrastructure. "Evidence" names
the strongest support above.

| # | Feature | What the user gets | Evidence | Builds on |
|---|---|---|---|---|
| F1 | **Library health and retire assistant** | One view per library or agent: each skill's observed invocations (consented `usage` roots), listing tokens, overlap partners and last measured lift. AI writes a cited recommendation: keep, slash-only (`disable-model-invocation` where the consumer supports it), merge with X, or archive. Applying any of them goes through batch preview and is reversible. No observation means "unknown", never "unused". | Strong: Skills Janitor, sprawl audits, #98220, Cursor analytics requests, Library Drift ([link](https://arxiv.org/abs/2605.19576)), SkillOps ([link](https://arxiv.org/abs/2605.13716)) | `usage`, `tokens`, overlap judge, `archive`, batch preview |
| F2 | **Model-upgrade recheck** | Runs when the configured model changes or on request. Saved regression packs and with/without evals rerun on the new model. A deterministic lint flags MUST/NEVER density, rigid numbered procedures and scaffolding the model no longer needs. A result reads like "lift fell from +0.18 to −0.02; 1,240 listing tokens" and offers a leaner rewrite through Edit with AI and Compare. | Strong: model-upgrade write-ups, SWE-Skills-Bench, HN eval thread | Regression packs, `ai_evals`, `ai_edit`, compare-edit |
| F3 | **Honest test statistics** | k trials per condition (default 3, capped) in shuffled order. Paired lift with a bootstrap confidence interval and an "inconclusive" label. Token and latency regression flags. Assertions that pass or fail on every variant are flagged as non-discriminating. Covers evals, compare-edit and trigger tests. The plan shows trials × calls × cost before anything is sent. | Strong: ACES, skilljack-evals, skill-creator's benchmark mode, #1721, judge-flip preprint | `evals`, `ai_evals`, `ai_edit.compare_edit`, the existing estimate step |
| F4 | **Per-hunk accept and AI provenance** | Every AI proposal opens as hunks with accept and reject. The accepted set becomes a new candidate under the same source-update review and tree-hash checks. Recovery and history label each AI change with its feature, model, a short request summary and the evidence run ID. | Strong UX evidence: Cursor's move from inline diffs to session review drew complaints; HAX G14 and G16 [?] | `source_update` review and commit, snapshots, run receipts |
| F5 | **Draft from real work** | Choose a transcript excerpt from an already consented `usage` root, a git commit range, or selected project files and docs. A redaction preview masks secrets and paths before anything is sent, and a local model is recommended. Output is a draft plus proposed positive, near-miss and negative cases. It stays labelled "unproven" until F3 shows positive lift. | Strong for grounding (ASI, AWM, SkillAxe vs SkillsBench); competitors: ChatGPT Record & Replay ([link](https://learn.chatgpt.com/docs/extend/record-and-replay)), Cline `/newrule`; warning: 10,557 → 0 pipeline | `usage` consent model, `ai_draft`, `risk` secret checks |
| F6 | **Judge calibration** | The user labels about 20 outputs pass or fail. The tool reports how often the LLM judge agrees (TPR/TNR) and lets the user edit criteria while grading. Deterministic assertions come first. The LLM judge never gates a result alone. | Moderate: EvalGen criteria drift ([link](https://arxiv.org/abs/2404.12272)), Hamel Husain practice [?], Langfuse calibration [?] | `evals` assertions, run receipts |
| F7 | **Bounded optimize loop** | Extends the one-pass verified rewrite (description or body section) to at most N reflective iterations, with a spend cap, a held-out split and a stop rule. Only the held-out delta is shown, and the result is offered as a reviewed diff. | Moderate: GEPA ([link](https://arxiv.org/abs/2507.19457)), skill-creator description optimizer; Tessl's modest gain argues for small N | Verified rewrite, trigger test, F3, F4 |
| F8 | **Library scorecard with staleness** | Per-skill grade: spec validity, last trigger recall, last measured lift, listing tokens, security findings, usage. Stored under `<data>/ai/` with a signature of model and content hash, and greyed out when either changes. AI writes only the one-line "why". | Moderate: SkillCat A–D grades, Tessl scores | Validate, risk, trigger runs, evals, `usage` |
| F9 | **Natural-language command bar** | "Disable codex skills I haven't used in 30 days" compiles to an ordinary batch preview showing exact copies. The user executes from the preview; the model never executes anything. Read-only queries are answered with Ask your library. | Moderate: Linear, Raycast, Shape of AI "action plan" pattern | `/api/batch/preview`, Ask your library |
| F10 | **Explain before destructive or confusing actions** | Before trash, purge, restore, sync overwrite or batch disable: a cited summary of which instructions, scripts and agents are affected. Also explains a validation or Doctor error and proposes a fix as a reviewed diff. | Moderate: doc 58 backlog "Explain sync, history, recovery" (Sync map and Inbox done; Recovery and Trash not) | Copy-diff explainer, snapshots, `validate` |
| F11 | **Install-time fit** | Before installing from a registry: overlap against the local library using full text, project fit from profile signals, and an AI-ranked search result list showing audit status. The existing review briefing remains mandatory. | Moderate: Skills Janitor comments, vercel-labs/skills [#2355](https://github.com/vercel-labs/skills/issues/2355), HN "Craigslist for agent skills" | Registry search, overlap judge, profiles |
| F12 | **Applied conversion** | Convert a Cursor rule, slash command, Copilot instruction or AGENTS.md/CLAUDE.md section into a SKILL.md, and adapt a skill into another agent's copy. The output is a reviewed diff, not notes. A "belongs in always-on guidance vs opt-in skill" split is shown. | Weak to moderate: Cursor `/migrate-to-skills` ([guide](https://dev.to/sriram7/how-to-migrate-from-cursor-rules-to-agent-skills-1cl7)), community converters | Porting notes, `key_support`, F4 |
| F13 | **Semantic update and rug-pull review** | For an upstream update, list the behavior and capability changes the diff makes (new tools, URLs, scripts), require re-approval when bundled scripts change, and offer a three-way proposal when a common ancestor exists. | Moderate: ClawVet Show HN, Practice Makes Unsafe, vercel-labs/skills update issues | Review briefing, `source_lock`, `source_update` |
| F14 | **Write-time gate for agent-authored skills** | Skills that agents create or change show up in the Inbox as proposals with a diff, risk scan and rollback, instead of silently entering the library. | Moderate: Practice Makes Unsafe (21 of 21 unsafe; 21.3% → 4.0% with checks) | Inbox, `risk`, source-update review |
| F15 | **Security depth and CI export** | A capability-mismatch check between `allowed-tools` and what bundled scripts do. LLM semantic review shown in its own column beside static findings. SARIF export for CI. A local-model-only review mode. | Moderate: 26.1% vulnerable, scripts 2.12x; Cisco presets | `risk`, explain findings, `ai` CI contract |

Later, only if demand appears: tag and template suggestions, README and
changelog generation from actual diffs, generating and testing bundled scripts
(weak demand found), and multi-model grids beyond the current second-model
comparison.

## Cross-cutting rules for every AI feature

**[SPEC]** These restate existing product rules for the new features.

- **No auto-apply.** Every AI output is a proposal. Applying it goes through an
  existing reviewed path: source-update review, batch preview, or a confirm
  dialog.
- **Preview what is sent.** Show the destination, the outbound content summary
  and the call and token estimate before sending, and bind the confirmed send to
  that preview, as v2 already does.
- **Evidence over scores.** Show raw outputs, trial counts and intervals.
  "Inconclusive" is a valid result. Simulation, observed native use and
  measured output quality keep separate labels.
- **Unknown is not zero.** Missing usage data, an unscanned scope or a skipped
  trial is reported as unknown.
- **Visible AI state.** The header shows AI off, local or remote. `provider:
  null` stays a full off switch, and every feature degrades to its
  deterministic part.
- **Privacy defaults.** Transcript and repository inputs require an explicit
  selection, pass a redaction preview, and recommend a local model. Saved
  evidence keeps grades and hashes, not prompts or outputs, as today.

## What not to build

- Auto-promoting corrections or learned observations into skills without
  review. Evidence shows this either produces nothing or produces unsafe skills.
- Cloud transcript mining by default, or screen recording.
- A hosted registry, accounts or team approval service. That remains outside
  the product's local scope.
- An LLM judge that can block or pass a result on its own.

## Decisions needing maintainer approval

**[NOTE]** Under `AGENTS.md` these need a yes before implementation:

- **CLI commands.** F1, F2 and F3 are useful from the CLI and CI, for example
  `ai health`, `ai recheck` and `--trials` on existing AI test commands. New CLI
  commands and flags need approval.
- **Store methods.** None expected. F1 and F9 should reuse batch preview, and
  F8 stores files under `<data>/ai/` like existing run receipts, with no SQLite
  schema change.
- **REST routes.** New `/api/ai/*` routes follow the existing pattern. They are
  listed here so the scope is visible.
- **Transcript content.** F5 would send transcript content to a model. The
  `usage` consent today covers local aggregation only. Sending content needs
  its own explicit per-excerpt consent and an agreed redaction rule.

## Proposed sequence

| Slice | Ship | Check before expanding |
|---|---|---|
| 1. Trust the numbers (**shipped 2026-11-22** for AI evals and current-vs-proposed comparisons; trigger tests keep their existing repeats) | F3 trials, CI, inconclusive; F4 per-hunk accept and provenance | On fixtures with known lift, confirm interval coverage and that non-discriminating assertions are flagged. Confirm that a partial hunk set applies exactly. |
| 2. Keep the library lean | F1 health and retire; F2 model recheck; F8 scorecard | Run on empty, 1, and 10,000-skill fixtures and on missing or partial usage data. Measure how many recommendations a user accepts and whether archived skills are restored. |
| 3. Grounded authoring | F5 draft from real work; F6 judge calibration; F7 bounded loop | Grounded drafts must show positive held-out lift more often than brief-only drafts on a small labelled set. Confirm the redaction preview catches seeded secrets. |
| 4. Safer intake | F11 install fit; F13 semantic updates; F14 agent-write gate; F15 security depth | Measure false positives on benign skills, including CJK text, and truncation under token caps. |
| 5. Convenience | F9 command bar; F10 explain-before-destructive; F12 applied conversion | The command bar must never reach execution without a preview. Record mismatches between intent and preview. |
