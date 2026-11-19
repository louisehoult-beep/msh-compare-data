#!/usr/bin/env python3
"""One-off: re-key Crest Medical Ltd's 872 category decisions from numeric
URL row ids to product-override entries on each product's own name.

Found 02/11/2026 when drug-tariff.yml (run 41482428133) refused to publish the
November Part IX update: rebuilding the product dossiers would drop 573
records, 562 of them Crest Medical wound/first-aid products (Advapore,
Advacare, Blue Dot kits, Pharmatull).

THE CAUSE. www.crestmedical.co.uk files every product at /product/<id>/<slug>.
The old crawl read <id> as a division, so each product sat in its own
"division" ("285", "286", ...), and the Crest decisions (decidedIn
Crest-Medical-Ltd.json) were made against those ids: one product per entry,
the product's name in `examples`. The 21/09/2026 crawler fix (^o564,
test_numeric_id_division.py) rightly stopped inventing divisions out of row
ids, so the re-crawl filed all 883 products under "Uncategorised". No entry
matched any more, and the 08/10/2026 Differentiator rebuild (ca8552a3)
published 2 Crest products instead of 867. verify.py's division-stability gate
did not catch it because it only checks breadcrumb-read suppliers.

THE FIX. Each numeric entry is a decision about ONE named product, so it is
exactly a product-override (see the `kinds` note in
differentiator-category-map.json): same hub, same why, division = the
product's own current name. Entries whose example name is no longer in
supplier-products.json, or that carry no hub, are dropped (they can never
match and a stranded override fails check_product_override_stability). A
name that already has a product-override (the 30/10/2026 orthotics batch)
keeps the newer decision. The numeric decisions also leave the parts file,
because merge_differentiator_parts.py refuses a division not in the worklist.

Usage: python3 scripts/_fix_crest_numeric_divisions_1102.py [--apply]
"""
import json
import re
import sys

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/Crest-Medical-Ltd.json"
SUPPLIER = "Crest Medical Ltd"
NUMERIC = re.compile(r"\d+")


def main():
    apply_it = "--apply" in sys.argv
    cmap = json.load(open(MAP))
    part = json.load(open(PART))
    names = {p.get("n") for p in
             json.load(open("data/supplier-products.json"))["suppliers"][SUPPLIER]["products"]}

    entries = cmap["entries"]
    overridden = {e["division"] for e in entries
                  if e.get("supplier") == SUPPLIER and e.get("kind") == "product-override"}
    kept, converted, dropped = [], 0, []
    for e in entries:
        if e.get("supplier") != SUPPLIER or not NUMERIC.fullmatch(str(e.get("division") or "")):
            kept.append(e)
            continue
        ex = e.get("examples") or []
        name = ex[0] if len(ex) == 1 else None
        if not e.get("hub") or name not in names or name in overridden:
            dropped.append((e["division"], name, e.get("hub")))
            continue
        overridden.add(name)
        e = dict(e)
        e["division"] = name
        e["kind"] = "product-override"
        e["evidence"] = (e.get("evidence", "") + "; re-keyed 02/11/2026 from the product's "
                         "URL row id to its own name after the re-crawl filed the range "
                         "under 'Uncategorised' (scripts/_fix_crest_numeric_divisions_1102.py)")
        kept.append(e)
        converted += 1

    before = len(part["decisions"])
    part["decisions"] = [d for d in part["decisions"]
                         if not NUMERIC.fullmatch(str(d.get("division") or ""))]

    print("converted to product-override: %d" % converted)
    print("dropped (no hub, name gone, or already overridden): %d" % len(dropped))
    for d in dropped:
        print("   ", d)
    print("parts file decisions: %d -> %d" % (before, len(part["decisions"])))
    if not apply_it:
        print("dry run - nothing written (pass --apply)")
        return 0
    cmap["entries"] = kept
    json.dump(cmap, open(MAP, "w"), ensure_ascii=False, indent=1)
    json.dump(part, open(PART, "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
