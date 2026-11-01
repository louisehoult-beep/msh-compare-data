#!/usr/bin/env python3
"""Clinician programme sign-up: the WPCode snippet's rules.

hub/wpcode/clinician-signup.php cleans each sign-up (msh_cp_clean), refuses
one without box 1 (the CSP programme agreement) or with a stale agreement or
privacy notice version, stores boxes 2 (KORE sharing) and 3 (updates) as
given, and builds the two emails. The welcome must carry the free offer, the
choices made, the agreement copy and the booking link; Lou's must carry the
CV link and the KORE choice.

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
  if ($fn === 'clean') { $out[] = msh_cp_clean($a[0], $a[1], $a[2], $a[3]); }
  elseif ($fn === 'welcome') { $out[] = msh_cp_welcome_email($a[0], $a[1], $a[2]); }
  elseif ($fn === 'lou') { $out[] = msh_cp_lou_email($a[0], $a[1], $a[2]); }
  elseif ($fn === 'live') { $out[] = msh_cp_live(); }
  elseif ($fn === 'options') { $out[] = msh_cp_options(); }
  elseif ($fn === 'boxes') { $out[] = msh_cp_boxes(); }
  elseif ($fn === 'consts') { $out[] = array(MSH_CP_AGREEMENT_VERSION, MSH_CP_PRIVACY_VERSION, MSH_CP_SIGNED_OFF); }
}
echo json_encode($out);
"""

GOOD = {
    "first_name": "Jo", "last_name": "Bloggs", "email": "Jo@Example.com", "phone": "07700 900123",
    "region": "east-midlands", "postcode": "ln6 ", "icb": "Lincolnshire", "travel": "region",
    "relocate": "maybe", "licence": "full", "profession": "nurse", "pin": "12a3456e",
    "regstatus": "live", "band": "6", "current_role": "Theatre sister", "employer": "nhs",
    "years": "9", "specialities": ["theatres", "wound-care", "made-up"], "roles": ["clinical-specialist"],
    "availability": "3-months", "box1": "1", "agreement_version": "v1", "privacy_version": "p1",
    "linkedin": "https://www.linkedin.com/in/jo", "source": "ANTT!",
}
NOW = "2026-10-31T12:00:00Z"

def agreement_dir():
    """02-Elevate-and-Thrive/Clinical-Recruitment/Agreement, found from the repo or any worktree of it."""
    d = HERE
    while d != os.path.dirname(d):
        c = os.path.join(d, "Clinical-Recruitment", "Agreement")
        if os.path.isdir(c):
            return c
        d = os.path.dirname(d)
    return ""


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
        (c,) = self.run_php([["clean", [GOOD, NOW, "v1", "p1"]]])
        self.assertEqual(c["errors"], [])
        r = c["record"]
        self.assertEqual(r["email"], "jo@example.com")
        self.assertEqual(r["postcode"], "LN6")
        self.assertEqual(r["pin"], "12A3456E")
        self.assertEqual(r["specialities"], ["theatres", "wound-care"])
        self.assertEqual(r["years"], 9)
        self.assertEqual(r["source"], "antt")
        self.assertEqual(r["agreement_version"], "v1")
        self.assertEqual(r["privacy_version"], "p1")
        self.assertEqual(r["agreement_accepted"], NOW)
        # Box 1 alone is enough; boxes 2 and 3 default to false (never share with KORE).
        self.assertIs(r["box1"], True)
        self.assertIs(r["box2"], False)
        self.assertIs(r["box3"], False)
        self.assertNotIn("gdpr_consent", r)

    def test_optional_boxes_stored(self):
        (c,) = self.run_php([["clean", [dict(GOOD, box2="1", box3="on"), NOW, "v1", "p1"]]])
        self.assertEqual(c["errors"], [])
        self.assertIs(c["record"]["box2"], True)
        self.assertIs(c["record"]["box3"], True)

    def test_box1_and_versions_required(self):
        bad = dict(GOOD, box1="", box2="1")
        (a, b, p) = self.run_php([["clean", [bad, NOW, "v1", "p1"]], ["clean", [GOOD, NOW, "v2", "p1"]],
                                  ["clean", [GOOD, NOW, "v1", "p2"]]])
        self.assertEqual(a["errors"], ["box1"])          # boxes 2 and 3 never block
        self.assertEqual(a["record"]["agreement_accepted"], "")
        self.assertIs(a["record"]["box1"], False)
        self.assertIn("box1", b["errors"])
        self.assertIn("box1", p["errors"])

    def test_wording_matches_agreement_files(self):
        """Every box is word for word from CSP-PA-v1.0, and the form stays shut until Lou says yes."""
        boxes, consts = self.run_php([["boxes", []], ["consts", []]])
        self.assertEqual(consts, ["CSP-PA-v1.0", "CSP-PN-v1.0", False])
        src = os.path.join(agreement_dir(), "01-programme-agreement-one-page.md")
        if not os.path.exists(src):
            self.skipTest("agreement file not on this machine")
        text = open(src).read()
        for k, (head, body) in boxes.items():
            self.assertIn(f"**{k[3]}. {head}** {body}", text, k)

    def test_no_fees_wording(self):
        """No fees clause at all (Lou, 31/10/2026): nothing about charges, repayment or price."""
        boxes, = self.run_php([["boxes", []]])
        (c,) = self.run_php([["clean", [GOOD, NOW, "CSP-PA-v1.0", "CSP-PN-v1.0"]]])
        (w,) = self.run_php([["welcome", [dict(c["record"], agreement_version="CSP-PA-v1.0", privacy_version="CSP-PN-v1.0"), "CLN-X", ""]]])
        for text in [w["html"]] + [b for pair in boxes.values() for b in pair]:
            for word in ("repay", "charged", "fee", "price", "pay back", "solicitor"):
                self.assertNotIn(word, text.lower(), word)

    def test_field_checks(self):
        bad = dict(GOOD, email="nope", phone="123", postcode="LN6 7TS", pin="", specialities=[], roles=["x"],
                   linkedin="https://evil.example", years="lots", region="mars")
        (c,) = self.run_php([["clean", [bad, NOW, "v1", "p1"]]])
        for k in ("email", "phone", "postcode", "pin", "specialities", "roles", "linkedin", "years", "region"):
            self.assertIn(k, c["errors"])
        pending = dict(GOOD, pin="", regstatus="pending")
        (p,) = self.run_php([["clean", [pending, NOW, "v1", "p1"]]])
        self.assertNotIn("pin", p["errors"])

    def test_emails(self):
        (c,) = self.run_php([["clean", [dict(GOOD, box2="1"), NOW, "CSP-PA-v1.0", "CSP-PN-v1.0"]]])
        r = dict(c["record"], agreement_version="CSP-PA-v1.0", privacy_version="CSP-PN-v1.0", first_name="Jo<b>")
        w, l, live = self.run_php([["welcome", [r, "CLN-ABC123", "https://book.example/x"]],
                                   ["lou", [r, "CLN-ABC123", "https://hub.example/cv?t=1"]], ["live", []]])
        self.assertIn("CLN-ABC123", w["subject"])
        self.assertIn("https://book.example/x", w["html"])
        self.assertIn("What you get, free", w["html"])    # agreement copy present
        self.assertIn("The Clinical Interview Playbook (full bundle, 12 months' access).", w["html"])
        self.assertIn("12 months of Medical Sales Hub access.", w["html"])
        self.assertIn("Your login details for both follow within 5 business days.", w["html"])
        self.assertIn("One-to-one support from me through the whole process", w["html"])
        self.assertIn("Kore Executive Limited for industry roles: yes", w["html"])
        self.assertIn("training and events: no", w["html"])
        self.assertIn("Industry Nurse Professional Standard&trade; course (launching December 2026)", w["html"])
        self.assertIn("CSP-PN-v1.0", w["html"])
        self.assertNotIn("Jo<b>", w["html"])               # escaped
        self.assertIn("https://hub.example/cv?t=1", l["html"])
        self.assertIn("Integrated Care Board (ICB) area", l["html"])
        self.assertIn("Share with KORE (box 2)", l["html"])
        self.assertFalse(live)                             # not signed off keeps the form shut

    def test_options_keys_slug_safe(self):
        (o,) = self.run_php([["options", []]])
        import re
        for lst, items in o.items():
            for k in items:
                self.assertRegex(k, r"^[a-z0-9-]+$", lst)


if __name__ == "__main__":
    unittest.main()
