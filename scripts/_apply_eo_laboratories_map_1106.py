#!/usr/bin/env python3
"""One-off: apply the E&O Laboratories category decisions directly to
data/differentiator-category-map.json (framework-coverage batch, 06/11/2026).

merge_differentiator_parts.py --apply refuses to write ANYTHING while any part
file anywhere has a problem, and 245 pre-existing refusals (Crest Medical Ltd's
two stale part files, unrelated to this run) block the whole merge. Rather than
touch Crest Medical Ltd's files -- a different supplier this run did not pick --
this applies only the 6 (E&O Laboratories, <division>) decisions already
reviewed in data/differentiator-map-parts/E&O Laboratories - framework-coverage-1106.json,
using the exact same write call merge_differentiator_parts.py uses
(json.dump(..., ensure_ascii=False, indent=1)) so the diff is scoped to this
supplier only."""
import json

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/E&O Laboratories - framework-coverage-1106.json"

doc = json.load(open(MAP))
part = json.load(open(PART))
co = part["supplier"]
decisions = {d["division"]: d for d in part["decisions"]}

applied = 0
for e in doc["entries"]:
    if e["supplier"] != co:
        continue
    d = decisions.get(e["division"])
    if not d or e.get("hub"):
        continue
    e["hub"] = d["hub"]
    e["why"] = d["why"]
    e["decidedIn"] = "E&O Laboratories - framework-coverage-1106.json"
    applied += 1

products = sum(e.get("products", 0) for e in doc["entries"] if e.get("hub"))
doc["counts"]["mapped"] = sum(1 for e in doc["entries"] if e.get("hub"))
doc["counts"]["productsMapped"] = products

json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("%d applied; map now %d of %d pairs mapped, covering %d products."
      % (applied, doc["counts"]["mapped"], len(doc["entries"]), products))
