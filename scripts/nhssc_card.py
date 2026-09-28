#!/usr/bin/env python3
"""Read one NHS Supply Chain pilot-catalogue search card, by field, never by position.

Shared by scripts/refresh_nhssc_cache.py (name search) and
scripts/seed_nhssc_from_icc_npc.py (NPC search), so the two can never drift into
reading the same card two different ways again. No playwright import here: the
parser is pure, so test_nhssc_card.py runs offline in the unit-test job.

WHY IT CHANGED (28/09/2026)
  Both scripts used to split the card's innerText into lines and take
  lines[0], [1], [2] as brand, supplier and description, then guess the MPC
  and status from the leftovers. At the 1200px viewport the refresh uses:

  * the MPC sits in data-cy="productMPC" with no class at all, so the old
    `[class*="product-card_mpc"]` selector (which only matches the phone
    layout's productMPCMobile) found nothing, and the fallback took the NPC
    as the MPC. 4,813 of 15,028 cache rows had mpc == npc.
  * an all-letter MPC ("VCDTCE", "Maxri") failed the `not ln.isalpha()` code
    test and was title-cased into `status` instead: 73 junk statuses.
  * a "SUSPENDED" badge renders ABOVE the brand, so every field slid one place
    (ELA679: name "SUSPENDED", supplier "Cuticell Contact", desc "ESSITY UK
    TENA HM"). A card with no brand line slid the other way, so desc held the
    MPC (FDQ3419, FDD2248/2249/2253/2257).

  Every field on the card carries its own data-cy attribute, verified live
  28/09/2026 on ELA679, FDQ3419 and 187 cards across ten searches. Reading
  those is the fix; there is no positional fallback, because a guessed field is
  a worse fault than a missing card (the refresh's 0.8x never-shrink guard makes
  a selector change fail loudly instead).

ITEM SHAPE (unchanged, so every consumer keeps working)
  name     the card's BRAND line ("Cuticell Contact"); "" when the card has none
  supplier the supplier line ("ESSITY UK TENA HM")
  desc     the product name/description line
  npc, mpc, status ("Suspended" etc., title case; "" when live), pack, img
"""
import re

EXTRACT_JS = r"""
() => Array.from(document.querySelectorAll('div.cardWrapper')).map(card => {
  const txt = sel => { const e = card.querySelector(sel); return e ? (e.textContent || '').trim() : ''; };
  const img = card.querySelector('img[src*="media.supplychain"]');
  let npcClass = '';
  const prev = card.querySelector('[class*="product-card-prev-"]');
  if (prev) { const m = String(prev.className).match(/product-card-prev-([A-Z0-9]+)/); if (m) npcClass = m[1]; }
  const badges = Array.from(card.querySelectorAll('[class*="badge_badge"]'))
    .filter(e => e.getAttribute('data-cy') !== 'productNPC')
    .map(e => (e.textContent || '').trim()).filter(Boolean);
  return {
    brand: txt('[data-cy="productBrand"]'),
    supplier: txt('[data-cy="productSupplier"]'),
    name: txt('[data-cy="productName"]'),
    mpc: txt('[data-cy="productMPC"]') || txt('[data-cy="productMPCMobile"]'),
    npc: txt('[data-cy="productNPC"]'),
    npcClass: npcClass,
    badges: badges,
    uom: txt('[data-cy="uom"]'),
    img: img ? img.src : ''
  };
})
"""

# NPCs seen in the cache: letters then digits, sometimes a letter suffix
# (ELA679, FDQ3419, FAL15619, CFP213H). Anything else in the NPC slot means the
# card is not what we think it is.
NPC_RE = re.compile(r"^[A-Z]{2,5}\d{2,6}[A-Z]{0,2}$")

# A badge that is a card status, not a field. Kept in step with
# build_product_dossiers.STATUS_BADGES, which guards the same shapes downstream.
STATUS_BADGES = {"SUSPENDED", "DISCONTINUED", "WITHDRAWN"}


def _clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse_card(c):
    """One extracted card -> one cache item, or None if the card cannot be read
    for certain. Required: an NPC-shaped code, a supplier and a description."""
    if not isinstance(c, dict):
        return None
    npc = _clean(c.get("npc")) or _clean(c.get("npcClass"))
    supplier = _clean(c.get("supplier"))
    desc = _clean(c.get("name"))
    if not NPC_RE.match(npc) or not supplier or not desc:
        return None
    # Two different NPCs on one card (badge vs carousel class) means the DOM is
    # not what this parser was written against. Refuse rather than pick one.
    alt = _clean(c.get("npcClass"))
    if alt and alt != npc:
        return None
    status = ""
    for b in c.get("badges") or []:
        b = _clean(b)
        if b and b != npc:
            status = b.title()
            break
    pack = _clean(c.get("uom"))
    if pack.lower().startswith("sold in"):
        pack = pack[len("sold in"):].strip()
    return {"name": _clean(c.get("brand")), "supplier": supplier, "desc": desc,
            "npc": npc, "mpc": _clean(c.get("mpc")), "status": status,
            "pack": pack, "img": c.get("img") or ""}


def row_defects(item):
    """The fingerprints the old positional parser left on a cache item. Empty
    list = the row does not look misread. Used to pick rows to re-fetch and, by
    the tests, to prove a freshly parsed card never carries one."""
    out = []
    npc = (item.get("npc") or "").strip()
    mpc = (item.get("mpc") or "").strip()
    desc = (item.get("desc") or "").strip()
    name = (item.get("name") or "").strip()
    if npc and mpc == npc:
        out.append("mpc-is-npc")
    if name.upper() in STATUS_BADGES:
        out.append("badge-in-name")
    if desc and " " not in desc:
        out.append("single-token-desc")
    st = (item.get("status") or "").strip()
    if st and st.upper() not in STATUS_BADGES:
        out.append("junk-status")
    return out
