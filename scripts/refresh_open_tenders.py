#!/usr/bin/env python3
"""Live/open NHS-medical tender and pipeline notices — the forward-looking
companion to Tender History (data/company-awards.json, WP page 3198).

WHAT THIS IS, AND WHY IT IS SEPARATE FROM company-awards.json
---------------------------------------------------------------
Tender History (3198) answers "what has been awarded and when does its
contract end". This file answers "what is open for bidding right now, and
what is coming". The two must never be merged: an award has a winning
supplier and a contract period; an open notice has neither yet, only a
closing date. Scoped as "proposal 1" in the 26/08/2026 Hub gap audit
(Hub/Medical-Sales-Hub/Hub Documents/hub-gap-audit.md) — carried forward
three prior audits (24/07, 31/07, 07/08) before this build.

THE TWO FEEDS (both public, no key) — same feeds as refresh_awards.py,
different stage filter
------------------------------------------------------------------------
Find a Tender    — above-threshold, UK statutory. OCDS release packages.
    https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages
        ?stages=tender&limit=100&updatedFrom=…&updatedTo=…
    Notice URL:  /Notice/{id}      id is "nnnnnn-yyyy"   (capital N)

Contracts Finder — below-threshold and sub-£139k. OCDS search.
    https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search
        ?size=100&stages=tender
    Notice URL:  /Notice/{GUID}    GUID is the release id with its trailing
                 "-NNNNNN" removed. NOT the ocid.   (capital N)

URL construction is copied verbatim from refresh_awards.py — same bug class,
same fix, done once.

WHAT COUNTS AS "OPEN"
----------------------
A release is kept only when `tender.status` is "active" (open for bids) or
"planning" (Procurement Act pipeline / preliminary market engagement notice
— published ahead of the formal tender so reps get more runway, not less).
"complete", "cancelled", "unsuccessful" and "withdrawn" are dropped — those
belong in Tender History once they resolve to an award, or nowhere if they
lapse. A notice whose own `tender.tenderPeriod.endDate` has already passed
is dropped even if the feed still reports it active — a stale "still open"
row is worse than no row.

MEDICAL FILTER — copied from refresh_awards.py, deliberately not loosened
----------------------------------------------------------------------------
Same CPV-33 headline-classification-or-strong-title-keyword rule, same
exclude list. See that file's docstring for the false-positive history this
guards against (buyer-name matching would false-match NHS Blood and
Transplant onto every notice).

NO COMPANY MATCHING HERE
--------------------------
Unlike awards, an open notice names a BUYER (trust/ICB/NHS Supply Chain),
never a supplier — there is nothing to resolve against the Hub company
seed. Rows are tagged by speciality (best-effort keyword match against the
Hub's own taxonomy, same approach as cloud-pipeline/tender_backfill.py's
tag_speciality — reimplemented here rather than imported cross-repo, since
this repo publishes independently of cloud-pipeline) so the Hub page can
filter the way every other tracker does.

USAGE
    python3 scripts/refresh_open_tenders.py                # weekly: last 8 days
    python3 scripts/refresh_open_tenders.py --days 30      # catch up after an outage
    python3 scripts/refresh_open_tenders.py --dry-run      # fetch, report, write nothing

Then, as for every data file:
    python3 scripts/stamp_notice.py
    python3 verify.py
"""

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

OUT_PATH = "data/open-tenders.json"

UA = {"User-Agent": "MedicalSalesHub/1.0 (+https://elevateandthrive.uk; open tenders index)",
      "Accept": "application/json"}

FTS_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
FTS_NOTICE = "https://www.find-tender.service.gov.uk/Notice/{}"
CF_API = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
CF_NOTICE = "https://www.contractsfinder.service.gov.uk/Notice/{}"

# Default window. Kept identical to refresh_awards.py's DEFAULT_DAYS/overlap
# logic for the same reason: a weekly job with a one-day overlap so a notice
# published mid-run is picked up the following week, never lost. Rows de-dup
# on the notice URL, so overlap costs nothing.
DEFAULT_DAYS = 8
MAX_PAGES = 60
CF_MAX_PAGES = 40
PAGE_SLEEP = 1.0
MAX_WAIT = 600

# Both statutory feeds report a pipeline/PIN notice as tender.status "planned",
# NOT "planning" (verified live against both APIs 02/09/2026: FTS stages=planning
# returned 94/100 releases as "planned", CF stages=planning returned 100/100).
# "planning" is kept in the set because it is what the OCDS spec's own stage is
# called and a feed could legitimately emit it. Anything matched here is
# NORMALISED to "planning" on the way out (see row_from_release) so the Hub page
# keeps one canonical value to filter and count on.
OPEN_STATUSES = {"active", "planning", "planned"}
PLANNING_STATUSES = {"planning", "planned"}

CPV_MEDICAL_PREFIX = "33"

STRONG_KW = re.compile(
    r'\b(surgic|theatre|endoscop|catheter|cannula|vascular access|wound care|'
    r'dressing|stoma|continence|implant|prosthe|orthopaed|radiotherap|'
    r'ultrasound|ct scanner|mri scanner|x-ray|mammograph|infusion pump|syringe '
    r'driver|sterilis|steriliz|decontaminat|ventilat|anaesthe|dialysis|'
    r'defibrillat|mattress|spineboard|scoop|hoist|lymphoedema|dosimet|'
    r'ligation|biopsy|electrosurg|sutures|arthroscop|laparoscop|pacemaker|'
    r'stent|guidewire|nebuliser|oximeter|spirometer|audiometer|ophthalmic)\b',
    re.I)

EXCLUDE = re.compile(
    r'\b(mental health|talking therap|counsell|homecare|home care|floor walker|'
    r'nhs\.net|migration|software|licen[cs]e|onboarding|it services|saas|'
    r'estates|facilities management|construction|design contract|refurbish|'
    r'grounds|catering|cleaning|security|car park|landscap|roof|boiler|'
    r'painting|legal serv|recruit|translat|taxi|vehicle|leasing|fleet|courier|'
    r'waste|training|leadership programme|consultancy|advertising|insurance|'
    r'audit services|drug (and|&) alcohol|substance misuse|sexual health|'
    r'domestic abuse|advocacy|helpline|outreach|recovery service|vape|'
    r'smoking cessation|assertive|supported living|placement)\b',
    re.I)

# Best-effort speciality tagging — same 43-slug taxonomy the rest of the Hub
# uses (cloud-pipeline/speciality-template/pages_map.py). Reimplemented, not
# imported, per the module docstring above. Keep in sync by hand if that
# taxonomy changes; a mismatch here only weakens a filter, never publishes a
# wrong fact.
SPECIALITY_KEYWORDS = [
    ("vascular-access", r'\b(vascular access|cannula|picc|central line|vascath)\b'),
    ("tissue-viability-and-wound-care", r'\b(wound care|dressing|tissue viability|'
     r'negative pressure wound|stoma|continence)\b'),
    ("orthopaedics-and-trauma", r'\b(orthopaed|trauma|arthroplast|fracture fixation)\b'),
    ("theatres-and-surgical", r'\b(theatre|surgical instrument|electrosurg|sutures|'
     r'laparoscop|arthroscop)\b'),
    ("critical-care", r'\b(critical care|intensive care|ventilat|icu)\b'),
    ("respiratory", r'\b(respiratory|oxygen therapy|spirometer|nebuliser|oximet)\b'),
    ("cardiology", r'\b(cardio|pacemaker|defibrillat|stent(?!\w))\b'),
    ("renal", r'\b(renal|dialysis|haemodialysis)\b'),
    ("diabetes-and-endocrinology", r'\b(diabet|insulin|glucose monitor)\b'),
    ("radiology", r'\b(radiolog|ct scanner|mri scanner|x-ray|mammograph|ultrasound)\b'),
    ("interventional-radiology", r'\b(interventional radiolog|guidewire|angiograph)\b'),
    ("oncology-and-sact", r'\b(oncolog|chemotherap|sact|radiotherap|dosimet)\b'),
    ("pathology", r'\b(patholog|histolog|laborator(y|ies) equipment)\b'),
    ("ipc", r'\b(infection prevention|decontaminat|sterilis|steriliz)\b'),
    ("maternity-and-neonatal", r'\b(matern|neonat|obstetric)\b'),
    ("patient-handling", r'\b(hoist|mattress|patient handling|moving and handling)\b'),
    ("ent", r'\b(\bent\b|otolaryng|audiolog|audiometer)\b'),
    ("ophthalmology", r'\b(ophthalm|optic)\b'),
    ("emergency-and-urgent-care", r'\b(emergency department|urgent care|spineboard|scoop)\b'),
    ("pharmacy", r'\b(pharmac|medicines management|syringe driver)\b'),
]


def tag_speciality(title):
    for slug, pattern in SPECIALITY_KEYWORDS:
        if re.search(pattern, title, re.I):
            return slug
    return "unclassified"


# ------------------------------------------------------------------ fetching

def get(url, timeout=90, retries=3):
    """GET + parse JSON, honouring Retry-After. Both feeds rate-limit with 429."""
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503):
                wait = int(exc.headers.get("Retry-After") or 30)
                if wait > MAX_WAIT:
                    raise SystemExit(
                        "ABORT: the feed asked for a %ds wait — stopping rather than "
                        "hammering it. Re-run later." % wait)
                time.sleep(min(wait, MAX_WAIT) + 2)
                continue
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(5 * attempt)
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(5 * attempt)


def headline_cpv(tender):
    cl = tender.get("classification") or {}
    return str(cl["id"]) if cl.get("scheme") == "CPV" and cl.get("id") else ""


def relevant(tender, title):
    if EXCLUDE.search(title):
        return False
    if headline_cpv(tender).startswith(CPV_MEDICAL_PREFIX):
        return True
    return bool(STRONG_KW.search(title))


def cf_guid(release_id):
    return re.sub(r"-\d+$", "", release_id or "")


def row_from_release(rel, source, today_iso):
    tender = rel.get("tender") or {}
    title = (tender.get("title") or "").strip()
    if not relevant(tender, title):
        return None
    status = (tender.get("status") or "").strip().lower()
    if status not in OPEN_STATUSES:
        return None
    period = tender.get("tenderPeriod") or {}
    end_date = period.get("endDate")
    if end_date and end_date[:10] < today_iso:
        # Feed says active, but its own closing date has passed — drop rather
        # than publish a stale "still open" row.
        return None
    buyer = ((rel.get("buyer") or {}).get("name") or "").strip()
    value = tender.get("value") or {}
    rid = rel.get("id", "")
    url = (FTS_NOTICE.format(rid) if source == "Find a Tender"
           else (CF_NOTICE.format(cf_guid(rid)) if cf_guid(rid) else ""))
    raw_status = status
    if status in PLANNING_STATUSES:
        # Canonical value for everything downstream — the Hub page counts and
        # filters on "planning". rawStatus keeps what the feed actually said.
        status = "planning"
        stage = "preliminary market engagement / planning"
    else:
        stage = "open tender"
    return {
        "title": title,
        "buyer": buyer,
        "status": status,
        "rawStatus": raw_status,
        "stage": stage,
        "date": (rel.get("date") or "")[:10],
        "closingDate": end_date,
        "startDate": period.get("startDate"),
        "url": url,
        "source": source,
        "cpv": headline_cpv(tender),
        "valueAmount": value.get("amount"),
        "valueCurrency": value.get("currency") or ("GBP" if value.get("amount") is not None else ""),
        "speciality": tag_speciality(title),
        "ocid": rel.get("ocid", ""),
    }


def fetch_fts(days, today_iso, max_pages=MAX_PAGES, stage="tender"):
    """One pass over ONE OCDS stage.

    Called once per stage (see fetch_fts_all). The two statutory feeds disagree
    about how to ask for more than one stage in a single call, and BOTH failure
    modes are silent — verified live 02/09/2026:
      * Find a Tender: "stages=planning,tender" returns 0 releases (HTTP 200,
        empty). Only repeated params work.
      * Contracts Finder: repeated params make the LAST one win, dropping the
        other stage entirely; only the comma form mixes them.
    Rather than depend on either quirk, each stage gets its own pass and the
    results are merged and de-duplicated. Slower, impossible to get silently
    wrong.
    """
    now = dt.datetime.now(dt.timezone.utc)
    qs = urllib.parse.urlencode({
        "stages": stage, "limit": 100,
        "updatedFrom": (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00"),
        "updatedTo": now.strftime("%Y-%m-%dT23:59:59")})
    url = "%s?%s" % (FTS_API, qs)
    rows, pages, scanned, complete = [], 0, 0, True
    while url and pages < max_pages:
        data = get(url)
        releases = data.get("releases", [])
        scanned += len(releases)
        for rel in releases:
            row = row_from_release(rel, "Find a Tender", today_iso)
            if row:
                rows.append(row)
        pages += 1
        url = (data.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
    if url and pages >= max_pages:
        complete = False
    note = ("Find a Tender (%s stage): %d open notice(s) from %d release(s) over "
            "%d page(s)" % (stage, len(rows), scanned, pages))
    if not complete:
        note += (" — ⚠️ STOPPED AT THE %d-PAGE GUARD before the window was exhausted, "
                 "so this window was NOT fully walked and notices are missing." % max_pages)
    return rows, note, complete


def fetch_cf(days, today_iso, max_pages=CF_MAX_PAGES, stage="tender"):
    """One pass over ONE OCDS stage — see fetch_fts's docstring for why."""
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    url = "%s?size=100&stages=%s" % (CF_API, stage)
    rows, pages, scanned, reached = [], 0, 0, False
    while url and pages < max_pages:
        data = get(url)
        releases = data.get("releases", [])
        if not releases:
            reached = True
            break
        pages += 1
        scanned += len(releases)
        for rel in releases:
            rdate = (rel.get("date") or "")[:10]
            if rdate and rdate < cutoff:
                reached = True
                continue
            row = row_from_release(rel, "Contracts Finder", today_iso)
            if row:
                rows.append(row)
        if reached:
            break
        url = (data.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
    note = ("Contracts Finder (%s stage): %d open notice(s) from %d release(s) over "
            "%d page(s), back to %s" % (stage, len(rows), scanned, pages, cutoff))
    if not reached:
        note += (" — ⚠️ STOPPED AT THE %d-PAGE GUARD before reaching the cutoff, so "
                 "this window was NOT fully walked and notices are missing." % max_pages)
    return rows, note, reached


# ------------------------------------------------------------------ assembly

def dedup_key(row):
    return row.get("url", "") or (row.get("ocid", ""), row.get("title", ""))


def assemble(rows, existing, window, notes, complete, today):
    kept = {}
    for row in (existing or {}).get("_rows", []):
        # Drop stored rows whose closing date has now passed — this file is
        # a live "open now" list, not a history.
        cd = row.get("closingDate")
        if cd and cd[:10] < today.isoformat():
            continue
        kept[dedup_key(row)] = row
    for row in rows:
        kept[dedup_key(row)] = row

    ordered = sorted(kept.values(),
                     key=lambda r: (r.get("closingDate") or "9999-12-31"))

    by_speciality = {}
    for row in ordered:
        by_speciality.setdefault(row["speciality"], []).append(row)

    doc = {
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "source": ("Find a Tender and Contracts Finder tender-stage OCDS notices, "
                   "Open Government Licence v3"),
        "sourceUrls": {
            "Find a Tender": "https://www.find-tender.service.gov.uk/",
            "Contracts Finder": "https://www.contractsfinder.service.gov.uk/",
        },
        "scopeRule": (
            "Live/open NHS-medical procurement notices only: tender.status "
            "'active' (open for bids) or 'planning' (Procurement Act pipeline / "
            "preliminary market engagement, published ahead of the formal "
            "tender). A notice whose own closing date has passed is dropped "
            "even if the feed still reports it open. This is the forward-"
            "looking companion to Tender History (page 3198), which holds "
            "AWARDS only — the two never overlap by design."
        ),
        "filterRule": (
            "A notice is in scope when the buyer's HEADLINE CPV classification is in "
            "division 33 (medical equipment, pharmaceuticals and personal care "
            "products), or its TITLE carries a high-confidence device term. Buyer "
            "names are never matched on. Services, estates, IT, transport and "
            "consumer notices are excluded even under a medical buyer."
        ),
        "specialityRule": (
            "Best-effort keyword match on the notice title against the Hub's own "
            "43-slug speciality taxonomy. 'unclassified' means the title alone "
            "did not carry a recognised term — the notice is still shown, just "
            "unfiltered by speciality."
        ),
        "coverage": {
            "complete": bool(complete),
            "window": window,
            "note": ("Notices indexed from the two statutory feeds over the windows "
                     "listed. An absence here is a statement about this index, never "
                     "about the buyer or the market." if complete else
                     "⚠️ INCOMPLETE — at least one feed hit its page guard before the "
                     "window was exhausted, so notices from this window are missing. "
                     "Re-run with a shorter window."),
            "notes": notes,
        },
        "counts": {
            "openNotices": len(ordered),
            "bySpeciality": {k: len(v) for k, v in sorted(by_speciality.items())},
        },
        "notices": ordered,
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
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    args = ap.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    existing = load(OUT_PATH)
    today = dt.date.today()
    today_iso = today.isoformat()
    window = {"from": (today - dt.timedelta(days=args.days)).isoformat(),
              "to": today_iso, "days": args.days, "run": today_iso}

    # BOTH stages, one pass each, per feed. "tender" = open for bids now;
    # "planning" = Procurement Act pipeline / PIN / preliminary market engagement,
    # published ahead of the formal tender. Before 02/09/2026 only the tender
    # stage was ever requested, so the pipeline half of this page's own stated
    # scope was silently empty — the "Pipeline / PIN notices" tile read 0 not
    # because the market was quiet but because nothing ever asked for them.
    all_rows, notes, ok = [], [], True
    for stage in ("tender", "planning"):
        rows, note, good = fetch_fts(args.days, today_iso, stage=stage)
        all_rows += rows
        notes.append(note)
        ok = ok and good
        print(" ", note, flush=True)
        rows, note, good = fetch_cf(args.days, today_iso, stage=stage)
        all_rows += rows
        notes.append(note)
        ok = ok and good
        print(" ", note, flush=True)

    # De-duplicate: a notice can legitimately surface under more than one stage
    # pass (CF's comma behaviour mixes stages, and a release that moved from
    # planning to tender inside the window appears in both). Keep the first,
    # preferring the open-tender row since that is the more actionable state.
    seen, deduped = set(), []
    for r in all_rows:
        key = r.get("ocid") or r.get("url") or (r.get("title"), r.get("buyer"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    dropped = len(all_rows) - len(deduped)
    if dropped:
        notes.append("De-duplicated %d notice(s) seen under more than one stage." % dropped)
        print("  de-duplicated %d cross-stage duplicate(s)" % dropped, flush=True)

    n_planning = sum(1 for r in deduped if r.get("status") == "planning")
    notes.append("Stage split: %d open tender(s), %d pipeline/PIN notice(s)."
                 % (len(deduped) - n_planning, n_planning))

    doc = assemble(deduped, existing, window, notes, ok, today)

    print("\n%d open notice(s) held across %d speciality bucket(s)."
          % (doc["counts"]["openNotices"], len(doc["counts"]["bySpeciality"])))

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    write(doc)
    print("\nwrote %s. Now: python3 scripts/stamp_notice.py && python3 verify.py"
          % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
