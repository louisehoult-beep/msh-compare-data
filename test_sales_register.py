#!/usr/bin/env python3
"""Medical Sales Register: the WPCode snippet's rules and the page's filters.

hub/wpcode/sales-register.php cleans every profile a member saves, decides
what a Hub Employer sees (msh_sr_public), types live roles from their titles,
and builds the weekly MailerLite jobs email per region. The employer view must
never carry a name, email, phone, LinkedIn or current employer, and must drop
hidden, unconsented and year-old profiles. app/sales-register.js filters the
employer list and matches roles to a member in the browser.

Stdlib only; php and node are on ubuntu-latest and each is skipped, loudly,
where missing.

    python3 test_sales_register.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PHP_SNIPPET = os.path.join(HERE, "hub", "wpcode", "sales-register.php")
JS_PAGE = os.path.join(HERE, "app", "sales-register.js")

PHP_STUBS = r"""
function add_action() {}
"""
PHP_RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  $fn = $c[0]; $a = $c[1];
  if ($fn === 'clean') { $out[] = msh_sr_clean($a[0], $a[1], $a[2], $a[3]); }
  elseif ($fn === 'public') { $out[] = msh_sr_public($a[0], $a[1]); }
  elseif ($fn === 'contact') { $out[] = msh_sr_contact($a[0], $a[1], $a[2]); }
  elseif ($fn === 'options') { $out[] = msh_sr_options(); }
  elseif ($fn === 'cv') { $out[] = msh_sr_cv_suggest($a[0]); }
  elseif ($fn === 'summary') { $out[] = msh_sr_summary_email($a[0], $a[1], $a[2]); }
  elseif ($fn === 'links') { $out[] = msh_sr_career_links(); }
  elseif ($fn === 'kind') { $out[] = msh_sr_job_kind($a[0]); }
  elseif ($fn === 'feed') { $out[] = msh_sr_feed_roles($a[0]); }
  elseif ($fn === 'region') { $out[] = msh_sr_region_jobs($a[0], $a[1], $a[2]); }
  elseif ($fn === 'email') { $out[] = msh_sr_digest_email($a[0], $a[1], $a[2]); }
  elseif ($fn === 'plan') { $out[] = msh_sr_ml_plan($a[0], $a[1]); }
  elseif ($fn === 'groups') { $out[] = msh_sr_ml_groups(); }
  elseif ($fn === 'access') { $out[] = msh_sr_employer_access($a[0], $a[1], $a[2]); }
}
echo json_encode($out);
"""

TODAY = "2026-10-14"
GOOD = {
    "region": "yorkshire-humber", "area": "Leeds", "travel": "region", "relocate": False, "overnights": True,
    "level": "experienced", "yearsInSales": "6", "currentRole": "Territory Manager, Wound Care",
    "rolesDone": ["field-sales"], "roles": ["kam", "sales-manager"], "background": ["medical-sales"],
    "areas": ["wound-care"], "customers": ["ward-nurses", "procurement"], "skills": ["tenders", "evaluations"],
    "qualifications": ["degree"], "targetPct": "112", "achievement": "Grew territory 34% in 2025",
    "availability": "3-months", "notice": "1-month", "salary": "50-60", "driving": True, "rightToWork": True,
    "bio": "Six years in wound care.", "employer": "Acme Medical", "phone": "07700 900123",
    "linkedin": "https://www.linkedin.com/in/sam-sales", "visible": True, "consent": True,
}
PRIVATE = {"phone", "linkedin", "employer", "consentAt", "visible", "name", "email", "private",
           "shareContact", "shareAt", "jobsEmail"}


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

    def clean(self, body, old=None, ref="MSR-ABC234"):
        return self.call(("clean", [body, old or {}, TODAY, ref]))[0]

    def test_good_profile_saves(self):
        r = self.clean(GOOD)
        self.assertTrue(r["ok"], r)
        p = r["profile"]
        self.assertEqual(p["ref"], "MSR-ABC234")
        self.assertEqual(p["yearsInSales"], 6)
        self.assertEqual(p["targetPct"], 112)
        self.assertEqual(p["consentAt"], TODAY)
        self.assertEqual(p["roles"], ["kam", "sales-manager"])
        self.assertEqual(p["customers"], ["ward-nurses", "procurement"])

    def test_required_and_validated_fields(self):
        for field, bad in [("region", "mars"), ("level", ""), ("roles", []), ("roles", ["nonsense"]),
                           ("yearsInSales", "lots"), ("yearsInSales", 99), ("targetPct", "-5"), ("targetPct", 900),
                           ("linkedin", "https://evil.example/in/x"), ("phone", "call me")]:
            r = self.clean(dict(GOOD, **{field: bad}))
            self.assertEqual(r, {"ok": False, "why": field}, field)

    def test_optional_numbers_may_be_blank(self):
        p = self.clean(dict(GOOD, yearsInSales="", targetPct=""))["profile"]
        self.assertIsNone(p["yearsInSales"])
        self.assertIsNone(p["targetPct"])

    def test_visible_needs_consent(self):
        self.assertEqual(self.clean(dict(GOOD, consent=False)), {"ok": False, "why": "consent"})
        r = self.clean(dict(GOOD, consent=False, visible=False))
        self.assertTrue(r["ok"])
        self.assertEqual(r["profile"]["consentAt"], "")

    def test_booleans_are_strict(self):
        p = self.clean(dict(GOOD, driving="yes", relocate=1, jobsEmail="true"))["profile"]
        self.assertFalse(p["driving"])
        self.assertFalse(p["relocate"])
        self.assertFalse(p["jobsEmail"])

    def test_unknown_ticks_dropped_and_order_fixed(self):
        p = self.clean(dict(GOOD, skills=["evaluations", "made-up", "new-business", "new-business", 7]))["profile"]
        self.assertEqual(p["skills"], ["new-business", "evaluations"])

    def test_ref_and_consent_date_kept(self):
        old = dict(self.clean(GOOD)["profile"], consentAt="2026-01-01")
        p = self.clean(GOOD, old=old, ref="MSR-ZZZZZZ")["profile"]
        self.assertEqual(p["ref"], "MSR-ABC234")
        self.assertEqual(p["consentAt"], "2026-01-01")

    def test_contact_details_scrubbed_from_free_text(self):
        p = self.clean(dict(GOOD, bio="<b>Hi</b> email sam@acme.com or ring 07700 900123, see www.sam.co.uk",
                            achievement="Top rep, call 07700 900123", currentRole="TM sam@acme.com"))["profile"]
        for k in ("bio", "achievement", "currentRole"):
            self.assertNotIn("sam@acme.com", p[k])
            self.assertNotIn("900123", p[k])
        self.assertNotIn("sam.co.uk", p["bio"])
        self.assertNotIn("<b>", p["bio"])

    def test_employer_view_has_no_private_fields(self):
        p = self.clean(dict(GOOD, shareContact=True, jobsEmail=True))["profile"]
        pub = self.call(("public", [p, TODAY]))[0]
        self.assertEqual(PRIVATE & set(pub), set())
        blob = json.dumps(pub)
        for secret in ("Acme Medical", "900123", "linkedin.com"):
            self.assertNotIn(secret, blob)
        self.assertEqual(pub["level"], "experienced")

    def test_employer_view_drops_hidden_unconsented_and_stale(self):
        p = self.clean(GOOD)["profile"]
        got = self.call(
            ("public", [dict(p, visible=False), TODAY]),
            ("public", [dict(p, consentAt=""), TODAY]),
            ("public", [dict(p, updated="2025-10-13"), TODAY]),
            ("public", [dict(p, updated="2025-10-14"), TODAY]),
        )
        self.assertEqual(got[:3], [None, None, None])
        self.assertIsNotNone(got[3], "exactly a year old is still shown")

    def test_contact_shared_only_with_separate_consent(self):
        shared = self.clean(dict(GOOD, shareContact=True))["profile"]
        self.assertEqual(shared["shareAt"], TODAY)
        got = self.call(("contact", [shared, "Sam Sales", "sam@example.org"]),
                        ("contact", [self.clean(GOOD)["profile"], "Sam Sales", "sam@example.org"]),
                        ("contact", [self.clean(dict(GOOD, shareContact="yes"))["profile"], "Sam Sales", "sam@example.org"]))
        self.assertEqual(got[0], {"name": "Sam Sales", "email": "sam@example.org", "phone": "07700 900123",
                                  "linkedin": "https://www.linkedin.com/in/sam-sales", "employer": "Acme Medical"})
        self.assertEqual(got[1:], [None, None])
        again = self.clean(dict(GOOD, shareContact=True), old=dict(shared, shareAt="2026-01-01"))["profile"]
        self.assertEqual(again["shareAt"], "2026-01-01")
        self.assertEqual(self.clean(GOOD, old=shared)["profile"]["shareAt"], "")

    CV = """Sam Example
    12 High Street, Leeds, LS1 1AA

    Territory Manager, Advanced Wound Care, 2020 to present. 8 years in medical device sales.
    Sell NPWT and dressings to tissue viability nurse specialists, district nurses and procurement.
    Won three trust tenders on the NHS Supply Chain framework; ran product evaluations; wrote business cases.
    Presented at study days. Exceeded target: 118% in 2025. President's Club.

    Sales Executive, office supplies, 2017 to 2020. New business.
    Education: BSc (Hons) Sports Science. ABPI Representatives Examination.
    """

    def test_cv_suggest(self):
        got, empty = self.call(("cv", [self.CV]), ("cv", ["nothing useful here"]))
        for k, ids in {"rolesDone": ["field-sales"], "background": ["medical-sales", "pharma", "other-sales"],
                       "areas": ["wound-care"],
                       "customers": ["ward-nurses", "community", "procurement"],
                       "skills": ["new-business", "tenders", "business-case", "evaluations", "presenting", "nhs-structures"],
                       "qualifications": ["degree", "life-science", "abpi"]}.items():
            for i in ids:
                self.assertIn(i, got[k], k + " " + i)
        self.assertNotIn("roles", got, "the CV says what was done, not what is wanted")
        self.assertEqual(got["yearsInSales"], 8)
        self.assertEqual(got["region"], "yorkshire-humber")
        self.assertEqual(empty["rolesDone"], [])
        self.assertIsNone(empty["yearsInSales"])
        self.assertEqual(empty["region"], "")

    def test_job_kind(self):
        # Real titles from data/supplier-careers.json, 14/10/2026, plus a few common shapes.
        cases = [
            ("(Senior) Territory Manager Electrophysiology - South Coast", "field-sales", "senior"),
            ("Regional Sales Manager TAVI, Structural Heart - North", "sales-manager", "manager"),
            ("Key Account Manager Cardiometabolics Field based Central Region", "kam", "experienced"),
            ("Clinical Specialist - Interventional Technologies (Vascular Closure) - London based", "clinical-specialist", "experienced"),
            ("Business Development Manager - Essex & Suffolk", "business-development", "experienced"),
            ("Trade Marketing Manager", "marketing", "experienced"),
            ("Sales Operations Admin - Pricing & Contracts Lead", "inside-sales", "senior"),
            ("Head of Sales UK & Ireland", "national-manager", "senior-manager"),
            ("Commercial Director", "director", "director"),
            ("Graduate Sales Representative", "field-sales", "entry"),
            ("Clinical Educator, Wound Care", "clinical-educator", "experienced"),
            ("Product Manager - Orthopaedics", "product-manager", "experienced"),
            ("Market Access Manager", "market-access", "experienced"),
            ("HGV Class 2 Driver (days)", "other", ""),
            ("VP, Research & Development", "other", ""),
            ("Sales Spine Specialist - East Anglia", "field-sales", "experienced"),
            ("Clinical Development Specialist Electrophysiology London/South East UK", "clinical-specialist", "experienced"),
            ("Clinical Research Associate", "other", ""),
            ("Field Service Engineer / Jr. Field Service Engineer - East Midlands based", "service-engineer", "entry"),
        ]
        got = self.call(*[("kind", [t]) for t, _, _ in cases])
        for (t, ty, lv), g in zip(cases, got):
            self.assertEqual((g["type"], g["level"]), (ty, lv), t)

    FEED = {"suppliers": [
        {"name": "A", "roles": [
            {"title": "Territory Manager (Scotland)", "location": "", "uk": True, "url": "https://a/1", "commercial": True, "clinical": False},
            {"title": "Product Specialist", "location": "Remote", "uk": None, "url": "https://a/3", "commercial": False, "clinical": False},
            {"title": "Data Analyst (Scotland)", "location": "", "uk": True, "url": "https://a/4", "commercial": False, "clinical": False},
            {"title": "Sales Rep", "location": "Paris", "uk": False, "url": "https://a/5", "commercial": True, "clinical": False},
            {"title": "Account Manager (Scotland)", "location": "", "uk": True, "url": "https://a/6", "commercial": True, "clinical": False},
            {"title": "Clinical Specialist - South West", "location": "", "uk": True, "url": "https://a/2", "commercial": False, "clinical": True},
            {"title": "Bad", "location": "", "uk": True, "url": "javascript:x", "commercial": True, "clinical": False},
            {"title": "Territory Manager (Scotland)", "location": "", "uk": True, "url": "https://a/1", "commercial": True, "clinical": False},
        ]},
        {"name": "B", "refused": "no roles"},
    ]}

    def test_feed_and_region_jobs(self):
        roles, empty = self.call(("feed", [self.FEED]), ("feed", [None]))
        self.assertEqual([r["url"] for r in roles], ["https://a/1", "https://a/3", "https://a/6", "https://a/2"],
                         "uk false, non-sales unflagged roles, bad urls and duplicates dropped")
        self.assertEqual(roles[1]["type"], "product-specialist", "a sales-family title counts even unflagged")
        self.assertEqual(empty, [])
        got = self.call(("region", [roles, "scotland", ["https://a/6"]]))[0]
        self.assertEqual([j["url"] for j in got["local"]], ["https://a/1"])
        self.assertEqual([j["url"] for j in got["national"]], ["https://a/3"])

    def test_digest_email(self):
        links = {"careers": "https://h/careers/", "register": "https://h/reg/"}
        job = {"title": "<b>TM</b>", "company": "A & B", "location": "Leeds", "url": "https://a/1",
               "type": "field-sales", "level": "senior", "regions": ["yorkshire-humber"]}
        other = dict(job, title="Lab Tech", type="other", level="", url="https://a/9")
        got = self.call(
            ("email", ["Yorkshire and the Humber", {"local": [job, other], "national": []}, links]),
            ("email", ["London", {"local": [], "national": [job]}, links]),
            ("email", ["London", {"local": [], "national": []}, links]),
        )
        h = got[0]["html"]
        self.assertEqual(got[0]["subject"], "2 new medical sales roles in Yorkshire and the Humber this week")
        for want in ("{$name}", "{$unsubscribe}", "&lt;b&gt;TM&lt;/b&gt;", "A &amp; B",
                     "Territory manager or sales representative", "Senior or specialist",
                     "Other commercial and clinical roles", "https://h/careers/", "https://h/reg/"):
            self.assertIn(want, h)
        self.assertLess(h.index("Territory manager or sales"), h.index("Other commercial"), "grouped in option order")
        self.assertEqual(got[1]["subject"], "New UK-wide medical sales roles this week")
        self.assertIsNone(got[2], "nothing new, no campaign")

    def test_mailerlite_plan(self):
        groups = self.call(("groups", []))[0]
        self.assertEqual(len(groups), 12)
        for g in groups.values():
            self.assertRegex(g, r"^\d{15,20}$")
        self.assertEqual(len(set(groups.values())), 12)
        p = self.clean(dict(GOOD, jobsEmail=True))["profile"]
        on, off, gone = self.call(("plan", [p, groups]), ("plan", [dict(p, jobsEmail=False), groups]), ("plan", [None, groups]))
        self.assertEqual(on["join"], [groups["yorkshire-humber"]])
        self.assertEqual(len(on["leave"]), 11)
        self.assertNotIn(groups["yorkshire-humber"], on["leave"])
        self.assertEqual(off["join"], [])
        self.assertEqual(len(off["leave"]), 12)
        self.assertEqual(gone, off)

    def test_regions_match_options(self):
        opts, groups = self.call(("options", []), ("groups", []))
        self.assertEqual(sorted(opts["regions"]), sorted(groups))

    def test_summary_email(self):
        p = self.clean(dict(GOOD, shareContact=True, jobsEmail=True))["profile"]
        m = self.call(("summary", ["Sam", p, "https://hub.example"]))[0]
        self.assertEqual(m["subject"], "Your Medical Sales Register profile is saved (MSR-ABC234)")
        h = m["html"]
        for want in ("Hi Sam,", "Yorkshire and the Humber, Leeds", "Key account manager", "112%",
                     "Overnight stays fine", "https://hub.example/medical-sales-hub/careers/", "https://hub.example/medical-sales-register/"):
            self.assertIn(want, h)
        self.assertNotIn("900123", h)

    def test_career_links(self):
        for l in self.call(("links", []))[0]:
            self.assertRegex(l["url"], r"^/[A-Za-z0-9/_.-]+$")

    def test_employer_access(self):
        got = self.call(("access", [True, False, ""]), ("access", [False, True, ""]), ("access", [False, False, "1"]),
                        ("access", [False, False, ""]), ("access", [False, False, None]))
        self.assertEqual(got, [True, True, True, False, False])

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
            self.skipTest("node not installed; app/sales-register.js not exercised")
        return run([node, "-e", script, JS_PAGE] + list(args))

    def test_filters(self):
        people = [
            {"ref": "MSR-A", "region": "london", "level": "experienced", "roles": ["kam"], "rolesDone": ["field-sales"],
             "areas": ["wound-care"], "customers": ["procurement"], "skills": ["tenders"], "availability": "now", "yearsInSales": 3, "bio": "dressings"},
            {"ref": "MSR-B", "region": "london", "level": "manager", "roles": ["national-manager"], "rolesDone": ["kam"],
             "areas": ["orthopaedics"], "customers": ["surgeons"], "skills": [], "availability": "6-months", "yearsInSales": 12, "bio": ""},
            {"ref": "MSR-C", "region": "wales", "level": "entry", "roles": ["field-sales"], "rolesDone": [],
             "areas": [], "customers": [], "skills": [], "availability": "exploring", "yearsInSales": 0, "bio": ""},
        ]
        opts = {"areas": {"wound-care": "Wound care", "orthopaedics": "Orthopaedics and spine"}}
        filters = [
            {"region": "london"}, {"level": "manager"}, {"role": "kam"}, {"role": "field-sales"}, {"area": "orthopaedics"},
            {"customer": "procurement"}, {"skill": "tenders"}, {"availability": "3-months"}, {"minYears": "10"},
            {"text": "ORTHOPAEDICS"}, {"text": "dressings"}, {},
        ]
        script = r"""
const P = require(process.argv[1])._pure;
const [people, opts, fs] = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(fs.map(f => P.filter(people, f, opts).map(p => p.ref))));
"""
        got = self.node(script, json.dumps([people, opts, filters]))
        self.assertEqual(got, [["MSR-A", "MSR-B"], ["MSR-B"], ["MSR-A", "MSR-B"], ["MSR-A", "MSR-C"], ["MSR-B"],
                               ["MSR-A"], ["MSR-A"], ["MSR-A"], ["MSR-B"], ["MSR-B"], ["MSR-A"], ["MSR-A", "MSR-B", "MSR-C"]])

    def test_roles_for_member(self):
        roles = [
            {"title": "KAM North", "url": "u1", "regions": ["yorkshire-humber", "north-east"], "type": "kam", "level": "experienced"},
            {"title": "KAM UK", "url": "u2", "regions": [], "type": "kam", "level": "senior"},
            {"title": "KAM London", "url": "u3", "regions": ["london"], "type": "kam", "level": "experienced"},
            {"title": "RSM Leeds", "url": "u4", "regions": ["yorkshire-humber"], "type": "sales-manager", "level": "manager"},
            {"title": "Lab Tech", "url": "u5", "regions": [], "type": "other", "level": ""},
        ]
        me = {"region": "yorkshire-humber", "level": "experienced", "roles": ["kam", "sales-manager"], "travel": "region"}
        script = r"""
const P = require(process.argv[1])._pure;
const [roles, me] = JSON.parse(process.argv[2]);
const a = P.rolesFor(roles, me).map(m => [m.role.url, m.local, m.levelMatch]);
const b = P.rolesFor(roles, Object.assign({}, me, {travel: 'national'})).map(m => m.role.url);
process.stdout.write(JSON.stringify([a, b, P.rolesFor(roles, null)]));
"""
        a, b, none = self.node(script, json.dumps([roles, me]))
        self.assertEqual(a, [["u1", True, True], ["u4", True, False], ["u2", False, False]])
        self.assertEqual(sorted(b), ["u1", "u2", "u3", "u4"], "UK-wide travel opens every region")
        self.assertEqual(none, [])

    def test_cv_merge_adds_never_removes(self):
        script = r"""
const P = require(process.argv[1])._pure;
const cur = { areas: ['renal'], skills: [], yearsInSales: '3', region: '' };
const s = { areas: ['renal', 'wound-care'], skills: ['tenders'], rolesDone: ['kam'], yearsInSales: 8, region: 'london' };
const m = P.mergeSuggest(cur, s);
process.stdout.write(JSON.stringify([m.profile.areas, m.profile.skills, m.profile.rolesDone, m.profile.yearsInSales,
  m.profile.region, m.added.areas, m.count, P.mergeSuggest({}, null).count]));
"""
        self.assertEqual(self.node(script), [["renal", "wound-care"], ["tenders"], ["kam"], "3", "london", ["wound-care"], 4, 0])

    def test_days_left_and_escaping(self):
        script = r"""
const P = require(process.argv[1])._pure;
process.stdout.write(JSON.stringify([P.daysLeft('2025-10-14', '2026-10-14', 365), P.esc('<img src=x onerror="a">&\'')]));
"""
        self.assertEqual(self.node(script), [0, "&lt;img src=x onerror=&quot;a&quot;&gt;&amp;&#39;"])


if __name__ == "__main__":
    unittest.main()
