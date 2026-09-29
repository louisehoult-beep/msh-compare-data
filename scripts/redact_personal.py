#!/usr/bin/env python3
"""Strip named individuals' contact details before anything lands in data/.

This repo is PUBLIC: every file under data/ is fetched straight into members'
browsers from raw GitHub, so whatever is in it is world-readable. On 29/09/2026
an independent review found 92 distinct person-shaped work emails (NHS
procurement staff, NHS Supply Chain category managers, tender contacts, one
supplier employee) plus direct phone numbers across eleven data files. They had
been copied in verbatim from tender descriptions, ICC support-document text,
supplier website snippets and hand-written trust profiles. Lou's rule the same
day: no personal data in the public repo.

What counts as personal here (the rule, so a reader does not have to infer it):

  * PERSON-SHAPED EMAIL — the local part looks like a person: first.last,
    f.last, first-last, or a single first name (gareth@, les@, tlarkin@), at
    ANY domain. These are removed wherever they appear, field or free text.
  * GENERIC / ROLE ADDRESS — procurement@, supplies@, info@, sales@,
    NEY.Maintenance@, cuh.procurement@, ccsinbox@ … These name a function,
    not a person, and stay. The test is whether any token of the local part
    is a role/team word (ROLE_WORDS below).
  * PHONE ATTACHED TO A PERSON — a phone number that sits right after a
    person's email, or anywhere in a trust profile `people[].note` (every note
    there is about one named person, so every phone in one is that person's
    line). Departmental helpdesk numbers in `structure` prose stay.

Names alone (a Head of Procurement named on the trust's own page, an NHS
Supply Chain category manager named in a public ICC document, a Companies
House officer) are NOT touched by this module — they are public-record facts
the Hub's features are built on. This module removes the ways to reach the
person, not the fact that they hold the role.

Two entry points, and one gate:

  redact_text(text, strip_all_phones=False)   free text → redacted text
  redact_obj(obj)                              walk a JSON structure in place
  find_person_emails(text)                     what verify.py fails on

Replacement wording is deliberately visible ("[contact details withheld]")
rather than silent deletion: a member reading "Site visits should be arranged
with [contact details withheld]" knows there IS a named route and goes to the
notice for it, instead of thinking the sentence was always vague.
"""
from __future__ import annotations

import re

# An email, tolerating one PDF-wrap space inside a short domain prefix
# ("keith.johnson@s upplychain.nhs.uk" appears verbatim in ICC text). The
# optional gap is only allowed when the piece before the space is <=3 chars,
# so "john@x.com www.site.com" is never swallowed as one address. The leading
# lookbehind stops a match starting on the "n" of a JSON "\\n" escape when a
# file is redacted as raw text ("\\nLuca.ghirlanda@…" must match from the L).
EMAIL_RE = re.compile(
    r"(?<!\\)[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]{1,3} )?[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

# UK phone shapes: 07xxx xxxxxx, 01722 336262, 0208 296 4692, 03033 305267,
# +44 20 ..., optionally followed by "ext 5755". Deliberately anchored on a
# leading 0 / +44 so product codes and tender refs (P01491 499573) do not match.
PHONE_RE = re.compile(
    r"(?<![\dA-Za-z-])(?:\+44\s?\(?0?\)?\s?\d{2,4}|\(?0\d{2,4}\)?)"
    r"[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?:\s?(?:ext|extension|x)\.?\s?\d{1,5})?(?![\d])",
    re.I,
)

# A phone that follows a person's email within a few characters is that
# person's direct line ("ann.hamed@cht.nhs.uk, 07584538719").
_TRAILING_PHONE_RE = re.compile(
    r"\[email withheld\](?P<sep>[,;:/ ]{0,4}(?:tel(?:ephone)?\.?:?\s*|phone:?\s*|on\s+)?)"
    r"(?P<phone>" + PHONE_RE.pattern + r")",
    re.I,
)

# Not an email at all: image filenames like Carry-Case@700x-100.jpg.
_NOT_EMAIL_TLDS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "avif"}

# Any of these inside the local part means a function, team or mailbox rather
# than a person. ROLE_STEMS match as substrings of the lowercased local part,
# so "cuh.procurement", "ccsinbox", "customerserviceuk", "NEY.Maintenance" and
# "coch.clinicalprocurementspecialistnurse" all read as generic. ROLE_TOKENS
# are short words that only count when they are a whole token (split on . - _),
# because as substrings they sit inside ordinary names ("hr" in christine,
# "it" in smith, "eu" in eugene).
ROLE_STEMS = (
    "procure", "proc", "purchas", "suppl", "tender", "contract", "sourcing",
    "commercial", "info", "sales", "enquir", "contact", "hello", "support",
    "help", "service", "customer", "order", "admin", "office", "team", "dept",
    "department", "group", "desk", "inbox", "mail", "noreply", "webmaster",
    "marketing", "export", "accounts", "reception", "general", "quote",
    "maintenance", "governance", "prescrib", "medicine", "pharmac", "clinical",
    "nursing", "category", "buyer", "recall", "fieldaction", "quality",
    "regulatory", "compliance", "privacy", "protection", "career", "recruit",
    "charity", "grant", "finance", "payable", "invoice", "billing", "training",
    "education", "welcome", "distribution", "logistic", "warehouse", "trial",
    "research", "cheata", "infusion", "interop", "veterinary", "international",
    "england", "scotland", "midlands", "australia", "denmark", "mexico",
    "turkey", "germany", "france", "kontakt", "bestellung", "online", "shop",
    "store", "returns", "complaint", "feedback", "newsletter", "customercare",
    "emea", "apac", "europe", "global", "corporate",
    "otection",  # "otection@tristel.com": a crawl-truncated dataprotection@ mailbox, not a person
)
ROLE_TOKENS = frozenset((
    "hr", "it", "uk", "usa", "eu", "ops", "vet", "web", "ips", "hub", "data",
    "acute", "care", "north", "south", "east", "west", "london", "wales",
    "ireland", "spain", "italy", "nordic", "asia", "china", "people", "study",
    "action", "legal", "unit", "press", "media", "job", "jobs", "corp", "tr",
    "nhs", "ics", "icb", "ccg", "trust", "team", "office",
))


def _local_tokens(local: str) -> list[str]:
    return [t for t in re.split(r"[._\-+]", local.lower()) if t]


def is_person_email(addr: str) -> bool:
    """True when the local part looks like an individual rather than a role."""
    addr = addr.replace(" ", "")
    if "@" not in addr:
        return False
    local, _, domain = addr.rpartition("@")
    tld = domain.rsplit(".", 1)[-1].lower()
    if tld in _NOT_EMAIL_TLDS:
        return False
    if domain.lower().endswith("example.invalid") or domain.lower().endswith("example.com"):
        return False  # synthetic fixture people, never real
    lo = local.lower()
    if any(w in lo for w in ROLE_STEMS):
        return False
    toks = _local_tokens(local)
    if not toks or any(t in ROLE_TOKENS for t in toks):
        return False
    # Trailing digits are common on nhs.net (lisa.jones125, warren.peacock1).
    core = [re.sub(r"\d+$", "", t) for t in toks]
    if any(not t.isalpha() for t in core):
        return False
    if len(core) >= 2:
        # first.last / f.last / first.middle.last — every token alphabetic
        return all(len(t) >= 1 for t in core) and any(len(t) >= 2 for t in core)
    # single token: a bare first name or initial+surname (gareth, les, tlarkin,
    # jakepatching, paula). Needs a vowel and at least three letters so that
    # opaque mailbox codes (prcgm) are not mistaken for a person.
    t = core[0]
    return len(t) >= 3 and bool(re.search(r"[aeiouy]", t))


def find_person_emails(text: str) -> list[str]:
    """Distinct person-shaped addresses in `text`, original spelling, sorted."""
    found = set()
    for m in EMAIL_RE.finditer(text):
        a = m.group(0)
        if is_person_email(a):
            found.add(a.replace(" ", ""))
    return sorted(found, key=str.lower)


def _tidy(text: str) -> str:
    # "[email withheld], [phone withheld]" reads better as one marker.
    text = re.sub(
        r"\[email withheld\](?:[,;/ ]{0,3}(?:and\s+)?\[phone withheld\])+",
        "[contact details withheld]", text)
    # "cced to [email withheld]" after another withheld marker collapses.
    text = re.sub(
        r"\[contact details withheld\](?:\s*(?:,|and|cced to|cc'd to|cc to|copied to)?\s*\[(?:email|contact details) withheld\])+",
        "[contact details withheld]", text)
    return text


def redact_text(text, strip_all_phones: bool = False):
    """Remove person-shaped emails (and the phone that follows one). With
    strip_all_phones, every phone number goes too — use for text that is
    about one named person, such as a trust profile people[].note."""
    if not isinstance(text, str) or "@" not in text and not strip_all_phones:
        return text

    def _sub(m):
        return "[email withheld]" if is_person_email(m.group(0)) else m.group(0)

    out = EMAIL_RE.sub(_sub, text)
    out = _TRAILING_PHONE_RE.sub(lambda m: "[email withheld], [phone withheld]", out)
    if strip_all_phones:
        out = PHONE_RE.sub("[phone withheld]", out)
    return _tidy(out) if "[" in out else out


def redact_obj(obj, *, _key=None, _in_people_note=False):
    """Walk a JSON structure and redact every string in place (lists/dicts are
    mutated; the redacted object is also returned). Strings under a
    `people[].note` key have every phone stripped as well."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = redact_obj(v, _key=k, _in_people_note=_in_people_note)
        return obj
    if isinstance(obj, list):
        # A list under "people" holds one dict per named person: their note is
        # about them, so a phone inside it is theirs.
        child_people = (_key == "people")
        for i, v in enumerate(obj):
            obj[i] = redact_obj(v, _key=None, _in_people_note=_in_people_note or child_people)
        return obj
    if isinstance(obj, str):
        return redact_text(obj, strip_all_phones=(_in_people_note and _key == "note"))
    return obj


def redact_file_text(raw: str) -> str:
    """Redact a JSON file as text, preserving its exact formatting. Safe
    because an email or phone never contains a quote, backslash or newline,
    so replacing it inside a JSON string literal leaves the document valid."""
    return redact_text(raw)


if __name__ == "__main__":  # quick manual check: python3 scripts/redact_personal.py < file
    import sys
    sys.stdout.write(redact_text(sys.stdin.read()))
