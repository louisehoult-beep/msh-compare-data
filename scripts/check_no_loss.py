#!/usr/bin/env python3
"""
check_no_loss.py — refuse to lose a record without being told.

Git sees these data files as lines. It will merge, rebase and fast-forward a JSON
file that has quietly lost half its entries, and nothing about that looks like a
conflict. On 12/08/2026 a laptop crawl rebuilt data/supplier-products.json from a
state that predated the Arjo UK and HoverTech International ranges. A plain push
would have deleted both from the live data with no warning anywhere.

So this compares BY RECORD, not by line. For every JSON file under data/ it finds
the collections inside, works out each record's identity, and reports any identity
that exists in the baseline and not in the candidate.

  python3 scripts/check_no_loss.py
      working tree vs origin/main. Run this before every push from a laptop.

  python3 scripts/check_no_loss.py --base HEAD~5 --head HEAD
      audit any two revisions, e.g. to ask what a week of runs quietly dropped.

  python3 scripts/check_no_loss.py --file data/supplier-seed.json

Exit 0 = nothing lost. Exit 1 = something would be lost, and it is named.
A loss is not automatically wrong: a supplier that genuinely stopped trading
should go. It is only ever wrong to lose one WITHOUT NOTICING, which is the
whole job of this script. Use --allow to record a deletion you have decided on.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

# Keys that hold housekeeping rather than records, and would only add noise.
SKIP_KEYS = {"_notice", "_meta", "meta", "thresholds"}

# Tried in order to identify a record inside a list.
ID_KEYS = ("name", "id", "slug", "title", "trust", "code", "company",
           "companyName", "supplier", "url", "sku")

# Company names are written a dozen ways and the pipeline keeps normalising them:
# "Stryker UK Limited" becomes "Stryker", "Vernacare International Limited" becomes
# an alias of "Vernacare". Those are the pipeline working, not records going missing.
# A checker that shouts about 25 of them a week is a checker nobody runs, so a name
# that still exists in some recognisable form is reported separately and does not
# fail the run. Only a name with no trace left is a loss.
SUFFIXES = re.compile(
    r"\b(u\.?k\.?|limited|ltd|plc|llp|lp|inc|international|group|holdings"
    r"|medical|healthcare|health\s+care|medtech)\b")


def core(name):
    """A company name with the corporate furniture stripped off."""
    x = name.lower().replace("&", " and ")
    x = re.sub(r"[^a-z0-9 ]", " ", x)
    x = SUFFIXES.sub(" ", x)
    return re.sub(r"\s+", " ", x).strip()


def surviving_forms(records):
    """Every name still findable in a collection: names, aliases, and their cores."""
    forms = set()
    for key, rec in records.items():
        forms.add(key)
        if isinstance(rec, dict):
            for k in ("name", "title", "company", "companyName", "supplier"):
                v = rec.get(k)
                if isinstance(v, str):
                    forms.add(v)
            for a in rec.get("aliases") or []:
                if isinstance(a, str):
                    forms.add(a)
    return forms | {core(f) for f in forms}


def read(rev, path):
    """The file at a revision, or None if it wasn't there."""
    if rev is None:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    r = subprocess.run(["git", "show", f"{rev}:{path}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def identity(item, index):
    """A stable name for one record."""
    if isinstance(item, dict):
        for k in ID_KEYS:
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        # No obvious key. Hash the content so a moved record is not read as a
        # deletion plus an addition.
        return "sha:" + str(hash(json.dumps(item, sort_keys=True, ensure_ascii=False)))
    if isinstance(item, str):
        return item
    return f"[{index}]"


def collections(doc, prefix=""):
    """Every collection of records in the document, as {path: {identity: record}}."""
    found = {}
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k in SKIP_KEYS:
                continue
            here = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                # A dict whose values are records is itself a collection, and its
                # keys are the identities. A dict of scalars is configuration.
                if v and all(isinstance(x, (dict, list)) for x in v.values()):
                    found[here] = dict(v)
                else:
                    found.update(collections(v, here))
            elif isinstance(v, list):
                if v and all(isinstance(x, (dict, str)) for x in v):
                    found[here] = {identity(x, i): x for i, x in enumerate(v)}
    elif isinstance(doc, list):
        found[prefix or "(root)"] = {identity(x, i): x for i, x in enumerate(doc)}
    return found


def compare(base_doc, head_doc):
    """[(collection, [gone], [renamed])] — gone fails, renamed is reported only."""
    if base_doc is None:
        return []
    if head_doc is None:
        return [("(whole file)", ["FILE DELETED"], [])]
    b, h = collections(base_doc), collections(head_doc)
    out = []
    for path, brecs in sorted(b.items()):
        if path not in h:
            out.append((path, [f"COLLECTION REMOVED ({len(brecs)} records)"], []))
            continue
        missing = [x for x in sorted(set(brecs) - set(h[path]))
                   if not x.startswith("sha:")]
        if not missing:
            continue
        forms = surviving_forms(h[path])
        gone, renamed = [], []
        (renamed if False else gone)  # keep flake quiet
        for x in missing:
            (renamed if (x in forms or core(x) in forms) else gone).append(x)
        if gone or renamed:
            out.append((path, gone, renamed))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/main",
                    help="revision to compare against (default: origin/main)")
    ap.add_argument("--head", default=None,
                    help="revision to check (default: the working tree)")
    ap.add_argument("--file", action="append",
                    help="limit to these paths (default: every data/*.json)")
    ap.add_argument("--allow", action="append", default=[],
                    help="an identity you have decided to delete; repeatable")
    ap.add_argument("--show-renames", action="store_true",
                    help="also list names that were normalised or made an alias")
    args = ap.parse_args()

    paths = args.file or sorted(glob.glob("data/*.json"))
    allowed = set(args.allow)
    total = renames = 0

    for path in paths:
        base_doc = read(args.base, path)
        head_doc = read(args.head, path)
        if base_doc is None and head_doc is None:
            continue
        for coll, gone, renamed in compare(base_doc, head_doc):
            gone = [x for x in gone if x not in allowed]
            renames += len(renamed)
            if gone:
                total += len(gone)
                print(f"\nLOSS  {path} :: {coll} — {len(gone)} record(s) would be lost")
                for x in gone[:40]:
                    print(f"        {x}")
                if len(gone) > 40:
                    print(f"        ... and {len(gone) - 40} more")
            if renamed and args.show_renames:
                print(f"\nrenamed  {path} :: {coll} — {len(renamed)}, still present "
                      f"under another form")
                for x in renamed[:40]:
                    print(f"        {x}")

    head_name = args.head or "the working tree"
    tail = f" {renames} name(s) were normalised or made an alias; "\
           f"re-run with --show-renames to see them." if renames else ""
    if total:
        print(f"\n{total} record(s) present in {args.base} are missing from {head_name}.")
        print("Restore them, or re-run with --allow for each one you meant to delete.")
        if tail:
            print(tail.strip())
        return 1
    print(f"No records lost between {args.base} and {head_name}.{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
