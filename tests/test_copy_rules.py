"""Copy rules for the Paper shell and its new screens."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


WEBUI = Path(__file__).resolve().parent.parent / "skillsmgr" / "webui"


class VisibleCopy(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.parts = []
        self.buttons = []
        self.button = None
        self.feed(markup)

    def handle_data(self, data):
        text = re.sub(r"\{\{.*?\}\}", "", data)
        self.parts.append(text)
        if self.button is not None:
            self.button["parts"].append(text)

    def handle_starttag(self, tag, attrs):
        self.parts.extend(value for name, value in attrs
                          if name in {"aria-label", "placeholder", "title"} and value)
        attributes = dict(attrs)
        if tag == "button" and attributes.get("role") != "option":
            self.button = {"label": attributes.get("aria-label"), "parts": []}

    def handle_endtag(self, tag):
        if tag == "button" and self.button is not None:
            label = self.button["label"] or "".join(self.button["parts"]).strip()
            if label:
                self.buttons.append(label)
            self.button = None


def shell_copy():
    html = (WEBUI / "index.html").read_text(encoding="utf-8")
    palette = html.split('<div v-if="dialog.commands" class="palette jf-palette">', 1)[1]
    palette = palette.split('<div class="pick-list"', 1)[0]
    discard = html.split('<div class="dlg-f" v-if="dialog.createDiscard">', 1)[1]
    discard = discard.split('<div class="dlg-f" v-else-if=', 1)[0]
    shared = html.split('<template id="jf-nav-template">', 1)[1].split('<script src=', 1)[0]
    return VisibleCopy(palette + discard + shared)


class PaperCopyTests(unittest.TestCase):
    def test_shell_and_new_screens_keep_internal_errors_out_of_visible_copy(self):
        copy = " ".join(shell_copy().parts)
        self.assertNotRegex(copy, r"\[Errno\b|\b(?:Traceback|StoreError|SkillNotFound|claude-code|project-local|api/v1)\b")
        self.assertNotRegex(copy, r"\\[dDwWsS]|\(\?:|\[[A-Za-z0-9]-[A-Za-z0-9]\]")
        for text in ("Nothing matches", "Did you mean", "Go to Skills", "Look in Trash"):
            self.assertIn(text, copy)

    def test_new_action_labels_start_with_verbs(self):
        js = (WEBUI / "palette.js").read_text(encoding="utf-8")
        actions = js.split("const actions = [", 1)[1].split("];", 1)[0]
        labels = re.findall(r'label: "([^"]+)"', actions)
        self.assertEqual(len(labels), 8)
        verbs = {"Fix", "Show", "Download", "Switch", "Refresh", "Add", "Search",
                 "Close", "Dismiss", "Undo", "Keep", "Discard"}
        conventional_labels = {"New skill", "Keyboard shortcuts"}
        self.assertIn("Keep editing", shell_copy().buttons)
        for label in [*labels, *shell_copy().buttons]:
            with self.subTest(label=label):
                self.assertTrue(label in conventional_labels or label.split()[0] in verbs)
