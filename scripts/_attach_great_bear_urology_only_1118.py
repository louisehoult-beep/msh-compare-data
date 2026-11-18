#!/usr/bin/env python3
"""Attach ONLY the Urology and Bowel Management lot match from this run.

scripts/_rematch_framework_lot_unresolved_1117.py resolves five source
spellings once a Hub record exists for CLINISUPPLIES GB LIMITED (02503030).
One of them is this job's: "Great Bear Healthcare Ltd" on NHS Supply Chain's
Urology and Bowel Management, verified at source 2026-11-18 from the OCDS
release for ocds-h6vhtk-03c1e4, where the award relatedLots for that party
are 1, 2, 3, 5 and 13 (recorded as
~/.claude/framework-claims/032330-2023-2026-11-18.json).

The other four -- Uniphar Medtech UK Limited on Airway Management,
P.W.Coole & Son Limited on Electrosurgical Consumables, Ortus Technology
Limited on External Defibrillation Devices and Jenavalve Production Limited
on Transcatheter Heart Valve -- are NOT this job's and are NOT written here.
They were already pending at HEAD: the rematch run on an unmodified clone
resolves four of the five without this record, so they were unlocked by the
matcher tier that landed in 4ac02c7 and have simply not been re-run since.

Two of them check out at source today (Airway Lot 2; Electrosurgical Lots 1
and 6). Two do not:
  * Ortus Technology Limited. The OCDS release package for the ocid printed
    on notice 050296-2025 (ocds-h6vhtk-0333fc) comes back as a DIFFERENT
    notice's release, 103405-2026-1, with a single lot -- so the lots stored
    against Ortus cannot be read off it. Publishing Lots 1, 2 and 3 on that
    basis would be taking lots from a neighbouring record, which is the exact
    thing Lou ruled out on 17/11/2026.
  * Jenavalve Production Limited. Its lot source is a product-matrix
    spreadsheet, not a Find a Tender notice, so framework_award_check.py does
    not cover it and it was not read today.
A lot a Hub card asserts needs a same-day read of the notice itself. These
four are a separate, verifiable job; leaving them pending costs nothing,
because an unattached name is a question for a human, not a loss.

SINCE SUPERSEDED for those four: all four were read at source later the same
day and are attached by scripts/_attach_remaining_four_lot_matches_1118.py,
whose docstring records each read. The Ortus doubt above was a too-narrow read
of one release, not a conflict between sources -- see that script. This script
is kept as written because it is the thing that ran, and it stays a no-op.

Idempotent: re-running changes nothing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seed_format  # noqa: E402
import refresh_framework_lots as R  # noqa: E402

URL = ("https://www.supplychain.nhs.uk/product-information/"
       "contract-launch-brief/urology-and-bowel-management/")
ROW = "Clinisupplies GB Limited"
SOURCE_NAME = "Great Bear Healthcare Ltd"
LOTS = ["Lot 1", "Lot 2", "Lot 3", "Lot 5", "Lot 13"]

FULL = sys.argv[1] if len(sys.argv) > 1 else "/tmp/full-rematch.json"

lots_doc = json.load(open(R.LOTS_PATH, encoding="utf-8"))
cur = lots_doc["frameworks"][URL]

if (cur.get("supplierLots") or {}).get(ROW) == LOTS:
    print("framework-lots.json: already as intended")
    sys.exit(0)

full = json.load(open(FULL, encoding="utf-8"))["frameworks"][URL]
got = (full.get("supplierLots") or {}).get(ROW)
if got != LOTS:
    raise SystemExit(
        "the rematch output attaches %r to %r, not the lots verified at "
        "source today (%r); refusing to write." % (got, ROW, LOTS)
    )
named = (full.get("namedAs") or {}).get(ROW)
if named != [SOURCE_NAME]:
    raise SystemExit(
        "the rematch output names %r as %r, not %r; refusing to write."
        % (ROW, named, [SOURCE_NAME])
    )

# Take this one framework's entry wholesale from the rematch output, so every
# derived field on it (coversLots, lotsNotCovered, suppliersWithLots,
# suppliersWithoutLot, unresolved) is the matcher's own, not hand-computed.
lots_doc["frameworks"][URL] = full

fw_doc = json.load(open(R.FW_PATH, encoding="utf-8"))

# R.attach() re-resolves EVERY framework, so it would also write the four
# matches documented above into frameworks.json -- the file the Hub's cards
# actually read. Run it, then put every framework except this one back to the
# two keys it rewrites, so the published diff carries only the match that was
# verified at source today. Deliberately keyed off the attach output rather
# than hand-written, so this one entry is still the matcher's own work.
# frameworks.json holds a LIST of frameworks, each with its own url.
BEFORE = [
    {k: f.get(k) for k in ("supplierLots", "lotNamedAs") if k in f}
    for f in fw_doc["frameworks"]
]

R.attach(fw_doc, lots_doc)

# attach() only mutates fw_doc; writing it is this script's job.
held = []
for i, f in enumerate(fw_doc["frameworks"]):
    if f.get("url") == URL:
        continue
    for k, v in BEFORE[i].items():
        if f.get(k) != v:
            held.append(f.get("name") or f.get("url"))
            f[k] = v
for nm in sorted(set(held)):
    print("  held back (not verified today): %s" % nm)

fmt_fw, rt_fw = seed_format.write_like(R.FW_PATH, fw_doc)
seed_format.describe(os.path.basename(R.FW_PATH), fmt_fw, rt_fw)

fmt, round_trips = seed_format.write_like(R.LOTS_PATH, lots_doc)
seed_format.describe(os.path.basename(R.LOTS_PATH), fmt, round_trips)
print("  attached %s -> %s as %r" % (ROW, LOTS, SOURCE_NAME))
