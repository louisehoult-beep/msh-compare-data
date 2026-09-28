"""One-off, 28/09/2026: remove or correct the crawl junk found during the wound
dossier rebuild (08413ef; "Still open" item 3 in Cowork-OS/02-Elevate-and-Thrive/
Process flows for all brands/nhssc-term-product-override-and-hartmann-fixes-
2026-09-28.md). The crawlers themselves were fixed in the same commit
(crawl_supplier_site.UUID_RE / DOWNLOAD_LEAF_WORDS / TAXONOMY_INDEX_LEAVES /
"nice-guidance", crawl_supplier_product_detail._TAG_END / looks_like_site_chrome);
this applies the same rules to what those crawlers already stored.

Targeted, not a wholesale re-crawl: a live re-crawl of convatec.com on 28/09
returned a restructured range (divisions collapsed, US-market items added), which
is a separate review, not a junk fix. Every change below was checked against the
live supplier page on 28/09/2026.

supplier-products.json
  Convatec  UUID rows: named from the product page's own <h1> (en-gb sitemap-
            Product.xml / sitemap-Page.xml read 28/09) where it answers; the 25
            whose id is no longer in the en-gb sitemap are dropped (all 25 were
            held, none published). "Cure Dextra® Closed System" duplicates the
            existing "Cure Dextra Closed System" row, so its UUID row is dropped.
            "Product Names" (continence + stoma facet index pages) dropped.
  L&R       "Nice Guidance" dropped (h1 "Debrisoft recommended by NICE" — an
            evidence page); "Debrisoft" added (Woundcare), the product the prefix
            test had dropped as a category page because nice-guidance nests under
            it; "Lomutell Pro" renamed "Lomatuell Pro" (the page's own h1 is
            "Lomatuell® Pro"; only L&R's slug misspells it).
  Mölnlycke 4 brochure/catalogue download pages dropped.

supplier-product-detail.json
  Matching records dropped or re-keyed; every Convatec record whose description
  is the site header ("False /oidc-signin/..." language picker) re-read with the
  fixed parser — and, found while doing so, the 685 Steris records whose
  description was steris.com's menu and region picker (no <main> on that site).
  A re-read is a parser correction, not a supplier change, so it
  never sets changedSince. A page that no longer answers keeps no description.

Run once from the repo root, then rebuild the Differentiator.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl_supplier_site as cs                    # noqa: E402
import crawl_supplier_product_detail as d           # noqa: E402

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"
CV = "Convatec"
LR = "L&R Medical / Activa (Lohmann & Rauscher)"
MOL = "Mölnlycke"

# uuid -> (name from the page's own <h1>, en-gb URL), read 28/09/2026.
CV_NAMED = {
    "8b817add-f70b-42b1-bb95-d1ada7fe6a45": "AQUACEL® Foam Pro",
    "1b845cb1-2f05-476d-bc85-e40feb9bb7a2": "AQUACEL® Ribbon Dressing with Strengthening Fiber",
    "43d27ee2-5527-4858-a3eb-9c640dafe295": "ConvaFoam™ Border",
    "9de6e478-b265-4725-a1ad-09201d999866": "ConvaFoam™ Non-adhesive",
    "5fa8b340-af6f-414b-a905-31482098b026": "ConvaFoam™ Silicone",
    "c5d76c88-c089-4c45-b1b1-389b7d909087": "Cure Ultra® Male",
    "2c203995-7dcc-4534-83bc-4bc633d72b1a": "Esteem Body™ Soft Convex One-Piece Closed-end Pouch - Clear",
    "ea1f583b-7598-4871-9cfc-0e1b67d58074": "Esteem Body™ Soft Convex One-Piece Closed-end Pouch - with window",
    "5565d69e-59cd-4d34-90b7-0b863e756fda": "Esteem Body™ Soft Convex One-Piece Drainable Pouch - Clear",
    "db68c1b9-8b7e-464a-a131-2c2800880732": "Esteem Body™ Soft Convex One-Piece Drainable Pouch - with window",
    "0f344f1e-bbc3-4a4b-a3a6-35228cccaf87": "Esteem Body™ Soft Convex One-Piece Urostomy Pouch - with window",
    "5c48c2d4-f1c3-4d3a-a116-6d13406b285e": "Esteem Body™ Soft Convex One-Piece Urostomy Pouch - Clear",
    "998b651b-8834-4bc1-9a10-dd2ca7f27d86": "Esteem® + One-Piece Drainable Pouch",
    "2009de65-25e9-4411-be7f-515254b7df81": "Natura® Two Piece High Output Pouch",
    "6d8d004c-5df9-40b8-bd70-2ac2311f2807": "Natura™ Durahesive™ Mouldable Skin Barrier with Accordion Flange",
    "baf67bb8-6217-4d6a-9fbc-f6d96f4318e7": "Neria™ Soft – infusion set",
}
# Named, but already in the range under its own name ("Cure Dextra Closed System").
CV_DUPLICATE = {"675b3c46-c708-444f-a932-7d4d22c5cd3f"}

DROP_RANGE = {
    CV: {"Product Names"},
    LR: {"Nice Guidance"},
    MOL: {"Download Ons Wondassortimentsboekje",
          "Telechargez Le Livret D Assortiment Soins Des Plaies",
          "Productcataloog Downloaden", "Telecharger Catalogue Produit"},
}
RENAME_RANGE = {LR: {"Lomutell Pro": "Lomatuell Pro"}}
ADD_RANGE = {LR: [{"n": "Debrisoft", "division": "Woundcare", "category": ""}]}

DROP_DETAIL = {
    CV + "|product names", LR + "|nice guidance", LR + "|lomutell pro",
    MOL + "|download ons wondassortimentsboekje",
    MOL + "|telechargez le livret d assortiment soins des plaies",
    MOL + "|productcataloog downloaden", MOL + "|telecharger catalogue produit",
}


def uuid_of(name):
    s = re.sub(r"\s+", "-", name.strip()).lower()
    return s if cs.is_uuid_slug(s) else None


def recount(rec):
    counts = {}
    for p in rec["products"]:
        counts[p["division"]] = counts.get(p["division"], 0) + 1
    rec["divisions"] = [{"name": k, "products": v}
                        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


def fix_range(sp, log):
    for co in (CV, LR, MOL):
        rec = sp[co]
        kept = []
        for p in rec["products"]:
            n = p["n"]
            u = uuid_of(n) if co == CV else None
            if u:
                if u in CV_NAMED:
                    log.append("range %s: %r -> %r" % (co, n, CV_NAMED[u]))
                    p = dict(p, n=CV_NAMED[u])
                else:
                    log.append("range %s: dropped %r (%s)" % (
                        co, n, "duplicates 'Cure Dextra Closed System'" if u in CV_DUPLICATE
                        else "id not in the en-gb sitemap on 28/09; no name to read"))
                    continue
            elif n in DROP_RANGE.get(co, ()):
                log.append("range %s: dropped %r" % (co, n))
                continue
            elif n in RENAME_RANGE.get(co, {}):
                log.append("range %s: %r -> %r" % (co, n, RENAME_RANGE[co][n]))
                p = dict(p, n=RENAME_RANGE[co][n])
            kept.append(p)
        have = {(p["division"], p["n"]) for p in kept}
        for p in ADD_RANGE.get(co, []):
            if (p["division"], p["n"]) not in have:
                kept.append(dict(p))
                log.append("range %s: added %r (%s)" % (co, p["n"], p["division"]))
        rec["products"] = kept
        recount(rec)


def reread(store, key, name, url, log, supplier=CV):
    """Re-read one page with the fixed parser; never raise a change flag."""
    old = store.get(key) or {}
    rec, why = d.page_product_detail(url)
    if rec:
        d.record_capture(store, supplier, name, rec)
        new = store[supplier + "|" + d.nk(name)]
        new.pop("changedSince", None)
        if old.get("changedSince"):
            new["changedSince"] = old["changedSince"]
        log.append("detail %s: re-read %s" % (name, url))
    else:
        # Page gone or refused: keep the record's link and image, drop the header text.
        kept = dict(old, product=name, description="", features=[])
        store.pop(key, None)
        store[supplier + "|" + d.nk(name)] = kept
        log.append("detail %s: re-read refused (%s) — description and features cleared"
                   % (name, why))
    time.sleep(0.5)


def d_key(name):
    return CV + "|" + d.nk(name)


def fix_detail(store, log):
    for k in sorted(DROP_DETAIL):
        if store.pop(k, None) is not None:
            log.append("detail: dropped %s" % k)
    for k in list(store):
        v = store.get(k)
        if not v:
            continue
        if v.get("supplier") != CV:
            # Same shape, other suppliers: steris.com's mega-menu and region
            # picker, read as the description of 685 products because the site
            # has no <main> (see _MAIN_MARKER in crawl_supplier_product_detail.py).
            if (d.looks_like_site_chrome(v.get("description") or "")
                    or (v["supplier"] == "Steris" and "*Required" in (v.get("description") or ""))):
                reread(store, k, v["product"], v["sourceUrl"], log, v["supplier"])
            continue
        u = uuid_of(v.get("product") or "")
        if u:
            store.pop(k)
            if u in CV_NAMED:
                name = CV_NAMED[u]
                existing = store.get(d_key(name))
                if existing:
                    # ConvaFoam Border: a hand-captured record (with specs) for the
                    # same page already exists under the real name — keep that one.
                    log.append("detail: dropped %s (page already held as %r)"
                               % (k, existing.get("product")))
                    if d.looks_like_site_chrome(existing.get("description") or ""):
                        reread(store, d_key(name), name, existing["sourceUrl"], log)
                    continue
                store[d_key(name)] = dict(v, product=name)
                reread(store, d_key(name), name, v["sourceUrl"], log)
            else:
                log.append("detail: dropped %s (no range row)" % k)
        elif (d.looks_like_site_chrome(v.get("description") or "")
              or (v.get("description") or "").startswith("Search Products by Category")
              or "*Required" in (v.get("description") or "")):
            # The last two: convatec.com's category search and sample-request form,
            # read inside <main> before strip_boilerplate learned to drop them.
            reread(store, k, v["product"], v["sourceUrl"], log)
    # One page, one record for a renamed UUID product: the hand-captured record
    # (with specs) already held for that page wins over the re-keyed crawl copy.
    by_url = {}
    for k, v in store.items():
        if v.get("supplier") == CV:
            by_url.setdefault((v.get("sourceUrl") or "").rstrip("/"), []).append(k)
    renamed = {d_key(n) for n in CV_NAMED.values()}
    for url, keys in by_url.items():
        curated = [k for k in keys if store[k].get("specs")]
        if curated:
            for k in keys:
                if k in renamed and not store[k].get("specs"):
                    store.pop(k)
                    log.append("detail: dropped %s (page already held with specs as %r)"
                               % (k, store[curated[0]].get("product")))


def main():
    sp_doc = json.load(open(RANGE))
    det_doc = json.load(open(DETAIL))
    log = []
    fix_range(sp_doc["suppliers"], log)
    fix_detail(det_doc["products"], log)
    left = [k for k, v in det_doc["products"].items()
            if d.looks_like_site_chrome(v.get("description") or "")]
    for line in log:
        print(line)
    print("\n%d change(s); %d record(s) still carry site chrome: %s"
          % (len(log), len(left), left[:5]))
    for path, doc in ((RANGE, sp_doc), (DETAIL, det_doc)):
        with open(path, "w") as f:
            f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
