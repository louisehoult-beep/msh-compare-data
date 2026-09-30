#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 30/09/2026.

"Thesis Technology Products Ltd" and "Thesis (LimbO)" are two separate
supplier-seed records for the SAME real company: both list domain
limboproducts.co.uk, and "Thesis Technology Products Ltd"'s own seed record is
proved to that domain by registered-office address matching Companies House
02894920 (domain-proof-tier policy, data/identity-vocabulary-policy.json).
"Thesis (LimbO)" is an older, explicitly UNVERIFIED record carried over from
the Hub's retired supplier-directory page (06/08/2026). The Orthotics,
Podiatry and Immobilisation framework award (NHSSC contract launch brief,
captured 22/09/2026) is recorded against "Thesis Technology Products Ltd", the
verified record -- data/coverage-ledger.json flags it as
`duplicateOfCapturedSupplier`, pointing at "Thesis (LimbO)".

The two crawls (data/supplier-products.json) hold the IDENTICAL catalogue --
same domain, same division names, same product names and counts (46 LimbO
Waterproof Protectors, 8 Cast Accessories, 7 Diabetic Socks & Mobility Aids, 1
PICC Line/Midline Accessories) -- captured at different times under the two
different seed-record names. "Thesis (LimbO)"'s four divisions already carry
considered category decisions in differentiator-category-map.json, each with
its own `why`. This script applies those SAME decisions to the identical
divisions recorded under "Thesis Technology Products Ltd", rather than
guessing or inventing a new category: same domain, same products, same
reasoning.

This does not merge or alias the two seed records (no change to aliases /
award routing), and does not touch "Thesis (LimbO)"'s own entries.

Run once: python3 scripts/_seed_thesis_technology_duplicate_record_overrides_0930.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Thesis Technology Products Ltd"
SOURCE_SUPPLIER = "Thesis (LimbO)"

# (division, hub, why) copied verbatim from the existing "Thesis (LimbO)" entries.
DECISIONS = [
    ("LimbO Waterproof Protectors", "wound:protect",
     "elbow, PICC line and cast waterproof protectors"),
    ("Cast Accessories", "wound:protect",
     "outdoor weather protectors for arm, foot and leg casts"),
    ("Diabetic Socks & Mobility Aids", "orthotics:hosiery",
     "IOMI, Gentle Grip and Prosox are specialist therapeutic/compression sock ranges."),
    ("PICC Line/ Midline Accessories", "vascular:sec",
     "A PICC line sleeve secures/protects the vascular access dressing site."),
]

doc = json.load(open(MAP))
by_key = {(e["supplier"], e["division"]): e for e in doc["entries"]}

updated = 0
for division, hub, why in DECISIONS:
    key = (SUPPLIER, division)
    entry = by_key.get(key)
    if entry is None:
        print("MISSING worklist entry, skipping:", key)
        continue
    if entry.get("hub"):
        print("already mapped, skipping:", key, "->", entry["hub"])
        continue
    entry["hub"] = hub
    entry["why"] = why
    entry["decidedIn"] = (
        "_seed_thesis_technology_duplicate_record_overrides_0930.py -- copied from "
        "the identical, already-decided '%s' record (same domain, same catalogue)"
        % SOURCE_SUPPLIER
    )
    updated += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("updated %d entries for %r" % (updated, SUPPLIER))
