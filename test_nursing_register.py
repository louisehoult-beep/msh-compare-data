#!/usr/bin/env python3
"""Nursing Register: the WPCode snippet's rules and the page's filters.

hub/wpcode/nursing-register.php cleans every profile a nurse saves and decides
what an employer sees (msh_nr_public). The employer view must never carry a
name, email, phone, NMC PIN or LinkedIn, must drop hidden, unconsented and
year-old profiles, and contact details typed into free text are scrubbed.
app/nursing-register.js filters the employer list in the browser.

Stdlib only; php and node are on ubuntu-latest and each is skipped, loudly,
where missing.

    python3 test_nursing_register.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PHP_SNIPPET = os.path.join(HERE, "hub", "wpcode", "nursing-register.php")
JS_PAGE = os.path.join(HERE, "app", "nursing-register.js")

PHP_STUBS = r"""
function add_action() {}
"""
PHP_RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  $fn = $c[0]; $a = $c[1];
  if ($fn === 'clean') { $out[] = msh_nr_clean($a[0], $a[1], $a[2], $a[3]); }
  elseif ($fn === 'public') { $out[] = msh_nr_public($a[0], $a[1]); }
  elseif ($fn === 'scrub') { $out[] = msh_nr_scrub($a[0]); }
  elseif ($fn === 'options') { $out[] = msh_nr_options(); }
  elseif ($fn === 'regions') { $out[] = msh_nr_job_regions($a[0], $a[1]); }
  elseif ($fn === 'digest') { $out[] = msh_nr_digest_jobs($a[0], $a[1], $a[2]); }
  elseif ($fn === 'email') { $out[] = msh_nr_digest_email($a[0], $a[1], $a[2], $a[3]); }
}
echo json_encode($out);
"""

TODAY = "2026-10-08"
GOOD = {
    "region": "yorkshire-humber", "area": "Leeds", "travel": "region", "relocate": False,
    "registration": ["adult"], "qualYear": 2012, "band": "7", "currentRole": "Tissue Viability Nurse Specialist",
    "sectors": ["nhs-acute"], "specialities": ["tissue-viability", "community"],
    "clinicalSkills": ["npwt", "compression"], "qualifications": ["nmp"], "transferable": ["teaching", "procurement"],
    "roles": ["clinical-specialist"], "availability": "3-months", "driving": True, "rightToWork": True,
    "training": False, "bio": "Ten years in wound care.", "nmcPin": "12a3456e", "phone": "07700 900123",
    "linkedin": "https://www.linkedin.com/in/jane-nurse", "visible": True, "consent": True,
}
PRIVATE = {"nmcPin", "phone", "linkedin", "consentAt", "visible", "name", "email", "private"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr or r.stdout)
    return json.loads(r.stdout)


class Snippet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.php = shutil.which("php")
        if not cls.php:
            return
        with open(PHP_SNIPPET, encoding="utf-8") as f:
            body = f.read()
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False, encoding="utf-8") as t:
            t.write("<?php\n" + PHP_STUBS + "\n" + body + "\n" + PHP_RUN)
            cls.tmp = t.name

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "tmp", None):
            os.unlink(cls.tmp)

    def call(self, *cases):
        if not self.php:
            self.skipTest("php not installed; the WPCode snippet's rules not exercised")
        return run([self.php, self.tmp, json.dumps([list(c) for c in cases])])

    def clean(self, body, old=None, ref="NR-ABC234"):
        return self.call(("clean", [body, old or {}, TODAY, ref]))[0]

    def test_good_profile_saves(self):
        r = self.clean(GOOD)
        self.assertTrue(r["ok"], r)
        p = r["profile"]
        self.assertEqual(p["ref"], "NR-ABC234")
        self.assertEqual(p["nmcPin"], "12A3456E")
        self.assertEqual(p["consentAt"], TODAY)
        self.assertEqual(p["updated"], TODAY)
        self.assertEqual(p["specialities"], ["tissue-viability", "community"])

    def test_required_fields(self):
        for field, bad in [("region", "mars"), ("registration", []), ("qualYear", 1950),
                           ("qualYear", 2027), ("specialities", ["nonsense"])]:
            r = self.clean(dict(GOOD, **{field: bad}))
            self.assertEqual(r, {"ok": False, "why": field}, field)

    def test_visible_needs_consent(self):
        self.assertEqual(self.clean(dict(GOOD, consent=False)), {"ok": False, "why": "consent"})
        r = self.clean(dict(GOOD, consent=False, visible=False))
        self.assertTrue(r["ok"])
        self.assertEqual(r["profile"]["consentAt"], "")

    def test_booleans_are_strict(self):
        p = self.clean(dict(GOOD, driving="yes", relocate=1))["profile"]
        self.assertFalse(p["driving"])
        self.assertFalse(p["relocate"])
        self.assertEqual(self.clean(dict(GOOD, visible="true")), {"ok": True, "profile": self.clean(dict(GOOD, visible=False))["profile"]})

    def test_private_fields_validated(self):
        self.assertEqual(self.clean(dict(GOOD, nmcPin="123456"))["why"], "nmcPin")
        self.assertEqual(self.clean(dict(GOOD, linkedin="https://evil.example/in/x"))["why"], "linkedin")
        self.assertEqual(self.clean(dict(GOOD, phone="call me"))["why"], "phone")

    def test_unknown_ticks_dropped_and_order_fixed(self):
        p = self.clean(dict(GOOD, clinicalSkills=["compression", "made-up", "npwt", "npwt", 7]))["profile"]
        self.assertEqual(p["clinicalSkills"], ["npwt", "compression"])

    def test_ref_and_consent_date_kept(self):
        old = self.clean(GOOD)["profile"]
        old["consentAt"] = "2026-01-01"
        old["nmcChecked"] = "2026-02-02"
        p = self.clean(GOOD, old=old, ref="NR-ZZZZZZ")["profile"]
        self.assertEqual(p["ref"], "NR-ABC234")
        self.assertEqual(p["consentAt"], "2026-01-01")
        self.assertEqual(p["nmcChecked"], "2026-02-02")

    def test_changed_pin_clears_nmc_check(self):
        old = dict(self.clean(GOOD)["profile"], nmcChecked="2026-02-02")
        p = self.clean(dict(GOOD, nmcPin="99Z9999Z"), old=old)["profile"]
        self.assertEqual(p["nmcChecked"], "")

    def test_contact_details_scrubbed_from_free_text(self):
        p = self.clean(dict(GOOD, bio="<b>Hi</b> email jane@nhs.net or ring 07700 900123, see www.jane.co.uk",
                            currentRole="Nurse jane@nhs.net"))["profile"]
        self.assertNotIn("jane@nhs.net", p["bio"])
        self.assertNotIn("07700", p["bio"])
        self.assertNotIn("jane.co.uk", p["bio"])
        self.assertNotIn("<b>", p["bio"])
        self.assertNotIn("@", p["currentRole"])

    def test_employer_view_has_no_private_fields(self):
        p = self.clean(GOOD)["profile"]
        pub = self.call(("public", [p, TODAY]))[0]
        self.assertEqual(PRIVATE & set(pub), set())
        self.assertEqual(pub["yearsQualified"], 14)
        self.assertNotIn("12A3456E", json.dumps(pub))
        self.assertNotIn("900123", json.dumps(pub))

    def test_employer_view_drops_hidden_unconsented_and_stale(self):
        p = self.clean(GOOD)["profile"]
        got = self.call(
            ("public", [dict(p, visible=False), TODAY]),
            ("public", [dict(p, consentAt=""), TODAY]),
            ("public", [dict(p, updated="2025-10-07"), TODAY]),
            ("public", [dict(p, updated="2025-10-08"), TODAY]),
        )
        self.assertEqual(got[:3], [None, None, None])
        self.assertIsNotNone(got[3], "exactly a year old is still shown")

    def test_jobs_email_is_strict_opt_in(self):
        self.assertTrue(self.clean(dict(GOOD, jobsEmail=True))["profile"]["jobsEmail"])
        self.assertFalse(self.clean(dict(GOOD, jobsEmail="yes"))["profile"]["jobsEmail"])
        self.assertFalse(self.clean(GOOD)["profile"]["jobsEmail"])

    def test_job_regions(self):
        # Real titles and locations from data/supplier-careers.json, 08/10/2026.
        cases = [
            ("Territory Manager Endovascular (Scotland)", "3 Locations", ["scotland"]),
            ("Territory Manager Endovascular (London & South East)", "2 Locations", ["south-east", "london"]),
            ("Territory Manager Radiofrequency Ablation (RF) - South West", "4 Locations", ["south-west"]),
            ("Business Development Manager Rapid Diagnostics - North West", "6 Locations", ["north-west"]),
            ("Clinical Specialist NMD - North", "4 Locations", ["north-east", "north-west", "yorkshire-humber"]),
            ("Key Account Manager Cardiometabolics Field based Central Region", "United Kingdom - Maidenhead", ["south-east"]),
            ("Territory Manager, Structural Heart; Field Based Midlands", "United Kingdom > Solihull : Remote", ["west-midlands"]),
            ("Business Development Manager - Essex & Suffolk", "Remote - England", ["east-of-england"]),
            ("Clinical Solution Specialist- Medical Physicist", "Crawley", ["south-east"]),
            ("Territory Manager TAVI, Structural Heart - Central UK", "7 Locations", ["east-midlands", "west-midlands"]),
            ("Product Specialist", "United Kingdom - Remote", []),
            ("Sales Rep", "Manchester", ["north-west"]),
        ]
        got = self.call(*[("regions", [t, l]) for t, l, _ in cases])
        for (t, l, want), g in zip(cases, got):
            self.assertEqual(sorted(g), sorted(want), t + " | " + l)

    def test_digest_picks_region_national_and_skips_sent(self):
        feed = {"suppliers": [
            {"name": "A", "roles": [
                {"title": "Territory Manager (Scotland)", "location": "", "uk": True, "url": "https://a/1", "commercial": True, "clinical": False},
                {"title": "Clinical Specialist - South West", "location": "", "uk": True, "url": "https://a/2", "commercial": False, "clinical": True},
                {"title": "Product Specialist", "location": "Remote", "uk": None, "url": "https://a/3", "commercial": True, "clinical": False},
                {"title": "Data Analyst (Scotland)", "location": "", "uk": True, "url": "https://a/4", "commercial": False, "clinical": False},
                {"title": "Sales Rep", "location": "Paris", "uk": False, "url": "https://a/5", "commercial": True, "clinical": False},
                {"title": "Account Manager (Scotland)", "location": "", "uk": True, "url": "https://a/6", "commercial": True, "clinical": False},
                {"title": "Bad", "location": "", "uk": True, "url": "javascript:x", "commercial": True, "clinical": False},
            ]},
            {"name": "B", "refused": "no roles"},
        ]}
        got = self.call(("digest", [feed, "scotland", ["https://a/6"]]), ("digest", [None, "scotland", []]))
        self.assertEqual([j["url"] for j in got[0]["local"]], ["https://a/1"])
        self.assertEqual([j["url"] for j in got[0]["national"]], ["https://a/3"])
        self.assertEqual(got[0]["local"][0]["company"], "A")
        self.assertEqual(got[1], {"local": [], "national": []})

    def test_digest_email(self):
        links = {"careers": "https://h/careers/", "register": "https://h/reg/", "unsub": "https://h/?msh_nr_unsub=5&t=abc"}
        job = {"title": "<b>TM</b>", "company": "A & B", "location": "Leeds", "url": "https://a/1"}
        got = self.call(
            ("email", ["Jane", "Yorkshire and the Humber", {"local": [job], "national": []}, links]),
            ("email", ["", "London", {"local": [], "national": [job, job]}, links]),
            ("email", ["Jane", "London", {"local": [], "national": []}, links]),
        )
        self.assertEqual(got[0]["subject"], "1 new role in Yorkshire and the Humber this week")
        self.assertIn("Hi Jane,", got[0]["html"])
        self.assertIn("&lt;b&gt;TM&lt;/b&gt;", got[0]["html"])
        self.assertIn("A &amp; B", got[0]["html"])
        self.assertIn("msh_nr_unsub=5&amp;t=abc", got[0]["html"])
        self.assertEqual(got[1]["subject"], "New UK-wide roles this week")
        self.assertIn("<p>Hi,</p>", got[1]["html"])
        self.assertIsNone(got[2], "nothing new, no email")

    def test_option_ids_are_slugs(self):
        opts = self.call(("options", []))[0]
        for k, d in opts.items():
            self.assertTrue(d, k)
            for i in d:
                self.assertRegex(i, r"^[a-z0-9]+(-[a-z0-9]+)*$", k)


class Page(unittest.TestCase):
    def node(self, script, *args):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed; app/nursing-register.js not exercised")
        return run([node, "-e", script, JS_PAGE] + list(args))

    def test_filters(self):
        people = [
            {"ref": "NR-A", "region": "london", "specialities": ["stoma"], "clinicalSkills": ["stoma-care"],
             "qualifications": [], "roles": ["clinical-specialist"], "availability": "now", "yearsQualified": 3, "bio": "ostomy"},
            {"ref": "NR-B", "region": "london", "specialities": ["renal"], "clinicalSkills": [],
             "qualifications": ["nmp"], "roles": ["territory-manager"], "availability": "6-months", "yearsQualified": 12, "bio": ""},
            {"ref": "NR-C", "region": "wales", "specialities": ["stoma"], "clinicalSkills": [],
             "qualifications": [], "roles": [], "availability": "exploring", "yearsQualified": 20, "bio": ""},
        ]
        opts = {"specialities": {"stoma": "Stoma care", "renal": "Renal and dialysis"}}
        filters = [
            {"region": "london"}, {"speciality": "stoma"}, {"skill": "nmp"}, {"skill": "stoma-care"},
            {"role": "territory-manager"}, {"availability": "3-months"}, {"minYears": "10"},
            {"text": "dialysis"}, {"text": "OSTOMY"}, {},
        ]
        script = r"""
const P = require(process.argv[1])._pure;
const [people, opts, fs] = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(fs.map(f => P.filter(people, f, opts).map(p => p.ref))));
"""
        got = self.node(script, json.dumps([people, opts, filters]))
        self.assertEqual(got, [["NR-A", "NR-B"], ["NR-A", "NR-C"], ["NR-B"], ["NR-A"], ["NR-B"], ["NR-A"],
                               ["NR-B", "NR-C"], ["NR-B"], ["NR-A"], ["NR-A", "NR-B", "NR-C"]])

    def test_days_left_and_escaping(self):
        script = r"""
const P = require(process.argv[1])._pure;
process.stdout.write(JSON.stringify([P.daysLeft('2025-10-08', '2026-10-08', 365), P.daysLeft('2026-10-01', '2026-10-08', 365),
  P.daysLeft('bad', '2026-10-08', 365), P.esc('<img src=x onerror="a">&\'')]));
"""
        self.assertEqual(self.node(script), [0, 358, None, "&lt;img src=x onerror=&quot;a&quot;&gt;&amp;&#39;"])


if __name__ == "__main__":
    unittest.main()
