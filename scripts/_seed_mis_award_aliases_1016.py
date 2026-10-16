"""One-off: two Find a Tender award spellings on the Minimally Invasive Surgery
framework (2026/S 000-061906) recorded as aliases, so their lots attach to the
brief's supplier (16/10/2026).

Found while checking the Hub for a Schultz Medical demo: the award notice
https://www.find-tender.service.gov.uk/Notice/061906-2026 (read in Chrome
16/10/2026) has Lot 3 = 17, Lot 4 = 46, Lot 5 = 22, Lot 7 = 12 contractors; the
Hub showed 16 / 45 / 21 / 11 because these two names sat in `unresolved`.

  Genmed Enterprises International Ltd -> seed "Genmed Enterprises Ltd"
      CH: company-financials.json matches the seed record to 12992754 GENMED
      ENTERPRISES INTERNATIONAL LTD (Cardiff, SIC 32500), the award's own
      contractor name. No company is registered as "Genmed Enterprises Ltd"
      (CH search 16/10/2026 returns only ...INTERNATIONAL LTD 12992754 and
      ...UK LTD 10715490). Within this one procurement the brief names exactly one
      Genmed and the award names exactly one, and the other 57 award contractors
      all resolve to brief names. The overlay's distinct rule (International is
      NOT the pathology "Genmed" / Genmed Ltd record) is untouched.
  Advanced Medial Solutions Limited -> seed "Advanced Medical Solutions (AMS)"
      typo ("Medial") of the brief's own name "Advanced Medical Solutions Ltd",
      which already resolves to this record; CH 02666957 ADVANCED MEDICAL
      SOLUTIONS LIMITED. No "Advanced Medial Solutions" registration exists.

NOT added: "Vanguard Medical Devices Ltd" (award, Lot 2) vs brief "Vanguard AG".
CH 12215708 VANGUARD MEDICAL DEVICES LIMITED (London) has an individual as its
only PSC, not Vanguard AG, so it is a separate legal entity and stays
unresolved under the repo rule.

The script refuses to add an alias whose normalised form already reaches a
different Hub company. Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

PATH = "data/supplier-seed.json"

ALIASES = [
    # (seed record, alias, evidence)
    ("Genmed Enterprises Ltd", "Genmed Enterprises International Ltd", "CH 12992754 is this record's matched number; award 061906-2026 contractor"),
    ("Advanced Medical Solutions (AMS)", "Advanced Medial Solutions Limited", "typo of the brief's 'Advanced Medical Solutions Ltd' (CH 02666957)"),
]


def main():
    with open(PATH, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    by = {s.get("name"): s for s in doc["suppliers"]}
    idx = company_match.build_index(doc)
    added = 0
    for rec, alias, _why in ALIASES:
        if "gbuk" in rec.lower():
            raise SystemExit("refusing to touch GBUK")
        sup = by.get(rec)
        if sup is None:
            raise SystemExit("supplier not found: %s" % rec)
        aliases = sup.setdefault("aliases", [])
        if alias in aliases:
            continue
        others = (idx.get(company_match.key(alias)) or set()) | (idx.exact.get(company_match.norm(alias)) or set())
        if others - {rec}:
            raise SystemExit("alias %r already reaches %s" % (alias, sorted(others - {rec})))
        aliases.append(alias)
        added += 1
    if not added:
        print("all aliases already present, nothing to do")
        return
    fmt, round_trips = write_like(PATH, doc)
    print("added %d aliases" % added)
    print(describe(PATH, fmt, round_trips))


if __name__ == "__main__":
    main()
