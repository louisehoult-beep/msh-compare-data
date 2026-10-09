#!/usr/bin/env python3
"""One-off exhaustion record, framework-coverage batch 08/10/2026.

Run once: python3 scripts/_add_physio_ot_exhausted_1008.py
"""
import json

PATH = "docs/framework-coverage-exhausted.json"

ENTRY = {
    "framework": "Physiotherapy and Occupational Therapy",
    "checkedOn": "2026-10-08",
    "coverageAtCheck": "31.8% (7/22)",
    "suppliersChecked": [
        "Crest Medical Ltd",
        "DJO UK Ltd (Enovis)",
        "Essity UK Limited",
        "Medline Industries",
        "Orca Medical Ltd",
        "Reliance Medical",
        "Phoenix Medical Ltd",
    ],
    "reason": (
        "All 7 remaining actionable items checked (6 publishedElsewhereNeedingCategory, "
        "1 needDomain). Checked each of the 6 publishedElsewhere suppliers' actual captured "
        "categories against this framework's catsInScope (rehab:bath, rehab:chair, "
        "rehab:therapy, rehab:walk): Orca Medical Ltd publishes ultrasound:port/trans "
        "(diagnostic ultrasound, not rehab); Crest Medical Ltd and Essity UK Limited "
        "(formerly BSN Medical Ltd) publish wound:deb/adv (wound debridement/advanced wound "
        "care); DJO UK Ltd (Enovis) publishes orthotics:brace/afo (bracing, a different "
        "speciality to rehab); Essity UK Limited publishes wound:fa/continence:pads/"
        "ortho:trauma/wound:adv/wound:comp/orthotics:afo/brace/upper (none rehab-shaped); "
        "Medline Industries publishes respiratory:aero; Reliance Medical publishes wound:fa "
        "(first-aid dressings). None of the 6 carries a genuine bathing/seating/therapy-"
        "equipment/walking-aid product under any division, so there is nothing to map -- "
        "this is the same 'lowest coverage is often the most finished' shape the brief "
        "itself describes, not neglect. Four of the six (DJO, Essity UK Limited, Medline, "
        "Reliance) also carry recorded crawl refusals for their own sites (robots.txt or no "
        "product API, all inside the refusal TTL), so re-crawling them is forbidden by the "
        "brief's own rule regardless. Phoenix Medical Ltd (needDomain) remains unconfirmed "
        "and uncrawlable: phoenixmedical.com still returns an empty/bot-challenged response "
        "(re-checked 08/10/2026, unchanged from the 05/09/2026 finding already in "
        "supplier-seed.json), and its recorded company number (08921091, evidence tier "
        "'name-exact, not confirmed') cannot be corroborated from the site. This run also "
        "found a second, equally plausible candidate at the same registered address (5 "
        "Lonebarn Link, Chelmsford CM2 5AR) -- PHOENIX MEDICAL GROUP LTD, 08370979 -- which "
        "third-party listings associate with the phoenixmedical.com trading site itself; "
        "this is a genuine identity ambiguity under rule 10/11, not something to resolve by "
        "guessing, so it is left unconfirmed and flagged to Lou (OUTSTANDING, added "
        "08/10/2026) rather than decided here. No permitted route left on any of the 7."
    ),
    "wouldReopenIf": (
        "Any of the 6 publishedElsewhere suppliers gets a new/changed crawl result revealing "
        "a genuine bathing/seating/therapy-equipment/walking-aid product; Phoenix Medical "
        "Ltd's site becomes readable, or Lou's ruling on the Phoenix Medical Ltd / Phoenix "
        "Medical Group Ltd identity question gives a confirmable domain or company number; "
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
