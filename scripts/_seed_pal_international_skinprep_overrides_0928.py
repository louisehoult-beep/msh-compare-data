#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 28/09/2026.

PAL International Ltd (palinternational.com, crawled fresh 28/09/2026 after
the domain was confirmed) files its whole catalogue under 4 flat divisions
that are the site's own filter FACETS, not real divisions -- "Considerations",
"Purpose", "Effective Against", "Category" -- mixing genuine patient skin-
cleansing/disinfection wipes with general surface/environmental disinfectant
wipes (a DIFFERENT NHSSC framework, "Wipes for Surface Cleaning and
Disinfection", which PAL is also awarded on), dry patient wipes, dispensers
and unrelated PPE/catering items (gloves, aprons, overshoes, hairnets,
masks, chef hats). No single division can take one hub tag
(mixed-division-mapping policy, data/identity-vocabulary-policy.json).

Only the 7 products whose own name unambiguously names them as a patient
SKIN (not surface) cleansing/disinfection product are mapped here, for the
"Skin Cleansing, Disinfection and Hygiene" framework
(catsInScope: skin-prep:disinfect/pack/prep/wipe; vocabulary: disinfect =
"Skin disinfectant (medicinal)", wipe = "Antimicrobial wipes & cleansing"):

- "Chlorhexidine & Alcohol skin wipes – single sachets x 100" names itself a
  SKIN wipe (medicinal chlorhexidine antiseptic) -> skin-prep:disinfect,
  the same shape as Molnlycke's Hibiclens/Hibiwash already mapped there.
- "Skin Cleansing Wash Cloths x 8", "Skin Cleansing Wash Mitts x 8",
  "Maceratable Skin Cleansing Wash Cloth x 50", "Antimicrobial Wash Cloths
  x 8", "Antimicrobial Wash Mitts x 8", "Hand Sanitising Wipes – 150 TUB"
  -> skin-prep:wipe, the same shape as Nine Group International's Alcohol
  Hand Gel / Medi9 Hand & Body Wipes already mapped there.

NOT mapped, left held (a different framework's scope, or too generic to
place unambiguously by name alone): "Chlorhexidine & Alcohol SURFACE wipes"
(named surface, not skin -- belongs on the Wipes for Surface Cleaning
framework, not this one), "Alcohol Wipes- 70% IPA", "Disinfectant wipes",
"IPA/Multisurface/Probe & Surface Disinfectant Wipes", "Multipurpose
Sanitizing Surface Wipes" (all explicitly surface/environmental, same other
framework), "Continence Care Wipes", "Maceratable Dry Wipes", "Dry Patient
Wipe Soft Pack", "Detergent wipes", "Hydrotek Dry Wipes" (patient wipes but
not named as antimicrobial/disinfecting, so not unambiguous), dispensers/
brackets, "Indicator Note"/"Clean Indicator Rolls" (cleaning-verification
indicators, not products), and all PPE/catering items (overshoes, aprons,
gloves, hairnets, masks, chef/catering hats).

Run once: python3 scripts/_seed_pal_international_skinprep_overrides_0928.py
"""
import json

from seed_format import write_like, describe

MAP = "data/differentiator-category-map.json"
SUPPLIER = "PAL International Ltd"

EVIDENCE = (
    "palinternational.com (crawled 28/09/2026). PAL's own site files this "
    "product under a filter facet (Considerations/Purpose/Effective "
    "Against/Category), not a real division, so the division-level map "
    "cannot be used (mixed-division-mapping policy) -- decided at product "
    "name level instead, against the same precedent already mapped for "
    "other suppliers in this file (Molnlycke's Hibiclens/Hibiwash under "
    "skin-prep:disinfect; Nine Group International's Alcohol Hand Gel / "
    "Medi9 Hand & Body Wipes under skin-prep:wipe)."
)

PRODUCTS = {
    "Chlorhexidine & Alcohol skin wipes – single sachets x 100": (
        "skin-prep:disinfect",
        "names itself a SKIN wipe with a medicinal chlorhexidine/alcohol "
        "antiseptic formulation, distinct from PAL's separate 'surface "
        "wipes' SKU of the same chemistry (left held: named surface, not "
        "skin).",
    ),
    "Skin Cleansing Wash Cloths x 8": (
        "skin-prep:wipe",
        "names itself a skin cleansing product.",
    ),
    "Skin Cleansing Wash Mitts x 8": (
        "skin-prep:wipe",
        "names itself a skin cleansing product.",
    ),
    "Maceratable Skin Cleansing Wash Cloth x 50": (
        "skin-prep:wipe",
        "names itself a skin cleansing product.",
    ),
    "Antimicrobial Wash Cloths x 8": (
        "skin-prep:wipe",
        "names itself an antimicrobial wash product, matching the "
        "vocabulary's own 'Antimicrobial wipes & cleansing' label for "
        "this type.",
    ),
    "Antimicrobial Wash Mitts x 8": (
        "skin-prep:wipe",
        "names itself an antimicrobial wash product, matching the "
        "vocabulary's own 'Antimicrobial wipes & cleansing' label for "
        "this type.",
    ),
    "Hand Sanitising Wipes – 150 TUB": (
        "skin-prep:wipe",
        "names itself a hand sanitising wipe, the same shape already "
        "mapped for Nine Group International's hand sanitiser products.",
    ),
}


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    added = 0
    for name, (hub, why) in PRODUCTS.items():
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
            "hub": hub,
            "notTaxonomy": False,
            "kind": "product-override",
            "evidence": EVIDENCE,
            "why": why,
        })
        added += 1
    fmt, round_trips = write_like(MAP, doc)
    print("added %d product-override entries for %s" % (added, SUPPLIER))
    print(describe(MAP, fmt, round_trips))


if __name__ == "__main__":
    main()
