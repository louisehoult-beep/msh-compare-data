#!/usr/bin/env python3
"""One-off: product-level bloodcoll overrides for Reflex Medical Limited.

The 'Patient Monitoring' division (148 products) is a genuine mixed-division-
mapping-policy shape: a flat catch-all spanning ECG/monitoring consumables,
blood glucose, cuffs, thermometers AND blood collection tubes/sets/lancets,
so the whole division is correctly left unmapped (hub: null). These 14
products unambiguously name themselves as blood collection devices (BD
Vacutainer tubes/holders/safety-lok sets, Ayset collection tubes, UniStik
safety lancets) and are mapped at product level per the mixed-division-
mapping policy (standing authority, ruled 20/09/2026) — the remainder of the
division stays held, exactly as the policy requires.

Detail pages captured 29/09/2026 via crawl_supplier_product_detail.py so each
of these now has a manufacturer source and can actually publish.

Framework-coverage batch, Blood Collection Devices, 29/09/2026.
"""
import json

PATH = "data/differentiator-category-map.json"

# name -> (hub, why-specific)
ITEMS = {
    "Sodium Citrate 2ml Blood Collection Tube for Coagulation Testing": "bloodcoll:tube",
    "Ayset Fluoride Oxalate Blood Collection Tube 2ml": "bloodcoll:tube",
    "Ayset Clot Activator Blood Collection Tube 6ml": "bloodcoll:tube",
    "Ayset Clot Activator Blood Collection Tube 4ml": "bloodcoll:tube",
    "Ayset Sodium Citrate Blood Collection Tube 2.7ml": "bloodcoll:tube",
    "Ayset Gel & Clot Activator Blood Collection Tube 5ml": "bloodcoll:tube",
    "Ayset K3 EDTA Blood Collection Tube 2ml": "bloodcoll:tube",
    "BD Vacutainer Disposable Tube Holder": "bloodcoll:adapt",
    "BD Vacutainer Safety-Lok Blood Collection Set 23g x 178mm": "bloodcoll:set",
    "BD Vacutainer Safety-Lok 21g Blood Collection Set": "bloodcoll:set",
    "BD K2 EDTA Vacutainer Haematology (Purple) 4ml": "bloodcoll:tube",
    "BD SST II Advance Vacutainer Serum Analysis (Gold) 3.5ml": "bloodcoll:tube",
    "Unistik 3 Normal 23G Lancets – Box of 100": "bloodcoll:lance",
    "UniStik 3 Extra 21G Single Use Safety Lancet – Pack of 100": "bloodcoll:lance",
}

WHY_BY_TYPE = {
    "bloodcoll:tube": "Name is an explicit 'Blood Collection Tube' (or Vacutainer serum/haematology tube) "
                       "for venous sample collection — the vocabulary's 'Collection tubes & systems' type.",
    "bloodcoll:adapt": "A disposable holder that a Vacutainer needle screws into to draw a sample — the "
                        "vocabulary's 'Adaptors & tube holders' type, by name and function.",
    "bloodcoll:set": "A winged/safety blood collection set ('Safety-Lok') — the vocabulary's 'Winged / "
                      "safety collection sets' type, by name.",
    "bloodcoll:lance": "A single-use safety lancet for capillary sampling — the vocabulary's 'Lancets & "
                        "capillary' type, by name.",
}

with open(PATH) as f:
    data = json.load(f)

existing = {(e.get("supplier"), e.get("division")) for e in data["entries"]}
added = []
for name, hub in ITEMS.items():
    key = ("Reflex Medical Limited", name)
    if key in existing:
        print("already present, skipping:", key)
        continue
    data["entries"].append({
        "kind": "product-override",
        "supplier": "Reflex Medical Limited",
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": hub,
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py; "
                    "product detail captured 29/09/2026 via scripts/crawl_supplier_product_detail.py "
                    "(structured, reflexmedical.co.uk); found under the 'Patient Monitoring' division, "
                    "a genuine mixed catch-all (ECG/monitoring, blood glucose, cuffs, thermometers AND "
                    "blood collection) correctly left unmapped as a whole",
        "why": WHY_BY_TYPE[hub],
        "decidedIn": "framework-coverage batch, Blood Collection Devices, 29/09/2026 "
                      "(mixed-division-mapping policy, standing authority since 20/09/2026)",
    })
    added.append(name)

with open(PATH, "w") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print("added", len(added), "entries")
