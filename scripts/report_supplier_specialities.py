#!/usr/bin/env python3
"""
report_supplier_specialities.py — which specialities does a supplier ACTUALLY
sell into, judged by its products rather than by a framework listing.

A supplier belongs under every speciality it sells into, not one. The seed
records that as a list, but for most suppliers the list came from a framework
they were named on, and carries a _specialitiesEvidence note saying exactly that:
no product-level evidence. Interweave Textiles has 29 product divisions and one
recorded speciality. Oticon has 46.

Once a division is mapped to a Hub category, its products supply the missing
evidence: the set of specialities a supplier's mapped products land in IS the set
it sells into, each backed by named products and the source they were read from.

This reports, it does not write. A speciality added to a supplier's seed record
is a published claim about that company, so it goes in as a reviewed change with
its evidence, never as a side effect of a build.

  MISSING  the products prove a speciality the seed does not record
  UNPROVEN the seed records a speciality no mapped product supports — which may
           simply mean that part of the range is not mapped yet, so it is never
           a reason to remove anything

Usage:  python3 scripts/report_supplier_specialities.py [--json]
"""
import json, sys, collections


def main():
    diff = json.load(open("data/differentiator.json"))
    seed = {s["name"]: s for s in json.load(open("data/supplier-seed.json"))["suppliers"]}
    lmap = {e["label"]: e for e in
            json.load(open("data/speciality-label-map.json"))["entries"]}
    vocab = json.load(open("data/compare-suppliers.json"))["specialities"]

    proven = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in diff.get("products") or []:
        spec = (p.get("cat") or "").split(":")[0]
        if spec:
            proven[p["supplier"]][spec].append(p["name"])

    rows = []
    for co, specs in sorted(proven.items()):
        labs = (seed.get(co) or {}).get("specialities") or []
        recorded = set()
        for l in labs:
            e = lmap.get(l) or {}
            if e.get("slugs") and len(e["slugs"]) == 1:
                recorded.add(e["slugs"][0])
        missing = sorted(set(specs) - recorded)
        unproven = sorted(recorded - set(specs))
        rows.append({
            "supplier": co,
            "recorded": sorted(recorded),
            "proven": sorted(specs),
            "missing": missing,
            "unproven": unproven,
            "evidence": {s: specs[s][:4] for s in missing},
            "seedCaveat": bool((seed.get(co) or {}).get("_specialitiesEvidence")),
        })

    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return 0

    n_missing = sum(len(r["missing"]) for r in rows)
    print("%d supplier(s) have mapped products. %d speciality/ies are proven by "
          "product but not recorded on the seed.\n" % (len(rows), n_missing))
    for r in rows:
        if not r["missing"]:
            continue
        print("%s%s" % (r["supplier"], "   (seed carries an evidence caveat)"
                        if r["seedCaveat"] else ""))
        print("   recorded: %s" % (", ".join(r["recorded"]) or "none"))
        print("   proven  : %s" % ", ".join(r["proven"]))
        for s in r["missing"]:
            label = (vocab.get(s) or {}).get("label", s)
            print("   MISSING %-14s %s — e.g. %s"
                  % (s, label, "; ".join(r["evidence"][s][:3])))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
