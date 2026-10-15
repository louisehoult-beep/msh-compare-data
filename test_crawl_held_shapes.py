#!/usr/bin/env python3
"""test_crawl_held_shapes.py — the three shapes that held ten supplier re-crawls
on 09/10/2026 (^o635), and tidy_capture(), which now handles each one.

  1. Breadcrumb's last crumb is the product itself: one division per product
     (PDI 32/32, Macromed 44/44, Welland 47/43). Shown flat instead.
  2. FAQ questions read as products (Vitalograph). Dropped.
  3. Form-confirmation pages read as products ("Thanks", Insulet). Dropped.
Offline, no fetches.   python3 test_crawl_held_shapes.py   exit 0 = pass
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as cs                     # noqa: E402


def cap(rows):
    divs = {}
    for n, d in rows:
        divs[d] = divs.get(d, 0) + 1
    return {"products": [{"n": n, "division": d, "category": ""} for n, d in rows],
            "divisions": [{"name": k, "products": v} for k, v in divs.items()],
            "hasDivisions": True, "captureCaveat": "x."}


class HeldShapes(unittest.TestCase):
    def test_product_named_divisions_go_flat(self):
        rows = [("Prevantics® %d%% CHG Swab" % i, "Prevantics %d%% CHG Swab" % i) for i in range(20)]
        s, notes = cs.tidy_capture(cap(rows))
        self.assertFalse(s["hasDivisions"])
        self.assertEqual([d["name"] for d in s["divisions"]], ["Uncategorised"])
        self.assertEqual(len(s["products"]), 20)
        self.assertTrue(notes)

    def test_one_division_per_product_goes_flat(self):
        rows = [("Product %d" % i, "Range %d" % i) for i in range(12)]
        s, _ = cs.tidy_capture(cap(rows))
        self.assertFalse(s["hasDivisions"])

    def test_real_divisions_survive(self):
        rows = [("Item %d" % i, "Wound care" if i % 2 else "Continence") for i in range(20)]
        s, notes = cs.tidy_capture(cap(rows))
        self.assertEqual(notes, [])
        self.assertTrue(s["hasDivisions"])
        self.assertEqual(sorted(d["name"] for d in s["divisions"]), ["Continence", "Wound care"])

    def test_faq_and_thanks_dropped(self):
        rows = [("Does the Alpha require cleaning?", "U"), ("Thanks", "U"), ("Thank you", "U"),
                ("Disposable ECG Electrodes", "U"), ("Nose Clips with Foam Pads (200)", "U")]
        s, _ = cs.tidy_capture(cap(rows))
        self.assertEqual([p["n"] for p in s["products"]],
                         ["Disposable ECG Electrodes", "Nose Clips with Foam Pads (200)"])

    def test_main_applies_it(self):
        import inspect
        self.assertIn("tidy_capture(shaped)", inspect.getsource(cs.main))


if __name__ == "__main__":
    unittest.main()
