#!/usr/bin/env python3
"""Merge verified trust-profile JSON files into data/prep-config.json.

Usage: python3 scripts/merge_trust_profiles.py [--dir DIR] <CODE1> [CODE2 ...]

Refuses:
  - a code already present in prep-config.json trusts[]
  - a profile whose name does not match trustDirectory's entry for that code
  - a profile with the wrong key order/set

Run from the repo root (or a worktree of it) — expects ./data/prep-config.json.
Writes with indent=1 to match the file's existing convention; a different indent
width reformats the whole file and makes the diff unreviewable.
"""
import argparse
import json
import sys

CONFIG_PATH = "data/prep-config.json"
EXPECTED_KEYS = ["name", "code", "region", "context", "news", "structure", "reportFacts", "people", "voices"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="tmp/trust-batch")
    ap.add_argument("codes", nargs="+")
    args = ap.parse_args()

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    existing_codes = {t.get("code") for t in config["trusts"]}
    dir_by_code = {e["code"]: e for e in config["trustDirectory"]}

    to_add = []
    for code in args.codes:
        if code in existing_codes:
            print(f"REFUSED: {code} is already profiled in prep-config.json")
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

        dir_entry = dir_by_code.get(code)
        if not dir_entry:
            print(f"REFUSED: {code} not found in trustDirectory")
            sys.exit(1)

        if profile.get("name") != dir_entry["n"]:
            print(f"REFUSED: {code} name mismatch: profile={profile.get('name')!r} vs trustDirectory={dir_entry['n']!r}")
            sys.exit(1)

        to_add.append(profile)

    config["trusts"].extend(to_add)

    merged_codes = {p["code"] for p in to_add}
    before = len(config["trustDirectory"])
    config["trustDirectory"] = [e for e in config["trustDirectory"] if e["code"] not in merged_codes]
    after = len(config["trustDirectory"])

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"Merged {len(to_add)} trust(s): {sorted(merged_codes)}")
    print(f"trustDirectory: {before} -> {after}")
    print(f"trusts: {len(config['trusts']) - len(to_add)} -> {len(config['trusts'])}")


if __name__ == "__main__":
    main()
