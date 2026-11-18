# Context Strategy — Session Loading Model

**Version 0.3.0**

**AI manifest**: How to scope repository context, hand off active work, and verify stale guidance. `AGENTS.md` summarizes the rules agents need at session start.

## The model

**[SPEC]** Three tiers:

| Tier | Contents | Loaded |
|---|---|---|
| Hot | `AGENTS.md` (root), imported by `CLAUDE.md` | At the start of a session |
| Warm | The active task, its owning spec, and the relevant entry points and tests | As needed for the requested work |
| Cold | Archived docs, completed plans and older Git history | For a specific evidence question |

**[SPEC]** Rules:
- Read `AGENTS.md` fully (it is deliberately small — the hot cache).
- Use the router table in `AGENTS.md` to pick the one or two `@docs/...` files for the current task. Backticks keep those pointers literal in Claude Code's import syntax.
- Prefer explicit pointers (`@docs/04-store-api.md`) over inlining content in this doc or in answers. For source citations use **symbol names** (`Store.edit`, `webapp.MAX_BODY_BYTES`, `archive.commit_staged_skill`) rather than `file:line`: by 2026-09-11 most line numbers in the security docs and `docs/04-store-api.md` had drifted onto unrelated code, while a symbol name fails loudly when it is renamed.
- In the live section of `task.md`, `[ ]` means pending, `[/]` means in progress,
  and `[x]` means completed. Deferred items carry their decision or blocker.
  Update the status and its evidence after each change. Historical
  checkboxes can document prior work and decisions.
- Verify actual behavior through the normal entry point and relevant tests.
  Establish intended behavior from the current request and active project
  decisions. When intent changes, link or update the affected spec and
  task before marking implementation complete. Label retired guidance as
  superseded and name its replacement.

## What to load when

| Task | Load |
|---|---|
| Any change to `store.py` | @docs/04-store-api.md + run `python3 smoke_store.py` |
| Any change to `webapp.py` / a REST endpoint | @docs/08-web-ui.md + run `python3 smoke_web.py` |
| Any CLI work / GUI mirroring | @docs/03-cli-surface.md |
| GUI build or testing | @docs/08-web-ui.md + @docs/04-store-api.md (the GTK plan in @docs/05-gui-plan.md is a labelled historical record) |
| Any edit to `skillsmgr/` internals | @docs/02-modules.md |
| Anything touching paths/data | @docs/01-architecture.md (data-dir layout, symlink policy, locking model) |
| Long session or after compaction | `AGENTS.md` (re-anchor) + @docs/07-context-strategy.md + @docs/06-progress-log.md |

## Compaction anchors

**[SPEC]** Start a fresh session for an independent task when practical.
When handing off planning or recovering from compaction, check the latest
request, active status, relevant spec, verification already performed and
the next unfinished step. Load the newest applicable receipt in
`docs/06-progress-log.md` as needed. Keep unrelated work in the ledger.

## Context sweep

**[SPEC]** For a read-only audit of stale guidance, use `/context-sweep` in
Claude Code or ask Codex to run the
[context sweep](../tools/context-sweep/SKILL.md) by path. The procedure
lives under developer tools so it stays outside the product's managed skill
roots. Pass a topic or paths to narrow the review. Findings cite current
evidence and the history or decision behind it. The report distinguishes
confirmed factual drift, unresolved intent and insufficient evidence.
The same evidence applies when separately reviewing a proposed archive move.
See `@docs/51-agent-context-sweep-2026-11-18.md` for source findings and limits.

## Budget guidance

**[NOTE]** Keep hot cache small (AGENTS.md <=150 lines) so ~100% of it can stay resident. Aim to stay within comfortable context utilization (roughly 40–60%) on typical sessions; load cold files, extract the facts, then drop them. `docs/` files themselves follow HADS so they read compactly for models.

## Open questions

- `[?]` None. If a session reveals a better loading pattern, record it here and bump the version.
