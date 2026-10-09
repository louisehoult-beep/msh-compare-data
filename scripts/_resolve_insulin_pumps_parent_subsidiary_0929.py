#!/usr/bin/env python3
"""One-off: resolve the Insulin Pumps/CGM/HCL framework's three-supplier
identity deferral (decision-queue #8, OUTSTANDING ^o527, coverage-deferrals
entry decisionRef ^o527) against the parent-subsidiary-award-credit policy
Lou ruled 20/09/2026 (data/identity-vocabulary-policy.json).

Policy clause (a): the AWARD credits to the entity the awarding source names,
exactly as named. NHSSC's own contract launch brief names "Abbott Laboratories
Ltd", "Medtronic Ltd" and "Urathon Europe Ltd" as the three remaining awardees
-- supplier-seed.json already carries the award under each of those exact
records (frameworks[], source: nhssc-brief), which is already correct per the
ruling and needs no change. Clause (b): financials/specialities attach to the
entity they actually describe. None of the three's own real, crawled catalogue
carries a genuine CGM/pump product (already confirmed by prior crawl work,
recorded in the coverage-deferrals.json entry and
docs/framework-coverage-findings-2026-09-18.md), so they stay correctly held
for this framework -- the policy answers "which entity gets the award noted",
not "invent a product that isn't there".

The one genuine stale-data fix the policy surfaces: Medtronic's specialities
array still lists "Diabetes / CGM" and a duplicate "Diabetes" tag, left over
from before the Diabetes business was spun off into MiniMed Group, Inc. (IPO
completed 9 March 2026, confirmed on MiniMed's own seed record 20/07/2026).
Per clause (a) the award itself stays with Medtronic Ltd (as NHSSC's brief
names it) -- this does not touch that -- but the speciality tags describing
what Medtronic itself currently sells are simply wrong and are removed.

Framework-coverage batch, 29/09/2026.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "Medtronic")
    before = list(rec["specialities"])
    rec["specialities"] = [s for s in rec["specialities"] if s not in ("Diabetes / CGM", "Diabetes")]
    removed = [s for s in before if s not in rec["specialities"]]
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Removed stale specialities from Medtronic: {removed}")


if __name__ == "__main__":
    main()
