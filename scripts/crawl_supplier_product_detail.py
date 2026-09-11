#!/usr/bin/env python3
"""Capture EACH product's OWN page on its supplier's OWN website, into
data/supplier-product-detail.json — full spec/feature/image detail that
data/supplier-products.json (the range-listing crawl) never captured, because
that crawl only ever asked "what does this company sell", never "what does
this ONE product page say".

WHY THIS EXISTS
---------------
The Differential compares products on the NHS Supply Chain catalogue text
plus bare product names from data/supplier-products.json. Neither carries the
supplier's own description, features/benefits or product image — the detail
a rep actually needs in the room, and the thing most likely to change between
sweeps (a supplier rewording a claim, updating a spec, swapping an image).
This script reads that page, once per known product, and remembers what it
said last time so a genuine change can be shown as sales intelligence:
"this supplier updated their description on DD/MM/YYYY".

HOW IT DECIDES WHAT IT CAN READ
--------------------------------
Two routes, same order of preference as scripts/crawl_supplier_site.py, and
this script says which one produced a result:

  A. **WordPress REST, single record** (structured). Where the site exposes a
     `product` post type, this reads the id+title LISTING once per supplier
     (the same call scripts/crawl_supplier_site.py already proves works),
     matches the product name against it, then fetches that ONE record with
     `_embed=1` — `content.rendered` / `excerpt.rendered` for description and
     features, `_embedded['wp:featuredmedia']` for the image. This is a
     company's own product record, read as data. It deliberately does NOT use
     the API's `?search=` parameter: on Vygon (18/08/2026) that parameter hung
     for 55+ seconds on every attempt while the plain listing and a
     single-record-by-id fetch both returned in under 3 seconds — a slow or
     blocked search endpoint must never read as "no product page exists".
  B. **Product page HTML** (weaker, and labelled so). The product's URL is
     located from the site's XML sitemap by matching the product name against
     the URL's last path segment. The page is then fetched and read in order
     of confidence:
       B1. a JSON-LD `Product` schema block, if the page carries one
           (`parsed: "structured"` — still a data record, just embedded in
           HTML rather than served by an API);
       B2. failing that, a best-effort text extraction from the page's
           `<main>`/`<article>`/content area, with `<nav>`, `<header>`,
           `<footer>`, `<script>`, `<style>` and anything that looks like a
           cookie/consent banner stripped out first (`parsed: "heuristic"`).

`parsed` travels with every entry so nothing downstream can treat a guess at
"the text that looked like the product" the same as a structured record.

WHAT IT WILL NOT DO
--------------------
- It does not invent a product page. If WP search returns nothing and no
  sitemap URL matches the product name closely enough, the product is
  SKIPPED and the reason is printed — never a plausible-looking summary
  built from the product name alone.
- It does not write a description or feature list from thin air. Route B2
  only reports text that is actually present on the page, inside the area
  identified as the main content; it never pads out a short capture.
- It does not claim a change without a prior capture to compare against. A
  product's first-ever capture never carries `changedSince` — there is
  nothing to compare it to yet.
- robots.txt is honoured (reuses scripts/crawl_supplier_site.py's `allowed`).
- It never overwrites the file with less than it started with: unreadable
  entries keep whatever was captured last time, and are simply not refreshed.

WHERE IT PICKS UP FROM
----------------------
A supplier's range can be far longer than one run's time budget, so the run
does NOT start at product 1 each time: it resumes after the last product it
attempted, recorded per supplier in state/product-detail-cursor.json, and
wraps round at the end of the range. Committing that file is part of the
weekly sweep (.github/workflows/supplier-product-detail-capture.yml) — a
cursor left behind in a CI checkout is the same as no cursor at all. Pass
--restart for a deliberate re-read of a range from the top.

Run:  python3 scripts/crawl_supplier_product_detail.py --supplier "Vygon (UK)" --domain vygon.co.uk --products-limit 5
      python3 scripts/crawl_supplier_product_detail.py --auto --limit 20
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl_supplier_site as base  # reuses get(), allowed(), clean(), UA_STR, socket timeout

OUT = "data/supplier-product-detail.json"
RANGE = "data/supplier-products.json"
SITE_BUDGET_S = 60          # per SUPPLIER (not per product) — several products share one budget
PRODUCT_BUDGET_S = 15       # per product lookup, inside the site budget
MAX_PRODUCTS_PER_SUPPLIER = 40
# The Shopify bulk route (route 0, added 28/08/2026) answers an entire
# supplier's range from a handful of paged /products.json requests rather
# than one request per product, so it gets its OWN, much larger budget —
# SITE_BUDGET_S=60s exists to bound N per-product lookups and is far too
# short for a 250-per-page walk of an 8,000+ product catalogue (Farla Medical:
# ~34 pages). Matches crawl_supplier_site.py's own SHOPIFY_BUDGET_S order of
# magnitude for the same reason.
SHOPIFY_BUDGET_S = 900

# A RESUME POSITION, so a range longer than one run's budget is not read from
# product 1 for ever (06/09/2026, ^o295/^o288/^o331). The per-supplier loop
# below stops when the site budget is spent, and used to start again at the
# first product in the range every run — so Medical Imaging Systems captured
# the identical first 36 of its 105 products on three consecutive runs, Conmed
# UK stalled at 30 of 167 and Avicenna at 23 of 78, however often the sweep
# ran. Raising the budget (--site-budget) only moves where the wall is; it
# does not make successive runs walk forward.
#
# The cursor records, per supplier, the NAME of the last product this script
# ATTEMPTED — attempted, not captured, because a product that can never be
# read (no matching sitemap URL, no WP record) would otherwise sit at the head
# of the queue and re-block the range every single run, which is the same
# stall in a different place. The next run resumes at the product AFTER that
# name and wraps round at the end of the range, so successive runs walk the
# whole range and then start refreshing it.
#
# A name, not an index: the range list is rebuilt by the site crawl and
# products are added and removed, so an index silently points at a different
# product later. If the recorded name is no longer in the range, the cursor
# has nothing to resume from and the run honestly starts at the beginning.
CURSOR = "state/product-detail-cursor.json"


def cursor_path_for(out_path):
    """Separate --out shards must not share one cursor file: two parallel
    workers writing the same cursor would each overwrite the other's position
    and both keep re-reading the same slice — the exact stall this fixes. The
    canonical output keeps the canonical cursor; any other --out gets its own
    beside it."""
    if os.path.normpath(out_path) == os.path.normpath(OUT):
        return CURSOR
    return out_path + ".cursor.json"


def load_cursors(path):
    if not os.path.exists(path):
        return {}
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError):
        # A cursor is an optimisation, never a source of truth: an unreadable
        # one costs a run that restarts at product 1, not a wrong capture.
        return {}
    return doc.get("cursors") or {}


def save_cursors(path, cursors):
    doc = {
        "_note": "Resume position for scripts/crawl_supplier_product_detail.py: "
                 "the last product NAME attempted per supplier. Not published data "
                 "- delete it and the next run simply starts each range at the top.",
        "generated": time.strftime("%Y-%m-%d"),
        "cursors": cursors,
    }
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def resume_slice(products, last_attempted, limit):
    """The next `limit` products to attempt, starting after `last_attempted`
    and wrapping round at the end of the range.

    Returns (slice, started_at_top). `started_at_top` is True when there was
    no usable resume position, so the caller can say so rather than implying
    it resumed.

    Wrapping matters: without it, a supplier whose cursor sits near the end of
    its range would get a slice of one or two products and the run would spend
    its budget on almost nothing. With it, every run gets a full window and the
    window advances; once the whole range has been walked the cursor comes back
    round to the start and the oldest captures get refreshed.
    """
    if limit <= 0 or not products:
        return [], True
    names = [nk(p.get("n")) for p in products]
    start = 0
    started_at_top = True
    if last_attempted:
        key = nk(last_attempted)
        if key in names:
            start = (names.index(key) + 1) % len(products)
            started_at_top = False
    if limit >= len(products):
        # The whole range fits in one window; ordering it from the resume
        # point still puts the unreached tail first, which is the point.
        return products[start:] + products[:start], started_at_top
    out = []
    i = start
    while len(out) < limit:
        out.append(products[i])
        i = (i + 1) % len(products)
    return out, started_at_top


def bootstrap_cursor(products, products_store, supplier):
    """A ONE-TIME resume position for a supplier that has captures but no saved
    cursor yet — every supplier, the first run after the cursor was added.

    Without it the first run re-reads the prefix it has already got (105
    products at 36 a run means three wasted runs before Medical Imaging
    Systems reaches anything new), because a cursor can only be written by a
    run that has happened.

    This is DERIVED FROM STORED CAPTURES, not guessed: it returns the last
    product in range order that this file already holds a capture for, i.e.
    the furthest point the old take-the-first-N loop can be shown to have
    reached. Anything unread before that point is not lost — resume_slice
    wraps, so the next cycle comes back round to it.

    Returns None when nothing in the range has been captured, and the run then
    honestly starts at the top."""
    last = None
    for prod in products:
        name = prod.get("n")
        if name and (supplier + "|" + nk(name)) in products_store:
            last = name
    return last



def nk(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return re.sub(r"-+", "-", s)


# ---------------------------------------------------------------- route A
def wp_ptype(domain):
    types, _ = base.get("https://%s/wp-json/wp/v2/types" % domain, as_json=True)
    for key, val in types.items():
        if key.lower() in ("product", "products") or "product" in (val.get("rest_base") or ""):
            return val.get("rest_base") or key
    return None


def wp_product_id_index(domain, ptype, deadline=None):
    """The id+title listing crawl_supplier_site.py already proves works and is
    fast (~2-3s/page). Built ONCE per supplier and reused for every product,
    rather than one lookup per product — because the site's own `?search=`
    query parameter hangs indefinitely on at least one real site (Vygon,
    18/08/2026: 55s+ with no response, on every attempt, while plain listing
    and single-record-by-id both return in under 3s). A slow or blocked
    search endpoint must not read as "no product page exists"."""
    idx, page = {}, 1
    while page <= 40:
        if deadline and time.time() > deadline:
            break
        try:
            items, _ = base.get("https://%s/wp-json/wp/v2/%s?per_page=100&page=%d&_fields=id,title"
                                % (domain, ptype, page), as_json=True, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                break
            raise
        if not items:
            break
        for it in items:
            t = base.clean((it.get("title") or {}).get("rendered")).lower()
            if t:
                idx[t] = it.get("id")
        if len(items) < 100:
            break
        page += 1
    return idx


def wp_single_product(domain, name, id_index, ptype="product"):
    """Fetch the ONE matching product record (by id, from the pre-built title
    index) with embedded media. Returns (record-dict, None) or (None, why).

    `ptype` is the rest_base wp_ptype() discovered and wp_product_id_index()
    already listed against. It used to be hardcoded to "product" here while the
    listing used the discovered one, so every site whose product post type is
    named anything else answered HTTP 404 to the single-record fetch and the
    whole supplier fell through to the sitemap route. Found 08/09/2026 on
    BioSpectrum Ltd, whose type is "products-custom": all 19 products skipped
    with "the site's WordPress API returned HTTP 404", so none of its mapped
    products could publish for want of a source."""
    if id_index is None:
        return None, "the site's WordPress product listing could not be read"
    target = base.clean(name).lower()
    pid = id_index.get(target)
    if not pid:
        return None, "no product titled exactly %r in the site's own WordPress product listing" % name

    url = "https://%s/wp-json/wp/v2/%s/%d?_embed=1" % (domain, ptype, pid)
    try:
        chosen, _ = base.get(url, as_json=True, timeout=20)
    except urllib.error.HTTPError as e:
        return None, "the site's WordPress API returned HTTP %d fetching this product record" % e.code
    except Exception as e:
        return None, "the site's WordPress API failed fetching this product record (%s)" % str(e)[:70]

    title = base.clean((chosen.get("title") or {}).get("rendered"))
    content_html = (chosen.get("content") or {}).get("rendered") or ""
    excerpt_html = (chosen.get("excerpt") or {}).get("rendered") or ""
    desc = base.clean(content_html) or base.clean(excerpt_html)
    features = extract_list_items(content_html)[:20]

    image = None
    embedded = chosen.get("_embedded") or {}
    media = embedded.get("wp:featuredmedia") or []
    if isinstance(media, list) and media and isinstance(media[0], dict):
        image = media[0].get("source_url") or None

    link = chosen.get("link") or url
    return {
        "title": title,
        "sourceUrl": link,
        "parsed": "structured",
        "description": desc[:2000] if desc else "",
        "features": features,
        "image": image,
    }, None


# ---------------------------------------------------------------- route 0 (Shopify, bulk)
# ADDED 28/08/2026, per Lou's decision the same day. WHY THIS EXISTS: the 12
# Shopify suppliers already identified by crawl_supplier_site.py's own Shopify
# route (Farla Medical, Scala Surgical, Appleton Woods, Nine Group
# International, Trulife, MedScience Distribution, Bailey Instruments, Blink
# Medical, Gailarde, Unigloves UK, Empire Medical UK, Advancis Medical —
# 23,792 products between them) sat almost entirely in the HELD bucket because
# routes A/B above are written per-product: one WordPress-listing check plus
# one sitemap-and-page fetch per product, which is the right shape for a site
# that has no other way to expose product detail, but is 20,000+ HTTP
# round-trips for suppliers that in fact publish it far more cheaply.
#
# A Shopify storefront serves its ENTIRE catalogue's own description, images
# and variant detail from `/products.json?page=N&limit=250` — a handful of
# paged requests per supplier, not one request per product. Confirmed live
# 28/08/2026 against farlamedicalhealthcare.com, scalasurgical.co.uk and
# appletonwoods.co.uk: every record carries `body_html` (the description),
# `images` (product photos), `vendor` and `variants[].sku`. This route reads
# that bulk feed ONCE per Shopify supplier and answers every product in the
# range from the single pull, rather than calling the per-product routes 40 or
# 400 times over. This is what turns ~20,000 held Shopify products into
# published ones — bulk beats N page-fetches, and route A/B would have taken
# weeks of per-supplier budget slices to reach the same coverage one page at a
# time.
#
# Detection reuses crawl_supplier_site.py's own probe (`/collections.json?
# limit=1`, checking `"collections" in probe`) rather than trusting the
# `source` label already recorded in data/supplier-products.json for these
# suppliers — a platform migration would silently stale that label, and the
# probe costs one request. main() below probes before choosing a route.
def shopify_probe(domain):
    """True if `domain` is a live, readable Shopify storefront right now."""
    try:
        probe, _ = base.get("https://%s/collections.json?limit=1" % domain, as_json=True)
    except Exception:
        return False
    return isinstance(probe, dict) and "collections" in probe


def shopify_product_details(domain, deadline):
    """Bulk-pull EVERY product this Shopify storefront serves, in one paged
    walk of /products.json, and return them keyed by normalised title so the
    caller can match against data/supplier-products.json's own product names
    (case/whitespace-insensitively, via nk()) without a second request per
    product. Raises on a hard failure (caller decides how to report it);
    returns {} if the storefront answered but carried no usable records."""
    prods = base._shopify_paged(domain, "/products.json", "products", deadline=deadline)
    out = {}
    for p in prods:
        title = base.clean(p.get("title"))
        if not title:
            continue
        handle = p.get("handle")
        url = "https://%s/products/%s" % (domain, handle) if handle else "https://%s/" % domain
        desc = base.clean(p.get("body_html") or "")

        variants = p.get("variants") or []
        features = []
        if len(variants) > 1:
            for v in variants:
                if not isinstance(v, dict):
                    continue
                vt = base.clean(v.get("title"))
                if not vt or vt.lower() == "default title":
                    continue
                sku = base.clean(v.get("sku"))
                features.append("%s (SKU %s)" % (vt, sku) if sku else vt)

        images = p.get("images") or []
        image = None
        if images and isinstance(images[0], dict):
            image = images[0].get("src") or None

        entry = {
            "sourceUrl": url,
            "parsed": "structured",
            "description": desc[:2000],
            "features": features[:20],
            "image": image,
        }
        key = nk(title)
        if key and key not in out:      # first record wins on a duplicate title
            out[key] = entry
    return out


# ---------------------------------------------------------------- route B
def extract_list_items(html_frag):
    out = []
    for m in re.finditer(r"<li[^>]*>(.*?)</li>", html_frag, re.I | re.S):
        t = base.clean(m.group(1))
        if t and len(t) > 2:
            out.append(t)
    return out


_SITEMAP_CACHE = {}

def _sitemap_urls(domain, deadline):
    """Read the site's sitemap ONCE per domain and remember the URL list.

    WHY (added 21/08/2026): find_product_url() rebuilt the entire sitemap for
    EVERY product. On a site with a large sitemap index the per-product budget
    expired mid-build every single time, so the run reported "gave up reading
    the sitemap inside the time budget" for all of that supplier's products and
    captured nothing at all, while still making hundreds of requests against
    that site. Two shards of the 21/08 sweep sat at zero captures for this
    reason. One build per domain, reused for every product, is both far faster
    and far politer to the site being read."""
    if domain in _SITEMAP_CACHE:
        return _SITEMAP_CACHE[domain]
    cachefile = "sitemap-cache/%s.json" % re.sub(r"[^a-z0-9.-]", "_", domain.lower())
    if os.path.exists(cachefile):
        try:
            urls = json.load(open(cachefile, encoding="utf-8"))
            _SITEMAP_CACHE[domain] = urls
            return urls
        except Exception:
            pass
    seen, urls = set(), []
    to_read = ["https://%s/sitemap.xml" % domain, "https://%s/sitemap_index.xml" % domain]
    build_deadline = time.time() + 240   # generous, but ONCE per domain
    while to_read and len(seen) < 60:
        if time.time() > build_deadline:
            break
        u = to_read.pop(0)
        if u in seen:
            continue
        seen.add(u)
        try:
            body, _ = base.get(u)
        except Exception:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        if "<sitemapindex" in body[:400].lower():
            to_read.extend([l for l in locs
                            if "product" in l.lower() or "sitemap" in l.lower()][:40])
            continue
        urls.extend(locs)
    _SITEMAP_CACHE[domain] = urls
    try:
        os.makedirs("sitemap-cache", exist_ok=True)
        json.dump(urls, open(cachefile, "w", encoding="utf-8"))
    except Exception:
        pass
    return urls


# Default: the generic product path segments. main() overrides from
# --product-path for a single run.
product_paths = None

# A NUMERIC-SLUG SITE'S NAME INDEX, and the pages it was read from.
# Both are per-run, per-domain and in-memory only: sitemap-cache/ is gitignored
# and every scheduled run works in a throwaway clone, so there is no run-to-run
# disk cache to lean on here — one build per domain per run is the whole win.
_NAME_INDEX = {}        # domain -> {nk(product name): url}
_PAGE_CACHE = {}        # url -> the HTML already fetched while indexing


def _leaf_stem(u):
    """The last path segment with any file extension removed: /product/15.php -> 15."""
    leaf = urllib.parse.urlparse(u).path.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.[a-zA-Z0-9]{1,5}$", "", leaf)


def _is_numeric_slug_site(prod_urls):
    """Are this site's product URLs bare ids rather than names?

    THE SAME TEST crawl_supplier_site.py's sitemap route already applies before
    it reads names off the pages themselves — at least 80% of product leaf stems
    pure digits — and deliberately the same numbers, so the two crawlers cannot
    disagree about what kind of site they are looking at. A URL that merely ends
    in a digit ("...-2") is not this failure and must not divert a normal
    descriptive-slug site into the slower per-page read.
    """
    if not prod_urls:
        return False
    numeric = sum(1 for u in prod_urls if re.match(r"^\d+$", _leaf_stem(u)))
    return numeric * 5 >= len(prod_urls) * 4


# The name index gets ITS OWN budget, deliberately equal to the budget
# crawl_supplier_site.py gives the identical per-page read, so the two crawlers
# cannot disagree about how long reading one site's product pages is worth.
NAME_INDEX_BUDGET_S = base.NUMERIC_SLUG_BUDGET_S


def _name_index(domain, prod_urls):
    """Map each numeric-slug product URL to the name its own page publishes.

    WHY (11/09/2026, OUTSTANDING ^o379). find_product_url() below matches a
    product name against the URL's last path segment. On a site that files
    products at bare ids — swann-morton.co.uk/product/15.php is the worked
    example, 137 of them — that segment slugifies to "15-php" and can never
    match "Surgical Scalpel Blade No. 9", so EVERY product was refused for "no
    sitemap URL's slug matches this product's name", no row ever got a source,
    and the coverage ledger read the supplier as never crawled and re-offered
    all 137 on every single run.

    The name is not missing, only absent from the URL: crawl_supplier_site.py
    already reads it off each page to capture the range at all, via
    `_page_title()` (schema.org markup, then <h1>, then <title> minus the site's
    own name tail). This reuses that exact function rather than writing a second
    one, so a page the range crawl named "Surgical Scalpel Blade No. 9" cannot
    be named anything else here.

    ONE GET PER URL, ONCE PER DOMAIN PER RUN — and the HTML is kept, so route B
    below does not fetch the same page a second time to read its detail. That
    keeps this route's request count equal to the range crawl's, not double it.
    Running out of budget partway is a PARTIAL index, not a refusal: the names
    read so far are returned and used, exactly as numeric_slug_products() treats
    the same situation, and the rest simply miss this run.

    THE BUDGET IS THIS FUNCTION'S OWN AND NOT THE CALLER'S, for the same reason
    _sitemap_urls() above keeps its own: find_product_url() is handed a
    PER-PRODUCT deadline (PRODUCT_BUDGET_S, 15 seconds), and a whole-site index
    built inside one product's 15 seconds is not an index. Measured on the first
    real run against swann-morton.co.uk, that read 32 of 137 pages before the
    deadline and then refused the other 105 products for "no page in its name
    index publishes this product's name" — a wrong answer, not a slow one, and
    the exact failure the sitemap cache above was written to stop. The deadline
    argument is not accepted here at all, so it cannot be reintroduced by
    accident.
    """
    if domain in _NAME_INDEX:
        return _NAME_INDEX[domain]
    idx = {}
    _NAME_INDEX[domain] = idx           # set first: a partial index is still an index
    build_deadline = time.time() + NAME_INDEX_BUDGET_S
    read = failed = 0
    for u in prod_urls:
        if time.time() > build_deadline:
            print("      (name index stopped at %d of %d page(s) — out of budget)"
                  % (read + failed, len(prod_urls)), flush=True)
            break
        try:
            body, _ = base.get(u, timeout=20)
        except Exception:
            failed += 1
            continue
        name = base._page_title(body)
        if not name:
            failed += 1
            continue
        _PAGE_CACHE[u] = body
        idx.setdefault(nk(name), u)     # first wins, like the sitemap slug match
        read += 1
    print("      built a name index for %s from %d page(s) (%d unreadable)"
          % (domain, read, failed), flush=True)
    return idx


def find_product_url(domain, name, deadline):
    """Locate this product's own URL from the site's XML sitemap, by matching
    the product name against the URL's last path segment. Same discovery
    surface as crawl_supplier_site.py's sitemap route, but this keeps the
    full URL (that route discards it after deriving a name).

    `product-page` is added here, and ONLY here — never to
    crawl_supplier_site.py's global PRODUCT_PATHS — because that is the flat
    path every Wix product sits at (see this repo's route-3 Wix comment
    block). Route B below (page_product_detail -> extract_jsonld_product)
    already reads a Wix product's JSON-LD generically once it has the URL;
    the one thing missing was finding that URL at all.

    --product-path (added 05/09/2026) widens this list for ONE run, exactly as
    crawl_supplier_site.py's flag of the same name does, and for the same
    reason: a supplier whose range was captured under an operator-named segment
    (HD Clinical files its whole range under /solutions/) had no product URL
    this function could ever match, so every one of its products was held out
    of the Differentiator for "no source carries this product" however
    completely the range itself had been read. The default list is unchanged,
    so no other supplier's capture moves.

    A SITE THAT FILES PRODUCTS AT BARE IDS IS NOT MATCHED ON ITS URLs AT ALL
    (11/09/2026). swann-morton.co.uk publishes 137 products at /product/15.php
    and the like: there is no name in the URL to match, so every one of them was
    refused here and the ledger re-offered the whole supplier on every run. Those
    sites go through _name_index() above instead, which reads the name off each
    product's own page exactly as crawl_supplier_site.py already does to capture
    the range. The slug route below is untouched for every other site."""
    urls = _sitemap_urls(domain, deadline)

    segs = tuple(product_paths) if product_paths else \
        ("product", "products", "our-products", "range", "ranges", "product-page")
    pattern = r"/(%s)/" % "|".join(re.escape(x) for x in segs)
    prod = [u for u in urls if re.search(pattern, u, re.I)]
    if not prod:
        return None, "the sitemap carries no product URLs to match against"

    # A BARE-ID SITE CAN NEVER BE MATCHED ON ITS URLs. Try the page-read index
    # first on those sites — not as a fallback after the slug match, because on
    # a numeric-slug site the slug match cannot succeed and its "partial" branch
    # can only ever mis-fire (slugify("15.php") is "15-php", and "15-php"
    # contains "15", so a product literally called "15" would match the wrong
    # page).
    if _is_numeric_slug_site(prod):
        idx = _name_index(domain, prod)
        hit = idx.get(nk(name))
        if hit:
            return hit, None
        if idx:
            return None, ("this site files products at bare ids, and no page in its name "
                          "index publishes this product's name")
        return None, ("this site files products at bare ids and none of its product pages "
                      "could be read to find out what they are")

    target = slugify(name)
    if not target:
        return None, "product name has no usable slug to match against a URL"

    exact, partial = [], []
    for u in prod:
        path = urllib.parse.urlparse(u).path.strip("/").split("/")
        if not path or not path[-1]:
            continue
        seg = slugify(path[-1])
        if seg == target:
            exact.append(u)
        elif target in seg or seg in target:
            partial.append(u)
    if exact:
        return exact[0], None
    if len(partial) == 1:
        return partial[0], None
    if partial:
        return None, ("%d sitemap URLs partially match this product's slug and none matches "
                      "exactly — not guessed which one is right" % len(partial))
    return None, "no sitemap URL's slug matches this product's name"


def strip_boilerplate(html_doc):
    html_doc = re.sub(r"<(script|style|nav|header|footer)\b[^>]*>.*?</\1>", " ", html_doc,
                      flags=re.I | re.S)
    html_doc = re.sub(r'<(div|section)[^>]*class="[^"]*(cookie|consent|gdpr|banner)[^"]*"[^>]*>.*?</\1>',
                      " ", html_doc, flags=re.I | re.S)
    # Breadcrumb trails ("Home > Our Products > X") are frequently marked up as
    # an <ol>/<div> OUTSIDE <nav> — a common enough theme pattern that this is
    # worth naming explicitly, rather than a name-based guess at which list
    # items are "really" navigation.
    html_doc = re.sub(r'<(ol|ul|div)[^>]*class="[^"]*breadcrumb[^"]*"[^>]*>.*?</\1>',
                      " ", html_doc, flags=re.I | re.S)
    return html_doc


def main_content_fragment(html_doc):
    body = strip_boilerplate(html_doc)
    for pat in (r"<main\b[^>]*>(.*?)</main>",
               r"<article\b[^>]*>(.*?)</article>",
               r'<div[^>]*id="content"[^>]*>(.*?)</div>',
               r'<div[^>]*class="[^"]*(?:product-detail|product-info|entry-content|product-description)[^"]*"[^>]*>(.*?)</div>'):
        m = re.search(pat, body, re.I | re.S)
        if m:
            return m.group(1)
    return body


def extract_jsonld_product(html_doc):
    for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_doc, re.I | re.S):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue
        blocks = data if isinstance(data, list) else [data]
        expanded = []
        for b in blocks:
            if isinstance(b, dict) and isinstance(b.get("@graph"), list):
                expanded.extend(b["@graph"])
            else:
                expanded.append(b)
        for b in expanded:
            if not isinstance(b, dict):
                continue
            t = b.get("@type")
            if t == "Product" or (isinstance(t, list) and "Product" in t):
                return b
    return None


_MICRODATA_FIELDS = ("brand", "model", "manufacturer", "sku", "mpn", "material", "colour", "color")


def _itemprop(doc, prop):
    """One schema.org MICRODATA property, as text or as an attribute value.

    A property is carried either by an element's text (<span itemprop="name">X)
    or by an attribute on a void element (<meta itemprop="model" content="No. 09">,
    <img itemprop="image" src="...">). Both forms are read; neither is guessed at.
    """
    m = re.search(r'<(meta|img|link)\b[^>]*itemprop=["\']%s["\'][^>]*>' % prop, doc, re.I)
    if m:
        v = re.search(r'(?:content|src|href)=["\']([^"\']+)["\']', m.group(0), re.I)
        if v:
            return v.group(1).strip()
    m = re.search(r'<([a-zA-Z0-9]+)\b[^>]*itemprop=["\']%s["\'][^>]*>(.*?)</\1>' % prop,
                  doc, re.I | re.S)
    if m:
        v = base.clean(m.group(2))
        if v:
            return v
        inner = re.search(r'<(?:img|meta|link)\b[^>]*(?:src|content|href)=["\']([^"\']+)["\']',
                          m.group(2), re.I)
        if inner:
            return inner.group(1).strip()
    return None


def extract_microdata_product(html_doc):
    """The schema.org Product a page marks up as MICRODATA rather than JSON-LD.

    WHY (11/09/2026). Once the bare-id name index above could finally find
    swann-morton.co.uk's 137 product pages, route B read them — and produced
    navigation: "Product Ranges Product Ranges... No. 3 Range No. 4 Range Safety
    Scalpels". The site's theme puts nothing this file's main_content_fragment()
    recognises around the product copy, so the heuristic swept up the menu. That
    is worse than capturing nothing: it would have put a site menu in front of
    members as 137 product descriptions.

    The page was never short of a description. It carries a full schema.org
    Product — <body itemscope itemtype="https://schema.org/Product"> with
    itemprop name, description, brand, model and manufacturer — in microdata,
    the older of the two schema.org encodings, which extract_jsonld_product()
    above does not read. Reading it is not a heuristic: it is the site telling
    us, in a standard vocabulary, what this page is about.

    NO IMAGE IS READ FROM MICRODATA, AND THAT IS DELIBERATE. Swann Morton's only
    itemprop="image" sits inside a block its own theme has commented out
    (<!-- <span itemprop="image"><img src="..."> -->), so publishing it would put
    a picture on 137 product pages that the site itself has switched off. There
    is no dependable way to tell from here: that page carries 84 "<!--" against
    82 "-->", because of IE conditional comments, so neither stripping them nor
    counting them decides reliably whether a given match is live markup. A
    description that is one sentence about this exact blade is self-evidently the
    product's own; an image URL carries no such tell. So the image comes from
    og:image — a single unambiguous <meta> in <head> — or the product simply has
    none, which on this site is the truthful answer.

    A BREADCRUMB IS NOT A PRODUCT. A schema.org BreadcrumbList marks each crumb
    up as itemprop="name", the same attribute the Product uses, and sits above it
    in the document — the exact trap that made MIS Healthcare read as 105
    products called "Home" (see _page_title() in crawl_supplier_site.py). The
    trail is removed before anything is read.

    Returns None unless the page actually declares itself a Product, so a page
    carrying only a BreadcrumbList or an Organization block falls through to the
    heuristic below rather than being mined for stray attributes.
    """
    # Best effort only — see the docstring: this removes ordinary well-formed
    # comments, and is NOT trusted to decide anything on its own.
    doc = re.sub(r"<!--.*?-->", " ", html_doc, flags=re.S)
    if not re.search(r'itemtype=["\'][^"\']*schema\.org/Product["\']', doc, re.I):
        return None
    doc = re.sub(base._BREADCRUMB_CONTAINER, "", doc, flags=re.S | re.I)

    desc = _itemprop(doc, "description") or ""
    features = []
    for f in _MICRODATA_FIELDS:
        v = _itemprop(doc, f)
        if v and len(v) < 120:
            features.append("%s: %s" % (f.capitalize(), v))
    if not desc and not features:
        return None
    return {"description": desc, "features": features}


def og_image(html_doc):
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                  html_doc, re.I)
    return m.group(1) if m else None


def page_product_detail(url):
    # Already read while building the name index for a bare-id site — reading it
    # again would double this route's request count against the same site for
    # nothing.
    cached = _PAGE_CACHE.get(url)
    if cached is not None:
        return _detail_from_html(url, cached)
    try:
        html_doc, _ = base.get(url, timeout=25)
    except urllib.error.HTTPError as e:
        return None, "the product page returned HTTP %d" % e.code
    except Exception as e:
        return None, "the product page could not be fetched (%s)" % str(e)[:60]
    return _detail_from_html(url, html_doc)


def _detail_from_html(url, html_doc):
    """Everything page_product_detail() does once the HTML is in hand. Split out
    11/09/2026 so the bare-id name index above and the ordinary fetch share ONE
    parser — two copies would be free to drift, and this is the code that decides
    what a member reads."""
    ld = extract_jsonld_product(html_doc)
    if ld:
        desc = base.clean(ld.get("description") or "")
        img = ld.get("image")
        if isinstance(img, list):
            img = img[0] if img else None
        if isinstance(img, dict):
            img = img.get("url")
        features = []
        ap = ld.get("additionalProperty")
        if isinstance(ap, list):
            for p in ap:
                if isinstance(p, dict) and p.get("name") and p.get("value") is not None:
                    features.append("%s: %s" % (p["name"], p["value"]))
        if not desc and not features and not img:
            return None, "a JSON-LD Product block was present but carried no usable description, image or property"
        return {
            "sourceUrl": url, "parsed": "structured",
            "description": desc[:2000], "features": features[:20], "image": img or og_image(html_doc),
        }, None

    md = extract_microdata_product(html_doc)
    if md:
        return {
            "sourceUrl": url, "parsed": "structured",
            "description": md["description"][:2000], "features": md["features"][:20],
            "image": og_image(html_doc),
        }, None

    frag = main_content_fragment(html_doc)
    desc = base.clean(frag)
    if len(desc) < 40:
        return None, ("fetched the page but could not isolate usable product content from "
                      "navigation/boilerplate — refusing to guess")
    features = extract_list_items(frag)[:15]
    return {
        "sourceUrl": url, "parsed": "heuristic",
        "description": desc[:1200], "features": features, "image": og_image(html_doc),
    }, None


def capture_one(domain, name, id_index, deadline, ptype="product"):
    """Try route A, then route B. Returns (entry-fields dict, None) or (None, why)."""
    reasons = []
    if id_index is not None:
        try:
            rec, why = wp_single_product(domain, name, id_index, ptype)
        except Exception as e:
            rec, why = None, "WordPress single-product fetch failed (%s)" % str(e)[:70]
        if rec:
            return rec, None
        reasons.append("WP REST: %s" % why)

    try:
        url, why = find_product_url(domain, name, deadline)
    except Exception as e:
        url, why = None, "sitemap lookup failed (%s)" % str(e)[:70]
    if not url:
        reasons.append("sitemap: %s" % why)
        return None, "; ".join(reasons)

    try:
        rec, why = page_product_detail(url)
    except Exception as e:
        rec, why = None, "page read failed (%s)" % str(e)[:70]
    if rec:
        return rec, None
    reasons.append("page: %s" % why)
    return None, "; ".join(reasons)


def record_capture(products_store, supplier, name, entry):
    """Shared by every route (A, B and the Shopify bulk route): builds the
    stored entry, diffs it against whatever this product held last time, and
    writes it into products_store under the same key format everyone uses.
    Kept as one function so the changedSince diffing logic can't drift between
    routes — extracted 28/08/2026 when the Shopify bulk route needed the exact
    same behaviour as the existing per-product loop."""
    key = supplier + "|" + nk(name)
    new_entry = {
        "supplier": supplier,
        "product": name,
        "sourceUrl": entry["sourceUrl"],
        "capturedDate": time.strftime("%Y-%m-%d"),
        "parsed": entry["parsed"],
        "description": entry.get("description") or "",
        "features": entry.get("features") or [],
        "image": entry.get("image") or None,
    }

    old = products_store.get(key)
    is_change = False
    if old:
        diffs = [f for f in ("description", "features", "image")
                if json.dumps(new_entry.get(f), sort_keys=True) != json.dumps(old.get(f), sort_keys=True)]
        if diffs:
            new_entry["changedSince"] = {"date": old.get("capturedDate"), "changed": diffs}
            is_change = True
        elif old.get("changedSince"):
            new_entry["changedSince"] = old["changedSince"]

    products_store[key] = new_entry
    return is_change


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplier")
    ap.add_argument("--domain")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--limit", type=int, default=6, help="max SUPPLIERS to attempt (auto mode)")
    ap.add_argument("--products-limit", type=int, default=MAX_PRODUCTS_PER_SUPPLIER,
                    help="max products per supplier, per run")
    ap.add_argument("--dry-run", action="store_true")
    # A SUPPLIER WITH MORE PRODUCTS THAN 60 SECONDS BUYS HAS AN UNREACHABLE TAIL
    # (06/09/2026). The per-supplier loop below always starts at the first
    # product in the range and stops when SITE_BUDGET_S is spent, so a supplier
    # whose range is longer than that budget reaches the same prefix every run,
    # for ever: three consecutive runs against Medical Imaging Systems (MIS
    # Healthcare) each captured the identical first 36 of its 105 products, and
    # its whole PACS division — the part the Digital Diagnostic Solutions
    # framework actually needs — sits at the end of the range and could never be
    # read. The default is UNCHANGED, so the nightly --auto sweep behaves exactly
    # as before and no site is read harder without someone asking for it; this
    # flag is for an operator working one named supplier deliberately.
    ap.add_argument("--site-budget", type=int, default=SITE_BUDGET_S,
                    help="seconds of per-SUPPLIER budget (default %d). Raise it only "
                         "for a named --supplier whose range is longer than the "
                         "default budget can reach." % SITE_BUDGET_S)
    ap.add_argument("--product-path", action="append", default=[],
                    help="a URL path segment this company files products under, e.g. "
                         "--product-path solutions. Use ONLY after looking at that "
                         "site's sitemap and confirming the segment holds products "
                         "and not news or support pages. Repeatable. Mirrors the flag "
                         "of the same name on crawl_supplier_site.py.")
    ap.add_argument("--out", default=OUT,
                    help="output file (default %s). Point separate parallel "
                         "workers at separate --out files to crawl concurrently "
                         "without racing each other on the same file — two "
                         "processes both loading+saving the SAME file can silently "
                         "drop each other's captures. Merge the shard files back "
                         "into the canonical one afterwards." % OUT)
    ap.add_argument("--restart", action="store_true",
                    help="ignore the saved resume position and start every supplier "
                         "at the first product in its range. Use when you want a "
                         "deliberate re-read of a range from the top; the default "
                         "resumes where the last run stopped.")
    ap.add_argument("--cursor-file", default=None,
                    help="where the per-supplier resume position is kept (default "
                         "%s for the canonical --out, or <out>.cursor.json for a "
                         "shard). Deleting it costs nothing but a run that starts "
                         "each range at the top." % CURSOR)
    ap.add_argument("--coverage-from", default=None,
                    help="read coverage ranking (for --auto's least-covered-first "
                         "ordering) from THIS file instead of --out — use when "
                         "--out is a fresh empty shard file but you still want "
                         "auto mode to rank against the real, current coverage.")
    a = ap.parse_args()
    out_path = a.out

    global product_paths
    product_paths = a.product_path or None

    rangedoc = json.load(open(RANGE, encoding="utf-8"))
    suppliers_range = rangedoc.get("suppliers", {})

    cursor_file = a.cursor_file or cursor_path_for(out_path)
    cursors = {} if a.restart else load_cursors(cursor_file)

    coverage_path = a.coverage_from or out_path
    if os.path.exists(coverage_path):
        coverage_doc = json.load(open(coverage_path, encoding="utf-8"))
    else:
        coverage_doc = {"products": {}}
    coverage_store = coverage_doc.get("products", {})

    if os.path.exists(out_path):
        outdoc = json.load(open(out_path, encoding="utf-8"))
    else:
        outdoc = {"generated": time.strftime("%Y-%m-%d"), "products": {}}
    outdoc.setdefault("products", {})
    products_store = outdoc["products"]

    def save():
        # ATOMIC (added 21/08/2026). save() runs after every product, so a
        # process killed mid-dump left a truncated, unparseable JSON file and
        # lost the whole run's captures. Write to a temp file and rename: the
        # real file is then always either the previous complete version or the
        # new complete version, never half of one.
        outdoc["generated"] = time.strftime("%Y-%m-%d")
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(outdoc, f, indent=1, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, out_path)
        # The resume position goes down with the captures it describes. A run
        # killed part-way through would otherwise lose its position and read
        # the same slice again next time, which is the stall this fixes.
        save_cursors(cursor_file, cursors)

    if a.supplier:
        targets = [(a.supplier, a.domain or (suppliers_range.get(a.supplier) or {}).get("domain"))]
    elif a.auto:
        # RANKED BY LEAST COVERED, NOT TAKEN IN FILE ORDER. A plain "first N
        # suppliers with a domain" would hit the SAME suppliers every scheduled
        # run and never reach the rest — the exact stall crawl_supplier_site.py
        # hit and fixed on 12/08/2026. Coverage here is "how much of this
        # supplier's known range already has a detail capture, and how stale is
        # the oldest one" — least-covered and stalest first, so a weekly slice
        # advances across the whole supplier list over successive runs.
        def coverage(name):
            prods = suppliers_range[name].get("products") or []
            if not prods:
                return (1.0, "9999-99-99")
            have = [coverage_store.get(name + "|" + nk(p.get("n")))
                   for p in prods if p.get("n")]
            have = [h for h in have if h]
            ratio = len(have) / max(len(prods), 1)
            oldest = min((h.get("capturedDate") or "9999-99-99") for h in have) if have else "0000-00-00"
            return (ratio, oldest)
        names = [n for n in suppliers_range if suppliers_range[n].get("domain")]
        names.sort(key=coverage)
        targets = [(n, suppliers_range[n]["domain"]) for n in names[:a.limit]]
    else:
        sys.exit("Nothing to crawl. Pass --supplier NAME [--domain host], or --auto.")

    if not targets:
        print("Nothing to do.")
        return

    captured = skipped = changed = 0

    for supplier, domain in targets:
        if not domain:
            print("== %s: no website domain recorded — skipped" % supplier, flush=True)
            continue
        rec = suppliers_range.get(supplier) or {}
        full_range = rec.get("products") or []
        if not full_range:
            print("== %s: no products recorded in %s to look detail up for" % (supplier, RANGE), flush=True)
            continue
        resume_from = cursors.get(supplier)
        bootstrapped = False
        if not resume_from and not a.restart:
            resume_from = bootstrap_cursor(full_range, products_store, supplier)
            bootstrapped = resume_from is not None
        products, from_top = resume_slice(full_range, resume_from, a.products_limit)
        if len(full_range) > len(products):
            print("== %s: %d of %d product(s) this run, %s"
                  % (supplier, len(products), len(full_range),
                     "starting at the top of the range" if from_top
                     else "resuming after %r%s" % (resume_from,
                          " (from the last product already captured — no saved "
                          "cursor yet)" if bootstrapped else "")), flush=True)

        started = time.time()
        deadline = started + a.site_budget
        if not base.allowed(domain):
            print("== %s (%s): robots.txt disallows automated reading — skipped entirely"
                  % (supplier, domain), flush=True)
            continue

        # ---- route 0: Shopify bulk pull, one crawl for the WHOLE supplier ----
        # Probed rather than trusted from data/supplier-products.json's cached
        # "source" label, per the same reasoning as crawl_supplier_site.py's
        # own Shopify route: a platform migration would silently stale a
        # cached label, and the probe is one cheap request.
        is_shopify = False
        try:
            is_shopify = shopify_probe(domain)
        except Exception:
            is_shopify = False

        if is_shopify:
            shopify_deadline = started + SHOPIFY_BUDGET_S
            print("== %s (%s) — Shopify storefront, %d product(s) to match against ONE bulk pull"
                  % (supplier, domain, len(products)), flush=True)
            try:
                bulk = shopify_product_details(domain, shopify_deadline)
            except Exception as e:
                print("   -- bulk Shopify pull failed (%s) — supplier skipped entirely"
                      % str(e)[:100], flush=True)
                continue
            if not bulk:
                print("   -- Shopify storefront answered but exposed no usable product "
                      "records — supplier skipped entirely", flush=True)
                continue
            print("      pulled %d product record(s) from the storefront's own /products.json"
                  % len(bulk), flush=True)

            for p in products:
                name = p.get("n")
                if not name:
                    continue
                cursors[supplier] = name
                entry = bulk.get(nk(name))
                if not entry:
                    print("   -- %-40s skipped: not in this supplier's Shopify bulk pull "
                          "(name doesn't match any product title)" % name[:40], flush=True)
                    skipped += 1
                    continue
                is_change = record_capture(products_store, supplier, name, entry)
                captured += 1
                if is_change:
                    changed += 1
                tag = "CHANGED" if is_change else "OK"
                print("   %-7s %-40s %s (%s)" % (tag, name[:40], entry["sourceUrl"], entry["parsed"]),
                      flush=True)
                if not a.dry_run:
                    save()

            if not a.dry_run:
                save()
            continue    # next supplier — route A/B below is not used for Shopify

        try:
            ptype = wp_ptype(domain)
        except Exception:
            ptype = None
        id_index = None
        if ptype:
            try:
                id_index = wp_product_id_index(domain, ptype, deadline)
            except Exception as e:
                print("   (WordPress product listing could not be built: %s — falling back to "
                      "the sitemap route for every product)" % str(e)[:80], flush=True)

        print("== %s (%s) — %d product(s) to check, %s WP route"
              % (supplier, domain, len(products), "has" if id_index is not None else "no"), flush=True)

        for p in products:
            name = p.get("n")
            if not name:
                continue
            if time.time() > deadline:
                print("   -- (site time budget spent — %d product(s) left this window, "
                      "next run resumes after %r)"
                      % (len(products) - products.index(p),
                         cursors.get(supplier) or resume_from), flush=True)
                break
            # BEFORE the attempt, not after it: a product that raises, times
            # out or can never be matched must still advance the cursor, or it
            # blocks the head of the range on every future run.
            cursors[supplier] = name
            pdeadline = min(deadline, time.time() + PRODUCT_BUDGET_S)
            entry, why = capture_one(domain, name, id_index, pdeadline, ptype or "product")
            if not entry:
                print("   -- %-40s skipped: %s" % (name[:40], (why or "")[:100]), flush=True)
                skipped += 1
                continue

            is_change = record_capture(products_store, supplier, name, entry)
            captured += 1
            if is_change:
                changed += 1
            tag = "CHANGED" if is_change else "OK"
            print("   %-7s %-40s %s (%s)" % (tag, name[:40], entry["sourceUrl"], entry["parsed"]), flush=True)

            if not a.dry_run:
                save()

    if not a.dry_run:
        save()
        save_cursors(cursor_file, cursors)
    print("\n%d captured, %d skipped, %d changed since a prior capture."
          % (captured, skipped, changed))


if __name__ == "__main__":
    main()
