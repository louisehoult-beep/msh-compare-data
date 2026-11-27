#!/usr/bin/env python3
"""One-off detail tidy, framework-coverage batch 27/11/2026, CT Scanners and
Associated Options and Related Services.

NHS Supply Chain's launch brief for this framework names "Philips Electronics UK
Limited". philips.co.uk's own terms of use say the site is offered by Philips
Electronics UK Limited (read 27/11/2026). Ten CT scanner and CT simulator
products were already mapped on 13/11/2026 (_seed_philips_ct_overrides_1113.py)
but stayed HELD because no product page had been read, so no source carried them
(^o657). CT software, viewers, services and accessories stay HELD.

Sources are each product's own page, read 27/11/2026 by
crawl_supplier_product_detail.py (--product-path product, with the URL list from
the healthcare products sitemap named in robots.txt placed in sitemap-cache/,
because the script only reads /sitemap.xml). The heuristic read repeats the page
title and mixes other products' text into the feature list, so rows are trimmed
to the page's own opening text and features are dropped. No wording is added.

Run once: python3 scripts/_map_philips_ct_1127.py
"""
import json
import re

DETAIL = "data/supplier-product-detail.json"
SUPPLIER = "Philips"

# product name -> where the page's own prose begins
PRODUCTS = {
    "Incisive Ct Ct Scanner": "Incisive CT helps you meet",
    "Ct 5300 Hc728285 Ct Scanner": "Philips CT 5300 is intelligence",
    "Philips Ct 3500 Hc728134 Computed Tomography Scanner": "Philips CT 3500 lets you",
    "Rembra 728383 Ct Scanner": "Designed for the ED and beyond",
    "Spectral Ct 7500 Philips All New Spectral Detector Ct 750": "Philips Spectral CT 7500 offers",
    "Spectral Ct 7500 Rt 728343 Ct Simulator": "Targeting with spectral certainty",
    "Rembra Rt 728381 Ct Simulator": "When you can target tumors",
    "Verida Spectral Detector Ct Scanner": "Smart. Simple. Spectral.",
    "Areta Rt 728382 Ct Simulator": "When you can target tumors",
    "Ct 6000 Ict Refurbished Ct Scanner": "With advanced vascular imaging",
}
BOILER = re.compile(r"(For all support resources|Whitepaper |See all )")

detail = json.load(open(DETAIL))
rows = {v["product"]: v for v in detail["products"].values() if v["supplier"] == SUPPLIER}
missing = [n for n in PRODUCTS if n not in rows]
if missing:
    raise SystemExit("capture does not match the 27/11 read, stopping: missing %s" % missing)

for name, start in PRODUCTS.items():
    row = rows[name]
    desc = re.sub(r"[​‌¹]|\[1\]|\*", "", row.get("description") or "")
    desc = re.sub(r"\s+", " ", desc)
    at = desc.find(start)
    if at < 0:
        raise SystemExit("opening text not found on %s, stopping" % name)
    desc = BOILER.split(desc[at:])[0].strip()
    if len(desc) > 600:
        cut = desc[:600]
        desc = cut[:cut.rfind(". ") + 1] if ". " in cut else cut[:cut.rfind(" ")]
    row["description"] = desc
    row["features"] = None

with open(DETAIL, "w") as f:
    json.dump(detail, f, ensure_ascii=False, indent=1)
print("trimmed %d detail rows" % len(PRODUCTS))
