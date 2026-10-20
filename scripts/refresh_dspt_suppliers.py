#!/usr/bin/env python3
"""Data Security and Protection Toolkit (DSPT) status for the Digital suppliers.

Source: the DSPT Organisation Search CSV export, NHS England.
Reuse: the site's Terms and conditions (checked 20/10/2026) say Crown copyright
material "may be reproduced free of charge in any format or medium, provided it is
reproduced accurately and not used in a misleading context", with the source
identified. The script refuses to run if that wording is no longer on the page.

Matching is EXACT on the normalised name only (lower case, "&" -> "and",
punctuation removed, whitespace collapsed). No fuzzy matching: a wrong match would
put another company's assurance status on a supplier. Anyone not matched is listed
as unmatched, never guessed.

  python3 scripts/refresh_dspt_suppliers.py
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.dsptoolkit.nhs.uk"
TERMS_URL = BASE + "/Home/TermsAndConditions"
SEARCH_URL = BASE + "/OrganisationSearch"
EXPORT_URL = BASE + "/OrganisationSearch/ExportSearchResults?searchValue="
ROBOTS_URL = BASE + "/robots.txt"
REUSE_PHRASE = "may be reproduced free of charge in any format or medium"
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
OUT = os.path.join(ROOT, "data", "dspt-supplier-check.json")
UA = "Mozilla/5.0 (compatible; MedicalSalesHub-data/1.0)"


def norm(name):
    t = name.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def fetch(url, timeout=60):
    last = None
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8-sig", errors="replace")
        except Exception as e:  # one retry, then record the gap
            last = e
            time.sleep(2)
    raise RuntimeError("fetch failed %s: %s" % (url, last))


def terms_permit_reuse(html):
    text = re.sub(r"<[^>]+>", " ", html)
    return REUSE_PHRASE in " ".join(text.split())


def robots_allows_export(robots):
    """True unless a Disallow line covers /OrganisationSearch (robots lists Allow rules only)."""
    for line in robots.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path and "/OrganisationSearch".startswith(path):
                return False
    return True


def digital_suppliers(seed):
    return [s for s in seed["suppliers"]
            if any("Digital" in l for l in s.get("specialities", []))]


def parse_export(csv_text):
    rows = list(csv.reader(io.StringIO(csv_text)))
    index = {}
    for r in rows[1:]:
        if len(r) < 5:
            continue
        rec = {"odsCode": r[0].strip(), "dsptName": r[1].strip(),
               "dsptStatus": r[2].strip(), "statusDate": r[3].strip(),
               "primarySector": r[4].strip()}
        index.setdefault(norm(rec["dsptName"]), []).append(rec)
    return index


def build(suppliers, index, checked):
    matched, unmatched = [], []
    for s in suppliers:
        hits = index.get(norm(s["name"]), [])
        if not hits:
            unmatched.append(s["name"])
            continue
        entry = {"name": s["name"], "matches": hits, "sourceUrl": SEARCH_URL}
        if len(hits) == 1:
            entry.update({k: hits[0][k] for k in ("odsCode", "dsptStatus", "statusDate")})
        else:
            entry["ambiguous"] = True  # several DSPT records share the name: no single status claimed
        matched.append(entry)
    return {
        "defined": True,
        "checked": checked,
        "source": "NHS England Data Security and Protection Toolkit, Organisation Search CSV export",
        "sourceUrl": SEARCH_URL,
        "reuseBasis": ("Terms and conditions at %s: Crown copyright material may be reproduced "
                       "free of charge in any format or medium, provided it is reproduced "
                       "accurately and not used in a misleading context; source identified." % TERMS_URL),
        "note": ("Status is as published by DSPT on the checked date, for the organisation "
                 "whose DSPT name exactly matches the supplier name. Identity beyond the "
                 "name match is not verified, and this is not an endorsement."),
        "suppliers": matched,
        "unmatched": unmatched,
    }


def main():
    today = date.today().isoformat()
    if not terms_permit_reuse(fetch(TERMS_URL, 30)):
        print("Reuse wording not found on the DSPT terms page; not scraping.")
        return 1
    if not robots_allows_export(fetch(ROBOTS_URL, 30)):
        print("robots.txt disallows the search; not scraping.")
        return 1
    index = parse_export(fetch(EXPORT_URL, 180))
    if len(index) < 1000:
        print("Export looks truncated (%d names); not writing." % len(index))
        return 1
    with open(SEED, encoding="utf-8") as f:
        seed = json.load(f)
    out = build(digital_suppliers(seed), index, today)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("matched %d, unmatched %d" % (len(out["suppliers"]), len(out["unmatched"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
