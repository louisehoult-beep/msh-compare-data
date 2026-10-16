#!/usr/bin/env python3
"""test_crawl_manual_carry.py — a hand-captured product survives a re-crawl (^o524).

Offline, no fetches.   python3 test_crawl_manual_carry.py   exit 0 = pass
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as cs  # noqa: E402

MANUAL = {"n": "Yuwell Anytime CT-3 CGM System", "division": "Yuwell Anytime CGM",
          "manualCapture": {"sourceUrl": "https://www.urathon.com/yuwellanytime/",
                            "capturedDate": "2026-10-16"}}


def crawled():
    return {"divisions": [{"name": "Mobility Aids", "products": 1}],
            "products": [{"n": "Apollo Wheelchair AP", "division": "Mobility Aids"}]}


class CarryManualProducts(unittest.TestCase):
    def test_manual_product_survives_a_recrawl_that_does_not_find_it(self):
        out = cs.carry_manual_products({"products": [MANUAL]}, crawled())
        self.assertEqual([p["n"] for p in out["products"]],
                         ["Apollo Wheelchair AP", MANUAL["n"]])
        self.assertIn({"name": "Yuwell Anytime CGM", "products": 1}, out["divisions"])
        self.assertTrue(out["products"][1]["manualCapture"]["sourceUrl"])

    def test_not_duplicated_when_the_crawl_finds_it_too(self):
        shaped = crawled()
        shaped["products"].append({"n": "yuwell anytime ct-3 cgm system", "division": "Mobility Aids"})
        out = cs.carry_manual_products({"products": [MANUAL]}, shaped)
        self.assertEqual(len(out["products"]), 2)

    def test_crawled_products_that_were_not_manual_are_not_carried(self):
        out = cs.carry_manual_products({"products": [{"n": "Old Product", "division": "X"}]}, crawled())
        self.assertEqual(len(out["products"]), 1)

    def test_no_existing_record_is_fine(self):
        self.assertEqual(len(cs.carry_manual_products({}, crawled())["products"]), 1)

    def test_division_count_increments_when_division_exists(self):
        m = dict(MANUAL, division="Mobility Aids")
        out = cs.carry_manual_products({"products": [m]}, crawled())
        self.assertEqual(out["divisions"][0]["products"], 2)


class OutOfScopeRanges(unittest.TestCase):
    def shaped(self):
        return {"divisions": [{"name": "Uncategorised", "products": 3},
                              {"name": "Alle ACUVUE Kontaktlinsen", "products": 1}],
                "products": [{"n": "tecnis-eyhance", "division": "Uncategorised"},
                             {"n": "ACUVUE OASYS 1-Day", "division": "Uncategorised"},
                             {"n": "Lens Parameters", "division": "Uncategorised"},
                             {"n": "x", "division": "Alle ACUVUE Kontaktlinsen"}]}

    def test_contact_lens_range_is_dropped_for_the_surgical_entity(self):
        out = cs.drop_out_of_scope_ranges("Johnson & Johnson Surgical Vision", self.shaped())
        self.assertEqual([p["n"] for p in out["products"]], ["tecnis-eyhance"])
        self.assertEqual(out["divisions"], [{"name": "Uncategorised", "products": 1}])

    def test_other_suppliers_are_untouched(self):
        out = cs.drop_out_of_scope_ranges("Someone Else Ltd", self.shaped())
        self.assertEqual(len(out["products"]), 4)


if __name__ == "__main__":
    unittest.main()
