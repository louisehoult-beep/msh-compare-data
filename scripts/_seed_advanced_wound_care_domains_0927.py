"""One-off: add proven website domains for 2 of Advanced Wound Care's needDomain
suppliers. Framework-coverage batch, 27/09/2026.

Clarity Pharma -- CLARITY PHARMA LTD, Companies House 03657934, registered
office "Unit 3 Mead Way, Great Hallingbury, Bishop's Stortford, CM22 7FD".
The company's own site (clarity-pharma.com/contact-us/) prints the identical
address, building and postcode -- domain-proof-tier's address-match test
(data/identity-vocabulary-policy.json), read 27/09/2026.

Firstkind Ltd -- FIRSTKIND LTD, Companies House 07161626. Its own site
(gekodevices.com) could not be read directly this session (empty response),
so this is not a registration- or address-match-tier proof. Instead it rests
on an independent third-party source: the ABHI (Association of British
HealthTech Industries) member directory entry for "Firstkind Ltd" names
www.gekodevices.com as that company's own website
(https://www.abhi.org.uk/membership/company/10830/firstkind-ltd, read
27/09/2026) -- a curated trade-association listing, not a guess from the
company name. Recorded as a distinct, weaker evidence tier ("third-party
directory") so a reader can judge it; crawl_supplier_site.py will still have
to prove it carries a real catalogue before anything publishes.

The third needDomain candidate checked this run, Phoenix Medical Ltd, is
deliberately NOT touched here: its existing supplier-seed.json record already
investigated phoenixmedical.com on 05/09/2026, found it bot-challenged
(HTTP 202) and unable to corroborate the company number, and recorded a
decision not to add it. Nothing found this session changes that. ClearHeal
LTD and Oswell Penda were also checked and left alone -- see the run report.

Run once, then delete.
"""
import json

from seed_format import write_like, describe

PATH = "data/supplier-seed.json"

UPDATES = {
    "Clarity Pharma": {
        "label": "Website",
        "url": "https://clarity-pharma.com",
        "evidence": (
            "Companies House 03657934 CLARITY PHARMA LTD registered office "
            "\"Unit 3 Mead Way, Great Hallingbury, Bishop's Stortford, CM22 "
            "7FD\" (read 27/09/2026); clarity-pharma.com/contact-us/ prints "
            "the identical address -- domain-proof-tier address-match "
            "(data/identity-vocabulary-policy.json)."
        ),
    },
    "Firstkind Ltd": {
        "label": "Website",
        "url": "https://www.gekodevices.com",
        "evidence": (
            "Third-party directory match, not registration- or address-"
            "tier: the ABHI member directory names \"Firstkind Ltd\" at "
            "www.gekodevices.com "
            "(https://www.abhi.org.uk/membership/company/10830/firstkind-"
            "ltd, read 27/09/2026). The site itself returned no readable "
            "content this session, so its own registration/address could "
            "not be cross-checked -- treat as a weaker tier than a "
            "registration-number or address match."
        ),
    },
}


def main():
    with open(PATH, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    suppliers = doc["suppliers"]
    by_name = {s.get("name"): s for s in suppliers}
    for name, link in UPDATES.items():
        sup = by_name.get(name)
        if sup is None:
            raise SystemExit("supplier not found: %s" % name)
        links = sup.setdefault("links", [])
        if any(l.get("label") == "Website" for l in links):
            print("%s already has a Website link, skipping" % name)
            continue
        links.append(link)
        print("added Website link for %s -> %s" % (name, link["url"]))
    fmt, round_trips = write_like(PATH, doc)
    print(describe(PATH, fmt, round_trips))


if __name__ == "__main__":
    main()
