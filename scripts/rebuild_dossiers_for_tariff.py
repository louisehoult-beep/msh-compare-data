#!/usr/bin/env python3
"""
Rebuild the product dossiers when the Drug Tariff Part IX copy has changed.

WHY (01/10/2026)
  data/product-dossiers-{wound,respiratory,dermatology}.json copy Drug Tariff prices
  out of data/drug-tariff-part-ix.json (scripts/build_product_dossiers.py), and
  test_product_dossiers.py checks they still match. drug-tariff.yml refreshed the
  tariff but not the dossiers, so every new tariff month broke the pre-push unit
  tests and blocked every land.sh push until someone rebuilt by hand (01/10, ed7aaaa).

ONLY WHEN THE TARIFF CHANGED. The dossier file carries a `generated` timestamp, so an
  unconditional daily rebuild would commit three large files every day for nothing.
  The tariff's own dataAsOf also moves daily, so "changed" means effectiveMonth or
  rows differ from the committed copy (HEAD), not that the file differs.

NO-LOSS CHECK. A rebuild also re-reads differentiator.json, so it can drop records for
  reasons unrelated to the tariff. land.sh runs check_no_loss.py for hand pushes; the
  workflow had no such check. This runs it on the rebuilt dossiers against HEAD and
  exits 1, naming the records, if any went. A refused rebuild fails the run loudly and
  leaves the committed dossiers (and the committed tariff) live until someone decides.

  python3 scripts/rebuild_dossiers_for_tariff.py
Exit 0 = rebuilt cleanly or nothing to do. Exit 1 = records would be lost.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARIFF = "data/drug-tariff-part-ix.json"
SPECIALITIES = ("wound", "respiratory", "dermatology")


def committed_tariff():
    r = subprocess.run(["git", "show", "HEAD:" + TARIFF], cwd=REPO,
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def tariff_changed():
    old = committed_tariff()
    with open(os.path.join(REPO, TARIFF)) as fh:
        new = json.load(fh)
    if old is None:
        return True
    return (old.get("effectiveMonth"), old.get("rows")) != (new.get("effectiveMonth"), new.get("rows"))


def main():
    if not tariff_changed():
        print("Part IX unchanged since HEAD - product dossiers left as committed.")
        return 0
    print("Part IX changed - rebuilding product dossiers.")
    files = []
    for s in SPECIALITIES:
        subprocess.run([sys.executable, "scripts/build_product_dossiers.py", "--speciality", s],
                       cwd=REPO, check=True)
        files += ["--file", "data/product-dossiers-%s.json" % s]
    r = subprocess.run([sys.executable, "scripts/check_no_loss.py", "--base", "HEAD"] + files, cwd=REPO)
    if r.returncode:
        print("REFUSING: the dossier rebuild drops records (see above) - likely a change in "
              "differentiator.json, not the tariff. Not publishing.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
