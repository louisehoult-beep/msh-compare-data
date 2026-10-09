"""One-off: add product-override entries for the genuinely electrosurgical
consumable products sitting in two suppliers' flat 'Uncategorised' catalogue
divisions, found while working the Electrosurgical Consumables and Related
Accessories framework (coverage batch, 27/09/2026).

Bolton Surgical Limited: 132 products, every one carrying "Monopolar",
"Bipolar", "Electrode" or "Diathermy" explicitly in its own name -- reusable
and single-use monopolar/bipolar forceps, disposable needle/ball/loop/
spatula/blade/knife electrodes, and diathermy generator-connector cables.
Unambiguous by name alone; the rest of Bolton's ~2,300-product Uncategorised
division (ENT hand instruments, gynae specula, etc.) is correctly left held,
per the mixed-division-mapping policy (data/identity-vocabulary-policy.json)
-- nothing here forces the ambiguous remainder.

Ideal Medical Solutions: 2 of its 41 flat range/brand names are genuinely
electrosurgical -- "THOR Electrodes" (THOR-brand disposable electrosurgery
pencil electrodes) and "Bipolar Forceps" -- confirmed by web search against
the supplier's own site (ideal-ms.com/product/thor-electrodes/). Its other
39 ranges (hernia mesh, wound gel, skin staplers, splints, etc.) are
correctly left mapped elsewhere / held, unaffected by this change.

All hub = theatres:electro ("Electrosurgery consumables"), which the
speciality's own routeNote names explicitly: "diathermy plates, pencils,
smoke evacuation, argon pencils, suction coagulators and forceps"
(data/compare-suppliers.json, theatres.routeNote).

Per-product detail pages captured this run (scripts/crawl_supplier_
product_detail.py) so each has a manufacturer source (Ideal Medical
Solutions' 2 already had source pages from an earlier, unrelated capture).
Run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"
WHY = ("Product name explicitly names it as a monopolar/bipolar/diathermy "
       "electrosurgery item -- theatres:electro (Electrosurgery "
       "consumables), the type this framework's own routeNote names "
       "(\"diathermy plates, pencils, smoke evacuation, argon pencils, "
       "suction coagulators and forceps\", data/compare-suppliers.json).")
EVIDENCE_BOLTON = ("the supplier's own site filing (boltons.co.uk), read by "
                   "scripts/crawl_supplier_site.py; product detail page "
                   "captured 27/09/2026 by "
                   "scripts/crawl_supplier_product_detail.py")
EVIDENCE_IDEAL = ("the supplier's own site filing (ideal-ms.com), read by "
                  "scripts/crawl_supplier_site.py; product detail page "
                  "already captured 2026-09-07 by "
                  "scripts/crawl_supplier_product_detail.py")


def bolton_names():
    d = json.load(open("data/supplier-products.json"))
    prods = d["suppliers"]["Bolton Surgical Limited"]["products"]
    names = []
    for p in prods:
        n = p.get("n", "")
        cat = (p.get("category") or "").lower()
        if "ear nose" in cat or "gu / gynaecology" in cat:
            continue
        if any(k in n.lower() for k in
               ("electro", "diathermy", "plume", "coagul", "bipolar",
                "monopolar", "cautery", "electrosurg")):
            names.append(n)
    return names


def main():
    d = json.load(open(PATH))
    existing = {(e.get("supplier"), e.get("division")) for e in d["entries"]}
    added = 0

    for name in bolton_names():
        key = ("Bolton Surgical Limited", name)
        if key in existing:
            continue
        d["entries"].append({
            "kind": "product-override",
            "supplier": "Bolton Surgical Limited",
            "division": name,
            "products": 1,
            "categories": [],
            "examples": [name],
            "hub": "theatres:electro",
            "notTaxonomy": False,
            "evidence": EVIDENCE_BOLTON,
            "why": WHY,
            "decidedIn": "_seed_bolton_ideal_electro_overrides_0927.py",
        })
        existing.add(key)
        added += 1

    for name in ("THOR Electrodes", "Bipolar Forceps"):
        key = ("Ideal Medical Solutions", name)
        if key in existing:
            continue
        d["entries"].append({
            "kind": "product-override",
            "supplier": "Ideal Medical Solutions",
            "division": name,
            "products": 1,
            "categories": [],
            "examples": [name],
            "hub": "theatres:electro",
            "notTaxonomy": False,
            "evidence": EVIDENCE_IDEAL,
            "why": WHY,
            "decidedIn": "_seed_bolton_ideal_electro_overrides_0927.py",
        })
        existing.add(key)
        added += 1

    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("added", added, "entries")


if __name__ == "__main__":
    main()
