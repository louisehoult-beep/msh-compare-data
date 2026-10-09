#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 22/09/2026.

Hologic UK's own-site crawl (95 products) sits under one flat "Uncategorised"
division spanning mammography/breast biopsy imaging, molecular diagnostics
assays (Panther/Aptima/ThinPrep), DXA and a genuine gynaecological surgical
line — so the whole division cannot take one hub tag (mixed-division-mapping
policy, data/identity-vocabulary-policy.json).

Seven named, branded products on the record are unambiguously the
gynaecological-endoscopy/uterine-ablation line the "Minimally Invasive
Surgery, Related Equipment and Accessories" framework's own lot description
names ("gynaecological endoscopy and uterine ablation" -> mis:gynae in
data/compare-suppliers.json): MyoSure (hysteroscopic tissue removal),
NovaSure and Sonata (endometrial/fibroid ablation), Omni Hysteroscopes and
Omni Lok Cervical Seal (hysteroscopy hardware/accessory), and the Fluent /
Fluent Pro fluid management systems (hysteroscopy fluid management). These
are real, distinguishable Hologic product families, not a supplier-wide
default and not a generic navigation label.

The remaining 88 products in the division (mammography, breast biopsy,
molecular/pathology assays, DXA) are NOT touched here and stay held per the
mixed-division-mapping policy: their own names do not identify mis:*.

Run once: python3 scripts/_seed_hologic_mis_gynae_overrides_0922.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Hologic UK"

PRODUCTS = [
    "MyoSure® Tissue Removal Suite",
    "NovaSure® Endometrial Ablation",
    "Sonata® Fibroid Ablation System",
    "Omni® Hysteroscopes",
    "Omni® Lok Cervical Seal",
    "Fluent® Fluid Management System",
    "Fluent® Pro Fluid Management System",
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
            "under the flat 'Uncategorised' division; confirmed 22/09/2026 that this "
            "is a named Hologic gynaecological-surgical product family matching the "
            "'Minimally Invasive Surgery, Related Equipment and Accessories' "
            "framework's own lot description ('gynaecological endoscopy and uterine "
            "ablation', mis:gynae in data/compare-suppliers.json)."
        ),
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
