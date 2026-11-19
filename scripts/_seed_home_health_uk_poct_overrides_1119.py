#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 19/11/2026, working Laboratory
Diagnostics, Point of Care Testing and Pathology Managed Services.

Home Health (UK) Ltd is named on NHS Supply Chain's contract launch brief for
this framework. Its domain homehealth-uk.com was proved this run by
scripts/seed_supplier_domains.py on the REGISTRATION tier: the site footer
states "REGISTERED IN ENGLAND NO. 03176158", matching the Companies House
number already on record. Crawled live 19/11/2026: 524 products in 29 of the
company's own categories.

The range is mixed: consumer home tests, pet health, pharmacy remedies,
supplements and a "Professional Health Testing Kits" category. Mapped at
PRODUCT level per the mixed-division-mapping policy, and only inside the
"Professional Health Testing Kits" category: the products below name
themselves, by their own product name, as rapid test cassettes, multi-panel
drug test kits/cups or swab tests for professional use, i.e. point-of-care
tests. All map to pathology:poct ("Point of care testing").

NOT mapped (held, not forced): the postal/laboratory-processed hair drug test
kits and the "Lab Test Kits" category (sample collected, analysed in a lab, so
not point of care); breathalysers, their replacement sensors and mouthpieces
(breath-alcohol devices, not a pathology test); and every consumer/home
category (Drug & Alcohol, Pregnancy, Home Health Testing Kits, Diabetes home
kits, Pet Health and so on), which are retail self-tests rather than
professional point-of-care testing.

Run once: python3 scripts/_seed_home_health_uk_poct_overrides_1119.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Home Health (UK)"
HUB = "pathology:poct"

EVIDENCE = (
    "the product's own name on the supplier's own site (homehealth-uk.com), "
    "filed by the company under its own 'Professional Health Testing Kits' "
    "category, read by scripts/crawl_supplier_site.py 19/11/2026 (WordPress "
    "REST product catalogue)"
)
WHY = (
    "the manufacturer's own product name identifies this as a professional-use "
    "point-of-care test (a rapid test cassette, a multi-panel urine or oral "
    "fluid drug test kit/cup, or a swab test) -- mapped at product level per "
    "the mixed-division-mapping policy, because the same category also holds "
    "breathalysers, sensors, mouthpieces and lab-processed postal kits that "
    "are not point-of-care tests and are left held"
)

PRODUCTS = [
    "5in1 Professional Drug Test Kit | Multi-Panel Urine Test",
    "6in1 Professional Drug Test Kit | Multi-Panel Urine Test",
    "7in1 Professional Drug Test Kit (BUP) | Multi-Panel Urine Test",
    "7in1 Professional Drug Test Kit | Multi-Panel Urine Test",
    "8in1 Professional Drug Test Cup | Multi-Panel Urine Test",
    "10in1 Professional Drug Test Kit | Multi-Panel Urine Test",
    "7in1 Saliva Drug Test | Professional Oral Fluid Testing Kits",
    "Candida Infection Vaginal Swab Test",
    "Alpha-Fetoprotein (AFP) Rapid Test | Professional Use | 10 Pack",
    "10 CEA Lung Cancer Test Cassettes | Professional Use",
    "AMH Fertility Test Cassettes | Ovarian Reserve | Professional Use",
    "Measles Rapid Test Cassettes | IgG/IgM | Professional Use",
    "HCV Rapid Test Cassettes | Hepatitis C Antibody | 40 Pack",
    "Cortisol Rapid Test Kit | Saliva Stress Hormone Test",
    "Pancreatic Cancer Tumour Marker Pro CA19-9 Blood Test Kit 9 Tests",
    "CA15-3 Rapid Test Cassettes | Professional Use Only",
    "Bowel Cancer Faecal Occult Blood (FOB) / Transferrin GP / Pro Tests",
    "Troponin & H-FABP Combo Rapid Test Cassettes | Professional Use",
    "GP Professional Zinc Rapid Urine Test | One Step",
    "IBD Test Kit | Calprotectin & Lactoferrin, Professional Use",
    "CA19-9 Rapid Test Cassettes | Professional Use Only",
    "CA125 Rapid Test Cassettes | Professional Use Only",
    "Typhoid Rapid Test Cassettes | IgG/IgM | Professional Use",
    "TSH Rapid Test Cassettes | Professional Use Only",
    "Tuberculosis (TB) Diagnostic Blood Test – GP – Medical Professional Kits",
    "Strep A Throat Swab Test | Professional Testing Kit",
    "PSA Rapid Test Cassettes | Professional Use Only",
    "Glandular Fever Rapid Test Cassettes | Professional Use Only",
    "Malaria Rapid Test Cassettes | Professional Use Only",
    "Lyme Disease Rapid Test Cassettes | Professional Use Only",
    "H Pylori Blood Test | Professional Rapid Cassette",
    "Dengue NS1 Rapid Test Cassettes | Professional Use Only",
    "D-Dimer Rapid Test Cassettes | Professional Use Only",
    "Meningitis Urine Tests Streptococcus Pneumonia Professional Testing Kits",
    "Legionella Urine Test Kits GP Professional Test Kits",
]

caught = json.load(open("data/supplier-products.json"))
caught = caught.get("suppliers", caught)[SUPPLIER]["products"]
present = {p["n"] for p in caught if p.get("division") == "Professional Health Testing Kits"}
missing = [p for p in PRODUCTS if p not in present]
assert not missing, "not in this run's capture: %r" % missing

doc = json.load(open(MAP))
entries = doc["entries"]
known = {(e["supplier"], e["division"]) for e in entries}
added = 0
for name in PRODUCTS:
    if (SUPPLIER, name) in known:
        print("already present, skipping:", name)
        continue
    entries.append({
        "supplier": SUPPLIER, "division": name, "products": 1,
        "categories": [], "examples": [name], "hub": HUB,
        "notTaxonomy": False, "kind": "product-override",
        "evidence": EVIDENCE, "why": WHY,
    })
    added += 1
doc["counts"]["pairs"] = len(entries)
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries (hub=%s)" % (added, HUB))
