#!/usr/bin/env python3
"""Read turnover and employee numbers out of the FILED ACCOUNTS themselves, and
write them into data/company-financials.json as a dated, sourced series.

WHY THIS IS A SEPARATE SCRIPT FROM refresh_companies_house.py
-------------------------------------------------------------
The Companies House company-profile API returns no turnover and no employee
count — the fields do not exist on that resource. Both live only inside the
accounts document a company files. So the profile fetch and this are different
jobs against different APIs, and conflating them is how `turnoverGBP` ends up
holding something nobody sourced.

WHAT IT READS, AND WHAT IT REFUSES TO READ
------------------------------------------
Companies House serves each filing in up to two formats. Where an **iXBRL**
(application/xhtml+xml) rendering exists, the figures are machine-TAGGED by the
filer: `TurnoverRevenue` is turnover because the company said so. That is read.

Where the only format is **PDF**, this script writes NOTHING and records why.
Roughly six filings in ten are PDF-only. Lifting a number off a scanned profit
and loss account by position or proximity would be a guess about which figure is
turnover, and a wrong turnover published against a named company is exactly the
class of error the 24/07/2026 incident was. An honest "not disclosed in a
machine-readable filing" beats a plausible number every time.

Small and micro companies may lawfully omit the profit and loss account, and
most UK medtech subsidiaries do. A missing turnover is therefore usually a fact
about the filing regime, not a gap in this script — the record says which.

THE SERIES
----------
Every accounts filing tags the current year AND the comparative year, so walking
several filings back builds a multi-year run from primary documents. Each point
carries the period it belongs to, the tag it came from, the filing date and the
document URL, so any figure on the growth chart can be traced to the page it was
read from. Where two filings disagree about the same period (a restatement), the
MORE RECENT filing wins and the disagreement is recorded rather than hidden.

Run:  python3 scripts/extract_accounts_figures.py [--limit N] [--filings N] [--only NAME]
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import base64
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

FIN = "data/company-financials.json"
API = "https://api.company-information.service.gov.uk"
KEY_ENV = "COMPANIES_HOUSE_KEY"
KEY_FILE = "~/.companies-house-key"
MIN_GAP = 0.55          # 600 requests / 5 min; stay well under
FILINGS_PER_COMPANY = 4  # each gives 2 years, so ~8 years of run

# Local tag names accepted as TURNOVER. Namespace prefixes vary by taxonomy and
# filer (core:, d:, ns5:, uk-gaap:), so matching is on the local name only.
# This list is deliberately short: every entry means turnover in the taxonomy it
# comes from. Anything else — RevenueFromRoyaltiesLicencesSimilarItems,
# RevenueFromSaleOfGoods on its own, segment breakdowns — is NOT the top line
# and must never be promoted to one.
TURNOVER_TAGS = {
    "turnoverrevenue",
    "turnover",
    "turnovergrossoperatingrevenue",
    "revenue",
}
EMPLOYEE_TAGS = {
    "averagenumberemployeesduringperiod",
    "averagenumberofemployeesduringtheperiod",
}


def load_key():
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key
    p = os.path.expanduser(KEY_FILE)
    if os.path.exists(p):
        key = pathlib.Path(p).read_text(encoding="utf-8").strip()
        if key:
            return key
    sys.exit("ABORT: no Companies House key in $%s or %s." % (KEY_ENV, KEY_FILE))


KEY = load_key()
AUTH = {"Authorization": "Basic " + base64.b64encode((KEY + ":").encode()).decode()}
_last = [0.0]


def pace():
    gap = time.time() - _last[0]
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    _last[0] = time.time()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """The document content endpoint 302s to signed storage. Following it with
    the Authorization header attached makes the storage host reject the request,
    so the redirect is caught and the signed URL fetched clean."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, newurl, headers, fp)


_opener = urllib.request.build_opener(_NoRedirect)


def api_get(path):
    pace()
    try:
        r = urllib.request.urlopen(urllib.request.Request(API + path, headers=AUTH), timeout=45)
        return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(30)
            return api_get(path)
        return None
    except Exception:
        return None


def doc_json(url):
    pace()
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=AUTH), timeout=45))
    except Exception:
        return None


def doc_content(url, _retry=0):
    """The document bytes, or None. A network fault on ONE document must never
    end a run that is walking hundreds of them."""
    pace()
    req = urllib.request.Request(url, headers=dict(AUTH, Accept="application/xhtml+xml"))
    try:
        return _opener.open(req, timeout=90).read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307):
            try:
                return urllib.request.urlopen(e.reason, timeout=120).read()  # signed: no auth
            except Exception:
                return None
        if e.code == 429 and _retry < 2:
            time.sleep(30)
            return doc_content(url, _retry + 1)
        return None
    except Exception:
        if _retry < 1:
            time.sleep(5)
            return doc_content(url, _retry + 1)
        return None


CTX_RE = re.compile(r"(?is)<[a-z0-9]*:?context\b[^>]*\bid=\"([^\"]+)\"(.*?)</[a-z0-9]*:?context>")
ENDDATE_RE = re.compile(r"(?is)<[a-z0-9]*:?(?:endDate|instant)>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
STARTDATE_RE = re.compile(r"(?is)<[a-z0-9]*:?startDate>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
# ix:nonFraction carries the tagged numeric facts.
FACT_RE = re.compile(r"(?is)<[a-z0-9]*:?nonFraction\b([^>]*)>(.*?)</[a-z0-9]*:?nonFraction>")
# unitRef points at a LOCAL id ("u1"), not a currency. The currency lives in the
# unit's own measure element. Comparing the id against "GBP" silently discarded
# every turnover fact in the file, which is why this is resolved properly.
UNIT_RE = re.compile(r"(?is)<[a-z0-9]*:?unit\b[^>]*\bid=\"([^\"]+)\"(.*?)</[a-z0-9]*:?unit>")
MEASURE_RE = re.compile(r"(?is)<[a-z0-9]*:?measure>\s*([^<\s]+)")


def units(html):
    out = {}
    for uid, body in UNIT_RE.findall(html):
        m = MEASURE_RE.search(body)
        if m:
            out[uid] = m.group(1).split(":")[-1].upper()
    return out
ATTR_RE = re.compile(r"([a-zA-Z:.\-]+)\s*=\s*\"([^\"]*)\"")


def contexts(html):
    """context id -> (period end, has a start date i.e. a duration not an instant)."""
    out = {}
    for cid, body in CTX_RE.findall(html):
        # A context carrying a dimension is a SEGMENT (a division, a subsidiary,
        # a class of share). The top line belongs to the plain company context,
        # so segmented contexts are dropped rather than competing with it.
        if re.search(r"(?i)<[a-z0-9]*:?(?:segment|scenario)\b", body):
            continue
        end = ENDDATE_RE.search(body)
        if not end:
            continue
        out[cid] = (end.group(1), bool(STARTDATE_RE.search(body)))
    return out


def facts(html):
    for attrs_s, inner in FACT_RE.findall(html):
        a = dict(ATTR_RE.findall(attrs_s))
        name = (a.get("name") or "").split(":")[-1].strip().lower()
        if not name:
            continue
        text = re.sub(r"<[^>]+>", "", inner)
        text = text.replace(",", "").replace(" ", " ").strip()
        if text in ("", "-", "–"):
            continue
        neg = a.get("sign") == "-"
        try:
            val = float(text)
        except ValueError:
            continue
        try:
            val *= 10 ** int(a.get("scale") or 0)
        except ValueError:
            pass
        if neg:
            val = -val
        yield name, a.get("contextRef") or a.get("contextref") or "", val, a.get("unitRef") or a.get("unitref") or ""


def figures_from(html):
    """[(period_end, kind, value, tag)] for the plain company contexts."""
    ctx = contexts(html)
    umap = units(html)
    out = []
    for name, cref, val, unit in facts(html):
        c = ctx.get(cref)
        if not c:
            continue
        end, is_duration = c
        if name in TURNOVER_TAGS:
            # Turnover is a flow: it belongs to a period, never to an instant.
            if not is_duration:
                continue
            # Turnover must be money, and money we can read: an untagged unit is
            # accepted (older filings omit it), a non-GBP one is not, because the
            # page prints a pound sign.
            cur = umap.get(unit)
            if cur and cur != "GBP":
                continue
            out.append((end, "turnover", val, name))
        elif name in EMPLOYEE_TAGS:
            out.append((end, "employees", val, name))
    return out


def arg(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def _save(doc):
    doc["figuresAsOf"] = time.strftime("%Y-%m-%d")
    doc["figuresSource"] = ("Turnover and employee numbers are read from the iXBRL (tagged) "
                            "accounts filed at Companies House, via the Document API. Filings "
                            "available only as PDF are NOT parsed and yield null: identifying a "
                            "turnover line on a PDF by position would be a guess. Each figure "
                            "carries the tag, the period, the filing date and the document it "
                            "was read from.")
    with open(FIN, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")


def main():
    limit = arg("--limit")
    limit = int(limit) if limit else None
    per = int(arg("--filings", FILINGS_PER_COMPANY))
    only = arg("--only")

    doc = json.load(open(FIN, encoding="utf-8"))
    companies = doc.get("companies") or {}
    targets = [(n, r) for n, r in sorted(companies.items())
               if r.get("matchConfidence") == "confirmed" and r.get("companyNumber")]
    if only:
        targets = [(n, r) for n, r in targets if n == only]
    skip = int(arg("--skip", 0) or 0)
    if skip:
        targets = targets[skip:]
    if limit:
        targets = targets[:limit]

    stats = {"companies": 0, "with_turnover": 0, "pdf_only": 0, "no_ixbrl_figures": 0, "points": 0}

    for name, rec in targets:
        num = rec["companyNumber"]
        fh = api_get("/company/%s/filing-history?category=accounts&items_per_page=%d" % (num, per))
        items = (fh or {}).get("items") or []
        if not items:
            rec["turnoverNote"] = "no accounts filing found on the register"
            continue

        series, employees, pdf_only, ixbrl_read, seen_periods = {}, {}, 0, 0, {}
        for it in items:
            dm = (it.get("links") or {}).get("document_metadata")
            if not dm:
                continue
            md = doc_json(dm)
            if not md:
                continue
            res = md.get("resources") or {}
            if "application/xhtml+xml" not in res:
                pdf_only += 1
                continue
            raw = doc_content(dm + "/content")
            if not raw:
                continue
            ixbrl_read += 1
            html = raw.decode("utf-8", "replace")
            filed = it.get("date")
            for end, kind, val, tag in figures_from(html):
                point = {"periodEnd": end, "value": val, "tag": tag,
                         "filedOn": filed, "document": dm}
                if kind == "turnover":
                    prev = series.get(end)
                    if prev and abs(prev["value"] - val) > 0.5:
                        # A restatement. The later filing is the company's own
                        # current view; the earlier figure is kept as a note so
                        # the change is visible rather than silently overwritten.
                        if prev["filedOn"] >= (filed or ""):
                            prev.setdefault("supersededValues", []).append(val)
                            continue
                        point["supersededValues"] = [prev["value"]]
                    series[end] = point
                    seen_periods[end] = 1
                else:
                    if end not in employees or (filed or "") > employees[end]["filedOn"]:
                        employees[end] = point

        stats["companies"] += 1
        if pdf_only and not ixbrl_read:
            stats["pdf_only"] += 1

        points = [series[k] for k in sorted(series)]
        # A zero turnover for a trading company is a parse fault far more often
        # than a fact, and this file's null already means "not disclosed".
        points = [p for p in points if p["value"] > 0]
        stats["points"] += len(points)

        if points:
            latest = points[-1]
            rec["turnoverGBP"] = latest["value"]
            rec["accountsMadeUpTo"] = rec.get("accountsMadeUpTo") or latest["periodEnd"]
            rec["turnoverSeries"] = points
            rec["turnoverNote"] = ("read from the tagged (iXBRL) accounts filed at Companies "
                                   "House; %d period(s) from %d filing(s)"
                                   % (len(points), len(items)))
            stats["with_turnover"] += 1
        else:
            rec["turnoverGBP"] = None
            rec.pop("turnoverSeries", None)
            if pdf_only and not ixbrl_read:
                rec["turnoverNote"] = ("the filed accounts are available only as a PDF, which "
                                       "carries no tagged figures. Nothing is read from it: "
                                       "identifying the turnover line by position would be a "
                                       "guess, not a reading.")
            else:
                rec["turnoverNote"] = ("the tagged accounts carry no turnover: small and micro "
                                       "companies may lawfully omit the profit and loss account, "
                                       "and most UK medtech subsidiaries do.")
                stats["no_ixbrl_figures"] += 1

        emp = [employees[k] for k in sorted(employees)]
        # A headcount that rounds to zero is not a headcount. Some filings tag a
        # fractional or zero average (dormant and holding companies do), and this
        # file's null already means "not disclosed" — writing 0 would print as a
        # trading company with no staff, which is a parse fault, not a fact.
        if emp and int(round(emp[-1]["value"])) >= 1:
            rec["employees"] = int(round(emp[-1]["value"]))
            rec["employeesNote"] = ("average during the period ended %s, from the tagged accounts"
                                    % emp[-1]["periodEnd"])

        # Save as we go. This walks hundreds of documents; a run that stops
        # part way must keep what it has already read rather than starting over.
        if stats["companies"] % 15 == 0:
            _save(doc)

        print("  %-34s %s" % (name[:34],
                              ("£%s (%d period(s))" % (format(int(points[-1]['value']), ','), len(points)))
                              if points else rec["turnoverNote"][:64]))

    _save(doc)
    print("\n%d company(ies) read: %d with turnover (%d data points), %d PDF-only, "
          "%d tagged but with no turnover line."
          % (stats["companies"], stats["with_turnover"], stats["points"],
             stats["pdf_only"], stats["no_ixbrl_figures"]))
    return


def _unused(doc):
    doc["figuresAsOf"] = time.strftime("%Y-%m-%d")
    doc["figuresSource"] = ("Turnover and employee numbers are read from the iXBRL (tagged) "
                            "accounts filed at Companies House, via the Document API. Filings "
                            "available only as PDF are NOT parsed and yield null: identifying a "
                            "turnover line on a PDF by position would be a guess. Each figure "
                            "carries the tag, the period, the filing date and the document it "
                            "was read from.")
    with open(FIN, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("\n%d company(ies) read: %d with turnover (%d data points), %d PDF-only, "
          "%d tagged but with no turnover line."
          % (stats["companies"], stats["with_turnover"], stats["points"],
             stats["pdf_only"], stats["no_ixbrl_figures"]))


if __name__ == "__main__":
    main()
