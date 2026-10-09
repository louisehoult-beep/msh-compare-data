#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 30/09/2026.

Footlabs Ltd's own-site crawl (data/supplier-products.json) is read from a
flat XML sitemap with no division structure, so all 8 of its products are
filed under a single "Uncategorised" division and would otherwise stay held
under the nav-labels-are-not-products policy. But these 8 names are not
navigation labels standing in for products -- they are specific, standard
orthotics/podiatry device and insole names read straight off the product URL
slugs. Mapped at PRODUCT level (never at division level, since "Uncategorised"
itself names nothing):

  Simple Inlays              -> insole   (a basic insole/footcare product)
  Functional Foot Orthoses   -> insole   (FFO = a rigid custom foot orthosis /
                                           insole device; standard podiatry term)
  Ankle Foot Orthoses        -> afo      (exact match to the gated type's own name)
  Tlsos                      -> spine    (TLSO = thoraco-lumbo-sacral orthosis,
                                           a trunk brace)
  Semi Custom Rx             -> insole   ("Rx" = prescription; a semi-custom
                                           prescription foot orthotic/insole)
  Total Contact Inlays       -> insole   (total contact insoles: a named,
                                           standard pressure-offloading insole type)

Left HELD, deliberately, not mapped here: "Shoe Repairs" and "Shoe Modification"
are repair/modification SERVICES performed on a patient's own existing
footwear, not a finished orthopaedic shoe (which the gated `footwear` type is
defined as) and not an insole. No gated orthotics type fits a service
unambiguously, so per the mixed-division-mapping policy's guard (never assume
a dominant fit) these two stay unmapped and uncounted -- publishing nothing
beats guessing.

Run once: python3 scripts/_seed_footlabs_orthotics_product_overrides_0930.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Footlabs Ltd"

DECISIONS = [
    ("Simple Inlays", "orthotics:insole",
     "a basic insole/footcare product"),
    ("Functional Foot Orthoses", "orthotics:insole",
     "FFO = a rigid custom foot orthosis/insole device, standard podiatry term"),
    ("Ankle Foot Orthoses", "orthotics:afo",
     "exact match to the gated type's own name"),
    ("Tlsos", "orthotics:spine",
     "TLSO = thoraco-lumbo-sacral orthosis, a trunk brace"),
    ("Semi Custom Rx", "orthotics:insole",
     "\"Rx\" = prescription; a semi-custom prescription foot orthotic/insole"),
    ("Total Contact Inlays", "orthotics:insole",
     "total contact insoles: a named, standard pressure-offloading insole type"),
]

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}

added = 0
for name, hub, why in DECISIONS:
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
        "why": why,
        "evidence": (
            "the supplier's own site filing (sitemap-derived, URL slug as name), "
            "read by scripts/crawl_supplier_site.py; category decided 30/09/2026 "
            "from the product's own standard podiatry/orthotics name."
        ),
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries for %r" % (added, SUPPLIER))
