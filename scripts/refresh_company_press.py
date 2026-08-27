#!/usr/bin/env python3
"""refresh_company_press.py — build data/company-press.json.

WHAT THIS REPLACES
------------------
build_supplier_index.py already had a verified-news feature: Google News RSS per
company, clustered by headline, kept only where two distinct reputable
publishers carried it. Two things stopped it being a feature anybody could use.

1. THROUGHPUT. NEWS_MAX = 30 companies a run, taken in a STABLE order that put
   the curated suppliers first. There are 1,216 suppliers in the seed and 1,215
   are curated, so the same top-30 were re-queried every night and supplier 31
   onwards was never reached. Measured 18/08/2026: 21 of 1,334 supplier records
   carried any news at all - 1.6%.
2. NO FALSE-POSITIVE GUARD. The query was the display name in quotes, and
   anything that came back was attributed. See scripts/press_match.py for the
   live example that makes this unsafe.

This script fixes both, and writes a separate file rather than into
supplier-seed.json - which is one minified line, so every parallel edit to it
conflicts.

ROTATION, AND WHY THESE NUMBERS
-------------------------------
Every supplier is reached on a fixed cycle, oldest-checked first:

  * suppliers carrying a curated `note` (the ones a member is most likely to
    open a report on)      -> PRESS_CYCLE_NOTED_DAYS = 14
  * every other supplier                                -> PRESS_CYCLE_OTHER_DAYS = 35

The daily query count is DERIVED from those cycles, not typed: ceil(n/cycle) per
tier. On the 18/08/2026 seed (1,045 noted, 171 other) that is 75 + 5 = 80
queries a day, capped by PRESS_DAILY_CAP = 90. Eighty queries at a 2-second
pause is about 5 minutes of requests against Google News once a day, which is
polite for a public RSS endpoint and roughly 2.7x what the old code did while
covering 40x more suppliers.

Selection is by OLDEST lastPressCheck first, with never-checked sorting first.
That is what stops the head of the list being re-queried: a supplier checked
today sorts to the back until every other supplier in its tier has been reached.
No supplier can go unchecked indefinitely.

The stamps live in state/company-press-rotation.json, NOT in supplier-seed.json.

LINKS
-----
Google News RSS gives a news.google.com redirect, not the publisher's URL. 97%
of the links the old feature published (132 of 136) were those redirects. This
script resolves them to the real article through Google's own
DotsSplashUi/batchexecute endpoint and records the publisher and resolved URL.
Where a link will not resolve it is KEPT and marked
`"urlType": "google-news-redirect"` - never dressed up as a publisher link.
Resolutions are cached in the state file, so a link is resolved once.

Usage
    python3 scripts/refresh_company_press.py                 # a scheduled run
    python3 scripts/refresh_company_press.py --limit 20
    python3 scripts/refresh_company_press.py --only "GBUK Group,Abbott Diabetes Care"
    python3 scripts/refresh_company_press.py --dry-run --only "Jeenie Solutions"
    python3 scripts/refresh_company_press.py --merge OURS.json   # see MERGING

MERGING (the rebase defect, NOTE-company-intelligence-rebase-merge-defect-2026-08-14)
-------------------------------------------------------------------------------
A generated JSON file must never be text-merged. `-X theirs` keeps the other
writer's non-conflicting hunks, which produced a company-awards.json with the
counts header from one generation and the rows from another. So this file is
never merged by git. After a rejected push the workflow takes ORIGIN's copy,
then runs `--merge OURS.json`, which merges SUPPLIER BLOCK BY SUPPLIER NAME
(a block's lastChecked and items belong together and move together) and then
RECOMPUTES the counts header from the rows it ended up with. The header is
therefore always derived, never carried over.

Stdlib only. Exits 0 on a degraded run - a throttled fetch keeps what was there.
"""
import argparse
import datetime
import html
import json
import math
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import press_match                                            # noqa: E402
import stamp_notice                                           # noqa: E402

REPO = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = REPO / "data"
SEED = DATA / "supplier-seed.json"
OUT = DATA / "company-press.json"
STATE = REPO / "state" / "company-press-rotation.json"

# --- rotation -------------------------------------------------------------
PRESS_CYCLE_NOTED_DAYS = 14
PRESS_CYCLE_OTHER_DAYS = 35
PRESS_DAILY_CAP = 90          # hard ceiling on queries per run, whatever the maths says

# --- priority handoff from the Live Desk (27/08/2026) ----------------------
# The rotation is fair but slow: 1,181 suppliers at ~79 a day is a 14-day cycle
# for a noted supplier. On 27/08/2026 Boston Scientific's last check was 18/08,
# its cyberattack broke on the 26th, and its next turn was ~01/09 — so the
# SUPPLIER PRESS panel could not have carried the company's biggest news of the
# year. Reordering the rotation itself was considered and rejected: it just
# trades one company's freshness for another's.
#
# Instead the Live Desk, which already identifies suppliers in the news in order
# to rank them, writes the names to a file and DELIVERS it into this repo at
# state/supplier-press-priority.json. This run reads that local file.
#
# ⚠️ IT USED TO FETCH THE FILE OVER AN UNAUTHENTICATED RAW-CONTENT URL FROM THE
# PIPELINE REPO. That never worked once, and could not have: that repo is
# PRIVATE, so an unauthenticated raw fetch returns 404. Because every failure
# path here returns [], the 404 was indistinguishable from "no supplier had news
# today" and the feature looked healthy while doing nothing. Proved on
# 27/08/2026: the Live Desk flagged Boston Scientific at 16:38 and the 17:56
# sweep never queried it. DO NOT reintroduce a cross-repo fetch of a private
# repo. See 02-Elevate-and-Thrive/Hub/news-capture-lag-review-2026-08-27.md.
#
# The delivery runs in the pipeline (priority-handoff.yml) on the SSH deploy key
# that already writes here, shortly before this sweep's 01:40 cron.
#
# IT CHANGES QUERY ORDER AND NOTHING ELSE. A name here is queried sooner; it is
# not published sooner and it is not published more easily. The five-part match
# rule, the two-publisher corroboration rule and verify.py are all downstream of
# this and all still have to be satisfied.
#
# IT FAILS OPEN, BUT IT NO LONGER FAILS SILENTLY. Missing file, bad JSON, stale
# timestamp, a name not in the seed — any of these and the run proceeds on the
# normal rotation, but it SAYS which happened. That distinction is the whole
# lesson of the 404 above: "nothing flagged" and "could not read it" must never
# look the same in the log again.
PRIORITY_PATH = REPO / "state" / "supplier-press-priority.json"
PRIORITY_MAX_AGE_DAYS = 3     # older than this and the Live Desk has stopped writing it
PRIORITY_MAX_NAMES = 20       # a day's budget at most; past this it is not a rotation
QUERY_PAUSE = 2.0             # seconds between Google News queries
RESOLVE_PAUSE = 0.8           # seconds between link resolutions

PRESS_DAYS = 550              # ~18 months, same window the old feature used
PRESS_KEEP = 4                # published stories kept per supplier

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
RSS_UA = "Mozilla/5.0 (msh-compare-data; company-press; contact@elevateandthrive.uk)"

# --- corroboration (rule 5). Lifted unchanged from build_supplier_index.py so
# the two agree on what a reputable publisher is.
REPUTABLE = [
    "bbc", "reuters", "financial times", "ft.com", "the guardian", "the times", "telegraph",
    "sky news", "the independent", "bloomberg", "associated press", "ap news", "the economist",
    "med-technews", "med-tech innovation", "medtech dive", "medtechdive", "massdevice", "fierce",
    "medical product outsourcing", "medical plastics news", "md+di", "mddi", "device talks",
    "devicetalks", "ns medical devices", "medtech insight", "medtech world",
    "medtech intelligence", "drug delivery business", "medical design",
    "medical device developments", "european medical device", "biospace", "medcity",
    "clinical services journal", "hospital healthcare", "national health executive",
    "healthcare today", "health tech world", "pharmaphorum", "pharmatimes",
    "the pharma letter", "pharmafile", "pharmaceutical journal", "digital health",
    "building better healthcare", "health service journal", "hsj", "nursing times",
    "nursing standard", "independent nurse", "british journal of nursing", "gp online",
    "pulse today", "the bmj", "bmj", "lancet", "nature", "npj", "jama", "plos", "cochrane",
    "biomed central", "bmc", "journal of wound care", "journal of vascular access",
    "infection prevention", "open access government", "health europa", "omnia health",
    "healthcare in europe", "hospital times", "medwatch", "medtech europe",
    "investors in healthcare",
]
MED_KEYWORDS = [
    "medical", "clinical", "medtech", "med-tech", "medicine", "hospital", "nursing", "nurse",
    "surgery", "surgical", "pharma", "device", "diagnostic", "therapy", "therapeutic",
    "healthcare", "health tech", "journal of", "bmj", "lancet", "biomed", "cardiolog",
    "oncolog", "radiolog", "wound", "vascular", "nhs",
]
PRWIRE = [
    "globenewswire", "prnewswire", "pr newswire", "businesswire", "business wire", "einnews",
    "openpr", "yahoo finance", "simply wall", "marketbeat", "stocktitan", "zacks",
    "insider monkey", "defense world", "investing.com", "tipranks", "gurufocus", "benzinga",
    "seeking alpha", "accesswire", "newsfilecorp", "healthline", "verywell", "patch.com",
    "medianews", "stocktwits", "fool.com", "barchart", "nasdaq.com",
]

CORROBORATION_RULE = (
    "A story publishes only where at least two DISTINCT publishers carry it and each of those "
    "publishers is either a named reputable outlet or a publication whose own name signals a "
    "clinical or medical-device title. PR wires, stock-tip sites and SEO syndication never "
    "count towards the two, whatever else they look like."
)
ROTATION_RULE = (
    "Every supplier in supplier-seed.json is queried on a fixed rotation, oldest-checked first, "
    "with never-checked suppliers first: those carrying a curated note every %d days, the "
    "remainder every %d days. The daily query count is derived from those cycles rather than "
    "typed, and capped at %d. A supplier checked today sorts to the back of its tier, so the "
    "head of the list is never re-queried while others wait."
    % (PRESS_CYCLE_NOTED_DAYS, PRESS_CYCLE_OTHER_DAYS, PRESS_DAILY_CAP)
)
LINK_RULE = (
    "Google News RSS returns a news.google.com redirect rather than the publisher's URL. Each is "
    "resolved to the publisher's own article and recorded with urlType 'publisher'. Where it "
    "cannot be resolved the redirect is kept and recorded with urlType 'google-news-redirect', "
    "so a link that has not been resolved is never presented as though it had been."
)

log = lambda m: print("[company-press]", m)


# ---------------------------------------------------------------------------
# plumbing
# ---------------------------------------------------------------------------
def fetch(url, timeout=30, ua=RSS_UA, data=None, headers=None):
    h = {"User-Agent": ua}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def load_json(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def today_iso():
    return datetime.date.today().isoformat()


def parse_rss_date(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date().isoformat()
        except Exception:
            pass
    return ""


def reputable(pub):
    p = (pub or "").lower()
    if not p or any(x in p for x in PRWIRE):
        return False
    if any(x in p for x in REPUTABLE):
        return True
    return any(x in p for x in MED_KEYWORDS)


# ---------------------------------------------------------------------------
# link resolution
# ---------------------------------------------------------------------------
def resolve_google_link(link, cache):
    """The publisher's own article URL, or None.

    Google's RSS link is an opaque redirect. The base64 payload used to carry the
    real URL in plain text; it no longer does (checked 18/08/2026 - the newer
    AU_yqL... payloads decode to bytes containing no URL at all). What does work
    is the endpoint Google's own reader uses: pull data-n-a-sg / data-n-a-ts off
    the article shell, then POST them to DotsSplashUi/batchexecute.

    It is undocumented and can stop working without notice. That is exactly why a
    failure here keeps the redirect and marks it, rather than dropping the story
    or pretending the link is a publisher link.
    """
    if link in cache:
        return cache[link] or None
    if "news.google.com" not in link:
        return link
    try:
        aid = link.rsplit("/articles/", 1)[-1].split("?")[0]
        shell = fetch(link, timeout=25, ua=BROWSER_UA)
        sg = re.search(r'data-n-a-sg="([^"]+)"', shell)
        ts = re.search(r'data-n-a-ts="([^"]+)"', shell)
        if not (sg and ts):
            cache[link] = ""
            return None
        inner = ["garturlreq",
                 [["X", "X", ["X", "X"], None, None, 1, 1, "GB:en", None, 1, None, None, None,
                   None, None, 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
                 aid, int(ts.group(1)), sg.group(1)]
        body = urllib.parse.urlencode(
            {"f.req": json.dumps([[["Fbv4je", json.dumps(inner), None, "generic"]]])}).encode()
        resp = fetch("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                     timeout=25, ua=BROWSER_UA, data=body,
                     headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        m = re.search(r'https?://(?!news\.google)[^"\\\]]+', resp)
        url = m.group(0) if m else ""
    except Exception:
        url = ""
    cache[link] = url
    return url or None


# ---------------------------------------------------------------------------
# query + guard
# ---------------------------------------------------------------------------
def query_google_news(name):
    """Raw items for a supplier, or None if the fetch failed (throttled)."""
    q = urllib.parse.quote('"%s" (NHS OR UK OR medical OR healthcare)' % name)
    url = "https://news.google.com/rss/search?q=%s&hl=en-GB&gl=GB&ceid=GB:en" % q
    xml = ""
    for _ in (0, 1):
        try:
            xml = fetch(url, timeout=25)
            if "<item>" in xml or "<channel>" in xml:
                break
        except Exception:
            xml = ""
        time.sleep(3)
    if "<item>" not in xml:
        if "<channel>" in xml:
            return []                                   # a real, empty result set
        return None                                     # could not fetch
    cutoff = (datetime.date.today() - datetime.timedelta(days=PRESS_DAYS)).isoformat()
    items = []
    for m in re.findall(r"<item>(.*?)</item>", xml, re.S):
        t = re.search(r"<title>(.*?)</title>", m, re.S)
        l = re.search(r"<link>(.*?)</link>", m, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", m)
        so = re.search(r"<source[^>]*>(.*?)</source>", m, re.S)
        desc = re.search(r"<description>(.*?)</description>", m, re.S)
        pub = html.unescape(so.group(1)).strip() if so else ""
        title = html.unescape(t.group(1)).strip() if t else ""
        headline = (re.sub(r"\s+-\s+" + re.escape(pub) + r"\s*$", "", title).strip()
                    if pub else title)
        summary = re.sub(r"<[^>]+>", " ", html.unescape(desc.group(1))) if desc else ""
        date = parse_rss_date(d.group(1)) if d else ""
        if date and date < cutoff:
            continue
        items.append({"headline": headline, "summary": re.sub(r"\s+", " ", summary).strip()[:400],
                      "publisher": pub, "link": l.group(1).strip() if l else "", "date": date})
    return items


def cluster(items, name_toks=None):
    """Group items that are the SAME STORY, by headline token overlap.

    ⚠️ TWO DEFECTS FIXED HERE ON 18/08/2026. Both made rule 5 CORROBORATION test
    the same COMPANY rather than the same STORY, which is the opposite of what the
    rule printed beside the item on the Hub claims. Found by dry-running the Live
    Desk panel against the published file; 14 of 34 live items were affected.

    1. THE FLOOR WAS SATISFIED BY THE COMPANY'S OWN NAME. The old test was
       `len(common) >= max(2, ...)`, and every headline about a supplier contains
       that supplier's name. Any two-token company name — "Smith+Nephew" normalises
       to {smith, nephew} — supplied both tokens on its own, so two unrelated
       stories clustered and each corroborated the other. Live example: the
       headline "Smith+Nephew and Imperial College London launch centre to
       accelerate innovation in surgical robotics" was published carrying Reuters
       and MedTech Dive as its corroboration, and both were covering Smith+Nephew
       BUYING INTEGRITY ORTHOPAEDICS — a different story entirely. A member reading
       "two independent publishers carried this" was being told something false.

       So the supplier's own name and alias tokens are removed before the overlap
       is measured. Corroboration now has to come from what the story is ABOUT.

    2. THE CLUSTER GOT LOOSER AS IT GREW. `c["toks"] |= toks` accumulated every
       absorbed headline's tokens into the set future items were compared against,
       so a cluster that had swallowed three stories offered a much larger surface
       for the fourth to match on. Each item is now compared against the cluster's
       SEED tokens, which do not move.

    Root rule 14: this is a derived claim, so the rule it was derived under is
    printed beside it and there is now an invariant that fails if the logic breaks
    (verify.check_company_press, "corroboration satisfied by the company name").
    """
    name_toks = name_toks or set()
    clusters = []
    for it in items:
        toks = set(t for t in press_match.norm(it["headline"]).split() if len(t) > 3)
        # The company's own name is not evidence that two stories are the same story.
        topic = toks - name_toks
        if not topic:
            # A headline that is nothing but the company's name carries no topic to
            # corroborate on. It starts its own cluster and can only ever be joined
            # by another such headline, which rule 5 will then reject for want of a
            # second reputable publisher unless they are genuinely the same story.
            clusters.append({"toks": toks, "topic": topic, "items": [it]})
            continue
        placed = False
        for c in clusters:
            if not c["topic"]:
                continue
            common = topic & c["topic"]
            # Compared against the cluster's SEED topic, never an accumulating union.
            if len(common) >= max(2, int(0.5 * min(len(topic), len(c["topic"])))):
                c["items"].append(it)
                placed = True
                break
        if not placed:
            clusters.append({"toks": toks, "topic": topic, "items": [it]})
    return clusters


def build_items(supplier, raw, cache, resolve=True, rejects=None, universe=None):
    """Apply the whole rule to one supplier's raw results.

    IDENTITY is tested per item — an item that does not name this supplier is not
    about it, whatever else it says. Everything after that is tested on the STORY,
    not on each syndication of it: a story reaches us through several outlets, and
    the one that carries the UK detail or the clinical framing is often not the
    one that ranked first. So the cluster is formed from the items that identify
    the supplier, and the item PUBLISHED as the lead is one that independently
    satisfies every rule on its own stored text — which is what lets verify.py
    re-derive the decision from the published file alone.
    """
    rejects = rejects if rejects is not None else []
    identified = []
    for it in raw:
        ok, why, ev = press_match.assess(supplier, it, publisher=it.get("publisher"),
                                         universe=universe)
        it["_ok"], it["_evidence"] = ok, ev
        if press_match.identify(supplier, it, universe):
            identified.append(it)
        else:
            rejects.append({"headline": it["headline"], "publisher": it.get("publisher", ""),
                            "reason": why})

    # Every token in this supplier's own name and alias forms. These are stripped
    # before two headlines are compared, so corroboration is measured on the story
    # and never on the company name — see cluster()'s docstring for the live
    # example that made this necessary.
    name_toks = set()
    for form in [supplier.get("name", "")] + list(supplier.get("aliases") or []):
        name_toks |= set(t for t in press_match.norm(form).split() if len(t) > 3)

    out = []
    for c in cluster(identified, name_toks=name_toks):
        reps = {}
        for it in c["items"]:
            if reputable(it["publisher"]) and it["publisher"] not in reps:
                reps[it["publisher"]] = it
        leads = [it for it in c["items"] if it.get("_ok")]
        best = sorted(c["items"], key=lambda x: x.get("date", ""), reverse=True)[0]
        if len(reps) < 2:                                # rule 5
            rejects.append({"headline": best["headline"],
                            "publisher": ", ".join(sorted({i["publisher"] for i in c["items"]})),
                            "reason": ("rule 5 CORROBORATION: %d distinct reputable publisher(s), "
                                       "two required" % len(reps))})
            continue
        if not leads:                                    # rules 3 and 4, on the story
            why = next((i["_evidence"] for i in c["items"] if i.get("_evidence")), None)
            reason = "rules 3/4: no item in this story clears the sector and relevance tests"
            rejects.append({"headline": best["headline"],
                            "publisher": ", ".join(sorted({i["publisher"] for i in c["items"]})),
                            "reason": reason})
            continue
        # Prefer a lead that is itself one of the corroborating reputable outlets,
        # then the most recent. The lead is what the page shows and what the gate
        # re-derives, so it has to be an item that passes on its own text.
        leads.sort(key=lambda x: (x["publisher"] in reps, x.get("date", "")), reverse=True)
        lead = leads[0]
        srcs = [lead] + [s for s in sorted(reps.values(), key=lambda x: x.get("date", ""),
                                           reverse=True) if s is not lead]
        sources = []
        for s in srcs[:4]:
            real = resolve_google_link(s["link"], cache) if resolve else None
            if resolve:
                time.sleep(RESOLVE_PAUSE)
            if real:
                sources.append({"publisher": s["publisher"], "url": real,
                                "urlType": "publisher", "redirectUrl": s["link"]})
            else:
                sources.append({"publisher": s["publisher"], "url": s["link"],
                                "urlType": "google-news-redirect"})
        out.append({
            "headline": lead["headline"],
            "date": lead.get("date") or "",
            "summary": lead.get("summary", ""),
            "sources": sources,
            "match": lead["_evidence"],
            "verified": True,
            "autoDetected": True,
        })
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    return out[:PRESS_KEEP]


# ---------------------------------------------------------------------------
# rotation
# ---------------------------------------------------------------------------
def tiers(suppliers):
    noted = [s for s in suppliers if str(s.get("note") or "").strip()]
    other = [s for s in suppliers if not str(s.get("note") or "").strip()]
    return noted, other


def due(suppliers, stamps, quota):
    """The `quota` suppliers longest overdue. Never-checked first, then oldest."""
    ordered = sorted(suppliers, key=lambda s: (stamps.get(s["name"], ""), s["name"].lower()))
    return ordered[:quota]


def read_priority_file(reader=None):
    """Raw text of the handoff file, or None if it is not readable."""
    try:
        if reader is not None:
            return reader()
        return PRIORITY_PATH.read_text(encoding="utf-8")
    except OSError:
        return None


def priority_names(reader=None, today=None):
    """Supplier names the Live Desk flagged, or [] for any reason at all.

    Every path returns [] on failure deliberately — see PRIORITY_PATH above; this
    is an optimisation, never a dependency. Unlike the version this replaced, it
    LOGS which path it took, so a delivery that has stopped arriving cannot go on
    looking like a quiet day.
    """
    raw = read_priority_file(reader)
    if raw is None:
        log("PRIORITY HANDOFF NOT DELIVERED — no %s. Normal rotation. "
            "If this persists, priority-handoff.yml in the pipeline has stopped."
            % PRIORITY_PATH.name)
        return []
    try:
        doc = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        gen = str(doc.get("generatedAt") or "")[:10]
        age = (datetime.date.fromisoformat(today or today_iso())
               - datetime.date.fromisoformat(gen)).days
    except Exception as exc:
        log("PRIORITY HANDOFF UNREADABLE (%s: %s) — normal rotation."
            % (type(exc).__name__, exc))
        return []
    if age < 0 or age > PRIORITY_MAX_AGE_DAYS:
        log("PRIORITY HANDOFF STALE (generated %s, %d day(s) old, max %d) — "
            "normal rotation." % (gen, age, PRIORITY_MAX_AGE_DAYS))
        return []
    names = [n for n in (doc.get("suppliers") or []) if isinstance(n, str) and n.strip()]
    if not names:
        log("priority handoff delivered %s, no suppliers flagged — normal rotation." % gen)
        return []
    return names[:PRIORITY_MAX_NAMES]


def plan(suppliers, stamps, priority=None):
    """Front-load flagged suppliers, then fill the rest by normal rotation.

    A flagged name still has to BE in the seed — an unknown name is ignored, not
    queried — and flagged suppliers come out of the same daily budget rather than
    being added on top, so the politeness cap on Google News is unchanged.
    """
    noted, other = tiers(suppliers)
    q_noted = math.ceil(len(noted) / PRESS_CYCLE_NOTED_DAYS) if noted else 0
    q_other = math.ceil(len(other) / PRESS_CYCLE_OTHER_DAYS) if other else 0
    if q_noted + q_other > PRESS_DAILY_CAP:              # trim the longer cycle first
        q_other = max(0, PRESS_DAILY_CAP - q_noted)
        q_noted = min(q_noted, PRESS_DAILY_CAP)
    picked = due(noted, stamps, q_noted) + due(other, stamps, q_other)
    if not priority:
        return picked, q_noted, q_other
    by_name = {s["name"]: s for s in suppliers}
    front = [by_name[n] for n in priority if n in by_name]
    if not front:
        return picked, q_noted, q_other
    front_names = {s["name"] for s in front}
    # Out of the same budget, not on top of it: drop the equivalent number from
    # the TAIL of the rotation pick, which is the least overdue end of it.
    rest = [s for s in picked if s["name"] not in front_names]
    return (front + rest)[:len(picked)], q_noted, q_other


# ---------------------------------------------------------------------------
# file assembly
# ---------------------------------------------------------------------------
def recount(doc):
    """Recompute the counts header FROM the rows. Never carried, always derived."""
    sup = doc.get("suppliers") or {}
    items = sources = resolved = redirect = with_items = 0
    for rec in sup.values():
        rows = rec.get("items") or []
        if rows:
            with_items += 1
        items += len(rows)
        for row in rows:
            for s in (row.get("sources") or []):
                sources += 1
                if s.get("urlType") == "publisher":
                    resolved += 1
                else:
                    redirect += 1
    doc["counts"] = {"suppliers": len(sup), "suppliersWithItems": with_items,
                     "items": items, "sources": sources,
                     "resolvedLinks": resolved, "redirectLinks": redirect}
    return doc


def assemble(suppliers_block, seed_total, checked_this_run, q_noted, q_other, never):
    doc = {
        "_notice": stamp_notice.notice_for(OUT.name),
        "dataAsOf": datetime.date.today().strftime("%d/%m/%Y"),
        "generated": datetime.datetime.utcnow().isoformat() + "Z",
        "source": ("Google News RSS (https://news.google.com/rss/search), one query per supplier, "
                   "hl=en-GB&gl=GB. Each story is then attributed to the publishers that carried "
                   "it, and those publishers are the source of the claim - Google News is the "
                   "index, never the authority."),
        "sourceUrls": {"Google News": "https://news.google.com/"},
        "matchRule": press_match.RULE,
        "corroborationRule": CORROBORATION_RULE,
        "rotationRule": ROTATION_RULE,
        "linkRule": LINK_RULE,
        "emptyStateRule": ("A supplier with lastChecked set and no items has been checked and "
                           "nothing met the bar. That is a statement about this index on that "
                           "date, never a statement that the company has had no news."),
        "rotation": {"dailyBudget": q_noted + q_other,
                     "notedQuota": q_noted, "otherQuota": q_other,
                     "notedCycleDays": PRESS_CYCLE_NOTED_DAYS,
                     "otherCycleDays": PRESS_CYCLE_OTHER_DAYS,
                     "dailyCap": PRESS_DAILY_CAP,
                     "seedSuppliers": seed_total,
                     "checkedThisRun": checked_this_run},
        "coverage": {
            "complete": never == 0,
            "suppliersNeverChecked": never,
            "note": ("Every supplier has been checked at least once." if never == 0 else
                     "INCOMPLETE: %d of %d suppliers have not been reached yet on the first "
                     "rotation. An absence here is a statement about this index, never about "
                     "the company." % (never, seed_total)),
        },
        "counts": {},
        "suppliers": suppliers_block,
    }
    return recount(doc)


def write(doc, path):
    pathlib.Path(path).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                                  encoding="utf-8")


# ---------------------------------------------------------------------------
def do_merge(ours_path, base_path):
    """Merge OURS into BASE by supplier name, then recompute the header.

    This is the rebase path. Git must never text-merge this file; see the module
    docstring and NOTE-company-intelligence-rebase-merge-defect-2026-08-14.md.
    A supplier block moves whole - its lastChecked and its items were produced by
    the same run and mean nothing apart.
    """
    base = load_json(base_path, None)
    ours = load_json(ours_path, None)
    if base is None or ours is None:
        sys.exit("--merge needs both files to be readable JSON")
    merged = dict(base)
    block = dict(base.get("suppliers") or {})
    for name, rec in (ours.get("suppliers") or {}).items():
        keep = block.get(name)
        if not keep or (rec.get("lastChecked", "") >= keep.get("lastChecked", "")):
            block[name] = rec
    merged["suppliers"] = block
    # Header fields are re-derived from the rows, never inherited from either side.
    merged["_notice"] = stamp_notice.notice_for(OUT.name)
    merged["dataAsOf"] = datetime.date.today().strftime("%d/%m/%Y")
    merged["generated"] = datetime.datetime.utcnow().isoformat() + "Z"
    merged["matchRule"] = press_match.RULE
    merged["corroborationRule"] = CORROBORATION_RULE
    merged["rotationRule"] = ROTATION_RULE
    merged["linkRule"] = LINK_RULE
    seed_total = len(load_json(SEED, {"suppliers": []}).get("suppliers") or [])
    never = max(0, seed_total - len(block))
    merged["coverage"] = {
        "complete": never == 0, "suppliersNeverChecked": never,
        "note": ("Every supplier has been checked at least once." if never == 0 else
                 "INCOMPLETE: %d of %d suppliers have not been reached yet on the first "
                 "rotation. An absence here is a statement about this index, never about "
                 "the company." % (never, seed_total))}
    recount(merged)
    write(merged, base_path)
    log("merged %d supplier block(s) by name; header recomputed from the rows"
        % len(ours.get("suppliers") or {}))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=0, help="cap suppliers queried this run")
    ap.add_argument("--only", default="", help="comma-separated supplier names (ignores rotation)")
    ap.add_argument("--all", action="store_true",
                    help="one-off catch-up: query every supplier in the seed this run, "
                         "ignoring PRESS_DAILY_CAP. For a manual full sweep only - the "
                         "GitHub Actions cron never passes this, so the 80/day politeness "
                         "cap still governs every scheduled run.")
    ap.add_argument("--no-priority", action="store_true",
                    help="ignore the Live Desk priority handoff and use the plain "
                         "rotation. For reproducing a run exactly.")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--no-resolve", action="store_true", help="skip Google link resolution")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--merge", default="", metavar="OURS.json",
                    help="merge OURS.json into --out by supplier name and recompute the header")
    args = ap.parse_args()

    if args.merge:
        return do_merge(args.merge, args.out)

    seed = load_json(SEED, {"suppliers": []})
    suppliers = [s for s in (seed.get("suppliers") or []) if s.get("name")]
    if not suppliers:
        sys.exit("data/supplier-seed.json holds no suppliers - refusing to write an empty file")

    universe = press_match.alias_universe(seed)
    state = load_json(STATE, {}) or {}
    stamps = state.get("lastPressCheck") or {}
    cache = state.get("resolvedUrls") or {}

    if args.only:
        wanted = [n.strip() for n in args.only.split(",") if n.strip()]
        by = {s["name"]: s for s in suppliers}
        missing = [n for n in wanted if n not in by]
        if missing:
            log("NOT IN THE SEED, skipped: %s" % ", ".join(missing))
        batch = [by[n] for n in wanted if n in by]
        q_noted = q_other = 0
    elif args.all:
        noted, other = tiers(suppliers)
        batch = due(noted, stamps, len(noted)) + due(other, stamps, len(other))
        q_noted, q_other = len(noted), len(other)
        log("--all: ignoring PRESS_DAILY_CAP, querying the full seed this run")
    else:
        # --only and --all deliberately bypass this: both are explicit manual
        # instructions and a hint from another repo must not second-guess them.
        prio = [] if args.no_priority else priority_names()
        if prio:
            log("Live Desk flagged %d supplier(s) for an early check: %s"
                % (len(prio), ", ".join(prio)))
        batch, q_noted, q_other = plan(suppliers, stamps, priority=prio)
    if args.limit:
        batch = batch[:args.limit]

    existing = load_json(args.out, {}) or {}
    block = dict(existing.get("suppliers") or {})

    log("seed %d suppliers; querying %d this run (noted quota %d, other quota %d)"
        % (len(suppliers), len(batch), q_noted, q_other))

    checked = published = dropped = throttled = 0
    all_rejects = {}
    for s in batch:
        name = s["name"]
        raw = query_google_news(name)
        time.sleep(QUERY_PAUSE)
        if raw is None:
            throttled += 1
            log("  %-45s fetch failed (throttled) - previous state kept" % name[:45])
            continue
        rejects = []
        items = build_items(s, raw, cache, resolve=not args.no_resolve, rejects=rejects,
                            universe=universe)
        checked += 1
        published += len(items)
        dropped += len(rejects)
        all_rejects[name] = rejects
        block[name] = {"lastChecked": today_iso(), "items": items}
        stamps[name] = today_iso()
        log("  %-45s %d raw -> %d published, %d dropped"
            % (name[:45], len(raw), len(items), len(rejects)))
        for r in rejects[:6]:
            log("      DROPPED %-38s [%s] %s" % (r["headline"][:38], r["publisher"][:22],
                                                 r["reason"][:90]))

    # Publish the aliases the Live Desk carve-out may match on, for EVERY
    # supplier in the block rather than only the ones queried this run — the
    # consumer needs the whole list on the first run, not over a 14-day cycle.
    # See press_match.match_aliases for the four gates and why capitalisation is
    # the discriminator. A supplier the seed no longer carries keeps whatever it
    # had; it is not our business to strip it here.
    by_name = {s["name"]: s for s in suppliers}
    aliased = 0
    for name, rec in block.items():
        src = by_name.get(name)
        if not src:
            continue
        al = press_match.match_aliases(src, universe)
        if al["caseInsensitive"] or al["caseSensitive"]:
            rec["matchAliases"] = al
            aliased += 1
    log("published match aliases for %d of %d supplier(s)" % (aliased, len(block)))

    never = max(0, len(suppliers) - len(block))
    doc = assemble(block, len(suppliers), checked, q_noted, q_other, never)

    log("checked %d, published %d item(s), dropped %d, throttled %d"
        % (checked, published, dropped, throttled))
    log("counts: %s" % json.dumps(doc["counts"]))

    if args.dry_run:
        log("DRY RUN - nothing written")
        print(json.dumps({n: block[n] for n in (s["name"] for s in batch) if n in block},
                         ensure_ascii=False, indent=1))
        return 0

    write(doc, args.out)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"lastPressCheck": stamps, "resolvedUrls": cache,
                                 "updated": datetime.datetime.utcnow().isoformat() + "Z"},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log("wrote %s and %s" % (args.out, STATE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
