#!/usr/bin/env python3
"""test_supplier_not_products.py — a page ruled not a product stays out.

Offline, no fetches.   python3 test_supplier_not_products.py   exit 0 = pass
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, HERE)
import crawl_supplier_site as cs  # noqa: E402
import verify  # noqa: E402


def row(n, d="Uncategorised"):
    return {"n": n, "division": d, "category": ""}


def doc(rows):
    return {"_meta": {"notProducts": {"X": [{"n": "Neck"}, {"n": "Cloth", "division": "Highlights"}]}},
            "suppliers": {"X": {"products": rows}}}


def failures(d):
    before = len(verify.fails)
    verify.check_not_products(d)
    out = verify.fails[before:]
    del verify.fails[before:]
    return out


class NotProducts(unittest.TestCase):
    def test_recapture_is_filtered_and_counts_follow(self):
        shaped = {"products": [row("neck", "Orthopaedics"), row("Cloth", "Highlights"), row("Cloth"),
                               row("Neck Brace")],
                  "filingRule": "3 of 4 product URLs carry no division segment."}
        removed = cs.drop_non_products(doc([]), "X", shaped)
        self.assertEqual([p["n"] for p in removed], ["neck", "Cloth"])
        self.assertEqual([p["n"] for p in shaped["products"]], ["Cloth", "Neck Brace"])
        self.assertEqual(shaped["divisions"], [{"name": "Uncategorised", "products": 2}])
        self.assertFalse(shaped["hasDivisions"])
        self.assertIn("2 of 2 product URLs", shaped["filingRule"])

    def test_other_supplier_untouched(self):
        shaped = {"products": [row("Neck")]}
        self.assertEqual(cs.drop_non_products(doc([]), "X Ltd", shaped), [])
        self.assertEqual(len(shaped["products"]), 1)

    def test_gate(self):
        self.assertTrue(failures(doc([row("Neck")])))
        self.assertTrue(failures(doc([row("Cloth", "Highlights")])))
        self.assertEqual(failures(doc([row("Cloth")])), [])


if __name__ == "__main__":
    unittest.main()
