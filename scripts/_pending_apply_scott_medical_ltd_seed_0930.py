#!/usr/bin/env python3
"""
PENDING APPLY — left over from a differentiator-framework-coverage run on
30/09/2026 that could not land data/supplier-seed.json directly: the file
saw sustained concurrent-writer contention that night (repeated rebase
conflicts across roughly 10 successive land.sh attempts, each re-synced to
a fresh origin/main and re-verified green), so the change is banked here
instead of being retried indefinitely.

WHAT THIS DOES: adds ONE new supplier record to data/supplier-seed.json —
"Scott Medical Ltd" — under the unconfirmable-awardee identity policy
(data/identity-vocabulary-policy.json). The company is named on NHS Supply
Chain's own contract launch brief for "Anaesthesia Machines, Ventilators,
Neonatal Equipment and Phototherapy Systems, Related Accessories and
Services" (2026/S 000-008108) as "Scott Medical Ltd", but the identity
cannot be confirmed: Companies House and web search turn up three distinct
"Scott Medical" entities (Scott Medical Limited NI065193, Lisburn —
physiotherapy/rehab/GP supplies, no anaesthesia/ventilator/neonatal range;
Scott Medical Supplies Ltd SC875037, Scotland, incorporated Jan 2026, too
recent to be this 2 March 2026 award's established supplier; Scot Medical
Ltd SC533540, dissolved 2017) and none is a confident product-category or
timing match. Per policy, the award is published under the name as given,
with no company number, explicitly marked identityUnconfirmed — same
pattern already used for "Ingles Ltd" elsewhere in this file.

NEXT RUN: run this script from a fresh ./begin.sh clone. It is idempotent —
it checks whether "Scott Medical Ltd" is already in data/supplier-seed.json
(a peer may have landed an equivalent record independently) and, if so,
does nothing and exits 0. Otherwise it appends the record, in the same
compact single-line-JSON format the file already uses.

After running this script:
  1. python3 scripts/crawl_supplier_site.py --supplier "Charter Kontron Limited" --domain charter-kontron.com
     python3 scripts/crawl_supplier_site.py --supplier "Mieka Ltd" --domain mieka.co.uk
     python3 scripts/crawl_supplier_site.py --supplier "mOm Incubators Ltd" --domain momincubators.com
     python3 scripts/crawl_supplier_site.py --supplier "Loewenstein Medical UK Ltd" --domain loewensteinmedical.com
     python3 scripts/crawl_supplier_site.py --supplier "@SimulationMan Ltd" --domain simulationcollective.com
     (all five are genuine confirmed domains for the framework's other needDomain
     suppliers that were already investigated this run; all five refused on the
     standard crawl routes — no WP/WooCommerce API, or robots.txt disallow — so
     recording the refusal just prevents a future run wasting time re-trying them.
     Atom Medical Corporation UK ltd (company number 12413115) could NOT be
     confirmed to a distinct UK domain this run — its global site atomed-global.com
     names no UK-specific page — leave it needDomain, do not guess.)
  2. python3 scripts/build_differentiator.py
  3. python3 scripts/stamp_notice.py
  4. python3 company-aliases/company_alias.py build
  5. python3 scripts/refresh_awards.py --rematch
     (this will resolve a quarantined Companies-award-history row — "UVB Machine",
     a Contracts Finder notice for Queen Elizabeth Hospital King's Lynn, supplier
     name "Scott Medical Limited" — onto this new Scott Medical Ltd record. That
     is a correct match-by-name under the unconfirmable-awardee policy, not a new
     identity claim, and land.sh's record-level no-loss check will need --allow
     "UVB Machine" the first time it is staged alongside data/company-awards.json.)
  6. python3 scripts/build_coverage_ledger.py
  7. python3 verify.py — must exit 0.
  8. ./land.sh "supplier-seed: add Scott Medical Ltd, unconfirmed-identity
     awardee on the Anaesthesia Machines/Ventilators/Neonatal Equipment
     framework (2026/S 000-008108)" --allow "UVB Machine" <the files you
     actually touched>
  9. Delete this script (it is a scratch scaffold, not part of the pipeline) as
     part of that same land.sh call.

This record does NOT move framework coverage on its own (Scott Medical Ltd
carries no products, so it does not count toward "suppliersPublished") — it
only turns the framework's "1 unresolved name" into a correctly-recorded
"1 unconfirmed identity", which is real, honest progress but not a coverage
percentage change. The coverage jump from this same run (32.0%->36.0%,
8/25->9/25, via a Penlon Anaesthesia division mapping) already landed
separately as commit 7e20d77.
"""
import json

PATH = "data/supplier-seed.json"


def main():
    with open(PATH) as f:
        d = json.load(f)

    names = [s["name"] for s in d["suppliers"]]
    if "Scott Medical Ltd" in names:
        print("Scott Medical Ltd already present in data/supplier-seed.json — nothing to do.")
        return

    new_supplier = {
        "name": "Scott Medical Ltd",
        "aliases": ["Scott Medical Ltd"],
        "specialities": ["Anaesthesia", "Neonatal"],
        "products": [],
        "frameworks": [
            {
                "name": "Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy Systems, Related Accessories and Services",
                "dates": "2 March 2026 to 28 February 2029",
                "note": "Named on NHS Supply Chain's own contract launch brief for this framework, as \"Scott Medical Ltd\". 25 suppliers on the framework.",
                "reference": "2026/S 000-008108",
                "category": "Diagnostic Equipment and Services",
                "supplierCount": 25,
                "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/anaesthesia-machines-ventilator-equipment-and-related-accessories/",
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
            "Added 30/09/2026 from NHS Supply Chain's own contract launch brief "
            "for this framework (2026/S 000-008108). The framework award is the "
            "only verified fact in this record. Identity could not be confirmed: "
            "web/Companies House search turns up several distinct \"Scott Medical\" "
            "companies (Scott Medical Limited NI065193, Lisburn -- physiotherapy/"
            "rehab/GP supplies, no anaesthesia/ventilator/neonatal range; Scott "
            "Medical Supplies Ltd SC875037, Scotland, incorporated Jan 2026, too "
            "recent to be the 2 March 2026 awardee's established supplier; Scot "
            "Medical Ltd SC533540, dissolved 2017) and none is a confident "
            "product-category or timing match. Product range, UK entity, "
            "ownership and website have NOT been verified and must be checked "
            "at source before being used with a customer."
        ),
        "verified": "2026-09-30",
        "source": "NHS Supply Chain contract launch brief (2026/S 000-008108), fetched 30/09/2026",
        "reconciledFrom": "differentiator-framework-coverage run, 30/09/2026, unconfirmable-awardee policy",
        "_specialitiesEvidence": (
            "Speciality assigned solely because the company is named on NHS "
            "Supply Chain's Anaesthesia Machines, Ventilators, Neonatal "
            "Equipment and Phototherapy Systems framework. No product-level "
            "evidence yet."
        ),
        "companyNumberNote": (
            "No confident Companies House match: multiple distinct \"Scott "
            "Medical\" entities exist and none is a confirmed product-category "
            "or timing fit for this NHSSC award (see note)."
        ),
        "productCategories": [],
        "identityUnconfirmed": True,
    }

    d["suppliers"].append(new_supplier)
    with open(PATH, "w") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Added Scott Medical Ltd. New supplier count: {len(d['suppliers'])}")


if __name__ == "__main__":
    main()
