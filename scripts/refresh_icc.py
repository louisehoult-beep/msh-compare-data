#!/usr/bin/env python3
"""
Information for Clinical Choice (ICC) ingestion.

NHS Supply Chain's Clinical Collaboration Teams publish, free and without login,
specification-level comparison material for clinically similar products:

  https://www.supplychain.nhs.uk/savings/information-for-clinical-choice/

Two document types sit on that page:

  Product Matrix (.xlsx)  a populated grid: supplier, brand, MPC, NPC and one
                          column per specification attribute. This is the same
                          grain as the Hub's Differentiator, authored by the NHS.
  Support Document (.pdf) narrative describing the features a clinician should
                          weigh in that category. Not a grid.

This script downloads every publicly linked document to the ICC library on
OneDrive (so we hold the source evidence), then writes two structured files:

  data/icc-catalogue.json  every document, its category label, type, issue date
                           parsed from the filename, and its source URL
  data/icc-matrices.json   the parsed Product Matrices: one record per product
                           with its supplier, codes and every spec attribute

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO
-----------------------------------------
It only fetches URLs that are linked from the ICC page itself. The Azure blob
container does not permit listing (verified 28/08/2026: restype=container&comp=list
returns 404 ResourceNotFound), and we do not guess at unlinked filenames. If a
Product Matrix is not linked publicly, we do not have it, and the Hub must not
imply otherwise.

Only one full Product Matrix was publicly linked as at 28/08/2026 (Adult ECG
Electrodes). That is not a bug in this script. Matrices generally sit behind
authentication.supplychain.nhs.uk. The count is reported on every run so a drop
or a jump is visible rather than silent.

Usage:
    python3 scripts/refresh_icc.py            # download new/changed, rebuild JSON
    python3 scripts/refresh_icc.py --no-fetch # rebuild JSON from the local library
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

ICC_URL = "https://www.supplychain.nhs.uk/savings/information-for-clinical-choice/"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")

# The source documents are kept outside the git repo: they are ~20MB of PDFs and
# the repo is fetched by the live Hub tools on every page load.
LIBRARY = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-Personal/Cowork-OS/"
    "02-Elevate-and-Thrive/Hub/ICC-Library"
)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Filenames carry their issue date, in several shapes:
#   ...-29-February-2024-T1.xlsx      ...-8-May-2026.pdf
#   ...-September-2024.pdf            ...-18-December-2025-6944172c5abed.pdf
#   ...-Aug-2026.pdf                 (abbreviated months appear too)
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
DATE_RE = re.compile(r"(?:(\d{1,2})-)?(" + MONTHS + r")-(\d{4})", re.I)

PUB_BOX_RE = re.compile(
    r'<a href="(https://azuksappnpdsa01\.blob\.core\.windows\.net/datashare/'
    r'[^"]+\.(?:xlsx|pdf))"[^>]*>.*?<div class="pub-text">\s*<strong>(.*?)</strong>',
    re.S,
)


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, binary: bool = False, tries: int = 3):
    """Fetch a URL with a browser user-agent. Returns bytes or str, or None."""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
            return raw if binary else raw.decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == tries:
                log("    FETCH FAILED after %d tries: %s (%s)" % (tries, url, exc))
                return None
            time.sleep(2 * attempt)
    return None


def parse_issue_date(filename: str) -> str | None:
    """Pull the issue date out of the filename. Returns ISO date, or None."""
    m = DATE_RE.search(filename)
    if not m:
        return None
    day, month, year = m.group(1), m.group(2), m.group(3)
    try:
        month_num = dt.datetime.strptime(month[:3], "%b").month
    except ValueError:
        return None
    try:
        return dt.date(int(year), month_num, int(day) if day else 1).isoformat()
    except ValueError:
        return None


def doc_type(filename: str) -> str:
    low = filename.lower()
    if low.endswith(".xlsx"):
        return "product_matrix"
    if "product-matrix" in low:
        return "product_matrix"
    return "support_document"


# --------------------------------------------------------------------------
# Product Matrix parsing
# --------------------------------------------------------------------------

def _cell_text(c, shared):
    """Resolve one worksheet cell to a string."""
    t = c.get("t")
    v = None
    for child in c:
        tag = child.tag.split("}")[-1]
        if tag == "v":
            v = child.text
        elif tag == "is":
            return "".join(x.text or "" for x in child.iter() if x.tag.split("}")[-1] == "t")
    if v is None:
        return ""
    if t == "s":
        try:
            return shared[int(v)]
        except (ValueError, IndexError):
            return ""
    return v


def _sheet_grid(root, ns, shared) -> list[list[str]]:
    """Turn one worksheet into a dense row/column grid of strings."""
    grid: list[list[str]] = []
    for row in root.iter(ns + "row"):
        cells: list[str] = []
        for c in row.iter(ns + "c"):
            ref = c.get("r") or ""
            col = re.match(r"([A-Z]+)", ref)
            idx = 0
            if col:
                for ch in col.group(1):
                    idx = idx * 26 + (ord(ch) - 64)
                idx -= 1
            while len(cells) < idx:
                cells.append("")
            cells.append(_cell_text(c, shared).strip())
        grid.append(cells)
    return grid


def parse_matrix(path: str) -> dict | None:
    """
    Parse an ICC Product Matrix .xlsx.

    The workbooks carry one tab per clinical sub-category (for ECG electrodes:
    Ambulatory/holter, Resting, Stress or Exercise) behind an Introduction tab.
    Each data tab repeats a title block above the real header row, which is
    identified by containing 'Supplier'. The preamble is kept as `notes` rather
    than discarded, because it carries the pricing-currency caveat NHS Supply
    Chain attaches to every matrix.

    Returns a dict of sub-category name -> {columns, notes, products}, plus a
    flattened product list across all sub-categories.
    """
    import xml.etree.ElementTree as ET

    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        log("    cannot open workbook: %s" % exc)
        return None

    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
            shared.append("".join(t.text or "" for t in si.iter(ns + "t")))

    # Map sheet display name -> worksheet part, via the workbook relationships.
    rel_target = {}
    if "xl/_rels/workbook.xml.rels" in z.namelist():
        for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            rel_target[rel.get("Id")] = rel.get("Target", "").lstrip("/")

    sheets: list[tuple[str, str]] = []
    for s in ET.fromstring(z.read("xl/workbook.xml")).iter(ns + "sheet"):
        target = rel_target.get(s.get(rns + "id"), "")
        if not target:
            continue
        part = target if target.startswith("xl/") else "xl/" + target
        if part in z.namelist():
            sheets.append((s.get("name") or part, part))

    sub_matrices: dict[str, dict] = {}
    all_products: list[dict] = []
    all_columns: list[str] = []

    for sheet_name, part in sheets:
        grid = _sheet_grid(ET.fromstring(z.read(part)), ns, shared)

        header_i = None
        for i, row in enumerate(grid[:30]):
            if any(cell.strip().lower() == "supplier" for cell in row):
                header_i = i
                break
        if header_i is None:
            continue                      # Introduction tab and similar

        header = [h.strip() for h in grid[header_i]]
        notes = [c.strip() for r in grid[:header_i] for c in r if c.strip()]

        records = []
        for row in grid[header_i + 1:]:
            if not any(c.strip() for c in row):
                continue
            rec = {}
            for j, name in enumerate(header):
                if not name:
                    continue
                val = row[j].strip() if j < len(row) else ""
                if val:
                    rec[name] = val
            # A row is only a product if it carries an identifying code or brand.
            if any(k in rec for k in ("Supplier", "Brand", "NPC", "MPC")):
                rec["_sub_category"] = sheet_name
                records.append(rec)

        if not records:
            continue

        cols = [h for h in header if h]
        sub_matrices[sheet_name] = {
            "columns": cols,
            "notes": notes,
            "products": records,
        }
        all_products.extend(records)
        for c in cols:
            if c not in all_columns:
                all_columns.append(c)

    if not sub_matrices:
        log("    no 'Supplier' header row found on any sheet, skipping")
        return None

    return {
        "columns": all_columns,
        "sub_categories": sub_matrices,
        "products": all_products,
        "notes": next(iter(sub_matrices.values()))["notes"],
    }


# --------------------------------------------------------------------------
# Support Document text extraction
# --------------------------------------------------------------------------

def pdf_text(path: str, limit: int = 6000) -> str:
    """
    Extract text from a PDF using only the standard library.

    Handles Flate-compressed content streams and the two common text operators.
    Good enough to capture the opening description, which is what we want. It is
    not a full PDF parser and does not pretend to be: if it returns nothing, the
    catalogue records an empty summary rather than a wrong one.
    """
    import zlib

    try:
        data = open(path, "rb").read()
    except OSError:
        return ""

    parts: list[str] = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        chunk = m.group(1)
        try:
            chunk = zlib.decompress(chunk)
        except zlib.error:
            continue
        for t in re.findall(rb"\((.*?)\)\s*Tj", chunk):
            parts.append(t.decode("latin1"))
        for arr in re.findall(rb"\[(.*?)\]\s*TJ", chunk):
            parts.append("".join(
                x.decode("latin1") for x in re.findall(rb"\((.*?)\)", arr)
            ))
        if sum(len(p) for p in parts) > limit * 3:
            break

    text = " ".join(parts)
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=\w) - (?=\w)", "-", text)   # rejoin hyphen splits
    return text.strip()[:limit]


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true",
                    help="rebuild JSON from the local library without downloading")
    args = ap.parse_args()

    os.makedirs(LIBRARY, exist_ok=True)
    os.makedirs(DATA, exist_ok=True)

    log("ICC refresh  %s" % dt.datetime.now().isoformat(timespec="seconds"))
    log("  library: %s" % LIBRARY)

    html = fetch(ICC_URL)
    if not html:
        log("FAILED: could not fetch the ICC page. Nothing written.")
        return 1

    seen: dict[str, str] = {}
    entries = []
    for url, label in PUB_BOX_RE.findall(html):
        label = re.sub(r"<[^>]+>", "", label).strip()
        label = re.sub(r"\s+", " ", label)
        if url in seen:
            continue
        seen[url] = label
        entries.append((url, label))

    if not entries:
        log("FAILED: no documents found on the ICC page. The page markup has")
        log("        probably changed. Nothing written, so nothing is silently lost.")
        return 1

    log("  %d documents linked on the page" % len(entries))

    catalogue = []
    matrices = {}
    downloaded = skipped = failed = 0

    for url, label in sorted(entries, key=lambda e: e[1].lower()):
        filename = url.rsplit("/", 1)[-1]
        dest = os.path.join(LIBRARY, filename)
        kind = doc_type(filename)

        if not args.no_fetch and not os.path.exists(dest):
            blob = fetch(url, binary=True)
            if blob is None:
                failed += 1
                continue
            with open(dest, "wb") as fh:
                fh.write(blob)
            downloaded += 1
            time.sleep(0.4)          # be a considerate guest
        elif os.path.exists(dest):
            skipped += 1
        else:
            continue

        if not os.path.exists(dest):
            continue

        raw = open(dest, "rb").read()
        entry = {
            "category": label,
            "type": kind,
            "filename": filename,
            "source_url": url,
            "issued": parse_issue_date(filename),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()[:16],
        }

        if kind == "product_matrix":
            parsed = parse_matrix(dest)
            if parsed:
                entry["product_count"] = len(parsed["products"])
                entry["spec_columns"] = len(parsed["columns"])
                matrices[label] = {
                    "category": label,
                    "source_url": url,
                    "issued": entry["issued"],
                    **parsed,
                }
                log("  MATRIX  %-42s %3d products, %2d columns"
                    % (label[:42], len(parsed["products"]), len(parsed["columns"])))
        else:
            summary = pdf_text(dest, limit=4000)
            entry["summary"] = summary
            entry["has_text"] = bool(summary)

        catalogue.append(entry)

    catalogue.sort(key=lambda e: (e["type"], e["category"].lower()))

    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    n_matrix = sum(1 for e in catalogue if e["type"] == "product_matrix")
    n_support = sum(1 for e in catalogue if e["type"] == "support_document")

    cat_out = {
        "source": "NHS Supply Chain, Information for Clinical Choice",
        "source_url": ICC_URL,
        "licence": "Published openly by NHS Supply Chain. No login required.",
        "generated": stamp,
        "note": (
            "Only documents linked from the ICC page are held. The blob container "
            "does not permit listing, and unlinked filenames are never guessed. "
            "Product Matrices are the populated comparison grids; Support Documents "
            "are narrative descriptions of the features clinicians weigh, not grids."
        ),
        "counts": {
            "documents": len(catalogue),
            "product_matrices": n_matrix,
            "support_documents": n_support,
        },
        "documents": catalogue,
    }

    mat_out = {
        "source": "NHS Supply Chain, Information for Clinical Choice product matrices",
        "source_url": ICC_URL,
        "generated": stamp,
        "note": (
            "Specification-level comparison authored by NHS Supply Chain Clinical "
            "Collaboration Teams with NHS clinical stakeholders. Join to the NHSSC "
            "catalogue on the NPC column. A product appearing here is evidence it is "
            "available through NHS Supply Chain, not evidence of uptake at any trust."
        ),
        "matrix_count": len(matrices),
        "matrices": matrices,
    }

    with open(os.path.join(DATA, "icc-catalogue.json"), "w") as fh:
        json.dump(cat_out, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(DATA, "icc-matrices.json"), "w") as fh:
        json.dump(mat_out, fh, indent=1, ensure_ascii=False)

    total_products = sum(len(m["products"]) for m in matrices.values())
    log("")
    log("  downloaded %d, already held %d, failed %d" % (downloaded, skipped, failed))
    log("  catalogue: %d documents (%d matrices, %d support docs)"
        % (len(catalogue), n_matrix, n_support))
    log("  matrices:  %d products across %d categories" % (total_products, len(matrices)))
    log("  wrote data/icc-catalogue.json and data/icc-matrices.json")

    if failed:
        log("  NOTE: %d downloads failed. Re-run before relying on the counts." % failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
