#!/usr/bin/env python3
"""Capture the NHSBSA Drug Tariff Part VIIIA (medicines basic prices) as compact JSON.

WHY THIS EXISTS
---------------
Part IX (appliances) is already captured by refresh_drug_tariff_part_ix.py into
data/drug-tariff-part-ix.json. Part VIIIA is its medicines counterpart: the basic
price NHS dispensing contractors are reimbursed for each generic medicine pack,
with its Drug Tariff category (A, C, M, and a small H group). For a medicines
rep the category and price are the commercial context of every generic line in
their therapy area, and Category M prices move quarterly. Same publisher, same
page family, same monthly cadence, so it mirrors Part IX's structure and runs in
the same workflow, .github/workflows/drug-tariff.yml.

SOURCE, AND WHY THE LINK IS READ, NOT BUILT
-------------------------------------------
Index page (every month back to 2021, Excel and CSV):
  https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-viii
Unlike Part IX, the VIIIA file names are irregular. Read off that page on
29/09/2026: "Part VIIIA Sep 26.csv", "Part VIIIA Oct 2026.csv",
"Part VIIIA Jul 26.xls.csv", "Part VIIIA April 2026.csv",
"Part VIIIA December 20251.xls_0.csv", and a March 2026 file filed under a
2026-08 folder. A URL constructed from a pattern would miss most of them, so
this script parses the index page, reads the effective month out of each link's
own file name, and takes the edition in force for the requested month (default:
the current month, the same edition Part IX publishes). Needs a browser
User-Agent; a bare client gets 403.

The CSV's first line names the month ("September Drug Tariff Part VIIIA"). It is
checked against the month read from the link, and a mismatch refuses to write:
a mislabelled upload must not publish one month's prices as another's.

SCHEMA
------
Array-of-arrays like Part IX (3,500 rows). Columns kept:
  medicine   NHSBSA's VMP description, verbatim
  packSize   pack quantity, verbatim
  unit       unit of the pack (tablet, capsule, gram ...), verbatim
  category   "A", "C", "M" or "H" (from "Part VIIIA Category X")
  price      basic price in PENCE, integer, as published (3750 is GBP 37.50)
  vmpSnomed  dm+d VMP code, kept (unlike Part IX) because it is the join key to
             prescribing data; VMPP code dropped.

BNF CODES, ADDED 29/09/2026 (speciality panels phase 2)
-------------------------------------------------------
Part VIIIA carries no BNF code and no therapy column, so on its own a speciality can
only find its lines by matching the medicine name, which is the approach that hid Ego's
QV range from the Part IX dermatology slice (commit c6b861e). The panel builder
classifies Part IX by NHSBSA's own BNF code instead, and Part VIIIA is given the same
footing here: `bnfBySnomed` maps each line's VMP SNOMED code to the 15-character BNF
presentation code NHSBSA itself attaches to that SNOMED code in the English
Prescribing Dataset with SNOMED (the same NHSBSA source as data/gp-prescribing/),
read over the latest three published months. Where one SNOMED code carries two BNF
codes, the one with the most items wins. A line whose VMP was not prescribed in
primary care in those months has no entry and is counted in `bnfUnmapped`; the
builder never guesses a code for it. The rows and schema are unchanged, so every
existing reader and the verify.py gate see the same file. If the dataset cannot be
reached, the previous file's map is carried forward for the codes it already held
and the run says so in `bnfMapNote`, rather than publishing the tariff without it.

Run: python3 scripts/refresh_drug_tariff_part_viiia.py [--out PATH] [--month YYYY-MM]
"""
import argparse
import csv
import datetime
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
BASE = "https://www.nhsbsa.nhs.uk"
INDEX = BASE + "/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-viii"
SCHEMA = ["medicine", "packSize", "unit", "category", "price", "vmpSnomed"]
CATEGORIES = ("A", "C", "H", "M")

FULL_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
               "august", "september", "october", "november", "december"]
MONTHS = {}
for i, name in enumerate(FULL_MONTHS, 1):
    MONTHS[name] = i
    MONTHS[name[:3]] = i
MONTHS["sept"] = 9

LINK_RE = re.compile(r'href="([^"]*Part(?:%20|\s|_)VIIIA[^"]*?\.csv)"', re.I)
NAME_RE = re.compile(r"VIIIA\s+([A-Za-z]+)\s+(\d{2,5})", re.I)
CAT_RE = re.compile(r"Category\s+([A-Z])\b")


def http_get(url, timeout=60, retries=3):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError:
            if attempt == retries:
                raise
        except Exception:
            if attempt == retries:
                raise
        time.sleep(3 * attempt)


def month_of_link(href):
    """(year, month) the file is FOR, read from its own name, or None.

    Handles every form seen on the index: "Sep 26", "Oct 2026", "Sept 2025",
    "April 2026", "Jul 26.xls", and the typo "December 20251" (first four
    digits taken when the year has five)."""
    name = urllib.parse.unquote(href.rsplit("/", 1)[-1])
    m = NAME_RE.search(name)
    if not m:
        return None
    mon = MONTHS.get(m.group(1).lower())
    digits = m.group(2)
    if mon is None:
        return None
    if len(digits) == 2:
        year = 2000 + int(digits)
    elif len(digits) >= 4:
        year = int(digits[:4])
    else:
        return None
    return year, mon


def editions(index_html):
    """{(year, month): absolute CSV url}. Where a month appears twice the later
    upload folder wins (NHSBSA re-uploads corrections under a newer folder)."""
    out = {}
    for href in LINK_RE.findall(index_html):
        href = html.unescape(href)
        ym = month_of_link(href)
        if not ym:
            continue
        url = href if href.startswith("http") else BASE + href
        folder = re.search(r"/files/(\d{4}-\d{2})/", url)
        key = folder.group(1) if folder else ""
        prev = out.get(ym)
        if prev is None or key >= prev[0]:
            out[ym] = (key, url)
    return {ym: v[1] for ym, v in out.items()}


def pick(eds, year, month):
    """The edition in force for (year, month): that month if published, else the
    latest earlier one. None if nothing at or before it."""
    eligible = [ym for ym in eds if ym <= (year, month)]
    return max(eligible) if eligible else None


def parse_csv(text, year, month):
    """(rows, problems). Header row is located by its 'Medicine' first cell, so
    the two title lines above it can change without breaking the parse."""
    lines = list(csv.reader(io.StringIO(text)))
    title = (lines[0][0] if lines and lines[0] else "").strip()
    problems = []
    month_name = FULL_MONTHS[month - 1]
    if month_name not in title.lower():
        problems.append("title line %r does not name %s" % (title, month_name.title()))
    hdr_i = next((i for i, r in enumerate(lines) if r and r[0].strip().lower() == "medicine"), None)
    if hdr_i is None:
        return [], problems + ["no 'Medicine' header row"]
    hdr = [h.strip().lower() for h in lines[hdr_i]]
    try:
        i_med, i_pack = hdr.index("medicine"), hdr.index("pack size")
        i_vmp = hdr.index("vmp snomed code")
        i_cat, i_price = hdr.index("drug tariff category"), hdr.index("basic price")
    except ValueError as exc:
        return [], problems + ["header drifted: %s (%s)" % (lines[hdr_i], exc)]
    i_unit = i_pack + 1
    rows = []
    for r in lines[hdr_i + 1:]:
        if not r or not any(c.strip() for c in r):
            continue
        med = r[i_med].strip()
        cm = CAT_RE.search(r[i_cat]) if len(r) > i_cat else None
        price = r[i_price].strip().replace(",", "") if len(r) > i_price else ""
        if not med or not cm or not price.isdigit():
            problems.append("unparsed row: %r" % (r,))
            continue
        rows.append([med, r[i_pack].strip(), r[i_unit].strip() if len(r) > i_unit else "",
                     cm.group(1), int(price), r[i_vmp].strip()])
    return rows, problems


BNF_MONTHS = 3
BNF_CHUNK = 400


def bnf_map(codes, run_sql=None, resources=None, months=BNF_MONTHS):
    """{vmpSnomed: bnf15} from NHSBSA EPD with SNOMED, latest `months` months.

    run_sql(table, query) -> rows of dicts, and resources() -> [(YYYYMM, table)],
    are injectable so the tests stay offline.
    """
    if run_sql is None or resources is None:
        import refresh_gp_prescribing as gp  # same NHSBSA datastore helpers
        run_sql = run_sql or gp.sql
        resources = resources or gp.resources
    tables = [t for _p, t in resources()][-months:]
    codes = sorted({c for c in codes if c and c.isdigit()})
    best = {}
    for table in tables:
        for i in range(0, len(codes), BNF_CHUNK):
            chunk = codes[i:i + BNF_CHUNK]
            q = ("SELECT SNOMED_CODE AS s, BNF_PRESENTATION_CODE AS b, SUM(ITEMS) AS i "
                 "FROM `%s` WHERE SNOMED_CODE IN (%s) GROUP BY 1, 2"
                 % (table, ",".join("'%s'" % c for c in chunk)))
            for r in run_sql(table, q):
                s, b = str(r.get("s") or "").strip(), str(r.get("b") or "").strip()
                try:
                    n = float(r.get("i") or 0)
                except (TypeError, ValueError):
                    n = 0.0
                if not s or not b:
                    continue
                cur = best.setdefault(s, {})
                cur[b] = cur.get(b, 0.0) + n
    out = {}
    for s, by_b in best.items():
        out[s] = sorted(by_b.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return out, tables


def attach_bnf(doc, prior=None, mapper=bnf_map):
    """Add bnfBySnomed / bnfUnmapped / bnfMapNote to a built doc, in place."""
    codes = [r[5] for r in doc["rows"]]
    try:
        m, tables = mapper(codes)
        doc["bnfMapNote"] = ("BNF presentation codes read from NHSBSA EPD with SNOMED, "
                             "resources %s." % ", ".join(tables))
    except Exception as exc:  # noqa: BLE001 - reported in the file and on stdout
        old = (prior or {}).get("bnfBySnomed") or {}
        m = {c: old[c] for c in codes if c in old}
        doc["bnfMapNote"] = ("NHSBSA EPD with SNOMED could not be read this run (%s); "
                             "the previous run's codes are carried forward for the %d "
                             "lines they cover." % (str(exc)[:120], len(m)))
    doc["bnfBySnomed"] = {c: m[c] for c in sorted(set(codes)) if c in m}
    doc["bnfUnmapped"] = sum(1 for c in codes if c not in m)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/drug-tariff-part-viiia.json")
    ap.add_argument("--month", default=None, help="Effective month YYYY-MM, default: current")
    args = ap.parse_args(argv)

    today = datetime.date.today()
    ty, tm = (int(x) for x in args.month.split("-")) if args.month else (today.year, today.month)

    page = http_get(INDEX).decode("utf-8", "replace")
    eds = editions(page)
    if not eds:
        print("No Part VIIIA CSV links found on %s. NHSBSA may have changed the page; "
              "check it by hand. Nothing written." % INDEX)
        return 1
    chosen = pick(eds, ty, tm)
    if chosen is None:
        print("No Part VIIIA edition at or before %04d-%02d. Nothing written." % (ty, tm))
        return 1
    ey, em = chosen
    url = eds[chosen]
    text = http_get(url).decode("utf-8-sig", "replace")
    rows, problems = parse_csv(text, ey, em)
    if problems:
        print("Refusing to write, %d problem(s) parsing %s:" % (len(problems), url))
        for p in problems[:10]:
            print("  " + p)
        return 1

    cats = {c: 0 for c in CATEGORIES}
    for r in rows:
        cats[r[3]] = cats.get(r[3], 0) + 1
    latest = max(eds)
    doc = {
        "dataAsOf": today.isoformat(),
        "effectiveMonth": "%04d-%02d" % (ey, em),
        "latestPublishedMonth": "%04d-%02d" % latest,
        "source": url,
        "sourcePage": INDEX,
        "schema": SCHEMA,
        "rowCount": len(rows),
        "categoryCounts": cats,
        "note": "Every Part VIIIA line NHSBSA publishes for this effective month, verbatim. "
                "price is the basic price in pence (3750 is GBP 37.50) at publication. "
                "category is the Drug Tariff category letter. latestPublishedMonth is the "
                "newest edition on the index, which NHSBSA publishes ahead of its effective "
                "month. Refreshed daily by .github/workflows/drug-tariff.yml, not hand-rebuilt.",
        "rows": rows,
    }
    prior = None
    try:
        with open(args.out, encoding="utf-8") as f:
            prior = json.load(f)
    except (OSError, ValueError):
        pass
    attach_bnf(doc, prior)
    print(doc["bnfMapNote"], "%d of %d lines have a BNF code."
          % (len(rows) - doc["bnfUnmapped"], len(rows)))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
    print("Wrote %s: %d rows, effective %04d-%02d (latest published %04d-%02d), %s, from %s"
          % (args.out, len(rows), ey, em, latest[0], latest[1], cats, url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
