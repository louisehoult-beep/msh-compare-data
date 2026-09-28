#!/usr/bin/env python3
"""Which supplier job listings are relevant to a medical sales professional.

Lou, in chat 28/09/2026: "the careers page should use the job listings please. And
there is no max, they just need to be in the right categories or job titles."

So there is no maximum number of roles and no minimum supplier base. A UK role in
data/supplier-careers.json is shown on the Career Centre (Hub page 679) when its job
title matches a category in config/careers-relevant-roles.json and none of that
file's exclude patterns. That config is the one place the list lives. The page
applies the same file in app/careers-roles.js, and test_careers_relevance.py runs
both implementations over the same real titles so they cannot drift apart.

    python3 scripts/careers_relevance.py            # what the page would show today
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "careers-relevant-roles.json")
DATA = os.path.join(ROOT, "data", "supplier-careers.json")


def load_config(path=CONFIG):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    return compile_config(cfg)


def compile_config(cfg):
    """Compile once. Raises ValueError on a malformed config, so a bad edit fails loudly."""
    if not isinstance(cfg.get("categories"), list) or not cfg["categories"]:
        raise ValueError("config has no categories")
    keys = set()
    cats = []
    for c in cfg["categories"]:
        for f in ("key", "label", "patterns"):
            if not c.get(f):
                raise ValueError("category %r is missing %s" % (c.get("key"), f))
        if c["key"] in keys:
            raise ValueError("duplicate category key %r" % c["key"])
        keys.add(c["key"])
        cats.append((c["key"], c["label"], [_compile(p) for p in c["patterns"]]))
    excl = [_compile(p) for p in cfg.get("exclude", [])]
    return {"categories": cats, "exclude": excl}


# Syntax the browser's RegExp reads differently from Python's re, or not at all.
_NOT_PORTABLE = re.compile(r"\(\?P|\(\?<[=!]|\(\?[aiLmsux]|\\[AZz]")


def _compile(p):
    if _NOT_PORTABLE.search(p):
        raise ValueError("pattern %r uses syntax the page's JavaScript would read "
                         "differently" % p)
    return re.compile(p, re.I)


def classify(title, compiled):
    """Return the category key for a relevant title, or None."""
    t = title or ""
    if any(x.search(t) for x in compiled["exclude"]):
        return None
    for key, _label, pats in compiled["categories"]:
        if any(p.search(t) for p in pats):
            return key
    return None


def relevant_roles(doc, compiled):
    """(roles, suppliers) the page would list: UK roles whose title classifies."""
    out = []
    for s in doc.get("suppliers", []):
        for r in s.get("roles") or []:
            if r.get("uk") is not True or not r.get("url"):
                continue
            cat = classify(r.get("title"), compiled)
            if cat:
                out.append({"supplier": s["name"], "category": cat,
                            "checkedOn": s.get("checkedOn"), **r})
    return out, sorted({r["supplier"] for r in out})


def main():
    compiled = load_config()
    with open(DATA, encoding="utf-8") as f:
        doc = json.load(f)
    roles, suppliers = relevant_roles(doc, compiled)
    labels = {k: l for k, l, _ in compiled["categories"]}
    print("%d matching roles from %d suppliers" % (len(roles), len(suppliers)))
    for r in sorted(roles, key=lambda r: (r["category"], r["title"])):
        print("  [%s] %s | %s | %s" % (labels[r["category"]], r["title"],
                                        r["supplier"], r.get("location", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
