#!/usr/bin/env python3
"""Fold the named people on a company desk's territory map into Build Your Network.

Asked for by Lou on 20/11/2026 after the Meril UK call: the territory map held 400+
named people (trust buyers, consultants, board members, regional clinicians), each read
from a public page with the date, but Build Your Network did not know about them, so a
rep searching the network by trust found less than the map already showed.

Input: a desk's areas file (for Meril: Partnerships/Meril-UK-2026-11/_build/territory-map/
meril-areas.json in OneDrive). Only items marked verified with a source are taken, and
only from the categories that name a person: Contacts, Board, Regional clinicians.

Output: data/kol-sources/territory-trust-people.json, in the kol-sources format that
scripts/build_kol_finder.py merges, with two additions that builder understands:
  * "specialities" per person (inferred from the role; board members carry none and are
    found by trust, region or search), and
  * "trustCode" per person, the ODS code the map filed them under.

Text on the map reads "Name, Role, Organisation. Why start here: ...". The why line is a
desk note for one company and is dropped here. Nothing is added that the map did not say.

Usage: python3 scripts/import_territory_people.py <areas.json> [--checked YYYY-MM-DD]
"""
import json, re, sys, pathlib, datetime, hashlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "kol-sources" / "territory-trust-people.json"
CATS = ("Contacts", "Board", "Regional clinicians")

SPEC_RULES = [
    (r"thoracic|colorectal|general surg|upper gi|hepato|laparoscop|robotic|da vinci|hernia|bariatric|minimally invasive", ["mis", "theatres"]),
    (r"orthopaed|trauma|arthroplast|spine|spinal", ["ortho"]),
    (r"cardiolog|cardiac|cardiothoracic|heart", ["cardiology"]),
    (r"urogyn", ["womens", "continence"]),
    (r"urolog", ["continence", "endourology"]),
    (r"gynae|obstet|maternity|women", ["womens"]),
    (r"vascular", ["vascsurg"]),
    (r"theatre|perioperative|anaesth|critical care", ["theatres", "anaesthesia"]),
    (r"sutur|wound closure|haemostat", ["closure", "theatres"]),
    (r"endoscop|gastro", ["endoscopy", "gastro"]),
    (r"tissue viability|wound", ["wound"]),
    (r"procure|buyer|purchas|supplies|commercial|category", ["theatres", "mis", "closure"]),
]
NAME_RE = re.compile(r"^((?:(?:Mr|Mrs|Ms|Miss|Dr|Prof|Professor|Sir|Dame)\.?\s+)?[A-Z][\w'’\-]*(?:\s+[A-Z][\w'’\-\.]*){0,4}(?:\s+(?:CBE|OBE|MBE|DL|KC))*)$")


def classes_for(cat, role):
    r = role.lower()
    if re.search(r"procure|buyer|purchas|supplies|commercial|category", r):
        return ["supply"]
    if cat == "Board":
        return ["trust"]
    if re.search(r"consultant|surgeon|physician|clinical lead|clinical director|professor|speaker|matron|nurse", r):
        return ["clinical"]
    return ["trust"]


def specs_for(cat, role):
    if cat == "Board":
        return []
    out = []
    for pat, ids in SPEC_RULES:
        if re.search(pat, role, re.I):
            out += [i for i in ids if i not in out]
    return out


ROLEWORD = re.compile(r"\b(director|officer|chief|consultant|manager|head|lead|buyer|nurse|chair|team|department|service)\b", re.I)


def is_name(s):
    w = s.split()
    return 2 <= len(w) <= 12 and len(s) <= 90 and not re.search(r"\d", s) and (len(w) <= 2 or not ROLEWORD.search(s)) \
        and all(x[0].isupper() or x[0] in "(" or x in ("de", "van", "von", "da", "le") for x in w)


ORGISH = re.compile(r"hospital|nhs|trust|universit|infirmary|teaching|health|care|centre|wythenshawe|freeman|royal|general", re.I)


def split(text, level="trusts"):
    t = re.split(r"\s+Why start here", str(text))[0].strip().rstrip(".")
    parts = [p.strip() for p in t.split(",")]
    if len(parts) < 2 or not is_name(parts[0]):
        return None
    name, rest = parts[0], ", ".join(parts[1:])
    org = None
    m = re.search(r"\(([^()]{4,80})\)\s*$", rest)
    if m and level != "trusts" and ORGISH.search(m.group(1)):
        org, rest = m.group(1), rest[:m.start()].strip()
    return name, rest.strip(" ,"), org


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    areas = json.load(open(sys.argv[1]))
    checked = datetime.date.today().isoformat()
    if "--checked" in sys.argv:
        checked = sys.argv[sys.argv.index("--checked") + 1]
    sources, people, seen, skipped = {}, [], set(), []
    groups = [("trusts", areas.get("trusts", {})), ("icbs", areas.get("icbs", {})), ("regions", areas.get("regions", {}))]
    for level, grp in groups:
        for code, t in grp.items():
            for it in t.get("items", []):
                if it.get("cat") not in CATS or it.get("verified") is not True or not str(it.get("src", "")).startswith("http"):
                    continue
                got = split(it.get("text", ""), level)
                if not got:
                    skipped.append(it.get("text", "")[:90])
                    continue
                name, role, org = got
                key = (re.sub(r"^(Mr|Mrs|Ms|Miss|Dr|Prof|Professor)\.?\s+", "", name).lower(), role.lower()[:40])
                if key in seen:
                    continue
                seen.add(key)
                sid = "terr-" + hashlib.sha1(it["src"].encode()).hexdigest()[:10]
                if sid not in sources:
                    sources[sid] = {"id": sid, "short": re.sub(r",? (read|checked) \d\d/\d\d/\d{4}", "", it.get("srcName") or "Public page")[:70],
                                    "body": t.get("name") if level == "trusts" else "Trust and professional body pages",
                                    "title": it.get("srcName") or "Public page", "url": it["src"],
                                    "note": "Read for a company desk territory map; the person's name and public role only.",
                                    "checked": checked}
                p = {"name": name, "body": None, "role": role, "organisation": org or (t.get("name") if level == "trusts" else None),
                     "term": "Page dated " + re.search(r"page dated (\d{4})", it["text"]).group(1) if re.search(r"page dated (\d{4})", it["text"]) else None,
                     "source": sid, "classes": classes_for(it["cat"], role), "specialities": specs_for(it["cat"], role)}
                if level == "trusts":
                    p["trustCode"] = code
                    p["trust"] = t.get("name")
                    p["title_basis"] = "Trust as filed on the territory map from the source page."
                people.append(p)
    doc = {"speciality": "theatres", "checked": checked,
           "_note": "Generated by scripts/import_territory_people.py from a desk territory map. Do not hand-edit; re-run.",
           "perPersonSpecialities": True, "bodies": [], "sources": list(sources.values()), "people": people}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    for x in skipped:
        print("  not a name, skipped:", x)
    print(f"wrote {OUT.name}: {len(people)} people from {len(sources)} pages")


if __name__ == "__main__":
    main()
