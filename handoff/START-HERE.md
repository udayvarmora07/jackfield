# START HERE: Skills Manager UI redesign handoff

This folder holds the complete design record of the Skills Manager web UI redesign, packaged on 2026-11-26. It is written for an AI assistant or a teammate who opens the folder cold. A person can open `index.html` for the same story as one page.

## What the project is

Skills Manager (`skillsmgr`) is a Python CLI with a local web UI for managing the skills of AI coding agents: Claude Code, Codex, OpenCode, Cursor, Gemini, Command Code, the shared `~/.agents` folder and per-project folders. The web UI runs with `python3 -m skillsmgr webui`. It has a stdlib Python backend and a vendored Vue 3 frontend with no build step, binds to 127.0.0.1 and works offline.

A full test on 2026-11-24 found about 100 problems in the existing UI: statuses that are wrong or hidden, risky actions without a preview, one job spread over many pages, engineer language, and a plain admin-panel look. This redesign fixes trust and clarity first, then the look.

**Status:** requirements, UX and UI are done and approved. That means 14 screens in light and dark, and design system version 11. **The build has not started.** Audience for this package: a developer who will build it, and the maintainer (the only founder) coming back later.

**The solution in one line:** "one table of truth". Skills are rows, agents are columns, and each square says in one plain word whether that agent has the skill, whether it is on, and whether it is the same copy. Added to that: one global search (`/`, Ctrl+K) and one quiet "Needs attention" count with a fixer that handles one problem at a time.

## Which file answers which question

| Question | File |
|---|---|
| What problem, for whom, what's in and out of scope, which assumptions are signed off? | `1-idea-and-requirements/requirements.md` |
| Which concepts were considered and why the hybrid won; the flows F1–F9; the IA; the screen inventory S1–S13 with every state | `2-ux/ux-brief.md` |
| A short, self-contained brief for the UI, including the square states S1/S2 must cover | `2-ux/design-brief.md` |
| How each screen was chosen (rounds 1–5), and the colour, type and icon reviews with their measurements | `3-ui/ui-progress.md` |
| What the approved screens look like | `3-ui/screens/light/A01–A14*.png`, `3-ui/screens/dark/D01–D14*.png` |
| Clicking through the screens | `3-ui/prototype/index.html` (offline; `.dc.html` files rendered by `support.js`, the canvas runtime) |
| What the losing options looked like | `3-ui/exploration/*.png` (rounds R1/R2/R5, Winner, Phone, States, colour C0–C5, type T0–T3, T-Review) |
| Colours, type sizes, spacing, radii, shadows, control sizes | `4-design-system/tokens.json` (source of truth); `tokens.css` is generated from it |
| How a component looks and behaves; voice; status vocabulary; icon rules; accessibility | `4-design-system/README.md`, `4-design-system/components/*/README.md`, `components/bundle.css` |
| Every decision, with the options and the reason | `decisions.md` (45 rows, oldest first) |
| What is still undecided, and who decides | `open-questions.md` (11 items, most important first) |
| Where the code is, how to run and test it, which rules the build must keep | `5-build-and-launch/BUILD-NOTES.md` |

## Rules any future work must follow

**Locked technical rules** (from the repository's `AGENTS.md`; ask the maintainer before deviating):
1. The filesystem is the source of truth. SQLite is a rebuildable index, never trusted over the files.
2. The SQLite schema and `SCHEMA_VERSION` stay unchanged.
3. The CLI stays stdlib-only.
4. Web UI: stdlib backend, no build step, no new runtime dependencies, Vue vendored in the repository, binds 127.0.0.1 by default.
5. No new CLI commands or Store methods without approval.

**From the design:**
- **Fonts:** IBM Plex Sans for everything people read, IBM Plex Mono only for paths, keycaps and exact file content.
  - Bundle them as package data (`skillsmgr/webui/static/fonts/`), never Google Fonts.
  - Ship the SIL OFL licence with them.
  - `check_package_data.py` and the packaging rules in `AGENTS.md` (SEC-8, SEC-13) apply.
- **Agent marks:** one colour (`ink-2`), decorative, always beside the place name.
  - Claude Code and OpenCode: their own logos from simple-icons 16.36.0.
  - Codex: a neutral terminal icon (decided; `decisions.md` row 45).
  - Shared folder: a folder icon. This project: code brackets.
  - Never brand colours: Claude's orange reads as the Different warning.
- **Status vocabulary:** every status is a mark plus a word (On, Off, Off in settings, Different, Can't read, Not here). Colour is never the only signal. When the app can't verify something, it says "unknown" and never borrows the On mark.
- **One signal colour:** the blue `accent`. `warn` and `bad` are states, not decoration. No gradients, glows, emoji or left-border cards.
- **Voice:** short, plain and specific. Say what happened, to which skill, in which agent, and what to do next. No raw error codes, regular expressions or internal scope ids in the main text.
- **Choosing places** is always vertical checkbox rows (Editor "Save to", New skill "Add it to").
- **Navigation** has exactly four places: Skills, Needs attention, Trash & backups, Advanced. New tools go under Advanced.
- **Use the system class names** (`sm-*`), not the artboard-local names (`tick`, `seg`, `choice`, `chk`).

**UX principles:**
1. Tell the truth, or say "unknown".
2. Show before you change, offer Undo after.
3. One place for each thing.
4. Plain words first, details on request.
5. Calm by default.

**Won't have this version:** accounts, sync between computers, cloud hosting or remote access; languages other than English; new CLI commands, Store methods or database changes without approval; a build step or new runtime dependencies; a dedicated clean-up helper; detailed Profiles and Templates screens beyond the tool-page template. Don't invent features beyond the brief.

**Order of work:** bugs first (wrong status, silent overwrite, broken tools, off-screen errors), then the four everyday jobs (find and read; turn on/off per agent; copy or sync; create or edit), then all other pages.

## What's open (top five; all 11 are in `open-questions.md`)

1. **A page to choose which agents to track**, which users can update later. This is a new request from the maintainer on 2026-11-26 and is not designed. It needs requirements, UX and UI first, and possibly Store or config changes, which need approval.
2. **Marks and table columns for Cursor, Gemini and Command Code.** Only 5 places are designed.
3. **States described in the brief but not drawn:** square states Evenly split, Unknown, working and failed; the first-launch scanning step; an unreadable skill page; 1,000 rows.
4. **The product still has the old look.** `styles.css` and `DESIGN.md` use a teal accent and a cool ground. `check_design_tokens.py` binds them together, so they must change in one go.
5. **Font packaging is partly done.** The woff2 files are already shipped and checked. The OFL licence text and the Mono latin-ext loading are missing.

## Where things live outside this folder

- **Code:** the repository one level up (`skillsmgr/webapp.py`, `skillsmgr/webui/`). Web UI docs are in `docs/08-web-ui.md`.
- **Canvas** (private, version 36): https://claude.ai/artifact/2bRpEoQ192WY2Tp7dYsXdq. The approved row is at y 14080, dark at y 15980, colour at y 17900/19800, type at y 21800.
- **Design system** (private, version 11): https://claude.ai/artifact/27HHwcNGwDAZ2cne6xW4ei
- **Originals** of the four briefs are in the repository root. They are uncommitted, and this folder holds copies.

If the project files change, make a fresh package rather than editing this one.
