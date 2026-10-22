#!/usr/bin/env python3
"""ICB pack (dermatology, emollients): one editable page of starting figures for one
ICB and one brand, built only from published open data.

Spec: 02-Elevate-and-Thrive/Process flows for all brands/icb-pack-dermatology-spec-2026-10-22.md
Check: python3 test_icb_pack.py            (offline, on the cached inputs)

Stages
  fetch   download the open sources into a cache folder (default tmp/icb-pack-cache,
          git-ignored). Needs the network. Skipped when the files are already there
          unless --refresh is given.
  build   compute every figure and write <out>/icb-pack-<ICB>-<BRAND>.html and a
          .json of the figures behind it.

Nothing is invented. Where a figure cannot be had from a named source this session it
is printed as "Not verified" with what would settle it (HUB-VERIFICATION-STANDARD).

Brand = rows whose BNF presentation name starts with "<brand> " (QV by default).
Market = emollient preparations: BNF 130201 (drug-tariff emollients) plus 2122
(appliance-list emollients). That denominator is OUR definition, shown on the page
and editable: Aneeka's own denominator is not known.
"""
import argparse
import collections
import csv
import datetime
import glob
import html
import io
import json
import math
import os
import re
import statistics
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

GP_DIR = os.path.join(ROOT, "data", "gp-prescribing")
UA = {"User-Agent": "msh-compare-data/icb-pack (+elevateandthrive.uk)"}

# Source landing pages. File URLs carry content hashes that change every release, so
# they are resolved from these pages at fetch time, never stored.
RTT_PAGE = "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2026-27/"
IMD_API = "https://www.gov.uk/api/content/government/statistics/english-indices-of-deprivation-2025"
# ONS LSOA (2021) to ICB (April 2026) lookup; item id from data.gov.uk dataset 1d16e489-1dc8-443e-9e1c-15de4f961c6d
LSOA_ICB_LOOKUP = "https://open-geography-portalx-ons.hub.arcgis.com/api/download/v1/items/bebf631bb1ac40cf9ec7dc060897ca99/csv?layers=0"
GPREG_PARENT = "https://digital.nhs.uk/data-and-information/publications/statistical/patients-registered-at-a-gp-practice"

LICENCES = [
    ("NHSBSA English Prescribing Dataset (SNOMED)", "Open Government Licence 3.0; reuse statement: NHSBSA Copyright. "
     "https://opendata.nhsbsa.net/dataset/english-prescribing-dataset-epd-with-snomed-code"),
    ("NHS England RTT waiting times (Incomplete Commissioner)", "Open Government Licence v3.0. " + RTT_PAGE),
    ("English Indices of Deprivation 2025, File 13 ICB summaries (MHCLG)", "Open Government Licence v3.0. "
     "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025"),
    ("IMD 2025 File 7 (LSOA scores and population) with ONS LSOA (2021) to ICB (April 2026) lookup",
     "Open Government Licence v3.0 (IMD); ONS lookup: data.gov.uk dataset licence field unset, site footer says "
     "Open Government Licence v3.0 except where stated. https://www.data.gov.uk/dataset/1d16e489-1dc8-443e-9e1c-15de4f961c6d"),
    ("NHS Digital Patients Registered at a GP Practice, mapping and practice totals", "NHS England terms: "
     "released under the Open Government Licence. " + GPREG_PARENT),
    ("NHS England, items which should not routinely be prescribed in primary care", "Open Government Licence v3.0. "
     "https://www.england.nhs.uk/long-read/items-which-should-not-routinely-be-prescribed-in-primary-care-policy-guidance"),
]

NOT_VERIFIED = "Not verified"
MARKET_PREFIXES = ("130201", "2122")      # BNF presentation-code prefixes


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------
def http(url, timeout=120, retries=2):
    last = None
    for _ in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001 - retried then reported
            last = exc
    raise RuntimeError("could not fetch %s: %s" % (url.split("?")[0], last))


def resolve_urls():
    """Current file URLs from the publishers' own pages."""
    urls = {}
    page = http(RTT_PAGE).decode("utf-8", "replace")
    m = re.search(r'href="([^"]*Incomplete-Commissioner-[A-Za-z]{3}\d\d[^"]*\.xlsx)"', page)
    if not m:
        raise RuntimeError("RTT Incomplete Commissioner link not found on %s" % RTT_PAGE)
    urls["rtt"] = html.unescape(m.group(1))
    doc = json.loads(http(IMD_API))
    atts = (doc.get("details") or {}).get("attachments", [])
    m = next((a for a in atts if "Integrated Care Board" in (a.get("title") or "") and a.get("url", "").endswith(".xlsx")), None)
    if not m:
        raise RuntimeError("IMD 2025 File 13 link not found")
    urls["imd"] = m["url"]
    f7 = next((a for a in atts if (a.get("title") or "").startswith("File 7")), None)
    if not f7:
        raise RuntimeError("IMD 2025 File 7 link not found")
    urls["imd7"] = f7["url"]
    parent = http(GPREG_PARENT).decode("utf-8", "replace")
    pubs = sorted(set(re.findall(r'href="([^"]*patients-registered-at-a-gp-practice/[a-z]+-\d{4})"', parent)))
    if not pubs:
        raise RuntimeError("no Patients Registered publication links found")
    months = ["january", "february", "march", "april", "may", "june", "july", "august",
              "september", "october", "november", "december"]

    def key(u):
        mo, yr = u.rsplit("/", 1)[1].split("-")
        return (int(yr), months.index(mo))
    # Newest first; a forthcoming month is listed before it has files, so take the first
    # publication that actually carries the mapping zip.
    for latest in sorted(pubs, key=key, reverse=True):
        if latest.startswith("/"):
            latest = "https://digital.nhs.uk" + latest
        try:
            pub = http(latest).decode("utf-8", "replace")
        except RuntimeError:
            continue
        found = {}
        for tag, pat in (("gpmap", r"gp-reg-pat-prac-map\.zip"), ("gpall", r"gp-reg-pat-prac-all\.zip")):
            m = re.search(r'href="([^"]*%s)"' % pat, pub)
            if m:
                found[tag] = m.group(1)
        if len(found) == 2:
            urls.update(found)
            break
    else:
        raise RuntimeError("no Patients Registered publication with the mapping and practice files")
    urls["gpreg_page"] = latest
    return urls


def fetch_all(cache, refresh=False):
    os.makedirs(cache, exist_ok=True)
    meta_path = os.path.join(cache, "sources.json")
    files = ("rtt-incomplete-commissioner.xlsx", "imd2025-file13-icb.xlsx", "imd2025-file7-lsoa.csv",
             "lsoa21-icb26-lookup.csv", "gp-reg-pat-prac-map.zip", "gp-reg-pat-prac-all.zip")
    need = refresh or not os.path.exists(meta_path) or any(
        not os.path.exists(os.path.join(cache, f)) for f in files)
    if need:
        urls = resolve_urls()
        urls["lsoa"] = LSOA_ICB_LOOKUP
        for tag, fn in (("rtt", "rtt-incomplete-commissioner.xlsx"), ("imd", "imd2025-file13-icb.xlsx"), ("imd7", "imd2025-file7-lsoa.csv"),
                        ("lsoa", "lsoa21-icb26-lookup.csv"),
                        ("gpmap", "gp-reg-pat-prac-map.zip"), ("gpall", "gp-reg-pat-prac-all.zip")):
            with open(os.path.join(cache, fn), "wb") as f:
                f.write(http(urls[tag], timeout=240))
        urls["fetchedOn"] = datetime.date.today().isoformat()
        json.dump(urls, open(meta_path, "w"), indent=1)
    return json.load(open(meta_path))


def fetch_rtt_history(cache, refresh=False, months=13):
    """The last `months` Incomplete Commissioner files, from the two NHS England RTT year pages."""
    os.makedirs(os.path.join(cache, "rtt"), exist_ok=True)
    found = {}
    mon = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    for page in (RTT_PAGE, RTT_PAGE.replace("2026-27", "2025-26")):
        text = http(page).decode("utf-8", "replace")
        for u in re.findall(r'href="([^"]*Incomplete-Commissioner-[A-Za-z]{3}\d\d[^"]*\.xlsx)"', text):
            m = re.search(r"Commissioner-([A-Za-z]{3})(\d\d)", u)
            found["20%s%02d" % (m.group(2), mon[m.group(1)])] = html.unescape(u)
    wanted = sorted(found)[-months:]
    for p in wanted:
        path = os.path.join(cache, "rtt", "%s.xlsx" % p)
        if refresh or not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(http(found[p], timeout=240))
    return wanted


def load_rtt_history(cache):
    """{period: {icb_code: row}} for dermatology from every cached month."""
    out = {}
    for path in sorted(glob.glob(os.path.join(cache, "rtt", "*.xlsx"))):
        out[os.path.basename(path)[:6]] = load_rtt(cache, path)[0]
    return out


def fetch_practice_level(cache, periods, refresh=False):
    """Practice-level market and brand items/cost per month, England, via the NHSBSA
    datastore SQL API (server-side aggregation, ~6.5k rows a month)."""
    import refresh_gp_prescribing as g
    path = os.path.join(cache, "epd-practice-months.json")
    have = json.load(open(path)) if os.path.exists(path) and not refresh else {}
    res = dict(g.resources())
    for p in periods:
        if p in have:
            continue
        t = res[p]
        q = ("SELECT PRACTICE_CODE AS pr, SUM(ITEMS) AS mi, SUM(ACTUAL_COST) AS mc, "
             "SUM(CASE WHEN BNF_PRESENTATION_NAME LIKE 'QV %' THEN ITEMS ELSE 0 END) AS qi, "
             "SUM(CASE WHEN BNF_PRESENTATION_NAME LIKE 'QV %' THEN ACTUAL_COST ELSE 0 END) AS qc "
             "FROM `{t}` WHERE SUBSTR(BNF_PRESENTATION_CODE,1,6)='130201' "
             "OR SUBSTR(BNF_PRESENTATION_CODE,1,4)='2122' GROUP BY PRACTICE_CODE".format(t=t))
        rows = g.sql(t, q)
        have[p] = {r["pr"]: [float(r["mi"] or 0), float(r["mc"] or 0), float(r["qi"] or 0), float(r["qc"] or 0)]
                   for r in rows}
        json.dump(have, open(path, "w"))
    return have


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def zip_csv(path):
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))


def load_gpreg(cache):
    mp = {}
    for r in zip_csv(os.path.join(cache, "gp-reg-pat-prac-map.zip")):
        mp[r["PRACTICE_CODE"]] = {"pcn": r["PCN_CODE"], "pcn_name": r["PCN_NAME"], "icb": r["ICB_CODE"],
                                  "icb_name": r["ICB_NAME"], "ons_icb": r["ONS_ICB_CODE"], "name": r["PRACTICE_NAME"]}
    size = {}
    for r in zip_csv(os.path.join(cache, "gp-reg-pat-prac-all.zip")):
        if r["TYPE"] == "GP" and r["SEX"] == "ALL" and r["AGE"] == "ALL":
            size[r["CODE"]] = int(r["NUMBER_OF_PATIENTS"])
    return mp, size


def load_rtt(cache, path=None):
    """Dermatology Service (C_330) rows: per ICB from the ICB sheet, England from the
    National sheet. Returns ({icb_code: row, "ENGLAND": row}, period)."""
    import openpyxl
    wb = openpyxl.load_workbook(path or os.path.join(cache, "rtt-incomplete-commissioner.xlsx"),
                                read_only=True, data_only=True)
    need = ["Total number of incomplete pathways", "Total within 18 weeks",
            "Average (median) waiting time (in weeks)", "Total 52 plus weeks", "Total 65 plus weeks",
            "Total 78 plus weeks"]
    out, period = {}, None

    def rows_of(sheet):
        rows = list(wb[sheet].iter_rows(values_only=True))
        hi = next(i for i, r in enumerate(rows) if r[1] in ("ICB Code", "Treatment Function Code"))
        h = {str(c).strip(): i for i, c in enumerate(rows[hi]) if c is not None}
        return rows, hi, h

    def pick(r, h, name):
        return {"name": name, "total": r[h[need[0]]], "w18": r[h[need[1]]], "median": r[h[need[2]]],
                "w52": r[h[need[3]]], "w65": r[h[need[4]]], "w78": r[h[need[5]]]}
    rows, hi, h = rows_of("ICB")
    for r in rows[:12]:
        if r[1] == "Period:":
            period = r[2]
    for r in rows[hi + 1:]:
        if r[3] == "C_330" and r[1] != "-":
            out[r[1]] = pick(r, h, r[2])
    rows, hi, h = rows_of("National")
    for r in rows[hi + 1:]:
        if r[1] == "C_330":
            out["ENGLAND"] = pick(r, h, "England")
    return out, period


def load_imd(cache):
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(cache, "imd2025-file13-icb.xlsx"), read_only=True, data_only=True)
    rows = list(wb["IMD"].iter_rows(values_only=True))
    out = {}
    for r in rows[1:]:
        if r[0]:
            out[r[0]] = {"name": r[1], "avg_rank": r[2], "rank_avg_rank": r[3], "avg_score": r[4],
                         "rank_avg_score": r[5], "prop10": r[6], "rank_prop10": r[7]}
    return out


def load_imd_recomputed(cache):
    """IMD 2025 for the ICBs as at April 2026, from LSOA-level File 7 and the ONS LSOA to
    ICB (April 2026) lookup. Population-weighted mean IMD score (mid-2022 population) and
    the share of LSOAs in the most deprived national decile: the same two measures File 13
    publishes for the 2024 ICBs, and test_icb_pack.py reproduces File 13 on the ICBs that
    did not change. Ranks are among the ICBs returned (36)."""
    look = {}
    with open(os.path.join(cache, "lsoa21-icb26-lookup.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            look[r["LSOA21CD"]] = r["ICB26CDH"]
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0, 0])
    with open(os.path.join(cache, "imd2025-file7-lsoa.csv"), encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        sc = next(c for c in cols if c.startswith("Index of Multiple Deprivation (IMD) Score"))
        dc = next(c for c in cols if c.startswith("Index of Multiple Deprivation (IMD) Decile"))
        pc = "Total population: mid 2022"
        for r in rd:
            icb = look.get(r["LSOA code (2021)"])
            if not icb:
                continue
            a = agg[icb]
            pop = float(r[pc])
            a[0] += pop
            a[1] += pop * float(r[sc])
            a[2] += 1
            a[3] += 1 if r[dc].strip() == "1" else 0
    out = {k: {"avg_score": v[1] / v[0], "prop10": v[3] / v[2], "lsoas": v[2], "population": v[0]}
           for k, v in agg.items()}
    for rank, k in enumerate(sorted(out, key=lambda k: -out[k]["avg_score"]), 1):
        out[k]["rank_avg_score"] = rank
    return out


def norm_icb(n):
    n = (n or "").upper().replace(" INTEGRATED CARE BOARD", "").replace(" ICB", "")
    n = re.sub(r"^NHS ", "", n)
    return re.sub(r"[^A-Z0-9]+", " ", n).strip()


def load_shards(brand):
    """From the repo's own ICB-level shards: brand and market items per ICB per month."""
    idx = json.load(open(os.path.join(GP_DIR, "index.json")))
    periods = idx["periods"]
    n = len(periods)
    brand_i = collections.defaultdict(lambda: [0] * n)
    brand_c = collections.defaultdict(lambda: [0.0] * n)
    mkt_i = collections.defaultdict(lambda: [0] * n)
    mkt_c = collections.defaultdict(lambda: [0.0] * n)
    brands = collections.defaultdict(lambda: collections.defaultdict(int))   # icb -> label -> 12m items
    for fn in ("s-1302.json", "s-2122.json"):
        s = json.load(open(os.path.join(GP_DIR, fn)))["s"]
        for sub, v in s.items():
            if not (sub.startswith("130201") or sub.startswith("2122")):
                continue
            for icb, prods in v["t"].items():
                for key, arr in prods.items():
                    label = v["p"].get(key, key)
                    for k in range(n):
                        mkt_i[icb][k] += arr[k] or 0
                    brands[icb][label] += sum(arr[-12:])
                    if label.lower().startswith(brand.lower()):
                        for k in range(n):
                            brand_i[icb][k] += arr[k] or 0
    return idx, brand_i, brand_c, mkt_i, mkt_c, brands


# --------------------------------------------------------------------------
# computation
# --------------------------------------------------------------------------
def pct(a, b):
    return None if not b else 100.0 * a / b


def trend(series, floor):
    base, now = series[0], series[-1]
    if base < floor:
        return None
    return 100.0 * (now - base) / base


def cv(values):
    if len(values) < 3:
        return None
    m = statistics.mean(values)
    return None if m == 0 else statistics.pstdev(values) / m


def assemble(cache, icb_code, brand):
    idx, bi, bc, mi, mc, brands = load_shards(brand)
    periods = idx["periods"]
    floor = idx["minBaselineItems"]
    icb_names = idx["icbs"]
    gmap, size = load_gpreg(cache)
    rtt, rtt_period = load_rtt(cache)
    imd = load_imd_recomputed(cache)
    rtt_hist = load_rtt_history(cache)
    rtt_periods = sorted(rtt_hist)
    prac = json.load(open(os.path.join(cache, "epd-practice-months.json")))
    last12 = periods[-12:]
    sources = json.load(open(os.path.join(cache, "sources.json")))

    # practice -> PCN level, per (icb, pcn)
    pcn = {}
    unmapped_items = 0.0
    for p in periods:
        for pr, (m_i, m_c, q_i, q_c) in prac.get(p, {}).items():
            g = gmap.get(pr)
            if not g:
                unmapped_items += m_i
                continue
            key = (g["icb"], g["pcn"])
            d = pcn.setdefault(key, {"name": g["pcn_name"], "icb": g["icb"], "practices": set(),
                                     "m": {}, "q": {}, "qc": {}})
            d["practices"].add(pr)
            d["m"][p] = d["m"].get(p, 0) + m_i
            d["q"][p] = d["q"].get(p, 0) + q_i
            d["qc"][p] = d["qc"].get(p, 0) + q_c
    for (icb, code), d in pcn.items():
        d["list"] = sum(size.get(pr, 0) for pr in d["practices"])
        d["q12"] = sum(d["q"].get(p, 0) for p in last12)
        d["m12"] = sum(d["m"].get(p, 0) for p in last12)
        d["per1000"] = (1000.0 * d["q12"] / d["list"]) if d["list"] else None
        d["share"] = pct(d["q12"], d["m12"])

    # cost: not held per ICB in the shards, so taken from the practice-level pull
    cost_b = collections.defaultdict(lambda: [0.0] * len(periods))
    cost_m = collections.defaultdict(lambda: [0.0] * len(periods))
    nat_bc = [0.0] * len(periods)
    nat_mc = [0.0] * len(periods)
    for k, p in enumerate(periods):
        for pr, (m_i, m_c, q_i, q_c) in prac.get(p, {}).items():
            nat_bc[k] += q_c
            nat_mc[k] += m_c
            g = gmap.get(pr)
            if g:
                cost_b[g["icb"]][k] += q_c
                cost_m[g["icb"]][k] += m_c
    for code in icb_names:
        bc[code] = cost_b[code]
        mc[code] = cost_m[code]
    icbs = {}
    for code, name in icb_names.items():
        if code == "-":
            continue
        pcns = [d for (i, _), d in pcn.items() if i == code and d["list"]]
        per = [d["per1000"] for d in pcns if d["per1000"] is not None]
        q12 = sum(bi[code][-12:])
        m12 = sum(mi[code][-12:])
        imd_hit = imd.get(code)
        # a series only where the same ICB code carries a row in every month (April 2026
        # mergers break the series for the ICBs they created)
        series = None
        if all(code in rtt_hist[q] for q in rtt_periods):
            series = {"total": [rtt_hist[q][code]["total"] for q in rtt_periods],
                      "median": [rtt_hist[q][code]["median"] for q in rtt_periods],
                      "w52": [rtt_hist[q][code]["w52"] for q in rtt_periods]}
        icbs[code] = {"rtt_series": series, 
            "code": code, "name": name, "q12": q12, "m12": m12, "share12": pct(q12, m12),
            "brand_items": bi[code], "mkt_items": mi[code], "brand_cost": bc[code], "mkt_cost": mc[code],
            "trend_items": trend(bi[code], floor) if len(bi[code]) > 1 else None,
            "pcn_cv": cv(per), "n_pcn": len(per),
            "rtt": rtt.get(code), "imd": imd_hit,
            "list": sum(d["list"] for d in pcns),
        }
    nat_bi = [sum(bi[c][k] for c in bi if c != "-") + bi["-"][k] for k in range(len(periods))]
    nat_mi = [sum(mi[c][k] for c in mi) for k in range(len(periods))]
    return {"brand": brand, "icb": icb_code, "periods": periods, "floor": floor, "icbs": icbs, "pcn": pcn,
            "brands_in_icb": brands[icb_code], "nat": {"bi": nat_bi, "mi": nat_mi, "bc": nat_bc, "mc": nat_mc},
            "rtt_period": rtt_period, "rtt_national": rtt.get("ENGLAND"), "rtt_periods": rtt_periods,
            "rtt_nat_series": {"total": [rtt_hist[q]["ENGLAND"]["total"] for q in rtt_periods],
                               "median": [rtt_hist[q]["ENGLAND"]["median"] for q in rtt_periods]}, "sources": sources,
            "unmapped_items": unmapped_items, "gpreg_extract": "see sources.gpreg_page",
            "generated": datetime.date.today().isoformat(), "imd_n": len(imd)}


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def pretty(name):
    n = re.sub(r"^NHS ", "", name or "")
    n = re.sub(r" INTEGRATED CARE BOARD$", "", n, flags=re.I)
    n = n.title()
    return re.sub(r"\b(And|Of|The|On)\b", lambda m: m.group(1).lower(), n)


def e(x):
    return html.escape(str(x), quote=True)


def num(x, d=0):
    return NOT_VERIFIED if x is None else ("{:,.%df}" % d).format(x)


def pcts(x, d=1):
    return NOT_VERIFIED if x is None else "%.*f%%" % (d, x)


def money(x):
    return "£{:,.0f}".format(x)


def mlabel(p):
    return datetime.date(int(p[:4]), int(p[4:]), 1).strftime("%b %Y")


def ramp(v, lo, hi):
    """Light to deep navy; returns (background, text colour) with contrast chosen."""
    if v is None or hi == lo:
        return "#EDE7DC", "#1D2733"
    t = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    a, b = (237, 231, 220), (20, 48, 79)
    c = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return "#%02X%02X%02X" % c, ("#FFFFFF" if t > 0.45 else "#1D2733")


def line_svg(series, labels, w=640, h=170, colour="#14304F"):
    if not series or max(series) == 0:
        return "<p>No items.</p>"
    mx = max(series)
    pts = []
    for i, v in enumerate(series):
        x = 40 + i * (w - 60) / max(1, len(series) - 1)
        y = h - 28 - (v / mx) * (h - 50)
        pts.append((x, y, v))
    path = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", x, y) for i, (x, y, _) in enumerate(pts))
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (x, y, colour) for x, y, _ in pts)
    ticks = "".join('<text x="%.1f" y="%d" font-size="10" text-anchor="middle" fill="#1D2733">%s</text>'
                    % (x, h - 8, e(labels[i])) for i, (x, _, _) in enumerate(pts) if i % 3 == 0 or i == len(pts) - 1)
    return ('<svg viewBox="0 0 %d %d" role="img" aria-label="monthly items" style="width:100%%;max-width:%dpx">'
            '<text x="4" y="14" font-size="10" fill="#1D2733">max %s</text>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="2"/>%s%s</svg>'
            % (w, h, w, num(mx), path, colour, dots, ticks))


def build_html(D):
    brand, code, periods = D["brand"], D["icb"], D["periods"]
    I = D["icbs"][code]
    labels = [mlabel(p) for p in periods]
    nat = D["nat"]
    n12b, n12m = sum(nat["bi"][-12:]), sum(nat["mi"][-12:])
    css = """
:root{--navy:#0B1C33;--deep:#14304F;--gold:#A8842C;--goldl:#E0BE8E;--ink:#1D2733;--warm:#EDE7DC}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 Georgia,serif;color:var(--ink);background:#fff}
.band{padding:28px 0}.band.dark{background:var(--navy);color:#F5F1E8}.band.warm{background:var(--warm)}
.col{max-width:1080px;margin:0 auto;padding:0 40px}@media(max-width:600px){.col{padding:0 20px}}
h1,h2{font-family:"Didot","Bodoni 72",Georgia,serif;margin:0 0 10px}h1{font-size:34px}h2{font-size:24px;color:var(--navy)}
.dark h1,.dark h2,.dark p,.dark li{color:#F5F1E8}.dark .gold{color:var(--goldl)}
.eyebrow{font:700 12px/1 Helvetica,Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--navy);margin-bottom:8px}
.dark .eyebrow{color:var(--goldl)}
table{border-collapse:collapse;width:100%;font:13px/1.4 Helvetica,Arial,sans-serif}th,td{padding:6px 8px;border-bottom:1px solid #d8d2c4;text-align:right}
th:first-child,td:first-child{text-align:left}th{background:var(--deep);color:#fff;cursor:pointer}
.kpis{display:flex;flex-wrap:wrap;gap:14px;margin:12px 0}.kpi{border-left:4px solid var(--gold);padding:4px 12px;min-width:150px}
.kpi b{display:block;font:700 24px Georgia,serif;color:var(--navy)}.kpi span{font:12px Helvetica,Arial,sans-serif}
.nv{color:#7A1F1F;font-weight:700}.edit{border:1px dashed var(--gold);padding:10px;min-height:60px;background:#fff}
.note{font:12px/1.5 Helvetica,Arial,sans-serif;color:#39424d}.scroll{overflow-x:auto}
button{background:var(--navy);color:#fff;border:0;padding:9px 16px;font:14px Helvetica,Arial,sans-serif;cursor:pointer}
.hm td{text-align:center;font-size:11px;padding:4px 3px;min-width:34px}.hm td:first-child{min-width:230px;text-align:left}
@media print{button{display:none}.band.dark{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""
    def nv(x):
        return '<span class="nv">%s</span>' % NOT_VERIFIED if x == NOT_VERIFIED else e(x)

    # ---- national overview
    nat_trend = trend(nat["bi"], D["floor"])
    nat_html = ('<div class="kpis"><div class="kpi"><b>%s</b><span>%s items, 12 months to %s</span></div>'
                '<div class="kpi"><b>%s</b><span>%s share of emollient items (our market definition)</span></div>'
                '<div class="kpi"><b>%s</b><span>%s items %s vs %s</span></div>'
                '<div class="kpi"><b>%s</b><span>%s actual cost, 12 months</span></div></div>'
                % (num(n12b), e(brand), labels[-1], pcts(pct(n12b, n12m)), e(brand),
                   pcts(nat_trend) if nat_trend is not None else "too few to trend", e(brand), labels[-1], labels[0],
                   money(sum(nat["bc"][-12:])), e(brand)))
    rn = D["rtt_national"]
    nat_rtt = ("Dermatology, England, %s: %s incomplete pathways, median wait %s weeks, %s waiting 52+ weeks."
               % (e(D["rtt_period"]), num(rn["total"]), num(rn["median"], 1), num(rn["w52"])) if rn else NOT_VERIFIED)

    # ---- ICB view
    ti = I["trend_items"]
    brands_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(l), num(n), pcts(pct(n, I["m12"])))
        for l, n in sorted(D["brands_in_icb"].items(), key=lambda kv: -kv[1])[:12])
    icb_html = ('<div class="kpis"><div class="kpi"><b>%s</b><span>%s items, 12 months</span></div>'
                '<div class="kpi"><b>%s</b><span>share of emollient items in %s</span></div>'
                '<div class="kpi"><b>%s</b><span>%s items %s vs %s</span></div>'
                '<div class="kpi"><b>%s</b><span>%s actual cost, 12 months</span></div></div>'
                % (num(I["q12"]), e(brand), pcts(I["share12"]), e(pretty(I["name"])),
                   pcts(ti) if ti is not None else "too few to trend", e(brand), labels[-1], labels[0],
                   money(sum(I["brand_cost"][-12:])), e(brand)))
    icb_html += line_svg(I["brand_items"], labels)
    icb_html += ('<p class="note">Monthly %s items in the ICB. Market in the ICB: %s items in the 12 months.</p>'
                 '<h3>Top emollient products in the ICB (12 months, items)</h3><table><tr><th>Product</th>'
                 '<th>Items</th><th>Share of emollient items</th></tr>%s</table>'
                 % (e(brand), num(I["m12"]), brands_rows))

    # ---- PCN tables
    pcns = sorted([d for (i, _), d in D["pcn"].items() if i == code and d["list"]], key=lambda d: -d["q12"])
    top = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                  % (e(d["name"]), num(d["q12"]), num(d["list"]), num(d["per1000"], 1), pcts(d["share"]))
                  for d in pcns[:10])
    vals = [d["per1000"] for d in pcns]
    allv = [d["q"].get(p, 0) / d["list"] * 1000 for d in pcns for p in periods]
    lo, hi = min(allv), max(allv)
    hm_head = "".join("<th>%s</th>" % e(l) for l in labels)
    hm = ""
    for d in sorted(pcns, key=lambda d: -(d["per1000"] or 0)):
        cells = ""
        for p in periods:
            v = d["q"].get(p, 0) / d["list"] * 1000
            bg, fg = ramp(v, lo, hi)
            cells += '<td style="background:%s;color:%s">%.1f</td>' % (bg, fg, v)
        hm += "<tr><td>%s</td>%s</tr>" % (e(d["name"]), cells)
    pcn_html = ('<h3>Highest-prescribing PCNs (12 months)</h3><table><tr><th>PCN</th><th>%s items</th>'
                '<th>Registered patients</th><th>Items per 1,000 patients</th><th>Share of emollient items</th></tr>%s</table>'
                '<p class="note">Registered patients: NHS Digital practice totals, %s snapshot, applied to every month. '
                'A PCN is the sum of its member practices as NHS Digital maps them today.</p>'
                '<h3>Variation across the ICB\'s PCNs: %s items per 1,000 registered patients, by month</h3>'
                '<div class="scroll"><table class="hm"><tr><th>PCN</th>%s</tr>%s</table></div>'
                '<p class="note">PCN figures cover registered GP practices: %s of the ICB emollient items in the 12 months. The rest come from prescriber codes that have no PCN.</p><p class="note">Colour runs from the lowest to the highest cell in this ICB (%.1f to %.1f). '
                'Spread across PCNs (coefficient of variation of 12-month items per 1,000): %s, over %d PCNs.</p>'
                % (e(brand), top, e(D["sources"].get("gpreg_page", "")), e(brand), hm_head, hm,
                   pcts(pct(sum(d["m12"] for d in pcns), I["m12"])), lo, hi,
                   num(I["pcn_cv"], 2), I["n_pcn"]))

    # ---- RTT and IMD
    r = I["rtt"]
    if r:
        rtt_html = ('<div class="kpis"><div class="kpi"><b>%s</b><span>incomplete dermatology pathways</span></div>'
                    '<div class="kpi"><b>%s</b><span>median wait, weeks (England %s)</span></div>'
                    '<div class="kpi"><b>%s</b><span>within 18 weeks (England %s)</span></div>'
                    '<div class="kpi"><b>%s</b><span>waiting 52+ weeks</span></div></div>'
                    '<p class="note">NHS England RTT, Incomplete pathways, Commissioner basis, ICB sheet, treatment function '
                    'C_330 Dermatology Service, %s. Commissioner basis means patients registered with this ICB, wherever '
                    'they are treated. Trend below.</p>'
                    % (num(r["total"]), num(r["median"], 1), num(rn["median"], 1) if rn else NOT_VERIFIED,
                       pcts(pct(r["w18"], r["total"])), pcts(pct(rn["w18"], rn["total"])) if rn else NOT_VERIFIED,
                       num(r["w52"]), e(D["rtt_period"])))
        rs = I["rtt_series"]
        rl = [mlabel(q) for q in D["rtt_periods"]]
        if rs:
            rtt_html += ('<h3>Incomplete dermatology pathways, by month</h3>' + line_svg(rs["total"], rl) +
                         '<h3>Median wait (weeks), by month</h3>' + line_svg(rs["median"], rl, colour="#A8842C") +
                         '<p class="note">England median: ' + ", ".join(num(v, 1) for v in D["rtt_nat_series"]["median"]) +
                         '. Series is complete only for ICBs whose code is unchanged since April 2025.</p>')
        else:
            rtt_html += '<p><span class="nv">%s</span>: no 13-month series, this ICB was created by the April 2026 mergers.</p>' % NOT_VERIFIED
    else:
        rtt_html = "<p>%s</p>" % nv(NOT_VERIFIED)
    m = I["imd"]
    if m:
        imd_html = ('<div class="kpis"><div class="kpi"><b>%s of %d</b><span>rank of average score (1 = most deprived ICB)</span></div>'
                    '<div class="kpi"><b>%s</b><span>average IMD score</span></div>'
                    '<div class="kpi"><b>%s</b><span>of LSOAs in the most deprived 10%% nationally</span></div></div>'
                    '<p class="note">English Indices of Deprivation 2025: population-weighted mean of LSOA IMD scores (mid-2022 population), '
                    'LSOAs assigned to ICBs as at April 2026 (ONS lookup). Same method as the official File 13 ICB summaries, '
                    'which it reproduces on the ICBs unchanged since 2024; File 13 itself uses 2024 boundaries.</p>'
                    % (num(m["rank_avg_score"]), D["imd_n"], num(m["avg_score"], 2), pcts(100 * m["prop10"])))
    else:
        imd_html = '<p><span class="nv">%s</span>: no IMD figure for this ICB.</p>' % NOT_VERIFIED

    otc = ('<p><b>National position (verified this session).</b> NHS England\'s policy guidance, "Items which should not '
           'routinely be prescribed in primary care" (published 3 August 2023, updated 19 August 2025), lists bath and '
           'shower preparations for dry and pruritic skin conditions as prescribe only in exceptional circumstances, with '
           'the advice to substitute leave-on emollients. It does not list plain leave-on emollients.</p>'
           '<p><b>This ICB\'s own policy: <span class="nv">%s</span>.</b> No Birmingham and Solihull emollient or '
           'self-care policy was found at source this session. Several other ICBs (for example Somerset, Barnsley, '
           'North East London, South West London) publish over-the-counter positions for mild dry skin; each is its own '
           'document. What would settle it: the ICB\'s formulary or Area Prescribing Committee page, or a written answer '
           'from the ICB medicines optimisation team.</p>' % NOT_VERIFIED)

    # ---- cross-ICB ranking
    rows = sorted(D["icbs"].values(), key=lambda x: x["name"])
    def rank_of(key, reverse=False):
        vals = [(c["code"], c[key]) for c in rows if c[key] is not None]
        vals.sort(key=lambda kv: kv[1], reverse=reverse)
        return {c: i + 1 for i, (c, _) in enumerate(vals)}, len(vals)
    r_share, _ = rank_of("share12")
    r_cv, _ = rank_of("pcn_cv", reverse=True)
    imd_rank_pop = [c for c in rows if c["imd"]]
    tr = "".join(
        "<tr%s><td>%s</td><td data-v='%s'>%s</td><td>%s</td><td data-v='%s'>%s</td><td>%s</td><td data-v='%s'>%s</td>"
        "<td data-v='%s'>%s</td><td data-v='%s'>%s</td></tr>" % (
            ' style="background:#F3E9D2"' if c["code"] == code else "",
            e(pretty(c["name"])),
            c["share12"] or "", pcts(c["share12"]), r_share.get(c["code"], ""),
            c["pcn_cv"] if c["pcn_cv"] is not None else "", num(c["pcn_cv"], 2), r_cv.get(c["code"], ""),
            c["imd"]["rank_avg_score"] if c["imd"] else "", (str(c["imd"]["rank_avg_score"]) if c["imd"] else NOT_VERIFIED),
            c["rtt"]["median"] if c["rtt"] else "", num(c["rtt"]["median"], 1) if c["rtt"] else NOT_VERIFIED,
            c["rtt"]["w52"] if c["rtt"] else "", num(c["rtt"]["w52"]) if c["rtt"] else NOT_VERIFIED)
        for c in rows)
    rank_html = ('<div class="scroll"><table id="rank"><tr><th>ICB</th><th>%s share of emollient items</th>'
                 '<th>Rank (1 = lowest share)</th><th>PCN spread (CV)</th><th>Rank (1 = most varied)</th>'
                 '<th>IMD rank of 36 (1 = most deprived)</th><th>Derm median wait (wks)</th><th>Derm 52+ weeks</th></tr>%s</table></div>'
                 '<p class="note">Click a heading to sort. No composite score: the focus is picked by reading the columns, '
                 'not by a formula we invented. IMD is recomputed for the April 2026 ICBs from LSOA data. Share and spread are our definitions (see the spec).</p>'
                 % (e(brand), tr))

    srcs = "".join("<li>%s: %s</li>" % (e(a), e(b)) for a, b in LICENCES)
    body = f"""
<div class="band dark"><div class="col"><div class="eyebrow">Medical Sales Intelligence Hub · starting figures</div>
<h1 contenteditable="true">{e(brand)} — {e(pretty(I['name']))}</h1>
<p>Dermatology emollients, prototype. Built {e(D['generated'])} from open data only. Every figure below is from a named published source; anything that could not be verified is marked <span style="color:#E0BE8E;font-weight:700">Not verified</span>. Every block is editable in your browser, then use Save edited copy.</p>
<p><button id="save">Save edited copy</button></p></div></div>
<div class="band"><div class="col"><div class="eyebrow">1 · National overview</div><h2>England</h2>{nat_html}<p>{nat_rtt}</p>
<p class="note">Market definition: BNF 130201 (emollient preparations) plus appliance section 2122 (emollients). Brand: presentations whose name starts "{e(brand)} ". Items are NHSBSA English Prescribing Dataset, primary care, 12 months to {e(labels[-1])}.</p></div></div>
<div class="band warm"><div class="col"><div class="eyebrow">2 · ICB view</div><h2>Brand share and trend</h2>{icb_html}</div></div>
<div class="band"><div class="col"><div class="eyebrow">3 · Primary Care Networks</div><h2>Where it is prescribed, and how much it varies</h2>{pcn_html}</div></div>
<div class="band warm"><div class="col"><div class="eyebrow">4 · Dermatology waiting times</div><h2>Referral to Treatment</h2>{rtt_html}</div></div>
<div class="band"><div class="col"><div class="eyebrow">5 · Deprivation</div><h2>Index of Multiple Deprivation</h2>{imd_html}</div></div>
<div class="band warm"><div class="col"><div class="eyebrow">6 · Context</div><h2>Moves towards over-the-counter</h2>{otc}</div></div>
<div class="band"><div class="col"><div class="eyebrow">7 · Choosing a focus</div><h2>All ICBs side by side</h2>{rank_html}</div></div>
<div class="band warm"><div class="col"><div class="eyebrow">8 · Your notes</div><h2>Value proposition starting points</h2>
<div class="edit" contenteditable="true">Type here: what the figures say for this ICB, the access barrier, the ask.</div></div></div>
<div class="band"><div class="col"><div class="eyebrow">Sources and licences</div><ul class="note">{srcs}</ul>
<p class="note">PCN prescribing is practice-level NHSBSA data rolled up with the NHS Digital practice-to-PCN mapping; {num(D['unmapped_items'])} market items across the window belong to practices not in today's mapping and are excluded from PCN figures only.</p></div></div>
<script>
document.getElementById('save').onclick=function(){{var h='<!doctype html>'+document.documentElement.outerHTML;
var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([h],{{type:'text/html'}}));a.download='icb-pack-edited.html';a.click();}};
document.querySelectorAll('#rank th').forEach(function(th,i){{th.onclick=function(){{var t=document.getElementById('rank'),
rows=[].slice.call(t.rows,1),asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
rows.sort(function(a,b){{var x=a.cells[i].dataset.v||a.cells[i].textContent,y=b.cells[i].dataset.v||b.cells[i].textContent;
var nx=parseFloat(x),ny=parseFloat(y);var r=(isNaN(nx)||isNaN(ny))?String(x).localeCompare(String(y)):nx-ny;return asc?r:-r;}});
rows.forEach(function(r){{t.tbody.appendChild(r);}});}};}});
</script>"""
    return ("<!doctype html><html lang=\"en-GB\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>ICB pack %s %s</title><style>%s</style></head><body>%s</body></html>" % (e(brand), e(I["name"]), css, body))


def jsonable(D):
    out = dict(D)
    out["pcn"] = {"%s|%s" % k: {kk: (sorted(vv) if isinstance(vv, set) else vv) for kk, vv in d.items()}
                  for k, d in D["pcn"].items() if k[0] == D["icb"]}
    out["brands_in_icb"] = dict(D["brands_in_icb"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--icb", default="QHL", help="NHS ICB code (QHL = Birmingham and Solihull)")
    ap.add_argument("--brand", default="QV")
    ap.add_argument("--cache", default=os.path.join(ROOT, "tmp", "icb-pack-cache"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "icb-pack"))
    ap.add_argument("--refresh", action="store_true", help="re-download every source")
    ap.add_argument("--no-fetch", action="store_true", help="use the cache as it stands")
    a = ap.parse_args(argv)
    if a.brand.upper() != "QV":
        sys.exit("The practice-level query is written for the QV brand prefix only; generalise "
                 "fetch_practice_level before using another brand.")
    idx = json.load(open(os.path.join(GP_DIR, "index.json")))
    if not a.no_fetch:
        fetch_all(a.cache, a.refresh)
        fetch_practice_level(a.cache, idx["periods"], a.refresh)
        fetch_rtt_history(a.cache, a.refresh)
    D = assemble(a.cache, a.icb, a.brand)
    os.makedirs(a.out, exist_ok=True)
    base = os.path.join(a.out, "icb-pack-%s-%s" % (a.icb, a.brand))
    open(base + ".html", "w").write(build_html(D))
    json.dump(jsonable(D), open(base + ".json", "w"), indent=1, default=str)
    print("wrote", base + ".html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
