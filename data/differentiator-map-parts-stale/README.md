# Stale map-parts, moved aside 18/10/2026

These three files were committed 09/10/2026 and have blocked every run of
`scripts/merge_differentiator_parts.py` since: every decision in them names a
(supplier, division/term) pair that is no longer in the current worklist
(product/division names changed under a later recrawl), so the script refuses
the WHOLE merge, not just these entries, until they're fixed or removed.

Moved here rather than deleted — the judgement calls inside them may still be
correct for the supplier's current catalogue under today's names, just not
re-keyed. Written to OUTSTANDING.md the same day. Re-derive and re-key each
against the current worklist (`data/differentiator-category-map.json`
`entries`), or confirm they're superseded, before deleting this folder.

- Insulet-International-Ltd--agent-batch5.json — "Omnipod5" not in worklist.
- Johnson-Johnson-Surgical-Vision.json — two non-English ACUVUE product names
  not in worklist (likely a locale variant captured by an earlier crawl).
- Wassenburg Medical.json — 9 decontamination-equipment product names not in
  worklist. Likely cause: these read as product-level decisions (the
  "division" value is a full product name, e.g. "EndoHigh® PAA and Detergent
  Process Chemicals") filed WITHOUT `"kind": "product-override"` — compare
  the two EndoHigh/EndoCart entries already live in
  `../differentiator-category-map.json` with that kind tag, evidenced
  15/10/2026, which look like this same batch done correctly. Re-key these 9
  as product-override entries (written directly into
  differentiator-category-map.json per its own rule — merge_differentiator_parts.py
  cannot create a product-override pair) rather than re-deciding them.
