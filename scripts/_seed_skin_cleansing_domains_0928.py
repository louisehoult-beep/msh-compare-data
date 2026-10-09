"""One-off: add proven website domains for 6 of Skin Cleansing, Disinfection
and Hygiene's needDomain suppliers. Framework-coverage batch, 28/09/2026.

PTP Healthcare Ltd -- ptphealthcare.net prints "Registered Company Number:
10896609" directly on the site, matching the existing companyNumberCandidate
(PTP HEALTHCARE LTD 10896609) and Companies House's registered office (Unit
17, Vicarage Farm Business Park, Winchester Road, Fair Oak, Eastleigh,
Hampshire, SO50 7HD), read 28/09/2026 -- the strongest tier (on-site
registration number, corroborated by Companies House).

Premium Wipes & Textiles Ltd -- pwt-uk.com/contact-details/ prints "Company
Registration Number: 12040483" and the registered office address, both
matching Companies House's PREMIUM WIPES AND TEXTILES LTD record exactly
(Unit 2, Warrington Central Trading Estate, Bewsey Road, Warrington, WA2
7LP), read 28/09/2026 -- on-site registration number, corroborated.

Procotech Limited -- procotech.com's own footer prints "13 Hornbeam Square
South, Harrogate, HG2 8NB", matching Companies House's PROCOTECH LTD
(05543851) registered office exactly, though the site does not itself print
the number -- domain-proof-tier address-match
(data/identity-vocabulary-policy.json), read 28/09/2026.

TerraMed Limited -- terramed.co.uk's own site prints "Suite 7, Innovation
House, Molly Millars Close, Wokingham, RG41 2RX", matching Companies House's
TERRAMED LIMITED (15484367, incorporated 12/02/2024) registered office
exactly -- domain-proof-tier address-match, read 28/09/2026. (A second,
unrelated company "TERRA MED" 10272444 also exists on Companies House; this
address match is specific to 15484367, not a name-only pick.)

Saraco Industries -- saraco-industries.com self-identifies as "Saraco
Industries Limited" and its Contact page prints "Egerton St, Farnworth,
Bolton BL4 7ER" -- a trading address, NOT the registered office Companies
House holds for SARACO INDUSTRIES LIMITED (05446285: Parkside House, 167
Chorley New Road, Bolton, BL1 4RA). Per the domain-proof-tier guard, a
trading address that is not the registered office does not satisfy the
address-match test, and the existing companyNumberCandidate is a name search
only (rule 11) -- so the domain is added here (it is genuinely the
company's own trading site, confirmed by phone/email on that site) but the
company number is deliberately left as a candidate, not promoted.

PAL International Ltd -- palinternational.com is genuinely the company's own
site (Medipal/Paltx/Palpro brands, matches this framework's "PAL
International Ltd" / "Pal International" aliases and sells chlorhexidine/
skin-cleansing wipes), but prints no registration number or address at all.
The seed's companyNumberNote already documents that Companies House carries
three equally plausible "PAL International" entities and rule 10/11 forbid
picking one -- domain added for crawl purposes only, company number left
unresolved.

Run once, then delete.
"""
import json

from seed_format import write_like, describe

PATH = "data/supplier-seed.json"

UPDATES = {
    "PTP Healthcare Ltd": {
        "label": "Website",
        "url": "https://www.ptphealthcare.net",
        "evidence": (
            "ptphealthcare.net prints \"Registered Company Number: "
            "10896609\" directly on the site, matching Companies House's "
            "PTP HEALTHCARE LTD record (registered office Unit 17, "
            "Vicarage Farm Business Park, Winchester Road, Fair Oak, "
            "Eastleigh, Hampshire, SO50 7HD) exactly -- on-site "
            "registration number, corroborated. Read 28/09/2026."
        ),
    },
    "Premium Wipes & Textiles Ltd": {
        "label": "Website",
        "url": "https://pwt-uk.com",
        "evidence": (
            "pwt-uk.com/contact-details/ prints \"Company Registration "
            "Number: 12040483\" and the registered office address, both "
            "matching Companies House's PREMIUM WIPES AND TEXTILES LTD "
            "record exactly (Unit 2, Warrington Central Trading Estate, "
            "Bewsey Road, Warrington, WA2 7LP) -- on-site registration "
            "number, corroborated. Read 28/09/2026."
        ),
    },
    "Procotech Limited": {
        "label": "Website",
        "url": "https://procotech.com",
        "evidence": (
            "procotech.com's own footer prints \"13 Hornbeam Square South, "
            "Harrogate, HG2 8NB\", matching Companies House's PROCOTECH "
            "LTD (05543851) registered office exactly, though the site "
            "does not itself print the number -- domain-proof-tier "
            "address-match (data/identity-vocabulary-policy.json). Read "
            "28/09/2026."
        ),
    },
    "TerraMed Limited": {
        "label": "Website",
        "url": "https://www.terramed.co.uk",
        "evidence": (
            "terramed.co.uk prints \"Suite 7, Innovation House, Molly "
            "Millars Close, Wokingham, RG41 2RX\", matching Companies "
            "House's TERRAMED LIMITED (15484367, incorporated 12/02/2024) "
            "registered office exactly -- domain-proof-tier address-match. "
            "A separate, unrelated company \"TERRA MED\" (10272444) also "
            "exists on Companies House; this match is specific to "
            "15484367 by address, not a name-only pick. Read 28/09/2026."
        ),
    },
    "Saraco Industries": {
        "label": "Website",
        "url": "https://www.saraco-industries.com",
        "evidence": (
            "saraco-industries.com self-identifies as \"Saraco Industries "
            "Limited\" and is genuinely the company's own trading site "
            "(Egerton St, Farnworth, Bolton BL4 7ER; own phone/email). "
            "That address is a trading address, not the registered office "
            "Companies House holds for SARACO INDUSTRIES LIMITED "
            "(05446285: Parkside House, 167 Chorley New Road, Bolton, BL1 "
            "4RA), so the domain-proof-tier address-match test is NOT "
            "satisfied and the existing companyNumberCandidate stays a "
            "candidate (rule 11 -- a name search is not evidence for a "
            "number). Domain added for crawl purposes only. Read "
            "28/09/2026."
        ),
    },
    "PAL International Ltd": {
        "label": "Website",
        "url": "https://palinternational.com",
        "evidence": (
            "palinternational.com is genuinely the company's own site "
            "(Medipal/Paltx/Palpro brands; sells chlorhexidine and skin-"
            "cleansing wipes matching this framework's scope) but prints "
            "no registration number or address anywhere. The seed's "
            "existing companyNumberNote already documents that Companies "
            "House carries three equally plausible \"PAL International\" "
            "entities (03272370, 14323014, 14290031) and rules 10/11 "
            "forbid picking one -- domain added for crawl purposes only, "
            "company number left unresolved. Read 28/09/2026."
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
