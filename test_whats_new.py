#!/usr/bin/env python3
"""Invariants for hub/whats-new.json, the What's new box on My Hub.

Lou, 01/10/2026: navigation, tools and functions only, never content; one
sentence each; tags New, Improved or Fixed; a Show me link. Members' accounts
remember which entry ids they have seen, so an id is never reused or renamed.
Any nav or tool change adds an entry in the same session
(Process flows for all brands/my-hub-home-screen.md).

    python3 test_whats_new.py
"""
import datetime
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WN = os.path.join(HERE, "hub", "whats-new.json")
TAGS = {"New", "Improved", "Fixed"}
TARGETS = {"spec", "scope", "tools", "library", "briefing", "saved", "search", "how", "new", "checklist", "pages"}
KEYS = {"id", "date", "tag", "title", "text", "showMe"}
DASHES = ("\u2014", "\u2013")
US = re.compile(r"\b(color|center|favorite|organiz|optimiz|customiz|personaliz|catalog\b)", re.I)


class WhatsNew(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WN, encoding="utf-8") as f:
            cls.doc = json.load(f)
        cls.entries = cls.doc["entries"]

    def test_shape(self):
        self.assertIsInstance(self.entries, list)
        for e in self.entries:
            self.assertEqual(set(e), KEYS, e.get("id"))

    def test_ids_unique_and_storable(self):
        ids = [e["id"] for e in self.entries]
        self.assertEqual(len(ids), len(set(ids)), "an id is used twice")
        for i in ids:
            self.assertRegex(i, r"^[a-z0-9-]{3,64}$", i)

    def test_dates_iso_not_future_newest_first(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        dates = []
        for e in self.entries:
            d = datetime.date.fromisoformat(e["date"])
            self.assertLessEqual(d, tomorrow, "%s is dated in the future" % e["id"])
            dates.append(e["date"])
        self.assertEqual(dates, sorted(dates, reverse=True), "keep the newest entry first")

    def test_tags(self):
        for e in self.entries:
            self.assertIn(e["tag"], TAGS, e["id"])

    def test_one_short_sentence(self):
        for e in self.entries:
            t, x = e["title"].strip(), e["text"].strip()
            self.assertTrue(0 < len(t) <= 60, e["id"])
            self.assertFalse(t.endswith("."), "%s: the title gets its full stop on the page" % e["id"])
            self.assertTrue(x.endswith("."), "%s: text is one sentence ending in a full stop" % e["id"])
            self.assertLessEqual(len(x), 160, e["id"])
            self.assertNotRegex(x[:-1], r"[.!?]\s", "%s: one sentence only" % e["id"])

    def test_show_me_target(self):
        for e in self.entries:
            s = e["showMe"]
            if s is None:
                continue
            ok = s in TARGETS or re.match(r"^/medical-sales-hub/([a-z0-9-]+/)*(#[a-z0-9-]+)?$", s)
            self.assertTrue(ok, "%s: showMe %r is not a My Hub control or a Hub path" % (e["id"], s))

    def test_house_copy_rules(self):
        for e in self.entries:
            for k in ("title", "text"):
                v = e[k]
                for d in DASHES:
                    self.assertNotIn(d, v, "%s %s has a dash" % (e["id"], k))
                self.assertNotRegex(v.lower(), r"\bmed ?tech\b", e["id"])
                self.assertIsNone(US.search(v), "%s: US spelling %r" % (e["id"], US.search(v) and US.search(v).group(0)))
        for d in DASHES:
            self.assertNotIn(d, self.doc.get("_readme", ""))


if __name__ == "__main__":
    unittest.main(verbosity=1)
