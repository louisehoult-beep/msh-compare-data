#!/usr/bin/env python3
"""
Invariant gate for the NHS Supply Chain card parser (scripts/nhssc_card.py).

The parser's failure mode is not a crash - it is a field read from the wrong
place: an MPC stored as a status, the NPC stored as the MPC, a "SUSPENDED"
badge published as a brand name, an MPC published as a product description.
Until 28/09/2026 all four were in data/nhssc-cache.json (4,813 mpc == npc rows,
73 junk statuses, 7 badge rows, 9 MPC-as-description rows) and reached the
Differentiator and the product dossiers.

The fixtures below are the extractor's real output for four live cards, read at
pilot.supplychain.nhs.uk/search?query=<NPC> on 28/09/2026 at the refresh's own
1200x900 viewport. Each check is self-tested: the old positional parser is kept
here as LEGACY and must FAIL the same check, so no check can pass vacuously.

Usage:  python3 test_nhssc_card.py
"""

from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import nhssc_card as N                                              # noqa: E402

failures: list[str] = []
checks = 0


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        failures.append(what)
    return ok


# --- Live cards (extractor output), 28/09/2026 -----------------------------------
# innerText order at 1200px, which the old parser split by position, is kept in
# `lines` so LEGACY can be run against exactly what it used to see.
ELA679 = {  # SUSPENDED badge renders above the brand; hyphenated MPC
    "brand": "Cuticell Contact", "supplier": "ESSITY UK TENA HM",
    "name": "Wound contact layer silicone dressing one sided 10cm x 18cm",
    "mpc": "72762-02", "npc": "ELA679", "npcClass": "ELA679", "badges": ["SUSPENDED"],
    "uom": "Sold in  Pack of 5",
    "img": "https://media.supplychain.nhs.uk/media/images/ELA679/large/947452_ELA679.jpg",
    "lines": ["SUSPENDED", "Cuticell Contact", "ESSITY UK TENA HM",
              "Wound contact layer silicone dressing one sided 10cm x 18cm",
              "72762-02", "ELA679", "Sold in Pack of 5"],
}
FDQ3419 = {  # no brand line at all
    "brand": "", "supplier": "DRAEGER MEDICAL",
    "name": "Facemask anaesthetic with air cushion no check valve Size 4 NON RETURNABLE",
    "mpc": "MP01514", "npc": "FDQ3419", "npcClass": "FDQ3419", "badges": [],
    "uom": "Sold in  Box of 20",
    "img": "https://media.supplychain.nhs.uk/media/images/FDQ3419/large/709314_FDQ3419.jpg",
    "lines": ["DRAEGER MEDICAL",
              "Facemask anaesthetic with air cushion no check valve Size 4 NON RETURNABLE",
              "MP01514", "FDQ3419", "Sold in Box of 20"],
}
FSQ9400 = {  # all-letter MPC
    "brand": "Statlock", "supplier": "BECTON DICKINSON UK LTD WOKING",
    "name": "Fixation device sterile For PICC opsted paediatric pad with clamp",
    "mpc": "VCDTCE", "npc": "FSQ9400", "npcClass": "FSQ9400", "badges": [],
    "uom": "Sold in  Box of 50",
    "img": "https://media.supplychain.nhs.uk/media/images/FSQ9400/large/1105019_FSQ9400.jpg",
    "lines": ["Statlock", "BECTON DICKINSON UK LTD WOKING",
              "Fixation device sterile For PICC opsted paediatric pad with clamp",
              "VCDTCE", "FSQ9400", "Sold in Box of 50"],
}
EKH112 = {  # an ordinary live card, alphanumeric MPC: must read the same as ever
    "brand": "Biatain Contact", "supplier": "COLOPLAST LIMITED",
    "name": "Wound contact layer silicone dressing one sided 10 x 18",
    "mpc": "33562", "npc": "EKH112", "npcClass": "EKH112", "badges": [],
    "uom": "Sold in  Pack of 5",
    "img": "https://media.supplychain.nhs.uk/media/images/EKH112/large/751980_EKH112.jpg",
    "lines": ["Biatain Contact", "COLOPLAST LIMITED",
              "Wound contact layer silicone dressing one sided 10 x 18",
              "33562", "EKH112", "Sold in Pack of 5"],
}

# What each card says, read by eye off the live page on 28/09/2026.
TRUTH = {
    "ELA679": {"name": "Cuticell Contact", "supplier": "ESSITY UK TENA HM",
               "desc": "Wound contact layer silicone dressing one sided 10cm x 18cm",
               "npc": "ELA679", "mpc": "72762-02", "status": "Suspended", "pack": "Pack of 5"},
    "FDQ3419": {"name": "", "supplier": "DRAEGER MEDICAL",
                "desc": "Facemask anaesthetic with air cushion no check valve Size 4 NON RETURNABLE",
                "npc": "FDQ3419", "mpc": "MP01514", "status": "", "pack": "Box of 20"},
    "FSQ9400": {"name": "Statlock", "supplier": "BECTON DICKINSON UK LTD WOKING",
                "desc": "Fixation device sterile For PICC opsted paediatric pad with clamp",
                "npc": "FSQ9400", "mpc": "VCDTCE", "status": "", "pack": "Box of 50"},
    "EKH112": {"name": "Biatain Contact", "supplier": "COLOPLAST LIMITED",
               "desc": "Wound contact layer silicone dressing one sided 10 x 18",
               "npc": "EKH112", "mpc": "33562", "status": "", "pack": "Pack of 5"},
}
CARDS = {"ELA679": ELA679, "FDQ3419": FDQ3419, "FSQ9400": FSQ9400, "EKH112": EKH112}


def LEGACY(c):
    """The pre-28/09/2026 positional parser, verbatim in logic, fed what the old
    extractor gave it: innerText lines, the NPC from the carousel class, and an
    MPC only from the phone-layout class (empty at 1200px)."""
    lines = c["lines"]
    name, supplier, desc = lines[0], lines[1], lines[2]
    npc, mpc = c["npcClass"], ""
    status = pack = ""
    codeish = []
    for ln in lines[3:]:
        if ln.startswith("Sold in"):
            pack = ln.replace("Sold in", "").strip()
        elif re.fullmatch(r"[A-Z0-9]{4,10}", ln) and not ln.isalpha():
            codeish.append(ln)
        elif re.fullmatch(r"[A-Z][A-Z ]{4,}", ln) and "SOLD" not in ln and not status and ln != supplier:
            status = ln.title()
    if not npc and len(codeish) >= 2:
        npc = codeish[1]
    if not mpc and codeish:
        mpc = codeish[0]
    if not npc and len(codeish) == 1:
        npc = codeish[0]
    return {"name": name, "supplier": supplier, "desc": desc, "npc": npc, "mpc": mpc,
            "status": status, "pack": pack, "img": c.get("img", "")}


def wrong_fields(parser, card, truth):
    got = parser(card)
    if got is None:
        return ["<no item>"]
    return [k for k, v in truth.items() if got.get(k) != v]


def test_reads_every_field_from_its_own_element():
    """Each live card parses to exactly what the page shows - and the old parser
    gets every one of the three problem cards wrong, so the check has teeth."""
    for k, card in CARDS.items():
        bad = wrong_fields(N.parse_card, card, TRUTH[k])
        check(not bad, "%s: fields read wrongly: %s" % (k, bad))
    for k in ("ELA679", "FDQ3419", "FSQ9400"):
        check(wrong_fields(LEGACY, CARDS[k], TRUTH[k]),
              "self-test: the old positional parser must misread %s" % k)
    # The ordinary card is the control: the old parser read it right, and so must
    # the new one. A fix that only works on the broken shapes is not a fix.
    check(not wrong_fields(LEGACY, EKH112, TRUTH["EKH112"]),
          "self-test: EKH112 is the control and the old parser read it correctly")


def test_no_defect_fingerprint_on_a_parsed_card():
    """row_defects() finds the old parser's fingerprints, and a card parsed now
    never carries one."""
    for k, card in CARDS.items():
        item = N.parse_card(card)
        check(item is not None and not N.row_defects(item),
              "%s: freshly parsed card carries %s" % (k, item and N.row_defects(item)))
    want = {"ELA679": {"badge-in-name", "mpc-is-npc"},
            "FDQ3419": {"single-token-desc", "mpc-is-npc"},
            "FSQ9400": {"junk-status", "mpc-is-npc"}}
    for k, expect in want.items():
        got = set(N.row_defects(LEGACY(CARDS[k])))
        check(expect <= got, "self-test: row_defects missed %s on legacy %s (got %s)"
              % (sorted(expect - got), k, sorted(got)))
    check(not N.row_defects(LEGACY(EKH112)),
          "self-test: row_defects flags a correctly read row")
    # A real status is not junk.
    check(not N.row_defects({"npc": "ELA679", "mpc": "72762-02", "name": "Cuticell Contact",
                             "desc": "Wound contact layer", "status": "Suspended"}),
          "a genuine Suspended status was flagged as junk")


def test_refuses_rather_than_guesses():
    """A card the parser cannot read for certain yields nothing. Guessing a field
    is how the four defects got into the cache."""
    old_shape = {"lines": ELA679["lines"], "npc": "ELA679", "mpc": "", "img": ""}
    check(N.parse_card(old_shape) is None,
          "a line-only card (no data-cy fields) must not be parsed by position")
    for missing in ("supplier", "name", "npc"):
        c = dict(EKH112)
        c[missing] = ""
        if missing == "npc":
            c["npcClass"] = ""
        check(N.parse_card(c) is None, "card with no %s must be refused" % missing)
    c = dict(EKH112, npc="72762-02", npcClass="")
    check(N.parse_card(c) is None, "a non-NPC-shaped code in the NPC slot must be refused")
    c = dict(EKH112, npcClass="ELA679")
    check(N.parse_card(c) is None, "two different NPCs on one card must be refused")
    # The NPC badge falls back to the carousel class when the badge is absent,
    # and a letter-suffixed NPC is still an NPC.
    c = dict(EKH112, npc="", npcClass="EKH112")
    check((N.parse_card(c) or {}).get("npc") == "EKH112", "carousel-class NPC fallback lost")
    c = dict(EKH112, npc="CFP213H", npcClass="CFP213H")
    check((N.parse_card(c) or {}).get("npc") == "CFP213H", "letter-suffixed NPC refused")


def test_extractor_reads_data_cy_not_position():
    """The browser-side extractor must read the data-cy fields, including the
    desktop productMPC element the old class selector never matched."""
    js = N.EXTRACT_JS
    for cy in ("productBrand", "productSupplier", "productName", "productMPC",
               "productNPC", "uom"):
        check('data-cy="%s"' % cy in js, "EXTRACT_JS does not read data-cy=%s" % cy)
    check("innerText" not in js, "EXTRACT_JS still splits innerText by position")


def test_both_scripts_share_this_parser():
    """The two writers of nhssc-cache.json must not carry private copies again."""
    for fn in ("refresh_nhssc_cache.py", "seed_nhssc_from_icc_npc.py"):
        src = open(os.path.join(REPO, "scripts", fn)).read()
        check("from nhssc_card import EXTRACT_JS, parse_card" in src,
              "%s does not import the shared parser" % fn)
        check("def parse_card" not in src and "EXTRACT_JS = r" not in src,
              "%s still defines its own card parser" % fn)


for fn in (test_reads_every_field_from_its_own_element,
           test_no_defect_fingerprint_on_a_parsed_card,
           test_refuses_rather_than_guesses,
           test_extractor_reads_data_cy_not_position,
           test_both_scripts_share_this_parser):
    try:
        fn()
    except Exception as exc:                                        # noqa: BLE001
        failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))

if failures:
    print("NHSSC CARD PARSER GATE FAILED (%d of %d checks)" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("nhssc card parser gate passed: %d checks" % checks)
