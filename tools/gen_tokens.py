#!/usr/bin/env python3
"""Generate the checked-in web UI token sheet from the approved design export."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design" / "tokens.json"
OUTPUT = ROOT / "skillsmgr" / "webui" / "tokens.css"

# The vendored IBM Plex subsets use the same Unicode ranges for both families.
SUBSETS = {
    "latin": (
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, "
        "U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, "
        "U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"
    ),
    "latin-ext": (
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, "
        "U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, "
        "U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF"
    ),
}
FACES = (
    ("Sans", "400", "100 700"),
    ("Mono", "400", "400"),
    ("Mono", "500", "500"),
    ("Mono", "600", "600"),
)


def font_rules() -> list[str]:
    return [
        "@font-face {\n"
        f'  font-family: "IBM Plex {family}";\n'
        f'  src: url("static/fonts/IBMPlex{family}-{file_weight}-{subset}.woff2") format("woff2");\n'
        f"  font-weight: {weight};\n"
        "  font-display: swap;\n"
        f"  unicode-range: {codepoints};\n"
        "}"
        for family, file_weight, weight in FACES
        for subset, codepoints in SUBSETS.items()
    ]


def token_values(source: dict, theme: str) -> dict[str, str]:
    values = {}
    for section in ("color", "spacing", "radius", "shadow", "size"):
        for token in source[section]["tokens"]:
            value = token["value"]
            values[token["name"]] = value[theme] if isinstance(value, dict) else value
    for name, value in source["type"]["families"].items():
        values[f"font-{name}"] = value
    for group in source["type"]["groups"]:
        for style in group["styles"]:
            name = style["name"]
            values[f"type-{name}-size"] = style["fontSize"]
            values[f"type-{name}-line"] = style["lineHeight"]
            values[f"type-{name}-weight"] = str(style["fontWeight"])
            if "letterSpacing" in style:
                values[f"type-{name}-tracking"] = style["letterSpacing"]
    return values


def css_block(selector: str, theme: str, values: dict[str, str]) -> str:
    declarations = [f"  color-scheme: {theme};"]
    declarations.extend(f"  --{name}: {value};" for name, value in values.items())
    return "\n".join([selector + " {", *declarations, "}"])


def render_tokens(source: dict) -> str:
    light = token_values(source, "light")
    dark = {k: v for k, v in token_values(source, "dark").items() if v != light[k]}
    return "\n\n".join([
        "/* Jackfield — generated from design/tokens.json; do not edit */",
        *font_rules(),
        css_block(":root", "light", light),
        css_block(':root[data-theme="dark"]', "dark", dark),
    ]) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the generated sheet without editing it.")
    args = parser.parse_args()
    css = render_tokens(json.loads(SOURCE.read_text(encoding="utf-8")))
    if args.check:
        if OUTPUT.is_file() and OUTPUT.read_text(encoding="utf-8") == css:
            return 0
        parser.exit(1, "tokens.css is stale. Run python3 tools/gen_tokens.py.\n")
    OUTPUT.write_text(css, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
