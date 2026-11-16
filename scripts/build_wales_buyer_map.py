#!/usr/bin/env python3
"""
build_wales_buyer_map.py — the Wales buyer map. Writes data/wales-buyer-map.json.

WHY THIS EXISTS. Until 16/11/2026 the Hub had no Wales buyer coverage worth the
name. data/trust-map.json carried exactly three Welsh organisations — Velindre,
Welsh Ambulance and Public Health Wales — because the trust crawl asked ODS only
for RO197 (NHS TRUST) and RO107 (CARE TRUST). Wales does not buy through trusts.
It buys through SEVEN Local Health Boards, whose ODS primary role is RO142
(LOCAL HEALTH BOARD), and in practice it buys through ONE procurement service,
NWSSP, on behalf of all of them. None of that was anywhere on the Hub, so a rep
asking "who buys this in Wales" got England's answer or nothing.

It came up because Rocialle Healthcare sell into Wales. Their own award record in
this repo names NWSSP on five notices — their second-largest buyer after NHS
Supply Chain and SCCL together (nine). That is read from the data, not asserted.

WHAT IS DERIVED AND WHAT IS CURATED, and why the curated half lives in THIS FILE
rather than in the JSON.

  * organisations  — derived, every run, from the ODS ORD API. Never edited.
  * buyerNames     — derived, every run, from this repo's own Find a Tender and
                     Contracts Finder captures. Never edited.
  * procurementRoute — curated. Every field carries the URL it was read from and
                     the date it was read.

The curated block is a Python constant below, NOT a block this script reads back
out of its own output and preserves. That is deliberate and it is the lesson of
08/11/2026, when the Daily refresh regenerated supplier-index.json and silently
dropped a hand-written product range, and of the comment in refresh_trusts.py
about a key a generator does not write being a key that generator destroys. A
generator that rebuilds a file from scratch must hold everything that file needs
to say. If PROCUREMENT_ROUTE were merged in from the previous output, one run
with a missing or truncated input would quietly publish a Wales page with no
route to market on it and nothing would fail.

SOURCES, all primary:
  * NHS Organisation Data Service (ODS) ORD API, Open Government Licence v3.
    Nation comes from the organisation's own GeoLoc.Location.Country field, not
    from "has no ICB link" — see the note in refresh_trusts.py's fetch_detail.
  * nwssp.nhs.wales, NWSSP's own site, for the procurement route.
  * The award notices already captured in data/company-awards.json, for the
    buyer-name spellings. A rep searching "NWSSP" has to find the 151 notices
    filed under "NHS Wales Shared Services Partnership-Procurement Services
    (hosted by Velindre University NHS Trust)" too, and there are twenty-odd
    spellings of the same buyer across the notices.

python has no DNS in the sandbox this was written in. Fetch with curl into a
directory and pass --ods-dir, or let the script fetch directly where it can.

  python3 scripts/build_wales_buyer_map.py
  python3 scripts/build_wales_buyer_map.py --ods-dir /tmp/ods
  python3 scripts/build_wales_buyer_map.py --check
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "wales-buyer-map.json")
AWARDS = os.path.join(DATA, "company-awards.json")

ODS_BASE = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"

# RO142 is the seven Local Health Boards — the buyers. RO197 is the three Welsh
# NHS Trusts. Both are crawled and then filtered on Country == WALES, so an
# English trust appearing under either role cannot leak in.
#
# NOT RO144 (WELSH LOCAL HEALTH BOARD). It looks like the obvious role and it is
# the wrong one: checked 16/11/2026, RO144 returns ZERO active organisations.
# Every live Welsh health board is filed under RO142. Do not "correct" this.
LIST_ROLES = ("RO142", "RO197")

# A floor, not a target. Wales has had seven health boards since the Cwm Taf
# Morgannwg boundary change of 01/04/2019 and three NHS trusts since Public
# Health Wales was created on 01/10/2009. If this crawl returns fewer, ODS has
# changed shape or the fetch is broken, and publishing a short Wales map is
# worse than publishing none.
MIN_HEALTH_BOARDS = 7
MIN_TRUSTS = 3

# Curated. Every value was read at the URL given, on the date given.
PROCUREMENT_ROUTE = {
    "name": "NHS Wales Shared Services Partnership — Procurement Services",
    "shortName": "NWSSP",
    "whatItIs": (
        "The single procurement service for NHS Wales. It runs the frameworks and "
        "the tenders that the seven Local Health Boards and three NHS Trusts buy "
        "through, rather than each of them tendering separately."
    ),
    "whatItIsSource": "https://nwssp.nhs.wales/ourservices/procurement-services/",
    "whatItIsSourceQuote": (
        "As an established Procurement Service we have been assisting the Health "
        "Boards and Trusts in the delivery of patient centred services for NHS "
        "Wales Shared Services."
    ),
    "buysOnBehalfOf": "The health boards and trusts across NHS Wales.",
    "buysOnBehalfOfSource": "https://nwssp.nhs.wales/about-us/our-suppliers/",
    "buysOnBehalfOfSourceQuote": (
        "Information about how to register for contract opportunities and details "
        "about the types of goods and services procured by NHS Wales Shares "
        "Services Partnership on behalf of health boards and trusts across NHS "
        "Wales can be found below."
    ),
    # NWSSP is not an organisation in its own right on the ODS register. It is
    # hosted by Velindre, which is why award notices are filed under Velindre's
    # name and why the ODS-derived organisation list below has no NWSSP row.
    # The hosting is stated by the notices themselves, verbatim, on 151 of them.
    "hostedBy": {
        "name": "Velindre University NHS Trust",
        "odsCode": "RQF",
        "odsName": "VELINDRE NHS TRUST",
        "odsNameNote": (
            "ODS still carries the pre-university-status name. The notices and "
            "NWSSP's own site use 'Velindre University NHS Trust'. Both are "
            "recorded; neither is corrected into the other."
        ),
        "source": "Find a Tender and Contracts Finder award notices, as captured "
                  "in data/company-awards.json",
        "sourceQuote": "NHS Wales Shared Services Partnership-Procurement Services "
                       "(hosted by Velindre University NHS Trust)",
    },
    # THE FACT A REP ACTUALLY NEEDS. Wales does not advertise through Find a
    # Tender alone. A supplier who watches only FTS misses the Welsh pipeline.
    "advertisedOn": {
        "name": "Sell2Wales",
        "url": "https://www.sell2wales.gov.uk",
        "source": "https://nwssp.nhs.wales/about-us/our-suppliers/",
        "sourceQuote": (
            "Frameworks are advertised on Sell2Wales ( www.sell2wales.gov.uk ) "
            "where suppliers are given the opportunity to bid for business."
        ),
    },
    "enquiries": "ProcurementServicesenquiries@wales.nhs.uk",
    "enquiriesSource": "https://nwssp.nhs.wales/about-us/our-suppliers/",
    "frameworkScope": (
        "Both goods and services, including capital equipment, pharmaceutical, "
        "medical and clinical, food and textiles, utilities, maintenance, "
        "information technology and the commissioning of healthcare services."
    ),
    "frameworkScopeSource": "https://nwssp.nhs.wales/about-us/our-suppliers/",
    "frameworkScopeSourceQuote": (
        "NWSSP Frameworks covers both goods and services including, capital "
        "equipment, Pharmaceutical, medical and clinical, food and textiles, "
        "utilities, maintenance, Information technology and the commissioning of "
        "healthcare services."
    ),
    "frameworkTerm": "Generally three to four years.",
    "frameworkTermSource": "https://nwssp.nhs.wales/about-us/our-suppliers/",
    "frameworkTermSourceQuote": "Frameworks or contracts generally last for three "
                                "to four years.",
    "smes": (
        "Tenders are broken into smaller lots where appropriate so that small and "
        "medium enterprises can bid."
    ),
    "smesSource": "https://nwssp.nhs.wales/about-us/our-suppliers/",
    "smesSourceQuote": (
        "NWSSP welcome tenders from small and medium enterprises where appropriate "
        "tenders are broken down into smaller lots to make it easier for SME's to "
        "bid for business."
    ),
    "checkedAt": "2026-11-16",
}

# Any award-notice buyer string matching this is NWSSP or one of the Welsh
# buyers. Deliberately narrow: it must not catch "Registered in England and
# Wales", which is boilerplate in the SCCL and CPP LLP notices and would
# otherwise drag 55 English framework awards onto a Welsh page.
WELSH_BUYER = re.compile(
    r"(nwssp"
    r"|wales shared service"          # covers "Services" and the "Service" typo
    r"|wales shares services"         # NWSSP's own typo, which reaches the notices
    r"|shared services parternship"   # as spelled on one notice
    r"|etenderwales"
    r"|velindre"
    r"|public health wales"
    r"|welsh ambulance"
    r"|betsi cadwaladr|hywel dda|swansea bay|cardiff and vale|cardiff & vale"
    r"|cwm taf|aneurin bevan|powys teaching"
    r"|local health board|\blhb\b|\buhb\b"
    r")", re.I)

# Boilerplate that mentions Wales without being a Welsh buyer.
NOT_A_WELSH_BUYER = re.compile(r"registered in england and wales", re.I)

# ODS CALLS THEM SOMETHING NOBODY ELSE CALLS THEM. Every Welsh board's ODS name
# ends "LOCAL HEALTH BOARD"; every award notice, and the board's own website,
# says "University Health Board". A rep searching the name they actually see
# would match nothing. These stems tie a notice spelling back to an ODS code.
#
# Each stem is a place or person name that belongs to exactly one board and to
# nothing else in the notices — checked against all 8,514 captured award rows on
# 16/11/2026. Do not add a stem that is merely suggestive: "university health
# board" on its own is shared by half of England, and "cardiff" alone also
# reaches Cardiff University and Public Health Wales, which is why the stem is
# "cardiff and vale" and its ampersand form.
ORG_NAME_STEMS = {
    "7A1": (r"betsi cadwaladr",),
    "7A2": (r"hywel dda",),
    "7A3": (r"swansea bay", r"\bsbuhb\b"),
    "7A4": (r"cardiff and vale", r"cardiff & vale"),
    "7A5": (r"cwm taf",),
    "7A6": (r"aneurin bevan",),
    "7A7": (r"powys teaching", r"powys local health board",
            r"powys university health board"),
    "RQF": (r"velindre",),
    "RT4": (r"welsh ambulance",),
    "RYT": (r"public health wales",),
}


def clean_name(n):
    """ODS publishes names in capitals. Match refresh_trusts.py's casing so the
    two files read as one dataset rather than two."""
    n = n.title().replace(" Nhs ", " NHS ").replace("'S ", "'s ").replace("'S", "'s")
    n = re.sub(r"\bAnd\b", "and", n)
    n = re.sub(r"\bOf\b", "of", n)
    n = re.sub(r"\bThe\b", "the", n)
    n = n.replace("Nwssp", "NWSSP")
    return n[0].upper() + n[1:]


def _get_json(url, ods_dir, name):
    """Read from --ods-dir if it has the file, else fetch. The sandbox this was
    written in has no DNS from python, so a curl-then-read path has to exist."""
    if ods_dir:
        p = os.path.join(ods_dir, name)
        if os.path.exists(p):
            with open(p) as fh:
                return json.load(fh)
    return json.loads(urllib.request.urlopen(url, timeout=60).read())


def fetch_organisations(ods_dir):
    """The Welsh NHS buyers, from ODS, filtered on the register's own country."""
    listed = {}
    for role in LIST_ROLES:
        url = "%s?PrimaryRoleId=%s&Status=Active&Limit=1000" % (ODS_BASE, role)
        doc = _get_json(url, ods_dir, "list-%s.json" % role)
        for o in doc.get("Organisations", []):
            listed.setdefault(o["OrgId"], o)

    out = []
    for code, o in sorted(listed.items()):
        detail = _get_json("%s/%s" % (ODS_BASE, code), ods_dir, "org-%s.json" % code)
        r = detail["Organisation"]
        loc = (r.get("GeoLoc") or {}).get("Location") or {}
        if (loc.get("Country") or "").strip().upper() != "WALES":
            continue
        # Same liveness test as the trust crawl: ODS keeps merged and dissolved
        # organisations at Status Active indefinitely. A Legal date carrying an
        # End is the reliable signal.
        if any(d.get("Type") == "Legal" and d.get("End") for d in r.get("Date", [])):
            continue
        roles = [x["id"] for x in (r.get("Roles") or {}).get("Role", [])
                 if x.get("primaryRole")]
        primary = roles[0] if roles else None
        operational = next((d.get("Start") for d in r.get("Date", [])
                            if d.get("Type") == "Operational"), None)
        out.append({
            "n": clean_name(r["Name"]),
            "odsName": r["Name"],
            "code": code,
            "kind": ("Local Health Board" if primary == "RO142"
                     else "NHS Trust" if primary == "RO197" else None),
            "primaryRoleId": primary,
            "town": (loc.get("Town") or "").title(),
            "postcode": loc.get("PostCode", ""),
            "nation": "Wales",
            "operationalFrom": operational,
            "buysVia": PROCUREMENT_ROUTE["shortName"],
            "source": "%s/%s" % (ODS_BASE, code),
        })
    return out


def buyer_names(orgs):
    """Every spelling of a Welsh buyer in the award notices this repo has already
    captured, with how many notices carry it and the dates it spans.

    This is the search problem, not a vanity count. The notices spell this buyer
    twenty-odd ways and a rep typing "NWSSP" would otherwise find one notice out
    of two hundred."""
    if not os.path.exists(AWARDS):
        return [], {}
    doc = json.load(open(AWARDS))
    rows = []
    for company, recs in (doc.get("companies") or {}).items():
        for r in (recs if isinstance(recs, list) else recs.get("awards", [])):
            rows.append((company, r))

    names, by_company = {}, {}
    for company, r in rows:
        b = (r.get("buyer") or "").strip()
        if not b or NOT_A_WELSH_BUYER.search(b) or not WELSH_BUYER.search(b):
            continue
        e = names.setdefault(b, {"name": b, "awards": 0, "firstSeen": None,
                                 "lastSeen": None, "sources": set()})
        e["awards"] += 1
        d = r.get("date")
        if d:
            e["firstSeen"] = min(e["firstSeen"] or d, d)
            e["lastSeen"] = max(e["lastSeen"] or d, d)
        if r.get("source"):
            e["sources"].add(r["source"])
        by_company[company] = by_company.get(company, 0) + 1

    out = []
    for e in sorted(names.values(), key=lambda x: (-x["awards"], x["name"])):
        e["sources"] = sorted(e["sources"])
        out.append(e)
    return out, by_company


def attach_notice_spellings(orgs, names):
    """Record, per organisation, the names the award notices actually use for it,
    with the notice count behind each. Derived from the notices alone: a spelling
    nothing was awarded under does not appear."""
    for o in orgs:
        pats = [re.compile(p, re.I) for p in ORG_NAME_STEMS.get(o["code"], ())]
        seen = []
        for e in names:
            if any(p.search(e["name"]) for p in pats):
                seen.append({"name": e["name"], "awardNotices": e["awards"]})
        o["noticeSpellings"] = seen
        o["noticeSpellingsSource"] = (
            "Find a Tender and Contracts Finder award notices captured in "
            "data/company-awards.json. Tied to this ODS code by a place-name stem "
            "that belongs to this organisation and nothing else in the notices.")
        # Velindre's rows are overwhelmingly NWSSP acting for all of Wales, not
        # Velindre buying for itself. Say so rather than letting a reader take
        # 180-odd notices as one cancer centre's purchasing.
        if o["code"] == "RQF":
            o["note"] = (
                "NWSSP is hosted by this trust and has no ODS record of its own, "
                "so all-Wales procurement notices are filed under Velindre's name. "
                "Most notices counted here are NWSSP buying for every health board "
                "and trust in Wales, not Velindre buying for itself.")
    return orgs


def build(ods_dir):
    orgs = fetch_organisations(ods_dir)
    boards = [o for o in orgs if o["primaryRoleId"] == "RO142"]
    trusts = [o for o in orgs if o["primaryRoleId"] == "RO197"]
    if len(boards) < MIN_HEALTH_BOARDS or len(trusts) < MIN_TRUSTS:
        raise SystemExit(
            "ABORT: ODS returned %d Welsh health board(s) and %d Welsh trust(s); "
            "expected at least %d and %d. Refusing to publish a short Wales map."
            % (len(boards), len(trusts), MIN_HEALTH_BOARDS, MIN_TRUSTS))

    names, by_company = buyer_names(orgs)
    top = sorted(by_company.items(), key=lambda kv: (-kv[1], kv[0]))[:25]
    attach_notice_spellings(orgs, names)

    return {
        "rule": (
            "The Wales buyer map. Welsh NHS organisations are taken from the NHS "
            "Organisation Data Service register every run and filtered on the "
            "register's own country field, never on 'has no ICB link'. An "
            "organisation whose ODS record carries a legal end date is excluded, "
            "because ODS leaves merged and dissolved bodies at status Active. The "
            "procurement route is read at NWSSP's own site and every field carries "
            "the URL and the date it was read. Buyer-name spellings and their "
            "counts are read from the Find a Tender and Contracts Finder notices "
            "already captured in data/company-awards.json; nothing is inferred "
            "from a name that does not appear in a notice. NWSSP has no ODS record "
            "of its own, so it appears as the procurement route rather than as an "
            "organisation."
        ),
        "asOf": datetime.date.today().strftime("%d/%m/%Y"),
        "generated": datetime.date.today().isoformat(),
        "sources": [
            {"name": "NHS Organisation Data Service (ODS) ORD API",
             "url": ODS_BASE,
             "licence": "Open Government Licence v3",
             "usedFor": "the Welsh health boards and trusts, their towns, "
                        "postcodes and operational start dates"},
            {"name": "NHS Wales Shared Services Partnership",
             "url": "https://nwssp.nhs.wales/",
             "usedFor": "the procurement route, the tender portal, the framework "
                        "scope and term, and the enquiries address"},
            {"name": "Find a Tender and Contracts Finder award notices",
             "url": "https://www.find-tender.service.gov.uk/",
             "usedFor": "the buyer-name spellings, their notice counts and the "
                        "suppliers who hold Welsh awards"},
        ],
        "nation": "Wales",
        "noIcbs": (
            "Wales has no Integrated Care Boards. The seven Local Health Boards "
            "are both the commissioner and the provider for their area, which is "
            "why every Welsh row in data/trust-map.json carries a null icb and "
            "why an England-shaped stakeholder map does not describe Wales."
        ),
        "procurementRoute": PROCUREMENT_ROUTE,
        "counts": {
            "organisations": len(orgs),
            "healthBoards": len(boards),
            "trusts": len(trusts),
            "buyerNameSpellings": len(names),
            "awardNotices": sum(e["awards"] for e in names),
            "suppliersWithWelshAwards": len(by_company),
        },
        "organisations": orgs,
        "buyerNames": names,
        "suppliersWithWelshAwards": [{"company": c, "awards": n} for c, n in top],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ods-dir", default=None,
                    help="Directory of pre-fetched ODS JSON (list-<role>.json, "
                         "org-<code>.json). For sandboxes with no DNS from python.")
    ap.add_argument("--check", action="store_true",
                    help="Build and report, write nothing. Exit 1 if the built "
                         "map differs from what is on disk.")
    args = ap.parse_args()

    doc = build(args.ods_dir)

    if os.path.exists(OUT):
        old = json.load(open(OUT))
        doc["_notice"] = old.get("_notice")
    else:
        doc["_notice"] = None

    c = doc["counts"]
    print("wales-buyer-map: %d organisations (%d health boards / %d trusts), "
          "%d buyer-name spelling(s) across %d award notice(s), "
          "%d supplier(s) holding Welsh awards."
          % (c["organisations"], c["healthBoards"], c["trusts"],
             c["buyerNameSpellings"], c["awardNotices"],
             c["suppliersWithWelshAwards"]))

    if args.check:
        if not os.path.exists(OUT):
            print("data/wales-buyer-map.json does not exist yet.", file=sys.stderr)
            return 1
        old = json.load(open(OUT))
        drift = [k for k in ("organisations", "procurementRoute", "buyerNames")
                 if old.get(k) != doc.get(k)]
        if drift:
            print("STALE: %s differ(s) from a fresh build." % ", ".join(drift),
                  file=sys.stderr)
            return 1
        print("data/wales-buyer-map.json matches a fresh build.")
        return 0

    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote data/wales-buyer-map.json")
    print("NOW RUN: python3 scripts/stamp_notice.py   (the gate fails without the notice)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
