#!/usr/bin/env python3
"""One-off: record a proved domain for E&O Laboratories (framework-coverage batch,
run 06/11/2026, Laboratory Diagnostics, Point of Care Testing and Pathology Managed
Services). Address-tier proof: the site's own footer publishes the registered office
address, which matches Companies House for SC125360 (E & O LABORATORIES LIMITED)."""
import json, sys
sys.path.insert(0, "scripts")
import seed_format
SEED = "data/supplier-seed.json"
D = "2026-11-06"

PROOF = dict(
    domain="eolabs.com",
    url="https://www.eolabs.com",
    num="SC125360",
    route="address-match",
    evidence=('footer states "E&O Laboratories Ltd, Burnhouse, Bonnybridge, Scotland, FK4 2HH"; '
              'Companies House confirms E & O LABORATORIES LIMITED (SC125360), active, registered '
              'office Burnhouse, Bonnybridge, Stirlingshire, FK4 2HH -- same address'),
)

def main():
    seed = json.load(open(SEED))
    by = {s["name"]: s for s in seed["suppliers"]}
    r = by["E&O Laboratories"]
    r["domain"] = PROOF["domain"]
    r["links"].append({
        "label": "Company website",
        "url": PROOF["url"],
        "route": PROOF["route"],
        "source": f'Proved by registered-office address match on {D}: {PROOF["evidence"]}.',
    })
    r["companyNumberProof"] = {
        "number": PROOF["num"], "route": PROOF["route"], "url": PROOF["url"],
        "evidence": PROOF["evidence"], "checkedOn": D,
    }
    seed_format.write_like(SEED, seed)
    print("done")

main()
