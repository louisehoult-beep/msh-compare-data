#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 26/11/2026: Harvest Healthcare on
Pressure Area Care and Patient Handling.

Identity: harvesthealthcare.co.uk/terms-and-conditions/ (read 26/11/2026) names
"Harvest Healthcare Limited (company number 07210261)" and the site footer prints
"Company Number: 7210261", matching the confirmed Companies House record.

Range: 183 products in the company's own top-level categories (WordPress REST
capture, 24/11/2026). Categories that hold one kind of product map at division
level. Mixed categories (Shear & Friction Relief, Fall Mats, Other Products,
Uncategorised) map at product level only; the rest of them is held. Cadence is
mapped as beds because each of its product pages (read 26/11/2026) describes a
headboard and footboard style for the Cadence bed frames; Pumps because the
Harvest pump pages read describe pumps for its active/pressure care mattresses.

Run once: python3 scripts/_seed_harvest_healthcare_handling_1126.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Harvest Healthcare"
EVIDENCE = ("the supplier's own site filing (harvesthealthcare.co.uk), read by "
            "scripts/crawl_supplier_site.py 24/11/2026; site and product pages "
            "re-read 26/11/2026")

DIVISIONS = {
    "Hoists & Stand Aids": ("handling:hoist", "hoists, stand aids and transfer movers"),
    "Active Cushions": ("handling:cushion", "active pressure care seat cushions"),
    "Static Cushions": ("handling:cushion", "static pressure-relieving cushions"),
    "Static Mattresses": ("handling:mattress", "static pressure care mattresses and extension infill"),
    "Hybrid Mattresses": ("handling:mattress", "hybrid pressure care mattresses"),
    "Active Mattresses": ("handling:mattress", "active pressure care mattresses"),
    "Pumps": ("handling:mattress", "pumps for the company's active pressure care mattresses"),
    "Positioning Aids": ("handling:mattress", "positioning pads, wedges and cushions (mattresses, overlays and positioning)"),
    "Woburn Range": ("handling:bed", "Woburn profiling beds"),
    "Cadence Range": ("handling:bed", "Cadence bed styles (headboard and footboard) on the Cadence frames"),
    "Bed Accessories": ("handling:bed", "bed accessories"),
    "Bed Bumpers": ("handling:bed", "bed side rail bumpers (Farla 'Side Rail Pads / Bed Bumpers' precedent)"),
    "Slings & Accessories": ("handling:sling", "patient handling slings"),
    "Showering & Toilet Aids": ("rehab:bath", "shower chairs and trolleys, commodes, toilet and bathing aids"),
    "Evacuation": ("rehab:access", "exitMASTER evacuation equipment"),
}

# (product name, hub, why)
PRODUCTS = [
    ("Freeway Scales Unit Incorporating QRS", "handling:scale", "hoist-mounted patient weighing scale"),
    ("Portable Wheelchair Weighbeams", "handling:scale", "wheelchair weighing beams"),
    ("Overbed Table", "handling:furniture", "overbed table, clinical furniture"),
    ("Connoisseur Overbed Table", "handling:furniture", "overbed table, clinical furniture"),
    ("Double Tilting Overbed Table", "handling:furniture", "overbed table, clinical furniture"),
    ("Non-Tilting Overbed Table", "handling:furniture", "overbed table, clinical furniture"),
    ("PivotPro Bedside Table", "handling:furniture", "bedside table, clinical furniture"),
    ("Slide Sheets", "handling:slide", "slide sheets"),
    ("Lateral Transfer Board", "handling:slide", "transfer board"),
    ("Modular Foam Overlay", "handling:mattress", "mattress overlay"),
    ("50mm White Foam Underlay", "handling:mattress", "mattress underlay"),
    ("Divan Bed", "handling:bed", "divan bed"),
    ("Wheelchair Leg Extensions", "rehab:chair", "wheelchair accessory"),
    ("Car Transit Wheelchair", "rehab:chair", "wheelchair"),
    ("Self Propel Wheelchair", "rehab:chair", "wheelchair"),
    ("Wall Mounted Evacuation Mattress with Storage Bag", "rehab:access", "evacuation mattress"),
    ("Evacuation Sheet for Active Mattresses", "rehab:access", "evacuation sheet"),
    ("Evacuation Sheet", "rehab:access", "evacuation sheet"),
]

caught = json.load(open("data/supplier-products.json"))["suppliers"][SUPPLIER]["products"]
by_div = {}
for p in caught:
    by_div.setdefault(p["division"], []).append(p["n"])
names = {p["n"] for p in caught}
assert not [d for d in DIVISIONS if d not in by_div], "division missing from capture"
assert not [n for n, _, _ in PRODUCTS if n not in names], "product missing from capture"

doc = json.load(open(MAP))
entries = doc["entries"]
known = {(e["supplier"], e["division"]) for e in entries}
rows = []
for div, (hub, why) in DIVISIONS.items():
    rows.append({"supplier": SUPPLIER, "division": div, "products": len(by_div[div]),
                 "categories": [], "examples": by_div[div][:4], "hub": hub,
                 "notTaxonomy": False, "evidence": EVIDENCE,
                 "why": "the company's own category holds " + why})
for name, hub, why in PRODUCTS:
    rows.append({"supplier": SUPPLIER, "division": name, "products": 1,
                 "categories": [], "examples": [name], "hub": hub,
                 "notTaxonomy": False, "kind": "product-override", "evidence": EVIDENCE,
                 "why": "named product: %s (mixed-division-mapping policy)" % why})
added = 0
for r in rows:
    if (r["supplier"], r["division"]) in known:
        raise SystemExit("already present: %r" % r["division"])
    entries.append(r); added += 1
doc["counts"]["pairs"] = len(entries)
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d entries" % added)

# Trim the site's footer sign-off ("For more Information about Harvest ... follow
# us on LinkedIn") from the captured page descriptions, leaving the product text.
# Applied after crawl_supplier_product_detail.py --supplier "Harvest Healthcare".
import re

DETAIL = "data/supplier-product-detail.json"
FOOTER = re.compile(r"\s*(For more [Ii]nformation(?: about Harvest|,? please visit)"
                    r"|For news and update|For more news).*$", re.S)
raw = open(DETAIL, encoding="utf-8").read()
det = json.loads(raw)
recs = det["products"]
recs = recs.values() if isinstance(recs, dict) else recs
n = 0
for r in recs:
    if r.get("supplier") == SUPPLIER and r.get("description"):
        new = FOOTER.sub("", r["description"]).strip()
        if new != r["description"]:
            r["description"] = new or None; n += 1
indent = 2 if raw.startswith('{\n  "') else (1 if raw.startswith('{\n "') else None)
with open(DETAIL, "w", encoding="utf-8") as f:
    json.dump(det, f, ensure_ascii=False, indent=indent)
    if raw.endswith("\n"):
        f.write("\n")
print("trimmed %d descriptions" % n)
