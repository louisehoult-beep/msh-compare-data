#!/usr/bin/env python3
"""Correct Meeting Prep trust profiles that print a speciality MEDIAN WAIT as a percentage.

Found 30/09/2026 while tracing a "high dermatology waits" reading of Manchester University
NHS FT on the Analysis page. Thirteen profiles in data/prep-config.json quoted NHS England
RTT median waits by treatment function (a figure in WEEKS) with a "%" sign and a label
that named a different measure: "% within 18 weeks", "share of the waiting list",
"proportion waiting over 18 weeks", "52-week breach rate". Every figure matched the
trust's own median wait for that treatment function in the June or July 2026 Incomplete
Provider return to 0.05, so the number was right and the unit and measure were wrong. Two
of them (RWP, RCB) also drew the wrong conclusion from it, calling the SHORTEST waits the
worst, so those two sentences are rewritten from the source, not just relabelled.

Re-runnable: a replacement already applied is skipped; an old sentence that is missing and
whose replacement is also missing stops the run (the profile changed underneath, re-check
it by hand). The source check is --verify <Incomplete-Provider XLSX> [...]: every
"<speciality> <n> weeks" figure in each replacement is read back from the workbook for the
month the replacement names.

Usage: python3 scripts/fix_speciality_wait_units.py [--write] [--verify JUN.xlsx JUL.xlsx]
"""
import argparse
import json
import re
import sys

PATH = "data/prep-config.json"

# code -> (old text, new text). Month in each new text is the RTT month the figures match.
FIXES = {
    "RA7": ("the specialities carrying the highest RTT waits under this code, notably Cardiology (14.8%), Trauma & Orthopaedics (12.6%) and Gynaecology (13.3%).",
            "the specialities with the longest median RTT waits under this code, notably Cardiology (14.8 weeks), Gynaecology (13.3 weeks) and Trauma & Orthopaedics (12.6 weeks) (median wait by treatment function, NHS England RTT, June 2026)."),
    "RXP": ("Specialty-level 52-week breach rates are highest in Dermatology (16.4%), General Surgery (13.1%) and Gynaecology (11.8%)",
            "The longest median waits by speciality are Dermatology (16.4 weeks), General Surgery (13.1 weeks) and Gynaecology (11.8 weeks) (median wait by treatment function, NHS England RTT, June 2026)"),
    "RXR": ("Specialities with the longest waits by percentage of the total waiting list include Gynaecology (14.2%), General Surgery (13.6%) and Dermatology (13.4%)",
            "The specialities with the longest median waits are Gynaecology (14.2 weeks), General Surgery (13.6 weeks) and Dermatology (13.4 weeks) (median wait by treatment function, NHS England RTT, June 2026)"),
    "RN5": ("The largest specialty pressures are General Surgery (21.9%) and Cardiology (14.8%)",
            "The longest median waits by speciality are General Surgery (21.9 weeks) and Cardiology (14.8 weeks) (median wait by treatment function, NHS England RTT, June 2026)"),
    "RGP": ("ENT is worst at 21.5% within 18 weeks, then Urology at 18.8% and Cardiology at 17.5%, while Dermatology at 8.4% and Trauma and Orthopaedics at 9.7% are the tightest",
            "ENT has the longest median wait at 21.5 weeks, then Urology at 18.8 weeks and Cardiology at 17.5 weeks, while Dermatology at 8.4 weeks and Trauma and Orthopaedics at 9.7 weeks are the shortest (median wait by treatment function, NHS England RTT, June 2026)"),
    "RJ2": ("Specialty-level 18-week performance is weakest in Urology (17.3%) and ENT (16.8%), with General Surgery, Trauma & Orthopaedics, Cardiology and Gynaecology all also below the standard, indicating pressure spread across several surgical specialties rather than concentrated in one.",
            "The longest median waits by speciality are Urology (17.3 weeks) and ENT (16.8 weeks), followed by Gynaecology (14.7 weeks), Trauma & Orthopaedics (13.4 weeks), Cardiology (11.9 weeks) and General Surgery (11.8 weeks), so the pressure is spread across several surgical specialties rather than concentrated in one (median wait by treatment function, NHS England RTT, June 2026)."),
    "RXF": ("Its highest-pressure specialities on the 18-week measure are Trauma & Orthopaedics (16.4%) and ENT (15.4%).",
            "Its longest median waits by speciality are Trauma & Orthopaedics (16.4 weeks) and ENT (15.4 weeks) (median wait by treatment function, NHS England RTT, June 2026)."),
    "RNS": ("(General Surgery 12.0%, Trauma & Orthopaedics 14.9%, ENT 17.1%, Dermatology 17.7% and Gynaecology 20.0% all showing longer specialty-level waits)",
            "(median waits of General Surgery 12.0 weeks, Trauma & Orthopaedics 14.9 weeks, ENT 17.1 weeks, Dermatology 17.7 weeks and Gynaecology 20.0 weeks, by treatment function, NHS England RTT, June 2026)"),
    "RHU": ("The specialty-level waits show Trauma & Orthopaedics (18.6%), Gynaecology (15.2%) and ENT (15.7%) as the longest 18-week performers among those recorded",
            "The longest median waits by speciality are Trauma & Orthopaedics (18.6 weeks), ENT (15.7 weeks) and Gynaecology (15.2 weeks) (median wait by treatment function, NHS England RTT, June 2026)"),
    "RXK": ("Longest specialty waits are in ENT at 21.3% within 18 weeks and Cardiology at 18.4%, with Ophthalmology the strongest performer at 8.6%.",
            "The longest median waits by speciality are ENT at 21.3 weeks and Cardiology at 18.4 weeks, with Ophthalmology the shortest at 8.6 weeks (median wait by treatment function, NHS England RTT, June 2026)."),
    "R0D": ("The specialties with the highest proportion of patients waiting over 18 weeks are Gynaecology (18.7%) and Trauma & Orthopaedics (15.8%), with ENT at 14.9% and Ophthalmology at 11.6%",
            "The longest median waits by speciality are Gynaecology (18.7 weeks) and Trauma & Orthopaedics (15.8 weeks), with ENT at 14.9 weeks and Ophthalmology at 11.6 weeks (median wait by treatment function, NHS England RTT, July 2026)"),
    "RWP": ("By specialty, the widest waits recorded were Cardiology (8.0%), Dermatology (8.9%) and Ophthalmology (12.4%) treated within 18 weeks, all well below the national standard.",
            "By speciality, the longest median waits are Trauma & Orthopaedics (18.1 weeks) and ENT (18.1 weeks), then Gynaecology (14.7 weeks), Urology (14.6 weeks) and General Surgery (14.5 weeks), while Cardiology (8.0 weeks) and Dermatology (8.9 weeks) are the shortest (median wait by treatment function, NHS England RTT, July 2026)."),
    "RCB": ("Worst-performing specialities against the 18-week standard are General Surgery (3.7%), Urology (14.4%) and Cardiology (14.0%), with Gynaecology also under pressure at 17.6%.",
            "The longest median waits by speciality are Gynaecology (18.8 weeks) and ENT (15.9 weeks), then Dermatology (14.5 weeks), Urology (14.3 weeks) and Cardiology (14.2 weeks), while General Surgery is the shortest at 1.9 weeks (median wait by treatment function, NHS England RTT, July 2026)."),
}

RTT_FN = {
    "Trauma & Orthopaedics": "Trauma and Orthopaedic Service", "Trauma and Orthopaedics": "Trauma and Orthopaedic Service",
    "ENT": "Ear Nose and Throat Service", "Urology": "Urology Service", "Cardiology": "Cardiology Service",
    "Gynaecology": "Gynaecology Service", "General Surgery": "General Surgery Service",
    "Dermatology": "Dermatology Service", "Ophthalmology": "Ophthalmology Service",
}


def read_rtt(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)["Provider"]
    rows = ws.iter_rows(values_only=True)
    period = None
    for r in rows:
        cells = [str(c).strip() if c is not None else "" for c in r]
        for j, c in enumerate(cells[:-1]):
            if c.rstrip(":").lower() == "period":
                period = cells[j + 1]
        if "Provider Code" in cells:
            low = [c.lower() for c in cells]
            break
    ci, tf = low.index("provider code"), low.index("treatment function")
    md = low.index("average (median) waiting time (in weeks)")
    out = {}
    for r in rows:
        if r[ci] and isinstance(r[md], (int, float)):
            out.setdefault(r[ci], {})[r[tf]] = round(r[md], 1)
    return period, out


def verify(workbooks):
    months = dict(read_rtt(p) for p in workbooks)
    bad = 0
    for code, (_old, new) in FIXES.items():
        month = re.search(r"NHS England RTT, (\w+ 2026)", new).group(1)
        data = months.get(month)
        if data is None:
            print(f"[{code}] no workbook supplied for {month}"); bad += 1; continue
        for name, fn in RTT_FN.items():
            for m in re.finditer(re.escape(name) + r"\D{0,40}?(\d+\.\d) weeks", new):
                got = data.get(code, {}).get(fn)
                if got is None or abs(got - float(m.group(1))) > 0.05:
                    print(f"[{code}] {name} {m.group(1)} weeks does not match {month} ({got})"); bad += 1
    print("verify:", "OK" if not bad else f"{bad} mismatch(es)")
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--verify", nargs="*")
    a = ap.parse_args()
    if a.verify and not verify(a.verify):
        sys.exit(1)
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    by = {t.get("code"): t for t in d["trusts"]}
    changed = 0
    for code, (old, new) in FIXES.items():
        t = by.get(code)
        ctx = (t or {}).get("context") or ""
        if new in ctx:
            continue
        if old not in ctx:
            sys.exit(f"STOP: [{code}] neither the old nor the corrected sentence is present; re-check by hand.")
        t["context"] = ctx.replace(old, new)
        changed += 1
    print(f"{changed} profile(s) corrected, {len(FIXES) - changed} already correct")
    if a.write and changed:
        # Preserve the file's existing formatting convention.
        indent = 1 if raw.startswith("{\n ") and not raw.startswith("{\n  ") else (2 if raw.startswith("{\n  ") else None)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=indent)
            if raw.endswith("\n"):
                f.write("\n")


if __name__ == "__main__":
    main()
