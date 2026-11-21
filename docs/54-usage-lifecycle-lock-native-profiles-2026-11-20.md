# Usage, Stale Archive, Project Lock and Native Profiles — Decisions

**Version 1.0.0**

**AI manifest**: On 2026-11-20 the owner approved the three features that
@docs/35-open-decisions-resolved-2026-11-07.md had deferred: per-project
profiles written to each agent's native setting, stale → archive with pin,
restore and dry-run, and transcript usage counts with a project skill
lockfile. The approval covers the new CLI commands below. This file records
how each was built and why. Research memos (primary sources, cited there):
`~/skills-manager-artifacts/2026-11-20-feature-research/`.

## Rules that still hold

**[SPEC]** The approval does not relax the other locked constraints:

1. The filesystem is the source of truth. SQLite and `SCHEMA_VERSION` do
   not change. New state lives in plain files under the private data
   directory (0700 directories, 0600 files, written atomically).
2. No new `Store` method. Features are module functions, the precedent set
   by `scopes.scope_trash_list` / `restore_trashed`.
3. Stdlib only. No comment-preserving TOML/JSONC library.
4. The web server stays unauthenticated on loopback. **Nothing that widens
   what the tool reads, or that writes another tool's settings, may be
   enabled from a REST route alone**: consent is CLI-only, and native writes
   need a plan hash produced by a prior read-only preview.
5. Project and pin writes bind to a preview of the prior bytes and retain
   a guarded undo receipt. Consent, refresh and consent revocation are
   explicit CLI operations.

## Order of work

**[SPEC]** Readers before writers (docs/35 "do the read side first"):

1. `lockfiles.py` reads the vercel project lock **v2** (`commit`, portable
   `computedHash`) as well as v1.
2. `native_state.py` reads OpenCode V2 `permissions` arrays, `.jsonc` and
   `.opencode/` files, and Command Code `disabledSkills`.
3. Usage, then lifecycle (needs usage), then lock commands, then native writes.

## Implemented surface

**[NOTE]** The commands and flags are listed in @docs/03-cli-surface.md.
They use the supplied project or manager data directory. Preview and cached
reports can run before an index exists. No HTTP consent or mutation route
was added.

## 1. Usage counts from transcripts

**[SPEC]**
- **Opt-in per agent, CLI-only.** `skills-mgr usage enable --agent A`
  writes `<data>/usage/consent.json` naming the exact roots. No transcript
  root is opened without it. There is no REST route that grants consent.
- **Extract only** `(agent, skill name, UTC day, kind)`. `kind` is
  `explicit` (a structured skill tool call) or `inferred` (Codex reading a
  `SKILL.md`). Never message text, arguments, tool output or the working
  directory. Names must match the skill-name rule (plus an optional
  `plugin:` prefix) or are dropped.
- **Evidence events** (structured fields only, never free text): Claude
  `tool_use` named `Skill` (`input.skill`); Command Code `tool_use`
  `activate_skill` (`input.name`); OpenCode legacy `part` rows with
  `tool:"skill"`, 2.3.2 assistant messages containing completed skill calls,
  and 2.3.2 top-level skill activations read from a checkpointed SQLite file
  opened read-only; Gemini
  `activate_skill` tool calls; Codex `<skill><name>` fragments (explicit)
  and `SKILL.md` reads under a known root (inferred). Listings,
  re-injected `invoked_skills`, mentions and duplicate call ids never count.
- **Bounded, tolerant reads**: regular files only, no symlinks, per-line,
  per-file, per-scan byte and time caps; an unknown shape is "no evidence",
  never an error. Each report lists parser coverage per agent.
- **Cache**: `<data>/usage/counts.json` with per-day buckets kept 400 days
  and bounded scan watermarks for incremental rescans. Cached reports read
  aggregates only. They accept legacy integer counts and the current explicit
  and inferred counts on canonical UTC dates. A damaged scan summary is marked
  `cache-invalid` for that agent while valid counts remain visible. Reported
  scan summaries include only documented fields and leave the coverage window
  unset. Reports include dates within the selected UTC window
  through today. JSONL scans save progress through complete records that
  fit the byte and time budgets. If a refresh stops partway through a file
  or line, the next refresh can resume from the saved offset, provided the
  file still has the saved prefix. The 32 MiB per-file limit applies to
  each JSONL refresh, so long sessions can be read in successive passes.
  A refresh scans each selected agent once, including repeated selections.
  Directory discovery and transcript reads share the deadline. Directories
  count toward a separate metadata limit. A capped refresh saves a numeric
  position in the file walk and can continue with later transcripts. The
  position wraps at the end or when it can no longer be reached. Resumed
  walks show partial coverage and the cache bounds per-agent file marks.
  Multi-agent refreshes rotate their starting agent when they exhaust the
  shared budget. A deferred source keeps its saved file position.
  A skipped oversized record is discarded through its newline even across
  several passes. A skipped malformed or oversized record keeps coverage
  partial across appends. Gemini's whole-document JSON still has a file-size
  limit. OpenCode scans checkpointed data
  again with call-ID deduplication so a tool that completes in an existing
  row can count. The current-format table is read first, and each table is
  read in descending SQLite row ID order so long histories leave room for
  new rows. A timed-out scan keeps events already extracted from a stable
  snapshot and reports partial coverage. A write-ahead log
  with frames yields partial coverage. `usage disable --purge` removes the
  private usage directory.
- **OpenCode database selection.** An absolute `XDG_DATA_HOME` replaces
  the default data base, and `OPENCODE_DB` can select a filename under its
  OpenCode folder or an absolute path. In-memory or ambiguous relative-base
  configurations provide no scan source. When the configured database
  changes, the CLI requires fresh consent for that path. A cache read
  suppresses counts when it observes a change in the consent root or a
  mismatch with the cache's root binding. A refresh through a currently
  consented root rebuilds mismatched evidence.
  [OpenCode XDG roots](https://github.com/anomalyco/opencode/blob/v2.3.2/packages/util/src/global-roots.ts)
  [OpenCode database selection](https://github.com/anomalyco/opencode/blob/v2.3.2/packages/cli/src/database-path.ts)

The 2.3.2 database shape was observed using the isolated probe in
@docs/48-ai-http-study-2026-11-17.md. The tool went through a checkpointed
assistant message with `state.status` of `completed` and `state.input.id`.
The reader counted it on two refreshes without changing the database.
[OpenCode session schema](https://github.com/anomalyco/opencode/blob/dev/packages/core/schema.json)
[SQLite URI parameters](https://www.sqlite.org/uri.html)

**[NOTE]** Formats are undocumented vendor internals and will drift; counts
join to library skills by name, so they are approximate across scopes.

## 2. Stale, pin and archive

**[NOTE]** Implemented: cached lifecycle report and pin, unpin and guarded
pin undo. Current transcript formats provide observed events with partial
parser coverage. They do not prove gap-free observation or cover every
possible consumer and edit/install period. The report therefore emits
`unknown` and `in-use` only. Moving skills into or out of archive is
pending eligibility evidence. Text and disk state of skills are untouched
by pin changes.

**[SPEC]** The read-only preview reports the primary document's filesystem
modification time as `last_edit` for active and disabled copies. Linked,
malformed or unavailable documents have no timestamp evidence. A recent
modification or cached usage event is positive activity evidence. Both use the
last `N` UTC dates including today. A modification time covers one file and
can be preserved by a copy, so it cannot establish install age, the age of
supporting files, or an uninterrupted edit history.

The JSON `inventory` distinguishes sampled roots (`scanned`), missing roots,
incomplete observations (`partial`), physical roots already represented by
another scope (`shared-root`), and scopes omitted by the row limit
(`not-scanned`). Scan diagnostics contain fixed descriptions of the failure.
Shared physical roots only reuse an equivalent completed scan. A flat root
and a grouped or recursive root are scanned separately even if they resolve
to the same directory. Project-root aliases participate in this inventory.
When the preview reuses an equivalent scan, each consolidated row's
`pinned_scopes` lists the represented scopes with a pin for that name.
`pinned` is true if any represented scope has a pin. Pin and unpin
still apply to the named scope.
The rows include `relative_path` where the folder can be attributed to the
scope root. Skipped documents with unaddressable names make inventory partial.
`used_by` and its explanation identify cached matches by name. A name match
leaves the exact originating copy unknown.

The preview's `archive_readiness` reports documented readers for each
selected managed scope by matching scope IDs and known project-relative root
conventions in the consumer catalog. This is a partial configuration hint.
Readers are combined for selected scopes observed at the same physical root.
The resulting hints apply to the root. Individual readers may discover
different copies under their own discovery rules.
Project roots beyond the working directory, aliases, explicit registrations and
additional agent installations can change which consumer sees a physical
copy. The last transcript scan status describes one scan. It establishes
neither continuous coverage nor that a name match came from the selected
copy. Gemini CLI documents session cleanup, and OpenCode describes its live
event stream as volatile across disconnects. Any lookback over such signals
needs independent evidence that observation was continuous.
[Gemini session retention](https://geminicli.com/docs/cli/session-management/#session-retention)
[OpenCode event stream](https://opencode.ai/docs/api#event)

**[SPEC]** Future eligibility and moves:
- `state` is **`unknown | in-use | stale-candidate`**, never a boolean.
  Stale-candidate needs all of: usage consent, a parser and a coverage
  window of at least T days for every agent that can load the skill, zero
  events in T days, no edit or install in T days, and no pin. Anything less
  is `unknown`, and archive is never offered from it. T defaults to 90.
- **Archive is not trash.** `trash purge` empties trash, so archives live in
  `<data>/archive/<scope>/<name>-<stamp>/` with `ARCHIVE.json` (original
  path, reason, evidence, tree hash). Moves reuse
  `atomic_io.move_trash_tree` (EXDEV-safe) and verify `tree_content_hash`
  before and after. Restore refuses an occupied destination or a changed hash.
- **Pins** live in `<data>/pins.json`, never inside the skill tree.
  A pin or unpin saves its private undo receipt before replacing the file.
  The updated file includes the unique preview ID. Undo verifies that ID
  and the resulting bytes, so an interruption after the replacement leaves
  a usable receipt. An interruption before replacement leaves the original
  pin state in place. Earlier confirmed receipts still work by matching the
  saved post-write hash.
- Archiving is never automatic. `archive candidates` is the dry run;
  `archive apply` needs the plan hash from it.

## 3. Project skill lockfile

**[SPEC]** Use the vercel `skills-lock.json` format; do not invent one and
do not write APM files (docs/53). `lock verify` is read-only and exits 1 on
drift (CI-friendly, no network). `lock write` updates only named skills,
keeps unknown fields and untouched entries, stores project-relative local
sources, and never fabricates a `commit`. Installing from a lock is
delegated to the existing `install --runner`. The reader accepts v1 and
v2. Writing v1 requires prior vendor migration because the legacy hash uses
ICU ordering. The preview shows selected managed fields and avoids unrelated lockfile
data. A v2 write keeps an undo receipt in the private manager data
directory before publishing the staged lock. New receipts record the
replacement file's identity, exact bytes and permissions. A replacement that
completed before an interruption can be undone. Undo refuses a different file
even when its contents match. A failed attempt with a saved receipt
also requires a fresh preview before retrying. Verification compares
installed document trees offline. It does
not establish remote provenance. [Vercel lock source](https://github.com/vercel-labs/skills/blob/main/src/local-lock.ts).

Apply and undo honor the write protection on an existing lockfile, including
on systems where the containing directory would allow an atomic replacement.
The CLI leaves a busy companion lock in place because its age alone cannot
establish whether another process still holds it.

## 4. Native per-project profiles

**[SPEC]** Each native settings request selects one project, one agent and
the declarations to turn off. Supply repeated `--off NAME` flags or select
a saved profile with `--profile NAME`. The profile's optional `native.off`
list is edited as metadata in v2 Profiles. Preview and apply re-read it,
so changing the list invalidates an earlier plan.

Catalogs with saved native lists use catalog format v2. Older installed
managers reject that format before writing. The current reader accepts
both versions, and writes v1 while all native lists are empty. The v2
editor compares the loaded profile at save time to catch stale edits.
Legacy HTTP clients can omit the native list to preserve it.

| Agent | Write | Why |
|---|---|---|
| claude-code | `<project>/.claude/settings.local.json` `skillOverrides[name] = "off"` | The vendor's own `/skills` menu writes this file and key |
| gemini | `<project>/.gemini/settings.json` `skills.disabled` | Documented; the preview warns that a user-level disable cannot be undone by a project and that untrusted workspaces ignore the file |
| opencode | project `opencode.json` skill deny rule in the dialect the file already uses | Unknown dialect → refuse |
| commandcode | **Patch only** | Whether `disabledSkills` merges or replaces across layers is unverified; a replace would silently re-enable user-disabled skills |
| codex | **`-c` launch line only** | Project `[[skills.config]]` is ignored by design (openai/codex#20210) |
| cursor, agents | **Unsupported**; the existing global rename is offered and labelled global | No native per-skill switch |

**[SPEC] Safe-write rule.** A file is written only when it is absent or is
strict JSON that re-serializes byte for byte with its detected indentation,
so the write provably changes nothing but the target key. Input outside those rules is refused.
Raw changes are shown only when their lines contain the requested declarations
and known structure. Otherwise the preview shows the requested semantic
changes without unrelated setting values. Also refused: symlinked file
or parent, non-regular file, over 1 MiB, duplicate keys, an unexpected value
type. Writes keep the file's mode, compare the pre-image hash immediately
before replacing, back up the pre-image under `<data>/native-backups/`, and
undo only when the file still has the post-image hash. The shared
`.claude/settings.json` stays outside the supported write path. Writers
require guarded directory descriptors and existing settings parent
directories. OpenCode requires an existing recognized dialect and refuses
competing project JSONC or `.opencode/` layers. The manager can recheck files
just before replacement, but native applications do not share that lock.
An interruption before the receipt is finalized can leave a private
preimage that requires manual recovery.

Native setting references: [Claude Code skills](https://code.claude.com/docs/en/skills),
[Gemini CLI skills](https://geminicli.com/docs/cli/skills/) and
[OpenCode permissions](https://opencode.ai/docs/permissions/).

**[NOTE]** Rejected: a hand-written JSONC/TOML span editor (new parser and
attack surface for a minority of files) and rename-only profiles (not
per-project). Results say "declared in file", not "effective": vendors can
change precedence, and a running agent may rewrite its file at any moment.
