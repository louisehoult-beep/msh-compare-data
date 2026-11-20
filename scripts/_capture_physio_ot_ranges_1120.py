#!/usr/bin/env python3
"""One-off, 20/11/2026 (follow-up to o276, Physiotherapy and Occupational Therapy):
publish the physiotherapy/OT product ranges of the framework's unpublished awardees
via the manual product capture route (sanctioned by Lou 30/09/2026; Cowork-OS
02-Elevate-and-Thrive/Process flows for all brands/manual-product-capture-route.md).

The 01/11/2026 hand curation (Cowork-OS 02-Elevate-and-Thrive/Hub/Supplier-
Consultations/physio-ot-hand-curation-2026-11-01.md) proved each awardee's legal
entity. The automated crawler refused or could not read these sites (WordPress /
WooCommerce / sitemap shapes, bot challenge), so each product's own page was read
individually on 20/11/2026 in a normal browser session (Claude in Chrome). robots.txt
was read on each site the same day and allows every captured path; Algeo's
/catalog/ product path is disallowed, so the one product only reachable there was
NOT captured. No login, no reseller page, no bot challenge bypassed.

Identity of each source site (read 20/11/2026):
  Algeo                    algeos.com contact page: "A. Algeo Ltd (UK) Sheridan House ...
                           Liverpool, L24 9HB" (matches Companies House 00437100).
  Cuxson Gerrard           hapla.co.uk: linked from cuxsongerrard.com's own home page as
                           one of its brands; hapla.co.uk's terms are "an agreement
                           between you and Cuxson Gerrard & Co. Ltd.".
  DJO UK Ltd (Enovis)      enovis.co.uk (address-matched 01/11/2026).
  Essity UK Limited        actimove.co.uk terms of use: "Essity UK Ltd ... Registration
                           number: 03226403".
  Eureka Physiocare Ltd    eurekaphysiocare.co.uk (footer matched 01/11/2026).
  Kinetik Medical Devices  kinetikwellbeing.com (footer matched 01/11/2026).
  Koolpak Ltd              koolpak.co.uk (01/11/2026; sister company CMUK Visual Safety
                           Ltd trades as Koolpak at the same address, noted there).
  Medline Industries       medline.eu/uk (Medline's UK site; contact block names
                           "Medline Industries Ltd ... Warrington WA4 6HL").
  Phoenix Medical Ltd      phoenixmedical.com footer: 5 Lonebarn Link, Chelmsford CM2 5AR
                           (address match to 08921091; sister Phoenix Medical Group Ltd
                           shares the address, as the 01/11 note records).
  Physiolab                physiolab.com (privacy policy number matched 01/11/2026).
  Reliance Medical         reliancemedicalltd.com (www.reliancemedical.co.uk redirects
                           there): "Reliance Medical Limited. Registered in England No.
                           5701697".
  Thera Trainer UK Ltd     thera-trainer.com/en-uk (UK contact page matched 01/11/2026).

Selection: only the physiotherapy / OT division of each range (hot and cold therapy,
strapping and tapes, electrotherapy, exercise and rehabilitation equipment,
acupuncture). Everything else on those sites (first aid, wound care, podiatry
padding, nutrition, diagnostics) is NOT captured; each record is partialRead with a
filingRule saying so. Orca Medical Ltd is not touched: its own site sells diagnostic
ultrasound only, already recorded under ultrasound:*, and names no physio/OT product.

Category: rehab:therapy ("Therapy and exercise equipment"), the decision already
recorded for Medfac UK Ltd's therapy range on this framework (6256af46).

Run once from the repo root:
  python3 scripts/_capture_physio_ot_ranges_1120.py
"""
import json
import os

DATE = "2026-11-20"
HUB = "rehab:therapy"
STAGED = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-Personal/Cowork-OS/02-Elevate-and-Thrive/Hub/"
    "Medical-Sales-Hub/proposed-data/manual-capture-physio-ot-ranges-proposed-2026-11-20.json")
FRAMEWORK = "Physiotherapy and Occupational Therapy"

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"
MAP = "data/differentiator-category-map.json"
SEED = "data/supplier-seed.json"

# staged supplier name -> (supplier-products key, domain, identity sentence)
META = {
    "Algeo": ("Algeo", "algeos.com",
              "algeos.com (contact page names A. Algeo Ltd (UK), Sheridan House, Liverpool)"),
    "Cuxson Gerrard & Company Limited": ("Cuxson Gerrard & Company Limited", "hapla.co.uk",
              "hapla.co.uk (Hapla, a Cuxson Gerrard brand linked from cuxsongerrard.com; its "
              "terms name Cuxson Gerrard & Co. Ltd.)"),
    "DJO UK Ltd (Enovis)": ("DJO UK Ltd (Enovis)", "enovis.co.uk",
              "enovis.co.uk rehabilitation pages (Enovis UK, Guildford)"),
    "Essity UK Limited": ("Essity UK Limited (formerly BSN Medical Ltd)", "actimove.co.uk",
              "actimove.co.uk (terms of use name Essity UK Ltd, registration number 03226403)"),
    "Eureka Physiocare Ltd": ("Eureka Physiocare Ltd", "eurekaphysiocare.co.uk",
              "eurekaphysiocare.co.uk (footer names Eureka Physiocare Ltd, Newtown)"),
    "Kinetik Medical Devices": ("Kinetik Medical Devices", "kinetikwellbeing.com",
              "kinetikwellbeing.com (footer names Kinetik Medical Devices Limited, Redhill)"),
    "Koolpak Ltd": ("Koolpak Ltd", "koolpak.co.uk", "koolpak.co.uk"),
    "Medline Industries": ("Medline Industries", "medline.eu/uk",
              "medline.eu/uk (Medline UK; contact block names Medline Industries Ltd, Warrington)"),
    "Phoenix Medical Ltd": ("Phoenix Medical Ltd", "phoenixmedical.com",
              "phoenixmedical.com (footer address 5 Lonebarn Link, Chelmsford CM2 5AR, matching "
              "Phoenix Medical Ltd 08921091)"),
    "Physiolab Technologies Limited": ("Physiolab Technologies Limited", "physiolab.com",
              "physiolab.com (privacy policy names registered number 06430772)"),
    "Reliance Medical": ("Reliance Medical", "reliancemedicalltd.com",
              "reliancemedicalltd.com (footer: Reliance Medical Limited, Registered in England "
              "No. 5701697)"),
    "Thera Trainer UK Ltd": ("Thera Trainer UK Ltd", "thera-trainer.com",
              "thera-trainer.com/en-uk (UK contact page names THERA-Trainer UK Ltd., Milton Keynes)"),
}


def save(path, doc, compact=False):
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            f.write(json.dumps(doc, ensure_ascii=False))
        else:
            f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


staged = json.load(open(STAGED, encoding="utf-8"))
assert staged["date"] == DATE
sp = json.load(open(RANGE, encoding="utf-8"))
dd = json.load(open(DETAIL, encoding="utf-8"))
cm = json.load(open(MAP, encoding="utf-8"))
known_pairs = {(e["supplier"], e["division"]) for e in cm["entries"]}

for sname, items in staged["suppliers"].items():
    key, domain, ident = META[sname]
    assert items, sname
    divs = []
    for p in items:
        if p["division"] not in divs:
            divs.append(p["division"])
    counts = {d: sum(1 for p in items if p["division"] == d) for d in divs}
    prods = [{"n": p["n"], "division": p["division"], "category": "",
              "manualCapture": {"sourceUrl": p["sourceUrl"], "capturedDate": DATE}}
             for p in items]

    rec = sp["suppliers"].get(key)
    if rec is None:
        sp["suppliers"][key] = {
            "domain": domain,
            "verified": DATE,
            "source": "%s: each product's own page read individually on %s (manual product "
                      "capture route, sanctioned 30/09/2026)." % (ident, DATE),
            "structureFrom": "the site's own section names",
            "hasDivisions": True,
            "partialRead": True,
            "structure": "Physiotherapy / OT range only, filed under the section names the "
                         "site gives it.",
            "filingRule": "Partial manual capture for the %s framework, not the whole range: "
                          "only the physiotherapy and occupational therapy section(s) named "
                          "below. Other sections of the site were not captured." % FRAMEWORK,
            "divisions": [{"name": d, "products": counts[d]} for d in divs],
            "products": prods,
        }
        print("range: %s added (%d products)" % (key, len(prods)))
    else:
        # Existing crawled record (Essity's cutimed.co.uk capture): add the hand-captured
        # products with manualCapture blocks so a re-crawl carries them (^o524).
        have = {(x.get("n") or "").lower() for x in rec.get("products") or []}
        new = [x for x in prods if x["n"].lower() not in have]
        rec.setdefault("products", []).extend(new)
        dnames = {d["name"] for d in rec.get("divisions") or []}
        for d in divs:
            if d not in dnames:
                rec.setdefault("divisions", []).append({"name": d, "products": counts[d]})
        rec["manualCaptureNote"] = (
            "Added %s: %d products from %s, each page read individually (manual product "
            "capture route), for the %s framework." % (DATE, len(new), ident, FRAMEWORK))
        print("range: %s extended (+%d products)" % (key, len(new)))

    added = 0
    for p in items:
        k = key + "|" + p["n"].lower()
        if k in dd["products"]:
            continue
        dd["products"][k] = {
            "supplier": key, "product": p["n"], "sourceUrl": p["sourceUrl"],
            "capturedDate": DATE, "parsed": "structured",
            "description": p.get("description"), "features": None, "image": None,
        }
        added += 1
    print("detail: %s +%d" % (key, added))

    for d in divs:
        if (key, d) in known_pairs:
            print("map: %s / %s already present" % (key, d))
            continue
        ex = [p["n"] for p in items if p["division"] == d][:4]
        cm["entries"].append({
            "supplier": key, "division": d, "products": counts[d], "categories": [],
            "examples": ex, "hub": HUB, "notTaxonomy": False,
            "evidence": "%s, product pages read %s: the '%s' section of the site. %s is named "
                        "on NHS Supply Chain's %s contract launch brief." % (
                            ident, DATE, d, sname, FRAMEWORK),
            "why": "physiotherapy / occupational therapy treatment, exercise and "
                   "rehabilitation products, the same category as Medfac UK Ltd's therapy "
                   "range on this framework.",
        })
        known_pairs.add((key, d))
        print("map: %s / %s -> %s" % (key, d, HUB))

cm["counts"]["pairs"] = len(cm["entries"])
save(RANGE, sp)
save(DETAIL, dd)
save(MAP, cm, compact=True)

# Phoenix Medical Ltd had no website link in the seed (ledger: domainsMissing).
seed = json.load(open(SEED, encoding="utf-8"))
for s in seed.get("suppliers") or seed.get("entries") or []:
    if isinstance(s, dict) and s.get("name") == "Phoenix Medical Ltd":
        links = s.setdefault("links", [])
        if not any("phoenixmedical.com" in (l.get("url") or "") for l in links):
            links.append({
                "label": "Company website", "url": "https://phoenixmedical.com",
                "route": "address",
                "source": "Proved phoenixmedical.com by registered address on %s: footer gives "
                          "5 Lonebarn Link, Chelmsford, Essex, CM2 5AR, Phoenix Medical Ltd's "
                          "Companies House address (08921091). Sister company Phoenix Medical "
                          "Group Ltd shares the address." % DATE})
            s["_curatorNotes"] = ((s.get("_curatorNotes") or "") + " %s: phoenixmedical.com "
                "loaded in a normal browser session with no challenge; its footer gives the "
                "registered address, so the site is now linked by address (route: address). The "
                "company number is still not printed on the site, so companyNumberEvidence is "
                "unchanged." % DATE).strip()
            print("seed: Phoenix Medical Ltd website link added")
save(SEED, seed)
