#!/usr/bin/env python3
r"""GP prescribing by ICB (scripts/refresh_gp_prescribing.py). Offline, stdlib only.

Added 29/09/2026 with the builder. What it holds the builder to:

1. ICB RE-ATTRIBUTION. Months before April 2026 carry 42 old ICB codes. An old
   ICB whose practices all went to one current ICB rolls up whole; a SPLIT old
   ICB (Frimley, QNQ, went three ways) is resolved practice by practice; a
   practice missing from the latest month follows its old ICB's majority and is
   counted, never silently dropped. No dissolved code may reach the output.
2. RECONCILIATION. Every month's rows must add up to the server-side section
   totals, or the build stops (a short CSV.gz download parses perfectly).
3. BRAND RULE. 'AA' is the generic in chapters 01-19; appliance chapters 20-23
   have no generic, so g is null, not false.
4. SOURCE PARSING. Revised months (…FINAL) win; resources not loaded into the
   datastore are skipped; results over 32,000 rows arrive via gc_urls CSV.gz.

  python3 test_gp_prescribing.py        exit 0 = holds
"""
import gzip
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scripts", "refresh_gp_prescribing.py")


def load():
    spec = importlib.util.spec_from_file_location("rgp_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = load()


class Attribution(unittest.TestCase):
    def test_whole_split_and_carried(self):
        current = {"P1": "S0E4D", "P2": "QRL", "P3": "S9B9J", "P4": "QOP", "-": "-"}
        month = [
            ("P1", "QNQ", 600), ("P2", "QNQ", 250), ("P3", "QNQ", 200),  # split
            ("P9", "QNQ", 5),                                             # closed practice
            ("P4", "QOP", 1000),                                          # unchanged
            ("-", "-", 7),
        ]
        primary, exc, carried = M.plan_attribution(month, current)
        self.assertEqual(primary["QNQ"], "S0E4D")
        self.assertEqual(primary["QOP"], "QOP")
        self.assertEqual(primary["-"], "-")
        self.assertEqual(exc, {"P2": "QRL", "P3": "S9B9J"})
        self.assertEqual(carried, 5)
        self.assertEqual(M.resolve("QNQ", primary, exc), "S0E4D")
        self.assertEqual(M.resolve("P:P2", primary, exc), "QRL")

    def test_current_month_needs_no_exceptions(self):
        current = {"P1": "QOP", "P2": "QE1"}
        primary, exc, carried = M.plan_attribution(
            [("P1", "QOP", 3), ("P2", "QE1", 4)], current)
        self.assertEqual(exc, {})
        self.assertEqual(carried, 0)
        self.assertEqual(M.group_expr(exc), "ICB_CODE")

    def test_old_icb_with_no_surviving_practice_is_not_published_under_its_code(self):
        primary, _e, carried = M.plan_attribution([("PX", "QXX", 9)], {"P1": "QOP"})
        self.assertEqual(primary["QXX"], "-")
        self.assertEqual(carried, 9)

    def test_group_expr_refuses_odd_codes(self):
        self.assertIn("'A81001'", M.group_expr({"A81001": "QHM"}))
        with self.assertRaises(ValueError):
            M.group_expr({"A1'); DROP": "QHM"})


class Rules(unittest.TestCase):
    def test_label(self):
        self.assertEqual(M.label_of("Zerobase 11% cream"), "Zerobase")
        self.assertEqual(M.label_of("QV cream"), "QV cream")
        self.assertEqual(M.label_of("3M Cavilon barrier cream"), "3M Cavilon barrier cream")

    def test_product_key_and_generic(self):
        self.assertEqual(M.product_key("1302011C0", "1302011C0AA"), "AA")
        self.assertEqual(M.product_key("2122", "21220000210"), "0000210")
        self.assertTrue(M.is_generic("1302011C0", "AA"))
        self.assertFalse(M.is_generic("1302011C0", "BB"))
        self.assertFalse(M.is_generic("2122", "AA"))

    def test_catch_all_codes_split_but_strengths_do_not(self):
        from collections import Counter
        m = M.product_codes({
            "130201000BBIC": Counter({"Dermol 500 lotion": 9}),
            "130201000BBJG": Counter({"Doublebase gel": 5}),
            "0402010ABBBAA": Counter({"Zimovane 3.75mg tablets": 3}),
            "0402010ABBBAB": Counter({"Zimovane 7.5mg tablets": 4}),
            "21220000210": Counter({"QV cream": 2}),
            "0403040W0BIAA": Counter({"ViePax XL 75mg capsules": 2}),
            "0403040W0BIAD": Counter({"ViePax 37.5mg tablets": 2}),
        })
        self.assertEqual(m["0403040W0BIAA"], "0403040W0BI")
        g = M.product_codes({"0902011U0AAAA": Counter({"Potassium chloride 600mg": 1}),
                             "0902011U0AAAB": Counter({"Pot chloride 8% liquid": 1})})
        self.assertEqual(set(g.values()), {"0902011U0AA"})
        self.assertEqual(m["0403040W0BIAD"], "0403040W0BI")
        self.assertEqual(m["130201000BBIC"], "130201000BBIC")
        self.assertEqual(m["130201000BBJG"], "130201000BBJG")
        self.assertEqual(m["0402010ABBBAA"], "0402010ABBB")
        self.assertEqual(m["0402010ABBBAB"], "0402010ABBB")
        self.assertEqual(m["21220000210"], "21220000210")

    def test_calendar(self):
        self.assertEqual(M.calendar_back("202602", 3), ["202512", "202601", "202602"])


class Source(unittest.TestCase):
    def test_resources_revision_wins_and_inactive_skipped(self):
        doc = {"result": {"resources": [
            {"name": "EPD_SNOMED_202505", "datastore_active": True},
            {"name": "EPD_SNOMED_202505FINAL", "datastore_active": True},
            {"name": "EPD_SNOMED_202506", "datastore_active": False},
            {"name": "EPD_SNOMED_202507", "datastore_active": True},
            {"name": "EPD_SNOMED metadata", "datastore_active": True},
        ]}}
        self.assertEqual(M.resources(doc), [("202505", "EPD_SNOMED_202505FINAL"),
                                            ("202507", "EPD_SNOMED_202507")])

    def test_inline_and_gc_urls(self):
        inline = {"success": True, "result": {"result": {"records": [{"a": 1}]}}}
        self.assertEqual(M.parse_sql_response(inline), [{"a": 1}])
        blob = gzip.compress(b"a,b\n1,2\n")
        seen = []

        def get(url):
            seen.append(url)
            return blob
        big = {"success": True, "result": {"records_truncated": "true", "gc_urls": [
            {"url": "https://x/`T`-000.csv.gz"}, {"url": "https://x/`T`-001.csv.gz"}]}}
        rows = M.parse_sql_response(big, get=get)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["b"], "2")
        self.assertTrue(all("`" not in u for u in seen))

    def test_error_is_loud(self):
        with self.assertRaises(RuntimeError):
            M.parse_sql_response({"success": False, "error": {"message": "bad"}})


def fake_sql(short=False):
    """A two-month source: 202506 on old boundaries (QNQ split), 202507 current."""
    prac = {
        "EPD_SNOMED_202507": [
            {"pr": "P1", "icb": "S0E4D", "nm": "NHS THAMES VALLEY ICB", "i": 10},
            {"pr": "P2", "icb": "QRL", "nm": "NHS HAMPSHIRE ICB", "i": 10},
            {"pr": "-", "icb": "-", "nm": "UNIDENTIFIED", "i": 1}],
        "EPD_SNOMED_202506": [
            {"pr": "P1", "icb": "QNQ", "nm": "NHS FRIMLEY ICB", "i": 10},
            {"pr": "P2", "icb": "QNQ", "nm": "NHS FRIMLEY ICB", "i": 5}],
    }
    main = {
        "EPD_SNOMED_202507": [
            {"g": "S0E4D", "s": "1302011C0", "p": "1302011C0AA", "i": 30, "k": 10.0},
            {"g": "QRL", "s": "1302011C0", "p": "1302011C0BB", "i": 5, "k": 4.0},
            {"g": "-", "s": "2122", "p": "21220000210", "i": 2, "k": 3.0},
            {"g": "QRL", "s": "130201000", "p": "130201000BBIC", "i": 7, "k": 1.0},
            {"g": "QRL", "s": "130201000", "p": "130201000BBJG", "i": 3, "k": 1.0}],
        "EPD_SNOMED_202506": [
            {"g": "QNQ", "s": "1302011C0", "p": "1302011C0AA", "i": 20, "k": 8.0},
            {"g": "P:P2", "s": "1302011C0", "p": "1302011C0BB", "i": 6, "k": 5.0}],
    }
    names = [{"p": "1302011C0AA", "n": "Emollient 50% cream", "s": "1302011C0",
              "sn": "Emollient", "i": 1},
             {"p": "1302011C0BB", "n": "Brandex cream", "s": "1302011C0",
              "sn": "Emollient", "i": 1},
             {"p": "21220000210", "n": "QV cream", "s": "2122",
              "sn": "Emollient devices", "i": 1},
             {"p": "130201000BBIC", "n": "Dermol 500 lotion", "s": "130201000",
              "sn": "Other emollient preparations", "i": 7},
             {"p": "130201000BBJG", "n": "Doublebase gel", "s": "130201000",
              "sn": "Other emollient preparations", "i": 3}]

    def run(table, q):
        if "PRACTICE_CODE AS pr" in q:
            return prac[table]
        if "BNF_PRESENTATION_NAME" in q:
            return names
        if "AS sec" in q:
            rows = main[table]
            tot = {}
            for r in rows:
                t = tot.setdefault(r["p"][:4], [0, 0.0])
                t[0] += r["i"]
                t[1] += r["k"]
            out = [{"sec": k, "i": v[0], "k": v[1]} for k, v in tot.items()]
            if short:
                out[0]["i"] += 1
            return out
        if "P:" in q or table == "EPD_SNOMED_202507":
            return main[table]
        raise AssertionError("SQL for 202506 must resolve the split ICB: %s" % q)
    return run


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.res = [("202506", "EPD_SNOMED_202506"), ("202507", "EPD_SNOMED_202507")]

    def tearDown(self):
        shutil.rmtree(self.tmp, True)

    def test_build_attributes_to_current_icbs(self):
        idx = M.build(2, self.tmp, run_sql=fake_sql(), res=self.res)
        self.assertEqual(sorted(idx["icbs"]), ["-", "QRL", "S0E4D"])
        s = json.load(open(os.path.join(self.tmp, "s-1302.json")))["s"]["1302011C0"]
        self.assertEqual(s["t"]["S0E4D"]["AA"], [20, 30])
        self.assertEqual(s["t"]["QRL"]["BB"], [6, 5])
        self.assertIs(s["g"], True)
        self.assertEqual(s["p"], {"AA": "Emollient", "BB": "Brandex cream"})
        self.assertEqual(s["nc"]["BB"], [5.0, 4.0])
        a = json.load(open(os.path.join(self.tmp, "s-2122.json")))["s"]["2122"]
        self.assertIsNone(a["g"])
        self.assertEqual(a["t"]["-"]["0000210"], [0, 2])
        self.assertEqual(idx["icbAttribution"]["202506"]["oldIcbsRemapped"],
                         {"QNQ": "S0E4D"})
        self.assertEqual(idx["minBaselineItems"], M.MIN_BASELINE_ITEMS)
        other = json.load(open(os.path.join(self.tmp, "s-1302.json")))["s"]["130201000"]
        self.assertEqual(other["p"], {"BBIC": "Dermol", "BBJG": "Doublebase gel"})
        self.assertEqual(other["t"]["QRL"]["BBIC"], [0, 7])
        self.assertIs(other["g"], False)
        self.assertEqual(idx["splitProducts"], ["130201000BB"])

    def test_short_download_stops_the_build(self):
        with self.assertRaises(RuntimeError):
            M.build(2, self.tmp, run_sql=fake_sql(short=True), res=self.res)

    def test_missing_month_is_null_not_zero(self):
        idx = M.build(3, self.tmp, run_sql=fake_sql(),
                      res=self.res)  # window 202505..202507, 202505 absent
        self.assertEqual(idx["missingPeriods"], ["202505"])
        s = json.load(open(os.path.join(self.tmp, "s-1302.json")))["s"]["1302011C0"]
        self.assertIsNone(s["t"]["S0E4D"]["AA"][0])


if __name__ == "__main__":
    unittest.main()
