#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 16/09/2026.

Electrodes, Ultrasound Gels, Defibrillation and Related Consumables: Salter
Labs UK Ltd is one of the framework's 37 awarded suppliers, crawled
successfully (409 declared products across 11 divisions, verified
2026-09-16) but entirely held because its own "Patient Monitoring" division
(53 products) is a genuine mixed bag spanning ECG leadwires, invasive blood
pressure cables, temperature probes, capnography/EtCO2 cannulas and
stethoscopes — mapping the whole division to one category would misfile most
of it.

Nine of its 53 products in that division name themselves unambiguously as
this framework's own scope (ECG leadwires/systems, and one foetal scalp
electrode — Lot 6 of this framework's own 9 lots is literally "foetal scalp
electrodes"):

  * Multi-Link X2, ECG Leadwires, ApexPro FH, Maternal ECG Cables and
    Leadwires, ECG Monitoring Accessories (8 products) -> cardiology:ecg
    ("ECG electrodes" — the gated type nearest to ECG lead/consumable work;
    no separate "ECG leadwires" type exists in the vocabulary).
  * Fetal Spiral Electrode System (1 product) -> cardiology:ctg
    ("Foetal / CTG") — a foetal scalp electrode by name and function.

Left out deliberately, all in the same division: Invasive Blood Pressure
(IBP) Cables (a different measurement, not an electrode/ECG/gel/defib
product), MYOTouch Muscle Stimulator, nasal cannulas and EtCO2/capnography
lines (respiratory, not cardiology), temperature probes/cables, stethoscopes,
peak flow meter, Diagnostic Cardiology Paper and Fetal Monitoring Paper
(recorder paper, a stretch even as an "equip" accessory). Also left out: this
supplier's other 10 divisions (Emergency, Airway Management, Home Care,
Respiratory, AirLife Secure Products, Anesthesia, Resuscitation etc.), which
are respiratory/airway/anaesthesia products entirely outside this framework's
speciality and this run's scope.

Run once: python3 scripts/_seed_salter_labs_ecg_ctg_overrides_0916.py
Then:     python3 scripts/merge_differentiator_parts.py --apply
          python3 scripts/build_differentiator.py
"""
import json

MAP = "data/differentiator-category-map.json"

PRODUCTS = [
    ("Salter Labs UK Ltd", "Multi-Link X2™ Universal ECG System, Telemetry"),
    ("Salter Labs UK Ltd", "Multi-Link X2™ Direct Connect Telemetry Leadwires"),
    ("Salter Labs UK Ltd", "ECG Leadwires, Reusable"),
    ("Salter Labs UK Ltd", "ApexPro™ FH Reusable Leadwires"),
    ("Salter Labs UK Ltd", "Multi-Link X2™ Universal ECG System, Traditional Setup"),
    ("Salter Labs UK Ltd", "ECG Monitoring Accessories"),
    ("Salter Labs UK Ltd", "Multi-Link X2™ Universal ECG System, Extra-Long Lead Setup"),
    ("Salter Labs UK Ltd", "Maternal ECG Cables and Leadwires"),
    ("Salter Labs UK Ltd", "Fetal Spiral Electrode System"),
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
