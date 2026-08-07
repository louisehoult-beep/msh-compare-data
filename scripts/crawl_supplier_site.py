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
import html as H
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

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
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url("https://%s/robots.txt" % domain)
    try:
        rp.read()
    except Exception:
        return True                     # no robots.txt served = no prohibition
    return rp.can_fetch(UA_STR, "https://%s%s" % (domain, path))


def clean(s):
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


# ---------------------------------------------------------------- route 1
def wp_products(domain):
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
    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": ("%s product catalogue (WordPress REST API), read this run" % domain),
        "structureFrom": "the company's own product category taxonomy",
        "structure": "The company's own top-level product categories.",
        "filingRule": ("Grouping MIRRORS the manufacturer's own filing. Where a product sits "
                       "under a category that reads oddly clinically, that is where the company "
                       "files it, and a rep searching the company's way will find it there."),
        "divisions": [{"name": k, "products": v}
                      for k, v in sorted(divisions.items(), key=lambda kv: -kv[1])],
        "products": plist,
    }


# ---------------------------------------------------------------- route 2
def sitemap_products(domain):
    seen, urls = set(), []
    to_read = ["https://%s/sitemap.xml" % domain, "https://%s/sitemap_index.xml" % domain]
    while to_read and len(seen) < 12:
        u = to_read.pop(0)
        if u in seen:
            continue
        seen.add(u)
        try:
            body, _ = get(u)
        except Exception:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        if "<sitemapindex" in body[:400].lower():
            to_read.extend([l for l in locs if "product" in l.lower() or "sitemap" in l.lower()][:8])
            continue
        urls.extend(locs)

    prod = [u for u in urls if re.search(r"/(product|products|our-products|range|ranges)/", u, re.I)]
    if len(prod) < MIN_PRODUCTS:
        return None, ("the sitemap carries %d product URLs, too few to call a catalogue" % len(prod))

    divisions, plist = {}, []
    for u in prod:
        path = urllib.parse.urlparse(u).path.strip("/").split("/")
        try:
            i = next(n for n, seg in enumerate(path)
                     if re.fullmatch(r"(?i)product|products|our-products|range|ranges", seg))
        except StopIteration:
            continue
        rest = path[i + 1:]
        if not rest:
            continue
        name = rest[-1].replace("-", " ").strip().title()
        div = (rest[0].replace("-", " ").strip().title() if len(rest) > 1 else "Uncategorised")
        if not name or len(name) < 3:
            continue
        divisions[div] = divisions.get(div, 0) + 1
        plist.append({"n": name, "division": div, "category": ""})

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

    if len(plist) < MIN_PRODUCTS:
        return None, "sitemap URLs did not resolve into product names"
    # Everything in one bucket means the URL structure carried NO division
    # information — a flat list of names, not the company's own filing. The
    # report presents divisions as the company's own structure, so publishing a
    # single "Uncategorised" division of 1,300 items would be a false structure.
    real = [d for d in divisions if d != "Uncategorised"]
    if not real:
        return None, ("the sitemap's product URLs are flat, so they carry no division structure "
                      "(%d names, all uncategorised) — a product list without the company's own "
                      "grouping is not the range this report shows" % len(plist))
    return {
        "domain": domain,
        "verified": time.strftime("%Y-%m-%d"),
        "source": "%s XML sitemap, read this run" % domain,
        "structureFrom": "sitemap",
        "structure": "Grouped by the company's own URL structure.",
        "droppedCategoryPages": dropped,
        "filingRule": ("Read from the sitemap, so product NAMES come from URL slugs and the "
                       "grouping is the company's own URL structure, not a product record. "
                       "Treat names as the company's own wording tidied for display, and expect "
                       "no category detail below the top level."),
        "divisions": [{"name": k, "products": v}
                      for k, v in sorted(divisions.items(), key=lambda kv: -kv[1])],
        "products": plist,
    }, None


def crawl(domain):
    started = time.time()
    if not allowed(domain):
        return None, "robots.txt disallows automated reading of this site"
    try:
        raw, why = wp_products(domain)
        if raw:
            return shape_from_wp(raw, domain), None
    except urllib.error.HTTPError as e:
        why = "the site's WordPress API returned HTTP %d" % e.code
    except Exception as e:
        why = "the site's WordPress API could not be read (%s)" % str(e)[:60]
    if time.time() - started > SITE_BUDGET_S:
        return None, ("gave up after %ds — the site answers too slowly to crawl inside its "
                      "budget" % SITE_BUDGET_S)
    try:
        shaped, why2 = sitemap_products(domain)
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
    a = ap.parse_args()

    doc = json.load(open(OUT, encoding="utf-8"))
    index = {s["name"]: s for s in json.load(open(INDEX, encoding="utf-8"))["suppliers"]}

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
                d = domain_for(rec)
                if d:
                    ranked.append((count[k], name, d))
        ranked.sort(reverse=True)
        targets = [(n, d) for _, n, d in ranked[:a.limit]]

    if not targets:
        sys.exit("Nothing to crawl. Pass --supplier NAME [--domain host], or --auto.")

    done, refused = 0, 0
    for name, domain in targets:
        if not domain:
            print("  -- %-30s no website recorded for this supplier" % name[:30], flush=True)
            refused += 1
            continue
        shaped, why = crawl(domain)
        if not shaped:
            print("  -- %-30s %s" % (name[:30], (why or "")[:70]), flush=True)
            refused += 1
            continue
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
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=1, ensure_ascii=False)
                f.write("\n")

    if not a.dry_run and done:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
            f.write("\n")
    print("\n%d supplier range(s) captured, %d refused.%s"
          % (done, refused, "  (dry run: nothing written)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
