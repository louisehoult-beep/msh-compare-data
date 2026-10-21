#!/usr/bin/env python3
"""Feed digital framework lot memberships into suppliers' `frameworks[]` arrays.

WHY THIS EXISTS (20/10/2026)
----------------------------
data/digital-frameworks.json (scripts/refresh_digital_frameworks.py) reads the
Government Commercial Agency's own supplier lists for the national digital
frameworks — Technology Services 4 (RM6190) and the rest — lot by lot. Nothing
fed it back into a supplier's own record, so a Hub company on Technology
Services 4 showed no framework on the Suppliers directory, Meeting Prep or the
Company Report. This does for those lists what backfill_index_frameworks.py
does for NHS Supply Chain's launch briefs.

WHAT IT DOES, AND WHAT IT REFUSES TO DO
--------------------------------------
- ADDS one framework row to a supplier only where the framework's own supplier
  list names it, resolved by scripts/company_match.py's exact-only rule (the
  same rule every award match uses). Never by resemblance, and never a new
  supplier: the 343 general IT firms on Technology Services 4 that the Hub does
  not track stay off the Hub.
- Each row carries `source: "digital-frameworks"`, the owner's URL, the
  reference, the dates, the lots the list names the supplier on and the date the
  list was read, so a reader can tell it from a curated row.
- Skips a framework a curated row on the same supplier already carries (same
  reference), so a hand-read row that names the lot is not shown twice.
- NEVER touches a row it did not write. Re-running replaces only its own rows
  (matched on source + framework name), so it is idempotent, and a supplier the
  list no longer names loses the row.
- Only frameworks whose supplier list was actually read (non-empty). A
  framework with `suppliers: null` or empty lots says nothing about anyone.

Writes data/supplier-seed.json (the nightly index rebuild copies seed records)
and mirrors the same rows into data/supplier-index.json. Then stamp_notice.py,
then verify.py.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

ROOT = os.path.dirname(HERE)
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")
DIGITAL = os.path.join(ROOT, "data", "digital-frameworks.json")
SOURCE = "digital-frameworks"


def uk_date(iso):
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return None
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def lot_order(kv):
    """Lot "3a" sorts after lot "3" and before lot "4"."""
    m = re.match(r"(\d+)(.*)", str(kv[0]))
    return (int(m.group(1)), m.group(2)) if m else (10 ** 6, str(kv[0]))


def memberships(doc, index):
    """{company: [row]} from every framework whose supplier list was read."""
    out = {}
    for fw in (doc or {}).get("frameworks") or []:
        lots_by_name = {}
        for lot in fw.get("lots") or []:
            for n in lot.get("suppliers") or []:
                lots_by_name.setdefault(n, []).append(lot)
        names = set(fw.get("suppliers") or []) | set(lots_by_name)
        if not names:
            continue
        per_company = {}
        for n in sorted(names):
            company, state, _ = company_match.resolve(n, index)
            if state != "confirmed":
                continue
            per_company.setdefault(company, {"names": set(), "lots": {}})
            per_company[company]["names"].add(n)
            for lot in lots_by_name.get(n, []):
                per_company[company]["lots"][str(lot.get("lot"))] = lot.get("name")
        start, end = uk_date(fw.get("starts")), uk_date(fw.get("ends"))
        for company, m in per_company.items():
            lots = [{"lot": k, "name": v} for k, v in
                    sorted(m["lots"].items(), key=lot_order)]
            named = ", ".join("\"%s\"" % n for n in sorted(m["names"]))
            lot_text = ("on lot%s %s" % ("s" if len(lots) > 1 else "",
                                         ", ".join(l["lot"] for l in lots))) if lots else "on no named lot"
            row = {
                "name": fw.get("name"),
                "reference": fw.get("reference"),
                "dates": ("%s to %s" % (start, end)) if start and end else None,
                "note": ("Named on %s's own supplier list for this framework as %s, %s. "
                         "%d suppliers on the framework."
                         % (fw.get("owner") or "the framework owner", named, lot_text,
                            len(names))),
                "owner": fw.get("owner"),
                "lots": lots,
                "supplierCount": len(names),
                "url": fw.get("url"),
                "source": SOURCE,
                "capturedOn": fw.get("verifiedOn"),
            }
            out.setdefault(company, []).append({k: v for k, v in row.items() if v is not None})
    return out


def apply(path, rows_by_company):
    with open(path, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    added = removed = 0
    for s in doc.get("suppliers") or []:
        fws = s.get("frameworks") or []
        keep = [f for f in fws if not (isinstance(f, dict) and f.get("source") == SOURCE)]
        # A curated row for the same framework (read by hand at the supplier's own
        # service page, so it can name the lot) wins; never show the framework twice.
        curated = {f.get("reference") for f in keep if isinstance(f, dict) and f.get("reference")}
        mine = [r for r in rows_by_company.get(s.get("name"), [])
                if r.get("reference") not in curated]
        old = [f for f in fws if isinstance(f, dict) and f.get("source") == SOURCE]
        if old == mine:
            continue
        removed += len(old)
        added += len(mine)
        s["frameworks"] = keep + mine
    if added or removed:
        fmt, round_trips = write_like(path, doc)
        print(describe(path, fmt, round_trips))
    print("%s: %d digital framework row(s) written, %d replaced" % (path, added, removed))


def main():
    with open(SEED, encoding="utf-8") as f:
        seed = json.load(f)
    with open(DIGITAL, encoding="utf-8") as f:
        digital = json.load(f)
    rows = memberships(digital, company_match.build_index(seed))
    print("digital framework memberships on Hub companies: %d company(ies): %s"
          % (len(rows), ", ".join(sorted(rows)) or "none"))
    if "--check" in sys.argv:
        return
    apply(SEED, rows)
    apply(INDEX, rows)


if __name__ == "__main__":
    main()
