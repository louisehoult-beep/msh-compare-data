#!/usr/bin/env python3
"""
mint_data_ref.py — mint the data-file marker ref for a new file in data/, and
add it to scripts/stamp_notice.py.

WHY THIS EXISTS
---------------
verify.py blocks the push when a file in data/ has no ref in stamp_notice.py's
REFS table. Until now the only way to mint one was to work out the hashing
scheme by hand from the salt, which meant putting the salt in front of whoever
was doing the minting. That is the one thing the 06/08/2026 redaction was for.

This script never prints the salt and never writes it anywhere. It reads it the
same two ways decode-marker.py does, works out the scheme by REPRODUCING the
refs already published in stamp_notice.py, and only then applies that scheme to
the new filename. If it cannot reproduce every existing ref it stops and says
so, rather than minting something that looks right and is not — a wrong ref is
worse than no ref, because a marker that decodes to nothing cannot prove where
a copy came from, and nobody would find out until they needed it in a dispute.

USAGE
    python3 scripts/mint_data_ref.py interview-prep.json          # print it
    python3 scripts/mint_data_ref.py interview-prep.json --write  # and add it

After --write, run the usual two:
    python3 scripts/stamp_notice.py
    python3 verify.py
"""
import hashlib
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
STAMP = HERE / "stamp_notice.py"


def salt():
    v = os.environ.get("ETH_MARKER_SALT")
    if v:
        return v.strip()
    f = pathlib.Path(os.path.expanduser("~/.eth-marker-salt"))
    if f.is_file():
        return f.read_text().strip()
    raise SystemExit(
        "No salt. Set ETH_MARKER_SALT, or restore ~/.eth-marker-salt from the "
        "password manager. Without it no ref can be minted."
    )


def known_refs(text):
    block = re.search(r"REFS\s*=\s*\{(.*?)\n\}", text, re.S)
    if not block:
        raise SystemExit("Could not find the REFS table in stamp_notice.py.")
    return dict(re.findall(r'"([^"]+\.json)":\s*"(ETH-[A-Z0-9]+)"', block.group(1)))


# Every scheme that could plausibly have produced the published refs. The right
# one is whichever reproduces ALL of them; anything less is not a match.
SCHEMES = {
    'sha256(salt + "d" + filename)':
        lambda s, f: hashlib.sha256((s + "d" + f).encode()).hexdigest(),
    'sha256(salt + "d" + stem)':
        lambda s, f: hashlib.sha256((s + "d" + f[:-5]).encode()).hexdigest(),
    'sha256(salt + "D" + filename)':
        lambda s, f: hashlib.sha256((s + "D" + f).encode()).hexdigest(),
    'sha256(salt + filename)':
        lambda s, f: hashlib.sha256((s + f).encode()).hexdigest(),
    'sha256(salt + "data/" + filename)':
        lambda s, f: hashlib.sha256((s + "data/" + f).encode()).hexdigest(),
    'sha256(salt + "d" + "data/" + filename)':
        lambda s, f: hashlib.sha256((s + "d" + "data/" + f).encode()).hexdigest(),
}


def find_scheme(s, refs):
    for name, fn in SCHEMES.items():
        if all("ETH-D" + fn(s, f)[:8].upper() == r for f, r in refs.items()):
            return name, fn
    return None, None


def add_to_stamp(text, filename, ref):
    if f'"{filename}"' in text:
        return text, False
    block = re.search(r"(REFS\s*=\s*\{)(.*?)(\n\})", text, re.S)
    body = block.group(2)
    rows = re.findall(r'\n(\s*)"([^"]+\.json)":(\s*)"(ETH-[A-Z0-9]+)",', body)
    indent = rows[0][0] if rows else "    "
    # Match the column the existing values are aligned to, so the diff is one line.
    width = max(len(f'"{f}":') for _, f, _, _ in rows)
    new = '\n%s%s %s"%s",' % (indent, f'"{filename}":'.ljust(width), "", ref)
    names = [f for _, f, _, _ in rows] + [filename]
    at = sorted(names).index(filename)
    if at >= len(rows):
        body = body.rstrip().rstrip(",") + "," + new
    else:
        anchor = re.search(r'\n\s*"%s":\s*"ETH-[A-Z0-9]+",' % re.escape(rows[at][1]), body)
        body = body[:anchor.start()] + new + body[anchor.start():]
    return text[:block.start()] + block.group(1) + body + block.group(3) + text[block.end():], True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--write" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 1
    filename = args[0].split("/")[-1]
    text = STAMP.read_text()
    refs = known_refs(text)
    if filename in refs:
        print("%s already has a ref: %s" % (filename, refs[filename]))
        return 0
    name, fn = find_scheme(salt(), refs)
    if not fn:
        print("STOP. None of the known schemes reproduces the %d published refs." % len(refs))
        print("Either the salt has been rotated, or the refs were minted another way.")
        print("Do not guess a ref: mint it the way the originals were minted.")
        return 1
    ref = "ETH-D" + fn(salt(), filename)[:8].upper()
    print("scheme verified against all %d published refs: %s" % (len(refs), name))
    print("%-26s %s" % (filename, ref))
    if write:
        out, changed = add_to_stamp(text, filename, ref)
        if changed:
            STAMP.write_text(out)
            print("added to scripts/stamp_notice.py — now run:")
            print("    python3 scripts/stamp_notice.py && python3 verify.py")
        else:
            print("stamp_notice.py already mentions it; left alone.")
    else:
        print("re-run with --write to add it to stamp_notice.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
