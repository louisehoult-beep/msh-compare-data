#!/usr/bin/env python3
"""Invariants for hub/my-hub-catalogue.json, read by app/my-hub.js.

A member's saved My Hub is a list of catalogue ids, so the catalogue has to
stay consistent: ids unique and never reused for a different page, every item
in a declared group, every role starter pointing at a real item, and the
"+ news" flag set exactly where a speciality news file exists (a flag with no
file is a promise of news that never arrives; a file with no flag is news the
member never sees).

    python3 test_my_hub_catalogue.py
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(HERE, "hub", "my-hub-catalogue.json")
NEWS = os.path.join(HERE, "data", "speciality-news")
JS = os.path.join(HERE, "app", "my-hub.js")


class MyHubCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CAT, encoding="utf-8") as f:
            cls.cat = json.load(f)
        cls.items = cls.cat["items"]
        cls.ids = [i["id"] for i in cls.items]

    def test_ids_unique_and_storable(self):
        self.assertEqual(len(self.ids), len(set(self.ids)), "duplicate catalogue id")
        # The account store runs ids through WordPress sanitize_key().
        for i in self.ids:
            self.assertRegex(i, r"^[a-z0-9_-]{1,80}$", i)

    def test_urls_are_hub_member_pages(self):
        urls = [i["url"] for i in self.items]
        self.assertEqual(len(urls), len(set(urls)), "two items open the same page")
        for i in self.items:
            self.assertTrue(re.match(r"^/medical-sales-hub/([a-z0-9-]+/)*$", i["url"]), i["url"])
            self.assertTrue(i["label"].strip(), i["id"])

    def test_groups_declared(self):
        groups = {g["id"] for g in self.cat["groups"]}
        for i in self.items:
            self.assertIn(i["group"], groups, i["id"])
        used = {i["group"] for i in self.items}
        self.assertEqual(groups, used, "a group with no items shows as an empty heading")

    def test_role_starters_resolve(self):
        ids = set(self.ids)
        for k, r in self.cat["roles"].items():
            self.assertTrue(r["pins"], k)
            for p in r["pins"]:
                self.assertIn(p, ids, "role %s names %s, not in the catalogue" % (k, p))

    def test_news_flag_matches_files(self):
        files = {f[:-5] for f in os.listdir(NEWS) if f.endswith(".json")}
        flagged = {i["id"] for i in self.items if i.get("news")}
        spec_ids = {i["id"] for i in self.items if i["group"] == "specialities"}
        self.assertEqual(flagged, files & spec_ids)
        self.assertEqual(files - spec_ids, set(), "a news file whose speciality cannot be pinned")

    def test_js_reads_this_catalogue(self):
        with open(JS, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("hub/my-hub-catalogue.json", src)
        self.assertIn("data/speciality-news/", src)
        # Never write a member's page with raw catalogue or feed text.
        self.assertIn("function esc(", src)


if __name__ == "__main__":
    unittest.main(verbosity=1)
