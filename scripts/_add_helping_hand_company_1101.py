#!/usr/bin/env python3
"""One-off: add "The Helping Hand Company" to supplier-seed.json, 01/11/2026.

Named by NHS Supply Chain's own contract launch brief for "Aids for Daily
Living" (Lots 14, 15, 35) -- previously UNRESOLVED (not in the seed at all).
Identity confirmed via the domain-proof-tier's strongest tier: the site itself
(https://www.helping-hand.com/, redirected from helpinghand.co.uk) prints
"Registered in England No. 02172956", which Companies House confirms as THE
HELPING HAND COMPANY (LEDBURY) LIMITED, SIC 32500 (manufacture of medical and
dental instruments and supplies), registered office Unit 9, Bromyard Road
Trading Estate, Ledbury, Herefordshire, HR8 1NS -- matching the company's own
long-standing Ledbury HQ (NHS directory listing, independent sources).
"""
import json

SEED = "data/supplier-seed.json"

RECORD = {
    "name": "The Helping Hand Company",
    "aliases": ["The Helping Hand Company", "Helping Hand",
                "The Helping Hand Company (Ledbury) Limited"],
    "specialities": ["Rehabilitation and mobility"],
    "products": [],
    "frameworks": [
        {
            "name": "Aids for Daily Living",
            "dates": "1 November 2023 to 31 October 2027",
            "note": "Named on NHS Supply Chain's own contract launch brief for "
                    "this framework, as \"The Helping Hand Company\" (Lot 14, "
                    "Lot 15, Lot 35). 31 suppliers on the framework.",
            "reference": "2022/S 000-033396",
            "category": "Rehabilitation and Community",
            "supplierCount": 31,
            "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/walking-aids-and-simple-aids-for-daily-living/",
            "source": "nhssc-brief",
            "capturedOn": "2026-11-01",
        }
    ],
    "alerts": [],
    "news": [],
    "links": [
        {
            "label": "Company website",
            "url": "https://www.helping-hand.com/",
            "source": "Proved by registration number on 2026-11-01: footer states "
                       "\"Registered in England No. 02172956\", matching "
                       "Companies House 02172956 (THE HELPING HAND COMPANY "
                       "(LEDBURY) LIMITED, active, SIC 32500). helpinghand.co.uk "
                       "301-redirects here.",
        }
    ],
    "awards": [],
    "curated": True,
    "note": "Added 01/11/2026 from NHS Supply Chain's own contract launch brief "
            "for the Aids for Daily Living framework (2022/S 000-033396). Was "
            "previously unresolved (not in the seed). The framework award and "
            "the website/company-number identity are both verified; the "
            "product range has not been crawled yet.",
    "verified": "2026-11-01",
    "source": "NHS Supply Chain contract launch brief (2022/S 000-033396), "
              "fetched 01/11/2026",
    "domain": "www.helping-hand.com",
    "companyNumberProof": {
        "number": "02172956",
        "route": "website-registration",
        "url": "https://www.helping-hand.com/",
        "evidence": "footer states \"Registered in England No. 02172956\"; "
                     "Companies House confirms THE HELPING HAND COMPANY "
                     "(LEDBURY) LIMITED, active, SIC 32500, registered office "
                     "Unit 9, Bromyard Road Trading Estate, Ledbury, "
                     "Herefordshire, HR8 1NS",
        "checkedOn": "2026-11-01",
    },
}


def main():
    doc = json.load(open(SEED))
    suppliers = doc["suppliers"]
    if any(s.get("name") == RECORD["name"] for s in suppliers):
        print("already present, not adding")
        return
    suppliers.append(RECORD)
    json.dump(doc, open(SEED, "w"), ensure_ascii=False, separators=(",", ":"))
    print("added The Helping Hand Company to supplier-seed.json")


if __name__ == "__main__":
    main()
