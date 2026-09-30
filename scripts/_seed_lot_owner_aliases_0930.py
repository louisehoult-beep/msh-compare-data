"""One-off: record NHS Supply Chain / Find a Tender owner spellings as aliases,
so framework lots attach to the brief's supplier (30/09/2026).

scripts/refresh_framework_lots.py lists in `unresolved` every lot-source name
the brief does not use. Each alias below was checked to be the SAME legal
entity as the seed record it is added to, by one of:

  typo   - an obvious typo / punctuation / spacing / case / legal-suffix variant
           of that record's own name or a recorded alias, and of nothing else
           in the seed
  CH     - Companies House: the alias is the registered name, or a recorded
           previous name, of the company number that record is matched to
           (company-financials.json, matchConfidence noted), read 30/09/2026
           from find-and-update.company-information.service.gov.uk

Names that could be a different group company, a parent/subsidiary, a separate
registration, or that would need a seed merge are NOT here; they stay
unresolved (see the 30/09/2026 landing commit message).

The script refuses to add an alias whose normalised form already reaches a
different Hub company. Idempotent. Run once, then delete.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

PATH = "data/supplier-seed.json"

ALIASES = [
    # (seed record, alias, evidence)
    ("Richardson Healthcare", "Richardson Healthcare Limted", "typo of RICHARDSON HEALTHCARE LIMITED (04190638, the only CH match)"),
    ("Zoll Medical UK Limited", "Zoll Medcial UK Limited", "typo; CH 02823225 ZOLL MEDICAL UK LIMITED (confirmed)"),
    ("HC21 (UK) Ltd", "Heathcare 21 (UK) Limited", "typo of recorded alias Healthcare 21 (UK) Limited; CH 05020682 (confirmed)"),
    ("Henleys Medical Supplies Limited", "Henleys Medical Suppliers Limited", "typo; CH advanced search 'henleys medical' returns only 00452882 HENLEYS MEDICAL SUPPLIES LIMITED"),
    ("WSR Medical Solutions Ltd", "W S R Medical Solutions Limited", "spacing; CH 09366606 WSR MEDICAL SOLUTIONS LIMITED is the only match"),
    ("Natus Nicolet UK", "NATUS NICOLET U.K LIMTED", "typo of NATUS NICOLET U.K. LIMITED (02986787)"),
    ("2San Global", "2 San Global", "spacing; CH 12620104 2SAN GLOBAL LIMITED is the only match"),
    ("British Bins Ltd", "BritishBins Ltd", "spacing"),
    ("Mainline Instruments Ltd", "Mainline Instrument", "typo (plural dropped)"),
    ("Vision Pharmaceuticals Ltd T/A Spectrum", "Vision pharmaceuticals ltd t/as spectrum", "case and t/as for T/A"),
    ("GI UK Medical Ltd (Duomed)", "DUOMED MEDICAL UK LIMITED", "CH 12125248 DUOMED MEDICAL UK LIMITED, previous name GI UK MEDICAL LTD (a recorded alias of this record)"),
    ("Ingles Ltd", "INGLES MEDICAL LIMITED", "CH 08650170 INGLES MEDICAL LIMITED is this record's confirmed number"),
    ("Synectics Medical T/A SynMed", "SYNECTICS MEDICAL LIMITED", "legal-suffix variant of the record's own name; CH 09043744 is the only active SYNECTICS MEDICAL LIMITED"),
    ("Baxter Healthcare Ltd", "Baxter Healthcare Limited Newbury01", "the brief's depot listing of Baxter Healthcare Limited (a recorded alias; CH 00461365 confirmed)"),
    ("Talarmade Limited", "Talar-Made Limited", "CH 04575555 TALAR-MADE LIMITED is this record's confirmed number"),
    ("Uniphar Medtech UK Ltd (Cardiac Services / Synapse Medical)", "Cardiac Services (Uniphar Medtech UK Ltd T/A Cardiac Services)", "format variant of recorded alias Uniphar Medtech UK Limited T/A Cardiac Services (NI018037 confirmed)"),
    ("Fannin (UK) Limited", "Fannin UK Ltd (previously Iskus Health UK Limited)", "names FANNIN (UK) LIMITED (02663514 confirmed; recorded alias FANNIN UK LTD)"),
    ("Fannin (UK) Limited", "Fanin UK Ltd", "typo of recorded alias FANNIN UK LTD (02663514 confirmed)"),
    ("Pennine Healthcare (Ivor Shaw Ltd)", "Ivor Shaw Ltd/Pennine Healthcare", "format variant of the record's own name (IVOR SHAW LIMITED 00755641 confirmed)"),
    ("Pennine Healthcare (Ivor Shaw Ltd)", "Ivor Shaw Ltd trading as Pennine Healthcare", "format variant of the record's own name (IVOR SHAW LIMITED 00755641 confirmed)"),
    ("OscarTech UK", "OscarTeck UK Ltd", "typo of recorded alias OscarTech UK Ltd"),
    ("It’s Interventional Limited", "Its Interventional Ltd", "apostrophe dropped; CH 02144870 IT'S INTERVENTIONAL LIMITED (confirmed)"),
    ("Sela Medical UK Ltd", "Selamedical UK Limited", "CH registered name: 07416808 SELAMEDICAL UK LIMITED; no 'Sela Medical' registration exists"),
    ("PCByVoice", "PCBy Voice", "spacing; CH 07251002 PCBYVOICE LTD is the only match"),
    ("United Orthopaedic Corporation UK Limited", "United Orthopedic Corporation UK Limite", "truncation; CH 11530585 UNITED ORTHOPEDIC CORPORATION (UK), LTD. is the only match"),
    ("NISSHA Medical Technologies", "NISSHA MEDICAL TECHNIOLOGIES LTD", "typo of NISSHA MEDICAL TECHNOLOGIES LTD (05999241, the only match)"),
    ("J Heinz Foods UK Limited", "H.J. HEINZ FOODS UK LIMITED", "CH 08322668 H.J. HEINZ FOODS UK LIMITED is this record's confirmed number"),
    ("Aayan Medical Imaging Limited", "Aayan Medical Imaging Limted", "typo; CH 06547415 AAYAN MEDICAL IMAGING LIMITED is the only match"),
    ("Blatchford Limited", "Blatchford Limted", "typo of the record's own name"),
    ("Etac Ltd", "Etac Lmited", "typo; CH 03936516 ETAC LIMITED (confirmed)"),
]


def main():
    with open(PATH, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    by = {s.get("name"): s for s in doc["suppliers"]}
    idx = company_match.build_index(doc)
    added = 0
    for rec, alias, _why in ALIASES:
        if "gbuk" in rec.lower():
            raise SystemExit("refusing to touch GBUK")
        sup = by.get(rec)
        if sup is None:
            raise SystemExit("supplier not found: %s" % rec)
        aliases = sup.setdefault("aliases", [])
        if alias in aliases:
            continue
        others = (idx.get(company_match.key(alias)) or set()) | (idx.exact.get(company_match.norm(alias)) or set())
        if others - {rec}:
            raise SystemExit("alias %r already reaches %s" % (alias, sorted(others - {rec})))
        aliases.append(alias)
        added += 1
    if not added:
        print("all aliases already present, nothing to do")
        return
    fmt, round_trips = write_like(PATH, doc)
    print("added %d aliases" % added)
    print(describe(PATH, fmt, round_trips))


if __name__ == "__main__":
    main()
