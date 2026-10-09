#!/usr/bin/env python3
"""Private hospital group moves — the tracker for the Private Sector page (1666).

WHAT THIS IS
------------
Hub gap audit (17/07 through 28/08, seven consecutive audits) flagged that page 1666
("Selling to the Private Sector") had a narrative-only "five major groups" table but no
live tracker of what those groups are actually doing — capacity, investment, ownership
and partnership moves. This file is that tracker's data source, added as Hub build 3/3
(OUTSTANDING ^o138), sequenced behind build 1/3 (Tenders Tracker, page 3198) and build
2/3 (MHRA Regulatory Desk, page 3483).

Same client-side live-fetch pattern as 3483 (see
"Process flows for all brands/MHRA-Regulatory-Desk-build-and-refresh.md"): this script
writes data/private-provider-moves.json, page 1666's own inline script fetches it
live on every page load from the raw GitHub URl. There is no page-rebuild step.

SOURCE DISCIPLINE — CHECKED 08/09/2026, NOT ASSUMED
-----------------------------------------------------
The five groups named on page 1666 were checked one at a time for a genuine,
citable, directly fetchable dated source (same bar as every other Hub feed).
Full record: 00-Planning/Workstreams/WS-private-provider-tracker.md.

    HCA Healthcare UK      OK   /about-us/news-and-press-releases — dated card list
    Ramsay Health Care UK  OK   /about/news — dated card list, paginated
    Spire Healthcare       OK   investegate.co.uk/company/SPI — RNS regulatory
                                 announcements (FCA-approved Primary Information
                                 Provider), NOT spirehealthcare.com's own investor
                                 page (that page is JS-rendered, no items in raw
                                 HTML, not scrapable). Heavily diluted by Form
                                 8.3/8.5 shareholding-disclosure noise — filtered
                                 out below, kept only substantive announcements.
    Nuffield Health        OK   /about-us/media-centre/press-releases — this is
                                 NOT the page linked from the Media Centre landing
                                 page (that is a contacts hub); found via the
                                 /about-us/news redirect chain.
    Circle Health Group    BLOCKED — circlehealthgroup.co.uk 403s every fetch
                                 (curl and a rendering fetch), any user-agent —
                                 Cloudflare bot protection. No RSS. No syndicated
                                 alternative found (PRNewswire/Cision hits under
                                 "Circle Health" are a different US company,
                                 Circle Medical/WELL Health, not this one).
                                 DELIBERATELY NOT scraped around — per root rule
                                 14, Circle renders as an honest empty state on
                                 the page rather than being filled with weak or
                                 indirect data. This is a stated coverage gap,
                                 not a silent one.

DERIVATION RULE (root rule 14)
-------------------------------
A row is a fact read from the group's own published announcement, not a derived
claim — no "supplier X displaced supplier Y"-style inference happens anywhere in
this file. The only judgement applied is the CATEGORY tag (capacity / investment /
partnership / leadership / other), assigned by a fixed keyword match against the
headline text, never invented per item. A row that matches no keyword still
publishes as "other" — never dropped, never re-categorised by guesswork. The
EVIDENCE FLOOR is the source list above: a provider with no genuinely fetchable
source (Circle) gets zero rows and an explicit "not currently trackable, see
page footer" state, not a lower-quality substitute feed.

CATEGORY KEYWORDS — fixed, not per-item judgement
----------------------------------------------------
    capacity      hospital, centre, unit, ward, theatre, bed, expand, open(s|ed|ing)
    investment    invest, £, million, refinanc, funding, acqui
    partnership   partner, collaborat, deal, agreement
    leadership    appoint, chief, director, board, ceo, chair
    (else)        "other"
A headline matching more than one is tagged by the first rule it hits, in the
order above (capacity first — a "new cancer centre" is capacity news even though
it likely also involves investment).

USAGE
    python3 scripts/refresh_private_provider_moves.py               # fetch all four
    python3 scripts/refresh_private_provider_moves.py --dry-run      # fetch, report, write nothing

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
import urllib.request

OUT_PATH = "data/private-provider-moves.json"

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                     "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
      "Accept": "text/html"}

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

CATEGORY_RULES = [
    ("capacity", re.compile(
        r"\bhospital\b|\bcentre\b|\bcenter\b|\bunit\b|\bward\b|\btheatre\b|\bbed(s)?\b|"
        r"\bexpand(s|ed|ing)?\b|\bopen(s|ed|ing)?\b", re.I)),
    ("investment", re.compile(
        r"\binvest(s|ed|ment|ing)?\b|£|\bmillion\b|\brefinanc\w*\b|\bfunding\b|\bacqui\w*\b",
        re.I)),
    ("partnership", re.compile(
        r"\bpartner(s|ship|ed|ing)?\b|\bcollaborat\w*\b|\bdeal\b|\bagreement\b", re.I)),
    ("leadership", re.compile(
        r"\bappoint(s|ed|ment)?\b|\bchief\b|\bdirector\b|\bboard\b|\bceo\b|\bchair\b", re.I)),
]


def categorise(title):
    for name, pattern in CATEGORY_RULES:
        if pattern.search(title):
            return name
    return "other"


def get(url, timeout=30, retries=3):
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503):
                time.sleep(10)
                attempt += 1
                if attempt >= retries:
                    raise
                continue
            raise
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(3 * attempt)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


# --------------------------------------------------------------------------- HCA
def fetch_hca():
    base = "https://www.hcahealthcare.co.uk"
    listing = base + "/about-us/news-and-press-releases"
    body = get(listing)
    rows = []
    # Cards: <time dateTime="ISO...">D Mon, YYYY</time>...<h3 ...><a href="/about-us/
    # news-and-press-releases/<slug>">TITLE</a></h3> — the ISO datetime attribute is
    # the reliable date source, the immediately-following <h3><a> is the title/link.
    for m in re.finditer(
        r'<time dateTime="(\d{4}-\d{2}-\d{2})[^"]*">.*?'
        r'<a href="(/about-us/news-and-press-releases/[a-z0-9\-]+)">([^<]{8,220})</a></h3>',
        body, re.S):
        date_iso, href, title = m.group(1), m.group(2), clean(m.group(3))
        if (m.start(2) - m.end(1)) > 500:
            continue  # date and link too far apart to be the same card
        rows.append({"provider": "HCA Healthcare UK", "title": title,
                     "url": base + href, "date": date_iso,
                     "category": categorise(title)})
    return rows


# ------------------------------------------------------------------------ RAMSAY
def fetch_ramsay():
    base = "https://www.ramsayhealth.co.uk"
    listing = base + "/about/news"
    body = get(listing)
    rows = []
    for m in re.finditer(
        r'<a href="(/about/news/[a-z0-9\-]+)">\s*<h3[^>]*>([^<]{8,220})</h3>',
        body):
        href, title = m.group(1), clean(m.group(2))
        window = body[m.end():m.end() + 600]
        date_m = re.search(
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+(20\d{2})', window)
        if not date_m:
            continue
        day, mon, year = date_m.groups()
        try:
            date_iso = dt.date(int(year), MONTHS[mon.lower()], int(day)).isoformat()
        except ValueError:
            continue
        rows.append({"provider": "Ramsay Health Care UK", "title": title,
                     "url": base + href, "date": date_iso,
                     "category": categorise(title)})
    return rows


# ----------------------------------------------------------------------- SPIRE
# Anywhere in the title, not just the start — shareholding-disclosure filings are
# sometimes prefixed with the discloser's own name ("Dimensional Fund Advisors
# Ltd. : Form 8.3 - ...").
FORM_RE = re.compile(r"\bform\s*8\.\d", re.I)


def fetch_spire():
    url = "https://www.investegate.co.uk/company/SPI"
    body = get(url)
    rows = []
    for m in re.finditer(
        r'<td>(\d{1,2}\s+[A-Za-z]{3}\s+20\d{2})</td>\s*<td>[^<]*</td>\s*<td>.*?</td>\s*<td>\s*'
        r'<a class="announcement-link" href="([^"]+)">([^<]+)</a>',
        body, re.S):
        date_txt, href, title = m.group(1), m.group(2), clean(m.group(3))
        if FORM_RE.search(title):
            continue
        try:
            date_iso = dt.datetime.strptime(date_txt, "%d %b %Y").date().isoformat()
        except ValueError:
            continue
        rows.append({"provider": "Spire Healthcare", "title": title,
                     "url": href, "date": date_iso,
                     "category": categorise(title)})
    return rows


# --------------------------------------------------------------------- NUFFIELD
def fetch_nuffield():
    base = "https://www.nuffieldhealth.com"
    listing = base + "/about-us/media-centre/press-releases"
    body = get(listing)
    rows = []
    for m in re.finditer(
        r'<h2 class="article-summary__heading"><a href="(/article/[a-z0-9\-]+)"[^>]*>'
        r'<span[^>]*>([^<]{8,260})</span>',
        body):
        href, title = m.group(1), clean(m.group(2))
        window = body[m.end():m.end() + 800]
        date_m = re.search(
            r'Published:\s*[A-Za-z]+\s+(\d{1,2})\s+(January|February|March|April|May|June|'
            r'July|August|September|October|November|December)\s+(20\d{2})', window)
        if not date_m:
            continue
        day, mon, year = date_m.groups()
        try:
            date_iso = dt.date(int(year), MONTHS[mon.lower()], int(day)).isoformat()
        except ValueError:
            continue
        rows.append({"provider": "Nuffield Health", "title": title,
                     "url": base + href, "date": date_iso,
                     "category": categorise(title)})
    return rows


FETCHERS = {
    "HCA Healthcare UK": fetch_hca,
    "Ramsay Health Care UK": fetch_ramsay,
    "Spire Healthcare": fetch_spire,
    "Nuffield Health": fetch_nuffield,
}

SOURCE_URLS = {
    "HCA Healthcare UK": "https://www.hcahealthcare.co.uk/about-us/news-and-press-releases",
    "Ramsay Health Care UK": "https://www.ramsayhealth.co.uk/about/news",
    "Spire Healthcare": "https://www.investegate.co.uk/company/SPI",
    "Nuffield Health": "https://www.nuffieldhealth.com/about-us/media-centre/press-releases",
}


def dedup_key(row):
    return row.get("url", "")


def assemble(all_rows, existing, per_provider_status, today):
    kept = {}
    for row in (existing or {}).get("_rows", []):
        kept[dedup_key(row)] = row
    for row in all_rows:
        kept[dedup_key(row)] = row

    # Keep a rolling window — 18 months — so the file doesn't grow without bound.
    cutoff = (today - dt.timedelta(days=548)).isoformat()
    ordered = sorted(
        (r for r in kept.values() if (r.get("date") or "") >= cutoff),
        key=lambda r: r.get("date") or "", reverse=True)

    by_provider = {}
    for row in ordered:
        by_provider[row["provider"]] = by_provider.get(row["provider"], 0) + 1

    doc = {
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "scopeRule": (
            "One row per dated announcement published directly by the provider itself "
            "(or, for Spire, its RNS regulatory announcements via investegate.co.uk — "
            "the FCA-approved Primary Information Provider route, not a secondary "
            "summary). No row is inferred or derived; the only judgement applied is the "
            "category tag, assigned by a fixed keyword match stated in the source file, "
            "never invented per item."
        ),
        "evidenceFloor": (
            "A provider is only tracked here when it has a genuine, directly fetchable, "
            "dated source. Circle Health Group does not — its site blocks automated "
            "fetching outright (Cloudflare) and no syndicated alternative exists for its "
            "routine announcements — so it is not tracked live and is shown as an "
            "honest empty state rather than filled with indirect or weak data."
        ),
        "sources": SOURCE_URLS,
        "coverage": {
            "trackedProviders": sorted(SOURCE_URLS.keys()),
            "notTracked": {"Circle Health Group": "Source is bot-protected; no viable "
                                                    "fetch route found — see evidenceFloor."},
            "fetchStatus": per_provider_status,
        },
        "counts": {"moves": len(ordered), "byProvider": by_provider},
        "moves": ordered,
        "_rows": ordered,
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
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    existing = load(OUT_PATH)
    today = dt.date.today()

    all_rows, status = [], {}
    for provider, fetcher in FETCHERS.items():
        try:
            rows = fetcher()
            status[provider] = "ok (%d row(s))" % len(rows)
            all_rows.extend(rows)
            print("  %-24s %d row(s)" % (provider, len(rows)))
        except Exception as exc:
            status[provider] = "FAILED: %s" % exc
            print("  %-24s FAILED: %s" % (provider, exc))
        time.sleep(0.5)

    doc = assemble(all_rows, existing, status, today)
    print("\n%d move(s) held. By provider: %s" % (doc["counts"]["moves"], doc["counts"]["byProvider"]))

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    write(doc)
    print("\nwrote %s. Now: python3 scripts/stamp_notice.py && python3 verify.py" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
