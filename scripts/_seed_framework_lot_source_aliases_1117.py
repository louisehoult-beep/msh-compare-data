"""One-off: source-notice supplier spellings recorded as aliases, so the lots the
notice publishes attach to the brief's own supplier name (17/11/2026).

WHY. The publish gate warned that 47 frameworks publish lots under supplier
names no Hub supplier resolves to, so those suppliers showed "lot not confirmed"
on a lot the source does name them on. The fix the gate asks for is an alias on
the right record, never a looser match (verify.py check_framework_lots).

Each alias below is one judgement that the source spelling and the brief's own
supplier name are the SAME legal entity. Companies House was searched for each
on 17/11/2026 (find-and-update.company-information.service.gov.uk), or the
brief's own supplier list states the rename. Names that could not be settled
that way were left unresolved — see the companion note in the session folder.

NOT added, and why (so nobody "fixes" these by loosening the rule):
  Marshall Airway Products Limited   CH 07959494, a different company from the
      brief's Marshall Products Limited CH 08738168 (same address, separate
      registrations; 08738168 dissolved 09/06/2026).
  3M United Kingdom PLC / ...Public Limited Company  3M's UK entity is not
      KCI Medical Ltd / Solventum; aliasing it would make a false identity
      claim everywhere else in the Hub.
  BHF Shops Limited                  the charity's trading subsidiary, not the
      brief's British Heart Foundation.
  Babease Foods Limited CH 12320133  a different registration from the seed's
      Babease Limited CH 07473497 (dissolved 01/11/2023).
  MDI Medical (N.I.) Limited NI023111 vs the seed's "MDI Medical Ltd" — two MDI
      Medical registrations exist (NI023111 and OE032148), so which one the seed
      record is cannot be settled from the name.
  Martek Healthcare                  no such registration found; "Martek
      Lifecare" could not be confirmed as the same entity.
  Uniphar Medtech / T.J Smith & Nephew / Aquilant Endoscopy / Simulation Man and
      the like already resolve to a Hub record of their own that is not the
      brief's — a duplicate-record question, not an alias one.

The script refuses an alias whose normalised form already reaches a different
Hub company. Idempotent. Mirrors each alias into supplier-index.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"

ALIASES = [
    # (seed record, source spelling, evidence read 17/11/2026)
    ("Philips", "Philips Electronic Limited",
     "Angiography supplier matrix spelling; no 'Philips Electronic Limited' registration exists, "
     "and the brief names one Philips, 'Philips Electronics UK Limited'"),
    ("United Imaging Health Ltd", "United Imaging Limited",
     "Angiography matrix spelling of the brief's one United Imaging; CH holds UNITED IMAGING "
     "HEALTHCARE UK LTD 11327810 and ...GB LIMITED 17236952, neither spelt as either name"),
    ("Cosium Healthcare", "Cosium UK Limited",
     "CH 11159879 COSIUM UK LIMITED is the only Cosium registration; the brief names it "
     "'Cosium Healthcare'"),
    ("Vernacare", "Frontier Plastics Ltd",
     "the brief's own supplier name states it: 'Vernacare International Limited (previously "
     "Frontier Plastics Limited)'"),
    ("Inpress Precision Limited", "Inpress Plastics",
     "CH 03556496 INPRESS PRECISION LTD, previous name INPRESS PLASTICS LIMITED — one registration"),
    ("Orn Health", "ORN (Int) Limited T/A ORN Health",
     "the matrix spelling states the trading name the brief uses, 'Orn Health'"),
    ("SRA Developments", "SRA Developments Lee Roach",
     "award spelling of the brief's 'SRA Developments Limited' with a contact name appended"),
    ("IGEA S.p.A. Branch UK", "IGEA S.P.A",
     "CH BR014963 IGEA S.P.A is the UK establishment of FC029969 IGEA S.P.A — the same legal "
     "entity the brief names as 'IGEA S.p.A. Branch UK'"),
    ("Airbon Ltd, trading as Smart Air UK", "Airbon Ltd T/A Smart Air UK",
     "the brief's own name with 'trading as' written T/A"),
    ("Bioguard Hygiene Solutions", "Bioguard Hygeine Solutions Ltd",
     "award typo ('Hygeine') of the brief's 'Bioguard Hygiene Solutions'"),
    ("Genmed", "Genmed.Me Ltd",
     "CH 06045647 GENMED.ME LIMITED, Genmed House, Cwmbran — the Genmed the Angiography matrix "
     "calls 'GenMed' and the Laboratory Diagnostics brief calls 'Genmed Ltd'. Distinct from the "
     "seed's Genmed Enterprises Ltd (CH 12992754, Cardiff)"),
    ("QuidelOrtho (Ortho Clinical Diagnostics UK)", "Ortho Clinical Diagnostics",
     "award spelling of the brief's 'Ortho Clinical Diagnostics/Quidel'"),
    ("Revvity (formerly PerkinElmer)", "PerkinElmer LAS (UK) Limited",
     "the brief's own supplier name states it: 'Revvity formerly PerkinElmer LAS (UK) Limited'"),
    ("Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)", "Kinetec Medical Products UK Ltd",
     "the brief's own supplier name states the rename"),
    ("Lisclare", "Liscare Limited",
     "award spelling; no 'Liscare' registration exists and CH NI031180 LISCLARE LIMITED is the "
     "brief's own supplier"),
    ("Beaver Visitec International Sales Ltd", "Beaver-Vistec",
     "Surgical Instruments matrix shorthand for Beaver-Visitec; the brief names one BVI entity, "
     "CH 07289364 BEAVER-VISITEC INTERNATIONAL SALES LIMITED"),
    ("Pajunk UK Medical Products Limited", "PAJUNK U.K. MEDICAL PRODUCTS LIMITED",
     "the brief's own name, punctuated"),
    ("Marsden Weighing Machine Co Ltd", "Marsden Weighing Group Ltd",
     "CH 01014815 MARSDEN WEIGHING MACHINE GROUP LIMITED, already an alias on this record"),
    ("Schuco International (London) Ltd", "Schuco International",
     "CH 00592183 SCHUCO INTERNATIONAL (LONDON) LIMITED is the trading Schuco; the award drops "
     "'(London)'"),
    ("C&P Medical Trading Ltd", "C&P Medical",
     "CH 03613589 C & P MEDICAL TRADING LIMITED is the brief's own supplier"),
    ("Flexicare Medical", "Flexicare UK Ltd",
     "CH 02428573 FLEXICARE MEDICAL LIMITED (Flexicare (Group) Limited, Mountain Ash) is the one "
     "Flexicare on the brief; no 'Flexicare UK Ltd' registration exists"),
    ("Consolor Ltd", "Consolar Limited",
     "matrix spelling; no 'Consolar' registration exists and CH 05811150 CONSOLOR LIMITED is the "
     "brief's own supplier"),
    ("FormAL Group Ltd", "Formal AL Group",
     "matrix spelling of the brief's 'FormAL Group Ltd'"),
]


def add(path, check_index):
    with open(path, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    by = {s.get("name"): s for s in doc["suppliers"]}
    idx = company_match.build_index(doc)
    added = 0
    for rec, alias, _why in ALIASES:
        sup = by.get(rec)
        if sup is None:
            raise SystemExit("%s: supplier not found: %s" % (path, rec))
        aliases = sup.setdefault("aliases", [])
        if alias in aliases:
            continue
        if check_index:
            others = ((idx.get(company_match.key(alias)) or set())
                      | (idx.exact.get(company_match.norm(alias)) or set()))
            if others - {rec}:
                raise SystemExit("alias %r already reaches %s" % (alias, sorted(others - {rec})))
        aliases.append(alias)
        added += 1
    if added:
        fmt, round_trips = write_like(path, doc)
        print(describe(path, fmt, round_trips))
    print("%s: added %d aliases" % (path, added))


def main():
    add(SEED, True)
    add(INDEX, False)


if __name__ == "__main__":
    main()
