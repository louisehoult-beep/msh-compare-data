#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 25/09/2026.

Celtic SMR Ltd (celticsmr.co.uk) crawls to a flat "Healthcare" division (50
products) mixing digital x-ray systems (Stationary/Portable Dr Systems,
Medici Dr Retrofits, Divario Cr Systems, generators, Dicompacs/Orca Medical
Cloud imaging software, stands/accessories), diagnostic ultrasound
(SonoScape-branded scanners), therapeutic laser (Hilterapia, MLS Class IV),
magnetotherapy and shockwave (Medispec) equipment under one bucket, plus
site-navigation artefacts (Calendly links, FAQ pages, case studies, banner
images) that crawl_supplier_site.py's sitemap route could not structurally
separate from real products — so the division cannot take one hub tag
(mixed-division-mapping policy, data/identity-vocabulary-policy.json).

Only the products whose own name is a confirmed SonoScape diagnostic
ultrasound model are mapped here, for the "Ultrasound Scanners and
Associated Options and Related Services" framework
(catsInScope: ultrasound:cart/hand/port/trans). Confirmed live 25/09/2026:
- celticsmr.co.uk's own "Diagnostic Ultrasound Scanners" page names E11,
  P25 Elite, P60 and S80 Elite (plus E2 and X3, not present in the current
  crawl capture — see note below) as SonoScape ultrasound scanners
  distributed for human healthcare (distinct from Celtic SMR's separate
  "Veterinary" division, which carries the same SonoScape family branded
  "...V" for equine/animal use and is out of scope here).
- SonoScape's own site (sonoscape.com) files E11 under
  products/ultrasound/portable_color_doppler, and P25 Elite, P60 and S80
  Elite under products/ultrasound/trolley_color_doppler. The Hub's own
  ultrasound vocabulary groups "Trolley & portable" as one type (port),
  distinct from "cart" (cart-based systems marketed as consoles rather than
  trolleys, e.g. GE LOGIQ E10, Canon's Aplio range, already mapped
  ultrasound:cart elsewhere in this map) and from "hand" (handheld
  probes/dopplers). So all four map to ultrasound:port, not ultrasound:cart.

NOTE: celticsmr.co.uk also names two smaller SonoScape models, E2 and X3, on
the same page, but neither appears in data/supplier-products.json's current
capture of this supplier — crawl_supplier_site.py's sitemap route drops any
resolved name under 3 characters (`len(name) < 3`), which silently discards
both 2-character model names. This is a crawler limitation, not a mapping
gap, and is left for a future crawler fix rather than touched here (a batch
scoped to one framework's data should not edit shared crawl code used by
every other supplier). Flagged in the run report, not fixed in this batch.

NOT mapped (different speciality or genuine navigation/site-component
artefacts), left held: Stationary/Portable Dr Systems, Medici Dr Retrofits,
Divario Cr Systems, Generators, Dicompacs Image Management System, Orca
Medical Cloud Solution, Stands And Accessories (digital x-ray — a different
NHSSC framework, not this one); Hilterapia/MLS Class IV laser, Magnetotherapy,
Medispec Shockwave (therapeutic laser/shockwave, not ultrasound); Page
Components, Calendly Link/Form, Image, Lets Start With What You Need, Ex
Demo, Who Are We Celticsmr, FAQ pages, Banner Image 1, Products/Products 1,
Case Studies(Title), Testimonial Banner, Charlotte/Rudi/Tracey, Pmt
Qs/Easy Qs, Roi Calculator, training/how-to/why-choose marketing copy pages
(site navigation and page-builder components, not products — matches the
nav-labels-are-not-products policy shape).

Run once: python3 scripts/_seed_celtic_smr_ultrasound_overrides_0925.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Celtic SMR Ltd"

EVIDENCE = (
    "celticsmr.co.uk/products/healthcare/diagnostic-ultrasound (confirmed live "
    "25/09/2026) names this SonoScape model as a human-healthcare diagnostic "
    "ultrasound scanner; sonoscape.com's own product filing (portable_color_doppler "
    "or trolley_color_doppler category, both read live 25/09/2026) confirms it is "
    "not the veterinary-branded '...V' equivalent under Celtic SMR's separate "
    "Veterinary division. Captured under the flat 'Healthcare' division because "
    "crawl_supplier_site.py's sitemap route only resolves one path segment as "
    "division (mixed-division-mapping policy)."
)

PRODUCTS = {
    "E11": "portable_color_doppler on sonoscape.com; Hub vocabulary files 'Trolley & portable' as one type (port).",
    "P25 Elite": "trolley_color_doppler on sonoscape.com; Hub vocabulary files 'Trolley & portable' as one type (port).",
    "P60": "trolley_color_doppler on sonoscape.com; Hub vocabulary files 'Trolley & portable' as one type (port).",
    "S80 Elite": "trolley_color_doppler on sonoscape.com; Hub vocabulary files 'Trolley & portable' as one type (port).",
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
        "hub": "ultrasound:port",
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": EVIDENCE,
        "why": why,
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries (hub=ultrasound:port)" % added)
