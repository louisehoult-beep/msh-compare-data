#!/usr/bin/env python3
"""GP (primary care) prescribing in England, brand share by ICB.

Source: NHSBSA Open Data, package `english-prescribing-dataset-epd-with-snomed-code`
(resources EPD_SNOMED_YYYYMM), Open Government Licence 3.0. Attribution is carried
in index.json because OGL requires it and because a reader has to be able to check us.

WHY THIS PACKAGE
----------------
The older `english-prescribing-data-epd` package stops at June 2025. The SNOMED
package is the live one (checked 29/09/2026: latest month 202607, published
18/09/2026). This is the GP-practice-level sibling of
scripts/refresh_hospital_prescribing.py and follows its rules and layout.

WHAT THIS DATASET IS, AND IS NOT
--------------------------------
Items prescribed in primary care in England (GP practices and the other
prescribers NHSBSA attributes to a practice or ICB) and dispensed in the
community. It is NOT hospital in-patient use and NOT the trust-level
"hospital prescribing dispensed in the community" dataset.

HOW IT IS FETCHED
-----------------
The NHSBSA CKAN datastore SQL API (`datastore_search_sql`) aggregates on the
server, so we never download the ~18.6 million practice-level rows a month.
One grouped query per month returns ~233,000 ICB x product rows. Results over
32,000 rows come back as one or more temporary CSV.gz links (`gc_urls`), which
are downloaded and parsed. Every month is reconciled against a separate
server-side total per BNF section; a short download fails the build.

THE DERIVATION RULES, STATED
----------------------------
Rule 14 of the constitution: a derived claim carries the rule it was derived under.
All of these are published in index.json.

  1. SUBSTANCE = NHSBSA's own BNF_CHEMICAL_SUBSTANCE_CODE. For chapters 01-19 that is
                 BNF code characters 1-9. For the appliance chapters 20-23 NHSBSA
                 sets it to the 4-character section (2122 = emollient devices),
                 because an appliance has no chemical substance.
  2. PRODUCT   = BNF code characters 1-11. The product key stored in a shard is the
                 part after the substance: characters 10-11 for chapters 01-19, where
                 "AA" is the generic and any other pair is a brand (as in the
                 hospital tool); characters 5-11 for chapters 20-23, where every
                 product is a named proprietary product and there is no generic, so
                 `g` is null rather than false.
  2b. CATCH-ALLS = where one 11-character code holds presentations whose rule-3
                 labels do not all start with the same word, each 13-character code is its own product (key of
                 4 characters, e.g. "BBIC"). BNF's catch-all substances do this:
                 130201000BB "Other emollient preparations" holds Dermol, Doublebase,
                 Aveeno, E45 and more under one 11-character code. The hospital rule
                 alone would have called all 395,249 of those July 2026 items
                 "Dermol". Generics ('AA') are never split. The codes so split are
                 listed in index.json splitProducts.
  3. LABEL     = the product's most common BNF_PRESENTATION_NAME in the window,
                 truncated at its first word that starts with a digit ("Zerobase 11% cream" -> "Zerobase").
                 A name with no digit, or starting with one, is kept whole.
  4. TREND     = a percentage change is published ONLY where the baseline month is at
                 or above MIN_BASELINE_ITEMS. Below that the panel must print "too few
                 to trend" and no number.
  5. ICB       = the 36 ICBs effective 01/04/2026, as carried in NHSBSA's ICB_CODE
                 column for the latest month (NHSBSA assigns each practice to its
                 sub-ICB location and ICB from the NHS ODS register). Months before
                 April 2026 carry the old 42 ICB codes, so they are re-attributed to
                 today's boundaries by PRACTICE: every practice is placed in the ICB
                 the latest month puts it in. Rows from an old ICB are rolled up
                 whole where all its practices went to one current ICB; the three old
                 ICBs that were split (QJG, QM7, QNQ in 2025/26) are resolved practice
                 by practice in the same server-side query. A practice absent from the
                 latest month (closed or merged) goes to the current ICB that took the
                 largest share of its old ICB, and the items so placed are counted per
                 month in index.json (`icbAttribution`).
                 Rows NHSBSA could not attribute to any practice keep ICB code "-"
                 so national totals still reconcile to the source.

Output: data/gp-prescribing/index.json plus one shard per BNF section
(data/gp-prescribing/s-XXXX.json), so a panel fetches only the section it reads.

Usage:  python3 scripts/refresh_gp_prescribing.py [--months N] [--out DIR] [--if-new]

Runtime measured 29/09/2026: 3 to 5.5 minutes for 13 months, all chapters.
"""

import argparse
import collections
import csv
import gzip
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bnf_products import first_word, label_of, product_codes  # noqa: E402,F401
import time
import urllib.parse
import urllib.request

PACKAGE = "english-prescribing-dataset-epd-with-snomed-code"
CKAN = "https://opendata.nhsbsa.net/api/3/action"
LICENCE = "Open Government Licence 3.0"
ATTRIBUTION = ("Contains public sector information licensed under the Open Government "
               "Licence v3.0. Source: NHS Business Services Authority.")

# 13 months: a 12-month trend plus the same month last year, the one comparison
# that survives seasonality. Measured 29/09/2026: ~25s of API time per month.
MONTHS = 13

# The evidence floor for a published percentage change. Read by verify.py out of this
# file, so the gate checks the number that actually runs rather than a copy of it.
MIN_BASELINE_ITEMS = 25

# Chapters 20-23 are appliances: no chemical substance, no generic.
APPLIANCE_CHAPTERS = {"20", "21", "22", "23"}

UNIDENTIFIED = "-"

UA = {"User-Agent": "msh-compare-data/gp-prescribing (+elevateandthrive.uk)"}


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------
def fetch(url, data=None, timeout=180, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:          # noqa: BLE001 - retried, then reported
            last = exc
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError("could not fetch %s: %s" % (url.split("?")[0], last))


def parse_sql_response(doc, get=None):
    """Rows from a datastore_search_sql response, inline or via gc_urls.

    Returns a list of dicts with string values (CSV) or native values (inline).
    `get` is injectable for tests.
    """
    get = get or fetch
    if not doc.get("success"):
        raise RuntimeError("SQL API error: %s" % str(doc.get("error") or doc)[:300])
    res = doc.get("result") or {}
    inner = res.get("result")
    if isinstance(inner, dict) and "records" in inner:
        return list(inner["records"])
    urls = [u.get("url") for u in (res.get("gc_urls") or []) if u.get("url")]
    if not urls:
        raise RuntimeError("SQL API returned neither records nor gc_urls: %s"
                           % str(res)[:300])
    rows = []
    for u in urls:
        raw = get(u.replace("`", "%60"))
        text = gzip.decompress(raw).decode("utf-8-sig")
        rows.extend(csv.DictReader(io.StringIO(text)))
    return rows


def sql(table, query):
    body = urllib.parse.urlencode({"resource_id": table, "sql": query}).encode()
    doc = json.loads(fetch("%s/datastore_search_sql" % CKAN, data=body, timeout=300))
    return parse_sql_response(doc)


def resources(doc=None):
    """Monthly resources, oldest first, as [(YYYYMM, resource_name)].

    Names are EPD_SNOMED_YYYYMM. As in the hospital tool, a revised month may carry
    a trailing word (…202505FINAL) and the revision wins over the plain file.
    Only resources NHSBSA has loaded into the datastore can be queried.
    """
    if doc is None:
        doc = json.loads(fetch("%s/package_show?id=%s" % (CKAN, PACKAGE), timeout=90))
    best = {}
    for r in doc["result"]["resources"]:
        name = (r.get("name", "") or "").strip()
        m = re.fullmatch(r"EPD_SNOMED_(\d{6})([A-Z]*)", name.upper())
        if not m or r.get("datastore_active") is False:
            continue
        period, revision = m.group(1), m.group(2)
        if period not in best or (revision and not best[period][0]):
            best[period] = (revision, name)
    return sorted((p, n) for p, (_rev, n) in best.items())


# --------------------------------------------------------------------------
# pure helpers (tested offline)
# --------------------------------------------------------------------------
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


def product_key(sub, code):
    """Rule 2: the product segment after the substance code."""
    return code[len(sub):]


def is_generic(sub, key):
    return sub[:2] not in APPLIANCE_CHAPTERS and key[:2] == "AA"


# label_of, first_word and product_codes (rule 2b, the catch-all split) live in
# scripts/bnf_products.py since 29/09/2026, shared with refresh_hospital_prescribing.py
# so the GP and hospital tools cannot disagree on what a "product" is. The shared
# first_word splits at hyphens and underscores and skips a leading "Half", which the
# copy that used to be here did not.


def plan_attribution(month_practices, current):
    """Rule 5. Decide how one month's rows reach today's ICBs.

    month_practices: [(practice_code, icb_code_that_month, items)]
    current:         {practice_code: icb_code_in_latest_month}

    Returns (primary, exceptions, carried):
      primary    {old_icb: current_icb}  where the old ICB's rows go by default
      exceptions {practice: current_icb} practices resolved one by one, because
                 they are in a current ICB other than their old ICB's primary
      carried    items from practices absent from the latest month, placed by
                 their old ICB's primary (reported, never hidden)
    """
    share = collections.defaultdict(collections.Counter)
    for prac, icb, items in month_practices:
        if icb == UNIDENTIFIED:
            continue
        tgt = current.get(prac)
        if tgt and tgt != UNIDENTIFIED:
            share[icb][tgt] += items
    current_icbs = set(v for v in current.values() if v != UNIDENTIFIED)
    primary = {UNIDENTIFIED: UNIDENTIFIED}
    for prac, icb, _items in month_practices:
        if icb in primary:
            continue
        if share[icb]:
            # Deterministic: most items, then code order.
            primary[icb] = sorted(share[icb].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        elif icb in current_icbs:
            primary[icb] = icb
        else:
            primary[icb] = UNIDENTIFIED
    exceptions, carried = {}, 0
    for prac, icb, items in month_practices:
        if icb == UNIDENTIFIED:
            continue
        tgt = current.get(prac)
        if not tgt or tgt == UNIDENTIFIED:
            carried += items
        elif tgt != primary[icb]:
            exceptions[prac] = tgt
    return primary, exceptions, carried


def group_expr(exceptions):
    """SQL expression that keeps exception practices separate, everything else by ICB."""
    if not exceptions:
        return "ICB_CODE"
    for p in exceptions:
        if not re.fullmatch(r"[A-Z0-9]{2,8}", p):
            raise ValueError("unexpected practice code %r" % p)
    codes = ",".join("'%s'" % p for p in sorted(exceptions))
    return ("CASE WHEN PRACTICE_CODE IN (%s) THEN CONCAT('P:', PRACTICE_CODE) "
            "ELSE ICB_CODE END" % codes)


def resolve(group, primary, exceptions):
    if group.startswith("P:"):
        return exceptions[group[2:]]
    return primary.get(group, UNIDENTIFIED)


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def build(months, outdir, run_sql=sql, res=None):
    res = res if res is not None else resources()
    if not res:
        sys.exit("no EPD_SNOMED resources found in package %s" % PACKAGE)
    available = dict(res)
    periods = calendar_back(res[-1][0], months)
    missing = [p for p in periods if p not in available]
    pidx = {p: i for i, p in enumerate(periods)}
    n = len(periods)
    latest_table = available[periods[-1]]
    print("periods: %s -> %s (%d months)" % (periods[0], periods[-1], n))
    if missing:
        print("  NOT PUBLISHED BY NHSBSA, carried as null: %s" % ", ".join(missing))

    # Latest month: practice -> current ICB, and current ICB names.
    q_prac = ("SELECT PRACTICE_CODE AS pr, ICB_CODE AS icb, ICB_NAME AS nm, "
              "SUM(ITEMS) AS i FROM `%s` GROUP BY PRACTICE_CODE, ICB_CODE, ICB_NAME")
    latest_rows = run_sql(latest_table, q_prac % latest_table)
    current, icb_names = {}, {}
    for r in latest_rows:
        current[r["pr"]] = r["icb"]
        icb_names[r["icb"]] = (r["nm"] or "").strip()
    icb_names[UNIDENTIFIED] = "Unidentified (NHSBSA could not attribute to a practice)"

    items = collections.defaultdict(       # sub -> icb -> key -> [n]
        lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * n)))
    cost = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0] * n)))
    names = collections.defaultdict(collections.Counter)      # code13 -> name counter
    sub_names = {}
    sec_totals = collections.defaultdict(lambda: {"i": [None] * n, "c": [None] * n})
    attribution = {}

    for period in periods:
        if period not in available:
            continue
        table, i = available[period], pidx[period]
        t0 = time.time()
        if period == periods[-1]:
            prac_rows = latest_rows
        else:
            prac_rows = run_sql(table, q_prac % table)
        mp = [(r["pr"], r["icb"], int(float(r["i"] or 0))) for r in prac_rows]
        primary, exceptions, carried = plan_attribution(mp, current)
        remapped = sorted(k for k, v in primary.items() if k != v)
        attribution[period] = {
            "oldIcbsRemapped": {k: primary[k] for k in remapped},
            "practicesResolvedIndividually": len(exceptions),
            "itemsFromPracticesAbsentFromLatestMonth": carried,
        }

        g = group_expr(exceptions)
        q_main = ("SELECT %s AS g, BNF_CHEMICAL_SUBSTANCE_CODE AS s, "
                  "SUBSTR(BNF_PRESENTATION_CODE, 1, 13) AS p, SUM(ITEMS) AS i, "
                  "SUM(ACTUAL_COST) AS k FROM `%s` GROUP BY 1, 2, 3" % (g, table))
        rows = run_sql(table, q_main)
        got_i = collections.Counter()
        got_c = collections.Counter()
        for r in rows:
            sub, code13 = r["s"], r["p"]
            if not sub or not code13 or not code13.startswith(sub):
                continue
            icb = resolve(r["g"], primary, exceptions)
            key = code13            # collapsed to the product code at write time
            it = int(float(r["i"] or 0))
            ct = float(r["k"] or 0)
            items[sub][icb][key][i] += it
            cost[sub][icb][key][i] += ct
            got_i[code13[:4]] += it
            got_c[code13[:4]] += ct

        # Names and the server-side section totals the rows must reconcile to.
        q_names = ("SELECT SUBSTR(BNF_PRESENTATION_CODE, 1, 13) AS p, "
                   "BNF_PRESENTATION_NAME AS n, BNF_CHEMICAL_SUBSTANCE_CODE AS s, "
                   "BNF_CHEMICAL_SUBSTANCE AS sn, SUM(ITEMS) AS i FROM `%s` "
                   "GROUP BY 1, 2, 3, 4" % table)
        for r in run_sql(table, q_names):
            names[r["p"]][(r["n"] or "").strip()] += int(float(r["i"] or 0))
            sub_names.setdefault(r["s"], (r["sn"] or "").strip())
        q_tot = ("SELECT SUBSTR(BNF_PRESENTATION_CODE, 1, 4) AS sec, SUM(ITEMS) AS i, "
                 "SUM(ACTUAL_COST) AS k FROM `%s` GROUP BY 1" % table)
        bad = []
        for r in run_sql(table, q_tot):
            sec = r["sec"]
            ti, tc = int(float(r["i"] or 0)), float(r["k"] or 0)
            sec_totals[sec]["i"][i] = ti
            sec_totals[sec]["c"][i] = round(tc, 2)
            if got_i[sec] != ti or abs(got_c[sec] - tc) > 0.5:
                bad.append("%s items %d/%d cost %.2f/%.2f" % (sec, got_i[sec], ti,
                                                               got_c[sec], tc))
        if bad:
            raise RuntimeError("%s did not reconcile to the server totals (a short "
                               "download?): %s" % (period, "; ".join(bad[:5])))
        print("  %s  %7d rows  %d practices resolved individually  %d carried  (%.0fs)"
              % (period, len(rows), len(exceptions), carried, time.time() - t0))

    # ---- write ------------------------------------------------------------
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if re.fullmatch(r"s-\d{4}\.json", f):
            os.remove(os.path.join(outdir, f))
    miss_idx = [pidx[p] for p in missing]

    def blank(arr):
        """Null out the months NHSBSA did not publish. Never zero."""
        out = list(arr)
        for j in miss_idx:
            out[j] = None
        return out

    # SIZE (measured 29/09/2026, all chapters, 13 months): cost per ICB per PRODUCT
    # made the dataset 47.8 MB, 30 MB of it the appliance chapters 20-23. So, as in
    # the hospital tool, cost is kept per ICB per SUBSTANCE, and per PRODUCT only
    # nationally ("nc"). Items stay per ICB per product, which is what brand share
    # by ICB needs. Result ~23 MB across ~200 section shards; a panel loads one or two.
    pcode = product_codes(names)
    split = sorted({v[:11] for v in pcode.values() if len(v) == 13})
    print("  %d catch-all 11-character codes counted per 13-character product" % len(split))
    prod_names = collections.defaultdict(collections.Counter)
    for c13, counter in names.items():
        prod_names[pcode[c13]].update(counter)

    def collapse(by13, cby13):
        """Rule 2b applied: sum 13-character rows into their product code."""
        it_out = collections.defaultdict(lambda: [0] * n)
        ct_out = collections.defaultdict(lambda: [0.0] * n)
        for c13, arr in by13.items():
            pc = pcode.get(c13, c13[:11])
            for j in range(n):
                it_out[pc][j] += arr[j]
                ct_out[pc][j] += cby13[c13][j]
        return it_out, ct_out

    shards = collections.defaultdict(dict)
    catalogue = []
    for sub in sorted(items):
        t_out, c_out, keys, total = {}, {}, set(), 0
        nat_cost = collections.defaultdict(lambda: [0.0] * n)
        for icb in sorted(items[sub]):
            by_pc, cost_pc = collapse(items[sub][icb], cost[sub][icb])
            by_key = {product_key(sub, pc): arr for pc, arr in by_pc.items()}
            cost_key = {product_key(sub, pc): arr for pc, arr in cost_pc.items()}
            ti, csum = {}, [0.0] * n
            for key in sorted(by_key):
                arr = by_key[key]
                carr = cost_key[key]
                if not any(arr) and not any(abs(v) >= 0.005 for v in carr):
                    continue
                ti[key] = blank(arr)
                for j in range(n):
                    csum[j] += carr[j]
                    nat_cost[key][j] += carr[j]
                keys.add(key)
                total += sum(arr)
            if ti:
                t_out[icb] = ti
                c_out[icb] = blank([round(v, 2) for v in csum])
        if not t_out:
            continue
        prods = {}
        for key in sorted(keys):
            top = prod_names[sub + key].most_common(1)
            prods[key] = label_of(top[0][0]) if top else sub + key
        appliance = sub[:2] in APPLIANCE_CHAPTERS
        g = None if appliance else any(k[:2] == "AA" for k in keys)
        sec = sub[:4]
        shards[sec][sub] = {"n": sub_names.get(sub, sub), "g": g, "p": prods,
                            "t": t_out, "c": c_out,
                            "nc": {k: blank([round(v, 2) for v in nat_cost[k]])
                                   for k in sorted(keys)}}
        generic_labels = {v for k, v in prods.items() if not appliance and k[:2] == "AA"}
        brands = sorted({v for k, v in prods.items()
                         if (appliance or k[:2] != "AA") and v and v not in generic_labels})
        row = {"c": sub, "n": sub_names.get(sub, sub), "sec": sec, "g": g,
               "i": total, "icbs": len([k for k in t_out if k != UNIDENTIFIED])}
        if brands:
            row["b"] = brands
        catalogue.append(row)

    total_bytes = 0
    for sec, subs in sorted(shards.items()):
        path = os.path.join(outdir, "s-%s.json" % sec)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"periods": periods, "section": sec, "s": subs}, f,
                      separators=(",", ":"))
        total_bytes += os.path.getsize(path)

    catalogue.sort(key=lambda r: -r["i"])
    index = {
        "generatedOn": time.strftime("%Y-%m-%d"),
        "source": {
            "name": "NHSBSA Open Data: English Prescribing Dataset (EPD) with SNOMED code",
            "package": PACKAGE,
            "url": "https://opendata.nhsbsa.net/dataset/%s" % PACKAGE,
            "api": "%s/datastore_search_sql" % CKAN,
            "licence": LICENCE,
            "attribution": ATTRIBUTION,
        },
        "scope": ("Items prescribed in primary care in England (GP practices and other "
                  "prescribers NHSBSA attributes to a practice) and dispensed in the "
                  "community, aggregated to ICB. Not hospital in-patient use, and not "
                  "the trust-level hospital prescribing dataset."),
        "rules": {
            "substance": "NHSBSA BNF_CHEMICAL_SUBSTANCE_CODE: BNF characters 1-9 for "
                         "chapters 01-19; the 4-character section for appliance "
                         "chapters 20-23.",
            "product": "BNF code characters 1-11. Shard key is the part after the "
                       "substance: characters 10-11 for chapters 01-19, where 'AA' is "
                       "the generic and any other pair is a brand; characters 5-11 for "
                       "chapters 20-23, where every product is a named proprietary "
                       "product and there is no generic (g is null). Exception: where "
                       "one 11-character code holds presentations whose labels do not "
                       "all start with the same word (BNF catch-alls such as 130201000BB, 'Other emollient "
                       "preparations', which holds Dermol, Doublebase, Aveeno, E45 and "
                       "more), each 13-character code is its own product and the key is "
                       "4 characters (e.g. 'BBIC'). Generic 'AA' codes are never split. "
                       "Split codes are listed in splitProducts.",
            "label": "The product's most common BNF_PRESENTATION_NAME in the window, "
                     "truncated at its first word that starts with a digit (a digit inside a brand word, as in E45, is kept).",
            "trend": "A percentage change is published only where the baseline month is "
                     "at or above %d items. Below that the tool prints 'too few to "
                     "trend' and no number." % MIN_BASELINE_ITEMS,
            "icb": "The 36 ICBs effective 01/04/2026, as NHSBSA's ICB_CODE carries them "
                   "in the latest month (NHSBSA derives it from the NHS ODS register). "
                   "Earlier months are re-attributed practice by practice to the ICB the "
                   "latest month places each practice in; a practice absent from the "
                   "latest month goes to the current ICB that took most of its old ICB. "
                   "'-' is NHSBSA's unidentified-prescriber bucket, kept so national "
                   "totals reconcile.",
            "cost": "ACTUAL_COST in pounds, as published by NHSBSA. Per ICB it is "
                    "summed to the substance ('c'); per product it is national only "
                    "('nc'), which keeps the dataset to a sane size.",
        },
        "minBaselineItems": MIN_BASELINE_ITEMS,
        "periods": periods,
        "missingPeriods": missing,
        "icbs": {k: icb_names.get(k, "") for k in sorted(
            {icb for sec in shards.values() for s in sec.values() for icb in s["t"]})},
        "icbAttribution": attribution,
        "sectionTotals": {sec: sec_totals[sec] for sec in sorted(sec_totals)},
        "sections": sorted(shards),
        "splitProducts": split,
        "substances": catalogue,
    }
    with open(os.path.join(outdir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"))
    total_bytes += os.path.getsize(os.path.join(outdir, "index.json"))
    print("  wrote %d section shards + index.json, %.1f MB total"
          % (len(shards), total_bytes / 1e6))
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=MONTHS)
    ap.add_argument("--out", default=os.path.join("data", "gp-prescribing"))
    ap.add_argument("--if-new", action="store_true",
                    help="exit without rebuilding when NHSBSA has published no month "
                         "newer than the one already in OUT/index.json")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    res = resources()
    if a.if_new:
        try:
            with open(os.path.join(a.out, "index.json")) as f:
                have = json.load(f)["periods"][-1]
        except Exception:
            have = None
        if res and have == res[-1][0]:
            print("no new month: NHSBSA latest is %s, already built. Nothing to do." % have)
            return
    idx = build(a.months, a.out, res=res)
    print("\nOK  %d substances across %d ICBs, %s to %s"
          % (len(idx["substances"]), len([k for k in idx["icbs"] if k != UNIDENTIFIED]),
             idx["periods"][0], idx["periods"][-1]))


if __name__ == "__main__":
    main()
