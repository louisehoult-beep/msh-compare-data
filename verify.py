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
8. ONE LIST      the Hub is meant to hold one supplier list and one speciality
                 vocabulary. It holds several, and they disagree. Each drift
                 count carries a baseline: rising FAILS, falling WARNS, and any
                 company name NEW in this commit that reaches no supplier
                 record FAILS by name whatever the totals say.
9. COMPANY REPT  Companies House facts, and the two claims the Company Report
                 DERIVES. No market share as a percentage, no count typed into
                 prose, no figure on a probable name match, no band without the
                 dated threshold it was assigned under, no phantom company.
                 A no-op until the feature's files exist.

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

    # 'unsorted' is a holding pen, and the tab must go on skipping it. If that
    # skip is ever removed, whatever the vocabulary could not place goes live
    # with a blank tactical line — which is what happened on 06/08/2026, when the
    # first overnight run after the fallback landed put 28 generic medicines
    # recalls in front of members.
    if (specs.get("unsorted") or {}).get("issues") and comptab_js:
        if "k==='unsorted'" not in comptab_js.replace('"', "'"):
            FAIL("compare", "data carries %d unsorted notice(s) but app/comptab.js no longer skips "
                            "the 'unsorted' holding pen, so items nobody has filed yet would "
                            "publish with blank tactical lines."
                            % len(specs["unsorted"]["issues"]))
    if (specs.get("unsorted") or {}).get("issues"):
        n_un = len(specs["unsorted"]["issues"])
        if n_un >= 25:
            WARN("compare", "%d notices are sitting in the unsorted holding pen. They are not "
                            "published, but nothing is learning from them either — either file "
                            "them under a speciality or tighten what the fetcher collects."
                            % n_un)

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
        # The real question is whether the Compare tab can show this set, not
        # whether the id is in the canonical vocabulary. Two ids the tab renders
        # every day are deliberately NOT in products.json SPECS: `skin-prep`,
        # one of the original keyword buckets, and `product-match`, which is not
        # a body system at all. Failing on those would be the gate refusing to
        # publish a speciality the feed itself uses.
        if canon and sp not in canon and sp not in feed:
            FAIL("suppliers", "%s is a speciality the Compare tab cannot show: it is neither in "
                              "products.json SPECS nor carrying notices in the feed, so nothing "
                              "would ever select it." % who)
        rows = (blk or {}).get("suppliers") or []
        if not rows:
            # A speciality may legitimately have no supplier table. Medicines are
            # the case that forced this: NHS England's MPSC frameworks publish no
            # award list and their prices are confidential to authorised NHS
            # pharmacy staff, so there is no public competitor set to show. The
            # honest output is to say so — inventing one to fill the space is how
            # a comparison tool starts lying to a rep in a meeting. But it has to
            # be a DECLARED absence with a reason a reader can judge, never an
            # empty array somebody forgot to fill.
            if (blk or {}).get("noSuppliers", "").strip():
                continue
            FAIL("suppliers", "%s has no suppliers and no `noSuppliers` explanation, so it would "
                              "replace a working notices-only panel with an empty table. If the "
                              "competitor set genuinely is not public, say so in `noSuppliers`."
                              % who)
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
            # The expiry is shown on the tab with a countdown, so it is a real
            # field, not something re-parsed out of prose at render time. It is
            # cross-checked against the prose here: if someone updates the date
            # range and forgets the field, the page counts down to the old one
            # and says so with total confidence.
            ends = re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", r.get("dates") or "")
            if not (r.get("endsOn") or "").strip():
                # A rolling programme genuinely has no single end date —
                # NHS England's medicines frameworks are the case. That is
                # allowed, but only as a DECLARED absence with a reason, so
                # nobody can quietly ship a route with no expiry at all.
                if not (r.get("noExpiry") or "").strip():
                    FAIL("suppliers", "%s: framework %r has no endsOn and no `noExpiry` reason, so "
                                      "the tab cannot show when it runs out — the most perishable "
                                      "fact on the panel." % (who, (r.get("name") or "")[:50]))
            elif ends:
                d2, m2, y2 = ends[-1]
                if r["endsOn"] != "%s-%s-%s" % (y2, m2, d2):
                    FAIL("suppliers", "%s: framework %r says it ends %s in its date range but "
                                      "endsOn is %r. The page counts down to endsOn."
                                      % (who, (r.get("name") or "")[:40],
                                         "/".join((d2, m2, y2)), r["endsOn"]))
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


# --------------------------------------------------------------------------
# 8. COMPANY REPORT — Companies House facts, and the two claims that are DERIVED
# --------------------------------------------------------------------------
# Added 06/08/2026, written against docs/COMPANY-REPORT-METHOD.md and BEFORE the
# feature ships. Of the panels James Moloney asked for, two are computed rather
# than read: "also on this framework" (co-listing, which is not competition) and
# the field-position band (co-listing x statutory accounts category). Root rule
# 14 governs both — a derived claim carries the rule it was derived under, is
# tested against an invariant that would fail if the logic broke, and refuses to
# fire on thin evidence. The method doc is the specification. If the doc and
# this file disagree, the doc wins and this file is wrong.
#
# BOTH INPUTS ARE OPTIONAL, AND ABSENCE IS A NO-OP.
# Neither data/company-financials.json nor app/company-report.js exists yet.
# Nothing is being published, so there is nothing to refuse — this behaves like
# check_shrink does for a missing path. The two halves are checked
# independently: the source invariants run whenever the JavaScript is there,
# because a percentage in the source is a percentage whether or not today's data
# would reach it.
#
# WHAT THIS CANNOT ENFORCE, SAID PLAINLY RATHER THAN FAKED:
#   * The two evidence floors — fewer than two suppliers on the lot, and fewer
#     than half the field with a resolved accounts category — are runtime
#     conditions over data the page assembles in the browser. This gate can see
#     whether a guard of roughly that shape exists in the source (the same
#     technique as the `feedOnly` guard in check_compare); it cannot prove the
#     guard fires, and it does not claim to.
#   * "Every name rendered resolves to a supplier record carrying that
#     framework" is a render-time fact for the same reason. What IS enforced is
#     the other end of it: every company in the data must resolve to a supplier
#     this repo actually holds.
#   * Whether a probable match is excluded from the size bands. What is
#     enforced is that it carries no figures, and that the source reads
#     matchConfidence at all when probable matches are present — code that
#     never looks at the field cannot be filtering on it.

# The statutory categories, from the method doc's table. Companies House
# publishes other values; mapping one of them belongs in the refresh script and
# in that table, NOT in a quietly widened enum here. A band a reader cannot look
# up is a band nobody can audit.
ACCOUNTS_CATEGORIES = {
    "micro-entity", "small", "small-abridged", "medium", "full", "group", "dormant",
}
# The three statutory thresholds. There is no fourth: "large" is not a
# threshold, it is the name for being above the medium one.
THRESHOLD_BANDS = {"micro", "small", "medium"}
BAND_LABELS = THRESHOLD_BANDS | {"large"}
MATCH_CONFIDENCE = {"confirmed", "probable"}

# A share claim, in the words it would actually be written in. Deliberately
# phrase-based: bare "share" is the Share button on the interview pack, and bare
# "position" is a CSS property. Both would false-FAIL, and a false FAIL blocks
# the unattended refresh workflows from committing — see the long note above
# check_source_links for why that is the worse outcome.
SHARE_CTX = re.compile(
    r"market\s*share|share\s*of\s*(?:the\s*)?(?:market|lot|framework|field)|"
    r"field\s*position|position\s*band|of\s*th(?:is|e)\s*(?:market|lot)|"
    r"share\s*(?:pc|pct|percent)|(?:pc|pct|percent)\s*of\s*(?:the\s*)?market",
    re.I)

# CSS lengths that legitimately end in a percent sign. The property name must be
# followed IMMEDIATELY by its colon, which is what keeps "Position band: 12%"
# out of the exclusion — hence a list of LENGTH properties, not of CSS
# properties. The value may contain quotes and plus signs, because in this repo
# a width is nearly always built by string concatenation.
CSS_LENGTH = re.compile(
    r"\b(?:width|height|max-width|min-width|max-height|min-height|top|left|right|"
    r"bottom|margin(?:-\w+)?|padding(?:-\w+)?|flex|flex-basis|basis|gap|inset|"
    r"border-radius|radius|translate|translatex|translatey|background-size|"
    r"background-position|stroke-dashoffset|size)\s*:\s*[^;{}]{0,30}$", re.I)

# A count typed into rendered prose. Same failure class as the cluster `rule`
# count in check_compare: the sentence and the rows drift apart, and the page
# states a number that its own table contradicts.
COUNT_IN_PROSE = re.compile(
    r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
    r"(?:suppliers?|companies|competitors?|firms?|manufacturers?|files?|filed)\b", re.I)
# ...except where the number is the THRESHOLD being refused, not a count of what
# was rendered. "Only one supplier on this lot" and "fewer than two suppliers on
# the lot" are the evidence floor's own honest empty states — the exact strings
# the method doc requires — and a gate that fails on those is a gate that gets
# the empty state deleted to make a push go through. That is the failure this
# whole file exists to prevent, pointed the wrong way.
COUNT_QUALIFIED = re.compile(r"(?:only|than|least|fewer|under|below)\s+$", re.I)

CO_SUFFIX = re.compile(r"\b(?:limited|ltd|plc|llp|llc|inc|incorporated)\b", re.I)


def _js_scan(src):
    """Blank out comments (length preserved) and return the string-literal spans.

    Literal-aware on purpose. A regex that strips `//` comments eats the tail of
    every "https://..." in the file, and the lines this check reads are exactly
    the lines that carry URLs. Comments are BLANKED rather than removed so the
    offsets still point at the real line, and they are excluded from the scan at
    all because a check that trips on the comment explaining the rule is a check
    somebody deletes — test_verify.py strips comments before its own temp-path
    guard for that same reason.
    """
    out = list(src)
    spans = []
    i, n, quote, start = 0, len(src), None, 0
    while i < n:
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                spans.append((start, i + 1))
                quote = None
            i += 1
            continue
        if c == "\\":                      # an escape inside a regex literal
            i += 2
            continue
        if c in "\"'`":
            quote, start = c, i
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out), spans


def _line_at(src, i):
    a = src.rfind("\n", 0, i) + 1
    b = src.find("\n", i)
    return src[a:(len(src) if b < 0 else b)]


def _norm_co(name):
    """A company name flattened enough that "GBUK GROUP LIMITED" meets "GBUK Group".

    Deliberately shallow. Stripping more — "group", "healthcare", "UK" — would
    start matching different companies to each other, and medtech is full of
    similarly-named entities: the seed already records that Abbott Diabetes Care
    was formerly MediSense (U.K.) Holding Ltd.
    """
    s = re.sub(r"[^\w\s&-]", " ", str(name or "").lower())
    s = CO_SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _supplier_universe():
    """Every supplier name and alias this repo holds, normalised. None if unreadable."""
    names = set()
    seen_file = False
    for fn in ("supplier-seed.json", "supplier-index.json"):
        doc = load(fn)
        if not isinstance(doc, dict):
            continue
        seen_file = True
        for s in (doc.get("suppliers") or []):
            if not isinstance(s, dict):
                continue
            for v in [s.get("name")] + list(s.get("aliases") or []):
                k = _norm_co(v)
                if k:
                    names.add(k)
    return names if seen_file else None


# --------------------------------------------------------------------------
# 9. ONE LIST — supplier and speciality vocabulary drift
# --------------------------------------------------------------------------
# WHY THIS EXISTS
# ---------------
# The Hub is supposed to hold ONE list of suppliers, so that adding a supplier
# makes it appear everywhere it should. It does not. On 06/08/2026 an audit
# found the same companies spelled differently in every file that names them:
# BD alone appears as nine distinct strings across five files — "BD / Bard",
# "Bard Access Systems / BD", "Becton Dickinson", "Becton Dickinson (BD)",
# "Becton Dickinson U.K.", "Becton Dickinson UK", "Becton Dickinson UK Ltd" and
# a corrupt record whose whole name is a sentence listing seven companies —
# against a master that calls it "BD — Becton, Dickinson".
#
# That is not cosmetic. app/supplier-search.js and app/company-report.js fall
# back to a SUBSTRING match when the exact name misses, and return the FIRST
# hit. Run every Compare-tab company name through the live find(): 63 return
# "not yet indexed", and of the 42 that only match on a substring, at least
# three land on the wrong company — "Becton Dickinson UK" resolves to the
# corrupt seven-company record, and "KaVo Dental" resolves to Dentaquip Ltd
# because Dentaquip's product list happens to contain the word KaVo. A rep
# reads that as a company report about the firm they typed.
#
# THE RATCHET
# -----------
# 73 of the 196 Compare-tab companies do not resolve today. Failing on that
# now would block every push, including the two scheduled refreshes, so each
# counter carries a baseline: the gate FAILS when a number RISES and WARNS
# when it falls. New drift is blocked from today; the standing backlog is
# worked down by lowering these numbers, never by raising them (rule 13 — if
# the gate and the data disagree, the data is wrong).
#
# The count is only the backstop. The precise catch is the git diff: any
# company name that is NEW in this commit and does not resolve fails by name,
# whatever the totals say. That is what stops the backlog masking a fresh
# mistake.
#
# WHAT THIS DELIBERATELY DOES NOT DO
# ----------------------------------
# It does not judge whether a company is real. 38 of the unresolved names are
# absent from the master entirely (Alpha Laboratories, Bunzl Healthcare,
# Rocialle, Vitalograph...) and are most likely real suppliers nobody has
# indexed yet. The gate says "this name reaches no record", never "delete it".
# It does not merge, rewrite or normalise any data — a mass merge changes what
# members read and needs Lou's sign-off.
VOCAB_BASELINE = {
    # Distinct companies in compare-suppliers.json reaching no supplier record.
    # 73 on 06/08/2026; lowered to 71 the same day when the supplier-directory
    # merge added the directory's own spellings to aliases[] in the seed and
    # "Ambu" and "Advanced Medical Solutions" started resolving. Lowering a
    # ratchet after the backlog is worked down is how the ratchet is meant to be
    # maintained — it TIGHTENS the gate. It must never be raised.
    # Tightened 71 -> 69 on 07/08/2026: "Becton Dickinson UK" and
    # "Becton Dickinson UK Ltd" are BD's own name and were added to that
    # record's aliases. Until then the first of them resolved, wrongly, to the
    # seven-company record removed the same day.
    "compare_unresolved": 69,        # of 196 distinct companies, 07/08/2026
    # Companies spelled two ways INSIDE compare-suppliers.json itself
    # ("Vygon (UK)" and "Vygon UK"; "ConvaTec" and "Convatec").
    #
    # These 11 no longer fragment the Compare tab's company picker: as of
    # 07/08/2026 each supplier row also carries `ref`, the master record it
    # resolves to, and the picker groups on that. This stays a tracked backlog
    # because the file is still inconsistent with itself and `ref` only masks it
    # where the name resolves — 69 of 196 still reach no master at all.
    "compare_internal_dupes": 11,
    # products.json SPECS vs speciality-map.json canonicalSpecialities.
    #
    # REACHED 0 on 07/08/2026 and is now a HARD FAIL with no baseline —
    # `skin-prep` and `neonatal` were added to SPECS, `skin-prep` and
    # `endourology` to canonicalSpecialities, and both lists hold the same 38
    # ids. Per the design in docs/ONE-LIST-AUDIT.md section D: when a ratchet
    # reaches 0, delete its entry so the check can never tolerate drift again.
    # Adding a speciality to one list only now fails the build outright.
    #
    # Free-text supplier.specialities strings resolving to no canonical id —
    # includes junk the auto-build wrote ("Product Match"). 5 -> 4 on
    # 07/08/2026 when `skin-prep` became canonical, then 4 -> 3 later the same
    # day when the Nikkiso merge retired a stray "Renal / dialysis" spelling.
    "supplier_spec_unresolved": 3,
    # `alias_steals_name` REACHED 0 on 07/08/2026 and is now a HARD FAIL with no
    # baseline. An alias on record A that is, normalised, record B's own NAME
    # hands A every lookup meant for B, because alias resolution is first-wins.
    # 18 of them: 15 were an auto-detected duplicate carried forward beside its
    # seed original ("Medtronic Limited" beside "Medtronic"), now merged and
    # prevented at source in build_supplier_index.py; 2 were duplicate seed
    # records (Vernacare, Nikkiso), merged with the dropped name kept as an
    # alias; 1 was "Abbott Diagnostics" holding "Abbott Laboratories", which is
    # a different company's registered name and sent every FreeStyle Libre
    # lookup to Abbott's diagnostics arm.
    # A supplier record whose name is a list of companies, not a company.
    #
    # REACHED 0 on 07/08/2026 and is now a HARD FAIL with no baseline. The one
    # offender was "B Braun, Baxter, Becton Dickinson UK Ltd, CODAN, Fannin,
    # GBUK Group Ltd and RPG Medical Ltd", deleted from supplier-index.json the
    # same day. split_companies() stops one being CREATED; the carry-forward
    # guard in build_supplier_index.py stops this one being resurrected; this
    # makes a third one impossible to publish by any route.
}

# A name is a list-of-companies, not a company: two or more commas AND a
# conjunction. "BD — Becton, Dickinson" and "Cardinal Health U.K. 432 Ltd"
# both survive this; the seven-company record does not.
LIST_AS_NAME = re.compile(r"\band\b", re.I)


def _compare_companies(sup):
    """Distinct `co` strings across every speciality's supplier rows, in order."""
    out, seen = [], set()
    for blk in ((sup or {}).get("specialities") or {}).values():
        for row in ((blk or {}).get("suppliers") or []):
            co = (row or {}).get("co")
            if isinstance(co, str) and co.strip() and co not in seen:
                seen.add(co)
                out.append(co)
    return out


def _ratchet(check, key, actual, offenders, what, fix):
    """FAIL when a drift count rises above its baseline; WARN when it falls.

    Never silent: a standing backlog that stops being mentioned is a backlog
    that stops being worked.

    A key ABSENT from VOCAB_BASELINE is a backlog that has been cleared to zero
    and graduated to a hard check — the last step of the ratchet, per
    docs/ONE-LIST-AUDIT.md section D. Baseline 0, so a single offender fails the
    build. Deleting the entry is what makes that permanent: there is no longer a
    number anyone can quietly raise.
    """
    base = VOCAB_BASELINE.get(key, 0)
    graduated = key not in VOCAB_BASELINE
    sample = ", ".join(repr(o) for o in sorted(offenders)[:8])
    more = "" if len(offenders) <= 8 else " (+%d more)" % (len(offenders) - 8)
    if graduated:
        if actual:
            FAIL(check, "%s: %d. This reached zero and is now a hard check with no "
                        "baseline — it must stay at zero. %s Offenders: %s%s"
                        % (what, actual, fix, sample, more))
        return
    if actual > base:
        FAIL(check, "%s rose from %d to %d. %s Offenders: %s%s"
                    % (what, base, actual, fix, sample, more))
    elif actual < base:
        WARN(check, "%s is down to %d from a baseline of %d — lower "
                    "VOCAB_BASELINE[%r] to %d so it cannot drift back."
                    % (what, actual, base, key, actual))
    else:
        WARN(check, "%s: %d, unchanged against the recorded baseline. Standing "
                    "backlog, not new drift." % (what, actual))


def check_vocab(sup, products, specmap, index, comptab_js):
    """One list, or an honest count of how far from one list this repo is."""
    if sup is None:
        return                              # check_suppliers already warns

    universe = _supplier_universe()
    if universe is None:
        WARN("vocab", "neither supplier-seed.json nor supplier-index.json could be read, "
                      "so no supplier name can be reconciled. Nothing checked.")
        return

    # -- 1. Compare-tab companies that reach no supplier record --------------
    companies = _compare_companies(sup)
    unresolved = [c for c in companies if _norm_co(c) not in universe]

    # The precise catch: a name NEW in this commit that resolves to nothing.
    # Counts can hide this — remove one old offender, add one new one, and the
    # total is unchanged while a fresh mistake ships.
    was = committed("data/compare-suppliers.json")
    if was is not None:
        before = set(_compare_companies(was))
        fresh = [c for c in unresolved if c not in before]
        if fresh:
            FAIL("vocab", "new supplier name(s) on the Compare tab that reach no record in "
                          "supplier-seed.json or supplier-index.json: %s. A rep who reads "
                          "this name on Compare and types it into Supplier Search gets "
                          "“not yet indexed”, or worse, the first company whose "
                          "products happen to contain the words. Add the company to the "
                          "seed, or add this spelling to an existing record's `aliases`."
                 % ", ".join(repr(c) for c in sorted(fresh)))

    _ratchet("vocab", "compare_unresolved", len(unresolved), unresolved,
             "Compare-tab companies reaching no supplier record",
             "Every name here must exist in supplier-seed.json, as a `name` or in `aliases`.")

    # -- 2. The same company spelled two ways in the same file ---------------
    groups = {}
    for c in companies:
        groups.setdefault(_norm_co(c), set()).add(c)
    dupes = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
    _ratchet("vocab", "compare_internal_dupes", len(dupes),
             [" / ".join(v) for v in dupes.values()],
             "companies spelled more than one way inside compare-suppliers.json",
             "Pick the master's spelling; the Compare tab lists them as separate companies.")

    # -- 3. The two speciality vocabularies -----------------------------------
    # A speciality has to be added ONCE. Today it has to be added to
    # products.json (which fills the dropdown on page 1109 and the Stakeholder
    # Mapper) AND to speciality-map.json (which Meeting Prep and the Company
    # Report reconcile supplier records through). Miss either and the
    # speciality exists in half the Hub.
    specs = {s.get("id") for s in (products or {}).get("SPECS") or [] if s.get("id")}
    canon = {s.get("id") for s in (specmap or {}).get("canonicalSpecialities") or []
             if s.get("id")}
    if specs and canon:
        diff = specs ^ canon
        _ratchet("vocab", "spec_vocab_mismatch", len(diff), sorted(diff),
                 "speciality ids in products.json SPECS but not speciality-map.json "
                 "canonicalSpecialities, or the reverse",
                 "A speciality in only one of the two is selectable in half the tools.")

    # -- 4. Supplier speciality strings that resolve to nothing --------------
    # supplier.specialities is free text. speciality-map.json exists to
    # reconcile it. A string in neither the canonical labels nor the map is a
    # supplier that no speciality filter can reach.
    if canon:
        labels = {s.get("label") for s in (specmap or {}).get("canonicalSpecialities") or []}
        mapped = set((specmap or {}).get("supplierSpecialityMap") or {})
        strings = set()
        for s in ((index or {}).get("suppliers") or []):
            for x in (s.get("specialities") or []):
                if isinstance(x, str) and x.strip():
                    strings.add(x)
        orphan = sorted(x for x in strings if x not in labels and x not in mapped)
        _ratchet("vocab", "supplier_spec_unresolved", len(orphan), orphan,
                 "supplier speciality strings resolving to no canonical speciality",
                 "Add the string to speciality-map.json supplierSpecialityMap, or fix "
                 "whatever wrote it.")

    # -- 5. A supplier record that is not one supplier -----------------------
    malformed = [s.get("name") for s in ((index or {}).get("suppliers") or [])
                 if isinstance(s.get("name"), str)
                 and s["name"].count(",") >= 2 and LIST_AS_NAME.search(s["name"])]
    # -- 6. An alias that is really another record's name ---------------------
    # Alias lookup is first-wins, so this does not just create a duplicate: it
    # silently redirects every reference to the record that owns the name.
    steals = []
    for fn in ("supplier-seed.json", "supplier-index.json"):
        doc = load(fn)
        if not isinstance(doc, dict):
            continue
        recs = [r for r in (doc.get("suppliers") or []) if isinstance(r, dict) and r.get("name")]
        own = {}
        for r in recs:
            own.setdefault(_norm_co(r["name"]), r["name"])
        for r in recs:
            for a in r.get("aliases") or []:
                k = _norm_co(a)
                if k in own and own[k] != r["name"]:
                    steals.append("%s: alias %r is %r's own name" % (r["name"], a, own[k]))
    _ratchet("vocab", "alias_steals_name", len(steals), steals,
             "aliases that are another supplier record's own name",
             "Alias lookup is first-wins, so the wrong record answers for that name. "
             "Remove the alias, or merge the two records.")

    _ratchet("vocab", "malformed_supplier_names", len(malformed), malformed,
             "supplier records whose name is a list of companies rather than a company",
             "build_supplier_index.py lifted a notice's whole supplier field into a "
             "record. Supplier Search will return it to anyone typing any name in it.")

    # -- 6. The baked fallback must reach the master -------------------------
    # HARD FAIL, no baseline: app/comptab.js carries vascular and continence
    # inline so the Compare tab is never empty if the fetch fails. It is clean
    # today and there is no reason it may ever stop being — it is 16 names.
    m = re.search(r"^var D=(\{.*\});\s*$", comptab_js or "", re.M)
    if m:
        try:
            baked = json.loads(m.group(1))
        except Exception:
            WARN("vocab", "app/comptab.js `var D=` is no longer a plain JSON literal, so the "
                          "baked fallback's company names cannot be reconciled.")
            baked = None
        if baked:
            bad = sorted({row["co"] for blk in baked.values()
                          for row in (blk.get("suppliers") or [])
                          if isinstance(row.get("co"), str)
                          and _norm_co(row["co"]) not in universe})
            if bad:
                FAIL("vocab", "app/comptab.js's baked fallback names companies that reach no "
                              "supplier record: %s. This is what members see when the data "
                              "fetch fails, so it is the one supplier list with no way to "
                              "correct it after publication."
                     % ", ".join(repr(b) for b in bad))


def check_company_report(financials, report_js):
    if financials is None and not (report_js or "").strip():
        return                              # feature not built yet — nothing to gate

    clean, spans = _js_scan(report_js or "")
    has_js = bool(clean.strip())

    # ---- source invariants -------------------------------------------------
    if has_js:
        # THE PERCENTAGE INVARIANT. Nobody holds market-share data — Drive
        # DeVilbiss's own commercial director told James Moloney their internal
        # figure is a guess — so a percentage published as share is an invented
        # fact, which is the 24/07/2026 class of error with a different label on
        # it. What may be published is a position band: the count on the lot,
        # and each supplier's statutory accounts category.
        offending = []
        for a, b in spans:
            for m in re.finditer("%", clean[a:b]):
                i = a + m.start()
                if CSS_LENGTH.search(clean[max(0, i - 40):i]):
                    continue                # width:100%, translate(-50%) and friends
                line = _line_at(clean, i).strip()
                if SHARE_CTX.search(line) and line not in offending:
                    offending.append(line)
        for line in offending[:5]:
            FAIL("company-report", "app/company-report.js emits a percent sign in a market-share "
                                   "context: %r. Market share is published as a POSITION BAND and "
                                   "never as a percentage — nobody has the underlying data, so a "
                                   "figure here is invented, not measured. Print the count on the "
                                   "lot and the statutory accounts categories instead."
                                   % line[:140])
        if len(offending) > 5:
            FAIL("company-report", "...and %d further percent sign(s) in a share context "
                                   "(suppressed)." % (len(offending) - 5))

        # A share computed but rendered without the sign is the same claim. This
        # WARNS rather than fails, because the identical arithmetic legitimately
        # sizes a bar in a counts chart and nothing in the source distinguishes
        # the two — a FAIL here would block a push over a bar width.
        for m in re.finditer(r"\*\s*100\b", clean):
            line = _line_at(clean, m.start()).strip()
            if SHARE_CTX.search(line) and not CSS_LENGTH.search(clean[max(0, m.start() - 40):m.start()]):
                WARN("company-report", "app/company-report.js computes a percentage on a line "
                                       "about market share or field position: %r. If that number "
                                       "reaches the page it is an invented market share; if it is "
                                       "only a bar width it is fine. The gate cannot tell them "
                                       "apart from the source — check it." % line[:140])
                break

        # THE COUNT INVARIANT. Same failure class as the cluster `rule` count in
        # check_compare: prose drifted from the data it described. A count in a
        # rendered string is typed, so it cannot follow the rows.
        typed = []
        for a, b in spans:
            lit = clean[a:b]
            for m in COUNT_IN_PROSE.finditer(lit):
                if COUNT_QUALIFIED.search(lit[max(0, m.start() - 16):m.start()]):
                    continue                # "only one supplier", "fewer than two suppliers"
                if lit not in typed:
                    typed.append(lit)
                break
        for lit in typed[:5]:
            FAIL("company-report", "app/company-report.js has a count typed into rendered prose: "
                                   "%r. The sentence must be built from the rows it describes "
                                   "(the length of the list you are about to render), or it states "
                                   "a number the table beneath it contradicts — which is exactly "
                                   "what the cluster `rule` count check exists to stop."
                                   % lit[:120])
        if len(typed) > 5:
            FAIL("company-report", "...and %d further typed count(s) in rendered prose "
                                   "(suppressed)." % (len(typed) - 5))

        # The evidence floors, as far as a source read can see them. This
        # recognises a SHAPE — it does not prove the floor fires. Said here
        # rather than left implied.
        if not re.search(r"<\s*2\b|<\s*=\s*1\b", clean):
            WARN("company-report", "app/company-report.js contains nothing shaped like the "
                                   "two-supplier evidence floor. One supplier on a framework is a "
                                   "framework with one supplier, not a competitive field, and the "
                                   "panel must refuse to render. This gate can only recognise the "
                                   "shape of that guard in the source; it cannot prove it fires.")
        # `known/2`, `known*2 < total`, `*0.5` and the word "half" are all the
        # same guard written four ways. Recognising all four keeps this quiet
        # once the floor is really there — a warning that fires on correct code
        # is the noise that teaches people to skim the gate's output. It is also
        # held back until the accounts categories exist at all: the floor guards
        # a comparison of resolved categories, and nagging for it while there is
        # no such data is nagging for something nobody can write yet.
        if financials is not None and not re.search(
                r"/\s*2\b|\*\s*2\b|\*\s*0?\.5\b|half", clean, re.I):
            WARN("company-report", "app/company-report.js contains nothing shaped like the "
                                   "half-the-field floor. A size comparison built on a third of "
                                   "the lot is not a size comparison. Same limitation: the gate "
                                   "sees a shape, not a behaviour.")

    if financials is None:
        WARN("company-report", "app/company-report.js is present but data/company-financials.json "
                               "is not, so every company fact and every size band in it is "
                               "unchecked. The source invariants above ran; nothing else did.")
        return

    # ---- data ---------------------------------------------------------------
    if not isinstance(financials, dict):
        FAIL("company-report", "data/company-financials.json is not a JSON object.")
        return
    if not has_js:
        WARN("company-report", "data/company-financials.json is present but app/company-report.js "
                               "is not, so the percentage invariant and the typed-count invariant "
                               "could not be checked at all. They are source checks.")

    companies = financials.get("companies")
    if not isinstance(companies, dict) or not companies:
        FAIL("company-report", "data/company-financials.json carries no companies. Refusing to "
                               "publish a company-facts panel with nothing in it — an honest empty "
                               "state is the page's job, not an empty data file's.")
        return

    as_of = as_date(financials.get("dataAsOf"))
    if not as_of:
        FAIL("company-report", "data/company-financials.json has no usable dataAsOf (%r). Every "
                               "figure on this panel is quoted as at a date."
                               % financials.get("dataAsOf"))
    elif as_of > today():
        FAIL("company-report", "data/company-financials.json is stamped dataAsOf %s, a date in the "
                               "future. Companies House cannot have been read tomorrow." % as_of)

    banded = sorted(n for n, r in companies.items()
                    if isinstance(r, dict) and str(r.get("accountsCategory") or "").strip())
    th = financials.get("thresholds")
    if not isinstance(th, dict) or not th:
        if banded:
            FAIL("company-report", "%d company record(s) carry an accountsCategory but the file has "
                                   "no `thresholds` block. A band assigned without the threshold it "
                                   "was assigned under is unauditable — and the thresholds changed "
                                   "for periods beginning on or after 6 April 2025, so which set "
                                   "was used is the whole question. e.g. %s"
                                   % (len(banded), ", ".join(banded[:3])))
    else:
        read_on = as_date(th.get("readOn"))
        if not read_on:
            FAIL("company-report", "the `thresholds` block has no usable readOn (%r). An undated "
                                   "threshold cannot be checked against the rules in force when "
                                   "the band was assigned." % th.get("readOn"))
        elif read_on > today():
            FAIL("company-report", "the `thresholds` block says it was read on %s, a date in the "
                                   "future." % read_on)
        src_url = str(th.get("readFrom") or "").strip()
        if not src_url:
            FAIL("company-report", "the `thresholds` block has no readFrom. The statutory figures "
                                   "are a fact with a shelf life; without the page they were read "
                                   "from, nobody can re-check them.")
        elif not src_url.startswith("https://"):
            FAIL("company-report", "the `thresholds` block cites a non-HTTPS source (%r)."
                                   % src_url[:70])
        if not (th.get("appliesTo") or "").strip():
            WARN("company-report", "the `thresholds` block does not say which accounting periods "
                                   "it applies to, so a reader cannot tell whether a band was "
                                   "assigned under the pre- or post-April-2025 figures.")
        bands = th.get("bands")
        if not isinstance(bands, dict) or not bands:
            if banded:
                FAIL("company-report", "the `thresholds` block carries no band figures, so the page "
                                       "would print a band with no threshold beside it. The whole "
                                       "point of the band is that a reader can look the figure up.")
        else:
            odd = sorted(set(bands) - THRESHOLD_BANDS)
            if odd:
                FAIL("company-report", "the `thresholds` block invents band(s) %s. The statutory "
                                       "set is %s — 'large' is not a threshold, it is the name for "
                                       "being above the medium one. A band nobody legislated is a "
                                       "band we made up."
                                       % (", ".join(repr(o) for o in odd),
                                          ", ".join(sorted(THRESHOLD_BANDS))))

    universe = _supplier_universe()
    if universe is None:
        WARN("company-report", "could not read supplier-seed.json or supplier-index.json, so the "
                               "companies in this file were not checked against the suppliers this "
                               "repo actually holds.")

    probable = []
    for name in sorted(companies):
        rec = companies[name]
        who = "company %r" % name
        if not isinstance(rec, dict):
            FAIL("company-report", "%s is not a record." % who)
            continue

        conf = str(rec.get("matchConfidence") or "").strip().lower()
        if conf not in MATCH_CONFIDENCE:
            FAIL("company-report", "%s records matchConfidence %r. It must be one of %s — a third "
                                   "value slips past a `=== 'probable'` filter and a name-search "
                                   "match then feeds the size bands, which is how the wrong "
                                   "company's finances get attached to a named business."
                                   % (who, rec.get("matchConfidence"),
                                      ", ".join(sorted(MATCH_CONFIDENCE))))
        if conf == "probable":
            probable.append(name)

        # NULL MEANS NOT DISCLOSED, AND 0 DOES NOT.
        # Small and micro companies are legally permitted to omit the profit and
        # loss account, and most UK medtech subsidiaries do. The page renders
        # null as "turnover not disclosed"; a 0 renders as a figure, and tells a
        # rep a trading company turned over nothing. It is a parse bug.
        for field in ("turnoverGBP", "employees"):
            v = rec.get(field)
            if v is None:
                continue
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                FAIL("company-report", "%s has %s = %r, which is neither a number nor null."
                                       % (who, field, v))
            elif v == 0:
                FAIL("company-report", "%s has %s = 0. In this file null means 'not disclosed' and "
                                       "the page prints that phrase; 0 prints as a real figure — a "
                                       "trading company with no turnover, or no staff. It is a "
                                       "parse bug, not a fact. Use null." % (who, field))
            elif v < 0:
                FAIL("company-report", "%s has a negative %s (%r) — the same parse bug as a 0, one "
                                       "sign further on." % (who, field, v))

        # A name-search match is a guess about identity. It may be shown as a
        # company fact; it may not carry figures, because a wrong match attaches
        # the wrong company's finances to a named business.
        if conf == "probable":
            for field in ("turnoverGBP", "employees"):
                if rec.get(field) is not None:
                    FAIL("company-report", "%s is a PROBABLE match (matched by name search) but "
                                           "carries %s = %r. A probable match feeds no derived "
                                           "claim: medtech is full of similarly-named entities and "
                                           "a wrong match puts another company's finances against "
                                           "this name. Confirm it by company number or drop the "
                                           "figure." % (who, field, rec.get(field)))
            if str(rec.get("accountsCategory") or "").strip():
                WARN("company-report", "%s is a PROBABLE match and carries an accountsCategory, "
                                       "which is what the field-position band is built from. Only "
                                       "confirmed matches may feed the band — check the report "
                                       "excludes it before this ships." % who)

        cat = str(rec.get("accountsCategory") or "").strip()
        if cat and cat not in ACCOUNTS_CATEGORIES:
            FAIL("company-report", "%s has accountsCategory %r, which is not one of the statutory "
                                   "categories (%s). If Companies House has started returning a "
                                   "new value, map it in scripts/refresh_companies_house.py and "
                                   "add it to the table in docs/COMPANY-REPORT-METHOD.md — do not "
                                   "widen this list to let an unmapped value through."
                                   % (who, cat, ", ".join(sorted(ACCOUNTS_CATEGORIES))))

        for key in ("band", "sizeBand", "positionBand"):
            lab = str(rec.get(key) or "").strip().lower()
            if lab and lab not in BAND_LABELS:
                FAIL("company-report", "%s carries %s = %r, which is not one of the statutory band "
                                       "labels (%s). A band computed ad hoc is our estimate wearing "
                                       "a legal band's clothes."
                                       % (who, key, rec.get(key), ", ".join(sorted(BAND_LABELS))))

        if rec.get("turnoverGBP") is not None and not str(rec.get("accountsMadeUpTo") or "").strip():
            FAIL("company-report", "%s discloses a turnover with no accountsMadeUpTo. A turnover "
                                   "figure is shown WITH the date the accounts were made up to, "
                                   "never bare — otherwise a 2019 figure reads as this year's."
                                   % who)

        for field in ("accountsMadeUpTo", "incorporated"):
            d = rec.get(field)
            if d in (None, ""):
                continue
            when = as_date(d)
            if not when:
                FAIL("company-report", "%s has an unreadable %s (%r)." % (who, field, d))
            elif when > today():
                FAIL("company-report", "%s has %s = %s, a date in the future." % (who, field, when))

        # PHANTOM COMPANY. Every company on this panel must be one this repo
        # holds a supplier record for. A name that resolves to nothing is a
        # company we have invented a report about.
        if universe:
            keys = [_norm_co(name), _norm_co(rec.get("registeredName"))]
            if not any(k and k in universe for k in keys):
                FAIL("company-report", "%s does not resolve to any supplier in supplier-seed.json "
                                       "or supplier-index.json (tried %r and %r). A company report "
                                       "about a company this repo has no record of is a report "
                                       "about nobody — and the panels around it claim framework "
                                       "co-listings drawn from those very files."
                                       % (who, keys[0], keys[1]))

    if probable and has_js and not re.search(r"matchConfidence|probable", clean):
        FAIL("company-report", "%d record(s) are probable name-search matches, and "
                               "app/company-report.js never reads matchConfidence or mentions "
                               "'probable'. Code that never looks at the field cannot be excluding "
                               "those records from the size bands, so a guess about identity is "
                               "feeding a derived claim. e.g. %s"
                               % (len(probable), ", ".join(repr(p) for p in probable[:3])))


def check_no_clusters_on_tools(comptab_js):
    """Standing clusters must never render on the Med Sales Tools page.

    Ruled by Lou, 06/08/2026. A cluster was pinned ABOVE the speciality picker
    and shown whatever the member had selected, so a single running supply story
    sat in front of everybody and buried the speciality they came to read. That
    class of item belongs on the Live Desk.

    This is a check rather than a comment because a comment is a memory, and a
    memory is what the last person edited straight past. Rendering a cluster
    means iterating CLUSTERS — there is no other way to get one on screen — so
    that is what this looks for. The declaration, the assignment from the feed
    and any `.length` guard all stay legal: the data contract is unchanged and
    the Live Desk still consumes the same key.
    """
    if not comptab_js:
        return
    # _js_scan returns (comment-blanked source, string-literal spans) — take the
    # source. Comments are blanked so the note explaining this very rule, which
    # names CLUSTERS, cannot trip the check that enforces it.
    src = _js_scan(comptab_js)[0]
    for pat, why in (
        (r"CLUSTERS\s*\.\s*forEach", "iterates CLUSTERS"),
        (r"CLUSTERS\s*\[\s*\d", "indexes into CLUSTERS"),
        (r"for\s*\(\s*var\s+\w+\s*=\s*0\s*;[^;]*CLUSTERS\s*\.\s*length", "loops over CLUSTERS"),
    ):
        m = re.search(pat, src)
        if m:
            FAIL("clusters", "app/comptab.js %s at offset %d. Standing clusters must not "
                             "render on the tools page — that was ruled on 06/08/2026 after a "
                             "pinned thread buried the speciality picker for every member. "
                             "Put it on the Live Desk (page 675, via the cloud-pipeline) instead."
                             % (why, m.start()))
            return


def check_compare_groups_by_ref(comptab_js):
    """The Compare tab's company picker must group on the master record.

    Lou, 07/08/2026: picking "GBUK Group" offered Vascular access and nothing
    else, for a company on 20 NHS Supply Chain frameworks. The picker matched
    `s.co` exactly, so a firm written four ways in compare-suppliers.json became
    four companies each holding a quarter of its footprint. Nineteen companies
    were split this way and the tool looked like it was working.

    A comment is a memory and a memory is what the last person edited past, so
    this is a check. Two things have to hold, and both are cheap to break by
    accident while editing something else nearby:

      1. coKey() still reads `ref` before falling back to `co`. Drop the `ref`
         arm and every merge silently reverts.
      2. Nothing compares `.co` directly against the picker's value again. That
         is the exact line that caused this, and it read perfectly sensibly.

    Reading `s.co` is still legal and necessary — it is what the table prints,
    and what allCompanies() lists as the alternative spellings. Only comparing
    it against the selection is banned.
    """
    if not comptab_js:
        return
    src = _js_scan(comptab_js)[0]          # comments blanked, so this note is safe

    if not re.search(r"function\s+coKey\s*\([^)]*\)\s*\{[^}]*\.\s*ref\b", src):
        FAIL("compare-ref", "app/comptab.js has no coKey() resolving `ref` before `co`. "
                            "Without it the company picker groups on the raw `co` string and "
                            "one firm becomes as many companies as it has spellings — GBUK "
                            "showed 1 speciality of 7 on 07/08/2026. See refRule in "
                            "data/compare-suppliers.json.")
        return

    # `s.co === me` / `s.co === onlyCo` and the reverse. Comparing the display
    # string against the picker's value is the bug itself.
    bad = re.search(r"\.\s*co\s*={2,3}\s*(me|onlyCo)\b|\b(me|onlyCo)\s*={2,3}\s*\w+\s*\.\s*co\b", src)
    if bad:
        FAIL("compare-ref", "app/comptab.js compares `.co` against the picker's value at "
                            "offset %d. Use coKey(), which resolves `ref` first — comparing the "
                            "display spelling is what made GBUK four separate companies. "
                            "Printing `.co` in the table is fine; matching on it is not."
             % bad.start())


def check_curated_test_matches(comptab_js):
    """The renderer and the gate must agree on what "curated" means.

    Found live 07/08/2026. `verify.py` judges an item curated with
    `not autoDetected or use.strip()`. `app/comptab.js` printed its red
    "NEW — auto-detected, verify at source" banner on `it.autoDetected` ALONE —
    and that flag records how an item ARRIVED, so it never goes false. The result
    was 12 curated items on Med Sales Tools telling a paying member not to trust
    the tactical line written directly beneath them, in the house's own warning
    colour.

    THE PUBLISH GATE COULD NOT SEE IT, because nothing in it read the renderer.
    It reported success on the commit that made it worse. That is the actual
    lesson: a gate over the data alone cannot catch a data/renderer disagreement,
    and this is the class of bug that produces.

    So this checks the renderer's own test, not the output. The banner must be
    guarded by BOTH `autoDetected` and an emptiness test on `use`.
    """
    if not comptab_js:
        return
    src = _js_scan(comptab_js)[0]          # comments blanked
    m = re.search(r"if\s*\(([^)]*?)\)\s*\{[^{}]*auto-detected, verify at source", src)
    if not m:
        # The banner text itself is gone, or it is no longer inside a simple
        # guard. Either way this check can no longer prove anything, and saying
        # so is better than passing silently.
        if "auto-detected, verify at source" in src:
            WARN("curated", "app/comptab.js still prints the auto-detected banner but its guard "
                            "could not be read, so it was not checked. Look at it by hand.")
        return
    guard = m.group(1)
    if "autoDetected" not in guard:
        FAIL("curated", "app/comptab.js prints the auto-detected banner without testing "
                        "`autoDetected` at all: guard is %r." % guard[:90])
        return
    if not re.search(r"!\s*\(?\s*\(?\s*\w*\.?use\b", guard):
        FAIL("curated", "app/comptab.js prints “NEW — auto-detected, verify at source” on "
                        "`autoDetected` alone (guard: %r). That flag records how an item "
                        "ARRIVED and never goes false, so every curated item wears a warning "
                        "telling the reader not to trust the tactical line beneath it. "
                        "verify.py treats an item as curated when `use` is non-empty — the "
                        "renderer must use the same test." % guard[:90])


def check_ref_present(sup):
    """A row whose `co` resolves to a master record must carry that `ref`.

    coKey() falls back to `co` when `ref` is absent, which is right for the 69
    names that reach no master — they stay visible as themselves. But it means a
    MISSING ref is indistinguishable from an unresolvable one at render time,
    and it fails silently: the row simply becomes its own company in the picker
    again.

    Caught while building the patient-handling set on 07/08/2026, hours after
    the fix. Eight rows were hand-written without `ref` and "GBUK Healthcare"
    split straight back out of GBUK Group into a separate one-speciality entry —
    the identical bug, reintroduced by the person who had just removed it.
    Deriving `ref` once is not enough; the invariant has to be enforced, or the
    next hand-added row does this again.
    """
    if not sup:
        return
    # Same two files and the same loader as _supplier_universe(), so this check
    # and the ratchet can never disagree about what the master holds. The seed
    # is read first and wins ties: it is the human-owned record.
    universe = {}
    for fn in ("supplier-seed.json", "supplier-index.json"):
        doc = load(fn)
        if not isinstance(doc, dict):
            continue
        for s in doc.get("suppliers") or []:
            if not isinstance(s, dict):
                continue
            nm = s.get("name")
            if not nm:
                continue
            for key in [nm] + list(s.get("aliases") or []):
                k = _norm_co(key)
                if k and k not in universe:
                    universe[k] = nm
    if not universe:
        WARN("compare-ref", "no supplier record could be read, so no `ref` was checked.")
        return

    missing, wrong = [], []
    for sk, blk in ((sup.get("specialities") or {})).items():
        for row in (blk or {}).get("suppliers") or []:
            co = (row.get("co") or "").strip()
            if not co:
                continue
            should = universe.get(_norm_co(co))
            if not should:
                continue                    # genuinely unresolved — groups as itself, correctly
            ref = row.get("ref")
            if ref is None:
                missing.append("%s: %r -> %r" % (sk, co, should))
            elif ref != should:
                wrong.append("%s: %r says ref %r, master is %r" % (sk, co, ref, should))

    if missing:
        FAIL("compare-ref", "%d Compare-tab supplier row(s) resolve to a master record but carry "
                            "no `ref`, so the company picker lists each as its own company again — "
                            "the bug fixed on 07/08/2026. Add `ref` beside `co`. %s%s"
             % (len(missing), "; ".join(missing[:6]),
                "" if len(missing) <= 6 else " (+%d more)" % (len(missing) - 6)))
    if wrong:
        FAIL("compare-ref", "%d Compare-tab supplier row(s) name a `ref` that is not the master "
                            "record their `co` resolves to. %s%s"
             % (len(wrong), "; ".join(wrong[:6]),
                "" if len(wrong) <= 6 else " (+%d more)" % (len(wrong) - 6)))


# --------------------------------------------------------------------------
# 10. HUB SEARCH INDEX — what a member can find, and what they must not be shown
# --------------------------------------------------------------------------
# Added 06/08/2026 with app/hub-search.js, and written against the two ways this
# index can be wrong in a manner nobody notices from looking at the page.
#
#   1. NAV CONTAMINATION. Every Hub page carries the same header listing every
#      section name. If the strip in build_search_index.py ever stops working,
#      every page contains every nav word, so every query matches all 65 pages
#      and search silently reverts to the "returns all random stuff" behaviour
#      this replaced. The page still looks perfect. Only an invariant catches it.
#
#   2. STALE ROTATING CONTENT. The Live Desk's panels are rewritten hourly and
#      this index rebuilds daily. If the volatile strip fails, search starts
#      pointing members at headlines that left the Hub hours ago — presented as
#      Hub content, which is the class of thing root rule 16 exists to stop.
#
# Neither is visible in the output unless something checks for it, which is the
# lesson of 24/07/2026: one line would have caught it and nobody had written it.
SEARCH_INDEX = "hub-search-index.json"

# A section's words are stored as a BAG: unique, alphabetised, stopwords gone.
# That is what stops this public file being readable as the Hub's paid content
# (see the note above MAX_WORDS in build_search_index.py). It also means neither
# check below can look for a phrase — word order does not survive — so both are
# written as set tests instead.

# Nav-only labels. Any one of these can appear in real Hub prose; SIX of them in
# one section cannot, because that is the header listing the whole site. This is
# the shape the old phrase probe had before the index stopped carrying prose.
NAV_WORDS = frozenset((
    "pathways", "briefings", "trackers", "theatres", "conferences", "podcasts",
    "icons", "careers", "glossary", "downloads", "reference", "frameworks",
))
NAV_MIN = 6

# Pages the cloud pipeline rewrites faster than this index is rebuilt. Their
# rotating rows are date-stamped ("03 AUG"), so a month abbreviation in the bag
# means a row got indexed. "may" cannot false-positive: it is a stopword and is
# dropped before the bag is built.
PIPELINE_PAGES = {675}
MONTHS = frozenset(("jan", "feb", "mar", "apr", "jun", "jul",
                    "aug", "sep", "sept", "oct", "nov", "dec"))


def check_search_index(doc):
    """The Hub's own search index: is it real, is it whole, is it clean?"""
    if not doc:
        WARN("search", "data/%s is missing — Hub search on page 675 will fall back to "
                       "WordPress core search. Run build_search_index.py." % SEARCH_INDEX)
        return

    pages = doc.get("pages")
    if not isinstance(pages, list) or not pages:
        FAIL("search", "data/%s has no pages. Publishing this takes Hub search offline "
                       "for every member." % SEARCH_INDEX)
        return

    # -- shape ------------------------------------------------------------
    for p in pages:
        if not p.get("t") or not p.get("u"):
            FAIL("search", "a page in %s has no title or no URL (id %r). A result a member "
                           "cannot click is worse than no result." % (SEARCH_INDEX, p.get("id")))
            break

    # -- every link must stay on the Hub ----------------------------------
    for p in pages:
        u = str(p.get("u") or "")
        if not u.startswith("/"):
            FAIL("search", "%s indexes an absolute or off-site URL (%r). Search results must "
                           "stay on this site." % (SEARCH_INDEX, u[:80]))
            break

    # -- shrink guard -----------------------------------------------------
    # A crawl that half-fails returns a valid, small index. Without this the
    # repo would happily publish "the Hub has four pages".
    old = committed("data/" + SEARCH_INDEX)
    if old and isinstance(old.get("pages"), list):
        o, n = len(old["pages"]), len(pages)
        if o and n < o * 0.9:
            FAIL("search", "%s drops from %d pages to %d (-%.0f%%). Either the crawl failed or "
                           "pages were deleted; say which in the commit message and override "
                           "deliberately." % (SEARCH_INDEX, o, n, (1 - n / o) * 100))
        oldrec, newrec = len(old.get("records") or []), len(doc.get("records") or [])
        if oldrec and newrec < oldrec * 0.9:
            FAIL("search", "%s drops from %d records to %d. Supplier names would stop being "
                           "findable." % (SEARCH_INDEX, oldrec, newrec))

    # -- the index must not be readable as Hub content --------------------
    # The whole protection is that a section stores a bag of words rather than
    # prose. If a future edit puts running text back under another key, this
    # public file starts publishing a paywalled product again.
    allowed = {"h", "a", "w"}
    for p in pages:
        for s in p.get("sec") or []:
            extra = set(s.keys()) - allowed
            if extra:
                FAIL("search", "%s carries unexpected field(s) %s on a section of %r. Sections "
                               "hold a heading, an anchor and a bag of words and nothing else — "
                               "this repo is PUBLIC, so anything readable here republishes the "
                               "Hub. Ruled 06/08/2026."
                     % (SEARCH_INDEX, sorted(extra), p.get("t")))
                return
            words = (s.get("w") or "").split()
            if words != sorted(set(words)):
                FAIL("search", "%s has an unsorted or duplicated word bag on %r. Sorting and "
                               "de-duplication are what stop the prose being reassembled; if "
                               "the order is meaningful, the text is still in here."
                     % (SEARCH_INDEX, p.get("t")))
                return

    # -- nav contamination ------------------------------------------------
    for p in pages:
        for s in p.get("sec") or []:
            words = set((s.get("w") or "").split())
            hit = NAV_WORDS & words
            if len(hit) >= NAV_MIN:
                FAIL("search", "%s has the page header in its words (%d nav labels in one "
                               "section of %r: %s). Every page then matches every query and "
                               "search returns everything, while the page still looks perfect. "
                               "Fix the strip in build_search_index.py — do not relax this."
                     % (SEARCH_INDEX, len(hit), p.get("t"), ", ".join(sorted(hit))))
                return

    # -- rotating content that would be stale by the time it is searched ---
    for p in pages:
        if p.get("id") not in PIPELINE_PAGES:
            continue
        for s in p.get("sec") or []:
            hit = MONTHS & set((s.get("w") or "").split())
            if hit:
                FAIL("search", "%s indexes the hourly rows on page %r (month %r in the word "
                               "bag). This index rebuilds daily, so those results point at items "
                               "already gone from the page. The VOLATILE strip in "
                               "build_search_index.py has stopped working."
                     % (SEARCH_INDEX, p.get("t"), sorted(hit)[0]))
                return

    # -- records must land somewhere that resolves ------------------------
    for r in doc.get("records") or []:
        u = str(r.get("u") or "")
        if not u.startswith("/medical-sales-hub/"):
            FAIL("search", "%s has a record pointing off the Hub (%r)." % (SEARCH_INDEX, u[:80]))
            break

    if not doc.get("records"):
        WARN("search", "%s carries no dataset records, so supplier names are not findable. "
                       "build_search_index.py reads data/supplier-index.json — check it ran."
             % SEARCH_INDEX)

    # -- size, because every member downloads this ------------------------
    # The index is fetched into the browser the first time somebody uses the
    # search box. Nothing else in this repo is shipped to a member that way, so
    # nothing else has ever needed a size limit. Left unchecked, raising
    # SECTION_CHARS or MAX_SECTIONS in build_search_index.py would quietly make
    # the Hub slower for everyone, and the only symptom would be a search box
    # that feels sluggish — which nobody reports and nobody can attribute.
    path = os.path.join(DATA, SEARCH_INDEX)
    if os.path.exists(path):
        mb = os.path.getsize(path) / (1024.0 * 1024.0)
        if mb > 4:
            FAIL("search", "%s is %.1f MB. Every member downloads this on their first "
                           "search. Tighten SECTION_CHARS or MAX_SECTIONS in "
                           "build_search_index.py rather than raising this limit."
                 % (SEARCH_INDEX, mb))
        elif mb > 2:
            WARN("search", "%s is %.1f MB, which is large for a file the browser fetches. "
                           "Worth trimming SECTION_CHARS before it grows further."
                 % (SEARCH_INDEX, mb))


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
    check_vocab(load("compare-suppliers.json"), load("products.json"),
                load("speciality-map.json"), load("supplier-index.json"), comptab_js)
    check_source_links(load("compare-issues.json"),
                       offline or "--no-links" in sys.argv)

    # The Company Report. Both halves are optional today — neither file exists —
    # and both are read the same way the Compare tab's data and source are.
    report_js = ""
    report_path = os.path.join("app", "company-report.js")
    if os.path.exists(report_path):
        try:
            report_js = open(report_path).read()
        except Exception as exc:
            WARN("company-report", "could not read app/company-report.js (%s) — the percentage "
                                   "and typed-count invariants were not checked." % exc)
    check_company_report(load("company-financials.json"), report_js)

    check_search_index(load(SEARCH_INDEX))

    check_shrink()
    check_notice()
    check_no_clusters_on_tools(comptab_js)
    check_compare_groups_by_ref(comptab_js)
    check_ref_present(load("compare-suppliers.json"))
    check_curated_test_matches(comptab_js)

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
