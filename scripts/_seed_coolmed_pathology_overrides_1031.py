#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 31/10/2026.

Coolmed's own-site capture (data/supplier-products.json, domain
coolmed.co.uk) files its "Freezers" and "Medical Fridges" divisions as one
flat pharma:cold mapping each -- correct for most of their contents (general
medical/pharmacy fridges, vaccine carriers), but six products in those two
divisions name themselves "Laboratory ..." in the manufacturer's own product
title, the same shape already settled for Labcold's parallel "Laboratory
Refrigeration" division (-> pathology:equip) on this same framework earlier
in this run. Per the mixed-division-mapping policy
(data/identity-vocabulary-policy.json), a flat division mapping is never
blanket-correct for all of it; here the product's own name unambiguously
identifies six of them as laboratory equipment, so they are mapped at
product level, in ADDITION to the existing pharma:cold division mapping
(two categories per row, not a replacement -- these products are genuinely
both: pharmacy/medical-grade cold storage hardware, badged and sold by the
manufacturer specifically for laboratory use).

Two of the six (CMCF650, CMCF550) were already published under pharma:cold
with a manufacturer source on record. The other four had no per-product
detail and so were held in full; sourced live 31/10/2026 via
scripts/crawl_supplier_product_detail.py --supplier Coolmed --domain
coolmed.co.uk, each resolving to its own coolmed.co.uk page.

NOT touched: the rest of "Freezers" (-86C Ultra Low Temperature Freezers,
Portable Vaccine Carrier) and all of "Medical Fridges" except as listed --
none of those names itself as laboratory equipment, so they stay pharma:cold
only, as already mapped. Never widened from these six named products.

Run once: python3 scripts/_seed_coolmed_pathology_overrides_1031.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Coolmed"
HUB = ["pharma:cold", "pathology:equip"]

EVIDENCE = (
    "the product's own name on the supplier's own site (coolmed.co.uk), "
    "read by scripts/crawl_supplier_site.py (division mapping) and "
    "scripts/crawl_supplier_product_detail.py (per-product source, crawled "
    "live 31/10/2026 for the four not already sourced)"
)
WHY = (
    "the manufacturer's own product name identifies this unit as "
    "laboratory refrigeration/freezing equipment, the same shape as "
    "Labcold's Laboratory Refrigeration division on this framework -- "
    "mapped at product level per the mixed-division-mapping policy, "
    "additionally to (not instead of) the existing pharma:cold division "
    "mapping of 'Freezers'/'Medical Fridges'"
)

PRODUCTS = [
    "Laboratory Large Chest Freezer Sparkfree 567L CMCF650",
    "Laboratory Large Chest Freezer Sparkfree 473L CMCF550",
    "CMLFF260 Laboratory Combi Fridge Freezer",
    "Laboratory Fridge Solid Door CMLFR145",
    "Laboratory Freezer Solid Door CMLFZ115",
    "Laboratory Freezer Solid Door CMLFZ47",
]

doc = json.load(open(MAP))
entries = doc["entries"]
known = {(e["supplier"], e["division"]) for e in entries}
added = 0
for name in PRODUCTS:
    key = (SUPPLIER, name)
    if key in known:
        print("already present, skipping:", name)
        continue
    entries.append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": HUB,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE,
        "why": WHY,
    })
    added += 1

doc["counts"]["pairs"] = len(entries)
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries (hub=%s)" % (added, HUB))
