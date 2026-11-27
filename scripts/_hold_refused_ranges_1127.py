#!/usr/bin/env python3
"""One-off, 27/11/2026: three ranges listed in _meta.refusedOnReading were still
published (the crawler never read that list). Canon and Terumo still show the
fault: hold them. medi UK's named fault was superseded by the 25/08/2026 flat-
range ruling: rewrite its stale note. Nothing is discarded: the held records go
to ops/held-captures/, with the held suppliers' product-detail entries.

Run once from the repo root:  python3 scripts/_hold_refused_ranges_1127.py
"""
import json
import os
import sys

from crawl_supplier_site import atomic_write_json

PATH = "data/supplier-products.json"
HELD = "ops/held-captures/supplier-ranges-refused-2026-11-27.json"
DETAIL = "data/supplier-product-detail.json"
DAY = "2026-11-27"

HOLDS = {
    "Canon Medical Systems": (
        "nav-labels-are-not-products",
        "07/08/2026, re-read 27/11/2026: refused on reading and still faulty. Page titles are "
        "published as products (Experience, Publications, Deep Learning Reconstruction, "
        "Interventional Radiology/Oncology, and many Benefits, Technology, Workflow and Clinical "
        "Gallery sub-pages, read live on uk.medical.canon) and product-line codes as divisions "
        "(Aice, Alphenix, Ai, Mobiles Relocatables 2). The capture of 07/08/2026 has not been "
        "replaced since."),
    "Terumo UK": (
        "no-parent-catalogue-credit-to-uk-subsidiary; nav-labels-are-not-products",
        "07/08/2026, re-read 27/11/2026: refused on reading and still faulty. The 09/10/2026 "
        "capture files products under the site's facet names (Product Type, Product Types, "
        "Medical Field) and lists category pages such as Cardiovascular and View All Products as "
        "products. terumo-europe.com is run by Terumo Europe NV (Belgium, its terms of use), not "
        "TERUMO UK LTD (04571001)."),
}

MEDI = (
    "Superseded; range published. The 07/08/2026 refusal (84% of product URLs carried no "
    "division segment) was lifted by the 25/08/2026 ruling that a flat range publishes as one "
    "honestly labelled list (commit 49ae45ecd6). Re-read 27/11/2026: the 09/10/2026 capture is "
    "marked hasDivisions false and says 148 of 176 URLs have no division. www.mediuk.co.uk is "
    "medi UK Ltd's own site. Still open: some entries are body-part category pages or page "
    "template blocks, not products.")


def main():
    doc = json.load(open(PATH, encoding="utf-8"))
    suppliers = doc["suppliers"]
    holds = doc["_meta"].setdefault("holds", {})
    done = [n for n in HOLDS if n in holds]
    if done or os.path.exists(HELD):
        sys.exit("already run: %s" % (done or HELD))
    held = {"note": "Captures held out of member view on 27/11/2026. No app reads this file. "
                    "To restore one, the fault named in _meta.refusedOnReading must be fixed in "
                    "a capture the named policy accepts; then remove its _meta.holds entry in "
                    "data/supplier-products.json.",
            "source": "data/supplier-products.json as published on 27/11/2026",
            "suppliers": {n: suppliers[n] for n in HOLDS}}
    detail = json.load(open(DETAIL, encoding="utf-8"))
    held["productDetail"] = {k: v for k, v in detail["products"].items()
                             if v.get("supplier") in HOLDS}
    for key in held["productDetail"]:
        del detail["products"][key]
    os.makedirs(os.path.dirname(HELD), exist_ok=True)
    atomic_write_json(HELD, held)

    for name, (policy, reason) in HOLDS.items():
        rec = suppliers.pop(name)
        holds[name] = {"heldOn": DAY, "policy": policy, "capture": HELD}
        doc["_meta"]["refusedOnReading"][name] = reason
        doc["refusals"][name] = {"domain": rec["domain"], "reason": reason, "checked": DAY}
        print("%s: %d held" % (name, len(rec["products"])))
    doc["_meta"]["refusedOnReading"]["medi UK"] = MEDI
    print("medi UK: %d published, note updated" % len(suppliers["medi UK"]["products"]))
    atomic_write_json(PATH, doc)
    atomic_write_json(DETAIL, detail)
    print("product detail: %d held" % len(held["productDetail"]))


if __name__ == "__main__":
    main()
