#!/usr/bin/env python3
"""seed_format.py — write a JSON data file back in the byte format it already has.

WHY THIS EXISTS (21/09/2026, `^o584`)

  Five scripts write data/supplier-seed.json, and every one of them hardcoded a
  format and a comment asserting it was "the file's own format":

    scripts/seed_supplier_domains.py   minified, no trailing newline
    scripts/verify_name_proofs.py      minified, no trailing newline
    scripts/confirm_company_numbers.py minified, no trailing newline
    scripts/confirm_from_catalogue.py  minified, trailing newline
    scripts/refresh_brand_colours.py   minified, trailing newline
    scripts/merge_seed_on_retry.py     indent=2

  They cannot all be right, and on 21/09/2026 none of the minified ones were:
  the file on main was pretty-printed at indent 2 (7,578,190 bytes, 110,172
  lines), written that way by merge_seed_on_retry.py during a push race. So
  running seed_supplier_domains.py --write to add two fields would have rewritten
  all 110,172 lines as one, and the ultrasound-scanners run on 21/09 had to
  hand-edit the links array instead of using the script it has.

  In this repo a push to main IS a live publish (root rule 13) and the diff is
  the only review there is. A whole-file diff is not a cosmetic problem: it is
  the review disappearing.

THE RULE: nothing asserts what shape this file is in. Read the bytes you are
about to overwrite, match them, and say so if you could not.

  from seed_format import write_like
  write_like("data/supplier-seed.json", seed)

Round-tripping is checked, not assumed — write_like() returns the format it used
and whether re-serialising the file as it found it reproduced the original bytes
exactly. A False there means this writer is about to make a bigger diff than the
change deserves, and the caller should say so out loud rather than push quietly.
"""
import json
import os

# Observed on main at various times; see the memory note supplier-seed-is-single-line-json.
# Order matters only for reporting — detection reads the bytes, it does not guess
# from this list.
MINIFIED = "minified"


class Format:
    """How a JSON file is laid out on disk: indent, and trailing newline or not."""

    def __init__(self, indent, trailing_newline):
        self.indent = indent                      # None == minified
        self.trailing_newline = trailing_newline

    def __repr__(self):
        shape = MINIFIED if self.indent is None else "indent=%d" % self.indent
        return "%s%s" % (shape, ", trailing newline" if self.trailing_newline else ", no trailing newline")

    def __eq__(self, other):
        return (isinstance(other, Format)
                and self.indent == other.indent
                and self.trailing_newline == other.trailing_newline)

    def dumps(self, doc):
        if self.indent is None:
            text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        else:
            text = json.dumps(doc, ensure_ascii=False, indent=self.indent)
        return (text + "\n" if self.trailing_newline else text).encode("utf-8")


def detect(raw):
    """Work out the layout of `raw` (bytes) from the bytes themselves.

    Minified is 'no newline before the first key'. Otherwise the indent is the
    leading whitespace on the second line — json.dumps' own output always puts
    exactly one level of indent there, whatever the container type."""
    text = raw.decode("utf-8")
    trailing = text.endswith("\n")
    body = text[:-1] if trailing else text
    lines = body.split("\n")
    if len(lines) < 2:
        return Format(None, trailing)
    second = lines[1]
    indent = len(second) - len(second.lstrip(" "))
    # A pretty-printed file always indents its second line. Zero means something
    # else produced it (tabs, or a hand edit) — treat it as minified rather than
    # inventing indent=0, which json.dumps renders as newlines with no indent.
    return Format(indent if indent > 0 else None, trailing)


def dumps_like(doc, raw):
    """Serialise `doc` in the layout `raw` already uses.

    Returns (bytes, Format, round_trips) where round_trips is True only if
    re-serialising the ORIGINAL document in the detected format reproduced `raw`
    byte for byte — i.e. the detection is proven, not merely plausible."""
    fmt = detect(raw)
    try:
        round_trips = fmt.dumps(json.loads(raw.decode("utf-8"))) == raw
    except ValueError:
        round_trips = False
    return fmt.dumps(doc), fmt, round_trips


def write_like(path, doc):
    """Overwrite `path` with `doc`, keeping the layout the file already has.

    A file that does not exist yet has no format to keep, so it is written the
    way this repo's data files are written: pretty, indent 1, trailing newline.
    Returns (Format, round_trips) so the caller can report an unproven match."""
    if not os.path.exists(path):
        fmt = Format(1, True)
        with open(path, "wb") as f:
            f.write(fmt.dumps(doc))
        return fmt, True
    with open(path, "rb") as f:
        raw = f.read()
    out, fmt, round_trips = dumps_like(doc, raw)
    with open(path, "wb") as f:
        f.write(out)
    return fmt, round_trips


def describe(path, fmt, round_trips):
    """The one line a writer prints so a surprising diff is explained in the log,
    not discovered in review."""
    if round_trips:
        return "wrote %s in its existing format (%s)" % (path, fmt)
    return ("wrote %s as %s — WARNING: the file did not round-trip in any "
            "detected format, so expect a larger diff than the change itself"
            % (path, fmt))
