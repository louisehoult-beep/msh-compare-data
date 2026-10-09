#!/usr/bin/env python3
"""MHRA Drug Safety Updates, tagged to Hub speciality panels.

WHY THIS IS A SEPARATE FILE FROM data/mhra-alerts.json
-------------------------------------------------------
data/mhra-alerts.json (scripts/refresh_mhra_alerts.py) is the MHRA Regulatory
Desk's DEVICE feed: DSI- and NatPSA-numbered alerts only, and it excludes Drug
Safety Updates by rule. Speciality panels serve every speciality, and for a
medicines-facing rep the monthly Drug Safety Update is the MHRA publication
that actually changes prescribing conversations (isotretinoin, topical steroid
withdrawal, emollient fire risk in dermatology alone). Widening mhra-alerts.json
would break the Regulatory Desk's stated scope and its single-writer rule, so
Drug Safety Updates get their own file, data/mhra-dsu.json, and their own
workflow, .github/workflows/mhra-dsu.yml.

THE SOURCE (public, no key)
---------------------------
GOV.UK search API, the same host refresh_mhra_alerts.py already reads:
    https://www.gov.uk/api/search.json
        ?filter_content_store_document_type=drug_safety_update
        &order=-public_timestamp&count=100&start=<n>
        &fields=title,link,description,public_timestamp,first_published_at,therapeutic_area
`therapeutic_area` is GOV.UK's own medical specialty facet on the Drug Safety
Update finder (https://www.gov.uk/drug-safety-update). Its labels come from the
finder's content item: https://www.gov.uk/api/content/drug-safety-update
(details.facets). Probed 29/09/2026: 867 updates, 40 facet values, and the
dermatology filter returns 87, matching the finder page.

The whole archive is re-read every run (nine API pages), so the file is a pure
function of GOV.UK's index plus the mapping table: no merge state to go stale,
and a withdrawn update disappears rather than lingering.

SPECIALITY MAPPING, ONE PLACE, NEVER GUESSED
--------------------------------------------
config/mhra-dsu-speciality-map.json maps each GOV.UK facet to zero or more Hub
panel slugs (data/speciality-panels/<slug>.json). A facet mapped to nothing
carries its reason there. A facet GOV.UK adds that is not in the table is
published under `unmappedFacets` as "not in mapping table" and contributes no
speciality; it is never matched by name. verify.py re-derives every row's
specialities from the same table, so the file and the table cannot drift.

USAGE
    python3 scripts/refresh_mhra_dsu.py              # fetch and write
    python3 scripts/refresh_mhra_dsu.py --dry-run    # fetch and report only
Then, as for every data file:
    python3 scripts/stamp_notice.py && python3 verify.py
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OUT_PATH = "data/mhra-dsu.json"
MAP_PATH = "config/mhra-dsu-speciality-map.json"
PANELS_DIR = "data/speciality-panels"

SEARCH_API = "https://www.gov.uk/api/search.json"
FINDER_API = "https://www.gov.uk/api/content/drug-safety-update"
FINDER_URL = "https://www.gov.uk/drug-safety-update"
URL_PREFIX = "https://www.gov.uk/drug-safety-update/"
FIELDS = "title,link,description,public_timestamp,first_published_at,therapeutic_area"
PAGE = 100
PAGE_SLEEP = 0.3

UA = {"User-Agent": "MedicalSalesHub/1.0 (+https://elevateandthrive.uk; speciality panels)",
      "Accept": "application/json"}

# The monthly "Letters and medicine recalls sent to healthcare professionals in
# <month>" item is a digest of other communications, not a safety update about
# one medicine. Flagged (not dropped) so a panel can choose to leave it out.
ROUNDUP_RE = re.compile(r"^\s*letters(?:,)? (?:and )?(?:drug alerts and )?medicine recalls sent",
                        re.I)


def get(url, timeout=60, retries=3):
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < retries:
                attempt += 1
                wait = int(exc.headers.get("Retry-After") or 20)
                time.sleep(min(wait, 120) + 1)
                continue
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(3 * attempt)
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(3 * attempt)


def panel_slugs(panels_dir=PANELS_DIR):
    return sorted(fn[:-5] for fn in os.listdir(panels_dir) if fn.endswith(".json"))


def load_map(path=MAP_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["facets"]


def validate_map(table, slugs):
    """Every target in the table must be a real panel. Returns a list of errors."""
    errs = []
    known = set(slugs)
    for facet, entry in table.items():
        hub = entry.get("hub")
        if not isinstance(hub, list):
            errs.append("%s: 'hub' must be a list" % facet)
            continue
        for s in hub:
            if s not in known:
                errs.append("%s -> %s: no data/speciality-panels/%s.json" % (facet, s, s))
        if not hub and not entry.get("unmappedReason"):
            errs.append("%s: mapped to nothing but carries no unmappedReason" % facet)
    return errs


def map_facets(facets, table):
    """(hub slugs in first-seen order, facets that contributed nothing)."""
    out, unmapped = [], []
    for f in facets or []:
        entry = table.get(f)
        hub = (entry or {}).get("hub") or []
        if not hub:
            unmapped.append(f)
        for s in hub:
            if s not in out:
                out.append(s)
    return out, unmapped


def _day(ts):
    return (ts or "")[:10]


def row_from(result, table):
    link = result.get("link") or ""
    facets = sorted(set(result.get("therapeutic_area") or []))
    hub, _ = map_facets(facets, table)
    title = (result.get("title") or "").strip()
    published = _day(result.get("first_published_at")) or _day(result.get("public_timestamp"))
    return {
        "title": title,
        "url": "https://www.gov.uk" + link,
        "published": published,
        "updated": _day(result.get("public_timestamp")) or published,
        "summary": re.sub(r"\s+", " ", (result.get("description") or "")).strip(),
        "therapeuticAreas": facets,
        "specialities": sorted(hub),
        "roundup": bool(ROUNDUP_RE.match(title)),
    }


def assemble(results, table, slugs, live_labels, api_total, today):
    rows = {}
    for r in results:
        row = row_from(r, table)
        if not row["url"].startswith(URL_PREFIX):
            continue
        rows[row["url"]] = row
    ordered = sorted(rows.values(), key=lambda r: (r["published"], r["url"]), reverse=True)

    by_spec = {s: 0 for s in slugs}
    by_facet = {}
    for row in ordered:
        for s in row["specialities"]:
            by_spec[s] = by_spec.get(s, 0) + 1
        for f in row["therapeuticAreas"]:
            by_facet[f] = by_facet.get(f, 0) + 1

    labels = {f: (table.get(f) or {}).get("label") for f in table}
    labels.update({k: v for k, v in (live_labels or {}).items() if v})

    unmapped = []
    for f in sorted(set(by_facet) | set(live_labels or {})):
        entry = table.get(f)
        if entry and entry.get("hub"):
            continue
        unmapped.append({
            "facet": f,
            "label": labels.get(f),
            "updates": by_facet.get(f, 0),
            "reason": (entry or {}).get("unmappedReason") or "not in mapping table",
        })

    mapped_targets = {s for e in table.values() for s in (e.get("hub") or [])}
    no_facet = [s for s in slugs if s not in mapped_targets]

    return {
        "dataAsOf": today.isoformat(),
        "source": "MHRA Drug Safety Update, GOV.UK search API, Open Government Licence v3",
        "sourcePage": FINDER_URL,
        "scopeRule": ("Every item GOV.UK indexes as content_store_document_type "
                      "drug_safety_update, the whole archive, re-read each run. Device alerts "
                      "(DSI, NatPSA) are in data/mhra-alerts.json, not here."),
        "specialityRule": ("A row's specialities come only from GOV.UK's own therapeutic_area "
                           "facet, mapped through config/mhra-dsu-speciality-map.json. A facet "
                           "that maps to no panel contributes nothing and is listed in "
                           "unmappedFacets. No speciality is inferred from the title or text."),
        "note": ("published is GOV.UK's first_published_at; updated is its public_timestamp. "
                 "roundup marks the monthly 'Letters and medicine recalls sent to healthcare "
                 "professionals' digest. Refreshed daily by .github/workflows/mhra-dsu.yml."),
        "coverage": {"complete": len(ordered) == api_total, "apiTotal": api_total,
                     "fetched": len(ordered)},
        "counts": {
            "updates": len(ordered),
            "withSpeciality": sum(1 for r in ordered if r["specialities"]),
            "roundups": sum(1 for r in ordered if r["roundup"]),
            "bySpeciality": by_spec,
            "byTherapeuticArea": dict(sorted(by_facet.items())),
        },
        "facetLabels": {f: labels[f] for f in sorted(labels) if labels[f]},
        "unmappedFacets": unmapped,
        "panelsWithNoFacet": no_facet,
        "updates": ordered,
    }


def fetch_all():
    results, start, total = [], 0, None
    while True:
        qs = urllib.parse.urlencode({
            "filter_content_store_document_type": "drug_safety_update",
            "order": "-public_timestamp", "count": PAGE, "start": start, "fields": FIELDS})
        data = get("%s?%s" % (SEARCH_API, qs))
        total = data.get("total", total)
        page = data.get("results") or []
        results.extend(page)
        start += PAGE
        if not page or start >= (total or 0):
            break
        time.sleep(PAGE_SLEEP)
    return results, total or 0


def fetch_live_labels():
    try:
        doc = get(FINDER_API)
    except Exception as exc:
        print("  WARN could not read finder facet labels (%s); using the table's" % exc)
        return {}
    for f in (doc.get("details") or {}).get("facets") or []:
        if f.get("key") == "therapeutic_area":
            return {v["value"]: v.get("label") for v in f.get("allowed_values") or []}
    return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    slugs = panel_slugs()
    table = load_map()
    errs = validate_map(table, slugs)
    if errs:
        print("mapping table is broken, refusing to run:\n  " + "\n  ".join(errs))
        return 1

    results, total = fetch_all()
    if len({r.get("link") for r in results}) != total:
        # GOV.UK's index can shift between pages mid-walk. One retry, then refuse:
        # the last good commit stays live rather than publishing a partial file.
        time.sleep(10)
        results, total = fetch_all()
    labels = fetch_live_labels()
    doc = assemble(results, table, slugs, labels, total, dt.date.today())
    c = doc["counts"]
    print("%d Drug Safety Updates (API total %d), %d with a Hub speciality, %d roundups"
          % (c["updates"], total, c["withSpeciality"], c["roundups"]))
    for u in doc["unmappedFacets"]:
        print("  unmapped facet %-38s %4d  %s" % (u["facet"], u["updates"], u["reason"][:60]))
    if not doc["coverage"]["complete"]:
        print("INCOMPLETE: fetched %d of %d. Nothing written." % (c["updates"], total))
        return 1
    if args.dry_run:
        print("--dry-run: nothing written.")
        return 0
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote %s. Now: python3 scripts/stamp_notice.py && python3 verify.py" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
