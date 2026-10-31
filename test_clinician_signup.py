#!/usr/bin/env python3
"""Clinician programme sign-up: the WPCode snippet's rules.

hub/wpcode/clinician-signup.php cleans each sign-up (msh_cp_clean), refuses
one without the agreement and data-consent ticks or with a stale agreement
version, and builds the two emails. The welcome must carry the agreement
copy and the booking link; Lou's must carry the CV link.

Stdlib only; skipped, loudly, where php is missing.

    python3 test_clinician_signup.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PHP_SNIPPET = os.path.join(HERE, "hub", "wpcode", "clinician-signup.php")

PHP_STUBS = r"""
function add_action() {}
function add_filter() {}
function add_shortcode() {}
"""
PHP_RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  $fn = $c[0]; $a = $c[1];
  if ($fn === 'clean') { $out[] = msh_cp_clean($a[0], $a[1], $a[2]); }
  elseif ($fn === 'welcome') { $out[] = msh_cp_welcome_email($a[0], $a[1], $a[2]); }
  elseif ($fn === 'lou') { $out[] = msh_cp_lou_email($a[0], $a[1], $a[2]); }
  elseif ($fn === 'live') { $out[] = msh_cp_live(); }
  elseif ($fn === 'options') { $out[] = msh_cp_options(); }
}
echo json_encode($out);
"""

GOOD = {
    "first_name": "Jo", "last_name": "Bloggs", "email": "Jo@Example.com", "phone": "07700 900123",
    "region": "east-midlands", "postcode": "ln6 ", "icb": "Lincolnshire", "travel": "region",
    "relocate": "maybe", "licence": "full", "profession": "nurse", "pin": "12a3456e",
    "regstatus": "live", "band": "6", "current_role": "Theatre sister", "employer": "nhs",
    "years": "9", "specialities": ["theatres", "wound-care", "made-up"], "roles": ["clinical-specialist"],
    "availability": "3-months", "agreement": "1", "agreement_version": "v1", "gdpr": "1",
    "linkedin": "https://www.linkedin.com/in/jo", "source": "ANTT!",
}
NOW = "2026-10-31T12:00:00Z"


@unittest.skipUnless(shutil.which("php"), "php not installed: snippet rules NOT tested")
class SignupRules(unittest.TestCase):
    def run_php(self, cases):
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as t:
            src = open(PHP_SNIPPET).read().replace("<?php", "", 1)
            t.write("<?php\n" + PHP_STUBS + src + PHP_RUN)
        try:
            r = subprocess.run(["php", t.name, json.dumps(cases)], capture_output=True, text=True, check=True)
            return json.loads(r.stdout)
        finally:
            os.unlink(t.name)

    def test_clean_good(self):
        (c,) = self.run_php([["clean", [GOOD, NOW, "v1"]]])
        self.assertEqual(c["errors"], [])
        r = c["record"]
        self.assertEqual(r["email"], "jo@example.com")
        self.assertEqual(r["postcode"], "LN6")
        self.assertEqual(r["pin"], "12A3456E")
        self.assertEqual(r["specialities"], ["theatres", "wound-care"])
        self.assertEqual(r["years"], 9)
        self.assertEqual(r["source"], "antt")
        self.assertEqual(r["agreement_version"], "v1")
        self.assertEqual(r["agreement_accepted"], NOW)
        self.assertEqual(r["gdpr_consent"], NOW)

    def test_ticks_and_version_required(self):
        bad = dict(GOOD, agreement="", gdpr="")
        stale = dict(GOOD)
        (a, b) = self.run_php([["clean", [bad, NOW, "v1"]], ["clean", [stale, NOW, "v2"]]])
        self.assertIn("agreement", a["errors"])
        self.assertIn("gdpr", a["errors"])
        self.assertEqual(a["record"]["agreement_accepted"], "")
        self.assertIn("agreement", b["errors"])

    def test_field_checks(self):
        bad = dict(GOOD, email="nope", phone="123", postcode="LN6 7TS", pin="", specialities=[], roles=["x"],
                   linkedin="https://evil.example", years="lots", region="mars")
        (c,) = self.run_php([["clean", [bad, NOW, "v1"]]])
        for k in ("email", "phone", "postcode", "pin", "specialities", "roles", "linkedin", "years", "region"):
            self.assertIn(k, c["errors"])
        pending = dict(GOOD, pin="", regstatus="pending")
        (p,) = self.run_php([["clean", [pending, NOW, "v1"]]])
        self.assertNotIn("pin", p["errors"])

    def test_emails(self):
        (c,) = self.run_php([["clean", [GOOD, NOW, "PLACEHOLDER-v0"]]])
        r = dict(c["record"], agreement_version="PLACEHOLDER-v0", agreement_accepted=NOW, first_name="Jo<b>")
        w, l, live = self.run_php([["welcome", [r, "CLN-ABC123", "https://book.example/x"]],
                                   ["lou", [r, "CLN-ABC123", "https://hub.example/cv?t=1"]], ["live", []]])
        self.assertIn("CLN-ABC123", w["subject"])
        self.assertIn("https://book.example/x", w["html"])
        self.assertIn("PLACEHOLDER", w["html"])          # agreement copy present
        self.assertNotIn("Jo<b>", w["html"])               # escaped
        self.assertIn("https://hub.example/cv?t=1", l["html"])
        self.assertIn("Integrated Care Board (ICB) area", l["html"])
        self.assertFalse(live)                             # placeholder keeps the form shut

    def test_options_keys_slug_safe(self):
        (o,) = self.run_php([["options", []]])
        import re
        for lst, items in o.items():
            for k in items:
                self.assertRegex(k, r"^[a-z0-9-]+$", lst)


if __name__ == "__main__":
    unittest.main()
