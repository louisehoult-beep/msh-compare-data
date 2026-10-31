#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 31/10/2026.

pfm medical UK's own-site capture (data/supplier-products.json, domain
www.pfmmedical.co.uk, verified 2026-10-22) carries a "Histotechnology"
division of 61 products that was entirely unmapped (hub: null in
data/differentiator-category-map.json) and so held in full, even though
pfm medical UK already publishes elsewhere on this framework via nine
product-override vascular entries.

The division's own products -- microtome blades, autopsy/dissection/trimming
blades and handles, rotary microtomes, fixatives, formalin neutralisers,
decalcifiers, embedding cassettes, histology wax, mounting media, microscope
slides, tinctorial/special stains, biopsy pads/bags/punches, cryotomy
accessories, a slide printer -- are unambiguously histopathology laboratory
equipment and consumables, matching this repo's existing pathology:histo
type ("Histology & cellular", data/differentiator-category-map.json
vocabulary.pathology.histo) by name and by content, not by inference from
the supplier's other divisions. All 61 are now backed by a per-product
manufacturer source (crawled live 31/10/2026 via
scripts/crawl_supplier_product_detail.py --supplier "pfm medical UK"
--domain www.pfmmedical.co.uk, each resolving to its own
pfmmedical.co.uk/products/histotechnology/... page).

NOT mapped here: "Breast Cancer Diagnostics" (1 product, Clearcoast Mri
System). Its own product name and page both describe it as an MRI system,
and although its use (intraoperative surgical-margin assessment compared to
frozen-section histopathology) is pathology-adjacent, "MRI System" in the
name is the kind of ambiguity the mixed-division-mapping policy guard
(data/identity-vocabulary-policy.json) says to hold rather than force --
left held, noted in the run report rather than guessed.

Run once: python3 scripts/_seed_pfm_medical_histotechnology_1031.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "pfm medical UK"
DIVISION = "Histotechnology"
HUB = "pathology:histo"

EVIDENCE = (
    "the supplier's own site filing (www.pfmmedical.co.uk/products/"
    "histotechnology/..., crawled live 31/10/2026 via "
    "scripts/crawl_supplier_product_detail.py), structure already read by "
    "scripts/crawl_supplier_site.py (data/supplier-products.json, verified "
    "2026-10-22)"
)
WHY = (
    "every product in this division (microtome blades, autopsy/dissection/"
    "trimming blades, rotary microtomes, fixatives, decalcifiers, embedding "
    "cassettes, histology wax, mounting media, microscope slides, "
    "tinctorial and special stains, biopsy pads/bags/punches, cryotomy "
    "accessories, a histology slide printer) is histopathology laboratory "
    "equipment or consumables, matching this repo's existing pathology:histo "
    "type (\"Histology & cellular\") by name and by content"
)

doc = json.load(open(MAP))
entries = doc["entries"]
examples = None
products_count = None
for e in entries:
    if e["supplier"] == SUPPLIER and e["division"] == DIVISION:
        if e.get("hub"):
            raise SystemExit("already mapped: %r" % e)
        e["hub"] = HUB
        e["evidence"] = EVIDENCE
        e["why"] = WHY
        e["decidedIn"] = "framework-coverage batch 31/10/2026"
        products_count = e.get("products")
        examples = e.get("examples")
        break
else:
    raise SystemExit("no existing (supplier, division) entry found to update")

doc["counts"]["pairs"] = len(entries)
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("mapped %s / %s -> %s (%s products, examples: %s)"
      % (SUPPLIER, DIVISION, HUB, products_count, examples))
