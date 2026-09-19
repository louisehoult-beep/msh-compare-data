# Mapped but unpublished — the Hub-wide scan (19/09/2026)

Answers `^o542`, raised 18/09/2026: *"a division mapped to a hub category with no
`supplier-product-detail.json` entry never publishes (found on Griffiths and Nielsen Ltd,
fixed; reproduced on Vernacare, unfixable there). Worth a Hub-wide scan."*

Scan script: `scripts/scan_mapped_but_unpublished.py` (read-only, stdlib, writes nothing).
Figures below are its output against `main` at `5536c035`, data as generated 19/09/2026 07:36.

## The rule this is measuring

`scripts/build_differentiator.py` publishes a product only when **both** halves hold:

1. it carries a category from the gated vocabulary, **and**
2. at least one source carries it — the manufacturer's own product page (captured by
   `scripts/crawl_supplier_product_detail.py`) or an NHS Supply Chain catalogue entry.

The two halves are independent, and only the first one has a person attached to it. A
division can be mapped correctly, with evidence, by hand — and every product under it still
sits in `held` forever, because nothing ever captured a source. The held row says so in as
many words: *"no source carries this product — neither the manufacturer's own page nor
NHSSC"*. Nothing about the mapping is wrong; the product simply never reaches a member.

## The count

| | |
|---|---:|
| crawled product rows | 84,059 |
| of those, division or product **is** mapped to a hub category | 53,725 |
| **…and carries no source, so never publishes** | **21,514** |
| across (supplier, division) pairs | 1,098 |
| across suppliers | 127 |

For scale: the Differentiator publishes **35,581** products today. The stranded set is
**60% of that again**, already mapped, waiting only on a capture run.

## Whether it is fixable, which is the point of the scan

This is the part that turns a number into a decision. The gap splits cleanly:

| situation | products | share |
|---|---:|---:|
| supplier has a working domain and is **not** a recorded crawl refusal | 21,102 | 98% |
| …of which, at suppliers the detail crawler has **already succeeded on** | 20,213 | 94% |
| supplier is a recorded crawl refusal (route genuinely closed) | 412 | 2% |
| supplier has no domain recorded | 0 | 0% |

**94% of the backlog sits behind a site the crawler has already proven it can read.** This
is not a blocked-route problem like Altomed (Cloudflare, `^o458`) or a fake-product problem
like Vernacare and Globus (`^o521`) — for the large majority it is simply an unfinished run.

The two named in `^o542` land on opposite sides of that split, which is why the one-supplier
view was misleading in both directions:

- **Griffiths and Nielsen Ltd** — 7 products, crawler worked first time, fixed 18/09. Typical
  of the 94%.
- **Vernacare** — its "products" are navigation labels (`Large Range`, `Pocket Size Range`),
  so there is no product page to source from and no run will ever fix it. Same shape as
  Globus (Shetland) Ltd's Hand Protection division. Part of the 412, and correctly held.

## Why it is not clearing on its own

`.github/workflows/supplier-product-detail-capture.yml` runs **weekly, Sunday 02:40 UTC**, with
`--limit 15 --products-limit 40`: at most **15 suppliers × 40 products = 600 products a week**
(`MAX_PRODUCTS_PER_SUPPLIER = 40` caps it per supplier per run, with a resume cursor in
`state/product-detail-cursor.json` so the next run continues rather than repeats).

21,514 ÷ 600 ≈ **36 weeks, about 8 months**, and that assumes no new crawl ever adds to it.
The concentration makes it worse for the biggest suppliers, not better: Surtex Instruments Ltd
alone has 2,864 stranded products and takes 40 a week, so on its own it is **72 weeks**.

The backlog is also top-heavy — the ten largest suppliers hold **13,210 of the 21,514 (61%)**:

| products | supplier | domain | crawler state |
|---:|---|---|---|
| 2,864 | Surtex Instruments Ltd | surtex-instruments.com | some detail captured |
| 2,071 | Kettering Surgical Appliances | ketteringsurgical.co.uk | some detail captured |
| 1,751 | Kimberly Clark | avanos.com | some detail captured |
| 1,588 | Abilia Ltd | www.abilia.com | some detail captured |
| 1,051 | Aero Healthcare Ltd | aerohealthcare.com | some detail captured |
| 1,030 | Sysmex UK | sysmex.co.uk | some detail captured |
| 808 | QIAGEN UK | www.qiagen.com | some detail captured |
| 720 | HC21 (UK) Ltd | healthcare21.eu | some detail captured |
| 664 | Millbrook Healthcare | millbrookhealthcare.co.uk | some detail captured |
| 663 | Uniplex | uniplexuk.com | some detail captured |

## What this scan does NOT claim

- It does **not** say any of the 21,514 *should* publish. Each one still has to pass the same
  gate on the way out, and a capture that reads navigation labels instead of products must
  still be refused — the Vernacare and Globus cases are the standing proof that "mapped" and
  "real product" are different questions (root rule 14).
- It does **not** re-open any supplier's recorded refusal. The 412 stay refused.
- It is a **throughput** observation, not a ruling. Raising `--limit` / `--products-limit`, or
  running the capture more often than weekly, is a cost-and-politeness decision about how hard
  to hit 127 suppliers' websites — that is Lou's call, not one to make inside a sweep.

## Suggested next step, for a decision rather than an action

The cheapest meaningful change is to raise the weekly workflow's two inputs (both are already
`workflow_dispatch` inputs, so no code change is needed to trial it) and watch one Sunday's
run for refusals or rate-limiting before making it the default. Clearing the top ten suppliers
alone would move 61% of the backlog.

Recorded, not actioned. Re-run the count any time with:

```
python3 scripts/scan_mapped_but_unpublished.py --top 40
```
