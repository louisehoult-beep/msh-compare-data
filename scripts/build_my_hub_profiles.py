#!/usr/bin/env python3
"""Label every My Hub catalogue page with the nav profiles that list it.

    python3 scripts/build_my_hub_profiles.py --nav <file holding snippet 1331 as served> [--check]

Lou, 01/10/2026: a member can add a page from any profile, and the picker must
make that obvious. Each item in hub/my-hub-catalogue.json gets `profiles`: the
profile keys (company, rep, clinical, procurement, recruit) whose nav carries
its URL, in that order. A page in no profile's nav gets []; specialities are
reached through Find Your Speciality from every profile, so the picker shows
them under every profile chip whatever this list says.

SOURCE IS THE LIVE NAV, NOT routes.json. Landing-Page-2026-09/routes.json has
drifted from the live snippet 1331 before (hub-nav-grouped-menu). Snippet 1331
renders verbatim into every Hub page, even for a logged-out request, so save a
page and pass it:

    curl -s https://medsalesintelligencehub.co.uk/medical-sales-hub/ -o /tmp/nav.html

If the page carries the snippet twice (a known render bug), the LAST copy is
the one that runs, so the last NAV_BY_ROLE is read.

Writes the catalogue in place with its own serialisation (indent=1,
ensure_ascii=False, no trailing newline) and records the source in
`_profilesFrom`. --check exits 1 if the file would change and writes nothing.
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(HERE, "hub", "my-hub-catalogue.json")
ROLES = ["company", "rep", "clinical", "procurement", "recruit"]
PAIR = re.compile(r'\[\s*"((?:[^"\\]|\\.)*)"\s*,\s*"([^"]*)"\s*\]')


def norm(u):
    u = re.sub(r"^https?://(www\.)?medsalesintelligencehub\.co\.uk", "", u.strip())
    u = u.split("#")[0].split("?")[0]
    return u if u.endswith("/") else u + "/"


def nav_by_role(text):
    starts = [m.start() for m in re.finditer(r"var NAV_BY_ROLE\s*=\s*\{", text)]
    if not starts:
        raise SystemExit("no NAV_BY_ROLE in the nav file: is it a saved Hub page?")
    block = text[starts[-1]:]
    end = block.find("\n  };")
    if end == -1:
        raise SystemExit("NAV_BY_ROLE has no closing '  };' line: has the snippet's layout changed?")
    block = block[:end]
    heads = list(re.finditer(r'"?(%s)"?\s*:\s*\[' % "|".join(ROLES), block))
    found = {}
    for i, h in enumerate(heads):
        seg = block[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(block)]
        found[h.group(1)] = [norm(u) for _, u in PAIR.findall(seg)]
    missing = [r for r in ROLES if not found.get(r)]
    if missing:
        raise SystemExit("the nav file has no pages for: " + ", ".join(missing))
    return found, block


def label(cat, navs):
    out = json.loads(json.dumps(cat))
    for it in out["items"]:
        base = it["url"].split("#")[0]   # a tool view takes its page's profiles
        it["profiles"] = [r for r in ROLES if base in set(navs[r])]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--nav", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    with open(a.nav, encoding="utf-8") as f:
        text = f.read()
    navs, block = nav_by_role(text)
    with open(CAT, encoding="utf-8") as f:
        before = f.read()
    cat = label(json.loads(before), navs)
    cat["_profilesFrom"] = {
        "source": "snippet 1331 NAV_BY_ROLE as served",
        "sha256": hashlib.sha256(block.encode("utf-8")).hexdigest()[:16],
        "navPages": {r: len(set(navs[r])) for r in ROLES},
    }
    after = json.dumps(cat, indent=1, ensure_ascii=False)
    urls = {i["url"] for i in cat["items"]}
    stray = sorted({u for r in ROLES for u in navs[r]} - urls)
    if stray:
        print("nav pages not in the catalogue (not pickable): " + ", ".join(stray))
    none = sorted(i["id"] for i in cat["items"] if not i["profiles"] and i["group"] != "specialities")
    if none:
        print("catalogue pages in no profile nav: " + ", ".join(none))
    if a.check:
        old = json.loads(before)
        old.pop("_profilesFrom", None)
        new = json.loads(after)
        new.pop("_profilesFrom", None)
        if old != new:
            print("CHANGED: profiles differ from the live nav. Re-run without --check.")
            return 1
        print("unchanged")
        return 0
    with open(CAT, "w", encoding="utf-8") as f:
        f.write(after)
    print("labelled %d items from %s" % (len(cat["items"]), ", ".join("%s %d" % (r, len(set(navs[r]))) for r in ROLES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
