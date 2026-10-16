#!/usr/bin/env python3
"""Discontinued lines still on formularies (16/10/2026): the curated listings, the join
to the speciality's local-intel items, the panel block and the renderer.

Stdlib only; builds in memory and writes nothing.

  python3 test_discontinued_on_formulary.py
"""
import copy
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
os.chdir(HERE)
import build_speciality_panels as B  # noqa: E402

STATUSES = {"recommended", "less-cost-effective", "non-formulary"}


def load(p):
    with open(os.path.join(HERE, p), encoding="utf-8") as fh:
        return json.load(fh)


DOC = load("data/discontinued-on-formulary.json")
LI = load("data/speciality-local-intel.json")
DT = {"schema": ["part", "supplier", "vmp", "amp", "size", "qty", "uom", "price", "bnf"],
      "effectiveMonth": "2026-10",
      "rows": [["IXA", "S", "Emollient", "Other cream", "", "500", "gram", "100", "21220000"]]}


class Data(unittest.TestCase):
    def test_every_listing_resolves_to_a_product_and_a_local_intel_item(self):
        prods = {p["id"] for p in DOC["products"]}
        ids = {i["id"] for v in LI["specialities"].values() for i in v}
        for slug, entries in DOC["specialities"].items():
            for e in entries:
                self.assertIn(e["product"], prods, e)
                self.assertIn(e["item"], ids, e)
                self.assertIn(e["status"], STATUSES, e)
                self.assertTrue(e["line"].strip() and e["position"].strip(), e)
                self.assertRegex(e["readOn"], r"^\d{4}-\d{2}-\d{2}$")

    def test_each_product_carries_its_dmd_record_and_pack_dates(self):
        for p in DOC["products"]:
            self.assertEqual(p["dmd"]["status"], "Discontinued")
            self.assertTrue(p["dmd"]["url"].startswith("https://dmd-browser.nhsbsa.nhs.uk/amp/view/"))
            self.assertTrue(p["dmd"]["packs"])
            for k in p["dmd"]["packs"]:
                self.assertRegex(k["discontinued"], r"^\d{4}-\d{2}-\d{2}$")

    def test_no_customer_is_named(self):
        text = json.dumps(DOC).lower()
        self.assertNotIn("ego ", text + " ")
        self.assertNotIn("ego pharm", text)

    def test_one_listing_per_item_and_product(self):
        seen = set()
        for e in DOC["specialities"]["dermatology"]:
            k = (e["item"], e["product"])
            self.assertNotIn(k, seen)
            seen.add(k)


class Build(unittest.TestCase):
    def test_join_uses_item_details_and_drops_withheld_items(self):
        li = B.build_local_intel("dermatology", LI)
        full = B.build_discontinued_on_formulary("dermatology", DOC, li, DT)
        self.assertEqual(len(full["listings"]), len(DOC["specialities"]["dermatology"]))
        victim = DOC["specialities"]["dermatology"][0]["item"]
        li2 = [i for i in li if i["id"] != victim]
        part = B.build_discontinued_on_formulary("dermatology", DOC, li2, DT)
        self.assertEqual(part["listingsDropped"], sum(1 for e in DOC["specialities"]["dermatology"] if e["item"] == victim))
        self.assertTrue(all(l["org"] for l in part["listings"]))

    def test_gone_source_is_withheld_through_local_intel(self):
        li = copy.deepcopy(LI)
        for it in li["specialities"]["dermatology"]:
            if it["id"] == "derm-gm":
                it["lastCheck"] = {"status": "gone"}
        out = B.build_discontinued_on_formulary("dermatology", DOC, B.build_local_intel("dermatology", li), DT)
        self.assertNotIn("Greater Manchester (GMMMG formulary)", {l["org"] for l in out["listings"]})

    def test_part_ix_presence_is_computed_not_stored(self):
        li = B.build_local_intel("dermatology", LI)
        out = B.build_discontinued_on_formulary("dermatology", DOC, li, DT)
        self.assertFalse(any(p["partIxListed"] for p in out["products"]))
        dt = copy.deepcopy(DT)
        dt["rows"].append(["IXA", "S", "x", "QV 5% skin lotion", "", "500", "ml", "1", "21220000"])
        out = B.build_discontinued_on_formulary("dermatology", DOC, li, dt)
        self.assertTrue([p for p in out["products"] if p["id"] == "qv-5-skin-lotion"][0]["partIxListed"])

    def test_no_entries_means_no_block(self):
        li = B.build_local_intel("dermatology", LI)
        self.assertIsNone(B.build_discontinued_on_formulary("renal", DOC, li, DT))

    def test_counts_add_up(self):
        li = B.build_local_intel("dermatology", LI)
        out = B.build_discontinued_on_formulary("dermatology", DOC, li, DT)
        for p in out["products"]:
            self.assertEqual(sum(p["counts"].values()), sum(1 for l in out["listings"] if l["product"] == p["id"]))


class Published(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = B.build("dermatology", B.load_sources())

    def test_live_panel_carries_block_and_rule(self):
        self.assertIn("discontinuedOnFormulary", self.panel)
        self.assertIn("discontinuedOnFormulary", self.panel["rules"])
        self.assertIn("Dictionary of Medicines and Devices (dm+d)", self.panel["rules"]["discontinuedOnFormulary"])
        self.assertNotIn("[[", self.panel["rules"]["discontinuedOnFormulary"])

    def test_other_panels_carry_nothing(self):
        p = B.build("renal", B.load_sources())
        self.assertNotIn("discontinuedOnFormulary", p)
        self.assertNotIn("discontinuedOnFormulary", p["rules"])


class Wiring(unittest.TestCase):
    def test_renderer_reads_block_and_rule(self):
        js = open(os.path.join(HERE, "app", "speciality-panels.js"), encoding="utf-8").read()
        self.assertIn("d.discontinuedOnFormulary", js)
        self.assertIn("'discontinuedOnFormulary'", js)

    def test_data_file_is_stamped(self):
        self.assertIn("ref", DOC["_notice"])


if __name__ == "__main__":
    unittest.main()
