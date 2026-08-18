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

Then, once, by one person:

```bash
python3 scripts/merge_differentiator_parts.py          # report only
python3 scripts/merge_differentiator_parts.py --apply  # fold them in
python3 scripts/build_differentiator.py
./land.sh "Differentiator: category mappings for <batch>" data/differentiator-category-map.json data/differentiator.json data/differentiator-map-parts
```
