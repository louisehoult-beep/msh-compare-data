#!/usr/bin/env python3
"""Personal alerts, shadow run: judge the Monday briefing and phone triggers without telling anyone.

Added 04/11/2026 (Lou: get it working and improving in the background, do not advertise it yet).
SENDS NOTHING and reads no member data. It uses made-up profiles: one per speciality, plus a few
with several specialities and a company. Output goes to a folder OUTSIDE this public repo.

  python3 scripts/personal_alerts_shadow.py --today 2026-11-02 --out <folder> [--check-links 20]

Writes <folder>/<today>/scorecard.md, scorecard.json and sample briefings, and appends one line to
<folder>/history.jsonl. Exit 0 whatever the score: a poor score is the finding, not a failure.
"""
import argparse
import collections
import datetime
import json
import os
import statistics
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly_briefing as wb  # noqa: E402

STALE_DAYS = 14
UA = "Mozilla/5.0 (compatible; HubBriefingLinkCheck/1.0)"
MULTI = [
    ["dermatology", "tissue-viability-and-wound-care"],
    ["cardiology-and-cardiac-surgery", "vascular-surgery-and-pad"],
    ["primary-care-and-general-practice", "diabetes-and-endocrinology", "respiratory"],
]


def speciality_slugs():
    cat = wb._load("hub/my-hub-catalogue.json", {})
    return [i["id"] for i in cat.get("items", []) if i.get("group") == "specialities"]


def active_companies(data, today, n=3):
    """The companies with most activity in the window, so company items get exercised every run."""
    scored = []
    for cid in sorted(data.co_index):
        c = wb.company_section(data, cid, today)
        if c and c["items"]:
            scored.append((-len(c["items"]), cid))
    return [cid for _, cid in sorted(scored)[:n]]


def profiles(data, today):
    out = [{"key": "spec-" + s, "specialities": [s], "companies": []} for s in speciality_slugs()]
    out += [{"key": "multi-%d" % i, "specialities": m, "companies": []} for i, m in enumerate(MULTI, 1)]
    out += [{"key": "co-" + c, "specialities": [], "companies": [c]} for c in active_companies(data, today)]
    return out


def latest_news(data, slug):
    days = [d for d in (wb._day(n.get("published")) for n in data.news(slug)) if d]
    return max(days) if days else None


def check_links(urls, limit):
    """Status of a sample of links. A refusal or a timeout is unverified, never dead."""
    res = {"ok": 0, "dead": [], "unverified": 0, "checked": 0}
    for u in sorted(set(urls))[:limit]:
        res["checked"] += 1
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=8) as r:
                r.read(1)
            res["ok"] += 1
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                res["dead"].append(u)
            else:
                res["unverified"] += 1
        except Exception:  # noqa: BLE001  network trouble says nothing about the link
            res["unverified"] += 1
    return res


def score(today, data, link_limit=0):
    ps = profiles(data, today)
    built = {}
    for p in ps:
        b = wb.build(p, today, data)
        if b:
            built[p["key"]] = b
    single = [p for p in ps if p["key"].startswith("spec-")]
    sent_single = [p for p in single if p["key"] in built]
    counts = [built[p["key"]]["changes"] for p in sent_single]

    journal_only, no_news, sources, urls = [], [], collections.Counter(), []
    hidden = shown = 0
    for p in sent_single:
        b = built[p["key"]]
        s = b["specialities"][0]
        hidden += s["hidden"]
        shown += b["changes"]
        for n in s["news"]:
            sources[n["source"]] += 1
        if s["news"] and all(n["journal"] for n in s["news"]) and not s["awards"] and not s["safety"]:
            journal_only.append(s["slug"])
        if not s["news"]:
            no_news.append(s["slug"])
    for b in built.values():
        urls += [i["url"] for s in b["specialities"] for k in ("news", "awards", "safety") for i in s[k]]
        urls += [i["url"] for c in b["companies"] for i in c["items"]]

    silent = [p["specialities"][0] for p in single if p["key"] not in built]
    stale = []
    for s in speciality_slugs():
        d = latest_news(data, s)
        if d is None or (today - d).days > STALE_DAYS:
            stale.append({"speciality": s, "latestNews": d.isoformat() if d else None})

    week = [today - datetime.timedelta(days=i) for i in range(7)]
    pushes = collections.Counter()
    kinds = collections.Counter()
    for p in ps:
        for day in week:
            c = wb.instant_candidates(p, day, data)
            if c:
                pushes[p["key"]] += 1
                kinds.update(i["kind"] for i in c)
    alerts = [a for a in data.alerts if wb._in_window(a.get("issuedDate"), today)]
    no_match = [a["title"][:80] for a in alerts if not wb.alert_specialities(a, data.facets)]

    return {
        "today": today.isoformat(),
        "profiles": len(ps),
        "specialities": len(single),
        "specialitiesWithBriefing": len(sent_single),
        "silentSpecialities": silent,
        "medianItems": statistics.median(counts) if counts else 0,
        "maxItems": max(counts) if counts else 0,
        "itemsShown": shown,
        "itemsLeftOut": hidden,
        "journalOnly": journal_only,
        "noNewsThisWeek": no_news,
        "staleNewsFeeds": stale,
        "topSources": sources.most_common(12),
        "safetyAlertsInWindow": len(alerts),
        "safetyAlertsNoSpecialityMatch": no_match,
        "phoneTriggers": {"profilesWithAny": len(pushes), "byKind": dict(kinds),
                          "maxDaysForOneProfile": max(pushes.values()) if pushes else 0},
        "links": check_links(urls, link_limit) if link_limit else None,
        "_built": built,
    }


def verdicts(s):
    """The things to fix next, worst first. Plain findings, no thresholds loosened to pass."""
    out = []
    n = s["specialities"] or 1
    if s["links"] and s["links"]["dead"]:
        out.append("%d dead link(s) in the sample" % len(s["links"]["dead"]))
    if s["staleNewsFeeds"]:
        out.append("%d specialities have no news for over %d days: fix the sourcing, not the rule" % (len(s["staleNewsFeeds"]), STALE_DAYS))
    if s["journalOnly"]:
        out.append("%d specialities would get journal papers and nothing else" % len(s["journalOnly"]))
    if s["silentSpecialities"]:
        out.append("%d specialities get no email this week" % len(s["silentSpecialities"]))
    if s["itemsLeftOut"] > s["itemsShown"]:
        out.append("More items left out (%d) than shown (%d): ranking decides most of the email" % (s["itemsLeftOut"], s["itemsShown"]))
    if s["safetyAlertsNoSpecialityMatch"]:
        out.append("%d safety alert(s) match no speciality" % len(s["safetyAlertsNoSpecialityMatch"]))
    if s["specialitiesWithBriefing"] / n < 0.5:
        out.append("Under half of specialities have a briefing")
    return out


def to_md(s):
    v = verdicts(s)
    lines = ["# Personal alerts shadow scorecard, week to %s" % s["today"], "",
             "Test profiles only. Nothing was sent. Not advertised to members.", "",
             "| Measure | This week |", "|---|---|",
             "| Specialities with a briefing | %d of %d |" % (s["specialitiesWithBriefing"], s["specialities"]),
             "| Items per briefing, median and most | %s and %d |" % (s["medianItems"], s["maxItems"]),
             "| Items shown, and left out by ranking | %d and %d |" % (s["itemsShown"], s["itemsLeftOut"]),
             "| Journal-only briefings | %d |" % len(s["journalOnly"]),
             "| News feeds quiet for over %d days | %d |" % (STALE_DAYS, len(s["staleNewsFeeds"])),
             "| Safety alerts in the week | %d |" % s["safetyAlertsInWindow"],
             "| Test profiles a phone alert would have reached | %d of %d |" % (s["phoneTriggers"]["profilesWithAny"], s["profiles"]),
             ]
    if s["links"]:
        lines.append("| Links sampled: fine, dead, could not tell | %d, %d, %d |" % (s["links"]["ok"], len(s["links"]["dead"]), s["links"]["unverified"]))
    lines += ["", "## Fix next", ""] + (["%d. %s" % (i, x) for i, x in enumerate(v, 1)] or ["Nothing flagged this week."])
    for title, rows in (("Journal only", s["journalOnly"]), ("No email this week", s["silentSpecialities"]),
                        ("Quiet news feeds", ["%s (latest %s)" % (x["speciality"], x["latestNews"]) for x in s["staleNewsFeeds"]]),
                        ("Dead links", (s["links"] or {}).get("dead", []))):
        if rows:
            lines += ["", "## " + title, ""] + ["* " + str(r) for r in rows]
    return "\n".join(lines) + "\n"


def write(s, out):
    folder = os.path.join(out, s["today"])
    os.makedirs(folder, exist_ok=True)
    built = s.pop("_built")
    want = ["multi-1", "multi-3"] + [k for k in sorted(built) if k.startswith("co-")][:1]
    for k in want:
        if k in built:
            with open(os.path.join(folder, "sample-%s.html" % k), "w", encoding="utf-8") as f:
                f.write(wb.render_html(built[k]))
    with open(os.path.join(folder, "scorecard.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1)
    with open(os.path.join(folder, "scorecard.md"), "w", encoding="utf-8") as f:
        f.write(to_md(s))
    line = {k: s[k] for k in ("today", "specialitiesWithBriefing", "medianItems", "itemsShown", "itemsLeftOut")}
    line.update(journalOnly=len(s["journalOnly"]), staleFeeds=len(s["staleNewsFeeds"]), fixNext=verdicts(s))
    hist = os.path.join(out, "history.jsonl")
    old = open(hist, encoding="utf-8").read().splitlines() if os.path.exists(hist) else []
    old = [x for x in old if json.loads(x).get("today") != s["today"]]
    with open(hist, "w", encoding="utf-8") as f:
        f.write("\n".join(old + [json.dumps(line)]) + "\n")
    return folder


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--out", required=True)
    ap.add_argument("--check-links", type=int, default=0)
    a = ap.parse_args(argv)
    repo = os.path.realpath(wb.ROOT)
    if os.path.realpath(a.out).startswith(repo + os.sep):
        print("Refusing: the output folder is inside the public repo")
        return 2
    s = score(datetime.date.fromisoformat(a.today), wb.Data(), a.check_links)
    print(to_md(s))
    print("Written to", write(s, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
