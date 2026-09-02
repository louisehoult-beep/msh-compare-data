#!/usr/bin/env python3
"""
test_stale_brief_rows.py — proves a still-warranted framework row is never
classified as one to delete.

THE HOLE THIS CLOSES. backfill_index_frameworks.py skips any supplier the
current briefs match on nothing (`if not hits: continue`), so rows written by an
older capture outlive the brief being revised. The tempting fix is to purge
every sourced row of a supplier with no current hits. On the 01/09/2026 capture
that would have deleted 41 rows the briefs STILL justify, including all eleven
of Unisurge's: the Hub holds the record as "Unisurge", every brief names
"Unisurge International Ltd", and co_key() reduces those to different keys. The
record would have been left showing no frameworks at all, on a paid page.

So the classifier must put a row whose brief still names a lookalike into
ALIAS-GAP (a human identity call — the records carry no company number to
anchor on) and never into UNWARRANTED, which is the only list a purge may read.

    python3 test_stale_brief_rows.py

Exit 0 = the distinction holds. Exit 1 = a correct row could be deleted.
"""
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

spec = importlib.util.spec_from_file_location(
    "rsbr", os.path.join(REPO, "scripts", "report_stale_brief_rows.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

fails = []


def check(desc, got, want):
    if got != want:
        fails.append("%s\n     got %r, want %r" % (desc, got, want))


# --- the shapes that actually occur, each taken from a real 01/09 row --------
# Left: how the brief spells it. Right: the names the Hub record carries.
LOOKALIKE = [
    ("Unisurge International Ltd", ["Unisurge"],
     "brief appends words to a short Hub name"),
    ("Drive DeVilbiss Healthcare Ltd", ["Drive Devilbiss Health Care"],
     "'Healthcare' vs 'Health Care' — spacing only"),
    ("Live By Lulu Limited, trading as Caversham Health, (parent company "
     "Magicdust Holdings)", ["Caversham Health", "Live By Lulu Limited"],
     "brief states the trading name inline"),
    ("Steris IMS Ltd", ["Steris Instrument Management Services"],
     "shared distinguishing word, initialised remainder"),
    ("RB Medical Engineering Ltd", ["R B Medical"],
     "initials spaced in one, joined in the other"),
    ("Baxter Healthcare Limited", ["Baxter Healthcare Corporation"],
     "same group, different legal form"),
]

# Must NOT look alike: these are the rows a purge is actually for. Every one is
# a real supplier on the Surgical Instruments or Finance Solutions brief that
# genuinely no longer names the Hub's supplier.
DIFFERENT = [
    ("B Braun Medical Limited", ["R B Medical"],
     "a single shared letter is not a name"),
    ("Surgical Instrument Group Holdings Ltd", ["Sovereign Surgical LPP"],
     "'surgical'/'instrument' describe the framework, not the supplier"),
    ("Accrington Surgical Instrument", ["Murray Surgical Limited"],
     "category words only"),
    ("GE Capital Equipment Finance Limited",
     ["Societe Generale Equipment Finance Limited"],
     "'equipment finance' is the framework's subject"),
    ("Bolton Surgical Limited", ["Cairn Technology Limited"], "unrelated"),
    ("Timesco Healthcare Ltd", ["Network Medical Products Ltd"], "unrelated"),
]

for brief_name, own, why in LOOKALIKE:
    check("MUST be a lookalike (%s): %r vs %r" % (why, brief_name, own),
          R.looks_like(brief_name, own), True)

for brief_name, own, why in DIFFERENT:
    check("must NOT be a lookalike (%s): %r vs %r" % (why, brief_name, own),
          R.looks_like(brief_name, own), False)

# The report must only report. A purge that ran by accident is the failure mode
# this whole split exists to prevent, so the script may not write data files.
src = open(os.path.join(REPO, "scripts", "report_stale_brief_rows.py")).read()
if 'encoding="utf-8") as f' in src or ', "w"' in src:
    fails.append("report_stale_brief_rows.py opens a file for writing — it must "
                 "only report; deleting rows is a separate, reviewed step")

# Live data: the classifier must agree with itself about every row it emits.
try:
    m = R._load_matcher()
    fw = m.load(R.FW)
    rows = R.classify(R.INDEX, m, fw) + R.classify(R.SEED, m, fw)
except FileNotFoundError as e:
    rows = None
    print("skipping the live-data check (%s)" % e)

if rows is not None:
    for r in rows:
        if r["verdict"] == "UNWARRANTED" and r["candidates"]:
            fails.append("UNWARRANTED row still has a lookalike in its brief — "
                         "it would be deleted wrongly: %s / %s -> %s"
                         % (r["supplier"], r["framework"], r["candidates"]))
        if r["verdict"] == "ALIAS-GAP" and not r["candidates"]:
            fails.append("ALIAS-GAP row names no lookalike: %s / %s"
                         % (r["supplier"], r["framework"]))
    n = {v: sum(1 for r in rows if r["verdict"] == v)
         for v in ("UNWARRANTED", "ALIAS-GAP", "BRIEF-GONE")}
    print("live capture: %d UNWARRANTED, %d ALIAS-GAP, %d BRIEF-GONE"
          % (n["UNWARRANTED"], n["ALIAS-GAP"], n["BRIEF-GONE"]))

if fails:
    print("\nFAILED — a still-warranted row could be deleted:\n")
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)

print("OK — every lookalike shape is held back from the purge list.")
