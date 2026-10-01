#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 01/10/2026.

Electrodes, Ultrasound Gels, Defibrillation and Related Consumables:
Optimum Medical is one of the framework's 37 awarded suppliers, held under
this framework because its own crawl (optimummedical.co.uk, sitemap route,
verified 2026-08-25) is a flat 88-item "Uncategorised" bucket mixing real
products (OptiLube/Ugo/catheter lines) with blog-post titles ("Earth Day
2023", "Medica 2023") — the sitemap route cannot structurally tell the two
apart, so the whole division stays unmapped rather than being forced onto
one category (nav-labels-are-not-products / mixed-division-mapping policy
shapes). One product-override already exists for this supplier (Optilube
Lubrication Gynaecology -> womens:gyn).

One further item in that same 88-item list, "Vue Ultrasound Gel", is a real,
confirmed product for this framework's own scope (Lot 1, ultrasound gels):

  https://optimummedical.co.uk/product/vue-ultrasound-gel/ (read 01/10/2026,
  HTTP 200, title "Vue Ultrasound Gel - Optimum Medical"): "Vue Ultrasound
  Gel is a non-sterile, single use, non-invasive medical device used in
  medical diagnostic ultrasound procedures", offered as sterile single-use
  20ml sachets and non-sterile 250ml/1l bottles.

Maps to cardiology:gel ("Ultrasound gels") exactly. The sitemap route
carries no per-product detail (captureCaveat on the supplier-products.json
record: "Names are derived from the last segment of each product URL ...
carry no category"), so without a supplier-product-detail.json record this
would stay HELD as "no source carries this product" even with the map entry
in place (Celtic SMR precedent, scripts/_seed_celtic_smr_ultrasound_overrides_0925.py)
— this seeder adds both.

Left unmapped deliberately, same division: the other ~86 entries are either
other-specialism lubricant/catheter products (already covered or out of
scope for cardiology) or blog-post titles with no product content.

Run once: python3 scripts/_seed_optimum_medical_ultrasound_gel_override_1001.py
Then:     python3 scripts/build_differentiator.py
          python3 scripts/stamp_notice.py
          python3 scripts/build_coverage_ledger.py
"""
import json

SUPPLIER = "Optimum Medical"
NAME = "Vue Ultrasound Gel"
URL = "https://optimummedical.co.uk/product/vue-ultrasound-gel/"
DATE = "2026-10-01"
HUB = "cardiology:gel"

MAP = "data/differentiator-category-map.json"
DETAIL = "data/supplier-product-detail.json"

DESCRIPTION = (
    "Vue Ultrasound Gel is a non-sterile, single use, non-invasive medical device "
    "used in medical diagnostic ultrasound procedures. Offered in sterile, "
    "single-use 20ml sachets (single- and double-wrapped) and non-sterile 250ml "
    "and 1l bottles."
)
FEATURES = [
    "Sterile, single-use sachets are recommended for procedures requiring a "
    "sterile technique and have a five-year shelf-life.",
    "Non-sterile bottles (250ml/1l) are for low-risk, general external "
    "examinations on intact skin, not within 24 hours of an invasive procedure "
    "on the same area; three-year shelf-life unopened, one month once opened.",
    "For external examinations only; non-sterile format is not suitable for "
    "immunocompromised, neonatal or critically ill hospitalised patients.",
]

# 1. Map entry (the recorded category decision).
doc = json.load(open(MAP, encoding="utf-8"))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
if (SUPPLIER, NAME) in known:
    print("map: already present")
else:
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": NAME,
        "products": 1,
        "categories": [],
        "examples": [NAME],
        "hub": HUB,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": "the supplier's own site filing (optimummedical.co.uk), read by "
                    "scripts/crawl_supplier_site.py; product page "
                    + URL + " read 01/10/2026 (HTTP 200, title "
                    "\"Vue Ultrasound Gel - Optimum Medical\").",
        "why": "A genuine, named ultrasound gel product on the supplier's own site, "
               "currently sitting in the flat 88-product 'Uncategorised' sitemap "
               "capture (a mix of real products and blog-post titles with no "
               "division structure). Matches cardiology:gel (\"Ultrasound gels\") "
               "exactly -- the Electrodes, Ultrasound Gels, Defibrillation and "
               "Related Consumables framework's own Lot 1. The rest of the "
               "Uncategorised bucket stays unmapped (blog posts, and other-"
               "specialism lubricant/catheter lines already covered by the "
               "existing Optilube Lubrication Gynaecology override or out of "
               "scope here).",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    json.dump(doc, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("map: added product-override (hub=%s)" % HUB)

# 2. Per-product detail (sitemap capture carries none; build_differentiator.py
#    holds any product-override with no source, so this is required, not optional).
dd = json.load(open(DETAIL, encoding="utf-8"))
key = SUPPLIER + "|" + NAME.lower()
if key in dd["products"]:
    print("detail: already present")
else:
    dd["products"][key] = {
        "supplier": SUPPLIER,
        "product": NAME,
        "sourceUrl": URL,
        "capturedDate": DATE,
        "parsed": "structured",
        "description": DESCRIPTION,
        "features": FEATURES,
        "image": None,
    }
    json.dump(dd, open(DETAIL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("detail: added", key)
