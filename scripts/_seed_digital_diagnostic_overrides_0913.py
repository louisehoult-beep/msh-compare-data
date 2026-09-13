#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 13/09/2026.

Digital Diagnostic Solutions (13.0% coverage) has been re-confirmed a
structural ceiling three times over (^o268, ^o303, ^o433): its 11
publishedElsewhere suppliers' crawled ranges are genuinely filed under other
specialities, not digital, and no route reaches the suppliers who actually
sell software/AI diagnostic products under this award. ^o450 (12/09) found a
narrow exception inside that: two of those suppliers each carry a HANDFUL of
named products, sitting inside an otherwise correctly-filed bulk, that are
themselves genuinely digital clinical software:

  * Getinge — "Tegris" and "Talis Hub" sit in Getinge's flat, wholly
    Uncategorised 351-product division (nothing in that division is mapped,
    so nothing about it is being overridden). Confirmed 13/09/2026 against
    Getinge's own product pages:
      - getinge.com/int/products/tegris — "Tegris OR Integration... one
        platform for each operating room" — a hardware+software OR video/data
        integration and hospital-efficiency platform.
      - getinge.com/int/products/talis-hub/ — "an integrated platform
        combining hardware, software, and support services" for vendor-neutral
        medical-device-to-EMR data capture.
    Both are clinical/departmental data-integration software platforms, which
    is what digital:sw covers. The other 349 products in the same division
    are untouched — this does not claim to have categorised Getinge's range,
    only these two named products.

  * Huntleigh — "Dopplex® Vascular Reporter Software" and "Dopplex® DR4
    Patient Record Software" sit inside the "Vascular Assessment" division,
    which is correctly mapped to ultrasound:hand for its handheld Doppler
    devices. These two are not devices; confirmed 13/09/2026 against
    Huntleigh's own product pages:
      - huntleigh-diagnostics.com/products/dopplex-vascular-reporter-software/
        — "Software... vascular reporting application... visualisation of
        waveforms on a PC and stored for reviewing, archiving and printing".
      - huntleigh-diagnostics.com/products/dr4/ — "Software... enables
        automated ABIs to be undertaken and saved in a patient database".
    Both are Windows PC reporting/patient-record software, not the Doppler
    hardware the rest of the division correctly maps to.

ADDENDUM 13/09/2026, same run: Sysmex UK's crawled range has one genuinely
held division ("Products Detail", 99 products, entirely unmapped) sitting
alongside its correctly-mapped pathology-analyser divisions elsewhere in this
file. Three named products in that bucket are 3DHISTECH-built digital
pathology software (Sysmex is 3DHISTECH's UK distributor for these), not lab
analysers:
  - "Quantcenter" — confirmed via 3dhistech.com's own software index (listed
    under Image Analysis) and product description: an image-analysis toolset
    for quantifying tissue structures, IHC/CISH/FISH staining.
  - "Slidecenter" — confirmed via 3dhistech.com's own software index and
    Sysmex's own description: a web-based database/repository for digitised
    tissue slides.
  - "Slideviewer" — confirmed via 3dhistech.com/software/slide-viewer/:
    "SlideViewer is software, not hardware... a digital microscope
    application designed for viewing and analyzing pathology slides."
A fourth candidate, "Slidedriver", was checked and left alone: it is a
physical USB 3-axis stage-control device (a hardware input peripheral), not
software, and does not cleanly fit any digital:* type — left held rather
than forced.

Run once: python3 scripts/_seed_digital_diagnostic_overrides_0913.py
Then write the part files and:  python3 scripts/merge_differentiator_parts.py --apply
"""
import json

MAP = "data/differentiator-category-map.json"

# (supplier, exact product name as crawled) — hub left null, filled by the
# part-file merge next.
PRODUCTS = [
    ("Getinge", "Tegris"),
    ("Getinge", "Talis Hub"),
    ("Huntleigh", "Dopplex® Vascular Reporter Software"),
    ("Huntleigh", "Dopplex® DR4 Patient Record Software"),
    ("Sysmex UK", "Quantcenter"),
    ("Sysmex UK", "Slidecenter"),
    ("Sysmex UK", "Slideviewer"),
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
