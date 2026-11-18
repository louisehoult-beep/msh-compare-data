#!/usr/bin/env python3
"""Put the Beverages/Nestle lots back in quarantine, 18/11/2026 (pm).

WHAT WENT WRONG, AND WHERE
--------------------------
Commit fd12566 added the territory-preserving tier to
refresh_framework_lots.attach_names() and ran
scripts/_reattach_territory_tier_1118.py, which settled the two names the gate
had quarantined as reaching two rows on one brief. One of the two was right and
stays: "Clinisupplies Limited" -> the "Clinisupplies Ltd" row, which is
Companies House 04013240's own registered name while the other row is 02503030.

The other was wrong. Beverages, Confectionary and Snacks names both "Nestle Ltd"
and "Nestle UK", the award notice names "Nestle UK Ltd", and the tier narrowed
that to the "Nestle UK" row. That commit's reasoning was that attaching a lot to
a brief row creates no Hub record, and food is out of scope for records -- true,
but it is not what the Hub renders. app/company-report.js renders a COMPANY, not
a row: supplierFrameworks() collects every brief row whose coKey() matches one of
a record's own names or aliases, and fwLotLine() unions the lots of all of them.
coKey() strips "ltd" and "uk", so BOTH Nestle rows collapse onto "nestle" -- and
the only Nestle-keyed Hub record is Nestle Health Science UK, which carries a
bare alias "nestle".

So the live effect was a confectionery and beverages Lot 1 and Lot 13 asserted on
the card of Nestle Health Science UK, the clinical nutrition arm (ONS, enteral
feeds, Vitaflo per its own record) -- not the awardee. Before that commit the card
correctly read "Lot: not confirmed". That record's own identityNote, written
17/11/2026, had already ruled on this exact shape: "A bare group word cannot be
read as naming one of several Nestle entities", and left its Infant Feeding lots
unattached for that reason.

THE FIX
-------
attach_names()' territory tier now fires only where the seed holds BOTH the
source name and the chosen brief row VERBATIM on one record -- the same evidence
company_match's own verbatim tier turns on. Clinisupplies has it (the record
records "Clinisupplies Limited" and "Clinisupplies Ltd"); Nestle has neither
spelling, only the bare group word. Checked across every framework before this
was written: exactly one published row stops attaching, the one below.

This script removes that one attachment and puts the name back in `unresolved`
with the reason it had. It re-reads nothing, fetches nothing and touches no other
framework. Idempotent: it writes nothing once the row is gone.

Run:
    python3 scripts/_detach_nestle_beverages_lots_1118.py
    bash scripts/gate.sh
The gate's "TWO OR MORE rows" line returns, counting this one name. That is the
honest state and is recorded as decided in
state/two-brief-rows-one-key-adjudication-1118.json.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh_framework_lots as R  # noqa: E402
import seed_format  # noqa: E402

FW_NAME = "Beverages, Confectionary and Snacks"
ROW = "Nestle UK"
SOURCE_NAME = "Nestle UK Ltd"
LOTS = ["Lot 1", "Lot 13"]
KIND = "fts-award"
REASON = "matches 2 suppliers on this brief"


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    fwdoc = json.load(open(R.FW_PATH, encoding="utf-8"))
    lotsdoc = json.load(open(R.LOTS_PATH, encoding="utf-8"))
    by_url = {f.get("url"): f
              for f in (fwdoc.get("frameworks") or []) + (fwdoc.get("expired") or [])}

    target = [(u, r) for u, r in (lotsdoc.get("frameworks") or {}).items()
              if r.get("name") == FW_NAME]
    if len(target) != 1:
        raise SystemExit("expected exactly one %r framework, found %d" % (FW_NAME, len(target)))
    url, rec = target[0]

    if ROW not in (rec.get("supplierLots") or {}):
        print("%s: %r already carries no lot, nothing written" % (FW_NAME, ROW))
        return 0
    if (rec["supplierLots"][ROW]) != LOTS:
        raise SystemExit("%s: %r holds %s, not %s — stopping rather than guessing"
                         % (FW_NAME, ROW, rec["supplierLots"][ROW], LOTS))

    suppliers = (by_url.get(url) or {}).get("suppliers") or []
    rec["supplierLots"].pop(ROW)
    (rec.get("lotsBySource") or {}).get(KIND, {}).pop(ROW, None)
    (rec.get("namedAs") or {}).pop(ROW, None)
    rec["unresolved"] = sorted(
        [u for u in (rec.get("unresolved") or []) if u.get("name") != SOURCE_NAME]
        + [{"name": SOURCE_NAME, "lots": list(LOTS), "reason": REASON, "source": KIND}],
        key=lambda u: str(u.get("name") or ""))
    rec["status"] = "published" if rec["supplierLots"] else rec["status"]
    rec["suppliersWithoutLot"] = [x for x in suppliers if x not in rec["supplierLots"]] \
        if rec["status"] == "published" else []
    for q in rec.get("sources") or []:
        if "suppliersWithLots" in q:
            q["suppliersWithLots"] = len((rec.get("lotsBySource") or {}).get(q.get("kind")) or {})
    covered = sorted({l for q in rec.get("sources") or [] for l in q.get("coversLots") or []},
                     key=R.lot_sort_key)
    rec["coversLots"] = covered or None
    rec["lotsNotCovered"] = sorted(
        [k for k in (rec.get("lotTitles") or {})
         if not any(l == k or re.match(re.escape(k) + r"[.a-z]", l) for l in covered)],
        key=R.lot_sort_key) if rec["status"] == "published" else []

    lotsdoc["counts"] = {st: sum(1 for r in (lotsdoc.get("frameworks") or {}).values()
                                 if r.get("status") == st) for st in R.STATUSES}
    lotsdoc["rule"] = R.RULE

    fmt, rt = seed_format.write_like(R.LOTS_PATH, lotsdoc)
    print(" ", seed_format.describe(R.LOTS_PATH, fmt, rt))
    R.attach(fwdoc, lotsdoc)
    fmt, rt = seed_format.write_like(R.FW_PATH, fwdoc)
    print(" ", seed_format.describe(R.FW_PATH, fmt, rt))
    print("  - %s: %r no longer carries %s; %r back in unresolved (%s)"
          % (FW_NAME, ROW, LOTS, SOURCE_NAME, REASON))
    return 0


if __name__ == "__main__":
    sys.exit(main())
