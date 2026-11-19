"""One-off seeder, framework-coverage batch 13/11/2026, working CT Scanners
and Associated Options and Related Services (catsInScope includes
imaging:angio/ct/dxa/inject/mobile/mri/pet/xray).

Philips (Philips Electronics UK, curated under imaging with types
["ct", "serv"]) is awarded on this framework and sits in one flat
'Uncategorised' own-site division (1280 products, philips.co.uk crawl).
mixed-division-mapping policy applies: map at product level where the
product's own name unambiguously identifies its speciality, hold the
remainder. Only genuine scanner/simulator hardware names are mapped here
-- the many CT-prefixed clinical analysis/visualisation software options
in the same crawl (Ct Protocol Manager, Ct Lung Nodule Cad, SmartCT tools,
etc.) are left held: the gated vocabulary has no software-option type for
them and several (the SmartCT family) are interventional/angio overlay
tools, not CT-scanner hardware, so forcing them would be a guess.

Mapped:
  - Incisive Ct Ct Scanner, Ct 5300 Hc728285 Ct Scanner, Philips Ct 3500
    Hc728134 Computed Tomography Scanner, Rembra 728383 Ct Scanner,
    Spectral Ct 7500 Philips All New Spectral Detector Ct 750, Verida
    Spectral Detector Ct Scanner, Ct 6000 Ict Refurbished Ct Scanner ->
    imaging:ct. Each name states "Ct Scanner" or "Computed Tomography
    Scanner" directly.
  - Spectral Ct 7500 Rt 728343 Ct Simulator, Rembra Rt 728381 Ct
    Simulator, Areta Rt 728382 Ct Simulator -> imaging:mobile (gated
    label "Mobile & RT simulation"). Each name states "Rt ... Ct
    Simulator" -- a radiotherapy-planning CT simulator, not a diagnostic
    scanner.

Run once: python3 scripts/_seed_philips_ct_overrides_1113.py
"""
import json

MAP = "data/differentiator-category-map.json"

EVIDENCE = (
    "the supplier's own site filing (philips.co.uk), read by "
    "scripts/crawl_supplier_site.py, under the 'Uncategorised' division."
)

CT_SCANNERS = [
    "Incisive Ct Ct Scanner",
    "Ct 5300 Hc728285 Ct Scanner",
    "Philips Ct 3500 Hc728134 Computed Tomography Scanner",
    "Rembra 728383 Ct Scanner",
    "Spectral Ct 7500 Philips All New Spectral Detector Ct 750",
    "Verida Spectral Detector Ct Scanner",
    "Ct 6000 Ict Refurbished Ct Scanner",
]

RT_SIMULATORS = [
    "Spectral Ct 7500 Rt 728343 Ct Simulator",
    "Rembra Rt 728381 Ct Simulator",
    "Areta Rt 728382 Ct Simulator",
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
        "decidedIn": ("framework-coverage batch, CT Scanners and "
                       "Associated Options and Related Services, "
                       "13/11/2026"),
    })
    known.add(key)
    return 1


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    added = 0

    for product in CT_SCANNERS:
        added += add(doc, known, "Philips", product, "imaging:ct",
                      "the product's own name states \"Ct Scanner\" or "
                      "\"Computed Tomography Scanner\" directly.",
                      EVIDENCE)

    for product in RT_SIMULATORS:
        added += add(doc, known, "Philips", product, "imaging:mobile",
                      "the product's own name states \"Rt ... Ct "
                      "Simulator\" -- a radiotherapy-planning CT "
                      "simulator (gated label \"Mobile & RT simulation\"), "
                      "not a diagnostic scanner.",
                      EVIDENCE)

    doc["counts"]["pairs"] = len(doc["entries"])
    with open(MAP, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("added %d product-override entries" % added)


if __name__ == "__main__":
    main()
