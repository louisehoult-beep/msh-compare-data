#!/usr/bin/env python3
"""One-off: union Amplivox's 4 new (supplier, division) pairs onto
data/differentiator-category-map.json and fill the two decided in
data/differentiator-map-parts/Amplivox.json (framework-coverage batch,
19/11/2026, Audiological Diagnostics framework).

seed_differentiator_map.py refuses to run (it would destroy the nhssc-term
entries) and merge_differentiator_parts.py --apply refuses while 245 unrelated
pre-existing part refusals stand, so -- as _apply_eo_laboratories_map_1106.py
did -- this adds only Amplivox's pairs, in the seeder's own entry shape, and
adjusts the counts by the delta so the diff is scoped to this supplier.
Software (3) is left unmapped (held); Uncategorised (2: Spirometry, Vision
Testers) is notTaxonomy, as the seeder marks it."""
import collections, json

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/Amplivox.json"
CO = "Amplivox"
NOT_TAX = {"uncategorised", "uncategorized"}

doc = json.load(open(MAP))
sp = json.load(open("data/supplier-products.json"))
prods = sp.get("suppliers", sp)[CO]["products"]
decisions = {d["division"]: d for d in json.load(open(PART))["decisions"]}

have = {(e["supplier"], e["division"]) for e in doc["entries"]}
count = collections.Counter(p["division"] for p in prods)
examples = collections.defaultdict(list)
for p in prods:
    if len(examples[p["division"]]) < 4:
        examples[p["division"]].append(p["n"])

d_pairs = d_mapped = d_nt = d_prod = d_pmapped = 0
for div, n in count.most_common():
    if (CO, div) in have:
        continue
    e = {"supplier": CO, "division": div, "products": n, "categories": [],
         "examples": examples[div], "hub": None,
         "notTaxonomy": div.strip().lower() in NOT_TAX,
         "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py"}
    d = decisions.get(div)
    if d:
        e["hub"] = d["hub"]
        e["why"] = d["why"]
        e["decidedIn"] = "Amplivox.json"
        d_mapped += 1
        d_pmapped += n
    doc["entries"].append(e)
    d_pairs += 1
    d_prod += n
    d_nt += e["notTaxonomy"]

c = doc["counts"]
c["pairs"] += d_pairs
c["mapped"] += d_mapped
c["notTaxonomy"] += d_nt
c["products"] += d_prod
c["productsMapped"] += d_pmapped
open(MAP, "w").write(json.dumps(doc, ensure_ascii=False))
print("added %d pairs (%d mapped, %d products mapped)" % (d_pairs, d_mapped, d_pmapped))
