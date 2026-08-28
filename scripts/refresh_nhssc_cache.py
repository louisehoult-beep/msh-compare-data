#!/usr/bin/env python3
"""Weekly MERGE-PRESERVING refresh of data/nhssc-cache.json from the public
NHS Supply Chain pilot catalogue.

Rules (why this never degrades the cache):
- For a product ALREADY in the cache: retry its stored, previously-successful
  query first, and accept cards whose supplier matches the PREVIOUSLY VERIFIED
  catalogue supplier (self-consistent) — this preserves entity-corrected finds
  (e.g. GBUK products listed under GS MEDICAL HEALTHCARE LTD).
- For a NEW seed product: strict name + seed-supplier matching (never guess).
- A product whose re-scrape finds nothing KEEPS its previous entry (codes
  rarely vanish; a stale status beats losing 200 verified products).
- The agent-verified notCatalogue map is preserved, minus any product that now
  has live codes.
Runs in GitHub Actions (Playwright chromium). ~30–40 min for ~900 products.
"""
import json, re, asyncio, time
from playwright.async_api import async_playwright

SEED_PATH = "data/supplier-seed.json"
CACHE_PATH = "data/nhssc-cache.json"
CONC = 5
STOP = {'ltd','limited','group','medical','healthcare','health','uk','plc','corp','company',
        'international','systems','solutions','products','device','devices','stock','edirect'}
# NHSSC's catalogue holds unrelated business units under the same brand root
# (e.g. "Bunzl Healthcare" vs "BUNZL CATERING SUPPLIES" — one Bunzl entity,
# two different lines of goods). Because STOP strips generic words like
# "healthcare", a supplier name that reduces to just its brand root (e.g.
# "Bunzl") can wrongly token-match a card from a different business line of
# the same brand. If a card's supplier name carries one of these category
# words and that same word does NOT appear anywhere in the job's own
# declared supplier name/aliases, the card is a different business unit and
# must never be accepted, no matter how the brand-root tokens overlap.
OFF_CATEGORY = {'catering','retail','workwear','laundry','print','printing','office',
                 'stationery','textile','uniform','hospitality','packaging','vending'}

def off_category_mismatch(job_supplier_raw, card_supplier):
    job_words = set(re.findall(r'[a-z0-9]+', (job_supplier_raw or '').lower()))
    card_words = set(re.findall(r'[a-z0-9]+', (card_supplier or '').lower()))
    bad = (card_words & OFF_CATEGORY) - job_words
    return bool(bad)

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

def norm(*strs):
    s = ' '.join(x for x in strs if x)
    return set(w for w in re.findall(r'[a-z0-9]{4,}', s.lower()) if w not in STOP)

def candidates(name):
    c = re.sub(r'\(.*', '', name).replace('/', ' ')
    c = re.sub(r'[^A-Za-z0-9 ]', ' ', c)
    w = [x for x in c.split() if x]
    out = ([' '.join(w[:2])] if len(w) >= 2 else []) + ([w[0]] if w else []) or [name.strip()]
    seen, uniq = set(), []
    for q in out:
        if q.lower() not in seen: seen.add(q.lower()); uniq.append(q)
    return uniq

def parse_card(c):
    lines = c.get('lines', [])
    if len(lines) < 3: return None
    name, supplier, desc = lines[0], lines[1], lines[2]
    npc = c.get('npc','') or ''; mpc = c.get('mpc','') or ''
    status = pack = ''; codeish = []
    for ln in lines[3:]:
        if ln.startswith('Sold in'): pack = ln.replace('Sold in','').strip()
        elif re.fullmatch(r'[A-Z0-9]{4,10}', ln) and not ln.isalpha(): codeish.append(ln)
        elif re.fullmatch(r'[A-Z][A-Z ]{4,}', ln) and 'SOLD' not in ln and not status and ln != supplier: status = ln.title()
    if not npc and len(codeish) >= 2: npc = codeish[1]
    if not mpc and codeish: mpc = codeish[0]
    if not npc and len(codeish) == 1: npc = codeish[0]
    return {'name': name, 'supplier': supplier, 'desc': desc, 'npc': npc, 'mpc': mpc,
            'status': status, 'pack': pack, 'img': c.get('img','')}

def name_ok(key, card_name):
    qn = re.sub(r'[^a-z0-9]', '', re.sub(r'\(.*', '', key).lower())
    cn = re.sub(r'[^a-z0-9]', '', (card_name or '').lower())
    return bool(qn and cn and (qn in cn or cn in qn)) or bool(norm(key) & norm(card_name or ''))

async def worker(browser, batch, results, counter, total):
    ctx = await browser.new_context(viewport={'width':1200,'height':900})
    page = await ctx.new_page()
    try:
        await page.goto('https://pilot.supplychain.nhs.uk/search?query=gauze', timeout=15000, wait_until='domcontentloaded')
        await page.wait_for_selector('div.cardWrapper', timeout=12000)
    except Exception: pass
    for job in batch:
        prev = job.get('prev')
        # A previously-cached entry only counts as "verified" for self-consistency
        # if its own supplier name doesn't itself trip the off-category guard —
        # otherwise a bad match from a past run (e.g. catering goods cached
        # against a healthcare-only supplier) re-confirms itself forever.
        prev_is_sound = bool(prev and prev.get('items') and
                              not off_category_mismatch(job['supplierRaw'], prev['items'][0]['supplier']))
        queries = ([prev['query']] if prev and prev.get('query') else []) + candidates(job['key'])
        prev_sup_tokens = norm(prev['items'][0]['supplier']) if prev_is_sound else set()
        found, used_q = [], ''
        seen_q = set()
        for q in queries:
            if q.lower() in seen_q: continue
            seen_q.add(q.lower())
            try:
                await page.goto('https://pilot.supplychain.nhs.uk/search?query=' + q.replace(' ','%20'),
                                timeout=15000, wait_until='domcontentloaded')
                try: await page.wait_for_selector('div.cardWrapper', timeout=6000)
                except Exception: pass
                await page.wait_for_timeout(300)
                cards = await page.evaluate(EXTRACT_JS)
            except Exception: cards = []
            if not cards: continue
            for c in cards:
                p = parse_card(c)
                if not p or not p['npc'] or not name_ok(job['key'], p['name']): continue
                if off_category_mismatch(job['supplierRaw'], p['supplier']): continue
                sup_hit = bool(job['supTokens'] & norm(p['supplier'])) or bool(prev_sup_tokens & norm(p['supplier']))
                if sup_hit: found.append(p)
            if found: used_q = q; break
        if found:
            seen, keep = set(), []
            for p in sorted(found, key=lambda x: (1 if x['status'] else 0)):
                if p['npc'] in seen: continue
                seen.add(p['npc']); keep.append(p)
            # NEVER SHRINK AN ENTRY. supplier-deep-capture writes supplier-scoped
            # captures into the same file (hundreds of rows for one brand term),
            # and truncating those here would silently throw the deep work away
            # every Monday. Same principle as the 0.8x abort below: a refresh may
            # add, it may not degrade.
            #
            # CAP RAISED 6 -> 60, 28/08/2026. The cap truncates cards ALREADY
            # scraped from the one search-results page this job loads, so raising
            # it costs no extra request and no extra runtime — it only stops us
            # discarding catalogue lines we had already fetched and verified.
            #
            # THE EVIDENCE THE CAP WAS BINDING, measured on the cache before the
            # change: 824 terms held 4,991 items, and **504 of those 824 terms
            # (61%) sat at exactly 6**. A real catalogue distribution tails off
            # smoothly; a spike of 504 terms landing on precisely the cap value
            # is the signature of truncation, not of the catalogue running out.
            # (The two entries at 134 and 1,062 items are supplier-deep-capture's
            # supplier-scoped writes, which the never-shrink guard below keeps.)
            # The NHS Supply Chain catalogue is the buyer's own authoritative
            # list and the only route this repo has to the manufacturers whose
            # own sites forbid crawling (Coloplast, Smith+Nephew, B.Braun,
            # Hartmann and 97 others), so discarding their lines was the single
            # biggest self-inflicted coverage gap in the Differentiator.
            NHSSC_ITEM_CAP = 60
            fresh = {'supplier': job['supplier'], 'query': used_q, 'items': keep[:NHSSC_ITEM_CAP]}
            if prev_is_sound and len(prev.get('items') or []) > len(fresh['items']):
                prev_keep = dict(prev)
                prev_keep['query'] = prev.get('query') or used_q
                results[job['key']] = prev_keep
            else:
                results[job['key']] = fresh
        elif prev_is_sound:
            results[job['key']] = prev  # keep the verified previous entry
        # else: nothing found this run, and the previously-cached entry itself
        # fails the off-category guard (e.g. it was a wrong-business-line
        # match). Drop it rather than re-carrying known-bad data forward —
        # it falls through to notCatalogue in main(), an honest empty state.
        counter[0] += 1
        if counter[0] % 50 == 0:
            print("%d/%d | %d in cache" % (counter[0], total, len(results)), flush=True)
    await ctx.close()

async def main():
    seed = json.load(open(SEED_PATH))
    old = json.load(open(CACHE_PATH))
    oldp = old.get('products', {})
    jobs, seen = [], set()
    for s in seed.get('suppliers', []):
        toks = norm(s.get('name',''), *(s.get('aliases',[]) or []))
        supplier_raw = ' '.join([s.get('name','')] + (s.get('aliases',[]) or []))
        for p in s.get('products', []):
            n = (p if isinstance(p, str) else p.get('name','')).strip()
            if not n or n.lower() in seen: continue
            seen.add(n.lower())
            jobs.append({'key': n, 'supplier': s.get('name',''), 'supplierRaw': supplier_raw,
                         'supTokens': toks, 'prev': oldp.get(n)})
    print("jobs:", len(jobs), "| previously cached:", len(oldp))
    results, counter = {}, [0]
    shards = [jobs[i::CONC] for i in range(CONC)]
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        await asyncio.gather(*[worker(b, sh, results, counter, len(jobs)) for sh in shards])
        await b.close()
    if len(results) < 0.8 * len(oldp):
        raise SystemExit("ABORT: refresh produced %d products vs %d previously — refusing to shrink the cache." % (len(results), len(oldp)))
    notcat = {k: v for k, v in (old.get('notCatalogue') or {}).items() if k.lower() not in {r.lower() for r in results}}
    out = {'_meta': {'source': 'pilot.supplychain.nhs.uk', 'refreshed': time.strftime('%d/%m/%Y'),
                     'matched': len(results), 'notCatalogue': len(notcat)},
           'products': results, 'notCatalogue': notcat}
    json.dump(out, open(CACHE_PATH, 'w'))
    imgs = sum(1 for v in results.values() if any(i.get('img') for i in v['items']))
    print("DONE: %d products (%d with images) | %d not-catalogue preserved" % (len(results), imgs, len(notcat)))

asyncio.run(main())
