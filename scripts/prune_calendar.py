#!/usr/bin/env python3
"""
prune_calendar.py — drop the calendar rows that have aged into the past.

WHY THIS EXISTS. data/hub-calendar.json is a derived file: every row is a date
taken from a framework brief, an awareness day, an event or a contract. Dates do
not stay in the future. verify.py refuses to publish a calendar row whose date
has gone past (the one exception is a framework END inside the recent-past
window, which must be flagged `past`), and verify.py is the gate every workflow
in this repo runs before it commits.

So a single row ageing out takes the WHOLE repo down. That is not a theory:

  25/08/2026  fw-framework-start-disposable-and-washable-continence-care fell
              one day into the past. All five overnight workflows failed on it
              — search index, press sweep, range capture, daily refresh,
              Differentiator — and two finished commits sat unpushed behind it.
              Nothing was wrong with the gate. The data had gone stale under it.

The calendar is built by calendar_build.py, which lives in the cloud-pipeline
repo and already omits past rows. Nothing ran it. It was built once and left to
go stale on a timer, so the outage was scheduled from the day it landed.

This script is the standing answer: it applies the SAME rules the builder
applies, using only the file itself, so it can run here on a schedule with no
cross-repo dependency. It does not invent, re-date or add rows — it only removes
what the gate would reject and flags the recent-past framework ends.

It deliberately does NOT touch `_meta.dataAsOf`. That field is a claim about when
the sources were last read, and pruning reads no sources. Bumping it would be a
false freshness claim. `_meta.lastPruned` records this pass instead.

Rules mirrored from calendar_build.py (framework_rows, RECENT_PAST_DAYS = 90):
  * date today or later                      -> keep, untouched
  * framework-end, within 90 days past       -> keep, force `past: true`
  * framework-end, more than 90 days past    -> drop (the builder's "too_old")
  * anything else with a past date           -> drop

Idempotent: running it twice changes nothing the second time.

  python3 scripts/prune_calendar.py            prune in place
  python3 scripts/prune_calendar.py --check    report only, exit 1 if stale
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALENDAR = os.path.join(HERE, "data", "hub-calendar.json")

RECENT_PAST_DAYS = 90

# A prune that empties the calendar is a bug — a wrong clock, a truncated file, a
# source that stopped parsing — not a day's housekeeping. Refuse rather than
# quietly publish a gutted diary to members.
MIN_ENTRIES_AFTER = 50
MAX_DROP_FRACTION = 0.25


def decide(entry, today, horizon):
    """(keep?, mutated_entry, reason). Mirrors calendar_build.framework_rows."""
    date = entry.get("date") or ""
    try:
        d = datetime.date.fromisoformat(date)
    except ValueError:
        # Not this script's job to judge — verify.py has a specific, better
        # message for a malformed date. Leave it exactly as found.
        return True, entry, None

    if d >= today:
        return True, entry, None

    if entry.get("type") == "framework-end" and d >= horizon:
        if not entry.get("past"):
            entry = dict(entry, past=True)
            return True, entry, "flagged past"
        return True, entry, None

    if entry.get("type") == "framework-end":
        return False, entry, "framework end more than %d days past" % RECENT_PAST_DAYS
    return False, entry, "%s date is past" % (entry.get("type") or "row")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Report what would change and exit 1 if anything would. "
                         "Changes nothing.")
    ap.add_argument("--file", default=CALENDAR)
    args = ap.parse_args()

    with open(args.file) as fh:
        doc = json.load(fh)

    today = datetime.date.today()
    horizon = today - datetime.timedelta(days=RECENT_PAST_DAYS)
    entries = doc.get("entries") or []

    kept, dropped, flagged = [], [], []
    for e in entries:
        keep, e2, reason = decide(e, today, horizon)
        if keep:
            kept.append(e2)
            if reason:
                flagged.append((e2.get("id"), reason))
        else:
            dropped.append((e.get("id"), e.get("date"), reason))

    if not dropped and not flagged:
        print("hub-calendar.json: nothing to prune, %d entries, all current." % len(kept))
        return 0

    for eid, date, reason in dropped:
        print("  drop   %s  %s  (%s)" % (date, eid, reason))
    for eid, reason in flagged:
        print("  flag   %s  (%s)" % (eid, reason))

    if args.check:
        print("hub-calendar.json IS STALE: %d row(s) the publish gate would reject."
              % (len(dropped) + len(flagged)))
        return 1

    # Guards. A prune this large is a fault, not housekeeping.
    if len(kept) < MIN_ENTRIES_AFTER:
        print("REFUSING: pruning would leave %d entries, below the floor of %d. "
              "Check the clock and the file before re-running."
              % (len(kept), MIN_ENTRIES_AFTER), file=sys.stderr)
        return 1
    if entries and len(dropped) / len(entries) > MAX_DROP_FRACTION:
        print("REFUSING: pruning would drop %d of %d entries (>%d%%). That is a fault, "
              "not a day's ageing. Rebuild with calendar_build.py instead."
              % (len(dropped), len(entries), int(MAX_DROP_FRACTION * 100)), file=sys.stderr)
        return 1

    doc["entries"] = kept
    meta = doc.setdefault("_meta", {})
    # NOT dataAsOf — see the module docstring.
    meta["lastPruned"] = today.isoformat()
    meta["lastPrunedCounts"] = {"dropped": len(dropped), "flaggedPast": len(flagged),
                                "remaining": len(kept)}

    with open(args.file, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)

    print("hub-calendar.json: dropped %d, flagged %d, %d entries remain."
          % (len(dropped), len(flagged), len(kept)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
