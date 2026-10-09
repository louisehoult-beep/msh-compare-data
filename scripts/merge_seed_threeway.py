#!/usr/bin/env python3
"""Three-way merge for data/supplier-seed.json (single-line minified JSON).

Text merge is useless here: the whole file is one line, so any two changes
collide. Merge by supplier name instead.

  base   = merge-base version
  ours   = the branch being cherry-picked onto (already has origin's edits)
  theirs = the backfill commit being replayed

Rule: keep every company either side added, apply either side's edits to an
existing company, and refuse (exit 1) if both sides edited the same company
differently. Identical edits on both sides are not a conflict.
"""
import json
import subprocess
import sys

REPO = None


def load(rev, path="data/supplier-seed.json"):
    out = subprocess.run(["git", "show", f"{rev}:{path}"],
                         capture_output=True, check=True, cwd=REPO)
    return json.loads(out.stdout)


def by_name(doc):
    return {s["name"]: s for s in doc["suppliers"]}


def main():
    global REPO
    base_rev, ours_rev, theirs_rev, out_path = sys.argv[1:5]
    REPO = sys.argv[5] if len(sys.argv) > 5 else None

    base_doc, ours_doc, theirs_doc = load(base_rev), load(ours_rev), load(theirs_rev)
    B, O, T = by_name(base_doc), by_name(ours_doc), by_name(theirs_doc)

    # Top-level keys other than suppliers must not diverge silently.
    for k in set(base_doc) | set(ours_doc) | set(theirs_doc):
        if k == "suppliers":
            continue
        o, t = ours_doc.get(k), theirs_doc.get(k)
        if o != t and o != base_doc.get(k) and t != base_doc.get(k):
            sys.exit(f"CONFLICT: top-level key {k!r} edited on both sides")

    conflicts = []
    for name in set(O) & set(T):
        o_edit = O[name] != B.get(name)
        t_edit = T[name] != B.get(name)
        if o_edit and t_edit and O[name] != T[name]:
            conflicts.append(name)
    if conflicts:
        sys.exit("CONFLICT: edited differently on both sides: " + ", ".join(sorted(conflicts)))

    # Walk theirs' ordering (it holds the new companies in place), then append
    # anything only ours has. For each name take whichever side edited it.
    merged, seen = [], set()

    def pick(name):
        if name in T and T[name] != B.get(name):
            return T[name]
        if name in O and O[name] != B.get(name):
            return O[name]
        return O.get(name, T.get(name))

    for s in theirs_doc["suppliers"]:
        merged.append(pick(s["name"]))
        seen.add(s["name"])
    for s in ours_doc["suppliers"]:
        if s["name"] not in seen:
            merged.append(pick(s["name"]))
            seen.add(s["name"])

    out = dict(ours_doc)
    for k in theirs_doc:
        if k != "suppliers" and theirs_doc[k] != base_doc.get(k):
            out[k] = theirs_doc[k]
    out["suppliers"] = merged

    text = json.dumps(out, separators=(",", ":"), ensure_ascii=False)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    added_t = len(set(T) - set(B))
    added_o = len(set(O) - set(B))
    print(f"base {len(B)} | ours {len(O)} (+{added_o}) | theirs {len(T)} (+{added_t}) "
          f"-> merged {len(merged)}")
    names = [s["name"] for s in merged]
    if len(names) != len(set(names)):
        sys.exit("CONFLICT: duplicate names in merged output")


if __name__ == "__main__":
    main()
