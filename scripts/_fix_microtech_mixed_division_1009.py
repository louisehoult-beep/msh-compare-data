"""One-off: replace the single Micro-Tech (UK) Ltd "Uncategorised" division
entry (decidedIn Micro-Tech-UK-Ltd--framework-coverage-0928.json) with
per-product overrides.

Found while working the Endoscopy, Endourology and Oncology Ablation
Consumables framework (coverage batch, 09/10/2026). The 28/09/2026 decision
mapped the WHOLE flat "Uncategorised" division to a LIST of five categories
(endoscopy:endo, endoscopy:access, endourology:stone, gastro:snare,
gastro:haem). build_differentiator.py's division-level match applies every
category in that list to EVERY product in the division (not "each product
picks the category its own name says" -- the mechanism purely locks one
category PER ROW, each row being one (product, category) pair from the
WHOLE list). The result, invisible while the supplier had no per-product
source (`capturedNothingCounted`), is that running
scripts/crawl_supplier_product_detail.py for this supplier this run (to give
each product a source) would have published all 56 products FIVE TIMES
EACH -- e.g. "EyeMAX Stone Extraction Basket" tagged simultaneously as
endoscopy:endo, endoscopy:access, endourology:stone, gastro:snare AND
gastro:haem, four of those five wrong for that specific product. This is
exactly the shape the mixed-division-mapping policy (ruled 20/09/2026, after
this decision was made) exists to prevent: "Map at PRODUCT level wherever
the product's own name unambiguously identifies its speciality, and hold
the remainder unmapped."

31 of the 56 products are reclassified individually below, each on an
unambiguous functional word in its own name (stent, snare/polypectomy,
stone extraction, haemostasis, retrieval/foreign body, or the general
endoscopy consumables -- biopsy forceps, guidewires, dilation balloons,
caps, cholangioscope, channel/valve sets -- the original entry's own "why"
text already named these correctly, just needed applying per-product
instead of blanket). The other 25 (brand-only names with no on-site
description -- SureFire, ToteTimer, ValveSafe, LesionHunter, SureTrac,
DiLumen variants, SureClip, Protrap Luma, DAT Closure Device -- plus
cleaning/reprocessing/apparel items and two borderline energy-device names,
Sphincterotome/Sphinx 3-Lumen Papillotome and GOLDKNIFE ESD Knife, and
sampling tools EUS Needles/Cytology Brushes/Injection Needles that do not
match gastro:diag's actual scope, "GI physiology & motility testing") stay
unmapped and held -- partial coverage of a mixed division is the correct
output here, not a gap to force.

Run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"

SUPPLIER = "Micro-Tech (UK) Ltd"
DOMAIN = "www.micro-tech-uk.com"
EVIDENCE = "the supplier's own site filing, read by scripts/crawl_supplier_site.py"
DECIDED_IN = "_fix_microtech_mixed_division_1009.py"

GROUPS = [
    ("endoscopy:endo",
     "General endoscopy consumable (biopsy forceps / guidewire / dilation "
     "balloon / cap / cholangioscope / channel valve), unambiguous from the "
     "product's own name -- same category the original 28/09/2026 division "
     "decision itself named for this product type, now applied per-product "
     "instead of blanket.",
     ["EyeMAX Biopsy Forceps", "TechBite Biopsy Forceps", "Hot Biopsy Forceps",
      "EyeMAX Distal Caps", "EyeMAX Cholangioscope",
      "SpiraTrax Guidewire", "Biliary Longwire Guidewires",
      "Biliary Shortwire Guidewires", "EUS Guidewires",
      "Locking Device Guidewire", "Dilation Guidewires",
      "Dilation Balloon Catheter", "Dilation Balloons",
      "Multi-Stage Dilation Balloons",
      "Disposable Channel Valves", "Disposable Endoscopy Valve Sets"]),
    ("endoscopy:access",
     "Access & retrieval device, unambiguous from the product's own name "
     "(retrieval / foreign-body / trap) -- same category the original "
     "decision named for this product type.",
     ["Foreign Body Forceps", "Retrieval Nets", "Polyp Trap"]),
    ("endourology:stone",
     "Stone retrieval & access device, unambiguous -- \"stone extraction\" "
     "is in the product's own name.",
     ["EyeMAX Stone Extraction Basket", "Stone Extraction Basket",
      "Stone Extraction Balloons", "Sweeper Stone Extraction Balloons"]),
    ("gastro:snare",
     "Snares & resection device, unambiguous -- \"snare\"/\"polypectomy\" "
     "is in the product's own name.",
     ["DailySnare", "Coldsnare", "ENDOx Polypectome"]),
    ("gastro:haem",
     "Haemostasis & banding device, unambiguous -- \"haemostasis\"/"
     "\"coagulation\" is in the product's own name.",
     ["Lockado™ Haemostasis Clip", "Ensure Coagulation Forceps"]),
    ("gastro:stent",
     "GI stents & dilatation, unambiguous -- \"Stent\" is in the product's "
     "own name (VacStent).",
     ["VacStent GI™ XL", "VacStent GI™ Colon", "VacStent GI™"]),
]


def main():
    d = json.load(open(PATH))
    entries = d["entries"]
    before = len(entries)
    entries = [e for e in entries
               if not (e.get("supplier") == SUPPLIER
                       and e.get("division") == "Uncategorised"
                       and e.get("kind") != "product-override")]
    removed = before - len(entries)

    added = 0
    for hub, why, names in GROUPS:
        for name in names:
            entries.append({
                "kind": "product-override",
                "supplier": SUPPLIER,
                "division": name,
                "products": 1,
                "categories": [],
                "examples": [name],
                "hub": hub,
                "notTaxonomy": False,
                "evidence": EVIDENCE,
                "why": why,
                "decidedIn": DECIDED_IN,
            })
            added += 1

    d["entries"] = entries
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("removed %d division-level entry, added %d product-overrides"
          % (removed, added))


if __name__ == "__main__":
    main()
