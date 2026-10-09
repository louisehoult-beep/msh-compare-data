"""One-off, 28/09/2026: finish the 08413ef spec restore properly.

08413ef restored 51 product records (Essity 33, L&R 11, Convatec 7) whose hand-
captured `specs` the 08/09 image backfill (55b3bad) had wiped. It restored each
record WHOLE from 55b3bad^ — and at 55b3bad^ those were spec-only records, with
no description, features or image. So the restore brought the specs back and
threw away the description and features the backfill had read from the live
page: 47 of the 51 lost their description. The Differentiator had not been
rebuilt since, so members still saw the backfill's text; the next rebuild would
have blanked 47 published product rows.

The right record is what record_capture() now produces on a re-crawl: the crawl's
own fields from the backfill (sourceUrl, capturedDate, parsed, description,
features, image, changedSince) plus the curated fields it carries forward
(`specs`, `category`). `specs` keeps its own _sourceUrl/_capturedDate, so it stays
attributed to the page it was read from.

Records whose backfill text was site chrome (7 Convatec) are left as re-read by
_fix_crawl_junk_records_0928.py. Run this first, then that, then rebuild the Differentiator and dossiers.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crawl_supplier_product_detail import looks_like_site_chrome  # noqa: E402

DETAIL = "data/supplier-product-detail.json"
CRAWL_FIELDS = ("sourceUrl", "capturedDate", "parsed", "description", "features",
                "image", "changedSince")
CURATED = ("specs", "category")


def at(rev):
    return json.loads(subprocess.check_output(
        ["git", "show", "%s:%s" % (rev, DETAIL)]))["products"]


def main():
    before = at("08413ef^")          # the backfill's records, specs wiped
    restore = at("08413ef")          # the restore, specs back, crawl text gone
    doc = json.load(open(DETAIL))
    store = doc["products"]
    fixed = []
    for k, v in restore.items():
        b = before.get(k)
        if not (v.get("specs") and b and not b.get("specs")):
            continue                 # not one of the 51 restored records
        cur = store.get(k)
        if cur is None:
            continue
        if looks_like_site_chrome(b.get("description") or ""):
            # 7 Convatec records: the backfill's text was the site header, and
            # _fix_crawl_junk_records_0928.py has re-read the page since. Keep that.
            continue
        merged = {f: cur[f] for f in ("supplier", "product") if f in cur}
        for f in CRAWL_FIELDS:
            if b.get(f) is not None:
                merged[f] = b[f]
        for f in CURATED:
            if cur.get(f) is not None:
                merged[f] = cur[f]
        if merged != cur:
            store[k] = merged
            fixed.append(k)
    with open(DETAIL, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("%d restored record(s) re-merged: crawl fields from 08413ef^, specs/category kept"
          % len(fixed))
    for k in fixed:
        print("  " + k)


if __name__ == "__main__":
    main()
