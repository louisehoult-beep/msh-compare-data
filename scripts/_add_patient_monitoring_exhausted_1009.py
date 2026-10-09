#!/usr/bin/env python3
"""One-off exhaustion record, framework-coverage batch 09/10/2026.

Run once: python3 scripts/_add_patient_monitoring_exhausted_1009.py
"""
import json

PATH = "docs/framework-coverage-exhausted.json"

ENTRY = {
    "framework": "Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring Systems, Related Products and Services",
    "checkedOn": "2026-10-09",
    "coverageAtCheck": "34.3% (12/35)",
    "suppliersChecked": [
        "Draeger Medical UK",
        "Philips",
        "Zoll Medical UK Limited",
        "Probo Medical (formerly MIUS)",
        "Deltex Medical Ltd",
        "Pro Health Solutions Limited",
    ],
    "reason": (
        "All 6 remaining actionable items checked (4 publishedElsewhereNeedingCategory, "
        "1 heldNeedingCategory, 1 needDomain). Draeger Medical UK and Philips are both "
        "awarded here for capital patient-monitoring systems -- supplier-seed.json's own "
        "curated product lines name them explicitly ('Infinity monitoring' for Draeger, "
        "'IntelliVue monitoring'/'IntelliVue monitors' for Philips) -- but both terms were "
        "already queried against the live NHS Supply Chain public catalogue and recorded "
        "in data/nhssc-cache.json's notCatalogue map with reason 'capital patient "
        "monitoring'/'capital patient-monitoring equipment': NHSSC's public catalogue lists "
        "only orderable consumable SKUs, not capital equipment procured by direct framework "
        "call-off, so no NPC route exists for either. Both suppliers' own global corporate "
        "sites (draeger.com, philips.co.uk) were already crawl-attempted and refused (404 "
        "on WordPress/WooCommerce APIs, no readable product sitemap, checked 31/08/2026) -- "
        "no permitted route on either. Zoll Medical UK Limited's own-site crawl succeeded "
        "(zoll.com, 11/09/2026) and its Software/Data and Accessories divisions are already "
        "mapped (digital:sw, cardiology:defib); the remaining Emergency Care division (28 "
        "products) and Critical Care/Uncategorised singles carry only brand/model names "
        "(Zenix, ResQSystem, Zoll AED 3 BLS, Propaq MD, EMV Plus, Z Vent, R Series ALS, "
        "Powerheart G5, Bellavista 1000 variants, Mobilize apps, Iqool) -- none states "
        "'monitor' or any monitoring:gen/sens/spec term in the name itself, so none can be "
        "mapped under the mixed-division-mapping policy's own guard (unambiguous from the "
        "product's own name alone, never from brand recognition or the framework the award "
        "sits on); held, not forced. Probo Medical (formerly MIUS)'s full 842-product "
        "catalogue is already completely mapped by division (Acuson and Terason were "
        "mapped to ultrasound:trans by an earlier run today, 09/10/2026) -- every division "
        "is a resale brand line for diagnostic "
        "imaging/ultrasound/MRI-coil equipment (GE HealthCare, Philips, Mindray, Siemens, "
        "SonoSite, Chison, Samsung, Toshiba, Hitachi, Invivo, Medtron, Dexis, DURR, Hologic, "
        "Canon, Medrad, Medical Advances, Esaote) -- no patient-monitoring product exists "
        "anywhere in the range to map. Deltex Medical Ltd's deltexmedical.com crawl captured "
        "only 10 items across 'Uncategorised'/'Cardioq Odm'/'Cardioq Odm Plus', and every "
        "example ('How The Odm Works', 'Technical Specification', 'Accuracy Precision', "
        "'Pressure Parameters', 'Probe Solutions', 'Truevue', 'Pca', 'Hdicg') is a website "
        "page title from the CardioQ-ODM product pages, not a named product -- a failed "
        "capture under the nav-labels-are-not-products policy shape, needing a different "
        "crawl path to Deltex's real product names, not a category decision. Pro Health "
        "Solutions Limited carries no website on record (supplier-seed.json links: []); a "
        "fresh web search today found no company trading as 'Pro Health Solutions' in "
        "patient monitoring, and the only company-number candidate already on file "
        "(12576961, Companies House, status active) is registered at 20-22 Wenlock Road, "
        "London N1 7GU -- a mass company-formation-agent address -- under SIC codes for "
        "food-product manufacturing, mail-order/internet retail, other professional/"
        "technical activities and other human health activities, none of which indicate "
        "medical-device supply; the seed record already correctly withholds the number and "
        "flags identityUnconfirmed: true, which this run's check confirms rather than "
        "overturns. No permitted route left on any of the 6."
    ),
    "wouldReopenIf": (
        "A new supplier is awarded on this framework; Draeger's or Philips' own corporate "
        "site becomes crawlable, or a future NHS Supply Chain catalogue refresh ever lists "
        "'Infinity monitoring'/'IntelliVue monitoring' as orderable lines (the recorded "
        "reason is structural -- capital equipment is not in the public catalogue -- so "
        "this is unlikely but not impossible if NHSSC changes what it lists); a genuine "
        "monitoring product is confirmed for Zoll from a verified primary source naming it "
        "as such (not brand inference from a model number); Pro Health Solutions Limited's "
        "real website or a confirmed company number is identified; or Deltex Medical Ltd's "
        "catalogue is recaptured with real CardioQ-ODM product names instead of page titles."
    ),
}

doc = json.load(open(PATH))
names = {f.get("framework") for f in doc["frameworks"]}
if ENTRY["framework"] in names:
    raise SystemExit("already present, aborting: %r" % ENTRY["framework"])

doc["frameworks"].append(ENTRY)
with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("added exhausted entry for", ENTRY["framework"])
