#!/usr/bin/env python3
"""Builds docs/join-the-hub-hybrid.html from the repo data files.
Run from the repo root of a checkout that has data/ (default: sibling fhi worktree)."""
import json, sys, datetime, html
from pathlib import Path
here = Path(__file__).resolve().parent
data = Path(sys.argv[1]) if len(sys.argv) > 1 else here.parent.parent / "fhi-opportunities-platform-0a5e43" / "data"
J = lambda f: json.load(open(data / f))
fw, sup, icc, awd = J("frameworks.json"), J("supplier-index.json"), J("icc-matrices.json"), J("framework-awards.json")
frameworks = fw["frameworks"]
today = datetime.date.today()
def pd(s):
    try: return datetime.datetime.strptime(s.strip(), "%d %B %Y").date()
    except Exception: return None
rows = sorted([(pd(f["ends"]), f) for f in frameworks if f.get("ends") and pd(f["ends"]) and pd(f["ends"]) >= today], key=lambda x: x[0])[:5]
fw_rows = "".join(
    f'<tr><td>{html.escape(f["name"])}<span class="sub">{html.escape(f.get("category",""))}</span></td>'
    f'<td class="num"><span class="pill">{d.day} {d.strftime("%b %Y")}</span></td>'
    f'<td class="num hide-sm">{f.get("supplierCount","")}</td></tr>' for d, f in rows)
stats = {
 "FW": fw["frameworkCount"],
 "PLACES": sum(f.get("supplierCount", 0) for f in frameworks),
 "AWARDS": awd["counts"]["awards"],
 "SUPPLIERS": len(sup["suppliers"]),
 "PRODUCTS": icc["product_count"],
 "BUYERS": awd["counts"]["distinct_buyers"],
 "MATRICES": icc["matrix_count"],
}
asof = fw.get("dataAsOf", str(today))
try: asof_h = datetime.date.fromisoformat(asof[:10]).strftime("%-d %b %Y")
except Exception: asof_h = asof
pub = sorted(a.get("published","")[:10] for a in awd["awards"] if a.get("published"))
fmtd = lambda x: datetime.date.fromisoformat(x).strftime("%-d %B %Y")
tpl = (here / "join-the-hub-hybrid.template.html").read_text()
for k, v in stats.items():
    tpl = tpl.replace("{{%s}}" % k, str(v)).replace("{{%s_FMT}}" % k, f"{v:,}")
tpl = tpl.replace("{{AW_SINCE}}", fmtd(pub[0])).replace("{{AW_TO}}", fmtd(pub[-1]))
tpl = tpl.replace("{{FW_ROWS}}", fw_rows).replace("{{ASOF}}", asof_h)
assert "{{" not in tpl, "unfilled placeholder"
(here / "join-the-hub-hybrid.html").write_text(tpl)
print("built", stats, asof_h, len(rows), "rows")
