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
        ?limit=100&updatedFrom=…&updatedTo=…      (NO stages filter: it drops
        every Procurement Act 2023 notice, see walk_fts; stage read from
        tender.status instead)
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

# Fixed 12/11/2026. The list used to be one alternation closed by \b, so a stem
# such as "surgic" or "laparoscop" could only match when the word ENDED there:
# "Surgical stapling", "Laparoscopic consumables" and "Endoscopy stack" were all
# missed, and so was every stapling, closure and MIS title, which had no term at
# all. Whole words keep the closing \b; stems may run on (\w*); and the surgical
# consumable terms are added. "ventilat" stays whole-word only, so a building
# "Ventilation" contract is not pulled in.
_KW_WORDS = (
    r'theatre|catheter|cannula|vascular access|wound care|dressing|stoma|'
    r'continence|implants?|ultrasound|ct scanner|mri scanner|x-ray|infusion pump|'
    r'syringe driver|ventilator|ventilators|dialysis|mattress|spineboard|scoop|'
    r'hoist|ligation|biopsy|sutures?|pacemaker|stent|guidewire|nebuliser|'
    r'oximeter|spirometer|audiometer|ophthalmic|wound closure|clip appliers?|'
    r'ligating clips?|ligation clips?|trocars?|minimally invasive|'
    r'tissue adhesives?|hernia mesh|vessel sealing|surgical energy|'
    r'hernia|surgical mesh|skin closure|diathermy|thoracic|robotic surgery|'
    r'robot(?:ic)?[- ]assisted')
_KW_STEMS = (
    r'surgic|endoscop|laparoscop|arthroscop|prosthe|orthopaed|radiotherap|'
    r'mammograph|sterilis|steriliz|decontaminat|anaesthe|defibrillat|'
    r'lymphoedema|dosimet|electrosurg|haemostat|hemostat|endomechanic|stapling|surgical robot|'
    r'(?:surgical|skin|circular|linear|endo|endoscopic) stapl')
STRONG_KW = re.compile(
    r'\b(?:(?:%s)\b|(?:%s)\w*)' % (_KW_WORDS, _KW_STEMS), re.I)

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

# Speciality tagging (09/10/2026): scripts/award_speciality.py, shared with the
# Awards tab, so a notice carries the SAME slug the page's speciality selector uses
# (the speciality panels' curated rules plus label-only corrections). The hand-kept
# keyword list this replaced used slugs that matched no option on page 3198; every
# one of 13 open notices was "unclassified" on 09/10/2026.
def tag_speciality(title, buyer=""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import award_speciality
    return award_speciality.tag(title, buyer)


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


def item_cpvs(tender):
    """Every CPV on the notice's items, in order, de-duplicated."""
    out = []
    for item in tender.get("items") or []:
        for c in [item.get("classification") or {}] + list(item.get("additionalClassifications") or []):
            cid = str(c.get("id") or "")
            if c.get("scheme") == "CPV" and cid and cid not in out:
                out.append(cid)
    return out


def headline_cpv(tender):
    """The notice's main CPV.

    Fixed 20/11/2026: Procurement Act 2023 notices (legalBasis 2023/54) carry NO
    tender.classification. Their CPVs sit only on tender.items[], the first one
    being the main code. Reading tender.classification alone gave "" for every
    such notice, so a medical tender with a plain title ("Urology and Bowel
    Management", 107391-2026, all CPVs in 33) failed relevant() and was dropped.
    """
    cl = tender.get("classification") or {}
    if cl.get("scheme") == "CPV" and cl.get("id"):
        return str(cl["id"])
    items = item_cpvs(tender)
    return items[0] if items else ""


def relevant(tender, title):
    if EXCLUDE.search(title):
        return False
    if headline_cpv(tender).startswith(CPV_MEDICAL_PREFIX):
        return True
    return bool(STRONG_KW.search(title))


def cf_guid(release_id):
    return re.sub(r"-\d+$", "", release_id or "")


def tender_value(tender):
    """(amount, currency, basis) for a tender, or (None, "", "").

    Old-regime (PCR 2015) notices give tender.value.amount, net of VAT.
    Procurement Act 2023 notices give tender.value.amountGross (incl. VAT) and
    no amount, so 107391-2026 (Urology and Bowel Management, £260m) showed "—"
    until 20/11/2026. Some Act notices give no tender-level value at all and put
    it on tender.lots[].value; those are summed only when every valued lot
    shares one currency, otherwise no value is shown rather than a wrong one.
    basis says which figure was used: "net", "gross" or "lots".
    """
    v = tender.get("value") or {}
    if v.get("amount") is not None:
        return v["amount"], v.get("currency") or "GBP", "net"
    if v.get("amountGross") is not None:
        return v["amountGross"], v.get("currency") or "GBP", "gross"
    total, currencies = 0, set()
    for lot in tender.get("lots") or []:
        lv = (lot or {}).get("value") or {}
        amt = lv.get("amount") if lv.get("amount") is not None else lv.get("amountGross")
        if amt is None:
            continue
        total += amt
        currencies.add(lv.get("currency") or "GBP")
    if len(currencies) == 1:
        return total, currencies.pop(), "lots"
    return None, "", ""


def row_from_release(rel, source, today_iso, keep=None):
    """keep(tender, title, buyer) -> bool overrides the medical rule. Only the
    digital lane (scripts/refresh_digital_lane.py) passes one; this file's own
    output always uses relevant() unchanged."""
    tender = rel.get("tender") or {}
    title = (tender.get("title") or "").strip()
    if keep is None:
        if not relevant(tender, title):
            return None
    elif not keep(tender, title, ((rel.get("buyer") or {}).get("name") or "").strip()):
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
    value_amount, value_currency, value_basis = tender_value(tender)
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
        "valueAmount": value_amount,
        "valueCurrency": value_currency,
        "valueBasis": value_basis,
        "speciality": tag_speciality(title, buyer),
        "ocid": rel.get("ocid", ""),
    }


# Stage of a release, from the feed's own tender.status (the same field
# row_from_release gates on). Used to split the single unstaged walk below.
FTS_STAGE_STATUSES = {"tender": {"active"}, "planning": PLANNING_STATUSES}

_FTS_WALKS = {}


def walk_fts(days, max_pages=MAX_PAGES):
    """Walk EVERY Find a Tender release updated in the window, with NO stage filter.

    Fixed 20/11/2026. Until then this asked for "stages=tender" and
    "stages=planning". Verified live 20/11/2026: Find a Tender's stages filter
    returns ONLY old-regime notices (legalBasis 32014L0024/5, PCR 2015). Every
    Procurement Act 2023 notice (legalBasis 2023/54), which is now most of the
    feed, is silently left out. Over 12-20/11/2026 stages=tender gave 59 releases,
    all old-regime; the unstaged feed for 09:00-10:00 on 12/11 alone held five
    Act tenders (107380, 107390, 107391, 107392, 107396) that never appeared.
    107391-2026, NHS Supply Chain's £260m Urology and Bowel Management tender,
    was one of them. The stage is now decided here, from tender.status.

    The walk is shared by both stage passes (and by refresh_digital_lane.py), so
    the feed is read once per run. Returns (latest release per ocid, pages,
    scanned, complete).
    """
    key = (days, max_pages)
    if key in _FTS_WALKS:
        return _FTS_WALKS[key]
    now = dt.datetime.now(dt.timezone.utc)
    qs = urllib.parse.urlencode({
        "limit": 100,
        "updatedFrom": (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00"),
        "updatedTo": now.strftime("%Y-%m-%dT23:59:59")})
    url = "%s?%s" % (FTS_API, qs)
    releases, pages, scanned = [], 0, 0
    while url and pages < max_pages:
        data = get(url)
        got = data.get("releases", [])
        scanned += len(got)
        releases += got
        pages += 1
        url = (data.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
    complete = not (url and pages >= max_pages)
    result = (latest_per_ocid(releases), pages, scanned, complete)
    _FTS_WALKS[key] = result
    return result


def latest_per_ocid(releases):
    """Keep only the newest release of each procurement, so a tender that has
    since been awarded or cancelled is judged on its latest state, not on an
    older "active" release still inside the window."""
    best = {}
    for rel in releases:
        k = rel.get("ocid") or rel.get("id")
        if k not in best or (rel.get("date") or "") > (best[k].get("date") or ""):
            best[k] = rel
    return sorted(best.values(), key=lambda r: r.get("date") or "", reverse=True)


def release_stage(rel):
    status = ((rel.get("tender") or {}).get("status") or "").strip().lower()
    for stage, statuses in FTS_STAGE_STATUSES.items():
        if status in statuses:
            return stage
    return None


def fetch_fts(days, today_iso, max_pages=MAX_PAGES, stage="tender", keep=None):
    """The rows for ONE stage, cut from the shared unstaged walk (walk_fts).

    Contracts Finder still gets one feed pass per stage (see fetch_cf): its
    stages filter does not have this fault. Find a Tender's does, so it is not
    used at all; "stages=planning,tender" also returned 0 releases (02/09/2026).
    """
    releases, pages, scanned, complete = walk_fts(days, max_pages)
    rows = []
    for rel in releases:
        if release_stage(rel) != stage:
            continue
        row = row_from_release(rel, "Find a Tender", today_iso, keep)
        if row:
            rows.append(row)
    note = ("Find a Tender (%s stage): %d open notice(s) from %d release(s) over "
            "%d page(s), all notice types, stage read from tender.status"
            % (stage, len(rows), scanned, pages))
    if not complete:
        note += (" — ⚠️ STOPPED AT THE %d-PAGE GUARD before the window was exhausted, "
                 "so this window was NOT fully walked and notices are missing." % max_pages)
    return rows, note, complete


def fetch_cf(days, today_iso, max_pages=CF_MAX_PAGES, stage="tender", keep=None):
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
            row = row_from_release(rel, "Contracts Finder", today_iso, keep)
            if row:
                rows.append(row)
        if reached:
            break
        url = (data.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
    note = ("Contracts Finder (%s stage): %d open notice(s) from %d release(s) over "
            "%d page(s), back to %s" % (stage, len(rows), scanned, pages, cutoff))
    if not reached and pages < max_pages:
        # Fixed 20/10/2026: the walk also ends when the feed hands back no next
        # cursor, and that was being published as the page guard.
        note += (" — ⚠️ THE FEED RETURNED NO NEXT CURSOR after %d page(s), before "
                 "reaching the cutoff, so this window was NOT fully walked and notices "
                 "are missing." % pages)
    elif not reached:
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
