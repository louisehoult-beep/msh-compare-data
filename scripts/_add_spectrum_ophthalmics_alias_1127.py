#!/usr/bin/env python3
"""Record Spectrum Ophthalmics as aliases of the Vision Pharmaceuticals Ltd seed record.

Why (27/11/2026): data/company-awards.json held eleven Contracts Finder awards by
The Queen Elizabeth Hospital King's Lynn NHS Foundation Trust (2021 to 2023) as
unmatched. Ten name the supplier "Spectrum Ophthalmics", one "Spectrum Ophthalmic".

Sources, read 27/11/2026: all eleven notices (Contracts Finder notice API) give the
supplier address as Fernbank House, Springwood Way, Macclesfield SK10 2XA.
spectrumophthalmics.uk/terms-of-use names Vision Pharmaceuticals Ltd ('Spectrum'),
company 02175795, at that address, as owner of the Spectrum Ophthalmics website.
Companies House 02175795: VISION PHARMACEUTICALS LTD, active.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seed_format

P = os.path.join(os.path.dirname(HERE), "data", "supplier-seed.json")
doc = json.load(open(P, encoding="utf-8"))
rec = [s for s in doc["suppliers"] if s.get("name") == "Vision Pharmaceuticals Ltd T/A Spectrum"]
assert len(rec) == 1, "expected one record"
al = rec[0].setdefault("aliases", [])
new = [a for a in ("Spectrum Ophthalmics", "Spectrum Ophthalmic") if a not in al]
if new:
    al.extend(new)
    fmt, ok = seed_format.write_like(P, doc)
    print(seed_format.describe(P, fmt, ok))
print("added", new)
