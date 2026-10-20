#!/usr/bin/env python3
"""
refresh_digital_sources.py - build data/digital-sources.json (added 20/10/2026).

Digital-lane sources that are not procurement frameworks, each read from its owner's page
under the Open Government Licence (NHS England Content, terms and conditions section 8,
https://digital.nhs.uk/about-nhs-digital/terms-and-conditions):

  nhsApp  NHS App integrated live partners, partners currently integrating, and partners
          that plan to integrate (digital.nhs.uk). Organisation, product and the section
          the owner lists it under. Functionality text is not copied.
  dma     NHS England Digital Maturity Assessment 2024 and 2025 results data file
          (digital.nhs.uk): per-trust 2025 pillar scores (What Good Looks Like) and the
          per-ICB equivalent, read from the published data file (current version link
          taken from the report page).

  notAdded  Sources scoped in "Hub health tech intelligence gap" that were checked and
          not added, each with the reason read on the date it was checked.

RULES (binding)
  * Every fact is read at the named owner page in the run that writes it.
  * Failure to read a source never overwrites a good file with a worse one: that block is
    kept from the previous file and flagged; if nothing at all can be read, exit 1.
  * Attribution carried in the file: "Contains information from NHS England, licensed
    under the current version of the Open Government Licence".

  python3 scripts/refresh_digital_sources.py [--out PATH] [--today YYYY-MM-DD]
Stdlib only. Short timeout, one retry.
"""

import argparse
import html
import io
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "digital-sources.json")

NHSD = "https://digital.nhs.uk"
APP_BASE = NHSD + "/services/nhs-app/how-to-integrate-with-the-nhs-app/"
APP_PAGES = [
    ("live", APP_BASE + "nhs-app-integrated-partners-and-services/nhs-app-integrated-live-partners-and-services"),
    ("integrating", APP_BASE + "nhs-app-partners-and-services-currently-integrating"),
    ("planned", APP_BASE + "nhs-app-integrated-partners-and-services/partners-and-services-that-plan-to-be-integrated"),
]
DMA_REPORT = NHSD + "/data-and-information/digital-maturity-assessment-report-2024-and-2025-results/report"
TERMS = NHSD + "/about-nhs-digital/terms-and-conditions"
UA = "Mozilla/5.0 (compatible; msh-compare-data digital-sources; contact@elevateandthrive.uk)"
TIMEOUT = 40
LICENCE = ("Contains information from NHS England, licensed under the current version of the "
           "Open Government Licence (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).")
RULE = ("Every fact read at the named NHS England Digital page on verifiedOn. NHS App rows hold the "
        "organisation, product and the owner's section only. Digital Maturity Assessment scores are "
        "self-assessment scores as published by NHS England, not a ranking or a judgement.")

# Checked 20/10/2026 and not added. Reasons are what was read, not assumptions.
NOT_ADDED = [
    {"source": "AI Diagnostic Fund (NHS England)",
     "url": "https://transform.england.nhs.uk/ai-lab/ai-lab-programmes/ai-in-imaging/ai-diagnostic-fund",
     "reason": "Not added. The NHS England Transformation Directorate host (transform.england.nhs.uk) "
               "did not resolve from the build host on 20/10/2026, so the page was not read and no "
               "figure or network list is recorded. Search snippets disagree on the trust count and "
               "are not a source. Settled by reading the page when the host is reachable; a named "
               "list of networks and trusts is needed before anything is published."},
    {"source": "Digital social care records assured supplier list / DPS",
     "url": "https://transform.england.nhs.uk/key-tools-and-info/procurement-frameworks/dynamic-purchasing-system-dps-for-digital-social-care-record-solutions",
     "reason": "Not added. The NHS England DPS page host did not resolve on 20/10/2026. The older "
               "digitalsocialcare.co.uk address redirects to digitisingsocialcare.co.uk and on to a "
               "beta site whose root returned 404, so no current supplier list was found at a primary "
               "source. Settled by the owner publishing the current list at a stable address."},
    {"source": "SBRI Healthcare competitions",
     "url": "https://sbrihealthcare.co.uk/competitions/overview?cat=open-competitions",
     "reason": "Not added. The page is readable, but the site's terms and conditions "
               "(https://sbrihealthcare.co.uk/policies/terms-conditions) grant no reuse licence and its "
               "robots.txt carries content-signal reservations of rights, so competition details are "
               "linked to, not copied. Link out only."},
    {"source": "MHRA device registration (PARD)",
     "url": "https://pard.mhra.gov.uk/",
     "reason": "Not added. PARD is an interactive search application (page content is loaded by script) "
               "with no published bulk download, feed or reuse statement found; MHRA's guidance says "
               "the register is searched one manufacturer at a time. A systematic extract cannot be "
               "built authoritatively. Link out only."},
]


def fetch(url, timeout=TIMEOUT, retries=1, binary=False):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return b if binary else b.decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < retries:
                time.sleep(2)
    raise RuntimeError("fetch failed %s: %s" % (url, last))


def txt(s):
    s = re.sub(r"<(script|style)[\s\S]*?</\1>", "", s)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


# ------------------------------------------------------------------ NHS App

def parse_app_tables(page):
    """[(section heading, [first two cell texts])] for every table row under an h3 heading."""
    rows, head = [], None
    for m in re.finditer(r"<h3[^>]*>([\s\S]*?)</h3>|<table[\s\S]*?</table>", page):
        if m.group(0).startswith("<h3"):
            head = txt(m.group(1)) or head
            continue
        for tr in re.findall(r"<tr[\s\S]*?</tr>", m.group(0)):
            cells = [txt(c) for c in re.findall(r"<t[hd][^>]*>([\s\S]*?)</t[hd]>", tr)]
            if cells:
                rows.append((head, cells))
    return rows


def app_rows(page, stage):
    out = []
    for head, cells in parse_app_tables(page):
        org = cells[0].rstrip("*").strip()
        if org.lower() in ("organisation", "product", "n/a", "") or org.startswith("None currently"):
            continue
        if len(cells) >= 3:
            product = cells[1] or None
        else:
            product = None  # two-column notification tables list organisation and functionality only
        if len(cells) == 2 and cells[1].lower() == "functionality":
            continue
        out.append({"stage": stage, "section": (head or "").strip(), "organisation": org,
                    "product": product})
    return out


def build_app(fetcher, today):
    rows, pages, nv = [], [], []
    for stage, url in APP_PAGES:
        page = fetcher(url)
        r = app_rows(page, stage)
        edited = re.search(r"Last edited:\s*(\d{1,2} \w+ \d{4})", txt(page))
        pages.append({"stage": stage, "url": url, "pageLastEdited": edited.group(1) if edited else None,
                      "rows": len(r)})
        if not r:
            raise RuntimeError("NHS App page parsed empty (layout changed?): " + url)
        rows.extend(r)
    nv.append("The owner states these lists are not an extensive directory of live services and are "
              "not designed for patients; coverage is uneven. A company's absence is not evidence "
              "that it has no NHS App integration.")
    return {"licence": LICENCE, "pages": pages, "rows": rows, "notVerified": nv}


# ------------------------------------------------------------------ DMA

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _col(ref):
    n = 0
    for c in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(c) - 64
    return n - 1


def read_xlsx_sheets(blob):
    """{sheet name: [row dict {col index: text}]} using only the standard library."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sst = []
    for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
        sst.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    out = {}
    for s in wb.find("m:sheets", NS):
        target = rels[s.get("{%s}id" % NS["r"])].lstrip("/")
        path = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(path)).iter("{%s}row" % NS["m"]):
            vals = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                if v is None:
                    continue
                vals[_col(c.get("r"))] = sst[int(v.text)] if c.get("t") == "s" else v.text
            if vals:
                rows.append(vals)
        out[s.get("name")] = rows
    return out


PILLARS = ["Well Led", "Ensure Smart Foundations", "Safe Practice", "Support Workforce",
           "Empower People", "Improve Care", "Healthy Populations"]


def num(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def parse_dma(blob):
    sheets = read_xlsx_sheets(blob)
    sc = next((k for k in sheets if k.startswith("SC") and "Pillar" in k), None)
    icb = next((k for k in sheets if k.startswith("ICB") and "Pillar" in k and "PC" not in k), None)
    if not sc or not icb:
        raise RuntimeError("DMA data file: expected sheets not found: %s" % list(sheets))

    def table(name, key_cols):
        rows = sheets[name]
        hi = next(i for i, r in enumerate(rows) if r.get(1) == "Region")
        head = rows[hi]
        out = []
        for r in rows[hi + 1:]:
            if not r.get(2):
                continue
            rec = {}
            for ci, label in head.items():
                if ci == 1:
                    rec["region"] = r.get(ci)
                elif label == "ICS":
                    rec["ics"] = r.get(ci)
                elif label == "Provider":
                    rec["provider"] = r.get(ci)
                elif label == "Care Setting":
                    rec["careSetting"] = r.get(ci)
                elif label in PILLARS:
                    rec.setdefault("pillars", {})[label] = num(r.get(ci))
            out.append(rec)
        return out

    providers = table(sc, None)
    icbs = table(icb, None)
    return providers, icbs


def build_dma(fetcher, today):
    page = fetcher(DMA_REPORT)
    links = re.findall(r'href="([^"]*digital-maturity-assessment-results-data-file[^"]*\.xlsx)"', page)
    if not links:
        raise RuntimeError("DMA data file link not found on " + DMA_REPORT)
    link = sorted(set(links))[-1]
    url = link if link.startswith("http") else NHSD + link
    blob = fetcher(url, binary=True)
    providers, icbs = parse_dma(blob)
    if len(providers) < 150 or len(icbs) < 30:
        raise RuntimeError("DMA data file parsed short: %d providers, %d ICBs" % (len(providers), len(icbs)))
    published = re.search(r"Date Published:\s*(\d{1,2} \w+ \d{4})", txt(fetcher(
        NHSD + "/data-and-information/digital-maturity-assessment-report-2024-and-2025-results")))
    return {
        "licence": LICENCE,
        "reportUrl": DMA_REPORT,
        "dataFileUrl": url,
        "published": published.group(1) if published else None,
        "scale": "1 to 5 maturity score per What Good Looks Like pillar, as published",
        "providers": providers,
        "icbs": icbs,
        "notVerified": [
            "Scores are NHS England's published self-assessment results, not a ranking or a judgement "
            "(the owner's own wording); 2025 values include domains marked non-comparable with 2024.",
            "Provider names are as published and are not alias-resolved to Hub trust records here.",
        ],
    }


# ------------------------------------------------------------------ main

def build(fetcher=fetch, today="2026-10-20", previous=None):
    previous = previous or {}
    doc = {"rule": RULE, "source": "digital.nhs.uk (NHS England Digital) pages and data file; Open Government Licence",
           "termsUrl": TERMS, "generated": today, "dataAsOf": today}
    problems = []
    for key, fn in (("nhsApp", build_app), ("dma", build_dma)):
        try:
            block = fn(fetcher, today)
            block["verifiedOn"] = today
            doc[key] = block
        except Exception as e:  # noqa: BLE001
            problems.append("%s: %s" % (key, e))
            old = previous.get(key)
            if old:
                old["staleNote"] = ("Source could not be read on %s (%s); this block is last week's, "
                                    "verified %s." % (today, e, old.get("verifiedOn")))
                doc[key] = old
    if len(problems) == 2:
        # Nothing could be read this run (e.g. GitHub's runners are blocked by digital.nhs.uk):
        # keep the file exactly as it is rather than rewriting last week's blocks with a flag.
        raise RuntimeError("; ".join(problems))
    doc["notAdded"] = [dict(x, checkedOn="2026-10-20") for x in NOT_ADDED]
    if problems:
        # A single string, not a list: a list would be a collection that the landing lane's
        # no-loss check sees shrink on the next clean run and refuses.
        doc["readProblems"] = "; ".join(problems)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--today", default=time.strftime("%Y-%m-%d"))
    a = ap.parse_args(argv)
    prev = None
    if os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as f:
            prev = json.load(f)
    try:
        doc = build(today=a.today, previous=prev)
    except Exception as e:  # noqa: BLE001
        print("refresh_digital_sources: FAILED, file not written: %s" % e, file=sys.stderr)
        return 1
    if prev and prev.get("_notice"):
        doc = {"_notice": prev["_notice"], **doc}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    if "nhsApp" in doc:
        print("NHS App rows:", len(doc["nhsApp"]["rows"]), [p["rows"] for p in doc["nhsApp"]["pages"]])
    if "dma" in doc:
        print("DMA providers:", len(doc["dma"]["providers"]), "ICBs:", len(doc["dma"]["icbs"]))
    if doc.get("readProblems"):
        print("PROBLEM:", doc["readProblems"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
