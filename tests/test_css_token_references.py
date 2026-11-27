"""The loaded Paper and migration rules must resolve every custom property."""

from pathlib import Path
import re
import unittest


WEBUI = Path(__file__).resolve().parents[1] / "skillsmgr" / "webui"
SHEETS = ("tokens.css", "system.css", "layout.css", "styles.css", "tools.css")
INLINE_STYLE = re.compile(r"""(?<![\w-]):?style\s*=\s*(["'])(.*?)\1""", re.DOTALL)
PAGE_FILES = (WEBUI / "index.html", *sorted(WEBUI.glob("*.js")))


class CssTokenReferenceTests(unittest.TestCase):
    def test_all_loaded_stylesheets_resolve_their_token_names(self):
        html = (WEBUI / "index.html").read_text(encoding="utf-8")
        self.assertEqual(tuple(re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)), SHEETS)
        source = "\n".join((WEBUI / name).read_text(encoding="utf-8") for name in SHEETS)
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        declares = set(re.findall(r"(--[a-z][a-z0-9-]*)\s*:", source))
        templates = "\n".join(path.read_text(encoding="utf-8") for path in PAGE_FILES)
        uses = set(re.findall(r"var\(\s*(--[a-z][a-z0-9-]*)", source + templates))
        self.assertTrue(uses)
        self.assertEqual(uses - declares, set())

    def test_hex_colours_live_in_the_generated_stylesheet(self):
        hex_colour = r"#[0-9a-fA-F]{3,8}(?=[, );}]|$)"
        for name in SHEETS[1:]:
            text = (WEBUI / name).read_text(encoding="utf-8")
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            with self.subTest(stylesheet=name):
                self.assertNotRegex(text, hex_colour)
        for path in PAGE_FILES:
            with self.subTest(template=path.name):
                for _, style in INLINE_STYLE.findall(path.read_text(encoding="utf-8")):
                    self.assertNotRegex(style, hex_colour)
