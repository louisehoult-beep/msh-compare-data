#!/usr/bin/env python3
"""Drug Tariff price-move alerts (16/10/2026): snapshot recording, the month-on-month
diff, the panel block, the renderer and the workflow wiring.

Stdlib only; builds in memory and writes nothing.

  python3 test_tariff_moves.py
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
import tariff_snapshots as T  # noqa: E402

SCHEMA = ["part", "supplier", "vmp", "amp", "size", "qty", "uom", "price", "bnf"]
RULE = {"tariffParts": ("IXA",), "tariffBnf": ("2122",), "tariffMoves": True}


def row(sup, amp, qty, price, bnf="21220000", part="IXA"):
    return [part, sup, "Emollient " + amp, amp, "", qty, "gram", str(price), bnf]


def dt(month, rows):
    return {"schema": SCHEMA, "effectiveMonth": month, "dataAsOf": month + "-15",
            "sourcePage": "https://example.test", "rows": rows}


def snaps_for(month_to_rows):
    s = {}
    for m, rows in month_to_rows.items():
        T.record(s, dt(m, rows), {"x": RULE})
    return s


class Diff(unittest.TestCase):
    def test_price_rise_fall_new_and_dropped(self):
        sept = [row("A", "a1", "500", 100), row("A", "a2", "500", 200),
                row("B", "b1", "100", 300), row("B", "b2", "100", 400)]
        octo = [row("A", "a1", "500", 101), row("A", "a2", "500", 190),
                row("B", "b1", "100", 300), row("C", "c1", "50", 500)]
        snaps = snaps_for({"2026-09": sept})
        m = B.build_tariff_moves("x", RULE, dt("2026-10", octo), snaps)
        self.assertEqual((m["previousMonth"], m["currentMonth"]), ("2026-09", "2026-10"))
        self.assertEqual((m["upCount"], m["downCount"], m["unchanged"]), (1, 1, 1))
        self.assertEqual((m["addedCount"], m["droppedCount"]), (1, 1))
        up = [x for x in m["moves"] if x["product"] == "a1"][0]
        self.assertEqual((up["was"], up["now"], up["pct"]), (1.0, 1.01, 1.0))
        dn = [x for x in m["moves"] if x["product"] == "a2"][0]
        self.assertEqual((dn["was"], dn["now"], dn["pct"]), (2.0, 1.9, -5.0))
        self.assertEqual(m["moves"][0]["product"], "a2")  # largest absolute move first
        self.assertEqual(m["dropped"][0]["product"], "b2")

    def test_pack_size_is_part_of_the_key(self):
        sept = [row("A", "a1", "500", 100), row("A", "a1", "100", 30)]
        octo = [row("A", "a1", "500", 100), row("A", "a1", "100", 31)]
        m = B.build_tariff_moves("x", RULE, dt("2026-10", octo), snaps_for({"2026-09": sept}))
        self.assertEqual(m["movedCount"], 1)
        self.assertEqual(m["moves"][0]["qty"], "100")

    def test_no_change_is_an_honest_result(self):
        rows = [row("A", "a1", "500", 100)]
        m = B.build_tariff_moves("x", RULE, dt("2026-10", rows), snaps_for({"2026-09": rows}))
        self.assertEqual((m["movedCount"], m["unchanged"]), (0, 1))

    def test_no_earlier_month_means_no_block(self):
        rows = [row("A", "a1", "500", 100)]
        self.assertIsNone(B.build_tariff_moves("x", RULE, dt("2026-10", rows), snaps_for({"2026-10": rows})))
        self.assertIsNone(B.build_tariff_moves("x", RULE, dt("2026-10", rows), None))

    def test_not_opted_in_means_no_block(self):
        rows = [row("A", "a1", "500", 100)]
        r = dict(RULE, tariffMoves=False)
        self.assertIsNone(B.build_tariff_moves("x", r, dt("2026-10", rows), snaps_for({"2026-09": rows})))

    def test_uses_latest_earlier_month_not_a_later_one(self):
        s = snaps_for({"2026-08": [row("A", "a1", "500", 90)], "2026-09": [row("A", "a1", "500", 100)],
                       "2026-11": [row("A", "a1", "500", 999)]})
        m = B.build_tariff_moves("x", RULE, dt("2026-10", [row("A", "a1", "500", 110)]), s)
        self.assertEqual(m["previousMonth"], "2026-09")
        self.assertEqual(m["moves"][0]["was"], 1.0)

    def test_duplicate_keys_are_left_out_not_guessed(self):
        sept = [row("A", "a1", "500", 100), row("A", "a1", "500", 150)]
        octo = [row("A", "a1", "500", 101), row("A", "a1", "500", 150)]
        m = B.build_tariff_moves("x", RULE, dt("2026-10", octo), snaps_for({"2026-09": sept}))
        self.assertEqual((m["ambiguousCount"], m["movedCount"]), (1, 0))

    def test_slice_only_lines_outside_the_bnf_section_are_ignored(self):
        sept = [row("A", "a1", "500", 100), row("Z", "dressing", "1", 10, bnf="20030100113")]
        octo = [row("A", "a1", "500", 100), row("Z", "dressing", "1", 99, bnf="20030100113")]
        m = B.build_tariff_moves("x", RULE, dt("2026-10", octo), snaps_for({"2026-09": sept}))
        self.assertEqual(m["movedCount"], 0)


class Snapshots(unittest.TestCase):
    def test_record_is_idempotent_and_keeps_earlier_months_fixed(self):
        s = snaps_for({"2026-09": [row("A", "a1", "500", 100)]})
        frozen = copy.deepcopy(s["slices"]["x"]["months"]["2026-09"])
        T.record(s, dt("2026-10", [row("A", "a1", "500", 101)]), {"x": RULE})
        T.record(s, dt("2026-10", [row("A", "a1", "500", 102)]), {"x": RULE})
        months = s["slices"]["x"]["months"]
        self.assertEqual(months["2026-09"], frozen)
        self.assertEqual(len(months["2026-10"]["rows"]), 1)
        self.assertEqual(months["2026-10"]["rows"][0][-2], "102")

    def test_keeps_only_the_last_few_months(self):
        s = {}
        for i in range(1, 8):
            T.record(s, dt("2026-%02d" % i, [row("A", "a1", "500", 100 + i)]), {"x": RULE})
        self.assertEqual(sorted(s["slices"]["x"]["months"]), ["2026-04", "2026-05", "2026-06", "2026-07"])

    def test_refuses_an_empty_slice(self):
        with self.assertRaises(SystemExit):
            T.record({}, dt("2026-10", [row("Z", "d", "1", 1, bnf="20030100113")]), {"x": RULE})

    def test_only_opted_in_specialities_are_recorded(self):
        s = {}
        touched = T.record(s, dt("2026-10", [row("A", "a1", "500", 1)]), {"x": RULE, "y": dict(RULE, tariffMoves=False)})
        self.assertEqual(touched, ["x"])


class Published(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = B.load_sources()
        cls.panel = B.build("dermatology", cls.src)

    def test_dermatology_carries_the_block_with_its_rule(self):
        m = self.panel["drugTariffMoves"]
        self.assertIn("drugTariffMoves", self.panel["rules"])
        self.assertLess(m["previousMonth"], m["currentMonth"])
        self.assertEqual(m["linesCompared"], m["unchanged"] + m["movedCount"])
        self.assertEqual(m["movedCount"], m["upCount"] + m["downCount"])

    def test_every_move_is_a_real_difference_in_both_months(self):
        m = self.panel["drugTariffMoves"]
        for x in m["moves"]:
            self.assertNotEqual(x["was"], x["now"])
            self.assertAlmostEqual(x["pct"], round((x["now"] - x["was"]) / x["was"] * 100, 1), places=1)

    def test_other_panels_carry_no_block(self):
        p = B.build("tissue-viability-and-wound-care", self.src)
        self.assertNotIn("drugTariffMoves", p)
        self.assertNotIn("drugTariffMoves", p["rules"])

    def test_rule_text_makes_no_launch_or_discontinuation_claim(self):
        t = self.panel["rules"]["drugTariffMoves"]
        self.assertIn("neither is described as launched or discontinued", t)


class Wiring(unittest.TestCase):
    def read(self, p):
        with open(os.path.join(HERE, p), encoding="utf-8") as fh:
            return fh.read()

    def test_workflow_records_the_snapshot_and_commits_it(self):
        w = self.read(".github/workflows/drug-tariff.yml")
        self.assertIn("python3 scripts/tariff_snapshots.py", w)
        for line in w.splitlines():
            if line.strip().startswith("git add data/drug-tariff-part-ix.json"):
                self.assertIn("data/tariff-snapshots.json", line)

    def test_renderer_reads_the_block_and_its_rule(self):
        js = self.read("app/speciality-panels.js")
        self.assertIn("d.drugTariffMoves", js)
        self.assertIn("'drugTariffMoves'", js)

    def test_snapshot_file_is_stamped(self):
        d = json.load(open(os.path.join(HERE, "data", "tariff-snapshots.json"), encoding="utf-8"))
        self.assertIn("ref", d["_notice"])
        self.assertTrue(len(d["slices"]["dermatology"]["months"]) >= 2)


if __name__ == "__main__":
    unittest.main()
