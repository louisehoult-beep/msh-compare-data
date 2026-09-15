#!/usr/bin/env python3
"""
test_orphaned_product_categories.py — proves a derived product category never
outlives the framework it was derived from, and that nothing else is touched.

THE HOLE THIS CLOSES. A supplier's `productCategories` is derived, by
backfill_product_categories.py, from the framework rows on that supplier: each
entry carries the `frameworkRef` it came from. backfill_index_frameworks.py
rewrites `frameworks[]` from the fresh brief capture on every company-intelligence
run — but nothing re-derived the categories, so a delisting left the category
behind, still citing a framework the supplier is no longer recorded as being on.
That is a published claim with its evidence removed.

It is not hypothetical. NHS Supply Chain took J & M Medical off the Textiles and
Associated Products brief (2025/S 000-048142); the run of 14/09/2026 and every
run after it failed the publish gate on the orphaned "Facilities and Office
Solutions" category, and the whole company-intelligence refresh — frameworks,
awards, Companies House — stopped landing for three days.

The tempting fix is to purge every category whose reference is not currently in
frameworks[]. That would delete correct data in two shapes that look identical
from the inside: a curated category somebody entered by hand, and a supplier the
capture simply did not cover this cycle (same reasoning as the `if not hits`
skip in backfill_index_frameworks.main(), see STALE-BRIEF-ROWS-2026-09-02.md).
So the pruner must drop ONLY a generated row whose framework has gone from a
supplier that still has framework references, and leave every other shape alone.

    python3 test_orphaned_product_categories.py

Exit 0 = the distinction holds. Exit 1 = correct data could be deleted, or an
unevidenced category could still be published.
"""
import copy
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

spec = importlib.util.spec_from_file_location(
    "bif", os.path.join(REPO, "scripts", "backfill_index_frameworks.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

GEN = "backfill_product_categories.py"
fails = []


def check(desc, got, want):
    if got != want:
        fails.append("%s\n     got %r, want %r" % (desc, got, want))


def fw(ref):
    return {"name": "Framework " + ref, "reference": ref, "source": "nhssc-brief"}


def cat(label, ref, generated=True):
    row = {"category": label, "source": {"frameworkRef": ref, "frameworkName": "Framework " + str(ref)}}
    if generated:
        row["generatedBy"] = GEN
    return row


def categories_of(s):
    return [r.get("category") for r in (s.get("productCategories") or [])]


# --- the shapes that actually occur -----------------------------------------
# Each case: (description, supplier record, categories that must survive,
#             how many rows must be reported dropped)
CASES = [
    ("the J & M Medical case: framework delisted, its generated category goes",
     {"name": "J & M Medical",
      "frameworks": [fw("2024/S 000-001161")],
      "productCategories": [cat("Facilities and Office Solutions", "2025/S 000-048142"),
                            cat("Medical and Surgical Consumables", "2024/S 000-001161")]},
     ["Medical and Surgical Consumables"], 1),

    ("a generated category whose framework is still there is kept",
     {"name": "Still on both",
      "frameworks": [fw("A/1"), fw("B/2")],
      "productCategories": [cat("Alpha", "A/1"), cat("Beta", "B/2")]},
     ["Alpha", "Beta"], 0),

    ("a CURATED category is never dropped, even with its framework gone",
     {"name": "Hand-entered",
      "frameworks": [fw("A/1")],
      "productCategories": [cat("Someone's own fact", "GONE/9", generated=False)]},
     ["Someone's own fact"], 0),

    ("a capture gap — no framework references at all — drops nothing",
     {"name": "Not covered this cycle",
      "frameworks": [],
      "productCategories": [cat("Alpha", "A/1")]},
     ["Alpha"], 0),

    ("frameworks present but none carrying a reference drops nothing",
     {"name": "Curated rows without references",
      "frameworks": [{"name": "Some curated framework"}],
      "productCategories": [cat("Alpha", "A/1")]},
     ["Alpha"], 0),

    ("a generated row citing no frameworkRef is left alone — nothing to check it against",
     {"name": "No reference to judge",
      "frameworks": [fw("A/1")],
      "productCategories": [{"category": "Unsourced", "source": {"frameworkName": "Something"},
                             "generatedBy": GEN}]},
     ["Unsourced"], 0),

    ("a supplier with no productCategories at all is untouched",
     {"name": "Nothing derived", "frameworks": [fw("A/1")]},
     [], 0),
]

for desc, supplier, survivors, want_dropped in CASES:
    s = copy.deepcopy(supplier)
    before = copy.deepcopy(s)
    dropped = B.prune_orphaned_categories(s)
    check("%s — rows dropped" % desc, dropped, want_dropped)
    check("%s — categories left" % desc, categories_of(s), survivors)
    check("%s — frameworks[] untouched" % desc, s.get("frameworks"), before.get("frameworks"))
    check("%s — name untouched" % desc, s.get("name"), before.get("name"))

# The field is REMOVED, not left as an empty list: an empty array reads as
# "we looked and there are none", which is a different and untrue statement
# from "nothing is derived here".
s = {"name": "Everything orphaned", "frameworks": [fw("A/1")],
     "productCategories": [cat("Alpha", "GONE/9")]}
B.prune_orphaned_categories(s)
check("a supplier left with no surviving categories loses the field entirely",
      "productCategories" in s, False)

# Idempotence: a second pass must find nothing, or the pruner is unstable and
# the workflow's re-run after a rebase would keep changing the file.
s = {"name": "J & M Medical", "frameworks": [fw("2024/S 000-001161")],
     "productCategories": [cat("Facilities and Office Solutions", "2025/S 000-048142"),
                           cat("Medical and Surgical Consumables", "2024/S 000-001161")]}
B.prune_orphaned_categories(s)
check("pruning twice drops nothing the second time", B.prune_orphaned_categories(s), 0)

# --- the live data, if it is here -------------------------------------------
# The invariant verify.py's seed-product-categories check enforces, asserted
# here over whatever is actually on disk: every generated category on a
# supplier that HAS framework references must cite one of them.
import json

for path in ("data/supplier-seed.json", "data/supplier-index.json"):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        print("skipping the live-data check (%s not found)" % path)
        continue
    orphans = []
    for s in (doc.get("suppliers") or []):
        if not isinstance(s, dict):
            continue
        own = {f.get("reference") for f in (s.get("frameworks") or [])
               if isinstance(f, dict) and f.get("reference")}
        if not own:
            continue
        for r in (s.get("productCategories") or []):
            if not isinstance(r, dict) or r.get("generatedBy") != GEN:
                continue
            src = r.get("source")
            ref = src.get("frameworkRef") if isinstance(src, dict) else None
            if ref and ref not in own:
                orphans.append("%s: %r cites %s" % (s.get("name"), r.get("category"), ref))
    if orphans:
        fails.append("%s carries %d orphaned generated category/ies, which the publish "
                     "gate will reject:\n     %s" % (path, len(orphans), "\n     ".join(orphans)))
    else:
        print("%-28s no orphaned generated categories" % path)

if fails:
    print("\nFAILED — a derived category is out of step with its evidence:\n")
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)

print("OK — orphaned categories are dropped, curated and uncovered ones are kept.")
