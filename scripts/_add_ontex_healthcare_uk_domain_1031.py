#!/usr/bin/env python3
"""One-off: add Ontex Healthcare UK Ltd's confirmable domain to the seed,
proved by the address-tier route (registered-office address match).

Framework-coverage batch, 31/10/2026, Disposable and Washable Continence Care.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "Ontex Healthcare UK Ltd")
    rec["links"].append({
        "label": "Company website",
        "url": "https://www.id-direct.com/ukb2c/en/",
        "route": "address-tier",
        "source": ("Proved id-direct.com/ukb2c/en by registered-office address match on "
                   "2026-10-31 (domain-proof-tier policy, data/identity-vocabulary-policy.json, "
                   "ruled 20/09/2026): the site's own UK Terms and Conditions of Sale "
                   "(id-direct.com/ukb2c/en/page/conditions.html) names \"Ontex Healthcare UK "
                   "Ltd, Weldon House, 2nd Floor, NN17 5JG Corby, Northants, United Kingdom\" as "
                   "the UK main trading address, exactly matching Companies House's registered "
                   "office for ONTEX HEALTHCARE UK LIMITED (02274216) — \"2nd Floor, Original "
                   "Wing, Weldon House, Corbygate Business Park, Priors Haw Road, Corby, "
                   "Northamptonshire, United Kingdom, NN17 5JG\". The contracting party on the "
                   "page's own terms is the Belgian parent, Ontex BV (0419.457.296) — this UK "
                   "locale of the shared id-direct.com storefront is the only route carrying the "
                   "UK entity's own named trading address, so it is crawled scoped to its own "
                   "sitemap (id-direct.com/ukb2c/en/sitemap.xml) only, never the shared site's "
                   "other-market sitemaps, per no-parent-catalogue-credit-to-uk-subsidiary."),
    })
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain link for Ontex Healthcare UK Ltd")


if __name__ == "__main__":
    main()
