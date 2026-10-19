#!/usr/bin/env python3
"""^o641: mapped NHSSC terms are read before unmapped ones, so a second unmapped
term carrying the same catalogue name cannot starve the mapped one in the
(supplier, name) dedup. Usage: python3 test_differentiator_mapped_terms_first.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from build_differentiator import nhssc_terms_mapped_first, norm

nh = {"products": {
    "Gynaecology resectoscopes": {"supplier": "Olympus (KeyMed)", "items": []},
    "THUNDERBEAT / POWERSEAL (energy)": {"supplier": "Olympus (KeyMed)", "items": []},
    "Other": {"supplier": "Acme", "items": []},
}}
m = {(norm("Olympus (KeyMed)"), norm("THUNDERBEAT / POWERSEAL (energy)")): ["mis:energy"]}
order = [t for t, _ in nhssc_terms_mapped_first(nh, m)]
assert order[0] == "THUNDERBEAT / POWERSEAL (energy)", order
assert order[1:] == ["Gynaecology resectoscopes", "Other"], order  # stable
# same supplier + term, different supplier: only the matching supplier counts as mapped
nh2 = {"products": {"X": {"supplier": "B", "items": []}, "Y": {"supplier": "A", "items": []}}}
assert [t for t, _ in nhssc_terms_mapped_first(nh2, {(norm("A"), norm("Y")): ["c:t"]})] == ["Y", "X"]
print("ok")
