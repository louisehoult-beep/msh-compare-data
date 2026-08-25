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
