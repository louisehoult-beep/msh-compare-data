#!/usr/bin/env python3
"""Invariants for the digital health lane and the Federated Data Platform profile
(20/10/2026). Stdlib only, no network.

    python3 test_digital_lane.py
"""
import datetime
import json
import os
import sys
import unittest


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import digital_lane_rules as R  # noqa: E402
import refresh_digital_lane as L  # noqa: E402
import refresh_fdp_live as F  # noqa: E402
import refresh_atamis as A  # noqa: E402
import refresh_open_tenders as OT  # noqa: E402


class Rules(unittest.TestCase):

    def test_lane_needs_nhs_buyer_and_cpv_48_or_72(self):
        self.assertTrue(R.in_lane("Medway NHS Foundation Trust", ["48000000"]))
        self.assertTrue(R.in_lane("NHS Somerset Integrated Care Board", ["72212000"]))
        self.assertTrue(R.in_lane("Cwm Taf Morgannwg University Health Board", ["48180000"]))
        self.assertFalse(R.in_lane("Medway NHS Foundation Trust", ["33100000"]))
        # Bare "Trust" is not an NHS buyer: academy and housing trusts flood the feed.
        self.assertFalse(R.in_lane("Oak Academy Trust", ["48000000"]))
        self.assertFalse(R.in_lane("", ["48000000"]))

    def test_clinical_flag_is_specific(self):
        for t in ["NECTAR Electronic Patient Record", "Ambient Voice Technology - Pilot",
                  "Chest X-Ray Artificial Intelligence Solution", "BSOL LIMS - PME",
                  "Virtual Ward Service", "PN426 Electronic Prescribing System ESP",
                  "One-Off PACS Interface Integration Project"]:
            with self.subTest(t=t):
                self.assertTrue(R.clinical(t))
        # The words the digital speciality rule refuses never flag a row on their own.
        for t in ["Annual Licence", "Cloud License Renewal", "Learning Management System",
                  "Provision of DocuSign eSignature", "GP IT and Corporate IT Support",
                  "EPRR Training VR Project", "Digital Printing Services"]:
            with self.subTest(t=t):
                self.assertFalse(R.clinical(t))

    def test_atamis_category_stands_in_for_cpv(self):
        self.assertTrue(R.digital_category("Software package and information systems"))
        self.assertTrue(R.digital_category("IT"))
        self.assertTrue(R.digital_category("Specialist Software (SaaS)"))
        for c in ["Network Cables", "Telecoms", "Medical equipments pharmaceuticals and personal care products",
                  "Computer Hardware Accessories Printer / Copier Hire / Lease", ""]:
            with self.subTest(c=c):
                self.assertFalse(R.digital_category(c))


class Atamis(unittest.TestCase):

    def test_classify_adds_digital_labels_without_touching_the_others(self):
        self.assertEqual(A.classify("Hoist servicing", "", "", "Medical equipment"), [])
        self.assertEqual(A.classify("UHB Patient Companion - PME", "", "", "Information technology services"),
                         ["pre_market_engagement", "digital"])
        self.assertEqual(A.classify("Fertility EPR System", "", "", "Software package and information systems"),
                         ["digital", "digital_clinical"])

    def test_lane_keeps_only_open_digital_engagement(self):
        today = "2026-10-20"
        doc = {"opportunities": [
            {"name": "BSOL LIMS - PME", "category": "Information technology services",
             "deadline": "2026-11-01", "authority": "University Hospitals Birmingham NHS FT"},
            {"name": "Fertility EPR System", "category": "Software package and information systems",
             "deadline": "2026-11-01"},                         # digital, but no engagement label
            {"name": "Market engagement - hoists", "category": "Medical equipment",
             "deadline": "2026-11-01"},                         # engagement, not digital
            {"name": "AI market engagement", "category": "IT", "deadline": "2026-10-01"},  # closed
        ]}
        rows = L.atamis_rows(doc, today)
        self.assertEqual([r["title"] for r in rows], ["BSOL LIMS - PME"])
        self.assertTrue(rows[0]["clinical"])
        self.assertEqual(rows[0]["lane"], "digital")


class Awards(unittest.TestCase):

    def test_award_rows_apply_the_rule_and_tag_every_row(self):
        fa = {"awards": [
            {"title": "NECTAR Electronic Patient Record", "buyer": {"name": "The Newcastle Upon Tyne Hospitals NHS Foundation Trust"},
             "cpv": ["48000000", "72000000"], "tag": ["award", "contract"], "published": "2026-10-01",
             "suppliers": [{"name": "X Ltd"}], "contracts": [{"value": 10, "end": "2030-01-01"}]},
            {"title": "Annual Licence", "buyer": {"name": "Barts Health NHS Trust"}, "cpv": ["48000000"],
             "tag": ["planning"], "published": "2026-09-01"},
            {"title": "Hoists", "buyer": {"name": "Barts Health NHS Trust"}, "cpv": ["33190000"], "tag": ["award"]},
            {"title": "Payroll", "buyer": {"name": "Some Council"}, "cpv": ["48000000"], "tag": ["award"]},
        ]}
        rows = L.award_rows(fa)
        self.assertEqual([r["title"] for r in rows], ["NECTAR Electronic Patient Record", "Annual Licence"])
        self.assertEqual([r["clinical"] for r in rows], [True, False])
        self.assertEqual(rows[0]["stage"], "award")
        self.assertEqual(rows[1]["stage"], "planning")
        self.assertTrue(all(r["lane"] == "digital" for r in rows))

    def test_lane_keep_reads_the_headline_and_additional_cpv(self):
        t = {"classification": {"scheme": "CPV", "id": "33100000"},
             "additionalClassifications": [{"scheme": "CPV", "id": "48180000"}]}
        self.assertTrue(L.lane_keep(t, "anything", "Leeds Teaching Hospitals NHS Trust"))
        self.assertFalse(L.lane_keep({"classification": {"scheme": "CPV", "id": "33100000"}},
                                     "Electronic Patient Record", "Leeds Teaching Hospitals NHS Trust"))

    def test_open_tenders_default_rule_is_unchanged(self):
        # The medical feed still drops a software notice under an NHS buyer.
        rel = {"id": "x", "buyer": {"name": "Leeds Teaching Hospitals NHS Trust"},
               "tender": {"title": "EPR software licence", "status": "active",
                          "classification": {"scheme": "CPV", "id": "48000000"}}}
        self.assertIsNone(OT.row_from_release(rel, "Find a Tender", "2026-10-20"))
        row = OT.row_from_release(rel, "Find a Tender", "2026-10-20", keep=L.lane_keep)
        self.assertIsNotNone(row)

    def test_merge_open_drops_closed_notices(self):
        old = {"openNotices": [{"url": "a", "closingDate": "2026-10-01"},
                               {"url": "b", "closingDate": "2026-12-01"}]}
        got = L.merge_open([{"url": "c", "closingDate": None}], old, "2026-10-20")
        self.assertEqual([r["url"] for r in got], ["b", "c"])


UPTAKE = """<main><p>The next update will be in December 2026.</p>
<p>The data below was updated on 25 September 2026.</p>
<p>2 – number of NHS trusts that are live on the NHS Federated Data Platform*</p>
<p>* The number of NHS trusts that are live on the NHS Federated Data Platform as at end of August 2026.</p>
<p>1 – number of NHS integrated care boards that are on the NHS Federated Data Platform*</p>
<p>3 – number of NHS trusts that have signed up to the NHS Federated Data Platform*</p>
<p>1 – number of NHS integrated care boards that have signed up to the NHS Federated Data Platform*</p></main>"""
LIVE = """<main><h1>Live</h1><h2>NHS trusts</h2><ol><li>Alder Hey Children’s NHS Foundation Trust</li>
<li>Renamed Old NHS Trust</li></ol><h2>Integrated care boards (ICBs)</h2><ol><li>NHS Devon ICB</li></ol></main>"""
SIGNUP = """<main><h2>NHS trusts signed up to the NHS FDP</h2><ol><li>Alder Hey Children's NHS Foundation Trust</li>
<li>Barts Health NHS Trust</li><li>Renamed Old NHS Trust</li></ol>
<h2>NHS integrated care boards (ICBs) signed up to the NHS FDP</h2><ol><li>NHS Devon ICB</li></ol></main>"""
MAP = {"trusts": [{"n": "Alder Hey Children's NHS Foundation Trust", "code": "RBS"},
                  {"n": "Barts Health NHS Trust", "code": "R1H"},
                  {"n": "Airedale NHS Foundation Trust", "code": "RCF"}]}


class Fdp(unittest.TestCase):

    def setUp(self):
        self.doc = F.build(UPTAKE, LIVE, SIGNUP, MAP, datetime.date(2026, 10, 20))

    def test_headline_and_dates_are_the_sources_own(self):
        self.assertEqual(self.doc["headline"], {"trustsLive": 2, "icbsLive": 1,
                                                "trustsSignedUp": 3, "icbsSignedUp": 1})
        self.assertEqual(self.doc["sourceUpdatedOn"], "25 September 2026")
        self.assertEqual(self.doc["sourceNextUpdate"], "December 2026")
        self.assertTrue(all(c["agrees"] for c in self.doc["countCheck"]))

    def test_exact_join_curly_apostrophe_and_no_fuzzy_match(self):
        by = {t["code"]: t for t in self.doc["trusts"]}
        self.assertTrue(by["RBS"]["fdpLive"])        # curly apostrophe normalised
        self.assertFalse(by["R1H"]["fdpLive"])
        self.assertTrue(by["R1H"]["fdpSignedUp"])
        self.assertFalse(by["RCF"]["fdpLive"])
        self.assertEqual(self.doc["unmatched"], ["Renamed Old NHS Trust"])

    def test_icbs(self):
        self.assertEqual(self.doc["icbs"], [{"name": "NHS Devon ICB", "fdpLive": True, "fdpSignedUp": True}])


class StoredFiles(unittest.TestCase):
    """The committed files pass their own stated rules."""

    def test_digital_lane_file(self):
        p = os.path.join(HERE, "data", "digital-lane.json")
        if not os.path.exists(p):
            self.skipTest("digital-lane.json not built")
        doc = _load(p)
        for r in doc["awards"] + doc["openNotices"]:
            self.assertTrue(R.in_lane(r["buyer"], r.get("digitalCpv") or [r.get("cpv")]), r["title"])
            self.assertEqual(r["clinical"], R.clinical(r["title"]))
        for k in ("awards", "openNotices", "marketEngagement"):
            self.assertEqual(doc["counts"][k], len(doc[k]))

    def test_medical_feeds_carry_no_lane_rows(self):
        for name, key in (("open-tenders.json", "notices"),):
            doc = _load(os.path.join(HERE, "data", name))
            self.assertFalse(any(r.get("lane") for r in doc.get(key) or []))

    def test_digital_panel_shows_clinical_rows_only(self):
        p = os.path.join(HERE, "data", "speciality-panels", "digital-and-medical-it.json")
        doc = _load(p)
        lane = doc.get("digitalLane")
        self.assertIsNotNone(lane)
        for k in ("openNotices", "marketEngagement", "awards"):
            self.assertTrue(all(r["clinical"] for r in lane[k]), k)
        self.assertEqual(doc["label"], "Digital health and AI")


if __name__ == "__main__":
    unittest.main(verbosity=1)
