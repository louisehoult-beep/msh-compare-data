#!/usr/bin/env python3
"""Per-trust JAG endoscopy accreditation, from the JAG participating services register.

WHAT THIS IS (16/11/2026, Medilogik endoscopy work). The Joint Advisory Group on GI
Endoscopy (JAG) publishes a live register of every participating endoscopy service in
the UK and the Republic of Ireland, with each service's accreditation status. It is
the single most asked-about fact in an endoscopy conversation, and until this file
existed the Hub held it only as a national aggregate: data/trust-digital-profile.json,
data/trust-map.json and data/trust-pressures.json contained no occurrence of "JAG", so
a trust profile could say nothing about it.

WHAT A ROW SAYS AND DOES NOT SAY. A row is one SERVICE, not one trust: a trust can run
several, and they can hold different statuses, so the trust-level fields below are
counts of its own services and never a single badge for the organisation. "Accredited"
is JAG's word on the day the register was read. Anything else is JAG's word too -
deferred, not awarded, undergoing a JAG onsite assessment, undergoing self-assessment
or not assessed - and none of them is rendered as a failure here. The register has no
feed and no publication date: a status changes on the page when it changes, so the read
date is the only date there is.

THE JOIN IS EXACT, NEVER FUZZY (the rule data/trust-digital-profile.json already uses).
An organisation name joins to data/trust-map.json (NHS ODS) only on an exact match after
normalising case, apostrophes and "&"/"and", plus two named expansions written out
below. Everything else is listed under `unmatched` with its services, never guessed:
most unmatched organisations are independent providers, and the register also covers
Scotland, Northern Ireland, the Republic of Ireland and the Isle of Man, which the
Hub's trust map does not hold at all.

USAGE
    python3 scripts/refresh_trust_jag.py
    python3 scripts/refresh_trust_jag.py --dry-run
    python3 scripts/refresh_trust_jag.py --from PATH   parse a saved copy of the page
Then: python3 scripts/stamp_notice.py && python3 verify.py
Stdlib only.
"""
import argparse
import collections
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

# www.thejag.org.uk/about/participating-services/ redirects here; the path without
# /about/ is a 404. The whole register is in this one page's HTML, which is why the
# table can be read without driving its pager.
SOURCE_URL = "https://app.thejag.org.uk/RegisteredUnits.aspx"
LANDING_URL = "https://www.thejag.org.uk/about/participating-services/"
OUT_PATH = "data/trust-jag.json"
MAP_PATH = "data/trust-map.json"
UA = {"User-Agent": "Elevate-and-Thrive-Hub/1.0 (Medical Sales Intelligence Hub; "
                    "contact@elevateandthrive.uk)"}

# JAG's own five statuses, in the order its own summary table prints them. A status
# the register starts using that is not here is reported, never silently bucketed.
STATUSES = ["Accredited", "Deferred", "Not awarded", "Undergoing JAG onsite assessment",
            "Undergoing self-assessment/not assessed"]

# Two named expansions, each one a spelling difference and not a resemblance:
#   "LHB" is the register's abbreviation of "Local Health Board", the ODS wording for
#   every Welsh board.
#   Cardiff and Vale is the one board the register names without the word "Local";
#   ODS, and the board's own registration, keep it. It is listed here by name rather
#   than handled by a rule, so the exception is visible in the file it affects.
#   Isle of Wight is on the register as a Foundation Trust. It is not one, and never
#   has been: ODS, and the trust's own name, are "Isle of Wight NHS Trust". Without
#   this line an accredited NHS service would be missing from a real Hub trust.
ALIASES = {
    "cardiff and vale university health board": "Cardiff & Vale University Local Health Board",
    "isle of wight nhs foundation trust": "Isle of Wight NHS Trust",
}

ALIAS_WHY = {
    "cardiff and vale university health board":
        "A spelling difference, not a resemblance: the register omits the word Local "
        "that ODS and the board's own registration keep.",
    "isle of wight nhs foundation trust":
        "The register calls it a Foundation Trust. It is not one: ODS, and the trust's "
        "own name, are Isle of Wight NHS Trust.",
}

RULE = (
    "One row on JAG's participating services register is one endoscopy SERVICE, not one "
    "trust. A trust running several services can hold several different statuses, so a "
    "trust's entry below carries its services and a count of each status it holds, never "
    "a single badge for the organisation. Every status is JAG's own word, read at "
    "https://app.thejag.org.uk/RegisteredUnits.aspx on the read date; the register has no "
    "feed and no publication date, so that date is the only date there is. Organisation "
    "names join to data/trust-map.json (NHS ODS) by exact match after normalising case, "
    "apostrophes and '&', plus two named expansions recorded under aliases. Nothing is "
    "fuzzy matched: an organisation that does not join is listed under unmatched with its "
    "services. A trust absent from the register is absent from JAG's list on the read "
    "date, which is a statement about the list and not about the trust.")


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    if len(body) < 50000:
        raise RuntimeError("HTTP %s with a %d byte body from %s (blocked or changed, not the "
                           "register)" % (getattr(r, "status", "?"), len(body), url))
    return body


def cells(row_html):
    out = []
    for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S):
        t = re.sub(r"<br\s*/?>", "\n", c)
        t = re.sub(r"<[^>]+>", "", t)
        out.append(html.unescape(t).strip())
    return out


def parse(page):
    """Every service row on the register. Raises if the table is not where it was."""
    i = page.find('id="tblParticipatingServices"')
    if i < 0:
        raise RuntimeError("the participating services table is not on the page; the layout "
                           "has changed. Nothing parsed.")
    tbl = page[i:page.index("</table>", i)]
    k = tbl.find("<tbody")
    if k < 0:
        raise RuntimeError("the participating services table has no body. Nothing parsed.")
    rows = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl[k:], re.S):
        c = cells(r)
        if len(c) < 10:
            continue
        rows.append({"country": c[0], "region": c[1], "sector": c[2], "adultPaediatric": c[3],
                     "typeOfService": c[4], "organisation": c[5], "service": c[6],
                     "sites": [s.strip() for s in c[7].split(",") if s.strip()],
                     "status": c[9]})
    if not rows:
        raise RuntimeError("the participating services table parsed empty. Nothing recorded.")
    return rows


def norm(name):
    s = (name or "").lower().replace("’", "'").replace("‘", "'").replace("&", " and ")
    s = re.sub(r"[^a-z0-9']+", " ", s).strip()
    return re.sub(r"\blhb\b", "local health board", s)


def tally(services):
    c = collections.Counter(s["status"] for s in services)
    return {k: c[k] for k in STATUSES if c[k]}


def build(page, trust_map, today):
    rows = parse(page)
    unknown = sorted({r["status"] for r in rows} - set(STATUSES))

    by_norm = {norm(t["n"]): t for t in (trust_map or {}).get("trusts") or []}
    alias_norm = {k: norm(v) for k, v in ALIASES.items()}

    joined, loose = collections.defaultdict(list), collections.defaultdict(list)
    for r in rows:
        key = norm(r["organisation"])
        key = alias_norm.get(key, key)
        service = {k: r[k] for k in ("service", "sites", "sector", "adultPaediatric",
                                     "typeOfService", "status")}
        (joined[key] if key in by_norm else loose[r["organisation"]]).append(service)

    trusts = []
    for key, services in joined.items():
        t = by_norm[key]
        services.sort(key=lambda s: s["service"])
        counts = tally(services)
        trusts.append({
            "code": t.get("code"), "name": t["n"], "icb": t.get("icb"),
            "icbName": t.get("icbName"), "region": t.get("region"), "nation": t.get("nation"),
            "services": len(services), "accredited": counts.get("Accredited", 0),
            "statuses": counts, "jagServices": services,
        })
    trusts.sort(key=lambda t: t["name"])

    unmatched = [{"organisation": o, "country": s[0].get("country") or "",
                  "services": len(s), "statuses": tally(s)}
                 for o, s in sorted(loose.items())]
    # country is not on the service dicts above; take it from the rows instead.
    country_of = {r["organisation"]: r["country"] for r in rows}
    for u in unmatched:
        u["country"] = country_of.get(u["organisation"], "")

    # JAG's own summary table is not parsed: these are counted from the service rows
    # this run read, so a disagreement with the page would be visible, not papered over.
    by_country = collections.defaultdict(list)
    by_region = collections.defaultdict(list)
    for r in rows:
        by_country[r["country"]].append(r)
        if r["country"] == "England":
            by_region[r["region"]].append(r)

    return {
        "generated": today.isoformat(),
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "source": "Joint Advisory Group on GI Endoscopy (JAG), participating services register",
        "sourceUrl": SOURCE_URL,
        "sourceLandingUrl": LANDING_URL,
        "rule": RULE,
        "statusValues": STATUSES,
        "unknownStatuses": unknown,
        "aliases": [{"registerName": k, "odsName": v, "why": ALIAS_WHY[k]}
                    for k, v in sorted(ALIASES.items())],
        "summary": {
            "services": len(rows),
            "byStatus": {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES},
            "byCountry": {c: {"services": len(v), **tally(v)} for c, v in sorted(by_country.items())},
            "englandByRegion": {g: {"services": len(v), **tally(v)}
                                for g, v in sorted(by_region.items())},
        },
        "counts": {
            "services": len(rows),
            "organisations": len(joined) + len(loose),
            "trustsJoined": len(trusts),
            "trustsInMap": len(by_norm),
            "servicesJoined": sum(t["services"] for t in trusts),
            "unmatchedOrganisations": len(unmatched),
        },
        "unmatched": unmatched,
        "trusts": trusts,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from", dest="saved", help="parse a saved copy of the register page")
    a = ap.parse_args(argv)
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(MAP_PATH, encoding="utf-8") as fh:
        trust_map = json.load(fh)
    try:
        page = (open(a.saved, encoding="utf-8", errors="replace").read() if a.saved
                else get(SOURCE_URL))
        doc = build(page, trust_map, dt.date.today())
    except Exception as e:  # noqa: BLE001 - a bad read never overwrites a good file
        print("ABORT: register not readable or not parseable, file kept: %s" % e)
        return 1
    c = doc["counts"]
    print("  %(services)d service(s) on the register, %(organisations)d organisation(s)" % c)
    print("  joined to the trust map: %(trustsJoined)d trust(s), %(servicesJoined)d service(s); "
          "%(unmatchedOrganisations)d organisation(s) unmatched" % c)
    print("  by status: " + ", ".join("%s %d" % (s, n)
                                      for s, n in doc["summary"]["byStatus"].items()))
    if doc["unknownStatuses"]:
        print("NOTE: status(es) the register now uses that this script does not list: %s"
              % ", ".join(doc["unknownStatuses"]))
    if a.dry_run:
        print("--dry-run: nothing written.")
        return 0
    old = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as fh:
            old = json.load(fh)
    if old and old.get("_notice"):
        doc = {"_notice": old["_notice"], **doc}
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote %s" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
