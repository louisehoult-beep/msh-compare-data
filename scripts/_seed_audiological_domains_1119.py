"""One-off seeder, framework-coverage batch 19/11/2026, working Audiological
Diagnostics Implantable Devices and Services (Neuromodulation recorded as
exhausted the same run).

Amplivox -> amplivox.com. Proved on the domain-proof-tier policy's ADDRESS
tier: the site's own contact page (https://amplivox.com/contact) and privacy
policy (https://amplivox.com/privacy-policy), read 19/11/2026, both name
"Amplivox Limited, Geneva House, International Park, Starley Way, Birmingham,
B37 7GN, United Kingdom", which matches Companies House's registered office for
AMPLIVOX LIMITED (01003695), read the same day. The site names the entity
itself next to the address, so this is not a bare shared-address match.
Its own news post (amplivox.com/knowledge-hub/amplivox-uk-operations-join-
diatec-diagnostics-ltd, 5 May 2026) says UK sales and support moved to Diatec
Diagnostics Ltd; the award still credits to "Amplivox" exactly as NHS Supply
Chain names it (parent-subsidiary-award-credit), and nothing is merged.

Not seeded, documented so they are not re-searched:
  - Guymark: guymark.com now redirects to diatec-diagnostics.co.uk, whose own
    site says Diatec UK was formed from Interacoustics UK, Guymark, Amplivox UK
    and Acoustic Metrology (Demant Group). Diatec is already a separate
    published record; under parent-subsidiary-award-credit its catalogue is
    not credited to Guymark and the two are not merged or aliased.
  - Audit Data: auditdata.com (Danish group site) names no UK entity on its
    contact page; cross-border-sibling-domain-attribution -> related brand
    site, not attributed.
  - Cosium Healthcare: cosium.com / cosium.co.uk (French group site) name no
    UK entity; Cosium UK Limited's registered office (Telford TF1 1EB per
    Companies House 11159879) is not printed. Same policy -> not attributed.
"""
import json

SEED = "data/supplier-seed.json"
ON = "2026-11-19"
RUN = "differentiator-framework-coverage scheduled run"

DOMAINS = [
    ("Amplivox", "amplivox.com",
     "Address tier (domain-proof-tier): amplivox.com/contact and "
     "amplivox.com/privacy-policy, read 2026-11-19, name \"Amplivox Limited, "
     "Geneva House, International Park, Starley Way, Birmingham, B37 7GN\", "
     "matching Companies House's registered office for AMPLIVOX LIMITED "
     "(01003695) read the same day."),
]

NOTES = {
    "Guymark": "Checked 19/11/2026: guymark.com redirects to diatec-diagnostics.co.uk; Diatec UK's own site says it was formed from Interacoustics UK, Guymark, Amplivox UK and Acoustic Metrology (Demant Group). Diatec is a separate record; under parent-subsidiary-award-credit its catalogue is not credited here and the records are not merged. No own domain -- do not re-search unless guymark.com stops redirecting.",
    "Audit Data": "Checked 19/11/2026: auditdata.com is the Danish group site and names no UK entity; recorded as a related brand site, not attributed (cross-border-sibling-domain-attribution). No confirmed UK domain.",
    "Cosium Healthcare": "Checked 19/11/2026: cosium.com (cosium.co.uk redirects there) is the French group site and prints neither a UK entity nor Cosium UK Limited's registered office; related brand site, not attributed (cross-border-sibling-domain-attribution). No confirmed UK domain.",
}


def main():
    doc = json.load(open(SEED))
    by_name = {s["name"]: s for s in doc["suppliers"]}
    for name, domain, evidence in DOMAINS:
        s = by_name[name]
        if s.get("domain"):
            print("already has a domain, skipping:", name)
            continue
        s["domain"] = domain
        s["domainEvidence"] = {"found": evidence, "on": ON, "run": RUN,
                               "route": "registered-address"}
        print("added domain:", name, "->", domain)
    for name, text in NOTES.items():
        s = by_name[name]
        if text in (s.get("note") or ""):
            continue
        s["note"] = ((s.get("note") or "") + " " + text).strip()
        print("noted:", name)
    with open(SEED, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
