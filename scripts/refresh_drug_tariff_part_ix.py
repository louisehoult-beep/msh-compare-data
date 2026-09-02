#!/usr/bin/env python3
"""Capture the current NHSBSA Drug Tariff Part IX (appliances) file as a compact,
client-fetchable JSON, so the Hub's Frameworks/Awards/Tenders page can offer a
searchable Part IX lookup without embedding 66,000+ rows in the WordPress page body.

WHY THIS EXISTS
---------------
Part IX is the national reimbursement list for appliances — every wound care dressing,
continence, stoma and IV/vascular consumable product, pack size and Drug Tariff price —
published monthly by NHSBSA. Lou asked for it "all... including on this page", but the
full file (~66,000 rows) is roughly 20x the size that already forced the tender-history
page onto a seed-plus-chunk publishing pattern (see build_tender_history_page.py and
Process flows for all brands/tender-history-and-calendar.md). Embedding it inline in a
WP page body isn't viable through the tools available in this session.

The fix already exists elsewhere on the same page: build_tender_history_page.py's "Open
now" panel fetches data/open-tenders.json from this repo's raw.githubusercontent.com URL
client-side, refreshed by its own GitHub Action. This script produces the equivalent for
Part IX — data/drug-tariff-part-ix.json — refreshed monthly by
.github/workflows/drug-tariff.yml, not rebuilt by hand each time.

SOURCE, AND WHY IT IS THE RIGHT ONE
------------------------------------
NHSBSA publishes Part IX itself at a predictable URL:
  https://www.nhsbsa.nhs.uk/sites/default/files/<YYYY-MM>/Drug%20Tariff%20Part%20IX%20<Month>%20<Year>.csv
where <YYYY-MM> is the month BEFORE the tariff's effective month (verified against the
September 2026 file, published under the 2026-08 path — NHSBSA publishes each month's
tariff ahead of its effective date). This script tries the current month's effective-date
folder pattern and falls back a month at a time if the guessed URL 404s, since publication
timing can drift by a few days either side of the calendar month boundary.

SCHEMA, DELIBERATELY LEAN
--------------------------
Array-of-arrays, not array-of-objects — cuts JSON size by ~25% by not repeating field
names on every one of 66k+ rows (verified 02/09/2026: 12.95MB vs 16.73MB for the same
data). gzip (which GitHub raw serves automatically) takes the array form to ~290KB over
the wire. Columns kept: DT Part, Supplier, VMP name (generic), AMP name (brand), size,
qty, unit of measure, price. SNOMED/GTIN/product-order-number codes are dropped — not
useful for a rep searching by product or supplier, and they roughly double row size.

Run: python3 scripts/refresh_drug_tariff_part_ix.py [--out PATH] [--month YYYY-MM]
"""
import argparse
import csv
import datetime
import io
import json
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def _url_for(effective_year, effective_month, publish_year, publish_month):
    fname = "Drug Tariff Part IX %s %d.csv" % (MONTH_NAMES[effective_month - 1], effective_year)
    return "https://www.nhsbsa.nhs.uk/sites/default/files/%04d-%02d/%s" % (
        publish_year, publish_month, fname.replace(" ", "%20"))


def _add_months(y, m, delta):
    idx = (y * 12 + (m - 1)) + delta
    return idx // 12, idx % 12 + 1


def fetch_current_csv(explicit_month=None, tries_back=3, tries_fwd=2):
    """Try the effective month implied by today's date (or --month), publish folder
    one month earlier per the verified naming pattern; step forward/back if that 404s.
    Returns (csv_bytes, effective_year, effective_month, url_used)."""
    today = datetime.date.today()
    if explicit_month:
        ey, em = (int(x) for x in explicit_month.split("-"))
    else:
        ey, em = today.year, today.month

    candidates = []
    for delta in range(-tries_back, tries_fwd + 1):
        cy, cm = _add_months(ey, em, delta)
        py, pm = _add_months(cy, cm, -1)  # publish folder = one month before effective month
        candidates.append((cy, cm, py, pm))
    # Try closest-to-today first, not strictly chronological
    candidates.sort(key=lambda t: abs((t[0], t[1])[0] * 12 + (t[0], t[1])[1] - (ey * 12 + em)))

    last_err = None
    for cy, cm, py, pm in candidates:
        url = _url_for(cy, cm, py, pm)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), cy, cm, url
        except urllib.error.HTTPError as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            time.sleep(2)
            continue
    raise RuntimeError("Could not find a working Drug Tariff Part IX URL near %04d-%02d "
                        "(last error: %s). NHSBSA may have changed its naming pattern — "
                        "re-check https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-"
                        "appliance-contractors/drug-tariff/drug-tariff-part-ix by hand."
                        % (ey, em, last_err))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/drug-tariff-part-ix.json")
    ap.add_argument("--month", default=None, help="Effective month YYYY-MM, default: current")
    args = ap.parse_args()

    raw, ey, em, url = fetch_current_csv(args.month)
    text = raw.decode("utf-8-sig", "replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append([
            (row.get("DT Part") or "").strip(),
            (row.get("Supplier Name") or "").strip(),
            (row.get("VMP Name") or "").strip(),
            (row.get("AMP Name") or "").strip(),
            (row.get("sz/wt") or "").strip(),
            (row.get("QTY") or "").strip(),
            (row.get("UOM QTY") or "").strip(),
            (row.get("Price") or "").strip(),
        ])

    doc = {
        "dataAsOf": time.strftime("%Y-%m-%d"),
        "effectiveMonth": "%04d-%02d" % (ey, em),
        "source": url,
        "sourcePage": "https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-"
                      "contractors/drug-tariff/drug-tariff-part-ix",
        "schema": ["part", "supplier", "vmp", "amp", "size", "qty", "uom", "price"],
        "rowCount": len(rows),
        "note": "Every Part IX line NHSBSA publishes for this effective month, verbatim. "
                "Price is the Drug Tariff reimbursement price at publication, not necessarily "
                "today's if this file has aged — check dataAsOf. Refreshed monthly by "
                ".github/workflows/drug-tariff.yml, not hand-rebuilt.",
        "rows": rows,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
    print("Wrote %s — %d rows, effective %04d-%02d, from %s" % (args.out, len(rows), ey, em, url))


if __name__ == "__main__":
    main()
