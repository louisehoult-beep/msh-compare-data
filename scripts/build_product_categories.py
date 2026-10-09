#!/usr/bin/env python3
"""
build_product_categories.py — a small lookup of each product's Differentiator
category, for Product Comparison (app/comparison.js) to suggest rivals from.

WHY IT EXISTS (30/09/2026). Product Comparison suggested a rival for HARTMANN's
HydroClean Advance, a debridement dressing, by word overlap on the product name
and the first catalogue description. That ranked honey, silver and contact
layer dressings first, because they share generic words ("dressing", "wound").
The Hub already records what category each product is in: every published
Differentiator row carries exactly one `cat` from the gated vocabulary
("wound:deb", Debridement & irrigation). The tool could not read it, because
data/differentiator.json is 45 MB. This file carries only the part the tool
needs: which category each NHS Supply Chain code (NPC) and each product name is
filed in.

A PURE DERIVATION of data/differentiator.json and nothing else. It adds no fact
the Differentiator does not already publish, and it never guesses a category:
a product with no category there has none here, and the tool falls back to its
word match for it. The Differentiator workflow runs it straight after
build_differentiator.py so the two never drift apart.

Keys are exactly what comparison.js looks up:
  categories[cat].npc                  NPC codes of the rows filed in `cat`
  categories[cat].names[supplier]      nk(product name), the tool's own
                                       normalisation (lower case, runs of white
                                       space folded to one space, trimmed)

Usage:  python3 scripts/build_product_categories.py   (from the repo root)
Writes: data/product-categories.json
"""
import json
import re
import sys
from collections import defaultdict

SRC = "data/differentiator.json"
OUT = "data/product-categories.json"


def nk(s):
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def main():
    with open(SRC, encoding="utf-8") as f:
        diff = json.load(f)
    npc = defaultdict(set)
    names = defaultdict(lambda: defaultdict(set))
    for p in diff.get("products") or []:
        cats = p.get("cat")
        cats = cats if isinstance(cats, list) else [cats]
        for c in (c for c in cats if c):
            if p.get("supplier") and p.get("name"):
                names[c][p["supplier"]].add(nk(p["name"]))
            for line in p.get("nhssc") or []:
                if line.get("npc"):
                    npc[c].add(line["npc"])
    cats = sorted(set(npc) | set(names))
    doc = {
        "rule": ("Derived from data/differentiator.json by scripts/build_product_categories.py. "
                 "A code or name is listed under a category only where a published Differentiator "
                 "row carries that category. Nothing is inferred here."),
        "source": SRC,
        "categories": {
            c: {
                "npc": sorted(npc.get(c, ())),
                "names": {s: sorted(v) for s, v in sorted(names.get(c, {}).items())},
            }
            for c in cats
        },
    }
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        if "_notice" in old:
            doc = dict({"_notice": old["_notice"]}, **doc)
    except (OSError, ValueError):
        pass
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote %s: %d categories, %d NPCs, %d names" % (
        OUT, len(cats), sum(len(v["npc"]) for v in doc["categories"].values()),
        sum(len(n) for v in doc["categories"].values() for n in v["names"].values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
