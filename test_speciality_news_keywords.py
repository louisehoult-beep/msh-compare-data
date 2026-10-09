#!/usr/bin/env python3
"""Invariants for the keyword slice of build_speciality_news.py (29/09/2026).

Stdlib only, no network. The headline fixtures below are REAL headlines from
Pulse, Nursing in Practice, Practice Nursing and the British Journal of Nursing,
read 29/09/2026 and judged by hand: ROUTES are ones that belong on that page,
NEVER are ones the first draft of the rules got wrong (or plausibly would).
A rule change that breaks one of these is a precision change and needs a
decision, not a fixture edit to make CI green.

    python3 test_speciality_news_keywords.py
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_speciality_news as N  # noqa: E402

RULES = N.load_keyword_rules()


def slugs_for(title, summary=""):
    return {s for s, _t in N.keyword_matches({"title": title, "summary": summary}, RULES)}


class RulesFile(unittest.TestCase):

    def test_rules_file_loads(self):
        self.assertIsNotNone(RULES)
        self.assertTrue(RULES["rules"])

    def test_every_speciality_page_has_a_rule(self):
        pages = set()
        for d in ("speciality-panels", "speciality-news"):
            path = os.path.join(HERE, "data", d)
            pages |= {n[:-5] for n in os.listdir(path) if n.endswith(".json")}
        with open(N.RULES_PATH, encoding="utf-8") as fh:
            no_rule = json.load(fh).get("noRule", {})
        for slug, why in no_rule.items():
            self.assertNotIn(slug, RULES["rules"], "%s is in both rules and noRule" % slug)
            self.assertTrue(len(why) > 40, "%s: noRule needs a written reason" % slug)
        missing = sorted(pages - set(RULES["rules"]) - set(no_rule))
        self.assertEqual(missing, [], "speciality pages with no keyword rule: %s" % missing)

    def test_no_rule_for_a_page_that_does_not_exist(self):
        panels = {n[:-5] for n in os.listdir(os.path.join(HERE, "data", "speciality-panels"))
                  if n.endswith(".json")}
        extra = sorted(set(RULES["rules"]) - panels)
        self.assertEqual(extra, [], "rules for unknown slugs (typo?): %s" % extra)

    def test_every_rule_has_include_patterns(self):
        for slug, r in RULES["rules"].items():
            self.assertTrue(r["include"], "%s has no include patterns" % slug)

    def test_general_sources_exist(self):
        ids = {s["id"] for s in N.SOURCES}
        self.assertEqual(sorted(RULES["general"] - ids), [])

    def test_unreadable_rules_file_is_none_not_a_crash(self):
        self.assertIsNone(N.load_keyword_rules("/nonexistent/rules.json"))


class WholeWords(unittest.TestCase):

    def test_burnham_is_not_burns(self):
        self.assertNotIn("plastics-burns-and-reconstruction",
                         slugs_for("Burnham warns NHS 'will collapse' without social care reform"))

    def test_falls_as_a_verb_is_not_frailty(self):
        self.assertNotIn("frailty-and-older-people",
                         slugs_for("Dispensing GP fee envelope falls 17.5% in real terms, DDA says"))

    def test_stomach_is_not_stoma(self):
        self.assertNotIn("continence-bladder-and-bowel",
                         slugs_for("Stomach acid tablet shortage expected to last until January"))

    def test_ms_is_case_sensitive(self):
        self.assertIn("neurology-and-neurosurgery",
                      slugs_for("Drug to help people with MS walk more easily to be offered on NHS"))
        self.assertNotIn("neurology-and-neurosurgery", slugs_for("People with ms walk"))

    def test_heat_stroke_is_not_stroke(self):
        self.assertNotIn("stroke", slugs_for("Nurses warned of heat stroke risk in hot wards"))


class Deny(unittest.TestCase):
    """Category alone is not relevance (Sales Triggers Desk, 14/08/2026)."""

    CASES = [
        "Pulse virtual event to feature menopause and COPD",
        "General Practice Awards 2026 shortlist revealed",
        "Clinical quiz – managing asthma in the returning traveller",
        "Sponsored CPD: Diagnosis and management of primary biliary cholangitis in general practice",
        "Nurse struck off NMC register after saying dementia resident did not need birthday cake",
        "Mental health nurses appointed new chair and vice chair of RCN Congress",
        "‘If you were suicidal, could you trust NHS mental health services?’",
        "Can you diagnose this woman’s mildly itchy facial rash?",
        "Key questions on fibroids",
        "Top ten advice and guidance requests in ophthalmology",
        "Childhood respiratory care and B12 deficiency on agenda at Nursing in Practice event",
        "Anaphylaxis: myths and facts explained",
        "Nursing careers fair for mental health nurses",
        "Privacy notice for the dementia audit",
        "Interview: legal tips on aesthetic nursing in an era of viral trends and AI",
        "The rise of unsolicited A&G; and when should GPs offer PSA tests?",
        "Job Advert – Trust – Diabetes Specialist Nurse",
    ]

    def test_routine_publications_route_nowhere(self):
        for title in self.CASES:
            self.assertEqual(slugs_for(title), set(), title)

    def test_a_quote_inside_a_news_headline_is_not_a_column(self):
        self.assertIn("mental-health",
                      slugs_for("‘Alarming’ rise in children attending A&E in mental health crisis"))


class RealHeadlines(unittest.TestCase):

    ROUTES = [
        ("Patient safety alert issued to prevent avoidable harm from hoists", "patient-handling"),
        ("Nurses told to stop using wound care products lacking appropriate conformity markings",
         "tissue-viability-and-wound-care"),
        ("Filters should be used when administering parenteral nutrition, MHRA states", "nutrition-and-dietetics"),
        ("Patients with certain hip replacement to be invited for clinical review after risk identified",
         "orthopaedics-and-trauma"),
        ("Mounjaro maker’s Foundayo weight-loss pill given MHRA approval", "obesity-and-weight-management"),
        ("NICE backs endometriosis saliva test for use in primary care", "gynaecology-and-womens-health"),
        ("Skin cancer detection: a primary care essential", "dermatology"),
        ("Understanding acute otitis media in children", "ent-and-head-and-neck"),
        ("GPs face restrictions to routine blood tests amid pathology worker strikes",
         "pathology-and-laboratory-medicine"),
        ("Common antidepressant out of stock", "pharmacy-and-medicines"),
        ("Two asthma inhalers to be discontinued this winter", "respiratory"),
        ("Urine test could speed up bladder cancer diagnosis in patients with haematuria", "urology"),
        ("Sustainable PPE: is it possible to protect the patient and the planet?",
         "infection-prevention-and-control"),
        ("Evaluating medication waste attributable to lack of proper flushing of intravenous administration sets",
         "vascular-access-and-iv-therapy"),
        ("Women needing ‘ongoing district nurse care’ after cosmetic procedure complications",
         "plastics-burns-and-reconstruction"),
        ("GLP-1s and SGLT-2s may help slow kidney damage in diabetes, study shows", "renal"),
    ]

    NEVER = [
        ("Dementia care needs same ambition as cancer, argues report", "oncology-and-sact"),
        ("Maternal RSV vaccination halved number of babies in intensive care", "critical-care"),
        ("From infected blood scandal campaigner to GP minister: Who is Dame Diana Johnson?",
         "haematology-and-patient-blood-management"),
        ("Nurse makes history in Wales as first independent care home nurse prescriber",
         "frailty-and-older-people"),
        ("GPs should let parents access children’s records but keep this ‘under review’, says GMC",
         "paediatrics"),
        ("Plans for £7.75m ‘super GP surgery’ scrapped as homes proposed for site",
         "theatres-and-surgical"),
        ("Practices struggling to stay open due to ‘severe’ nursing shortages", "pharmacy-and-medicines"),
        ("Patients know best, until they read their blood tests", "pathology-and-laboratory-medicine"),
    ]

    def test_routes(self):
        for title, slug in self.ROUTES:
            self.assertIn(slug, slugs_for(title), title)

    def test_never(self):
        for title, slug in self.NEVER:
            self.assertNotIn(slug, slugs_for(title), title)

    def test_summary_can_exclude_but_never_include(self):
        self.assertEqual(slugs_for("Nurses asked for views on pay",
                                   "Includes dermatology, eczema and psoriasis clinics."), set())
        self.assertNotIn("critical-care",
                         slugs_for("Intensive care admissions fall", "Newborn admissions halved."))


def _item(title, days_ago=1, link=None, **kw):
    when = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    it = {"title": title, "link": link or "https://example.com/%s" % abs(hash(title)),
          "published": when.isoformat(), "summary": "", "source": "X"}
    it.update(kw)
    return it


class Combine(unittest.TestCase):
    # The page cap. Since 30/09/2026 the file keeps a rolling month (ITEMS_PER_SPECIALITY
    # is a 100 ceiling) and a speciality page renders 6, so the slot logic is tested at 6.
    CAP = 6

    def test_no_keyword_items_is_the_old_behaviour(self):
        primary = [_item("p%d" % i, days_ago=i) for i in range(8)]
        got = N.combine(primary, [], cap=self.CAP)
        self.assertEqual([i["title"] for i in got], ["p%d" % i for i in range(6)])

    def test_keyword_capped_at_slots_on_a_full_page(self):
        primary = [_item("p%d" % i, days_ago=i + 10) for i in range(8)]
        kw = [_item("k%d" % i, days_ago=i) for i in range(5)]
        got = N.combine(primary, kw, cap=self.CAP)
        self.assertEqual(len(got), self.CAP)
        self.assertEqual(sum(1 for i in got if i["title"].startswith("k")), N.KEYWORD_SLOTS)

    def test_keyword_fills_an_empty_page(self):
        kw = [_item("k%d" % i, days_ago=i) for i in range(9)]
        self.assertEqual(len(N.combine([], kw, cap=self.CAP)), self.CAP)

    def test_keyword_fills_what_primary_cannot(self):
        primary = [_item("p0", days_ago=30)]
        kw = [_item("k%d" % i, days_ago=i) for i in range(9)]
        got = N.combine(primary, kw, cap=self.CAP)
        self.assertEqual(len(got), 6)
        self.assertIn("p0", [i["title"] for i in got])

    def test_opportunity_never_cut(self):
        primary = [_item("opp%d" % i, days_ago=50, opportunity=True) for i in range(6)]
        kw = [_item("k%d" % i, days_ago=i) for i in range(3)]
        got = N.combine(primary, kw, cap=self.CAP)
        self.assertEqual(sum(1 for i in got if i.get("opportunity")), 6)

    def test_duplicate_of_a_tagged_item_is_dropped(self):
        primary = [_item("Same story", link="https://x.example/a/")]
        kw = [_item("Same story (copy)", link="https://x.example/a?utm=1")]
        self.assertEqual(len(N.combine(primary, kw, cap=self.CAP)), 1)


class Build(unittest.TestCase):
    """build() end to end with stubbed fetches and a stubbed rules file."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._saved = (N.OUT_DIR, N.SOURCES, N.fetch, N.fetch_pipeline_intel, N.RULES_PATH)
        N.OUT_DIR = os.path.join(self._tmp, "out")
        os.makedirs(N.OUT_DIR)
        N.RULES_PATH = os.path.join(self._tmp, "rules.json")
        with open(N.RULES_PATH, "w") as fh:
            json.dump({"generalSources": ["gen"], "denyTitle": ["events?"], "denyTitleWhole": [],
                       "rules": {"urology": {"include": ["prostate"]},
                                 "dermatology": {"include": ["eczema"]}}}, fh)
        now = datetime.datetime.now(datetime.timezone.utc)

        def rss(titles, host):
            items = "".join("<item><title>%s</title><link>https://%s/%d</link><pubDate>%s</pubDate></item>"
                            % (t, host, n, (now - datetime.timedelta(days=1)).strftime("%a, %d %b %Y %H:%M:%S GMT"))
                            for n, t in enumerate(titles))
            return ('<?xml version="1.0"?><rss version="2.0"><channel>%s</channel></rss>' % items).encode()

        feeds = {"https://gen.example": rss(["Prostate test news", "Eczema cream study",
                                             "Prostate awareness event", "GP contract talks"], "g.example"),
                 "https://uro.example": rss(["Urology journal item"], "u.example")}
        N.fetch = lambda url: feeds[url]
        N.SOURCES = [{"id": "gen", "name": "General", "url": "https://gen.example", "specialities": []},
                     {"id": "uro", "name": "Uro Journal", "url": "https://uro.example",
                      "specialities": ["urology"]}]
        N.fetch_pipeline_intel = lambda token=None: N.PipelineIntel()

    def tearDown(self):
        N.OUT_DIR, N.SOURCES, N.fetch, N.fetch_pipeline_intel, N.RULES_PATH = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _read(self, slug):
        with open(os.path.join(N.OUT_DIR, slug + ".json"), encoding="utf-8") as fh:
            return json.load(fh)["items"]

    def test_slice_routes_records_match_and_keeps_tagged(self):
        N.build(pause=0)
        uro = self._read("urology")
        titles = [i["title"] for i in uro]
        self.assertIn("Urology journal item", titles)
        self.assertIn("Prostate test news", titles)
        self.assertNotIn("Prostate awareness event", titles)          # deny list
        kw = [i for i in uro if i.get("match")]
        self.assertEqual(kw[0]["match"], {"slice": "keyword", "rule": "urology", "terms": ["Prostate"]})
        self.assertEqual([i["title"] for i in self._read("dermatology")], ["Eczema cream study"])

    def test_every_rule_slug_gets_a_file(self):
        N.build(pause=0)
        self.assertTrue(os.path.exists(os.path.join(N.OUT_DIR, "dermatology.json")))

    def test_only_run_skips_the_slice(self):
        N.build(only_id="uro", pause=0)
        self.assertEqual([i["title"] for i in self._read("urology")], ["Urology journal item"])
        self.assertFalse(os.path.exists(os.path.join(N.OUT_DIR, "dermatology.json")))

    def test_failed_pipeline_keeps_verified_rows_on_a_non_rss_page(self):
        with open(os.path.join(N.OUT_DIR, "dermatology.json"), "w") as fh:
            json.dump({"items": [
                {"title": "Verified row", "link": "https://v.example", "published": None, "verified": True},
                {"title": "Old keyword row", "link": "https://o.example", "published": None,
                 "match": {"slice": "keyword", "rule": "dermatology", "terms": ["x"]}}]}, fh)
        N.fetch_pipeline_intel = lambda token=None: {}
        N.build(pause=0)
        titles = [i["title"] for i in self._read("dermatology")]
        self.assertIn("Verified row", titles)
        self.assertIn("Eczema cream study", titles)
        self.assertNotIn("Old keyword row", titles)   # re-derived each run, never carried

    def test_successful_pipeline_read_is_authoritative(self):
        with open(os.path.join(N.OUT_DIR, "dermatology.json"), "w") as fh:
            json.dump({"items": [{"title": "Dropped row", "link": "https://d.example"}]}, fh)
        N.build(pause=0)
        self.assertEqual([i["title"] for i in self._read("dermatology")], ["Eczema cream study"])


class Paging(unittest.TestCase):

    def setUp(self):
        self._fetch = N.fetch

    def tearDown(self):
        N.fetch = self._fetch

    def test_reads_pages_back_to_the_cutoff_then_stops(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        calls = []

        def page(n):
            when = now - datetime.timedelta(days=10 * n)
            return ('<?xml version="1.0"?><rss version="2.0"><channel><item><title>t%d</title>'
                    '<link>https://p.example/%d</link><pubDate>%s</pubDate></item></channel></rss>'
                    % (n, n, when.strftime("%a, %d %b %Y %H:%M:%S GMT"))).encode()

        def fake(url):
            calls.append(url)
            n = int(url.split("paged=")[1]) if "paged=" in url else 1
            return page(n)
        N.fetch = fake
        src = {"id": "p", "name": "P", "url": "https://p.example/feed/", "paged": True, "specialities": []}
        items = N.fetch_source_items(src, now - datetime.timedelta(days=35), pause=0)
        # pages 1..4 are dated 10, 20, 30, 40 days ago: page 4 crosses the cutoff, so no page 5.
        self.assertEqual(len(items), 4)
        self.assertEqual(calls[-1], "https://p.example/feed/?paged=4")

    def test_unpaged_source_fetches_once(self):
        calls = []
        N.fetch = lambda url: calls.append(url) or b'<rss><channel></channel></rss>'
        N.fetch_source_items({"id": "x", "name": "X", "url": "https://x.example"},
                             datetime.datetime.now(datetime.timezone.utc), pause=0)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
