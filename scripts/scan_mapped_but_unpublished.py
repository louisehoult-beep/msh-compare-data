#!/usr/bin/env python3
"""How many products are mapped to a Hub category and still never publish?

WHY THIS EXISTS. `build_differentiator.py` publishes a product only when it has
BOTH a category from the gated vocabulary AND at least one source that carries
it (the manufacturer's own product page, captured by
`scripts/crawl_supplier_product_detail.py`, or an NHS Supply Chain catalogue
entry). Those are two independent halves, and the second one is easy to forget:
a division can be mapped — correctly, with evidence, by a human — and every
product under it still sits in `held` forever because nothing ever captured a
source for it.

That shape was found on Griffiths and Nielsen Ltd on 18/09/2026 (mapped, 0
published, fixed by running the detail crawler over its 7 products) and
immediately reproduced on Vernacare, where it is NOT fixable — its "products"
are navigation labels, so there is no product page to source from. `^o542`
asked for a Hub-wide count, which is what this is.

It answers three questions and nothing else — it is a REPORT, it writes no data
file and changes no published output:

  1. how many crawled products are mapped but carry no source, and so are held;
  2. whether the supplier is reachable (has a domain, is not a recorded crawl
     refusal), i.e. whether a capture run would actually fix it;
  3. whether the detail crawler has ALREADY succeeded on that supplier — which
     separates "this site cannot be read" from "this site can be read and the
     run simply has not got there yet".

Read-only, stdlib only, exits 0. Run it from the repo root:

    python3 scripts/scan_mapped_but_unpublished.py
    python3 scripts/scan_mapped_but_unpublished.py --top 40
"""
import argparse
import collections
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm():
    """Reuse build_differentiator's own norm() rather than a second copy of it.

    A scan that normalises names even slightly differently from the builder
    reports a gap the builder does not have, which is worse than no scan.
    """
    spec = importlib.util.spec_from_file_location(
        "_bd", os.path.join(HERE, "scripts", "build_differentiator.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.norm


def load(name):
    with open(os.path.join(HERE, "data", name)) as fh:
        return json.load(fh)


def scan():
    norm = _norm()
    sp = load("supplier-products.json")
    own = sp["suppliers"]
    refusals = sp.get("refusals") or {}
    detail = load("supplier-product-detail.json")["products"]
    cmap = load("differentiator-category-map.json")
    diff = load("differentiator.json")

    det = {(norm(v.get("supplier", "")), norm(v.get("product", "")))
           for v in detail.values()}
    has_any_detail = {norm(v.get("supplier", "")) for v in detail.values()}
    mapped = {(e.get("supplier"), e.get("division")): e["hub"]
              for e in cmap.get("entries", []) if e.get("hub")}
    # Published is read from the LAST BUILD rather than recomputed: a product
    # the NHSSC route rescued has a source even with no detail capture, and
    # nothing here should count it as stranded.
    published = {(norm(r["supplier"]), norm(r["name"])) for r in diff["products"]}
    refused = {norm(x) for x in (refusals if isinstance(refusals, dict)
                                 else [r.get("supplier", "") for r in refusals])}

    rows = mapped_rows = 0
    per_supplier = collections.Counter()
    per_pair = collections.Counter()
    pair_hub = {}
    for co, rec in own.items():
        for p in (rec.get("products") or []):
            name = p.get("n")
            if not name:
                continue
            rows += 1
            div = p.get("division") or ""
            hub = mapped.get((co, div)) or mapped.get((co, name))
            if not hub:
                continue
            mapped_rows += 1
            key = (norm(co), norm(name))
            if key in det or key in published:
                continue
            per_supplier[co] += 1
            per_pair[(co, div)] += 1
            pair_hub[(co, div)] = hub

    return {
        "rows": rows, "mapped_rows": mapped_rows,
        "per_supplier": per_supplier, "per_pair": per_pair, "pair_hub": pair_hub,
        "own": own, "refused": refused, "has_any_detail": has_any_detail,
        "norm": norm,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=25,
                    help="how many suppliers and divisions to list")
    args = ap.parse_args()

    r = scan()
    per, own, norm = r["per_supplier"], r["own"], r["norm"]
    total = sum(per.values())

    reachable = refused_n = nodomain = already = 0
    for co, n in per.items():
        if norm(co) in r["refused"]:
            refused_n += n
        elif not (own.get(co, {}) or {}).get("domain"):
            nodomain += n
        else:
            reachable += n
            if norm(co) in r["has_any_detail"]:
                already += n

    print("MAPPED BUT UNPUBLISHED — products held only for want of a source")
    print("=" * 70)
    print("crawled product rows                        : %7d" % r["rows"])
    print("  division or product IS mapped to a hub cat: %7d" % r["mapped_rows"])
    print("  ...and has NO source, so never publishes  : %7d" % total)
    print("     across (supplier, division) pairs      : %7d" % len(r["per_pair"]))
    print("     across suppliers                       : %7d" % len(per))
    print()
    print("Is the gap fixable by running the detail crawler?")
    print("  supplier has a domain and is not refused  : %7d  (%.0f%%)"
          % (reachable, 100.0 * reachable / total if total else 0))
    print("    ...at a supplier the crawler has ALREADY"
          "\n       captured other products from        : %7d" % already)
    print("  supplier is a recorded crawl refusal      : %7d" % refused_n)
    print("  supplier has no domain recorded           : %7d" % nodomain)
    print()
    print("Top %d suppliers:" % args.top)
    for co, n in per.most_common(args.top):
        dom = (own.get(co, {}) or {}).get("domain") or "-"
        state = ("REFUSED" if norm(co) in r["refused"]
                 else "some detail captured" if norm(co) in r["has_any_detail"]
                 else "no detail captured")
        print("  %5d  %-38s %-28s %s" % (n, co[:38], dom[:28], state))
    print()
    print("Top %d (supplier, division) pairs:" % args.top)
    for (co, div), n in r["per_pair"].most_common(args.top):
        hub = r["pair_hub"][(co, div)]
        hub = ", ".join(hub) if isinstance(hub, list) else hub
        print("  %5d  %-34s %-30s -> %s" % (n, co[:34], div[:30], hub[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
