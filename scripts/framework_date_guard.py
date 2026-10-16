"""Guard: one framework, one expiry date, and no unnamed expiry dates.

WHY (16/10/2026): Hub page 2802's calendar note said the compression framework
(Vascular Therapy and Associated Products, 2023/S 000-012286) expires in
"February 2028", then two sentences later spoke of a "successor framework" and
"the confirmed 26 Feb 2027 expiry". Those belong to a DIFFERENT framework
(IC/IR, 2021/S 000-017565, successor Total Cardiology and Vascular Solutions),
but neither sentence named it, so the paragraph read as a self-contradiction and
nothing in the build or verify gate noticed.

Two rules, applied to the visible text of a page (or any prose field):

  1. A sentence that names a known framework (reference or exact name from
     data/frameworks.json) and gives an expiry date must give THAT framework's
     end date from frameworks.json.
  2. A paragraph that gives expiry dates in two or more different years must
     name the framework (reference or known name) in every sentence that carries
     an expiry date. Unnamed expiry dates next to differing ones are what made
     2802 unreadable.

CLI: framework_date_guard.py FILE.html [FILE...]   (exit 1 on findings)
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMEWORKS = os.path.join(HERE, "..", "data", "frameworks.json")

MONTHS = {m: i + 1 for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split())}
DATE = re.compile(r"\b(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(20\d\d)\b")
CUE = re.compile(r"(?i)\b(expires?|expired|expiry|expiring|ends?|ending|live to|runs? to|to|until|by)\b")
STRONG_CUE = re.compile(r"(?i)\b(expires?|expiry|expiring|ends?|ending|live to|runs? to)\b")
CODE = re.compile(r"\b[A-Z]{2,}\d+\b")  # TOS3, SBS10142: a named framework shorthand
REF = re.compile(r"\b20\d\d/S\s?000-\d{5,6}\b")


def load_frameworks(path=FRAMEWORKS):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("frameworks", data)
    out = []
    for fw in items:
        ref, name, ends = fw.get("reference"), fw.get("name"), fw.get("ends")
        if not (ref and ends):
            continue
        m = DATE.search(ends)
        if not m:
            continue
        out.append({"ref": ref.replace(" ", ""), "name": name or "",
                    "end": (int(m.group(1)) if m.group(1) else None,
                            MONTHS[m.group(2).lower()[:3]], int(m.group(3)))})
    return out


def visible_paragraphs(raw):
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)</(p|div|li|td|tr|h\d|section)>|<br\s*/?>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    for para in text.split("\n"):
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            yield para


def sentences(par):
    return [s for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z\"'])", par) if s.strip()]


def expiry_dates(sentence):
    """Dates tied to an expiry cue: cue within 25 chars before or 60 after, and the
    date is not a start date ("started 28 Feb 2024", "estimated start (27 Feb 2027)")."""
    found = []
    for m in DATE.finditer(sentence):
        before = sentence[max(0, m.start() - 25):m.start()]
        after = sentence[m.end():m.end() + 60]
        if re.search(r"(?i)\b(start|starts|started|starting|begin|begins|from)\b[^.;]{0,12}$", before):
            continue
        if STRONG_CUE.search(before) or STRONG_CUE.search(after):
            d = int(m.group(1)) if m.group(1) else None
            found.append((d, MONTHS[m.group(2).lower()[:3]], int(m.group(3)), m.group(0)))
    return found


def names_in(sentence, fws):
    s = sentence.replace(" ", "")
    hits = [f for f in fws if f["ref"] in s]
    low = sentence.lower()
    hits += [f for f in fws if f["name"] and f["name"].lower() in low and f not in hits]
    return hits, bool(REF.search(sentence.replace("\u00a0", " ")) or CODE.search(sentence))


def check_text(raw, fws=None):
    fws = load_frameworks() if fws is None else fws
    problems = []
    for par in visible_paragraphs(raw):
        per_sentence = []
        for s in sentences(par):
            dates = expiry_dates(s)
            if not dates:
                continue
            hits, has_ref = names_in(s, fws)
            per_sentence.append((s, dates, hits, has_ref))
            # Rule 1: only when exactly one known framework is named in the sentence.
            if len(hits) == 1:
                want = hits[0]["end"]
                for d, mth, yr, txt in dates:
                    if (mth, yr) != (want[1], want[2]) or (d and want[0] and d != want[0]):
                        problems.append("%s expiry given as %r but frameworks.json says %s: %s"
                                        % (hits[0]["ref"], txt, "%s/%s/%s" % want, s[:140]))
        # Rule 2
        years = {yr for _, ds, _, _ in per_sentence for _, _, yr, _ in ds}
        if len(years) >= 2:
            named_so_far = False
            for s in sentences(par):
                h, r = names_in(s, fws)
                named_so_far = named_so_far or bool(h) or r
                dates = expiry_dates(s)
                if dates and not named_so_far:
                    problems.append("expiry date %r sits in a paragraph with expiries in other years "
                                    "but names no framework: %s" % (dates[0][3], s[:140]))
    return problems


def main(argv):
    fws = load_frameworks()
    bad = 0
    for path in argv:
        with open(path, encoding="utf-8") as f:
            probs = check_text(f.read(), fws)
        for p in probs:
            print("FAIL %s: %s" % (path, p))
        bad += len(probs)
    if not bad:
        print("framework dates: OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
