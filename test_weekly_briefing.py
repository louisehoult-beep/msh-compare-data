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
7. WORTH READING. Unverified and correspondence items never appear; hub news outranks journals; journals
   are capped; an item appears once; the subject count is what the email shows; every safety alert shows
   but only a matching one justifies a send; every alert facet in the data resolves or is a known non-match.

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
    def __init__(self, news=(), awards=(), cal=(), icb=(), alerts=()):
        self.calendar = list(cal)
        self.tenders = []
        self.icb = list(icb)
        self.co_awards, self.co_press, self.co_index = {}, {}, {}
        self.alerts, self.facets = list(alerts), {"dermatology": {"hub": ["dermatology"]}, "renal-medicine": {"hub": ["renal"]}}
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
check("unverified news never appears", wb.build(M, TODAY, Fake(news=[dict(NEWS_IN, verified=False)])) is None)
check("correspondence never appears", wb.build(M, TODAY, Fake(news=[dict(NEWS_IN, title="Correspondence on: x")])) is None)
def _n(i, source, title=None):
    return {"title": title or "Story %d" % i, "link": "https://example.org/%d" % i, "published": "2026-10-23", "source": source}
J = "Journal of Things"
mix = [_n(i, J) for i in range(6)] + [_n(10, "Trade News"), _n(11, "Hub intelligence")]
bm = wb.build(M, TODAY, Fake(news=mix))
got = bm["specialities"][0]["news"]
check("hub first, then trade", got[0]["source"] == "Hub intelligence" and got[1]["source"] == "Trade News", str(got[:2]))
check("journals capped", sum(1 for g in got if g["journal"]) == wb.MAX_JOURNAL, str(len(got)))
check("left-outs are counted and linked", bm["specialities"][0]["hidden"] == 4 and "4 more this week" in wb.render_html(bm))
check("subject counts what shows", "%d changes" % len(got) in wb.subject(bm), wb.subject(bm))
dup = wb.build(M, TODAY, Fake(news=[_n(1, "A", "Same story"), _n(2, "B", "Same  story!")]))
check("same story once", len(dup["specialities"][0]["news"]) == 1)
check("full text suffix stripped", wb._clean_title("A study \u2013 Full Text") == "A study")
AL = {"title": "Alert", "url": "https://www.gov.uk/a", "alertType": "national-patient-safety", "issuedDate": "2026-10-23", "specialisms": ["renal-medicine"]}
check("other speciality alert never justifies a send", wb.build(M, TODAY, Fake(alerts=[AL])) is None)
ba = wb.build(M, TODAY, Fake(news=[NEWS_IN], alerts=[AL]))
check("every alert shows", "www.gov.uk/a" in wb.render_html(ba) and "National Patient Safety Alert" in wb.render_html(ba))
yours = wb.build(M, TODAY, Fake(alerts=[dict(AL, specialisms=["dermatology"])]))
check("own speciality alert sends", yours is not None and yours["changes"] == 1 and "In your specialities" in wb.render_html(yours))
check("instant candidate on the day only", len(wb.instant_candidates(M, datetime.date(2026, 10, 23), Fake(alerts=[dict(AL, specialisms=["dermatology"])]))) == 1
      and not wb.instant_candidates(M, datetime.date(2026, 10, 24), Fake(alerts=[dict(AL, specialisms=["dermatology"])])))
check("my hub link is the real page", wb.MY_HUB.endswith("/medical-sales-hub/my-hub/"))
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

check("no doubled supplier wording", "Supplier: Supplier" not in wb.render_html(wb.build(M, TODAY, Fake(awards=[
    {"title": "A", "url": "https://example.org/a", "date": "2026-10-23", "buyer": "B"}]))))
check("formulary page churn stays out", wb.build(M, TODAY, Fake(news=[NEWS_IN], icb=[dict(ICB, headline="X formulary: page text changed")]))["icb"] == [])

real = wb.Data()
for a in real.alerts:
    for f in a.get("specialisms") or []:
        name = wb.ALERT_FACET_ALIAS.get(f, f)
        check("alert facet known: %s" % f, name in real.facets)
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

# The shadow scorecard: test profiles only, sends nothing, and refuses to write into this public repo.
sys.path.insert(0, os.path.join(HERE, "scripts"))
import personal_alerts_shadow as shadow  # noqa: E402
sc = shadow.score(datetime.date(2026, 10, 26), real)
check("shadow covers every speciality", sc["specialities"] == len(slugs), str(sc["specialities"]))
check("shadow profiles are made up", all(p["key"].startswith(("spec-", "multi-", "co-")) for p in shadow.profiles(real, TODAY)))
check("shadow writes the scorecard", "Nothing was sent" in shadow.to_md(sc))
check("shadow refuses the repo", shadow.main(["--out", os.path.join(HERE, "out", "x")]) == 2)
sh = open(os.path.join(HERE, "scripts", "personal_alerts_shadow.py")).read()
check("shadow has no sending path", not re.search(r"mailerlite|smtplib|push_alerts|pywebpush", sh.replace("MailerLite", ""), re.I))

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("weekly briefing: all checks hold")
