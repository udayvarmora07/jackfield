# Jackfield — Build progress

## Setup

The local Python server serves the existing Vue interface in
`skillsmgr/webui/`. Phase 0 uses the approved v13 export and canvas v58.
The token generator uses Python's standard library. Its CSS is checked in,
and the app loads fonts, styles and icons from local files.

## Design references

- [Claude design system v13, shadows](https://claude.ai/artifact/27HHwcNGwDAZ2cne6xW4ei#shadows)
- [Claude UI and UX canvas v58](https://claude.ai/artifact/2bRpEoQ192WY2Tp7dYsXdq#page-dcb81aee8d83)

The checked-in `design/tokens.json` and `designs/final/` are the corresponding
local references. The Claude session records confirm canvas v58. They record a
later design-system publication numbered v14, titled “v13 · Jackfield name
and Logos”, that adds branding material. The local build still uses the
approved v13 tokens. The regular Chrome profile loaded the four live artifact
links after the initial access errors. The design system's Shadows values
match the checked-in tokens. The canvas fragment exposes the artboard list and
prototype controls. The browser accessibility view exposed the Skills table
states prototype's title and controls, with its inner screen content still
unavailable through that view.

[Naming research](https://claude.ai/artifact/Aag9hffBrvbZhQpmgSGPnB) and
[the brand kit](https://claude.ai/artifact/C2DFx7Tp3SNYUEmawBgm3G) explain the
Jackfield name and mark. Their project sources are in `branding/jackfield/`.

## Phases

- [x] Phase 0 · Foundations integrated on `main` as `c3087ec`. All 17
  [GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/45982680566) passed.
- [x] Phase 1 · Shell integrated on `main` as `72401c7`. All 17
  [GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/45997716936) passed.
- [x] Phase 2 · Skills table and side panel integrated on `main` as `78cfedd`.
  All 17 [GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/46011057550)
  passed on that commit. The four-artifact review corrections are recorded
  in [the progress log](docs/06-progress-log.md).
- [x] Phase 3 · The Skill page, Editor, New skill and diagnosis landed on
  `main` as `614bc4b`. All 17
  [GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/46056334181) passed.
- [x] Phase 4 · Needs attention and Trash & backups are approved, landed at `382364b`, and passed all 17 [GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/46113385797).
- [ ] Phases 5–8 · Remaining screens, migration cleanup and acceptance.

## Paper review fixes

The first review batch restores the A16 welcome card and shared disclosure
chevrons. Classic view bookmarks open the Paper Skills table with their
filters. The Skill page handles same-name copy selection using folder paths.
Doctor explains its count scope, Why leads with problems in existing copies,
and route changes clear stale reviews and success feedback. The application
still offers Undo after an automatic post-write redirect when the original
view is no longer available. See [the review](docs/62-redesign-review-2026-11-28.md).

## Phase 3 · Everyday jobs

| Screen | Behavior |
| --- | --- |
| Skill page | Uses the same squares and reviewed changes as the Skills table. File text retains the selected copy and checks its UTF-8 bytes against the observed hash. History identifies library events and separately reports saved snapshots for the selected place. |
| Editor | Different and missing copies start unticked. Save checks existing file hashes and stages edited trees for missing places. Undo uses checked snapshots for existing copies and checks the whole tree before moving a new copy to Trash. |
| New skill | Shows three starting layouts and stored templates. The preview and real create serialize through the same code. A partial result keeps confirmed files and shows the uncertain destinations. Existing AI authoring and metadata are available from the form. |
| Why isn’t it running? | Shows the first failed check in place order and distinguishes files, observed settings and runtime. Runtime loading remains Unknown. The original prompt and trace tools are under AI maintenance. |

The Skill page reads both views from the selected folder’s current document,
including when the library index is stale or a recursive scope holds several
copies with the same name. Details lists supporting files and counts lines
in readable text within the scan limits. The Claude Code size estimate uses
the selected personal copy and observed user settings.

The Editor can now save to a missing writable place. It keeps the selected
source’s supporting files and publishes the edited document with the folder.
An occupied destination is refused even if it appears during publication.
The verification uses the existing checked tree limits, including regular
files only, up to 256 entries, 4 MiB per file and 16 MiB total. The diagnostics
page offers the confirmed Claude settings path for copying. It uses a recheck
and a plain explanation when the exact settings path is unavailable.

Opened all four screens with synthetic data at 1440 and 390 pixels in light
and dark themes. The browser checks cover search to File text, exact creation
in two folders, partial creation, an external edit arriving before a write,
snapshot Undo, and a settings change followed by a diagnosis recheck.

The Skill page Details update passed 98 headless Chromium checks, including
two exact copies in one scope and filename changes after toggle and Undo.
The full Python 3.12 suite ran 2,538 tests with 13 platform-dependent skips.
The new reader and Claude listing contracts passed on Python 3.11–3.14.
Store and web smoke tests, browser smoke, four HTTP contracts, and clean
wheel and source distribution installs passed again.

The updated Editor was compared with A05 and D05 at 390, 1280, 1440 and
1920 px in both themes. Its missing-place choice and selection message
follow the boards. The application includes the actual folder labels,
formatter controls, metadata and AI editing. At phone width it uses the
shared bottom navigation and sticky Save header.

Chromium passed all 100 end-to-end checks, including saving to a missing
place, preserving supporting files, and Undo after an independent edit.
Python 3.11–3.14 each ran 2,544 tests successfully, with 12–13
platform-dependent skips.
Store and web smoke, HTTP contracts, browser smoke and clean package
installs passed.

Before the Skill page Details update, Python 3.11–3.14 each ran 2,531 tests
with 12–13 platform-dependent skips. Chromium passed 96 end-to-end checks and
a separate first-run creation case.
Store and web smoke tests, the browser smoke, four HTTP contracts, Ruff, the
documentation and token checks, and clean wheel and source distribution
installs passed. Bandit passed on the modified Python modules. The full scan
reported a low-severity finding in the existing seeded bootstrap calculation.
The preceding Phase 3 commit `6ee6641` passed all 17
[GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/46051136005).
The maintainer approved the updated Editor on 2026-11-28. It landed on
`main` and passed hosted CI. A physical phone check remains pending.

## Phase 4 · Needs attention

The maintainer approved this screen on 2026-11-28.

The navigation badge and To fix group count individual issues in the tracked
places. Skipped issues remain available in the review. Fix previews the
selected version, exact destinations and on/off changes. Jackfield moves
replaced folders to Trash and records Fixed after re-reading the copies.
Undo checks the installed tree before restoring the prior folder. Unreadable
binary files and ambiguous folders keep manual guidance.

Compared the implemented screen with A08 and D08 at 390, 1280, 1440 and
1920 px in both themes. The build uses observed folder names and document
excerpts in the choices. It shows the checked comparison and affected paths
after selecting a version. At phone width it uses the shared bottom tabs and
stacks the list and detail. The real-phone check remains part of acceptance.

The local Python 3.11–3.14 suites each ran 2,544 tests successfully, with
12–13 platform-dependent skips. All 101 headless Chromium checks passed,
including F7, exact folder Undo, and the responsive checks. The wheel and
source distribution passed clean-install checks.

## Phase 4 · Trash & backups

The maintainer delegated the scope and restore-conflict decisions. Restore
uses a unified list for library and agent copies and re-reads the exact
restored folder. Older agent copies without an origin record go to the
place's usual skill folder. An occupied destination leaves the live and saved
copies in place. The archive controls and Empty library trash are scoped
to the library. Backup preview shows additions, replacements and skips.
Load rechecks the reviewed archive bytes, options and destinations. An
addition cannot replace a folder that appears during the load. The last
download start and size are stored in the browser after handoff. Recent
changes shows library history and the separate disclosure keeps text
snapshot recovery available.

The A09/D09 comparison uses synthetic entries in both themes at 390, 1280,
1440 and 1920 pixels. It uses Jackfield's existing bottom navigation at
phone widths. Physical phone testing remains part of the acceptance work.

Local verification completed on Linux. The 2,557-test suite passed on Python
3.11–3.14 with platform-specific skips. All 103 Chromium checks passed,
including F7 and F8. Headed Chrome passed at 200% and 400% zoom. Store and Web
smoke tests, HTTP contracts, the classic browser harness, and clean wheel and
source distribution installs also passed. The maintainer approved the screen
and continued to Phase 4 integration. Phase 4 landed at `382364b` and all 17
[GitHub CI jobs](https://github.com/udayvarmora07/jackfield/actions/runs/46113385797)
passed.

## Phase 5 · Advanced

The maintainer approved the Advanced tool mapping (Q2). The directory
keeps the 21 existing tools and adds Doctor and a What to track link.
The Add skills switch controls Update from folder. Doctor lives under
Check my setup and uses Jackfield's existing hygiene report.

The desktop directory uses two columns when all four groups are visible,
keeping Settings alongside the expanded AI list. The visual comparison
uses browser widths of 390, 1280, 1440 and 1920 pixels in both themes.
Physical phone testing is part of the later acceptance work.

S9 passed the 2,557-test suite on Python 3.11–3.14 with platform-specific
skips, all 104 Chromium checks, and headed Chrome zoom at 200% and 400%.
The classic browser harness also passed with synthetic inventory failures.
Store and Web smoke tests, HTTP contracts, and clean wheel and source
distribution installs passed. Advanced is ready for the maintainer's review.

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
contracts passed. Chromium passed 78 end-to-end scenarios. The separate
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

## Review against the design references

### Phase 0 foundations

The shipped foundation uses the v13 light and dark token values and the local
IBM Plex font files. The two desktop shadow presets use the approved offsets
and theme-specific colours. The mobile Skills sheet in Phase 2 uses the
upward shadow shown on ATA-02 and ATD-02.

### Phase 1 shell

The shipped navigation, palette and Not found screen were checked against
A02/D02, A13/D13 and A14/D14. The review found that choosing “Did you mean”
removed the active button without moving keyboard focus back to the palette
input. The current local build restores focus to the input.

### Phase 2 Skills table and side panel

The implementation was compared with ATA-01 and ATD-01 on desktop, ATA-02
and ATD-02 at phone width, and the state guidance in A03/D03 and A15/D15.
The comparison caught long folder paths stretching the agent headers,
missing focus after closing the phone sheet and clutter above the phone list.
The headers now truncate on one line, the narrow list shows one agent at
a time, and the sheet is modal. Phone filter, sort and refresh controls open
under “Filter and sort”. The desktop toolbar keeps “Refresh files” visible.
Screenshots contain synthetic counts and folder names.

The default Skills route shows the table. The old shelf, Agents overview and
Sync map still have compatibility URLs. Exact instances remains reachable
from the table for disambiguating physical copies. The Needs attention page
retains its existing workflow until Phase 4.

Replacement previews expose the complete returned instruction text and wait
for the source to load. A refused replacement returns to review on retry.
Batch selection uses the existing 500-target limit with a visible message if
the selection exceeds it.

The safety review caught non-forced Sync replacing a populated folder that
appeared during staging. The copy now refuses a populated destination that
appears during publication. Batch evidence includes file and directory
permissions. A checked replacement uses a precise Trash entry for the former
folder, and Undo stops when it sees later changes to the replacement. The
filesystem checks cannot serialize unrelated processes writing to the same
directory.

Chromium captures cover 390, 1280, 1440 and 1920 px in both themes. The phone
sheet restores focus to the selected square. Manual checks in
`agent-browser` verified that a failed source read blocks replacement and
that a single Undo restores the earlier state of two copied skills. The
JavaScript model checks covered 0, 1 and 10,000 skills. A physical phone and
a screen reader were outside this local pass.

Python 3.11–3.14 each ran 2,526 tests successfully, with platform-dependent
skips. All 87 Chromium scenarios passed, including the Codex-only toggle and
Undo in both themes by keyboard and mouse, the 1,000-skill table and the
refused replacement retry. Store and web smokes, the separate browser harness,
HTTP contracts, static, design-token and documentation checks, and clean wheel
and source distribution installs passed.
