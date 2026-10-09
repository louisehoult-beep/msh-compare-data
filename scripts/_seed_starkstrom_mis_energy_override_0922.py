#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 22/09/2026.

Starkstrom Limited's own-site crawl (14 products) sits under one flat
"Uncategorised" division that is genuinely operating-theatre infrastructure
(isolated power supply systems, theatre control panels, operating tables,
lights, headlights, earthing/sockets, UPS, PACS) -- not minimally invasive
surgery equipment. One named product, "Electrosurgery - Starkstrom",
confirmed 22/09/2026 against its own product-detail page
starkstrom.com/product/electrosurgery/, is an electrosurgery generator
range -- an advanced energy-based device, matching mis:energy in the
"Minimally Invasive Surgery, Related Equipment and Accessories" framework's
own lot vocabulary (data/compare-suppliers.json).

The other 13 products (theatre infrastructure, not MIS) are NOT touched
here and stay held per the mixed-division-mapping policy.

Run once: python3 scripts/_seed_starkstrom_mis_energy_override_0922.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Starkstrom Limited"
NAME = "Electrosurgery – Starkstrom"

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
key = (SUPPLIER, NAME)
if key in known:
    print("already present, skipping:", NAME)
else:
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": NAME,
        "products": 1,
        "categories": [],
        "examples": [NAME],
        "hub": None,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": (
            "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
            "under the flat 'Uncategorised' division; confirmed 22/09/2026 by "
            "crawl_supplier_product_detail.py against the product's own detail page "
            "starkstrom.com/product/electrosurgery/, an electrosurgery generator range, "
            "matching mis:energy in data/compare-suppliers.json."
        ),
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
