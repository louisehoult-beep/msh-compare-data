#!/usr/bin/env python3
"""Second-source the 128 name-proof domains, or refuse them.

WHY THIS EXISTS (added 14/08/2026)
----------------------------------
seed_supplier_domains.py --accept-name recorded 128 domains on NAME proof: the
site's <title> contained the supplier's core name. Every one of those 128 was
also foundBy="guess" — the domain was invented from the company name, then
"confirmed" by a title containing that same name. That is circular. The title
did not identify the company; it echoed the string we had just guessed.

Three ways it fails, all present in the 14/08 report:

  PARKED     biorad.co.uk -> "biorad.co.uk for sale | Spaceship.com". The title
             of a for-sale page is the domain being sold, so a parked domain
             proves itself every time. The PARKED list in the seeding script
             misses Spaceship, Aftermarket, DomainMarket and BuyDomainNames.

  HOMONYM    core() strips trade words, so "Pentax Medical" -> "pentax", which
             matches PENTAX's camera store. Same route gave Richard Wolf
             (endoscopy) an Emmy-winning composer, Blatchford (prosthetics) a
             dental coaching firm, Saluda Medical a town in North Carolina, and
             Merits a Polish online casino. Distinctiveness is tested; industry
             is not.

  ECHO       "Bodystat Website | Bodystat Website", "Kinetik Kinetik" — a
             placeholder page whose title is just the domain label.

THE RULE THIS WRITES UNDER (root rule 14 — state the rule, set an evidence floor)
---------------------------------------------------------------------------------
A name match is a CANDIDATE, never a proof. A domain survives here only on the
strong proof the seeding script already defines: the live site publishes a
company registration number, next to registration wording, matching the
Companies House number recorded for this supplier. A number is unique to one
company and cannot be coincidence; a word in a title can be, and here it was.

Everything else is REFUSED and recorded with its reason. An unproven supplier
keeps its curated list and the member sees something honest. Publishing nothing
is the correct output when the evidence is thin.

USAGE
  python3 scripts/verify_name_proofs.py              # report only, writes nothing
  python3 scripts/verify_name_proofs.py --write      # merge SURVIVORS into the seed

Writes state/name-proof-verification.json always; data/supplier-seed.json only
with --write, and only for domains that passed registration proof.
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys

sys.path.insert(0, "scripts")
import seed_supplier_domains as S   # reuse fetch/prove/text_of — same bar, same code
# seed_format lives beside this script. Imported this way because these scripts
# are also loaded by tests via spec_from_file_location, which does not put the
# script's own directory on sys.path the way running it directly does.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from seed_format import write_like, describe

REPORT = "state/domain-seeding-report.json"
OUT = "state/name-proof-verification.json"
SEED = "data/supplier-seed.json"

# The parking and for-sale services the seeding script's PARKED list misses.
# Each of these produced a "proven" domain in the 14/08 report.
#
# TESTED ONLY AGAINST THE <title>, deliberately. An earlier version also scanned
# the page body for phrases like "buy now" and "make an offer" and refused Flow
# Neuroscience — a real company whose site sells a real product. A parking page
# announces itself in its title; a trading company's body text is full of
# commerce language. Scanning the body for it refuses the honest sites.
PARKED_HOSTS = (
    "spaceship.com", "aftermarket.com", "domainmarket.com", "buydomainnames",
    "sedo.com", "afternic", "dan.com", "hugedomains",
)
PARKED_TITLE = (
    "is for sale", "for sale |", "domain for sale", "is available!",
    "claim your brand", "domain name owner", "inquire about this domain",
    "this domain", "domain is for sale",
)


def is_parked(html, title):
    """True if this page is a parking/for-sale placeholder rather than a company."""
    low = (S.text_of(html) or "").lower()
    t = (title or "").lower()
    for p in S.PARKED:
        if p in low:
            return p
    for p in PARKED_HOSTS:          # a parking service named anywhere is decisive
        if p in t or p in low[:2000]:
            return p
    for p in PARKED_TITLE:          # for-sale wording, title only
        if p in t:
            return p
    return None


def verify(rec):
    """Re-probe one name-proof record for REGISTRATION proof only."""
    name = rec["name"]
    cn = rec.get("companyNumber")
    domain = rec.get("domain")
    base = "https://" + re.sub(r"^https?://", "", domain or "").split("/")[0]

    out = {"name": name, "domain": domain, "companyNumber": cn,
           "priorEvidence": rec.get("evidence"), "checked": dt.date.today().isoformat()}

    if not cn:
        out.update(verdict="REFUSED",
                   reason="no Companies House number recorded — registration proof is impossible")
        return out

    final, html = S.fetch(base)
    if not html:
        out.update(verdict="REFUSED", reason="site did not answer on re-check")
        return out

    parked = is_parked(html, S.title_of(html))
    if parked:
        out.update(verdict="REFUSED",
                   reason="parked or for-sale domain (matched %r) — the title echoed the "
                          "guessed domain, it did not identify the company" % parked)
        return out

    # Read the legal pages too: registration numbers live there, not on the homepage.
    pages = [(final, html)]
    m = re.match(r"(https?://[^/]+)", final or "")
    if m:
        for path in ("/contact", "/contact-us", "/privacy-policy", "/terms",
                     "/legal", "/about-us", "/imprint", "/terms-and-conditions"):
            u, h = S.fetch(m.group(1) + path)
            if h:
                pages.append((u, h))

    # accept_name=False — registration is the only proof that counts here.
    kind, ev, url = S.prove(name, cn, pages, accept_name=False)
    if kind == "registration":
        out.update(verdict="VERIFIED", proof="registration", evidence=ev, url=url)
    else:
        out.update(verdict="REFUSED",
                   reason="site read, but it never publishes registration number %s — "
                          "name-in-title was the only link and that is not evidence" % cn)
    return out


def merge_verdicts(fresh):
    """This run's verdicts on top of every verdict already banked.

    WHY THIS IS A MERGE AND NOT A WRITE (found 18/09/2026, `^o526`). Until today
    this function did not exist and main() wrote `results: res` straight over
    OUT — only the rows the CURRENT report happens to carry proof="name" for.
    That is safe exactly once. The 14/08/2026 adjudication banked 124 REFUSED
    verdicts, and seed_supplier_domains.refused_name_proofs() reads this file
    before every write and drops those 124 names; _ensure_refused_rows() also
    re-stamps them into the report on every --fresh sweep, citing this file as
    "an adjudication that outlives any sweep". But a later sweep produces a
    NEW, smaller set of name proofs — 20 of them on 18/09/2026, none of them
    among the original 128 — so re-running this script to adjudicate those 20,
    which is the documented remedy for them, would have replaced 128 verdicts
    with 20 and silently re-opened all 124 refusals for writing.

    A verdict is an adjudication. It is only ever added to or re-adjudicated by
    a fresh probe of the same supplier, never dropped because this run did not
    happen to look at it.

    Returns (merged, kept, updated): the full verdict list, how many rows came
    from the existing file untouched, and how many this run re-adjudicated.
    """
    try:
        prior = json.load(open(OUT, encoding="utf-8")).get("results", [])
    except (OSError, ValueError):
        prior = []

    by_name = {r["name"]: r for r in prior}
    updated = sum(1 for r in fresh if r["name"] in by_name)
    for r in fresh:
        by_name[r["name"]] = r
    merged = sorted(by_name.values(), key=lambda r: r["name"].lower())
    return merged, len(prior) - updated, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="merge VERIFIED domains into the seed")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    rep = json.load(open(REPORT))
    todo = [x for x in rep["results"] if x.get("proof") == "name"]
    print("re-checking %d name-proof domains for registration proof\n" % len(todo))

    res = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(verify, todo), 1):
            res.append(r)
            mark = "OK  " if r["verdict"] == "VERIFIED" else "  no"
            print("%s %3d/%d  %-42s %s" % (
                mark, i, len(todo), r["name"][:42],
                r.get("evidence", r.get("reason", ""))[:80]))

    ok = [r for r in res if r["verdict"] == "VERIFIED"]
    parked = [r for r in res if "parked" in r.get("reason", "")]
    print("\n%d of %d second-sourced. %d were parked/for-sale domains." % (
        len(ok), len(res), len(parked)))

    merged, kept, updated = merge_verdicts(res)
    if kept or updated:
        print("  carried forward %d earlier verdict(s); %d re-adjudicated this run"
              % (kept, updated))

    json.dump({"_notice": "Second-sourcing of every name-proof domain ever "
                          "recorded. CUMULATIVE — a verdict written here is an "
                          "adjudication and outlives any sweep, so this file is "
                          "merged, never replaced. VERIFIED = the live site "
                          "publishes this supplier's Companies House number. "
                          "REFUSED = not second-sourceable; must not be written.",
               "generated": dt.date.today().isoformat(),
               "checked": len(merged),
               "verified": sum(1 for r in merged if r.get("verdict") == "VERIFIED"),
               "results": merged}, open(OUT, "w"), indent=1)
    print("report -> %s  (%d verdicts, %d verified)"
          % (OUT, len(merged), sum(1 for r in merged if r.get("verdict") == "VERIFIED")))

    if not a.write:
        print("\nreport only — nothing written to the seed.")
        return
    if not ok:
        print("\nnothing second-sourced — seed untouched.")
        return

    # WRITE THE FIELD THE CONSUMER ACTUALLY READS. domain_for() in the seeding
    # script — the same test crawl_supplier_site.py applies — looks at
    # rec["links"] and rec["image"]. A "website" key would be ignored by every
    # consumer while looking, in the diff, exactly like a successful seed.
    seed = json.load(open(SEED, encoding="utf-8"))
    by = {s["name"]: s for s in seed["suppliers"]}
    n = 0
    for r in ok:
        rec = by.get(r["name"])
        if rec is None or S.domain_for(rec):
            continue
        rec.setdefault("links", []).append({
            "label": "Company website",
            "url": "https://" + r["domain"],
            "source": "Proved %s by registration number on %s: %s" % (
                r["domain"], r["checked"], r["evidence"])})
        n += 1
    # Keep whatever format the file already has — read the bytes, never assert
    # them. This hardcoded minified-on-one-line until 21/09/2026, by which time
    # the file on main was pretty-printed at indent 2 (`^o584`); a rewrite in the
    # wrong shape is a whole-file diff that buries the real change, and in this
    # repo the diff is the only review before a live publish.
    fmt, round_trips = write_like(SEED, seed)
    print(describe(SEED, fmt, round_trips))
    print("\nseeded %d website(s) into %s" % (n, SEED))
    print("next: python3 build_supplier_index.py, then python3 verify.py")


if __name__ == "__main__":
    main()
