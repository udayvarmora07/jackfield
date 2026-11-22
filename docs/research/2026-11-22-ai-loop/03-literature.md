# Literature research: AI features for a skills manager (SKILL.md)

Date: 2026-11-22. Method: web search plus arXiv abstract pages. Content was treated as untrusted data.
Tags: [abstract] = number read from the arXiv abstract page only (full paper not read). [snippet] = from a search-result summary only. [?] = unverified or secondhand.
Caveat: many 2026 preprints (IDs 26xx) are non-peer-reviewed and self-reported; several 2026 arXiv IDs are unusually high and I could not cross-check them independently.

---

## 1. Automatic skill generation / extraction

| Source | Year | Method | Key result |
|---|---|---|---|
| SkillsBench, https://arxiv.org/abs/2602.12670 | 2026 | Benchmark; same tasks run with no skill, curated skills, self-generated skills; deterministic verifiers; 7 agent/model configs, 7,308 trajectories | Curated skills +16.2pp average pass rate (varies +4.5pp SWE to +51.9pp healthcare); 16 of 84 tasks regress; self-generated skills about -1.3pp (no benefit) [snippet]. Versions disagree (84 vs 86 tasks, 16.2 vs 16.4pp), so cite one version. |
| SkillAxe, https://arxiv.org/abs/2606.10546 | 2026 | Unsupervised loop: LLM scores its own skill on quality impact, trigger precision, instruction compliance and path coverage, then writes improvement briefs | +28% relative over unimproved LLM-authored skills on SkillsBench, closing 47-67% of the gap to human skills; SpreadsheetBench 16.0% to 52.0% with 22 skills [abstract] |
| SkillGenBench, https://arxiv.org/abs/2605.18693 | 2026 | Benchmark of generation pipelines: task-conditioned vs task-agnostic; repository-grounded vs document-grounded sources; execution-based checks | No numbers in abstract. Qualitative: performance varies widely, reusable skill distillation is hard, failure modes differ between repo and doc sources [abstract] |
| Agent Skill Induction (ASI), https://arxiv.org/abs/2504.06821 | 2025 | Induce program-based skills on the fly and verify them programmatically | +23.5% over static baseline and +11.3% over text-skill version on WebArena, attributed mainly to verification [snippet] |
| SkillWeaver, https://arxiv.org/abs/2504.07079 | 2025 | Agent explores a site, proposes skills, practices them, distills into Python APIs | Up to +54.3% on WebArena when APIs from stronger agents are given to weaker ones [snippet] |
| Agent Workflow Memory, https://arxiv.org/abs/2409.07429 (ICML 2025) | 2024/25 | Induce reusable workflows from trajectories, offline or online | +24.6% relative on Mind2Web, +51.1% on WebArena; +7.9% over human-written workflows [snippet] |
| Voyager, https://arxiv.org/abs/2305.16291 | 2023 | Store code skills indexed by embedding of their description; retrieve by similarity | 3.3x more unique items, 15.3x faster tech-tree milestones vs prior SOTA [snippet] |
| ExpeL, https://arxiv.org/abs/2308.10144 | 2024 | Collect success/failure pools, extract natural-language insights; inspectable and editable | Insights can be reviewed and removed by users [snippet] |

Practical implication for a skills manager: the headline is that a model asked to write a skill cold, without evidence, adds roughly nothing, while skills grounded in evidence (trajectories, verified runs, real repo/doc content) and then refined against feedback close about half the gap to curated skills. A generator should therefore never be "write a skill about X". It should be "distill this transcript / this repo's scripts / this doc" and ship the candidate together with the evidence it came from (trajectory spans, file paths), plus an eval run showing lift over no-skill. Verification before acceptance (ASI) was the main driver of gains, so a generated skill should stay in a "draft/quarantine" state until it passes at least a with/without-skill check. Keep skills short and focused (SkillsBench: 2-3 modules beat comprehensive docs [snippet]).

---

## 2. Skill / prompt optimization

| Source | Year | Method | Key result |
|---|---|---|---|
| GEPA, https://arxiv.org/abs/2507.19457 (ICLR 2026 oral) | 2025/26 | Reflect on trajectories in natural language, mutate prompts, keep a Pareto frontier of candidates | +6pp average over GRPO (up to +19pp) with up to 35x fewer rollouts; beats MIPROv2 by over 10pp [snippet]. v1 reported +10%; use v2 numbers. Author-run only. |
| MIPRO / DSPy, https://arxiv.org/abs/2406.11695 (EMNLP 2024) | 2024 | Joint instruction and few-shot optimization with a surrogate model and minibatch evaluation | Beats baselines on 5 of 7 programs, up to 13% accuracy [snippet]; instruction optimization matters most for tasks with conditional rules |
| TextGrad, https://arxiv.org/abs/2406.07496 | 2024 | Backpropagate LLM textual feedback through a compute graph | GPQA 51% to 55%; +20% relative on LeetCode-Hard [snippet] |
| Skill-infinity, https://arxiv.org/abs/2610.35434 | 2026 | Meta-agent follows a meta-skill: diagnose traces, propose skills, independent review, budget allocation; also optimizes the meta-skill | 60.7% pass rate on 83 SkillsBench tasks vs 56.4% human-curated and 54.5% SkillEvolver [abstract] |
| Library Drift, https://arxiv.org/abs/2605.19576 | 2026 | Held-out pass@1 tracked over 100 rounds on MBPP+ hard-100 with outcome-driven retirement and bounded caps | Held-out pass@1 0.258 to 0.584 mean (late window) [abstract] |
| agentskills.io "Optimizing descriptions", https://agentskills.io/skill-creation/optimizing-descriptions | 2026 | Official guide: run each trigger query several times, compute trigger rate | Suggests 3 runs per query, 0.5 pass threshold [snippet]. Practitioner guidance, not a study. |
| Vercel, https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals | 2026 | Eval on Next.js 16 APIs absent from training data | Skills never invoked in the default setup: 53%, same as baseline; explicit instruction raised trigger rate to 95%+ and pass rate to 79%; AGENTS.md docs index 100% [snippet]. Small wording changes ("invoke first" vs "explore first") swung behavior. |

Practical implication for a skills manager: reflective optimization (GEPA-style) maps naturally onto skills because the artifact is text and trajectories are textual feedback. The central risk is overfitting to the eval set (GEPA and Skill-infinity both report on held-out tasks; Library Drift measures held-out pass@1). A tool should always split cases into train/validation/held-out, show the held-out delta separately, and refuse to present the train score as the result. Description optimization is its own sub-problem: triggering is the most fragile part (Vercel's 53% baseline), is sensitive to wording, and needs multiple runs per query because the agent is stochastic. Make description tuning a first-class "trigger eval" with should-trigger and near-miss should-not-trigger queries, repeated runs, and a train/test split of queries. Present a proposed edit as a diff with before/after metrics rather than silently rewriting.

---

## 3. Skill evaluation

| Source | Year | Method | Key result |
|---|---|---|---|
| ACES / NVIDIA SkillEvaluator, https://arxiv.org/abs/2608.20614 | 2026 | Paired trials with and without the skill; same model, sandbox, grader; reports "Skill Lift" | 145 skills, 947 paired cases; mean composite lift 0.2134 (95% CI [0.1967, 0.2301]); positive in 72.8% of cases; scan-vs-LLM-judge Spearman 0.14 [abstract] |
| SkillEval, https://arxiv.org/abs/2608.06891 | 2026 | Document-level scoring of SKILL.md along interpretable properties, controlling for confounding document features | Qualitative only: scores track downstream pass rate, targeted revisions raise it [abstract] |
| SkillCoach, https://arxiv.org/abs/2607.01874 | 2026 | Skill-specific process rubrics built from rollouts: selection, following, composition, reflection | No numbers; claims it exposes failures hidden by final accuracy [abstract] |
| Agent Skills Can Be Harmful, https://arxiv.org/abs/2608.11888 | 2026 | Differential analysis: skill-guided run vs no-skill/matched-skill run; SkillTriage taxonomy | 307 skill-induced failures: 125 functional, 182 efficiency regressions; excessive verification is the top cause (67) [abstract] |
| EvalGen / "Who validates the validators", https://arxiv.org/abs/2404.12272 | 2024 | Mixed-initiative: propose criteria + code/LLM graders, human grades a sample, select graders that align | Qualitative study; "criteria drift": users cannot fully define criteria before grading outputs [abstract; no quantitative results given] |
| The Coin Flip Judge?, https://arxiv.org/abs/2606.13685 | 2026 | Repeated pairwise/pointwise judging with two OpenAI judges | Pairwise verdicts flip 13.6% on repeat; 28% of questions have flip rate >20%; equivalent prompt templates change the majority outcome in 25% of cases; ~11 trials needed to match a 50-trial majority at 95% [abstract; single author, treat as provisional] |
| Am I More Pointwise or Pairwise?, https://arxiv.org/abs/2602.02219 | 2026 | Rubric order causes position bias even in pointwise scoring; average over permutations | Permutation averaging improves human correlation [snippet] |
| Adding Error Bars to Evals, https://arxiv.org/abs/2411.00640 | 2024 | Treat evals as experiments: standard errors, paired differences, clustered SEs, power analysis | Paired question-level differences recommended over comparing summary scores [snippet] |
| Hamel Husain evals FAQ, https://hamel.dev/blog/posts/evals-faq/ | 2025 | Practice: error analysis first, binary pass/fail, judge validated with TPR/TNR on held-out human labels | Suggests reviewing 20-50 outputs per significant change [snippet] |

Practical implication for a skills manager: the best-supported evaluation is behavioral and paired: run the same task with and without the skill and report lift with a confidence interval (ACES). Document-quality scoring (SkillEval, lint-like) and LLM judges measure different things from behavior (rho = 0.14), so present them as separate columns, not one grade. With few samples, use paired differences, repeat runs, and show CIs or an explicit "not enough data" state; do not call a 2-of-3 change an improvement. Prefer binary checks (code assertions first, LLM binary judge second), randomize order, use multi-trial majority, and calibrate any LLM judge against a small human-labeled set (TPR/TNR on held-out labels). Let the user grade a handful of outputs and use that to select/refine assertions (EvalGen), and expect their criteria to change while grading. Watch for harmful skills: track efficiency regressions (excessive verification) as well as pass-rate.

---

## 4. Retrieval / selection at scale

| Source | Year | Method | Key result |
|---|---|---|---|
| SkillRouter, https://arxiv.org/abs/2603.22455 | 2026 | Route over ~80K skills (SkillsBench-derived); compare name/description-only vs full body; 1.2B retrieve-and-rerank | Hiding the skill body drops routing accuracy 37-44pp; body-distilled descriptions recover part but remain 7-21pp below full-body; 74.0% Hit@1; 13x fewer parameters, 5.8x faster than strongest base pipeline [abstract] |
| SkillCoach, https://arxiv.org/abs/2607.01874 | 2026 | Separates positive triggering from negative abstention; near-neighbor skills are the dangerous distractors | No numbers [abstract; distractor claim from snippet] |
| ToolRet, https://arxiv.org/abs/2503.01763 (Findings of ACL 2025) | 2025 | 7.6k retrieval tasks over 43k tools | Models strong on standard IR do poorly on tool retrieval [snippet] |
| ToolScope, https://arxiv.org/abs/2510.20036 | 2025 | Merge overlapping tools, then retrieve top-k | No figures read [?] |
| SkillOps, https://arxiv.org/abs/2605.13716 | 2026 | Typed skill contracts + hierarchical skill ecosystem graph; mostly rule-based | ALFWorld 79.5%, +8.8pp over strongest baseline; +0.68 to +2.90pp as plug-in [abstract] |
| Scan Before You Install, https://arxiv.org/abs/2610.37901 | 2026 | Builds skill dependency graph via file handoffs, shared env state, named invocations | Composite module 98.7% precision / 99.6% recall on SCR-Bench (1,325 sets) [snippet, self-reported] |
| Library Drift, https://arxiv.org/abs/2605.19576 | 2026 | Unbounded accumulation degrades retrieval | Retrieval degradation and false-positive injection when libraries grow unmanaged [snippet] |

Practical implication for a skills manager: the description-only view the agent sees is a weak routing signal at scale, while the body carries most of the discriminative information. So a manager can add value by (a) generating descriptions distilled from the body, and (b) a "confusability" check that embeds or LLM-reranks each skill against its neighbors using full text and flags near-duplicates and descriptions that overlap another skill (the near-neighbor distractor problem). Show a per-skill "would this trigger on prompt X, and which competing skills would?" simulator. Keep active libraries bounded; Library Drift suggests a cap and retirement. A dependency/handoff graph (shared files, named invocations) is both a navigation feature and a security feature (composite vulnerabilities).

---

## 5. Maintenance: drift, dedup, consolidation, self-editing

| Source | Year | Method | Key result |
|---|---|---|---|
| Library Drift, https://arxiv.org/abs/2605.19576 | 2026 | Outcome-driven retirement, bounded active cap, append-only evidence log of per-skill contribution | Held-out pass@1 0.258 to 0.584; premature retirement harms (-0.019) [abstract] |
| SkillOps, https://arxiv.org/abs/2605.13716 | 2026 | Library health on utility, compatibility, risk, validation; merge/repair/retire actions | See topic 4 [abstract]. Notes library-time maintenance can conflict with task-time self-repair [snippet]. |
| SkillComposer, https://arxiv.org/abs/2606.06079 | 2026 | Create/improve/merge operations trained with rejection sampling; merge when similarity exceeds a threshold | 4B model improves a 27B executor by up to +4.5 (agent) and +3.4 (code) points [abstract] |
| SkillCAT, https://arxiv.org/abs/2606.13317 | 2026 | Verify patches before merging to avoid accumulating conflicting rules | No numbers read [snippet] |
| Practice Makes Unsafe, https://arxiv.org/abs/2608.12851 | 2026 | Skill misevolution benchmark (525 tasks); SafeEvolve checks skills at write and retrieval | All 21 agent/method combos wrote unsafe skills, 15 carried harm to new session; SafeEvolve cut new-session harm 21.3% to 4.0% with utility within 0.4pt [abstract] |
| SoK: Agentic Skills, https://arxiv.org/abs/2602.20867 | 2026 | Lifecycle taxonomy: discovery, practice, distillation, storage, composition, evaluation, update | Survey; no experiments [abstract] |
| Dynamic Agent Skills lifecycle survey, https://arxiv.org/pdf/2607.10113 | 2026 | Survey of evolving libraries | Not read in detail [?] |
| Stale-skill tooling (e.g. TanStack intent stale) | 2026 | Age/source-hash based staleness checks | Practitioner tooling, no evaluation [snippet] |

Practical implication for a skills manager: maintenance is a recognized open problem with early evidence. Cheap, rule-based operations (staleness by referenced file/package version/hash, dedup by similarity threshold, retire never-used or net-negative skills, cap active count) beat expensive LLM rewriting in at least one study (SkillOps is mostly rule-based). Any agent-driven auto-edit of skills should be gated: write-time and retrieval-time checks, versioned history, diff review, and rollback. Merge via a proposed diff plus a before/after eval, never silently. I found no strong research on detecting drift against external library/API version changes specifically; that part is [?] and is best built as deterministic checks (version strings, paths, command existence, link checks).

---

## 6. Security

| Source | Year | Method | Key result |
|---|---|---|---|
| Skill-Inject, https://arxiv.org/abs/2602.20156 | 2026 | 202 injection-task pairs; security vs utility axes | Attack success up to 80% on frontier models; argues scaling and input filtering will not suffice [abstract] |
| SkillHarm, https://arxiv.org/abs/2606.02540 (EMNLP 2026) | 2026 | 879 attack samples across 71 skills; fixed-payload and self-mutating poisoning | ASR up to 86.3% (fixed) and 69.3% (self-mutating); defenses unreliable [abstract] |
| Agent Skills in the Wild, https://arxiv.org/abs/2601.10338 | 2026 | SkillScan: static analysis + LLM classification on 31,132 skills | 26.1% have at least one vulnerability; scripts make skills 2.12x more likely vulnerable; detector precision 86.7%, recall 82.5% [abstract]; static scanner and LLM detector overlap very little [snippet] |
| Malicious Agent Skills in the Wild, https://arxiv.org/abs/2602.06547 | 2026 | Behavioral verification of 98,380 skills | 157 confirmed malicious skills; one actor 54.1%; 93.6% removed after disclosure [snippet] |
| Defenses and Enablers, https://arxiv.org/abs/2606.01567 | 2026 | Dynamic guardian (runtime mediation) and static guardian (rewrite pre-deploy) | ASR under reframing 81.4% unguarded vs 18.6% with dynamic guardian [abstract] |
| Towards Secure Agent Skills, https://arxiv.org/abs/2604.02837 | 2026 | Threat taxonomy over four lifecycle phases | Names three structural weaknesses: no data/instruction boundary, single-approval persistent trust, capability declarations without enforcement [abstract] |
| Agent Skills for LLMs, https://arxiv.org/abs/2602.12430 | 2026 | Survey with proposed trust-tier governance (four tiers) | Cites 26.1% vulnerable [abstract] |
| Scan Before You Install, https://arxiv.org/abs/2610.37901 | 2026 | Six-module scanner with evidence validation step | 96.95% precision / 95.05% recall on SkillTrustBench, self-reported [snippet] |
| Sifting the Noise, https://arxiv.org/abs/2601.22952 | 2026 | LLM agents as SAST false-positive filters | FP rate 92%+ down to 6.3%, but aggressive filtering suppressed true positives [snippet] |

Practical implication for a skills manager: scanning should be layered and honest about uncertainty. Deterministic checks (scripts present, network/exec/credential-path patterns, hidden Unicode, obfuscation, declared `allowed-tools` vs what the scripts actually do) are cheap and catch the capability-mismatch class. An LLM reviewer adds recall for semantic injection, but the two detectors overlap little, so run both and show their findings separately. LLM review should be advisory: labelled "risk signals with evidence," never a pass certificate, because filtering that removes false positives also removes true positives. Treat skill text as untrusted data when the manager's own LLM reads it (the manager is itself an injection target; guard its prompts). Scripts bundled with skills are the strongest risk factor, so show them prominently, diff them on every change, and offer sandboxed dry-run. Sandboxing for skill scripts: the literature establishes the need (capability declarations unenforced) but I found no measured results for specific sandboxes; [?].

---

## 7. Human-AI co-editing UX

| Source | Year | Method | Key result |
|---|---|---|---|
| Copilot controlled study (found via search, arXiv id not captured) | 2025 | Compared no use, inline, chat, both | Moderate use of either improves efficiency and lowers workload; excessive or combined use reduces benefits [snippet; paper not identified, [?]] |
| Co-design study with 56 developers (via search) | 2025 | Where to place suggestions and explanations | Inline for short completions; sidebar/chat for longer ones; minimal suggestions first, details on demand [snippet; [?]] |
| Take It, Leave It, or Fix It, https://arxiv.org/abs/2402.18498 | 2024 | Measure productivity and trust in human-AI collaboration | Participants increasingly depended on the AI despite reporting less trust [snippet] |
| Vasconcelos et al., https://arxiv.org/abs/2212.06823 | 2023 | Five studies, N=731, task difficulty and explanation cost | Whether explanations reduce overreliance depends on difficulty and effort; overreliance did not drop when explanations were simply added [abstract] |
| Spillner et al., https://arxiv.org/abs/2603.05229 | 2026 | N=300 workflow study | Effect of explanations on trust does not transfer across workflows; a two-step workflow increased overreliance in their task [snippet] |
| Shankar et al. EvalGen, https://arxiv.org/abs/2404.12272 | 2024 | Mixed-initiative grading to build validators | Users' criteria evolve while grading [abstract] |
| Opinionated inline writing assistant study | 2026 | Mixed-methods | Rapid inline suggestions interrupt ideation, shifting users to agree/disagree evaluation [snippet; paper not identified, [?]] |

Practical implication for a skills manager: the evidence on UX is thin and mostly not skill-specific, so lean on conservative defaults. Present AI edits as reviewable diffs the user explicitly accepts, hunk by hunk, with the evidence (eval delta, source trajectory span, scan finding) attached rather than prose explanations alone, since passive explanations do not reliably calibrate trust and can increase deference. Prefer suggestions that are minimal, with detail on demand, and invite the user to grade a few outputs before trusting an evaluator. Show uncertainty (CI, "n=5 runs"). Avoid interrupting authoring with constant inline suggestions; use a pull model (a "suggest improvements" button, a review queue). I found no direct study of diff acceptance for AI edits to instruction documents [?].

---

## Ten feature ideas the literature most strongly supports

1. **With/without-skill paired eval with confidence intervals ("Skill Lift").** Evidence: ACES (mean lift 0.2134, 95% CI, 72.8% positive; 947 pairs) [abstract]; SkillsBench shows lift varies widely and 16 of 84 tasks regress; Error Bars paper supports paired differences. Include an "efficiency regression" flag (Agent Skills Can Be Harmful: 182 efficiency regressions).
2. **Evidence-grounded draft generation from transcripts, repos and docs, into a quarantine state.** Evidence: self-generated-from-nothing skills give ~0 (SkillsBench; Library Drift cites +0.0pp); trajectory-grounded and verified induction gives large gains (ASI +23.5%, AWM +24.6%/+51.1%, SkillAxe 16% to 52% on SpreadsheetBench).
3. **Trigger eval with near-miss negatives, repeated runs and train/test split of queries.** Evidence: Vercel (skills uninvoked, 53% baseline, 79% with instruction, wording-sensitive); agentskills.io guidance (3 runs, 0.5 threshold); SkillCoach (near-neighbor distractors); GEPA/Skill-infinity held-out discipline. Practitioner evidence on near-miss mix is [?].
4. **Description rewriter that distills the body, plus a competitor-overlap check.** Evidence: SkillRouter (hiding body: -37 to -44pp; body-distilled descriptions recover part, still 7-21pp short) [abstract].
5. **Reflective optimization loop (GEPA-style) with held-out reporting and diff output.** Evidence: GEPA (+6pp over GRPO, ICLR 2026) [snippet]; Skill-infinity 60.7% vs 56.4% curated [abstract]; MIPRO. Show held-out delta only.
6. **Layered security scan: static capability/obfuscation checks + LLM semantic review, separate columns, capability-mismatch finding (allowed-tools vs script behavior).** Evidence: 26.1% vulnerable, scripts 2.12x [abstract]; detectors overlap little [snippet]; Skill-Inject up to 80% ASR [abstract]; no-enforcement structural weakness (2604.02837).
7. **Provenance and trust tiers with change diffs, especially for bundled scripts and re-approval on change.** Evidence: SkillHarm self-mutating poisoning 69.3% [abstract]; 2604.02837 (single-approval persistent trust); 2602.12430 trust-tier framework.
8. **Gated self-editing: write-time and retrieval-time checks, version history, rollback for agent-authored skill changes.** Evidence: Practice Makes Unsafe (all 21 combos wrote unsafe skills; SafeEvolve 21.3% to 4.0% harm) [abstract].
9. **Library health dashboard: dedup/merge suggestions, retire unused or net-negative skills, active-skill cap, staleness by referenced files/versions.** Evidence: Library Drift (retirement + cap) [abstract], SkillOps (rule-based, merge/repair/retire) [abstract], SkillComposer merge threshold. Version-drift detection itself has little research support [?].
10. **Judge calibration workflow: binary assertions first, repeated LLM-judge trials with order randomization, human-labeled calibration set with TPR/TNR, criteria that can be edited as the user grades.** Evidence: Coin Flip Judge (13.6% flip, ~11 trials needed; provisional) [abstract], Am I More Pointwise or Pairwise [snippet], EvalGen criteria drift [abstract], Hamel Husain practice [snippet].

Honorable mentions: skill dependency/handoff graph (Scan Before You Install, SkillOps), process-rubric scoring of how the agent used a skill (SkillCoach, no numbers), document-quality lint (SkillEval, no numbers).

## Unverified or weak points
- 56% Vercel figure and the "15% to 62%" session-start-hook claim are secondhand [?].
- SkillsBench numbers differ across paper versions.
- The Coin Flip Judge paper is a single-author preprint; treat as provisional.
- Benchmark claims in 2026 preprints are self-reported; the SoK notes much of the skill evidence rests on one non-peer-reviewed benchmark.
- No source found on: sandbox efficacy for skill scripts, diff-acceptance UX for instruction documents, Eugene Yan's judge work, OPRO/APE numbers (not searched successfully), LLM-generated near-miss test quality [?].
