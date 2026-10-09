#!/usr/bin/env python3
"""HARTMANN headline product order restored (09/10/2026).

WHY: Interview Prep (scripts/build_interview_prep.py) shows a company's FIRST
MAX_PRODUCTS (8) seed products, so the seed's product order is the curated
headline order. _hartmann_nonwound_products_0930.py split the Sterillium line
and inserted four lines straight after it (Stellisept med, the dispenser/pump
line, SicSac, the Vala range). That pushed PermaFoam Classic, RespoSorb
Silicone and HydroClean Advance out of the top eight, and the next rebuild
(424dab4, 09/10/2026) published HARTMANN without them, failing
test_hub_tools_demo_fixes.InterviewPrepHartmannLabels.

WHAT: move those four added lines to the END of HARTMANN's product list, in
data/supplier-seed.json and in data/supplier-index.json (which copies the seed's
products verbatim). Nothing added or removed; only order. Idempotent.
The 0930 script now appends the same way, so a re-run cannot reintroduce this.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")
SUP = "Paul Hartmann (HARTMANN)"
MOVE = [
    "Stellisept med (antimicrobial body wash)",
    "HARTMANN hand hygiene dispensers and single-use pumps",
    "SicSac (disposable sick bag)",
    "Vala disposable care range (bibs, towels, washing mitts, sheets)",
]


def pname(p):
    return p if isinstance(p, str) else (p or {}).get("name")


def reorder(doc, label):
    recs = [s for s in doc["suppliers"] if s.get("name") == SUP]
    if len(recs) != 1:
        sys.exit("%s: expected exactly one %r record, found %d" % (label, SUP, len(recs)))
    prods = recs[0]["products"]
    moved = [p for p in prods if pname(p) in MOVE]
    if len(moved) != len(MOVE):
        sys.exit("%s: expected all %d lines to move, found %d" % (label, len(MOVE), len(moved)))
    new = [p for p in prods if pname(p) not in MOVE] + moved
    assert sorted(map(pname, new)) == sorted(map(pname, prods))
    changed = new != prods
    recs[0]["products"] = new
    print("%s: %s, %d products, top 8 now: %s" % (
        label, "reordered" if changed else "already in order", len(new), [pname(p) for p in new[:8]]))
    return changed


def main():
    seed = json.loads(open(SEED, "rb").read())
    if reorder(seed, "seed"):
        print("seed written (%s)" % (write_like(SEED, seed),))
    index = json.loads(open(INDEX, "rb").read())
    if reorder(index, "index"):
        with open(INDEX, "w", encoding="utf-8") as f:
            f.write(json.dumps(index, ensure_ascii=False, indent=1))  # build_supplier_index.py's own format


if __name__ == "__main__":
    main()
