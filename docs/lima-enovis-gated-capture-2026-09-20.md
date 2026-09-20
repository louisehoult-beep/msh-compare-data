# Lima Orthopaedics UK Ltd — the 102-record capture was not a catalogue (20/09/2026)

Closes OUTSTANDING `^o554`, which read: *"Lima Orthopaedics UK Ltd (limacorporate.com)
crawled as 102 'divisions' that are just numeric IDs (1, 2, 3...337), not real taxonomy —
nothing can be safely mapped from this capture. Needs a different capture route (real
breadcrumb/category structure), a crawler fix, not a mapping decision."*

**There is no different capture route. The site cannot be read at all.** The line's premise
was that a better crawler would reach a real taxonomy on this site; it would not.

## What was actually held

`data/supplier-products.json` held 102 records for this supplier, captured 19/09/2026 by the
sitemap route (`structureFrom: "sitemap"`, so no page was ever fetched — names came from URL
slugs). Of those 102:

- **7 were category landing pages**, not products: `Shoulder.Html`, `Elbow.Html`, `Hip.Html`,
  `Knee.Html`, `Fixation.Html`, `Promade.Html` and one more, from
  `/en/products/category/<id>/<name>.html`.
- **95 were product URLs whose pages were never read**, from
  `/en/products/<id>/<slug>.html` — e.g. `Smr Anatomic`, `Discovery Elbow System`.
- **All 102 "divisions" were the numeric id segment of the URL** (1, 2, 3 ... 337), which is
  a record id, not the company's own filing. That is what `^o554` reported.

## What was checked, 20/09/2026

1. **`limacorporate.com` now serves `enovis-surgical.com`.** Its `sitemap.xml` (435 URLs)
   contains only `https://enovis-surgical.com/...` locations. The stored capture's
   `source` field still said "limacorporate.com XML sitemap", which no longer describes
   where the content comes from.
2. **Every product and category URL redirects to an interstitial.**
   `https://enovis-surgical.com/en/products/72/smr-anatomic.html` and
   `https://enovis-surgical.com/en/products/category/3/hip.html` both resolve to
   `https://enovis-surgical.com/en/check.html` — title "Check - Enovis Surgical", a
   healthcare-professional gate. Checked with a browser user agent, following redirects.
3. **A cookie jar does not clear it.** The same URL was requested twice in sequence with
   `-c`/`-b` against one jar: both responses were the same 17,581-byte `check.html`. The gate
   needs an in-page interaction, not a cookie the crawler can carry.

So there is no page on this site from which a product name, a division or a source record
can honestly be taken, and any future crawl of it would reproduce exactly the same 102
non-products.

## What changed

- `data/supplier-products.json` — the `Lima Orthopaedics UK Ltd` capture (102 records) is
  **removed**, and the supplier is recorded under `refusals` with the evidence above.
  Refusals: 518 → 519.
- `data/differentiator-category-map.json` — the supplier's 102 entries are removed. **None
  of them carried a `hub` category**, so nothing was published from this capture and no
  member-facing page changes. Entries 6164 → 6062.
- The map's `counts` block is recomputed from the entries. Note that it was **already 10
  pairs stale before this change** (stored `pairs: 6154` against an actual 6164 on the same
  file, `mapped` 5073 against 5083), so the new figures correct that drift as well as this
  removal — the difference is not this change's arithmetic.

## Still open, and not fixed here

The numeric-id-as-a-division defect is **not unique to Lima**. Two other suppliers currently
hold the same shape, and unlike Lima theirs *are* mapped and published:

| Supplier | Numeric "divisions" | Mapped entries |
|---|---|---|
| Crest Medical Ltd (`www.crestmedical.co.uk`) | 872 of 872 | 870 |
| Oticon (`www.oticon.co.uk`) | 43 of 46 | 48 entries total |

`app/supplier-search.js` renders a supplier's full range grouped "under the company's own
division names", so those numeric ids are member-visible as if they were the company's own
grouping. Raised as its own OUTSTANDING line rather than fixed in this change, because the
fix is a crawler rule (a path segment that is entirely digits is an id, never a division)
plus a re-crawl of both suppliers, and leaving either one stale behind a changed rule would
be worse than the current state.
