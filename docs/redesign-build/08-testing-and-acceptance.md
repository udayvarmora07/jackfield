# Testing and Acceptance

**Version 1.0.0**

**AI manifest**: How the redesign is proven: the existing tests that must move
with the markup, the new tests, the e2e scenarios and benchmarks, visual and
accessibility checks, performance budgets and the per-screen definition of
done. The ladder itself (3.11–3.14, smokes, gates, CI) is in `AGENTS.md`.

## The ladder for every redesign commit

**[SPEC]**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

Run it on Python 3.11, 3.12, 3.13 and 3.14 (uv-managed interpreters on the
maintainer's machine), then `python3 smoke_web.py` (and `smoke_store.py` if the
store changed), `python3 check_design_tokens.py`, `python3 check_docs.py`,
`python3 check_complexity.py`, `python3 check_package_data.py` (with built
artifacts before a release), the CI ruff gate at its pinned version, and the
browser runner:

```bash
NODE_PATH=tools/e2e_deps/node_modules python3 tools/e2e_v2/run.py --output-dir <private dir>
```

**[NOTE]** Since 2026-11-27 the suite treats the checkout as an empty project
(`tests/test_00_portable_environment.py`), so locally installed project skills
no longer change results.

## Existing tests that read the frontend

**[SPEC]** These 12 files assert today's markup, scripts or styles. Each is
rewritten in the commit that changes what it reads; the assertion's *intent*
(the behaviour or safety rule it pins) must survive in the new form.

| File | Tests | Phase that rewrites it |
|---|---|---|
| `tests/test_v2_interface_contracts.py` | 71 | 1–5, per screen (largest) |
| `tests/test_frontend_seam_contracts.py` | 13 | 1 (load order, `domain.js` first, globals) |
| `tests/test_webui_contracts.py` | 11 | 1 |
| `tests/test_redesign_contracts.py` | 11 | 0 (tokens, fonts) |
| `tests/test_package_data.py` | 18 | 0, 7 (shipped member set) |
| `tests/test_audit_batch4_contracts.py` | 32 | where it reads UI files |
| `tests/test_agent_scope_trash.py` | 20 | 4 (trash UI parts only) |
| `tests/test_g8_ui_structure_contracts.py` | 2 | 1 |
| `tests/test_document_baseline.py` | 5 | 3 |
| `tests/test_ai_local_ui.py`, `tests/test_ai_preview_inputs.py` | 1 + 1 | 5 (AI "What will be sent" must stay) |
| `tests/test_performance_frontend.py` | 1 | 2 (budgets below) |

## New tests

**[SPEC]**

| Test | Proves | Phase |
|---|---|---|
| `tests/test_css_token_references.py` | Every `var(--x)` resolves to a declared token; no hex outside `tokens.css`; no `alias:` lines after phase 7 | 0 |
| `tests/test_tokens_generated.py` | `tokens.css` equals `tools/gen_tokens.py` output for `design/tokens.json` | 0 |
| `tests/test_square_status_cases.py` + `tests/fixtures/square-status-cases.json` | The case table covers every status key and every precedence pair (off + different, settings + unreadable, split + off, …) | 2 |
| `tests/test_routes_contract.py` | Every route and legacy redirect in @docs/redesign-build/04-frontend-architecture.md is handled by `router.js` (parsed table vs source) | 1 |
| `tests/test_copy_rules.py` | No internal scope ids, `[Errno`, `Traceback` or regex fragments in static UI strings; every button label starts with a verb (allow-list for nouns like "Details") | 1, then each phase |
| `tests/test_tool_inventory.py` | Every tool id in `model.js` `toolGroups` has an S9 placement and an S10 route | 5 |

## Browser e2e scenarios (`tools/e2e_v2`)

**[SPEC]** Add one scenario per flow; each runs in light and dark and at 1440
and 390 wide, keyboard-only where marked.

| Scenario | Flow | Pass condition |
|---|---|---|
| B1 turn off for one agent (keyboard) | F2 | `code-review` found and turned off in Codex only; square shows Off only after the disk changed; Undo restores On |
| B2 stop tracking Cursor | T1 | Confirm names what leaves and "Nothing on disk changes"; column gone; Undo brings it back; files untouched (hash before = after) |
| B3 add Kilo at `~/.kilo/skills` | T3 | Live checks reject a missing folder and a folder outside home; preview "Kilo · N skills found"; column appears |
| F1 find and read | F1 | `/` → type → Enter opens S3; File text equals the file bytes |
| F3 add here / make match / evenly split | F3 | Previews shown; replaced copies appear in Trash; nothing preselected on split |
| F4 create | F4 | Preview equals created files in each chosen place |
| F5 edit | F5 | Different-copy place unticked by default; reload keeps the editor; leave guard |
| F6 why | F6 | First failing check matches the fixture; Actually loaded is Unknown |
| F7 needs attention | F7 | Count matches; fix + Undo; empty state |
| F8 changed on disk | F8 | Fixture edits a file while the page is open → notice → Refresh marks the row |
| F9 first launch | F9 | Scanning → summary → tip, once |
| S-status | — | `model.js` `squareStatus` passes every case in the JSON table inside the page |
| P-1000 | — | 1,000-skill fixture: table interactive under 1.5 s; Show 50 more works; filter responds under 100 ms |

## Visual check against the boards

**[SPEC]** No pixel-diff dependency is added. For each screen:

1. Render the board offline: copy the board from `designs/final/<theme>/` next
   to `handoff/3-ui/prototype/support.js` (the canvas runtime, with local
   fonts) in a private temp folder and open it in the runner's Chrome. On a
   clean checkout, get `support.js` from the approved Claude canvas export or
   the maintainer's handoff. Keep the exported runtime outside version control.
2. Open the same screen in the product with the matching fixture.
3. Screenshot both at 1440 × 900 (also 1280, 1920 and 390) in light and dark,
   and review side by side: layout, hierarchy, spacing rhythm, copy, states.
   Record differences as accepted (with a reason) or as fixes.

**[NOTE]** The boards use fixed sample data (142 skills, 5 places); build the
e2e fixture to match it (`code-review`, `debugging-and-error-recovery`,
`security-review`, `test-driven-development`, `git-workflow`, …) so the two
render the same rows.

## Accessibility

**[SPEC]** WCAG 2.2 AA in both themes:

- Contrast: from `check_design_tokens.py` (re-derived from tokens).
- Keyboard: every flow above completes keyboard-only; focus is always visible;
  overlays return focus to their opener; the grid follows the APG data-grid
  model (one tab stop, roving tabindex, arrow keys).
- Names and roles: squares `aria-label="<skill> in <agent>: <word>"`; marks
  `aria-hidden`; Undo bar `role="status"`; sheets and confirms `role="dialog"`
  with a labelled heading; numbers in ListGrid have hidden words.
- Colour never alone: every status has its word; the gate test asserts each
  status class renders a text node.
- Reduced motion: the Working ring stops turning; no other motion is required.
- Screen reader spot check: Orca on Linux for F2 and T1 (as in earlier release
  evidence).

## Performance budgets

**[SPEC]** Measured by the runner on CI hardware. At 1,000 skills, the table
becomes interactive within 1.5 s and the palette and filter update within
100 ms after a keystroke. A local square toggle round-trip takes at most
300 ms. Placeholders resolve without layout shift. The browser suite times the 1,000-record listing,
filter and palette with a deterministic response, and the real toggle from
the confirmation click through the refreshed square.

## Definition of done for one screen

**[SPEC]** A screen is done when:

1. It matches its light and dark boards (visual check recorded).
2. Its acceptance list in @docs/redesign-build/05-screens.md passes, with the
   e2e scenario for its flow.
3. Every state on its board exists and is reachable by a fixture.
4. It is keyboard-complete and passes the accessibility list above.
5. It works at 390 px or hands off to its phone layout.
6. The contract tests that read it are rewritten and green on 3.11–3.14.
7. No new token, no hex, no undeclared `var()`, no internal ids in copy.
8. `task.md` and the progress log record it; the hostile self-review ran on the
   diff.
