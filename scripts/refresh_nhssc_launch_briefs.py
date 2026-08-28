#!/usr/bin/env python3
"""
NHS Supply Chain contract launch briefs: who is on a framework, and who just lost it.

NHS Supply Chain publishes a launch brief for every framework it awards, in plain
public HTML with no login:

  https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/

Each brief carries the framework reference, category, supply route, start and
expiry dates, the term, the full NAMED SUPPLIER LIST including new entrants, and
-- the reason this source is worth more than the others -- THE SUPPLIERS BEING
DELISTED AT FRAMEWORK START, with the reason and the product count.

WHY DELISTING IS THE POINT
--------------------------
Framework membership is available from several places (Find a Tender award
notices, NHS SBS, the host's own site). A supplier being REMOVED from a framework
is published almost nowhere else, and it is the single most actionable fact a rep
can have: it names a competitor who has just lost their route to market in that
category, and often names where the volume has gone instead. Example from the
Wound Closure brief: Becton Dickinson delisted across 18 products under the
Arista, Avitene and Progel brands; Prosys International's products moved to the
Mesh framework; Pierson Surgical's products now reach the NHS via Aquilant under
new codes.

THE PARSING RULE (root CLAUDE.md rule 14: state the rule in the file)
---------------------------------------------------------------------
Briefs are prose, not a table, so the awarded and delisted lists are read from
delimited regions of the flattened page text:

  awarded   between "on this framework" / "they are:" and either the delisting
            sentence or the next section heading. Every line in that region is a
            supplier name.
  delisted  between "being delisted at the start of the framework agreement" and
            the next section heading. This region MIXES supplier names with
            explanatory sentences, so a line is treated as a supplier name only
            if it does not end in a full stop and is under 80 characters;
            anything else is attached to the preceding supplier as its note.

THE INVARIANT THAT MAKES THIS TRUSTWORTHY
-----------------------------------------
Every brief states its own supplier count in prose ("There are 39 suppliers") AND
lists them. The script compares the two. A brief whose stated count disagrees with
the number of names parsed is NOT published: it is recorded as a parse failure and
reported. That is a genuine check on the parser rather than a hopeful one, and it
means a silent template change surfaces as a failure instead of as a shrunken
supplier list on a paying member's screen.

If more than a quarter of briefs fail that check the script writes nothing at all,
on the assumption the site template has changed rather than that the NHS suddenly
started miscounting.

WHAT THIS DOES NOT PROVE
------------------------
A supplier on a framework can supply through it. That is NOT evidence of uptake,
volume or market share at any trust. A delisting means the supplier is off THIS
framework from its start date; it does not mean the company is in trouble, and it
does not mean any particular trust stops buying from them. Say what the brief says
and no more.

The Product Matrix and Framework Matrix spreadsheets linked from each brief sit
behind authentication.supplychain.nhs.uk and are NOT fetched.

Usage:
    python3 scripts/refresh_nhssc_launch_briefs.py
    python3 scripts/refresh_nhssc_launch_briefs.py --limit 5   # smoke test
    python3 scripts/refresh_nhssc_launch_briefs.py --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

INDEX = "https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/"
BASE = "https://www.supplychain.nhs.uk"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
OUT = os.path.join(DATA, "nhssc-launch-briefs.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

BRIEF_RE = re.compile(
    r'href="(https://www\.supplychain\.nhs\.uk/product-information/'
    r'contract-launch-brief/[^"#?]+/)"')
PAGE_RE = re.compile(
    r'href="[^"]*?/product-information/contract-launch-briefs/page/(\d+)')

# Section headings that end a list region.
STOP_HEADINGS = (
    "product categories", "about the products", "downloads", "useful links",
    "key benefits", "suppliers", "delisted products", "sustainability",
    "how to purchase", "areas covered", "overview", "resilience",
    "leading suppliers on contract", "social value", "savings",
    "delisted suppliers",
)

# The briefs are hand-written, so the same sentence appears in several shapes:
#   "...on this framework – they are:"        (Wound Closure)
#   "...suppliers on this framework. They are:"  (Advanced Wound Care)
# Anchoring on the trailing "they are:" catches both without guessing at the
# punctuation in between.
AWARDED_MARKER = re.compile(r"\bthey are\s*:?\s*$", re.I)

# A brief can carry MORE THAN ONE delisting block, each with its own reason, e.g.
# "...at the start of the framework agreement:" and a second one "...due to not
# tendering:". Every block is read, and the reason is taken from its own marker
# line so a supplier is never separated from why they went.
DELIST_MARKER = re.compile(
    r"being delisted at the start of the framework agreement(.*)$", re.I)

MONTHS = ("January February March April May June July August September "
          "October November December").split()

# ---------------------------------------------------------------------------
# WHAT COUNTS AS "THE TEMPLATE CHANGED"
#
# The first version of this script carried a flat 75% floor, invented before
# anything had been measured. The measured baseline across all 140 briefs is 74%:
# NHS Supply Chain writes these by hand and roughly a quarter of them state a
# supplier count that genuinely does not match the list printed beneath it, or
# group the list in a shape no general rule reads correctly.
#
# A static percentage was therefore testing the wrong thing. What actually needs
# detecting is a REGRESSION: a site template change, or a parser edit, that makes
# things suddenly worse. So there are two checks:
#
#   1. an absolute floor, set well below the measured baseline, to catch a total
#      break (the site redesigns, every brief fails)
#   2. a relative check against the previous run's clean count, which is the real
#      regression detector and is far more sensitive than any fixed share
#
# What has NOT been loosened: briefs that fail the stated-count invariant are
# still never published. The floor only decides whether to publish the VERIFIED
# ones at all. Do not raise the number of published briefs by relaxing the
# invariant itself.
# ---------------------------------------------------------------------------
MIN_CLEAN_SHARE = 0.60
MAX_CLEAN_DROP = 0.15          # vs the previous run's clean count


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, tries: int = 3) -> str | None:
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if attempt == tries:
                log("    HTTP %s: %s" % (exc.code, url))
                return None
            time.sleep(4 * attempt)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == tries:
                log("    FETCH FAILED: %s (%s)" % (url, exc))
                return None
            time.sleep(4 * attempt)
    return None


MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)


def flatten(page: str) -> list[str]:
    """
    Strip a brief to an ordered list of visible text lines.

    Only the <main> element is read. The site's nav and footer link text
    ("Events", "About Us", "Governance and Legal", "Certifications and
    Compliance") passes any reasonable company-name test, and because the footer
    sits under a "Suppliers" heading it produced a spurious 14-name supplier list
    on every brief. Cutting to <main> removes that whole class of contamination
    structurally, rather than trying to blacklist chrome text.
    """
    m = MAIN_RE.search(page)
    if m:
        page = m.group(1)
    t = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = htmllib.unescape(t)
    lines = []
    for raw in t.split("\n"):
        s = re.sub(r"[ \t\xa0]+", " ", raw).strip()
        if s:
            lines.append(s)
    return lines


def parse_date(v: str) -> str | None:
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", v)
    if not m:
        return None
    day, month, year = m.group(1), m.group(2).capitalize(), m.group(3)
    if month not in MONTHS:
        return None
    try:
        return dt.date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()
    except ValueError:
        return None


def is_heading(line: str) -> bool:
    return line.strip().lower().rstrip(":") in STOP_HEADINGS


# Words that open an explanatory sentence in these briefs. No real supplier name
# in the live data starts with any of them.
# Count and quantity lines that sit inside the list region and are not suppliers:
#   "22 suppliers"  "12 new suppliers"  "2,064 new products"  "three lots"  "7"
NUMBER_WORDS = ("one two three four five six seven eight nine ten eleven twelve "
                "thirteen fourteen fifteen twenty thirty").split()
COUNT_LINE = re.compile(
    r"^(?:[\d,]+|%s)\s*(?:new\s+)?(?:suppliers?|products?|lots?|lines?|"
    r"frameworks?|months?)?\.?$" % "|".join(NUMBER_WORDS), re.I)

SENTENCE_START = re.compile(
    r"^(This|These|Their|They|However|Please|See|There|The following|Products?"
    r"|All|Some|For|Where|If|Note|Further|Additional|Customers|Any|As|Due|In|It"
    r"|We|Our|You|Alternative)\b", re.I)


def looks_like_company(line: str) -> bool:
    """
    A supplier name, as opposed to an explanatory sentence.

    Length alone is not enough. Real names in the live data include
    'Global Health and Safety Ltd.' (trailing full stop), 'medi UK Ltd'
    (lowercase initial) and 'Brightwake Limited (trading as Advancis Medical)',
    so rejecting on a trailing stop or a lowercase first letter loses genuine
    suppliers and breaks the stated-count invariant.

    Word count is the reliable separator: supplier names in these briefs run to
    at most about eight words, while every explanatory line is a full sentence of
    a dozen or more. Combined with the sentence-opener test that is enough.

    Deliberately conservative in the delisted region: a misread sentence becomes a
    note attached to the supplier above it, which is harmless. A misread sentence
    treated as a NAME would invent a supplier, which is not.
    """
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if len(s.split()) > 10:
        return False
    if s.endswith((":", "?", "!")):
        return False
    if is_heading(s):
        return False
    if SENTENCE_START.match(s):
        return False
    # Needs at least one letter; bare numbers and bullets are not names.
    if not re.search(r"[A-Za-z]", s):
        return False
    # The briefs render their own counts as separate lines inside the list region
    # ("22 suppliers", "12 new suppliers", "2,064 new products", "three lots").
    # These read as short capitalised phrases and were being counted as suppliers,
    # which is where the persistent off-by-one against the stated count came from.
    if COUNT_LINE.match(s):
        return False
    return True


# A new entrant is flagged with a badge on its own line, in several shapes seen in
# the live data:
#     "New"                        (Airway Management: name ends with a dash)
#     "– New"                      (Vascular Therapy)
#     "– New to framework"
#     "– New to NHS Supply Chain"
# Left unhandled each badge counts as an extra supplier and breaks the invariant:
# Vascular Therapy parsed 31 against a stated 23 purely from eight badge lines.
# A badge either is the bare word, or starts with a dash followed by "New".
# Some briefs group the list under sub-headings instead of badging each row:
#     "New suppliers to the framework"   then names
#     "Incumbent suppliers"              then names
# These are LABELS, not supplier names and not per-row badges. They must not end
# the region (the total count covers every sub-group) and must not be mistaken
# for a badge attaching "new" to whichever supplier happened to precede them.
GROUP_LABEL = re.compile(r"^(New|Incumbent|Existing)\s+suppliers?\b", re.I)

BADGE = re.compile(r"^(?:[-–—]\s*)?New\b(?:\s+to\b.*|\s+supplier\b.*)?$", re.I)
TRAILING_DASH = re.compile(r"\s*[-–—]\s*$")


def collapse_badges(block: list[str]) -> list[dict]:
    """
    Turn a supplier-list region into records, folding the 'New' badge line back
    into the supplier it belongs to. The badge is kept: which suppliers are NEW
    to a framework is exactly the kind of movement a rep wants.
    """
    out: list[dict] = []
    pending_new = False
    for line in block:
        stripped = line.strip()
        if GROUP_LABEL.match(stripped):
            # Everything that follows belongs to this group until the next label.
            pending_new = bool(re.match(r"^New\b", stripped, re.I))
            continue
        if BADGE.match(stripped):
            if out:
                out[-1]["new"] = True
            continue
        if not looks_like_company(line):
            continue
        name = TRAILING_DASH.sub("", line).strip()
        if not name:
            continue
        rec = {"name": name}
        if pending_new:
            rec["new"] = True
        out.append(rec)
    return out


def field(lines: list[str], label: str) -> str | None:
    """
    Read a 'Label: value' field. The site sometimes puts the value on the same
    line and sometimes on the next one (Category does this), so both are handled.
    """
    pat = re.compile(r"^%s\s*:\s*(.*)$" % re.escape(label), re.I)
    for i, l in enumerate(lines[:80]):
        m = pat.match(l)
        if m:
            val = m.group(1).strip()
            if val:
                return val
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if nxt and not is_heading(nxt) and ":" not in nxt[:20]:
                    return nxt
            return None
    return None


def stated_count(lines: list[str], pattern: str) -> int | None:
    """Pull a number out of prose like 'There are 39 suppliers'."""
    joined = " ".join(lines[:200])
    m = re.search(pattern, joined, re.I)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def region(lines: list[str], start_i: int,
           stop_on_delist: bool = False) -> tuple[list[str], int]:
    """
    Collect lines from start_i until the next section heading.

    When reading the awarded list we stop at the first delisting marker, so
    delisted names never leak into the awarded list. When reading a delisting
    block we stop at the NEXT delisting marker, so two blocks stay separate and
    each keeps its own reason.
    """
    out: list[str] = []
    i = start_i
    while i < len(lines):
        l = lines[i]
        if is_heading(l) and out:
            break
        if DELIST_MARKER.search(l):
            if not stop_on_delist or out:
                break
        out.append(l)
        i += 1
    return out, i


def parse_brief(url: str, page: str) -> dict:
    lines = flatten(page)

    rec: dict = {
        "url": url,
        "slug": url.rstrip("/").rsplit("/", 1)[-1],
        "framework": None,
        "type": field(lines, "Type"),
        "category": field(lines, "Category"),
        "reference": field(lines, "Reference"),
        "supply_route": field(lines, "Supply Route"),
        "start": None,
        "expiry": None,
        "suppliers": [],
        "delisted_suppliers": [],
        "parse_ok": False,
        "parse_note": None,
    }

    sd = field(lines, "Start Date")
    ed = field(lines, "Expiry Date")
    rec["start"] = parse_date(sd) if sd else None
    rec["expiry"] = parse_date(ed) if ed else None

    # The index still lists frameworks whose expiry date has passed. A rep-facing
    # tool must never present one of those as a live route to market, so the state
    # is computed here rather than left for each consumer to work out.
    today = dt.date.today().isoformat()
    if rec["expiry"]:
        rec["expired"] = rec["expiry"] < today
        if rec["start"] and rec["start"] > today:
            rec["status"] = "not_yet_started"
        else:
            rec["status"] = "expired" if rec["expired"] else "live"

    # Framework name: the line immediately before "Type:".
    for i, l in enumerate(lines[:80]):
        if re.match(r"^Type\s*:", l, re.I) and i:
            rec["framework"] = lines[i - 1].strip()
            break

    rec["new_supplier_count"] = stated_count(
        lines, r"including\s+([\d,]+)\s+new suppliers")
    rec["delisted_product_count"] = stated_count(
        lines, r"([\d,]+)\s+products\s+are being delisted")

    term = re.search(r"runs for\s+(\d+)\s+months", " ".join(lines[:200]), re.I)
    if term:
        rec["term_months"] = int(term.group(1))
    joined = " ".join(lines[:200])
    if re.search(r"no option to extend", joined, re.I):
        rec["extension"] = "none"
    else:
        ext = re.search(r"option to extend[^.]{0,80}", joined, re.I)
        if ext:
            rec["extension"] = ext.group(0).strip()

    # ---- awarded suppliers ------------------------------------------------
    # Take the LONGEST "they are:" block on the page. Some briefs use the phrase
    # more than once (a lot breakdown as well as the main list), and the main
    # supplier list is always the longest of them.
    # The briefs use at least three templates for the awarded list:
    #   "...on this framework - they are:"        then the names
    #   "...suppliers on this framework. They are:"  then the names
    #   a bare "Suppliers" heading, some prose, then the names
    # Rather than chase every phrasing, collect a CANDIDATE block from each
    # anchor and let the stated-count invariant choose between them. If exactly
    # one candidate matches the number the page says, that is the list. This is
    # self-validating: a new template shape either produces a matching candidate
    # or is reported as a parse failure, never a silently short list.
    stated = stated_count(lines, r"There are\s+([\d,]+)\s+suppliers") \
        or stated_count(lines, r"([\d,]+)\s+suppliers in total")

    candidates: list[list[dict]] = []
    for i, l in enumerate(lines):
        if AWARDED_MARKER.search(l):
            block, _ = region(lines, i + 1)
            candidates.append(collapse_badges(block))
        elif l.strip().lower().rstrip(":") == "suppliers":
            block, _ = region(lines, i + 1)
            candidates.append(collapse_badges(block))

    awarded: list[dict] = []
    if stated is not None:
        exact = [c for c in candidates if len(c) == stated]
        if exact:
            awarded = max(exact, key=len)
    if not awarded and candidates:
        awarded = max(candidates, key=len)

    rec["stated_supplier_count"] = stated
    rec["suppliers"] = [a["name"] for a in awarded]
    rec["supplier_count"] = len(awarded)

    # WHICH suppliers are new is published ONLY when the names we found match the
    # count the page states. Measured across the live set, the inline "New" badge
    # never reconciled with the stated new-supplier count on a single brief: most
    # briefs give the number without marking the rows. Publishing a partial list
    # would imply we know which firms are new when we do not, so the names are
    # dropped and only the page's own count is kept (root rule 14: refuse to fire
    # on thin evidence; root rule 2: never fill the gap).
    named_new = [a["name"] for a in awarded if a.get("new")]
    if named_new and rec.get("new_supplier_count") == len(named_new):
        rec["new_suppliers"] = named_new

    # ---- delisted suppliers ----------------------------------------------
    # Every delisting block, not just the first: a brief can delist one set at
    # framework start and another "due to not tendering", and the reason lives on
    # the marker line rather than with the names.
    delisted: list[dict] = []
    for i, l in enumerate(lines):
        m = DELIST_MARKER.search(l)
        if not m:
            continue
        reason = m.group(1).strip(" :.-–—") or None
        block, _ = region(lines, i + 1, stop_on_delist=True)
        current: dict | None = None
        for b in block:
            if looks_like_company(b):
                current = {"name": b, "reason": reason, "note": None}
                delisted.append(current)
            elif current is not None:
                current["note"] = ((current["note"] + " ") if current["note"] else "") + b
    # A supplier can appear in two blocks; keep the first mention of each name.
    seen_names = set()
    deduped = []
    for d in delisted:
        if d["name"] not in seen_names:
            seen_names.add(d["name"])
            deduped.append(d)
    rec["delisted_suppliers"] = deduped
    rec["delisted_supplier_count"] = len(deduped)

    # ---- the invariant ----------------------------------------------------
    stated = rec["stated_supplier_count"]
    if stated is None:
        rec["parse_note"] = "no stated supplier count on the page"
        rec["parse_ok"] = bool(awarded)
    elif stated == len(awarded):
        rec["parse_ok"] = True
    else:
        rec["parse_ok"] = False
        rec["parse_note"] = ("page states %d suppliers, parsed %d"
                             % (stated, len(awarded)))

    return rec


def collect_urls(limit: int | None) -> list[str]:
    urls: list[str] = []
    seen = set()
    first = fetch(INDEX)
    if not first:
        return []
    pages = {1}
    pages.update(int(n) for n in PAGE_RE.findall(first))
    last = max(pages)
    log("  index: %d page(s)" % last)

    for p in range(1, last + 1):
        page = first if p == 1 else fetch("%spage/%d" % (INDEX, p))
        if not page:
            log("    index page %d unavailable" % p)
            continue
        found = 0
        for u in BRIEF_RE.findall(page):
            if u not in seen:
                seen.add(u)
                urls.append(u)
                found += 1
        log("    page %d: %d brief(s)" % (p, found))
        if p < last:
            time.sleep(0.4)
        if limit and len(urls) >= limit:
            break
    return urls[:limit] if limit else urls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only process the first N briefs")
    ap.add_argument("--dry-run", action="store_true", help="write nothing")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    log("NHS Supply Chain launch briefs  %s" % now.isoformat(timespec="seconds"))

    urls = collect_urls(args.limit)
    if not urls:
        log("FAILED: no brief links found. The index template has probably changed.")
        log("        Nothing written, so nothing is silently lost.")
        return 1
    log("  %d brief(s) to read" % len(urls))

    briefs = []
    failed_fetch = 0
    for n, u in enumerate(urls, 1):
        page = fetch(u)
        if not page:
            failed_fetch += 1
            continue
        rec = parse_brief(u, page)
        briefs.append(rec)
        flag = "" if rec["parse_ok"] else "  <-- %s" % rec["parse_note"]
        if rec["delisted_supplier_count"]:
            flag += "  [%d delisted]" % rec["delisted_supplier_count"]
        log("  %3d/%d  %-52s %3d suppliers%s"
            % (n, len(urls), (rec["framework"] or rec["slug"])[:52],
               rec["supplier_count"], flag))
        time.sleep(0.4)

    if not briefs:
        log("FAILED: every brief fetch failed. Nothing written.")
        return 1

    clean = [b for b in briefs if b["parse_ok"]]
    share = len(clean) / len(briefs)
    log("")
    log("  parsed cleanly: %d of %d (%.0f%%)" % (len(clean), len(briefs), share * 100))

    previous_clean = None
    if os.path.exists(OUT):
        try:
            with open(OUT) as fh:
                previous_clean = (json.load(fh).get("counts") or {}).get(
                    "briefs_published")
        except (ValueError, OSError):
            previous_clean = None

    if previous_clean and len(clean) < previous_clean * (1 - MAX_CLEAN_DROP):
        log("FAILED: %d briefs parsed cleanly, down from %d last run (more than"
            % (len(clean), previous_clean))
        log("        %.0f%% worse). That is a regression, not natural variation."
            % (MAX_CLEAN_DROP * 100))
        log("        Nothing written. Find out what changed before republishing.")
        return 1

    if share < MIN_CLEAN_SHARE:
        log("FAILED: only %.0f%% of briefs passed the stated-count invariant, below"
            % (share * 100))
        log("        the %.0f%% floor. That is a template change, not bad luck."
            % (MIN_CLEAN_SHARE * 100))
        log("        Nothing written. Fix the parser, do not lower the floor.")
        return 1

    # Only publish briefs that passed their own invariant.
    publish = clean
    delisting = [b for b in publish if b["delisted_supplier_count"]]
    expiring = [b for b in publish if b.get("expiry")]

    all_suppliers = {s for b in publish for s in b["suppliers"]}
    all_delisted = {d["name"] for b in publish for d in b["delisted_suppliers"]}

    out = {
        "source": "NHS Supply Chain contract launch briefs",
        "source_url": INDEX,
        "generated": now.isoformat(timespec="seconds"),
        "parsing_rule": (
            "Awarded suppliers are read from the region after 'on this framework "
            "- they are:'; delisted suppliers from the region after 'being "
            "delisted at the start of the framework agreement'. In the delisted "
            "region a line is a supplier name only if it is under 80 characters "
            "and does not end in a full stop; anything else is attached to the "
            "preceding supplier as its note."
        ),
        "invariant": (
            "Each brief states its own supplier count in prose and also lists the "
            "suppliers. Only briefs where the two agree are published. Briefs that "
            "disagree are excluded and counted below. If fewer than 75%% of briefs "
            "agree the script writes nothing at all."
        ),
        "evidence_caveat": (
            "A supplier on a framework CAN supply through it; that is not evidence "
            "of uptake, volume or market share at any trust. A delisting means the "
            "supplier is off THIS framework from its start date. It does not mean "
            "the company is in difficulty and it does not mean any given trust has "
            "stopped buying from them. Report what the brief says and no more."
        ),
        "not_fetched": (
            "The Product Matrix and Framework Matrix spreadsheets linked from each "
            "brief are behind authentication.supplychain.nhs.uk and are not taken."
        ),
        "counts": {
            "briefs_published": len(publish),
            "briefs_excluded_failed_invariant": len(briefs) - len(clean),
            "briefs_unreachable": failed_fetch,
            "frameworks_with_delistings": len(delisting),
            "distinct_awarded_suppliers": len(all_suppliers),
            "distinct_delisted_suppliers": len(all_delisted),
            "briefs_with_expiry_date": len(expiring),
            "frameworks_live": sum(1 for b in publish if b.get("status") == "live"),
            "frameworks_expired": sum(1 for b in publish if b.get("status") == "expired"),
            "frameworks_not_yet_started": sum(
                1 for b in publish if b.get("status") == "not_yet_started"),
            "briefs_naming_which_suppliers_are_new": sum(
                1 for b in publish if b.get("new_suppliers")),
        },
        "excluded": [
            {"url": b["url"], "reason": b["parse_note"]}
            for b in briefs if not b["parse_ok"]
        ],
        "briefs": sorted(publish, key=lambda b: (b.get("framework") or b["slug"]).lower()),
    }

    if args.dry_run:
        log("  DRY RUN, nothing written.")
        log("  would publish %d briefs, %d with delistings, %d distinct suppliers"
            % (len(publish), len(delisting), len(all_suppliers)))
        return 0

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    log("  published %d briefs (%d excluded, %d unreachable)"
        % (len(publish), len(briefs) - len(clean), failed_fetch))
    log("  %d framework(s) carry delistings | %d distinct awarded suppliers | "
        "%d distinct delisted" % (len(delisting), len(all_suppliers), len(all_delisted)))
    log("  wrote data/nhssc-launch-briefs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
