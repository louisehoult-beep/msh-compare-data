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

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import notice_tags  # noqa: E402  — the canonical speciality vocabulary

DATA = pathlib.Path("data/compare-issues.json")
STATE = pathlib.Path("state/last_run.json")

# The original three keyword sets. KEPT, not replaced: they are matched against
# the full alert text and they cover skin antisepsis, which notice_tags does not
# (SPEC_TERMS was built for Find a Tender procurement titles like "Infection
# Prevention Products", never for "ChloraPrep 2% w/v cutaneous solution").
# Dropping these would lose every chlorhexidine recall in the feed.
KEYWORDS = {
    "vascular": ["iv cannula", "intravenous cannula", "venous cannula", "picc",
                 "midline catheter", "vascular access", "central venous", "cvc",
                 "iv catheter", "catheter securement", "huber", "infusion set",
                 "extension set"],
    "continence": ["foley", "urinary catheter", "intermittent catheter", "urology",
                   "continence", "urine drainage", "sheath", "urethral",
                   "catheter valve", "leg bag", "nephrostomy", "self-retaining catheter"],
    # Brand names added 30/07/2026. Every chlorhexidine notice in the feed to
    # that date named a BRAND and never the molecule, so not one of them reached
    # this speciality: all five were filed elsewhere (four under product-match by
    # the tracked-product path, one under 'theatres' on "procedure pack"), and
    # the Skin Prep panel read empty while it was the richest area in the feed.
    # 'chloraprep', 'frepp' and 'hibiwash' are observed in the live feed;
    # 'hibiscrub' and 'videne' are the other two in routine NHS use.
    "skin-prep": ["chlorhexidine", "skin disinfect", "skin antisep", "antiseptic applicator",
                  "povidone iodine", "skin preparation", "chloraprep", "frepp",
                  "hibiwash", "hibiscrub", "videne", "cutaneous solution"],
}

# --- speciality coverage, widened 29/07/2026 ---------------------------------
# Before this, an alert reached the feed only if it hit one of the three keyword
# sets above or named a tracked supplier product. Everything in the other 30
# canonical specialities was invisible - and so were vascular items whose titles
# say "cannulation" or "cannulas" rather than "IV cannula" (ICN 3421, ICN 3338).
# notice_tags.SPEC_TERMS is the Hub's canonical vocabulary (33 specialities,
# already gated by verify.py against the speciality dropdown), so it is reused
# here rather than a second list being invented.
#
# TWO EVIDENCE RULES, because a loose match here publishes to paying members:
#
# 1. Match the TITLE, never a fetched round-up body. A "Field Safety Notices:
#    13 to 17 July 2026" page lists dozens of unrelated products; matching its
#    body would file one notice under fifteen specialities.
# 2. Strip the manufacturer from MHRA medicines titles before matching. These
#    read "Class N Medicines Recall: <COMPANY>, <PRODUCT>", and a speciality
#    term inside a trading name is not evidence about the product - "Bristol
#    Laboratories" is a penicillin recall, not a pathology notice. Four of ten
#    matches were exactly this before the strip was added.
# --- round-up index pages are never auto-filed, added 30/07/2026 -------------
# gov.uk publishes a weekly "Field Safety Notices: 13 to 17 July 2026" page that
# is an INDEX of dozens of unrelated notices. It names no single product, and it
# never says what any fault was. Until today the fetcher pulled that page's body
# in and matched KEYWORDS against it, so one week-listing was filed as though it
# were one notice about one product: "Field Safety Notices: 13 to 17 July 2026"
# reached the live feed under vascular on the strength of a word buried in a list.
# Three such items were in front of members, were deleted by hand on 29/07, and
# two were re-added by this job the next morning.
#
# A human CAN use these pages — one curated item cites a May 2025 round-up, from
# which a person read out the PowerPICC detail. That is the difference: extracting
# one notice from an index is a judgement, not a match. So automation refuses.
# Plural "Notices" is the discriminator; a single "Field Safety Notice ..." is a
# real notice about a real product and is still filed normally.
ROUNDUP_TITLE = re.compile(r"^\s*field safety notices\b", re.I)


def is_roundup(title):
    return bool(ROUNDUP_TITLE.match(title or ""))


# --- suppression list, added 30/07/2026 --------------------------------------
# The store is append-only AND this job re-reads still-live sources every morning,
# so deleting a false positive by hand buys exactly one day: it is re-detected and
# re-added on the next run, stamped as though it were new, which also re-fires the
# "new items" phone alert. A judgement that a notice does not belong has to live
# somewhere the fetcher reads. That is this file.
#
# It is authoritative in both directions: a suppressed URL is never added, and is
# removed if already present — so a judgement sticks without anyone editing the
# feed by hand. The one thing it will NOT do is destroy human work: an item
# carrying a curated 'use' line is left in place and logged loudly instead.
SUPPRESS_PATH = pathlib.Path("data/suppressed-notices.json")


def suppressed_urls(log):
    try:
        raw = json.loads(SUPPRESS_PATH.read_text())
        urls = {u.rstrip("/") for u in raw.get("urls", {})}
        log.append(f"suppression list: {len(urls)} notice(s) judged out of scope")
        return urls
    except FileNotFoundError:
        return set()
    except Exception as e:
        log.append(f"suppression list FAILED to parse ({e}) — treating as empty")
        return set()


MHRA_MEDICINES_PREFIX = re.compile(
    r"^\s*(class\s*\d\s*medicines?\s*(recall|defect\s*notification)"
    r"|company[- ]led\s*medicines?\s*recall"
    r"|medicines?\s*recall(\s*notification)?)\s*:\s*", re.I)

# When a notice genuinely spans two specialities, the rep's own patch wins.
SPEC_PRIORITY = ["vascular", "continence", "skin-prep"]


def strip_manufacturer(title):
    """'Class 2 Medicines Recall: Acme Laboratories Ltd, Widget 5mg' -> 'Widget 5mg'."""
    m = MHRA_MEDICINES_PREFIX.match(title or "")
    if not m:
        return title or ""
    rest = title[m.end():]
    return rest.split(",", 1)[1].strip() if "," in rest else rest


def canonical_speciality(cand):
    """One speciality id from the canonical vocabulary, or '' if none. Title-only."""
    title = cand.get("title", "")
    if title.lower().startswith("field safety notices"):
        probe = title                      # round-up: never the fetched body
    elif MHRA_MEDICINES_PREFIX.match(title):
        # Product half of the title ONLY. The description restates the company,
        # which would put "Bristol Laboratories" back into the text and refile a
        # penicillin recall as pathology - the exact bug the strip exists to stop.
        probe = strip_manufacturer(title)
    else:
        probe = title + " " + (cand.get("desc") or "")
    specs, _cls = notice_tags.tag(probe)
    if not specs:
        return ""
    for p in SPEC_PRIORITY:
        if p in specs:
            return p
    return sorted(specs)[0]

# Tracked-product matching: an alert naming a product from the supplier seed is
# attached to that supplier automatically ('use' stays human-only; co is flagged
# coAuto so a human can overrule on review).
SEED_PATH = pathlib.Path("data/supplier-seed.json")
PRODUCT_STOP = {"safety", "medical", "surgical", "system", "device", "sterile",
    "products", "range", "series", "clear", "closed", "needlefree", "connector",
    "connectors", "applicator", "dressing", "dressings", "catheter", "catheters",
    "cannula", "syringe", "syringes", "wipes", "gloves", "suture", "sutures",
    "stapler", "haemostat", "hydrogel", "compression", "standard", "premium"}

SUP_STOP = {"medical", "healthcare", "health", "group", "limited", "systems",
    "international", "industries", "surgical", "diagnostics", "pharma", "professional"}

def product_tokens():
    """(product_token, supplier_name, supplier_name_tokens) — a match requires the
    product token AND a supplier-name token, both word-bounded, in the alert text.
    Multi-vendor FSN round-ups are excluded upstream."""
    toks = []
    try:
        seed = json.loads(SEED_PATH.read_text())
        for s in seed.get("suppliers", []):
            sname = s.get("name", "")
            stoks = {w for w in re.findall(r"[a-z0-9]{4,}", (sname + " " + " ".join(s.get("aliases", []) or [])).lower()) if w not in SUP_STOP}
            if not stoks:
                continue
            for p in s.get("products", []):
                name = (p if isinstance(p, str) else p.get("name", "")).strip()
                t = re.sub(r"[^a-z0-9]", "", re.split(r"[\s(/]", name.lower())[0])
                if len(t) >= 5 and t not in PRODUCT_STOP:
                    toks.append((t, sname, stoks))
    except Exception:
        pass
    return toks

def word_hit(tok, hay_plain, hay_dehyph):
    pat = r"(?<![a-z0-9])" + re.escape(tok) + r"(?![a-z0-9])"
    return re.search(pat, hay_plain) is not None or re.search(pat, hay_dehyph) is not None

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
                    "&count=60&fields=title,link,public_timestamp,description")
        for r in json.loads(raw).get("results", []):
            title = r.get("title", "")
            desc = r.get("description") or ""
            link = "https://www.gov.uk" + r.get("link", "")
            ts = r.get("public_timestamp", "")[:10]
            hay = (title + " " + desc).lower()
            # The round-up detail page is deliberately NOT fetched. It used to be,
            # to "match keywords reliably", and that is precisely what filed index
            # pages as though they were single-product notices. Nothing downstream
            # may match on it, so there is no longer any reason to pull it.
            out.append({"title": title, "url": link, "date": ts, "hay": hay,
                        "desc": desc, "src": "MHRA / GOV.UK"})
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
    ptoks = product_tokens()
    log.append(f"tracked-product tokens: {len(ptoks)}")
    for spec in list(KEYWORDS.keys()) + ["product-match"]:
        store["specialities"].setdefault(spec, {"label": spec.replace("-", " ").title(), "issues": []})

    # Suppression is applied to what is already stored BEFORE anything is added,
    # so a judgement made yesterday is honoured today without a hand-edit.
    suppress = suppressed_urls(log)
    # Snapshot before removal: a suppression URL is copied by hand, so it can be
    # copied wrong — a slug rebuilt from a truncated item id rather than read off
    # the item itself cost one silent miss on 30/07/2026. Comparing against the
    # feed as it stood makes a typo visible on the day it is added, not never.
    stored_before = {i.get("url", "").rstrip("/")
                     for b in store["specialities"].values() for i in b.get("issues", [])}
    removed = []
    for sp, blk in store["specialities"].items():
        keep = []
        for it in blk.get("issues", []):
            if it.get("url", "").rstrip("/") in suppress:
                if (it.get("use") or "").strip():
                    # Never destroy a curated line. Somebody wrote this on purpose.
                    log.append(f"SUPPRESSED-BUT-KEPT {sp}: {it.get('url')} carries a human "
                               f"'use' line — left in place, resolve by hand")
                    keep.append(it)
                else:
                    removed.append(f"{sp}: {it.get('p', '')[:70]}")
                continue
            keep.append(it)
        blk["issues"] = keep

    if suppress:
        unmatched = suppress - stored_before
        log.append(f"suppression: {len(suppress) - len(unmatched)} entr(ies) matched a stored "
                   f"item, {len(unmatched)} matched nothing")
        for u in sorted(unmatched):
            log.append(f"  suppression entry matched nothing (already gone, or a typo): {u}")

    added = []
    for c in candidates:
        if c["url"].rstrip("/") in existing_urls:
            continue
        if c["url"].rstrip("/") in suppress:
            continue
        hay_plain = c["hay"]
        hay_dehyph = c["hay"].replace("-", "").replace(" ", "")
        if is_roundup(c["title"]):
            # An index of other people's notices. Never auto-filed. See the note
            # beside ROUNDUP_TITLE: extracting one notice from a round-up is a
            # human judgement, and a match on a word buried in a list is not one.
            continue
        hitco = ""
        for t, sup, stoks in ptoks:
            if word_hit(t, hay_plain, hay_dehyph) and any(word_hit(st, hay_plain, hay_dehyph) for st in stoks):
                hitco = sup; break
        if hitco:
            item = {
                "id": re.sub(r"[^a-z0-9]+", "-", c["url"].lower())[-60:].strip("-"),
                "d": month_label(c["date"]) if c["date"] else month_label(datetime.date.today().isoformat()),
                "co": hitco, "coAuto": True,
                "p": c["title"][:160],
                "s": f"Auto-detected from {c['src']} - names a tracked product. Open the source and verify before use.",
                "use": "",
                "url": c["url"],
                "autoDetected": True,
                "firstSeen": datetime.date.today().isoformat(),
            }
            store["specialities"]["product-match"]["issues"].append(item)
            existing_urls.add(c["url"].rstrip("/"))
            added.append(f"product-match [{hitco}]: {c['title'][:80]}")
            continue
        # Original keyword sets first (matched on the full alert text), then the
        # canonical vocabulary as a fallback for the other 30 specialities.
        spec = next((s for s, kws in KEYWORDS.items()
                     if any(k in c["hay"] for k in kws)), "")
        via = "keywords"
        if not spec:
            spec = canonical_speciality(c)
            via = "canonical"
        if spec:
            store["specialities"].setdefault(
                spec, {"label": spec.replace("-", " ").title(), "issues": []})
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
                # The rule this item was filed under, so a reader can judge it.
                "specVia": via,
            }
            store["specialities"][spec]["issues"].append(item)
            existing_urls.add(c["url"].rstrip("/"))
            added.append(f"{spec} [{via}]: {c['title'][:80]}")

    today = datetime.date.today()
    store["lastChecked"] = today.isoformat()
    store["dataAsOf"] = today.strftime("%d/%m/%Y")
    DATA.write_text(json.dumps(store, indent=1, ensure_ascii=False))
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"run": today.isoformat(), "added": added,
                                 "removed": removed, "log": log}, indent=1))
    print("\n".join(log))
    print(f"added {len(added)} new item(s)")
    for a in added:
        print("  +", a)
    if removed:
        print(f"removed {len(removed)} suppressed item(s)")
        for r in removed:
            print("  -", r)
    return 0

if __name__ == "__main__":
    sys.exit(main())
