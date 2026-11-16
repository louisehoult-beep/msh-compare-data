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


if __name__ == "__main__":
    unittest.main(verbosity=2)
