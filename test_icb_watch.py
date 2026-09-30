#!/usr/bin/env python3
"""Tests for scripts/refresh_icb_watch.py and verify.check_icb_watch (30/09/2026).

Stdlib only, no network: every read is replaced by a fixture, so this runs the
same on Lou's Mac and on the Actions runner.

What is pinned here, and why each one matters:
  * person-title pairing on the three layouts ICB sites use, and the two ways
    it went wrong while being built (a section heading taken for a job title;
    a partner member's own-organisation title taken for an ICB executive);
  * a leadership change is only published against a STORED earlier holder and
    only after the new holder is read on a second day (the 24/07/2026 lesson);
  * a role that stops being found is never reported as a departure;
  * the gate refuses an unsourced named executive, a change that does not say
    what it replaced, and an ICB list that has drifted from the 36.
"""
import copy
import datetime as dt
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, HERE)

import refresh_icb_watch as w          # noqa: E402
import verify as v                     # noqa: E402

LEADERS_URL = w.NHSE_LEADERS


def live_rows():
    return [{"code": c, "odsName": "NHS %s INTEGRATED CARE BOARD" % n.upper(),
             "legalStart": None, "legalEnd": None} for c, (n, _) in w.ICB_REGION.items()]


def leaders_for(overrides=None):
    out = {}
    for c, (n, _) in w.ICB_REGION.items():
        out[w.norm_icb_name(n)] = {"leaders": [{"role": "chair", "name": "Chair %s" % c, "qualifier": None},
                                               {"role": "ceo", "name": "Ceo %s" % c, "qualifier": None}],
                                   "clusterNote": None}
    out[w.norm_icb_name("Birmingham and Solihull")]["clusterNote"] = "Clustering with Black Country ICB."
    out[w.norm_icb_name("Black Country")]["clusterNote"] = "Clustering with Birmingham and Solihull ICB."
    for k, val in (overrides or {}).items():
        out[w.norm_icb_name(k)]["leaders"] = val
    return out


STATEMENT = {"url": w.NHSE_AREA, "text": "Six new ICBs were established ... future decisions ...",
             "hash": "abc"}


def run(prev, day, own=None, leaders=None, statement=STATEMENT):
    return w.build(prev, live_rows(), [], leaders or leaders_for(), "2026-08-21", statement,
                   own, [], day)[0]


def own_with(code, people, url="https://example.icb.nhs.uk/board"):
    return {code: {"people": [dict(p, url=url) for p in people], "errors": [], "urls": [url]}}


D1, D2, D3 = dt.date(2026, 9, 28), dt.date(2026, 9, 29), dt.date(2026, 9, 30)
PHARM_A = {"name": "Alex Example", "title": "Chief Pharmacist", "family": "medicines"}
PHARM_B = {"name": "Sam Sample", "title": "Chief Pharmacist", "family": "medicines"}


class Extraction(unittest.TestCase):
    def test_name_then_title_cards(self):
        lines = ["Members of the Board", "Danielle Oum", "Chair", "David Melbourne",
                 "Chief Executive", "Sally Roberts", "Chief Clinical and Quality Officer",
                 "Paul Athey", "Chief Financial Officer"]
        got = {(p["name"], p["family"]) for p in w.extract_people(lines)}
        self.assertIn(("Sally Roberts", "nursing"), got)
        self.assertIn(("Paul Athey", "cfo"), got)
        # Chair and chief executive come from NHS England's list, never an ICB page.
        self.assertFalse({f for _, f in got} & {"chair", "ceo"})

    def test_one_line_form(self):
        got = w.extract_people(["Hemant Patel, Chief Pharmacy Officer, Director of Medicines "
                                "and Clinical Policy"])
        self.assertEqual(got[0]["name"], "Hemant Patel")
        self.assertEqual(got[0]["family"], "medicines")

    def test_section_heading_is_not_a_title(self):
        # Black Country's board page, 30/09/2026: a heading sits above the first name.
        lines = ["Our Executive", "Chief Finance and Chief Nursing Officers", "Paul Athey",
                 "Chief Financial Officer", "Sally Roberts", "Chief Nurse"]
        got = [(p["name"], p["title"]) for p in w.extract_people(lines)]
        self.assertNotIn(("Paul Athey", "Chief Finance and Chief Nursing Officers"), got)
        self.assertIn(("Paul Athey", "Chief Financial Officer"), got)
        self.assertIn(("Sally Roberts", "Chief Nurse"), got)

    def test_partner_member_is_not_an_icb_executive(self):
        lines = ["Jonathan Brotherton",
                 "Group Chief Executive at University Hospitals Birmingham NHS Foundation Trust",
                 "Richard Kirby", "Chief Executive of Birmingham Community Healthcare NHS Foundation Trust"]
        self.assertEqual(w.extract_people(lines), [])

    def test_accented_name_pairs_with_its_own_title(self):
        lines = ["Roísìn Fallon-Williams", "Chief Executive of a Trust",
                 "Richard Kirby", "Chief Executive of Another Trust"]
        # Both are partner titles, so nothing — and crucially Kirby is never given
        # the title that belongs to the line above him.
        for p in w.extract_people(lines):
            self.assertNotEqual(p["name"], "Richard Kirby")

    def test_title_then_name_one_line(self):
        got = w.extract_people(["Chief finance officer - Mark Bakewell"])
        self.assertEqual((got[0]["name"], got[0]["family"]), ("Mark Bakewell", "cfo"))

    def test_partner_after_comma(self):
        self.assertIsNone(w.role_family("Chief Executive, Sirona care & health"))
        self.assertEqual(w.role_family("Executive Director of Nursing, NHS Norfolk and Suffolk "
                                       "Integrated Care Board"), "nursing")

    def test_deputy_is_not_the_role_holder(self):
        self.assertIsNone(w.role_family("Deputy Chief Medical Officer"))


class ChangeDetection(unittest.TestCase):
    def test_first_run_is_a_baseline_with_no_leadership_events(self):
        doc = run({}, D1, own=own_with("QHL", [PHARM_A]))
        self.assertFalse([e for e in doc["events"] if e["kind"] == "leadership"])
        self.assertEqual(doc["count"], 36)
        self.assertEqual(doc["clusters"], [["QHL", "QUA"]])

    def test_new_holder_needs_a_second_day(self):
        base = run({}, D1, own=own_with("QHL", [PHARM_A]))
        day2 = run(copy.deepcopy(base), D2, own=own_with("QHL", [PHARM_B]))
        self.assertFalse([e for e in day2["events"] if e["kind"] == "leadership"],
                         "a single sighting must not publish a change")
        self.assertTrue(day2["pending"])
        names = {e["name"] for e in next(i for i in day2["icbs"] if i["code"] == "QHL")["execs"]}
        self.assertNotIn("Sam Sample", names, "an unconfirmed holder must not be listed yet")
        day3 = run(copy.deepcopy(day2), D3, own=own_with("QHL", [PHARM_B]))
        evs = [e for e in day3["events"] if e["kind"] == "leadership"]
        self.assertEqual(len(evs), 1)
        self.assertIn("Sam Sample", evs[0]["headline"])
        self.assertIn("Alex Example", evs[0]["detail"])
        v.fails[:] = []
        v.check_icb_watch(day3, today_iso="2026-09-30")
        self.assertEqual(v.fails, [])

    def test_role_that_disappears_is_not_a_departure(self):
        base = run({}, D1, own=own_with("QHL", [PHARM_A]))
        later = run(copy.deepcopy(base), dt.date(2026, 10, 30), own=own_with("QHL", []))
        self.assertFalse(later["events"])
        kept = next(i for i in later["icbs"] if i["code"] == "QHL")["execs"]
        self.assertEqual(kept[0]["name"], "Alex Example")
        self.assertTrue(kept[0].get("stale"))

    def test_nhse_ceo_change_confirmed_on_day_two(self):
        base = run({}, D1)
        newl = leaders_for({"Greater Manchester": [
            {"role": "chair", "name": "Chair QOP", "qualifier": None},
            {"role": "ceo", "name": "New Person", "qualifier": "interim"}]})
        d2 = run(copy.deepcopy(base), D2, leaders=newl)
        self.assertFalse(d2["events"])
        d3 = run(copy.deepcopy(d2), D3, leaders=newl)
        self.assertEqual(len(d3["events"]), 1)
        self.assertIn("Interim chief executive is now New Person (was Ceo QOP)",
                      d3["events"][0]["headline"])

    def test_national_statement_change_is_an_event(self):
        base = run({}, D1)
        changed = dict(STATEMENT, text="Mergers confirmed for April 2027.", hash="def")
        d2 = run(copy.deepcopy(base), D2, statement=changed)
        self.assertEqual([e["kind"] for e in d2["events"]], ["national"])


class Gate(unittest.TestCase):
    def setUp(self):
        v.fails[:] = []
        v.warns[:] = []
        self.doc = run({}, D3, own=own_with("QHL", [PHARM_A]))

    def fails(self):
        v.check_icb_watch(self.doc, today_iso="2026-09-30")
        return " ".join(m for _, m in v.fails)

    def test_clean_document_passes(self):
        self.assertEqual(self.fails(), "")

    def test_unsourced_named_executive_fails(self):
        qhl = next(i for i in self.doc["icbs"] if i["code"] == "QHL")
        qhl["execs"][0]["url"] = ""
        self.assertIn("no https source", self.fails())

    def test_change_that_does_not_say_what_it_replaced_fails(self):
        self.doc["events"].append({"date": "2026-09-30", "icb": "QHL", "kind": "leadership",
                                   "headline": "QHL: someone is the new chief pharmacist",
                                   "detail": "x", "sources": ["https://example.nhs.uk/"]})
        self.assertIn("does not say what it replaced", self.fails())

    def test_icb_list_drift_fails(self):
        self.doc["icbs"] = self.doc["icbs"][:-1]
        self.doc["count"] = len(self.doc["icbs"])
        self.assertIn("no longer matches the 36", self.fails())

    def test_curated_event_without_verification_fails(self):
        self.doc["events"].append({"date": "2026-09-14", "icb": "QHL", "kind": "curated",
                                   "headline": "h", "detail": "d",
                                   "sources": ["https://example.nhs.uk/x.pdf"]})
        self.assertIn("no verifiedOn", self.fails())

    def test_future_event_fails(self):
        self.doc["events"].append({"date": "2026-12-01", "icb": "QHL", "kind": "curated",
                                   "headline": "h", "detail": "d", "verifiedOn": "2026-09-30",
                                   "sources": ["https://example.nhs.uk/x.pdf"]})
        self.assertIn("future date", self.fails())


if __name__ == "__main__":
    unittest.main(verbosity=1)
