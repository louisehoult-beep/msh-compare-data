#!/usr/bin/env python3
"""Clear the two company-report gate failures from the 05/10/2026 company-intelligence run.

1. Six seed records hold a companyNumberCandidate that still says "NOT verified",
   though each also carries a companyNumberProof (the number published on the
   company's own site) and the Company Report now resolves it as confirmed.
   The candidate is rewritten to cite that proof and marked confirmed, the same
   shape as Acurable Limited's.

2. Babease Limited was matched by name search to BABEASE LIMITED (07473497),
   dissolved 01/11/2023, while its seed record holds a framework from 29/02/2024.
   The record's own companyNumberNote (30/09/2026) already rejects that number.
   It is added to data/company-match-overrides.json as `exclude`, so the nightly
   rebuild cannot re-make the match.

Run once: python3 scripts/_fix_company_report_gate_1005.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

SEED = "data/supplier-seed.json"
OVERRIDES = "data/company-match-overrides.json"
TODAY = "2026-10-05"

CONFIRM = ["NSK United Kingdom Limited", "Ovidius Medical Ltd", "Ovidius Solutions Ltd",
           "Promed Limited", "Starkstrom Limited", "Steris IMS Ltd"]

seed = json.load(open(SEED))
by_name = {s.get("name"): s for s in seed["suppliers"]}
for name in CONFIRM:
    s = by_name[name]
    cand, proof = s["companyNumberCandidate"], s["companyNumberProof"]
    if str(cand["number"]) != str(proof["number"]):
        raise SystemExit("ABORT: %s candidate %s != proof %s" % (name, cand["number"], proof["number"]))
    cand["confidence"] = "confirmed"
    cand["matchedOn"] = (
        "CONFIRMED on %s: company number published on the company's own website, agreeing "
        "with the Companies House record — %s, read %s. data/company-financials.json "
        "carries this company as matchConfidence \"confirmed\". Superseded wording: the "
        "candidate was first found by Companies House name search and recorded as not verified."
        % (TODAY, proof["url"], proof["checkedOn"]))
write_like(SEED, seed)

ov = json.load(open(OVERRIDES))
if "Babease Limited" in ov["overrides"]:
    raise SystemExit("ABORT: Babease Limited already has an override")
ov["overrides"]["Babease Limited"] = {
    "exclude": ["07473497"],
    "excludedName": "BABEASE LIMITED",
    "reason": ("BABEASE LIMITED (07473497) was dissolved on 01/11/2023; the supplier holds the "
               "Infant Feeding and Accessories framework from 29/02/2024, so it cannot be the "
               "holder. The seed record's companyNumberNote (30/09/2026) already rejects it."),
    "evidence": "https://find-and-update.company-information.service.gov.uk/company/07473497",
    "decidedOn": TODAY,
}
write_like(OVERRIDES, ov)
print("confirmed %d candidates; excluded 07473497 for Babease Limited" % len(CONFIRM))
