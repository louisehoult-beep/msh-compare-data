#!/usr/bin/env python3
"""
refresh_npm_finder.py — one list of every NHS Supply Chain National Pricing
Matrix (NPM), for the Hub's NPM Finder.

WHY THIS EXISTS (added 20/10/2026)
----------------------------------
A clinical procurement lead told Lou that NHS Supply Chain keeps no list of the
NPMs a trust can use: trusts wait for their Hospital Care Team or a supplier to
raise one. NHS Supply Chain does publish the categories that have an NPM, on
one public page, and each framework's public launch brief says whether it
offers one. This script joins the two to the Hub's framework data, so a member
sees every NPM category beside its framework, dates and supplier count.

WHAT IT READS (public HTML only, no login, no secret)
    1. https://www.supplychain.nhs.uk/savings/npms/  — the category list and the
       page's own explanation of what an NPM is and how to sign up.
    2. Each matched framework's launch brief — the "Savings Opportunities"
       sentence about the NPM, and whether an NPM download is listed.
    3. data/frameworks.json — framework name, reference, dates, supply route,
       supplier count. Only live frameworks; expired ones are never matched.

WHAT IT DOES NOT READ
    The NPM spreadsheets themselves (which suppliers, which products, which
    tiers) sit behind authentication.supplychain.nhs.uk. They are deliberately
    NOT fetched, and nothing here claims to know which suppliers offer an NPM.

⚠️ MATCHING IS STRICT ON PURPOSE. A category is joined to a framework only when
the names are equal once punctuation and the word "and" are ignored, or when the
category name is the opening words of exactly one framework name ("Surgical
Mesh" matching "Surgical Mesh", "Central Venous Catheters" matching "Central
Venous Catheters and Associated Products"). Anything else is published as "not
matched". An NPM can belong to an earlier framework generation than the one
live today, and a guessed join would put the wrong dates and suppliers in front
of a member. Do not add fuzzy matching to raise the count.

⚠️ TWO GUARDS. If fewer than MIN_CATEGORIES categories are read, the page has
probably been redesigned: write nothing. If the count falls by more than
MAX_DROP against the previous run, write nothing and find out why.

⚠️ NOTHING ELSE MAY WRITE data/npm-finder.json. This is its only writer.

USAGE
    python3 scripts/refresh_npm_finder.py
"""
from __future__ import annotations

import datetime as dt
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.request

NPM_URL = "https://www.supplychain.nhs.uk/savings/npms/"
OUT = os.path.join("data", "npm-finder.json")
FRAMEWORKS = os.path.join("data", "frameworks.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

MIN_CATEGORIES = 15
MAX_DROP = 0.25


def fetch(url: str, tries: int = 2) -> str | None:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as exc:  # network errors are recorded, not fatal per brief
            print("fetch failed (%s): %s" % (exc, url), file=sys.stderr)
            time.sleep(3)
    return None


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def norm(name: str) -> str:
    s = name.lower().replace("&", " and ").replace("’", "'")
    words = re.findall(r"[a-z0-9']+", s)
    return " ".join(w for w in words if w != "and")


def parse_categories(page: str) -> list[str]:
    """The link texts under the 'NPMs (National Pricing Matrices)' heading,
    up to the 'Links section'. The intravenous cannula entry is split across
    two links on the live page ('... Associated Products' + 'National Pricing
    Matrix (NPM)'); a bare 'National Pricing Matrix (NPM)' is never a category."""
    start = page.find("NPMs (National Pricing Matrices)")
    if start < 0:
        return []
    end = page.find("Links section", start)
    seg = page[start:end if end > 0 else start + 30000]
    out: list[str] = []
    for inner in re.findall(r"<a\b[^>]*>(.*?)</a>", seg, flags=re.S):
        name = text_of(inner)
        if not name or re.fullmatch(r"National Pricing Matri(x|ces)( \(NPMs?\))?", name):
            continue
        name = re.sub(r"\s*National Pricing Matrix \(NPM\)$", "", name).strip()
        if name and name not in out:
            out.append(name)
    return out


def parse_guidance(page: str) -> dict:
    """The page's own words, quoted, for the panel header."""
    t = text_of(page)

    def between(a: str, b: str) -> str | None:
        i = t.find(a)
        if i < 0:
            return None
        j = t.find(b, i + len(a))
        return t[i + len(a):j].strip() if j > 0 else None

    return {
        "what": between("What is a National Pricing Matrix?", "Who can access"),
        "who": between("Who can access the NPM savings?", "How do I sign up"),
        "how": between("How do I sign up for an NPM?", "There are now a number"),
    }


def match_framework(category: str, frameworks: list[dict]) -> tuple[dict | None, str]:
    c = norm(category)
    exact = [f for f in frameworks if norm(f["name"]) == c]
    if len(exact) == 1:
        return exact[0], "same name"
    prefix = [f for f in frameworks if norm(f["name"]).startswith(c + " ")]
    if len(prefix) == 1:
        return prefix[0], "category name opens the framework name"
    return None, "not matched"


def brief_npm(url: str) -> dict:
    page = fetch(url)
    if page is None:
        return {"statement": None, "read": False}
    t = text_of(page)
    sentences = re.split(r"(?<=[.!?])\s+", t)
    said = [s for s in sentences if re.search(r"National Pricing Matrix|\bNPMs?\b", s)
            and len(s) < 400 and "An Excel file" not in s]
    statement = said[0] if said else None
    if statement:
        # The heading runs into the sentence once tags are stripped.
        statement = re.sub(r"^(Savings [Oo]pportunities\s*)+", "", statement).strip()
    return {"statement": statement, "read": True}


def main() -> int:
    page = fetch(NPM_URL)
    if page is None:
        print("NPM page unreachable; writing nothing.", file=sys.stderr)
        return 1
    cats = parse_categories(page)
    if len(cats) < MIN_CATEGORIES:
        print("Only %d categories read (minimum %d); page may have changed. Writing nothing."
              % (len(cats), MIN_CATEGORIES), file=sys.stderr)
        return 1
    if os.path.exists(OUT):
        prev = json.load(open(OUT)).get("categoryCount") or 0
        if prev and len(cats) < prev * (1 - MAX_DROP):
            print("Category count fell from %d to %d (more than %d%%). Writing nothing."
                  % (prev, len(cats), MAX_DROP * 100), file=sys.stderr)
            return 1

    fw_doc = json.load(open(FRAMEWORKS))
    frameworks = [f for f in fw_doc.get("frameworks", []) if f.get("name")]

    rows = []
    for name in cats:
        fw, rule = match_framework(name, frameworks)
        row = {"category": name, "match": rule, "framework": None, "brief": None}
        if fw:
            row["framework"] = {
                "name": fw["name"],
                "url": fw.get("url"),
                "reference": fw.get("reference"),
                "starts": fw.get("starts"),
                "ends": fw.get("ends"),
                "supplyRoute": fw.get("supplyRoute"),
                "supplierCount": len(fw.get("suppliers") or []),
            }
            if fw.get("url"):
                row["brief"] = brief_npm(fw["url"])
                time.sleep(1)
        rows.append(row)

    doc = {
        "source": "NHS Supply Chain, National Pricing Matrices page and contract launch briefs",
        "source_url": NPM_URL,
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "guidance": parse_guidance(page),
        "notFetched": ("The NPM spreadsheets (which suppliers, products and price tiers) are "
                       "behind authentication.supplychain.nhs.uk and are not taken. Nothing here "
                       "states which suppliers offer an NPM."),
        "matchRule": ("A category is joined to a live framework only when the names are equal "
                      "ignoring punctuation and the word 'and', or the category name opens exactly "
                      "one framework name. Anything else is shown as not matched."),
        "categoryCount": len(rows),
        "matchedCount": sum(1 for r in rows if r["framework"]),
        "categories": rows,
    }
    # Keep the notice block if the file already carries one; stamp_notice.py re-stamps.
    if os.path.exists(OUT):
        old = json.load(open(OUT))
        if "_notice" in old:
            doc = {"_notice": old["_notice"], **doc}
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("npm-finder: %d categories, %d matched to a live framework"
          % (doc["categoryCount"], doc["matchedCount"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
