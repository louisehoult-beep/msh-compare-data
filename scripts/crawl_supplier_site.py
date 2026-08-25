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
    # Medtronic returns "Incorrect Browser" — and HTML parses as a robots file
    # with NO rules, i.e. "crawl anything". That is precisely backwards: a site
    # serving a block page is refusing. If the response is not plainly a robots
    # file, treat it as a refusal.
    head = body.lstrip()[:400].lower()
    if "<html" in head or "<!doctype" in head:
        return False
    if body.strip() and "user-agent" not in body.lower():
        return False                    # something else entirely; do not assume consent

    rp.parse(body.splitlines())
    return rp.can_fetch(UA_STR, "https://%s%s" % (domain, path))


def clean(s):
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


# ---------------------------------------------------------------- route 1
def wp_products(domain, deadline=None):
    base = "https://%s/wp-json/wp/v2" % domain
    types, _ = get(base + "/types", as_json=True)
    ptype = None
    for key, val in types.items():
        if key.lower() in ("product", "products") or "product" in (val.get("rest_base") or ""):
            ptype = val.get("rest_base") or key
            taxes = val.get("taxonomies") or []
            break
    if not ptype:
        return None, "the site's WordPress API exposes no product post type"

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
                cats[c["id"]] = {"name": clean(c.get("name")), "parent": c.get("parent") or 0,
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
            ids = p.get(tax) or [] if tax else []
            products.append({"n": name, "cats": ids})
        if len(items) < 100:
            break
        page += 1

    if len(products) < MIN_PRODUCTS:
        return None, ("only %d product records on the site's API — that is a landing page, not a "
                      "catalogue" % len(products))
    return {"products": products, "cats": cats}, None


def top_level(cid, cats):
    """Walk a category to its root, so products group under the company's own top divisions."""
    seen = set()
    while cid and cid in cats and cats[cid]["parent"] and cid not in seen:
        seen.add(cid)
        cid = cats[cid]["parent"]
    return cid


def shape_from_wp(raw, domain):
    cats, products = raw["cats"], raw["products"]
    divisions, plist = {}, []
    for p in products:
        names = [cats[c]["name"] for c in p["cats"] if c in cats]
        roots = [cats[top_level(c, cats)]["name"] for c in p["cats"]
                 if top_level(c, cats) in cats]
        div = roots[0] if roots else "Uncategorised"
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
        "source": ("%s product catalogue (WordPress REST API), read this run" % domain),
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
def sitemap_products(domain, deadline=None):
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
            to_read.extend([l for l in locs if "product" in l.lower() or "sitemap" in l.lower()][:8])
            continue
        urls.extend(locs)

    prod = [u for u in urls if re.search(r"/(product|products|our-products|range|ranges)/", u, re.I)]
    if len(prod) < MIN_PRODUCTS:
        return None, ("the sitemap carries %d product URLs, too few to call a catalogue" % len(prod))

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
    paths = []
    for u in prod:
        path = urllib.parse.urlparse(u).path.strip("/").split("/")
        try:
            i = next(n for n, seg in enumerate(path)
                     if re.fullmatch(r"(?i)product|products|our-products|range|ranges", seg))
        except StopIteration:
            continue
        rest = path[i + 1:]
        if rest:
            paths.append(rest)
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


def crawl(domain):
    started = time.time()
    if not allowed(domain):
        return None, "robots.txt disallows automated reading of this site"
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
    try:
        shaped, why2 = sitemap_products(domain, deadline=started + SITE_BUDGET_S)
        if shaped:
            return shaped, None
        return None, "%s; %s" % (why, why2)
    except urllib.error.HTTPError as e:
        return None, "%s; the sitemap returned HTTP %d" % (why, e.code)
    except Exception as e:
        return None, "%s; the sitemap could not be read (%s)" % (why, str(e)[:50])


def domain_for(rec):
    for l in (rec.get("links") or []):
        u = l.get("url") if isinstance(l, dict) else l
        m = re.search(r"https?://([^/]+)", str(u or ""))
        if m and not any(x in m.group(1) for x in ("gov.uk", "supplychain", "nhs.uk", "linkedin")):
            return m.group(1)
    m = re.search(r"logo\.clearbit\.com/([^/?]+)|domain=([^&]+)", rec.get("image") or "")
    return (m.group(1) or m.group(2)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplier")
    ap.add_argument("--domain")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retry-refused", action="store_true",
                    help="re-attempt suppliers already recorded as refused")
    ap.add_argument("--refusal-ttl", type=int, default=90,
                    help="days a recorded refusal suppresses a re-attempt (default 90)")
    a = ap.parse_args()

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
