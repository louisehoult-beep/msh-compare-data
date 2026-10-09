#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 24/09/2026, working Renal
Replacement Therapies Services, Technologies and Consumables (catsInScope:
renal:crrt/hd/pd).

MedScience Distribution is awarded on this framework and already publishes
315 products across 30+ divisions, but none is filed under a division that
maps to renal — its captured range sits in "Dressing Packs", "Pharmacy
Refrigerator" etc (mixed-division-mapping policy,
data/identity-vocabulary-policy.json: map at product level where the
product's own name unambiguously identifies its speciality).

One product in the "Dressing Packs" division, scanned by name for
renal/dialysis terms this run, unambiguously identifies as a haemodialysis
vascular-access procedure pack:

  "Fistula & Renal Procedure Packs – Sterile, Ready-to-Use Dialysis &
  Access Care Kits" -> renal:hd. "Fistula pack" / "renal procedure pack" is
  an established named product category for arteriovenous-fistula
  haemodialysis access (cross-checked 24/09/2026 against the same product
  category sold by other UK suppliers, e.g. 365healthcare.com's "Renal
  Packs / Fistula Packs" line and ITL BioMedical's "INTAGREL Dialysis
  Packs"), not a general surgical dressing pack.

The rest of MedScience's "Dressing Packs" division (Wound Care packs, other
procedure packs) and its other 29 divisions are NOT renal and are left
alone -- this is a single-product override, not a division remap.

Two other products in this supplier's range also name "Renal" (Concave
Round Neck Renal retractors, in the "Surgical Instruments & Accessories"
division) but are surgical retraction instruments for renal/nephrectomy
SURGERY, a different speciality from replacement-therapy dialysis access,
and are correctly left mapped to surgical:retract, out of scope for this
framework.

Run once: python3 scripts/_seed_medscience_renal_override_0924.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "MedScience Distribution"
PRODUCT = "Fistula & Renal Procedure Packs – Sterile, Ready-to-Use Dialysis & Access Care Kits"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the 'Dressing Packs' division; the product's own name "
    "('Fistula & Renal Procedure Packs – Sterile, Ready-to-Use Dialysis & "
    "Access Care Kits') unambiguously identifies a haemodialysis "
    "vascular-access procedure pack, confirmed 24/09/2026 against the same "
    "named product category sold by 365healthcare.com ('Renal Packs / "
    "Fistula Packs') and ITL BioMedical ('INTAGREL Dialysis Packs')."
)

WHY = (
    "fistula/renal procedure packs are the standard sterile field-prep kit "
    "for arteriovenous-fistula cannulation, the access route for "
    "haemodialysis -> renal:hd, per mixed-division-mapping policy "
    "(product-level mapping inside a generic 'Dressing Packs' division)."
)

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
key = (SUPPLIER, PRODUCT)
if key in known:
    print("already present, skipping")
else:
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": PRODUCT,
        "products": 1,
        "categories": [],
        "examples": [PRODUCT],
        "hub": "renal:hd",
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE,
        "why": WHY,
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    json.dump(doc, open(MAP, "w"), ensure_ascii=False)
    print("added 1 product-override entry")
