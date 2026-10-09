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
print("PRUNER HOLDS — %d case(s) run." % 14)
