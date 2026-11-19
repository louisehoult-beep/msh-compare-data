#!/usr/bin/env python3
"""Merge the Hub's two records for ONE company: Credenhill Limited, CH 00547046,
trading as Daylong Direct. Lou's ruling, 17/11/2026 ("if so yes"), after the
identity was proved — the surviving page carries both names.

THE EVIDENCE (all read 17/11/2026, recorded on the records by
scripts/_seed_duplicate_record_identity_1117.py and kept in the merged note)
-------------------------------------------------------------------------
  * Companies House 00547046 CREDENHILL LIMITED, active, incorporated
    1 April 1955, Unit 5 Soloman Road, Cossall Industrial Estate, Ilkeston,
    England, DE7 5UD.
  * credenhill.co.uk states, verbatim: "Credenhill Ltd T/A Daylong Direct.
    Registered in England, company number 00547046. Registered office: Unit 5
    Soloman Road, Cossall Industrial Estate, Ilkeston, England, DE7 5UD." —
    the number AND the registered office agree with the register, which is
    route 2 of docs/COMPANY-REPORT-METHOD.md.
  * daylongdirect.co.uk states: "Daylong Direct is the trading name for
    Credenhill Limited."
  * NHS Supply Chain's own Vascular Therapy and Associated Products brief
    (2023/S 000-012286) names the awarded supplier "Daylong Direct
    (Credenhill)", so the awarding source makes the same identification and
    clause (a) of the parent-subsidiary-award-credit policy is not in the way.

This is the evidence data/identity-vocabulary-policy.json asks for before two
records become one: a shared REGISTRATION NUMBER, never a shared name.

WHAT IT DOES
------------
One record survives, named "Credenhill Ltd (trading as Daylong Direct)" — the
legal entity and the name NHS Supply Chain awards under, in the house style
already used by e.g. "Nottingham Rehab Limited (Trading as NRS Healthcare)".
It takes the union of both records' aliases, frameworks, links, products,
product categories, specialities, awards, news and alerts, keeps Credenhill's
brand and route-2 companyNumberProof, and records `mergedFrom: ["Daylong
Direct"]` — the field "Vernacare" and "Essity UK Limited" already use.

Then every file that keys a Hub record BY NAME is moved to the new name:
seed, index, financials, awards, logos, press, compare rows (`ref` only — the
gate requires `ref` to equal the master record's name while `co` stays the
printed spelling), coverage ledger, product-crawl refusals, careers, the
innovator report, interview prep and the search index.

WHAT IT DELIBERATELY DOES NOT TOUCH
-----------------------------------
  * `data/frameworks.json` supplier lists and `data/framework-lots.json`
    `unresolved` names: those are NHS Supply Chain's OWN words, and the gate
    requires a supplierLots key to be a brief supplier verbatim. The brief row
    stays "Daylong Direct"; it now resolves to the merged record through the
    aliases, which is what lets the Orthotics and Vascular Therapy lots attach.
  * `noticeSupplierName` on award rows, and `matchAliases` strings in
    company-press.json: source text and match patterns, not record names.
  * `data/drug-tariff-part-ix.json` (921 "Credenhill" rows): the Drug Tariff's
    own contractor name, not a Hub record key.
  * The Vascular Therapy framework is NOT hand-added to the record. The brief
    names "Daylong Direct (Credenhill)", which is now an alias, so
    backfill_seed_from_frameworks.py will attach it from the brief on its own
    next run — a framework claim should come from the capture, not from here.

Idempotent: a second run finds the new name in place, reports "already merged"
and writes nothing.

    python3 scripts/_merge_credenhill_daylong_1117.py
"""
import io
import json
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like, describe  # noqa: E402

KEEP = "Credenhill"                  # the surviving record, before the rename
FOLD = "Daylong Direct"              # the record folded into it
NEW = "Credenhill Ltd (trading as Daylong Direct)"
NUMBER = "00547046"
TODAY = "2026-11-17"

EXTRA_ALIASES = [
    "Credenhill", "Credenhill Limited", "Credenhill Ltd",
    "Daylong Direct", "Daylong Direct (Credenhill)",
    "credenhill.co.uk", "daylongdirect.co.uk",
]

MERGE_NOTE = (
    "MERGED %s on Lou's ruling: the Hub held this one company as two records, "
    "\"Credenhill\" and \"Daylong Direct\". Companies House %s CREDENHILL LIMITED, active, "
    "incorporated 1 April 1955, Unit 5 Soloman Road, Cossall Industrial Estate, Ilkeston, "
    "England, DE7 5UD; the company's own site states verbatim \"Credenhill Ltd T/A Daylong "
    "Direct. Registered in England, company number %s. Registered office: Unit 5 Soloman "
    "Road, Cossall Industrial Estate, Ilkeston, England, DE7 5UD.\" (credenhill.co.uk, read "
    "%s) — number and registered office both agreeing with the register, which is route 2 of "
    "docs/COMPANY-REPORT-METHOD.md; daylongdirect.co.uk states \"Daylong Direct is the "
    "trading name for Credenhill Limited.\"; and NHS Supply Chain's own Vascular Therapy and "
    "Associated Products brief (2023/S 000-012286) names the awarded supplier \"Daylong "
    "Direct (Credenhill)\". A shared registration number is the evidence "
    "data/identity-vocabulary-policy.json requires before two records become one. Both names "
    "are kept as aliases, so every award stays findable under the name its own source uses, "
    "and NHS Supply Chain's brief rows (\"Daylong Direct\", \"Daylong Direct (Credenhill)\") "
    "are untouched."
) % (TODAY, NUMBER, NUMBER, TODAY)


def rd(path):
    return json.load(io.open(path, encoding="utf-8"))


def norm_tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split() if t]


def uniq(seq):
    seen, out = set(), []
    for x in seq:
        key = json.dumps(x, sort_keys=True, ensure_ascii=False) if not isinstance(x, str) else x
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


# ------------------------------------------------------------ the records ---

def merge_supplier_file(path):
    doc = rd(path)
    sups = doc.get("suppliers") or []
    keep = [s for s in sups if isinstance(s, dict) and s.get("name") == KEEP]
    fold = [s for s in sups if isinstance(s, dict) and s.get("name") == FOLD]
    if not keep and any(isinstance(s, dict) and s.get("name") == NEW for s in sups):
        print("%s: already merged" % path)
        return 0
    if not keep or not fold:
        print("%s: expected both %r and %r, found keep=%d fold=%d — SKIPPED"
              % (path, KEEP, FOLD, len(keep), len(fold)))
        return 0
    a, b = keep[0], fold[0]

    LIST_KEYS = ("aliases", "frameworks", "links", "products", "productCategories",
                 "specialities", "awards", "news", "alerts")
    for k in LIST_KEYS:
        va, vb = a.get(k), b.get(k)
        if va is None and vb is None:
            continue
        a[k] = uniq(list(va or []) + list(vb or []))
    a["aliases"] = uniq([NEW] + EXTRA_ALIASES + list(a.get("aliases") or []))

    # prose: keep both records' own wording, each labelled, never silently dropped
    notes = [n for n in (a.get("note"), b.get("note")) if n]
    a["note"] = MERGE_NOTE + (("  Previous \"Credenhill\" record: " + notes[0]) if notes else "")
    if len(notes) > 1:
        a["note"] += "  Previous \"Daylong Direct\" record: " + notes[1]
    a["identityNote"] = MERGE_NOTE
    for k in ("source", "reconciledFrom", "companyNumberNote", "_specialitiesEvidence"):
        if b.get(k) and a.get(k) and b[k] != a[k]:
            a[k] = "%s | from the merged \"%s\" record: %s" % (a[k], FOLD, b[k])
        elif b.get(k) and not a.get(k):
            a[k] = b[k]
    a["mergedFrom"] = uniq(list(a.get("mergedFrom") or []) + [FOLD])
    a["verified"] = TODAY
    a["name"] = NEW

    doc["suppliers"] = [s for s in sups if not (isinstance(s, dict) and s.get("name") == FOLD)]
    fmt, rt = write_like(path, doc)
    print("%s: merged; %s" % (path, describe(path, fmt, rt)))
    return 1


# ------------------------------------------------- the name-keyed derivatives

def rename_keys(doc, container, merge_lists=False):
    """container[KEEP] and container[FOLD] -> container[NEW]."""
    node = doc
    for seg in container:
        node = node.get(seg) if isinstance(node, dict) else None
        if node is None:
            return 0
    if NEW in node and KEEP not in node and FOLD not in node:
        return 0
    a, b = node.pop(KEEP, None), node.pop(FOLD, None)
    if a is None and b is None:
        return 0
    if merge_lists or isinstance(a, list) or isinstance(b, list):
        node[NEW] = uniq(list(a or []) + list(b or []))
    else:
        node[NEW] = deep_merge(a or {}, b or {})
    return 1


PROSE = ("reason", "note", "why", "evidence", "source")


def deep_merge(a, b):
    """a wins, but nothing b holds is silently dropped.

    Nested maps merge recursively and lists union, so the folded record's
    matching aliases and crawl evidence survive the merge — losing
    ["Daylong Direct"] out of company-press.json's matchAliases would quietly
    stop that name's press ever matching again. Two different strings under one
    key are joined and labelled, never overwritten.
    """
    out = dict(a)
    for k, v in b.items():
        if k not in out:
            out[k] = v
        elif isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        elif isinstance(out[k], list) and isinstance(v, list):
            out[k] = uniq(out[k] + v)
        elif isinstance(out[k], str) and isinstance(v, str) and out[k] != v:
            # Only PROSE is joined. A domain or a date is read by other code, so
            # two of them must never become one string: the surviving record's
            # value stands, and the folded one is reported in the prose field.
            if k in PROSE:
                out[k] = "%s | the merged \"%s\" record held: %s" % (out[k], FOLD, v)
            else:
                out.setdefault("_mergedFromDetail", {})[k] = v
    return out


def rename_values(node, fields):
    """Set any string field in `fields` that holds KEEP or FOLD to NEW."""
    n = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if k in fields and isinstance(v, str) and v.strip() in (KEEP, FOLD):
                node[k] = NEW
                n += 1
            elif k in fields and isinstance(v, list):
                new = [NEW if (isinstance(x, str) and x.strip() in (KEEP, FOLD)) else x for x in v]
                if new != v:
                    node[k] = uniq(new)
                    n += 1
            else:
                n += rename_values(v, fields)
    elif isinstance(node, list):
        for v in node:
            n += rename_values(v, fields)
    return n


def patch(path, fn):
    doc = rd(path)
    n = fn(doc)
    if not n:
        print("%s: nothing to change" % path)
        return 0
    fmt, rt = write_like(path, doc)
    print("%s: %d change(s); %s" % (path, n, describe(path, fmt, rt)))
    return n


def fix_count(doc, counts_key, container):
    """Keep a file's own counts header true to the rows this merge changed.

    company-awards.json and company-press.json both publish a count of the
    companies they hold, and verify.py fails the file when the header and the
    rows disagree -- the 14/08/2026 drift, where a header from one generation
    sat over rows from another. Folding two records into one legitimately
    removes a row from each file, so its header moves WITH it, in the same
    change. This is not hand-correcting someone else's drift: regenerating
    either file would publish a day's unrelated pipeline output on top of a
    name merge.
    """
    counts = doc.get("counts")
    node = doc.get(container)
    if not isinstance(counts, dict) or not isinstance(node, dict):
        return 0
    if counts.get(counts_key) == len(node):
        return 0
    counts[counts_key] = len(node)
    return 1


def search_index(doc):
    recs = doc.get("records") or []
    old = [r for r in recs if isinstance(r, dict) and r.get("c") == "Supplier"
           and (r.get("t") or "").strip() in (KEEP, FOLD)]
    if not old:
        return 0
    # the builder's own shape: t = record name, u = the suppliers page anchored on
    # it, k = normalised name then alias/speciality/framework words.
    words = norm_tokens(NEW) + [w for r in old for w in norm_tokens(r.get("k"))]
    merged = {
        "t": NEW,
        "u": "/medical-sales-hub/suppliers/#q=" + quote(NEW),
        "k": " ".join(uniq(words)),
        "c": "Supplier",
    }
    at = recs.index(old[0])
    doc["records"] = [r for r in recs if r not in old]
    doc["records"].insert(at, merged)
    return 1


if __name__ == "__main__":
    total = 0
    total += merge_supplier_file("data/supplier-seed.json")
    total += merge_supplier_file("data/supplier-index.json")

    # keyed by record name
    total += patch("data/company-financials.json", lambda d: rename_keys(d, ("companies",)))
    total += patch("data/company-awards.json",
                   lambda d: rename_keys(d, ("companies",), merge_lists=True)
                   + rename_values(d.get("companies", {}).get(NEW) or [], {"company"})
                   + fix_count(d, "companies", "companies"))
    total += patch("data/company-press.json",
                   lambda d: rename_keys(d, ("suppliers",))
                   + fix_count(d, "suppliers", "suppliers"))
    total += patch("data/supplier-products.json", lambda d: rename_keys(d, ("refusals",)))
    # record name in a field
    total += patch("data/company-logos.json", lambda d: rename_values(d.get("logos") or [], {"name"}))
    total += patch("data/supplier-careers.json",
                   lambda d: rename_values(d.get("suppliers") or [], {"name"}))
    total += patch("data/interview-prep.json", lambda d: rename_values(d.get("co") or [], {"n"}))
    total += patch("data/coverage-ledger.json",
                   lambda d: rename_values(d.get("frameworks") or [], {"supplier", "refused"}))
    # `ref`/`matchedTo` must equal the master record's name; `co` stays the printed spelling
    total += patch("data/compare-suppliers.json",
                   lambda d: rename_values(d.get("specialities") or {}, {"ref"}))
    total += patch("data/innovator-report.json",
                   lambda d: rename_values(d.get("specialities") or {}, {"ref", "matchedTo"}))
    total += patch("data/hub-search-index.json", search_index)
    print("done: %d file change(s)" % total)
