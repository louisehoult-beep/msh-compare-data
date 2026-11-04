#!/usr/bin/env python3
"""Weekly briefing: one Monday email per member, built from THEIR specialities and companies.

Added 22/10/2026 for Aneeka Hussain's request. Offline, stdlib only. SENDS NOTHING.

WHAT IT IS
  The Rep's Briefing already goes to every Hub member group on Monday 09:00 and is the
  same for everyone. This is the personal one: what changed in the specialities (and
  companies) a member chose on My Hub, in the last 7 days, plus dates in the next 14.

WHERE EVERY LINE COMES FROM (stored data only, nothing computed from outside the repo)
  news         data/speciality-news/<slug>.json            items published in the window
  awards       data/speciality-panels/<slug>.json awards   non-framework awards dated in the window
  safety       data/speciality-panels/<slug>.json mhraDsu  Drug Safety Update items published in the window
  alerts       data/mhra-alerts.json                       every device and patient safety alert issued in the window;
                                                           speciality match only from GOV.UK's own facet, never the title
  tenders      data/open-tenders.json                      open notices tagged to the speciality, closing in the next 14 days
  dates ahead  data/hub-calendar.json                      awareness days, events, framework ends tagged to the speciality, next 14 days
  companies    data/company-awards.json, data/company-press.json
                                                           items dated in the window for the companies the member ticked
  NHS changes  data/icb-watch.json events                  Integrated Care Board events in the window (shared, never the reason to send)

THE SEND RULE (publishing nothing is the correct output when evidence is thin)
  A briefing is built only when at least one CHANGE item exists (news, awards, safety,
  company activity). Dates ahead, tenders and Integrated Care Board events ride along but
  never justify a send on their own. No change items: build() returns None and nothing is
  produced for that member. An alert outside the member's specialities and companies is
  still shown, because My Hub promises every alert, but never justifies a send by itself.

WHAT MAKES THE EMAIL (04/11/2026, after the first real-data audit)
  Unverified items never appear: verified at build time, never sent with a caveat. Editorial
  correspondence and corrections are dropped. Hub intelligence and trade news rank above
  journal papers, with at most MAX_JOURNAL papers per speciality. An item appears once in a
  member's email, under their company first. The count in the subject is what the email shows.

MAILERLITE MAPPING
  Opt-in is the My Hub box (state.briefing, saved in WordPress user meta msh_hub_state).
  Members who share the same speciality set get the same email, so audience groups are one
  per DISTINCT SET: "Hub briefing - <slug>+<slug>". One member is in one group, so nobody
  receives two emails. Companies change the content per member, so company items are
  rendered per member and the set group is split by company key only when the member has
  company items. plan() returns the groups; nothing here calls MailerLite.

  python3 scripts/weekly_briefing.py --today 2026-10-26 --members members.json --out outdir
  members.json: [{"key": "m1", "specialities": ["dermatology"], "companies": ["ego-pharmaceuticals"]}]
  Keys are opaque ids. Never put names or emails in the file or in this repo.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW_DAYS = 7
AHEAD_DAYS = 14
MAX_PER_SECTION = 5
MAX_JOURNAL = 2
JOURNAL_RE = re.compile(r"journal|\(contents\)|\(online first\)|nursing in critical care|colorectal disease"
                        r"|clinical otolaryngology|transfusion medicine", re.I)
NOISE_TITLE_RE = re.compile(r"^\s*(correspondence|comment on|reply to|response to|letter to|erratum|corrigendum|retraction)\b", re.I)
HUB_SOURCES = ("Hub intelligence",)
# GOV.UK tags alerts with medical_specialism and Drug Safety Updates with therapeutic_area. Where
# the two names differ, this points the alert facet at the map's name. Nothing else is inferred.
ALERT_FACET_ALIAS = {
    "anaesthetics": "anaesthesia-intensive-care", "haematology-oncology": "haematology",
    "obstetrics-gynaecology": "obstetrics-gynaecology-fertility", "paediatrics": "paediatrics-neonatology",
    "radiology": "radiology-imaging", "urology": "urology-nephrology",
}
ALERT_LABEL = {"device-safety-information": "Device Safety Information",
               "national-patient-safety": "National Patient Safety Alert"}
SITE = "https://medsalesintelligencehub.co.uk"
MY_HUB = SITE + "/medical-sales-hub/my-hub/"
NAVY, GOLD_ON_NAVY, INK, WARM = "#0B1C33", "#E0BE8E", "#1D2733", "#EDE7DC"
LIGHT_ON_NAVY = "#F5F1E8"


def _load(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _day(s):
    """First ten characters as a date, or None. Handles 2026-10-12T10:12:41+00:00 and 2026-10-12."""
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _in_window(s, today, days=WINDOW_DAYS):
    d = _day(s)
    return d is not None and today - datetime.timedelta(days=days) < d <= today


def _ahead(s, today, days=AHEAD_DAYS):
    d = _day(s)
    return d is not None and today <= d <= today + datetime.timedelta(days=days)


def _safe_url(u):
    return u if isinstance(u, str) and u.startswith("https://") else ""


def _speciality_item(slug):
    cat = _load("hub/my-hub-catalogue.json", {})
    for it in cat.get("items", []):
        if it.get("group") == "specialities" and it.get("id") == slug:
            return it
    return None


def speciality_label(slug):
    it = _speciality_item(slug)
    return (it.get("label") or slug) if it else None


def _norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def _clean_title(t):
    return re.sub(r"\s*[\u2013-]\s*Full Text\s*$", "", str(t)).strip()


def _news_tier(n):
    if n.get("source") in HUB_SOURCES:
        return 0
    return 2 if n.get("journal") else 1


class Data:
    """Everything the briefing reads, loaded once."""

    def __init__(self):
        self.calendar = (_load("data/hub-calendar.json", {}) or {}).get("entries", [])
        self.tenders = (_load("data/open-tenders.json", {}) or {}).get("notices", [])
        self.icb = (_load("data/icb-watch.json", {}) or {}).get("events", [])
        self.co_awards = (_load("data/company-awards.json", {}) or {}).get("companies", {})
        self.co_press = (_load("data/company-press.json", {}) or {}).get("suppliers", {})
        self.co_index = {c["id"]: c for c in (_load("data/company-key-info/index.json", {}) or {}).get("companies", [])}
        self.alerts = (_load("data/mhra-alerts.json", {}) or {}).get("alerts", [])
        self.facets = (_load("config/mhra-dsu-speciality-map.json", {}) or {}).get("facets", {})
        self._news, self._panel = {}, {}

    def news(self, slug):
        if slug not in self._news:
            self._news[slug] = (_load("data/speciality-news/%s.json" % slug, {}) or {}).get("items", [])
        return self._news[slug]

    def panel(self, slug):
        if slug not in self._panel:
            self._panel[slug] = _load("data/speciality-panels/%s.json" % slug, {}) or {}
        return self._panel[slug]


def speciality_section(data, slug, today):
    label = speciality_label(slug)
    if not label:
        return None
    panel = data.panel(slug)
    item = _speciality_item(slug) or {}
    sec = {"slug": slug, "label": label, "url": SITE + item.get("url", "/medical-sales-hub/"), "hidden": 0,
           "news": [], "awards": [], "safety": [], "tenders": [], "dates": []}
    for n in data.news(slug):
        if n.get("verified") is False or NOISE_TITLE_RE.match(str(n.get("title", ""))):
            continue
        if _in_window(n.get("published"), today) and _safe_url(n.get("link")):
            source = n.get("source") or ""
            sec["news"].append({
                "title": _clean_title(n.get("title", "")), "url": n["link"], "date": str(n["published"])[:10],
                "source": source, "journal": bool(JOURNAL_RE.search(source)),
            })
    for a in panel.get("awards", []) or []:
        if not a.get("isFramework") and _in_window(a.get("date"), today) and _safe_url(a.get("url")):
            sec["awards"].append({
                "title": a.get("title", ""), "url": a["url"], "date": a["date"],
                "buyer": a.get("buyer") or "", "supplier": a.get("supplier") or "Supplier not named on the notice",
            })
    for u in (panel.get("mhraDsu") or {}).get("updates", []) or []:
        if _in_window(u.get("published"), today) and _safe_url(u.get("url")):
            sec["safety"].append({"title": u.get("title", ""), "url": u["url"], "date": u["published"]})
    for t in data.tenders:
        if t.get("speciality") == slug and _ahead(t.get("closingDate"), today) and _safe_url(t.get("url")):
            sec["tenders"].append({
                "title": t.get("title", ""), "url": t["url"], "buyer": t.get("buyer") or "",
                "closes": str(t["closingDate"])[:10],
            })
    for e in data.calendar:
        if slug in (e.get("specialities") or []) and _ahead(e.get("date"), today) \
                and e.get("type") in ("awareness", "event", "framework-end"):
            src = _safe_url(e.get("source"))
            if src:
                sec["dates"].append({"title": e.get("title", ""), "date": e["date"], "url": src, "type": e["type"]})
    for k in ("news", "awards", "safety"):
        sec[k].sort(key=lambda x: x["date"], reverse=True)
    sec["news"].sort(key=_news_tier)
    sec["awards"].sort(key=lambda x: x["supplier"] == "Supplier not named on the notice")
    sec["tenders"].sort(key=lambda x: x["closes"])
    sec["dates"].sort(key=lambda x: x["date"])
    return sec


def company_section(data, cid, today):
    c = data.co_index.get(cid)
    if not c:
        return None
    name = c.get("n", cid)
    items = []
    for a in data.co_awards.get(name, []) or []:
        if _in_window(a.get("date"), today) and _safe_url(a.get("url")):
            items.append({"kind": "Contract award", "title": a.get("title", ""), "url": a["url"],
                          "date": a["date"], "detail": a.get("buyer") or ""})
    for p in (data.co_press.get(name) or {}).get("items", []) or []:
        srcs = [s for s in p.get("sources", []) if s.get("urlType") == "publisher" and _safe_url(s.get("url"))]
        if _in_window(p.get("date"), today) and srcs:
            items.append({"kind": "In the press", "title": p.get("headline", ""), "url": srcs[0]["url"],
                          "date": p["date"], "detail": srcs[0].get("publisher") or ""})
    items.sort(key=lambda x: x["date"], reverse=True)
    return {"id": cid, "name": name, "items": items}


def alert_specialities(alert, facets):
    """Hub specialities for an alert, from GOV.UK's facet through the shared map. Never from its words."""
    out = set()
    for f in alert.get("specialisms") or []:
        out.update((facets.get(ALERT_FACET_ALIAS.get(f, f)) or {}).get("hub") or [])
    return out


def alerts_for(member, today, data, days=WINDOW_DAYS):
    """Every alert in the window, those matching this member's specialities or companies first."""
    specs = set(member.get("specialities", []))
    names = {data.co_index[c].get("n") for c in member.get("companies", []) if c in data.co_index}
    out = []
    for a in data.alerts:
        if _in_window(a.get("issuedDate"), today, days) and _safe_url(a.get("url")):
            yours = bool(alert_specialities(a, data.facets) & specs) or a.get("company") in names
            out.append({"title": a.get("title", ""), "url": a["url"], "date": a["issuedDate"], "yours": yours,
                        "label": ALERT_LABEL.get(a.get("alertType"), "Safety alert")})
    out.sort(key=lambda x: (not x["yours"], x["date"]))
    return out


def _take(items, seen, limit=MAX_PER_SECTION, journal_limit=None):
    """Up to `limit` items not already in this email. Returns (kept, how many were left out)."""
    kept, left, journals = [], 0, 0
    for it in items:
        keys = (it["url"], _norm_title(it["title"]))
        if keys[0] in seen or keys[1] in seen:
            continue
        seen.update(keys)
        if len(kept) >= limit or (journal_limit is not None and it.get("journal") and journals >= journal_limit):
            left += 1
            continue
        journals += 1 if it.get("journal") else 0
        kept.append(it)
    return kept, left


def build(member, today, data=None):
    """The briefing for one member, or None when there is no change worth sending."""
    data = data or Data()
    seen = set()
    cos = []
    for c in (company_section(data, cid, today) for cid in member.get("companies", [])):
        if c and c["items"]:
            c["items"], c["hidden"] = _take(c["items"], seen)
            cos.append(c)
    alerts = alerts_for(member, today, data)
    seen.update(a["url"] for a in alerts)
    specs = []
    for s in (speciality_section(data, sl, today) for sl in member.get("specialities", [])):
        if not s:
            continue
        s["safety"], _ = _take(s["safety"], seen)
        s["news"], left_news = _take(s["news"], seen, journal_limit=MAX_JOURNAL)
        s["awards"], left_awards = _take(s["awards"], seen)
        s["hidden"] = left_news + left_awards
        specs.append(s)
    changes = (sum(len(s[k]) for s in specs for k in ("news", "awards", "safety"))
               + sum(len(c["items"]) for c in cos) + sum(1 for a in alerts if a["yours"]))
    if not changes:
        return None
    # "page text changed" says only that a formulary page moved: it tells a member nothing, and it is not personal.
    icb = [e for e in data.icb if _in_window(e.get("date"), today) and e.get("headline") and e.get("sources")
           and "page text changed" not in e["headline"]]
    return {"today": today.isoformat(), "specialities": specs, "companies": cos, "alerts": alerts,
            "icb": icb[:MAX_PER_SECTION], "changes": changes}


def instant_candidates(member, day, data):
    """What a phone alert would carry for this member on one day: their safety alerts and company activity.
    Shadow only. Nothing sends this until Lou approves it."""
    out = [{"kind": "safety", "title": a["title"], "url": a["url"]}
           for a in alerts_for(member, day, data, days=1) if a["yours"]]
    for cid in member.get("companies", []):
        c = company_section(data, cid, day)
        for i in (c or {}).get("items", []):
            if i["date"] == day.isoformat():
                out.append({"kind": "company", "title": i["title"], "url": i["url"]})
    return out


def set_group(member):
    """MailerLite group name for a member's speciality set (one group per distinct set)."""
    return "Hub briefing - " + "+".join(sorted(set(member.get("specialities", [])))) if member.get("specialities") else None


def plan(members, today, data=None):
    """Dry run: who would get a briefing, in which group. Calls nothing."""
    data = data or Data()
    out = {"groups": {}, "skipped": []}
    for m in members:
        b = build(m, today, data)
        g = set_group(m)
        if not g or b is None:
            out["skipped"].append(m["key"])
            continue
        out["groups"].setdefault(g, []).append(m["key"])
    return out


# ---------------------------------------------------------------- rendering

def _fmt(iso):
    d = _day(iso)
    return "%d %s %d" % (d.day, d.strftime("%b"), d.year) if d else ""


def _e(s):
    return html.escape(str(s), quote=True)


def _list(rows):
    return "".join(
        '<tr><td style="padding:10px 0;border-bottom:1px solid #D6CEBE;font:15px/1.5 Georgia,serif;color:%s">%s</td></tr>' % (INK, r)
        for r in rows)


def _link(url, text):
    return '<a href="%s" style="color:%s;font-weight:600;text-decoration:underline">%s</a>' % (_e(url), NAVY, _e(text))


def _band(title, rows):
    if not rows:
        return ""
    return ('<tr><td style="padding:22px 28px 6px;background:#FFFFFF"><div style="font:700 13px/1.2 Arial,sans-serif;'
            'letter-spacing:.12em;text-transform:uppercase;color:%s">%s</div>'
            '<table width="100%%" cellpadding="0" cellspacing="0" role="presentation" style="margin-top:6px">%s</table></td></tr>'
            % (NAVY, _e(title), _list(rows)))


def render_html(b):
    parts = [_band("Safety alerts this week", ["%s<br><small>%s, %s%s</small>" % (
        _link(a["url"], a["title"]), _e(a["label"]), _fmt(a["date"]), ". In your specialities." if a["yours"] else "")
        for a in b.get("alerts", [])])]
    for s in b["specialities"]:
        rows = []
        for u in s["safety"]:
            rows.append("%s<br><small>Medicines and Healthcare products Regulatory Agency (MHRA) Drug Safety Update, %s</small>" % (
                _link(u["url"], u["title"]), _fmt(u["date"])))
        for n in s["news"]:
            rows.append("%s<br><small>%s, %s</small>" % (_link(n["url"], n["title"]), _e(n["source"]), _fmt(n["date"])))
        for a in s["awards"]:
            who = a["supplier"].strip().rstrip(" .")
            who = who + "." if who == "Supplier not named on the notice" else "Supplier: %s." % who
            rows.append("%s<br><small>Contract award, %s. Buyer: %s. %s</small>" % (
                _link(a["url"], a["title"]), _fmt(a["date"]), _e(a["buyer"]), _e(who)))
        if s.get("hidden") and rows:
            rows.append(_link(s["url"], "%d more this week on your %s page" % (s["hidden"], s["label"])))
        parts.append(_band(s["label"] + ": what changed this week", rows))
        ahead = ["%s<br><small>Closes %s. Buyer: %s.</small>" % (_link(t["url"], t["title"]), _fmt(t["closes"]), _e(t["buyer"]))
                 for t in s["tenders"][:MAX_PER_SECTION]]
        ahead += ["%s<br><small>%s</small>" % (_link(d["url"], d["title"]), _fmt(d["date"])) for d in s["dates"][:MAX_PER_SECTION]]
        parts.append(_band(s["label"] + ": coming up in the next fortnight", ahead))
    for c in b["companies"]:
        parts.append(_band(c["name"], ["%s<br><small>%s, %s. %s</small>" % (
            _link(i["url"], i["title"]), _e(i["kind"]), _fmt(i["date"]), _e(i["detail"])) for i in c["items"]]))
    if b["icb"]:
        parts.append(_band("Integrated Care Board changes", ["%s<br><small>%s</small>" % (
            _link(e["sources"][0], e["headline"]), _fmt(e["date"])) for e in b["icb"] if _safe_url(e["sources"][0])]))
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Your Hub briefing</title></head>"
        '<body style="margin:0;background:%s"><table width="100%%" cellpadding="0" cellspacing="0" role="presentation" style="background:%s"><tr><td align="center">'
        '<table width="640" cellpadding="0" cellspacing="0" role="presentation" style="max-width:640px;width:100%%">'
        '<tr><td style="background:%s;padding:30px 28px"><div style="font:700 12px/1.2 Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:%s">Medical Sales Intelligence Hub</div>'
        '<div style="font:700 28px/1.2 Georgia,serif;color:%s;margin-top:10px">Your Monday briefing</div>'
        '<div style="font:15px/1.5 Georgia,serif;color:%s;margin-top:8px">What changed in your specialities in the week to %s. Every line links to its source.</div></td></tr>'
        "%s"
        '<tr><td style="background:%s;padding:24px 28px"><div style="font:15px/1.5 Georgia,serif;color:%s">'
        '<a href="%s" style="color:%s;font-weight:600">Change your specialities or turn this off in My Hub</a>. '
        "A week with nothing new in your specialities sends no email.</div>"
        '<div style="font:12px/1.5 Arial,sans-serif;color:%s;margin-top:12px">Elevate and Thrive Ltd, company number 17154474, England and Wales.</div></td></tr>'
        "</table></td></tr></table></body></html>"
    ) % (WARM, WARM, NAVY, GOLD_ON_NAVY, LIGHT_ON_NAVY, LIGHT_ON_NAVY, _fmt(b["today"]),
         "".join(parts), NAVY, LIGHT_ON_NAVY, MY_HUB, GOLD_ON_NAVY, LIGHT_ON_NAVY)


def subject(b):
    names = [c["name"] for c in b["companies"]] + [s["label"] for s in b["specialities"] if s["news"] or s["awards"] or s["safety"]]
    if not names:
        names = ["your specialities"]
    head = names[0] + (" and %d more" % (len(names) - 1) if len(names) > 1 else "")
    return "Your Hub briefing: %d changes in %s" % (b["changes"], head) if b["changes"] != 1 else "Your Hub briefing: 1 change in %s" % head


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--members", required=True, help="JSON list of {key, specialities, companies}; opaque keys only")
    ap.add_argument("--out", required=True, help="folder for the dry-run previews")
    a = ap.parse_args(argv)
    today = datetime.date.fromisoformat(a.today)
    members = json.load(open(a.members, encoding="utf-8"))
    data = Data()
    os.makedirs(a.out, exist_ok=True)
    for m in members:
        b = build(m, today, data)
        if b is None:
            print("%s: nothing worth sending, skipped" % m["key"])
            continue
        with open(os.path.join(a.out, "briefing-%s.html" % m["key"]), "w", encoding="utf-8") as f:
            f.write(render_html(b))
        print("%s: %d changes, subject %r" % (m["key"], b["changes"], subject(b)))
    json.dump(plan(members, today, data), open(os.path.join(a.out, "plan.json"), "w"), indent=1)
    print("Dry run only. Nothing sent, nothing scheduled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
