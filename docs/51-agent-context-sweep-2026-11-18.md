# Agent Context Sweep — 2026-11-18

**Version 0.2.0**

**AI manifest**: Research receipt for repository development context. Vendor discovery documentation and research findings are dated observations, not evidence of this checkout's agent behavior or product performance.

**[NOTE]**

Question: How should this repository present actionable guidance to coding agents while preserving its existing safety and product constraints? This is a targeted source check, not a systematic review. On 2026-11-18, web searches for agent distraction, the two specified arXiv IDs, and Claude/Codex discovery and imports were followed by direct checks of the sources below. No date filter was applied; the reviewed sources are in English. Primary reports and vendor documentation were included; search snippets and derivative commentary were not treated as independent evidence. No exhaustive screening, deduplication count, live model run, or independent replication was performed. The maintainer-supplied video transcript was the starting context; this receipt does not independently verify the video or treat its claims as separate experiments.

**[NOTE]**

| Source | Type and weight | Finding and boundary |
|---|---|---|
| [Google, Agent Distraction](https://developers.googleblog.com/agent-distraction/) (2026-11-06) | First-party observational industry report; useful signal, limited external validity. | Google's internal agent traces link exposure to bug-referencing TODOs with some unprompted secondary actions, including closed or unrelated tickets. Bug-ID actions and ticket status are proxies, not a controlled demonstration that all old documentation causes distraction; the population and tooling are Google's. Do not transfer its rates to this repository. |
| [Xu and Wu, arXiv:2610.30571v1](https://arxiv.org/abs/2610.30571v1) (2026-10-22) | Primary experimental preprint, submitted to a journal; no independent replication established here. | In 40 constructed Python projects, two agents across 320 runs often followed conflicting stale instructions; an added user-level sentence changed behavior in the tested setting. Synthetic examples and specific agents limit generalization. It does not justify overriding explicit user instructions, safety requirements, or intended migrations whenever code differs. |
| [Gloaguen et al., arXiv:2602.11988v3](https://arxiv.org/abs/2602.11988v3) (2026-09-29) | Primary benchmark study, preprint; useful comparative evidence with benchmark limits. | Across its tested settings, context files did not generally improve task success and increased average inference cost; the authors found that instructions were followed and non-standard practices could be useful. These results do not establish that every instruction file is harmful or quantify effects here. |
| [Claude Code skills](https://code.claude.com/docs/en/skills) | Vendor documentation; authoritative for documented intended behavior, not a local runtime test. | Project skills live under `.claude/skills/<name>/SKILL.md`. A skill directory entry may be a symlink to a directory elsewhere, and the target is loaded once if reachable by multiple locations. This documents a filesystem symlink, not a general path-alias configuration. Git/platform symlink support affects portability. |
| [Claude Code memory and imports](https://code.claude.com/docs/en/memory) | Vendor documentation; intended instruction loading, version and settings dependent. | `@path` in `CLAUDE.md` imports content into context; relative paths resolve from the importing file, and recursive imports have a four-hop maximum. Backticks make a path literal. Therefore an unquoted router pointer can eagerly load a document rather than defer reading it. |
| [Codex local skills](https://learn.chatgpt.com/docs/build-skills) and [AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | Vendor documentation; intended behavior, not a test of the installed CLI. | Repository skill discovery scans `.agents/skills` from the working directory through the repository root and supports symlinked skill folders. Instruction files merge from root toward the working directory, subject to a configurable combined size limit. Verify actual discovery separately for the installed version and session. |

**[NOTE]**

Application principles, inferred from these sources rather than measured here:

- Keep durable, non-obvious constraints and necessary safety boundaries visible; route task-specific detail to the relevant document. Historical records should be recognizable as historical and distinguish open work from completed work.
- When guidance and observed behavior conflict, inspect code, tests, current specifications, and task intent; surface the conflict and reconcile stale claims. Existing behavior alone is not authority to ignore a deliberate specification or requested change.
- Treat context changes as hypotheses: compare representative tasks and failure cases before claiming a benefit. Preserve essential instructions while reducing irrelevant material; brevity alone is not a measured outcome.
- Check literal versus eager-import syntax for each consumer. A relative symlink can make a canonical skill discoverable in Claude's documented project location, but portability, checkout integrity, and actual invocation remain to be verified. Do not infer deployment or automatic invocation from file existence alone.

**[?]**

The studies cover different populations and interventions. Their results describe those settings. This project has yet to measure instruction accuracy, task success or token use after the context changes.

## First repository sweep

**[NOTE]** The first sweep focused on current startup and handoff guidance.
An independent reviewer identified the drift, then checked the corrections
against normal entry points and local history. Historical checkpoints remain
available as evidence.

| Finding in the starting checkout | Evidence for the correction |
|---|---|
| The current session guide said v1.0.2 was unpublished. | The published version and completed recovery are recorded in @docs/06-progress-log.md. The live task status was already complete. |
| The common-task router sent default UI edits to classic files. | The `/` redirect in `skillsmgr/webapp.py` and the scripts at the end of `skillsmgr/webui/v2/index.html` identify the actual v2 entry point. Classic has its own router row. |
| The guide said `skillsmgr/insights.py` was gone. | The module at the refactor commit `e4e100b` and the current checkout both expose a compatibility API. |
| Data path notation appended `skills-manager` twice for the database. | The current `skillsmgr/paths.py` appends the name to the selected base once. `db_path()` appends only the database filename. |
| The decision notes still described a required release reviewer. | The dated release changes and complete workflow run establish closure. |
| The ledger labeled an older batch as the latest. | The 2026-11-18 continuation and subsequent release commits are newer than `5ada04a`. |

## Tool placement

**[SPEC]** The canonical procedure lives in
[the developer tools directory](../tools/context-sweep/SKILL.md).
Claude Code has a short manual command that reads the same procedure.
Codex uses the explicit route in `AGENTS.md`. An earlier trial under
`.agents/skills` and `.claude/skills` registered both copies in the product's
project inventory and exposed a test writing into the checkout. That trial
was moved out of the managed roots. Historical files remain readable for
targeted evidence requests. Routine work uses the live ledger and active
specs.
[Claude command files](https://code.claude.com/docs/en/skills#where-skills-live)

**[NOTE]** An isolated Claude Code 2.1.325 startup listed `context-sweep`
among the project slash commands. The test ran in a network namespace and
checked discovery. Validation also confirmed that the canonical procedure
and wrapper point to the same file and live outside the managed skill roots.
