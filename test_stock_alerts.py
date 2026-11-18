#!/usr/bin/env python3
"""Stock alerts feed (app/stock-alerts.js): the stapling / sutures / mesh filter over data/compare-issues.json.

    python3 test_stock_alerts.py
"""
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

NODE = r"""
const s = require(process.argv[1])._pure;
const doc = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const all = s.match(doc, 'stapling-sutures-mesh');
const two = s.match(doc, 'stapling-sutures');
console.log(JSON.stringify({
  all: all, two: two.map(x => x.id), sum: s.summary(all),
  bad: s.pickArea('zzz'),
  key: [s.sortKey({d: 'Aug 2026'}), s.sortKey({d: 'Aug 2026', firstSeen: '2026-08-19'}), s.sortKey({d: 'unknown'})],
  empty: s.summary(s.match({specialities: {}}, 'stapling-sutures')),
  esc: s.esc('<a href="x">&\'')
}));
"""


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Feed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run(["node", "-e", NODE, os.path.join(HERE, "app", "stock-alerts.js"),
                            os.path.join(HERE, "data", "compare-issues.json")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.o = json.loads(r.stdout)

    def test_known_notices_are_found(self):
        ids = {x["id"] for x in self.o["all"]}
        for must in ("ply-issues-johnson-johnson-medical-limited-surgical-sutures",
                     "n-medical-ltd-surgical-stapling-fge8405-fge8409-and-fge8418",
                     "tronic-limited-surgical-stapling-products-fgs183-and-fgs191"):
            self.assertIn(must, ids)

    def test_unrelated_notices_are_not(self):
        ids = {x["id"] for x in self.o["all"]}
        self.assertNotIn("kimal-bioflo-2026", ids)

    def test_every_item_has_a_notice_link_and_kind_and_no_duplicates(self):
        ids = [x["id"] for x in self.o["all"]]
        self.assertEqual(len(ids), len(set(ids)))
        for x in self.o["all"]:
            self.assertTrue(x["url"].startswith("https://"), x["id"])
            self.assertTrue(x["kinds"], x["id"])

    def test_newest_first(self):
        keys = [x["sort"] for x in self.o["all"]]
        self.assertEqual(keys, sorted(keys, reverse=True))

    def test_closed_flag_only_when_status_text_says_so(self):
        by = {x["id"]: x for x in self.o["all"]}
        self.assertTrue(by["tronic-limited-surgical-stapling-products-fgs183-and-fgs191"]["closed"])
        self.assertFalse(by["ply-issues-johnson-johnson-medical-limited-surgical-sutures"]["closed"])

    def test_two_area_is_a_subset_without_mesh_only_items(self):
        allids = {x["id"] for x in self.o["all"]}
        self.assertTrue(set(self.o["two"]) <= allids)

    def test_summary_and_edges(self):
        self.assertEqual(self.o["sum"]["total"], len(self.o["all"]))
        self.assertLessEqual(self.o["sum"]["open"], self.o["sum"]["total"])
        self.assertTrue(self.o["sum"]["latest"])
        self.assertEqual(self.o["bad"], "stapling-sutures-mesh")
        self.assertEqual(self.o["key"], ["2026-08-00", "2026-08-19", ""])
        self.assertEqual(self.o["empty"], {"total": 0, "open": 0, "latest": ""})
        self.assertNotIn("<", self.o["esc"])


if __name__ == "__main__":
    unittest.main()
