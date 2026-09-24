#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 24/09/2026.

Meril UK Pvt Ltd (Meril Life Sciences' UK arm, awarded on Total Orthopaedic
Solutions 3) crawls with 277 held products across 12 flat divisions spanning
infection prevention, diagnostics, vascular/peripheral-vascular/neurovascular
intervention, endo surgery, urology, cardiac surgery, ENT, orthopaedics,
sports medicine and surgical robots. None of the 12 divisions is a single
"speciality:type" (mixed-division-mapping policy,
data/identity-vocabulary-policy.json), so mapping happens at product level.

This seeder maps only the products whose own name, cross-checked against
Meril's own merillife.com product pages this run, unambiguously identifies an
orthopaedic implant, trauma-fixation device or joint-replacement robotic
system, for the "Total Orthopaedic Solutions 3" framework (catsInScope:
ortho:cement/equip/implant/trauma):

  - The 4-product "Desti Knee"/"Freedom"/"Opulent"/"Opulent Uni" and the
    7-product "Latitud"/"Auric Bionik" range: Meril's own
    merillife.com/our-products/orthopedics/ pages confirm these as total
    knee and total hip replacement implant systems -> ortho:implant.
  - The 10-product "Armar"/"Ket"/"Pfrn"/"Elastic Titanium Nail"/"Cannulated
    Titanium Tibial Nail System" range: plate-and-screw and intramedullary
    nailing systems for fracture fixation -> ortho:trauma.
  - "Misso Robotic System" / "Cuvis Joint" (and their near-duplicate capture
    under the "Surgical Robots" division, "Misso Robotic System Surgical
    Robots" / "Cuvis Joint Surgical Robot" — same physical products, read
    twice under two category pages; not de-duplicated here, noted for a
    future duplicate-product-same-supplier-site pass): Meril's own
    merillife.com/our-products/orthopedics/misso-robotic-system page
    confirms MISSO as an orthopaedic joint-replacement surgical robot,
    matching the existing Stryker "Robotic Consumables — Total Knee" ->
    ortho:equip precedent already in this map.
  - The 14-product Sports Medicine implant range (Rotafix Bio/Peek/Ti/Peek
    Ti suture anchors, Filahook, Flexibutton, Endostud, the four Bio
    Ference/Ference interference screws, and the two meniscal repair
    systems): soft-tissue fixation implants for ligament/meniscus repair,
    matching the existing Conmed "Implants And Suture Anchors" ->
    ortho:implant and Arthrex suture-anchor -> ortho:implant precedents
    already in this map.

NOT mapped (ambiguous, out of scope, or a different speciality by
established precedent), left held:
  - "Peek Peek" (Sports Medicine): an unexplained two-word capture with no
    confirmable identity of its own — not force-matched to the adjacent
    Rotafix Peek/Ti entries without direct evidence.
  - "Handx Robotics" / "Mizzo Flex Sa Robotics" / "Mizzo Endo 4000" (Surgical
    Robots): confirmed via merillife.com as general-surgery/soft-tissue
    robotic platforms (laparoscopic, urology, gynae, thoracic, colorectal,
    bariatric, ENT, GI, oncology) — not orthopaedic-specific.
  - The "Persist" arthroscopy-tower range (4K/HD/FHD endoscopes, monitors,
    shaver system, cold light source, trolley) and "Spinuss Rf Console"
    (Sports Medicine): arthroscopy visualisation/RF-ablation equipment.
    Established precedent in this map files this shape as mis:energy /
    theatres:theatre rather than ortho:equip (Farla Medical "Arthroscopy
    Ablation Probe" -> mis:energy, Stryker "Arthroscopic Pumps and Tubing
    Systems" -> theatres:theatre, Conmed "Edge Bipolar Arthroscopic Rf
    System" -> mis:energy) — correctly categorising this range is a
    different speciality's work, out of scope for this ortho batch, left
    held rather than guessed into ortho:equip.
  - "360 Infection Prevention Solution", "Diagnostics", "Vascular
    Intervention", "Endo Surgery" (beyond its already-mapped individual
    mis:staple/mis:trocar/mis:clips/mis:energy rows), "Urology", "Cardiac
    Surgery", "Peripheral Vascular Intervention", "Ent", "Neurovascular":
    real product ranges, different specialities, out of scope for this
    framework this run.

Run once: python3 scripts/_seed_meril_orthopedics_overrides_0924.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Meril UK Pvt Ltd"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the '%s' division; confirmed 24/09/2026 against Meril's own "
    "merillife.com product pages that the item is an orthopaedic implant, "
    "trauma-fixation device or joint-replacement surgical robot."
)

IMPLANT = {
    "Desti Knee": ("Orthopedics", "USFDA-approved/CE-certified total knee implant system (merillife.com/our-products/orthopedics/desti-knee)."),
    "Freedom": ("Orthopedics", "total knee implant system (merillife.com/our-products/orthopedics/freedom)."),
    "Opulent": ("Orthopedics", "TiNbN-coated total knee implant system (merillife.com/our-products/orthopedics/opulent)."),
    "Opulent Uni": ("Orthopedics", "unicompartmental variant of the Opulent knee implant system."),
    "Latitud Hip Replacement System": ("Orthopedics", "total hip replacement implant system."),
    "Latitud Monomod Stem": ("Orthopedics", "hip replacement femoral stem implant component."),
    "Latitud Cemented Femoral Stem": ("Orthopedics", "hip replacement femoral stem implant component."),
    "Latitud Femoral Head": ("Orthopedics", "hip replacement femoral head implant component."),
    "Latitud Acetabular Cup System": ("Orthopedics", "hip replacement acetabular cup implant component."),
    "Latitud Bipolar Cup System": ("Orthopedics", "hip replacement bipolar cup implant component."),
    "Auric Bionik Gold Surface": ("Orthopedics", "hip implant surface-coating range, part of the Latitud hip system."),
    "Rotafix Bio": ("Sports Medicine", "suture anchor implant, matching Conmed 'Implants And Suture Anchors' -> ortho:implant precedent."),
    "Rotafix Peek": ("Sports Medicine", "suture anchor implant (PEEK material variant)."),
    "Rotafix Ti": ("Sports Medicine", "suture anchor implant (titanium material variant)."),
    "Rotafix Peek Ti": ("Sports Medicine", "suture anchor implant (PEEK/Ti hybrid variant)."),
    "Filahook Soft Suture Anchor": ("Sports Medicine", "soft suture anchor implant."),
    "Flexibutton Adjustable Loop System": ("Sports Medicine", "adjustable-loop ligament fixation implant."),
    "Endostud Fixed Loop Fixation System": ("Sports Medicine", "fixed-loop ligament fixation implant."),
    "Bio Ference Bio Composite Interference Screw": ("Sports Medicine", "interference screw implant for ligament graft fixation."),
    "Bio Ference Bioabsorbable Interference Screw": ("Sports Medicine", "bioabsorbable interference screw implant."),
    "Ference Peek Interference Screws": ("Sports Medicine", "PEEK interference screw implant."),
    "Ference Ti Titanium Interference Screws": ("Sports Medicine", "titanium interference screw implant."),
    "Rapid Fix Allinside Meniscal Repair System": ("Sports Medicine", "meniscal repair implant device."),
    "Meniscal Darn Inside Out Meniscal Repair System": ("Sports Medicine", "meniscal repair implant device."),
}

TRAUMA = {
    "Armar Plate And Screw": "plate-and-screw fracture-fixation system.",
    "Ket Plate And Screws": "plate-and-screw fracture-fixation system.",
    "Ket Ss Trochanteric Femoral And Proximal Fixation Femoral Nail": "intramedullary nail for proximal femoral fracture fixation.",
    "Ket Ss Shaft Femur Ssfn": "intramedullary nail for femoral shaft fracture fixation.",
    "Ket Ss Shaft Tibia Sstn": "intramedullary nail for tibial shaft fracture fixation.",
    "Ket Ss Cannulated Tibial Nail": "cannulated intramedullary nail for tibial fracture fixation.",
    "Ket Ss Humerus Nail System": "intramedullary nail for humeral fracture fixation.",
    "Pfrn Nailing System": "proximal femoral nail (PFN) fracture-fixation system.",
    "Elastic Titanium Nail": "flexible/elastic titanium nail for fracture fixation.",
    "Cannulated Titanium Tibial Nail System": "cannulated intramedullary nail for tibial fracture fixation.",
}

EQUIP = {
    "Misso Robotic System": "orthopaedic joint-replacement surgical robot (merillife.com/our-products/orthopedics/misso-robotic-system).",
    "Cuvis Joint": "orthopaedic joint-replacement surgical robot, part of the MISSO/Cuvis Joint robotic platform.",
    "Misso Robotic System Surgical Robots": "same MISSO orthopaedic robot, captured a second time under the 'Surgical Robots' division page.",
    "Cuvis Joint Surgical Robot": "same Cuvis Joint orthopaedic robot, captured a second time under the 'Surgical Robots' division page.",
}

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0


def add(name, division, hub, why):
    global added
    key = (SUPPLIER, name)
    if key in known:
        print("already present, skipping:", name)
        return
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": hub,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE % division,
        "why": why,
    })
    added += 1


for name, (division, why) in IMPLANT.items():
    add(name, division, "ortho:implant", why)
for name, why in TRAUMA.items():
    add(name, "Orthopedics", "ortho:trauma", why)
for name, why in EQUIP.items():
    division = "Orthopedics" if name in ("Misso Robotic System", "Cuvis Joint") else "Surgical Robots"
    add(name, division, "ortho:equip", why)

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries" % added)
