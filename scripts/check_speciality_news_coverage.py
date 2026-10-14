#!/usr/bin/env python3
"""Speciality news coverage check. Read-only. Exit 0 clean, 1 findings.

WHY (Lou, 14/10/2026). ENT, haematology, pain and plastics/burns sat with no
news at all for a month and nothing noticed: the builder only ever logs what
it found, never what is missing. Lou: "Add this check to one of the routines
already set up so it doesnt happen again." The weekly-hub-gap-audit night job
runs this and scouts sources for whatever it flags.

Reads the published files in data/speciality-news/ (the rolling month the
pages show) and the SOURCES list in build_speciality_news.py, and reports:

  EMPTY   a speciality page with no item inside MAX_AGE_DAYS
  THIN    a speciality page with fewer than --min items inside MAX_AGE_DAYS
  STALE   a source in SOURCES that contributed no item to any page this month
          (dead feed, a feed that stopped publishing, or one whose items the
          keyword rules never match). Worth a look either way.

    python3 scripts/check_speciality_news_coverage.py
    python3 scripts/check_speciality_news_coverage.py --min 5 --json
"""
import argparse
import datetime
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_speciality_news as b  # noqa: E402

DEFAULT_MIN = 3


def in_window(it, cutoff):
    if not it.get("published"):
        return False
    dt = b.parse_pubdate(it["published"])
    return dt is not None and dt >= cutoff


def check(min_items=DEFAULT_MIN, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=b.MAX_AGE_DAYS)
    rules = b.load_keyword_rules() or {"rules": {}}
    slugs = set(rules["rules"])
    for src in b.SOURCES:
        slugs.update(src["specialities"])

    per_slug = {}
    seen_sources = {}
    for slug in sorted(slugs):
        path = os.path.join(b.OUT_DIR, slug + ".json")
        try:
            with open(path, encoding="utf-8") as fh:
                items = json.load(fh).get("items") or []
        except (OSError, ValueError):
            items = []
        live = [i for i in items if in_window(i, cutoff)]
        per_slug[slug] = len(live)
        for i in live:
            seen_sources[i.get("source")] = seen_sources.get(i.get("source"), 0) + 1

    empty = [s for s, n in per_slug.items() if n == 0]
    thin = [s for s, n in per_slug.items() if 0 < n < min_items]
    stale = [{"id": s["id"], "name": s["name"], "url": s["url"]}
             for s in b.SOURCES if not seen_sources.get(s["name"])]
    return {"checkedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "windowDays": b.MAX_AGE_DAYS,
            "min": min_items, "perSpeciality": per_slug, "empty": empty, "thin": thin,
            "staleSources": stale}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=DEFAULT_MIN)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = check(args.min)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print("Speciality news, last %d days: %d pages" % (r["windowDays"], len(r["perSpeciality"])))
        for s in r["empty"]:
            print("EMPTY  %s" % s)
        for s in r["thin"]:
            print("THIN   %s (%d)" % (s, r["perSpeciality"][s]))
        for s in r["staleSources"]:
            print("STALE  %s  %s" % (s["id"], s["url"]))
        if not (r["empty"] or r["thin"] or r["staleSources"]):
            print("clean")
    return 1 if (r["empty"] or r["thin"] or r["staleSources"]) else 0


if __name__ == "__main__":
    sys.exit(main())
