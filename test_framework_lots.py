#!/usr/bin/env python3
"""test_framework_lots.py — the lot rule on framework cards (Lou, 30/09/2026:
"When they are on a framework I want the company profile to pull the lots too").

Proves three things stay true:
  1. the lot readers in scripts/refresh_framework_lots.py read the shapes NHS
     Supply Chain actually publishes, and refuse the shapes that only look like
     them (a product-area sheet, a "Product training" row, prose mentioning a lot);
  2. a lot-source name attaches to a brief supplier only under the stated rule —
     normalised-name equality or a recorded alias — never by similarity;
  3. verify.py's framework-lots gate fails a framework whose owner publishes
     lots but whose record carries none, and a lot keyed to a name the brief
     does not use.

    python3 test_framework_lots.py
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, REPO)

import refresh_framework_lots as L  # noqa: E402
import verify  # noqa: E402


class LotLabels(unittest.TestCase):
    def test_normalises(self):
        self.assertEqual(L.lot_label("Lot One"), "Lot 1")
        self.assertEqual(L.lot_label("Lot 01 Digital"), "Lot 1")
        self.assertEqual(L.lot_label("LOT 1.10 - Graft"), "Lot 1.10")
        self.assertEqual(L.lot_label("Lot 4a"), "Lot 4a")
        self.assertIsNone(L.lot_label("Lots Awarded To"))
        self.assertIsNone(L.lot_label("Supplier"))


ROBOTIC = """<div id="suppliers"><h2>Suppliers</h2>
<p>The following suppliers are awarded on this framework (by lot):</p>
<p><strong>Lot 1</strong></p><ul><li>CMR Surgical Ltd</li><li>Medtronic Limited</li></ul>
<p><strong>Lot 2</strong></p><ul><li>Medtronic Limited</li></ul>
<p><strong>Lot 3&nbsp;</strong></p><ul><li>MCT Lifesciences Ltd <strong>(New to framework)</strong></li></ul>
</div><div id="categories"><p>There are 3 lots on this framework:</p>
<ul><li>Lot 1: Surgical Robots</li><li>Lot 2: Spinal Robots</li><li>Lot 3: Freestanding Arms</li></ul></div>
<div id="benefits"></div>"""

PROSE = """<div id="suppliers"><p>There are 3 suppliers on this framework. They are:</p>
<ul><li>Abbott</li><li>Ypsomed Ltd</li></ul>
<p>The following suppliers are being delisted:</p><ul><li>CamDiab Ltd</li></ul>
<p>CamDiab's algorithm that sits in Lot 3 is now available from Ypsomed.</p></div>
<div id="benefits"></div>"""


class BriefReaders(unittest.TestCase):
    def test_lot_lists(self):
        got = L.parse_brief_lot_lists(ROBOTIC)
        self.assertEqual(got["Medtronic Limited"], {"Lot 1", "Lot 2"})
        self.assertEqual(got["MCT Lifesciences Ltd"], {"Lot 3"})

    def test_prose_mentioning_a_lot_is_not_a_split(self):
        self.assertEqual(L.parse_brief_lot_lists(PROSE), {})

    def test_titles_and_stated_count(self):
        self.assertEqual(L.parse_lot_titles(ROBOTIC)["Lot 2"], "Spinal Robots")
        self.assertEqual(L.stated_lot_count(ROBOTIC), 3)


class MatrixReaders(unittest.TestCase):
    def test_header_with_spanning_lot(self):
        rows = [["Supplier Name", "Lot 1 - Single Use", "", "Lot 2 - Reusable"],
                ["Acme Ltd", "X", "", ""],
                ["Beta Ltd", "", "X", "X"],
                ["Gamma Ltd", "No", "", "-"]]
        got = L.parse_matrix_header_lots(rows)
        self.assertEqual(got["Acme Ltd"], {"Lot 1"})
        self.assertEqual(got["Beta Ltd"], {"Lot 1", "Lot 2"})   # col 2 sits under Lot 1's span
        self.assertNotIn("Gamma Ltd", got)

    def test_sections_ignore_a_product_training_row(self):
        rows = [["", "Product", "Acme Ltd", "Beta Ltd"],
                ["Lot 1 - Curtains", "Cubicle curtains", "Yes", "No"],
                ["", "Product training", "Yes", "Yes"],
                ["Lot 2 - Tracks", "Cubicle tracks", "No", "Yes"]]
        got = L.parse_matrix_sections(rows, "Product Matrix")
        self.assertEqual(got["Acme Ltd"], {"Lot 1"})
        self.assertEqual(got["Beta Ltd"], {"Lot 1", "Lot 2"})
        self.assertNotIn("Yes", got)

    def test_lot_rows_reconcile_to_brief_numbering(self):
        titles = {"Lot 1.1": "Dialysis Consumables and Equipment", "Lot 2": "CRRT"}
        self.assertEqual(L.reconcile_lot("Lot 1 - Dialysis Consumables and Equipment", titles), "Lot 1.1")
        self.assertEqual(L.reconcile_lot("Lot 2 - CRRT", titles), "Lot 2")
        # a finer source sub-lot is never folded into the brief's coarser lot
        self.assertEqual(L.reconcile_lot("Lot 1b - General Use Bandages", {"Lot 1": "General Use Bandages"}), "Lot 1b")


class NameRule(unittest.TestCase):
    def test_exact_normalised_only(self):
        brief = ["B. Braun Medical Limited", "Blatchford Limited", "Vantive Limited"]
        src = {"B Braun Medical Ltd": {"Lot 1"}, "Blatchford Limted": {"Lot 2"},
               "Baxter Healthcare Ltd": {"Lot 1"}}
        lots, unresolved = L.attach_names(src, brief, lambda n: None)
        self.assertEqual(lots, {"B. Braun Medical Limited": ["Lot 1"]})
        self.assertEqual(sorted(u["name"] for u in unresolved),
                         ["Baxter Healthcare Ltd", "Blatchford Limted"])

    def test_recorded_alias(self):
        brief = ["HARTMANN"]
        alias = {"hartmann": "Paul Hartmann", "paul hartmann ltd": "Paul Hartmann"}
        lots, unresolved = L.attach_names({"Paul Hartmann Ltd": {"Lot 3"}}, brief,
                                          lambda n: alias.get(n.lower()))
        self.assertEqual(lots, {"HARTMANN": ["Lot 3"]})
        self.assertEqual(unresolved, [])


class FindATender(unittest.TestCase):
    def test_call_off_linked_from_the_tender_is_refused(self):
        entry = {"kind": "f03", "title": "Hand Hygiene and Associated Products and Services",
                 "releases": [{"id": "006082-2026", "title": "PPE Mini Competition Hand Hygiene",
                               "lots": [["1", None]],
                               "awards": [[["1"], ["Ecolab Ltd"], "active", "a1"]]}]}
        self.assertEqual(L.fts_award_releases(entry, {"Lot 1": "Hand Rubs", "Lot 2": "Soaps"}), [])

    def test_framework_award_read_by_lot(self):
        entry = {"kind": "f03", "title": "Urology and Bowel Management",
                 "releases": [{"id": "032330-2023", "title": "Urology and Bowel Management",
                               "lots": [["12", "Stoma Appliances"], ["13", "Stoma accessories"]],
                               "awards": [[["12"], ["Hollister Limited"], "active", "a"],
                                          [["13"], ["Hollister Limited"], "active", "b"],
                                          [["13"], ["Gone Ltd"], "cancelled", "c"]]}]}
        titles = {"Lot 12": "Stoma Appliances", "Lot 13": "Stoma Accessories"}
        got, ids = L.parse_fts_awards(L.fts_award_releases(entry, titles), titles)
        self.assertEqual(got, {"Hollister Limited": {"Lot 12", "Lot 13"}})
        self.assertEqual(ids, ["032330-2023"])

    def test_single_lot_award_is_not_a_lot_split(self):
        entry = {"kind": "f03", "title": "CVC", "releases": [{"id": "x", "title": "CVC", "lots": [["1", None]],
                                                              "awards": [[["1"], ["A Ltd", "B Ltd"], "active", "a"]]}]}
        self.assertEqual(L.parse_fts_awards(L.fts_award_releases(entry, {}), {}), ({}, []))

    def test_partial_fts_file_keeps_an_award_it_does_not_contain(self):
        # 30/09/2026: an --fts file holding only NEW awards used to drop every award
        # already read, because a framework missing from the file never reached the
        # carry-forward branch.
        fw = {"name": "Urology", "url": "u", "reference": "2023/S 000-032330",
              "suppliers": ["Hollister Limited"]}
        prev = {"lotTitles": {"Lot 12": "Stoma Appliances"},
                "sources": [{"kind": "fts-award", "url": "x", "label": "award",
                             "coversLots": ["Lot 12"], "suppliersWithLots": 1}],
                "lotsBySource": {"fts-award": {"Hollister Limited": ["Lot 12"]}}}
        rec = L.build_one(fw, "", lambda n: None, None, {"999999-2025": {}}, prev)
        self.assertEqual(rec["supplierLots"], {"Hollister Limited": ["Lot 12"]})
        self.assertEqual(rec["status"], "published")


def run_gate(fw, lots_doc, js="function fwLotLine(){} lot not published by"):
    verify.fails.clear()
    verify.warns.clear()
    verify.check_framework_lots({"frameworks": [fw]}, lots_doc, js)
    return [m for c, m in verify.fails if c == "framework-lots"]


class Gate(unittest.TestCase):
    URL = "https://example/brief/"

    def fw(self, **kw):
        base = {"name": "Test FW", "url": self.URL, "suppliers": ["Acme Ltd", "Beta Ltd"],
                "supplierSource": "count verified", "lotStatus": "published",
                "supplierLots": {"Acme Ltd": ["Lot 1"]}}
        base.update(kw)
        return base

    def lots(self, supplierLots):
        return {"frameworks": {self.URL: {"status": "published" if supplierLots else "notPublished",
                                          "supplierLots": supplierLots, "unresolved": []}}}

    def test_clean_passes(self):
        self.assertEqual(run_gate(self.fw(), self.lots({"Acme Ltd": ["Lot 1"]})), [])

    def test_source_publishes_but_record_has_none(self):
        fails = run_gate(self.fw(supplierLots=None), self.lots({"Acme Ltd": ["Lot 1"]}))
        self.assertTrue(any("publishes supplier-by-lot" in m for m in fails), fails)

    def test_brief_lot_table_but_record_has_none(self):
        fails = run_gate(self.fw(supplierLots=None, lotStatus="notPublished",
                                 supplierSource="read from the page's lot table"), self.lots({}))
        self.assertTrue(any("publishes supplier-by-lot" in m for m in fails), fails)

    def test_stray_key(self):
        fails = run_gate(self.fw(supplierLots={"ACME LIMITED": ["Lot 1"]}), self.lots({"ACME LIMITED": ["Lot 1"]}))
        self.assertTrue(any("not a supplier the brief names" in m for m in fails), fails)

    def test_missing_status(self):
        fails = run_gate(self.fw(lotStatus=None), self.lots({"Acme Ltd": ["Lot 1"]}))
        self.assertTrue(any("no lotStatus" in m for m in fails), fails)

    def test_renderer_lost_empty_state(self):
        fails = run_gate(self.fw(), self.lots({"Acme Ltd": ["Lot 1"]}), js="nothing here")
        self.assertTrue(any("fwLotLine" in m for m in fails), fails)


if __name__ == "__main__":
    unittest.main(verbosity=1)
