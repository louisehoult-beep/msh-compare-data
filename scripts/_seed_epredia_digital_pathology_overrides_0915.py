#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 15/09/2026.

Digital Diagnostic Solutions: Epredia is one of the 11 suppliers named in
^o303 (05/09) as publishing a range but none of it under digital:hw/sw.
Epredia's crawled "Digital Pathology" division (25 products) is a mixed bag —
plain histology consumables (Microscope Slides, Coverglass, Filter Cubes,
Tma Grand Master/Master, Consumables, Coverslipping, Desk Ii, Flash Desk) sit
in the SAME division as named whole-slide-imaging scanners and image
management/analysis software. The division as a whole stays mapped to
pathology:histo (correct for the consumables); these 16 individually-named
products get their own product-override decision instead of forcing the
whole division, because a glass coverslip is not a digital product.

Confirmed 15/09/2026 directly against Epredia's own site
(epredia.com/products/digital-pathology/...), which is itself the primary
source: every one of the 16 sits under that "digital-pathology" URL branch,
split into three sub-paths that state their own kind —

  * /dx-whole-slide-imaging/ and /rx-whole-slide-imaging/ — whole-slide
    imaging SCANNERS (P1000/P250/P480 Dx and Rx Scanner, Midi II/III Rx
    Scanner, Scan II Rx Scanner, Midi Confocal, E1000 Dx Digital Pathology
    Solution) and the Barco Display monitor that pairs with them. Capital
    imaging hardware -> digital:hw ("Clinical IT hardware").
  * /image-management-software/ (Casemanager, Slidecenter, Slidemanager) and
    /image-analysis-software/ (Quantcenter) — the URL segment itself says
    "software". -> digital:sw ("Clinical and departmental software systems
    (imaging, oncology, laboratory...)").

Every one of the 16 has a supplier-product-detail.json record with its own
epredia.com sourceUrl already captured, so — unlike Sysmex UK's Quantcenter/
Slidecenter/Slideviewer (^o457/^o464, held pending re-crawl) — these publish
immediately once mapped, no re-crawl needed.

Run once: python3 scripts/_seed_epredia_digital_pathology_overrides_0915.py
Then write the part file and:  python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"

# (supplier, exact product name as crawled) — hub left null, filled by the
# part-file merge next.
PRODUCTS = [
    ("Epredia", "P1000 Dx Scanner"),
    ("Epredia", "P250 Dx Scanner"),
    ("Epredia", "P480 Dx Scanner"),
    ("Epredia", "E1000 Dx Digital Pathology Solution"),
    ("Epredia", "Barco Display"),
    ("Epredia", "Midi Confocal"),
    ("Epredia", "Midi Ii Rx Scanner"),
    ("Epredia", "Midi Iii Rx Scanner"),
    ("Epredia", "P1000 Rx Scanner"),
    ("Epredia", "P250 Rx Scanner"),
    ("Epredia", "P480 Rx Scanner"),
    ("Epredia", "Scan Ii Rx Scanner"),
    ("Epredia", "Casemanager"),
    ("Epredia", "Slidecenter"),
    ("Epredia", "Slidemanager"),
    ("Epredia", "Quantcenter"),
]

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for supplier, name in PRODUCTS:
    key = (supplier, name)
    if key in known:
        print("already present, skipping:", supplier, "/", name)
        continue
    doc["entries"].append({
        "supplier": supplier,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": None,
        "notTaxonomy": False,
        "kind": "product-override",
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override placeholder entries (hub=null, ready for the part file)" % added)
