#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 23/09/2026.

Praxis Medical Ltd is a broad-line NHS distributor awarded across many
unrelated frameworks (catering, cleaning, IV cannula) and its own-site
catalogue is filed by product type across those same unrelated lines
(mixed-division-mapping policy, data/identity-vocabulary-policy.json). Its
"Electronic Pulse Stimulator" division (3 products) is unambiguously TENS/EMS
therapy equipment used in physiotherapy -- matching "Physiotherapy and
Occupational Therapy"'s rehab:therapy. No other division in the range is
rehab-related and none is touched here.

Run once: python3 scripts/_seed_praxis_medical_rehab_overrides_0923.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Praxis Medical Ltd"

PRODUCTS = [
    "Self-Adlhesire Electrode Pads MDPS100",
    "Mini Tens & EMS PL-029K9",
    "Electronic Pulse Stimulator MDTS100",
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
            "under the 'Electronic Pulse Stimulator' division; confirmed 23/09/2026 "
            "that this is a named TENS/EMS therapy device unambiguously within the "
            "'Physiotherapy and Occupational Therapy' framework's own scope "
            "(rehab:therapy)."
        ),
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
