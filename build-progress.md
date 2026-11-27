# Jackfield — Build progress

## Setup

The local Python server serves the existing Vue interface in
`skillsmgr/webui/`. Phase 0 uses the approved v13 export and canvas v58.
The token generator uses Python's standard library. Its CSS is checked in,
and the app loads fonts, styles and icons from local files.

## Phases

- [x] Phase 0 · Foundations integrated on `main` as `c3087ec`. All 17
  [GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/45982680566) passed.
- [x] Phase 1 · Shell implemented and verified in the local checkout.
- [ ] Phase 1 · Integrate and verify GitHub CI.
- [ ] Phase 2 · Skills table and side panel (hero).
- [ ] Phases 3–8 · Remaining screens, migration cleanup and acceptance.

## Findings checked in Phase 0

| Finding | Status |
| --- | --- |
| Turned off filter misses skills with a mix of enabled and disabled copies | The filter now checks a skill's copies, including the selected agent when filtered. The skill's overall status is unchanged. |
| Contradiction check misses “Always use tabs” versus “Always use spaces” | The deterministic scanner now recognises those bare directives alongside explicit indentation rules. |
| History card says no changes after an agent-scope save | The card displays library history. Agent-scope saves create snapshots. Explain and surface the correct source on the Phase 3 Skill page. |
| AI Settings says Connected after a refused connection | The legacy badge reads whether a provider is configured. Phase 5 Settings must distinguish configuration from a successful check. |

The component stylesheet comes from the approved 30,447-byte export
(SHA-256 `7d5905e50046893960685ad25170f920c5fb6d3e0d9be710bb9c611c39923296`).
The local copy references the canonical ink token in its agent-mask rule.
Existing nav and page layouts remain in use during Phase 0.

Browser checks run in an empty project folder inside the fixture home. The
checkout's installed project skills would otherwise change counts, search
matches and the targets offered by Add to agent.

## Phase 1 · Shell

The four-place desktop and phone navigation, legacy redirects, search and
command palette, and Not found screen use the existing local app. Skills
views still links to Agents overview and the Sync map. Phase 2 replaces
their existing content and workflows with the Skills table and side panel.

The search and Not found checks use synthetic skill names and counts. The
palette currently opens over the existing Skills shelf. Its background will
use the new table when Phase 2 lands. The preview uses the shipped Python
and Vue stack.

The browser versions of search and Not found were inspected at 390, 1280,
1440 and 1920 px in both themes. Desktop captures were compared with
A13/D13 and A14/D14. The 390 px checks used Chromium's viewport controls and
the phone navigation was compared with A02/D02.

| Detail | Implementation decision |
| --- | --- |
| Search row icons and selected row | Use the app's existing glyphs for Phase 1 and give the keyboard selection an outline. |
| Missing skill navigation and copy | Keep Skills marked current for a missing skill. Use the actual checked locations and the closest visible skill. |
| Phone header | Keep the theme control in the header. Users can create a skill from the Skills page or the palette. |

The Python 3.11–3.14 suites and the focused route, copy and script-order
contracts passed. Chromium passed 74 end-to-end scenarios. The separate
browser smoke passed six viewports and four scan scenarios. The Store and web
smokes, HTTP contracts, lint, design tokens, documentation, complexity and
clean wheel and source distribution installs passed.

The integration review also checked Back and Cancel on new-skill drafts,
late stored template responses, query-only changes on tracking forms, and
retrying the first read of a directly opened editor.

## Verification of Phase 0

- Python 3.11–3.14 ran 2,511 tests each, with the platform-dependent skips.
- Chromium passed all 71 browser checks with the isolated fixture, including
  the responsive and theme sweeps. The desktop and phone-width previews
  showed the approved palette, lockup and agent marks.
- Store and web smoke tests passed. The documentation, token generation,
  contrast and complexity checks passed.
- The wheel and source distribution passed the package-data and clean-install
  checks using the pinned build toolchain.
