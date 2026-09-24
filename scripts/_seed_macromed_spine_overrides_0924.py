#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 24/09/2026.

Macromed UK Ltd (awarded on Total Orthopaedic Solutions 3, and separately on
Endoscopy/Endourology/Oncology Ablation Consumables) crawls to 44 products
under one flat "Uncategorised" division (macromed.co.uk's sitemap carries no
division structure) spanning spinal implants and vascular/GI interventional
devices — two different specialities under one supplier
(mixed-division-mapping policy, data/identity-vocabulary-policy.json), so
mapping happens at product level.

Macromed's own site organises its real catalogue under two brand archives —
product-category/spinal-products/ (4 items: GBM Cervical Cage, IntraSPINE,
MagnetOs Granules, MagnetOs Putty) and product-category/interventional-
products/ (18 items: the Hilzo stent range, ALN Vena Cava Filter, Cera
Vascular Plug, Fustar Steerable Sheath, BioMimics 3D, Angiodroid, NeverTouch
Gold-Tip EVLT Fibre, the two Dophi ablation systems, Micro Stent, Blueflow) —
but most of the sitemap-derived "Uncategorised" 44 sit outside both archives
(product pages exist but were never added to a brand taxonomy term on the
live site). Each of the 18 mapped here this run was independently confirmed
via its own manufacturer's site (ulrich medical AG for the spinal implant
hardware range, DBM Medical/Osmycin for the allograft, Woven Orthopedic
Technologies for OGMend) — not inferred from Macromed's own page alone.

Mapped ortho:implant (15) — spinal implant hardware:
  - "Cerv X" -> ulrich medical cerv-X cervical interbody cage.
  - "Pezo" -> ulrich medical pezo PEEK lumbar interbody cage family.
  - "Tezo" -> ulrich medical tezo titanium interbody cage.
  - "Add" / "Addplus" -> ulrich medical ADD/ADDplus vertebral body
    substitutes.
  - "Cosmicmia" -> ulrich medical cosmicMIA dynamic pedicle screw/rod spinal
    stabilisation system.
  - "Neon3" -> ulrich medical neon3 cervicothoracic screw-rod system.
  - "Obeliscpro" -> ulrich medical obeliscPRO vertebral body replacement
    device.
  - "Osmium" -> ulrich medical osmium anterior cervical plate system.
  - "Ucentum" -> ulrich medical uCentum thoracolumbosacral screw-rod system.
  - "Intraspine" -> Cousin Biotech IntraSPINE interspinous lumbar
    stabilisation implant.
  - "Gbm Cervical Cage" -> cervical fusion cage (matches Macromed's own
    product-category/spinal-products/ listing).
  - "Golden Gate" -> ulrich medical golden gate lateral plate system
    (thoracic/lumbar spine).
  - "Mambo" -> ulrich medical mambo cervical plate system.
  - "Ogmend" -> Woven Orthopedic Technologies OGmend implant-enhancement
    system for spinal screw fixation (FDA 510(k)-cleared for spine surgery).

Mapped ortho:equip (3) — bone-graft/allograft material, matching the
existing Hospital Innovations/Lindare Medical precedent already in this map
that allograft and synthetic bone-graft material is ortho:equip rather than
ortho:implant:
  - "Osmycin Antibiotic Allograft" -> antibiotic slow-elution bone allograft
    (DBM Medical Group / Osmycin V), used for chronic bone infection and
    bone-defect reconstruction.
  - "Magnetos Putty" / "Magnetos Granules" -> Kuros Biosciences MagnetOs
    synthetic bone-graft substitute, filed under Macromed's own
    product-category/spinal-products/ archive.

NOT mapped (confirmed a different speciality, or not confirmable), left
held:
  - "Gangi Softguard" / "Morrison": confirmed via web search as AprioMed
    interventional-radiology coaxial biopsy needle / steerable needle
    devices, distributed by Macromed — not orthopaedic.
  - "Bishop Microcatheter", "Run Run", "Amica Mw Ablation", "Amica Rf
    Ablation", "Jeti Thrombectomy System": read as vascular/interventional
    devices by name and by Macromed's own site structure (sitting outside
    the spinal-products archive, alongside the confirmed interventional
    range), but not individually source-confirmed this run — left held
    rather than guessed.
  - The 18 products in Macromed's own product-category/interventional-
    products/ archive (Hilzo stent range, ALN Vena Cava Filter, Cera
    Vascular Plug, Fustar Steerable Sheath, BioMimics 3D, Angiodroid,
    NeverTouch Gold-Tip EVLT Fibre, Dophi RF/MW ablation, Micro Stent,
    Blueflow): confirmed vascular/GI interventional devices, a different
    speciality, out of scope for this framework.

A capture-route gap (docs/framework-coverage-findings-2026-09-23-tos3.md,
same shape as ^o551/^o458) means none of Macromed's products carry a
manufacturer detail record (data/supplier-product-detail.json) or an NHSSC
catalogue match, so build_differentiator.py's publish gate will hold every
one of the 44 regardless of this mapping — correct and harmless now, and
will start publishing the moment that capture-route gap is fixed, with no
further mapping work needed (same accepted outcome as the Hospital
Innovations overrides added 23/09/2026).

Run once: python3 scripts/_seed_macromed_spine_overrides_0924.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Macromed UK Ltd"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the flat 'Uncategorised' division (macromed.co.uk sitemap carries "
    "no division structure); confirmed 24/09/2026 against the originating "
    "manufacturer's own site (ulrich medical AG / Cousin Biotech / Woven "
    "Orthopedic Technologies / DBM Medical) that the product is a spinal "
    "implant, spinal fixation hardware, or allograft bone-graft material."
)

IMPLANT = {
    "Cerv X": "ulrich medical cerv-X cervical interbody cage.",
    "Pezo": "ulrich medical pezo PEEK lumbar interbody cage family.",
    "Tezo": "ulrich medical tezo titanium interbody cage.",
    "Add": "ulrich medical ADD vertebral body substitute.",
    "Addplus": "ulrich medical ADDplus vertebral body substitute.",
    "Cosmicmia": "ulrich medical cosmicMIA dynamic pedicle screw/rod spinal stabilisation system.",
    "Neon3": "ulrich medical neon3 cervicothoracic screw-rod system.",
    "Obeliscpro": "ulrich medical obeliscPRO vertebral body replacement device.",
    "Osmium": "ulrich medical osmium anterior cervical plate system.",
    "Ucentum": "ulrich medical uCentum thoracolumbosacral screw-rod system.",
    "Intraspine": "Cousin Biotech IntraSPINE interspinous lumbar stabilisation implant.",
    "Gbm Cervical Cage": "cervical fusion cage, matches Macromed's own product-category/spinal-products/ listing.",
    "Golden Gate": "ulrich medical golden gate lateral plate system (thoracic/lumbar spine).",
    "Mambo": "ulrich medical mambo cervical plate system.",
    "Ogmend": "Woven Orthopedic Technologies OGmend implant-enhancement system for spinal screw fixation, FDA 510(k)-cleared for spine surgery.",
}

EQUIP = {
    "Osmycin Antibiotic Allograft": "antibiotic slow-elution bone allograft (DBM Medical Group / Osmycin V) for chronic bone infection and bone-defect reconstruction.",
    "Magnetos Putty": "Kuros Biosciences MagnetOs synthetic bone-graft substitute, matches Macromed's own product-category/spinal-products/ listing.",
    "Magnetos Granules": "Kuros Biosciences MagnetOs synthetic bone-graft substitute, matches Macromed's own product-category/spinal-products/ listing.",
}

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0

for name, why in list(IMPLANT.items()):
    key = (SUPPLIER, name)
    if key in known:
        print("already present, skipping:", name)
        continue
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": "ortho:implant",
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE,
        "why": why,
    })
    added += 1

for name, why in list(EQUIP.items()):
    key = (SUPPLIER, name)
    if key in known:
        print("already present, skipping:", name)
        continue
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": "ortho:equip",
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE,
        "why": why,
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries" % added)
