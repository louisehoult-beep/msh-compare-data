#!/usr/bin/env python3
"""scripts/refresh_company_digital_awards.py: the digital awards layer (20/10/2026).

Proves the three things the layer exists for: a lane award reaches the company the
exact-only rule names; an unresolved name is quarantined, never guessed; and a
notice already in the CPV 33 medical feed for that company is not repeated.

  python3 test_company_digital_awards.py        exit 0 = the layer holds
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import refresh_company_digital_awards as R  # noqa: E402

SEED = {"suppliers": [{"name": "Tortus", "aliases": ["Tortus", "Tortus AI Ltd"]},
                      {"name": "Sectra Limited", "aliases": ["Sectra Limited"]}]}


def lane(*awards):
    return {"laneRule": "r", "clinicalRule": "c", "dataAsOf": "20/10/2026", "awards": list(awards)}


def award(url, *suppliers, stage="award"):
    return {"stage": stage, "title": "T " + url, "buyer": "X NHS Trust", "published": "2026-10-01",
            "url": url, "suppliers": list(suppliers), "value": 1000.0,
            "digitalCpv": ["48000000"], "clinical": False, "lane": "digital"}


class Layer(unittest.TestCase):
    def test_exact_alias_attaches(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/1", "TORTUS AI LTD")), {}, {})
        self.assertEqual([r["noticeSupplierName"] for r in doc["companies"]["Tortus"]], ["TORTUS AI LTD"])
        self.assertEqual(doc["matchRule"], R.company_match.RULE)

    def test_unresolved_is_quarantined(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/2", "Tortus Health Ltd")), {}, {})
        self.assertEqual(doc["companies"], {})
        self.assertEqual(doc["counts"]["unmatched"], 1)

    def test_medical_feed_notice_not_repeated(self):
        url = "https://www.find-tender.service.gov.uk/Notice/3"
        medical = {"companies": {"Sectra Limited": [{"url": url}]}}
        doc = R.build(SEED, lane(award(url, "Sectra Limited")), medical, {})
        self.assertNotIn("Sectra Limited", doc["companies"])
        self.assertEqual(doc["counts"]["alreadyInMedicalFeed"], 1)

    def test_non_award_stages_ignored(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/4", "Sectra Limited",
                                       stage="planning")), {}, {})
        self.assertEqual(doc["counts"]["awardRows"], 0)

    def test_published_rows_are_carried_forward(self):
        url = "https://www.find-tender.service.gov.uk/Notice/5"
        first = R.build(SEED, lane(award(url, "Sectra Limited")), {}, {})
        later = R.build(SEED, lane(), {}, first)
        self.assertEqual(len(later["companies"]["Sectra Limited"]), 1)

    def test_every_row_is_a_lane_row(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/6", "Sectra Limited")), {}, {})
        self.assertTrue(all(r["lane"] == "digital" for rows in doc["companies"].values() for r in rows))


if __name__ == "__main__":
    unittest.main()
