#!/usr/bin/env python3
"""Hospitals inside each NHS trust, for the territory maps and How the NHS Fits Together.

Asked for by Lou on 20/11/2026 after the Meril UK call: a rep covering United Lincolnshire
needs Lincoln County, Pilgrim and Grantham as three accounts, not one trust name.

Source: the NHS Organisation Data Service (ODS) ORD API, Open Government Licence v3.
For every trust in data/trust-map.json we ask ODS for the organisations that hold an
active RE6 ("operated by") relationship to it with primary role RO198 (NHS TRUST SITE).

ODS lists every site a trust runs, often 100+: wards coded as sites, clinics, GP practices
a trust operates, screening centres. A rep wants the hospitals. So:

  * a site is a HOSPITAL when its name carries a hospital word (hospital, infirmary,
    treatment centre, surgical centre, ...) and no department word (surgery, medicine,
    A&E, endoscopy, women and children, ...). "PILGRIM SURGERY" is a department of
    Pilgrim Hospital; "PILGRIM HOSPITAL" is the hospital.
  * hospitals sharing a postcode are one hospital (ODS often files the same building
    twice); the shortest clean name wins.
  * every other site is counted, not listed, so the page can say "and 74 other sites".

Coordinates come from postcodes.io (ONS postcode directory, OGL), one bulk call per 100.

Writes data/trust-sites.json:
  {"asOf", "source", "sourceUrl", "trusts": {CODE: {"name", "hospitals": [{"ods", "name",
   "postcode", "lat", "lng"}], "otherSites": N}}}

Stdlib only. Run: python3 scripts/build_trust_sites.py
"""
import json, os, re, sys, time, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ORD = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
UA = {"User-Agent": "msh-compare-data trust-sites refresh", "Accept": "application/json"}

HOSP = re.compile(r"\b(HOSPITALS?|INFIRMARY|TREATMENT CENTRE|SURGICAL CENTRE|SURGICAL HUB|"
                  r"ELECTIVE (?:CARE |SURGERY |SURGICAL )?CENTRE|CANCER CENTRE|HEART CENTRE|"
                  r"EYE CENTRE|ORTHOPAEDIC CENTRE|DIAGNOSTIC CENTRE|MATERNITY UNIT|"
                  r"COMMUNITY HOSPITAL|BIRTH CENTRE)\b")
DEPT = re.compile(r"\b(SURGERY|MEDICINE|MEDICAL SPECIALTIES|MED SPECIALITIES|A ?& ?E|A AND E|ENDOSCOPY|"
                  r"WOMEN|CHILDREN|ADMISSIONS?|ASSESSMENT|HAEMATOLOGY|ONCOLOGY|WARD|THEATRES?|"
                  r"PHARMACY|DEPARTMENT|DEPT|OUTPATIENTS?|LABORATOR(?:Y|IES)|PATHOLOGY|RADIOLOGY|"
                  r"IMAGING|DIALYSIS|CLINIC|SUITE|WING|BLOCK|LOUNGE|SERVICE|SERVICES|PHYSIOTHERAPY|"
                  r"URGENT TREATMENT|EMERGENCY|MINOR INJUR|DAY CASE|DAY UNIT|HDU|ICU|CCU|SDEC|"
                  r"SCREENING|STORE|STORES|OFFICE|HQ|HEADQUARTERS|RESIDENCES?|ACCOMMODATION|"
                  r"VIRTUAL|LEGACY|(?<!MATERNITY )UNIT|SPIRE|NUFFIELD|NIGHTINGALE|COVID|VACCINATION|BMI|RAMSAY|CIRCLE|DO NOT USE|CLOSED|COST CENTRE|MORTUARY|CHAPEL|CAR PARK)\b")
SMALL = {"and", "of", "the", "for", "on", "upon", "in", "at", "de", "le"}
KEEP_UP = {"NHS", "UCLH", "ENT", "QE", "QEII", "UHB", "UHNM", "CDC"}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception as e:  # ODS rate-limits in bursts; back off and retry
            if i == tries - 1:
                raise
            time.sleep(2 + 3 * i)


def nice(name):
    words = re.split(r"(\s+|-|/)", name.strip())
    out = []
    for i, w in enumerate(words):
        if not w or w.isspace() or w in "-/":
            out.append(w)
            continue
        if w.upper() in KEEP_UP:
            out.append(w.upper())
        elif i and w.lower() in SMALL:
            out.append(w.lower())
        elif "'" in w:
            out.append(w.capitalize())
        elif re.fullmatch(r"[A-Z]{1,2}\d.*|\d.*", w):
            out.append(w)
        else:
            out.append(w.capitalize())
    s = "".join(out).replace(" & ", " and ")
    s = re.sub(r"\bSt\b\.?", "St", s)
    return s


def is_hospital(name):
    n = name.upper().replace("&", " & ")
    return bool(HOSP.search(n)) and not DEPT.search(n)


def sites_for(code):
    q = urllib.parse.urlencode({"RelTypeId": "RE6", "TargetOrgId": code, "RelStatus": "active",
                                "Limit": 1000})   # ODS answers 406 to a PrimaryRoleId filter here; role is checked below
    d = get(f"{ORD}?{q}")
    return [o for o in d.get("Organisations", []) if o.get("Status") == "Active" and o.get("PrimaryRoleId") == "RO198"]


def geocode(postcodes):
    out = {}
    pcs = sorted({p for p in postcodes if p})
    for i in range(0, len(pcs), 100):
        body = json.dumps({"postcodes": pcs[i:i + 100]}).encode()
        req = urllib.request.Request("https://api.postcodes.io/postcodes", data=body,
                                     headers={"Content-Type": "application/json", **UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            for row in json.load(r)["result"]:
                res = row.get("result")
                if res and res.get("latitude") is not None:
                    out[row["query"]] = (round(res["latitude"], 6), round(res["longitude"], 6))
    return out


OUTREACH = re.compile(r"\((?!ACUTE\)|SITE\)|MAIN\))[A-Z]{2,6}\)|\bEPACT\b|OUTPOSTED|REGISTRY|HOSPITAL AT HOME|\bOPD\b|OUT-PATIENTS|- ULHT$|HOSPITALS? AT (?!HOME)|PRIMARY CARE(?! HOSPITAL)")


# Community and mental health trusts often run units inside an acute trust's hospital; the
# hospital itself belongs to the acute trust.
SECONDARY = re.compile(r"COMMUNITY|PARTNERSHIP|MENTAL HEALTH|AMBULANCE|CARE NHS|HEALTHCARE NHS|HUMBER TEACHING", re.I)


SUBSITE = re.compile(r"DENTAL|\bEYE\b|LIAISON|LIASON|\bDAY HOSPITAL|KIDNEY|DIAGNOSTIC|CHILDREN|WOMEN|MATERNITY|CANCER|HEART|BIRTH")
MHWORDS = re.compile(r"MENTAL|PSYCH|CAMHS|LIAISON|RECOVERY|LEARNING DISAB|COMMUNITY|DISTRICT NURS|HEALTH VISIT|DEMENTIA|WELLBEING|ADDICTION|DRUG|ALCOHOL", re.I)


def clean(name):
    n = re.sub(r"\s*\((?:SITE|ACUTE|MAIN)\)|\s+SITE$", "", name.upper().strip())
    return re.sub(r"\s+", " ", n)


def km(a, b):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def pick(sites, code=None):
    """Hospitals, one per postcode and name, plus a count of the rest."""
    by_pc = {}
    at_pc = {}
    for s in sites:
        at_pc[s.get("PostCode")] = at_pc.get(s.get("PostCode"), 0) + 1
    for s in sites:
        if is_hospital(s["Name"]) and not OUTREACH.search(s["Name"].upper()):
            by_pc.setdefault(s.get("PostCode") or s["OrgId"], []).append(s)
    hosp = []
    for pc, group in by_pc.items():
        group.sort(key=lambda s: (not re.search(r"HOSPITAL|INFIRMARY", s["Name"].upper()),
                                  bool(SUBSITE.search(s["Name"].upper())), len(s["Name"]), s["OrgId"]))
        g = group[0]
        hosp.append({"ods": g["OrgId"], "name": nice(clean(g["Name"])), "postcode": g.get("PostCode") or "",
                     "own": bool(code) and g["OrgId"].startswith(code), "npc": at_pc.get(g.get("PostCode"), 1)})
    seen, out = set(), []
    for h in sorted(hosp, key=lambda h: (not h["own"], h["name"])):
        k = re.sub(r"^the |[^a-z]", "", h["name"].lower())
        if k not in seen:
            seen.add(k)
            out.append(h)
    hosp = sorted(out, key=lambda h: h["name"])
    return hosp, len(sites) - sum(len(v) for v in by_pc.values())


def main():
    tm = json.load(open(os.path.join(DATA, "trust-map.json")))
    trusts = {}

    def one(t):
        try:
            return t, sites_for(t["code"])
        except Exception as e:
            print(f"  {t['code']}: ODS failed ({e}); skipped", file=sys.stderr, flush=True)
            return t, None

    cache = os.environ.get("TRUST_SITES_CACHE")
    raw = json.load(open(cache)) if cache and os.path.exists(cache) else None
    if raw is None:
        raw = {}
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as ex:
            for i, (t, sites) in enumerate(ex.map(one, tm["trusts"]), 1):
                if sites is not None:
                    raw[t["code"]] = sites
                if i % 20 == 0:
                    print(f"  {i}/{len(tm['trusts'])}", flush=True)
        if cache:
            json.dump(raw, open(cache, "w"))
    for t in tm["trusts"]:
        if t["code"] in raw:
            hosp, other = pick(raw[t["code"]], t["code"])
            trusts[t["code"]] = {"name": t["n"], "hospitals": hosp, "otherSites": other, "_hq": t.get("postcode")}
    geo = geocode([h["postcode"] for t in trusts.values() for h in t["hospitals"]] + [t["_hq"] for t in trusts.values()])
    # Geography. ODS "operated by" also lists clinics a trust runs inside other trusts' hospitals
    # (Oxford lists University Hospital of Wales). Keep a site the trust codes as its own (code starts
    # with the trust code) within 80 km of the trust's registered address, any other within 30 km,
    # and give a hospital two trusts both claim to the nearer one.
    # Who runs the building. ODS also lists units a trust runs inside another trust's hospital
    # (a mental health liaison team at Pilgrim, a Christie unit at Salford Royal), and trusts that
    # merged keep codes at their old sites. The trust with the most registered sites at a postcode
    # runs it; community and mental health trusts count at 0.4, because their units sit inside
    # acute hospitals far more often than the other way round. Ties go to the nearer head office.
    names = {t["code"]: t["n"] for t in tm["trusts"]}
    weight = {}
    for c, sites in raw.items():
        f = 0.7 if SECONDARY.search(names.get(c, "")) else 1.0
        for s_ in sites:
            pc = s_.get("PostCode")
            if pc:
                weight.setdefault(pc, {})
                weight[pc][c] = weight[pc].get(c, 0) + f
    for c, t in trusts.items():
        hq = geo.get(t["_hq"])
        keep = []
        for h in t["hospitals"]:
            if h["postcode"] in geo:
                h["lat"], h["lng"] = geo[h["postcode"]]
            d = km(hq, (h["lat"], h["lng"])) if hq and "lat" in h else None
            h["_d"] = d if d is not None else 999
            if re.match(r"(IM|GY|JE)\d", h["postcode"]):   # Isle of Man and Channel Islands are not NHS England
                t["otherSites"] += 1
            elif d is None or d <= (80 if h["own"] else 30):
                keep.append(h)
            else:
                t["otherSites"] += 1
        t["hospitals"] = keep
    hosp_pcs = {c: {h["postcode"] for h in t["hospitals"]} for c, t in trusts.items()}

    def overlap(c, name):
        a = set(re.findall(r"[a-z]{4,}", names.get(c, "").lower())) - {"hospital", "hospitals", "trust", "foundation", "university", "teaching", "general"}
        return len(a & set(re.findall(r"[a-z]{4,}", name.lower())))

    def owner(pc, name=""):
        w = weight.get(pc) or {}
        cands = [c for c in w if c in trusts and pc in hosp_pcs.get(c, ())]   # only trusts that name a hospital here
        if not cands:
            return None
        def dist(c):
            hq = geo.get(trusts[c]["_hq"]); g = geo.get(pc)
            return km(hq, g) if hq and g else 999
        return min(cands, key=lambda c: (-w[c], -overlap(c, name), dist(c)))
    moved = {}
    for c, t in trusts.items():
        keep = []
        for h in t["hospitals"]:
            o = owner(h["postcode"], h["name"]) if h["postcode"] else c
            if o in (None, c):
                keep.append(h)
            else:
                t["otherSites"] += 1
                moved.setdefault(o, {}).setdefault(h["postcode"], h)
        t["hospitals"] = keep
    for o, by in moved.items():
        have = {h["postcode"] for h in trusts[o]["hospitals"]}
        for pc, h in by.items():
            if pc not in have:   # the running trust files the building under a non-hospital name
                trusts[o]["hospitals"].append(dict(h))
                have.add(pc)
    for c, t in trusts.items():
        seen, out = set(), []
        for h in sorted(t["hospitals"], key=lambda h: h["name"]):
            k = re.sub(r"^the |[^a-z]", "", h["name"].lower())
            if k not in seen:
                seen.add(k); out.append(h)
        t["hospitals"] = out
        for h in out:
            h.pop("_d", None); h.pop("own", None); h.pop("npc", None)
        t.pop("_hq", None)
    if len(trusts) < 0.9 * len(tm["trusts"]):
        sys.exit(f"Only {len(trusts)} of {len(tm['trusts'])} trusts answered; not writing a partial file.")
    doc = {
        "asOf": datetime.date.today().isoformat(),
        "source": "NHS Organisation Data Service (ODS) ORD API, active NHS trust sites (role RO198) "
                  "operated by each trust; coordinates from postcodes.io (ONS). Open Government Licence v3.",
        "sourceUrl": "https://digital.nhs.uk/services/organisation-data-service",
        "rule": "A hospital is a trust site whose name carries a hospital word and no department word; "
                "sites sharing a postcode count once; a hospital named by more than one trust is listed under the trust "
                "with the most registered sites at that postcode. Every other site is counted in otherSites.",
        "trusts": trusts,
    }
    p = os.path.join(DATA, "trust-sites.json")
    with open(p, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    n = sum(len(t["hospitals"]) for t in trusts.values())
    print(f"trust-sites.json: {len(trusts)} trusts, {n} hospitals")


if __name__ == "__main__":
    main()
