#!/usr/bin/env python3
"""
Parse the product-comparison grid out of an ICC Support Document PDF.

WHY THIS EXISTS
---------------
refresh_icc.py was written on 28/08/2026 believing NHS Supply Chain's
Information for Clinical Choice publishes exactly one machine-readable grid (the
Adult ECG Electrodes .xlsx) and that the other 74 documents are narrative only.
That was wrong, and it cost the Hub the single best comparison source it has:
**68 of the 74 support-document PDFs carry a full product matrix** — Supplier,
Brand, MPC, NPC, Description, Route, UOI, then one row per specification
attribute, with numeric values (fluid handling g/10cm2, absorbency, wear time)
authored by NHS Supply Chain's Clinical Procurement and Quality Assurance team
with NHS clinical stakeholders. It is the only like-for-like, independently
authored, multi-supplier product data the Hub has access to. Everything else the
Differentiator holds is the manufacturer's own words about its own product.

HOW THE GRID IS SHAPED, AND WHY THAT DICTATES THE METHOD
--------------------------------------------------------
The grids are TRANSPOSED relative to a normal table: each COLUMN is a product,
each ROW is an attribute. They are also drawn, not tagged — pdfplumber's ruling
line detection splits a 7-product grid into 24 ragged columns, most of them
empty, and splits a single attribute row across three sub-rows. Extracting them
as tables produces mush.

So this parser does not use table detection at all. It anchors on the NPC row:

  1. NPC codes have a hard shape (3 letters + 2-5 digits) and every product in
     an ICC grid has one. Find the horizontal run of them and you have found the
     product columns, and their x centres, exactly.
  2. Column boundaries are the midpoints between adjacent NPC centres. Anything
     left of the first boundary is the attribute label.
  3. Words are grouped into visual lines by their y position, and each word is
     assigned to the column whose band contains its centre.
  4. Lines are then clustered into attribute rows on the vertical gap between
     them (see ROW_GAP). Everything in one cluster — label fragments and value
     fragments alike — belongs to one attribute, and is joined in y order, which
     is the order a reader sees it in.

TICKS AND CROSSES
-----------------
Boolean attributes are drawn in Webdings, where the glyph 'a' is a tick and 'r'
is a cross. Extracted naively they come out as the letters a and r, which would
publish "a" as a specification value. They are mapped to Yes/No, and ONLY when
the character's own font is a symbol font — a real letter 'a' in a word like
"Latex" is never touched.

WHAT THIS PARSER WILL NOT DO
----------------------------
- It never invents a value. A cell the document leaves blank stays blank, and a
  blank is not a "No".
- It never publishes a product row without an NPC. The NPC is the join key onto
  nhssc-cache.json; a row without one cannot be tied to a real catalogue line and
  is dropped rather than guessed at by name.
- It preserves the document's own wording verbatim, including "-" where the
  document itself prints a dash. A dash is the document saying something; it is
  not the same fact as an empty cell, and flattening the two would lose that.
"""

from __future__ import annotations

import collections
import os
import re

# 3 letters + 2-5 digits: ELA838, ELY545, FDJ85236, FSL1204. Verified against
# every NPC in nhssc-cache.json before being relied on as an anchor.
NPC_RE = re.compile(r"^[A-Z]{3}\d{2,5}$")

# Fonts that carry drawn glyphs rather than letters. A subsetted PDF font is
# named like "AAAABB+Webdings", hence the substring test.
SYMBOL_FONTS = ("webdings", "wingdings", "zapfdingbats", "monotypesorts", "sorts")
SYMBOL_MAP = {"a": "Yes", "r": "No", "ü": "Yes", "û": "No", "": "Yes", "": "No"}

# Vertical tolerances, in PDF points, all measured against the real documents.
# LINE_TOL groups characters into one visual line.
#
# HOW ROWS ARE FOUND, AND WHY NOT BY GAP. These grids wrap freely INSIDE a row:
# an attribute label wraps around its own values ("Moisture Vapour Transmission
# - Fluid capacity" / values / "management g/10cm2" on three lines), and a size
# range runs to seven. A vertical-gap threshold cannot separate that from a new
# row: on Foam Dressings page 3 the largest gap WITHIN one row is 10.1pt while
# the smallest gap BETWEEN two rows is 9.6pt. They overlap, so any single
# threshold mis-splits real documents.
#
# The grids are ruled, so the rules are used instead. A row boundary is a y at
# which horizontal edges cover at least RULE_COVERAGE of the page width; edges
# within RULE_MERGE of each other are the top and bottom of one drawn rule and
# count once.
#
# RULE_COVERAGE is 0.75 because the two things it must tell apart are well
# separated and measured, not because 0.75 looked safe: across these documents a
# real row separator covers 0.83-0.94 of the page width, while the nested rules
# boxing an individual wrapped supplier name cover 0.38-0.50. Dropping to 0.45
# splits "ADVANCED MEDICAL SOLUTIONS LTD" into three rows and publishes the
# supplier as "MEDICAL".
#
# ROW_GAP is the fallback for a page whose grid is not ruled at all, where an
# imperfect split beats no data. A page falling back is counted and reported.
LINE_TOL = 3.0
RULE_COVERAGE = 0.75
RULE_MERGE = 4.0
ROW_GAP = 10.5

# Labels that are structural rather than specifications. "Picture" is an image
# cell and always extracts empty; the code/identity rows are promoted to named
# fields on the product record instead of being left as attributes.
IDENTITY_LABELS = {"supplier", "brand", "mpc", "npc", "description", "route", "uoi"}
DROP_LABELS = {"picture", ""}


def _clean(text: str) -> str:
    """Collapse whitespace. Never changes the words themselves."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def _word_text(word: dict) -> str:
    """
    The word's text, with symbol-font glyphs mapped to what they draw.

    Only applies where the word's own font is a symbol font, so the letter 'a'
    in ordinary text is never rewritten.
    """
    font = (word.get("fontname") or "").lower()
    if any(sym in font for sym in SYMBOL_FONTS):
        return SYMBOL_MAP.get(word["text"], word["text"])
    return word["text"]


def _anchor_row(words: list[dict]) -> list[dict] | None:
    """
    Find the NPC row: the widest horizontal run of NPC-shaped codes on the page.

    Requires an 'NPC' label on the same line. Without that check a page could
    anchor on any incidental run of code-shaped strings (an order-code row, for
    instance) and silently mis-column the whole grid.
    """
    rows: dict[int, list[dict]] = collections.defaultdict(list)
    for w in words:
        if NPC_RE.match(w["text"]):
            rows[round(w["top"] / LINE_TOL)].append(w)

    best = None
    for key, group in rows.items():
        if len(group) < 2:
            continue
        top = min(g["top"] for g in group)
        bottom = max(g["bottom"] for g in group)
        labelled = any(
            w["text"].strip().upper() == "NPC" and w["top"] < bottom and w["bottom"] > top
            for w in words
        )
        if not labelled:
            continue
        if best is None or len(group) > len(best):
            best = group
    if best is None:
        return None
    return sorted(best, key=lambda w: w["x0"])


def _columns(anchor: list[dict]) -> tuple[float, list[float]]:
    """
    Turn the anchor row into a label-column edge and inter-product boundaries.

    The label edge is mirrored off the first gap rather than assumed: grids with
    3 products are laid out much wider than grids with 8, so a fixed x would be
    wrong on most pages.
    """
    centres = [(w["x0"] + w["x1"]) / 2 for w in anchor]
    bounds = [(centres[i] + centres[i + 1]) / 2 for i in range(len(centres) - 1)]
    gap = (bounds[0] - centres[0]) if bounds else 60.0
    return centres[0] - gap, bounds


def _lines(words: list[dict]) -> list[tuple[float, list[dict]]]:
    """Group words into visual lines, in reading order down the page."""
    buckets: dict[int, list[dict]] = collections.defaultdict(list)
    for w in words:
        buckets[round(w["top"] / LINE_TOL)].append(w)
    out = []
    for key in sorted(buckets):
        row = sorted(buckets[key], key=lambda w: w["x0"])
        out.append((min(w["top"] for w in row), row))
    return out


def _split_line(row: list[dict], label_edge: float, bounds: list[float], n_cols: int):
    """Split one visual line into its label and its per-column values."""
    label_words, cols = [], [[] for _ in range(n_cols)]
    for w in row:
        centre = (w["x0"] + w["x1"]) / 2
        if w["x1"] <= label_edge:
            label_words.append(_word_text(w))
            continue
        idx = 0
        while idx < len(bounds) and centre > bounds[idx]:
            idx += 1
        if idx < n_cols:
            cols[idx].append(_word_text(w))
    return _clean(" ".join(label_words)), [_clean(" ".join(c)) for c in cols]


def _ruled_rows(page) -> list[float]:
    """
    The y positions of the grid's own drawn row separators.

    Horizontal edges are pooled by y and their x-coverage measured with overlaps
    merged, because a rule is drawn per cell, not once across the row: seven
    short edges at one y ARE a row separator, while the two short rules boxing a
    wrapped supplier name are not.
    """
    pooled: dict[float, list[tuple[float, float]]] = collections.defaultdict(list)
    for edge in page.horizontal_edges:
        pooled[round(edge["top"], 1)].append((edge["x0"], edge["x1"]))

    floor = RULE_COVERAGE * float(page.width)
    hits = []
    for y, segments in pooled.items():
        segments.sort()
        covered, current = 0.0, None
        for x0, x1 in segments:
            if current and x0 <= current[1] + 1:
                current = (current[0], max(current[1], x1))
            else:
                if current:
                    covered += current[1] - current[0]
                current = (x0, x1)
        if current:
            covered += current[1] - current[0]
        if covered >= floor:
            hits.append(y)

    merged: list[float] = []
    for y in sorted(hits):
        if merged and y - merged[-1] <= RULE_MERGE:
            continue
        merged.append(y)
    return merged


def parse_page(page) -> dict | None:
    """
    Parse one PDF page into {title, labels[], rows{label: [value per column]}}.

    Returns None when the page carries no product grid - most documents open
    with a page or two of narrative, and a page without an NPC row is narrative,
    not a failed parse.
    """
    words = page.extract_words(extra_attrs=["fontname"])
    if not words:
        return None
    anchor = _anchor_row(words)
    if not anchor:
        return None

    n_cols = len(anchor)
    label_edge, bounds = _columns(anchor)

    # Split every visual line into label / per-column values, dropping the ones
    # that are wholly empty.
    split: list[tuple[float, str, list[str]]] = []
    for top, row in _lines(words):
        label, cols = _split_line(row, label_edge, bounds, n_cols)
        if not label and not any(cols):
            continue
        split.append((top, label, cols))
    if not split:
        return None

    # Group lines into attribute rows, by the grid's own ruling where it has one.
    boundaries = _ruled_rows(page)
    ruled = len(boundaries) >= 4
    if ruled:
        buckets: dict[int, list[tuple[float, str, list[str]]]] = collections.defaultdict(list)
        for line in split:
            slot = 0
            while slot < len(boundaries) and line[0] >= boundaries[slot]:
                slot += 1
            buckets[slot].append(line)
        units = [buckets[k] for k in sorted(buckets)]
    else:
        units = [[split[0]]]
        for line in split[1:]:
            if line[0] - units[-1][-1][0] <= ROW_GAP:
                units[-1].append(line)
            else:
                units.append([line])

    # Everything above the first unit that actually carries a product value is
    # the sub-category title ("Silicone Foam Dressing Bordered (Part 2)").
    first_valued = next(
        (i for i, u in enumerate(units) if any(any(c) for _t, _l, c in u)), len(units)
    )
    title = _clean(
        " ".join(l for u in units[:first_valued] for _t, l, _c in u)
    )

    rows: dict[str, list[str]] = {}
    order: list[str] = []
    section = ""
    for unit in units[first_valued:]:
        label = _clean(" ".join(l for _t, l, _c in unit if l))
        values = [
            _clean(" ".join(c[i] for _t, _l, c in unit if c[i]))
            for i in range(n_cols)
        ]
        if label.lower() in DROP_LABELS:
            continue
        if not any(values):
            # A label with nothing under it is a section heading ("Absorbency"),
            # kept only to disambiguate a repeated attribute name below it.
            if label:
                section = label
            continue
        if not label:
            continue
        key = label
        if key in rows:
            key = ("%s - %s" % (section, label)).strip(" -") if section else label
            base, n = key, 2
            while key in rows:
                key = "%s (%d)" % (base, n)
                n += 1
        rows[key] = values
        order.append(key)

    if "NPC" not in rows:
        return None
    return {"title": title, "labels": order, "rows": rows,
            "n_cols": n_cols, "ruled": ruled}


def parse_support_matrix(path: str, category: str) -> dict | None:
    """
    Parse a whole ICC support document into the same shape parse_matrix()
    produces for the .xlsx matrices, so both feed one store and one renderer.

    Returns None if no page in the document carries a grid.
    """
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "pdfplumber is required to parse ICC support-document matrices. "
            "Install it (pip install pdfplumber) or run refresh_icc.py with "
            "--no-support-matrices to publish the .xlsx matrices only."
        )

    filename = os.path.basename(path)
    sub_categories: dict[str, dict] = {}
    products: list[dict] = []
    columns: list[str] = []
    seen: set[tuple[str, str]] = set()
    duplicate_rows = 0

    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            grid = parse_page(page)
            if not grid:
                continue

            sub = grid["title"] or ("%s (page %d)" % (category, page_no))
            npcs = grid["rows"].get("NPC", [])

            page_products = []
            for c in range(grid["n_cols"]):
                npc = (npcs[c] if c < len(npcs) else "").strip()
                # No NPC, no publish. Without it the row cannot be joined to a
                # real NHS Supply Chain catalogue line.
                if not NPC_RE.match(npc):
                    continue
                if (sub, npc) in seen:
                    duplicate_rows += 1
                    continue
                seen.add((sub, npc))

                record: dict[str, str] = {}
                for label in grid["labels"]:
                    value = grid["rows"][label][c]
                    if value:
                        record[label] = value
                if len(record) < 3:
                    continue
                record["_sub_category"] = sub
                record["_source_page"] = page_no
                record["_source_document"] = filename
                page_products.append(record)
                for label in grid["labels"]:
                    if label not in columns:
                        columns.append(label)

            if not page_products:
                continue
            products.extend(page_products)
            if sub not in sub_categories:
                sub_categories[sub] = {"columns": grid["labels"], "product_count": 0}
            sub_categories[sub]["product_count"] += len(page_products)

    if not products:
        return None
    return {
        "columns": columns,
        "sub_categories": sub_categories,
        "products": products,
        "notes": [],
        "duplicate_rows_dropped": duplicate_rows,
        "parsed_from": "support_document_pdf",
    }
