#!/usr/bin/env python3
"""Named NHS trust contacts from Find a Tender, and the job-change signal that
falls out of tracking them over time.

WHAT THIS IS
Find a Tender (FTS) is the statutory UK public-procurement notice service. Every
notice names a contact for enquiries. Where that contact is a person at an NHS
trust, this records the name, work email and phone against the trust — sourced,
dated and linked back to the notice it came from. Open Government Licence v3.

WHAT IT IS NOT
Not a mailing list. These are individuals' work contact details published for
enquiries about a specific procurement. The Hub shows them with the notice they
came from so a rep has a real reason to make contact. Handle under the outreach
evidence standard. OGL covers copyright, NOT UK GDPR lawful basis — an Article
14 notice is due within one month or at first contact.

THE JOB-CHANGE SIGNAL
There is no public register of NHS procurement job moves. But when the named
contact on a trust's notices changes, and the previous name stops appearing,
that is real dated evidence that someone's remit changed — from a primary
source, with the notices to prove it. That is what data/people-moves.json is:
observed changes, never inferred ones. A contact seen once is not a "move".

⚠️ RATE LIMIT — the reason this is incremental and not one big pull.
The OCDS API returns HTTP 429 with Retry-After after a small number of requests
(observed 24/07/2026: ~a dozen calls trips it, Retry-After: 120). A full 18-month
backfill in one run is not possible. So: run daily over a short window, append,
and let coverage build. Always honour Retry-After — do not lower the sleeps to
make a run finish faster, you will just get throttled harder.

USAGE
  python3 scripts/refresh_fts_contacts.py            # daily: last 3 days
  python3 scripts/refresh_fts_contacts.py --days 30  # catch up after an outage
  python3 scripts/refresh_fts_contacts.py --from 2025-01-01 --to 2025-02-01
"""
import json, urllib.request, urllib.error, re, sys, time, datetime, os

API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
UA = {"User-Agent": "MedicalSalesHub/1.0 (+https://elevateandthrive.uk; trust contact index)",
      "Accept": "application/json"}
MAP_PATH = "data/trust-map.json"
OUT_PATH = "data/trust-contacts.json"
MOVES_PATH = "data/people-moves.json"
OPTOUT_PATH = "data/contacts-optout.json"

PAGE_SLEEP = 3.0        # polite floor between pages
MAX_WAIT = 600          # give up on a 429 that wants longer than this

# Retention. A contact whose most recent notice is older than this is dropped.
# 24 months is deliberately just past NHS Supply Chain's own stated supplier
# engagement window (9–15 months before an arrangement expires), so a contact
# stays only while they are plausibly still the person to ask. THIS NUMBER IS
# STATED IN THE PUBLISHED PRIVACY NOTICE — if you change it, change that too.
RETENTION_MONTHS = 24

# Words that mean the "contact name" is a desk, not a person.
DEPARTMENTAL = re.compile(
    r"\b(team|dept|department|office|procurement|purchasing|supplies|supply|contracts?|"
    r"commercial|admin|helpdesk|help desk|mailbox|enquir|info|general|shared|group|"
    r"services?|unit|division|directorate|do not reply|noreply)\b", re.I)


def get(url):
    """GET with Retry-After-aware backoff. Returns parsed JSON."""
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 120)
                if wait > MAX_WAIT:
                    raise SystemExit("ABORT: FTS asked for a %ds wait — stopping rather than "
                                     "hammering it. Re-run later." % wait)
                print("  429 — waiting %ds (Retry-After)" % wait, flush=True)
                time.sleep(wait + 2)
                continue
            attempt += 1
            if attempt >= 3:
                raise
            time.sleep(5 * attempt)
        except Exception:
            attempt += 1
            if attempt >= 3:
                raise
            time.sleep(5 * attempt)


def norm(s):
    """Strip the words every NHS trust shares, so a fuzzy name match is meaningful."""
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(NHS|FOUNDATION|TRUST|UNIVERSITY|HOSPITALS?|HEALTHCARE|HEALTH|"
               r"SERVICES?|THE|AND|OF)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def main(argv):
    today = datetime.date.today()
    frm = to = None
    days = 3
    i = 0
    while i < len(argv):
        if argv[i] == "--days":
            days = int(argv[i + 1]); i += 2
        elif argv[i] == "--from":
            frm = argv[i + 1]; i += 2
        elif argv[i] == "--to":
            to = argv[i + 1]; i += 2
        else:
            i += 1
    if not frm:
        frm = (today - datetime.timedelta(days=days)).isoformat()
    if not to:
        to = (today + datetime.timedelta(days=1)).isoformat()

    trusts = json.load(open(MAP_PATH))["trusts"]
    index, keys = {}, []
    for t in trusts:
        k = norm(t["n"])
        if len(k) >= 4 and k not in index:
            index[k] = t
    # Longest first so "Guy's and St Thomas'" wins over a shorter accidental substring.
    keys = sorted(index, key=len, reverse=True)

    # ---- opt-outs -------------------------------------------------------
    # Someone who asks not to be contacted must STAY gone. Deleting their row
    # from trust-contacts.json is not enough — the next run would re-harvest
    # them from the same notice. Their name goes here and is filtered on the
    # way in, and stripped from anything already stored.
    optout = load(OPTOUT_PATH, {"note": "Names that must never appear in the contact index. "
                                        "Add a lower-cased name here when someone asks not to be "
                                        "contacted; the harvester filters them on the way in and "
                                        "removes them from what is already stored.",
                                "names": [], "emails": []})
    blocked_names = {n.strip().lower() for n in optout.get("names", []) if n.strip()}
    blocked_emails = {e.strip().lower() for e in optout.get("emails", []) if e.strip()}

    store = load(OUT_PATH, {"source": "Find a Tender (OCDS API), Open Government Licence v3",
                            "sourceUrl": "https://www.find-tender.service.gov.uk/",
                            "windows": [], "trusts": {}})
    before = {c: {e["name"].lower(): dict(e) for e in v}
              for c, v in store["trusts"].items()}

    url = "%s?updatedFrom=%sT00:00:00&updatedTo=%sT00:00:00&limit=100" % (API, frm, to)
    pages = releases = matched = 0
    t0 = time.time()
    while url:
        d = get(url)
        for r in d.get("releases", []):
            releases += 1
            date = (r.get("date") or "")[:10]
            tender = r.get("tender") or {}
            title = (tender.get("title") or "").strip()
            ocid = r.get("ocid", "")
            for p in r.get("parties", []):
                if "buyer" not in p.get("roles", []):
                    continue
                pname = p.get("name", "")
                if "NHS" not in pname.upper():
                    continue
                cp = p.get("contactPoint") or {}
                nm = (cp.get("name") or "").strip()
                if len(nm) < 4 or " " not in nm or DEPARTMENTAL.search(nm):
                    continue
                if nm.lower() in blocked_names or (cp.get("email") or "").strip().lower() in blocked_emails:
                    continue
                pk = norm(pname)
                match = next((k for k in keys if pk.startswith(k) or k in pk), None)
                if not match:
                    continue
                t = index[match]
                bucket = store["trusts"].setdefault(t["code"], [])
                existing = next((e for e in bucket if e["name"].lower() == nm.lower()), None)
                if existing:
                    existing["n"] = existing.get("n", 1) + 1
                    existing["first"] = min(existing["first"], date)
                    if date >= existing["last"]:
                        existing.update(last=date, notice=title[:180], ocid=ocid,
                                        email=(cp.get("email") or existing.get("email", "")).strip(),
                                        tel=(cp.get("telephone") or existing.get("tel", "")).strip())
                else:
                    bucket.append({"name": nm, "email": (cp.get("email") or "").strip(),
                                   "tel": (cp.get("telephone") or "").strip(),
                                   "first": date, "last": date, "n": 1,
                                   "notice": title[:180], "ocid": ocid})
                matched += 1
        pages += 1
        url = (d.get("links") or {}).get("next")
        if url:
            time.sleep(PAGE_SLEEP)
        if pages % 10 == 0:
            print("  %d pages / %d releases / %d NHS contact hits / %ds"
                  % (pages, releases, matched, time.time() - t0), flush=True)

    # ---- observed changes → people-moves.json -------------------------------
    # Only a genuinely NEW name at a trust that ALREADY had a different named
    # contact counts. A first-ever contact for a trust is coverage, not a move.
    moves = load(MOVES_PATH, {"note": "Observed changes of named contact on NHS procurement "
                                      "notices (Find a Tender). Evidence of a change of remit, "
                                      "not an announced appointment. Never inferred.",
                              "source": "Find a Tender (OCDS API), Open Government Licence v3",
                              "moves": []})
    seen_keys = {(m["trust"], m["name"].lower()) for m in moves["moves"]}
    for code, entries in store["trusts"].items():
        prior = before.get(code)
        if not prior:
            continue
        for e in entries:
            k = e["name"].lower()
            if k in prior or (code, k) in seen_keys:
                continue
            predecessors = sorted(prior.values(), key=lambda x: x["last"], reverse=True)
            moves["moves"].append({
                "trust": code,
                "name": e["name"],
                "email": e["email"],
                "firstSeen": e["first"],
                "replaces": predecessors[0]["name"] if predecessors else None,
                "replacesLastSeen": predecessors[0]["last"] if predecessors else None,
                "notice": e["notice"],
                "ocid": e["ocid"],
            })
            seen_keys.add((code, k))
    moves["moves"].sort(key=lambda m: m["firstSeen"], reverse=True)
    moves["asOf"] = today.strftime("%d/%m/%Y")

    # ---- retention ------------------------------------------------------
    # Enforced on every run, not on a separate schedule, so the published
    # retention promise cannot quietly drift from what the file actually holds.
    cutoff = (today - datetime.timedelta(days=int(RETENTION_MONTHS * 30.44))).isoformat()
    expired = 0
    for code in list(store["trusts"]):
        keep = [e for e in store["trusts"][code] if e["last"] >= cutoff]
        expired += len(store["trusts"][code]) - len(keep)
        if keep:
            store["trusts"][code] = keep
        else:
            del store["trusts"][code]
    moves["moves"] = [m for m in moves["moves"] if m["firstSeen"] >= cutoff]
    if expired:
        print("retention: dropped %d contact(s) last seen before %s" % (expired, cutoff))

    # Sweep opt-outs out of everything already stored, including past moves.
    if blocked_names or blocked_emails:
        def kept(e):
            return (e["name"].lower() not in blocked_names
                    and (e.get("email") or "").lower() not in blocked_emails)
        for code in list(store["trusts"]):
            store["trusts"][code] = [e for e in store["trusts"][code] if kept(e)]
            if not store["trusts"][code]:
                del store["trusts"][code]
        moves["moves"] = [m for m in moves["moves"]
                          if m["name"].lower() not in blocked_names
                          and (m.get("email") or "").lower() not in blocked_emails
                          and (m.get("replaces") or "").lower() not in blocked_names]

    store["windows"] = (store.get("windows", []) + [{"from": frm, "to": to,
                                                     "releases": releases, "run": today.isoformat()}])[-60:]
    store["asOf"] = today.strftime("%d/%m/%Y")
    store["retentionMonths"] = RETENTION_MONTHS
    store["trustsCovered"] = len(store["trusts"])
    store["contactsTotal"] = sum(len(v) for v in store["trusts"].values())
    for v in store["trusts"].values():
        v.sort(key=lambda e: e["last"], reverse=True)

    json.dump(store, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
    json.dump(moves, open(MOVES_PATH, "w"), ensure_ascii=False, indent=1)
    print("scanned %s→%s: %d releases, %d pages. Index now %d trusts / %d contacts. "
          "%d observed changes total."
          % (frm, to, releases, pages, store["trustsCovered"], store["contactsTotal"],
             len(moves["moves"])))


if __name__ == "__main__":
    main(sys.argv[1:])
