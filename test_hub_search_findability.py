#!/usr/bin/env python3
"""Hub search: a rep searching a PRODUCT must land on the buying route.

Added 18/11/2026. Searching "surgical stapling" returned three pages and neither
the Minimally Invasive Surgery framework (whose Lot 3 is "Surgical Stapling
Devices") nor the Compare tool. Four causes, each held here:

  1. build_search_index.bag() cut an over-long section to its first 120 words
     ALPHABETICALLY, so words from s to z (stapling, sutures, wound, thoracic)
     were thrown away from the sections that discuss them.
  2. Framework names live in data/frameworks.json and the tools draw their
     content from JSON, so neither exists in a crawled page: no framework or
     tool was in the index at all.
  3. "stapler / staplers / stapling / staples" matched only as exact words.
  4. The Hub files the answer under the buying route; the query names the
     product. A short curated concept list (CONCEPTS in app/hub-search.js) joins
     them.

The ranking tests run the SHIPPED app/hub-search.js under node against an index
built here from the real builder functions, so they need no network and do not
depend on the day's crawl. Skipped when node is absent.

    python3 test_hub_search_findability.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BSE = _load("bse_findability", "build_search_index.py")
NODE = shutil.which("node")

DRIVER = r"""
const fs=require('fs'),vm=require('vm');
const [,, js, idx, qsJson]=process.argv;
const embed={querySelector:()=>null};
const win={MSH_HUB_SEARCH_INDEX:JSON.parse(fs.readFileSync(idx,'utf8')),addEventListener(){}};
const doc={getElementById:()=>null,querySelector:(s)=>s==='[data-hub-search-embed]'?embed:null,
  documentElement:{getAttribute:()=>null,setAttribute(){}},addEventListener(){}};
win.document=doc;
const ctx=vm.createContext({window:win,document:doc,fetch:()=>Promise.reject(1),console,setTimeout,clearTimeout,Date,Promise,encodeURIComponent});
vm.runInContext(fs.readFileSync(js,'utf8'),ctx);
const out={}, plans={};
for(const q of JSON.parse(qsJson)){
  plans[q]=(win.MSH_HUB_PLAN(q)||[]).map(x=>x[1]);
  out[q]=win.MSH_HUB_RANK(q).slice(0,8).map(x=>x.kind==='rec'?{k:'rec',t:x.rec.t,c:x.rec.c,u:x.rec.u}:{k:'page',t:x.page.t,u:x.page.u,h:x.sec?x.sec.h:''});
}
out.__plans=plans;
console.log(JSON.stringify(out));
"""


def rank(index_path, queries):
    tmp = tempfile.mkdtemp()
    try:
        driver = os.path.join(tmp, "driver.js")
        with open(driver, "w") as f:
            f.write(DRIVER)
        r = subprocess.run([NODE, driver, os.path.join(HERE, "app", "hub-search.js"),
                            index_path, json.dumps(queries)], capture_output=True, text=True, timeout=120)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class Bag(unittest.TestCase):
    def test_rare_words_survive_the_cap(self):
        # 300 distinct words, alphabetically stapling/sutures sit past 120.
        filler = ["alpha%03d" % i for i in range(300)]
        text = " ".join(filler + ["stapling", "sutures", "wound"])
        df = {w: 400 for w in filler}           # filler is everywhere in the Hub
        df.update({"stapling": 3, "sutures": 3, "wound": 20})
        got = BSE.bag(text, df, 1000).split()
        for w in ("stapling", "sutures", "wound"):
            self.assertIn(w, got)
        self.assertEqual(len(got), BSE.MAX_WORDS)

    def test_alphabetical_cut_loses_them(self):
        filler = ["alpha%03d" % i for i in range(300)]
        got = BSE.bag(" ".join(filler + ["stapling"])).split()
        self.assertNotIn("stapling", got)      # the old behaviour, kept for a bare call

    def test_still_sorted_unique_and_capped(self):
        words = ["w%03d" % i for i in range(400)] * 3
        df = {w: i % 50 for i, w in enumerate(sorted(set(words)))}
        got = BSE.bag(" ".join(words), df, 500).split()
        self.assertEqual(got, sorted(set(got)))
        self.assertLessEqual(len(got), BSE.MAX_WORDS)

    def test_document_frequency_pass(self):
        pages = [{"id": 1, "title": {"raw": "One"}, "link": "https://x/medical-sales-hub/one/",
                  "content": {"raw": "<h2>Closure</h2><p>stapling and sutures for surgeons in theatres</p>"}},
                 {"id": 2, "title": {"raw": "Two"}, "link": "https://x/medical-sales-hub/two/",
                  "content": {"raw": "<h2>Other</h2><p>theatres and surgeons only matter here a lot</p>"}}]
        df, n = BSE.hub_document_frequency(pages)
        self.assertEqual(df["theatres"], 2)
        self.assertEqual(df["stapling"], 1)
        self.assertGreaterEqual(n, 2)


class Records(unittest.TestCase):
    def test_framework_records_carry_lot_titles_and_no_suppliers(self):
        recs = {r["t"]: r for r in BSE.framework_records()}
        mis = recs["Minimally Invasive Surgery, Related Equipment and Accessories"]
        self.assertIn("surgical stapling devices", mis["k"])
        self.assertEqual(mis["c"], "Framework")
        self.assertIn("Wound Closure", recs)
        self.assertIn("Surgical Mesh", recs)
        for r in recs.values():
            self.assertTrue(r["u"].startswith("/medical-sales-hub/"))
            self.assertEqual(set(r), {"t", "u", "k", "c"})
            self.assertLessEqual(len(r["k"]), 400)

    def test_framework_keywords_come_only_from_the_buyers_titles(self):
        # Every keyword is a word of the framework's own name, category or lot
        # titles (or the fixed label): never a supplier name read off a notice.
        with open(os.path.join(HERE, "data", "frameworks.json")) as f:
            fw = json.load(f)["frameworks"]
        by = {}
        for r in BSE.framework_records():
            by.setdefault(r["t"], []).append(set(r["k"].split()))
        for x in fw:
            allowed = set(BSE._kw(x["name"], x.get("category"),
                                  " ".join(str(v) for v in (x.get("lotTitles") or {}).values() if v),
                                  "framework nhs supply chain", limit=10 ** 6).split())
            self.assertTrue(any(ws <= allowed for ws in by[x["name"]]), x["name"])

    def test_tool_records(self):
        tools = {r["t"]: r for r in BSE.tool_records()}
        self.assertEqual(tools["Compare vs Competitors"]["u"], "/medical-sales-hub/med-sales-tools/#view-compare")
        self.assertIn("minimally invasive surgery", tools["Compare vs Competitors"]["k"])

    def test_build_adds_them_and_keeps_supplier_and_drops_desks(self):
        pages = [{"id": 6259, "title": {"raw": "Meril UK"}, "link": "https://x/medical-sales-hub/meril-uk/",
                  "content": {"raw": "<h2>A heading</h2><p>enough words live in this page body today</p>"}},
                 {"id": 1234, "title": {"raw": "Urology"}, "link": "https://x/medical-sales-hub/urology/",
                  "content": {"raw": "<h2>A heading</h2><p>enough words live in this page body today</p>"}}]
        doc = BSE.build(pages)
        kinds = {r.get("c") for r in doc["records"]}
        self.assertTrue({"Framework", "Tool"} <= kinds, kinds)
        self.assertEqual([p["id"] for p in doc["pages"]], [1234])
        self.assertTrue(any(r["t"].startswith("Meril UK") and r["c"] == "Supplier" for r in doc["records"]),
                        "the public supplier record must stay")


@unittest.skipUnless(NODE, "node is not installed")
class Ranking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def page(i, t, u, secs):
            return {"id": i, "t": t, "u": u, "sec": [{"h": h, "a": "", "w": w} for h, w in secs]}
        doc = {
            "pages": [
                page(2798, "Theatres and Surgical", "/medical-sales-hub/theatres-and-surgical/",
                     [("Surgical closure", "closure consumables sutures theatre trial wound")]),
                page(3198, "Frameworks, Tenders, Awards, Drug Tariff and Contracts",
                     "/medical-sales-hub/tender-history/",
                     [("Frameworks - routes to market", "buying frameworks routes")]),
                page(2830, "Colorectal, GI and Endoscopy", "/medical-sales-hub/colorectal-gi-and-endoscopy/",
                     [("Colorectal, GI and Endoscopy", "bowel endoscopy resection")]),
                page(1882, "Build Your Network", "/medical-sales-hub/build-your-network/",
                     [("Build Your Network", "contacts leaders network")]),
                page(3641, "Supply Disruption Tracker", "/medical-sales-hub/supply-disruption-tracker/",
                     [("Supply Disruption Tracker", "recalls shortages supply")]),
                page(2801, "Cardiology and Cardiac Surgery", "/medical-sales-hub/cardiology-and-cardiac-surgery/",
                     [("Cardiology and Cardiac Surgery", "cardiac heart surgeon")]),
                page(2831, "Ophthalmology", "/medical-sales-hub/ophthalmology/",
                     [("Cataract", "cataract lens surgery theatre")]),
            ],
            "records": [{"t": "Johnson & Johnson (Ethicon Sarl)", "u": "/medical-sales-hub/suppliers/#q=J",
                         "k": "johnson ethicon", "c": "Supplier"},
                        {"t": "Meril UK Pvt Ltd", "u": "/medical-sales-hub/suppliers/#q=Meril%20UK%20Pvt%20Ltd",
                         "k": "meril uk pvt ltd", "c": "Supplier"}]
                       + BSE.framework_records() + BSE.tool_records(),
        }
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "idx.json")
        json.dump(doc, open(cls.path, "w"))
        cls.q = ["surgical stapling", "stapler", "staplers", "staples", "sutures", "suture", "wound closure",
                 "hernia mesh", "surgical mesh", "Meril", "Ethicon", "thoracic", "tender"]
        cls.res = rank(cls.path, cls.q)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def titles(self, q):
        return [r["t"] for r in self.res[q]]

    def urls(self, q):
        return [r["u"] for r in self.res[q]]

    def test_surgical_stapling_finds_the_route(self):
        t = self.titles("surgical stapling")
        self.assertIn("Minimally Invasive Surgery, Related Equipment and Accessories", t)
        self.assertIn("Compare vs Competitors", t)
        self.assertIn("/medical-sales-hub/tender-history/", self.urls("surgical stapling"))
        self.assertIn("Theatres and Surgical", t)

    def test_plan_carries_framework_and_compare_steps(self):
        plan = self.res["__plans"]["surgical stapling"]
        self.assertIn("/medical-sales-hub/tender-history/#frameworks", plan)
        self.assertIn("/medical-sales-hub/med-sales-tools/#view-compare", plan)

    def test_stapler_forms_all_find_it(self):
        for q in ("stapler", "staplers", "staples"):
            self.assertIn("Minimally Invasive Surgery, Related Equipment and Accessories", self.titles(q), q)
            self.assertIn("Compare vs Competitors", self.titles(q), q)

    def test_sutures_and_wound_closure(self):
        for q in ("sutures", "suture", "wound closure"):
            self.assertIn("Wound Closure", self.titles(q), q)
            self.assertIn("Theatres and Surgical", self.titles(q), q)
        self.assertEqual(self.titles("wound closure")[0], "Wound Closure")

    def test_mesh(self):
        for q in ("hernia mesh", "surgical mesh"):
            self.assertIn("Surgical Mesh", self.titles(q), q)
            self.assertIn("Compare vs Competitors", self.titles(q), q)

    def test_thoracic_reaches_cardiac_surgery(self):
        self.assertEqual(self.titles("thoracic")[0], "Cardiology and Cardiac Surgery")

    def test_brands_still_lead_with_the_company(self):
        self.assertEqual(self.titles("Meril")[0], "Meril UK Pvt Ltd")
        self.assertIn("Johnson & Johnson (Ethicon Sarl)", self.titles("Ethicon")[:3])

    def test_no_concept_noise(self):
        # Cataract surgery is not minimally invasive surgery or wound closure.
        self.assertNotIn("Ophthalmology", self.titles("surgical stapling"))
        self.assertNotIn("Ophthalmology", self.titles("wound closure"))

    def test_framework_records_are_not_companies_in_the_planner(self):
        # findSupplier must skip Framework/Tool records: "wound closure" is not a company.
        src = open(os.path.join(HERE, "app", "hub-search.js")).read()
        self.assertIn("r.c !== 'Supplier'", src)

    def test_existing_word_rules_hold(self):
        # "tender" must not match "tending" (no -er stripping).
        self.assertEqual(self.res["tender"] and [r for r in self.res["tender"] if r["k"] == "rec" and r["c"] == "Supplier"], [])


@unittest.skipUnless(NODE, "node is not installed")
class ShippedIndex(unittest.TestCase):
    def test_shipped_index_finds_the_route_and_holds_no_desks(self):
        path = os.path.join(HERE, "data", "hub-search-index.json")
        d = json.load(open(path, encoding="utf-8"))
        for p in d["pages"]:
            self.assertFalse(BSE.is_private_desk(p["id"], p["u"]), p["u"])
        res = rank(path, ["surgical stapling", "sutures", "hernia mesh", "Meril"])
        titles = [r["t"] for r in res["surgical stapling"]]
        self.assertIn("Minimally Invasive Surgery, Related Equipment and Accessories", titles)
        self.assertIn("Compare vs Competitors", titles)
        self.assertIn("Wound Closure", [r["t"] for r in res["sutures"]])
        self.assertIn("Surgical Mesh", [r["t"] for r in res["hernia mesh"]])
        for q in [q for q in res if q != "__plans"]:
            for r in res[q]:
                self.assertNotIn("meril-uk/", r["u"].split("#")[0] if r["k"] == "page" else "")
                self.assertNotIn("/medilogik/", r["u"])


if __name__ == "__main__":
    unittest.main()
