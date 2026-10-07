#!/usr/bin/env python3
"""One-off exhaustion record, framework-coverage batch 07/10/2026.

Run once: python3 scripts/_add_surgical_gloves_exhausted_1007.py
"""
import json

PATH = "docs/framework-coverage-exhausted.json"

ENTRY = {
    "framework": "Surgical Gloves",
    "checkedOn": "2026-10-07",
    "coverageAtCheck": "33.3% (3/9)",
    "suppliersChecked": [
        "Semperit Investment",
        "Medline Industries",
        "Globus (Shetland) Ltd",
        "Leanvation",
    ],
    "reason": (
        "All 4 remaining actionable items checked, 1 resolved this run. "
        "\"Semperit Investment\" was an unresolved name on NHS Supply Chain's own "
        "contract launch brief (fetched 07/10/2026): no Companies House company "
        "is registered under that exact name, and the closest candidates "
        "(SEMPERIT INVESTMENTS ASIA PTE LTD 15776017 and SEMPERIT (U.K.) LIMITED "
        "00425090) are both dissolved. Semperit AG fully exited the medical glove "
        "business (Sempermed sold to HARPS Global Pte Ltd, closed July 2024) and "
        "there is no current UK-registered Sempermed/Semperit entity, as the "
        "existing 'Semperit / Sempermed' record already documented. Resolved "
        "under the unconfirmable-awardee policy (data/identity-vocabulary-policy.json): "
        "added as a new seed record, award published under the name exactly as "
        "given, marked identityUnconfirmed, no company number/domain/financials. "
        "This necessarily lands in needDomain, not published -- the policy forbids "
        "attaching a domain to an unconfirmed identity, so this item cannot ever "
        "close by this route. Medline Industries (publishedElsewhereNeedingCategory) "
        "carries a recorded crawl refusal (robots.txt disallows, checked "
        "2026-09-08, inside the 90-day TTL) -- re-confirmed via a --dry-run this "
        "run, not re-crawled. Globus (Shetland) Ltd (heldOnly, 881 held products "
        "on globusgroup.com) is the same FAILED capture already diagnosed on the "
        "Examination Gloves framework (nav-labels-are-not-products policy): the "
        "crawl returned the site's own navigation/section headings, not real "
        "products, for both frameworks alike, since it is the same capture. "
        "Leanvation (needDomain) remains genuinely unresolved: Companies House "
        "candidate LEANVATION LTD (07316310, active) is now ruled OUT on a "
        "trade-mismatch (its SIC codes are motor vehicle parts, not medical), "
        "narrowing it to LEANVATION WORLDWIDE LIMITED (08520866, in Liquidation, "
        "SIC 32500 medical/dental instruments and supplies) as the better-fitting "
        "candidate -- consistent with third-party coverage that already named "
        "'Leanvation Worldwide Ltd' as the NHS-facing entity -- but this is "
        "trade-code corroboration, not a rule-11 recorded source (the company's "
        "own site remains unreadable in full; repeated fetch truncation, "
        "confirmed again this run), so no company number is attached and it "
        "stays unresolved. No permitted route left on any of the 4."
    ),
    "wouldReopenIf": (
        "Medline Industries' recorded refusal expires (90-day TTL from "
        "2026-09-08) and a re-crawl finds a genuine surgical-glove product; "
        "Globus (Shetland) Ltd's globusgroup.com capture is re-run against a "
        "real product path instead of its navigation labels; Leanvation's own "
        "site becomes readable in full, or a procurement listing or the "
        "company's own material names its legal entity directly, allowing "
        "confirm_company_numbers.py to prove 08520866 (or another candidate); "
        "or a new supplier is awarded on this framework."
    ),
}

doc = json.load(open(PATH))
names = {f.get("framework") for f in doc["frameworks"]}
if ENTRY["framework"] in names:
    raise SystemExit("already present, aborting: %r" % ENTRY["framework"])

doc["frameworks"].append(ENTRY)
with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("added exhausted entry for", ENTRY["framework"])
