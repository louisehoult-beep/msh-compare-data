#!/usr/bin/env python3
"""
check_other_body_frameworks.py - re-read every "otherBodies" row in
data/framework-directory-extra.json at its own source page and say whether the
stored reference, start and end date still match what that page states.

WHY (added 22/10/2026). Page 3198's Frameworks directory renders NHS Supply Chain
rows live, but the 23 rows from other bodies (NHS Shared Business Services, the
Government Commercial Agency, NHS London Procurement Partnership and others) are
hand-curated and were last verified 31/07-31/08/2026. They drop off when their
end date passes, but an extension or a replacement framework would go unnoticed.
Lou: the page must not go out of date.

What it reads, per source shape:
  sbs.nhs.uk   "Framework Agreement Reference: SBS....." and the line under
               "What dates is the framework agreement active?"
               (parser shared with refresh_digital_frameworks.parse_sbs_page)
  gca.gov.uk   "Agreement number", "Start date", "End date"
               (parser shared with refresh_digital_frameworks.parse_agreement_header)
  lpp.nhs.uk   "Start:" and "End:" (dd-mm-yy)
Any other host, and any row with no end date, is reported NOT_CHECKED with the
reason. Nothing is guessed: a value counts only if it was read from the page.

Outcomes per row:
  OK            every value read matches the row
  CHANGED       a value read differs; the exact text read is printed
  GONE          the page answered 404/410
  UNPARSEABLE   the page loaded but the expected wording was not there
  UNREACHABLE   network error, timeout, or the site's own outage page
  NOT_CHECKED   no parser for this source, or nothing dated to compare

Usage:
  python3 scripts/check_other_body_frameworks.py           check; exit 1 if any
                                                           CHANGED/GONE/UNPARSEABLE
  python3 scripts/check_other_body_frameworks.py --apply   also write the values
                                                           read into CHANGED rows
                                                           (run only in a begin.sh
                                                           clone, then verify.py and
                                                           land.sh)
  --report FILE   write the findings as markdown (the workflow puts this in an issue)

Read-only by default. Stdlib only.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refresh_digital_frameworks as rdf  # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "framework-directory-extra.json")
UA = rdf.UA
TIMEOUT = 30
PROBLEMS = ("CHANGED", "GONE", "UNPARSEABLE")


class Gone(Exception):
    pass


def fetch(url, timeout=TIMEOUT, retries=1):
    """Decoded page text. 404/410 raise Gone; other failures retry once, then raise."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8-sig", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                raise Gone("HTTP %d" % e.code)
            last = e
        except Exception as e:  # noqa: BLE001 - report and retry
            last = e
        if attempt < retries:
            time.sleep(3)
    raise RuntimeError(str(last))


# ------------------------------------------------------------------ dates

def stored_date(s):
    """Leading date of a stored value -> ISO. '11 Nov 2033 (open framework ...)' ->
    '2033-11-11'. None when the value is not a plain date ('ongoing ...')."""
    if not s:
        return None
    m = re.match(r"\s*(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})", s)
    if not m:
        return None
    try:
        return dt.datetime.strptime("%s %s %s" % m.groups(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def display_date(iso):
    """'2027-08-01' -> '01 Aug 2027', the format the stored rows use."""
    return dt.date.fromisoformat(iso).strftime("%d %b %Y")


def short_uk_date(s):
    """LPP's '30-06-27' -> '2027-06-30'."""
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{2})", (s or "").strip())
    return "20%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else None


# ------------------------------------------------------------------ page parsers
# Each returns {"reference", "starts", "ends", "text"}: ISO dates, None for
# anything the page did not state, and "text" = the exact wording the values
# came from. A parser raises ValueError when the page lacks its expected wording.

def parse_sbs(page_html):
    p = rdf.parse_sbs_page(page_html)
    if not p["ends"]:
        raise ValueError("no 'What dates is the framework agreement active?' line")
    ref_txt = "Framework Agreement Reference: %s" % p["reference"] if p["reference"] else ""
    return {"reference": p["reference"], "starts": p["starts"], "ends": p["ends"],
            "text": "; ".join(x for x in (ref_txt, "Active: " + p["dateLine"]) if x)}


def parse_gca(page_html):
    try:
        h = rdf.parse_agreement_header(page_html)
    except RuntimeError as e:
        # The outage page has the GCA title "Service unavailable"; that is not a
        # changed page, it is a page we could not read today.
        if "Service unavailable" in page_html:
            raise ConnectionError("GCA outage page (Service unavailable)")
        raise ValueError(str(e))
    if not h["end"]:
        raise ValueError("no 'End date' on the agreement page")
    return {"reference": h["reference"], "starts": h["start"], "ends": h["end"],
            "text": "Agreement number: %s; Start date: %s; End date: %s" % (
                h["reference"], rdf.meta_field(h["text"], "Start date"),
                rdf.meta_field(h["text"], "End date"))}


def parse_lpp(page_html):
    txt = rdf.text_of(page_html)
    s = rdf.meta_field(txt, "Start")
    e = rdf.meta_field(txt, "End")
    if not short_uk_date(e):
        raise ValueError("no 'End:' date in dd-mm-yy form")
    return {"reference": None, "starts": short_uk_date(s), "ends": short_uk_date(e),
            "text": "Start: %s; End: %s" % (s, e)}


PARSERS = {
    "www.sbs.nhs.uk": parse_sbs,
    "www.gca.gov.uk": parse_gca,
    "www.lpp.nhs.uk": parse_lpp,
}


# ------------------------------------------------------------------ compare

def compare(row, read):
    """List of (field, stored, read) that disagree. Only values the page stated
    are compared, so a page that omits the start date never 'changes' it."""
    diffs = []
    if read.get("reference") and read["reference"] != (row.get("reference") or ""):
        diffs.append(("reference", row.get("reference"), read["reference"]))
    for f in ("starts", "ends"):
        if read.get(f) and read[f] != stored_date(row.get(f)):
            diffs.append((f, row.get(f), display_date(read[f])))
    return diffs


def check_row(row, fetcher=None):
    fetcher = fetcher or fetch
    out = {"name": row.get("name"), "url": row.get("url"), "reference": row.get("reference"),
           "status": None, "detail": "", "diffs": [], "read": None}
    host = urllib.parse.urlparse(row.get("url") or "").netloc.lower()
    parser = PARSERS.get(host)
    if not stored_date(row.get("ends")):
        out.update(status="NOT_CHECKED", detail="row has no end date to compare")
        return out
    if not parser:
        out.update(status="NOT_CHECKED", detail="no parser for %s" % (host or "this url"))
        return out
    try:
        page = fetcher(row["url"])
    except Gone as e:
        out.update(status="GONE", detail=str(e))
        return out
    except Exception as e:  # noqa: BLE001
        out.update(status="UNREACHABLE", detail=str(e)[:200])
        return out
    try:
        read = parser(page)
    except ConnectionError as e:
        out.update(status="UNREACHABLE", detail=str(e))
        return out
    except ValueError as e:
        out.update(status="UNPARSEABLE", detail=str(e))
        return out
    out["read"] = read
    out["diffs"] = compare(row, read)
    out["status"] = "CHANGED" if out["diffs"] else "OK"
    out["detail"] = read["text"]
    return out


def apply_changes(doc, results, today):
    """Write values read into CHANGED rows. Keeps any note after a stored date,
    e.g. '(open framework - re-opens at years 3 and 5)'. Returns rows changed."""
    by_url = {r["url"]: r for r in results if r["status"] == "CHANGED"}
    n = 0
    for row in doc["otherBodies"]:
        r = by_url.get(row.get("url"))
        if not r:
            continue
        for field, old, new in r["diffs"]:
            if field == "reference":
                row["reference"] = new
            else:
                m = re.match(r"\s*\d{1,2} [A-Za-z]+ \d{4}(.*)$", old or "", re.S)
                row[field] = new + (m.group(1) if m else "")
        n += 1
    read = sum(1 for r in results if r["read"] is not None)
    doc["otherBodiesCheckedAt"] = ("%d of %d rows re-read at their source by scripts/check_other_body_frameworks.py, %s"
                                   % (read, len(results), dt.date.fromisoformat(today).strftime("%d/%m/%Y")))
    return n


def report_markdown(results, today):
    lines = ["Checked %s by `scripts/check_other_body_frameworks.py` against each row's own source page." % today, ""]
    for r in results:
        if r["status"] not in PROBLEMS:
            continue
        lines.append("### %s: %s" % (r["status"], r["name"]))
        lines.append("- Source: %s" % r["url"])
        lines.append("- Stored reference: %s" % r["reference"])
        for field, old, new in r["diffs"]:
            lines.append("- `%s`: stored **%s**, page says **%s**" % (field, old, new))
        lines.append("- Exact text read: \"%s\"" % r["detail"])
        lines.append("")
    lines += ["How to fix: in a `begin.sh` clone run `python3 scripts/check_other_body_frameworks.py --apply`,",
              "then `python3 verify.py` and `./land.sh \"Other-body frameworks re-read at source\" data/framework-directory-extra.json`.",
              "GONE or UNPARSEABLE rows are never auto-applied: open the source and replace or remove the row by hand (Hub rule 8)."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report")
    ap.add_argument("--data", default=DATA)
    a = ap.parse_args(argv)
    today = dt.date.today().isoformat()
    with open(a.data, encoding="utf-8") as f:
        doc = json.load(f)
    results = []
    for row in doc.get("otherBodies", []):
        r = check_row(row)
        results.append(r)
        print("%-12s %s | %s" % (r["status"], r["name"], r["detail"]))
        for field, old, new in r["diffs"]:
            print("             %s: stored %r, page says %r" % (field, old, new))
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\nSummary: " + ", ".join("%s %d" % kv for kv in sorted(counts.items())))
    for r in results:
        if r["status"] == "UNREACHABLE":
            print("::warning::Could not read %s today (%s); not compared." % (r["url"], r["detail"]))
    checkable = [r for r in results if r["status"] != "NOT_CHECKED"]
    if checkable and all(r["status"] == "UNREACHABLE" for r in checkable):
        print("Every source was unreachable: the check itself is not working.", file=sys.stderr)
        return 2
    problems = [r for r in results if r["status"] in PROBLEMS]
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write(report_markdown(results, today) if problems else "")
    if a.apply and any(r["status"] == "CHANGED" for r in results):
        n = apply_changes(doc, results, today)
        with open(a.data, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)  # the file's own format
        print("Applied values read to %d row(s) in %s" % (n, a.data))
    if problems:
        print("\n%d row(s) disagree with their source. Fix: see the report / --apply." % len(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
