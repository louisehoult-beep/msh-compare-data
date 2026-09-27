#!/usr/bin/env python3
"""One-off: resolve 2 unresolved-name entries on Electrosurgical Consumables
and Related Accessories (Electrosurgical Consumables coverage ledger).

1. "KCI Medical Limited (Solventum)" is an exact-name-from-source variant of
   the existing Solventum (3M Health Care) record -- same shape as the
   "KCI Medical Limited (3m)" variant already resolved 26/09/2026 on the
   Urology and Bowel Management framework. Confirmed present verbatim on
   NHS Supply Chain's own contract launch brief for this framework via
   WebFetch, 27/09/2026.
2. "Surgica Limited" cannot be resolved to a confirmable company by any
   route: the framework award notice and third-party tender trackers carry
   no company number; the company's own site (surgica.co.uk) is copyrighted
   to "Surgica Gmbh" and gives only a Vantage London serviced-office address
   (a shared company-formation address used by many companies, explicitly
   excluded as proof by the domain-proof-tier policy guard) with no
   registration number anywhere on it. This is the unconfirmable-awardee
   policy shape (data/identity-vocabulary-policy.json): publish the award
   under the name exactly as given, no company number/domain/financials,
   marked identityUnconfirmed. No escalation required (standing authority).

Framework-coverage batch, 27/09/2026, Electrosurgical Consumables and
Related Accessories.
"""
import json

SEED = "data/supplier-seed.json"

ELECTROSURGICAL_FRAMEWORK = {
    "dates": "20 October 2025 to 19 October 2028",
    "reference": "2024/S 000-001161",
    "category": "Medical and Surgical Consumables",
    "supplierCount": 33,
    "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/electrosurgical-consumables/",
    "source": "nhssc-brief",
    "capturedOn": "2026-09-27",
}


def main():
    seed = json.load(open(SEED))
    suppliers = seed["suppliers"]

    solventum = next(s for s in suppliers if s.get("name") == "Solventum (3M Health Care)")
    alias = "KCI Medical Limited (Solventum)"
    if alias not in solventum["aliases"]:
        solventum["aliases"].append(alias)
    if not any(fw.get("reference") == "2024/S 000-001161" for fw in solventum["frameworks"]):
        solventum["frameworks"].append({
            "name": "Electrosurgical Consumables and Related Accessories",
            "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                     "framework, as \"KCI Medical Limited (Solventum)\". 33 suppliers on "
                     "the framework."),
            **ELECTROSURGICAL_FRAMEWORK,
        })

    if not any(s.get("name") == "Surgica Limited" for s in suppliers):
        suppliers.append({
            "name": "Surgica Limited",
            "aliases": ["Surgica Limited"],
            "specialities": ["Theatre / surgical"],
            "products": [],
            "frameworks": [{
                "name": "Electrosurgical Consumables and Related Accessories",
                "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                         "framework, as \"Surgica Limited\". 33 suppliers on the framework."),
                **ELECTROSURGICAL_FRAMEWORK,
            }],
            "alerts": [],
            "news": [],
            "links": [],
            "awards": [],
            "curated": True,
            "note": ("Added 27/09/2026 from NHS Supply Chain's own contract launch brief "
                     "for this framework (2024/S 000-001161), where this company is named "
                     "as \"Surgica Limited\". The framework award is the only verified fact "
                     "in this record. Identity could not be confirmed by any permitted "
                     "route: no company number is given on the award notice or on third-"
                     "party tender trackers (bidstats.uk, justskim.ai); the company's own "
                     "site (surgica.co.uk, which does sell matching electrosurgical "
                     "pencils/plume-extraction/forceps products) is copyrighted to "
                     "\"Surgica Gmbh\" and gives only a Vantage London serviced-office "
                     "address with no registration number — a shared formation-agent "
                     "address, not proof under the domain-proof-tier policy guard. "
                     "Companies House name search is not evidence per rule 11 and was not "
                     "used to guess a number. Published per the unconfirmable-awardee "
                     "policy (data/identity-vocabulary-policy.json, ruled 20/09/2026): "
                     "award published under the name as given, no company number, "
                     "financials, domain or logo attached."),
            "verified": "2026-09-27",
            "source": ("NHS Supply Chain contract launch brief (2024/S 000-001161), "
                       "fetched 27/09/2026"),
            "_specialitiesEvidence": ("Speciality assigned solely from the framework's own "
                                       "product scope (electrosurgical consumables) and the "
                                       "company's own site's product categories "
                                       "(electrosurgical/smoke-evacuation pencils, forceps) "
                                       "-- read for shape/plausibility only, not as identity "
                                       "proof. No product-level evidence attached to this "
                                       "record."),
            "identityUnconfirmed": True,
        })

    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Solventum alias added; Surgica Limited record added.")


if __name__ == "__main__":
    main()
