#!/usr/bin/env python3
"""Gates Tracker: when did the owner last change each health tech gate page?

WHAT THIS IS (20/10/2026, Hub health tech intelligence gap, build plan "Next 30
days", Gates Tracker). A health tech product meets a run of gates (MHRA
registration and software/AI rules, clinical safety standards, DTAC, the AI
Commission response, AI Airlock). The gates change monthly, so the Hub's value is
a DATED, SOURCE-LINKED record of when each owner page last changed and what the
owner said changed. This script reads only the owners' own pages:

  GOV.UK pages      the GOV.UK content API (https://www.gov.uk/api/content/<path>),
                    open, no key: public_updated_at and the page's own
                    change_history notes, verbatim.
  NHS England       digital.nhs.uk pages carry "Last edited: <date>" in the page
  Digital pages     footer; that line is read, nothing else is inferred.

It never summarises or interprets a change: `latestChange` is the owner's own note.
A page whose date moved since the last run is flagged `changedSinceLastRun`, which
is the change feed. A page that cannot be read keeps its last good reading and is
marked `status: "unreachable"`; nothing is invented.

USAGE
    python3 scripts/refresh_gates_watch.py
    python3 scripts/refresh_gates_watch.py --dry-run
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.request

OUT_PATH = "data/gates-watch.json"
UA = {"User-Agent": "Elevate-and-Thrive-Hub/1.0 (Medical Sales Intelligence Hub; contact@elevateandthrive.uk)"}

# (id, gate, owner, kind, path or url). Each was opened on 20/10/2026 and is the
# owner's own page for that gate. Add a page here, never in the data file.
WATCH = [
    ("mhra-registration", "Regulation", "Medicines and Healthcare products Regulatory Agency (MHRA)",
     "govuk", "/guidance/register-medical-devices-to-place-on-the-market"),
    ("mhra-regulating", "Regulation", "Medicines and Healthcare products Regulatory Agency (MHRA)",
     "govuk", "/guidance/regulating-medical-devices-in-the-uk"),
    ("mhra-software-ai", "Regulation", "Medicines and Healthcare products Regulatory Agency (MHRA)",
     "govuk", "/government/publications/software-and-artificial-intelligence-ai-as-a-medical-device"),
    ("mhra-avt", "Regulation", "Medicines and Healthcare products Regulatory Agency (MHRA)",
     "govuk", "/government/publications/ambient-voice-technology-enabled-products"),
    ("mhra-gmlp", "Regulation", "Medicines and Healthcare products Regulatory Agency (MHRA)",
     "govuk", "/government/publications/good-machine-learning-practice-for-medical-device-development-guiding-principles"),
    ("ai-airlock", "Regulation", "Medicines and Healthcare products Regulatory Agency (MHRA)",
     "govuk", "/government/collections/ai-airlock-a-regulatory-sandbox-for-ai-enabled-medical-devices"),
    ("ai-commission-response", "Regulation", "Department of Health and Social Care and the MHRA",
     "govuk", "/government/news/government-backs-recommendations-of-nhs-doctors-led-ai-commission"),
    ("ai-commission-recommendations", "Regulation", "National Commission into the Regulation of AI in Healthcare",
     "govuk", "/government/publications/national-commission-into-the-regulation-of-ai-in-healthcare-recommendations-for-a-future-regulatory-framework"),
    ("dtac", "Assurance", "NHS England",
     "nhsd", "https://digital.nhs.uk/services/digital-technology-assessment-criteria-dtac"),
    ("clinical-safety", "Clinical safety", "NHS England",
     "nhsd", "https://digital.nhs.uk/services/clinical-safety/clinical-risk-management-standards"),
]

RULE = (
    "Each row is one owner page for a health tech gate. lastUpdated is the owner's own "
    "date: GOV.UK's public_updated_at from its content API, or the 'Last edited' line "
    "on an NHS England Digital page. latestChange is the owner's own change note, "
    "verbatim, where the owner publishes one. changedSinceLastRun is true when that "
    "date moved since the previous run. Nothing is summarised or interpreted.")


def get(url, timeout=30, tries=2):
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == tries:
                raise
            time.sleep(4)


def read_govuk(path, fetch=get):
    d = json.loads(fetch("https://www.gov.uk/api/content" + path))
    hist = sorted(((d.get("details") or {}).get("change_history") or []),
                  key=lambda c: c.get("public_timestamp") or "", reverse=True)
    return {
        "title": d.get("title"),
        "url": "https://www.gov.uk" + path,
        "lastUpdated": (d.get("public_updated_at") or "")[:10] or None,
        "latestChange": (hist[0].get("note") or "").strip() if hist else None,
        "recentChanges": [{"date": (c.get("public_timestamp") or "")[:10],
                           "note": (c.get("note") or "").strip()} for c in hist[:5]],
    }


MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                      "august", "september", "october", "november", "december"], 1)}


def read_nhsd(url, fetch=get):
    page = fetch(url)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(
        r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S))))
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    m = re.search(r"Last edited:\s*(\d{1,2}) (\w+) (\d{4})", t)
    last = None
    if m and m.group(2).lower() in MONTHS:
        last = dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    return {"title": html.unescape(title.group(1)).split(" - ")[0].strip() if title else None,
            "url": url, "lastUpdated": last, "latestChange": None, "recentChanges": []}


def build(previous, today, fetch=get):
    prev = {p["id"]: p for p in (previous or {}).get("pages") or []}
    pages = []
    for pid, gate, owner, kind, where in WATCH:
        old = prev.get(pid) or {}
        try:
            got = read_govuk(where, fetch) if kind == "govuk" else read_nhsd(where, fetch)
            row = {"id": pid, "gate": gate, "owner": owner, "status": "ok", "checkedOn": today, **got}
            if not row["lastUpdated"]:
                row["status"] = "no date found"
        except Exception as exc:
            row = dict(old) if old else {"id": pid, "gate": gate, "owner": owner,
                                         "url": where if kind == "nhsd" else "https://www.gov.uk" + where,
                                         "title": None, "lastUpdated": None, "latestChange": None,
                                         "recentChanges": []}
            row.update({"status": "unreachable", "error": str(exc)[:160], "checkedOn": today})
        row["changedSinceLastRun"] = bool(old.get("lastUpdated") and row.get("lastUpdated")
                                          and row["lastUpdated"] != old["lastUpdated"])
        row["previousLastUpdated"] = old.get("lastUpdated") if row["changedSinceLastRun"] else None
        pages.append(row)
    pages.sort(key=lambda p: p.get("lastUpdated") or "", reverse=True)
    return {
        "generated": today,
        "dataAsOf": dt.date.fromisoformat(today).strftime("%d/%m/%Y"),
        "source": "GOV.UK content API (Open Government Licence v3) and NHS England Digital pages",
        "rule": RULE,
        "counts": {"pages": len(pages),
                   "ok": sum(1 for p in pages if p["status"] == "ok"),
                   "changedSinceLastRun": sum(1 for p in pages if p["changedSinceLastRun"])},
        "pages": pages,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    old = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as fh:
            old = json.load(fh)
    doc = build(old, dt.date.today().isoformat())
    for p in doc["pages"]:
        print("  %-30s %-11s %s%s" % (p["id"], p.get("lastUpdated"), p["status"],
                                      "  CHANGED" if p["changedSinceLastRun"] else ""))
    if args.dry_run:
        return 0
    if old and old.get("_notice"):
        doc = {"_notice": old["_notice"], **doc}
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote %s" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
