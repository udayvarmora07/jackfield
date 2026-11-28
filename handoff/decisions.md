# Decisions: Skills Manager UI redesign

Every decision from the redesign record in one table, oldest first. Each row names the document it came from, and the wording follows that document. Where a later decision replaced an earlier one, both are kept and the later row says so.

Sources: `requirements.md` (R), `ux-brief.md` (UX), `design-brief.md` (DB), `ui-progress.md` (UI), design-system `README.md` (DS). All of them are in this folder.

## Phase 1: requirements (2026-11-24)

| # | Decision | Options considered | Chosen | Why | Source |
|---|---|---|---|---|---|
| 1 | What to fix first | Looks first; trust and clarity first; both together | Trust and clarity, then looks | The full test showed wrong statuses and silent overwrites hurt more than a plain look | R · Decision log |
| 2 | Evidence source | AI walkthrough; maintainer's 20-min test; both; opinion only | AI agents with real QA tools now, maintainer's short test before release | No human had tested by hand; the agents give concrete evidence at no cost to the maintainer | R |
| 3 | Who to design for | Maintainer; new GitHub developer; both | Both | Maintainer is user #1; marketing later brings new developers | R |
| 4 | Success measure | Daily use over CLI; under-2-minute task; public polish | Under-2-minute task + no wrong status, then polish | Measurable and covers both user types | R |
| 5 | Scope order | Every page; everyday jobs first; bugs only | Bugs → everyday jobs → all pages | Lowest risk first; each step useful alone | R |
| 6 | Constraints | Keep all; keep tech, open look; all open | Keep tech rules, open look | Tech rules protect the project; the look is what needs work | R |
| 7 | Personality | Calm/clear/trustworthy; fast/techy; friendly/playful | Calm, clear, trustworthy | People must feel safe before a tool changes their agents' setup | R |
| 8 | Technical words | Plain by default + details; keep technical | Plain by default + details | Works for beginners and experts | R |
| 9 | Advanced tools | Group in "Advanced"; remove some; keep as is | Group in one "Advanced" area | Nothing lost, everyday pages lighter | R |
| 10 | First launch | Auto-found agents + hint; guided tour; empty page | Auto-found agents + one hint | Shows value in 10 seconds with no setup | R |
| 11 | Changes to other agents' files | Preview + Undo; Undo only; confirm every time | Preview, then Undo | Removes silent overwrites without nagging | R |
| 12 | Files changed on disk | Detect and offer Refresh; manual only | Detect and offer Refresh | Otherwise the screen shows old, untrue information | R |
| 13 | Data sent to AI | Always preview; as now | Always preview | Skills can hold private text | R |
| 14 | Language | English only; plan for more | English only | Simpler; revisit after marketing | R |
| 15 | Accessibility | WCAG 2.2 AA; best effort | WCAG 2.2 AA | Automated scan already passes; low cost to keep | R |
| 16 | Where requirements live | Project root file; chat only | `requirements.md` in project root | Lets phase 2 and later sessions resume automatically | R |
| 17 | Assumptions A1–A21 | n/a | All signed off ("all okay") | n/a | R · Assumptions |

## Phase 2: UX (2026-11-24)

| # | Decision | Options considered | Chosen | Why | Source |
|---|---|---|---|---|---|
| 18 | Solution concept | 1 "Just ask" (search-first); 2 "One table of truth" (grid-first); 3 "Health check" (to-do-first) | **Hybrid:** concept 2 as the heart, plus concept 1's global search (`/`, Ctrl+K) and concept 3's single quiet "Needs attention" count with a one-at-a-time fixer | Concept 1 fails time-to-value and cleanup; concept 3 is slowest for everyday jobs and risks nagging; concept 2 wins on overview, drift, first-launch value and build effort | UX · Decision |
| 19 | Information architecture | n/a | Home + Sync map → Skills table; Inbox → Needs attention; Recovery → Trash & backups (one trash list); Tools → Advanced | One place for each thing (UX principle 3) | UX · IA |
| 20 | Advanced grouping | n/a | By goal: Add skills (Install, Templates, Profiles); Check my setup (Quality, Where agents look, Doctor); AI assist (Connection; Write, Test, Shorten, Find conflicts); Settings | Grouped by what the user wants to do | UX · IA |
| 21 | Phone model | n/a | Bottom tab bar with the same four places; table shows one agent at a time ("Showing: Codex ▾") | The grid can't fit at 390px | UX · IA |
| 22 | Hero screen | n/a | S1 Skills table with its side panel (S2) | Carries the success task, the first 10 seconds and the "status is never wrong" promise | UX · Hero |
| 23 | Concept, flows and screen inventory | n/a | Approved by the maintainer | n/a | UX · Approval |

## Phase 3: UI (2026-11-24 → 2026-11-26)

| # | Decision | Options considered | Chosen | Why | Source |
|---|---|---|---|---|---|
| 24 | Round 1 direction | A Console (dark, dense, keyboard-first); B Paper (light, sentence-first); C Tiles (bright grid) | **B · Paper** | Closest to "trust and clarity first, in plain words": plain-sentence verdicts and a note-like panel; calmest | UI · Picks |
| 25 | Round 2 variation | A Focus (hierarchy); B Inline answer; C Fine print (craft) | **C · Fine print + A's attention banner** | C's craft and "Now → After" preview make the trust promise visible; A's banner puts attention first. B rejected: rows jumping breaks "calm" at 200 skills | UI · Picks |
| 26 | Round 3 critique fixes | 10 fixes proposed | All 10 approved: readable grey text, outlined New skill, working primary + Undo bar, pinned side panel, focus rings, 44px phone icon buttons, keyboard hint line, "Show 50 more", plus phone and states boards | n/a | UI · Earlier status notes |
| 27 | Round 4 | n/a | Design system locked (tokens light + dark, 9 components) | n/a | UI |
| 28 | S3 Skill page | A Reader; B Row on top; C Fact sheet | **B + C's File text switch and sticky Edit bar** (chosen by Claude at the maintainer's request) | Same squares and panel as the table (one way to act); File text shows the truth on disk; A is a second way of acting, C is not actionable | UI · Picks |
| 29 | S4 Editor | A Save-to card; B Side by side; C Review before save | **A · Save-to card** | One step for an everyday job; a note per place says what saving does there | UI · Picks |
| 30 | S5 New skill | A One form; B Live preview; C Quick dialog | **B · Live preview** | Creating writes files into agent folders, so "show before you change" applies | UI · Picks |
| 31 | S7 Needs attention | A One at a time; B List and detail; C Grouped | **B · List and detail** (maintainer ranked B > C > A; Claude had recommended A) | See every problem and jump to any; Skipped and Fixed stay visible. C's "Fix all…" stays a possible later addition | UI · Picks |
| 32 | Supporting screens S6, S8–S13 | One version each | Approved as built, after a consistency pass (title 30px, button heights 38/36/46, search wording) | n/a | UI · Round 5 |
| 33 | Approved screens | n/a | Row of 14 in journey order (A01–A14) with prototype links; phase 3 done | n/a | UI |
| 34 | Dark theme | n/a | Dark copies D01–D14 of all 14 screens, linked in Play | Maintainer asked "dark theme for all pages" | UI |
| 35 | Design system additions | n/a | 5 new components (Segmented, Chip, Document, ChecksGrid, Compare); Button gains Accent, Quiet, page size; Field gains label, hint, textarea, checkbox, rule; tokens `control-page`, `title-doc`, `doc`, `file-text` (DS v5) | Patterns introduced in round 5 | UI |
| 36 | Class names for the build | Artboard-local names (`tick`, `seg`, `choice`, `chk`) or system names | **System names** (`sm-*`) when building | Naming note in the record | UI |
| 37 | AI-slop fixes | n/a | Three AI-default palettes replaced (Paper/Flexoki → Cobalt, Forest → Green light, Midnight → Night); off-scale radii snapped to 9/11/14/5px; pills only on labels and counts | Scanner and by-eye catalogue | UI · AI-slop audit |
| 38 | Colour system | C0 Today; C1 Cobalt; C2 Nordic; C3 Graphite; C4 Green light; C5 Night | **C0 Today** (56/65) with five tunings: light `bg` #F6F6F3, light `text-faint` #6E6E67, dark `mute` #B0B0A9, dark `accent` #8CAEFF, dark `text-faint` #9A9A93 | Blue On mark survives deuteranopia (teal turns grey, green collides with Different); others read as IBM, Vercel or GitHub brands | UI · Colour exploration |
| 39 | Typeface | T0 Inter + JetBrains Mono; T1 IBM Plex Sans + Mono; T2 Atkinson Hyperlegible Next; T3 Recursive | **T1 IBM Plex** (37/40; Atkinson 35, Inter 28, Recursive 30). Heading weight 650 → 600, tabular numbers | Legible at 12–14px, I/l/1 and O/0 distinct, 5–6% narrower than Inter, one superfamily for words and paths, not an AI default | UI · Type exploration |
| 40 | Fonts in the product | Google Fonts; bundled woff2 | **Bundle the woff2 files** (OFL allows it) | The app is offline-first and binds to 127.0.0.1 | UI; DS · Typography |
| 41 | Icons pass 1 | Text glyphs; inline SVG | Text glyphs (✓ ✕ × ▾ ?) → inline SVG, 2px stroke, `currentColor`; keycaps stay text | Design-system rule: never a text character for an icon | UI · Icons replace text marks |
| 42 | Agent marks | Brand-colour logos; one-colour marks; monograms | **One-colour marks** (`ink-2`) via CSS mask. Claude Code and OpenCode use their own logos (simple-icons 16.36.0); Codex a neutral terminal icon; Shared folder a folder; This project code brackets; monogram kept as fallback text | Claude's orange #D97757 is ΔE 8.1 from the Different diamond #C06A00 and would read as a warning | UI; DS · Iconography |
| 43 | Icons pass 2 | n/a | Agent marks in every place list; standard action icons only (download, upload, restore, refresh, copy, plug, bin, theme, file, warning). Everyday verbs, desktop nav, headings stay text | "Icons on everything is noise" | UI · Icons pass 2 |
| 44 | Choosing places on New skill | (a) keep wrap; (b) tighter chips; (c) drop marks; (d) equal-width grid; (e) vertical checkbox rows | **(e) Checkbox rows**, like the Editor's Save to (chosen by Claude at the maintainer's request) | One pattern app-wide; scales to 8 places with room for the folder or a note; native checkboxes announce clearly | UI · New skill "Add it to" |
| 45 | Codex mark | Neutral terminal icon; OpenAI's logo | **Keep the neutral terminal icon** (decided by Claude at the maintainer's request, 2026-11-26) | OpenAI asked icon libraries to remove its logo (it is no longer in simple-icons). The neutral mark is already designed, checked and in every screen. If OpenAI later publishes logo terms that allow this use, revisit | This handoff, at the maintainer's request |

## Superseded

- **Inter as the only typeface** (the AI-slop audit's "open, maintainer decision") was replaced by row 39.
- **Place chips on New skill** (pass 2) were replaced by row 44.
- **`DESIGN.md`** in the repo root (cool bone ground, teal accent) was described as "a starting point, not a rule" (R, A8). The design system (rows 35–44) replaces its look. The file itself was not updated: see `open-questions.md`.
