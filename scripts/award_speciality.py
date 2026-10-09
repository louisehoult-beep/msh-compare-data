"""award_speciality.py: one speciality slug for a notice or award row, for page 3198's
speciality filter (Frameworks and Awards: Tenders, Awards, Contracts tabs).

WHY (09/10/2026). The awards and open-tenders taggers left 76% of awards and every
open notice "unclassified", so choosing a speciality on page 3198 showed the wrong
rows. They now share the speciality panels' curated rules
(build_speciality_panels.SPECIALITY_RULES), plus the corrections below. An audit of
the first re-tag found them: 2.5-4.5% wrong, mostly non-NHS buyers (college
manikins, council staff eye tests, a university drama theatre) and a few loose
terms (dental chairs as patient handling, vaccination trolleys as wound care).

The panel rules are not edited here: a panel lists every award a rule matches, while
this picks ONE slug per row for a filter label, so the extra excludes belong to the
label only. Nothing matching stays "unclassified"; a slug is never guessed.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Buyers whose purchases are not NHS buying signals even when the kit is clinical:
# university and college training manikins, research scanners, fire-service medical
# gas, police flu jabs. Councils are NOT here: integrated community equipment, hoists
# and telecare bought by councils are real buying signals for those suppliers.
NON_NHS_BUYER = re.compile(
    r"(universit|college|school|academy|fire (and|&) rescue|fire service|police|"
    r"forestry|british council|courts? service|prison)", re.I)
# ...unless the buyer is plainly a health body ("Oxford University Hospitals",
# "University College London Hospitals"; one source spells it "Hopsit").
NHS_BUYER = re.compile(r"(nhs|hosp|hopsit|infirmary|\bkfm\b|health|trust|foundation|integrated care|"
                       r"\bicb\b|supply chain|shared services|common services agency|"
                       r"business services organisation|\bhse\b)", re.I)

# Titles that are never a buying signal for a clinical speciality: training and
# simulation kit, and dental (the Hub has no dental speciality).
NOT_A_SIGNAL = re.compile(r"\b(manikins?|mannequins?|simulat\w*|phantoms?|"
                          r"task trainers?|dental)\b", re.I)

# Extra excludes for the label only, per slug.
EXTRA_EXCLUDE = {
    "patient-handling": r"\b(mobile surgery system|surgery system|operating table)\b",
    "tissue-viability-and-wound-care": r"\b(trolleys?|retention|sutures?|haemostat\w*|"
                                       r"barbed|tissue adhesives?|"
                                       r"pressure area care and patient handling|pacph)\b",
    "theatres-and-surgical": r"\b(gloves?|gowns?)\b",
    "capital-estates-watch": r"\b(refurbished replacement|ventilation machines?|"
                             r"ventilators?|library|flooring|autoclave|asbestos|"
                             r"recording booths?|legionella)\b",
    "ophthalmology": r"\b(employees?|staff|dse|vouchers?|corporate)\b",
    "audiology-and-hearing": r"\b(loop induction|hearing loop)\b",
}

_RULES = None


def _rules():
    global _RULES
    if _RULES is None:
        import build_speciality_panels as bsp
        out = []
        for slug, rule in bsp.SPECIALITY_RULES.items():
            if not rule.get("include"):
                continue
            exc = [rule.get("exclude"), EXTRA_EXCLUDE.get(slug)]
            exc = "|".join("(?:%s)" % e for e in exc if e)
            out.append((slug, re.compile(rule["include"], re.I),
                        re.compile(exc, re.I) if exc else None))
        _RULES = out
    return _RULES


def tag(title, buyer=""):
    """The first speciality rule the title matches, or "unclassified"."""
    t = title or ""
    b = buyer or ""
    if b and NON_NHS_BUYER.search(b) and not NHS_BUYER.search(b):
        return "unclassified"
    if NOT_A_SIGNAL.search(t):
        return "unclassified"
    for slug, inc, exc in _rules():
        if inc.search(t) and not (exc and exc.search(t)):
            return slug
    return "unclassified"
