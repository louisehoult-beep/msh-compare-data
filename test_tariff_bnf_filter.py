#!/usr/bin/env python3
"""A speciality's Drug Tariff slice is decided by NHSBSA's own BNF code, not the name.

Added 29/09/2026, after the dermatology panel was found to leave Ego
Pharmaceuticals out entirely.

THE BUG. build_tariff narrowed Part IXA by a regex on the virtual medicinal
product (VMP) description. NHSBSA lists many branded products with a VMP of
"Generic <brand name>": "Generic QV cream", "Generic QV Gentle wash", "Generic
QV Intensive ointment". Nothing in those names says emollient, so all five of
Ego's lines were invisible and the panel showed Cetraben and Hydromol, whose
VMPs happen to name the paraffin, as if they were the market.

THE FIX. Part IX carries NHSBSA's BNF code for every line, and NHSBSA files the
QV range under 21.22 alongside Cetraben and Hydromol. A rule that sets
`tariffBnf` is decided by that code; the name pattern is used only for a line
that arrives with no code at all.

These tests drive build_tariff with the REAL dermatology and ophthalmology rules
over synthetic rows copied from the September 2026 file, so they do not depend
on this month's data and do not rebuild any panel. Stdlib only.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import build_speciality_panels as B  # noqa: E402

SCHEMA = ["part", "supplier", "vmp", "amp", "size", "qty", "uom", "price", "bnf"]


def row(part, supplier, vmp, amp, price, bnf):
    return [part, supplier, vmp, amp, "", "1", "", str(price), bnf]


# Every row below is verbatim from NHSBSA Drug Tariff Part IX, September 2026
# (supplier, VMP, AMP, price in pence, BNF 15), one pack size each.
QV_LINES = [
    row("IXA", "Ego Pharmaceuticals", "Generic QV cream", "QV cream", 675, "21220000210"),
    row("IXA", "Ego Pharmaceuticals", "Generic QV Gentle wash", "QV Gentle wash", 560, "21220000211"),
    row("IXA", "Ego Pharmaceuticals", "Generic QV Intensive ointment", "QV Intensive ointment", 603, "21220000212"),
]
CETRABEN = row("IXA", "Thornton & Ross Ltd",
               "White soft paraffin 13.2% / Liquid paraffin light 10.5% cream",
               "Cetraben cream", 150, "21220000233")
# Not emollients, each a trap the name pattern was written around.
PARAFFIN_GAUZE = row("IXA", "Essity UK Ltd", "Paraffin gauze dressing sterile 10cm x 10cm",
                     "Cuticell Classic dressing 10cm x 10cm", 32, "20040200650")
CUREA = row("IXA", "GBUK Healthcare", "Generic Curea P1 dressing 10cm x 10cm square",
            "Curea P1 dressing 10cm x 10cm square", 126, "20031700136")
STOCKING = row("IXA", "Juzo UK Ltd", "Lymphoedema garments below knee closed toe",
               "Juzo Adventure class 1 (18-21mmHg) below knee closed toe lymphoedema "
               "garment extra short size I", 2990, "21270002698")


def tariff_for(slug, rows):
    doc = {"schema": SCHEMA, "rows": rows, "effectiveMonth": "2026-09"}
    return B.build_tariff(B.SPECIALITY_RULES[slug], doc)


class DermatologyByBnf(unittest.TestCase):
    def setUp(self):
        self.t = tariff_for("dermatology",
                            QV_LINES + [CETRABEN, PARAFFIN_GAUZE, CUREA, STOCKING])
        self.suppliers = {s["name"]: s["lines"] for s in self.t["topSuppliers"]}

    def test_rule_names_bnf_21_22(self):
        self.assertEqual(tuple(B.SPECIALITY_RULES["dermatology"]["tariffBnf"]), ("2122",))
        self.assertEqual(self.t["bnfFilter"], ["2122"])

    def test_the_name_pattern_alone_cannot_see_qv(self):
        # The failure this file exists for. If this ever passes, the pattern has
        # grown a brand list and the BNF rule should be re-examined, not deleted.
        rx = B.re.compile(B.SPECIALITY_RULES["dermatology"]["tariffVmp"], B.re.I)
        for r in QV_LINES:
            self.assertIsNone(rx.search(r[2]), r[2])

    def test_all_three_qv_lines_are_counted(self):
        self.assertEqual(self.suppliers.get("Ego Pharmaceuticals"), 3)

    def test_non_emollient_ixa_lines_are_not(self):
        for name in ("Essity UK Ltd", "GBUK Healthcare", "Juzo UK Ltd"):
            self.assertNotIn(name, self.suppliers)
        self.assertEqual(self.t["lineCount"], 4)

    def test_a_line_without_a_code_falls_back_to_the_pattern(self):
        uncoded_emollient = CETRABEN[:8] + [""]
        uncoded_brand = QV_LINES[0][:8] + [""]
        t = tariff_for("dermatology", [uncoded_emollient, uncoded_brand, PARAFFIN_GAUZE])
        self.assertEqual(t["lineCount"], 1)
        self.assertEqual(t["topSuppliers"], [{"name": "Thornton & Ross Ltd", "lines": 1}])

    def test_refuses_a_file_without_the_column(self):
        old = {"schema": SCHEMA[:8], "rows": [r[:8] for r in QV_LINES]}
        with self.assertRaises(SystemExit):
            B.build_tariff(B.SPECIALITY_RULES["dermatology"], old)

    def test_prices_are_pounds(self):
        self.assertEqual(self.t["priceMin"], 1.50)
        self.assertEqual(self.t["priceMax"], 6.75)


class OphthalmologyByBnf(unittest.TestCase):
    def test_bnf_21_30_corrects_the_eye_pattern_both_ways(self):
        lid_care = row("IXA", "Thea Pharmaceuticals Ltd", "Generic Lid-Care wipes",
                       "Blephaclean wipes", 549, "21300000850")
        silk_mask = row("IXA", "BAP Medical UK Ltd", "Silk eye mask",
                        "DermaSilk eye mask", 1119, "20200000320")
        drops = row("IXA", "Agepha Pharma s.r.o.",
                    "Sodium hyaluronate 0.2% eye drops 0.5ml unit dose preservative free",
                    "Ocusan 0.2% eye drops 0.5ml unit dose", 577, "21300000105")
        t = tariff_for("ophthalmology", [lid_care, silk_mask, drops])
        names = {s["name"] for s in t["topSuppliers"]}
        self.assertIn("Thea Pharmaceuticals Ltd", names)
        self.assertNotIn("BAP Medical UK Ltd", names)
        self.assertEqual(t["lineCount"], 2)


class RulesWithoutBnfAreUnchanged(unittest.TestCase):
    def test_gynaecology_still_narrows_by_name(self):
        pessary = row("IXA", "BBI Healthcare Ltd", "Lactic acid 250mg pessaries",
                      "Balance Activ pessaries", 530, "21340000102")
        t = tariff_for("gynaecology-and-womens-health", [pessary, QV_LINES[0]])
        self.assertIsNone(t["bnfFilter"])
        self.assertEqual(t["lineCount"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
