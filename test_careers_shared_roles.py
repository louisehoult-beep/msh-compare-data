#!/usr/bin/env python3
"""One role, one supplier — the careers collector and its gate.

Lou, 28/09/2026 (OUTSTANDING ^o190): "make rule so not shown 4 times, only once".
Identity policy `shared-careers-site-role-attribution`.

Four Abbott seed records resolve to one Abbott Workday board, so every one of its
UK roles was collected under all four and data/supplier-careers.json read 279 UK
roles where there were 78. This proves:

  1. the collector attributes each shared role URL to exactly one record, chosen
     deterministically (own domain = careers domain; else parent record; else
     lowest name), and the others hold none of it and state no count;
  2. verify.py's careers gate REFUSES a file that holds one role URL under more
     than one supplier — the old 4x file — and passes the attributed one.

Offline. python3 test_careers_shared_roles.py
"""
import copy
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("rc", "scripts/refresh_supplier_careers.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

vspec = importlib.util.spec_from_file_location("v", "verify.py")
V = importlib.util.module_from_spec(vspec)
vspec.loader.exec_module(V)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(label)
        print("FAIL  %s — got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


BOARD = "https://abbott.wd5.myworkdayjobs.com/abbottcareers/job/"


def roles(n, start=0):
    return [{"title": "Territory Manager %d" % i, "location": "Solihull, United Kingdom",
             "url": BOARD + "r%d" % i, "uk": True, "commercial": True, "clinical": False}
            for i in range(start, start + n)]


def row(name, domain, careers, n=3, **over):
    r = {"name": name, "domain": domain, "checkedOn": "2026-09-22",
         "careersUrl": careers, "careersUrlFoundBy": "nav", "ats": "workday",
         "atsAccount": "abbott", "countMethod": "ats", "ukCountFrom": "source",
         "rolesUnplaceable": 0, "ukRoleCount": n, "rolesRetrieved": n,
         "complete": True, "commercialRoles": n, "clinicalRoles": 0,
         "roles": roles(n)}
    r.update(over)
    return r


def abbott_four():
    """The live shape: four records, one board, the same roles under each."""
    return [row("Abbott Diabetes Care", "www.abbott.co.uk", "https://www.abbott.com/en-us/careers"),
            row("Abbott Diagnostics", "www.diagnostics.abbott", "https://www.abbott.com/careers.html",
                rolesUrl="https://www.abbott.com/en-us/careers"),
            row("Abbott Laboratories Limited", "www.abbott.co.uk", "https://www.abbott.com/en-us/careers"),
            row("Abbott Medical U.K. Ltd", "www.abbott.co.uk", "https://www.abbott.com/en-us/careers")]


def times_shown(rows):
    seen = {}
    for r in rows:
        for x in r.get("roles") or []:
            seen[x["url"]] = seen.get(x["url"], 0) + 1
    return seen


# 1. THE ABBOTT CASE: 4x before, 1x after.
before = abbott_four()
check("before: each role is shown four times",
      set(times_shown(before).values()), {4})
after = rc.attribute_shared_roles(abbott_four(), {})
check("after: each role is shown once", set(times_shown(after).values()), {1})
check("after: the UK total is the distinct role count, not four times it",
      rc.summary_counts(after)["ukRoles"], 3)
owners = [r["name"] for r in after if r.get("ukRoleCount") is not None]
check("no domain match, no parent record: the lowest name holds the roles",
      owners, ["Abbott Diabetes Care"])
for r in after[1:]:
    check("%s states no count" % r["name"], "ukRoleCount" in r, False)
    check("%s says where its roles are held" % r["name"],
          r.get("rolesAttributedTo"), "Abbott Diabetes Care")
check("a record that gave its roles away does not read as zero",
      any(r.get("ukRoleCount") == 0 for r in after), False)

# 2. DETERMINISTIC: input order does not change the owner.
rev = rc.attribute_shared_roles(list(reversed(abbott_four())), {})
check("input order does not move the roles",
      [r["name"] for r in rev if r.get("ukRoleCount") is not None], ["Abbott Diabetes Care"])

# 3. IDEMPOTENT: a second pass changes nothing.
again = rc.attribute_shared_roles(copy.deepcopy(after), {})
check("running it twice changes nothing", again, after)

# 4. TIER 1: a record whose own domain IS the careers site wins over a lower name.
t1 = abbott_four()
t1[3]["domain"] = "www.abbott.com"
t1 = rc.attribute_shared_roles(t1, {})
check("own domain matching the careers site wins",
      [r["name"] for r in t1 if r.get("ukRoleCount") is not None], ["Abbott Medical U.K. Ltd"])

# 5. TIER 2: the group's parent record — named in every other member's ownership.
seed = {n: {"name": n, "ownership": "Part of Abbott Laboratories Limited, source ..."}
        for n in ("Abbott Diabetes Care", "Abbott Diagnostics", "Abbott Medical U.K. Ltd")}
seed["Abbott Laboratories Limited"] = {"name": "Abbott Laboratories Limited"}
t2 = rc.attribute_shared_roles(abbott_four(), seed)
check("the parent record wins where no domain matches",
      [r["name"] for r in t2 if r.get("ukRoleCount") is not None], ["Abbott Laboratories Limited"])

# 6. PARTIAL OVERLAP: a record keeps its own roles and loses only the shared ones.
a = row("Alpha Group", "alpha.com", "https://alpha.com/careers", n=4)
b = row("Beta Ltd", "beta.co.uk", "https://alpha.com/careers", n=2)
b["roles"] = roles(1, start=0) + roles(1, start=90)   # one shared, one its own
b["commercialRoles"] = 2
p = rc.attribute_shared_roles([a, b], {})
check("partial overlap: the other record keeps its own role", p[1]["ukRoleCount"], 1)
check("partial overlap: and only its own role",
      [x["url"] for x in p[1]["roles"]], [BOARD + "r90"])
check("partial overlap: shown once each", set(times_shown(p).values()), {1})

# 7. THE GATE refuses the old 4x file and passes the attributed one.
def gate(rows):
    V.fails.clear()
    V.warns.clear()
    V.check_supplier_careers({"generatedOn": "2026-09-28", "rule": "r", "scope": "uk",
                              "ukRule": "u", "roleFlagRule": "f", "counts": {},
                              "suppliers": rows})
    return [m for _, m in V.fails]

old = gate(abbott_four())
check("gate: a role URL under four suppliers is refused",
      any("more than one supplier" in m for m in old), True)
check("gate: the attributed file passes", gate(rc.attribute_shared_roles(abbott_four(), {})), [])
dangling = rc.attribute_shared_roles(abbott_four(), {})
dangling[1]["rolesAttributedTo"] = "Nobody Ltd"
check("gate: attribution to a record with no count is refused",
      any("Nobody Ltd" in m for m in gate(dangling)), True)

# 8. A FAILED RE-READ OF THE OWNER never leaves the others pointing at nothing.
orph = rc.attribute_shared_roles(abbott_four(), {})
for f in rc.COUNT_FIELDS:
    orph[0].pop(f, None)
orph[0]["refused"] = "run failed (timeout)"
rc.settle_orphaned_attributions(orph)
check("orphaned attributions become stated refusals", gate(orph), [])

print()
if FAILURES:
    print("%d FAILURE(S)" % len(FAILURES))
    sys.exit(1)
print("One role, one supplier: all checks pass.")
