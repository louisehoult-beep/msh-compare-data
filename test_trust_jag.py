#!/usr/bin/env python3
"""test_trust_jag.py - prove scripts/refresh_trust_jag.py reads the JAG participating
services register from a fixture, joins organisations to the trust map by exact name
only, and keeps honest empty states.

  python3 test_trust_jag.py     exit 0 = pass. No network. Stdlib only.
"""
import datetime as dt
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_trust_jag as R  # noqa: E402

TODAY = dt.date(2026, 11, 16)

TRUST_MAP = {"trusts": [
    {"n": "Barnsley Hospital NHS Foundation Trust", "code": "RFF", "icb": "QF7",
     "icbName": "South Yorkshire", "region": "North East and Yorkshire", "nation": "England"},
    {"n": "East Sussex Healthcare NHS Trust", "code": "RXC", "icb": "S9B9J",
     "icbName": "Surrey and Sussex", "region": "South East", "nation": "England"},
    {"n": "Cardiff & Vale University Local Health Board", "code": "7A4", "icb": None,
     "icbName": None, "region": "Wales", "nation": "Wales"},
    {"n": "Betsi Cadwaladr University Local Health Board", "code": "7A1", "icb": None,
     "icbName": None, "region": "Wales", "nation": "Wales"},
    {"n": "Isle of Wight NHS Trust", "code": "R1F", "icb": "QRL",
     "icbName": "Hampshire and Isle of Wight", "region": "South East", "nation": "England"},
]}


def row(country, region, sector, ap, org, service, sites, status):
    return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>Not set</td><td>%s</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (country, region, sector, ap, org, service, sites, service, status))


def page(*rows):
    return ("<html><body><table id=\"tblParticipatingServices\"><thead><tr><th>Country</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></body></html>"
            + "x" * 60000)


ROWS = (
    row("England", "North East and Yorkshire", "Acute / large", "Adult",
        "Barnsley Hospital NHS Foundation Trust", "Barnsley District General Hospital", "",
        "Accredited"),
    row("England", "South East", "Acute / large", "Adult", "East Sussex Healthcare NHS Trust",
        "East Sussex Healthcare NHS Trust",
        "Conquest Hospital, Eastbourne District General Hospital", "Deferred"),
    row("England", "South East", "Independent non-acute", "Adult",
        "East Sussex Healthcare NHS Trust", "Sussex Premier Health", "",
        "Undergoing self-assessment/not assessed"),
    row("England", "South East", "Acute / large", "Adult", "Isle Of Wight NHS Foundation Trust",
        "St Mary's Hospital", "", "Accredited"),
    row("Wales", "Wales", "Acute / large", "Adult", "Betsi Cadwaladr University LHB",
        "Ysbyty Gwynedd", "", "Undergoing self-assessment/not assessed"),
    row("Wales", "Wales", "Acute / large", "Adult", "Cardiff &amp; Vale University Health Board",
        "University Hospital of Wales", "", "Accredited"),
    row("England", "London", "Independent non-acute", "Adult", "Nuffield Health",
        "Nuffield Health Something", "", "Accredited"),
    row("Scotland", "Scotland", "Acute / large", "Adult", "NHS Lothian",
        "Western General Hospital", "", "Undergoing self-assessment/not assessed"),
)


class Register(unittest.TestCase):
    def setUp(self):
        self.doc = R.build(page(*ROWS), TRUST_MAP, TODAY)

    def test_every_row_is_read(self):
        self.assertEqual(self.doc["counts"]["services"], 8)
        self.assertEqual(self.doc["summary"]["byStatus"]["Accredited"], 4)
        self.assertEqual(self.doc["summary"]["byCountry"]["Wales"]["services"], 2)

    def test_a_trust_with_two_services_keeps_both_statuses(self):
        """A row is a service, not a trust. One badge for the organisation would be a
        claim the register does not make."""
        t = [x for x in self.doc["trusts"] if x["code"] == "RXC"][0]
        self.assertEqual(t["services"], 2)
        self.assertEqual(t["accredited"], 0)
        self.assertEqual(t["statuses"], {"Deferred": 1,
                                         "Undergoing self-assessment/not assessed": 1})
        self.assertEqual(t["jagServices"][0]["sites"],
                         ["Conquest Hospital", "Eastbourne District General Hospital"])

    def test_welsh_lhb_abbreviation_joins(self):
        self.assertIn("7A1", [t["code"] for t in self.doc["trusts"]])

    def test_named_aliases_join_and_are_recorded(self):
        codes = [t["code"] for t in self.doc["trusts"]]
        self.assertIn("7A4", codes)   # Cardiff and Vale, the register drops "Local"
        self.assertIn("R1F", codes)   # Isle of Wight, the register adds "Foundation"
        names = {a["registerName"] for a in self.doc["aliases"]}
        self.assertEqual(names, set(R.ALIASES))
        self.assertTrue(all(a["why"] for a in self.doc["aliases"]))

    def test_an_organisation_that_does_not_join_is_listed_never_guessed(self):
        un = {u["organisation"]: u for u in self.doc["unmatched"]}
        self.assertIn("Nuffield Health", un)
        self.assertIn("NHS Lothian", un)
        self.assertEqual(un["NHS Lothian"]["country"], "Scotland")
        self.assertEqual(un["Nuffield Health"]["statuses"], {"Accredited": 1})
        joined = {t["name"] for t in self.doc["trusts"]}
        self.assertNotIn("Nuffield Health", joined)

    def test_counts_add_up(self):
        c = self.doc["counts"]
        self.assertEqual(c["servicesJoined"] + sum(u["services"] for u in self.doc["unmatched"]),
                         c["services"])
        self.assertEqual(c["trustsJoined"], len(self.doc["trusts"]))

    def test_a_status_the_register_invents_is_reported_not_bucketed(self):
        extra = ROWS + (row("England", "London", "Acute / large", "Adult",
                            "Barnsley Hospital NHS Foundation Trust", "New Service", "",
                            "Provisionally accredited"),)
        doc = R.build(page(*extra), TRUST_MAP, TODAY)
        self.assertEqual(doc["unknownStatuses"], ["Provisionally accredited"])

    def test_a_missing_table_is_refused_not_parsed_as_empty(self):
        with self.assertRaises(RuntimeError):
            R.build("<html><body><p>maintenance</p></body></html>", TRUST_MAP, TODAY)

    def test_an_empty_table_is_refused(self):
        with self.assertRaises(RuntimeError):
            R.build(page(), TRUST_MAP, TODAY)

    def test_the_rule_travels_with_the_data(self):
        for field in ("rule", "source", "sourceUrl", "dataAsOf", "statusValues"):
            self.assertTrue(self.doc.get(field))
        self.assertIn("one endoscopy SERVICE, not one trust", self.doc["rule"])


if __name__ == "__main__":
    unittest.main()
