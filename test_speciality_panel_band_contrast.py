#!/usr/bin/env python3
"""app/speciality-panels.js: no card can inherit its text colour from the page.

WHY THIS EXISTS (16/11/2026)
  The same defect has now shipped to paying members twice.

  Every speciality page seats #msh-spec-frameworks inside `.band#suppliers-frameworks`,
  and that band's own <style> paints its descendants light — #F5F1E8 on
  `.inner`, `.inner p` and `.inner li`, #DBE3EE on `.sp-tbl th` and
  `.sp-rule summary`, #E0BE8E on `.inner a`. Those rules are not in this repo:
  they live in each page's markup, patched there by Cowork-OS
  `02-Elevate-and-Thrive/Hub/patch_frameworks_band_navy.py` and identical on
  all 43 live pages since 09/10/2026.

  The panels render WHITE cards (`background:var(--panel)`, #ffffff) inside
  that band. Any text in such a card that has no colour of its own inherits
  the band's light ink and disappears:

    * 08/10/2026, Patient Handling. `.msh #suppliers-frameworks .inner p`
      (0,1,2,1) beat `.msh .sp-li p` (0,0,2,1) and left the supplier fact text
      near-white on the white `.sp-li` card. Fixed by giving the panel rule an
      id: `.msh #msh-spec-frameworks .sp-sec .sp-li, ... .sp-li p`.
    * 16/11/2026, every panel. The Sources and freshness table's lede, its four
      column headers and its two unstyled columns measured 1.13:1 and 1.29:1 on
      the live wound care page — a whole table effectively invisible. The lede
      and headers lost on specificity; the two columns simply INHERITED, because
      `.sp-fresh` declared no colour at all. Fixed by 9d98ece9.

  Nothing caught either one. No check in this repo looks at colour, and a
  rendered measurement needs a signed-in member session, so it cannot run in
  the gate at all. This is the static half.

WHAT IT ENFORCES
  For every light-background card in the panel stylesheet, either

    (a) the card sets its own `color`, so everything inside it starts from the
        panel's ink rather than the host band's; or
    (b) every rule the panel writes for something inside that card sets a
        `color` of its own.

  A card that satisfies neither has at least one text-bearing descendant whose
  colour is whatever the host band happens to give it. That is the 16/11 defect
  exactly, and under (a) it is also how the 08/10 one was fixed.

WHAT IT DOES NOT COVER
  It asserts no contrast ratio: it cannot, without rendering. It also cannot
  see the other half of the 16/11 defect — a panel rule that does set a colour
  but loses the cascade to the band's id-level rule, which is why the lede and
  the `th` rules carry `!important`. Classes alone can never beat
  `.msh #suppliers-frameworks ...`, so a colour on a bare `p`, `li`, `a`, `th`
  or `summary` inside the frameworks band needs an id in the selector or
  `!important`. Checking that needs the band each card lands in, which this
  repo does not hold. Measure it on the live page instead — the method is in
  00-Resources/Session-Handovers/2026-11-16-hub-followups-push-and-dead-link.md.

    python3 test_speciality_panel_band_contrast.py
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(HERE, "app", "speciality-panels.js")

# Light grounds a card can sit on. On the live speciality pages var(--panel) is
# #ffffff and var(--panel2) is #F2F1ED, read from the page's own :root
# (16/11/2026). Anything here needs dark ink over it.
LIGHT_BACKGROUNDS = ("var(--panel)", "var(--panel2)", "#fff", "#ffffff", "#f2f1ed")

# Form controls carry their own colour and are not cards.
CONTROL_TAGS = ("select", "input", "button", "textarea", "option")


def stylesheet(src):
    """Every CSS rule string in the file's `st.textContent = [ ... ]` arrays.

    Parsed line by line, not by array span: the file has two such arrays and
    `].join('')` also occurs inside the first one, so slicing between the
    markers silently reads a tenth of the sheet and the guard passes on
    nothing.
    """
    out = []
    pat = re.compile(r"^\s*'(.*)',?\s*$")
    for line in src.split("\n"):
        m = pat.match(line)
        if not m:
            continue
        s = m.group(1)
        if "{" in s and "}" in s and ":" in s:
            out.append(s)
    return out


def rules(sheet):
    """[(selector_list, declarations)] for every rule in the sheet."""
    out = []
    for chunk in sheet:
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", chunk):
            out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def value_of(decls, prop):
    m = re.search(r"(?:^|;)\s*%s\s*:([^;]*)" % re.escape(prop), decls)
    return m.group(1).strip().lower() if m else None


def classes_in(selector):
    return re.findall(r"\.([A-Za-z0-9_-]+)", selector)


def last_element(selector):
    """The bare element name a compound selector ends on, or None."""
    part = re.split(r"[\s>+~]+", selector.strip())[-1]
    part = re.sub(r":{1,2}[A-Za-z-]+(\([^)]*\))?$", "", part)
    part = re.sub(r"\[[^\]]*\]", "", part)
    m = re.match(r"^([A-Za-z][A-Za-z0-9]*)", part)
    return m.group(1).lower() if m else None


def has_class(text, card):
    """True when `text` carries .card as a whole class, not as a prefix.

    `".sp-fresh" in ".sp-fresh-lede"` is true as a substring and false as a
    class, and getting that wrong let both historical defects through this
    guard while it was being written.
    """
    return re.search(r"\.%s(?![A-Za-z0-9_-])" % re.escape(card), text) is not None


def targets_card_itself(selector, card):
    """True when this selector's subject IS the card, not something inside it."""
    last = re.split(r"[\s>+~]+", selector.strip())[-1]
    return has_class(last, card)


class SpecialityPanelBandContrast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(JS, encoding="utf-8") as f:
            src = f.read()
        cls.sheet = stylesheet(src)
        cls.rules = rules(cls.sheet)
        cards = set()
        for sel, decls in cls.rules:
            bg = value_of(decls, "background") or value_of(decls, "background-color")
            if not bg or not any(b in bg for b in LIGHT_BACKGROUNDS):
                continue
            for one in sel.split(","):
                one = one.strip()
                if not one or last_element(one) in CONTROL_TAGS:
                    continue
                cs = classes_in(one)
                if len(cs) < 2:          # .msh, then the card's own class
                    continue
                cards.add(cs[-1])
        cls.cards = cards

    def test_the_sheet_parsed(self):
        """A parser that reads nothing would make the guard below vacuous."""
        self.assertGreater(len(self.rules), 100,
                           "only %d rules parsed out of app/speciality-panels.js"
                           % len(self.rules))
        self.assertGreater(len(self.cards), 3,
                           "only %d light cards found; parser or palette is wrong"
                           % len(self.cards))

    def test_no_card_inherits_its_text_colour(self):
        bad = []
        for card in sorted(self.cards):
            own, inside, uncoloured = False, 0, []
            for sel, decls in self.rules:
                if not has_class(sel, card):
                    continue
                has_colour = value_of(decls, "color") is not None
                if any(targets_card_itself(one, card) for one in sel.split(",")):
                    own = own or has_colour
                else:
                    inside += 1
                    if not has_colour:
                        uncoloured.append(sel)
            if own:
                continue
            if inside and not uncoloured:
                continue                 # every styled descendant names its ink
            bad.append((card, uncoloured[:3]))
        self.assertEqual(
            [], bad,
            "card(s) on a light background neither set their own colour nor give "
            "one to everything inside them, so that text inherits whatever the "
            "host band paints — near-white on white in the navy Frameworks band "
            "(the Sources and freshness defect, 16/11/2026). Set `color` on the "
            "card: " + "; ".join("%s (e.g. %s)" % (c, ", ".join(u) or "nothing styled inside it")
                                 for c, u in bad))



# ---------------------------------------------------------------------------
# The band-seated half, added 16/11/2026.
#
# The docstring above says the host band "is not held in this repo". For one
# block that is not quite true, and the gap it left had shipped: #suppliers-
# frameworks is #14304F on all 43 live pages and has been since 09/10/2026,
# asserted by the computed-background check recorded in Cowork-OS
# "Process flows for all brands/speciality-frameworks-band-navy-2026-10-09.md".
# A known ground means a real contrast ratio CAN be computed without rendering
# -- but only for a block with no light card between it and the band.
#
# addCalendarAndPins() appends #sp-cal-slot straight to #msh-spec-frameworks,
# so the calendar is exactly that block, and the only one. Its rules were
# written for a light card: measured signed-in on the live pages on 16/11/2026
# the dates were 1.27:1, the meta line 2.90:1 and the three .empty-state
# messages 1.13:1, on every panel. Neither existing test could see it: the one
# above looks only at cards with a light background of their own.
#
# LIMIT: this can only judge colours THIS repo sets. .empty-state takes its
# dark ink from each page's own CSS, so pre-fix it was invisible here too; the
# fix pins it explicitly in the panel sheet, which is what makes it checkable.
BAND_GROUND = "#14304f"

# Read from the live pages' :root, signed in, 16/11/2026. Same discipline as
# LIGHT_BACKGROUNDS above: this repo does not hold the page palette.
PALETTE = {
    "var(--ink)": "#1d2733",
    "var(--navy)": "#0b1c33",
    "var(--dim)": "#6b7683",
    "var(--gold)": "#a8842c",
    "var(--panel)": "#ffffff",
    "var(--panel2)": "#f2f1ed",
}

CAL_SLOT = "#sp-cal-slot"


def _hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _luminance(rgb):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def resolve_colour(value):
    """A declaration's colour as rgb, resolving the page palette. None if unknown."""
    v = value.strip().rstrip("!important").strip().lower()
    if v in PALETTE:
        v = PALETTE[v]
    if v.startswith("#"):
        return _hex_to_rgb(v)
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
    if m:
        return tuple(int(m.group(i)) for i in (1, 2, 3))
    return None


def specificity(selector):
    """(ids, classes, elements) for one compound selector."""
    s = re.sub(r"\[[^\]]*\]", " attr ", selector)
    ids = len(re.findall(r"#[A-Za-z0-9_-]+", s))
    classes = len(re.findall(r"\.[A-Za-z0-9_-]+", s)) + s.count(" attr ")
    classes += len(re.findall(r":(?!:)(?!hover|focus|active|visited|first-child|last-child)[A-Za-z-]+", s))
    elements = len([p for p in re.split(r"[\s>+~]+", s.strip())
                    if re.match(r"^[A-Za-z]", p)])
    return (ids, classes, elements)


def calendar_source(src):
    """The JS that builds the calendar: calHtml() plus the slot's own innerHTML."""
    out = []
    for name in ("function calHtml()", "function addCalendarAndPins("):
        i = src.find(name)
        if i < 0:
            continue
        j = src.find("\n  function ", i + 1)
        out.append(src[i:j if j > 0 else len(src)])
    return "\n".join(out)


class CalendarSeatedOnTheBand(unittest.TestCase):
    """The calendar has no card under it, so its ink must suit #14304F."""

    @classmethod
    def setUpClass(cls):
        with open(JS, encoding="utf-8") as f:
            cls.src = f.read()
        cls.sheet = stylesheet(cls.src)
        cls.rules = rules(cls.sheet)
        cls.cal_src = calendar_source(cls.src)
        seated = set()
        for m in re.finditer(r'class="([^"]*)"', cls.cal_src):
            for c in m.group(1).split():
                if c:
                    seated.add(c)
        cls.seated = seated
        # Classes that bring their own light ground are the other test's business.
        own_light = set()
        for sel, decls in cls.rules:
            bg = value_of(decls, "background") or value_of(decls, "background-color")
            if bg and any(b in bg for b in LIGHT_BACKGROUNDS):
                for one in sel.split(","):
                    last = re.split(r"[\s>+~]+", one.strip())[-1]
                    own_light.update(re.findall(r"\.([A-Za-z0-9_-]+)", last))
        cls.own_light = own_light

    def test_it_found_the_calendar_and_its_classes(self):
        self.assertIn("sp-cal-row", self.seated,
                      "the calendar builder was not parsed; "
                      "found classes: %s" % sorted(self.seated))
        self.assertIn(CAL_SLOT.lstrip("#"), self.src,
                      "the calendar slot id changed; this test is scoped to it")

    def test_the_band_ground_is_still_what_we_assume(self):
        rgb = _hex_to_rgb(BAND_GROUND)
        self.assertIsNotNone(rgb)
        # Sanity: the band is dark, so light ink is what passes on it.
        self.assertLess(_luminance(rgb), 0.1, "BAND_GROUND is no longer dark")
        self.assertGreater(contrast(_hex_to_rgb("#f5f1e8"), rgb), 4.5)
        self.assertLess(contrast(_hex_to_rgb("#1d2733"), rgb), 4.5)

    def test_calendar_ink_passes_on_the_navy_band(self):
        band = _hex_to_rgb(BAND_GROUND)
        bad = []
        for cls_name in sorted(self.seated):
            if cls_name in self.own_light:
                continue                      # it carries its own light ground
            winner, best = None, None
            for sel, decls in self.rules:
                col = value_of(decls, "color")
                if col is None:
                    continue
                for one in sel.split(","):
                    one = one.strip()
                    if not has_class(one, cls_name):
                        continue
                    if not targets_card_itself(one, cls_name):
                        continue
                    spec = specificity(one)
                    if best is None or spec >= best:
                        best, winner = spec, (one, col)
            if winner is None:
                continue                      # this repo sets no colour for it
            rgb = resolve_colour(winner[1])
            if rgb is None:
                continue
            ratio = contrast(rgb, band)
            if ratio < 4.5:
                bad.append("%s -> %s (%s) = %.2f:1 via `%s`"
                           % (cls_name, winner[1].strip(),
                              "#%02x%02x%02x" % rgb, ratio, winner[0]))
        self.assertEqual(
            [], bad,
            "the calendar is appended straight to #msh-spec-frameworks, so its "
            "ground is the navy band (%s) and not a light card. These rules "
            "colour it for a light card, so the text is near-invisible to a "
            "signed-in member -- the 16/11/2026 defect (dates 1.27:1, meta "
            "2.90:1, empty states 1.13:1 on all 43 panels). Add a band-scoped "
            "light rule under %s: %s"
            % (BAND_GROUND, CAL_SLOT, "; ".join(bad)))

if __name__ == "__main__":
    unittest.main(verbosity=2)
