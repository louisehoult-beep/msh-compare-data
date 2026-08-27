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
10. AWARDS       every award attached to a named company is re-matched from the
                 same rule the writer used, carries its notice link and date,
                 and never a value of 0. The quarantine may hold nothing that
                 is publishable, the counts must equal the rows, an incomplete
                 walk must say so, and the page may never say a company HAS no
                 awards — only that this index has not captured any.

11. COMPANY PRESS  every published news story is re-derived from the same
                 match rule the writer applied, carries two distinct publishers
                 and working links, states honestly whether each link was
                 resolved to the publisher or is still a Google News redirect,
                 and the header counts equal the rows. Every supplier carries the
                 date it was last checked, so an empty panel reads as empty
                 rather than broken. A no-op until the file exists.

Usage
    python3 verify.py            # full run, including the live privacy check
    python3 verify.py --offline  # skip network checks (still fails on logic)
    python3 verify.py --no-links # skip only the source-link check
    python3 verify.py --json

Exit codes
    0  passed — safe to push
    1  FAILED — do not push until every FAIL is resolved
"""

import hashlib, json, os, re, subprocess, sys, datetime, shutil, tempfile, time
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
# 5b. TRUST PRESSURES
# --------------------------------------------------------------------------
def check_trust_pressures(doc, trust_codes):
    """The published figures behind every trust's Meeting Prep profile.

    This file is a COPY of someone else's numbers — NHS England's RTT return,
    the CQC's ratings, UKHSA's C. difficile counts — put in front of a rep who
    will quote them to the trust that produced them. Two ways that goes wrong,
    and both are checked here rather than trusted:

    1. A number that cannot be true. A percentage over 100, a median wait of
       900 weeks, an oversight segment of 7 — each means the upstream column
       moved and we copied the wrong one. The rep finds out in the meeting.
    2. A number with no period on it. "52,000 waiting" is not a fact without
       the month it describes; RTT is monthly and a figure quoted a year late
       is simply wrong. So every period must be present and every source must
       carry a resolvable URL, because root rule 12 says a figure without its
       source does not get published.

    Codes are checked against the trust map for the same reason the contacts
    check is: a figure filed against a trust that does not exist is a figure
    attached to nothing.
    """
    if not doc:
        return                                  # optional file — absence is not a failure
    trusts = doc.get("trusts") or {}
    if len(trusts) < 120:
        FAIL("pressures", "only %d trusts carry published figures (expected ~148). A shrunken "
                          "snapshot means the upstream fetch failed — rebuild with "
                          "scripts/build_trust_pressures.py rather than publishing a gap."
                          % len(trusts))

    for key in ("rtt", "cqc", "neverEvents", "cdiff", "eric"):
        if not (doc.get("periods") or {}).get(key):
            FAIL("pressures", "no period recorded for the %s figures. A trust-level number "
                              "without the period it covers cannot be quoted safely." % key)
    for name, src in (doc.get("sources") or {}).items():
        if not str(src.get("url", "")).startswith("http"):
            FAIL("pressures", "source '%s' has no URL. Every figure a member reads must link "
                              "to the publisher that issued it." % name)

    # Ranges that would have to be a mis-read column, not a real trust.
    BOUNDS = {"pct18": (0, 100), "med": (0, 200), "seg": (1, 4),
              "wl": (0, 5_000_000), "ne": (0, 100), "cdi": (0, 5000)}
    unknown = []
    for code, t in trusts.items():
        if trust_codes and code not in trust_codes:
            unknown.append(code)
        for field, (lo, hi) in BOUNDS.items():
            v = t.get(field)
            if v is None:
                continue
            if not isinstance(v, (int, float)) or v < lo or v > hi:
                FAIL("pressures", "%s (%s) has %s=%r, outside the possible range %s-%s. The "
                                  "upstream column has almost certainly moved — do not publish "
                                  "it." % (t.get("name", code), code, field, v, lo, hi))
        for sp, wks in (t.get("spec") or {}).items():
            if not isinstance(wks, (int, float)) or wks < 0 or wks > 200:
                FAIL("pressures", "%s: median wait for %s is %r weeks, which cannot be right."
                                  % (t.get("name", code), sp, wks))
    if unknown:
        FAIL("pressures", "%d ODS codes carry figures but are not in the trust map (%s). A "
                          "figure filed against a trust that does not exist is attached to "
                          "nothing." % (len(unknown), ", ".join(sorted(unknown)[:8])))

    # STALENESS. This file cannot refresh itself in CI — it is built from the
    # PRIVATE pipeline repo, which this repo's Actions runner has no credential
    # for — so the only thing standing between a member and a year-old waiting
    # list is somebody remembering to rebuild it. Make the gate remember
    # instead: WARN at six weeks (RTT is monthly, so one missed cycle), FAIL at
    # twelve. Fix: python3 scripts/build_trust_pressures.py
    try:
        stamped = datetime.datetime.strptime(doc.get("asOf", ""), "%d/%m/%Y").date()
        days = (datetime.date.today() - stamped).days
    except Exception:
        FAIL("pressures", "no readable asOf date (got %r). Figures with no date on them "
                          "cannot be published." % doc.get("asOf"))
        return
    if days > 84:
        FAIL("pressures", "the published figures were last rebuilt %d days ago (%s). RTT is a "
                          "monthly return — this is at least two cycles behind and members "
                          "would be quoting it as current. Run: python3 "
                          "scripts/build_trust_pressures.py" % (days, doc.get("asOf")))
    elif days > 42:
        WARN("pressures", "the published figures were last rebuilt %d days ago (%s). Rebuild "
                          "before the next push: python3 scripts/build_trust_pressures.py"
                          % (days, doc.get("asOf")))


# --------------------------------------------------------------------------
# 6. SHRINK GUARD
# --------------------------------------------------------------------------
def check_shrink():
    for path, count in (("data/trust-map.json", lambda d: len(d.get("trusts", []))),
                        ("data/trust-pressures.json",
                         lambda d: len(d.get("trusts", {}))),
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

# A framework entry that asserts a MONEY VALUE or an AWARD DATE is the single
# most quotable thing on the product: a rep reads "£140m ex VAT" off the tab and
# says it out loud to a category manager who negotiates that contract for a
# living. Getting it wrong is not a cosmetic error, it is the rep's credibility.
#
# The launch-brief entries are safe: refresh_frameworks.py stamps every one with
# url + source + capturedOn, so they are re-read and they carry a link a reader
# can open. The hand-curated entries are not. Nothing revisits them, so a
# "re-tender, award ~27/07/2026" typed in months ago is still sitting there
# three weeks after that date with nobody told.
#
# check_trust_pressures and check_compare already refuse to publish a figure
# with no source ("Every claim needs a source a reader can open. No exceptions").
# This applies the same rule to the seed, where the biggest numbers actually are.
def check_seed_framework_provenance(seed):
    suppliers = seed.get("suppliers") if isinstance(seed, dict) else seed
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    suppliers = suppliers or []

    # An award DATE is a claim with a fuse on it: "award ~27/07/2026" is fine on
    # the day it is written and misleading the day after, so it needs the same
    # provenance as a price. Plain "Awarded supplier" / "Awarded on Lot 7" is a
    # different, non-perishable kind of statement — a record of a past fact, not
    # a countdown — so only a date sitting next to the word counts here. Without
    # that qualifier this fired on hundreds of harmless "Awarded supplier" notes
    # and buried the handful of genuinely stale, undated re-tender claims.
    award_claim = re.compile(r"(?:award|re-?tender)\D{0,20}\d{1,2}/\d{1,2}/\d{2,4}"
                              r"|\d{1,2}/\d{1,2}/\d{2,4}\D{0,20}(?:award|re-?tender)", re.I)
    unsourced_no_value = 0

    for s in suppliers:
        who = s.get("name") or "(unnamed supplier)"
        for f in (s.get("frameworks") or []):
            sourced = bool((f.get("source") or "").strip()
                           or (f.get("url") or "").strip()
                           or (f.get("capturedOn") or "").strip())
            if sourced:
                u = (f.get("url") or "")
                if u and not u.startswith("https://"):
                    FAIL("seed-frameworks",
                         "%s: framework %r has a non-HTTPS source (%r)."
                         % (who, str(f.get("name"))[:50], u[:60]))
                continue

            value = (f.get("value") or "").strip()
            dates = (f.get("dates") or "").strip()
            note = (f.get("note") or "").strip()
            asserts_award = bool(award_claim.search(dates) or award_claim.search(note))

            if value:
                FAIL("seed-frameworks",
                     "%s: framework %r states a value of %r with no source, url or capturedOn. "
                     "A money figure a rep will quote has to link to the page it came from. "
                     "Add the NHS Supply Chain or Find a Tender URL it was read from, or "
                     "remove the value and keep the framework name."
                     % (who, str(f.get("name"))[:50], value[:40]))
            elif asserts_award:
                FAIL("seed-frameworks",
                     "%s: framework %r asserts an award or re-tender (%r) with no source, url or "
                     "capturedOn. An award date goes stale on a known day and nothing re-reads "
                     "this entry, so it has to carry the notice it came from."
                     % (who, str(f.get("name"))[:50], (dates or note)[:60]))
            else:
                unsourced_no_value += 1

    # Not a failure, but it should not be invisible either. These are entries
    # carrying only a framework name, so the harm is much lower, but every one
    # is a claim nothing in the pipeline will ever re-check.
    if unsourced_no_value:
        print("  note: %d seed framework entries carry no provenance but assert no value or "
              "award date. Lower risk, still unmaintained." % unsourced_no_value)


def check_seed_product_categories(seed):
    """`productCategories` (added 25/08/2026 by scripts/backfill_product_categories.py)
    holds framework CATEGORY labels — "Diagnostic Equipment and Services" — not
    product names, and it must stay legible as a different kind of fact to
    `products`, which is reserved for genuine branded/model-level names.

    Checked here:
    - every entry names a category and cites a source
    - the cited frameworkRef actually exists in THAT supplier's own
      `frameworks[]` — a category cannot be sourced to a framework the
      supplier isn't even on
    - `productCategories` and `products` never collide: no string appears in
      both, which would be the first sign of the two fields being conflated
      instead of kept separate
    """
    suppliers = seed.get("suppliers") if isinstance(seed, dict) else seed
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    suppliers = suppliers or []

    checked = 0
    for s in suppliers:
        pcs = s.get("productCategories")
        if not pcs:
            continue
        who = s.get("name") or "(unnamed supplier)"
        checked += 1

        own_refs = {fw.get("reference") for fw in (s.get("frameworks") or [])
                    if isinstance(fw, dict) and fw.get("reference")}
        products = set()
        for p in (s.get("products") or []):
            products.add(p if isinstance(p, str) else (p.get("name") if isinstance(p, dict) else None))
        products.discard(None)

        seen_categories = set()
        for row in pcs:
            if not isinstance(row, dict):
                FAIL("seed-product-categories", "%s: productCategories entry is not an object "
                                                 "(%r) — every entry must carry `category` and "
                                                 "`source`." % (who, row))
                continue
            cat = (row.get("category") or "").strip()
            if not cat:
                FAIL("seed-product-categories", "%s: a productCategories entry has no category." % who)
            if cat in seen_categories:
                FAIL("seed-product-categories", "%s: category %r appears more than once in "
                                                 "productCategories — should be deduped per "
                                                 "supplier." % (who, cat))
            seen_categories.add(cat)

            src = row.get("source")
            if not isinstance(src, dict) or not (src.get("frameworkRef") or src.get("frameworkName")):
                FAIL("seed-product-categories", "%s: productCategories entry %r has no source "
                                                 "(frameworkRef/frameworkName) — a derived category "
                                                 "must say which framework it came from."
                                                 % (who, cat[:50]))
                continue
            ref = src.get("frameworkRef")
            if ref and own_refs and ref not in own_refs:
                FAIL("seed-product-categories", "%s: productCategories entry %r cites framework "
                                                 "reference %r, which is not in this supplier's own "
                                                 "frameworks[] — a category cannot be sourced to a "
                                                 "framework the supplier isn't recorded as being on."
                                                 % (who, cat[:50], ref))

            # The conflation guard: a framework CATEGORY label must never also
            # be sitting in `products` as if it were a product name.
            if cat and cat in products:
                FAIL("seed-product-categories", "%s: %r appears in both `products` and "
                                                 "`productCategories` — these are different kinds "
                                                 "of fact (branded product vs. framework category) "
                                                 "and must never be conflated." % (who, cat[:60]))

    if checked:
        print("  note: %d supplier(s) carry productCategories, checked for provenance and no "
              "overlap with `products`." % checked)
    # Follow-up, not a gate failure: this repo has no page renderer to check.
    # Whatever WordPress/app code reads supplier-seed.json for the Hub pages
    # must label a `productCategories` chip distinctly from `products` (e.g.
    # "Framework category" vs "Products") rather than merging the two arrays
    # into one undifferentiated list — that check has to happen where the
    # renderer actually lives, which is outside this repo/session.


# --------------------------------------------------------------------------
# 6c. SEED LEADERSHIP AND PARTNERSHIPS — named people and named counterparties
# --------------------------------------------------------------------------
# Added 19/08/2026 alongside the leadership/partnerships panels in
# app/company-report.js.
#
# A NAMED PERSON PLUS AN UNSOURCED CLAIM IS THE 24/07/2026 CLASS OF ERROR.
# That incident published 145 job changes about named NHS staff, every one
# false, because a plausible derivation was allowed to stand without evidence a
# reader could open. Leadership claims are the same shape with different names
# in them: "ran GBUK's Banana division", "18 years in patient handling" — each
# is a statement about a real, identifiable person's career, published on a paid
# product. It carries the URL it was read from or it does not publish.
#
# A PARTNERSHIP ROW IS A CLAIM ABOUT TWO COMPANIES AT ONCE, so it needs the same
# floor, plus a declared confidence. The Arjo/Jeenie arrangement is the case
# that forced the field: both parties state it, it appears on neither party's
# own website, and it must never render as a verified commercial agreement just
# because a link exists. So `confidence` is required and always shown — a row
# that omits it would default to reading as confirmed, which is the failure.
def _sp_norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _structured_corpus(s):
    """All prose a supplier carries in the structured background fields."""
    bits = []
    for b in (s.get("background") or []):
        bits.append(b.get("text") or "")
    lead = s.get("leadership") or {}
    for p in (lead.get("people") or []):
        bits.append(p.get("note") or "")
        for c in (p.get("claims") or []):
            bits.append(c.get("text") or "")
    for p in (s.get("partnerships") or []):
        bits.append(p.get("note") or "")
    ft = s.get("frameworkTiming") or {}
    bits.append(ft.get("note") or "")
    return _sp_norm(" ".join(bits))


ALERT_KINDS = ("safety", "supply")


def _curated_alert(a):
    """True for a hand-written alert. An issue-derived one carries `_id`."""
    return not (isinstance(a, dict) and a.get("_id"))


def _alert_text(a):
    if isinstance(a, str):
        return a
    return " ".join(x for x in (a.get("title"), a.get("text"), a.get("detail")) if x)


def check_curated_alerts_are_typed(index):
    """A curated alert must say which of the two things it is.

    "Alerts & recalls" was one bucket holding two unlike things: a dated safety
    or availability event a rep must answer for, and curated background prose
    about who owns the company. 272 of 383 curated entries were the second kind,
    so the panel a member reads for safety was mostly corporate history — and a
    genuine FDA Class I recall sat in the same list as a note about a site move.

    There is no heuristic that separates them reliably: "delisting" is a product
    leaving a catalogue in one entry and a share listing ending in the next, and
    a company called Advanced Sterilization Products trips every keyword there
    is. So the distinction is DECLARED, not guessed. Every curated alert carries
    `kind`, and background prose has no valid kind — its home is `background[]`,
    which renders in Part 1 where it belongs.

    This is the check that stops the bucket refilling.
    """
    suppliers = (index or {}).get("suppliers") or []
    if not suppliers:
        WARN("alert-kind", "could not read supplier-index.json, so curated alert typing was "
                           "not checked.")
        return
    bad = []
    for s in suppliers:
        for a in (s.get("alerts") or []):
            if not _curated_alert(a):
                continue
            kind = a.get("kind") if isinstance(a, dict) else None
            if kind not in ALERT_KINDS:
                bad.append((s.get("name") or "(unnamed)", _alert_text(a)[:80], kind))
    for name, text, kind in bad[:5]:
        FAIL("alert-kind",
             "%s: a curated alert declares kind=%r. Every hand-written alert must declare "
             "`kind`: \"safety\" (a recall, field safety notice or regulator action) or "
             "\"supply\" (a product delisted, suspended, discontinued, end-of-life or "
             "unavailable). If it is neither — ownership, legal entity, a categorisation "
             "correction, an acquisition, a re-tagging note — it is BACKGROUND and belongs in "
             "`background[]`, not in the panel members read for safety. Entry: %r"
             % (name, kind, text))
    if len(bad) > 5:
        FAIL("alert-kind", "...and %d further untyped curated alert(s) (suppressed)."
                           % (len(bad) - 5))


def check_seed_links(seed):
    """A member-facing link that returns 200 and still shows an error page.

    Added 27/08/2026. 191 supplier records carried
    `https://my.supplychain.nhs.uk/catalogue/search/0?query=<name>` as their
    "NHS Supply Chain catalogue" link. Every one of them was dead: the stray
    `/0` segment redirects to `/catalogue/Error/Http404`. The correct path is
    `/catalogue/search?query=<name>`, which renders "Search products - NHS
    Supply Chain Online Catalogue".

    check_source_links() could never have caught this, and that is the point
    worth remembering. It asks for an HTTP status, and the dead URL answers
    200 — the 404 is a redirect to an error PAGE, not an error CODE. A soft
    404 is invisible to a status check, so the shape is banned by name here
    instead. When a link is found dead by hand, ban the shape; do not assume
    the status check will pick up the next one.
    """
    suppliers = seed.get("suppliers") if isinstance(seed, dict) else seed
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    suppliers = suppliers or []

    # Shapes proven dead by hand, with the date and the replacement. A URL is
    # only ever added here after somebody has opened both and seen the
    # difference — never on suspicion.
    DEAD = [
        ("my.supplychain.nhs.uk/catalogue/search/0?",
         "redirects to /catalogue/Error/Http404 (checked by hand 27/08/2026). "
         "Drop the '/0': my.supplychain.nhs.uk/catalogue/search?query=<name>"),
    ]

    bad = []
    for s in suppliers:
        who = s.get("name") or "(unnamed supplier)"
        for l in (s.get("links") or []):
            u = (l.get("url") or "") if isinstance(l, dict) else ""
            for shape, why in DEAD:
                if shape in u:
                    bad.append((who, l.get("label") if isinstance(l, dict) else None, u, why))

    for who, label, u, why in bad[:5]:
        FAIL("seed-links",
             "%s: the %r link points at a URL known to be dead — %s. Members click this from "
             "the Company Report and land on an error page, and the source-link check cannot "
             "see it because the dead URL answers HTTP 200. URL: %s"
             % (who, label or "(unlabelled)", why, u))
    if len(bad) > 5:
        FAIL("seed-links", "...and %d further supplier record(s) carrying the same dead link "
                           "shape (suppressed)." % (len(bad) - 5))

    # The seed was only where the shape was FOUND. Read on 27/08/2026 it was also
    # in differentiator.json (287), interview-prep.json (174), supplier-index.json
    # and four deepDive blocks — and hardcoded twice in the script that rebuilds
    # the Differential every night, so fixing the data alone would have let it
    # regenerate by morning. A banned URL has to be banned everywhere it can be
    # written, generator included, or the ban only holds until the next rebuild.
    ALSO = ["data/differentiator.json", "data/interview-prep.json",
            "data/supplier-index.json", "data/compare-suppliers.json",
            "scripts/build_differentiator.py", "scripts/build_interview_prep.py",
            "build_supplier_index.py"]
    for rel in ALSO:
        try:
            with open(rel, encoding="utf-8") as fh:
                raw = fh.read()
        except (IOError, OSError):
            continue
        for shape, why in DEAD:
            n = raw.count(shape)
            if n:
                FAIL("seed-links",
                     "%s carries the dead link shape %d time(s) — %s. Fix the file AND whatever "
                     "generates it; a data-only fix regenerates broken on the next run."
                     % (rel, n, why))


def check_seed_index_alert_parity(seed, index):
    """The seed and the index must agree about curated alerts.

    THE ASYMMETRY THAT CAUSED THE 19/08/2026 DEFECT. `alerts` is the one field
    mergeSuppliers() does NOT copy from the seed: the page reads it from the
    index alone. So editing the seed's alerts changes nothing a member sees, and
    editing only the index is undone by the next rebuild, which regenerates a
    curated supplier's record from the seed. Either edit on its own looks like a
    clean commit and is silently wrong, in opposite directions.

    Requiring the two to agree makes that impossible to ship: a one-sided edit
    fails here, naming the file that was missed.
    """
    seed_suppliers = seed.get("suppliers") if isinstance(seed, dict) else seed
    if isinstance(seed_suppliers, dict):
        seed_suppliers = list(seed_suppliers.values())
    idx_suppliers = (index or {}).get("suppliers") or []
    if not seed_suppliers or not idx_suppliers:
        WARN("alert-kind", "could not read both supplier-seed.json and supplier-index.json, so "
                           "seed/index alert parity was not checked.")
        return

    idx_by = {s.get("name"): s for s in idx_suppliers}
    drifted = []
    for s in seed_suppliers:
        rec = idx_by.get(s.get("name"))
        if rec is None:
            continue                    # seed-only supplier: the index has yet to be rebuilt
        a = sorted(_sp_norm(_alert_text(x)) for x in (s.get("alerts") or []) if _curated_alert(x))
        b = sorted(_sp_norm(_alert_text(x)) for x in (rec.get("alerts") or []) if _curated_alert(x))
        if a != b:
            drifted.append((s.get("name") or "(unnamed)", len(a), len(b)))
    for name, ns, ni in drifted[:5]:
        FAIL("alert-kind",
             "%s: curated alerts disagree between the seed (%d) and the index (%d). The page "
             "reads alerts from data/supplier-index.json, and the nightly rebuild regenerates "
             "the index from data/supplier-seed.json — so an edit to one file alone is either "
             "invisible to members or silently reverted. Make the same edit in both, in this "
             "commit." % (name, ns, ni))
    if len(drifted) > 5:
        FAIL("alert-kind", "...and %d further supplier(s) whose curated alerts disagree "
                           "(suppressed)." % (len(drifted) - 5))


def check_migrated_prose_not_in_alerts(seed, index):
    """The prose must leave alerts[] when it moves to a structured panel.

    THIS IS THE 19/08/2026 ERROR, GATED.

    mergeSuppliers() in app/company-report.js does NOT copy `alerts` from the
    seed — alerts are read from data/supplier-index.json only. So removing a
    curated entry from the SEED's alerts changes nothing on the page: the prose
    keeps rendering under "Alerts & recalls" while the new panel renders the
    same fact beside it. One fact, two homes, on a paid product, which is what
    root rule 18 exists to stop. It happened between 2b9205a and 692d14a in one
    direction and again on the migration commit in the other.

    The check is deliberately narrow. Curated prose in alerts[] is normal and
    widespread across this index, so its mere presence cannot fail. What fails
    is prose that has ALREADY been given a structured home on the same company
    and is still sitting in alerts as well — a duplicate, not a judgement call.
    """
    seed_suppliers = seed.get("suppliers") if isinstance(seed, dict) else seed
    if isinstance(seed_suppliers, dict):
        seed_suppliers = list(seed_suppliers.values())
    idx_suppliers = (index or {}).get("suppliers") or []
    if not seed_suppliers or not idx_suppliers:
        WARN("seed-people", "could not read both supplier-seed.json and supplier-index.json, so "
                            "the migrated-prose duplication check did not run.")
        return

    idx_by_name = {s.get("name"): s for s in idx_suppliers}
    for s in seed_suppliers:
        corpus = _structured_corpus(s)
        if len(corpus) < 80:
            continue                    # nothing migrated on this company
        rec = idx_by_name.get(s.get("name"))
        if not rec:
            continue
        for a in (rec.get("alerts") or []):
            # An issue-derived alert carries _id and is written by the refresh,
            # not by hand. It is never a migration leftover.
            if isinstance(a, dict) and a.get("_id"):
                continue
            text = a if isinstance(a, str) else (a.get("text") or a.get("detail") or "")
            n = _sp_norm(text)
            if len(n) < 60:
                continue
            # A 60-character run of the alert appearing verbatim in a structured
            # field is a copy, not a coincidence.
            if any(n[i:i + 60] in corpus for i in range(0, max(1, len(n) - 60), 20)):
                FAIL("seed-people",
                     "%s: prose that already has a structured panel (background, leadership, "
                     "partnerships or frameworkTiming) is STILL in data/supplier-index.json "
                     "alerts[]: %r. The page reads alerts from the INDEX, not the seed — "
                     "removing it from the seed alone changes nothing a member sees, and the "
                     "fact then renders twice. Delete it from the index in the same commit "
                     "(root rule 18)." % (s.get("name") or "(unnamed)", text[:90]))


def check_seed_people_and_partners(seed):
    suppliers = seed.get("suppliers") if isinstance(seed, dict) else seed
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    if not suppliers:
        WARN("seed-people", "could not read supplier-seed.json, so leadership and partnership "
                            "provenance was not checked.")
        return

    for s in suppliers:
        who = s.get("name") or "(unnamed supplier)"

        # Background is the one field here that MAY be unsourced: the panel
        # draws an unsourced entry on a dashed edge and says it is a prompt to
        # check, which is the honest state for "read off the company's own
        # about page". What it may not do is carry a broken or insecure link,
        # or an entry with no text at all.
        for b in (s.get("background") or []):
            if not (b.get("text") or "").strip():
                FAIL("seed-people", "%s: a background entry carries no text." % who)
            u = (b.get("url") or "").strip()
            if u and not u.startswith("https://"):
                FAIL("seed-people", "%s: background entry %r cites a non-HTTPS source (%r)."
                                    % (who, (b.get("heading") or "")[:40], u[:60]))

        lead = s.get("leadership") or {}
        for p in (lead.get("people") or []):
            name = (p.get("name") or "").strip()
            if not name:
                FAIL("seed-people", "%s: a leadership entry has no person name." % who)
                continue
            # `officer: true` asserts a Companies House register fact. The
            # register states an appointment date for every officer, so an
            # officer with no date means the register was not actually read.
            if p.get("officer") and not (p.get("appointed") or "").strip():
                FAIL("seed-people", "%s: %r is published as a Companies House officer with no "
                                    "appointed date. Officer status is a register fact and the "
                                    "register carries the date — read it, or set officer:false "
                                    "and describe them as an employee."
                                    % (who, name[:60]))
            for c in (p.get("claims") or []):
                text = (c.get("text") or "").strip()
                if not text:
                    FAIL("seed-people", "%s: %r carries an empty claim." % (who, name[:60]))
                    continue
                u = (c.get("url") or "").strip()
                if not u:
                    FAIL("seed-people", "%s: the claim %r about %r has no source URL. This is a "
                                        "statement about a named, identifiable person on a paid "
                                        "product — it carries the page it was read from, or it "
                                        "does not publish. (Root rule 16; the 24/07/2026 class of "
                                        "error.)" % (who, text[:70], name[:60]))
                elif not u.startswith("https://"):
                    FAIL("seed-people", "%s: the claim about %r cites a non-HTTPS source (%r)."
                                        % (who, name[:60], u[:60]))

        for p in (s.get("partnerships") or []):
            with_who = (p.get("with") or "").strip()
            if not with_who:
                FAIL("seed-people", "%s: a partnership row names no counterparty." % who)
                continue
            u = (p.get("url") or "").strip()
            if not u:
                FAIL("seed-people", "%s: the partnership with %r has no source URL. A partnership "
                                    "row is a claim about two companies at once and is read by "
                                    "reps as a route to market — it carries the page it was read "
                                    "from, or it does not publish."
                                    % (who, with_who[:60]))
            elif not u.startswith("https://"):
                FAIL("seed-people", "%s: the partnership with %r cites a non-HTTPS source (%r)."
                                    % (who, with_who[:60], u[:60]))
            if not (p.get("confidence") or "").strip():
                FAIL("seed-people", "%s: the partnership with %r declares no `confidence`. Without "
                                    "it the row renders as a verified commercial agreement, which "
                                    "is precisely what an uncorroborated arrangement is not. Use "
                                    "\"confirmed\", or say it is claimed by the parties."
                                    % (who, with_who[:60]))


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


WEBSITE_ROUTE_PHRASE = "published on the company's own website"


def _check_website_proofs(companies):
    """Route 2 must be able to show its working, or it is not a route.

    A record confirmed by route 2 (docs/COMPANY-REPORT-METHOD.md — the number the
    company publishes on its own site) claims a source a reader can open. This is
    the invariant root rule 14 asks for: it fails if the chain from evidence to
    published confidence ever breaks, in either direction.

      * a record whose `matchedOn` claims route 2 must have a matching
        `companyNumberProof` in supplier-seed.json, with the SAME number, a URL
        and a verbatim evidence string;
      * a seed proof must not be malformed, or refresh_companies_house.py will
        silently ignore it and the supplier stays probable for no visible reason.

    Without this, a bug that dropped `companyNumberProof` on the seed rewrite —
    exactly the failure mode the 14/08/2026 commit warns about, where the nightly
    rebuild destroys index-only edits — would leave records asserting a website
    source that no longer exists anywhere in the repo.
    """
    seed = load("supplier-seed.json")
    if not isinstance(seed, dict):
        WARN("company-report", "could not read supplier-seed.json, so website-proved company "
                               "numbers were not checked against their evidence.")
        return

    proofs = {}
    for s in (seed.get("suppliers") or []):
        if not isinstance(s, dict):
            continue
        p = s.get("companyNumberProof")
        if p is None:
            continue
        name = s.get("name")
        if not isinstance(p, dict):
            FAIL("company-report", "supplier %r carries a companyNumberProof that is not a "
                                   "record. It will be ignored, and the supplier will stay "
                                   "`probable` with nothing on the page saying why." % name)
            continue
        number = str(p.get("number") or "").strip().upper()
        if not re.match(r"^(?:[A-Z]{2}\d{6}|\d{8})$", number):
            FAIL("company-report", "supplier %r records a companyNumberProof number %r, which is "
                                   "not a company number (eight digits, or two letters and six)."
                                   % (name, p.get("number")))
        if not str(p.get("url") or "").strip() or not str(p.get("evidence") or "").strip():
            FAIL("company-report", "supplier %r records a companyNumberProof with no %s. Route 2 "
                                   "confirms a company number by quoting the company's own page — "
                                   "a proof nobody can open is not a proof, and must not raise a "
                                   "record to `confirmed`."
                                   % (name, "url" if not str(p.get("url") or "").strip() else "evidence"))
        if name:
            proofs[name] = number

    for name in sorted(companies):
        rec = companies[name]
        if not isinstance(rec, dict):
            continue
        if WEBSITE_ROUTE_PHRASE not in str(rec.get("matchedOn") or ""):
            continue
        if name not in proofs:
            FAIL("company-report", "company %r is confirmed on the strength of a number published "
                                   "on its own website, but supplier-seed.json holds no "
                                   "companyNumberProof for it. The evidence has been lost and the "
                                   "page is citing a source this repo can no longer produce." % name)
            continue
        held = str(rec.get("companyNumber") or "").strip().upper()
        if held != proofs[name]:
            FAIL("company-report", "company %r is confirmed by website proof of %s, but the record "
                                   "carries company number %s. The confirmation belongs to a "
                                   "different company from the one whose finances are published."
                                   % (name, proofs[name], held or "(none)"))



def _check_candidate_wording(companies):
    """A seed record must not still call a number unverified after it was confirmed.

    `companyNumberCandidate` is written by backfill_seed_from_frameworks.py when a
    number is first found by NAME SEARCH, and its `matchedOn` says so in terms:
    "NOT verified against a number published by the company". That sentence is true
    on the day it is written. It stops being true the moment
    confirm_company_numbers.py and refresh_companies_house.py raise the company to
    `matchConfidence: "confirmed"` in data/company-financials.json — and nothing was
    updating the seed block when that happened, so 54 records were still calling a
    confirmed number unverified on 27/08/2026. Lou read that as "probably wrong",
    which is exactly the wrong impression: the number had been proved off the
    company's own website.

    This is the same class of failure as `_check_website_proofs` above and is held
    the same way: the two files may only be separated by a bug, and the gate is what
    notices. Root rule 18 — a superseded statement is corrected, never left standing.

    HARD CHECK, no baseline. It was cleared to zero on 27/08/2026.

    Note it deliberately does NOT touch the 804 records that are genuinely still
    `probable`. Their wording is correct and is the honest empty state the Company
    Report renders as "IDENTITY NOT CONFIRMED".
    """
    seed = load("supplier-seed.json")
    if not isinstance(seed, dict):
        return                              # _check_website_proofs already warned

    stale, disagree = [], []
    for s in (seed.get("suppliers") or []):
        if not isinstance(s, dict):
            continue
        cand = s.get("companyNumberCandidate")
        if not isinstance(cand, dict):
            continue
        rec = companies.get(s.get("name")) or {}
        if str(rec.get("matchConfidence") or "").lower() != "confirmed":
            continue
        held = str(cand.get("number") or "").strip().upper()
        conf = str(rec.get("companyNumber") or "").strip().upper()
        if held and conf and held != conf:
            disagree.append("%s: seed candidate %s, confirmed %s" % (s.get("name"), held, conf))
            continue
        if "NOT verified" in str(cand.get("matchedOn") or ""):
            stale.append(s.get("name"))

    _ratchet("company-report", "candidate_says_unverified_after_confirmation",
             len(stale), stale,
             "seed records still calling a CONFIRMED company number unverified",
             "Rewrite that record's companyNumberCandidate.matchedOn to say how the number "
             "was confirmed, and set confidence to 'confirmed'. The wording reads as "
             "'probably wrong' to anyone who opens the file.")

    for d in disagree:
        FAIL("company-report", "a seed companyNumberCandidate names a different company number "
                               "from the one the Company Report publishes as confirmed (%s). Two "
                               "sourced numbers disagreeing is a fact to check by hand, never a "
                               "tie for code to break." % d)



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
    # `compare_internal_dupes` REACHED 0 on 07/08/2026 and is now a HARD FAIL
    # with no baseline. Lou's ruling that day: these are one company each and are
    # to be actioned as one. Two differed only in capitalisation
    # (ConvaTec/Convatec, ZOLL/Zoll Medical UK); the other nine differed by a
    # legal suffix or punctuation (Cook (UK) / Cook (UK) Ltd, Penlon / Penlon
    # Limited). All eleven already resolved to a single master through `ref`, so
    # nothing about who they are changes — this settles what the TABLE prints.
    # Where the two spellings were used equally often the master record's own
    # spelling wins; otherwise the one already dominant in the file does.
    #
    # docs/ONE-LIST-AUDIT.md step 5 had advised leaving these, on the grounds
    # that a `co` may be the procurement record's own wording. That was a
    # reasonable default and it has been overridden by the owner, on the specific
    # eleven, with the reasoning recorded here.
    # `supplier_spec_unresolved` REACHED 0 on 07/08/2026 and is now a HARD FAIL
    # with no baseline. It began the day at 5. The last two were "Matched to a
    # tracked product" — a tag fetch_issues.py retired on 05/08/2026 that stayed
    # on two carried-forward index records — and System C's "Social care / local
    # government software", now mapped to `digital`. A supplier tagged with a
    # string nothing can resolve is unreachable from every speciality filter, so
    # a new one must fail rather than accumulate.
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

    _check_website_proofs(companies)
    _check_candidate_wording(companies)

    probable = []
    probable_with_cat = []
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
                probable_with_cat.append(name)

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

    # THE PROBABLE-MATCH BAND GUARD.
    # A probable match is a guess about identity, and its accounts category must
    # not reach the field-position band. This used to warn once per company: 258
    # identical lines on a 262-warning run, which is how a gate stops being read.
    # The count is not the question — the guard in the source is. So ask that
    # once, of the code, and say nothing while the answer is yes.
    #
    # Every conditional that admits a record to the band on accountsCategory must
    # also test matchConfidence, directly or through isProbable(). If one does not,
    # a name-search guess is sizing a named company against its competitors, so it
    # fails by line rather than warning by company.
    if probable_with_cat and has_js:
        for m in re.finditer(r"accountsCategory", clean):
            line = _line_at(clean, m.start()).strip()
            if not re.search(r"\bif\s*\(", line):
                continue                    # rendering a value, not admitting a record
            if re.search(r"isProbable|matchConfidence", line):
                continue                    # guarded
            FAIL("company-report", "app/company-report.js admits a record to the field-position "
                                   "band on accountsCategory without testing matchConfidence: %r. "
                                   "%d of the records carrying an accounts category are PROBABLE "
                                   "name-search matches, e.g. %s. Medtech is full of similarly "
                                   "named entities, so an unguarded read puts another company's "
                                   "filing against this one and sizes it against its competitors "
                                   "on that basis."
                                   % (line[:140], len(probable_with_cat),
                                      ", ".join(repr(p) for p in probable_with_cat[:3])))

    if probable and has_js and not re.search(r"matchConfidence|probable", clean):
        FAIL("company-report", "%d record(s) are probable name-search matches, and "
                               "app/company-report.js never reads matchConfidence or mentions "
                               "'probable'. Code that never looks at the field cannot be excluding "
                               "those records from the size bands, so a guess about identity is "
                               "feeding a derived claim. e.g. %s"
                               % (len(probable), ", ".join(repr(p) for p in probable[:3])))


# --------------------------------------------------------------------------
# 8b. COMPANY AWARDS — a statutory notice attached to a NAMED company
# --------------------------------------------------------------------------
# Added 14/08/2026 with scripts/refresh_awards.py, which is the first thing in
# this repo to say "this company won this contract". That sentence is the
# 24/07/2026 failure mode with different nouns in it: the notice names a legal
# entity ("HILL-ROM LIMITED"), the seed holds a trading name ("Hill-Rom"), and
# a matching layer stands between them. A wrong match publishes a false, dated,
# sourced-looking claim about a real business under the Hub's name.
#
# So this gate does not take the writer's word for any match. It re-derives
# every published one from scripts/company_match.py — the SAME module the
# writer used — and fails on any disagreement. That is the technique
# check_tags() already uses for the contact index: the two can then only
# diverge because of a bug, and this is what notices.
#
# WHAT THIS CANNOT ENFORCE, SAID PLAINLY:
#   * Whether the alias in the seed is CORRECT. If somebody records "Acme
#     Surgical" as an alias of the wrong Acme, both the writer and this gate
#     resolve it the same way and agree. The defence against that is the alias
#     review queue and a human, not this file.
#   * Whether the CPV filter caught every medtech award. Coverage is measured
#     and declared in the file; it is not provable from here.
AWARD_SECTIONS = {
    # section key -> the feed that is allowed to produce it. Find a Tender is
    # above-threshold, Contracts Finder below. The split is a fact about which
    # statutory service published the notice, not a judgement.
    "tender-awards": "Find a Tender",
    "contract-awards": "Contracts Finder",
}

# Absolute-absence wording. The report may say an award is NOT CAPTURED — a
# statement about this index. It may never say the company HAS no awards, which
# is a statement about the company that neither feed supports: both cover only
# what was published in the windows walked, and only where the buyer coded it
# to CPV 33.
AWARD_ABSOLUTE = re.compile(
    r"no (?:tender |contract )?awards\b|has not won|never won|holds no (?:tender |contract )?awards",
    re.I)


def check_company_awards(doc, seed, report_js):
    """data/company-awards.json, and the source that renders it."""
    if doc is None and not (report_js or "").strip():
        return                              # feature not built yet — nothing to gate

    if doc is not None:
        try:
            sys.path.insert(0, "scripts")
            import company_match
        except Exception as exc:
            FAIL("company-awards", "cannot import scripts/company_match.py (%s), so no "
                                   "published match can be re-derived and nothing here is "
                                   "checked. Do not push." % exc)
            return

        seed_names = {s.get("name") for s in ((seed or {}).get("suppliers") or [])
                      if s.get("name")}
        index = company_match.build_index(seed or {"suppliers": []})

        # ---- the rule the file publishes must be the rule that ran ---------
        # A reader judges a match by the rule printed beside it. If the printed
        # rule and the code drift apart, every match on the page is being
        # judged against a rule that did not produce it.
        if doc.get("matchRule") != company_match.RULE:
            FAIL("company-awards", "the matchRule printed in data/company-awards.json is not the "
                                   "rule scripts/company_match.py actually applies. A reader "
                                   "judges every match by that printed rule. Re-run "
                                   "scripts/refresh_awards.py rather than editing the string.")
        for field in ("sectionRule", "filterRule", "source"):
            if not str(doc.get(field) or "").strip():
                FAIL("company-awards", "data/company-awards.json carries no %s. Every derived "
                                       "or filtered claim states the rule it was made under "
                                       "(root rule 14)." % field)

        # ---- dates ---------------------------------------------------------
        gen = as_date(doc.get("generated"))
        if gen and gen > today():
            FAIL("company-awards", "data/company-awards.json says it was generated on %s, which "
                                   "has not happened yet." % doc.get("generated"))

        companies = doc.get("companies") or {}
        rows_seen = 0
        for company, rows in sorted(companies.items()):
            # ---- INVARIANT: every company named resolves to a record --------
            # Same invariant as the Company Report's derived panels. A name the
            # Hub cannot open a page for is a claim about a company this repo
            # does not hold.
            if seed_names and company not in seed_names:
                FAIL("company-awards", "data/company-awards.json attaches award(s) to %r, which "
                                       "does not resolve to any supplier record in "
                                       "data/supplier-seed.json. Every company named on the Hub "
                                       "must open to a record; a name that does not is a bug, "
                                       "not a near-miss." % company)
            for row in (rows or []):
                rows_seen += 1
                supplier = row.get("noticeSupplierName") or ""

                # ---- INVARIANT: re-derive the match, independently ----------
                got, state, _ = company_match.resolve(supplier, index)
                if state != "confirmed" or got != company:
                    FAIL("company-awards", "the award notice naming %r is published against %r, "
                                           "but re-resolving that name against the seed gives "
                                           "%s (%s). The published file and the matching rule "
                                           "disagree, so one of them is wrong and a named "
                                           "company is carrying somebody else's contract. "
                                           "Re-run: python3 scripts/refresh_awards.py --rematch"
                                           % (supplier, company,
                                              repr(got) if got else "no company", state))

                # ---- INVARIANT: a fact whose link cannot be produced is not
                # published (the page standard, §4).
                url = str(row.get("url") or "")
                if not url.startswith("http"):
                    FAIL("company-awards", "an award published against %r carries no notice URL "
                                           "(%r). A contract award is a statutory notice; "
                                           "without the link the reader cannot check it and it "
                                           "does not publish." % (company, row.get("title")))
                if not as_date(row.get("date")):
                    FAIL("company-awards", "an award published against %r carries no usable date "
                                           "(%r). Every figure and event carries its date."
                                           % (company, row.get("date")))
                elif as_date(row.get("date")) > today():
                    FAIL("company-awards", "an award published against %r is dated %s, which has "
                                           "not happened yet."
                                           % (company, row.get("date")))

                # ---- INVARIANT: 0 is a parse bug, never a fact --------------
                amount = row.get("valueAmount")
                if amount is not None:
                    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                        FAIL("company-awards", "an award published against %r carries a value "
                                               "that is not a number (%r). A value is read from "
                                               "the notice or it is null — never coerced."
                                               % (company, amount))
                    elif amount == 0:
                        FAIL("company-awards", "an award published against %r carries a value of "
                                               "0. A notice that states no value gives null, "
                                               "which the page renders as 'value not stated'. "
                                               "A 0 here is a parse bug, never a free contract."
                                               % company)

                section = row.get("section")
                if section not in AWARD_SECTIONS:
                    FAIL("company-awards", "an award published against %r is filed under section "
                                           "%r, which is not one of %s."
                                           % (company, section, sorted(AWARD_SECTIONS)))
                elif row.get("source") and row["source"] != AWARD_SECTIONS[section]:
                    FAIL("company-awards", "an award from %r is filed as %r, but that section is "
                                           "the other feed's. Above-threshold notices are tender "
                                           "awards and below-threshold ones are contract awards; "
                                           "the split is the publishing service, not a judgement."
                                           % (row["source"], section))

        # ---- quarantine ----------------------------------------------------
        # Nothing in the quarantine may be publishable. If it is, the file is
        # stale against a seed that has since gained the alias — which is a
        # coverage miss, not a false claim, so it WARNS.
        stale = []
        for row in (doc.get("unmatched") or []) + (doc.get("ambiguous") or []):
            got, state, _ = company_match.resolve(row.get("noticeSupplierName") or "", index)
            if state == "confirmed":
                stale.append((row.get("noticeSupplierName"), got))
        if stale:
            WARN("company-awards", "%d quarantined award(s) now resolve to a Hub company (e.g. "
                                   "%s), so the seed has gained an alias since this file was "
                                   "written and those awards are missing from the page. Run: "
                                   "python3 scripts/refresh_awards.py --rematch"
                                   % (len(stale), ", ".join("%r -> %r" % s for s in stale[:3])))

        # ---- counts must equal the rows (prose-vs-data drift) --------------
        counts = doc.get("counts") or {}
        for label, stated, actual in (
                ("companies", counts.get("companies"), len(companies)),
                ("awardRows", counts.get("awardRows"), rows_seen),
                ("unmatched", counts.get("unmatched"), len(doc.get("unmatched") or [])),
                ("ambiguous", counts.get("ambiguous"), len(doc.get("ambiguous") or []))):
            if stated is not None and stated != actual:
                FAIL("company-awards", "data/company-awards.json states %s = %s but holds %d. "
                                       "The same drift class as a count typed into prose: the "
                                       "header is read as the summary of the rows."
                                       % (label, stated, actual))

        # ---- an incomplete walk must SAY it is incomplete -------------------
        cov = doc.get("coverage") or {}
        if cov.get("complete") is False and "INCOMPLETE" not in str(cov.get("note") or "").upper():
            FAIL("company-awards", "the award walk did not cover its window, and coverage.note "
                                   "does not say so. A short list that reads as complete is how "
                                   "a member concludes a company holds no awards.")

    # ---- source invariant ---------------------------------------------------
    clean, spans = _js_scan(report_js or "")
    if clean.strip() and "company-awards.json" in clean:
        offending = []
        for a, b in spans:
            for m in AWARD_ABSOLUTE.finditer(clean[a:b]):
                line = _line_at(clean, a + m.start()).strip()
                if line not in offending:
                    offending.append(line)
        for line in offending[:5]:
            FAIL("company-awards", "app/company-report.js renders an absolute absence of awards: "
                                   "%r. Both feeds cover only the windows walked, and only where "
                                   "the buyer coded the notice to CPV 33 — so the page may say "
                                   "the awards are NOT CAPTURED, which is about this index, and "
                                   "never that the company has none, which is about the company."
                                   % line[:140])


def check_pending_awards(doc, seed, fw_doc, report_js):
    """data/pending-awards.json — NHS Supply Chain framework awards public on
    Find a Tender but not yet on NHSSC's own contract launch brief. Every
    published match AND every published supersede decision is re-derived from
    scripts/refresh_pending_awards.py, the same module the writer used, so
    neither can drift from the file without the gate saying so."""
    if doc is None and not (report_js or "").strip():
        return                              # feature not built yet — nothing to gate

    if doc is not None:
        try:
            sys.path.insert(0, "scripts")
            import company_match
            import refresh_pending_awards as rpa
        except Exception as exc:
            FAIL("pending-awards", "cannot import scripts/refresh_pending_awards.py or "
                                   "scripts/company_match.py (%s), so no published match or "
                                   "supersede decision can be re-derived. Do not push." % exc)
            return

        seed_names = {s.get("name") for s in ((seed or {}).get("suppliers") or [])
                      if s.get("name")}
        index = company_match.build_index(seed or {"suppliers": []})
        confirmed_by_title = rpa.confirmed_frameworks_by_title(fw_doc or {"frameworks": []})

        if doc.get("matchRule") != company_match.RULE:
            FAIL("pending-awards", "the matchRule printed in data/pending-awards.json is not "
                                   "the rule scripts/company_match.py actually applies. Re-run "
                                   "scripts/refresh_pending_awards.py rather than editing the "
                                   "string.")

        awards = doc.get("awards") or []
        by_company_stated = doc.get("companies") or {}
        derived_by_company = {}

        for award in awards:
            title = award.get("title") or ""
            ocid = award.get("ocid") or ""

            # ---- INVARIANT: nothing published here may already be confirmed.
            # This is the whole point of the file — a stale entry here is a
            # member being shown "not yet live" for a framework that already
            # is, which is a worse error than the gap this file exists to fix.
            if rpa.superseded_by(title, award.get("contractStart"), confirmed_by_title):
                FAIL("pending-awards", "%r (ocid %s) is published as a PENDING award, but "
                                       "re-deriving the supersede check against the current "
                                       "data/frameworks.json shows NHS Supply Chain has now "
                                       "published its own brief for this same framework "
                                       "generation. Re-run: "
                                       "python3 scripts/refresh_pending_awards.py"
                                       % (title, ocid))

            url = str(award.get("url") or "")
            if not url.startswith("http"):
                FAIL("pending-awards", "the pending award %r carries no notice URL. A pending "
                                       "award is a statutory notice; without the link the "
                                       "reader cannot check it and it does not publish." % title)

            for field in ("reference", "buyer", "contractStart"):
                if not str(award.get(field) or "").strip():
                    FAIL("pending-awards", "the pending award %r carries no %s." % (title, field))

            # ---- INVARIANT: re-derive every published company match ---------
            matched_as = award.get("matchedAs") or {}
            for company in award.get("companies") or []:
                if seed_names and company not in seed_names:
                    FAIL("pending-awards", "the pending award %r names %r, which does not "
                                           "resolve to any supplier record in "
                                           "data/supplier-seed.json." % (title, company))
                notice_name = matched_as.get(company)
                if not notice_name:
                    FAIL("pending-awards", "the pending award %r attaches %r with no matchedAs "
                                           "entry — the page cannot show which name on the "
                                           "notice this company was identified by." % (title, company))
                    continue
                got, state, _ = company_match.resolve(notice_name, index)
                if state != "confirmed" or got != company:
                    FAIL("pending-awards", "the pending award %r naming %r is published against "
                                           "%r, but re-resolving that name against the seed "
                                           "gives %s (%s). Re-run: "
                                           "python3 scripts/refresh_pending_awards.py"
                                           % (title, notice_name, company,
                                              repr(got) if got else "no company", state))
                derived_by_company.setdefault(company, []).append(title)

        # ---- the published by-company index must match what was derived ----
        stated_pairs = set()
        for company, rows in by_company_stated.items():
            for row in (rows or []):
                stated_pairs.add((company, row.get("title")))
        derived_pairs = set()
        for company, titles in derived_by_company.items():
            for t in titles:
                derived_pairs.add((company, t))
        if stated_pairs != derived_pairs:
            missing = derived_pairs - stated_pairs
            extra = stated_pairs - derived_pairs
            FAIL("pending-awards", "data/pending-awards.json's `companies` index does not match "
                                   "its own `awards` list — missing %s, extra %s. Re-run: "
                                   "python3 scripts/refresh_pending_awards.py"
                                   % (sorted(missing)[:3], sorted(extra)[:3]))

        counts = doc.get("counts") or {}
        if counts.get("pending") is not None and counts["pending"] != len(awards):
            FAIL("pending-awards", "data/pending-awards.json states counts.pending = %s but "
                                   "holds %d." % (counts.get("pending"), len(awards)))

    # ---- source invariant: the panel must exist if the data does -----------
    clean, spans = _js_scan(report_js or "")
    if doc and (doc.get("awards")) and clean.strip() and "pending-awards.json" not in clean:
        FAIL("pending-awards", "data/pending-awards.json holds pending award(s) but "
                               "app/company-report.js does not reference the file — the panel "
                               "cannot be rendering.")


# --------------------------------------------------------------------------
# 11. SUPPLIER PRODUCT DETAIL — per-product pages captured from each
#     supplier's own website (scripts/crawl_supplier_product_detail.py)
# --------------------------------------------------------------------------
def check_supplier_product_detail(doc, rangedoc):
    """data/supplier-product-detail.json — full spec/feature/image detail
    captured from each product's OWN page on its supplier's OWN website, plus
    the changedSince flag The Differential renders as sales intelligence."""
    if doc is None:
        return                              # feature not built yet — nothing to gate

    products = doc.get("products") or {}
    range_suppliers = (rangedoc or {}).get("suppliers") or {}

    for key, row in sorted(products.items()):
        supplier = row.get("supplier")
        product = row.get("product")
        label = "%s / %s" % (supplier or "?", product or "?")

        if not supplier or not product:
            FAIL("supplier-product-detail", "the entry keyed %r carries no supplier and/or "
                                            "product name." % key)
            continue

        url = str(row.get("sourceUrl") or "")
        if not url.startswith("http"):
            FAIL("supplier-product-detail", "%s carries no usable sourceUrl (%r). A product-detail "
                                            "claim without a link to where it came from does not "
                                            "publish." % (label, row.get("sourceUrl")))

        d = as_date(row.get("capturedDate"))
        if not d:
            FAIL("supplier-product-detail", "%s carries no usable capturedDate (%r). Every capture "
                                            "carries the date it was read." % (label, row.get("capturedDate")))
        elif d > today():
            FAIL("supplier-product-detail", "%s is dated %s, which has not happened yet."
                                            % (label, row.get("capturedDate")))
        elif (today() - d).days > 400:
            WARN("supplier-product-detail", "%s was last captured on %s, over a year ago — due a "
                                            "re-crawl." % (label, row.get("capturedDate")))

        parsed = row.get("parsed")
        if parsed not in ("structured", "heuristic"):
            FAIL("supplier-product-detail", "%s carries parsed=%r, not one of 'structured' or "
                                            "'heuristic'. comparison.js and anyone reviewing this "
                                            "file needs to know which confidence tier a capture "
                                            "sits in — that distinction is the whole point of the "
                                            "field." % (label, parsed))

        # ---- INVARIANT: every named supplier resolves to a known range record
        if range_suppliers and supplier not in range_suppliers:
            FAIL("supplier-product-detail", "%s does not resolve to any supplier in "
                                            "data/supplier-products.json — a product-detail entry "
                                            "should only exist for a supplier this repo already "
                                            "holds a range record for." % label)

        # ---- changedSince: a change flag must name a date and name what changed
        cs = row.get("changedSince")
        if cs is not None:
            if not as_date(cs.get("date")):
                FAIL("supplier-product-detail", "%s carries a changedSince block with no usable "
                                                "date (%r)." % (label, cs.get("date")))
            elif as_date(cs.get("date")) > today():
                FAIL("supplier-product-detail", "%s carries a changedSince date of %s, which has "
                                                "not happened yet." % (label, cs.get("date")))
            if not (cs.get("changed") or []):
                FAIL("supplier-product-detail", "%s carries a changedSince block with an empty "
                                                "'changed' list. A change flag naming nothing that "
                                                "changed is noise on a paying page, not a finding."
                                                % label)
            bad_fields = [f for f in (cs.get("changed") or [])
                         if f not in ("description", "features", "image")]
            if bad_fields:
                FAIL("supplier-product-detail", "%s carries a changedSince.changed list naming %s, "
                                                "which %s not a field this capture tracks."
                                                % (label, bad_fields,
                                                   "is" if len(bad_fields) == 1 else "are"))


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


def check_no_expired_frameworks(fwdoc):
    """data/frameworks.json's `frameworks` list must hold only live routes.

    NHS Supply Chain leaves a contract launch brief published after its
    framework ends, so a straight capture keeps returning them. On 07/08/2026
    three sat in the live list — one 515 days past its end date — and every
    consumer treats that list as current: 24 supplier rows across the seed and
    the index showed them under "Frameworks on" with the date range printed and
    no other signal. Medtronic, Boston Scientific and Abbott all read as
    currently on a Transcatheter Heart Valve framework that stopped in
    September 2025.

    The Compare tab has refused an expired ROUTE since 05/08/2026. This is the
    same rule one level down, on the file those routes are drawn from.

    An entry with no readable end date passes. Refusing on an unparseable date
    would drop live frameworks to satisfy a check, which is backwards.
    """
    if not isinstance(fwdoc, dict):
        return
    bad = []
    for f in fwdoc.get("frameworks") or []:
        if not isinstance(f, dict):
            continue
        end = None
        for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d"):
            try:
                end = datetime.datetime.strptime(str(f.get("ends") or "").strip(), fmt).date()
                break
            except ValueError:
                pass
        if end and end < today():
            bad.append("%s (ended %s, %d days ago)"
                       % (f.get("name"), f.get("ends"), (today() - end).days))
    if bad:
        FAIL("frameworks", "%d framework(s) in data/frameworks.json have already ended but are "
                           "still in the live `frameworks` list, which every consumer reads as "
                           "current routes to market. Move them to `expired` — "
                           "scripts/refresh_frameworks.py does this on each run. %s"
             % (len(bad), "; ".join(bad[:6])))


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
    # Find the banner, then walk BACK to the `if (` that governs it, counting
    # parentheses. The first version used a regex with `[^)]*?` for the guard and
    # silently failed the moment the guard contained a nested paren — which is
    # exactly what the fix introduced: `!((it.use||'').trim())`. It degraded to
    # the "cannot read it" WARN rather than passing, which is why it was caught,
    # but a check that cannot read the thing it checks is not a check.
    at = src.find("auto-detected, verify at source")
    if at < 0:
        return                                  # banner gone entirely; nothing to guard
    head = src[:at]
    open_at = head.rfind("if")
    guard = None
    while open_at >= 0:
        j = src.find("(", open_at)
        if j < 0 or j > at:
            break
        depth, k = 0, j
        while k < at:
            if src[k] == "(":
                depth += 1
            elif src[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth == 0 and k < at and src[k + 1:at].count("{") >= 1:
            guard = src[j + 1:k]
            break
        open_at = head.rfind("if", 0, open_at)
    if guard is None:
        WARN("curated", "app/comptab.js still prints the auto-detected banner but the `if` "
                        "governing it could not be read, so it was NOT checked. Look at it by "
                        "hand — this check is not protecting anything until it parses.")
        return
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
# 12. COMPANY LOGOS — the brand-mark layer
# --------------------------------------------------------------------------
# Added 18/08/2026, with the feature.
#
# WHY THIS CHECK EXISTS, IN ONE SENTENCE: the report's previous logo route was a
# LIVE call to logo.clearbit.com, that host stopped resolving, every report
# silently fell through to the monogram, and nobody found out for weeks. A
# dependency nobody can see break is the fault; moving the marks into this repo
# only helps if something reads them before they publish.
#
# So this refuses to publish a logo layer that would be broken on arrival:
#
#   PATHS      every recorded file must exist, be non-empty, live under
#              assets/logos/, and be a .png or .svg. A row pointing at a file
#              that is not in the commit renders as a broken image on a paid
#              page, and the row's own presence is what tells the renderer to
#              try — so a missing file is worse than no row.
#   BYTES      every file's sha256 must match the one recorded with it. A mark
#              swapped or truncated after it was checked has not been checked.
#   ORPHANS    every file under assets/logos/ must be named by a row. Bytes that
#              ship to members and are never drawn are dead weight in a repo the
#              page fetches from.
#   PROVENANCE every row carries the URL it was fetched from and the date. A
#              mark with no source cannot be defended as the company's own, and
#              a mark with no date cannot be aged.
#   NO SERVICE no source may be a favicon SERVICE. Those serve a 16px tab glyph,
#              and their own grey placeholder arrow where they hold nothing —
#              which is exactly how 13 of the 15 legacy `image` values came to
#              point at a mark that is not the company's.
#   COUNTS     every count in the header must equal the rows it summarises. A
#              header from one generation with rows from another has caused a
#              real incident in this repo; it is not a hypothetical.
#   COLOUR     every published brand colour must be valid hex, and each derived
#              shade must clear, ON RECOMPUTATION HERE, the floor for the ground
#              it is painted on. The recorded ratio is re-derived rather than
#              trusted: a ratio typed next to a colour it does not describe is a
#              claim the file makes about itself.
#   RENDERER   the source may not reach for a third-party logo host, and must
#              still carry its own contrast guard — because the OTHER colour
#              source, the 95 `brand` records in supplier-seed.json, predates
#              any contrast rule and is checked nowhere else.
#
# A missing file is a NO-OP. The feature is optional and an absent layer means
# every company draws the monogram, which is a finished design.

LOGO_DIR = os.path.join("assets", "logos")
LOGO_NAVY = (0x0b, 0x1c, 0x33)      # .mcr-mast ground
LOGO_IVORY = (0xfd, 0xfc, 0xf9)     # .mcr-report card ground
LOGO_MIN_NAVY = 3.0                 # WCAG 2.1 1.4.11, non-text
LOGO_MIN_IVORY = 3.0                # WCAG 2.1 1.4.11, non-text
LOGO_MIN_WHITE = 4.5                # WCAG 2.1 1.4.3, normal text
LOGO_SIZE_WARN = 8 * 1024 * 1024    # assets/logos/ total; see the note at the check
FAVICON_SERVICE_RE = re.compile(
    r"(?://)(?:icons?\.duckduckgo\.com|www\.google\.com/s2/favicons|"
    r"favicons?\.[^/]+|t\d\.gstatic\.com/faviconV2)", re.I)
HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")


def _rel_lum(rgb):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = _rel_lum(a), _rel_lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _hex_rgb(h):
    h = str(h or "").lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def check_company_logos(doc, report_js, root="."):
    if doc is None:
        return
    rows = doc.get("logos")
    refusals = doc.get("refusals")
    if not isinstance(rows, list) or not isinstance(refusals, list):
        FAIL("logos", "data/company-logos.json has no `logos` and `refusals` lists. The "
                      "refusals are half the file: without them an empty layer cannot be "
                      "told apart from a sweep that never ran.")
        return

    if not str(doc.get("rule") or "").strip():
        FAIL("logos", "data/company-logos.json states no rule. Root rule 14 — a reader has "
                      "to be able to judge how these marks were chosen without re-running "
                      "the script.")

    seen_name, seen_file, referenced = {}, {}, set()
    for i, r in enumerate(rows):
        who = r.get("name") or "row %d" % i

        for field in ("name", "file", "source", "fetched", "sha256"):
            if not str(r.get(field) or "").strip():
                FAIL("logos", "%s has no %s. Every mark carries where it came from and when "
                              "it was read, or it cannot be defended as this company's own."
                     % (who, field))
        if not r.get("file") or not r.get("name"):
            continue

        if r["name"] in seen_name:
            FAIL("logos", "%s appears twice. Two rows for one company means the renderer "
                          "draws whichever it saw last, which is not a decision anybody made."
                 % who)
        seen_name[r["name"]] = 1

        # PROVENANCE
        src = str(r.get("source") or "")
        if src and not src.lower().startswith(("http://", "https://")):
            FAIL("logos", "%s records its source as %r, which is not a URL." % (who, src[:80]))
        if FAVICON_SERVICE_RE.search(src):
            FAIL("logos", "%s was taken from a favicon SERVICE (%s). Those serve a 16px tab "
                          "glyph, and their own grey placeholder where they hold nothing — "
                          "which is how 13 legacy `image` values came to point at a mark that "
                          "is not the company's." % (who, src[:80]))
        if not as_date(r.get("fetched")):
            FAIL("logos", "%s has no readable fetch date (%r). A mark with no date cannot be "
                          "aged." % (who, r.get("fetched")))

        # PATHS
        path = str(r["file"]).replace("\\", "/")
        if not path.startswith("assets/logos/") or ".." in path:
            FAIL("logos", "%s points outside assets/logos/ (%r)." % (who, path))
            continue
        if not path.lower().endswith((".png", ".svg")):
            FAIL("logos", "%s is %r — only .png and .svg are stored." % (who, path))
            continue
        if path in seen_file:
            FAIL("logos", "%s and %s both point at %s. One file cannot be two companies' "
                          "marks." % (who, seen_file[path], path))
        seen_file[path] = who
        referenced.add(os.path.basename(path))

        full = os.path.join(root, path)
        if not os.path.exists(full):
            FAIL("logos", "%s records %s, which is not in the repo. The row is what tells the "
                          "renderer to try, so a missing file is a broken image on a paid "
                          "page — not a fallback to the monogram." % (who, path))
            continue
        blob = open(full, "rb").read()
        if not blob:
            FAIL("logos", "%s: %s is empty." % (who, path))
            continue
        got = hashlib.sha256(blob).hexdigest()
        if r.get("sha256") and got != r["sha256"]:
            FAIL("logos", "%s: %s does not match the sha256 recorded with it. A mark changed "
                          "after it was checked has not been checked." % (who, path))
        if r.get("bytes") and int(r["bytes"]) != len(blob):
            FAIL("logos", "%s: %s is %d bytes, but the file records %s."
                 % (who, path, len(blob), r["bytes"]))

        # COLOUR
        b = r.get("brand")
        if b is None:
            if not str(r.get("brandRefused") or "").strip():
                FAIL("logos", "%s carries no brand colour and does not say why. A refusal "
                              "with no reason is indistinguishable from a step that was "
                              "skipped." % who)
            continue
        for k in ("c1", "c2"):
            if not HEX6.match(str(b.get(k) or "")):
                FAIL("logos", "%s brand.%s is %r, not a six-digit hex colour."
                     % (who, k, b.get(k)))
        if not str(b.get("source") or "").strip():
            FAIL("logos", "%s publishes a brand colour with no note saying what it was "
                          "sampled from and when." % who)
        navy = b.get("accentOnNavy") or b.get("c1")
        ivory = b.get("accentOnIvory") or b.get("c2")
        if not (HEX6.match(str(navy or "")) and HEX6.match(str(ivory or ""))):
            continue
        rn = _contrast(_hex_rgb(navy), LOGO_NAVY)
        ri = _contrast(_hex_rgb(ivory), LOGO_IVORY)
        rw = _contrast(_hex_rgb(ivory), (255, 255, 255))
        if rn < LOGO_MIN_NAVY:
            FAIL("logos", "%s publishes %s on the navy masthead at %.2f:1, below the %.1f:1 "
                          "floor. An accent nobody can see is worse than the house gold."
                 % (who, navy, rn, LOGO_MIN_NAVY))
        if ri < LOGO_MIN_IVORY:
            FAIL("logos", "%s publishes %s on the ivory card ground at %.2f:1, below the "
                          "%.1f:1 floor." % (who, ivory, ri, LOGO_MIN_IVORY))
        if rw < LOGO_MIN_WHITE:
            FAIL("logos", "%s publishes %s as the shade that carries white text, at %.2f:1, "
                          "below the %.1f:1 floor." % (who, ivory, rw, LOGO_MIN_WHITE))
        # The recorded ratios are re-derived, not trusted.
        for key, want in (("contrastOnNavy", rn), ("contrastOnIvory", ri),
                          ("contrastWhiteOnC2", rw)):
            if b.get(key) is None:
                continue
            try:
                if abs(float(b[key]) - want) > 0.05:
                    FAIL("logos", "%s records %s as %s, but it recomputes to %.2f. A ratio "
                                  "printed next to a colour it does not describe is a claim "
                                  "the file makes about itself."
                         % (who, key, b[key], want))
            except (TypeError, ValueError):
                FAIL("logos", "%s records %s as %r, which is not a number."
                     % (who, key, b[key]))

    for r in refusals:
        if not str(r.get("name") or "").strip() or not str(r.get("reason") or "").strip():
            FAIL("logos", "a refusal row has no name or no reason. 'Publishing nothing' is "
                          "only the correct output when the file says what was not published "
                          "and why.")
            break

    # ORPHANS
    d = os.path.join(root, LOGO_DIR)
    if os.path.isdir(d):
        stored = {n for n in os.listdir(d) if not n.startswith(".")}
        orphans = sorted(stored - referenced)
        if orphans:
            FAIL("logos", "%d file(s) in assets/logos/ are named by no row (%s). Bytes that "
                          "ship to members and are never drawn are dead weight in a repo the "
                          "page fetches from."
                 % (len(orphans), ", ".join(orphans[:5])))
        total = sum(os.path.getsize(os.path.join(d, n)) for n in stored)
        if total > LOGO_SIZE_WARN:
            WARN("logos", "assets/logos/ is %.2f MB. The Hub page fetches from this repo, so "
                          "this is a decision for Lou, not a threshold to raise quietly."
                 % (total / 1048576.0))

    # COUNTS — the header must equal the rows it summarises.
    c = doc.get("counts") or {}
    for key, want, what in (("logos", len(rows), "logo rows"),
                            ("refusals", len(refusals), "refusal rows"),
                            ("logosWithBrandColour",
                             sum(1 for r in rows if r.get("brand")),
                             "rows carrying a brand colour")):
        if c.get(key) is not None and int(c[key]) != want:
            FAIL("logos", "counts.%s says %s, but there are %d %s. A header from one "
                          "generation with rows from another has already put wrong numbers "
                          "in front of members here." % (key, c[key], want, what))

    # RENDERER
    if report_js:
        for host in ("logo.clearbit.com", "icons.duckduckgo.com", "/s2/favicons?",
                     "faviconV2"):
            if host in report_js:
                FAIL("logos", "app/company-report.js reaches for %s. A logo fetched live "
                              "from a third party is a dependency nobody is watching on a "
                              "page members pay for — that is the fault this layer replaced, "
                              "not one to reintroduce." % host)
        if "--mcr-accent-ink" not in report_js:
            FAIL("logos", "app/company-report.js no longer publishes --mcr-accent-ink. One "
                          "accent cannot serve both the navy masthead and the ivory card "
                          "ground; collapsing them back to one makes half of every brand "
                          "colour invisible.")
        if "function safe(" not in report_js or "0.03928" not in report_js:
            FAIL("logos", "app/company-report.js has lost its contrast guard. The 95 `brand` "
                          "records in supplier-seed.json predate any contrast rule and are "
                          "checked nowhere else — without the guard an unreadable accent "
                          "reaches the page.")

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


PRESS_URL_TYPES = {"publisher", "google-news-redirect"}

# Words that appear in a news URL's PATH because of how the site is built, not
# because of what the story says. Stripped before deciding whether a link carries
# a headline slug worth comparing (see the corroboration invariant in
# check_company_press). Keep this list to structural words only: every entry here
# is a word the check can no longer see, so a real headline word added by mistake
# would quietly weaken it.
PRESS_URL_BOILERPLATE = {
    "news", "article", "articles", "articleview", "html", "htm", "php", "aspx",
    "story", "stories", "view", "index", "idxno", "content", "print", "node",
    "post", "posts", "page", "pages", "default", "item", "items", "detail",
    "details", "feature", "featured", "topics", "topic", "section", "sections",
    "category", "categories", "tag", "tags", "archive", "latest", "breaking",
    "press", "releases", "release", "media", "read", "show", "full",
}


def check_company_press(doc, seed):
    """data/company-press.json — the supplier press feature.

    Three separate things can go wrong here and each has cost somebody real
    money or credibility already, in this repo or one like it.

    1. THE WRONG COMPANY'S STORY. Matching a news item on a company name alone
       eventually attributes somebody else's news to a Hub supplier. The rule
       that stops it is scripts/press_match.py, and this gate RE-DERIVES every
       published item against that module rather than trusting the file. If the
       file was written under a looser rule — an older script, a hand edit, a
       merge — the re-derivation disagrees and nothing publishes. Same
       arrangement as check_company_awards, same reason (root rule 14).

    2. A HEADER FROM ONE GENERATION AND ROWS FROM ANOTHER. That is exactly what
       -X theirs did to data/company-awards.json on 14/08/2026
       (NOTE-company-intelligence-rebase-merge-defect-2026-08-14.md). The counts
       are recomputed here from the rows they claim to summarise.

    3. A LINK THAT WAS NEVER RESOLVED, PRESENTED AS THOUGH IT HAD BEEN. Google
       News gives a redirect, not the publisher's article. A redirect recorded as
       urlType "publisher" is a claim the reader cannot check, so the two types
       are checked against the host they actually point at.

    An empty supplier block is NOT a failure. A supplier with lastChecked and no
    items has been checked and nothing met the bar — the honest empty state, and
    the whole reason lastChecked exists.
    """
    if doc is None:
        return                              # feature not built yet — nothing to gate

    try:
        sys.path.insert(0, "scripts")
        import press_match
    except Exception as exc:                                    # noqa: BLE001
        FAIL("company-press", "cannot import scripts/press_match.py (%s), so no published "
                              "press item can be re-derived and nothing here is checked. "
                              "Do not push." % exc)
        return

    # ---- the rule the file publishes must be the rule that ran --------------
    if doc.get("matchRule") != press_match.RULE:
        FAIL("company-press", "the matchRule printed in data/company-press.json is not the rule "
                              "scripts/press_match.py actually applies. A reader judges every "
                              "attribution by that printed rule. Re-run "
                              "scripts/refresh_company_press.py rather than editing the string.")
    for field in ("source", "corroborationRule", "rotationRule", "linkRule", "emptyStateRule"):
        if not str(doc.get(field) or "").strip():
            FAIL("company-press", "data/company-press.json carries no %s. Every derived or "
                                  "filtered claim states the rule it was made under "
                                  "(root rule 14)." % field)

    gen = as_date(doc.get("generated"))
    if gen and gen > today():
        FAIL("company-press", "data/company-press.json says it was generated on %s, which has "
                              "not happened yet." % doc.get("generated"))

    # ---- an incomplete rotation must SAY it is incomplete --------------------
    cov = doc.get("coverage") or {}
    if cov.get("complete") is False and "INCOMPLETE" not in str(cov.get("note") or "").upper():
        FAIL("company-press", "the rotation has not reached every supplier yet, and coverage.note "
                              "does not say so. A partial sweep that reads as complete is how a "
                              "member concludes a company has had no news.")

    seed_doc = seed or {"suppliers": []}
    by_name = {s.get("name"): s for s in (seed_doc.get("suppliers") or []) if s.get("name")}
    universe = press_match.alias_universe(seed_doc)

    suppliers = doc.get("suppliers") or {}
    items_seen = sources_seen = resolved_seen = redirect_seen = with_items = 0

    for name, rec in sorted(suppliers.items()):
        # ---- INVARIANT: every company named resolves to a record ------------
        if by_name and name not in by_name:
            FAIL("company-press", "data/company-press.json carries press for %r, which does not "
                                  "resolve to any supplier record in data/supplier-seed.json. "
                                  "Every company named on the Hub must open to a record." % name)
            continue
        supplier = by_name.get(name) or {"name": name}

        checked = as_date((rec or {}).get("lastChecked"))
        if not checked:
            FAIL("company-press", "the press block for %r carries no usable lastChecked date. "
                                  "Without it an empty panel cannot say when it was checked, and "
                                  "reads as broken rather than as empty." % name)
        elif checked > today():
            FAIL("company-press", "the press block for %r says it was checked on %s, which has "
                                  "not happened yet." % (name, rec.get("lastChecked")))

        rows = (rec or {}).get("items") or []
        if rows:
            with_items += 1
        for row in rows:
            items_seen += 1
            head = str(row.get("headline") or "").strip()
            if not head:
                FAIL("company-press", "a press item published against %r carries no headline."
                                      % name)

            if not as_date(row.get("date")):
                FAIL("company-press", "a press item published against %r carries no usable ISO "
                                      "date (%r). Every event carries its date."
                                      % (name, row.get("date")))
            elif as_date(row.get("date")) > today():
                FAIL("company-press", "a press item published against %r is dated %s, which has "
                                      "not happened yet." % (name, row.get("date")))

            # ---- INVARIANT: two DISTINCT publishers, with working links -----
            srcs = row.get("sources") or []
            pubs = set()
            for s in srcs:
                sources_seen += 1
                pub = str((s or {}).get("publisher") or "").strip()
                url = str((s or {}).get("url") or "").strip()
                kind = (s or {}).get("urlType")
                if pub:
                    pubs.add(pub.lower())
                else:
                    FAIL("company-press", "a source on %r's item %r carries no publisher name. "
                                          "The publisher IS the source of the claim; Google News "
                                          "is only the index." % (name, head[:60]))
                if not url.startswith("http"):
                    FAIL("company-press", "a source on %r's item %r carries no usable URL (%r). "
                                          "A claim whose link cannot be produced does not publish."
                                          % (name, head[:60], url))
                if kind not in PRESS_URL_TYPES:
                    FAIL("company-press", "a source on %r's item %r is filed as urlType %r, which "
                                          "is not one of %s." % (name, head[:60], kind,
                                                                 sorted(PRESS_URL_TYPES)))
                elif kind == "publisher":
                    resolved_seen += 1
                    if "news.google.com" in url:
                        FAIL("company-press", "a source on %r's item %r is recorded as a "
                                              "publisher link but still points at news.google.com. "
                                              "An unresolved redirect is marked as one, never "
                                              "dressed up as the publisher's own article."
                                              % (name, head[:60]))
                else:
                    redirect_seen += 1
                    if "news.google.com" not in url:
                        FAIL("company-press", "a source on %r's item %r is recorded as a Google "
                                              "News redirect but does not point at "
                                              "news.google.com." % (name, head[:60]))

            # ---- INVARIANT: rule 5 re-derived, not just counted ------------
            # Added 27/08/2026. Until today this gate could only COUNT the
            # publishers on an item. Rule 5 does not say "two publishers" — it
            # says two DISTINCT REPUTABLE publishers, and that PR wires,
            # stock-tip sites and SEO syndication never count towards the two.
            # That half of the rule lived only in the writer, so a wire carried
            # as one of the two would have published and this gate would have
            # said nothing. The vocabulary now lives in press_match beside rules
            # 1 to 4, and is re-derived here from the publisher names the file
            # itself carries — the same arrangement, and the same reason, as the
            # re-derivation of the match rule above.
            #
            # A wire is not merely uncounted here, it is REFUSED. An item whose
            # sources include one is an item written under a looser rule than the
            # one printed beside it, and the honest response to that is to
            # publish nothing (root rule 14), not to quietly drop the offending
            # source and keep the story.
            wires = sorted({str((s or {}).get("publisher") or "").strip()
                            for s in srcs
                            if press_match.wire((s or {}).get("publisher"))})
            if wires:
                FAIL("company-press", "the item %r published against %r cites %s as a source. "
                                      "Rule 5 says PR wires, stock-tip sites and SEO syndication "
                                      "never count towards corroboration, so this item was "
                                      "written under a looser rule than the one printed beside "
                                      "it. Re-run scripts/refresh_company_press.py."
                     % (head[:60], name, ", ".join(repr(w) for w in wires)))
            counted = {str((s or {}).get("publisher") or "").strip().lower()
                       for s in srcs
                       if press_match.reputable((s or {}).get("publisher"))}
            if len(counted) < 2:
                FAIL("company-press", "the item %r published against %r is presented as "
                                      "corroborated, but only %d of its sources is a publisher "
                                      "rule 5 counts (%s). Two distinct reputable publishers are "
                                      "required, and an item short of them is not published with "
                                      "a caveat."
                     % (head[:60], name, len(counted),
                        ", ".join(sorted(str((s or {}).get("publisher") or "?") for s in srcs))))

            # ---- INVARIANT: corroboration is about the STORY, not the COMPANY --
            # Added 18/08/2026 after the live file published 14 items whose
            # "two independent publishers" were carrying a DIFFERENT story about
            # the same company. refresh_company_press.cluster() grouped on headline
            # token overlap with a floor of two shared words, and a two-token
            # company name supplied both — so "Smith+Nephew ... launch centre ...
            # surgical robotics" was corroborated by Reuters and MedTech Dive
            # reporting Smith+Nephew BUYING Integrity Orthopaedics.
            #
            # The gate cannot read the corroborating articles, so it tests the
            # thing it CAN see: the lead headline must carry at least two
            # substantial words that are NOT part of the company's own name. A
            # headline that is only the company name plus filler has no topic for a
            # second publisher to have corroborated, and the claim cannot be
            # supported whatever the sources say.
            #
            # This is deliberately a check on the PUBLISHED EVIDENCE, not a
            # re-derivation of the clustering — re-running the clusterer here would
            # only re-assert the writer's own logic and would have passed the very
            # file that was wrong. Root rule 14: an invariant that fails if the
            # logic breaks, not a restatement of it.
            #
            # The gate cannot read the corroborating articles. What it CAN read is
            # each source's own URL: a publisher-resolved link usually carries the
            # article's headline as its path slug, and that slug is written by the
            # publisher, not by us. Comparing it against the lead headline is how
            # this defect was found in the first place. Sources whose URL is
            # ID-based carry no slug signal and are not assessed — absence of
            # evidence is not evidence here.
            if head and len(srcs) >= 2:
                name_toks = set()
                for form in [name] + list((supplier or {}).get("aliases") or []):
                    name_toks |= {t for t in press_match.norm(form).split() if len(t) > 3}
                topic = {t for t in press_match.norm(head).split() if len(t) > 3} - name_toks

                if len(topic) < 2:
                    FAIL("company-press",
                         "the item %r published against %r is presented as corroborated by %d "
                         "publishers, but its headline carries fewer than two substantial words "
                         "beyond the company's own name, so there is no story for a second "
                         "publisher to have corroborated." % (head[:60], name, len(srcs)))
                else:
                    agree, assessed, disagree = set(), 0, []
                    for s in srcs:
                        if (s or {}).get("urlType") != "publisher":
                            continue        # a redirect's URL is Google's, not the publisher's
                        pub = str((s or {}).get("publisher") or "").strip()
                        # PATH ONLY — the host is the publisher's name, not the story's.
                        raw_url = str((s or {}).get("url") or "")
                        path = raw_url.split("//")[-1]
                        path = path[path.find("/"):] if "/" in path else ""
                        slug = press_match.norm(re.sub(r"[-/_.?=&]", " ", path))
                        slug_toks = ({t for t in slug.split() if len(t) > 3}
                                     - name_toks - PRESS_URL_BOILERPLATE)
                        if len(slug_toks) < 3:
                            # An ID-style or section-only URL carries no headline to
                            # compare. Not assessed, in either direction: absence of
                            # evidence is not evidence. Live example that forced this
                            # (18/08/2026): koreabiomed.com/news/articleView.html?idxno
                            # scored 5 "words" — news, articleview, html, idxno and the
                            # host — none of which say anything about the story.
                            continue
                        assessed += 1
                        if topic & slug_toks:
                            agree.add(pub.lower())
                        else:
                            disagree.append((pub, str(s.get("url"))[:90]))
                    # Only judge when there is enough signal to judge on.
                    if assessed >= 2 and len(agree) < 2 and disagree:
                        FAIL("company-press",
                             "the item %r published against %r claims corroboration from %d "
                             "publishers, but %d of the resolved source links share no word with "
                             "the headline beyond the company's own name — so they appear to "
                             "carry a DIFFERENT story about the same company (e.g. %s %s). "
                             "Corroboration must be about the story, never about the company "
                             "name. This is the 18/08/2026 defect; do not loosen this check to "
                             "make a push go through."
                             % (head[:60], name, len(srcs), len(disagree),
                                disagree[0][0], disagree[0][1]))
            if len(pubs) < 2:
                FAIL("company-press", "the item %r published against %r is carried by %d distinct "
                                      "publisher(s); two are required. One outlet repeating a "
                                      "press release is not corroboration."
                                      % (head[:60], name, len(pubs)))

            # ---- INVARIANT: re-derive the match, independently --------------
            lead_pub = (srcs[0] or {}).get("publisher") if srcs else ""
            ok, why, ev = press_match.assess(supplier, row, publisher=lead_pub,
                                             universe=universe)
            if not ok:
                FAIL("company-press", "the item %r is published against %r, but re-applying the "
                                      "printed match rule to it fails: %s. The published file and "
                                      "the rule disagree, so one of them is wrong and a named "
                                      "company may be carrying somebody else's news. Re-run: "
                                      "python3 scripts/refresh_company_press.py"
                                      % (head[:60], name, why))
            else:
                claimed = (row.get("match") or {}).get("alias")
                if claimed and claimed != ev.get("alias"):
                    FAIL("company-press", "the item %r published against %r records that it "
                                          "matched on %r, but the rule matches on %r. The "
                                          "evidence shown to the reader is not the evidence that "
                                          "was used." % (head[:60], name, claimed, ev.get("alias")))

    # ---- counts must equal the rows (prose-vs-data drift) -------------------
    counts = doc.get("counts") or {}
    for label, stated, actual in (
            ("suppliers", counts.get("suppliers"), len(suppliers)),
            ("suppliersWithItems", counts.get("suppliersWithItems"), with_items),
            ("items", counts.get("items"), items_seen),
            ("sources", counts.get("sources"), sources_seen),
            ("resolvedLinks", counts.get("resolvedLinks"), resolved_seen),
            ("redirectLinks", counts.get("redirectLinks"), redirect_seen)):
        if stated is not None and stated != actual:
            FAIL("company-press", "data/company-press.json states %s = %s but holds %d. This is "
                                  "the drift that reached the gate on 14/08/2026: a counts header "
                                  "from one generation over rows from another. Regenerate the "
                                  "file; never hand-correct the header."
                                  % (label, stated, actual))




# --------------------------------------------------------------------------
# HOSPITAL PRESCRIBING (NHSBSA) — data/hospital-prescribing/ + app/hospital-prescribing.js
# --------------------------------------------------------------------------
# Items prescribed by an NHS trust in England and dispensed in a community
# pharmacy. The layer is optional: no index file means the tool is not built and
# nothing here fires. Built, it has to be whole, because every failure mode below
# looks completely normal in a diff of a machine-written file.
#
# The tests in test_verify.py drove each of these. They existed before the checks
# did, which is why the tool sat unpublished: 11 MB of member-facing prescribing
# data with a gate that could not see it.
HP_DIR = "data/hospital-prescribing"
HP_INDEX = os.path.join(HP_DIR, "index.json")
HP_JS = os.path.join("app", "hospital-prescribing.js")


def _hp_months_between(a, b):
    """Count of YYYYMM steps from a to b. Both are strings."""
    ya, ma = int(a[:4]), int(a[4:])
    yb, mb = int(b[:4]), int(b[4:])
    return (yb - ya) * 12 + (mb - ma)


def check_hospital_prescribing(doc):
    if not doc:
        return

    # 1. THE MONTHLY SERIES MUST NOT CLOSE UP OVER A MISSING MONTH.
    # NHSBSA does not publish every month on time. A month it never published is
    # carried in missingPeriods and rendered as a break in the line. If it is
    # simply dropped from periods instead, twelve months of trend quietly become
    # eleven and every rate computed across the gap is wrong, with nothing on the
    # page saying so.
    periods = [str(p) for p in (doc.get("periods") or [])]
    missing = [str(p) for p in (doc.get("missingPeriods") or [])]
    if not periods:
        FAIL("hospital-prescribing", "%s publishes no periods at all. An empty series is "
                                     "not a trend — do not publish the panel." % HP_INDEX)
    else:
        bad = [p for p in periods if not re.fullmatch(r"\d{6}", p)]
        if bad:
            FAIL("hospital-prescribing", "%s carries malformed period(s) %s — expected YYYYMM."
                                         % (HP_INDEX, ", ".join(bad[:5])))
        else:
            if sorted(periods) != periods:
                FAIL("hospital-prescribing", "%s lists its periods out of order. The panel trends "
                                             "them in file order, so the chart would read backwards "
                                             "over the jump." % HP_INDEX)
            span = _hp_months_between(periods[0], periods[-1]) + 1
            if span != len(periods):
                absent, y, m = [], int(periods[0][:4]), int(periods[0][4:])
                held = set(periods)
                for _ in range(span):
                    stamp = "%04d%02d" % (y, m)
                    if stamp not in held:
                        absent.append(stamp)
                    m += 1
                    if m == 13:
                        y, m = y + 1, 1
                FAIL("hospital-prescribing",
                     "gap in the monthly series: %s runs %s to %s, which is %d months, but holds "
                     "only %d. Absent: %s. A month NHSBSA never published keeps its slot and is "
                     "named in missingPeriods so the line breaks — it is never closed up, because "
                     "closing it up silently shortens every rate computed across it."
                     % (HP_INDEX, periods[0], periods[-1], span, len(periods),
                        ", ".join(absent[:6]) or "none identifiable"))
            stray = [p for p in missing if p not in set(periods)]
            if stray:
                FAIL("hospital-prescribing",
                     "%s names %s in missingPeriods but does not carry the slot in periods. A "
                     "missing month is a break in the series, not an absence from it."
                     % (HP_INDEX, ", ".join(stray[:5])))

    # 2. THE BRAND/GENERIC FLAG MUST AGREE WITH THE SHARD IT SUMMARISES.
    # BNF product code characters 10-11 are "AA" for the generic. The index's `g`
    # is a summary of what the chapter shard actually holds. If the two disagree
    # the panel tells a rep a molecule has no generic competition when the shard
    # in front of them lists one, which is the wrong way round for a sales call.
    subs = doc.get("substances") or []
    mismatched = 0
    shards = {}
    for row in subs:
        code, ch = str(row.get("c") or ""), str(row.get("ch") or "")
        if not code or not ch:
            continue
        if ch not in shards:
            try:
                with open(os.path.join(HP_DIR, "ch-%s.json" % ch)) as f:
                    shards[ch] = json.load(f)
            except Exception:
                shards[ch] = None
        shard = shards[ch]
        if not shard:
            continue
        rec = (shard.get("s") or {}).get(code)
        if not isinstance(rec, dict):
            continue
        prods = rec.get("p")
        if not isinstance(prods, dict) or not prods:
            continue
        has_generic = "AA" in prods
        if bool(row.get("g")) != has_generic:
            mismatched += 1
            if mismatched <= 5:
                FAIL("hospital-prescribing",
                     "the brand/generic rule has broken: %s (%s) is flagged g=%s but its chapter "
                     "%s shard %s a product under BNF segment 'AA'. The flag summarises the shard "
                     "and cannot disagree with it — a rep would be told a molecule has no generic "
                     "competition while the shard in front of them lists one."
                     % (row.get("n") or code, code, bool(row.get("g")), ch,
                        "does hold" if has_generic else "holds no"))
    if mismatched > 5:
        FAIL("hospital-prescribing", "the brand/generic rule has broken on %d further molecules "
                                     "(only the first 5 are listed)." % (mismatched - 5))

    # 3. THE PUBLISHED EVIDENCE FLOOR MUST BE THE ONE THE BUILDER APPLIED.
    # Root rule 14: the rule a claim was derived under is published with it. If
    # the file says the floor is 2 while the builder used 25, the file documents a
    # rule nothing enforced, and the reader judges the number against the wrong bar.
    stated = doc.get("minBaselineItems")
    built = None
    try:
        src = open("scripts/refresh_hospital_prescribing.py").read()
        m = re.search(r"^MIN_BASELINE_ITEMS\s*=\s*(\d+)", src, re.M)
        built = int(m.group(1)) if m else None
    except Exception:
        pass
    if built is None:
        WARN("hospital-prescribing", "could not read MIN_BASELINE_ITEMS from "
                                     "scripts/refresh_hospital_prescribing.py — the published "
                                     "evidence floor was not checked against the builder.")
    elif stated != built:
        FAIL("hospital-prescribing",
             "%s states an evidence floor of %s items, which is not the rule applied: the "
             "builder used MIN_BASELINE_ITEMS = %d. Lowering the floor on the published file "
             "does not lower it in the data — it only misdescribes it."
             % (HP_INDEX, stated, built))

    # 4. THE PANEL MUST STILL PRINT ITS REFUSAL.
    # Below the floor the tool prints "too few to trend" and no number. That
    # refusal IS the honest empty state. Silently swapping it for "n/a" or a
    # number is how thin evidence starts reading as a finding.
    if os.path.exists(HP_JS):
        try:
            js = open(HP_JS, encoding="utf-8").read()
        except Exception as exc:
            WARN("hospital-prescribing", "could not read %s (%s) — the refusal string was "
                                         "not checked." % (HP_JS, exc))
        else:
            if "too few to trend" not in js:
                FAIL("hospital-prescribing",
                     "%s no longer prints the refusal 'too few to trend'. Below the evidence "
                     "floor the panel must refuse in words and print no number." % HP_JS)

    # 5. THE INDEX MUST NOT SILENTLY SHRINK.
    # A part-completed NHSBSA download parses cleanly and produces a perfectly
    # valid file holding a fraction of the trusts. Nothing in git treats "this
    # file lost 170 trusts" as a conflict, so the gate has to.
    #
    # The guard is self-contained rather than a comparison against the last
    # commit, because the first publish of a file has nothing to compare to —
    # which is exactly when a truncated build is most likely to go out. The
    # shards are the evidence: every trust code they carry a series for must be
    # named in the index, or the index is not describing the data beside it.
    listed = set(doc.get("trusts") or {})
    referenced = set()
    for ch, shard in shards.items():
        if not shard:
            continue
        for rec in (shard.get("s") or {}).values():
            if isinstance(rec, dict) and isinstance(rec.get("t"), dict):
                referenced.update(rec["t"])
    if referenced:
        orphaned = referenced - listed
        if orphaned:
            FAIL("hospital-prescribing",
                 "Refusing a shrunken prescribing index: the chapter shards carry series for %d "
                 "trusts, but index.json names only %d of them — %d are unlisted (%s%s). A "
                 "truncated NHSBSA build parses perfectly and reads like a normal refresh, so "
                 "the shards are the check. Find out what broke; do not publish the short index."
                 % (len(referenced), len(referenced) - len(orphaned), len(orphaned),
                    ", ".join(sorted(orphaned)[:5]), " ..." if len(orphaned) > 5 else ""))

    # The relative guard still applies once there is a committed baseline: a drop
    # that keeps the index and its shards consistent (both truncated together)
    # would pass the check above and still be wrong.
    old = committed(HP_INDEX)
    if old:
        o, n = len(old.get("trusts") or {}), len(listed)
        if o and n < o * 0.9:
            FAIL("hospital-prescribing",
                 "Refusing a shrunken prescribing index: trusts drop from %d to %d (-%.0f%%). "
                 "Find out what broke, or override deliberately and say why in the commit."
                 % (o, n, (1 - n / o) * 100))


# --------------------------------------------------------------------------
# THE DIFFERENTIATOR — data/differentiator.json
# --------------------------------------------------------------------------
# Product-level comparison, built from the manufacturer's own site AND the NHSSC
# catalogue. Optional: no file means the layer is not built.
#
# The failure this gates is not a wrong number, it is a wrong COMPARISON. Two
# products put side by side that are not the same kind of thing produce a table
# where every row reads "n/a", and a member reads that as a product that fails on
# every measure rather than a product that was never comparable. So the category
# lock is the check: one category per product, from the vocabulary the Compare
# tab already gates, and nothing published without it.
def check_differentiator(doc, vocab):
    if not doc:
        return

    legal = set()
    for s, v in (vocab or {}).get("specialities", {}).items():
        for t in (v.get("types") or {}):
            legal.add("%s:%s" % (s, t))

    prods = doc.get("products") or []
    counts = doc.get("counts") or {}

    # The Frankenstein guard. A counts header from one generation above rows from
    # another is exactly what a text-merged generated file looks like (14/08).
    if counts.get("published") is not None and counts["published"] != len(prods):
        FAIL("differentiator", "data/differentiator.json states published = %s but holds %d "
                               "product(s). The header and the rows come from different "
                               "generations — regenerate, do not reconcile by hand."
                               % (counts["published"], len(prods)))

    uncategorised = [p for p in prods if not p.get("cat")]
    if uncategorised:
        FAIL("differentiator", "%d published product(s) carry no category, starting with %s. "
                               "An uncategorised product is held, never published: it would be "
                               "comparable against everything."
                               % (len(uncategorised),
                                  ", ".join("%s / %s" % (p.get("supplier"), p.get("name"))
                                            for p in uncategorised[:3])))

    if legal:
        stray = sorted({p["cat"] for p in prods if p.get("cat") and p["cat"] not in legal})
        if stray:
            FAIL("differentiator", "%d product category/ies are not in the gated vocabulary: %s. "
                                   "A category the Compare tab cannot render is a category no "
                                   "member can filter to." % (len(stray), ", ".join(stray[:5])))

    sourceless = [p for p in prods if not (p.get("sources") or [])]
    if sourceless:
        FAIL("differentiator", "%d published product(s) carry no source at all, starting with "
                               "%s. Every published fact carries its source — a product with "
                               "none cannot be checked by the member reading it."
                               % (len(sourceless),
                                  ", ".join("%s / %s" % (p.get("supplier"), p.get("name"))
                                            for p in sourceless[:3])))

    nourl = [p for p in prods
             if (p.get("sources") or []) and not any(s.get("url") for s in p["sources"])]
    if nourl:
        FAIL("differentiator", "%d published product(s) name a source with no URL to reach it, "
                               "starting with %s." % (len(nourl),
                               ", ".join("%s / %s" % (p.get("supplier"), p.get("name"))
                                         for p in nourl[:3])))

    # A category holding one product is not a comparison. It may be published and
    # read, but it must never be offered as something to compare within, or the
    # member is invited into a table with a single column.
    bycat = {}
    for p in prods:
        if p.get("cat"):
            bycat[p["cat"]] = bycat.get(p["cat"], 0) + 1
    singles = sorted(c for c, n in bycat.items() if n < 2)
    stated = counts.get("comparableCategories")
    if stated is not None and stated != len([c for c, n in bycat.items() if n >= 2]):
        FAIL("differentiator", "data/differentiator.json states %s comparable categories but "
                               "%d hold two or more products. The count a member is shown must "
                               "be the count that exists."
                               % (stated, len([c for c, n in bycat.items() if n >= 2])))
    if singles:
        WARN("differentiator", "%d category/ies hold a single product (%s%s) — publishable, but "
                               "never offer them as a comparison."
                               % (len(singles), ", ".join(singles[:4]),
                                  " ..." if len(singles) > 4 else ""))



def check_awareness(doc):
    """The hand-maintained half of the calendar. Every other calendar stream is derived
    from a store that already has its own gate; this one is typed by a person, so this
    is where the source discipline has to be enforced.

    Written 21/08/2026 with the calendar. The failure it exists to stop is the one root
    rule 12 was written after: an awareness date carried forward from a previous edition,
    or lifted off an aggregator, quietly going stale and telling a member to plan a
    campaign around a week that moved."""
    if doc is None:
        return  # The calendar is not built. An absent file is not a failure.

    days = doc.get("days")
    if days is None:
        FAIL("awareness", "awareness-days.json has no `days` list.")
        return
    if doc.get("unverified") is None:
        FAIL("awareness", "awareness-days.json has no `unverified` list. A gap that is "
                          "not recorded is a gap that gets silently filled later.")

    seen = set()
    for e in days:
        eid = e.get("id") or "(no id)"
        if eid in seen:
            FAIL("awareness", "%s: duplicate id." % eid)
        seen.add(eid)

        # Attribution. Nothing publishes without an owner and that owner's own page.
        for field in ("name", "owner", "source", "verified", "dateRule", "repAction"):
            if not e.get(field):
                FAIL("awareness", "%s: missing `%s`. Every published entry names the body "
                                  "that owns the date, the page it was read from, when it "
                                  "was read, and what a rep should do about it." % (eid, field))
        src = e.get("source") or ""
        if src:
            if not src.startswith("http"):
                FAIL("awareness", "%s: `source` is not a URL." % eid)

        rule = e.get("dateRule")
        if rule == "fixed":
            if not e.get("month"):
                FAIL("awareness", "%s: dateRule 'fixed' needs `month` and `day`." % eid)
            if not e.get("day"):
                FAIL("awareness", "%s: dateRule 'fixed' needs `month` and `day`." % eid)
        elif rule == "computed":
            for field in ("rule", "month", "weekday", "ordinal"):
                if not e.get(field):
                    FAIL("awareness", "%s: dateRule 'computed' needs `%s`. A moving date is "
                                      "projected ONLY from the rule its owner publishes, "
                                      "never from last year's date." % (eid, field))
        elif rule == "announced":
            occ = e.get("occurrences") or []
            if not occ:
                FAIL("awareness", "%s: dateRule 'announced' with no occurrences. It should "
                                  "be in `unverified`, not published with no date." % eid)
            newest = ""
            for o in occ:
                start = (o.get("start") or "")
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", start):
                    FAIL("awareness", "%s: occurrence start '%s' is not an ISO date."
                                      % (eid, start))
                if start > newest:
                    newest = start
            # The annual-review teeth. An announced date the owner has not restated is
            # the exact thing that goes stale, so an entry whose newest stated occurrence
            # has passed must be re-read, not left sitting there looking current.
            if newest:
                if newest < datetime.date.today().isoformat():
                    FAIL("awareness", "%s: the newest occurrence its owner has stated (%s) is "
                                      "in the past. Re-read %s and add the new dates, or move "
                                      "the entry to `unverified`."
                                      % (eid, newest, e.get("source")))
        else:
            FAIL("awareness", "%s: unknown dateRule '%s'. Must be fixed, computed or "
                              "announced." % (eid, rule))

    for u in (doc.get("unverified") or []):
        if not u.get("reason"):
            FAIL("awareness", "%s: recorded as unverified with no reason. The reason is the "
                              "whole point of the list." % (u.get("id") or "(no id)"))
        if u.get("id") in seen:
            FAIL("awareness", "%s: is in BOTH `days` and `unverified`." % u.get("id"))


def check_calendar(doc, specmap_unused=None):
    """The built calendar. Derived from stores that each have their own gate, so this
    checks the JOIN rather than re-deriving the data: that every row can be attributed,
    that no row asserts a date it cannot source, and above all that no row carries a Hub
    link the calendar invented.

    A dead link on a members' page is worse than no link, and it is the failure this
    build already hit once: pages-map.json calls a speciality `therapies-physio-and-ot`
    but that page was renamed and lives at /patient-handling/, so a URL built from the
    slug 404'd. The builder now resolves permalinks from the live site; this check makes
    sure nobody quietly reintroduces the shortcut."""
    if doc is None:
        return

    entries = doc.get("entries")
    if entries is None:
        FAIL("calendar", "hub-calendar.json has no `entries` list.")
        return

    meta = doc.get("_meta") or {}
    if not meta.get("derivationRule"):
        FAIL("calendar", "hub-calendar.json states no derivation rule. Every derived "
                         "dataset carries the rule it was derived under (root rule 14).")
    if not meta.get("dataAsOf"):
        FAIL("calendar", "hub-calendar.json carries no dataAsOf stamp.")

    allowed = set(meta.get("types") or [])
    known_specs = {s.get("slug") for s in (doc.get("specialities") or [])}
    spec_urls = {s.get("url") for s in (doc.get("specialities") or [])}
    today = datetime.date.today().isoformat()
    seen = set()

    for e in entries:
        eid = e.get("id") or "(no id)"
        if eid in seen:
            FAIL("calendar", "%s: duplicate entry id." % eid)
        seen.add(eid)

        if e.get("type") not in allowed:
            FAIL("calendar", "%s: type '%s' is not one the file declares."
                             % (eid, e.get("type")))
        if not e.get("title"):
            FAIL("calendar", "%s: no title." % eid)
        if not e.get("rule"):
            FAIL("calendar", "%s: no `rule`. A member has to be able to judge how a row "
                             "was arrived at." % eid)

        date = e.get("date") or ""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            FAIL("calendar", "%s: date '%s' is not an ISO date." % (eid, date))
            continue
        end = e.get("endDate")
        if end:
            if end < date:
                FAIL("calendar", "%s: endDate %s is before date %s." % (eid, end, date))
        # A past date is dropped, not shown as expired. The single exception is a
        # framework end inside the recent-past window, and it must be flagged as past.
        if date < today:
            if e.get("type") != "framework-end":
                FAIL("calendar", "%s: date %s is in the past. Only a recently expired "
                                 "framework may appear, and only flagged as past."
                                 % (eid, date))
            elif not e.get("past"):
                FAIL("calendar", "%s: past date %s not flagged `past`." % (eid, date))

        for slug in (e.get("specialities") or []):
            if slug not in known_specs:
                FAIL("calendar", "%s: speciality '%s' is not in the file's own speciality "
                                 "list, so the page link cannot be trusted." % (eid, slug))

        links = e.get("links") or []
        if not links:
            FAIL("calendar", "%s: no links at all. Every row reaches either the Hub page "
                             "that explains it or the source it came from." % eid)
        for l in links:
            if not l.get("url"):
                FAIL("calendar", "%s: a link with no url." % eid)
                continue
            if not l.get("label"):
                FAIL("calendar", "%s: a link with no label." % eid)
            if l.get("kind") == "hub":
                url = l["url"]
                if not url.startswith("https://medsalesintelligencehub.co.uk/"):
                    FAIL("calendar", "%s: hub link '%s' is not on the Hub." % (eid, url))
                    continue
                # The anti-guessing invariant. A hub link is either a resolved
                # speciality permalink or one of the declared anchor pages. A URL
                # assembled from a slug is exactly what 404'd before.
                if url not in spec_urls:
                    if "/medical-sales-hub/" not in url:
                        FAIL("calendar", "%s: hub link '%s' is neither a resolved "
                                         "speciality permalink nor a Hub page." % (eid, url))

    if doc.get("awarenessGaps") is None:
        FAIL("calendar", "hub-calendar.json carries no awarenessGaps list. The gaps are "
                         "published deliberately so a member can see what is missing.")


def main():
    offline = "--offline" in sys.argv
    as_json = "--json" in sys.argv
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    optout = load("contacts-optout.json") or {}
    blocked = {n.strip().lower() for n in optout.get("names", []) if n.strip()}

    # RETENTION_MONTHS moved to msh-hub-private on 17/08/2026 along with the
    # harvester itself (commit d5ba46e) — it lives at
    # scripts/refresh_fts_contacts.py there, currently 24, matching the
    # published privacy notice. This repo only ever sees synthetic contact
    # data (see contacts-optout.json / the _synthetic marker in
    # trust-contacts.json), so retention enforcement is meaningless here and
    # is the private repo's own verify.py's job, not this one's.
    retention = None

    trust_codes = check_trust_map(load("trust-map.json"))
    n = check_contacts(load("trust-contacts.json"), trust_codes, blocked, retention) or 0
    check_tags(load("trust-contacts.json"), load("products.json"))
    check_moves(load("people-moves.json"), trust_codes, blocked,
                (load("trust-contacts.json") or {}).get("trusts", {}))
    check_privacy(n, retention, offline)
    check_trust_pressures(load("trust-pressures.json"), trust_codes)
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
    check_seed_framework_provenance(load("supplier-seed.json"))
    check_seed_product_categories(load("supplier-seed.json"))
    check_seed_people_and_partners(load("supplier-seed.json"))
    check_seed_links(load("supplier-seed.json"))
    check_migrated_prose_not_in_alerts(load("supplier-seed.json"),
                                       load("supplier-index.json"))
    check_curated_alerts_are_typed(load("supplier-index.json"))
    check_seed_index_alert_parity(load("supplier-seed.json"),
                                  load("supplier-index.json"))
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
    # The award index. Every published match is re-derived from the same module
    # the writer used, so the file and the rule cannot drift apart unnoticed.
    check_company_awards(load("company-awards.json"), load("supplier-seed.json"), report_js)
    # NHS Supply Chain framework awards public on Find a Tender but not yet on
    # NHSSC's own contract launch brief. Every match AND every supersede
    # decision is re-derived from the same module the writer used.
    check_pending_awards(load("pending-awards.json"), load("supplier-seed.json"),
                         load("frameworks.json"), report_js)
    # The supplier press index. Every published attribution is re-derived from the
    # same module the writer used, so a story cannot end up under the wrong
    # company without the gate saying so.
    check_company_press(load("company-press.json"), load("supplier-seed.json"))
    # The brand-mark layer. Optional like the two above: an absent file means
    # every company draws the monogram, which is a finished design rather than a
    # gap. Present, it must be whole — see the note above check_company_logos.
    check_company_logos(load("company-logos.json"), report_js)
    # Per-product detail captured from each supplier's own product page.
    check_supplier_product_detail(load("supplier-product-detail.json"), load("supplier-products.json"))
    # NHSBSA hospital prescribing. Optional like the layers above: no index means
    # the tool is not built. Built, every check below is one the tests demanded
    # before the checks existed — which is exactly why it had not shipped.
    check_hospital_prescribing(load("hospital-prescribing/index.json"))
    # The Differentiator. The category lock is the check — see the note above.
    check_differentiator(load("differentiator.json"), load("compare-suppliers.json"))

    # The Calendar. Two checks: the hand-typed awareness input, where the source
    # discipline has to be enforced, and the built join, where the risk is an
    # invented Hub link.
    check_awareness(load("awareness-days.json"))
    check_calendar(load("hub-calendar.json"))

    check_search_index(load(SEARCH_INDEX))

    check_shrink()
    check_notice()
    check_no_clusters_on_tools(comptab_js)
    check_compare_groups_by_ref(comptab_js)
    check_no_expired_frameworks(load("frameworks.json"))
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
