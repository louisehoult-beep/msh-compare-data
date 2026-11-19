#!/usr/bin/env python3
"""Lou's six Hub data rulings of 19/11/2026 (^o640 ^o474 ^o643 ^o619 ^o639 ^o651).

Every source below was re-read on 19/11/2026 and, for each framework named, the
NHS Supply Chain contract launch brief was re-read the same day and recorded with
~/.claude/hooks/framework_award_check.py.

^o640  Merge "Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)" into
       "Medfac UK Ltd" (Companies House 08608060). Evidence: kinetecuk.com's own
       footer prints "MedFac UK Ltd ... Company Registration: 08608060"; the
       register returns MEDFAC UK LTD, 08608060, active; NHS Supply Chain's
       Physiotherapy and OT brief names the supplier "Medfac UK Ltd (previously
       Kinetec Medical Products UK Ltd)". KINETEC MEDICAL PRODUCTS UK LIMITED
       (09748313) is a different, active company and is not attached.
^o474  Accoson: use Companies House 00601273 (A. C. COSSOR & SON(SURGICAL)
       LIMITED, active; previous name ACCOSON LTD). The registration number the
       company's website prints is no longer shown anywhere a member reads.
^o643  Vyaire Medical Products Limited (10187476): marked in liquidation, with a
       member-visible alert. Jaeger Medical UK Limited is NOT linked: no source
       read today shows it supplies these frameworks.
^o619  Aquilant Endoscopy: award kept under the name NHS Supply Chain uses, with
       a note that the business is now FUJIFILM Healthcare UK (both companies'
       own FY2025 filings, already recorded on the Fujifilm Healthcare UK record).
^o639  Syringa Wholesale Distributor: held off the Hub (`heldOffHub`, honoured by
       build_supplier_index.py) until Companies House confirms who it is; out of
       the Respiratory Solutions coverage target.
^o651  Respiratory Solutions: add respiratory type `vent` ("Ventilation and
       critical care", from the framework's own Lot 4, Anaesthesia and
       Resuscitation); Hamilton Medical UK's ventilator terms map to it as well
       as anaesthesia:vent, and Hamilton gets a respiratory row.

Idempotent. Run from the repo root, then build_differentiator.py,
build_coverage_ledger.py and verify.py.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from seed_format import write_like  # noqa: E402
import _merge_credenhill_daylong_1117 as M  # noqa: E402

TODAY = "2026-11-19"
RULING = "Lou's ruling, 19/11/2026"
SEED, INDEX = "data/supplier-seed.json", "data/supplier-index.json"


def rd(p):
    return json.load(io.open(p, encoding="utf-8"))


def by_name(doc, name):
    for s in doc.get("suppliers") or []:
        if isinstance(s, dict) and s.get("name") == name:
            return s
    return None


def add_alert(rec, text, kind="supply"):
    rec.setdefault("alerts", [])
    if not any(isinstance(a, dict) and a.get("text") == text for a in rec["alerts"]):
        rec["alerts"].insert(0, {"kind": kind, "text": text})
        return 1
    return 0


# ----------------------------------------------------------------- ^o640 ---
MED_KEEP = "Medfac UK Ltd"
MED_FOLD = "Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)"
MED_NOTE = (
    "MERGED 19/11/2026 on Lou's ruling: the Hub held this one company as two records. "
    "Companies House 08608060 MEDFAC UK LTD, active (read 19/11/2026); the company's own site, "
    "kinetecuk.com, prints \"MedFac UK Ltd, 7 Redan Hill Industrial Estate, Redan Road, Aldershot, "
    "GU12 4SJ\" and \"Company Registration: 08608060\" (read 19/11/2026); NHS Supply Chain's "
    "Physiotherapy and Occupational Therapy brief (2023/S 000-033230) names the supplier "
    "\"Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)\" and its Orthotics, Podiatry and "
    "Immobilisation brief (2024/S 000-019205) names \"Medfac UK Ltd\" (both re-read 19/11/2026). "
    "KINETEC MEDICAL PRODUCTS UK LIMITED (09748313) is a different, active company and is not "
    "attached. Both brief names are kept as aliases."
)


def merge_medfac(path):
    doc = rd(path)
    a, b = by_name(doc, MED_KEEP), by_name(doc, MED_FOLD)
    if a is None:
        print("%s: no %r record — SKIPPED" % (path, MED_KEEP))
        return 0
    if b is None:
        print("%s: Medfac already merged" % path)
        return 0
    for k in ("aliases", "frameworks", "links", "products", "productCategories",
              "specialities", "awards", "news", "alerts"):
        va, vb = a.get(k), b.get(k)
        if va is None and vb is None:
            continue
        a[k] = M.uniq(list(va or []) + list(vb or []))
    # one entry per category (verify.py: seed-product-categories), first source kept
    cats, pcs = set(), []
    for c in a.get("productCategories") or []:
        if c.get("category") in cats:
            continue
        cats.add(c.get("category"))
        pcs.append(c)
    if pcs:
        a["productCategories"] = pcs
    a["aliases"] = M.uniq([MED_KEEP, MED_FOLD, "Kinetec Medical Products UK Ltd", "MedFac UK Ltd",
                           "MEDFAC UK LTD", "Kinetec UK"] + list(a.get("aliases") or []))
    # the folded record's website link duplicates the keep record's proved one
    seen, links = set(), []
    for l in a.get("links") or []:
        host = (l.get("url") or "").lower().replace("https://", "").replace("http://", "") \
            .replace("www.", "").rstrip("/")
        if host in seen:
            continue
        seen.add(host)
        links.append(l)
    a["links"] = links
    prev = [n for n in (a.get("note"), b.get("note")) if n]
    a["note"] = MED_NOTE + ("  Previous \"%s\" record: %s" % (MED_KEEP, prev[0]) if prev else "")
    if len(prev) > 1:
        a["note"] += "  Previous \"%s\" record: %s" % (MED_FOLD, prev[1])
    a["identityNote"] = MED_NOTE
    for k in ("source", "reconciledFrom", "_specialitiesEvidence"):
        if b.get(k) and a.get(k) and b[k] != a[k]:
            a[k] = "%s | from the merged \"%s\" record: %s" % (a[k], MED_FOLD, b[k])
        elif b.get(k) and not a.get(k):
            a[k] = b[k]
    # b's "no Companies House match" note is superseded by a's proved number
    a["mergedFrom"] = M.uniq(list(a.get("mergedFrom") or []) + [MED_FOLD])
    a["verified"] = TODAY
    doc["suppliers"] = [s for s in doc["suppliers"] if s is not b]
    write_like(path, doc)
    print("%s: Medfac merged" % path)
    return 1


def medfac():
    n = merge_medfac(SEED) + merge_medfac(INDEX)
    M.KEEP, M.FOLD, M.NEW = MED_KEEP, MED_FOLD, MED_KEEP
    n += M.patch("data/company-financials.json", lambda d: M.rename_keys(d, ("companies",)))
    n += M.patch("data/company-awards.json",
                 lambda d: M.rename_keys(d, ("companies",), merge_lists=True)
                 + M.rename_values(d.get("companies", {}).get(MED_KEEP) or [], {"company"})
                 + M.fix_count(d, "companies", "companies"))
    n += M.patch("data/company-press.json",
                 lambda d: M.rename_keys(d, ("suppliers",)) + M.fix_count(d, "suppliers", "suppliers"))
    n += M.patch("data/supplier-products.json", lambda d: M.rename_keys(d, ("refusals",)))
    n += M.patch("data/company-logos.json", lambda d: M.rename_values(d.get("logos") or [], {"name"}))
    n += M.patch("data/supplier-careers.json",
                 lambda d: M.rename_values(d.get("suppliers") or [], {"name"}))
    n += M.patch("data/interview-prep.json", lambda d: M.rename_values(d.get("co") or [], {"n"}))
    n += M.patch("data/coverage-ledger.json",
                 lambda d: M.rename_values(d.get("frameworks") or [], {"supplier", "refused"}))
    n += M.patch("data/compare-suppliers.json",
                 lambda d: M.rename_values(d.get("specialities") or {}, {"ref"}))
    n += M.patch("data/innovator-report.json",
                 lambda d: M.rename_values(d.get("specialities") or {}, {"ref", "matchedTo"}))
    n += M.patch("data/hub-search-index.json", M.search_index)
    return n


# ----------------------------------------------------------------- ^o474 ---
COSSOR = "AC Cossor & Son (Surgical) Ltd"
COSSOR_NO = "00601273"
COSSOR_CH = "https://find-and-update.company-information.service.gov.uk/company/00601273"
COSSOR_BRIEF = "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/patient-monitoring-equipment/"
COSSOR_NUMBER_NOTE = (
    "Companies House 00601273, A. C. COSSOR & SON(SURGICAL) LIMITED, active, registered office "
    "Egham TW20 0PB; its register history includes the name ACCOSON LTD (read 19/11/2026). "
    "Recorded on Lou's ruling, 19/11/2026. NHS Supply Chain's Patient Monitoring Equipment brief "
    "names the awardee \"AC Cossor & Son (Surgical) Ltd\" (re-read 19/11/2026). The registration "
    "number printed on the company's own website does not match the register and is not shown."
)


def cossor_record(path):
    doc = rd(path)
    s = by_name(doc, COSSOR)
    if s is None:
        print("%s: no Cossor record" % path)
        return 0
    before = json.dumps(s, sort_keys=True, ensure_ascii=False)
    note = s.get("note") or ""
    cut = note.find("; the company's own site states")
    if cut != -1:
        note = note[:cut] + ". Companies House record 00601273 (A. C. COSSOR & SON(SURGICAL) LIMITED) " \
            "is used, on Lou's ruling, 19/11/2026."
    s["note"] = note
    s["companyNumber"] = COSSOR_NO
    s["companyNumberNote"] = COSSOR_NUMBER_NOTE
    s["verified"] = TODAY
    if json.dumps(s, sort_keys=True, ensure_ascii=False) == before:
        print("%s: Cossor already done" % path)
        return 0
    write_like(path, doc)
    print("%s: Cossor updated" % path)
    return 1


def cossor_overrides(d):
    o = (d.get("overrides") or {}).get(COSSOR)
    if not o or o.get("correct") == COSSOR_NO:
        return 0
    o["exclude"] = ["SC135969"]
    o["excludedName"] = "GM INSTRUMENTS LIMITED, a different company at the Irvine address the website prints"
    o["correct"] = COSSOR_NO
    o["correctSources"] = [COSSOR_CH, COSSOR_BRIEF]
    o["reason"] = ("Lou ruled 19/11/2026 (^o474): use the Companies House record. 00601273, A. C. COSSOR "
                   "& SON(SURGICAL) LIMITED, active, whose register history includes the name ACCOSON "
                   "LTD (read 19/11/2026), matches the awardee NHS Supply Chain's Patient Monitoring "
                   "Equipment brief names, \"AC Cossor & Son (Surgical) Ltd\" (re-read 19/11/2026). The "
                   "number printed on the company's website is not used and not shown. SC135969 (GM "
                   "INSTRUMENTS LIMITED) stays excluded.")
    o["decidedOn"] = TODAY
    o.pop("clearedNote", None)
    return 1


def cossor_financials(d):
    rec = (d.get("companies") or {}).get(COSSOR)
    if not rec or "135969" not in json.dumps(rec):
        return 0
    rec["matchedOn"] = ("Companies House 00601273 (A. C. COSSOR & SON(SURGICAL) LIMITED) recorded on "
                        "Lou's ruling, 19/11/2026; company figures load on the next Companies House refresh.")
    return 1


def cossor():
    n = cossor_record(SEED) + cossor_record(INDEX)
    n += M.patch("data/company-match-overrides.json", cossor_overrides)
    n += M.patch("data/company-financials.json", cossor_financials)
    return n


# ----------------------------------------------------------------- ^o643 ---
VYAIRE = "Vyaire Medical Products Limited"
VYAIRE_ALERT = (
    "In liquidation: Companies House shows VYAIRE MEDICAL PRODUCTS LIMITED (10187476), the company "
    "NHS Supply Chain awarded these frameworks to, in liquidation (read 19/11/2026). Check who now "
    "supplies these products before quoting this company to a customer. Jaeger Medical UK Limited "
    "(01939558, called Vyaire UK 236 Limited 2019 to 2025) is a separate company and is not linked "
    "here until a source shows it supplies these frameworks."
)


def vyaire(path):
    doc = rd(path)
    s = by_name(doc, VYAIRE)
    if s is None:
        return 0
    n = add_alert(s, VYAIRE_ALERT)
    if s.get("companyStatus") != "liquidation":
        s["companyStatus"] = "liquidation"
        s["companyStatusSource"] = {
            "url": "https://find-and-update.company-information.service.gov.uk/company/10187476",
            "readOn": TODAY, "ruling": RULING + " (^o643)"}
        n += 1
    if n:
        write_like(path, doc)
        print("%s: Vyaire marked in liquidation" % path)
    return n


# ----------------------------------------------------------------- ^o619 ---
AQE = "Aquilant Endoscopy Limited"
FUJI = "Fujifilm Healthcare UK"
AQE_ALERT = (
    "The business is now FUJIFILM Healthcare UK. Fujifilm Healthcare UK Limited's FY2025 accounts "
    "(note 22) record its acquisition of Aquilant Endoscopy Limited's endoscopy business, completed "
    "1 December 2025, and Aquilant Endoscopy Limited's own FY2025 strategic report says it ceased to "
    "trade from that date. The NHS Supply Chain awards stay listed here under Aquilant Endoscopy, "
    "because the briefs still name it (ENT Endoscopes and Endoscopy, Endourology and Oncology Ablation "
    "Consumables, both re-read 19/11/2026)."
)
FUJI_ALERT = (
    "Now carries the former Aquilant Endoscopy business (acquired 1 December 2025, per this company's "
    "FY2025 accounts, note 22). The NHS Supply Chain endoscopy awards for that business are still "
    "listed under Aquilant Endoscopy Limited, the name the briefs use (re-read 19/11/2026)."
)


def aquilant(path):
    doc = rd(path)
    n = 0
    a, f = by_name(doc, AQE), by_name(doc, FUJI)
    if a is not None:
        n += add_alert(a, AQE_ALERT)
    if f is not None:
        n += add_alert(f, FUJI_ALERT)
    if n:
        write_like(path, doc)
        print("%s: Aquilant/Fujifilm notes added" % path)
    return n


# ----------------------------------------------------------------- ^o639 ---
SYRW = "Syringa Wholesale Distributor"
HOLD = {
    "since": TODAY, "decisionRef": "^o639", "ruledBy": "Louise Hoult",
    "reason": ("Lou ruled 19/11/2026: keep this name off the Hub until Companies House confirms which "
               "company it is. NHS Supply Chain's Respiratory Solutions brief names \"Syringa Wholesale "
               "Distributor\" (re-read 19/11/2026); no Companies House record matches that name, and it "
               "is not aliased to Syringa UK Ltd (7480088) on resemblance."),
    "liftWhen": "A Companies House record is proved for this name; then remove heldOffHub.",
}


def syringa_seed():
    doc = rd(SEED)
    s = by_name(doc, SYRW)
    if s is None or s.get("heldOffHub") == HOLD:
        return 0
    s["heldOffHub"] = HOLD
    write_like(SEED, doc)
    print("seed: Syringa Wholesale held off the Hub")
    return 1


def syringa_index(d):
    before = len(d.get("suppliers") or [])
    d["suppliers"] = [s for s in d.get("suppliers") or [] if s.get("name") != SYRW]
    n = before - len(d["suppliers"])
    if n and isinstance(d.get("count"), int):
        d["count"] = len(d["suppliers"])
    return n


def syringa_search(d):
    recs = d.get("records") or []
    keep = [r for r in recs if not (isinstance(r, dict) and r.get("c") == "Supplier"
                                    and (r.get("t") or "").strip() == SYRW)]
    n = len(recs) - len(keep)
    d["records"] = keep
    return n


def syringa_exclusion(d):
    ex = d.setdefault("exclusions", [])
    for e in ex:
        if e.get("decisionRef") == "^o639":
            return 0
    ex.append({
        "framework": "Respiratory Solutions", "decisionRef": "^o639", "ruledOn": TODAY,
        "ruledBy": "Louise Hoult", "suppliers": [SYRW],
        "reason": HOLD["reason"] + " Not a coverage target while it is held off the Hub.",
    })
    return 1


def syringa():
    n = syringa_seed()
    n += M.patch(INDEX, syringa_index)
    n += M.patch("data/hub-search-index.json", syringa_search)
    n += M.patch("data/coverage-deferrals.json", syringa_exclusion)
    return n


# ----------------------------------------------------------------- ^o651 ---
VENT_KEY = "vent"
VENT_LABEL = "Ventilation and critical care (Lot 4, Anaesthesia and Resuscitation)"
HAM = "Hamilton Medical UK"
HAM_WHY = ("Ventilator breathing-circuit and flow-sensor items for the HAMILTON ventilator range, by the "
           "catalogue's own descriptions. Also filed under respiratory:vent on Lou's ruling, 19/11/2026 "
           "(^o651): Hamilton is awarded on Respiratory Solutions, whose Lot 4 is Anaesthesia and "
           "Resuscitation.")
HAM_ROW = {
    "co": HAM, "ref": HAM, "brands": "Hamilton", "t": [VENT_KEY],
    "url": "https://www.hamilton-medical.com/en_GB/",
    "note": ("Named on NHS Supply Chain's Respiratory Solutions brief as \"Hamilton Medical Uk Ltd\" "
             "(re-read 19/11/2026). Ventilation specialist; listed under Ventilation and critical care."),
    "iss": [],
}


def vent_compare(d):
    resp = d["specialities"]["respiratory"]
    n = 0
    if VENT_KEY not in resp["types"]:
        resp["types"][VENT_KEY] = VENT_LABEL
        n += 1
    if not any(r.get("ref") == HAM for r in resp["suppliers"]):
        resp["suppliers"].append(dict(HAM_ROW))
        n += 1
    return n


def vent_map(d):
    n = 0
    if VENT_KEY not in d["vocabulary"]["respiratory"]:
        d["vocabulary"]["respiratory"][VENT_KEY] = VENT_LABEL
        n += 1
    for e in d["entries"]:
        if e.get("supplier") == HAM and e.get("hub") == "anaesthesia:vent":
            e["hub"] = ["anaesthesia:vent", "respiratory:" + VENT_KEY]
            e["why"] = HAM_WHY
            e["movedIn"] = "respiratory:vent added %s (scripts/_lou_rulings_1119.py)" % TODAY
            n += 1
    return n


def vent():
    n = M.patch("data/compare-suppliers.json", vent_compare)
    n += M.patch("data/differentiator-category-map.json", vent_map)
    return n


if __name__ == "__main__":
    total = medfac() + cossor() + vyaire(SEED) + vyaire(INDEX) + aquilant(SEED) + aquilant(INDEX) \
        + syringa() + vent()
    print("done: %d change(s)" % total)
