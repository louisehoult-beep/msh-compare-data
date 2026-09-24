#!/usr/bin/env python3
"""
build_ask_passages.py — load the Hub's own text into the PRIVATE store that
"Ask the Hub" answers from.

WHY THIS IS NOT IN data/
------------------------
"Ask the Hub" (app/hub-search.js, the ask card) answers a member's question from
the Hub's written content and cites a Hub link on every point. To do that it has
to read real passages, not the word bags in data/hub-search-index.json. This repo
is PUBLIC and Lou ruled on 06/08/2026 that the Hub's paid text never goes in it,
so this script never writes a passage to disk. It crawls the same pages the
search index crawls, cuts each section into passages, and sends them straight to
a Supabase table (public.hub_passages) that has row level security on and no
policies: only the service role can read it, and only the ask-the-hub Edge
Function holds that. The page text never touches git.

HOW A LOAD REPLACES THE LAST ONE
--------------------------------
Passages are staged under a fresh build id in batches, then ONE call
(ask_publish_build) deletes every other build in the same transaction. So a
crawl that dies half way leaves yesterday's passages serving, never half of
today's, and the publish function refuses a build that is suspiciously small
(the same "never publish an empty index" rule build_search_index.py follows).

RUNNING IT
    WPCOM_TOKEN=... SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python3 build_ask_passages.py
    python3 build_ask_passages.py --offline --dry-run      # fixtures, print counts, send nothing

It runs in search-index.yml straight after the search index is built.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import build_search_index as bsi

# A passage is what the model reads and what a member's source link lands on.
# ~1,200 characters is a paragraph or two: long enough to carry a whole point,
# short enough that ten of them fit a prompt comfortably.
CHUNK = 1200
MIN_TEXT = 40
BATCH = 250
SUPPLIER_PRODUCTS = 6


def text_fragment(heading):
    """Same rule as textFragment() in app/hub-search.js: the first six words."""
    words = " ".join(str(heading or "").split()[:6])
    if len(words) < 4:
        return ""
    return "#:~:text=" + urllib.parse.quote(words, safe="")


def chunks(text):
    """Split on sentence ends so a passage never stops mid-sentence if it can help it."""
    if len(text) <= CHUNK:
        return [text]
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + 1 + len(sent) > CHUNK:
            out.append(cur)
            cur = sent
        else:
            cur = (cur + " " + sent).strip()
        while len(cur) > CHUNK * 1.5:          # one enormous "sentence" (a table row dump)
            out.append(cur[:CHUNK])
            cur = cur[CHUNK:]
    if cur:
        out.append(cur)
    return out


def page_passages(page):
    title = bsi.plain_title(page)
    src = bsi.raw_content(page)
    if not title or not src:
        return []
    url = bsi.path_of(page)
    body = bsi.strip_furniture(src)
    marks = list(bsi.HEADING.finditer(body))
    out = []

    def add(heading, anchor, text):
        if len(text) < MIN_TEXT:
            return
        link = url + ("#" + anchor if anchor else text_fragment(heading))
        for part in chunks(text):
            out.append({"page_id": page.get("id"), "page_title": title, "url": link,
                        "heading": heading[:bsi.HEADING_CHARS], "body": part, "kind": "page"})

    lead = bsi.clean_text(body[:marks[0].start()] if marks else body)
    add(title, "", lead)
    for i, m in enumerate(marks):
        heading = bsi.clean_text(m.group(3))
        if not heading:
            continue
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        add(heading, bsi.anchor_for(m.group(2), body[:m.start()]), bsi.clean_text(body[m.end():end]))
    return out


def supplier_passages():
    """One passage per supplier, from the same file the company report reads.

    CONFIRMED FACTS ONLY, the same rule as the quick answer in hub-search.js: a
    framework goes in only when the record carries the URL of its source notice.
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
        lines = [name + "."]
        aliases = [a for a in (s.get("aliases") or []) if a and a != name]
        if aliases:
            lines.append("Also known as: " + ", ".join(aliases[:6]) + ".")
        specs = [x for x in (s.get("specialities") or []) if isinstance(x, str)]
        if specs:
            lines.append("Specialities: " + ", ".join(specs) + ".")
        fws = [fw for fw in (s.get("frameworks") or [])
               if isinstance(fw, dict) and fw.get("url") and fw.get("name")]
        if fws:
            lines.append("Confirmed framework places (from the source notice): " + "; ".join(
                fw["name"] + (" (" + fw["dates"] + ")" if fw.get("dates") else "") for fw in fws) + ".")
        else:
            lines.append("No framework place is confirmed from a source notice in the Hub's record.")
        prods = [p for p in (s.get("products") or []) if isinstance(p, str)][:SUPPLIER_PRODUCTS]
        if prods:
            lines.append("Key products: " + "; ".join(prods) + ".")
        out.append({"page_id": None, "page_title": "Company report: " + name,
                    "url": bsi.HUB_PREFIX + "company-report/?company=" + urllib.parse.quote(name),
                    "heading": name, "body": " ".join(lines)[:CHUNK * 2], "kind": "supplier"})
    return out


def build(pages):
    out = []
    for page in sorted(pages, key=lambda p: p.get("id", 0)):
        if bsi.wanted(page):
            out.extend(page_passages(page))
    return out, supplier_passages()


def rpc(base, key, name, payload):
    req = urllib.request.Request(
        base.rstrip("/") + "/rest/v1/rpc/" + name,
        data=json.dumps(payload).encode("utf-8"),
        headers={"apikey": key, "Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            if exc.code < 500 or attempt == 2:
                sys.exit("Supabase %s refused (HTTP %d): %s" % (name, exc.code, detail))
        except urllib.error.URLError as exc:
            if attempt == 2:
                sys.exit("Supabase %s unreachable: %s" % (name, exc))
        time.sleep(3 * (attempt + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="build from tests/fixtures/search")
    ap.add_argument("--dry-run", action="store_true", help="build and count, send nothing")
    args = ap.parse_args()

    if args.offline:
        pages = bsi.load_fixtures()
    else:
        token = os.environ.get("WPCOM_TOKEN")
        if not token:
            sys.exit("No WPCOM_TOKEN in the environment.")
        pages = bsi.fetch_pages(token)

    page_rows, sup_rows = build(pages)
    rows = page_rows + sup_rows
    chars = sum(len(r["body"]) for r in rows)
    print("Built %d page passages from %d pages and %d supplier passages (%.0f KB of text)"
          % (len(page_rows), len({r["page_id"] for r in page_rows}), len(sup_rows), chars / 1024.0))
    if not page_rows:
        sys.exit("No Hub page passages. Refusing to replace the store with nothing.")
    if args.dry_run:
        return

    base, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not base or not key:
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_KEY are both needed to load passages.")

    build_id = uuid.uuid4().hex
    for i in range(0, len(rows), BATCH):
        rpc(base, key, "ask_stage_passages", {"p_build": build_id, "p_rows": rows[i:i + BATCH]})
    live = rpc(base, key, "ask_publish_build", {"p_build": build_id, "p_min_pages": 20})
    print("Published build %s: %s passages now serving" % (build_id[:8], live))


if __name__ == "__main__":
    main()
