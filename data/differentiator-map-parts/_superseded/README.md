# Superseded map-parts — kept as a record, read by nothing

`merge_differentiator_parts.py` globs `*.json` in the parent directory only, so
nothing here is read. These files are kept because they carry the reasoning
behind decisions that were once applied, not because they still apply.

## Direct Healthcare Group, Talley, Macromed UK Ltd — moved 27/08/2026

All 208 decisions in these ten files were refused by the merge, and every one of
them was dead: not a single decision named a (supplier, division) pair that still
exists in the worklist.

They were written against a crawl that had mistaken each PRODUCT PAGE for a
division. The "divisions" they decide are product names — `Dyna Form Static Air
Hz`, `Florien Ii`, `Duo Mini` for Direct Healthcare Group; `Wendover Advance
Riser Recliner`, `Eclipse Wheelchair 125 318Kg` for Talley. A later re-crawl of
all three sites stopped reading the structure that way and now files them under
`Uncategorised`, so the pairs these files decide no longer exist.

They are NOT restored by re-crawling. The structure they describe was never the
company's filing; it was the crawler reading a product listing as a taxonomy.
Whatever eventually gives these three suppliers real divisions will produce
different division names, and will need its own decisions made against the
evidence then.

They were moved rather than deleted because the merge is all-or-nothing — it
refuses to write while any decision is refused, so 208 dead decisions blocked
every later batch from landing.

**Still outstanding:** Direct Healthcare Group (389 products), Talley (305) and
Macromed UK Ltd all remain in the crawler pseudo-division gap, filed entirely
under `Uncategorised`. See `Hub/Architecture/DIFFERENTIATOR-CRAWLER-ROUTES.md`.
