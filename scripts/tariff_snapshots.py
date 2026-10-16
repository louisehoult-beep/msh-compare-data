#!/usr/bin/env python3
"""tariff_snapshots.py - keep a durable previous-month copy of each speciality's
Drug Tariff Part IX slice, so the panels can show month-on-month price moves.

WHY THIS EXISTS (16/10/2026)
  data/drug-tariff-part-ix.json holds ONE month and the daily refresh overwrites it,
  so last month's prices are gone the day the new month publishes. A price move
  (a competitor's line rising 1%) is only visible by comparing two months. Git
  history happened to hold the prior month, but a workflow must not depend on
  history it can shorten or rewrite. This script stores the slice the panel
  already selects (build_speciality_panels.tariff_rows) for each month, in
  data/tariff-snapshots.json, and keeps the last KEEP months.

  Only specialities whose rule sets "tariffMoves": True are recorded. The slice,
  not the whole part: 66,000 rows a month would triple the file the Hub already
  ships. The slice is the same rows the panel summarises, so a move can never be
  shown for a line the panel does not count.

USAGE
  python3 scripts/tariff_snapshots.py                       # record current month
  python3 scripts/tariff_snapshots.py --seed-git <commit>   # one-off: record the
        Part IX file as it stood at <commit> (how September 2026 was seeded)

  Idempotent. Re-running in a month replaces that month's entry with the latest
  file; earlier months are never touched, so the previous month stays fixed.
  Run in .github/workflows/drug-tariff.yml straight after the Part IX refresh.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
DATA = os.path.join(ROOT, "data")
PATH = os.path.join(DATA, "tariff-snapshots.json")
SRC = os.path.join(DATA, "drug-tariff-part-ix.json")
KEEP = 4
ROW_FIELDS = ["supplier", "vmp", "amp", "size", "qty", "uom", "price", "bnf"]


def load_snapshots():
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def record(snaps, dt_doc, rules):
    """Add dt_doc's slice for each opted-in speciality. Returns the specialities touched."""
    import build_speciality_panels as bsp
    month = dt_doc.get("effectiveMonth")
    if not month:
        raise SystemExit("Part IX file has no effectiveMonth; refusing to record a snapshot")
    ix = {k: i for i, k in enumerate(dt_doc["schema"])}
    slices = snaps.setdefault("slices", {})
    touched = []
    for slug, rule in sorted(rules.items()):
        if not rule.get("tariffMoves"):
            continue
        rows = bsp.tariff_rows(rule, dt_doc)
        if not rows:
            raise SystemExit("%s: slice is empty for %s; refusing to record an empty month" % (slug, month))
        months = slices.setdefault(slug, {}).setdefault("months", {})
        months[month] = {
            "dataAsOf": dt_doc.get("dataAsOf"),
            "parts": list(rule["tariffParts"]),
            "rows": [[r[ix["part"]]] + [r[ix[f]] for f in ROW_FIELDS] for r in rows],
        }
        for old in sorted(months)[:-KEEP]:
            del months[old]
        touched.append(slug)
    snaps["schema"] = ["part"] + ROW_FIELDS
    snaps["note"] = ("Per-speciality slice of NHSBSA Drug Tariff Part IX, one entry per effective "
                     "month, kept so month-on-month price moves can be shown. Prices are pence as "
                     "NHSBSA publishes them. Written by scripts/tariff_snapshots.py from the "
                     "refreshed Part IX file; never hand-edited.")
    return touched


def main(argv):
    import build_speciality_panels as bsp
    if "--seed-git" in argv:
        commit = argv[argv.index("--seed-git") + 1]
        dt_doc = json.loads(subprocess.check_output(
            ["git", "show", "%s:data/drug-tariff-part-ix.json" % commit], cwd=ROOT))
    else:
        with open(SRC, encoding="utf-8") as fh:
            dt_doc = json.load(fh)
    snaps = load_snapshots()
    touched = record(snaps, dt_doc, bsp.SPECIALITY_RULES)
    text = json.dumps(snaps, indent=1, ensure_ascii=False) + "\n"
    old = open(PATH, encoding="utf-8").read() if os.path.exists(PATH) else ""
    if text != old:
        with open(PATH, "w", encoding="utf-8") as fh:
            fh.write(text)
    print("recorded %s for %s" % (dt_doc.get("effectiveMonth"), ", ".join(touched) or "nothing"))


if __name__ == "__main__":
    main(sys.argv[1:])
