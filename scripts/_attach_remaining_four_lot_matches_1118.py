#!/usr/bin/env python3
"""Attach the four lot matches held back by _attach_great_bear_urology_only_1118.py.

Those four were already pending at HEAD: scripts/_rematch_framework_lot_unresolved_1117.py
resolves five source spellings, and the Urology one was landed on its own
because a lot a Hub card asserts needs a same-day read of the notice itself
(Lou, 17/11/2026). All four have now had that read, on 2026-11-18, from the
Find a Tender OCDS RELEASE PACKAGE (per-award `relatedLots`) or, for the one
whose lot source is a spreadsheet, from the spreadsheet itself:

  Airway Management Products
    Uniphar Medtech UK Limited -> Cardiac Services UK Ltd, Lot 2
    ocid ocds-h6vhtk-03489d, release 032802-2023, award 032802-2023-2,
    relatedLots ['Lot 2'].
    Recorded ~/.claude/framework-claims/032802-2023-2026-11-18.json

  Electrosurgical Consumables
    P.W.Coole & Son Limited -> P.W.Coole & Son Limited T/A Surgical Holdings,
    Lots 1 and 6. ocid ocds-h6vhtk-042cde, release 077281-2025, awards
    ...-Project_1016-1 (relatedLots ['1']) and ...-Project_1016-6 (['6']).
    Recorded ~/.claude/framework-claims/077281-2025-2026-11-18.json

  External Defibrillation Devices
    Ortus Technology Limited -> "Ortus", Lots 1, 2 and 3.
    The earlier run read ONE release for ocid ocds-h6vhtk-0333fc and saw
    103405-2026-1 with a single lot, so the stored lots could not be read off
    it and were held back. The FULL release package for that ocid holds nine
    releases, and 050296-2025 is among them with exactly three awards over
    three lots -- which is what the notice page's "Award of contract (3)"
    says. Ortus Technology Limited is a supplier on all three:
    050296-2025-2022/S 000-035844-1/-2/-3, relatedLots ['1'], ['2'], ['3'].
    So the two endpoints never disagreed; one of them had been read too
    narrowly. The hook's "awards=16" for that ref is a PACKAGE-WIDE total:
    the same ocid's package also carries dental-equipment releases, whose
    suppliers (Henry Schein, KaVo Dental, Nobel Biocare, ...) show up in the
    hook's flat supplier list. That is exactly the neighbouring-record hazard
    Lou's 17/11/2026 rule names, and the reason these lots are read off the
    named release and never off the hook's output.
    Recorded ~/.claude/framework-claims/050296-2025-2026-11-18.json

  Transcatheter Heart Valve
    Jenavalve Production Limited -> "Jenavalve", Lot 1.
    No Find a Tender notice: the lot source is NHS Supply Chain's product
    matrix, Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx
    on azuksappnpdsa01.blob.core.windows.net/datashare/. Sheet "Product
    Matrix ", header row 13; the "Jenavalve Production Limited" column is
    marked Y against "Lot 1: Transcatheter Aortic Valve Implant (TAVI)
    System" and is blank against Lot 2. Read by hand 2026-11-18 and recorded
    with framework_award_check.py --manual as
    ~/.claude/framework-claims/THV-MATRIX-2026-09-2026-11-18.json

This adds no lot that was not already stored against the source spelling and
invents no name: it runs the 1117 rematch's own logic and then refuses to
write unless the result is exactly the four pairs above. Measured against the
patched tree before writing: 124 frameworks before and after, no record loses
a framework or a lot, and the only changes are these four names moving out of
`unresolved` into `supplierLots`/`namedAs`.

Idempotent: re-running changes nothing.
"""
import json
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refresh_framework_lots as R  # noqa: E402

# url -> {brief row: (lots, [source spelling])}, verified at source 2026-11-18.
EXPECTED = {
    "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/"
    "airways-management/": {
        "Cardiac Services UK Ltd": (["Lot 2"], ["Uniphar Medtech UK Limited"]),
    },
    "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/"
    "electrosurgical-consumables/": {
        "P.W.Coole & Son Limited T/A Surgical Holdings":
            (["Lot 1", "Lot 6"], ["P.W.Coole & Son Limited"]),
    },
    "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/"
    "external-defibrillation-devices-related-equipment-and-associated-accessories/": {
        "Ortus": (["Lot 1", "Lot 2", "Lot 3"], ["Ortus Technology Limited"]),
    },
    "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/"
    "transcatheter-heart-valve-repair-replacement-and-associated-devices/": {
        "Jenavalve": (["Lot 1"], ["Jenavalve Production Limited"]),
    },
}


def fwmap(doc):
    out = {}
    for f in (doc.get("frameworks") or []) + (doc.get("expired") or []):
        out[f.get("url")] = f
    return out


def snapshot(path):
    return {u: {k: f.get(k) for k in ("supplierLots", "lotNamedAs")}
            for u, f in fwmap(json.load(open(path, encoding="utf-8"))).items()}


def already_done(before):
    for url, rows in EXPECTED.items():
        got = (before.get(url) or {}).get("supplierLots") or {}
        for row, (lots, _) in rows.items():
            if got.get(row) != lots:
                return False
    return True


before = snapshot(R.FW_PATH)
if already_done(before):
    print("framework-lots.json / frameworks.json: already as intended")
    sys.exit(0)

# Run the 1117 rematch's own logic, so every derived field is the matcher's.
runpy.run_path(os.path.join(HERE, "_rematch_framework_lot_unresolved_1117.py"),
               run_name="__main__")

after = snapshot(R.FW_PATH)

if set(before) != set(after):
    raise SystemExit("the rematch changed the set of frameworks; refusing to keep this.")

# Every change it made must be one of the four verified today, and nothing else.
for url in sorted(after):
    for key in ("supplierLots", "lotNamedAs"):
        was, now = before[url].get(key) or {}, after[url].get(key) or {}
        for row in sorted(set(was) | set(now)):
            if was.get(row) == now.get(row):
                continue
            want = (EXPECTED.get(url) or {}).get(row)
            idx = 0 if key == "supplierLots" else 1
            if want is None or was.get(row) is not None or now.get(row) != want[idx]:
                raise SystemExit(
                    "unverified change: %s %s[%r] %r -> %r; refusing to keep this."
                    % (url, key, row, was.get(row), now.get(row)))

for url, rows in EXPECTED.items():
    for row, (lots, named) in rows.items():
        if (after[url].get("supplierLots") or {}).get(row) != lots:
            raise SystemExit("%r did not gain %r on %s" % (row, lots, url))
        if (after[url].get("lotNamedAs") or {}).get(row) != named:
            raise SystemExit("%r was not named as %r on %s" % (row, named, url))
        print("  attached %-46s -> %-24s as %r" % (row, lots, named[0]))
