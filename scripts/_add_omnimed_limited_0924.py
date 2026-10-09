#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 24/09/2026.

Omnimed Limited was awarded (per NHS Supply Chain's own contract launch
brief, reference 2024/S 000-029975) on "Endoscopy, Endourology and Oncology
Ablation Consumables and Associated Products" but had no supplier-seed.json
record at all -- the framework's ledger carried it as an unresolved name.

Identity confirmed from two primary sources that agree exactly:
  - Companies House 06478461 "OMNIMED LIMITED", active, incorporated
    21/01/2008, registered office Unit 1a, Abbas Business Centre Main Road,
    Itchen Abbas, Winchester, Hampshire, SO21 1BQ.
  - The company's own site (omnimed.co.uk), Terms of Service page, states
    verbatim: "Omnimed Limited, Unit 1A, Abbas Business Centre, Itchen
    Abbas, Winchester, Hampshire, England, SO21 1BQ. Registered in England
    and Wales. Company no. 6478461." -- same number, same address.
  - The site's own description ("the trusted, ISO accredited home of high
    quality, cost-effective endoscope accessories for the NHS and UK
    private healthcare market") matches the framework's own scope exactly.

Run once: python3 scripts/_add_omnimed_limited_0924.py
Then:     python3 scripts/crawl_supplier_site.py --supplier "Omnimed Limited" --domain omnimed.co.uk
"""
import json
import sys

sys.path.insert(0, "scripts")
from seed_format import write_like, describe

SEED = "data/supplier-seed.json"
NAME = "Omnimed Limited"

seed = json.load(open(SEED))
suppliers = seed["suppliers"]
if any(s.get("name") == NAME for s in suppliers):
    print("%s already in seed, nothing to do" % NAME)
    raise SystemExit(0)

record = {
    "name": NAME,
    "aliases": [NAME],
    "specialities": ["Endoscopy"],
    "products": [],
    "frameworks": [
        {
            "name": "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
            "dates": "1 October 2025 to 30 September 2027",
            "note": "Named on NHS Supply Chain's own contract launch brief for this framework, as \"Omnimed Limited\". 58 suppliers on the framework.",
            "reference": "2024/S 000-029975",
            "category": "Medical Technology",
            "supplierCount": 58,
            "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/endoscopy-endourology-oncology-ablation-consumables/",
            "source": "nhssc-brief",
            "capturedOn": "2026-09-24",
        }
    ],
    "alerts": [],
    "news": [],
    "links": [
        {
            "label": "Company website",
            "url": "https://www.omnimed.co.uk",
            "source": (
                "Proved omnimed.co.uk by registration number on 2026-09-24: the site's "
                "own Terms of Service page states \"Omnimed Limited, Unit 1A, Abbas "
                "Business Centre, Itchen Abbas, Winchester, Hampshire, England, SO21 "
                "1BQ. Registered in England and Wales. Company no. 6478461.\", agreeing "
                "exactly with Companies House 06478461's registered name and address."
            ),
        }
    ],
    "awards": [],
    "curated": True,
    "note": (
        "Added 24/09/2026 during framework-coverage batch work. Not previously in the "
        "seed at all -- the Endoscopy, Endourology and Oncology Ablation Consumables "
        "framework's coverage ledger carried it as an unresolved name. Identity "
        "confirmed from the company's own site cross-checked against Companies House; "
        "product range not yet crawled."
    ),
    "verified": "2026-09-24",
    "source": "NHS Supply Chain contract launch brief (2024/S 000-029975), fetched 2026-09-24; Companies House 06478461; omnimed.co.uk Terms of Service",
    "companyNumberCandidate": {
        "number": "06478461",
        "registeredName": "OMNIMED LIMITED",
        "companyStatus": "active",
        "incorporated": "2008-01-21",
        "confidence": "confirmed",
        "matchedOn": (
            "Found by Companies House name search on 2026-09-24. CONFIRMED same day: "
            "company number published on the company's own website, agreeing with the "
            "Companies House record -- https://www.omnimed.co.uk/policies/terms-of-service, "
            "read 2026-09-24."
        ),
        "confirmedOn": "2026-09-24",
        "confirmedRoute": "website-registration",
    },
    "companyNumberProof": {
        "number": "06478461",
        "route": "website-registration",
        "url": "https://www.omnimed.co.uk/policies/terms-of-service",
        "evidence": (
            "Omnimed Limited, Unit 1A, Abbas Business Centre, Itchen Abbas, Winchester, "
            "Hampshire, England, SO21 1BQ. Registered in England and Wales. Company no. 6478461."
        ),
        "checkedOn": "2026-09-24",
    },
}

suppliers.append(record)
fmt, round_trips = write_like(SEED, seed)
print(describe(SEED, fmt, round_trips))
print("added %s to %s" % (NAME, SEED))
