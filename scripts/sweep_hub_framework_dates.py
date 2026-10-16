#!/usr/bin/env python3
"""Daily sweep: run the framework-date guard over every live Hub page.

Added 16/10/2026 after page 2802's calendar note blurred two frameworks' expiry
dates. Lou's rule: no manual checks. This runs from GitHub Actions
(.github/workflows/framework-dates.yml) every day and on demand, reads every Hub
page through the WordPress.com API (token WPCOM_TOKEN, read only) and fails the
run on any finding that is not already in data/framework-date-guard-baseline.json.

The baseline is a ratchet: findings that existed when the guard was introduced
are recorded (as hashes, never page text, because this repo is public) so the
gate can go live without a week of cleanup; anything NEW fails the run, and a
baseline entry whose problem has gone is reported so it can be removed with
--update-baseline.

Output never prints page text (public repo, paid content): page id, framework
reference and the date only.

  python3 scripts/sweep_hub_framework_dates.py                  # gate
  python3 scripts/sweep_hub_framework_dates.py --update-baseline
"""
import hashlib
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import framework_date_guard as guard  # noqa: E402

BASELINE = os.path.join(HERE, "..", "data", "framework-date-guard-baseline.json")
API = "https://public-api.wordpress.com/wp/v2/sites/254135288/pages"
MIN_PAGES = 100   # the Hub has ~150; far fewer means the read failed, not that all is well


def fetch_pages(token):
    pages, n = [], 1
    while True:
        url = ("%s?context=edit&per_page=100&status=publish,private,draft&page=%d"
               "&_fields=id,title,content" % (API, n))
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token,
                                                   "User-Agent": "MedicalSalesHub/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                batch = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 400 and n > 1:      # past the last page
                break
            raise
        if not batch:
            break
        pages += batch
        n += 1
    return pages


def signature(page_id, problem):
    return hashlib.sha1(("%s|%s" % (page_id, problem)).encode("utf-8")).hexdigest()[:16]


def short(problem):
    """The reportable part of a finding without page text."""
    head = problem.split(":")[0]
    return head[:110]


def main(argv):
    token = os.environ.get("WPCOM_TOKEN", "")
    if not token:
        print("No WPCOM_TOKEN: nothing was checked.")
        return 1
    pages = fetch_pages(token)
    if len(pages) < MIN_PAGES:
        print("Only %d pages read (expected 100+): the read failed, nothing was checked." % len(pages))
        return 1
    fws = guard.load_frameworks()
    found = {}
    for p in pages:
        raw = (p.get("content") or {}).get("raw") or ""
        for problem in guard.check_text(raw, fws):
            found[signature(p["id"], problem)] = "page %s: %s" % (p["id"], short(problem))
    try:
        with open(BASELINE, encoding="utf-8") as f:
            baseline = json.load(f).get("findings", {})
    except FileNotFoundError:
        baseline = {}
    if "--update-baseline" in argv:
        with open(BASELINE, "w", encoding="utf-8") as f:
            json.dump({"note": "Findings recorded when the guard went live (16/10/2026). Hashes only: "
                               "the repo is public. Remove entries by fixing the page, then --update-baseline.",
                       "findings": found}, f, indent=1, sort_keys=True)
            f.write("\n")
        print("baseline written: %d finding(s) over %d pages" % (len(found), len(pages)))
        return 0
    new = {k: v for k, v in found.items() if k not in baseline}
    gone = [v for k, v in baseline.items() if k not in found]
    for v in sorted(new.values()):
        print("NEW  " + v)
    for v in sorted(gone):
        print("fixed since baseline (remove with --update-baseline): " + v)
    print("%d page(s) read, %d finding(s), %d baselined, %d new" % (len(pages), len(found), len(found) - len(new), len(new)))
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
