#!/usr/bin/env python3
"""
verify.py — publish gate for everything this repo serves to the Medical Sales Hub.

WHY THIS EXISTS
---------------
On 24/07/2026 the Stakeholder Mapper's "recent changes in who is named" panel
went live telling members about 145 job changes at named NHS trusts. All 145
were false. Moves were detected by diffing the contact index before and after a
run, which assumes runs walk forward in time; the backfill walked backwards, so
every earlier month's names were logged as having "replaced" people they
actually preceded — Paul Greenwood, first seen 30/06, recorded as replacing
Hannah Dimmick, last seen 24/07.

The check that would have caught it is one line: a person cannot replace
somebody who was still signing notices three weeks later. It was never written,
because this repo had no gate — unlike cloud-pipeline, which has hub_verify.py
and a standing rule that nothing sends until it passes.

The same day, data/trust-contacts.json and data/people-moves.json — real named
NHS staff and their work emails — were published by accident, swept into a
commit by `git add -A` before anyone had decided they should be public.

So: nothing in this repo reaches the Hub until this script exits 0.

WHAT IT CHECKS
--------------
1. MOVES         every claimed handover must be chronologically possible, and
                 clear the gap the file itself declares. This is the incident.
2. CONTACTS      dates sane, retention honoured, opt-outs absent, trusts real,
                 names look like people rather than departments.
3. TRUST MAP     size, unique ODS codes, ICB codes from the current 36, and
                 the ICB name matching the code it is paired with.
4. CONSENT GATE  if named personal data is present, the LIVE privacy notice
                 must carry its Article 14 section and the SAME retention
                 period the code enforces. Personal data cannot outrun its
                 own notice.
5. JAVASCRIPT    every app/*.js parses. A syntax error here takes out the whole
                 Med Sales Tools page, not one panel.
6. SHRINK        datasets may not silently collapse against what is committed.
7. SOURCE LINKS  every citation in the Compare feed must still open. WARNS, never
                 fails — see the note above check_source_links for why.

Usage
    python3 verify.py            # full run, including the live privacy check
    python3 verify.py --offline  # skip network checks (still fails on logic)
    python3 verify.py --no-links # skip only the source-link check
    python3 verify.py --json

Exit codes
    0  passed — safe to push
    1  FAILED — do not push until every FAIL is resolved
"""

import json, os, re, subprocess, sys, datetime, shutil, tempfile, time
from urllib.request import Request, urlopen

DATA = "data"
PRIVACY_URL = "https://medsalesintelligencehub.co.uk/privacy-policy/"
PRIVACY_MARKER = "NHS Contact Information in the Medical Sales Hub"
UA = {"User-Agent": "Mozilla/5.0 (msh-compare-data verify)"}

# The 36 ICBs effective 01/04/2026. Kept in step with scripts/refresh_trusts.py.
ICB_CODES = {
    'QOQ','QHM','QF7','QWO','QYG','QOP','QE1','QHL','QUA','QWU','QJ2','QGH',
    'QK1','QJM','QPM','QT1','QOC','QNC','S1Y5D','D7T5G','T6Y0W','QMF','QKK',
    'QWE','Z9B2Z','QRL','QKS','S9B9J','S0E4D','QOX','QUY','QT6','QJK','QVV',
    'QR1','QSL',
}
KINDS = {None, 'Ambulance service', 'Mental health', 'Community'}
DEPARTMENTAL = re.compile(
    r"\b(team|dept|department|office|procurement|purchasing|supplies|supply|"
    r"contracts?|commercial|admin|helpdesk|mailbox|enquir|info|general|shared|"
    r"group|services?|unit|division|directorate|noreply)\b", re.I)

fails, warns = [], []
def FAIL(check, msg): fails.append((check, msg))
def WARN(check, msg): warns.append((check, msg))


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def committed(path):
    """The version of a file currently on main, for shrink comparison."""
    try:
        out = subprocess.run(["git", "show", "HEAD:" + path],
                             capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout) if out.returncode == 0 else None
    except Exception:
        return None


def today():
    return datetime.date.today()


def as_date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


# --------------------------------------------------------------------------
# 1. MOVES — the incident check
# --------------------------------------------------------------------------
def check_moves(moves, trust_codes, blocked, contacts):
    if moves is None:
        return
    rows = moves.get("moves", [])
    gap = int(moves.get("gapDays") or 0)
    min_notices = int(moves.get("minNotices") or 0)
    # A moves file must DECLARE every rule it was generated under. Anything
    # missing means it came from an older generator, and the checks below would
    # silently skip rather than fail — which is how the Lancashire false
    # handover came back after being fixed: a background backfill rewrote the
    # file with pre-fix code and the gate waved it through. Fail closed.
    if rows:
        for flag in ("gapDays", "minNotices", "minSpanDays", "singleThreadedOnly"):
            if moves.get(flag) in (None, ""):
                FAIL("moves", "people-moves.json does not declare %r. It was written by an older "
                              "generator than the one in scripts/, so the rules it claims cannot be "
                              "checked. Re-run: python3 scripts/refresh_fts_contacts.py "
                              "--rebuild-moves" % flag)
    if rows and min_notices < 2:
        FAIL("moves", "people-moves.json declares minNotices=%s. Below 2, a single notice becomes "
                      "a claimed job change — do not publish moves on that basis." % min_notices)
    if gap <= 0:
        FAIL("moves", "people-moves.json declares no gapDays — the rule a reader "
                      "is being asked to trust must be stated in the file.")
    impossible = chrono = 0
    for m in rows:
        first, prev_last = as_date(m.get("firstSeen")), as_date(m.get("replacesLastSeen"))
        if not first:
            FAIL("moves", "move for %r has no usable firstSeen" % m.get("name")); continue
        if first > today():
            FAIL("moves", "move for %r is dated in the future (%s)" % (m.get("name"), first))
        if m.get("replaces") and not prev_last:
            FAIL("moves", "move for %r claims to replace %r with no date for that person"
                          % (m.get("name"), m.get("replaces")))
            continue
        if prev_last:
            # THE INCIDENT: you cannot take over from somebody who was still there.
            if first <= prev_last:
                impossible += 1
                if impossible <= 5:
                    FAIL("moves", "IMPOSSIBLE HANDOVER — %r first seen %s but is recorded as "
                                  "replacing %r, last seen %s. A person cannot replace someone "
                                  "who came after them."
                                  % (m.get("name"), first, m.get("replaces"), prev_last))
            elif gap and (first - prev_last).days < gap:
                chrono += 1
                if chrono <= 5:
                    FAIL("moves", "GAP TOO SHORT — %r appeared %d days after %r was last seen, "
                                  "below the %d-day rule this file declares."
                                  % (m.get("name"), (first - prev_last).days, m.get("replaces"), gap))
        if m.get("trust") and trust_codes and m["trust"] not in trust_codes:
            FAIL("moves", "move for %r is attached to trust code %r, which is not in "
                          "trust-map.json" % (m.get("name"), m["trust"]))
        if (m.get("name") or "").strip().lower() in blocked:
            FAIL("moves", "%r has opted out but still appears in people-moves.json" % m.get("name"))

        # CONCURRENT BUYERS. A trust where two contacts were active at the same
        # time has more than one buyer, so a new name cannot be read as taking
        # over from anyone. Lancashire and South Cumbria passed the gap rule and
        # the evidence floor and was still wrong on exactly this.
        if contacts:
            ent = sorted(contacts.get(m.get("trust"), []), key=lambda e: e["first"])
            for a_i in range(len(ent)):
                clash = None
                for b_i in range(a_i + 1, len(ent)):
                    a, b = ent[a_i], ent[b_i]
                    if a["last"] >= b["first"] and b["last"] >= a["first"]:
                        clash = (a["name"], b["name"]); break
                if clash:
                    FAIL("moves", "CONCURRENT BUYERS — trust %r has %r and %r active at the same "
                                  "time, so the move claimed for %r is not a handover, it is a "
                                  "trust with more than one buyer."
                                  % (m.get("trust"), clash[0], clash[1], m.get("name")))
                    break

        # EVIDENCE FLOOR. A name on a single notice is a data point, not a
        # post-holder. The first two moves that cleared the 60-day rule were
        # both one-notice-each at large trusts — i.e. two different buyers, not
        # a handover. Telling a rep someone changed role on that basis is the
        # same failure as the 145, just quieter.
        if contacts:
            held = {e["name"].lower(): e for e in contacts.get(m.get("trust"), [])}
            for who, label in ((m.get("name"), "new name"), (m.get("replaces"), "predecessor")):
                if not who:
                    continue
                e = held.get(who.lower())
                if e is None:
                    # Every claim about a person must be traceable to the index it
                    # was derived from. A name that is not there is unsourced, and
                    # unsourced is worse than thin.
                    FAIL("moves", "UNSOURCED — %s %r is not in the contact index for trust %r. "
                                  "A published claim about a named person must be traceable to "
                                  "the notices it came from."
                                  % (label, who, m.get("trust")))
                    continue
                if e.get("n", 1) < min_notices:
                    FAIL("moves", "THIN EVIDENCE — %s %r appears on only %d notice(s). One notice "
                                  "is a data point, not a post-holder; this is a trust with more "
                                  "than one buyer, not a handover."
                                  % (label, who, e.get("n", 1)))
    if impossible > 5:
        FAIL("moves", "...and %d further impossible handovers (suppressed)" % (impossible - 5))
    if chrono > 5:
        FAIL("moves", "...and %d further sub-gap handovers (suppressed)" % (chrono - 5))

    # Plausibility. Real procurement handovers are uncommon; a burst means the
    # detection has broken again, in some new way this script does not yet name.
    if trust_codes and rows:
        share = len({m.get("trust") for m in rows}) / max(len(trust_codes), 1)
        if share > 0.20:
            FAIL("moves", "%d moves across %.0f%% of all trusts — implausible. Real handovers "
                          "are rare; this is what a broken detector looks like."
                          % (len(rows), share * 100))


# --------------------------------------------------------------------------
# 2. CONTACTS
# --------------------------------------------------------------------------
def check_contacts(store, trust_codes, blocked, retention_months):
    if store is None:
        return
    trusts = store.get("trusts", {})
    cutoff = today() - datetime.timedelta(days=int(retention_months * 30.44)) if retention_months else None
    n = 0
    for code, entries in trusts.items():
        if trust_codes and code not in trust_codes:
            FAIL("contacts", "contacts filed under trust code %r, which is not in trust-map.json" % code)
        for e in entries:
            n += 1
            nm = (e.get("name") or "").strip()
            first, last = as_date(e.get("first")), as_date(e.get("last"))
            if not nm or " " not in nm:
                FAIL("contacts", "%r under %s does not look like a person's name" % (nm, code))
            if DEPARTMENTAL.search(nm):
                FAIL("contacts", "%r under %s looks like a department, not a person — a rep would "
                                 "address a desk by name" % (nm, code))
            if nm.lower() in blocked:
                FAIL("contacts", "%r has opted out but is still in the contact index" % nm)
            if not first or not last:
                FAIL("contacts", "%r under %s has unusable dates" % (nm, code)); continue
            if first > last:
                FAIL("contacts", "%r under %s: first seen %s is after last seen %s" % (nm, code, first, last))
            if last > today():
                FAIL("contacts", "%r under %s is dated in the future (%s)" % (nm, code, last))
            if cutoff and last < cutoff:
                FAIL("contacts", "%r under %s was last seen %s, past the %d-month retention this "
                                 "repo publishes. Retention is enforced on every run — if this "
                                 "fires, it stopped working." % (nm, code, last, retention_months))
            em = (e.get("email") or "").strip()
            if em and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
                FAIL("contacts", "%r under %s has a malformed email %r" % (nm, code, em))
    if n and store.get("contactsTotal") not in (None, n):
        WARN("contacts", "contactsTotal says %s, actual count is %d" % (store.get("contactsTotal"), n))
    return n


# --------------------------------------------------------------------------
# 2b. NOTICE TAGS — the relevance sort on the contacts panel
#
# The panel puts names whose notice title matches the rep's speciality above
# the rest. That ordering is a DERIVED claim, so under root constitution rule
# 14 it needs the rule shipped with it, an invariant that fails if the logic
# broke, and a refusal to fire on thin evidence.
#
# The invariant that matters: tags in the published file must equal what the
# current vocabulary produces from the same title. If someone edits the
# vocabulary and only the day's new rows get tagged, half the index sorts under
# the old rules and nothing else would notice.
# --------------------------------------------------------------------------
def check_tags(store, products):
    if store is None:
        return
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
        import notice_tags
    except Exception as e:
        FAIL("tags", "cannot import scripts/notice_tags.py (%s) — the contacts panel sorts by "
                     "these tags, so a broken vocabulary must not publish." % e)
        return

    # Tag against what the member can actually SELECT, not against the wider
    # canonical list. A tag for a speciality missing from the dropdown is work
    # nobody will ever see. (products.json -> SPECS fills that dropdown.)
    selectable = {s.get("id") for s in (products or {}).get("SPECS", [])}
    if not selectable:
        FAIL("tags", "no SPECS read from products.json — cannot check the tag vocabulary "
                     "against the speciality dropdown.")
        return
    unknown = set(notice_tags.SPEC_TERMS) - selectable
    if unknown:
        FAIL("tags", "notice_tags.py tags specialities the dropdown has no entry for: %s. A name "
                     "filed under a speciality nobody can select is invisible."
                     % ", ".join(sorted(unknown)))

    total = drift = untagged = 0
    spec_hits = {}
    for code, entries in store.get("trusts", {}).items():
        for e in entries:
            total += 1
            want_spec, want_cls = notice_tags.tag(e.get("notice"))
            if e.get("spec") is None or e.get("cls") is None:
                untagged += 1
                continue
            if sorted(e.get("spec") or []) != want_spec or e.get("cls") != want_cls:
                drift += 1
                if drift == 1:
                    FAIL("tags", "stored tags disagree with the current vocabulary — e.g. %r under "
                                 "%s is stored as %s/%s but re-derives as %s/%s. Run "
                                 "`python3 scripts/refresh_fts_contacts.py --retag`."
                                 % ((e.get("notice") or "")[:60], code, e.get("cls"),
                                    e.get("spec"), want_cls, want_spec))
            for s in (e.get("spec") or []):
                spec_hits[s] = spec_hits.get(s, 0) + 1
    if drift > 1:
        FAIL("tags", "%d of %d contacts carry tags that disagree with the current vocabulary."
                     % (drift, total))
    if untagged:
        FAIL("tags", "%d of %d contacts have no tags at all — they would sort to the bottom for "
                     "every speciality. Run --retag." % (untagged, total))

    # EVIDENCE FLOOR. A term broad enough to claim a large share of every
    # trust's notices is not evidence of a speciality, it is a bad regex. At
    # 27/07/2026 the biggest single speciality holds 40 of 1,400 (2.9%).
    for s, hits in spec_hits.items():
        if total and hits / total > 0.25:
            FAIL("tags", "speciality %r matches %d of %d notice titles (%.0f%%). No real speciality "
                         "is a quarter of NHS tendering — the vocabulary for it is too greedy, and "
                         "a rep would be shown everyone." % (s, hits, total, 100.0 * hits / total))

    # The rule must travel with the data (rule 14a). A member sorting by
    # relevance has to be able to see what "relevant" was taken to mean.
    if not (store.get("tagRule") or "").strip():
        FAIL("tags", "trust-contacts.json carries tags but not the rule they were derived under. "
                     "A derived claim ships with its rule or it does not ship.")
    counts = store.get("noticeClassCounts") or {}
    if counts and counts.get("clinical", 0) == 0:
        FAIL("tags", "not one notice classified as clinical across the whole index — the classifier "
                     "is broken, and every rep would see an empty relevant list.")


# --------------------------------------------------------------------------
# 3. TRUST MAP
# --------------------------------------------------------------------------
def check_trust_map(tm):
    if tm is None:
        FAIL("trustmap", "data/trust-map.json is missing — the trust picker cannot work without it.")
        return set()
    trusts = tm.get("trusts", [])
    if len(trusts) < 180:
        FAIL("trustmap", "only %d trusts — expected ~200. Refusing a shrunken directory." % len(trusts))
    codes = [t.get("code") for t in trusts]
    dupes = {c for c in codes if codes.count(c) > 1}
    if dupes:
        FAIL("trustmap", "duplicate ODS codes: %s" % ", ".join(sorted(dupes)[:8]))
    for t in trusts:
        if t.get("kind") not in KINDS:
            FAIL("trustmap", "%s has kind %r, which is not one the UI knows how to group"
                             % (t.get("n"), t.get("kind")))
        if t.get("nation") == "England":
            if t.get("icb") not in ICB_CODES:
                FAIL("trustmap", "%s has ICB code %r, not one of the 36 effective 01/04/2026. "
                                 "If the April 2027 round has landed, update ICB_CODES here AND "
                                 "in scripts/refresh_trusts.py together."
                                 % (t.get("n"), t.get("icb")))
            if not t.get("icbName"):
                FAIL("trustmap", "%s has an ICB code but no ICB name" % t.get("n"))
        elif t.get("icb"):
            FAIL("trustmap", "%s is tagged %s but carries an ICB code" % (t.get("n"), t.get("nation")))
    return set(codes)


# --------------------------------------------------------------------------
# 4. CONSENT GATE — personal data may not outrun its own privacy notice
# --------------------------------------------------------------------------
def check_privacy(contact_count, retention_months, offline):
    if not contact_count:
        return
    if offline:
        WARN("privacy", "skipped the live privacy-notice check (--offline). Do not push on this.")
        return
    try:
        html = urlopen(Request(PRIVACY_URL, headers=UA), timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        FAIL("privacy", "could not read %s (%s). %d named people are in this repo and the gate "
                        "cannot confirm their privacy notice is live — treat as a failure, not a "
                        "network blip." % (PRIVACY_URL, e, contact_count))
        return
    if PRIVACY_MARKER not in html:
        FAIL("privacy", "%d named NHS contacts are about to be published, but the live privacy "
                        "notice has no %r section. Article 14 information must be up BEFORE the "
                        "data is." % (contact_count, PRIVACY_MARKER))
        return
    if retention_months:
        if not re.search(r"more than\s+%d\s+months" % retention_months, html):
            FAIL("privacy", "the code enforces %d-month retention but the published privacy notice "
                            "does not state that figure. The promise and the behaviour must match."
                            % retention_months)


# --------------------------------------------------------------------------
# 5. JAVASCRIPT
# --------------------------------------------------------------------------
JSC = "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc"

def check_js():
    runner = None
    if shutil.which("node"):
        runner = "node"
    elif os.path.exists(JSC):
        runner = "jsc"
    if not runner:
        WARN("js", "no JavaScript engine available — app/*.js not syntax-checked.")
        return
    for fn in sorted(os.listdir("app")):
        if not fn.endswith(".js"):
            continue
        path = os.path.join("app", fn)
        if runner == "node":
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True, timeout=60)
            ok, err = r.returncode == 0, (r.stderr or "").strip().split("\n")[0]
        else:
            script = ("try{new Function(read(%r));print('OK');}"
                      "catch(e){print('ERR '+e);}" % os.path.abspath(path))
            # A PRIVATE temp file, per check, always cleaned up.
            #
            # This used to be a hardcoded "/tmp/_verify_js.js". Two runs at the
            # same moment overwrote each other's script, and whichever process
            # got there second handed jsc a half-written or foreign file — which
            # comes back as a SYNTAX ERROR against whatever app/*.js was being
            # checked at the time. That is a FALSE FAIL, and a false FAIL blocks
            # a push: the refresh workflows commit unattended, so the data simply
            # stops moving and the reason on screen is a parse error in a file
            # that parses perfectly.
            #
            # Not theoretical. On 05/08/2026 a clean clone reported
            # app/supplier-search.js and app/whos-who.js as not parsing, while a
            # second run seconds later passed; a Claude session was running
            # verify.py concurrently. Concurrent runs are now the norm here — CI,
            # the pre-push hook, two refresh workflows, and more than one session.
            fd, tmp = tempfile.mkstemp(prefix="verify_js_", suffix=".js")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(script)
                r = subprocess.run([JSC, tmp], capture_output=True, text=True, timeout=60)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            out = (r.stdout or "").strip()
            ok, err = out.startswith("OK"), out
        if not ok:
            FAIL("js", "%s does not parse (%s). This breaks the entire Med Sales Tools page, "
                       "not one panel." % (path, err))


# --------------------------------------------------------------------------
# 6. SHRINK GUARD
# --------------------------------------------------------------------------
def check_shrink():
    for path, count in (("data/trust-map.json", lambda d: len(d.get("trusts", []))),
                        ("data/trust-contacts.json",
                         lambda d: sum(len(v) for v in d.get("trusts", {}).values()))):
        if not os.path.exists(path):
            continue
        old = committed(path)
        if not old:
            continue
        with open(path) as f:
            new = json.load(f)
        o, n = count(old), count(new)
        if o and n < o * 0.9:
            FAIL("shrink", "%s drops from %d to %d (-%.0f%%). Say why in the commit message and "
                           "override deliberately, or find out what broke."
                           % (path, o, n, (1 - n / o) * 100))


# --------------------------------------------------------------------------
# 7. COMPARE FEED — the Compare tab's live issues
# --------------------------------------------------------------------------
# Added 30/07/2026. Until today this gate did not look at compare-issues.json at
# all, which is why three false positives sat in front of paying members for over
# a week: gov.uk weekly round-up INDEX pages filed as though each were a single
# notice about a single product, plus a respiratory notice outside every tracked
# speciality. Deleting them by hand on 29/07 held for one night; the 30/07 refresh
# re-added them because nothing stopped it. These are the checks that would have.
COMPARE_ROUNDUP = re.compile(r"^\s*field safety notices\b", re.I)


def check_compare(store, suppress, comptab_js):
    if not store:
        WARN("compare", "data/compare-issues.json is missing — the Compare tab's live "
                        "issues panel will fall back to whatever is baked into comptab.js.")
        return
    specs = store.get("specialities") or {}
    if not specs:
        FAIL("compare", "compare-issues.json carries no specialities at all.")
        return

    seen_urls = {}
    total = 0
    for sp, blk in specs.items():
        for it in (blk or {}).get("issues", []) or []:
            total += 1
            url = (it.get("url") or "").strip()
            title = it.get("p") or ""

            # Every claim needs a source a reader can open. No exceptions.
            if not url:
                FAIL("compare", "%s: %r has no source URL. Nobody can check it, and the "
                                "dashboard keys your tick boxes on that URL." % (sp, title[:60]))
            elif not url.startswith("https://"):
                FAIL("compare", "%s: %r has a non-HTTPS source (%r)." % (sp, title[:60], url[:60]))
            else:
                key = url.rstrip("/")
                if key in seen_urls:
                    FAIL("compare", "the same notice is filed twice: %r appears under %s and %s."
                                    % (url[:70], seen_urls[key], sp))
                seen_urls[key] = sp

            # The incident check. An index of other people's notices is not a
            # notice: it names no product and never says what the fault was.
            # Citing a round-up as a SOURCE is fine — a person can open it and
            # read out the one notice that matters, which is what happened to the
            # 16-20 February page (now "Convatec EsteemBody ... ref 38578479").
            # What is not fine is an item still WEARING the round-up's title,
            # because then nobody has done that reading.
            curated = not it.get("autoDetected") or (it.get("use") or "").strip()
            if COMPARE_ROUNDUP.match(title):
                if curated:
                    WARN("compare", "%s: %r has been curated but still carries the round-up's "
                                    "title. Name the actual notice and product, as the Convatec "
                                    "EsteemBody entry does." % (sp, title[:70]))
                else:
                    FAIL("compare", "%s: %r is a gov.uk weekly ROUND-UP index page, not a notice "
                                    "about a product — it names no product and never says what "
                                    "the fault was. This is the 22/07-30/07 false-positive class. "
                                    "Automation must refuse these; extracting one notice from a "
                                    "round-up is a person's job." % (sp, title[:70]))

            # A judgement already made must not be silently undone by a re-run.
            if url.rstrip("/") in suppress and not (it.get("use") or "").strip():
                FAIL("compare", "%s: %r is on the suppression list but is back in the feed. "
                                "That is exactly what happened on 30/07/2026 — check "
                                "fetch_issues.py is reading data/suppressed-notices.json."
                                % (sp, title[:60]))

            if not (it.get("d") or "").strip():
                WARN("compare", "%s: %r carries no date label." % (sp, title[:60]))

            # Return and resolution dates became a FIELD on 05/08/2026, so the
            # Compare tab can count down to them instead of burying them in a
            # paragraph. A countdown is a derived claim: if the field is wrong,
            # the page tells a rep with total confidence that they have a week
            # when the stock went back yesterday. So the field is gated.
            for dt in (it.get("dates") or []):
                if not isinstance(dt, dict):
                    FAIL("compare", "%s: %r has a malformed entry in `dates` (%r)."
                                    % (sp, title[:50], dt))
                    continue
                kind = dt.get("kind")
                if kind not in ("deadline", "resolve", "resolved"):
                    FAIL("compare", "%s: %r has a date of unknown kind %r. Use 'deadline' (the "
                                    "trust must act by this date), 'resolve' (the supplier hopes "
                                    "to be back) or 'resolved' (already closed) — the tab colours "
                                    "them differently and must not guess."
                                    % (sp, title[:50], kind))
                on = as_date(dt.get("on"))
                if not on or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(dt.get("on") or "")):
                    FAIL("compare", "%s: %r has a date %r that is not a plain ISO YYYY-MM-DD. "
                                    "The page does the arithmetic on this string."
                                    % (sp, title[:50], dt.get("on")))
                    continue
                if not (dt.get("what") or "").strip():
                    WARN("compare", "%s: %r has a %s date with nothing saying what it is, so the "
                                    "tab will show a bare countdown." % (sp, title[:50], kind))
                # A resolution date in the past means the notice has either
                # closed or slipped, and nobody has looked. Publishing "back in
                # stock 3 weeks ago" next to a live supply gap is worse than
                # publishing no date at all.
                if kind == "resolve" and on < today():
                    WARN("compare", "%s: %r says the supply issue resolves %s, which has passed. "
                                    "Re-read the notice: either it closed and the kind should be "
                                    "'resolved', or the date slipped and needs updating."
                                    % (sp, title[:50], on.isoformat()))
                if kind == "resolved" and on > today():
                    FAIL("compare", "%s: %r is marked resolved on %s, a date in the future."
                                    % (sp, title[:50], on.isoformat()))

    # A cluster pins a group of notices above the speciality picker. It holds no
    # facts of its own — only pointers — so the one way it can lie is by
    # pointing at something that is no longer in the feed, or by claiming a
    # count that no longer matches. Both are checked here rather than trusted.
    for c in (store.get("clusters") or []):
        cid = c.get("id") or "?"
        if not (c.get("title") or "").strip():
            FAIL("compare", "cluster %r has no title." % cid)
        if not (c.get("rule") or "").strip():
            FAIL("compare", "cluster %r states no membership rule. A pinned group that does not "
                            "say what put a notice in it is a claim a reader cannot judge."
                            % cid)
        urls = c.get("urls") or []
        if not urls:
            FAIL("compare", "cluster %r pins no notices." % cid)
        for u in urls:
            if u.rstrip("/") not in seen_urls:
                FAIL("compare", "cluster %r pins %r, which is not in the feed. Either the notice "
                                "was removed and the cluster was not updated, or the URL is "
                                "mistyped — either way the pinned panel is now wrong."
                                % (cid, u[:70]))
        # The rule text quotes a count. If the group grows and the sentence does
        # not, the page states a number that is verifiably false on its own page.
        m = re.search(r"\b(\d+)\s+notices\b", c.get("rule") or "")
        if m and int(m.group(1)) != len(urls):
            FAIL("compare", "cluster %r says %s notices in its membership rule but pins %d."
                            % (cid, m.group(1), len(urls)))

    # Until 30/07/2026 comptab.js merged the feed with `if(D[k])`, so a speciality
    # without a hand-researched entry was silently dropped and 14 of 24 items were
    # in the data and invisible on the page. It now creates an entry for any
    # speciality carrying notices, so the guard is that nobody reinstates the drop.
    if comptab_js:
        if "feedOnly" not in comptab_js:
            FAIL("compare", "app/comptab.js no longer creates entries for specialities it has no "
                            "researched supplier set for. That is the 30/07/2026 regression: items "
                            "stay in the feed and vanish from the page. Look for the merge loop "
                            "and the feedOnly branch.")
        if re.search(r"for\s*\(\s*var\s+k\s+in\s+j\.specialities\s*\)\s*\{\s*if\s*\(\s*D\[k\]\s*\)",
                     comptab_js):
            FAIL("compare", "app/comptab.js has gone back to `if(D[k])` when merging the feed, "
                            "which drops every speciality without a baked-in entry.")

    # A speciality that reaches the dropdown needs a name a rep would recognise.
    # Without one the tab offers "Bloodtx" instead of "Blood and transfusion".
    #
    # products.json SPECS is the authority, so it is asked first. Some real
    # labels are simply the id capitalised — "cardiology" is "Cardiology",
    # "respiratory" is "Respiratory" — and the shape test alone cannot tell
    # those from a missing label. It warned on both, which is the kind of noise
    # that teaches people to skim the gate's output.
    canon = {}
    try:
        canon = {s["id"]: (s.get("label") or "")
                 for s in (load("products.json") or {}).get("SPECS", [])}
    except Exception:
        pass
    for sp, blk in specs.items():
        n = len((blk or {}).get("issues", []) or [])
        if not n:
            continue
        lab = ((blk or {}).get("label") or "").strip()
        if lab and canon.get(sp, "").strip() == lab:
            continue
        if not lab or lab.lower() == sp.lower() or lab.lower() == sp.replace("-", " ").lower():
            WARN("compare", "speciality %r carries %d notice(s) but no proper label (%r), so the "
                            "Compare tab will name it after its internal id. Labels come from "
                            "products.json SPECS via fetch_issues.py." % (sp, n, lab))

    if total == 0:
        FAIL("compare", "the Compare feed is empty — refusing to publish a blank live-issues panel.")
    return total


# --------------------------------------------------------------------------
# 6b. SUPPLIER SETS — the researched half of the Compare tab
# --------------------------------------------------------------------------
def check_suppliers(sup, store):
    """Researched supplier sets moved out of app/comptab.js on 05/08/2026.

    A supplier table is what a rep reads INSTEAD of doing their own research, so
    it fails in ways the issues feed cannot: a framework that expired last year
    still reads as current, and a warning chip can silently point at the wrong
    notice because `iss` indexes the issues array BY POSITION. Both are checked.
    """
    if sup is None:
        WARN("suppliers", "data/compare-suppliers.json is missing — the Compare tab falls back "
                          "to the two sets baked into app/comptab.js and every other speciality "
                          "shows notices only.")
        return
    specs = sup.get("specialities") or {}
    if not specs:
        FAIL("suppliers", "compare-suppliers.json carries no specialities.")
        return
    if not (sup.get("sourceRule") or "").strip():
        FAIL("suppliers", "compare-suppliers.json states no sourceRule. A supplier table is read "
                          "in place of a rep's own research; the reader must be able to see what "
                          "it was built from.")

    feed = (store or {}).get("specialities") or {}
    canon = {}
    try:
        canon = {s["id"]: (s.get("label") or "")
                 for s in (load("products.json") or {}).get("SPECS", [])}
    except Exception:
        pass

    for sp, blk in specs.items():
        who = "suppliers/%s" % sp
        if canon and sp not in canon:
            FAIL("suppliers", "%s is not a speciality the Hub's dropdown can select. Supplier sets "
                              "must key on products.json SPECS ids." % who)
        rows = (blk or {}).get("suppliers") or []
        if not rows:
            FAIL("suppliers", "%s has no suppliers, so it would replace a working notices-only "
                              "panel with an empty table." % who)
            continue

        # A route to market with no dates is the claim most likely to go stale
        # unnoticed — a rep quotes a framework in a tender that ended last year.
        for r in (blk.get("route") or []):
            for field in ("name", "dates", "url"):
                if not (r.get(field) or "").strip():
                    FAIL("suppliers", "%s: a framework entry is missing %r." % (who, field))
            u = (r.get("url") or "")
            if u and not u.startswith("https://"):
                FAIL("suppliers", "%s: framework source %r is not HTTPS." % (who, u[:60]))
            # Dates read "DD/MM/YYYY – DD/MM/YYYY"; the end date is the one that bites.
            ends = re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", r.get("dates") or "")
            if ends:
                d, m, y = ends[-1]
                try:
                    end = datetime.date(int(y), int(m), int(d))
                    if end < today():
                        FAIL("suppliers", "%s: the framework it names ended %s. A rep quoting an "
                                          "expired route to market in a tender conversation is "
                                          "worse than no tool at all — re-read the contract launch "
                                          "brief and update it." % (who, end.strftime("%d/%m/%Y")))
                    elif (end - today()).days <= 90:
                        WARN("suppliers", "%s: the framework it names ends %s, within 90 days. "
                                          "Check whether a successor has been awarded."
                                          % (who, end.strftime("%d/%m/%Y")))
                except ValueError:
                    FAIL("suppliers", "%s: framework dates %r are not readable." % (who, r.get("dates")))

        types = (blk.get("types") or {})
        n_iss = len(((feed.get(sp) or {}).get("issues") or []))
        seen_co = set()
        for s in rows:
            co = (s.get("co") or "").strip()
            if not co:
                FAIL("suppliers", "%s: a supplier row has no company name." % who)
                continue
            if co in seen_co:
                FAIL("suppliers", "%s: %r is listed twice." % (who, co))
            seen_co.add(co)
            if not (s.get("brands") or "").strip():
                FAIL("suppliers", "%s: %r names no brands, so the row tells a rep nothing." % (who, co))
            u = (s.get("url") or "")
            if not u.startswith("https://"):
                FAIL("suppliers", "%s: %r has no HTTPS link of its own." % (who, co))
            for t in (s.get("t") or []):
                if t not in types:
                    FAIL("suppliers", "%s: %r covers product type %r, which is not in this "
                                      "speciality's `types` map, so the dropdown can never show it."
                                      % (who, co, t))
            # THE POSITIONAL TRAP. Chips index the issues array; a notice removed
            # from the middle renumbers everything after it and every chip past
            # that point starts pointing at somebody else's recall.
            for i in (s.get("iss") or []):
                if not isinstance(i, int) or i < 0 or i >= n_iss:
                    FAIL("suppliers", "%s: %r flags issue index %r, but that speciality carries %d "
                                      "notice(s). `iss` indexes the issues array BY POSITION — a "
                                      "notice removed or reordered renumbers every chip after it. "
                                      "Re-point them in the same commit."
                                      % (who, co, i, n_iss))


# --------------------------------------------------------------------------
# 7b. SOURCE LINKS — every citation must still open
# --------------------------------------------------------------------------
# Added 05/08/2026. That morning three Continence/Urology items pointed at NHS
# Supply Chain notices that had been retired, and paying members clicking through
# from Med Sales Tools landed on a 404. Nothing in this gate had ever opened a
# source link, so the only reason it was caught at all was a human reading the
# dashboard. Every claim in this repo is only as good as the link under it.
#
# THIS WARNS AND NEVER FAILS, DELIBERATELY.
# A hard FAIL would let one transient 503, or one rate-limited host, block a
# legitimate push — including the daily refresh workflows, which commit
# unattended. A push blocked by a network blip is a worse outcome than a stale
# link surviving one more run, because the first one stops the data moving at
# all. If a link is genuinely dead the warning repeats every run until somebody
# fixes it; it does not go quiet.
#
# THE CONTROL URL IS THE POINT.
# The other false-alarm mode is the host itself being down or throttling us: then
# every source under it "fails" at once and the output is noise that trains you
# to ignore it. So the control is checked first, and if the control cannot be
# reached the check says so and reports nothing else. This mirrors how the
# 05/08/2026 incident was actually confirmed — the three dead URLs were
# re-checked against a control ICN URL that returned 200, which is what proved
# it was retirement and not rate limiting.
#
# The fix when this warns is in README.md: find the notice's current URL, and if
# it is no longer live on NHSSC anywhere, drop the item and log why.
CONTROL_URL = "https://www.supplychain.nhs.uk/icn/"


def http_status(url, timeout=15):
    """Status code, or a string describing why there wasn't one."""
    try:
        return urlopen(Request(url, headers=UA), timeout=timeout).getcode()
    except Exception as exc:
        return getattr(exc, "code", None) or ("%s: %s" % (type(exc).__name__, exc))


def check_source_links(store, offline, fetch=http_status, pause=time.sleep):
    if offline:
        WARN("links", "skipped the source-link check (--offline). A dead link is member-facing, "
                      "so do not push on this without running it.")
        return
    if not store:
        return

    control = fetch(CONTROL_URL)
    if control != 200:
        WARN("links", "could not run the source-link check: the control URL %s returned %s, so "
                      "NHS Supply Chain is unreachable or throttling us and every source under it "
                      "would look dead. Checked nothing. Re-run later." % (CONTROL_URL, control))
        return

    seen, dead = set(), 0
    for sp, blk in (store.get("specialities") or {}).items():
        for it in (blk or {}).get("issues", []) or []:
            url = (it.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            status = fetch(url)
            if status != 200:
                # Re-check once before saying anything, the way the incident was
                # confirmed. One retry, not a loop: this runs on every push.
                pause(3)
                status = fetch(url)
            if status != 200:
                dead += 1
                WARN("links", "%s: the source for %r returned %s and members clicking through from "
                              "Med Sales Tools land on it. Find the notice's current URL; if it is "
                              "no longer live on NHSSC anywhere, drop the item and log why (see "
                              "README). %s" % (sp, (it.get("p") or "")[:60], status, url))
    if dead:
        WARN("links", "%d of %d source link(s) in the Compare feed did not return 200, checked "
                      "twice each against a control URL that did." % (dead, len(seen)))


# --------------------------------------------------------------------------
# 7. OWNERSHIP NOTICE
# --------------------------------------------------------------------------
def check_notice():
    """Every data file must carry its ownership notice and its marker.

    These files are served to the Hub from a PUBLIC repo, so the page watermark
    and the paywall never touch them. The notice is the only thing on a copy
    that says who owns it, and the ref is the only thing that ties a copy back
    here. Both are easy to lose by accident: build_supplier_index.py rebuilds
    its output from scratch every run and drops anything it was not told to
    write. So the gate checks, rather than trusting the stamper to have run.

    Fix: python3 scripts/stamp_notice.py
    """
    try:
        sys.path.insert(0, "scripts")
        import stamp_notice
    except Exception as exc:
        FAIL("notice", "cannot import scripts/stamp_notice.py (%s), so the ownership "
                       "notice cannot be checked." % exc)
        return

    for name in sorted(os.listdir(DATA)):
        if not name.endswith(".json"):
            continue
        doc = load(name)
        if not isinstance(doc, dict):
            continue
        if name not in stamp_notice.REFS:
            FAIL("notice", "data/%s has no marker ref. Mint one from the private salt in "
                           "the NDA pack and add it to scripts/stamp_notice.py before "
                           "publishing this file." % name)
            continue
        got = doc.get("_notice")
        if got != stamp_notice.notice_for(name):
            FAIL("notice", "data/%s is missing its ownership notice, or it has drifted. "
                           "Run: python3 scripts/stamp_notice.py" % name)


def main():
    offline = "--offline" in sys.argv
    as_json = "--json" in sys.argv
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    optout = load("contacts-optout.json") or {}
    blocked = {n.strip().lower() for n in optout.get("names", []) if n.strip()}

    # Retention is read from the code, so the gate checks what actually runs.
    retention = None
    try:
        src = open("scripts/refresh_fts_contacts.py").read()
        m = re.search(r"^RETENTION_MONTHS\s*=\s*(\d+)", src, re.M)
        retention = int(m.group(1)) if m else None
    except Exception:
        pass
    if retention is None:
        WARN("contacts", "could not read RETENTION_MONTHS from the harvester.")

    trust_codes = check_trust_map(load("trust-map.json"))
    n = check_contacts(load("trust-contacts.json"), trust_codes, blocked, retention) or 0
    check_tags(load("trust-contacts.json"), load("products.json"))
    check_moves(load("people-moves.json"), trust_codes, blocked,
                (load("trust-contacts.json") or {}).get("trusts", {}))
    check_privacy(n, retention, offline)
    check_js()

    suppress = set()
    sup = load("suppressed-notices.json") or {}
    for u in (sup.get("urls") or {}):
        suppress.add(u.rstrip("/"))
    try:
        comptab_js = open(os.path.join("app", "comptab.js")).read()
    except Exception:
        comptab_js = ""
        WARN("compare", "could not read app/comptab.js — cannot check that every filed "
                        "speciality is one the Compare tab can actually render.")
    check_compare(load("compare-issues.json"), suppress, comptab_js)
    check_suppliers(load("compare-suppliers.json"), load("compare-issues.json"))
    check_source_links(load("compare-issues.json"),
                       offline or "--no-links" in sys.argv)

    check_shrink()
    check_notice()

    if as_json:
        print(json.dumps({"pass": not fails, "fails": fails, "warns": warns}, indent=1))
    else:
        for c, m in warns:
            print("WARN  [%s] %s" % (c, m))
        for c, m in fails:
            print("FAIL  [%s] %s" % (c, m))
        print()
        if fails:
            print("VERIFY FAILED — %d failure(s), %d warning(s). Do not push." % (len(fails), len(warns)))
        else:
            print("VERIFY PASSED — %d warning(s)." % len(warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
