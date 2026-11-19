"""One-off: let the Transcatheter Heart Valve matrix's lots reach the brief's own
bare supplier names (17/11/2026).

WHY. NHS Supply Chain's brief for Transcatheter Heart Valve Repair, Replacement
and Associated Devices names its 11 suppliers as BARE WORDS — "Abbott",
"Edwards", "MCT", "BVM", "Biosensors", "Jenavalve" — and its count is verified
against the page's own stated total, so the capture is complete. The product
matrix attached to the same brief (issued 9 September 2026) names the same
companies in full legal form. refresh_framework_lots attaches a lot-source name
to a brief row only where the two normalise identically or both resolve to the
same Hub company, so six brief rows hold no lots and six matrix names sit in
`unresolved`.

WHAT THIS DOES. Records, on the Hub record each name belongs to, the brief's bare
word and the matrix's own spelling, so both sides of the same company meet:

    Edwards Lifesciences      "Edwards", "Edwards Lidesciences Limited"
    BVM Medical Ltd           "BVM"
    MCT Lifesciences Ltd      "MCT"
    Abbott Medical U.K. Ltd   "Abbott Meditcal UK Limited"

The two misspellings are NHS Supply Chain's own, in its own published matrix, and
are recorded as such with the file and its issue date. Without the Edwards one
the bare brief word attaches nothing, because the matrix row is the only place
the lots exist.

WHAT THIS DELIBERATELY DOES NOT DO.

* ABBOTT'S LOTS STAY UNATTACHED. The brief's bare "Abbott" resolves to ABBOTT
  DIABETES CARE, which holds the bare alias "abbott". On a transcatheter heart
  valve framework the company is Abbott Medical U.K. Ltd. The two sides therefore
  resolve to different Hub records and nothing attaches — which is the correct
  outcome: a global alias index cannot hold a truth that is only true on one
  framework, and attaching TAVI lots to a diabetes-care record would be a false
  statement about a named company. Do not "fix" this by moving the bare "abbott"
  alias.
* NO NEW RECORDS. Biosensors International UK Limited and JenaValve Production
  Limited have no Hub record. Both are transcatheter heart valve manufacturers,
  so they are clinical and in scope, but creating a record needs its own identity
  work and is not part of this change.

MEASURED BEFORE WRITING: re-resolving 5,922 distinct names (award rows, both
quarantine blocks, every brief's supplier list and every lot source) these
aliases change exactly five resolutions — the five names above — and nothing
else. No new ambiguity anywhere.

AFTER THIS:
    python3 scripts/_reparse_matrix_heading_rows_1117.py --cache DIR
    bash scripts/gate.sh
Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seed_format  # noqa: E402

SEED = "data/supplier-seed.json"
MATRIX = ("NHS Supply Chain's Product Matrix for Transcatheter Heart Valve Repair, "
          "Replacement and Associated Devices, issued 9 September 2026 "
          "(Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx)")

ADD = {
    "Edwards Lifesciences": [
        ("Edwards", "the name NHS Supply Chain's own brief uses for this company on "
                    "Transcatheter Heart Valve Repair, Replacement and Associated Devices"),
        ("Edwards Lidesciences Limited", "this company's name as spelled (mis-spelled) in " + MATRIX),
    ],
    "BVM Medical Ltd": [
        ("BVM", "the name NHS Supply Chain's own brief uses for this company on "
                "Transcatheter Heart Valve Repair, Replacement and Associated Devices"),
    ],
    "MCT Lifesciences Ltd": [
        ("MCT", "the name NHS Supply Chain's own brief uses for this company on "
                "Transcatheter Heart Valve Repair, Replacement and Associated Devices"),
    ],
    "Abbott Medical U.K. Ltd": [
        ("Abbott Meditcal UK Limited", "this company's name as spelled (mis-spelled) in " + MATRIX),
    ],
}


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    with open(SEED, encoding="utf-8") as f:
        seed = json.load(f)
    suppliers = seed["suppliers"] if isinstance(seed, dict) else seed
    by_name = {}
    for s in suppliers:
        by_name.setdefault(s.get("name"), []).append(s)

    missing = [n for n in ADD if len(by_name.get(n) or []) != 1]
    if missing:
        sys.exit("these records are not present exactly once, so nothing was written: %s"
                 % ", ".join(missing))

    changed = []
    for name, entries in ADD.items():
        rec = by_name[name][0]
        aliases = list(rec.get("aliases") or [])
        added = []
        for alias, why in entries:
            if alias not in aliases:
                aliases.append(alias)
                added.append((alias, why))
        if not added:
            continue
        rec["aliases"] = aliases
        line = ("Aliases recorded 2026-11-17 so the Transcatheter Heart Valve brief's "
                "own supplier names reach this record: "
                + "; ".join("%r — %s" % (a, w) for a, w in added) + ".")
        if line not in (rec.get("identityNote") or ""):
            rec["identityNote"] = ((rec.get("identityNote") or "").rstrip() + " " + line).strip()
        changed.append((name, [a for a, _ in added]))

    if not changed:
        print("nothing to do — already applied.")
        return 0
    fmt, round_trips = seed_format.write_like(SEED, seed)
    print(seed_format.describe(SEED, fmt, round_trips))
    for name, added in changed:
        print("  + %-28s %s" % (name, added))
    print("\nNow: python3 scripts/_reparse_matrix_heading_rows_1117.py --cache DIR "
          "&& bash scripts/gate.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
