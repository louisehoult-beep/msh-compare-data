#!/usr/bin/env python3
"""Pin a panel to My Hub, and the .ics calendar export (app/hub-panels.js).

Lou, 22/10/2026 (call with Aneeka Hussain, Ego Pharmaceuticals): a member can
star a prescribing panel or the calendar on a speciality page and see it on
My Hub; the speciality calendar downloads as .ics with a link back to the Hub
on every event, and only rows the Hub already holds. Pure functions run under
node; the wiring checks read the source. Stdlib only; node is skipped,
loudly, where missing.

    python3 test_my_hub_panels.py
"""
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "app", "hub-panels.js")
NOW = "2026-10-22T09:30:15.123Z"

RUNNER = r"""
const P = require(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(cases.map(([fn, args]) => P[fn].apply(null, args))));
"""


def node(calls):
    n = shutil.which("node")
    if not n:
        raise unittest.SkipTest("node not installed")
    r = subprocess.run([n, "-e", RUNNER, LIB, json.dumps(calls)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def src(*parts):
    with open(os.path.join(HERE, *parts), encoding="utf-8") as f:
        return f.read()


HUB = "https://medsalesintelligencehub.co.uk/medical-sales-hub/dermatology/"


def ev(id_, type_="event", date="2027-03-12", **kw):
    e = {"id": id_, "type": type_, "title": "Title " + id_, "date": date, "endDate": None, "owner": "Society (S)",
         "source": "https://example.org/" + id_, "verified": "2026-09-30", "specialities": ["dermatology"],
         "links": [{"label": "Dermatology", "url": HUB, "kind": "hub"}], "note": "A note, with; punctuation"}
    e.update(kw)
    return e


class PanelKeys(unittest.TestCase):
    def test_round_trip(self):
        key, parsed = node([["panelKey", ["/medical-sales-hub/dermatology/", "gp:skin"]],
                            ["parsePanelKey", ["/medical-sales-hub/dermatology/#pin=gp:skin"]]])
        self.assertEqual(key, "/medical-sales-hub/dermatology/#pin=gp:skin")
        self.assertEqual(parsed, {"page": "/medical-sales-hub/dermatology/", "slug": "dermatology", "kind": "gp", "id": "skin"})

    def test_only_hub_panel_addresses_parse(self):
        bad = ["/medical-sales-hub/dermatology/", "/medical-sales-hub/dermatology/#pin=", "https://evil.example/#pin=calendar",
               "/other/dermatology/#pin=calendar", "/medical-sales-hub/dermatology/#pin=calendar:a:b", None]
        for out in node([["parsePanelKey", [u]] for u in bad]):
            self.assertIsNone(out)

    def test_two_members_two_sets(self):
        a = [{"u": "/medical-sales-hub/dermatology/#pin=calendar", "t": "x", "k": "panel"}, {"u": "/p/", "t": "p", "k": "page"}]
        b = [{"u": "/medical-sales-hub/dermatology/#pin=gp:skin", "t": "y", "k": "panel"}]
        ra, rb = node([["pinnedPanels", [a]], ["pinnedPanels", [b]]])
        self.assertEqual([x["u"] for x in ra], ["/medical-sales-hub/dermatology/#pin=calendar"])
        self.assertEqual([x["u"] for x in rb], ["/medical-sales-hub/dermatology/#pin=gp:skin"])

    def test_a_panel_kind_with_a_page_address_is_not_a_pin(self):
        self.assertEqual(node([["pinnedPanels", [[{"u": "/medical-sales-hub/dermatology/", "t": "x", "k": "panel"}]]]])[0], [])


class CalendarRows(unittest.TestCase):
    def test_filters_to_speciality_dated_sourced_not_past_soonest_first(self):
        entries = [ev("late", date="2027-05-01"), ev("soon", date="2026-11-01"), ev("past", date="2026-01-01"),
                   ev("other", specialities=["cardiology-and-cardiac-surgery"]), ev("nosource", source=None),
                   ev("baddate", date="soon"), ev("body", type_="body"), ev("fw", type_="framework-end", date="2027-01-31"),
                   ev("running", date="2026-10-20", endDate="2026-10-23")]
        rows = node([["calendarRows", [entries, "dermatology", "2026-10-22"]]])[0]
        self.assertEqual([r["id"] for r in rows], ["running", "soon", "fw", "late"])

    def test_real_dermatology_rows_are_all_published_with_sources(self):
        with open(os.path.join(HERE, "data", "hub-calendar.json"), encoding="utf-8") as f:
            cal = json.load(f)
        rows = node([["calendarRows", [cal["entries"], "dermatology", "2000-01-01"]]])[0]
        self.assertTrue(rows, "dermatology has dated rows")
        for r in rows:
            self.assertRegex(r["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(r["source"].startswith("http"), r["id"])


class Ics(unittest.TestCase):
    def build(self, rows):
        return node([["ics", [rows, "dermatology", "Dermatology (Medical Sales Hub)", NOW]]])[0]

    def test_shape_and_crlf(self):
        t = self.build([ev("a", endDate="2027-03-13")])
        self.assertTrue(t.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"))
        self.assertTrue(t.endswith("END:VEVENT\r\nEND:VCALENDAR\r\n"))
        self.assertNotRegex(t, r"(?<!\r)\n")
        self.assertIn("DTSTAMP:20261022T093015Z", t)
        self.assertIn("UID:a@medsalesintelligencehub.co.uk", t)

    def test_all_day_dates_end_is_exclusive(self):
        t = self.build([ev("a", date="2027-03-12", endDate="2027-03-13"), ev("b", date="2026-12-31")])
        self.assertIn("DTSTART;VALUE=DATE:20270312\r\nDTEND;VALUE=DATE:20270314", t)
        self.assertIn("DTSTART;VALUE=DATE:20261231\r\nDTEND;VALUE=DATE:20270101", t)

    def test_each_event_links_back_to_the_hub_and_its_source(self):
        t = self.build([ev("a"), ev("b", links=[])])
        self.assertEqual(t.count("URL:" + HUB), 2)
        unfolded = t.replace("\r\n ", "")
        self.assertEqual(unfolded.count("More on the Medical Sales Hub: " + HUB), 2)
        self.assertIn("Published source: https://example.org/a", unfolded.replace("\\n", "\n"))

    def test_text_escaped_and_lines_folded(self):
        t = self.build([ev("a", title="A, B; C\\D", note="x" * 300, location="Hall, City")])
        self.assertIn(r"SUMMARY:A\, B\; C\\D", t)
        self.assertIn("LOCATION:Hall\\, City", t)
        for line in t.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_multibyte_is_not_split(self):
        t = self.build([ev("a", title="é" * 80)])
        self.assertIn("é" * 80, t.replace("\r\n ", ""))

    def test_filename(self):
        self.assertEqual(node([["icsName", ["dermatology", ""]]])[0], "msh-dermatology-calendar.ics")
        self.assertEqual(node([["icsName", ["dermatology", "ev-pcds-2027"]]])[0], "msh-dermatology-ev-pcds-2027.ics")


class GpSummary(unittest.TestCase):
    def test_real_dermatology_markets(self):
        with open(os.path.join(HERE, "data", "speciality-panels", "dermatology.json"), encoding="utf-8") as f:
            d = json.load(f)
        ids = [m["id"] for m in d["gpPrescribing"]["markets"]]
        self.assertTrue(ids)
        outs = node([["gpSummary", [d, i]] for i in ids] + [["gpSummary", [d, "nope"]]])
        for o in outs[:-1]:
            self.assertEqual(len(o["top"]) <= 5, True)
            self.assertTrue(o["label"])
        self.assertIsNone(outs[-1])


class Wiring(unittest.TestCase):
    def test_server_and_client_accept_panel_kind(self):
        self.assertIn("'panel' === $s['k']", src("hub", "wpcode", "my-hub-pins.php"))
        self.assertIn("s.k === 'panel'", src("app", "hub-account.js"))

    def test_speciality_page_has_pin_calendar_and_ics(self):
        s = src("app", "speciality-panels.js")
        for need in ("data-pin", "Add all to my calendar", "Add to my calendar", "hub-calendar.json", "'gp:' + M.id", "P.ics("):
            self.assertIn(need, s)
        self.assertIn("hidden data-pin", s, "pin buttons are hidden until the member's account is loaded")

    def test_my_hub_shows_pinned_panels_and_keeps_them_out_of_saved(self):
        s = src("app", "my-hub.js")
        self.assertIn("mx-panels", s)
        self.assertIn("M.panels.html()", s)
        self.assertIn("'app/hub-panels.js'", s)
        self.assertIn("x.k !== 'panel'", s)

    def test_one_click_add_speciality(self):
        s = src("app", "hub-chrome.js")
        self.assertIn("Add to My Hub", s)
        self.assertIn("A.addPin(it.id)", s)
        self.assertIn("it.group === 'specialities'", s)

    def test_no_dashes_in_member_copy(self):
        for f in ("hub-panels.js", "my-hub-panels.js"):
            body = re.sub(r"/\*.*?\*/", "", src("app", f), flags=re.S)
            self.assertNotRegex(body, "[–—]", f)


if __name__ == "__main__":
    unittest.main()
