#!/usr/bin/env python3
"""One-off: add product-override entries for GenX MediCare Ltd's "X-Dot" and
OscarTech UK's "lessa" ECG monitoring electrodes, both held because they
reach the Hub only via the NHS Supply Chain catalogue (neither supplier is
own-site crawled; GenX's own site 404s, OscarTech's too), so no (supplier,
division) mapping exists for either brand. Each catalogue item's own
description names it plainly: "ECG Monitoring Electrodes Solid/Wet Gel ...",
an exact match for the cardiology:ecg vocabulary type ("ECG electrodes").

GenX also sells an unrelated "AirX" respiratory range (nasal cannulas,
facemasks) under the same NHSSC supplier name — left untouched here, out of
scope for this framework (Electrodes, Ultrasound Gels, Defibrillation and
Related Consumables) and not a cardiology product.

Framework-coverage batch, Electrodes/Ultrasound Gels/Defibrillation, 17/10/2026.
"""
import json

PATH = "data/differentiator-category-map.json"

NEW = [
    {
        "supplier": "GENX MEDICARE LTD",
        "division": "X-Dot",
        "hub": "cardiology:ecg",
        "evidence": "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py "
                    "(data/nhssc-cache.json); item descriptions quoted in examples below, read "
                    "17/10/2026.",
        "why": "All 4 X-Dot catalogue lines are described \"ECG Monitoring Electrodes\" (solid/wet "
               "gel, carbon/metal centre stud, cloth/microporous/foam backing) — a direct match "
               "for the cardiology:ecg vocabulary type (\"ECG electrodes\"). GenX is not own-site "
               "crawled (404s on WP/WooCommerce/sitemap routes), so the NHSSC catalogue is the only "
               "route to this range; the supplier's unrelated AirX respiratory range (nasal "
               "cannulas, oxygen facemasks) is left unmapped here, out of scope for this framework.",
        "examples": ["ECG Monitoring Electrodes Solid Gel Adult Electrode Onset Carbon Centre Stud "
                     "with Cloth or Microporous Tape Material Backing",
                     "ECG Monitoring Electrodes Wet Gel Adult Electrode Onset Carbon Centre Stud "
                     "with Cloth or Microporous Tape Material Backing"],
    },
    {
        "supplier": "OSCARTECH UK",
        "division": "lessa",
        "hub": "cardiology:ecg",
        "evidence": "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py "
                    "(data/nhssc-cache.json); item description quoted in examples below, read "
                    "17/10/2026.",
        "why": "OscarTech UK's sole catalogue line is described \"ECG Monitoring Electrodes Solid "
               "Gel Foam press stud connection with adhesive conductor solid gel Size 32 x36mm\" — "
               "a direct match for the cardiology:ecg vocabulary type. OscarTech is not own-site "
               "crawled (404s), so the NHSSC catalogue is the only route to this item.",
        "examples": ["ECG Monitoring Electrodes Solid Gel Foam press stud connection with adhesive "
                     "conductor solid gel Size 32 x36mm"],
    },
]

with open(PATH) as f:
    data = json.load(f)

existing = {(e.get("supplier"), e.get("division")) for e in data["entries"]}
added = []
for item in NEW:
    key = (item["supplier"], item["division"])
    if key in existing:
        print("already present, skipping:", key)
        continue
    data["entries"].append({
        "kind": "product-override",
        "supplier": item["supplier"],
        "division": item["division"],
        "products": len(item["examples"]),
        "categories": [],
        "examples": item["examples"],
        "hub": item["hub"],
        "notTaxonomy": False,
        "evidence": item["evidence"],
        "why": item["why"],
        "decidedIn": "framework-coverage batch, Electrodes/Ultrasound Gels/Defibrillation, 17/10/2026",
    })
    added.append(key)

with open(PATH, "w") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print("added", len(added), "entries:", added)
