#!/usr/bin/env python3
"""One-off, 16/11/2026: clear 12 stale rows from data/hub-calendar.json.

verify.py [calendar] failed on 12 rows whose date had passed (BSIR ASM, ABPI
summit, Convenzis x3, ABHI, RCNi, Wounds UK, BAPEN, Procurex Wales, one contract
expiry, World Diabetes Day 2026). The gate's rule: a past row is dropped, except
a framework-end inside the recent-past window, which must carry `past: true`.

The standing pruner (scripts/prune_calendar.py, run daily by calendar-prune.yml)
applies exactly that rule, so this just runs it once now rather than waiting for
01:50 UTC. Nothing is re-dated or invented: World Diabetes Day already has its
own 2027 and 2028 rows in the file. _meta.dataAsOf is untouched.
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(HERE, "prune_calendar.py")]
runpy.run_path(sys.argv[0], run_name="__main__")
