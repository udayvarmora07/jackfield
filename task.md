# Task Checklist — Skills Manager

**Version 0.11.1**

**AI manifest**: Live work and the remaining gated/deferred queue. `[ ]` means
pending, `[/]` in progress, `[x]` completed. Historical milestones, including
older duplicates of this queue, are archived at
@docs/archive/task-history-through-2026-11-17.md. Archive checkboxes are dated
records, not additional live work.

## All-scope list request speed (2026-11-19)

- [x] Profile `GET /api/skills?scope=all&body=0` on 1,000 and 10,000-record
  synthetic fixtures; land only measured, behavior-preserving changes with a
  pinned equivalence test; reject gzip with evidence
  (@docs/52-list-request-performance-2026-11-19.md).

## Size, performance and Rust assessment (2026-11-17)

- [x] Research current primary sources and inspect this app using agent-reach,
  OpenCLI, OpenCLI Browser and Vercel agent-browser, as requested.
- [x] Measure package/runtime size and representative startup, scan and hygiene
  workloads; separate application bytes from shared interpreter/browser costs.
- [x] Keep only verified size/performance improvements with unchanged behavior:
  deduplicate identical font resources and test one-request Doctor scan reuse.
- [x] Record a source-backed Rust/native/hybrid/full-rewrite decision, including
  portability, security, maintenance, rollout and measured limitations.

The maintainer permits a stack/language migration if research justifies it.
Research does not itself select or ship a replacement. No skill data or native
consumer configuration may be sacrificed for a timing or package-size claim.

Verified outcome: the clean wheel is 14.32% smaller (1,069,942 → 916,682
bytes). Three paired synthetic warm-cache CLI samples show median reductions
of 18.7% at 1,000 skills and 25.6% at 10,000 for single-agent Doctor/hygiene.
All 2,172 tests pass on each supported Python version, both smokes and artifact
install probes pass. Rust/full migration remains an evidence-gated future
option; the assessment recommends the optimized Python/Vue shipping reference.
No language/framework/schema/runtime dependency changed. Full evidence:
@docs/50-rust-size-and-performance-assessment-2026-11-17.md.

## Second five-task continuation (2026-11-17)

- [x] Observe grouped personal Claude skill folders without asserting native discovery.
- [x] Observe supplied-project Codex skill declarations without applying native state.
- [x] Separate plugin manual-only intent from historical invocation compatibility reports.
- [x] Report lock-name collisions and unverified source-path declarations.
- [x] Archive completed tracker/progress history losslessly and preserve the open queue.

Verification, commit and normal push to `main` are authorized. No new CLI
command, Store method, schema or runtime dependency is planned. Native sessions,
human sign-offs, owner decisions and publication retain their separate gates.

Verification: 2,164 tests pass on each Python 3.11–3.14, with optional skips
of 5/5/5/4 respectively; both smokes, repository gates and exact package/install
probes pass. All 235 original task/progress sections survive byte-for-byte in
either their original file or indexed archives. Normal main integration is
authorized. The original 15 gated/deferred entries remain open.

## Additional maintainer request (2026-11-17)

- [x] Record research-first tool/setup authorization and Terra/Luna subagent
  preferences in `AGENTS.md`, preserving specific product and release gates.

## Continuation (2026-11-18)

- [x] Recheck the public release status and the cancelled macOS CI leg.
- [x] Exercise v2 in Firefox and retain a repeatable browser runner.
- [x] Report the presence of regular APM project manifests and locks in v2 Quality.
- [x] Verify OpenCode skill-load evidence with a synthetic local provider.
- [x] Capture dated local screenshots for the design-partner pilot review.
- [x] Stabilize the subprocess cleanup and browser sync/Undo assertions.
- [x] Recover and publish the original attested `v1.0.2` wheel and sdist.
- [x] Verify both public artifacts and a clean PyPI install, then remove the
  one-time recovery workflow.

Evidence and remaining decisions are recorded in @docs/06-progress-log.md.

## Agent context hygiene (2026-11-18)

- [x] Verify the research behind the video and record its limits.
- [x] Share task-scoping and context rules between Codex and Claude Code.
- [x] Add an evidence-only context sweep with explicit invocation.
- [x] Verify and correct stale guidance in the current session entry points.

## Autonomous review and improvement loops (2026-11-19)

The maintainer asked for an in-depth review, then repeated improve/evaluate
loops while away. Locked constraints and ASK gates still apply; items that
need a decision are listed under "Open for the maintainer" instead of being
done.

- [x] Loop 1 — review: backend, web security boundary, v2 UI (live), lint.
- [x] v2 nav: fade the tab strip only while tabs are actually clipped.
- [x] v2 skill page: library-only skills say "only in your library", not "in 0 places".
- [x] v2 Markdown: a link address with parentheses is shown whole.
- [x] Static gate: Ruff selects all of pyflakes (`F`); 40 dead imports/variables removed.
- [x] Remove unreferenced prototype/design-concept folders and generated build output.
- [x] Loop 2 — evaluate as a user with Lighthouse and axe-core (agent-browser `a11y`).
- [x] v2: turned-off cards keep AA contrast (dashed edge, muted tokens; no opacity).
- [x] v2: Claude/Gemini badge fills darkened to clear 4.5:1 under white initials; test added.
- [x] Every v2 page passes axe WCAG 2.2 AA in light and dark; Lighthouse a11y 100.
- [x] Brand: hand-drawn SVG mark (a skill page carrying a switch), v2 favicon,
  theme-token header mark and README logo; flat palette, no gradients or glyph tropes.
- [x] Loop 3 — phone width (375 px): no horizontal overflow on any v2 route.
- [x] Loop 3 — read-only REST fuzz: 3,528 malformed GET requests, zero 5xx.
- [x] Classic: the first-scan root list is a focusable, named scroll region (axe clean).
- [x] v2: text fields show the same 2 px focus outline as every other control.
- [x] Logo restart (owner rejected the page-and-switch mark): researched studio
  process and 2024–26 clichés, installed the vetted MIT `logo-designer` skill,
  drew five concepts in parallel, chose "the switchboard" by scale, 1-bit and
  distinctiveness tests; applied to favicon, header and README.
- [x] Real agent marks (Claude Code, Codex, Cursor, Gemini, OpenCode) replace
  initials badges across v2, vendored from Simple Icons (CC0) and theSVG (MIT);
  Command Code and the shared folder keep badges (no open mark exists).
- [x] Scope label "Opencode" corrected to the project's own "OpenCode".
- [x] Missing marks filled: Command Code's official ⌘ symbol and the Agent Skills
  hexagon (both from the Apache-2.0 agentskills/agentskills repo), and the
  Skills Manager mark for "Your library"; README shows the agent row.
- [x] v2: keyboard-shortcut help ("?") is reachable at tablet widths (601–900 px).
- [x] CLI: typo hints for commands (all supported Pythons) and library skill names.
- [x] Security review (subagent, each finding reproduced, then fixed):
  environment API keys follow only the provider's default endpoint (operator
  opt-in `SKILLS_MANAGER_AI_ENV_KEY_ENDPOINT`); `untrusted_block` labels and
  case-variant tags cannot end the data region; source manifests and tree
  hashes are size-bounded and skip FIFOs; `validate --path` output sanitized;
  `git_fetch` pins `--upload-pack` and the pager.
- [ ] Residual: a repository-local `credential.helper` still runs during
  `git_fetch` (resetting it would also clear the user's global helper); no
  product caller uses `git_fetch` yet.
- [x] v2 bug review (subagent, each finding verified): Ctrl+S save guard,
  dialog Escape/Tab trap after a click, stale-response guards for refresh and
  skill history, history reload after changes, Test connection keeps unsaved
  AI settings, visible plurals.
- [x] v2 follow-ups: "Compare with" shows the copy being compared; a failed
  re-read is announced on every page; a new import clears the old result; the
  command palette does nothing while busy.
- [x] AI Center: buttons stay disabled until every overlapping request ends
  (an in-flight counter; the old boolean re-enabled paid calls early).
- [x] Merged PR #23 (list request 29–49% faster, response unchanged) after
  reviewing the path-safety shortcuts against `realpath` semantics.
- [x] Docs audit (subagent, each finding re-verified): README data-root fix,
  localhost guidance, doctor drift recipe; CLI surface signatures for `create`,
  `trash restore`, `templates new`; `--scope` help lists `commandcode`.
- [/] Parallel sessions: CI full suite on macOS/Windows + e2e (`ci-portability`),
  all-scope list performance (`list-perf`); each lands as a PR for review.

Open for the maintainer:

- [x] Issue #14 F-2: `localhost:<port>` is accepted as a Host alias for a loopback bind (maintainer approved 2026-11-19).
- [ ] ADR-001 revisit: loopback is reachable by every local OS user, and
  `POST /api/install {"run": true}` executes the npm runner; a per-user token
  file (0600) would close that without a remote attack surface.
- [ ] `.specs/` (40 MB evidence) and history purge: keep, move, or rewrite history?
- [ ] `GET /api/skills?scope=all` sends ~4.8 MB for ~2,100 records; `portable_frontmatter`
  (17%) is read by neither UI. Trim it from list rows, or add an opt-in field set?
- [ ] Card `aria-label`s fail axe's experimental label-content-name-mismatch
  (weight 0); decide whether accessible names should mirror visible card text.

## Remaining gated and deferred entries

The 13 open entries include 12 pending and one in progress, with
historical overlaps. The full dated context remains in the archive.
One human visual sign-off
entry is retained verbatim in the parity section below and remains part of this
queue; the other twelve entries follow.

- [ ] Owner's call: choose the next release version and candidate after 1.0.2.
  Product questions Q1–Q4 remain in docs/45 §7.

- [/] Broader fidelity study with distractors, near misses, repeats and the
  product's configured HTTP transport; the two-case result does not validate it.
  HTTP portion completed 2026-11-17: DeepSeek V4.1 Flash via GOAT matched
  36/36 authored labels, using four skills, 12 prompts and three repeats.
  An offline OpenCode probe confirmed how to observe a successful skill load.
  An attended same-model comparison remains open for the permitted models.
  See @docs/48-ai-http-study-2026-11-17.md.

- [ ] Human spoken screen-reader sign-off using the docs/32 walkthrough.

- [ ] Human perceptual review and screen-reader validation of v2. Automated
  forced-colors, keyboard and actual 200%/400% browser-zoom results are recorded separately.

- [ ] Deferred (docs/35): per-project profiles that translate one toggle into each agent's
  native setting (⚠); Codex's switch is user-level only and must say so.

- [ ] Deferred (docs/35): interoperate with Microsoft APM `apm.yml` instead of
  a new lockfile. Presence checks for the manifest and resolved lock are
  implemented in the existing hygiene report. Interoperability still needs
  decisions about supported fields, validation and export.

- [ ] Deferred (docs/35): Hermes-Curator-style stale → archive with pin/restore/dry-run (⚠).

- [ ] Deferred (docs/35): transcript-based usage counts (⚠) and project skill lockfile (⚠).

- [ ] Owner's call, deferred (docs/35): docs/27 monetization questions MON-Q1…MON-Q5 (services-first year; widen scope to MCP + AGENTS.md; public top-skills report; zh-CN UI; which docs/14 tiers stay). Proposals only, nothing approved.

- [ ] **Human perceptual review of the redesign. Not an agent's to do.**
  The automated browser checks and Orca diagnostic evidence are recorded in
  @docs/06-progress-log.md and @docs/32-continuation-verification-2026-11-06.md.
  Human visual and spoken screen-reader sign-off remain open.

- [ ] Capture dated external screenshots and run real consented participant sessions; this repository records the protocol only.

- [ ] Run five consent-safe human usability sessions; automated work does not
  fabricate participant evidence.

## Earlier completed batch (2026-11-17)

Commit `5ada04a` completed static completion/typo suggestions, per-consumer
discovery evidence, scan degradation, AI simulation wording and unknown Codex
metadata. Its receipt is in @docs/06-progress-log.md. Earlier completed tasks
remain in the archive, rather than being counted again here.

## Historical sections retained for relative links

**[NOTE]** The following sections remain verbatim because moving them would
change the meaning of their relative Markdown links. Their completed steps
are historical; the queue above is authoritative.

## V2 feature parity and default interface (2026-11-06)

- [x] Audit classic and v2; create the [source-backed design and inventory](docs/superpowers/specs/2026-11-06-v2-feature-parity-design.md).
- [x] Use UI/UX Craft, Design Taste Frontend, Better Accessibility and Frontend
  UI Engineering; inspect three archived Inspo captures. Preserve v2's existing
  warm-paper/serif design. Luna/Terra provided scoped implementation and review.
- [x] Build the approved [demo-only mockups](https://github.com/udayvarmora07/skills-manager/blob/515f5be/prototype-v2-parity/README.md), then
  follow the user's expanded instruction to integrate production workflows.
- [x] Integrate Install, Profiles, Templates, Quality, Workspaces, Settings,
  source updates/snapshots, scoped history, full-archive modes, exact-instance
  batch actions, logical tags and rich create/edit into v2.
- [x] Add contained stored-template reads and explicit PATCH field clearing;
  preserve unknown/omitted metadata on ordinary edits. No schema, public Store
  API, application CLI or runtime dependency change.
- [x] Promote `/` and `/index.html` to `/v2/`; retain `/classic/` and query/hash
  behavior. Update classic browser harnesses for the explicit compatibility URL.
- [x] Fix review-discovered stale folder approval, mixed-copy description,
  omitted-metadata overwrite and independent read-state races; add regressions.
- [x] Verify real API/filesystem flows in private HOME/data fixtures, both
  themes, phone/tablet/desktop, keyboard dialogs and retry/error states.
- [x] Finish the final current-tree ladder: 1,386 unittest cases on Python 3.12,
  34 v2 browser scenarios, 38 classic scenarios / 318 assertions, both smokes,
  viewport harness, static/security/design/docs gates and pinned packaging.
  Evidence is in the [implementation plan](docs/superpowers/plans/2026-11-06-v2-feature-parity.md).
- [x] Design pass on the tool pages: Tools becomes a primary tab, duplicate
  header search removed, every tool page rebuilt on v2 components with worded
  status and humanized values; 34/34 v2 browser scenarios and 1,386 tests pass.
- [x] Commit and integrate the combined parity + design work: `61355a2` is on
  `origin/main` (verified 2026-11-06).
- [ ] Human visual sign-off of the redesigned tool pages.

Agent-scope in-app trash restore now uses the existing scope-aware trash API
and the v2 Recovery card (2026-11-07; see docs/35).
Live registry fetch/commit and actual external runner execution are not exercised
by this task's browser checks. Human screen-reader and spoken usability sign-off
remain unclaimed. The work landed on `main` as `61355a2`.

## External skill scanner — SkillSpector (planned 2026-11-06)

Plan: [external skill scanner](docs/superpowers/plans/2026-11-06-external-skill-scanner.md).
The maintainer chose both phases, hook first.

- [x] Decide D-A and D-B: show SkillSpector's score labelled as its own claim;
  accept OSV egress with a stated warning (maintainer, 2026-11-06). D-C
  (Quality integration) stays deferred.
- [x] Phase A: `skillsmgr/external_scan.py`, wired into registry fetch and
  source-update reviews; `--external-scan`/`--external-scan-llm`, REST
  `external_scan`, v2 Settings + review panels. LLM mode is bring-your-own-key
  from the server/CLI environment only. 19 tests incl. an optional real-tool
  test; real v2.12.0 output verified through the hook.
- [x] Installed SkillSpector under `~/.local/share/uv/tools` was group-writable
  (umask 002). Group write removed from `~/.local/share/uv`, `.../tools` and the
  `skillspector` tree (2026-11-07); `trusted_executable` now accepts it and the
  optional real-tool test runs instead of skipping. Policy unchanged.
- [x] CI `unit (py3.10)` red on `main` at `61355a2`: `/` answered 308, which
  3.10's urllib does not follow. Default-interface redirect is now 307; slash
  canonicalization stays 308; regression test added (2026-11-07).
- [x] Pre-existing test leak (2026-11-07): `WebAppServer` left its Store bound
  in the `scopes` ContextVar, so a later in-process `cli.main` resolved `global`
  through a stale Store. `cli.main` now binds its own Store per command and
  restores the prior binding. `tests/test_cli_store_binding.py`.
- [x] AI features (BYOK): D-AI-1…D-AI-7 answered and A0–A10 shipped on
  2026-11-09; see the top section and @docs/39-ai-features-research-and-catalogue-2026-11-09.md.
- [x] Phase B: stdlib rewrites of SC2/SC3/PE3/AR/RA2/SC8/P9/TR/AST checks in
  `insights.risk_scan()` — nine checks, `tests/test_risk_scan_phase_b.py`,
  2026-11-07.
- [x] Phase B noise measured on the maintainer's real library (1,764
  instances): high `credential-path` findings fell 192 → 18 after the
  mention-vs-access fix; numbers in the external-scanner plan. Independent
  review fixes (severity-downgrade bypass, hostile-AST crashes) and the
  production wiring of files/description into `risk_scan` landed 2026-11-07.

Current implementation evidence is recorded in @docs/06-progress-log.md.
