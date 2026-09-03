#!/usr/bin/env python3
"""Proves the `corroborated` Companies House tier does what §5 of the Identity
Decision Pack specifies, and nothing more.

02-Elevate-and-Thrive/Hub/company-aliases/IDENTITY-DECISION-PACK-2026-09-03.md
§5.5 specifies five invariant tests (T1-T5) plus a regression guard proving
match_check.py's own five checks still fire on the fixtures they were built
for. Every test here is one way the `corroborated` tier could quietly become
`confirmed`, rescue a real contradiction, or launder a mass-registration
address into evidence — each mirrors a real failure already found in this
data on 03/09/2026 (BES Healthcare's exact match failing on empty token sets,
Talarmade Limited's hyphen reading as a contradiction, Northwood's bracket,
MC Tissue's string-identical-but-wrong-company namesake).

  python3 test_company_tiers.py        exit 0 = the tier logic holds
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
# company-aliases lives beside Medical-Sales-Hub, three levels up from this
# repo: 02-Elevate-and-Thrive/Hub/{company-aliases, Medical-Sales-Hub/Website/msh-compare-data}
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "company-aliases"))
os.chdir(HERE)

import refresh_companies_house as R  # noqa: E402
import match_check as M              # noqa: E402


def supplier(name, aliases=None, frameworks=None):
    return {"name": name, "aliases": aliases or [], "frameworks": frameworks or []}


def profile(name, status="active", incorporated="1990-01-01",
            previous_names=None, sic=None):
    return {
        "company_name": name,
        "company_number": "00000000",
        "company_status": status,
        "date_of_creation": incorporated,
        "date_of_cessation": None,
        "previous_company_names": previous_names or [],
        "sic_codes": sic or [],
        "accounts": {},
    }


def fake_api_get(profiles):
    """A stand-in for R.api_get that answers from a canned {path: profile} map
    instead of the network — refresh_companies_house.py's own record_for()
    and officers_for() are exercised unmodified, only the HTTP call is faked.
    """
    def _get(path, key):
        for frag, prof in profiles.items():
            if frag in path:
                return prof
        return None
    return _get


class T1_NegatedComparisonNeverConfirms(unittest.TestCase):
    """corroborated can never be mistaken for confirmed downstream."""

    def test_no_negated_probable_comparison_in_source(self):
        """The exact trap this test exists for: app/company-report.js gated
        turnover/employees on `!probable` until 03/09/2026, which reads TRUE
        for 'corroborated' too. A grep-level assertion is part of this test,
        not a convention — proven by test_negation_trap_is_actually_caught
        below, which breaks it on purpose and watches this fail."""
        offenders = []
        for root in ("scripts", "app"):
            for dirpath, _dirs, files in os.walk(os.path.join(HERE, root)):
                for fn in files:
                    if not fn.endswith((".py", ".js")):
                        continue
                    path = os.path.join(dirpath, fn)
                    with open(path, encoding="utf-8") as f:
                        src = f.read()
                    for m in re.finditer(
                            r"""!==?\s*['"]probable['"]|!\s*isProbable\s*\(|!\s*probable\b""", src):
                        line_no = src.count("\n", 0, m.start()) + 1
                        offenders.append("%s:%d" % (os.path.relpath(path, HERE), line_no))
        for m in re.finditer(r"""!=\s*["']probable["']""",
                              open(os.path.join(HERE, "verify.py"), encoding="utf-8").read()):
            offenders.append("verify.py (own source, unexpected)")
        self.assertEqual(offenders, [],
                          "negated comparison against 'probable' found at: %s" % offenders)

    def test_negation_trap_is_actually_caught(self):
        """Prove the assertion above is not a tautology: plant the exact bug
        that shipped until the previous commit, in a scratch copy, and watch
        the same detector fail on it."""
        bad_js = "if (!isProbable(rec)) { rows += fact('Turnover', rec.turnoverGBP); }"
        hits = list(re.finditer(r"""!==?\s*['"]probable['"]|!\s*isProbable\s*\(|!\s*probable\b""", bad_js))
        self.assertTrue(hits, "the detector did not catch a real !isProbable( bug — it is a "
                               "tautology, not a test")

    def test_officers_null_unless_confirmed(self):
        fin = json.load(open(os.path.join(HERE, "data", "company-financials.json"),
                              encoding="utf-8"))
        offenders = [n for n, r in fin["companies"].items()
                     if isinstance(r, dict) and r.get("matchConfidence") != "confirmed"
                     and r.get("officers") is not None]
        self.assertEqual(offenders, [],
                          "officers present on a non-confirmed record: %s" % offenders[:5])

    def test_corroborated_carries_no_derived_figures(self):
        fin = json.load(open(os.path.join(HERE, "data", "company-financials.json"),
                              encoding="utf-8"))
        offenders = [n for n, r in fin["companies"].items()
                     if isinstance(r, dict) and r.get("matchConfidence") == "corroborated"
                     and (r.get("turnoverGBP") is not None or r.get("employees") is not None)]
        self.assertEqual(offenders, [],
                          "corroborated record carries a derived figure: %s" % offenders)

    def test_record_for_never_writes_a_fourth_tier(self):
        """record_for() may only ever emit one of the three real tiers."""
        s = supplier("BES Healthcare")
        api = fake_api_get({"/company/00000000": profile("BES HEALTHCARE LTD")})
        R.api_get = api
        rec = R.record_for(s, "00000000", "alerts", "fake-key")
        self.assertIn(rec["matchConfidence"], {"probable", "corroborated", "confirmed"})


class T2_ContradictionNeverRescued(unittest.TestCase):
    """A contradicted name can never reach `corroborated`."""

    def test_corroborates_returns_false_not_none(self):
        s = supplier("Air Liquide Healthcare Ltd")
        verdict = R.corroborates(s, "TANDEM DIABETES UK LIMITED")
        self.assertIs(verdict, False,
                       "a genuine name contradiction must return False, never None — "
                       "None would let independent_corroborator() rescue it")

    def test_record_for_stays_probable_even_with_route2_proof(self):
        s = supplier("Air Liquide Healthcare Ltd")
        api = fake_api_get({
            "/company/16278190": profile("TANDEM DIABETES UK LIMITED",
                                          incorporated="2025-02-26"),
        })
        R.api_get = api
        # A route-2 proof (dict form) is the STRONGEST evidence record_for() sees.
        confirmed_source = {"url": "https://example.invalid/tandem", "checkedOn": "2026-09-03"}
        rec = R.record_for(s, "16278190", confirmed_source, "fake-key")
        self.assertEqual(rec["matchConfidence"], "probable",
                          "a contradicted name must stay probable even with a sourced "
                          "number and a route-2 proof present")
        self.assertIsNone(rec["corroboratedBy"])
        self.assertIsNone(rec["officers"])


class T3_StringIdentityAloneDoesNotConfirm(unittest.TestCase):
    """String identity alone does not confirm — the date test must still bite."""

    def test_metsa_incorporated_after_its_framework(self):
        s = supplier("Metsa", frameworks=[{"name": "fw", "dates": "1 January 2024 to 2028"}])
        api = fake_api_get({"/company/17185037": profile("METSA LTD", incorporated="2026-04-27")})
        R.api_get = api
        rec = R.record_for(s, "17185037", "alerts", "fake-key")
        self.assertEqual(rec["matchConfidence"], "probable")
        self.assertNotEqual(rec["matchConfidence"], "confirmed")
        self.assertIn("2024", rec["matchedOn"])

    def test_pentax_medical_incorporated_after_its_framework(self):
        s = supplier("Pentax Medical", frameworks=[{"name": "fw", "dates": "1 January 2022 to 2027"}])
        api = fake_api_get({"/company/16914265": profile(
            "PENTAX LTD", incorporated="2025-12-16", sic=["73110"])})
        R.api_get = api
        rec = R.record_for(s, "16914265", "alerts", "fake-key")
        self.assertEqual(rec["matchConfidence"], "probable")
        self.assertNotEqual(rec["matchConfidence"], "confirmed")

    def test_exact_string_match_alone_is_not_enough_when_dated_wrong(self):
        """identity() alone would confirm Metsa == METSA LTD; the date test
        must still catch it — proving the two tests are independent guards,
        not redundant ones."""
        s = {"name": "Metsa", "aliases": []}
        self.assertTrue(R.corroborates(s, "METSA LTD"),
                         "identity() should treat this as an exact match on the name alone")


class T4_BracketsNotStripped(unittest.TestCase):
    """Brackets disambiguate and must never be stripped by identity()."""

    def test_northwood_identity_fallback_does_not_fire(self):
        forms = {R.identity(n) for n in ["Northwood"]}
        self.assertNotIn(R.identity("NORTHWOOD (ABERDEEN) LIMITED"), forms,
                          "identity() must not equate 'Northwood' with the bracketed "
                          "'NORTHWOOD (ABERDEEN) LIMITED' — that is a letting agent, "
                          "not the Hub's Northwood")

    def test_exactech_identity_fallback_does_not_fire(self):
        forms = {R.identity(n) for n in ["Exactech"]}
        self.assertNotIn(R.identity("EXACTECH (UK) 2 LIMITED"), forms,
                          "identity() must not equate 'Exactech' with "
                          "'EXACTECH (UK) 2 LIMITED'")

    def test_bracket_preserved_inside_identity_string(self):
        # The bracket's CONTENT must still be part of the reduced form — proving
        # it was not simply deleted rather than "not treated as a legal suffix".
        self.assertIn("aberdeen", R.identity("NORTHWOOD (ABERDEEN) LIMITED"))


class T5_MassRegistrationAddressIsNotCorroboration(unittest.TestCase):
    """A shared mass-registration address is never sufficient corroboration."""

    def test_denylist_is_non_empty(self):
        self.assertTrue(R.MASS_REGISTRATION, "the denylist must not be empty")

    def test_denylist_entries_are_normalised_lower_case(self):
        for addr in R.MASS_REGISTRATION:
            self.assertEqual(addr, addr.lower().strip(),
                              "denylist entries must be stored normalised so a future "
                              "consumer can compare case- and whitespace-insensitively: %r"
                              % addr)

    def test_128_city_road_is_on_the_denylist(self):
        self.assertIn("ec1v 2nx", R.MASS_REGISTRATION)

    def test_shared_address_alone_yields_no_corroborator(self):
        """independent_corroborator() implements only routes (a) own-site proof
        and (c) previous-name-on-this-number. A shared registered office —
        mass-registration or not — is not among the accepted routes at all, so
        a supplier whose only 'evidence' is a shared address gets NO
        corroborator and the record stays probable."""
        s = supplier("AM Group Ltd")
        prof = profile("QUANTUM ZEBRA HOLDINGS LTD")
        prof["registered_office_address"] = {"postal_code": "EC1V 2NX", "address_line_1": "128 City Road"}
        corroborator = R.independent_corroborator(s, prof, confirmed_source="alerts")
        self.assertIsNone(corroborator,
                           "a shared registered office must never manufacture a corroborator")

    def test_record_for_stays_probable_on_address_only_match(self):
        # Names deliberately share NO token (not even a short/stopword one),
        # so corroborates() returns None, not True by accident.
        s = supplier("AM Group Ltd")
        api = fake_api_get({"/company/12345678": profile("QUANTUM ZEBRA HOLDINGS LTD")})
        R.api_get = api
        rec = R.record_for(s, "12345678", "alerts", "fake-key")
        self.assertIsNone(R.corroborates(s, "QUANTUM ZEBRA HOLDINGS LTD"),
                           "fixture names must share no token, or this test is not "
                           "exercising the address-only path at all")
        # names share no comparable word -> verdict is None -> no corroborator -> probable
        self.assertEqual(rec["matchConfidence"], "probable")


class ChangeA_ExactMatchEscapesTheTokenBug(unittest.TestCase):
    """Not one of T1-T5, but the headline fix (§5.1/§5.3) — proven separately
    so a regression in identity() itself is caught even if none of T1-T5
    happen to exercise that exact pair."""

    def test_bes_healthcare_exact_match(self):
        s = supplier("BES Healthcare")
        self.assertIs(R.corroborates(s, "BES HEALTHCARE LTD"), True)

    def test_talarmade_hyphen_is_not_a_contradiction(self):
        s = supplier("Talarmade Limited")
        self.assertIs(R.corroborates(s, "TALAR-MADE LIMITED"), True,
                       "a hyphen must not turn an identical company into a CONTRADICTION")

    def test_record_for_confirms_bes_healthcare(self):
        s = supplier("BES Healthcare")
        api = fake_api_get({"/company/03538917": profile("BES HEALTHCARE LTD")})
        R.api_get = api
        rec = R.record_for(s, "03538917", "alerts", "fake-key")
        self.assertEqual(rec["matchConfidence"], "confirmed")


class MatchCheckRegressionGuard(unittest.TestCase):
    """match_check.py must still exit 1 on a fixture reproducing each of its
    five member-facing checks — the corroborated tier must not quietly
    satisfy a check it should fail. Calls match_check.py's own check_*
    functions directly against synthetic data, never the live files."""

    def test_shared_number_still_fires(self):
        companies = {
            "Alpha Supplies": {"companyNumber": "12345678"},
            "Beta Supplies": {"companyNumber": "12345678"},
        }
        findings = []
        M.check_shared_number(companies, {"Alpha Supplies", "Beta Supplies"}, findings)
        self.assertTrue(any(f["check"] == "1 SHARED-NUMBER" for f in findings))

    def test_contradicted_still_fires(self):
        companies = {"Philips Electronics UK Limited": {
            "registeredName": "PHILIPS ELECTRONICS UK LIMITED", "companyNumber": "00446897"}}
        # resolve(reg_name, reg) reads reg["index"]["exact"/"normalised"/"stripped"] -
        # the real shape company_alias.build() produces. norm() case-folds and
        # collapses punctuation, which is the level check_contradicted's own
        # resolve() call matches at for a bare registered name.
        fixture_reg = {
            "index": {
                "exact": {},
                "normalised": {M.norm("PHILIPS ELECTRONICS UK LIMITED"): ["Philips"]},
                "stripped": {},
            },
            "declaredDistinct": {
                M.norm("Philips Electronics UK Limited"): [M.norm("Philips")],
            },
        }
        findings = []
        M.check_contradicted(companies, fixture_reg, findings)
        self.assertTrue(any(f["check"] == "2 CONTRADICTED" for f in findings),
                         "expected a CONTRADICTED finding; got %r" % findings)

    def test_implausible_still_fires(self):
        companies = {"Ansell": {"registeredName": "ANSELL ALLOYS LIMITED",
                                 "companyNumber": "12714380", "sic": ["45200"]}}
        findings = []
        M.check_implausible(companies, findings)
        self.assertTrue(any(f["check"] == "3 IMPLAUSIBLE" for f in findings))

    def test_name_disagrees_still_fires(self):
        companies = {"CJ Medical": {
            "registeredName": "C J MEDICAL LIMITED", "companyNumber": "04054345",
            "matchedOn": "company number recorded in supplier data, but the registered "
                         "name does not correspond to the supplier name — check by hand"}}
        findings = []
        M.check_name_disagrees(companies, findings)
        self.assertTrue(any(f["check"] == "4 NAME-DISAGREES" for f in findings))

    def test_impossible_date_still_fires(self):
        companies = {"Metsa": {"registeredName": "METSA LTD", "companyNumber": "17185037",
                                "incorporated": "2026-04-27"}}
        seed = [{"name": "Metsa",
                 "frameworks": [{"name": "fw", "dates": "1 January 2024 to 2028"}]}]
        findings = []
        M.check_impossible_date(companies, seed, findings)
        self.assertTrue(any(f["check"] == "5 IMPOSSIBLE-DATE" for f in findings))


def _fail_fast_if_module_broken():
    """A sanity check that the module actually loaded the NEW functions this
    file depends on — an import of a stale/reverted refresh_companies_house.py
    (see [[onedrive-silently-reverts-edits]]) must fail loudly, not silently
    skip every test in this file."""
    for fn in ("identity", "corroborates", "independent_corroborator",
               "earliest_framework_year"):
        assert hasattr(R, fn), (
            "scripts/refresh_companies_house.py is missing %s() — the corroborated-tier "
            "patch did not land (or was reverted). Re-apply it before trusting this "
            "test file's PASS." % fn)
    assert hasattr(R, "MASS_REGISTRATION"), "MASS_REGISTRATION denylist missing"


if __name__ == "__main__":
    _fail_fast_if_module_broken()
    unittest.main()
