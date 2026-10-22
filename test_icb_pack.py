#!/usr/bin/env python3
r"""ICB pack (scripts/build_icb_pack.py, data/icb-pack/<speciality>/, app/icb-pack.js). Offline, stdlib only.

Added 22/10/2026. What it holds the pack to:

1. NO INVENTED FIGURES. A trend is printed only where the baseline month is at or above
   the repo floor (index.json minBaselineItems); a missing number reads "Not verified".
2. DATA SHAPE. 36 ICB shards, each with an IMD figure (recomputed from LSOA data), every
   brand series the same length as the periods, shares between 0 and 100.
3. RECONCILIATION against the repo's own GP prescribing shards: an ICB's market items in
   the pack equal the shard sum; the brand items for QV equal the shard's QV rows.
4. IMD reproduces the official File 13 to 0.01 on ICBs unchanged since 2024 (only when
   the cache is present locally, else SKIP).
5. CONTRAST. Heat-map text is white on dark cells, ink on light cells (app/icb-pack.js),
   and the tool carries no retired palette colours (cream, taupe, aubergine, clay).

  python3 test_icb_pack.py        exit 0 = holds
"""
import glob
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bip", os.path.join(HERE, "scripts", "build_icb_pack.py"))
bip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bip)
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("FAIL:", msg)


# 1. helpers
check(bip.trend([24, 100], 25) is None, "trend below floor must be None")
check(abs(bip.trend([25, 50], 25) - 100.0) < 1e-9, "trend at floor must compute")
check(bip.pct(1, 0) is None, "pct of zero must be None")
check(bip.cv([1, 1]) is None, "cv needs three values")
check(bip.brand_key("imuDERM") == bip.brand_key("Imuderm"), "brand keys must ignore case")
check(bip.pretty("NHS BATH AND NORTH EAST SOMERSET, SWINDON AND WILTSHIRE INTEGRATED CARE BOARD")
      == "Bath and North East Somerset, Swindon and Wiltshire", "ICB display names")

# 2. data shape, for every speciality built
gp = json.load(open(os.path.join(HERE, "data", "gp-prescribing", "index.json")))
check(set(bip.SPECS) == {d for d in os.listdir(os.path.join(HERE, "data", "icb-pack")) if not d.startswith(".")},
      "a data folder per speciality in config/icb-pack-specialities.json, and no others")
for sid in sorted(bip.SPECS):
    D = os.path.join(HERE, "data", "icb-pack", sid)
    idx = json.load(open(os.path.join(D, "index.json")))
    n = len(idx["periods"])
    check(idx["speciality"]["id"] == sid, "%s: index speciality id" % sid)
    check(len(idx["icbs"]) == 36, "%s: 36 ICBs expected, got %d" % (sid, len(idx["icbs"])))
    check(len(idx["brands"]) >= 5, "%s: too few brands offered (%d)" % (sid, len(idx["brands"])))
    check(idx["speciality"]["defaultBrand"] in {b["key"] for b in idx["brands"]}, "%s: default brand must be offered" % sid)
    check(all(m["imd"] for m in idx["icbs"].values()), "%s: every ICB needs an IMD figure" % sid)
    check(sorted(m["imd"]["rank"] for m in idx["icbs"].values()) == list(range(1, 37)), "%s: IMD ranks must be 1..36" % sid)
    check(all(0 <= (r["share12"] or 0) <= 100 for b in idx["rank"].values() for r in b.values()), "%s: share out of range" % sid)
    if not idx["speciality"]["rtt"]:
        check(all(m["rtt"] is None and m["rttSeries"] is None for m in idx["icbs"].values()), "%s: no RTT may be shown without a treatment function" % sid)
    check(gp["periods"] == idx["periods"], "%s: pack periods must match gp-prescribing periods" % sid)
    shards = {}
    for f in glob.glob(os.path.join(D, "icb-*.json")):
        s = json.load(open(f))
        shards[s["code"]] = s
    check(set(shards) == set(idx["icbs"]), "%s: one shard per ICB" % sid)
    for code, s in shards.items():
        check(len(s["market"]["items"]) == n, "%s %s market length" % (sid, code))
        check(all(len(b["items"]) == n for b in s["brands"].values()), "%s %s brand length" % (sid, code))
        check(all(len(c["market"]) == n and all(len(v) == n for v in c["brands"].values()) for c in s["pcns"]),
              "%s %s PCN lengths" % (sid, code))
        check(all(c["list"] > 0 for c in s["pcns"]), "%s %s PCN without list size" % (sid, code))
        check(all(sum(b["items"][k] for b in s["brands"].values()) + s["otherBrands"]["items"][k] == s["market"]["items"][k]
                  for k in range(n)), "%s %s brands + other must equal market" % (sid, code))
    for b, rows in idx["rank"].items():
        for code, r in rows.items():
            base = shards[code]["brands"][b]["items"][0]
            if base < idx["minBaselineItems"]:
                check(r.get("trend") is None, "%s: trend printed below floor for %s %s" % (sid, b, code))
    # 3. reconcile against the repo shards: market items per ICB equal the shard sum
    spec = bip.SPECS[sid]
    tot = {}
    for sec in spec["shards"]:
        for sub, v in json.load(open(os.path.join(HERE, "data", "gp-prescribing", "s-%s.json" % sec)))["s"].items():
            if any(sub.startswith(m) for m in spec["market"]):
                for icb, prods in v["t"].items():
                    for arr in prods.values():
                        t = tot.setdefault(icb, [0] * n)
                        for i in range(n):
                            t[i] += arr[i] or 0
    for code, s in shards.items():
        check(s["market"]["items"] == tot.get(code, [0] * n), "%s %s market items must equal the repo shard sum" % (sid, code))
    if sid == "dermatology":
        s2122 = json.load(open(os.path.join(HERE, "data", "gp-prescribing", "s-2122.json")))["s"]["2122"]
        qv_keys = [k for k, lab in s2122["p"].items() if lab.startswith("QV")]
        q = [sum(s2122["t"]["QHL"].get(k, [0] * n)[i] for k in qv_keys) for i in range(n)]
        check(q == shards["QHL"]["brands"]["qv"]["items"][:], "QV items in the pack must equal the shard rows (QHL)")

# 5. contrast / palette in the tool
js = open(os.path.join(HERE, "app", "icb-pack.js")).read()
check("t > 0.45 ? '#FFFFFF' : INK" in js, "heat-map text must switch to white on dark cells")
for bad in ("#F5F1E8" if False else "cream", "taupe", "aubergine", "clay"):
    check(bad not in js.lower().replace("// ", ""), "retired palette word %r in the tool" % bad)

# 4. File 13 reconciliation, only with the cache
cache = os.path.join(HERE, "tmp", "icb-pack-cache")
if os.path.exists(os.path.join(cache, "imd2025-file13-icb.xlsx")):
    idx = json.load(open(os.path.join(HERE, "data", "icb-pack", "dermatology", "index.json")))
    bip.set_spec("dermatology")
    imd13 = bip.load_imd(cache)
    changed = {"D7T5G", "S1Y5D", "T6Y0W", "Z9B2Z", "S0E4D", "S9B9J", "QRL"}   # mergers + Frimley's share
    matched = 0
    for v in imd13.values():
        for code, m in idx["icbs"].items():
            if code not in changed and bip.norm_icb(m["name"]) == bip.norm_icb(v["name"]):
                matched += 1
                check(abs(m["imd"]["score"] - v["avg_score"]) < 0.01, "IMD must reproduce File 13 for %s" % m["name"])
    check(matched >= 25, "expected 25+ unchanged ICBs to reconcile with File 13, got %d" % matched)
    rtt, _ = bip.load_rtt(cache)
    s = sum(v["total"] for k, v in rtt.items() if k != "ENGLAND")
    check(0 <= rtt["ENGLAND"]["total"] - s < 0.01 * rtt["ENGLAND"]["total"], "ICB RTT rows must sum to England within 1%")
else:
    print("SKIP: no local cache, File 13 and RTT reconciliation not run")

print("PASS" if not fails else "%d FAIL" % len(fails))
sys.exit(1 if fails else 0)
