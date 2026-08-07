#!/usr/bin/env python3
"""Capture NHS Supply Chain frameworks AND their full awarded-supplier lists from
NHS Supply Chain's own Contract Launch Briefs.

WHY THIS EXISTS
---------------
Framework membership in supplier-index.json was hand-curated and badly incomplete:
on 06/08/2026, GBUK Group carried 2 frameworks while NHSSC's own Advanced Wound Care
brief names "GBUK Ltd" among 56 awarded suppliers, and 148 of 459 suppliers carried no
framework at all. That is not a cosmetic gap: the Company Report derives its competitor
panels from framework co-listing, so an incomplete framework list produces an
incomplete competitor list, which is a wrong answer wearing a confident face.

THE SOURCE, AND WHY IT IS THE RIGHT ONE
---------------------------------------
NHS Supply Chain publishes a Contract Launch Brief per framework at
/product-information/contract-launch-brief/<slug>/. Each brief is the buying
organisation's OWN page for that framework and names, in its own words: the framework
reference, the contract start and end dates, and every awarded supplier. That is a
primary source for the exact claim being made (root rule 16), not trade coverage of one.

WHAT THIS SCRIPT WILL NOT DO
----------------------------
- It never infers membership. A supplier is on a framework only if that framework's own
  brief names it. No name-similarity guessing beyond the explicit alias table in the
  repo's supplier data, and every match records the verbatim string it matched.
- It never invents dates or references. A brief that does not state them yields null,
  and the report prints the absence rather than a plausible-looking blank.
- Frameworks whose brief cannot be parsed are recorded in `unparsed` WITH the reason and
  are never silently dropped — a missing framework is the failure mode this whole script
  exists to fix, so it must be visible.

Output: data/frameworks.json  (needs a marker ref in scripts/stamp_notice.py REFS)
Run:    python3 scripts/refresh_frameworks.py [--limit N] [--out PATH]
"""
import argparse
import html as H
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request

INDEX = "https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/"
INDEX_PAGE = INDEX + "page/%d/"
BRIEF_RE = re.compile(
    r'href="(https://www\.supplychain\.nhs\.uk/product-information/contract-launch-brief/[^"#?]+)"')
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
PAUSE = 1.0          # be a good citizen; this is somebody else's website
MAX_INDEX_PAGES = 12


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < tries - 1:
                time.sleep(3)
                continue
            raise
    return ""


def text_of(fragment):
    """HTML fragment -> plain text, with block tags becoming separators."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return H.unescape(s)


def find_briefs():
    urls = set()
    for page in range(1, MAX_INDEX_PAGES + 1):
        url = INDEX if page == 1 else INDEX_PAGE % page
        try:
            h = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            raise
        found = set(BRIEF_RE.findall(h))
        if not found:
            break
        before = len(urls)
        urls |= found
        if len(urls) == before and page > 1:
            break                      # pagination looping back on itself
        time.sleep(PAUSE)
    return sorted(urls)


# Some briefs decorate each name with its award status. That is a fact about the
# award round, not part of the company's name, and leaving it in means the name
# never matches the company on the register.
AWARD_TAIL = re.compile(
    r"(?i)\s*[–—-]\s*(new|incumbent|delisted|re-?awarded)"
    r"(\s+to\s+(the\s+)?(framework|nhs supply chain))?\s*$")


def clean_supplier(name):
    s = " ".join(name.split()).strip(" .;·•")
    prev = None
    while prev != s:
        prev = s
        s = AWARD_TAIL.sub("", s).strip(" .;·•–—-")
    if len(s) < 2 or len(s) > 120:
        return ""
    if not re.search(r"[A-Za-z]{2}", s):
        return ""
    return s


def parse_suppliers(h):
    """Return (suppliers, note) or ([], reason).

    The briefs carry a `<div id="suppliers">` section that STATES ITS OWN COUNT
    ("There are 56 suppliers on this framework. They are:") above a plain <ul>.
    That stated number is the invariant this parser is built around: if the list
    parsed does not match the count the page itself gives, the framework is
    refused rather than published short. A framework list that is quietly one
    supplier short is exactly the defect this script was written to remove, so
    it must never be able to reappear as a silent success.
    """
    m = re.search(r'(?is)<div[^>]+id="suppliers".*?(?=<div[^>]+id="(?!suppliers)|<footer|</body)', h)
    if not m:
        return [], "no #suppliers section on the page", {}
    block = m.group(0)

    # The count sentence is the anchor. Take the FIRST list after it and nothing
    # else: the section also carries downloads and navigation lists, and sweeping
    # up every <li> in the section is how a supplier count comes out too high.
    stated = None
    sm = re.search(r"(?is)there\s+are\s*(?:<[^>]+>)?\s*([\d,]+)\s*(?:</[^>]+>)?\s*supplier", block)
    if sm:
        stated = int(sm.group(1).replace(",", ""))
        after = block[sm.end():]
    else:
        # Single-supplier frameworks are stated in prose and carry no list at all:
        # "There is one supplier on this framework: Primel Corporation Ltd."
        one = re.search(r"(?is)there\s+is\s+(?:only\s+)?one\s+supplier[^:]{0,60}:\s*([^<\n\.]{3,90})", block)
        if one:
            name = clean_supplier(text_of(one.group(1)))
            if name:
                return [name], "single-supplier framework, stated in prose on the page", {}
        after = block

    # Many briefs open the section with a SUMMARY list — "14 suppliers are
    # incumbent / 7 are new / 1 has been delisted" — before the real lists, and
    # then say "This is the full list of suppliers available on this framework:".
    # Counting the summary bullets as suppliers is how a 21-supplier framework
    # parses to 24. Anchor past that sentence where the page provides it.
    fl = re.search(r"(?is)(?:this is the )?full list of suppliers[^:]{0,80}:", after)
    if fl:
        after = after[fl.end():]

    # Long lists are laid out in COLUMNS — several <ul> blocks that together make
    # the stated total. Accumulate list by list and stop the moment the running
    # total equals the number the page itself gives; anything after that belongs
    # to a different list (downloads, related links) and must not be swept in.
    def collect(scope):
        """Names from the supplier lists in `scope`, stopping the moment the
        running total equals the count the page states."""
        got, seen_l, hit = [], set(), False
        for chunk in re.findall(r"(?is)<ul[^>]*>(.*?)</ul>", scope):
            raws = re.findall(r"(?is)<li[^>]*>(.*?)</li>", chunk)
            plain = [" ".join(text_of(r).split()) for r in raws]
            summaryish = sum(1 for x in plain
                             if re.match(r"(?i)^\d+\s+suppliers?\b", x)
                             or re.search(r"(?i)suppliers? (?:are|has been|have been|is)\b", x))
            if plain and summaryish >= max(1, len(plain) // 2):
                continue
            for raw in raws:
                x = clean_supplier(text_of(raw))
                if x and x.lower() not in seen_l:
                    seen_l.add(x.lower())
                    got.append(x)
            if stated is not None and len(got) == stated:
                hit = True
                break
        return got, hit

    out, matched = collect(after)
    if stated is not None and not matched and after is not block:
        # The count sentence is not always ABOVE the lists — on some briefs it
        # sits below them, so starting after it skipped the first list entirely
        # (Aids for Daily Living parsed 19 of 31 that way). Retry over the whole
        # section before giving up.
        whole, hit = collect(block)
        if hit:
            out, matched = whole, True

    # A third layout states the field as a TABLE with a Lot column — one row per
    # supplier per lot. Distinct suppliers must still match the page's own count;
    # the lots are kept because "which lot" is the question a rep actually asks.
    if not out:
        lots = {}
        for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", after):
            cells = [" ".join(text_of(c).split())
                     for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row)]
            if len(cells) < 2:
                continue
            lot, name = "", ""
            for c in cells:
                lm2 = re.match(r"(?i)^(lot\s+[\w\d]+)\s*:?\s*(.*)$", c)
                if lm2:
                    lot = lm2.group(1).title()
                    if lm2.group(2).strip():
                        name = clean_supplier(lm2.group(2))
                    break
            if not name:
                cand = [c for c in cells if not re.fullmatch(r"(?i)[yn]|yes|no|-|", c.strip())
                        and not re.match(r"(?i)^lot\b", c)]
                name = clean_supplier(cand[0]) if cand else ""
            if not name or re.fullmatch(r"(?i)supplier|lot|npm|bulk buy", name):
                continue
            lots.setdefault(name, set())
            if lot:
                lots[name].add(lot)
        if lots:
            out = list(lots.keys())
            if stated is not None and len(out) != stated:
                return [], ("the page's lot table gives %d distinct suppliers but it states %d — "
                            "refusing rather than publishing a list that does not match the page"
                            % (len(out), stated)), {}
            note = "read from the page's lot table; %d distinct suppliers" % len(out)
            if stated is not None:
                note += ", count verified against the page's own stated total"
            return out, note, {n: sorted(v) for n, v in lots.items() if v}

    if not out:
        # Single-supplier frameworks are stated in prose. This runs as a FALLBACK
        # too, not only when there is no count sentence, because some briefs say
        # "There are 1 suppliers ... :" and then name the one in the sentence.
        one = re.search(r"(?is)there\s+(?:is|are)\s+(?:only\s+)?(?:one|1)\s+supplier[^:]{0,80}:\s*([^<\n]{3,90})", block)
        if one:
            name = clean_supplier(text_of(one.group(1)))
            if name:
                return [name], "single-supplier framework, stated in prose on the page", {}
        # Distinguish the two very different refusals, because they need
        # different fixes: a page that never publishes its supplier names cannot
        # be parsed harder, while a page that contradicts its own count is a
        # page to read by hand.
        has_any_list = bool(re.search(r"(?is)<ul[^>]*>|<table", block))
        if not has_any_list:
            return [], ("the page states its supplier count but publishes no list of names "
                        "(no list or table in the Suppliers section) — this framework cannot be "
                        "captured from this source"), {}
        return [], "no supplier list found after the count sentence", {}
    if stated is None:
        return out, "no stated count on the page; %d names parsed (UNVERIFIED COUNT)" % len(out), {}
    if not matched:
        return [], ("the page states %d suppliers but %d were parsed — refusing rather than "
                    "publishing a list that does not match the page" % (stated, len(out))), {}
    return out, "count verified against the page's own stated total (%d)" % stated, {}


# The header block runs the fields together as one line — "Type: New Contract
# Category: ... Reference: ... Supply Route: ... Start Date: ... Expiry Date: ...".
# Each value therefore has to stop at the NEXT KNOWN LABEL, not at the next
# capitalised word, or "Stocked, eDirect" swallows "Start Date" behind it.
LABELS = ("Type", "Category", "Reference", "Supply Route", "Start Date",
          "Expiry Date", "Contract Type", "Framework Reference")


def _labelled(text, label):
    others = "|".join(re.escape(l) for l in LABELS if l != label)
    m = re.search(r"(?i)\b" + re.escape(label) + r"\s*:\s*(.+?)\s*(?=\b(?:" + others + r")\s*:|$)", text)
    if not m:
        return None
    val = " ".join(m.group(1).split())
    # Expiry Date is the last field in the header run, so its match continues into
    # the page's prose. A date field is a date: take it and stop.
    if "date" in label.lower():
        dm = re.match(r"(\d{1,2}\s+\w+\s+20\d\d)", val)
        return dm.group(1) if dm else None
    return val[:120] or None


def parse_brief(url, h):
    text = " ".join(text_of(h).split())
    title = ""
    m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", h)
    if m:
        title = " ".join(text_of(m.group(1)).split())
    if not title:
        m = re.search(r"(?is)<title[^>]*>(.*?)</title>", h)
        title = " ".join(text_of(m.group(1)).split()).split("|")[0].strip() if m else ""

    ref = _labelled(text, "Reference")
    if ref and not re.search(r"\d", ref):
        ref = None

    suppliers, how, lots = parse_suppliers(h)
    return {
        "name": title,
        "url": url,
        "type": _labelled(text, "Type"),
        "category": _labelled(text, "Category"),
        "reference": ref,
        "supplyRoute": _labelled(text, "Supply Route"),
        "starts": _labelled(text, "Start Date"),
        "ends": _labelled(text, "Expiry Date"),
        "suppliers": suppliers,
        "supplierSource": how if suppliers else None,
        "supplierCount": len(suppliers),
        "supplierLots": lots or None,
        "_refusal": None if suppliers else how,
    }


def _end_date(text):
    """The framework's end date, or None when the brief does not give a readable one."""
    t = str(text or "").strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="data/frameworks.json")
    ap.add_argument("--urls", default="")
    args = ap.parse_args()

    urls = ([u.strip() for u in open(args.urls) if u.strip()] if args.urls else find_briefs())
    if args.limit:
        urls = urls[:args.limit]
    if not urls:
        sys.exit("No contract launch briefs found. The index page shape may have changed — "
                 "fix the crawler rather than shipping an empty framework file.")

    frameworks, unparsed = [], []
    for i, u in enumerate(urls, 1):
        try:
            rec = parse_brief(u, get(u))
        except Exception as exc:
            unparsed.append({"url": u, "reason": "fetch or parse error: %s" % exc})
            continue
        refusal = rec.pop("_refusal", None)
        if rec["suppliers"]:
            frameworks.append(rec)
        else:
            unparsed.append({"url": u, "name": rec["name"],
                             "reason": refusal or "no supplier list found"})
        if i % 10 == 0:
            print("  ...%d/%d" % (i, len(urls)), file=sys.stderr)
        time.sleep(PAUSE)

    # EXPIRED BRIEFS ARE NOT A ROUTE TO MARKET. NHS Supply Chain leaves a brief
    # published after its framework ends, so a straight capture of the index
    # keeps returning them: on 07/08/2026 three were in the file, one 515 days
    # past its end date, and 24 supplier rows across the seed and the index
    # showed them under "Frameworks on" with the dates printed and nothing else.
    # Medtronic, Boston Scientific and Abbott all read as current on a
    # Transcatheter Heart Valve framework that stopped in September 2025.
    #
    # They are moved to `expired` rather than dropped: the brief is real, it was
    # correctly captured, and knowing a framework has just ended is useful — it
    # is usually the moment incumbency resets. What it is not is somewhere to
    # sell today, so it must not sit in the list every consumer reads as live.
    # A brief with no readable end date STAYS in `frameworks`: refusing on an
    # unparseable date would silently drop live frameworks.
    expired = []
    live = []
    today = datetime.date.today()
    for rec in frameworks:
        end = _end_date(rec.get("ends"))
        if end and end < today:
            rec = dict(rec, endedOn=end.isoformat())
            expired.append(rec)
        else:
            live.append(rec)
    frameworks = live
    expired.sort(key=lambda r: r["name"].lower())
    for rec in expired:
        print("expired, moved out of frameworks: %s (ended %s)" % (rec["name"], rec.get("ends")),
              file=sys.stderr)

    frameworks.sort(key=lambda r: r["name"].lower())
    doc = {
        "dataAsOf": time.strftime("%Y-%m-%d"),
        "source": "NHS Supply Chain Contract Launch Briefs "
                  "(https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/), "
                  "each framework's own page, fetched this run.",
        "rule": "A supplier appears under a framework here ONLY because that framework's own "
                "NHS Supply Chain brief names it. Nothing is inferred from product ranges, "
                "specialities or catalogue categories. Frameworks whose brief could not be "
                "parsed are listed in `unparsed` with the reason and are NOT silently dropped.",
        "briefsSeen": len(urls),
        "frameworkCount": len(frameworks),
        "unparsedCount": len(unparsed),
        "expiredCount": len(expired),
        "expiredRule": "A brief whose framework has already ended is captured but kept OUT of "
                       "`frameworks`, because every consumer reads that list as live routes to "
                       "market. NHS Supply Chain leaves briefs published after they end. A brief "
                       "with no readable end date stays in `frameworks` rather than being dropped.",
        "frameworks": frameworks,
        "expired": expired,
        "unparsed": unparsed,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("Wrote %s — %d frameworks, %d unparsed, from %d briefs."
          % (args.out, len(frameworks), len(unparsed), len(urls)))


if __name__ == "__main__":
    main()
