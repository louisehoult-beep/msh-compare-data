#!/usr/bin/env python3
"""app/hub-chrome.js (nav icons and the page bar with Save) and the one line
that loads it from snippet 1331.

Snippet 1331 runs on every Hub page, so its loader must be plain ASCII with no
double ampersand (WordPress and the WPCode editor have both broken those
before). The observer that re-applies nav icons must watch childList only,
never attributes, or its own writes set it off forever.

    python3 test_hub_chrome.py
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = os.path.join(HERE, "app", "hub-chrome.js")
LOADER = os.path.join(HERE, "hub", "wpcode", "nav-1331-hub-chrome-loader.html")


class HubChrome(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CHROME, encoding="utf-8") as f:
            cls.src = f.read()
        with open(LOADER, encoding="utf-8") as f:
            cls.loader = f.read()

    def test_loader_is_safe_to_paste_into_1331(self):
        self.assertTrue(self.loader.isascii(), "snippet 1331 must stay plain ASCII")
        self.assertNotIn("&&", self.loader)
        self.assertIn("MSH-HUB-CHROME-LOADER", self.loader)
        self.assertIn("app/hub-chrome.js", self.loader)
        self.assertEqual(self.loader.count("<script>"), 1)
        self.assertTrue(self.loader.strip().endswith("</script>"))

    def test_observer_never_watches_attributes(self):
        obs = re.findall(r"\.observe\([^)]*\)", self.src)
        self.assertTrue(obs)
        for o in obs:
            self.assertNotIn("attributes", o)
            self.assertIn("childList: true", o)
        self.assertIn("data-mshc", self.src)

    def test_page_bar_skips_my_hub_and_profile_chooser(self):
        m = re.search(r"NO_BAR = \[([^\]]*)\]", self.src)
        self.assertIsNotNone(m)
        self.assertIn("'/medical-sales-hub/my-hub/'", m.group(1))
        self.assertIn("'/medical-sales-hub/choose-your-profile/'", m.group(1))

    def test_hub_pages_only_and_members_only(self):
        self.assertIn("here.indexOf('/medical-sales-hub/') !== 0", self.src)
        self.assertIn("window.mshRestNonce || window.mshPrefsNonce", self.src)

    def test_one_base_constant(self):
        self.assertEqual(len(re.findall(r"raw\.githubusercontent\.com", self.src)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
