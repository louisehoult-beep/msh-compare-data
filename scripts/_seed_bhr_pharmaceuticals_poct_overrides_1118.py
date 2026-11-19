#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 18/11/2026.

BHR Pharmaceuticals Ltd was newly awarded on the Laboratory Diagnostics,
Point of Care Testing and Pathology Managed Services framework (seed
capturedOn 2026-11-15, the condition that makes a previously-exhausted
check on this framework stale). Crawled live 18/11/2026 (bhr.co.uk): a
degraded capture -- 91 of 106 product pages could not be read and fall
back to their URL slug, so the site is filed as one flat "Uncategorised"
range plus six tiny real divisions. This company's actual range is mixed:
travel-health/novelty retail (ParaKito mosquito repellent, a Universal
Studios plushie, a knee thermal pad) alongside a genuine point-of-care
diagnostics line.

Mapped at product level, not by division (there is no usable division),
per the mixed-division-mapping policy (data/identity-vocabulary-policy.json):
only the ten products below identify themselves unambiguously, by their own
readable product name, as point-of-care test devices/kits or their
analyser-specific consumables -- a urinalysis self-test strip, a rapid
antigen/HIV cassette assay, a named point-of-care allergy test, or a reagent
disc/analyser for one of those systems. All ten map to pathology:poct
("Point of care testing").

NOT mapped: the 91 products whose name could only be read as a URL slug
(including further probable POCT items -- a1cnow-portable-hba1c-...,
quo-test-hba1c-test-reagent-kit, several more medi-test-combi-* strips,
more aeskucare-* tests -- genuinely plausible, but their names are an
unverified slug read, not the product's own stated name, so they are left
held rather than guessed); the travel-health/novelty items (ParaKito,
Universal Studios plushie, Biosynex knee thermal pad); and "Quo-Test
Heated Shoulder Bag" (a carry case accessory, not itself a diagnostic
item -- held, not forced).

Run once: python3 scripts/_seed_bhr_pharmaceuticals_poct_overrides_1118.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "BHR Pharmaceuticals"
HUB = "pathology:poct"

EVIDENCE = (
    "the product's own name on the supplier's own site (bhr.co.uk), read "
    "by scripts/crawl_supplier_site.py 18/11/2026 (per-page name/breadcrumb, "
    "the only one of its six small named divisions or page-level reads to "
    "resolve for this product)"
)
WHY = (
    "the manufacturer's/retailer's own product name identifies this as a "
    "point-of-care diagnostic test, kit or an analyser-specific consumable "
    "for one (urinalysis self-test strips, a rapid antigen/HIV cassette "
    "assay, a named point-of-care allergy test, or a reagent disc for one "
    "of those systems) -- mapped at product level per the "
    "mixed-division-mapping policy, since this supplier's capture has no "
    "usable division structure to map as a whole"
)

PRODUCTS = [
    "Medi-Test 'Glucose' urinalysis self-test strips (50 strips)",
    "Quo-Test HbA1c Analyser",
    "Medi-Test Combi 8L (100 urinalysis strips)",
    "Medi-Test Ketone (50 urinalysis strips)",
    "Medi-Test Protein 2 (50 urinalysis strips)",
    "Medi-Test Combi 10SGL (100 urinalysis strips)",
    "BIOSYNEX Strep A cassette",
    "Chembio Stat-View HIV Assay",
    "AESKUCARE® Allergy FOUR: Point-of-Care Test for Common Allergies",
    "LOC 200 General Chemistry II Reagent Disc",
    "LOC 200 Renal Function / Glucose & Lipid Reagent Disc",
]

doc = json.load(open(MAP))
entries = doc["entries"]
known = {(e["supplier"], e["division"]) for e in entries}
added = 0
for name in PRODUCTS:
    key = (SUPPLIER, name)
    if key in known:
        print("already present, skipping:", name)
        continue
    entries.append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": HUB,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE,
        "why": WHY,
    })
    added += 1

doc["counts"]["pairs"] = len(entries)
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries (hub=%s)" % (added, HUB))
