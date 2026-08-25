#!/usr/bin/env python3
"""
seed_differentiator_map.py — build the worklist that stands between the crawled
product data and a working Differentiator.

The Differentiator compares products WITHIN a category. Every product the Hub
holds already carries its manufacturer's own filing (a division, and for 41% of
them a finer category), because that is what the site crawler reads. What no
product outside GBUK carries is the Hub category it belongs to, and that is the
only thing missing:

    manufacturer's own division/category  ->  Hub speciality : type

There are 15,068 products and 1,834 distinct (supplier, division) pairs, so the
decision is made 1,834 times, not 15,068. This script writes those pairs out as
a worklist, biggest first, and marks the ones that are not taxonomy at all.

A mapping is a judgement, so it is recorded rather than guessed: each entry
carries the manufacturer's own string as its evidence, and nothing publishes
until a human or a sourced rule has filled in `hub`. Fuzzy string matching is
never used to fill one in — that is how "Bunzl Healthcare" became a catering
supplier.

Re-running is safe: existing decisions are preserved, only new pairs are added.
"""
import json, os, re, collections, sys

MAP = "data/differentiator-category-map.json"

# Labels a crawler picks up from site navigation that are not a product taxonomy.
# A pair marked notTaxonomy is not a mapping question — it means the crawl read
# the wrong element for that supplier and the fix is in the crawler, not here.
NOT_TAXONOMY = {
    "uncategorized", "uncategorised", "brands", "catalog", "catalogue", "sectors",
    "full store", "products", "product type", "products detail", "all products",
    "shop", "store", "home", "categories", "category", "range", "ranges",
    "our products", "product range", "browse", "all", "other", "misc",
    "miscellaneous", "general", "new", "featured", "clearance", "offers",
}


def main():
    sup = json.load(open("data/supplier-products.json"))["suppliers"]
    vocab = json.load(open("data/compare-suppliers.json"))["specialities"]

    pairs = collections.Counter()
    examples = collections.defaultdict(list)
    cats = collections.defaultdict(collections.Counter)
    for co, rec in sup.items():
        for p in rec.get("products") or []:
            key = (co, p.get("division") or "")
            pairs[key] += 1
            if len(examples[key]) < 4:
                examples[key].append(p.get("n") or "")
            if p.get("category"):
                cats[key][p["category"]] += 1

    prev = {}
    if os.path.exists(MAP):
        old = json.load(open(MAP))
        prev = {(e["supplier"], e["division"]): e for e in old.get("entries", [])}

    entries, kept, added = [], 0, 0
    for (co, div), n in pairs.most_common():
        was = prev.get((co, div))
        if was and was.get("hub"):
            kept += 1
            entries.append(was)
            continue
        added += 0 if was else 1
        entries.append({
            "supplier": co,
            "division": div,
            "products": n,
            "categories": [c for c, _ in cats[(co, div)].most_common(12)],
            "examples": examples[(co, div)],
            "hub": (was or {}).get("hub"),
            "notTaxonomy": (div or "").strip().lower() in NOT_TAXONOMY,
            "evidence": "the supplier's own site filing, read by "
                        "scripts/crawl_supplier_site.py",
        })

    doc = {
        "_notice": "GENERATED WORKLIST. Fill in `hub` only; everything else is rebuilt.",
        "rule": "A product's Hub category comes from its manufacturer's own filing, "
                "mapped once per (supplier, division) and recorded here with that "
                "filing as the evidence. `hub` is \"<speciality>:<type>\" using the "
                "vocabulary in data/compare-suppliers.json, which verify.py already "
                "gates. A pair with no mapping publishes nothing: an uncategorised "
                "product is held out of the Differentiator, never guessed into a "
                "category, because a product compared against the wrong category is "
                "worse than a product missing from the table. LOU'S RULE, 25/08/2026: "
                "`hub` may be a LIST of categories instead of one, when the division's "
                "OWN evidence genuinely names products from several at once — do not "
                "pick a single category for a division that spans more than one, put "
                "it in all of them. This is still not licence to guess: a division "
                "with no clear evidence for any category is still left unmapped. See "
                "data/differentiator-map-parts/README.md.",
        "vocabulary": {s: (v.get("types") or {}) for s, v in vocab.items()},
        "counts": {
            "pairs": len(entries),
            "mapped": sum(1 for e in entries if e.get("hub")),
            "notTaxonomy": sum(1 for e in entries if e.get("notTaxonomy")),
            "products": sum(pairs.values()),
            "productsMapped": sum(e["products"] for e in entries if e.get("hub")),
        },
        "entries": entries,
    }
    json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
    c = doc["counts"]
    print("%s: %d pairs (%d mapped, %d not taxonomy), %d products, %d categorised"
          % (MAP, c["pairs"], c["mapped"], c["notTaxonomy"], c["products"],
             c["productsMapped"]))
    print("  kept %d existing decisions, added %d new pairs" % (kept, added))


if __name__ == "__main__":
    main()
