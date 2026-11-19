"""One-off seeder, framework-coverage batch 28/10/2026, working Endoscopy,
Endourology and Oncology Ablation Consumables (catsInScope includes
endoscopy:endo/uro/abl/access, gastro:haem/snare/stent/energy/diag,
endourology:stone/stent/laser/litho/urodyn, oncology:abl/stent/acc).

Pennamed Limited and Macromed UK Ltd are both awarded on this framework
and both sit in one flat 'Uncategorised' own-site division (crawled, no
division structure found in the URLs). mixed-division-mapping policy
applies: map at product level where the product's own name unambiguously
identifies its speciality, hold the remainder.

PENNAMED LIMITED -- an endoscopy-accessories supplier (Getinge group). Its
own site (pennamed.co.uk, read 28/10/2026) lists 24 product categories as
flat top-level pages, each self-describing a real GI-endoscopy consumable
or a non-clinical reprocessing/PPE line:

  Mapped (patient-procedure consumables, each name self-identifying its
  speciality without inference from Pennamed's other lines):
    - Metal Stents, Dilatation Balloons, Dilatation Inflation Device,
      Oesophageal Dilator Bougies -> gastro:stent (GI stents & dilatation).
    - Polyp Traps, Hot/Hybrid/Cold Snares -> gastro:snare (snares &
      resection; polyp traps are the companion device used with snares
      during polypectomy).
    - Clip Fixing Devices, Injection Needles -> gastro:haem (haemostasis &
      banding; the site confirms clips for haemostasis and injection
      needles "for bleeding control or lifting lesions").
    - Retrieval Nets, Foreign Body Retrieval Graspers -> endoscopy:access
      (access & retrieval devices; the site confirms both are for
      capturing/removing stones, fragments or foreign bodies).
    - Guidewires, Mouth Guards, Biopsy Forceps, Biopsy Valves/Disposable
      Button Sets/Valve Baskets, Spray Catheters, Irrigation Tubing & CO2
      Bottle Caps -> endoscopy:endo (endoscopy consumables; generic
      procedure-use items the site confirms as used during the endoscopic
      procedure itself, e.g. CO2 insufflation and dye-spray for
      chromoendoscopy, rather than reprocessing).

  Left held (genuinely out of scope -- reprocessing/PPE/non-clinical lines,
  the site confirms these as cleaning/handling/comfort products, not
  procedure consumables; no category in this framework's gated vocabulary
  fits them, so they stay held rather than forced):
    Bedside Clean Kits, Cleaning Brushes, Detergents & Cleaning Solutions,
    Dosing Pumps, Endoscope Transport, Flushing Devices & Associated
    Tubing, Patient Dignity, Personal Protective Equipment.

MACROMED UK LTD -- a multi-specialty distributor (vascular, spine,
interventional oncology, GI/biliary). Its own-site crawl is a single flat
range of ~42 brand names; most carry no descriptive word at all (bare
trademarks such as "Morrison", "Blueflow", "Osmium") and are left held as
genuinely ambiguous. Only names that are self-describing by their own
wording (not inferred from Macromed's other business lines) are mapped:

  - Hilzo Biliary Moving Cell Stent, Hilzo Covered Biliary Stent, Hilzo
    Biliary Stent, Hilzo Uncovered Pyloric/Colonic Stent, Hilzo Covered
    Pyloric/Colonic Stent, Hilzo Covered Oesophageal Stent, Hilzo ATM
    Oesophageal Stent, Hilzo Saessak Biliary Stent -> gastro:stent. HILZO
    is a real GI metal-stent brand (biliary/oesophageal stents from BCM
    Co Ltd / ABIS Inc, confirmed via published clinical literature on
    PubMed Central read 28/10/2026 -- "Hilzo Biliary Moving Cell Stent"
    is named in a published case series as an uncovered biliary metal
    stent); every example here names both "stent" and a GI segment
    (biliary/pyloric/colonic/oesophageal) in the product's own name.
  - Hilzo Ureteric Stent -> endourology:stent (ureteric stents & drainage;
    same HILZO brand, this one explicitly named for the ureter rather
    than a GI segment).
  - Amica MW Ablation, Amica RF Ablation, Dophi Radiofrequency Ablation
    System, Dophi Microwave Ablation System -> oncology:abl. Each name
    states its own modality (MW/RF ablation); DOPHI is confirmed via FDA
    GUDID device records and a published clinical study (PMC, read
    28/10/2026) as a real liver/lung/kidney tumour-ablation platform
    (Surgnova Healthcare Technologies).

  Left held (out of scope for this framework's vocabulary, or genuinely
  ambiguous bare trademarks -- never forced):
    Gangi-SoftGuard, Morrison, Cerv-x, Pezo, Tezo, ALN Vena Cava Filter
    (vascular filter), ADD, ADDplus, CosmicMIA, ObeliscPRO, Osmium,
    uCentum, IntraSPINE (spinal implant), Cera Vascular Plug (vascular),
    Fustar Steerable Sheath (ambiguous, no named procedure), Bishop
    Microcatheter (ambiguous, used across many specialities), Run & Run,
    Blueflow, GBM Cervical Cage (spinal implant), Golden Gate, Mambo,
    Osmycin, JETi Thrombectomy System (vascular thrombectomy, out of
    scope), Micro Stent (too generic -- no segment or speciality named),
    BioMimics 3D, Angiodroid, NeverTouch Gold-Tip EVLT Fibre (endovenous
    laser treatment for varicose veins, vascular, out of scope), MagnetOs
    Putty, MagnetOs Granules (bone-graft substitute, out of scope).

Run once: python3 scripts/_seed_pennamed_macromed_overrides_1028.py
"""
import json

MAP = "data/differentiator-category-map.json"

PENNAMED_EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the 'Uncategorised' division; confirmed against pennamed.co.uk's "
    "own 24 product-category pages, read 28/10/2026."
)

MACROMED_EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the 'Uncategorised' division."
)

PENNAMED = [
    ("Metal Stents", "gastro:stent",
     "Pennamed's own site: keeping narrowed GI/biliary passages open "
     "(oesophagus, bile duct)."),
    ("Dilatation Balloons", "gastro:stent",
     "Pennamed's own site: widening narrowed sections of the GI or biliary "
     "tract -- GI stents & dilatation."),
    ("Dilatation Inflation Device", "gastro:stent",
     "Pennamed's own site (listed as 'Inflation Devices'): controlled "
     "inflation of dilatation balloons -- companion device."),
    ("Oesophageal Dilator Bougies", "gastro:stent",
     "Pennamed's own site: dilating oesophageal strictures."),
    ("Polyp Traps", "gastro:snare",
     "Pennamed's own site: capturing polyps removed during polypectomy, "
     "the companion device to snares."),
    ("Hot/Hybrid/Cold Snares", "gastro:snare",
     "Pennamed's own site: looped-wire devices for removing polyps, hot "
     "snares adding electrocautery -- snares & resection."),
    ("Clip Fixing Devices", "gastro:haem",
     "Pennamed's own site: placing or securing endoscopic haemostatic "
     "clips -- haemostasis & banding."),
    ("Injection Needles", "gastro:haem",
     "Pennamed's own site: injecting agents into tissue for bleeding "
     "control or lifting lesions -- haemostasis & banding."),
    ("Retrieval Nets", "endoscopy:access",
     "Pennamed's own site: capturing and removing stones, fragments or "
     "foreign bodies -- access & retrieval devices."),
    ("Foreign Body Retrieval Graspers", "endoscopy:access",
     "Pennamed's own site: grasping and removing swallowed or lodged "
     "objects -- access & retrieval devices."),
    ("Guidewires", "endoscopy:endo",
     "Pennamed's own site: guiding catheters/devices along a path during "
     "endoscopic procedures such as ERCP cannulation."),
    ("Mouth Guards", "endoscopy:endo",
     "Pennamed's own site: protecting the patient's teeth and the "
     "endoscope during procedures."),
    ("Biopsy Forceps", "endoscopy:endo",
     "Pennamed's own site: taking tissue samples through the endoscope's "
     "working channel."),
    ("Biopsy Valves, Disposable Button Sets & Valve Baskets", "endoscopy:endo",
     "Pennamed's own site: single-use valves/buttons for endoscope ports."),
    ("Spray Catheters", "endoscopy:endo",
     "Pennamed's own site: delivering dye or other agents across the "
     "mucosal surface during the procedure."),
    ("Irrigation Tubing & Co2 Bottle Caps", "endoscopy:endo",
     "Pennamed's own site: irrigation-fluid tubing and CO2-insufflation "
     "cylinder caps used during the procedure."),
]

MACROMED_STENT = [
    "Hilzo Biliary Moving Cell Stent",
    "Hilzo Covered Biliary Stent",
    "Hilzo Biliary Stent",
    "Hilzo Uncovered Pyloric/Colonic Stent",
    "Hilzo Covered Pyloric/Colonic Stent",
    "Hilzo Covered Oesophageal Stent",
    "Hilzo ATM Oesophageal Stent",
    "Hilzo Saessak Biliary Stent",
]

MACROMED_ABL = [
    "Amica MW Ablation",
    "Amica RF Ablation",
    "Dophi Radiofrequency Ablation System",
    "Dophi Microwave Ablation System",
]


def add(doc, known, supplier, product, hub, why, evidence):
    key = (supplier, product)
    if key in known:
        print("already present, skipping:", supplier, "|", product)
        return 0
    doc["entries"].append({
        "kind": "product-override",
        "supplier": supplier,
        "division": product,
        "products": 1,
        "categories": ["Uncategorised"],
        "examples": [product],
        "hub": hub,
        "notTaxonomy": False,
        "evidence": evidence,
        "why": why,
        "decidedIn": "_seed_pennamed_macromed_overrides_1028.py",
    })
    known.add(key)
    return 1


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    added = 0

    for product, hub, why in PENNAMED:
        added += add(doc, known, "Pennamed Limited", product, hub, why,
                      PENNAMED_EVIDENCE)

    for product in MACROMED_STENT:
        why = ("HILZO is a real GI metal-stent brand (BCM Co Ltd / ABIS "
               "Inc) confirmed via published clinical literature (PubMed "
               "Central, read 28/10/2026); the product's own name states "
               "both 'stent' and the GI segment it targets.")
        added += add(doc, known, "Macromed UK Ltd", product, "gastro:stent",
                      why, MACROMED_EVIDENCE)

    added += add(doc, known, "Macromed UK Ltd", "Hilzo Ureteric Stent",
                 "endourology:stent",
                 "same HILZO brand, this product explicitly named for the "
                 "ureter rather than a GI segment -- ureteric stents & "
                 "drainage.",
                 MACROMED_EVIDENCE)

    for product in MACROMED_ABL:
        why = ("the product's own name states its ablation modality "
               "(MW/RF); DOPHI is confirmed via FDA GUDID device records "
               "and a published clinical study (PMC, read 28/10/2026) as "
               "a real liver/lung/kidney tumour-ablation platform "
               "(Surgnova Healthcare Technologies).")
        added += add(doc, known, "Macromed UK Ltd", product, "oncology:abl",
                      why, MACROMED_EVIDENCE)

    doc["counts"]["pairs"] = len(doc["entries"])
    with open(MAP, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("added %d product-override entries" % added)


if __name__ == "__main__":
    main()
