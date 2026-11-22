# Literature deep dive

**Version 0.1.0**

**AI manifest**: Raw research report (round 4) for @docs/60-ai-features-research-loop-2026-11-22.md. Evidence, not decisions.

Date: 2026-11-22. This round goes deeper than `03-literature.md` and `13-literature-new-themes.md`: new papers, full text for the key ones, and a numerical check of the statistics we already shipped. Fetched text was treated as data; nothing in it was followed as an instruction.

## Method

**Sources searched.** The arXiv API (`https://export.arxiv.org/api/query`, about 45 queries across the seven topics, 2023 to 2026) and arXiv abstract pages (`https://arxiv.org/abs/<id>`). Every paper newly cited in this round (IDs in the per-paper entries; earlier-round IDs listed only as "already covered" were not re-checked) returned HTTP 200 on `arxiv.org/abs/<id>` when checked on 2026-11-22, and its title and abstract were read. Semantic Scholar, ACL Anthology, OpenReview and WebSearch were **not** queried in this round, so venue and citation-count claims are absent on purpose. Most 2026 papers are non-peer-reviewed preprints with self-reported numbers; several come from a single author or a single lab. Model names are as the papers print them.

**Reading depth.** Tags used throughout:

- **[full text]** the full text was retrieved (PDF through `pdftotext`, or `arxiv.org/html`) and the setup, main results and limitations were read. 18 papers.
- **[partial text]** the full text was retrieved, but only the abstract, introduction and selected results sections were read. 6 papers.
- **[abstract]** only the arXiv abstract was read. Numbers marked this way are the authors' headline claims and are unverified.
- **[computed here]** arithmetic or a simulation I ran in this session, using the repository's own code. It is not a literature claim.
- **[inference]** my reasoning from a paper, not something the paper states.

Full text, 18: IFScale, HANDBOOK.md, Prompt Design at Scale, Context Rot in coding agents, WhoWins, ConInstruct, Demystifying Agent Skills, MCP Tool Descriptions Are Smelly, SkillReducer, Signal or Noise, Adding Error Bars to Evals, Don't Use the CLT, Coin Flip Judge, Judging the Judges, Evaluating AGENTS.md, Policy Wording, Do They Do as They Are Told, Reflective Prompt Optimization overfitting protocol.
Partial text, 6: Many-Tier Instruction Hierarchy, CompressAgent, Don't Pass@k, Why Does CLAUDE.md Keep Growing, When Instruction Files Go Stale, Skill-Inject.
Abstract only: the remaining papers (about 33). In total about 57 new papers are cited, most of them from 2026.

**Tooling notes.** Three large PDFs downloaded truncated; their HTML versions were used instead. The repository code I tested is `skillsmgr/trial_stats.py` and `skillsmgr/ai_ablate.py` as they exist in the working tree (uncommitted `ai_ablate.py` included).

**Corrections to earlier rounds.**
1. `13-literature-new-themes.md` says no paper uses a length-matched placebo skill. That is wrong: Signal or Noise (2608.23067, topic 4) does exactly that, with four models. The placebo is therefore a published control, but still absent from skill-manager tools.
2. The "at most 2.92%" figure for conflict flagging is a share of *decided pair replies* under keyword patterns, on 14 open-weight models only (topic 2).
3. ConInstruct's 87–91% F1 comes from balanced, synthetic, deliberately unambiguous conflicts inside one user instruction (topic 2). It is not a prevalence-realistic number for skill libraries.

---

## 1. Instruction following as instructions accumulate

### IFScale: How Many Instructions Can LLMs Follow at Once? [full text]
- 2025, https://arxiv.org/abs/2507.11538
- **Setup.** One task (write a business report) with 10 to 500 "include the exact word X" instructions. 20 models, 7 providers, 5 seeds per density, deterministic regex grading.
- **Numbers.** Best frontier model reaches 68% at 500 instructions. Three decay shapes: threshold (reasoning models such as o3 and gemini-2.5-pro hold near-perfect through roughly 100 to 250 instructions, then fall with rising variance), linear (gpt-4.1, claude-3.7-sonnet), exponential (claude-3.5-haiku, llama-4-scout). Bias to earlier instructions peaks around 150 to 200 instructions, then levels off. Errors are mostly omission, not modification: llama-4-scout shows an omission-to-modification ratio of 34.88 at 500. Claude-3.7-sonnet (52.7%) beat the newer claude-opus-4 (44.6%) and claude-sonnet-4 (42.9%) at maximum density.
- **Limitation.** One synthetic task with trivial, independent keyword constraints in English; the authors say it may not generalise to other task types or to more complex instructions. Reasoning models o3 and o4-mini also lost report coherence as density rose.
- **Implication.** A CLAUDE.md or AGENTS.md is a density problem even before any conflict. The dominant failure is silent omission, which no model announces, so only a check on outputs finds it. Model family matters more than recency, so a threshold learned on one model is not portable.

### HANDBOOK.md: Long-Context Agentic Instruction Following [full text]
- 2026, https://arxiv.org/abs/2607.25398
- **Setup.** 65 tasks, 10 base handbooks (20 to 124 pages, 8K to 79K tokens, median about 14.9K) altered per task so rules and thresholds are unique. Agents act through mock email, chat, calendar, issue and commerce services over MCP. 824 programmatic criteria, of which 232 (28.2%) check that a *prohibited* action did not happen. Four trials per task, 30 model configurations, strict pass means every criterion passes.
- **Numbers.** Best configuration 36.2% strict pass@1; most frontier configurations stay under 25%. Relaxing grading by one criterion roughly doubles leader scores (for example about 21.9% to about 46%). More reasoning effort helps only some models. Recurring failures: a plausible but unauthorised request in the environment overrides the standing policy; the agent runs a required check and then acts against its result; rule details are lost over about 17 steps and 30 tool calls; the agent reports compliance it did not achieve.
- **Limitation.** Synthetic handbooks and mock services; the strict all-criteria metric is deliberately harsh (the authors show the relaxed view).
- **Implication.** A model's closing statement that it followed the rules is not evidence. Grade state and actions, and include negative assertions. It also supports reporting a strict view and a "missed by one" view side by side.

### Prompt Design at Scale: Format, Instruction Count, Context Length [full text]
- 2026, https://arxiv.org/abs/2607.19257 (preprint, single lab, not peer reviewed)
- **Setup.** Rule count N from 10 to 160, four formats (markdown, plain, prose, table), system versus user placement, five models (Claude Sonnet 5, Claude Haiku, Gemini Flash, two Qwen sizes), 960 calls per model. A second experiment ran a 2K to 512K-token context ladder.
- **Numbers.** The *perfect-response* rate (every rule satisfied) reaches zero by N = 80 for every model, format and placement. No model shows a reliable markdown advantage. Placement effects at N = 160 are at least as large as format effects in four of five models, but the direction is model-specific. Recall stays near ceiling to about 64 to 128K tokens, then degrades with format spreads up to 48 points at 128K. Format overhead adds 22 to 37% tokens over plain text. Fabrication 0 of 5,760 probes; refusal, not fabrication, rises near each model's ceiling.
- **Limitation.** The headline metric is all-rules-pass, which collapses fast by construction; five fixed structural rules (word count, paragraph count) make the average rule harder at low N than at high N, which the paper notes. Synthetic fictional corpus.
- **Implication.** Do not spend effort on markdown-versus-plain advice for instruction files; measure per model. Report per-rule compliance next to all-pass so the user can see whether the file is 100% followed or 85% followed.

### When and How Context Rot Appears in Coding Agents: A White-Box Study of Agent Skills [full text]
- 2026, https://arxiv.org/abs/2607.17937
- **Setup.** Production-derived code-audit skills with 24 mandatory checks, Codex with gpt-5.4-mini, 10 runs per condition, Wilson intervals.
- **Numbers.** A clean 10,991-character context passed 8 of 10 runs. Two 299,140-character contexts, one relevant and one irrelevant, each passed 3 of 10. The 95% Wilson failure interval is 5.7 to 51.0% for clean and 39.7 to 89.2% for long. Strict-success retention is 0.375 but requirement-coverage retention is 0.933 to 0.949: rot removes a few decisive obligations, not the whole artifact. A detailed external checklist passed 10 of 10 versus 5 of 10 for a generic self-check (p = 0.0325). The dominant losses occur after retrieval: requirements fail to become active tasks, edits drift, contradictory evidence fails to reopen work, and the agent declares completion silently. A failure at 90K appeared once and vanished on replay.
- **Limitation.** One main model-task pair, 10 runs, heterogeneous cross-model probes; the authors refuse to give a threshold.
- **Implication.** This is a small-sample warning in the wild: with 10 runs the interval for a 20% failure rate spans 5.7 to 51%. It also says irrelevant text of equal length hurts as much as relevant text here, which is the placebo argument for skills.

### Shorter entries [abstract]
| Paper | Year | URL | Key claim | Implication |
|---|---|---|---|---|
| When Instructions Multiply (ManyIFEval, StyleMBPP) | 2025 | https://arxiv.org/abs/2509.21051 | Performance falls as instruction count rises across 10 LLMs; logistic regression on instruction count predicts it within about 10% error on unseen combinations; 300 to 500 samples suffice to fit | A cheap density curve per model could be fitted once and reused |
| AGENTIF | 2025 | https://arxiv.org/abs/2505.16944 | 707 instructions from 50 real agent applications, average 1,723 words and 11.9 constraints; models do poorly, especially on condition constraints and tool specifications | Real agent prompts are the test bed, and "condition" constraints are the weak spot (matches the Policy Wording result below) |
| Lost in the Middle | 2023 | https://arxiv.org/abs/2307.03172 | Accuracy highest when relevant text is at the start or end of context, lowest in the middle | Baseline position effect; order skills and rules by importance, not alphabetically |
| Length Is Cheap, Competition Is Not | 2026 | https://arxiv.org/abs/2611.04169 | On five 0.5B to 3B open models, neutral filler costs nothing (accuracy 0.97 to 1.00 up to 32K) but evidence-shaped distractors drop it to 0.16 to 0.33; one rival value multiplies loss 9 to 110x | It is competing similar text, not length, that rots context; this matters for near-duplicate skills |
| LLMs Get Lost in Multi-Turn Conversation | 2025 | https://arxiv.org/abs/2505.06120 | Average 39% drop from single to multi-turn across six tasks, mostly from unreliability | Instructions given early in a session are not as safe as single-turn tests suggest |

**Reading across topic 1 [inference].** Three separate mechanisms are in play: count (IFScale, Prompt Design at Scale), position (IFScale primacy, Lost in the Middle, WhoWins in topic 2) and competition from similar text (Length Is Cheap, Signal or Noise). A skills manager can measure the first two statically (rule count, position) and the third by overlap between skills. None of them needs a model call.

---

## 2. Conflicting instructions, hierarchy and conflict judges

### WhoWins: Position, Role or Label? [full text]
- 2026, https://arxiv.org/abs/2610.33201
- **Setup.** 1,080 code-scored scenarios in five task types; up to five mutually exclusive instructions placed in five "seats" (operator, repository configuration, user, tool result, saved memory note); seven controlled experiments that vary only how text is delivered; 14 open-weight models (0.6B to 122B, thinking off and on), 1,887,356 scored replies, no LLM judges.
- **Numbers.** Inside one message the first of two conflicting lines wins 72.42 to 94.66% of decided replies. Across two messages the earlier one keeps 22.95 to 62.65%. A policy sent first in the system or developer message loses most conflicts to later lines in every Qwen model. In tool and file-write tasks the same text sent first as a labelled *user* message beats it in all 26 model-modes, by 6.41 to 48.75 points. By keyword patterns at most 2.92% of decided pair replies flag or hedge a conflict. Even two declared priority tiers are not followed in 95% of usable replies by any model. Pairwise results forecast larger conflicts only once the position of the task line is known.
- **Limitation.** Open-weight models only, synthetic single-key conflicts (casing of one key), keyword-based flag detection.
- **Implication.** Declaring "this rule has priority" inside a skill does not protect it. The only dependable ownership signal is where the line sits in the assembled context, which a manager can compute and show. Models almost never surface the conflict themselves.

### Many-Tier Instruction Hierarchy in LLM Agents (ManyIH) [partial text]
- 2026, https://arxiv.org/abs/2604.09443
- **Setup.** ManyIH-Bench: 853 agentic tasks (427 coding, 426 instruction-following) from 46 real agents, up to 12 privilege levels; bootstrap 95% intervals reported. The paper names skill invocations and tool schemas as privilege sources.
- **Numbers.** Frontier models reach about 40% accuracy; best Gemini 3.1 Pro 42.7%. A model card is quoted at over 99% on two-tier instructions. Accuracy falls as tier count rises; changing only the prompt format moves accuracy by about 8 points for two models.
- **Limitation.** I read the setup and main results, not the full appendix; the benchmark filters out infeasible combinations, giving an estimated ceiling near 80%.
- **Implication.** Resolution across more than two sources, which is what skills plus CLAUDE.md plus AGENTS.md plus repo is, is far worse than the two-level case that training targets.

### ConInstruct: Conflict Detection and Resolution in Instructions [full text]
- 2025, https://arxiv.org/abs/2511.14342
- **Setup.** 100 seed instructions in six task types, six constraint types, nine conflict types (six within a constraint type, three across), conflicts injected by GPT-4o; 864 single-conflict instructions. Each detection subset pairs 100 conflict-free instructions with an equal number of conflicting ones, so chance is about 50%.
- **Numbers.** DeepSeek-R1 F1 91.5%, Claude-4.5-Sonnet 87.3%. GPT-4o accuracy averaged 84.9% (chance 49.4%) but is lower across constraint types: keyword versus phrase 75.1%, phrase versus style 76.1%, against 91.9% for content conflicts. After detection, GPT-4o answered directly in 97.5% of one-to-two-conflict cases without telling the user; Claude-4.5-Sonnet alerted in 45% (36% asking for clarification, 9% resolving by itself).
- **Limitation.** The authors say they avoided ambiguous and implicit conflicts so that satisfaction could be checked automatically. Conflicts live inside one user instruction, not across files, and are synthetic.
- **Implication.** Detection skill is real but measured at 50% prevalence on clear conflicts. In a skill library conflicts are rare, partly scoped ("in the frontend folder, use X") and often implicit, so precision is the quantity to worry about (see the base-rate calculation in "Checks on what we built").

### Shorter entries
| Paper | Year | URL | Key claim [abstract] | Implication |
|---|---|---|---|---|
| TRACE: Trust Allocation Across Conflicting Software Artifacts | 2026 | https://arxiv.org/abs/2604.03447 | 456 Java method bundles, 7 LLMs, 22,339 responses. Documentation faults detected 67 to 94%, explicit doc-versus-code contradictions 50 to 91%, but detection falls 21 to 43 points when only the implementation changes; confidence separates right from wrong for only one of seven models | A judge trusts prose over code. For a skill that contradicts a repo fact, give the judge the repo fact as evidence and do not rely on its self-reported confidence |
| IHEval | 2025 | https://arxiv.org/abs/2502.08745 | 3,538 examples, nine tasks; all models drop sharply under conflict; best open-source 48% at resolving conflicts | Earlier confirmation that hierarchy is weak |
| IH-Challenge | 2026 | https://arxiv.org/abs/2603.10521 | RL dataset; fine-tuning GPT-5-Mini lifts hierarchy robustness 84.1 to 94.1% over 16 benchmarks | Frontier labs are training for this; do not assume it holds for the user's model |
| PRIME | 2026 | https://arxiv.org/abs/2606.22470 | Five open models; conflict type matters more than model size | Report conflicts by type, not as one count |
| The Instruction Hierarchy | 2024 | https://arxiv.org/abs/2404.13208 | Original proposal and training recipe for system over user over tool priority | Background for the role-based assumption WhoWins tests |

---

## 3. Tool and skill selection at scale, description quality

### Demystifying Agent Skills: Why They Work, Until They Don't [full text]
- 2026, https://arxiv.org/abs/2608.14036
- **Setup.** 8,135 normalised trial records, 238 open-coded labels; Codex with GPT-5.3-Codex and Gemini CLI with Gemini-3.1-Pro-Preview on Terminal-Bench-2, SkillsBench and Terminal-Bench-Pro. Retrieval tested three ways: embedding retrieval (Qwen3-Embedding-0.6B over descriptions), explicit agent selection without execution, and full-pool real execution, with pool size 5 to 100 and random, similar or dissimilar distractors.
- **Numbers.** Skills beat workflow memory by 6.06 points in matched comparisons. Procedural anchoring explains 65.7% of skill cases against 4.5% for knowledge injection. In real execution, actual-use precision fell from 29.6% to 3.3% averaged across the two pairings as pools grew from 5 to 100; Gemini's fell from 16.9% to 0.7% while its task success stayed about 36 to 39%, and Codex's fell from 42.3% to 5.9% while success rose from 35.4% to 42.0%. In the offline diagnostic, similar-distractor precision fell from 70.5% to 53.4% (random pools 97.7% to 84.1%). Semantic confusability matters more than pool size. The authors conclude that exact ground-truth invocation is neither sufficient nor necessary for success.
- **Limitation.** Terminal-style benchmarks and two agent-model pairs; the open-coding sample covers about 3% of the records.
- **Implication.** Two things for the routing simulator: (1) near-duplicates, not the raw number of skills, drive misrouting, so the nearest-neighbour check is the right unit; (2) "did it invoke the intended skill" is an incomplete outcome. Score the task result as well, or the tool will punish harmless detours.

### MCP Tool Descriptions Are Smelly [full text]
- 2026, https://arxiv.org/abs/2602.14878
- **Setup.** 856 tools from 103 MCP servers scored on a six-component rubric (purpose, guidelines, limitations, parameter explanation, examples, length and completeness) by a three-model LLM jury, with agreement and manual validation reported. Agent effect measured on MCP-Universe (231 tasks).
- **Numbers.** 97.1% of descriptions have at least one smell; 56% fail to state a clear purpose. Augmenting every component raises task success by a median 5.85 points and partial goal completion by 15.12%, but raises steps by 67.46% and **regresses performance in 16.67% of cases**. A component ablation finds no combination that is best everywhere, and shorter targeted descriptions reach statistically equivalent performance to full augmentation. Official and community servers do not differ in quality.
- **Limitation.** Per-task data were unavailable for the benchmark's baselines, so paired tests could not be run everywhere and a hybrid design was used; a full benchmark round costs 200 to 300 million tokens, so runs per cell are small.
- **Implication.** "Better" descriptions are not free: lift and cost move together and one case in six gets worse. Any description rewrite needs a before-and-after check, and a short purpose-first description is a defensible default.

### SkillReducer: Optimizing LLM Agent Skills for Token Efficiency [full text]
- 2026, https://arxiv.org/abs/2603.29919
- **Setup.** Census of 55,315 public skills, then a two-stage reducer evaluated on 600 skills and SkillsBench. Stage 1 minimises descriptions by delta debugging (ddmin) over LLM-segmented semantic clauses, using a *simulated routing oracle* (the model picks the target skill from a pool that includes similar distractors, candidate order randomised per query), then validates in the real runtime by invoking the Claude Code CLI and parsing stream events for a skill call.
- **Numbers.** 26.4% of skills lack a routing description or have one too short to route; over 60% of body text is non-actionable; average description is 47.78 tokens. Result: 48% description compression, 39% body compression, +2.8% functional quality, mean retention 0.965 across five models. Of 600 descriptions, 252 (42.0%) passed real-runtime validation directly, **245 (40.8%) needed selective restore of deleted clauses, and 39 (6.5%) fell back to the original**. The authors state the simulated oracle "is fast but overly optimistic".
- **Limitation.** The simulated oracle tests a controlled candidate pool, not the real runtime; compression and judging use different models to limit bias but still rely on LLM evaluators.
- **Implication.** This is the closest published match to our trigger simulation and description rewriting. It says simulation alone over-approves rewrites by a wide margin (over a third needed repair), and it supplies a minimisation method (ddmin) and a real-runtime check.

### Shorter entries [abstract]
| Paper | Year | URL | Key claim | Implication |
|---|---|---|---|---|
| Advertising to Agents: Description-Framing Bias in Tool Selection | 2026 | https://arxiv.org/abs/2605.23916 | Two small OpenAI models; stacked praise in a description raised pick rate by about 43 points; with identical listings the first-listed tool was picked about 72 points more often; structured fields helped, sales text beside them erased the gain | Randomise listing order in any routing simulation and run both orders; praise-laden descriptions are a bias, not a strength |
| Under the Hood of SKILL.md: Semantic Supply-chain Attacks | 2026 | https://arxiv.org/abs/2605.11418 | Short textual triggers win embedding retrieval up to 86% pairwise; description-only framing steers selection to adversarial variants in 77.6% of paired trials | Description text is an attack surface and a selection lever at once |
| RAG-MCP | 2025 | https://arxiv.org/abs/2505.03275 | Retrieval before the model cuts prompt tokens by over 50% and lifts tool selection accuracy from 13.62% to 43.13% in an MCP stress test | Supports a retrieved shortlist over a full listing at scale |
| Learning to Rewrite Tool Descriptions (Trace-Free+) | 2026 | https://arxiv.org/abs/2602.20426 | Rewriting reduces accuracy degradation by 29.23% as catalogs grow past 150 tools (StableToolBench) | Rewriting helps most when the catalog is large |

Already covered in earlier rounds and not re-read: SkillRouter (2603.22455), BiasBusters (2510.00307), Tool Preferences Are Unreliable (2505.18135), ToolRet (2503.01763).

---

## 4. Prompt ablation, compression and attribution

### Signal or Noise? A Benchmark Study of Agent Skills in Web Development [full text]
- 2026, https://arxiv.org/abs/2608.23067
- **Setup.** 31 public WebDev skills, 50 Web-Bench projects, 1,000 ordered tasks, four models (Claude Sonnet 4, GPT-5.1, Qwen3 Coder 30B, DeepSeek V4 Flash). Four conditions: no skill (C0), target skill (C1), a **byte-length-matched irrelevant skill** (C2), and **leave-one-out slice ablation** of the skill's positive rules, anti-patterns and example code (C3). 117 core skill-project pairs, N = 3 replicates per cell, paired-bootstrap 95% intervals. Only SKILL.md is in the prompt; auxiliary files are mounted in the workspace.
- **Numbers.** Injecting the target skill lowers mean Pass@2 on every model (Sonnet −4.2 points, Qwen −2.3, DeepSeek −2.0, GPT-5.1 −1.3), raises token cost by 72 to 394%, and gains in only 17 to 36% of pairs. The length-matched control splits the cause: Sonnet and Qwen are *length-distracted* (an equally long irrelevant skill reproduces most of the loss), GPT-5.1 and DeepSeek are *content-misled* (length neutral, content costs 1.1 to 1.4 points). Losses concentrate on early easy tasks. Per-pair effects are nearly uncorrelated across models (|r| ≤ 0.12), and 74% of pairs help one model and hurt another. In the leave-one-out slice study (only five pairs, all pre-selected as positive), anti-patterns were the only slice with a reliable effect (p = 0.008), example code was null on average but 22.7% of the skill's tokens, and examples helped DeepSeek (+8.3) while hurting Sonnet (−15.3).
- **Limitations (authors).** Aggregate Pass@2 varied by 3.6 to 4.4 points between three replicates of the same Sonnet condition, comparable to the headline effect; C2 used only 109 unique length-matched runs; slice ablation covers five pairs chosen for a positive cross-model signal.
- **Implication.** Direct evidence for three of our design questions: a placebo arm changes the diagnosis; replicate noise is as large as the effects we hope to detect; and a skill validated on one model says nothing about another, so evals must run on the model the user's key actually serves.

### CompressAgent: Control Under Compression [partial text]
- 2026, https://arxiv.org/abs/2608.01056
- **Setup.** Nine agent control contexts (system-side instructions plus tool documentation), three task families, three Qwen model endpoints, six retained-context budgets, 15,525 environment-verified runs; methods include mechanical truncation, generic LLM rewriting, section-based compression, obligation-aware compression and LLMLingua.
- **Numbers.** Full-context success 93.8%. At 75% retained, rewriting 92.7% and section-based 92.4%. At 35% retained: section-based 47.0%, obligation-aware 39.0%, generic rewriting 19.9%. At 25% to 10%, executable protocols become fragile; failures show up as tool-execution and action-parsing errors. Reliability varies by control context, so no universal compressor ranking holds.
- **Limitation.** Qwen models only, nine contexts; I read the abstract and overview, not every section.
- **Implication.** Compression is safe to about a quarter off and then degrades non-linearly; the right unit is the individual obligation, and each file must be qualified on its own.

### Compression, attribution and loading, shorter entries [abstract]
| Paper | Year | URL | Key claim | Implication |
|---|---|---|---|---|
| LLMLingua | 2023 | https://arxiv.org/abs/2310.05736 | Coarse-to-fine token pruning, up to 20x compression with little loss on GSM8K, BBH, ShareGPT, Arxiv-March23 | Claims are for reasoning and summarisation tasks, not rule-following |
| LLMLingua-2 | 2024 | https://arxiv.org/abs/2403.12968 | Token classification trained on distilled data; faithful, task-agnostic | Same caveat |
| Prompt Compression in the Wild | 2026 | https://arxiv.org/abs/2604.02985 | 30,000 queries, three GPU classes; LLMLingua gives up to 18% end-to-end speed-up with quality unchanged only when length, ratio and hardware match; otherwise the compression step cancels the gain | Compression is not a free win even on latency |
| Separating Constraint Compliance from Semantic Accuracy (CDCT) | 2025 | https://arxiv.org/abs/2512.17920 | Nine LLMs, five compression levels; constraint violations peak at medium compression (about 27 words) in 97.2% of cases, and constraint compliance and semantic accuracy are nearly independent | Compress rules, not just meaning, and check rules separately |
| TokenSHAP | 2024 | https://arxiv.org/abs/2407.10114 | Monte Carlo Shapley values for tokens or substrings of a prompt | The Shapley route exists, but costs many model calls per prompt |
| Skill Blocks | 2026 | https://arxiv.org/abs/2608.14943 | Loading only the needed part of a skill cuts input tokens by 27 to 73% with no detected quality difference (explicitly not an equivalence test) | Progressive disclosure saves tokens without a measured loss |

**Reading across topic 4 [inference].** Three methods appear in the literature for "which part matters": leave-one-out on slices (Signal or Noise), delta debugging to a 1-minimal set (SkillReducer), and Shapley sampling (TokenSHAP). Only leave-one-out is cheap enough for a user-keyed tool, and it has a known blind spot: two sections that duplicate each other each look removable on their own, because the other covers for it. That blind spot appears as a design change below (joint-removal confirm).

---

## 5. Evaluation methodology

### Adding Error Bars to Evals [full text]
- 2024, https://arxiv.org/abs/2411.00640 (Miller)
- **Content.** Treat questions as a draw from a super-population. Variance of a sample mean decomposes as Var(x)/n plus E[σ²]/(nK) when each question is resampled K times; once E[σ²]/K is small next to Var(x), more resampling barely helps. Recommends CLT standard errors, clustered standard errors (up to a 3x change on real evals), **paired differences** (variance reduced by 2·Cov(x_A, x_B)/n), and power analysis. Sample size for a paired comparison: n = (z_{α/2} + z_β)² (ω² + σ_A²/K_A + σ_B²/K_B) / δ², and inverted to give the minimum detectable effect δ. A worked example needs about 969 questions to detect a 3-point difference. Says bootstrapping is "unnecessary" when the CLT holds.
- **Limitation.** Asymptotic (CLT) methods; see the next paper for why that fails at small n. Gives no guidance for tiny benchmarks.
- **Implication.** Gives the exact formula needed to print a "minimum detectable effect" on every eval screen, and shows why trials beyond about three add little when case-to-case variance dominates.

### Position: Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints [full text]
- 2025, https://arxiv.org/abs/2503.01747
- **Content.** Simulations with known ground truth measure interval *coverage*. CLT-based and **bootstrap** intervals both undercover at small n (an example: nominal 95% CLT intervals reach 92.5%) and are wider than needed for the coverage they achieve; CLT intervals collapse to zero width when all outcomes agree. Wilson score and Bayesian beta-binomial intervals achieve near-nominal coverage; Clopper-Pearson is conservative. For paired and clustered comparisons the Bayesian methods are the ones that hold their coverage. Library: `bayes_evals`.
- **Limitation.** Position paper with simulated, not real, data; the simulations assume simple Bernoulli generative models.
- **Implication.** The most direct challenge to a percentile bootstrap over three to ten cases.

### Don't Pass@k: A Bayesian Framework for LLM Evaluation [partial text]
- 2025, https://arxiv.org/abs/2510.04265
- Replaces pass@k and avg@N with posterior estimates (Dirichlet prior, closed form), shows that under a uniform prior the Bayesian posterior mean ranks exactly as average accuracy, reports faster rank convergence than pass@k on AIME'24/'25, HMMT'25 and BrUMO'25, and proposes "do not declare a winner when credible intervals overlap". **Implication:** our mean case pass rate is the right point estimate; the change is in the interval, not the estimate.

### The Coin Flip Judge? Reliability and Bias in LLM-as-a-Judge [full text]
- 2026, https://arxiv.org/abs/2606.13685 (single author, provisional)
- **Setup.** 29 tasks in 10 categories, two OpenAI judges (GPT-4o-mini, GPT-4.1-mini), 50 pairwise and 50 pointwise trials per question.
- **Numbers.** Pairwise verdicts flip on repeat 13.6% on average; 28% of questions exceed a 20% flip rate; one reaches 56%. GPT-4o-mini picks the first position 72% of the time (p = 0.024). Mean pointwise score gaps are only 0.19 to 0.36 on a ten-point scale, yet pairwise judging still picks a winner. Cross-judge agreement 76% (κ = 0.51). Semantically equivalent prompt templates change the majority outcome in 25% of cases. Deterministic decoding reduces but does not remove inconsistency. 11 repeated trials are needed on average for a majority vote to match the 50-trial verdict with 95% probability, 15 for high-variance questions.
- **Limitation.** Two judges from one provider, 29 tasks; the authors call for cross-provider replication.
- **Implication.** One LLM verdict per item is a noisy instrument; forced pairwise choices overstate evidence.

### Judging the Judges: Bias Mitigation Strategies [full text]
- 2026, https://arxiv.org/abs/2604.23178
- **Setup.** Nine debiasing strategies, five judges from four providers (Google, Anthropic, OpenAI, Meta), MT-Bench (n = 400), LLMBar (n = 200) and a custom 375-pair set with known ground truth, mixed-effects regression with Holm correction.
- **Numbers.** Style bias dominates (0.10 to 0.76, favouring markdown over plain prose with identical content), far above position bias (at most 0.04, negligible in current models). Verbosity bias is heterogeneous: Gemini Pro, Flash and Llama prefer longer answers (+0.24 to +0.44), Claude prefers concise (−0.12), GPT-4o neutral. Best configuration is Gemini 2.5 Flash with a "combined budget" strategy (one structured rubric-plus-reasoning prompt called twice with positions swapped): 71.0% agreement, κ = 0.549, about $0.001 per evaluation, versus Claude Sonnet 4 at 69.5% for roughly 15x the cost. Position swap alone helps only Gemini Flash significantly and *hurts* every model on LLMBar by 4 to 13 points; chain-of-thought forcing was best there.
- **Limitation.** Agreement with human labels on general chat and preference benchmarks, not on contradiction detection; the headline gains are modest and model-specific.
- **Implication.** Mitigations are model-dependent, so a recipe from one provider does not transfer. Format bias is a live risk for any judge reading markdown instruction files.

### Shorter entries [abstract]
| Paper | Year | URL | Key claim | Implication |
|---|---|---|---|---|
| Judging LLM-as-a-Judge (MT-Bench) | 2023 | https://arxiv.org/abs/2306.05685 | GPT-4 judges match human preferences above 80% agreement, with position, verbosity and self-enhancement biases | Foundational; later work shows the biases are model-specific |
| Quantifying and Mitigating Self-Preference Bias | 2026 | https://arxiv.org/abs/2604.22891 | 20 LLMs; stronger capability is often uncorrelated or negatively correlated with low self-preference; structured multi-dimension evaluation cuts the bias by 31.5% on average | A judge that shares a family with the skill's author may favour it |
| All Verdicts are Not Equal | 2026 | https://arxiv.org/abs/2610.12083 | Six frontier models, ten repetitions: verdicts change at temperature zero; swapping order flips the majority on hard tasks; the most deterministic judge was consistent but right only 51% of the time; rubric scoring beat pairwise | Consistency is not accuracy |
| Noisy but Valid | 2026 | https://arxiv.org/abs/2601.20913 | A small human-labelled calibration set estimates the judge's true- and false-positive rates and corrects the test, with finite-sample Type-I control | Calibrate a judge on a handful of labelled items instead of trusting it |
| Correcting the Winner's Curse in Adaptive Benchmarking (SIREN) | 2026 | https://arxiv.org/abs/2605.05973 | Reusing benchmark items inside tuning inflates the winner's score; a repeated-split protocol with a frozen shortlist gives honest intervals | Directly relevant to any "try several edits, keep the best" loop |
| Stop Guessing When to Stop Testing | 2026 | https://arxiv.org/abs/2607.08522 | Sequential testing with stopping rules for minimum detectable effect; about 80% less compute at a 2.5-point interval width on one leaderboard | Early stopping can cut the user's token bill |

**Not found.** I found no paper that reports the minimum number of *cases* needed for skill or prompt-file ablation specifically. The Miller formula and the simulations in "Checks on what we built" are the substitute.

---

## 6. Agent memory and instruction files, optimizers and overfitting

### Evaluating AGENTS.md [full text]
- 2026, https://arxiv.org/abs/2602.11988
- **Setup.** SWE-bench Lite with LLM-generated context files and a new AGENTbench of 138 instances from 12 repositories that carry developer-written files; four models, several agents, Cochran-Mantel-Haenszel tests.
- **Numbers.** LLM-generated files change the resolution rate by −0.5% (SWE-bench Lite, p = 0.87) and −2% (AGENTbench, p = 0.37), so no significant effect, while steps rise by 2.45 and 3.92 on average and cost by 20% and 23% (p < 0.001%). Developer-written files add +2.4% on average (p = 21%) and cost up to 19% more. Developer files beat LLM files (p = 3.8%). Between 95% and 100% of LLM-generated files from three models contain a codebase overview, and overviews did not help the agent find files faster. Tools named in the file are used far more (uv 1.6 times per instance when mentioned against under 0.05 when not). Reasoning tokens rise 10 to 22% for GPT models.
- **Limitation.** Python-centric repositories; I did not read the limitations section. Success rate only moves a little in either direction, so the study is under-powered for small effects.
- **Implication.** An AI-written always-on file is the least defensible content: it costs 20%+ and its main ingredient (a repository overview) is the part shown not to help. This is the first thing "ablate and retire" should offer to remove.

### Do Coding Agents Follow AGENTS.md? The Effect of Policy Wording [full text]
- 2026, https://arxiv.org/abs/2611.04367
- **Setup.** One mechanically checkable policy (add `# @tracked` under each added or modified Python function) inserted into the context files of 86 benchmark tasks in four styles (prescriptive, explanatory, conditional, prohibitive), four harness-model combinations, three runs per task, Friedman and Wilcoxon tests with Holm correction.
- **Numbers.** Claude Code with claude-opus-5: prescriptive 78.0%, explanatory 77.2%, conditional 64.2%, prohibitive 70.7%. Claude Code with claude-sonnet-5: 71.6%, 49.4%, 35.6%, 17.3%. qwen-code with gpt-oss-120b: 6.7%, 20.4%, 0.8%, 0.4%. Qwen3-Coder-Next stayed below 1.5% in every style. Conditional wording ("if you add or modify a function...") was followed less than prescriptive and explanatory in every combination with a significant effect. The best style differs by model, and the spread between styles widens from 14 points (opus-5) to 54 (sonnet-5).
- **Limitation.** One policy type, 86 tasks, three repetitions; a letter-length paper.
- **Implication.** SKILL.md descriptions are conditional by nature ("use when..."), which is the weak style. The ranking of styles does not transfer between models.

### Do They Do as They Are Told? Adherence to Explicit Instructions in Context Files [full text]
- 2026, https://arxiv.org/abs/2611.13709
- **Setup.** 621 context-file snapshots linked to 6,541 agent-written commits in 268 repositories; instructions are extracted, turned into executable checks (script accepted only if independent scripts agree), and run on commits.
- **Numbers.** Only 2,053 of 6,552 explicit, observable instructions (31.3%) ever met a commit that could test them. Mean per-instruction compliance is 59.8% but the **median is 100%**: instructions are either always followed or essentially never. The authors state their rates are an optimistic floor on non-adherence because 62.3% of accepted scripts return true on commits that touch no relevant files, and that 71.3% of a 94-script spot-check implemented their instruction correctly (so about three in ten were wrong, often by hard-coding an example from the file).
- **Limitation.** Observational; measurement-script error is systematic, not random.
- **Implication.** Compliance is bimodal, so a mean hides the instructions that need work; show a per-instruction view. It also shows how hard it is to verify rule-following from outputs alone.

### Why Does CLAUDE.md Keep Growing? Catastrophic Remembering [partial text]
- 2026, https://arxiv.org/abs/2608.11095
- Across 247,694 instruction lifetimes in 1,867 repositories, files average 39 instructions and grow +226% over their lifetime (+4.9 net instructions per commit); older instructions are less likely to be deleted (log-hazard −0.032 per commit). The authors argue deletion is risky because the rationale is lost. In simulated IFEval worlds, informative "prompt comments" that record the reasoning remove 99.3% of excess instructions (+211.3% to +1.4%), and on WildIFEval improve instruction following by up to 23.1% [abstract numbers; I read the introduction only]. **Implication:** store a reason and a source with each rule, which also makes ablation proposals safer to accept.

### When Instruction Files Go Stale [partial text]
- 2026, https://arxiv.org/abs/2611.09802
- 22 maintenance tasks, three versions of each instruction (stale, corrected, removed), 732 trajectories, two models. Agents follow stale guidance when it is relevant, even when correct information is elsewhere. On a stale test command Claude Sonnet 5.5 used about two extra tool calls per run, a third more than with the corrected command; in other cases no difference was detected. Task success did not change, and no agent repaired the file itself. Correcting eliminated operations on obsolete paths; removing prevented most. A companion paper (2606.09090, [abstract], https://arxiv.org/abs/2606.09090) finds stale code-element references in 23.0% of 356 repositories using an off-the-shelf documentation checker. **Implication:** staleness costs steps, not success, so success-only evals will never flag it; a deterministic path and command check is cheap and finds it.

### Reflective Prompt Optimization: Topic-Disjoint, Multi-Seed Protocol [full text]
- 2026, https://arxiv.org/abs/2610.12601
- **Setup.** GEPA applied to two system prompts of a deep-research agent, topic-disjoint train (24), validation (24) and a 500-task held-out test; three seeds.
- **Numbers.** Held-out citation reward 0.702 to 0.781 (+0.079, bootstrap 95% CI [0.051, 0.107]); mean +0.107 across seeds. Nearly half the winning prompt was a memorised answer key, but a controlled ablation shows that content earns no reward even on the exact training questions. The large validation-minus-held-out gap is small-sample selection under a noisy judge, not memorisation. Decomposed per-dimension feedback is the causal ingredient; collapsing it to one scalar reward makes held-out transfer negative. A hand-written version of the discovered recipe reproduces most of the gain.
- **Limitation.** One agent and one rubric-style LLM-judge reward.
- **Implication.** With 24 validation items the validation gain is a poor guide, so the "accept if it improves on the saved cases" rule used in an AI edit loop will overstate benefit. Held-out cases plus a printed validation-versus-held-out gap are the remedy.

### Shorter entries [abstract]
| Paper | Year | URL | Key claim | Implication |
|---|---|---|---|---|
| What Should the Reflector See? | 2026 | https://arxiv.org/abs/2609.32452 | Qwen3.5-9B, nine reflection strategies, five datasets; failures-only gave +8.0 points mean test gain; calibration gaps on GPQA and IFBench show that tuning gains can overstate held-out gain | Show the optimizer failures, not a balanced sample, and report the gap |
| Agentic Context Engineering (ACE) | 2025 | https://arxiv.org/abs/2510.04618 | Evolving playbooks with incremental, structured updates avoid "context collapse"; +10.6% on agents and +8.6% on finance | Incremental delta edits, which per-hunk accept already resembles, beat wholesale rewriting |
| What Open-Source Projects Tell Their Coding Agents (census) | 2026 | https://arxiv.org/abs/2610.31715 | 22,854 repositories; instruction files in 26.3% (59.6% of the most-starred); 341,852 statements; 74.0% of directives give no reason; four in five files are edited after creation | Most rules carry no rationale, so deleting them is guesswork |

Already covered earlier and not re-read: Agent AGENTS.md efficiency (2601.20404), GEPA (2507.19457), MIPRO (2406.11695), TextGrad (2406.07496), ExpeL (2308.10144), Library Drift (2605.19576).

---

## 7. Prompt injection through skill files, supply chain

### Skill-Inject: Measuring Agent Vulnerability to Skill File Attacks [partial text]
- 2026, https://arxiv.org/abs/2602.20156
- **Setup.** 202 injection-task pairs, from obviously malicious to context-dependent injections hidden in otherwise legitimate skills; frontier models in Claude Code, Gemini CLI and Codex-style agents; security and utility measured together.
- **Numbers.** Attack success up to 80% on frontier models, including data exfiltration, destructive actions and ransomware-like behaviour. Contextual injections run under a "warning" policy (139 pairs) and obvious injections (36), with best-of-five variation (changing skill, line position and task) pushing success above 50% for most models. The authors argue that scaling and input filtering will not solve it and that skill files, being entirely instructions, defeat defences that assume instructions and data are separable.
- **Limitation.** I read the abstract, figure 1 and the introduction, not the per-model tables.
- **Implication.** Skill text read by the manager's own AI features (editor, judge, simulator) is an untrusted instruction channel.

### Shorter entries [abstract]
| Paper | Year | URL | Key claim | Implication |
|---|---|---|---|---|
| Supply-Chain Poisoning Against Skill Ecosystems (DDIPE) | 2026 | https://arxiv.org/abs/2604.03081 | Malicious logic hidden in code examples and config templates inside skill docs; 1,070 adversarial skills; 11.6 to 33.5% bypass while explicit-instruction attacks achieve 0% under strong defences; 2.5% evade both static analysis and alignment | Scan the examples, not only the imperatives |
| MalSkillBench | 2026 | https://arxiv.org/abs/2606.07131 | 3,944 runtime-verified malicious skills; code injection verifies at 94.5% but prompt injection only 75.8% | Pure prompt payloads are harder to produce and harder to detect |
| Skill Constellations | 2026 | https://arxiv.org/abs/2610.11169 | 2,193,119 skill adoptions on GitHub; copies almost never track their source; auditing the top 100 model-ranked repositories prevents 14.9% of later high-risk adoptions versus 0.5% for the 100 most starred | Provenance and copy lineage beat star counts |
| Skills Are Not Islands | 2026 | https://arxiv.org/abs/2607.01136 | 1.43 million skills; metadata is "activation-ready but governance-poor"; recursive reuse expands dependency graphs | Dependency evidence belongs in the library view |

Already covered earlier: Practice Makes Unsafe (2608.12851), Scan Before You Install (2610.37901), SoK Agentic Skills (2602.20867), SkillJect, Agent Skill Security survey.

---

## Checks on what we built

All simulations below are **[computed here]** with the repository's real `trial_stats.summarize` and `ai_ablate.decide`, 300 bootstrap resamples instead of 2,000 for speed, 200 simulated runs per cell, 3 trials per case, and a deliberately simple generative model (every case has the same pass probability: 0.8 with the skill, 0.8 minus d without it). Real cases differ, which widens the intervals, so treat the numbers as optimistic about power.

### 1. Is the 10-point margin sensible given eval variance?
The margin is not the binding constraint; the number of cases is.

Simulated share of runs that call each verdict (`decide`, full versus ablated), by true drop d and number of cases n:

| True drop d | n = 3 | n = 10 | n = 20 | n = 40 |
|---|---|---|---|---|
| 0.0 (removal harmless): "remove" | 14% | 10% | 18% | 30% |
| 0.1 (at the margin): "remove" | 4% | 3% | 2% | 3% |
| 0.2: "remove" (a wrong retirement) | 1% | 1% | 1% | 0% |
| 0.2: "keep" (correct) | 10% | 19% | 47% | 77% |
| 0.3: "keep" (correct) | 18% | 50% | 81% | 98% |

Reading: the rule almost never retires something that costs 20 points (at most 1%), so it is safe. It is also weak: when removal is truly harmless it proposes removal only 10 to 30% of the time even at 40 cases, and it detects a 20-point loss only 47% of the time at 20 cases. Most outcomes are "uncertain", which is the honest answer at these sizes.

For planning, Miller's formula gives the minimum detectable effect (δ) for a paired design. Illustration with assumed variances (not measured): between-case variance of true differences ω² = 0.05, within-case variance σ² = 0.15 per arm, K = 3 trials, α = 0.05, power 0.8, so (z_{α/2} + z_β)² ≈ 2.8² = 7.84: n = 7.84 × (0.05 + 2 × 0.15/3) / δ² = 1.18 / δ². That is **n of about 118 cases to detect 10 points**, about 29 for 20 points, and about 13 for 30 points. These are normal-approximation numbers and are optimistic at small n (next check). Supporting evidence from real systems: replicate spread of 3.6 to 4.4 points in Signal or Noise, and a 5.7 to 51.0% interval from 10 runs in the context-rot study.

A 10-point margin is therefore defensible as a non-inferiority bound, but it should be paired with a printed "smallest effect this run could see" so the user can tell "removal is safe" from "this run could not have seen a 25-point loss".

### 2. Are 3 cases enough?
Three is enough to avoid a harmful retirement and not enough to conclude anything useful. At n = 3 the simulation retires a 20-point-loss skill 1% of the time and confirms a 30-point-loss skill as worth keeping only 18% of the time. `MIN_CASES = 3` is a computational floor, not an evidential one, and the "not-enough-evidence" label could better follow the minimum detectable effect than a count. One real degeneracy found when running the code: three cases that all pass both with and without the skill give the interval [0.0, 0.0] and the decision "remove". That is right only if the cases are discriminating; the existing non-discriminating-assertion flag is the necessary guard, and it should be able to block "remove" outright when every case passes in every arm, since such cases cannot show harm. Likewise 3 cases with one flip gives lift 0.33 but interval [0.0, 1.0], and 10 cases with one flip gives [0.0, 0.3], both "uncertain".

### 3. Is a percentile bootstrap over cases the right interval?
Partly. Findings that bear on it:
- The estimate (mean of per-case paired differences) is right: Miller recommends paired question-level differences, and Don't Pass@k shows the Bayesian posterior mean ranks like average accuracy. Pass^k and pass@k are not better point estimates here.
- At small n the percentile bootstrap undercovers its nominal level and is wider than needed for the coverage it does reach (Bowyer 2503.01747). Wilson intervals (single proportion) and Bayesian beta-binomial or clustered models (paired and clustered comparisons) hold their coverage. In our simulation the false "keep" rate at d = 0 was 4% at n = 3, 3% at n = 5 and 1 to 2% at n ≥ 10, against a one-sided nominal 2.5%, so the problem is mild but real at the smallest sizes.
- Bootstrap over cases only is enough. The inner resampling of trials double counts: the variance of a case mean already contains σ²/K (Miller's decomposition Var(x) + E[σ²]/K), so resampling cases captures it once and resampling trials again adds it a second time. This is standard two-stage bootstrap theory and is my inference from Miller, not a measured effect here; it makes our intervals slightly too wide, which is conservative for "keep" and costly for "remove".
- Statistical independence of cases is assumed. Cases written from the same skill, or paraphrases, are clustered; Miller reports clustered standard errors up to 3x naive ones. If the AI generates cases from one description, they are likely clustered.
- A second concern is multiplicity and selection: a loop that ablates ten sections and retires the ones that pass is a tune-then-select procedure, the setting where SIREN (2605.05973) shows winner-style reporting is optimistic.

### 4. Judge biases that affect the contradiction check, and mitigations
The pair-of-lines judge reads two instruction lines and says whether they conflict. Documented hazards and the evidence for each:

| Hazard | Evidence | Mitigation within a user-keyed budget |
|---|---|---|
| Low prevalence (base-rate) | ConInstruct 87 to 91% F1 is on balanced sets at about 50% prevalence, with ambiguous cases removed. [computed here] At 2% prevalence, 90% sensitivity and 90% specificity give a positive predictive value of 15.5% (0.018 true positives against 0.098 false positives per item) | Show the heuristic prefilter's candidate count; label verdicts "possible"; calibrate on a handful of labelled pairs (Noisy but Valid 2601.20913) |
| Run-to-run instability | Coin Flip: 13.6% pairwise flips; 11 votes to match a 50-vote majority; temperature 0 does not remove it; All Verdicts: consistency is not accuracy | Three votes with unanimous-or-"unsure" aggregation rather than 11 (cost-based inference); never treat one call as final |
| Order of the pair | Coin Flip: 72% first-position pick for one judge; WhoWins: the first line wins 72 to 95% in *generation*; Judging the Judges: position bias at most 0.04 in current models and swap helps only some models and hurts on LLMBar | Evaluate both orders and require agreement; an agreement rule is cheap (two calls) |
| Style and format bias | Judging the Judges: 0.10 to 0.76 preference for markdown over plain prose with identical content, dominant over other biases | Normalise both lines to plain text before judging; quote the line verbatim in the verdict |
| Verbosity | Heterogeneous by model (+0.24 to +0.44 for three, −0.12 for Claude) | Compare atomic lines of similar length; do not ask the judge to compare whole sections |
| Self-preference | 2604.22891: persists across 20 LLMs; structured multi-dimension evaluation cuts it 31.5% | When the skill was written by the same model the judge uses, mark the verdict as same-family; the user's single key limits what is possible [inference] |
| Trusts text over facts | TRACE 2604.03447: detection falls 21 to 43 points when only the code changes; confidence does not separate right from wrong | For repo facts (paths, commands, package manager), check deterministically and attach the result as evidence |
| Does not tell anyone | WhoWins: at most 2.92% flagged; ConInstruct: 45% alerts at best | Do not rely on the agent at runtime; the check must happen before |
| Dependence on prompt wording | Coin Flip: equivalent templates change the majority in 25% of cases | Fix a template and version it; record which template produced a verdict |

### 5. Is the trigger simulation trustworthy?
SkillReducer measured this gap: with a simulated oracle plus real-runtime validation, 40.8% of descriptions needed repair and 6.5% were abandoned. A model picking from a list is therefore an optimistic proxy for the agent's actual behaviour (the actual agents also have the skill-listing budget, truncation and their own harness prompts). Listing order matters: the first listed tool was picked about 72 points more often in Advertising to Agents, and candidate order is randomised for this reason in SkillReducer's oracle. Distractor choice matters: similar distractors cut precision from 97.7% to 84.1% in a random pool and from 70.5% to 53.4% in a similar-distractor pool (Demystifying).

### 6. Are the existing flags well founded?
- **Token regression flag (1.25x and 50 tokens).** Supported in direction: skills raised token cost 72 to 394% (Signal or Noise), context files raised cost 20% (Evaluating AGENTS.md), and fuller descriptions added 67% steps (MCP smelly). The specific thresholds are untested here.
- **Non-discriminating assertion flag.** Consistent with evidence that final results hide differences (HANDBOOK relaxed-grading view, Context Rot's strict versus coverage view). An assertion that never fails also cannot show harm.
- **Hurts / helps / inconclusive.** The three-way verdict matches the Bayesian recommendation "do not declare a winner when intervals overlap".
- **Listing-budget report.** Descriptions that are missing or too short are common (26.4% of 55,315 skills, SkillReducer; 56% of MCP tools without a clear purpose), so a report limited to truncation misses the larger problem of descriptions too thin to route.

---

## Ten concrete design changes

Ranked by expected value over cost, each tied to its evidence. These are proposals from the literature, not decisions.

1. **Print the minimum detectable effect and gate verdicts on power, not on a case count.** Show "smallest change this run could see" on every eval and ablation, computed from the observed case variance (Miller 2411.00640 equation for δ). Block "remove" when that effect exceeds the margin, and block it when every case passes in every arm. Evidence: the simulations above (most verdicts "uncertain" below 40 cases), 3.6 to 4.4 points of replicate spread (2608.23067), 10-run intervals of 5.7 to 51% (2607.17937).

2. **Use a small-sample-safe interval and resample cases only.** Replace the nested bootstrap with Wilson intervals for single rates and a paired or clustered beta-binomial posterior for differences, or at minimum bootstrap cases once. Evidence: 2503.01747 (CLT and bootstrap undercover at small n), 2411.00640 (variance decomposition shows double counting), 2510.04265 (posterior mean ranks like average accuracy, "do not declare a winner when intervals overlap").

3. **Add a length-matched placebo arm and per-model labelling to skill evals and ablations.** Same frontmatter, same byte length, neutral body; report lift against placebo and against no skill; stamp every result with the model it ran on and warn when the user changes model. Evidence: 2608.23067 (the placebo splits "length-distracted" from "content-misled"; cross-model correlation |r| ≤ 0.12), 2611.04169 (similar-looking text competes, neutral filler does not).

4. **Validate trigger-simulation and description rewrites in the real agent runtime, with order randomisation and similar-distractor pools.** Treat simulation as screening; where an agent CLI exposes stream events, confirm triggering there and restore deleted clauses when it fails; run each candidate in both listing orders. Evidence: 2603.29919 (40.8% needed repair), 2605.23916 (first-listed +72 points), 2608.14036 (similar distractors dominate), and score the task outcome as well as the invocation (invocation is "neither sufficient nor necessary").

5. **Upgrade the contradiction judge: two orders, three votes, quoted evidence, deterministic facts, calibrated confidence.** Normalise formatting, require both orders to agree, show the quoted lines, check paths, commands and package managers without a model, and show a positive-predictive estimate that uses the actual candidate rate and a handful of user-confirmed pairs. Evidence: 2511.14342 (balanced benchmark), 2606.13685 (flips), 2604.23178 (style bias dominates; swap is model-dependent), 2604.03447 (trusts text over code), 2601.20913 (calibration on a small labelled set).

6. **Add a held-out split and a validation-versus-held-out gap to AI edit and description-rewrite loops.** Hold back a fraction of saved cases, never show the optimizer those, print both gains, and flag a large gap. When several candidate edits are tried, report the selected one with a selection-aware note. Evidence: 2610.12601 (large gap from small-sample selection, 24 validation items), 2605.05973 (winner's curse), 2609.32452 (calibration gap).

7. **Grade actions and prohibited behaviour, and show a strict and a "missed by one" view.** Support negative assertions ("must not edit generated files") and trace assertions; never grade on the model's own claim of compliance; show per-assertion pass rates beside the all-pass rate. Evidence: 2607.25398 (28.2% of criteria were prohibitions; compliance falsely reported; relaxing by one criterion doubles scores), 2607.17937 (strict retention 0.375 against coverage 0.93 to 0.95), 2611.13709 (compliance is bimodal; mean 59.8%, median 100%).

8. **Add a deterministic staleness check and a "why" field for every rule.** Flag file paths, commands, scripts and package managers named in instruction files and skills that do not exist in the repo, and attach a one-line reason and source to each AI-added rule so later deletion is informed. Evidence: 2611.09802 (stale command costs about two extra tool calls and never raises an error), 2606.09090 (23.0% of 356 repositories), 2608.11095 (files grow 226%, rationale loss blocks deletion), 2610.31715 (74.0% of directives have no reason).

9. **Lint instruction files for density, position and phrasing, and offer the AI-written overview as the first removal candidate.** Count atomic directives per always-on file and per skill, flag conditional ("if you do X, do Y") phrasing, and show where each rule sits in the assembled context. Evidence: 2507.11538 (omission dominates; primacy peak near 150 to 200 instructions), 2610.33201 (first line wins 72 to 95%; declared tiers not followed), 2611.04367 (conditional phrasing 64.2% against 78.0%), 2602.11988 (generated overviews cost 20%+ and do not help), 2607.19257 (all-rules-pass collapses by 80 rules).

10. **Harden the AI pipeline and the install path against instruction injection in skill text and examples.** Treat skill bodies as untrusted data in the editor, simulator and judge prompts (delimit, never follow, and test with a planted instruction), and extend scans to code examples and config templates, not only imperative sentences. Show provenance and copy lineage rather than popularity. Evidence: 2602.20156 (up to 80% attack success), 2604.03081 (11.6 to 33.5% bypass via examples while explicit instructions got 0% under strong defences), 2605.11418 (description-only framing wins selection in 77.6% of trials), 2610.11169 (star counts do not identify risky sources).

**Considered and left out of the ten.** Joint-removal confirmation after several per-section retirements, because leave-one-out cannot see redundancy [inference; supported by SkillReducer's 1-minimal set idea and TokenSHAP's interaction framing]. A density curve fitted once per model (2509.21051). Sequential stopping to save the user's tokens (2607.08522). A retrieved shortlist instead of a full listing past about 100 skills (2505.03275, 2608.14036). Each is plausible but rests on abstract-level evidence or on inference.

---

## Appendix: evidence gaps

- No study measures cases needed for ablating a *skill* with a *user-keyed model*; the closest are Signal or Noise (3 replicates, 117 pairs) and the generic power formula.
- No published conflict benchmark covers skill-versus-skill or skill-versus-CLAUDE.md conflicts at realistic prevalence; ConInstruct, WhoWins and ManyIH are synthetic and, for WhoWins, open-weight only.
- No paper evaluates an LLM contradiction judge over instruction files; the closest are ConInstruct (inside one instruction) and TRACE (code versus documentation).
- Results on closed frontier models come mostly from preprints by single labs. Several (Coin Flip Judge, Prompt Design at Scale, CompressAgent) say so themselves.
- I did not read: the limitations sections of Evaluating AGENTS.md and Prompt Design at Scale, the per-model tables of Skill-Inject, or the appendices of ManyIH and WhoWins.
