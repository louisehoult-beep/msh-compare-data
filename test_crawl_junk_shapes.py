#!/usr/bin/env python3
"""
test_crawl_junk_shapes.py — the crawl shapes that put junk in front of members
in the Differentiator, found 28/09/2026 during the wound dossier rebuild, and
the guards that now refuse each one.

  1. A CMS record id as a product name. convatec.com files some products at a
     bare GUID leaf (.../pc-wound-open-surgical-wounds/1b845cb1-2f05-476d-bc85-
     e40feb9bb7a2 is AQUACEL Ribbon), and the range crawl title-cased the slug
     into "1B845Cb1 2F05 476D Bc85 E40Feb9Bb7A2" — 42 Convatec rows, 13 published.
  2. Site chrome as a description. "<main\\b" matched convatec.com's <main-nav>
     custom element, so "the main content" was the header: the login-status flag
     and a 60-country language picker ("False /oidc-signin/en-gb/ България ...").
     37 records, 27 published.
  3. Brochure download pages under the product path (Mölnlycke's Belgian
     locales), a taxonomy index page (Convatec "Product Names"), and a guidance
     page nested under its product (L&R /debrisoft/nice-guidance), which also
     made the prefix test drop Debrisoft itself as a category page.

Offline: every fetch is served from fixtures below.

  python3 test_crawl_junk_shapes.py     exit 0 = none of these shapes can be captured
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, HERE)
import crawl_supplier_site as cs                     # noqa: E402
import crawl_supplier_product_detail as d            # noqa: E402
import verify                                        # noqa: E402

HOST = "example.test"

PICKER = ("False /oidc-signin/en-gb/ България Bosna i Hercegovina Česko Danmark Österreich "
          "Schweiz (Deutsch) Deutschland Ελλάδα United Kingdom Ireland España Eesti Suomi "
          "Suisse (Français) France Hrvatska Magyarország Ísland Italia Lietuva Latvija")

# The convatec.com shape, cut down: a <main-nav> custom element in the header
# carrying the login slot and the language picker, and the real <main> later.
CONVATEC_PAGE = """<html><head><title>AQUACEL&#xAE; Ribbon Dressing - Wound | ConvaTec</title></head>
<body><header-bar>
<main-nav data="[]"><span slot="login-status">False</span>
<span slot="auth-href">/oidc-signin/en-gb/</span>
<ul><li>България</li><li>Česko</li><li>Danmark</li><li>Österreich</li><li>Deutschland</li>
<li>Ελλάδα</li><li>España</li><li>Eesti</li><li>Suomi</li><li>Hrvatska</li></ul></main-nav>
</header-bar>
<main><div class="content" id="main-content">
<h1>AQUACEL<sup>&#174;</sup> Ribbon Dressing with Strengthening Fiber</h1>
<p>AQUACEL Ribbon Hydrofiber Dressing with Strengthening Fibre is a soft, sterile, non-woven
pad dressing composed of sodium carboxymethylcellulose and regenerated cellulose fibre.</p>
<ul><li>Absorbs wound fluid and forms a soft gel</li><li>Supports autolytic debridement</li></ul>
</div></main></body></html>"""

PLAIN_PRODUCT = """<html><head><title>%s</title></head><body><main><h1>%s</h1>
<p>A product description long enough to be product copy, and nothing else at all.</p>
</main></body></html>"""


def _sitemap(urls):
    return ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join("<url><loc>%s</loc></url>" % u for u in urls) + "</urlset>")


class _Fixture(object):
    def __init__(self, pages):
        self.pages = pages
        self.fetched = []

    def __call__(self, url, as_json=False, timeout=30):
        self.fetched.append(url)
        try:
            return self.pages[url], {}
        except KeyError:
            raise IOError("HTTP Error 404: Not Found")


def _crawl(urls, pages=None):
    all_pages = {"https://%s/sitemap.xml" % HOST: _sitemap(urls)}
    all_pages.update(pages or {})
    real = cs.get
    fx = _Fixture(all_pages)
    cs.get = fx
    try:
        return cs.sitemap_products(HOST), fx
    finally:
        cs.get = real


def _u(path):
    return "https://%s/%s" % (HOST, path)


# Enough ordinary products under two divisions that the range is a catalogue.
BASE = [_u("products/wound-care/dressing-%s" % c) for c in "abcdefgh"] + \
       [_u("products/stoma-care/pouch-%s" % c) for c in "abcd"]


class SiteChromeIsNotADescription(unittest.TestCase):
    def test_main_nav_custom_element_is_not_main(self):
        frag = d.main_content_fragment(CONVATEC_PAGE)
        self.assertIn("Strengthening Fibre", frag)
        self.assertNotIn("oidc-signin", frag)
        self.assertNotIn("България", frag)

    def test_picker_and_login_slot_are_recognised(self):
        self.assertTrue(d.looks_like_site_chrome(PICKER))
        self.assertTrue(d.looks_like_site_chrome("True /login/en-gb/ Search Products"))

    def test_steris_region_picker_is_chrome_without_double_counting(self):
        steris = ("Select Your Region United States Canada (EN) Canada (FR) Deutschland "
                  "España France Italia United Kingdom Australia 日本 New Zealand Brasil México")
        self.assertTrue(d.looks_like_site_chrome(steris))
        self.assertTrue(verify._diff_site_chrome(steris))
        # "Deutsch" inside "Deutschland" is one name, not two.
        self.assertFalse(d.looks_like_site_chrome("Deutschland España Italia Brasil"))

    def test_crawler_and_gate_agree(self):
        self.assertEqual(set(d.LANGUAGE_PICKER_NAMES), set(verify._DIFF_PICKER_NAMES))
        self.assertEqual(d.CHROME_MIN, 5)

    def test_a_description_naming_a_country_or_two_is_product_copy(self):
        self.assertFalse(d.looks_like_site_chrome(
            "Made in Deutschland and sold across España and Italia since 1998."))
        self.assertFalse(d.looks_like_site_chrome(
            "False negatives are reduced by the indicator layer."))

    def test_page_detail_reads_the_real_copy(self):
        rec, why = d._detail_from_html(_u("p"), CONVATEC_PAGE)
        self.assertIsNotNone(rec, why)
        self.assertIn("carboxymethylcellulose", rec["description"])
        self.assertFalse(d.looks_like_site_chrome(rec["description"]))

    def test_a_page_that_is_only_chrome_is_refused(self):
        page = "<html><body><div>%s %s</div></body></html>" % (PICKER, "x " * 40)
        rec, why = d._detail_from_html(_u("p"), page)
        self.assertIsNone(rec)
        self.assertIn("header", why)

    def test_jsonld_description_that_is_chrome_is_dropped(self):
        page = ('<html><head><script type="application/ld+json">{"@type":"Product",'
                '"description":"%s","image":"https://x.test/i.jpg"}</script></head></html>' % PICKER)
        rec, why = d._detail_from_html(_u("p"), page)
        self.assertIsNotNone(rec, why)
        self.assertEqual(rec["description"], "")


STERIS_PAGE = """<html><body><div class="mega">You are using an outdated browser.
Select Your Region United States Canada (EN) Deutschland España France Italia United Kingdom
Australia 日本 Brasil México Products Sterile Processing</div>
<nav><ol><li>Home</li></ol></nav>
<div class="main-content-wrapper"><section><div class="col-md"><h1>ENDO-LEAK&trade; Tester</h1>
<ul><li>Endoscope leak tester to identify microscopic damage in flexible endoscopes</li></ul>
</div></section><section><p>The ENDO-LEAK Tester is a mechanical wet leak tester used during
manual cleaning.</p></section></div><footer>Deutschland España Italia</footer></body></html>"""


class MainContentMarker(unittest.TestCase):
    def test_a_site_with_no_main_reads_from_its_main_content_marker(self):
        rec, why = d._detail_from_html(_u("p"), STERIS_PAGE)
        self.assertIsNotNone(rec, why)
        self.assertIn("mechanical wet leak tester", rec["description"])
        self.assertNotIn("outdated browser", rec["description"])
        self.assertFalse(d.looks_like_site_chrome(rec["description"]))

    def test_a_real_main_still_wins_over_the_marker(self):
        frag = d.main_content_fragment(CONVATEC_PAGE)
        self.assertIn("Strengthening Fibre", frag)


class FurnitureInsideMain(unittest.TestCase):
    def test_search_widget_and_sample_form_are_not_copy(self):
        page = """<html><body><main><div id="main-content">
<section-title><h2 slot="headline">Search Products by Category</h2></section-title>
<pim-subnav data="[]"><a href="/x">Surgery Type</a><a href="/y">Product Names</a></pim-subnav>
<h1>Clip</h1><p>Available as a straight clip or curved tail closure for use with drainable pouches.</p>
<button type="button"><span>Request Sample</span></button>
<form method="post"><label>Title*</label><select><option>Mr</option><option>Mrs</option></select>
<label>First Name*</label></form></div></main></body></html>"""
        rec, why = d._detail_from_html(_u("p"), page)
        self.assertIsNotNone(rec, why)
        self.assertTrue(rec["description"].startswith("Clip Available"), rec["description"])
        for junk in ("Search Products", "Surgery Type", "Request Sample", "First Name"):
            self.assertNotIn(junk, rec["description"])


class UuidIsNotAName(unittest.TestCase):
    UID = "1b845cb1-2f05-476d-bc85-e40feb9bb7a2"

    def test_uuid_leaf_is_named_from_its_own_page(self):
        u = _u("products/wound-care/%s" % self.UID)
        (res, err), _ = _crawl(BASE + [u], {u: CONVATEC_PAGE})
        self.assertIsNone(err)
        names = [p["n"] for p in res["products"]]
        self.assertIn("AQUACEL® Ribbon Dressing with Strengthening Fiber", names)
        self.assertFalse(any(cs.is_uuid_slug(n.replace(" ", "-")) for n in names), names)
        row = [p for p in res["products"] if p["n"].startswith("AQUACEL")][0]
        self.assertEqual(row["division"], "Wound Care")

    def test_uuid_leaf_whose_page_gives_no_name_is_dropped(self):
        u = _u("products/wound-care/%s" % self.UID)
        (res, err), _ = _crawl(BASE + [u], {})          # page 404s
        self.assertIsNone(err)
        self.assertEqual(len(res["products"]), len(BASE))
        self.assertFalse(any("2F05" in p["n"] or "2f05" in p["n"] for p in res["products"]))

    def test_numeric_route_fallback_never_emits_a_uuid(self):
        urls = [_u("product/%d.php" % i) for i in range(10)] + [_u("product/%s" % self.UID)]
        pages = {u: PLAIN_PRODUCT % ("Blade %d" % i, "Blade %d" % i)
                 for i, u in enumerate(urls[:10])}
        real = cs.get
        cs.get = _Fixture(pages)
        try:
            res, err = cs.numeric_slug_products(HOST, urls)
        finally:
            cs.get = real
        self.assertIsNone(err)
        self.assertFalse(any(cs.is_uuid_slug(p["n"]) for p in res["products"]))
        self.assertEqual(len(res["products"]), 10)

    def test_detail_crawler_refuses_a_uuid_named_product(self):
        rec, why = d.capture_one(HOST, "1B845Cb1 2F05 476D Bc85 E40Feb9Bb7A2", None, 0)
        self.assertIsNone(rec)
        self.assertIn("UUID", why)

    def test_a_product_code_with_hex_digits_is_not_a_uuid(self):
        self.assertFalse(cs.is_uuid_slug("aquacel-ag-plus-extra"))
        self.assertFalse(cs.is_uuid_slug("10200002-gb-additional-otiom-tag"))


class NonProductLeaves(unittest.TestCase):
    def test_download_pages_and_taxonomy_index_are_dropped(self):
        extra = [_u("products/wound-care/download-ons-wondassortimentsboekje"),
                 _u("products/wound-care/telechargez-le-livret-d-assortiment-soins-des-plaies"),
                 _u("products/or-solutions/productcataloog-downloaden"),
                 _u("products/continence-care/product-names")]
        (res, err), _ = _crawl(BASE + extra)
        self.assertIsNone(err)
        names = {p["n"].lower() for p in res["products"]}
        for bad in ("download ons wondassortimentsboekje", "productcataloog downloaden",
                    "telechargez le livret d assortiment soins des plaies", "product names"):
            self.assertNotIn(bad, names)
        self.assertEqual(len(res["products"]), len(BASE))

    def test_a_locator_page_is_not_a_product(self):
        (res, err), _ = _crawl(BASE + [_u("products/wound-care/trufreeze-facility-finder")])
        self.assertIsNone(err)
        self.assertNotIn("Trufreeze Facility Finder", [p["n"] for p in res["products"]])
        self.assertFalse(cs.is_locator_leaf("pathfinder-guidewire"))
        self.assertFalse(cs.is_locator_leaf("finder-probe"))

    def test_a_product_that_is_a_download_cable_or_software_survives(self):
        for slug in ("nonin-data-download-cable-for-7500-pulse-oximeters",
                     "iem-mobil-o-graph-usb-download-cable", "visi-download",
                     "aed-plus-software-download"):
            self.assertFalse(cs.is_download_leaf(slug), slug)
        for slug in ("download-ons-wondassortimentsboekje", "productcataloog-downloaden",
                     "telechargez-le-livret-d-assortiment-soins-des-plaies",
                     "telecharger-catalogue-produit", "brochure-download", "downloads",
                     "download_new_"):
            self.assertTrue(cs.is_download_leaf(slug), slug)

    def test_a_product_named_with_download_as_a_substring_survives(self):
        (res, err), _ = _crawl(BASE + [_u("products/wound-care/downloadable-dressing-guide-x")])
        self.assertIn("Downloadable Dressing Guide X", [p["n"] for p in res["products"]])

    def test_guidance_subpage_is_dropped_and_its_product_restored(self):
        extra = [_u("products/wound-care/debrisoft"),
                 _u("products/wound-care/debrisoft/nice-guidance")]
        (res, err), _ = _crawl(BASE + extra)
        self.assertIsNone(err)
        rows = {p["n"]: p["division"] for p in res["products"]}
        self.assertNotIn("Nice Guidance", rows)
        self.assertEqual(rows.get("Debrisoft"), "Wound Care")

    def test_a_real_category_page_is_still_a_landing_page(self):
        # /products/wound-care/ has real product children: never a product.
        (res, err), _ = _crawl(BASE + [_u("products/wound-care")])
        self.assertNotIn("Wound Care", [p["n"] for p in res["products"]])


class UkCatalogueWins(unittest.TestCase):
    def test_uk_prefixed_copy_beats_an_unprefixed_other_market(self):
        us = [_u("products/ostomy-care/pouch-%s-us" % c) for c in "abcdefghij"]
        gb = [_u("en-gb/products/stoma-care/pouch-%s" % c) for c in "abcdefghij"]
        de = [_u("de-de/products/stomaversorgung/beutel-%s" % c) for c in "abcdefghij"]
        (res, err), _ = _crawl(us + gb + de)
        self.assertIsNone(err)
        self.assertEqual({p["division"] for p in res["products"]}, {"Stoma Care"})
        self.assertEqual(len(res["products"]), 10)

    def test_a_site_with_no_uk_copy_keeps_its_root(self):
        root = [_u("products/beds/bed-%s" % c) for c in "abcdefghij"]
        da = [_u("da/products/senge/seng-%s" % c) for c in "abcdefghij"]
        (res, err), _ = _crawl(root + da)
        self.assertEqual({p["division"] for p in res["products"]}, {"Beds"})


class PublishGate(unittest.TestCase):
    def test_gate_recognises_both_shapes(self):
        self.assertTrue(verify._DIFF_UUID_NAME.match("1B845Cb1 2F05 476D Bc85 E40Feb9Bb7A2"))
        self.assertFalse(verify._DIFF_UUID_NAME.match("Aquacel Ag Foam"))
        self.assertTrue(verify._diff_site_chrome(PICKER))
        self.assertFalse(verify._diff_site_chrome("A soft, sterile, non-woven pad dressing."))


class HelpPagesAreNotProducts(unittest.TestCase):
    """30/09/2026: wellspect.com's FAQ and instructions pages, filed under each
    product's path, were published as bowel-irrigation "products" ("Usage",
    "Medical Issue", "Navina Smart Faq") and offered on the Supply Disruption
    Tracker as 25 alternatives to a ureteral stent."""
    WS = "https://www.wellspect.com/products/bowel-products/navina-irrigation-systems/"

    def test_faq_and_instructions_urls_are_non_product(self):
        for leaf in ("faq-navina/usage/", "faq-navina/medical-issue/", "faq-navina/instillation/",
                     "faq-navina/disassembling-cleaning/", "faq-navina/navina-smart-faq/"):
            self.assertTrue(cs.is_non_product_url(self.WS + leaf), leaf)
        self.assertTrue(cs.is_non_product_url(
            "https://www.wellspect.com/products/bladder-products/lofric-elle/instructions/"))
        self.assertTrue(cs.is_non_product_url(
            "https://www.wellspect.com/products/bladder-products/lofric-sense/instructions/"
            "instructions-for-using-lofric-sense---tetraplegic-handling/"))
        self.assertTrue(cs.is_non_product_url("https://www.elekta.com/products/radiation-therapy/proknow-news/faqs/"))

    def test_real_products_are_not_caught(self):
        for u in (self.WS + "navina-smart/", self.WS + "navina-classic/",
                  "https://www.wellspect.com/products/bowel-products/navina-mini/",
                  # a real Convatec product at a GUID leaf, name read off the page
                  "https://www.convatec.com/en-gb/products/advanced-wound-care/wound-type/"
                  "pc-wound-open-surgical-wounds/1b845cb1-2f05-476d-bc85-e40feb9bb7a2",
                  "https://example.test/products/instructional-video-camera",
                  "https://example.test/products/fafaq-probe"):
            self.assertFalse(cs.is_non_product_url(u), u)

    def test_existing_shapes_route_through_the_same_entry_point(self):
        self.assertTrue(cs.is_non_product_url(_u("products/wound-care/download-ons-wondassortimentsboekje")))
        self.assertTrue(cs.is_non_product_url(_u("products/stoma-care/product-names")))
        self.assertTrue(cs.is_non_product_url(_u("products/vbx/case-studies/severe-claudication")))

    def test_crawl_drops_them(self):
        base = "products/bowel-products/navina-irrigation-systems/"
        real = [_u(base + "navina-%s" % c) for c in ("smart", "classic", "mini", "insert", "go",
                                                      "plus", "one", "two", "three", "four")]
        faq = [_u(base + "faq-navina/%s" % leaf) for leaf in ("usage", "medical-issue", "instillation")]
        (res, err), _ = _crawl(real + faq + [_u(base + "faq-navina")])
        self.assertIsNone(err)
        names = {p["n"] for p in res["products"]}
        for junk in ("Usage", "Medical Issue", "Instillation", "Faq Navina"):
            self.assertNotIn(junk, names)
        self.assertIn("Navina Smart", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
