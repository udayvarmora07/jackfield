# AI Authoring and the Skill Lifecycle

**Version 0.1.0**

**AI manifest**: Research and proposed priorities for AI-assisted skill creation,
editing, testing, discovery, and maintenance. Dated 2026-11-22. The current
implementation was inspected at `02966f5`. Existing decisions and features are
recorded in @docs/39-ai-features-research-and-catalogue-2026-11-09.md. Priorities
and acceptance criteria here are proposals.

**[NOTE]**

## Recommendation

Put **Create with AI** in **New skill** and **Edit with AI** in the exact-copy
editor. Carry the proposed change from the editor into a comparison, a realistic
test, and Recovery. Use the existing AI tools from those entry points. Make
**Why didn't this skill run?** the next distinct workflow. It should combine
filesystem discovery, the model-facing listing where observable, and actual run
evidence. A user should be able to start with a workflow they want to capture or
a failed request they want to fix and end with a tested, recoverable change.

The first users to serve are people already maintaining local skills. A new
author needs guidance and a usable draft. A power user needs control over which
copy changes and whether the change introduces regressions. A team maintainer
needs comparable evidence across agents and versions. Each benefits from the
same authoring and review flow. Sharing policy, hosted services, and pricing can
wait until that flow proves useful.

The portable format already gives the editor a useful structure. The name and
description affect discovery. The body describes the procedure, examples, and
edge cases. Supporting files carry detailed references and resources. Show which
layer an edit changes and which consumer-specific fields need a compatibility
check. [Agent Skills specification](https://agentskills.io/specification),
[Claude Code Skills](https://code.claude.com/docs/en/skills).

## What the research supports

Three parallel reviews covered public user reports, comparable products, and
integration feasibility. The product claims below come from vendor docs and
published source. GitHub issues illustrate actual reported problems and requests.
They cannot estimate prevalence or willingness to pay. The benchmarks measure
their own configurations and datasets. No Skills Manager participants were
interviewed, competitor accounts exercised, or paid model calls made for this
study. The prior research and pilot plan are available in
[the AI catalogue](39-ai-features-research-and-catalogue-2026-11-09.md) and
[the pilot kit](25-design-partner-pilot-kit.md).

| Observed evidence | Product implication |
|---|---|
| Claude Code users reported a worktree discovery failure. A VS Code user reported skills visible in settings with loading problems in chat. A Codex issue asks for control over skill metadata truncation. [Claude Code worktrees](https://github.com/anthropics/claude-code/issues/45956), [VS Code](https://github.com/microsoft/vscode/issues/303115), [Codex metadata budget](https://github.com/openai/codex/issues/19679) | Diagnose the exact project, launch context, and copy. Check discovery and listing coverage before asking AI to rewrite anything. |
| A Claude Code generator report describes rewriting an existing nested skill. A Vercel Skills update report describes overwriting local changes, including supporting files. [Generator report](https://github.com/anthropics/claude-code/issues/81842), [Update report](https://github.com/vercel-labs/skills/issues/455) | Detect existing folders before creating. Compare the current copy and proposed revision before applying. Preserve local additions and show differences for supporting files. |
| An Anthropic skill-creator issue reports erroneous zero recall. Claude Code users also requested invocation tracking to understand how their collection is used. [Eval instrumentation report](https://github.com/anthropics/skills/issues/1721), [Usage analytics request](https://github.com/anthropics/claude-code/issues/35319) | Make missing or ambiguous observations visible. Usage summaries should report observed coverage and link to evidence. |
| Expo measured activation, uptake of the skill's guidance, and app behavior independently. On ten Expo app briefs with three runs per condition, Expo reported that 9% of baseline sessions chose a skill and 55% of candidate sessions went on to a specialized skill after an overview entry point was added. Relevant-skill recall remained incomplete. [Expo evaluation](https://expo.dev/blog/your-skills-need-an-evaluation-mechanism) | Test realistic implicit requests, trace multiple loads where observable, and test a routing overview or slimmer profile when descriptions alone cannot resolve overlap. The Expo result is a starting hypothesis for that experiment. |
| SkillsBench v4 reports average success moving from 33.9% to 50.5% with curated skills on 87 tasks across 18 model and harness configurations. A separate production study of nine skills and 372 cases found that one rewrite informed by both missed and unwanted triggers captured most of the measured gain. [SkillsBench v4](https://arxiv.org/abs/2602.12670v4), [Description optimization study](https://arxiv.org/abs/2606.30775) | Capture real procedures and keep an inexpensive first optimization pass. Compare outcomes on held-out cases, and look at genuinely overlapping scopes before investing in repeated prompt rewrites. |
| Authors of a November preprint report declining scores after repeated feedback-free rewriting of expert skills in their experiments. [Feedback-free skill evolution preprint](https://arxiv.org/abs/2611.25534) | Put expert exceptions, thresholds, and fallback steps in view during edits. Make a failed example or explicit user objective the starting point for an optimization. |

### What already exists elsewhere

| Reference | Published capability | Pattern for Skills Manager |
|---|---|---|
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) and [Agent Skills authoring guide](https://agentskills.io/skill-creation/optimizing-descriptions) | Draft and edit, evaluate realistic prompts, compare variants, and tune triggering. Anthropic uses the old version as a baseline for edits and a no-skill condition for new skills. | Bring old versus proposed and with versus without comparisons into the editor. Give authors direct access to the outputs that explain a score. |
| [ChatGPT Skills](https://help.openai.com/en/articles/20001066-skills-in-chatgpt), [Record & Replay](https://learn.chatgpt.com/docs/extend/record-and-replay), and [OpenAI skill eval guide](https://developers.openai.com/blog/eval-skills) | Skill creation and updating, capturing a demonstrated workflow, and guidance for inspecting traces and checking results. | Start with selected source material or examples. Make transcript import a deliberate, bounded workflow once the editor is working. |
| [uberSKILLS](https://github.com/uberskillsdev/uberskills) | Its published workflow includes visual AI-assisted creation, multi-model output comparison, history, and deployment to multiple tools. | Expect fast drafting and preview. Differentiate on exact live copies, evidence quality, and recoverable application. |
| [Promptfoo](https://www.promptfoo.dev/docs/usage/prompt-optimization/) and [LangSmith Prompt & Context Hub](https://docs.langchain.com/langsmith/prompt-context-hub) | Failure-driven candidate testing and validation splits, plus versioned prompts and promotion between environments. | Keep cases and evidence attached to revisions. Make cross-model comparison and team promotion follow a reliable local comparison flow. |
| [Vercel Skills](https://github.com/vercel-labs/skills), [GitHub CLI](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/), [Microsoft APM](https://microsoft.github.io/apm/about/compared/) and [Cisco Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner) | Discovery and installs, revision pinning, lockfile and integrity workflows, and layered defensive scanning, respectively. | Build on source and integrity facts. Use AI to explain relevance, incompatibilities, and concrete changes in behavior or capabilities. |

## Current Skills Manager baseline

| Existing behavior | Gap to close |
|---|---|
| The v2 AI Tools page already drafts from a brief, validates the result, runs sampled routing simulation, and hands a successful draft to New skill. [Draft backend](../skillsmgr/ai_draft.py), [AI view](../skillsmgr/webui/v2/ai-center.js), [Create form](../skillsmgr/webui/v2/app.js) | Start directly from New skill. Add optional source excerpts and example outputs. Give the user an editable draft while showing routing coverage separately. Current draft status `verified` reflects completed sampled simulation after validation. Use separate checks for useful output and native activation. |
| Description improvements already use held-out routing cases. Conciseness already stages a reviewed candidate for an exact physical copy, including reference-file changes. The normal reader has a manual editor. [Routing and rewrites](../skillsmgr/ai_skills.py), [Conciseness](../skillsmgr/ai_concise.py), [Reader and editor](../skillsmgr/webui/v2/index.html) | Generalize the reviewed edit workflow to an instruction or selected section. The existing description apply sends the generated description by name and scope through a PATCH. Use an exact, revision-bound review for the new workflow and route that existing action through it when parity is available. |
| Saved routing prompts, simulation comparisons, and a no-send CLI/CI path exist. The AI output eval compares a global library skill's text in the system prompt against a bare baseline with deterministic assertions. [AI CI contract](42-ai-cli-ci-2026-11-09.md), [Output eval runner](../skillsmgr/ai_evals.py) | Add the current copy versus the staged candidate, agent-scoped copy selection, and human-reviewed assertions. Add a separate native run for questions about discovery or behavior with the full bundle. |
| Doctor computes effective discovery facts, Ask your library narrows and recommends existing skills, porting notes use a documented key table, and profiles use bounded project signals. [Effective discovery](../skillsmgr/effective.py), [Library Q&A](../skillsmgr/ai_ask.py), [Porting](../skillsmgr/ai_port.py), [Profiles](../skillsmgr/ai_profiles.py) | Connect these facts to the selected project and copy. Let a user move from a failed run to the relevant diagnostic, edit, or deployment preview. |
| Source reviews, scoped snapshots, Recovery, diff comparison, and an evidence-linked AI review briefing exist. [Source update flow](../skillsmgr/source_update.py), [AI review](../skillsmgr/ai_review.py), [Web UI map](08-web-ui.md) | Carry a reviewed AI edit through the same snapshot and conflict protections. Show where a change came from and what evidence went with it in Recovery. |

The latest paid HTTP study matched 36 authored labels in 36 synthetic
observations from four skills, twelve prompts, and three repeats. The separately
attended native study produced two conclusive agreements on obvious synthetic
cases. The later OpenCode fixture validates event parsing with scripted provider
behavior. A broader matched native-agent comparison remains outstanding in the
live task queue. These results support keeping **simulation** and **observed
native use** as different evidence labels. [CLI study](41-ai-fidelity-study-2026-11-09.md),
[HTTP and OpenCode study](48-ai-http-study-2026-11-17.md), [Live queue](../task.md).

## Ranked feature backlog

Priorities reflect directness of the evidence, fit with the current UI and data
model, likely frequency of use, and validation effort. Demand for the late
features remains a hypothesis. Existing features are listed where integration
would close a user workflow.

| Priority | User workflow | Proposed AI assistance and result |
|---|---|---|
| 1 | **Create with AI** | Generate from a plain brief, existing template, selected SOP text, or pasted examples. Ask only for missing workflow boundaries or success criteria. Return editable instructions, when-to-use and when-to-skip examples, prerequisites, and a small proposed test pack. Preflight destination collisions and material assumptions. |
| 1 | **Edit with AI** | Use the selected section, explicit instruction, and optional failed example to propose a focused change. Offer tighten, clarify, add examples, fix a finding, or custom instructions. Highlight changed requirements, scope, examples, commands, and permissions. Preserve the user's unsaved work and offer a draft diff with selective acceptance. |
| 1 | **Compare and apply** | Explain the meaningful changed behavior against the diff. Apply the exact reviewed revision to one physical copy through its existing mutation and Recovery path. Reopen a fresh comparison on out-of-band changes. Offer a separate deployment preview for other copies. |
| 2 | **Generate and run tests** | Suggest realistic positives, negatives, near misses, competing-skill cases, missing prerequisites, and ambiguous requests. The author confirms expected outcomes and keeps independently written cases held out. Compare old vs proposed and, when useful, with vs without. |
| 2 | **Why didn't this skill run?** | Explain discovery rules, disabled or manual-only state, listing coverage, agent versions, duplicates, conflicting descriptions, and checks to do next. Link to Doctor, the exact copy, the routing simulation, or available native trace evidence. |
| 2 | **Turn a failed run into a fix** | From a user-selected prompt, output or trace excerpt, propose a regression case, identify the relevant instruction and draft a small change. Retest the original failure and nearby cases with the same baseline. This is the recurring-use loop. |
| 2 | **Find or reuse a skill** | Upgrade Ask your library with project fit and exact availability. Search locally first, then offer registry candidates on request. Show why each match fits, source, revision, scope, observed capabilities, and compatible alternatives. Offer to adapt an existing skill when it fits the workflow. |
| 3 | **Review installs and upstream updates** | Expand the existing briefing into a change summary that cites files and shows newly required tools, destinations, or dependencies. Explain which local instructions an upstream change affects. Use a common ancestor for a three-way proposal when available, otherwise show available diffs and ask the reviewer to resolve ambiguity. |
| 3 | **Port and deploy across agents** | Convert existing porting notes into a portable core plus proposed, supported per-agent changes. Expose fields that are ignored, manual-only invocation, dependency differences, and incomplete evidence. Preview affected roots and let the user add a smoke case per target. |
| 3 | **Improve a collection** | Flag neighboring skills whose scopes may collide, suggest boundary sentences, a merged draft or overview, and simulate the proposed collection. Connect budget-fit and concision tools. Show which prompts, skills and listing entries were sampled. |
| 3 | **Organize and onboard** | Suggest tags, categories, project profiles and a small starter set from a local shortlist. Explain why each proposed skill belongs and preview additions and removals. Keep naming, templates, and formatting useful with AI switched off. |
| 3 | **Explain sync, history, and recovery** | Summarize what changed in each exact copy, which local changes matter, and what restoring a given snapshot would change. Ground summaries in diffs and manifests. Keep the existing restore and sync confirmation as the authority. |
| 4 | **Learn a repeatable workflow** | Convert a selected successful interaction, checklist, or local transcript excerpt into a skill and test cases. Highlight sensitive passages for review and prefer a local model for transcripts. Begin with paste or import. Validate demand before building recorders or indexing sessions. |
| 4 | **Maintain skills over time** | Suggest review when a fingerprinted dependency, recorded API behavior, model, or target-agent version changes. Summarize supported local usage and retest options. Recommend retirement only with evidence and a reversible user action. No observation means unknown use. |
| 4 | **Share and hand off skills** | Generate a README, example requests, release notes, and a comparison receipt from actual changes. Package cases with the skill when the author wants to share them. Report portability and review provenance for team adoption. Follow existing distribution decisions before adding publishing or approvals. |

Use the edit and comparison workflows for these narrower extensions once the
first slices work:

| Extension | Design detail |
|---|---|
| Preserve expert rules | Let authors mark requirements and examples to keep. Compare the relevant text before and after. Flag changes to must, must never, fallback, approval, limit, or expected output. Use literal checks where the author needs exact preservation, and show paraphrase suggestions for review. |
| Author the whole bundle | Propose a `references/` document from supplied material, a text template under `assets/`, or an eval fixture. Show how each file is reached from `SKILL.md`. Check relative links and case-sensitive file names. Source licensing and supporting-file permissions belong in the review. |
| Migrate existing instructions | Turn a selected project rule, reusable prompt, or checklist into a skill when the user can name a bounded workflow. Show which parts belong in always-on project guidance and which are appropriate for an opt-in procedure. |
| Change the scope of a skill | Preview a split into focused skills, a consolidation, or a shared core with per-agent variations. Compare neighboring skills, links, expected triggers, and downstream deployment before proposing any moves. |
| Localized behavior | Translate examples and propose trigger phrases drawn from real requests in the target language. Compare the language-specific cases with source-language cases and preserve named commands and paths. |
| Model or agent upgrade readiness | Re-run a saved set across user-selected model or agent versions. Highlight expensive or low-uptake skills, old-version behavior that disappeared, and the cases that justify a follow-up. Distinguish changes in the model, listing, instructions, or fixtures. |

Keep byte checks, path containment, frontmatter validation, source pinning, scanner
findings, mutation, and restore logic deterministic. AI can explain findings and
propose changes. Offline search, filters, toggles, backups and manual editing
already meet their core purpose with deterministic behavior. Translate or restyle
selected text through the editor when requested. Treat hooks, binary assets,
executable files and arbitrary multi-file rewrites as separate follow-ons, with
initial authoring focused on text and test data. Defer hands-off maintenance and
bulk AI rewrites until comparative evidence, local change review, and per-copy
rollback are proven. Source links and expected outputs matter more than a global
AI quality score.

## First version in the v2 interface

1. **New skill → Create with AI.** For example, “Draft release notes from merged
   PRs. Match these two examples and ask before publishing.” The author chooses
   an intended scope, adds selected excerpts if useful, and sees the destination
   and content selected for the model call. The response notes missing
   assumptions, preloads an editable New skill form, and proposes examples with
   expected behavior. Local checks flag naming conflicts and unsupported keys.
2. **Exact skill copy → Edit with AI.** For example, “Group user-facing fixes by
   category. Keep our breaking-change rules.” Operate on a selected section or
   the whole `SKILL.md` when requested. Show current versus proposed wording,
   additions or removals of requirements, and references used. Use the source
   revision and the editor revision to detect changes to either baseline.
3. **Run checks → Save.** Display local validation, simulated trigger counts,
   and output comparisons independently. Saving a valid draft is a user action.
   Evidence labels show skipped, partial, complete or stale. Applying an edit
   creates a recoverable snapshot. Use deployment and sync review for other
   copies.
4. **Quality and Recovery.** Keep the saved version, previous version, model
   and run metadata, and any linked results together. A user can inspect a
   failing case, retest it, compare with the previous revision, or restore it.

Launch acceptance examples are a new author saving a first valid draft from the
New skill entry point, a maintainer editing one of two same-name copies, a
stale proposal refused after an external save, and a verified Recovery round
trip. Include a provider-disabled manual flow and a provider error with the
user's draft preserved. Proposed UI wording and placement should be exercised
through those tasks before choosing a separate authoring page.

For quick edits, generation and local validation are sufficient to show a
candidate. An optional test compares the behavior the user chose to change. For
a reusable or risky workflow, offer a fuller test plan and display the expected
number of provider calls, selected context, limits and supported native modes
before running it. A repair that changes where a skill triggers calls for a
routing comparison. A repair to output formatting calls for a paired output
check. A change to references or procedures calls for checking their use and the
result where the runner can observe both.

## How to evaluate a skill

| Evidence | What it can tell the author | Recommended check |
|---|---|---|
| **On disk and discoverable** | Which copy, if any, the project and agent are expected to read | Existing filesystem and consumer rules. Explicit unknown for undocumented precedence or listing truncation that cannot be observed. |
| **Simulated selection** | Which skill the configured model chooses from the supplied listing | Realistic saved positives and near misses, distractors, repeats and coverage. Label model and exact listing fingerprint. Always show the denominator and missing answers. |
| **Observed invocation** | Which copy or named skill a supported target agent actually loaded | Versioned event parsers and a completed trace. Record multiple loads where observable and separate missing from contradicted evidence. Agent prose alone is insufficient. |
| **Behavior and outcome** | Whether outputs satisfy the author-confirmed requirements and whether the procedure adds value | Paired current and proposed runs with the same model, fixtures and checks. Add a no-skill run when the question is whether the skill helps. Prefer deterministic assertions, show human-reviewable outputs, and label advisory rubric judgments. |

Guard against optimizers rewarding their own tests. Develop against observed
failures and open a held-out case set once a candidate is chosen. If held-out
results feed the next edit, establish fresh hold-outs for any subsequent promotion
claim. Test a new skill against near misses and neighboring skills as well as
its own positives. For edits that change procedure, add checks for preserved
exceptions and required outputs. Record the corpus, skill revision, consumer,
model, settings, repeats, and coverage. For small samples, show raw paired
counts and individual cases. An incomplete run can guide investigation without
earning a passing grade. [Agent Skills description guidance](https://agentskills.io/skill-creation/optimizing-descriptions),
[OpenAI eval guidance](https://developers.openai.com/blog/eval-skills).

Start native evaluation with imported or attended traces and a supported
adapter, building on the existing fixture work. Validate observations for a
clean load, no load, multiple loads, malformed or missing signals, and runtime
versions before offering general claims. Test first on synthetic, isolated
fixtures with limited access. Keep native agent availability, user authorization,
configuration and spend explicit. A native run through a different provider or
model from the simulator measures a different condition.

## Integration and data handling

- **Reuse the provider path.** Python's standard library, `AiRun`, existing
  Anthropic and OpenAI-compatible transports, provider selection and run/day
  admission stay the starting point. Use structured output where supported and
  validate locally on every provider. Tool execution is unnecessary for the
  authoring model. Provider capabilities and spend accounting vary, so show the
  destination and estimates and distinguish observed usage from billing.
  [Provider code](../skillsmgr/ai.py), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
  [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs),
  [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility).
- **Prepare context locally.** Pin the selected copy, scope, revision and
  provider configuration. Show what will be sent, including individual files or
  excerpts, and enforce file and token bounds. For library operations, retrieve
  candidates locally and disclose the shortlist. A shortlist-based answer can
  explain the retrieved candidates. A routing test that samples away other
  skills must disclose that sampling. Context can include private data even
  when names or descriptions are the only requested fields.
- **Treat proposals as data.** Validate operations, paths, fields, sizes and
  scope locally. Reject stale previews and changed candidate bytes before apply.
  Reuse content-bound review and snapshot machinery, including rollback. Keep a
  bounded private draft or run record where useful. Give users a retention and
  export choice for full prompt and output content, and prefer hashes and counts
  for long-lived receipts. Revalidate according to the full target
  scope when a user starts a separate deployment review. Filesystem ownership,
  the SQLite schema and the public Store and CLI contracts remain the repository
  constraints for the proposed first slice. [Review infrastructure](../skillsmgr/review_artifacts.py),
  [Repository rules](../AGENTS.md).
- **Keep the existing local service boundary explicit.** The localhost binding
  is the only security boundary for the unauthenticated web UI. Other local
  processes can reach it, including routes that spend against a configured key.
  Keep it loopback-only. Existing provider controls, no-send preflight, request
  limits and token reservations remain relevant. API timeouts, retries and
  cancellation can leave already accepted provider work billable.
  [Recorded provider and web decisions](39-ai-features-research-and-catalogue-2026-11-09.md).
- **Add background work when evaluation merits it.** A bounded server-owned
  stdlib queue can let a run survive page reloads, with a pollable run ID,
  progress, cancellation between calls and an interrupted state when the local
  process restarts. Capture the approved input and settings, deduplicate repeated
  submissions, keep run and day reservations, and make partial coverage explicit.
  Keep lightweight drafting on the existing request path until this complexity
  is justified. Native adapters and provider batching are optional later
  extensions with separate execution and data handling. [Existing web routes](../skillsmgr/webapp.py),
  [OpenAI background mode](https://developers.openai.com/api/docs/guides/background),
  [Anthropic message batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing).

## Proposed delivery sequence and measurements

| Release slice | Ship | Check before expanding |
|---|---|---|
| 1. Author | In-context Create with AI and exact-copy text edit, diff, intentional apply, Recovery. Reuse draft and shortening infrastructure. | Observe time to first saved valid draft and time to an accepted edit in paired manual and assisted tasks. Record corrections, stale-target handling, accidental scope writes, and recovery results. |
| 2. Prove | Test authoring from examples, exact-copy current vs proposed runs, and diagnosis from Doctor, simulator, and supported imported traces. Add a focused loop from failure to saved regression. | Run labeled fixtures for wrong and missing evidence, compare adjudicator and human decisions on a sample, and record coverage and costs separately from trigger and output changes. |
| 3. Maintain | Evidence-based registry and update briefings, port candidates, collection comparison, local discovery and targeted profiles, plus surfacing the relevant options from Sync map and Recovery. | Measure decision time, accuracy of selected copies, incorrect merge or port recommendations, and repeated use after subsequent changes. |
| 4. Expand | Pilot local transcript excerpts, comparative multi-agent runs, and versioned team handoffs. | Test whether people repeatedly bring their own workflows and whether maintaining the adapters and data controls is worth the observed usage. |

In the existing design-partner pilot, recruit a first-time author, a multi-agent
maintainer, and a team or client workflow owner. Ask each to bring a successful
real example and a failure they can share, or use synthetic equivalents. Capture
time, scope errors, harmful omissions, result acceptance, and willingness to
return at the next edit. Review these before setting numerical targets. Exercise
empty, one-skill and 10,000-entry fixture libraries, including same-name copies
and incomplete scans. Cover provider refusal, truncated answers, no-send mode,
out-of-order responses, double submissions and simultaneous edits. Confirm the
selected files, outbound context and rollback after a partial disk write. The
clearest early product signal is a user returning with a failed run, making a
small revision to the intended copy, and saving a regression case for next time.
