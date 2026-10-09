#!/usr/bin/env python3
"""Ask the Hub passage loader (build_ask_passages.py), offline.

Three promises checked without a token or a network:
  1. Every passage carries a Hub link, so every answer point can cite one.
  2. The Live Desk's rotating rows are stripped, as they are for search.
  3. A supplier passage states a framework only when the record carries the
     source notice URL, the same confirmed-facts rule as the quick answer.
Nothing here writes a passage to disk: the repo is public (ruled 06/08/2026).
"""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

import build_ask_passages as bap  # noqa: E402
import build_search_index as bsi  # noqa: E402


class TestAskPassages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages, cls.sups = bap.build(bsi.load_fixtures())

    def test_every_page_passage_links_into_the_hub(self):
        self.assertTrue(self.pages)
        for p in self.pages:
            self.assertTrue(p["url"].startswith(bsi.HUB_PREFIX), p["url"])
            self.assertTrue(p["heading"])
            self.assertGreaterEqual(len(p["body"]), bap.MIN_TEXT)

    def test_anchor_used_when_the_section_has_one(self):
        self.assertIn("/medical-sales-hub/value-based-procurement/#vbp-domains",
                      [p["url"] for p in self.pages])

    def test_live_desk_rows_are_not_passages(self):
        for p in self.pages:
            for month in (" January ", " February ", " September ", " October "):
                self.assertNotIn(month, " " + p["body"] + " ", p["url"])

    def test_long_text_is_cut_at_sentences(self):
        text = " ".join("Sentence number %d ends here." % i for i in range(200))
        parts = bap.chunks(text)
        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part), bap.CHUNK * 1.5)
            self.assertTrue(part.endswith("."), part[-30:])
        self.assertEqual(" ".join(parts), text)

    def test_supplier_frameworks_are_source_backed_only(self):
        self.assertTrue(self.sups)
        import json
        with open("data/supplier-index.json") as f:
            recs = {s["name"].strip(): s for s in json.load(f)["suppliers"] if s.get("name")}
        for p in self.sups:
            rec = recs[p["heading"]]
            unsourced = [fw["name"] for fw in rec.get("frameworks") or []
                         if isinstance(fw, dict) and fw.get("name") and not fw.get("url")]
            sourced = [fw["name"] for fw in rec.get("frameworks") or []
                       if isinstance(fw, dict) and fw.get("name") and fw.get("url")]
            for name in unsourced:
                if name not in sourced:
                    self.assertNotIn(name, p["body"], p["heading"])
            self.assertTrue(p["url"].startswith(bsi.HUB_PREFIX + "company-report/?company="))


if __name__ == "__main__":
    unittest.main(verbosity=1)
