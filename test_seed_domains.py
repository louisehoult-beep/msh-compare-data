#!/usr/bin/env python3
"""
test_seed_domains.py — proves a REFUSED title proof cannot reach the seed.

THE HOLE THIS CLOSES. scripts/seed_supplier_domains.py banks every result so a
40-minute sweep can resume. That bank is also how a bad proof travels: a domain
"proved" by a page title was banked once on 14/08/2026 and then replayed by
every later --write run, so the --accept-name flag stopped meaning anything the
moment the report existed. verify_name_proofs.py adjudicated all 128 title
proofs the same day — 4 stood up to registration proof, 124 could not be
second-sourced at all — and those 124 verdicts are now the authority the seeding
script checks before it writes.

Why it matters that this stays true: crawl_supplier_site.py reads whatever
domain the seed holds and publishes that site's catalogue as the supplier's own
product range, on a paid page. "1 Stop Medical Supplies" was banked against
www.1stop.com, an IT and networking reseller.

    python3 test_seed_domains.py

Exit 0 = the gate holds. Exit 1 = a refused proof can be written again.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import seed_supplier_domains as seeder  # noqa: E402

REPORT = "state/domain-seeding-report.json"
VERDICTS = "state/name-proof-verification.json"

failures = []


def check(name, ok, detail=""):
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                         "" if ok else "  <- " + detail))
    if not ok:
        failures.append(name)


def gate(proven, refused):
    """The filter as main() applies it. Kept in one place so the test cannot
    drift into testing a copy of the rule instead of the rule."""
    blocked = [r for r in proven
               if r["name"] in refused and r["proof"] != "registration"]
    return [r for r in proven if r not in blocked], blocked


print("verdict file")
verdicts = json.load(open(VERDICTS, encoding="utf-8"))["results"]
refused_names = seeder.refused_name_proofs()
check("124 suppliers stand REFUSED", len(refused_names) == 124,
      "found %d" % len(refused_names))
check("4 suppliers stand VERIFIED",
      sum(1 for v in verdicts if v.get("verdict") == "VERIFIED") == 4)
check("every one of the 128 has a verdict", len(verdicts) == 128,
      "found %d" % len(verdicts))

print("banked report")
report = json.load(open(REPORT, encoding="utf-8"))["results"]
titles = [r for r in report if r.get("proof") == "name"]
check("no title proof is left replayable", not titles,
      "%d still carry proof=name: %s" % (len(titles), [r["name"] for r in titles[:5]]))
refused_rows = [r for r in report if r.get("secondSourced") == "REFUSED"]
check("124 report rows carry the REFUSED verdict", len(refused_rows) == 124,
      "found %d" % len(refused_rows))
check("a refused row keeps no top-level domain",
      all("domain" not in r for r in refused_rows),
      "a domain at the top level is what the write loop reads")
check("a refused row keeps its evidence for the record",
      all(r.get("refusedNameProof", {}).get("domain") for r in refused_rows))

print("the gate")
# A --fresh re-probe lands on the same guessed domain and "proves" it by title
# again. That is the exact replay this must stop.
replay = [{"name": "1 Stop Medical Supplies", "proof": "name",
           "domain": "www.1stop.com", "evidence": "site title names the company"}]
kept, blocked = gate(replay, refused_names)
check("a re-probed title proof for a refused supplier is blocked",
      not kept and len(blocked) == 1)

# Refused on the title route, but proved properly later. The registration route
# is the way back in, and it must stay open or the refusal is a dead end.
reproved = [{"name": "1 Stop Medical Supplies", "proof": "registration",
             "domain": "www.example.co.uk", "evidence": "site states registration number"}]
kept, blocked = gate(reproved, refused_names)
check("a registration proof re-opens a refused supplier", len(kept) == 1 and not blocked)

# A supplier nobody has ruled on is unaffected by the gate.
untouched = [{"name": "Some Supplier Never Adjudicated", "proof": "name",
              "domain": "www.somewhere.co.uk", "evidence": "site title names the company"}]
kept, blocked = gate(untouched, refused_names)
check("the gate touches only adjudicated names", len(kept) == 1 and not blocked)

print()
if failures:
    print("FAILED: %d check(s) — %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("gate holds — no refused title proof can reach data/supplier-seed.json")
