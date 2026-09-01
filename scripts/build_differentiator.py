#!/usr/bin/env python3
"""
build_differentiator.py — one product record, built from every source that
describes it, filed in exactly one comparable category.

WHY BOTH SOURCES. NHS Supply Chain tells you what a trust can actually order:
the NPC code, the pack, whether it is still listed. It does not tell you what
distinguishes one product from another — the catalogue description is a line of
procurement shorthand. The manufacturer's own site carries the detail a rep
needs to sell against a competitor: the features, the materials, the claims. A
Differentiator built on either source alone is either unbuyable or undifferen-
tiated, so a product record here holds both, each with its own URL and the date
it was read, and neither is allowed to stand in for the other.

CATEGORY LOCK. Every published PRODUCT ROW carries exactly one `cat`, of the
form "<speciality>:<type>", from the vocabulary in data/compare-suppliers.json
that verify.py already gates. The comparison UI may only ever put two products
side by side when their `cat` is identical. That is not a UI nicety: comparing a
midline against a drainage bag produces a table where every row is "n/a", which
reads to a member as a product that fails on every measure.

MULTI-CATEGORY DIVISIONS (Lou's rule, 25/08/2026). A (supplier, division) pair's
recorded `hub` in differentiator-category-map.json can be a LIST of categories,
not just one, when the division's own evidence genuinely names products from
several — see that file's "rule" and data/differentiator-map-parts/README.md.
The lock above still holds per ROW: a division mapped to N categories publishes
its products N times, once per category, each row still locked to exactly one
`cat`. This is not "pick one" relaxed into "guess several" — an ambiguous
division with no supporting evidence for any of its plausible categories is
still held, exactly as before.

A product whose category is not known is HELD, not guessed — it goes to
`held`, is counted, and appears nowhere in the comparison. Root rule 14: an
honest empty state, never a loosened threshold.

Usage:  python3 scripts/build_differentiator.py
Writes: data/differentiator.json
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "..", "company-aliases"))

OUT = "data/differentiator.json"


def load(p):
    with open(p) as f:
        return json.load(f)


JOINERS = {"and", "or", "the", "for"}


def norm(s):
    import re as _re
    s = _re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return " ".join(s.split())


def tokens(s):
    """Normalised word set, joiners dropped. Used to match a manufacturer's own
    category against a gated type label where the two say the same thing in a
    different order ('Slings and slide sheets' vs 'Slide sheets and slings').
    Equality of the SET is still exact matching, not similarity."""
    return frozenset(w for w in norm(s).split() if w not in JOINERS)


def main():
    own = load("data/supplier-products.json")["suppliers"]
    detail = load("data/supplier-product-detail.json")["products"]
    nhssc = load("data/nhssc-cache.json")
    vocab = load("data/compare-suppliers.json")["specialities"]
    cmap = load("data/differentiator-category-map.json") if \
        os.path.exists("data/differentiator-category-map.json") else {"entries": []}
    seed = {s["name"]: s for s in load("data/supplier-seed.json")["suppliers"]}
    lmap = load("data/speciality-label-map.json") if \
        os.path.exists("data/speciality-label-map.json") else {"entries": []}
    label_slug = {e["label"]: e["slugs"][0]
                  for e in lmap.get("entries", [])
                  if e.get("slugs") and len(e["slugs"]) == 1}

    # A supplier recorded as selling into exactly ONE speciality files its products
    # to that speciality. The rule is stated, and its evidence is the supplier's own
    # seed record. A supplier whose labels reach two or more specialities is NOT
    # pre-filled: guessing which of them a given product belongs to is precisely the
    # error the category lock exists to prevent.
    # A SUPPLIER SELLS INTO SEVERAL SPECIALITIES, so its speciality is not a
    # property a product can inherit. This code used to file every product of a
    # "single-speciality" supplier to that speciality. Removed 18/08/2026, because
    # the inference is unsound twice over:
    #
    #   * 35 of the 44 suppliers it treated as single-speciality carry a
    #     _specialitiesEvidence caveat on their seed record — the speciality was
    #     read off a framework listing with no product-level evidence behind it.
    #     Interweave Textiles and Agile Medical each have 29 divisions filed under
    #     "Patient handling"; Oticon has 46 under audiology. An incomplete list
    #     propagated to every product mis-files most of them.
    #   * even a complete list would not settle it. Convatec genuinely sells into
    #     continence, wound, vascular and ostomy: the speciality of a Convatec
    #     product is a fact about the PRODUCT, not about Convatec.
    #
    # The division mapping already answers it correctly and uniformly, for
    # single- and multi-speciality suppliers alike: a division is mapped to one
    # "speciality:type", and its products take that. Nothing is inherited.
    #
    # The relationship runs the other way. A supplier's specialities are DERIVED
    # from the categories its products are mapped to — product-level evidence,
    # which is what the seed's framework-derived list is missing. See
    # scripts/report_supplier_specialities.py.

    # (supplier, division) -> "speciality:type", the recorded human decision.
    # kind="nhssc-term" entries live in this same file but are keyed on a
    # catalogue search term, not a division, and are read separately further
    # down. Excluded here explicitly rather than relying on their division
    # being null to keep them from matching.
    mapped = {(e["supplier"], e["division"]): e["hub"]
              for e in cmap.get("entries", [])
              if e.get("hub") and e.get("kind") != "nhssc-term"}

    # Every legal category, so a mapping cannot invent one.
    legal = {"%s:%s" % (s, t) for s, v in vocab.items()
             for t in (v.get("types") or {})}

    # THE TWO SOURCES ARE AT DIFFERENT GRANULARITIES, and joining them on an
    # equal product name returns nothing at all. NHS Supply Chain's cache is keyed
    # by the RANGE a rep would search for — "Nutricare", "Leaderflex", "Prolystica"
    # — while the site crawl holds individual product pages. So the join is made at
    # range level and only on a WHOLE-PHRASE match: the NHSSC range name has to
    # appear in the manufacturer's product name bounded by word breaks, under the
    # same supplier. "Multicath" matches "Multicath Expert Central Venous Catheter";
    # it does not match on a shared word or a prefix. A range shorter than four
    # characters is never matched on, because short tokens collide.
    nh_brands = {}
    for term, rec in (nhssc.get("products") or {}).items():
        co = rec.get("supplier")
        if not co:
            continue
        nh_brands.setdefault(norm(co), {}).setdefault(norm(term), []).extend(
            rec.get("items") or [])

    nh = {}
    for term, rec in (nhssc.get("products") or {}).items():
        co = rec.get("supplier")
        for it in rec.get("items") or []:
            nh.setdefault((norm(co), norm(it.get("name"))), []).append({
                "npc": it.get("npc"), "mpc": it.get("mpc"),
                "desc": it.get("desc"), "pack": it.get("pack"),
                "status": it.get("status"), "nhsscName": it.get("name"),
                "nhsscSupplier": it.get("supplier"), "term": term,
            })

    # Own-site per-product detail, keyed the same way.
    det = {}
    for rec in detail.values():
        det[(norm(rec.get("supplier")), norm(rec.get("product")))] = rec

    products, held = [], []
    hcount = collections.Counter()
    for co, rec in own.items():
        domain = rec.get("domain")
        for p in rec.get("products") or []:
            name = p.get("n")
            if not name:
                continue
            div = p.get("division") or ""
            # Falls back to a (supplier, PRODUCT NAME) match when there's no
            # division match. Needed for DHG/Talley (26/08/2026, Patient Handling
            # pre-review fix): their curated 168 (supplier, division) entries were
            # decided when the crawler mis-read attachment-sitemap pages as
            # sub-products, so `division` held what is actually the real product's
            # own name (e.g. "Dyna Form Static Air Hz"). Re-crawling against the
            # real products-sitemap.xml fixed the product list (389 real products
            # instead of 408 mostly-junk rows) but flattened it — there is no
            # division left, one product per row — so the curated decisions would
            # otherwise all miss. The curated string still equals the product's
            # own name in the fixed data, so this fallback recovers every one of
            # them without re-curating, and is a no-op for every supplier where
            # the two happen not to coincide.
            cat = mapped.get((co, div)) or mapped.get((co, name))
            # GBUK-style records already assert the speciality on the product
            # itself. Where they do AND the manufacturer's own category is one of
            # that speciality's gated types, the pair needs no separate decision:
            # the data already says it. Anything less certain is held.
            spec = p.get("s")
            if not cat and spec and p.get("category"):
                types = (vocab.get(spec, {}).get("types") or {})
                want, wantset = norm(p["category"]), tokens(p["category"])
                for key, label in types.items():
                    if norm(label) == want or (wantset and tokens(label) == wantset):
                        cat = "%s:%s" % (spec, key)
                        break

            k = (norm(co), norm(name))
            d = det.get(k)
            sources = []
            if d:
                sources.append({"kind": "manufacturer", "url": d.get("sourceUrl"),
                                "readOn": d.get("capturedDate"), "owner": co})
            n_items = list(nh.get(k) or [])
            matched_range = None
            if not n_items:
                nname = norm(name)
                for brand, items in (nh_brands.get(norm(co)) or {}).items():
                    if len(brand) < 4:
                        continue
                    if re.search(r"\b" + re.escape(brand) + r"\b", nname):
                        matched_range = brand
                        n_items = [{"npc": it.get("npc"), "mpc": it.get("mpc"),
                                    "desc": it.get("desc"), "pack": it.get("pack"),
                                    "status": it.get("status"),
                                    "nhsscName": it.get("name"),
                                    "nhsscSupplier": it.get("supplier"),
                                    "term": brand,
                                    "matchedOn": "range name, whole phrase"}
                                   for it in items]
                        break
            for it in n_items:
                sources.append({"kind": "nhssc", "npc": it["npc"],
                                "owner": "NHS Supply Chain",
                                "url": "https://my.supplychain.nhs.uk/catalogue/search?query=%s"
                                       % (it["npc"] or "")})

            base_row = {
                "supplier": co, "name": name, "domain": domain,
                "division": div, "mfrCategory": p.get("category"),
                "detail": ({"description": d.get("description"),
                            "features": d.get("features"),
                            "image": d.get("image")} if d else None),
                "nhssc": n_items or None,
                "nhsscRange": matched_range,
                "sources": sources,
            }
            if not cat:
                hcount[(co, div)] += 1
                held.append({"supplier": co, "name": name, "division": div,
                             "why": "no recorded category mapping for this "
                                    "supplier's own division"})
                continue
            # A division's own evidence can genuinely name products from several
            # categories at once (Lou's rule, 25/08/2026) — `hub` is then a LIST
            # rather than one "speciality:type". Nothing is guessed here: the same
            # physical product is published once per listed category, so it shows
            # up in every comparison it belongs in, still locked to exactly one
            # category PER ROW (see the module docstring's CATEGORY LOCK).
            cats = cat if isinstance(cat, list) else [cat]
            bad = [c for c in cats if c not in legal]
            if bad:
                held.append({"supplier": co, "name": name, "division": div,
                             "why": "mapping names a category that is not in the "
                                    "gated vocabulary: %s" % ", ".join(bad)})
                continue
            if not sources:
                held.append({"supplier": co, "name": name, "division": div,
                             "why": "no source carries this product — neither the "
                                    "manufacturer's own page nor NHSSC"})
                continue
            for c in cats:
                products.append(dict(base_row, cat=c))

    # ------------------------------------------------------------------
    # NHSSC-ONLY ROWS (added 26/08/2026, the Differentiator framework sweep).
    #
    # WHY THIS EXISTS. The loop above only ever creates a row from `own` — a
    # supplier's OWN-SITE crawl. A large medtech manufacturer routinely runs a
    # JS-rendered catalogue on a separate host, files by clinical area or
    # audience, or disallows crawling outright (root cause written up in
    # FINDINGS-2026-08-26-wound-care-pilot.md): Coloplast, Smith+Nephew,
    # Mölnlycke, Hartmann and B. Braun all sit in the NHSSC cache with real
    # items and were publishing ZERO products, because nothing ever iterated
    # the cache on its own. Fixing the crawler cannot reach these suppliers;
    # the fix is to stop requiring a crawl before an NHSSC item can publish.
    #
    # THE EVIDENCE THIS IS BUILT ON, and why it is not a guess. Every
    # speciality in compare-suppliers.json carries a human-curated
    # `suppliers[]` list, each entry with a `t` field — the type(s) that
    # supplier is confirmed to sell in that speciality, sourced (per that
    # file's own `sourceRule`) to the supplier's actual framework award, not a
    # trade summary. Two disjoint cases, and only these two publish:
    #
    #   1. THE SUPPLIER HAS EXACTLY ONE CURATED TYPE IN THIS SPECIALITY.
    #      Every NHSSC item under that supplier that has not already been
    #      published via the own-crawl path takes that type. There is nothing
    #      to disambiguate — Coloplast's `t` for wound is `['adv']` alone, so
    #      every uncrawled Coloplast wound item is an advanced dressing by the
    #      curated record, not by inference from the item's own text.
    #   2. THE SUPPLIER HAS SEVERAL CURATED TYPES. The item is assigned one
    #      only when the type's own label (e.g. "Compression") appears as a
    #      whole word in the NHSSC item's own description. A multi-type
    #      supplier's item that matches none of its types, or matches more
    #      than one, is HELD with the reason recorded — never guessed. This
    #      mirrors the existing single-division-category match a few lines
    #      above; it does not introduce a new invented keyword list.
    #
    # A supplier already producing a published row for that exact (supplier,
    # NHSSC name) pair via the own-crawl path is skipped here — this only
    # fills the gap the crawl cannot reach, never duplicates it.
    already_published_keys = {(norm(r["supplier"]), norm(r["name"])) for r in products}

    def label_tokens(label):
        return tokens(label)

    # THE (supplier, term) MAP — added 28/08/2026, data/nhssc-category-map.json.
    #
    # Until this existed, an NHSSC row could only publish when the catalogue's
    # own description text happened to literally contain the words of a curated
    # type label (the `candidates` logic further down). That gate is narrow by
    # design, and it left 976 rows held against 81 published — including most of
    # the 101 awarded suppliers this repo cannot crawl at all, whose catalogue
    # lines are the ONLY permitted route to them.
    #
    # A recorded human/agent decision, carrying its own `why`, outranks the text
    # heuristic — same precedence the division map already has over inference on
    # the own-site side. The heuristic stays as the fallback for pairs nobody has
    # judged yet, so this is purely additive: nothing that published before stops
    # publishing. A mapped category still has to be in the gated vocabulary; an
    # unmapped pair is still held, never guessed.
    # These live in differentiator-category-map.json alongside the division
    # entries, tagged kind="nhssc-term", rather than in a file of their own.
    # They are the same decision against the same gated vocabulary, differing
    # only in what identifies the row — a catalogue search term instead of a
    # heading on the supplier's website. Keeping them here means they sit under
    # that file's existing traceability marker rather than needing one of their
    # own, and there is one map to read rather than two to keep in step.
    nhssc_map = {}
    for e in cmap.get("entries", []):
        if e.get("kind") != "nhssc-term":
            continue
        hub = e.get("hub")
        if not hub or not e.get("supplier") or not e.get("term"):
            continue
        nhssc_map[(norm(e["supplier"]), norm(e["term"]))] = (
            hub if isinstance(hub, list) else [hub])

    nhssc_added, nhssc_held = 0, 0
    nhssc_from_map = 0
    for term, rec in (nhssc.get("products") or {}).items():
        co = rec.get("supplier")
        if not co:
            continue
        mapped_cats = nhssc_map.get((norm(co), norm(term)))
        for it in rec.get("items") or []:
            name = it.get("name") or term
            k = (norm(co), norm(name))
            if k in already_published_keys:
                continue
            already_published_keys.add(k)  # one row per (supplier, NHSSC name)

            desc_tok = tokens((it.get("desc") or "") + " " + name)
            # A supplier curated into ONLY ONE speciality has no other business
            # line an item could belong to instead, so its single curated type
            # (if it has one) is unambiguous without reading the item's text at
            # all — Convatec's sole curated speciality is wound, sole type
            # "adv", so every Convatec item not already published is an
            # advanced dressing by the curated record.
            #
            # A supplier curated into SEVERAL specialities cannot use a
            # name-only shortcut even where one of those specialities is
            # itself single-type: Coloplast is single-type ('adv') in wound
            # AND single-type ('stent') in oncology, so "single type in this
            # speciality" said nothing about which speciality a given item was
            # even in. Found live 26/08/2026: every one of Coloplast's 96 items
            # matched BOTH, because a shortcut then in place checked
            # type-uniqueness within a speciality, never speciality-uniqueness
            # across the supplier's whole curated list.
            #
            # The single-speciality shortcut removed same day (also 26/08/2026,
            # same sweep): a supplier's curated `t` records what it sells IN
            # THAT SPECIALITY, not what every NHSSC catalogue line bearing its
            # name actually is — Direct Healthcare Group's sole handling type
            # is 'mattress', but an uncrawled item under its name can be an
            # InFix orthopaedic locking screw or a CARTO 3 EP mapping-system
            # part, neither remotely a mattress, because NHS Supply Chain
            # catalogue search groups adjacent/unrelated lines under the same
            # brand term. Trusting supplier-name-plus-single-type alone
            # published both as "mattresses" on the live Hub. Every supplier
            # now goes through the same label-text match as the multi-
            # speciality case below — narrower, but never wrong the way the
            # bare shortcut was in either direction.
            # A RECORDED DECISION OUTRANKS THE TEXT HEURISTIC. If this
            # (supplier, term) pair carries a mapping in
            # data/nhssc-category-map.json, that mapping was made by reading the
            # catalogue's own item descriptions and carries its own `why`. It is
            # evidence, where the block below is inference, so it wins — exactly
            # as the division map outranks inference on the own-site side.
            # Illegal categories are dropped rather than trusted, so a typo in
            # the map cannot publish a category the Compare tab cannot render.
            if mapped_cats:
                good = [c for c in mapped_cats if c in legal]
                if good:
                    for cat in good:
                        nhssc_added += 1
                        nhssc_from_map += 1
                        products.append({
                            "supplier": co, "name": name,
                            "domain": (seed.get(co) or {}).get("domain"),
                            "division": "(NHS Supply Chain only)", "mfrCategory": None,
                            "detail": None,
                            "nhssc": [{"npc": it.get("npc"), "mpc": it.get("mpc"),
                                       "desc": it.get("desc"), "pack": it.get("pack"),
                                       "status": it.get("status"),
                                       "nhsscName": it.get("name"),
                                       "nhsscSupplier": it.get("supplier"),
                                       "term": term}],
                            "nhsscRange": None,
                            "sources": [{"kind": "nhssc", "npc": it.get("npc"),
                                         "owner": "NHS Supply Chain",
                                         "url": "https://my.supplychain.nhs.uk/catalogue/"
                                                "search?query=%s" % (it.get("npc") or "")}],
                            "cat": cat,
                        })
                    continue
                nhssc_held += 1
                held.append({"supplier": co, "name": name,
                             "division": "(NHS Supply Chain only)",
                             "why": "the recorded NHSSC map entry names %s, which is not in "
                                    "the gated vocabulary" % ", ".join(mapped_cats)})
                continue

            candidates = []  # (cat, why)
            for spec_key, spec_v in vocab.items():
                for sup in (spec_v.get("suppliers") or []):
                    if norm(sup.get("ref") or sup.get("co") or "") != norm(co):
                        continue
                    tlist = [t for t in (sup.get("t") or []) if t in (spec_v.get("types") or {})]
                    if not tlist:
                        continue
                    for tkey in tlist:
                        label = (spec_v["types"].get(tkey) or "")
                        ltok = label_tokens(label)
                        if ltok and ltok <= desc_tok:
                            candidates.append(("%s:%s" % (spec_key, tkey),
                                               "NHSSC description matches curated type label %r" % label))

            uniq = sorted(set(c for c, _ in candidates))
            if len(uniq) != 1:
                nhssc_held += 1
                held.append({"supplier": co, "name": name, "division": "(NHS Supply Chain only)",
                            "why": ("no curated type for this supplier in any speciality"
                                    if not candidates else
                                    "ambiguous — matches %d curated types (%s), never guessed"
                                    % (len(uniq), ", ".join(uniq)))})
                continue
            cat = uniq[0]
            if cat not in legal:
                nhssc_held += 1
                held.append({"supplier": co, "name": name, "division": "(NHS Supply Chain only)",
                            "why": "curated type resolves to a category not in the gated vocabulary: %s" % cat})
                continue
            nhssc_added += 1
            products.append({
                "supplier": co, "name": name, "domain": (seed.get(co) or {}).get("domain"),
                "division": "(NHS Supply Chain only)", "mfrCategory": None, "detail": None,
                "nhssc": [{"npc": it.get("npc"), "mpc": it.get("mpc"), "desc": it.get("desc"),
                          "pack": it.get("pack"), "status": it.get("status"),
                          "nhsscName": it.get("name"), "nhsscSupplier": it.get("supplier"),
                          "term": term}],
                "nhsscRange": None,
                "sources": [{"kind": "nhssc", "npc": it.get("npc"), "owner": "NHS Supply Chain",
                            "url": "https://my.supplychain.nhs.uk/catalogue/search?query=%s"
                                   % (it.get("npc") or "")}],
                "cat": cat,
            })
    print("  NHSSC-only rows: %d published from curated supplier/type evidence, %d held (no or ambiguous curated type)"
          % (nhssc_added, nhssc_held))
    print("    of those, %d published from the recorded (supplier, term) map" % nhssc_from_map)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # ICC JOIN — added 31/08/2026. NHS Supply Chain's Clinical Collaboration
    # Teams publish "Information for Clinical Choice" spec matrices, authored
    # with NHS clinical stakeholders. Where one covers a product we already
    # publish, that product gets an NHS-authored specification citation rather
    # than only the manufacturer's own copy.
    #
    # This is a CODE join on NPC, never a name match: both sides carry the NHS
    # Supply Chain product code, so a match is exact or it does not happen.
    #
    # ⚠️ CEILING, stated because the count looks disappointing and should:
    # NHS Supply Chain publishes ONE product matrix (Adult ECG Electrodes,
    # 108 NPCs). The other 74 ICC documents are support documents with no
    # product table to join to. So this pass can only ever reach ECG
    # electrodes until NHSSC publishes more matrices. It is wired up now so
    # that when they do, the coverage follows without another build change.
    icc_doc = load("data/icc-matrices.json")
    icc_by_npc = {}
    for _cat, _mx in (icc_doc.get("matrices") or {}).items():
        for _row in (_mx.get("products") or []):
            _npc = str(_row.get("NPC") or "").strip().upper()
            if not _npc:
                continue
            icc_by_npc.setdefault(_npc, {
                "category": _mx.get("category") or _cat,
                "issued": _mx.get("issued"),
                "sourceUrl": _mx.get("source_url"),
                "spec": {k: v for k, v in _row.items()
                         if k not in ("Supplier", "Brand", "MPC", "NPC",
                                      "Description") and str(v or "").strip()},
            })

    icc_matched = 0
    for r in products:
        seen = []
        for it in (r.get("nhssc") or []):
            npc = str(it.get("npc") or "").strip().upper()
            hit = icc_by_npc.get(npc)
            if hit and npc not in [x["npc"] for x in seen]:
                seen.append(dict(hit, npc=npc))
        if not seen:
            continue
        icc_matched += 1
        r["icc"] = seen
        for h in seen:
            r["sources"].append({
                "kind": "icc",
                "npc": h["npc"],
                "owner": "NHS Supply Chain Clinical Collaboration Teams",
                "url": h["sourceUrl"],
            })
    print("  ICC join: %d published product(s) carry an NHS-authored spec "
          "matrix (%d NPCs available across %d matrix/matrices)"
          % (icc_matched, len(icc_by_npc),
             len(icc_doc.get("matrices") or {})))
    # ------------------------------------------------------------------

    bycat = collections.Counter(r["cat"] for r in products)
    comparable = {c: n for c, n in bycat.items() if n >= 2}

    doc = {
        "_notice": "GENERATED. Do not edit by hand — run "
                   "scripts/build_differentiator.py.",
        "rule": "A product is published only when it has a recorded category from "
                "the gated vocabulary AND at least one source that carries it. "
                "Comparison is locked to a single category: two products may be "
                "put side by side only where their `cat` is identical.",
        "sources": {
            "manufacturer": "each supplier's own product pages, read by "
                            "scripts/crawl_supplier_product_detail.py",
            "nhssc": "NHS Supply Chain public catalogue, cached by "
                     "scripts/refresh_nhssc_cache.py",
            "icc": "NHS Supply Chain 'Information for Clinical Choice' product "
                   "matrices, authored by their Clinical Collaboration Teams "
                   "with NHS clinical stakeholders, captured by "
                   "scripts/refresh_icc.py. Joined on the NPC code only. "
                   "NHSSC publishes one such matrix today, so coverage is "
                   "limited to that category by the source, not by this join.",
        },
        "counts": {
            "published": len(products),
            "held": len(held),
            "categories": len(bycat),
            "comparableCategories": len(comparable),
            "withBothSources": sum(1 for r in products
                                   if r["detail"] and r["nhssc"]),
            "manufacturerOnly": sum(1 for r in products
                                    if r["detail"] and not r["nhssc"]),
            "nhsscOnly": sum(1 for r in products
                             if r["nhssc"] and not r["detail"]),
            "withIccSpecMatrix": icc_matched,
        },
        "byCategory": dict(sorted(bycat.items())),
        "products": products,
        "held": held[:2000],
        "heldTopDivisions": [{"supplier": c, "division": d, "products": n}
                             for (c, d), n in hcount.most_common(40)],
    }
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    c = doc["counts"]
    print("%s: %d published in %d categories (%d comparable), %d held"
          % (OUT, c["published"], c["categories"], c["comparableCategories"],
             c["held"]))
    print("  sources: both %d | manufacturer only %d | NHSSC only %d"
          % (c["withBothSources"], c["manufacturerOnly"], c["nhsscOnly"]))


if __name__ == "__main__":
    main()
