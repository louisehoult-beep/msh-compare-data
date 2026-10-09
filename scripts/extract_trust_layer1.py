#!/usr/bin/env python3
"""Extract layer-1 reference data for a batch of trusts, for the research step.

Usage: python3 scripts/extract_trust_layer1.py [--dir DIR] <CODE1> [CODE2 ...]

Writes <dir>/<CODE>-layer1.json for each code, with:
  directory  - the trustDirectory entry (name, town, postcode, ICB, region)
  pressures  - the trust-pressures.json record (waiting list, 18-week %, median wait,
               CQC, oversight segment, Never Events, C. diff, ERIC backlog)
  periods    - which month/year each pressures figure is from

Run from the repo root (or a worktree of it).
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="tmp/trust-batch")
    ap.add_argument("codes", nargs="+")
    args = ap.parse_args()

    os.makedirs(args.dir, exist_ok=True)

    with open("data/prep-config.json") as f:
        config = json.load(f)
    with open("data/trust-pressures.json") as f:
        pressures = json.load(f)

    dmap = {e["code"]: e for e in config["trustDirectory"]}
    tp = pressures["trusts"]
    periods = pressures["periods"]

    for code in args.codes:
        dir_entry = dmap.get(code)
        pr = tp.get(code)
        if dir_entry is None:
            print(f"WARNING: {code} not found in trustDirectory (already profiled, or wrong code?)")
        if pr is None:
            print(f"WARNING: {code} not found in trust-pressures.json (no RTT/pressures data published for it)")
        out = {"directory": dir_entry, "pressures": pr, "periods": periods}
        with open(f"{args.dir}/{code}-layer1.json", "w") as f:
            json.dump(out, f, indent=2)
        print(f"{code}: wrote {args.dir}/{code}-layer1.json (directory={'found' if dir_entry else 'MISSING'}, pressures={'found' if pr else 'MISSING'})")


if __name__ == "__main__":
    main()
