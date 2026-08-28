#!/usr/bin/env python3
"""Seed data/nhssc-category-map.json — the worklist that lets NHS Supply Chain
catalogue rows publish into the Differentiator.

WHY THIS EXISTS (28/08/2026)
----------------------------
The Differentiator has two sources. The supplier's own site is one, and it is
the one every mapping tool so far has served: data/differentiator-category-map.json
maps a (supplier, DIVISION) pair — a heading read off the company's own website.

The other source is the NHS Supply Chain catalogue, and it had no map at all.
An NHSSC row could only publish if the catalogue's own description text happened
to literally contain the words of a curated type label (see the NHSSC-only block
in build_differentiator.py). That is a very narrow gate, and it left **976 rows
held** against 81 published.

That gap matters more than its size suggests. Measured 28/08/2026: of the 281
awarded suppliers this repo cannot crawl — because their robots.txt forbids it,
or their catalogue is JS-rendered, or their site publishes no product structure
at all — **101 are already sitting in the NHSSC cache**, holding 3,330 catalogue
lines between them. They include Coloplast, B.Braun, Smith+Nephew, Convatec,
Mölnlycke, Paul Hartmann, Urgo, Medtronic, BD, Boston Scientific, Stryker,
Johnson & Johnson MedTech and GE HealthCare — which is to say, most of the
manufacturers a rep is actually sold against.

The NHS Supply Chain catalogue is the BUYER'S OWN published list. Reading it is
not a way around a supplier's robots.txt — it is a different, public source that
the supplier itself supplies to. It is therefore the only permitted route this
repo has to those companies, and the reason this map is worth building.

WHAT A ROW IS, AND WHAT IT IS NOT
---------------------------------
One row per (supplier, catalogue search term) pair — the same grain the cache
itself uses. `hub` is "<speciality>:<type>" from the gated vocabulary in
data/compare-suppliers.json, or a LIST of them where the term genuinely spans
several (Lou's rule, 25/08/2026, same as the division map).

**A term is not a product and not a division.** It is the phrase the cache
searched NHS Supply Chain for, and the items beneath it are whatever the
catalogue returned under that phrase for that supplier. So the evidence for a
mapping is the ITEM DESCRIPTIONS, which is why every row carries up to eight of
them verbatim. Read those, not the term.

Leave `hub` null where the items do not clearly belong to one gated category.
An unmapped row is held, which is the correct outcome — a product compared
against the wrong category reads to a member as a product that fails on every
measure, rather than one that was never comparable.

RE-RUNNABLE. Existing decisions are preserved by (supplier, term) key; only the
evidence fields are refreshed and genuinely new pairs are appended. Same
contract as scripts/seed_differentiator_map.py.

Run:  python3 scripts/seed_nhssc_map.py
Then: agents fill `hub` + `why`, then python3 scripts/build_differentiator.py
"""
import json, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
CACHE = os.path.join(DATA, "nhssc-cache.json")
VOCAB = os.path.join(DATA, "compare-suppliers.json")
OUT = os.path.join(DATA, "nhssc-category-map.json")

MAX_EXAMPLES = 8


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    cache = load(CACHE).get("products") or {}
    vocab = load(VOCAB).get("specialities") or {}

    legal = {}
    for sk, sv in vocab.items():
        for tk, label in (sv.get("types") or {}).items():
            legal["%s:%s" % (sk, tk)] = "%s / %s" % (sv.get("label") or sk, label)

    prior = {}
    if os.path.exists(OUT):
        for e in load(OUT).get("entries", []):
            prior[(e.get("supplier"), e.get("term"))] = e

    entries, kept = [], 0
    for term, rec in cache.items():
        co = rec.get("supplier")
        if not co:
            continue
        items = rec.get("items") or []
        if not items:
            continue
        # Verbatim catalogue descriptions — the evidence a decision is made on.
        ex = []
        for it in items[:MAX_EXAMPLES]:
            d = (it.get("desc") or it.get("name") or "").strip()
            if d:
                ex.append(d)
        old = prior.get((co, term))
        row = {
            "supplier": co,
            "term": term,
            "items": len(items),
            "examples": ex,
            "npcSample": [it.get("npc") for it in items[:3] if it.get("npc")],
            "hub": (old or {}).get("hub"),
            "why": (old or {}).get("why"),
            "decidedIn": (old or {}).get("decidedIn"),
            "evidence": "NHS Supply Chain public catalogue, cached by "
                        "scripts/refresh_nhssc_cache.py; decision made on the "
                        "catalogue's own item descriptions above",
        }
        if old and old.get("hub"):
            kept += 1
        entries.append(row)

    entries.sort(key=lambda e: (-e["items"], e["supplier"]))
    mapped = sum(1 for e in entries if e.get("hub"))
    doc = {
        "rule": "One row per (supplier, NHS Supply Chain search term). `hub` is "
                "'<speciality>:<type>' from the gated vocabulary below, or a list "
                "where the term genuinely spans several. Decide from the catalogue "
                "item descriptions in `examples`, never from the term string. A row "
                "with no clear evidence stays null and is held, never guessed.",
        "whyThisExists": "The NHS Supply Chain catalogue is the buyer's own published "
                         "list, and the only permitted route to the 101 awarded "
                         "suppliers this repo cannot crawl — including Coloplast, "
                         "B.Braun, Smith+Nephew, Convatec and Medtronic. Without this "
                         "map their catalogue lines are held rather than comparable.",
        "vocabulary": legal,
        "counts": {
            "pairs": len(entries),
            "mapped": mapped,
            "unmapped": len(entries) - mapped,
            "itemsBehindPairs": sum(e["items"] for e in entries),
            "itemsUnlockedSoFar": sum(e["items"] for e in entries if e.get("hub")),
        },
        "entries": entries,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("wrote %s" % os.path.relpath(OUT, REPO))
    print("  pairs: %d   mapped: %d   unmapped: %d   (preserved %d prior decisions)"
          % (len(entries), mapped, len(entries) - mapped, kept))
    print("  catalogue items behind them: %d" % doc["counts"]["itemsBehindPairs"])
    top = collections.Counter()
    for e in entries:
        if not e.get("hub"):
            top[e["supplier"]] += e["items"]
    print("\n  biggest unmapped suppliers (items still held):")
    for co, n in top.most_common(15):
        print("    %5d  %s" % (n, co))


if __name__ == "__main__":
    main()
