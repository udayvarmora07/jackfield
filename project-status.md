# Skills Manager UI (Jackfield) — Project status

## Path
Not yet confirmed by the maintainer. The files show the design path run through `/uxui-workflow`
(requirements → UX discovery → UI → design system → screens), plus a handoff package and a
partial build. Proposed on 2026-11-27: design path + build → UX review → launch.

## Skipped steps
| Step | Skipped on | Why |
|---|---|---|
| 11 Native app | 2026-11-27 (inferred) | A local web UI, not a phone app |

Steps 1 (brainstorm) and 4 (journey map) were never run; not yet recorded as skipped.

## Notes
- Agent tracking was built onto the shipped UI (option A, "fit shipped UI"), commit 78cc21b,
  2026-11-26. The main redesign's look is not built yet: `styles.css` still uses the old bone
  ground `#f2f3f1` and teal `#0d6a63`.
- The design system and the approved screens live on claude.ai (design system v13, canvas v58).
  The approved screens are exported to `designs/final/` (light and dark, 25 each). There is
  still no `design-system.md` or `design-tokens.css` in the root; the older copies are in
  `handoff/4-design-system/`.
- `redesign/ui-v2` is a separate, older restyle branch. Never merge it unasked.
- The Jackfield rename is committed (`75c1bb6`, CI green). Since 2026-11-27 the approved
  screens and the design system use the Jackfield name and logo. The briefs, `ui-progress.md`'s
  title and the handoff package still say "Skills Manager".
- 2026-11-27 UI gap check: every inventoried screen was drawn, but four S2 side-panel states and
  the first-launch scan were missing. Both are now designed and approved (round 6, B · Two
  camps, picked by the maintainer).
- 2026-11-27 local run: 15 of 2,508 tests fail on this checkout (CI green). Cause: project
  scopes read `Path.cwd()`, and the untracked project skills in `.agents/skills` and
  `.claude/skills` leak into "all scopes" tests. A test-isolation gap, not a product bug.
  Fixed later on 2026-11-27: the suite treats the checkout as an empty project
  (`tests/test_00_portable_environment.py`); 2,509 tests pass locally.

## Last check
2026-11-27 (third check) · Steps 5–7 complete again (UI gaps closed, design system v13) ·
Step 8 Build in progress (agent tracking done, main redesign look not started). Recommended:
settle handoff open question 4 (DESIGN.md vs design-system tokens), then `/build` for the main
redesign from `designs/final/`. The handoff package is out of date.
