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


# ------------------------------------------------------- the award history
#
# ADDED 30/09/2026. The feeds above are walked over a rolling 8-day window, so on
# its own this file only ever held a few weeks of awards (129 rows, 70
# companies, Contracts Finder back to 14/09/2026). A company report showed no
# awards for Hollister while data/tender-history.json — the same two statutory
# feeds, walked back to 2021 by the pipeline's tender-history-refresh — held its
# £1.98m Solent NHS Trust stoma care award and its place on NHS Scotland's
# "Stoma Acute Patient" award. So every run now ALSO reads that history and
# resolves it under exactly the same rule (company_match.resolve, unchanged).
#
# The history rows are re-derived from that file on every run, never copied into
# `_rows`: the file is already in this repo, and copying it would double the
# weight of a file the Company Report fetches on every page load.
#
# SUPPLIER STRINGS. The history export holds one supplier STRING per award, and a
# multi-supplier award is joined with commas ("Clinimed Limited, Coloplast Ltd,
# ConvaTec Ltd, Hollister Ltd, Peak Medical Ltd, "). So:
#   1. The whole string is tried first, exactly as the notice wrote it. A legal
#      name containing a comma ("Becton, Dickinson U.K. Limited") resolves here
#      or not at all — it is never split into two companies.
#   2. Otherwise it is split on commas and semicolons outside brackets. That is
#      splitting only: every piece then faces the same exact-only resolve().
#      A piece that is nothing but legal-form or territory words ("Inc.") is
#      rejoined to the piece before it rather than tried as a name.
#   3. The export cuts supplier strings at 80 characters. A string that long may
#      end mid-name ("Organon Pharma (UK"), so its LAST piece is quarantined
#      unmatched with that reason — a cut-off name is never tried against the
#      seed, because a fragment can exactly equal a shorter, different company.
HISTORY_PATH = "data/tender-history.json"
HISTORY_SUPPLIER_CAP = 80
HISTORY_SOURCE = {"f": "Find a Tender", "c": "Contracts Finder"}
SECTION_FOR = {"Find a Tender": "tender-awards", "Contracts Finder": "contract-awards"}
_BARE_FORM = re.compile(r"^(?:(?:%s|%s)\s*)+$"
                        % (company_match.LEGAL_SUFFIX, company_match.TERRITORY))


def split_suppliers(text):
    """Split a joined supplier string on , and ; outside brackets. Pieces that
    are only legal-form/territory words are rejoined to the previous piece."""
    pieces, buf, depth = [], "", 0
    for ch in text or "":
        if ch in "([":
            depth += 1
        elif ch in ")]" and depth:
            depth -= 1
        if ch in ",;" and depth == 0:
            pieces.append(buf)
            buf = ""
        else:
            buf += ch
    pieces.append(buf)
    out = []
    for p in (x.strip() for x in pieces):
        if not p:
            continue
        if out and _BARE_FORM.match(company_match.norm(p)):
            out[-1] = out[-1] + ", " + p
        else:
            out.append(p)
    return out


def history_source(url, code):
    """Which statutory service published the notice. The URL host is the fact;
    the export's source code is the fallback (legacy rows carry 'l')."""
    if "find-tender.service.gov.uk" in (url or ""):
        return "Find a Tender"
    if "contractsfinder.service.gov.uk" in (url or ""):
        return "Contracts Finder"
    return HISTORY_SOURCE.get(code)


def history_rows(history, index):
    """(rows, quarantined, stats) from data/tender-history.json.

    rows are award rows in this file's own shape, one per supplier piece, still
    to be resolved. quarantined are pieces that must not be tried at all (cut
    off by the export), already carrying their reason."""
    schema = (history or {}).get("schema") or []
    rows, quarantined = [], []
    stats = {"awards": 0, "noSupplier": 0, "noSource": 0, "split": 0, "truncated": 0}
    if not schema:
        return rows, quarantined, stats
    col = {name: i for i, name in enumerate(schema)}

    def f(r, name):
        i = col.get(name)
        return r[i] if i is not None and i < len(r) else None

    for r in history.get("rows") or []:
        stats["awards"] += 1
        url = str(f(r, "u") or "")
        source = history_source(url, f(r, "s"))
        sup = str(f(r, "sup") or "")
        if not source:
            stats["noSource"] += 1
            continue
        if not sup.strip():
            stats["noSupplier"] += 1
            continue
        amount = f(r, "v")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            amount = None
        base = {
            "title": str(f(r, "t") or "").strip(),
            "buyer": str(f(r, "b") or "").strip(),
            "date": str(f(r, "d") or "")[:10],
            "url": url,
            "hubUrl": HUB_AWARD_TRACKER,
            "source": source,
            "section": SECTION_FOR[source],
            "valueAmount": amount,
            "valueCurrency": "GBP" if amount is not None else "",
            "periodEnd": f(r, "pe"),
            "origin": "tender-history",
        }
        cut = len(sup) >= HISTORY_SUPPLIER_CAP
        whole = sup.strip().rstrip(",;").strip()
        if not cut and company_match.resolve(whole, index)[1] == "confirmed":
            pieces = [whole]
        else:
            pieces = split_suppliers(sup)
        if len(pieces) > 1:
            stats["split"] += 1
        for n, piece in enumerate(pieces):
            row = dict(base, noticeSupplierName=piece)
            if len(pieces) > 1 or cut:
                row["noticeSupplierString"] = sup
                row["noticeSupplierCount"] = len(pieces)
            if cut and n == len(pieces) - 1:
                stats["truncated"] += 1
                row["cutOff"] = True
                row["reason"] = (
                    "the award history export cuts supplier names at %d characters and "
                    "this one reaches that limit, so \"%s\" may be the start of a longer "
                    "name. A cut-off name is never matched; read the notice to settle it."
                    % (HISTORY_SUPPLIER_CAP, piece))
                quarantined.append(row)
            else:
                rows.append(row)
    return rows, quarantined, stats


def history_floor(history):
    """The earliest publication date the history's walk covers, as the history
    file itself states it. Falls back to its earliest award date."""
    cov = (history or {}).get("coverage") or {}
    m = re.search(r"published from (\d{4}-\d{2}-\d{2})", str(cov.get("note") or ""))
    return m.group(1) if m else cov.get("awardsFrom")


# ------------------------------------------------------------------ assembly

def award_key(row):
    """The same award seen twice: once on the weekly feed walk, once in the
    history (which lists a republished award once, under its latest notice, so
    the notice URL alone does not always line up)."""
    return (company_match.key(row.get("noticeSupplierName", "")),
            company_match.norm(row.get("title", "")),
            row.get("date") or "",
            row.get("valueAmount"))


def dedup_key(row):
    """One award, one supplier. The notice link alone would collapse a
    four-supplier framework award into one row."""
    return (row.get("url", ""), company_match.key(row.get("noticeSupplierName", "")))


def assemble(rows, seed, existing, window, notes, complete, history=None):
    """Resolve every row and lay the file out. Pure — no network, no clock
    beyond today's date — so the gate and the tests can drive it directly."""
    index = company_match.build_index(seed)
    today = dt.date.today()

    kept = {}
    for row in (existing or {}).get("_rows", []):
        kept[dedup_key(row)] = row
    for row in rows:
        kept[dedup_key(row)] = row

    # The history, resolved under the same rule. A feed row already held wins
    # over its history twin: it carries CPV, ocid and the contract start date.
    h_rows, h_quarantined, h_stats = history_rows(history, index)
    seen_url = set(kept)
    seen_award = {award_key(r) for r in kept.values()}
    to_resolve = list(kept.values())
    h_dupes = 0
    for row in h_rows:
        if dedup_key(row) in seen_url or award_key(row) in seen_award:
            h_dupes += 1
            continue
        seen_url.add(dedup_key(row))
        seen_award.add(award_key(row))
        to_resolve.append(row)

    companies, unmatched, ambiguous = {}, list(h_quarantined), []
    for row in to_resolve:
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

    feeds_note = ("the weekly walk of both feeds over the windows listed" if complete else
                  "the weekly walk of both feeds over the windows listed, which is "
                  "INCOMPLETE: at least one feed hit its page guard before the window "
                  "was exhausted, so awards from that window are missing (re-run with a "
                  "shorter window)")
    coverage = {"complete": bool(complete), "feedsComplete": bool(complete),
                "window": window, "notes": notes}
    if history:
        hcov = history.get("coverage") or {}
        floor = history_floor(history)
        coverage["complete"] = bool(complete) and hcov.get("complete") is True
        coverage["historyFrom"] = floor
        coverage["history"] = {
            "file": HISTORY_PATH,
            "dataAsOf": history.get("dataAsOf"),
            "complete": hcov.get("complete"),
            "note": hcov.get("note"),
        }
        coverage["note"] = (
            "Awards are indexed from (1) the award history in %s (data as of %s), "
            "covering notices published from %s — %s — and (2) %s. Coverage is "
            "INCOMPLETE before %s. %d supplier name(s) that the history export cut off "
            "at %d characters are quarantined, never matched. An absence here is a "
            "statement about this index, never about the company."
            % (HISTORY_PATH, history.get("dataAsOf") or "not stated", floor or "not stated",
               "earlier notices are not fetched on either feed",
               feeds_note, floor or "the history's floor", h_stats["truncated"],
               HISTORY_SUPPLIER_CAP))
    else:
        coverage["note"] = (
            "Awards indexed from %s. An absence here is a statement about this index, "
            "never about the company." % feeds_note if complete else
            "⚠️ INCOMPLETE — at least one feed hit its page guard before the window was "
            "exhausted, so awards from this window are missing. Re-run with a shorter "
            "window.")
    doc = {
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "source": ("Find a Tender and Contracts Finder award-stage OCDS notices, "
                   "Open Government Licence v3" +
                   (" — the weekly walk of both feeds, plus the award history of the "
                    "same two feeds held in data/tender-history.json" if history else "")),
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
        "coverage": coverage,
        "counts": {
            "companies": len(companies),
            "awardRows": matched_rows,
            "unmatched": len(unmatched),
            "ambiguous": len(ambiguous),
            "rowsHeld": len(kept),
            "historyAwardsRead": h_stats["awards"],
            "historyAlreadyHeldFromFeeds": h_dupes,
            "historySupplierNotNamed": h_stats["noSupplier"],
            "historyMultiSupplierSplit": h_stats["split"],
            "historySupplierCutOff": h_stats["truncated"],
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
    history = load(HISTORY_PATH)

    if args.rematch:
        if not existing:
            sys.exit("%s does not exist yet — nothing to re-match. Run without "
                     "--rematch first." % OUT_PATH)
        # The feed notes still describe the stored rows, so they are carried.
        kept_notes = [n for n in ((existing.get("coverage") or {}).get("notes") or [])
                      if not str(n).startswith("re-matched")]
        doc = assemble([], seed, existing, None,
                       kept_notes + ["re-matched from stored rows, no fetch"],
                       (existing.get("coverage") or {}).get("feedsComplete",
                           (existing.get("coverage") or {}).get("complete", True)),
                       history)
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
                   [fts_note, cf_note], fts_ok and cf_ok, history)

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
