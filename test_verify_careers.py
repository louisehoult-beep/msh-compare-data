#!/usr/bin/env python3
"""Prove verify.py's careers gate catches the failures it was built for.

A gate nobody has tried to get past is a gate you are trusting on faith. Each
case below is a real failure from the build on 28/08/2026, replayed as data. If
any of them passes, the gate has stopped doing its job.

  python3 test_verify_careers.py
"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("v", "verify.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

RESULTS = []


def run(doc):
    """Run the check over one document and return the failure messages."""
    V.fails.clear()
    V.warns.clear()
    V.check_supplier_careers(doc)
    return [m for c, m in V.fails]


def wrap(rows, **over):
    doc = {"generatedOn": "2026-08-28", "rule": "r", "ukRule": "u", "roleFlagRule": "f",
           "counts": {}, "suppliers": rows}
    doc.update(over)
    return doc


def must_fail(label, doc, needle):
    got = run(doc)
    hit = any(needle.lower() in m.lower() for m in got)
    RESULTS.append((label, hit))
    print(("ok    " if hit else "FAIL  ") + label)
    if not hit:
        print("        gate said: %s" % (got or "nothing at all"))


def must_pass(label, doc):
    got = run(doc)
    RESULTS.append((label, not got))
    print(("ok    " if not got else "FAIL  ") + label)
    for m in got:
        print("        unexpected: %s" % m)


GOOD = {
    "name": "Accora", "domain": "accora.care",
    "careersUrl": "https://accora.care/careers", "countMethod": "ats",
    "atsAccount": "accora", "roleCount": 3, "rolesRetrieved": 3, "complete": True,
    "ukRoles": 2, "rolesWithoutLocation": 1, "commercialRoles": 1, "clinicalRoles": 0,
    "roles": [{"title": "Territory Manager", "location": "Leeds", "uk": True},
              {"title": "Design Engineer", "location": "Cambridge", "uk": True},
              {"title": "Buyer", "location": "", "uk": None}],
}


def variant(**over):
    r = dict(GOOD)
    r.update(over)
    return r


must_pass("a complete, well-evidenced row passes", wrap([variant()]))

# 1. THE ACUMED / MARMON FAILURE. Acumed's own careers page hands off to Workday
#    tenant `marmon` — its parent conglomerate — returning 40 US roles. Published
#    unguarded, the Hub states "Acumed: 40 open roles" and none of them are.
must_fail("a parent group's ATS account is rejected",
          wrap([variant(name="Acumed Ltd", domain="www.acumed.net",
                        careersUrl="https://www.acumed.net/careers/",
                        atsAccount="marmon", roleCount=40, rolesRetrieved=40,
                        roles=[{"title": "Machine Operator", "location": "Boyne City, MI",
                                "uk": False}] * 40,
                        ukRoles=0, rolesWithoutLocation=0,
                        commercialRoles=0, clinicalRoles=0)]),
          "does not carry this company's own identity")

must_fail("an ATS count with no account recorded is rejected",
          wrap([variant(atsAccount=None)]), "no atsAccount recorded")

# 2. THE STRYKER FAILURE. Workday states its real total on page 1 and 0 after it,
#    so the loop halted at 40 and 1,184 roles were counted as 40.
must_fail("retrieving more than the stated total is rejected",
          wrap([variant(roleCount=40, rolesRetrieved=300)]),
          "retrieved 300 roles but states a total of 40")

must_fail("claiming completeness on a truncated fetch is rejected",
          wrap([variant(roleCount=1184, rolesRetrieved=500, complete=True)]),
          "marked complete but retrieved 500 of 1184")

must_fail("not saying how many were retrieved is rejected",
          wrap([variant(rolesRetrieved=None)]), "does not state how many roles were retrieved")

# 3. NO PARTIAL BREAKDOWN. A breakdown over the first 500 of 1,184 sits beside a
#    full total and reads as the whole list.
must_fail("a breakdown on an incomplete fetch is rejected",
          wrap([variant(roleCount=1184, rolesRetrieved=500, complete=False,
                        breakdownWithheld="withheld", roles=[])]),
          "partial breakdown beside a full total")

must_pass("an incomplete fetch that withholds its breakdown passes",
          wrap([{"name": "Stryker", "domain": "www.stryker.com",
                 "careersUrl": "https://careers.stryker.com/", "countMethod": "ats",
                 "atsAccount": "stryker", "roleCount": 1184, "rolesRetrieved": 500,
                 "complete": False, "breakdownWithheld": "cap reached",
                 "roles": [{"title": "Assembler", "location": "Irvine, CA", "uk": False}]}]))

# 4. A COUNT WITHOUT A RECORD SOURCE IS AN ESTIMATE.
must_fail("a pattern-counted layout is rejected",
          wrap([variant(countMethod="html")]), "pattern-counted")

# 5. AN EMPTY STATE MUST SAY WHY. Silence reads as broken, not as empty.
must_fail("no count and no reason is rejected",
          wrap([{"name": "Alpha Laboratories", "domain": "www.alphalabs.co.uk",
                 "careersUrl": "https://www.alphalabs.co.uk/company/jobs"}]),
          "no role count and no reason")

must_pass("a refusal with a reason passes",
          wrap([{"name": "Alpha Laboratories", "domain": "www.alphalabs.co.uk",
                 "careersUrl": "https://www.alphalabs.co.uk/company/jobs",
                 "refused": "the page publishes no role records"}]))

# 6. THE HEADER MUST AGREE WITH THE ROWS — the company-awards defect, replayed.
must_fail("a header count that disagrees with the rows is rejected",
          wrap([variant()], counts={"roles": 99}), "counts.roles states 99")

# 7. THE FILE MUST CARRY THE RULE IT WAS DERIVED UNDER (root rule 14).
must_fail("a file with no stated rule is rejected",
          {"generatedOn": "2026-08-28", "ukRule": "u", "roleFlagRule": "f",
           "suppliers": [variant()]},
          "states no rule")

# 8. UK IS TRUE, FALSE OR UNKNOWN — never inferred from the company's country.
must_fail("an invented UK flag is rejected",
          wrap([variant(roles=[{"title": "Buyer", "location": "", "uk": "probably"}],
                        roleCount=1, rolesRetrieved=1, ukRoles=0,
                        rolesWithoutLocation=1, commercialRoles=0, clinicalRoles=0)]),
          "must stay unknown")

# 9. A NO-OP UNTIL THE FILE EXISTS.
must_pass("an absent file is a no-op, not a failure", None)

print()
bad = [n for n, ok in RESULTS if not ok]
if bad:
    print("%d of %d cases FAILED: %s" % (len(bad), len(RESULTS), ", ".join(bad)))
    sys.exit(1)
print("All %d gate cases behave correctly." % len(RESULTS))
