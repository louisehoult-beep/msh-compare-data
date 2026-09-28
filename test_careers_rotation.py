#!/usr/bin/env python3
"""The weekly careers rotation must cycle the whole list, and "new" must fire.

Found 28/09/2026 (^o190 follow-on). Four sweeps (01, 08, 15, 22/09) all sat
between "2San Global" and "Cortrium". The runner is a fresh checkout every
Tuesday: data/supplier-careers.json keeps only rows WITH a careers page, and
state/careers-report.json was never committed. So a supplier that was checked
and refused left no trace, sorted as never-checked, and was re-picked ahead of
the rest of the alphabet every week until refusals alone filled the slice. The
same missing report meant previous_keys() found nothing: `firstRun: true` after
four sweeps, and no role ever carried `new`.

This replays that on a runner: each sweep starts from what git holds (the
published file plus whatever the workflow commits), with the uncommitted report
deleted, and the fetch replaced by a stub. Offline.

  python3 test_careers_rotation.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "rc", os.path.join(HERE, "scripts/refresh_supplier_careers.py"))
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(label)
        print("FAIL  %s — got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


# 20 suppliers. Most are refused, as most real careers pages are; a few have
# a readable board. Names sort alphabetically in seed order, as the real seed does.
NAMES = ["Supplier %02d" % i for i in range(20)]
COUNTED = {"Supplier 01", "Supplier 12"}
ROLES = {"Supplier 01": ["https://x.example/job/1"],
         "Supplier 12": ["https://y.example/job/1"]}


def fake_run_one(name, domain, prev):
    row = {"name": name, "domain": domain, "checkedOn": rc.TODAY}
    if name not in COUNTED:
        # Half the refusals still found a page, half did not — the published
        # file keeps only the former, which is what hid the latter.
        if int(name[-2:]) % 2:
            row["careersUrl"] = "https://%s/careers" % domain
        row["refused"] = "stub refusal"
        return row
    roles = [rc.role("Sales Representative", "Leeds, United Kingdom", u)
             for u in ROLES[name]]
    seen = prev.get(name) if prev else None
    for r in roles:
        if seen is not None:
            r["new"] = rc.role_key(r) not in seen
    row.update({"careersUrl": "https://%s/careers" % domain,
                "countMethod": "ats", "atsAccount": name.replace(" ", "").lower(),
                "ukCountFrom": "location strings published by the company",
                "rolesUnplaceable": 0, "ukRoleCount": len(roles),
                "rolesRetrieved": len(roles), "complete": True,
                "commercialRoles": len(roles), "clinicalRoles": 0, "roles": roles})
    if seen is not None:
        row["newRoles"] = sum(1 for r in roles if r.get("new"))
    return row


def sweep(work, day):
    """One Tuesday on a fresh runner: only what git holds survives."""
    report = os.path.join(work, rc.REPORT)
    if os.path.exists(report):
        os.remove(report)                     # never committed, so never there
    rc.TODAY = day
    old_argv, old_cwd = sys.argv, os.getcwd()
    sys.argv = ["refresh_supplier_careers.py", "--rotate", "5", "--write"]
    os.chdir(work)
    try:
        rc.main()
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
    return json.load(open(os.path.join(work, rc.OUT)))


work = tempfile.mkdtemp(prefix="careers-rotation-")
try:
    os.makedirs(os.path.join(work, "data"))
    os.makedirs(os.path.join(work, "state"))
    seed = {"suppliers": [{"name": n, "links": [
        {"label": "Website", "url": "https://%s.example/" % n.replace(" ", "").lower()}]}
        for n in NAMES]}
    json.dump(seed, open(os.path.join(work, rc.SEED), "w"))
    visited = []

    def recording(name, domain, prev):
        visited.append(name)
        return fake_run_one(name, domain, prev)
    rc.run_one = recording

    days = ["2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22"]
    docs = []
    for d in days:
        docs.append(sweep(work, d))
        # What the workflow commits between runs is all a runner ever has. Add
        # it here exactly as the workflow's own `git add` line names it.
        wf = open(os.path.join(HERE, ".github/workflows/supplier-careers.yml")).read()
        add_line = [l for l in wf.splitlines() if l.strip().startswith("git add ")][0]
        committed = add_line.strip().split()[2:]
        for p in list(os.listdir(os.path.join(work, "state"))):
            if os.path.join("state", p) not in committed:
                os.remove(os.path.join(work, "state", p))

    # 1. Four sweeps of 5 over 20 suppliers visit all 20, once each.
    check("four sweeps of 5 cover all 20 suppliers", sorted(set(visited)), NAMES)
    check("no supplier is re-checked before every supplier has been checked once",
          len(visited), len(set(visited)))

    # 2. A supplier re-checked after the whole list cycled has the previous run's
    #    role keys to diff against: firstRun is false from the second sweep on.
    check("the first sweep says firstRun", docs[0].get("firstRun"), True)
    check("a later sweep does not say firstRun", docs[-1].get("firstRun"), False)

    # 3. A role appearing between two checks of the same supplier is `new`.
    #    Sweep 5 re-reaches Supplier 01 (oldest checkedOn), which now has a
    #    second role alongside the one it had on 01/09.
    ROLES["Supplier 01"] = ["https://x.example/job/1", "https://x.example/job/2"]
    doc5 = sweep(work, "2026-09-29")
    row = {r["name"]: r for r in doc5["suppliers"]}.get("Supplier 01") or {}
    flags = {x["url"]: x.get("new") for x in row.get("roles") or []}
    check("Supplier 01 was re-checked on the fifth sweep", row.get("checkedOn"), "2026-09-29")
    check("the role seen last time is not new, the fresh one is",
          flags, {"https://x.example/job/1": False, "https://x.example/job/2": True})
    check("newRoles counts only the fresh one", row.get("newRoles"), 1)
    check("the published row does not leak the private all-keys field",
          any(k.startswith("_") for k in row), False)
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if FAILURES:
    print("%d FAILURE(S)" % len(FAILURES))
    sys.exit(1)
print("Rotation cycles and 'new' fires.")
