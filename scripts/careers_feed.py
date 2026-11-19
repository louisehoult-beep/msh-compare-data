#!/usr/bin/env python3
"""careers_feed.py — the Live Desk app's Careers tab, and its new-role alerts.

Added 27/10/2026 (Lou: "Careers need to go on the app").

WHAT IT PUBLISHES
  The roles the Hub's Career Centre already lists (careers_relevance.relevant_roles:
  UK roles read from a supplier's own applicant-tracking page whose title matches
  config/careers-relevant-roles.json), written as one JSON document to the Supabase
  row livedesk_feed id='careers'. The app reads it through the livedesk function's
  'careers' action, behind the same access check as the Desk.

  Nothing is added to what the Hub publishes: same roles, same links (each one the
  employer's own listing), same checked-on date. Only two things are derived here:

    regions      from an area named in the job title ("... (Scotland)", "... - South
                 West"), else from the location the company published. Never guessed
                 from a company's head office. No area stated -> [] and the app says
                 "area not stated"; such a role matches every area filter.
    specialities from the supplier's own speciality labels in
                 data/supplier-index.json, kept only where a label is exactly one
                 of the app's speciality labels (after normalising case, "&"/"and"
                 and punctuation). A supplier with none matching shows under every
                 speciality filter as "all", never under a wrong one.

ROLE ALERTS
  A role is NEW when its URL was not in the previous published careers row. Devices
  that switched on role alerts (livedesk_devices.role_alerts) get one push per run
  for new roles that match their regions and specialities (none chosen = all).
  The first ever publish sends nothing (there is no previous row to compare with).

    python3 scripts/careers_feed.py build            # write data/livedesk-careers.json only
    python3 scripts/careers_feed.py publish          # + upsert + alerts (needs secrets)
    python3 scripts/careers_feed.py publish --dry-run

Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY (publish); FCM_SERVICE_ACCOUNT (alerts).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import careers_relevance  # noqa: E402

CAREERS = os.path.join(ROOT, "data", "supplier-careers.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")
ALERT_CONFIG = os.path.join(ROOT, "alerts", "config.json")
OUT = os.path.join(ROOT, "data", "livedesk-careers.json")
FEED_TABLE = "livedesk_feed"
FEED_ID = "careers"
HUB_CAREERS = "https://medsalesintelligencehub.co.uk/medical-sales-hub/careers/"

# The areas offered in the app. Keep in step with livedesk-app/src/regions.js and
# supabase/functions/livedesk/rules.ts (REGIONS).
REGIONS = [
    ("london", "London"),
    ("south-east", "South East"),
    ("south-west", "South West"),
    ("east-of-england", "East of England"),
    ("east-midlands", "East Midlands"),
    ("west-midlands", "West Midlands"),
    ("north-west", "North West"),
    ("north-east", "North East"),
    ("yorkshire-and-humber", "Yorkshire and the Humber"),
    ("scotland", "Scotland"),
    ("wales", "Wales"),
    ("northern-ireland", "Northern Ireland"),
]

# Places that are not in the UK but contain a UK word ("New South Wales"). A location
# naming one is dropped even if the source flagged it UK.
NOT_UK = re.compile(r"\b(new south wales|nsw|australia|victoria, au|queensland|new england|"
                    r"new brunswick|new jersey|new york|new hampshire|new mexico|"
                    r"ireland, republic|republic of ireland|dublin|cork|galway)\b", re.I)

# Place or area word -> region. Whole-word matches only, longest first. Only places
# this was checked for; a place not here gives region "" (area not stated), not a guess.
PLACES = {
    "london": "london", "rainham": "london", "croydon": "london", "wembley": "london",
    "south east": "south-east", "kent": "south-east", "crawley": "south-east",
    "witney": "south-east", "oxford": "south-east", "oxfordshire": "south-east",
    "abingdon": "south-east", "maidenhead": "south-east",
    "brighton": "south-east", "guildford": "south-east", "southampton": "south-east",
    "slough": "south-east", "milton keynes": "south-east", "surrey": "south-east",
    "sussex": "south-east", "hampshire": "south-east", "berkshire": "south-east",
    "south west": "south-west", "plymouth": "south-west", "bristol": "south-west",
    "exeter": "south-west", "devon": "south-west",
    "cornwall": "south-west", "somerset": "south-west", "dorset": "south-west",
    "east of england": "east-of-england", "east anglia": "east-of-england",
    "midlands": ("east-midlands", "west-midlands"), "elstree": "east-of-england",
    "loughton": "east-of-england", "cambridge": "east-of-england",
    "norwich": "east-of-england", "essex": "east-of-england",
    "hertfordshire": "east-of-england", "suffolk": "east-of-england",
    "norfolk": "east-of-england", "ipswich": "east-of-england",
    "east midlands": "east-midlands", "nottingham": "east-midlands",
    "leicester": "east-midlands", "derby": "east-midlands", "lincoln": "east-midlands",
    "northampton": "east-midlands",
    "west midlands": "west-midlands", "coventry": "west-midlands",
    "birmingham": "west-midlands", "solihull": "west-midlands",
    "stoke on trent": "west-midlands", "stoke-on-trent": "west-midlands",
    "wolverhampton": "west-midlands", "worcester": "west-midlands",
    "north west": "north-west", "manchester": "north-west", "liverpool": "north-west",
    "preston": "north-west", "warrington": "north-west", "cheshire": "north-west",
    "lancashire": "north-west",
    "north east": "north-east", "newcastle": "north-east", "sunderland": "north-east",
    "durham": "north-east", "gateshead": "north-east", "middlesbrough": "north-east",
    "yorkshire": "yorkshire-and-humber", "leeds": "yorkshire-and-humber",
    "sheffield": "yorkshire-and-humber", "bradford": "yorkshire-and-humber",
    "hull": "yorkshire-and-humber", "york": "yorkshire-and-humber",
    "scotland": "scotland", "glasgow": "scotland", "edinburgh": "scotland",
    "dundee": "scotland", "aberdeen": "scotland",
    "wales": "wales", "cardiff": "wales", "swansea": "wales",
    "northern ireland": "northern-ireland", "belfast": "northern-ireland",
}
_PLACE_RE = re.compile(r"(?<![a-z])(" + "|".join(
    re.escape(p) for p in sorted(PLACES, key=len, reverse=True)) + r")(?![a-z])", re.I)


def _regions_in(text: str) -> set[str]:
    out: set[str] = set()
    for m in _PLACE_RE.finditer(text or ""):
        v = PLACES[m.group(1).lower()]
        out.update((v,) if isinstance(v, str) else v)
    return out


def regions_of(role: dict) -> list[str] | None:
    """Areas the role covers. [] = UK but area not stated; None = drop (not UK after all).
    A territory named in the title (\"(Wales)\", \"South West\") wins over the company's
    base office, which says where the desk is, not where the role works."""
    loc = role.get("location") or ""
    if NOT_UK.search(loc):
        return None
    found = _regions_in(role.get("title") or "") or _regions_in(loc)
    return sorted(found)


def _norm(label: str) -> str:
    s = (label or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def speciality_slugs(supplier_name: str, index: dict, app_specs: list[dict]) -> list[str]:
    by_label = {_norm(s["label"]): s["slug"] for s in app_specs}
    row = index.get(supplier_name) or {}
    out = []
    for lab in row.get("specialities") or []:
        slug = by_label.get(_norm(lab))
        if slug and slug not in out:
            out.append(slug)
    return out


def build(careers_doc: dict, index_doc: dict, app_specs: list[dict], compiled,
          today: str | None = None) -> dict:
    index = {s.get("name"): s for s in (index_doc.get("suppliers") or [])}
    roles, _ = careers_relevance.relevant_roles(careers_doc, compiled)
    labels = {k: l for k, l, _p in compiled["categories"]}
    rows, dropped = [], 0
    for r in roles:
        regions = regions_of(r)
        if regions is None:
            dropped += 1
            continue
        rows.append({
            "title": r["title"],
            "company": r["supplier"],
            "location": r.get("location") or "",
            "regions": regions,
            "kind": labels.get(r["category"], ""),
            "specialities": speciality_slugs(r["supplier"], index, app_specs),
            "url": r["url"],
            "checked": r.get("checkedOn") or "",
            "new": bool(r.get("new")),
        })
    rows.sort(key=lambda x: (x["company"].lower(), x["title"].lower()))
    return {
        "generated": today or _dt.date.today().isoformat(),
        "dataAsOf": careers_doc.get("generatedOn", ""),
        "regions": [{"slug": s, "label": l} for s, l in REGIONS],
        "count": len(rows),
        "suppliersRead": len({x["company"] for x in rows}),
        "source": "Each role is the employer's own listing, read from its careers page. "
                  "Only suppliers whose careers page the Hub can read role by role appear here.",
        "hub": HUB_CAREERS,
        "roles": rows,
    }


def new_roles(doc: dict, previous: dict | None) -> list[dict]:
    """Roles whose URL was not in the previous document. First publish -> none."""
    if not previous or not isinstance(previous.get("roles"), list):
        return []
    seen = {r.get("url") for r in previous["roles"]}
    return [r for r in doc["roles"] if r["url"] not in seen]


def matches(role: dict, regions: list[str], specs: list[str]) -> bool:
    """A device's choice against a role. Empty choice = everything. A role with no
    stated area, or no mapped speciality, is not excluded by a choice it cannot answer."""
    if regions and role["regions"] and not set(role["regions"]) & set(regions):
        return False
    if specs and role["specialities"] and not set(role["specialities"]) & set(specs):
        return False
    return True


def role_message(roles: list[dict]) -> dict:
    n = len(roles)
    first = roles[0]
    body = "%s, %s" % (first["title"], first["company"])
    if n > 1:
        body += " and %d more" % (n - 1)
    return {
        "title": "New role%s on the Live Desk" % ("" if n == 1 else "s"),
        "body": body[:160],
        "url": HUB_CAREERS,
        "tag": "msh-careers",
        "hub": [{"l": "Careers", "u": HUB_CAREERS}],
        "items": [{"t": "%s — %s" % (r["title"], r["company"]), "u": r["url"],
                   "sp": r["location"]} for r in roles[:8]],
        "more": max(0, n - 8),
        "kind": "careers",
    }


# --------------------------------------------------------------------------
def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_from_disk() -> dict:
    return build(_load(CAREERS), _load(INDEX), _load(ALERT_CONFIG)["specialities"],
                 careers_relevance.load_config())


def _rest(env, method, query, body=None, prefer=None):
    import urllib.request
    base = env["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    req = urllib.request.Request(base + query, method=method)
    req.add_header("apikey", env["SUPABASE_SERVICE_KEY"])
    req.add_header("Authorization", "Bearer " + env["SUPABASE_SERVICE_KEY"])
    req.add_header("Accept", "application/json")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)
    with urllib.request.urlopen(req, data, timeout=30) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


def cmd_build(_a) -> int:
    doc = build_from_disk()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("careers: %d roles from %d suppliers -> %s" % (doc["count"], doc["suppliersRead"], OUT))
    return 0


def cmd_publish(args, env=os.environ, log=print) -> int:
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if not env.get(k):
            log("careers: %s not set — nothing published" % k)
            return 0
    doc = build_from_disk()
    prev_rows = _rest(env, "GET", "%s?select=payload&id=eq.%s" % (FEED_TABLE, FEED_ID)) or []
    previous = prev_rows[0]["payload"] if prev_rows else None
    fresh = new_roles(doc, previous)
    log("careers: %d roles, %d new since the last publish%s" % (
        doc["count"], len(fresh), "" if previous else " (first publish: no alerts)"))
    if args.dry_run:
        for r in fresh:
            log("  new: %s | %s | %s" % (r["title"], r["company"], ",".join(r["regions"]) or "area not stated"))
        return 0
    _rest(env, "POST", "%s?on_conflict=id" % FEED_TABLE,
          {"id": FEED_ID, "payload": doc, "published_at": _dt.datetime.now(_dt.timezone.utc).isoformat()},
          "resolution=merge-duplicates,return=minimal")
    if fresh and env.get("FCM_SERVICE_ACCOUNT", "").strip():
        try:
            import fcm_push
            sender = fcm_push.sender(json.loads(env["FCM_SERVICE_ACCOUNT"]))
            devices = _rest(env, "GET", "livedesk_push_targets?select=token,platform,specialities,"
                            "regions,role_alerts&role_alerts=eq.true&limit=5000") or []
            sent = failed = 0
            for d in devices:
                mine = [r for r in fresh if matches(r, d.get("regions") or [], d.get("specialities") or [])]
                if not mine:
                    continue
                ok, gone, detail = sender(d, role_message(mine))
                if ok:
                    sent += 1
                else:
                    failed += 1
                    log("  FAILED a device (%s)" % detail[:120])
                    if gone:
                        _rest(env, "DELETE", "livedesk_devices?token=eq.%s" % urllib.parse.quote(d["token"], safe=""),
                              prefer="return=minimal")
            log("careers: role alerts sent=%d failed=%d (devices opted in: %d)" % (sent, failed, len(devices)))
        except Exception as exc:   # noqa: BLE001 — the publish already succeeded
            log("careers: role alerts FAILED (%s) — feed unaffected" % str(exc)[:200])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    p = sub.add_parser("publish")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_publish)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
