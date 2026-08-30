# One file per supplier — never edit the map directly

Agents write here. Nothing writes `../differentiator-category-map.json` except
`scripts/merge_differentiator_parts.py`.

One file per supplier, named for the supplier, so two agents working different
suppliers can never touch the same file:

```json
{"supplier": "Guldmann",
 "decisions": [
   {"division": "Slings",
    "hub": "handling:sling",
    "why": "the division holds sling products only — checked against the example
            products carried on the worklist row"}
 ]}
```

`supplier` and `division` must match the worklist row **exactly**; a typo maps
nothing and the merge will say so. `hub` is `<speciality>:<type>` from the
vocabulary printed at the top of the map file. `why` is required: a mapping is a
judgement, and it publishes with its reason.

**A division that spans several categories goes in ALL of them (Lou's rule,
25/08/2026) — do not pick one.** `hub` can be a list instead of a single string:

```json
{"supplier": "Vygon (UK)",
 "decisions": [
   {"division": "Vascular Access Devices",
    "hub": ["vascular:picc", "vascular:cvc", "vascular:sec"],
    "why": "the division's own categories name PICC lines, tunnelled catheters/
            ports and dressings/fixation as separate lines within it"}
 ]}
```

`build_differentiator.py` then publishes the division's products once per listed
category, so it shows up in every comparison it genuinely belongs in — still
locked to one category per published row, never a product compared against the
wrong thing. This replaces "pick the dominant type or leave it unmapped" for a
division whose own evidence supports more than one category — it does **not**
mean map every ambiguous division to everything plausible. A division whose
evidence doesn't clearly support any category is still left unmapped, exactly as
before; a list is for a division that has done the reading and genuinely spans
several, not a hedge for one that hasn't been read closely enough to tell.

Then, once, by one person:

```bash
python3 scripts/merge_differentiator_parts.py          # report only
python3 scripts/merge_differentiator_parts.py --apply  # fold them in
python3 scripts/build_differentiator.py
./land.sh "Differentiator: category mappings for <batch>" data/differentiator-category-map.json data/differentiator.json data/differentiator-map-parts
```

## Two traps, both found on 29/08/2026

**1. Reverting a mapping in the map alone does not stick.** The 14:00 run
reverted four thin-evidence mappings by editing
`../differentiator-category-map.json` directly, but left the part files that
proposed them in place. `merge_differentiator_parts.py` only ever fills a `hub`
that is currently null — so the very next merge re-applied all four, silently.
The 20:00 run caught it and deleted the offending decisions from
`Corin--agent-batch6.json` and `Heidelberg-Engineering--agent-batch6.json`.

**A revert is only done when the decision is removed from the part file that
proposed it.** Fix the part file first, then the map. If you revert in the map
only, you have scheduled the same wrong mapping to publish on the next run.

**2. `scripts/seed_differentiator_map.py` must NOT be re-run.** It rebuilds the
pair list from `data/supplier-products.json` alone, which predates the NHSSC
route. Every `kind: "nhssc-term"` entry — and every division belonging to a
supplier reached only through the NHS Supply Chain catalogue — has no record
there at all. Re-running it on 29/08 dropped 982 mapped pairs covering 10,850
products, including Coloplast, BD, B. Braun, Smith+Nephew, Medtronic, Boston
Scientific and Stryker: precisely the un-crawlable majors the whole NHSSC route
exists to reach. It was backed out and not published.

Adding new divisions from a fresh crawl unions the new pairs onto the existing
map instead of regenerating the list. **That seeder now exists:**

```bash
python3 scripts/union_differentiator_pairs.py            # report only
python3 scripts/union_differentiator_pairs.py --apply     # append the new pairs
```

Built 30/08/2026, after the 20:00 sprint run found **428 (supplier, division)
pairs holding 11,030 products that were in `supplier-products.json` but had no
entry in the map at all** — invisible to every "how many are unmapped?" query,
because those queries count map entries and these had none. They arrived with
the WooCommerce Store API route (Surtex alone: 204 pairs) and the nightly cloud
captures, and `merge_differentiator_parts.py` refuses any decision for a pair
that is not already in the worklist, so there was no route for them into the
map.

It is append-only by construction and asserts it rather than trusting it: every
existing entry is carried through object-for-object, a pair already in the map is
never touched even if the fresh crawl now sees different products under it, and
the run refuses to write if it would add a duplicate pair. An entry's identity is
`(supplier, division)` for a division row and `(supplier, term)` for an
`nhssc-term` row — keying both on division collapses every one of a supplier's
NHSSC terms onto `(supplier, None)`.
