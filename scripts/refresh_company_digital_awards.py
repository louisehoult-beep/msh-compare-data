#!/usr/bin/env python3
"""Attach digital-lane award notices to Hub companies: data/company-digital-awards.json.

WHY A SEPARATE FILE (20/10/2026)
--------------------------------
data/company-awards.json is the CPV 33 medical feed (scripts/refresh_awards.py,
CPV_MEDICAL_PREFIX "33"). It deliberately excludes software and IT, and
verify.py's check_digital_lane() keeps it that way: no lane row may be written
into it. So until today a software award to a health tech company reached no
company report at all, and a digital company's report read as if it had won
nothing.

This file is the digital twin of that one, built from data/digital-lane.json
(NHS buyer AND a CPV 48 or 72 code, the lane rule printed in that file). It
does not touch company-awards.json, and the company report shows it in its own
section, labelled as software and IT notices, so a reader never mistakes a
payroll licence for a clinical device award.

THE MATCH RULE IS THE SAME ONE, NOT A COPY
------------------------------------------
Every supplier name on a lane award is resolved by scripts/company_match.py,
the exact-only rule refresh_awards.py uses, and verify.py re-derives every
published match independently. A name that matches no company, or two, is
quarantined in `unmatched` / `ambiguous`, never guessed.

APPEND-ONLY, LIKE THE MEDICAL FEED
----------------------------------
An award is a dated historical fact. digital-lane.json holds the notices of its
own walk, so rows already published here are carried forward and re-resolved
against today's seed on every run. A row is dropped only when its supplier name
no longer resolves (an alias was corrected), and then it moves to `unmatched`.

A notice that is ALSO in company-awards.json for the same company (a buyer can
code one notice to CPV 33 and to 48) is not repeated here: the medical feed
already carries it.

USAGE
    python3 scripts/refresh_company_digital_awards.py          # write
    python3 scripts/refresh_company_digital_awards.py --check  # report only
Stdlib only, no network.
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import company_match  # noqa: E402

ROOT = os.path.dirname(HERE)
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
LANE = os.path.join(ROOT, "data", "digital-lane.json")
MEDICAL = os.path.join(ROOT, "data", "company-awards.json")
OUT = os.path.join(ROOT, "data", "company-digital-awards.json")
FRAMEWORKS = os.path.join(ROOT, "data", "digital-frameworks.json")

SECTION_RULE = (
    "Software and IT notices only. Each row is one supplier named on one Find a Tender "
    "or Contracts Finder award notice that an NHS buyer classified under a Common "
    "Procurement Vocabulary (CPV) code beginning 48 (software packages and information "
    "systems) or 72 (IT services). Those codes cover payroll, finance and office "
    "systems as much as clinical ones, so a row is not a claim of health technology. "
    "A row is counted as clinical only where the notice title names a clinical "
    "system. Medical device awards (CPV division 33) appear in the award sections "
    "above and are never repeated here."
)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def source_of(url):
    u = str(url or "")
    if "contractsfinder" in u:
        return "Contracts Finder"
    if "find-tender" in u:
        return "Find a Tender"
    return "award notice"


def row_key(r):
    return (r.get("url") or "", company_match.norm(r.get("noticeSupplierName")))


def rows_from_lane(lane):
    out = []
    for a in (lane or {}).get("awards") or []:
        if a.get("stage") != "award":
            continue
        names = [n for n in (a.get("suppliers") or []) if str(n or "").strip()]
        for n in names:
            value = a.get("value")
            out.append({
                "title": a.get("title"),
                "buyer": a.get("buyer"),
                "date": a.get("published"),
                "url": a.get("url"),
                "ocid": a.get("ocid"),
                "source": source_of(a.get("url")),
                "valueAmount": value if isinstance(value, (int, float)) else None,
                "valueCurrency": "GBP" if isinstance(value, (int, float)) else None,
                "periodEnd": a.get("contractEnd"),
                "isFramework": bool(a.get("isFramework")),
                "digitalCpv": list(a.get("digitalCpv") or []),
                "clinical": bool(a.get("clinical")),
                "lane": "digital",
                "noticeSupplierName": n,
                "noticeSupplierCount": len(names),
            })
    return out


def medical_keys(medical):
    keys = set()
    for company, rows in ((medical or {}).get("companies") or {}).items():
        for r in rows or []:
            keys.add((company, r.get("url") or ""))
    return keys


def framework_index(frameworks):
    """{normalised key: framework record} from data/digital-frameworks.json.

    Keyed on the agreement reference AND on the agreement name, because a notice
    states one or the other and sometimes only the name: West Hertfordshire's award
    says "via G-Cloud 12 Digital Marketplace ID ... Framework" and gives no RM
    number, so the name is the only key it can be matched on.
    """
    index = {}
    for f in (frameworks or {}).get("frameworks") or []:
        for key in (f.get("reference"), f.get("name")):
            k = str(key or "").strip().casefold()
            if k:
                index.setdefault(k, f)
    return index


def attach_framework(row, index):
    """Add the framework's own status and term to a row that states its route.

    WHY (16/11/2026). The route a call-off was bought through is only half the
    fact. The half a rep acts on is whether that framework is still open: a
    call-off on a closed agreement runs to its own end date and nothing on it rolls
    forward, so the contract end IS the decision date. Medilogik's Barnsley award
    is a G-Cloud 13 call-off ending 30/11/2026 on an agreement that expired in
    November 2024.

    The framework facts are read from data/digital-frameworks.json every run, so
    they never go stale in this file. A route naming a framework the Hub holds no
    record of is left exactly as the notice stated it; nothing is invented.
    """
    # Cleared first, so a framework record that has gone from
    # data/digital-frameworks.json does not leave its facts behind on the row.
    for k in ("frameworkStatus", "frameworkStarts", "frameworkEnds", "frameworkUrl",
              "frameworkOwner", "frameworkCallOffRule"):
        row.pop(k, None)
    if row.pop("frameworkRefSource", None):
        row["frameworkRef"] = None
    for key in (row.get("frameworkRef"), row.get("frameworkName")):
        f = index.get(str(key or "").strip().casefold())
        if not f:
            continue
        row["frameworkStatus"] = f.get("status")
        row["frameworkStarts"] = f.get("starts")
        row["frameworkEnds"] = f.get("ends")
        row["frameworkUrl"] = f.get("url")
        row["frameworkOwner"] = f.get("owner")
        if f.get("callOffRule"):
            row["frameworkCallOffRule"] = f["callOffRule"]
        # The notice gave a name but no reference, and the Hub's own record has
        # one. Record it as the Hub's, not as something the notice said.
        if not row.get("frameworkRef") and f.get("reference"):
            row["frameworkRefSource"] = ("the Hub's own record of %s; the notice names the "
                                         "framework but gives no agreement number."
                                         % f.get("name"))
            row["frameworkRef"] = f.get("reference")
        return row
    return row


def build(seed, lane, medical, previous, frameworks=None):
    index = company_match.build_index(seed)
    seed_names = {s.get("name") for s in (seed or {}).get("suppliers") or []}
    med = medical_keys(medical)

    # Previous published, unmatched and ambiguous rows, plus today's lane rows.
    pool, seen = [], set()
    prev = previous or {}
    carried = [r for rows in (prev.get("companies") or {}).values() for r in rows or []]
    carried += list(prev.get("unmatched") or []) + list(prev.get("ambiguous") or [])
    for r in rows_from_lane(lane) + carried:
        k = row_key(r)
        if k in seen:
            continue
        seen.add(k)
        r = {f: v for f, v in r.items() if f not in ("company", "matchedOn", "reason")}
        pool.append(r)

    fw_index = framework_index(frameworks)
    companies, unmatched, ambiguous, in_medical = {}, [], [], 0
    for r in pool:
        if r.get("frameworkRef") or r.get("frameworkName"):
            attach_framework(r, fw_index)
        company, state, reason = company_match.resolve(r.get("noticeSupplierName"), index)
        if state == "confirmed" and company in seed_names:
            if (company, r.get("url") or "") in med:
                in_medical += 1
                continue
            r["company"] = company
            r["matchedOn"] = reason
            companies.setdefault(company, []).append(r)
        elif state == "ambiguous":
            r["reason"] = reason
            ambiguous.append(r)
        else:
            r["reason"] = reason
            unmatched.append(r)

    for rows in companies.values():
        rows.sort(key=lambda r: (r.get("date") or "", r.get("url") or ""), reverse=True)
    unmatched.sort(key=lambda r: (r.get("date") or "", r.get("url") or ""), reverse=True)
    ambiguous.sort(key=lambda r: (r.get("date") or "", r.get("url") or ""), reverse=True)

    attached = sum(len(v) for v in companies.values())
    doc = {
        "_notice": prev.get("_notice") or (lane or {}).get("_notice"),
        "lane": "digital",
        "dataAsOf": (lane or {}).get("dataAsOf"),
        "generated": datetime.date.today().isoformat(),
        "source": ("Find a Tender and Contracts Finder award notices in the Hub's digital "
                   "lane (data/digital-lane.json), Open Government Licence v3."),
        "sectionRule": SECTION_RULE,
        "laneRule": (lane or {}).get("laneRule"),
        "clinicalRule": (lane or {}).get("clinicalRule"),
        "matchRule": company_match.RULE,
        "coverage": {
            "complete": False,
            "note": ("Only award notices the digital lane has read are here. Most NHS digital "
                     "money moves as framework call-offs, which publish no notice of their "
                     "own, so an empty section says what this index holds, not what a "
                     "company has won."),
            "laneCoverage": (lane or {}).get("coverage"),
        },
        "counts": {
            "companies": len(companies),
            "awardRows": attached,
            "unmatched": len(unmatched),
            "ambiguous": len(ambiguous),
            "alreadyInMedicalFeed": in_medical,
        },
        "companies": dict(sorted(companies.items())),
        "unmatched": unmatched,
        "ambiguous": ambiguous,
    }
    if not doc["_notice"]:
        doc.pop("_notice")
    return doc


def main():
    check = "--check" in sys.argv
    seed, lane = load(SEED), load(LANE)
    if not seed or not lane:
        raise SystemExit("cannot read %s or %s" % (SEED, LANE))
    doc = build(seed, lane, load(MEDICAL, {}), load(OUT, {}), load(FRAMEWORKS, {}))
    c = doc["counts"]
    print("company-digital-awards: %d rows on %d companies, %d unmatched, %d ambiguous, "
          "%d already in the medical feed" % (c["awardRows"], c["companies"], c["unmatched"],
                                              c["ambiguous"], c["alreadyInMedicalFeed"]))
    if check:
        return
    prev = load(OUT)
    if prev is not None:
        a = dict(prev, generated=None)
        b = dict(doc, generated=None)
        if a == b:
            print("unchanged, not written")
            return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
