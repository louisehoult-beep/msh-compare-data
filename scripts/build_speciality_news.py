#!/usr/bin/env python3
"""build_speciality_news.py — build data/speciality-news/<slug>.json.

WHY THIS EXISTS. Found 15/09/2026: the Hub's cloud-pipeline (a separate repo,
louisehoult-beep/medical-sales-hub-pipeline) has tagged 29 trade-press RSS
sources with a speciality slug in sources.py since 18/08/2026, and its own
comments say a "publish_speciality.py" writes matched items onto each
speciality page's News band. That script does not exist, no workflow calls
it, and the fetch engine there never even carries the specialities tag
through to a stored item. Every speciality page's News content has been
100% hand-written and never refreshed since its build pass as a result.
See 02-Elevate-and-Thrive/Hub/speciality-page-news-pipeline-gap-2026-09-15.md.

THE FIX, HERE NOT THERE. Rather than repair cloud-pipeline's much larger,
already-complex engine, this script is a small, independent, stdlib-only
fetcher that lives beside the OTHER thing that already renders live content
onto a speciality page: app/speciality-panels.js, added 07/09/2026, which
reads data/speciality-panels/<slug>.json from THIS repo via a raw.githubusercontent
loader script sitting on the WordPress page. app/speciality-news.js (added with
this script) follows the exact same pattern for the same reason: it works, it
is proven live, and a WordPress page never needs re-touching once its loader
is in place.

THE SOURCE LIST. SOURCES below is a synced copy of the 29 entries in
cloud-pipeline/sources.py that carry feeds=["speciality_pages"], as read
15/09/2026. It is a COPY, not an import — the two repos are not checked out
together in CI. If a source is added, removed, or re-tagged in sources.py,
this list needs the same edit by hand. That drift risk is written down here
on purpose rather than solved with a cross-repo dependency this repo's CI
cannot resolve.

THE EVIDENCE FLOOR (root rule 14). A speciality with no source in SOURCES
gets an EMPTY list, never a guess pulled from an untagged general feed. The
renderer (app/speciality-news.js) shows an honest empty state for that case,
the same as speciality-panels.js does for a speciality with no panel rule.

THE PIPELINE MERGE (added 16/09/2026). SOURCES above is trade press: fetched,
not individually checked. The cloud-pipeline repo separately produces
data/speciality-intel.json (speciality_handoff.py, landed there as 0b487f3) —
items it has ranked and, for the cowork_intel ones, that intel-ingest verified
at source, each carrying a controlled speciality slug. Those are a HIGHER tier
of content than an RSS title, and Lou's 16/09 decision was that a sales
opportunity belongs on the speciality page as well as in the Rep's Briefing.
fetch_pipeline_intel() merges them into the same per-slug lists, tagged
verified=True so the renderer can label and badge them differently.

  * That repo is PRIVATE, so raw.githubusercontent 404s anonymously. This
    reads the GitHub Contents API with a token instead (PIPELINE_TOKEN_ENV),
    which is why the workflow passes secrets.PIPELINE_READ_TOKEN through. The
    merge happens server-side in CI; what a member's browser fetches is still
    only the PUBLIC file this script writes in this repo, so no token is ever
    exposed to a page.
  * NO TOKEN, OR A FAILED FETCH, IS NOT AN ERROR. The run continues with trade
    press alone and says so loudly in the log. That keeps local dry runs
    working with no credentials at all, and keeps one repo's outage from
    failing the other repo's daily build.

CADENCE AND FRESHNESS. Items older than MAX_AGE_DAYS are dropped before
writing — a "what changed this month" band should not still be citing a
six-month-old article. Each file keeps at most ITEMS_PER_SPECIALITY entries,
newest first.

Usage
    python3 scripts/build_speciality_news.py                # every tagged speciality
    python3 scripts/build_speciality_news.py --only ijtr_toc
    python3 scripts/build_speciality_news.py --dry-run
"""
import argparse
import datetime
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "data", "speciality-news")

MAX_AGE_DAYS = 60
ITEMS_PER_SPECIALITY = 6
FETCH_TIMEOUT = 20
UA = "Mozilla/5.0 (compatible; MedSalesHub/1.0; +https://medsalesintelligencehub.co.uk)"

# --- cloud-pipeline handoff (see "THE PIPELINE MERGE" in the docstring) ------
# The Contents API, NOT raw.githubusercontent: the pipeline repo is private, and
# raw 404s for a private repo even with a token on the request. The Contents
# endpoint honours Authorization, and with Accept: application/vnd.github.raw it
# returns the file body itself rather than the base64-in-JSON wrapper.
PIPELINE_INTEL_URL = ("https://api.github.com/repos/louisehoult-beep/"
                      "medical-sales-hub-pipeline/contents/data/speciality-intel.json")
PIPELINE_TOKEN_ENV = "PIPELINE_READ_TOKEN"
# What a member sees under a merged item. Deliberately names the Hub, not the
# upstream RSS feed or the pipeline's internal source_id, because the point of
# the label is the TIER of checking, not the plumbing.
PIPELINE_LABEL = "Hub intelligence"

# Synced from cloud-pipeline/sources.py, feeds=["speciality_pages"] entries, 15/09/2026.
# id/name/url/specialities only — everything else in that registry (cadence, category)
# is cloud-pipeline's own concern, not needed here.
SOURCES = [
    {"id": "vascular_news", "name": "Vascular News", "url": "https://vascularnews.com/feed/",
     "specialities": ["vascular-surgery-and-pad"]},
    {"id": "cardiovascular_news", "name": "Cardiovascular News", "url": "https://cardiovascularnews.com/feed/",
     "specialities": ["cardiology-and-cardiac-surgery"]},
    {"id": "cardiac_rhythm_news", "name": "Cardiac Rhythm News", "url": "https://cardiacrhythmnews.com/feed/",
     "specialities": ["cardiology-and-cardiac-surgery"]},
    {"id": "interventional_news", "name": "Interventional News", "url": "https://interventionalnews.com/feed/",
     "specialities": ["interventional-radiology"]},
    {"id": "jowc_toc", "name": "Journal of Wound Care (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=jowc&type=etoc&feed=rss",
     "specialities": ["tissue-viability-and-wound-care"]},
    {"id": "bjca_toc", "name": "British Journal of Cardiac Nursing (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=bjca&type=etoc&feed=rss",
     "specialities": ["cardiology-and-cardiac-surgery"]},
    {"id": "bjnn_toc", "name": "British Journal of Neuroscience Nursing (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=bjnn&type=etoc&feed=rss",
     "specialities": ["neurology-and-neurosurgery", "stroke"]},
    {"id": "bjom_toc", "name": "British Journal of Midwifery (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=bjom&type=etoc&feed=rss",
     "specialities": ["maternity-and-neonatal"]},
    {"id": "ijpn_toc", "name": "International Journal of Palliative Nursing (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=ijpn&type=etoc&feed=rss",
     "specialities": ["palliative-and-end-of-life-care"]},
    {"id": "jpar_toc", "name": "Journal of Paramedic Practice (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=jpar&type=etoc&feed=rss",
     "specialities": ["emergency-and-urgent-care"]},
    {"id": "nrec_toc", "name": "Nursing and Residential Care (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=nrec&type=etoc&feed=rss",
     "specialities": ["frailty-and-older-people"]},
    {"id": "pnur_toc", "name": "Practice Nursing (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=pnur&type=etoc&feed=rss",
     "specialities": ["primary-care-and-general-practice"]},
    {"id": "ijtr_toc", "name": "International Journal of Therapy and Rehabilitation (contents)",
     "url": "https://www.magonlinelibrary.com/action/showFeed?jc=ijtr&type=etoc&feed=rss",
     # Was also tagged to patient-handling (2913, formerly "Therapies") until
     # 16/09/2026 — dropped on the slug rename because a general therapy-and-rehab
     # ToC feed is a poor fit for a page now specifically about moving/handling
     # equipment and technique, not physio/OT research.
     "specialities": ["rehabilitation-prosthetics-and-orthotics"]},
    {"id": "wounds_uk", "name": "Wounds UK", "url": "https://wounds-uk.com/feed/",
     "specialities": ["tissue-viability-and-wound-care"]},
    {"id": "ivteam", "name": "IVTeam", "url": "https://www.ivteam.com/feed/",
     "specialities": ["vascular-access-and-iv-therapy"]},
    {"id": "ips_infection", "name": "Infection Prevention Society", "url": "https://www.ips.uk.net/rss",
     "specialities": ["infection-prevention-and-control"]},
    {"id": "rcem_news", "name": "Royal College of Emergency Medicine", "url": "https://rcem.ac.uk/feed/",
     "specialities": ["emergency-and-urgent-care"]},
    {"id": "sepsis_trust", "name": "UK Sepsis Trust", "url": "https://sepsistrust.org/feed/",
     "specialities": ["sepsis-and-the-deteriorating-patient"]},
    {"id": "afpp_theatres", "name": "AfPP", "url": "https://www.afpp.org.uk/feed/",
     "specialities": ["theatres-and-surgical"]},
    {"id": "bopa_oncology", "name": "British Oncology Pharmacy Association", "url": "https://www.bopa.org.uk/feed/",
     "specialities": ["oncology-and-sact"]},
    {"id": "bapen_nutrition", "name": "BAPEN", "url": "https://www.bapen.org.uk/feed/",
     "specialities": ["nutrition-and-dietetics"]},
    {"id": "aso_obesity", "name": "Association for the Study of Obesity", "url": "https://aso.org.uk/feed/",
     "specialities": ["obesity-and-weight-management"]},
    {"id": "rcophth", "name": "Royal College of Ophthalmologists", "url": "https://www.rcophth.ac.uk/feed/",
     "specialities": ["ophthalmology"]},
    {"id": "bapo_orthotics", "name": "British Association of Prosthetists and Orthotists", "url": "https://www.bapo.com/feed/",
     "specialities": ["rehabilitation-prosthetics-and-orthotics"]},
    {"id": "diabetes_times", "name": "Diabetes Times", "url": "https://diabetestimes.co.uk/feed/",
     "specialities": ["diabetes-and-endocrinology"]},
    {"id": "htn_health_tech", "name": "HTN", "url": "https://htn.co.uk/feed/",
     "specialities": ["digital-and-medical-it"]},
    {"id": "pulse_today", "name": "Pulse Today", "url": "https://www.pulsetoday.co.uk/feed/",
     "specialities": ["primary-care-and-general-practice"]},
    {"id": "nursing_in_practice", "name": "Nursing in Practice", "url": "https://www.nursinginpractice.com/feed/",
     "specialities": ["primary-care-and-general-practice"]},
    {"id": "bgs_news", "name": "British Geriatrics Society", "url": "https://www.bgs.org.uk/rss.xml",
     "specialities": ["frailty-and-older-people"]},
]


def log(msg):
    print(msg, file=sys.stderr)


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_pubdate(raw):
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except ValueError:
            continue
    return None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        return r.read()


def _local(tag):
    """Strip a {namespace}tag down to its bare local name. RSS 1.0/RDF feeds
    (e.g. the magonlinelibrary.com journal TOCs) declare xmlns="...rss/1.0/"
    as the DEFAULT namespace, which puts every element — <item>, <title>,
    <link> — inside that namespace. A plain './/item' search finds nothing
    against that, silently, which is exactly what happened here: those nine
    feeds all came back "0 items" on the first pass despite fetching fine.
    Matching by local name instead works uniformly across RSS 2.0 (no
    namespace), RSS 1.0/RDF (default namespace) and Atom (its own namespace),
    without needing to special-case any of them."""
    return tag.rsplit("}", 1)[-1]


def _child_text(el, *names):
    """First matching child's text, by local name, trying each name in order."""
    for child in el:
        if _local(child.tag) in names:
            return (child.text or "").strip()
    return ""


def parse_feed(raw_bytes, source_name):
    """Parses RSS 2.0, RSS 1.0/RDF, or Atom — whichever the feed turns out to
    be, matched by local element name so the default-namespace RDF case
    doesn't silently return nothing. Returns a list of
    {title, link, published, summary}, published as a UTC ISO string or None."""
    items = []
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as e:
        log("  PARSE ERROR (%s): %s" % (source_name, e))
        return items

    # RSS 2.0 and RSS 1.0/RDF both use <item>; Atom uses <entry>.
    for it in root.iter():
        tag = _local(it.tag)
        if tag == "item":
            title = strip_tags(_child_text(it, "title"))
            link = _child_text(it, "link")
            pub = _child_text(it, "pubDate", "date")   # "date" catches dc:date
            dt = parse_pubdate(pub)
            summary = strip_tags(_child_text(it, "description", "summary"))
            if title and link:
                items.append({"title": title, "link": link,
                              "published": dt.isoformat() if dt else None, "summary": summary[:220]})
        elif tag == "entry":
            title = strip_tags(_child_text(it, "title"))
            link = ""
            for child in it:
                if _local(child.tag) == "link":
                    link = child.get("href") or (child.text or "").strip()
                    break
            pub = _child_text(it, "updated", "published")
            dt = parse_pubdate(pub)
            summary = strip_tags(_child_text(it, "summary", "content"))
            if title and link:
                items.append({"title": title, "link": link,
                          "published": dt.isoformat() if dt else None, "summary": summary[:220]})
    return items


def pipeline_entry(row):
    """One cloud-pipeline row -> this script's own item shape.

    The two sides name the same things differently (url/link, date/published)
    and the renderer only understands this side's names. `verified` and
    `opportunity` are additions, not renames: they carry WHY the item is on the
    page, which is what app/speciality-news.js badges and labels on."""
    return {
        "title": row.get("title", ""),
        "link": row.get("url", ""),
        "published": row.get("date") or None,
        "summary": (row.get("summary") or "")[:220],
        "source": PIPELINE_LABEL,
        "verified": True,
        "opportunity": bool(row.get("opportunity")),
    }


def fetch_pipeline_intel(token=None):
    """Fetch the cloud-pipeline handoff. Returns {slug: [entry, ...]}.

    Returns {} — never raises — when there is no token, the fetch fails, or the
    body is not the document we expect. A speciality page losing its merged
    rows for a day is a bad day; this repo's daily build failing outright, and
    every page's trade-press band going stale with it, is a worse one."""
    token = token if token is not None else os.environ.get(PIPELINE_TOKEN_ENV, "")
    if not token:
        log("pipeline intel: no %s in the environment — trade press only this run. "
            "(Expected locally; in CI it means the secret is missing.)" % PIPELINE_TOKEN_ENV)
        return {}

    req = urllib.request.Request(PIPELINE_INTEL_URL, headers={
        "User-Agent": UA,
        "Accept": "application/vnd.github.raw",
        "Authorization": "Bearer %s" % token,
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
            doc = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
            ValueError) as e:
        log("pipeline intel: FETCH FAILED (%s) — trade press only this run. Merged "
            "items will be absent from every page until the next successful run." % e)
        return {}

    data = doc.get("specialities") if isinstance(doc, dict) else None
    if not isinstance(data, dict):
        log("pipeline intel: unexpected document shape — no 'specialities' object. "
            "Trade press only this run.")
        return {}

    out = {}
    for slug, rows in data.items():
        if not isinstance(rows, list):
            continue
        entries = [pipeline_entry(r) for r in rows if isinstance(r, dict)]
        entries = [e for e in entries if e["title"] and e["link"]]
        if entries:
            out[slug] = entries
    log("pipeline intel: %d row(s) across %d speciality page(s)"
        % (sum(len(v) for v in out.values()), len(out)))
    return out


def build(only_id=None, dry_run=False, pause=0.6):
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=MAX_AGE_DAYS)

    by_speciality = {}   # slug -> list of {title, link, published, summary, source}
    fetch_errors = []

    for src in SOURCES:
        if only_id and src["id"] != only_id:
            continue
        log("fetching %s (%s)" % (src["id"], src["url"]))
        try:
            raw = fetch(src["url"])
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            log("  FETCH ERROR: %s" % e)
            fetch_errors.append({"id": src["id"], "error": str(e)})
            time.sleep(pause)
            continue

        items = parse_feed(raw, src["name"])
        kept = 0
        for it in items:
            dt = parse_pubdate(it["published"]) if it["published"] else None
            # An item with no parseable date is kept (some journal TOC feeds
            # carry no pubDate at all) but never used to push an OLDER, dated
            # item off the cap — it sorts after every dated item.
            if dt is not None and dt < cutoff:
                continue
            entry = dict(it)
            entry["source"] = src["name"]
            for slug in src["specialities"]:
                by_speciality.setdefault(slug, []).append(entry)
            kept += 1
        log("  %d item(s) within %dd" % (kept, MAX_AGE_DAYS))
        time.sleep(pause)

    # Merge the cloud-pipeline handoff on top of the trade press. Done for an
    # --only run too: that run rewrites its source's slug files, and skipping
    # the merge there would silently strip those pages' verified rows until the
    # next full run.
    pipeline = fetch_pipeline_intel()
    for slug, entries in pipeline.items():
        by_speciality.setdefault(slug, []).extend(entries)

    if only_id:
        # Partial run for one source — do not touch every other speciality's
        # file. Note the pipeline's own slugs deliberately do NOT widen this
        # set: writing a slug this run never fetched RSS for would rewrite its
        # file with merged rows only, wiping its trade-press items.
        touched = set()
        for src in SOURCES:
            if src["id"] == only_id:
                touched.update(src["specialities"])
        slugs = touched
    else:
        slugs = {s for src in SOURCES for s in src["specialities"]}
        slugs |= set(pipeline)

    if dry_run:
        for slug in sorted(slugs):
            got = by_speciality.get(slug, [])
            log("--- %s: %d item(s) (%d merged, %d opportunity)"
                % (slug, len(got),
                   sum(1 for i in got if i.get("verified")),
                   sum(1 for i in got if i.get("opportunity"))))
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    for slug in sorted(slugs):
        items = by_speciality.get(slug, [])

        def sort_key(it):
            dt = parse_pubdate(it["published"]) if it["published"] else None
            return dt or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

        items.sort(key=sort_key, reverse=True)
        # Second, STABLE sort: anything flagged as a sales opportunity goes to
        # the top, newest-first order preserved inside each group. A rep opening
        # a speciality page wants the thing to act on first; Lou, 16/09/2026.
        # This runs after the cap-free date sort and before the cap, so an
        # opportunity can never be cut by six older trade-press headlines.
        items.sort(key=lambda it: 0 if it.get("opportunity") else 1)
        items = items[:ITEMS_PER_SPECIALITY]
        doc = {
            "speciality": slug,
            "generatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "maxAgeDays": MAX_AGE_DAYS,
            "items": items,
        }
        path = os.path.join(OUT_DIR, "%s.json" % slug)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        log("wrote %s (%d item(s))" % (path, len(items)))

    if fetch_errors:
        log("%d source(s) failed to fetch this run — their specialities keep " % len(fetch_errors)
            + "whatever this run already gathered from any OTHER source tagged to the same slug, "
            + "or an empty list if that was the only one:")
        for e in fetch_errors:
            log("  %s: %s" % (e["id"], e["error"]))

    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run a single source id, e.g. ijtr_toc")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return build(only_id=args.only, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
