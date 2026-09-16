#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 16/09/2026.

Electrodes, Ultrasound Gels, Defibrillation and Related Consumables: Electro
Spyres Healthcare Limited is one of the framework's 37 awarded suppliers,
crawled successfully (46 products, verified 2026-09-11) but held entirely
under a single "Uncategorised" division because the crawl read its sitemap
slugs rather than a WooCommerce/WordPress product taxonomy, so there is no
division structure to map as a block.

The division is a genuine mixed bag (ultrasound gel, ECG electrodes, wound
dressings, lubricating jelly, electrosurgical dispersive plates) so mapping
the whole division to one category would misfile most of it. Eight of its 46
product slugs name themselves unambiguously as this framework's own scope —
ultrasound gel and ECG electrodes — and get their own product-override
decision instead:

  * ultragel-ug50-* (5 slugs) — "ultrasound gel" in the name itself.
    -> cardiology:gel ("Ultrasound gels").
  * vitatrode-*-radiolucent-ecg-electrode-* (3 slugs) — "ecg-electrode" in
    the name itself. -> cardiology:ecg ("ECG electrodes").

Left out deliberately: electrogel-eg40-conductive-gel-300ml-bottle. It is a
conductive/electrode-prep gel, not an ultrasound diagnostic gel, and
cardiology:gel is gated specifically to "Ultrasound gels" — mapping it there
would misrepresent it to a rep comparing ultrasound gels. No other type in
the vocabulary fits a conductive gel, so it stays held rather than forced.
The other ~37 products (wound dressings, lubricant, chest seals, thermoblue
electrosurgical accessories) belong to other specialities entirely and are
out of scope for this framework's batch.

Run once: python3 scripts/_seed_electro_spyres_electrodes_gel_overrides_0916.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
          python3 scripts/build_differentiator.py
"""
import json

MAP = "data/differentiator-category-map.json"

# (supplier, exact product name as crawled) — hub left null, filled by the
# part file (data/differentiator-map-parts/Electro Spyres Healthcare Limited.json).
PRODUCTS = [
    ("Electro Spyres Healthcare Limited", "ultragel-ug50-ultrasound-gel-300ml-bottle"),
    ("Electro Spyres Healthcare Limited", "ultragel-ug50-ultrasound-gel-5l-jerrycan"),
    ("Electro Spyres Healthcare Limited", "ultragel-ug50-ultrasound-gel-5l-flexibag"),
    ("Electro Spyres Healthcare Limited", "ultragel-ug50-ultrasound-gel-5l-standup-pouch"),
    ("Electro Spyres Healthcare Limited", "ultragel-ug50-sterile-ultrasound-gel-25g-sachet"),
    ("Electro Spyres Healthcare Limited", "vitatrode-midi-acf-radiolucent-ecg-electrode-36mm"),
    ("Electro Spyres Healthcare Limited", "vitatrode-maxi-asf-radiolucent-ecg-electrode-40x32mm"),
    ("Electro Spyres Healthcare Limited", "vitatrode-mini-gp-radiolucent-ecg-electrode-30x25mm"),
]

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for supplier, name in PRODUCTS:
    key = (supplier, name)
    if key in known:
        print("already present, skipping:", supplier, "/", name)
        continue
    doc["entries"].append({
        "supplier": supplier,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": None,
        "notTaxonomy": False,
        "kind": "product-override",
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override placeholder entries (hub=null, ready for the part file)" % added)
