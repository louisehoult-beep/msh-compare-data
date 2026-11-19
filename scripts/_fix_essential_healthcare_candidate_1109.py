#!/usr/bin/env python3
"""Clear the company-report gate failure from the 08/11/2026 Company intelligence run.

Essential Healthcare Solutions (UK) Ltd's seed record holds a companyNumberCandidate
that still says "NOT verified", though it also carries a companyNumberProof (the
company's own website states "Registered Company 04991941", agreeing with the
Companies House record for ESSENTIAL HEALTHCARE SOLUTIONS (UK) LIMITED, active,
checked 2026-11-05). The candidate is rewritten to cite that proof and marked
confirmed, the same pattern as scripts/_fix_company_report_gate_1005.py.

Run once: python3 scripts/_fix_essential_healthcare_candidate_1109.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

SEED = "data/supplier-seed.json"
TODAY = "2026-11-09"

seed = json.load(open(SEED))
by_name = {s.get("name"): s for s in seed["suppliers"]}
name = "Essential Healthcare Solutions (UK) Ltd"
s = by_name[name]
cand, proof = s["companyNumberCandidate"], s["companyNumberProof"]
if str(cand["number"]) != str(proof["number"]):
    raise SystemExit("ABORT: %s candidate %s != proof %s" % (name, cand["number"], proof["number"]))
cand["confidence"] = "confirmed"
cand["matchedOn"] = (
    "CONFIRMED on %s: company number published on the company's own website, agreeing "
    "with the Companies House record — %s, read %s. The next refresh_companies_house.py "
    "run resolves this company as matchConfidence \"confirmed\". Superseded wording: the "
    "candidate was first found by Companies House name search and recorded as not verified."
    % (TODAY, proof["url"], proof["checkedOn"]))
write_like(SEED, seed)
print("confirmed 1 candidate: %s" % name)
