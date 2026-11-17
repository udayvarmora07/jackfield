# Task Checklist — Skills Manager

**Version 0.10.0**

**AI manifest**: Live work and the remaining gated/deferred queue. `[ ]` means
pending, `[/]` in progress, `[x]` completed. Historical milestones, including
older duplicates of this queue, are archived at
@docs/archive/task-history-through-2026-11-17.md. Archive checkboxes are dated
records, not additional live work.

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

## Remaining gated and deferred entries

These are the original 15 live entries: 12 pending and 3 in progress, with
historical overlaps. This continuation does not turn them into approved scope.
The full dated context remains in the archive. One human visual sign-off
entry is retained verbatim in the parity section below and remains part of this
queue; the other fourteen entries follow.

- [ ] Owner's call: release 1.1.0 (PyPI still serves 1.0.1) and questions
  Q1–Q4 in docs/45 §7.

- [/] Broader fidelity study with distractors, near misses, repeats and the
  product's configured HTTP transport; the two-case result does not validate it.
  HTTP portion completed 2026-11-17: DeepSeek V4.1 Flash via GOAT matched
  36/36 authored labels, using four skills, 12 prompts and three repeats.
  Native comparison remains unavailable for the permitted models in the
  existing harness; see @docs/48-ai-http-study-2026-11-17.md.

- [ ] Human spoken screen-reader sign-off using the docs/32 walkthrough.

- [ ] Human perceptual review and screen-reader validation of v2. Automated
  forced-colors, keyboard and actual 200%/400% browser-zoom results are recorded separately.

- [ ] Deferred (docs/35): per-project profiles that translate one toggle into each agent's
  native setting (⚠); Codex's switch is user-level only and must say so.

- [ ] Deferred (docs/35): interoperate with Microsoft APM `apm.yml` instead of a new lockfile.

- [ ] Deferred (docs/35): Hermes-Curator-style stale → archive with pin/restore/dry-run (⚠).

- [ ] Deferred (docs/35): transcript-based usage counts (⚠) and project skill lockfile (⚠).

- [ ] Owner's call, deferred (docs/35): docs/27 monetization questions MON-Q1…MON-Q5 (services-first year; widen scope to MCP + AGENTS.md; public top-skills report; zh-CN UI; which docs/14 tiers stay). Proposals only, nothing approved.

- [ ] **Human perceptual review of the redesign. Not an agent's to do.**
  The harness renders and measures; it does not sign off. Still unexercised:
  a non-Chromium engine, forced-colors mode, 200%/400% zoom, and a screen
  reader. This is the same open gate G8 carried, carried forward honestly.

- [/] Publish 1.0.2 — **TestPyPI SHIPPED; PyPI is `waiting` on the maintainer's
  `release`-environment approval.** `v1.0.2` is pushed at `ef9bfd6`; CI is
  16/16 green. The external outage that blocked this has cleared: the failing
  call was `audience retrieval` against
  `https://test.pypi.org/_/oidc/audience`, which answered 503 on 2026-10-06
  morning and answers **200** now (three samples, with `/simple/`, `/legacy/`
  and `/pypi/<name>/json` all 200). Re-running the failed job was the whole fix,
  exactly as recorded. `publish to TestPyPI` **succeeded**; `publish to PyPI` is
  `waiting` on the `release` environment, whose required reviewer is
  `udayvarmora07` — it cannot and did not proceed unattended. Not worked around
  by publishing straight to PyPI: the TestPyPI stage is the gate, and skipping it
  is the failure mode SEC-7 exists to prevent.

- [/] T2: Prepare the metadata-corrected package release; publish only after
  exact candidate review and maintainer approval. **Preparation is complete** —
  the 1.0.2 artifacts are built from `522b81f` and independently verified (see the
  artifact item above). Only the publish step remains, and it is human-gated.

- [ ] Capture dated external screenshots and run real consented participant sessions; this repository records the protocol only.

- [ ] Run five consent-safe human usability sessions; automated work does not
  fabricate participant evidence.

## Last delivered batch

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
- [x] Build the approved [demo-only mockups](prototype-v2-parity/README.md), then
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
