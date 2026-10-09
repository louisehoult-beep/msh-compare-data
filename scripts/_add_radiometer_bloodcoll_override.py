#!/usr/bin/env python3
"""One-off: add product-override entries for Radiometer UK's 3 "Blood Gas
Syringes And Capillaries" products (Safe Clinitubes, Self Fill, Aspirating).

These are capillary blood-gas sampling tubes/syringes, currently filed under
the division's own pathology:poct mapping (correct for the division's other
6 divisions, e.g. analysers), but these 3 are the collection device, not
testing equipment. Same shape as ICU Medical's 6 arterial-blood-gas products
(bloodcoll:abg addition, 07/09/2026) and the product-override tier that
exists exactly for this: one category for named products inside a division
that is correctly mapped to a different category for everything else.

Framework-coverage batch, Blood Collection Devices, 29/09/2026.
"""
import json

PATH = "data/differentiator-category-map.json"
PRODUCTS = ["Safe Clinitubes", "Self Fill", "Aspirating"]
WHY = (
    "Radiometer's capillary blood-gas sampling tubes/syringes (safeCLINITUBES "
    "range) — the collection device drawn at the bedside and fed into a "
    "blood-gas analyser, not the analyser or testing equipment itself. The "
    "'Blood Gas Syringes And Capillaries' division's other 6 divisions "
    "(Blood Gas Testing, Hematology, etc.) are correctly pathology:poct/equip "
    "analysers; these 3 products are the collection device and belong in "
    "bloodcoll:abg, same shape as ICU Medical's arterial-blood-gas product-"
    "override (07/09/2026)."
)

with open(PATH) as f:
    data = json.load(f)

existing = {(e.get("supplier"), e.get("division")) for e in data["entries"]}
added = []
for name in PRODUCTS:
    key = ("Radiometer UK", name)
    if key in existing:
        print("already present, skipping:", key)
        continue
    data["entries"].append({
        "kind": "product-override",
        "supplier": "Radiometer UK",
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": "bloodcoll:abg",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py; "
                    "found under the 'Blood Gas Syringes And Capillaries' division (mapped to "
                    "pathology:poct), which is right for the rest of the supplier's divisions "
                    "but wrong for these 3 collection-device products",
        "why": WHY,
        "decidedIn": "framework-coverage batch, Blood Collection Devices, 29/09/2026",
    })
    added.append(name)

with open(PATH, "w") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print("added", len(added), "entries:", added)
