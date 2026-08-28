#!/usr/bin/env python3
"""
Atamis Health Family: NHS opportunity archive, pulled once per day.

Atamis is the NHS's single eCommercial system. Its public opportunity search
exposes an undocumented CSV endpoint that returns the ENTIRE result set in one
request (the `page` parameter is ignored), which is why this script makes exactly
one HTTP call per run rather than paging 500+ times.

WHY THIS SOURCE EARNS ITS PLACE
-------------------------------
For any above-threshold notice, Find a Tender carries strictly more detail
(value, CPV, contract dates, award criteria, ODS and PPON codes, structured
OCDS). Atamis does not compete with that and this script does not pretend it
does. What Atamis carries that Find a Tender does not:

  * market engagement notices, expressions of interest and pre-engagement
  * framework FURTHER COMPETITIONS (mini-competitions), which are not notifiable
    under the Procurement Act 2023 and therefore need never appear on FTS

For a rep already on a framework, a mini-competition is the most actionable
signal there is. That is what this script is mined for, and the output is
classified accordingly rather than dumped as a generic tender feed.

WHAT IS NOT HERE
----------------
The public Atamis data has NO supplier name, NO contract value, NO CPV code and
NO contract end date. Those fields exist in Atamis (Valid To, Extension Terms,
Estimated Value, Supplier) but sit behind supplier login. Do not imply the Hub
has them from this source. Contract end dates come from Find a Tender instead:
see scripts/refresh_framework_awards.py.

ACCESS POSITION (decided by Lou, 28/08/2026)
--------------------------------------------
The search site's robots.txt is `Disallow: /` for all agents except Googlebot.
The Atamis Browser Terms of Use §6.1 state that public-website content may be
published under the Open Government Licence and "You may reproduce content
published on the Public Website under the OGL", and §10.1.1 prohibits only
crawling "that impairs or disrupts the Facilities". Those two point in opposite
directions. Lou's decision was to proceed at ONE request per day: a single CSV
pull replaces ~514 page fetches, which is the least burdensome possible access
pattern and cannot plausibly impair the service. If that position is ever
revisited, this script is the only thing to turn off.

Usage:
    python3 scripts/refresh_atamis.py
    python3 scripts/refresh_atamis.py --dry-run   # fetch and report, write nothing
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CSV_URL = (
    "https://health-family-contract-search.secure.force.com/ProSpend__CS_DownloadCSV"
    "?SearchType=Projects&searchStr=&sortStr=Recently+Published&page=1&filters=&County="
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
OUT = os.path.join(DATA, "atamis-opportunities.json")

UA = "Elevate-and-Thrive-Hub/1.0 (Medical Sales Intelligence Hub; contact@elevateandthrive.uk)"

EXPECTED_HEADER = [
    "Name", "Contract Ref", "Contracting Authority", "Description",
    "Category", "Open On (dd/mm/yyyy)", "Response Deadline (dd/mm/yyyy)",
    "Time Remaining",
]

# Classification rules. Stated here so the derived label can be judged
# (root CLAUDE.md rule 14).
PRE_MARKET_RE = re.compile(
    r"\b(market engagement|pre-?engagement|expression of interest|\bEOI\b|"
    r"soft market|market sounding|prior information|request for information|\bRFI\b)\b",
    re.I,
)
FURTHER_COMP_RE = re.compile(
    r"\b(further competition|mini-?competition|call-?off|call off|"
    r"framework (?:mini|further))\b",
    re.I,
)

# A minimum floor before we believe the pull at all. The archive held 5,135
# live results on 28/08/2026; anything under this means a broken or truncated
# response, and we would rather write nothing than overwrite a good store.
MIN_PLAUSIBLE_ROWS = 500


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, tries: int = 3) -> bytes | None:
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == tries:
                log("  FETCH FAILED after %d tries: %s" % (tries, exc))
                return None
            time.sleep(5 * attempt)
    return None


def parse_uk_date(v: str) -> str | None:
    """dd/mm/yyyy (optionally with a time) to ISO. Returns None if unparseable."""
    if not v:
        return None
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", v)
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


def classify(name: str, desc: str, route: str = "") -> list[str]:
    """Label an opportunity. A record can carry more than one label."""
    blob = " ".join([name or "", desc or "", route or ""])
    labels = []
    if PRE_MARKET_RE.search(blob):
        labels.append("pre_market_engagement")
    if FURTHER_COMP_RE.search(blob):
        labels.append("framework_further_competition")
    return labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, but write nothing")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    log("Atamis Health Family opportunities  %s" % now.isoformat(timespec="seconds"))
    log("  one request per day, by design. See the module docstring.")

    raw = fetch(CSV_URL)
    if raw is None:
        log("FAILED: no response. Existing store left untouched.")
        return 1

    text = raw.decode("utf-8-sig", errors="replace")

    # The CSV has unescaped quotes and embedded newlines in Description.
    # csv.reader handles embedded newlines inside quoted fields; the stray
    # quotes are absorbed rather than allowed to shift every later column,
    # and any row with the wrong column count is counted and skipped rather
    # than silently mangled.
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        log("FAILED: empty response. Existing store left untouched.")
        return 1

    header = [h.strip().lstrip("﻿") for h in header]
    if header[:3] != EXPECTED_HEADER[:3]:
        log("FAILED: unexpected CSV header, the endpoint has changed.")
        log("  got: %s" % header[:8])
        log("  expected to start: %s" % EXPECTED_HEADER[:3])
        log("  Nothing written, so nothing is silently corrupted.")
        return 1

    # The export writes NINE fields per row but names only eight in the header.
    # The unnamed ninth is Procurement Route ("PA23 Open Procedure", "PA23 Below
    # Threshold", "PSR Competitive Process", "PA23 Framework - Further
    # Competition"...), which is the single most useful field in the file for our
    # purposes and is blank on roughly half the rows. Naming it here recovers it.
    #
    # Short rows are genuine breakage: Description contains raw newlines that
    # sometimes fall outside the quoting, splitting one record across several.
    # Those are counted and skipped rather than mangled into the wrong columns.
    if len(header) == 8:
        header = header + ["Procurement Route"]
    ncols = len(header)

    rows = []
    malformed = 0
    for row in reader:
        if not any(c.strip() for c in row):
            continue
        if len(row) > ncols:
            row = row[:ncols]
        elif len(row) < ncols:
            malformed += 1
            continue
        rows.append(dict(zip(header, [c.strip() for c in row])))

    log("  parsed %d rows (%d broken rows skipped)" % (len(rows), malformed))

    if len(rows) < MIN_PLAUSIBLE_ROWS:
        log("FAILED: only %d rows, below the %d floor. This looks like a truncated"
            % (len(rows), MIN_PLAUSIBLE_ROWS))
        log("        or blocked response. Existing store left untouched.")
        return 1

    records = {}
    for r in rows:
        ref = r.get("Contract Ref", "").strip()
        if not ref:
            continue
        name = r.get("Name", "").strip()
        desc = r.get("Description", "").strip()
        route = r.get("Procurement Route", "").strip()
        labels = classify(name, desc, route)
        rec = {
            "ref": ref,
            "name": name,
            "authority": r.get("Contracting Authority", "").strip(),
            "description": desc[:1200],
            "category": r.get("Category", "").strip(),
            "procurement_route": route,
            "opens": parse_uk_date(r.get("Open On (dd/mm/yyyy)", "")),
            "deadline": parse_uk_date(r.get("Response Deadline (dd/mm/yyyy)", "")),
            "time_remaining": r.get("Time Remaining", "").strip(),
            "labels": labels,
            "url": ("https://health-family-contract-search.secure.force.com/"
                    "?searchtype=Projects&searchStr=" + urllib.parse.quote(ref)),
        }
        records[ref] = rec

    # ---- merge with the existing store, tracking what is genuinely new ----
    store: dict[str, dict] = {}
    first_seen: dict[str, str] = {}
    if os.path.exists(OUT):
        try:
            with open(OUT) as fh:
                prev = json.load(fh)
            for rec in prev.get("opportunities", []):
                if rec.get("ref"):
                    store[rec["ref"]] = rec
                    if rec.get("first_seen"):
                        first_seen[rec["ref"]] = rec["first_seen"]
        except (ValueError, OSError) as exc:
            log("  WARNING: existing store unreadable (%s)." % exc)
            log("           Refusing to overwrite it. Fix or move it, then re-run.")
            return 1

    today = now.date().isoformat()
    new_refs = []
    for ref, rec in records.items():
        rec["first_seen"] = first_seen.get(ref, today)
        if ref not in store:
            new_refs.append(ref)
        store[ref] = rec

    # Records that dropped off the live search are kept, marked, not deleted.
    gone = 0
    for ref, rec in store.items():
        if ref not in records:
            if not rec.get("delisted_on"):
                rec["delisted_on"] = today
                gone += 1
        elif rec.get("delisted_on"):
            rec.pop("delisted_on", None)      # reappeared

    opps = sorted(store.values(),
                  key=lambda r: (r.get("opens") or "", r.get("ref")), reverse=True)

    pre_market = [o for o in opps if "pre_market_engagement" in (o.get("labels") or [])]
    further = [o for o in opps if "framework_further_competition" in (o.get("labels") or [])]
    live = [o for o in opps if not o.get("delisted_on")]

    out = {
        "source": "Atamis Health Family public opportunity search",
        "source_url": "https://health-family-contract-search.secure.force.com/?searchtype=Projects",
        "generated": now.isoformat(timespec="seconds"),
        "access_note": (
            "One request per day. The endpoint returns the whole result set in a "
            "single response, so this is the least burdensome access pattern "
            "available. See the script docstring for the robots.txt / OGL position."
        ),
        "field_caveat": (
            "The public Atamis data carries NO supplier name, NO contract value, NO "
            "CPV code and NO contract end date. Those fields exist in Atamis but are "
            "behind supplier login. Contract end dates come from Find a Tender: see "
            "data/framework-awards.json."
        ),
        "classification_rule": (
            "pre_market_engagement: title or description matches market engagement, "
            "pre-engagement, expression of interest, EOI, soft market, market sounding, "
            "prior information, request for information or RFI. "
            "framework_further_competition: the title, description or Procurement Route "
            "matches further competition, mini-competition, call-off or framework "
            "mini/further. A record may carry both labels or neither. Procurement "
            "Route is the unnamed ninth CSV column, recovered by this script."
        ),
        "counts": {
            "total_held": len(opps),
            "live_on_last_run": len(live),
            "new_this_run": len(new_refs),
            "newly_delisted_this_run": gone,
            "pre_market_engagement": len(pre_market),
            "framework_further_competition": len(further),
            "distinct_authorities": len({o.get("authority") for o in opps if o.get("authority")}),
            "broken_rows_skipped": malformed,
        },
        "opportunities": opps,
    }

    if args.dry_run:
        log("  DRY RUN, nothing written.")
        log("  would hold %d (%d new, %d newly delisted)"
            % (len(opps), len(new_refs), gone))
        log("  pre-market %d | further competition %d"
            % (len(pre_market), len(further)))
        return 0

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    log("")
    log("  store now %d opportunities (%d live, %d new this run, %d newly delisted)"
        % (len(opps), len(live), len(new_refs), gone))
    log("  pre-market engagement %d | framework further competition %d"
        % (len(pre_market), len(further)))
    log("  distinct authorities: %d" % out["counts"]["distinct_authorities"])
    log("  wrote data/atamis-opportunities.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
