#!/usr/bin/env python3
"""refresh_acquirer_press.py — LSE RNS acquisition sweep for Hub suppliers'
listed parent companies.

WHY THIS EXISTS (added 25/08/2026)
-----------------------------------
scripts/refresh_company_press.py finds news by querying each Hub SUPPLIER's own
name on Google News. It cannot find an acquisition of that supplier by a listed
group, because the story is filed under the ACQUIRER's name, not the target's,
and a small bolt-on rarely gets independent trade-press coverage at all.

Live example that exposed the gap (25/08/2026): Altomed Limited (on the Hub,
Complete Ophthalmology Solutions 3 framework) was bought by Halma plc for £29m
in February 2026, folded into Halma's ophthalmic group MST. Six months later
data/company-press.json still held nothing for Altomed. The deal was never
issued as its own "Acquisition"-category RNS either — it only surfaced inside
Halma's 12 March 2026 trading update. A feed that only watches the Acquisition
category on the acquirer's own page would have missed it too.

WHAT THIS SCRIPT DOES
----------------------
For each LISTED ACQUIRER in TRACKED_ACQUIRERS, it reads that company's public
RNS history from investegate.co.uk (no login, no API key) across the categories
in WATCHED_CATEGORIES, fetches the full text of announcements not yet processed,
and tests that text against every Hub supplier's own recorded aliases using
scripts/press_match.identify() — the SAME identity rule refresh_company_press.py
uses, so a match here means the same thing a match there means.

A hit is never written straight into data/supplier-seed.json. That file is
CURATED and human-owned (see its own "note" field) — a script writing into it
unattended is exactly the failure mode root rule 13 exists to prevent. Instead
every hit is appended to state/pending-acquirer-matches.json for a person to
review and, if it holds up, copy into the supplier's `news` array by hand (see
Process flows for all brands/hub-acquirer-news-sourcing.md for the exact
shape that app/company-report.js actually renders — headline/date/sources[],
not the older text/url shape some seed entries still carry).

WHY state/, NOT data/ — this file is a curator's review queue, never rendered
on the Hub, so it carries none of data/'s public-facing content and does not
need the ownership notice/marker ref every data/*.json file must carry
(verify.py's check_notice enforces that for data/, and does not scan state/,
the same way state/company-press-rotation.json already doesn't carry one).
Minting a new data/ ref needs the private salt in ~/.eth-marker-salt to
reproduce every ref already in scripts/stamp_notice.py — it did not on
25/08/2026 (see scripts/mint_data_ref.py), which is a separate, pre-existing
problem worth someone checking, not something to route around by guessing a
ref for this file.

An acquisition that names no known Hub supplier is still logged, to
state/pending-acquirer-matches.json under "unmatched" — it may be the FIRST
sighting of a company that should be added to the seed, which is its own kind
of finding.

TRACKED_ACQUIRERS — HOW TO EXTEND
----------------------------------
Start conservative: only Halma plc is seeded, because that is the case that is
actually proven today. Add another listed group ONLY once you have confirmed,
by hand, that it owns (or has owned) at least one company already on the Hub —
otherwise this script spends its whole budget watching a company with no
Hub relevance. Verify the investegate ticker resolves (HTTP 200, a real
per-company RNS listing, not a search/404 page) before adding it; the script
WARNs and skips any ticker that doesn't resolve rather than failing the whole run.

Usage
    python3 scripts/refresh_acquirer_press.py
    python3 scripts/refresh_acquirer_press.py --only "Halma plc"
    python3 scripts/refresh_acquirer_press.py --dry-run

Stdlib only. Exits 0 on a degraded run — a throttled fetch keeps what was there.
"""
import argparse
import datetime
import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import press_match                                            # noqa: E402

REPO = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = REPO / "data"
SEED = DATA / "supplier-seed.json"
OUT = REPO / "state" / "pending-acquirer-matches.json"
STATE = REPO / "state" / "acquirer-press-rotation.json"

UA = "Mozilla/5.0 (msh-compare-data; acquirer-press; contact@elevateandthrive.uk)"
PAUSE = 2.0                    # seconds between investegate fetches — polite, public site
LOOKBACK_DAYS = 730             # how far back a NEW acquirer's history is swept on first run

# Categories that have, in practice, carried a bolt-on acquisition. "Acquisition"
# alone is not enough — Altomed never got its own Acquisition-category RNS; it
# only ever appeared inside a Trading Update. See module docstring.
WATCHED_CATEGORIES = {
    "acquisition", "trading update", "trading statement", "interim results",
    "half-year report", "full year results", "annual financial report",
    "preliminary results", "final results",
}

ACQUISITION_KEYWORDS = [
    "acqui", "bolt-on", "bolt on", "bought", "purchase of", "acquired",
]

TRACKED_ACQUIRERS = [
    # name, ticker (investegate's per-company page is /company/<TICKER> — the
    # slug format in its own announcement links, e.g. "halma--hlma", redirects
    # to the site-wide live feed instead, not this company's history; proven
    # 25/08/2026, use the bare ticker), why it's tracked (a fact, checkable,
    # not a guess) — every entry here MUST already own a company on the Hub.
    {
        "name": "Halma plc",
        "ticker": "HLMA",
        "why": ("Owns Altomed Limited (Hub supplier, Complete Ophthalmology Solutions 3), "
                "via its Healthcare Sector company MST. Confirmed 25/08/2026."),
    },
    # Add the next one only after verifying it owns a Hub supplier by hand —
    # see the module docstring.
]

log = lambda m: print("[acquirer-press]", m)


# ---------------------------------------------------------------------------
def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def load_json(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def today_iso():
    return datetime.date.today().isoformat()


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s))).strip()


# ---------------------------------------------------------------------------
def list_announcements(ticker):
    """[(date_iso, category, url, ann_id), ...] from an investegate company page.

    Returns None if the page did not resolve to a real per-company listing
    (wrong/stale ticker) rather than guessing.
    """
    url = "https://www.investegate.co.uk/company/%s" % ticker
    try:
        page = fetch(url)
    except Exception as e:
        log("  fetch failed for %s: %s" % (ticker, e))
        return None
    if "RNS Announcements" not in page and "announcement-link" not in page:
        return None
    out = []
    for row in re.findall(r"<tr[^>]*>.*?</tr>", page, re.S):
        m_date = re.search(r"<td>(\d{2} \w{3} \d{4})</td>", row)
        m_link = re.search(
            r'<a class="announcement-link" href="(https://www\.investegate\.co\.uk/'
            r'announcement/rns/[^"]+/([^"/]+)/(\d+))"[^>]*>([^<]*)</a>', row)
        if not (m_date and m_link):
            continue
        try:
            date_iso = datetime.datetime.strptime(m_date.group(1), "%d %b %Y").date().isoformat()
        except Exception:
            continue
        category = strip_tags(m_link.group(4)).lower()
        out.append((date_iso, category, m_link.group(1), m_link.group(3)))
    return out


def fetch_body(url):
    """Plain text of one announcement page — heading + released text."""
    try:
        page = fetch(url)
    except Exception:
        return ""
    page = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    page = re.sub(r"<style.*?</style>", " ", page, flags=re.S)
    text = strip_tags(page)
    # The useful text starts at the page <title>; drop the nav/head boilerplate
    # before it so keyword/alias matching isn't diluted by menu text.
    marker = re.search(r"\| Company Announcement \| Investegate", text)
    return text[marker.end():marker.end() + 6000] if marker else text[:6000]


def has_acquisition_language(text):
    t = text.lower()
    return any(k in t for k in ACQUISITION_KEYWORDS)


# ---------------------------------------------------------------------------
def sweep_acquirer(entry, seed, universe, state, only_all=False):
    ticker = entry["ticker"]
    anns = list_announcements(ticker)
    if anns is None:
        log("  WARN %-20s ticker did not resolve to a real RNS listing — skipping "
            "(check TRACKED_ACQUIRERS)" % entry["name"])
        return [], [], state
    seen = set(state.get(ticker, {}).get("seenIds") or [])
    cutoff = (datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat()

    matches, unmatched = [], []
    checked = 0
    for date_iso, category, url, ann_id in anns:
        if category not in WATCHED_CATEGORIES:
            continue
        if date_iso < cutoff:
            continue
        if not only_all and ann_id in seen:
            continue
        time.sleep(PAUSE)
        body = fetch_body(url)
        checked += 1
        seen.add(ann_id)
        if not body or not has_acquisition_language(body):
            continue

        item = {"headline": category, "summary": body}
        hit_any = False
        for s in seed.get("suppliers") or []:
            alias = press_match.identify(s, item, universe)
            if not alias:
                continue
            hit_any = True
            matches.append({
                "acquirer": entry["name"],
                "supplierMatched": s.get("name"),
                "matchedAlias": alias,
                "date": date_iso,
                "category": category,
                "url": url,
                "excerpt": body[:500],
                "foundOn": today_iso(),
            })
        if not hit_any:
            unmatched.append({
                "acquirer": entry["name"],
                "date": date_iso,
                "category": category,
                "url": url,
                "excerpt": body[:500],
                "foundOn": today_iso(),
            })

    state.setdefault(ticker, {})["seenIds"] = sorted(seen)
    state[ticker]["lastChecked"] = today_iso()
    log("  %-20s %d announcement(s) checked this run, %d supplier match(es), %d unmatched"
        % (entry["name"], checked, len(matches), len(unmatched)))
    return matches, unmatched, state


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", default="", help="comma-separated acquirer names")
    ap.add_argument("--all", action="store_true",
                     help="re-check every watched announcement in the lookback window, "
                          "ignoring the seen-ids skip — for a manual full sweep only")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    seed = load_json(SEED, {"suppliers": []})
    if not seed.get("suppliers"):
        sys.exit("data/supplier-seed.json holds no suppliers — refusing to run")
    universe = press_match.alias_universe(seed)

    state = load_json(STATE, {}) or {}
    existing = load_json(args.out, {"matches": [], "unmatched": []})

    wanted = set(n.strip() for n in args.only.split(",") if n.strip()) if args.only else None
    acquirers = [a for a in TRACKED_ACQUIRERS if not wanted or a["name"] in wanted]
    if not acquirers:
        sys.exit("no tracked acquirer matches --only")

    all_matches, all_unmatched = [], []
    for entry in acquirers:
        m, u, state = sweep_acquirer(entry, seed, universe, state, only_all=args.all)
        all_matches.extend(m)
        all_unmatched.extend(u)

    # De-dupe against what's already pending, by (acquirer, url) — a match found
    # again on a later run (e.g. re-run with --all) doesn't duplicate the queue.
    def key(d):
        return (d.get("acquirer"), d.get("url"), d.get("supplierMatched", ""))

    seen_keys = {key(d) for d in existing.get("matches", [])}
    for m in all_matches:
        if key(m) not in seen_keys:
            existing["matches"].append(m)
            seen_keys.add(key(m))
    seen_u = {(d.get("acquirer"), d.get("url")) for d in existing.get("unmatched", [])}
    for u in all_unmatched:
        if (u.get("acquirer"), u.get("url")) not in seen_u:
            existing["unmatched"].append(u)
            seen_u.add((u.get("acquirer"), u.get("url")))

    existing["dataAsOf"] = datetime.date.today().strftime("%d/%m/%Y")
    existing["generated"] = datetime.datetime.utcnow().isoformat() + "Z"
    existing["source"] = ("Investegate.co.uk (public RNS aggregator, no login), one company "
                           "listing page per tracked acquirer, categories: %s."
                           % ", ".join(sorted(WATCHED_CATEGORIES)))
    existing["howToUse"] = (
        "Every row here is a CANDIDATE, not a published fact. A match under "
        "'matches' means press_match.identify() found one of a Hub supplier's own "
        "recorded aliases inside an acquisition-flavoured RNS announcement from a "
        "tracked listed acquirer. Read the excerpt and the source URL, then, if it "
        "holds up, add it BY HAND to that supplier's `news` array in "
        "data/supplier-seed.json in the shape app/company-report.js actually "
        "renders: {\"headline\",\"date\",\"sources\":[{\"publisher\",\"url\"}, ...]} "
        "with at least two distinct sources, or the Press panel holds it back. "
        "Rows under 'unmatched' are acquisitions by a tracked group that named no "
        "company currently in the seed — possibly a company that should be added.")
    existing["counts"] = {"matches": len(existing["matches"]), "unmatched": len(existing["unmatched"])}
    existing["trackedAcquirers"] = [{"name": a["name"], "ticker": a["ticker"], "why": a["why"]}
                                     for a in TRACKED_ACQUIRERS]

    log("total pending: %d match(es), %d unmatched acquisition(s)"
        % (existing["counts"]["matches"], existing["counts"]["unmatched"]))

    if args.dry_run:
        log("DRY RUN — nothing written")
        return 0

    pathlib.Path(args.out).write_text(
        json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log("wrote %s and %s" % (args.out, STATE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
