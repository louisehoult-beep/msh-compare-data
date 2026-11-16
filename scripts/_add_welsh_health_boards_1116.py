#!/usr/bin/env python3
"""
_add_welsh_health_boards_1116.py — one-off. Put the seven Welsh Local Health
Boards into data/trust-map.json now, rather than waiting for Saturday.

WHY THIS EXISTS. refresh_trusts.py was changed on 16/11/2026 to crawl ODS role
RO142 (LOCAL HEALTH BOARD) as well as RO197 and RO107, so Wales's seven actual
buyers reach the Hub. That crawl is weekly-refresh.yml's job and runs Saturdays
at 20:45 UTC. Wales coverage was wanted for a call before then, and shipping the
app/mst-logic.js Wales branch with no Welsh boards in the data would put a picker
on a live page whose every board entry resolved to nothing.

WHY IT IMPORTS refresh_trusts RATHER THAN REIMPLEMENTING IT. A one-off that
re-derives the same rows by its own logic is a second definition of what a trust
row is, and the two drift. This calls refresh_trusts.fetch_detail and
refresh_trusts.kind_for, so a row written here is byte-identical to the row
Saturday's crawl will write. If they ever disagree, this script is wrong, not the
refresher.

python has no DNS in the sandbox this was written in, so the ODS records are read
from a directory of files fetched with curl:

  mkdir -p /tmp/ods && cd /tmp/ods
  curl -s "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?PrimaryRoleId=RO142&Status=Active&Limit=1000" -o list-RO142.json
  for c in 7A1 7A2 7A3 7A4 7A5 7A6 7A7; do \
    curl -s "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/$c" -o "org-$c.json"; done

  python3 scripts/_add_welsh_health_boards_1116.py --ods-dir /tmp/ods

Idempotent: a board already in the file is left alone, not duplicated.
Delete this script once Saturday's refresh has run — the refresher owns this.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import refresh_trusts as rt  # noqa: E402

MAP_PATH = os.path.join(HERE, "data", "trust-map.json")
EXPECTED = 7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ods-dir", required=True,
                    help="Directory holding list-RO142.json and org-<code>.json")
    args = ap.parse_args()

    with open(os.path.join(args.ods_dir, "list-RO142.json")) as fh:
        listed = json.load(fh)["Organisations"]

    # fetch_detail takes the list entry and follows its OrgLink. Point that link
    # at the local copy so the shared code path is used unchanged.
    rows = []
    for o in listed:
        local = os.path.join(args.ods_dir, "org-%s.json" % o["OrgId"])
        if not os.path.exists(local):
            print("MISSING: %s (%s) — fetch it before re-running."
                  % (o["OrgId"], o["Name"]), file=sys.stderr)
            return 1
        row = rt.fetch_detail(dict(o, OrgLink="file://" + local))
        if row is None:
            print("  skip   %s %s (legally ended, or unreadable)"
                  % (o["OrgId"], o["Name"]))
            continue
        if row["nation"] != "Wales":
            print("  skip   %s %s (ODS country %r, not Wales)"
                  % (o["OrgId"], o["Name"], row["odsCountry"]))
            continue
        rows.append(row)

    if len(rows) != EXPECTED:
        print("ABORT: %d Welsh Local Health Board(s), expected %d. Refusing to write "
              "a partial Wales." % (len(rows), EXPECTED), file=sys.stderr)
        return 1

    doc = json.load(open(MAP_PATH))
    trusts = doc["trusts"]
    have = {t["code"] for t in trusts}
    added = [r for r in rows if r["code"] not in have]

    if not added:
        print("trust-map.json already carries all %d Welsh health boards — nothing to do."
              % EXPECTED)
        return 0

    # Backfill odsCountry on the rows already in the file. They were written
    # before the field existed, and a file where some rows carry it and some do
    # not is the kind of half-migration that makes the next reader guess.
    for t in trusts:
        t.setdefault("odsCountry", "WALES" if t.get("nation") == "Wales" else "ENGLAND")

    trusts.extend(added)
    # Same ordering the refresher uses, so Saturday's rewrite is a no-op diff.
    trusts.sort(key=lambda e: (0 if e["kind"] is None else 1, e["n"]))
    doc["trusts"] = trusts
    doc["count"] = len(trusts)
    doc["asOf"] = datetime.date.today().strftime("%d/%m/%Y")
    doc["walesNote"] = (
        "Wales has no Integrated Care Boards. The seven Local Health Boards are "
        "both commissioner and provider for their area, so every Welsh row "
        "carries a null icb. Almost all Welsh buying goes through NHS Wales "
        "Shared Services Partnership (NWSSP) Procurement Services, hosted by "
        "Velindre University NHS Trust. See data/wales-buyer-map.json.")

    with open(MAP_PATH, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)

    for r in added:
        print("  added  %s  %s  (%s)" % (r["code"], r["n"], r["town"]))
    print("trust-map.json: %d trusts, %d of them Welsh."
          % (len(trusts), sum(1 for t in trusts if t["nation"] == "Wales")))
    print("NOW RUN: python3 scripts/stamp_notice.py && python3 verify.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
