"""The loaded Paper and migration rules must resolve every custom property."""

from pathlib import Path
import re
import unittest


WEBUI = Path(__file__).resolve().parents[1] / "skillsmgr" / "webui"
SHEETS = ("tokens.css", "system.css", "layout.css", "styles.css", "tools.css")


class CssTokenReferenceTests(unittest.TestCase):
    def test_all_loaded_stylesheets_resolve_their_token_names(self):
        html = (WEBUI / "index.html").read_text(encoding="utf-8")
        self.assertEqual(tuple(re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)), SHEETS)
        source = "\n".join((WEBUI / name).read_text(encoding="utf-8") for name in SHEETS)
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        declares = set(re.findall(r"(--[a-z][a-z0-9-]*)\s*:", source))
        uses = set(re.findall(r"var\(\s*(--[a-z][a-z0-9-]*)", source))
        self.assertTrue(uses)
        self.assertEqual(uses - declares, set())

    def test_hex_colours_live_in_the_generated_stylesheet(self):
        for name in SHEETS[1:]:
            text = (WEBUI / name).read_text(encoding="utf-8")
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            with self.subTest(stylesheet=name):
                self.assertNotRegex(text, r"#[0-9a-fA-F]{3,8}(?=[, );}])")
