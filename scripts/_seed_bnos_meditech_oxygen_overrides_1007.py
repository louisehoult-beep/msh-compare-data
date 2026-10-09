#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 07/10/2026.

Respiratory Solutions: B.N.O.S Meditech Ltd is one of the framework's 37 awarded
suppliers. Its own site (meditech.uk.com, WordPress REST product catalogue, read
07/10/2026, 205 products across 16 divisions) files its oxygen therapy range under
"Regulators", "Cylinders" and "Demand Valves", but those divisions also hold
nitrous oxide, nitrous/oxygen blends, medical air, CO2 and analgesic (Entonox)
lines. A division-level map would be wrong for part of each, so this maps at
PRODUCT level, and only where the product's own name says oxygen and nothing
else: respiratory:o2 ("Oxygen therapy").

Held deliberately, same divisions: "Nitrous Oxide & Oxygen Regulators", "Carbon
Dioxide Regulators", "Nitrous Oxide Regulator", "Medical Air ..." regulators,
the two 50% nitrous/oxygen cylinders, "Analgesic Demand Valve" (pain relief, not
oxygen therapy), and the resuscitator, kit and flow-selector lines whose names do
not say which gas they serve.

Run once: python3 scripts/_seed_bnos_meditech_oxygen_overrides_1007.py
Then:     python3 scripts/build_differentiator.py
          python3 scripts/stamp_notice.py
          python3 scripts/build_coverage_ledger.py
"""
import json

SUPPLIER = "B.N.O.S Meditech Ltd"
HUB = "respiratory:o2"
SITE = "meditech.uk.com"
MAP = "data/differentiator-category-map.json"

NAMES = [
    "Oxygen Regulator, Pin Index, Therapy Only",
    "Oxygen Regulator, Pin Index, 2 x BS Schrader Therapy",
    "Oxygen Regulator, Pin Index, 1 x BS Schrader",
    "Oxygen Regulator, Pin Index, 2 x BS Schrader",
    "Oxygen Regulator, Pin Index, 1 x BS Schrader Therapy",
    "Oxygen Regulator, Bullnose Inlet, Therapy Only",
    "Oxygen Regulator, Bullnose Inlet, 1 x BS Schrader, Therapy",
    "Oxygen Regulator, Bullnose Inlet, 2 x BS Schrader, Therapy",
    "Oxygen Regulator, Bullnose Inlet, 1 x BS Schrader",
    "Oxygen Regulator, Bullnose Inlet, 2 x BS Schrader",
    "2L Medical Oxygen Cylinder",
    "5L Medical Oxygen Cylinder",
    "10L Medical Oxygen Cylinder",
    "40L Medical Oxygen Cylinder",
    "Oxygen Demand Valve",
]

doc = json.load(open(MAP, encoding="utf-8"))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for name in NAMES:
    if (SUPPLIER, name) in known:
        continue
    if "Cylinder" in name:
        filed = "Cylinders"
    elif "Demand Valve" in name:
        filed = "Demand Valves"
    else:
        filed = "Regulators"
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": HUB,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": "the supplier's own site filing (" + SITE + "), read by "
                    "scripts/crawl_supplier_site.py, WordPress REST product catalogue, "
                    "07/10/2026; filed under the company's own division \"" + filed + "\".",
        "why": "The product's own name is an oxygen therapy device (\"" + name + "\") and "
               "names no other gas, so it matches respiratory:o2 (\"Oxygen therapy\"). The "
               "division it sits in also holds nitrous oxide, nitrous/oxygen blend, medical "
               "air and analgesic lines, so the division itself is not mapped (mixed-division-"
               "mapping policy, data/identity-vocabulary-policy.json).",
        "decidedIn": "scripts/_seed_bnos_meditech_oxygen_overrides_1007.py",
    })
    added += 1
doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("map: added %d product-override entries (hub=%s)" % (added, HUB))
