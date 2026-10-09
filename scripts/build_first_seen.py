#!/usr/bin/env python3
"""
build_first_seen.py — give every Hub record the one date it never carried: when it arrived.

The seed records what is true now. Nothing in it says when a supplier first appeared,
when a framework place was first captured, or how long a company has been on the Hub —
so "who is new this month" could only ever be answered by reading a JSON diff by hand.

The history is already there: every nightly run commits, back to the repo's first commit.
This walks those commits once and writes down, for each supplier and each of its framework
places, the earliest commit date it can be seen in. After that the walk is incremental —
it starts from the commit it finished on last time.

  python3 scripts/build_first_seen.py            # update state/first-seen.json
  python3 scripts/build_first_seen.py --rebuild  # throw it away and walk the whole history
  python3 scripts/build_first_seen.py --report   # what arrived, newest first
  python3 scripts/build_first_seen.py --report --days 30

HONESTY ABOUT THE FLOOR. A record present in the first commit was not necessarily new
then — it is simply as far back as this repo goes. Those carry "atHistoryStart": true
and must never be described as having arrived on that date.

Exit 0 = written. Exit 2 = the history could not be read.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = "data/supplier-seed.json"
OUT = os.path.join(ROOT, "state", "first-seen.json")


def git(*args):
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"build_first_seen: git {' '.join(args)} failed: {r.stderr.strip()}",
              file=sys.stderr)
        sys.exit(2)
    return r.stdout


def uk(d):
    try:
        return datetime.date.fromisoformat(d).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return d or "unknown"


def commits(after=None):
    """Every commit that touched the seed, oldest first, as (sha, YYYY-MM-DD)."""
    rng = [f"{after}..HEAD"] if after else []
    out = git("log", "--reverse", "--format=%H %ad", "--date=short", *rng, "--", SEED)
    rows = []
    for line in out.splitlines():
        sha, _, when = line.partition(" ")
        if sha:
            rows.append((sha, when.strip()))
    return rows


def seed_at(sha):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{sha}:{SEED}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None       # a commit mid-rebuild; the next one covers it


def fw_name(item):
    if isinstance(item, dict):
        return item.get("name")
    return item if isinstance(item, str) else None


def load_existing():
    if not os.path.exists(OUT):
        return None
    with open(OUT, encoding="utf-8") as f:
        return json.load(f)


def walk(state, rows, history_start):
    seen = state["suppliers"]
    for sha, when in rows:
        doc = seed_at(sha)
        if not isinstance(doc, dict):
            continue
        for s in doc.get("suppliers") or []:
            name = s.get("name")
            if not name:
                continue
            rec = seen.setdefault(name, {"firstSeen": when,
                                         "atHistoryStart": when == history_start,
                                         "frameworks": {}})
            for f in s.get("frameworks") or []:
                fn = fw_name(f)
                if fn and fn not in rec["frameworks"]:
                    rec["frameworks"][fn] = when
        state["throughCommit"] = sha
        state["throughDate"] = when
    return state


def report(state, days):
    cutoff = None
    if days:
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    rows = [(v["firstSeen"], k, v) for k, v in state["suppliers"].items()
            if not v.get("atHistoryStart") and (not cutoff or v["firstSeen"] >= cutoff)]
    rows.sort(reverse=True)
    floor = state.get("historyStart")
    print(f"Suppliers by arrival date (history starts {uk(floor)}; "
          f"{sum(1 for v in state['suppliers'].values() if v.get('atHistoryStart'))} "
          f"were already present then and are not datable)")
    print()
    day = None
    for when, name, v in rows:
        if when != day:
            day, = (when,)
            print(f"{uk(when)}")
        print(f"    {name}  ({len(v['frameworks'])} framework place(s))")
    if not rows:
        print("    nothing arrived in this window.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rebuild", action="store_true", help="walk the whole history again")
    ap.add_argument("--report", action="store_true", help="print arrivals, newest first")
    ap.add_argument("--days", type=int, help="with --report, only this many days back")
    a = ap.parse_args()

    state = None if a.rebuild else load_existing()
    all_rows = commits()
    if not all_rows:
        print("build_first_seen: no history for the seed", file=sys.stderr)
        return 2
    history_start = all_rows[0][1]

    if state is None:
        state = {"_notice": "GENERATED by scripts/build_first_seen.py from this repo's "
                            "commit history — do not edit. Rebuild with --rebuild.",
                 "historyStart": history_start,
                 "historyStartNote": "A record marked atHistoryStart was present in the "
                                     "first commit and may be far older. It did NOT arrive "
                                     "on this date and must never be published as new.",
                 "suppliers": {}}
        rows = all_rows
    else:
        rows = commits(after=state.get("throughCommit"))

    if not rows and a.report:
        report(state, a.days)
        return 0

    before = len(state["suppliers"])
    state = walk(state, rows, history_start)
    state["generated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"{len(rows)} commit(s) walked, {len(state['suppliers'])} supplier(s) known "
          f"({len(state['suppliers']) - before} newly dated), through "
          f"{uk(state['throughDate'])} ({state['throughCommit'][:8]})")
    print(f"written to state/first-seen.json")
    if a.report:
        print()
        report(state, a.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
