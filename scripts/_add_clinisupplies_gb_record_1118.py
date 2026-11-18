#!/usr/bin/env python3
"""Give CLINISUPPLIES GB LIMITED (02503030) its own Hub record.

Why this exists
---------------
NHS Supply Chain's Urology and Bowel Management brief names TWO rows,
"Clinisupplies Ltd" and "Clinisupplies GB Limited". They are two
registrations at Companies House, 04013240 and 02503030, and the existing
"Clinisupplies" record is 04013240. Until now 02503030 had no record, so
company_match.key() -- which strips "GB" -- routed its brief row to
04013240's record as well. The residual was written down on that record's
identityNote on 18/11/2026; this script is the thing that note named as
what would settle it.

The lot link is a previous-name link, not a name coincidence
------------------------------------------------------------
Find a Tender award notice 032330-2023 (NHS Supply Chain, Urology and Bowel
Management, published 1 November 2023) names "Great Bear Healthcare Ltd" as
an awarded supplier, and names "Clinisupplies Limited" SEPARATELY on the same
notice -- two parties, GB-FTS-96957 and GB-FTS-96951. Companies House, read
2026-11-18, states that registration 02503030 was named GREAT BEAR HEALTHCARE
LIMITED from 21 March 2007 to 19 July 2024, and is now CLINISUPPLIES GB
LIMITED. No company currently holds the Great Bear Healthcare name. So the
2023 awardee is this registration under its then-name.

That is a previous-name record ON one registration, not two companies sharing
a word, which is why the aliases below carry the Great Bear spellings. The
notice itself publishes no Companies House number for any party (only an
FTS-internal id), so the NUMBER stays a candidate per the repo's standing
rule: a name-search number may not be written to companyNumber.

Lots
----
Read at source 2026-11-18 from the OCDS release for ocds-h6vhtk-03c1e4.
Award relatedLots for Great Bear Healthcare Ltd: 1, 2, 3, 5, 13. Recorded by
~/.claude/hooks/framework_award_check.py as
~/.claude/framework-claims/032330-2023-2026-11-18.json.

Idempotent: re-running changes nothing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seed_format  # noqa: E402

ROOT = os.path.dirname(HERE)
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")

NAME = "Clinisupplies GB Limited"
EXISTING = "Clinisupplies"

ALIASES = [
    "Clinisupplies GB Limited",
    "Clinisupplies GB Ltd",
    "Great Bear Healthcare Limited",
    "Great Bear Healthcare Ltd",
]

IDENTITY_NOTE = (
    "Companies House, read 2026-11-18: CLINISUPPLIES GB LIMITED 02503030, "
    "active, private limited company, incorporated 17 May 1990, registered "
    "office 1 Blackmoor Lane, Croxley Park, Watford WD18 8GA, SIC 86900 "
    "other human health activities. Previous names on this registration: "
    "GREAT BEAR HEALTHCARE LIMITED from 21 March 2007 to 19 July 2024, and "
    "before that SIGMA HEALTHCARE LIMITED, WILLIAM JONES PACKAGING LIMITED "
    "and JONES PACKAGING LIMITED. "
    "This is NOT the Hub's \"Clinisupplies\" record, which is CLINISUPPLIES "
    "LIMITED 04013240. Two registrations at one Watford address are two "
    "companies; under data/identity-vocabulary-policy.json a shared name or "
    "address is not evidence, a shared registration number is. Neither "
    "record may take the other's spellings as aliases. "
    "The Great Bear Healthcare spellings ARE aliases here because they are a "
    "previous-name record on this same registration, not a shared word: "
    "Find a Tender award notice 032330-2023 names \"Great Bear Healthcare "
    "Ltd\" and \"Clinisupplies Limited\" as two separate parties "
    "(GB-FTS-96957 and GB-FTS-96951), and Companies House places the former "
    "name on 02503030. "
    "The notice publishes no Companies House number for any party, so "
    "02503030 is held as companyNumberCandidate and must be proved by "
    "scripts/confirm_company_numbers.py before it may be written to "
    "companyNumber or feed any derived claim."
)

FRAMEWORK = {
    "name": "Urology and Bowel Management",
    "dates": "21 February 2024 to 20 February 2028",
    "note": (
        "Named on NHS Supply Chain's own contract launch brief for this "
        "framework, as \"Clinisupplies GB Limited\". 57 suppliers on the "
        "framework. Lots 1, 2, 3, 5 and 13 per Find a Tender contract award "
        "notice 032330-2023, which names this registration under its "
        "then-name \"Great Bear Healthcare Ltd\" (Companies House 02503030 "
        "was GREAT BEAR HEALTHCARE LIMITED until 19 July 2024); the contract "
        "launch brief itself publishes no per-supplier lot breakdown. Lot "
        "source read 2026-11-18."
    ),
    "reference": "2023/S 000-011173",
    "category": "Rehabilitation and Community",
    "supplierCount": 57,
    "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/urology-and-bowel-management/",
    "source": "nhssc-brief",
    "capturedOn": "2026-11-18",
    "lotSourceUrl": "https://www.find-tender.service.gov.uk/Notice/032330-2023",
}

CANDIDATE = {
    "number": "02503030",
    "registeredName": "CLINISUPPLIES GB LIMITED",
    "companyStatus": "active",
    "incorporated": "1990-05-17",
    "confidence": "candidate",
    "matchedOn": (
        "Companies House name search on 2026-11-18 — NOT verified against "
        "a number published by the company. Find a Tender notice 032330-2023 "
        "publishes no registration number for any party. Must be proved by "
        "confirm_company_numbers.py before it may be written to "
        "companyNumber or feed any derived claim."
    ),
}

# The paragraph the existing record's identityNote ends with, and what it
# becomes now that the residual is settled.
OLD_TAIL = (
    "RESIDUAL, recorded so it is not re-found as new: 02503030 has no Hub "
    "record, and company_match.key() still strips the \"GB\", so anything "
    "that resolves a brief row to a company routes that row here too — "
    "which is why this record's framework card can still list that spelling "
    "among the names it was matched on. Narrowing that is a change to "
    "company_match.resolve() and would move award routing repo-wide, so it "
    "is a separate question, not a loose end of this one. What would settle "
    "it: a Hub record for 02503030."
)
NEW_TAIL = (
    "RESIDUAL SETTLED 2026-11-18: 02503030 now has its own Hub record, "
    "\"Clinisupplies GB Limited\". company_match.key() still strips the "
    "\"GB\", so the two records share the stripped key and a bare "
    "\"Clinisupplies\" spelling now resolves as AMBIGUOUS rather than to "
    "either record — which is the correct outcome, a question for a human "
    "rather than a guess. Each record keeps its own spellings because "
    "company_match.resolve() tries the verbatim tier first, and "
    "app/company-report.js was given the same verbatim tier on the same day "
    "so neither card shows the other's lots."
)


def record():
    return {
        "name": NAME,
        "aliases": list(ALIASES),
        "specialities": ["Continence & urology"],
        "frameworks": [dict(FRAMEWORK)],
        "companyNumberCandidate": dict(CANDIDATE),
        "identityNote": IDENTITY_NOTE,
    }


def patch(path):
    doc = json.load(open(path, encoding="utf-8"))
    rows = doc["suppliers"]
    changed = []

    if not any(s.get("name") == NAME for s in rows):
        # Insert immediately after the 04013240 record rather than appending
        # and re-sorting: neither data file is in any single sort order (it is
        # not sorted by name, nor by name.lower()), so a global sort would
        # reorder every row and bury this one-line change in a 1,000-line
        # diff -- and a push to main is a live publish whose diff is the only
        # review. This position is also where the file's own local alphabetical
        # run puts it: Clinisupplies, Clinisupplies GB Limited, Clinisys.
        at = next(
            (i for i, s in enumerate(rows) if s.get("name") == EXISTING), None
        )
        if at is None:
            raise SystemExit(
                "%s: no %r record to insert after; refusing to guess a "
                "position." % (path, EXISTING)
            )
        rows.insert(at + 1, record())
        changed.append("added %s after %s" % (NAME, EXISTING))

    for s in rows:
        if s.get("name") != EXISTING:
            continue
        note = s.get("identityNote") or ""
        if OLD_TAIL in note:
            s["identityNote"] = note.replace(OLD_TAIL, NEW_TAIL)
            changed.append("updated residual on %s" % EXISTING)
        elif NEW_TAIL not in note:
            raise SystemExit(
                "%s: the residual paragraph on %r is not the one this script "
                "was written against; refusing to guess." % (path, EXISTING)
            )

    if not changed:
        print("%s: already as intended" % os.path.basename(path))
        return
    fmt, round_trips = seed_format.write_like(path, doc)
    seed_format.describe(os.path.basename(path), fmt, round_trips)
    for c in changed:
        print("  %s" % c)


for p in (SEED, INDEX):
    patch(p)
