#!/usr/bin/env python3
"""One-off, 21/10/2026: health tech suppliers on G-Cloud 15 that the Hub had no record for.

WHY
---
data/digital-frameworks.json holds the 2,836 company names on the G-Cloud 15
(RM1557.15) supplier A to Z. Only 44 resolved to a Hub company, because G-Cloud
is a cross-government IT framework and most of its suppliers are general IT
firms the Hub deliberately does not track. The gap that matters is the health
tech companies on G-Cloud 15 that the Hub's health tech lane should know about.

HOW THE LIST WAS MADE
---------------------
1. Every G-Cloud 15 supplier's own A to Z description was read (Digital
   Marketplace, 21/10/2026). 409 named or described health, care or NHS work.
2. Each one's G-Cloud 15 service listings were read (search results, then each
   service page for its lot). Name-only false positives ("care" in another
   sense, general IT firms that merely list the NHS as a client, staffing
   agencies, NHS bodies, universities, charities) were dropped by hand: 233 left.
3. Each of the 233 was checked at source: the company's own site and the
   Companies House register. A record is seeded ONLY where the company number
   comes from one of the two routes HUB-VERIFICATION-STANDARD.md rule 11 allows:
     * website-registration: the number printed on the company's own site;
     * legal-name: the company's own legal page names the exact registered
       legal name and exactly one active Companies House record carries it.
   The register was read for status (Active) and incorporation date on the
   same day. Anything that failed is listed in _gcloud15_healthtech_1021.json
   under "leftOut" with the reason, and is NOT in the seed.

WHAT IT WRITES
--------------
data/supplier-seed.json only (build_supplier_index.py copies seed records into
the index). Each new record carries one curated G-Cloud 15 framework row naming
the lot(s) read on the service page(s), so backfill_digital_frameworks.py leaves
it alone (same reference). Aliases include the exact A to Z name so the name
resolves for every later award match. Company names only: no person, email,
phone or address is stored. Idempotent: a record already present is left alone,
and an alias that already reaches a different company stops the run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

ROOT = os.path.dirname(HERE)
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
DATA = os.path.join(HERE, "_gcloud15_healthtech_1021.json")
DAY = "2026-10-21"
SPEC = "Digital and medical IT"
GC15 = {
    "name": "G-Cloud 15",
    "reference": "RM1557.15",
    "owner": "Government Commercial Agency (GCA)",
    "dates": "6 August 2026 to 5 February 2028",
    "frameworkUrl": "https://www.gca.gov.uk/agreements/RM1557.15",
}
LOT_NAMES = {
    "1a": "Infrastructure as a Service (IaaS) and Platform as a Service (PaaS)",
    "1b": "Infrastructure as a Service (IaaS) and Platform as a Service (PaaS) AO",
    "2a": "Infrastructure Software as a Service (iSaaS)",
    "2b": "Software as a Service (SaaS)",
    "3": "Cloud Support Service",
}
SERVICE_URL = "https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/%s"


def uniq(names):
    out, seen = [], set()
    for n in names:
        k = company_match.norm(n)
        if n and k not in seen:
            seen.add(k)
            out.append(n)
    return out


def framework_row(e):
    svcs = e["services"]
    lots = sorted({s["lot"] for s in svcs}, key=lambda l: (l[0], l))
    first = svcs[0]
    listed = "; ".join("\"%s\" (service ID %s, Lot %s)" % (s["service"], s["id"], s["lot"])
                       for s in svcs)
    row = dict(GC15)
    row.update({
        "lots": [{"lot": l, "name": LOT_NAMES[l]} for l in lots],
        "service": first["service"],
        "serviceId": first["id"],
        "note": ("Listed on the Digital Marketplace as \"%s\", framework G-Cloud 15, with %d "
                 "service%s: %s. Read on the service pages 21/10/2026; also named on the "
                 "G-Cloud 15 supplier A to Z, read the same day. Agreement dates as read on "
                 "GCA's agreement page for RM1557.15, 20/10/2026."
                 % (e["dmName"], len(svcs), "" if len(svcs) == 1 else "s", listed)),
        "url": SERVICE_URL % first["id"],
        "source": "Digital Marketplace service page",
        "capturedOn": DAY,
        "verifiedOn": DAY,
    })
    return row


MAX_PRODUCTS = 12


def products(e):
    """Seed products are plain strings: each G-Cloud 15 service the company lists,
    named as listed, with the first sentence of its own listing summary."""
    out = []
    for sv in e["services"][:MAX_PRODUCTS]:
        desc = (sv.get("desc") or "").strip()
        out.append("%s — %s" % (sv["service"], desc) if desc else sv["service"])
    return out


def products_evidence(e):
    n = len(e["services"])
    return ("Products are the company's own G-Cloud 15 service listings on the Digital Marketplace, "
            "read 21/10/2026: each is the service name as listed, with the first sentence of the "
            "listing's own summary (the supplier's description, not verified by the Hub). %s"
            "Service pages: %s." % (
                ("%d of %d services shown. " % (MAX_PRODUCTS, n)) if n > MAX_PRODUCTS else "",
                ", ".join(SERVICE_URL % sv["id"] for sv in e["services"][:MAX_PRODUCTS])))


def record(e):
    proof = {
        "number": e["companyNumber"],
        "route": e["proofRoute"],
        "url": e["proofUrl"],
        "evidence": e["proofQuote"],
        "checkedOn": DAY,
    }
    if e["proofRoute"] == "legal-name":
        proof["note"] = ("Exact registered legal name on the company's own legal page, and exactly "
                         "one active Companies House record of that name (%s, %s), read %s. "
                         "HUB-VERIFICATION-STANDARD rule 11, second route."
                         % (e["registeredName"], e["companyNumber"], DAY))
    note = ("Added 21/10/2026 (G-Cloud 15 health tech sweep). On the Digital Marketplace G-Cloud 15 "
            "supplier A to Z as \"%s\". Companies House %s %s, active, incorporated %s, read "
            "21/10/2026. What it sells, from the company's own site read 21/10/2026: %s Products below are "
            "its G-Cloud 15 service listings; no full range captured in supplier-products.json."
            % (e["dmName"], e["companyNumber"], e["registeredName"], e["incorporated"],
               e["productSummary"].strip()))
    return {
        "name": e["name"],
        "aliases": uniq([e["name"], e["dmName"], e["registeredName"]] + e.get("extraAliases", [])),
        "specialities": [SPEC],
        "products": products(e),
        "_productsEvidence": products_evidence(e),
        "frameworks": [framework_row(e)],
        "alerts": [],
        "news": [],
        "links": [{"label": "Company website", "url": e["website"],
                   "source": "Company's own site, read %s." % DAY}],
        "awards": [],
        "curated": True,
        "note": note,
        "verified": DAY,
        "source": ("Digital Marketplace G-Cloud 15 service listings, Companies House register and "
                   "the company's own site, read %s" % DAY),
        "companyNumberProof": proof,
    }


def load(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def main():
    data = load(DATA)
    doc = load(SEED)
    sups = doc["suppliers"]
    by = {s.get("name"): s for s in sups}
    index = company_match.build_index(doc)
    numbers = {}
    for s in sups:
        for n in ((s.get("companyNumberProof") or {}).get("number"), s.get("companyNumber")):
            if n:
                numbers.setdefault(str(n).upper(), s.get("name"))
    added = changed = 0

    for e in data["add"]:
        rec = record(e)
        if rec["name"] in by:
            continue
        clash = numbers.get(e["companyNumber"].upper())
        if clash:
            raise SystemExit("%s: company number %s is already held by %r"
                             % (rec["name"], e["companyNumber"], clash))
        for a in rec["aliases"]:
            hits = ((index.get(company_match.key(a)) or set())
                    | (index.exact.get(company_match.norm(a)) or set()))
            if hits - {rec["name"]}:
                raise SystemExit("alias %r of %r already reaches %s" % (a, rec["name"], sorted(hits)))
        sups.append(rec)
        by[rec["name"]] = rec
        for a in rec["aliases"]:
            index.setdefault(company_match.key(a), set()).add(rec["name"])
            index.exact.setdefault(company_match.norm(a), set()).add(rec["name"])
        numbers[e["companyNumber"].upper()] = rec["name"]
        added += 1

    for name, a in data["aliases"].items():
        s = by.get(name)
        if s is None:
            raise SystemExit("no record %r for alias %r" % (name, a["alias"]))
        before = json.dumps(s, sort_keys=True)
        hits = ((index.get(company_match.key(a["alias"])) or set())
                | (index.exact.get(company_match.norm(a["alias"])) or set()))
        if hits - {name}:
            raise SystemExit("alias %r of %r already reaches %s" % (a["alias"], name, sorted(hits)))
        al = s.setdefault("aliases", [])
        if a["alias"] not in al:
            al.append(a["alias"])
        if a.get("proof") and not s.get("companyNumberProof"):
            s["companyNumberProof"] = a["proof"]
        ev = s.get("_aliasesEvidence") or ""
        if a["evidence"] not in ev:
            s["_aliasesEvidence"] = (ev.rstrip() + " " + a["evidence"]).strip()
        if a.get("site") and not any(l.get("url") == a["site"] for l in s.get("links") or []):
            s.setdefault("links", []).append({"label": "Company website", "url": a["site"],
                                              "source": "Company's own site, read %s." % DAY})
        if json.dumps(s, sort_keys=True) != before:
            changed += 1

    if added or changed:
        fmt, rt = write_like(SEED, doc)
        print(describe(SEED, fmt, rt))
    print("%s: %d record(s) added, %d alias record(s) changed" % (SEED, added, changed))


if __name__ == "__main__":
    main()
