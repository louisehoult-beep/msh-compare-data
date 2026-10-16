#!/usr/bin/env python3
"""Land the Sectra Limited re-crawl (^o635), 16/10/2026.

Names come from the page <title> (TITLE_NAMED_DOMAINS), not the tagline <h1>:
all 35 are product names. Usage: python3 scripts/_land_sectra_1016.py <capture.json>
Category map, checked against each product page's own breadcrumb on 16/10/2026:
- the 6 Orthopaedics product-overrides move from slug names to printed names, same hub category;
- the flat 'Uncategorised' digital:sw entry is recounted, and the site's own divisions
  (now read from the breadcrumbs) carry the same digital:sw mapping, Orthopaedics ortho:equip.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl_supplier_site as cs

NAME = "Sectra Limited"
NOTE = " Re-curated 16/10/2026 (^o635) to the name the product page's <title> prints, after the re-crawl replaced the URL-slug name."
REN = {"Sectra 3D Joint Replacement": "Sectra 3D Joint Replacement for orthopaedics",
       "Sectra 3D Trauma": "Sectra 3D Trauma",
       "Sectra 2D Planning System": "Sectra 2D Planning System for orthopaedics",
       "Sectra 3D Spine": "Sectra 3D Spine for orthopaedics",
       "Sectra Ima": "Sectra Implant Movement Analysis (Implant Movement Analysis) for orthopaedics",
       "Sectra Ctma": "Sectra CT-based Micromotion Analysis (CTMA) for orthopaedics"}
shaped, notes = cs.tidy_capture(json.load(open(sys.argv[1])))
prod = json.load(open(cs.OUT, encoding="utf-8"))
for k in ("aliases", "companyNo", "notSold", "tubesNote", "domainWarning"):
    if k in (prod["suppliers"].get(NAME) or {}):
        shaped[k] = prod["suppliers"][NAME][k]
prod["suppliers"][NAME] = shaped
cs.atomic_write_json(cs.OUT, prod)
names = {p["n"] for p in shaped["products"]}
bydiv = {}
for p in shaped["products"]:
    bydiv.setdefault(p["division"], []).append(p["n"])

MAP = "data/differentiator-category-map.json"
m = json.load(open(MAP, encoding="utf-8"))
out, flat = [], None
for e in m["entries"]:
    if e.get("supplier") != NAME:
        out.append(e); continue
    if e.get("kind") == "product-override":
        new = REN[e["division"]]
        assert new in names, new
        e["division"] = new; e["examples"] = [new]; e["evidence"] += NOTE
    elif e.get("division") == "Uncategorised":
        flat = e
        e["products"] = len(bydiv["Uncategorised"]); e["examples"] = bydiv["Uncategorised"][:4]
    out.append(e)
assert flat
for d, ps in bydiv.items():
    if d == "Uncategorised":
        continue
    ne = json.loads(json.dumps(flat))
    ne["division"] = d; ne["products"] = len(ps); ne["examples"] = ps[:4]
    ne["evidence"] = ("the supplier's own site filing: the division is the breadcrumb on each product page "
                      "(medical.sectra.com), read by scripts/crawl_supplier_site.py 16/10/2026.")
    if d == "Orthopaedics":
        ne["hub"] = "ortho:equip"
        ne["why"] = ("Sectra files these under its Orthopaedics solution area (breadcrumb read 16/10/2026): "
                     "pre-operative planning / implant-analysis software, as for its six product-overrides.")
    out.append(ne)
m["entries"] = out
from seed_format import write_like
write_like(MAP, m)
print(notes, {d: len(v) for d, v in bydiv.items()})
