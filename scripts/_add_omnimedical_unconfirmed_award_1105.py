#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 05/11/2026 (redo of 04/11/2026 work).

Omnimedical Ltd is named on NHS Supply Chain's own contract launch brief for
Aids for Daily Living (Lot 20, Lot 29), 31 suppliers. It has no seed record.
Companies House's only exact-name match, OMNIMEDICAL LIMITED (04850088), is in
Liquidation with an unrelated SIC code, and no primary source states the legal
entity behind the award, so this is the "unconfirmable-awardee" shape in
data/identity-vocabulary-policy.json: publish under the name as given, marked
unconfirmed, no company number, domain, financials or logo attached.
"""
import json, sys
sys.path.insert(0, "scripts")
import seed_format

PATH = "data/supplier-seed.json"
RECORD = {
    "name": "Omnimedical Ltd",
    "aliases": ["Omnimedical Ltd"],
    "specialities": [],
    "products": [],
    "frameworks": [{
        "name": "Aids for Daily Living",
        "dates": "1 November 2023 to 31 October 2027",
        "note": ("Named on NHS Supply Chain's own contract launch brief for this framework, "
                 "as \"Omnimedical Ltd\" (Lot 20, Lot 29). 31 suppliers on the framework."),
        "reference": "2022/S 000-033396",
        "category": "Rehabilitation and Community",
        "supplierCount": 31,
        "url": ("https://www.supplychain.nhs.uk/product-information/contract-launch-brief/"
                "walking-aids-and-simple-aids-for-daily-living/"),
        "source": "nhssc-brief",
        "capturedOn": "2026-11-05",
    }],
    "alerts": [], "news": [], "links": [], "awards": [],
    "curated": True,
    "note": ("Added 05/11/2026 by the framework-coverage routine, resolving the unresolved-name "
             "gap on the Aids for Daily Living framework. Marked identityUnconfirmed under the "
             "unconfirmable-awardee policy (data/identity-vocabulary-policy.json): the only "
             "Companies House exact-name match, OMNIMEDICAL LIMITED (04850088), is in "
             "Liquidation with an unrelated SIC code, too weak to attach (rule 10/11). No "
             "company number, domain or financials attached."),
    "verified": "2026-11-05",
    "source": ("NHS Supply Chain contract launch brief (2022/S 000-033396); Companies House "
               "name search for \"Omnimedical\", read 05/11/2026"),
    "companyNumberNote": ("No Companies House match could be established: the only exact-name "
                          "match (04850088) is in Liquidation with an unrelated SIC code and is "
                          "not linked on name alone (rule 10)."),
    "identityUnconfirmed": True,
}
seed = json.load(open(PATH))
assert not any(s["name"] == RECORD["name"] for s in seed["suppliers"])
seed["suppliers"].append(RECORD)
seed_format.write_like(PATH, seed)
print("added Omnimedical Ltd")
