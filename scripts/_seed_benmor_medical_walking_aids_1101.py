#!/usr/bin/env python3
"""One-off: Benmor Medical product-level overrides for Aids for Daily Living, 01/11/2026.

Benmor Medical's own-site crawl (data/supplier-products.json, verified 2026-08-25)
returns 68 products in one flat "Uncategorised" division -- no real taxonomy, but
every name is a genuine, specific product name (not a navigation label), so the
mixed-division-mapping policy applies: map at product level wherever the name alone
unambiguously identifies the speciality, hold the remainder. 10 of the 68 are
unambiguous by name alone; the other 58 (hoists, slings, slide sheets, scales,
mattresses, bariatric beds/couches, care chairs) are patient-handling/pressure-care
equipment, out of this framework's catsInScope (rehab:access/bath/chair/daily/
hygiene/therapy/walk) and not reassessed here.
"""
import json

MAP = "data/differentiator-category-map.json"

ENTRIES = [
    # rehab:walk -- "Walking aids"
    ("Walking Frame with Wheels", "rehab:walk",
     "name is an explicit walking frame, the exact product type this framework "
     "(NHS Supply Chain's own title: \"Walking Aids and Simple Aids for Daily "
     "Living\") exists to cover"),
    ("Walking Sticks", "rehab:walk", "name is an explicit walking aid"),
    ("Walking Frames", "rehab:walk", "name is an explicit walking aid"),
    ("Elbow Crutches", "rehab:walk", "name is an explicit walking aid (crutches)"),
    # rehab:chair -- "Wheelchairs and specialist seating"
    ("Phoenix Heavy Duty Wheelchair", "rehab:chair",
     "name is an explicit wheelchair"),
    ("Goliath Heavy Duty Wheelchair", "rehab:chair",
     "name is an explicit wheelchair"),
    ("Wheelchair Powerpack", "rehab:chair",
     "name identifies it as a wheelchair accessory/power add-on, not an "
     "ambiguous product"),
    # rehab:bath -- "Bathing and toileting aids"
    ("Freeway Bariatric Commode", "rehab:bath",
     "a commode is a toileting aid by definition"),
    ("X399 Bariatric Commode with Footplates", "rehab:bath",
     "a commode is a toileting aid by definition"),
    ("Bariatric Bed Pan", "rehab:bath", "a bed pan is a toileting aid"),
]

EVIDENCE = ("Benmor Medical's own-site product catalogue (www.benmormedical.co.uk, "
            "WordPress REST API), read 2026-08-25 -- data/supplier-products.json. "
            "One flat 'Uncategorised' division, 68 named products, no real "
            "taxonomy; named per the mixed-division-mapping policy "
            "(data/identity-vocabulary-policy.json).")

def main():
    doc = json.load(open(MAP))
    existing = {(e.get("supplier"), e.get("division"), e.get("kind"))
                for e in doc["entries"]}
    added = 0
    for name, hub, why in ENTRIES:
        key = ("Benmor Medical", name, "product-override")
        if key in existing:
            print("skip (already present):", name)
            continue
        doc["entries"].append({
            "kind": "product-override",
            "supplier": "Benmor Medical",
            "division": name,
            "products": 1,
            "categories": ["Uncategorised"],
            "examples": [name],
            "hub": hub,
            "notTaxonomy": False,
            "evidence": EVIDENCE,
            "why": why,
            "decidedIn": "framework-coverage-batch, 01/11/2026, Aids for Daily Living",
        })
        added += 1
    json.dump(doc, open(MAP, "w"), ensure_ascii=False, separators=(",", ":"))
    print("added", added, "product-override entries for Benmor Medical")

if __name__ == "__main__":
    main()
