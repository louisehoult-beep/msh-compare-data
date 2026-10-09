#!/usr/bin/env python3
"""One-off: add B.N.O.S Meditech Ltd's confirmable domain to the seed, proved by
the address-tier route from the 20/09/2026 identity-vocabulary policy
(registered-office address match, not an on-site registration number).

Framework-coverage batch, 07/10/2026, Respiratory Solutions (needDomain item).

Identity check done first: company-financials.json already records 02368331
(B.N.O.S. MEDITECH LIMITED, active, incorporated 04/04/1989), with previous name
B.N.O.S. R.F. PRODUCTS LIMITED. Companies House registered office for 02368331 is
"Unit 9 Fifth Avenue, Bluebridge Industrial Estate, Halstead, Essex, CO9 2SZ",
which is the address printed in the footer of meditech.uk.com. The site prints
no registration number, so the strong tier is not available; this is the
address tier. The address is a works unit on an industrial estate, not a shared
serviced office.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "B.N.O.S Meditech Ltd")
    rec["links"].append({
        "label": "Company website",
        "url": "https://www.meditech.uk.com",
        "route": "address-tier",
        "source": ("Proved meditech.uk.com by registered-office address match on 2026-10-07 "
                   "(domain-proof-tier policy, data/identity-vocabulary-policy.json, ruled "
                   "20/09/2026): the site's own footer states \"Unit 9, Fifth Avenue, "
                   "Bluebridge Industrial Estate, Halstead, Essex, CO9 2SZ\" and the "
                   "copyright line \"B.N.O.S. Meditech Ltd\", exactly matching Companies "
                   "House's registered office for B.N.O.S. MEDITECH LIMITED (02368331) — "
                   "\"Unit 9 Fifth Avenue, Bluebridge Industrial Estate, Halstead, Essex, "
                   "CO9 2SZ\". Identity 02368331 is already recorded in company-financials.json; "
                   "the site prints no registration number."),
    })
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain link for B.N.O.S Meditech Ltd")


if __name__ == "__main__":
    main()
