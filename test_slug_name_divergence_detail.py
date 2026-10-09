#!/usr/bin/env python3
"""
test_slug_name_divergence_detail.py — prove the product-detail crawler can
source a product on a DESCRIPTIVE-slug site whose own display name diverges
from the wording of its own URL.

WHY THIS EXISTS (20/09/2026, ^o575, electrospyres.com). find_product_url()
matches a product's slugified display name against the last path segment of
a sitemap URL. That works for most sites, but electrospyres.com's own pages
disagree with their own URLs: the page for
/product/skinresq-dynaderm-film-island-dressing-80x60mm titles itself
"SkinResQ(TM) Film Island Dressing 80mm x 60mm" — no "Dynaderm" anywhere in
the name crawl_supplier_site.py's _page_title() reads off the page.
slugify(name) can never match that URL, exactly or partially, however
correct both strings are on their own. This is NOT the bare-id case
test_numeric_slug_detail.py covers (electrospyres.com's URLs carry real,
descriptive slugs, so _is_numeric_slug_site() is false and the per-page name
index used to never be tried) — it is a second, distinct way the same
"slug-matching" assumption breaks. 39 of 46 Electro Spyres products were
refused this way before the fix below, which falls back to the SAME
per-page name index the bare-id route already builds, once ordinary
exact/partial slug matching has found nothing at all.

  python3 test_slug_name_divergence_detail.py     exit 0 = the fallback works
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


PRODUCT_PAGE = """<!DOCTYPE html><html><head><title>%(name)s. Electro Spyres Medical</title></head>
<body itemscope itemtype="https://schema.org/Product">
<h1><span itemprop="name">%(name)s</span></h1>
<span itemprop="description">%(desc)s</span>
</body></html>"""

# Real shape, not the real text: a descriptive slug the page's own display
# name does not repeat in full.
PAGES = {
    "https://electrospyres.test/product/skinresq-dynaderm-film-island-dressing-80x60mm": {
        "name": "SkinResQ™ Film Island Dressing 80mm x 60mm",
        "desc": "A transparent film island dressing for low-to-moderately exuding wounds."},
    "https://electrospyres.test/product/pneumo-sos-vented-chest-seal": {
        "name": "Pneumo SOS™ Vented Chest Seal",
        "desc": "A sterile, vented chest seal for penetrating chest trauma."},
}
FETCHED = []


def fake_get(url, timeout=None, **kw):
    FETCHED.append(url)
    if url in PAGES:
        return PRODUCT_PAGE % PAGES[url], {}
    raise AssertionError("unexpected fetch: %s" % url)


base_get = base.get


def install_stubs():
    reset()
    del FETCHED[:]
    base.get = fake_get
    d._SITEMAP_CACHE["electrospyres.test"] = list(PAGES)


def remove_stubs():
    base.get = base_get


# ---------------------------------------------------------------------------
# 1. THIS IS NOT A BARE-ID SITE. Both product paths carry real, descriptive
#    words — the divergence-fallback path must not be confused with the
#    numeric-slug one.
# ---------------------------------------------------------------------------
print("descriptive slugs are not mistaken for bare ids")
check("not a numeric-slug site", not d._is_numeric_slug_site(list(PAGES)))

# ---------------------------------------------------------------------------
# 2. ORDINARY SLUG MATCHING FAILS FIRST, AS EXPECTED. Confirms the test fixture
#    actually reproduces the incident rather than accidentally slug-matching.
# ---------------------------------------------------------------------------
print("slugify(name) genuinely does not match either URL")
install_stubs()
target = d.slugify("SkinResQ™ Film Island Dressing 80mm x 60mm")
check("the slug the display name would produce is not in the URL",
      "dynaderm" not in target, target)

# ---------------------------------------------------------------------------
# 3. THE FALLBACK FINDS IT ANYWAY, by the name the page itself publishes.
# ---------------------------------------------------------------------------
print("the name-index fallback finds the product slug matching could not")
install_stubs()
url, why = d.find_product_url("electrospyres.test",
                              "SkinResQ™ Film Island Dressing 80mm x 60mm", None)
check("matched via the name index",
      url == "https://electrospyres.test/product/skinresq-dynaderm-film-island-dressing-80x60mm",
      (url, why))
url2, _ = d.find_product_url("electrospyres.test",
                             "Pneumo SOS™ Vented Chest Seal", None)
check("the second product matched its own page",
      url2 == "https://electrospyres.test/product/pneumo-sos-vented-chest-seal", url2)

# ---------------------------------------------------------------------------
# 4. A NAME THE SITE DOES NOT PUBLISH IS STILL REFUSED, NOT GUESSED AT.
# ---------------------------------------------------------------------------
print("a product the site does not carry is still refused")
u, why = d.find_product_url("electrospyres.test", "Something Else Entirely", None)
check("no URL returned", u is None, u)
check("and it says why", "no sitemap URL's slug matches" in (why or ""), why)
remove_stubs()

print()
if FAILURES:
    print("FAILED: %s" % ", ".join(FAILURES))
    sys.exit(1)
print("all cases pass — a descriptive-slug site whose names diverge from its "
      "own URLs is still sourced")
