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


if __name__ == "__main__":
    unittest.main(verbosity=2)
