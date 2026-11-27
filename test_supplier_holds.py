#!/usr/bin/env python3
"""test_supplier_holds.py — a ruled hold is never crawled or republished.

Offline, no fetches.   python3 test_supplier_holds.py   exit 0 = pass
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, HERE)
import crawl_supplier_site as cs  # noqa: E402
import verify  # noqa: E402

HOLD = {"heldOn": "2026-11-27", "policy": "p"}


def doc(products=None, publishable=None):
    h = dict(HOLD, publishable=publishable) if publishable else dict(HOLD)
    d = {"_meta": {"holds": {"X": h}}, "suppliers": {}}
    if products is not None:
        d["suppliers"]["X"] = {"products": [{"n": n} for n in products]}
    return d


def failures(d):
    before = len(verify.fails)
    verify.check_held_ranges(d)
    out = verify.fails[before:]
    del verify.fails[before:]
    return out


class Holds(unittest.TestCase):
    def test_hold_found_by_exact_name_only(self):
        self.assertTrue(cs.hold_for(doc(), "X"))
        self.assertIsNone(cs.hold_for(doc(), "X Ltd"))
        self.assertIsNone(cs.hold_for({}, "X"))

    def test_absent_range_passes(self):
        self.assertEqual(failures(doc()), [])

    def test_republished_range_fails(self):
        self.assertTrue(failures(doc(products=["a"])))
        self.assertTrue(failures(doc(products=[])))

    def test_only_publishable_products_pass(self):
        self.assertEqual(failures(doc(["a"], publishable=["a"])), [])
        self.assertTrue(failures(doc(["a", "b"], publishable=["a"])))


if __name__ == "__main__":
    unittest.main()
