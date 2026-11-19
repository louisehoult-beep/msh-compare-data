#!/usr/bin/env python3
r"""Dermatology ICB context (scripts/build_derm_icb_context.py). Offline. Added 22/10/2026.

Holds data/derm-icb-context/context.json to its sources and to the panel it feeds:
1. 36 ICBs, each with an IMD figure; ICB codes match the explorer's ICB list.
2. RTT is dermatology (treatment function C_330) and every series has 13 months; months before
   an ICB existed are null, never filled.
3. Brand share reconciles: the brand's ICB items / the ICB's emollient items, from trends.json.
4. England dermatology waiting list in the latest month is at least the sum of ICB totals
   (the rest is the unknown-commissioner row) and within 3% of it.
5. IMD ranks are 1..36 with no gaps; rank 1 has the highest score.
6. PCN spread is only shown with enough PCNs; every figure block names source and period.
7. The panel JS carries the Not verified fallback and the source line.

  python3 test_derm_icb_context.py   exit 0 = holds
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    with open(os.path.join(HERE, p), encoding="utf-8") as fh:
        return json.load(fh)


C = load("data/derm-icb-context/context.json")
T = load("data/emollient-explorer/trends.json")


class Context(unittest.TestCase):
    def test_all_icbs(self):
        self.assertEqual(len(C["icbs"]), 36)
        self.assertEqual({i["code"] for i in C["icbs"]}, {i["code"] for i in T["icbs"]})
        for i in C["icbs"]:
            self.assertIsNotNone(i["imd"], i["code"])

    def test_rtt_is_dermatology_13_months(self):
        self.assertEqual(C["sources"]["rtt"]["treatmentFunctionCode"], "C_330")
        self.assertEqual(C["sources"]["rtt"]["treatmentFunction"], "Dermatology Service")
        self.assertEqual(len(C["periods"]["rtt"]), 13)
        for i in C["icbs"]:
            s = i["rtt"]
            if s is None:
                continue
            for k in ("total", "median", "w18pct", "w52"):
                self.assertEqual(len(s[k]), 13, i["code"])
            first = i["rttFirstMonth"]
            for p, v in zip(C["periods"]["rtt"], s["total"]):
                if p < first:
                    self.assertIsNone(v)
                else:
                    self.assertIsNotNone(v)
            for v in s["w18pct"]:
                self.assertTrue(v is None or 0 <= v <= 100)

    def test_share_reconciles(self):
        brand_idx = {b["name"]: k for k, b in enumerate(T["brands"])}
        for i in C["icbs"]:
            tot = sum(T["icbTotal"][i["code"]][-12:])
            self.assertEqual(i["marketItems12m"], tot)
            for bn, r in i["brands"].items():
                items = sum(sum(p["icb"].get(i["code"], [0] * 13)[-12:]) for p in T["products"] if p["b"] == brand_idx[bn])
                self.assertEqual(r["items12m"], items, (i["code"], bn))
                self.assertAlmostEqual(r["share"], round(100.0 * items / tot, 2), places=2)

    def test_england_total(self):
        e = C["england"]["total"][-1]
        s = sum(i["rtt"]["total"][-1] for i in C["icbs"] if i["rtt"])
        self.assertLessEqual(s, e)
        self.assertGreater(s, e * 0.97)

    def test_imd_ranks(self):
        r = sorted(i["imd"]["rank"] for i in C["icbs"])
        self.assertEqual(r, list(range(1, 37)))
        top = [i for i in C["icbs"] if i["imd"]["rank"] == 1][0]
        self.assertEqual(top["imd"]["score"], max(i["imd"]["score"] for i in C["icbs"]))

    def test_spread_needs_pcns(self):
        for i in C["icbs"]:
            for bn, r in i["brands"].items():
                if r["pcnSd"] is not None:
                    self.assertGreaterEqual(r["pcnN"], 5)
                    self.assertLessEqual(r["pcnMin"], r["pcnMax"])

    def test_sources_named(self):
        for k in ("rtt", "imd", "items"):
            self.assertTrue(C["sources"][k]["name"] and C["sources"][k]["measure"])
        self.assertTrue(C["periods"]["rtt"] and C["periods"]["items"])

    def test_panel_js(self):
        js = open(os.path.join(HERE, "app", "speciality-panels.js"), encoding="utf-8").read()
        self.assertIn("derm-icb-context", js)
        self.assertIn("Not verified", js)
        self.assertIn("C.sources.rtt.treatmentFunctionCode", js)
        self.assertIn("ms-opp-", js)


if __name__ == "__main__":
    unittest.main()
