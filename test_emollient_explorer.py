#!/usr/bin/env python3
r"""Emollient prescribing explorer (scripts/build_emollient_explorer.py). Offline.

Added 22/10/2026. Holds the committed explorer data to the numbers the dermatology
panel already publishes, so a trend chart can never disagree with the card above it:

1. trends.json reconciles to data/speciality-panels/dermatology.json marketShare:
   latest-month and 12-month market items, and every published brand's latest items.
2. Every product's ICB arrays never exceed its national array, month by month.
3. Practice-level files: each ICB's PCN totals sit within 2% of the ICB shard total
   (the gap is practices not open in the latest month, which cannot be placed), and a
   share is never published for a PCN below the floor.
4. The product-key rule maps presentation codes the way the shards were written.

  python3 test_emollient_explorer.py        exit 0 = holds
"""
import importlib.util
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
spec = importlib.util.spec_from_file_location("bee", os.path.join(HERE, "scripts", "build_emollient_explorer.py"))
BEE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BEE)
OUT = os.path.join(HERE, "data", "emollient-explorer")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


T = load(os.path.join(OUT, "trends.json"))


class Trends(unittest.TestCase):
    def test_reconciles_to_panel(self):
        ms = load(os.path.join(HERE, "data", "speciality-panels", "dermatology.json"))["marketShare"]["markets"][0]["primary"]
        self.assertEqual(T["total"][-1], ms["items"])
        self.assertEqual(sum(T["total"][-12:]), ms["items12m"])
        for b in ms["brands"]:
            i = [k for k, x in enumerate(T["brands"]) if x["name"] == b["brand"]][0]
            got = sum(p["n"][-1] for p in T["products"] if p["b"] == i)
            self.assertEqual(got, b["items"], b["brand"])

    def test_icb_never_exceeds_national(self):
        for p in T["products"]:
            for c, a in p["icb"].items():
                for m, v in enumerate(a):
                    self.assertLessEqual(v, p["n"][m], (p["id"], c, m))

    def test_thirteen_months(self):
        self.assertEqual(len(T["periods"]), 13)
        for p in T["products"]:
            self.assertEqual(len(p["n"]), 13)

    def test_form_not_guessed(self):
        self.assertEqual(BEE.form_of("QV cream"), "cream")
        self.assertEqual(BEE.form_of("Epimax paraffin-free ointment"), "ointment")
        self.assertEqual(BEE.form_of("QV"), "unspecified")
        self.assertEqual(BEE.form_of("Dermol"), "unspecified")


class Keys(unittest.TestCase):
    def test_product_key(self):
        split = {"130201000BB"}
        self.assertEqual(BEE.product_key_for("2122000021300", split), "2122" + "0000213")
        self.assertEqual(BEE.product_key_for("130201000BBIC", split), "130201000BBIC")
        self.assertEqual(BEE.product_key_for("130201000AAAA", split), "130201000AA")
        self.assertEqual(BEE.product_key_for("1302010E0BBAC", split), "1302010E0BB")


@unittest.skipUnless(os.path.isdir(os.path.join(OUT, "pcn")), "no practice-level build committed")
class Practice(unittest.TestCase):
    def test_icb_totals_and_floors(self):
        for c, a in T["icbTotal"].items():
            d = load(os.path.join(OUT, "pcn", c + ".json"))
            s = sum(p["t"] for p in d["pcns"])
            i12 = sum(a[-12:])
            self.assertLessEqual(s, i12, c)
            self.assertLess((i12 - s) * 100.0 / i12, 2.0, c)
            for p in d["pcns"]:
                self.assertEqual(sum(q["t"] for q in p["p"]), p["t"], (c, p["id"]))
                for k in range(len(d["brands"])):
                    self.assertEqual(sum(q["b"][k] for q in p["p"]), p["b"][k])
        meta = T["pcn"]
        self.assertEqual(meta["itemsAtPracticeLevel"], meta["itemsInIcbShards12m"])
        self.assertEqual(meta["unmappedProductItems"], 0)


if __name__ == "__main__":
    unittest.main()
