#!/usr/bin/env python3
"""Weekly refresh for the Med Sales Hub Compare tab's "live issues".

RULES (do not weaken):
- APPEND-ONLY. Never edit or delete an existing entry. Human-curated fields
  (especially 'use' - the "what this means for a rep" line) are sacred.
- New items carry verbatim titles only, use="" and autoDetected=True.
- Any source failure degrades gracefully: log it, keep going, exit 0.
Stdlib only.
"""
import json, re, sys, urllib.request, datetime, pathlib

DATA = pathlib.Path("data/compare-issues.json")
STATE = pathlib.Path("state/last_run.json")

KEYWORDS = {
    "vascular": ["iv cannula", "intravenous cannula", "venous cannula", "picc",
                 "midline catheter", "vascular access", "central venous", "cvc",
                 "iv catheter", "catheter securement", "huber", "infusion set",
                 "extension set"],
    "continence": ["foley", "urinary catheter", "intermittent catheter", "urology",
                   "continence", "urine drainage", "sheath", "urethral",
                   "catheter valve", "leg bag", "nephrostomy", "self-retaining catheter"],
}

UA = {"User-Agent": "Mozilla/5.0 (msh-compare-data; weekly refresh; contact via repo)"}

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def month_label(iso):
    d = datetime.date.fromisoformat(iso[:10])
    return d.strftime("%b %Y")

def gov_uk_alerts(log):
    """Recent MHRA medical safety alerts via the official GOV.UK search API."""
    out = []
    try:
        raw = fetch("https://www.gov.uk/api/search.json"
                    "?filter_format=medical_safety_alert&order=-public_timestamp"
                    "&count=25&fields=title,link,public_timestamp,description")
        for r in json.loads(raw).get("results", []):
            title = r.get("title", "")
            desc = r.get("description") or ""
            link = "https://www.gov.uk" + r.get("link", "")
            ts = r.get("public_timestamp", "")[:10]
            hay = (title + " " + desc).lower()
            # FSN round-ups need the detail page to match keywords reliably
            if title.lower().startswith("field safety notices"):
                try:
                    hay += " " + re.sub(r"<[^>]+>", " ", fetch(link)).lower()
                except Exception as e:
                    log.append(f"gov.uk detail fetch failed for {link}: {e}")
            out.append({"title": title, "url": link, "date": ts, "hay": hay, "src": "MHRA / GOV.UK"})
        log.append(f"gov.uk: {len(out)} alerts scanned")
    except Exception as e:
        log.append(f"gov.uk FAILED: {e}")
    return out

def nhssc_notices(log):
    """NHS Supply Chain customer notices (ICN) listing scrape."""
    out = []
    try:
        html = fetch("https://www.supplychain.nhs.uk/product-information/customer-notices/")
        seen = set()
        for m in re.finditer(r'href="(https://www\.supplychain\.nhs\.uk/icn/([a-z0-9-]+)/)"[^>]*>([^<]*)<', html):
            url, slug, text = m.group(1), m.group(2), m.group(3).strip()
            if url in seen:
                continue
            seen.add(url)
            title = text if len(text) > 10 else slug.replace("-", " ").title()
            out.append({"title": title, "url": url, "date": "", "hay": (title + " " + slug.replace("-", " ")).lower(), "src": "NHS Supply Chain ICN"})
        log.append(f"nhssc icn: {len(out)} notices scanned")
    except Exception as e:
        log.append(f"nhssc icn FAILED: {e}")
    return out

def main():
    log = []
    store = json.loads(DATA.read_text())
    existing_urls = {i["url"].rstrip("/") for sp in store["specialities"].values() for i in sp["issues"]}

    candidates = gov_uk_alerts(log) + nhssc_notices(log)
    added = []
    for c in candidates:
        if c["url"].rstrip("/") in existing_urls:
            continue
        for spec, kws in KEYWORDS.items():
            if any(k in c["hay"] for k in kws):
                item = {
                    "id": re.sub(r"[^a-z0-9]+", "-", c["url"].lower())[-60:].strip("-"),
                    "d": month_label(c["date"]) if c["date"] else month_label(datetime.date.today().isoformat()),
                    "co": "",  # unverified - human fills on review
                    "p": c["title"][:160],
                    "s": f"Auto-detected from {c['src']} - open the source for details and verify before use.",
                    "use": "",  # SACRED field: only ever written by a human
                    "url": c["url"],
                    "autoDetected": True,
                    "firstSeen": datetime.date.today().isoformat(),
                }
                store["specialities"][spec]["issues"].append(item)
                existing_urls.add(c["url"].rstrip("/"))
                added.append(f"{spec}: {c['title'][:80]}")
                break

    today = datetime.date.today()
    store["lastChecked"] = today.isoformat()
    store["dataAsOf"] = today.strftime("%d/%m/%Y")
    DATA.write_text(json.dumps(store, indent=1, ensure_ascii=False))
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"run": today.isoformat(), "added": added, "log": log}, indent=1))
    print("\n".join(log))
    print(f"added {len(added)} new item(s)")
    for a in added:
        print("  +", a)
    return 0

if __name__ == "__main__":
    sys.exit(main())
