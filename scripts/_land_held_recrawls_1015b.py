#!/usr/bin/env python3
"""Land two of the four re-crawls still held after _land_held_recrawls_1015.py,
and record a third as a refusal, 15/10/2026 (^o635 round 2).

    python3 scripts/_land_held_recrawls_1015b.py <dir holding ottobock.json, optimum.json>

Each capture was read live this session with crawl_supplier_site.crawl() and
passed through tidy_capture().

- Otto Bock Healthcare PLC (www.ottobock.com): the sitemap route now keeps only
  the en-gb locale (the root sitemap index lists ~50 markets; the earlier reads
  mixed Italian and French). 189 products, which is exactly the number of
  /en-gb/product/ URLs in https://www.ottobock.com/en-gb/sitemap.xml, each named
  from its own page (previously 429 bare catalogue codes such as "4R57 62898")
  and filed under the site's own breadcrumb divisions. The 31 product-overrides
  keyed on catalogue codes move to the printed name of the same product page, same
  hub category; the 39 product-detail records are re-keyed to the same names.
- Optimum Medical (optimummedical.co.uk): blog posts that WordPress files at
  /products/<slug>/ came only from post-sitemap.xml and are no longer read as
  products: 41 products, down from 88 records of which 47 were posts.
- Insulet International Ltd (www.omnipod.com): the site is the marketing and
  patient-education site for two systems (Omnipod 5, Omnipod DASH). Pages left
  after tidying are topics ("Type 2 Diabetes", "Custom Foods", a German
  "Celebrate" page, "Interest List"), not a range. Recorded as a refusal so the
  published capture (which carried two "Thanks" pages) goes; the curated list in
  the seed (Omnipod 5, Omnipod DASH, the controllers) is what members see.
- Sectra Limited stays HELD: see the report.
"""
import json, os, re, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crawl_supplier_site as cs

CAP = sys.argv[1]
NOTE = (" Re-curated 15/10/2026 (^o635) to the name the product's own page prints, after the "
        "en-gb re-crawl replaced the bare catalogue code.")
INSULET_WHY = ("omnipod.com is the marketing and patient-education site for two insulin pump systems, "
               "Omnipod 5 and Omnipod DASH. Read live 15/10/2026: after dropping the form-confirmation "
               "pages, the 13 pages left are topics, not products ('Type 2 Diabetes', 'Custom Foods', "
               "'Interest List', 'Clinical Summaries', a German 'Celebrate' page). It is not a product "
               "range, so nothing is published from it; the seed's curated list stands.")

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

prod = json.load(open(cs.OUT, encoding="utf-8"))

# ---- Otto Bock: capture
ob = json.load(open(os.path.join(CAP, "ottobock.json")))["shaped"]
ob, notes = cs.tidy_capture(ob)
ob_old_names = [p["n"] for p in prod["suppliers"]["Otto Bock Healthcare PLC"]["products"]]
existing = prod["suppliers"]["Otto Bock Healthcare PLC"]
for k in ("aliases", "companyNo", "notSold", "tubesNote", "domainWarning"):
    if k in existing:
        ob[k] = existing[k]
prod["suppliers"]["Otto Bock Healthcare PLC"] = ob
prod.get("refusals", {}).pop("Otto Bock Healthcare PLC", None)
ob_names = {p["n"] for p in ob["products"]}

# the printed name for each old catalogue code, read from the code's own en-gb page
sm, _ = cs.get("https://www.ottobock.com/en-gb/sitemap.xml")
urls = {}
for loc in re.findall(r"<loc>(.*?)</loc>", sm):
    m = re.search(r"/en-gb/product/([^/]+)$", loc.strip())
    if m:
        urls[norm(m.group(1))] = loc.strip()
newname = {}
for old in ob_old_names:
    u = urls.get(norm(old))
    if not u:
        continue
    try:
        body, _ = cs.get(u, timeout=30)
    except Exception as ex:
        print("   %r: %s did not answer (%s)" % (old, u, str(ex)[:40]))
        continue
    nm = cs._page_title(body)
    if nm in ob_names:
        newname[old] = nm
print("Otto Bock: %d of %d old catalogue codes have an en-gb page printing a captured name" %
      (len(newname), len(ob_old_names)))

# ---- Optimum Medical: capture
op = json.load(open(os.path.join(CAP, "optimum.json")))["shaped"]
op, notes_op = cs.tidy_capture(op)
existing = prod["suppliers"]["Optimum Medical"]
for k in ("aliases", "companyNo", "notSold", "tubesNote", "domainWarning"):
    if k in existing:
        op[k] = existing[k]
prod["suppliers"]["Optimum Medical"] = op
op_names = {p["n"] for p in op["products"]}

# ---- Insulet: refusal, capture removed
prod["suppliers"].pop("Insulet International Ltd", None)
prod.setdefault("refusals", {})["Insulet International Ltd"] = {
    "domain": "www.omnipod.com", "reason": INSULET_WHY, "checked": dt.date.today().isoformat()}
cs.atomic_write_json(cs.OUT, prod)

# ---- product-detail: re-key Otto Bock's records to the new names; Insulet's go with its capture
DET = "data/supplier-product-detail.json"
det = json.load(open(DET, encoding="utf-8"))
new_products, moved, dropped_ins = {}, 0, 0
for key, rec in det["products"].items():
    sup = rec.get("supplier")
    if sup == "Insulet International Ltd":
        dropped_ins += 1
        continue
    if sup == "Otto Bock Healthcare PLC" and rec.get("product") in newname:
        nm = newname[rec["product"]]
        rec["product"] = nm
        key = "%s|%s" % (sup, nm.lower())
        moved += 1
    new_products[key] = rec
det["products"] = new_products
with open(DET, "w", encoding="utf-8") as f:
    json.dump(det, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("detail: %d Otto Bock records re-keyed, %d Insulet records removed" % (moved, dropped_ins))

# ---- category map
MAP = "data/differentiator-category-map.json"
m = json.load(open(MAP, encoding="utf-8"))
out = []
def count(c, d):
    return sum(1 for p in c["products"] if (p.get("division") or "Uncategorised") == d)
for e in m["entries"]:
    sup = e.get("supplier")
    if sup == "Insulet International Ltd" and e.get("kind") != "nhssc-term":
        print("dropped Insulet map entry %r (supplier is now a recorded refusal)" % e.get("division"))
        continue
    if sup == "Otto Bock Healthcare PLC" and e.get("kind") != "nhssc-term":
        if e.get("kind") == "product-override":
            new = newname.get(e["division"])
            if not new:
                print("dropped Otto Bock override %r: no en-gb page" % e["division"])
                continue
            e["division"] = new
            e["examples"] = [new]
            e["evidence"] = (e.get("evidence") or "") + NOTE
            e["why"] = (e.get("why") or "") + NOTE
        elif e.get("division") == "Uncategorised":
            e["products"] = count(ob, "Uncategorised")
            e["examples"] = [p["n"] for p in ob["products"] if p.get("division") == "Uncategorised"][:4]
            e["why"] = ("Re-crawled 15/10/2026 on the en-gb locale only: products are now named from their "
                        "own pages and filed under the site's breadcrumb divisions; the 4 left here have no "
                        "breadcrumb division. The earlier hold on bare catalogue codes (^o423, 20/09/2026) no "
                        "longer applies to these names; the product-overrides below carry it forward.")
        out.append(e)
        continue
    if sup == "Optimum Medical" and e.get("kind") != "nhssc-term":
        if e.get("kind") == "product-override":
            d = e["division"]
            if d not in op_names:
                print("dropped Optimum override %r: not in the product sitemap (it was a blog post)" % d)
                continue
        elif e.get("division") == "Uncategorised":
            e["products"] = count(op, "Uncategorised")
            e["examples"] = [p["n"] for p in op["products"]][:4]
        out.append(e)
        continue
    out.append(e)
m["entries"] = out
with open(MAP, "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("category map rewritten")
