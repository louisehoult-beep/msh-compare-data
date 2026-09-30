#!/usr/bin/env python3
"""Offline, stdlib-only tests for the MHRA Drug Safety Update feed and Drug
Tariff Part VIIIA (both added 29/09/2026), and for their verify.py checks.

Nothing here touches the network or writes into the repo. Run on its own:
    python3 test_mhra_dsu_and_tariff_viiia.py
"""
import copy
import datetime
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import refresh_mhra_dsu as dsu                     # noqa: E402
import refresh_drug_tariff_part_viiia as viiia     # noqa: E402
import verify                                       # noqa: E402


def run_check(fn, doc):
    verify.fails.clear()
    verify.warns.clear()
    fn(doc)
    return list(verify.fails)


TABLE = {
    "dermatology": {"label": "Dermatology", "hub": ["dermatology"]},
    "haematology": {"label": "Haematology and oncology",
                    "hub": ["haematology-and-patient-blood-management", "oncology-and-sact"]},
    "cancer": {"label": "Cancer", "hub": ["oncology-and-sact"]},
    "dentistry": {"label": "Dentistry", "hub": [], "unmappedReason": "No panel."},
}
SLUGS = ["dermatology", "haematology-and-patient-blood-management", "oncology-and-sact"]


def result(link, facets, title="Isotretinoin: update", first="2026-01-22", ts="2026-01-22T10:00:00Z"):
    return {"link": "/drug-safety-update/" + link, "title": title, "description": "  a  summary ",
            "first_published_at": first, "public_timestamp": ts, "therapeutic_area": facets}


class DsuMapping(unittest.TestCase):
    def test_real_table_targets_real_panels(self):
        errs = dsu.validate_map(dsu.load_map(), dsu.panel_slugs())
        self.assertEqual(errs, [])

    def test_validate_catches_missing_panel_and_missing_reason(self):
        bad = {"x": {"hub": ["no-such-panel"]}, "y": {"hub": []}}
        errs = dsu.validate_map(bad, SLUGS)
        self.assertEqual(len(errs), 2)

    def test_map_dedupes_and_reports_unmapped(self):
        hub, unmapped = dsu.map_facets(["haematology", "cancer", "dentistry", "brand-new"], TABLE)
        self.assertEqual(hub, ["haematology-and-patient-blood-management", "oncology-and-sact"])
        self.assertEqual(unmapped, ["dentistry", "brand-new"])

    def test_unknown_facet_is_reported_not_guessed(self):
        doc = dsu.assemble([result("a", ["brand-new-area", "dermatology"])], TABLE, SLUGS,
                           {}, 1, datetime.date(2026, 9, 29))
        row = doc["updates"][0]
        self.assertEqual(row["specialities"], ["dermatology"])
        u = {x["facet"]: x for x in doc["unmappedFacets"]}
        self.assertEqual(u["brand-new-area"]["reason"], "not in mapping table")
        self.assertEqual(u["brand-new-area"]["updates"], 1)

    def test_assemble_counts_and_fields(self):
        res = [result("a", ["dermatology"]),
               result("b", ["haematology"], first="2024-05-29T13:32:45Z", ts="2024-06-01T00:00:00Z"),
               result("c", [], title="Letters and medicine recalls sent to healthcare professionals in June 2024")]
        doc = dsu.assemble(res, TABLE, SLUGS, {}, 3, datetime.date(2026, 9, 29))
        self.assertTrue(doc["coverage"]["complete"])
        self.assertEqual(doc["counts"]["updates"], 3)
        self.assertEqual(doc["counts"]["bySpeciality"]["oncology-and-sact"], 1)
        self.assertEqual(doc["counts"]["roundups"], 1)
        b = [r for r in doc["updates"] if r["url"].endswith("/b")][0]
        self.assertEqual((b["published"], b["updated"]), ("2024-05-29", "2024-06-01"))
        self.assertEqual(doc["updates"][0]["summary"], "a summary")
        self.assertEqual(doc["updates"][0]["published"], "2026-01-22")   # newest first

    def test_short_walk_is_incomplete(self):
        doc = dsu.assemble([result("a", [])], TABLE, SLUGS, {}, 2, datetime.date(2026, 9, 29))
        self.assertFalse(doc["coverage"]["complete"])


class DsuGate(unittest.TestCase):
    """verify.check_mhra_dsu against a doc built from the REAL mapping table."""

    def good(self):
        table = dsu.load_map()
        res = [result("a", ["dermatology", "cancer"]), result("b", ["dentistry"])]
        return dsu.assemble(res, table, dsu.panel_slugs(), {}, 2, datetime.date.today())

    def test_good_doc_passes(self):
        self.assertEqual(run_check(verify.check_mhra_dsu, self.good()), [])

    def test_hand_added_speciality_fails(self):
        doc = self.good()
        doc["updates"][0]["specialities"] = sorted(doc["updates"][0]["specialities"] + ["stroke"])
        self.assertTrue(run_check(verify.check_mhra_dsu, doc))

    def test_future_date_fails(self):
        doc = self.good()
        doc["updates"][0]["published"] = "2999-01-01"
        self.assertTrue(run_check(verify.check_mhra_dsu, doc))

    def test_count_mismatch_and_incomplete_fail(self):
        doc = self.good()
        doc["counts"]["updates"] = 99
        doc["coverage"]["complete"] = False
        self.assertEqual(len(run_check(verify.check_mhra_dsu, doc)), 2)

    def test_absent_file_is_a_no_op(self):
        self.assertEqual(run_check(verify.check_mhra_dsu, None), [])

    def test_committed_file_passes_if_present(self):
        p = os.path.join("data", "mhra-dsu.json")
        if not os.path.exists(p):
            self.skipTest("data/mhra-dsu.json not built yet")
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(run_check(verify.check_mhra_dsu, json.load(fh)), [])


INDEX_HTML = """
<a href="/sites/default/files/2026-08/Part%20VIIIA%20Sep%2026.csv">x</a>
<a href="/sites/default/files/2026-09/Part%20VIIIA%20Oct%202026.csv">x</a>
<a href="/sites/default/files/2026-06/Part%20VIIIA%20Jul%2026.xls.csv">x</a>
<a href="/sites/default/files/2026-06/Part%20VIIIA%20April%202026.csv">x</a>
<a href="/sites/default/files/2025-12/Part%20VIIIA%20December%2020251.xls_0.csv">x</a>
<a href="/sites/default/files/2025-08/Part%20VIIIA%20Sept%202025.xls.csv">x</a>
<a href="/sites/default/files/2026-05/Part%20VIIIA%20Jun%202026.csv">x</a>
<a href="/sites/default/files/2026-05/Part%20VIIIA%20Jun%202026.xlsx">x</a>
<a href="/sites/default/files/2026-09/Cat%20M%20Prices%20-%20Quarter%203%20Oct%2026.csv">x</a>
<a href="/sites/default/files/2021-02/Part%20VIIIB%20Feb%2021_0.csv">x</a>
"""

CSV_TEXT = ("September Drug Tariff Part VIIIA,,,,,,\r\n,,,,,,\r\n"
            "Medicine,Pack size,,VMP Snomed Code,VMPP Snomed Code,Drug Tariff Category,Basic Price\r\n"
            "Acitretin 10mg capsules,60,capsule,111,222,Part VIIIA Category A,1776\r\n"
            "Clobetasol 0.05% cream,30,gram,333,444,Part VIIIA Category C,269\r\n"
            "Hydrocortisone 10mg tablets,30,tablet,555,666,Part VIIIA Category M,142\r\n"
            "Cinchocaine 5mg / Hydrocortisone 5mg suppositories,12,suppository,7,8,Part VIIIA Category H,597\r\n"
            ",,,,,,\r\n")


class ViiiaSource(unittest.TestCase):
    def test_irregular_names_parse(self):
        eds = viiia.editions(INDEX_HTML)
        self.assertEqual(sorted(eds), [(2025, 9), (2025, 12), (2026, 4), (2026, 6), (2026, 7),
                                       (2026, 9), (2026, 10)])
        self.assertTrue(eds[(2025, 12)].endswith("December%2020251.xls_0.csv"))
        self.assertTrue(all(u.startswith("https://www.nhsbsa.nhs.uk/") for u in eds.values()))

    def test_pick_is_the_edition_in_force(self):
        eds = viiia.editions(INDEX_HTML)
        self.assertEqual(viiia.pick(eds, 2026, 9), (2026, 9))
        self.assertEqual(viiia.pick(eds, 2026, 5), (2026, 4))    # May missing -> April in force
        self.assertEqual(viiia.pick(eds, 2027, 3), (2026, 10))
        self.assertIsNone(viiia.pick(eds, 2020, 1))

    def test_parse_csv(self):
        rows, problems = viiia.parse_csv(CSV_TEXT, 2026, 9)
        self.assertEqual(problems, [])
        self.assertEqual(rows[0], ["Acitretin 10mg capsules", "60", "capsule", "A", 1776, "111"])
        self.assertEqual([r[3] for r in rows], ["A", "C", "M", "H"])

    def test_title_month_mismatch_refuses(self):
        rows, problems = viiia.parse_csv(CSV_TEXT, 2026, 10)
        self.assertTrue(any("does not name October" in p for p in problems))

    def test_bad_row_is_a_problem_not_a_silent_drop(self):
        rows, problems = viiia.parse_csv(CSV_TEXT.replace(",1776", ",n/a"), 2026, 9)
        self.assertTrue(problems)


class ViiiaGate(unittest.TestCase):
    def good(self):
        rows = [["Med %d" % i, "28", "tablet", "ACMH"[i % 4], 100 + i, str(i)] for i in range(3100)]
        cats = {}
        for r in rows:
            cats[r[3]] = cats.get(r[3], 0) + 1
        return {"schema": list(verify.VIIIA_SCHEMA), "rowCount": len(rows), "rows": rows,
                "effectiveMonth": datetime.date.today().strftime("%Y-%m"),
                "source": "https://www.nhsbsa.nhs.uk/sites/default/files/x.csv",
                "categoryCounts": cats}

    def test_good_doc_passes(self):
        self.assertEqual(run_check(verify.check_drug_tariff_viiia, self.good()), [])

    def test_failures(self):
        for mutate in (lambda d: d["rows"][0].__setitem__(3, "Z"),
                       lambda d: d["rows"][0].__setitem__(4, "12.50"),
                       lambda d: d.__setitem__("rowCount", 1),
                       lambda d: d.__setitem__("effectiveMonth", "2999-01"),
                       lambda d: d.__setitem__("rows", d["rows"][:100]),
                       lambda d: d.__setitem__("schema", ["medicine"])):
            doc = copy.deepcopy(self.good())
            mutate(doc)
            self.assertTrue(run_check(verify.check_drug_tariff_viiia, doc))

    def test_committed_file_passes_if_present(self):
        p = os.path.join("data", "drug-tariff-part-viiia.json")
        if not os.path.exists(p):
            self.skipTest("data/drug-tariff-part-viiia.json not built yet")
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(run_check(verify.check_drug_tariff_viiia, json.load(fh)), [])


class Wiring(unittest.TestCase):
    def read(self, p):
        with open(p, encoding="utf-8") as fh:
            return fh.read()

    def test_workflows_run_the_writers_and_the_gate(self):
        dt = self.read(".github/workflows/drug-tariff.yml")
        self.assertIn("scripts/refresh_drug_tariff_part_viiia.py", dt)
        self.assertIn("git add data/drug-tariff-part-ix.json data/drug-tariff-part-viiia.json", dt)
        md = self.read(".github/workflows/mhra-dsu.yml")
        self.assertIn("python3 scripts/refresh_mhra_dsu.py", md)
        self.assertIn("bash scripts/gate.sh", md)
        self.assertIn("git add data/mhra-dsu.json", md)

    def test_both_files_have_marker_refs(self):
        import stamp_notice
        self.assertIn("mhra-dsu.json", stamp_notice.REFS)
        self.assertIn("drug-tariff-part-viiia.json", stamp_notice.REFS)


if __name__ == "__main__":
    unittest.main(verbosity=1)
