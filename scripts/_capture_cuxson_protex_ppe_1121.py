#!/usr/bin/env python3
"""One-off, 21/11/2026 (differentiator-framework-coverage, Hand Hygiene and Associated
Products and Services): publish Cuxson Gerrard & Company Limited's own PPE range via the
manual product capture route (sanctioned by Lou 30/09/2026; Cowork-OS 02-Elevate-and-Thrive/
Process flows for all brands/manual-product-capture-route.md).

Why now: backfill_seed_from_frameworks.py attached the Hand Hygiene award (NHS Supply Chain
brief, "Cuxson Gerrard & Company Ltd", Lot 4) to this supplier on 20/11/2026, after the
framework's exhausted record (14/10) was written, so it was new work.

The automated crawler's refusal of www.cuxsongerrard.com (05/09/2026, no product post type,
no sitemap) is left untouched: that site carries no catalogue, only links to the company's
brand sites. Nothing here re-runs the crawler.

Identity (read 21/11/2026):
  * cuxsongerrard.com home page links protexrespirators.co.uk and its online shop
    firstaidfast.co.uk among "our leading brands, product range and online shop".
  * The Protex UKCA Declaration of Conformity
    (protexrespirators.co.uk/wp-content/uploads/2023/11/PROTEX-UKCA-DECLARATION.pdf) is
    issued by "Cuxson Gerrard & Company Limited of 125 Broadwell Road, Oldbury" (Registered
    in England No. 80715) for Protex Respirators S1, S1181, S1191, S2, S2V, S2O, S1182, S3, S3V
    as PPE to EN 149:2001+A1:2009.
robots.txt on all three sites: "User-agent: * / Disallow:" (everything allowed).

Each product's own firstaidfast.co.uk page was read individually (HTTP 200, product name on
the page). Captured: the seven Protex EN149 respirators the shop sells and its Full Face
Visor (in the shop's Protex Respiratory Protection section). NOT captured: the Protex Everyday
Face Covering (sold as a non-medical face covering, not EN149 PPE) and Hibiscrub / pump top
(a third-party brand the shop resells). Stock/availability wording is dropped from the
descriptions: it is a fact with a shelf life.

Category: infection:ppe, where FFP2/FFP3 EN149 face masks and face shields already publish
(e.g. "ffp3 nr face masks without valve | en 149:2001+a1:2009", "mckinnon face shield").

Run once from the repo root:
  python3 scripts/_capture_cuxson_protex_ppe_1121.py
"""
import json
import os
import re

DATE = "2026-11-21"
HUB = "infection:ppe"
KEY = "Cuxson Gerrard & Company Limited"
DIVISION = "Protex Respiratory Protection"
FRAMEWORK = "Hand Hygiene and Associated Products and Services"
STAGED = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-Personal/Cowork-OS/02-Elevate-and-Thrive/Hub/"
    "Medical-Sales-Hub/proposed-data/manual-capture-cuxson-protex-ppe-proposed-2026-11-21.json")
IDENT = ("firstaidfast.co.uk (Cuxson Gerrard's online shop, linked from cuxsongerrard.com; "
         "the Protex UKCA Declaration of Conformity is issued by Cuxson Gerrard & Company "
         "Limited, Registered in England No. 80715)")

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"
MAP = "data/differentiator-category-map.json"

STOCK = re.compile(r"(BACK IN STOCK!.*?DELIVERY\.|S3 and S3V respirators as well as Protex face "
                   r"coverings are available for despatch now \(whilst stocks last\)\.)\s*", re.I)


def clean(desc):
    return re.sub(r"\s+", " ", STOCK.sub("", desc or "")).strip() or None


def save(path, doc, compact=False):
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            f.write(json.dumps(doc, ensure_ascii=False))
        else:
            f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


staged = json.load(open(STAGED, encoding="utf-8"))
assert staged["date"] == DATE and staged["supplier"] == KEY
items = staged["products"]
sp = json.load(open(RANGE, encoding="utf-8"))
dd = json.load(open(DETAIL, encoding="utf-8"))
cm = json.load(open(MAP, encoding="utf-8"))

rec = sp["suppliers"][KEY]  # existing hapla.co.uk manual capture (20/11/2026)
have = {(x.get("n") or "").lower() for x in rec.get("products") or []}
new = [{"n": p["n"], "division": DIVISION, "category": "",
        "manualCapture": {"sourceUrl": p["sourceUrl"], "capturedDate": DATE}}
       for p in items if p["n"].lower() not in have]
rec.setdefault("products", []).extend(new)
if DIVISION not in {d["name"] for d in rec.get("divisions") or []}:
    rec.setdefault("divisions", []).append({"name": DIVISION, "products": len(items)})
rec["filingRule"] = ((rec.get("filingRule") or "").rstrip() + " Added %s for the %s "
                     "framework: the PPE section of %s (Protex EN149 respirators and a full "
                     "face visor) only; the rest of that shop was not captured." % (
                         DATE, FRAMEWORK, "firstaidfast.co.uk")).strip()
rec["manualCaptureNote"] = ("Added %s: %d products from %s, each page read individually "
                            "(manual product capture route), for the %s framework." % (
                                DATE, len(new), IDENT, FRAMEWORK))
print("range: %s extended (+%d products)" % (KEY, len(new)))

added = 0
for p in items:
    k = KEY + "|" + p["n"].lower()
    if k in dd["products"]:
        continue
    dd["products"][k] = {
        "supplier": KEY, "product": p["n"], "sourceUrl": p["sourceUrl"],
        "capturedDate": DATE, "parsed": "structured",
        "description": clean(p.get("description")), "features": None, "image": None,
    }
    added += 1
print("detail: +%d" % added)

if any(e["supplier"] == KEY and e["division"] == DIVISION for e in cm["entries"]):
    print("map: already present")
else:
    cm["entries"].append({
        "supplier": KEY, "division": DIVISION, "products": len(items), "categories": [],
        "examples": [p["n"] for p in items][:4], "hub": HUB, "notTaxonomy": False,
        "evidence": "%s, product pages read %s: the '%s' section of the shop. %s is named on "
                    "NHS Supply Chain's %s contract launch brief (Lot 4)." % (
                        IDENT, DATE, DIVISION, KEY, FRAMEWORK),
        "why": "EN 149 FFP1/FFP2/FFP3 disposable respirators declared as PPE by the "
               "manufacturer, and a full face visor: personal protective equipment, the same "
               "category as the FFP2/FFP3 EN149 masks and face shields already published.",
    })
    print("map: %s / %s -> %s" % (KEY, DIVISION, HUB))
cm["counts"]["pairs"] = len(cm["entries"])

save(RANGE, sp)
save(DETAIL, dd)
save(MAP, cm, compact=True)
