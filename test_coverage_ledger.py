#!/usr/bin/env python3
"""
test_coverage_ledger.py — prove the coverage ledger does not call a framework
BLOCKED when it still has reachable work.

WHY THIS EXISTS. BLOCKED is not a soft label. The Differentiator sweep skips a
blocked framework, so a framework marked BLOCKED in error is dropped for good
and its coverage can never rise again. On 09/09/2026 four frameworks carried
the label and three of them were wrong: Digital Diagnostic Solutions (11 of 54
suppliers), Blood Collection Devices (8 of 19) and CT Scanners (4 of 8) all had
awarded suppliers that were crawled and publishing — just under a category
outside that framework's speciality — and the ledger counted a
`publishedElsewhere` supplier towards nothing at all. Worse, the sentence it
wrote said those suppliers "had been read and refused", which was untrue of
every one of them, and on a framework with no refusals at all it would have
claimed "(0 recorded refusal(s))".

Each case below is either that incident or a way the fix could make things
worse — chiefly by turning mapping work into a re-crawl, which is how three
considered refusal records were destroyed on 06/09/2026.

  python3 test_coverage_ledger.py     exit 0 = the ledger holds
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scripts", "build_coverage_ledger.py")
ALIASES = os.path.join(HERE, "company-aliases")

# Real canonical names, so the alias registry resolves them exactly as it does
# in production. Nothing here is fuzzy-matched; an unresolved name would land in
# `unknown` and quietly change what these cases prove.
PUB = "Philips"
ELSE1, ELSE2, ELSE3 = "Siemens Healthineers", "Stryker", "Getinge"
REF1, REF2 = "Roche Diagnostics UK", "Sysmex UK"

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def build(frameworks, refused=(), published=(), held=None):
    """Run the real script over a throwaway repo and return its ledger rows."""
    repo = tempfile.mkdtemp(prefix="ledger-test-")
    os.makedirs(os.path.join(repo, "scripts"))
    os.makedirs(os.path.join(repo, "data"))
    os.makedirs(os.path.join(repo, "docs"))
    shutil.copy(SCRIPT, os.path.join(repo, "scripts"))
    os.symlink(ALIASES, os.path.join(repo, "company-aliases"))

    def w(name, doc):
        with open(os.path.join(repo, "data", name), "w") as f:
            json.dump(doc, f)

    w("frameworks.json", {"frameworks": frameworks})
    w("compare-suppliers.json", {"specialities": {
        "digital": {"types": {"sw": {}},
                    "route": [{"url": "https://example.org/fw/one"}]},
        "wound": {"types": {"dressings": {}},
                  "route": [{"url": "https://example.org/fw/two"}]}}})
    w("differentiator.json", {
        "counts": {"published": len(published), "held": 0},
        "products": [{"supplier": s, "cat": c} for s, c in published],
        "heldBySupplier": held or {}})
    w("supplier-seed.json", {"suppliers": [
        {"name": n, "links": [{"label": "Website",
                               "url": "https://%s.example.org" % i}]}
        for i, n in enumerate([PUB, ELSE1, ELSE2, ELSE3, REF1, REF2])]})
    w("supplier-products.json", {"refusals": {
        n: {"domain": "x.example.org", "reason": "robots.txt forbids it",
            "checked": "2026-09-01"} for n in refused}})

    p = subprocess.run([sys.executable, os.path.join(repo, "scripts",
                                                     "build_coverage_ledger.py")],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("build_coverage_ledger.py failed:\n%s" % p.stderr)
    with open(os.path.join(repo, "data", "coverage-ledger.json")) as f:
        rows = {r["framework"]: r for r in json.load(f)["frameworks"]}
    shutil.rmtree(repo, ignore_errors=True)
    return rows


FW = {"name": "One", "url": "https://example.org/fw/one",
      "category": "Medical Technology"}


def fw(suppliers):
    return [dict(FW, suppliers=list(suppliers))]


print(__doc__.strip().splitlines()[0])

# 1. THE INCIDENT. Suppliers that publish outside this speciality are reachable
#    work — a category mapping — so the framework is not blocked.
r = build(fw([PUB, ELSE1, ELSE2, REF1]), refused=[REF1],
          published=[(PUB, "digital:sw"), (ELSE1, "wound:dressings"),
                     (ELSE2, "wound:dressings")])["One"]
check("publishedElsewhere is counted as work",
      r["actionable"].get("publishedElsewhereNeedingCategory") == 2, r["actionable"])
check("a framework with suppliers publishing elsewhere is NOT blocked",
      r["blockedReason"] is None, r["blockedReason"])
check("actionableTotal includes the mapping work", r["actionableTotal"] == 2,
      r["actionableTotal"])

# 2. IT MUST NOT BECOME A RE-CRAWL. A publishedElsewhere supplier has already
#    been read; queueing it is how recorded refusals got overwritten on 06/09.
check("publishedElsewhere never enters crawlWorklist",
      [w["supplier"] for w in r["crawlWorklist"]] == [], r["crawlWorklist"])
check("publishedElsewhere never enters domainsMissing",
      r["domainsMissing"] == [], r["domainsMissing"])

# 3. THE LABEL STILL WORKS. A framework whose whole remainder really was read
#    and refused is still BLOCKED, with the refusals counted honestly.
r = build(fw([PUB, REF1, REF2]), refused=[REF1, REF2],
          published=[(PUB, "digital:sw")])["One"]
check("a genuinely exhausted framework is still BLOCKED",
      r["blockedReason"] is not None, r["blockedReason"])
check("the reason counts the real refusals",
      r["blockedReason"] and "2 recorded refusal(s)" in r["blockedReason"],
      r["blockedReason"])

# 4. NO PHANTOM REFUSALS. With no refusal on record the ledger must never write
#    a sentence claiming any — the shape that produced "(0 recorded refusal(s))".
r = build(fw([PUB, ELSE1, ELSE2, ELSE3]),
          published=[(PUB, "digital:sw"), (ELSE1, "wound:dressings"),
                     (ELSE2, "wound:dressings"), (ELSE3, "wound:dressings")])["One"]
check("no refusals on record means no BLOCKED sentence",
      r["blockedReason"] is None, r["blockedReason"])

# 5. HELD IS UNCHANGED. The held bucket keeps its own kind of work and still
#    drives the crawl worklist.
r = build(fw([PUB, ELSE1]), published=[(PUB, "digital:sw")],
          held={ELSE1: 12})["One"]
check("held suppliers still count as heldNeedingCategory",
      r["actionable"].get("heldNeedingCategory") == 1, r["actionable"])
check("held suppliers still reach the crawl worklist",
      [w["supplier"] for w in r["crawlWorklist"]] == [ELSE1], r["crawlWorklist"])

print("\n%d case group(s) failed" % len(FAILURES) if FAILURES else "\nall cases hold")
sys.exit(1 if FAILURES else 0)
