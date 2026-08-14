#!/usr/bin/env python3
"""Tender and contract awards, keyed to the Hub company they were awarded to.

WHAT THIS IS, AND WHY IT IS IN THIS REPOSITORY
----------------------------------------------
The Company Intelligence report's sections 13–16 (tender awards, contract
awards) had no data source at all. Award data existed only as <tr> rows
appended to WordPress page 703 (the Award Tracker) by cloud-pipeline/awards.py,
which writes no data file — so nothing in msh-compare-data could read it, the
`awards` and `tenders` keys in the report schema were unpopulated in every
record, and a company fact was being typed into a WordPress page, which the
standing rule forbids.

This is the fix's first half: the same two statutory OCDS feeds, fetched here,
matched to Hub companies here, written to data/company-awards.json here, and
gated by verify.py like every other data file. It lives in this repository
rather than in cloud-pipeline because cloud-pipeline publishes to WordPress and
would have to push cross-repo to reach the data layer.

THE TWO FEEDS (both public, no key)
-----------------------------------
Find a Tender    — above-threshold, UK statutory. OCDS release packages.
    https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages
        ?stages=award&limit=100&updatedFrom=…&updatedTo=…
    Notice URL:  /Notice/{id}      id is "nnnnnn-yyyy"   (capital N)

Contracts Finder — below-threshold and sub-£139k. OCDS search.
    https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search
        ?size=100&stages=award
    Notice URL:  /Notice/{GUID}    GUID is the release id with its trailing
                 "-NNNNNN" removed. NOT the ocid.   (capital N)

Getting the notice URL wrong is what put six dead links in the 20/07/2026
briefing, so URL construction is done in one place and nowhere else.

⚠️ CONTRACTS FINDER MUST BE PAGED, AND THE REASON IS MEASURED.
A single size=100 page of award notices covers the WHOLE UK public sector,
newest first. Measured 14/08/2026, those 100 notices spanned 14:57 back to
09:51 the SAME DAY — about five hours. A weekly job reading one page is reading
five hours and calling it a week. So the cursor in links.next is walked until
the release dates cross the cutoff. max_pages is a runaway guard, NOT a
coverage limit: if the walk stops there the window was not fully covered, and
this script SAYS SO in the file it writes rather than handing over a short list
that reads as complete.

WHICH SECTION AN AWARD LANDS IN
-------------------------------
Find a Tender carries above-threshold procurements — the report's "Tender
awards". Contracts Finder carries below-threshold ones — "Contract awards".
That split is a fact about which statutory service published the notice, not a
judgement this script makes.

MATCHING, AND WHAT IS DELIBERATELY NOT PUBLISHED
------------------------------------------------
Notices name legal entities; the seed holds trading names. The resolution rule
is in scripts/company_match.py, is exact-only, and verify.py re-derives every
published match from the same module. Anything that does not resolve to exactly
one Hub company is written to the quarantine blocks (`unmatched`, `ambiguous`)
and is NOT attached to any company. A quarantined row is a question for a
human, answered by adding the alias to that company's seed record — never by
loosening the rule here.

USAGE
    python3 scripts/refresh_awards.py                # weekly: last 8 days
    python3 scripts/refresh_awards.py --days 30      # catch up after an outage
    python3 scripts/refresh_awards.py --dry-run      # fetch, report, write nothing
    python3 scripts/refresh_awards.py --rematch      # re-resolve what is stored,
                                                     # no network (after a seed edit)

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match

SEED_PATH = "data/supplier-seed.json"
OUT_PATH = "data/company-awards.json"

UA = {"User-Agent": "MedicalSalesHub/1.0 (+https://elevateandthrive.uk; award index)",
      "Accept": "application/json"}

FTS_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
FTS_NOTICE = "https://www.find-tender.service.gov.uk/Notice/{}"
CF_API = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
CF_NOTICE = "https://www.contractsfinder.service.gov.uk/Notice/{}"

HUB_AWARD_TRACKER = "https://medsalesintelligencehub.co.uk/medical-sales-hub/awards/"

# Default window. 8 days against a weekly (Monday) job is a deliberate one-day
# overlap, so a notice published while the job is mid-run is picked up the
# following week rather than lost. Duplicates cost nothing — rows de-dup on the
# notice link plus the supplier named on it.
DEFAULT_DAYS = 8
MAX_PAGES = 40
PAGE_SLEEP = 1.0
MAX_WAIT = 600

# PRIMARY FILTER — CPV code. The award feeds are the entire UK public sector,
# so keyword matching alone is fooled by volume. CPV division 33 is "Medical
# equipments, pharmaceuticals and personal care products". Keywords are only a
# backstop for notices a buyer has mis-coded.
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
    """The buyer's primary classification of the WHOLE contract.

    A stray medical sub-code on one line item does not make a social-care
    service a device award, so only the headline counts for CPV inclusion.
    """
    cl = tender.get("classification") or {}
    return str(cl["id"]) if cl.get("scheme") == "CPV" and cl.get("id") else ""


def relevant(tender, title):
    """Headline CPV in division 33, or a high-confidence device term in the
    TITLE — never the buyer name, or every award by "NHS Blood and Transplant"
    would false-match. Always subject to the exclude list."""
    if EXCLUDE.search(title):
        return False
    if headline_cpv(tender).startswith(CPV_MEDICAL_PREFIX):
        return True
    return bool(STRONG_KW.search(title))


def cf_guid(release_id):
    """Contracts Finder notice GUID = release id minus its trailing -NNNNNN."""
    return re.sub(r"-\d+$", "", release_id or "")


def rows_from_release(rel, source, section):
    """One row per SUPPLIER named on the release, not one per notice.

    A framework award naming four suppliers is four companies' news. Joining
    them into one string and splitting it later loses any name that contains a
    comma, so the OCDS supplier array is kept as an array all the way through.
    """
    tender = rel.get("tender") or {}
    title = (tender.get("title") or "").strip()
    if not relevant(tender, title):
        return []
    buyer = ((rel.get("buyer") or {}).get("name") or "").strip()
    out = []
    for award in (rel.get("awards") or []):
        value = award.get("value") or {}
        amount, currency = value.get("amount"), value.get("currency") or "GBP"
        if amount is None:
            tv = tender.get("value") or {}
            amount, currency = tv.get("amount"), tv.get("currency") or "GBP"
        period = award.get("contractPeriod") or {}
        date = (award.get("date") or rel.get("date") or "")[:10]
        rid = rel.get("id", "")
        url = (FTS_NOTICE.format(rid) if source == "Find a Tender"
               else (CF_NOTICE.format(cf_guid(rid)) if cf_guid(rid) else ""))
        for supplier in (award.get("suppliers") or []):
            name = (supplier.get("name") or "").strip()
            if not name:
                continue
            out.append({
                "noticeSupplierName": name,
                "title": title,
                "buyer": buyer,
                "date": date,
                "url": url,
                "hubUrl": HUB_AWARD_TRACKER,
                "source": source,
                "section": section,
                "cpv": headline_cpv(tender),
                # Null means the notice did not state a value. It is NEVER 0 —
                # a 0 in a value field is a parse bug, not a free contract.
                "valueAmount": amount,
                "valueCurrency": currency if amount is not None else "",
                "periodStart": period.get("startDate"),
                "periodEnd": period.get("endDate"),
                "ocid": rel.get("ocid", ""),
            })
    return out


def fetch_fts(days, max_pages=60):
    """Find a Tender award notices for the window. updatedFrom bounds the
    window server-side, so paging stops naturally; the cap is a runaway guard."""
    now = dt.datetime.now(dt.timezone.utc)
    qs = urllib.parse.urlencode({
        "stages": "award", "limit": 100,
        "updatedFrom": (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00"),
        "updatedTo": now.strftime("%Y-%m-%dT23:59:59")})
    url = "%s?%s" % (FTS_API, qs)
    rows, pages, scanned, complete = [], 0, 0, True
    while url and pages < max_pages:
        data = get(url)
        releases = data.get("releases", [])
        scanned += len(releases)
        for rel in releases:
            rows.extend(rows_from_release(rel, "Find a Tender", "tender-awards"))
        pages += 1
        url = (data.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
    if url and pages >= max_pages:
        complete = False
    note = ("Find a Tender: %d supplier row(s) from %d release(s) over %d page(s)"
            % (len(rows), scanned, pages))
    if not complete:
        note += (" — ⚠️ STOPPED AT THE %d-PAGE GUARD before the window was exhausted, "
                 "so this window was NOT fully walked and awards are missing."
                 % max_pages)
    return rows, note, complete


def fetch_cf(days, max_pages=MAX_PAGES):
    """Contracts Finder award notices, cursor walked back to the cutoff.

    See the module docstring for why a single page is five hours of notices.
    """
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    url = "%s?size=100&stages=award" % CF_API
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
            rows.extend(rows_from_release(rel, "Contracts Finder", "contract-awards"))
        if reached:
            break
        url = (data.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
    note = ("Contracts Finder: %d supplier row(s) from %d release(s) over %d page(s), "
            "back to %s" % (len(rows), scanned, pages, cutoff))
    if not reached:
        note += (" — ⚠️ STOPPED AT THE %d-PAGE GUARD before reaching the cutoff, so "
                 "this window was NOT fully walked and awards are missing." % max_pages)
    return rows, note, reached


# ------------------------------------------------------------------ assembly

def dedup_key(row):
    """One award, one supplier. The notice link alone would collapse a
    four-supplier framework award into one row."""
    return (row.get("url", ""), company_match.key(row.get("noticeSupplierName", "")))


def assemble(rows, seed, existing, window, notes, complete):
    """Resolve every row and lay the file out. Pure — no network, no clock
    beyond today's date — so the gate and the tests can drive it directly."""
    index = company_match.build_index(seed)
    today = dt.date.today()

    kept = {}
    for row in (existing or {}).get("_rows", []):
        kept[dedup_key(row)] = row
    for row in rows:
        kept[dedup_key(row)] = row

    companies, unmatched, ambiguous = {}, [], []
    for row in kept.values():
        company, state, reason = company_match.resolve(row["noticeSupplierName"], index)
        entry = dict(row)
        if state == "confirmed":
            entry["company"] = company
            entry["matchedOn"] = reason
            companies.setdefault(company, []).append(entry)
        else:
            entry["reason"] = reason
            (ambiguous if state == "ambiguous" else unmatched).append(entry)

    for rows_for_company in companies.values():
        rows_for_company.sort(key=lambda r: (r.get("date") or "", r.get("title") or ""),
                              reverse=True)
    unmatched.sort(key=lambda r: (r.get("date") or ""), reverse=True)
    ambiguous.sort(key=lambda r: (r.get("date") or ""), reverse=True)

    matched_rows = sum(len(v) for v in companies.values())
    doc = {
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "source": ("Find a Tender and Contracts Finder award-stage OCDS notices, "
                   "Open Government Licence v3"),
        "sourceUrls": {
            "Find a Tender": "https://www.find-tender.service.gov.uk/",
            "Contracts Finder": "https://www.contractsfinder.service.gov.uk/",
        },
        "sectionRule": (
            "Find a Tender publishes above-threshold procurements and its awards are "
            "the report's TENDER AWARDS; Contracts Finder publishes below-threshold "
            "ones and its awards are CONTRACT AWARDS. The split is a fact about which "
            "statutory service published the notice, not a judgement made here."
        ),
        "filterRule": (
            "A notice is in scope when the buyer's HEADLINE CPV classification is in "
            "division 33 (medical equipment, pharmaceuticals and personal care "
            "products), or its TITLE carries a high-confidence device term. Buyer "
            "names are never matched on. Services, estates, IT, transport and "
            "consumer notices are excluded even under a medical buyer."
        ),
        "matchRule": company_match.RULE,
        "coverage": {
            "complete": bool(complete),
            "window": window,
            "note": ("Awards indexed from the two statutory feeds over the windows "
                     "listed. An absence here is a statement about this index, never "
                     "about the company." if complete else
                     "⚠️ INCOMPLETE — at least one feed hit its page guard before the "
                     "window was exhausted, so awards from this window are missing. "
                     "Re-run with a shorter window."),
            "notes": notes,
        },
        "counts": {
            "companies": len(companies),
            "awardRows": matched_rows,
            "unmatched": len(unmatched),
            "ambiguous": len(ambiguous),
            "rowsHeld": len(kept),
        },
        "companies": companies,
        # QUARANTINE. Not published to any company, kept so the gap is countable
        # and so a human can settle it by adding the alias to the seed record.
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        # Every row as fetched, before resolution. This is what --rematch
        # re-resolves after a seed edit, so a newly-added alias attaches its
        # awards without re-fetching the feeds.
        "_rows": sorted(kept.values(),
                        key=lambda r: (r.get("date") or "", r.get("url") or "")),
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
    """indent=1, the house style for this repo's data files — stamp_notice.py
    reproduces a file's own formatting and refuses anything it cannot."""
    with open(path, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    ap.add_argument("--rematch", action="store_true",
                    help="re-resolve the stored rows against the seed, no network")
    args = ap.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    seed = load(SEED_PATH, {"suppliers": []})
    existing = load(OUT_PATH)

    if args.rematch:
        if not existing:
            sys.exit("%s does not exist yet — nothing to re-match. Run without "
                     "--rematch first." % OUT_PATH)
        doc = assemble([], seed, existing, None,
                       ["re-matched from stored rows, no fetch"],
                       (existing.get("coverage") or {}).get("complete", True))
        write(doc)
        print("re-matched %d stored row(s): %d company/ies, %d unmatched, %d ambiguous"
              % (doc["counts"]["rowsHeld"], doc["counts"]["companies"],
                 doc["counts"]["unmatched"], doc["counts"]["ambiguous"]))
        return 0

    today = dt.date.today()
    window = {"from": (today - dt.timedelta(days=args.days)).isoformat(),
              "to": today.isoformat(), "days": args.days, "run": today.isoformat()}

    fts_rows, fts_note, fts_ok = fetch_fts(args.days)
    print(" ", fts_note, flush=True)
    cf_rows, cf_note, cf_ok = fetch_cf(args.days)
    print(" ", cf_note, flush=True)

    doc = assemble(fts_rows + cf_rows, seed, existing, window,
                   [fts_note, cf_note], fts_ok and cf_ok)

    print("\n%d row(s) held: %d attached to %d Hub company/ies, %d unmatched, "
          "%d ambiguous."
          % (doc["counts"]["rowsHeld"], doc["counts"]["awardRows"],
             doc["counts"]["companies"], doc["counts"]["unmatched"],
             doc["counts"]["ambiguous"]))
    if doc["counts"]["unmatched"]:
        print("\nUnmatched supplier names (add the alias to that company's seed record "
              "to attach these — never loosen the match rule):")
        seen = []
        for row in doc["unmatched"]:
            if row["noticeSupplierName"] not in seen:
                seen.append(row["noticeSupplierName"])
        for name in seen[:40]:
            print("  - %s" % name)
        if len(seen) > 40:
            print("  … and %d more (all in the file's unmatched block)" % (len(seen) - 40))

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    write(doc)
    print("\nwrote %s. Now: python3 scripts/stamp_notice.py && python3 verify.py"
          % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
