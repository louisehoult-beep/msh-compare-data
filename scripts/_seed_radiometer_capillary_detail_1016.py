#!/usr/bin/env python3
"""One-off, 16/10/2026 (^o626): manufacturer detail records for Radiometer UK's three
blood-gas sampling products, so the product-override to bloodcoll:abg (29/09/2026)
can publish. Without a detail record (or NHSSC record) a product has no source and the
Differentiator builder holds it.

Source: Radiometer UK's own public product pages, read 16/10/2026
(robots.txt disallows only /sitecore). Sentences are the pages' own, verbatim; nothing
inferred. Run once from the repo root.
"""
import json

BASE = "https://www.radiometer.co.uk/en-gb/products/blood-gas-syringes-and-capillaries/"
DATE = "2026-10-16"
REC = {
    "Safe Clinitubes": ("safe-clinitubes", (
        "In neonates, capillary blood samples are desirable over other forms of sampling. "
        "safe CLINITUBES, the capillary tubes from Radiometer, are made of plastic, not glass."),
        ["Minimise the risk of contact with patient blood",
         "Reduce the risk of preanalytical errors, specifically the formation of clots",
         "Match the sample volume requirements of different analysers",
         "Electrolyte balanced heparin 45 μl, 70 μl, 100 μl and 125 μl",
         "High concentration heparin 55 μl and 85 μl"]),
    "Self Fill": ("self-fill", (
        "With the safe PICO self-fill blood gas syringe, you can improve your mixing and "
        "get results you can trust."),
        ["Mixing ball helps you obtain a homogeneous sample",
         "safe TIPCAP minimises the risk of blood contact",
         "Barcode helps you get a correct match between your patient and blood sample",
         "Integrated needle shield device minimises the risk of needlestick injury",
         "Dry electrolyte-balanced heparin reduces the risk of your sample clotting"]),
    "Aspirating": ("aspirating", (
        "The safe PICO Aspirator has an integrated mixing ball and a recommended fill volume "
        "of 1.0 mL."),
        ["Barcode helps you get a correct match between your patient and blood sample",
         "Vented safe TIPCAP is designed to safely remove air bubbles with minimised risk of blood exposure",
         "Integrated mixing ball and automatic mixing helps you obtain a homogeneous sample",
         "Uniquely designed, dry, electrolyte-balanced heparin brick reduces the risk of clots"]),
}

p = "data/supplier-product-detail.json"
dd = json.load(open(p, encoding="utf-8"))
for name, (slug, desc, feats) in REC.items():
    key = "Radiometer UK|" + name.lower()
    if key in dd["products"]:
        print("already present", key)
        continue
    dd["products"][key] = {"supplier": "Radiometer UK", "product": name,
                           "sourceUrl": BASE + slug, "capturedDate": DATE,
                           "parsed": "structured", "description": desc,
                           "features": feats, "image": None}
    print("added", key)
open(p, "w", encoding="utf-8").write(json.dumps(dd, ensure_ascii=False, indent=1) + "\n")
