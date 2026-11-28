"""Guard the shared disclosure icon against later global overrides."""
import re
import unittest
from pathlib import Path


WEB = Path(__file__).resolve().parents[1] / "skillsmgr" / "webui"


class DisclosureCssContract(unittest.TestCase):
    def test_shared_chevron_does_not_shrink_in_flex_summary(self):
        css = (WEB / "system.css").read_text(encoding="utf-8")
        rule = re.search(r"details>summary::before\s*\{([^{}]*)\}", css)
        self.assertIsNotNone(rule)
        self.assertRegex(rule.group(1), r"(?:^|;)\s*flex\s*:\s*none\s*(?:;|$)")

    def test_later_stylesheets_do_not_override_global_chevron_geometry(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        sheets = re.findall(r'<link\b[^>]*href="([^"]+\.css)(?:\?[^"]*)?"', index)
        self.assertIn("system.css", sheets)
        for sheet in sheets[sheets.index("system.css") + 1:]:
            css = re.sub(r"/\*.*?\*/", "", (WEB / sheet).read_text(encoding="utf-8"), flags=re.S)
            for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
                for part in selector.split(","):
                    compact = re.sub(r"\s+", "", part)
                    if compact in ("details>summary::before", "details[open]>summary::before"):
                        self.assertNotRegex(declarations, r"(?:^|;)\s*(?:width|height|transform|border(?:-[\w-]+)?|margin(?:-[\w-]+)?)\s*:",
                                            f"{sheet}: {part} overrides the shared chevron")

    def test_findings_exception_is_preserved(self):
        css = (WEB / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.tp-findings\s*>\s*li\s*>\s*details\s*>\s*summary::before\s*\{\s*content:\s*none")
