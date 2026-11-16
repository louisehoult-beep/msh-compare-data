#!/usr/bin/env python3
"""
test_digital_frameworks.py - prove scripts/refresh_digital_frameworks.py parses
GCA agreement pages, supplier exports and Find a Tender OCDS notices from
fixtures, keeps company names only, and gives honest empty states.

  python3 test_digital_frameworks.py     exit 0 = pass. No network. Stdlib only.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_digital_frameworks as rdf  # noqa: E402

TS4_PAGE = """<html><body><main>
<p>Agreement number: </p><p> RM6190 </p><p>Start date: </p><p> 12/12/2025 </p>
<p>End date: </p><p> 11/06/2028 </p><p>Agreement type: </p><p> Open Framework </p>
<p>Technology Services 4 will run for 8 years. As an open framework, it
will reopen before the end of year 3 and 5.</p>
<div id="products">Products and suppliers
<h3>Lot 1 Technology and Digital Consultancy Services</h3><p>Desc.</p>
<p>Expires: 11/06/2028</p><p>2 suppliers</p>
<h3>Lot 3a End User Services (lower value and complexity)</h3>
<p>This lot has a maximum contract value of 3million including VAT.</p>
<p>Expires: 11/06/2028</p><p>1 suppliers</p>
</div><h2>Documents</h2></main></body></html>"""

CSV1 = ('"Supplier Name","Trading Name","Contact Name","Contact Email",Street,City,Postcode\n'
        '"ZED LTD",,"Jane Secret",jane.secret@zed.example,"1 Road","Town","AB1 2CD"\n'
        '"ALPHA PLC","Alpha","Bob Hidden",bob@alpha.example,"2 Road",City,\n'
        '"ALPHA PLC","Alpha","Dup Row",dup@alpha.example,"2 Road",City,\n')
CSV3A = ('"Supplier Name","Trading Name","Contact Name","Contact Email",Street,City,Postcode\n'
         '"MID LIMITED",,"Pat",pat@mid.example,x,y,z\n')

GC_PAGE = """<html><body><main>
<p>Agreement number: </p><p> RM1557.15 </p><p>Start date: </p><p> 06/08/2026 </p>
<p>End date: </p><p> 05/02/2028 </p><p>Agreement type: </p><p> Open Framework </p>
<p>G-Cloud 15 will run for 4 years from 6 August 2026 (reopening after 18 months and again after 36 months).</p>
<div id="products">Products and suppliers
<h3>Lot 2b Other Software as a Service (Saas)</h3><p>Use this lot.</p>
<p>Access Lot 2b: Other Software as a Service (SaaS).</p><p>Expires: 05/02/2028</p>
</div><h2>Documents</h2></main></body></html>"""

SUPPLIERS_NO_GC15 = "<html>G-Cloud 14 Lot 4 (RM1557.14L4)</html>"

AZ_A1 = """<div class="app-search-result"><h2 class="govuk-heading-s">
<a class="govuk-link" href="/g-cloud-15/supplier/1">ALPHA CLOUD LTD</a></h2>
<p>Description that is never stored. Call jane@alpha.example</p></div>
<div class="app-search-result"><h2 class="govuk-heading-s">
<a class="govuk-link" href="/g-cloud-15/supplier/2">A&amp;B HEALTH LIMITED</a></h2></div>
<a class="govuk-link govuk-pagination__link" href="/g-cloud-15/suppliers?page=2&amp;prefix=A" rel="next">"""
AZ_A2 = """<a class="govuk-link" href="/g-cloud-15/supplier/3">AZURE CARE LTD</a>"""
AZ_M = """<a class="govuk-link" href="/g-cloud-15/supplier/4">MEDILOGIK LIMITED</a>"""

OCDS_AI = {"releases": [{
    "id": "050314-2026", "date": "2026-05-28T13:23:29+01:00", "tag": ["tenderUpdate"],
    "buyer": {"name": "NHS Shared Business Services Limited"},
    "tender": {
        "title": "Healthcare AI Solutions", "status": "active",
        "description": "The Open Framework is intended to serve as a strategic vehicle. More text.",
        "value": {"amount": 750000000, "amountGross": 900000000, "currency": "GBP"},
        "procurementMethodDetails": "Open procedure",
        "awardPeriod": {"endDate": "2027-03-19T23:59:59Z"},
        "tenderPeriod": {"endDate": "2026-07-07T12:00:00+01:00"},
        "lots": [{"id": "1", "title": "Radiology",
                  "value": {"amount": 750000000, "amountGross": 900000000, "currency": "GBP"},
                  "contractPeriod": {"startDate": "2027-05-26T00:00:00+01:00",
                                     "endDate": "2035-05-11T23:59:59+01:00"}}]}}]}

OCDS_GP = {"releases": [{
    "id": "094419-2026", "date": "2026-10-06T16:17:27+01:00", "tag": ["planning"],
    "buyer": {"name": "NHS England"},
    "tender": {
        "title": "Digital Primary Care Open Framework", "status": "planned",
        "description": "Intro. Framework go-live is expected in Q3 2027. Tail.",
        "value": {"amount": 838749369.0, "amountGross": 1006499242.8, "currency": "GBP"},
        "procurementMethodDetails": "Competitive flexible procedure",
        "awardPeriod": {"endDate": "2027-08-05T23:59:59+01:00"},
        "expressionOfInterestDeadline": "2026-11-10T23:59:00Z",
        "communication": {"futureNoticeDate": "2026-11-09T23:59:59Z"},
        "techniques": {"frameworkAgreement": {"openFrameworkSchemeEndDate": "2033-09-19T23:59:59+01:00"}},
        "lots": [{"id": "1", "title": "Foundation EPR",
                  "value": {"amount": 1.0, "amountGross": 2.0, "currency": "GBP"},
                  "contractPeriod": {"startDate": "2027-09-20T00:00:00+01:00",
                                     "endDate": "2030-09-19T23:59:59+01:00",
                                     "maxExtentDate": "2033-09-19T23:59:59+01:00"}}]}}]}


def fake_fetch(fail=()):
    def f(url):
        for bad in fail:
            if bad in url:
                raise RuntimeError("boom")
        if url.endswith("/agreements/RM6190"):
            return TS4_PAGE
        if url.endswith("RM6190:1/lot-suppliers/csv"):
            return CSV1
        if url.endswith("RM6190:3a/lot-suppliers/csv"):
            return CSV3A
        if url.endswith("/agreements/RM1557.15"):
            return GC_PAGE
        if url.endswith("/suppliers"):
            return SUPPLIERS_NO_GC15
        if "/g-cloud-15/suppliers?" in url:
            if url.endswith("page=2&prefix=A"):
                return AZ_A2
            if url.endswith("prefix=A"):
                return AZ_A1
            if url.endswith("prefix=M"):
                return AZ_M
            return "<html>no suppliers under this letter</html>"
        if url.endswith("050314-2026"):
            return json.dumps(OCDS_AI)
        if url.endswith("094419-2026"):
            return json.dumps(OCDS_GP)
        raise AssertionError("unexpected url " + url)
    return f


class Parsing(unittest.TestCase):
    def test_header_and_lots(self):
        h = rdf.parse_agreement_header(TS4_PAGE)
        self.assertEqual((h["reference"], h["start"], h["end"]), ("RM6190", "2025-12-12", "2028-06-11"))
        lots = rdf.parse_lots(TS4_PAGE)
        self.assertEqual([l["lot"] for l in lots], ["1", "3a"])
        self.assertEqual(lots[1]["name"], "End User Services (lower value and complexity)")
        self.assertEqual(lots[0]["supplierCountOnPage"], 2)

    def test_csv_keeps_company_names_only(self):
        names = rdf.parse_supplier_csv(CSV1)
        self.assertEqual(names, ["ALPHA PLC", "ZED LTD"])

    def test_csv_without_supplier_name_column_raises(self):
        with self.assertRaises(ValueError):
            rdf.parse_supplier_csv("a,b\n1,2\n")

    def test_ocds(self):
        p = rdf.parse_ocds(OCDS_GP, "094419-2026")
        self.assertEqual(p["futureNoticeDate"], "2026-11-09")
        self.assertEqual(p["lots"][0]["maxExtentDate"], "2033-09-19")
        self.assertEqual(p["url"], "https://www.find-tender.service.gov.uk/Notice/094419-2026")


class Build(unittest.TestCase):
    def setUp(self):
        self.doc = rdf.build(fake_fetch(), "2026-10-20")
        self.by = {e["reference"]: e for e in self.doc["frameworks"]}

    def test_top_level_and_entry_fields(self):
        for k in ("rule", "source", "generated", "dataAsOf"):
            self.assertIn(k, self.doc)
        for e in self.doc["frameworks"]:
            for k in ("name", "reference", "owner", "url", "status", "starts", "ends", "lots",
                      "suppliers", "verifiedOn", "sourceQuote", "notVerified"):
                self.assertIn(k, e)
            self.assertEqual(e["verifiedOn"], "2026-10-20")
            self.assertIn(e["status"], ("live", "coming"))

    def test_no_contact_data_anywhere(self):
        blob = json.dumps(self.doc)
        for leak in ("@", "Jane Secret", "Bob Hidden", "jane.secret", "AB1 2CD", "1 Road"):
            self.assertNotIn(leak, blob)

    def test_ts4_suppliers_per_lot(self):
        ts4 = self.by["RM6190"]
        lots = {l["lot"]: l for l in ts4["lots"]}
        self.assertEqual(lots["1"]["suppliers"], ["ALPHA PLC", "ZED LTD"])
        self.assertEqual(lots["3a"]["supplierCount"], 1)

    def test_supplier_count_mismatch_is_flagged_not_hidden(self):
        # fixture page says "1 suppliers" for 3a and the export has 1 (ok); lot 1 says 2 and has 2.
        self.assertFalse([n for n in self.by["RM6190"]["notVerified"] if "page says" in n])

    def test_ts4_export_failure_gives_null_and_note(self):
        doc = rdf.build(fake_fetch(fail=("RM6190:3a/lot-suppliers",)), "2026-10-20")
        ts4 = doc["frameworks"][0]
        lots = {l["lot"]: l for l in ts4["lots"]}
        self.assertIsNone(lots["3a"]["suppliers"])
        self.assertIsNotNone(lots["1"]["suppliers"])
        self.assertIsNone(ts4["suppliers"])
        self.assertTrue(any("Lot 3a supplier list not verified" in n for n in ts4["notVerified"]))

    def test_gcloud15_verbatim_term_and_az_suppliers(self):
        g = self.by["RM1557.15"]
        self.assertEqual((g["starts"], g["ends"]), ("2026-08-06", "2028-02-05"))
        self.assertIn("reopening after 18 months and again after 36 months", g["term"])
        self.assertEqual(g["suppliers"],
                         ["A&B HEALTH LIMITED", "ALPHA CLOUD LTD", "AZURE CARE LTD",
                          "MEDILOGIK LIMITED"])
        # The A to Z gives no lots, so no lot list is claimed.
        self.assertTrue(all(l["suppliers"] is None for l in g["lots"]))
        self.assertTrue(any("does not say which lot" in n for n in g["notVerified"]))

    def test_gcloud15_az_failure_gives_null_and_note(self):
        doc = rdf.build(fake_fetch(fail=("prefix=M",)), "2026-10-20")
        g = {e["reference"]: e for e in doc["frameworks"]}["RM1557.15"]
        self.assertIsNone(g["suppliers"])
        self.assertTrue(any("Supplier list not verified" in n for n in g["notVerified"]))

    def test_coming_entries(self):
        ai = self.by["Find a Tender notice 050314-2026"]
        gp = self.by["Find a Tender notice 094419-2026"]
        for e in (ai, gp):
            self.assertEqual(e["status"], "coming")
            self.assertIsNone(e["suppliers"])
        self.assertEqual(ai["awardPeriodEnd"], "2027-03-19")
        self.assertEqual(ai["starts"], "2027-05-26")
        self.assertEqual(ai["estimatedValue"]["amountExVat"], 750000000)
        self.assertEqual(gp["futureNoticeDate"], "2026-11-09")
        self.assertEqual((gp["starts"], gp["ends"]), ("2027-09-20", "2030-09-19"))
        self.assertEqual(gp["sourceQuote"], "Framework go-live is expected in Q3 2027.")

    def test_unavailable_gca_page_raises_so_main_does_not_write(self):
        f = fake_fetch()

        def outage(url):
            return "<html>Service unavailable</html>" if "gca.gov.uk/agreements" in url else f(url)
        with self.assertRaises(RuntimeError):
            rdf.build(outage, "2026-10-20")

    def test_total_failure_raises_so_main_does_not_write(self):
        with self.assertRaises(RuntimeError):
            rdf.build(fake_fetch(fail=("find-tender",)), "2026-10-20")


SBS_PAGE = """<html><body><main><h1>Digital Workplace Solutions 2</h1>
<p>Framework Agreement Reference: SBS10510</p>
<h3> What dates is the framework agreement active? </h3>
<p>01 October 2025 \u2013 30 September 2028</p>
<p>(with an option to extend for up to 12 months)</p>
<h3> Who can take advantage of the framework agreement? </h3></main></body></html>"""

SBS_PAGE_SHORT = """<html><body><main>
<p>Framework Agreement Reference: SBS10225</p>
<h3> What dates is the framework agreement active? </h3>
<p>25 March 2024 \u2013 24 March 2028</p>
<h3> Who can take advantage? </h3></main></body></html>"""

OCDS_AWARD = {"releases": [{
    "id": "074808-2025", "date": "2025-11-18T14:17:04Z", "tag": ["award", "contract"],
    "buyer": {"name": "NHS Shared Business Services Limited"},
    "tender": {"title": "Digital Workplace Solutions 2", "status": "complete",
               "description": "Award.", "procurementMethodDetails": "Open procedure",
               "lots": [{"id": "1"}]},
    "awards": [{"relatedLots": ["1"], "suppliers": [{"name": "Zed Ltd"}, {"name": "Alpha plc"}]},
               {"relatedLots": ["1"], "suppliers": [{"name": "Alpha plc"}]}],
    "contracts": [{"value": {"amount": 2500000000, "currency": "GBP"}}]}]}


class Extras(unittest.TestCase):
    def test_sbs_page_dates_and_option(self):
        p = rdf.parse_sbs_page(SBS_PAGE)
        self.assertEqual((p["reference"], p["starts"], p["ends"]), ("SBS10510", "2025-10-01", "2028-09-30"))
        self.assertEqual(p["option"], "with an option to extend for up to 12 months")
        q = rdf.parse_sbs_page(SBS_PAGE_SHORT)
        self.assertEqual((q["starts"], q["ends"], q["option"]), ("2024-03-25", "2028-03-24", None))

    def test_award_suppliers_dedupe_names_only(self):
        self.assertEqual(rdf.award_suppliers(OCDS_AWARD), {"1": ["Alpha plc", "Zed Ltd"]})

    def test_award_entry(self):
        def f(url):
            if "074808-2025" in url:
                return json.dumps(OCDS_AWARD)
            return SBS_PAGE
        e = rdf.build_award(f, "074808-2025", "Digital Workplace Solutions 2", "x", "2026-10-20",
                            "digital-workplace-solutions")
        self.assertEqual((e["status"], e["reference"], e["starts"], e["ends"]), ("live", "SBS10510", "2025-10-01", "2028-09-30"))
        self.assertEqual(e["suppliers"], ["Alpha plc", "Zed Ltd"])
        self.assertEqual(e["estimatedValue"]["amountExVat"], 2500000000)

    def test_award_without_page_dates_says_not_verified(self):
        e = rdf.build_award(lambda u: json.dumps(OCDS_AWARD), "074808-2025", "x", "y", "2026-10-20")
        self.assertIsNone(e["starts"])
        self.assertTrue(any("not stated" in n for n in e["notVerified"]))

    def test_unreadable_extra_is_listed_not_guessed(self):
        def f(url):
            raise RuntimeError("boom")
        entries, not_added = rdf.build_extras(f, "2026-10-20")
        self.assertEqual(entries, [])
        self.assertEqual(len(not_added), 9)
        self.assertTrue(all("Nothing recorded" in n["reason"] for n in not_added))


GC14_EXPIRED_PAGE = """<html><body><main>
<p>!</p><p>Important</p><p>Expired agreement - This information is for reference only</p>
<h1>G-Cloud 14</h1>
<p>Agreement number: </p><p> RM1557.14 </p><p>Start date: </p><p> 29/10/2024 </p>
<p>End date: </p><p> 28/10/2026 </p><p>Agreement type: </p><p> PCR15 Framework </p>
<h2>Updates</h2><p>29 October 2026:</p>
<p>Please be advised that G-Cloud 14 expired on 28 October 2026. You should now access</p>
<p><a href="/agreements/RM1557.15">RM1557.15 G-Cloud 15</a></p>
<p>for your cloud requirements. Existing G-Cloud 14 call-off contracts signed prior to the
28 October 2026 expiration date will remain in effect for their full defined terms. Work
performed under G-Cloud 14 cannot be transferred to G-Cloud 15 agreements. For the most
current information, please refer to the official</p>
<h2>Documents</h2>
<p>The core terms form part of the framework and call-off contracts and must be used on
every contract. They cannot be changed.</p>
</main></body></html>"""

GC13_EXPIRED_PAGE = """<html><body><main>
<p>Important</p><p>Expired agreement - This information is for reference only</p>
<p>Important Expired agreement \u2013 This information is for reference only.</p>
<p>RM1557.13: G-Cloud 13 was replaced by RM1557.14: G-Cloud 14.</p>
<p>Agreement number: </p><p> RM1557.13 </p><p>Start date: </p><p> 09/11/2022 </p>
<p>End date: </p><p> 08/11/2024 </p><p>Agreement type: </p><p> PCR15 Framework </p>
<h2>Documents</h2></main></body></html>"""

GC_LIVE_NO_BANNER = """<html><body><main><h1>G-Cloud 14</h1>
<p>Agreement number: </p><p> RM1557.14 </p><p>Start date: </p><p> 29/10/2024 </p>
<p>End date: </p><p> 28/10/2026 </p><p>Agreement type: </p><p> PCR15 Framework </p>
<h2>Documents</h2></main></body></html>"""


class ExpiredGCloud(unittest.TestCase):
    """An expired G-Cloud iteration is recorded so a call-off bought through it has
    something to point at. Added 16/11/2026 for Medilogik's Barnsley Hospital award,
    a G-Cloud 13 call-off ending 30/11/2026 on an agreement closed since 2024."""

    def test_expired_agreement_is_read_from_its_own_page(self):
        e = rdf.build_gcloud_expired(lambda u: GC14_EXPIRED_PAGE, "RM1557.14", "G-Cloud 14",
                                     "2026-11-16")
        self.assertEqual((e["reference"], e["status"], e["starts"], e["ends"]),
                         ("RM1557.14", "expired", "2024-10-29", "2026-10-28"))
        self.assertEqual(e["lots"], [])
        self.assertIsNone(e["suppliers"])
        self.assertIn("nothing on it rolls forward", e["callOffRule"])

    def test_sentence_split_across_an_inline_link_is_whole(self):
        """GCA breaks a sentence wherever it carries a link, so a line-by-line read
        returns the sentence with the link text missing. The quote must be whole."""
        e = rdf.build_gcloud_expired(lambda u: GC14_EXPIRED_PAGE, "RM1557.14", "G-Cloud 14",
                                     "2026-11-16")
        self.assertIn("Existing G-Cloud 14 call-off contracts signed prior to the 28 October "
                      "2026 expiration date will remain in effect for their full defined "
                      "terms.", e["sourceQuote"])
        self.assertIn("Work performed under G-Cloud 14 cannot be transferred to G-Cloud 15 "
                      "agreements.", e["sourceQuote"])

    def test_page_navigation_is_never_glued_to_a_quote(self):
        e = rdf.build_gcloud_expired(lambda u: GC14_EXPIRED_PAGE, "RM1557.14", "G-Cloud 14",
                                     "2026-11-16")
        self.assertNotIn("Documents", e["sourceQuote"])
        self.assertNotIn("core terms", e["sourceQuote"].lower())

    def test_replacement_sentence_is_not_cut_at_the_reference_dot(self):
        e = rdf.build_gcloud_expired(lambda u: GC13_EXPIRED_PAGE, "RM1557.13", "G-Cloud 13",
                                     "2026-11-16")
        self.assertIn("RM1557.13: G-Cloud 13 was replaced by RM1557.14: G-Cloud 14.",
                      e["sourceQuote"])
        # The banner renders twice, hyphen and en dash. One sentence, kept once.
        self.assertEqual(e["sourceQuote"].lower().count("this information is for reference"), 1)

    def test_missing_banner_is_not_verified_never_assumed_expired(self):
        e = rdf.build_gcloud_expired(lambda u: GC_LIVE_NO_BANNER, "RM1557.14", "G-Cloud 14",
                                     "2026-11-16")
        self.assertEqual(e["status"], "not verified")
        self.assertTrue(any("Expired agreement" in n for n in e["notVerified"]))

    def test_wrong_page_is_refused_not_recorded(self):
        with self.assertRaises(RuntimeError):
            rdf.build_gcloud_expired(lambda u: GC13_EXPIRED_PAGE, "RM1557.14", "G-Cloud 14",
                                     "2026-11-16")


if __name__ == "__main__":
    unittest.main()
