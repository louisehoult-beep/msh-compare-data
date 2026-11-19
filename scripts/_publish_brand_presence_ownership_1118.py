#!/usr/bin/env python3
"""
_publish_brand_presence_ownership_1118.py — the second half of the
18/11/2026 ownership-visibility job, authorised by Lou after the first.

WHAT a3389b7 DID, AND WHAT IT LEFT
----------------------------------
a3389b7 published the 19 records whose top-level `ownership` string reached
no member at all, because app/company-report.js renders "Structure &
ownership" only from deepDive.ownership (ownershipBlock(), line 2630).

It deliberately left the other 13 string-typed records alone. Each of those
already had a deepDive.ownership naming the same controlling entity, so no
member was missing the ownership fact, and appending the whole top-level
string would have restated the same PSC notification two paragraphs below
itself — on Nevro Medical Limited almost word for word.

But those 13 top-level strings were not pure duplication. They were written
from a DIFFERENT source class: the companies' own websites and press
releases, read for BRAND and TRADING-NAME status — which brand a member
actually meets, whether the company still has a website of its own, what the
product range is called now. The deepDive paragraphs beside them are
Companies-House and filed-accounts work, which does not carry any of that.
A rep asking "is there still a Diversey to sell against?" was not served.

WHAT THIS SCRIPT PUBLISHES
--------------------------
Nine of the 13, one appended paragraph each, built from the clauses of that
record's OWN top-level string with its source citation kept attached. The
clauses whose facts already appear in the record's deepDive.ownership are
left out; nothing is re-worded into new claims and no fact is added that the
string does not already carry. Nothing was re-fetched today: each paragraph
carries the read date the string itself records.

  Armstrong Medical (Eakin Respiratory)  trading brand is Eakin Respiratory,
                                         legal entity still Armstrong Medical
                                         Ltd NI025560
  Axonics Modulation Technologies UK Ltd axonics.com redirects to Boston
                                         Scientific; shared registered office
  Baxter / Hillrom                       Hill-Rom and Welch Allyn are Baxter
                                         BRANDS; hillrom.com 301s to Baxter
  Diversey                               diversey.com 301s to solenis.com;
                                         the $4.6bn completion itself
  Essity UK Limited                      the UK brands (Leukoplast, Cutimed,
                                         JOBST, Actimove, Delta-Cast); BSN
                                         Medical Ltd still separately registered
  HC21 (UK) Ltd                          Healthcare 21 brand still trades
  Pennamed Limited                       still trades as Pennamed, and where
  Promedics Orthopaedics Ltd             exclusive UK provider of Aspen products
  Richardson Healthcare                  NO LONGER TRADES UNDER THAT NAME --
                                         rebranded DirectMed Imaging 01/06/2025

Richardson Healthcare is the one that mattered most. Its rendered deepDive
says in terms "There is no parent company or corporate group structure on
the public record ... the sole person with significant control is an
individual", so a member reading the card today would take it for an
independent owner-managed business. It was acquired and rebranded in 2025.
The appended paragraph states both readings and infers nothing about how the
acquisition was structured, in the same register the Smith+Nephew paragraphs
already use on this file.

THE FOUR LEFT ALONE, AND WHY
----------------------------
  DJO UK Ltd (Enovis)         top-level is the Enovis PSC notification
                              (deepDive para 2, same entity and date) and the
                              Lima/Enovis group link (para 3). No brand fact.
  GS Medical Healthcare Ltd   GBUK and A&M Capital Europe are both already in
                              deepDive para 3. The Green SM Holdings detail is
                              corporate finance, not brand.
  Nevro Medical Limited       near word-for-word duplicate of paras 1 and 2.
  Smith+Nephew                the group chain is paras 1-3 in full, and what
                              remains is a curation instruction to the data
                              writer ("must not be listed as a second
                              competitor"), which is not member prose.

Append-only: existing paragraphs are asserted untouched, and exactly one
paragraph is added per record. Idempotent: a record whose last paragraph is
already the one below is skipped.

    python3 scripts/_publish_brand_presence_ownership_1118.py
    python3 scripts/_publish_brand_presence_ownership_1118.py --dry-run
"""
import json
import sys
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "supplier-seed.json"

# One appended paragraph per record, each ending in the source the record's
# own top-level `ownership` string cites, with that string's read date.
ADD = {
    "Armstrong Medical (Eakin Respiratory)": (
        "The trading brand is Eakin Respiratory; the legal entity is still "
        "Armstrong Medical Ltd, registered in Northern Ireland, company number "
        "NI025560. Source: the company's own site, "
        "https://www.eakinrespiratory.com/our-company , read 21/08/2026, which "
        "states under 'Eakin Healthcare': 'In 2020, Armstrong Medical was "
        "acquired by Eakin Healthcare, a Northern Irish family owned healthcare "
        "business', carries a 2020 'Eakin Acquisition' entry on its history "
        "timeline, and gives in its footer 'Armstrong Medical Ltd is a limited "
        "company registered in Northern Ireland', company number NI025560, VAT "
        "GB432578934, Wattstown Business Park, Newbridge Road, Coleraine BT52 1BS."
    ),
    "Axonics Modulation Technologies UK Limited": (
        "Axonics has no independent web presence, and the sacral neuromodulation "
        "portfolio now sits inside Boston Scientific's urology and pelvic health "
        "business, with effect from 15/11/2024. Source: three things read "
        "21/08/2026. (1) Boston Scientific's own newsroom listing, "
        "https://news.bostonscientific.com/news-releases , which carries 'Nov 15, "
        "2024 - Boston Scientific closes acquisition of Axonics, Inc.' linking to "
        "https://news.bostonscientific.com/2024-11-15-Boston-Scientific-Closes-"
        "Acquisition-of-Axonics,-Inc , the earlier agreement release being dated "
        "8 January 2024. (2) A live fetch of https://axonics.com/ , which "
        "redirects to https://www.bostonscientific.com/en-US/home.html . (3) "
        "Companies House advanced search: AXONICS MODULATION TECHNOLOGIES, U.K. "
        "LIMITED, 09622653, status Active, registered office Breakspear Park, "
        "Breakspear Way, Hemel Hempstead HP2 4TZ, which is the same registered "
        "office as BOSTON SCIENTIFIC LIMITED, 02729626."
    ),
    "Baxter / Hillrom": (
        "For a member meeting this supplier, Hill-Rom and Welch Allyn are brands "
        "of Baxter International Inc., not separate companies: Welch Allyn was "
        "acquired by Hillrom in 2015, and Baxter acquired Hillrom in 2021. "
        "Source: Baxter's own site, "
        "https://www.baxter.com/about-baxter/our-evolution/affiliated-brands , "
        "read 21/08/2026: 'In 2021, Baxter acquired Hillrom' and 'Welch Allyn was "
        "acquired by Hillrom in 2015 and became part of Baxter in 2021'. "
        "Corroborated by hillrom.com, which 301-redirects to "
        "https://pro.baxter.com/ (checked 21/08/2026)."
    ),
    "Diversey": (
        "Diversey survives as a brand inside Solenis and has no independent web "
        "presence, with effect from 05/07/2023. Source: two things read "
        "21/08/2026. (1) A live fetch of https://diversey.com/ , which "
        "301-redirects to https://www.solenis.com/en/ . (2) Solenis' own news "
        "release, "
        "https://www.solenis.com/en/resources/news-releases/2023/solenis-diversey-purchase/ "
        ", headed 'Solenis Completes Acquisition of Diversey for $4.6 Billion', "
        "datelined 'July 5, 2023 FOR IMMEDIATE RELEASE'."
    ),
    "Essity UK Limited": (
        "The UK product brands a member will meet from Essity's Health & Medical "
        "business area are Leukoplast, Cutimed, JOBST, Actimove and Delta-Cast; "
        "that business came in with BSN medical, which Essity acquired in 2017. "
        "Source: Essity's own 'Our Journey' page, "
        "https://www.essity.com/company/about-us/our-journey/ , read 21/08/2026. "
        "A separate point, corrected at source on 03/09/2026: BSN MEDICAL LIMITED "
        "(Companies House 04085346, Hull HU10 6FE) is still an ACTIVE, separately "
        "registered company — it was not absorbed as a legal entity, only the "
        "acquired product business was, so the two are not one company."
    ),
    "HC21 (UK) Ltd": (
        "Healthcare 21 continues to trade under its own brand as an AddLife "
        "subsidiary, AddLife AB being a publicly listed Swedish medtech group. "
        "Source: the group's own About page, https://healthcare21.eu/about-us/ , "
        "read 21/08/2026: 'Healthcare 21 is part of the AddLife AB Group, a "
        "listed Swedish Medtech company active on the European market' and 'In "
        "2021, Healthcare 21 was acquired by the AddLife AB Group'."
    ),
    "Pennamed Limited": (
        "Pennamed continues to trade under the Pennamed name, as the Hull-based "
        "distributor of endoscopic and decontamination consumables, at 30 Redcliff "
        "Road, Melton, East Yorkshire HU14 3RS. Source: Pennamed's own news page, "
        "item dated 08/04/2026, 'Getinge acquires Pennamed to strengthen "
        "endoscopy offering in the UK', "
        "https://pennamed.co.uk/news/getinge-acquires-pennamed-to-strengthen-endoscopy-offering-in-the-uk "
        "(read in full from https://pennamed.co.uk/news/)."
    ),
    "Promedics Orthopaedics Ltd": (
        "Commercially, Promedics presents as an Aspen Medical Products company "
        "and the exclusive UK provider of Aspen products. Source: the company's "
        "own About Us page, https://www.promedics.co.uk/pages/about-us , read "
        "21/08/2026: 'Promedics are an Aspen Medical Products company and the "
        "exclusive provider of Aspen products in the UK.'"
    ),
    "Richardson Healthcare": (
        "Trading name, which the register above does not show: Richardson "
        "Healthcare no longer trades under that name. It was acquired by "
        "DirectMed Imaging and rebranded as DirectMed Imaging with effect from "
        "01/06/2025, and DirectMed Imaging is itself now part of Tri-Imaging "
        "Solutions and a Frazier Healthcare Partners portfolio company. This "
        "record's own persons-with-significant-control paragraph above records an "
        "individual, Mayur Patel, as the sole person with significant control of "
        "company 04190638; that register reading and this rebrand are both "
        "reported here as they were read, and nothing is inferred about how the "
        "acquisition was structured or which entity now holds the shares. Source: "
        "DirectMed Imaging's own announcement 'Richardson Healthcare is Now "
        "DirectMed Imaging', published 1 June 2025, "
        "https://directmedimaging.com/richardson-healthcare-is-now-directmed-imaging/ "
        ", which also links its own acquisition release of 24 January 2025, "
        "https://directmedimaging.com/directmed-imaging-acquires-richardson-healthcare/ "
        "(read 21/08/2026)."
    ),
}

# Read, judged duplicative, and deliberately not touched. See the docstring.
SKIPPED = (
    "DJO UK Ltd (Enovis)",
    "GS Medical Healthcare Ltd",
    "Nevro Medical Limited",
    "Smith+Nephew",
)

# Settled by other sessions on 18/11/2026.
LEAVE_ALONE = ("Clinisupplies", "Clinisupplies GB Limited")


def dump(doc):
    return json.dumps(doc, indent=1, ensure_ascii=False)


def main():
    dry = "--dry-run" in sys.argv

    raw = SEED.read_text(encoding="utf-8")
    doc = json.loads(raw)

    # GUARD 1 — the formatting contract.
    assert dump(doc) == raw, (
        "round-trip is not byte-identical to data/supplier-seed.json; "
        "the formatting contract has changed and this script must not write"
    )

    recs = doc["suppliers"]
    before_count = len(recs)
    by_name = {}
    for r in recs:
        if isinstance(r, dict) and r.get("name"):
            by_name.setdefault(r["name"], r)

    frozen = {n: json.dumps(by_name[n], ensure_ascii=False, sort_keys=True)
              for n in tuple(LEAVE_ALONE) + SKIPPED if n in by_name}

    changed, done_already = [], []
    for name, para in ADD.items():
        assert name in by_name, "no record named %r" % name
        r = by_name[name]

        # GUARD 2 — this pass only ever APPENDS to a section that already
        # renders. A record with no ownership array is not this job.
        existing = (r.get("deepDive") or {}).get("ownership")
        assert isinstance(existing, list) and existing, \
            "%s has no deepDive.ownership to append to" % name

        # GUARD 3 — never append to one of the 19 published in a3389b7,
        # whose single paragraph IS the top-level string.
        assert existing != [r.get("ownership")], \
            "%s was published by a3389b7; this pass must not touch it" % name

        if existing[-1] == para:
            done_already.append(name)
            continue

        assert para not in existing, "%s already carries this paragraph" % name
        prior = list(existing)
        existing.append(para)

        # GUARD 4 — append only: every prior paragraph byte-identical, exactly
        # one added, and the new one carries its source.
        assert existing[:-1] == prior, name
        assert len(existing) == len(prior) + 1, name
        assert existing[-1] == para, name
        assert "Source:" in para and "http" in para, \
            "%s: appended paragraph carries no source" % name

        # GUARD 5 — the top-level string and its date are not disturbed;
        # scripts/refresh_supplier_careers.py:1079 still reads them.
        assert isinstance(r.get("ownership"), str) and r["ownership"].strip(), name
        changed.append((name, len(para), len(existing)))

    # GUARD 6 — nothing else moved.
    assert len(doc["suppliers"]) == before_count, "record count changed"
    for n, fp in frozen.items():
        assert json.dumps(by_name[n], ensure_ascii=False, sort_keys=True) == fp, \
            "%s was altered; it is on the leave-alone list" % n

    out = dump(doc)

    print("appended this run : %d" % len(changed))
    for name, n, total in sorted(changed):
        print("  %-42s +%4d chars  -> %d para" % (name, n, total))
    if done_already:
        print("already done      : %d" % len(done_already))
    print("read, left alone  : %d (%s)" % (len(SKIPPED), ", ".join(SKIPPED)))

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
