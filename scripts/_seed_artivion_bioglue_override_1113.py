"""One-off seeder, framework-coverage batch 13/11/2026, working Wound
Closure (catsInScope: closure:adhes/haemo/stapler/strips/sutures).

Artivion UK Ltd was crawled fresh this run (artivion.com, 38 products, flat
'Uncategorised' division -- no per-page detail captured). Of its 38 named
products, "BioGlue (R)" is Artivion's albumin-glutaraldehyde surgical
sealant, used to control bleeding at suture lines in cardiovascular and
vascular surgery.

NHS Supply Chain's own Wound Closure Product Matrix by Lot (linked from the
framework's contract launch brief, read when Artivion's closure record was
first curated) already assigns Artivion UK Ltd to the Haemostats sub-lot
only (closure:haemo), not Tissue Adhesives (closure:adhes) -- see
compare-suppliers.json's existing "t": ["haemo"] entry for this supplier.
BioGlue is filed to closure:haemo to match that awarding-source assignment,
not guessed from the product's own marketing name alone.

Run once: python3 scripts/_seed_artivion_bioglue_override_1113.py
"""
import json

MAP = "data/differentiator-category-map.json"

WHY = (
    "BioGlue is Artivion's albumin-glutaraldehyde surgical sealant, used to "
    "control bleeding at suture lines in cardiovascular and vascular "
    "surgery. NHS Supply Chain's own Wound Closure Product Matrix by Lot "
    "already assigns Artivion UK Ltd to the Haemostats sub-lot only, so "
    "this is filed to match the awarding source rather than guessed from "
    "the product's marketing name."
)


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    key = ("Artivion UK Ltd", "BioGlue ®")
    if key in known:
        print("already present, skipping")
        return
    doc["entries"].append({
        "kind": "product-override",
        "supplier": "Artivion UK Ltd",
        "division": "BioGlue ®",
        "products": 1,
        "categories": ["Uncategorised"],
        "examples": ["BioGlue ®"],
        "hub": "closure:haemo",
        "notTaxonomy": False,
        "evidence": ("the supplier's own site filing (artivion.com), read "
                      "by scripts/crawl_supplier_site.py 13/11/2026."),
        "why": WHY,
        "decidedIn": "framework-coverage batch, Wound Closure, 13/11/2026",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    with open(MAP, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("added 1 product-override entry")


if __name__ == "__main__":
    main()
