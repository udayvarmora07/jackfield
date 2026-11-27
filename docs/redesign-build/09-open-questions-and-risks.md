# Open Questions and Risks

**Version 1.0.0**

**AI manifest**: Questions the redesign build still needs answered, each with a
recommended answer, its owner and the phase it blocks; and the main risks with
their mitigations. Until a question is answered, build the recommended option
in a way that is cheap to change. Settled decisions are in
@docs/redesign-build/01-sources-and-decisions.md; do not reopen them here.

## Open questions

**[?]** Answer each in this table (keep the question, add the decision and date).

| # | Question | Recommended | Owner | Blocks |
|---|---|---|---|---|
| Q1 | Cursor and custom agents have no settings reader. May their squares say **On**, or must they say **Unknown** (principle 1: no On unless checked)? | **On**, with the side panel's details saying "Cursor's own settings aren't checked", and "Settings allow it" as Unknown in S6. Unknown on every Cursor square would make a whole column grey and train people to ignore Unknown | Maintainer | Phase 2 (one constant) |
| Q2 | The approved Advanced board shows 11 tool rows; the app has 21 tool ids (`model.js` `toolGroups`), and the board's "Doctor" is not one of them. Is the placement in @docs/redesign-build/05-screens.md (S9 table) right, and do the extra AI tools appear as rows or under their sub-label (Write, Test, Shorten, Find conflicts)? | The S9 mapping, with each sub-label as a small heading and its tools as rows, so nothing is lost and the board's four AI labels stay | Maintainer | Phase 5 |
| Q3 | `DESIGN.md`: rewrite it from v13, or retire it and let the gate read `design/tokens.json` only? | **Both**: the gate reads `design/tokens.json` (one source of values); `DESIGN.md` is rewritten as the short human and agent guide (voice, statuses, rules) with no colour values of its own | Maintainer | Phase 0 |
| Q4 | Should "Off in settings" count in Needs attention? A01 counts 3 (Different + Can't read only), while A08's empty state says it also checks settings | Not counted; listed as checked in the empty state (matches the hero board) | Maintainer | Phase 2 |
| Q5 | Backups "Last one: 20 Nov": the app does not record backup downloads | Store the last download time in the browser (per browser); omit the line when unknown | Developer | Phase 4 |
| Q6 | Brand guidelines for the Claude, OpenCode, Cursor and Gemini logos (simple-icons) before release | Check each brand's terms; fall back to neutral marks for any that refuse | Maintainer | Release |
| Q7 | The DS artifact's `tokens.json` says `"name": "Skills Manager"` and the index `namespace` is `SkillsManager` | Rename both in the DS artifact; the repo copy uses "Jackfield" from the start | Maintainer (DS owner) | None |
| Q8 | `requirements.md`, `ui-progress.md` and `designs/final/` are untracked, but this spec cites them as sources. The repository is **public** | Commit `requirements.md`, `ui-progress.md` and `designs/final/` (2.2 MB) so the build's sources are versioned; keep `handoff/` (29 MB with a zip) out of git. A scan on 2026-11-27 found no emails, but ATA-07/08 and ATD-07/08 hard-code a sample home path containing the maintainer's first name in their scripts; change it to `/home/you/` first if that should not be public | Maintainer | Phase 0 (before the first screen) |
| Q9 | The handoff package is stale (DS v11, "Skills Manager", 14 screens) | Regenerate it with `/handoff-package` after phase 2, not now | Maintainer | None |
| Q10 | Phone cut-over width | 600px (DS fixes only 900 for Sheet and 640 for ListGrid) | Developer | Phase 6 |
| Q11 | "Fix all…" batch on Needs attention (option C) | Not in this build; revisit after real use | Maintainer | None |

## Risks

**[SPEC]**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A square shows On when it is not (the product promise breaks) | Medium | High | One `squareStatus` function, a shared case table run in the browser, precedence pairs tested, confirm-on-disk before any new word |
| The 92 KB in-DOM template and 124 KB `app.js` rewrite collides with other work | High | High | Strangler phases (BD-1), one owner for shared files, phases merged green to `main`, no long-lived branch |
| 12 contract test files (≈ 186 tests) break as markup moves; the temptation is to delete them | High | Medium | Rewrite each assertion's intent in the same commit (rule 3 of the build plan); never skip a test to get green |
| Undeclared CSS tokens render transparent and pass every gate | Medium | Medium | `tests/test_css_token_references.py` in phase 0 (memory: css-token-reference-blind-spot) |
| An AI tool loses its "What will be sent" step while moving into the S10 shell | Medium | High | `test_ai_preview_inputs.py` and `test_ai_local_ui.py` kept; S10 makes step 2 mandatory for AI tools |
| Copy drifts from the approved boards (engineer words come back) | Medium | Medium | `tests/test_copy_rules.py`; quote board copy verbatim; visual check per screen |
| Performance regresses with 8 columns × 1,000 rows | Low | Medium | 50-row paging, no per-square watchers, P-1000 e2e budget |
| Complexity ratchet blocks big template computeds | Medium | Low | Small computed properties per row and square; never raise the budget |
| Design and code diverge after launch (two sources of truth) | Medium | Medium | Tokens only from `design/tokens.json`; DS artifact changes come back through phase-0's pipeline, never by hand-editing `tokens.css` |
| Brand use of third-party logos | Low | Medium | Q6 before release; neutral fallbacks already designed |
