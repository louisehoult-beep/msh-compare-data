#!/usr/bin/env python3
"""press_match.py — the rule that decides whether a news story is about a Hub supplier.

WHY THIS IS A SEPARATE MODULE
-----------------------------
The same rule has to run in two places that must never drift apart: the writer
(scripts/refresh_company_press.py) applies it, and the publish gate (verify.py)
RE-APPLIES it to every item already in data/company-press.json. If the two ever
disagree, the gate fails and nothing publishes. That is the same arrangement as
scripts/company_match.py and the award gate, and for the same reason: a reader
judges a published claim by the rule printed beside it, so the printed rule has
to be the rule that ran (root rule 14).

WHAT IT IS GUARDING AGAINST
---------------------------
Matching a news story on a company name alone eventually publishes the wrong
company's story under a Hub supplier's name. The live example this was written
from, checked on 18/08/2026:

  "Jeenie Solutions" is a UK bariatric patient-handling supplier in Wetherby
  (Companies House 15942976). It carries the alias "Jeenie".

  Google News for "Jeenie Solutions" returns ZERO items.
  Google News for "Jeenie" returns a US remote-interpreting company — "Remote
  Interpreting Platform Jeenie Valued at USD 34m in Series A" (Slator), "Jeenie
  Caps 2025 with Inc. 5000 Ranking" (PR Newswire) — plus two stories about a
  TikTok flight attendant.

Note what a "medical corroborator" alone would have done: the interpreting
company sells medical interpreting, so its coverage is full of "patients",
"healthcare" and "limited English proficiency". The sector test passes on the
WRONG company. The test that actually kills it is the distinctiveness rule
below: "Jeenie" is a single token that is not the supplier's whole name, so it
is not a name this repo will match on at all.

THE RULE (all five, or the item is dropped — never published with a hedge)
-------------------------------------------------------------------------
1. ALIAS       The story text contains one of the supplier's own recorded
               aliases from data/supplier-seed.json, matched as a whole
               word-token sequence after normalisation. Never a fuzzy match,
               never a substring, and never a match on the display name that is
               not also in the alias list. (Verification Standard §10.)
2. DISTINCTIVE A single-token alias only counts when it IS the supplier's whole
               canonical name, or when it is a domain the supplier owns.
               "Jeenie" does not stand for "Jeenie Solutions"; "Abbott" does not
               stand for "Abbott Laboratories Limited". Two-token-and-longer
               aliases always count.
3. SECTOR      The item itself carries a medical / clinical / NHS-sector term.
               A company's name in a story about something else is not news
               about that company's market.
4. RELEVANCE   The item ALSO carries UK or NHS geography, or one of the
               supplier's own recorded specialities, or is carried by a
               UK/clinical named outlet. Sector alone is satisfied by any
               health-adjacent US story.
5. CORROBORATION  At least two DISTINCT reputable publishers carry the same
               story. PR wires, stock-tip sites and SEO syndication never count
               towards it. (This bar predates the module and is applied by the
               writer when it clusters; the gate re-counts it on the file.)

Publishing nothing is the correct output when the evidence is thin (root rule
14). Every rejection is recorded with its reason so the drop rate is visible
rather than looking like an empty feed.
"""
import re

# The string printed into data/company-press.json. verify.py FAILS if the file's
# matchRule is not byte-identical to this, so the rule a reader is shown is
# always the rule that ran.
RULE = (
    "A news story is attached to a Hub supplier only where ALL FIVE of these hold, "
    "and it is dropped outright otherwise. "
    "(1) ALIAS: the story text contains one of that supplier's own recorded aliases from "
    "supplier-seed.json, matched as a whole word-token sequence after normalisation - never a "
    "fuzzy match, never a substring, and never a match on the display name alone. "
    "(2) DISTINCTIVENESS: an alias of two or more tokens, or a domain the supplier owns, stands "
    "for the supplier on its own, and so does a single word that IS the company's whole name "
    "(Coloplast, Convatec, Elekta) provided no other supplier record carries that word. A "
    "single-token alias that is a SHORTENING of a longer name does not stand for it, and "
    "counts only where it is "
    "unique to one supplier across the whole seed, is not a generic trade word, AND the item "
    "also carries one of that same supplier's OWN recorded specialities or product names as a "
    "whole token sequence. So 'Jeenie' alone never stands for 'Jeenie Solutions': a US "
    "translation company of the same name is full of 'patients' and 'healthcare' but carries "
    "nothing from Jeenie Solutions' own bariatric patient-handling range. "
    "(3) SECTOR: the item itself carries a medical, clinical or NHS-sector term, or one of that "
    "supplier's own recorded specialities or product names, which is a more specific clinical "
    "term than any general one. "
    "(4) RELEVANCE: the item also carries UK or NHS geography, or one of that supplier's own "
    "recorded specialities, or is carried by a UK or clinical named outlet. "
    "(5) CORROBORATION: at least two DISTINCT reputable publishers carry the same story; PR "
    "wires, stock-tip sites and SEO syndication never count towards the two. "
    "An item failing any one of the five is not published with a caveat - it is not published."
)

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

# (3) SECTOR. Deliberately broad: this test is a floor, not the discriminator.
SECTOR_TERMS = [
    "nhs", "hospital", "hospitals", "clinic", "clinical", "clinician", "clinicians",
    "medical", "medicine", "medicines", "medtech", "med tech", "surgery", "surgical",
    "surgeon", "patient", "patients", "healthcare", "health service", "health system",
    "diagnostic", "diagnostics", "therapy", "therapeutic", "therapeutics", "nurse",
    "nurses", "nursing", "pharmacy", "pharmaceutical", "pharma", "formulary", "mhra",
    "nice", "cqc", "icb", "ics", "trust", "trusts", "ward", "theatre", "theatres",
    "wound", "vascular", "catheter", "stoma", "ostomy", "continence", "enteral",
    "infusion", "endoscopy", "oncology", "cardiology", "radiology", "orthopaedic",
    "orthopedic", "physiotherapy", "prosthetic", "ambulance", "care home", "care homes",
    "device", "devices", "implant", "implants", "biotech", "life sciences",
]

# (4) RELEVANCE — UK / NHS geography and institutions.
UK_TERMS = [
    "nhs", "uk", "u k", "united kingdom", "britain", "british", "england", "english",
    "scotland", "scottish", "wales", "welsh", "northern ireland", "nice", "mhra", "cqc",
    "icb", "nhs supply chain", "nhs england", "dhsc", "gbp", "london", "manchester",
    "birmingham", "leeds", "glasgow", "edinburgh", "cardiff", "belfast",
]

# (4) RELEVANCE — outlets whose masthead already establishes UK or clinical scope.
UK_OR_CLINICAL_OUTLETS = [
    "bbc", "the guardian", "the times", "telegraph", "sky news", "the independent",
    "financial times", "ft.com", "health service journal", "hsj", "nursing times",
    "nursing standard", "independent nurse", "british journal of nursing", "gp online",
    "pulse today", "the bmj", "bmj", "lancet", "pharmaceutical journal", "pharmatimes",
    "clinical services journal", "hospital healthcare", "national health executive",
    "building better healthcare", "digital health", "med-technews",
    "med-tech innovation", "health tech world", "journal of wound care",
    "journal of vascular access", "medical plastics news", "healthcare today",
    "hospital times", "open access government", "investors in healthcare",
]

# Publications whose masthead is itself a clinical or medical-device title. Used
# ONLY for rule (3), and ONLY behind a distinctive alias: a medical outlet writing
# about a same-named company in another sector must not inherit the sector test.
MED_TITLE_KEYWORDS = [
    "medical", "clinical", "medtech", "med-tech", "medicine", "hospital", "nursing",
    "nurse", "surgery", "surgical", "pharma", "device", "diagnostic", "therapy",
    "therapeutic", "healthcare", "health tech", "journal of", "bmj", "lancet",
    "biomed", "cardiolog", "oncolog", "radiolog", "wound", "vascular", "nhs",
    "orthopedic", "orthopaedic", "diabetes",
]


# Aliases that are real but must never be matched on their own: too generic, or
# a word that means something else outside this repo. A single token here is
# rejected even when it IS the whole canonical name.
NEVER_MATCH_ALONE = {
    "medical", "healthcare", "health", "surgical", "clinical", "care", "medic",
    "group", "holdings", "limited", "ltd", "plc", "uk", "solutions", "systems",
    "technologies", "products", "services", "international", "global", "supplies",
    "the", "and", "life", "prime", "apex", "summit", "vital", "pure", "core",
}

MIN_ALIAS_CHARS = 4          # a 3-character token is a homonym waiting to happen

_TOKEN = re.compile(r"[^a-z0-9]+")


def norm(s):
    """Lower-case, punctuation to single spaces. The one normalisation used everywhere."""
    return _TOKEN.sub(" ", str(s or "").lower()).strip()


def _is_domain(alias):
    return bool(re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", str(alias or "").strip().lower()))


def alias_universe(seed):
    """How many DISTINCT suppliers carry each single-token alias.

    Rule (2) needs to know whether one word belongs to one company or several.
    Built once from data/supplier-seed.json and passed in, so the writer and the
    gate answer the question from the same data.
    """
    counts = {}
    for s in (seed or {}).get("suppliers") or []:
        seen = set()
        for alias in ([s.get("name") or ""] + list(s.get("aliases") or [])):
            n = norm(alias)
            if n and len(n.split()) == 1:
                seen.add(n)
        for n in seen:
            counts[n] = counts.get(n, 0) + 1
    return counts


def scope_terms(supplier):
    """The supplier's OWN scope: its recorded specialities and product names.

    This is what a single-token alias has to be corroborated by. It is deliberately
    the supplier's own recorded data and nothing else — a generic health word will
    not do, because the homonym this rule exists to stop is itself a health company.
    """
    out = set()
    for spec in (supplier.get("specialities") or []):
        for part in re.split(r"[/,&+]|\band\b", str(spec or "")):
            n = norm(part)
            if not n:
                continue
            parts = n.split()
            if len(parts) == 1 and (n in NEVER_MATCH_ALONE or len(n) < 5):
                continue
            out.add(n)
    for prod in (supplier.get("products") or []):
        raw = prod.get("name") if isinstance(prod, dict) else prod
        parts = norm(raw).split()
        while parts and parts[0] in ("the", "a", "an"):
            parts = parts[1:]
        if len(parts) >= 2:
            out.add(" ".join(parts[:2]))
            if len(parts) >= 3:
                out.add(" ".join(parts[:3]))
    return {t for t in out if t and t not in NEVER_MATCH_ALONE}


def matchable_aliases(supplier, universe=None):
    """(strong, weak) alias lists after rule (2).

    strong — stands for the supplier on its own: two tokens or more, or a domain.
    weak   — one token, unique to this supplier across the seed, not a generic
             trade word. Only usable when the item also carries one of the
             supplier's own scope terms.

    Both are longest-first, so the strongest evidence is the one reported.
    """
    name = supplier.get("name") or ""
    strong, weak = set(), set()
    for alias in ([name] + list(supplier.get("aliases") or [])):
        raw = str(alias or "").strip()
        if not raw:
            continue
        if _is_domain(raw):
            strong.add(norm(raw))
            continue
        n = norm(raw)
        if not n or len(n) < MIN_ALIAS_CHARS:
            continue
        if len(n.split()) > 1:
            strong.add(n)
            continue
        if n in NEVER_MATCH_ALONE:
            continue
        if universe is not None and universe.get(n, 0) != 1:
            # Shared by more than one supplier record, so on its own it names
            # neither of them. Verification Standard §10: an ambiguous name is
            # published with the distinguishing detail, or not at all. This is
            # what stops a bare "Abbott" story being filed under one of the six
            # Abbott records the seed holds.
            continue
        if n == norm(name):
            # The company IS this one word — Coloplast, Convatec, Elekta. Then
            # the word stands for it, because there is no fuller name being
            # abbreviated away. This is exactly the case "Jeenie" is NOT:
            # the company is "Jeenie Solutions", so "Jeenie" is a shortening,
            # and a shortening is where the homonym gets in.
            strong.add(n)
        else:
            weak.add(n)
    key = lambda a: (-len(a), a)
    return sorted(strong, key=key), sorted(weak, key=key)


def _contains_phrase(hay_tokens, needle):
    """Whole word-token sequence containment. No substrings, ever.

    'jeenie' does not match inside 'jeenies'; 'gbuk' does not match inside
    'gbukgroup'. Token equality is the whole test.
    """
    n = needle.split()
    if not n:
        return False
    for i in range(len(hay_tokens) - len(n) + 1):
        if hay_tokens[i:i + len(n)] == n:
            return True
    return False


def _hit(text_tokens, terms):
    for t in terms:
        if _contains_phrase(text_tokens, norm(t)):
            return t
    return None


def item_text(item):
    """Everything about an item that the rule is allowed to read."""
    return " ".join(str(item.get(k) or "") for k in ("headline", "summary"))


def assess(supplier, item, publisher=None, universe=None):
    """Apply rules 1-4 to one item. Returns (ok, reason, evidence).

    `reason` names the FIRST rule that failed, so a rejection can be reported
    rather than disappearing. `evidence` is what gets written beside a published
    item so a reader — and the gate — can re-derive the decision.
    """
    text = item_text(item)
    toks = norm(text).split()
    if not toks:
        return False, "the item carries no text to test", {}

    strong, weak = matchable_aliases(supplier, universe)

    alias = strength = scope = None
    for cand in strong:
        if _contains_phrase(toks, cand):
            alias, strength = cand, "distinctive"
            break
    if not alias:
        terms = sorted(scope_terms(supplier), key=lambda a: (-len(a), a))
        for cand in weak:
            if not _contains_phrase(toks, cand):
                continue
            for term in terms:
                if _contains_phrase(toks, term):
                    alias, strength, scope = cand, "single-token+own-scope", term
                    break
            if alias:
                break
    if not alias:
        return False, ("rule 1/2 ALIAS: no distinctive recorded alias of %r appears in the item "
                       "as a whole word sequence, and no single-token alias of it is corroborated "
                       "by one of this supplier's own specialities or products"
                       % supplier.get("name")), {}

    sector = _hit(toks, SECTOR_TERMS)
    if not sector and scope:
        # The supplier's own recorded speciality or product name IS a clinical
        # term, and a more specific one than anything in SECTOR_TERMS. An item
        # naming it has already cleared this floor.
        sector = scope
    if not sector:
        for term in sorted(scope_terms(supplier), key=lambda a: (-len(a), a)):
            if _contains_phrase(toks, term):
                sector = term
                break
    if not sector and strength == "distinctive":
        # A clinical or medical-device title reporting a company it has already
        # identified unambiguously has established the sector itself. This is
        # allowed ONLY behind a distinctive alias: a medical outlet writing about
        # a same-named company in another sector must not inherit the test, which
        # is the exact shape of the Jeenie hazard.
        p = (publisher or item.get("publisher") or "").lower()
        for kw in MED_TITLE_KEYWORDS:
            if kw in p:
                sector = "publisher: %s" % (publisher or item.get("publisher"))
                break
    if not sector:
        return False, ("rule 3 SECTOR: the item carries no medical, clinical or NHS-sector term, "
                       "none of this supplier's own specialities or products, and is not carried "
                       "by a clinical or medical-device title"), {}

    relevance = _hit(toks, UK_TERMS)
    if not relevance:
        for spec in (supplier.get("specialities") or []):
            s = norm(spec)
            if s and _contains_phrase(toks, s):
                relevance = spec
                break
    if not relevance:
        p = (publisher or item.get("publisher") or "").lower()
        for outlet in UK_OR_CLINICAL_OUTLETS:
            if outlet in p:
                relevance = "publisher: %s" % outlet
                break
    if not relevance:
        return False, ("rule 4 RELEVANCE: the item carries no UK or NHS geography, none of this "
                       "supplier's own specialities, and is not carried by a UK or clinical "
                       "outlet"), {}

    ev = {"alias": alias, "aliasStrength": strength,
          "sectorTerm": sector, "relevanceTerm": relevance}
    if scope:
        ev["scopeTerm"] = scope
    return True, "", ev


def identify(supplier, item, universe=None):
    """Rules 1 and 2 alone: does this item name THIS supplier?

    Separated out because identity is a property of each item, while sector and
    relevance are properties of the story. Returns the matched alias or None.
    """
    toks = norm(item_text(item)).split()
    if not toks:
        return None
    strong, weak = matchable_aliases(supplier, universe)
    for cand in strong:
        if _contains_phrase(toks, cand):
            return cand
    terms = sorted(scope_terms(supplier), key=lambda a: (-len(a), a))
    for cand in weak:
        if not _contains_phrase(toks, cand):
            continue
        for term in terms:
            if _contains_phrase(toks, term):
                return cand
    return None


# ---------------------------------------------------------------------------
# MATCH ALIASES FOR THE LIVE DESK CARVE-OUT (27/08/2026)
# ---------------------------------------------------------------------------
# The pipeline's rank.py decides whether a headline names a verified Hub
# supplier. It built its pattern from the KEYS of company-press.json — canonical
# names only — and never looked at aliases at all. So "Fifth Baxter particulate
# recall since July in the US" did not match "Baxter Healthcare Ltd", scored 5
# instead of 11, and fell off the Industry Wire the moment two other supplier
# stories were correctly boosted. Its own comment read "Longest first so 'Baxter
# Healthcare Ltd' wins over 'Baxter'", so the short form was expected to be
# there. It never was.
#
# These functions publish the aliases that are SAFE to match on, so the consumer
# never has to guess and can never widen the rule on its own.
#
# WHY TWO LISTS. 316 single-token aliases are >= 4 characters, and 29 of them are
# also ordinary English words — amity, bard, cook, flow, merit, nestle, span,
# ultimate ... and baxter. A dictionary denylist is therefore useless here: it
# would drop the exact case this was written to fix.
#
# Capitalisation is what actually separates them. "Fifth Baxter particulate
# recall" is the company; "trusts cook meals" is not. So a single-token alias is
# published for CASE-SENSITIVE matching only, in the casing its own supplier's
# canonical name uses, and only when the token genuinely appears in that name —
# so the capitalisation is evidence from the seed, never invented here.
#
# Multi-token aliases are specific enough on their own and stay case-insensitive.
#
# EVERY GATE MUST HOLD. Unambiguous across the whole seed (alias_universe), at
# least MIN_MATCH_ALIAS characters, and present in the canonical name. A name
# that fails any gate is simply not published — the consumer then behaves exactly
# as it did before, which is the same evidence floor the carve-out itself uses.
MIN_MATCH_ALIAS = 4


def _cased_token(token, name):
    """The token as `name` capitalises it, or None if `name` does not contain it.

    Evidence, not invention: the casing comes from the seed's own canonical name.
    """
    for word in re.findall(r"[\w&'-]+", name or ""):
        if norm(word) == token:
            return word
    return None


def match_aliases(supplier, universe):
    """{"caseInsensitive": [...], "caseSensitive": [...]} for one supplier.

    caseSensitive entries are single words that are only safely a company name
    when capitalised. caseInsensitive entries are two words or more.
    """
    name = supplier.get("name") or ""
    insensitive, sensitive = [], []
    for alias in ([name] + list(supplier.get("aliases") or [])):
        n = norm(alias)
        if not n or len(n) < MIN_MATCH_ALIAS:
            continue
        if len(n.split()) > 1:
            if alias.strip() and alias.strip() not in insensitive:
                insensitive.append(alias.strip())
            continue
        if universe.get(n, 0) != 1:      # the same word on two suppliers proves nothing
            continue
        cased = _cased_token(n, name)
        if cased and cased not in sensitive:
            sensitive.append(cased)
    return {"caseInsensitive": insensitive, "caseSensitive": sensitive}
