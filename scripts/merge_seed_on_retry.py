"""
merge_seed_on_retry.py — called by company-intelligence.yml and any other
automated workflow when a push is rejected and a rebase is needed.

WHY THIS EXISTS (^o478, landed 16/09/2026)
-------------------------------------------
On 15/09/2026 two automated commits reached data/supplier-seed.json within
17 minutes of each other. The second (hub-bot) used `git pull --rebase -X theirs`,
which replays the hub-bot commit's version of the file on top of origin/main.
Because the hub-bot had read supplier-seed.json before the first commit landed,
its version of the file lacked the first commit's curated additions (Ovidius
links). `-X theirs` caused git to choose hub-bot's stale version, silently
discarding those additions. The same class of bug already caused data loss on
12/08/2026 (company-financials race), 14/08/2026 (JSON text-merge corruption),
18/08/2026, 25/08/2026 and 26/08/2026.

This script replaces the `-X theirs` step for supplier-seed.json specifically.
It reads the current HEAD (this workflow's modified version) and origin/main
(the freshest curated state), and produces a merged result that:

  - includes EVERY supplier from origin/main (the master record)
  - applies this workflow's field updates to each supplier, but ONLY
    to the fields this workflow is authoritative for
  - never discards a curated field (website, links, aliases, note,
    background, alerts) that exists in origin/main but not in HEAD

USAGE
-----
Called by company-intelligence.yml after a push rejection, before the next
commit-and-push attempt:

    git fetch origin
    python3 scripts/merge_seed_on_retry.py
    git add data/supplier-seed.json

The script exits 0 on success (merged seed written to data/supplier-seed.json)
or 1 on any error (caller should abort rather than push a possibly-corrupt file).

No arguments. Reads from the working tree and from git's object database.
"""
import json, subprocess, sys
# seed_format lives beside this script. Imported this way because these scripts
# are also loaded by tests via spec_from_file_location, which does not put the
# script's own directory on sys.path the way running it directly does.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from seed_format import write_like, describe


SEED = "data/supplier-seed.json"

# Fields this workflow (company-intelligence) is authoritative for.
# On a conflict (both sides non-empty and different), prefer HEAD's value.
CI_OWNED_FIELDS = {
    "companyNumber",
    "companyNumberCandidate",
    "registeredName",
    "companyStatus",
    "incorporationDate",
    "sicCodes",
    "officers",
}

# Fields that are curated by hand and should NEVER be lost from origin/main,
# even if HEAD has a null or empty value for them. On a conflict (both non-empty
# and different), prefer origin/main's value — curators have primacy.
CURATED_FIELDS = {
    "website",
    "links",
    "aliases",
    "note",
    "background",
    "alerts",
    "companyNumberProof",
}


def load_from_git(rev_path):
    """Load a JSON file from a specific git revision (e.g. 'origin/main:data/supplier-seed.json')."""
    try:
        raw = subprocess.check_output(
            ["git", "show", rev_path],
            stderr=subprocess.DEVNULL,
        )
        return json.loads(raw)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        sys.exit("ABORT: could not read %s from git: %s" % (rev_path, exc))


def load_file(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        sys.exit("ABORT: could not read %s: %s" % (path, exc))


def _is_empty(v):
    return v is None or v == [] or v == "" or v == {}


def merge_supplier(head_s, main_s):
    """Merge two supplier records. Returns a new dict."""
    merged = dict(head_s)  # start from HEAD

    # Walk every key in origin/main's version
    for key, main_val in main_s.items():
        head_val = head_s.get(key)

        if key in CI_OWNED_FIELDS:
            # HEAD wins when non-empty; fall back to origin/main if HEAD is empty
            if _is_empty(head_val) and not _is_empty(main_val):
                merged[key] = main_val
            # else keep HEAD's value (already in merged)

        elif key in CURATED_FIELDS:
            # origin/main wins when non-empty; HEAD wins only when origin/main is empty
            if not _is_empty(main_val):
                merged[key] = main_val
            # else keep HEAD's value (already in merged) or leave null if HEAD also empty

        else:
            # For any other field: prefer the non-empty value; if both non-empty, HEAD wins.
            if _is_empty(head_val) and not _is_empty(main_val):
                merged[key] = main_val
            # else keep HEAD's value

    # Also add any keys that are only in HEAD (already in merged)
    return merged


def run():
    head = load_file(SEED)
    main = load_from_git("origin/main:" + SEED)

    head_by_name = {s["name"]: s for s in head.get("suppliers", [])}
    main_by_name = {s["name"]: s for s in main.get("suppliers", [])}

    result_suppliers = []
    added_from_main = 0
    merged_count = 0
    head_only = 0

    # Walk origin/main first (it is the master record — every supplier there stays)
    for name, main_s in main_by_name.items():
        if name in head_by_name:
            result_suppliers.append(merge_supplier(head_by_name[name], main_s))
            merged_count += 1
        else:
            # HEAD removed or never had this supplier; keep origin/main's version
            result_suppliers.append(main_s)
            added_from_main += 1

    # Then any suppliers that are in HEAD but not in origin/main (new additions)
    for name, head_s in head_by_name.items():
        if name not in main_by_name:
            result_suppliers.append(head_s)
            head_only += 1

    # Sort by name (case-insensitive) to preserve the file's canonical order
    result_suppliers.sort(key=lambda s: s.get("name", "").lower())

    # Build output, preserving the header fields from origin/main
    out = dict(main)
    out["suppliers"] = result_suppliers

    # Keep the file's existing byte format rather than asserting one. This
    # hardcoded indent=2, and because it runs on every push race it is what put
    # main's seed into indent=2 while five other writers still believed it was
    # minified (`^o584`). See scripts/seed_format.py.
    fmt, round_trips = write_like(SEED, out)
    print(describe(SEED, fmt, round_trips))

    print(
        "[merge_seed_on_retry] wrote %s: %d merged, %d preserved from origin/main, "
        "%d new from HEAD" % (SEED, merged_count, added_from_main, head_only)
    )


if __name__ == "__main__":
    run()
