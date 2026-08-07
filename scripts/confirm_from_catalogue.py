#!/usr/bin/env python3
"""Confirm supplier identities using the NHS Supply Chain catalogue's own LEGAL
supplier name, and record the company number in the seed so it stays confirmed.

WHY
---
A name-search match is `probable` forever, and a probable record feeds nothing:
no officers, no accounts figures, no field filing profile. On 07/08/2026 that was
302 of 442 records. The bottleneck on almost everything downstream is therefore
identity, not data.

There is a confirmation route already written into docs/COMPANY-REPORT-METHOD.md
(route 3) that has not been used at scale: **the NHSSC catalogue prints the LEGAL
entity name of the company actually supplying each product**. That ties a trading
name we hold to a registered name — something a name search cannot do, because
the catalogue is the buyer's own record of who supplies it.

THE RULE, AND WHY IT IS DELIBERATELY STRICT
-------------------------------------------
A supplier is confirmed here ONLY when the cleaned catalogue legal name matches
**exactly one ACTIVE company** on the register, compared after normalising
nothing more than legal form and punctuation (LIMITED/LTD, &/AND, dots, spaces).

- Zero exact matches  -> left probable, reason recorded.
- More than one       -> left probable. Two companies of the same name is
                         precisely when guessing attaches the wrong accounts to
                         a named business.
- Inactive only       -> left probable, and worth a human look: the supplier may
                         now trade through a different entity.

No fuzzy matching, no "closest result", no taking the first hit. The catalogue
name is cleaned only of DEPOT and ROUTE decoration the catalogue itself adds
("(E-DIRECT)", "(STOCKED)", "STOCK OXFORD", "ED WOKINGHAM"), because those
describe how NHS Supply Chain buys, not who the company is.

Written into the seed as an anchored `Companies House NNNNNNNN` sentence WITH its
provenance, so refresh_companies_house.py confirms it on every future run instead
of this having to be re-done.

Run:  python3 scripts/confirm_from_catalogue.py [--limit N] [--dry-run]
Then: python3 scripts/refresh_companies_house.py   (to pick the confirmations up)
"""
import base64
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SEED = "data/supplier-seed.json"
CACHE = "data/nhssc-cache.json"
FIN = "data/company-financials.json"
API = "https://api.company-information.service.gov.uk"
KEY_ENV = "COMPANIES_HOUSE_KEY"
KEY_FILE = "~/.companies-house-key"
MIN_GAP = 0.55

CH_ANCHOR = re.compile(
    r"(?i)compan(?:y|ies)\s+house[^A-Za-z0-9]{0,4}(?:number|no\.?|reg(?:istration)?\.?)?"
    r"[^A-Za-z0-9]{0,4}((?:[A-Z]{2})?\d{6,8})")

# Decoration the CATALOGUE adds to describe the buying route or the depot. None
# of it is part of the company's name, and leaving it in guarantees a miss.
ROUTE_NOISE = re.compile(
    r"(?i)\s*(\(\s*e[\s-]?direct\s*\)|\(\s*stocked\s*\)|\(\s*stock\s*\)|e[\s-]?direct|"
    r"\bstocked\b|\bstock\b)\s*")
DEPOT_TAIL = re.compile(
    r"(?i)\s+(ed|stock|stocked|depot)?\s*(wokingham|oxford|newbury\d*|leeds|bury|"
    r"normanton|rugby|alfreton|maidstone|runcorn|bridgwater|swindon|"
    r"sheffield|nottingham|glasgow|belfast)\d*\s*$")
BRACKET_PLACE = re.compile(r"(?i)\s*\((berks|bucks|uk|gb|england|scotland|wales|ni)\)\s*$")


def load_key():
    k = os.environ.get(KEY_ENV, "").strip()
    if k:
        return k
    p = os.path.expanduser(KEY_FILE)
    if os.path.exists(p):
        k = pathlib.Path(p).read_text(encoding="utf-8").strip()
        if k:
            return k
    sys.exit("ABORT: no Companies House key in $%s or %s." % (KEY_ENV, KEY_FILE))


KEY = load_key()
AUTH = {"Authorization": "Basic " + base64.b64encode((KEY + ":").encode()).decode()}
_last = [0.0]


def pace():
    d = time.time() - _last[0]
    if d < MIN_GAP:
        time.sleep(MIN_GAP - d)
    _last[0] = time.time()


def api_get(path):
    pace()
    try:
        return json.load(urllib.request.urlopen(
            urllib.request.Request(API + path, headers=AUTH), timeout=45))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(30)
            return api_get(path)
        return None
    except Exception:
        return None


def clean_catalogue_name(name):
    s = " ".join(str(name or "").split())
    prev = None
    while prev != s:
        prev = s
        s = ROUTE_NOISE.sub(" ", s).strip(" -–,")
        s = DEPOT_TAIL.sub("", s).strip()
        s = BRACKET_PLACE.sub("", s).strip()
    return " ".join(s.split())


def key_of(name):
    """Normalise ONLY legal form and punctuation — nothing that changes identity."""
    s = str(name or "").upper()
    s = s.replace("&", " AND ")
    s = re.sub(r"[.,'’`]", "", s)
    s = re.sub(r"\bLIMITED\b", "LTD", s)
    s = re.sub(r"\bPUBLIC LTD COMPANY\b", "PLC", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(s.split())


def catalogue_legal_names(cache):
    out = {}
    for rec in (cache.get("products") or {}).values():
        ours = rec.get("supplier")
        if not ours:
            continue
        for it in (rec.get("items") or []):
            ln = (it.get("supplier") or "").strip()
            if ln:
                out.setdefault(ours, {}).setdefault(clean_catalogue_name(ln), 0)
                out[ours][clean_catalogue_name(ln)] += 1
    return out


def resolve(cleaned):
    """(number, registered_name) if EXACTLY one active exact match, else (None, reason)."""
    res = api_get("/search/companies?items_per_page=40&q=" + urllib.parse.quote(cleaned))
    if not res:
        return None, "no response from the company search"
    want = key_of(cleaned)
    exact = []
    for it in (res.get("items") or []):
        title = it.get("title") or ""
        if key_of(title) != want:
            continue
        exact.append(it)
    if not exact:
        return None, "no company on the register carries this exact name"
    active = [i for i in exact if (i.get("company_status") or "").lower() == "active"]
    if len(active) == 1:
        return (active[0].get("company_number"), active[0].get("title")), None
    if not active:
        return None, ("the only exact name match(es) on the register are not active (%s) — the "
                      "supplier may now trade through a different entity"
                      % ", ".join(sorted({i.get("company_status", "?") for i in exact})))
    return None, ("%d active companies share this exact name, so the catalogue name alone does "
                  "not identify one" % len(active))


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    dry = "--dry-run" in sys.argv

    seed = json.load(open(SEED, encoding="utf-8"))
    cache = json.load(open(CACHE, encoding="utf-8"))
    fin = json.load(open(FIN, encoding="utf-8")).get("companies", {})
    legal = catalogue_legal_names(cache)

    by_name = {s["name"]: s for s in seed["suppliers"]}
    todo = []
    for name, names in legal.items():
        rec = by_name.get(name)
        if not rec:
            continue
        if CH_ANCHOR.search(rec.get("note") or ""):
            continue                                   # already confirmed here
        if (fin.get(name) or {}).get("matchConfidence") == "confirmed":
            continue
        best = sorted(names.items(), key=lambda kv: -kv[1])
        todo.append((name, [n for n, _ in best]))
    todo.sort()
    if limit:
        todo = todo[:limit]

    confirmed, refused = [], []
    for name, candidates in todo:
        got = None
        why = ""
        for cand in candidates[:3]:                    # most-seen legal name first
            if not cand:
                continue
            got, why = resolve(cand)
            if got:
                number, registered = got
                break
        if not got:
            refused.append((name, candidates[0] if candidates else "", why))
            print("  -- %-32s %s" % (name[:32], (why or "")[:60]))
            continue

        sentence = ("Companies House %s — the NHS Supply Chain catalogue names the supplying "
                    "legal entity as \"%s\", and the register holds exactly one active company "
                    "of that name (%s). Confirmed by catalogue legal name on %s."
                    % (number, cand, registered, time.strftime("%d/%m/%Y")))
        rec = by_name[name]
        rec["note"] = ((rec.get("note") or "") + " " + sentence).strip()
        confirmed.append((name, number, registered))
        print("  OK %-32s %s  %s" % (name[:32], number, registered[:40]))

    if not dry:
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(seed, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")

    print("\n%d confirmed by catalogue legal name, %d left probable.%s"
          % (len(confirmed), len(refused), "  (dry run: nothing written)" if dry else ""))
    print("Run scripts/refresh_companies_house.py next so the confirmations take effect.")


if __name__ == "__main__":
    main()
