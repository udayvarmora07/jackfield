# Jackfield — Logo Guidelines

Status: **approved direction (B7, Quiet soft J), 2026-11-26; in use since the rename on 2026-11-27.**
The product, repository and CLI are Jackfield (formerly Skills Manager). Trademark and domain checks
for "Jackfield" are not done yet.

## 1. The logo

- **Idea:** a 3×3 field of jacks. The cells that spell **J** are lit, the three quiet cells stay grey, and the
  blue cell at the top right is the jack being patched in. It is the product's own skills × agents table
  with the active cells lit.
- **Versions:** horizontal lockup (primary) · stacked lockup · symbol · wordmark.
- **Wordmark:** "jackfield" in IBM Plex Mono SemiBold, tracking −30, outlined. The dots of the **i** and
  **j** are replaced by field cells; the **j**'s dot is the blue jack.

## 2. Construction

- Canvas 256 × 256. Cells 64, gaps 16, margin 16, so every cell edge sits on a whole pixel at 16 px.
- Corner radius 8 on every cell; the bowl's two outer corners use radius 40.
- Dark versions inset each light cell by 1 unit (cells 62) to offset irradiation, the effect that makes
  light shapes on dark grounds look heavier. Use the `-dark` and `-white` files and don't invert the light ones.

## 3. Clear space

One cell on every side: **¼ of the symbol's height** (64 units at 256). The gap between symbol and wordmark
in the lockups is also one cell.

## 4. Minimum size

| Version | Minimum | Below that |
|---|---|---|
| Symbol | 24 px | use `jackfield-symbol-small*.svg` (no quiet cells), down to 16 px |
| Horizontal lockup | 120 px wide | use the symbol |
| Stacked lockup | 80 px wide | use the symbol |
| Wordmark | 72 px wide | — |

## 5. Colour

| Role | HEX | RGB | CMYK (approx.) | Contrast |
|---|---|---|---|---|
| Ink | `#191917` | 25 25 23 | 0 0 8 90 | 17.6:1 on white |
| Jack blue | `#2D58D0` | 45 88 208 | 78 58 0 18 | 6.1:1 on white |
| Quiet | `#DDDDD8` | 221 221 216 | 0 0 2 13 | decorative |
| Ink (dark) | `#EDEDEA` | — | — | 16.0:1 on `#121211` |
| Jack blue (dark) | `#8CAEFF` | — | — | 8.6:1 on `#121211` |
| Quiet (dark) | `#2C2C2A` | — | — | decorative |

These are the Jackfield design system v11 tokens (`--ink`, `--accent`, dark `--line`). CMYK values are
straight conversions, so match on press. No Pantone has been chosen.

**One colour:** black, white or blue files drop the quiet cells and keep the J. The J carries the identity
on its own.

## 6. Typography

- Wordmark: IBM Plex Mono SemiBold (SIL Open Font License), outlined in the masters.
- Product UI: IBM Plex Sans / Plex Mono, as in DESIGN.md.

## 7. Don'ts

- Don't recolour the jack cell or make more than one cell blue.
- Don't rotate, mirror or rearrange the cells. The J must stay a J.
- Don't use the full symbol (with quiet cells) below 24 px. Use the small cut.
- Don't put the light-mode files on dark grounds. Use the `-dark` or `-white` files.
- Don't place the blue jack on a blue ground. Use the white one-colour version.
- Don't add gradients, shadows, glows or outlines.
- Don't retype the wordmark in live text or another font.
- Don't stretch, skew or squeeze any version.

## 8. Files

```
svg/  jackfield-{symbol,horizontal,stacked,wordmark}[-dark|-black|-white|-blue].svg
      jackfield-symbol-small[-dark].svg      small cut, 16–24 px
      jackfield-*-adaptive.svg               follows prefers-color-scheme (README, docs)
      jackfield-favicon.svg                  adaptive small cut for browser tabs
png/  1024-px renders of each version, light and dark (transparent)
web/  favicon.ico, favicon.svg, favicon-16/32/48.png, apple-touch-icon.png, icon-192/512.png,
      maskable-512.png, site.webmanifest, head-snippet.html
board/ presentation board (HTML) and slides/*.png with README, app icon, website, terminal,
       sticker and social mockups
```
