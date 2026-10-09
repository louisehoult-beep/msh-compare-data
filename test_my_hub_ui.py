#!/usr/bin/env python3
"""My Hub's front-end modules: they parse, they load what they say they load,
and their member-facing copy keeps the house rules.

The home screen (2026-10) is app/my-hub.js plus five modules it loads itself.
A module that is renamed, or a file that stops being loaded, leaves members on
"My Hub is unavailable" with nothing in the logs, so the wiring is pinned
here. Copy rules: no em or en dash, "medical sales" never "medtech", and
the controls the tour and What's new point at actually exist.

    python3 test_my_hub_ui.py
"""
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
FILES = ["my-hub.js", "my-hub-feeds.js", "my-hub-overlays.js", "my-hub-logic.js", "hub-icons.js", "hub-account.js", "hub-chrome.js"]
TARGETS = {"spec", "scope", "tools", "library", "briefing", "saved", "search", "how", "new"}


def read(name):
    with open(os.path.join(APP, name), encoding="utf-8") as f:
        return f.read()


class MyHubUi(unittest.TestCase):
    def test_modules_parse(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed; parse not checked here (verify.py also checks)")
        for f in FILES:
            r = subprocess.run([node, "--check", os.path.join(APP, f)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, f + ": " + r.stderr)

    def test_loader_loads_every_module_and_file(self):
        src = read("my-hub.js")
        for need in ("app/hub-icons.js", "app/hub-account.js", "app/my-hub-logic.js", "app/my-hub-feeds.js",
                     "app/my-hub-overlays.js", "app/my-hub.css", "hub/my-hub-catalogue.json", "hub/whats-new.json"):
            self.assertIn("'" + need + "'", src, need)
        self.assertEqual(len(re.findall(r"raw\.githubusercontent\.com", src)), 1, "one BASE constant only")
        self.assertIn("window.MSH_MYHUB_BASE", src)

    def test_search_modal_reuses_hub_search(self):
        ov = read("my-hub-overlays.js")
        self.assertIn("data-hub-search-embed", ov)
        self.assertIn("data-hub-search-results", ov)
        self.assertIn("'app/hub-search.js'", ov)
        self.assertIn("[data-hub-search-embed]", read("hub-search.js"))

    def test_every_tour_stop_and_bar_control_exists(self):
        page, ov = read("my-hub.js"), read("my-hub-overlays.js")
        stops = re.findall(r"\[\s*'([a-z]+)',\s*'[^']+',\s*'[^']*'\s*\]", ov)
        self.assertEqual(len(stops), 9, "the tour has nine stops (the checklist says so)")
        controls = set(re.findall(r"data-tour=\"([a-z]+)\"", page)) | set(re.findall(r"ib\('([a-z]+)'", page))
        for s in stops:
            self.assertIn(s, controls, "tour stop %s has no control" % s)
        self.assertEqual(TARGETS, set(stops))

    def test_whats_new_targets_are_real_controls(self):
        with open(os.path.join(HERE, "hub", "whats-new.json"), encoding="utf-8") as f:
            entries = json.load(f)["entries"]
        for e in entries:
            s = e["showMe"]
            if s and not s.startswith("/"):
                self.assertIn(s, TARGETS | {"checklist", "pages"}, e["id"])

    def test_whats_new_box_pill_strip_and_footer(self):
        page = read("my-hub.js")
        # Phone strip (Lou, 01/10/2026) and the box/pill rule (ruling F10).
        self.assertIn('id="wn-strip"', page)
        self.assertIn("whatsNewMode(", page)
        # Nothing unseen: the bar button still opens the recent entries read-only.
        self.assertIn("No new changes since your last visit", page)
        # Ruling F13: the "tell us what you need" path ships with stage 4.
        self.assertNotIn("tell us what you need", page.lower())

    def test_copy_has_no_dashes_or_medtech(self):
        for f in FILES:
            src = read(f)
            for ch in ("\u2014", "\u2013"):
                # Comments may quote history; strings shown to members may not.
                for lit in re.findall(r"'(?:[^'\\\n]|\\.)*'", src):
                    self.assertNotIn(ch, lit, "%s: dash in %s" % (f, lit[:60]))
            self.assertNotRegex(src.lower(), r"\bmed ?tech\b", f)

    def test_phone_alerts_not_in_page_or_feeds_source(self):
        for f in ("my-hub.js", "my-hub-feeds.js"):
            self.assertNotIn("phone-alerts", read(f), "phone alerts are parked: not promoted on My Hub")

    def test_phone_alerts_not_in_launcher_or_picker_lists(self):
        # Source text cannot see this: the catalogue feeds phone-alerts
        # (group "account") into the launcher, so check the lists themselves.
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed; lists not checked here")
        script = (
            "var fs=require('fs');var cat=JSON.parse(fs.readFileSync('hub/my-hub-catalogue.json','utf8'));"
            "global.window={};window.MSH_MYHUB_LOGIC=require('./app/my-hub-logic.js');"
            "var by={};cat.items.forEach(function(i){by[i.id]=i;});"
            "window.MSH_MYHUB={cat:cat,byId:by,esc:String,svg:String,mine:function(){return {};},narrowed:function(){return false;}};"
            "(0,eval)(fs.readFileSync('app/my-hub-overlays.js','utf8'));"
            "console.log(JSON.stringify(window.MSH_MYHUB.ui.lists()));")
        r = subprocess.run([node, "-e", script], cwd=HERE, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        lists = json.loads(r.stdout)
        self.assertGreater(len(lists["picker"]), 50, "the picker lists the catalogue")
        self.assertGreater(len(lists["tools"]), 30, "All tools lists the catalogue")
        for name, ids in lists.items():
            self.assertNotIn("phone-alerts", ids, name)

    def _tool_lists(self, mine, narrowed):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed; lists not checked here")
        script = (
            "var fs=require('fs');var cat=JSON.parse(fs.readFileSync('hub/my-hub-catalogue.json','utf8'));"
            "global.window={};window.MSH_MYHUB_LOGIC=require('./app/my-hub-logic.js');"
            "var by={};cat.items.forEach(function(i){by[i.id]=i;});"
            "var mine=" + json.dumps(mine) + ",nar=" + json.dumps(narrowed) + ";"
            "window.MSH_MYHUB={cat:cat,byId:by,esc:String,svg:String,mine:function(){return mine;},narrowed:function(){return nar;}};"
            "(0,eval)(fs.readFileSync('app/my-hub-overlays.js','utf8'));"
            "console.log(JSON.stringify(window.MSH_MYHUB.ui.lists()));")
        r = subprocess.run([node, "-e", script], cwd=HERE, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_tools_launcher_narrows_by_speciality_but_picker_does_not(self):
        wide = self._tool_lists({}, False)
        for id_ in ("tool-supplier-search", "tool-wound-savings-calculator", "intelligence-feed", "pharmaceutical-sales"):
            self.assertIn(id_, wide["tools"], id_)
        narrow = self._tool_lists({"renal": 1}, True)
        self.assertIn("tool-supplier-search", narrow["tools"], "general tools stay")
        for id_ in ("tool-wound-savings-calculator", "intelligence-feed", "pharmaceutical-sales", "fall-prevention-medical-sales-market-insights"):
            self.assertNotIn(id_, narrow["tools"], id_)
        hit = self._tool_lists({"tissue-viability-and-wound-care": 1}, True)
        self.assertIn("tool-wound-savings-calculator", hit["tools"])
        self.assertNotIn("intelligence-feed", hit["tools"])
        self.assertEqual(narrow["picker"], wide["picker"], "the page picker is never narrowed")
        self.assertEqual(narrow["popular"], wide["popular"])
        for lists in (wide, narrow, hit):
            for name, ids in lists.items():
                self.assertNotIn("phone-alerts", ids, name)

    def test_tools_launcher_offers_everything_from_its_note(self):
        src = read("my-hub-overlays.js")
        self.assertIn("Showing tools for your specialities. Everything shows the rest.", src)
        self.assertRegex(src, r'data-scope="all"[^>]*data-k="tools-all"')

    def test_tour_skips_missing_targets_and_never_marks_seen_when_empty(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        script = (
            "var fs=require('fs');global.window={};window.MSH_MYHUB_LOGIC=require('./app/my-hub-logic.js');"
            "window.MSH_MYHUB={cat:{items:[]},byId:{},esc:String,svg:String};"
            "(0,eval)(fs.readFileSync('app/my-hub-overlays.js','utf8'));var p=window.MSH_MYHUB.ui.pickStep;"
            "var all=[1,1,1,1,1,1,1,1,1].map(Boolean),mid=all.slice();mid[3]=false;"
            "console.log(JSON.stringify([p(3,1,mid),p(3,-1,mid),p(2,1,mid),p(0,1,all),"
            "p(5,1,[0,0,0,0,0,0,0,0,0].map(Boolean)),p(8,1,[1,0,0,0,0,0,0,0,0].map(Boolean))]));")
        r = subprocess.run([node, "-e", script], cwd=HERE, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [4, 2, 2, 0, -1, 0])
        ov = read("my-hub-overlays.js")
        body = ov[ov.index("function show("):ov.index("function show(") + 500]
        self.assertIn("closeTourQuietly(); return;", body)
        self.assertNotIn("endTour(false)", body, "a missing target must not store tourSeen")

    def test_tour_traps_tab_and_wire_runs_once(self):
        ov = read("my-hub-overlays.js")
        self.assertIn("getComputedStyle(x).visibility", ov)
        self.assertIn("if (wired) { return; }", ov)

    def test_home_screen_dialog_names_no_third_party_platform(self):
        ov = read("my-hub-overlays.js")
        for word in ("Safari", "Chrome", "iPhone", "Android"):
            self.assertNotIn(word, ov, word)


if __name__ == "__main__":
    unittest.main(verbosity=1)
