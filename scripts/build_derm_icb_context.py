#!/usr/bin/env python3
"""Dermatology ICB context layers: RTT waiting time, deprivation, brand share and PCN
variation for all 36 ICBs, as one committed data file the dermatology speciality page
renders (app/speciality-panels.js, "ICB opportunity" panel).

Added 22/10/2026 after the Ego Pharmaceuticals call. Output: data/derm-icb-context/context.json
Check:  python3 test_derm_icb_context.py   (offline)

Sources (each figure in the file carries its source and period):
  RTT   NHS England, Referral to Treatment waiting times, "Incomplete Pathways, Commissioner"
        monthly workbook, ICB sheet, Treatment Function Code C_330 = "Dermatology Service"
        (read from the workbook's own columns, not assumed). Thirteen months.
  IMD   English Indices of Deprivation 2025 (MHCLG) File 7, LSOA to ICB (April 2026) by the
        ONS lookup: population-weighted mean IMD score. Recomputed in build_icb_pack.py,
        which test_icb_pack.py holds to the official File 13 on unchanged ICBs.
  Items NHSBSA English Prescribing Dataset, BNF 13.02.01 and 21.22 (data/emollient-explorer).

Nothing is estimated. An ICB created in April 2026 has no RTT rows before that month: its
earlier months are null, never borrowed from a predecessor. Share of ITEMS, not company share.

Usage: python3 scripts/build_derm_icb_context.py [--fetch] [--cache DIR]
  --fetch downloads the open files into the (git-ignored) cache first; needs the network.
"""
import argparse
import datetime
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_icb_pack as bip  # noqa: E402

EX = os.path.join(ROOT, "data", "emollient-explorer")
OUT = os.path.join(ROOT, "data", "derm-icb-context", "context.json")
TFC = "C_330"
PCN_MIN = 5          # PCNs above the floor needed before a spread is shown


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def pretty(name):
    return bip.pretty(name)


def build(cache):
    T = load(os.path.join(EX, "trends.json"))
    rtt_hist = bip.load_rtt_history(cache)
    periods = sorted(rtt_hist)
    imd = bip.load_imd_recomputed(cache)
    src = json.load(open(os.path.join(cache, "sources.json")))
    icbs = []
    n = len(T["periods"])
    brand_names = [b["name"] for b in T["brands"]]
    # brand items per ICB, 12 months, summed over the products of each brand family
    bitems = {}
    for p in T["products"]:
        for code, arr in p["icb"].items():
            bitems.setdefault(code, {}).setdefault(p["b"], 0)
            bitems[code][p["b"]] += sum(arr[-12:])
    top_brands = [b["name"] for b in T["brands"] if not b["generic"]][:25]
    for ic in T["icbs"]:
        code = ic["code"]
        tot12 = sum(T["icbTotal"][code][-12:])
        pcn_doc = load(os.path.join(EX, "pcn", code + ".json"))
        bnames = pcn_doc["brands"]
        brands = {}
        for bn in top_brands:
            bi = brand_names.index(bn)
            items = bitems.get(code, {}).get(bi, 0)
            rec = {"items12m": items, "share": round(100.0 * items / tot12, 2) if tot12 else None,
                   "pcnN": 0, "pcnMin": None, "pcnMax": None, "pcnSd": None}
            if bn in bnames:
                k = bnames.index(bn)
                sh = [100.0 * p["b"][k] / p["t"] for p in pcn_doc["pcns"]
                      if p["id"] != "none" and p["t"] >= pcn_doc["pcnFloor"]]
                rec["pcnN"] = len(sh)
                if len(sh) >= PCN_MIN:
                    rec["pcnMin"] = round(min(sh), 2)
                    rec["pcnMax"] = round(max(sh), 2)
                    rec["pcnSd"] = round(statistics.pstdev(sh), 2)   # percentage points
            brands[bn] = rec
        series = None
        if code in rtt_hist[periods[-1]]:
            def col(f):
                return [rtt_hist[q][code][f] if code in rtt_hist[q] else None for q in periods]
            tot, w18, w52, med = col("total"), col("w18"), col("w52"), col("median")
            series = {"total": tot, "median": [None if m is None else round(m, 2) for m in med],
                      "w18pct": [None if (t is None or not t) else round(100.0 * a / t, 1) for t, a in zip(tot, w18)],
                      "w52": w52}
        im = imd.get(code)
        icbs.append({"code": code, "name": ic["name"], "marketItems12m": tot12, "brands": brands,
                     "rtt": series, "rttFirstMonth": next((q for q, v in zip(periods, (series or {}).get("total", [])) if v is not None), None),
                     "imd": None if not im else {"score": round(im["avg_score"], 2), "rank": im["rank_avg_score"],
                                                 "prop10": round(100 * im["prop10"], 1), "population": round(im["population"])}})
    eng = [rtt_hist[q]["ENGLAND"] for q in periods]
    return {
        "generatedOn": datetime.date.today().isoformat(),
        "periods": {"rtt": periods, "items": [T["periods"][-12], T["periods"][-1]]},
        "brands": top_brands,
        "england": {"total": [e["total"] for e in eng], "median": [round(e["median"], 2) for e in eng],
                    "w18pct": [round(100.0 * e["w18"] / e["total"], 1) for e in eng], "w52": [e["w52"] for e in eng]},
        "imdCount": len(imd),
        "sources": {
            "rtt": {"name": "NHS England, Referral to Treatment (RTT) waiting times, incomplete pathways by commissioner",
                    "page": bip.RTT_PAGE, "treatmentFunctionCode": TFC, "treatmentFunction": "Dermatology Service",
                    "basis": "Commissioner (ICB sheet)", "licence": "Open Government Licence v3.0",
                    "measure": "Incomplete pathways (patients still waiting) at month end. Median is NHS England's 'Average (median) waiting time (in weeks)'. 18 weeks is the constitutional standard, so the share waiting under 18 weeks is shown.",
                    "latestFile": src.get("rtt")},
            "imd": {"name": "English Indices of Deprivation 2025 (MHCLG), File 7 LSOA scores and population, with the ONS LSOA (2021) to ICB (April 2026) lookup",
                    "page": "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025",
                    "measure": "Population-weighted mean IMD score (mid-2022 population). Higher = more deprived. Rank 1 = most deprived of the 36 ICBs. Share = percentage of the ICB's LSOAs in the most deprived 10% nationally.",
                    "method": "Recomputed for the April 2026 ICBs because MHCLG's own ICB file (File 13) uses the 2024 boundaries. The same method reproduces File 13 on every ICB unchanged since 2024 (test_icb_pack.py).",
                    "licence": "Open Government Licence v3.0"},
            "items": {"name": "NHSBSA English Prescribing Dataset with SNOMED code, BNF 13.02.01 and 21.22",
                      "page": T["sourceUrl"], "attribution": T["attribution"],
                      "measure": "Brand share = the brand's items as a share of all emollient items prescribed in the ICB, 12 months. PCN variation = standard deviation, in percentage points, of that share across the ICB's Primary Care Networks (PCNs) with at least %d emollient items in the 12 months (needs %d such PCNs). PCN membership is the current NHS England Organisation Data Service membership applied to all 12 months." % (load(os.path.join(EX, "pcn", "QHL.json"))["pcnFloor"], PCN_MIN)},
        },
        "icbs": icbs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--cache", default=os.path.join(ROOT, "tmp", "icb-pack-cache"))
    a = ap.parse_args()
    if a.fetch:
        bip.fetch_all(a.cache, refresh=True)
        bip.fetch_rtt_history(a.cache, refresh=True)
    doc = build(a.cache)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    print("wrote %s: %d ICBs, %d RTT months, %d bytes" % (OUT, len(doc["icbs"]), len(doc["periods"]["rtt"]), os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
