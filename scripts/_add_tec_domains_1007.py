#!/usr/bin/env python3
"""One-off: add confirmed domains for Jabbla UK Ltd and Tobii Dynavox Ltd to the
seed — both needDomain items on the Technology Enabled Care framework.

Framework-coverage batch, 07/10/2026, Technology Enabled Care (lowest-coverage
STARTED, non-deferred, non-exhausted framework with work left, 33.3%/18 awarded).

Jabbla UK Ltd: domain found via Communication Matters UK professional register
and The Sequal Trust listings (independent AAC-sector directories), both naming
Jabbla UK Ltd at Kempton House, Kempton Way, Dysart Road, Grantham, Lincolnshire
NG31 7LE and pointing to jabbla.co.uk. The site itself prints no registration
number or address, so this is a directory-match, not a domain-proof-tier
address/number match. Crawled 07/10/2026: WordPress site exposes no product
post type and the WooCommerce Store API returns 404 — correctly refused, not
a product source.

Tobii Dynavox Ltd: domain found via Communication Matters UK professional
register, BATA and autism.org.uk (independent AAC-sector directories), each
naming Tobii Dynavox and pointing to uk.tobiidynavox.com; a company-registry
mirror (kompany.co.nz) separately gives company 05091720's registered office
as 1 Chapel Street, Warwick, CV34 4HL, consistent with the UK entity, though
not read directly off the site's own footer. Crawled 07/10/2026: Shopify
storefront, 32 products across Accessories/Apps & software/Uncategorised,
mapped (Accessories, Apps & software) to digital:aac in
data/differentiator-map-parts/Tobii Dynavox Ltd.json; per-product detail
captured via crawl_supplier_product_detail.py so the mapped rows carry a
source and publish.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    by_name = {s.get("name"): s for s in seed["suppliers"]}

    by_name["Jabbla UK Ltd"]["links"].append({
        "label": "Website",
        "url": "https://www.jabbla.co.uk",
        "source": ("Found via Communication Matters UK professional register and The "
                   "Sequal Trust listings (independent AAC-sector directories), both "
                   "naming Jabbla UK Ltd at Kempton House, Kempton Way, Dysart Road, "
                   "Grantham, Lincolnshire NG31 7LE and pointing to this domain. The site "
                   "itself prints no registration number or registered address. Crawled "
                   "07/10/2026 (framework-coverage-tec run): WordPress site exposes no "
                   "product post type and the WooCommerce Store API returns 404, so the "
                   "award is correctly recorded refused, not needDomain."),
    })
    by_name["Tobii Dynavox Ltd"]["links"].append({
        "label": "Website",
        "url": "https://uk.tobiidynavox.com",
        "source": ("Found via Communication Matters UK professional register, BATA and "
                   "autism.org.uk (independent AAC-sector directories), each naming Tobii "
                   "Dynavox and pointing to this domain; a company-registry mirror "
                   "(kompany.co.nz) separately gives company 05091720's registered office "
                   "as 1 Chapel Street, Warwick, CV34 4HL, consistent with the UK entity "
                   "(not read directly off the site's own footer). Crawled 07/10/2026 "
                   "(framework-coverage-tec run): Shopify storefront, 32 products captured "
                   "across Accessories/Apps & software/Uncategorised, mapped to digital:aac."),
    })

    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain links for Jabbla UK Ltd and Tobii Dynavox Ltd")


if __name__ == "__main__":
    main()
