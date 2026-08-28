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


def wp_single_product(domain, name, id_index):
    """Fetch the ONE matching product record (by id, from the pre-built title
    index) with embedded media. Returns (record-dict, None) or (None, why)."""
    if id_index is None:
        return None, "the site's WordPress product listing could not be read"
    target = base.clean(name).lower()
    pid = id_index.get(target)
    if not pid:
        return None, "no product titled exactly %r in the site's own WordPress product listing" % name

    url = "https://%s/wp-json/wp/v2/product/%d?_embed=1" % (domain, pid)
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
    the one thing missing was finding that URL at all."""
    urls = _sitemap_urls(domain, deadline)

    prod = [u for u in urls
           if re.search(r"/(product|products|our-products|range|ranges|product-page)/", u, re.I)]
    if not prod:
        return None, "the sitemap carries no product URLs to match against"

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


def og_image(html_doc):
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                  html_doc, re.I)
    return m.group(1) if m else None


def page_product_detail(url):
    try:
        html_doc, _ = base.get(url, timeout=25)
    except urllib.error.HTTPError as e:
        return None, "the product page returned HTTP %d" % e.code
    except Exception as e:
        return None, "the product page could not be fetched (%s)" % str(e)[:60]

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


def capture_one(domain, name, id_index, deadline):
    """Try route A, then route B. Returns (entry-fields dict, None) or (None, why)."""
    reasons = []
    if id_index is not None:
        try:
            rec, why = wp_single_product(domain, name, id_index)
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
    a = ap.parse_args()

    rangedoc = json.load(open(RANGE, encoding="utf-8"))
    suppliers_range = rangedoc.get("suppliers", {})

    if os.path.exists(OUT):
        outdoc = json.load(open(OUT, encoding="utf-8"))
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
        tmp = OUT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(outdoc, f, indent=1, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, OUT)

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
            have = [products_store.get(name + "|" + nk(p.get("n")))
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
        products = (rec.get("products") or [])[:a.products_limit]
        if not products:
            print("== %s: no products recorded in %s to look detail up for" % (supplier, RANGE), flush=True)
            continue

        started = time.time()
        deadline = started + SITE_BUDGET_S
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
                print("   -- (site time budget spent — remaining products skipped this run)", flush=True)
                break
            pdeadline = min(deadline, time.time() + PRODUCT_BUDGET_S)
            entry, why = capture_one(domain, name, id_index, pdeadline)
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
    print("\n%d captured, %d skipped, %d changed since a prior capture."
          % (captured, skipped, changed))


if __name__ == "__main__":
    main()
