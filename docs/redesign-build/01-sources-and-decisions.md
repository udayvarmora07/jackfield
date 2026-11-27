# Sources and Decisions

**Version 1.0.0**

**AI manifest**: Which design records are current, which are stale, the
decisions the redesign has already made (with their source), and the build
decisions this spec makes on top. Read before any redesign work. Open
questions that still need the maintainer are in
@docs/redesign-build/09-open-questions-and-risks.md.

## Current records (checked 2026-11-27)

**[SPEC]** These are current and agree with each other:

| Record | Version | Notes |
|---|---|---|
| Design system artifact | v13, `lastChange` 2026-11-27 | Renamed to Jackfield; adds statuses Version 1, Version 2, Unknown, Working; SidePanel states Evenly split, Unknown, Working, Failed; Jackfield lockup in Navigation. Its `tokens.json` still says `"name": "Skills Manager"` (a label only; values are current) |
| Canvas artifact | v58 | 50 approved boards: A01–A16 / D01–D16 and ATA-01…09 / ATD-01…09 |
| `designs/final/` | = canvas v58 | Byte-identical (sha256 of A01, A15, A16, ATA-01, ATA-05, D01, ATD-09 compared 2026-11-27) |
| `ux-brief.md`, `design-brief.md`, `requirements.md` | 2026-11-24 + Agent tracking 2026-11-26 | Use the Jackfield name. `design-brief.md` still cites DS v11 for tracking; v13 supersedes it |
| `ui-progress.md` | Round 6 done | Title still says "Skills Manager" |
| `branding/jackfield/kit/` | Committed (`8ba0bc8`) | Logo files and `GUIDELINES.md` |

## Stale records

**[SPEC]** Do not build from these where they disagree with the records above:

- `handoff/` (packaged 2026-11-26): says DS v11, 14 screens, "Skills Manager",
  "Agent tracking not designed", "no marks for Cursor, Gemini, Command Code".
  All five are out of date. Its `4-design-system/tokens.json` matches v13
  colour values but lacks the v12–v13 components (ListGrid, TablePreview, Sheet,
  Placeholder, the new statuses). Its `decisions.md` (45 rows) is still the best
  history of *why*.
- `DESIGN.md` (repository root, tracked): the old look (cool bone ground, teal
  signal, `ok` green). It is the contract `check_design_tokens.py` enforces
  today. Phase 0 rewrites both (@docs/redesign-build/02-design-system.md).
- `redesign/ui-v2` branch: an older restyle of the **classic** UI. Never merge
  it; nothing in this build comes from it.

## Decisions already made (do not reopen)

**[SPEC]** From the redesign record (`handoff/decisions.md` rows, `ui-progress.md`
and the DS README):

| Topic | Decision |
|---|---|
| Concept | Hybrid "one table of truth" + global search + one quiet Needs attention count |
| Direction | B · Paper, variation C · Fine print with A's attention banner |
| Navigation | Exactly four places: Skills, Needs attention, Trash & backups, Advanced. New tools go under Advanced |
| Colour | C0 "Today" tuned: warm-neutral greys, **one blue accent** (`#2D58D0` light / `#8CAEFF` dark); `warn` and `bad` are states only |
| Type | IBM Plex Sans for everything people read; Plex Mono only for paths, keycaps and exact file content; skill names are sans 600 |
| Fonts | Bundled woff2, never Google Fonts (the boards load Google Fonts only because they run on the canvas) |
| Icons | Inline SVG, 2px stroke, `currentColor`; never a text character as an icon; keycaps stay text |
| Agent marks | One colour (`ink-2`) via CSS mask; Claude Code, OpenCode, Cursor, Gemini use their own simple-icons logos; Codex a neutral terminal; Command Code a neutral command glyph; Shared folder a folder; This project code brackets; custom agents a dashed square |
| S3 Skill page | B · Row on top + C's File text switch and sticky Edit bar |
| S4 Editor | A · Save-to card |
| S5 New skill | B · Live preview; places chosen with vertical checkbox rows |
| S7 Needs attention | B · List and detail |
| Side-panel states | Round 6 "B · Two camps" for Evenly split |
| Agent tracking | One "What to track" page (S14) with doorways from the table; backend contract signed off 2026-11-26 and **already built** (`tracking.py`, `/api/tracking*`) |
| Class names | System names (`sm-*`), never the artboard-local names (`tick`, `seg`, `choice`, `chk`, `cell k-on`) |

## Build decisions this spec makes

**[SPEC]** Each is the simplest option that keeps the locked rules. Change one
only by updating this table.

| # | Decision | Chosen | Why |
|---|---|---|---|
| BD-1 | Migration strategy | **Strangler inside the one app**: new shell and tokens first, then screen by screen, each phase merged to `main` green | One interface at `/` is a locked behaviour (2026-11-23); a long-lived branch would collide with every other change |
| BD-2 | Old look | Phase 0 aliases every old CSS custom property to a new token, so the whole app switches palette in one commit and old screens look "new-ish" until rebuilt | Meets "the old look must go in one change" (open question 4 of the handoff) without a big-bang rewrite |
| BD-3 | Routing | Keep **hash routes**; new paths `#/skills`, `#/skills/<name>`, `#/skills/<name>/edit`, `#/skills/<name>/why`, `#/new`, `#/attention`, `#/trash`, `#/advanced[/<tool>]`, `#/settings[/tracking…]`; old hashes redirect | The server serves only `/`; history-API paths would need new server routes. The boards' `/skills/<name>` breadcrumb maps to `#/skills/<name>` |
| BD-4 | Component files | Plain scripts, **flat in `skillsmgr/webui/`**, each registering Vue components with string templates (`ui-*.js` for components, `screen-*.js` for screens) | No build step; `pyproject.toml` ships `webui/*` one level deep and `check_package_data.py` fails on deeper files |
| BD-5 | Token pipeline | Copy DS `tokens.json` to `design/tokens.json`; a stdlib script `tools/gen_tokens.py` writes `skillsmgr/webui/tokens.css`; both committed; a test fails if they drift | Generated-and-committed is not a build step (same model as the vendored Vue) |
| BD-6 | Component CSS | Copy DS `components/bundle.css` to `skillsmgr/webui/system.css`, unchanged except agent-mark data URIs checked; page layout in a new `layout.css`; `styles.css` and `tools.css` shrink to zero by phase 7 | The bundle is the approved implementation of every component |
| BD-7 | Undo | Reuse today's client Undo (toast with an inverse action, `app.js` `toast()`), restyled as the UndoBar | Already correct, tested and backend-neutral |
| BD-8 | Status truth | One pure function `squareStatus(copy, row, agent)` in `model.js` derives every square word from API data, unit-tested in isolation | Status correctness is the product promise; one place to test it |
| BD-9 | Sync map and Inbox | Their jobs move into S1 (Different, Make match) and S7; routes redirect | IA decision 19 |
| BD-10 | Advanced tool pages | Every existing tool keeps its id and backend calls; only its page shell changes to the S10 template | "Nothing lost" and no backend churn |
