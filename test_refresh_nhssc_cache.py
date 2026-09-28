#!/usr/bin/env python3
"""
Invariant gate for the weekly NHS Supply Chain term refresh
(scripts/refresh_nhssc_cache.py).

The refresh's failure mode is a line that is still listed dropping out of the
cache. Until 28/09/2026 a term's items were replaced wholesale whenever the
fresh search returned at least as many lines as before, so a result page that
merely shifted lost real lines: EKH112 (Biatain Contact), ELA451 (Biatain
Silicone) and ELA838 (ActivHeal) all fell out that way, each still live on
NHSSC, and had to be re-added by hand as NPC: entries.

Each check is self-tested: the old count rule is kept here as OLD_RULE and must
FAIL the same check, so no check can pass vacuously.

Usage:  python3 test_refresh_nhssc_cache.py
"""

from __future__ import annotations

import inspect
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import refresh_nhssc_cache as R                                     # noqa: E402

failures: list[str] = []
checks = 0


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        failures.append(what)
    return ok


def item(npc, **kw):
    d = {"name": "Biatain", "supplier": "COLOPLAST LIMITED", "desc": "Foam dressing %s" % npc,
         "npc": npc, "mpc": "M" + npc, "status": "", "pack": "Pack of 5", "img": ""}
    d.update(kw)
    return d


def OLD_RULE(prev_items, fresh_items):
    """The pre-28/09/2026 worker logic: keep prev only if strictly longer."""
    return prev_items if len(prev_items) > len(fresh_items) else fresh_items


def npcs(items):
    return [i.get("npc") for i in items]


def test_same_size_fresh_set_keeps_the_line_it_did_not_return():
    """The EKH112 case: a fresh page of the same size that happens not to show
    one still-listed line must not drop it."""
    prev = [item("EKH112"), item("ELA451"), item("ELA838")]
    fresh = [item("ELA451"), item("ELA838"), item("ELA999")]
    got = npcs(R.merge_items(prev, fresh))
    check("EKH112" in got, "same-size refresh dropped EKH112: %s" % got)
    check(set(got) == {"EKH112", "ELA451", "ELA838", "ELA999"}, "merge lost or invented lines: %s" % got)
    check("EKH112" not in npcs(OLD_RULE(prev, fresh)),
          "self-test: the old count rule must drop EKH112 here")


def test_larger_fresh_set_keeps_the_line_it_did_not_return():
    prev = [item("EKH112"), item("ELA451")]
    fresh = [item("ELA451"), item("ELA838"), item("ELA999")]
    got = npcs(R.merge_items(prev, fresh))
    check("EKH112" in got, "larger refresh dropped EKH112: %s" % got)
    check("EKH112" not in npcs(OLD_RULE(prev, fresh)),
          "self-test: the old count rule must drop EKH112 here too")


def test_smaller_fresh_set_still_takes_its_new_values():
    """The old rule kept a longer prev list wholesale, so a line seen again this
    week kept LAST week's status. Fresh values must win for a line seen again."""
    prev = [item("ELA679"), item("EKH112"), item("ELA451")]
    fresh = [item("ELA679", status="Suspended", mpc="72762-02")]
    out = R.merge_items(prev, fresh)
    by = {i["npc"]: i for i in out}
    check(by["ELA679"]["status"] == "Suspended" and by["ELA679"]["mpc"] == "72762-02",
          "a line seen again kept its stale values: %s" % by["ELA679"])
    check(set(by) == {"ELA679", "EKH112", "ELA451"}, "smaller refresh lost lines: %s" % sorted(by))
    old = {i["npc"]: i for i in OLD_RULE(prev, fresh)}
    check(old["ELA679"]["status"] == "",
          "self-test: the old rule must keep the stale status here")


def test_no_duplicates_and_npc_less_rows_kept():
    prev = [item("EKH112"), item("", desc="deep capture row without an NPC")]
    fresh = [item("EKH112", pack="Box of 10"), item("EKH112", pack="dup")]
    out = R.merge_items(prev, fresh)
    check(npcs(out).count("EKH112") == 1, "duplicate NPC in merged list: %s" % npcs(out))
    check([i for i in out if i["npc"] == "EKH112"][0]["pack"] == "Box of 10",
          "the first fresh card for an NPC must win")
    check(any(i["npc"] == "" for i in out), "an item with no NPC was dropped")
    check(R.merge_items([], []) == [], "empty merge must be empty")
    check(npcs(R.merge_items(None, [item("A1")])) == ["A1"], "no previous entry must be tolerated")


def test_worker_uses_the_merge():
    """The worker must actually call merge_items, and the count comparison that
    caused the drop-outs must be gone from it."""
    src = inspect.getsource(R.worker)
    check("merge_items(" in src, "worker() does not call merge_items")
    check("len(fresh['items'])" not in src and "> len(fresh" not in src,
          "worker() still compares item counts")


for fn in (test_same_size_fresh_set_keeps_the_line_it_did_not_return,
           test_larger_fresh_set_keeps_the_line_it_did_not_return,
           test_smaller_fresh_set_still_takes_its_new_values,
           test_no_duplicates_and_npc_less_rows_kept,
           test_worker_uses_the_merge):
    try:
        fn()
    except Exception as exc:                                        # noqa: BLE001
        failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))

if failures:
    print("NHSSC TERM REFRESH GATE FAILED (%d of %d checks)" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("nhssc term refresh gate passed: %d checks" % checks)
