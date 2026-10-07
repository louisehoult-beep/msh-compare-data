#!/usr/bin/env python3
"""Invariants for hub/my-hub-catalogue.json, read by app/my-hub.js.

A member's saved My Hub is a list of catalogue ids, so the catalogue has to
stay consistent: ids unique and never reused for a different page, every item
in a declared group, every role starter pointing at a real item, and the
"+ news" flag set exactly where a speciality news file exists (a flag with no
file is a promise of news that never arrives; a file with no flag is news the
member never sees).

    python3 test_my_hub_catalogue.py
"""
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(HERE, "hub", "my-hub-catalogue.json")
NEWS = os.path.join(HERE, "data", "speciality-news")
JS = os.path.join(HERE, "app", "my-hub.js")

ICONS_JS = os.path.join(HERE, "app", "hub-icons.js")
ROLES = ["company", "rep", "clinical", "procurement", "recruit"]

# The Clinical Evidence Library's band ids (page 3791 opens on `#<band-id>`),
# read from the live page's `.stab[data-band]` tabs on 30/09/2026
# (Hub/Wound-Care-Updates-2026-09-30/page-3791-live-20260930-150720.html).
# If 3791 gains or renames a band, re-read the live page and update this list
# and scripts/_my_hub_icons_bands_1001.py together.
LIBRARY_BANDS = {
    "wound-care", "oncology-sact", "renal", "diabetes-endocrinology", "respiratory",
    "interventional-radiology", "plastics-burns-reconstruction", "obesity-weight-management",
    "paediatrics", "dermatology", "palliative-eol", "mental-health", "emergency-urgent-care",
    "frailty-older-people", "sepsis-deteriorating-patient", "digital-medical-it", "primary-care",
    "audiology-hearing", "pharmacy-medicines", "radiology-imaging", "infection-prevention-control",
    "patient-handling", "vascular-access-iv", "nutrition-dietetics", "continence-bladder-bowel",
    "rehab-prosthetics-orthotics", "pain-management", "haematology-pbm", "maternity-neonatal",
    "gynaecology-womens-health", "ent-head-neck", "ophthalmology", "colorectal-gi-endoscopy",
    "pathology-lab-medicine", "critical-care", "urology", "vascular-surgery-pad",
    "cardiology-cardiac-surgery", "neurology-neurosurgery", "orthopaedics-trauma", "stroke",
}


def glyph_names():
    with open(ICONS_JS, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"/\*GLYPHS\*/(.*?)/\*END-GLYPHS\*/", src, re.S)
    if not m:
        raise AssertionError("app/hub-icons.js has lost its GLYPHS markers")
    return set(json.loads(m.group(1)))


class MyHubIconsBandsProfiles(unittest.TestCase):
    """Phase 1 of the home screen (01/10/2026): icons, library bands, profiles."""

    @classmethod
    def setUpClass(cls):
        with open(CAT, encoding="utf-8") as f:
            cls.cat = json.load(f)
        cls.items = cls.cat["items"]
        cls.byid = {i["id"]: i for i in cls.items}
        cls.glyphs = glyph_names()

    def test_every_page_has_its_own_icon(self):
        used = {}
        for i in self.items:
            if i["group"] == "specialities":
                self.assertNotIn("icon", i, "%s: specialities share the speciality icon" % i["id"])
                continue
            self.assertIn("icon", i, "%s has no icon" % i["id"])
            self.assertIn(i["icon"], self.glyphs, "%s names a glyph app/hub-icons.js lacks" % i["id"])
            self.assertNotIn(i["icon"], used, "%s and %s share an icon" % (i["id"], used.get(i["icon"])))
            used[i["icon"]] = i["id"]
        self.assertIn("steth", self.glyphs)

    def test_every_speciality_maps_to_a_library_band_or_null(self):
        seen = {}
        for i in self.items:
            if i["group"] != "specialities":
                self.assertNotIn("libraryBand", i, i["id"])
                continue
            self.assertIn("libraryBand", i, "%s: say null rather than leave it out" % i["id"])
            b = i["libraryBand"]
            if b is None:
                continue
            self.assertIn(b, LIBRARY_BANDS, "%s points at %s, not a band on page 3791" % (i["id"], b))
            self.assertNotIn(b, seen, "%s and %s open the same band" % (i["id"], seen.get(b)))
            seen[b] = i["id"]

    def test_profiles_are_labelled_from_the_live_nav(self):
        self.assertEqual(list(self.cat["profiles"].keys()), ROLES)
        frm = self.cat.get("_profilesFrom") or {}
        self.assertTrue(frm.get("sha256"), "run scripts/build_my_hub_profiles.py --nav <saved Hub page>")
        for r in ROLES:
            self.assertGreater(frm["navPages"][r], 0, r)
        for i in self.items:
            self.assertIn("profiles", i, i["id"])
            self.assertEqual(i["profiles"], [r for r in ROLES if r in i["profiles"]], "%s: unknown or unordered profile" % i["id"])
        for r in ROLES:
            n = sum(1 for i in self.items if r in i["profiles"])
            self.assertGreaterEqual(n, 10, "only %d catalogue pages carry %s: is the nav file right?" % (n, r))

    def test_profile_starters_are_pages_in_that_profiles_nav(self):
        st = self.cat["profileStarters"]
        self.assertEqual(sorted(st), sorted(ROLES))
        for r, ids in st.items():
            self.assertTrue(ids, r)
            for pid in ids:
                self.assertIn(pid, self.byid, "%s starter %s is not in the catalogue" % (r, pid))
                self.assertIn(r, self.byid[pid]["profiles"], "%s starter %s is not in the %s nav" % (r, pid, r))


EXTRA_TOOL_PAGES = {"/critecocare-tool-example/"}
TOOLS_12B = {
    "tool-supplier-search": ("Supplier Search", "/medical-sales-hub/med-sales-tools/#view-compare"),
    "tool-compare-product": ("Compare Your Product", "/medical-sales-hub/med-sales-tools/#view-compare"),
    "tool-help-me-prepare": ("Help Me Prepare", "/medical-sales-hub/med-sales-tools/#view-prep"),
    "tool-stakeholder-mapper": ("Stakeholder Mapper", "/medical-sales-hub/med-sales-tools/#view-mapper"),
    "tool-value-case-calculator": ("Value Case Calculator", "/medical-sales-hub/med-sales-tools/#view-value"),
    "tool-wound-savings-calculator": ("Wound Care Savings Calculator", "/medical-sales-hub/med-sales-tools/#view-value"),
    "tool-carbon-calculator": ("Sustainability (Carbon) Calculator", "/medical-sales-hub/med-sales-tools/#view-value"),
    "tool-sustainability-comparison": ("Sustainability Comparison Tool", "/critecocare-tool-example/"),
}
SPECIALITY_TAGGED = {
    "tool-wound-savings-calculator": ["tissue-viability-and-wound-care"],
    "intelligence-feed": ["theatres-and-surgical"],
    "fall-prevention-medical-sales-market-insights": ["frailty-and-older-people"],
    "pharmaceutical-sales": ["pharmacy-and-medicines"],
}


class MyHubCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CAT, encoding="utf-8") as f:
            cls.cat = json.load(f)
        cls.items = cls.cat["items"]
        cls.ids = [i["id"] for i in cls.items]

    def test_ids_unique_and_storable(self):
        self.assertEqual(len(self.ids), len(set(self.ids)), "duplicate catalogue id")
        # The account store runs ids through WordPress sanitize_key().
        for i in self.ids:
            self.assertRegex(i, r"^[a-z0-9_-]{1,80}$", i)

    def test_urls_are_hub_member_pages(self):
        # Page items own their URL. Tool views (Task 12b) share their page's URL
        # with a #view-... hash, so only hash-free URLs must be unique.
        urls = [i["url"] for i in self.items if "#" not in i["url"]]
        self.assertEqual(len(urls), len(set(urls)), "two items open the same page")
        for i in self.items:
            base, _, frag = i["url"].partition("#")
            self.assertTrue(re.match(r"^/medical-sales-hub/([a-z0-9-]+/)*$", base) or base in EXTRA_TOOL_PAGES, i["url"])
            if "#" in i["url"]:
                self.assertEqual(i["group"], "tools", i["id"])
                self.assertRegex(frag, r"^view-[a-z]+$", i["id"])
                self.assertIn(base, urls, "%s: the hash belongs to a page that is in the catalogue" % i["id"])
            self.assertTrue(i["label"].strip(), i["id"])

    def test_every_tool_is_listed_individually(self):
        byid = {i["id"]: i for i in self.items}
        self.assertIn("med-sales-tools", byid, "the Med Sales Tools page itself stays")
        for id_, (label, url) in TOOLS_12B.items():
            self.assertIn(id_, byid)
            self.assertEqual((byid[id_]["label"], byid[id_]["url"], byid[id_]["group"]), (label, url, "tools"), id_)
            self.assertNotIn("critec", (byid[id_]["label"] + id_).lower(), "no third-party name in a label")
            self.assertIn("profiles", byid[id_], id_)
        # a tool view takes the profiles of its page
        for id_, (_, url) in TOOLS_12B.items():
            page = [i for i in self.items if i["url"] == url.split("#")[0]]
            if page:
                self.assertEqual(byid[id_]["profiles"], page[0]["profiles"], id_)

    def test_hash_urls_pass_safe_url(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        urls = [i["url"] for i in self.items]
        r = subprocess.run([node, "-e", "const L=require('./app/my-hub-logic.js');"
                            "console.log(JSON.stringify(JSON.parse(process.argv[1]).map(u=>L.safeUrl(u))))", json.dumps(urls)],
                           cwd=HERE, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), urls, "safeUrl must pass every catalogue URL unchanged")

    def test_speciality_tags_are_real_and_only_on_the_four(self):
        spec_ids = {i["id"] for i in self.items if i["group"] == "specialities"}
        tagged = {i["id"]: i["specialities"] for i in self.items if "specialities" in i}
        self.assertEqual(tagged, SPECIALITY_TAGGED)
        for id_, sp in tagged.items():
            for s in sp:
                self.assertIn(s, spec_ids, "%s is tagged with %s, not a speciality item" % (id_, s))

    def test_retired_pages_are_gone(self):
        for gone in ("icb-diabetes-tech-tracker", "frameworks"):
            self.assertNotIn(gone, self.ids)
            for r, ids in self.cat["profileStarters"].items():
                self.assertNotIn(gone, ids, r)
            for k, role in self.cat["roles"].items():
                self.assertNotIn(gone, role["pins"], k)

    def test_groups_declared(self):
        groups = {g["id"] for g in self.cat["groups"]}
        for i in self.items:
            self.assertIn(i["group"], groups, i["id"])
        used = {i["group"] for i in self.items}
        self.assertEqual(groups, used, "a group with no items shows as an empty heading")

    def test_role_starters_resolve(self):
        ids = set(self.ids)
        for k, r in self.cat["roles"].items():
            self.assertTrue(r["pins"], k)
            for p in r["pins"]:
                self.assertIn(p, ids, "role %s names %s, not in the catalogue" % (k, p))

    def test_news_flag_matches_files(self):
        files = {f[:-5] for f in os.listdir(NEWS) if f.endswith(".json")}
        flagged = {i["id"] for i in self.items if i.get("news")}
        spec_ids = {i["id"] for i in self.items if i["group"] == "specialities"}
        self.assertEqual(flagged, files & spec_ids)
        self.assertEqual(files - spec_ids, set(), "a news file whose speciality cannot be pinned")

    def test_js_reads_this_catalogue(self):
        with open(JS, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("hub/my-hub-catalogue.json", src)
        # Never write a member's page with raw catalogue or feed text.
        self.assertIn("function esc(", src)
        # Since 2026-10 the feeds live in their own module, loaded by my-hub.js.
        with open(os.path.join(HERE, "app", "my-hub-feeds.js"), encoding="utf-8") as f:
            self.assertIn("data/speciality-news/", f.read())


if __name__ == "__main__":
    unittest.main(verbosity=1)
