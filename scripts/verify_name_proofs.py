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

    json.dump({"_notice": "Second-sourcing of the 128 name-proof domains. "
                          "VERIFIED = the live site publishes this supplier's "
                          "Companies House number. REFUSED = not second-sourceable; "
                          "must not be written.",
               "generated": dt.date.today().isoformat(),
               "checked": len(res), "verified": len(ok),
               "results": res}, open(OUT, "w"), indent=1)
    print("report -> %s" % OUT)

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
    # Minified, single line, no trailing newline — the file's own format. A
    # pretty-printed rewrite is a 35,000-line diff that buries the real change,
    # and in this repo the diff is the only review before a live publish.
    with open(SEED, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, separators=(",", ":"))
    print("\nseeded %d website(s) into %s" % (n, SEED))
    print("next: python3 build_supplier_index.py, then python3 verify.py")


if __name__ == "__main__":
    main()
