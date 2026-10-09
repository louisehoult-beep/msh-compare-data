#!/usr/bin/env python3
"""One-off correction, framework-coverage batch 07/10/2026.

Leanvation (Surgical Gloves framework) carried a stale companyNumberCandidate
pointing at LEANVATION LTD (07316310), added 14/08/2026 from a plain
Companies House name search and already flagged there as unverified. Fetched
both Companies House candidate pages directly today (07/10/2026):

  - LEANVATION LTD (07316310): status active, but its own SIC codes are
    "Wholesale/retail distribution of motor vehicle parts and accessories"
    plus a generic "other professional/scientific/technical" code -- not a
    medical or surgical business at all. This rules it out on trade grounds,
    not name similarity.
  - LEANVATION WORLDWIDE LIMITED (08520866): status "Liquidation", SIC code
    32500 "Manufacture of medical and dental instruments and supplies" --
    matches the awarded trade. The seed's own existing note already recorded
    that third-party coverage (Clinical Services Journal supplier directory)
    names the NHS-facing entity as "Leanvation Worldwide Ltd", i.e. this
    company, not 07316310.

This is still not a rule-11 "recorded source" (no procurement listing or the
company's own material has been read naming the legal entity directly -- the
company's own site could not be read in full; repeated fetch truncation,
confirmed again today), so no companyNumber is attached and the record stays
identityUnconfirmed in effect. But the PREVIOUS candidate (07316310) is now
actively wrong on trade-mismatch evidence and should not sit as the only
candidate note a future run might lean on. Swapping the candidate pointer to
08520866, still marked unverified, and recording why 07316310 is excluded.

Run once: python3 scripts/_update_leanvation_candidate_1007.py
"""
import json

PATH = "data/supplier-seed.json"

doc = json.load(open(PATH))
hit = None
for s in doc["suppliers"]:
    if s.get("name") == "Leanvation":
        hit = s
        break
if hit is None:
    raise SystemExit("Leanvation record not found")

hit["note"] = (
    hit["note"]
    + " UPDATE 07/10/2026 (framework-coverage routine): fetched both Companies "
      "House candidate pages directly. LEANVATION LTD (07316310) is RULED OUT "
      "on trade-mismatch grounds, not name similarity -- its own SIC codes are "
      "motor vehicle parts wholesale/retail distribution, not medical. "
      "LEANVATION WORLDWIDE LIMITED (08520866, in Liquidation) carries SIC "
      "32500 \"Manufacture of medical and dental instruments and supplies\", "
      "matching the awarded trade, and is the entity third-party coverage "
      "already named as the NHS-facing one. Still not attached as companyNumber: "
      "no procurement listing or the company's own material (site unreadable, "
      "repeated fetch truncation) names the legal entity directly, so this is "
      "SIC-code corroboration, not a rule-11 recorded source. Candidate pointer "
      "updated below to reflect the better-fitting, still-unconfirmed company."
)
hit["companyNumberCandidate"] = {
    "number": "08520866",
    "registeredName": "LEANVATION WORLDWIDE LIMITED",
    "companyStatus": "liquidation",
    "sicCode": "32500 - Manufacture of medical and dental instruments and supplies",
    "confidence": "candidate",
    "matchedOn": (
        "Companies House direct fetch on 2026-10-07. Trade-code match (SIC 32500) "
        "and third-party (Clinical Services Journal) naming of this entity as the "
        "NHS-facing one supersede the previous candidate, LEANVATION LTD "
        "(07316310), which is ruled out by SIC mismatch (motor vehicle parts). "
        "NOT verified against a number published by the company itself or a "
        "procurement listing -- must be proved by confirm_company_numbers.py "
        "before it may be written to companyNumber or feed any derived claim."
    ),
}

with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print("updated Leanvation companyNumberCandidate -> 08520866 (still unconfirmed)")
