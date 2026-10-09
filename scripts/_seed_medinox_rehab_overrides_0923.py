#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 23/09/2026.

Medinox (London) Limited's own-site crawl (234 products) sits under one flat
"Uncategorised" division spanning OTC pharmacy items, wound plasters,
kinesiology tape, PPE, sutures, monitoring devices and mobility/rehab
equipment -- so the whole division cannot take one hub tag
(mixed-division-mapping policy, data/identity-vocabulary-policy.json).

Ten named products on the record are unambiguously physiotherapy/occupational-
therapy mobility, transfer and hygiene aids, matching the "Physiotherapy and
Occupational Therapy" framework's own scope: walking aids (rollators, walking
frame, walking stick, elbow crutch), a wheelchair, and bathing/toileting aids
(shower chair, mobile commode), plus a named myofascial-release therapy tool.

The remaining 224 products in the division (OTC pharmacy, wound plasters,
elasticated/neoprene joint supports, sutures, PPE, monitoring devices) are NOT
touched here and stay held per the mixed-division-mapping policy: their own
names identify other specialities (orthotics, wound, pathology/monitoring,
PPE) out of scope for this batch, not rehab.

Run once: python3 scripts/_seed_medinox_rehab_overrides_0923.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Medinox (London) Limited"

# name -> hub
PRODUCTS = {
    "Folding Rollator Walking Frame – Front Wheels": "rehab:walk",
    "Foldable Walker": "rehab:walk",
    "Rollator": "rehab:walk",
    "Walking Stick – Quad Straight": "rehab:walk",
    "Aluminium Walking Stick": "rehab:walk",
    "Elbow Crutch – Per Unit": "rehab:walk",
    "Basic Wheelchair": "rehab:chair",
    "Shower Chair With Backrest": "rehab:bath",
    "Mobile Commode – Including Wheels": "rehab:bath",
    "mx Health Myofascial Release Tool": "rehab:therapy",
}

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for name, hub in PRODUCTS.items():
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
            "under the flat 'Uncategorised' division; confirmed 23/09/2026 that this "
            "is a named mobility/transfer/hygiene or therapy product unambiguously "
            "within the 'Physiotherapy and Occupational Therapy' framework's own "
            "scope (rehab:%s)." % hub.split(":", 1)[1]
        ),
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
