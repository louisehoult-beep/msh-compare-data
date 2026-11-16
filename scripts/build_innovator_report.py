#!/usr/bin/env python3
"""
build_innovator_report.py — build data/innovator-report.json, the one file
app/innovator-report.js needs on top of the data files the Hub already serves.

WHY THIS EXISTS
---------------
The Innovator Market Analysis Report (Hub page, new 16/11/2026) renders
client-side from the repo's own JSON, the way app/icb-pack.js does. Six of the
files it needs are small enough to fetch in the browser:

    products.json  compare-suppliers.json  frameworks.json
    framework-directory-extra.json  icb-watch.json  open-tenders.json
    pending-awards.json  trust-pressures.json  digital-lane.json

One is not. data/company-awards.json is 20 MB, and the report only ever needs,
per speciality, the award history of the companies that speciality's competitor
set already names. So this script reduces that 20 MB to the rows the report
asks for, and bundles three other things the report cannot read at runtime:

 1. AWARDS. Per speciality, per competitor company: how many award rows the Hub
    holds, the earliest and latest dates, and the three most recent rows in
    full (title, buyer, date, value, notice URL). A company with no rows is
    recorded with count 0, not omitted — "no award record in the Hub's set" is
    a finding an innovator needs, and silence would read as "no contracts".

 2. STAKEHOLDER ROLES. Parsed out of app/mst-logic.js, which is the Hub's
    Stakeholder Mapper and the single source of truth for these roles. Parsed,
    not re-typed: if the mapper's role library changes and this parse stops
    matching, the script fails loudly rather than letting the report drift away
    from the tool members already use. The `spin` closures are not carried over
    (they are functions, and the report does not ask SPIN questions).

 3. FRESHNESS INDEX. Every source file's own `dataAsOf`/`asOf`, read here at
    build time. app/innovator-report.js prints these, and — this is the point —
    if a file cannot be fetched in the browser, the report says so and shows
    this last good reading and its date instead of dropping the section. That
    is the Hub's rule for an unreachable source, and without a date recorded
    somewhere outside the file itself the report could not keep it.

 4. DIGITAL FRAMEWORK FLAG. framework-directory-extra.json's `otherBodies` rows
    carry no machine-readable "this is a digital or technology framework" field,
    so the report cannot filter them for a software or diagnostic-software
    product. The flag is set here, from each row's own name and owner against
    the explicit list in DIGITAL_ROWS below, and the rule is written into the
    output so the page can print it. Nothing is inferred from a keyword guess.

NOTHING IS COMPUTED THAT IS NOT IN A SOURCE FILE. Every row written here keeps
the URL it came in with, and the output records which file each block came from
and when that file was last read.

USAGE
    python3 scripts/build_innovator_report.py
    python3 scripts/build_innovator_report.py --check    # exit 1 if stale

Run it after refresh_awards.py / refresh_frameworks.py, then:
    python3 scripts/stamp_notice.py
    bash scripts/gate.sh
"""
import argparse
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
APP = os.path.join(ROOT, "app")
OUT = os.path.join(DATA, "innovator-report.json")

# How many award rows to carry per company. Three is what fits one printed row
# of the report without pushing the competitor table onto a second page.
AWARDS_PER_COMPANY = 3

# The framework-directory-extra rows that are digital or technology routes, by
# their own `name` exactly as that file holds it. An explicit list, not a
# keyword match: "Medical & Industrial Gases" contains no digital word and
# "Digital Dictation" does, but so would a row about digital thermometers. The
# 17 digital and technology rows added on 16/11/2026 plus the four that were
# already there are named here one by one, each read at its own agreement page.
DIGITAL_ROWS = {
    "Artificial Intelligence (AI)",
    "Audio Visual Solutions and Integrated Operating Theatres 2",
    "Back Office Software 2",
    "Cloud Compute 2",
    "Cloud Solutions 2",
    "Crown Hosting II",
    "Cyber Security Services 3",
    "Digital Dictation, Speech Recognition and Outsourced Transcription 2",
    "Digital Health Advisory",
    "Digital Outcomes and Specialists 7 (DOS7)",
    "Digital Workplace Solutions 2",
    "G-Cloud 15",
    "Intelligent Automation",
    "Medicines Optimisation Prescribing Decision Support Systems 3",
    "Reporting Services: Teleradiology",
    "Spark DPS (emerging technology marketplace)",
    "Tech Devices - Link 4 (Lot 2: Specialist healthcare related IT hardware)",
    "Technology Enabled Care Services 2 (TECS2)",
    "Technology Products & Associated Services 2 (TePAS2) — Lot 5 Health and Social Care Technology",
    "Technology Services 4 (TS4)",
}

DIGITAL_RULE = (
    "A row is flagged digital when its own name appears in the explicit list in "
    "scripts/build_innovator_report.py (DIGITAL_ROWS), each of which was read at "
    "its own agreement page. No keyword match is used: a keyword match would "
    "catch a framework for digital thermometers and miss one named only for its "
    "service."
)

# The Hub page each block of the report points at, so every generated line can
# carry a Hub link beside its upstream source link.
HUB = "https://medsalesintelligencehub.co.uk/medical-sales-hub/"
HUB_PAGES = {
    "suppliers": HUB + "suppliers/",
    "competitors": HUB + "who-are-the-competitors/",
    "frameworks": HUB + "tender-history/",
    "digitalRoutes": HUB + "nhs-digital-health-buying-routes/",
    "mapper": HUB + "med-sales-tools/#view-mapper",
    "icbPack": HUB + "icb-pack/",
    "evidence": HUB + "clinical-evidence-library/",
    "girft": HUB + "girft/",
    "structure": HUB + "nhs-structure-map/",
    "gates": HUB + "health-tech-approval-gates/",
    "mhra": HUB + "mhra-regulatory-desk/",
    "awards": HUB + "tender-history/",
    "valueEquation": HUB + "med-sales-tools/value-equation/",
}

NOTICE_PLACEHOLDER = {"ref": "stamp_notice.py writes this"}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def norm_co(name):
    """Fold a company name to a comparison key.

    Deliberately the same shape as verify.py's _norm_co: lower case, strip the
    legal-form and territory words, collapse punctuation. It exists only to tie
    a competitor row in compare-suppliers.json to a company key in
    company-awards.json; where it does not tie, the company is written out with
    count 0 and matched=false, never quietly dropped.
    """
    s = (name or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    words = s.split()
    drop = {
        "ltd", "limited", "plc", "llp", "inc", "incorporated", "gmbh", "ab", "as",
        "bv", "nv", "sa", "srl", "spa", "pty", "co", "company", "holdings", "group",
        "uk", "u", "k", "gb", "england", "europe", "international", "the", "t", "a",
        "trading", "medical", "healthcare", "health",
    }
    # 'medical'/'healthcare'/'health' are dropped only when they are not the
    # whole distinguishing part of the name, or "Crest Medical" and "Crest"
    # would stop being the same row for no good reason while "Medical Ltd"
    # would fold to nothing.
    kept = [w for w in words if w not in drop]
    if not kept:
        kept = [w for w in words if w not in {"ltd", "limited", "plc", "the"}]
    return " ".join(kept)


def parse_stakeholder_roles(js):
    """Pull the role library and the per-product templates out of app/mst-logic.js.

    The mapper holds them as a JavaScript object literal with a `spin` closure
    on most roles, so this is a field-by-field read of the string properties,
    not a JSON parse. It is strict on purpose: a role that loses a field, or a
    template that disappears, stops the build.
    """
    body = js[js.index("var L={"):]
    roles = {}
    # Each role starts "key:{icon:'…',role:'…'" at one nesting level inside L.
    for m in re.finditer(r"\n    ([a-z_]+):\{(.*?)\n    \}?(?=,\n    [a-z_]+:\{|\n  \};)", body, re.S):
        pass  # the file is minified onto single lines; the simple scan below is used instead
    # The real shape: one role per line, "key:{...}," with no newlines inside.
    for line in body.splitlines():
        line = line.strip()
        m = re.match(r"^([a-z_]+):\{(.*?)\},?$", line)
        if not m:
            continue
        key, fields = m.group(1), m.group(2)
        got = {}
        for field in ("role", "whoSec", "whoPri", "cares", "evidence", "hook", "risk"):
            fm = re.search(field + r":'((?:[^'\\]|\\.)*)'", fields)
            if fm:
                got[field] = fm.group(1).replace("\\'", "'").replace("\\\\", "\\")
        if "role" in got:
            roles[key] = got
    if len(roles) < 15:
        raise SystemExit(
            "build_innovator_report.py: only %d stakeholder roles parsed out of "
            "app/mst-logic.js (expected the mapper's full library, 19 on "
            "16/11/2026). The mapper's layout has changed — read it and fix this "
            "parse rather than shipping a short role list." % len(roles)
        )

    tm = re.search(r"var TPL=\{(.*?)\};", js, re.S)
    if not tm:
        raise SystemExit(
            "build_innovator_report.py: no `var TPL={...};` in app/mst-logic.js, so "
            "the per-product stakeholder templates cannot be read."
        )
    tpl = {}
    for k, lst in re.findall(r"([a-z]+):\[([^\]]*)\]", tm.group(1)):
        tpl[k] = [x.strip().strip("'\"") for x in lst.split(",") if x.strip()]
    missing = [k for v in tpl.values() for k in v if k not in roles]
    if missing:
        raise SystemExit(
            "build_innovator_report.py: template(s) name stakeholder role(s) the "
            "parse did not find: %s" % ", ".join(sorted(set(missing)))
        )
    return roles, tpl


def build():
    products = load("products.json")
    compare = load("compare-suppliers.json")
    frameworks = load("frameworks.json")
    extra = load("framework-directory-extra.json")
    icbwatch = load("icb-watch.json")
    tenders = load("open-tenders.json")
    pending = load("pending-awards.json")
    pressures = load("trust-pressures.json")
    calendar = load("nhssc-procurement-calendar.json")
    digital_fw = load("digital-frameworks.json")
    digital_awards = load("company-digital-awards.json")
    digital_lane = load("digital-lane.json")
    awards = load("company-awards.json")

    with open(os.path.join(APP, "mst-logic.js"), encoding="utf-8") as fh:
        roles, tpl = parse_stakeholder_roles(fh.read())

    # Index company-awards by the normalised company name, once.
    by_key = {}
    for company, rows in awards["companies"].items():
        by_key.setdefault(norm_co(company), []).append((company, rows))

    # The 43-slug speciality taxonomy that open-tenders.json and the Hub's
    # speciality desks use is NOT the compare-suppliers key. products.json
    # already reconciles them: EVIDENCE_BAND maps a compare key to a Clinical
    # Evidence Library band, and that band's own `progress_slug` is the desk
    # slug the tender feed tags its notices with. Both hops come out of the
    # Hub's own files, so no new mapping is invented here.
    bands = products.get("EVIDENCE_BAND") or {}
    highlights = products.get("EVIDENCE_HIGHLIGHTS") or {}

    def tender_slug(sid):
        band = bands.get(sid)
        if not band:
            return None
        return (highlights.get(band) or {}).get("progress_slug")

    # Framework rows, matched to a speciality through the framework names the
    # curated route in compare-suppliers.json already names. Substring match on
    # the framework's own name inside the route line, longest first, so
    # "General Wound Care" is not swallowed by "Wound Care".
    fw_by_name = {}
    for row in frameworks.get("frameworks") or []:
        if row.get("name"):
            fw_by_name[row["name"]] = row
    fw_names = sorted(fw_by_name, key=len, reverse=True)
    signals = extra.get("signals") or []
    cal_rows = calendar.get("rows") or []

    def frameworks_for(route):
        hits, seen = [], set()
        for leg in route:
            line = (leg.get("name") or "").lower()
            for name in fw_names:
                if name.lower() in line and name not in seen:
                    seen.add(name)
                    row = dict(fw_by_name[name])
                    ref = row.get("reference")
                    row["signals"] = [s for s in signals
                                      if (ref and s.get("reference") == ref)
                                      or s.get("name") == name]
                    row["calendar"] = [c for c in cal_rows if c.get("framework") == name]
                    hits.append(row)
                    break
        return hits

    specs = {}
    for sid, block in compare["specialities"].items():
        suppliers = block.get("suppliers") or []
        if not suppliers:
            continue
        out = []
        for s in suppliers:
            name = s.get("ref") or s.get("co")
            key = norm_co(name)
            hits = by_key.get(key) or by_key.get(norm_co(s.get("co"))) or []
            rows = [r for _, rs in hits for r in rs]
            rows.sort(key=lambda r: r.get("date") or "", reverse=True)
            dated = [r.get("date") for r in rows if r.get("date")]
            out.append({
                "co": s.get("co"),
                "ref": s.get("ref"),
                "brands": s.get("brands"),
                "url": s.get("url"),
                "note": s.get("note"),
                "matched": bool(rows),
                "matchedTo": hits[0][0] if hits else None,
                "awardCount": len(rows),
                "firstAward": min(dated) if dated else None,
                "lastAward": max(dated) if dated else None,
                "awards": [{
                    "title": r.get("title"),
                    "buyer": r.get("buyer"),
                    "date": r.get("date"),
                    "url": r.get("url"),
                    "source": r.get("source"),
                    "valueAmount": r.get("valueAmount"),
                    "valueCurrency": r.get("valueCurrency"),
                    "periodEnd": r.get("periodEnd"),
                } for r in rows[:AWARDS_PER_COMPANY]],
            })
        out.sort(key=lambda r: (-r["awardCount"], (r["co"] or "").lower()))
        route = block.get("route") or []
        specs[sid] = {
            "label": block.get("label"),
            "route": route,
            "routeNote": block.get("routeNote"),
            "frameworks": frameworks_for(route),
            "tenderSlug": tender_slug(sid),
            "evidenceBand": bands.get(sid),
            "suppliers": out,
            "supplierCount": len(out),
            "matchedCount": sum(1 for r in out if r["matched"]),
        }

    # THE DIGITAL ARM. A software or diagnostic-software innovator has no
    # competitor set in compare-suppliers.json: the Hub's researched supplier
    # sets are consumable and device categories, and its 'digital' and 'it'
    # keys are deliberately empty. Two files cover it instead, and the report
    # uses them for exactly what each one proves:
    #
    #  - digital-frameworks.json, for the ROUTE. Ten agreements read at their
    #    own GCA, NHS SBS and Find a Tender pages, lot by lot. The lot supplier
    #    LISTS are not carried over: Technology Services 4 Lot 1 alone names
    #    hundreds of IT suppliers, almost none of them health tech, and
    #    printing that as "who already sells here" would be a false competitor
    #    set. The lot's supplier COUNT and its own page URL are carried over,
    #    which is the market-structure fact without the false claim.
    #
    #  - company-digital-awards.json, for the COMPETITORS. Companies that have
    #    actually won a digital NHS award, matched the same way the medical
    #    feed is matched. That is a competitor set an investor can check.
    dig_fw = []
    for row in digital_fw.get("frameworks") or []:
        lots = [{
            "lot": l.get("lot"),
            "name": l.get("name"),
            "note": l.get("note"),
            "supplierCount": len(l.get("suppliers") or []),
        } for l in (row.get("lots") or [])]
        dig_fw.append({
            "name": row.get("name"),
            "reference": row.get("reference"),
            "owner": row.get("owner"),
            "url": row.get("url"),
            "status": row.get("status"),
            "starts": row.get("starts"),
            "ends": row.get("ends"),
            "agreementType": row.get("agreementType"),
            "term": row.get("term"),
            "lots": lots,
            "supplierCount": sum(l["supplierCount"] for l in lots),
        })

    dig_co = []
    for company, rows in (digital_awards.get("companies") or {}).items():
        rows = sorted(rows, key=lambda r: r.get("date") or "", reverse=True)
        dated = [r.get("date") for r in rows if r.get("date")]
        dig_co.append({
            "co": company,
            "matched": True,
            "awardCount": len(rows),
            "firstAward": min(dated) if dated else None,
            "lastAward": max(dated) if dated else None,
            "awards": [{
                "title": r.get("title"),
                "buyer": r.get("buyer"),
                "date": r.get("date"),
                "url": r.get("url"),
                "source": r.get("source"),
                "valueAmount": r.get("valueAmount"),
                "valueCurrency": r.get("valueCurrency"),
                "periodEnd": r.get("periodEnd"),
                "clinical": r.get("clinical"),
            } for r in rows[:AWARDS_PER_COMPANY]],
        })
    dig_co.sort(key=lambda r: (-r["awardCount"], r["co"].lower()))

    #  - digital-lane.json, for WHAT IS MOVING NOW. The medical open-tender feed
    #    is filtered by a Clinical Evidence Library desk slug, and the digital
    #    specialities have no band and so no slug: a digital innovator's
    #    section 6 could only say the feed cannot be filtered for them. This
    #    file is the digital lane of the same two feeds, already walked daily,
    #    so the digital arm gets the same "is this market moving" evidence the
    #    medical arm gets. Its own scopeNote travels with it: a call-off under a
    #    framework is not a notice, so the lane is a floor, not a census.
    dig_open = [{
        "title": n.get("title"),
        "buyer": n.get("buyer"),
        "stage": n.get("stage"),
        "date": n.get("date"),
        "closingDate": n.get("closingDate"),
        "url": n.get("url"),
        "source": n.get("source"),
        "cpv": n.get("cpv"),
        "valueAmount": n.get("valueAmount"),
        "valueCurrency": n.get("valueCurrency"),
    } for n in (digital_lane.get("openNotices") or [])]
    dig_open.sort(key=lambda r: r.get("date") or "", reverse=True)

    dig_eng = [{
        "title": m.get("title"),
        "authority": m.get("authority"),
        "category": m.get("category"),
        "opens": m.get("opens"),
        "deadline": m.get("deadline"),
        "url": m.get("url"),
        "ref": m.get("ref"),
    } for m in (digital_lane.get("marketEngagement") or [])]
    dig_eng.sort(key=lambda r: r.get("deadline") or "", reverse=True)

    other = []
    for row in extra.get("otherBodies") or []:
        r = dict(row)
        r["digital"] = row.get("name") in DIGITAL_ROWS
        other.append(r)
    flagged = sum(1 for r in other if r["digital"])
    unknown = sorted(DIGITAL_ROWS - {r.get("name") for r in other})
    if unknown:
        raise SystemExit(
            "build_innovator_report.py: DIGITAL_ROWS names %d framework(s) that are "
            "no longer in framework-directory-extra.json: %s. Read that file and "
            "update the list — a stale name means the report silently stops "
            "offering a digital route." % (len(unknown), "; ".join(unknown))
        )

    doc = {
        "_notice": NOTICE_PLACEHOLDER,
        "generatedOn": datetime.date.today().isoformat(),
        "rule": (
            "Built by scripts/build_innovator_report.py for the Innovator Market "
            "Analysis Report (app/innovator-report.js). Holds only what that report "
            "cannot read in the browser: the award history of each speciality's "
            "competitor set, reduced from data/company-awards.json (20 MB); the "
            "Stakeholder Mapper's role library, parsed from app/mst-logic.js; a "
            "digital flag on the other-body framework rows; and every source "
            "file's own as-of date, so an unreachable source can still be reported "
            "with its last good reading. Nothing here is computed beyond counts, "
            "earliest and latest dates, and a name match."
        ),
        "awardsPerCompany": AWARDS_PER_COMPANY,
        "matchRule": (
            "A competitor row is tied to a company in company-awards.json by the "
            "normalised form of its `ref` (the master supplier record), falling "
            "back to its `co`. Where no company matches, the row is written with "
            "awardCount 0 and matched false, and the report prints \"No award row "
            "in the Hub's set\" — which is not the same as \"no contracts\", and "
            "the report says so."
        ),
        "digitalRule": DIGITAL_RULE,
        "frameworkMatchRule": (
            "A speciality's NHS Supply Chain framework rows are the rows in "
            "frameworks.json whose own `name` appears inside one of the framework "
            "names in that speciality's curated route in compare-suppliers.json. "
            "Longest name first, so \"General Wound Care\" is not swallowed by "
            "\"Wound Care\". Each row keeps its own Contract Launch Brief URL, and "
            "carries the renewal signals from framework-directory-extra.json and "
            "the NHS Supply Chain procurement-calendar rows that name it."
        ),
        "tenderSlugRule": (
            "The open-tenders.json speciality slug for a speciality is reached in "
            "two hops through products.json, both of them the Hub's own: the "
            "speciality's EVIDENCE_BAND, then that band's own progress_slug in "
            "EVIDENCE_HIGHLIGHTS. A speciality with no band has no slug and the "
            "report says the tender feed cannot be filtered for it, rather than "
            "guessing a slug."
        ),
        "digitalArmRule": (
            "For a software or diagnostic-software product the route comes from "
            "digital-frameworks.json (ten agreements read at their own GCA, NHS SBS "
            "and Find a Tender pages) and the competitor set from "
            "company-digital-awards.json (companies that have won a digital NHS "
            "award). The framework lots' supplier lists are deliberately NOT "
            "carried into the report: Technology Services 4 Lot 1 alone names "
            "hundreds of IT suppliers, almost none of them health tech, so "
            "printing that list as \"who already sells here\" would be a false "
            "competitor set. Each lot's supplier count and its own page URL are "
            "shown instead."
        ),
        "signals": signals,
        "procurementCalendar": {
            "pageLastUpdated": calendar.get("pageLastUpdated"),
            "count": calendar.get("count"),
        },
        "digitalFrameworks": dig_fw,
        "digitalOpenNotices": dig_open,
        "digitalMarketEngagement": dig_eng,
        "digitalCompetitors": dig_co,
        "specialityList": [{
            "id": s.get("id"),
            "label": s.get("label"),
        } for s in (products.get("SPECS") or [])],
        "hubPages": HUB_PAGES,
        "sources": {
            "company-awards.json": {
                "dataAsOf": awards.get("dataAsOf"),
                "source": awards.get("source"),
                "sourceUrls": awards.get("sourceUrls"),
                "counts": {k: awards["counts"].get(k) for k in ("companies", "awardRows")},
            },
            "compare-suppliers.json": {
                "verifiedOn": compare.get("verifiedOn"),
                "sourceRule": compare.get("sourceRule"),
            },
            "frameworks.json": {
                "dataAsOf": frameworks.get("dataAsOf"),
                "source": frameworks.get("source"),
                "frameworkCount": frameworks.get("frameworkCount"),
            },
            "framework-directory-extra.json": {
                "checkedAt": extra.get("otherBodiesCheckedAt"),
                "rule": extra.get("rule"),
                "rowCount": len(other),
                "digitalCount": flagged,
            },
            "icb-watch.json": {
                "asOf": icbwatch.get("asOf"),
                "leadersCheckedOn": icbwatch.get("leadersCheckedOn"),
                "count": icbwatch.get("count"),
            },
            "open-tenders.json": {
                "dataAsOf": tenders.get("dataAsOf"),
                "source": tenders.get("source"),
                "openNotices": (tenders.get("counts") or {}).get("openNotices"),
            },
            "pending-awards.json": {
                "dataAsOf": pending.get("dataAsOf"),
                "source": pending.get("source"),
            },
            "digital-frameworks.json": {
                "dataAsOf": digital_fw.get("dataAsOf"),
                "source": digital_fw.get("source"),
                "rule": digital_fw.get("rule"),
                "frameworkCount": len(dig_fw),
            },
            "company-digital-awards.json": {
                "dataAsOf": digital_awards.get("dataAsOf"),
                "source": digital_awards.get("source"),
                "laneRule": digital_awards.get("laneRule"),
                "counts": {k: (digital_awards.get("counts") or {}).get(k)
                           for k in ("companies", "awardRows")},
            },
            "digital-lane.json": {
                "dataAsOf": digital_lane.get("dataAsOf"),
                "source": digital_lane.get("source"),
                "laneRule": digital_lane.get("laneRule"),
                "scopeNote": digital_lane.get("scopeNote"),
                "openNotices": len(dig_open),
                "marketEngagement": len(dig_eng),
            },
            "nhssc-procurement-calendar.json": {
                "pageLastUpdated": calendar.get("pageLastUpdated"),
                "source": "NHS Supply Chain, procurement calendar page, as fetched by "
                          "scripts/refresh_nhssc_procurement_calendar.py",
            },
            "trust-pressures.json": {
                "asOf": pressures.get("asOf"),
                "sources": {k: v.get("label") for k, v in (pressures.get("sources") or {}).items()},
            },
            "products.json": {
                "note": "The Hub's own speciality list, product and problem list, framework "
                        "family map, national priority map and Clinical Evidence Library "
                        "highlights — the same records behind the Hub's Stakeholder "
                        "Mapper and Value Equation. Human-curated; no automation writes it.",
            },
            "app/mst-logic.js": {
                "note": "The Hub's Stakeholder Mapper. Its role library is read straight out "
                        "of the tool, so the roles in this report and the roles a member sees "
                        "in the mapper cannot drift apart.",
            },
        },
        "stakeholderRoles": roles,
        "stakeholderTemplates": tpl,
        "otherBodies": other,
        "specialities": specs,
    }
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the file on disk differs from a fresh build")
    a = ap.parse_args()
    doc = build()
    if a.check:
        try:
            with open(OUT, encoding="utf-8") as fh:
                have = json.load(fh)
        except OSError:
            print("data/innovator-report.json is missing. Run this script.")
            return 1
        doc["_notice"] = have.get("_notice")
        doc["generatedOn"] = have.get("generatedOn")
        if json.dumps(have, sort_keys=True) != json.dumps(doc, sort_keys=True):
            print("data/innovator-report.json is stale. Run this script, then "
                  "scripts/stamp_notice.py.")
            return 1
        print("data/innovator-report.json is current.")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")
    n = len(doc["specialities"])
    rows = sum(len(v["suppliers"]) for v in doc["specialities"].values())
    matched = sum(v["matchedCount"] for v in doc["specialities"].values())
    print("data/innovator-report.json: %d specialities, %d competitor rows, "
          "%d with an award row, %d stakeholder roles, %d other-body frameworks "
          "(%d digital), %.1f MB"
          % (n, rows, matched, len(doc["stakeholderRoles"]), len(doc["otherBodies"]),
             sum(1 for r in doc["otherBodies"] if r["digital"]),
             os.path.getsize(OUT) / 1e6))
    print("Now run: python3 scripts/stamp_notice.py  (then bash scripts/gate.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
