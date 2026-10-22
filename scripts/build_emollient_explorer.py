#!/usr/bin/env python3
"""Emollient prescribing explorer data: month-by-month trends, presentation level,
ICB scope, and PCN / practice variation.

Feeds the "Prescribing explorer" block under the dermatology "who holds the market"
cards (app/speciality-panels.js). Built 22/10/2026 after a customer call (Ego
Pharmaceuticals, QV) asked for trends instead of single-month figures.

TWO OUTPUTS, TWO DIFFERENT SOURCES
----------------------------------
1. data/emollient-explorer/trends.json  (offline, no network)
   Built from data/gp-prescribing/ (NHSBSA English Prescribing Dataset with SNOMED
   code, already aggregated to the 36 ICBs effective 01/04/2026). Same BNF codes as
   the panel's emollient market (13.02.01 and 21.22), same brand rule (the first word
   of NHSBSA's product label, build_speciality_panels.brand_key), same ICB
   re-attribution (rule 5 of refresh_gp_prescribing.py). Every product (BNF product
   code, which is the presentation level: "QV cream" and "QV Intensive ointment" are
   different products) carries 13 monthly item counts nationally and per ICB.

2. data/emollient-explorer/pcn/<ICB code>.json  (needs network, --pcn)
   Practice-level items for the latest 12 months, from the same NHSBSA dataset
   (PRACTICE_CODE is a column; ICB aggregation in data/gp-prescribing/ throws it
   away), joined to Primary Care Network membership from the NHS England Organisation
   Data Service (ODS) Reference Data API (relationship RE8, practice to PCN). The
   dataset carries NO PCN column, so PCN membership is ODS's CURRENT membership
   applied to all 12 months: a practice that changed network in the window is shown
   in its current one. A practice is placed in its ICB as of the latest month (rule 5).
   Practices absent from the latest month cannot be placed and are counted, not hidden.

WHAT IS NEVER DONE
------------------
No estimate, no model, no imputation. A PCN with fewer than PCN_FLOOR emollient items
in 12 months shows no share. Share is share of ITEMS, never company share.

Usage:  python3 scripts/build_emollient_explorer.py [--pcn] [--out DIR]
"""

import argparse
import collections
import concurrent.futures
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_speciality_panels as bsp  # noqa: E402  brand_key, icb_display
import refresh_gp_prescribing as gpr  # noqa: E402  sql(), fetch()

PREFIXES = ("130201", "2122")
BRAND_PCN_N = 25          # brands carried in the PCN/practice files
PCN_FLOOR = 200           # emollient items in 12 months below which a PCN shows no share
PRACTICE_FLOOR = 50       # same, for a practice
PRODUCT_MIN_12M = 1       # products below this are folded away; 1 = keep everything
ODS = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
FORMS = (("ointment", r"\bointment\b"), ("cream", r"\bcream\b"), ("lotion", r"\blotion\b"),
         ("gel", r"\bgel\b"), ("wash / bath", r"\b(wash|bath|shower)\b"),
         ("spray", r"\bspray\b"), ("oil", r"\boil\b"))


def form_of(label):
    """Form read from the product label's own words. 'unspecified' where the label
    names none ('QV', 'Hydromol', 'White soft paraffin'): it is never guessed."""
    low = (label or "").lower()
    for name, rx in FORMS:
        if re.search(rx, low):
            return name
    return "unspecified"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def emollient_products(gp_root):
    """{pk: {label, generic, n:[..], icb:{code:[..]}}} over the emollient BNF codes."""
    ix = load(os.path.join(gp_root, "index.json"))
    n = len(ix["periods"])
    prod = {}
    secs = [s for s in ix["sections"] if any(s.startswith(p[:4]) for p in PREFIXES)]
    for sec in secs:
        doc = load(os.path.join(gp_root, "s-%s.json" % sec))
        for code, sub in doc["s"].items():
            if not code.startswith(PREFIXES):
                continue
            labels = sub.get("p") or {}
            for icb, by_key in (sub.get("t") or {}).items():
                for key, arr in by_key.items():
                    pk = code + key
                    rec = prod.setdefault(pk, {
                        "label": labels.get(key) or pk,
                        "generic": key.startswith("AA") and sub.get("g") is True,
                        "n": [0] * n, "icb": {}})
                    for m, v in enumerate(arr):
                        rec["n"][m] += v
                    if icb != "-":
                        a = rec["icb"].setdefault(icb, [0] * n)
                        for m, v in enumerate(arr):
                            a[m] += v
    return ix, prod


def build_trends(gp_root):
    ix, prod = emollient_products(gp_root)
    periods = ix["periods"]
    n = len(periods)
    fam = bsp._families(prod)
    brand_of = {}
    for f in fam.values():
        for pk in f["members"]:
            brand_of[pk] = f
    brands = []
    brand_idx = {}
    for key, f in sorted(fam.items(), key=lambda kv: -sum(sum(prod[p]["n"][-12:]) for p in kv[1]["members"])):
        it12 = sum(sum(prod[p]["n"][-12:]) for p in f["members"])
        if it12 < PRODUCT_MIN_12M:
            continue
        brand_idx[key] = len(brands)
        brands.append({"name": f["name"], "generic": key == "__generic__", "i12": int(it12)})
    products = []
    for pk, r in prod.items():
        f = brand_of[pk]
        if f["key"] not in brand_idx or sum(r["n"][-12:]) < PRODUCT_MIN_12M:
            continue
        products.append({
            "id": pk, "label": r["label"], "form": form_of(r["label"]),
            "b": brand_idx[f["key"]], "n": r["n"],
            "icb": {c: a for c, a in sorted(r["icb"].items()) if any(a)}})
    products.sort(key=lambda p: -sum(p["n"][-12:]))
    total = [sum(p["n"][m] for p in products) for m in range(n)]
    icb_total = collections.defaultdict(lambda: [0] * n)
    for p in products:
        for c, a in p["icb"].items():
            for m, v in enumerate(a):
                icb_total[c][m] += v
    names = ix.get("icbs") or {}
    icbs = [{"code": c, "name": bsp.icb_display(names.get(c, c))} for c in sorted(icb_total)]
    icbs.sort(key=lambda x: x["name"])
    src = ix.get("source") or {}
    return {
        "generatedOn": ix.get("generatedOn"),
        "periods": periods,
        "source": src.get("name"), "sourceUrl": src.get("url"),
        "attribution": src.get("attribution"),
        "scope": ix.get("scope"),
        "bnf": ["13.02.01", "21.22"],
        "minBaselineItems": ix.get("minBaselineItems") or 25,
        "total": total,
        "icbTotal": dict(sorted(icb_total.items())),
        "icbs": icbs,
        "brands": brands,
        "products": products,
    }


# --------------------------------------------------------------------------
# practice and PCN level
# --------------------------------------------------------------------------
def product_key_for(c13, split):
    """The shard product key (pk) for a 13-character presentation prefix, by the same
    rules refresh_gp_prescribing.py wrote the shards under (rules 1, 2 and 2b)."""
    if c13.startswith("2122"):
        return "2122" + c13[4:11]
    sub = c13[:9]
    if c13[:11] in split and c13[9:11] != "AA":
        return sub + c13[9:13]
    return sub + c13[9:11]


def ods_json(url):
    req = urllib.request.Request(url, headers=dict(gpr.UA, Accept="application/json"))
    last = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r), r.headers
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError("ODS fetch failed %s: %s" % (url, last))


def pcn_membership():
    """{practice code: (pcn code, pcn name)} and {pcn code: name}, from ODS RE8."""
    pcns, off = {}, 0
    while True:
        d, h = ods_json("%s?PrimaryRoleId=RO272&Limit=1000&Status=Active%s" % (ODS, "&Offset=%d" % off if off else ""))
        for o in d["Organisations"]:
            pcns[o["OrgId"]] = o["Name"]
        if len(d["Organisations"]) < 1000:
            break
        off += 1000

    def one(code):
        out, o = [], 0
        while True:
            d, _ = ods_json("%s?TargetOrgId=%s&RelTypeId=RE8&RelStatus=active&Limit=1000%s" % (ODS, code, "&Offset=%d" % o if o else ""))
            rows = d.get("Organisations") or []
            out += [r["OrgId"] for r in rows]
            if len(rows) < 1000:
                return code, out
            o += 1000

    member, dup = {}, 0
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for code, pr in ex.map(one, sorted(pcns)):
            for p in pr:
                if p in member and member[p] != code:
                    dup += 1
                member[p] = code
    return member, pcns, dup


def pcn_title(name):
    t = re.sub(r"\s+", " ", name or "").strip()
    keep = {"PCN": "PCN", "AND": "and", "OF": "of", "THE": "the", "NHS": "NHS", "GP": "GP"}
    return " ".join(keep.get(w, w.capitalize() if not re.search(r"\d", w) else w) for w in t.split())


def build_pcn(trends, gp_root, outdir):
    ix = load(os.path.join(gp_root, "index.json"))
    split = set(ix.get("splitProducts") or [])
    periods = ix["periods"][-12:]
    # brand of each product, same families as trends.json
    brand_of_pk = {p["id"]: p["b"] for p in trends["products"]}
    top = sorted(range(len(trends["brands"])), key=lambda i: -trends["brands"][i]["i12"])[:BRAND_PCN_N]
    col = {b: j for j, b in enumerate(top)}
    member, pcns, dup = pcn_membership()
    res = {p: n for p, n in gpr.resources()}
    latest = res[ix["periods"][-1]]
    q_prac = ("SELECT PRACTICE_CODE AS pr, ICB_CODE AS icb, MAX(PRACTICE_NAME) AS nm, "
              "SUM(ITEMS) AS i FROM `%s` GROUP BY PRACTICE_CODE, ICB_CODE" % latest)
    cur = {}
    for r in gpr.sql(latest, q_prac):
        cur[r["pr"]] = (r["icb"], (r["nm"] or "").strip())
    items = collections.defaultdict(lambda: [0] * (len(top) + 2))   # practice -> [top brands..., other, total]
    unmapped = 0
    for per in periods:
        tab = res[per]
        q = ("SELECT PRACTICE_CODE AS pr, SUBSTR(BNF_PRESENTATION_CODE,1,13) AS c13, SUM(ITEMS) AS i "
             "FROM `%s` WHERE BNF_PRESENTATION_CODE LIKE '130201%%' OR BNF_PRESENTATION_CODE LIKE '2122%%' "
             "GROUP BY PRACTICE_CODE, SUBSTR(BNF_PRESENTATION_CODE,1,13)" % tab)
        for r in gpr.sql(tab, q):
            v = int(float(r["i"] or 0))
            b = brand_of_pk.get(product_key_for(r["c13"], split))
            if b is None:
                unmapped += v
                continue
            row = items[r["pr"]]
            row[col[b] if b in col else len(top)] += v
            row[len(top) + 1] += v
    grand = sum(r[-1] for r in items.values())
    national12 = sum(trends["total"][-12:])
    if grand + unmapped != national12:
        # The practice query and the ICB shards are the same dataset; any gap is
        # reported, never papered over.
        print("NOTE: practice-level total %d + unmapped %d vs ICB-shard total %d"
              % (grand, unmapped, national12))
    by_icb = collections.defaultdict(lambda: collections.defaultdict(list))
    absent = noicb = 0
    for pr, row in items.items():
        if pr not in cur or cur[pr][0] == "-":
            absent += row[-1]
            continue
        icb, nm = cur[pr]
        by_icb[icb][member.get(pr, "")].append((pr, nm, row))
    os.makedirs(os.path.join(outdir, "pcn"), exist_ok=True)
    for old in os.listdir(os.path.join(outdir, "pcn")):
        os.remove(os.path.join(outdir, "pcn", old))
    names = {i["code"]: i["name"] for i in trends["icbs"]}
    nopcn = 0
    for icb, groups in sorted(by_icb.items()):
        plist = []
        for pcn, prs in sorted(groups.items(), key=lambda kv: kv[0]):
            tot = [sum(r[2][k] for r in prs) for k in range(len(top) + 2)]
            if not pcn:
                nopcn += tot[-1]
            plist.append({
                "id": pcn or "none",
                "name": pcn_title(pcns.get(pcn)) if pcn else "Not in a PCN on the ODS register",
                "b": tot[:-1], "t": tot[-1],
                "p": [{"c": pr, "n": nm.title() if nm.isupper() else nm, "b": row[:-1], "t": row[-1]}
                      for pr, nm, row in sorted(prs, key=lambda x: -x[2][-1])]})
        plist.sort(key=lambda x: (x["id"] == "none", -x["t"]))
        doc = {"icb": icb, "name": names.get(icb, icb), "window": [periods[0], periods[-1]],
               "brands": [trends["brands"][b]["name"] for b in top] + ["All other brands"],
               "pcnFloor": PCN_FLOOR, "practiceFloor": PRACTICE_FLOOR,
               "pcns": plist}
        with open(os.path.join(outdir, "pcn", icb + ".json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, separators=(",", ":"))
    meta = {"window": [periods[0], periods[-1]], "practicesWithItems": len(items),
            "itemsAtPracticeLevel": grand, "itemsInIcbShards12m": national12,
            "itemsNotPlacedInAnIcb": absent, "unmappedProductItems": unmapped,
            "itemsInPracticesWithNoPcn": nopcn, "practicesInTwoPcns": dup,
            "pcnsOnRegister": len(pcns), "pcnFloor": PCN_FLOOR, "practiceFloor": PRACTICE_FLOOR,
            "membershipSource": "NHS England ODS Reference Data API, relationship RE8 (practice is a member of PCN), active, read at build time",
            "membershipSourceUrl": "https://digital.nhs.uk/services/organisation-data-service/guidance-for-developers/organisation-reference-data-api",
            "membershipCaveat": "ODS membership is the current one, applied to all 12 months.",
            "practiceDataSource": "NHSBSA English Prescribing Dataset with SNOMED code, practice level (PRACTICE_CODE)"}
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcn", action="store_true", help="also build practice and PCN files (network)")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "emollient-explorer"))
    a = ap.parse_args()
    gp_root = os.path.join(ROOT, "data", "gp-prescribing")
    os.makedirs(a.out, exist_ok=True)
    t = build_trends(gp_root)
    tpath = os.path.join(a.out, "trends.json")
    if not a.pcn and os.path.exists(tpath):
        old = load(tpath)
        if old.get("pcn"):
            t["pcn"] = old["pcn"]          # keep the last PCN build's metadata
    if a.pcn:
        t["pcn"] = build_pcn(t, gp_root, a.out)
    with open(tpath, "w", encoding="utf-8") as fh:
        json.dump(t, fh, separators=(",", ":"))
    print("trends.json: %d products, %d brands, %d ICBs, %d bytes"
          % (len(t["products"]), len(t["brands"]), len(t["icbs"]), os.path.getsize(tpath)))
    if a.pcn:
        print(json.dumps(t["pcn"], indent=1))


if __name__ == "__main__":
    main()
