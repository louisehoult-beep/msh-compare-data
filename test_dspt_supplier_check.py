#!/usr/bin/env python3
"""Fixture tests for scripts/refresh_dspt_suppliers.py (no network).

  python3 test_dspt_supplier_check.py
"""
import importlib.util
import json
import os
import sys

spec = importlib.util.spec_from_file_location("rd", "scripts/refresh_dspt_suppliers.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(label)
        print("FAIL  %s: got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


CSV = '''" Code"," Organisation Name"," Status"," Date Of Publication"," Primary Sector"," ICB"
" 8HM92"," HEALTH NET CONNECTIONS LTD"," 2025-26 (version 8) - Standards exceeded"," 30 June 2026"," IT Supplier",""
" X1"," Acme Health"," 2025-26 (version 8) - Standards met"," 1 June 2026"," IT Supplier",""
" X2"," ACME HEALTH"," Not Published",""," No Sector Identified",""
" N4H0A"," SIM&CURE"," Not Published",""," No Sector Identified",""
" Z9"," Huma Therapeutics"," 2025-26 (version 8) - Standards met"," 2 June 2026"," IT Supplier",""
" A1"," ACCURX LIMITED"," 2025-26 (version 8) - Standards met"," 3 June 2026"," IT Supplier",""
" B1"," Two Orgs Ltd"," 2025-26 (version 8) - Standards met"," 4 June 2026"," IT Supplier",""
" B2"," Two Orgs Trading"," Not Published",""," No Sector Identified",""
'''
TERMS_OK = "<p>Crown copyright protected material may be reproduced free of charge in\n any format or medium, provided it is reproduced accurately</p>"
seed = {"suppliers": [
    {"name": "Health Net Connections Ltd", "specialities": ["Digital health / AI"]},
    {"name": "Acme Health", "specialities": ["Digital and medical IT"]},
    {"name": "Huma", "specialities": ["Digital health / AI"],
     "aliases": ["Huma", "Huma Therapeutics Limited"]},
    {"name": "Accurx", "specialities": ["Digital health / AI"],
     "aliases": ["Accurx", "Accurx Limited", "accurx.com"]},
    {"name": "Two Orgs", "specialities": ["Digital and medical IT"],
     "aliases": ["Two Orgs Ltd", "Two Orgs Trading"]},
    {"name": "Was Sold Ltd", "specialities": ["Digital health / AI"],
     "previousNames": ["Huma Therapeutics"]},
    {"name": "Sim & Cure", "specialities": ["Digital and medical IT"]},
    {"name": "Not Digital Ltd", "specialities": ["Pathology and laboratory"]},
]}

check("norm folds case, ampersand, punctuation", rd.norm("SIM&CURE, Ltd."), rd.norm("sim and cure ltd"))
dig = rd.digital_suppliers(seed)
check("only Digital-tagged suppliers selected", [s["name"] for s in dig],
      ["Health Net Connections Ltd", "Acme Health", "Huma", "Accurx", "Two Orgs",
       "Was Sold Ltd", "Sim & Cure"])
check("domain-shaped aliases are not names", rd.looks_like_a_domain("accurx.com"), True)
check("a real name is not a domain", rd.looks_like_a_domain("Accurx Limited"), False)
check("candidate names start with the supplier's own and drop domains",
      rd.candidate_names({"name": "Accurx", "aliases": ["Accurx", "Accurx Limited", "accurx.com"]}),
      ["Accurx", "Accurx Limited"])
out = rd.build(dig, rd.parse_export(CSV), "2026-10-20")
by = {s["name"]: s for s in out["suppliers"]}
h = by["Health Net Connections Ltd"]
check("exact match gives status as published", (h["dsptStatus"], h["statusDate"], h["odsCode"]),
      ("2025-26 (version 8) - Standards exceeded", "30 June 2026", "8HM92"))
check("sourceUrl present", h["sourceUrl"], rd.SEARCH_URL)
check("duplicate name is ambiguous, no single status",
      ("dsptStatus" in by["Acme Health"], by["Acme Health"]["ambiguous"]), (False, True))
check("an alias matches the registered name",
      (by["Accurx"]["matchedOn"], by["Accurx"]["odsCode"], by["Accurx"]["dsptStatus"]),
      ("Accurx Limited", "A1", "2025-26 (version 8) - Standards met"))
check("matchedOn is the supplier's own name when that is what matched",
      by["Health Net Connections Ltd"]["matchedOn"], "Health Net Connections Ltd")
check("two DSPT organisations under one supplier's names is ambiguous",
      ("dsptStatus" in by["Two Orgs"], by["Two Orgs"]["ambiguous"]), (False, True))
check("still no fuzzy match: bare Huma never reaches Huma Therapeutics without an alias",
      rd.build([{"name": "Huma", "specialities": ["Digital health / AI"]}],
               rd.parse_export(CSV), "2026-10-20")["unmatched"], ["Huma"])
# "Huma"'s only alias is "Huma Therapeutics Limited", which this CSV does not
# carry, so it stays unmatched: an alias is still an exact match, not a near one.
check("previousNames are never matched, and a near-miss alias does not match",
      out["unmatched"], ["Huma", "Was Sold Ltd"])
check("Sim & Cure matches SIM&CURE, Not Published kept as published", by["Sim & Cure"]["dsptStatus"], "Not Published")
check("non-digital never appears", "Not Digital Ltd" in by or "Not Digital Ltd" in out["unmatched"], False)
check("terms wording detected across line breaks", rd.terms_permit_reuse(TERMS_OK), True)
check("terms wording missing refuses", rd.terms_permit_reuse("<p>All rights reserved</p>"), False)
check("robots with only Allow rules permits", rd.robots_allows_export("User-agent: *\nAllow: /OrganisationSearch"), True)
check("robots Disallow blocks", rd.robots_allows_export("User-agent: *\nDisallow: /OrganisationSearch"), False)
if os.path.exists("data/dspt-supplier-check.json"):
    d = json.load(open("data/dspt-supplier-check.json"))
    check("data file defined", d["defined"], True)
    check("data file every supplier has source and status", all(
        s["sourceUrl"] and (s.get("ambiguous") or s["dsptStatus"]) for s in d["suppliers"]), True)
sys.exit(1 if FAILURES else 0)
