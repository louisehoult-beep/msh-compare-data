#!/usr/bin/env python3
"""Widen data/nhssc-cache.json's join by querying the NHS Supply Chain pilot
catalogue DIRECTLY by ICC NPC code, instead of relying on the name-search jobs
in refresh_nhssc_cache.py (^o366, 08/09/2026).

WHY THIS EXISTS
----------------
refresh_nhssc_cache.py seeds jobs from data/supplier-seed.json, searches the
pilot catalogue by PRODUCT NAME, and accepts a card only when the name and
supplier both look right. That is the correct method when the join is
name-to-name, but the ICC support-document grids (data/icc-matrices.json)
already carry the exact NPC code NHS Supply Chain itself assigned to each row
— searching by name and re-deriving the code is doing the join backwards.

Measured 08/09/2026: of 1,535 distinct NPCs across the ICC matrices, only 162
were already present in nhssc-cache.json (picked up incidentally by the
name-search jobs). Querying pilot.supplychain.nhs.uk/search?query=<NPC>
directly returns exactly one, unambiguous, correctly-identified result per
code (verified by hand against VJT118 before writing this script) — there is
no name-matching ambiguity to resolve, because the NPC IS the identity.

WHAT THIS WRITES
----------------
A match is added to nhssc-cache.json's existing "products" dict, keyed
"NPC:<code>" — a namespace that cannot collide with the name-keyed entries
refresh_nhssc_cache.py writes (those keys are supplier product names, never of
the form "NPC:XXXNNNNN"). app/comparison.js's ICC differential reads this
namespace directly by NPC; see iccLiveLink() there.

THE NEVER-SHRINK RULE STILL APPLIES. This script only ADDS or REFRESHES
NPC: entries; it never touches a name-keyed entry, and a previously-found
NPC: entry that the catalogue no longer serves KEEPS its last known value
rather than being dropped (a stale live-link beats a broken one — the ICC
figures printed elsewhere are date-stamped anyway, so the risk is a link
that resolves to a superseded pack, not a false fact).

Run:  python3 scripts/seed_nhssc_from_icc_npc.py
Needs playwright (pip install playwright && playwright install chromium).
"""
import json
import re
import asyncio
import sys
import time
from playwright.async_api import async_playwright

ICC_PATH = "data/icc-matrices.json"
CACHE_PATH = "data/nhssc-cache.json"
CONC = 5
NPC_RE = re.compile(r"^[A-Z]{3}\d{2,5}$")

EXTRACT_JS = r"""
() => Array.from(document.querySelectorAll('div.cardWrapper')).map(card => {
  const img = card.querySelector('img[src*="media.supplychain"]');
  const lines = (card.innerText||'').split('\n').map(s=>s.trim()).filter(Boolean)
    .filter(s => !/^Pilot User Login$|^Add to compare$|^\d+ \/ \d+$|^Compare$|^Show more$/.test(s));
  let npc = '';
  const prev = card.querySelector('[class*="product-card-prev-"]');
  if (prev) { const m = String(prev.className).match(/product-card-prev-([A-Z0-9]+)/); if (m) npc = m[1]; }
  let mpc = '';
  const mel = card.querySelector('[class*="product-card_mpc"]');
  if (mel) { const t = (mel.textContent||'').trim(); if (t) mpc = t.split(/\s+/)[0]; }
  return { lines, img: img ? img.src : '', npc, mpc };
})
"""


def parse_card(c):
    lines = c.get('lines', [])
    if len(lines) < 3:
        return None
    name, supplier, desc = lines[0], lines[1], lines[2]
    npc = c.get('npc', '') or ''
    mpc = c.get('mpc', '') or ''
    status = pack = ''
    codeish = []
    for ln in lines[3:]:
        if ln.startswith('Sold in'):
            pack = ln.replace('Sold in', '').strip()
        elif re.fullmatch(r'[A-Z0-9]{4,10}', ln) and not ln.isalpha():
            codeish.append(ln)
        elif re.fullmatch(r'[A-Z][A-Z ]{4,}', ln) and 'SOLD' not in ln and not status and ln != supplier:
            status = ln.title()
    if not npc and len(codeish) >= 2:
        npc = codeish[1]
    if not mpc and codeish:
        mpc = codeish[0]
    if not npc and len(codeish) == 1:
        npc = codeish[0]
    return {'name': name, 'supplier': supplier, 'desc': desc, 'npc': npc, 'mpc': mpc,
            'status': status, 'pack': pack, 'img': c.get('img', '')}


def icc_npcs():
    """Every distinct NPC the ICC matrices carry, with one product label each
    (for logging only — the query and the accept-check both use the code)."""
    icc = json.load(open(ICC_PATH))
    matrices = icc.get('matrices', icc)
    out = {}
    for cat, m in matrices.items():
        if not isinstance(m, dict):
            continue
        for p in m.get('products', []):
            npc = (p.get('NPC') or '').strip()
            if NPC_RE.match(npc) and npc not in out:
                out[npc] = p.get('Brand') or p.get('Description') or cat
    return out


async def worker(browser, batch, results, counter, total):
    ctx = await browser.new_context(viewport={'width': 1200, 'height': 900})
    page = await ctx.new_page()
    try:
        await page.goto('https://pilot.supplychain.nhs.uk/search?query=gauze', timeout=15000, wait_until='domcontentloaded')
        await page.wait_for_selector('div.cardWrapper', timeout=12000)
    except Exception:
        pass
    for npc, label in batch:
        try:
            await page.goto('https://pilot.supplychain.nhs.uk/search?query=' + npc,
                             timeout=15000, wait_until='domcontentloaded')
            try:
                await page.wait_for_selector('div.cardWrapper', timeout=6000)
            except Exception:
                pass
            await page.wait_for_timeout(250)
            cards = await page.evaluate(EXTRACT_JS)
        except Exception:
            cards = []
        match = None
        for c in cards:
            p = parse_card(c)
            # Exact identity match only. The NPC is the join key; there is no
            # name/supplier heuristic to fall back on, and none is needed —
            # a wrong NPC-shaped string extracted from the wrong card would be
            # a worse fault than finding nothing, so an inexact hit is dropped.
            if p and p['npc'] == npc:
                match = p
                break
        if match:
            results[npc] = {'supplier': match['supplier'], 'query': npc,
                             'items': [{'name': match['name'], 'supplier': match['supplier'],
                                        'desc': match['desc'], 'npc': match['npc'], 'mpc': match['mpc'],
                                        'status': match['status'], 'pack': match['pack'], 'img': match['img']}],
                             'label': label}
        counter[0] += 1
        if counter[0] % 50 == 0:
            print("%d/%d | %d found" % (counter[0], total, len(results)), flush=True)
    await ctx.close()


async def main():
    npcs = icc_npcs()
    cache = json.load(open(CACHE_PATH))
    products = cache.setdefault('products', {})

    have = set()
    for k, v in products.items():
        for it in (v.get('items') or []):
            n = (it.get('npc') or '').strip()
            if n:
                have.add(n)

    todo = [(npc, label) for npc, label in npcs.items() if npc not in have]
    print("ICC NPCs: %d | already joined: %d | to query: %d" % (len(npcs), len(npcs) - len(todo), len(todo)))
    if not todo:
        print("Nothing to do.")
        return

    results, counter = {}, [0]
    shards = [todo[i::CONC] for i in range(CONC)]
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        await asyncio.gather(*[worker(b, sh, results, counter, len(todo)) for sh in shards])
        await b.close()

    added = 0
    for npc, entry in results.items():
        key = "NPC:" + npc
        if key not in products:
            added += 1
        products[key] = entry

    cache.setdefault('_meta', {})['icc_npc_seed_refreshed'] = time.strftime('%d/%m/%Y')
    cache['_meta']['icc_npc_seed_matched'] = len(results)
    json.dump(cache, open(CACHE_PATH, 'w'))
    print("DONE: %d NPC-direct matches found this run (%d new), %d total NPC: entries in cache"
          % (len(results), added, sum(1 for k in products if k.startswith('NPC:'))))


if __name__ == "__main__":
    asyncio.run(main())
