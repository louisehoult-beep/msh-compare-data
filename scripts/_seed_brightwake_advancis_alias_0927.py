"""One-off: add "Brightwake Limited (trading as Advancis Medical)" as an alias
on the existing "Advancis Medical (Brightwake)" supplier record.

Advanced Wound Care coverage batch, 27/09/2026. NHS Supply Chain's own
Advanced Wound Care contract launch brief names the awarded supplier as
"Brightwake Limited (trading as Advancis Medical)", which does not match any
alias already recorded and so sits in the ledger as an unresolved name.

This is not a fuzzy match: the Hub's own "Advancis Medical (Brightwake)"
record already carries, in its `background` field, entity identification
confirmed against Companies House 01356034 (BRIGHTWAKE LIMITED) as the legal
entity trading as Advancis Medical (added during the 06/08/2026 supplier-
directory merge). The framework award name is just that same fact stated the
other way around (legal name first, trading name second). Evidence is
"seed:Advancis Medical (Brightwake)" per alias-overlay.json's rule that this
counts as evidence when the fact is already recorded in supplier-seed.json.

Run once, then delete.
"""
import json

from seed_format import write_like, describe

PATH = "data/supplier-seed.json"
CANONICAL = "Advancis Medical (Brightwake)"
NEW_ALIAS = "Brightwake Limited (trading as Advancis Medical)"


def main():
    with open(PATH, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    suppliers = doc["suppliers"]
    hit = [s for s in suppliers if s.get("name") == CANONICAL]
    if not hit:
        raise SystemExit("supplier not found: %s" % CANONICAL)
    sup = hit[0]
    aliases = sup.setdefault("aliases", [])
    if NEW_ALIAS in aliases:
        print("alias already present, nothing to do")
        return
    aliases.append(NEW_ALIAS)
    fmt, round_trips = write_like(PATH, doc)
    print(describe(PATH, fmt, round_trips))


if __name__ == "__main__":
    main()
