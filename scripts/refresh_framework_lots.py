#!/usr/bin/env python3
"""Which LOT(S) each supplier holds on each NHS Supply Chain framework, read only
from the framework owner's own published sources.

WHY THIS EXISTS
---------------
Lou's standing rule, 30/09/2026: "When they are on a framework I want the company
profile to pull the lots too." Until then data/frameworks.json carried a lot map
for ONE framework of 122 (Patient Temperature Management, whose brief happens to
publish a supplier-by-lot table), so the Company Intelligence Report named the
framework and left the rep to find the lot, which is the question they actually
get asked in a call.

THE RULE (printed into data/framework-lots.json so a reader can judge it)
-------------------------------------------------------------------------
A supplier is shown on a lot ONLY where one of these, published by the framework
owner for that framework, names that supplier against that lot:

  1. brief-lists   NHS Supply Chain's own contract launch brief, where its
                   Suppliers section lists the awarded suppliers lot by lot
                   ("Lot 1" then a list, "Lot 2" then a list).
  2. brief-table   The same brief, where it gives a supplier-by-lot TABLE. This
                   is already read by scripts/refresh_frameworks.py and kept.
  3. matrix        The Product / Supplier Matrix spreadsheet attached to that
                   brief's own Downloads section (azuksappnpdsa01 blob store),
                   where the sheet has an explicit lot axis: a "Supplier | Lot 1 |
                   Lot 2" header with marks, or a lot heading above a supplier
                   header row with products beneath. A supplier is on a lot there
                   only if it has at least one mark or product in that lot.
  4. fts-award     The Find a Tender contract award notice for the framework's
                   own procurement (OCDS awards[].relatedLots + suppliers), reached
                   through the tender notice the brief's own reference names,
                   never by title search. Read only where 1-3 name no lots, so
                   two lot numbering schemes are never mixed on one card.

Nothing is inferred from product ranges, specialities, catalogue categories or
the lot titles. A framework the brief breaks into lots but for which no source
above names who holds which lot gets lotStatus "notPublished", and the report
says "lot not published by NHS Supply Chain" for it. A framework whose brief lists
no lots at all gets "noLots".

NAME MATCHING (same rule as scripts/company_match.py, the repo's alias rule)
---------------------------------------------------------------------------
A lot source names suppliers its own way ("Olympus (Keymed)", "HARTMANN",
"B Braun Medical Limited"). Lots are attached to the EXACT supplier string the
brief uses, because that is the key the report matches a company on. A lot-source
name attaches to a brief name only when, within that one framework:
  (a) brief_names.clean() then company_match.key() of both are identical, or
  (b) both resolve, under company_match.resolve() against data/supplier-seed.json
      names and recorded aliases, to the same single Hub company.
No fuzzy, substring or edit-distance matching. A name that matches no brief
supplier, or more than one, is recorded in `unresolved` with the reason and
attaches to nothing.

USAGE
    python3 scripts/refresh_framework_lots.py                  # fetch briefs + matrices, write data/framework-lots.json, attach
    python3 scripts/refresh_framework_lots.py --cache DIR      # reuse/save brief HTML and xlsx in DIR
    python3 scripts/refresh_framework_lots.py --fts FILE.json  # also read Find a Tender award releases, keyed by tender notice id
    python3 scripts/refresh_framework_lots.py --attach-only    # re-attach data/framework-lots.json to data/frameworks.json

refresh_frameworks.py calls attach() on every run, so a rebuilt frameworks.json
keeps its lots without re-fetching anything.
"""
import argparse
import datetime
import html as H
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brief_names  # noqa: E402
import company_match  # noqa: E402

FW_PATH = "data/frameworks.json"
LOTS_PATH = "data/framework-lots.json"
SEED_PATH = "data/supplier-seed.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
PAUSE = 1.0
OWNER = "NHS Supply Chain"

RULE = (
    "A supplier is shown on a lot ONLY where the framework owner's own published "
    "source for that framework names it against that lot: the NHS Supply Chain "
    "contract launch brief's lot-by-lot supplier lists or supplier-by-lot table, the "
    "Product/Supplier Matrix spreadsheet attached to that brief (only where the sheet "
    "has an explicit lot axis, and only where the supplier has a mark or a product in "
    "that lot), or the Find a Tender contract award notice for that framework's own "
    "procurement. Nothing is inferred from product ranges, specialities or lot titles. "
    "Lots attach to the exact supplier string the brief uses; a source name attaches "
    "only where its normalised form (brief_names.clean + company_match.key) equals "
    "that brief name's, or both resolve to the same single Hub company under the "
    "seed's recorded aliases. Unmatched names are listed in `unresolved`, never "
    "guessed. Where the brief breaks a framework into lots but no source names who "
    "holds which, lotStatus is 'notPublished' and the report says so.")

STATUSES = ("published", "notPublished", "noLots")

NUM_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
             "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
             "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
             "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
             "twenty": "20"}

LOT_HEAD = re.compile(
    r"(?i)^\s*lot\s*[:#]?\s*(\d{1,2}(?:\.\d{1,2})?[a-z]?|" + "|".join(NUM_WORDS) + r")\b")


def lot_label(raw):
    """'Lot One' / 'Lot 01' / 'LOT 1.1' / 'Lot 4a' -> 'Lot 1' / 'Lot 1' / 'Lot 1.1' / 'Lot 4a'.
    None when the text does not start with a lot number."""
    m = LOT_HEAD.match(str(raw or ""))
    if not m:
        return None
    n = m.group(1).lower()
    n = NUM_WORDS.get(n, n)
    parts = n.split(".")
    parts[0] = re.sub(r"^0+(?=\d)", "", parts[0])
    return "Lot " + ".".join(parts)


def lot_sort_key(label):
    nums = re.findall(r"\d+|[a-z]", label.lower())
    return [int(x) if x.isdigit() else ord(x) for x in nums]


def text_of(fragment):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|ul|ol)>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return H.unescape(s).replace("\xa0", " ")


def section(h, sid):
    m = re.search(r'(?is)<div[^>]+id="%s".*?(?=<div[^>]+id="(?!%s)|<footer|</body)' % (sid, sid), h)
    return m.group(0) if m else ""


# ---------------------------------------------------------------- brief ----

def parse_lot_titles(h):
    """{'Lot 1': 'Internal Urinary Catheters and Accessories', ...} from the brief's
    Product Categories section (items may be list items or paragraphs). Empty when
    the brief names no lots."""
    out = {}
    for sid in ("categories", "overview"):
        blk = section(h, sid)
        for ln in text_of(blk).split("\n"):
            t = " ".join(ln.split())
            lab = lot_label(t)
            if not lab or len(t) > 200:
                continue
            title = LOT_HEAD.sub("", t, count=1).strip(" :–—-.")
            if lab not in out:
                out[lab] = title or None
        if out:
            break
    return out


def stated_lot_count(h):
    """The number of lots the brief itself states ("There are 18 lots on this
    framework", "There is one lot ..."), or None."""
    t = " ".join(text_of(h).split())
    m = re.search(r"(?i)there (?:are|is) (?:only )?(\d{1,2}|" + "|".join(NUM_WORDS) + r") lots? on this framework", t)
    if not m:
        return None
    n = m.group(1).lower()
    return int(NUM_WORDS.get(n, n))


def parse_brief_lot_lists(h):
    """{source_name: set(lots)} where the brief's Suppliers section lists awarded
    suppliers under lot headings. Empty dict when it does not."""
    blk = section(h, "suppliers")
    if not blk:
        return {}
    lines = [" ".join(x.split()) for x in text_of(blk).split("\n")]
    cur, out = None, {}
    for ln in lines:
        if not ln or "|" in ln:
            continue                 # table rows are the brief-table reader's job
        lab = lot_label(ln)
        # A heading is a short line that is ONLY the lot and maybe its title —
        # "CamDiab's algorithm that sits in Lot 3 ..." is prose, not a heading.
        if lab and len(ln) <= 90 and not re.search(r"(?i)\bsuppliers?\b", ln):
            cur = lab
            continue
        if re.search(r"(?i)delist|following suppliers|full list|there (?:are|is)\b|suppliers? (?:are|is|have|has)\b|:$", ln):
            if re.search(r"(?i)delist", ln):
                cur = None          # a delisted list is never an award
            continue
        if cur and len(ln) <= 120:
            name = brief_names.clean(ln).strip(" .")
            if name and re.search(r"[A-Za-z]{2}", name):
                out.setdefault(name, set()).add(cur)
    # One heading with a list under it is a lot title, not a lot split.
    lots = {l for v in out.values() for l in v}
    return out if len(lots) >= 2 else {}


MATRIX_LINK = re.compile(r'https://azuksappnpdsa01\.blob\.core\.windows\.net/datashare/[^"\'<>\s]+?\.xlsx', re.I)
MATRIX_SKIP = re.compile(r"(?i)social-?value|kpi|sustainab|alternative-products|hierarchy|sales-insight")


def matrix_links(h):
    out = []
    for u in sorted(set(MATRIX_LINK.findall(h))):
        base = u.rsplit("/", 1)[-1]
        if re.search(r"(?i)matri", base) and not MATRIX_SKIP.search(base):
            out.append(u)
    return out


# ---------------------------------------------------------------- matrix ---

NEGATIVE = {"", "no", "n", "-", "–", "n/a", "na", "none", "0", "false", "x not awarded", "not awarded"}


def _cell(v):
    if v is None:
        return ""
    return " ".join(str(v).split())


def _is_mark(v):
    return _cell(v).lower() not in NEGATIVE


MARK_WORDS = re.compile(r"(?i)^(yes|no|y|n|x|awarded|available.*|tick|✓|✔)$")


def _rows(ws, limit=600):
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i >= limit:
            break
        rows.append([_cell(v) for v in row[:80]])
    return rows


def _looks_like_company(s):
    return bool(s) and bool(re.search(r"[A-Za-z]{2}", s)) and len(s) <= 90 \
        and not MARK_WORDS.match(s) \
        and not re.match(r"(?i)^(key|note|notes|total|product|specification|supplier|lot)\b", s)


def parse_matrix_header_lots(rows):
    """Shape H: a header row with >=2 lot labels (Supplier | Lot 1 | Lot 2 ... or
    1.1 - title | 1.2 - title), supplier names in the first column beneath, marks in
    the cells. A lot label spans the blank header cells to its right until the next
    label (merged-cell headers). Returns {supplier: set(lots)}."""
    for ri, row in enumerate(rows):
        labels = {}
        for ci, v in enumerate(row):
            if ci == 0:
                continue
            lab = lot_label(v)
            if not lab:
                m = re.match(r"^(\d{1,2}\.\d{1,2})\s*[-–]\s*\S", v)
                lab = ("Lot " + m.group(1)) if m else None
            if lab:
                labels[ci] = lab
        numeric_row = False
        if len(labels) < 2 and re.match(r"(?i)^supplier", row[0] if row else "") \
                and any(re.match(r"(?i)^lots?$", v) for v in row[1:4]) and ri + 1 < len(rows):
            # "Supplier | Lots" with the lot numbers on the row beneath.
            nxt = rows[ri + 1]
            labels = {ci: "Lot " + v for ci, v in enumerate(nxt)
                      if ci > 0 and re.match(r"^\d{1,2}[a-z]?$", v)}
            numeric_row = True
        if len(labels) < 2:
            continue
        first = row[0] if row else ""
        if first and not re.match(r"(?i)^(supplier|lot name|lot|specification)\b", first):
            continue
        cols = sorted(labels)
        width = max(len(r) for r in rows[ri:ri + 200])
        span = {}
        for i, c in enumerate(cols):
            stop = cols[i + 1] if i + 1 < len(cols) else width
            for cc in range(c, stop):
                span[cc] = labels[c]
        out, blanks = {}, 0
        for row2 in rows[ri + (2 if numeric_row else 1):]:
            name = row2[0] if row2 else ""
            if not name:
                blanks += 1
                if blanks >= 3:
                    break
                continue
            blanks = 0
            if not _looks_like_company(name):
                continue
            for cc, lab in span.items():
                if cc < len(row2) and _is_mark(row2[cc]):
                    out.setdefault(name, set()).add(lab)
        if out:
            return out
    return {}


def parse_matrix_sections(rows, sheet_title):
    """Shape S: a lot heading (sheet title, or a short row whose text starts
    "Lot N") and a 'Specification | Supplier A | Supplier B' header row, products
    or marks beneath. A supplier is on the lot where its column has any positive
    cell inside that lot's section. Returns {supplier: set(lots)}."""
    cur_lot = lot_label(sheet_title)
    header = None
    out = {}
    for row in rows:
        nonempty = [v for v in row if v]
        if not nonempty:
            continue
        first = row[0] if row else ""
        hc = next((i for i, v in enumerate(row[:2]) if re.match(r"(?i)^(specification|products?|product areas?|service levels?|suppliers?|supplier names?)\s*:?$", v)), None)
        if hc is not None and len(nonempty) >= 3 and not lot_label(first):
            # Supplier names start in the column after the label cell.
            header = [""] * (hc + 1) + row[hc + 1:]
            continue
        lab = lot_label(first)
        if not lab and len(nonempty) <= 3:
            for v in nonempty:
                lab = lot_label(v)
                if lab:
                    break
        if lab:
            cur_lot = lab
            if len(nonempty) <= 3:
                continue
        if header is None or cur_lot is None:
            continue
        for ci in range(1, min(len(row), len(header))):
            sup = header[ci]
            if not sup:
                continue
            if sup and _looks_like_company(sup) and _is_mark(row[ci]):
                out.setdefault(sup, set()).add(cur_lot)
    return out


def parse_matrix_lot_rows(rows):
    """Shape T (transposed): a header row 'Lot | Supplier A | Supplier B ...' with
    one row per lot beneath ('Lot 1 - Dialysis ...') and marks in the cells.
    Returns {supplier: set(lot_row_text)} — the full lot text is kept so the
    caller can reconcile it against the brief's own lot titles."""
    for ri, row in enumerate(rows):
        if not row or not re.match(r"(?i)^lots?\s*:?$", row[0]):
            continue
        header = row
        if sum(1 for v in header[1:] if _looks_like_company(v)) < 3:
            continue
        out = {}
        for row2 in rows[ri + 1:ri + 60]:
            if not row2 or not lot_label(row2[0]):
                continue
            for ci in range(1, min(len(row2), len(header))):
                if _looks_like_company(header[ci]) and _is_mark(row2[ci]):
                    out.setdefault(header[ci], set()).add(row2[0])
        if out:
            return out
    return {}


def reconcile_lot(text, titles):
    """A lot label for `text`, checked against the brief's own titles. Where the
    matrix numbers a lot differently from the brief ("Lot 1 - Dialysis
    Consumables" beside the brief's "Lot 1.1: Dialysis Consumables and
    Equipment"), the brief's number wins when the title words agree exactly."""
    lab = lot_label(text)
    if not titles or not lab:
        return lab
    body = " ".join(re.sub(r"[^a-z0-9 ]", " ", LOT_HEAD.sub("", text, count=1).lower()).split())
    if not body:
        return lab
    def nt(t):
        return " ".join(re.sub(r"[^a-z0-9 ]", " ", (t or "").lower()).split())
    same = [k for k, t in titles.items() if nt(t) and (nt(t) == body or nt(t).startswith(body) or body.startswith(nt(t)))]
    # Only ever re-number to a FINER or equal brief label ("Lot 1" -> "Lot 1.1"),
    # never coarser: a source's "Lot 1b" is a real sub-lot, not the brief's "Lot 1".
    same = [k for k in same if k == lab or re.match(re.escape(lab) + r"[.a-z]", k)]
    if lab in titles and lab in same:
        return lab
    if len(same) == 1:
        return same[0]
    return lab


def parse_matrix(data):
    """[(sheet_title, shape, {source_name: set(lots)})] for every sheet with a lot
    axis. Header-shaped sheets win over section-shaped ones in the same workbook."""
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheets = [(ws.title, _rows(ws)) for ws in wb.worksheets]
    found = [(t, "matrix-header", m) for t, m in ((t, parse_matrix_header_lots(r)) for t, r in sheets) if m]
    if not found:
        found = [(t, "matrix-lot-rows", m) for t, m in ((t, parse_matrix_lot_rows(r)) for t, r in sheets) if m]
    if not found:
        found = [(t, "matrix-sections", m) for t, m in ((t, parse_matrix_sections(r, t)) for t, r in sheets) if m]
    return found


# A sheet is only read as a supplier-by-lot axis when most of the names on it are
# suppliers the brief itself names. A product-area sheet ("Disposable Cold Cups |
# Lot 2 | Lot 3") has the same shape and must not be mistaken for one.
MIN_RESOLVED_SHARE = 0.34


# ---------------------------------------------------------------- FTS -------

def _norm_title(s):
    s = re.sub(r"(?i)\b(20\d\d|tender notice|framework|agreement|nhs supply chain|the|and|&|of|for)\b", " ", s or "")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def tender_notice_id(fw):
    """The Find a Tender notice id the brief's reference points to, or None."""
    m = re.search(r"(20\d\d)/S\s*\d{3}-0*(\d+)", fw.get("reference") or "")
    return "%06d-%s" % (int(m.group(2)), m.group(1)) if m else None


def fts_award_releases(entry, lot_titles=None):
    """Award releases for the framework's OWN procurement from one --fts entry.

    Two shapes, both read from Find a Tender by the tender notice the brief's
    reference names:
      record  Procurement Act 2023 notices: the OCDS record for that notice, so
              every release shares the tender's ocid by construction.
      f03     PCR 2015 notices: the F03 contract award notice(s) the tender
              notice page links to. Accepted only where the award's own tender
              title equals the tender notice's title once year and boilerplate
              words are removed, so a mini-competition or call-off linked from the
              same page ("PPE Mini Competition Hand Hygiene") is refused. An
              award whose title was reworded is still accepted where at least
              two of its lot titles are, word for word, lot titles the brief
              itself publishes.
    Awards whose status is anything but active are dropped."""
    if not entry:
        return []
    if entry.get("kind") == "record":
        rels = [entry.get("compiled") or {}]
    elif entry.get("kind") == "f03":
        want = _norm_title(entry.get("title"))
        brief_titles = {_norm_title(t) for t in (lot_titles or {}).values() if t}

        def same_lots(r):
            return len({_norm_title(l[1]) for l in r.get("lots") or [] if l[1]} & brief_titles) >= 2
        rels = [r for r in entry.get("releases") or []
                if (want and _norm_title(r.get("title")) == want) or same_lots(r)]
    else:
        return []
    out = []
    for r in rels:
        r = dict(r)
        r["awards"] = [a for a in r.get("awards") or [] if (a[2] or "active") == "active"]
        out.append(r)
    return out


def _lot_text(lid, title):
    """'Lot <id> - <title>' for an OCDS lot id, whether the notice writes the id
    as '12' or as 'Lot 12'.

    Where the lot's own title opens with an explicit "Lot <label>" that differs
    from the OCDS id, the title's label is the notice's own lot name and wins:
    Instrument Decontamination's award (035065-2022) numbers its lots 1, 2, 3
    but titles them "Lot 1A ...", "Lot 1B ...", "Lot 2 ...". The title is then
    used as it stands, so the label is read from the notice, never renumbered."""
    lid = str(lid).strip()
    base = lid if lot_label(lid) else "Lot %s" % lid
    own = lot_label(title)
    if own and own != lot_label(base):
        return str(title).strip()
    return "%s - %s" % (base, title) if title else base


def parse_fts_awards(releases, titles=None):
    """{source_name: set(lots)} and the notice ids used. Lot ids are read as
    'Lot <id>' and reconciled against the brief's own lot titles."""
    out, ids = {}, []
    for r in releases:
        lot_titles = {str(l[0]): l[1] for l in r.get("lots") or []}
        used = False
        for rel, names, _status, _aid in r.get("awards") or []:
            for lid in rel or []:
                t = lot_titles.get(str(lid))
                lab = reconcile_lot(_lot_text(lid, t), titles or {})
                if not lab:
                    continue
                for nm in names or []:
                    if nm and nm.strip():
                        out.setdefault(nm.strip(), set()).add(lab)
                        used = True
        if used and r.get("id"):
            ids.append(r.get("id"))
    if len({l for v in out.values() for l in v}) < 2:
        return {}, []                      # one lot is not a lot split
    return out, ids


# ---------------------------------------------------------------- matching --

def resolver(seed):
    idx = company_match.build_index(seed or {})

    def to_company(n):
        c, state, _ = company_match.resolve(n, idx)
        return c if state == "confirmed" else None
    return to_company


def attach_names(source_map, brief_suppliers, to_company, names_out=None):
    """({brief_name: sorted lots}, unresolved[]) under the stated matching rule.
    names_out, when given, collects {brief_name: {source spelling, ...}}."""
    by_key, by_co = {}, {}
    for b in brief_suppliers:
        by_key.setdefault(company_match.key(brief_names.clean(b)), set()).add(b)
        c = to_company(brief_names.clean(b)) or to_company(b)
        if c:
            by_co.setdefault(c, set()).add(b)
    lots, unresolved = {}, []
    for src, labs in sorted(source_map.items()):
        k = company_match.key(brief_names.clean(src))
        cands = by_key.get(k) or set()
        how = "normalised name"
        if len(cands) != 1:
            c = to_company(brief_names.clean(src)) or to_company(src)
            cands = by_co.get(c, set()) if c else set()
            how = "recorded alias"
        if len(cands) == 1:
            b = next(iter(cands))
            lots.setdefault(b, set()).update(labs)
            if names_out is not None:
                names_out.setdefault(b, set()).add(src)
        else:
            unresolved.append({
                "name": src, "lots": sorted(labs, key=lot_sort_key),
                "reason": ("matches %d suppliers on this brief" % len(cands)) if cands else
                          "no supplier on this brief normalises to it, and no recorded alias links it to one"})
    return {b: sorted(v, key=lot_sort_key) for b, v in lots.items()}, unresolved


# ---------------------------------------------------------------- fetch -----

def fetch(url, cache=None, binary=False):
    if cache:
        fn = os.path.join(cache, re.sub(r"[^A-Za-z0-9._-]+", "_", url.rstrip("/").split("/")[-1]) or "index")
        if not binary:
            fn += ".html"
        if os.path.exists(fn) and os.path.getsize(fn):
            with open(fn, "rb") as f:
                d = f.read()
            return d if binary else d.decode("utf-8", "replace")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < 2:
                time.sleep(3)
                continue
            raise
    time.sleep(PAUSE)
    if cache:
        with open(fn, "wb") as f:
            f.write(d)
    return d if binary else d.decode("utf-8", "replace")


def build_one(fw, h, to_company, cache, fts_releases, previous):
    """The framework-lots record for one live framework."""
    rec = {"name": fw["name"], "lotTitles": parse_lot_titles(h) if h else {},
           "statedLotCount": stated_lot_count(h) if h else None,
           "signals": [], "sources": [], "unresolved": [], "lotsBySource": {}, "namedAs": {}}
    lots = {}

    def take(kind, url, label, source_map, date=None):
        spelled = {}
        got, unres = attach_names(source_map, fw.get("suppliers") or [], to_company, spelled)
        for b, names in spelled.items():
            other = sorted(n for n in names if n != b)
            if other:
                rec["namedAs"].setdefault(b, [])
                rec["namedAs"][b] = sorted(set(rec["namedAs"][b]) | set(other))
        rec["signals"].append(kind)
        for u in unres:
            u["source"] = kind
        rec["unresolved"].extend(unres)
        if got:
            for b, v in got.items():
                lots.setdefault(b, set()).update(v)
                rec["lotsBySource"].setdefault(kind, {}).setdefault(b, [])
                rec["lotsBySource"][kind][b] = sorted(set(rec["lotsBySource"][kind][b]) | set(v),
                                                      key=lot_sort_key)
            covers = sorted({l for v in source_map.values() for l in v}, key=lot_sort_key)
            rec["sources"].append({"kind": kind, "url": url, "label": label, "coversLots": covers,
                                   "suppliersWithLots": len(got), **({"date": date} if date else {})})

    table = fw.get("supplierLotsFromBrief") or (
        fw.get("supplierLots") if (fw.get("lotSourceKind") in (None, "brief-table")
                                   and "lot table" in (fw.get("supplierSource") or "")) else None)
    if table:
        take("brief-table", fw["url"], "NHS Supply Chain contract launch brief (supplier-by-lot table)",
             {k: set(lot_label(x) or x for x in v) for k, v in table.items()})
    if h:
        lists = parse_brief_lot_lists(h)
        if lists:
            take("brief-lists", fw["url"], "NHS Supply Chain contract launch brief (suppliers listed by lot)", lists)
        for u in matrix_links(h):
            base = u.rsplit("/", 1)[-1]
            try:
                sheets = parse_matrix(fetch(u, cache, binary=True))
            except Exception as exc:
                rec["unresolved"].append({"name": None, "source": "matrix",
                                          "reason": "matrix %s could not be read: %s" % (base, exc)})
                continue
            src = {}
            for title, shape, m in sheets:
                if shape == "matrix-lot-rows":
                    m = {k: {reconcile_lot(x, rec["lotTitles"]) for x in v} - {None} for k, v in m.items()}
                _, unres = attach_names(m, fw.get("suppliers") or [], to_company)
                resolved = len(m) - len(unres)
                if resolved >= 2 and resolved / float(len(m)) >= MIN_RESOLVED_SHARE:
                    for k, v in m.items():
                        src.setdefault(k, set()).update(v)
            if src and len({l for v in src.values() for l in v}) >= 2:
                dm = re.search(r"(\d{1,2}-[A-Za-z]+-20\d\d)", base)
                take("matrix", u, "NHS Supply Chain %s (%s), attached to the brief" % (
                    "supplier matrix" if re.search(r"(?i)supplier", base) else "product matrix", base),
                    src, date=dm.group(1).replace("-", " ") if dm else None)
    # PRECEDENCE: NHS Supply Chain's own current documents (brief, then its
    # matrix) win. The award notice is read only where they name no lots, so
    # two lot numbering schemes are never mixed on one card (Renal: the matrix
    # numbers Lot 1.1-1.3, 2, 3; the 2023 award notice numbers Lot 1-3).
    # An --fts file carries only the procurements it was collected for. A framework
    # it does not contain falls through to the carried-forward read below, so a
    # partial file can add awards without silently dropping every other one
    # (30/09/2026: 15 new awards would otherwise have wiped the 29 already held).
    tid = tender_notice_id(fw)
    entry = fts_releases.get(tid) if (fts_releases is not None and tid) else None
    if lots:
        pass
    elif entry is not None:
        rels = fts_award_releases(entry, rec["lotTitles"])
        src, ids = parse_fts_awards(rels, rec["lotTitles"])
        if src:
            # The award notice's lots are the procurement's legal lots. Where a
            # brief numbers its PRODUCT CATEGORIES as "lots" differently (Advanced
            # Wound Care: 18 categories on the brief, 2 lots on the award), the
            # award's own lot titles are what the card shows, never the brief's
            # title for the same number.
            award_titles = {}
            for r in rels:
                for lid, t in r.get("lots") or []:
                    lab = reconcile_lot(_lot_text(lid, t), rec["lotTitles"])
                    t = LOT_HEAD.sub("", t or "", count=1).strip(" :–—-") or None
                    if lab and t:
                        award_titles.setdefault(lab, t)
            # Decide the clash on the brief's own titles BEFORE filling any gap,
            # so an award-only label (Instrument Decontamination's "Lot 2") is
            # never written into the brief's scheme and briefLotTitles stays the
            # brief's alone.
            clash = [l for l, t in award_titles.items()
                     if rec["lotTitles"].get(l) and _norm_title(rec["lotTitles"][l]) != _norm_title(t)]
            if clash:
                rec["briefLotTitles"] = rec["lotTitles"]
                rec["lotTitles"] = award_titles
            else:
                for l, t in award_titles.items():
                    if l not in rec["lotTitles"] or not rec["lotTitles"][l]:
                        rec["lotTitles"][l] = t
            nid = re.sub(r"^ocds-[a-z0-9]+-[a-z0-9]+-", "", ids[0])
            take("fts-award", "https://www.find-tender.service.gov.uk/Notice/%s" % nid,
                 "Find a Tender contract award notice %s" % ", ".join(
                     re.sub(r"^ocds-[a-z0-9]+-[a-z0-9]+-", "", x) for x in ids), src)
    elif previous:
        # Award notices do not change. Carry a previously read award forward
        # rather than losing it on a run that did not re-read the feed.
        for s in previous.get("sources") or []:
            if s.get("kind") == "fts-award":
                prev_lots = {b: set(v) for b, v in (previous.get("lotsBySource", {}).get("fts-award") or {}).items()}
                if prev_lots:
                    if previous.get("briefLotTitles"):
                        rec["briefLotTitles"] = rec["lotTitles"]
                        rec["lotTitles"] = dict(previous.get("lotTitles") or {})
                    for l, t in (previous.get("lotTitles") or {}).items():
                        if t and not rec["lotTitles"].get(l):
                            rec["lotTitles"][l] = t
                    rec["signals"].append("fts-award")
                    rec["sources"].append(s)
                    rec["unresolved"].extend(u for u in previous.get("unresolved") or []
                                             if u.get("source") == "fts-award")
                    for b, v in prev_lots.items():
                        if b in (fw.get("suppliers") or []):
                            lots.setdefault(b, set()).update(v)
                            rec["lotsBySource"].setdefault("fts-award", {})[b] = sorted(v, key=lot_sort_key)
                            if (previous.get("namedAs") or {}).get(b):
                                rec["namedAs"][b] = previous["namedAs"][b]

    rec["supplierLots"] = {b: sorted(v, key=lot_sort_key) for b, v in sorted(lots.items())}
    if rec["supplierLots"]:
        rec["status"] = "published"
    elif len(rec["lotTitles"]) >= 2 or (rec["statedLotCount"] or 0) >= 2 or rec["signals"]:
        rec["status"] = "notPublished"
    else:
        rec["status"] = "noLots"
    rec["suppliersWithoutLot"] = [s for s in (fw.get("suppliers") or []) if s not in rec["supplierLots"]] \
        if rec["status"] == "published" else []
    covered = sorted({l for src in rec["sources"] for l in src.get("coversLots") or []}, key=lot_sort_key)
    rec["coversLots"] = covered or None
    known = set(rec["lotTitles"])
    # Partial coverage: the brief names lots that no source above covers, so a
    # supplier absent from the source may still hold one of those lots.
    def is_covered(k):
        return any(l == k or re.match(re.escape(k) + r"[.a-z]", l) for l in covered)
    rec["lotsNotCovered"] = sorted([k for k in known if not is_covered(k)], key=lot_sort_key) \
        if rec["status"] == "published" else []
    return rec


# ---------------------------------------------------------------- attach ----

def attach(fwdoc, lotsdoc):
    """Copy lots onto each live framework record in place. Idempotent. Returns the
    number of frameworks carrying supplierLots afterwards."""
    by_url = (lotsdoc or {}).get("frameworks") or {}
    n = 0
    for f in (fwdoc.get("frameworks") or []) + (fwdoc.get("expired") or []):
        # Keep the brief's own table apart so re-attaching never loses it.
        if f.get("supplierLots") and "lot table" in (f.get("supplierSource") or "") \
                and not f.get("supplierLotsFromBrief"):
            f["supplierLotsFromBrief"] = f["supplierLots"]
        r = by_url.get((f.get("url") or "").rstrip("/") + "/") or by_url.get(f.get("url"))
        if not r:
            f.setdefault("lotStatus", None)
            continue
        f["lotTitles"] = r.get("lotTitles") or None
        f["lotStatus"] = r.get("status")
        lots = {b: v for b, v in (r.get("supplierLots") or {}).items() if b in (f.get("suppliers") or [])}
        f["supplierLots"] = lots or None
        f["lotSources"] = [{k: v for k, v in x.items() if k in ("kind", "url", "label", "date", "coversLots")}
                           for x in (r.get("sources") or [])] or None
        f["lotsNotCovered"] = r.get("lotsNotCovered") or None
        f["lotNamedAs"] = {b: v for b, v in (r.get("namedAs") or {}).items() if b in lots} or None
        f["statedLotCount"] = r.get("statedLotCount")
        f["lotOwner"] = OWNER
        if lots:
            n += 1
    fwdoc["lotRule"] = RULE
    fwdoc["lotsAsOf"] = (lotsdoc or {}).get("dataAsOf")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="")
    ap.add_argument("--fts", default="", help="JSON of Find a Tender award releases keyed by tender notice id")
    ap.add_argument("--attach-only", action="store_true")
    ap.add_argument("--only", default="", help="substring of a framework name, for testing")
    args = ap.parse_args()

    with open(FW_PATH, encoding="utf-8") as f:
        fwdoc = json.load(f)
    prev = {}
    if os.path.exists(LOTS_PATH):
        with open(LOTS_PATH, encoding="utf-8") as f:
            prev = json.load(f)

    if not args.attach_only:
        with open(SEED_PATH, encoding="utf-8") as f:
            seed = json.load(f)
        to_company = resolver(seed)
        fts = None
        if args.fts:
            # {tender_notice_id: {"kind": "record"|"f03", "title": ..., ...}} as
            # collected from Find a Tender (see the process doc for how).
            with open(args.fts, encoding="utf-8") as f:
                fts = json.load(f)
        if args.cache:
            os.makedirs(args.cache, exist_ok=True)
        out = dict((prev.get("frameworks") or {})) if args.only else {}
        for fw in fwdoc.get("frameworks") or []:
            if args.only and args.only.lower() not in fw["name"].lower():
                continue
            try:
                h = fetch(fw["url"], args.cache or None)
            except Exception as exc:
                print("brief unreadable, lots not read: %s (%s)" % (fw["name"], exc), file=sys.stderr)
                h = ""
            p = (prev.get("frameworks") or {}).get(fw["url"])
            rec = build_one(fw, h, to_company, args.cache or None, fts, p)
            if h == "" and p:
                rec = p            # an unreachable page is not evidence the lots went away
            out[fw["url"]] = rec
            print("%-12s %3d/%-3d %s" % (rec["status"], len(rec["supplierLots"]),
                                          len(fw.get("suppliers") or []), fw["name"]), file=sys.stderr)
        counts = {s: sum(1 for r in out.values() if r["status"] == s) for s in STATUSES}
        lotsdoc = {
            **({"_notice": prev["_notice"]} if prev.get("_notice") else {}),
            "dataAsOf": datetime.date.today().isoformat(),
            "owner": OWNER,
            "rule": RULE,
            "counts": counts,
            "frameworks": out,
        }
        with open(LOTS_PATH, "w", encoding="utf-8") as f:
            json.dump(lotsdoc, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("Wrote %s — %s" % (LOTS_PATH, counts))
    else:
        lotsdoc = prev

    n = attach(fwdoc, lotsdoc)
    with open(FW_PATH, "w", encoding="utf-8") as f:
        json.dump(fwdoc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("Attached lots: %d of %d live frameworks carry supplierLots." % (
        sum(1 for x in fwdoc.get("frameworks") or [] if x.get("supplierLots")), len(fwdoc.get("frameworks") or [])))


if __name__ == "__main__":
    main()
