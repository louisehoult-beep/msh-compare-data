#!/usr/bin/env python3
"""refresh_workforce_source.py - record where the latest NHS Workforce Statistics
"Trusts and core organisations - CSV data files" zip lives (added 25/11/2026).

WHY: digital.nhs.uk answers GitHub's runners HTTP 403, so the pipeline's trust_table.py
(medical-sales-hub-pipeline, trust-table.yml) cannot read the publication pages that
name the zip. The zip itself sits on files.digital.nhs.uk, which the runner CAN reach.
This script runs on the Mac (LaunchAgent digital-sources-weekly, Mondays), reads the
same pages, and writes config/workforce-source.json:

    {"publication": <publication page URL>, "file": <zip URL>, "readOn": "YYYY-MM-DD",
     "readFrom": <index URL>}

The runner downloads and parses that zip; the data month comes from the file itself.
Nothing is guessed: if no publication with the core zip is found, the file is left as
it is and the script exits 1.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

UA = "MedicalSalesHub/2.0 (+https://medsalesintelligencehub.co.uk; contact@elevateandthrive.uk)"
INDEX = "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-workforce-statistics"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "workforce-source.json")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
ZIP_RE = (r'https://files\.digital\.nhs\.uk/[^"\'\s]+Trusts%20and%20core%20organisations'
          r'%20-%20CSV%20data%20files[^"\'\s]*\.zip')


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*",
                                               "Accept-Language": "en-GB,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def candidates(index_html, today):
    found = set()
    for mon, yr in re.findall(r"/nhs-workforce-statistics/([a-z]+)-(20\d\d)\b", index_html):
        if mon in MONTHS:
            d = datetime.date(int(yr), MONTHS.index(mon) + 1, 1)
            if d <= today:
                found.add((d, "%s-%s" % (mon, yr)))
    return [s for _d, s in sorted(found, reverse=True)]


def find(getter, today):
    idx = getter(INDEX)
    for slug in candidates(idx, today)[:6]:
        page_url = INDEX + "/" + slug
        try:
            page = getter(page_url)
        except Exception as e:  # an announced-but-unpublished month can 404
            print("  %s: %s" % (slug, e))
            continue
        m = re.findall(ZIP_RE, page)
        if m:
            return page_url, m[0]
        print("  %s: no core CSV zip yet" % slug)
    return None, None


def main(getter=get, today=None, out=OUT):
    today = today or datetime.date.today()
    pub, z = find(getter, today)
    if not pub:
        print("workforce source: no publication with a core CSV zip found; %s left unchanged" % out)
        return 1
    doc = {"publication": pub, "file": z, "readOn": today.isoformat(), "readFrom": INDEX}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    print("workforce source: %s -> %s" % (pub, z))
    return 0


if __name__ == "__main__":
    sys.exit(main())
