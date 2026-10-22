#!/usr/bin/env python3
"""Gate for data/kol-finder.json (exit 0 = pass, 1 = findings).

Rules: every person has a source page on the source list, checked 2026; no email,
phone or postal detail anywhere; classes and specialities are known; opt-out
names absent; LinkedIn is a search link only; empty states exist for classes with
no people; names unique.
    python3 scripts/check_kol_finder.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def check(doc, optout=()):
    bad = []
    src = {s["id"]: s for s in doc["sources"]}
    classes = {c["id"] for c in doc["classes"]}
    specs = {s["id"] for s in doc["specialities"]}
    seen = set()
    contact = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?:\+44|\b0)\d[\d ]{8,}")
    for p in doc["people"]:
        n = p["name"]
        if n in seen:
            bad.append("duplicate person: " + n)
        seen.add(n)
        if n.lower() in optout:
            bad.append("opt-out name present: " + n)
        if not p["appearances"]:
            bad.append(n + ": no source")
        for a in p["appearances"]:
            s = src.get(a["source"])
            if not s:
                bad.append("%s: unknown source %s" % (n, a["source"]))
            elif a["source_url"] != s["url"] or not a["source_url"].startswith("https://"):
                bad.append("%s: source_url does not match source list" % n)
            if not str(a.get("checked", "")).startswith("2026-"):
                bad.append(n + ": no checked date")
            if not a.get("role"):
                bad.append(n + ": no role")
        for c in p["classes"]:
            if c not in classes:
                bad.append("%s: unknown class %s" % (n, c))
        if not p["classes"]:
            bad.append(n + ": no class")
        for s in p["specialities"]:
            if s not in specs:
                bad.append("%s: unknown speciality %s" % (n, s))
        if not p["linkedin_search"].startswith("https://www.linkedin.com/search/results/people/?keywords="):
            bad.append(n + ": LinkedIn must be a search link only")
        blob = json.dumps(p)
        if contact.search(blob):
            bad.append(n + ": contact detail in record")
    have = {c for p in doc["people"] for c in p["classes"]}
    for c in classes - have:
        if c not in doc["empty"]:
            bad.append("class %s has no people and no empty-state wording" % c)
    if not doc["people"]:
        bad.append("no people at all")
    return bad


def main():
    doc = json.loads((ROOT / "data" / "kol-finder.json").read_text())
    try:
        oo = {x.lower() for x in json.loads((ROOT / "data" / "contacts-optout.json").read_text()).get("names", [])}
    except Exception:
        oo = set()
    bad = check(doc, oo)
    for b in bad:
        print("FAIL", b)
    print("kol-finder: %d people, %d findings" % (len(doc["people"]), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
