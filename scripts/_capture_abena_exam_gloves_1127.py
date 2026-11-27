#!/usr/bin/env python3
"""One-off capture, framework-coverage batch 27/11/2026, Examination Gloves:
Abena UK Limited.

Identity: abena.co.uk prints "ABENA UK LTD ... Registered number: 03750590" in
its footer, the number already proved on the seed record. NHS Supply Chain's
brief names the company on Examination Gloves.

Range: the 10/10/2026 sitemap capture kept only the Gloves category labels. The
company's sitemap also carries individual examination glove pages (filed under
/industry/production/on-the-floor/). The 12 pages below were each read on
27/11/2026; each calls itself an examination glove and states CE Class I medical
device. robots.txt disallows /NHS/, /api, /search, /sitecore and /checkout; none
of these pages sits under them. Name = the page title without the pack size.
Description = the page's own Product Description, nothing added. Mapped one
product at a time by the material in the product's own name. Other glove pages
(household, work, textile, other disposable) are not added.

Each row carries manualCapture so a re-crawl keeps it.

Run once from the repo root: python3 scripts/_capture_abena_exam_gloves_1127.py
"""
import html
import json
import re
import time
import urllib.request

SUPPLIER = "Abena UK Limited"
TODAY = "2026-11-27"
BASE = "https://www.abena.co.uk/industry/production/on-the-floor/"
PAGES = [
    "examination-gloves-abena-classic-protect/p-9200-pm015775/v-290438",
    "examination-gloves-abena-classic-sensitive/p-9200-pm015769/v-290482",
    "examination-gloves-abena-classic-sensitive/p-9200-pm015772/v-290741",
    "examination-gloves-abena-classic-sensitive/p-9200-pm022967/v-290711",
    "examination-gloves-abena-classic-sensitive/p-9200-pm022969/v-290721",
    "examination-gloves-abena-classic-sensitive/p-9200-pm022970/v-290731",
    "examination-gloves-abena-classic/p-9200-pm015747/v-4424",
    "examination-gloves-abena-classic/p-9200-pm015815/v-438199",
    "examination-gloves-abena-classic/p-9200-pm027436/v-1999905273",
    "examination-gloves-abena-excellent/p-9200-pm015750/v-290254",
    "examination-gloves-abena-excellent/p-9200-pm015762/v-3958",
    "long-examination-gloves-abena-classic/p-9200-pm032521/v-1999917575",
]
HUBS = {"nitrile": "infection:nitrile", "vinyl": "infection:vinyl", "latex": "infection:latex"}


def text(raw):
    raw = re.sub(r"(?s)<(script|style).*?</\1>", "", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


rows = []
for path in PAGES:
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; catalogue-reader)"})
    raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
    t = text(raw)
    assert "Registered number: 03750590" in t, "company number missing: " + url
    assert "CE Class (Medical Devices) Class I" in t, "not stated Class I: " + url
    title = html.unescape(re.search(r"<title>(.*?)</title>", raw, re.S).group(1)).strip()
    title = re.sub(r"\s*-\s*ABENA UK\s*$", "", title)
    name = re.sub(r",\s*(XS|S|M|L|XL|XXL),", ",", title)
    name = re.sub(r"Powder-free", "powder-free", name)
    assert name != title and "xamination gloves" in name, "unexpected title: " + title
    material = [m for m in HUBS if re.search(r"\b%s\b" % m, name)]
    assert len(material) == 1, "material not single: " + name
    a = t.index("Product Description", t.index("Description Product Description") ) + len("Product Description")
    b = t.index("Product Data", a)
    desc = re.split(r"\s+Instructions\b\s*$", t[a:b].strip())[0].strip()
    img = re.search(r'property="og:image"[^>]*content="([^"]+)"', raw)
    div = "Long examination gloves" if name.startswith("Long ") else "Examination gloves"
    rows.append({"name": name, "division": div, "hub": HUBS[material[0]], "material": material[0],
                 "url": url, "description": desc, "image": html.unescape(img.group(1)) if img else None})
    time.sleep(1)

assert len({r["name"] for r in rows}) == len(PAGES), "duplicate names"


def rewrite(path, mutate):
    raw = open(path, encoding="utf-8").read()
    doc = json.loads(raw)
    mutate(doc)
    kw = {"ensure_ascii": False}
    if raw.startswith('{\n  "'):
        kw["indent"] = 2
    elif raw.startswith('{\n "'):
        kw["indent"] = 1
    elif '": ' not in raw[:200]:
        kw["separators"] = (",", ":")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, **kw)
        if raw.endswith("\n"):
            f.write("\n")


def products(doc):
    rec = doc["suppliers"][SUPPLIER]
    have = {p["n"].lower() for p in rec["products"]}
    for r in rows:
        assert r["name"].lower() not in have, "already present: " + r["name"]
        rec["products"].append({"n": r["name"], "division": r["division"], "category": r["division"],
                                "manualCapture": {"url": r["url"], "readOn": TODAY}})
    for div in sorted({r["division"] for r in rows}):
        rec["divisions"].append({"name": div, "products": sum(r["division"] == div for r in rows)})
    rec["captureCaveat"] += (" %d examination glove products were added from their own product pages, "
                             "read 27/11/2026." % len(rows))


def detail(doc):
    for r in rows:
        doc["products"]["%s|%s" % (SUPPLIER, r["name"].lower())] = {
            "supplier": SUPPLIER, "product": r["name"], "sourceUrl": r["url"], "capturedDate": TODAY,
            "parsed": "heuristic", "description": r["description"], "features": None, "image": r["image"]}


def mapping(doc):
    entries = doc["entries"]
    evidence = "the supplier's own product pages on abena.co.uk, each read 27/11/2026"
    for div in sorted({r["division"] for r in rows}):
        mine = [r for r in rows if r["division"] == div]
        entries.append({"supplier": SUPPLIER, "division": div, "products": len(mine), "categories": [],
                        "examples": [r["name"] for r in mine][:4], "hub": None, "notTaxonomy": False,
                        "evidence": evidence})
    for r in rows:
        entries.append({"supplier": SUPPLIER, "division": r["name"], "products": 1, "categories": [],
                        "examples": [r["name"]], "hub": r["hub"], "notTaxonomy": False,
                        "kind": "product-override", "evidence": evidence,
                        "why": "the product's own name states an examination glove in %s "
                               "(mixed-division-mapping policy)" % r["material"]})
    doc["counts"]["pairs"] = len(entries)


rewrite("data/supplier-products.json", products)
rewrite("data/supplier-product-detail.json", detail)
rewrite("data/differentiator-category-map.json", mapping)
for r in rows:
    print(r["hub"], "|", r["name"], "|", r["description"][:90], "|", bool(r["image"]))
