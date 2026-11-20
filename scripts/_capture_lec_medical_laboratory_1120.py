#!/usr/bin/env python3
"""One-off, 20/11/2026 (differentiator-framework-coverage run): publish Glen Dimplex
Home Appliances' Lec Medical laboratory refrigeration range in the Differentiator for
the "Laboratory Diagnostics, Point of Care Testing and Pathology Managed Services"
framework (NHS Supply Chain names the awardee "Glen Dimplex Home Appliances").

Identity: www.lec-medical.co.uk proved on the REGISTRATION tier this run by
scripts/seed_supplier_domains.py: its privacy policy states "Glen Dimplex Professional
Appliances, trading as Lec Medical is a division of Glen Dimplex Home Appliances Limited
(company number 2692306)". The awarded entity itself owns the site; no parent/subsidiary
crediting is involved.

Route: manual product capture route, sanctioned by Lou 30/09/2026 (Cowork-OS
02-Elevate-and-Thrive/Process flows for all brands/manual-product-capture-route.md).
crawl_supplier_site.py refuses the site (Drupal, products at flat /en-gb/<model> paths,
no product path segment, category pages fill their product lists by script), so each
product page was read individually. robots.txt allows every product path. Staged first at
02-Elevate-and-Thrive/Hub/Medical-Sales-Hub/proposed-data/
manual-capture-lec-medical-laboratory-proposed-2026-11-20.json.

Selection (mixed-division-mapping policy): only the 30 pages in lec-medical.co.uk's own
sitemap whose own <h1> names the product a Laboratory fridge, freezer or fridge/freezer.
Pharmacy, ward, neonatal, staff-room, cooler, data-logger and bare-SKU pages (L5010,
R5511 ...) are NOT captured: their names do not identify a laboratory product. The record
is marked partialRead with a filingRule saying so.

Description: the page's own meta description where it carries one (e.g. "310L Upright
refrigerator with solid door. ATEX approved"); None where it carries none. The
specifications panel is script-loaded and was not read; nothing is inferred.

Category: pathology:equip, the same decision recorded for Appleton Woods' laboratory
ULT freezers and refrigerators (division-level, "benchtop or capital laboratory
instruments"). The captured division is homogeneous: every product's own name says
Laboratory.

Run once from the repo root: python3 scripts/_capture_lec_medical_laboratory_1120.py
"""
import json
import os

SUPPLIER = "Glen Dimplex Home Appliances"
DOMAIN = "lec-medical.co.uk"
DIVISION = "Laboratory Fridges and Freezers"
DATE = "2026-11-20"
HUB = "pathology:equip"
STAGED = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-Personal/Cowork-OS/02-Elevate-and-Thrive/Hub/"
    "Medical-Sales-Hub/proposed-data/manual-capture-lec-medical-laboratory-proposed-2026-11-20.json")

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"
MAP = "data/differentiator-category-map.json"


def save(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


staged = json.load(open(STAGED, encoding="utf-8"))
assert staged["supplier"] == SUPPLIER
items = staged["products"]
assert len(items) == 30 and all("laborator" in p["n"].lower() for p in items)

# 1. Range record.
sp = json.load(open(RANGE, encoding="utf-8"))
if SUPPLIER in sp["suppliers"]:
    print("range: already present, left untouched")
else:
    sp["suppliers"][SUPPLIER] = {
        "domain": DOMAIN,
        "verified": DATE,
        "source": "lec-medical.co.uk (Lec Medical, a division of Glen Dimplex Home Appliances "
                  "Limited, company number 2692306 per the site's own privacy policy): each "
                  "product's own page read individually on %s (manual product capture route, "
                  "sanctioned 30/09/2026)." % DATE,
        "structureFrom": "the site's own 'Laboratory Fridges and Freezers' section name",
        "hasDivisions": True,
        "partialRead": True,
        "structure": "Laboratory refrigeration only, filed under the section name "
                     "lec-medical.co.uk gives it.",
        "filingRule": "Partial manual capture, not Lec Medical's whole range: only the 30 "
                      "product pages whose own name says Laboratory. Pharmacy, ward, "
                      "neonatal, staff-room and bare model-number pages were not captured "
                      "because their names do not identify a laboratory product.",
        "divisions": [{"name": DIVISION, "products": len(items)}],
        "products": [{"n": p["n"], "division": DIVISION, "category": "",
                      "manualCapture": {"sourceUrl": p["sourceUrl"], "capturedDate": DATE}}
                     for p in items],
    }
    save(RANGE, sp)
    print("range: added %d-product record" % len(items))

# 2. Detail records.
dd = json.load(open(DETAIL, encoding="utf-8"))
added = 0
for p in items:
    key = SUPPLIER + "|" + p["n"].lower()
    if key in dd["products"]:
        continue
    dd["products"][key] = {
        "supplier": SUPPLIER,
        "product": p["n"],
        "sourceUrl": p["sourceUrl"],
        "capturedDate": DATE,
        "parsed": "structured",
        "description": p["description"],
        "features": None,
        "image": None,
    }
    added += 1
save(DETAIL, dd)
print("detail: added", added)

# 3. Division map entry.
doc = json.load(open(MAP, encoding="utf-8"))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
if (SUPPLIER, DIVISION) in known:
    print("map: already present")
else:
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": DIVISION,
        "products": len(items),
        "categories": [],
        "examples": [items[i]["n"] for i in (0, 9, 22, 29)],
        "hub": HUB,
        "notTaxonomy": False,
        "evidence": "lec-medical.co.uk's own product pages, read %s: every product in this "
                    "division is named a Laboratory refrigerator, freezer or fridge/freezer "
                    "(spark-free and ATEX-approved models). Glen Dimplex Home Appliances is "
                    "named on NHSSC's Laboratory Diagnostics, Point of Care Testing and "
                    "Pathology Managed Services contract launch brief." % DATE,
        "why": "capital laboratory refrigeration, the same category as Appleton Woods' "
               "laboratory ULT freezers and refrigerators; not consumables.",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    with open(MAP, "w", encoding="utf-8") as f:  # this file is stored compact, one line
        f.write(json.dumps(doc, ensure_ascii=False))
    print("map: added division entry (hub=%s)" % HUB)
