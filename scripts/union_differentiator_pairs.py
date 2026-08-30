#!/usr/bin/env python3
"""
union_differentiator_pairs.py — add newly crawled (supplier, division) pairs to
the category map WITHOUT regenerating the pair list.

WHY THIS EXISTS. `seed_differentiator_map.py` rebuilds the worklist from
data/supplier-products.json alone. That file holds no NHS Supply Chain supplier,
so a rebuild deletes every `kind: "nhssc-term"` entry and every division
belonging to a supplier reached only through the NHSSC catalogue — 982 mapped
pairs covering 10,850 products when it was run unguarded on 29/08, including
Coloplast, BD, B. Braun, Smith+Nephew, Medtronic, Boston Scientific and Stryker.
It now refuses to run for that reason, which left new crawl captures with no
route into the map at all: `merge_differentiator_parts.py` refuses any decision
for a pair that is not already in the worklist.

This script is the missing half. It is APPEND-ONLY by construction:

  * every existing entry is carried through unchanged, object for object
  * a pair already in the map is never touched — not its `hub`, not its
    `examples`, not its `notTaxonomy` flag, even if the fresh crawl now sees
    different products under it
  * only pairs with NO entry at all are appended, unmapped, for judging

Two assertions enforce that rather than trusting it, because the loss the
seeder caused was silent and a later push publishes it.

Usage:  python3 scripts/union_differentiator_pairs.py [--apply]
Without --apply it reports and changes nothing.
"""
import json, os, sys, collections

MAP = "data/differentiator-category-map.json"
PRODUCTS = "data/supplier-products.json"

# Same list as seed_differentiator_map.py: labels a crawler picks up from site
# navigation that are not a product taxonomy. A pair marked notTaxonomy is not a
# mapping question — the crawl read the wrong element and the fix is in the
# crawler, not here.
NOT_TAXONOMY = {
    "uncategorized", "uncategorised", "brands", "catalog", "catalogue", "sectors",
    "full store", "products", "product type", "products detail", "all products",
    "shop", "store", "home", "categories", "category", "range", "ranges",
    "our products", "product range", "browse", "all", "other", "misc",
    "miscellaneous", "general", "new", "featured", "clearance", "offers",
}


def _key(e):
    """Identity of a map entry. nhssc-term rows are (supplier, term); division
    rows are (supplier, division)."""
    if e.get("kind") == "nhssc-term":
        return ("nhssc", e["supplier"], e.get("term"))
    return ("division", e["supplier"], e.get("division"))


def main():
    apply_it = "--apply" in sys.argv
    doc = json.load(open(MAP))
    before = doc["entries"]
    # A division entry is identified by (supplier, division); an nhssc-term entry
    # by (supplier, term) and carries division: null. Keying both on division
    # would collapse every one of a supplier's NHSSC terms onto (supplier, None).
    known = {_key(e) for e in before}

    sup = json.load(open(PRODUCTS))["suppliers"]

    counts = collections.Counter()
    examples = collections.defaultdict(list)
    cats = collections.defaultdict(collections.Counter)
    for co, rec in sup.items():
        for p in rec.get("products") or []:
            key = (co, p.get("division") or "")
            counts[key] += 1
            if len(examples[key]) < 4:
                examples[key].append(p.get("n") or "")
            if p.get("category"):
                cats[key][p["category"]] += 1

    new = []
    for (co, div), n in counts.most_common():
        if ("division", co, div) in known:
            continue
        new.append({
            "supplier": co,
            "division": div,
            "products": n,
            "categories": [c for c, _ in cats[(co, div)].most_common(12)],
            "examples": examples[(co, div)],
            "hub": None,
            "notTaxonomy": (div or "").strip().lower() in NOT_TAXONOMY,
            "evidence": "the supplier's own site filing, read by "
                        "scripts/crawl_supplier_site.py",
        })

    by_supplier = collections.Counter(e["supplier"] for e in new)
    print("%d new (supplier, division) pair(s), %d products:"
          % (len(new), sum(e["products"] for e in new)))
    for s, k in by_supplier.most_common():
        print("  %4d  %s" % (k, s))

    entries = before + new

    # Append-only, asserted rather than assumed.
    assert entries[:len(before)] == before, \
        "existing entries were modified — refusing to write"
    # Not global uniqueness: the map already carries 2 duplicate Grafton Optical
    # division entries (found 30/08, both agreeing on the same hub, so nothing is
    # published twice into different categories). Assert that THIS run adds no
    # new collision, rather than failing on one that was already there.
    dup_before = len(before) - len({_key(e) for e in before})
    dup_after = len(entries) - len({_key(e) for e in entries})
    assert dup_after == dup_before, \
        "this run would add %d duplicate pair(s) — refusing to write" % (
            dup_after - dup_before)

    doc["entries"] = entries
    doc["counts"]["pairs"] = len(entries)
    doc["counts"]["mapped"] = sum(1 for e in entries if e.get("hub"))
    doc["counts"]["notTaxonomy"] = sum(1 for e in entries if e.get("notTaxonomy"))
    doc["counts"]["products"] = sum(e["products"] for e in entries)
    doc["counts"]["productsMapped"] = sum(e["products"] for e in entries if e.get("hub"))

    print("\nmap would be: %d pairs, %d mapped, %d products."
          % (doc["counts"]["pairs"], doc["counts"]["mapped"], doc["counts"]["products"]))
    if apply_it:
        json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
        print("written to %s — the new pairs are unmapped and need judging." % MAP)
    else:
        print("(report only — pass --apply to write)")


if __name__ == "__main__":
    sys.exit(main() or 0)
