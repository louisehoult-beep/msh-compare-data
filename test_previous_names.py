#!/usr/bin/env python3
"""Register-sourced previous names: searchable, evidenced, and NEVER a merge.

Added 03/09/2026. Companies House records a change of registered NAME against
one company number, so a member who knows a supplier by its old name should
still find it. What the register does NOT record is whether the business behind
the name was sold, split or bought — so a shared previous name is a lead, never
proof that two Hub records are one company.

That distinction is the whole reason for this file. Healthcare 25 Ltd's
registered previous name is GEMINI SURGICAL UK LTD, and the seed also holds a
SEPARATE `Gemini Surgical UK` record. Aliasing the old name onto Healthcare 25
would quietly merge two records on a name alone — the exact move the alias
registry exists to refuse (see the Sigma Healthcare case in
ALIAS-REVIEW-QUEUE.md, where three different companies have held one name).
Rename-versus-sale is Lou's open decision and no automated step may pre-empt it.

  python3 -m unittest test_previous_names       exit 0 = the rule holds
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "company-aliases")))
from company_alias import norm_stripped  # noqa: E402

SEED = json.load(open(os.path.join(HERE, "data", "supplier-seed.json")))["suppliers"]
FIN = json.load(open(os.path.join(HERE, "data", "company-financials.json")))["companies"]
BY_NAME = {s["name"]: s for s in SEED}


class PreviousNamesAreEvidenced(unittest.TestCase):
    def test_every_previous_name_cites_the_register(self):
        """Never hand-typed. A previous name without its number is unciteable."""
        for s in SEED:
            for p in (s.get("previousNames") or []):
                self.assertTrue(p.get("name"), "%s: nameless previousNames entry" % s["name"])
                self.assertIn("Companies House", p.get("source", ""),
                              "%s / %s: no register source" % (s["name"], p.get("name")))
                self.assertTrue(str(p.get("sourceUrl", "")).startswith(
                    "https://find-and-update.company-information.service.gov.uk/company/"),
                    "%s / %s: source URL is not a Companies House record"
                    % (s["name"], p.get("name")))
                self.assertTrue(p.get("readOn"), "%s / %s: no read date" % (s["name"], p.get("name")))

    def test_previous_names_are_searchable(self):
        """The point of the exercise: the old name must be an alias, because
        build_supplier_index.py and build_search_index.py both read aliases and
        nothing else. An index-only alias is destroyed by the nightly rebuild."""
        for s in SEED:
            aliases = {norm_stripped(a) for a in (s.get("aliases") or [])}
            for p in (s.get("previousNames") or []):
                self.assertIn(norm_stripped(p["name"]), aliases,
                              "%s records previous name %r but it is not an alias, so no "
                              "search will ever find it" % (s["name"], p["name"]))


class PreviousNamesAreNotAMerge(unittest.TestCase):
    # Two name forms were already claimed by two suppliers before any previous
    # name was added, and both are known open items, not regressions:
    #   cardiac services  - the ^o143 five-record Uniphar Medtech cluster
    #   gs medical        - the declared AMBIGUOUS case in the registry README
    #                       (GS MEDICAL HEALTHCARE LTD inside GBUK vs GS MEDICAL
    #                       LIMITED NI659208), which must stay ambiguous forever
    # They are listed so that a NEW collision still fails this test.
    KNOWN_PRE_EXISTING = {"cardiac services", "gs medical"}

    def test_no_previous_name_is_claimed_by_another_supplier(self):
        """The guard. A previous name that is already another supplier's own
        name or alias must NOT have been added — that is a merge by the back
        door, done on a name alone."""
        owners = {}
        for s in SEED:
            for v in [s["name"]] + list(s.get("aliases") or []):
                if not v:
                    continue
                owners.setdefault(norm_stripped(v), set()).add(s["name"])
        bad = {}
        for s in SEED:
            for p in (s.get("previousNames") or []):
                k = norm_stripped(p["name"])
                others = owners.get(k, set()) - {s["name"]}
                if others:
                    bad[p["name"]] = "%s vs %s" % (s["name"], sorted(others))
        self.assertEqual(bad, {},
                         "a registered previous name was added to one supplier while another "
                         "supplier already claims it. That merges two records on a name: %s" % bad)

    def test_no_new_two_supplier_name_collisions(self):
        """Belt and braces: the whole seed, minus the two known open cases."""
        owners = {}
        for s in SEED:
            for v in [s["name"]] + list(s.get("aliases") or []):
                if v:
                    owners.setdefault(norm_stripped(v), set()).add(s["name"])
        clashes = {k: sorted(v) for k, v in owners.items()
                   if len(v) > 1 and k not in self.KNOWN_PRE_EXISTING}
        self.assertEqual(clashes, {},
                         "new name forms are claimed by more than one supplier: %s" % clashes)

    def test_gemini_surgical_was_not_folded_into_healthcare_25(self):
        """The live example, asserted by name because it is the one that matters.

        Healthcare 25 Ltd IS registered as formerly Gemini Surgical UK Ltd, and
        the Companies House panel says so. But the two seed records stay
        separate until Lou decides rename-versus-sale."""
        self.assertIn("Gemini Surgical UK", BY_NAME, "the separate record must survive")
        h25 = BY_NAME["Healthcare 25 Ltd"]
        aliases = {norm_stripped(a) for a in (h25.get("aliases") or [])}
        self.assertNotIn(norm_stripped("Gemini Surgical UK Ltd"), aliases,
                         "Gemini Surgical UK Ltd must NOT be an alias of Healthcare 25 Ltd — "
                         "that folds a separate supplier record in on a name alone")
        self.assertNotIn(norm_stripped("Gemini Surgical UK"), aliases)

    def test_the_register_still_records_the_rename_for_display(self):
        """Refusing the alias must not lose the fact. The bracketed display in
        app/company-report.js reads previousNames off company-financials.json,
        so the connection is still visible to a member — without asserting it."""
        rec = FIN.get("Healthcare 25 Ltd") or {}
        prev = {(p.get("name") or "").upper() for p in (rec.get("previousNames") or [])}
        self.assertIn("GEMINI SURGICAL UK LTD", prev,
                      "the register fact must survive even though the alias was refused")


if __name__ == "__main__":
    unittest.main(verbosity=2)
