#!/usr/bin/env python3
"""The pure functions behind My Hub (app/my-hub-logic.js), run under node.

Each case is a call with fixed inputs, so a rule can be changed only by
changing this file too: the What's new window, the checklist, which library
band a member is sent to, the two-per-speciality news rule, which profile a
page shows under. Stdlib only; node is on ubuntu-latest and is skipped,
loudly, where it is missing.

    python3 test_my_hub_logic.py
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
const out = cases.map(([fn, args]) => L[fn].apply(null, args));
process.stdout.write(JSON.stringify(out));
"""

TODAY = "2026-10-01"
NOW = "2026-10-01T12:00:00+01:00"


def story(spec, title, published, **kw):
    it = {"title": title, "link": "https://example.org/" + title.replace(" ", "-"), "published": published}
    it.update(kw)
    return {"it": it, "spec": spec}


class MyHubLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")

    def call(self, *cases):
        if not self.node:
            self.skipTest("node not installed; my-hub-logic.js not exercised")
        r = subprocess.run([self.node, "-e", RUNNER, LOGIC, json.dumps(list(cases))],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_words(self):
        got = self.call(["greeting", [9]], ["greeting", [13]], ["greeting", [19]],
                        ["joinNames", [[]]], ["joinNames", [["Urology"]]],
                        ["joinNames", [["A", "B", "C"]]],
                        ["specShort", [[]]],
                        ["specShort", [["Tissue Viability and Wound Care", "Urology", "Theatres and Surgical"]]])
        self.assertEqual(got, ["Good morning", "Good afternoon", "Good evening", "", "Urology",
                               "A, B and C", "None chosen", "Tissue Viability +2"])

    def test_whats_new_unseen_window_and_order(self):
        entries = [
            {"id": "old", "date": "2026-06-01", "showMe": None},
            {"id": "seen", "date": "2026-09-30", "showMe": "tools"},
            {"id": "a", "date": "2026-09-20", "showMe": "tools"},
            {"id": "b", "date": "2026-10-01", "showMe": "/medical-sales-hub/calendar/"},
            {"id": "future", "date": "2026-10-09", "showMe": "saved"},
        ]
        unseen, = self.call(["whatsNewUnseen", [entries, ["seen"], TODAY, 60]])
        self.assertEqual([e["id"] for e in unseen], ["b", "a"])
        dots, ids = self.call(["dotTargets", [unseen]], ["idsForTarget", [unseen, "tools"]])
        self.assertEqual(dots, {"tools": 1}, "a page path never puts a dot on a control")
        self.assertEqual(ids, ["a"])

    def test_whats_new_box_or_pill(self):
        e = [{"id": "b", "date": "2026-10-01"}, {"id": "a", "date": "2026-09-20"}]
        none, first, mini, newer = self.call(
            ["whatsNewMode", [[], None]], ["whatsNewMode", [e, None]],
            ["whatsNewMode", [e, "b"]], ["whatsNewMode", [e, "a"]])
        self.assertEqual((none, first, mini, newer), ("none", "box", "pill", "box"),
                         "box on first visit after a new entry, pill once minimised, box again for a newer one")

    def test_checklist(self):
        none, some, alls = self.call(
            ["checklist", [{"route": None, "specCount": 0, "briefing": False, "phone": False, "standalone": False, "tour": False}]],
            ["checklist", [{"route": "rep", "routeName": "Rep", "specCount": 3, "briefing": False, "phone": False, "standalone": True, "tour": False}]],
            ["checklist", [{"route": "rep", "routeName": "Rep", "specCount": 1, "briefing": True, "phone": True, "standalone": False, "tour": True}]])
        self.assertEqual((none["done"], none["total"], none["complete"]), (0, 5, False))
        self.assertEqual([s["key"] for s in none["steps"]], ["profile", "spec", "brief", "phone", "tour"])
        self.assertEqual(some["done"], 3, "profile, specialities, and a Home Screen launch count")
        self.assertEqual(some["steps"][0]["sub"], "Rep")
        self.assertEqual(some["steps"][1]["sub"], "3 chosen")
        self.assertTrue(alls["complete"])

    def test_library_targets(self):
        by = {"tissue-viability-and-wound-care": {"label": "Tissue Viability and Wound Care", "libraryBand": "wound-care"},
              "theatres-and-surgical": {"label": "Theatres and Surgical", "libraryBand": None},
              "urology": {"label": "Urology", "libraryBand": "urology"}}
        lib = "/medical-sales-hub/clinical-evidence-library/"
        a, b, c = self.call(
            ["libraryTargets", [["tissue-viability-and-wound-care", "urology"], by, False]],
            ["libraryTargets", [["theatres-and-surgical"], by, True]],
            ["libraryTargets", [["theatres-and-surgical", "tissue-viability-and-wound-care", "urology"], by, True]])
        self.assertEqual(a, [{"label": "All specialities", "url": lib}], "Everything opens the whole library")
        self.assertEqual(b, [{"label": "All specialities", "url": lib}], "a speciality with no band falls back")
        self.assertEqual([x["url"] for x in c], [lib + "#wound-care", lib + "#urology"])

    def test_by_profile(self):
        items = [{"id": "x", "group": "tools", "profiles": ["rep"]},
                 {"id": "y", "group": "tools", "profiles": []},
                 {"id": "z", "group": "specialities", "profiles": []}]
        allp, rep, rec = self.call(["byProfile", [items, "all"]], ["byProfile", [items, "rep"]], ["byProfile", [items, "recruit"]])
        self.assertEqual([i["id"] for i in allp], ["x", "y", "z"])
        self.assertEqual([i["id"] for i in rep], ["x", "z"])
        self.assertEqual([i["id"] for i in rec], ["z"], "specialities show under every profile")

    def test_news_two_per_speciality_above_the_fold(self):
        feed = [story("urology", "u%d" % i, "2026-10-01T0%d:00:00+01:00" % (9 - i)) for i in range(5)]
        feed += [story("renal", "r1", "2026-09-30T08:00:00+01:00"), story("renal", "job advert one", "2026-09-30T09:00:00+01:00")]
        out, = self.call(["newsList", [feed, {}, False, 3, NOW]])
        self.assertEqual([g["it"]["title"] for g in out[:3]], ["u0", "u1", "r1"])
        self.assertNotIn("job advert one", [g["it"]["title"] for g in out])
        mine, = self.call(["newsList", [feed, {"renal": 1}, True, 3, NOW]])
        self.assertEqual([g["it"]["title"] for g in mine], ["r1"])
        loading, failed = self.call(["newsList", [None, {}, False, 3, NOW]], ["newsList", [False, {}, False, 3, NOW]])
        self.assertIsNone(loading)
        self.assertFalse(failed)

    def test_dedupe_news(self):
        a = story("urology", "Same Story", "2026-09-30T08:00:00+01:00")
        b = story("renal", "Same story!", "2026-10-01T08:00:00+01:00")
        f = story("renal", "Event later", "2026-11-01T08:00:00+01:00")
        out, = self.call(["dedupeNews", [[a, b, f], NOW]])
        self.assertEqual([g["it"]["title"] for g in out], ["Same Story", "Event later"])

    def test_calendar_lists(self):
        cal = [
            {"id": 1, "type": "event", "date": "2026-10-05", "specialities": ["urology"]},
            {"id": 2, "type": "awareness", "date": "2026-09-20", "endDate": "2026-10-03", "specialities": ["renal"]},
            {"id": 3, "type": "event", "date": "2027-03-01", "specialities": ["urology"]},
            {"id": 4, "type": "framework-end", "date": "2026-10-20", "specialities": ["urology"]},
            {"id": 5, "type": "contract-expiry", "date": "2026-09-01", "specialities": ["urology"]},
        ]
        ev, mine, pr = self.call(["eventsList", [cal, {}, False, TODAY, 90]],
                                 ["eventsList", [cal, {"urology": 1}, True, TODAY, 90]],
                                 ["procList", [cal, {}, False, TODAY, 180]])
        self.assertEqual([e["id"] for e in ev], [2, 1], "ongoing first, then by date; beyond 90 days left out")
        self.assertEqual([e["id"] for e in mine], [1])
        self.assertEqual([e["id"] for e in pr], [4], "a past contract date is not a deadline")

    def test_tidy_and_dates(self):
        long = "A sentence that goes on for a while and does not stop at all because the feed cut it off mid wor"
        got = self.call(["tidy", ["Ends properly."]], ["tidy", [long]],
                        ["whenLabel", ["2026-10-02", TODAY]], ["whenLabel", ["2026-09-28", TODAY]],
                        ["fmtDate", ["2026-10-01"]], ["money", [2500000]], ["isJob", [{"title": "Vacancy: nurse"}]])
        self.assertEqual(got[0], "Ends properly.")
        self.assertTrue(got[1].endswith("\u2026"))
        self.assertNotIn(" wor\u2026", got[1])
        self.assertEqual(got[2:], ["Tomorrow", "3 days ago", "1 Oct 2026", "\u00a32.5m", True])

    def test_tools_for(self):
        items = [{"id": "a"}, {"id": "w", "specialities": ["wound"]}, {"id": "t", "specialities": ["theatres", "wound"]},
                 {"id": "u", "specialities": ["urology"]}, {"id": "b", "specialities": []}]
        ids = lambda r: [i["id"] for i in r]
        snapshot = json.dumps(items)
        none, nomatch, match, everything, nonarrow = self.call(
            ["toolsFor", [items, {}, True]],
            ["toolsFor", [items, {"renal": 1}, True]],
            ["toolsFor", [items, {"wound": 1}, True]],
            ["toolsFor", [items, {"wound": 1}, False]],
            ["toolsFor", [items, {"wound": 1, "urology": 1}, True]])
        self.assertEqual(ids(none), ["a", "w", "t", "u", "b"], "no specialities picked: everything")
        self.assertEqual(ids(nomatch), ["a", "b"], "narrowed, no match: generals only")
        self.assertEqual(ids(match), ["a", "w", "t", "b"], "narrowed with a match, order kept")
        self.assertEqual(ids(everything), ["a", "w", "t", "u", "b"], "Everything mode: every item")
        self.assertEqual(ids(nonarrow), ["a", "w", "t", "u", "b"])
        mut = subprocess.run([self.node, "-e",
            "const L=require(process.argv[1]);const it=JSON.parse(process.argv[2]),m={wound:1};"
            "const a=JSON.stringify(it)+JSON.stringify(m);const r=L.toolsFor(it,m,true);r.pop();"
            "process.stdout.write(String(a===JSON.stringify(it)+JSON.stringify(m)&&r!==it))",
            LOGIC, snapshot], capture_output=True, text=True, timeout=60)
        self.assertEqual(mut.stdout, "true", "inputs are not mutated and the result is a new array")
        hashed, = self.call(["safeUrl", ["/medical-sales-hub/med-sales-tools/#view-value"]])
        self.assertEqual(hashed, "/medical-sales-hub/med-sales-tools/#view-value", "a tool view URL survives safeUrl")

    def test_safe_url(self):
        urls = ["javascript:alert(1)", "JAVASCRIPT:alert(1)", "data:text/html,x", "//evil.com", "/\\evil.com",
                " javascript:x", "/path", "https://x", "http://x/a?b=1", "", None]
        got = self.call(*[["safeUrl", [u]] for u in urls])
        self.assertEqual(got, ["#", "#", "#", "#", "#", "#", "/path", "https://x", "http://x/a?b=1", "#", "#"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
