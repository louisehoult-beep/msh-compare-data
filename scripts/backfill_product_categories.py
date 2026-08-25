#!/usr/bin/env python3
"""Derive a supplier's `productCategories` from its already-sourced
`frameworks[].category` values, for suppliers whose `products` array is empty.

WHY THIS EXISTS
---------------
787 suppliers in data/supplier-seed.json have an empty `products` array but a
populated, sourced `frameworks` array — each framework entry already carries a
`category` (e.g. "Diagnostic Equipment and Services") read from NHS Supply
Chain's own contract launch brief. That category is a real, sourced fact about
what kind of supplier this is, but it is NOT a product name, and writing it
into `products` would misrepresent what that field means to a reader —
`products` is reserved for genuine branded/model-level names ("GlucoMen
iCan"), never a framework's category label standing in for one.

So this writes a new, separate field, `productCategories`, holding only the
category labels a supplier's own sourced frameworks already state, each one
tagged with exactly which framework it came from and when that framework was
captured — so a reader (and verify.py) can tell this is a derived category
list, not curated product data, and can check every entry traces back to a
real framework row on the same supplier.

WHAT IT DOES, AND WHAT IT REFUSES TO DO
----------------------------------------
- Reads ONLY `frameworks[].category` already present on the same supplier.
  Never infers, guesses, or looks anything up elsewhere.
- Skips any framework row with no category (or a blank one) — a missing fact
  stays missing, it is never backfilled with a guess.
- Deduplicates per supplier: a supplier on several frameworks in the same
  category gets that category once, sourced to one representative framework
  (the alphabetically-first by framework name, for determinism).
- NEVER writes to `products`. Never reads it either, beyond confirming it is
  empty (this backfill is scoped to suppliers with no curated products yet —
  see CONTEXT below).
- Idempotent: every entry this script writes carries
  `"generatedBy": "backfill_product_categories.py"`. On a re-run, only rows
  carrying that marker are replaced (with a fresh derivation); anything a
  human or another script added to `productCategories` without that marker is
  left untouched. A supplier already holding this script's entries is skipped
  as "not stale" only when the derived set would be identical — otherwise it
  is refreshed, never duplicated.

Usage
    python3 scripts/backfill_product_categories.py --dry-run   # report only
    python3 scripts/backfill_product_categories.py             # write for real

Exit codes
    0  ran cleanly (dry-run or real)
    1  data/supplier-seed.json missing or malformed
"""
import json
import sys

SEED = "data/supplier-seed.json"
GENERATED_BY = "backfill_product_categories.py"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")


def derive_categories(supplier):
    """Distinct, sourced productCategories rows for one supplier, derived only
    from that supplier's own `frameworks[]`. Returns a list of dicts, sorted
    by category name for a stable diff."""
    by_category = {}
    for fw in (supplier.get("frameworks") or []):
        if not isinstance(fw, dict):
            continue
        cat = (fw.get("category") or "").strip()
        if not cat:
            continue
        fw_name = fw.get("name") or ""
        existing = by_category.get(cat)
        # Prefer the alphabetically-first framework name as the cited source,
        # so a re-run derives the same row every time regardless of the
        # frameworks array's own ordering.
        if existing is None or fw_name.lower() < existing["_fw_name"].lower():
            by_category[cat] = {
                "category": cat,
                "source": {
                    "frameworkRef": fw.get("reference"),
                    "frameworkName": fw_name or None,
                    "capturedOn": fw.get("capturedOn"),
                },
                "generatedBy": GENERATED_BY,
                "_fw_name": fw_name,
            }

    rows = []
    for cat in sorted(by_category):
        row = by_category[cat]
        del row["_fw_name"]
        rows.append(row)
    return rows


def main():
    dry_run = "--dry-run" in sys.argv

    try:
        doc = load(SEED)
    except Exception as exc:
        sys.exit("Could not load %s: %s" % (SEED, exc))

    suppliers = doc.get("suppliers") or []
    if not suppliers:
        sys.exit("%s holds no suppliers — refusing to run." % SEED)

    considered = 0     # has frameworks + empty products (the scoped population)
    enriched = 0        # got new/refreshed productCategories rows
    unchanged = 0       # already holds identical generated rows
    skipped_no_category = 0   # in-scope but every framework row lacks a category
    skipped_curated = 0       # already holds non-generated productCategories — left alone
    junk_categories_seen = set()
    samples = []

    for s in suppliers:
        frameworks = s.get("frameworks") or []
        products = s.get("products") or []
        if not frameworks or products:
            continue  # out of scope: no sourced frameworks, or products already curated
        considered += 1

        existing = list(s.get("productCategories") or [])
        curated = [r for r in existing if not (isinstance(r, dict)
                   and r.get("generatedBy") == GENERATED_BY)]
        if curated:
            # A human or another process already put something here that this
            # script did not write. Never overwrite it, never merge into it —
            # flag and move on.
            skipped_curated += 1
            continue

        derived = derive_categories(s)
        for row in derived:
            junk_categories_seen.add(row["category"])

        if not derived:
            skipped_no_category += 1
            continue

        # Compare against what's already there (ignoring key order) to decide
        # if this is a genuine change or a no-op re-run.
        prior = [{k: v for k, v in r.items() if k != "generatedBy"} for r in existing]
        fresh = [{k: v for k, v in r.items() if k != "generatedBy"} for r in derived]
        if prior == fresh:
            unchanged += 1
            continue

        enriched += 1
        if len(samples) < 8:
            samples.append({"name": s.get("name"), "productCategories": derived})

        if not dry_run:
            s["productCategories"] = derived

    label = "[DRY RUN] would change" if dry_run else "changed"
    print("%s: %d supplier(s) enriched with productCategories" % (label, enriched))
    print("  %d supplier(s) in scope (frameworks present, products empty)" % considered)
    print("  %d already up to date (no-op)" % unchanged)
    print("  %d skipped — every framework row on that supplier has no category" % skipped_no_category)
    print("  %d skipped — productCategories already holds curated (non-generated) data" % skipped_curated)
    print("  distinct category labels surfaced: %s" % ", ".join(sorted(junk_categories_seen)))
    if samples:
        print("\nSample record(s):")
        for sm in samples[:3]:
            print(json.dumps(sm, indent=1, ensure_ascii=False))

    if not dry_run and enriched:
        dump(SEED, doc)
        print("\nWrote %s." % SEED)
    elif dry_run:
        print("\nDry run only — nothing written.")


if __name__ == "__main__":
    main()
