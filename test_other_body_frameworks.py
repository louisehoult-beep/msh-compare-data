#!/usr/bin/env python3
"""
test_other_body_frameworks.py - prove scripts/check_other_body_frameworks.py reads
NHS Shared Business Services (SBS), Government Commercial Agency (GCA) and NHS
London Procurement Partnership (LPP) page shapes, reports a change with the exact
text read, treats an outage as unreachable rather than changed, and that --apply
writes only values it read.

  python3 test_other_body_frameworks.py     exit 0 = pass. No network. Stdlib only.
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import check_other_body_frameworks as c  # noqa: E402

# Shape of sbs.nhs.uk framework pages as read 22/10/2026.
SBS_PAGE = """<html><body><main>
<h1>Insourcing of Clinical Services</h1>
<p>Framework Agreement Reference: SBS10203</p>
<h2>Framework Agreement Information</h2>
<h3>What dates is the framework agreement active?</h3>
<p>03 July 2023 &ndash; 01 July 2028</p>
<h3>Who can take advantage of the framework agreement?</h3>
</main></body></html>"""

SBS_PAGE_OPTION = """<html><body><main>
<p>Framework Agreement Reference: SBS10515</p>
<h3>What dates is the framework agreement active?</h3>
<p>01 April 2025 &ndash; 31 March 2028</p><p>(with the option to extend until 31 March 2029)</p>
</main></body></html>"""

SBS_PAGE_REWORDED = """<html><body><main>
<p>Framework Agreement Reference: SBS10203</p><p>Dates: July 2023 onwards</p>
</main></body></html>"""

# Shape of gca.gov.uk agreement pages (same fixture shape as test_digital_frameworks).
GCA_PAGE = """<html><body><main>
<p>Agreement number: </p><p> RM6331 </p><p>Start date: </p><p> 20/02/2024 </p>
<p>End date: </p><p> 19/02/2028 </p><p>Agreement type: </p><p> Framework </p>
</main></body></html>"""

GCA_PAGE_EXTENDED = GCA_PAGE.replace("19/02/2028", "19/02/2029")

GCA_OUTAGE = """<html><head><title >Government Commercial Agency: Service unavailable</title>
</head><body><h1>Sorry, the service is unavailable</h1></body></html>"""

# Shape of lpp.nhs.uk category pages as read 22/10/2026.
LPP_PAGE = """<html><body><dl><dt>Start:</dt><dd>01-07-25</dd><dt>End:</dt><dd>30-06-27</dd>
<dt>Extensions remaining:</dt><dd>2.00</dd></dl></body></html>"""

SBS_URL = "https://www.sbs.nhs.uk/services/framework-agreements/insourcing-of-clinical-services/"
GCA_URL = "https://www.gca.gov.uk/agreements/RM6331"
LPP_URL = "https://www.lpp.nhs.uk/categories/healthcare-and-pharmacy-services/contrast-media/"


def row(url, reference, starts, ends, name="X"):
    return {"name": name, "url": url, "owner": "o", "reference": reference,
            "starts": starts, "ends": ends}


def serve(page):
    return lambda url: page


class Parsers(unittest.TestCase):
    def test_sbs_shape(self):
        p = c.parse_sbs(SBS_PAGE)
        self.assertEqual(p["reference"], "SBS10203")
        self.assertEqual((p["starts"], p["ends"]), ("2023-07-03", "2028-07-01"))
        self.assertIn("03 July 2023 – 01 July 2028", p["text"])

    def test_sbs_with_extension_option(self):
        p = c.parse_sbs(SBS_PAGE_OPTION)
        self.assertEqual(p["ends"], "2028-03-31")

    def test_sbs_reworded_page_is_unparseable(self):
        with self.assertRaises(ValueError):
            c.parse_sbs(SBS_PAGE_REWORDED)

    def test_gca_shape(self):
        p = c.parse_gca(GCA_PAGE)
        self.assertEqual(p["reference"], "RM6331")
        self.assertEqual((p["starts"], p["ends"]), ("2024-02-20", "2028-02-19"))
        self.assertEqual(p["text"], "Agreement number: RM6331; Start date: 20/02/2024; End date: 19/02/2028")

    def test_gca_outage_is_not_a_change(self):
        with self.assertRaises(ConnectionError):
            c.parse_gca(GCA_OUTAGE)

    def test_lpp_shape(self):
        p = c.parse_lpp(LPP_PAGE)
        self.assertEqual((p["starts"], p["ends"]), ("2025-07-01", "2027-06-30"))
        self.assertIsNone(p["reference"])

    def test_stored_dates(self):
        self.assertEqual(c.stored_date("11 Nov 2033 (open framework — re-opens)"), "2033-11-11")
        self.assertEqual(c.stored_date("1 Aug 2026 (estimated)"), "2026-08-01")
        self.assertIsNone(c.stored_date("ongoing, republished monthly"))
        self.assertIsNone(c.stored_date(None))


class Rows(unittest.TestCase):
    def test_sbs_ok(self):
        r = c.check_row(row(SBS_URL, "SBS10203", "03 Jul 2023", "01 Jul 2028"), serve(SBS_PAGE))
        self.assertEqual(r["status"], "OK")

    def test_sbs_end_date_changed_carries_exact_text(self):
        r = c.check_row(row(SBS_URL, "SBS10203", "03 Jul 2023", "02 Jul 2027"), serve(SBS_PAGE))
        self.assertEqual(r["status"], "CHANGED")
        self.assertEqual(r["diffs"], [("ends", "02 Jul 2027", "01 Jul 2028")])
        self.assertIn("01 July 2028", r["detail"])

    def test_gca_changed_and_outage(self):
        base = row(GCA_URL, "RM6331", "20 Feb 2024", "19 Feb 2028")
        self.assertEqual(c.check_row(base, serve(GCA_PAGE))["status"], "OK")
        r = c.check_row(base, serve(GCA_PAGE_EXTENDED))
        self.assertEqual(r["diffs"], [("ends", "19 Feb 2028", "19 Feb 2029")])
        self.assertEqual(c.check_row(base, serve(GCA_OUTAGE))["status"], "UNREACHABLE")

    def test_lpp_name_reference_is_not_compared(self):
        r = c.check_row(row(LPP_URL, "Contrast Media (NHS LPP)", "01 Jul 2025", "30 Jun 2027"), serve(LPP_PAGE))
        self.assertEqual(r["status"], "OK")

    def test_gone_unreachable_unparseable_not_checked(self):
        def gone(url):
            raise c.Gone("HTTP 404")

        def down(url):
            raise RuntimeError("timed out")
        base = row(SBS_URL, "SBS10203", "03 Jul 2023", "01 Jul 2028")
        self.assertEqual(c.check_row(base, gone)["status"], "GONE")
        self.assertEqual(c.check_row(base, down)["status"], "UNREACHABLE")
        self.assertEqual(c.check_row(base, serve(SBS_PAGE_REWORDED))["status"], "UNPARSEABLE")
        self.assertEqual(c.check_row(row("https://www.find-tender.service.gov.uk/Notice/1", "r", None, None),
                                     serve(""))["status"], "NOT_CHECKED")
        self.assertEqual(c.check_row(row("https://example.org/x", "r", None, "01 Jan 2030"),
                                     serve(""))["status"], "NOT_CHECKED")


class Apply(unittest.TestCase):
    def test_apply_writes_only_values_read_and_keeps_notes(self):
        doc = {"otherBodies": [
            row(SBS_URL, "SBS10203", "03 Jul 2023", "02 Jul 2027 (extension pending)"),
            row(GCA_URL, "RM6331", "20 Feb 2024", "19 Feb 2028"),
        ], "otherBodiesCheckedAt": "old"}
        pages = {SBS_URL: SBS_PAGE, GCA_URL: GCA_OUTAGE}
        results = [c.check_row(r, lambda u: pages[u]) for r in doc["otherBodies"]]
        self.assertEqual(c.apply_changes(doc, results, "2026-10-22"), 1)
        self.assertEqual(doc["otherBodies"][0]["ends"], "01 Jul 2028 (extension pending)")
        self.assertEqual(doc["otherBodies"][0]["starts"], "03 Jul 2023")
        self.assertEqual(doc["otherBodies"][1]["ends"], "19 Feb 2028")  # outage: untouched
        self.assertEqual(doc["otherBodiesCheckedAt"],
                         "1 of 2 rows re-read at their source by scripts/check_other_body_frameworks.py, 22/10/2026")

    def test_report_names_exact_text_and_fix(self):
        r = c.check_row(row(SBS_URL, "SBS10203", "03 Jul 2023", "02 Jul 2027"), serve(SBS_PAGE))
        md = c.report_markdown([r], "2026-10-22")
        self.assertIn("stored **02 Jul 2027**, page says **01 Jul 2028**", md)
        self.assertIn("03 July 2023 – 01 July 2028", md)
        self.assertIn("--apply", md)

    def test_main_exit_codes_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"otherBodies": [row(SBS_URL, "SBS10203", "03 Jul 2023", "02 Jul 2027")]}, f)
            orig = c.fetch
            c.fetch = serve(SBS_PAGE)
            try:
                rep = os.path.join(d, "r.md")
                self.assertEqual(c.main(["--data", path, "--report", rep]), 1)
                self.assertIn("SBS10203", open(rep, encoding="utf-8").read())
                self.assertEqual(c.main(["--data", path, "--apply"]), 1)
                self.assertEqual(c.main(["--data", path]), 0)
                def down(url):
                    raise RuntimeError("timed out")
                c.fetch = down
                self.assertEqual(c.main(["--data", path]), 2)  # every source unreachable
            finally:
                c.fetch = orig


if __name__ == "__main__":
    unittest.main(verbosity=1)
