#!/usr/bin/env python3
"""
Find a Tender (OCDS) framework awards: who is on which framework, and when it ends.

Find a Tender publishes every above-threshold UK procurement notice as OCDS 1.1
JSON at an open, unauthenticated endpoint:

  https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages

Under the Procurement Act 2023 (mandatory for procurements commencing on or after
24/02/2025) this carries three things the Hub could not previously assemble:

  * the full NAMED SUPPLIER LIST on a framework award, each with a Companies House
    number (GB-COH-...) and/or a PPON (GB-PPON-...), so entity resolution is a code
    join rather than fuzzy name matching
  * contracts[].period.endDate      when the contract actually ends
  * contracts[].period.maxExtentDate  how far it could be extended

This script pulls a rolling window, keeps only health-relevant releases under a
stated rule, and merges them into data/framework-awards.json by OCID.

THE HEALTH-RELEVANCE RULE (root CLAUDE.md rule 14: state the rule in the file)
-----------------------------------------------------------------------------
A release is health-relevant if EITHER:
  (a) the buyer name matches an NHS-specific pattern: contains "NHS", or
      "Integrated Care Board", or "Health Board", or ends "Foundation Trust"
      where "NHS" also appears; or
  (b) any CPV code on the notice begins 33 (medical equipments, pharmaceuticals
      and personal care products) or 851 (health services).

Bare "Trust" is deliberately NOT a match: academy trusts and housing trusts flood
the feed and would produce false positives. CPV 852 (veterinary) and 853 (social
work) are deliberately excluded. Both decisions are recorded in the output file.

WHAT THIS DATA DOES AND DOES NOT PROVE
--------------------------------------
A supplier named on a framework award is evidence they CAN sell through that
framework. It is NOT evidence of uptake, volume or market share at any trust.
The Hub must never convert this into a share claim. The output carries this
caveat in the file itself so it travels with the data.

Usage:
    python3 scripts/refresh_framework_awards.py                # last 14 days
    python3 scripts/refresh_framework_awards.py --days 90
    python3 scripts/refresh_framework_awards.py --from 2025-02-24 --to 2025-04-01
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
OUT = os.path.join(DATA, "framework-awards.json")

UA = "Elevate-and-Thrive-Hub/1.0 (Medical Sales Intelligence Hub; contact@elevateandthrive.uk)"

NHS_PATTERNS = (
    re.compile(r"\bNHS\b", re.I),
    re.compile(r"\bIntegrated Care Board\b", re.I),
    re.compile(r"\bHealth Board\b", re.I),
)

MAX_PAGES = 400          # backstop against a runaway cursor loop


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch_json(url: str, tries: int = 4):
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429) and attempt < tries:
                wait = 30 * attempt
                log("    %s, backing off %ds" % (exc.code, wait))
                time.sleep(wait)
                continue
            log("    HTTP %s: %s" % (exc.code, url[:110]))
            return None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            if attempt == tries:
                log("    FETCH FAILED: %s (%s)" % (url[:110], exc))
                return None
            time.sleep(4 * attempt)
    return None


# --------------------------------------------------------------------------

def all_cpv(release: dict) -> list[str]:
    """Every CPV code anywhere on the release."""
    out: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("scheme") == "CPV" and node.get("id"):
                out.append(str(node["id"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(release)
    return out


def is_health(release: dict, cpvs: list[str]) -> tuple[bool, str]:
    """Apply the stated health-relevance rule. Returns (match, reason)."""
    buyer = (release.get("buyer") or {}).get("name") or ""
    for pat in NHS_PATTERNS:
        if pat.search(buyer):
            return True, "buyer_name"
    for c in cpvs:
        if c.startswith("33"):
            return True, "cpv_33_medical"
        if c.startswith("851"):
            return True, "cpv_851_health_services"
    return False, ""


def org_ids(party: dict) -> dict:
    """Pull the useful identifiers off a supplier/buyer object."""
    out = {"name": party.get("name")}
    ident = party.get("id") or ""
    if ident.startswith("GB-COH-"):
        out["companies_house"] = ident[len("GB-COH-"):]
    elif ident.startswith("GB-PPON-"):
        out["ppon"] = ident[len("GB-PPON-"):]
    if ident and "companies_house" not in out and "ppon" not in out:
        out["identifier"] = ident
    return out


def iso_date(v):
    """Trim an OCDS datetime to a plain ISO date."""
    if not v or not isinstance(v, str):
        return None
    return v[:10]


def extract(release: dict, cpvs: list[str], reason: str) -> dict:
    tender = release.get("tender") or {}
    tech = tender.get("techniques") or {}
    fw = tech.get("frameworkAgreement") or {}

    suppliers = []
    seen = set()
    for award in (release.get("awards") or []):
        for s in (award.get("suppliers") or []):
            key = s.get("id") or s.get("name")
            if key in seen:
                continue
            seen.add(key)
            suppliers.append(org_ids(s))

    contracts = []
    for c in (release.get("contracts") or []):
        period = c.get("period") or {}
        val = c.get("value") or {}
        rec = {
            "start": iso_date(period.get("startDate")),
            "end": iso_date(period.get("endDate")),
            "max_extent": iso_date(period.get("maxExtentDate")),
            "signed": iso_date(c.get("dateSigned")),
        }
        if val.get("amount") is not None:
            rec["value"] = val.get("amount")
            rec["currency"] = val.get("currency")
        if any(rec.values()):
            contracts.append(rec)

    buyer = release.get("buyer") or {}
    rec = {
        "ocid": release.get("ocid"),
        "notice_id": release.get("id"),
        "tag": release.get("tag"),
        "published": iso_date(release.get("date")),
        "title": tender.get("title"),
        "buyer": org_ids(buyer),
        "is_framework": bool(tech.get("hasFrameworkAgreement")),
        "suppliers": suppliers,
        "supplier_count": len(suppliers),
        "contracts": contracts,
        "cpv": sorted(set(cpvs))[:25],
        "matched_by": reason,
        "url": "https://www.find-tender.service.gov.uk/Notice/%s" % (
            (release.get("id") or "").replace("ocds-h6vhtk-", "")),
    }
    if fw:
        rec["framework"] = {
            "method": fw.get("method"),
            "type": fw.get("type"),
            "open_scheme": fw.get("isOpenFrameworkScheme"),
            "scheme_end": iso_date(fw.get("openFrameworkSchemeEndDate")),
        }
    return rec


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14,
                    help="rolling window size in days (default 14)")
    ap.add_argument("--from", dest="dfrom", help="ISO start date, overrides --days")
    ap.add_argument("--to", dest="dto", help="ISO end date")
    ap.add_argument("--limit", type=int, default=100, help="page size (max 100)")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    if args.dfrom:
        start = dt.datetime.fromisoformat(args.dfrom).replace(tzinfo=dt.timezone.utc)
    else:
        start = now - dt.timedelta(days=args.days)
    end = (dt.datetime.fromisoformat(args.dto).replace(tzinfo=dt.timezone.utc)
           if args.dto else now)

    log("Find a Tender framework awards  %s" % now.isoformat(timespec="seconds"))
    log("  window %s to %s" % (start.date(), end.date()))

    params = {
        "updatedFrom": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "updatedTo": end.strftime("%Y-%m-%dT%H:%M:%S"),
        "limit": str(min(args.limit, 100)),
    }
    url = API + "?" + urllib.parse.urlencode(params)

    scanned = 0
    kept: dict[str, dict] = {}
    pages = 0

    while url and pages < MAX_PAGES:
        pkg = fetch_json(url)
        if pkg is None:
            if not kept:
                log("FAILED: could not read the API and nothing was collected.")
                return 1
            log("  stopping early after a fetch failure, keeping what was collected")
            break
        releases = pkg.get("releases") or []
        scanned += len(releases)
        for r in releases:
            cpvs = all_cpv(r)
            ok, reason = is_health(r, cpvs)
            if not ok:
                continue
            rec = extract(r, cpvs, reason)
            if not rec["ocid"]:
                continue
            prev = kept.get(rec["ocid"])
            # keep the richest version of a repeated OCID
            if prev is None or (rec["supplier_count"] > prev["supplier_count"]) \
                    or (len(rec["contracts"]) > len(prev["contracts"])):
                kept[rec["ocid"]] = rec
        pages += 1
        url = (pkg.get("links") or {}).get("next")
        if not releases:
            break
        time.sleep(0.5)

    if pages >= MAX_PAGES:
        log("  NOTE: hit the %d page backstop; window may be truncated." % MAX_PAGES)

    log("  scanned %d releases over %d pages" % (scanned, pages))
    log("  health-relevant kept: %d" % len(kept))

    # ---- merge with the existing store, by OCID -------------------------
    store: dict[str, dict] = {}
    if os.path.exists(OUT):
        try:
            with open(OUT) as fh:
                prev = json.load(fh)
            for rec in prev.get("awards", []):
                if rec.get("ocid"):
                    store[rec["ocid"]] = rec
            log("  existing store: %d awards" % len(store))
        except (ValueError, OSError) as exc:
            log("  WARNING: could not read the existing store (%s)." % exc)
            log("           Refusing to overwrite it. Fix or move it, then re-run.")
            return 1

    added = updated = 0
    for ocid, rec in kept.items():
        if ocid not in store:
            store[ocid] = rec
            added += 1
        elif rec["supplier_count"] >= store[ocid].get("supplier_count", 0):
            store[ocid] = rec
            updated += 1

    awards = sorted(store.values(), key=lambda r: (r.get("published") or ""), reverse=True)

    # ---- invariants (root CLAUDE.md rule 14) ----------------------------
    problems = []
    for rec in awards:
        if rec.get("supplier_count") != len(rec.get("suppliers") or []):
            problems.append("supplier_count mismatch on %s" % rec.get("ocid"))
        for c in rec.get("contracts") or []:
            if c.get("end") and c.get("max_extent") and c["max_extent"] < c["end"]:
                problems.append("maxExtent before end on %s" % rec.get("ocid"))
            if c.get("start") and c.get("end") and c["end"] < c["start"]:
                problems.append("end before start on %s" % rec.get("ocid"))
    if problems:
        log("  INVARIANT FAILURES (%d), nothing written:" % len(problems))
        for p in problems[:10]:
            log("    %s" % p)
        return 1

    frameworks = [a for a in awards if a.get("is_framework")]
    with_suppliers = [a for a in awards if a.get("supplier_count")]
    with_end = [a for a in awards
                if any(c.get("end") for c in (a.get("contracts") or []))]
    with_extent = [a for a in awards
                   if any(c.get("max_extent") for c in (a.get("contracts") or []))]

    out = {
        "source": "Find a Tender Service (OCDS 1.1)",
        "source_url": API,
        "licence": "Open Government Licence",
        "generated": now.isoformat(timespec="seconds"),
        "window_last_run": {"from": start.date().isoformat(), "to": end.date().isoformat()},
        "health_relevance_rule": (
            "Kept if the buyer name matches NHS / Integrated Care Board / Health Board, "
            "or any CPV code begins 33 (medical equipment and pharmaceuticals) or 851 "
            "(health services). Bare 'Trust' is not a match (academy and housing trusts "
            "would flood the feed). CPV 852 (veterinary) and 853 (social work) excluded."
        ),
        "evidence_caveat": (
            "A supplier named on a framework award is evidence they CAN supply through "
            "that framework. It is NOT evidence of uptake, volume or market share at any "
            "trust. Do not convert these records into share-of-market claims."
        ),
        "counts": {
            "awards": len(awards),
            "framework_awards": len(frameworks),
            "with_named_suppliers": len(with_suppliers),
            "with_contract_end_date": len(with_end),
            "with_max_extent_date": len(with_extent),
            "distinct_buyers": len({(a.get("buyer") or {}).get("name") for a in awards}),
        },
        "awards": awards,
    }

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    log("")
    log("  added %d, updated %d, store now %d awards" % (added, updated, len(awards)))
    log("  frameworks %d | named suppliers %d | end dates %d | max-extent %d"
        % (len(frameworks), len(with_suppliers), len(with_end), len(with_extent)))
    log("  wrote data/framework-awards.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
