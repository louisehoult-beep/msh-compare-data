#!/usr/bin/env python3
"""
Build one dossier per product, gathering every source the Hub holds about it.

WHY
---
The Hub holds product facts in six different files, each written by a different
job, each keyed differently, and none of them aware of the others. A member
comparing two dressings sees whichever single file the tool happened to read.
This builds the join: one record per product, carrying EVERY source that says
anything about it, with the source named against every value.

THE POINT IS NOT TO MERGE THE SOURCES. IT IS TO SHOW THEM TOGETHER.
-------------------------------------------------------------------
Where two sources disagree - the manufacturer's page says "up to 7 days" and NHS
Supply Chain's clinical matrix says "-" - BOTH are published, side by side, each
labelled. Picking a winner would be inventing a fact neither source states, and
the disagreement is itself the intelligence: it is exactly what a rep needs to
know before quoting a number in front of a clinician.

So there is no "value" field anywhere in the output. There is a list of
observations, each with what was said, who said it, when it was captured, and a
link to where it came from.

THE JOIN RULE (root rule 14: state the rule in the file)
--------------------------------------------------------
Two records describe the same product when EITHER:

  (a) they carry the same NPC - NHS Supply Chain's own catalogue code, which is
      the only genuine product identifier in any of these sources; or
  (b) their supplier resolves, through the Hub's alias registry, to the same
      company AND their normalised product names are identical.

Anything weaker is NOT merged. Two dressings from one supplier whose names share
a prefix are routinely different products with different absorbency, and merging
them would publish one product's specification under another's name.

BRAND FAMILIES - THE REASON THE SOURCES LOOK LIKE THEY DON'T MATCH
------------------------------------------------------------------
The sources name products at different grains, and this is the single thing that
makes a naive join produce almost nothing:

  ICC matrix     Brand "ActivHeal", "Allevyn Gentle Border Lite"  - the RANGE,
                 with the variant carried in the Description and the NPC
  manufacturer   "ActivHeal Silicone Foam Border"                 - the VARIANT
  Drug Tariff    "Tegaderm Foam dressing (adhesive) 10cm x 11cm"  - the variant
                 PLUS the pack size

So a brand-family layer sits underneath the join. Families are taken from the
ICC matrices' own Brand column - NHS Supply Chain's naming of its own ranges,
not something invented here - and a record belongs to the LONGEST family whose
name its own normalised name begins with.

A family link is NOT a claim that two records are the same product. ICC
observations reaching a dossier through its family are marked scope "family" and
carry the NPC and description of the exact variant NHS Supply Chain measured, so
a reader sees "these are the measurements for this range, on these variants" and
never "this is your product's absorbency". Observations that reached a dossier
by its own NPC are marked scope "product". The tool must show the difference.

Supplier resolution is company_match.py's, unchanged: confirmed, ambiguous or
unmatched, never a best guess. An unresolved supplier does not stop a dossier
being built - it means the dossier cannot be joined by rule (b), and says so.

WHAT COUNTS AS A SOURCE, AND WHAT KIND OF FACT IT IS
-----------------------------------------------------
Every observation is tagged with the KIND of fact it is, because these are not
equivalent and a reader must not treat them as though they were:

  independent   NHS Supply Chain's Information for Clinical Choice matrices.
                Specifications measured the same way across every supplier in a
                category, authored with NHS clinical stakeholders. The only
                genuinely like-for-like source here.
  catalogue     The NHS Supply Chain catalogue entry - codes, pack, price basis,
                availability status. Fact about the listing, not the product.
  manufacturer  The supplier's own product page. Their words about their own
                product. Useful, and never independent.
  tariff        NHSBSA Drug Tariff Part IX. What is reimbursable in primary care,
                at what price. A listing fact, like the catalogue.
  regulatory    MHRA field safety notices and alerts.

Usage:
    python3 scripts/build_product_dossiers.py --speciality wound
    python3 scripts/build_product_dossiers.py --speciality wound --report
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match                                                # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")


def load(name, default=None):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path) as fh:
        return json.load(fh)


def nk(s):
    """Normalise a PRODUCT name. Deliberately gentler than company_match.key():
    a product name's trailing words are part of its identity ("Border", "Lite",
    "Ag"), so nothing is stripped - only case and punctuation are levelled."""
    s = str(s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


NPC_RE = re.compile(r"^[A-Z]{3}\d{2,5}$")

# A trailing dimension on a Drug Tariff appliance name is the PACK, not part of
# the product's identity: "Tegaderm Foam dressing (adhesive) 10cm x 11cm oval"
# is the same product as the 14.3cm one. Stripping it is not fuzzy matching -
# it removes a measurement, and what is removed is kept and published as the
# variant so nothing is lost.
SIZE_RE = re.compile(
    r"\s*\b\d+(?:\.\d+)?\s*(?:cm|mm|m|g|ml|inch|in)\b\s*(?:x\s*\d+(?:\.\d+)?\s*"
    r"(?:cm|mm|m|inch|in)\b\s*)*.*$", re.I)


def strip_size(name):
    """('Tegaderm Foam dressing (adhesive)', '10cm x 11cm oval')"""
    s = str(name or "").strip()
    m = SIZE_RE.search(s)
    if not m:
        return s, ""
    return s[:m.start()].strip(" -,"), s[m.start():].strip()

# ---------------------------------------------------------------------------
# Speciality scoping.
#
# Wound care is defined by the Hub's OWN vocabulary (differentiator `wound:*`)
# plus the six ICC categories that are wound care, named explicitly rather than
# keyword-matched. A keyword sweep for "wound" pulls in wound-closure staplers
# and surgical drapes; naming the categories cannot drift.
# ---------------------------------------------------------------------------
SPECIALITIES = {
    "wound": {
        "differentiator_prefix": "wound:",
        "icc_categories": [
            "Foam Dressings",
            "Gelling Fibres",
            "Silicone Wound Contact",
            "Non Silicone Wound Contact",
            "Antimicrobial Wound Contact",
            "NPWT",
        ],
        # Drug Tariff Part IX is organised by appliance part, not speciality.
        # IXA is the dressings part; these terms are the MIE's own wound-care
        # filter, and the exclusions are the categories that also sit under IXA
        # and would otherwise dominate it (see 01-WOUND-CARE-POC.md section 6).
        "tariff_parts": ["IXA"],
        "tariff_include": [
            "dressing", "bandage", "gauze", "foam", "alginate", "hydrocolloid",
            "hydrogel", "hydrofiber", "hydrofibre", "silicone", "film",
            "absorbent", "compression", "wound", "tulle", "paraffin", "honey",
            "silver", "collagen", "charcoal", "swab", "pad",
        ],
        "tariff_exclude": [
            "lymphoedema", "garment", "stocking", "catheter", "sensor",
            "pen needle", "lancet", "test strip", "stoma", "ostomy", "truss",
        ],
    },
}


class Dossier:
    """One product, and everything every source says about it."""

    def __init__(self, supplier, name, supplier_state):
        self.supplier = supplier
        self.name = name
        self.supplier_state = supplier_state
        self.family = None
        self.npcs = {}            # npc -> set of source ids that gave it
        self.mpcs = {}
        self.observations = []    # every fact, with its source
        self.sources = {}         # source id -> its provenance block
        self.candidates = set()   # near-name links, never merged
        self.categories = set()

    @property
    def key(self):
        return "%s|%s" % (self.supplier, nk(self.name))

    def add_source(self, sid, block):
        if sid not in self.sources:
            self.sources[sid] = block

    def observe(self, sid, field, value, npc=None, scope="product", variant=None):
        if value is None:
            return
        value = str(value).strip()
        if not value:
            return
        ob = {"field": field, "value": value, "source": sid, "scope": scope}
        if npc:
            ob["npc"] = npc
        if variant:
            ob["variant"] = variant
        if ob in self.observations:
            return
        self.observations.append(ob)

    def to_json(self):
        # Group observations by field so the tool can show one row per
        # specification with every source's answer under it. Sources that agree
        # are still listed separately - "both said it" is a stronger fact than
        # "one said it", and collapsing them would hide that.
        by_field = collections.OrderedDict()
        for ob in self.observations:
            by_field.setdefault(ob["field"], []).append(
                {k: v for k, v in ob.items() if k != "field"})
        return {
            "key": self.key,
            "name": self.name,
            "supplier": self.supplier,
            "supplierResolved": self.supplier_state == "confirmed",
            "supplierResolution": self.supplier_state,
            "npc": sorted(self.npcs),
            "mpc": sorted(self.mpcs),
            "family": self.family,
            "categories": sorted(self.categories),
            "sourceCount": len(self.sources),
            "sources": self.sources,
            "fields": by_field,
            "familyMembers": sorted(self.candidates),
        }


class Builder:
    def __init__(self, speciality):
        self.spec = SPECIALITIES[speciality]
        self.speciality = speciality
        seed = load("supplier-seed.json", {"suppliers": []})
        self.index = company_match.build_index(seed)
        self.by_key = {}          # supplier|name -> Dossier
        self.by_npc = {}          # npc -> Dossier
        # supplier -> [family names, longest first]. Filled by add_icc() from the
        # ICC matrices' own Brand column; see the module docstring.
        self.families = collections.defaultdict(list)
        self.stats = collections.Counter()

    # -- supplier resolution ------------------------------------------------
    def resolve_supplier(self, raw):
        company, state, _reason = company_match.resolve(raw, self.index)
        self.stats["supplier_" + state] += 1
        return (company or str(raw or "").strip() or "Unknown supplier"), state

    def note_family(self, supplier, brand):
        if not brand:
            return
        fam = self.families[supplier]
        if brand not in fam:
            fam.append(brand)
            fam.sort(key=lambda b: -len(nk(b)))

    def family_of(self, supplier, name):
        """The longest ICC brand family this product's name begins with.

        Longest-first, so "Allevyn Gentle Border Lite" wins over "Allevyn
        Gentle" for a product that is one - taking the shorter would file a Lite
        dressing under the standard one's measurements.
        """
        n = nk(name)
        for brand in self.families.get(supplier, []):
            b = nk(brand)
            if b and (n == b or n.startswith(b + " ")):
                return brand
        return None

    # -- the join -----------------------------------------------------------
    def dossier_for(self, raw_supplier, name, npc=None):
        """Find or make the dossier for this record, applying the join rule."""
        if npc and npc in self.by_npc:
            self.stats["joined_by_npc"] += 1
            return self.by_npc[npc]

        supplier, state = self.resolve_supplier(raw_supplier)
        key = "%s|%s" % (supplier, nk(name))
        d = self.by_key.get(key)
        if d is None:
            d = Dossier(supplier, str(name).strip(), state)
            self.by_key[key] = d
            self.stats["dossiers_created"] += 1
        else:
            self.stats["joined_by_name"] += 1
        if npc:
            self.by_npc.setdefault(npc, d)
            d.npcs.setdefault(npc, set())
        return d

    # -- sources ------------------------------------------------------------
    def add_icc(self):
        store = load("icc-matrices.json", {"matrices": {}})
        wanted = set(self.spec["icc_categories"])
        for cat, matrix in (store.get("matrices") or {}).items():
            if cat not in wanted:
                continue
            sid = "icc:" + cat
            block = {
                "id": sid,
                "kind": "independent",
                "name": "NHS Supply Chain — Information for Clinical Choice",
                "detail": cat,
                "issued": matrix.get("issued"),
                "url": matrix.get("source_url"),
                "listingStatus": matrix.get("listing_status"),
                "authority": ("Authored by NHS Supply Chain's Clinical Collaboration "
                              "Teams with NHS clinical stakeholders."),
            }
            for p in matrix.get("products") or []:
                npc = (p.get("NPC") or "").strip()
                if not NPC_RE.match(npc):
                    continue
                brand = p.get("Brand") or p.get("Description") or npc
                d = self.dossier_for(p.get("Supplier"), brand, npc)
                self.note_family(d.supplier, brand)
                d.family = d.family or brand
                d.add_source(sid, block)
                d.npcs.setdefault(npc, set()).add(sid)
                if p.get("MPC"):
                    d.mpcs.setdefault(p["MPC"], set()).add(sid)
                d.categories.add(cat)
                # The ICC Brand is the range, so one dossier legitimately holds
                # several NPCs. Each observation carries the variant's own
                # description as well as its NPC, or a reader cannot tell which
                # of five ActivHeal dressings an absorbency figure belongs to.
                variant = p.get("Description") or npc
                for field, value in p.items():
                    if field.startswith("_") or field in ("Supplier", "Brand", "NPC", "MPC"):
                        continue
                    d.observe(sid, field, value, npc, variant=variant)
                self.stats["icc_rows"] += 1

    def add_manufacturer(self):
        store = load("supplier-product-detail.json", {"products": {}})
        wanted = self.wound_manufacturer_keys()
        for key, rec in (store.get("products") or {}).items():
            if key not in wanted:
                continue
            sid = "manufacturer:" + (rec.get("supplier") or "")
            d = self.dossier_for(rec.get("supplier"), rec.get("product"))
            d.family = d.family or self.family_of(d.supplier, d.name)
            d.add_source(sid, {
                "id": sid,
                "kind": "manufacturer",
                "name": rec.get("supplier"),
                "detail": "the supplier's own product page",
                "captured": rec.get("capturedDate"),
                "url": rec.get("sourceUrl"),
                "authority": ("The manufacturer's own words about its own product. "
                              "Not independently verified."),
            })
            d.observe(sid, "Description", rec.get("description"))
            for f in (rec.get("features") or [])[:12]:
                d.observe(sid, "Features", f)
            specs = rec.get("specs") or {}
            for field, value in specs.items():
                if field.startswith("_"):
                    continue
                if isinstance(value, list):
                    for v in value:
                        d.observe(sid, field, v)
                else:
                    d.observe(sid, field, value)
            if specs:
                d.sources[sid]["specsCaptured"] = specs.get("_capturedDate") or rec.get("capturedDate")
                d.sources[sid]["specsUrl"] = specs.get("_sourceUrl") or rec.get("sourceUrl")
            self.stats["manufacturer_rows"] += 1

    def wound_manufacturer_keys(self):
        """Manufacturer records in this speciality, per the Hub's own vocabulary.

        Membership comes from differentiator.json's gated category - the same
        rule the Differentiator publishes under - never from a keyword sweep of
        product names, which files wound-closure staplers as wound care.
        """
        diff = load("differentiator.json", {"products": []})
        prefix = self.spec["differentiator_prefix"]
        keys = set()
        for p in diff.get("products") or []:
            if not str(p.get("cat") or "").startswith(prefix):
                continue
            keys.add("%s|%s" % (p.get("supplier"), nk(p.get("name"))))
            self.stats["differentiator_in_speciality"] += 1
        return keys

    def add_catalogue(self):
        store = load("nhssc-cache.json", {"products": {}})
        sid = "nhssc"
        block = {
            "id": sid,
            "kind": "catalogue",
            "name": "NHS Supply Chain catalogue",
            "detail": "the public catalogue entry",
            "url": "https://www.supplychain.nhs.uk/",
            "authority": ("What NHS Supply Chain lists and how it is packed. A fact "
                          "about the listing, not a measurement of the product."),
        }
        for _q, rec in (store.get("products") or {}).items():
            for item in rec.get("items") or []:
                npc = (item.get("npc") or "").strip()
                # Catalogue lines only attach to a product a richer source has
                # already established. The catalogue alone cannot tell us which
                # brand a line belongs to, and guessing would invent products.
                d = self.by_npc.get(npc)
                if not d:
                    continue
                d.add_source(sid, block)
                d.npcs.setdefault(npc, set()).add(sid)
                if item.get("mpc"):
                    d.mpcs.setdefault(item["mpc"], set()).add(sid)
                d.observe(sid, "Catalogue description", item.get("desc"), npc)
                d.observe(sid, "Pack", item.get("pack"), npc)
                if item.get("status"):
                    d.observe(sid, "Catalogue status", item.get("status"), npc)
                self.stats["catalogue_rows"] += 1

    def add_tariff(self):
        store = load("drug-tariff-part-ix.json")
        if not store:
            return
        schema = store.get("schema") or []
        try:
            i_part, i_sup, i_amp = (schema.index("part"), schema.index("supplier"),
                                    schema.index("amp"))
            i_qty, i_uom, i_price = (schema.index("qty"), schema.index("uom"),
                                     schema.index("price"))
        except ValueError:
            return
        parts = set(self.spec["tariff_parts"])
        inc = self.spec["tariff_include"]
        exc = self.spec["tariff_exclude"]
        sid = "drug-tariff"
        block = {
            "id": sid,
            "kind": "tariff",
            "name": "NHSBSA Drug Tariff Part IX",
            "detail": "Part %s, %s" % ("/".join(sorted(parts)), store.get("effectiveMonth") or ""),
            "url": store.get("sourcePage"),
            "asOf": store.get("dataAsOf"),
            "authority": ("What is reimbursable in primary care and at what price. "
                          "A listing fact, not a measurement of the product."),
        }
        for row in store.get("rows") or []:
            if row[i_part] not in parts:
                continue
            hay = (str(row[i_amp]) + " " + str(row[2] if len(row) > 2 else "")).lower()
            if not any(t in hay for t in inc) or any(t in hay for t in exc):
                continue
            # Tariff lines carry no NPC, so they join by rule (b) or by brand
            # family. The pack size is stripped off the appliance name first -
            # it is the pack, not the product - and kept as the variant, so a
            # reader still sees exactly which line the price belongs to.
            supplier, _state = self.resolve_supplier(row[i_sup])
            base, variant = strip_size(row[i_amp])
            d = (self.by_key.get("%s|%s" % (supplier, nk(row[i_amp])))
                 or self.by_key.get("%s|%s" % (supplier, nk(base))))
            scope = "product"
            if d is None:
                fam = self.family_of(supplier, base)
                if fam:
                    d = self.by_key.get("%s|%s" % (supplier, nk(fam)))
                    scope = "family"
            if d is None:
                self.stats["tariff_unmatched"] += 1
                continue
            label = " ".join(x for x in (base, variant) if x)
            d.add_source(sid, block)
            if row[i_price]:
                d.observe(sid, "Drug Tariff price", "£%s" % row[i_price],
                          scope=scope, variant=label)
            d.observe(sid, "Drug Tariff pack", "%s %s" % (row[i_qty], row[i_uom]),
                      scope=scope, variant=label)
            self.stats["tariff_rows"] += 1

    def link_families(self):
        """Cross-attach ICC measurements across a brand family, clearly marked.

        A dossier that has no independent specification of its own, but whose
        family NHS Supply Chain HAS measured, gets those measurements marked
        scope "family" and carrying the NPC and description of the exact variant
        measured. That is a genuinely different statement from "this is your
        product's absorbency", and the renderer must keep saying so.
        """
        by_family = collections.defaultdict(list)
        for d in self.by_key.values():
            if d.family:
                by_family[(d.supplier, d.family)].append(d)

        for (_supplier, _family), group in by_family.items():
            donors = [d for d in group
                      if any(s.get("kind") == "independent" for s in d.sources.values())]
            if not donors:
                continue
            for d in group:
                for other in group:
                    if other is not d:
                        d.candidates.add(other.key)
                if d in donors:
                    continue
                for donor in donors:
                    for sid, block in donor.sources.items():
                        if block.get("kind") != "independent":
                            continue
                        d.add_source(sid, block)
                        for ob in donor.observations:
                            if ob["source"] != sid:
                                continue
                            d.observe(sid, ob["field"], ob["value"], npc=ob.get("npc"),
                                      scope="family",
                                      variant=donor.name)
                            self.stats["family_observations_attached"] += 1

    def build(self):
        self.add_icc()            # first: establishes NPC -> product
        self.add_manufacturer()
        self.add_catalogue()      # attaches to NPCs the ICC pass established
        self.add_tariff()
        self.link_families()
        return self

    def output(self):
        dossiers = [d.to_json() for d in self.by_key.values()]
        # Most-evidenced first: a product three sources describe is the one a
        # member gets most from, and it makes a thin dossier visibly thin.
        dossiers.sort(key=lambda x: (-x["sourceCount"], x["name"].lower()))
        multi = sum(1 for d in dossiers if d["sourceCount"] > 1)
        return {
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "speciality": self.speciality,
            "joinRule": (
                "Two records describe the same product when either they carry the same "
                "NPC, or their supplier resolves to the same Hub company AND their "
                "normalised product names are identical. A name that merely contains "
                "another is recorded as a candidate link and never merged."
            ),
            "readingRule": (
                "Sources are shown side by side, never merged into one value. Where two "
                "sources disagree, both are published with their own attribution — the "
                "disagreement is the intelligence. Only the 'independent' source (NHS "
                "Supply Chain's Information for Clinical Choice) measures every supplier "
                "the same way; 'manufacturer' is each supplier's own words about its own "
                "product."
            ),
            "counts": {
                "dossiers": len(dossiers),
                "withMoreThanOneSource": multi,
                "withIndependentSpec": sum(
                    1 for d in dossiers
                    if any(s.get("kind") == "independent" for s in d["sources"].values())),
            },
            "dossiers": dossiers,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speciality", default="wound", choices=sorted(SPECIALITIES))
    ap.add_argument("--report", action="store_true", help="print the build stats")
    args = ap.parse_args()

    b = Builder(args.speciality).build()
    out = b.output()
    path = os.path.join(DATA, "product-dossiers-%s.json" % args.speciality)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    print("wrote %s" % os.path.relpath(path, REPO))
    print("  dossiers                : %d" % out["counts"]["dossiers"])
    print("  with >1 source          : %d" % out["counts"]["withMoreThanOneSource"])
    print("  with an independent spec: %d" % out["counts"]["withIndependentSpec"])
    if args.report:
        print("\n  build stats:")
        for k, v in sorted(b.stats.items()):
            print("    %-34s %d" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
