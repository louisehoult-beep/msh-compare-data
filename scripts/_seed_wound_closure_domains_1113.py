"""One-off seeder, framework-coverage batch 13/11/2026, working Wound Closure.
Adds confirmed domains for two of the framework's 7 domain-missing suppliers,
found by primary source during this run. The other 5 (Assut UK LTD, Lenience
UK Ltd, Pearsalls Ltd, GS Medical Healthcare Ltd (novating to GBUK Ltd), SAI
Medical Solutions Ltd) stay unconfirmed -- no route found that meets rule 11's
bar, left for OUTSTANDING.md:
  - Assut UK LTD: assutsutures.com is the Swiss parent (Assut Medical Sarl);
    a separate "Assut Europe S.p.A." UK branch is referenced in a supplier
    listing but no UK-specific domain or address was found.
  - Lenience UK Ltd: Companies House 12545155 confirmed, but no live site,
    product range or any other web presence found.
  - Pearsalls Ltd: now produced by Corza Medical (corza.com) at its former
    Taunton site, but corza.com is the PARENT GROUP's site -- publishing it
    under "Pearsalls Ltd" would breach no-parent-catalogue-credit-to-uk-
    subsidiary. pearsalls.co.uk (a directory-listed address) is a dead/parked
    domain (cert mismatch, resolves to domainlore.uk).
  - SAI Medical Solutions Ltd: Companies House 12347370 confirmed (previously
    "SAI Quality Veg & Fruits Ltd"), no website found.

Artivion UK Ltd -> artivion.com. The company's own global site's contact page
(https://artivion.com/contact/) names "Artivion UK Ltd." at "Bramley House,
The Guildway, Old Portsmouth Road, Guildford, Surrey GU3 1LR" -- confirmed by
cross-checking that exact address against Companies House 03837138's
registered office (read 13/11/2026), which matches verbatim. Satisfies the
domain-proof-tier policy's second (address-match) tier.

R&D Surgical Ltd -> randdsurgical.com. The site's own footer copyright states
"R&D Surgical Ltd." verbatim, and its LinkedIn link
(linkedin.com/company/r-&-d-surgical-limited) uses the same ampersand
trading name. No address or company number is shown on the site itself, so
this is NOT strong enough to attach a company number (rule 11) -- Companies
House 15539790 "RD SURGICAL LTD." (Manchester) is a plausible match on name
alone but is left unconfirmed; this entry only adds the domain so the site
can be crawled, not a companyNumberCandidate.

Run once: python3 scripts/_seed_wound_closure_domains_1113.py
"""
import json

SEED = "data/supplier-seed.json"

UPDATES = [
    ("Artivion UK Ltd", "artivion.com",
     "the company's own global site's contact page "
     "(https://artivion.com/contact/) names \"Artivion UK Ltd.\" at "
     "\"Bramley House, The Guildway, Old Portsmouth Road, Guildford, Surrey "
     "GU3 1LR\" -- cross-checked against Companies House 03837138's "
     "registered office, which matches verbatim (domain-proof-tier, address "
     "tier)."),
    ("R&D Surgical Ltd", "randdsurgical.com",
     "the site's own footer copyright states \"R&D Surgical Ltd.\" "
     "verbatim, corroborated by its LinkedIn company page "
     "(linkedin.com/company/r-&-d-surgical-limited) using the same "
     "ampersand trading name. No address or company number is shown on the "
     "site, so no company number is attached here -- domain only."),
]


def main():
    doc = json.load(open(SEED))
    by_name = {s["name"]: s for s in doc["suppliers"]}
    changed = 0
    for name, domain, evidence in UPDATES:
        s = by_name.get(name)
        if not s:
            print("NOT FOUND, skipping:", name)
            continue
        if s.get("domain"):
            print("already has a domain, skipping:", name, "->", s["domain"])
            continue
        s["domain"] = domain
        s["domainEvidence"] = {
            "found": evidence,
            "on": "2026-11-13",
            "run": "differentiator-framework-coverage scheduled run",
        }
        changed += 1
        print("added domain:", name, "->", domain)
    with open(SEED, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("changed %d supplier(s)" % changed)


if __name__ == "__main__":
    main()
