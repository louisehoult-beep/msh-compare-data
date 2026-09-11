#!/usr/bin/env python3
"""
test_supplier_index_awards.py — prove a supplier's contract awards survive a
rebuild of data/supplier-index.json.

WHY THIS EXISTS. build_supplier_index.py's rules line has always said awards are
append-only. For the 1,238 CURATED suppliers in the index it was not true. main()
rebuilds `by_name` from data/supplier-seed.json, which carries no awards at all —
they only ever accumulate in the index — and the carry-forward loop underneath it
re-attached AUTO-DETECTED records only. A curated supplier's awards therefore
lasted exactly one run: anything that had scrolled out of Contracts Finder's
MAX_PAGES scan window since the previous build was dropped in silence.

Counted across the index's own git history, that bled it from 121 awards on
23/08/2026 to 54 on 11/09/2026, with nothing ever withdrawn at source, and no
gate anywhere said a word.

Each case below is that incident, or a way the fix for it could make things
worse — chiefly by double-counting an award that is both carried forward and
re-found this run, or by pinning an award to a supplier name that has since been
merged away.

  python3 test_supplier_index_awards.py     exit 0 = awards are safe
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER = os.path.join(HERE, "build_supplier_index.py")
VERIFY = os.path.join(HERE, "verify.py")

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def award(title, date="2026-08-01"):
    return {"_id": title[:50] + "|" + date, "title": title, "value": "£1,000",
            "buyer": "A Trust", "date": date,
            "url": "https://www.contractsfinder.service.gov.uk/", "autoDetected": True}


def rebuild(seed_suppliers, prev_suppliers):
    """Run the REAL builder over a throwaway repo, with the network stubbed out.

    MAX_PAGES=0 and NEWS_MAX=0 stop the two network sections doing anything, so
    the run exercises exactly the seed load and the carry-forward and nothing
    else. `fetch` is replaced as well, belt and braces, so a future change to
    those loops cannot silently start calling Contracts Finder from a test.
    """
    repo = tempfile.mkdtemp(prefix="index-awards-test-")
    os.makedirs(os.path.join(repo, "data"))
    shutil.copy(BUILDER, repo)

    def w(name, doc):
        with open(os.path.join(repo, "data", name), "w") as f:
            json.dump(doc, f)

    # Real seed records always carry these; main() only setdefaults awards/news,
    # so a fixture missing `alerts` fails on a KeyError that no real data hits.
    for rec in seed_suppliers:
        rec.setdefault("alerts", [])
        rec.setdefault("news", [])
    w("supplier-seed.json", {"suppliers": seed_suppliers})
    w("supplier-index.json", {"suppliers": prev_suppliers})
    w("compare-issues.json", {"specialities": {}})

    runner = os.path.join(repo, "run.py")
    with open(runner, "w") as f:
        f.write(
            "import build_supplier_index as b\n"
            "b.MAX_PAGES = 0\n"
            "b.NEWS_MAX = 0\n"
            "def _no_network(*a, **k):\n"
            "    raise AssertionError('the test must not reach the network')\n"
            "b.fetch = _no_network\n"
            "b.main()\n")
    r = subprocess.run([sys.executable, "run.py"], cwd=repo,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("builder failed: %s\n%s" % (r.stdout, r.stderr))
    with open(os.path.join(repo, "data", "supplier-index.json")) as f:
        out = json.load(f)
    with open(os.path.join(repo, "state", "supplier_index_last_run.json")) as f:
        state = json.load(f)
    return {s["name"]: s for s in out["suppliers"]}, state, r.stdout


def titles(rec):
    return sorted(a["title"] for a in (rec.get("awards") or []))


# ---------------------------------------------------------------------------
# 1. THE INCIDENT ITSELF. A curated supplier holds an award in the published
#    index and nothing in the seed. Before the fix, the rebuild dropped it.
# ---------------------------------------------------------------------------
print("curated supplier keeps the awards it was published with")
recs, state, _ = rebuild(
    seed_suppliers=[{"name": "Acme Medical", "aliases": ["Acme Medical"], "curated": True}],
    prev_suppliers=[{"name": "Acme Medical", "aliases": ["Acme Medical"], "curated": True,
                     "awards": [award("Wound care consumables")], "alerts": [], "news": []}])
check("award survives the rebuild",
      titles(recs["Acme Medical"]) == ["Wound care consumables"],
      titles(recs.get("Acme Medical", {})))
check("the run says it carried one forward", state.get("carried_awards") == 1,
      state.get("carried_awards"))
check("awards_total is recorded", state.get("awards_total") == 1, state.get("awards_total"))

# ---------------------------------------------------------------------------
# 2. NO DOUBLE COUNT. The same award already on the record (because the seed or
#    an earlier step put it there) must not be appended a second time. The
#    carry-forward has to dedupe on the same `_id` section 3 dedupes on, or
#    every run doubles the list.
# ---------------------------------------------------------------------------
print("an award already present is not appended twice")
a = award("Theatre packs")
recs, state, _ = rebuild(
    seed_suppliers=[{"name": "Acme Medical", "aliases": ["Acme Medical"], "curated": True,
                     "awards": [a]}],
    prev_suppliers=[{"name": "Acme Medical", "aliases": ["Acme Medical"], "curated": True,
                     "awards": [dict(a)], "alerts": [], "news": []}])
check("one copy, not two", len(recs["Acme Medical"]["awards"]) == 1,
      len(recs["Acme Medical"]["awards"]))
check("nothing reported as carried", state.get("carried_awards") == 0,
      state.get("carried_awards"))

# ---------------------------------------------------------------------------
# 3. AN IDENTITY CORRECTION RE-ROUTES AN AWARD, IT DOES NOT STRAND IT. The
#    published index called the company "Acme Medical Ltd"; the seed has since
#    settled on "Acme Medical" and kept the old spelling as an alias. The award
#    must land on the record that name resolves to TODAY.
# ---------------------------------------------------------------------------
print("an award follows its supplier through a rename")
recs, state, _ = rebuild(
    seed_suppliers=[{"name": "Acme Medical",
                     "aliases": ["Acme Medical", "Acme Medical Ltd"], "curated": True}],
    prev_suppliers=[{"name": "Acme Medical Ltd", "aliases": ["Acme Medical Ltd"],
                     "curated": True, "awards": [award("Infusion sets")],
                     "alerts": [], "news": []}])
check("award lands on the current record",
      titles(recs.get("Acme Medical", {})) == ["Infusion sets"],
      titles(recs.get("Acme Medical", {})))
check("the old spelling did not become a second record",
      "Acme Medical Ltd" not in recs, sorted(recs))

# ---------------------------------------------------------------------------
# 4. A RECORD THAT HAS LEFT THE INDEX IS REPORTED, NOT GUESSED AT. An award on
#    a supplier this build no longer has must not be re-attached to whichever
#    record looks closest — it is counted and named on stdout for a human.
# ---------------------------------------------------------------------------
print("an award on a vanished supplier is named, not reassigned")
recs, state, out = rebuild(
    seed_suppliers=[{"name": "Acme Medical", "aliases": ["Acme Medical"], "curated": True}],
    prev_suppliers=[{"name": "Gone Medical Ltd", "aliases": ["Gone Medical Ltd"],
                     "curated": True, "awards": [award("Endoscopes")],
                     "alerts": [], "news": []}])
check("not reassigned to the surviving supplier",
      titles(recs.get("Acme Medical", {})) == [], titles(recs.get("Acme Medical", {})))
check("counted as unplaced", state.get("unplaced_awards") == 1, state.get("unplaced_awards"))
check("named on stdout", "Gone Medical Ltd" in out, out[-300:])


# ---------------------------------------------------------------------------
# 5. THE GATE. check_supplier_index_awards() must fire on the failure shape and
#    stay quiet on a good build — otherwise the fix above is one careless edit
#    from being removed again with nothing to notice.
# ---------------------------------------------------------------------------
def gate(published, working):
    sys.path.insert(0, HERE)
    import importlib
    v = importlib.import_module("verify")
    importlib.reload(v)
    v.fails[:] = []
    v.warns[:] = []
    v.check_supplier_index_awards({"suppliers": working},
                                  committed_index={"suppliers": published})
    return [m for c, m in v.fails if c == "index-awards"]

print("the gate catches a build that drops a published award")
pub = [{"name": "Acme Medical", "awards": [award("Wound care consumables")]}]
check("fires when the award is gone",
      len(gate(pub, [{"name": "Acme Medical", "awards": []}])) == 1)
check("quiet when the award is still there",
      gate(pub, [{"name": "Acme Medical", "awards": [award("Wound care consumables")]}]) == [])
check("quiet when the build ADDS an award",
      gate(pub, [{"name": "Acme Medical", "awards": [award("Wound care consumables"),
                                                     award("Gloves")]}]) == [])
check("silent about a supplier that has left the index entirely",
      gate(pub, [{"name": "Other Medical", "awards": []}]) == [])

print()
if FAILURES:
    print("FAILED: %s" % ", ".join(FAILURES))
    sys.exit(1)
print("all cases pass — awards survive a rebuild and the gate says so")
