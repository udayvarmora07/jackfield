# Skills Manager design system

The look and language of Skills Manager: a calm, plain-spoken table of truth for the skills of every AI coding agent on one computer. Built from the approved Skills table (phase 3, round 3, 2026-11-24).

## Who it is for, and how it should feel

Developers who use two to four AI coding agents and keep 50–200 skills, visiting for a quick answer in the middle of coding work.

- **Personality:** calm, clear, trustworthy.
- **Never:** scary to click, a cluttered admin panel, full of engineer words, toy-like.
- **References:** Linear, Vercel, Obsidian, Notion, Raycast, GitHub — restraint, crisp type, one accent, generous white space.

## Principles

1. **Tell the truth, or say "unknown".** No `accent` On mark unless the app checked it. Every status names its agent.
2. **Show before you change, offer Undo after.** Every action that touches another agent's files shows a Now → After preview (Pill) and ends in the Undo bar.
3. **One place for each thing.** One search, one attention banner, one trash, one name per idea.
4. **Plain words first, details on request.** Paths, sizes and codes live in `path` mono text or behind "Details".
5. **Calm by default.** Only one colour signals (`accent`); warnings use `warn` once, in the attention banner and on the squares that need it.

## Voice

Short, plain, specific. Say what happened, to which skill, in which agent, and what to do next.

| Write | Not |
|---|---|
| Codex has a different copy of code-review. | Document differs from the reference in scope codex. |
| Turned off code-review in Codex. Undo | Operation completed successfully. |
| Couldn't reach your AI service. Check the address in AI settings. | [Errno 111] Connection refused |
| Uses about 3% of Claude's skill list space. | ~9,373 characters of ~40,000 listing budget |
| No skills match this filter. Clear filters | 0 results |

Sentence case everywhere. Buttons start with a verb and name the agent when one is involved: "Turn off in Codex", "Add to OpenCode".

## Status vocabulary

The heart of the system. Each status is a **mark + word**; colour is never the only signal, and the marks differ in shape as well as colour.

| Status | Mark | Word | Text colour | When |
|---|---|---|---|---|
| On | filled dot, `accent` | On | `ink` | The file is there, readable, switched on, and its settings allow it. |
| Off | ring, `mark-faint` | Off | `mute` | The file is switched off by Skills Manager. |
| Off in settings | dashed ring, `mute` | Off in settings | `mute` | The file is on, but the agent's own settings turn it off. Never shown as On. |
| Different | diamond, `warn-mark` | Different | `warn` | This agent's copy differs from the others. |
| Can't read | cross, `bad` | Can't read | `bad` | The file is damaged or not readable text. |
| Not here | dash, `mark-faint` | Not here | `text-faint` | The agent has no copy. Clicking offers "Add to …". |

When the app cannot verify something (for example whether an agent really loads a skill), say "unknown" in words; never borrow the On mark. In step-by-step checks (ChecksGrid) Unknown has its own mark: a dashed ring with "?".

## Colour

One neutral ramp (`bg` → `surface` → `raise`, `line`, `line-subtle`; `ink` → `ink-2` → `mute` → `text-faint`), one signal (`accent` with `on-accent` and `accent-soft`), and two state families used sparingly (`warn*` for differences, `bad*` for unreadable files). The Undo bar is the one inverted surface (`toast`, `on-toast`).

- `mark-faint` is for shapes only; the lowest grey for text is `text-faint`.
- Every text pair meets 4.5:1 in both themes; warn and bad differ in lightness, not only hue.
- Dark mode is a first-class theme, not an inversion: use the tokens, never hard-coded hex.

## Typography

IBM Plex Sans for everything people read (`--font-sans`), IBM Plex Mono only for folder paths, keycaps and exact file content (`--font-mono`): the editor, the File text view, code blocks and diff lines. Both are one open-source superfamily (SIL OFL), so paths sit naturally beside words. Chosen on 2026-11-25 over Inter (the AI-slop audit's one finding), Atkinson Hyperlegible and Recursive. It is clear at 12–14px, I/l/1 and O/0 look different, it is about 5% narrower than Inter, and it has been IBM Carbon's interface font at these sizes since 2017. Skill names are **sans at 600**, not mono. Weights in use: 400, 500, 600 (headings), 700 only where a page needs it; never below 400 under 18px. Tabular numbers on (`font-variant-numeric: tabular-nums`; Plex's digits are tabular by default). Styles: `title-page` 30, `title-panel` 22, `title-doc` 19, `title-banner` 17, `body-lg` 15, `doc` 15/25.5, `body` 14, `ui` 14/500, `cell` 13/500, `caption` 12/600, `file-text` 13 mono, `path` 11.5 mono, `keycap` 11 mono. Every page has one `title-page` title, including the editor ("Editing test-driven-development"). The app runs offline, so it bundles the woff2 files (OFL allows it) instead of loading Google Fonts.

## Layout

- **Desktop (1280–1920):** header (60px) → title row → attention banner (only if anything needs attention) → filter toolbar → table (flexible) + side panel (`panel`, 392px, pinned while scrolling), gap `space-6`. Page margins `space-10`.
- **Table:** skill column (name 14/600, description 13 `mute`, verdict 12/500) then one column per agent with a monogram (`ag`) and path. Rows and squares are at least `square` (64px). Long lists load in steps ("Show 50 more").
- **Phone (390):** one agent at a time ("Showing: Codex ▾"), rows show that agent's status, tapping opens a bottom sheet with the same panel content, and a bottom tab bar. Everything tappable is at least `touch` (44px).
- **Other pages:** the same header on every page; a breadcrumb above the title on pages below Skills or Advanced ("Skills / test-driven-development / Edit"); the title row holds the page's one main action. Long pages keep the title row with its main action pinned while scrolling (skill page, editor). Reading width stays under about 760px.
- **Button heights:** page-level actions in a title row or page footer are `control-page` (38px, `sm-btn--page`); buttons inside cards, panels, rows and toolbars are `control` (36px); the side panel's main action is `control-lg` (46px). Phones: at least `touch`.

## Iconography

Thin stroke icons (2px, round joins), drawn inline, `currentColor`, 13–20px. Never a text character standing in for an icon (no ✓, ✕, ×, ▾); keyboard keys in keycaps stay as text. The logo is a 3×3 grid of rounded squares with the centre square in `accent`. No emoji, no illustrations.

**Where icons go.** Icons are used only where they speed recognition:
- **Chrome:** search, theme, help, close, chevron, the tab bar.
- **States:** tick and cross in checks; a warning triangle on the attention banner; alert, tick and info on connection status.
- **Standard actions**, left of the label at 15px: download, upload (choose a file), restore, refresh (check again, re-read), copy, test the connection (plug), and the bin for Move to Trash / Empty trash.
- **Files:** file, file-text and file-code in file lists.
- **Choices:** sun, moon and monitor for the theme; file, ordered list and checklist for the New skill templates.

Everyday verbs (Turn off, Compare, Save, Create, Cancel, Skip) stay text-only, and so do the desktop navigation and section headings. Icons on everything is noise.

**Agent marks.** Each place has a mark, one colour (`ink-2`), so the table stays calm. Use a 20px tile (`sm-ag`) beside a place name in tables, lists, panel headers and save-to lists, and a bare 14px mark (`agm`) inside chips, pills and history lines. Set `data-a` to the code (`CX`) or the place name (`Codex`). Marks are decorative (`aria-hidden`) because the name always sits beside them. Every list that names places shows marks, except running sentences. Marks are never in brand colour: Claude's orange is ΔE 8 from the Different diamond and would read as a warning.

| Place | `data-a` | Mark |
|---|---|---|
| Claude Code | `CC` | Claude's own logo (simple-icons) |
| Codex | `CX` | A neutral terminal icon. OpenAI asked icon libraries to remove its logo, so it is not shipped without a decision. |
| OpenCode | `OC` | OpenCode's own logo (simple-icons) |
| Shared folder | `SH` | A folder |
| This project | `PJ` | Code brackets |

The logos are their owners' trademarks, used only to name each tool. Check each brand's guidelines before release. The two-letter monogram stays in the markup as the fallback text.

## Components

Button · Field · Keycap · StatusMark · Square · AttentionBanner · SidePanel · UndoBar · Navigation, plus five added from the approved screens on 2026-11-25: Segmented (Read / File text), Chip (short filter-like choices), Document (rendered skill and exact file text), ChecksGrid (why isn't it running, with Unknown) and Compare (Now / Suggested, choose a version). Button gained Accent, Quiet and the page size; Field gained labels, hints, multi-line text, checkboxes and live rules. Classes live in `components/bundle.css` (`sm-*`), reading only `tokens.css` custom properties. Wrap a page in `.sm-root`.

## Accessibility

- WCAG 2.2 AA. Every button, link and field shows a 2px `accent` focus ring.
- Squares are real `<button>`s with an `aria-label` like "code-review in Codex: On".
- Never colour alone: every status has its word.
- Touch targets 44px on phones; desktop controls 34–38px (see Button heights).
- Dialogs that guard unsaved work ("Leave without saving?") make the safe choice the accent button ("Keep editing").
- The Undo bar uses `role="status"` so screen readers announce it.

## Don'ts

- No gradients, glows, left-border cards or emoji.
- No second accent colour; `warn` and `bad` are states, not decoration.
- No raw error codes, regular expressions or internal scope ids in the main text.
- Don't show a green or blue "On" or "Connected" unless it was checked.
