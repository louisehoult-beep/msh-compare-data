#!/usr/bin/env python3
"""One-off: fill the 16 rehab:therapy decisions in
data/differentiator-map-parts/Medfac UK Ltd.json onto their existing (null-hub)
pairs in data/differentiator-category-map.json (framework-coverage batch,
20/11/2026, Physiotherapy and Occupational Therapy framework).

merge_differentiator_parts.py --apply refuses while 245 unrelated pre-existing
part refusals stand, so -- as _apply_amplivox_map_1119.py did -- this touches
only Medfac UK Ltd's pairs and adjusts the counts by the delta. It only fills a
hub that is currently null, the same rule the merge applies."""
import json

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/Medfac UK Ltd.json"
CO = "Medfac UK Ltd"

doc = json.load(open(MAP))
decisions = {d["division"]: d for d in json.load(open(PART))["decisions"]}
filled = pm = 0
for e in doc["entries"]:
    if e["supplier"] != CO or e.get("hub") or e.get("notTaxonomy"):
        continue
    d = decisions.get(e["division"])
    if not d:
        continue
    e["hub"] = d["hub"]
    e["why"] = d["why"]
    e["decidedIn"] = "Medfac UK Ltd.json"
    filled += 1
    pm += e["products"]
doc["counts"]["mapped"] += filled
doc["counts"]["productsMapped"] += pm
open(MAP, "w").write(json.dumps(doc, ensure_ascii=False))
print("filled %d pairs, %d products mapped" % (filled, pm))
