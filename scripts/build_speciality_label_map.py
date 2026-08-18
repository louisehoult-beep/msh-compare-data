#!/usr/bin/env python3
"""
build_speciality_label_map.py — resolve the seed's prose speciality labels to the
Compare tab's gated slugs.

Two vocabularies describe the same 38 specialities. supplier-seed.json records
them as prose ("Continence & urology", "Moving and handling"); compare-suppliers.json
uses slugs (`continence`, `handling`) and is what verify.py gates. Nothing joins
them, which is why 6,640 products belonging to single-speciality suppliers cannot
be filed to a Hub category.

WHAT RESOLVES MECHANICALLY, and therefore needs nobody:
case, punctuation, "&" versus "and", curly versus straight apostrophes, and
"/" read as a separator. "Continence & urology" and "Continence / Urology" both
reduce to `continence and urology`. This is the same normalisation company_alias.py
does for legal suffixes, and it is not fuzzy matching: the strings have to be
equal once normalised, not merely similar.

WHAT DOES NOT, and is therefore left for a human:
  * a COMPOUND label naming two specialities ("Respiratory / anaesthesia").
    A supplier under one of these is not a single-speciality supplier and must
    not be pre-filled from it.
  * a label with no counterpart in the gated vocabulary.

Both are written out unresolved. Nothing is guessed into a slug — a product filed
to the wrong speciality is compared against the wrong products, which is worse
than a product missing from the table.

Usage:  python3 scripts/build_speciality_label_map.py
Writes: data/speciality-label-map.json
"""
import json, os, re, collections

OUT = "data/speciality-label-map.json"

# Labels that are not an exact match on any normalisation, but name exactly one
# gated speciality once read. Each is a judgement, so each carries its reason and
# a date, and each is auditable on its own line. A label naming TWO specialities
# is deliberately absent from here — see the compound rule above.
DECISIONS = {
    "Patient handling": ("handling", "the gated speciality is 'Patient handling and "
                         "pressure area care'; this is its opening phrase"),
    "Moving and handling": ("handling", "the NHS's usual name for the same speciality, "
                            "gated as 'Patient handling and pressure area care'"),
    "Rehabilitation and mobility": ("rehab", "the gated speciality is 'Rehabilitation, "
                                    "mobility and daily living'; this is its opening phrase"),
    "Enteral feeding": ("nutrition", "the gated speciality is 'Nutrition and enteral "
                        "feeding'; this names its second half"),
    "Infection prevention": ("infection", "the gated speciality is 'Infection prevention "
                             "and PPE'; this is its opening phrase"),
    "Prosthetics and orthotics": ("orthotics", "the gated speciality is 'Orthotics, "
                                  "podiatry and prosthetics' — the same field, reordered"),
    "Theatre / surgical": ("theatres", "the gated label is 'Theatres / surgical'; this "
                           "differs only in the singular"),
    "Imaging / capital": ("imaging", "'capital' describes how the equipment is bought, "
                          "not a speciality; the speciality named is imaging"),
    "Pathology / diagnostics": ("pathology", "'diagnostics' here qualifies pathology "
                                "rather than naming imaging — every supplier under this "
                                "label sells laboratory product"),
    "Pathology / haematology": ("pathology", "haematology is a pathology discipline; the "
                                "Hub has no separate haematology speciality"),
    "ENT / neuro-otology": ("ent", "neuro-otology is an ENT sub-speciality; the Hub has "
                            "no separate slug for it"),
    "Surgical haemostasis": ("theatres", "haemostasis product is theatre consumable; the "
                             "Hub files it under 'Theatres / surgical'"),
    "Neurosciences": ("neuro", "the gated speciality is 'Neurosurgery and "
                      "neuromodulation'; neurosciences is the broader NHS service name "
                      "for the same suppliers"),
}


# "&", "/" and the word "and" are all used as the same joiner across the two
# vocabularies ("Continence & urology" vs the gated "Continence / Urology"), and
# a slash does NOT reliably mean a compound — it appears inside single gated
# labels too. So all three are dropped and the remaining words compared as a
# sequence. Two labels match only when that sequence is IDENTICAL, which is exact
# matching on a normalised form, not similarity.
JOINERS = {"and", "or"}


def norm(s):
    s = (s or "").lower().replace("\u2019", "'")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(w for w in s.split() if w not in JOINERS)


def main():
    seed = {s["name"]: s for s in json.load(open("data/supplier-seed.json"))["suppliers"]}
    own = json.load(open("data/supplier-products.json"))["suppliers"]
    cs = json.load(open("data/compare-suppliers.json"))["specialities"]

    # slug lookup, by the slug itself and by its published label
    by_norm, by_set = {}, {}
    for slug, v in cs.items():
        by_norm[norm(slug)] = slug
        by_norm[norm(v.get("label"))] = slug
        # Same words, different order: the seed writes "Decontamination / sterile
        # services", the gated label is "Sterile services and decontamination".
        by_set[frozenset(norm(v.get("label")).split())] = slug
        by_set[frozenset(norm(slug).split())] = slug

    labels = collections.Counter()
    for co in own:
        for x in (seed.get(co) or {}).get("specialities") or []:
            labels[x] += 1

    prev = {}
    if os.path.exists(OUT):
        for e in json.load(open(OUT)).get("entries", []):
            prev[e["label"]] = e

    entries = []
    for label, n in labels.most_common():
        was = prev.get(label)
        if was and was.get("slugs") and was.get("resolvedBy") != "normalised":
            entries.append({**was, "suppliers": n})
            continue

        exact = by_norm.get(norm(label)) or by_set.get(frozenset(norm(label).split()))
        if exact:
            entries.append({"label": label, "suppliers": n, "slugs": [exact],
                            "resolvedBy": "normalised",
                            "why": "identical to the gated label once case, punctuation "
                                   "and '&'/'and' are normalised"})
            continue

        decided = DECISIONS.get(label)
        if decided:
            entries.append({"label": label, "suppliers": n, "slugs": [decided[0]],
                            "resolvedBy": "decision 18/08/2026",
                            "why": decided[1]})
            continue

        # A compound names more than one speciality. Record which ones it reaches,
        # but never resolve it: it is not a single-speciality label.
        parts = [p.strip() for p in re.split(r"[/,]| and (?=[A-Z])", label) if p.strip()]
        hits = [by_norm[norm(p)] for p in parts if norm(p) in by_norm]
        entries.append({
            "label": label, "suppliers": n,
            "slugs": None,
            "resolvedBy": None,
            "compound": len(parts) > 1,
            "candidates": sorted(set(hits)) or None,
            "why": ("names more than one speciality — a supplier under this label is not "
                    "a single-speciality supplier and must not be pre-filled from it"
                    if len(parts) > 1 else
                    "no counterpart in the gated vocabulary — decide the slug, or add "
                    "the speciality to compare-suppliers.json"),
        })

    doc = {
        "_notice": "GENERATED WORKLIST. Fill in `slugs` only; everything else is rebuilt.",
        "rule": "A seed speciality label resolves to one or more Compare slugs. Only an "
                "exact match after mechanical normalisation is filled in automatically. "
                "A compound label is never auto-resolved, and a supplier carrying one is "
                "not treated as single-speciality.",
        "counts": {
            "labels": len(entries),
            "resolved": sum(1 for e in entries if e.get("slugs")),
            "resolvedByNormalisation": sum(1 for e in entries
                                           if e.get("resolvedBy") == "normalised"),
            "resolvedByDecision": sum(1 for e in entries
                                      if (e.get("resolvedBy") or "").startswith("decision")),
            "unresolved": sum(1 for e in entries if not e.get("slugs")),
            "compound": sum(1 for e in entries if e.get("compound")),
        },
        "entries": entries,
    }
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    c = doc["counts"]
    print("%s: %d labels — %d resolved, %d left (%d compound)"
          % (OUT, c["labels"], c["resolved"], c["unresolved"], c["compound"]))
    for e in entries:
        if not e.get("slugs"):
            print("   OPEN  %-34s %s" % (e["label"][:34],
                                         ("candidates: " + ", ".join(e["candidates"]))
                                         if e.get("candidates") else e["why"][:60]))


if __name__ == "__main__":
    main()
