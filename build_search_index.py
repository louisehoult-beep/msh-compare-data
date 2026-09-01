#!/usr/bin/env python3
"""
build_search_index.py — build the Hub's own search index from the Hub's own pages.

WHY THIS EXISTS
---------------
Until 06/08/2026 the search box on the Live Desk (WP page 675) ranked a list of
47 Hub pages TYPED BY HAND into the page's own script, with a line of synonyms
per page. That had three faults that no amount of editing fixes:

  1. It never looked inside a page. Only the title and the synonyms I had
     thought to type were searchable. "ChloraPrep", "Evergreen Level 1",
     "Agenda for Change" — none of it was findable.
  2. A new Hub page was invisible until a person remembered to add a line. By
     06/08 the Hub had 65 pages and the list still had 47.
  3. It could not see the datasets. 459 suppliers are loaded into the Suppliers
     page from JSON at run time, so none of those names existed in any page's
     HTML and none of them were searchable anywhere on the Hub.

This script removes all three by building the index from what is actually
published: it crawls every live Hub page, takes each section's heading, anchor
and searchable words, and merges in the supplier records this repo already
holds. The output is data/hub-search-index.json, which app/hub-search.js loads
in the browser.

Nothing here is AI and nothing here costs anything to run: it is a crawl, a
strip and a sort. Search happens in the member's browser against a static file.

IT CARRIES NO READABLE HUB TEXT, ON PURPOSE. This repo is public, so anything in
the index is readable by anyone; a paywalled product's prose does not go in it.
See the note above MAX_WORDS for what that means and what it costs.

WHAT IS DELIBERATELY THROWN AWAY
--------------------------------
Every Hub page carries the same <header> nav listing all the section names, and
the same <footer>. Indexed, that makes every page match every nav word — search
"frameworks" and all 65 pages come back, which is the exact "returns all random
stuff" failure this replaces. So header, footer, nav, style, script and svg are
stripped before a single word is indexed, and a short BOILERPLATE list catches
the stragglers that sit outside those tags.

RUNNING IT
    WPCOM_TOKEN=... python3 build_search_index.py            # crawl and write
    WPCOM_TOKEN=... python3 build_search_index.py --dry-run   # crawl, write, no commit (CI decides)
    python3 build_search_index.py --offline                   # fixtures only, no token needed

--offline is how the parsing is tested without a token: it reads the captured
pages in tests/fixtures/search/ instead of the API. The token only ever exists
as the GitHub secret WPCOM_TOKEN — never in this repo, never in chat.

AFTER RUNNING: scripts/stamp_notice.py, then verify.py. The workflow does both.
"""
import argparse
import glob
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SITE = "254135288"
API = "https://public-api.wordpress.com/wp/v2/sites/%s/pages" % SITE

OUT = "data/hub-search-index.json"
FIXTURES = "tests/fixtures/search"

# Hub pages live under this path. Anything else on the site is the shop, the
# login flow or marketing, and a member searching the Hub does not want it.
HUB_PREFIX = "/medical-sales-hub/"

# Pages outside /medical-sales-hub/ that a member genuinely searches for.
# Keep this SHORT and keep it justified — every id here is a page that answers
# a question a member asks, not a page we would like them to see.
EXTRA_IDS = {
    2324,  # How to Get the Most Out of the Hub — Member Guide
}

# Never index these, whatever their path: they are transactional, they contain
# no answers, and a member landing on them from a search has been sent nowhere.
EXCLUDE_IDS = {165, 166, 167, 685, 686, 687, 688, 946, 955, 957}

# Text that appears on many pages and belongs to the furniture, not the content.
# Matched after tag-stripping, case-insensitively, and removed.
BOILERPLATE = (
    "back to main site",
    "subscribers only",
    "medical sales hub",
    "join log in",
)

# THE INDEX CARRIES NO READABLE HUB TEXT. THIS IS THE POINT, NOT A LIMITATION.
#
# The browser fetches this file from a PUBLIC repository — that is how the Hub
# loads it, and it is why anyone can read data/supplier-index.json today. An
# index holding running prose from every Hub page would therefore put the
# written content of a PAYWALLED product on GitHub for anyone to download. The
# Hub is the product; publishing its text to make its search box better is a bad
# trade, and Lou ruled on it on 06/08/2026.
#
# So a section stores its HEADING, its ANCHOR, and a BAG OF WORDS: unique,
# alphabetised, stopwords dropped. Sorting destroys word order and dropping
# duplicates destroys frequency, so the prose cannot be reassembled from it,
# while every word a member might search for is still there to match on.
#
# WHAT THIS COSTS: a result cannot quote the line it matched on. It gives you
# the page and the section, and links straight to it. If that quoted line is
# ever wanted back, the index has to move behind the login first — never make
# this file more readable to get it.
MAX_WORDS = 120
MAX_SECTIONS = 60
HEADING_CHARS = 120

# Dropped from the bag: they match everything, so they narrow nothing, and they
# are the words that would help most in reconstructing a sentence.
BAG_STOP = set((
    "the a an of for in on at to is are am was were be been being do does did "
    "how what where which who whom why when this that these those it its and or "
    "but if as by from with without into onto over under than then so such not "
    "no nor can could should would will shall may might must have has had you "
    "your we our they their he she his her i me my us them there here all any "
    "each every other more most some very also just only own same too s t"
).split())

TAG_BLOCKS = ("style", "script", "header", "footer", "nav", "svg", "noscript")

# Decorative glyphs that are furniture, not words. "GOV.UK ↗" is a link marker.
GLYPHS = "←→↑↓↗↘↖↙⟶▸▪●■"

# CONTENT THAT MOVES FASTER THAN THIS INDEX REBUILDS.
#
# The Live Desk's panels are rewritten HOURLY by the cloud pipeline, and the
# ticker with them. This index rebuilds daily. Indexing those rows would put a
# member one search away from a headline that left the page hours ago — a result
# that looks like Hub content and is not on the Hub any more. So the rotating
# regions are stripped and only the stable page around them is indexed.
#
# <ul class="rows"> is exactly the region publish.py owns; the ticker is the
# other one. Both are matched by class, so a page that does not carry the
# pipeline pattern is untouched.
#
# THESE MUST BE STRIPPED WITH NESTING HONOURED, NOT WITH A NON-GREEDY REGEX.
# The first version used `<span class="tick">.*?</span>` and looked correct
# against a hand-written fixture. The real ticker nests:
#
#     <span class="tick"><span class="tag t-tender">TENDER</span><a …>…</a></span>
#
# so `.*?` stopped at the FIRST </span> — the inner one — and left the headline
# behind. The gate caught it on the first real crawl (a month token reached the
# Live Desk's words); a simpler fixture never would have.
VOLATILE = (
    ("ul", "rows"),
    ("span", "tick"),
    ("div", "ticker"),        # the wrapper, in case an item ever loses its class

    # IN-PAGE DIRECTORIES. The Live Desk carries two grids of links to other Hub
    # pages — "ON THE DESK" (.eth-index) and "EXPLORE THE HUB" (.explore). They
    # are navigation that happens to sit in the body rather than the header, and
    # indexing them gave the Live Desk 120 words made entirely of other pages'
    # names, so it competed with the very pages it links to. Same reasoning as
    # stripping <nav>: a list of where to go is not an answer.
    ("section", "explore"),
    ("div", "eth-index"),
)


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------
def api_get(url, token, timeout=45, tries=3):
    """Retries a transient WP.com 5xx (same pattern as scripts/refresh_frameworks.py).

    This build failed outright on a bare HTTP 500 five times between 28/08 and
    01/09/2026 with no retry at all — a single blip from WordPress.com's own
    API killed the whole run and left search on the last good index (harmless,
    but avoidable) instead of the day's real content changes.
    """
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "User-Agent": "msh-search-index/1.0",
    })
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def fetch_pages(token):
    """Every published page, with its raw content. Paginated."""
    out, page = [], 1
    while True:
        url = API + "?" + urllib.parse.urlencode({
            "status": "publish",
            "per_page": "100",
            "page": str(page),
            "context": "edit",
            "orderby": "id",
            "order": "asc",
        })
        try:
            batch = api_get(url, token)
        except urllib.error.HTTPError as exc:
            if exc.code == 400 and page > 1:
                break          # ran off the end of the pagination
            raise
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.4)
    return out


def load_fixtures():
    files = sorted(glob.glob(os.path.join(FIXTURES, "*.json")))
    if not files:
        sys.exit("--offline needs captured pages in %s/ and there are none." % FIXTURES)
    out = []
    for path in files:
        with open(path) as f:
            out.append(json.load(f))
    return out


# --------------------------------------------------------------------------
# Text extraction
# --------------------------------------------------------------------------
def raw_content(page):
    c = page.get("content") or {}
    if isinstance(c, dict):
        return c.get("raw") or c.get("rendered") or ""
    return c or ""


def plain_title(page):
    t = page.get("title") or {}
    if isinstance(t, dict):
        t = t.get("raw") or t.get("rendered") or ""
    t = htmllib.unescape(re.sub(r"<[^>]+>", "", str(t))).strip()
    # Hub page titles carry an access marker that is not part of the name.
    t = re.sub(r"\s*\(Subscribers only\)\s*$", "", t, flags=re.I)
    return t.strip()


def path_of(page):
    link = page.get("link") or ""
    try:
        return urllib.parse.urlparse(link).path or "/"
    except ValueError:
        return "/"


def strip_element(html, tag, class_word):
    """Remove every <tag class="… class_word …"> … </tag>, counting nesting.

    A non-greedy regex cannot do this: it closes on the first </tag> it meets,
    which for a nested element is the WRONG one and leaves the tail behind. That
    is not hypothetical — see the note above VOLATILE.
    """
    opener = re.compile(r"<%s\b[^>]*\bclass\s*=\s*[\"'][^\"']*\b%s[^\"']*[\"'][^>]*>"
                        % (tag, class_word), re.I)
    any_open = re.compile(r"<%s\b[^>]*?(?<!/)>" % tag, re.I)
    closer = re.compile(r"</%s\s*>" % tag, re.I)

    out, pos = [], 0
    while True:
        m = opener.search(html, pos)
        if not m:
            break
        depth, i = 1, m.end()
        while depth > 0:
            nxt_close = closer.search(html, i)
            if not nxt_close:
                i = len(html)          # unbalanced markup: drop to the end
                break
            nxt_open = any_open.search(html, i)
            if nxt_open and nxt_open.start() < nxt_close.start():
                depth += 1
                i = nxt_open.end()
            else:
                depth -= 1
                i = nxt_close.end()
        out.append(html[pos:m.start()])
        pos = i
    out.append(html[pos:])
    return " ".join(out)


def strip_furniture(src):
    """Remove everything that is chrome rather than content.

    Order matters: comments first (Gutenberg wraps every block in one), then
    whole tag blocks, then remaining tags. Losing the nav here is the single
    most important step — see the module docstring.
    """
    s = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    for tag, cls in VOLATILE:
        s = strip_element(s, tag, cls)
    for tag in TAG_BLOCKS:
        s = re.sub(r"<%s\b[^>]*>.*?</%s\s*>" % (tag, tag), " ", s, flags=re.S | re.I)
        # Unclosed or self-closing leftovers.
        s = re.sub(r"<%s\b[^>]*/?>" % tag, " ", s, flags=re.I)
    return s


def clean_text(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    t = htmllib.unescape(t)
    t = t.replace(" ", " ")
    t = re.sub(r"\s+", " ", t).strip()
    for junk in BOILERPLATE:
        t = re.sub(re.escape(junk), " ", t, flags=re.I)
    for g in GLYPHS:
        t = t.replace(g, " ")
    return re.sub(r"\s+", " ", t).strip(" -·—|")


HEADING = re.compile(r"<h([1-4])\b([^>]*)>(.*?)</h\1\s*>", re.S | re.I)
ID_ATTR = re.compile(r"""\bid\s*=\s*["']([A-Za-z][\w:.-]*)["']""")
# An id on the tag that opens immediately before the heading — that tag is the
# section wrapper, so its id is the right anchor. Anything further back is a
# guess, and a guess sends the reader to the wrong part of the page.
ID_BEFORE = re.compile(r"""\bid\s*=\s*["']([A-Za-z][\w:.-]*)["'][^<>]*>\s*$""")


def anchor_for(attrs, preceding):
    m = ID_ATTR.search(attrs or "")
    if m:
        return m.group(1)
    m = ID_BEFORE.search(preceding[-160:])
    if m:
        return m.group(1)
    return ""


def bag(text):
    """A section's searchable words: unique, alphabetised, stopwords dropped.

    Sorting throws away word order and de-duplication throws away frequency, so
    what is left matches a query but cannot be read back as the Hub's prose. See
    the note on MAX_WORDS — this is the whole reason the index is shaped this
    way, and turning it back into running text would republish a paid product.
    """
    words = set()
    for w in re.split(r"[^a-z0-9]+", text.lower()):
        if len(w) < 2:
            continue
        if w in BAG_STOP:
            continue
        words.add(w)
    return " ".join(sorted(words)[:MAX_WORDS])


def sections_of(src, page_title):
    """Split a page into (heading, anchor, word-bag) in document order."""
    body = strip_furniture(src)
    out = []
    marks = list(HEADING.finditer(body))

    # Text before the first heading. Often it is the page's standfirst and worth
    # having; sometimes it is a stray glyph left by the "back to main site" bar,
    # which is a result with nothing in it. 25 characters separates the two.
    lead = clean_text(body[:marks[0].start()] if marks else body)
    if len(lead) >= 25:
        out.append({"h": page_title[:HEADING_CHARS], "a": "", "w": bag(lead)})

    for i, m in enumerate(marks):
        heading = clean_text(m.group(3))
        if not heading:
            continue
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        text = clean_text(body[m.end():end])
        anchor = anchor_for(m.group(2), body[:m.start()])
        out.append({"h": heading[:HEADING_CHARS], "a": anchor, "w": bag(text)})

    # A section needs a heading someone could read, or enough words to be worth
    # matching. Anything else is a row in the results list that wastes a click.
    out = [s for s in out if len(s["h"]) >= 3 or len(s["w"].split()) >= 5]
    return out[:MAX_SECTIONS]


# --------------------------------------------------------------------------
# Dataset records — things that are on the Hub but not in any page's HTML
# --------------------------------------------------------------------------
def supplier_records():
    """The 459 suppliers the Suppliers page loads at run time.

    These names exist in data/supplier-index.json and in no page's HTML, which
    is why searching a supplier name has never found anything. The link carries
    #q=<name>, which app/supplier-search.js reads on load and runs.
    """
    path = "data/supplier-index.json"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        doc = json.load(f)
    out = []
    for s in doc.get("suppliers", []):
        name = (s.get("name") or "").strip()
        if not name:
            continue
        bits = [name]
        bits.extend(a for a in (s.get("aliases") or []) if a)
        bits.extend(x for x in (s.get("specialities") or []) if isinstance(x, str))
        for fw in (s.get("frameworks") or []):
            if isinstance(fw, str):
                bits.append(fw)
            elif isinstance(fw, dict) and fw.get("name"):
                bits.append(fw["name"])
        keywords = " ".join(bits).lower()
        keywords = re.sub(r"[^a-z0-9 ]+", " ", keywords)
        keywords = re.sub(r"\s+", " ", keywords).strip()
        out.append({
            "t": name,
            "u": HUB_PREFIX + "suppliers/#q=" + urllib.parse.quote(name),
            "k": keywords[:400],
            "c": "Supplier",
        })
    out.sort(key=lambda r: r["t"].lower())
    return out


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def wanted(page):
    pid = page.get("id")
    if pid in EXCLUDE_IDS:
        return False
    if pid in EXTRA_IDS:
        return True
    return path_of(page).startswith(HUB_PREFIX)


def build(pages):
    indexed = []
    for page in sorted(pages, key=lambda p: p.get("id", 0)):
        if not wanted(page):
            continue
        title = plain_title(page)
        src = raw_content(page)
        if not title or not src:
            continue
        secs = sections_of(src, title)
        words = sum(len(s["w"].split()) for s in secs)
        if words < 5:
            # A page with essentially no text is a shell — a loader, a redirect
            # stub or a page whose content is drawn entirely by script. Indexing
            # it puts a result in front of a member that answers nothing.
            continue
        indexed.append({
            "id": page.get("id"),
            "t": title,
            "u": path_of(page),
            "sec": secs,
        })

    now = datetime.now(timezone.utc)
    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataAsOf": now.strftime("%Y-%m-%d"),
        "note": ("Search index for the Medical Sales Intelligence Hub, built from the "
                 "Hub's own published pages. Rebuilt daily; see build_search_index.py."),
        "pages": indexed,
        "records": supplier_records(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="build from tests/fixtures/search instead of the API (no token needed)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--stats", action="store_true", help="print a size and coverage report")
    args = ap.parse_args()

    if args.offline:
        pages = load_fixtures()
    else:
        token = os.environ.get("WPCOM_TOKEN")
        if not token:
            sys.exit("No WPCOM_TOKEN in the environment. Use --offline to build from "
                     "fixtures, or run this where the secret exists.")
        pages = fetch_pages(token)

    doc = build(pages)

    if not doc["pages"]:
        sys.exit("No Hub pages were indexed. Refusing to write an empty index — that "
                 "would silently take Hub search offline.")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")

    secs = sum(len(p["sec"]) for p in doc["pages"])
    size = os.path.getsize(args.out)
    print("Indexed %d pages, %d sections, %d records -> %s (%.0f KB)"
          % (len(doc["pages"]), secs, len(doc["records"]), args.out, size / 1024.0))

    if args.stats:
        print("\nPages by section count:")
        for p in sorted(doc["pages"], key=lambda p: -len(p["sec"]))[:15]:
            words = sum(len(s["w"].split()) for s in p["sec"])
            print("  %-52s %3d sections %6d words" % (p["t"][:52], len(p["sec"]), words))


if __name__ == "__main__":
    main()
