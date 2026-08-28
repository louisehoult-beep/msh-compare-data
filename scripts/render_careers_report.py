#!/usr/bin/env python3
"""Render state/careers-report.json as a page Lou can actually look at.

A working report, not a Hub asset: it is written outside the repo, into the Hub
folder on OneDrive, and nothing serves it. Its job is to make the REFUSALS as
visible as the results, because the refusal rate is the thing to judge before
any of this is allowed near a paid page.

  python3 scripts/render_careers_report.py [out.html]
"""
import html
import json
import sys

NAVY, DEEP, GOLD_L, GOLD_D, INK = "#0B1C33", "#14304F", "#E0BE8E", "#A8842C", "#26364B"
SRC = "state/careers-report.json"
DEFAULT_OUT = ("/Users/louisehoult/Library/CloudStorage/OneDrive-Personal/Cowork-OS/"
               "02-Elevate-and-Thrive/Hub/supplier-careers-report.html")


def e(s):
    return html.escape(str(s or ""))


def main():
    d = json.load(open(SRC))
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    c = d["counts"]
    sup = d["suppliers"]
    counted = [r for r in sup if not r.get("refused")]
    counted.sort(key=lambda r: -r["roleCount"])
    linked = [r for r in sup if r.get("careersUrl") and r.get("refused")]
    nothing = [r for r in sup if not r.get("careersUrl")]

    P = []
    A = P.append
    A(f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Supplier hiring signal — working report</title><style>
*{{box-sizing:border-box}}
body{{margin:0;font:16px/1.6 Georgia,'Times New Roman',serif;color:{INK};background:#F7F5F1}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 24px 80px}}
header{{background:linear-gradient(135deg,{NAVY} 0%,#132B4A 55%,#1B3A5F 100%);color:#fff;padding:56px 24px 44px;margin-bottom:36px}}
header .wrap{{padding-bottom:0}}
.kicker{{color:{GOLD_L};text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-family:system-ui,sans-serif;margin:0 0 12px}}
h1{{margin:0 0 10px;font-size:34px;line-height:1.2;color:#fff;font-weight:600}}
header p{{margin:0;color:#C8D4E2;max-width:62ch}}
h2{{font-size:22px;color:{NAVY};margin:44px 0 6px;border-left:3px solid {GOLD_D};padding-left:12px}}
h2+p.note{{margin:0 0 18px 15px;color:#5A6B7F;font-size:15px;max-width:72ch}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:28px 0 0}}
.stat{{background:rgba(255,255,255,.07);border:1px solid rgba(224,190,142,.3);padding:14px 16px;border-radius:4px}}
.stat b{{display:block;font-size:28px;color:{GOLD_L};font-family:system-ui,sans-serif}}
.stat span{{font-size:12px;color:#C8D4E2;text-transform:uppercase;letter-spacing:.08em;font-family:system-ui,sans-serif}}
table{{width:100%;border-collapse:collapse;font-size:15px;background:#fff}}
.scroll{{overflow-x:auto;border:1px solid #E2DCD2;border-radius:4px}}
th{{background:{NAVY};color:{GOLD_L};text-align:left;padding:10px 12px;font:600 12px/1.4 system-ui,sans-serif;text-transform:uppercase;letter-spacing:.07em;white-space:nowrap}}
td{{padding:10px 12px;border-top:1px solid #EDE8E0;vertical-align:top}}
td.num{{text-align:right;font-family:system-ui,sans-serif;white-space:nowrap}}
a{{color:{DEEP}}}
.tag{{display:inline-block;font:600 10px/1 system-ui,sans-serif;text-transform:uppercase;letter-spacing:.07em;padding:4px 7px;border-radius:3px;background:#EFE7D8;color:{GOLD_D};margin-right:4px}}
.rule{{background:#fff;border-left:3px solid {GOLD_D};padding:18px 22px;margin:0 0 8px;font-size:15px}}
.rule b{{color:{NAVY}}}
details{{background:#fff;border:1px solid #E2DCD2;border-radius:4px;padding:12px 16px;margin-top:10px}}
summary{{cursor:pointer;font:600 14px system-ui,sans-serif;color:{NAVY}}}
ul.roles{{margin:10px 0 0;padding-left:20px;font-size:14px}}
.why{{color:#7A5C2E;font-size:14px}}
footer{{margin-top:56px;padding-top:20px;border-top:1px solid #E2DCD2;font-size:13px;color:#7C8899}}
</style></head><body>
<header><div class="wrap">
<p class="kicker">Medical Sales Intelligence Hub &middot; working report</p>
<h1>Supplier hiring signal</h1>
<p>Read from each company&rsquo;s own careers page &mdash; not LinkedIn. Generated {e(d['generatedOn'])}.
This is a working report: nothing here is published, and the refusals matter as much as the results.</p>
<div class="stats">
<div class="stat"><b>{c['checked']}</b><span>Suppliers checked</span></div>
<div class="stat"><b>{c['withCareersPage']}</b><span>Careers pages found</span></div>
<div class="stat"><b>{c['withRoleCount']}</b><span>Countable as records</span></div>
<div class="stat"><b>{c.get('completeBreakdowns', 0)}</b><span>Full breakdown</span></div>
<div class="stat"><b>{c['roles']}</b><span>Roles</span></div>
<div class="stat"><b>{c['ukRoles']}</b><span>UK roles</span></div>
</div></div></header><div class="wrap">""")

    A(f'<div class="rule"><b>The rule this was built under.</b> {e(d["rule"])}</div>')
    A(f'<div class="rule">{e(d["ukRule"])}</div>')
    A(f'<div class="rule">{e(d["roleFlagRule"])}</div>')

    A("<h2>Countable — roles read as records</h2>")
    A('<p class="note">Every row here was read from an applicant tracking system\'s own API '
      'or from schema.org JobPosting data. The count is the company\'s own count.</p>')
    if counted:
        A('<div class="scroll"><table><tr><th>Supplier</th><th>Roles</th><th>UK</th>'
          '<th>No location</th><th>Commercial</th><th>Clinical</th><th>New</th><th>Read from</th></tr>')
        for r in counted:
            u = r.get("rolesUrl") or r["careersUrl"]
            if r.get("complete"):
                cells = ("<td class='num'>%d</td><td class='num'>%d</td>"
                         "<td class='num'>%d</td><td class='num'>%d</td><td class='num'>%s</td>"
                         % (r["ukRoles"], r["rolesWithoutLocation"], r["commercialRoles"],
                            r["clinicalRoles"], r.get("newRoles", "—")))
            else:
                # Withheld, and it must LOOK withheld. A dash in a numeric column
                # reads as zero at a glance, which is the wrong number again.
                cells = ("<td colspan='5' class='why'>breakdown withheld &mdash; %d of %d "
                         "retrieved</td>" % (r["rolesRetrieved"], r["roleCount"]))
            A("<tr><td><strong>%s</strong><br><a href='%s'>%s</a></td>"
              "<td class='num'><strong>%d</strong></td>%s"
              "<td><span class='tag'>%s</span>%s</td></tr>"
              % (e(r["name"]), e(u), e(u[:56] + "…"), r["roleCount"], cells,
                 e(r["countMethod"]), e(r.get("ats") or "")))
        A("</table></div>")
        for r in counted:
            head = ("%s &mdash; %d role(s)" % (e(r["name"]), r["roleCount"]))
            if not r.get("complete"):
                head += (" &mdash; showing %d, breakdown withheld" % len(r["roles"]))
            A("<details><summary>%s</summary><ul class='roles'>" % head)
            for x in r["roles"]:
                tags = "".join("<span class='tag'>%s</span>" % t for t in
                               (["new"] if x.get("new") else []) +
                               (["commercial"] if x["commercial"] else []) +
                               (["clinical"] if x["clinical"] else []) +
                               (["UK"] if x["uk"] else []))
                A("<li>%s %s<span style='color:#7C8899'> &mdash; %s</span></li>"
                  % (tags, e(x["title"]), e(x["location"] or "no location published")))
            A("</ul></details>")
    else:
        A('<p class="note">Nothing in this run met the record bar.</p>')

    A("<h2>Careers page found, count refused</h2>")
    A('<p class="note">These pages are real and linked. The roles could not be read as '
      'discrete records, so no number is stated. This is the honest empty state, not a zero.</p>')
    A('<div class="scroll"><table><tr><th>Supplier</th><th>Careers page</th><th>Why no count</th></tr>')
    for r in linked:
        A("<tr><td><strong>%s</strong></td><td><a href='%s'>%s</a></td><td class='why'>%s</td></tr>"
          % (e(r["name"]), e(r["careersUrl"]), e(r["careersUrl"][:60] + "…"), e(r["refused"])))
    A("</table></div>")

    A("<h2>Nothing found</h2>")
    A('<p class="note">No careers page in the company&rsquo;s own navigation or at a conventional path, '
      'or the site refused automated reads.</p>')
    A('<div class="scroll"><table><tr><th>Supplier</th><th>Site</th><th>Reason</th></tr>')
    for r in nothing:
        A("<tr><td>%s</td><td>%s</td><td class='why'>%s</td></tr>"
          % (e(r["name"]), e(r["domain"]), e(r.get("refused"))))
    A("</table></div>")

    A("<footer>Generated by <code>scripts/refresh_supplier_careers.py</code> in "
      "<code>msh-compare-data</code>. Process: "
      "<code>02-Elevate-and-Thrive/Process flows for all brands/supplier-careers-hiring-signal.md</code>. "
      "Not published &mdash; a push to that repo is a publish.</footer></div></body></html>")

    with open(out, "w") as f:
        f.write("\n".join(P))
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
