---
version: beta
name: Jackfield
description: >-
  A local authority over the skill files that coding agents actually load. For a
  developer whose agents disagree and who has no way to see why. It should feel
  like a measuring instrument laid over a pile of documents: calm, exact, and
  slightly old-fashioned in the way good laboratory equipment is.
colors:
  ground: "#f2f3f1"
  surface: "#fdfdfc"
  sunken: "#eaecea"
  ink: "#1a1c1f"
  ink-2: "#454a50"
  muted: "#5a6168"
  signal: "#0d6a63"
  on-ink: "#ffffff"
  ok: "#1c7a47"
  ok-bg: "#e5f2ea"
  warn: "#8f4f00"
  warn-bg: "#fbf0dc"
  error: "#b42318"
  error-bg: "#fbe8e6"
  line: "#dfe2e0"
  line-strong: "#80878e"
typography:
  display:
    fontFamily: "IBM Plex Sans"
    fontSize: 30px
    fontWeight: 600
    letterSpacing: "-0.018em"
  body:
    fontFamily: "IBM Plex Sans"
    fontSize: 15px
    lineHeight: 1.55
  identifier:
    fontFamily: "IBM Plex Mono"
    fontSize: 13px
    fontWeight: 500
rounded:
  sm: 5px
  md: 6px
  lg: 8px
spacing:
  sm: 8px
  md: 16px
  lg: 28px
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-ink}"
    rounded: "{rounded.sm}"
    padding: "0 16px"
  button-quiet:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0 16px"
  button-danger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.error}"
    rounded: "{rounded.sm}"
    padding: "0 16px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    height: 38px
  state-ok:
    backgroundColor: "{colors.ok-bg}"
    textColor: "{colors.ok}"
    rounded: "{rounded.sm}"
    padding: "0 11px"
  state-differ:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn}"
    rounded: "{rounded.sm}"
    padding: "0 11px"
  state-unreadable:
    backgroundColor: "{colors.error-bg}"
    textColor: "{colors.error}"
    rounded: "{rounded.sm}"
    padding: "0 11px"
  focus-ring:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.signal}"
    rounded: "{rounded.sm}"
    height: 2px
  current-tab:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    height: 2px
  prose-body:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
---

## Overview

A skill is a markdown file that gets concatenated into a model's context window.
Users of this tool arrive because their agents are behaving differently and they
suspect the cause is their files. So the product's world is not "developer
dashboard" — it is **paperwork**: documents, copies, provenance, corrections,
and the budget of a single context window.

The visual source is the **printer's proof sheet**: a bone-coloured stock that
is cool rather than warm, set with one ink used like a stamp, ruled with
hairlines, and annotated in the margin wherever a claim needs its evidence.
Colour is spent on exactly one job — *state* — plus one reserved signal ink for
*interaction* (selection, focus, the current page, counts).

There is one interface, served at `/` by `python3 -m skillsmgr webui`. Its
stylesheets are `skillsmgr/webui/styles.css` and `skillsmgr/webui/tools.css`.
The previous "classic" interface and the cream, serif and terracotta prototype
look were both retired on 2026-11-23; see **Don't change**.

## Who uses it, and on what

This is a **local desktop tool**. The server binds `127.0.0.1` with no
authentication, and the port must never be forwarded, so it is reached from the
same computer: a laptop (1280–1536px, often 768px tall) or a monitor
(1920–2560px). Design for those first:

- The first useful content sits above the fold on a 1366×768 screen.
- Wide screens get wider tables and grids (the page frame is 1560px, the Sync
  map 1680px), not larger type or bigger margins.
- Keyboard first: `/` focuses the header search, Ctrl/Cmd K opens the command
  palette, arrow keys move through both, Escape closes.
- A narrow window or 200–400% zoom must still reflow without horizontal scroll
  (WCAG 1.4.10), but phone-first polish is not a goal.

## Colors

Every value is **measured**, not chosen by eye. Ratios use the WCAG 2.x
relative-luminance formula; `check_design_tokens.py` re-derives every pair from
`styles.css` in CI and fails on a regression.

- **Ground `#f2f3f1` (light) / `#101316` (dark):** a cool bone, not a parchment.
  This product is stared at for hours while debugging an agent; warm cream is
  fatiguing at that duration and is the first entry in the "tasteful AI"
  cluster. Cool bone reads as office paper under fluorescent light.
- **Surface `#fdfdfc` / `#171a1e`:** one step above ground, so cards separate by
  a hairline rather than a shadow.
- **Ink `#1a1c1f` → `#5a6168`:** three steps, every one of which clears 4.5:1 on
  every surface it can land on (ground, surface, sunken, hover, the reader's
  paper and tree). There is deliberately **no grey that fails AA**, because this
  tool's de-emphasised text is usually a file path, and a path you cannot read
  is a path you cannot debug.
- **Signal `#0d6a63` (light) / `#4fc7bd` (dark):** the one reserved ink — focus
  rings, the current tab's rule, the selected Sync map column, count badges and
  the brand mark's flagged cell. Chosen from a hue family with no overlap with
  the status colours, so a selection is never mistaken for a state.
- **Primary actions are ink, not signal.** One filled ink button per view; every
  other action is a bordered quiet button. A disabled button becomes an outline
  with muted text, never a grey fill that looks pressable.
- **Status:** ok green, warn amber, error red, off grey, each on its own tint.
  Red means *can't be read*, never *differs*. Different copies are amber: worth
  attention, not an error.

**Status is never colour alone.** Every state is an icon + colour + the word,
and an over-budget meter says "Over limit" in words.

## Typography

Two families, both **vendored as woff2** under `webui/static/fonts/` and never
fetched from a CDN (`font-src 'self'`): this app must work offline, and a font
request to a third party is a third party in the page.

- **IBM Plex Sans** — interface, headings and prose. Chosen over `system-ui`
  for a functional reason: `system-ui` renders differently on every platform,
  and this tool's job is comparing a file on macOS with a file on Linux.
  Identical glyphs on both machines is a correctness property here. There is no
  serif display face; headings are Plex Sans 600 with slight negative tracking.
- **IBM Plex Mono** — every identifier: skill names (cards, map rows, the
  reader's title, chips, search results), file paths, counts and percentages.
  A hyphen in `agent-desktop-ffi` must never read as a dash.

Scale (`--fs-*`, every step multiplied by the "Large text" preference):
caption 12, small 13, ui 14, body 15, lead 16, title 18, h3 20, h2 23, h1 30.
**12px is the floor** for any text a user must read. Skill documents render at
15/1.7 with a 72ch measure; a long description folds after four lines.

## Layout

- **Top bar** (66px): brand, six tabs (the current one carries a 2px signal
  rule), the header skill search with a results list, theme and help.
- **Pages** share one frame: `max-width: 1560px`, 40px gutters, the same left
  edge. Tools pages use a 1260px frame with a sticky local sidebar that fits a
  768px-tall screen.
- **Home:** agent cards in an auto-fill grid (two columns on a laptop, three on
  a 1920px monitor); each card's meter sits on the card floor so meters line up
  across a row. A side column carries "Needs a look" and listing budgets.
- **Skill reader:** a filterable tree, the document (72ch), and a margin rail of
  notes aligned with the document's first line.
- **Sync map:** a fixed-layout table (all six agent columns fit at 1280px) with
  a sticky comparison panel; capped at 1680px.

## Components

- **Buttons:** 40px (34px small). Ink primary, bordered quiet, red-text danger.
  A row's actions are text buttons, never icon-only.
- **Pills:** icon + word on a status tint, `999px` radius — the only rounded-pill
  shape in the product.
- **Cards:** 8px radius, 1px hairline, no shadow at rest; hover strengthens the
  hairline. A turned-off card is dashed, never faded with opacity.
- **Disclosures:** a drawn chevron that rotates, never the browser's triangle.
- **Command palette:** one field over a grouped list (Go to, Actions, Tools, AI
  assist), arrow keys move a highlighted row, Enter opens it.
- **Meter (the signature component):** the context-budget bar. Track, fill and a
  labelled 100% tick. The axis runs 0–125% so the threshold sits at 80% of the
  track — on a 0–100% axis, 111% and 121% both render as a full bar and the
  chart hides its own point.
- **Motion:** 120–180ms, `cubic-bezier(.2, 0, .2, 1)`, on paint properties and
  small transforms only. No bounce, no entrance animation on content that was
  already there. `prefers-reduced-motion` disables all of it.

## Don't change

These are refused defaults, recorded so a later pass cannot slide back into them.

- **Cream/parchment ground + serif display + terracotta accent.** The prototype
  and the first default interface used `#f7f5f0` + Newsreader + `#b8492a`. That
  is the "tasteful AI" cluster's exact coordinates and the first entry in every
  tell catalogue; it was removed on 2026-11-23. **Do not move the ground back
  toward warm or reintroduce a serif display face.**
- **Near-black ground + one neon accent in dark mode.** The dark theme is a full
  cool-graphite palette, not one bright colour on black.
- **Purple gradients, gradient-filled headline text, glassmorphism, neon glow.**
- **Decorative `01 / 02 / 03` numbering.** Number only genuine sequences.
- **One accented word inside a headline.**
- **Uppercase tracked-out labels above headings, and metadata joined with
  middle dots.** Labels are sentence case in the body face; metadata is a short
  sentence or comma list.
- **Bounce or elastic easing.**
- **Emoji as iconography.** Zero emoji anywhere in this interface.
- **A runtime CDN.** No Google Fonts link, no icon CDN, no webfont fetch.

## Verification

1. **This file** — the constraint. Read before designing any screen.
2. **`check_design_tokens.py`** — re-computes every contrast pair in
   `styles.css` (light and dark) against the WCAG formula, checks this file's
   colours match the stylesheet, and checks the fonts are vendored.
3. **`tests/test_v2_interface_contracts.py`** and the browser suite in
   `tools/e2e_v2` — the behaviour.
4. `python3 ~/.claude/skills/unslop-ui/scripts/devibe_scan.py skillsmgr/webui`
   as an advisory anti-slop scan. A clean scan is necessary, not sufficient.
