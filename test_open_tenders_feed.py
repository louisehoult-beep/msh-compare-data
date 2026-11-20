#!/usr/bin/env python3
"""Regression test for the open-tenders feed gap (20/11/2026). Stdlib only, no
network.

Find a Tender's "stages=" filter silently drops every Procurement Act 2023
notice, and those notices carry their CPVs only on tender.items[]. Together they
kept 107391-2026 (NHS Supply Chain, Urology and Bowel Management, £260m, closes
13/01/2027) out of data/open-tenders.json. The fixture is that notice's own
release, trimmed to one item, as read from the feed on 20/11/2026.

    python3 test_open_tenders_feed.py
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_open_tenders as OT  # noqa: E402

with open(os.path.join(HERE, "tests", "fixtures", "fts-107391-2026-release.json"),
          encoding="utf-8") as fh:
    ACT_TENDER = json.load(fh)

OLD_REGIME = {
    "id": "107409-2026", "ocid": "ocds-h6vhtk-000001", "date": "2026-11-12T09:53:51Z",
    "tag": ["tender"], "buyer": {"name": "Some NHS Trust"},
    "tender": {"title": "Wound care dressings", "status": "active",
               "legalBasis": {"id": "32014L0024"},
               "classification": {"scheme": "CPV", "id": "33141110"},
               "tenderPeriod": {"endDate": "2027-01-01T12:00:00+00:00"}},
}

TODAY = "2026-11-20"


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


class FindATenderGap(unittest.TestCase):

    def setUp(self):
        getattr(OT, "_FTS_WALKS", {}).clear()
        self._get, self._sleep = OT.get, OT.time.sleep
        OT.time.sleep = lambda s: None

    def tearDown(self):
        OT.get, OT.time.sleep = self._get, self._sleep
        getattr(OT, "_FTS_WALKS", {}).clear()

    def test_act_notice_headline_cpv_comes_from_items(self):
        self.assertEqual(OT.headline_cpv(ACT_TENDER["tender"]), "33125000")
        self.assertTrue(OT.relevant(ACT_TENDER["tender"], ACT_TENDER["tender"]["title"]))

    def test_old_regime_headline_unchanged(self):
        self.assertEqual(OT.headline_cpv(OLD_REGIME["tender"]), "33141110")

    def test_107391_2026_reaches_the_tender_rows(self):
        OT.get, calls = fake_feed([ACT_TENDER, OLD_REGIME])
        rows, note, complete = OT.fetch_fts(8, TODAY, stage="tender")
        urls = [r["url"] for r in rows]
        self.assertIn("https://www.find-tender.service.gov.uk/Notice/107391-2026", urls)
        self.assertIn("https://www.find-tender.service.gov.uk/Notice/107409-2026", urls)
        self.assertTrue(complete)
        self.assertTrue(calls and all("stages=" not in u for u in calls),
                        "Find a Tender must be walked without a stages= filter")
        row = rows[urls.index("https://www.find-tender.service.gov.uk/Notice/107391-2026")]
        self.assertEqual(row["closingDate"][:10], "2027-01-13")
        self.assertEqual(row["cpv"], "33125000")

    def test_one_walk_serves_both_stages(self):
        planned = copy.deepcopy(ACT_TENDER)
        planned.update(id="107398-2026", ocid="ocds-h6vhtk-000002", tag=["planning"])
        planned["tender"]["status"] = "planned"
        OT.get, calls = fake_feed([ACT_TENDER, planned])
        tender, _, _ = OT.fetch_fts(8, TODAY, stage="tender")
        planning, _, _ = OT.fetch_fts(8, TODAY, stage="planning")
        self.assertEqual([r["url"][-11:] for r in tender], ["107391-2026"])
        self.assertEqual([r["url"][-11:] for r in planning], ["107398-2026"])
        self.assertEqual(len(calls), 1, "the feed should be read once per run")

    def test_later_award_retires_the_open_release(self):
        awarded = copy.deepcopy(ACT_TENDER)
        awarded.update(id="120000-2026", date="2026-11-19T10:00:00Z", tag=["award"])
        awarded["tender"]["status"] = "complete"
        OT.get, _ = fake_feed([awarded, ACT_TENDER])
        rows, _, _ = OT.fetch_fts(8, TODAY, stage="tender")
        self.assertEqual(rows, [])


class ActNoticeValue(unittest.TestCase):
    """Act notices give amountGross, not amount, or put the value on lots.
    107391-2026 showed "-" on the Hub until 20/11/2026."""

    def test_107391_2026_shows_its_gross_value(self):
        row = OT.row_from_release(copy.deepcopy(ACT_TENDER), "Find a Tender", TODAY)
        self.assertEqual(row["valueAmount"], 260000000)
        self.assertEqual(row["valueCurrency"], "GBP")
        self.assertEqual(row["valueBasis"], "gross")

    def test_old_regime_net_amount_unchanged(self):
        t = {"value": {"amount": 5000, "amountGross": 6000, "currency": "GBP"}}
        self.assertEqual(OT.tender_value(t), (5000, "GBP", "net"))

    def test_lots_summed_when_no_tender_value(self):
        rel = copy.deepcopy(ACT_TENDER)
        rel["tender"].pop("value")
        rel["tender"]["lots"] = [
            {"id": "1", "value": {"amountGross": 160000000, "currency": "GBP"}},
            {"id": "2", "value": {"amount": 100000000, "currency": "GBP"}},
            {"id": "3"},
        ]
        row = OT.row_from_release(rel, "Find a Tender", TODAY)
        self.assertEqual((row["valueAmount"], row["valueBasis"]), (260000000, "lots"))

    def test_mixed_currency_lots_give_no_value(self):
        t = {"lots": [{"value": {"amount": 1, "currency": "GBP"}},
                      {"value": {"amount": 1, "currency": "EUR"}}]}
        self.assertEqual(OT.tender_value(t), (None, "", ""))

    def test_no_value_anywhere(self):
        self.assertEqual(OT.tender_value({}), (None, "", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
