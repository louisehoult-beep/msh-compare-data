#!/usr/bin/env python3
"""One-off, 07/11/2026, differentiator-framework-coverage batch (Urology and
Bowel Management). Hollister's own-site crawl already carries a genuine
"Continence Care Products" division (21 products, data/supplier-products.json)
that has sat held with hub:None since its capture — its name is a real
division heading, not navigation, but it mixes three distinct continence
types by product name: intermittent catheters (Infyna/Vapro/Advance/
Instantcath ranges), one external/sheath catheter (Inview), and urinary
drainage bags/pouches (bedside collection system, leg bags, leg bag strap).
Every product's own name unambiguously identifies its type, so per the
mixed-division-mapping policy (data/identity-vocabulary-policy.json) this is
mapped at PRODUCT level with one product-override entry per item, not a
single division-level category.

Source: supplier's own site crawl, already in data/supplier-products.json
under Hollister's "Continence Care Products" division. No new crawl, no new
data — only the category decision for data already captured.

Run once from the repo root: python3 scripts/_seed_hollister_continence_overrides_1107.py
"""
import json

SUPPLIER = "Hollister"
DIVISION = "Continence Care Products"

IC = [
    "Infyna Chic Ready To Use Hydrophilic Intermittent Catheter",
    "Infyna Ready To Use Hydrophilic Intermittent Catheter Female",
    "Infyna Ready To Use Hydrophilic Intermittent Catheter Male",
    "Vapro F Style Intermittent Catheter",
    "Vapro Plus F Style Intermittent Catheter",
    "Vapro Plus Pocket Intermittent Catheter Female",
    "Vapro Plus Pocket Intermittent Catheter Male",
    "Vapro Plus Touch Free Hydrophilic Intermittent Catheter",
    "Vapro Pocket Intermittent Catheter Female",
    "Vapro Pocket Intermittent Catheter Male",
    "Vapro Touch Free Hydrophilic Intermittent Catheter",
    "Advance Plus Touch Free Intermittent Catheter System",
    "Advance Touch Free Intermittent Catheter",
    "Instantcath Pre Lubricated Intermittent Catheter",
    "Instantcath Protect Pre Lubricated Intermittent Catheter",
]
SH = [
    "Inview Silicone Male External Catheter",
]
DR = [
    "Bedside Drainage Collection System _ Non_Drainable",
    "Male Urinary Pouch External Collection Device",
    "Extended Wear Urinary Leg Bag   Sterile",
    "Urinary Leg Bag Combination Pack",
    "Leg Bag Strap",
]

ASSIGN = [(n, "continence:ic") for n in IC] + [(n, "continence:sh") for n in SH] \
         + [(n, "continence:dr") for n in DR]


def save(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))


sp = json.load(open("data/supplier-products.json", encoding="utf-8"))
names_in_division = {p["n"] for p in sp["suppliers"][SUPPLIER]["products"]
                      if p.get("division") == DIVISION}
assert names_in_division == {n for n, _ in ASSIGN}, "name set mismatch vs captured division"

doc = json.load(open("data/differentiator-category-map.json", encoding="utf-8"))
existing = {(e["supplier"], e["division"]) for e in doc["entries"]
            if e.get("kind") == "product-override" and not e.get("npc")}

added = 0
for name, hub in ASSIGN:
    if (SUPPLIER, name) in existing:
        continue
    doc["entries"].append({
        "kind": "product-override",
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": hub,
        "notTaxonomy": False,
        "evidence": "Hollister's own-site crawl (data/supplier-products.json), division "
                    "\"Continence Care Products\" — the product's own name names its type.",
        "why": "Product name identifies the type unambiguously (intermittent catheter / "
               "external catheter / urinary drainage bag), per the mixed-division-mapping "
               "policy's product-level rule.",
        "decidedIn": "differentiator-framework-coverage batch 07/11/2026, Urology and Bowel "
                     "Management",
    })
    added += 1

if added:
    doc["counts"]["pairs"] = len(doc["entries"])
    save("data/differentiator-category-map.json", doc)
print("added %d of %d" % (added, len(ASSIGN)))
