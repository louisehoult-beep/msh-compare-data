#!/usr/bin/env python3
"""
refresh_digital_frameworks.py - build data/digital-frameworks.json.

Digital / technology frameworks a medical-sales rep may meet:
  live    Technology Services 4 (RM6190) and G-Cloud 15 (RM1557.15), Government
          Commercial Agency (GCA, formerly Crown Commercial Service, renamed
          1 April 2026), read from gca.gov.uk. The G-Cloud 15 supplier list
          is the Digital Marketplace supplier A to Z (company names only; the
          A to Z does not give lots, so G-Cloud 15 lot lists stay null).
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
DM = "https://www.applytosupply.digitalmarketplace.service.gov.uk"
GC15_AZ = DM + "/g-cloud-15/suppliers"
AZ_PREFIXES = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + ["other"]
AZ_MAX_PAGES = 40
FTS_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages/"
FTS_NOTICE = "https://www.find-tender.service.gov.uk/Notice/"
UA = "Mozilla/5.0 (compatible; msh-compare-data digital-frameworks)"
TIMEOUT = 20

RULE = ("Every fact read at the named primary source on verifiedOn, else 'Not verified' "
        "with what would settle it. Supplier lists hold company names only; no contact "
        "person, email, phone or address is ever stored. suppliers null means no list was read.")
SOURCE = ("gca.gov.uk agreement pages and lot-supplier CSV exports; "
          "find-tender.service.gov.uk OCDS API; sbs.nhs.uk framework pages")


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
    if not m:
        # 23/10/2026: gca.gov.uk dropped the colons ("Agreement ID" / value on the next line).
        m = re.search(r"^" + re.escape(label) + r"[ \t]*\n\s*([^\n]+)", txt, re.M)
    return m.group(1).strip() if m else None


def parse_agreement_header(page_html):
    txt = text_of(page_html)
    ref = meta_field(txt, "Agreement number") or meta_field(txt, "Agreement ID")
    if not ref:
        # gca.gov.uk answers an outage with a redirect to an "unavailable" page, which
        # reads as an empty agreement. Fail the run rather than overwrite good data.
        raise RuntimeError("agreement page has no 'Agreement number' (site unavailable?)")
    return {
        "reference": ref,
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


def parse_dm_az(page_html):
    """One page of a Digital Marketplace supplier A to Z: (company names, next href).
    Only the supplier link text is read. The description under each name and the
    supplier's own page (which carries a contact person, phone and email) are never
    read or stored."""
    names = [html.unescape(re.sub(r"\s+", " ", m)).strip() for m in
             re.findall(r'<a class="govuk-link" href="/g-cloud-15/supplier/\d+">([^<]+)</a>',
                        page_html)]
    m = re.search(r'href="([^"]+)"\s+rel="next"', page_html)
    return [n for n in names if n], (html.unescape(m.group(1)) if m else None)


def read_gc15_az(fetcher):
    """Every name on the G-Cloud 15 supplier A to Z, all prefixes and pages."""
    names = set()
    for prefix in AZ_PREFIXES:
        url = "%s?prefix=%s" % (GC15_AZ, prefix)
        for _ in range(AZ_MAX_PAGES):
            got, nxt = parse_dm_az(fetcher(url))
            names.update(got)
            if not nxt:
                break
            url = DM + nxt
        else:
            raise RuntimeError("prefix %s ran past %d pages" % (prefix, AZ_MAX_PAGES))
    if not names:
        raise RuntimeError("the A to Z gave no supplier names")
    return sorted(names, key=str.casefold)


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
        suppliers = read_gc15_az(fetcher)
        nv.append("Supplier list read from the Digital Marketplace G-Cloud 15 supplier A to Z "
                  "(%s), company names only, %d suppliers. The A to Z does not say which lot "
                  "each supplier holds, so every lot's list stays null; a supplier's lot is "
                  "shown only where its own service page was read." % (GC15_AZ, len(suppliers)))
    except Exception as e:  # noqa: BLE001
        nv.append("Supplier list not verified: the Digital Marketplace G-Cloud 15 supplier A to Z "
                  "(%s) could not be read in full (%s). Settled by re-running when it is "
                  "reachable." % (GC15_AZ, e))
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


# ------------------------------------------------------------------ added 20/10/2026 (second pass)
# NHS Shared Business Services (SBS) framework pages and Find a Tender award / planning
# notices for the digital frameworks scoped in "Hub health tech intelligence gap".

SBS = "https://www.sbs.nhs.uk/services/framework-agreements/"
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def long_date(s):
    """'01 October 2025' or '9 January 2023' -> ISO."""
    import datetime as _dt
    try:
        return _dt.datetime.strptime(s.strip(), "%d %B %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_sbs_page(page_html):
    """Reference, active dates and the extension option, as the SBS page states them."""
    txt = text_of(page_html)
    ref = re.search(r"Framework Agreement Reference:\s*(SBS\d+)", txt)
    m = re.search(r"What dates is the framework agreement active\?\s*\n\s*(\d{1,2} (?:%s) \d{4})\s*[\u2013-]\s*(\d{1,2} (?:%s) \d{4})(?:\s*\n\s*\(([^)\n]+)\))?" % (MONTHS, MONTHS), txt)
    return {
        "reference": ref.group(1) if ref else None,
        "starts": long_date(m.group(1)) if m else None,
        "ends": long_date(m.group(2)) if m else None,
        "option": m.group(3).strip() if m and m.group(3) else None,
        "dateLine": re.sub(r"\s+", " ", m.group(0).split("?", 1)[1]).strip() if m else None,
    }


def award_suppliers(pkg):
    """{lot id: sorted company names} from the award notice, names exactly as published."""
    r = pkg["releases"][0]
    out = {}
    for a in r.get("awards", []):
        for lot in a.get("relatedLots") or ["1"]:
            for s in a.get("suppliers") or []:
                n = (s.get("name") or "").strip()
                if n:
                    out.setdefault(str(lot), set()).add(n)
    return {k: sorted(v, key=str.casefold) for k, v in out.items()}


def build_award(fetcher, notice_id, name, owner, today, sbs_slug=None, extra_nv=(), url=None):
    nv = list(extra_nv)
    pkg = json.loads(fetcher(FTS_API + notice_id))
    r = pkg["releases"][0]
    p = parse_ocds(pkg, notice_id)
    sup = award_suppliers(pkg)
    page = None
    if sbs_slug:
        page = parse_sbs_page(fetcher(SBS + sbs_slug + "/"))
    lots = []
    lot_ids = [str(l["lot"]) for l in p["lots"]] or sorted(sup)
    for lid in sorted(set(lot_ids) | set(sup)):
        names = sup.get(lid)
        meta = next((l for l in p["lots"] if str(l["lot"]) == lid), {})
        lots.append({"lot": lid, "name": meta.get("name"), "note": None,
                     "suppliers": names, "supplierCount": len(names) if names else None})
    allnames = sorted({n for v in sup.values() for n in v}, key=str.casefold)
    contract_val = None
    for c in r.get("contracts") or []:
        if c.get("value"):
            contract_val = ocds_money(c["value"])
            break
    if page and page["starts"]:
        starts, ends = page["starts"], page["ends"]
    else:
        starts = ends = None
        nv.append("Framework start and end dates are not stated in the award notice. Settled by "
                  "the framework owner's page or the framework agreement documents.")
    entry = {
        "name": name,
        "reference": (page or {}).get("reference") or "Find a Tender notice " + notice_id,
        "owner": p["buyer"] or owner,
        "url": url or (SBS + sbs_slug + "/" if sbs_slug else p["url"]),
        "status": "live",
        "starts": starts,
        "ends": ends,
        "lots": lots,
        "suppliers": allnames or None,
        "noticeTitle": p["title"],
        "noticeStatus": p["status"],
        "noticeUrl": p["url"],
        "noticeTag": p["noticeTag"],
        "noticeReleaseDate": p["publishedRelease"],
        "procedure": p["procedure"],
        "estimatedValue": contract_val,
        "verifiedOn": today,
        "sourceQuote": (page or {}).get("dateLine"),
        "notVerified": nv,
    }
    if page and page.get("option"):
        entry["extensionOption"] = page["option"]
    nv.append("Supplier names are as published in the award notice (a trading name or former "
              "name may appear); not alias-resolved to Hub companies here.")
    return entry


def build_sbs_page_only(fetcher, slug, name, today, extra_nv=()):
    nv = list(extra_nv)
    page_html = fetcher(SBS + slug + "/")
    pg = parse_sbs_page(page_html)
    if not pg["reference"] or not pg["starts"]:
        raise RuntimeError("SBS page %s: reference or dates not found" % slug)
    nv.append("Supplier list not read: the SBS page lists suppliers behind its own supplier tab "
              "and no award notice was read for this framework. Settled by the SBS supplier "
              "details or the award notice.")
    return {
        "name": name,
        "reference": pg["reference"],
        "owner": "NHS Shared Business Services (NHS SBS)",
        "url": SBS + slug + "/",
        "status": "live",
        "starts": pg["starts"],
        "ends": pg["ends"],
        "extensionOption": pg["option"],
        "lots": [],
        "suppliers": None,
        "verifiedOn": today,
        "sourceQuote": pg["dateLine"],
        "notVerified": nv,
    }


def build_extras(fetcher, today):
    """Each extra is independent: one that cannot be read is listed under notAdded with the
    reason, never guessed, and never stops the core four writing."""
    entries, not_added = [], []

    def attempt(label, url, fn):
        try:
            entries.append(fn())
        except Exception as e:  # noqa: BLE001
            not_added.append({"source": label, "url": url, "checkedOn": today,
                              "reason": "Could not be read on this run (%s). Nothing recorded; "
                                        "settled by re-running when the source is reachable." % e})

    attempt("NHS SBS Technology Enabled Care Services 2 (SBS10144)", SBS + "technology-enabled-care-services-2/",
            lambda: build_sbs_page_only(fetcher, "technology-enabled-care-services-2",
                                        "Technology Enabled Care Services 2", today))
    def tecs3():
        e = build_coming(fetcher, "050041-2025", "Technology Enabled Care Services 3 (SBS10529)",
                         "NHS Shared Business Services Limited", today)
        e["reference"] = "SBS10529 (Find a Tender notice 050041-2025)"
        e["noticeStatus"] = "planning (preliminary market engagement only)"
        e["notVerified"].insert(0, "Only a preliminary market engagement notice exists; no tender "
                                   "notice had been found on Find a Tender on the read date. The "
                                   "SBS bidder webinar page says the tender is due to launch soon. "
                                   "Settled by the tender notice once published.")
        return e
    attempt("NHS SBS Technology Enabled Care Services 3 (SBS10529)", FTS_NOTICE + "050041-2025", tecs3)
    attempt("NHS SBS Digital Workplace Solutions 2 (SBS10510)", SBS + "digital-workplace-solutions/",
            lambda: build_award(fetcher, "074808-2025", "Digital Workplace Solutions 2", "NHS Shared Business Services Limited",
                                today, "digital-workplace-solutions"))
    attempt("NHS SBS Tech Devices (SBS10515)", SBS + "tech-devices-link-4/",
            lambda: build_sbs_page_only(fetcher, "tech-devices-link-4", "Tech Devices", today))
    attempt("NHS SBS Digital Health Advisory (SBS10225)", SBS + "digital-health-advisory/",
            lambda: build_sbs_page_only(fetcher, "digital-health-advisory", "Digital Health Advisory", today))
    attempt("HealthTrust Europe Digital Pathology 2024 Framework", FTS_NOTICE + "058054-2026",
            lambda: build_award(fetcher, "058054-2026", "Digital Pathology 2024 Framework (HealthTrust Europe)",
                                "HealthTrust Europe LLP", today, None,
                                ["Value is the contract value stated in the award notice, not a spend figure."]))
    # Conflict check, computed from what was read: the TECS 3 notice states when the existing
    # TECS framework expires; the TECS 2 page states its own end date. If they differ, say so.
    by = {e["name"]: e for e in entries}
    t2, t3 = by.get("Technology Enabled Care Services 2"), by.get("Technology Enabled Care Services 3 (SBS10529)")
    if t2 and t3:
        try:
            raw = fetcher(FTS_API + "050041-2025")
            m = re.search(r"existing TECS framework is due to expire on (\d{2}/\d{2}/\d{4})", raw)
            notice_end = uk_date(m.group(1)) if m else None
            if notice_end and t2.get("ends") and notice_end != t2["ends"]:
                msg = ("Notice 050041-2025 says the existing TECS framework is due to expire on %s; "
                       "the SBS TECS 2 page states an end date of %s. The two disagree, both are "
                       "recorded as read, and the end date is Not verified. Settled by NHS SBS "
                       "confirming the TECS 2 expiry." % (notice_end, t2["ends"]))
                t2["notVerified"].append(msg)
                t3["notVerified"].append(msg)
        except Exception:  # noqa: BLE001 - the conflict note is a bonus, not a gate
            pass
    return entries, not_added


def build(fetcher=fetch, today="2026-10-20"):
    entries = [
        build_ts4(fetcher, today),
        build_gc15(fetcher, today),
        build_coming(fetcher, "050314-2026", "Healthcare AI Solutions",
                     "NHS Shared Business Services Limited", today),
        build_coming(fetcher, "094419-2026", "Digital Primary Care (GP IT) Open Framework",
                     "NHS England", today),
    ]
    extra, not_added = build_extras(fetcher, today)
    entries.extend(extra)
    return {"rule": RULE, "source": SOURCE, "generated": today, "dataAsOf": today,
            "frameworks": entries, "notAdded": not_added}


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
