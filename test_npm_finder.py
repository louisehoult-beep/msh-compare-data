#!/usr/bin/env python3
"""Tests for scripts/refresh_npm_finder.py and verify.check_npm_finder (20/10/2026).

Stdlib only, no network. What is pinned, and why:
  * the category list is read from the right block, and the intravenous cannula
    entry that the live page splits across two links is read once, cleanly;
  * matching is strict: a category joins a framework only on the same name or
    when it opens exactly one framework name, so a guessed join never puts the
    wrong dates in front of a member;
  * the "Savings Opportunities" heading is stripped from the quoted sentence;
  * the gate refuses a supplier list, a join to a framework the Hub does not
    publish as live, drifted dates and counts that disagree with the rows.
"""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, HERE)

import refresh_npm_finder as n   # noqa: E402
import verify as v               # noqa: E402

PAGE = """<h2>NPMs (National Pricing Matrices)</h2>
<ul><li><a href="x">Advanced Wound Care</a></li>
<li><a href="x">Central Venous Catheters</a></li>
<li><a href="x">Intravenous Cannula and Associated Products</a> <a href="x">National Pricing Matrix (NPM)</a></li>
<li><a href="x">Suction Consumables</a></li></ul>
<h3>Links section</h3><a href="x">Framework Agreements</a>"""

FRAMEWORKS = [
    {"name": "Advanced Wound Care", "starts": "1 September 2025", "ends": "31 August 2027"},
    {"name": "Central Venous Catheters and Associated Products", "starts": "1 May 2024", "ends": "30 April 2028"},
    {"name": "Intravenous Cannula and Associated Products", "starts": "27 March 2023", "ends": "31 March 2027"},
    {"name": "Surgical Mesh", "starts": "1 June 2024", "ends": "31 May 2028"},
    {"name": "Surgical Mesh Fixation", "starts": "1 June 2024", "ends": "31 May 2028"},
]


class Parse(unittest.TestCase):
    def test_categories_read_once_and_clean(self):
        self.assertEqual(n.parse_categories(PAGE), [
            "Advanced Wound Care", "Central Venous Catheters",
            "Intravenous Cannula and Associated Products", "Suction Consumables"])

    def test_no_block_means_nothing(self):
        self.assertEqual(n.parse_categories("<p>redesigned</p>"), [])


class Match(unittest.TestCase):
    def test_same_name(self):
        fw, rule = n.match_framework("Advanced Wound Care", FRAMEWORKS)
        self.assertEqual(fw["name"], "Advanced Wound Care")
        self.assertEqual(rule, "same name")

    def test_opening_words(self):
        fw, _ = n.match_framework("Central Venous Catheters", FRAMEWORKS)
        self.assertEqual(fw["name"], "Central Venous Catheters and Associated Products")

    def test_punctuation_and_the_word_and_ignored(self):
        fw, _ = n.match_framework("Intravenous Cannula & Associated Products", FRAMEWORKS)
        self.assertIsNotNone(fw)

    def test_no_guess(self):
        fw, rule = n.match_framework("Suction Consumables", FRAMEWORKS)
        self.assertIsNone(fw)
        self.assertEqual(rule, "not matched")

    def test_exact_wins_over_prefix(self):
        fw, _ = n.match_framework("Surgical Mesh", FRAMEWORKS)
        self.assertEqual(fw["name"], "Surgical Mesh")


class Brief(unittest.TestCase):
    def test_heading_stripped(self):
        page = ("<h2>Savings Opportunities</h2><p>The framework provides a National Pricing "
                "Matrix (NPM) from a number of suppliers. Other text.</p>")
        orig = n.fetch
        n.fetch = lambda url, tries=2: page
        try:
            got = n.brief_npm("https://example")
        finally:
            n.fetch = orig
        self.assertEqual(got["statement"],
                         "The framework provides a National Pricing Matrix (NPM) from a number of suppliers.")


class Gate(unittest.TestCase):
    def setUp(self):
        v.fails[:] = []
        v.warns[:] = []
        self.fw = {"frameworks": FRAMEWORKS}
        self.doc = {
            "categoryCount": 15, "matchedCount": 1,
            "categories": [{"category": "Advanced Wound Care", "framework": {
                "name": "Advanced Wound Care", "starts": "1 September 2025", "ends": "31 August 2027"}}]
            + [{"category": "Cat %d" % i, "framework": None} for i in range(14)],
        }

    def fails(self):
        return [m for c, m in v.fails if c == "npm-finder"]

    def warns(self):
        return [m for c, m in v.warns if c == "npm-finder"]

    def test_clean_passes(self):
        v.check_npm_finder(self.doc, self.fw)
        self.assertEqual(self.fails(), [])

    def test_supplier_list_refused(self):
        d = copy.deepcopy(self.doc)
        d["categories"][0]["suppliers"] = ["Anyone Ltd"]
        v.check_npm_finder(d, self.fw)
        self.assertTrue(any("supplier list" in m for m in self.fails()))

    def test_join_to_unpublished_framework_warns_never_blocks(self):
        d = copy.deepcopy(self.doc)
        d["categories"][0]["framework"]["name"] = "Expired Framework"
        v.check_npm_finder(d, self.fw)
        self.assertEqual(self.fails(), [])
        self.assertTrue(any("not a live framework" in m for m in self.warns()))

    def test_drifted_dates_warn_never_block(self):
        d = copy.deepcopy(self.doc)
        d["categories"][0]["framework"]["ends"] = "31 August 2029"
        v.check_npm_finder(d, self.fw)
        self.assertEqual(self.fails(), [])
        self.assertTrue(any("dates" in m for m in self.warns()))

    def test_counts_must_agree(self):
        d = copy.deepcopy(self.doc)
        d["matchedCount"] = 5
        v.check_npm_finder(d, self.fw)
        self.assertTrue(any("matchedCount" in m for m in self.fails()))

    def test_short_list_refused(self):
        d = copy.deepcopy(self.doc)
        d["categories"] = d["categories"][:5]
        d["categoryCount"] = 5
        v.check_npm_finder(d, self.fw)
        self.assertTrue(any("partial list" in m for m in self.fails()))


if __name__ == "__main__":
    unittest.main()
