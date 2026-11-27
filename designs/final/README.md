# Approved screens (Jackfield UI)

Copies of the approved boards on the Design canvas
(https://claude.ai/artifact/2bRpEoQ192WY2Tp7dYsXdq, version 58, 2026-11-27), for `/build`.
Each file is a canvas artboard source (`.dc.html`); it renders on the canvas (Play), not as a
plain web page, because it loads the canvas runtime (`support.js`). Read them for layout, copy,
states and behaviour; the look comes from the design system v13
(https://claude.ai/artifact/27HHwcNGwDAZ2cne6xW4ei).

`light/` and `dark/` hold the same screens in the same journey order:

| # | Light | Dark | Screen |
|---|---|---|---|
| 1 | A01 | D01 | S1 Skills table + S2 side panel (hero) |
| 2 | A02 | D02 | Skills table, phone |
| 3 | A03 | D03 | Skills table states (first launch summary, loading, no agents, files changed) |
| 4 | A04 | D04 | S3 Skill page |
| 5 | A05 | D05 | S4 Editor |
| 6 | A06 | D06 | S5 New skill |
| 7 | A07 | D07 | S6 Why isn't it running? |
| 8 | A08 | D08 | S7 Needs attention |
| 9 | A09 | D09 | S8 Trash & backups |
| 10 | A10 | D10 | S9 Advanced |
| 11 | A11 | D11 | S10 Tool page template |
| 12 | A12 | D12 | S11 Settings |
| 13 | A13 | D13 | S12 Search |
| 14 | A14 | D14 | S13 Not found |
| 15 | A15 | D15 | S2 side panel: Evenly split, Unknown, Working, Failed |
| 16 | A16 | D16 | S1 first launch: Looking for your agents… |
| AT 1–9 | ATA-01…09 | ATD-01…09 | Agent tracking: S1+, phone, S9+, S11+, S14/S15/S17, phone, S16, S18, S10+ |

Where an Agent tracking screen (ATA/ATD) changes a main screen (S1, S9, S10, S11), the Agent
tracking version is the current one.

**Edited after export (2026-11-27):** in ATA-07, ATA-08, ATD-07 and ATD-08 the sample home path
in the `norm()` helper was changed to `/home/you/` (and its prefix length from 11 to 10) before
these files were committed to the public repository. Nothing visible changed; those four files
no longer match the canvas byte for byte. Every other file is an unmodified copy of canvas v58.

The build spec that uses these boards is `docs/61-redesign-build-spec-2026-11-27.md`.
