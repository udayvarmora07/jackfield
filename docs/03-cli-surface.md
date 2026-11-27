# CLI Surface — Jackfield

**Version 0.6.0**

**AI manifest**: Authoritative inventory of every command, alias, flag, and exit code of the `jackfield` CLI. Facts verified against the parser/handler modules (`cli_parser.py`, `cli_handlers.py`, `cli_output.py` behind the stable `cli.py` adapter) plus live invocations on 2026-09-22. Usage consent, archive lifecycle and reviewed project changes are CLI-only. See @docs/08-web-ui.md for the shared web surface. Do not add commands or flags without updating this doc and @docs/02-modules.md.

**[SPEC]** Invocation: `python3 -m skillsmgr` (or `jackfield` once installed). argparse `prog="jackfield"`. Command count: **33 top-level commands + 28 subcommands + 3 aliases (`ls`, `rm`, `gui`) = 64 invocable names**. The `gui` alias is a pure alias of `webui` (the GTK GUI is gone).

## Usage, lifecycle and project controls

### `usage`

- `usage enable --agent AGENT [--agent AGENT ...] [--json]` grants consent
  for exact transcript roots. Supported agents are `claude-code`, `codex`,
  `opencode`, `gemini`, and `commandcode`.
- `usage report [--agent AGENT ...] [--days N] [--refresh] [--json]` reads
  stored aggregates by default. `--refresh` scans authorized roots. Days
  defaults to 90 and accepts 1–400 UTC dates including today. Reports show
  separate explicit and inferred counts and the earliest and latest dates
  observed in that window. Changed roots require fresh consent. OpenCode's
  database follows an absolute `XDG_DATA_HOME` and any explicit `OPENCODE_DB`
  filename or absolute path. Give an explicit filename for a nondefault
  channel database. In-memory databases have no local transcript source.
  OpenCode refreshes need a checkpointed database. If its write-ahead log
  still has frames, close OpenCode and refresh again. A cached report
  suppresses aggregates when consent and cache roots disagree.
- `usage disable [--agent AGENT ... | --purge] [--json]` revokes selected
  consent, or all consent when no agent is named. `--purge` also erases
  cached usage data.

### `lock`

- `lock verify --project DIR [--json]` compares Vercel lock entries with
  `DIR/.agents/skills` offline. Exit 1 signals drift or incomplete evidence.
- `lock write NAME [NAME ...] --project DIR [--source NAME=PATH ...]`
  `[--dry-run | --plan-id HASH] [--json]` defaults to preview. A new
  entry requires an explicit project-relative source with bytes matching
  the installed skill. Apply repeats the same arguments with the plan ID.
  Writes support v2 and retain untouched entries and unknown fields.
- `lock undo --project DIR --plan-id HASH [--json]` restores the preimage
  if the current file still matches the recorded write.
- Preview can read a write-protected lockfile. Apply and undo require write
  access to an existing lockfile before replacing or removing it.

### `native-profile`

- `native-profile preview --project DIR --agent AGENT`
  `(--off NAME ... | --profile NAME) [--json]` reviews declarations for
  one project. `--profile` reads the native off list saved in v2 Profiles.
- `native-profile apply --project DIR --agent AGENT`
  `(--off NAME ... | --profile NAME) --plan-id HASH [--json]` applies a matching preview
  for supported Claude Code, Gemini, and OpenCode settings. Codex preview
  provides launch arguments and Command Code preview gives a manual patch.
- `native-profile undo --backup-id ID [--json]` restores the preimage if
  the current settings still match the recorded file and bytes. An
  interruption after replacement leaves the backup ID available in the
  diagnostic and the receipt in `native-backups`.

### `archive`

- `archive apply NAME [--plan-id HASH] [--json]` previews one named
  manager-library copy. Supplying the matching plan ID moves the complete
  unpinned folder to private archive storage. The preview shows the exact
  source, destination, folder digest and archive ID. The plan binds the
  reviewed tree and is single-use. Select copies for this command yourself.
- `archive restore ARCHIVE_ID [--json]` verifies the saved folder and moves it
  back to its original library address if the destination is unoccupied.
  Save the archive ID from the preview or result. The receipt also identifies
  the name under `archive/global/<id>/ARCHIVE.json` in the data directory.
  These moves require the same filesystem and accept ordinary directories and
  single-link regular files, up to 10,000 entries, 16 MiB per file, and 256 MiB
  total. Archive payloads are outside Trash and outside the current backup
  export. Preserve the archive directory when backing up or migrating it.
- `archive candidates [--scope SCOPE] [--days N] [--json]` combines
  inventory, pins and cached usage. The default scope is `global`.
  The activity window includes today and the preceding `N - 1` UTC dates.
  `in-use` indicates a cached usage event or a primary document modified in
  that window. JSON `last_edit` is the observed document modification time
  when available, and `used_by` lists the agents with same-name cached events.
  The `reason` and text view distinguish this name match from document
  modification evidence. Inventory reports which scope roots were scanned,
  missing, incomplete, shared with another scope or skipped by the row cap.
  A scanned empty root and a broken root are distinguishable in JSON.
  `relative_path` identifies the folder under its scope root when available.
  The text view includes nested folders so same-name copies can be told apart.
  Scopes that resolve to the same directory are scanned separately when their
  discovery rules differ. The preview includes discovered project-root aliases.
  A row that represents several equivalent scopes reports a pin if any of
  those scopes has one. JSON `pinned_scopes` identifies the scopes with a pin.
  The JSON `archive_readiness` field lists the documented readers for the
  selected scope IDs, including matched project-root conventions and readers
  of other selected scopes observed at the same physical root. These are
  root-level hints. Individual consumers may discover different copies there.
  The field includes their last transcript scan statuses and states
  the outstanding consumer mapping, usage, and edit/install prerequisites.
- `archive pin NAME [--scope SCOPE] [--note TEXT] [--plan-id HASH] [--json]`
  and `archive unpin NAME [--scope SCOPE] [--plan-id HASH] [--json]` preview
  by default and mutate only with the matching plan ID.
- `archive undo-pin --plan-id HASH [--json]` restores the previous pin
  state if the current file matches the recorded write. A new pin or unpin
  remains undoable if the process stops just after replacing the pin file.

Archive eligibility needs continuous observation for all potential
consumers. The current transcript parsers cannot establish that coverage.
This version reports evidence and manages pins without moving skills.
See @docs/54-usage-lifecycle-lock-native-profiles-2026-11-20.md.

## Read-only compatibility findings

**[SPEC]** Existing `doctor --hygiene` output and JSON expose grouped personal
Claude folders, supplied-project Codex declarations, plugin invocation intent,
lock-name collisions and source-path uncertainty. The observations do not
change inventory or native state. Existing scope/project flags and exit
behavior remain unchanged; no command or flag is added. Details and bounds:
@docs/49-read-only-compatibility-followups-2026-11-17.md.

## Shell completion

**[SPEC]** The installed package includes static Bash and Zsh completion scripts.
For the current shell, source the matching file (after `compinit` in Zsh):

```bash
# Bash
source "$(python3 -c 'import pathlib, skillsmgr; print(pathlib.Path(skillsmgr.__file__).parent / "completions/skills-mgr.bash")')"
# Zsh
source "$(python3 -c 'import pathlib, skillsmgr; print(pathlib.Path(skillsmgr.__file__).parent / "completions/_skills-mgr")')"
```

Completion offers command names, options and common scope values from a static
snapshot; it does not inspect installed skills or contact the network. It does
not change shell startup files. Python 3.14 also suggests close matches for
invalid commands when argparse supports it; invalid input still exits with code 2.

## Exit codes

**[SPEC]**

| Code | Meaning | Raised when |
|---|---|---|
| 0 | OK | `args.func(args, store)` returns None/0 |
| 1 | Error | `StoreError`, `ValueError`, or `OSError`; message printed via `_err` |
| 2 | Usage | No subcommand given (help shown); argparse usage errors |
| 130 | Interrupted | `KeyboardInterrupt`; prints `interrupted` |

`__main__.py` wraps `cli.main()` in `sys.exit(...)`, so exit codes propagate to the shell.

**[SPEC] Typo hints (2026-11-19).** An invalid command or other choice ends its
usage error with `-- did you mean '<choice>'?` when one is close (argparse's own
`suggest_on_error` on 3.14, a `difflib` fallback before it). A missing library
skill (`scope` unset or `global`) appends `; did you mean '<name>'?` with up to
three close folder names that pass the skill-name rule. Exit codes are unchanged
(2 and 1); agent-scope errors keep their exact text.

Before Store construction and command dispatch, skill-name arguments are checked
against the canonical `NAME_RE` contract. Invalid names, path fragments, and
encoded traversal-style values therefore fail with exit code 1 without creating
or mutating the data directory.

## Global and command flags

**[SPEC]**

- `--json` — a per-command flag, placed after the command, for machine-readable output; `_print_json(data)` with indent=2.

- `--color` — force color output.
- `--no-color` — disable color output. The default is automatic terminal detection.
- `--scope SCOPE` — scope selector on `list`, `view`, `search`, `doctor`, `stats`. Values: `global` (default; the Store + DB), `all` (aggregate commands only; `view` requires one scope), an agent scope ID (`claude-code`, `codex`, `cursor`, `opencode`, `gemini`, `commandcode`, `agents`), or a discovered project scope. `agents` uses the shared `~/.agents/skills` root.
- Existing `.gemini/skills` and `.commandcode/skills` folders in the current project appear as `project-gemini` and `project-commandcode`. Gemini inventory reads skills in immediate child folders. Command Code inventory also reads grouped skills, stopping at the first active or disabled skill document in each branch of the tree. For a Gemini `SKILL.md` directly in a Gemini or shared skills root, `doctor --explain gemini` reports a read-only file observation. Archive preview marks that root's managed inventory partial.

**[NOTE]** The scope flag is a **per-command flag**, not a global flag — each scope-aware command declares its own `--scope`. `tokens` and `install` also accept `--scope` with their own semantics (see below).

## Commands

**[NOTE]** `ls` and `rm` are aliases of `list` and `remove` — they are NOT separate commands. `gui` is an alias of `webui`.

### `ai trigger-test --saved [--scope SCOPE] [--seed N] [--repeats N] [--run] [--baseline RUN_ID] [--fail-on-regression] [--json]`

**[SPEC] A14, approved 2026-11-09.** Estimate the scope's saved A7 prompts by
default; only `--run` contacts the configured provider using existing settings,
environment credentials and token caps. `--saved` is required. Scope defaults
to `global`; choose one scope (`all` is refused). At most 120 prompts and 1–5
repeats; missing expected skills are errors. Seed defaults to 0 and accepts an
initial integer 0–4294967295; each repeat shuffles the sorted listing using
`seed + repeat_index`. This controls local order, not provider determinism.

`--baseline` pins an existing retained run; otherwise the newest modified
saved-prompt trigger run is considered (ID order breaks ties). A requested
`--fail-on-regression` requires `--run` and complete matching scope, prompt,
provider/model/endpoint, seed, repeats and routing-version evidence before any
request. Listing changes are allowed and disclosed. Integer hits/answers are
recomputed, including expected-none prompts. A measured decrease fails the
requested gate; incomplete current answers fail with or without that flag.
Missing, incompatible, legacy or damaged baselines cannot pass the gate.

JSON is a versioned `{schema_version: 1, command: "ai trigger-test", status,
result, comparison}` envelope; errors use `{error: {code, message}}`. It includes
prompt text, listing snapshots and fingerprints, so keep artifacts/logs private.
No credential argument, skill write, Store method or index initialization is
added. Exit codes remain 0/1/2/130. Argparse usage errors remain text on stderr.
Detailed states, limits and private-artifact CI recipe:
@docs/42-ai-cli-ci-2026-11-09.md.

### `ai ablate NAME [--section N] [--trials N] [--max-cases N] [--placebo] [--run] [--json]`

**[SPEC] docs/60 G1, approved 2026-11-22.** Tests whether a library skill, or
one headed section of it, earns its place. It replays the skill's
`evals/evals.json` cases with the whole skill and without it (or without the
section), `--trials` times each (1–5, default 3), in a random order. Without
`--run` it prints the section numbers, the planned call count and the egress
and sends nothing. The decision is `untested` when every answer passes (or
every answer fails) with and without it, since such cases cannot show harm;
`keep` when the whole 95% interval for the lift is above zero; otherwise `remove` when its upper end is at most 10 points
(ties go to removal), `uncertain` otherwise, and `not-enough-evidence` below 3
graded cases or 4 graded pairs. A run with a missing, cut-off or ungraded
answer is `partial` and never proposes removal. `coverage_warning` says when no
check's pass rate differed, since such cases may not test the removed text. A section
`remove` stages an ordinary reviewed edit, applied with `update apply`; a
whole-skill `remove` prints the demotion ladder (slash-only, `disable`,
`archive apply`) and writes nothing. A turned-off skill is refused. JSON is
`{schema_version: 1, command: "ai ablate", status, result}`; saved evidence
keeps pass counts, not outputs. `--placebo` adds a third variant with the
removed text swapped for neutral filler of the same length and reports
`placebo_statistics` (whole skill against filler); the decision still compares
the whole skill with the removal. `previous` names the newest saved ablation
for the same target with its decision, model, and whether the model and skill
revision match. For a section run, both the section and skill revision must
match to avoid attributing a result to the wrong section after an edit.

### `ai conflicts [--scope SCOPE] [--project PATH] [--judge] [--max-pairs N] [--votes 2|3] [--run] [--json]`

**[SPEC] docs/60 G2, approved 2026-11-22.** Lists heuristic candidate pairs of
instruction lines that may contradict: `~/.claude/CLAUDE.md`,
`~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, the project's `CLAUDE.md`,
`CLAUDE.local.md`, `.claude/CLAUDE.md`, `AGENTS.md` and `GEMINI.md`, against
each other and against the enabled skills of one scope (default `global`;
`all` is refused). Every pair involves at least one instruction file;
skill-against-skill conflicts are the overlap judge's job. No model is used
unless `--judge`; `--judge` alone estimates, and `--run` (which requires
`--judge`) sends only the two quoted lines of the top `--max-pairs` pairs
(1–40, default 20), twice with the two lines in opposite orders, or three times
with `--votes 3` (both orders and a repeat that lists the pairs in reverse order
under a distinct header; it adds evidence only when the model samples); a
verdict counts only when every call agrees, otherwise it is `unclear`. Quotes always
come from the files. Project files that link
outside the project are reported as unreadable. Precedence between the two
sides is reported as `unknown`. Lines longer than 400 characters are skipped
rather than cut, skill documents that are links are not read, line numbers
count `\n`, `\r\n` and `\r` only, and inputs dropped by size bounds are listed in
`inputs_limited`. The report also counts directive lines per instruction file
(`density`, `dense` above 150, `with_reason` for lines that state a reason,
`conditional` for "if/when…" and `prohibitive` for "never/don't…" lines) and, with `--project`, lists `stale_references`:
code spans in the project's instruction files naming a path, a
`npm`/`pnpm`/`yarn`/`bun` script, a `make` target or a Python file that does not
exist in the project. Only spans resolving inside the project are checked; a
bare file name is stale only when no file of that name exists in the project
(trees over 50,000 entries are not judged). Writes nothing except the saved run
evidence.

### `init [--json]`
Create the data directory layout and initialize the SQLite index.

### `list` / `ls [--json] [--disabled] [--category CAT] [--scope SCOPE]`
List skills in the scope (default global) with a STATUS column (`active`/`disabled`); disabled skills are shown marked and `--disabled` narrows the list to disabled skills only. `--category` filters; `--scope all` merges every scope and adds a SCOPE column. DESCRIPTION/CATEGORY cells are sanitized before printing (see *Untrusted display text*).

An empty, unfiltered global text listing also checks agent scopes and prints
their populated counts with a `list --scope all` hint. JSON, named-scope and
filtered listings keep their existing output and avoid this extra scan.

### `create NAME [-d/--description TEXT] [--license LIC] [--category CAT] [--compatibility SPEC] [--version VER] [--allowed-tools TOOLS] [--metadata KEY=VALUE] [--body TEXT] [--body-file PATH] [--json]`
Create a skill in the global store. Name must match `NAME_RE`; description required. `--body` and `--body-file` are mutually exclusive.

**[NOTE]** `create` is global-only in the CLI — agent-scope creates go through the web UI (`POST /api/skills?scope=`) or `scopes.create_skill()`.

### `add PATH [--name NAME] [--json]`
Add an existing skill directory (or SKILL.md file) from `PATH` to the global store. `--name` chooses the target directory name; existing
frontmatter `name` must already match it, so this flag does not rename the document.

### `view NAME [--raw|--json] [--scope SCOPE]`
Print a skill. `--raw` prints the full `SKILL.md` file (frontmatter + body, not body-only, and verbatim — `--raw` is deliberately unsanitized); `--json` shows structured data (agent-scope detail includes token estimates;
global JSON is the Store record and does not add tokens). `--scope all` is
unsupported for this name-addressed command; choose one exact scope. The output modes are incompatible: passing both `--raw` and `--json` is rejected with a clean exit-1 `StoreError`; neither mode silently overrides the other. In the default text form every field value is sanitized (see *Untrusted display text*); `--json` and `--raw` emit the stored bytes unchanged, so pipe JSON through a formatter rather than to a raw terminal.

### `edit NAME [-d TEXT] [--license LIC] [--category CAT] [--compatibility SPEC] [--version VER] [--allowed-tools TOOLS] [--metadata KEY=VALUE] [--body TEXT] [--body-file PATH] [--json]`
Edit a skill in the global store. All fields optional; partial update. Repeated `--metadata` appends.

**[SPEC]** `--metadata` **rejects a key containing a control character** (a newline above all) with `error: metadata key must not contain a control character, got '...'` and exit 1, before anything is written. It used to write a `SKILL.md` the tool could not parse, exit 0, and let a later `edit` append a *second* frontmatter block (CLI-2). The dumper's own guard (`frontmatter.dump_frontmatter`) independently raises on a key it cannot render, so a bad key fails loudly rather than emitting junk (FM-9, partial).

**[SPEC]** `edit` also **fails closed on an unparseable document**: when the existing frontmatter is malformed the command prints `error: cannot safely edit skill '<name>': its frontmatter is malformed (<reason>); repair it by hand first` and exits 1 with the file left byte-for-byte untouched. It no longer treats "no frontmatter parsed" as "no frontmatter present" and rewrite the document into a second block, which had silently discarded the original metadata (CLI-2, SCOPE-12). The same guard protects agent-scope edits through `scopes.edit_skill`.

### `open NAME`
Open the skill file in `$EDITOR` (falls back if unset). Global store only.

### `remove` / `rm NAME [--purge|--trash] [--json]`
Delete a skill from the global store. Default moves to trash; `--purge` deletes permanently.

### `disable NAME [--json]` / `enable NAME [--json]`
Toggle enabled state in the global store (renames `SKILL.md` <-> `SKILL.md.disabled`).

### `validate [NAMES...] [--all] [--path DIR] [--evals] [--evals-run FILE] [--workspace DIR] [--json]`
Validate skills by name, all (`--all`), or a directory (`--path`). Prints issues.
Target selectors are mutually exclusive; `--workspace` is valid only with
`--evals` or `--evals-run`, and ignored combinations fail with a clean exit-1
error rather than silently discarding an argument.

`--evals` also reports the advisory eval harness status per target
(`evals/evals.json` case count, malformed-content errors, missing input files,
and the run workspace path). Eval findings never change `valid` or the exit
code. `--evals-run FILE` scores runs from a JSON file
(`{iteration, runs:[{case, variant, output, duration_ms?, tokens?}]}`, or a bare
run list) and records `outputs/output.txt`, `grading.json`, `timing.json`, and
`benchmark.json` in the iteration workspace; it requires exactly one target and
a valid case file. `--workspace DIR` overrides the workspace location (default
`<data>/evals/<name>-workspace`; with `--path`, `<DIR>-workspace` only when
`DIR` is outside the store's `skills/` tree, since a sibling workspace inside
`skills/` would be scanned as skill data). Eval
results are workspace files only — never SQLite rows — and never gate installs
or edits. See @docs/ADR-003-registry-bridge-and-eval-harness.md.

### `search TERM [--limit N] [--json] [--scope SCOPE]`
Search with scoring (see @docs/02-modules.md); `--limit` caps results. `--scope all` searches every scope. The global portion always uses the Store selected by `--data-dir`; merged search keeps that same requested global store while agent scopes use their filesystem adapters.

### `import ARCHIVE [--force] [--full] [--json]`
Import a `.tar.gz`/`.tgz`/`.tar` or `.zip` archive of skills into the global
store. Content is sniffed rather than trusted from the filename. Tar and ZIP
imports enforce resource budgets, reject traversal/Windows/special members, and
use a strict versioned `jackfield` manifest contract; `--force` overwrites
existing names with staged per-skill recovery.
`--full` restores trash, templates and catalog metadata from a full export.
It checks any recorded skill checksums before changing the library or its
recovery data.
Trash, templates and catalog metadata roll back together on failure. They
finish before active skills are installed. Individual install failures after
preflight appear in `skipped`.

### `export [--dest PATH] [--full] [--json]`
Export all skills (global scope only) to an archive. `--dest` names a file,
not a directory. An explicit existing file is atomically replaced. With no
`--dest`, each publication chooses its own filename under `backups/`, even
when multiple backups start in the same second.
Choose an explicit destination outside managed state. Within the data
directory, `backups/` and existing root-level `.tar.gz` naming conventions
are supported. The command reports the saved archive path.
`--full` includes trash, templates and catalog metadata. Alias: `backup`.
The finished TAR must pass import size and member checks before replacing an
existing destination. Unreadable supporting folders stop the export. Retry if
export reports that the source changed while it was being read. TAR supports
up to 12,000 members and 12,000 directories
within the byte limits in @docs/04-store-api.md.

### `backup [--dest PATH] [--full] [--json]`
Alias of `export` (identical behavior).

### `restore NAME [--snapshot TS] [--scope SCOPE] [--json]`
Restore a skill from the trash, or roll back to a retained snapshot.

### `history [NAME] [--limit N] [--json]`
Show recent history. When `NAME` is supplied, JSON output includes retained
snapshot IDs and text output lists them after the history table.

### `doctor [--json] [--scope SCOPE] [--hygiene] [--explain CONSUMER [--project DIR] [--skill NAME]]`
Health check: data dir, DB, skill files, consistency between FS and index, content drift, incomplete transaction artifacts, temporary files, and stale snapshots. `global` (the default) runs the Store/DB doctor; an agent scope scans that scope's filesystem directly and reports malformed documents; unknown scope ids are clean errors with exit 1. With `--scope all`, the global Store report also lists per-scope counts and same-name duplicates (`scopes.find_duplicates()`: name, scopes, descriptions-differ flag — converge with `sync`); `--json` adds a `duplicates` key. The historical “all filesystem is healthy”
headline reflects the global Store report only; it is not an aggregate
validation of every agent document. Use named-scope doctor or hygiene for
those findings. `--project` is evaluated only with `--explain`.

An empty filesystem tree with no index is a healthy first run; Doctor creates
nothing. A missing index with surviving skills/trash, or an existing unusable
index even with no skills, still reports repair guidance. In text output,
`scopes`, Doctor and hygiene abbreviate paths under the current home as `~/…`;
JSON retains absolute paths.

`--explain CONSUMER` switches to the read-only effective-resolution diagnostic
(issue #12): it derives, at read time, which instance of a skill that consumer
would load for `--project DIR` (default: the current directory), reporting the
winner plus the instances it shadows and the primary source behind the decision.
It writes nothing — no file, no SQLite row, no cache — and `effective_state`
stays `unresolved`. Consumers with a recorded precedence row: `commandcode`
(six-way order), `codex` (explicit no-merge, so no winner is elected),
`claude-code` (personal > project for the conflict pair, with nested copies
reported under `also_loads` because they both load), `gemini` (built-in <
extension < user < workspace, same-tier ties reported as `ambiguous`),
`opencode` (built-in < `.claude/skills` < `.agents/skills` <
`~/.config/opencode/skills` < project `.opencode/skills` < explicit `skills`
config; the config tier is unobservable here, so a lower win is provisional),
`cline` (global > project; the three project roots tie as `ambiguous`), `kiro`
(workspace > global), `amp` (first frontmatter `name` in its documented search
order), `roo` (project > global, `.roo` > `.agents`, mode-specific > generic —
the four mode-specific tiers are unobservable without a mode slug), and `zed`
(project > user `~/.agents/skills`). `cursor`, `copilot` and `devin` document no
same-name order and therefore return `undocumented-precedence` instead of a
guess. An unknown consumer returns
`unknown-consumer` and exit 1; a missing `--project` directory returns
`missing-project` and exit 1. Diagnostics that legitimately resolve nothing
(`no-merge`, `undocumented-precedence`, `no-instances`) exit 0. `--skill NAME`
narrows the report to one name. See `effective.py` in @docs/02-modules.md.

`--hygiene` adds the deterministic, read-only Skill Hygiene Report under the
`hygiene` JSON key, or after the ordinary Doctor sections in terminal output.
It accepts `global`, one known agent/project scope, or `all`; `all` scans the
deduplicated observed instances from the configured scope roots. The report
covers malformed/unreadable documents, validator references and description
guidance, exact duplicate and same-name drift groups, bounded heuristic
near-duplicate candidates, context hotspots, and source-lock evidence. It also
lists degraded and unavailable signals. The report's `lockfiles` section reads
the `skills` CLI's global `.skill-lock.json` (version 3) and, when a project
root context exists, its project `skills-lock.json` (version 1), then reports
declared/present/disabled state, `computedHash` and `skillFolderHash` comparison
status, and undeclared installed skills. v2 Quality can provide a contained
project context for the same report, which then shows presence-only APM
evidence. The CLI's human output adds one bounded lockfile summary line.
The report leaves files untouched and offers individual findings;
findings return exit 0 once the scan completes, while a total acquisition
failure returns exit 1. `--hygiene` and `--explain` are incompatible and
produce a clean exit-1 error.

The report's `claude_listing` section estimates what the Claude Code skill
listing puts in front of the model: one entry per listed `claude-code` scope
skill, `off` overrides excluded, `name-only` counted as its name, every other
entry capped at `skillListingMaxDescChars` (default 1,536) for
`description` plus `when_to_use`, and `SKILL.md.disabled` instances never
listed. The character budget comes from `SLASH_COMMAND_TOOL_CHAR_BUDGET` when
it is set, otherwise `skillListingBudgetFraction` (default 0.01) times the
token window, with the character figure reported as an estimate because the
documented conversion is not published. The section also lists name-only
candidates ordered by description size and an over-cap count. Those candidates
are **by size only**: Claude Code drops descriptions starting with the
least-invoked skills, which this tool cannot observe, so it never claims which
descriptions are dropped. The human output prints one summary line, for example
`Claude Code listing: 41,200 chars vs ~40,000 budget (estimate); 25 name-only
candidates`. Every number is read-only evidence; no listing is edited.
The text summary shows candidate counts only at 90% or more of a known
estimated budget. Unknown budgets and smaller listings omit that advice;
the JSON candidate evidence remains available at every size.

The report's `codex_config` section (`--scope codex` or `all`) names Codex
`[[skills.config]]` `path` entries that can never match a skill — a folder
instead of its `SKILL.md`, a missing file, or another file — and the human
output prints each with the `SKILL.md` path to use. Nothing is changed.

The report's `codex_listing` section estimates Codex's skill listing from
`~/.agents/skills` against its default 2% context-window budget (codex#19679) and
prints one line, for example `Codex listing: ~10,600 tokens vs 8,000 budget
(2% of the gpt-5 context window, estimate); 40 skills from ~/.agents/skills`.
A positive `skills.max_context_tokens` in the bounded user Codex config
(`$CODEX_HOME/config.toml`, otherwise `~/.codex/config.toml`) replaces the
default budget and is capped at 10,000 tokens. The text states its actual
basis. Invalid or unreadable settings produce `status: unknown`, null
`budget.budget_tokens` and `tokens_to_free`, and `budget unknown` in text;
they do not produce a pass or a budget warning. CLI, profile, managed and
project settings remain unobserved. Bundled skills are not counted, so
`skills.bundled.enabled` does not change this user-root estimate. Sources:
@docs/46-vendor-compatibility-verification-2026-11-17.md. Skills whose
`agents/openai.yaml` sets `policy.allow_implicit_invocation: false` are left
out of that estimate, because Codex hides them from the model, and a second
line names up to five of them (`Codex explicit-only (not shown to the model,
invoke with $name): …`) with a `codex-explicit-only-skill` info finding
(openai/codex#23454). A link target that is a `file:` URL or an absolute
home path is reported as a machine-local broken reference. An
`opencode-output-truncation` warning names enabled skills OpenCode reads
whose `SKILL.md` exceeds 2,000 lines or 50 KiB, the head OpenCode keeps of a
tool result (opencode#62718). Both are read-only estimates.

The report's `skills_dir_plugins` section (`--scope claude-code` or `all`)
lists `~/.claude/skills` folders that Claude Code loads as plugins
(`.claude-plugin/plugin.json`) and prints one line, for example `Claude Code:
1 skills-dir plugin in ~/.claude/skills (1 without a root SKILL.md; copy each
as a whole folder)`. A `plugin-member-skill` info finding names a skill that
sits in such a plugin folder, because `sync` copies only the skill folder and
drops the plugin around it (vercel-labs/skills#2609). An
`opencode-autoinvoke-conflict` warning names a skill whose
`disable-model-invocation` and `metadata.opencode/autoinvoke` disagree, since
OpenCode lets the second win (sst/opencode#52747). All are read-only.

The report's `agents_bridge` section (docs/29 H2, explain-only) names enabled,
readable skills that exist in `~/.agents/skills` but have no copy or link in
`~/.claude/skills`. Claude Code's documented roots do not include
`~/.agents/skills` (@docs/34-agent-skill-loading-research-2026-11-07.md), so it
does not load them. The section carries the cited source, up to 50 names with
home-redacted paths plus `missing_total`/`omitted`, and two remedies. One is
the existing `jackfield sync <name> --from agents --to claude-code` copy. The
other is a manual link, with the caveat that anthropics/claude-code #14836
reports symlinked skill folders as unreliable. It needs `--scope all`; any
other scope reports `state: unavailable`, and a scan that hit the instance limit
reports `state: partial` and names nothing. One `agents-bridge-gap` info finding
appears when the gap is non-empty, and the human output adds one summary line.
Nothing is linked, copied or written.

### `stats [--json] [--scope SCOPE]`
Counts and summary (skills, disabled, trash, categories, sizes). With `--scope all`, also lists per-scope counts. Category names are sanitized before printing (see *Untrusted display text*).

### `trash list [--json] | trash restore NAME [--snapshot TS] [--scope SCOPE] [--json] | trash purge [--json]`
Manage the trash: list, restore one, purge all. Human `trash purge` reports the
number of purged skills; `--json` preserves the structured `purged` name list.

### `templates list [--json] | templates new NAME [--body TEXT] [--json]`
List templates; create a new template NAME (optional `--body`). Templates are files under `<data>/templates/`, used when creating skills.

### `db rebuild [--json] | db resync [--json]`
`rebuild` drops and re-creates the index from the filesystem; `resync` syncs the index with FS without dropping. Both leave skill documents untouched. A bare `db` is a usage error.

### `sync NAME [--from SCOPE] [--to SCOPE ...] [--force] [--json]`
Copy a skill from one scope to others. Default: `--from global` → every writable existing agent scope. `--to` is repeatable (target scope ids); `--force` overwrites existing names after preserving the target document
bytes in `<data>/snapshots/SCOPE/NAME/ID.md`. An undecodable snapshot requires
manual byte recovery from that file; text restore refuses to rewrite it
lossily. Sync copies the source enabled/disabled state. Failed backup cleanup
leaves the installed copy intact and retains `.NAME.skillsmgr-backup` for
manual review; another sync refuses to discard that backup.

### `scopes [--json] [--no-tokens]`
List known skill scopes and their counts (id, label, path, kind, exists, count, tokens). `--no-tokens` omits token totals from both text and JSON output; document
scanning and estimation still occur. Scope ids: `global`, `claude-code`, `codex`, `cursor`, `opencode`, `gemini`, `commandcode`, `agents`, plus project-local scopes when present.

### `tokens [NAME] [--scope SCOPE] [--text TEXT] [--window WINDOW] [--json]`
Estimate token/context usage. `NAME` = a skill; omit to aggregate over `--scope` (default `all`). `--text` estimates raw text instead (`@path` reads a UTF-8 file; missing, unreadable or undecodable paths are errors). `--window` selects the context window (claude 1M, claude-haiku 200k, gpt-5.6 1.05M, gpt-5 400k, gpt-4o 128k, gemini 1M, gemini-2m 2M). Uses tiktoken when installed, else chars/4 heuristic.

### `install [SOURCE] [--runner RUNNER] [--scope SCOPE] [--agent AGENT ...] [--skill SKILL ...] [--copy] [--list-only] [--dry-run] [--preview] [--trust-confirmed] [--registry-hash HEX] [--review REVIEW_ID] [--browse|--search QUERY|--curated|--fetch] [--page N] [--per-page N] [--view VIEW] [--allow-stale] [--external-scan|--external-scan-llm] [--json]`
Install skills from the open skills ecosystem via the `skills` npm package (npx/pnpm/yarn/bunx). `SOURCE` like `vercel-labs/agent-skills` or `owner/repo@skill`. `--scope global` passes `-g`; `--agent` targets agent install dirs; `--skill` filters names; `--copy` copies instead of symlinking; `--list-only` executes the runner's list mode and reports its output/exit status; `--dry-run` prints the command without running. Source, agent, and skill values must be non-empty, at most 256 characters, and may not be option-like, traversal-shaped, absolute, or Windows drive-prefixed. `uvx` is rejected (it's an npm package).

`--preview` prints the offline registry bridge preview instead of installing: the parsed registry reference, linkable per-skill audit pages, the `--registry-hash` slot used to detect upstream change, and the exact command this surface would run (`-s <slug>` is added for a registry skill id). It performs no registry request, no cache write, and no execution. `--trust-confirmed` records caller review intent only for the offline plan; that plan still reports `trust_verified: false`, `eligibility_status: "unverified-offline"`, `hash_verified: false`, and `may_install: false` (a supplied hash is `unverified-provided` until an authenticated read and comparison).

The existing install surface also supports the network registry operations
`--browse`, `--search QUERY`, `--curated`, and two-step `--fetch`. Browse/search/
curated and the first `--fetch SOURCE` return bounded catalog/review evidence
and cache metadata without mutating the Store. The second request is
`--fetch --review REVIEW_ID --trust-confirmed`; it is global-store-only,
revalidates the expiring review snapshot and optional `--registry-hash` evidence,
then writes a credential-free `.skillsmgr-provenance.json` sidecar. The commit
request performs no network request and a review id is single-use. `--allow-stale`
opts into an expired cache only when the network is unavailable.
The registry client rejects unsafe hosts/redirects, oversized or malformed
responses, traversal/symlink paths, duplicate files, and resource-limit
violations. See @docs/ADR-003-registry-bridge-and-eval-harness.md and
@docs/ADR-005-registry-network-and-provenance.md.

**[SPEC] Endpoint tiers (changed 2026-10-04).** skills.sh moved its read API
behind Vercel-project OIDC, so every `/api/v1` request answers `401` without a
project token — and a binary on a user's laptop cannot mint one. Three routes
remain public, and this client depends only on those:

| Operation | Route | Auth |
|---|---|---|
| `--search QUERY` | `/api/search` | **public** — returns `{skills:[…]}` at most 100 rows, honours `limit`, ignores paging |
| `--fetch` (detail + commit) | `/api/download/{source}/{slug}` | **public** |
| `--browse`, `--curated` | `/api/v1/skills`, `/api/v1/skills/curated` | **token required** — no public equivalent |

`--search` normalizes the public envelope into the same listing shape every
caller reads, applies the requested `limit` itself, and reports `truncated`
when the route returned more than asked for. `--browse`/`--curated` still work
with `JACKFIELD_REGISTRY_TOKEN` or `VERCEL_OIDC_TOKEN` (never persisted);
without one they fail with a message naming the token **and** the public
alternative, rather than an opaque `HTTP 401`.

**[SPEC] `--registry-hash` is the manager's own content digest.** The public
download route's `hash` field is produced by an undocumented upstream algorithm
(verified live: ten candidate algorithms, none matching), so it is never claimed
as verified. It is preserved as `upstream_hash` with `upstream_hash_verified:
false`, and the review artifact plus the provenance sidecar both carry that
demotion. Integrity rests on the framed `snapshot_hash`, which is what
`--registry-hash` compares and what detects upstream change between fetches.

Before the existing store-add seam is reached, a fetched snapshot is
materialized in a private temporary directory, fully validated, and scanned
with the advisory `risk_scan()` heuristic. Validation errors fail before any
managed-file mutation; warnings and risk findings are returned under the JSON
`inspection` block and are never a safety certification.

### `update preview NAME (--from DIR | --snapshot SNAPSHOT_ID) [--scope SCOPE] [--target-path PATH] [--external-scan|--external-scan-llm] [--json]`

Create a private, expiring review for one exact observed local skill instance.
`--from` and `--snapshot` are mutually exclusive and exactly one is required;
`--scope all` is rejected. Recursive scopes require `--target-path` when the
name has multiple observed physical instances. The preview never mutates the
target or caller source. JSON includes target/source identity, current and
candidate hashes, bounded added/removed/changed/line-ending-only evidence,
validation errors/warnings, advisory risk findings, activation preservation,
snapshot policy, and the 32-character review id. Invalid or no-change previews
are non-committable; valid no-change exits 0, while blocked/unreadable input
exits 1.

**[SPEC] Optional external scanner (2026-11-06).** `--external-scan` runs an
installed NVIDIA SkillSpector on a private copy of the staged candidate and adds
its findings as `external_scan` evidence; `--external-scan-llm` also enables
SkillSpector's LLM stage with the user's own provider key, read from this
process's environment (`SKILLSPECTOR_PROVIDER` plus that provider's key). The key
is passed only to SkillSpector and is never stored, logged or returned. Static
mode may send declared dependency names to `api.osv.dev`; LLM mode sends skill
file contents to the configured provider. The evidence is advisory: it never
changes validation, readiness or exit codes, and the tool's own score and
recommendation are reported under `reported` as its claim. A missing or
untrusted executable (`launcher_security.trusted_executable`) reports
`unavailable` with the reason. See `external_scan.py` in @docs/02-modules.md.

### `update apply NAME REVIEW_ID [--scope SCOPE] [--target-path PATH] --yes [--json]`

Apply only the staged candidate bound to the returned review id. `--yes` is
mandatory and confirms review of the displayed evidence; it is not a trust or
safety claim. The service rechecks the candidate and target hashes, snapshots
the complete current tree, atomically replaces the exact instance, persists a
source-lock sidecar, and resyncs the global index only after filesystem success.
Stale, expired, cancelled, committed, mismatched, or replayed reviews fail
without changing target bytes. Successful JSON includes the opaque snapshot id;
post-commit index/review/retention failures are reported as
`committed_with_warning` with recovery guidance.

### `update snapshots NAME [--scope SCOPE] [--target-path PATH] [--json]`

List the newest five retained source-update snapshots for one exact observed
target. The JSON list reports opaque snapshot id, creation time, source review
id, tree hash, activation state, and readability. A snapshot is never applied
directly: `update preview --snapshot SNAPSHOT_ID` creates a normal rollback
review, which must be separately approved and applied.

### `webui [--host H] [--port P] [--no-browser]` (alias: `gui`)
Launch the local web UI (see @docs/08-web-ui.md). Defaults: `127.0.0.1:8765`, opens browser unless `--no-browser`.

## Flags cheat sheet

**[NOTE]** Multi-word values (descriptions, bodies, metadata) must be quoted or passed via `--body-file`/`--metadata KEY=VALUE`. All mutation commands print human-readable confirmation unless `--json`. Scope ids are lowercase; `--scope all` merges scopes for list/search/stats/tokens.

## Untrusted display text

**[SPEC]** `list`, `view`, and `stats` print strings that an attacker can influence:
a description or category can arrive from an imported archive or from a scope
directory another tool wrote. Every printed cell therefore passes through
`cli_output.sanitize_text()` first — C0 controls, DEL, and C1 controls (ESC
included, so `ESC[2K` is covered), the Unicode line/paragraph separators, Unicode
format characters (a bidi override can reorder a whole line), and lone surrogates
are each replaced with `?`.

The consequence is the contract worth remembering: a hostile `ESC`/CR payload can
no longer erase the real row and print a convincing "verified" one, and can no
longer corrupt column widths, because the escape stops counting towards `len()`.
`render_table()` and `truncate()` sanitize as well, so a value cannot reach the
terminal through a path that skips the seam, and the colors this tool emits itself
are applied *after* sanitizing, so they are unaffected.

The guards cover the `list`, `view`, `stats`, `search`, and `history` text output.
`--json` and `view --raw` are exempt **by design** — they are data, not a rendered
view — so do not pipe either to a live terminal. (CLI-3.)

## Stale-fact note

**[NOTE]** The `gui` command previously launched a GTK4 desktop GUI; since 2026-08-14 it is an alias for `webui` (the GTK GUI was replaced by the local web UI — see @docs/08-web-ui.md). The `scopes`/`sync`/`tokens`/`install` commands and the `--scope` flag were added after the 2026-08-14 doc version.
