#!/usr/bin/env python3
"""One-off, 27/11/2026: take the pages that are not products out of medi UK's
published range, each read at www.mediuk.co.uk that day. The removed rows go to
ops/held-captures/ and the names to _meta.notProducts, which the crawler drops
and verify.py refuses.

Run once from the repo root:  python3 scripts/_remove_medi_non_products_1127.py
"""
import json
import os
import sys

from crawl_supplier_site import atomic_write_json, drop_non_products

PATH = "data/supplier-products.json"
HELD = "ops/held-captures/medi-uk-non-products-2026-11-27.json"
DAY = "2026-11-27"
NAME = "medi UK"

TEMPLATE = "page template preview, not a product"
CATEGORY = "body-part or assessment category page"
ARTICLE = "article, campaign or tool page, not a product"
COPY = "second page about a product already listed (%s)"

# (name, division or None for any division, why)
NOT_PRODUCTS = [
    ("Product Details Contact Panel Teaser", None, TEMPLATE),
    ("Product Details Info Panel Teaser", None, TEMPLATE),
    ("Product Details Hotspot Elements", None, TEMPLATE),
] + [(n, None, CATEGORY) for n in (
    "Assessment", "Arm", "Hand Arm", "Foot", "Leg", "Neck", "Shoulder", "Spine", "Upper Limb")
] + [(n, None, ARTICLE) for n in (
    "Painful Elbow", "Therapy Concepts", "Colours Patterns Oedema Therapy",
    "Peripheral Arterial Disease Pad", "Hosiery Hunter", "Times Approach",
    "Supported Self Care", "Variety Venous Therapy", "Oa Orthoses",
    "Spring Loaded Bracing", "Jas Range")
] + [
    ("M4S Pcl Dynamic Brace", None, COPY % "M4S Pcl Dynamic"),
    ("Mediven Leg Ulcer Kit", None, COPY % "Mediven Ulcer Kit"),
    ("Medi Soft Oa Light Uk", None, COPY % "Medi Soft Oa Light"),
    ("Ucs Debridement", "Highlights", COPY % "Ucs Debridement"),
    ("Duomed Soft 2Easy", "Highlights", COPY % "Duomed Soft 2Easy"),
]


def main():
    doc = json.load(open(PATH, encoding="utf-8"))
    ruled = doc["_meta"].setdefault("notProducts", {})
    if NAME in ruled or os.path.exists(HELD):
        sys.exit("already run")
    ruled[NAME] = [dict({"n": n, "why": why, "readOn": DAY}, **({"division": d} if d else {}))
                   for n, d, why in NOT_PRODUCTS]
    rec = doc["suppliers"][NAME]
    before = list(rec["products"])
    removed = drop_non_products(doc, NAME, rec)
    if len(removed) != len(NOT_PRODUCTS):
        sys.exit("expected %d rows, matched %d" % (len(NOT_PRODUCTS), len(removed)))
    detail = json.load(open("data/supplier-product-detail.json", encoding="utf-8"))["products"]
    gone = {p["n"] for p in removed} - {p["n"] for p in rec["products"]}
    stray = [k for k, v in detail.items() if v.get("supplier") == NAME and v.get("product") in gone]
    if stray:
        sys.exit("product-detail entries exist for removed rows: %s" % stray)
    os.makedirs(os.path.dirname(HELD), exist_ok=True)
    atomic_write_json(HELD, {
        "note": "Rows taken out of medi UK's published range on 27/11/2026 because their pages "
                "are not products (nav-labels-are-not-products). No app reads this file.",
        "source": "data/supplier-products.json, captured 2026-10-09",
        "removed": [dict(p, why=next(w for n, d, w in NOT_PRODUCTS
                                     if n == p["n"] and d in (None, p["division"])))
                    for p in removed]})
    doc["_meta"]["refusedOnReading"][NAME] = doc["_meta"]["refusedOnReading"][NAME].split(
        " Still open:")[0] + (" 27/11/2026: %d entries whose pages are not products were removed "
                              "(_meta.notProducts; rows in %s)." % (len(removed), HELD))
    atomic_write_json(PATH, doc)
    print("%s: %d before, %d removed, %d kept" % (NAME, len(before), len(removed), len(rec["products"])))


if __name__ == "__main__":
    main()
