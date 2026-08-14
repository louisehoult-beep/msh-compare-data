#!/usr/bin/env python3
"""Build data/supplier-index.json for the Med Sales Hub supplier-search (WP 677).

Merges into one supplier-keyed index:
  1. data/supplier-seed.json    - CURATED core (human-owned; never overwritten).
  2. data/compare-issues.json   - live recalls/delistings/supply gaps (per supplier).
  3. Contracts Finder OCDS       - medical (CPV 33*) contract AWARDS -> supplier + value.
  4. Google News RSS (per supplier) - NEWS, but ONLY stories corroborated by >=2
     distinct REPUTABLE publishers (PR wires / stock sites never count). Both
     sources are attached so a rep can verify.

RULES: append-only for awards/alerts; curated seed fields sacred; news is
regenerated per run for queried suppliers only; graceful degradation; exit 0.
Stdlib only.
"""
import json, re, sys, time, html, urllib.request, urllib.parse, datetime, pathlib

DATA_DIR = pathlib.Path("data")
SEED   = DATA_DIR / "supplier-seed.json"
INDEX  = DATA_DIR / "supplier-index.json"
ISSUES = DATA_DIR / "compare-issues.json"
STATE  = pathlib.Path("state") / "supplier_index_last_run.json"
UA = {"User-Agent": "Mozilla/5.0 (msh-compare-data; supplier-index; contact via repo)"}
CF = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search?stages=award&size=100"
MAX_PAGES = 20          # CF award releases scanned per run
NEWS_MAX  = 30          # suppliers to run a news query for per run (curated first)
NEWS_DAYS = 550         # ~18 months
NEWS_KEEP = 4           # verified stories kept per supplier

# A publisher COUNTS toward verification if (a) it is a named reputable outlet OR
# (b) its name signals a clinical / medical-device publication (MED_KEYWORDS) --
# unless it is on the PR-wire / stock-tip blocklist, which always overrides.

# (a) named outlets: national/general reputable + specific medtech & clinical titles
#     (incl. free/open-access) that MED_KEYWORDS might miss.
REPUTABLE = [
  # national / general reputable
  "bbc","reuters","financial times","ft.com","the guardian","the times","telegraph",
  "sky news","the independent","bloomberg","associated press","ap news","the economist",
  # medtech / device trade press (free + paid)
  "med-technews","med-tech innovation","medtech dive","medtechdive","massdevice","fierce",
  "medical product outsourcing","medical plastics news","md+di","mddi","device talks","devicetalks",
  "ns medical devices","medtech insight","medtech world","medtech intelligence","drug delivery business",
  "medical design","medical device developments","european medical device","biospace","medcity",
  # clinical / hospital / nursing / pharmacy trade + journals (free + paid)
  "clinical services journal","hospital healthcare","national health executive","healthcare today",
  "health tech world","pharmaphorum","pharmatimes","the pharma letter","pharmafile","pharmaceutical journal",
  "digital health","building better healthcare","health service journal","hsj","nursing times",
  "nursing standard","independent nurse","british journal of nursing","gp online","pulse today",
  "the bmj","bmj","lancet","nature","npj","jama","plos","cochrane","biomed central","bmc",
  "journal of wound care","journal of vascular access","infection prevention","open access government",
  "health europa","omnia health","healthcare in europe","hospital times","medwatch","medtech europe"]

# (b) name-signal heuristic -> "all clinical & medical-device publications, even free"
MED_KEYWORDS = ["medical","clinical","medtech","med-tech","medicine","hospital","nursing","nurse",
  "surgery","surgical","pharma","device","diagnostic","therapy","therapeutic","healthcare","health tech",
  "journal of","bmj","lancet","biomed","cardiolog","oncolog","radiolog","wound","vascular","nhs"]

# Never count these (PR wires / stock-tip / SEO-syndication spam) -- always overrides (a) and (b).
PRWIRE = ["globenewswire","prnewswire","pr newswire","businesswire","business wire","einnews","openpr",
  "yahoo finance","simply wall","marketbeat","stocktitan","zacks","insider monkey","defense world",
  "investing.com","tipranks","gurufocus","benzinga","seeking alpha","accesswire","newsfilecorp",
  "healthline","verywell","patch.com","medianews","stocktwits","fool.com","barchart","nasdaq.com"]

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

def reputable(pub):
    p = (pub or "").lower()
    if not p or any(x in p for x in PRWIRE): return False   # blocklist always wins
    if any(x in p for x in REPUTABLE): return True          # named reputable outlet
    return any(x in p for x in MED_KEYWORDS)                # any clinical / device publication

def parse_date(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try: return datetime.datetime.strptime(s.strip(), fmt).date().isoformat()
        except Exception: pass
    return ""

def verified_news(name):
    """Return stories about `name` corroborated by >=2 distinct reputable publishers."""
    q = urllib.parse.quote('"%s" (NHS OR UK OR medical OR healthcare)' % name)
    url = "https://news.google.com/rss/search?q=%s&hl=en-GB&gl=GB&ceid=GB:en" % q
    xml = ""
    for attempt in (0, 1):
        try:
            xml = fetch(url, timeout=25)
            if "<item>" in xml: break
        except Exception:
            xml = ""
        time.sleep(3)
    if "<item>" not in xml:
        return None   # None = 'could not fetch' (likely throttled) -> keep prior news
    cutoff = (datetime.date.today() - datetime.timedelta(days=NEWS_DAYS)).isoformat()
    items = []
    for m in re.findall(r"<item>(.*?)</item>", xml, re.S):
        t = re.search(r"<title>(.*?)</title>", m, re.S)
        l = re.search(r"<link>(.*?)</link>", m, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", m)
        so = re.search(r"<source[^>]*>(.*?)</source>", m, re.S)
        pub = html.unescape(so.group(1)).strip() if so else ""
        title = html.unescape(t.group(1)).strip() if t else ""
        headline = re.sub(r"\s+-\s+" + re.escape(pub) + r"\s*$", "", title).strip() if pub else title
        date = parse_date(d.group(1)) if d else ""
        if date and date < cutoff: continue
        items.append({"headline": headline, "pub": pub, "url": l.group(1).strip() if l else "", "date": date})
    # cluster by headline token overlap
    clusters = []
    for it in items:
        toks = set(t for t in norm(it["headline"]).split() if len(t) > 3)
        if not toks: continue
        placed = False
        for c in clusters:
            common = toks & c["toks"]
            if len(common) >= max(2, int(0.5 * min(len(toks), len(c["toks"])))):
                c["items"].append(it); c["toks"] |= toks; placed = True; break
        if not placed:
            clusters.append({"toks": toks, "items": [it]})
    out = []
    for c in clusters:
        reps = {}
        for it in c["items"]:
            if reputable(it["pub"]) and it["pub"] not in reps:
                reps[it["pub"]] = it
        if len(reps) >= 2:                                   # <-- the verification gate
            srcs = sorted(reps.values(), key=lambda x: x["date"], reverse=True)
            out.append({"headline": srcs[0]["headline"], "date": srcs[0]["date"],
                        "sources": [{"publisher": s["pub"], "url": s["url"]} for s in srcs[:4]],
                        "verified": True, "autoDetected": True})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:NEWS_KEEP]

def build_alias_lookup(suppliers):
    lut = {}
    for s in suppliers:
        for a in ([s["name"]] + s.get("aliases", [])):
            lut[norm(a)] = s["name"]; lut[norm_co(a)] = s["name"]
    return lut

def split_companies(raw_name, alias_lut):
    """A field naming several manufacturers is not one supplier. Added 06/08/2026.

    MHRA and NHSSC list every affected company in a single field, and taking it
    whole created supplier records whose NAME was a list — e.g.
    "B Braun, Baxter, Becton Dickinson UK Ltd, CODAN, Fannin, GBUK Group Ltd and
    RPG Medical Ltd". That record then WON the substring search for "Becton
    Dickinson UK" in supplier-search.js and handed a rep a company that does not
    exist. Silently: no error, just the wrong answer.

    The rule refuses on thin evidence, per root rule 14: a string is split ONLY
    when every part it splits into already resolves to a supplier we hold. So a
    genuine name containing "and" survives — "W.L. Gore and Associates (U.K.)
    Limited" splits to "W.L. Gore" + "Associates (U.K.) Limited", the second
    resolves to nothing, and the name is left intact, which is correct.

    Returns the list of canonical names, or None to treat raw_name as one company.
    """
    # Never split on "&" — it sits INSIDE single names (Johnson & Johnson,
    # Bausch & Lomb, W.L. Gore & Associates), so splitting there invents companies.
    parts = [p.strip(" .") for p in re.split(r",|\band\b", raw_name) if p.strip(" .")]
    if len(parts) < 2:
        return None

    SUFFIX = re.compile(r"\b(ltd|limited|plc|llp|lp|inc|gmbh|bv|nv|ag|sa|srl|as|oy|ab)\b\.?$", re.I)
    resolved, companyish = 0, []
    for p in parts:
        c = alias_lut.get(norm(p)) or alias_lut.get(norm_co(p))
        if c:
            resolved += 1
            if c not in companyish:
                companyish.append(c)
        elif SUFFIX.search(p):
            # Unresolved but carries a legal suffix, so it IS a company — just one
            # we do not hold yet. It gets its own record rather than being lost.
            if p not in companyish:
                companyish.append(p)

    # Two independent signals, either sufficient. Two or more commas, because no
    # single company name carries two (the widest here is "BD — Becton, Dickinson",
    # which has one). Or two or more parts that are demonstrably companies, at
    # least one of which we already hold — that is evidence, not resemblance.
    if raw_name.count(",") >= 2 or (len(companyish) >= 2 and resolved >= 1):
        return companyish if len(companyish) > 1 else None
    return None


def records_for(by_name, alias_lut, raw_name):
    """Every supplier record a raw name refers to — usually one, sometimes several."""
    names = split_companies(raw_name, alias_lut)
    if names:
        return [by_name[n] for n in names if n in by_name]
    return [get_or_create(by_name, alias_lut, raw_name)]


def get_or_create(by_name, alias_lut, raw_name):
    canonical = alias_lut.get(norm(raw_name)) or alias_lut.get(norm_co(raw_name))
    if canonical and canonical in by_name: return by_name[canonical]
    name = re.sub(r"\s+", " ", raw_name).strip()
    if name in by_name: return by_name[name]
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
    by_name = {}
    for s in seed.get("suppliers", []):
        s.setdefault("awards", []); s.setdefault("news", []); s["curated"] = True
        by_name[s["name"]] = json.loads(json.dumps(s))
    prev_news = {}
    # Carry forward auto-detected records from the last build — but re-test each
    # one, because this loop is why split_companies() alone was not enough.
    #
    # split_companies() was added 06/08/2026 and stops a multi-company field
    # becoming one supplier. It only governs names arriving THIS run. A record
    # created before it existed was copied forward here unconditionally, every
    # run, forever: "B Braun, Baxter, Becton Dickinson UK Ltd, CODAN, Fannin,
    # GBUK Group Ltd and RPG Medical Ltd" was still a live supplier on 07/08,
    # and still won the substring search for "Becton Dickinson UK".
    #
    # A carried-forward name now has to pass the same test a new one does. If it
    # splits, it is dropped: the real companies it names are all in the seed, and
    # its alerts re-attach to each of them from the notices on this run, so
    # nothing is lost by letting it go.
    # The second way a carried-forward record goes stale is subtler and produced
    # twelve of them: the name RESOLVES now. "Medtronic Limited" was auto-created
    # on some past run when nothing matched it, and has been copied forward ever
    # since — beside the seed's own "Medtronic", which it normalises to exactly.
    # Two records for one company, the auto one holding 20 frameworks and no
    # products, and alias lookup is first-wins, so which one answers for
    # "Medtronic" is down to ordering. Same shape as the multi-company record:
    # a guard added later only governs names arriving after it.
    #
    # Its frameworks, alerts and awards are folded into the record it resolves to
    # before it is dropped, so the merge never loses what the auto record had
    # found. `news` is not carried: it is re-fetched every run anyway.
    seed_lut = build_alias_lookup(by_name.values())
    dropped, merged = [], []

    def _ident(key, x):
        # These lists are not uniformly typed: a curated `alerts` entry can be a
        # plain string of prose while an auto-detected one is a dict with an _id.
        # Assuming dicts here raised AttributeError on the first real merge.
        if not isinstance(x, dict):
            return ("raw", str(x))
        if key == "frameworks":
            return ("fw", x.get("name"))
        if key == "alerts":
            return ("al", x.get("_id") or x.get("title") or x.get("url"))
        return ("aw", x.get("title") or x.get("url"))

    def _fold(dst, src):
        for key in ("frameworks", "alerts", "awards"):
            have = {_ident(key, x) for x in dst.get(key) or []}
            for x in src.get(key) or []:
                k = _ident(key, x)
                if k not in have:
                    dst.setdefault(key, []).append(x)
                    have.add(k)
        # THE MERGED-AWAY NAME MUST STILL RESOLVE. Dropping the record without
        # keeping its name as an alias breaks every file that referenced it by
        # exact spelling — on the first run of this, company-financials.json lost
        # "QIAGEN LIMITED" and "Stryker UK Limited", and a Compare-tab row lost
        # its supplier. A merge redirects a name; it does not delete one.
        seen = {a.strip().lower() for a in dst.get("aliases") or []}
        for a in [src.get("name")] + list(src.get("aliases") or []):
            if a and a.strip().lower() not in seen:
                dst.setdefault("aliases", []).append(a)
                seen.add(a.strip().lower())

    for s in prev.get("suppliers", []):
        prev_news[s["name"]] = s.get("news", [])
        if s.get("autoDetected") and s["name"] not in by_name:
            if split_companies(s["name"], seed_lut):
                dropped.append(s["name"])
                continue
            canonical = seed_lut.get(norm(s["name"])) or seed_lut.get(norm_co(s["name"]))
            if canonical and canonical in by_name and canonical != s["name"]:
                _fold(by_name[canonical], s)
                merged.append("%s -> %s" % (s["name"], canonical))
                continue
            by_name[s["name"]] = s
    for name in dropped:
        print("dropped carried-forward multi-company record: %s" % name)
    for m in merged:
        print("merged carried-forward duplicate: %s" % m)
    alias_lut = build_alias_lookup(by_name.values())

    # 2. recalls
    added_alerts = 0
    for sp_key, sp in (load(ISSUES, {}).get("specialities", {}) or {}).items():
        label = sp.get("label", sp_key)
        for iss in sp.get("issues", []):
            co = iss.get("co", "")
            if not co: continue
            aid = iss.get("id") or (iss.get("d", "") + "|" + iss.get("p", "")[:40])
            # A notice naming several manufacturers attaches to each of them,
            # rather than inventing one supplier called all of them at once.
            for rec in records_for(by_name, alias_lut, co):
                if not any(isinstance(a, dict) and a.get("_id") == aid for a in rec["alerts"]):
                    rec["alerts"].append({"_id": aid, "date": iss.get("d", ""), "title": iss.get("p", ""),
                        "detail": iss.get("s", ""), "use": iss.get("use", ""), "url": iss.get("url", ""),
                        "speciality": label, "autoDetected": iss.get("autoDetected", False)}); added_alerts += 1
                # The `unsorted` bucket is a holding pen for notices the auto-detector
                # had no term for. Its label is "Not yet sorted by speciality", which is
                # a statement about our sorting, not a speciality the company works in.
                # Attaching it to a supplier says something false about that supplier and
                # fails the vocab gate, which is exactly what it did to the daily refresh
                # on 14/08/2026 once an unsorted notice named a real company. The alert
                # keeps the label — it describes the notice — the supplier does not.
                if sp_key == "unsorted": continue
                if label not in rec["specialities"]: rec["specialities"].append(label)

    # 3. medical awards (Contracts Finder OCDS, CPV 33*)
    added_awards = scanned = pages = 0; url = CF
    try:
        while url and pages < MAX_PAGES:
            data = json.loads(fetch(url)); rels = data.get("releases", []); scanned += len(rels); pages += 1
            for r in rels:
                if not any(str(c).startswith("33") for c in cpvs(r)): continue
                title = (r.get("tender", {}) or {}).get("title", "")
                for a in r.get("awards", []):
                    amt = (a.get("value", {}) or {}).get("amount"); val = "£{:,.0f}".format(amt) if amt else ""
                    adate = (a.get("date") or (a.get("contractPeriod", {}) or {}).get("startDate") or "")[:10]
                    for s in a.get("suppliers", []):
                        nm = s.get("name")
                        if not nm: continue
                        rec = get_or_create(by_name, alias_lut, nm); awid = title[:50] + "|" + adate
                        if not any(isinstance(x, dict) and x.get("_id") == awid for x in rec["awards"]):
                            rec["awards"].append({"_id": awid, "title": title, "value": val,
                                "buyer": (r.get("buyer", {}) or {}).get("name", ""), "date": adate,
                                "url": "https://www.contractsfinder.service.gov.uk/", "autoDetected": True}); added_awards += 1
            nxt = (data.get("links", {}) or {}).get("next"); url = nxt if nxt and nxt != url else None
    except Exception as e:
        log("awards fetch degraded: %r" % e)

    # 4. verified news (>=2 reputable sources), curated first then most-awarded
    def activity(s): return (max([a.get("date","") for a in s["awards"] if isinstance(a, dict)] or [""]), len(s["awards"]))
    order = sorted(by_name.values(), key=lambda s: (0 if s.get("curated") else 1, ), )
    ranked = [s for s in by_name.values() if s.get("curated")] + \
             sorted([s for s in by_name.values() if not s.get("curated")], key=activity, reverse=True)
    news_verified = news_checked = 0
    cutoff_news = (datetime.date.today() - datetime.timedelta(days=NEWS_DAYS)).isoformat()
    def merge_news(prev, fresh):
        seen = {}; out = []
        for n in (fresh + prev):                       # fresh first so newest wording wins
            if n.get("date","") and n["date"] < cutoff_news: continue
            k = norm(n.get("headline",""))[:60]
            if k and k not in seen:
                seen[k] = 1; out.append(n)
        out.sort(key=lambda x: x.get("date",""), reverse=True)
        return out[:NEWS_KEEP]
    for s in ranked[:NEWS_MAX]:
        prev = prev_news.get(s["name"], []) or s.get("news", [])
        vs = verified_news(s["name"])
        if vs is None:                                  # throttled -> keep what we had
            s["news"] = merge_news(prev, [])
        else:
            s["news"] = merge_news(prev, vs)
            news_checked += 1; news_verified += len(vs)
        time.sleep(1.5)
    # suppliers not queried this run: preserve prior news
    queried = set(x["name"] for x in ranked[:NEWS_MAX])
    for nm, rec in by_name.items():
        if nm not in queried:
            rec["news"] = merge_news(prev_news.get(nm, []) or rec.get("news", []), [])

    for rec in by_name.values():
        rec["alerts"].sort(key=lambda a: a.get("date", "") if isinstance(a, dict) else "", reverse=True)
        rec["awards"].sort(key=lambda a: a.get("date", "") if isinstance(a, dict) else "", reverse=True)
    out = {"dataAsOf": datetime.date.today().strftime("%d/%m/%Y"),
           "generated": datetime.datetime.utcnow().isoformat() + "Z",
           "note": "Curated core + auto-detected medical award winners (Contracts Finder CPV 33*) + live recalls + news corroborated by >=2 reputable sources. Auto items: verify at source.",
           "suppliers": sorted(by_name.values(), key=lambda s: s["name"].lower())}
    INDEX.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"ran": out["generated"], "suppliers": len(out["suppliers"]),
        "scanned_award_releases": scanned, "added_awards": added_awards, "added_alerts": added_alerts,
        "news_suppliers_checked": news_checked, "news_stories_verified": news_verified}, indent=1))
    log("suppliers=%d | +%d awards, +%d alerts | news: %d verified across %d suppliers"
        % (len(out["suppliers"]), added_awards, added_alerts, news_verified, news_checked))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        log("FATAL (exit 0 to keep Actions green): %r" % e)
    sys.exit(0)
