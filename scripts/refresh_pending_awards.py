#!/usr/bin/env python3
"""NHS Supply Chain framework awards that are PUBLIC but not yet on NHSSC's own
contract launch brief — so refresh_frameworks.py has nothing to read yet.

WHY THIS EXISTS
----------------
The Company Report's FRAMEWORKS panel is deliberately narrow (root rule 16): a
supplier appears on a framework only when that framework's OWN NHS Supply
Chain contract launch brief names it (scripts/refresh_frameworks.py). That is
correct and stays correct.

But an award notice is public MONTHS before NHS Supply Chain publishes its own
brief for it. The Intravenous Cannula and Associated Products framework was
awarded 06/07/2026 and the award notice went live on Find a Tender 18/08/2026
(2026/S 000-078334, OCID ocds-h6vhtk-054eab) naming 21 suppliers including
Mediq Healthcare UK Ltd — but as at 25/08/2026 the URL that will eventually
carry NHSSC's own brief for it still serves the OLD 2023-2027 framework, so
refresh_frameworks.py correctly has nothing to add and the new award is
invisible on every affected supplier's Company Report. Lou flagged this
25/08/2026 on Mediq's report.

That is a real gap, not a bug in the frameworks panel's own rule — it needs a
second, clearly-labelled source, not a loosened first one.

THE RULE THIS FILE ENFORCES
----------------------------
An award appears in data/pending-awards.json ONLY while BOTH are true:
  1. It is a framework award (tender.techniques.hasFrameworkAgreement) naming
     Supply Chain Coordination Limited (NHS Supply Chain's own legal buyer
     name) as buyer, read from its own Find a Tender release.
  2. NO framework in data/frameworks.json — which is only ever populated from
     NHSSC's own contract launch brief — has the same name (normalised).

The moment condition 2 stops holding — NHSSC publishes its own brief and
refresh_frameworks.py captures it — this script drops the entry on its very
next run. Never both panels naming the same framework, never neither.

DATA IS NEVER LOST ON A FRAMEWORKS REFRESH. This file is written by THIS
script alone; refresh_frameworks.py never touches it, so a frameworks.json
refresh can only ever REMOVE a pending entry by genuinely superseding it
(condition 2 above), never by running.

DISCOVERY, AND ITS LIMIT — read before assuming this is fully automatic
------------------------------------------------------------------------
Find a Tender's OWN search API (stages=award, updatedFrom/updatedTo) does NOT
reliably return this class of notice. Confirmed 25/08/2026: notice
078334-2026 (buyer Supply Chain Coordination Limited, released 18/08/2026) is
absent from that search across every window tried, from 8 days to 55 days,
despite existing and being fetchable directly by its own OCID. This looks like
a genuine indexing gap in the feed, not a filter this script applies — nothing
here narrows scope beyond "framework award, this buyer".

So `discover()` below is best-effort: it walks the search feed and unions
whatever it finds with KNOWN_OCIDS, a short, human-maintained list of notices
found by other means (a member's post, an NHSSC newsletter, this session).
When a member or Lou flags an award the search missed, the fix is one line:
add its OCID to KNOWN_OCIDS below. This script says plainly, every run,
whether the search discovery step itself succeeded — so a silent feed outage
never reads as "no new awards".

    python3 scripts/refresh_pending_awards.py               # fetch + write
    python3 scripts/refresh_pending_awards.py --dry-run      # fetch + report only
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
import company_match  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEED_PATH = os.path.join(ROOT, "data", "supplier-seed.json")
FW_PATH = os.path.join(ROOT, "data", "frameworks.json")
OUT_PATH = os.path.join(ROOT, "data", "pending-awards.json")

FTS_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
FTS_NOTICE = "https://www.find-tender.service.gov.uk/Notice/{}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36 "
                    "(medsalesintelligencehub.co.uk pending-framework-awards)"}
PAGE_SLEEP = 1.0
MAX_PAGES = 60
MAX_WAIT = 600

BUYER_KEY = "supply chain coordination limited"

# Notices found by a route other than the search feed (see docstring). Add an
# OCID here the day it is flagged; remove it once this script's own supersede
# check confirms NHSSC's brief has landed and it has aged out of the file.
KNOWN_OCIDS = [
    # Intravenous Cannula and Associated Products, £140m over 4 years if
    # extended, starts 01/04/2027. Flagged by Lou 25/08/2026, sourced from
    # notice 2026/S 000-078334. See Data-Verification/iv-cannula-framework-bd-
    # 2026-08-21/README.md for the full deep dive on this award.
    "ocds-h6vhtk-054eab",
]


# ------------------------------------------------------------------ fetching

def get(url, timeout=60, retries=3):
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
                    raise
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


def discover(days=90, max_pages=MAX_PAGES):
    """Best-effort walk of the search feed for this buyer. Returns
    (set_of_ocids, ok, note). ok=False means the walk itself failed or hit its
    page guard — NOT that no framework awards exist — and the caller must say
    so rather than silently trusting an empty result."""
    now = dt.datetime.now(dt.timezone.utc)
    qs = urllib.parse.urlencode({
        "stages": "award", "limit": 100,
        "updatedFrom": (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00"),
        "updatedTo": now.strftime("%Y-%m-%dT23:59:59")})
    url = "%s?%s" % (FTS_API, qs)
    found, pages, scanned = set(), 0, 0
    try:
        while url and pages < max_pages:
            data = get(url)
            releases = data.get("releases", [])
            scanned += len(releases)
            for rel in releases:
                buyer = ((rel.get("buyer") or {}).get("name") or "").strip().lower()
                fw = bool((rel.get("tender") or {}).get("techniques", {}).get("hasFrameworkAgreement"))
                if buyer == BUYER_KEY and fw:
                    ocid = rel.get("ocid")
                    if ocid:
                        found.add(ocid)
            pages += 1
            url = (data.get("links") or {}).get("next")
            if url:
                time.sleep(PAGE_SLEEP)
    except Exception as exc:
        return found, False, ("search discovery FAILED after %d page(s)/%d release(s) scanned: %s"
                              % (pages, scanned, exc))
    if url and pages >= max_pages:
        return found, False, ("search discovery hit the %d-page guard before the %d-day window "
                              "was exhausted — incomplete, not empty" % (max_pages, days))
    return found, True, ("search discovery walked %d page(s)/%d release(s) over %d days, "
                         "found %d framework-agreement award(s) from this buyer"
                         % (pages, scanned, days, len(found)))


def fetch_release(ocid):
    """The compiled package for one OCID, and the specific release inside it
    that carries an 'award' tag with at least one award. None if there isn't
    one — a planning-only or tender-only OCID is not an award yet."""
    data = get("%s/%s" % (FTS_API, ocid))
    releases = data.get("releases", []) or []
    award_rels = [r for r in releases
                 if "award" in (r.get("tag") or []) and r.get("awards")]
    if not award_rels:
        return None
    # Latest by date if more than one award-stage release exists.
    award_rels.sort(key=lambda r: r.get("date") or "")
    return award_rels[-1]


def fw_title_key(name):
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


# NHSSC reuses a framework's name across generations — the 2023-2027 and the
# 2027-2029 "Intravenous Cannula and Associated Products" briefs share a title
# and would falsely supersede each other on name alone. The framework's own
# START date is the second signal that tells the two generations apart, so a
# pending award is only superseded by a confirmed brief that names the SAME
# framework AND starts within a few days of the SAME date — not merely shares
# a title. Confirmed 25/08/2026 against exactly this pair.
FW_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def parse_fw_date(text):
    """"1 April 2027" -> date(2027, 4, 1). None if it doesn't parse — never a
    guess standing in for a real date."""
    m = re.match(r"^\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*$", str(text or ""))
    if not m:
        return None
    month = FW_MONTHS.get(m.group(2).strip().lower())
    if not month:
        return None
    try:
        return dt.date(int(m.group(3)), month, int(m.group(1)))
    except ValueError:
        return None


def confirmed_frameworks_by_title(fw_doc):
    """title-key -> list of {starts: date|None} for every confirmed framework,
    so a pending award can be checked against the SAME generation, not just
    the same name."""
    out = {}
    for f in (fw_doc or {}).get("frameworks") or []:
        k = fw_title_key(f.get("name"))
        if not k:
            continue
        out.setdefault(k, []).append(parse_fw_date(f.get("starts")))
    return out


def superseded_by(title, contract_start_iso, confirmed_by_title):
    """True only when a confirmed brief names the same framework AND its own
    start date is within 5 days of this award's contract start — the same
    generation, not a same-named predecessor or successor."""
    hits = confirmed_by_title.get(fw_title_key(title))
    if not hits:
        return False
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(contract_start_iso or ""))
    if not m:
        # No usable contract start on the pending award — fall back to name
        # only, which is the pre-fix (unsafe) behaviour, so refuse rather than
        # risk a false supersede.
        return False
    pending_start = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return any(d is not None and abs((d - pending_start).days) <= 5 for d in hits)


def extract(rel):
    """One release -> one pending-award record, or None if it carries nothing
    usable (no title, no suppliers)."""
    tender = rel.get("tender") or {}
    title = (tender.get("title") or "").strip()
    if not title:
        return None
    buyer = ((rel.get("buyer") or {}).get("name") or "").strip()
    suppliers = []
    seen = set()
    contract_start = contract_end = contract_max = None
    award_date = None
    for award in (rel.get("awards") or []):
        award_date = award_date or award.get("date")
        period = award.get("contractPeriod") or {}
        contract_start = contract_start or period.get("startDate")
        contract_end = contract_end or period.get("endDate")
        contract_max = contract_max or period.get("maxExtentDate")
        for s in (award.get("suppliers") or []):
            nm = (s.get("name") or "").strip()
            if nm and nm.lower() not in seen:
                seen.add(nm.lower())
                suppliers.append(nm)
    if not suppliers:
        return None
    rid = rel.get("id", "")
    return {
        "title": title,
        "buyer": buyer,
        "reference": rid,
        "url": FTS_NOTICE.format(rid) if rid else "",
        "ocid": rel.get("ocid", ""),
        "publishedDate": (rel.get("date") or "")[:10],
        "awardDate": (award_date or "")[:10],
        "contractStart": (contract_start or "")[:10],
        "contractEnd": (contract_end or "")[:10],
        "contractExtendedEnd": (contract_max or "")[:10],
        "noticeSuppliers": suppliers,
    }


def assemble(records, seed, fw_doc, discovery_note, discovery_ok):
    index = company_match.build_index(seed)
    confirmed_by_title = confirmed_frameworks_by_title(fw_doc)
    today = dt.date.today()

    kept, superseded = [], []
    for rec in records:
        if superseded_by(rec["title"], rec.get("contractStart"), confirmed_by_title):
            superseded.append({"title": rec["title"], "ocid": rec["ocid"],
                               "reason": ("NHS Supply Chain has now published its own contract "
                                          "launch brief for this framework — see data/frameworks.json. "
                                          "This pending record is retired, not deleted from history; "
                                          "it will not reappear unless removed from KNOWN_OCIDS and "
                                          "re-discovered.")})
            continue
        companies, matched_as, unmatched, ambiguous = [], {}, [], []
        for nm in rec["noticeSuppliers"]:
            company, state, reason = company_match.resolve(nm, index)
            if state == "confirmed":
                companies.append(company)
                matched_as[company] = nm  # the exact wording the notice used
            elif state == "ambiguous":
                ambiguous.append({"name": nm, "reason": reason})
            else:
                unmatched.append({"name": nm, "reason": reason})
        entry = dict(rec)
        entry["companies"] = sorted(set(companies))
        entry["matchedAs"] = matched_as
        entry["unmatchedSuppliers"] = unmatched
        entry["ambiguousSuppliers"] = ambiguous
        kept.append(entry)

    by_company = {}
    for entry in kept:
        for name in entry["companies"]:
            by_company.setdefault(name, []).append(entry)

    doc = {
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "source": ("Find a Tender award-stage OCDS notices naming Supply Chain "
                  "Coordination Limited (NHS Supply Chain's own legal buyer name) "
                  "as buyer, with a framework agreement. Open Government Licence v3. "
                  "https://www.find-tender.service.gov.uk/"),
        "rule": ("An award is published here ONLY while NHS Supply Chain has NOT YET "
                "published its own contract launch brief for the SAME framework "
                "generation — matched on framework name AND a start date within 5 "
                "days of this award's own contract start, because NHSSC reuses a "
                "framework's name across generations and name alone would falsely "
                "match a predecessor or successor brief. The moment the matching "
                "brief exists in data/frameworks.json, this entry is retired here on "
                "this script's next run — the confirmed FRAMEWORKS panel is always "
                "the one to trust once both exist."),
        "matchRule": company_match.RULE,
        "discovery": {
            "ok": bool(discovery_ok),
            "note": discovery_note,
            "knownOcids": KNOWN_OCIDS,
            "caveat": ("Find a Tender's own search API does not reliably surface every "
                      "framework award from this buyer (confirmed 25/08/2026 against "
                      "notice 2026/S 000-078334, absent from every search window tried "
                      "despite existing). KNOWN_OCIDS in this script is the safety net — "
                      "add an OCID there the day an award is flagged by any other route."),
        },
        "counts": {
            "pending": len(kept),
            "superseded": len(superseded),
            "companies": len(by_company),
        },
        "awards": kept,
        "superseded": superseded,
        "companies": by_company,
    }
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
    ap.add_argument("--days", type=int, default=90,
                    help="lookback for the best-effort search discovery step")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report, write nothing")
    args = ap.parse_args(argv)

    root = ROOT
    os.chdir(root)

    seed = load(SEED_PATH, {"suppliers": []})
    fw_doc = load(FW_PATH, {"frameworks": []})

    discovered, disc_ok, disc_note = discover(args.days)
    print(" ", disc_note, flush=True)
    ocids = sorted(set(KNOWN_OCIDS) | discovered)

    records = []
    for ocid in ocids:
        try:
            rel = fetch_release(ocid)
        except Exception as exc:
            print("  ! %s: could not fetch (%s) — skipped this run, not dropped "
                  "(stays in KNOWN_OCIDS)." % (ocid, exc), flush=True)
            continue
        if not rel:
            print("  - %s: no award-stage release with suppliers yet" % ocid, flush=True)
            continue
        rec = extract(rel)
        if rec:
            records.append(rec)
            print("  + %s: %r, %d supplier(s)" % (ocid, rec["title"], len(rec["noticeSuppliers"])),
                  flush=True)

    doc = assemble(records, seed, fw_doc, disc_note, disc_ok)
    print("pending %d, superseded %d (now on NHSSC's own brief), %d Hub compan(y/ies) named"
          % (doc["counts"]["pending"], doc["counts"]["superseded"], doc["counts"]["companies"]))

    if args.dry_run:
        print(json.dumps(doc, indent=1)[:4000])
        return 0

    write(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
