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
import json, os, sys, collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "..", "company-aliases"))

OUT = "data/differentiator.json"


def load(p):
    with open(p) as f:
        return json.load(f)


def norm(s):
    return " ".join((s or "").lower().split())


def main():
    own = load("data/supplier-products.json")["suppliers"]
    detail = load("data/supplier-product-detail.json")["products"]
    nhssc = load("data/nhssc-cache.json")
    vocab = load("data/compare-suppliers.json")["specialities"]
    cmap = load("data/differentiator-category-map.json") if \
        os.path.exists("data/differentiator-category-map.json") else {"entries": []}

    # (supplier, division) -> "speciality:type", the recorded human decision.
    mapped = {(e["supplier"], e["division"]): e["hub"]
              for e in cmap.get("entries", []) if e.get("hub")}

    # Every legal category, so a mapping cannot invent one.
    legal = {"%s:%s" % (s, t) for s, v in vocab.items()
             for t in (v.get("types") or {})}

    # NHSSC detail, keyed by (supplier, product name). The cache is keyed by the
    # search term used, and each entry records the Hub supplier it belongs to.
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
            if not cat and p.get("s") and p.get("category"):
                types = (vocab.get(p["s"], {}).get("types") or {})
                for key, label in types.items():
                    if norm(label) == norm(p["category"]):
                        cat = "%s:%s" % (p["s"], key)
                        break

            k = (norm(co), norm(name))
            d = det.get(k)
            sources = []
            if d:
                sources.append({"kind": "manufacturer", "url": d.get("sourceUrl"),
                                "readOn": d.get("capturedDate"), "owner": co})
            n_items = nh.get(k) or []
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
