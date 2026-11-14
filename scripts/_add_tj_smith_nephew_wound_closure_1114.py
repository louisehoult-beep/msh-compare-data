#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 14/11/2026.

Wound Closure framework names the awardee as "T.J Smith & Nephew Ltd"
(confirmed verbatim on NHS Supply Chain's own contract launch brief,
fetched 14/11/2026: https://www.supplychain.nhs.uk/product-information/
contract-launch-brief/wound-closure/). company_alias.py returns UNRESOLVED
for this name -- it has no supplier-seed record of its own.

Companies House confirms this is a real, DISTINCT legal entity:
T.J.SMITH AND NEPHEW,LIMITED, company number 00093994, incorporated
02/07/1907, registered office 101 Hessle Road, Hull HU3 2BN (read
14/11/2026: https://find-and-update.company-information.service.gov.uk/
company/00093994). It is the historic Hull manufacturing entity of the
Smith & Nephew group, held by Smith & Nephew Trading Group Limited
(00681256), itself held by Smith & Nephew UK Limited (04421171).

This is the "Smith+Nephew" supplier-seed record's OWN existing ownership
note (data/supplier-seed.json, ownershipCheckedOn 2026-10-01), written
before this run: "T.J.SMITH AND NEPHEW,LIMITED is a different registered
company from this record's [00156031, SMITH & NEPHEW HEALTHCARE LIMITED],
so it is not an alias; it is the same group and must not be listed as a
second competitor."

Applying identity-vocabulary-policy.json's parent-subsidiary-award-credit
policy directly (standing authority, no per-case escalation required):
  (a) the award credits to T.J Smith & Nephew Ltd exactly as NHS Supply
      Chain names it -- a record of its own, confirmed by Companies House.
  (c) was dropped 28/09/2026 (^o569): never add this as an alias of the
      Smith+Nephew record, which would wrongly re-route the award.

Respecting the existing "must not be listed as a second competitor" note:
no entry is added to any competitor-comparison file (compare-suppliers.json
etc.), and no products are attached. T.J. Smith and Nephew's own Hull site
is a manufacturing facility, not an independent brand/catalogue -- it trades
entirely under smith-nephew.com, which this record does not inherit, per
no-parent-catalogue-credit-to-uk-subsidiary. Record stays a minimal,
unpublished stub: confirmed identity, no domain, no products, until NHS
Supply Chain's own catalogue names a specific product against this entity.

Run once: python3 scripts/_add_tj_smith_nephew_wound_closure_1114.py
"""
import json

PATH = "data/supplier-seed.json"

RECORD = {
    "name": "T.J Smith & Nephew Ltd",
    "aliases": ["T.J Smith & Nephew Ltd", "T.J.SMITH AND NEPHEW,LIMITED"],
    "specialities": ["Wound care"],
    "products": [],
    "frameworks": [
        {
            "name": "Wound Closure",
            "dates": "19 January 2026 to 18 January 2030",
            "reference": "2025/S 000-001071",
            "category": "Medical and Surgical Consumables",
            "supplierCount": 39,
            "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/wound-closure/",
            "source": "nhssc-brief",
            "capturedOn": "2026-11-14",
            "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                      "framework, as \"T.J Smith & Nephew Ltd\". 39 suppliers on the framework."),
        }
    ],
    "alerts": [],
    "news": [],
    "links": [],
    "awards": [],
    "curated": False,
    "companyNumber": "00093994",
    "companyNumberSource": ("Companies House, read 14/11/2026: "
                             "https://find-and-update.company-information.service.gov.uk/company/00093994 "
                             "-- T.J.SMITH AND NEPHEW,LIMITED, incorporated 02/07/1907, "
                             "registered office 101 Hessle Road, Hull HU3 2BN."),
    "note": (
        "Added 14/11/2026 by the framework-coverage routine, resolving an "
        "unresolved-name gap on the Wound Closure framework. This is a DISTINCT "
        "confirmed legal entity (Companies House 00093994, Hull) from the Hub's "
        "existing \"Smith+Nephew\" record (00156031, SMITH & NEPHEW HEALTHCARE "
        "LIMITED) -- per that record's own ownership note and the "
        "parent-subsidiary-award-credit policy (identity-vocabulary-policy.json), "
        "the award credits here, exactly as NHS Supply Chain names it, and is "
        "never aliased or merged into the Smith+Nephew record (clause (c) was "
        "dropped 28/09/2026, ^o569). Per that same note, this entity 'must not be "
        "listed as a second competitor': it is not added to any competitor-"
        "comparison file. It is the group's historic Hull manufacturing operation, "
        "trading entirely under smith-nephew.com with no independent site or "
        "catalogue of its own, so no domain or products are attached here "
        "(no-parent-catalogue-credit-to-uk-subsidiary) -- stays a minimal, "
        "unpublished stub until NHS Supply Chain's own catalogue names a specific "
        "product against this entity."
    ),
    "verified": "2026-11-14",
    "source": ("NHS Supply Chain contract launch brief (2025/S 000-001071), fetched "
               "14/11/2026; Companies House company 00093994, read 14/11/2026."),
    "_specialitiesEvidence": (
        "Speciality assigned solely because the company is named on NHS Supply "
        "Chain's Wound Closure framework. No product-level evidence -- none exists "
        "for this entity independent of its parent group."
    ),
}

doc = json.load(open(PATH))
names = {s.get("name") for s in doc["suppliers"]}
if RECORD["name"] in names:
    raise SystemExit("already present, aborting: %r" % RECORD["name"])

doc["suppliers"].append(RECORD)
with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print("added", RECORD["name"], "- total suppliers:", len(doc["suppliers"]))
