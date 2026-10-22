#!/usr/bin/env python3
"""The My Hub snapshot (app/my-hub-snapshot.js, app/my-hub-logic.js), 22/10/2026.

Customer call with Aneeka Hussain (Ego Pharmaceuticals, dermatology): My Hub
opens as a dashboard for the member's chosen specialities. Four cards (news,
prescribing market, calendar, ICB changes), every figure from a file the Hub
already holds, honest empty states. The pure functions run under node against
the real dermatology and ICB files; wiring is checked on the source.

    python3 test_my_hub_snapshot.py
"""
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LOGIC = os.path.join(HERE, "app", "my-hub-logic.js")
RUNNER = r"""
const L = require(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(cases.map(([fn, args]) => L[fn].apply(null, args))));
"""


def node(calls):
    n = shutil.which("node")
    if not n:
        raise unittest.SkipTest("node not installed")
    r = subprocess.run([n, "-e", RUNNER, LOGIC, json.dumps(calls)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def load(*p):
    with open(os.path.join(HERE, *p), encoding="utf-8") as f:
        return f.read()


DERM = json.loads(load("data", "speciality-panels", "dermatology.json"))
ICB = json.loads(load("data", "icb-watch.json"))
DERM_SPEC = {"id": "dermatology", "label": "Dermatology"}


class Market(unittest.TestCase):
    def test_dermatology_figures_are_the_files_own(self):
        h = node([["marketHeadlines", [DERM]]])[0]
        self.assertIsNotNone(h)
        gp = DERM["gpPrescribing"]
        self.assertEqual([m["id"] for m in h["markets"]], [m["id"] for m in gp["markets"]])
        for m, src in zip(h["markets"], gp["markets"]):
            self.assertEqual(m["items"], src["items"])
            self.assertEqual(m["cost"], src["cost"])
            self.assertEqual(m["itemsYoY"], src["itemsYoY"])
            self.assertEqual(m["lead"]["label"], src["topNational"][0]["label"])
        self.assertTrue(h["sourceUrl"].startswith("https://opendata.nhsbsa.net"))
        self.assertIn("Open Government Licence", h["attribution"])

    def test_period_is_a_month_name(self):
        out = node([["periodLabel", ["202608"]], ["periodLabel", ["2026"]], ["periodLabel", [None]]])
        self.assertEqual(out, ["August 2026", "", ""])

    def test_no_market_is_null_never_invented(self):
        out = node([["marketHeadlines", [{"gpPrescribing": {"defined": False}}]], ["marketHeadlines", [{}]],
                    ["marketHeadlines", [None]], ["marketHeadlines", [{"gpPrescribing": {"defined": True, "markets": []}}]]])
        self.assertEqual(out, [None, None, None, None])


class Icb(unittest.TestCase):
    def test_window_and_counts(self):
        c = node([["icbChanges", [ICB, [DERM_SPEC], "2026-10-22", 120]]])[0]
        self.assertEqual(c["count"], ICB["count"])
        self.assertEqual(c["abolished"], len(ICB["abolished"]))
        self.assertEqual(c["clusters"], len(ICB["clusters"]))
        self.assertEqual(len(c["events"]), len(ICB["events"]))
        old = node([["icbChanges", [ICB, [DERM_SPEC], "2026-10-22", 10]]])[0]
        self.assertTrue(all(e["date"] >= "2026-10-12" for e in old["events"]))

    def test_relevance_needs_the_speciality_named_in_the_text(self):
        c = node([["icbChanges", [ICB, [DERM_SPEC], "2026-10-22", 120]]])[0]
        rel = [e for e in c["events"] if e["relevant"]]
        self.assertEqual(len(rel), 1)
        self.assertIn("Skin chapter", rel[0]["headline"])
        self.assertEqual(c["events"][0], rel[0])      # relevant first
        none = node([["icbChanges", [ICB, [{"id": "orthopaedics-and-trauma", "label": "Orthopaedics and Trauma"}], "2026-10-22", 120]]])[0]
        self.assertFalse(any(e["relevant"] for e in none["events"]))

    def test_failed_or_odd_file_is_null(self):
        self.assertEqual(node([["icbChanges", [None, [], "2026-10-22", 120]], ["icbChanges", [{}, [], "2026-10-22", 120]]]), [None, None])

    def test_future_dated_event_is_not_shown(self):
        w = {"count": 36, "events": [{"id": "x", "date": "2026-12-01", "kind": "curated", "headline": "Skin thing", "sources": []}]}
        self.assertEqual(node([["icbChanges", [w, [DERM_SPEC], "2026-10-22", 120]]])[0]["events"], [])


PANELS = os.path.join(HERE, "app", "hub-panels.js")
SECS = ["frameworks", "tenders", "local", "awards", "tariff-moves", "dsu"]


def sec(panels, ids):
    n = shutil.which("node")
    if not n:
        raise unittest.SkipTest("node not installed")
    run = "const P=require(process.argv[1]);const d=JSON.parse(process.argv[2]);const o={};JSON.parse(process.argv[3]).forEach(i=>o[i]=P.sectionSummary(d,i,'2026-10-22'));process.stdout.write(JSON.stringify(o))"
    r = subprocess.run([n, "-e", run, PANELS, json.dumps(panels), json.dumps(ids)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class PinnableSections(unittest.TestCase):
    """Every section of a speciality page can be pinned; the My Hub card is the file's own rows."""

    def test_rows_come_from_the_file(self):
        o = sec(DERM, SECS)
        self.assertEqual(o["awards"]["total"], len(DERM["awards"]))
        self.assertEqual(o["awards"]["rows"][0]["t"], DERM["awards"][0]["title"])
        self.assertEqual(o["local"]["total"], len(DERM["localIntel"]))
        self.assertEqual(o["dsu"]["rows"][0]["t"], DERM["mhraDsu"]["updates"][0]["title"])
        self.assertIn("lines changed price", o["tariff-moves"]["lede"])
        self.assertLessEqual(len(o["awards"]["rows"]), 5)

    def test_empty_sections_are_null_not_invented(self):
        o = sec(DERM, ["frameworks", "tenders"])   # dermatology has none of either
        self.assertIsNone(o["frameworks"])
        self.assertIsNone(o["tenders"])

    def test_frameworks_soonest_end_first(self):
        d = {"frameworks": [{"name": "B", "ends": "31 August 2028"}, {"name": "A", "ends": "1 March 2027"}, {"name": "C"}]}
        self.assertEqual([r["t"] for r in sec(d, ["frameworks"])["frameworks"]["rows"]], ["A", "B", "C"])

    def test_tender_stage_is_not_called_an_award(self):
        d = {"awards": [{"title": "T", "stage": "tender", "date": "2026-10-16", "buyer": "B"}]}
        self.assertIn("not yet awarded", sec(d, ["awards"])["awards"]["rows"][0]["s"])

    def test_unknown_section_is_null(self):
        self.assertIsNone(sec(DERM, ["nonsense"])["nonsense"])

    def test_pin_buttons_wired_on_the_page_and_drawn_on_my_hub(self):
        sp = load("app", "speciality-panels.js")
        for i in SECS:
            self.assertIn("secHead('" + i + "'", sp)
        self.assertIn("'sec:' + id", sp)
        mp = load("app", "my-hub-panels.js")
        self.assertIn("P.sectionSummary(d, k.id", mp)
        self.assertIn("k.kind === 'sec'", mp)
        self.assertIn("Source: ", mp)

    def test_add_to_my_hub_on_every_page(self):
        self.assertNotIn("it.group === 'specialities' ? '<button", load("app", "hub-chrome.js"))


class Wiring(unittest.TestCase):
    def setUp(self):
        self.js = load("app", "my-hub.js")
        self.snap = load("app", "my-hub-snapshot.js")

    def test_module_is_loaded_before_overlays_and_painted_first(self):
        self.assertIn("'app/my-hub-snapshot.js'", self.js)
        m = [l for l in self.js.splitlines() if l.lstrip().startswith("var MODULES")][0]
        self.assertLess(m.index("my-hub-snapshot.js"), m.index("my-hub-overlays.js"))
        self.assertLess(self.js.index('id="mx-snap"'), self.js.index('id="mx-know"'))
        self.assertIn("M.snapshot.load()", self.js)

    def test_full_desk_sits_under_more_and_opens_when_nothing_is_picked(self):
        self.assertIn('<details class="mx-deeper" id="mx-deeper">', self.js)
        self.assertIn("dd.open = true", self.js)

    def test_snapshot_sources_are_repo_files_and_each_card_links_deeper(self):
        for f in ("data/speciality-panels/", "data/icb-watch.json"):
            self.assertIn(f, self.snap)
        for link in ("/medical-sales-hub/news/", "/medical-sales-hub/calendar/", "/medical-sales-hub/nhs-structure-map/"):
            self.assertIn(link, self.snap)
        self.assertIn("NHSBSA English Prescribing Dataset", self.snap)

    def test_empty_states_are_honest(self):
        for s in ("Pick your specialities", "No prescribing market is defined for", "No ICB change recorded",
                  "unavailable just now", "Nothing dated for your specialities"):
            self.assertIn(s, self.snap)

    def test_no_stale_copy_or_hard_coded_figures(self):
        self.assertNotRegex(self.snap, r"\b\d{3},\d{3}\b")   # no pasted prescribing totals
        self.assertNotIn("1 April 2026", self.snap)

    def test_pages_exist_in_catalogue(self):
        urls = {i["url"] for i in json.loads(load("hub", "my-hub-catalogue.json"))["items"]}
        self.assertIn("/medical-sales-hub/nhs-structure-map/", urls)

    def test_css_present(self):
        css = load("app", "my-hub.css")
        for c in (".snap-grid", ".mx-deeper"):
            self.assertIn(c, css)


if __name__ == "__main__":
    unittest.main()
