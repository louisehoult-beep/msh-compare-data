#!/usr/bin/env python3
"""Cache NHS Supply Chain's Procurement Calendar.

Written 02/09/2026 after the NBE leave-behind review found that the Hub was
publishing an expiry date for Technology Enabled Care (2021/S 000-031857) that
NHS Supply Chain's own procurement calendar contradicts. The framework launch
brief said the framework runs to 31/08/2027; the calendar gave its successor a
contract go-live of 01/09/2026. Both pages are NHS Supply Chain's, both were
edited within the last six weeks, and the Hub had copied one half of a
contradiction and published it as a fact.

The calendar is the only public source that says what is coming NEXT for a
category, so caching it is what lets verify.py cross-check a framework's stated
expiry against its successor's stated go-live. Nothing here is interpreted: the
rows are copied as published.

Run daily alongside the launch-brief refresh. One request.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

URL = "https://www.supplychain.nhs.uk/savings/procurement-calendar/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "nhssc-procurement-calendar.json")

NOTICE = {
    "owner": "Elevate and Thrive Ltd, company number 17154474, England and Wales",
    "source": "NHS Supply Chain Procurement Calendar",
    "sourceUrl": URL,
    "rule": ("Rows are copied exactly as published. Nothing is derived, ranked or "
             "interpreted here. 'Published' in the publication column is NHS Supply "
             "Chain's own word for a procurement already out to market, not a date."),
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def strip(html):
    html = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", html)
    txt = re.sub(r"(?s)<[^>]+>", "", html)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#8217;", "'"),
                 ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        txt = txt.replace(a, b)
    return re.sub(r"\s+", " ", txt).strip()


def parse(html):
    rows = []
    for tr in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", html):
        cells = [strip(c) for c in re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
        if len(cells) < 4:
            continue
        name, category, publication, golive = cells[0], cells[1], cells[2], cells[3]
        if not name or name.lower().startswith("contract"):
            continue
        rows.append({
            "framework": name,
            "category": category,
            "plannedPublication": publication,
            "contractGoLive": golive,
        })
    return rows


def main():
    html = fetch(URL)
    rows = parse(html)
    if len(rows) < 30:
        print("REFUSING to write: parsed only %d rows. The calendar has carried "
              "50+ for as long as we have read it, so this is a parse failure or a "
              "page redesign, not a shrunken calendar." % len(rows), file=sys.stderr)
        return 1

    m = re.search(r"Last updated:\s*([0-9]{1,2} [A-Za-z]+ 20[0-9]{2})", strip(html))
    doc = {
        "_notice": NOTICE,
        "generated": datetime.datetime.now(datetime.timezone.utc)
                             .isoformat(timespec="seconds"),
        "pageLastUpdated": m.group(1) if m else None,
        "count": len(rows),
        "rows": rows,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote %s — %d rows, page last updated %s"
          % (OUT, len(rows), doc["pageLastUpdated"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
