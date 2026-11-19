#!/usr/bin/env python3
"""One-off, 22/10/2026: two Solus endoscopy software awards the 21/10 seed left out.

The 21/10 seed (_seed_endoscopy_ems_awards_1021.py) left out Whittington Health
(1128d509, 21/07/2026, CPV 72261000) and Northampton General Hospital (1a70d2aa,
28/02/2023, CPV 48180000) because the lane rule matches an NHS buyer by the word
"NHS" and these two buyers publish their own name without it. Both are NHS
trusts: each is on the JAG participating-services register (thejag.org.uk, read
22/10/2026) as "Whittington Health NHS Trust" and "Northampton General Hospital
NHS Trust". Each notice is re-read below from its own Contracts Finder OCDS
release and the CPV test still applies; only the buyer-name test is waived, for
these two named buyers and nothing else. digital_lane_rules.py is unchanged.

USAGE   python3 scripts/_seed_endoscopy_ems_awards_1022.py [--check]
Then:   python3 scripts/stamp_notice.py && python3 verify.py
"""
import json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import digital_lane_rules as R
import refresh_company_digital_awards as CDA
import _seed_endoscopy_ems_awards_1021 as S

IDS = ["1128d509-85ed-49f1-bd7b-d902d7a7e47e", "1a70d2aa-d2ff-4982-b7d7-5ed3b2f67ba3"]
WAIVED_BUYERS = {"Whittington Health", "Northampton General Hospital"}


def main():
    check = "--check" in sys.argv
    rows = []
    for i in IDS:
        pkg = S.fetch_json(S.CF % i)
        r = S.award_release(pkg)
        buyer = (r.get("buyer") or {}).get("name") or ""
        assert buyer in WAIVED_BUYERS, buyer
        assert R.digital_cpvs(S.cpvs_of(r.get("tender") or {})), "no digital CPV"
        real = R.nhs_buyer
        R.nhs_buyer = lambda n: True  # waived for the two named buyers only
        try:
            got, why = S.rows_for(pkg, S.CF_NOTICE % i)
        finally:
            R.nhs_buyer = real
        assert got, why
        rows += got
    seed, lane = CDA.load(CDA.SEED), CDA.load(CDA.LANE)
    prev = CDA.load(CDA.OUT, {}) or {}
    pool = dict(prev)
    pool["unmatched"] = list(prev.get("unmatched") or []) + rows
    doc = CDA.build(seed, lane, CDA.load(CDA.MEDICAL, {}), pool)
    for r in rows:
        placed = [c for c, rs in doc["companies"].items() if any(CDA.row_key(x) == CDA.row_key(r) for x in rs)]
        print(r["date"], r["buyer"], "|", r["title"], "|", r["noticeSupplierName"], r["valueAmount"], r["periodEnd"], "->", placed[:1] or "UNMATCHED")
    if check:
        return
    with open(CDA.OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1); f.write("\n")
    print("wrote", CDA.OUT)

if __name__ == "__main__":
    main()
