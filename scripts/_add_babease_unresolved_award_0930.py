#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 30/09/2026.

Babease Limited is named on NHS Supply Chain's own contract launch brief for
"Infant Feeding and Accessories" (baby-food-and-feeding-accessories), one of
18 awarded suppliers. It has no supplier-seed record at all.

Companies House carries three companies matching "Babease" and NONE of them
is a clean match for the awarded name:
  - BABEASE LIMITED (07473497) -- the only company whose registered name is
    an exact match -- was DISSOLVED on 1 November 2023, before this
    framework's own award period (29 Feb 2024 - 28 Feb 2028) begins. It
    cannot be the awardee.
  - BABEASE FOODS LIMITED (12320133) -- the real trading baby-food company
    (babease.co, "Food for babies, not baby food") -- is the obvious
    candidate on trading identity, but its registered name is not "Babease
    Limited" and rule 10 of docs/HUB-VERIFICATION-STANDARD.md forbids
    linking two names on similarity alone ("'Ingles Ltd' is not linked to
    'Ingles Medical Limited' on similarity" is the standard's own example of
    this exact shape). It is ALSO currently in Liquidation, which is itself
    unverified against and unrelated to the award.
  - BABEASE WITH JESS LTD (15880100) -- unrelated, also dissolved.

No primary source (the awarding brief, a procurement listing, the company's
own site) states the registered legal entity behind the award name, so this
is the "unconfirmable-awardee" shape in
data/identity-vocabulary-policy.json: publish the award under the name
exactly as given, marked unconfirmed, with no company number, financials,
domain or logo attached. Applying that standing policy directly rather than
escalating, per its own "no per-case escalation required" ruling.

Run once: python3 scripts/_add_babease_unresolved_award_0930.py
"""
import json

PATH = "data/supplier-seed.json"

RECORD = {
    "name": "Babease Limited",
    "aliases": ["Babease Limited"],
    "specialities": ["Neonatal / infant feeding"],
    "products": [],
    "frameworks": [
        {
            "name": "Infant Feeding and Accessories",
            "dates": "29 February 2024 to 28 February 2028",
            "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                      "framework, as \"Babease Limited\". 18 suppliers on the framework."),
            "reference": "2023/S 000-011743",
            "category": "Rehabilitation and Community",
            "supplierCount": 18,
            "url": ("https://www.supplychain.nhs.uk/product-information/"
                     "contract-launch-brief/baby-food-and-feeding-accessories/"),
            "source": "nhssc-brief",
            "capturedOn": "2026-09-30",
        }
    ],
    "alerts": [],
    "news": [],
    "links": [],
    "awards": [],
    "curated": True,
    "note": (
        "Added 30/09/2026 by the framework-coverage routine, resolving an "
        "unresolved-name gap on the Infant Feeding and Accessories framework. "
        "Marked identityUnconfirmed under the unconfirmable-awardee policy "
        "(data/identity-vocabulary-policy.json): Companies House's only exact-name "
        "match, BABEASE LIMITED (07473497), was dissolved 1 November 2023, before "
        "this framework's award period starts, so it cannot be the awardee; the "
        "real trading baby-food company, BABEASE FOODS LIMITED (12320133, now in "
        "Liquidation), is a plausible but UNCONFIRMED candidate -- its registered "
        "name does not match the awarded string and rule 10 forbids linking the two "
        "on similarity alone. No company number, domain or financials attached."
    ),
    "verified": "2026-09-30",
    "source": ("NHS Supply Chain contract launch brief (2023/S 000-011743), fetched "
               "30/09/2026; Companies House search for \"Babease\", read 30/09/2026"),
    "_specialitiesEvidence": (
        "Speciality assigned solely because the company is named on NHS Supply "
        "Chain's Infant Feeding and Accessories framework. No product-level "
        "evidence yet."
    ),
    "companyNumberNote": (
        "No Companies House match could be established: the only exact-name match "
        "(07473497) is dissolved and pre-dates the award period; the trading "
        "company operating as Babease (BABEASE FOODS LIMITED, 12320133) has a "
        "different registered name and is not linked on similarity alone (rule 10)."
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
