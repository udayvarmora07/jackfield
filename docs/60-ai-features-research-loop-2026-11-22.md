# AI Features: Multi-Platform Research Loop

**Version 0.3.0**

**AI manifest**: Research loop of 2026-11-22. The first three rounds covered
Reddit, X, YouTube, Hacker News, GitHub, forums, Bilibili, V2EX, Quora,
Instagram, vendor documentation and hands-on product walkthroughs, then
fact-checked 30 weight-bearing claims. It extends the F1–F15 proposals in
@docs/59-ai-everywhere-research-2026-11-22.md, whose slice 1 (honest test
statistics, per-hunk accept, AI provenance) shipped as `bb33fac`. Round 4
records later research, shipped changes and remaining proposals. Sourced reports are in
@docs/research/2026-11-22-ai-loop/README.md.

**[NOTE]**

## Recommendation

The loop confirmed doc 59's direction and sharpened it. Writing a skill is not
the hard part. People struggle to know whether a skill earns its place, why one
skill beats another, and what to delete when the model changes. The most
upvoted items were all about subtraction: the post on Anthropic cutting about
80% of Claude Code's system prompt (1,562 points on r/ClaudeAI, about 16k likes
on X), "delete CLAUDE.md and re-add on each model release", and library audits
finding most installed skills unused.

Build slice 2 around **measured subtraction and conflict**:

1. **Ablate and retire** (new, extends F1 and F2): remove one skill, section
   or rule, replay saved cases with the slice 1 statistics, and propose
   deletion when the result is not worse. Ties go to deletion. Offer a demotion
   ladder (slash-only, disabled, archived) rather than keep or delete.
2. **Contradiction and ownership check** (new): statically find instructions
   that disagree across skills, CLAUDE.md and AGENTS.md layers, and the repo
   itself, with quoted evidence and the precedence that decides today. Models
   rarely notice conflicts on their own, so this must not rely on the agent.
3. **Routing trace and delivered-listing report** (extends "Why didn't it
   run?"): show which descriptions each agent actually receives, which are
   truncated or dropped, which skills compete for a request, and why.
4. **Placement advisor** (new, absorbs F12): for each skill, rule or section,
   recommend always-on guidance, an on-demand skill, a hook or script, or
   deletion, and offer the converted draft as a reviewed diff.

## Method and coverage

**[NOTE]** Twelve research agents (Sonnet 5.5 and Haiku 5.5) ran in three
rounds. Tools: `opencli` with its browser bridge (read-only adapters only),
`agent-reach`, `agent-browser`, `gh`, the HN Algolia API, WebSearch and
WebFetch. Nothing was posted, liked, followed or logged into. No CAPTCHA was
attempted. Fetched text was treated as data.

| Platform | Outcome | Main tool |
|---|---|---|
| Reddit | About 55 threads with top comments read; r/claudeskills was the richest source | `agent-reach` public-web search, then `opencli reddit read` |
| X | About 420 posts plus selected reply threads; rate-limited (HTTP 429) late | `agent-reach`, `opencli twitter` timelines |
| YouTube | Transcripts for 3 videos; comments on 11 videos; descriptions for more | `agent-reach`, `opencli youtube` |
| Hacker News | Stories and comment threads | Algolia API, `opencli hackernews` |
| GitHub | Issue trackers of 12 agent and skill tools; 2026 skill-tool repos | `gh` |
| Bilibili, V2EX | About 15 searches and 23 comment threads; V2EX thin | `opencli`, `agent-reach` |
| Quora | Loaded without a wall through the browser bridge, mostly keyword noise | `opencli browser` |
| Instagram | No usable results: search returned HTTP 404 through every tool | `agent-reach`, `opencli instagram` |
| Zhihu, Xiaohongshu | Blocked (sign-in required, timeouts) | `opencli` |
| Products | About 18 products walked through; 5 open-source tools read from source | `agent-browser`, cloned repos (never executed) |
| Literature | Two passes, abstracts only | arXiv, Semantic Scholar, vendor blogs |

**Fact-check.** 30 weight-bearing claims were checked against their sources:
23 confirmed, 7 partly right, 0 wrong. Corrections are applied below. Three
GitHub "+N" counts were totals across all emoji reactions, not thumbs-up (for
example claude-code #6235: 6,693 total, 5,194 thumbs-up). One Reddit score had
drifted by about 10%. Cisco's 7.7% rules-only catch rate applies at HIGH
severity only.

## What is new since doc 59

1. **Subtraction beats addition.** The 80% system-prompt cut
   ([Reddit](https://www.reddit.com/r/ClaudeAI/comments/1v5mhhl/), 1,562
   points) produced the most-repeated advice of the loop: baseline without your
   skills on the new model, then add back one at a time. Users who keep a
   heavy skill pack run "a handful of real tickets with and without" it. A
   placebo study of nine popular skills found only two beat a length-matched
   dummy skill ([Reddit](https://www.reddit.com/r/ClaudeAI/comments/1wz4rfz/)).
2. **Contradictions are a library problem, and models do not catch them.**
   Users describe a top-level CLAUDE.md saying pnpm while a package file says
   yarn, and skills that disagree depending on "which one the agent reads
   first" ([Reddit](https://www.reddit.com/r/ChatGPTCoding/comments/1xg5nq7/)).
   In the literature, models flag at most 2.92% of conflicting instruction
   pairs and the earlier instruction tends to win, while static detectors
   reach F1 87–91% [abstract]. Deleting an "unused" skill that two others
   referenced caused silent quality loss
   ([Reddit](https://www.reddit.com/r/ClaudeAI/comments/1rxjyex/)).
3. **Usage telemetry is masked or incomplete.** Claude Code `skill_activated`
   events report `custom_skill` instead of the name (claude-code #58674,
   #76957, #77541). Transcript readers miss hook-fired and plugin-installed
   skills: one scanner missed the whole `plugins/` tree for six weeks. The
   existing `usage` aggregates need these gaps labelled as unknown.
4. **Descriptions are silently truncated.** Codex reserves 2% of context for
   skill descriptions ([#19679](https://github.com/openai/codex/issues/19679));
   users measured 235 characters lost per skill. No tool reports what each
   agent actually receives.
5. **Placement is the real authoring question.** "Half your skills should be
   rules" and "turn checkable rules into hooks" recur on Reddit. Two AGENTS.md
   studies disagree on whether always-on context helps (one finds cost up 20%
   with no gain, the other finds runtime down 29%), so the advice has to be
   measured per library, not assumed.
6. **Self-improvement needs a strict gate.** Practitioner loops on X accept an
   AI edit only on a strict held-out win, reject ties, and cap a proposal at
   about 4–8 edits. Learned-rule tools that people trust show the correction
   behind each rule, with accept, undo and decay
   ([Reddit](https://www.reddit.com/r/claudeskills/comments/1x4p1z7/)).
7. **Install counts are gameable.** A backdoored skill reached the top of a
   registry with about 4,000 fake downloads (reported on X). Users want
   provenance, capabilities and a pre-enable preview instead of popularity.
   Of 6,309 public skills profiled, 5.4% received a threat verdict and about
   70% carried at least one capability "worth knowing about"
   ([Reddit](https://www.reddit.com/r/ClaudeAI/comments/1xb2eyh/)).
8. **Localization and providers matter outside English.** Bilibili comments
   on a skills-manager video ask for AI classification and a Chinese note per
   skill. Users also want DeepSeek, Kimi, GLM and Qwen as bring-your-own-key
   providers with local-currency cost previews, and a per-model trigger test
   because skills tuned for Claude are reportedly ignored by some other models
   [single source, secondhand].
9. **Teams want governance the product can support locally.** Vendor docs
   show approval modes (Anthropic: Requires review, Open, Off), "Needs Review"
   and "Blocked" scan states (ChatGPT), 30-day invocation counts per skill,
   and audit gaps (share events logged but not skill contents).
10. **Comparable products split the market.** Sync managers get the stars
    (xingkongliang/skills-manager, 7,681) but ship no AI. Eval and security
    tools do no library management. Nothing combines sync, observed usage,
    measured lift and reviewed apply, which is Skills Manager's position.

## Round 4: the user's own browser and a literature deep dive

**[NOTE]** Reports 15–18 in @docs/research/2026-11-22-ai-loop/. Earlier rounds
were blocked on Reddit search (403), X search and Instagram (404). Round 4 ran
read-only through the user's own Chrome via the opencli bridge: Reddit search
and threads, Instagram keyword pages and Quora all worked, and automated or
headless Chrome stayed blocked by Reddit. X search failed on every route, so
X evidence comes from timelines, threads and articles. The literature pass
cited about 58 papers and read 18 in full.

Findings that change or confirm the plan:

- **G3 is the strongest social signal.** A user with 91 skills found 34
  without a description in context, and all 12 "never fired" skills were among
  them; they nearly deleted them (r/ClaudeAI). SkillReducer reports 26.4% of
  55,315 skills with missing or thin descriptions, so the listing report should
  also flag thin descriptions, not only cut ones.
- **G1 is wanted but needs power.** Three subreddits ask how to tell a working
  rule from one the model follows anyway, and on/off comparison is the answer
  people trust. A user's mutation test caught 6 of 15 deliberate config breaks.
  Simulating the shipped rule with the real `trial_stats` and `decide`: it
  wrongly retires a 20-point loss at most 1% of the time, but proposes a
  harmless removal only 10–30% of the time even at 40 cases. Detecting 10
  points needs on the order of 100 cases (Miller, arXiv 2411.00640).
- **G2 judges need care at low prevalence.** At 2% prevalence, a judge with
  90% sensitivity and specificity is right only about 15% of the time when it
  says "conflict"; judges also favour one position and markdown over prose.
- **Simulation is optimistic.** SkillReducer found 40.8% of
  simulation-approved descriptions needed repair in the real runtime, and the
  first-listed tool won about 72 points more often in one study.
- Unverified but notable: commenters report Claude Code `/doctor` checks for
  stale or contradictory instructions, and that Claude Code reads AGENTS.md
  only when no CLAUDE.md exists [?].

**[SPEC]** Applied on 2026-11-22:

- `trial_stats` resamples cases only (resampling trials again double counted
  trial noise) and reports `min_detectable`, shown on every eval, comparison
  and ablation.
- `ai ablate` returns `untested` instead of `remove` when every answer passes
  or every answer fails in both variants, and its `remove` reason states the
  smallest loss the run could have seen.
- The contradiction judge asks in both orders and keeps a verdict only when
  both agree.
- Next batch, same day: the listing report marks `thin` descriptions (under
  the validator's 20 characters); `ai ablate --placebo` adds a same-length
  filler arm; `ai conflicts` reports directive density per instruction file
  and deterministic stale references in project instruction files.

**[NOTE]** Deliberately not applied: blocking `remove` whenever the minimum
detectable effect exceeds the 10-point margin. With the 0.5 spread floor that
needs about 200 cases, more than the 20-case limit, so the feature would never
propose anything. Removal stays a reviewed, recoverable proposal that states
its evidence limit. Batch 3 added the held-out gap and a selection
note to description rewrites (held-out prompts already existed), optional
three-vote judging, reason and wording counts per instruction file, and
planted-instruction tests, and labels ablations with the previous run's model and revision.
Remaining literature proposals: confirming trigger
results in the real agent runtime (listing order is already shuffled per
repeat); a predictive-value estimate for the judge; action assertions
(negative text assertions already exist as `not_contains`).

## Consolidated feature catalogue

**[NOTE]** "Source" counts independent platforms with supporting evidence. F
numbers refer to doc 59. Shipped items are marked.

| # | Feature | What the user gets | Sources | Relation |
|---|---|---|---|---|
| G1 | **Ablate and retire** | Pick a skill, section or rule; replay saved cases without it; the slice 1 statistics decide. "Not worse" proposes removal via the demotion ladder (slash-only, disabled, archived). After a model change, a "reset and re-add" plan ranks what to add back. | Reddit, X, HN, YouTube, literature | New; extends F1, F2 |
| G2 | **Contradiction and ownership check** | Quoted conflicts across skills, CLAUDE.md/AGENTS.md layers and repo facts (paths, commands, package managers); the precedence that wins today; a proposal naming one owner with "points to" stubs; a reference graph shown before delete or archive. | Reddit, X, literature | New |
| G3 | **Delivered-listing report and routing trace** | Per agent: which descriptions fit, which are truncated or dropped and by how much. Per request: competing skills, the likely winner and rejected near-matches with reasons, labelled as simulation. Discovery checks for symlinks, nesting, naming, plugin trees and per-agent `disable-model-invocation` behaviour. | GitHub, Reddit, OpenAI forum, literature | Extends shipped "Why didn't it run?" |
| G4 | **Placement advisor** | For each skill, rule or section: always-on, on-demand skill, hook or script, or delete, from need-frequency, determinism, token cost and measured lift. Converted drafts arrive as reviewed diffs. Includes Cursor-rule, command and subagent conversion. | Reddit, X, GitHub, products, literature | New; absorbs F12 |
| G5 | **Trustworthy evals, part 2** | A length-matched placebo arm; "was the skill invoked" per run; first-tool-call (behavioural) grading with pass^k beside pass rate; comparison against the last approved version; a per-model trigger test with untested cells marked. | Reddit, HN, YouTube, literature, products | Extends shipped F3 |
| G6 | **Observed usage, honestly labelled** | Usage per skill that counts hook-, subagent- and plugin-fired skills where transcripts show them, labels the rest unknown, and pairs resident (description) cost with on-demand body cost, including MCP tool-schema size. | Reddit, GitHub, YouTube, Bilibili, enterprise docs | Extends F1, F8 |
| G7 | **Grounded drafting with an intent stage** | From a transcript excerpt, git range, SOP document or a short interview: an editable intent and numbered steps first, then the draft, test cases and a redaction preview. Learned rules arrive in an inbox with their source correction, scope, accept, undo and decay. | Reddit, X, YouTube, Bilibili, products, enterprise | Extends F5 |
| G8 | **Gated self-improvement** | The bounded optimize loop (F7) accepts only strict held-out wins, rejects ties, caps edits per proposal, shows the token delta and warns as a skill grows. | X, products, literature | Refines F7 |
| G9 | **Provenance over popularity** | A pre-enable card: source, author, revision, change since install, bundled scripts, network and tool capabilities, encoded install steps, repository-rename hijack check, and separate deterministic, heuristic and AI findings. | X, Reddit, products, GitHub | Extends F13, F15 |
| G10 | **Project sets and setup recommender** | Scan a project and suggest which skills to enable and which installed ones are irrelevant there, as a batch preview; role starter packs that install and remove as one unit. | X, GitHub, YouTube, enterprise | Extends F11 and profiles |
| G11 | **Local notes, translation and classification** | A sidecar note and translated summary per skill shown in lists, never altering SKILL.md; AI-suggested tags and categories. | Bilibili, enterprise | New |
| G12 | **More providers and agent scopes** | Presets for DeepSeek, Kimi, GLM and Qwen endpoints with a cost preview in the user's currency, and scopes for further agents (Trae, Qoder, Kimi Code, Qwen Code) once their paths are verified. | Bilibili, V2EX | New (provider presets are configuration, scopes are non-AI work) |
| G13 | **Team export and governance, locally** | Export a reviewed, hash-pinned bundle with owner, version and evidence; an approval state per skill in a shared repository; a usage and change report for a maintainer; a PII scan before sharing. No hosted service. | Enterprise docs, GitHub, Reddit | Extends F13; scope decision needed |
| G14 | **Plain-language guidance for non-developers** | "Which should I use?" explainer (rule, skill, project instructions, custom agent), three-example test scripts graded by reading, and plain block and review reasons. | Enterprise, YouTube | New |
| G15 | **Skill chains** | Save an ordered playbook such as interview, PRD, issues, implementation. | YouTube | New; weak evidence |

Already shipped and reconfirmed by this loop: Create with AI, Edit with AI with
per-hunk accept, current-vs-proposed comparison with repeated trials and
intervals, "Why didn't it run?", overlap judge, listing-budget fitter, install
and update briefings, and AI provenance in Recovery.

## Interface patterns to adopt

**[NOTE]** From the product walkthroughs, each seen in at least one shipping
product:

- Title each result card as a question ("Does the skill make a difference?")
  and answer with a one-word verdict and a noise band.
- Keep "not measured" and "unknown" distinct from zero. Never show a headline
  multiplier without its sample size; one product's 1.44x headline sat above
  its own "no measurable difference" verdict.
- Tag each finding as deterministic, heuristic or AI. Mark saved AI results
  stale when the model or the content hash changes, and keep them until the
  user regenerates, to avoid repeat spend.
- Report first, then ask, then apply. Name the exact command or action a
  recommendation would take.
- Let a deterministic pre-filter choose candidates and the model judge only
  those.
- Show a read-only preview of a generated SKILL.md that is reused exactly on
  save; any edit to the plan discards it.
- Store human pass/fail overrides with the evidence and export them.

## What not to build

- Popularity and install counts as a trust signal.
- An AI optimizer that reports success from a measurement it cannot make (the
  skill-creator 0%-recall failure).
- Unattended learning that writes rules without review, or never forgets them.
- Hosted accounts, a public registry or team services. G13 stays export-only.

## Decisions needing maintainer approval

- **CLI commands.** Still pending from doc 59: `ai health` and `ai recheck`.
  G1, G2 and G3 would also be useful from the CLI, for example
  `ai ablate` and `doctor --listing`.
- **New agent scopes** (G12) change the scope list and discovery rules.
- **Team features** (G13) touch the product's single-user scope.
- **Transcript content** (G7) still needs per-excerpt consent before it is sent
  to a model.

## Proposed slice 2

**[NOTE]** Shipped 2026-11-22 as `ai ablate`, `ai conflicts` and per-skill
description cuts in the listing report; see @docs/03-cli-surface.md and
@docs/08-web-ui.md. Both checks below are covered by `tests/test_ai_ablate.py`,
`tests/test_conflicts.py` and the listing tests. Contradiction pairs between
two skills were left to the overlap judge after a real-library run showed
they were mostly noise.

| Ship | Check before expanding |
|---|---|
| G1 ablate and retire for one skill or section, using saved cases and slice 1 statistics; G3 delivered-listing report per agent (deterministic) | On fixtures with a known-useless and a known-useful skill, the useless one is proposed for removal and the useful one is not. Truncation numbers match each agent's documented budget. |
| G2 contradiction check over skills and CLAUDE.md/AGENTS.md layers, deterministic candidates plus an AI judge with quoted evidence | Seeded conflicts are found, unrelated pairs are not, and every reported conflict quotes both sides verbatim. |
