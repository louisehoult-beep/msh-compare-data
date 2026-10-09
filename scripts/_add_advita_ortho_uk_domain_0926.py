#!/usr/bin/env python3
"""One-off: add Advita Ortho UK Limited's confirmable domain to the seed,
proved by the address-tier route from the 20/09/2026 identity-vocabulary
policy (registered-office address match, not an on-site registration number).

Framework-coverage batch, 26/09/2026, Total Orthopaedic Solutions 3.

Identity check done first: two Companies House candidates surfaced by name
search (05316864 and 16540209). 16540209's CURRENT registered name is
"EXACTECH (UK) 2 LIMITED", not Advita — a different company. 05316864 is the
one company currently named "ADVITA ORTHO UK LIMITED", renamed from
"EXACTECH (UK) LIMITED" on 18/02/2026 (Companies House previous-names record),
matching the Nov 2025 global Advita Ortho rebrand of Exactech's shoulder/ankle
extremities business reported in trade press. No ambiguity once the rename
history is read.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "Advita Ortho UK Limited")
    rec["links"].append({
        "label": "Company website",
        "url": "https://uk.advita.com",
        "route": "address-tier",
        "source": ("Proved uk.advita.com by registered-office address match on 2026-09-26 "
                   "(domain-proof-tier policy, data/identity-vocabulary-policy.json, ruled "
                   "20/09/2026): the site's own Contact page states \"Prospect house, "
                   "Fishing Line Road, Redditch, B97 6EW\", exactly matching Companies "
                   "House's registered office for ADVITA ORTHO UK LIMITED (05316864) — "
                   "\"Prospect House, Fishing Line Road, Redditch, Worcestershire, United "
                   "Kingdom, B97 6EW\". Identity confirmed as 05316864, not the other name "
                   "candidate 16540209, which is currently registered as EXACTECH (UK) 2 "
                   "LIMITED, a different company. 05316864 was itself EXACTECH (UK) LIMITED "
                   "until renamed to ADVITA ORTHO UK LIMITED on 18/02/2026 (Companies House "
                   "previous-names record), matching the Nov 2025 global Advita Ortho "
                   "rebrand of Exactech's shoulder/ankle extremities business."),
    })
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain link for Advita Ortho UK Limited")


if __name__ == "__main__":
    main()
