# Design System v13 in the Product

**Version 1.0.0**

**AI manifest**: Every token value of the approved design system v13, how the
tokens reach the product (pipeline, files, gates), fonts, icons, agent marks,
the logo, the status vocabulary and voice. Values are copied from the DS
artifact's `project/tokens.json` and `README.md` on 2026-11-27. Component
anatomy is in @docs/redesign-build/03-components.md.

## Files the build adds or replaces

**[SPEC]**

| File | Role | Source |
|---|---|---|
| `design/tokens.json` | Token source of truth in the repo (not shipped) | DS artifact `project/tokens.json`, `name` changed to `"Jackfield"` |
| `tools/gen_tokens.py` | Stdlib script: `tokens.json` → `tokens.css` | New |
| `skillsmgr/webui/tokens.css` | Generated custom properties, light on `:root`, dark on `[data-theme="dark"]`, and the `@font-face` rules | Generated, committed, line 1 `/* Jackfield — generated from design/tokens.json; do not edit */` |
| `skillsmgr/webui/system.css` | The `sm-*` component classes | DS artifact `project/components/bundle.css` (30,447 bytes, sha256 `7d5905e5…`) |
| `skillsmgr/webui/layout.css` | Page grid, header, title rows, page widths, breakpoints | New, reads tokens only |
| `skillsmgr/webui/static/fonts/OFL-IBM-Plex.txt` | SIL OFL 1.1 licence | `handoff/3-ui/prototype/fonts/OFL-IBM-Plex.txt` |
| `skillsmgr/webui/logo.svg` | Favicon | `branding/jackfield/kit/svg/jackfield-favicon.svg` (already wired in `8ba0bc8`; verify) |
| `DESIGN.md` | Rewritten as a short guide (voice, statuses, rules, where values live) with **no colour values** (Q3, decided 2026-11-27) | Phase 0 |
| `check_design_tokens.py` | Reads `design/tokens.json` (the only source of values) + `tokens.css`, not `DESIGN.md` | Phase 0 |

**[SPEC]** Load order in `index.html`: `tokens.css` → `system.css` →
`layout.css` → (until phase 7) `styles.css`, `tools.css`. Wrap the app root in
`.sm-root`.

## Colour tokens (light / dark)

**[SPEC]** Every text pair meets 4.5:1 in both themes (DS claim; re-measured by
the gate). `mark-faint` is for shapes only.

| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | `#F6F6F3` | `#121211` | Page ground |
| `surface` | `#FFFFFF` | `#1A1A19` | Table, panel, buttons, inputs |
| `raise` | `#F5F5F3` | `#222220` | Row/square hover, monogram fill, placeholders |
| `line` | `#ECECE9` | `#2C2C2A` | Card and control borders, header rule (never the only sign of a control) |
| `line-subtle` | `#F3F3F1` | `#242422` | Row and column dividers in the table |
| `ink` | `#191917` | `#EDEDEA` | Primary text; fill of the dark button |
| `ink-2` | `#3B3B37` | `#CFCFCA` | Body sentences; agent marks |
| `mute` | `#666660` | `#B0B0A9` | Descriptions, counts, captions, Off words |
| `text-faint` | `#6E6E67` | `#9A9A93` | Paths, Not here; lowest grey allowed for text |
| `mark-faint` | `#9A9A93` | `#77776F` | Off ring, Not here dash. **Never text** |
| `accent` | `#2D58D0` | `#8CAEFF` | The one signal: primary action, On mark, links, focus ring, selected square |
| `on-accent` | `#FFFFFF` | `#0C1430` | Text on accent |
| `accent-soft` | `#EDF1FC` | `#1C2540` | Selected square, pressed toggle, tip and refresh banners |
| `warn` | `#8A4700` | `#F2B866` | Different text, attention banner title |
| `warn-mark` | `#C06A00` | `#F2A33C` | Different / Version diamonds only |
| `warn-soft` | `#FFF7EC` | `#241B10` | Attention banner ground; `is-camp` squares |
| `warn-line` | `#F1DDC0` | `#4A3517` | Attention banner border |
| `bad` | `#A3261A` | `#FF9C8F` | Can't read mark and word; failed titles |
| `bad-soft` | `#FDEEEC` | `#2E1714` | Ground behind a Can't read block |
| `toast` | `#191917` | `#EDEDEA` | Undo bar ground (the one inverted surface) |
| `on-toast` | `#FAFAF9` | `#121211` | Undo bar text |

## Type

**[SPEC]** Families: `--font-sans: "IBM Plex Sans", system-ui, -apple-system,
"Segoe UI", sans-serif`; `--font-mono: "IBM Plex Mono", ui-monospace, "SF Mono",
Menlo, monospace`. Tabular numbers on. Weights 400/500/600, 700 only where a
page needs it; never below 400 under 18px.

| Style | Size / line | Weight | Tracking | Use |
|---|---|---|---|---|
| `title-page` | 30 / 33 | 600 | −0.02em | One per page, including the editor ("Editing test-driven-development") |
| `title-panel` | 22 / 26 | 600 | −0.015em | Skill name at the top of the side panel and sheets |
| `title-doc` | 19 / 25 | 600 | −0.01em | Section headings inside a rendered skill |
| `title-banner` | 17 / 24 | 600 | −0.01em | Attention banner, card titles, empty-state headline |
| `body-lg` | 15 / 23 | 400 | — | Side-panel sentences |
| `doc` | 15 / 25.5 | 400 | — | Rendered skill body |
| `body` | 14 / 21 | 400 | — | Default text |
| `ui` | 14 / 20 | 500 | — | Buttons, navigation; skill names in rows at 600 |
| `cell` | 13 / 16 | 500 | — | The word in a square |
| `caption` | 12 / 16 | 600 | 0.02em | Column headers, section labels; row verdicts at 500 |
| `path` (mono) | 11.5 / 16 | 400 | −0.01em | Folder paths only |
| `keycap` (mono) | 11 / 11 | 500 | — | Keyboard hints, monogram fallback |
| `file-text` (mono) | 13 / 21 | 400 | — | Editor, File text view, code blocks, diff lines |

**[SPEC]** Fonts already shipped in `skillsmgr/webui/static/fonts/`: Plex Sans
variable (latin, latin-ext) and Plex Mono 400/500/600 (latin, latin-ext). Phase
0 adds the OFL licence file and `@font-face` rules for the Mono **latin-ext**
files (shipped but never loaded today). `check_package_data.py` must keep
asserting both, and the new licence file, with `unicode-range` on every face.

## Spacing, radius, shadow, size

**[SPEC]**

| Spacing | Value | Use |
|---|---|---|
| `space-1` | 4px | Keycap pair gap, icon nudge |
| `space-2` | 8px | Toolbar gaps, mark to word |
| `space-3` | 12px | Row block padding |
| `space-4` | 16px | Square side padding; phone gutter |
| `space-5` | 20px | Row side padding; gap between sections |
| `space-6` | 24px | Side panel padding; table-to-panel gap |
| `space-8` | 32px | Header gaps |
| `space-10` | 40px | Desktop page margins |

| Radius | Value | Use |
|---|---|---|
| `radius-xs` | 5px | Keycaps, agent tiles |
| `radius-sm` | 9px | Buttons, inputs |
| `radius-md` | 11px | Side-panel primary button |
| `radius-lg` | 14px | Table frame, attention banner |
| `radius-xl` | 16px | Side panel, cards; phone sheet top corners (18px there) |
| `radius-pill` | 999px | Now/After pills, counts |

| Shadow | Light | Dark | Use |
|---|---|---|---|
| `shadow-panel` | `0 1px 2px rgba(25,25,23,.04), 0 10px 28px rgba(25,25,23,.07)` | `0 1px 2px rgba(0,0,0,.3), 0 10px 28px rgba(0,0,0,.35)` | Side panel only |
| `shadow-toast` | `0 12px 32px rgba(0,0,0,.22)` | same | Undo bar, phone sheet |

| Size | Value | Use |
|---|---|---|
| `control` | 36px | Buttons and inputs in cards, panels, rows, toolbars |
| `control-page` | 38px | Page-level actions (title row, page footer) |
| `control-lg` | 46px | Side-panel primary button |
| `touch` | 44px | Minimum tappable size on phones |
| `square` | 64px | Minimum table row and square height |
| `panel` | 392px | Side panel maximum width |

## Artboard names → system tokens

**[SPEC]** The boards declare local custom properties. Never copy them; map
them:

| Board | System | | Board | System |
|---|---|---|---|---|
| `--acc` | `accent` | | `--line2` | `line-subtle` |
| `--acc-ink` | `on-accent` | | `--faint` | `mark-faint` |
| `--acc-soft` | `accent-soft` | | `--faint-text` | `text-faint` |
| `--ink2` | `ink-2` | | `--warn-mk` | `warn-mark` |
| `--toast-ink` | `on-toast` | | `--shadow` | `shadow-panel` |
| `.theme-dark` | `[data-theme="dark"]` | | class `tick`, `seg`, `choice`, `chk`, `cell k-*` | `sm-rule`, `sm-seg`, `sm-choice`, `sm-chk`, `sm-square` + `sm-status is-*` |

## Old tokens → new tokens (phase 0 alias layer)

**[SPEC]** Phase 0 keeps the old custom-property names alive as aliases, so the
unrebuilt screens switch palette in the same commit (BD-2). The exact old names
are read from `styles.css` at the start of phase 0; the mapping rule is:

| Old meaning (DESIGN.md) | New token |
|---|---|
| `ground` | `bg` |
| `surface` | `surface` |
| `sunken` | `raise` |
| `ink`, `ink-2`, `muted` | `ink`, `ink-2`, `mute` |
| `signal` (teal) | `accent` |
| `ok` / `ok-bg` (green) | `accent` / `accent-soft` (there is no green in v13: On is blue) |
| `warn*` | `warn`, `warn-soft`, `warn-line` |
| danger / error | `bad`, `bad-soft` |

**[SPEC]** Every alias line carries a `/* alias: remove in phase 7 */`
comment; phase 7 deletes them and the gate fails if any remain.

## Icons

**[SPEC]** Thin stroke icons, 2px, round joins, inline SVG, `currentColor`,
13–20px. `app.js` already has a `PATHS` table and an `<ic>` component; keep the
mechanism, align the set to the DS list:

- **Chrome:** search, theme (sun / moon / monitor), help, close, chevron, tab bar.
- **States:** tick and cross in checks; warning triangle on the attention
  banner; alert, tick and info on connection status.
- **Standard actions** (15px, left of the label): download, upload, restore,
  refresh, copy, plug (test the connection), bin (Move to Trash, Empty trash).
- **Files:** file, file-text, file-code. **Choices:** template icons blank,
  ordered list, checklist.
- Everyday verbs (Turn off, Compare, Save, Create, Cancel, Skip), desktop
  navigation and headings stay text-only. Remove icons the DS does not list
  (`home`, `map`, `inbox`, `tools` in `PATHS` go with the old navigation).

## Agent marks

**[SPEC]** One colour (`ink-2`), drawn by CSS mask from data URIs in
`system.css` (`span.sm-ag[data-a]` 20px tile, `span.agm[data-a]` 14px bare
mark). Decorative (`aria-hidden="true"`); the place name always sits beside
them; the two-letter monogram stays as fallback text.

| Place | `data-a` | Mark | Source |
|---|---|---|---|
| Claude Code | `CC` | Claude logo | simple-icons 16.36.0 |
| Codex | `CX` | Neutral terminal | Drawn (OpenAI asked icon sets to drop its logo; decisions row 45) |
| OpenCode | `OC` | OpenCode logo | simple-icons 16.36.0 |
| Cursor | `Cursor` | Cursor logo | simple-icons 16.26.0 (DS README) |
| Gemini | `Gemini` | Gemini logo | simple-icons 16.26.0 (DS README) |
| Command Code | `Command Code` | Neutral command glyph | Drawn (no logo source found) |
| Shared folder | `SH` | Folder | Drawn |
| This project / project folders | `PJ` | Code brackets | Drawn |
| Custom agent | `Custom agent` | Dashed square | Drawn |

**[SPEC]** Today `model.js` `AGENT_ICONS` holds vendored marks; phase 0
replaces them with the `system.css` mask rules so there is one mark source. The
mapping from scope id to `data-a` lives in one table in `model.js`
(`claude-code→CC`, `codex→CX`, `opencode→OC`, `cursor→Cursor`, `gemini→Gemini`,
`commandcode→Command Code`, `agents→SH`, `project-*→PJ`, `custom-*→Custom agent`).
Never brand colours (Claude's orange is ΔE 8 from the Different diamond).
Brand-guideline review before release is open question Q6.

## Logo

**[SPEC]** Use the files in `branding/jackfield/kit/svg/` (the DS Logos group is
a copy): horizontal lockup in the header (30px tall, 125px wide desktop; 29px /
121px phone), the symbol below 120px wide, the small symbol below 24px; the
`-dark` cuts on dark grounds (inline both, let `[data-theme]` pick, `.jf-l` /
`.jf-d`). Never retype the wordmark, recolour it, or light more than one cell
blue. Full rules: `branding/jackfield/kit/GUIDELINES.md`.

## Status vocabulary

**[SPEC]** Every status is a mark + a word; shapes differ so colour is never the
only signal. Classes: `sm-status is-…` with an `sm-mk` mark span.

| Status | Class | Mark | Word | Word colour |
|---|---|---|---|---|
| On | `is-on` | filled dot, `accent` | On | `ink` |
| Off | `is-off` | ring, `mark-faint` | Off | `mute` |
| Off in settings | `is-settings` | dashed ring, `mute` | Off in settings | `mute` |
| Different | `is-different` | diamond, `warn-mark` | Different | `warn` |
| Can't read | `is-unreadable` | cross, `bad` | Can't read | `bad` |
| Not here | `is-missing` | dash, `mark-faint` | Not here | `text-faint` |
| Version 1 / 2 | `is-version-1` / `is-version-2` | filled / hollow diamond, `warn-mark` | Version 1 / Version 2 | `warn` |
| Unknown | `is-unknown` | question mark, `mute` | Unknown | `mute` |
| Working | `is-working` | open ring that turns; it stops turning under `prefers-reduced-motion` | Working… | `accent` |

**[SPEC]** A failed change keeps the square's true word; the reason lives in the
side panel. When the app cannot verify a square it says Unknown with its own
mark and never borrows On. Which data produces which word:
@docs/redesign-build/04-frontend-architecture.md.

## Voice

**[SPEC]** Short, plain, specific: what happened, to which skill, in which agent,
what to do next. Sentence case. Buttons start with a verb and name the agent or
count ("Turn off in Codex", "Save to 3 places"). Never raw error codes, regular
expressions, internal scope ids (`commandcode`, `project-claude`) or
`<redacted>` in main text; raw detail goes under "Technical details" or
"Details". Examples to copy are in the DS README and the boards.

## Gates

**[SPEC]** Phase 0 leaves these green and phase 7 tightens them:

1. `check_design_tokens.py` re-derives every contrast pair from
   `design/tokens.json` **and** checks `tokens.css` was generated from it.
2. New test `tests/test_css_token_references.py`: every `var(--x)` in
   `skillsmgr/webui/*.css` and in inline styles in `*.js`/`index.html` resolves
   to a declared custom property (a `var(--a, var(--b))` chain passes when any
   member is declared). Closes the blind spot recorded in memory
   `css-token-reference-blind-spot`: an undeclared token renders transparent and
   passes Lighthouse.
3. The same test fails on any hex colour outside `tokens.css` (except mask data
   URIs) and, from phase 7, on any `alias:` line.
4. `check_package_data.py` asserts the new CSS/JS files, the fonts with their
   `@font-face` rules, and the OFL licence.
