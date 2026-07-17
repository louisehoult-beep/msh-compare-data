#!/usr/bin/env python3
"""Build data/supplier-index.json for the Med Sales Hub supplier-search (WP 677).

Merges three sources into one supplier-keyed index:
  1. data/supplier-seed.json    - CURATED core (human-owned; never overwritten).
  2. data/compare-issues.json   - live recalls/delistings/supply gaps (per supplier).
  3. Contracts Finder OCDS       - medical (CPV 33*) contract AWARDS -> supplier + value.

RULES (do not weaken):
- APPEND-ONLY for auto data. Curated seed fields are sacred and never edited here.
- Auto-added suppliers carry autoDetected=True and "verify at source".
- Any source failure degrades gracefully: log, keep going, exit 0. Stdlib only.
"""
import json, re, sys, urllib.request, datetime, pathlib

DATA_DIR = pathlib.Path("data")
SEED   = DATA_DIR / "supplier-seed.json"
INDEX  = DATA_DIR / "supplier-index.json"
ISSUES = DATA_DIR / "compare-issues.json"
STATE  = pathlib.Path("state") / "supplier_index_last_run.json"
UA = {"User-Agent": "Mozilla/5.0 (msh-compare-data; supplier-index; contact via repo)"}
CF = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search?stages=award&size=100"
MAX_PAGES = 20  # ~2000 award releases scanned per run; medical is ~1%

log = lambda m: print("[supplier-index]", m)

def norm(s): return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()
def norm_co(s):
    n = norm(s)
    return re.sub(r"\b(limited|ltd|plc|uk|u k|gmbh|inc|llc|llp|group|holdings|the)\b", " ", n).strip()

def fetch(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def load(p, default):
    try: return json.loads(p.read_text())
    except Exception: return default

def build_alias_lookup(suppliers):
    lut = {}
    for s in suppliers:
        for a in ([s["name"]] + s.get("aliases", [])):
            lut[norm(a)] = s["name"]; lut[norm_co(a)] = s["name"]
    return lut

def get_or_create(by_name, alias_lut, raw_name):
    """Return the supplier dict for raw_name, creating an auto entry if new."""
    canonical = alias_lut.get(norm(raw_name)) or alias_lut.get(norm_co(raw_name))
    if canonical and canonical in by_name:
        return by_name[canonical]
    name = re.sub(r"\s+", " ", raw_name).strip()
    if name in by_name:
        return by_name[name]
    rec = {"name": name, "aliases": [name], "specialities": [], "frameworks": [],
           "products": [], "alerts": [], "awards": [], "news": [], "note": "",
           "links": [], "curated": False, "autoDetected": True}
    by_name[name] = rec
    alias_lut[norm(name)] = name; alias_lut[norm_co(name)] = name
    return rec

def cpvs(rel):
    out = set(); t = rel.get("tender", {}) or {}
    c = t.get("classification", {}) or {}
    if c.get("id"): out.add(str(c["id"]))
    for i in (t.get("items", []) or []):
        cc = i.get("classification", {}) or {}
        if cc.get("id"): out.add(str(cc["id"]))
        for ac in (i.get("additionalClassifications", []) or []):
            if ac.get("id"): out.add(str(ac["id"]))
    return out

def main():
    seed = load(SEED, {"suppliers": []})
    prev = load(INDEX, {"suppliers": []})
    # start from curated seed; carry forward previously auto-detected entries (append-only)
    by_name = {}
    for s in seed.get("suppliers", []):
        s.setdefault("awards", []); s.setdefault("news", [])
        s["curated"] = True; by_name[s["name"]] = json.loads(json.dumps(s))
    for s in prev.get("suppliers", []):
        if s.get("autoDetected") and s["name"] not in by_name:
            by_name[s["name"]] = s
    alias_lut = build_alias_lookup(by_name.values())

    # ---- 2. recalls/issues from compare-issues.json ----
    added_alerts = 0
    issues = load(ISSUES, {})
    for sp_key, sp in (issues.get("specialities", {}) or {}).items():
        label = sp.get("label", sp_key)
        for iss in sp.get("issues", []):
            co = iss.get("co", "")
            if not co: continue
            rec = get_or_create(by_name, alias_lut, co)
            aid = iss.get("id") or (iss.get("d","")+"|"+iss.get("p","")[:40])
            if not any(a.get("_id") == aid for a in rec["alerts"]):
                rec["alerts"].append({"_id": aid, "date": iss.get("d",""), "title": iss.get("p",""),
                    "detail": iss.get("s",""), "use": iss.get("use",""), "url": iss.get("url",""),
                    "speciality": label, "autoDetected": iss.get("autoDetected", False)})
                added_alerts += 1
            if label not in rec["specialities"]: rec["specialities"].append(label)

    # ---- 3. medical AWARDS from Contracts Finder OCDS (CPV 33*) ----
    added_awards = 0; scanned = 0; pages = 0; url = CF
    try:
        while url and pages < MAX_PAGES:
            data = json.loads(fetch(url)); rels = data.get("releases", [])
            scanned += len(rels); pages += 1
            for r in rels:
                if not any(str(c).startswith("33") for c in cpvs(r)): continue
                t = r.get("tender", {}) or {}
                title = t.get("title", ""); val = ""
                for a in r.get("awards", []):
                    v = (a.get("value", {}) or {}); amt = v.get("amount")
                    if amt: val = "£{:,.0f}".format(amt)
                    adate = (a.get("date") or a.get("contractPeriod", {}).get("startDate") or "")[:10]
                    aurl = ""
                    for doc in (a.get("documents", []) or []):
                        if doc.get("url"): aurl = doc["url"]; break
                    for s in a.get("suppliers", []):
                        nm = s.get("name")
                        if not nm: continue
                        rec = get_or_create(by_name, alias_lut, nm)
                        awid = (title[:50] + "|" + adate)
                        if not any(x.get("_id") == awid for x in rec["awards"]):
                            rec["awards"].append({"_id": awid, "title": title, "value": val,
                                "buyer": (r.get("buyer", {}) or {}).get("name", ""), "date": adate,
                                "url": aurl or "https://www.contractsfinder.service.gov.uk/",
                                "autoDetected": True})
                            added_awards += 1
            nxt = (data.get("links", {}) or {}).get("next")
            url = nxt if nxt and nxt != url else None
    except Exception as e:
        log("awards fetch degraded: %r" % e)

    # ---- write ----
    for rec in by_name.values():
        rec["alerts"].sort(key=lambda a: a.get("date",""), reverse=True)
        rec["awards"].sort(key=lambda a: a.get("date",""), reverse=True)
    out = {"dataAsOf": datetime.date.today().strftime("%d/%m/%Y"),
           "generated": datetime.datetime.utcnow().isoformat()+"Z",
           "note": "Supplier intelligence index for the Hub supplier-search. Curated core + auto-detected award winners (Contracts Finder, medical CPV 33*) and live recalls. Auto entries marked autoDetected - verify at source. Append-only.",
           "suppliers": sorted(by_name.values(), key=lambda s: s["name"].lower())}
    INDEX.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"ran": out["generated"], "suppliers": len(out["suppliers"]),
        "scanned_award_releases": scanned, "added_awards": added_awards, "added_alerts": added_alerts}, indent=1))
    log("suppliers=%d (scanned %d award releases; +%d awards, +%d alerts)" % (len(out["suppliers"]), scanned, added_awards, added_alerts))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        log("FATAL (exit 0 to keep Actions green): %r" % e)
    sys.exit(0)
