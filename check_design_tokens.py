#!/usr/bin/env python3
"""Verify the generated Paper tokens and contrast in both shipped themes."""

from __future__ import annotations

import json
import re
from tools.gen_tokens import OUTPUT, SOURCE, render_tokens, token_values


def _channel(value: int) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"not a 6-digit hex colour: {hex_colour!r}")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


TEXT_PAIRS = (
    ("accent", "accent-soft", "selected and On labels"),
    ("accent", "bg", "links on page ground"),
    ("accent", "surface", "links on cards"),
    ("on-accent", "accent", "primary action and count badges"),
    ("on-toast", "toast", "Undo bar and inverted controls"),
    ("warn", "warn-soft", "warning labels"),
    ("warn", "surface", "warning text within a card"),
    ("bad", "bad-soft", "unreadable and error labels"),
    ("bad", "surface", "error text within a card"),
    ("mute", "raise", "Off labels"),
    ("ink", "warn-soft", "highlighted document text"),
)
TEXT_PAIRS += tuple(
    (ink, surface, f"{ink} on {surface}")
    for ink in ("ink", "ink-2", "mute", "text-faint")
    for surface in ("bg", "surface", "raise", "accent-soft")
)
NON_TEXT_PAIRS = (
    ("text-faint", "bg", "legacy control boundary"),
    ("text-faint", "surface", "legacy control boundary on a card"),
    ("text-faint", "raise", "legacy control boundary on hover and panels"),
    ("accent", "bg", "focus and selection"),
    ("accent", "surface", "focus and selection on a card"),
    ("accent", "raise", "focus and selection on hover"),
)


def check_theme(palette: dict[str, str]) -> list[str]:
    failures = []
    for threshold, pairs in ((4.5, TEXT_PAIRS), (3.0, NON_TEXT_PAIRS)):
        for foreground, background, label in pairs:
            ratio = contrast(palette[foreground], palette[background])
            if ratio < threshold:
                failures.append(f"{label}: {foreground} on {background} = {ratio:.2f}:1 (needs {threshold}:1)")
    if contrast(palette["surface"], palette["bg"]) < 1.02:
        failures.append("Page ground and card surface do not separate by tone.")
    return failures


def check_fonts(css: str) -> list[str]:
    fonts = OUTPUT.parent / "static" / "fonts"
    failures = []
    for face in re.findall(r"@font-face\s*\{([^}]*)\}", css):
        path = re.search(r'url\("(static/fonts/[^"]+)"\)', face)
        if not path or not (OUTPUT.parent / path[1]).is_file() or "unicode-range:" not in face:
            failures.append(f"Incomplete vendored font face: {face.strip()}")
    if not (fonts / "OFL-IBM-Plex.txt").is_file():
        failures.append("The bundled IBM Plex fonts are missing their OFL licence.")
    return failures


def main() -> int:
    try:
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        css = OUTPUT.read_text(encoding="utf-8")
        failures = check_fonts(css)
        if css != render_tokens(source):
            failures.append("tokens.css differs from design/tokens.json. Run python3 tools/gen_tokens.py.")
        for theme in ("light", "dark"):
            failures.extend(f"{theme}: {reason}" for reason in check_theme(token_values(source, theme)))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failures = [f"Cannot verify the design tokens: {exc}"]
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("DESIGN TOKENS OK — generated stylesheet, offline font faces and contrast in both themes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
