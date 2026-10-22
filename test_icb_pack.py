#!/usr/bin/env python3
r"""ICB pack generator (scripts/build_icb_pack.py). Offline, stdlib only.

Added 22/10/2026 with the prototype. What it holds the generator to:

1. NO INVENTED FIGURES. A trend is printed only where the baseline month is at or
   above the repo floor (index.json minBaselineItems); an ICB with no sourced figure reads
   "Not verified", never a neighbour's number.
2. IMD. Recomputed from LSOA File 7 + ONS April 2026 lookup; must reproduce the
   official File 13 average score (to 0.01) on every ICB unchanged since 2024.
3. RECONCILIATION (only when the cache and a built pack exist locally, else SKIP):
   ICB dermatology RTT rows + the unknown-commissioner row = the National row;
   practice-level market items mapped to the ICB agree with the repo's ICB shard
   within 3% for the latest month; the page's share arithmetic recomputes.
4. CONTRAST. Heat-map text colour is white on dark cells, ink on light cells.

  python3 test_icb_pack.py        exit 0 = holds
"""
import importlib.util
import json
import os
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


# 1. trend floor
check(bip.trend([24, 100], 25) is None, "trend below floor must be None")
check(abs(bip.trend([25, 50], 25) - 100.0) < 1e-9, "trend at floor must compute")
check(bip.pct(1, 0) is None, "pct of zero must be None")
check(bip.num(None) == "Not verified", "missing number must read Not verified")
check(bip.cv([1, 1]) is None, "cv needs three values")

# 2. IMD name guard
check(bip.norm_icb("NHS Birmingham and Solihull Integrated Care Board")
      == bip.norm_icb("NHS BIRMINGHAM AND SOLIHULL INTEGRATED CARE BOARD"), "ICB names must normalise equal")
check(bip.norm_icb("NHS Essex ICB") != bip.norm_icb("NHS Mid and South Essex Integrated Care Board"),
      "a merged ICB must not match its predecessor")

# 4. contrast
bg, fg = bip.ramp(0, 0, 10)
check(fg == "#1D2733", "light cell must carry dark text")
bg, fg = bip.ramp(10, 0, 10)
check(fg == "#FFFFFF" and bg == "#14304F", "dark cell must carry white text")

# 3. data reconciliation
cache = os.path.join(HERE, "tmp", "icb-pack-cache")
pack = os.path.join(HERE, "out", "icb-pack", "icb-pack-QHL-QV.json")
if os.path.exists(os.path.join(cache, "sources.json")) and os.path.exists(pack):
    D = json.load(open(pack))
    rtt, _ = bip.load_rtt(cache)
    s = sum(v["total"] for k, v in rtt.items() if k != "ENGLAND")
    unknown = rtt["ENGLAND"]["total"] - s
    check(0 <= unknown < 0.01 * rtt["ENGLAND"]["total"], "ICB RTT rows must sum to within 1%% of England (gap %s)" % unknown)
    gmap, _ = bip.load_gpreg(cache)
    prac = json.load(open(os.path.join(cache, "epd-practice-months.json")))
    last = D["periods"][-1]
    via_practice = sum(v[0] for pr, v in prac[last].items() if gmap.get(pr, {}).get("icb") == "QHL")
    via_shard = D["icbs"]["QHL"]["mkt_items"][-1]
    check(abs(via_practice - via_shard) / via_shard < 0.03,
          "practice-level and shard market items disagree: %s vs %s" % (via_practice, via_shard))
    imd13 = bip.load_imd(cache)
    names = {bip.norm_icb(c["name"]): c for c in D["icbs"].values()}
    matched = 0
    # April 2026 mergers (index.json oldIcbsRemapped targets) plus Hampshire and Isle of Wight,
    # which took part of the old Frimley ICB: their boundaries differ from File 13's, so
    # they are not expected to reproduce it.
    changed = {"D7T5G", "S1Y5D", "T6Y0W", "Z9B2Z", "S0E4D", "S9B9J", "QRL"}
    for v in imd13.values():
        c = names.get(bip.norm_icb(v["name"]))
        if c and c["code"] not in changed:
            matched += 1
            check(abs(c["imd"]["avg_score"] - v["avg_score"]) < 0.01, "IMD recompute must reproduce File 13 for %s" % v["name"])
    check(matched >= 25, "expected at least 25 unchanged ICBs to reconcile with File 13, got %d" % matched)
    check(all(c["imd"] for c in D["icbs"].values()), "every current ICB must carry a recomputed IMD")
    I = D["icbs"]["QHL"]
    check(abs(I["share12"] - 100.0 * I["q12"] / I["m12"]) < 1e-9, "share must recompute")
    page = open(os.path.join(HERE, "out", "icb-pack", "icb-pack-QHL-QV.html")).read()
    for bad in ("nan", "None", "undefined"):
        check(">%s<" % bad not in page and (" %s " % bad) not in page, "page contains stray %r" % bad)
    check(all(w in page for w in ("Not verified", "Save edited copy", "contenteditable")), "page lacks core parts")
else:
    print("SKIP: no cache/pack present (run scripts/build_icb_pack.py first); unit checks only")

print("PASS" if not fails else "%d FAIL" % len(fails))
sys.exit(1 if fails else 0)
