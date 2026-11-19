"""One-off: stop "Uniphar Medtech UK Limited" resolving to the wrong Hub record
(17/11/2026).

WHY. NI018037's Companies House registered name is UNIPHAR MEDTECH UK LIMITED
(read at source 17/11/2026, active). company_match normalisation strips the
territory word "UK" and the legal suffix "Limited", so that name collapses to
"uniphar medtech" — which the SEPARATE bare-brand record "Uniphar Medtech" holds
verbatim. The verbatim tier in company_match.py exists precisely to stop a
territory strip collapsing two real companies onto one key, but it can only fire
on strings the seed actually holds, and the NI018037 record held no bare
"Uniphar Medtech UK …" form: only trading-name variants ("Uniphar Medtech UK
Limited T/A Cardiac Services").

So ten award rows sat on the brand record, including four published under the
exact registered name and a Synapse MR400 award for Hull University Teaching
Hospitals — a Synapse Medical product on the record that does not own the Synapse
name.

THE FIX IS DATA, NOT THE MATCH RULE. The rule is deliberately narrow and is not
loosened here. The record that owns the registration simply gains the registered
name it already quotes in its own companyNumberNote.

THE TWO RECORDS ARE NOT MERGED. The brand record's identityNote (17/11/2026)
records that the bare name cannot be tied to one registration — Companies House
holds NI018037 and NI040976 (UNIPHAR MEDTECH HOLDINGS UK LIMITED) at the same
Belfast address, and NHS Supply Chain names the group's IRISH entity as "Uniphar
Medtech Ltd t/a M.E.D. Surgical" elsewhere. Under
data/identity-vocabulary-policy.json a shared NAME is not evidence. This change
only stops the territory-qualified UK legal name being swallowed by that
unidentified brand record.

MEASURED BEFORE WRITING: re-resolving 6,624 distinct notice supplier names, this
changes five. Two ("Uniphar Medtech UK Limited", "Uniphar Medtech UK Ltd") move
to the NI018037 record. Three with NO territory word ("Uniphar Medtech Limited",
"Uniphar Medtech LIMITED", "Uniphar Medtech Ltd.") become AMBIGUOUS and are
quarantined — correct, since those are the forms that could equally be the Irish
entity. Nothing else moves.

AFTER THIS: python3 scripts/refresh_awards.py --rematch, then bash scripts/gate.sh.
Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seed_format  # noqa: E402

SEED = "data/supplier-seed.json"
NUMBER = "NI018037"
REGISTERED = ["Uniphar Medtech UK Limited", "Uniphar Medtech UK Ltd"]
BRAND = "Uniphar Medtech"

NOTE = (
    "Checked 2026-11-17: the Companies House registered name of this record's own "
    "confirmed number NI018037 is UNIPHAR MEDTECH UK LIMITED (read at source "
    "17/11/2026, active). Both the full and the abbreviated form are recorded as "
    "aliases because company_match normalisation strips \"UK\" and \"Limited\", "
    "collapsing the registered name onto the bare brand record \"Uniphar "
    "Medtech\" and attaching this company's awards — including a Synapse MR400 "
    "award — to a record that holds no registration. The records are NOT merged: "
    "the bare name cannot be tied to one registration (NI018037 vs NI040976 "
    "UNIPHAR MEDTECH HOLDINGS UK LIMITED, and the group's Irish entity, which NHS "
    "Supply Chain names as \"Uniphar Medtech Ltd t/a M.E.D. Surgical\"). Forms "
    "with no territory word therefore quarantine as ambiguous on purpose."
)
BRAND_NOTE = (
    " Added 2026-11-17: the NI018037 record now also holds \"Uniphar Medtech UK "
    "Limited\" and \"Uniphar Medtech UK Ltd\" as aliases, so those territory-"
    "qualified legal names no longer resolve here. Forms with no territory word "
    "(\"Uniphar Medtech Ltd\") now resolve to neither record and are quarantined "
    "as ambiguous, which is the intended outcome while the bare name is tied to "
    "no registration."
)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    with open(SEED, encoding="utf-8") as f:
        seed = json.load(f)
    suppliers = seed["suppliers"] if isinstance(seed, dict) else seed

    owner = [s for s in suppliers if (s.get("companyNumber") or "") == NUMBER]
    if len(owner) != 1:
        sys.exit("expected exactly one record with companyNumber %s, found %d. "
                 "Nothing written." % (NUMBER, len(owner)))
    rec = owner[0]
    brand = [s for s in suppliers if s.get("name") == BRAND]

    changed = []
    aliases = list(rec.get("aliases") or [])
    for a in REGISTERED:
        if a not in aliases:
            aliases.append(a)
            changed.append(a)
    if changed:
        rec["aliases"] = aliases
    if NOTE not in (rec.get("identityNote") or ""):
        rec["identityNote"] = ((rec.get("identityNote") or "").rstrip() + " " + NOTE).strip()
        changed.append("identityNote on %s" % rec["name"])
    if brand and BRAND_NOTE.strip() not in (brand[0].get("identityNote") or ""):
        brand[0]["identityNote"] = ((brand[0].get("identityNote") or "").rstrip()
                                    + BRAND_NOTE).strip()
        changed.append("identityNote on %s" % BRAND)

    if not changed:
        print("nothing to do — already applied.")
        return 0
    fmt, round_trips = seed_format.write_like(SEED, seed)
    print(seed_format.describe(SEED, fmt, round_trips))
    for c in changed:
        print("  + %s" % c)
    print("\nNow: python3 scripts/refresh_awards.py --rematch && bash scripts/gate.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
