#!/usr/bin/env python3
"""
stamp_notice.py — put the ownership notice, and this repo's data marker, inside
every data file.

WHY THIS EXISTS
---------------
These files are served straight to the Hub from a PUBLIC repository. The Hub's
page watermark rides on WordPress rendering, so it never touches them, and the
paywall never touches them either: anyone can fetch data/products.json without
logging in and without agreeing to anything.

That leaves two holes this closes.

1. NOTICE. A copy taken today carries nothing saying who owns it. Whoever takes
   it can say, truthfully, that they found an unmarked file on the internet.
   Marking it does not stop anybody, but it removes that defence, and taking a
   clearly marked work is what attracts additional damages under s.97(2) of the
   Copyright, Designs and Patents Act 1988.

2. MARKER. Each file carries a "ref" that is unique to it and is not derived
   from anything in the file. It is a one-way hash of the private salt and the
   filename, the same scheme as the Hub's page watermark, so a ref found in the
   wild decodes back to the file it came from and cannot be forged.

   THE SALT IS NOT IN THIS FILE AND MUST NEVER BE. The refs below are hash
   OUTPUTS, which give nothing away. The salt lives OUTSIDE the synced workspace,
   in ~/.eth-marker-salt (chmod 600), or in $ETH_MARKER_SALT — and in the
   password manager. It was moved there on 06/08/2026: it had been a literal in
   three files inside OneDrive, so any session that read one of them disclosed
   it. Mint a new ref with "NDA Pack/decode-marker.py", which now reads it from
   the same two places.

The notice is deliberately STABLE: no date, no run number, nothing that changes
between runs. Stamping a fresh timestamp would touch all thirteen files every
day and bury the real diffs. The dated evidence trail is the snapshot's job, not
this one's.

USAGE
    python3 scripts/stamp_notice.py            # stamp, report what changed
    python3 scripts/stamp_notice.py --check    # exit 1 if anything is unstamped

Run it AFTER any refresh script and BEFORE verify.py. build_supplier_index.py
builds its output from scratch, so it drops the notice every run; the workflows
re-stamp rather than each generator having to remember.
"""
import json
import pathlib
import sys

DATA = pathlib.Path("data")

TERMS = "https://medsalesintelligencehub.co.uk/terms/"

# Hash outputs, safe to publish. See the module docstring on the salt.
REFS = {
    "awareness-days.json":              "ETH-D230F035D",
    "open-tenders.json":        "ETH-DCEFAF9C5",
    "company-awards.json":     "ETH-D8F9201A9",
    "company-press.json":      "ETH-D5A18D6E2",
    "company-logos.json":      "ETH-D6F85FA5F",
    "company-financials.json": "ETH-DCC5A9B31",
    "compare-issues.json":     "ETH-D6991A2E7",
    "compare-suppliers.json":  "ETH-D21869855",
    "contacts-optout.json":    "ETH-D12682420",
    "differentiator-category-map.json": "ETH-D01E00B2A",
    "differentiator.json":          "ETH-D29A49944",
    "frameworks.json":         "ETH-DB4D6B772",
    "hub-calendar.json":                "ETH-DB8887BA0",
    "hub-search-index.json":   "ETH-D50A4C4E3",
    "interview-prep.json":     "ETH-D77050906",
    "nhssc-cache.json":        "ETH-D84BDB325",
    "pending-awards.json":     "ETH-D8245EB13",
    "people-moves.json":       "ETH-D4435AEAF",
    "prep-config.json":        "ETH-D459CF4F3",
    "products.json":           "ETH-D34736E9E",
    "speciality-label-map.json":        "ETH-DF33A4F04",
    "speciality-map.json":     "ETH-DF6043FFA",
    "supplier-index.json":     "ETH-D773506D0",
    "supplier-product-detail.json": "ETH-D2C42E102",
    "supplier-products.json":  "ETH-D12B91CCA",
    "supplier-seed.json":      "ETH-DBE24A96B",
    "suppressed-notices.json": "ETH-DB591E91D",
    "trust-contacts.json":     "ETH-D38ACEED2",
    "trust-map.json":          "ETH-D5BBB9C7A",
    "trust-pressures.json":    "ETH-DAE43C750",
}


def notice_for(filename):
    """The block stamped into one file. Key order is fixed so diffs stay quiet."""
    return {
        "owner": "Elevate and Thrive Ltd, company number 17154474, England and Wales",
        "copyright": "© Elevate and Thrive Ltd 2026. All rights reserved.",
        "databaseRight": (
            "Database right asserted. Elevate and Thrive Ltd has made, and continues to make, "
            "substantial investment in obtaining, verifying and presenting these records."
        ),
        "published": (
            "Published solely to serve the Medical Sales Intelligence Hub. Public accessibility "
            "of this file is a technical consequence of how the Hub loads it and is not a licence "
            "to use it."
        ),
        "prohibited": (
            "Extraction or re-utilisation of all or a substantial part of this dataset; repeated or "
            "systematic extraction of insubstantial parts; redistribution, resale or syndication; "
            "use as training, fine-tuning, evaluation or retrieval data for any AI or machine-learning "
            "system; and use to design, build, populate, benchmark, launch, operate or improve any "
            "competing product or service."
        ),
        "terms": TERMS,
        "traceability": (
            "This file carries identifying characteristics that establish the origin of any copy. "
            "They must not be detected, altered, stripped or defeated."
        ),
        "ref": REFS[filename],
        "contact": "contact@elevateandthrive.uk",
    }


# Every writer in this repo has its own JSON style: most use indent=1, but
# nhssc-cache.json and supplier-seed.json are single-line and use different
# separators again. Re-dumping in one house style would reformat those two
# wholesale — 54,000 changed lines on the first run, with the real change buried
# inside it. So the original style is worked out per file and reused, and the
# diff stays at the notice block.
STYLES = (
    {"indent": 1, "ensure_ascii": False},
    {"indent": 1, "ensure_ascii": True},
    {"indent": 2, "ensure_ascii": False},
    {"indent": 2, "ensure_ascii": True},
    {"separators": (", ", ": "), "ensure_ascii": True},
    {"separators": (", ", ": "), "ensure_ascii": False},
    {"separators": (",", ":"), "ensure_ascii": True},
    {"separators": (",", ":"), "ensure_ascii": False},
)


def detect_style(original_text, doc):
    """The dump settings that reproduce this file byte for byte, or None."""
    stripped = original_text.rstrip("\n")
    for style in STYLES:
        try:
            if json.dumps(doc, **style) == stripped:
                return style, original_text.endswith("\n")
        except (TypeError, ValueError):
            continue
    return None, original_text.endswith("\n")


def main():
    check_only = "--check" in sys.argv
    if not DATA.is_dir():
        sys.exit("data/ not found. Run this from the repository root.")

    changed, missing, skipped = [], [], []

    for path in sorted(DATA.glob("*.json")):
        if path.name not in REFS:
            # A new data file. It needs a ref minted from the salt in the private
            # pack, so fail loudly rather than stamping it with nothing.
            skipped.append(path.name)
            continue

        original = path.read_text(encoding="utf-8")
        try:
            doc = json.loads(original)
        except json.JSONDecodeError as exc:
            sys.exit("%s is not valid JSON (%s). Fix that before stamping." % (path, exc))

        if not isinstance(doc, dict):
            # Every file in this repo is a JSON object today. A top-level array
            # has nowhere to hold a notice, so say so instead of failing silently.
            skipped.append(path.name + " (top-level array, cannot hold a notice)")
            continue

        wanted = notice_for(path.name)
        if doc.get("_notice") == wanted:
            continue

        if check_only:
            missing.append(path.name)
            continue

        style, trailing_newline = detect_style(original, doc)
        if style is None:
            # Unknown style. Reformatting would bury the notice in a whole-file
            # diff, so refuse and let a human decide rather than doing it anyway.
            skipped.append(path.name + " (unrecognised JSON formatting, not rewritten)")
            continue

        # Rebuild with _notice first so it is the first thing anyone opening the
        # file sees, rather than buried under a megabyte of records.
        rest = {k: v for k, v in doc.items() if k != "_notice"}
        merged = {"_notice": wanted}
        merged.update(rest)
        text = json.dumps(merged, **style)
        path.write_text(text + ("\n" if trailing_newline else ""), encoding="utf-8")
        changed.append(path.name)

    if skipped:
        print("NOT STAMPED, needs a ref minting from the private salt:")
        for name in skipped:
            print("  - %s" % name)

    if check_only:
        if missing:
            print("UNSTAMPED (%d):" % len(missing))
            for name in missing:
                print("  - %s" % name)
            return 1
        if skipped:
            return 1
        print("All %d data files carry the current notice." % len(REFS))
        return 0

    print("stamped %d, already current %d" % (len(changed), len(REFS) - len(changed) - len(skipped)))
    for name in changed:
        print("  + %s" % name)
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
