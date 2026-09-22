#!/usr/bin/env python3
"""Merge REFRESHED trust-profile JSON files back into data/prep-config.json, in place.

Usage: python3 scripts/refresh_merge_trust_profiles.py [--dir DIR] [--date YYYY-MM-DD] <CODE1> [CODE2 ...]

The sibling script merge_trust_profiles.py is BUILD-only: it refuses any code already
present in trusts[]. A refresh is the opposite case, so this script updates the existing
entry in place instead of appending a new one.

Refuses:
  - a code NOT already present in prep-config.json trusts[] (that is a build, not a refresh)
  - a profile with the wrong key order/set
  - a profile whose name does not match the name already recorded for that code

Preserves any key the existing entry carries that a profile file does not (notably
`contacts`), and stamps `verifiedAt`. Writes with indent=1 to match the file's existing
convention; a different indent width reformats the whole file and makes the diff
unreviewable.
"""
import argparse
import datetime
import json
import sys

CONFIG_PATH = "data/prep-config.json"
EXPECTED_KEYS = ["name", "code", "region", "context", "news", "structure", "reportFacts", "people", "voices"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="tmp/trust-batch")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("codes", nargs="+")
    args = ap.parse_args()

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    by_code = {}
    for i, t in enumerate(config["trusts"]):
        by_code.setdefault(t.get("code"), i)

    updated, unchanged = [], []
    for code in args.codes:
        idx = by_code.get(code)
        if idx is None:
            print(f"REFUSED: {code} is not yet profiled in prep-config.json (use merge_trust_profiles.py)")
            sys.exit(1)

        profile_path = f"{args.dir}/{code}-profile.json"
        try:
            with open(profile_path) as f:
                profile = json.load(f)
        except FileNotFoundError:
            print(f"REFUSED: no profile file at {profile_path}")
            sys.exit(1)

        if list(profile.keys()) != EXPECTED_KEYS:
            print(f"REFUSED: {code} has wrong key order/set: {list(profile.keys())}")
            sys.exit(1)

        existing = config["trusts"][idx]
        if profile.get("name") != existing.get("name"):
            print(f"REFUSED: {code} name mismatch: profile={profile.get('name')!r} vs recorded={existing.get('name')!r}")
            sys.exit(1)

        before = {k: existing.get(k) for k in EXPECTED_KEYS}
        merged = dict(existing)
        merged.update(profile)
        merged["verifiedAt"] = args.date
        config["trusts"][idx] = merged

        if before == {k: profile.get(k) for k in EXPECTED_KEYS}:
            unchanged.append(code)
        else:
            updated.append(code)

    config["dataAsOf"] = datetime.date.fromisoformat(args.date).strftime("%d/%m/%Y")

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"Stamped verifiedAt={args.date} on {len(args.codes)} trust(s)")
    print(f"  content changed: {len(updated)} {sorted(updated)}")
    print(f"  content identical: {len(unchanged)} {sorted(unchanged)}")
    print(f"  dataAsOf -> {config['dataAsOf']}")


if __name__ == "__main__":
    main()
