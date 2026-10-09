"""One-off seeder, framework-coverage batch 28/09/2026, working Endoscopy,
Endourology and Oncology Ablation Consumables (catsInScope includes
endoscopy:uro -> Endourology).

TSC Endovision is awarded on this framework and its captured range sits in
one 'Uncategorised' site bucket (mixed-division-mapping policy applies: map
at product level where the product's own name unambiguously identifies its
speciality, hold the remainder). The bucket holds ~7 distinct product lines
repeated across 20 captured rows:

  - Cystoflex -- confirmed (tsc-life.com/products/cystoflex/, web search
    28/09/2026) as TSC Life's single-use cystoscope -> endourology
    equipment, endoscopy:uro.
  - Broncoflex -- confirmed as TSC Life's single-use bronchoscope, an
    airway/respiratory endoscope, not a GI/urology device this framework's
    vocabulary covers (no matching type in endoscopy/endourology/gastro/
    oncology) -> genuine vocabulary gap, left unmapped rather than forced.
  - Fluido (Irrigation/Compact/Airguard System) and Mistral-Air -- confirmed
    as TSC Life's rapid-infusion/fluid-management and patient-warming lines,
    not endoscopy products at all -> correctly out of scope for this
    framework, left unmapped.

So only Cystoflex is promoted here, by product-override (the division's own
evidence cannot split it: one flat "Uncategorised" bucket holds an
endourology device beside unrelated respiratory-endoscopy and
warming/infusion lines).

Run once: python3 scripts/_seed_tsc_endovision_cystoflex_override_0928.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "TSC Endovision"
PRODUCT = "Cystoflex"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the 'Uncategorised' division; confirmed via tsc-life.com/products/"
    "cystoflex/ (web search 28/09/2026) as TSC Life's single-use cystoscope."
)

WHY = (
    "a single-use cystoscope is endourology diagnostic/therapeutic equipment "
    "-> endoscopy:uro, per mixed-division-mapping policy (product-level "
    "mapping inside a flat 'Uncategorised' division that also holds "
    "unrelated bronchoscopy, infusion and patient-warming lines)."
)


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    key = (SUPPLIER, PRODUCT)
    if key in known:
        print("already present, skipping")
        return
    doc["entries"].append({
        "kind": "product-override",
        "supplier": SUPPLIER,
        "division": PRODUCT,
        "products": 1,
        "categories": ["Uncategorised"],
        "examples": [PRODUCT],
        "hub": "endoscopy:uro",
        "notTaxonomy": False,
        "evidence": EVIDENCE,
        "why": WHY,
        "decidedIn": "_seed_tsc_endovision_cystoflex_override_0928.py",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    with open(MAP, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("added 1 product-override entry")


if __name__ == "__main__":
    main()
