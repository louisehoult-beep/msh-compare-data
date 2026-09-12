#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 12/09/2026.

Continuation of scripts/_seed_mis_imaging_overrides_0910.py, which extracted
22 of the ~159 products held in MIS Healthcare's flat "Imaging" (55) and
"Uncategorised" (104) divisions by name, confirmed against the company's own
mishealthcare.co.uk/products/categories/imaging/<slug> pages. This batch adds
the Dental, DXA and Molecular Imaging families the same way.

Confirmed 12/09/2026 directly against mishealthcare.co.uk's own site nav,
which lists Dental, DXA and Molecular Imaging as full sibling categories to
the already-mapped Fixed CT / Mobile CT / MRI / Digital Radiography /
Cathlabs — same taxonomy, same evidence standard.

Run once: python3 scripts/_seed_mis_imaging_overrides_0912.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Medical Imaging Systems (MIS Healthcare)"

# name -> category page slug it was confirmed on, 12/09/2026
PRODUCTS = {
    "Rayscan α": "dental", "Rayscan α+": "dental",
    "Rioscan": "dental", "Riosensor": "dental",
    "DEXUM T Quantum": "dxa", "Dexxum T Half Body DXA": "dxa",
    "Excellus DXA": "dxa", "Primus Whole Body DXA": "dxa",
    "uEXPLORER": "molecular-imaging", "uMI 550": "molecular-imaging",
    "uMI Panorama": "molecular-imaging", "uMI Panorama GS": "molecular-imaging",
    "uMI Panvivo": "molecular-imaging", "uMI Panvivo EX/ES": "molecular-imaging",
    "uPMR® 790": "molecular-imaging",
}

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for name, page in PRODUCTS.items():
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
            "the supplier's own site filing, read by scripts/crawl_supplier_site.py "
            "under the flat 'Imaging'/'Uncategorised' divisions; confirmed 12/09/2026 "
            "against the company's own category page "
            "mishealthcare.co.uk/products/categories/imaging/%s, which lists this "
            "product by name."
        ) % page,
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
