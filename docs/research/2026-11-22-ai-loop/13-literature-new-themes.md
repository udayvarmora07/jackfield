# Round-3 literature: new themes for an AI-assisted skills manager

Date: 2026-11-22. Method: WebSearch + WebFetch of arxiv.org/abs pages and vendor blogs. Fetched content treated as untrusted data.
Tags: [abstract] = only the arXiv abstract page read; [page] = blog/page body read via fetch; [snippet] = search-result summary only (not verified); [?] = unverified.
Warning: several search-engine summaries mislabelled papers (e.g. 2606.13174 was reported as "TRACE" but is "TellOnce"; 2606.32008 was reported as system-prompt transfer but is about surrogate fidelity; 2608.18379 was reported as a placebo paper but is not). Every row below that carries a number was re-checked on the arXiv abstract page unless tagged [snippet]. Most 2026 IDs are non-peer-reviewed, self-reported preprints.

---
## 1. Placebo / length-matched controls

| Source | Year | Method | Key result |
|---|---|---|---|
| Context Length Alone Hurts LLM Performance, https://arxiv.org/abs/2510.05381 | 2025 | 5 LLMs, math/QA/code; irrelevant tokens replaced by whitespace or masked | Perfect retrieval still degrades 13.9%-85% as input grows; recite-then-solve gave up to +4% on RULER for GPT-4o [abstract] |
| Spurious Prompts, https://arxiv.org/abs/2605.29678 | 2026 | Semantically unrelated prompts + black-box search; 0.8B-27B, 3 families | Spurious prompts can match or beat standard prompting and task-aware prompt optimization; steer toward first answer option. No numbers in abstract [abstract] |
| Illusion of Robustness (irrelevant context flips answers), via aiweekly.co | 2026 | Prepend irrelevant context to benchmarks | Aggregate accuracy stable but individual predictions flip both ways [snippet, secondary; ?] |
| Google Cloud, Evaluate agent skills before they bloat your context, https://cloud.google.com/blog/topics/developers-practitioners/evaluate-agent-skills-before-they-bloat-your-context-window | 2026-11-03 | Paired WITH/WITHOUT skill arms, Pass@3, Harbor sandboxes | A skill with identical success and no efficiency gain is "pure context tax"; skills that copied public API tables gave almost no lift; >1/3 of tasks scored differently across reruns. No pass-rate numbers [page] |
| NVIDIA SkillEvaluator docs, https://docs.nvidia.com/skills/evaluating-agent-skills | 2026 | With-skill vs baseline arm, negative cases | Recommends negative cases; no placebo arm [snippet] |

Finding: I found no paper or tool that uses a length-matched placebo skill as a control. The nearest evidence is indirect: length alone costs accuracy, unrelated text can steer or even raise scores on some tasks, and aggregate means hide per-item flips. The SkillsBench-style no-skill baseline therefore conflates "content" with "extra tokens". The placebo is a gap, not an established practice.

Practical implication: add a third arm to skill evals: the same frontmatter, same token count, body replaced by neutral or shuffled-but-fluent filler (and optionally a "wrong-domain skill" arm). Report lift = real minus placebo, not real minus none, and report per-item flips (wins and losses) alongside the mean. Because the router sees only name+description, keep frontmatter identical across arms so activation is not the variable. Label results "relative to placebo" and flag any skill whose lift over none is positive but whose lift over placebo is within noise.

---
## 2. Instruction conflicts, contradictions, hierarchy

| Source | Year | Method | Key result |
|---|---|---|---|
| ConInstruct, https://arxiv.org/abs/2511.14342 (AAAI 2026) | 2025 | Benchmark: detect injected conflicting constraints inside one instruction | DeepSeek-R1 F1 91.5%, Claude-4.5-Sonnet 87.3% [abstract]. Search summary adds: models asked for clarification 36% and silently resolved 9% [snippet] |
| IH-Benchmark, https://arxiv.org/abs/2607.25987 | 2026 | System-over-User and User-over-Tool conflicts, 7 constraint categories, 32 model configs x5 runs, predicate DSL + LLM judge | Compliance 32.9%-97.8%; mean 84.6% System-over-User vs 69.6% User-over-Tool [abstract] |
| WhoWins, Position, Role or Label?, https://arxiv.org/abs/2610.33201 | 2026 | 1,080 scenarios, 14 open-weight models, 1.89M scored replies; vary only delivery | Within a message the first of two conflicting lines wins 72.4%-94.7%; across messages earlier wins 23%-63%; system-placed text can lose to later lines in all Qwen models; at most 2.92% of replies flag a conflict [abstract] |
| OctoBench, https://arxiv.org/abs/2601.10343 | 2026 | 34 environments, 217 tasks, 7,098 checklist items over trajectories | "Systematic gap" between solving the task and scaffold-aware rule compliance. Abstract gives no conflict numbers; a search summary says it has a 32-instance conflict set across system prompt / user / AGENTS.md-CLAUDE.md [abstract; conflict part snippet] |
| IFScale, https://arxiv.org/abs/2507.11538 | 2025 | 500 keyword instructions, 20 models | Best models ~68% at 500 simultaneous instructions; bias to earlier instructions [abstract] |

Practical implication: contradictions between skills (and between a skill and CLAUDE.md/AGENTS.md) are almost never surfaced by the model (under 3% flag them) and precedence is decided by position, not by declared importance. So the manager must find conflicts statically, before runtime: extract atomic directives per skill, pair directives about the same subject, and ask an LLM judge (ConInstruct shows ~87-91% F1 is attainable) to label contradictory / compatible / redundant, with the two quoted lines as evidence. Show a precedence preview ("which line a model is likely to obey: the earlier one"), and offer a deterministic fix (reorder, scope, or delete) rather than trusting "system" placement. Instruction count matters too: warn when always-on directives pile up.

---
## 3. Routing traces / explaining tool or skill selection

| Source | Year | Method | Key result |
|---|---|---|---|
| Tool Preferences in Agentic LLMs are Unreliable, https://arxiv.org/abs/2505.18135 (EMNLP 2025) | 2025 | Edit tool descriptions; 17 models | Properly edited descriptions got over 10x usage from GPT-4.1 and Qwen2.5-7B [abstract] |
| BiasBusters, https://arxiv.org/abs/2510.00307 (ICLR 2026) | 2025/26 | Equivalent tools per category, 7 LLMs; isolate metadata, features, pretraining exposure | Substantial selection bias persists; filter-then-sample mitigation. Search summary: query-description semantic alignment is the most interpretable factor [abstract; last part snippet] |
| SkillRouter, https://arxiv.org/abs/2603.22455 | 2026 | ~80K overlapping skills; routing with and without skill body | Hiding the body drops routing accuracy 37-44pp; 1.2B body-aware router 74.0% Hit@1; body-distilled descriptions still 7-21pp below full [abstract] |
| Demystifying Agent Skills, https://arxiv.org/abs/2608.14036 | 2026 | Controlled experiments, 8,135 trial records, open coding | Actual-use retrieval precision falls from 29.6% to 3.3% as the pool grows 5 to 100 [abstract] |
| When Tools Look Alike (NeurIPS 2026 listing), https://neurips.cc/virtual/2026/158000 | 2026 | Accuracy vs semantic closeness of distractors; contrastive boundary descriptions | Accuracy falls as distractors get closer; 50-task preliminary [snippet] |
| Google Cloud skill-reach, link in topic 1 | 2026 | Lint + vocabulary overlap + routing probes | Example collision flagged at 0.69 vocabulary overlap; sibling hijacking named as a failure mode [page] |

Gap: no source gives per-call attribution of "which description caused this choice". The defensible approach is perturbation (counterfactual) analysis.

Practical implication: build a "why this skill" panel from three cheap, honest signals: (a) static: description overlap/embedding margin between each skill and its nearest neighbours (flag sibling-hijack risk before any run); (b) counterfactual: re-run a probe prompt with candidate skill A's description removed or swapped, and report the flip; (c) observed: log which skill the agent actually invoked in a transcript. Present the margin to the nearest competitor, not a single "confidence". Warn that routing is strongly pool-size dependent, so the report should be re-run when skills are added.

---
## 4. Behavioural (trajectory / first-action) grading vs text grading; repeated-run consistency

| Source | Year | Method | Key result |
|---|---|---|---|
| Anthropic, Demystifying evals for AI agents, https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | 2026-01-09 | Practitioner guide | pass^k = probability all k trials succeed (falls with k); example 75% per trial gives ~42% pass^3; grade the outcome/final state, check required tool calls rather than a rigid sequence; use transcript grading for constraints [page] |
| tau-bench, https://arxiv.org/abs/2406.12045 | 2024 | Introduces pass^k | gpt-4o under 50% of tasks, pass^8 under 25% in retail [snippet] |
| Procedure-Aware Evaluation, https://arxiv.org/abs/2603.03116 | 2026 | tau-bench with procedural-integrity gating | 27-78% of reported successes are "corrupt successes"; gating lowers Pass^4 and changes rankings [abstract] |
| Claw-Eval, https://arxiv.org/abs/2604.06132 | 2026 | 300 tasks, 14 models; traces + audit logs + snapshots; 3 trials | Trajectory-opaque grading misses 44% of safety violations, 13% of robustness failures; under error injection Pass@3 stable while Pass^3 drops up to 24pp [abstract] |
| Google Cloud (topic 1) | 2026 | Paired repeated runs | >1/3 of tasks scored differently across consecutive identical runs; use Pass@3 [page] |
| Scott Spence, sandboxed activation evals, https://scottspence.com/posts/measuring-claude-code-skill-activation-with-sandboxed-evals | 2026-02-08 | `claude -p` in sandboxes, parse JSONL for Skill() calls; 22 prompts, 2 runs, Sonnet 4.5, 4 Svelte skills | No hook 55%/50% activation; forced-eval hook 100%/100%; on 24 harder prompts forced-eval 75% accuracy, 0 false positives; llm-eval 20% on true negatives [page]. Small n, one model |

Practical implication: for a skills manager the cheapest behavioural signal is the first tool call: did the agent invoke the right Skill() (and not a wrong one) in the stream-JSON trace? That is deterministic, needs no judge, and catches the Vercel-style "skill never invoked" failure that output grading misses. Grade outcome where possible, but add trace checks for required/forbidden tool calls (Anthropic's advice: required tools, not exact order). Always run each case k times and show pass@k and pass^k side by side; a skill that is "100% once" can be 42% pass^3. Show the number of runs next to every percentage and refuse to render a lift without a confidence interval when n is small.

---
## 5. Always-on context vs on-demand skills vs deterministic hooks/scripts

| Source | Year | Method | Key result |
|---|---|---|---|
| Evaluating AGENTS.md, https://arxiv.org/abs/2602.11988 | 2026 | SWE-bench-style tasks, generated and developer-written context files | Context files do not generally improve success; inference cost up over 20% on average [abstract] |
| Impact of AGENTS.md on efficiency, https://arxiv.org/abs/2601.20404 | 2026 | 10 repos, 124 PRs, with vs without | Median runtime -28.64%, output tokens -16.58%, completion comparable [abstract]. Opposite cost direction from the above; setups differ |
| Anthropic, Effective context engineering, https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 2025-09-29 | Guide | Smallest high-signal token set; hybrid upfront + just-in-time; minimal tool set because overlapping tools cause ambiguity; context rot [page] |
| Anthropic, Agent Skills progressive disclosure, https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | 2025 | Design article | Metadata, then SKILL.md, then bundled files, loaded on demand [snippet; page not read] |
| Spence forced-eval hook (topic 4) and Towards Data Science session-start hook article, https://towardsdatascience.com/a-session-start-hook-raised-claude-code-skill-firing-from-15-to-62/ | 2026 | Hooks to raise skill firing | Control 55%/50% to 100% with a forced-eval hook (one model, 22 prompts) [page]. TDS: pooled firing 15% to 62% over six skills, 0 of 972 near-miss runs fired the target [snippet, 403 on fetch] |
| What Should a Skill Remember?, https://arxiv.org/abs/2606.09421 | 2026 | Cost-aware skill rewriting on SkillsBench | Learned rewriting cuts total cost 7.0% (14.7% on frozen cross-model transfer), verifier quality preserved [abstract] |
| IFScale (topic 2) | 2025 | | Instruction-following falls with density [abstract] |
| Vercel (first pass) | 2026 | | Docs index in AGENTS.md beat skills when skills were not invoked [per first pass] |

Practical implication: a placement advisor with three rules, each backed by evidence. (1) Move to always-on only content that is short, needed in nearly every task, and not derivable from the repo (the AGENTS.md results say bloat costs 20%+ with no success gain). (2) Keep conditional know-how as a skill, but verify it actually fires (activation can be 20-55% without help) and budget the description. (3) Anything that must happen every time (lint, format, a forbidden command) belongs in a hook or script, not prose: a hook is deterministic and costs zero instruction slots. The manager can score each directive on frequency-of-need, determinism-possible, and token cost, and suggest "demote to skill", "promote to hook" or "delete (model already knows it)". Pair this with the paired-arm result: if the skill adds nothing over no-skill, suggest deletion.

---
## 6. Cross-model portability

| Source | Year | Method | Key result |
|---|---|---|---|
| Prompt Engineering a Prompt Engineer / transfer studies via search, https://arxiv.org/pdf/2311.05661 | 2023 | Prompts from optimizers tested on other models | No consistent generalization; prompts tied to the source model [snippet] |
| PromptBridge, https://arxiv.org/abs/2512.01420 | 2025 | MAP-RPE per-model optimization + learned cross-model mapping | Reports a "transfer gap"; consistent accuracy gain, no numbers in abstract [abstract] |
| Chess prompt-optimization benchmark, https://arxiv.org/pdf/2610.00416 | 2026 | Transfer across 8 models | One prompt with largest native gain degraded 5 of 7 other models; another improved all 7 [snippet] |
| SkCC, https://arxiv.org/abs/2605.03353 | 2026 | Compile one SKILL.md IR into per-framework variants; SkillsBench | Claude Code pass rate 21.1% to 33.3%, Kimi CLI 35.1% to 48.7%; tokens -10% to -46% [abstract]. Format-sensitivity claim (XML vs markdown) is secondhand [snippet] |
| SkillCommit / SKILL-DISCO via search, https://arxiv.org/pdf/2608.15165 , https://arxiv.org/pdf/2606.26669 | 2026 | Skills authored by one model run by another | Cross-family reuse mostly positive; gains larger on small open models (Qwen3.5-9B +80.8% on ALFWorld vs +3-7% for GPT) [snippet only] |
| SkillsBench (first pass) | 2026 | Claude/Gemini/GPT configs | Curated skills help; self-generated do not [per first pass] |
| Skill Is Not Document, https://arxiv.org/pdf/2606.03565 | 2026 | Query-conditioned skill routing | [snippet only, not read] |

Practical implication: results are mixed and pair-dependent, so a manager should never claim "validated" without naming the model. Store eval results keyed by (skill hash, model id, harness) and show a matrix with blanks for untested cells instead of extrapolating. Offer "run this skill on model B" as the explicit portability test (DeepSeek/Qwen/GPT/Gemini via the user's own keys), and surface which skills show lift only on smaller models (they are likely to look useless on a frontier model: candidates for the zero-delta delete flag). Treat any per-model rewrite (SkCC-style) as a generated variant with its own eval, not as the same skill.

---
## 7. Learning rules from corrections, with approval; consolidation; forgetting

| Source | Year | Method | Key result |
|---|---|---|---|
| TellOnce, https://arxiv.org/abs/2606.13174 | 2026 | Convert conversational corrections to scoped, revisable rules + executable checks; frozen state tested on later tasks | Mem0-style memory violated 57.5% of applicable preference checks; TellOnce lowest violation in all 6 settings; 19.3-42.3pp fewer than PGMem on ClawArena; task performance comparable [abstract] |
| Decision Context, https://neurips.cc/virtual/2026/169598 | 2026 | Compile corrections and tool failures into imperative RULE directives | Imperative rules followed reliably, raw retrieved text unreliably [snippet] |
| Rubric feedback memory, https://arxiv.org/pdf/2601.05960 | 2026 | Distil feedback into file-based lessons | [snippet only] |
| Memory Worth, https://arxiv.org/abs/2604.12007 | 2026 | Two counters (success/failure with a memory) per memory | Spearman 0.89 vs true utility on synthetic data; stale memories fell to 0.17 vs 0.77 for specialist ones. Associational, synthetic [abstract] |
| Reasoning Contraction, https://arxiv.org/abs/2610.17544 | 2026 | Failure-weighted, likelihood-ratio certificates for memory retirement | Plain success/failure counters (ExpeL/ACE-style) served 7.0-13.5x more stale answers (35-73x on code with exact verifier) [abstract] |
| RSPM, https://arxiv.org/abs/2610.25561 | 2026 | Cluster failures into rules, decay unless reinforced, promote cross-context rules | +9.1 pts SWE-bench simulation, ~93% fewer retry loops, ~30% fewer entries [abstract] |
| Always-On Agents survey, https://arxiv.org/pdf/2606.30306 | 2026 | Survey | Forgetting should be governed (who authorised decay, how to reverse) [snippet] |

Practical implication: a "propose a rule from this correction" flow is well supported, provided the proposal is (a) atomic and scoped (which skill/project, when it applies), (b) accompanied by the quoted correction as evidence, (c) paired with an executable check where possible, and (d) reconciled against existing rules (conflict check from topic 2) before the human approves. Human approval is the manager's job; none of the papers evaluate it with real users, so state that as unverified. Decay should be evidence-driven, not clock-driven: record per rule how often it was applicable, followed, and violated, and flag stale rules for human retirement; weight failures more than successes. Every retirement must be reversible (the filesystem/trash model already fits).

---
## 8. Activation precision/recall monitoring and drift

| Source | Year | Method | Key result |
|---|---|---|---|
| Demystifying Agent Skills (topic 3) | 2026 | | Actual-use precision 29.6% to 3.3% as pool grows 5 to 100 [abstract] |
| Spence + TDS (topic 5) | 2026 | Activation counting from tool-call logs | 0 of 972 near-miss prompts fired the target [snippet]; forced-eval had 0 false positives on 5 no-skill prompts, llm-eval 4 false positives [page, tiny n] |
| Sequential inference for LLMs, https://arxiv.org/pdf/2606.07624 ; Who Drifted: the System or the Judge?, https://arxiv.org/pdf/2606.15474 | 2026 | Online change-point / anytime-valid monitoring | Fixed-threshold tests re-run at every step lose error control; attribute drift to system vs judge [snippet only] |
| W&B / DEV Community retrieval monitoring guides | 2025-26 | Practitioner | Frozen regression set replayed on a schedule and after provider/index changes; recall@k drops precede complaints; sample manually to catch judge drift [snippet, vendor blogs] |
| Google Cloud (topic 1) | 2026 | | Re-run paired matrix on each model upgrade, delete skills whose delta drops to zero [page] |

Gap: I found no published method for production precision/recall of skill routing; the practice is borrowed from retrieval monitoring.

Practical implication: parse local agent session logs (Skill() calls plus the user prompts that preceded them) to compute, per skill: activation count, how often a user manually invoked it after the agent missed it (a recall proxy), and how often the agent invoked it and the user rejected or ignored it (a precision proxy). Be honest that these are proxies without ground truth. Keep a frozen probe set per skill (positive, near-miss, negative prompts) and replay it on model/harness upgrades; alert only on sequential, not single-run, changes, and show n. Keep logs local and treat prompts as personal data.

---
## 8 feature ideas best supported by the evidence

1. Placebo-controlled skill eval (third arm: length-matched filler body, identical frontmatter) with lift reported over placebo and per-item win/loss flips. Strength: strong indirect evidence (2510.05381, 2605.29678, Google), no direct precedent.
2. Static contradiction/overlap linter across skills + CLAUDE.md/AGENTS.md with quoted evidence and a precedence preview. Strength: high (ConInstruct F1 ~87-91, WhoWins <3% flagging, position dominates).
3. First-tool-call trace grader: did the right Skill() fire (and no wrong one), from stream-JSON logs, run k times with pass@k and pass^k side by side. Strength: high (Anthropic, Claw-Eval, PAE, Spence).
4. "Why this skill" routing panel: nearest-neighbour description margin + counterfactual description swap + observed invocation. Strength: medium-high (BiasBusters, 10x description-edit effect, SkillRouter, Google skill-reach).
5. Placement advisor: always-on vs skill vs hook vs delete, using need-frequency, determinism, tokens, and zero-delta evidence. Strength: medium-high (2602.11988, 2601.20404 conflict in direction, Anthropic, Google).
6. Model-keyed result matrix (skill hash x model x harness) with explicit "untested" cells and a run-on-another-model button. Strength: medium (transfer is pair-dependent).
7. Correction-to-rule proposals with scope, evidence quote, optional executable check, conflict check, and human approve/reject, plus evidence-based staleness flags (applicable/followed/violated counters, failure-weighted). Strength: medium (TellOnce, 2610.17544, 2604.12007; no human-approval study).
8. Activation-drift monitor from local session logs with a frozen probe set replayed after model/harness updates. Strength: medium-low (mechanism borrowed from retrieval monitoring; precision falling with pool size is documented).

## Unverified points

- Full text was read for none of the arXiv papers; numbers tagged [abstract] come from abstract pages only. Search-engine summaries were wrong about the identity of three papers, so any [snippet] row may also be wrong.
- Rows tagged [snippet only]: 2311.05661 transfer claim, 2610.00416, 2608.15165, 2606.26669, 2606.03565, 2601.05960, 2606.30306, 2606.07624, 2606.15474, Decision Context (NeurIPS listing), When Tools Look Alike, TDS 15%->62% article (403), Anthropic Agent Skills post layer details, W&B/DEV guides, Illusion of Robustness.
- Spence's 100% activation figures are from one model, 22 prompts, 4 skills, 20 s windows; an earlier DeepWiki-derived 20%/84% figure came from a different setup and conflicts with them. Do not quote a single "activation rate".
- The AGENTS.md papers disagree on cost direction (+20% vs -17%/-29%) because settings differ; no study tests SKILL.md content vs always-on content directly.
- No source tests human approval of learned rules, production precision/recall of skill routing, or a length-matched placebo skill. Those are gaps, not findings.
- The Google blog and the TDS article mention model names (Claude Sonnet 5, Opus 5.5) I could not independently confirm.
- Whether position-dominance (WhoWins) holds for Claude/GPT/Gemini is unknown: the study covers 14 open-weight models, with gpt-oss as the only non-Qwen example in the abstract.
