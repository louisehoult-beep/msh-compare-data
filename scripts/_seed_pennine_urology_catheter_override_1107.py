#!/usr/bin/env python3
"""One-off, 07/11/2026, differentiator-framework-coverage batch (Urology and
Bowel Management). Pennine Healthcare (Ivor Shaw Ltd) sits as a heldOnly
actionable supplier on this framework: its own site returns HTTP 401 to
automated reading (checked 22/09/2026, inside the 90-day refusal TTL, so a
re-crawl is forbidden by the brief's own rule), but NHS Supply Chain's own
catalogue — a sanctioned source, read independently of the refused site — is
already cached under the search term "Urology — intermittent catheters
(female standard and standard Nelaton); Urethrotech UCD; Camstent
BACTERIA-PHOBIC coated Foley catheter (distributed); Peezy Midstream urine
collection device" (data/nhssc-cache.json), holding 16 items, all of them
self-retaining (Foley) catheters under the Urethrotech and Camstent brand
names: 2-way and 3-way silicone catheters in a range of Ch sizes, male and
female, Nelaton and Tiemann tip. Every item's own NHSSC description reads
"Self-retaining catheter (foley)" — a single, unambiguous category, so this is
a (supplier, term) nhssc-term map entry, not a per-item product-override.

This does not touch the Peezy Midstream urine collection device or the female
intermittent catheters the same seed note describes — neither has its own
NHSSC-cache entry under this or any other cached term for this supplier, so
there is no catalogue-item data to attach a category to for those two; they
stay held, not forced.

Run once from the repo root: python3 scripts/_seed_pennine_urology_catheter_override_1107.py
"""
import json

SUPPLIER = "Pennine Healthcare (Ivor Shaw Ltd)"
TERM = ("Urology — intermittent catheters (female standard and standard Nelaton); "
        "Urethrotech UCD; Camstent BACTERIA-PHOBIC coated Foley catheter (distributed); "
        "Peezy Midstream urine collection device")
HUB = "continence:ind"


def save(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        if path.endswith("differentiator-category-map.json"):
            f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
        else:
            f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


cache = json.load(open("data/nhssc-cache.json", encoding="utf-8"))
rec = cache["products"][TERM]
assert rec["supplier"] == SUPPLIER
items = rec["items"]
examples = [it["desc"] for it in items[:8]]

doc = json.load(open("data/differentiator-category-map.json", encoding="utf-8"))
if any(e.get("kind") == "nhssc-term" and e["supplier"] == SUPPLIER and e["term"] == TERM
       for e in doc["entries"]):
    print("map: already present")
else:
    doc["entries"].append({
        "kind": "nhssc-term",
        "supplier": SUPPLIER,
        "term": TERM,
        "division": None,
        "products": len(items),
        "categories": [],
        "examples": examples,
        "hub": HUB,
        "notTaxonomy": False,
        "evidence": "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py "
                    "under supplier Pennine Healthcare (as \"PENNINE HEALTHCARE ALL ROUTES\" and "
                    "\"PENNINE HEALTHCARE EDIRECT\"); decision made on the catalogue's own item "
                    "descriptions above. Pennine Healthcare's own site (penninehealthcare.co.uk) "
                    "returns HTTP 401 to automated reading (checked 22/09/2026, inside the 90-day "
                    "refusal TTL) so this NHSSC catalogue entry is the only permitted route.",
        "why": "Every item's own NHSSC description reads \"Self-retaining catheter (foley)\" "
               "— 2-way and 3-way silicone Foley catheters, Urethrotech and Camstent brands, "
               "matching continence:ind (Indwelling (Foley) catheters).",
        "decidedIn": "differentiator-framework-coverage batch 07/11/2026, Urology and Bowel "
                     "Management",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    save("data/differentiator-category-map.json", doc)
    print("map: added, %d items" % len(items))
