#!/usr/bin/env python3
"""Synthetic stand-ins for the two named-NHS-contact files, for THIS public repo.

WHY THIS EXISTS
`data/trust-contacts.json` and `data/people-moves.json` hold real named NHS staff
and their work email addresses. They were published to this public repo by accident
on 24/07/2026 and removed on 17/08/2026; they now live only in the private repo
`msh-hub-private` and reach members through the gated endpoint. See
`.gitignore` and the process note `hub-data-gate.md`.

test_verify.py went with them, because every one of its contact and moves cases
reads those files off disk. That left the public repo's CI running `verify.py`
untested, and two copies of `verify.py` free to drift apart — the exact
"a gate nobody tests is a gate that quietly stops working" failure the suite was
written to prevent.

So this module manufactures a contacts index and a moves file that are SHAPED
like the real ones and contain no real person. Nothing here is harvested,
inferred, or derived from the real data: the names are invented, the addresses
are all at `.invalid` (RFC 2606 — a domain guaranteed never to resolve), and the
trust codes are the only real thing, read from the public `data/trust-map.json`
because `verify.py` rightly refuses contacts filed under a code it cannot place.

WHAT IT IS AND IS NOT FOR
It proves the gate's LOGIC still fires. It cannot prove anything about the real
data, and it must never be published: `write()` returns the paths it created so
the caller deletes them at the end of the run, and both paths are in `.gitignore`
so a stray `git add -A` cannot commit them either.

THE ONE RULE THAT MATTERS HERE
The baseline this writes must PASS verify.py cleanly. Every case in the suite
works by breaking one thing and demanding a specific rejection; if the baseline
itself trips a check, every case "passes" for the wrong reason and the suite is
decoration. `python3 tests/fixtures/contacts.py --check` asserts exactly that.

Stdlib only. Tags are derived by calling `scripts/notice_tags.py`, the same module
verify.py re-derives them with, so the two cannot disagree by construction.
"""
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def set_root(path):
    """Point the fixture at `path` instead of the real repo.

    test_verify.py runs against a per-run COPY of the repo so it never writes to
    the live data/ directory (see its header, 03/09/2026). The fixture writes
    two synthetic contact files, and it wrote them by absolute path into the
    real repo — so it was the one part of the run still touching live data.
    Everything below reads this global at call time, so redirecting it here is
    enough; the copy carries data/ and scripts/, which is all the fixture reads.
    """
    global REPO
    REPO = os.path.abspath(path)
CONTACTS = os.path.join("data", "trust-contacts.json")
MOVES = os.path.join("data", "people-moves.json")

# The rules the moves file declares. verify.py fails a moves file that does not
# state every one of them, so the fixture states them too — and at the real
# values, not looser ones. minNotices below 2 is itself a failure the suite tests.
GAP_DAYS = 60
MIN_NOTICES = 2
MIN_SPAN_DAYS = 30

TAG_RULE = ("Synthetic fixture. Speciality tags are derived from the notice title only, by "
            "scripts/notice_tags.py. A tag means the person was named on a notice whose title "
            "matches that speciality — never that they hold the remit.")

# Notice titles, chosen to spread across specialities and to include clinical,
# nonclinical and unclear titles in roughly the proportion the real index has
# (about one title in eleven is clinical). The FIRST title must not tag as
# vascular/clinical: the vocabulary-drift case rewrites the first contact's tags
# to exactly that and expects the gate to notice the disagreement.
TITLES = [
    "Provision of managed print and reprographics IT0912",
    "Supply of peripheral vascular access devices and midlines",
    "Wound care dressings and negative pressure therapy",
    "Staff restaurant and hospitality catering services",
    "Continence assessment and product supply",
    "Grounds maintenance and external cleaning",
    "Flexible endoscopy decontamination equipment",
    "Agency locum medical staffing framework",
    "UHL_A_Neurophysiology_2628.V.0.1",
    "Fire alarm system replacement and maintenance",
]

# Invented people. Deliberately ordinary two-part names that no DEPARTMENTAL
# term appears in — 'team', 'procurement', 'supplies', 'services' and the rest
# are what verify.py rejects as a desk rather than a person.
PEOPLE = [
    "Alice Fernsby", "Bruno Calderwood", "Carys Millward", "Dermot Ashfield",
    "Elena Rothbury", "Farouk Pemberly", "Greta Lindmoor", "Hamish Trelawn",
    "Imogen Vasterly", "Joseph Marbeck", "Kirsten Aldwych", "Lucian Everdon",
    "Marisa Quenton", "Nathaniel Broughsey", "Orla Pennington", "Piers Halcombe",
]


def _trust_codes(n):
    """Real ODS codes from the public trust map, minus the ones cases hardcode.

    'RWD' is excluded on purpose. Two cases claim a handover at RWD for a person
    who is not in the index and expect UNSOURCED, so RWD must stay empty here.
    """
    with open(os.path.join(REPO, "data", "trust-map.json")) as f:
        codes = [t.get("code") for t in json.load(f).get("trusts", []) if t.get("code")]
    return [c for c in codes if c != "RWD"][:n]


def _tagger():
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import notice_tags
    return notice_tags.tag


def _notice(filename):
    """The repo's real ownership notice, taken from the script that stamps it.

    verify.py fails any data file whose notice is missing or has drifted, and it
    is right to: a file published without it is published without its licence
    terms. It compares the block for EXACT equality, so nothing may be added to
    it — the "this is invented" warning goes in a sibling key, `_synthetic`.
    """
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import stamp_notice
    return stamp_notice.notice_for(filename)


SYNTHETIC_WARNING = ("TEST FIXTURE — invented names, no real person appears here. Generated by "
                     "tests/fixtures/contacts.py because the real file holds named NHS staff and "
                     "lives only in the private repo. Never commit or publish this file.")


def build():
    """The two documents, as Python objects. Dates are relative to today, always.

    Hardcoded dates would age into the retention cutoff and start failing the
    baseline months later, for a reason nobody would connect to this file.
    """
    tag = _tagger()
    today = datetime.date.today()

    def d(days_ago):
        return (today - datetime.timedelta(days=days_ago)).isoformat()

    # Six trusts. Trust 0 gets three contacts and is the one the tag, retention
    # and opt-out cases reach for (they take list(trusts)[0]). Trust 1 holds
    # exactly two contacts on one notice each, which is what pick(1, 2) hunts
    # for — the thin-evidence and minNotices cases are built on that pair.
    codes = _trust_codes(6)
    if len(codes) < 6:
        raise SystemExit("trust-map.json holds too few codes to build the fixture")

    plan = [
        (codes[0], [(0, 3), (1, 4), (2, 2)]),      # (title index, n notices)
        (codes[1], [(3, 1), (4, 1)]),              # the two single-notice contacts
        (codes[2], [(5, 2), (6, 3)]),
        (codes[3], [(7, 2)]),
        (codes[4], [(8, 5), (9, 2)]),
        (codes[5], [(1, 2), (2, 3)]),
    ]

    trusts, who, window = {}, 0, 20
    for code, entries in plan:
        rows = []
        for title_i, n in entries:
            # WINDOWS NEVER OVERLAP, within a trust or across the file. Two
            # contacts active at the same time at one trust means the trust has
            # more than one buyer, and verify.py fails any move claimed there —
            # correctly. An overlap here would make the thin-evidence case fail
            # as CONCURRENT BUYERS instead, i.e. pass for the wrong reason.
            last, first = window, window + 25
            window = first + 10
            notice = TITLES[title_i]
            spec, cls = tag(notice)
            rows.append({
                "name": PEOPLE[who % len(PEOPLE)],
                "email": "%s@example.invalid" % PEOPLE[who % len(PEOPLE)].lower().replace(" ", "."),
                "first": d(first),
                "last": d(last),
                "n": n,
                "notice": notice,
                "ocid": "ocds-synthetic-%04d" % who,
                "spec": sorted(spec),
                "cls": cls,
            })
            who += 1
        trusts[code] = rows

    total = sum(len(v) for v in trusts.values())
    counts = {}
    for rows in trusts.values():
        for e in rows:
            counts[e["cls"]] = counts.get(e["cls"], 0) + 1
    if not counts.get("clinical"):
        raise SystemExit("fixture has no clinical notice — check_tags requires at least one")

    contacts = {
        "_notice": _notice("trust-contacts.json"),
        "_synthetic": SYNTHETIC_WARNING,
        "generated": today.isoformat(),
        "contactsTotal": total,
        "tagRule": TAG_RULE,
        "noticeClassCounts": counts,
        "trusts": trusts,
    }

    # An EMPTY moves list is the correct baseline. A published handover has to
    # clear the gap rule, the evidence floor and the concurrency test, and a
    # fixture that ships one would be asserting a claim it cannot source. The
    # cases add their own move and expect it rejected.
    moves = {
        "_notice": _notice("people-moves.json"),
        "_synthetic": SYNTHETIC_WARNING,
        "generated": today.isoformat(),
        "gapDays": GAP_DAYS,
        "minNotices": MIN_NOTICES,
        "minSpanDays": MIN_SPAN_DAYS,
        "singleThreadedOnly": True,
        "rule": ("A handover is claimed only where one name stops appearing and another starts, "
                 "at a trust with a single active contact, with at least %d days between them "
                 "and each name seen on at least %d notices." % (GAP_DAYS, MIN_NOTICES)),
        "moves": [],
    }
    return contacts, moves


def write(force=False):
    """Materialise the fixture. Returns the paths written, for the caller to remove.

    Refuses to overwrite a file that is already there. In the private repo both
    files exist and hold the real data; silently replacing them would run the
    suite against invented people and report a green gate for data it never read.
    """
    written = []
    for path, doc in ((CONTACTS, None), (MOVES, None)):
        if os.path.exists(os.path.join(REPO, path)) and not force:
            return []                     # real data present — use it, untouched
    contacts, moves = build()
    for path, doc in ((CONTACTS, contacts), (MOVES, moves)):
        full = os.path.join(REPO, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            json.dump(doc, f, indent=1)
        written.append(path)
    return written


def remove(paths):
    for p in paths:
        full = os.path.join(REPO, p)
        if os.path.exists(full):
            os.remove(full)


def _check():
    """Prove the baseline passes the gate, then clean up. Exit 0 = usable."""
    import subprocess
    if os.path.exists(os.path.join(REPO, CONTACTS)):
        print("real contact data is present — the fixture is not needed here")
        return 0
    paths = write()
    if not paths:
        print("FIXTURE NOT WRITTEN")
        return 1
    try:
        r = subprocess.run([sys.executable, "verify.py", "--offline"], cwd=REPO,
                           capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        if r.returncode != 0:
            print("FIXTURE IS NOT CLEAN — verify.py rejects the baseline:\n" + out)
            return 1
        noise = [l for l in out.splitlines()
                 if l.startswith("WARN") and ("contacts" in l or "moves" in l or "privacy" in l)]
        print("fixture baseline PASSES verify.py")
        for l in noise:
            print("   " + l)
        return 0
    finally:
        remove(paths)


if __name__ == "__main__":
    sys.exit(_check() if "--check" in sys.argv else
             (print("\n".join(write() or ["(nothing written — real data present)"])) or 0))
