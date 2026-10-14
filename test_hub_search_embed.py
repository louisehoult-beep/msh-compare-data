#!/usr/bin/env python3
"""app/hub-search.js: the My Hub search modal mount.

Search from My Hub reuses the Live Desk's full-text search rather than a copy
of it (spec item 7), through a third mount, [data-hub-search-embed]. Static
checks: the file is served to every Live Desk visit, so node --check in
verify.py guards the syntax.

    python3 test_hub_search_embed.py
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "app", "hub-search.js")


class HubSearchEmbed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SRC, encoding="utf-8") as f:
            cls.src = f.read()

    def test_third_mount(self):
        self.assertIn("var EMBED = document.querySelector('[data-hub-search-embed]');", self.src)
        self.assertIn("if (!MOUNT && !MAST && !EMBED) { return; }", self.src)
        self.assertIn("document.querySelector('[data-hub-search-results]')", self.src)
        self.assertIn("if (EMBED) { bindEmbed(EMBED); }", self.src)

    def test_no_inline_font_below_12px(self):
        small = re.findall(r"font-size:\s*(?:1[01](?:\.\d+)?|[0-9](?:\.\d+)?)px", self.src)
        self.assertEqual(small, [])

    def test_need_path(self):
        self.assertIn("return askBox(inner + needHtml());", self.src)
        self.assertIn("JSON.stringify({ need: t, pass: pass })", self.src)
        self.assertIn("data-need-open", self.src)
        self.assertIn("data-need-send", self.src)

    def test_need_copy_rules(self):
        start = self.src.index("TELL US WHAT YOU NEED")
        end = self.src.index("function askAnswer(d)")
        block = self.src[start:end]
        for lit in re.findall(r"'(?:[^'\\\n]|\\.)*'", block):
            self.assertNotIn("—", lit)
            self.assertNotIn("–", lit)
        self.assertNotRegex(block.lower(), r"\bmed ?tech\b")
        self.assertNotRegex(block, r"sk-ant|service_role|SECRET", "no secret ever in a browser file")

    def test_need_reset_and_accessibility(self):
        # I1: NEED.state 'sent' must be reset when a new ask starts
        self.assertIn("if (NEED.state === 'sent') { NEED = { open: false, state: '', msg: '', text: '' }; }", self.src)
        # M1: Thanks line must have role="status" for accessibility
        thanksidx = self.src.index("Thanks. Your request is with the Hub team")
        thanksblock = self.src[thanksidx - 300:thanksidx + 50]
        self.assertIn('role="status"', thanksblock)


if __name__ == "__main__":
    unittest.main(verbosity=1)
