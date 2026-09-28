#!/usr/bin/env python3
"""
Invariant gate for the NHSSC cache row repair (scripts/repair_nhssc_cache_rows.py).

The repair writes catalogue values over rows the old positional parser misread.
Its failure modes are writing a card over the wrong row, touching a row that
was never misread, or dropping a row the catalogue no longer serves. Each check
is self-tested against a deliberately wrong input, so none passes vacuously.

Usage:  python3 test_repair_nhssc_cache_rows.py
"""

from __future__ import annotations

import copy
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import repair_nhssc_cache_rows as RP                                # noqa: E402

failures: list[str] = []
checks = 0


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        failures.append(what)
    return ok


# The ELA679 row exactly as the old parser wrote it, and the card as read live
# on 28/09/2026.
SHIFTED = {"name": "SUSPENDED", "supplier": "Cuticell Contact", "desc": "ESSITY UK TENA HM",
           "npc": "ELA679", "mpc": "ELA679", "status": "", "pack": "Pack of 5", "img": "old.jpg"}
LIVE = {"name": "Cuticell Contact", "supplier": "ESSITY UK TENA HM",
        "desc": "Wound contact layer silicone dressing one sided 10cm x 18cm",
        "npc": "ELA679", "mpc": "72762-02", "status": "Suspended", "pack": "Pack of 5", "img": ""}
GOOD = {"name": "Biatain Contact", "supplier": "COLOPLAST LIMITED",
        "desc": "Wound contact layer silicone dressing one sided 10 x 18",
        "npc": "EKH112", "mpc": "33562", "status": "", "pack": "Pack of 5", "img": "e.jpg"}
GONE = {"name": "Pennine", "supplier": "PENNINE HEALTHCARE", "desc": "Gauze swab 10cm",
        "npc": "FWP084", "mpc": "FWP084", "status": "", "pack": "Each", "img": ""}


def cache():
    return {"products": {"Cuticell": {"items": [copy.deepcopy(SHIFTED), copy.deepcopy(GOOD)]},
                         "NPC:ELA679": {"items": [copy.deepcopy(SHIFTED)]},
                         "Pennine": {"items": [copy.deepcopy(GONE)]}}}


def test_picks_only_misread_rows():
    aff = RP.affected_npcs(cache())
    check(set(aff) == {"ELA679", "FWP084"}, "wrong rows picked for repair: %s" % sorted(aff))
    check("EKH112" not in aff, "a correctly read row was picked for repair")


def test_rewrites_every_copy_and_nothing_else():
    c = cache()
    stats, missing = RP.apply(c, {"ELA679": dict(LIVE), "FWP084": None, "EKH112": dict(LIVE)})
    rows = [it for rec in c["products"].values() for it in rec["items"] if it["npc"] == "ELA679"]
    check(len(rows) == 2 and all(r["desc"] == LIVE["desc"] and r["mpc"] == "72762-02"
                                 and r["status"] == "Suspended" for r in rows),
          "not every copy of ELA679 was repaired: %s" % rows)
    check(all(r["img"] == "old.jpg" for r in rows), "an empty fetched image wiped a stored one")
    good = c["products"]["Cuticell"]["items"][1]
    check(good == GOOD, "a correctly read row was overwritten (self-test fed it a wrong card)")
    check(missing == {"FWP084": "not served by the catalogue"}, "missing report wrong: %s" % missing)
    gone = c["products"]["Pennine"]["items"]
    check(gone == [dict(GONE, mpc="")],
          "a row the catalogue no longer serves must be kept, with only its NPC-as-MPC blanked: %s" % gone)
    c2 = cache()
    RP.apply(c2, {"FWP084": "error"})
    check(c2["products"]["Pennine"]["items"] == [GONE],
          "a fetch ERROR is not evidence: the row must be left exactly as it was")
    check(stats["items_rewritten"] == 2, "rewrite count wrong: %s" % stats)


def test_a_card_is_never_written_over_a_different_npc():
    c = cache()
    RP.apply(c, {"ELA679": dict(LIVE, npc="ELA999")})
    # apply() trusts fetch_all's exact-NPC match; this pins that it never writes
    # the npc field itself, so a mismatched card cannot re-key a row.
    rows = [it for rec in c["products"].values() for it in rec["items"]]
    check(all(r["npc"] in ("ELA679", "EKH112", "FWP084") for r in rows),
          "a repair re-keyed a row to another NPC")
    check("npc" not in RP.FIELDS, "FIELDS must not include npc")


for fn in (test_picks_only_misread_rows, test_rewrites_every_copy_and_nothing_else,
           test_a_card_is_never_written_over_a_different_npc):
    try:
        fn()
    except Exception as exc:                                        # noqa: BLE001
        failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))

if failures:
    print("NHSSC ROW REPAIR GATE FAILED (%d of %d checks)" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("nhssc row repair gate passed: %d checks" % checks)
