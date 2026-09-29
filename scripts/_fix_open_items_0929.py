"""One-off, 29/09/2026: the open items left by 61b88c6 (Cowork-OS/02-Elevate-and-
Thrive/Process flows for all brands/nhssc-term-product-override-and-hartmann-
fixes-2026-09-28.md, "Crawl junk: what was fixed" -> "Still open").

Every change checked against the live supplier page on 29/09/2026.

supplier-products.json / supplier-product-detail.json
  Steris      "Trufreeze Facility Finder" dropped: its page is "Find a Facility
              Offering truFreeze Spray Cryotherapy", a US hospital locator, and it
              was publishing as a GI energy device (gastro:energy).
  Radiometer  "Download_New_" dropped: the page's only heading and title are
              "Download_NEW"; it was publishing as a blood gas product.
  UNOQUIP     "Urine Bag Accessories" is a real product page (urine bag hangers)
              whose capture ran on into an enquiry form; re-read with the fixed
              parser, which strips forms.
  L&R         Five range rows named from L&R's own misspelt or run-together slugs,
              each beside a hand-captured record (with specs) for the same page
              under the page's real name. The range row takes the real name, so
              the Differentiator row carries the specs; the spec-less slug-named
              record goes. Vliwasorb's page covers two products, each with its own
              spec record, so its one row becomes two.

Run once from the repo root, then rebuild the Differentiator and dossiers.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl_supplier_product_detail as d           # noqa: E402

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"
LR = "L&R Medical / Activa (Lohmann & Rauscher)"

DROP = {
    ("Steris", "Trufreeze Facility Finder"),
    ("Radiometer UK", "Download_New_"),
}
# range name -> the page's real product name(s), each already held with specs.
LR_RENAME = {
    "Supersorb A Ag": ["Suprasorb A + Ag"],
    "Suprasorb R Liquacel Ag": ["Suprasorb Liquacel Ag"],
    "Suprasorb X And X Phmb": ["Suprasorb X and X-PHMB"],
    "Suprasorb R Liquacel Pro": ["Suprasorb Liquacel Pro"],
    "Vliwasorb Pro And Vliwasorb Adhesive": ["Vliwasorb Pro", "Vliwasorb Adhesive"],
}
REREAD = [("UNOQUIP GMBH", "urine bag accessories")]


def recount(rec):
    counts = {}
    for p in rec["products"]:
        counts[p["division"]] = counts.get(p["division"], 0) + 1
    rec["divisions"] = [{"name": k, "products": v}
                        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


def main():
    sp_doc, det_doc = json.load(open(RANGE)), json.load(open(DETAIL))
    sp, store = sp_doc["suppliers"], det_doc["products"]
    log = []

    for co, name in sorted(DROP):
        rec = sp[co]
        before = len(rec["products"])
        rec["products"] = [p for p in rec["products"] if p["n"] != name]
        if len(rec["products"]) != before:
            recount(rec)
            log.append("range %s: dropped %r" % (co, name))
        if store.pop(co + "|" + d.nk(name), None) is not None:
            log.append("detail %s: dropped %r" % (co, name))

    rec = sp[LR]
    out = []
    for p in rec["products"]:
        if p["n"] in LR_RENAME:
            for real in LR_RENAME[p["n"]]:
                assert store.get(LR + "|" + d.nk(real), {}).get("specs"), real
                out.append(dict(p, n=real))
            log.append("range L&R: %r -> %s" % (p["n"], LR_RENAME[p["n"]]))
            if store.pop(LR + "|" + d.nk(p["n"]), None) is not None:
                log.append("detail L&R: dropped slug-named %r" % p["n"])
        else:
            out.append(p)
    rec["products"] = out
    recount(rec)

    # The hand-captured records the L&R rows now point at are spec-only (no
    # description, features or image); the page's own text was on the slug-named
    # record for the SAME page. Carry it across so the rename gains the specs
    # without losing the description. Read from 61b88c6, where the slug records
    # still exist, so this step is repeatable.
    import subprocess
    old = json.loads(subprocess.check_output(
        ["git", "show", "61b88c6:" + DETAIL]))["products"]
    for slug_name, reals in LR_RENAME.items():
        src = old.get(LR + "|" + d.nk(slug_name))
        if not src:
            continue
        for real in reals:
            tgt = store[LR + "|" + d.nk(real)]
            if tgt.get("description"):
                continue
            for f in ("description", "features", "image"):
                if src.get(f) and not tgt.get(f):
                    tgt[f] = src[f]
            tgt["pageTextFrom"] = {"sourceUrl": src.get("sourceUrl"),
                                   "capturedDate": src.get("capturedDate"),
                                   "parsed": src.get("parsed")}
            log.append("detail L&R: %r takes the page text of %r (same page)" % (real, slug_name))

    for co, key_name in REREAD:
        k = co + "|" + key_name
        v = store[k]
        got, why = d.page_product_detail(v["sourceUrl"])
        if got:
            old_cs = v.get("changedSince")
            d.record_capture(store, co, v["product"], got)
            store[k].pop("changedSince", None)      # a parser fix, not a supplier change
            if old_cs:
                store[k]["changedSince"] = old_cs
            log.append("detail %s: re-read %s" % (co, v["sourceUrl"]))
        else:
            log.append("detail %s: re-read refused (%s)" % (co, why))
        time.sleep(0.5)

    for path, doc in ((RANGE, sp_doc), (DETAIL, det_doc)):
        with open(path, "w") as f:
            f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
