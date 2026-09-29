#!/usr/bin/env python3
"""A framework named twice under one reference must draw one row (^o206).

Find a Tender and the NHS Supply Chain launch brief both name the same award and
the seed holds both, so supplier-search.js drew a row for each. The build now
collapses them. These cases pin the rule: same reference AND same name merges,
a shared reference across different lots never does, and a disagreement on a
core field is left alone rather than guessed.

  python3 test_supplier_index_framework_dedupe.py     exit 0 = rule holds
"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bsi", os.path.join(HERE, "build_supplier_index.py"))
bsi = importlib.util.module_from_spec(spec); spec.loader.exec_module(bsi)
D = bsi.dedupe_frameworks
FAIL = []

def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: FAIL.append(name)

R = "2026/S 000-061906"
a = {"name": "Minimally Invasive Surgery, Related Equipment and Accessories", "dates": None, "reference": R, "supplierCount": 60}
b = {"name": "Minimally Invasive Surgery, Related Equipment and Accessories", "dates": "10 August 2026 to 9 August 2028", "reference": R, "supplierCount": 60, "source": "nhssc-brief"}
out, n = D([a, b])
check("same reference and name collapse to one", len(out) == 1 and n == 1)
check("the kept entry takes the dates it lacked", out[0]["dates"] == "10 August 2026 to 9 August 2028" and out[0]["source"] == "nhssc-brief")

c = {"name": "Static X-Ray", "reference": "2021/S 1", "dates": "x"}
d = {"name": "Mobile X-Ray", "reference": "2021/S 1", "dates": "x"}
out, n = D([c, d])
check("one reference over two different lots stays as two", len(out) == 2 and n == 0)

e = dict(b, dates="1 May 2027 to 1 May 2029")
out, n = D([b, e])
check("conflicting dates are not merged or guessed", len(out) == 2 and n == 0)

out, n = D([{"name": "NHS TPN framework"}, {"name": "NHS TPN framework"}, "prose entry", "prose entry"])
check("entries with no reference and plain strings pass through untouched", len(out) == 4 and n == 0)

check("case and punctuation do not hide a duplicate",
      len(D([{"name": "Wound Closure, and Products", "reference": "r"}, {"name": "wound closure and products", "reference": "r"}])[0]) == 1)
check("empty and None input are safe", D(None) == ([], 0) and D([]) == ([], 0))
out, _ = D([a, b, c]); check("order of survivors is preserved", [x["name"][:4] for x in out] == ["Mini", "Stat"])
sys.exit(1 if FAIL else 0)
