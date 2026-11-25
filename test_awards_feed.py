#!/usr/bin/env python3
"""Regression test for the awards feed gap (20/11/2026). Stdlib only, no network.

Find a Tender's "stages=" filter silently drops every Procurement Act 2023
notice (legalBasis 2023/54). Act award notices also carry their CPVs only on
awards[].items[] (no tender.classification, no tender.items), so headline_cpv()
read "" and relevant() dropped a medical award with a plain title. The fixture
is 107411-2026 (Manchester University NHS FT, MLPA reagents, MRC Holland,
£669,612, CPV 33696300) as read from the feed on 20/11/2026, contact details
removed.

    python3 test_awards_feed.py
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_awards as RA  # noqa: E402

with open(os.path.join(HERE, "tests", "fixtures", "fts-107411-2026-award-release.json"),
          encoding="utf-8") as fh:
    ACT_AWARD = json.load(fh)

OLD_REGIME = {
    "id": "107400-2026", "ocid": "ocds-h6vhtk-000002", "date": "2026-11-12T09:50:00Z",
    "tag": ["award"], "buyer": {"name": "Some NHS Trust"},
    "tender": {"title": "Wound care dressings", "status": "complete",
               "legalBasis": {"id": "32014L0024"},
               "classification": {"scheme": "CPV", "id": "33141110"}},
    "awards": [{"id": "1", "status": "active", "date": "2026-11-10T00:00:00Z",
                "value": {"amount": 1000.0, "currency": "GBP"},
                "suppliers": [{"name": "Acme Medical Ltd"}]}],
}

ACT_TENDER_NOT_AWARD = {
    "id": "107391-2026", "ocid": "ocds-h6vhtk-000003", "date": "2026-11-12T09:30:00Z",
    "tag": ["tender"], "tender": {"title": "Urology and Bowel Management",
                                 "status": "active", "legalBasis": {"id": "2023/54"}},
}


def fake_feed(releases):
    """Behaves as the live feed did on 20/11/2026: with a stages= filter only
    old-regime notices come back; without one, everything does."""
    calls = []

    def get(url, *a, **k):
        calls.append(url)
        if "stages=" in url:
            got = [r for r in releases
                   if (r["tender"].get("legalBasis") or {}).get("id") != "2023/54"]
        else:
            got = list(releases)
        return {"releases": copy.deepcopy(got), "links": {}}
    return get, calls


class FindATenderAwardsGap(unittest.TestCase):

    def setUp(self):
        self._get, self._sleep = RA.get, RA.time.sleep
        RA.time.sleep = lambda s: None

    def tearDown(self):
        RA.get, RA.time.sleep = self._get, self._sleep

    def test_fixture_is_an_act_award_with_cpv_only_on_award_items(self):
        t = ACT_AWARD["tender"]
        self.assertEqual(t["legalBasis"]["id"], "2023/54")
        self.assertNotIn("classification", t)
        self.assertFalse(t.get("items"))
        self.assertEqual(RA.headline_cpv(t), "")

    def test_headline_cpv_reads_award_items(self):
        self.assertEqual(RA.headline_cpv(ACT_AWARD["tender"], ACT_AWARD["awards"]), "33696300")
        self.assertTrue(RA.relevant(ACT_AWARD["tender"], ACT_AWARD["tender"]["title"],
                                    ACT_AWARD["awards"]))

    def test_act_award_row_built_from_awards(self):
        rows = RA.rows_from_release(ACT_AWARD, "Find a Tender", "tender-awards")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["noticeSupplierName"], "MRC Holland")
        self.assertEqual(r["buyer"], "Manchester University NHS Foundation Trust")
        self.assertEqual(r["valueAmount"], 669612.0)
        self.assertEqual(r["valueCurrency"], "GBP")
        self.assertEqual(r["cpv"], "33696300")
        self.assertEqual(r["date"], "2026-11-12")
        self.assertEqual(r["periodStart"], "2026-11-24T00:00:00Z")
        self.assertEqual(r["url"], "https://www.find-tender.service.gov.uk/Notice/107411-2026")

    def test_fetch_fts_walks_unstaged_and_keeps_act_awards(self):
        RA.get, calls = fake_feed([ACT_AWARD, OLD_REGIME, ACT_TENDER_NOT_AWARD])
        rows, note, complete = RA.fetch_fts(8)
        self.assertTrue(complete)
        self.assertTrue(calls and all("stages=" not in u for u in calls), calls)
        names = sorted(r["noticeSupplierName"] for r in rows)
        self.assertEqual(names, ["Acme Medical Ltd", "MRC Holland"])
        self.assertIn("2 award release(s) among 3 release(s)", note)

    def test_republished_award_counted_once_newest_notice_wins(self):
        later = copy.deepcopy(ACT_AWARD)
        later["id"], later["date"] = "107416-2026", "2026-11-12T09:58:29Z"
        RA.get, _ = fake_feed([ACT_AWARD, later])
        rows, _, _ = RA.fetch_fts(8)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["url"].endswith("/107416-2026"))

    def test_cancelled_award_names_no_winner(self):
        dead = copy.deepcopy(ACT_AWARD)
        dead["awards"][0]["status"] = "cancelled"
        self.assertEqual(RA.rows_from_release(dead, "Find a Tender", "tender-awards"), [])

    def test_zero_value_is_not_stated_value(self):
        z = copy.deepcopy(ACT_AWARD)
        z["awards"][0]["value"] = {"amount": 0, "currency": "GBP"}
        rows = RA.rows_from_release(z, "Find a Tender", "tender-awards")
        self.assertIsNone(rows[0]["valueAmount"])

    def test_supplier_name_that_is_a_personal_email_is_dropped(self):
        e = copy.deepcopy(ACT_AWARD)
        e["awards"][0]["suppliers"] = [{"name": "matthew.wood7@nhs.net"}, {"name": "MRC Holland"}]
        rows = RA.rows_from_release(e, "Find a Tender", "tender-awards")
        self.assertEqual([r["noticeSupplierName"] for r in rows], ["MRC Holland"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
