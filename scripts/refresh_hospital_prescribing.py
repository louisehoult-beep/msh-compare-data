#!/usr/bin/env python3
"""Hospital prescribing dispensed in the community — England, trust level.

Source: NHSBSA Open Data, package `hospital-prescribing-dispensed-in-the-community`,
Open Government Licence 3.0. Attribution is carried in index.json and printed by the
tool, because OGL requires it and because a reader has to be able to check us.

WHAT THIS DATASET IS, AND IS NOT
--------------------------------
It is items PRESCRIBED BY AN NHS TRUST and DISPENSED IN A COMMUNITY PHARMACY in
England. It is NOT in-hospital usage, and it is NOT GP prescribing. A rep reading a
trust's row is seeing what that trust's prescribers sent out to community pharmacies,
which is a real but partial view of the trust. The tool says so on its face; do not
remove that line to make the panel tidier.

Not to be confused with `english-prescribing-data-epd` (GP practice level). That
package is ALSO the wrong one to reach for: it is frozen at June 2025. The live GP
dataset is `english-prescribing-dataset-epd-with-snomed-code`. Verified 15/08/2026.

THE DERIVATION RULES, STATED
----------------------------
Rule 14 of the constitution: a derived claim carries the rule it was derived under.
All four are published in index.json and rendered by app/hospital-prescribing.js.

  1. SUBSTANCE   = BNF code characters 1-9. This is the chemical substance, so all
                   strengths and forms of one molecule collapse into one row.
  2. PRODUCT     = BNF code characters 1-11. Characters 10-11 are the product
                   segment. "AA" is the generic; any other pair is a brand.
                   Checked against the live file on 15/08/2026: AA gave the generic
                   for Zopiclone/Zimovane, Olanzapine/Zyprexa, Aripiprazole/Abilify,
                   Methylphenidate/Concerta XL, Methadone/Physeptone and Sodium
                   valproate/Epilim. 74.3% of substances have an AA product; the
                   remainder had no generic dispensed in the month and are flagged
                   `g: false` rather than silently labelled.
  3. LABEL       = the product's most common BNF_NAME truncated at its first digit,
                   so "Zopiclone 3.75mg tablets" becomes "Zopiclone". Names with no
                   digit are kept whole.
  4. TREND       = a percentage change is published ONLY where the baseline month is
                   at or above MIN_BASELINE_ITEMS. Below that, the tool prints "too
                   few to trend" and no number. A trust going from 1 item to 2 is
                   +100% and means nothing; publishing it would be exactly the kind
                   of derived claim rule 14 exists to stop.

Output: data/hospital-prescribing/index.json plus one shard per BNF chapter, so the
browser fetches ~1 MB rather than the lot.

Usage:  python3 scripts/refresh_hospital_prescribing.py [--months N] [--out DIR]
"""

import argparse
import collections
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request

PACKAGE = "hospital-prescribing-dispensed-in-the-community"
CKAN = "https://opendata.nhsbsa.net/api/3/action"
LICENCE = "Open Government Licence 3.0"
ATTRIBUTION = ("Contains public sector information licensed under the Open Government "
               "Licence v3.0. Source: NHS Business Services Authority.")

# How many months of history to carry. 13 gives a 12-month trend AND a same-month
# year-on-year comparison, which is the one comparison that survives seasonality.
MONTHS = 13

# The evidence floor for a published percentage change. Read by verify.py out of this
# file, so the gate checks the number that actually runs rather than a copy of it.
MIN_BASELINE_ITEMS = 25

UA = {"User-Agent": "msh-compare-data/hospital-prescribing (+elevateandthrive.uk)"}


def fetch(url, timeout=180, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:          # noqa: BLE001 - retried, then reported
            last = exc
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
    raise RuntimeError("could not fetch %s: %s" % (url, last))


def resources():
    """Monthly CSVs, oldest first. Names are HOSPITAL_DISP_COMMUNITY_YYYYMM."""
    doc = json.loads(fetch("%s/package_show?id=%s" % (CKAN, PACKAGE), timeout=90))
    out = []
    for r in doc["result"]["resources"]:
        m = re.search(r"(\d{6})$", r.get("name", "") or "")
        if m and (r.get("format", "") or "").upper() == "CSV":
            out.append((m.group(1), r["url"]))
    return sorted(out)


def label_of(name):
    """Rule 3: truncate at the first digit. 'Zopiclone 3.75mg tablets' -> 'Zopiclone'."""
    m = re.search(r"\d", name or "")
    return ((name[:m.start()] if m else name) or "").strip(" _-") or (name or "").strip()


def calendar_back(latest, months):
    """N contiguous YYYYMM ending at `latest`, oldest first."""
    y, m = int(latest[:4]), int(latest[4:6])
    out = []
    for _ in range(months):
        out.append("%04d%02d" % (y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def build(months, outdir):
    res = resources()
    if not res:
        sys.exit("no CSV resources found in package %s" % PACKAGE)

    # The period list is a CALENDAR range, not "the last N files NHSBSA happens to
    # have published". They are not the same thing: NHSBSA never published May 2025
    # (202505), and taking the last 13 files silently produced a 14-month span with
    # the gap closed up — so every sparkline plotted April 2025 next to June 2025 as
    # though they were consecutive, and the year-on-year column compared the wrong
    # months. A month the source does not publish is carried as null, named in
    # index.json, and rendered as a break in the line. It is never carried as zero,
    # which would read as a collapse in prescribing that never happened.
    available = dict(res)
    periods = calendar_back(res[-1][0], months)
    window = [(p, available[p]) for p in periods if p in available]
    missing = [p for p in periods if p not in available]
    pidx = {p: i for i, p in enumerate(periods)}
    n = len(periods)
    print("periods: %s -> %s (%d months)" % (periods[0], periods[-1], n))
    if missing:
        print("  NOT PUBLISHED BY NHSBSA, carried as null: %s" % ", ".join(missing))

    trusts = {}
    # series[substance][trust][product_segment] = [items per month]
    series = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * n)))
    # cost[substance][trust] = [actual cost per month]
    cost = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0] * n))
    names = collections.defaultdict(collections.Counter)   # (sub, seg) -> name counter

    for period, url in window:
        raw = fetch(url)
        i = pidx[period]
        rows = 0
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
            code = (row.get("BNF_CODE") or "").strip()
            tcode = (row.get("HOSPITAL_TRUST_CODE") or "").strip()
            if len(code) < 11 or not tcode:
                continue
            sub, seg = code[:9], code[9:11]
            trusts.setdefault(tcode, (row.get("HOSPITAL_TRUST") or "").strip())
            try:
                items = int(row.get("TOTAL_ITEMS") or 0)
            except ValueError:
                items = 0
            series[sub][tcode][seg][i] += items
            try:
                cost[sub][tcode][i] += float(row.get("TOTAL_ACTUAL_COST") or 0)
            except ValueError:
                pass
            names[(sub, seg)][(row.get("BNF_NAME") or "").strip()] += items
            rows += 1
        print("  %s  %7d rows  (%.1f MB)" % (period, rows, len(raw) / 1e6))

    # ---- labels -----------------------------------------------------------
    # Segments are taken from what actually SHIPS — a segment whose every month is
    # zero is dropped at packing time, so counting it here flagged molecules as
    # having a generic that the shard did not contain. Caught by verify.py on
    # 15/08/2026: "Generic Methadose diluent" appeared as a real AA presentation on
    # nil volume, which would have put a false brand share on the panel.
    sub_label, sub_generic, prod_label = {}, {}, {}
    for sub in series:
        segs = set()
        for _tc, by_seg in series[sub].items():
            for seg, arr in by_seg.items():
                if any(arr):
                    segs.add(seg)
        if not segs:
            continue
        for seg in segs:
            top = names[(sub, seg)].most_common(1)
            prod_label[(sub, seg)] = label_of(top[0][0]) if top else seg
        if "AA" in segs:
            sub_label[sub] = prod_label[(sub, "AA")]
            sub_generic[sub] = True
        else:
            # Rule 2 fallback: no generic dispensed in the window. Use the highest
            # volume presentation and flag it, rather than pass a brand off as the
            # molecule name.
            best = max(segs, key=lambda g: sum(names[(sub, g)].values()), default=None)
            sub_label[sub] = prod_label[(sub, best)] if best else sub
            sub_generic[sub] = False

    # ---- write ------------------------------------------------------------
    os.makedirs(outdir, exist_ok=True)
    miss_idx = [pidx[p] for p in missing]

    def blank(arr):
        """Null out the months NHSBSA did not publish. Never zero — see build()."""
        out = list(arr)
        for i in miss_idx:
            out[i] = None
        return out

    chapters = collections.defaultdict(dict)
    catalogue = []
    for sub, by_trust in series.items():
        if sub not in sub_label:
            continue
        packed = {}
        total = 0
        for tcode, by_seg in by_trust.items():
            entry = {}
            for seg, arr in by_seg.items():
                if any(arr):
                    entry[seg] = blank(arr)
                    total += sum(arr)
            if entry:
                packed[tcode] = entry
        if not packed:
            continue
        chapters[sub[:2]][sub] = {
            "p": {seg: prod_label[(sub, seg)] for seg in
                  {s for t in packed.values() for s in t}},
            "t": packed,
            "c": {tc: blank([round(v, 2) for v in cost[sub][tc]]) for tc in packed},
        }
        # Brand labels ride in the index so they are SEARCHABLE. A rep sells
        # Abilify, not aripiprazole, and will type the brand — without this the
        # index only holds the generic and the primary use case returns nothing.
        brands = sorted({prod_label[(sub, seg)]
                         for t in packed.values() for seg in t
                         if seg != "AA" and prod_label.get((sub, seg))
                         and prod_label[(sub, seg)] != sub_label[sub]})
        row = {
            "c": sub, "n": sub_label[sub], "ch": sub[:2],
            "g": sub_generic[sub], "i": total, "tr": len(packed),
        }
        if brands:
            row["b"] = brands
        catalogue.append(row)

    for ch, subs in sorted(chapters.items()):
        path = os.path.join(outdir, "ch-%s.json" % ch)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"periods": periods, "s": subs}, f, separators=(",", ":"))
        print("  wrote %-28s %6.2f MB  (%d substances)"
              % (os.path.basename(path), os.path.getsize(path) / 1e6, len(subs)))

    catalogue.sort(key=lambda r: -r["i"])
    index = {
        "generatedOn": time.strftime("%Y-%m-%d"),
        "source": {
            "name": "NHSBSA Open Data — hospital prescribing dispensed in the community",
            "package": PACKAGE,
            "url": "https://opendata.nhsbsa.net/dataset/%s" % PACKAGE,
            "licence": LICENCE,
            "attribution": ATTRIBUTION,
        },
        "scope": ("Items prescribed by an NHS trust in England and dispensed in a "
                  "community pharmacy. Not in-hospital usage, and not GP prescribing."),
        "rules": {
            "substance": "BNF code characters 1-9.",
            "product": "BNF code characters 1-11; segment 10-11 'AA' is the generic, "
                       "any other pair is a brand.",
            "label": "The product's most common BNF_NAME truncated at its first digit.",
            "trend": "A percentage change is published only where the baseline month is "
                     "at or above %d items. Below that the tool prints 'too few to "
                     "trend' and no number." % MIN_BASELINE_ITEMS,
        },
        "minBaselineItems": MIN_BASELINE_ITEMS,
        "periods": periods,
        "missingPeriods": missing,
        "trusts": trusts,
        "substances": catalogue,
    }
    with open(os.path.join(outdir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"))
    print("  wrote %-28s %6.2f MB  (%d substances, %d trusts)"
          % ("index.json", os.path.getsize(os.path.join(outdir, "index.json")) / 1e6,
             len(catalogue), len(trusts)))
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=MONTHS)
    ap.add_argument("--out", default=os.path.join("data", "hospital-prescribing"))
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    idx = build(a.months, a.out)
    print("\nOK  %d substances across %d trusts, %s to %s"
          % (len(idx["substances"]), len(idx["trusts"]),
             idx["periods"][0], idx["periods"][-1]))


if __name__ == "__main__":
    main()
