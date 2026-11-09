#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 09/11/2026.

Adds "Applied Medical Technology Limited" (Companies House 03561938,
Biggleswade), named by NHS Supply Chain's own contract launch brief for
Intravenous Cannula and Associated Products as an incumbent supplier. This is
a GENUINELY DIFFERENT company from the existing "Applied Medical UK Ltd"
record (Companies House 06126148, Bootle) already in the seed for the
Minimally Invasive Surgery framework -- different company number, different
registered address, different trade (portable subcutaneous infusion pumps
and sets vs laparoscopic/MIS devices). company_alias.py returned UNRESOLVED
for the exact string "Applied Medical Technology Limited" because no existing
alias covers it, confirming it is new, not a variant spelling.

Company number confirmed from the company's own site (applied-medical.co.uk
footer: "REGISTERED IN ENGLAND - REG NO.3561938"), matching Companies House
03561938 exactly -- a recorded source under verification-standard rule 11,
not a Companies House name search.

Run once: python3 scripts/_add_applied_medical_technology_1109.py
"""
import json

SEED = "data/supplier-seed.json"

NEW_SUPPLIER = {
    "name": "Applied Medical Technology Limited",
    "aliases": [
        "Applied Medical Technology Limited",
        "Applied Medical Technology Ltd",
    ],
    "specialities": ["Vascular access"],
    "products": [],
    "frameworks": [
        {
            "name": "Intravenous Cannula and Associated Products",
            "dates": "27 March 2023 to 31 March 2027",
            "note": (
                "Named on NHS Supply Chain's own contract launch brief for this "
                "framework, as \"Applied Medical Technology Limited\" (incumbent "
                "supplier). 21 suppliers on the framework."
            ),
            "reference": "2022/S 000-005941",
            "category": "Medical and Surgical Consumables",
            "supplierCount": 21,
            "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/intravenous-cannula-and-associated-products/",
            "source": "nhssc-brief",
            "capturedOn": "2026-11-09",
        }
    ],
    "alerts": [],
    "news": [],
    "links": [{"label": "Website", "url": "https://www.applied-medical.co.uk/"}],
    "awards": [],
    "curated": True,
    "note": (
        "Added 09/11/2026 during the framework-coverage batch for Intravenous "
        "Cannula and Associated Products. Not the same company as the existing "
        "\"Applied Medical UK Ltd\" record (Companies House 06126148, Bootle, "
        "Minimally Invasive Surgery framework) -- a distinct Companies House "
        "entity, distinct registered address, distinct trade. This company "
        "trades portable subcutaneous infusion systems (CRONO pumps, infusion "
        "sets, syringes) for home-use immunoglobulin/other subcutaneous "
        "therapy, per its own site (applied-medical.co.uk) and an EBME Expo "
        "exhibitor listing. Resolved via company_alias.py (returned UNRESOLVED "
        "for the exact award-brief name, confirming no existing alias covers "
        "it) and web search identifying the company's own site."
    ),
    "verified": "2026-11-09",
    "source": "NHS Supply Chain contract launch brief, Intravenous Cannula and Associated Products (2022/S 000-005941), fetched 09/11/2026; company's own site applied-medical.co.uk, fetched 09/11/2026.",
    "companyNumberCandidate": {
        "number": "03561938",
        "registeredName": "APPLIED MEDICAL TECHNOLOGY LIMITED",
        "companyStatus": "active",
        "incorporated": "1998-05-12",
        "confidence": "confirmed",
        "matchedOn": (
            "The company's own site (applied-medical.co.uk) footer prints "
            "\"REGISTERED IN ENGLAND - REG NO.3561938\", matching Companies "
            "House 03561938 exactly -- a self-stated registration number "
            "(verification standard rule 11), not a name search."
        ),
    },
}

doc = json.load(open(SEED))
names = {s["name"] for s in doc["suppliers"]}
if NEW_SUPPLIER["name"] in names:
    print("already present, nothing to do")
else:
    doc["suppliers"].append(NEW_SUPPLIER)
    json.dump(doc, open(SEED, "w"), ensure_ascii=False, indent=1)
    print("added", NEW_SUPPLIER["name"])
