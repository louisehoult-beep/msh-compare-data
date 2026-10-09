#!/usr/bin/env python3
"""One-off: record the Insulin Pumps/CGM/HCL framework as exhausted, now that
the parent-subsidiary-award-credit policy (ruled 20/09/2026) has answered the
identity question that previously deferred it (see
scripts/_resolve_insulin_pumps_parent_subsidiary_0929.py for the full
reasoning). Moves it from data/coverage-deferrals.json (awaiting a ruling)
to docs/framework-coverage-exhausted.json (structurally blocked, ruling
applied, no route left) -- the deferral is removed by a separate edit.

Framework-coverage batch, 29/09/2026.
"""
import json

PATH = "docs/framework-coverage-exhausted.json"

ENTRY = {
    "framework": "Insulin Pumps, Continuous Glucose Monitoring, Products Contributing to the Delivery of Hybrid Closed Loop Pathways and Associated Products",
    "checkedOn": "2026-09-29",
    "coverageAtCheck": "16.7% (2/12)",
    "suppliersChecked": [
        "Abbott Laboratories Limited",
        "Medtronic",
        "Urathon Europe Ltd",
    ],
    "reason": (
        "Moved here from data/coverage-deferrals.json: the \"routing or identity ruling from Lou\" "
        "this entry was waiting on is answered by the parent-subsidiary-award-credit policy Lou "
        "ruled 20/09/2026 (data/identity-vocabulary-policy.json). Clause (a): the award credits to "
        "the entity NHSSC's own contract launch brief names, exactly as named -- supplier-seed.json "
        "already carries this framework under Abbott Laboratories Limited, Medtronic and Urathon "
        "Europe Ltd (source: nhssc-brief, capturedOn 2026-09-22), which is already correct and is "
        "not moved to Abbott Diabetes Care or MiniMed Group, Inc. under this policy. Clause (b): "
        "specialities/financials attach to the entity they actually describe, not the award -- "
        "Medtronic's stale \"Diabetes / CGM\"/\"Diabetes\" speciality tags (left over from before the "
        "March 2026 MiniMed spin-off) are removed as a data-hygiene fix, which does not move the "
        "award. None of the three's own real, crawled catalogue carries a genuine CGM/insulin-pump "
        "product: Abbott Laboratories Limited is nutrition-only (CH 00329102, confirmed); Medtronic's "
        "diabetes product line spun off to MiniMed Group, Inc. in March 2026 and its current "
        "catalogue has nothing diabetes-shaped; Urathon Europe Ltd's Yuwell Anytime CGM award is "
        "real but was crawled fresh 15/09/2026 (104 products across 5 divisions) with no CGM item "
        "surfacing on the crawlable catalogue. No permitted route left on any of the 3 -- this "
        "restates the crawl-confirmed findings already on record "
        "(docs/framework-coverage-findings-2026-09-18.md), the policy only settles the identity "
        "question that was blocking it from being recorded as exhausted."
    ),
    "wouldReopenIf": (
        "A new supplier is awarded on this framework; Abbott Laboratories Limited, Medtronic or "
        "Urathon Europe Ltd gets a new/changed crawl result revealing a genuine CGM/insulin-pump "
        "product; or NHSSC's own contract launch brief is revised to name a different awardee for "
        "any of the 3 (which would change which record the award credits to under clause (a), not "
        "reopen the identity question itself)."
    ),
}


def main():
    d = json.load(open(PATH))
    names = [f["framework"] for f in d["frameworks"]]
    assert ENTRY["framework"] not in names, "already exhausted"
    d["frameworks"].append(ENTRY)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("Added exhausted entry for Insulin Pumps framework")


if __name__ == "__main__":
    main()
