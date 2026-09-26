#!/usr/bin/env python3
"""One-off: add Marquardt UK's confirmable domain to the seed, proved by the
registration number printed on the site's own imprint page.

Framework-coverage batch, 26/09/2026, Total Orthopaedic Solutions 3.
"""
import json

SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED))
    rec = next(s for s in seed["suppliers"] if s.get("name") == "Marquardt UK")
    rec["links"].append({
        "label": "Company website",
        "url": "https://marquardt-uk.com",
        "route": "registration",
        "source": ("Proved marquardt-uk.com by registration number on 2026-09-26: the "
                   "site's own Legal notice/imprint page states \"Marquardt U.K. Ltd. "
                   "... Registration (England) 6206385\", matching Companies House "
                   "06206385 (MARQUARDT U.K. LIMITED), which this record's own "
                   "previousNames entry already ties to this supplier via the "
                   "\"ORTHOPAEDIC IMPLANTS LIMITED\" former name."),
    })
    with open(SEED, "w") as f:
        json.dump(seed, f, separators=(",", ":"), ensure_ascii=False)
    print("Added domain link for Marquardt UK")


if __name__ == "__main__":
    main()
