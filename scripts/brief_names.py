#!/usr/bin/env python3
"""The one rule for cleaning supplier names out of NHS Supply Chain briefs.

NHS Supply Chain's contract launch briefs decorate supplier names with editorial
notes about the award rather than the company:

    Accora Ltd - New
    2San Global Limited (New to the framework and NHS Supply Chain)
    NJ Devices Ltd t/a Ocean Med - (New supplier)
    MCT Lifesciences Ltd (New to framework)
    OscarTech UK Ltd*

Those are formatting, not names. Left in, one company becomes seven — OscarTech
appeared seven times on the supplier gap list as seven separate companies.

THIS FILE IS THE ONLY HOME FOR THAT RULE. It lives in the repo because the briefs
do; anything that reads data/frameworks.json imports it rather than writing its
own regex. It was split out on 14/08/2026 after a second, weaker copy in
backfill_seed_from_frameworks.py silently dropped MCT Lifesciences' third
framework — it stripped the trailing "- New" form but not the bracketed one.

Trading names are deliberately NOT stripped. "t/a Ocean Med" is a real
alternative name a Hub section might legitimately hold.
"""
import re

DECORATION = [
    re.compile(r"\((?:[^)]*\b(?:new|incumbent|existing|current)\b[^)]*)\)", re.I),
    re.compile(r"[–—-]\s*\(?\s*(?:new|incumbent|existing)\b[^)]*\)?\s*$", re.I),
    re.compile(r"\bnew to (?:the )?framework\b[^,]*", re.I),
    re.compile(r"\*+$"),
]


def clean(raw):
    """Strip brief formatting from a supplier name. Idempotent."""
    s = (raw or "").replace("–", "-").replace("—", "-")
    prev = None
    while prev != s:
        prev = s
        for pat in DECORATION:
            s = pat.sub(" ", s).strip(" -,;")
    return " ".join(s.split()) or (raw or "").strip()
