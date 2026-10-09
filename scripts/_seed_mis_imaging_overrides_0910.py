#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 10/09/2026.

MIS Healthcare's "Imaging" division (55 products) mixes at least eight
different modalities (CT, MRI, digital radiography, cathlab/angio,
fluoroscopy, DXA, dental, molecular imaging/PET, plus a video-documentation
line and accessories) under one flat crawl division, so it cannot be given a
single (or list) division-level `hub` the way Ultrasound and PACS were:
tagging the whole division would publish DXA, dental, PET and video products
as if they were CT/MRI/X-ray/angio systems.

The site's OWN category pages (mishealthcare.co.uk/products/categories/
imaging/{fixed-ct,mobile-ct,mri,digital-radiography,cathlabs}) name a subset
of the division's products unambiguously by device family, confirmed against
the sitemap's own file-path filing (…/MIS/Imaging/<SubCategory>/<Product>/).
Those 22 products get individual kind="product-override" entries (seeded
here with hub=null) so the sanctioned merge_differentiator_parts.py path can
fill them from a part file — this script never sets `hub` itself.

Run once: python3 scripts/_seed_mis_imaging_overrides_0910.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Medical Imaging Systems (MIS Healthcare)"

# name -> category page it was confirmed on, 10/09/2026
PRODUCTS = {
    "uCT 550": "fixed-ct", "uCT 780": "fixed-ct", "uCT 820": "fixed-ct",
    "uCT 868": "fixed-ct", "uCT 960+": "fixed-ct",
    "uCT Orion Elite": "fixed-ct", "uCT Orion Extra": "fixed-ct",
    "BodyTom®": "mobile-ct", "CereTom®": "mobile-ct", "OmniTom®": "mobile-ct",
    "uMR® 670": "mri", "uMR® 680": "mri", "uMR 780": "mri",
    "uMR Ultra": "mri", "uMR Omega": "mri", "uMR Jupiter 5.0T": "mri",
    "GC85A Vision+": "digital-radiography", "GM85 Elite": "digital-radiography",
    "GM85 FIT": "digital-radiography", "GF85": "digital-radiography",
    "GR40 Retro-Fit": "digital-radiography",
    "Shimadzu Trinias": "cathlabs",
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
            "06/09/2026 under the flat 'Imaging' division; confirmed 10/09/2026 "
            "against the company's own category page "
            "mishealthcare.co.uk/products/categories/imaging/%s, which lists this "
            "product by name, and against the product's own file path on the site's "
            "sitemap (…/MIS/Imaging/…), which names the same sub-category."
        ) % page,
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries (hub=null, ready for the part file)" % added)
