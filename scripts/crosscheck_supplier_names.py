#!/usr/bin/env python3
"""Read each candidate site's OWN legal name, and cross-check it three ways.

WHY THIS EXISTS (added 14/08/2026)
----------------------------------
verify_name_proofs.py second-sourced 4 of the 128 title-match domains and
refused the rest. Refused is not the same as wrong: Novo Nordisk, QIAGEN and
Thermo Fisher are almost certainly on the domain we guessed, they just never
publish a UK registration number on it. The refusals were correct but blunt.

This asks a different and better question. Instead of "does the site publish a
number", it asks "WHAT COMPANY DOES THIS SITE SAY IT IS", then compares that to
the three names we already hold for the supplier:

  SEED NAME        the trading name on the Hub, e.g. "Pentax Medical"
  REGISTERED NAME  Companies House, e.g. "PENTAX MEDICAL UK LIMITED"
  FRAMEWORK NAME   as NHS Supply Chain published it on the award notice

WHY THE FULL NAME WORKS WHERE core() FAILED. The seeding script matched on the
stripped core, so "Pentax Medical" became "pentax" and matched a camera shop;
"Richard Wolf" became "richardwolf" and matched a composer. A full registered
name is many words long and specific to one company — a camera shop's site does
not contain the string "Pentax Medical UK Limited". The homonyms that slipped
through the core test cannot survive the full-name test.

WHAT THIS PROVES, AND WHAT IT DOES NOT. A site publishing its own registered
legal name, next to legal wording, is real corroboration of ownership from a
second source. It is still weaker than a registration NUMBER, because a name can
be shared across group companies and jurisdictions. So this writes nothing to
the seed. It produces a review list, with the evidence quoted, split into:

  CONFIRMED        the site names the registered, seed or framework company
  CONFIRMED_GROUP  it names a company sharing two or more words with one of them
                   — same group, different legal entity (Air Liquide Healthcare
                   Ltd / "Air Liquide UK Ltd")
  REVIEW           it names a company sharing fewer than two words with any of
                   them. Either the domain is wrong, or it is a group company
                   under an unrelated name (Laborie / "Medical Measurement
                   Systems BV"). Only industry knowledge separates those two.
  SILENT           it names no legal entity anywhere it was read

TWO shared words, not one, is what makes CONFIRMED_GROUP safe. Every genuinely
wrong domain found on 14/08/2026 shared exactly one generic word with the site's
real owner — Hamilton Medical UK / Hamilton Rentals, Inspire Medical Systems /
Inspire Group Investments, Critical Healthcare / Critical Research, Peacocks
Medical Group / Peacocks Stores. A one-word rule would have confirmed all four.

REVIEW is the valuable output. It is the only tier that positively identifies a
suspect domain rather than merely failing to confirm a good one. It is
deliberately NOT auto-resolved: see the four above, where the only thing
separating a wrong domain from a group company is knowing the industry.

CAVEAT CARRIED DELIBERATELY. company-financials.json records matchConfidence
"probable" and matchedOn "name search on Companies House — NOT verified against
a recorded number" for many suppliers. The registered name is therefore itself a
name-match and can be the wrong company. It is used here as one of three
cross-checks, never alone, and its confidence is printed beside every verdict.

USAGE
  python3 scripts/crosscheck_supplier_names.py            # all 128 candidates
  python3 scripts/crosscheck_supplier_names.py --all      # every seed supplier with a domain

Writes state/supplier-name-crosscheck.json. Never touches the seed.
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys

sys.path.insert(0, "scripts")
import seed_supplier_domains as S

VERIFIED = "state/name-proof-verification.json"
FIN = "data/company-financials.json"
FW = "data/frameworks.json"
SEED = "data/supplier-seed.json"
OUT = "state/supplier-name-crosscheck.json"
OUT_ALL = "state/supplier-name-crosscheck-all.json"

# Bare "AS" (Norwegian) is deliberately EXCLUDED: it matched the ordinary phrase
# "AS WELL AS" and reported it as RB Medical Engineering's legal name. A suffix
# that is also a common English word is not worth the entities it finds.
LEGAL_SUFFIX = r"(?:Limited|Ltd\.?|PLC|P\.L\.C\.|LLP|LLC|Inc\.?|GmbH|A/S|AB|BV|B\.V\.|NV|S\.A\.|AG|SpA|Oy)"

# Connectives are allowed INSIDE a name ("Smith and Nephew", "Bank of England")
# but never as the first word, which is how "of Oxford BioSystems Ltd" and
# "Terms and Conditions of Sale QIAGEN LLC" leaked into the first run.
CONNECT = r"(?:of|and|the|for|de|von|van|&)"
WORD = r"[A-Z][\w&'’\-\.]*"

ENTITY = re.compile(
    r"\b(%s(?:[ \t]+(?:%s|%s)){0,5}[ \t]+%s)\b" % (WORD, WORD, CONNECT, LEGAL_SUFFIX))

# Capitalised words that start a sentence far more often than a company name.
# Without these, boilerplate like "These Terms ... Ltd" becomes an entity.
NOT_A_NAME_START = {
    "terms", "conditions", "these", "this", "our", "your", "the", "all", "any",
    "please", "copyright", "registered", "company", "we", "you", "it", "if",
    "where", "when", "such", "well", "as", "in", "on", "at", "by", "from",
    "with", "under", "about", "contact", "home", "privacy", "cookie", "policy",
    "website", "site", "page", "read", "more", "learn", "view", "click",
}

# Anchored to the END of the name. Unanchored, this stripped the "AB" from
# "AB SCIENTIFIC LTD" and left "scientific", which then shared only one word
# with the site's own "AB Scientific Ltd" and reported an exact match as a
# contradiction. A suffix is only a suffix in the suffix position.
SUFFIX_RE = re.compile(
    r"[\s,\.]+(limited|ltd|plc|llp|llc|inc|corp|corporation|gmbh|a/s|ab|bv|nv|sa|ag|spa|oy|as)\b\.?\s*$")


def same_company(a, b):
    """True if two company names denote the same company or its group.

    Equality and containment FIRST. A word-overlap test alone cannot handle a
    one-word name — CliniMed Limited and CLINIMED LIMITED share exactly one
    word, and so does Hamilton Medical and Hamilton Rentals. Only the overlap
    test needs the two-word floor; an exact or containing match never did.
    """
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return False
    if ka == kb or ka in kb or kb in ka:
        return True
    # Spacing is not a contradiction: "C J MEDICAL LIMITED" is Companies House's
    # rendering of the site's "CJ Medical Ltd".
    ja, jb = ka.replace(" ", ""), kb.replace(" ", "")
    if ja == jb or ja in jb or jb in ja:
        return True
    return len(set(ka.split()) & set(kb.split())) >= 2


def key(s):
    """Comparable form of a company name: lowercase alnum words, suffix dropped."""
    t = re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower())
    t = SUFFIX_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def entities(pages):
    """Every legal entity name the site publishes, most frequent first."""
    seen = {}
    for url, html in pages:
        if not html:
            continue
        body = S.text_of(html)
        for m in ENTITY.finditer(body):
            name = re.sub(r"\s+", " ", m.group(1)).strip()
            # Trim boilerplate that ran into the front of the name.
            parts = name.split()
            while len(parts) > 2 and parts[0].lower().strip(".,") in NOT_A_NAME_START:
                parts.pop(0)
            name = " ".join(parts)
            k = key(name)
            if not k or len(k) < 4 or k.split()[0] in NOT_A_NAME_START:
                continue
            rec = seen.setdefault(k, {"name": name, "n": 0, "url": url, "quote": None})
            rec["n"] += 1
            if rec["quote"] is None:
                w = body[max(0, m.start() - 90):m.end() + 90]
                rec["quote"] = re.sub(r"\s+", " ", w).strip()[:200]
    return sorted(seen.values(), key=lambda r: -r["n"])


def check(job):
    rec, fin, fwnames = job
    name = rec["name"]
    domain = rec.get("domain")
    reg = (fin or {}).get("registeredName")
    conf = (fin or {}).get("matchConfidence")

    out = {"name": name, "domain": domain, "registeredName": reg,
           "registeredNameConfidence": conf, "frameworkNames": fwnames,
           "checked": dt.date.today().isoformat()}

    base = "https://" + re.sub(r"^https?://", "", domain or "").split("/")[0]
    final, html = S.fetch(base)
    if not html:
        out.update(verdict="UNREACHABLE", reason="site did not answer")
        return out

    pages = [(final, html)]
    m = re.match(r"(https?://[^/]+)", final or "")
    if m:
        for p in ("/contact", "/contact-us", "/privacy-policy", "/terms", "/legal",
                  "/about-us", "/imprint", "/terms-and-conditions", "/cookie-policy"):
            u, h = S.fetch(m.group(1) + p)
            if h:
                pages.append((u, h))

    found = entities(pages)
    out["siteEntities"] = [{"name": e["name"], "seen": e["n"], "quote": e["quote"]}
                           for e in found[:6]]

    # The names that would confirm this domain, from every source we hold.
    wanted = {key(x): x for x in ([reg, name] + list(fwnames)) if x}
    wanted.pop("", None)

    # Pass 1 — the site publishes a name we hold, whole or containing it.
    for e in found:
        for wk, wname in wanted.items():
            ke = e_k(e)
            if len(wk) >= 6 and (wk == ke or wk in ke or ke in wk):
                out.update(verdict="CONFIRMED", matched=wname,
                           siteSays=e["name"], evidence=e["quote"], url=e["url"])
                return out

    # Pass 2 — a group company. "Air Liquide Healthcare Ltd" is not a substring of
    # "Air Liquide UK Ltd", and "Allard Support UK Limited" is not a substring of
    # "Allard Support for Better Life AB", but both are plainly the same business.
    #
    # TWO shared words, not one. One is what lets a homonym through, and the four
    # genuinely wrong domains found on 14/08/2026 all share exactly one generic
    # word with the site's real owner: Hamilton Medical UK / Hamilton Rentals,
    # Inspire Medical Systems / Inspire Group Investments, Critical Healthcare /
    # Critical Research, Peacocks Medical Group / Peacocks Stores. Requiring a
    # second shared word refuses all four and still accepts the real groups.
    for e in found:
        et = set(e_k(e).split())
        for wk, wname in wanted.items():
            shared = et & set(wk.split())
            if len(shared) >= 2:
                out.update(verdict="CONFIRMED_GROUP", matched=wname,
                           siteSays=e["name"], sharedWords=sorted(shared),
                           evidence=e["quote"], url=e["url"],
                           reason="site names a company sharing %d words with this "
                                  "supplier — same group, different legal entity"
                                  % len(shared))
                return out

    if found:
        out.update(verdict="REVIEW",
                   siteSays=found[0]["name"], evidence=found[0]["quote"],
                   url=found[0]["url"],
                   siteEntitiesAll=[e["name"] for e in found],
                   reason="site publishes a legal entity that shares fewer than two "
                          "words with any name on record. EITHER the domain belongs to "
                          "a different company, OR it is a group company named "
                          "differently. Only industry knowledge separates the two — "
                          "judge it by eye, do not auto-accept.")
    else:
        out.update(verdict="SILENT",
                   reason="site names no legal entity on any page read")
    return out


def e_k(e):
    return key(e["name"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="check every seed supplier that has a domain, not just the 128")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    fin = json.load(open(FIN, encoding="utf-8"))["companies"]
    fwdata = json.load(open(FW, encoding="utf-8"))

    # Framework names, grouped by stripped core so a supplier finds its own variants.
    bycore = {}
    for f in fwdata["frameworks"]:
        for s in f["suppliers"]:
            bycore.setdefault(S.core(s), set()).add(s)

    def job(name, domain):
        return ({"name": name, "domain": domain}, fin.get(name),
                sorted(bycore.get(S.core(name), [])))

    todo, mode = [], "the 128 title-match candidates"
    if a.all:
        # EVERY supplier carrying a domain, wherever that domain came from —
        # curated links, a Clearbit logo URL, an old import. Those were never
        # put through any proof at all; the 128 at least had a title match.
        # This is also the only pass that touches the 283 suppliers whose
        # Companies House record is a "probable" name match: comparing the
        # site's own legal entity to the registered name is what tests it.
        seed = json.load(open(SEED, encoding="utf-8"))["suppliers"]
        for s in seed:
            d = S.domain_for(s)
            if d:
                todo.append(job(s["name"], d))
        mode = "every seed supplier with a domain on record"
    else:
        for r in json.load(open(VERIFIED, encoding="utf-8"))["results"]:
            if r["verdict"] == "VERIFIED" or not r.get("domain"):
                continue                 # already proved by registration number
            todo.append(job(r["name"], r["domain"]))
    print("mode: %s" % mode)

    print("cross-checking %d candidate domains against seed / Companies House / "
          "framework names\n" % len(todo))

    res = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(check, todo), 1):
            res.append(r)
            tag = {"CONFIRMED": "OK  ", "CONFIRMED_GROUP": "OK~ ",
                   "REVIEW": "EYES", "SILENT": "  ? ",
                   "UNREACHABLE": "  - "}.get(r["verdict"], "    ")
            detail = r.get("siteSays") or r.get("reason", "")
            print("%s %3d/%d  %-34s %-30s %s" % (
                tag, i, len(todo), r["name"][:34], (r["domain"] or "")[:30], detail[:46]))

    # THE COMPANIES HOUSE CROSS-CHECK, which comes free with this sweep.
    # 283 suppliers carry matchConfidence "probable" — a Companies House NAME
    # search that was never verified against a recorded number. Where the site
    # is confirmed as the right company but its own legal entity shares fewer
    # than two words with the registered name we hold, that registered name
    # (and the company number, turnover and officers attached to it) is
    # probably the WRONG COMPANY. Air Liquide Healthcare Ltd is recorded as
    # TANDEM DIABETES UK LIMITED.
    suspect = []
    for r in res:
        if r["verdict"] not in ("CONFIRMED", "CONFIRMED_GROUP"):
            continue
        reg, says = r.get("registeredName"), r.get("siteSays")
        if not reg or not says:
            continue
        if not same_company(reg, says):
            suspect.append({"name": r["name"], "domain": r["domain"],
                            "registeredName": reg,
                            "confidence": r.get("registeredNameConfidence"),
                            "siteSays": says})
    if suspect:
        print("\n%d Companies House record(s) contradicted by the supplier's own site:"
              % len(suspect))
        for x in suspect[:40]:
            print("   %-30s CH: %-34s site: %s (%s)" % (
                x["name"][:30], (x["registeredName"] or "")[:34], x["siteSays"],
                x["confidence"]))

    order = ("CONFIRMED", "CONFIRMED_GROUP", "REVIEW", "SILENT", "UNREACHABLE")
    c = {v: sum(1 for r in res if r["verdict"] == v) for v in order}
    print("\n" + "   ".join("%s %d" % (v, c[v]) for v in order))

    json.dump({"_notice": "Cross-check of candidate supplier domains against the "
                          "supplier's seed name, Companies House registered name and "
                          "NHS framework award names. CONFIRMED = the site publishes a "
                          "name we hold. MISMATCH = it publishes a different company. "
                          "Review only — nothing here is written to the seed.",
               "generated": dt.date.today().isoformat(),
               "counts": c, "companiesHouseSuspect": suspect, "results": res},
              open(OUT_ALL if a.all else OUT, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("report -> %s" % (OUT_ALL if a.all else OUT))


if __name__ == "__main__":
    main()
