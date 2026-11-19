"""One-off: re-run the name rule over the names quarantined as ambiguous, now
that attach_names() tries a territory-preserving key before giving up
(18/11/2026).

WHY. The gate's third framework-lots warning counted names that reach TWO brief
rows, and told the reader to "de-duplicate the brief's supplier list". On the
one clinical case that was the wrong remedy, and NHS Supply Chain's own brief
says so: Urology and Bowel Management states "There are 57 suppliers on this
framework" and prints 57, naming BOTH

    Clinisupplies GB Limited
    Clinisupplies Ltd

so the capture is not duplicated — the brief genuinely names two companies.
Companies House, read 18/11/2026, confirms two live registrations at the same
Watford address: CLINISUPPLIES LIMITED 04013240 (incorporated 13 June 2000) and
CLINISUPPLIES GB LIMITED 02503030 (incorporated 17 May 1990). Different
numbers, so under data/identity-vocabulary-policy.json they are different
companies and the shared address is not evidence otherwise. Deleting either row
would have falsified a correct capture.

The defect was in the matcher. company_match.key() strips the trailing
territory word, so both brief rows key to "clinisupplies" and the award
notice's "Clinisupplies Limited" reached both. company_match.resolve() already
guards against exactly this with its verbatim tier — the published rule says it
exists "so two real companies whose names differ only by a territory word are
told apart rather than quarantined against each other" — but attach_names()
keyed brief rows with key() alone, so brief-row matching never had that guard.
A verbatim tier alone would not have helped here either: these sources write
the legal form long in one place ("Limited") and short in the other ("Ltd"), so
norm() matches none of the three names to each other.

attach_names() now retries an ambiguous match on company_match.
key_keep_territory() — legal form canonicalised, territory word kept. It fires
only where the wider key was already ambiguous, and a tie on the narrower key
is still quarantined, so it can only narrow.

WHAT THIS CHANGES, MEASURED BEFORE WRITING. Across every framework in the file
exactly two names were quarantined as ambiguous, and the tier settles both:

  Urology and Bowel Management  "Clinisupplies Limited"  -> "Clinisupplies Ltd"
      Lots 1, 2, 3, 5 and 10. 04013240's own registered name; the other row is
      02503030.
  Beverages, Confectionary and Snacks  "Nestle UK Ltd"   -> "Nestle UK"
      Lots 1 and 13, by the same reading of the notice's own words. This
      framework is food and stays out of scope for Hub RECORDS under Lou's
      17/11/2026 non-clinical ruling; attaching a lot to a brief row creates no
      record and adds none.

It re-reads nothing. No brief, award notice or matrix is fetched: it re-runs the
rule over the names the file already holds in `unresolved`, and touches only
names that move from quarantined to resolved. Idempotent.

USAGE
    python3 scripts/_reattach_territory_tier_1118.py [--dry-run]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh_framework_lots as R  # noqa: E402
import seed_format  # noqa: E402


def main(argv):
    dry = "--dry-run" in argv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    seed = json.load(open("data/supplier-seed.json", encoding="utf-8"))
    fwdoc = json.load(open(R.FW_PATH, encoding="utf-8"))
    lotsdoc = json.load(open(R.LOTS_PATH, encoding="utf-8"))
    to_company = R.resolver(seed)
    by_url = {f.get("url"): f
              for f in (fwdoc.get("frameworks") or []) + (fwdoc.get("expired") or [])}

    moved = 0
    for url, rec in (lotsdoc.get("frameworks") or {}).items():
        amb = [u for u in rec.get("unresolved") or []
               if "matches" in (u.get("reason") or "")]
        if not amb:
            continue
        suppliers = (by_url.get(url) or {}).get("suppliers") or []
        src = {u["name"]: set(u["lots"]) for u in amb}
        spelled = {}
        got, still = R.attach_names(src, suppliers, to_company, spelled)
        if not got:
            continue
        settled = {u["name"] for u in amb} - {u["name"] for u in still}
        lots = {b: set(v) for b, v in (rec.get("supplierLots") or {}).items()}
        for b, v in got.items():
            lots.setdefault(b, set()).update(v)
            for kind in sorted({u.get("source") or "fts-award"
                                for u in amb if u["name"] in settled}):
                cur = set((rec.setdefault("lotsBySource", {})
                           .setdefault(kind, {})).get(b) or [])
                rec["lotsBySource"][kind][b] = sorted(cur | set(v),
                                                     key=R.lot_sort_key)
            moved += 1
            print("  + %-38s %-26s -> %-26s %s"
                  % (rec["name"][:38], sorted(settled)[0][:26], b[:26],
                     sorted(v, key=R.lot_sort_key)))
        for b, names in spelled.items():
            other = sorted(n for n in names if n != b)
            if other:
                rec.setdefault("namedAs", {})[b] = sorted(
                    set((rec.get("namedAs") or {}).get(b) or []) | set(other))
        rec["unresolved"] = [u for u in rec.get("unresolved") or []
                             if u["name"] not in settled]
        rec["supplierLots"] = {b: sorted(v, key=R.lot_sort_key)
                               for b, v in sorted(lots.items())}
        if rec["supplierLots"]:
            rec["status"] = "published"
        rec["suppliersWithoutLot"] = [x for x in suppliers
                                      if x not in rec["supplierLots"]] \
            if rec["status"] == "published" else []
        covered = sorted({l for q in rec.get("sources") or []
                          for l in q.get("coversLots") or []}, key=R.lot_sort_key)
        rec["coversLots"] = covered or None
        rec["lotsNotCovered"] = sorted(
            [k for k in (rec.get("lotTitles") or {})
             if not any(l == k or re.match(re.escape(k) + r"[.a-z]", l)
                        for l in covered)],
            key=R.lot_sort_key) if rec["status"] == "published" else []

    lotsdoc["counts"] = {st: sum(1 for r in (lotsdoc.get("frameworks") or {}).values()
                                 if r.get("status") == st) for st in R.STATUSES}
    lotsdoc["rule"] = R.RULE

    if not moved:
        print("nothing moved out of quarantine; file unchanged.")
        return
    if dry:
        print("\n--dry-run: %d name(s) would move, nothing written." % moved)
        return
    fmt, round_trips = seed_format.write_like(R.LOTS_PATH, lotsdoc)
    print(" ", seed_format.describe(R.LOTS_PATH, fmt, round_trips))
    R.attach(fwdoc, lotsdoc)
    fmt, round_trips = seed_format.write_like(R.FW_PATH, fwdoc)
    print(" ", seed_format.describe(R.FW_PATH, fmt, round_trips))
    print("\n%d name(s) moved out of quarantine. Now: bash scripts/gate.sh" % moved)


if __name__ == "__main__":
    main(sys.argv[1:])
