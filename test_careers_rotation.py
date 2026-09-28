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
# Supplier 13 shares Supplier 12's careers site (one role URL, two records),
# so one-role-one-supplier attribution holds the role under 12 and leaves 13
# pointing at it — the Abbott shape: a record that holds roles only by
# attribution.
COUNTED = {"Supplier 01", "Supplier 12", "Supplier 13"}
ROLES = {"Supplier 01": ["https://x.example/job/1"],
         "Supplier 12": ["https://y.example/job/1"],
         "Supplier 13": ["https://y.example/job/1"]}


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


def sweep(work, day, argv=("--rotate", "5", "--write")):
    """One Tuesday on a fresh runner: only what git holds survives."""
    report = os.path.join(work, rc.REPORT)
    if os.path.exists(report):
        os.remove(report)                     # never committed, so never there
    rc.TODAY = day
    old_argv, old_cwd = sys.argv, os.getcwd()
    sys.argv = ["refresh_supplier_careers.py"] + list(argv)
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
    per_sweep = []

    def recording(name, domain, prev):
        visited.append(name)
        per_sweep[-1].append(name)
        return fake_run_one(name, domain, prev)
    rc.run_one = recording

    days = ["2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22"]
    docs = []
    for d in days:
        per_sweep.append([])
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
    # The ROTATION slice never repeats a supplier before the whole list has been
    # checked once. The only re-checks are of suppliers holding roles, which are
    # re-read every sweep ON TOP of the slice (below).
    holders_seen = COUNTED
    rotation_visits = [n for s in per_sweep for n in s
                       if n not in holders_seen or s is per_sweep[0]]
    check("the rotation slice re-checks no supplier before every one was checked once",
          len(rotation_visits) - len(set(rotation_visits)), 0)

    # 1b. EVERY SUPPLIER HOLDING ROLES IS RE-CHECKED EVERY SWEEP, IN ADDITION TO
    #     THE SLICE (28/09/2026). Abbott held 19 roles on the Hub's careers page
    #     and was last read 01/09: never-checked suppliers kept taking the slice,
    #     so 7 of its roles had closed at source and were still listed. A record
    #     holding a count (01 from sweep 2, 12 from sweep 4) or holding roles by
    #     attribution (13, pointed at 12) must be re-read on every later sweep.
    check("sweep 2 re-reads Supplier 01 (held a count after sweep 1)",
          "Supplier 01" in per_sweep[1], True)
    check("sweep 4 re-reads the count holder and the attributed record",
          {"Supplier 01", "Supplier 12", "Supplier 13"} <= set(per_sweep[3]), True)
    check("sweep 4 still checks a full slice of 5 besides the holders",
          len([n for n in per_sweep[3] if n not in COUNTED]), 5)
    check("Supplier 13 holds its roles by attribution to Supplier 12",
          {r["name"]: r for r in docs[2]["suppliers"]}["Supplier 13"]
          .get("rolesAttributedTo"), "Supplier 12")

    # 2. A supplier re-checked after the whole list cycled has the previous run's
    #    role keys to diff against: firstRun is false from the second sweep on.
    check("the first sweep says firstRun", docs[0].get("firstRun"), True)
    check("a later sweep does not say firstRun", docs[-1].get("firstRun"), False)

    # 3. A role appearing between two checks of the same supplier is `new`.
    #    Sweep 5 re-reaches Supplier 01 (oldest checkedOn), which now has a
    #    second role alongside the one it had on 01/09.
    ROLES["Supplier 01"] = ["https://x.example/job/1", "https://x.example/job/2"]
    # ...and the role Supplier 12 held (and 13 shared) CLOSES at source.
    ROLES["Supplier 12"] = []
    ROLES["Supplier 13"] = []
    per_sweep.append([])
    doc5 = sweep(work, "2026-09-29")
    row = {r["name"]: r for r in doc5["suppliers"]}.get("Supplier 01") or {}
    flags = {x["url"]: x.get("new") for x in row.get("roles") or []}
    check("Supplier 01 was re-checked on the fifth sweep", row.get("checkedOn"), "2026-09-29")
    check("the role seen last time is not new, the fresh one is",
          flags, {"https://x.example/job/1": False, "https://x.example/job/2": True})
    check("newRoles counts only the fresh one", row.get("newRoles"), 1)
    check("the published row does not leak the private all-keys field",
          any(k.startswith("_") for k in row), False)

    # 4. A CLOSED ROLE DROPS OFF AT THE NEXT SWEEP. Supplier 12 was last in the
    #    slice on 15/09; it is re-read on 29/09 only because it held a role.
    by5 = {r["name"]: r for r in doc5["suppliers"]}
    check("the supplier whose role closed was re-read on the next sweep",
          by5["Supplier 12"].get("checkedOn"), "2026-09-29")
    check("the closed role is gone from the published file",
          any(x.get("url") == "https://y.example/job/1"
              for r in doc5["suppliers"] for x in (r.get("roles") or [])), False)
    check("the attributed record was re-read too and no longer points at it",
          (by5["Supplier 13"].get("checkedOn"), by5["Supplier 13"].get("rolesAttributedTo")),
          ("2026-09-29", None))

    # 5. `--supplier NAME --write` MERGES the named rows into the published file.
    #    Before 28/09/2026 it replaced the whole file with just those rows, so a
    #    targeted refresh of one supplier would have unpublished every other.
    before = {r["name"] for r in doc5["suppliers"]}
    per_sweep.append([])
    doc6 = sweep(work, "2026-09-30", ("--supplier", "Supplier 05", "--write"))
    by6 = {r["name"]: r for r in doc6["suppliers"]}
    check("--supplier --write keeps every other published row",
          set(by6), before)
    check("--supplier --write re-read only the named supplier", per_sweep[-1],
          ["Supplier 05"])
    check("--supplier --write updated the named supplier's row",
          by6["Supplier 05"].get("checkedOn"), "2026-09-30")
    check("--supplier --write left another supplier's row as it was",
          by6["Supplier 01"], by5["Supplier 01"])
    check("the header counts cover the merged rows, not just the one re-read",
          doc6["counts"]["withCareersPage"], len(doc6["suppliers"]))
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if FAILURES:
    print("%d FAILURE(S)" % len(FAILURES))
    sys.exit(1)
print("Rotation cycles and 'new' fires.")
