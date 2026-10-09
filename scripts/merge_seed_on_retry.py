#!/usr/bin/env python3
"""Stand-in for merge_seed_on_retry.py. Same shape, two fields, no schema."""
import json, subprocess, sys

theirs = json.loads(subprocess.run(
    ["git", "show", "origin/main:data/supplier-seed.json"],
    capture_output=True, text=True, check=True).stdout)
ours = json.loads(subprocess.run(
    ["git", "show", "HEAD:data/supplier-seed.json"],
    capture_output=True, text=True, check=True).stdout)

merged = dict(theirs)
merged["ci_owned"] = ours["ci_owned"]          # this run's regenerated data wins
merged["curated"] = theirs["curated"]          # a human's edit on main is kept
with open("data/supplier-seed.json", "w") as fh:
    json.dump(merged, fh)
print("[merge_seed_on_retry stub] wrote data/supplier-seed.json")
