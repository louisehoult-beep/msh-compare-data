#!/usr/bin/env python3
"""One-off: add npc-keyed product-override entries for RPG Medical Limited's
4 gravity IV/blood administration sets in the NHS Supply Chain cache.

RPG Medical Limited's own site (rpgmedical.co.uk) is robots.txt-blocked, so
these items only exist via the NHSSC-cache route. RPG Medical already carries
curated types ['grav', 'pump'] for the bloodtx speciality in
data/compare-suppliers.json, sourced to DSI/2026/003 and its own framework
awards. The NHSSC-cache text-match (build_differentiator.py's label-token
check) requires the curated type's own label tokens to be a subset of the
item's description tokens. The label for 'grav' is "Gravity administration
sets" (tokens: gravity, administration, sets) — every one of these 4 items'
own NHS Supply Chain descriptions says "Administration set gravity ..."
(singular "set", not "sets"), so the plural token never matches and all 4
sit held despite being unambiguous gravity administration sets by their own
wording. Keyed on the NPC because the catalogue term groups them with 7
other RPG Medical items (blood-collection needles, lancets, tourniquets)
that are NOT administration sets and must not be swept in by a term-level
mapping.

Framework-coverage batch, Infusion Pumps and Administration Sets and
Associated Products, 18/10/2026.
"""
import json

PATH = "data/differentiator-category-map.json"
SUPPLIER = "RPG MEDICAL LIMITED"  # exact casing as stored in data/nhssc-cache.json

ITEMS = [
    ("FSB2248", "EZ-IV Admin 0001",
     "Administration set gravity solution 185cm vented/non vented 15 micron "
     "filter & prime stop MRI and CT safe Latex & DEHP free"),
    ("FSB2247", "EZ-IV Admin",
     "Administration set gravity solution Backcheck 185 cm vented/non vented "
     "15 micron filter & prime stop backcheck valve MRI and CT safe Latex & "
     "DEHP free"),
    ("FSB2501", "EZ-IV Admin 0002",
     "Administration Set for Gravity Solution Y-site 185cm vented/non vented "
     "15 micron filter & prime stop MRI and CT safe Latex & DEHP free"),
    ("FSB2230", "EZ-IV Blood Admin",
     "Administration set gravity blood and blood derivatives 185cm single "
     "chamber - 200 micron filter prime stop MRI - CT safe Latex / DEHP free"),
]

WHY = (
    "RPG Medical Limited's own curated bloodtx types are ['grav', 'pump'] "
    "(data/compare-suppliers.json, sourced to DSI/2026/003 and the company's "
    "NHS Supply Chain framework awards). This item's own NHS Supply Chain "
    "description names it a gravity administration set in its own words "
    "('Administration set gravity solution ...' / 'gravity blood and blood "
    "derivatives'), matching the 'grav' type (Gravity administration sets) "
    "unambiguously. It was held only because the curated label's plural "
    "'sets' does not literally appear in the NHSSC description's singular "
    "'set', a text-matching artefact, not an unmapped category or an "
    "ambiguous one — the supplier has no other curated type this wording "
    "could fit."
)

with open(PATH) as f:
    data = json.load(f)

existing = {(e.get("supplier"), str(e.get("npc"))) for e in data["entries"]
            if e.get("kind") == "product-override"}
added = []
for npc, name, desc in ITEMS:
    key = (SUPPLIER, npc)
    if key in existing:
        print("already present, skipping:", key)
        continue
    data["entries"].append({
        "kind": "product-override",
        "supplier": SUPPLIER,
        "division": "(NHS Supply Chain only)",
        "npc": npc,
        "products": 1,
        "categories": [],
        "examples": [desc],
        "hub": "bloodtx:grav",
        "notTaxonomy": False,
        "evidence": "NHS Supply Chain public catalogue, cached by "
                    "scripts/refresh_nhssc_cache.py (data/nhssc-cache.json), "
                    "NPC %s, supplier field \"%s\", item name %r, "
                    "description %r." % (npc, SUPPLIER, name, desc),
        "why": WHY,
        "decidedIn": "differentiator-framework-coverage run 18/10/2026 "
                     "(Infusion Pumps and Administration Sets and Associated "
                     "Products)",
    })
    added.append(npc)

with open(PATH, "w") as f:
    json.dump(data, f, indent=1)

print("added", len(added), "entries:", added)
