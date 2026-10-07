#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 07/10/2026.

"Semperit Investment" is named on NHS Supply Chain's own contract launch
brief for "Surgical Gloves" (https://www.supplychain.nhs.uk/product-information/
contract-launch-brief/surgical-gloves/, fetched 07/10/2026), one of 9 awarded
suppliers (reference 2022/S 000-028900). It has no supplier-seed record under
that exact name.

Companies House search for "Semperit Investment" (fetched 07/10/2026) returns
no company registered under that exact name. The closest candidates are:
  - SEMPERIT INVESTMENTS ASIA PTE LTD (15776017) -- not an exact-name match
    ("Investments Asia", not "Investment") -- DISSOLVED 11 March 2025.
  - SEMPERIT (U.K.) LIMITED (00425090) -- DISSOLVED 18 February 2025.
This matches the Hub's own existing curated record "Semperit / Sempermed",
whose alert already documents that Semperit AG fully exited the medical
glove business (Sempermed sold to HARPS Global Pte Ltd, deal closed July
2024; sempermed.com now redirects to harpsglobal.com) and that there is no
current UK-registered Sempermed/Semperit entity. The framework remains live
to 25 April 2027 and NHS Supply Chain's own brief still names the supplier
as "Semperit Investment" -- not yet updated to reflect the exit.

No live or dissolved-but-live-at-award-time entity can be confirmed as the
named awardee. This is the "unconfirmable-awardee" shape in
data/identity-vocabulary-policy.json: publish the award under the name
exactly as given, marked unconfirmed, with no company number, financials,
domain or logo attached. Applying that standing policy directly rather than
escalating, per its own "no per-case escalation required" ruling.

Deliberately a NEW record rather than an alias onto "Semperit / Sempermed" or
"Semperit Investments Asia": neither existing record's name is an exact match
for "Semperit Investment", and rule 10 of docs/HUB-VERIFICATION-STANDARD.md
forbids linking names on similarity alone.

Run once: python3 scripts/_add_semperit_investment_surgical_gloves_1007.py
"""
import json

PATH = "data/supplier-seed.json"

RECORD = {
    "name": "Semperit Investment",
    "aliases": ["Semperit Investment"],
    "specialities": ["Theatre / surgical"],
    "products": [],
    "frameworks": [
        {
            "name": "Surgical Gloves",
            "dates": "27 November 2023 to 25 April 2027",
            "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                      "framework, as \"Semperit Investment\". 9 suppliers on the framework."),
            "reference": "2022/S 000-028900",
            "category": "Medical and Surgical Consumables",
            "supplierCount": 9,
            "url": ("https://www.supplychain.nhs.uk/product-information/"
                     "contract-launch-brief/surgical-gloves/"),
            "source": "nhssc-brief",
            "capturedOn": "2026-10-07",
        }
    ],
    "alerts": [],
    "news": [],
    "links": [],
    "awards": [],
    "curated": True,
    "note": (
        "Added 07/10/2026 by the framework-coverage routine, resolving an "
        "unresolved-name gap on the Surgical Gloves framework. Marked "
        "identityUnconfirmed under the unconfirmable-awardee policy "
        "(data/identity-vocabulary-policy.json): Companies House has no exact-name "
        "match for \"Semperit Investment\"; the closest candidates, SEMPERIT "
        "INVESTMENTS ASIA PTE LTD (15776017) and SEMPERIT (U.K.) LIMITED (00425090), "
        "are both dissolved (11/03/2025 and 18/02/2025) and neither is an exact-name "
        "match. Semperit AG sold its medical glove business (Sempermed) to HARPS "
        "Global Pte Ltd, deal closed July 2024 -- see the existing curated record "
        "'Semperit / Sempermed' for the full exit history. NHS Supply Chain's brief "
        "still names the supplier as \"Semperit Investment\"; not linked to either "
        "existing Semperit-related seed record on name similarity alone (rule 10). "
        "No company number, domain or financials attached."
    ),
    "verified": "2026-10-07",
    "source": ("NHS Supply Chain contract launch brief (2022/S 000-028900), fetched "
               "07/10/2026; Companies House search for \"Semperit Investment\", "
               "read 07/10/2026"),
    "_specialitiesEvidence": (
        "Speciality assigned solely because the company is named on NHS Supply "
        "Chain's Surgical Gloves framework. No product-level evidence yet."
    ),
    "companyNumberNote": (
        "No Companies House match could be established: no company is registered "
        "under the exact name \"Semperit Investment\"; the closest candidates "
        "(Semperit Investments Asia Pte Ltd, 15776017; Semperit (U.K.) Limited, "
        "00425090) are both dissolved and neither is an exact-name match, so "
        "neither is linked to the award (rule 10)."
    ),
    "identityUnconfirmed": True,
}

doc = json.load(open(PATH))
names = {s.get("name") for s in doc["suppliers"]}
if RECORD["name"] in names:
    raise SystemExit("already present, aborting: %r" % RECORD["name"])

doc["suppliers"].append(RECORD)
with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print("added", RECORD["name"], "- total suppliers:", len(doc["suppliers"]))
