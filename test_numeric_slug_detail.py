#!/usr/bin/env python3
"""
test_numeric_slug_detail.py — prove the product-detail crawler can source a
product whose URL is a bare id, and that it does not invent anything doing it.

WHY THIS EXISTS (OUTSTANDING ^o379). find_product_url() matches a product name
against the last segment of a sitemap URL. swann-morton.co.uk files 137 products
at /product/15.php and the like, so that segment slugifies to "15-php" and can
never match "Surgical Scalpel Blade No. 9". Every one of the supplier's products
was refused for "no sitemap URL's slug matches this product's name", no row ever
got a source, and the coverage ledger read the supplier as never crawled and
re-offered all 137 on every run, indefinitely.

The name was never missing — only absent from the URL. crawl_supplier_site.py
already reads it off each page to capture the range at all. The fix reuses that
same reader here.

Each case below is that incident, or a way the fix could make things worse:
diverting an ordinary descriptive-slug site into the slow per-page read, reading
a breadcrumb crumb as the product, or — the one found on the first real page —
publishing a product image out of markup the site has commented out.

  python3 test_numeric_slug_detail.py     exit 0 = bare-id sites are sourced
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_product_detail as d          # noqa: E402
import crawl_supplier_site as base                 # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def reset():
    d._NAME_INDEX.clear()
    d._PAGE_CACHE.clear()
    d._SITEMAP_CACHE.clear()


PRODUCT_PAGE = """<!DOCTYPE html><html><head><title>%(name)s. Acme Ltd</title></head>
<body itemscope itemtype="https://schema.org/Product">
<ol class="breadcrumb"><li><span itemprop="name">Home</span></li>
<li><span itemprop="name">Blades</span></li></ol>
<h1><span itemprop="name">%(name)s</span></h1>
<span itemprop="description">%(desc)s</span>
<meta itemprop="model" content="%(model)s">
<!-- <span itemprop="image"><img src="/images/switched-off.jpg"></span> -->
</body></html>"""

PAGES = {
    "https://acme.test/product/15.php": {"name": "Surgical Scalpel Blade No. 9",
                                         "desc": "A broad hatchet-shaped blade used in podiatry.",
                                         "model": "No. 09"},
    "https://acme.test/product/17.php": {"name": "Surgical Scalpel Blade No.10A",
                                         "desc": "A fine curved blade for precise incisions.",
                                         "model": "No. 10A"},
}
FETCHED = []


def fake_get(url, timeout=None, **kw):
    FETCHED.append(url)
    if url in PAGES:
        return PRODUCT_PAGE % PAGES[url], {}
    raise AssertionError("unexpected fetch: %s" % url)


base_get = base.get


def install_stubs(urls):
    reset()
    del FETCHED[:]
    base.get = fake_get
    d._SITEMAP_CACHE["acme.test"] = urls


def remove_stubs():
    base.get = base_get


# ---------------------------------------------------------------------------
# 1. WHICH SITES GET THE SLOW PER-PAGE READ. Same 80% rule the range crawler
#    already applies, so the two cannot disagree about what a site looks like.
# ---------------------------------------------------------------------------
print("only a genuinely bare-id site is diverted to the per-page read")
check("bare numeric ids",
      d._is_numeric_slug_site(["https://x/product/15.php", "https://x/product/17.php"]))
check("descriptive slugs are not",
      not d._is_numeric_slug_site(["https://x/product/blue-widget",
                                   "https://x/product/red-widget"]))
check("a slug that merely ends in a digit is not",
      not d._is_numeric_slug_site(["https://x/product/widget-2", "https://x/product/widget-3"]))
check("a lone numeric oddity does not divert a descriptive site",
      not d._is_numeric_slug_site(["https://x/product/a", "https://x/product/b",
                                   "https://x/product/c", "https://x/product/15"]))
check("no product URLs at all is not a bare-id site", not d._is_numeric_slug_site([]))

# ---------------------------------------------------------------------------
# 2. THE INCIDENT. A bare-id product is found by the name its own page publishes.
# ---------------------------------------------------------------------------
print("a bare-id product is found by the name its page publishes")
install_stubs(list(PAGES))
url, why = d.find_product_url("acme.test", "Surgical Scalpel Blade No. 9", None)
check("matched", url == "https://acme.test/product/15.php", (url, why))
url2, _ = d.find_product_url("acme.test", "Surgical Scalpel Blade No.10A", None)
check("the second product matched its own page",
      url2 == "https://acme.test/product/17.php", url2)
check("the index was built once, not once per product", len(FETCHED) == 2, FETCHED)

# ---------------------------------------------------------------------------
# 2b. THE INDEX IS NOT BUILT INSIDE ONE PRODUCT'S BUDGET. find_product_url() is
#     handed a PER-PRODUCT deadline (15s). The first real run against
#     swann-morton.co.uk built 32 of 137 pages inside it and then refused the
#     other 105 for "no page in its name index publishes this product's name" —
#     a wrong answer, not a slow one.
# ---------------------------------------------------------------------------
print("a spent per-product deadline does not truncate the index")
install_stubs(list(PAGES))
expired = 0.0                                   # a deadline already long gone
u1, _ = d.find_product_url("acme.test", "Surgical Scalpel Blade No. 9", expired)
u2, _ = d.find_product_url("acme.test", "Surgical Scalpel Blade No.10A", expired)
check("both products still found", u1 and u2, (u1, u2))
check("every page was read", len(FETCHED) == 2, FETCHED)
check("the build has its own budget, not the caller's",
      d.NAME_INDEX_BUDGET_S >= base.NUMERIC_SLUG_BUDGET_S, d.NAME_INDEX_BUDGET_S)
install_stubs(list(PAGES))
url, _ = d.find_product_url("acme.test", "Surgical Scalpel Blade No. 9", None)

# ---------------------------------------------------------------------------
# 3. NO DOUBLE FETCH. Route B reads the detail off the page the index already
#    pulled, so this route costs the same as the range crawl, not twice.
# ---------------------------------------------------------------------------
print("the detail is read from the page already fetched")
before = len(FETCHED)
entry, why = d.page_product_detail(url)
check("no second request", len(FETCHED) == before, FETCHED[before:])
check("read as structured, not heuristic", (entry or {}).get("parsed") == "structured", why)
check("the description is the product's own",
      (entry or {}).get("description", "").startswith("A broad hatchet-shaped blade"),
      (entry or {}).get("description"))

# ---------------------------------------------------------------------------
# 4. A NAME THE SITE DOES NOT PUBLISH IS REFUSED, NOT GUESSED AT.
# ---------------------------------------------------------------------------
print("a product the site does not carry is refused")
u, why = d.find_product_url("acme.test", "Something Else Entirely", None)
check("no URL returned", u is None, u)
check("and it says why", "name index" in (why or ""), why)
remove_stubs()

# ---------------------------------------------------------------------------
# 5. THE MICRODATA READER. The traps that made the first real read wrong.
# ---------------------------------------------------------------------------
print("the microdata reader takes the product, not the furniture")
md = d.extract_microdata_product(PRODUCT_PAGE % PAGES["https://acme.test/product/15.php"])
check("description read", md["description"].startswith("A broad hatchet-shaped"), md)
check("model read as a feature", "Model: No. 09" in md["features"], md["features"])
check("NO image is taken from microdata", "image" not in md, md)
check("a breadcrumb crumb is not read as the product",
      "Home" not in str(md) and "Blades" not in str(md), md)
check("a page that is not a Product returns nothing",
      d.extract_microdata_product(
          '<html><body><ol class="breadcrumb"><span itemprop="name">Home</span></ol>'
          '<span itemprop="description">site blurb</span></body></html>') is None)

entry, why = d._detail_from_html("https://acme.test/product/15.php",
                                 PRODUCT_PAGE % PAGES["https://acme.test/product/15.php"])
check("the switched-off image is not published", entry.get("image") is None, entry.get("image"))

print()
if FAILURES:
    print("FAILED: %s" % ", ".join(FAILURES))
    sys.exit(1)
print("all cases pass — bare-id sites are sourced from their own pages")
