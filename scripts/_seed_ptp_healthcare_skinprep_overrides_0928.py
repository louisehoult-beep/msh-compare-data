#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 28/09/2026.

PTP Healthcare Ltd (ptphealthcare.net, crawled fresh 28/09/2026 after the
domain was confirmed) files its whole catalogue under 4 flat divisions
(Hygiene, Patient Comfort, Grooming, Uncategorised) mixing genuine hand-
hygiene items with patient amenity/comfort products (soap, shampoo,
toothpaste, razors, slipper socks, pillowcases, briefs, deodorant, combs) and
PPE (facemasks, aprons) -- none of which is Skin Cleansing/Disinfection/
Hygiene-shaped, so the divisions cannot take one hub tag
(mixed-division-mapping policy, data/identity-vocabulary-policy.json).

Only the 6 products whose own name unambiguously names them as a hand
sanitiser are mapped here, for the "Skin Cleansing, Disinfection and
Hygiene" framework (catsInScope: skin-prep:disinfect/pack/prep/wipe). This
is the same shape already mapped for Nine Group International's Alcohol
Hand Gel / Uni9 Alcohol Hand Sanitiser products under skin-prep:wipe: a
hand sanitiser is a hand sanitiser regardless of alcohol content.

NOT mapped, left held (genuinely a different product, not this framework's
scope, or too generic to place unambiguously): Antimicrobial shampoo wrap,
Shampoo wraps, Shampoo cap, Nilaqua shampoo/body wash (hair/body washing,
not disinfection), Nilaqua Biodegradable Sachet Wipes (a generic personal
wipe, no disinfectant claim on its own name), Insette Deodorant, all patient
packs and comfort items (patient packs, eyeshades, bonnets, durags, hair
conditioner/shampoo for Afro hair, scalp oil, disposable bedsheets/
pillowcases/briefs, slipper socks), soap/toothbrush/toothpaste/razor/
grooming items, and Type I/II facemasks + polythene apron (PPE, a different
framework).

Run once: python3 scripts/_seed_ptp_healthcare_skinprep_overrides_0928.py
"""
import json

from seed_format import write_like, describe

MAP = "data/differentiator-category-map.json"
SUPPLIER = "PTP Healthcare Ltd"

EVIDENCE = (
    "ptphealthcare.net (crawled 28/09/2026) names this product a hand "
    "sanitiser in its own product title. Nine Group International's "
    "'Alcohol Hand Gel' and 'Uni9 Alcohol Hand Sanitiser Hand Pump Foam' "
    "are already mapped skin-prep:wipe in this file on the same basis -- a "
    "hand sanitiser is unambiguously a hand-hygiene product regardless of "
    "alcohol content, distinct from PTP's other Hygiene-division items "
    "(shampoo, body wash, soap, deodorant) which wash rather than "
    "sanitise and are left held."
)

PRODUCTS = {
    "Nilaqua 500ml Alcohol-Free Hand Sanitiser": "hand sanitiser, named as such.",
    "Nilaqua 55ml Alcohol-Free Hand Sanitiser": "hand sanitiser, named as such.",
    "Nilaqua 200ml Alcohol-Free Hand Sanitiser": "hand sanitiser, named as such.",
    "Nilaqua 100ml Alcohol-Free Hand Sanitiser": "hand sanitiser, named as such.",
    "Wax Lyrical alcohol hand sanitiser – 500ml": "hand sanitiser, named as such.",
    "Wax Lyrical alcohol hand sanitiser – 250ml": "hand sanitiser, named as such.",
}


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    added = 0
    for name, why in PRODUCTS.items():
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
            "hub": "skin-prep:wipe",
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
