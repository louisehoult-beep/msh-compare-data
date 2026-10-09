#!/usr/bin/env python3
"""One-off: add J & M Medical's confirmable domain to the seed, proved by the
own-site route (the site's own printed name matches an existing alias on
this exact record).

Framework-coverage batch, 27/09/2026, Electrosurgical Consumables and
Related Accessories.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "J & M Medical")
    rec["links"].append({
        "label": "Company website",
        "url": "https://www.jmmedical.co.uk",
        "route": "own-site",
        "source": ("Confirmed 27/09/2026: jmmedical.co.uk's own footer references "
                   "\"J & M Medical NE Ltd\" -- the exact existing alias on this "
                   "record -- and its Contact page phone number carries the 0191 "
                   "(Tyne & Wear) dialling code, consistent with J&M MEDICAL NE "
                   "LTD's Companies House registered office (Unit 1 Colliery School "
                   "Yard, Sunderland SR5 1DD, company 12602547). The site sells "
                   "genuine electrosurgical items (reusable/single-use monopolar "
                   "and bipolar diathermy forceps) matching this framework's scope, "
                   "alongside unrelated theatre footwear/PPE. Domain added to "
                   "enable a catalogue crawl attempt; no company number was found "
                   "printed on the site itself, so companyNumberNote (dissolved "
                   "J&M MEDICAL LTD vs active J&M MEDICAL NE LTD) is left "
                   "unresolved and not attached here -- rule 11 is about the "
                   "number specifically, not the domain."),
    })
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain link for J & M Medical")


if __name__ == "__main__":
    main()
