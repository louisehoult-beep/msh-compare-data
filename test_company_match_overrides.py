#!/usr/bin/env python3
"""Proves the curated match-override mechanism still catches what it was built for.

^o96, open since 22/08/2026: a wrong Companies House match fixed by hand in
data/company-financials.json was silently re-made by the next nightly name
search, because refresh_companies_house.py rebuilds that file from scratch. On
03/09/2026, 35 suppliers were publishing a wrong company's registered name and
number to paying members — a dissolved takeaway (MISS TINA'S HC21 LTD), a Paris
railway branch (HITACHI RAIL SYSTEMS FRANCE UK BRANCH), a Richmond advertising
agency (PENTAX LTD) — because app/company-report.js renders the identity rows
BEFORE its `!probable` gate, so the caveat withheld the figures and not the name.

Every test below is one way that fix could silently stop working.

  python3 test_company_match_overrides.py        exit 0 = the guard holds
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
os.chdir(HERE)

import refresh_companies_house as R  # noqa: E402

OVERRIDES = json.load(open(R.OVERRIDES, encoding="utf-8"))
ENTRIES = OVERRIDES["overrides"]
FIN = json.load(open(R.OUT, encoding="utf-8"))["companies"]


class OverrideFileShape(unittest.TestCase):
    def test_every_entry_carries_its_evidence(self):
        """An override with no reason is an unreviewable decision."""
        for name, e in ENTRIES.items():
            self.assertTrue(e.get("reason"), "%s: no reason" % name)
            self.assertTrue(e.get("decidedOn"), "%s: no decidedOn" % name)
            self.assertTrue(e.get("exclude"), "%s: no exclude list" % name)

    def test_a_corrected_number_cites_two_independent_sources(self):
        """Lou's rule, 03/09/2026: one source is not enough to assert an identity."""
        for name, e in ENTRIES.items():
            if e.get("correct"):
                srcs = e.get("correctSources") or []
                self.assertGreaterEqual(
                    len(srcs), 2,
                    "%s sets a corrected number with %d source(s); two independent "
                    "sources are required" % (name, len(srcs)))

    def test_a_corrected_number_is_never_also_excluded(self):
        for name, e in ENTRIES.items():
            if e.get("correct"):
                self.assertNotIn(e["correct"].upper(),
                                 {n.upper() for n in e["exclude"]},
                                 "%s both sets and excludes the same number" % name)

    def test_overrides_name_real_suppliers(self):
        """A stale override reads as protection and provides none."""
        seed = {s["name"] for s in json.load(open(R.SEED, encoding="utf-8"))["suppliers"]}
        index = json.load(open(R.INDEX, encoding="utf-8"))
        index_names = {s.get("name") for s in (index.get("suppliers") or index.get("companies") or [])}
        known = seed | index_names
        for name in ENTRIES:
            self.assertIn(name, known, "%s is in the override file but not a supplier" % name)


class OverrideLogic(unittest.TestCase):
    def test_excluded_number_is_refused(self):
        s = {"name": "Hitachi Medical Systems UK Ltd"}
        excluded, correct = R.override_for(s, ENTRIES)
        self.assertIn("FC041492", excluded)
        self.assertIsNone(correct)

    def test_corrected_number_is_returned(self):
        s = {"name": "HC21 (UK) Ltd"}
        excluded, correct = R.override_for(s, ENTRIES)
        self.assertEqual(correct, "05020682")
        self.assertIn("10939295", excluded, "the dissolved takeaway must stay excluded")

    def test_a_correct_without_sources_is_refused(self):
        """The uncitable-proof rule, same as website_proof()."""
        fake = {"X": {"correct": "01234567", "exclude": []}}
        _, correct = R.override_for({"name": "X"}, fake)
        self.assertIsNone(correct)

    def test_a_malformed_correct_is_refused(self):
        fake = {"X": {"correct": "not-a-number", "correctSources": ["a", "b"], "exclude": []}}
        _, correct = R.override_for({"name": "X"}, fake)
        self.assertIsNone(correct)

    def test_supplier_with_no_override_is_untouched(self):
        excluded, correct = R.override_for({"name": "Talley"}, ENTRIES)
        self.assertEqual(excluded, set())
        self.assertIsNone(correct)

    def test_cleared_record_asserts_nothing(self):
        rec = R.cleared_record("03/09/2026")
        for field in ("companyNumber", "registeredName", "status", "incorporated",
                      "sic", "turnoverGBP", "employees", "sourceUrl", "officers"):
            self.assertIsNone(rec[field], "cleared_record leaks %s" % field)
        self.assertEqual(rec["matchConfidence"], "probable",
                         "a cleared record must never read as usable downstream")


class LiveDataMatchesTheDecision(unittest.TestCase):
    def test_excluded_companies_are_not_published(self):
        """The whole point: no supplier still carries a number we excluded for it."""
        for name, e in ENTRIES.items():
            rec = FIN.get(name)
            if not rec:
                continue
            num = (rec.get("companyNumber") or "").upper()
            if not num:
                continue
            self.assertNotIn(num, {n.upper() for n in e["exclude"]},
                             "%s still publishes excluded company %s (%s)"
                             % (name, num, rec.get("registeredName")))

    def test_cleared_records_carry_no_identity(self):
        cleared = [n for n, e in ENTRIES.items() if not e.get("correct")]
        self.assertGreaterEqual(len(cleared), 30)
        for name in cleared:
            rec = FIN.get(name)
            if not rec:
                continue
            self.assertIsNone(rec.get("companyNumber"), "%s still has a number" % name)
            self.assertIsNone(rec.get("registeredName"), "%s still has a name" % name)
            self.assertIsNone(rec.get("officers"), "%s still names officers" % name)

    def test_corrected_records_carry_the_decided_number(self):
        for name, e in ENTRIES.items():
            if not e.get("correct"):
                continue
            rec = FIN.get(name)
            if not rec:
                continue
            self.assertEqual(rec.get("companyNumber"), e["correct"],
                             "%s does not carry its decided number" % name)

    def test_talley_was_not_collateral_damage(self):
        """Talley is a correct `confirmed` match that only appeared in the
        findings as the other half of a shared-number pair. Clearing it would
        have destroyed a good record; this asserts it survived."""
        rec = FIN["Talley"]
        self.assertEqual(rec["companyNumber"], "00520386")
        self.assertEqual(rec["registeredName"], "TALLEY GROUP LIMITED")
        self.assertEqual(rec["matchConfidence"], "confirmed")


class ProseIsNotACuratorAssertion(unittest.TestCase):
    """^o345, 09/09/2026 — route 1 read a curator EXPLAINING a number as one
    ASSERTING it.

    `recorded_number()` finds route-1 numbers with a regex over the supplier's
    own alerts/background/note. On 03/09/2026 the Identity Decision Pack wrote
    research prose into those fields; four records then had a number matched out
    of a sentence whose whole point was that the number is unproved, or is a
    DIFFERENT company. `record_for()` graded those `confirmed` — the top tier,
    which also fetches officers and feeds derived claims — and verify.py refused
    the 07/09/2026 company-intelligence commit because the seed's own
    `companyNumberCandidate` still called the same number unverified.

    Each test below is one way `candidate_refuses()` could silently stop working.
    """

    def _supplier(self, note, candidate):
        s = {"name": "Test Supplier Ltd", "note": note}
        if candidate is not None:
            s["companyNumberCandidate"] = candidate
        return s

    def test_refuses_a_number_its_own_candidate_calls_unverified(self):
        s = self._supplier(
            "Companies House 02559193 — OSSUR UK LIMITED, active.",
            {"number": "02559193",
             "matchedOn": "Companies House name search on 2026-08-14 — NOT verified "
                          "against a number published by the company."})
        number, why, source = R.recorded_number(s)
        self.assertIsNone(number, "an unverified number was taken as route 1")
        self.assertIsNone(source)
        self.assertIn("NOT verified", why)

    def test_refuses_a_sibling_companys_number_named_only_to_distinguish_it(self):
        """Beaver Visitec: the note names 01889847 to say it is a DIFFERENT entity."""
        s = self._supplier(
            "The seed already carries a separate record for Beaver Visitec International "
            "(Companies House 01889847) — that is a DIFFERENT legal entity from this one.",
            {"number": "07289364",
             "matchedOn": "Found by Companies House name search on 2026-09-02."})
        number, why, source = R.recorded_number(s)
        self.assertIsNone(number, "a sibling company's number was taken as route 1")
        self.assertIn("07289364", why)

    def test_a_genuine_curator_assertion_still_confirms(self):
        """The guard must not cost the 246 records that are real route 1."""
        s = self._supplier("Companies House 00520386 — TALLEY GROUP LIMITED.", None)
        number, _why, source = R.recorded_number(s)
        self.assertEqual(number, "00520386")
        self.assertEqual(source, "alerts")

    def test_a_candidate_rewritten_to_say_how_it_was_proved_stops_matching(self):
        """The refusal is a statement about the record, not a permanent block."""
        s = self._supplier(
            "Companies House 02559193 — OSSUR UK LIMITED, active.",
            {"number": "02559193",
             "matchedOn": "Proved from the company's own imprint page publishing 02559193."})
        number, _why, source = R.recorded_number(s)
        self.assertEqual(number, "02559193")
        self.assertEqual(source, "alerts")

    def test_the_four_live_records_are_actually_refused(self):
        """Against the real seed, not a fixture — this is what failed the gate."""
        seed = {s["name"]: s
                for s in json.load(open(R.SEED, encoding="utf-8"))["suppliers"]}
        for name in ("Daniels Health (Sharpsmart)", "Ossur UK Limited",
                     "Ontex Healthcare UK Ltd",
                     "Beaver Visitec International Sales Ltd"):
            with self.subTest(name):
                number, why, source = R.recorded_number(seed[name])
                self.assertIsNone(number, "%s is still anchored by prose" % name)
                self.assertIsNone(source)
                self.assertTrue(why, "%s refused with no reason logged" % name)

    def test_daniels_cleared_number_is_excluded_by_every_route(self):
        """The 03/09 decision said 04261387 is not asserted; the exclude list
        must carry it, or a name search re-attaches it — ^o96 all over again."""
        self.assertIn("04261387",
                      {n.upper() for n in ENTRIES["Daniels Health (Sharpsmart)"]["exclude"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
