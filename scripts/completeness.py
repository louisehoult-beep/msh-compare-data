#!/usr/bin/env python3
"""
completeness.py — the gap report.

For every company, and (separately, coarsely) every speciality, report what the
GBUK/Jeenie 19-section deep-dive standard needs, what already exists, and where it
came from: assembled from a Tier 1 data store with no new research, sitting in an
existing `deepDive` editorial record, or absent.

v1, built 20/08/2026 per audit recommendation #3 (HUB-INTELLIGENCE-ARCHITECTURE-AUDIT-
2026-08-18.md). This is a first pass against the data as it stands, not the full
ledger-backed completeness checker the audit specifies for phase 4 (`verify.py`
integration) — it reads the existing five Tier 1 stores directly by supplier name,
which means it inherits their known alias/attribution gaps (see audit §1.2, §3).
Re-run after entity resolution widens (audit §3.1) for a cleaner number.

Usage:
    python3 scripts/completeness.py                 # full run, all suppliers, summary only
    python3 scripts/completeness.py --sample 20      # N-supplier sample with per-section detail
    python3 scripts/completeness.py --out FILE.json  # write full per-supplier report as JSON
"""
import json
import random
import argparse
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# The 19 GBUK/Jeenie sections, each tagged with how it CAN be filled:
#   "tier1"     — assembled from a Tier 1 store, no judgement needed
#   "editorial" — needs a Claude/human session even when raw material exists
SECTIONS = [
    ("identity",          "tier1",     "name, domain, brand — supplier-seed.json"),
    ("ch_status",         "tier1",     "Companies House status/number — company-financials.json"),
    ("turnover",          "tier1",     "filed turnover — company-financials.json"),
    ("employees",         "tier1",     "filed headcount — company-financials.json"),
    ("officers",          "tier1",     "officers/PSC — company-financials.json"),
    ("frameworks",        "tier1",     "NHSSC framework membership — frameworks.json"),
    ("own_product_range", "tier1",     "own-site crawl — supplier-product-detail.json / supplier-products.json"),
    ("nhssc_catalogue",   "tier1",     "NHS Supply Chain catalogue presence — nhssc-cache.json"),
    ("press",             "tier1",     "matched press items — company-press.json"),
    ("lede",              "editorial", "opening editorial framing"),
    ("stats",             "editorial", "curated stat panel (may draw on turnover/employees)"),
    ("growth_series",     "editorial", "multi-year growth narrative"),
    ("ownership",         "editorial", "ownership/parent narrative"),
    ("people",            "editorial", "leadership narrative"),
    ("people_note",       "editorial", "people/succession footnote"),
    ("hiring",            "editorial", "hiring signal narrative"),
    ("market_position",   "editorial", "competitive position narrative"),
    ("glassdoor",         "editorial", "Glassdoor rating/review synthesis"),
    ("interview",         "editorial", "interview-prep angle"),
]
TIER1_SECTIONS = [s for s, kind, _ in SECTIONS if kind == "tier1"]
EDITORIAL_SECTIONS = [s for s, kind, _ in SECTIONS if kind == "editorial"]


def load(name):
    return json.load(open(DATA / name))


def build_indexes():
    seed = load("supplier-seed.json")["suppliers"]
    fin = load("company-financials.json")["companies"]
    fw = load("frameworks.json")["frameworks"]
    pd = load("supplier-product-detail.json")["products"]
    nhssc = load("nhssc-cache.json")["products"]
    press = load("company-press.json")["suppliers"]

    fw_suppliers = set()
    for f in fw:
        for s in f.get("suppliers", []) or []:
            fw_suppliers.add(s if isinstance(s, str) else s.get("name"))

    pd_suppliers = set(v.get("supplier") for v in pd.values())
    nhssc_suppliers = set(v.get("supplier") for v in nhssc.values() if isinstance(v, dict))

    return seed, fin, fw_suppliers, pd_suppliers, nhssc_suppliers, press


def assess(supplier, fin, fw_suppliers, pd_suppliers, nhssc_suppliers, press):
    name = supplier.get("name")
    result = {}

    result["identity"] = bool(name)

    finrec = fin.get(name)
    result["ch_status"] = bool(finrec and finrec.get("status"))
    result["turnover"] = bool(finrec and finrec.get("turnoverGBP") is not None)
    result["employees"] = bool(finrec and finrec.get("employees") is not None)
    result["officers"] = bool(finrec and finrec.get("officers"))

    result["frameworks"] = bool(supplier.get("frameworks")) or (name in fw_suppliers)
    result["own_product_range"] = bool(supplier.get("products")) or (name in pd_suppliers)
    result["nhssc_catalogue"] = name in nhssc_suppliers

    pressrec = press.get(name)
    result["press"] = bool(pressrec and pressrec.get("items"))

    dd = supplier.get("deepDive") or {}
    for sec in EDITORIAL_SECTIONS:
        key = {"people_note": "peopleNote", "growth_series": "growth"}.get(sec, sec)
        result[sec] = bool(dd.get(key))

    result["_has_deep_dive"] = bool(dd)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260820)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    seed, fin, fw_suppliers, pd_suppliers, nhssc_suppliers, press = build_indexes()

    all_results = {}
    for s in seed:
        name = s.get("name")
        if not name:
            continue
        all_results[name] = assess(s, fin, fw_suppliers, pd_suppliers, nhssc_suppliers, press)

    n = len(all_results)
    has_dd = sum(1 for r in all_results.values() if r["_has_deep_dive"])

    # Aggregate Tier 1 fill rate across ALL suppliers (not just non-deep-dive ones)
    tier1_totals = {sec: 0 for sec in TIER1_SECTIONS}
    for r in all_results.values():
        for sec in TIER1_SECTIONS:
            if r[sec]:
                tier1_totals[sec] += 1

    print(f"Suppliers in supplier-seed.json: {n}")
    print(f"With a GBUK-standard deepDive record: {has_dd}")
    print()
    print("Tier 1 section fill rate across ALL suppliers (no new research required):")
    for sec, kind, desc in SECTIONS:
        if kind != "tier1":
            continue
        c = tier1_totals[sec]
        print(f"  {sec:20s} {c:5d}/{n}  ({c/n*100:5.1f}%)  — {desc}")

    if args.sample:
        no_dd = [name for name, r in all_results.items() if not r["_has_deep_dive"]]
        rng = random.Random(args.seed)
        sample_names = rng.sample(no_dd, min(args.sample, len(no_dd)))
        print()
        print(f"--- Sample of {len(sample_names)} suppliers WITHOUT a deep dive: Tier 1 section coverage ---")
        totals_by_supplier = []
        for name in sample_names:
            r = all_results[name]
            filled = [sec for sec in TIER1_SECTIONS if r[sec]]
            totals_by_supplier.append(len(filled))
            print(f"  {name:40s} {len(filled)}/{len(TIER1_SECTIONS)} tier1 sections: {', '.join(filled) if filled else '(none)'}")
        avg = sum(totals_by_supplier) / len(totals_by_supplier)
        print()
        print(f"Average Tier 1 sections fillable with no new research: {avg:.1f} / {len(TIER1_SECTIONS)} "
              f"tier1 sections ({avg/len(SECTIONS)*100:.0f}% of all 19 GBUK sections)")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(all_results, f, indent=1)
        print(f"\nFull per-supplier report written to {args.out}")


if __name__ == "__main__":
    main()
