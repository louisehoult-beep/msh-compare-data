"""BNF product rules shared by the NHSBSA prescribing builders.

Used by scripts/refresh_hospital_prescribing.py. The same rules were written first
for scripts/refresh_gp_prescribing.py (GP prescribing by ICB, built 29/09/2026 and
not yet landed); when that lands it can import these instead of carrying its own
copy, so the two tools cannot drift apart on what a "product" is.

Stdlib only. Pure functions, tested offline in test_bnf_products.py.
"""

import collections
import re

# Appliances, dressings and devices. Their BNF codes are 11 characters, so there is
# no 13-character child to split to, and characters 10-11 are not a brand/generic
# segment in the drug sense.
APPLIANCE_CHAPTERS = {"20", "21", "22", "23"}


def label_of(name):
    """Truncate a BNF name at its first word that starts with a digit.
    'Zopiclone 3.75mg tablets' -> 'Zopiclone'.

    A digit INSIDE a word is part of the brand and is kept (30/09/2026): 'E45 cream'
    used to become 'E', 'Fifty:50 ointment' became 'Fifty:' and 'Adcal-D3' became
    'Adcal-D', which put wrong brand names on the prescribing tools and would have
    put them in the emollient brand-share table. A name that starts with a digit
    ('3M Cavilon barrier cream') or has none is kept whole.
    """
    m = re.search(r"(?:^|\s)[(\[]?\d", name or "")
    return ((name[:m.start()] if m else name) or "").strip(" _-") or (name or "").strip()


def first_word(label):
    """The brand word of a label: its first alphanumeric token, lower-cased.

    Tokens split on any non-alphanumeric character, so a BNF suffix joined by a
    hyphen or underscore stays with its brand: 'Adizem-XL' and 'Adizem-SR' are both
    'adizem', 'Fybogel_Gran Sach' and 'Fybogel' are both 'fybogel'. BNF's leading
    'Half' (half-strength presentations: 'Half Sinemet CR', 'Half Securon SR') is
    skipped, because the brand is the word after it.

    The GP builder's first version stripped punctuation instead of splitting on it,
    which read 'Adizem-XL' as 'adizemxl' and split 14 hospital codes that each held
    one brand. Changed 29/09/2026 when the rule was shared.
    """
    toks = re.findall(r"[a-z0-9]+", (label or "").lower())
    if len(toks) > 1 and toks[0] == "half":
        toks = toks[1:]
    return toks[0] if toks else ""


def product_codes(names13):
    """Map each 13-character BNF code to the product code it is counted under.

    names13: {code13: Counter({BNF_NAME: items})}. An 11-character code (an
    appliance) may be passed too; it always maps to itself.

    Normally the product is characters 1-11 and characters 12-13 are the strength or
    form of that one product. But BNF's catch-all "substances" put many unrelated
    brands under one 11-character code: 130201000BB ("Other emollient preparations")
    holds Dermol, Doublebase, Aveeno, E45 and more, and only characters 12-13 tell
    them apart. Counting at 11 characters labels all of them with whichever brand
    sold most ("Dermol").

    So: where the 13-character children of one 11-character code carry labels that
    do not all begin with the same word, each child is its own product (characters
    1-13). Where they do (Zimovane 3.75mg / 7.5mg; Epilim / Epilim Chrono), they
    stay one product, so a brand is never fragmented by strength or form.

    A generic ('AA' in characters 10-11) is never split: it is one molecule by
    definition, and splitting it on naming noise ("Pot chloride" vs "Potassium
    chloride") would break the generic's share.
    """
    labels = collections.defaultdict(dict)
    for c13, counter in names13.items():
        top = counter.most_common(1)
        labels[c13[:11]][c13] = label_of(top[0][0]) if top else c13
    out = {}
    for c11, kids in labels.items():
        split = (c11[9:11] != "AA" and len(c11) == 11
                 and any(len(k) >= 13 for k in kids)
                 and len({first_word(v) for v in kids.values()}) > 1)
        for c13 in kids:
            out[c13] = c13[:13] if split else c13[:11]
    return out


def split_codes(pmap):
    """The 11-character codes that product_codes() split, sorted."""
    return sorted({v[:11] for v in pmap.values() if len(v) == 13})
