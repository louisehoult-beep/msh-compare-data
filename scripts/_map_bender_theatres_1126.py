#!/usr/bin/env python3
"""One-off mapping, framework-coverage batch 26/11/2026, Operating Theatres
Equipment and Related Accessories and Services.

Bender UK Ltd is named on NHS Supply Chain's launch brief for this framework
(award captured 23/11/2026). Its own-site capture (bender-uk.com, 24/11/2026;
domain proved by registration number 03294339, recorded on the seed 14/08/2026)
had nothing mapped, so every product was HELD.

Policy mixed-division-mapping: the range is mostly electrical monitoring, so
only the theatre lines are mapped. Two divisions are theatre capital equipment
throughout (operating tables/trolleys, integrated theatre). Six further products
are mapped one at a time where the product's own name identifies theatre use.
HELD: examination lights (Q Flow 1, Q Flow 2, Merilux X1), battery backup
units, ICU and Contempo pendants, PACS consoles, CP9xx/CP305 indicators,
Visualisation, and the whole electrical monitoring range.

Sources are each product's own page, read 26/11/2026 by
crawl_supplier_product_detail.py. That heuristic read repeats the page title and
carries contact/consent boilerplate, so Bender's detail rows are trimmed here to
the page's own opening text and short bullet lines. No wording is added.

Run once: python3 scripts/_map_bender_theatres_1126.py
"""
import json
import re

MAP = "data/differentiator-category-map.json"
DETAIL = "data/supplier-product-detail.json"
SUPPLIER = "Bender UK Ltd"
TODAY = "2026-11-26"
HUB = "theatres:capital"
DECIDED = "framework-coverage-batch, 26/11/2026, Operating Theatres Equipment"

DIVISIONS = {
    "Operating Tables And Trolleys":
        "the division holds two operating tables and the Rapido trolley, which its own page calls a multi-functional operating table or trolley",
    "Integrated Theatre Solution For Advanced Hospitals":
        "the division's one product is the OpenOR integrated operating theatre system (OR integration)",
}
PRODUCTS = {
    "Q Flow": "its own page is headed Q-Flow Operating Theatre Lights",
    "Q Flow Mobile Operating Light": "named an operating light",
    "Operating Light Camera": "a camera fitted into Q-Flow operating light heads",
    "Solido Pendants For Operating Theatres": "named a theatre pendant",
    "Comtraxx Cp9 24 Glass Theatre Control Panel": "named a theatre control panel (OR integration)",
    "Theatre Control Panels": "named theatre control panels (OR integration)",
}

# Where each published page's own prose begins (the text before it is the title
# and bullet block the heuristic read ran together).
STARTS = {
    "Comtraxx Cp9 24 Glass Theatre Control Panel": "This innovative theatre control panel",
    "Theatre Control Panels": "Theatre or surgeons control panels",
    "Q Flow": "The award-winning Merivaara",
    "Q Flow Mobile Operating Light": "Q-Flow\u2122 Mobile is a portable",
    "Operating Light Camera": "To enable training",
    "Solido Pendants For Operating Theatres": "Merivaara offer a variety",
    "Rapido Hospital Trolley": "A wide range of surgical procedures",
    "Smarter Practico Operating Table": "The Smarter Practico\u2122 mobile",
    "Grand Promerix Operating Table": "Grand Promerix\u2122 mobile operating table",
    "Openor Integrated Theatre": "Merivaara OpenOR\u2122 is",
}

rng = json.load(open("data/supplier-products.json"))["suppliers"][SUPPLIER]["products"]
detail = json.load(open(DETAIL))
rows = {v["product"]: v for v in detail["products"].values() if v["supplier"] == SUPPLIER}

wanted = list(PRODUCTS) + [p["n"] for p in rng if p.get("division") in DIVISIONS]
missing = [n for n in wanted if n not in rows]
if missing or len(wanted) != 10:
    raise SystemExit("capture does not match the 26/11 read, stopping: %d wanted, missing %s"
                     % (len(wanted), missing))

BOILER = re.compile(r"(Questions\? Contact us|We need your consent|To find out more about our products)", re.I)
for name, row in rows.items():
    desc = BOILER.split(row.get("description") or "")[0].strip()
    if name in STARTS:
        at = desc.find(STARTS[name])
        if at < 0:
            raise SystemExit("opening text not found on %s, stopping" % name)
        desc = desc[at:]
    if len(desc) > 600:
        cut = desc[:600]
        desc = cut[:cut.rfind(". ") + 1] if ". " in cut else cut[:cut.rfind(" ")]
    feats = [f.strip() for f in (row.get("features") or [])[1:]
             if len(f.strip()) <= 160 and not BOILER.search(f)]
    row["description"] = desc
    row["features"] = list(dict.fromkeys(feats)) or None

cmap = json.load(open(MAP))
have = {(e.get("supplier"), e.get("division")) for e in cmap["entries"]}
added = 0


def add(division, names, why, kind=None):
    global added
    if (SUPPLIER, division) in have:
        return
    entry = {
        "supplier": SUPPLIER,
        "division": division,
        "products": len(names),
        "categories": [],
        "examples": names,
        "hub": HUB,
        "notTaxonomy": False,
        "evidence": ("Bender UK's own site, captured 24/11/2026 and each product page read "
                     "26/11/2026: %s" % ", ".join(rows[n]["sourceUrl"] for n in names)),
        "why": why + " -- 'Capital equipment (tables, lights & OR integration)'.",
        "decidedIn": DECIDED,
        "addedOn": TODAY,
    }
    if kind:
        entry["kind"] = kind
    cmap["entries"].append(entry)
    added += 1


for div, why in DIVISIONS.items():
    add(div, [p["n"] for p in rng if p.get("division") == div], why)
for name, why in PRODUCTS.items():
    add(name, [name], why, "product-override")

with open(MAP, "w") as f:
    json.dump(cmap, f, ensure_ascii=False)
with open(DETAIL, "w") as f:
    json.dump(detail, f, ensure_ascii=False, indent=1)
print("added %d map entries covering %d products; trimmed %d detail rows"
      % (added, len(wanted), len(rows)))
