#!/usr/bin/env python3
"""One-off: add Contura Orthopaedics Ltd's confirmable domain to the seed,
proved by the address-tier route (registered-office address match).

Framework-coverage batch, 26/09/2026, Total Orthopaedic Solutions 3.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "Contura Orthopaedics Ltd")
    rec["links"].append({
        "label": "Company website",
        "url": "https://contura.com",
        "route": "address-tier",
        "source": ("Proved contura.com by registered-office address match on 2026-09-26 "
                   "(domain-proof-tier policy, data/identity-vocabulary-policy.json, ruled "
                   "20/09/2026): the site's own Contact Us page lists \"CONTURA "
                   "ORTHOPAEDICS\" at \"Contura International Limited, 14 Took's Court, "
                   "London EC4A 1LB\", exactly matching Companies House's registered office "
                   "for CONTURA ORTHOPAEDICS LIMITED (13119470) — \"14 Took's Court, London, "
                   "United Kingdom, EC4A 1LB\". The site groups the Arthrosamid orthopaedics "
                   "range under the same UK office and phone number as the parent Contura "
                   "International Limited, at the exact registered address of the named "
                   "awardee."),
    })
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain link for Contura Orthopaedics Ltd")


if __name__ == "__main__":
    main()
