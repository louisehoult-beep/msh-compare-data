#!/usr/bin/env python3
"""Capture a supplier's OWN product range from its OWN website, into
data/supplier-products.json, in the shape the Company Report already renders.

WHY
---
The report's product listing has three tiers. Tier 1 (NHS Supply Chain
catalogue rows) and tier 2 (confirmed off-catalogue items) run across 183
suppliers. Tier 3 — the company's own full range, grouped by the company's own
divisions — existed for exactly ONE supplier (GBUK), because it was built by
hand. That is the gap between what the reports show and what was asked for:
"the catalogue verified per framework, then add any other not listed in
frameworks but on the company's website".

This generalises that one-off into something repeatable.

HOW IT DECIDES WHAT IT CAN READ
-------------------------------
Two routes, tried in order, and it says which one produced the result:

  1. **WordPress REST** (`/wp-json/wp/v2/`) where the site exposes a `product`
     post type with a category taxonomy. This is the best case: the company's
     own product records and its own category tree, read as data rather than
     scraped out of a layout. GBUK and Vygon both work this way.
  2. **XML sitemap**, where product URLs are grouped by their own path segment.
     Weaker — a URL path is the company's filing, but it carries no product
     record — so a sitemap crawl records `structureFrom: "sitemap"` and the
     report can say so.

If neither works — the site blocks automated reads (GE HealthCare returns 403
to everything), or exposes no product structure — the supplier gets NO entry and
the reason is printed. A half-crawl presented as a range is worse than no range:
the report states product counts, and an undercount reads as a fact.

BOTH ROUTES ARE HELD TO THE SAME TWO BARS, because both feed the same panel:
  - a capture whose products land mostly in one "Uncategorised" bucket is
    REFUSED — the report presents divisions as the company's own structure, and
    that is not one. Route 1 is not exempt: Unisurge's WordPress taxonomy holds
    "Uncategorised", "Range" and "Products", which is a flat list wearing a
    taxonomy (12/08/2026);
  - counts are de-inflated before they are written. Category landing pages are
    dropped by the prefix test, and one product is kept per (division, name) —
    Mölnlycke's sitemap lists its range once per market, 1,662 URLs for 222
    products.

WHAT IT WILL NOT DO
-------------------
- It does not invent divisions. Categories come from the company's own taxonomy
  (route 1) or its own URL structure (route 2), and `filingRule` records that
  the grouping MIRRORS the manufacturer, exactly as the GBUK entry does — a rep
  searching the way the company files will find what the company filed.
- It does not merge, tidy or reclassify. GBUK files lancets under enteral
  feeding; that stays, because it is where the company puts them.
- It never writes `notSold`. A product absent from a crawl is absent from the
  crawl; proving a company does NOT sell something needs a human (the GBUK
  tourniquet entry came from Lou, who ran that division).
- robots.txt is honoured.

Run:  python3 scripts/crawl_supplier_site.py --supplier "Vygon (UK)" --domain vygon.co.uk
      python3 scripts/crawl_supplier_site.py --auto --limit 6
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import datetime as dt
import difflib
import html as H
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import socket

# Backstop. Every fetch here passes an explicit timeout, but a library that
# opens its own connection (RobotFileParser did) would otherwise inherit "wait
# forever" — which is how three crawl runs hung for hours on one unresponsive
# host with nothing to show for it.
socket.setdefaulttimeout(25)

OUT = "data/supplier-products.json"
INDEX = "data/supplier-index.json"
SEED = "data/supplier-seed.json"
FW = "data/frameworks.json"
UA_STR = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
UA = {"User-Agent": UA_STR}
PAUSE = 0.4
MAX_PAGES = 40          # 100 products per page
# A per-site wall clock. On the first wide pass one run reached 2h25m with no
# way to see which site it was stuck on: sites time out slowly, and a large
# sitemap paginates for a long time. A crawl that cannot be observed cannot be
# trusted, so each site now gets a bounded slot and says when it runs out.
SITE_BUDGET_S = 90
MIN_PRODUCTS = 8        # below this a "range" is a landing page, not a catalogue

# A WordPress post type whose rest_base merely CONTAINS "product" is not
# necessarily a catalogue. Nevro's site exposes `product-manuals` and
# `l-product-manuals` (Product Manuals / Legacy Product Manuals) and no product
# post type at all; the old substring test matched the first of those and wrote
# 483 "products" that were warranties, clinician programmer manuals, patient
# information leaflets and MRI guidelines (checked against
# https://www.nevro.com/wp-json/wp/v2/types, 28/08/2026). A document library
# read as a range is worse than no range: the report states product counts, and
# a count of manuals reads as a count of products.
#
# The rule: an EXACT `product`/`products` type is taken as the catalogue. A
# loose match is taken only if neither its key nor its rest_base carries a word
# that marks a document library. Nothing is guessed from the records themselves.
DOC_LIBRARY_WORDS = (
    "manual", "document", "literature", "ifu", "instruction", "brochure",
    "download", "leaflet", "guide", "warrant", "datasheet", "data-sheet",
    "spec-sheet", "specsheet", "resource", "support", "faq", "video",
    "case-stud", "casestud", "white-paper", "whitepaper", "training",
    "certificat", "msds", "sds", "recall", "notice", "review", "testimonial",
    # Not documents, but the same failure: a product-named post type that holds
    # something other than the product range. Each was found live on a supplier
    # site already captured by this crawler (28/08/2026).
    "feature",      # agfa_product_feature "Product Features" — Agfa published
                    # 41 of these as its range: "Cloud Native Architecture",
                    # "Interoperability-Based APIs", "RUBEE(R) Inside"
    "jp_pay",       # Jetpack "Pay with PayPal" buttons — present on 5 sites
    "tab",          # neve_product_tabs, a theme's product-tab content
    "widget", "block-", "addon", "add-on", "attribute", "variation",
)


# ---------------------------------------------------------------------------
# A SITE WITH TWO GENUINE CATALOGUES (29/08/2026)
#
# The crawler reads ONE post type per site. Where a company files its range
# across two real catalogues, whichever one is picked, the report states a
# partial range as the whole — a count that reads as a fact. Joint Operations
# was doing exactly that: `product` ("Surgical Products", 109 records) and
# `product-recovery` ("Recovery Products", 46) are both genuine catalogues, and
# the report carried 46 of 155.
#
# THE RULE: a second post type is merged ONLY where it is named here, and it is
# named here only on evidence read live from that site — its own type registry
# calls it a product type, it holds a catalogue's worth of records, and its
# titles do NOT overlap the primary type's. A wider deny/allow list is not a
# safe substitute: of the 72 WordPress-route suppliers, 9 expose more than one
# product-named type and on 8 of them the second is a platform artefact
# (Jetpack payment buttons, theme tabs, feature blurbs), which is why
# DOC_LIBRARY_WORDS exists at all.
#
# CHECKED LIVE 29/08/2026 against each site's /wp-json/wp/v2/types and the
# x-wp-total of each type:
#
#   jointoperations.co.uk   product 109 + product-recovery 46 = 155.
#                           0 of 46 recovery titles appear in the surgical
#                           range (compared on normalised titles). Two ranges,
#                           no double count — MERGED.
#
#   www.benmormedical.co.uk product 68 + rentalproduct 46. NOT MERGED, and the
#                           near case is recorded here so the next pass does not
#                           re-open it: 28 of the 45 distinct `rentalproduct`
#                           titles are already in `product` ("Bariatric
#                           Community Bed", "Freeway Commode", "Flojac"...).
#                           That type is a RENTAL OFFER of goods the catalogue
#                           already lists, not a second catalogue. Merging it
#                           would publish 28 products twice and overstate the
#                           range by 60%.
#
# An entry here is a claim about one company's site. It is not carried forward
# unchecked: `postTypes` on the capture records which types were actually read,
# and verify.py fails the file if a merged site's capture drops back to one.
SECOND_CATALOGUE = {
    "jointoperations.co.uk": ("product-recovery",),
}


def extra_product_types(domain, types, primary):
    """Evidenced second catalogues for this domain, as declared in SECOND_CATALOGUE.

    Only types the site's OWN registry still exposes are returned, so a company
    that retires a post type stops being merged rather than failing the run.
    """
    want = SECOND_CATALOGUE.get((domain or "").lower(), ())
    out = []
    for key, val in (types or {}).items():
        base = (val or {}).get("rest_base") or key
        if base == primary:
            continue
        if base in want or key in want:
            out.append((base, (val or {}).get("taxonomies") or []))
    return out


def pick_product_type(types):
    """Choose the WordPress post type that is the company's product catalogue.

    Returns (rest_base, taxonomies, None) on success, or (None, None, reason)
    where reason says which of the two ways it failed, because "no product post
    type" and "only a document library" are different findings and the refusal
    record should not blur them.
    """
    loose = None
    rejected = []
    for key, val in (types or {}).items():
        val = val or {}
        base = val.get("rest_base") or key
        taxes = val.get("taxonomies") or []
        if key.lower() in ("product", "products") or base.lower() in ("product", "products"):
            return base, taxes, None
        if "product" not in base.lower() and "product" not in key.lower():
            continue
        haystack = ("%s %s %s" % (key, base, val.get("name") or "")).lower()
        if any(w in haystack for w in DOC_LIBRARY_WORDS):
            rejected.append(base)
            continue
        if loose is None:
            loose = (base, taxes)
    if loose:
        return loose[0], loose[1], None
    if rejected:
        return None, None, ("the site's WordPress API exposes no product catalogue \u2014 its only "
                            "product-named post types are document libraries (%s), which hold "
                            "manuals and leaflets, not a product range"
                            % ", ".join(sorted(set(rejected))))
    return None, None, "the site's WordPress API exposes no product post type"


def get(url, as_json=False, timeout=30):
    time.sleep(PAUSE)
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
    raw = r.read()
    if as_json:
        return json.loads(raw.decode("utf-8", "replace")), dict(r.headers)
    return raw.decode("utf-8", "replace"), dict(r.headers)


def allowed(domain, path="/"):
    """Honour robots.txt — and never hang on it.

    RobotFileParser.read() opens its OWN connection with NO timeout. A host that
    accepts the connection and then goes quiet stalls the entire run, which is
    exactly what happened three times: 2h25m, 26m and 2h50m, each with nothing
    captured. The file is fetched here instead, with a timeout, and handed to
    the parser as text.
    """
    rp = urllib.robotparser.RobotFileParser()
    try:
        body, _ = get("https://%s/robots.txt" % domain, timeout=12)
    except urllib.error.HTTPError as e:
        # RobotFileParser.read() treats 401 and 403 as DISALLOW ALL, and it is
        # right to: a site that refuses to show its robots.txt is not inviting a
        # crawler. Rewriting the fetch lost that rule and briefly had this
        # trying sites that had said no — GE HealthCare serves 403 here.
        if e.code in (401, 403):
            return False
        return True                     # 404 and friends = nothing to obey
    except Exception:
        return True                     # unreachable = nothing to obey

    # WHAT CAME BACK MUST ACTUALLY BE A robots.txt.
    # Sites behind a bot filter answer this path with an HTML block page —
    # Medtronic used to return "Incorrect Browser" — and HTML parses as a
    # robots file with NO rules, i.e. "crawl anything". That is precisely
    # backwards: a site serving a block page is refusing. If the response is
    # not plainly a robots file, treat it as a refusal — UNLESS it turns out
    # to be case 2 below.
    head = body.lstrip()[:400].lower()
    looks_like_html = "<html" in head or "<!doctype" in head
    if looks_like_html or (body.strip() and "user-agent" not in body.lower()):
        # SECOND CASE, found 22/08/2026 (OUTSTANDING ^o99): a single-page-app
        # site answers EVERY unknown path with its own homepage HTML and
        # HTTP 200, including /robots.txt. There is no robots file and
        # nothing has refused anything — Mediq Healthcare UK is the worked
        # example, on both www.mediq.co.uk and mediq.co.uk. The block-page
        # rule above cannot tell the two cases apart from the /robots.txt
        # response alone, so when the response looks like HTML, compare it
        # against the site's own homepage: near-identical means "this is
        # just the homepage, there is no robots.txt", not a refusal.
        # Different means it is a genuine block page and the refusal stands.
        try:
            home, _ = get("https://%s/" % domain, timeout=12)
        except Exception:
            return False                # can't confirm which case; stay cautious
        ratio = difflib.SequenceMatcher(None, body, home).ratio()
        if ratio >= 0.99:
            return True                 # SPA fallback homepage, not a refusal
        return False                    # genuinely different HTML: a block page

    rp.parse(body.splitlines())
    return rp.can_fetch(UA_STR, "https://%s%s" % (domain, path))


def clean(s):
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())



# ---------------------------------------------------------------- route 0
# SHOPIFY, added 27/08/2026.
#
# WHY THIS ROUTE HAD TO EXIST. Every Shopify storefront serves its products at
# a FLAT `/products/<handle>` URL — the platform has no per-category product
# path, by design. Route 2 reads a division out of the URL path segment above
# the leaf, so on a Shopify site there is never one to read and EVERY product
# lands in "Uncategorised". That is not a finding about the supplier's filing;
# it is this crawler reading the wrong place. Eleven suppliers in the held list
# were Shopify — Farla Medical (6,992), Scala Surgical (6,726), Appleton Woods
# (5,616), Nine Group, Trulife, Bailey Instruments, MedScience, Blink Medical,
# Gailarde, Empire Medical and Unigloves — 22,364 products filed as
# "Uncategorised" by a platform quirk, with the real filing sitting in public
# JSON the crawler never asked for.
#
# WHERE THE REAL FILING LIVES. Shopify publishes two of them, without auth:
#   * `product_type` on each product record in /products.json — a single free
#     text field the merchant fills in, and
#   * COLLECTIONS (/collections.json, /collections/<handle>/products.json) —
#     the browse structure a customer actually navigates.
# Neither is reliably the better one, so the route MEASURES which is, per site,
# under a stated rule rather than a per-site override (root rule 14).
#
# THE RULE, and why each half of it is there:
#   `product_type` is used only when it is stated for >= 80% of the catalogue
#   AND its single commonest value covers <= 50% of it. The first half rejects
#   a field the merchant never filled in (Appleton Woods: stated on 11%). The
#   second rejects one filled in with a CLASS rather than a division (Scala
#   Surgical: 100% stated, but 89% of the range is the single word "Surgical
#   Instrument", which groups nothing). Farla Medical passes both — 100%
#   stated, commonest value 4% — and its 636 values are real categories
#   ("Medical Trolleys", "Consulting Rooms", "Continence Care").
#   Otherwise collection membership is used.
#
# A BRAND IS NOT A CATEGORY, and it is separated on evidence, not on its name.
# Farla files 910 collections, a large share of them one per manufacturer it
# resells (3M, A&D Medical, Behrens). Reading the titles to guess which are
# brands is the guesswork this crawler refuses everywhere else, so instead a
# collection is judged a brand collection when >= 90% of its products share one
# `vendor` AND the collection title matches that vendor. That is the site's own
# data answering the question.
#
# WHICH COLLECTION WINS when a product sits in several: the SMALLEST. A product
# in both "Sale" and "Artery Forceps" is an artery forceps that happens to be
# discounted, and the smaller collection is the more specific claim. This also
# keeps merchandising mega-collections ("All Products", "Clearance") from
# swallowing a range whose real filing is right beside them.
#
# It does not publish a partial catalogue. A sweep that runs out of budget
# mid-way REFUSES, because the report prints the product count as a fact about
# the company's range and a truncated sweep reads as an undercount, not as a
# missing crawl.
SHOPIFY_BUDGET_S = 1200     # a 500-collection sweep is ~500 requests at PAUSE

# product_type is trusted as the division only if it is filled in this widely...
SHOPIFY_TYPE_MIN_STATED = 0.80
# ...and does not collapse the whole range into one value.
SHOPIFY_TYPE_MAX_TOPSHARE = 0.50
# ...and does not simply restate the product name. Trulife fills product_type in
# on 96% of its range with 413 distinct values across 491 products — a field
# that names almost every item individually groups nothing, which is the same
# failure as Scala's single value at the other extreme (27/08/2026).
SHOPIFY_TYPE_MAX_DISTINCT_RATIO = 0.50
# A collection whose products are this dominated by one vendor, and named for
# that vendor, is a brand shelf rather than a category.
SHOPIFY_BRAND_VENDOR_SHARE = 0.90


def _norm_brand(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _shopify_paged(domain, path, key, deadline=None, cap=200):
    """Walk Shopify's ?page= pagination to the end, or say it could not."""
    out, page = [], 1
    while page <= cap:
        if deadline and time.time() > deadline:
            raise RuntimeError("budget exhausted after %d page(s) of %s" % (page - 1, path))
        j, _ = get("https://%s%s%spage=%d&limit=250"
                   % (domain, path, "&" if "?" in path else "?", page), as_json=True)
        chunk = j.get(key) or []
        out += chunk
        if len(chunk) < 250:
            break
        page += 1
    return out


def shopify_products(domain, deadline=None):
    """Read a Shopify storefront's own product records and its own filing."""
    try:
        probe, _ = get("https://%s/collections.json?limit=1" % domain, as_json=True)
    except Exception as e:
        return None, "not a readable Shopify storefront (%s)" % str(e)[:50]
    if "collections" not in probe:
        return None, "not a Shopify storefront"

    prods = _shopify_paged(domain, "/products.json", "products", deadline=deadline)
    if len(prods) < MIN_PRODUCTS:
        return None, ("the Shopify storefront returned %d product(s), too few to be a "
                      "catalogue" % len(prods))

    # ---- which of the two filings does this site actually keep? -------------
    types = [clean(p.get("product_type")) for p in prods]
    stated = [t for t in types if t]
    share_stated = len(stated) / float(len(prods))
    topshare = 0.0
    if stated:
        topshare = max(stated.count(t) for t in set(stated)) / float(len(prods))
    distinct_ratio = len(set(stated)) / float(len(prods)) if stated else 1.0
    use_type = (share_stated >= SHOPIFY_TYPE_MIN_STATED
                and topshare <= SHOPIFY_TYPE_MAX_TOPSHARE
                and distinct_ratio <= SHOPIFY_TYPE_MAX_DISTINCT_RATIO)
    print("      shopify: %d products, product_type stated on %.0f%%, commonest value "
          "%.0f%% of range, %.0f%% distinct -> division from %s"
          % (len(prods), 100 * share_stated, 100 * topshare, 100 * distinct_ratio,
             "product_type" if use_type else "collections"), flush=True)

    divisions, plist = {}, []
    brand_shelves = 0
    if use_type:
        source_note = "the company's own product_type on each product record"
        for p in prods:
            name = clean(p.get("title"))
            div = clean(p.get("product_type")) or "Uncategorised"
            if not name or len(name) < 3:
                continue
            divisions[div] = divisions.get(div, 0) + 1
            plist.append({"n": name, "division": div, "category": ""})
    else:
        source_note = "the company's own collections (its published browse structure)"
        cols = _shopify_paged(domain, "/collections.json", "collections", deadline=deadline)
        vendor_of = {p.get("id"): clean(p.get("vendor")) for p in prods}
        # collection handle -> set of product ids, minus the brand shelves
        member = {}
        for c in cols:
            h, title = c.get("handle"), clean(c.get("title"))
            if not h or not title:
                continue
            try:
                cp = _shopify_paged(domain, "/collections/%s/products.json" % h,
                                    "products", deadline=deadline)
            except urllib.error.HTTPError:
                continue        # a collection listed but not served is not a division
            ids = [p.get("id") for p in cp]
            if not ids:
                continue
            vend = [vendor_of.get(i, "") for i in ids]
            named = [v for v in vend if v]
            if named:
                top = max(set(named), key=named.count)
                if (named.count(top) / float(len(ids)) >= SHOPIFY_BRAND_VENDOR_SHARE
                        and _norm_brand(top) and _norm_brand(top) == _norm_brand(title)):
                    brand_shelves += 1
                    continue
            member[title] = ids
        if brand_shelves:
            print("      dropped %d collection(s) that are a manufacturer's brand shelf, not a "
                  "category — the collection is named for the vendor that supplies >=%d%% of it"
                  % (brand_shelves, int(100 * SHOPIFY_BRAND_VENDOR_SHARE)), flush=True)
        # smallest collection wins: the more specific claim about the product
        best = {}
        for title, ids in sorted(member.items(), key=lambda kv: -len(kv[1])):
            for i in ids:
                best[i] = title
        for p in prods:
            name = clean(p.get("title"))
            if not name or len(name) < 3:
                continue
            div = best.get(p.get("id")) or "Uncategorised"
            divisions[div] = divisions.get(div, 0) + 1
            plist.append({"n": name, "division": div, "category": ""})

    if not plist:
        return None, "the Shopify storefront exposed no readable product records"

    real = [d for d in divisions if d != "Uncategorised"]
    uncat = divisions.get("Uncategorised", 0)
    has_divisions = bool(real) and uncat * 2 <= len(plist)
    flat_note = ("" if has_divisions else
                 "%d of %d products carry neither a product_type nor a category collection on "
                 "the company's own storefront, so most of the range sits in one unsorted "
                 "'Uncategorised' list rather than the company's own grouping"
                 % (uncat, len(plist)))
    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": "%s Shopify storefront product records, read this run" % domain,
        "structureFrom": source_note,
        "hasDivisions": has_divisions,
        "structure": "The company's own product filing, as published on its storefront."
                     if has_divisions else
                     "No usable grouping on the storefront — listed as one flat range.",
        "filingRule": (("Grouping MIRRORS the manufacturer's own filing, read from %s. Where a "
                        "product sits under a heading that reads oddly clinically, that is where "
                        "the company files it, and a rep searching the company's way will find it "
                        "there." % source_note)
                       if has_divisions else
                       ("Read from the storefront's own product records, so names are exact. "
                        + flat_note + " — every item is listed by name below rather than grouped, "
                        "because a fabricated grouping would misrepresent the company's own "
                        "filing.")),
        "divisions": [{"name": k, "products": v}
                      for k, v in sorted(divisions.items(), key=lambda kv: -kv[1])],
        "products": plist,
    }, None

# ---------------------------------------------------------------- route 1
def _wp_read_type(base, ptype, taxes, deadline=None):
    """Read one post type: its own category taxonomy, then its records.

    Category ids are namespaced by post type. Two post types on the same site
    carry two SEPARATE taxonomies (Joint Operations: `surgical` and `recovery`),
    and their term ids start at 1 in both — merging them on the raw id would
    file a surgical product under a recovery division.
    """
    tax = None
    for t in taxes:
        if "cat" in t.lower():
            tax = t
            break

    cats = {}
    if tax:
        page = 1
        while page <= 10:
            try:
                items, _ = get("%s/%s?per_page=100&page=%d" % (base, tax, page), as_json=True)
            except urllib.error.HTTPError:
                break
            if not items:
                break
            for c in items:
                cats["%s:%s" % (ptype, c["id"])] = {
                    "name": clean(c.get("name")),
                    "parent": ("%s:%s" % (ptype, c["parent"])) if c.get("parent") else 0,
                    "count": c.get("count") or 0}
            if len(items) < 100:
                break
            page += 1

    products, page = [], 1
    while page <= MAX_PAGES:
        if deadline and time.time() > deadline:
            break                       # keep what has been read, stop fetching
        try:
            items, _ = get("%s/%s?per_page=100&page=%d&_fields=id,title,%s"
                           % (base, ptype, page, tax or "id"), as_json=True)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                break                   # past the last page
            raise
        if not items:
            break
        for p in items:
            name = clean((p.get("title") or {}).get("rendered"))
            if not name:
                continue
            ids = ["%s:%s" % (ptype, i) for i in (p.get(tax) or [])] if tax else []
            products.append({"n": name, "cats": ids})
        if len(items) < 100:
            break
        page += 1
    return products, cats


def wp_products(domain, deadline=None):
    base = "https://%s/wp-json/wp/v2" % domain
    types, _ = get(base + "/types", as_json=True)
    ptype, taxes, why = pick_product_type(types)
    if not ptype:
        return None, why

    products, cats = _wp_read_type(base, ptype, taxes, deadline=deadline)
    read = [ptype]

    # A SECOND GENUINE CATALOGUE, only where this domain is named in
    # SECOND_CATALOGUE on evidence read from that site. Nothing is inferred
    # from the type names here.
    for xtype, xtaxes in extra_product_types(domain, types, ptype):
        if deadline and time.time() > deadline:
            break
        xprod, xcats = _wp_read_type(base, xtype, xtaxes, deadline=deadline)
        if not xprod:
            continue
        products += xprod
        cats.update(xcats)
        read.append(xtype)

    if len(products) < MIN_PRODUCTS:
        return None, ("only %d product records on the site's API — that is a landing page, not a "
                      "catalogue" % len(products))
    return {"products": products, "cats": cats, "postTypes": read}, None


def top_level(cid, cats):
    """Walk a category to its root, so products group under the company's own top divisions."""
    seen = set()
    while cid and cid in cats and cats[cid]["parent"] and cid not in seen:
        seen.add(cid)
        cid = cats[cid]["parent"]
    return cid


# WordPress's own default term. It is not a category name a company chose — it
# is the platform's word for "none was set" — so where a product carries it
# ALONGSIDE a real one, the real one is the company's filing.
WP_DEFAULT_TERMS = ("uncategorised", "uncategorized")


def shape_from_wp(raw, domain):
    cats, products = raw["cats"], raw["products"]
    post_types = raw.get("postTypes") or []

    # WHICH ROOT WINS WHEN A PRODUCT SITS UNDER SEVERAL (fixed 27/08/2026).
    # This used to be `roots[0]` — whichever term WordPress happened to return
    # first, which is an ordering accident, not a filing decision. Three sites
    # published a meaningless division that way, because each keeps a
    # CROSS-CUTTING root beside its real product tree and every product is in
    # both: Renray Healthcare files 321 products under "Sectors" (Care Home,
    # Hospital, Community — the market it sells to, not what the thing is)
    # while its real roots Furniture, Seating, Beds and Pressure Area Care sat
    # unused; Hospital Services Limited published 303 under "Brands" (Canon,
    # Barco, Bayer) over its real Ophthalmology, Xray and Surgical Equipment
    # roots; Inspiration Healthcare published 132 under "Products".
    #
    # THE RULE: the root that covers the SMALLEST share of the catalogue wins.
    # A cross-cutting axis is by definition one nearly every product carries,
    # so it discriminates nothing; the root that applies to fewer products is
    # the more specific claim about this one. This is the same principle the
    # Shopify route applies to overlapping collections, and it reads no term
    # names to reach it — "Sectors" loses to "Seating" on coverage, not on
    # anybody's opinion of the two words.
    # A ROOT THAT HOLDS THE WHOLE CATALOGUE IS A CONTAINER, NOT A DIVISION.
    # Inspiration Healthcare files its entire range under one root term called
    # "Products", whose two children are "Acute Care" (66) and "Infusion
    # therapies" (43) — the real divisions, one level down. Publishing
    # "Products" as the company's structure states nothing; it is the same
    # failure as "Sectors", reached by a different route, so it is answered by
    # the same test — a level that separates nothing is not a level. Where such
    # a root exists its children are promoted and the walk repeats, so a site
    # nested two containers deep resolves too.
    for _ in range(4):
        cov = {}
        for p in products:
            for r in {top_level(c, cats) for c in p["cats"] if top_level(c, cats) in cats}:
                cov[r] = cov.get(r, 0) + 1
        # ONLY when it is the sole root in the catalogue. An earlier version
        # fired on any root covering >=95%, which was wrong in both directions:
        # it promoted Renray's "Sectors" children (so a wing-back chair filed as
        # "Hospital" instead of "Seating") and HSL's "Brands" children (so every
        # division became a manufacturer name), while still missing Inspiration
        # at 94.96%. Where a site has other roots, the coverage rule below
        # already picks the right one and this must not interfere; the container
        # case is specifically a tree with NOTHING to choose between.
        swollen = ([r for r in cov if any(c["parent"] == r for c in cats.values())]
                   if len(cov) == 1 else [])
        if not swollen:
            break
        for r in swollen:
            print("      '%s' is the only root in the catalogue and holds all %d products — a "
                  "container, not a division; its sub-categories are used instead"
                  % (cats[r]["name"], cov[r]), flush=True)
            for c in cats.values():
                if c["parent"] == r:
                    c["parent"] = 0

    cover = {}
    for p in products:
        for r in {top_level(c, cats) for c in p["cats"] if top_level(c, cats) in cats}:
            cover[r] = cover.get(r, 0) + 1

    divisions, plist = {}, []
    for p in products:
        names = [cats[c]["name"] for c in p["cats"] if c in cats]
        rids = list({top_level(c, cats) for c in p["cats"] if top_level(c, cats) in cats})
        real = [r for r in rids if cats[r]["name"].strip().lower() not in WP_DEFAULT_TERMS]
        if real:
            rids = real
        rid = min(rids, key=lambda r: (cover.get(r, 0), cats[r]["name"])) if rids else None
        div = cats[rid]["name"] if rid else "Uncategorised"
        cat = names[0] if names else ""
        divisions[div] = divisions.get(div, 0) + 1
        plist.append({"n": p["n"], "division": div, "category": cat})

    # THE FLATNESS BAR APPLIES TO THIS ROUTE TOO. It used to guard only the
    # sitemap route, on the assumption that a site exposing a `product` post type
    # necessarily files its products under a real taxonomy. Unisurge disproved
    # that on 12/08/2026: its WordPress taxonomy holds three terms —
    # "Uncategorised" (25), "Range" (16) and "Products" (3) — so a capture would
    # have published "44 products across 3 divisions: Uncategorised, Products,
    # Range" as the company's own structure, on a member-facing report, for a
    # company whose real range is procedure packs by speciality. Reading the term
    # NAMES to judge them would be guesswork; the same structural test the
    # sitemap route already uses catches it without any name judgement.
    # Lou's call, 25/08/2026: a flat/near-flat taxonomy no longer refuses the
    # capture outright — it publishes the list with `hasDivisions: False` and
    # says so, rather than withholding a real product list over grouping.
    real = [d for d in divisions if d != "Uncategorised"]
    uncat = divisions.get("Uncategorised", 0)
    has_divisions = bool(real) and uncat * 2 <= len(plist)
    flat_note = (
        "" if has_divisions else
        ("the site's product taxonomy put every product in one 'Uncategorised' bucket, so it "
         "carries no division structure — shown as one unsorted list, not the company's own "
         "filed grouping" if not real else
         "%d of %d products carry no category in the site's own taxonomy, so most of the range "
         "sits in one unsorted 'Uncategorised' list rather than the company's own grouping"
         % (uncat, len(plist)))
    )

    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": (("%s product catalogue (WordPress REST API), read this run" % domain)
                   if len(post_types) < 2 else
                   ("%s product catalogue (WordPress REST API), read this run \u2014 the site files "
                    "its range across %d separate catalogues (%s) and all were read"
                    % (domain, len(post_types), ", ".join(post_types)))),
        "postTypes": post_types,
        "structureFrom": "the company's own product category taxonomy",
        "hasDivisions": has_divisions,
        "structure": "The company's own top-level product categories." if has_divisions else
                     "No usable category structure in the site's own taxonomy — listed as one flat range.",
        "filingRule": (("Grouping MIRRORS the manufacturer's own filing. Where a product sits "
                       "under a category that reads oddly clinically, that is where the company "
                       "files it, and a rep searching the company's way will find it there.")
                       if has_divisions else
                       ("Read from the site's own product records, so names are exact. " + flat_note +
                        " — every item is listed by name below rather than grouped, because a "
                        "fabricated grouping would misrepresent the company's own filing.")),
        "divisions": [{"name": k, "products": v}
                      for k, v in sorted(divisions.items(), key=lambda kv: -kv[1])],
        "products": plist,
    }, None


# ---------------------------------------------------------------- route 2
# Path segments that mark a URL as a product page. The default list is the
# generic one; a supplier whose site files by CLINICAL AREA instead is given its
# own segment explicitly via --product-path, never by widening this list.
#
# WHY IT IS NOT WIDENED GLOBALLY (26/08/2026). Coloplast files wound products
# under /wound/, B. Braun under its own therapy paths, Mölnlycke under
# /wound-care/. None contain the word "product", so all three were refused with
# "the sitemap carries 0 product URLs" — read as three sites with no readable
# catalogue when in fact each publishes a full one. But matching ANY path
# segment is not the fix: a sitemap's other segments are news, events, support
# and careers, and sweeping those in would publish press releases as products.
# So the operator names the segment, having looked at that company's sitemap,
# and the capture records which segment it was told to read.
PRODUCT_PATHS = ("product", "products", "our-products", "range", "ranges")


def sitemap_products(domain, deadline=None, product_paths=None):
    seen, urls = set(), []
    to_read = ["https://%s/sitemap.xml" % domain, "https://%s/sitemap_index.xml" % domain]
    while to_read and len(seen) < 12:
        if deadline and time.time() > deadline:
            return None, ("gave up while reading the sitemap — the site answers too slowly to "
                          "crawl inside its budget")
        u = to_read.pop(0)
        if u in seen:
            continue
        seen.add(u)
        try:
            body, _ = get(u)
        except Exception:
            continue
        # Locs come either bare (<loc>url</loc>) or CDATA-wrapped
        # (<loc><![CDATA[url]]></loc>) — All in One SEO (Altomed and others)
        # uses the CDATA form, which the bare-URL regex silently matched zero
        # times, so the whole sitemap read looked empty. Extract the raw loc
        # body first, then unwrap CDATA if present.
        raw_locs = re.findall(r"<loc>(.*?)</loc>", body, re.S)
        locs = []
        for raw in raw_locs:
            raw = raw.strip()
            m = re.match(r"<!\[CDATA\[(.*?)\]\]>", raw, re.S)
            locs.append(m.group(1).strip() if m else raw)
        if "<sitemapindex" in body[:400].lower():
            # BUG FIXED 26/08/2026: "sitemap" is a substring of every sub-sitemap
            # URL (they all end "...-sitemap.xml"), so the old filter was a
            # no-op — it kept document order and just took the first 8 entries.
            # For Direct Healthcare Group that meant post-sitemap, page-sitemap
            # and attachment-sitemap pages, never reaching the real
            # products-sitemap.xml at all. Worse: WordPress media attachments
            # get URLs nested under their parent product's own path
            # (/products/<product>/<image-slug>/), which the path-segment match
            # below cannot tell apart from a real product page — so reading an
            # attachment sitemap by mistake doesn't just miss products, it
            # publishes gallery images and spec-sheet PDFs AS products (84 real
            # ranges inflated to 408 rows, caught in the Patient Handling
            # pre-review sweep). Attachment/media/download/event/category/tag/
            # author sitemaps are excluded outright, never just deprioritised;
            # sub-sitemaps whose own name says "product" are read first.
            EXCLUDE_SITEMAP_HINTS = ("attachment", "media", "author", "category",
                                      "tag", "download", "event", "swatch",
                                      "distributor", "bitforms", "home-slider")
            candidates = [l for l in locs if "sitemap" in l.lower()
                          and not any(h in l.lower() for h in EXCLUDE_SITEMAP_HINTS)]
            candidates.sort(key=lambda l: 0 if "product" in l.lower() else 1)
            to_read.extend(candidates[:8])
            continue
        urls.extend(locs)

    segs = tuple(product_paths) if product_paths else PRODUCT_PATHS
    pat = r"/(%s)/" % "|".join(re.escape(x) for x in segs)
    prod = [u for u in urls if re.search(pat, u, re.I)]
    if len(prod) < MIN_PRODUCTS:
        return None, ("the sitemap carries %d URLs under %s, too few to call a catalogue"
                      % (len(prod), "/" + "/, /".join(segs) + "/"))

    # A LANDING PAGE IS A PREFIX OF OTHER PAGES. This is the structural test, and
    # it is the one that matters: the old code took the last URL segment as a
    # product name, so every intermediate CATEGORY page became a product. Steris
    # published "Specialty", "Returned Equipment" and a whole "Certified Pre
    # Owned" division that way; Mindray published "High Acuity" and "Mid Low
    # Acuity", which are the headings ABOVE its monitors, not monitors.
    #
    # Nothing here reads the names. If /a/b/ is a strict prefix of /a/b/c/ then
    # /a/b/ is the page you pass through, not the thing you arrive at. Judging by
    # name — dropping anything that "looks like a category" — is guesswork that
    # would take real products with generic names down with it.
    paths, has_root = [], False
    for u in prod:
        path = urllib.parse.urlparse(u).path.strip("/").split("/")
        try:
            i = next(n for n, seg in enumerate(path)
                     if any(seg.lower() == x.lower() for x in segs))
        except StopIteration:
            continue
        rest = path[i + 1:]
        if rest:
            paths.append((path[:i], rest))
            if not path[:i]:
                has_root = True

    # A MULTI-MARKET SITE PUBLISHES THE SAME CATALOGUE ONCE PER LOCALE, NESTED
    # UNDER A COUNTRY/LANGUAGE PREFIX BEFORE THE PRODUCT SEGMENT — Direct
    # Healthcare Group's /da/products/…, /fi/products/…, /sv/products/… sit
    # alongside its plain /products/… range and carry DIFFERENT (translated)
    # slugs, so the existing same-name dedup below cannot catch them: 823 URLs
    # collapsed to 647 "products" that were still 260-odd real ranges' worth of
    # foreign-locale duplicates (26/08/2026, Patient Handling pre-review sweep).
    # Only fires when a root, unprefixed catalogue is actually confirmed to
    # exist for this site — sites that nest EVERYTHING under one locale
    # (e.g. always /uk/products/…) never trip `has_root` and fall through to
    # the unchanged behaviour below.
    dropped_locale = 0
    if has_root:
        kept = [(pre, rest) for pre, rest in paths if not pre]
        dropped_locale = len(paths) - len(kept)
        paths = kept
    paths = [rest for _, rest in paths]
    if dropped_locale:
        print("      dropped %d locale-prefixed duplicate URL(s) — a plain, unprefixed "
              "catalogue exists for this site so the country/language-prefixed copies "
              "are not counted as extra products" % dropped_locale, flush=True)
    prefixes = {tuple(r[:k]) for r in paths for k in range(1, len(r))}

    divisions, plist = {}, []
    landing = 0
    for rest in paths:
        if tuple(rest) in prefixes:
            landing += 1
            continue
        name = rest[-1].replace("-", " ").strip().title()
        div = (rest[0].replace("-", " ").strip().title() if len(rest) > 1 else "Uncategorised")
        if not name or len(name) < 3:
            continue
        # A "browse everything" landing page (/products/all/, /products/all-products/)
        # sits at the SAME path depth as real products, so the prefix test above
        # cannot catch it — nothing else is nested under it. Found on Welland
        # Medical's site (26/08/2026) alongside the sitemap-selection bug fix.
        # Deliberately just these two generic phrases, never a wider word list —
        # a real product legitimately named "Urostomy" or similar single-word
        # clinical term must never be silently dropped on a guess.
        if name.lower() in ("all", "all products"):
            continue
        divisions[div] = divisions.get(div, 0) + 1
        plist.append({"n": name, "division": div, "category": ""})
    if landing:
        print("      dropped %d category landing page(s) that are a prefix of other product URLs"
              % landing, flush=True)

    # A sitemap lists every page, including the CATEGORY landing pages. Those are
    # not products, and counting them inflates a number the report prints as a
    # fact. Drop any entry whose name is just a division name.
    divnames = {d.lower() for d in divisions}
    before = len(plist)
    plist = [p for p in plist if p["n"].lower() not in divnames]
    for d in list(divisions):
        divisions[d] = sum(1 for p in plist if p["division"] == d)
        if not divisions[d]:
            del divisions[d]
    dropped = before - len(plist)

    # ONE PRODUCT PER (DIVISION, NAME), BECAUSE A SITEMAP LISTS MARKETS, NOT ONLY
    # PRODUCTS. Mölnlycke's sitemap carries the same range once per locale:
    # 1,662 product URLs resolving to 222 distinct names, 'Aperture Drapes'
    # sixteen times over. The report prints the product count as a fact about the
    # company's range, so publishing 1,662 would overstate it more than sevenfold
    # — the same failure as the landing pages that inflated Getinge to 1,333,
    # arriving by a different road. Counting a genuine same-name pair once is an
    # undercount of one; counting locales is an overcount of everything.
    deduped, seen_np = [], set()
    for p in plist:
        k = (p["division"], p["n"].lower())
        if k in seen_np:
            continue
        seen_np.add(k)
        deduped.append(p)
    duplicate_urls = len(plist) - len(deduped)
    if duplicate_urls:
        print("      dropped %d duplicate product URL(s) resolving to a name already captured "
              "in the same division (locale or market variants)" % duplicate_urls, flush=True)
        plist = deduped
        for d in list(divisions):
            divisions[d] = sum(1 for p in plist if p["division"] == d)
            if not divisions[d]:
                del divisions[d]

    if len(plist) < MIN_PRODUCTS:
        return None, "sitemap URLs did not resolve into product names"
    # A flat URL structure (no path segment above the leaf) carries no division
    # information. Lou's call, 25/08/2026: publish the list anyway rather than
    # refuse it outright — a rep can use a flat product list; they cannot use a
    # refusal. The report must still never CLAIM a division structure that
    # isn't there, so `hasDivisions` records whether "Uncategorised" is a real
    # grouping-not-found state, and captureCaveat/filingRule say so in words.
    # This REPLACES the two refusals that used to fire here (all-uncategorised,
    # and majority-uncategorised — the medi UK case, 07/08/2026, is now handled
    # by labelling the bucket honestly instead of hiding it).
    real = [d for d in divisions if d != "Uncategorised"]
    uncat = divisions.get("Uncategorised", 0)
    has_divisions = bool(real) and uncat * 2 <= len(plist)
    flat_note = (
        "" if has_divisions else
        ("the sitemap's product URLs are flat, so they carry no division structure — shown as "
         "one unsorted list, not the company's own filed grouping" if not real else
         "%d of %d product URLs carry no division segment, so most of the range sits in one "
         "unsorted 'Uncategorised' list rather than the company's own grouping" % (uncat, len(plist)))
    )
    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": "%s XML sitemap, read this run" % domain,
        "structureFrom": "sitemap",
        "hasDivisions": has_divisions,
        "landingPagesDropped": landing,
        "duplicateUrlsDropped": duplicate_urls,
        "captureCaveat": ("Names are derived from the last segment of each product URL, not read "
                          "from a product record, so they carry no category and read as title-cased "
                          "slugs. %d category landing page(s) were dropped by the prefix test — a "
                          "path that is a strict prefix of other paths is a page you pass through, "
                          "not a product. A leaf URL that is not a product cannot be detected "
                          "structurally and a few may remain, so treat this range as the shape of "
                          "the catalogue rather than an exact product list. A WordPress REST "
                          "capture (structureFrom: 'wp-rest') does not have this limitation."
                          % landing) + (" " + flat_note + "." if flat_note else ""),
        "structure": "Grouped by the company's own URL structure." if has_divisions else
                     "No division structure found in the URLs — listed as one flat range.",
        "droppedCategoryPages": dropped,
        "filingRule": (("Read from the sitemap, so product NAMES come from URL slugs and the "
                       "grouping is the company's own URL structure, not a product record. "
                       "Treat names as the company's own wording tidied for display, and expect "
                       "no category detail below the top level.") if has_divisions else
                       ("Read from the sitemap, so product NAMES come from URL slugs. " + flat_note +
                        " — every item is listed by name below rather than grouped, because a "
                        "flat list is honest and a fabricated grouping would not be.")),
        "divisions": [{"name": k, "products": v}
                      for k, v in sorted(divisions.items(), key=lambda kv: -kv[1])],
        "products": plist,
    }, None


# ---------------------------------------------------------------- route 3
# WIX, added 28/08/2026 — see 02-Elevate-and-Thrive/Hub/Architecture/
# DIFFERENTIATOR-CRAWLER-ROUTES.md, "Gap found 27/08/2026 — there is no Wix
# route, and it is why Jeenie publishes nothing".
#
# WHY THIS ROUTE HAD TO EXIST. Every Wix store serves its products at a FLAT
# `/product-page/<handle>` URL — like Shopify, the platform has no
# per-category product path. Route 2 (sitemap) derives a division from the
# URL path segment above the leaf, so on Wix there is never one to read, and
# this is structurally the SAME bug as Bug 1 (Shopify) above: even adding
# `product-page` to PRODUCT_PATHS would only file every product under
# "Uncategorised" and hold it forever, not recover a division. Jeenie
# Solutions' own products sitemap already carries 32 real product URLs; they
# were being refused as "too few to call a catalogue" purely because none of
# them matched the generic path-segment list — a platform gap, not a thin
# site.
#
# DETECTION IS DEFINITIVE, exactly like route 0's Shopify probe. A Wix site
# stamps its OWN `/sitemap.xml` (never `/sitemap_index.xml` — Wix answers
# that with HTTP 400, confirmed live 27/08/2026) with `generatedBy="WIX"` and
# indexes a `*-products-sitemap.xml` sub-sitemap whenever Wix Stores is
# switched on. Both signals are read off the SAME one request, so a
# non-Wix site pays exactly one extra request to be told no, and this route
# never guesses.
#
# WHAT IT READS, AND WHY IT IS ONE REQUEST PER PRODUCT. There is no bulk
# product endpoint on Wix — Shopify's `/products.json` returns the whole
# catalogue in one call; Wix has nothing equivalent. Each product's own name,
# SKU, brand and description come from fetching ITS OWN page and reading its
# JSON-LD `Product` block — verified live on
# https://www.jeenie.uk/product-page/bed-pull, 27/08/2026 (name, sku, brand,
# description all present). That is genuinely 32 requests for Jeenie's range,
# not one.
#
# DIVISION: CHECKED, NOT GUESSED. Wix's JSON-LD Product block was read on
# five live Jeenie product pages, 27-28/08/2026 (Bed Pull, Evacone, Limb
# Support, Jeenie1/Jeenie4 SPU Slide Sheet, Oxford Quickfit Deluxe Poly
# Padded Legs). NONE of the five carried a `category` or `additionalProperty`
# field — only @context/@type/name/description/sku/brand/image/offers.
# Jeenie's real 12 categories (read off `store-categories-sitemap.xml`:
# acute-products, seating, evacuation, training-aids, empathy-suits, slings,
# community-products, air-products, moving-and-handling, bariatric-equipment,
# plus "all"/"featured" shelves) are JS-rendered pages with no server-side
# membership list a plain fetch can read. There is genuinely no division to
# read here, so — the same rule the Shopify and sitemap routes already apply
# to a flat range — this route does not invent one. Every product is filed
# under one flat "Uncategorised" list, `hasDivisions` is False, and
# `filingRule` says why. Matching each product's description text against
# the Hub vocabulary (the smaller, reusable option the architecture doc
# records — build_differentiator.py already applies the same rule to NHSSC
# rows) is a mapping-stage decision, not something this crawler manufactures.
WIX_BUDGET_S = 900     # no bulk endpoint — one request per product page


def _wix_jsonld_product(html_doc):
    """The same JSON-LD `Product` extraction
    scripts/crawl_supplier_product_detail.py's extract_jsonld_product() does,
    replicated rather than imported: that module imports THIS one
    (`import crawl_supplier_site as base`), so importing it back here would
    be circular. Kept to the same regex/parsing approach deliberately —
    diverging would mean two crawlers reading the same JSON-LD differently."""
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


def wix_products(domain, deadline=None):
    """Read a Wix storefront's products sitemap, then each product's own
    JSON-LD `Product` block. See the route-3 comment block above."""
    try:
        body, _ = get("https://%s/sitemap.xml" % domain, timeout=15)
    except Exception as e:
        return None, "no readable /sitemap.xml (%s)" % str(e)[:50]
    if not re.search(r'generatedby\s*=\s*["\']wix["\']', body[:2000], re.I):
        return None, "not a Wix storefront (sitemap.xml carries no Wix marker)"

    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
    prod_sitemaps = [l for l in locs if re.search(r"-products-sitemap\.xml", l, re.I)]
    if not prod_sitemaps:
        return None, "a Wix storefront, but its sitemap.xml lists no products sitemap"

    urls = []
    for sm in prod_sitemaps[:4]:
        try:
            sbody, _ = get(sm, timeout=15)
        except Exception:
            continue
        urls.extend(u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sbody)
                    if "/product-page/" in u.lower())
    urls = sorted(set(urls))
    if len(urls) < MIN_PRODUCTS:
        return None, ("the Wix products sitemap carries %d product URL(s), too few to call a "
                      "catalogue" % len(urls))

    plist, unreadable = [], 0
    for i, u in enumerate(urls):
        if deadline and time.time() > deadline:
            return None, ("ran out of budget after reading %d of %d Wix product page(s) — Wix "
                          "has no bulk product endpoint, so this is one request per product, and "
                          "a partial sweep is refused rather than published as an undercount"
                          % (i, len(urls)))
        try:
            phtml, _ = get(u, timeout=20)
        except Exception:
            unreadable += 1
            continue
        ld = _wix_jsonld_product(phtml)
        name = clean((ld or {}).get("name"))
        if not name or len(name) < 3:
            unreadable += 1
            continue
        plist.append({"n": name, "division": "Uncategorised", "category": ""})

    if len(plist) < MIN_PRODUCTS:
        return None, ("only %d of %d Wix product page(s) carried a readable JSON-LD Product "
                      "name, too few to call a catalogue" % (len(plist), len(urls)))
    if unreadable:
        print("      wix: %d of %d product page(s) carried no readable JSON-LD Product block, "
              "skipped" % (unreadable, len(urls)), flush=True)

    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": "%s Wix storefront, each product page's own JSON-LD, read this run" % domain,
        "structureFrom": "Wix product pages' own JSON-LD Product blocks (no bulk endpoint, one "
                         "request per product)",
        "hasDivisions": False,
        "structure": "No usable grouping — Wix's JSON-LD Product block carries no category or "
                     "additionalProperty field on any product checked, and the site's real "
                     "categories are JS-rendered pages with no server-side membership list a "
                     "plain fetch can read. Listed as one flat range.",
        "filingRule": ("Read from each product's own JSON-LD record on its Wix product page, so "
                      "names, SKUs and descriptions are exact. Wix's Product schema carries no "
                      "division field on this site — checked against several live product pages, "
                      "not assumed — so every item is listed by name below rather than grouped, "
                      "because a fabricated grouping would misrepresent the company's own filing. "
                      "A future mapping pass may still assign a Hub category per product from its "
                      "description text (the same rule build_differentiator.py already applies to "
                      "NHS Supply Chain rows); this crawl does not attempt that."),
        "divisions": [{"name": "Uncategorised", "products": len(plist)}],
        "products": plist,
    }, None


# ---------------------------------------------------------------- route 4
# WOOCOMMERCE STORE API, added 29/08/2026 (weekend sprint, Step 4 priority 1).
#
# WHY THIS ROUTE HAD TO EXIST. Route 1 asks `/wp-json/wp/v2/types` for a
# product-shaped post type, then reads it via the generic WordPress REST API.
# WooCommerce does not always register `product` there — many stores ship it
# with the default WP REST product endpoint disabled or non-public, which
# route 1 correctly reads as "no usable type" and refuses, and route 2
# (sitemap) then also fails wherever the site's sitemap is JS-rendered or
# omits a product sitemap. 28/08/2026 found this is a crawler gap, not a
# supplier refusal: `/wp-json/wc/store/v1/products` is WooCommerce's OWN
# storefront API, served publicly by default (it powers the site's own cart/
# checkout blocks), and it answers on sites route 1 could not reach at all.
# Verified reachable on 8 previously-refused suppliers, 6 of them returning
# real product categories usable as divisions: harvesthealthcare.co.uk,
# andrac.com, surtex-instruments.com, careflex.co.uk, silvalea.com,
# kinetikwellbeing.com, gammacore.co.uk, cdmedical.co.uk.
#
# WHAT IT RETURNS. Each product record carries its own `categories` — a list
# of `{id, name, slug, link}`, already the company's own filing, no taxonomy
# walk needed the way route 1 needs one. A product can carry more than one;
# the SMALLEST category (by catalogue coverage) wins, the same rule route 0
# applies to overlapping Shopify collections and route 1 applies to competing
# WordPress taxonomy roots — the category that covers fewer products is the
# more specific claim about this one.
#
# Detection is one definitive request, same principle as route 0: a genuine
# WooCommerce Store API returns a JSON list of product objects (even an empty
# store returns `[]`); anything else — 404, HTML, a REST-disabled response —
# is read as "not this route" and costs exactly one wasted request on every
# site that isn't WooCommerce-with-a-public-Store-API.
WC_STORE_BUDGET_S = 600


def _wc_store_paged(domain, deadline=None, cap=MAX_PAGES):
    """Walk the WooCommerce Store API's ?page= pagination to the end."""
    out, page = [], 1
    while page <= cap:
        if deadline and time.time() > deadline:
            raise RuntimeError("budget exhausted after %d page(s)" % (page - 1))
        items, _ = get("https://%s/wp-json/wc/store/v1/products?per_page=100&page=%d"
                       % (domain, page), as_json=True)
        if not isinstance(items, list):
            raise RuntimeError("Store API returned a non-list response")
        out += items
        if len(items) < 100:
            break
        page += 1
    return out


def wc_store_products(domain, deadline=None):
    """Read a WooCommerce Store API's own product records and their own
    filed categories. See the route-4 comment block above."""
    try:
        prods = _wc_store_paged(domain, deadline=deadline)
    except urllib.error.HTTPError as e:
        return None, "the WooCommerce Store API returned HTTP %d" % e.code
    except Exception as e:
        return None, "not a readable WooCommerce Store API (%s)" % str(e)[:60]

    if len(prods) < MIN_PRODUCTS:
        return None, ("the WooCommerce Store API returned %d product(s), too few to be a "
                      "catalogue" % len(prods))

    # Coverage of each category across the whole range, so the smallest (most
    # specific) one can win when a product carries several.
    cov = {}
    for p in prods:
        for c in (p.get("categories") or []):
            name = clean(c.get("name"))
            if name:
                cov[name] = cov.get(name, 0) + 1

    divisions, plist = {}, []
    for p in prods:
        name = clean(p.get("name"))
        if not name or len(name) < 3:
            continue
        cats = [clean(c.get("name")) for c in (p.get("categories") or []) if clean(c.get("name"))]
        div = min(cats, key=lambda c: (cov.get(c, 0), c)) if cats else "Uncategorised"
        divisions[div] = divisions.get(div, 0) + 1
        plist.append({"n": name, "division": div, "category": cats[0] if cats else ""})

    if not plist:
        return None, "the WooCommerce Store API exposed no readable product records"

    real = [d for d in divisions if d != "Uncategorised"]
    uncat = divisions.get("Uncategorised", 0)
    has_divisions = bool(real) and uncat * 2 <= len(plist)
    flat_note = ("" if has_divisions else
                 "%d of %d products carry no category on the store's own Store API, so most of "
                 "the range sits in one unsorted 'Uncategorised' list rather than the company's "
                 "own grouping" % (uncat, len(plist)))
    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": "%s WooCommerce Store API product records, read this run" % domain,
        "structureFrom": "the company's own WooCommerce product categories (Store API)",
        "hasDivisions": has_divisions,
        "structure": "The company's own product categories, as published on its own store." if
                     has_divisions else
                     "No usable grouping on the Store API — listed as one flat range.",
        "filingRule": (("Grouping MIRRORS the manufacturer's own filing, read from the company's "
                        "own WooCommerce Store API. Where a product sits under a category that "
                        "reads oddly clinically, that is where the company files it, and a rep "
                        "searching the company's way will find it there.")
                       if has_divisions else
                       ("Read from the Store API's own product records, so names are exact. "
                        + flat_note + " — every item is listed by name below rather than grouped, "
                        "because a fabricated grouping would misrepresent the company's own "
                        "filing.")),
        "divisions": [{"name": k, "products": v}
                      for k, v in sorted(divisions.items(), key=lambda kv: -kv[1])],
        "products": plist,
    }, None


def reachable_host(domain):
    """Return whichever of `domain` / `www.domain` actually answers, or None.

    WHY THIS EXISTS (26/08/2026). The wound care sweep refused Coloplast, CD
    Medical, Iskus/Fannin and B. Braun with "[SSL: CERTIFICATE_VERIFY_FAILED]"
    and "nodename nor servname provided" — read at first glance as four sites
    blocking automated reads. They are not. All four serve their certificate on
    the `www.` host only: the bare apex either resolves to nothing or presents a
    certificate that does not cover it. `https://www.coloplast.co.uk/` returns
    200 to the very same urllib call that fails on `https://coloplast.co.uk/`.

    Seeded domains are recorded bare, so every such supplier was being written
    off on a host-selection artefact rather than anything the site does. That is
    the same failure mode as reading a blocked tool as a blocked site
    ([[nice-blocks-webfetch-not-curl]]): the honest answer needs both hosts
    tried before "refused" is recorded.

    This changes no evidence bar. It selects the host to ask; what counts as a
    readable product range afterwards is untouched.
    """
    d = domain[4:] if domain.startswith("www.") else domain
    for host in (d, "www." + d):
        try:
            get("https://%s/" % host, timeout=12)
            return host
        except urllib.error.HTTPError:
            # An HTTP status means the host resolved and served TLS. That is
            # reachable; whether this particular path 404s is not the question.
            return host
        except Exception:
            continue
    return None


def crawl(domain):
    started = time.time()
    host = reachable_host(domain)
    if not host:
        return None, ("neither %s nor www.%s answered — the domain does not resolve or "
                      "serves no usable certificate" % (domain, domain))
    domain = host
    if not allowed(domain):
        return None, "robots.txt disallows automated reading of this site"
    # Route 0 first, and on its own budget. Detection is definitive — a site
    # either serves /collections.json as Shopify JSON or it does not — so this
    # costs one request on every non-Shopify site and never guesses. It runs
    # BEFORE the WordPress and sitemap routes because on a Shopify site both of
    # those "succeed" while filing the entire range as Uncategorised, which is
    # the failure this route exists to end (27/08/2026).
    shop_why = None
    try:
        shaped, shop_why = shopify_products(domain, deadline=started + SHOPIFY_BUDGET_S)
        if shaped:
            return shaped, None
    except urllib.error.HTTPError as e:
        shop_why = "the Shopify storefront returned HTTP %d" % e.code
    except Exception as e:
        shop_why = "the Shopify storefront could not be read (%s)" % str(e)[:60]
    try:
        raw, why = wp_products(domain, deadline=started + SITE_BUDGET_S)
        if raw:
            shaped, why = shape_from_wp(raw, domain)
            if shaped:
                return shaped, None
    except urllib.error.HTTPError as e:
        why = "the site's WordPress API returned HTTP %d" % e.code
    except Exception as e:
        why = "the site's WordPress API could not be read (%s)" % str(e)[:60]

    # Route 4 — WOOCOMMERCE STORE API (29/08/2026), tried here rather than
    # after the sitemap route. A WordPress site that failed route 1 may still
    # be a WooCommerce store with its default product REST type disabled but
    # its own Store API public, and the Store API's real product categories
    # are a better filing than the generic sitemap route ever recovers — the
    # sitemap route has no category signal at all, so it always "succeeds"
    # flat. Tried here so a genuine WooCommerce store gets its own divisions
    # instead of silently falling through to an Uncategorised sitemap listing
    # that never gets revisited once route 2 has "succeeded". See the route-4
    # comment block above wc_store_products() for why this is a distinct
    # route rather than folded into route 1.
    try:
        shaped, why4 = wc_store_products(domain, deadline=started + WC_STORE_BUDGET_S)
        if shaped:
            return shaped, None
    except urllib.error.HTTPError as e:
        why4 = "the WooCommerce Store API returned HTTP %d" % e.code
    except Exception as e:
        why4 = "the WooCommerce Store API could not be read (%s)" % str(e)[:60]

    try:
        shaped, why2 = sitemap_products(domain, deadline=started + SITE_BUDGET_S,
                                        product_paths=crawl.product_paths)
        if shaped:
            return shaped, None
    except urllib.error.HTTPError as e:
        why2 = "the sitemap returned HTTP %d" % e.code
    except Exception as e:
        why2 = "the sitemap could not be read (%s)" % str(e)[:50]

    # Route 3 — WIX (28/08/2026), tried only once routes 0-2 and 4 have all
    # failed. Detection is one definitive request — /sitemap.xml either
    # stamps generatedBy="WIX" and indexes a *-products-sitemap.xml, or it
    # does not — so a non-Wix site pays exactly one extra request to be told
    # no. See the route-3 comment block above wix_products() for why this
    # cannot simply be folded into route 2's PRODUCT_PATHS.
    try:
        shaped, why3 = wix_products(domain, deadline=started + WIX_BUDGET_S)
        if shaped:
            return shaped, None
    except urllib.error.HTTPError as e:
        why3 = "the Wix products sitemap returned HTTP %d" % e.code
    except Exception as e:
        why3 = "the Wix storefront could not be read (%s)" % str(e)[:60]

    return None, "%s; %s; %s; %s" % (why, why4, why2, why3)


def domain_for(rec):
    for l in (rec.get("links") or []):
        u = l.get("url") if isinstance(l, dict) else l
        m = re.search(r"https?://([^/]+)", str(u or ""))
        if m and not any(x in m.group(1) for x in ("gov.uk", "supplychain", "nhs.uk", "linkedin")):
            return m.group(1)
    m = re.search(r"logo\.clearbit\.com/([^/?]+)|domain=([^&]+)", rec.get("image") or "")
    return (m.group(1) or m.group(2)) if m else None


# Default: the generic PRODUCT_PATHS. main() overrides from --product-path.
crawl.product_paths = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplier")
    ap.add_argument("--domain")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--product-path", action="append", default=[],
                    help="a URL path segment this company files products under, e.g. "
                         "--product-path wound. Use ONLY after looking at that site's "
                         "sitemap and confirming the segment holds products and not "
                         "news or support pages. Repeatable.")
    ap.add_argument("--retry-refused", action="store_true",
                    help="re-attempt suppliers already recorded as refused")
    ap.add_argument("--refusal-ttl", type=int, default=90,
                    help="days a recorded refusal suppresses a re-attempt (default 90)")
    a = ap.parse_args()
    crawl.product_paths = a.product_path or None

    doc = json.load(open(OUT, encoding="utf-8"))
    doc.setdefault("refusals", {})
    index = {s["name"]: s for s in json.load(open(INDEX, encoding="utf-8"))["suppliers"]}

    # WHY THIS EXISTS (added 12/08/2026). `--auto` chose its targets from
    # "on a framework AND not already in doc['suppliers']". A refusal wrote
    # nothing, so a refused supplier stayed eligible and was ranked first
    # again on the next run — every scheduled run re-attempted the same
    # top-ranked refusals and the sweep could never advance past them. That
    # is why 21 of 548 had a range after five weeks of daily runs.
    #
    # A refusal is a READ OUTCOME, not a claim about the company, so it is
    # recorded beside the ranges rather than inside them. No consumer reads
    # this key: the member-facing rule is unchanged — a supplier absent from
    # `suppliers` still falls back to the seed's curated list. It never says
    # a company has no products; it says this crawler could not read them,
    # on a date, for a stated reason.
    cutoff = (dt.date.today() - dt.timedelta(days=a.refusal_ttl)).isoformat()

    def recently_refused(name):
        r = doc["refusals"].get(name)
        return bool(r) and r.get("checked", "") >= cutoff

    def record_refusal(name, domain, why):
        doc["refusals"][name] = {"domain": domain or None,
                                 "reason": why or "no reason recorded",
                                 "checked": dt.date.today().isoformat()}

    def save(d):
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
            f.write("\n")

    targets = []
    if a.supplier:
        targets = [(a.supplier, a.domain or domain_for(index.get(a.supplier, {})))]
    elif a.auto:
        fw = json.load(open(FW, encoding="utf-8"))
        suf = re.compile(r"\b(ltd|limited|plc|llp|inc|corp|co|company|group|holdings|"
                         r"international|uk|u k|gb|healthcare|health|medical|med|products|"
                         r"solutions|systems|technologies|devices)\b")
        def key(s):
            k = re.sub(r"[^a-z0-9]+", " ", str(s).lower())
            return re.sub(r"\s+", " ", suf.sub(" ", k)).strip()
        count = {}
        for f in fw["frameworks"]:
            for k in {key(x) for x in f["suppliers"]}:
                if k:
                    count[k] = count.get(k, 0) + 1
        ranked = []
        for name, rec in index.items():
            k = key(name)
            if k in count and name not in doc["suppliers"]:
                if not a.retry_refused and recently_refused(name):
                    continue
                d = domain_for(rec)
                if d:
                    ranked.append((count[k], name, d))
        ranked.sort(reverse=True)
        targets = [(n, d) for _, n, d in ranked[:a.limit]]

        # WHY THIS EXISTS (added 14/08/2026). An empty --auto queue is the
        # SWEEP FINISHING, not a fault: every framework supplier that has a
        # website recorded in the index has now either been captured or
        # refused inside the TTL. Exiting non-zero turned that into a red
        # scheduled run every night. The genuine error — invoked with no
        # target and no --auto — still exits 1 below.
        if not targets:
            print("Nothing due: every framework supplier with a website recorded "
                  "in the index has been captured or refused within the last "
                  "%d days. Nothing crawled, nothing written." % a.refusal_ttl,
                  flush=True)
            return

    if not targets:
        sys.exit("Nothing to crawl. Pass --supplier NAME [--domain host], or --auto.")

    done, refused = 0, 0
    for name, domain in targets:
        if not domain:
            print("  -- %-30s no website recorded for this supplier" % name[:30], flush=True)
            record_refusal(name, None, "no website recorded for this supplier")
            refused += 1
            if not a.dry_run:
                save(doc)
            continue
        shaped, why = crawl(domain)
        if not shaped:
            print("  -- %-30s %s" % (name[:30], (why or "")[:70]), flush=True)
            record_refusal(name, domain, why)
            refused += 1
            # Saved immediately, for the same reason captures are: a long sweep
            # gets interrupted, and an unsaved refusal is a target the next run
            # spends its budget on again.
            if not a.dry_run:
                save(doc)
            continue
        doc["refusals"].pop(name, None)
        existing = doc["suppliers"].get(name) or {}
        # Never overwrite a hand-verified entry's curated fields.
        for k in ("aliases", "companyNo", "notSold", "tubesNote", "domainWarning"):
            if k in existing:
                shaped[k] = existing[k]
        doc["suppliers"][name] = shaped
        done += 1
        print("  OK %-30s %d products, %d divisions (%s)"
              % (name[:30], len(shaped["products"]), len(shaped["divisions"]),
                 shaped["structureFrom"]), flush=True)
        # Save after EVERY supplier. The first wide pass wrote only at the end,
        # so stopping it would have thrown away everything it had read.
        if not a.dry_run:
            save(doc)

    # Refusals are saved too, and on the SAME terms as captures. The end-of-run
    # write used to be `if done`, so a batch that captured nothing wrote
    # nothing — which is exactly the batch whose refusals need remembering, or
    # the next run picks the same targets again.
    if not a.dry_run and (done or refused):
        save(doc)
    print("\n%d supplier range(s) captured, %d refused (%d refusals on record).%s"
          % (done, refused, len(doc["refusals"]),
             "  (dry run: nothing written)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
