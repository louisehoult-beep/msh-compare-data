#!/usr/bin/env python3
"""Trust digital profile, first field: NHS Federated Data Platform (FDP) status.

WHAT THIS IS (20/10/2026, Hub health tech intelligence gap, build plan "Next 30
days", Trust Digital Profile). NHS England publishes, as plain web pages under the
Open Government Licence v3:

  UPTAKE   .../impact/fdp-uptake-and-benefits/
           headline counts (trusts live, ICBs live, trusts and ICBs signed up),
           the date the numbers were updated, and when the next update is due.
  LIVE     .../impact/fdp-uptake-and-benefits/nhs-trusts-live-with-nhs-fdp/
           two ordered lists: NHS trusts, and integrated care boards (ICBs).
  SIGN-UP  .../impact/fdp-uptake-and-benefits/sign-up/
           the same two lists for organisations that have signed a Memorandum of
           Understanding (MOU) to join.

This script reads all three, cross-checks each list's length against the headline
count on the uptake page, and joins trusts to data/trust-map.json (NHS ODS) by
EXACT name after normalising case, apostrophes and "&"/"and". Nothing is fuzzy
matched: a name that does not join is listed under `unmatched`, never guessed.

WHAT A ROW DOES AND DOES NOT SAY. fdpLive true means NHS England lists the trust as
live. false means it is not on that list on the date read, which is a statement
about the list, not about what the trust runs. The source updates quarterly; the
file carries NHS England's own "updated on" date and next-update month.

USAGE
    python3 scripts/refresh_fdp_live.py
    python3 scripts/refresh_fdp_live.py --dry-run
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.england.nhs.uk/digitaltechnology/nhs-federated-data-platform/impact/fdp-uptake-and-benefits/"
UPTAKE_URL = BASE
LIVE_URL = BASE + "nhs-trusts-live-with-nhs-fdp/"
SIGNUP_URL = BASE + "sign-up/"
OUT_PATH = "data/trust-digital-profile.json"
MAP_PATH = "data/trust-map.json"
UA = {"User-Agent": "Elevate-and-Thrive-Hub/1.0 (Medical Sales Intelligence Hub; contact@elevateandthrive.uk)"}


def get(url, tries=2, timeout=40):
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
                if len(body) < 2000:
                    # NHS England's host answers some non-browser clients (GitHub's runners
                    # on 20/10/2026) with HTTP 202 and an empty body. That is a block, not a
                    # page: say so instead of parsing it as an empty list.
                    raise RuntimeError("HTTP %s with a %d byte body from %s (blocked, not a page)"
                                       % (getattr(r, "status", "?"), len(body), url))
                return body
        except Exception:
            if attempt == tries:
                raise
            time.sleep(5)


def text(fragment):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def main_html(page):
    i, j = page.find("<main"), page.find("</main>")
    return page[i:j] if i >= 0 and j > i else page


def lists_by_heading(page):
    """{h2 text: [li text]} for each <h2> followed by an <ol>/<ul> inside <main>."""
    body = main_html(page)
    out = {}
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|$)", body, re.S):
        head = text(m.group(1))
        lst = re.search(r"<(ol|ul)[^>]*>(.*?)</\1>", m.group(2), re.S)
        if not lst:
            continue
        items = [text(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", lst.group(2), re.S)]
        out[head] = [x for x in items if x]
    return out


def pick(lists, *words):
    for head, items in lists.items():
        h = head.lower()
        if all(w in h for w in words):
            return head, items
    return None, []


def headline(page):
    t = text(main_html(page))

    def num(pattern):
        m = re.search(pattern, t, re.I)
        return int(m.group(1).replace(",", "")) if m else None

    upd = re.search(r"The data below was updated on (\d{1,2} \w+ \d{4})", t)
    nxt = re.search(r"The next update will be in (\w+ \d{4})", t)
    asat = re.search(r"live on the NHS Federated Data Platform as at (end of \w+ \d{4})", t)
    return {
        "trustsLive": num(r"(\d[\d,]*)\s*[–-]\s*number of NHS trusts that are live"),
        "icbsLive": num(r"(\d[\d,]*)\s*[–-]\s*number of NHS integrated care boards that are on"),
        "trustsSignedUp": num(r"(\d[\d,]*)\s*[–-]\s*number of NHS trusts that have signed up"),
        "icbsSignedUp": num(r"(\d[\d,]*)\s*[–-]\s*number of NHS integrated care boards that have signed up"),
        "updatedOn": upd.group(1) if upd else None,
        "nextUpdate": nxt.group(1) if nxt else None,
        "asAt": asat.group(1) if asat else None,
    }


def norm(name):
    s = (name or "").lower().replace("’", "'").replace("‘", "'").replace("&", " and ")
    return re.sub(r"[^a-z0-9']+", " ", s).strip()


def build(uptake_html, live_html, signup_html, trust_map, today):
    head = headline(uptake_html)
    live = lists_by_heading(live_html)
    signed = lists_by_heading(signup_html)
    lt_h, live_trusts = pick(live, "trust")
    li_h, live_icbs = pick(live, "integrated care")
    st_h, signed_trusts = pick(signed, "trust")
    si_h, signed_icbs = pick(signed, "integrated care")

    checks = []
    for label, items, want in (("trustsLive", live_trusts, head["trustsLive"]),
                               ("icbsLive", live_icbs, head["icbsLive"]),
                               ("trustsSignedUp", signed_trusts, head["trustsSignedUp"]),
                               ("icbsSignedUp", signed_icbs, head["icbsSignedUp"])):
        checks.append({"list": label, "listed": len(items), "headline": want,
                       "agrees": want is not None and len(items) == want})

    by_norm = {norm(t["n"]): t for t in (trust_map or {}).get("trusts") or []}
    live_n = {norm(x) for x in live_trusts}
    signed_n = {norm(x) for x in signed_trusts}
    unmatched, seen_u = [], set()
    for x in sorted(live_trusts + signed_trusts):
        if norm(x) not in by_norm and norm(x) not in seen_u:
            seen_u.add(norm(x))
            unmatched.append(x)

    trusts = []
    for key, t in sorted(by_norm.items(), key=lambda kv: kv[1]["n"]):
        trusts.append({
            "code": t.get("code"), "name": t["n"], "icb": t.get("icb"), "icbName": t.get("icbName"),
            "fdpLive": key in live_n, "fdpSignedUp": key in signed_n,
        })
    signed_icb_n = {norm(x) for x in signed_icbs}
    live_icb_n = {norm(x) for x in live_icbs}
    icbs = [{"name": x, "fdpLive": norm(x) in live_icb_n, "fdpSignedUp": norm(x) in signed_icb_n}
            for x in sorted(set(live_icbs) | set(signed_icbs))]

    return {
        "generated": today.isoformat(),
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "source": "NHS England, NHS Federated Data Platform uptake and benefits, Open Government Licence v3",
        "sourceUrls": {"uptake": UPTAKE_URL, "live": LIVE_URL, "signUp": SIGNUP_URL},
        "sourceUpdatedOn": head["updatedOn"],
        "sourceAsAt": head["asAt"],
        "sourceNextUpdate": head["nextUpdate"],
        "rule": (
            "fdpLive: the trust's name appears on NHS England's list of NHS trusts live "
            "with the NHS Federated Data Platform. fdpSignedUp: it appears on the list of "
            "organisations that have signed a Memorandum of Understanding (MOU) to join. "
            "Names are joined to data/trust-map.json (NHS ODS) by exact match after "
            "normalising case, apostrophes and '&'; nothing is fuzzy matched, and a name "
            "that does not join is listed under unmatched (most are trusts renamed or "
            "merged since NHS England wrote the list; joining them needs the ODS "
            "successor record, so they are left unjoined). false means 'not on the list "
            "on the date read', a statement about the list and not about the trust."),
        "headline": {k: head[k] for k in ("trustsLive", "icbsLive", "trustsSignedUp", "icbsSignedUp")},
        "countCheck": checks,
        "counts": {
            "trustsInMap": len(trusts),
            "trustsLiveJoined": sum(1 for t in trusts if t["fdpLive"]),
            "trustsSignedUpJoined": sum(1 for t in trusts if t["fdpSignedUp"]),
            "unmatched": len(unmatched),
            "icbsLive": sum(1 for i in icbs if i["fdpLive"]),
        },
        "unmatched": unmatched,
        "trusts": trusts,
        "icbs": icbs,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(MAP_PATH, encoding="utf-8") as fh:
        trust_map = json.load(fh)
    try:
        pages = (get(UPTAKE_URL), get(LIVE_URL), get(SIGNUP_URL))
    except Exception as e:  # noqa: BLE001
        print("ABORT: source not readable from this host, file kept: %s" % e)
        return 1
    doc = build(pages[0], pages[1], pages[2], trust_map, dt.date.today())
    bad = [c for c in doc["countCheck"] if not c["agrees"]]
    for c in doc["countCheck"]:
        print("  %-15s listed %s, headline %s%s" % (c["list"], c["listed"], c["headline"],
                                                   "" if c["agrees"] else "  <-- DISAGREES"))
    print("  joined to trust map: %(trustsLiveJoined)d live, %(trustsSignedUpJoined)d signed up, "
          "%(unmatched)d unmatched name(s)" % doc["counts"])
    if not doc["countCheck"][0]["listed"]:
        print("ABORT: the live list parsed empty, so the page layout has changed. Nothing written.")
        return 1
    if bad:
        print("NOTE: list length and headline disagree; both are recorded, neither is corrected.")
    if args.dry_run:
        print("--dry-run: nothing written.")
        return 0
    old = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as fh:
            old = json.load(fh)
    if old and old.get("_notice"):
        doc = {"_notice": old["_notice"], **doc}
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote %s" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
