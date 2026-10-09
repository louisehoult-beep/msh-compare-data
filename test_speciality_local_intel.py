#!/usr/bin/env python3
"""Invariants for data/speciality-local-intel.json and its path into the panels.

The file is hand-curated from primary sources and published on paid speciality
pages, so every item must carry the evidence a member needs to check it, and a
source that has gone must never reach a page. Run on its own: python3 test_speciality_local_intel.py
"""
import json, os, re, sys, unittest

sys.path.insert(0, "scripts")
import build_speciality_panels as bsp

PATH = os.path.join("data", "speciality-local-intel.json")
REQUIRED = ("id", "group", "kind", "nation", "org", "title", "fact", "url", "verifiedOn")


class LocalIntel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PATH, encoding="utf-8") as fh:
            cls.doc = json.load(fh)

    def items(self):
        for slug, items in self.doc["specialities"].items():
            for it in items:
                yield slug, it

    def test_every_speciality_has_a_rule(self):
        # A slice for a slug with no SPECIALITY_RULES entry would never be built.
        for slug in self.doc["specialities"]:
            self.assertIn(slug, bsp.SPECIALITY_RULES, slug)

    def test_required_evidence_fields(self):
        for slug, it in self.items():
            for k in REQUIRED:
                self.assertTrue(it.get(k), "%s/%s missing %s" % (slug, it.get("id"), k))

    def test_urls_are_https(self):
        for slug, it in self.items():
            for k in ("url", "checkUrl"):
                if it.get(k):
                    self.assertTrue(it[k].startswith("https://"), "%s/%s %s" % (slug, it["id"], k))

    def test_group_is_declared(self):
        for slug, it in self.items():
            self.assertIn(it["group"], self.doc["groups"], "%s/%s" % (slug, it["id"]))

    def test_verified_on_is_a_real_past_date(self):
        import datetime
        for slug, it in self.items():
            self.assertRegex(it["verifiedOn"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertLessEqual(datetime.date.fromisoformat(it["verifiedOn"]), datetime.date.today())

    def test_ids_unique(self):
        ids = [it["id"] for _, it in self.items()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_gone_source_is_withheld(self):
        slug, first = next(self.items())
        gone = dict(first, lastCheck={"status": "gone", "date": "2026-09-28", "http": 404})
        kept = dict(first, id="x2", lastCheck={"status": "unreachable", "date": "2026-09-28", "http": 403})
        out = bsp.build_local_intel(slug, {"specialities": {slug: [gone, kept]}})
        self.assertEqual([x["id"] for x in out], ["x2"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
