#!/usr/bin/env python3
"""State the Clinisupplies group relationship on both Clinisupplies records.

Lou's decision, 18/11/2026: "Two records + link".
------------------------------------------------
Keep BOTH Hub records and publish the common ownership as an explicit, sourced
fact on each. Do not merge. The two options she turned down were merging into
one record (which would assert one legal person where the register has two,
and contradict Find a Tender notice 032330-2023) and leaving the split with no
group link at all (which left a member who asks "are these the same company?"
with nothing but two similar names).

What was open, and what closes it
---------------------------------
scripts/_add_clinisupplies_gb_record_1118.py gave 02503030 its own record on
18/11/2026 and was right to refuse the shared Watford address as evidence of
anything. What neither that script nor fd12566 looked at is the PSC register,
and that is what settles the question: the two registrations are controlled,
75% or more at every link, through one group up to one ultimate owner.

  KKR & Co. Inc. (Delaware 6284582)
   +- CLINISUPPLIES GROUP LIMITED (14506446, named CURA BIDCO 1 LIMITED until
      20 December 2024)
       +- CLINISUPPLIES LIMITED (04013240) - PSC notified 13 January 2023,
       |  ownership of shares 75% or more
       +- GREAT BEAR HEALTHCARE GROUP LIMITED (12570444, 1 Lambourne Crescent,
          Cardiff Business Park, Cardiff CF14 5GF)  - PSC notified 11 July
          2023, 75% or more
           +- CLINISUPPLIES GB LIMITED (02503030) - PSC notified 8 December
              2020, 75% or more

Read from /persons-with-significant-control on each of 04013240, 02503030,
12570444 and 14506446, all on 2026-11-18.

The dates cohere: KKR's vehicle took Clinisupplies in January 2023 and the
Great Bear group in July 2023, and the subsidiary was renamed Great Bear
Healthcare Ltd -> Clinisupplies GB Limited in July 2024, a year after being
bought. That is a group tidying a name, not a company changing hands - and it
is also what explains the shared Watford address.

So: one business, two live registrations. That is a group link, NOT a merge.

What this script deliberately does NOT do
-----------------------------------------
- It does not promote 02503030 from companyNumberCandidate to companyNumber.
  Notice 032330-2023 publishes no registration number for any party, and the
  repo's standing rule needs scripts/confirm_company_numbers.py.
- It does not cross the aliases. Each record keeps its own spellings; the
  verbatim tiers in company_match.resolve() and app/company-report.js exist to
  keep the two cards apart and the group link must not undo them.
- It does not touch the NHS Supply Chain capture. The Urology and Bowel
  Management brief genuinely prints 57 suppliers naming both rows.
- It does not union the lots. 04013240 keeps 1, 2, 3, 5, 10 and 02503030 keeps
  1, 2, 3, 5, 13. Notice 032330-2023 awards them as two separate parties,
  GB-FTS-96951 and GB-FTS-96957, and that separation is the reason the records
  stay apart.
- It adds no award and removes none.

Where the fact goes
-------------------
deepDive.ownership, because app/company-report.js renders that array as the
"Structure & ownership" section, so a member reading either card sees it. The
GB record had no deepDive at all, so it gets a minimal one carrying only this.
Every other block in composeSections() guards on its own key, so a partial
deepDive renders just this section and nothing else.

The stale entity caution on 04013240 is replaced at the same time. It told the
reader that "at least one framework in this record may sit with the sibling
entity" and asked for it to be "checked brief by brief". That check has now
been done and the lots are settled on both records, so leaving the caution up
would show members an open question that is closed.

Idempotent: re-running changes nothing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seed_format  # noqa: E402

ROOT = os.path.dirname(HERE)
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")

PARENT = "Clinisupplies"          # CLINISUPPLIES LIMITED 04013240
GB = "Clinisupplies GB Limited"   # CLINISUPPLIES GB LIMITED 02503030

CH = "https://find-and-update.company-information.service.gov.uk/company/"

# The group link, written once per record and from the register only. Both
# paragraphs name the same four numbers and the same read date, so either card
# can be quoted on its own.
LINK_PARENT = (
    "Group link, read at Companies House on 18 November 2026. This "
    "registration and the Hub's separate \"Clinisupplies GB Limited\" record "
    "(CLINISUPPLIES GB LIMITED 02503030) are under common ultimate control. "
    "The sole active person with significant control of CLINISUPPLIES LIMITED "
    "04013240 is CLINISUPPLIES GROUP LIMITED 14506446 (named CURA BIDCO 1 "
    "LIMITED when the entry was made), notified 13 January 2023, ownership of "
    "shares 75% or more. The same CLINISUPPLIES GROUP LIMITED 14506446 is the "
    "person with significant control of GREAT BEAR HEALTHCARE GROUP LIMITED "
    "12570444, notified 11 July 2023, 75% or more, and that company in turn "
    "is the person with significant control of CLINISUPPLIES GB LIMITED "
    "02503030, notified 8 December 2020, 75% or more. The register names "
    "KKR & Co. Inc. above CLINISUPPLIES GROUP LIMITED. So the two Hub records "
    "are one business held through one group, and not two unrelated "
    "namesakes. Sources, all read 2026-11-18: the "
    "persons-with-significant-control page of each of "
    + CH + "04013240/persons-with-significant-control , "
    + CH + "02503030/persons-with-significant-control , "
    + CH + "12570444/persons-with-significant-control and "
    + CH + "14506446/persons-with-significant-control ."
)

LINK_GB = (
    "Group link, read at Companies House on 18 November 2026. This "
    "registration and the Hub's separate \"Clinisupplies\" record "
    "(CLINISUPPLIES LIMITED 04013240) are under common ultimate control. The "
    "person with significant control of CLINISUPPLIES GB LIMITED 02503030 is "
    "GREAT BEAR HEALTHCARE GROUP LIMITED 12570444, notified 8 December 2020, "
    "ownership of shares 75% or more. That company's own person with "
    "significant control is CLINISUPPLIES GROUP LIMITED 14506446, notified "
    "11 July 2023, 75% or more - and the same CLINISUPPLIES GROUP LIMITED is "
    "the person with significant control of CLINISUPPLIES LIMITED 04013240, "
    "notified 13 January 2023, 75% or more. The register names KKR & Co. Inc. "
    "above CLINISUPPLIES GROUP LIMITED. So the two Hub records are one "
    "business held through one group, and not two unrelated namesakes. "
    "Sources, all read 2026-11-18: the persons-with-significant-control page "
    "of each of "
    + CH + "02503030/persons-with-significant-control , "
    + CH + "04013240/persons-with-significant-control , "
    + CH + "12570444/persons-with-significant-control and "
    + CH + "14506446/persons-with-significant-control ."
)

# Why they still stay two records, said once on each card so neither can be
# read as a merge.
WHY_TWO_PARENT = (
    "Two records, not one, and deliberately so. Common ownership is not one "
    "legal person: CLINISUPPLIES LIMITED 04013240 and CLINISUPPLIES GB "
    "LIMITED 02503030 are both active registrations in their own right, and "
    "neither appears in the other's previous names, so this is not a "
    "renaming. Find a Tender contract award notice 032330-2023 for NHS Supply "
    "Chain's Urology and Bowel Management framework awards them as two "
    "separate supplier parties, GB-FTS-96951 and GB-FTS-96957, on different "
    "lots - 1, 2, 3, 5 and 10 to this registration, and 1, 2, 3, 5 and 13 to "
    "02503030 under its then-name Great Bear Healthcare Ltd. A buying "
    "organisation is treating them as two suppliers, so this Hub does too, "
    "and each card shows only its own lots."
)

WHY_TWO_GB = (
    "Two records, not one, and deliberately so. Common ownership is not one "
    "legal person: CLINISUPPLIES GB LIMITED 02503030 and CLINISUPPLIES "
    "LIMITED 04013240 are both active registrations in their own right, and "
    "neither appears in the other's previous names, so this is not a "
    "renaming. Find a Tender contract award notice 032330-2023 for NHS Supply "
    "Chain's Urology and Bowel Management framework awards them as two "
    "separate supplier parties, GB-FTS-96957 and GB-FTS-96951, on different "
    "lots - 1, 2, 3, 5 and 13 to this registration under its then-name Great "
    "Bear Healthcare Ltd, and 1, 2, 3, 5 and 10 to 04013240. A buying "
    "organisation is treating them as two suppliers, so this Hub does too, "
    "and each card shows only its own lots."
)

# The GB record has no deepDive. Give it one carrying only what is sourced.
GB_DEEPDIVE = {
    "checked": "2026-11-18",
    "origin": (
        "Written by scripts/_add_clinisupplies_group_link_1118.py on "
        "18/11/2026, on Lou's decision to keep two Clinisupplies records and "
        "publish the group relationship on each. Built from Companies House "
        "only: the company record and the persons-with-significant-control "
        "page of 02503030, 04013240, 12570444 and 14506446, all read "
        "2026-11-18. No financial or trading claim is made here - this record "
        "carries no filed-accounts capture of its own."
    ),
    "ownership": [LINK_GB, WHY_TWO_GB],
}

# The paragraph on 04013240 that this script retires. Matched on a distinctive
# fragment so a reworded original fails loudly rather than being guessed at.
STALE_MARK = "Entity caution."
STALE_TAIL = "no framework is reassigned on the strength of a name."

RESOLVED = (
    "Entity resolved, 18/11/2026. NHS Supply Chain's briefs behind this "
    "record name the supplier both as \"Clinisupplies Limited\" and as "
    "\"Clinisupplies GB Limited\". Those are two distinct registrations, "
    "04013240 and 02503030, and this record is 04013240. That was once an "
    "open caution here; it is now closed. 02503030 has its own Hub record, "
    "\"Clinisupplies GB Limited\", and the lots have been read brief by brief "
    "off Find a Tender notice 032330-2023 and attached to the registration "
    "each was awarded to: 1, 2, 3, 5 and 10 here, 1, 2, 3, 5 and 13 there. No "
    "framework was reassigned on the strength of a name, and none is shared "
    "between the two cards. A bare \"Clinisupplies\" spelling resolves as "
    "ambiguous by design, because on the names alone it genuinely is."
)


def paragraphs_for(name):
    if name == PARENT:
        return [LINK_PARENT, WHY_TWO_PARENT]
    return [LINK_GB, WHY_TWO_GB]


def patch(path):
    doc = json.load(open(path, encoding="utf-8"))
    rows = doc["suppliers"]
    by_name = {s.get("name"): s for s in rows}
    changed = []

    for name in (PARENT, GB):
        if name not in by_name:
            raise SystemExit(
                "%s: expected a record named %r and there is none. Refusing "
                "to create one - this script only adds the group link to the "
                "two records that already exist."
                % (os.path.basename(path), name)
            )

    # --- the GB record: a minimal deepDive, or the link appended to its own ---
    gb = by_name[GB]
    dd = gb.get("deepDive")
    if not isinstance(dd, dict):
        gb["deepDive"] = json.loads(json.dumps(GB_DEEPDIVE))
        changed.append("%s: added deepDive carrying the group link" % GB)
    else:
        own = dd.setdefault("ownership", [])
        for para in paragraphs_for(GB):
            if para not in own:
                own.append(para)
                changed.append("%s: appended an ownership paragraph" % GB)

    # --- 04013240: append the link, and retire the stale caution ------------
    parent = by_name[PARENT]
    pdd = parent.get("deepDive")
    if not isinstance(pdd, dict):
        raise SystemExit(
            "%s: %r has no deepDive and this script was written against the "
            "one it had; refusing to guess." % (os.path.basename(path), PARENT)
        )
    own = pdd.setdefault("ownership", [])

    stale = [i for i, p in enumerate(own)
             if STALE_MARK in p and p.rstrip().endswith(STALE_TAIL)]
    if stale:
        for i in stale:
            own[i] = RESOLVED
        changed.append("%s: retired the entity caution, now resolved" % PARENT)
    elif RESOLVED not in own:
        raise SystemExit(
            "%s: the entity-caution paragraph on %r is not the one this "
            "script was written against, and the resolved text is not there "
            "either; refusing to guess." % (os.path.basename(path), PARENT)
        )

    for para in paragraphs_for(PARENT):
        if para not in own:
            own.append(para)
            changed.append("%s: appended an ownership paragraph" % PARENT)

    # --- nothing else may move ---------------------------------------------
    assert GB not in [a for a in (parent.get("aliases") or [])], \
        "the GB name must never become an alias of %s" % PARENT
    assert PARENT not in [a for a in (gb.get("aliases") or [])][1:], \
        "the parent name must never become a bare alias of %s" % GB
    assert "companyNumber" not in gb, \
        "02503030 must stay a candidate until confirm_company_numbers.py proves it"

    if not changed:
        print("%s: already as intended" % os.path.basename(path))
        return
    fmt, round_trips = seed_format.write_like(path, doc)
    seed_format.describe(os.path.basename(path), fmt, round_trips)
    for c in changed:
        print("  %s" % c)


for p in (SEED, INDEX):
    patch(p)
