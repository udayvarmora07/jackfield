# Progress Log — Skills Manager

**Version 0.8.0**

**AI manifest**: Current delivery receipts and a bounded resident window.
Earlier entries moved verbatim to @docs/archive/06-progress-log-through-2026-11-17.md;
older archives remain indexed by @docs/archive/README.md. The live queue is
@task.md. Retained historical sections are explicitly labeled below.

## 2026-11-19 — Accept the `localhost` Host alias (issue #14 F-2)

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
