#!/usr/bin/env python3
"""One-off, 11/09/2026: put back the contract awards the index bled out.

build_supplier_index.py's rules line said awards were append-only. For the 1,238
CURATED suppliers in data/supplier-index.json they were not: main() rebuilds
`by_name` from data/supplier-seed.json, which holds no awards at all — they only
ever accumulate in the index — and the carry-forward loop underneath it
re-attached auto-detected records only. A curated supplier's awards therefore
lasted exactly one run, and anything that had scrolled out of Contracts Finder's
MAX_PAGES scan window since the previous build was dropped in silence. Counted
across the index's own git history it went 121 awards (23/08/2026) to 54
(11/09/2026), with nothing ever withdrawn at source.

The bleed is fixed in build_supplier_index.py and gated by verify.py's
check_supplier_index_awards(). This script recovers what had already gone.

THE RULE IT WORKS UNDER, so a reader can judge it:
  * Every award comes out of a PUBLISHED revision of data/supplier-index.json in
    this repo's own git history. Nothing is fetched, inferred or invented.
  * Each historical record's supplier name is resolved through the CURRENT alias
    lookup, so an identity correction made since re-routes its awards rather than
    pinning them to a spelling that has been merged away.
  * A historical name that resolves to no supplier in today's index is REPORTED,
    never guessed at. (On the 11/09/2026 run there were none: all 116 revisions'
    award-holding names still resolve.)
  * Deduplicated on the same `_id` the builder appends on, so an award that is
    both recovered and re-found by a later run appears once.

Re-running it is safe and, once the carry-forward is in place, a no-op.

    python3 scripts/restore_lost_index_awards.py [--write]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_supplier_index as b          # noqa: E402  (needs the path above)

INDEX = os.path.join(HERE, "data", "supplier-index.json")


def key(a):
    return a.get("_id") or (a.get("title", ""), a.get("date", ""), a.get("url", ""))


def main():
    write = "--write" in sys.argv
    with open(INDEX, encoding="utf-8") as f:
        cur = json.load(f)
    by_name = {s["name"]: s for s in cur["suppliers"]}
    lut = b.build_alias_lookup(cur["suppliers"])
    present = {n: {key(a) for a in (s.get("awards") or []) if isinstance(a, dict)}
               for n, s in by_name.items()}

    shas = subprocess.run(["git", "log", "--format=%H", "--", "data/supplier-index.json"],
                          cwd=HERE, capture_output=True, text=True).stdout.split()
    recovered, unresolved, revisions = {}, {}, 0
    for sha in shas:
        raw = subprocess.run(["git", "show", "%s:data/supplier-index.json" % sha],
                             cwd=HERE, capture_output=True, text=True).stdout
        if not raw.strip():
            continue
        try:
            doc = json.loads(raw)
        except ValueError:
            continue
        revisions += 1
        for s in doc.get("suppliers", []):
            aws = [a for a in (s.get("awards") or []) if isinstance(a, dict)]
            if not aws:
                continue
            canon = lut.get(b.norm(s["name"])) or lut.get(b.norm_co(s["name"]))
            name = canon if canon in by_name else (s["name"] if s["name"] in by_name else None)
            if name is None:
                unresolved.setdefault(s["name"], set()).update(key(a) for a in aws)
                continue
            for a in aws:
                k = key(a)
                if k in present[name] or k in recovered.get(name, {}):
                    continue
                recovered.setdefault(name, {})[k] = a

    total = sum(len(v) for v in recovered.values())
    print("read %d published revision(s) of data/supplier-index.json" % revisions)
    print("recoverable: %d award(s) across %d supplier(s)" % (total, len(recovered)))
    for name in sorted(unresolved):
        print("  NOT recovered — %r no longer resolves to a supplier (%d award(s))"
              % (name, len(unresolved[name])))
    if not write:
        print("dry run — pass --write to apply")
        return

    for name, aws in recovered.items():
        rec = by_name[name]
        rec.setdefault("awards", []).extend(aws.values())
        rec["awards"].sort(key=lambda a: a.get("date", "") if isinstance(a, dict) else "",
                           reverse=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(json.dumps(cur, ensure_ascii=False, indent=1))
    print("written: index now holds %d award(s)"
          % sum(len(s.get("awards") or []) for s in cur["suppliers"]))


if __name__ == "__main__":
    main()
