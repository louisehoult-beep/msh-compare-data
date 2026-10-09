#!/usr/bin/env python3
"""Proves the dead-company publish gate still catches what it was built for.

^o238. On 03/09/2026 three suppliers were showing paying members a struck-off
company as their identity:

  HC21 (UK) Ltd            MISS TINA'S HC21 LTD, a takeaway dissolved 18/09/2018
  Gemini Surgical UK       GEMINI SURGICAL INNOVATIONS (U.K.) LIMITED, dissolved 27/06/2017
  Semperit Investments Asia SEMPERIT INVESTMENTS ASIA PTE LTD, struck off 11/03/2025

None was caught by anything. match_check.py had five checks and none of them
asked whether the matched company was still alive, and app/company-report.js
renders the registered name before its `!probable` gate, so the caveat withheld
the figures and not the identity. They were found by re-reading an OUTSTANDING
line, which is not a control.

This test reintroduces the real records against a COPY of the repo and asserts
verify.py refuses to publish them. It also asserts the gate does NOT fire on a
supplier that is genuinely dissolved, because a check that cries wolf on the
true ones is a check people learn to route around — Emmat Medical (^o204) and
BK Medical UK are real, correct, dissolved records and a supplier going under
is intelligence a member wants.

  python3 -m unittest test_dead_company_check     exit 0 = the gate holds
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

# The three real records, as they stood before they were cleared.
HC21 = {
    "companyNumber": "10939295", "registeredName": "MISS TINA'S HC21 LTD",
    "matchConfidence": "probable", "matchedOn": "name search on Companies House",
    "status": "dissolved", "incorporated": "2017-08-31", "dissolvedOn": "2018-09-18",
    "sic": ["56102"], "accountsCategory": None, "accountsCategoryRaw": None,
    "accountsCategoryNote": None, "accountsMadeUpTo": None,
    "turnoverGBP": None, "employees": None, "officers": None,
    "sourceUrl": "https://find-and-update.company-information.service.gov.uk/company/10939295",
}
GEMINI = dict(HC21, companyNumber="09955180",
              registeredName="GEMINI SURGICAL INNOVATIONS (U.K.) LIMITED",
              incorporated="2016-01-18", dissolvedOn="2017-06-27", sic=[])


def _run_verify(root):
    return subprocess.run([sys.executable, os.path.join(HERE, "verify.py"),
                           "--root", root, "--offline"],
                          capture_output=True, text=True, cwd=HERE)


class DeadCompanyGate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="deadco-")
        shutil.copytree(os.path.join(HERE, "data"), os.path.join(self.root, "data"))
        # Symlinked, not copied: assets/ is large and read-only to every check,
        # and a copy that omits it makes 200 logo checks fail for reasons that
        # have nothing to do with this test.
        # scripts/ and company-aliases/ are REQUIRED, not optional extras: verify.py
        # calls os.chdir(root) for a --root run (see verify.py's own comment on that
        # line), and every one of its `sys.path.insert(0, "scripts")` /
        # `sys.path.insert(0, "company-aliases")` calls is relative — so once chdir'd
        # into this temp root, those imports resolve against IT, not the real repo.
        # Omitting them here isn't a missing nice-to-have: it makes every check that
        # imports from either directory silently unable to run, which is exactly the
        # class of silent gap this test file exists to catch elsewhere. Found
        # 15/09/2026 when this test failed with "No module named 'company_match'"
        # etc. on an otherwise-unrelated change, and reproduced identically on a
        # clean, unmodified checkout — confirming it was always broken, not a
        # regression from that change.
        for extra in ("app", "docs", "assets", "sitemap-cache", "state", "hooks",
                      "scripts", "company-aliases"):
            src = os.path.join(HERE, extra)
            if os.path.isdir(src):
                os.symlink(src, os.path.join(self.root, extra))
        self.fin_path = os.path.join(self.root, "data", "company-financials.json")
        self.seed_path = os.path.join(self.root, "data", "supplier-seed.json")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, name, rec):
        doc = json.load(open(self.fin_path))
        doc["companies"][name] = rec
        json.dump(doc, open(self.fin_path, "w"), indent=1)

    def _seed_framework_years(self, name):
        doc = json.load(open(self.seed_path))
        for s in doc["suppliers"]:
            if s.get("name") == name:
                return [f.get("dates") for f in (s.get("frameworks") or [])]
        return []

    def test_baseline_copy_passes(self):
        """The untouched copy must pass, or the rest of this proves nothing."""
        r = _run_verify(self.root)
        self.assertEqual(r.returncode, 0,
                         "baseline copy failed:\n%s" % r.stdout[-3000:])

    def test_hc21_takeaway_is_refused(self):
        self.assertTrue(self._seed_framework_years("HC21 (UK) Ltd"),
                        "HC21 must hold a framework for this test to mean anything")
        self._write("HC21 (UK) Ltd", HC21)
        r = _run_verify(self.root)
        self.assertNotEqual(r.returncode, 0, "the gate let a dissolved takeaway publish")
        self.assertIn("MISS TINA'S HC21 LTD", r.stdout)
        self.assertIn("cannot be the holder", r.stdout)

    def test_gemini_dissolved_2017_is_refused(self):
        # Found 15/09/2026: "Gemini Surgical UK", the original supplier this
        # test used, no longer exists anywhere in data/supplier-seed.json (no
        # record, no alias, no company-financials entry) — removed from the
        # Hub's data since this test was written on 03/09/2026, for reasons
        # this test can't see. Without a seed record carrying a framework
        # date, injecting a fake company-financials.json entry under that name
        # gave the gate NOTHING to compare a dissolution date against, so it
        # could never fire — the test was silently checking nothing, not
        # confirming the gate holds (it passed "0 == 0" by accident, not by
        # the gate working).
        #
        # Fixed by re-pointing this test at a real, CURRENT supplier instead
        # of trying to keep Gemini alive artificially: "365 Healthcare" holds
        # a real framework starting 2 May 2023 and has no existing
        # company-financials.json entry (so nothing here can collide with a
        # live record — everything in this test runs against a throwaway
        # tempdir copy, never the real data). The fictional dissolved company
        # this test injects (GEMINI SURGICAL INNOVATIONS (U.K.) LIMITED,
        # dissolved 27/06/2017 — well before 2023) is unchanged; only the
        # supplier name it's attached to changed, so the assertion this test
        # makes is exactly the one it always made: a company that died years
        # before its earliest framework cannot be that framework's holder.
        supplier = "365 Healthcare"
        self.assertTrue(self._seed_framework_years(supplier),
                        "%s must hold a framework in data/supplier-seed.json "
                        "for this test to mean anything." % supplier)
        self._write(supplier, GEMINI)
        r = _run_verify(self.root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("GEMINI SURGICAL INNOVATIONS", r.stdout)

    def test_a_genuinely_dissolved_supplier_does_not_fail(self):
        """The distinction the whole check rests on.

        Same supplier, same dissolved status — but it died AFTER its earliest
        framework, so it plausibly held it. That is true, it is useful, and it
        must warn rather than block.
        """
        later = dict(HC21, companyNumber="10939295", dissolvedOn="2030-01-01",
                     registeredName="HEALTHCARE 21 (UK) LIMITED")
        self._write("HC21 (UK) Ltd", later)
        r = _run_verify(self.root)
        self.assertEqual(r.returncode, 0,
                         "a supplier that dissolved after its framework must not block "
                         "the publish:\n%s" % r.stdout[-2000:])

    def test_active_company_is_untouched(self):
        doc = json.load(open(self.fin_path))
        self.assertEqual(doc["companies"]["Talley"]["status"], "active")
        r = _run_verify(self.root)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
