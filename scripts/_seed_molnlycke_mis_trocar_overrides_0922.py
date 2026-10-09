#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 22/09/2026.

Molnlycke's own-site crawl (222 products) files by real site divisions, but
its "Or Solutions" division (operating-room products: drapes, gowns, gauze,
patient warming, PLUS a surgical-instruments sub-range) mixes several
specialities under one flat crawl division. Seven named products in that
division are unambiguously trocars, confirmed by their own product-detail
URLs on molnlycke.com, all filed under
/products/or-solutions/surgical-instruments/trocars/<name>: Veress Needles,
Balloon Fixation Trocars, Bladeless Trocars, Hasson Trocars, Optical
Trocars, Shielded Bladed Trocars, Trocar Cannulas. These match mis:trocar
("Trocars") in the "Minimally Invasive Surgery, Related Equipment and
Accessories" framework's own lot vocabulary (data/compare-suppliers.json).

The rest of "Or Solutions" (drapes, gowns, masks, patient warming, etc.) is
NOT touched here and stays held per the mixed-division-mapping policy.

Run once: python3 scripts/_seed_molnlycke_mis_trocar_overrides_0922.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Mölnlycke"

PRODUCTS = [
    "Veress Needles",
    "Balloon Fixation Trocars",
    "Bladeless Trocars",
    "Hasson Trocars",
    "Optical Trocars",
    "Shielded Bladed Trocars",
    "Trocar Cannulas",
]

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for name in PRODUCTS:
    key = (SUPPLIER, name)
    if key in known:
        print("already present, skipping:", name)
        continue
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": None,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": (
            "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
            "under the flat 'Or Solutions' division; confirmed 22/09/2026 by "
            "crawl_supplier_product_detail.py against the product's own detail page "
            "at molnlycke.com/en-gb/products/or-solutions/surgical-instruments/trocars/..., "
            "which names it a trocar product, matching mis:trocar in "
            "data/compare-suppliers.json."
        ),
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
