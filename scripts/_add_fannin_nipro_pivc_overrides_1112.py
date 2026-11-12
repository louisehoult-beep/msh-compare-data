#!/usr/bin/env python3
"""One-off: add product-override entries for Fannin (UK) Limited and Nipro
Medical Europe's peripheral IV cannula lines, held because both suppliers
reach the Hub only via the NHS Supply Chain catalogue (Fannin's own site,
fannin.eu, is robots.txt-blocked; Nipro is not own-site crawled either), so
no (supplier, division) mapping exists for either brand's cannula range.
Each catalogue item's own description names it plainly: "Safety Peripheral
Intravenous Cannula ..." / "Safety Integrated Cannula ..." — a direct match
for the vascular:pivc vocabulary type ("Peripheral IV cannula").

NPC-keyed throughout except three Fannin lines with no recorded NPC, kept
name-keyed only after confirming no collision: Nipro's own catalogue name
"NIPRO Safetouch" is reused for an unrelated winged metal needle/butterfly
device (FSB85204, FSB85207), so every Nipro entry here is NPC-keyed to avoid
misclassifying that unrelated product; Fannin's three blank-npc brand names
(Delta Ven, Neo Delta Straight, Delta S Safe 2) were checked against the
whole Fannin/Nipro catalogue and carry no other product under the same name.

Framework-coverage batch, Intravenous Cannula and Associated Products,
12/11/2026.
"""
import json

PATH = "data/differentiator-category-map.json"

EVIDENCE = ("NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py "
            "(data/nhssc-cache.json); item description quoted in examples below, read "
            "12/11/2026.")
WHY_FANNIN = ("Fannin's own site (fannin.eu) is robots.txt-blocked, so the NHSSC catalogue is "
              "the only route to this range. Described \"Safety Peripheral Intravenous Cannula\" "
              "or \"Safety Integrated Cannula\" with gauge/length — a direct match for the "
              "vascular:pivc vocabulary type (\"Peripheral IV cannula\"), not a central venous "
              "catheter, midline or PICC.")
WHY_NIPRO = ("Nipro Medical Europe is not own-site crawled for this range. Described \"Safety "
             "Peripheral Intravenous Cannula\" with gauge/length — a direct match for the "
             "vascular:pivc vocabulary type. NPC-keyed because Nipro's catalogue reuses the same "
             "brand name \"NIPRO Safetouch\" for an unrelated winged metal needle/butterfly "
             "device (FSB85204, FSB85207); a name-keyed override would wrongly reclassify those.")

NPC_ENTRIES = [
    # Fannin (UK) Limited
    ("Fannin (UK) Limited", "FSP5051", "SentraCan Safety",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Grey 16G x 45mm PUR"),
    ("Fannin (UK) Limited", "FSP5070", "Neo Delta Straight",
     "Safety Peripheral Intravenous Cannula Non-winged Yellow 24G x 19mm NON RETURNABLE ITEM"),
    ("Fannin (UK) Limited", "FSP85114", "Sentra Safety BC",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Blue 22Gx25mm with Blood Control Technology PUR"),
    ("Fannin (UK) Limited", "FSP85107", "Sentra Nuovo Safety",
     "Safety Integrated Cannula Yellow 24G x 19mm PUR Single Port Luer Lock"),
    ("Fannin (UK) Limited", "FSP5041", "SentraCan Safety",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Green 18G x 32mm PUR"),
    ("Fannin (UK) Limited", "FSP85233", "Sentracan Safety",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Yellow 24G x 19mm"),
    ("Fannin (UK) Limited", "FSP5059", "SentraCan Safety",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Green 18G x 45mm PUR"),
    ("Fannin (UK) Limited", "FSP85115", "Sentra Nuovo Safety",
     "Safety Integrated Cannula Pink 20G x 32mm PUR Dual Port with Y-Connector and 2 Needle Free Connectors"),
    ("Fannin (UK) Limited", "FSP85240", "Sentra Cath Safety Closed System",
     "Safety Integrated Cannula Yellow 24G x 19mm Single Port with Stopcock and Flashback"),
    ("Fannin (UK) Limited", "FVM85014", "Poly Medicure",
     "Safety Peripheral Intravenous Cannula Ported With Wings 20G x 32mm PUR blood control technology"),
    ("Fannin (UK) Limited", "FSP85070", "Neo Delta",
     "Safety Peripheral Intravenous Cannula Ported With Wings Blue 22G x 25mm NON RETURNABLE ITEM"),
    ("Fannin (UK) Limited", "FSP85076", "Neo Delta",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Yellow 24G x 19mm NON RETURNABLE ITEM"),
    ("Fannin (UK) Limited", "FVM85011", "Poly Medicure",
     "Safety Peripheral Intravenous Cannula Ported With Wings 18G x 32mm PUR blood control technology"),
    ("Fannin (UK) Limited", "FVM85010", "Poly Medicure",
     "Safety Peripheral Intravenous Cannula Ported With Wings 24G x 19mm PUR blood control technology"),
    ("Fannin (UK) Limited", "FSP85103", "Sentra Safety BC",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Green 18Gx45mm with Blood Control Technology PUR"),
    ("Fannin (UK) Limited", "FSP85105", "Sentra Nuovo Safety",
     "Safety Integrated Cannula Green 18G x 32mm PUR Dual Port with Y-Connector and 2 Needle Free Connectors"),
    ("Fannin (UK) Limited", "FSP85238", "Sentra Cath Safety Closed System",
     "Safety Integrated Cannula Pink 20G x 32mm Single Port with Stopcock and Flashback"),
    ("Fannin (UK) Limited", "FSP85067", "Neo Delta Ported",
     "Safety Peripheral Intravenous Cannula Ported With Wings Grey 16G x 45mm NON RETURNABLE ITEM"),
    ("Fannin (UK) Limited", "FSP85235", "Sentracan Safety",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Blue 22G x 25mm"),
    ("Fannin (UK) Limited", "FSP85237", "Sentrawin Safety",
     "Safety Peripheral Intravenous Cannula Non-winged Yellow 24G x 19mm"),
    ("Fannin (UK) Limited", "FSP85104", "Sentra Nuovo Safety",
     "Safety Integrated Cannula Green 18G x 45mm PUR Dual Port with Y- Connector and 2 Needle Free Connectors"),
    ("Fannin (UK) Limited", "FSN85071", "Sentraflex Safety",
     "Safety Peripheral Intravenous Cannula Ported With Wings Green 18G x 45mm"),
    ("Fannin (UK) Limited", "FSP5065", "SentraCan Safety",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Violet 26G x 19mm FEP"),
    ("Fannin (UK) Limited", "FSP5046", "SentraWin Safety",
     "Safety Peripheral Intravenous Cannula Non-winged Violet 26G x 19mm FEP"),
    # Nipro Medical Europe (NPC-keyed only — see WHY_NIPRO)
    ("Nipro Medical Europe", "FSN85055", "NIPRO Safetouch",
     "Safety Peripheral Intravenous Cannula Ported With Wings Pink 20G x 32mm Flashback Radiopaque PUR NON RETURNABLE"),
    ("Nipro Medical Europe", "FSP85220", "NIPRO Safetouch",
     "Safety Peripheral Intravenous Cannula Non-winged Pink 20G x 32mm Flashback Radiopaque PUR NON RETURNABLE"),
    ("Nipro Medical Europe", "FSP85204", "NIPRO Safetouch",
     "Safety Peripheral Intravenous Cannula Non-Ported With Wings Pink 20G x 32mm Flashback Radiopaque PUR NON RETURNABLE"),
    ("Nipro Medical Europe", "FSN85061", "NIPRO Safetouch",
     "Safety Peripheral Intravenous Cannula Ported With Wings Yellow 24G x 19mm Flashback Radiopaque PUR NON RETURNABLE"),
]

# Fannin's three blank-NPC lines — name-keyed, checked for collision above.
NAME_ENTRIES = [
    ("Fannin (UK) Limited", "Delta Ven",
     "Peripheral Intravenous Cannula Ported With Wings Yellow 24G x 19mm FEP NON RETURNABLE ITEM"),
    ("Fannin (UK) Limited", "Neo Delta Straight",
     "Safety Peripheral Intravenous Cannula Non-winged Violet 26G x 19mm NON RETURNABLE ITEM"),
    ("Fannin (UK) Limited", "Delta S Safe 2",
     "Safety Peripheral Intravenous Cannula Ported With Wings Blue 22G x 25mm NON RETURNABLE ITEM"),
]

with open(PATH) as f:
    data = json.load(f)

existing_npc = {(e.get("supplier"), e.get("npc")) for e in data["entries"] if e.get("npc")}
existing_div = {(e.get("supplier"), e.get("division")) for e in data["entries"] if not e.get("npc")}

added = []
for supplier, npc, brand, desc in NPC_ENTRIES:
    key = (supplier, npc)
    if key in existing_npc:
        print("already present, skipping:", key)
        continue
    why = WHY_FANNIN if supplier == "Fannin (UK) Limited" else WHY_NIPRO
    data["entries"].append({
        "kind": "product-override",
        "supplier": supplier,
        "division": "%s [%s]" % (brand, npc),
        "npc": npc,
        "products": 1,
        "categories": [],
        "examples": [desc],
        "hub": "vascular:pivc",
        "notTaxonomy": False,
        "evidence": EVIDENCE,
        "why": why,
        "decidedIn": "framework-coverage batch, Intravenous Cannula and Associated Products, 12/11/2026",
    })
    added.append(key)

for supplier, brand, desc in NAME_ENTRIES:
    key = (supplier, brand)
    if key in existing_div:
        print("already present, skipping:", key)
        continue
    data["entries"].append({
        "kind": "product-override",
        "supplier": supplier,
        "division": brand,
        "products": 1,
        "categories": [],
        "examples": [desc],
        "hub": "vascular:pivc",
        "notTaxonomy": False,
        "evidence": EVIDENCE,
        "why": WHY_FANNIN + " No NPC recorded on this catalogue line; checked against the whole "
               "Fannin/Nipro catalogue for a same-named non-cannula product before keying on the "
               "name alone — none found.",
        "decidedIn": "framework-coverage batch, Intravenous Cannula and Associated Products, 12/11/2026",
    })
    added.append(key)

data["counts"]["pairs"] = len(data["entries"])

with open(PATH, "w") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print("added", len(added), "entries")
