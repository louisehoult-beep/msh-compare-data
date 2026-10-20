"""One-off: two digital-lane award spellings recorded as aliases, so they reach the
Hub's existing supplier records (20/10/2026).

Found by the health tech company-intel audit of 20/10/2026: both names sat
unresolved in data/digital-lane.json.

  Tortus AI Ltd -> seed "Tortus"
      Companies House 14487060 TORTUS AI LTD, active, incorporated 15/11/2022,
      SIC 62020 and 86900 (read 20/10/2026). The company's own privacy page,
      https://tortus.ai/privacy, states verbatim: "TORTUS AI LTD ('TORTUS AI')
      is registered as a limited company (Companies House No. 14487060) in the
      United Kingdom" (read 20/10/2026). company-financials.json already holds
      14487060 confirmed for this record.
  Clinisys Solution Limited -> seed "Clinisys Solutions Limited"
      Singular-for-plural typo of the registered name. Companies House search
      for "clinisys solution" (20/10/2026) returns no "Clinisys Solution"
      registration; the only match is 03477318 CLINISYS SOLUTIONS LIMITED,
      active, Woking, SIC 62012, which is the number company-financials.json
      already holds for this record.

NOT added here: Dedalus and EMIS / Egton have no supplier record to alias to.
They are seeded as new records, with their own sources, in the seeding batch.

Writes the seed and mirrors the alias into supplier-index.json, so the index is
right before the nightly rebuild copies the seed over it. Refuses an alias whose
normalised form already reaches a different Hub company. Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"

ALIASES = [
    # (seed record, alias, evidence)
    ("Tortus", "Tortus AI Ltd", "CH 14487060 TORTUS AI LTD; tortus.ai/privacy states Companies House No. 14487060"),
    ("Clinisys Solutions Limited", "Clinisys Solution Limited", "typo of CH 03477318 CLINISYS SOLUTIONS LIMITED; no 'Clinisys Solution' registration exists"),
]


def add(path, check_index):
    with open(path, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    by = {s.get("name"): s for s in doc["suppliers"]}
    idx = company_match.build_index(doc)
    added = 0
    for rec, alias, _why in ALIASES:
        sup = by.get(rec)
        if sup is None:
            raise SystemExit("%s: supplier not found: %s" % (path, rec))
        aliases = sup.setdefault("aliases", [])
        if alias in aliases:
            continue
        if check_index:
            others = ((idx.get(company_match.key(alias)) or set())
                      | (idx.exact.get(company_match.norm(alias)) or set()))
            if others - {rec}:
                raise SystemExit("alias %r already reaches %s" % (alias, sorted(others - {rec})))
        aliases.append(alias)
        added += 1
    if added:
        fmt, round_trips = write_like(path, doc)
        print(describe(path, fmt, round_trips))
    print("%s: added %d aliases" % (path, added))


def main():
    add(SEED, True)
    add(INDEX, False)


if __name__ == "__main__":
    main()
