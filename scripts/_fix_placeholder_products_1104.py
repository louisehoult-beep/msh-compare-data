"""One-off, 04/11/2026: drop CMS placeholder pages ("Test Product" and the like)
already stored by the range and detail crawls. Found on Hospital Direct's own
profile while preparing the Hub for their team. The crawler now refuses the
shape (crawl_supplier_site.is_junk_product_name, rule 4) and build_differentiator
skips it, so this only cleans what was captured before the rule existed.

Only placeholder names are touched (the regex in rule 4). FAQ and confirmation
names that the older rules cover are left as stored; the build already skips them.

Run once from the repo root, then rebuild the Differentiator and product categories.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl_supplier_site as cs                    # noqa: E402

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"


def placeholder(n):
    return bool(cs._PLACEHOLDER_NAME_RE.match(str(n or "").strip()))


def dump(doc, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def main():
    rng = json.load(open(RANGE, encoding="utf-8"))
    dropped = []
    for co, rec in rng["suppliers"].items():
        rows = rec.get("products") or []
        kept = [p for p in rows if not placeholder(p.get("n"))]
        if len(kept) == len(rows):
            continue
        dropped += [(co, p.get("n")) for p in rows if placeholder(p.get("n"))]
        rec["products"] = kept
        for p in rows:
            if placeholder(p.get("n")):
                d = p.get("division") or "Uncategorised"
                for dv in rec.get("divisions") or []:
                    if isinstance(dv, dict) and dv.get("name") == d and isinstance(dv.get("products"), int):
                        dv["products"] -= 1
                rec["divisions"] = [dv for dv in rec.get("divisions") or []
                                    if not (isinstance(dv, dict) and dv.get("products") == 0)]
        for k in ("productCount", "count"):
            if isinstance(rec.get(k), int):
                rec[k] = len(kept)
    dump(rng, RANGE)

    det = json.load(open(DETAIL, encoding="utf-8"))
    gone = [k for k, v in det["products"].items() if placeholder(v.get("product"))]
    for k in gone:
        del det["products"][k]
    dump(det, DETAIL)

    for co, n in dropped:
        print("range  -", co, "|", n)
    for k in gone:
        print("detail -", k)


if __name__ == "__main__":
    main()
