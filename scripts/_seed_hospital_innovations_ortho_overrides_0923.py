#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 23/09/2026.

Hospital Innovations (UK tissue bank / allograft & instrument supplier,
hospitalinnovations.com, domain confirmed this run) crawls to 83 products under
one flat "Uncategorised" division spanning orthopaedic bone-graft/instruments,
spine (PliaFX), sports medicine (NanoFX, Hyalofast, meniscus/tendon allograft),
ENT/CMF (Piezotome/Piezomed rhinoplasty tips), and plastics/breast
reconstruction (DermACELL, Fortiva porcine dermis) — so the division cannot
take one hub tag (mixed-division-mapping policy,
data/identity-vocabulary-policy.json).

Only the products whose OWN NAME unambiguously names orthopaedic anatomy or an
orthopaedic-specific surgical term are mapped here, for the "Total Orthopaedic
Solutions 3" framework (catsInScope: ortho:cement/equip/implant/trauma).
Everything else in the division — generic bone-graft shapes with no anatomic
specificity (chips, cubes, particulate, cortical struts/plates/dowels/wedges,
iliac crest strips), spine/sports-med/ENT/dermal items, and "Innomed Complete
Catalogue" (a catalogue link, not a product) — is NOT touched and stays held.

Classed ortho:equip throughout rather than split equip/implant, matching the
existing precedent for allograft/tendon material already in the map (Lindare
Medical Ltd's "Allograft Cancellous Bone" and frozen tendons are both
ortho:equip, not ortho:implant) — this repo already treats bone-graft/
instrument material as ortho:equip rather than drawing a fresh line.

  - "Allograft Femoral and Humeral Heads" / "Allograft HTO Wedges": explicit
    joint-reconstruction anatomy (femoral/humeral heads, High Tibial
    Osteotomy) naming orthopaedic joint surgery specifically.
  - "Stulberg Hip Positioner" / "Stulberg Leg Positioner" / "Fromm - Femur and
    Tibia Triangles" / "Tibial Wedge Clamp": surgical positioning/clamping
    equipment named for the specific orthopaedic joint/bone it positions.
  - "CupX - Acetabular Cup Extraction System" / "Femoral Component Extractor" /
    "Glenosphere Component Retractor": revision hip/shoulder arthroplasty
    instrument systems named for the specific implant component they remove.
  - "Bodycad Fine Osteotomy(TM)": "osteotomy" is itself a bone-cutting surgical
    term.
  - "Orthovise(TM)": names orthopaedic scope in the product name itself.

NOT mapped (ambiguous or out of scope), left held:
  - Generic bone-graft shapes (chips, cubes, particulate, cortical
    struts/plates/dowels/wedges/shafts, iliac crest/ilium strips): used
    across dental, spine and orthopaedic surgery with no anatomic
    specificity in the name alone.
  - "Osteochondral Allograft(s)" / "Meniscus Allograft": joint cartilage
    restoration material that reads as Sports Med (the supplier files
    NanoFX/Hyalofast under its own "Sports Med" division), not this
    framework's ortho:* scope.
  - "Hohmann Retractor" / "Bone Hooks" / "Jones Mallet" / "Universal Screw
    Removal System": real orthopaedic-surgery instruments by trade knowledge,
    but the product name alone does not name a specific orthopaedic site —
    left held rather than mapped from outside inference.
  - "Innomed Complete Catalogue": a catalogue/brochure link mislabelled as a
    product entry, not itself a product.
  - Spine (PliaFX), Sports Med, Skin Allograft, "Non-Allograft Products"
    (Piezotome/Piezomed ENT/CMF tips), and dermal/breast-reconstruction items:
    real products, but a different speciality, out of scope for this batch.

Run once: python3 scripts/_seed_hospital_innovations_ortho_overrides_0923.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Hospital Innovations"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the flat 'Uncategorised' division; confirmed 23/09/2026 that the "
    "product's own name unambiguously names orthopaedic anatomy or an "
    "orthopaedic-specific surgical term."
)

PRODUCTS = {
    "Allograft Femoral and Humeral Heads": "explicit joint-reconstruction anatomy (femoral/humeral heads).",
    "Allograft HTO Wedges": "HTO = High Tibial Osteotomy, a specific orthopaedic knee procedure.",
    "Stulberg Hip Positioner": "named surgical positioning equipment for hip surgery.",
    "Stulberg Leg Positioner": "named surgical positioning equipment for lower-limb orthopaedic surgery.",
    "Fromm - Femur and Tibia Triangles": "positioning equipment named for the femur and tibia specifically.",
    "Tibial Wedge Clamp": "clamp equipment named for the tibia specifically.",
    "CupX - Acetabular Cup Extraction System": "revision hip arthroplasty instrument system named for the acetabular cup component it removes.",
    "Femoral Component Extractor": "revision arthroplasty instrument named for the femoral implant component it removes.",
    "Glenosphere Component Retractor": "shoulder arthroplasty instrument named for the glenosphere implant component.",
    "Bodycad Fine Osteotomy™": "\"osteotomy\" is itself a bone-cutting orthopaedic surgical term.",
    "Orthovise™": "names orthopaedic scope in the product name itself.",
}

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for name, why in PRODUCTS.items():
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
print("added %d product-override entries (hub=ortho:equip)" % added)
