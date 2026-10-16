#!/usr/bin/env python3
"""One-off, 16/10/2026 (^o524): publish Urathon Europe Ltd's Yuwell Anytime CT-3
CGM system in the Differentiator.

Manual product capture route (Cowork-OS 02-Elevate-and-Thrive/Process flows for
all brands/manual-product-capture-route.md). The product sits on a marketing
microsite outside the /product/ catalogue crawl_supplier_site.py reads, so it
is carried on Urathon's supplier-products.json record with a "manualCapture"
block, which crawl_supplier_site.carry_manual_products() keeps across every
future crawl. Plus one supplier-product-detail.json record and one
kind="product-override" map entry, as for ZEISS INTRABEAM 600.

Source, read 16/10/2026: https://www.urathon.com/yuwellanytime/ (public page;
urathon.com/robots.txt disallows only /wp-admin/). Sentences are the page's own,
verbatim. Nothing inferred. The page's trial figures are the supplier's own
claims and are not recorded here.

Run once from the repo root: python3 scripts/_seed_urathon_yuwell_anytime_1016.py
"""
import json

SUPPLIER = "Urathon Europe Ltd"
NAME = "Yuwell Anytime CT-3 CGM System"
DIVISION = "Yuwell Anytime CGM"
URL = "https://www.urathon.com/yuwellanytime/"
DATE = "2026-10-16"
HUB = "diabetes:cgm"


def save(path, doc):
    # The category map is compact with no trailing newline; the other two are indent=1.
    # Re-dumping in the wrong style would bury the one new entry in a whole-file diff.
    with open(path, "w", encoding="utf-8") as f:
        if path.endswith("differentiator-category-map.json"):
            f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
        else:
            f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


sp = json.load(open("data/supplier-products.json", encoding="utf-8"))
rec = sp["suppliers"][SUPPLIER]
if any(p["n"] == NAME for p in rec["products"]):
    print("range: already present")
else:
    rec["products"].append({"n": NAME, "division": DIVISION,
                            "manualCapture": {"sourceUrl": URL, "capturedDate": DATE}})
    rec["divisions"].append({"name": DIVISION, "products": 1})
    save("data/supplier-products.json", sp)
    print("range: added")

dd = json.load(open("data/supplier-product-detail.json", encoding="utf-8"))
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
        "description": (
            "Introducing a world-first rechargeable CGM transmitter. With readings every "
            "three minutes and unlimited data storage, this cutting-edge device uses "
            "Bluetooth technology to sync seamlessly with your phone or tablet. The Anytime "
            "CT-3 CGM transmitter lasts an impressive two years, reducing both costs and "
            "environmental waste."
        ),
        "features": [
            "Best of all, you only need to replace the sensor every two weeks.",
            "7 Glucose trend arrows.",
            "Share real-time data with up to 20 people.",
            "Allow logging of meals, exercise and insulin.",
            "Efficient Real-time High and Low alerts to take action.",
        ],
        "image": None,
    }
    save("data/supplier-product-detail.json", dd)
    print("detail: added")

doc = json.load(open("data/differentiator-category-map.json", encoding="utf-8"))
if any(e["supplier"] == SUPPLIER and e["division"] == NAME for e in doc["entries"]):
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
        "evidence": "urathon.com's own page for this product (" + URL + ", read 16/10/2026) "
                    "describes a continuous glucose monitoring (CGM) system: a rechargeable "
                    "transmitter with a sensor replaced every two weeks. Urathon Europe Ltd is "
                    "an awarded supplier on the NHS Supply Chain Insulin Pumps, CGM and Hybrid "
                    "Closed Loop framework.",
        "why": "Continuous glucose monitoring system, not test strips (diabetes:strip), pens "
               "(diabetes:pen) or pump sets (diabetes:pumpset).",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    save("data/differentiator-category-map.json", doc)
    print("map: added")
