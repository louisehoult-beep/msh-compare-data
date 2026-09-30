#!/usr/bin/env python3
"""
test_awards_history.py — prove scripts/refresh_awards.py reads the award history
(data/tender-history.json) under the SAME exact-only match rule, and that
splitting a joined supplier string never loosens it.

WHY THIS EXISTS (30/09/2026). The Company Report read awards only from a rolling
8-day feed walk, so Hollister showed none while the history held its £1.98m
Solent NHS Trust stoma award and a place on NHS Scotland's "Stoma Acute Patient"
award (supplier string "Clinimed Limited, Coloplast Ltd, ConvaTec Ltd, Hollister
Ltd, Peak Medical Ltd, "). Each case below is that fix, or a way it could make a
false claim: a comma inside a legal name, a name cut off by the export's
80-character limit, a bare "Inc." piece, and the feed/history double count.

  python3 test_awards_history.py     exit 0 = pass. Stdlib only.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_awards as ra  # noqa: E402

SEED = {"suppliers": [
    {"name": "Hollister", "aliases": ["Hollister"]},
    {"name": "Coloplast", "aliases": []},
    {"name": "BD — Becton, Dickinson", "aliases": ["Becton, Dickinson U.K. Limited"]},
    {"name": "Becton", "aliases": []},
    {"name": "Biorep Technologies", "aliases": []},
    {"name": "Organon Pharma", "aliases": []},
    {"name": "Acme", "aliases": []},
    {"name": "Acme Medical", "aliases": []},
]}
SCHEMA = ["u", "s", "t", "b", "sup", "d", "spec", "v", "pe", "ms", "x"]
CF = "https://www.contractsfinder.service.gov.uk/Notice/"
FTS = "https://www.find-tender.service.gov.uk/Notice/"


def history(*rows):
    return {"schema": SCHEMA, "dataAsOf": "2026-09-29",
            "coverage": {"complete": False, "awardsFrom": "2015-12-01",
                         "note": "both feeds are therefore walked for notices published "
                                 "from 2021-01-01, and earlier ones are not fetched"},
            "rows": [list(r) for r in rows]}


def build(hist, feed_rows=()):
    return ra.assemble(list(feed_rows), SEED, None, None, ["test"], True, hist)


class HistoryIngest(unittest.TestCase):

    def test_single_supplier_attaches_as_contract_award(self):
        doc = build(history([CF + "3ccff227", "c", "Solent NHS Trust Stoma Care Provision",
                             "Solent NHS Trust", "Hollister Limited", "2023-08-03",
                             "unclassified", 1976585, "2026-06-30", None, None]))
        rows = doc["companies"]["Hollister"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["section"], "contract-awards")
        self.assertEqual(rows[0]["source"], "Contracts Finder")
        self.assertEqual(rows[0]["valueAmount"], 1976585)
        self.assertEqual(rows[0]["periodEnd"], "2026-06-30")  # expired awards stay

    def test_multi_supplier_string_is_split_then_matched_exactly(self):
        doc = build(history([FTS + "034511-2022", "f", "Stoma Acute Patient", "NSS",
                             "Clinimed Limited, Coloplast Ltd, ConvaTec Ltd, Hollister Ltd, "
                             "Peak Medical Ltd, ", "2022-12-06", "cardiology", None, None,
                             None, None]))
        self.assertEqual(doc["companies"]["Hollister"][0]["section"], "tender-awards")
        self.assertEqual(doc["companies"]["Hollister"][0]["noticeSupplierCount"], 5)
        self.assertIn("Coloplast", doc["companies"])
        names = sorted(r["noticeSupplierName"] for r in doc["unmatched"])
        self.assertEqual(names, ["Clinimed Limited", "ConvaTec Ltd", "Peak Medical Ltd"])

    def test_comma_inside_a_legal_name_is_not_split(self):
        doc = build(history([CF + "bd1", "c", "Cannulae", "Trust",
                             "Becton, Dickinson U.K. Limited", "2024-01-01", "x", 5000,
                             None, None, None]))
        self.assertIn("BD — Becton, Dickinson", doc["companies"])
        self.assertNotIn("Becton", doc["companies"])  # never split onto a namesake

    def test_bare_legal_form_piece_rejoins(self):
        self.assertEqual(ra.split_suppliers("Biorep Technologies, Inc."),
                         ["Biorep Technologies, Inc."])
        doc = build(history([CF + "bio", "c", "Kit", "Trust", "Biorep Technologies, Inc.",
                             "2024-01-01", "x", None, None, None, None]))
        self.assertIn("Biorep Technologies", doc["companies"])

    def test_cut_off_last_piece_is_quarantined_not_matched(self):
        sup = "Lupin Healthcare UK Ltd, Morningside Pharmaceuticals Limited, Organon Pharma (UK"
        self.assertEqual(len(sup), 80)
        doc = build(history([FTS + "org", "f", "Drugs", "NSS", sup, "2024-01-01", "x",
                             None, None, None, None]))
        self.assertNotIn("Organon Pharma", doc["companies"])
        cut = [r for r in doc["unmatched"] if "cuts supplier names" in r["reason"]]
        self.assertEqual([r["noticeSupplierName"] for r in cut], ["Organon Pharma (UK"])
        self.assertEqual(doc["counts"]["historySupplierCutOff"], 1)

    def test_uncapped_export_never_marks_an_80_char_name_cut(self):
        # 30/09/2026: the export stopped cutting names. When any supplier string in
        # the file runs past 80 characters, the file is uncapped, so an exactly-80
        # string is a whole name and is never quarantined as a fragment.
        sup = "Lupin Healthcare UK Ltd, Morningside Pharmaceuticals Limited, Organon Pharma (UK"
        long_sup = "A" * 120
        doc = build(history([FTS + "org", "f", "Drugs", "NSS", sup, "2024-01-01", "x",
                             None, None, None, None],
                            [FTS + "long", "f", "Other", "NSS", long_sup, "2024-01-02", "x",
                             None, None, None, None]))
        self.assertEqual(doc["counts"]["historySupplierCutOff"], 0)
        self.assertFalse([r for r in doc["unmatched"] if "cuts supplier names" in r["reason"]])

    def test_no_fuzzy_or_substring(self):
        doc = build(history([CF + "a1", "c", "Beds", "Trust", "Acme Medical Group Ltd",
                             "2024-01-01", "x", 10, None, None, None]))
        self.assertEqual(doc["companies"], {})
        self.assertEqual(len(doc["unmatched"]), 1)

    def test_feed_row_and_history_twin_count_once(self):
        feed = {"noticeSupplierName": "Hollister Limited", "title": "Stoma",
                "buyer": "Trust", "date": "2026-09-20", "url": CF + "zz",
                "source": "Contracts Finder", "section": "contract-awards",
                "valueAmount": 100, "valueCurrency": "GBP"}
        doc = build(history([CF + "zz", "c", "Stoma", "Trust", "Hollister Limited",
                             "2026-09-20", "x", 100, None, None, None]), [feed])
        self.assertEqual(len(doc["companies"]["Hollister"]), 1)
        self.assertEqual(doc["counts"]["historyAlreadyHeldFromFeeds"], 1)
        self.assertEqual(len(doc["_rows"]), 1)  # history is never copied into _rows

    def test_coverage_says_incomplete_and_names_the_floor(self):
        doc = build(history())
        cov = doc["coverage"]
        self.assertFalse(cov["complete"])
        self.assertIn("INCOMPLETE", cov["note"])
        self.assertEqual(cov["historyFrom"], "2021-01-01")

    def test_legacy_rows_take_their_section_from_the_url(self):
        doc = build(history([FTS + "076038-2026", "l", "Kit", "Board", "Hollister Ltd",
                             "2026-08-11", "x", None, None, None, None]))
        self.assertEqual(doc["companies"]["Hollister"][0]["section"], "tender-awards")

    def test_placeholder_values_are_null_not_zero(self):
        doc = build(history([CF + "v0", "c", "Kit", "Trust", "Hollister Ltd",
                             "2024-01-01", "x", 0, None, None, None]))
        self.assertIsNone(doc["companies"]["Hollister"][0]["valueAmount"])


if __name__ == "__main__":
    unittest.main()
