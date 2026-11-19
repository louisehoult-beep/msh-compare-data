#!/usr/bin/env python3
"""One-off: The Helping Hand Company product-level overrides for Aids for Daily
Living (framework-coverage batch, redo 05/11/2026).

The company's Shopify collections leave 45 products in "Uncategorised" and 15 in
"Bundles", neither a taxonomy. Every name below is a specific product whose name
alone identifies its type (walking stick/frame/crutch, bath seat/board, raised
toilet seat, sponge, sock aid, shoe horn, stocking frame). Patient hoists, slings,
cushions, back supports/trays for rollators and anything whose name does not
settle its type are NOT mapped and stay held (mixed-division-mapping policy).
Written straight into the map (merge_differentiator_parts.py refuses
product-name keys); the parts file named below is documentation only.
"""
import json, sys
sys.path.insert(0, "scripts")
import seed_format

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/The Helping Hand Company - product overrides 1104.json"
S = "The Helping Hand Company"
W, B, H, D = "rehab:walk", "rehab:bath", "rehab:hygiene", "rehab:daily"
GROUPS = [
 (W, "name is an explicit walking stick, crutch, walking frame/walker or a replacement ferrule for one -- a walking aid", [
  "Folding Elbow Crutches – Adjustable Open Cuff Forearm Crutches (Pair)",
  "Type Z Latex Free Replacement Ferrules for Walking Sticks and Crutches",
  "Type D Replacement Ferrules for Walking Sticks",
  "Tripod Walking Stick - 3 Point Cane", "Tetrapod Walking Stick - 4 Point Quad Cane",
  "Escort Handle Cane - Lightweight Adjustable Walking Stick",
  "Fischer Walking Stick – Ergonomic Arthritis Stick, Silver (Left or Right)",
  "Elbow Crutches – Adjustable Open Cuff Forearm Crutches (Pair)",
  "Forearm Walking Frame with Castors", "Ultra Narrow Lightweight Walking Frame with Wheels",
  "Ultra Lightweight Walking Frame with Wheels", "Aluminium Quad Cane – 4-Point Walking Stick",
  "Aluminium Walking Stick – Height Adjustable", "Hospital Walking Frame With Wheels",
  "Hospital Walking Frame", "Rolling Walker", "Lightweight Rolling Walker",
  "Ultra-Narrow Walking Frame", "Domestic Walking Frame With Wheels", "Domestic Walking Frame",
  "Fischer Walking Stick Black – Adjustable Ergonomic Stick (Left or Right)"]),
 (B, "name is an explicit bath seat, bath/shower board, raised toilet seat or a spare for one -- a bathing/toileting aid", [
  "Merlin Bath Seat - Reinforced Bath Seat", "Kingfisher Bath Seat Spare Suckers",
  "Kingfisher Bath Seat Extension Legs", "Kingfisher Height Adjustable Bath Seat",
  "Surefoot Bath and Shower Board", "Unifix Raised Toilet Seat",
  "EZY-FIT Height Adjustable Raised Toilet Seat", "EZY-FIT 4\" Raised Toilet Seat",
  "Surefoot Shower Kit – Surefoot® Bathboard with Handle & Toe-Foot Sponge",
  "Surefoot Bathroom Kit – Surefoot® Bath Board with Handle & Exfoliating Sponge",
  "Kingfisher Shower Kit – Kingfisher® Bathboard with Handle & Toe-Foot Sponge",
  "Kingfisher Bathroom Kit – Kingfisher® Bath Board with Handle & Exfoliating Sponge"]),
 (H, "name is an explicit long-handled wash sponge or sponge set -- a personal hygiene aid, matching the company's own Long Handled Sponges division", [
  "Long Handled Complete Sponge Bundle – Ultimate Pamper Set", "Long Handled Bath & Body Sponge Duo",
  "Long Handled Deluxe Shower Sponge Duo", "Long Reach Sponge & Exfoliator Sponge Duo",
  "Long Handled Foot Care Sponges Duo", "Long Handled Pampering Sponges Duo"]),
 (D, "name is an explicit sock aid, shoe horn, stocking frame or reacher kit -- a classic daily-living dressing aid", [
  "Long Handled Plastic Shoe Horn", "Ezy-On Tall Compression Stocking Frame",
  "Foxy Plastic Sock Aid/Stocking Aid",
  "The Travel Kit – Foxy Sock Aid & Folding Classic PRO Reacher/Grabber",
  "The Car Kit – Leg Lifter & Folding Classic PRO Reacher 680 mm (27″)",
  "Ezy-On Compression Frame Aid Duo Pack", "Sock Assist Kit – Soxon and Shoe Horn",
  "Sock & Shoe Application Kit – Foxy Sock Aid and Shoe Horn", "Sock Aid Kit – Soxon and Foxy"]),
]
EVIDENCE = ("The Helping Hand Company's own storefront product records (helping-hand.com, Shopify), "
            "crawled and detail-read 05/11/2026 -- data/supplier-products.json. The product sits in the "
            "non-taxonomy 'Uncategorised' or 'Bundles' collection, so it is mapped at product level by its own name.")
DECIDED = "framework-coverage-batch, 05/11/2026, Aids for Daily Living"

def main():
    prods = json.load(open("data/supplier-products.json"))["suppliers"][S]["products"]
    byname = {p["n"]: p for p in prods}
    doc = json.load(open(MAP))
    have = {(e["supplier"], e["division"]) for e in doc["entries"] if e.get("kind") == "product-override"}
    added, parts = 0, []
    for hub, why, names in GROUPS:
        for n in names:
            assert n in byname, "not in crawl: " + n
            parts.append({"division": n, "hub": hub, "why": why})
            if (S, n) in have:
                continue
            doc["entries"].append({"kind": "product-override", "supplier": S, "division": n, "products": 1,
                "categories": [byname[n]["division"]], "examples": [n], "hub": hub, "notTaxonomy": False,
                "evidence": EVIDENCE, "why": why, "decidedIn": DECIDED, "addedOn": "2026-11-05"})
            added += 1
    seed_format.write_like(MAP, doc)
    json.dump({"_note": "DOCUMENTATION ONLY -- product-override entries live in differentiator-category-map.json; merge_differentiator_parts.py cannot take product-name keys.",
               "supplier": S, "decisions": parts}, open(PART, "w"), indent=1, ensure_ascii=False)
    print("added", added, "product-override entries")
main()
