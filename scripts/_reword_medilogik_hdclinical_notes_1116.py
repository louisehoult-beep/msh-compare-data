#!/usr/bin/env python3
r"""
_reword_medilogik_hdclinical_notes_1116.py — 16/11/2026

company-report.js suppresses any supplier `note` naming an internal file
(the INTERNAL_TEXT guard, a filename regex)|md|py|toml)\b`). That guard is
correct and stays. But it means the Medilogik and HD Clinical report pages
render NO background prose at all, because both notes end a sentence with
"see supplier-products.json" — a curator's cross-reference, not member copy.

Both are endoscopy-reporting companies Lou may open on a screen-share today.
This rewords the cross-reference out of the member-facing prose and preserves
it verbatim in `_curatorNotes`, which nothing renders. No fact is changed,
added or removed: only the pointer to a file a member cannot open.

58 other suppliers are suppressed for the same single reason and are left for
a reviewed batch.

Usage:  python3 scripts/_reword_medilogik_hdclinical_notes_1116.py
Writes: data/supplier-seed.json
"""
import json, re

PATH = "data/supplier-seed.json"
GUARD = re.compile(r"\b[\w\-/]+\.(?:json|md|py|toml)\b")

EDITS = {
    "Medilogik": (
        " (see supplier-products.json)",
        "",
    ),
    "HD Clinical Ltd": (
        ", see supplier-products.json.",
        ".",
    ),
}

def main():
    doc = json.load(open(PATH))
    changed = []
    for s in doc["suppliers"]:
        edit = EDITS.get(s.get("name"))
        if not edit:
            continue
        old = s.get("note") or ""
        find, repl = edit
        if find not in old:
            raise SystemExit("expected wording not found in %s's note: %r" % (s["name"], find))
        new = old.replace(find, repl)
        if GUARD.search(new):
            raise SystemExit("%s still names an internal file after rewording" % s["name"])
        s["note"] = new
        prior = s.get("_curatorNotes")
        s["_curatorNotes"] = ((prior + " | ") if prior else "") + (
            "16/11/2026: the member note previously read %r. The internal "
            "cross-reference was reworded out so the note renders; the product "
            "range remains recorded in supplier-products.json." % find.strip(" ,.")
        )
        changed.append(s["name"])
    if sorted(changed) != sorted(EDITS):
        raise SystemExit("not every company was found: %s" % changed)
    with open(PATH, "w") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
    print("reworded:", ", ".join(changed))

if __name__ == "__main__":
    main()
