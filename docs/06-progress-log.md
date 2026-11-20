# Progress Log — Skills Manager

**Version 0.8.1**

**AI manifest**: Current delivery receipts and a bounded resident window.
Earlier entries moved verbatim to @docs/archive/06-progress-log-through-2026-11-17.md;
older archives remain indexed by @docs/archive/README.md. The live queue is
@task.md. Retained historical sections are explicitly labeled below.

## 2026-11-20 — Lifecycle evidence and remaining-task review

- `archive candidates` now shows the primary document modification time
  for active and disabled copies. The CLI skips linked or malformed documents
  and keeps the scan independent of the SQLite index. Recent mtime and cached
  usage use the same UTC date window. Archive apply and restore still require
  continuous usage coverage, verified consumer mapping and edit/install
  evidence. See @docs/54-usage-lifecycle-lock-native-profiles-2026-11-20.md.
- Reviewed the dated `2359e7a` pilot ZIP locally. All seven PNGs matched the
  manifest hashes and viewport dimensions, and the files contained only PNG
  header, image data and end chunks. Visual review found synthetic names and
  no visible personal paths or account identifiers. The captures document the
  named checkpoint and predate the later Inbox overwrite preview. External
  approval and consented sessions remain with the maintainer.
- Rechecked the ten retained HTTP study artifact hashes. The native harness
  joined all twelve saved prompts to the DeepSeek simulation in dry-run mode,
  including verification of the captured listing fingerprint. This is
  offline input validation. The same-model native run remains an attended
  study. See @docs/48-ai-http-study-2026-11-17.md.

Linux verification ran 2,335 unit cases on each of Python 3.11–3.14, with
7/7/7/6 skips and no failures. Both smokes, compile, CLI help, Ruff, Bandit,
complexity, documentation, design tokens and offline AI evidence checks
passed. The pinned wheel and sdist passed package-data checks and eight
lifecycle tests each after clean installs. Synthetic CLI checks covered an
empty library, two concurrent reports of a single skill, and a 10,001-skill
library truncated at 10,000 rows.

## 2026-11-20 — Claude Code recovery hardening handoff

Continued from Claude Code's `Skills Manager recovery hardening` after
verifying that the recovery commits through `487de61` had reached `main`.
That revision's GitHub CI run completed all 16 jobs successfully.

- Forced Sync identifies the actual v2 Inbox targets, records the previous
  folder in Recovery when its supporting files would change, and reports
  a retained backup path when the move fails. Resync preserves Recovery
  payloads and retained backups. New scoped Recovery entries record and
  validate the original location of nested skills.
- CLI-only usage consents record the selected roots, while usage reports
  distinguish observed counts from parser coverage. Lifecycle reports
  and reversible pins are available. Archive moves await continuous,
  all-consumer observation evidence.
- The CLI verifies Vercel project lockfiles offline and previews guarded
  v2 updates with undo. Native project changes support reviewed settings
  writes, a saved profile's off list, and read-only handoffs. See
  @docs/54-usage-lifecycle-lock-native-profiles-2026-11-20.md.

Verification on Linux: the full Python 3.12 suite ran 2,332 tests with
7 skipped. The 44-test recovery, CLI and profile subset passed on
Python 3.11–3.14. The final lock and usage checks passed 66 tests. Both
smokes, Ruff, complexity, design tokens and documentation gates passed.
Chromium 158 and Firefox 151 each passed 47 v2 checks and 349 classic
assertions. Agent-browser and agent-desktop independently confirmed the Inbox
Sync action's source and destination on an isolated desktop fixture.
The v2 lock hash matched Vercel's `skill-hash.ts` at `57217cf` on a
fixture with nested links, Unicode names, binary bytes and CRLF. Both
distribution artifacts passed package-data checks and all six installed
CLI integration tests. Human perceptual and spoken screen-reader
sign-off remain separate.

## 2026-11-20 — Recovery follow-ups from parallel review

Four parallel subagents (Sonnet/Haiku) worked from this session's gaps: an
agent-scope implementation in an isolated worktree, a hostile review of
`9ca8ff6..4d83e86`, an investigation of a stray CI log line, and a flake hunt
under CPU contention. Their diffs and claims were re-checked before landing.

- Agent-scope `restore_trashed` now shares the global copy, verify, publish,
  retire helper (moved to `atomic_io.move_trash_tree`). The global default
  restore orders by trash stamp and serial with mtime as the last tiebreak,
  so an mtime bump on an older entry no longer changes which copy returns.
  An entry that vanishes during selection is skipped; other inspection
  errors become `StoreError`.
- Review found that `POST /api/trash/purge` with a `{"trash_path": ...}` body
  and no `?scope=` emptied the whole trash (`purge` is a valid skill name).
  Only a bare request purges now; a regression covers both body shapes.
  The shipped UIs always send `?scope=`, so neither was exposed.
- Not changed, recorded for later: Windows directory renames that fail with
  a held handle no longer fall back to copy and delete (only `EXDEV` does);
  new trash names add 26 characters, which matters near MAX_PATH; a crash
  between publishing and retiring leaves both copies until resync.
- The stray `FAIL: File is not a zip file` was a negative-path test writing to
  stderr. It is now captured, and the test asserts the reason for both the
  wheel and the sdist reader, which it previously never reached.
- Flake hunt (18 timing modules, 15 runs each under load): the fidelity
  descendant test failed 4/15 (`State: R` with SIGKILL pending) and the
  skill CI recipe test 1/15 (SIGTERM between `mktemp -d` and `trap`). The
  first now polls up to 5 s, the simulator test uses its short timeout only
  for the timeout case, and the recipe test signals after the stub starts.
  Both modules then passed 10/10 under six busy loops, and on Python 3.11.
- Ladder on the integrated tree: Ruff 0.16.8, compile, complexity (one stale
  baseline entry removed, `_route_trash_post` ratcheted 5 → 4), docs, design
  tokens, unit suite on 3.12 and 3.11, both smokes, v2 and classic e2e.

## 2026-11-20 — Recovery across linked and cross-volume trash

- Global Recovery accepts either the listed trash path or the physical path
  `remove()` returned when the trash folder is a link to another location.
  The incoming string is only compared against listed children of the trash.
- Restore and its rollback now survive `EXDEV`. The fallback stages a copy
  beside the destination, verifies relative names and bytes with
  `tree_content_hash`, publishes it, then parks and deletes the original.
  If the original cannot be parked, the published copy is withdrawn, so only
  the untouched original remains and the restore can be retried.
- New regressions cover a successful cross-volume restore, a copy that does
  not match, an original that cannot be retired (mutation-checked: red with
  the withdrawal disabled), and listed versus returned paths through a linked
  trash. A manual run with data on ext4 and trash linked to `/dev/shm` tmpfs
  restored a skill and its binary companion through a real `EXDEV`.
- `test_restore_reports_a_lost_trash_copy_as_a_store_error` mocked
  `shutil.move`, which restore no longer calls; it now injects the failure at
  `os.rename` and again proves the clean `StoreError`.
- Ladder on the final tree: 2,252 unit cases with 7 skips on Python 3.12 and
  3.11; Store and Web smokes; v2 and classic e2e (39 scenarios, 349
  assertions) in a chmod-700 temp dir; docs, complexity and design tokens.
  macOS and Windows coverage comes from CI.
- CI run 44705858668 then failed only `unit (py3.13)`:
  `test_timeout_terminates_fake_descendant` read `/proc/<pid>/status` while
  the killed child was in the transient `X (dead)` state. The test now accepts
  `Z` or `X`; both prove the child stopped. All nine cross-platform jobs
  (ubuntu, macOS, Windows on 3.11 and 3.14) had already passed.
- The rerun (44707293366) passed 3.13 but hit two other races. On macOS,
  `os.killpg` returned EPERM for a process group holding only zombies; the
  fidelity harness's `_stop` now treats EPERM like ESRCH after killing the
  direct child if it is still alive. The v2 "Peer scope link" scenario read
  `.use` rows once without waiting; it now waits for the shared-folder row.
  The fidelity tests and the full v2 e2e suite pass locally.

## 2026-11-20 — Recovery paths for repeat removals

- A restore followed by another removal in the same UTC second could reuse
  the earlier path in either trash. A browser with the old path could then
  restore the new version. New paths add a numeric suffix ordered by the
  host's monotonic clock, with extra entropy for equal readings. Both trash
  readers still accept dated paths and collision counters from earlier builds.
- Regressions freeze the clock, restore the first version, change the body
  and remove it again. The old path is refused and the new path restores the
  expected bytes. An agent name-only restore still picks the later copy in
  the same second. A full backup containing old and new path formats imported
  both and restored each by its exact path.
- On Linux, Python 3.11–3.14 each ran 2,245 cases with no failures and
  7, 7, 7 and 6 skips. Store and Web smokes, checked package contents and
  clean wheel and sdist installs passed. Chromium and Firefox each passed
  46 v2 scenarios and 39 classic scenarios with 349 classic assertions.

## 2026-11-20 — Firefox replay and pilot screenshot package

- The matching Firefox 151.0 build in a private Playwright cache passed all
  46 v2 scenarios. The classic runner now also accepts `--browser firefox`,
  isolates Codex and Gemini config paths, and records browser and version in
  `results.json`. Both engines passed 39 classic scenarios and 349 assertions.
  Chromium remains the default for CI. The Linux Python 3.12 suite passed
  2,242 cases with seven skips after the runner change.
- Captured seven screenshots from local checkpoint `2359e7a` with synthetic
  skills. The package covers Skills, Sync map and exact copy evidence,
  Workspaces discovery, Quality and Recovery. It includes a phone capture
  of the Sync map and a manifest with dates, viewport sizes and SHA-256
  digests. The ZIP is at
  `~/skills-manager-artifacts/2026-11-20-pilot/2026-11-20-2359e7a-pilot-screenshots.zip`.
  The package is ready for external-use review. Participant sessions and
  human visual and spoken sign-off remain open.
- The Unreleased changelog records the Sync map and exact Recovery changes
  for the maintainer's release-candidate review.
- The `.specs/` checkout contains 288 tracked files totaling 40,234,010
  bytes. Of those, 30,222,125 bytes are under `evidence/` and 9,951,650 under
  `prototypes/`. Git reported 277 unique `.specs/` blobs across named refs
  with 40,787,437 uncompressed bytes. That count includes blobs still in the
  checkout. The checked wheel and sdist contain no `.specs/` entries. The
  [combined verification report](31-combined-e2e-verification-2026-11-06.md)
  and other records still reference this evidence. Retention and any history
  rewrite remain a maintainer decision.

## 2026-11-20 — Sync map review filter and exact Recovery restore

- Sync map can show only skills with a copy that needs review in a displayed
  scope. The filter combines with name search and returns to the first page.
  Opening a different skill copy clears the previous repair selection.
- Both interfaces restore the selected global trash entry. Scoped restore
  also works for a skill named `purge`, while the explicit empty-trash action
  still uses its existing endpoint. A missing selected entry fails without
  restoring a different version. The Store matches paths against listed
  children while holding the index and trash locks.
- Older v2 responses can no longer overwrite newer global trash, agent trash,
  catalog or Recent changes results and errors.
- Linux verification ran 2,242 unit cases on each of Python 3.11–3.14 with
  7, 7, 7 and 6 skips, respectively. Both smokes, the viewport harness,
  Ruff, the medium/high Bandit check, docs, design tokens and complexity
  passed. The pinned wheel and sdist built, passed package inspection and
  installed in fresh environments. Offline AI verification passed.
- Chromium passed 46 v2 scenarios and a separate 200%/400% zoom check.
  Classic passed 39 scenarios and 349 assertions.
  The Sync map filtered 10,000 fixture records, and 20 concurrent restore
  rounds each preserved the unselected trash entry. agent-browser reported
  zero axe violations on the sampled light desktop and dark phone map.
  agent-desktop exposed the filter, table and row through Linux AT-SPI.
- The Playwright Firefox download timed out. A WebDriver smoke on installed
  Firefox 157.0.1 verified the Sync map and review filter. macOS, Windows
  and human spoken or visual sign-off remain outside this run.
- The remaining release, native-tool, and human-study decisions are listed
  in @task.md.

## 2026-11-20 — Shelf density and Sync map matrix

- The Skills shelf remembers its card density. Compact uses a tighter grid and
  one-line description previews. Exact instances uses its existing layout.
- Sync map shows one skill per row and one observed agent scope per column,
  with name search, sticky table headers and 48 rows per page. Cells use glyphs
  and accessible labels for file and content states. Copy details open the
  existing repair panel and can return keyboard focus to the selected cell.
  Same-name copies within one scope are flagged for review.
- Map sync acts on selected eligible rows visible in the repair panel. A
  double-click sent one sync request in the disposable browser fixture.
  Undo restored the original file content. If a later copy fails, the panel
  reports the failure and retains Undo for completed copies with snapshots.
- Browser regression cases cover density after reload, observed states, focus
  return, mobile table scrolling, empty and single-row inventories, and
  filtering and paging a 10,000-skill fixture.
- The 13 px control-label trial saved no toolbar height at seven widths.
  The proposed translucent ink ramp fell below the text threshold on several
  surfaces. Kept the measured scale and palette, improved reader group and
  heading contrast, and added both reader surfaces to the contrast test.
- Quality links to Microsoft APM's audit reference when project metadata
  includes an APM manifest or lock. APM retains ownership of manifest
  validation and package import/export. The research and decisions are in
  @docs/53-apm-and-interface-decisions-2026-11-20.md.
- Verification on the updated tree ran 2,238 unit tests with seven skips,
  43 v2 cases in Chrome, 42 in Firefox and 342 classic browser assertions.
  Chrome covered actual 200% and 400% zoom. Both smokes, package checks
  and offline AI verification passed. Axe reported zero violations in the
  sampled light desktop and dark phone Sync map. Linux AT-SPI exposed the
  search field, table and named copy buttons. Spoken sign-off remains
  a human review item.

## 2026-11-20 — Two residuals closed: legacy Windows archives, repo credential helpers

- **Legacy Windows archives import again.** Tree hashes join names with `/` on
  every OS since 2026-11-20, so a manifest a Windows build wrote earlier (with
  `\`) failed verification for any skill with nested files.
  `atomic_io.tree_hash_matches` accepts the legacy digest only on an exact
  match (top-level files hash the same either way; the bytes are still fully
  hashed). `tests/test_archive_legacy_windows_hash.py` builds such an archive
  and imports it; a wrong digest is still skipped with "content hash mismatch".
- **Repository credential helpers.** `backup_sync.git_fetch` now refuses a
  `credential.helper` (incl. URL-scoped `credential.<url>.helper`) whose scope
  is the repository's own config, before fetching: a helper is a program, so a
  crafted repository could run code. Global/system helpers stay in use (a
  `-c credential.helper=` reset would have broken private HTTPS remotes).
  `_run_git` takes explicit `ok_codes` for the one `git config` lookup that
  exits 1 when nothing matches. Regression test in
  `tests/test_backup_sync_contracts.py` (fails without the fix).

## 2026-11-20 — v2 component ports and guideline pass

**[NOTE]** From the component-library survey (Aceternity, Magic UI, Untitled
UI, and the Vue libraries Inspira UI, shadcn-vue and Reka UI; 68 components
assessed, 13 rewritten for this stack outside the repo under
`~/design-refs/ports/`; Uiverse was blocked by Cloudflare). React/Tailwind/
framer-motion code cannot ship here (no build step, no new runtime
dependency), so only patterns were ported, rewritten from scratch.

- **Recovery backup dropzone** (visual spec: Untitled UI FileUploadDropzone,
  MIT): the bare native "Choose File" input became a labelled drop target. The
  native `#imp-file` input stays inside the `<label>`, so click, keyboard and
  screen readers need no script; a dropped file must end in
  .tar.gz/.tgz/.tar/.zip (the server still decides whether the bytes are an
  archive); status text is `role=status`. New `upload` glyph in the icon set.
- **Switch (WCAG 1.4.11):** the off track (~1.5:1 against the page) gets a 1px
  `--line-strong` ring (3.6:1).
- **Web Interface Guidelines (vercel-labs) pass:** `theme-color` meta for both
  schemes; `touch-action: manipulation` on controls; `scroll-margin-top` on
  anchored headings to clear the sticky bar; `overscroll-behavior: contain` on
  dialogs and the skill tree; `translate="no"` on skill names (identifiers were
  open to browser auto-translation); explicit text colour on `.field` for
  Windows dark-mode selects.
- **Browser surfaces (impeccable craft floor):** text selection uses the
  highlighter token, the caret is brand, scrollbars are quiet.
- CI hygiene: `65f3a62` went red on Windows / Python 3.11 only, three
  unrelated tests erroring in `TemporaryDirectory.cleanup` with WinError 32 on
  a `locks/*.lock` file (the lock code closes its handle on every release; the
  prior seven runs on the same code were green). `tests/test_00_portable_
  environment.py` now retries Windows temp cleanup for up to 2 s; a genuinely
  leaked handle still fails. Windows-only regression test.
- Not ported on purpose: the app already has a switch, tabs, toasts, dialogs
  and a command palette that pass axe and the browser suites; replacing them
  would churn tested markup for little gain. The ports remain a spec to diff.

## 2026-11-20 — v2 reference-driven polish: radii, icon stroke, history runs

**[NOTE]** From the measured reference study (`~/design-refs/`, 14 product UIs
incl. Linear, Vercel, Raycast, Resend, Supabase, Attio, via the godly/awwwards/
inspo MCPs and live pages): the near-universal radius family is 6/8/12/pill,
and icons render at a constant ~1.5px stroke.

- `--r-lg`/`--r-xl` 10 → 12px (cards, panels); controls keep 6, groups 8.
- Icons: `stroke-width: 1.5px` with `vector-effect: non-scaling-stroke` on the
  shapes, so every size renders the same stroke; the 2.4 / 2.2 / 1.2 per-size
  overrides are gone (measured: 1.5px at 14 and 18px).
- Recovery history collapses consecutive rows with one action in one minute
  ("6 skills · Create", names in a native `<details>`); single events are
  unchanged. `tests/test_v2_tool_behaviors.py`.
- Skills shelf letter headers are sticky under the 66px top bar (z-index
  below it), so a long shelf keeps its place; contract-tested.
- Skills toolbar: the Tag filter joins the filter row with a visually-hidden
  label like Agent and Sort (it was the only visible-label filter and sat
  alone on a second row); on phones the header actions span the page gutter
  instead of shrinking to a ragged right edge (measured: right edges 372/372/372
  at 390px).
- Sync copy rewritten in plain words ("whether the skill is on or off, and its
  supporting files"), replacing "file enabled state and companion files".
- Kept on purpose: the three font families and the serif page titles (the
  study endorses a serif display + sans UI + mono system); Plus Jakarta vs Inter
  density was not measured on our screens, so no family swap.

## 2026-11-20 — v2 interface pass: type scale, spacing rhythm, a11y, Home layout

**[NOTE]** Driven by the `better-interface` review (accessibility, layout,
writing, typography, colour, UI skills), two read-only audit subagents (a
designer walk-through at 1440/768/390 in both themes, and an axe-core 4.7
sweep of 11 routes × 2 themes), and design references gathered with the inspo
MCP plus Godly/Awwwards/vendor product UIs (report kept outside the repo at
`~/design-refs/skills-manager-references.md`).

- **Type scale.** 28 ad-hoc font sizes became 11 named tokens (`--fs-caption`
  12 … `--fs-display` 52) in `v2/styles.css`; every size is `calc(N px ×
  --fs-k)`. The "Large text" preference used to enlarge only `body` (almost
  every element sets its own size), so it barely changed anything; it now sets
  `--fs-k: 1.133` and every step follows (verified: card text 13 → 14.7px, h1
  44 → 49.9px, no horizontal overflow). Agent-logo initials stay fixed to their
  tiles. Fonts unchanged: Plus Jakarta Sans / Newsreader / IBM Plex Mono is the
  serif-display + sans-UI + mono pairing the references endorse.
- **Spacing.** 20 distinct `gap` values snapped to one rhythm
  (2/4/6/8/12/16/20/24/32/56).
- **Typography.** `text-wrap: balance` on headings, `pretty` on ledes and card
  descriptions; the empty-state icon stroke (rendered ~2.75px) now matches the
  ~1.5px set.
- **Accessibility.** axe `aria-allowed-attr` (serious): skill-tree status dots
  carried `aria-label` without a role (`role="img"` added); the Inbox badge's
  label moved to visually-hidden text; the formatting bar is a `toolbar` and the
  mini-diff a labelled `region`; the Sync map's mobile list had a second `h1`
  (now `h2`). axe: 0 violations on every route in both themes after the change.
- **Home.** "Shared by most agents" and "Recent changes" moved from the long
  right rail into the main column under the agent cards, removing a ~1,300px
  empty area; agent paths show their informative end (`…/.claude/skills`, full
  path in the tooltip) instead of a leading-ellipsis cut; the "If read in full"
  meter says "under 0.1%" instead of a misleading "0%" over a forced 1.5% bar,
  and its limit tick has a title.
- **Copy.** "skills in all" → "skills in total"; detected apps are "agents"
  throughout the shelf (was "tools"); "Delete forever" → "Delete permanently"
  (matching the rest of the UI).

## 2026-11-20 — Open-queue pass: peer-user check, list payload, card names, Windows reads

**[NOTE]** Work on the agent-actionable entries of the "Open for the maintainer"
list, done unattended at the maintainer's request.

- **ADR-001 revisit (Linux).** `web_security.require_same_user` refuses a
  loopback connection whose client socket another OS user owns, read from
  `/proc/net/tcp[6]` once per connection (~0.2 ms). Unknown ownership keeps the
  old behaviour, so macOS/Windows and restricted `/proc` are unaffected; no
  token, no client contract change. ADR-001 v1.2.0. `tests/test_peer_user.py`.
- **List payload.** `GET /api/skills?body=0` (both UIs' list request) also drops
  `portable_frontmatter` and `frontmatter_extensions`: 896 KB of the 4.8 MB
  body-less `scope=all` response on the maintainer's 2,082 rows, read by no
  list. The detail route and `body=1`/absent are unchanged.
  `test_performance_http`'s projection contract now names the omitted set.
- **Shelf cards (WCAG 2.5.3).** The card link's `aria-label` omitted visible
  text, failing axe's label-content-name-mismatch. The label is gone; the name
  block precedes the status row in the DOM and `.sk-top { order: -1 }` keeps the
  layout. axe 4.7: no violations on the Skills page. A library-only card said
  "In 0 tools"; it now says "Only in your library".
- **Windows reads racing a replace.** `documents.document_text` (the raw route)
  and `loader._probe_document` retry for ≤100 ms on Windows when a document is
  momentarily delete-pending (PermissionError / `is_file()` False). An absent
  document is never retried in scans. `tests/test_windows_read_retry.py`
  patches the platform flag so the branch runs everywhere.
- **Housekeeping.** Leaked 2026-10-09 fixtures `agent-only`/`demo` trashed from
  the maintainer's agent roots (restorable); two dangling Claude links removed.

## 2026-11-20 — Scope scan no longer blanks non-canonical names

**[NOTE]** Found by exploratory testing of the v2 Skills page against the
maintainer's real roots: a Codex row named `.system` showed as an "active"
skill with no description. `loader.scan_dir` passed each enumerated entry to
`path_safety.contained_entry_under`, which applies the skill-name rule to a
single-part path; the resulting `ValueError` was handled as a *link escape*.
So every directory whose name fails `NAME_RE` (`Upper-Case`, `.hidden-skill`)
was listed as a blank link-escape stub ("path escapes managed root"
reason, empty description), and a container with no `SKILL.md` of its own
(Codex's bundled `~/.codex/skills/.system/`) appeared as a skill.

**[SPEC]** `contained_entry_under(..., check_name=False)` is for scans only: the
entry was enumerated, not named by a caller, so containment and the Windows
separator check still run but the name rule does not. Non-canonical rows now
keep their real content and stay marked `unaddressable` (SCOPE-14). A
non-canonical directory with **no** document (Codex's `.system/`) stays visible,
because the v2 Inbox's "Not a skill" note depends on it (docs/08), but as a
document-less husk (`document_missing: true`, `addressable: false`) instead of
a link escape; `husk_record` now carries `addressable`. An empty folder with a
valid name keeps the old contract (not listed outside doctor). Name-addressed
callers keep the default. Doctor output on the maintainer's roots is
byte-identical before and after.

**[NOTE]** The first cut dropped document-less dot-folders entirely; unit tests
stayed green but the v2 browser suite failed ("Home Inbox count equals queue"
expects the `.system` note). Fixed before commit — the browser suites are the
only evidence for that contract.

Also in this pass (v2 copy): the on/off toast read "turned off in Codex. —
frees about…"; the token effect is now its own sentence. The AI "Shorten a
skill" page was titled "AI assist" while no model was configured (its id was
missing from the fallback heading map). Regression tests:
`tests/test_audit_batch4_contracts.py`, `tests/test_v2_interface_contracts.py`
(each fails without its fix).

## 2026-11-20 — Full suite on every OS, browser e2e in CI

**[NOTE]** CI ran only a four-module path/archive subset on macOS and Windows,
and `tools/e2e_v2` / `tools/e2e_classic` (not unittest modules, so `discover`
never reaches them) ran nowhere. The `xplat` job now runs `python -m unittest
discover -s tests` on ubuntu, macOS and Windows (Python 3.11 and 3.14), and a
new `e2e` job (Ubuntu, headless Chrome, sandbox on) runs both browser suites
against throwaway fixtures. Playwright comes from `tools/e2e_deps`, a
hash-verified lockfile installed with `npm ci --ignore-scripts`; it is CI/dev
tooling only, never a package or runtime dependency.

**[NOTE] Product portability bugs the full suite exposed** (each fixed with a
regression test):

- **macOS:** `/var` is a symlink to `/private/var`, so a folder upload
  (`web_upload`: resolved target vs unresolved `mkdtemp` root) and every
  registry fetch/commit (`install`: staging below a symlinked ancestor) failed
  on every default macOS install. Staging directories are now canonical
  (`path_safety.canonical_mkdtemp`). `check_docs` anchors were keyed by an
  unresolved path for the same reason.
- **Windows:** `os.fchmod` does not exist (registry cache, sidecar and review
  writes crashed; `fchmod_private`); `DirEntry.stat()` reports inode 0, so the
  risk scan marked every nested directory "changed" and returned
  `listing-incomplete` with no findings; the regex-assertion deadline needs
  `SIGALRM` and now refuses the pattern (fail closed) instead of raising
  `AttributeError`; the registry provenance manifest sorted `Path` objects
  (case-insensitive on Windows) against a string-sorted snapshot, so any tree
  with `SKILL.md` and `references/` looked like drift; `tree_content_hash` used
  `\` separators, giving an archive a different manifest hash per OS; the
  source-lock digest sorted `Path` objects (now `parts`, which keeps the
  existing POSIX order); `os.replace` onto a document a reader had open raised
  `PermissionError` (now retried briefly on Windows).

**[NOTE] Skips, each precise.** POSIX mode bits (assertions guarded, not whole
tests), shebang-script fake scanner (SkillSpector hook, skipped on Windows),
`fork`, FIFOs, `SIGALRM`, ESC in file names, `~user`, replace-while-open
descriptor races, WSL `bash`, and three concurrency stress tests whose racing
reader/renamer sees a transient sharing violation on Windows (see Open items).
The suite now normalises two platform differences before any test runs
(`tests/test_00_portable_environment.py`): a symlink-free temp root and LF from
`Path.write_text`.

**[?] Open items.** On Windows a reader that races an in-flight document
replace can get a transient `PermissionError`; the writer now retries, readers
do not. The external-scanner hook is not exercised against a fake tool on
Windows. A `macos-latest` leg can sit queued and be cancelled; that is runner
capacity, not a test result.

## 2026-11-19 — Faster all-scope list request (v2 Home first paint)

**[NOTE]** `GET /api/skills?scope=all&body=0` is 29–49% faster on a synthetic
fixture with an unchanged response: paired medians 212 → 128 ms (1,000 records,
root 6 components deep), 270 → 138 ms (10 deep) and 3.95 → 2.79 s (10,000).
Profile: about 30% of the request was `os.path.realpath` re-walking every path
component per row. Changes: one-`lstat` containment below a resolved root
(deferring to `realpath` for links and anything odd), a per-scan memo of resolved
parents for `physical_path`, the global scan's resolved root reused per row, the
reserved-name set hoisted, `os.path.isfile` and a string sidecar probe, and
compact JSON for list pages only. Parsed output identical at 1,000 and 10,000
records. gzip was measured and rejected (loopback-only). No field, schema, CLI or
Store change. Evidence: @docs/52-list-request-performance-2026-11-19.md,
@benchmarks/list-request-2026-11-19.json; tool `benchmarks/list_perf.py`.

## 2026-11-19 — Accept the `localhost` Host alias (issue #14 F-2)

**[NOTE] AI Center busy state.** One `busy` boolean was cleared by whichever
guarded request finished first, re-enabling buttons that start paid model
calls while another request ran. An in-flight counter now keeps it set until
the last one ends; a new Node test fails on the old code ([true, false, false])
and passes now.

**[NOTE] v2 follow-ups and PR #23.** The remaining frontend-review findings
were fixed: the "Compare with" select rendered blank while a copy was already
compared (now bound to the compared copy, verified live), a failed re-read was
shown only on Home, a new import kept the previous result line, and the
command palette navigated while a dialog refused to close. PR #23 (list
request) was reviewed and merged: its lexical containment shortcut answers only
when every component below an already-resolved root is a present, non-link
plain entry (exactly when `realpath` returns the joined path) and defers to
`realpath` otherwise. One post-merge suite run showed a single intermittent
failure that two further full runs did not reproduce.

**[NOTE] Security review.** A subagent reviewed archive, install, upload,
source-lock, backup-sync, frontmatter, CLI and AI paths; five findings were
reproduced and fixed. (1) Any caller of the settings API could point
`base_url` at itself and receive `OPENAI_API_KEY` from the server's
environment on the next call; environment keys now go only to the provider's
default endpoint unless the operator names one endpoint in
`SKILLS_MANAGER_AI_ENV_KEY_ENDPOINT` (the 2026-11-17 study workflow needs that
variable now). The end-to-end repro's fake server received no Authorization
header afterwards. (2) `untrusted_block` put labels into an attribute
unescaped and only defanged lowercase `</untrusted`. (3) `local_manifest` read
a file before its 4 MiB check and `tree_content_hash` read whole files and
blocked on FIFOs; both are bounded/streamed, with an identical digest.
(4) `git_fetch` let `remote.<name>.uploadpack` run a program; it now pins
`--upload-pack` and the pager (a repo-local credential helper is a recorded
residual). (5) `validate --path` printed raw directory names.

**[NOTE] v2 bug review.** A subagent traced the v2 code; each finding was
checked. Ctrl/Cmd+S skipped the Save button's guard, so with no target ticked
it discarded the edit (reproduced, then fixed and re-verified). Clicking inside
a dialog left focus on `body`, so Escape and the Tab trap stopped working
(fixed: the dialog takes focus). `refresh()` and skill history had no
stale-response guard; history never reloaded after a change; Test connection
reloaded the AI form and wiped unsaved edits including a typed key; several
counts printed "1 skills".

**[NOTE] Docs audit.** A subagent compared README and the CLI surface doc with
real runs in an isolated HOME; each finding was re-run before editing. The
README told users to `chmod 700 ~/.local/share/skills-manager`, but the check
is on the base folder, so that never cleared the error; it still said to avoid
`localhost`; and its drift recipe missed body-only differences (plain `doctor
--scope all` flags differing descriptions, `--hygiene` flags differing bodies).
The CLI surface doc lacked `create --metadata` and `trash restore --snapshot/
--scope` and described `templates new` wrongly. `--scope` help omitted
`commandcode`.

**[NOTE] CLI typo hints.** A first-time-user pass found clear errors and exit
codes but no help for typos: `skills-mgr lst` listed 32 commands with no hint on
3.11–3.13 (argparse's `suggest_on_error` exists only on 3.14), and `view
pdf-tool` did not mention `pdf-tools`. Both now suggest the closest match;
skill suggestions come only from library folder names that pass the name rule,
so a hostile directory name cannot reach the terminal. Exit codes are unchanged.

**[NOTE] Tablet help.** The header hid the "?" keyboard-shortcut button from
601 to 900 px although it fits there (checked at 900/820/700/640/601 px with no
overflow and unclipped tabs); it now hides only below 600 px.

**[NOTE]** Maintainer-approved. Opening `http://localhost:<port>` against the
default `127.0.0.1` bind returned 403 on every request. `WebAppServer` now
allows exactly `localhost:<port>` beside the bound literal; Origin follows the
same set. `localhost` resolves on this machine, so a DNS-rebinding page, which
arrives under an attacker-controlled name, is still refused, as are other
ports, bare `localhost`, `sub.localhost` and `localhost.evil.example`. The
pinned rejection test became an acceptance test plus a boundary regression;
ADR-001, the threat model and the web UI client contract were updated.

## 2026-11-19 — Review loop 1: UI fixes, pyflakes gate, repository cleanup

**[NOTE]** An in-depth review (backend, web security boundary, live v2 UI,
lint) produced three v2 fixes: the narrow-width tab mask now applies only
while tabs are clipped (it dimmed "Tools" when every tab fit); a skill held
only in the library reads "only in your library" instead of "in 0 places";
and a Markdown link address containing parentheses is no longer cut short
(new regression test). Ruff now selects all of pyflakes, and 40 dead
imports/variables were removed. Seven `prototype-*` folders, `design-concepts/`
and `.design/` (about 18 MB, referenced by no code, test, CI or packaging)
were removed; three historical links now point at commit `515f5be`.
`.specs/` evidence is kept pending a maintainer decision.

**[NOTE] Loop 2 (accessibility).** Lighthouse scored v2 accessibility 96: 1,508
text nodes on turned-off skill cards fell to 2.4–2.8:1 because the card was
dimmed with `opacity: .6`. Those cards are links, so AA applies; they now use a
dashed edge and passing muted tokens. axe-core (agent-browser `a11y`, WCAG 2.2
AA tags) then flagged white initials on the Claude (3.1:1) and Gemini (4.1:1)
badges; both fills were darkened along their hue to 4.6/4.8:1, and a test pins
every badge fill at 4.5:1 or better. All seven v2 routes now pass axe in light
and dark; Lighthouse reports accessibility, best practices and SEO at 100.

**[NOTE] Brand mark.** v2 had no favicon (`data:,`) and a text "SM" tile. The
new mark is drawn by hand on a 32-unit grid: a folded skill page carrying a
switch, the product's core action. `skillsmgr/webui/v2/logo.svg` is the
favicon and README logo and inverts on dark colour schemes; the header carries
the same drawing coloured by theme tokens so it follows the in-app toggle.
Checked at 16–160 px on light and dark grounds; a test keeps the file
well-formed XML, since a malformed SVG decodes to a silent 0x0 image.

**[NOTE] Loop 3.** At 375 px no v2 route overflows horizontally. A read-only
fuzz sent 3,528 GET requests with malformed parameters (negative, huge, NUL,
traversal, invalid UTF-8) to every read route and received no 5xx. axe found
one classic violation, a scrollable first-scan list keyboard users could not
reach; it is now a focusable, named region. A keyboard walk of v2 showed text
fields signalled focus only by a 1 px border change; they now carry the same
2 px outline as every other control.

**[NOTE] Logo restart.** The owner rejected the page-and-switch mark. A
research pass (studio process: brief, volume, reduction, choosing by function;
2024–26 clichés: sparkles, gradients, circle-with-hole, hexagons, node
networks, documents with badges, toggles) informed five concepts drawn in
parallel with the vetted MIT `logo-designer` skill. Each was rendered at 128,
32 and 16 px, in 1-bit and on dark (board: `docs/images/logo-concepts-2026-11-19.png`).
The S monogram was legible but generic; the bars read as a sort icon; the
stepped and pixel S read as "5". The winner is **the switchboard**: rows are
skills, columns are agents, one row has slipped out of step and its last copy
is the one the tool flags in terracotta. The offset carries the meaning in
1-bit, and every edge sits on a whole pixel at 16 px.

**[NOTE] Real agent marks.** v2 now shows the official marks for Claude Code,
Codex, Cursor, Gemini and OpenCode instead of initials badges. Path data is
vendored verbatim from Simple Icons (CC0-1.0) and theSVG (MIT, Codex), with
the source and licence beside each entry; marks remain their owners'
trademarks and only identify the agent. Monochrome marks take the theme ink,
so they invert in dark mode. Command Code and the shared skills folder keep
initials badges because no open mark exists. All seven routes still pass axe
WCAG 2.2 AA in light and dark.

**[NOTE] Missing marks filled.** The Agent Skills standard's own repository
(agentskills/agentskills, Apache-2.0) carries official adopter logos, so
Command Code now shows its ⌘ symbol (extracted from its lockup) and the shared
`~/.agents/skills` folder shows the Agent Skills hexagon. "Your library" shows
the Skills Manager mark. The icon table supports several paths per mark, a
custom viewBox and theme-token fills. `docs/images/agents/*.svg` are generated
from the same table with a dark-scheme rule and form the README agent row.

**[NOTE] Logo research and refinement (superseded mark).** A survey of logo tooling found no
MCP server worth adopting: the SVG-generation servers wrap an image model
(the "AI slop" risk), and the icon servers only search existing sets. The
adopted pipeline is free CLI tooling: resvg (via `@resvg/resvg-js`) rasterised
the mark at 16/24/32 px for an 8x nearest-neighbour legibility check, which
showed half-pixel edges blurring at 16 px. The mark was redrawn with every edge
on an even coordinate (one whole pixel at 16 px), a solid text line and a
full-width switch track. No PNG/ICO set ships: every supported browser takes
the SVG favicon, and nothing else in the product displays an icon.

## 2026-11-18 — Evidence-based context sweep

**[NOTE]** Applied the supplied video's context-management practices to
the development workflow. `AGENTS.md` now distinguishes verified behavior
from intended change, uses the active task status and routes historical
lookups explicitly. `CLAUDE.md` imports the shared entry point with literal
router pointers. The developer-only context sweep asks for present evidence
and history, gives independent reviewers the claims without the proposed
verdict, and reports before any authorized correction.

The first sweep corrected current guidance for the v1.0.2 release, default
v2 paths, the insights compatibility module, and the data root. It also
updated the historical task label and retired manual release approval claim.
The research and file evidence are in @docs/51-agent-context-sweep-2026-11-18.md.

Initial verification exposed a collision between the skill trial and
the product's project-root discovery. Its test-generated files were
relocated to a private evidence directory. The final procedure lives
under `tools/` with a manual Claude command and an explicit Codex route.

**[NOTE] Verification.** Claude Code 2.1.325 listed `/context-sweep` in an
offline startup probe. Skills Manager's validator accepted the procedure,
and scope discovery found no project skill roots from this change. The
2,175-case test suite passed on Python 3.11–3.14 with 5/5/5/4 optional skips.
Both smokes, docs, complexity, design-token and static gates passed.
The pinned wheel and sdist passed package-data checks and excluded the
developer tooling. The installed-wheel AI probe also passed.

## 2026-11-18 — Published and verified v1.0.2

**[NOTE]** GitHub rejected a retry of the original run because it was
more than 30 days old. Recovery verified the original tag and retained
artifact against both TestPyPI hashes and the original GitHub build
attestations. The run used the existing `release.yml` Trusted Publisher
to publish both files to PyPI with publish attestations. It then created
the GitHub release on the existing tag and passed the published install
and CRUD smoke job.
[Recovery run](https://github.com/udayvarmora07/skills-manager/actions/runs/44252837346)
[PyPI release](https://pypi.org/project/skill-control-plane/1.0.2/)
[GitHub release](https://github.com/udayvarmora07/skills-manager/releases/tag/v1.0.2)

**[NOTE]** Both PyPI file digests and both downloaded GitHub release assets
matched the original artifact. A separate fresh install with the pinned
wheel hash confirmed the version, vendored Vue and CLI create/list. The
original tag still resolves to `ef9bfd6`. The one-time dispatch was removed
from `main` after verification. Future tagged releases use the automatic
TestPyPI-to-PyPI workflow.

## 2026-11-18 — Automatic PyPI release after TestPyPI

**[NOTE]** The maintainer removed the GitHub deployment approval requirement
for package publication. GitHub's API confirmed the existing `release`
environment now has zero required reviewers. The workflow still publishes
through `testpypi` before the `release` environment, which remains the
environment named in the publish job. The completed `v1.0.2` run remains
failed. A retry or a new release tag would start a separate publishing action.
[Release environment](https://github.com/udayvarmora07/skills-manager/settings/environments/21667496623/edit)
[Failed job](https://github.com/udayvarmora07/skills-manager/actions/runs/37442412642/job/112279779295)

## 2026-11-18 — Browser coverage, APM evidence, and offline fidelity probe

**[NOTE]** The v2 browser runner can replay the regression suite in
Playwright-managed Firefox. It records the engine and version and redirects
Codex and Gemini settings reads to fixture paths. Firefox 151 passed all
38 scenarios and headed Chrome 157 passed all 39, including real zoom at
200% and 400%. Both passed the forced-colors focus check. Browser results
are under `/tmp/skillsmgr-remaining-20261118/final-firefox` and
`/tmp/skillsmgr-remaining-20261118/final-chrome`. The classic harness passed
six viewports and four first-scan scenarios. Its six dated screenshots are under
`/tmp/skillsmgr-remaining-20261118/pilot-screenshots-final`. External
screenshot review, human visual and spoken sign-off, and consented
participant sessions remain pending. The protocol is in
@docs/25-design-partner-pilot-kit.md.
[Playwright Firefox setup](https://playwright.dev/docs/browsers#firefox)

**[NOTE]** Selected projects in v2 Quality now report `apm.yml` and
`apm.lock.yaml` as separate unavailable signals. Microsoft defines the first
as the project declaration and the second as a resolved lock. The check uses
two metadata probes, ignores leaf symlinks and non-regular files, and keeps an
inspection error local to the affected signal. APM YAML parsing, installation,
export and project-lock ownership remain deferred. Native profile writes
still need a per-agent write policy. Transcript usage needs a privacy
decision before collection, and stale-archive policy depends on that evidence.
[APM manifest schema](https://github.com/microsoft/apm/blob/main/docs/src/content/docs/reference/manifest-schema.md)
[APM install and lockfile documentation](https://github.com/microsoft/apm/blob/main/docs/src/content/docs/consumer/install-packages.md)

**[NOTE]** An OpenCode 2.3.2 offline probe confirmed that the JSON CLI emits a
completed `skill` tool call and the next model request receives the synthetic
skill instructions. The fake provider directed the call. An attended run
using an approved model and the real transport remains required for native
routing agreement. Source paths, protocol and observed limits are recorded
in @docs/48-ai-http-study-2026-11-17.md.

**[NOTE]** The first parallel matrix run exposed an existing cleanup-test
race on Python 3.12. The process-group kill was pending for the child when
the test inspected `/proc`. The test now polls for an exited or reaped child
with a three-second deadline. The v2 double-click test likewise waits for
the sync response and the completed Undo message before checking filesystem
state. Fresh hash-locked wheel and source artifacts
passed inspection and offline install probes with the pinned backend. The
installed-wheel AI probe passed. The artifacts identify as 1.0.2 and were
built for local verification. The complete Linux matrix passed 2,175 tests
on each of Python 3.11–3.14 with 5/5/5/4 optional skips. Both smokes, the AI
suite, compilation, the docs gate, the complexity ratchet, design tokens,
Ruff and Bandit passed. Current macOS and Windows execution was unavailable.

## 2026-11-18 — Release state recheck

**[NOTE]** The `v1.0.2` release run completed with failure on November 5.
Attempt 3 shows the TestPyPI publish succeeded, the PyPI publish job failed,
and the GitHub Release and published-distribution verification jobs were
skipped. The run reports zero pending deployments. The job has no listed
steps and its log is unavailable, so the cause of the PyPI failure remains
unknown. TestPyPI lists the non-yanked 1.0.2 wheel and sdist; PyPI lists
1.0.1. The repository still declares 1.0.2, so a future 1.1.0 candidate
requires an owner-selected version and a matching reviewed tag. The
workflow builds and verifies once, attests the bytes, then requires the
TestPyPI stage and protected release environment.
[Release run](https://github.com/udayvarmora07/skills-manager/actions/runs/37442412642)
[TestPyPI](https://test.pypi.org/pypi/skill-control-plane/json)
[PyPI](https://pypi.org/pypi/skill-control-plane/json)

**[NOTE]** Public CI for `9aafb94` shows successful jobs except the cancelled
macOS Python 3.14 leg. GitHub's annotations say the hosted runner never
acquired that job and cite macOS ARM64 capacity constraints.
[CI run](https://github.com/udayvarmora07/skills-manager/actions/runs/44135509064)

## 2026-11-17 — Measured size/performance improvement and Rust assessment

**[NOTE]** Completed the maintainer's research-first Rust/stack assessment and
kept the optimized Python/Vue reference. Conditional permission for migration
is recorded; no runtime language, framework, dependency or data/schema change
was justified by the present evidence. The assessment compares optional Rust,
native backends, Tauri, GPUI/Iced/Slint, Go and full rewrites, including size,
startup/RSS, frontend, safety, portability, maintenance and rollback. Sources,
limits and the decision are in
@docs/50-rust-size-and-performance-assessment-2026-11-17.md.

Used all four requested research tools: agent-reach retrieved the uv README and
the original Discord CTO post through its OpenCLI-backed Twitter channel;
OpenCLI Browser read the Vue performance guide in an owned session; Vercel's
agent-browser read Cargo documentation and verified the isolated app. The CTO
post confirms a Rust/GPUI client effort and upcoming testing, not independently
measured resource gains or general availability. No external message/post or
live model request was sent.

Four byte-identical Plex Sans resources now share canonical files. All twelve
font-face weight/style/range descriptors and font bytes remain identical;
prototype references were corrected too. The wheel shrank **14.32%**, from
1,069,942 to **916,682 bytes** including the scan optimization. An incremental
build retained deleted fonts in ignored output; the unchanged exact-members
gate rejected it. Fresh-source, hash-locked wheel/sdist builds and exact installs
pass; all **99** packaged files match source. The isolated wheel target has
4,258,350 file bytes including generated bytecode/metadata, excluding shared
Python/browser runtimes and filesystem allocation overhead.

Combined single-agent Doctor/hygiene requests reuse one diagnostic observation,
with distinct husk/duplicate handling and fresh reads on the next request.
Malformed recursive document directories/links retain separate-scan behavior;
collector errors remain visible. Standalone/global/all paths are unchanged.
Three alternating warm-cache synthetic CLI samples including JSON show
1,000-skill median **829.5 → 674.6 ms** (−18.7%) and 10,000-skill median
**8,127.2 → 6,045.1 ms** (−25.6%). Each after range is below its before range;
small sample counts and shared-host activity preclude p95/portable/UI/global-
scope or Rust-speed claims. Raw samples, CPU/RSS and source hashes:
@benchmarks/rust-assessment-2026-11-17.json.

**[NOTE] Verification:** **2,172 tests** pass on each Python 3.11–3.14
(5/5/5/4 optional skips), including eight new reuse regressions. Both smokes,
docs, unchanged complexity budget, design tokens, Ruff/Bandit, compilation and
exact wheel/sdist install/AI probes pass. Browser checks load all three Sans
weights from two canonical resources with no page errors/overflow, including
320px layouts; v2 fonts also load. Independent review found and verified the
prototype-reference and recursive-directory corrections. No full native-agent,
other-OS, human accessibility or fresh-machine runtime comparison is claimed.
Private traces, source snapshots, artifacts and recovery evidence are retained
at `/tmp/skillsmgr-rust-study-20261117`. The earlier five-task batch is already
pushed as `d97072e`; normal verified main integration remains authorized.
The original 15 owner/release/human/native/deferred entries remain open.

## 2026-11-17 — Second five-task continuation verified for main

**[NOTE]** Completed five bounded tasks: grouped personal Claude folder
observations; supplied-project Codex declarations; plugin manual-only intent
caveats; lockfile normalized-name collisions/source-path uncertainty; and
lossless tracker/progress archival. Native discovery, trusted/session settings
and unique upstream source resolution remain unknown. The two originally cited
lockfile bugs are closed upstream; no stale bug verdict is added. Sources and
bounds: @docs/49-read-only-compatibility-followups-2026-11-17.md.

Review corrected false collisions from display-path truncation, explicit null
source paths mistaken for absence, and display-name truncation changing the
folder being checked. Incomplete advisory reads remain separate from primary
skill-document coverage, so unrelated config/group evidence does not block a
complete document baseline. CLI and both UIs expose group/collision evidence;
scrollable v2 finding JSON now has a named keyboard-focusable region.

**[NOTE] Verification:** All 2,164 tests pass on each Python 3.11–3.14
(5/5/5/4 optional skips), including 34 added tests. Both smokes, docs,
complexity (1,364 functions across 49 files), design tokens, Ruff 0.16.8,
Bandit 1.9.4 (zero findings), compilation and changed JS syntax pass. The two
new observer modules are included in the unchanged complexity budget. Fresh
hash-locked wheel/sdist builds, isolated installs and installed compatibility/
AI probes pass; all 103 packaged source files match both delivery installs.

Agent-browser verified all new finding types, contained project selection,
classic group/collision names, keyboard focus, no page errors and no horizontal
overflow at checked 320/1,440px views. Expanded-view axe 4.12.0 reports zero
automatic violations after the scroll-panel correction. Some contrast checks
and two classic ARIA rules remain inconclusive; no full accessibility or human
spoken-screen-reader sign-off is claimed. Real Windows/macOS and native-agent
comparison remain untested; unsupported safe-reading capabilities report
unavailable. No live model provider was called for this continuation.

All 136 original task sections and 99 original progress sections remain
byte-identical in the live files or new indexed archives. The original 15
gated/deferred live entries remain open, including historical overlaps. Prior
archives and skill data were not modified. The maintainer's additional request
is recorded in `AGENTS.md` v0.3.1: research first, use/install suitable tools,
skills, custom agents, MCP servers and open-source projects as needed, with
Terra/Luna preferences and the specific existing product/release gates retained.

Private matrix logs, browser observations, artifact hashes, source/archive
receipts and recovery checkpoints are retained at
`/tmp/skillsmgr-next5-20261117-wia_vn2t`. Main integration and a normal push are
authorized after this current-tree verification and hostile diff review.

## Resident-history rule (2026-11-17)

**[SPEC]** Keep current delivery receipts and live pending work resident. Move
historical entries verbatim into indexed archives when the resident log grows
past approximately 100,000 characters. Sections with relative Markdown links
stay at their original location; this avoids rewriting historical evidence.
The archival receipt verifies each original entry is still present byte-for-byte
in either its original file or the new archive. The original 15 open tracker
entries remain in the live queue. No skill data, releases or prior archive was
modified by this documentation move.

## 2026-11-17 — Five-task batch verified for main

**[NOTE]** Completed the five selected unlocked tasks: F8 packaged static
Bash/Zsh completion and optional Python 3.14 suggestions; per-skill discovery
evidence in Workspaces; filesystem acquisition degradation for hygiene;
accurate model-simulation wording; and conservative unknown Codex invocation
metadata. History archival was replaced by the last concrete estimate fix.
No new command, flag, Store method, schema or runtime dependency was added.

GPT 6.1 Terra handled completion/packaging and scanner changes in separate
file-owned tasks; GPT 6 Luna handled Codex metadata and independent review.
Root integration added the UI/evidence work and owning docs. Actual Python
3.14 root and nested command typos exit 2 with a suggestion; unsupported Python
versions keep their existing error behavior. Completion scripts are static and
never scan skills, contact a service or change shell startup files. Final
shell review also replaced the Zsh-special `path` variable with a private
grammar variable; its path-preservation regression fails with the original
script and passes with the correction.

The scanner regressions were red before their fixes. Review also corrected
ordinary-folder and file-link false degradation, classified wrong-type roots,
and preserved managed peer links. Discovery matching now enforces flat versus
recursive roots and lexical boundaries, deduplicates represented physical
copies, and labels missing/suppressed scope mappings unverified. A bounded empty
result keeps its partial-evidence notice. These views do not assert runtime
activation or elect precedence winners. Unknown Codex metadata produces a
known-only token subtotal and unknown inclusion, independently of the budget.

**[NOTE] Verification:** 2,130 tests pass on Python 3.12 (five optional skips),
including 36 added tests. Sixty-six focused cases pass on each Python 3.11,
3.13 and 3.14 (two optional skips on 3.11/3.13, one on 3.14). The ordinary host
PATH has no Zsh and skips its case; a separate run using a temporary extracted
Ubuntu Zsh 5.9 passes, including shell-path preservation. Bash execution/syntax,
static grammar parity and exact packaged script bytes are checked. Both smokes,
docs/design/complexity (1,336 functions), pinned Ruff 0.16.8/Bandit 1.9.4 (zero
findings), compilation and changed JS syntax pass. Initial full runs exposed
synthetic archive fixtures missing the new package data; the fixtures were
updated without changing their security assertions. The final full run is green.

Fresh hash-locked wheel/sdist builds pass package-data checks, installed-wheel
AI verification, and isolated five-task probes from each exact artifact. All
101 packaged files match current source. Private logs, artifact hashes,
source manifests and recovery data are retained at
`/tmp/skillsmgr-five-20261117-42g781b1`.

Agent-browser observed the shared-skill discovery rows and Home's unknown
Codex listing/known budget, plus simulation notices on configured synthetic
Trigger/Budget pages. The fixture used a no-key localhost provider setting
without a provider request. New discovery-panel axe audits passed in settled
light/dark themes with zero violations or incomplete rules. Checks at 320,
768 and 1,440 px found no overflow; no page runtime errors were observed.
No real native-agent comparison, Windows/macOS execution or human visual/
spoken-screen-reader sign-off is claimed. Existing scans remain non-atomic;
files removed before observation can still look absent. Vendor root rules
were reused, not newly re-verified. The maintainer authorized a normal main
push after current-tree verification and hostile diff review. The original
15 release/owner/human/native-fidelity/deferred entries remain open.


## Historical sections retained for relative links

**[NOTE]** The following dated receipts remain verbatim to preserve their
relative Markdown link targets. They are historical, not current test counts.

## 2026-11-06 — Plan: optional SkillSpector hook, then stdlib risk patterns

**[NOTE]** Plan only; no source changed. NVIDIA SkillSpector cannot be merged
(about 20 runtime dependencies, Python >= 3.12, LLM/OSV egress, and a
DO_NOT_INSTALL verdict that conflicts with the advisory-only rule), so the plan
runs an installed copy as an optional external program in the two existing
review chokepoints and later rewrites a few static checks with the stdlib.
Verified locally on v2.12.0: `--format json --no-llm` reported AR1/PE3/SC2 on a
hostile fixture. SC4 still contacts `api.osv.dev` under `--no-llm`, with no
offline switch. See the
[plan](superpowers/plans/2026-11-06-external-skill-scanner.md).

## 2026-11-06 — Complete v2 feature parity and promote the default

**[NOTE]** The maintainer first approved clickable mockups, then explicitly
requested production integration using the existing v2 design and default
promotion after verification. Work is local on `feat/v2-feature-parity`.
The [design inventory](superpowers/specs/2026-11-06-v2-feature-parity-design.md)
records the source baseline; the
[implementation plan](superpowers/plans/2026-11-06-v2-feature-parity.md)
records acceptance evidence. The
[earlier mockup](https://github.com/udayvarmora07/skills-manager/blob/515f5be/prototype-v2-parity/README.md) remained an isolated design aid (removed from the tree 2026-11-19; last present in `515f5be`).

V2 now contains the remaining classic workflows: registry/runner/folder install,
profiles, templates, hygiene/validation/diagnostics, workspaces, preferences and
index maintenance, exact-copy source update/whole-tree rollback, logical tags,
reviewed batch operations, rich metadata editing, persistent scoped history and
full archive recovery. `/` and `/index.html` redirect to `/v2/`, preserving
query/hash; classic remains at `/classic/`. Existing v2 fonts, colours, document
reader, daily navigation and dark theme remain the visual authority. Inspo's
configured HTTPS MCP endpoint supplied recommendations/searches and three
archived captures; it was not enabled globally. UI/UX Craft, Design Taste
Frontend, Better Accessibility and Frontend UI Engineering informed the work.

The backend additions are contained template reads and explicit PATCH optional
field/body clears. Omission preserves values; empty descriptions are rejected.
The shared field guard's complexity budget tightened from 7 to 6. No public
Store method, application CLI command, schema or runtime dependency changed.
Luna/Terra reviews found races and copy-identity problems; fixes bind folder
approval to File identities, use the selected copy's description/scope, send
only changed editor fields and isolate independent read results. Behavioral
and real-HTTP regressions cover these cases. The final narrow Terra review
reported no unresolved defects in those fixes.

All write checks use temporary HOME/data roots. The classic browser suite
passed 38 scenarios / 318 assertions; the expanded v2 suite passed 34 scenarios,
including real template/profile operations, retry and 320/768/1280 layouts in
both themes. The six-viewport classic smoke harness also passed after moving
its probes to `/classic/`. The final current-tree suite passed 1,386 tests on Python 3.12; both smokes,
syntax/compilation, docs, design tokens, complexity, Ruff and the medium/high
Bandit scan passed. The final v2 browser repeat again passed all 34 scenarios. Packaging with the pinned hash-checked
toolchain includes all three new v2 assets in wheel and sdist. Live registry
fetch/commit, actual external runner execution and human screen-reader sign-off
are not claimed. Agent-scope trash has no in-app restore, and the interface
states that limit. No personal skills were changed; no commit or push was made.

The live queue and current delivery state remain in @task.md.
