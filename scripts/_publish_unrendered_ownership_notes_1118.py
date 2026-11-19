#!/usr/bin/env python3
"""
_publish_unrendered_ownership_notes_1118.py — make 19 records' sourced
ownership facts visible to a member, without rewriting a word of them.

THE FINDING (verified 18/11/2026 against main at 7a0a9365)
----------------------------------------------------------
app/company-report.js renders the member-facing "Structure & ownership"
section from ownershipBlock(s) (line 2630), and that function reads ONE
thing:

    function ownershipBlock(s) {
      var d = deepFor(s);                      // s.deepDive || null
      if (!(d && d.ownership && d.ownership.length)) return '';
      ...
    }

Nothing anywhere in app/*.js reads a TOP-LEVEL `ownership` key. The only
two `.ownership` reads in the whole app directory are the two lines inside
ownershipBlock. So a top-level `ownership` string is invisible on the card.

In data/supplier-seed.json there were, at 7a0a9365:

    310  records with deepDive.ownership          -> rendered
     32  records with a top-level `ownership`     -> string
      2  records with a top-level `ownership`     -> dict (structured
         (Direct Healthcare Group, Talley)           companyNumber/ultimateParent
                                                     fields, a different shape;
                                                     both already carry their
                                                     own deepDive.ownership)

Of the 32 string-typed ones, 13 ALREADY have a deepDive.ownership that
names the same controlling entity, so the ownership fact is on their card
already. 19 have no deepDive at all, so their ownership fact reaches no one.
Those 19 are what this script publishes. Lengths run 479 to 1743
characters; every one names a parent, carries an effective or read date,
and cites the page it was read from. Not one is a throwaway line.

WHY COPY AND NOT MOVE
---------------------
The top-level key has a live consumer. scripts/refresh_supplier_careers.py,
in _is_umbrella() at line 1079:

    own = str((seed_by_name.get(g.get("name")) or {}).get("ownership") or "").lower()

reads the top-level string as flat text to work out which record in a group
sharing one careers site is the umbrella parent — "true where every OTHER
member's own ownership text names this record". Moving the key would blind
that rule. test_careers_shared_roles.py line 113 builds its TIER 2 fixture
on the same top-level shape. So the string is COPIED into
deepDive.ownership and left in place, and ownershipCheckedOn is left
exactly where it is.

Checked and found NOT to consume the top-level key: build_supplier_index.py
(no mention of ownership at all), verify.py (its `ownership` hits are the
repo's ownership NOTICE, an unrelated thing), scripts/completeness.py
(reads deepDive only, via EDITORIAL_SECTIONS), scripts/_report_text_cleanup_0930.py
(walks deepDive.ownership only), app/mst-logic.js ("total cost of
ownership", unrelated).

WHY THE PROSE IS NOT TOUCHED
----------------------------
Each string was written deliberately, is dated, and ends in the source it
was read from. Re-wording it would strip the sourcing, which is the thing
that makes it publishable at all. It is copied byte for byte as a single
paragraph, and an assertion below proves that.

NOT IN SCOPE
------------
  * The two Clinisupplies records, settled on 18/11/2026 by
    scripts/_add_clinisupplies_group_link_1118.py. Asserted untouched.
  * The 13 string-typed records that already render an ownership section.
    Their deepDive prose already names the same controlling entity, so no
    ownership fact is hidden there, and appending a second account of the
    same PSC notification would print it to a member twice. Left alone.
  * The 2 dict-shaped records. A different shape, both already rendering.

Idempotent: a record that already has a deepDive.ownership is skipped, so
a second run writes nothing.

    python3 scripts/_publish_unrendered_ownership_notes_1118.py          # apply
    python3 scripts/_publish_unrendered_ownership_notes_1118.py --dry-run
"""
import json
import sys
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "supplier-seed.json"

# The 19, enumerated from the file at 7a0a9365 and pinned here so a later run
# cannot silently sweep up a record some other writer has added since.
EXPECTED = {
    "Abiomed Ltd",
    "Aidence",
    "Arrow County Supplies",
    "Baywater Healthcare UK Ltd",
    "Blink Medical Limited",
    "DePuy Synthes (J&J MedTech)",
    "Eckert & Ziegler BEBIG",
    "Freedom Neuro BV",
    "Globus Medical (NuVasive UK)",
    "Globus Medical UK Ltd",
    "Grosvenor Contracts London Ltd",
    "H & R Healthcare Ltd",
    "Iskus Health UK Limited",
    "Kimberly Clark",
    "Lima Orthopaedics UK Ltd",
    "Nagor Limited",
    "NuVasive UK Ltd",
    "Ovidius Medical Ltd",
    "Ovidius Solutions Ltd",
}

# Settled elsewhere on 18/11/2026; this script must not alter them.
LEAVE_ALONE = ("Clinisupplies", "Clinisupplies GB Limited")


def dump(doc):
    """Byte-identical to the committed formatting: indent 1, no ASCII
    escaping, no trailing newline. Proved by round-trip before any write."""
    return json.dumps(doc, indent=1, ensure_ascii=False)


def main():
    dry = "--dry-run" in sys.argv

    raw = SEED.read_text(encoding="utf-8")
    doc = json.loads(raw)

    # GUARD 1 — the formatting contract. If a round-trip of the untouched
    # file is not byte-identical, this script would reformat ~133k lines and
    # bury the change, so it stops instead.
    assert dump(doc) == raw, (
        "round-trip is not byte-identical to data/supplier-seed.json; "
        "the formatting contract has changed and this script must not write"
    )

    recs = doc["suppliers"]
    assert isinstance(recs, list), "suppliers is not a list"
    before_count = len(recs)
    by_name = {}
    for r in recs:
        if isinstance(r, dict) and r.get("name"):
            by_name.setdefault(r["name"], r)

    frozen = {n: json.dumps(by_name[n], ensure_ascii=False, sort_keys=True)
              for n in LEAVE_ALONE if n in by_name}

    # Derive the target set by rule, then prove it is the set we audited.
    targets = sorted(
        r["name"] for r in recs
        if isinstance(r, dict)
        and isinstance(r.get("ownership"), str)
        and r["ownership"].strip()
        and not (r.get("deepDive") or {}).get("ownership")
    )

    # GUARD 2 — the set is the one that was read record by record. A new
    # record with the same defect is a new editorial decision, not this one.
    unexpected = set(targets) - EXPECTED
    assert not unexpected, (
        "records now match the rule that were not audited on 18/11/2026: %s. "
        "Read each one before publishing it." % sorted(unexpected)
    )
    missing = EXPECTED - set(targets)

    # Counted before anything is mutated, or the 19 would count themselves.
    already = sum(
        1 for r in recs if isinstance(r, dict)
        and isinstance(r.get("ownership"), str) and r["ownership"].strip()
        and (r.get("deepDive") or {}).get("ownership"))

    changed = []
    for name in targets:
        r = by_name[name]
        note = r["ownership"]

        # GUARD 3 — never touch a record that already renders.
        assert not (r.get("deepDive") or {}).get("ownership"), name

        dd = r.get("deepDive")
        if dd is None:
            dd = {}
            r["deepDive"] = dd
        assert isinstance(dd, dict), "deepDive is not an object on %s" % name

        dd["ownership"] = [note]

        # GUARD 4 — the prose is copied, not rewritten, and the top-level
        # key and its date stay put for refresh_supplier_careers.py.
        assert r["deepDive"]["ownership"] == [note], name
        assert r["ownership"] == note, name
        assert r["deepDive"]["ownership"][0] is note or \
            r["deepDive"]["ownership"][0] == note, name
        changed.append((name, len(note), r.get("ownershipCheckedOn")))

    # GUARD 5 — nothing else moved.
    assert len(doc["suppliers"]) == before_count, "record count changed"
    for n, fp in frozen.items():
        assert json.dumps(by_name[n], ensure_ascii=False, sort_keys=True) == fp, \
            "%s was altered; it was settled on 18/11/2026" % n

    out = dump(doc)

    print("already rendering, left alone : %d" % already)
    print("published by this run         : %d" % len(changed))
    if missing:
        print("already done on a previous run: %d" % len(missing))
    for name, n, on in sorted(changed):
        print("  %-34s %5d chars  checkedOn %s" % (name, n, on))

    if not changed:
        print("nothing to do.")
        return

    if dry:
        print("\n--dry-run: nothing written.")
        return

    SEED.write_text(out, encoding="utf-8")
    print("\nwrote data/supplier-seed.json")


if __name__ == "__main__":
    main()
