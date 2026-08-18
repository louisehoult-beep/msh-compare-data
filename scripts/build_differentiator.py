#!/usr/bin/env python3
"""
build_differentiator.py — one product record, built from every source that
describes it, filed in exactly one comparable category.

WHY BOTH SOURCES. NHS Supply Chain tells you what a trust can actually order:
the NPC code, the pack, whether it is still listed. It does not tell you what
distinguishes one product from another — the catalogue description is a line of
procurement shorthand. The manufacturer's own site carries the detail a rep
needs to sell against a competitor: the features, the materials, the claims. A
Differentiator built on either source alone is either unbuyable or undifferen-
tiated, so a product record here holds both, each with its own URL and the date
it was read, and neither is allowed to stand in for the other.

CATEGORY LOCK. Every published product carries exactly one `cat`, of the form
"<speciality>:<type>", from the vocabulary in data/compare-suppliers.json that
verify.py already gates. The comparison UI may only ever put two products side
by side when their `cat` is identical. That is not a UI nicety: comparing a
midline against a drainage bag produces a table where every row is "n/a", which
reads to a member as a product that fails on every measure.

A product whose category is not known is HELD, not guessed — it goes to
`held`, is counted, and appears nowhere in the comparison. Root rule 14: an
honest empty state, never a loosened threshold.

Usage:  python3 scripts/build_differentiator.py
Writes: data/differentiator.json
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "..", "company-aliases"))

OUT = "data/differentiator.json"


def load(p):
    with open(p) as f:
        return json.load(f)


JOINERS = {"and", "or", "the", "for"}


def norm(s):
    import re as _re
    s = _re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return " ".join(s.split())


def tokens(s):
    """Normalised word set, joiners dropped. Used to match a manufacturer's own
    category against a gated type label where the two say the same thing in a
    different order ('Slings and slide sheets' vs 'Slide sheets and slings').
    Equality of the SET is still exact matching, not similarity."""
    return frozenset(w for w in norm(s).split() if w not in JOINERS)


def main():
    own = load("data/supplier-products.json")["suppliers"]
    detail = load("data/supplier-product-detail.json")["products"]
    nhssc = load("data/nhssc-cache.json")
    vocab = load("data/compare-suppliers.json")["specialities"]
    cmap = load("data/differentiator-category-map.json") if \
        os.path.exists("data/differentiator-category-map.json") else {"entries": []}
    seed = {s["name"]: s for s in load("data/supplier-seed.json")["suppliers"]}
    lmap = load("data/speciality-label-map.json") if \
        os.path.exists("data/speciality-label-map.json") else {"entries": []}
    label_slug = {e["label"]: e["slugs"][0]
                  for e in lmap.get("entries", [])
                  if e.get("slugs") and len(e["slugs"]) == 1}

    # A supplier recorded as selling into exactly ONE speciality files its products
    # to that speciality. The rule is stated, and its evidence is the supplier's own
    # seed record. A supplier whose labels reach two or more specialities is NOT
    # pre-filled: guessing which of them a given product belongs to is precisely the
    # error the category lock exists to prevent.
    sole = {}
    for co in own:
        labs = (seed.get(co) or {}).get("specialities") or []
        slugs = {label_slug[l] for l in labs if l in label_slug}
        if len(slugs) == 1 and len(slugs) == len([l for l in labs if l in label_slug]) \
                and all(l in label_slug for l in labs):
            sole[co] = slugs.pop()

    # (supplier, division) -> "speciality:type", the recorded human decision.
    mapped = {(e["supplier"], e["division"]): e["hub"]
              for e in cmap.get("entries", []) if e.get("hub")}

    # Every legal category, so a mapping cannot invent one.
    legal = {"%s:%s" % (s, t) for s, v in vocab.items()
             for t in (v.get("types") or {})}

    # NHSSC detail, keyed by (supplier, product name). The cache is keyed by the
    # search term used, and each entry records the Hub supplier it belongs to.
    # THE TWO SOURCES ARE AT DIFFERENT GRANULARITIES, and joining them on an
    # equal product name returns nothing at all. NHS Supply Chain's cache is keyed
    # by the RANGE a rep would search for — "Nutricare", "Leaderflex", "Prolystica"
    # — while the site crawl holds individual product pages. So the join is made at
    # range level and only on a WHOLE-PHRASE match: the NHSSC range name has to
    # appear in the manufacturer's product name bounded by word breaks, under the
    # same supplier. "Multicath" matches "Multicath Expert Central Venous Catheter";
    # it does not match on a shared word or a prefix. A range shorter than four
    # characters is never matched on, because short tokens collide.
    nh_brands = {}
    for term, rec in (nhssc.get("products") or {}).items():
        co = rec.get("supplier")
        if not co:
            continue
        nh_brands.setdefault(norm(co), {}).setdefault(norm(term), []).extend(
            rec.get("items") or [])

    nh = {}
    for term, rec in (nhssc.get("products") or {}).items():
        co = rec.get("supplier")
        for it in rec.get("items") or []:
            nh.setdefault((norm(co), norm(it.get("name"))), []).append({
                "npc": it.get("npc"), "mpc": it.get("mpc"),
                "desc": it.get("desc"), "pack": it.get("pack"),
                "status": it.get("status"), "nhsscName": it.get("name"),
                "nhsscSupplier": it.get("supplier"), "term": term,
            })

    # Own-site per-product detail, keyed the same way.
    det = {}
    for rec in detail.values():
        det[(norm(rec.get("supplier")), norm(rec.get("product")))] = rec

    products, held = [], []
    hcount = collections.Counter()
    for co, rec in own.items():
        domain = rec.get("domain")
        for p in rec.get("products") or []:
            name = p.get("n")
            if not name:
                continue
            div = p.get("division") or ""
            cat = mapped.get((co, div))
            # GBUK-style records already assert the speciality on the product
            # itself. Where they do AND the manufacturer's own category is one of
            # that speciality's gated types, the pair needs no separate decision:
            # the data already says it. Anything less certain is held.
            spec = p.get("s") or sole.get(co)
            if not cat and spec and p.get("category"):
                types = (vocab.get(spec, {}).get("types") or {})
                want, wantset = norm(p["category"]), tokens(p["category"])
                for key, label in types.items():
                    if norm(label) == want or (wantset and tokens(label) == wantset):
                        cat = "%s:%s" % (spec, key)
                        break

            k = (norm(co), norm(name))
            d = det.get(k)
            sources = []
            if d:
                sources.append({"kind": "manufacturer", "url": d.get("sourceUrl"),
                                "readOn": d.get("capturedDate"), "owner": co})
            n_items = list(nh.get(k) or [])
            matched_range = None
            if not n_items:
                nname = norm(name)
                for brand, items in (nh_brands.get(norm(co)) or {}).items():
                    if len(brand) < 4:
                        continue
                    if re.search(r"\b" + re.escape(brand) + r"\b", nname):
                        matched_range = brand
                        n_items = [{"npc": it.get("npc"), "mpc": it.get("mpc"),
                                    "desc": it.get("desc"), "pack": it.get("pack"),
                                    "status": it.get("status"),
                                    "nhsscName": it.get("name"),
                                    "nhsscSupplier": it.get("supplier"),
                                    "term": brand,
                                    "matchedOn": "range name, whole phrase"}
                                   for it in items]
                        break
            for it in n_items:
                sources.append({"kind": "nhssc", "npc": it["npc"],
                                "owner": "NHS Supply Chain",
                                "url": "https://my.supplychain.nhs.uk/catalogue/search/0?query=%s"
                                       % (it["npc"] or "")})

            row = {
                "supplier": co, "name": name, "domain": domain,
                "division": div, "mfrCategory": p.get("category"),
                "cat": cat,
                "detail": ({"description": d.get("description"),
                            "features": d.get("features"),
                            "image": d.get("image")} if d else None),
                "nhssc": n_items or None,
                "nhsscRange": matched_range,
                "sources": sources,
            }
            if not cat:
                hcount[(co, div)] += 1
                held.append({"supplier": co, "name": name, "division": div,
                             "why": "no recorded category mapping for this "
                                    "supplier's own division"})
                continue
            if cat not in legal:
                held.append({"supplier": co, "name": name, "division": div,
                             "why": "mapping names a category that is not in the "
                                    "gated vocabulary: %s" % cat})
                continue
            if not sources:
                held.append({"supplier": co, "name": name, "division": div,
                             "why": "no source carries this product — neither the "
                                    "manufacturer's own page nor NHSSC"})
                continue
            products.append(row)

    bycat = collections.Counter(r["cat"] for r in products)
    comparable = {c: n for c, n in bycat.items() if n >= 2}

    doc = {
        "_notice": "GENERATED. Do not edit by hand — run "
                   "scripts/build_differentiator.py.",
        "rule": "A product is published only when it has a recorded category from "
                "the gated vocabulary AND at least one source that carries it. "
                "Comparison is locked to a single category: two products may be "
                "put side by side only where their `cat` is identical.",
        "sources": {
            "manufacturer": "each supplier's own product pages, read by "
                            "scripts/crawl_supplier_product_detail.py",
            "nhssc": "NHS Supply Chain public catalogue, cached by "
                     "scripts/refresh_nhssc_cache.py",
        },
        "counts": {
            "published": len(products),
            "held": len(held),
            "categories": len(bycat),
            "comparableCategories": len(comparable),
            "withBothSources": sum(1 for r in products
                                   if r["detail"] and r["nhssc"]),
            "manufacturerOnly": sum(1 for r in products
                                    if r["detail"] and not r["nhssc"]),
            "nhsscOnly": sum(1 for r in products
                             if r["nhssc"] and not r["detail"]),
        },
        "byCategory": dict(sorted(bycat.items())),
        "products": products,
        "held": held[:2000],
        "heldTopDivisions": [{"supplier": c, "division": d, "products": n}
                             for (c, d), n in hcount.most_common(40)],
    }
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    c = doc["counts"]
    print("%s: %d published in %d categories (%d comparable), %d held"
          % (OUT, c["published"], c["categories"], c["comparableCategories"],
             c["held"]))
    print("  sources: both %d | manufacturer only %d | NHSSC only %d"
          % (c["withBothSources"], c["manufacturerOnly"], c["nhsscOnly"]))


if __name__ == "__main__":
    main()
