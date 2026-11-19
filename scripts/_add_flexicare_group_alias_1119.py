#!/usr/bin/env python3
"""Record FLEXICARE (GROUP) LIMITED as an alias of the Flexicare Medical seed record.

Why (19/11/2026)
----------------
The daily refresh failed the company-report gate: data/company-financials.json
holds a Companies House record for FLEXICARE (GROUP) LIMITED (09109193), but no
supplier record carried that name. Until 18/11 only the GENERATED
supplier-index.json carried it, so a rebuild that dropped it took the gate red.
data/company-awards.json lists the Find a Tender award "Medical Consumables -
Oxygen Therapy FLEXICARE" to FLEXICARE (GROUP) LIMITED as unmatched and says to
add the alias to the seed. This does that, in the seed, so it cannot flap.

Source, read 19/11/2026
-----------------------
Companies House, persons with significant control of FLEXICARE MEDICAL LIMITED
(02428573): "Flexicare (Group) Limited", Active, registration number 09109193,
notified 3 October 2016, ownership of shares 75% or more, voting rights 75% or
more, right to appoint or remove directors. Companies House overview of
09109193: FLEXICARE (GROUP) LIMITED, active, incorporated 1 July 2014,
registered office Cynon Valley Business Park, Mountain Ash CF45 4ER.

The parent is named as the awarded party for Flexicare-branded products; the
alias lets that award attach to the Flexicare record. No figures move between
the two entities: the company-report gate still keeps each registration's own
finances apart.
"""
import json
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "supplier-seed.json")
ALIAS = "FLEXICARE (GROUP) LIMITED"

raw = open(P, encoding="utf-8").read()
doc = json.loads(raw)
rec = [s for s in doc["suppliers"] if s.get("name") == "Flexicare Medical"]
assert len(rec) == 1, "expected one Flexicare Medical record"
al = rec[0].setdefault("aliases", [])
if ALIAS not in al:
    al.append(ALIAS)
    indent = 1 if raw.startswith('{\n "') else 2
    with open(P, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=indent, ensure_ascii=False)
        fh.write("\n" if raw.endswith("\n") else "")
    print("added", ALIAS)
else:
    print("already present")
