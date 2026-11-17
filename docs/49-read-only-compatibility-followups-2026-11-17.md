# Read-only Compatibility Follow-ups — 2026-11-17

**Version 0.1.0**

**AI manifest**: Boundaries for the second five-task continuation after `5ada04a`.
Existing hygiene surfaces consume these observations; no native setting is
changed and no new command, Store method, schema or runtime dependency is added.

## Evidence and implementation

**[SPEC]** Local declarations and filesystem layout are evidence about files,
not about what an active consumer session loaded.

| Task | Delivered observation | Boundary and primary source |
|---|---|---|
| Grouped personal Claude folders | Two-level personal groups without their own primary document, excluding `synced` and plugin roots | Flat inventory and listing estimates stay unchanged. [Claude docs](https://code.claude.com/docs/en/skills#load-skills-in-monorepos-and-subdirectories) describe nested project roots, not recursive personal discovery; [#18192](https://github.com/anthropics/claude-code/issues/18192) does not justify changing the scanner. |
| Codex project declarations | Boolean `skills.include_instructions` and bounded name/path rule kinds plus `enabled`, from the explicitly supplied project's `.codex/config.toml` | Selector values are omitted. Trust, ancestor/managed/profile/CLI layers, installed version and session effect remain unknown. [#24237](https://github.com/openai/codex/issues/24237) is an attributed issue report, not a current runtime verdict. |
| Plugin manual-only intent | An enabled readable member of a named plugin declares boolean `disable-model-invocation: true` | [Current invocation docs](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill) describe the intent; [#22345](https://github.com/anthropics/claude-code/issues/22345) reports contrary behavior in 2.1.29. The separate `skillOverrides` plugin limitation is not this key. |
| Lockfile provenance ambiguity | Colliding lock names that normalize to the same installed folder; source-path syntax/type/parent-segment/truncation evidence | No source checkout is scanned or unique upstream path elected. [Upstream lock interface](https://github.com/vercel-labs/skills/blob/main/src/skill-lock.ts) permits folder or document paths. [#2406](https://github.com/vercel-labs/skills/issues/2406) and [#2574](https://github.com/vercel-labs/skills/issues/2574) are closed upstream; their old defects are not asserted here. |
| Completed history archival | Byte-preserved historical entries in indexed cold files; current queue retained | @docs/archive/README.md defines the lossless rule. Relative-link sections remain at their original paths. No skill data or prior archive changes. |

## Report contract

**[SPEC]** `codex_project_config` and `claude_grouped_folders` are additive
sections in the existing hygiene result. Findings use the generic Quality
layout and existing CLI rendering. Relevant scopes only inspect their extra
roots. Missing files, unavailable observations and partial/truncated evidence
are distinct. Incomplete attempted advisory observations remain partial in their own sections
and unavailable signals. They do not invalidate a complete primary-document
baseline; filesystem acquisition failures still do. CLI text and both UI
versions expose the observed group names, without turning them into instances.

The Codex observer reads at most 1 MiB and inspects at most 50 rules. It pins
each directory with no-follow descriptors and uses Linux `/proc/self/fd` for
the bounded final read; unsupported hosts report unavailable. The grouped
observer requires descriptor-based directory traversal, never follows links,
and inspects at most 4,096 entries across both levels, returning at most 50
groups and 50 names per group, with names capped at 128 characters. It reads
document names/types, not document contents. Neither scan is an atomic snapshot.

Lock comparisons retain their existing entry/hash budgets. `source_path`
contains syntax observations only and keeps `resolution: unverified`. Display
truncation of a long lock name does not choose its installed directory: the
full key is sanitized first. A collision identifies shared local addressing,
not which entry or upstream source is correct. Reported paths are home-redacted.

## Verification and limits

**[NOTE]** Focused observer, report, CLI and lockfile regressions cover malformed,
missing, oversized, unsafe, truncated and unsupported-platform evidence, plus
unchanged files and listing counts. Final current-tree verification is recorded
in @docs/06-progress-log.md. Native comparison, real Windows/macOS execution,
human visual/spoken-screen-reader sign-off and publishing are separate tasks.
Issue reports were checked as reports, not independently reproduced native bugs.
