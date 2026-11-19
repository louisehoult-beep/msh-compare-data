#!/usr/bin/env python3
"""
test_prune_calendar.py — prove the calendar pruner still does what it was built for.

Every case below is either the incident of 25/08/2026 or a way this script could
quietly make things worse. A pruner that deletes member-facing rows has to be
held to the same standard as the gate it protects.

  python3 test_prune_calendar.py     exit 0 = the pruner holds
"""

import datetime
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scripts", "prune_calendar.py")

TODAY = datetime.date.today()
FAILURES = []


def d(offset):
    return (TODAY + datetime.timedelta(days=offset)).isoformat()


def row(eid, date, kind="event", **kw):
    r = {"id": eid, "type": kind, "title": eid, "date": date,
         "rule": "test", "links": [{"label": "x", "url": "https://example.org", "kind": "source"}]}
    r.update(kw)
    return r


def run(entries, args=(), meta=None):
    doc = {"_notice": "test", "_meta": meta or {"dataAsOf": "2026-08-21"},
           "specialities": [], "awarenessGaps": [], "entries": entries}
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(doc, fh)
    fh.close()
    p = subprocess.run([sys.executable, SCRIPT, "--file", fh.name, *args],
                       capture_output=True, text=True)
    with open(fh.name) as g:
        after = json.load(g)
    os.unlink(fh.name)
    return p.returncode, p.stdout + p.stderr, after


def case(label, ok):
    print("%-6s %s" % ("ok" if ok else "FAIL", label))
    if not ok:
        FAILURES.append(label)


# Enough future rows that the guards (floor 50, max 25% dropped) are not the
# thing under test except where they are.
BULK = [row("ev-future-%03d" % i, d(30 + i)) for i in range(80)]


def ids(doc):
    return {e["id"] for e in doc["entries"]}


# --- the incident ----------------------------------------------------------
rc, out, after = run(BULK + [row("fw-start-x", d(-1), "framework-start")])
case("the 25/08 incident: a framework-start one day past is dropped",
     rc == 0 and "fw-start-x" not in ids(after))

rc, out, after = run(BULK + [row("ev-bapen", d(-1))])
case("the 27/08 recurrence: an event one day past is dropped",
     rc == 0 and "ev-bapen" not in ids(after))

# --- what must survive -----------------------------------------------------
rc, out, after = run(BULK + [row("ev-today", d(0))])
case("a row dated today is not touched — it has not gone past",
     rc == 0 and "ev-today" in ids(after))

rc, out, after = run(BULK + [row("fw-end-recent", d(-10), "framework-end")])
kept = [e for e in after["entries"] if e["id"] == "fw-end-recent"]
case("a framework END inside 90 days is kept AND flagged past (the gate needs the flag)",
     rc == 0 and kept and kept[0].get("past") is True)

rc, out, after = run(BULK + [row("fw-end-old", d(-120), "framework-end")])
case("a framework END past 90 days is dropped, matching the builder's `too_old`",
     rc == 0 and "fw-end-old" not in ids(after))

rc, out, after = run(BULK + [row("ev-bad", "not-a-date")])
case("a malformed date is left alone — verify.py has the better message for it",
     rc == 0 and "ev-bad" in ids(after))

# --- multi-day rows: judged on FINISHING, not on STARTING ------------------
# Added 16/11/2026. The pruner judged on `date` alone, so a conference that had
# started but not finished was deleted while the gate rightly kept it — silent
# data loss on a members' page. Due to fire 17/11/2026 on COMPAMED, MEDICA and
# Hospice UK National, all running 16-19 November. verify.py had the identical
# bug, fixed 12/09/2026 on ev-dukes-club-2026; the fix was never mirrored here.
rc, out, after = run(BULK + [row("ev-in-progress", d(-1), endDate=d(2))])
case("a multi-day row that has STARTED but not FINISHED is kept",
     rc == 0 and "ev-in-progress" in ids(after))

rc, out, after = run(BULK + [row("ev-ends-today", d(-3), endDate=d(0))])
case("a multi-day row ending today is kept — its last day is not past",
     rc == 0 and "ev-ends-today" in ids(after))

rc, out, after = run(BULK + [row("ev-finished", d(-5), endDate=d(-1))])
case("a multi-day row that has FINISHED is dropped",
     rc == 0 and "ev-finished" not in ids(after))

rc, out, after = run(BULK + [row("aw-week", d(-2), kind="awareness", endDate=d(4))])
case("an awareness week part-way through is kept, not deleted mid-week",
     rc == 0 and "aw-week" in ids(after))

rc, out, after = run(BULK + [row("ev-bad-end", d(-1), endDate="not-a-date")])
case("a malformed endDate is left alone — verify.py has the better message",
     rc == 0 and "ev-bad-end" in ids(after))

# The pruner must never disagree with the gate about a row. This checks the two
# rules against each other directly rather than trusting that they were both
# edited: a row the gate would ACCEPT must never be one the pruner DROPS.
sys.path.insert(0, os.path.join(HERE, "scripts"))
import prune_calendar as _pc  # noqa: E402

_HORIZON = TODAY - datetime.timedelta(days=_pc.RECENT_PAST_DAYS)


def gate_accepts(e):
    """verify.py check_calendar's past-date rule, transcribed."""
    end = e.get("endDate")
    effective_end = end or e["date"]
    if effective_end >= TODAY.isoformat():
        return True
    return e.get("type") == "framework-end" and bool(e.get("past"))


disagreements = []
for _kind in ("event", "awareness", "framework-start", "framework-end"):
    for _start in (-200, -95, -89, -5, -1, 0, 1, 30):
        for _span in (None, 0, 1, 3, 7):
            _e = row("probe", d(_start), _kind,
                     **({"endDate": d(_start + _span)} if _span is not None else {}))
            _keep, _mut, _ = _pc.decide(dict(_e), TODAY, _HORIZON)
            if gate_accepts(_e) and not _keep:
                disagreements.append((_kind, _start, _span, "gate keeps, pruner drops"))
            # And the converse: a row the pruner keeps must leave the gate happy.
            if _keep and not gate_accepts(_mut):
                disagreements.append((_kind, _start, _span, "pruner keeps, gate rejects"))

case("pruner and gate agree on every (type, start, span) probe — %d cases"
     % (4 * 8 * 5), not disagreements)
for _d in disagreements[:10]:
    print("        disagreement:", _d)

# --- honesty ---------------------------------------------------------------
rc, out, after = run(BULK + [row("fw-start-y", d(-1), "framework-start")])
case("dataAsOf is NOT bumped — pruning reads no sources, so it may not claim freshness",
     after["_meta"].get("dataAsOf") == "2026-08-21")
case("the pass is recorded as lastPruned instead",
     after["_meta"].get("lastPruned") == TODAY.isoformat())

# --- idempotence -----------------------------------------------------------
rc1, _, after1 = run(BULK + [row("fw-start-z", d(-1), "framework-start")])
rc2, out2, after2 = run(after1["entries"])
case("running twice changes nothing the second time",
     rc1 == 0 and rc2 == 0 and ids(after1) == ids(after2) and "nothing to prune" in out2)

# --- the guards ------------------------------------------------------------
rc, out, after = run([row("ev-p-%03d" % i, d(-5)) for i in range(60)])
case("a file that is ALL past refuses rather than publishing an empty diary",
     rc == 1 and len(after["entries"]) == 60 and "REFUSING" in out)

rc, out, after = run([row("ev-f-%03d" % i, d(30)) for i in range(40)])
case("a calendar already under the floor is untouched when nothing is stale",
     rc == 0 and len(after["entries"]) == 40)

rc, out, after = run(BULK + [row("ev-p-%03d" % i, d(-5)) for i in range(40)])
case("dropping more than a quarter of the file refuses — that is a fault, not ageing",
     rc == 1 and len(after["entries"]) == 120 and "REFUSING" in out)

# --- --check is read-only --------------------------------------------------
rc, out, after = run(BULK + [row("fw-start-c", d(-1), "framework-start")], args=("--check",))
case("--check reports staleness, exits 1, and changes nothing",
     rc == 1 and "fw-start-c" in ids(after))

rc, out, after = run(BULK, args=("--check",))
case("--check on a current calendar exits 0", rc == 0)

print()
if FAILURES:
    print("PRUNER BROKEN — %d case(s) failed:" % len(FAILURES))
    for f in FAILURES:
        print("   ", f)
    sys.exit(1)
print("PRUNER HOLDS — %d case(s) run." % 20)
