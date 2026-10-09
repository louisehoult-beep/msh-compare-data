#!/usr/bin/env python3
"""MHRA device safety alerts — the source for the MHRA / SaMD Regulatory Desk.

WHAT THIS IS, AND WHY IT IS SEPARATE FROM THE EXISTING mhra_alerts SOURCE
---------------------------------------------------------------------------
cloud-pipeline/sources.py already fetches MHRA's gov.uk feed for page 675's
static "MHRA ALERTS & RECALLS" panel and page 2180's "Safety notice · recall"
signal row — but both read only the flat search-API fields (title, link,
date, description) and cap at 2 rows on 2180. Scoped as "proposal 2" in the
26/08/2026 Hub gap audit: a full, filterable, company/speciality-tagged log,
each row with a fixed "why it matters now" line for the alert's type. This
file is that fuller feed. It does not replace sources.py's mhra_alerts entry
— 675 and 2180 keep working exactly as they do today.

THE SOURCE (public, no key) — the SAME endpoint sources.py already uses
--------------------------------------------------------------------------
List:    https://www.gov.uk/api/search.json
             ?filter_format=medical_safety_alert&order=-public_timestamp
             &count=100&start=<n>&fields=title,link,public_timestamp,description
Detail:  https://www.gov.uk/api/content<link>
             — adds details.metadata.alert_type, .medical_specialism,
             .issued_date, and the full body (used for company-name
             extraction only, see below).

SCOPE — DEVICE-RELEVANT ALERT TYPES ONLY
-------------------------------------------
Confirmed by probing the content API across a 40-item sample (26/08/2026):
alert_type takes distinct values for each alert family —
    device-safety-information   individual DSI-numbered device alerts
    national-patient-safety     NatPSA-numbered, device-relevant
    medicines-recall-notification / medicines-defect-notification
                                 drug batch issues — NOT devices, excluded
    mhra-safety-round-up        a monthly digest of the above — excluded,
                                 its content already appears as the
                                 individual DSI/NatPSA items themselves
    field-safety-notices        a weekly digest LISTING many manufacturers'
                                 own FSNs inside one page body — excluded
                                 from v1 (see KNOWN GAP below); it is not
                                 the individual notices this file's schema
                                 expects a company/product to attach to.

KNOWN GAP, STATED PLAINLY: the weekly "Field Safety Notices: X to Y" digest
pages are NOT walked into individual manufacturer notices in this version —
that would mean parsing many separate FSNs out of one page body, a materially
bigger job. Only DSI- and NatPSA-numbered individual alerts are covered.
This file's coverage note says so; it is not silently claimed as complete.

COMPANY EXTRACTION — RESOLVED, NEVER GUESSED
------------------------------------------------
Device alert titles carry a company/brand name inconsistently (e.g. "Dräger
Atlan Anaesthesia workstations...", "Kimal Procedure Packs...", "ResMed
Astral 100 and 150 Ventilators..." all lead with the name; "Cobalt-chrome
modular neck hip replacements..." does not). Rather than inventing a company
from a description, the candidate phrase before the title's first colon is
checked against company_match.resolve() — the SAME alias index
refresh_awards.py already uses. A candidate that does not resolve to exactly
one Hub company is published with company=null, never a guessed name. Per
root rule 8 ("never do half a job"), an unresolved row is still published —
speciality, device, date and link are all real and useful on their own — it
is only the company field that stays "Not verified".

"WHY IT MATTERS" — FIXED PER ALERT TYPE, NEVER INVENTED PER ITEM
----------------------------------------------------------------------
Same discipline as publish_2180.py's SIGNALS table: one fixed rep-facing line
per alert_type, not an LLM-invented note per alert (that would be an
unverifiable claim on every single row). See PLAYS below.

USAGE
    python3 scripts/refresh_mhra_alerts.py                # weekly: last 8 days
    python3 scripts/refresh_mhra_alerts.py --days 30      # catch up after an outage
    python3 scripts/refresh_mhra_alerts.py --dry-run      # fetch, report, write nothing

Then, as for every data file:
    python3 scripts/stamp_notice.py
    python3 verify.py
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match

SEED_PATH = "data/supplier-seed.json"
OUT_PATH = "data/mhra-alerts.json"

UA = {"User-Agent": "MedicalSalesHub/1.0 (+https://elevateandthrive.uk; MHRA regulatory desk)",
      "Accept": "application/json"}

SEARCH_API = "https://www.gov.uk/api/search.json"
CONTENT_API = "https://www.gov.uk/api/content"
NOTICE_BASE = "https://www.gov.uk"

DEFAULT_DAYS = 8
MAX_ITEMS = 400
PAGE_SLEEP = 0.3

ALLOWED_ALERT_TYPES = {"device-safety-information", "national-patient-safety"}

REF_RE = re.compile(r'\(([A-Z]{2,6}/\d{4}/\d+(?:/[A-Z]+)?)\)')

PLAYS = {
    "device-safety-information": (
        "An active MHRA device safety action. Check whether your accounts still hold or use "
        "this device — if it's yours, that's a proactive account-protection call; if it's a "
        "competitor's, this is a live switching conversation this week."
    ),
    "national-patient-safety": (
        "A National Patient Safety Alert — the more serious tier, with a mandated trust "
        "response and deadline. Check whether the affected trusts on your patch have logged "
        "their compliance yet; this is the kind of gap a rep can help close."
    ),
}


def get(url, timeout=60, retries=3):
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503):
                wait = int(exc.headers.get("Retry-After") or 20)
                time.sleep(min(wait, 120) + 1)
                continue
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(3 * attempt)
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(3 * attempt)


def strip_html(body):
    text = re.sub(r"<[^>]+>", " ", body or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


PREFIX_RE = re.compile(
    r'^(UPDATE|National Patient Safety Alert|Device Safety Information)\s*$', re.I)


def company_candidate(title):
    """The title segment that carries a company/brand name, if any is present
    at all — many titles carry none (e.g. "Cobalt-chrome modular neck hip
    replacements: risk of..."), which is a correct, expected outcome, not a
    parsing failure.

    Titles are colon-separated: an alert-type label ("National Patient Safety
    Alert"), then the device/brand segment, then the clinical detail. A title
    with only one colon (no leading label segment) puts the brand first."""
    segments = [s.strip() for s in title.split(":")]
    head = segments[0] if segments else ""
    if PREFIX_RE.match(head) and len(segments) > 1:
        head = segments[1]
    head = REF_RE.sub("", head).strip(" ,-")
    return head


def company_prefixes(candidate):
    """Progressively shorter word-count prefixes of the candidate phrase, to
    try against the EXACT-match alias index — a brand name is often just the
    candidate's first word or two ("Dräger Atlan Anaesthesia workstations" ->
    "Dräger"), never the whole product description. Still exact matching at
    each length, never fuzzy — company_match.resolve() itself stays untouched."""
    words = candidate.split()
    seen, out = set(), []
    for n in range(len(words), 0, -1):
        phrase = " ".join(words[:n])
        if phrase not in seen:
            seen.add(phrase)
            out.append(phrase)
    return out


def fetch_list(days, max_items=MAX_ITEMS):
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days))
    items, start, complete = [], 0, True
    while start < max_items:
        qs = urllib.parse.urlencode({
            "filter_format": "medical_safety_alert", "order": "-public_timestamp",
            "count": 100, "start": start,
            "fields": "title,link,public_timestamp,description"})
        data = get("%s?%s" % (SEARCH_API, qs))
        results = data.get("results", [])
        if not results:
            break
        stop = False
        for r in results:
            ts = r.get("public_timestamp", "")
            try:
                pub = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if pub < cutoff:
                stop = True
                break
            items.append(r)
        start += 100
        if stop:
            break
        time.sleep(PAGE_SLEEP)
    else:
        complete = False
    return items, complete


def enrich(item, index, today_iso):
    link = item.get("link", "")
    title = (item.get("title") or "").strip()
    try:
        detail = get(CONTENT_API + link)
    except Exception:
        return None
    meta = (detail.get("details") or {}).get("metadata") or {}
    alert_type = meta.get("alert_type")
    if alert_type not in ALLOWED_ALERT_TYPES:
        return None
    specialisms = meta.get("medical_specialism") or []
    issued = meta.get("issued_date") or (item.get("public_timestamp") or "")[:10]

    candidate = company_candidate(title)
    company, match_state = None, "no candidate"
    if candidate:
        match_state = "unresolved: %s" % candidate
        for phrase in company_prefixes(candidate):
            resolved, state, reason = company_match.resolve(phrase, index)
            if state == "confirmed":
                company, match_state = resolved, "resolved '%s': %s" % (phrase, reason)
                break

    ref_match = REF_RE.search(title)

    return {
        "title": title,
        "url": NOTICE_BASE + link,
        "alertType": alert_type,
        "reference": ref_match.group(1) if ref_match else None,
        "issuedDate": issued,
        "specialisms": specialisms,
        "company": company,
        "companyMatch": match_state,
        "description": (item.get("description") or "").strip(),
        "play": PLAYS.get(alert_type, ""),
    }


def dedup_key(row):
    return row.get("url", "")


def assemble(rows, existing, window, complete, today):
    kept = {}
    for row in (existing or {}).get("_rows", []):
        kept[dedup_key(row)] = row
    for row in rows:
        kept[dedup_key(row)] = row

    ordered = sorted(kept.values(), key=lambda r: r.get("issuedDate") or "", reverse=True)

    by_type = {}
    for row in ordered:
        by_type[row["alertType"]] = by_type.get(row["alertType"], 0) + 1

    companies = sum(1 for r in ordered if r.get("company"))

    doc = {
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "source": "MHRA device safety alerts, gov.uk drug-device-alerts feed, Open Government Licence v3",
        "sourceUrl": "https://www.gov.uk/drug-device-alerts",
        "scopeRule": (
            "Individual DSI-numbered Device Safety Information alerts and NatPSA-numbered "
            "National Patient Safety Alerts only. Medicines recalls/defect notices are drug "
            "batch issues, not devices, and are excluded. The weekly 'Field Safety Notices: X "
            "to Y' digest pages are NOT walked into their individual manufacturer notices in "
            "this version — that page lists many separate FSNs inside one body, a materially "
            "bigger parsing job than this file does. This is a stated coverage gap, not a "
            "claim of completeness."
        ),
        "companyRule": (
            "A company is only ever attached when the phrase before the title's first colon "
            "resolves, via the same alias index refresh_awards.py uses, to exactly one Hub "
            "company. An alert with no resolvable company still publishes with company=null — "
            "device, speciality, date and link are real and useful without it. Never a guess."
        ),
        "coverage": {
            "complete": bool(complete),
            "window": window,
            "note": ("Alerts indexed from the two allowed alert types over the window listed. "
                     "An absence here is a statement about this index, never about a supplier."
                     if complete else
                     "⚠️ INCOMPLETE — the walk stopped before the window was exhausted. "
                     "Re-run with a shorter window."),
        },
        "counts": {
            "alerts": len(ordered),
            "byAlertType": by_type,
            "withCompanyResolved": companies,
        },
        "alerts": ordered,
        "_rows": ordered,
    }
    windows = ((existing or {}).get("windows") or [])
    if window:
        windows = (windows + [window])[-60:]
    doc["windows"] = windows
    return doc


def load(path, default=None):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def write(doc, path=OUT_PATH):
    with open(path, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    seed = load(SEED_PATH, {"suppliers": []})
    index = company_match.build_index(seed)
    existing = load(OUT_PATH)
    today = dt.date.today()
    today_iso = today.isoformat()
    window = {"from": (today - dt.timedelta(days=args.days)).isoformat(),
              "to": today_iso, "days": args.days, "run": today_iso}

    raw_items, complete = fetch_list(args.days)
    print("  fetched %d candidate item(s) from the search API" % len(raw_items))

    rows = []
    for item in raw_items:
        row = enrich(item, index, today_iso)
        if row:
            rows.append(row)
        time.sleep(PAGE_SLEEP)

    doc = assemble(rows, existing, window, complete, today)
    print("\n%d device-relevant alert(s) held (%d with a resolved company). By type: %s"
          % (doc["counts"]["alerts"], doc["counts"]["withCompanyResolved"],
             doc["counts"]["byAlertType"]))

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    write(doc)
    print("\nwrote %s. Now: python3 scripts/stamp_notice.py && python3 verify.py" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
