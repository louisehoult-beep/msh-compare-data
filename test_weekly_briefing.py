#!/usr/bin/env python3
"""Weekly briefing (scripts/weekly_briefing.py). Offline, stdlib only, sends nothing.

1. SKIPPED WHEN THIN. No change item (news, awards, safety, company activity) means build() is None,
   even if dates ahead, tenders and Integrated Care Board events exist.
2. SOURCED. Every link in a built briefing is https and appears in the stored data it came from;
   items outside the 7 day window never appear.
3. ONE GROUP PER MEMBER. plan() puts each member in exactly one speciality-set group; skipped members are in none.
4. CONTRAST. Header band is navy with light text; body text is ink on white. No retired colours.
5. NO FREE TRIAL wording, and the script never imports a network or mail module.
6. Real data builds without error for every speciality in the catalogue.

  python3 test_weekly_briefing.py     exit 0 = holds
"""
import datetime
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "scripts", "weekly_briefing.py")
spec = importlib.util.spec_from_file_location("wb", SRC)
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)
fails = []
TODAY = datetime.date(2026, 10, 26)


def check(name, ok, detail=""):
    if not ok:
        fails.append("%s %s" % (name, detail))


class Fake(wb.Data):
    def __init__(self, news=(), awards=(), cal=(), icb=()):
        self.calendar = list(cal)
        self.tenders = []
        self.icb = list(icb)
        self.co_awards, self.co_press, self.co_index = {}, {}, {}
        self._news = {"dermatology": list(news)}
        self._panel = {"dermatology": {"awards": list(awards), "mhraDsu": {"updates": []}}}


NEWS_IN = {"title": "In", "link": "https://example.org/in", "published": "2026-10-23", "source": "S"}
NEWS_OLD = {"title": "Old", "link": "https://example.org/old", "published": "2026-10-10", "source": "S"}
CAL = {"type": "event", "title": "Conf", "date": "2026-11-02", "specialities": ["dermatology"], "source": "https://example.org/c"}
ICB = {"date": "2026-10-24", "headline": "H", "sources": ["https://example.org/i"]}
M = {"key": "m1", "specialities": ["dermatology"], "companies": []}

check("thin week is skipped", wb.build(M, TODAY, Fake(news=[NEWS_OLD], cal=[CAL], icb=[ICB])) is None)
b = wb.build(M, TODAY, Fake(news=[NEWS_IN, NEWS_OLD], cal=[CAL], icb=[ICB]))
check("change builds", b is not None and b["changes"] == 1, repr(b and b["changes"]))
h = wb.render_html(b)
check("window respected", "example.org/old" not in h and "example.org/in" in h)
check("dates ahead ride along", "example.org/c" in h and "example.org/i" in h)
links = re.findall(r'href="([^"]+)"', h)
check("all links https", all(l.startswith("https://") for l in links), str(links))
check("unverified news is labelled", "not yet checked at source" in wb.render_html(
    wb.build(M, TODAY, Fake(news=[dict(NEWS_IN, verified=False)]))))
check("navy header, light text", "background:#0B1C33" in h and "#F5F1E8" in h and "#E0BE8E" in h)
check("ink on white body", "color:#1D2733" in h and "background:#FFFFFF" in h)
check("no retired colours", not re.search(r"cream|taupe|aubergine|clay", h, re.I))
check("no free trial", not re.search(r"free (trial|week)", h + open(SRC).read(), re.I))
src = open(SRC).read()
check("no network or mail imports", not re.search(r"^\s*(import|from)\s+(urllib|requests|smtplib|http)", src, re.M))
check("first use spelled out", "Medicines and Healthcare products Regulatory Agency (MHRA)" in wb.render_html(
    dict(b, specialities=[dict(b["specialities"][0], safety=[{"title": "T", "url": "https://x.org/t", "date": "2026-10-23"}])])))

p = wb.plan([M, {"key": "m2", "specialities": ["dermatology"], "companies": []},
             {"key": "m3", "specialities": [], "companies": []}], TODAY, Fake(news=[NEWS_IN]))
check("one group per member", p["groups"] == {"Hub briefing - dermatology": ["m1", "m2"]} and p["skipped"] == ["m3"], str(p))

real = wb.Data()
cat = json.load(open(os.path.join(HERE, "hub", "my-hub-catalogue.json")))
slugs = [i["id"] for i in cat["items"] if i.get("group") == "specialities"]
for d in range(0, 28, 7):
    day = datetime.date(2026, 10, 22) - datetime.timedelta(days=d)
    for sl in slugs:
        try:
            r = wb.build({"key": "x", "specialities": [sl], "companies": []}, day, real)
            if r:
                wb.render_html(r)
                wb.subject(r)
        except Exception as e:  # noqa: BLE001
            fails.append("real data %s %s: %r" % (sl, day, e))

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("weekly briefing: all checks hold")
