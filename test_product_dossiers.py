#!/usr/bin/env python3
"""
Invariant gate for the product dossiers (root rule 14).

A dossier publishes several sources about one product. Its failure mode is not a
crash - it is a quiet mis-attribution: one product's specification appearing
under another's name, or a manufacturer's marketing claim reading as an
NHS-authored measurement. These checks pin the things that would make that
happen, and each is self-tested so it cannot pass vacuously.

Usage:  python3 test_product_dossiers.py
"""

from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import build_product_dossiers as B                                  # noqa: E402

failures: list[str] = []
checks = 0


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        failures.append(what)
    return ok


def test_size_stripping():
    """The pack size comes off the name and is KEPT, never discarded."""
    base, variant = B.strip_size("Tegaderm Foam dressing (adhesive) 10cm x 11cm oval")
    check(base == "Tegaderm Foam dressing (adhesive)", "size strip base: %r" % base)
    check("10cm x 11cm" in variant, "the stripped size must be kept: %r" % variant)
    # A name with no size must be returned untouched - stripping a real word out
    # of a product name is how "Allevyn Gentle Border Lite" becomes "Allevyn".
    base2, variant2 = B.strip_size("Allevyn Gentle Border Lite")
    check(base2 == "Allevyn Gentle Border Lite" and variant2 == "",
          "a name with no size must be untouched: %r / %r" % (base2, variant2))


def test_longest_family_wins():
    """A Lite dressing must not be filed under the standard one's family."""
    b = B.Builder("wound")
    b.note_family("ACME", "Allevyn Gentle")
    b.note_family("ACME", "Allevyn Gentle Border Lite")
    got = b.family_of("ACME", "Allevyn Gentle Border Lite dressing")
    check(got == "Allevyn Gentle Border Lite",
          "longest family must win, got %r" % got)
    # And a family must match on a word boundary, never mid-word: "Allevyn
    # Gentle" must not swallow a hypothetical "Allevyn Gentleman".
    check(b.family_of("ACME", "Allevyn Gentleness") is None,
          "family matching must respect word boundaries")
    check(b.family_of("ACME", "Mepilex Border") is None,
          "an unrelated product must not be given a family")


def test_published_store():
    path = os.path.join(REPO, "data", "product-dossiers-wound.json")
    if not check(os.path.exists(path), "product-dossiers-wound.json is missing"):
        return
    store = json.load(open(path))
    dossiers = store.get("dossiers") or []
    check(bool(dossiers), "the store publishes no dossiers")
    check(bool(store.get("joinRule")), "the join rule must be stated in the file")
    check(bool(store.get("readingRule")), "the reading rule must be stated in the file")

    kinds_seen = set()
    for d in dossiers:
        # Every source block must say who it is and what KIND of fact it is -
        # without the kind, a manufacturer claim reads as an NHS measurement.
        for sid, block in d["sources"].items():
            if not check(block.get("kind") in
                         ("independent", "catalogue", "manufacturer", "tariff", "regulatory"),
                         "%s: source %s has no usable kind" % (d["key"], sid)):
                return
            kinds_seen.add(block["kind"])
            if not check(bool(block.get("name")),
                         "%s: source %s is unattributed" % (d["key"], sid)):
                return

        for field, obs in d["fields"].items():
            for ob in obs:
                if not check(ob.get("source") in d["sources"],
                             "%s/%s: observation cites source %r that is not listed"
                             % (d["key"], field, ob.get("source"))):
                    return
                if not check(ob.get("scope") in ("product", "family"),
                             "%s/%s: observation has no scope" % (d["key"], field)):
                    return
                # A family-scope observation MUST name the variant it was
                # actually measured on. Without it the figure reads as this
                # product's own, which is the mis-attribution this whole
                # structure exists to prevent.
                if ob["scope"] == "family" and not check(
                        bool(ob.get("variant")),
                        "%s/%s: family-scope value %r names no variant"
                        % (d["key"], field, ob.get("value"))):
                    return

        # A family-scope observation can only exist where a family was assigned.
        if any(o["scope"] == "family" for obs in d["fields"].values() for o in obs):
            if not check(bool(d.get("family")),
                         "%s carries family-scope values but has no family" % d["key"]):
                return

    check("independent" in kinds_seen,
          "no independent (ICC) source reached any dossier — the join has broken")
    check(store["counts"]["withMoreThanOneSource"] >= 50,
          "only %s dossiers carry more than one source — the join has regressed"
          % store["counts"]["withMoreThanOneSource"])
    check(len(dossiers) >= 700,
          "only %d dossiers — the speciality filter has narrowed" % len(dossiers))


def test_antimicrobial_variant_never_joins_plain_family():
    """Exufiber Ag+, Durafiber Ag, ActivHeal PHMB, Biatain Silicone Ag, Mepitel
    Ag, Urgotul Ag, UrgoClean Ag and ActivHeal Aquafiber Ag all begin with a
    plain range's name. Until 30/09/2026 the longest-prefix rule filed them
    under it, so the plain range's dossier carried the antimicrobial variant's
    tariff lines and the variant inherited the plain range's NHS measurements.
    The same fault in the comparison tool credited plain Atrauman with an
    antimicrobial element on a HARTMANN prospect's own product."""
    b = B.Builder("wound")
    b.note_family("ACME", "Exufiber")
    b.note_family("ACME", "Atrauman")
    b.note_family("ACME", "Atrauman AG")
    b.note_family("ACME", "ActivHeal")
    check(b.family_of("ACME", "Exufiber Ag+ dressing") is None,
          "a silver variant was filed under the plain family")
    check(b.family_of("ACME", "ActivHeal PHMB Foam Non-Adhesive dressing") is None,
          "a PHMB variant was filed under the plain family")
    check(b.family_of("ACME", "Exufiber dressing") == "Exufiber",
          "the plain variant lost its own family")
    check(b.family_of("ACME", "Atrauman Ag dressing") == "Atrauman AG",
          "the silver variant did not reach its own silver family")
    check(b.family_of("ACME", "Atrauman dressing") == "Atrauman",
          "plain Atrauman did not reach the plain family")
    check(B.names_antimicrobial("Mepilex Border Ag") and not B.names_antimicrobial("Mepilex Border"),
          "names_antimicrobial must read Ag as a word, not a letter pair")
    check(not B.names_antimicrobial("Algivon Plus") and not B.names_antimicrobial("Aglet"),
          "names_antimicrobial must not fire inside a word")

    # The published stores: no dossier mixes antimicrobial and plain through its
    # family, in either direction.
    for spec in ("wound", "respiratory"):
        path = os.path.join(REPO, "data", "product-dossiers-%s.json" % spec)
        if not os.path.exists(path):
            continue
        for d in json.load(open(path)).get("dossiers") or []:
            fam = d.get("family") or ""
            own = B.names_antimicrobial(d["name"]) or B.names_antimicrobial(fam)
            if fam and not check(
                    not (B.names_antimicrobial(d["name"]) and not B.names_antimicrobial(fam)),
                    "%s: an antimicrobial product sits in plain family %r" % (d["key"], fam)):
                return
            for field, obs in d["fields"].items():
                for ob in obs:
                    if ob.get("scope") == "family" and not own and not check(
                            not B.names_antimicrobial(ob.get("variant") or ""),
                            "%s/%s: plain product carries antimicrobial variant %r"
                            % (d["key"], field, ob.get("variant"))):
                        return


def test_no_silent_merge():
    """Self-test: two same-supplier products whose names share a prefix must
    stay two dossiers, however tempting the prefix looks."""
    b = B.Builder("wound")
    a = b.dossier_for("Advanced Medical Solutions Ltd", "ActivHeal Foam")
    c = b.dossier_for("Advanced Medical Solutions Ltd", "ActivHeal Foam Border")
    check(a is not c, "a shared name prefix must never merge two products")
    # ...but the same NPC must merge them, because that IS the same catalogue line.
    e = b.dossier_for("Advanced Medical Solutions Ltd", "Something", npc="ELA838")
    f = b.dossier_for("A Totally Different Name Ltd", "Other", npc="ELA838")
    check(e is f, "the same NPC must join two records")


def with_store(name, store, fn):
    """Run fn with B.load returning `store` for one data file."""
    real = B.load
    B.load = lambda n, default=None: store if n == name else real(n, default)
    try:
        fn()
    finally:
        B.load = real


def test_alert_needs_a_product_word():
    """An MHRA alert must name the product, not just the company. Until
    28/09/2026 the word "resmed" alone put the Astral ventilator NatPSA on the
    ResMed AirSense 11 AutoSet dossier."""
    b = B.Builder("respiratory")
    supplier, _ = b.resolve_supplier("ResMed")
    airsense = b.dossier_for(supplier, "ResMed AirSense 11 AutoSet")
    astral = b.dossier_for(supplier, "ResMed Astral 150")
    alert = {"company": "ResMed", "url": "https://www.gov.uk/x", "issuedDate": "2026-08-17",
             "title": "ResMed Astral 100 and 150 ventilators: interruption of ventilation"}
    with_store("mhra-alerts.json", {"alerts": [alert]}, b.add_regulatory)
    check(not any(s.startswith("mhra") for s in airsense.sources),
          "an alert naming only the company attached to a product it never names")
    check(any(s.startswith("mhra") for s in astral.sources),
          "an alert naming the product failed to attach to it")


def test_shifted_catalogue_row_skipped():
    """A column-shifted catalogue card must not publish a supplier name or an
    MPC as a product description (ELA679, FDQ3419 on 28/09/2026)."""
    b = B.Builder("wound")
    d = b.dossier_for("ACME", "Cuticell Contact", npc="ELA679")
    good = b.dossier_for("ACME", "Other", npc="ELA838")
    rows = [
        {"name": "SUSPENDED", "supplier": "Cuticell Contact", "desc": "ESSITY UK TENA HM",
         "npc": "ELA679", "mpc": "ELA679", "pack": "Pack of 5"},
        {"name": "DRAEGER MEDICAL", "supplier": "Facemask anaesthetic", "desc": "MP01514",
         "npc": "ELA679", "mpc": "ELA679", "pack": "Box of 20"},
        {"name": "ActivHeal", "supplier": "ADVANCED MEDICAL SOLUTIONS (PLYMOUTH)LTD",
         "desc": "Foam dressing silicone including adhesive border 10cm x 10cm",
         "npc": "ELA838", "mpc": "10012556", "pack": "Carton of 10"},
    ]
    with_store("nhssc-cache.json", {"products": {"q": {"items": rows}}}, b.add_catalogue)
    check("nhssc" not in d.sources, "a column-shifted catalogue row reached a dossier")
    check("nhssc" in good.sources, "a well-formed catalogue row was dropped")


def test_tariff_price_is_pounds():
    """NHSBSA publishes Part IX prices in pence (dm+d glossary). 666 is £6.66,
    never "£666" - the hundredfold overstatement this pins."""
    check(B.pounds_from_pence("666") == "£6.66", "666p must read £6.66")
    check(B.pounds_from_pence("17") == "£0.17", "17p must read £0.17")
    check(B.pounds_from_pence("") is None, "a blank price must publish nothing")
    path = os.path.join(REPO, "data", "product-dossiers-wound.json")
    tariff = json.load(open(os.path.join(REPO, "data", "drug-tariff-part-ix.json")))
    ix = {n: i for i, n in enumerate(tariff["schema"])}
    raw = {}
    for r in tariff["rows"]:                  # one AMP can list several pack sizes
        if r[ix["price"]]:
            raw.setdefault(r[ix["amp"]], set()).add(B.pounds_from_pence(r[ix["price"]]))
    seen = 0
    for d in json.load(open(path)).get("dossiers") or []:
        for ob in d["fields"].get("Drug Tariff price", []):
            amp = ob.get("variant") or ""
            if amp in raw:
                seen += 1
                if not check(ob["value"] in raw[amp],
                             "%s: tariff price %s for %r, the tariff lists %s"
                             % (d["key"], ob["value"], amp, sorted(raw[amp]))):
                    return
    check(seen > 0, "no published tariff price could be matched back to its tariff row")


def test_dermatology_tariff_anchor():
    """Dermatology is anchored on the Drug Tariff (30/09/2026): every BNF 21.22
    line reaches a dossier, the scope is NHSBSA's BNF section and never a
    keyword, each dossier states it is an emollient, and every price names the
    pack it belongs to (a 100g and a 500g price on one dossier are otherwise
    indistinguishable)."""
    path = os.path.join(REPO, "data", "product-dossiers-dermatology.json")
    if not check(os.path.exists(path), "product-dossiers-dermatology.json is missing"):
        return
    store = json.load(open(path))
    tariff = json.load(open(os.path.join(REPO, "data", "drug-tariff-part-ix.json")))
    ix = {n: i for i, n in enumerate(tariff["schema"])}
    rows = [r for r in tariff["rows"] if str(r[ix["bnf"]]).startswith("2122")]
    check(len(rows) > 100, "only %d BNF 21.22 rows in the tariff copy" % len(rows))
    want = {}
    for r in rows:
        label = "%s, %s %s" % (r[ix["amp"]], r[ix["qty"]], r[ix["uom"]])
        want[label] = B.pounds_from_pence(r[ix["price"]])
    got = {}
    for d in store.get("dossiers") or []:
        for ob in d["fields"].get("Drug Tariff price", []):
            got[ob.get("variant")] = ob["value"]
            if not check(d.get("productType") == "emollient",
                         "%s carries a tariff price but no stated productType" % d["key"]):
                return
    missing = sorted(set(want) - set(got))
    check(not missing, "%d BNF 21.22 tariff lines reached no dossier, e.g. %s"
          % (len(missing), missing[:3]))
    wrong = [k for k in want if k in got and got[k] != want[k]]
    check(not wrong, "tariff price mismatch for %s" % wrong[:3])
    extra = sorted(set(got) - set(want))
    check(not extra, "a priced variant outside BNF 21.22 reached the emollient set: %s" % extra[:3])
    # Scope is the BNF section: a row with an emollient-sounding name outside
    # 21.22 (Fontus's AproDerm barrier cream is Part IXC ostomy) must stay out.
    check(not any("barrier cream" in (k or "").lower() for k in got),
          "an ostomy barrier cream was filed as an emollient")


for fn in (test_size_stripping, test_longest_family_wins, test_tariff_price_is_pounds,
           test_published_store, test_no_silent_merge,
           test_antimicrobial_variant_never_joins_plain_family,
           test_alert_needs_a_product_word, test_shifted_catalogue_row_skipped,
           test_dermatology_tariff_anchor):
    try:
        fn()
    except Exception as exc:                                        # noqa: BLE001
        failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))

if failures:
    print("PRODUCT DOSSIER GATE FAILED (%d of %d checks)" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("product dossier gate passed: %d checks" % checks)
