#!/usr/bin/env python3
"""One-off, idempotent: HARTMANN's non-wound range, product by product, on its
existing seed record. Runs ON TOP OF the HARTMANN company-entry change landed the
same day (MoliCare's 61 catalogue lines under the one "MoliCare (incontinence
pads, pull-ups, fixation pants)" term; Baktolin, Baktolan and Varolast Plus
seeded) and adds only what that left missing. Nothing it wrote is removed.

WHAT WAS STILL MISSING (reconciliation 30/09/2026, report in Cowork-OS
02-Elevate-and-Thrive/Hub/Data-Verification/hartmann-product-reconciliation-nonwound-2026-09-30.md)
  1. Help me prepare lists a company's seed strings only, so the whole MoliCare
     range was ONE pickable product. Here the one "MoliCare (incontinence pads,
     pull-ups, fixation pants)" term is replaced by one seed product per NHS
     Supply Chain MoliCare brand line, named exactly as the catalogue names it
     ("MoliCare Premium Elastic 6D"), so MoliCare is listed once per product and
     never twice. Its 61 cached lines are redistributed, not re-read: every line
     lands under its own brand's term (the script checks the NPC sets match), and
     the term's category decision (continence:pads, 28/09/2026) is carried to
     each brand term. Product Comparison and the Differentiator already showed
     these brand lines under the same names, so neither changes.
     Each gets its own cache entry holding only that line's NPCs, and its stored
     query is the brand name itself (the NPC for "MoliCare Fixpants", a prefix of
     two other lines). Every query was run on the pilot catalogue on 30/09/2026
     and returns that brand line and nothing else, so refresh_nhssc_cache.py,
     which retries the stored query first, keeps each entry to its own lines.
     Without an entry, the refresh would search "MoliCare Premium" and its
     word-overlap name_ok() would file every Premium line under each term.
  2. "Sterillium med / Stellisept med (hand disinfectants)" listed Stellisept med
     as the same product as Sterillium med and showed it with Sterillium's three
     catalogue lines. Stellisept med is HARTMANN's antimicrobial body wash
     (hartmann.info/en-gb Disinfection > Skin > Antimicrobial Body Cleansing) and
     has no catalogue line. Split: the term becomes "Sterillium med (hand
     disinfectant)" (same query, same lines, same category decision) and
     Stellisept med is its own product, recorded as not in the catalogue.
  3. Not on the Hub at all: SicSac (hartmann.info/en-gb Patient Care), the Vala
     disposable care range (HARTMANN Direct, same legal entity, and the UK brand
     overview page), and the six HARTMANN dispenser/pump lines under PAUL
     HARTMANN LTD on NHS Supply Chain (brand HARTMANN/Hartmann, found through
     the "Hartmann" search, the only such lines in its 325 results).

  Names carry the product and what it is, nothing else (no curator notes).
  No seed name here contains ";": app/comparison.js splits a term on ";" and
  would list the text after it as a product of its own.

  NOT added, deliberately: MoliCare products HARTMANN lists that NHS Supply
  Chain does not (Lady pads, MEN pants, absorbent underwear, skin care, ...),
  and Peha-soft vinyl/latex gloves. A seed term with no catalogue line is
  searched each Sunday by its first two words, then its first word, and name_ok()
  accepts any card sharing one 4+ letter word, so each would collect other
  MoliCare (or Peha-haft) lines. They stay listed as missing, with that cause.

SOURCES, all read 30/09/2026 in Chrome as a person would: hartmann.info/en-gb
product tree (robots.txt that day: a Sitemap line only), hartmanndirect.co.uk
Infection Prevention and Skin Care, pilot.supplychain.nhs.uk searches read with
scripts/nhssc_card.EXTRACT_JS ("MoliCare" 61 lines, matching the continence
page's own snapshot NPC for NPC; "Stellisept", "SicSac", "Vala" no results).

Writes data/supplier-seed.json (seed_format.write_like), data/nhssc-cache.json,
data/differentiator-category-map.json; then run scripts/build_differentiator.py.
Run from the repo root: python3 scripts/_hartmann_nonwound_products_0930.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

SEED = "data/supplier-seed.json"
CACHE = "data/nhssc-cache.json"
CMAP = "data/differentiator-category-map.json"
SUP = "Paul Hartmann (HARTMANN)"
READ = "30/09/2026"
IMG = "https://media.supplychain.nhs.uk/media/images/"
MOLI_TERM = "MoliCare (incontinence pads, pull-ups, fixation pants)"
STER_OLD = "Sterillium med / Stellisept med (hand disinfectants)"
STER_NEW = "Sterillium med (hand disinfectant)"
PADS = "continence:pads"

# NHS Supply Chain lines, read 30/09/2026: npc, mpc, brand, account, desc, pack, image tail.
H, HD = "PAUL HARTMANN LTD", "PAUL HARTMANN LTD (HDS)"
LINES = [
    ("CFP4334", "947741", "MoliCare Fixpants", H, "Fixation Pants for use with Pads with Legs Medium 60-100cm Basic", "Case of 300", "CFP4334/large/786944_CFP4334.jpg"),
    ("CFP4263", "160892", "MoliCare Rectangular 4D", H, "Rectangular pad absorbency band I7 60x20cm (PE Back Sheet)", "Case of 200", "CFP4263/large/786803_CFP4263_2.jpg"),
    ("CFP3416", "160890", "MoliCare Rectangular 3D", HD, "Rectangular pad absorbency band I5 40x20cm (PE Back Sheet)", "Pack of 50", "CFP3416/large/1130185_CFP3416.jpg"),
    ("CFP3434", "160892", "MoliCare Rectangular 4D", HD, "Rectangular pad absorbency band I7 60x20cm (PE Back Sheet)", "Pack of 50", "CFP3434/large/1130194_CFP3434.jpg"),
    ("CFP4288", "166225", "MoliCare Premium Mobile 6D", H, "Absorbent Pull Up Pants D14 XS 45-70cm (Textile Back Sheet) NON-RETURNABLE", "Case of 56", "CFP4288/large/786859_CFP4288.jpg"),
    ("CFP4313", "165372", "MoliCare Premium Elastic 7D", H, "All-in-one pads absorbency band D16 Medium 85-120cm (Textile Back Sheet)", "Case of 90", "CFP4313/large/786908_CFP4313_2.jpg"),
    ("CFP4259", "166029", "MoliCare Premium Mobile 8D", H, "Absorbent Pull Up Pants D15 Small 60-90cm (Textile Back Sheet)", "Case of 56", "CFP4259/large/786796_CFP4259_1.jpg"),
    ("CFP4291", "947743", "MoliCare Fixpants Long Leg", H, "Fixation Pants for use with Pads with Legs XL 100-160cm Basic", "Case of 300", "CFP4291/large/786867_CFP4291_1.jpg"),
    ("CFP4283", "915844", "MoliCare Premium Mobile 6D", H, "Absorbent Pull Up Pants D15 XL 130-170cm (Textile Back Sheet)", "Case of 56", "CFP4283/large/786852_CFP4283.jpg"),
    ("CFP4293", "166014", "MoliCare Premium Mobile 6D", H, "Absorbent Pull Up Pants D14 Medium 75-120cm (Textile Back Sheet)", "Case of 42", "CFP4293/large/776583_CFP4293.jpg"),
    ("CXP85288", "166225", "MoliCare Premium Mobile 6D", HD, "Absorbent Pull Up Pants D14 XS 45-70cm (Textile Back Sheet)", "Pack of 14", "CXP85288/large/1130623_CXP85288.jpg"),
    ("CFP4294", "165572", "MoliCare Premium Elastic 9D", H, "All-in-one pads absorbency band D19 Medium 70-125cm (Textile Back Sheet)", "Case of 78", "CFP4294/large/786870_CFP4294.jpg"),
    ("CFP4255", "165273", "MoliCare Premium Elastic 6D", H, "All-in-one pads absorbency band D16 Large 115-145cm (Textile Back Sheet)", "Case of 90", "CFP4255/large/786787_CFP4255.jpg"),
    ("CFP4247", "166030", "MoliCare Premium Mobile 8D", H, "Absorbent Pull Up Pants D15 Medium 75-120cm (Textile Back Sheet)", "Case of 42", "CFP4247/large/776582_CFP4247.jpg"),
    ("CFP4279", "165172", "MoliCare Premium Elastic 5D", H, "All-in-one pads absorbency band D15 Medium 70-125cm (Textile Back Sheet)", "Case of 90", "CFP4279/large/786845_CFP4279_2.jpg"),
    ("CFP4319", "166123", "MoliCare Premium Mobile 5D", H, "Absorbent Pull Up Pants D13 Small 60-90cm (Textile Back Sheet)", "Case of 56", "CFP4319/large/786917_CFP4319.jpg"),
    ("CFP4264", "165373", "MoliCare Premium Elastic 7D", H, "All-in-one pads absorbency band D17 Large 115-145cm (Textile Back Sheet)", "Case of 90", "CFP4264/large/786805_CFP4264_1.jpg"),
    ("CFP4246", "947742", "MoliCare Fixpants Long Leg", H, "Fixation Pants for use with Pads with Legs Large 80-120cm Basic", "Case of 300", "CFP4246/large/786772_CFP4246_1.jpg"),
    ("CXP85181", "166031", "MoliCare Premium Mobile 8D", H, "Absorbent Pull Up Pants D16 Large 100-150cm (Textile Back Sheet)", "Case of 56", "CXP85181/large/1027062_CXP85181.jpg"),
    ("CFP4261", "165672", "MoliCare Premium Elastic 10D", H, "All-in-one pads absorbency band D20 Medium 70-125cm (Textile Back Sheet)", "Case of 56", "CFP4261/large/786800_CFP4261_2.jpg"),
    ("CFP4331", "165583", "MoliCare Premium Elastic 9D", H, "All-in-one pads absorbency band D20 Large 115-145cm (Textile Back Sheet)", "Case of 72", "CFP4331/large/786938_CFP4331.jpg"),
    ("CFP4268", "165471", "MoliCare Premium Elastic 8D", H, "All-in-one pads absorbency band D16 Small 70-90cm (Textile Back Sheet)", "Case of 78", "CFP4268/large/786814_CFP4268.jpg"),
    ("CXP85010", "947744", "MoliCare Fixpants Long Leg", H, "Fixation Pants for use with Pads with Legs 2XL 140-180cm Basic", "Case of 300", "CXP85010/large/929998_CXP85010.jpg"),
    ("CFP4435", "168403", "MoliCare Premium Form 3D", H, "Shaped pad with absorbency band I9 (Textile Back Sheet)", "Case of 128", "CFP4435/large/786964_CFP4435_2.jpg"),
    ("CFP3462", "165571", "MoliCare Premium Elastic 9D", HD, "All-in-one pads absorbency band D17 Small 70-90cm (Textile Back Sheet)", "Pack of 26", "CFP3462/large/1130204_CFP3462.jpg"),
    ("CFP4434", "168405", "MoliCare Premium Form 5D", H, "Shaped pad with absorbency band I11 (Textile Back Sheet)", "Case of 128", "CFP4434/large/786959_CFP4434.jpg"),
    ("CFP4310", "165474", "MoliCare Premium Elastic 8D", H, "All-in-one pads absorbency band D19 XL 140-174cm (Textile Back Sheet)", "Case of 56", "CFP4310/large/786899_CFP4310.jpg"),
    ("CFP3455", "915881", "MoliCare Premium Mobile 8D", HD, "Absorbent Pull Up Pants D15 Small 60-90cm (Textile Back Sheet)", "Pack of 14", "CFP3455/large/1130199_CFP3455.jpg"),
    ("CFP4316", "915841", "MoliCare Premium Mobile 6D", H, "Absorbent Pull Up Pants D14 Small 60-90cm (Textile Back Sheet)", "Case of 56", "CFP4316/large/786916_CFP4316_1.jpg"),
    ("CFP4249", "166015", "MoliCare Premium Mobile 6D", H, "Absorbent Pull Up Pants D15 Large 100-150cm (Textile Back Sheet)", "Case of 56", "CFP4249/large/786774_CFP4249_1.jpg"),
    ("CXP85180", "166031", "MoliCare Premium Mobile 8D", HD, "Absorbent Pull Up Pants D16 Large 100-150cm (Textile Back Sheet)", "Pack of 14", "CXP85180/large/1130557_CXP85180.jpg"),
    ("CFP4272", "165674", "MoliCare Premium Elastic 10D", H, "All-in-one pads absorbency band D21 XL 140-175cm (Textile Back Sheet)", "Case of 56", "CFP4272/large/786826_CFP4272_1.jpg"),
    ("CFP4243", "165673", "MoliCare Premium Elastic 10D", H, "All-in-one pads absorbency band D20 Large 115-145cm (Textile Back Sheet)", "Case of 56", "CFP4243/large/786767_CFP4243_2.jpg"),
    ("CFP4433", "168407", "MoliCare Premium Form 7D", H, "Shaped pad with absorbency band I14 (Textile Back Sheet)", "Case of 128", "CFP4433/large/786956_CFP4433.jpg"),
    ("CFP3481", "165172", "MoliCare Premium Elastic 5D", HD, "All-in-one pads absorbency band D15 Medium 70-125cm (Textile Back Sheet)", "Pack of 30", "CFP3481/large/1130210_CFP3481.jpg"),
    ("CFP4253", "166032", "MoliCare Premium Mobile 8D", H, "Absorbent Pull Up Pants D16 XL 130-170cm (Textile Back Sheet)", "Case of 56", "CFP4253/large/786782_CFP4253.jpg"),
    ("CFP3480", "915842", "MoliCare Premium Mobile 6D", HD, "Absorbent Pull Up Pants D14 Medium 75-120cm (Textile Back Sheet)", "Pack of 14", "CFP3480/large/1130209_CFP3480.jpg"),
    ("CFP4437", "168404", "MoliCare Premium Form 4D", H, "Shaped pad with absorbency band I10 (Textile Back Sheet)", "Case of 128", "CFP4437/large/786968_CFP4437.jpg"),
    ("CFP3457", "165273", "MoliCare Premium Elastic 6D", HD, "All-in-one pads absorbency band D16 Large 115-145cm (Textile Back Sheet)", "Pack of 30", "CFP3457/large/1130201_CFP3457.jpg"),
    ("CFP4244", "915862", "MoliCare Premium Mobile 5D", H, "Absorbent Pull Up Pants D13 Medium 75-120cm (Textile Back Sheet)", "Case of 42", "CFP4244/large/776581_CFP4244.jpg"),
    ("CFP4339", "915855", "MoliCare Premium Mobile 5D", H, "Absorbent Pull Up Pants D13 XL 130-170cm (Textile Back Sheet)", "Case of 56", "CFP4339/large/786953_CFP4339_1.jpg"),
    ("CFP4269", "165472", "MoliCare Premium Elastic 8D", H, "All-in-one pads absorbency band D18 Medium 70-125cm (Textile Back Sheet)", "Case of 78", "CFP4269/large/786817_CFP4269.jpg"),
    ("CFP4289", "166001", "MoliCare Premium Mobile 5D", H, "Absorbent Pull Up Pants D13 Large 100-150cm (Textile Back Sheet)", "Case of 56", "CFP4289/large/786861_CFP4289.jpg"),
    ("CFP4438", "168408", "MoliCare Premium Form 8D", H, "Shaped pad with absorbency band I15 (Textile Back Sheet)", "Case of 128", "CFP4438/large/786973_CFP4438_2.jpg"),
    ("CFP4436", "168406", "MoliCare Premium Form 6D", H, "Shaped pad with absorbency band I13 (Textile Back Sheet)", "Case of 128", "CFP4436/large/786967_CFP4436_2.jpg"),
    ("CFP85417", "165284", "MoliCare Premium Elastic 6D", H, "All-in-one pads absorbency band D17 XL 140-145cm (Textile Back Sheet)", "Case of 56", "CFP85417/large/844532_CFP85417.jpg"),
    ("CFP4305", "165473", "MoliCare Premium Elastic 8D", H, "All-in-one pads absorbency band D18 Large 115-145cm (Textile Back Sheet)", "Case of 72", "CFP4305/large/786889_CFP4305.jpg"),
    ("CFP4297", "165574", "MoliCare Premium Elastic 9D", H, "All-in-one pads absorbency band D20 XL 140-175cm (Textile Back Sheet)", "Case of 56", "CFP4297/large/786875_CFP4297.jpg"),
    ("CFP85076", "165284", "MoliCare Premium Elastic 6D", HD, "All-in-one pads absorbency band D17 XL 140-174cm (Textile Back Sheet)", "Pack of 14", "CFP85076/large/1130276_CFP85076.jpg"),
    ("VMU627", "161063", "MoliCare Premium Bed Mat 5D", H, "Procedure Pad - Non Recycled Fluff 60x60cm without SAP", "Case of 120", "VMU627/large/786999_VMU627_2.jpg"),
    ("CFP4300", "168707", "MoliCare Premium Men Pad 4D", H, "Male shaped pad with absorbency band I6 (Textile Back Sheet)", "Case of 168", "CFP4300/large/786883_CFP4300_2.jpg"),
    ("CFP4270", "947815", "MoliCare Premium Fixpant Long Leg", H, "Fixation Pants for use with Pads with Legs 3XL 160-200cm Comfort", "Case of 200", "CFP4270/large/786820_CFP4270.jpg"),
    ("CFP4395", "169190", "MoliCare Premium Slip Extra Plus", H, "All-in-one pads absorbency band D14 XS 40-60cm (Textile Back Sheet)", "Case of 120", "CFP4395/large/844527_CFP4395.jpg"),
    ("CFP4286", "168069", "MoliCare Premium Men Pad 5D", H, "Male shaped pad with absorbency band I7 (Textile Back Sheet)", "Case of 168", "CFP4286/large/786855_CFP4286_1.jpg"),
    ("VMU628", "161065", "MoliCare Premium Bed Mat 5D", H, "Procedure Pad - Non Recycled Fluff 60x90cm without SAP", "Case of 120", "VMU628/large/787001_VMU628_1.jpg"),
    ("CFP4338", "947798", "MoliCare Premium Fixpant Long Leg", H, "Fixation Pants for use with Pads with Legs XL 100-160cm Comfort", "Case of 200", "CFP4338/large/786950_CFP4338.jpg"),
    ("VMU571", "161065", "MoliCare Premium Bed Mat 5D", HD, "Procedure Pad - Non Recycled Fluff 60x90cm without SAP", "Pack of 30", "VMU571/large/1130699_VMU571.jpg"),
    ("CFP4273", "947796", "MoliCare Premium Fixpant Long Leg", H, "Fixation Pants for use with Pads with Legs Medium 60-100cm Comfort", "Case of 200", "CFP4273/large/786828_CFP4273.jpg"),
    ("VMU567", "161063", "MoliCare Premium Bed Mat 5D", HD, "Procedure Pad - Non Recycled Fluff 60x60cm without SAP", "Pack of 30", "VMU567/large/1130698_VMU567.jpg"),
    ("CFP3397", "168600", "MoliCare Premium Men Pad Pouch 2D", HD, "Male shaped pad with absorbency band I5 (Textile Back Sheet)", "Pack of 14", "CFP3397/large/1130176_CFP3397.jpg"),
    ("CFP4266", "168600", "MoliCare Premium Men Pad Pouch 2D", H, "Male shaped pad with absorbency band I5 (Textile Back Sheet)", "Case of 168", "CFP4266/large/786811_CFP4266_2.jpg"),
    # Infection prevention, hand hygiene, compression
    ("MRB843", "981329", "Baktolin", H, "Hand wash Liquid bottle 1000ml", "Case of 10", "MRB843/large/604103_MRB843.jpg"),
    ("MTH85000", "980360", "Baktolan", H, "Moisturiser Cream Bottle 350ml", "Case of 20", "MTH85000/large/804945_MTH85000.jpg"),
    ("MTH85001", "980140", "Baktolan", H, "Moisturiser Intensive Repair Cream 100ml Tube", "Case of 25", "MTH85001/large/804946_MTH85001.jpg"),
    ("EFA85001", "931582", "Varolast Plus", H, "Bandage zinc paste BP 8cm x 5m", "Case of 16", "EFA85001/large/1116141_EFA85001_1.jpg"),
    ("MTH85178", "981600", "HARTMANN", H, "Dispensers and Accessories Single-use pump short nozzle to fit 350/500 ml bottle", "Case of 200", "MTH85178/large/888341_MTH85178.jpg"),
    ("MTH85179", "981601", "HARTMANN", H, "Dispensers and Accessories Single-use pump short nozzle to fit 1 litre bottle", "Case of 200", "MTH85179/large/888342_MTH85179.jpg"),
    ("MTH85180", "981602", "HARTMANN", H, "Dispensers and Accessories Single-use pump long nozzle to fit 350/500ml bottle", "Case of 200", "MTH85180/large/888343_MTH85180.jpg"),
    ("MTH85220", "981603", "Hartmann", H, "Dispensers and Accessories Single-use pump long nozzle 1 litre non-returnable", "Pack of 50", ""),
    ("MTH85221", "980478", "Hartmann", H, "Dispensers and Accessories Euro dispenser 1 plus 500 ml long arm non-returnable", "Each", ""),
    ("MTH85222", "980479", "Hartmann", H, "Dispensers and Accessories Euro Dispenser 1 plus 1 l long arm non-returnable", "Each", ""),
]


MOLI_BRANDS = []
for _l in LINES:
    if _l[2].startswith("MoliCare") and _l[2] not in MOLI_BRANDS:
        MOLI_BRANDS.append(_l[2])
MOLI_BRANDS.sort(key=lambda b: [int(t) if t.isdigit() else t.lower()
                                 for t in __import__("re").findall(r"\d+|\D+", b)])
# (seed product name, NHSSC brand line(s), stored query, category)
TERMS = [(b, [b], ("CFP4334" if b == "MoliCare Fixpants" else b), PADS) for b in MOLI_BRANDS]
TERMS.append(("HARTMANN hand hygiene dispensers and single-use pumps",
              ["HARTMANN", "Hartmann"], "Hartmann", None))

NOT_CATALOGUE = [
    ("Stellisept med (antimicrobial body wash)",
     "on hartmann.info/en-gb (Disinfection > Skin > Antimicrobial Body Cleansing); NHS Supply Chain search 'Stellisept' returned no results 30/09/2026"),
    ("SicSac (disposable sick bag)",
     "on hartmann.info/en-gb (Patient Care > Personal and Patient Hygiene); NHS Supply Chain search 'SicSac' returned no results 30/09/2026"),
    ("Vala disposable care range (bibs, towels, washing mitts, sheets)",
     "on HARTMANN Direct (hartmanndirect.co.uk, Infection Prevention and Skin Care) and hartmann.info/en-gb's brand overview; NHS Supply Chain search 'Vala' returned no results 30/09/2026"),
]

NOTE = (" Non-wound range made product by product 30/09/2026: each NHS Supply Chain MoliCare brand line, "
        "Stellisept med split from Sterillium med, SicSac, the Vala range and HARTMANN's dispenser/pump lines, "
        "from hartmann.info/en-gb, HARTMANN Direct and the NHS Supply Chain catalogue read that day. "
        "MoliCare products the site lists but the catalogue does not are not seeded yet.")


def item(line):
    npc, mpc, brand, acct, desc, pack, img = line
    return {"name": brand, "supplier": acct, "desc": desc, "npc": npc, "mpc": mpc,
            "status": "", "pack": pack, "img": (IMG + img) if img else ""}


def pname(p):
    return p if isinstance(p, str) else (p or {}).get("name")


def main():
    seed = json.loads(open(SEED, "rb").read())
    recs = [s for s in seed["suppliers"] if s.get("name") == SUP]
    if len(recs) != 1:
        sys.exit("expected exactly one %r record, found %d" % (SUP, len(recs)))
    rec = recs[0]
    prods = [STER_NEW if pname(p) == STER_OLD else p for p in rec["products"]]
    names = [pname(p) for p in prods]
    # MoliCare lines go straight after the MoliCare term; the rest after Sterillium.
    moli_new = [t[0] for t in TERMS if t[0].startswith("MoliCare") and t[0] not in names]
    other_new = [n for n in [TERMS[-1][0]] + [n for n, _ in NOT_CATALOGUE] if n not in names]
    def insert_after(lst, anchor, new):
        if not new:
            return lst
        i = next((k for k, p in enumerate(lst) if pname(p) == anchor), len(lst) - 1)
        return lst[:i + 1] + new + lst[i + 1:]
    prods = insert_after(prods, MOLI_TERM, moli_new)
    prods = [p for p in prods if pname(p) != MOLI_TERM]
    prods = insert_after(prods, STER_NEW, other_new)
    rec["products"] = prods
    if NOTE.strip() not in (rec.get("note") or ""):
        rec["note"] = ((rec.get("note") or "") + NOTE).strip()
    fmt = write_like(SEED, seed)
    print("seed: %d added, Sterillium term %s, %d products now (%s)" % (
        len(moli_new) + len(other_new), "renamed" if STER_OLD in names or STER_NEW in names else "NOT FOUND",
        len(prods), fmt))

    cache = json.loads(open(CACHE, "rb").read())
    P = cache["products"]
    if STER_OLD in P and STER_NEW not in P:
        P[STER_NEW] = P.pop(STER_OLD)
    by_brand = {}
    for ln in LINES:
        by_brand.setdefault(ln[2], []).append(item(ln))
    old_moli = P.pop(MOLI_TERM, None)
    if old_moli:
        want = {ln[0] for ln in LINES if ln[2].startswith("MoliCare")}
        got = {it.get("npc") for it in old_moli.get("items") or []}
        if got - want:
            sys.exit("MoliCare term holds lines this script does not place: %s" % sorted(got - want))
    for name, brands, query, _cat in TERMS:
        items = [it for b in brands for it in by_brand[b]]
        seen = {it["npc"] for it in items}
        for it in (P.get(name) or {}).get("items") or []:   # never shrink an entry
            if it.get("npc") not in seen:
                items.append(it)
        P[name] = {"supplier": SUP, "query": query, "items": items}
    nc = cache.setdefault("notCatalogue", {})
    for name, reason in NOT_CATALOGUE:
        nc[name] = {"supplier": SUP, "reason": reason, "checkedOn": READ}
    for name in [t[0] for t in TERMS] + [STER_NEW]:
        nc.pop(name, None)
    cache.setdefault("_meta", {})["hartmannNonWoundRead"] = {
        "when": READ, "by": "scripts/_hartmann_nonwound_products_0930.py",
        "how": "pilot.supplychain.nhs.uk searches read in Chrome with nhssc_card.EXTRACT_JS",
        "terms": len(TERMS)}
    write_like(CACHE, cache)
    print("cache: %d terms, %d lines; %d notCatalogue" % (
        len(TERMS), sum(len(P[t[0]]["items"]) for t in TERMS), len(NOT_CATALOGUE)))

    cm = json.loads(open(CMAP, "rb").read())
    ents = cm["entries"]
    for e in ents:
        if e.get("kind") == "nhssc-term" and e.get("supplier") == SUP and e.get("term") == STER_OLD:
            e.setdefault("_renamedFrom2", STER_OLD)
            e["term"] = STER_NEW
            e["_splitNote"] = ("30/09/2026: Stellisept med (antimicrobial body wash, no catalogue line) split out "
                               "to its own product; this term keeps Sterillium Med's three lines and its category.")
    retired = [e for e in ents if e.get("kind") == "nhssc-term" and e.get("supplier") == SUP
               and e.get("term") == MOLI_TERM]
    ents[:] = [e for e in ents if e not in retired]
    have = {e.get("term") for e in ents if e.get("kind") == "nhssc-term" and e.get("supplier") == SUP}
    added = 0
    for name, brands, query, cat in TERMS:
        if not cat or name in have:
            continue
        its = P[name]["items"]
        ents.append({
            "kind": "nhssc-term", "supplier": SUP, "term": name, "division": None,
            "products": len(its), "categories": [],
            "examples": ["%s (%s, %s)" % (it["desc"], it["name"], it["npc"]) for it in its[:4]],
            "hub": cat, "notTaxonomy": False,
            "evidence": "NHS Supply Chain public catalogue (pilot.supplychain.nhs.uk search), read 30/09/2026; "
                        "decision made on the catalogue's own item descriptions above",
            "why": ("One MoliCare brand line of the 'MoliCare (incontinence pads, pull-ups, fixation pants)' term, "
                    "seeded on its own so Help me prepare can offer it; same decision as that term (28/09/2026): "
                    "containment pads, pants, all-in-ones, underpads and fixation pants are continence:pads."),
            "decidedIn": "HARTMANN non-wound reconciliation 30/09/2026",
        })
        added += 1
    write_like(CMAP, cm)
    print("category map: %d added, %d MoliCare term entry retired" % (added, len(retired)))


if __name__ == "__main__":
    main()
