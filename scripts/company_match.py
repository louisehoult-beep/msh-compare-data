#!/usr/bin/env python3
"""Resolve a legal entity name from an award notice to ONE Hub supplier record.

WHY THIS IS A SEPARATE MODULE
-----------------------------
Award notices name legal entities — "HILL-ROM LIMITED", "PHILIPS ELECTRONICS
UK LIMITED", "SMITH & NEPHEW UK LIMITED". The supplier seed holds trading
names — "Hill-Rom", "Philips Healthcare", "Smith+Nephew". Attaching an award
to the wrong one of those publishes a false statement about a named company
under the Hub's name, which is the 24/07/2026 class of error with different
words in it.

So the resolution rule lives in one file, is imported by BOTH the writer
(scripts/refresh_awards.py) and the gate (verify.py), and the gate re-derives
every published match independently. The two can then only disagree because of
a bug, and the gate is what notices — the same technique notice_tags.py and
check_tags() already use for the contact index.

THE RULE, IN FULL — and it is deliberately narrow
-------------------------------------------------
A name resolves only when its normalised form matches, EXACTLY, the normalised
form of a seed company's own name or one of its recorded aliases.

Normalisation, and nothing more than this:
  * lower case; "&" becomes "and"; punctuation becomes a space; whitespace
    collapsed;
  * trailing legal suffixes stripped (Ltd, Limited, plc, LLP, Inc, GmbH, BV,
    A/S, AB, Oy, Pty …);
  * trailing territory words stripped (UK, GB, England, Ireland, Europe, EMEA).

There is NO fuzzy matching, no substring matching, no edit distance and no
initial matching, on purpose. Those are how homonyms merge. The stripping is
shallow for the same reason: "healthcare", "medical", "group", "holdings" and
"international" are NOT stripped, because removing them starts matching
genuinely different companies to each other — "Prism Healthcare" and "Prism
Medical" are two different businesses.

This is the same rule, written the same way, as the Hub's company alias
registry (Hub/company-aliases/company_alias.py). It is reimplemented here
rather than imported because that file sits outside this repository, and this
repository is served to the Hub on its own; a cross-repo import would work on
the laptop and fail in CI.

THREE OUTCOMES, AND ONLY THREE
------------------------------
  confirmed  exactly one seed company matched. Publishable.
  ambiguous  two or more DIFFERENT seed companies matched the same name.
             Quarantined — a name that means two companies proves neither.
  unmatched  nothing matched. Quarantined.

Quarantined is not a near-miss to be nudged over the line later by loosening
the rule. It is a question for a human, who settles it by adding the alias to
the company's own seed record — where the nightly index rebuild will keep it,
and where every other part of the Hub gets the benefit too.
"""

import re

# Stripped from the END of a name when matching. Deliberately shallow — see the
# module docstring. Kept in step with Hub/company-aliases/company_alias.py.
LEGAL_SUFFIX = (
    "limited|ltd|plc|p l c|llp|llc|inc|incorporated|corp|corporation|co|"
    "gmbh|a s|as|ab|bv b v|bv|nv n v|nv|sa s a|sa|ag|spa s p a|spa|oy|"
    "pty|pte|srl|sarl|kk"
)
TERRITORY = "uk|u k|gb|great britain|united kingdom|england|ireland|europe|emea"

# The rule, in the words it is published in. Written into the data file so a
# reader can judge a match without reading this source (root rule 14).
RULE = (
    "A supplier named on an award notice is attached to a Hub company only where "
    "the notice's name, normalised, is EXACTLY a normalised form of that company's "
    "own name or one of its recorded aliases. Normalisation lower-cases, turns & "
    "into and, drops punctuation, and strips trailing legal-form words (Ltd, "
    "Limited, plc, LLP, Inc, GmbH, BV, A/S, AB, Oy, Pty) and trailing territory "
    "words (UK, GB, England, Ireland, Europe, EMEA). Nothing else is stripped and "
    "there is no fuzzy, substring or edit-distance matching. A name matching two "
    "different companies, or none, is quarantined unpublished — it is a question "
    "for a human, never a best guess."
)


def norm(s):
    """Lower case, & -> and, punctuation to space, whitespace collapsed."""
    s = str(s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def key(s):
    """norm() with trailing legal-form and territory words removed.

    Applied repeatedly because real names stack them: "SMITH & NEPHEW UK
    LIMITED" is territory then suffix, "PHILIPS ELECTRONICS UK LTD" the same,
    and "COLOPLAST LIMITED UK" the other way round.
    """
    n = norm(s)
    prev = None
    while prev != n:
        prev = n
        n = re.sub(r"\s+(%s)$" % LEGAL_SUFFIX, "", n).strip()
        n = re.sub(r"\s+(%s)$" % TERRITORY, "", n).strip()
    return n


def build_index(seed):
    """{normalised key: set of seed company names} from a supplier-seed doc.

    A key that reaches more than one company is kept AS a set rather than being
    resolved to the first one seen. Silently taking the first is how a homonym
    becomes a published fact, and dictionary order is not evidence.
    """
    index = {}
    for company in (seed or {}).get("suppliers", []) or []:
        name = company.get("name")
        if not name:
            continue
        for candidate in [name] + list(company.get("aliases") or []):
            k = key(candidate)
            if not k:
                continue
            index.setdefault(k, set()).add(name)
    return index


def resolve(name, index):
    """(company_or_None, state, reason) for one incoming supplier name.

    state is one of "confirmed", "ambiguous", "unmatched". The reason is
    written into the published file verbatim, so it is phrased for a reader,
    not for a log.
    """
    k = key(name)
    if not k:
        return None, "unmatched", "the notice records no supplier name"
    hits = index.get(k)
    if not hits:
        return None, "unmatched", (
            "no Hub company's name or recorded alias normalises to \"%s\". Add the "
            "alias to that company's record in data/supplier-seed.json to attach "
            "this award." % k)
    if len(hits) > 1:
        return None, "ambiguous", (
            "\"%s\" normalises to a name held by %d different Hub companies (%s), so "
            "it identifies none of them." % (k, len(hits), ", ".join(sorted(hits))))
    company = next(iter(hits))
    return company, "confirmed", (
        "the notice names \"%s\", which normalises to \"%s\" — exactly the normalised "
        "form of this company's own name or a recorded alias." % (name, k))
