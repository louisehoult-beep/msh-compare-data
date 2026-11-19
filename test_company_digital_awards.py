#!/usr/bin/env python3
"""scripts/refresh_company_digital_awards.py: the digital awards layer (20/10/2026).

Proves the three things the layer exists for: a lane award reaches the company the
exact-only rule names; an unresolved name is quarantined, never guessed; and a
notice already in the CPV 33 medical feed for that company is not repeated.

  python3 test_company_digital_awards.py        exit 0 = the layer holds
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import refresh_company_digital_awards as R  # noqa: E402

SEED = {"suppliers": [{"name": "Tortus", "aliases": ["Tortus", "Tortus AI Ltd"]},
                      {"name": "Sectra Limited", "aliases": ["Sectra Limited"]}]}


def lane(*awards):
    return {"laneRule": "r", "clinicalRule": "c", "dataAsOf": "20/10/2026", "awards": list(awards)}


def award(url, *suppliers, stage="award"):
    return {"stage": stage, "title": "T " + url, "buyer": "X NHS Trust", "published": "2026-10-01",
            "url": url, "suppliers": list(suppliers), "value": 1000.0,
            "digitalCpv": ["48000000"], "clinical": False, "lane": "digital"}


class Layer(unittest.TestCase):
    def test_exact_alias_attaches(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/1", "TORTUS AI LTD")), {}, {})
        self.assertEqual([r["noticeSupplierName"] for r in doc["companies"]["Tortus"]], ["TORTUS AI LTD"])
        self.assertEqual(doc["matchRule"], R.company_match.RULE)

    def test_unresolved_is_quarantined(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/2", "Tortus Health Ltd")), {}, {})
        self.assertEqual(doc["companies"], {})
        self.assertEqual(doc["counts"]["unmatched"], 1)

    def test_medical_feed_notice_not_repeated(self):
        url = "https://www.find-tender.service.gov.uk/Notice/3"
        medical = {"companies": {"Sectra Limited": [{"url": url}]}}
        doc = R.build(SEED, lane(award(url, "Sectra Limited")), medical, {})
        self.assertNotIn("Sectra Limited", doc["companies"])
        self.assertEqual(doc["counts"]["alreadyInMedicalFeed"], 1)

    def test_non_award_stages_ignored(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/4", "Sectra Limited",
                                       stage="planning")), {}, {})
        self.assertEqual(doc["counts"]["awardRows"], 0)

    def test_published_rows_are_carried_forward(self):
        url = "https://www.find-tender.service.gov.uk/Notice/5"
        first = R.build(SEED, lane(award(url, "Sectra Limited")), {}, {})
        later = R.build(SEED, lane(), {}, first)
        self.assertEqual(len(later["companies"]["Sectra Limited"]), 1)

    def test_every_row_is_a_lane_row(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/6", "Sectra Limited")), {}, {})
        self.assertTrue(all(r["lane"] == "digital" for rows in doc["companies"].values() for r in rows))


FRAMEWORKS = {"frameworks": [
    {"name": "G-Cloud 13", "reference": "RM1557.13", "status": "expired",
     "starts": "2022-11-09", "ends": "2024-11-08",
     "url": "https://www.gca.gov.uk/agreements/RM1557.13",
     "owner": "Government Commercial Agency (GCA), formerly Crown Commercial Service",
     "callOffRule": "A call-off already signed under this agreement runs to its own end date."},
    {"name": "G-Cloud 12", "reference": "RM1557.12", "status": "expired",
     "starts": "2020-09-28", "ends": "2022-11-27",
     "url": "https://www.gca.gov.uk/agreements/RM1557.12", "owner": "GCA"},
    {"name": "G-Cloud 15", "reference": "RM1557.15", "status": "live",
     "starts": "2026-08-06", "ends": "2028-02-05",
     "url": "https://www.gca.gov.uk/agreements/RM1557.15", "owner": "GCA"},
]}


def call_off(url, supplier, **route):
    """A carried row that states the route its notice named."""
    row = {"title": "T", "buyer": "X NHS Trust", "date": "2024-05-14", "url": url,
           "source": "Contracts Finder", "valueAmount": 1000.0, "valueCurrency": "GBP",
           "periodEnd": "2026-11-30", "isFramework": False, "digitalCpv": ["48311100"],
           "clinical": True, "lane": "digital", "noticeSupplierName": supplier,
           "noticeSupplierCount": 1,
           "procurementMethodDetails": "Call-off from a framework agreement",
           "frameworkRouteStated": True, "frameworkName": None, "frameworkRef": None,
           "frameworkRouteQuote": None}
    row.update(route)
    return {"companies": {}, "unmatched": [row], "ambiguous": []}


class FrameworkRoute(unittest.TestCase):
    """The route a call-off was bought through, and that framework's own status
    (16/11/2026). A call-off on a closed framework runs to its own end date and
    nothing rolls forward, so the contract end is the decision date. Medilogik's
    Barnsley award is a G-Cloud 13 call-off ending 30/11/2026."""

    def test_framework_facts_are_attached_from_the_framework_file(self):
        prev = call_off("https://www.find-tender.service.gov.uk/Notice/10", "Sectra Limited",
                        frameworkName="G-Cloud 13", frameworkRef="RM1557.13")
        doc = R.build(SEED, lane(), {}, prev, FRAMEWORKS)
        row = doc["companies"]["Sectra Limited"][0]
        self.assertEqual(row["frameworkStatus"], "expired")
        self.assertEqual(row["frameworkEnds"], "2024-11-08")
        self.assertEqual(row["frameworkUrl"], "https://www.gca.gov.uk/agreements/RM1557.13")
        self.assertIn("runs to its own end date", row["frameworkCallOffRule"])
        # The contract outlives the framework it was bought through. That is the fact.
        self.assertEqual(row["periodEnd"], "2026-11-30")

    def test_a_name_with_no_reference_still_matches(self):
        """West Hertfordshire's award names G-Cloud 12 and gives no RM number."""
        prev = call_off("https://www.find-tender.service.gov.uk/Notice/11", "Sectra Limited",
                        frameworkName="G-Cloud 12")
        row = R.build(SEED, lane(), {}, prev, FRAMEWORKS)["companies"]["Sectra Limited"][0]
        self.assertEqual(row["frameworkRef"], "RM1557.12")
        self.assertIn("the notice names the framework but gives no agreement number",
                      row["frameworkRefSource"])

    def test_an_unknown_framework_is_left_as_the_notice_stated_it(self):
        prev = call_off("https://www.find-tender.service.gov.uk/Notice/12", "Sectra Limited",
                        frameworkName="Medical IT Framework")
        row = R.build(SEED, lane(), {}, prev, FRAMEWORKS)["companies"]["Sectra Limited"][0]
        self.assertEqual(row["frameworkName"], "Medical IT Framework")
        self.assertNotIn("frameworkStatus", row)
        self.assertNotIn("frameworkRefSource", row)

    def test_a_framework_dropped_from_the_file_leaves_no_stale_facts(self):
        prev = call_off("https://www.find-tender.service.gov.uk/Notice/13", "Sectra Limited",
                        frameworkName="G-Cloud 13", frameworkRef="RM1557.13")
        once = R.build(SEED, lane(), {}, prev, FRAMEWORKS)
        self.assertEqual(once["companies"]["Sectra Limited"][0]["frameworkStatus"], "expired")
        again = R.build(SEED, lane(), {}, once, {"frameworks": []})
        row = again["companies"]["Sectra Limited"][0]
        self.assertNotIn("frameworkStatus", row)
        self.assertNotIn("frameworkUrl", row)

    def test_a_reference_the_hub_supplied_is_not_kept_as_the_notices_own(self):
        prev = call_off("https://www.find-tender.service.gov.uk/Notice/14", "Sectra Limited",
                        frameworkName="G-Cloud 12")
        once = R.build(SEED, lane(), {}, prev, FRAMEWORKS)
        again = R.build(SEED, lane(), {}, once, {"frameworks": []})
        row = again["companies"]["Sectra Limited"][0]
        self.assertIsNone(row["frameworkRef"])
        self.assertNotIn("frameworkRefSource", row)

    def test_a_row_with_no_route_is_untouched(self):
        doc = R.build(SEED, lane(award("https://www.find-tender.service.gov.uk/Notice/15",
                                       "Sectra Limited")), {}, {}, FRAMEWORKS)
        row = doc["companies"]["Sectra Limited"][0]
        self.assertNotIn("frameworkStatus", row)


class RouteReadFromTheNotice(unittest.TestCase):
    """scripts/_seed_endoscopy_ems_awards_1021.py reads the route off the notice.
    Nothing is inferred from the supplier, the buyer or the date."""

    def setUp(self):
        import _seed_endoscopy_ems_awards_1021 as seed
        self.route = seed.framework_route

    def test_gcloud_written_three_ways_normalises_to_one_name(self):
        """Across these notices the same framework is "G-Cloud13", "G-Cloud 14" and
        "G Cloud 12". The quote keeps the buyer's own wording."""
        r = self.route({"procurementMethodDetails": "Call-off from a framework agreement",
                        "description": "Endoscopy Management System\r\n\r\nAdditional "
                                       "information: \r\nAwarded via the Crown Commercial "
                                       "Services G-Cloud13 framework RM1557.13"})
        self.assertEqual((r["frameworkName"], r["frameworkRef"]), ("G-Cloud 13", "RM1557.13"))
        self.assertEqual(r["frameworkRouteQuote"],
                         "Awarded via the Crown Commercial Services G-Cloud13 framework "
                         "RM1557.13")
        self.assertTrue(r["frameworkRouteStated"])

    def test_a_name_with_no_reference_gives_no_reference(self):
        r = self.route({"procurementMethodDetails": "Call-off from a framework agreement",
                        "description": "award for EMS Solution via G-Cloud 12 Digital "
                                       "Marketplace ID 732379006255769 Framework"})
        self.assertEqual(r["frameworkName"], "G-Cloud 12")
        self.assertIsNone(r["frameworkRef"])

    def test_a_framework_the_hub_cannot_name_still_keeps_its_quote(self):
        r = self.route({"procurementMethodDetails": "Call-off from a framework agreement",
                        "description": "Medical IT Framework, Specifically lot 1 - Software"})
        self.assertIsNone(r["frameworkName"])
        self.assertIsNone(r["frameworkRef"])
        self.assertEqual(r["frameworkRouteQuote"],
                         "Medical IT Framework, Specifically lot 1 - Software")

    def test_a_call_off_naming_no_framework_states_no_route(self):
        r = self.route({"procurementMethodDetails": "Call-off from a framework agreement",
                        "description": "Endoscopy management system software and hosting."})
        self.assertFalse(r["frameworkRouteStated"])
        self.assertIsNone(r["frameworkRouteQuote"])
        self.assertEqual(r["procurementMethodDetails"], "Call-off from a framework agreement")

    def test_the_additional_information_label_is_never_the_quote(self):
        r = self.route({"procurementMethodDetails": "x",
                        "description": "Additional information: framework RM1557.14"})
        self.assertEqual(r["frameworkRouteQuote"], "framework RM1557.14")


if __name__ == "__main__":
    unittest.main()
