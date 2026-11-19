#!/usr/bin/env python3
"""One-off: Helapet Ltd product-level overrides for Enteral Feeding, Bile Bags
and Associated Products (framework-coverage batch, 16/11/2026).

Helapet's own site (helapet.co.uk, crawled 16/11/2026) carries no usable
breadcrumb division -- all 153 products sit in one flat "Uncategorised"
range (data/supplier-products.json: hasDivisions false). Mixed-division-
mapping policy (data/identity-vocabulary-policy.json) applies: map at
PRODUCT level wherever the name alone settles the type, hold the rest.

16 products carry the company's own "Nutricair(TM)" enteral-feeding brand
name, or explicitly say "Enteral"/"ENFit" (the ISO 80369-3 enteral connector
standard) -- unambiguous without inference from the rest of Helapet's
catalogue (general syringes, wipes, PPE, etc., which stay held). Classified
by the product's own stated type, same vocabulary as the existing nutrition
category-map entries (Kimberly Clark feeding-tube kits -> nutrition:dev,
oral/Enfit syringes -> nutrition:syr, extension/giving sets -> nutrition:sets):
  - nutrition:syr  — the syringe itself, and its own cap (a syringe accessory)
  - nutrition:sets — gravity/pump giving sets (the delivery line)
  - nutrition:dev  — the feeding tube itself and every connector/adapter/cap
                      that attaches to the tube or feed container (not a
                      syringe, not a giving set)
"""
import json, sys
sys.path.insert(0, "scripts")
import seed_format

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/Helapet Ltd - product overrides 1116.json"
S = "Helapet Ltd"
SYR, SETS, DEV = "nutrition:syr", "nutrition:sets", "nutrition:dev"

GROUPS = [
 (SYR, "the enteral syringe itself, or a cap that is an accessory to that syringe", [
  "Nutricair™ ENFIT Enteral Single-Use Syringe (1ml – 50ml)",
  "Nutricair™ Snap-On ENFIT Syringe Cap (Push Fit – Sterile)",
 ]),
 (SETS, "a gravity or pump giving set -- the enteral feed delivery line", [
  "Nutricair™ Enteral Gravity Giving Sets",
  "Nutricair™ Enteral Pump Giving Sets",
 ]),
 (DEV, "the feeding tube itself, or a connector/adapter/cap that attaches to the feeding tube or feed container (not a syringe, not a giving set)", [
  "Nutricair™ Enteral Drug Sampling Vial Cap w/ ENFIT Connection Ø 20mm",
  "Nutricair™ Enteral Stepped Bottle Adapter w/ ENFIT Connection Ø 10-24.5mm",
  "Nutricair™ Screw Cap For Enteral Nutrition w/ ENFit Connection Ø 28mm",
  "Nutricair™ Enteral Cap for Feeding Tubes",
  "Nutricair™ Enteral Screw Cap For Baby Bottle Ø 39.4 mm w/ ENPlus Cross Port",
  "Nutricair™ 3-Way Enteral Stopcock (2 ENFit males, 1 ENFit female)",
  "Nutricair™ Enteral Feeding Tubes - Adults",
  "Nutricair™ Enteral Feeding Tubes - Neonatology / Paediatrics",
  "Nutricair™ Soft Funnel Adapter and Cap w/ Female ENfit Connector",
  "Nutricair™ Stepped Adapter w/ Male ENFit Connector and Cap",
  "Nutricair™ Enteral Y Port Adapter - 1 ENFit male, 1 funnel and 1 stepped connector",
  "Nutricair™ Enteral Y Port Adapter - 2 ENFit male and 1 ENFit female",
 ]),
]
EVIDENCE = ("Helapet Ltd's own storefront product records (helapet.co.uk), crawled "
            "16/11/2026 -- data/supplier-products.json. The product sits in the "
            "site's single non-taxonomy 'Uncategorised' range (no usable breadcrumb "
            "division), so it is mapped at product level by its own name.")
DECIDED = "framework-coverage-batch, 16/11/2026, Enteral Feeding, Bile Bags and Associated Products"

def main():
    prods = json.load(open("data/supplier-products.json"))["suppliers"][S]["products"]
    byname = {p["n"]: p for p in prods}
    doc = json.load(open(MAP))
    have = {(e["supplier"], e["division"]) for e in doc["entries"] if e.get("kind") == "product-override"}
    added, parts = 0, []
    for hub, why, names in GROUPS:
        for n in names:
            assert n in byname, "not in crawl: " + repr(n)
            parts.append({"division": n, "hub": hub, "why": why})
            if (S, n) in have:
                continue
            doc["entries"].append({"kind": "product-override", "supplier": S, "division": n, "products": 1,
                "categories": [byname[n]["division"]], "examples": [n], "hub": hub, "notTaxonomy": False,
                "evidence": EVIDENCE, "why": why, "decidedIn": DECIDED, "addedOn": "2026-11-16"})
            added += 1
    seed_format.write_like(MAP, doc)
    json.dump({"_note": "DOCUMENTATION ONLY -- product-override entries live in differentiator-category-map.json; merge_differentiator_parts.py cannot take product-name keys.",
               "supplier": S, "decisions": parts}, open(PART, "w"), indent=1, ensure_ascii=False)
    print("added", added, "product-override entries")
main()
