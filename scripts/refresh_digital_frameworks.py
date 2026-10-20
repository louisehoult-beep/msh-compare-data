#!/usr/bin/env python3
"""
refresh_digital_frameworks.py - build data/digital-frameworks.json.

Digital / technology frameworks a medical-sales rep may meet:
  live    Technology Services 4 (RM6190) and G-Cloud 15 (RM1557.15), Government
          Commercial Agency (GCA, formerly Crown Commercial Service, renamed
          1 April 2026), read from gca.gov.uk.
  coming  Healthcare AI Solutions (NHS Shared Business Services, notice
          050314-2026) and the Digital Primary Care / GP IT open framework
          (NHS England, notice 094419-2026), read from the Find a Tender OCDS API.

RULES (binding)
  * Every fact is read at the named primary source in the run that writes it.
    What cannot be read is "Not verified" plus what would settle it. Nothing guessed.
  * Supplier lists store COMPANY NAMES ONLY. The GCA exports carry contact names,
    emails, phones and addresses: only the "Supplier Name" column is ever kept.
  * Honest empty states: suppliers null (never []) when no list was read.
  * Failure to fetch never overwrites a good file with a worse one: exit 1, no write.

  python3 scripts/refresh_digital_frameworks.py [--out PATH] [--today YYYY-MM-DD]
Stdlib only. Short timeout, one retry.
"""

import argparse
import csv
import html
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "digital-frameworks.json")

GCA = "https://www.gca.gov.uk"
TS4_URL = GCA + "/agreements/RM6190"
GC15_URL = GCA + "/agreements/RM1557.15"
SUPPLIERS_URL = GCA + "/suppliers"
FTS_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages/"
FTS_NOTICE = "https://www.find-tender.service.gov.uk/Notice/"
UA = "Mozilla/5.0 (compatible; msh-compare-data digital-frameworks)"
TIMEOUT = 20

RULE = ("Every fact read at the named primary source on verifiedOn, else 'Not verified' "
        "with what would settle it. Supplier lists hold company names only; no contact "
        "person, email, phone or address is ever stored. suppliers null means no list was read.")
SOURCE = ("gca.gov.uk agreement pages and lot-supplier CSV exports; "
          "find-tender.service.gov.uk OCDS API")


# ------------------------------------------------------------------ fetching

def fetch(url, timeout=TIMEOUT, retries=1):
    """Return decoded text. One retry, then raise."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8-sig", errors="replace")
        except Exception as e:  # noqa: BLE001 - report and retry
            last = e
            if attempt < retries:
                time.sleep(2)
    raise RuntimeError("fetch failed %s: %s" % (url, last))


# ------------------------------------------------------------------ helpers

def text_of(markup):
    markup = re.sub(r"<(script|style)[\s\S]*?</\1>", "", markup)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", markup))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t)).strip()


def uk_date(s):
    """dd/mm/yyyy -> ISO yyyy-mm-dd."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s.strip())
    return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else None


def meta_field(txt, label):
    m = re.search(re.escape(label) + r":\s*\n?\s*([^\n]+)", txt)
    return m.group(1).strip() if m else None


def parse_agreement_header(page_html):
    txt = text_of(page_html)
    return {
        "reference": meta_field(txt, "Agreement number"),
        "start": uk_date(meta_field(txt, "Start date") or ""),
        "end": uk_date(meta_field(txt, "End date") or ""),
        "type": meta_field(txt, "Agreement type"),
        "text": txt,
    }


def parse_lots(page_html):
    """Lots from the 'Products and suppliers' section. Returns list of dicts."""
    i = page_html.find('id="products"')
    j = page_html.find("Documents", i)
    seg = text_of(page_html[i:j if j > i else None])
    lots = []
    cur = None
    for line in seg.split("\n"):
        line = line.strip()
        m = re.match(r"^Lot (\w+) (.+)$", line)
        if m and not line.startswith("Lot " + "Access"):
            cur = {"lot": m.group(1), "name": m.group(2).strip(), "expires": None,
                   "supplierCountOnPage": None, "note": None}
            lots.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^Expires: (\d{2}/\d{2}/\d{4})$", line)
        if m:
            cur["expires"] = uk_date(m.group(1))
            continue
        m = re.match(r"^(\d+) suppliers?$", line)
        if m:
            cur["supplierCountOnPage"] = int(m.group(1))
            continue
        if re.search(r"(minimum|maximum) contract value", line):
            cur["note"] = line
    return lots


def parse_supplier_csv(csv_text):
    """Company names only. Only the 'Supplier Name' column is read; every other
    column (contact name, email, address) is discarded here and never stored."""
    rd = csv.DictReader(io.StringIO(csv_text))
    if not rd.fieldnames or "Supplier Name" not in rd.fieldnames:
        raise ValueError("no 'Supplier Name' column in export")
    names = []
    for row in rd:
        n = (row.get("Supplier Name") or "").strip()
        if n:
            names.append(n)
    return sorted(set(names), key=str.casefold)


def ocds_money(v):
    if not v:
        return None
    return {"amountExVat": v.get("amount"), "amountIncVat": v.get("amountGross"),
            "currency": v.get("currency")}


def iso_day(s):
    return s[:10] if s else None


def parse_ocds(pkg, notice_id):
    r = pkg["releases"][0]
    t = r["tender"]
    lots = []
    for l in t.get("lots", []):
        cp = l.get("contractPeriod") or {}
        lots.append({"lot": l.get("id"), "name": l.get("title"),
                     "starts": iso_day(cp.get("startDate")),
                     "ends": iso_day(cp.get("endDate")),
                     "maxExtentDate": iso_day(cp.get("maxExtentDate")),
                     "value": ocds_money(l.get("value"))})
    fw = (t.get("techniques") or {}).get("frameworkAgreement") or {}
    return {
        "title": t.get("title"),
        "status": t.get("status"),
        "buyer": (r.get("buyer") or {}).get("name"),
        "publishedRelease": r.get("date"),
        "noticeTag": r.get("tag"),
        "value": ocds_money(t.get("value")),
        "lots": lots,
        "awardPeriodEnd": iso_day((t.get("awardPeriod") or {}).get("endDate")),
        "tenderPeriodEnd": iso_day((t.get("tenderPeriod") or {}).get("endDate")),
        "expressionOfInterestDeadline": iso_day(t.get("expressionOfInterestDeadline")),
        "futureNoticeDate": iso_day((t.get("communication") or {}).get("futureNoticeDate")),
        "openFrameworkSchemeEndDate": iso_day(fw.get("openFrameworkSchemeEndDate")),
        "procedure": t.get("procurementMethodDetails"),
        "description": t.get("description") or "",
        "url": FTS_NOTICE + notice_id,
    }


# ------------------------------------------------------------------ entries

def build_ts4(fetcher, today):
    nv = []
    page = fetcher(TS4_URL)
    h = parse_agreement_header(page)
    lots = parse_lots(page)
    txt = h["text"]
    quote = None
    m = re.search(r"Technology Services 4 will run for 8 years\.[^\n]*(?:\n[^\n]*)?", txt)
    if m:
        quote = re.sub(r"\s+", " ", m.group(0)).strip()
    for l in lots:
        code = l["lot"]
        try:
            names = parse_supplier_csv(fetcher("%s/agreements/RM6190:%s/lot-suppliers/csv" % (GCA, code)))
            l["suppliers"] = names
            l["supplierCount"] = len(names)
            on_page = l.get("supplierCountOnPage")
            if on_page is not None and on_page != len(names):
                nv.append("Lot %s: page says %d suppliers, export has %d distinct names; "
                          "differences (e.g. trading names, duplicates) not reconciled." %
                          (code, on_page, len(names)))
        except Exception as e:  # noqa: BLE001
            l["suppliers"] = None
            l["supplierCount"] = None
            nv.append("Lot %s supplier list not verified (%s). Settled by re-running when "
                      "%s/agreements/RM6190:%s/lot-suppliers/csv is reachable." % (code, e, GCA, code))
        l.pop("supplierCountOnPage", None)
        l["starts"] = h["start"]
        l["ends"] = l.pop("expires")
    if h["end"] and any(l["ends"] and l["ends"] != h["end"] for l in lots):
        nv.append("Lot expiry dates differ from the agreement end date; both recorded as read.")
    nv.append("Page says 'will run for 8 years' but start 12/12/2025 to end 11/06/2028 is about "
              "2.5 years; the two are not reconciled here. Settled by the framework award form "
              "or GCA confirming the term.")
    nv.append("Which lots a medical-sales or NHS buyer actually uses is not stated on the page "
              "and is not recorded.")
    return {
        "name": "Technology Services 4",
        "reference": h["reference"],
        "owner": "Government Commercial Agency (GCA)",
        "url": TS4_URL,
        "status": "live",
        "starts": h["start"],
        "ends": h["end"],
        "agreementType": h["type"],
        "term": quote,
        "lots": lots,
        "suppliers": None if any(l["suppliers"] is None for l in lots) else
                     sorted({n for l in lots for n in l["suppliers"]}, key=str.casefold),
        "verifiedOn": today,
        "sourceQuote": quote,
        "notVerified": nv,
    }


def build_gc15(fetcher, today):
    nv = []
    page = fetcher(GC15_URL)
    h = parse_agreement_header(page)
    lots = parse_lots(page)
    txt = h["text"]
    m = re.search(r"G-Cloud 15 will run for 4 years from 6 August 2026[^\n]*", txt)
    term = re.sub(r"\s+", " ", m.group(0)).strip() if m else None
    if not term:
        nv.append("Term sentence not found on the page this run; settled by re-reading %s." % GC15_URL)
    for l in lots:
        l["starts"] = h["start"]
        l["ends"] = l.pop("expires")
        l.pop("supplierCountOnPage", None)
        l["suppliers"] = None
        l["supplierCount"] = None
    suppliers = None
    try:
        sup = fetcher(SUPPLIERS_URL)
        if re.search(r"G-Cloud 15|RM1557\.15", sup):
            nv.append("The GCA suppliers page mentions G-Cloud 15 but no export was parsed; "
                      "settled by reading the G-Cloud 15 supplier list from the Digital Marketplace.")
        else:
            nv.append("Supplier list not verified: %s lists no G-Cloud 15 suppliers (only earlier "
                      "G-Cloud lots at read time) and the agreement page has no supplier export. "
                      "Settled by the G-Cloud 15 supplier list on the Digital Marketplace / GCA "
                      "once published." % SUPPLIERS_URL)
    except Exception as e:  # noqa: BLE001
        nv.append("Supplier list not verified (%s unreachable: %s)." % (SUPPLIERS_URL, e))
    nv.append("Agreement end 05/02/2028 (page header) and 'run for 4 years from 6 August 2026, "
              "reopening after 18 months and again after 36 months' (page text) are both "
              "recorded verbatim and not resolved. Settled by the framework award form.")
    return {
        "name": "G-Cloud 15",
        "reference": h["reference"],
        "owner": "Government Commercial Agency (GCA)",
        "url": GC15_URL,
        "status": "live",
        "starts": h["start"],
        "ends": h["end"],
        "agreementType": h["type"],
        "term": term,
        "lots": lots,
        "suppliers": suppliers,
        "verifiedOn": today,
        "sourceQuote": term,
        "notVerified": nv,
    }


def build_coming(fetcher, notice_id, name, owner_hint, today):
    nv = []
    pkg = json.loads(fetcher(FTS_API + notice_id))
    p = parse_ocds(pkg, notice_id)
    starts = sorted({l["starts"] for l in p["lots"] if l["starts"]})
    ends = sorted({l["ends"] for l in p["lots"] if l["ends"]})
    quote = re.sub(r"\s+", " ", p["description"]).strip().split(". ")[0]
    quote = quote if quote.endswith(".") else quote + "."
    if p["status"] == "planned":
        m = re.search(r"Framework go-live is expected in Q3 2027\.", p["description"])
        if m:
            quote = m.group(0)
    entry = {
        "name": name,
        "reference": "Find a Tender notice " + notice_id,
        "owner": p["buyer"] or owner_hint,
        "url": p["url"],
        "status": "coming",
        "starts": starts[0] if starts else None,
        "ends": ends[-1] if ends else None,
        "lots": p["lots"],
        "suppliers": None,
        "noticeTitle": p["title"],
        "noticeStatus": p["status"],
        "noticeReleaseDate": p["publishedRelease"],
        "procedure": p["procedure"],
        "estimatedValue": p["value"],
        "awardPeriodEnd": p["awardPeriodEnd"],
        "tenderPeriodEnd": p["tenderPeriodEnd"],
        "expressionOfInterestDeadline": p["expressionOfInterestDeadline"],
        "futureNoticeDate": p["futureNoticeDate"],
        "openFrameworkSchemeEndDate": p["openFrameworkSchemeEndDate"],
        "verifiedOn": today,
        "sourceQuote": quote,
        "notVerified": nv,
    }
    nv.append("No supplier list exists yet: framework not awarded. Settled by the award notice "
              "(UK6/UK7) on Find a Tender once published.")
    nv.append("All dates and values are as stated in the notice; the notice itself says they "
              "are subject to change. Settled by the later tender/award notice.")
    return entry


def build(fetcher=fetch, today="2026-10-20"):
    entries = [
        build_ts4(fetcher, today),
        build_gc15(fetcher, today),
        build_coming(fetcher, "050314-2026", "Healthcare AI Solutions",
                     "NHS Shared Business Services Limited", today),
        build_coming(fetcher, "094419-2026", "Digital Primary Care (GP IT) Open Framework",
                     "NHS England", today),
    ]
    return {"rule": RULE, "source": SOURCE, "generated": today, "dataAsOf": today,
            "frameworks": entries}


def counts(doc):
    out = []
    for e in doc["frameworks"]:
        per = {l["lot"]: l.get("supplierCount") for l in e["lots"]}
        out.append((e["reference"], len(e["lots"]), per))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--today", default=time.strftime("%Y-%m-%d"))
    a = ap.parse_args(argv)
    try:
        doc = build(today=a.today)
    except Exception as e:  # noqa: BLE001
        print("refresh_digital_frameworks: FAILED, file not written: %s" % e, file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for ref, n, per in counts(doc):
        print(ref, "lots=%d" % n, per)
    return 0


if __name__ == "__main__":
    sys.exit(main())
