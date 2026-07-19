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
        queries = ([prev['query']] if prev and prev.get('query') else []) + candidates(job['key'])
        prev_sup_tokens = norm(prev['items'][0]['supplier']) if prev and prev.get('items') else set()
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
                sup_hit = bool(job['supTokens'] & norm(p['supplier'])) or bool(prev_sup_tokens & norm(p['supplier']))
                if sup_hit: found.append(p)
            if found: used_q = q; break
        if found:
            seen, keep = set(), []
            for p in sorted(found, key=lambda x: (1 if x['status'] else 0)):
                if p['npc'] in seen: continue
                seen.add(p['npc']); keep.append(p)
            results[job['key']] = {'supplier': job['supplier'], 'query': used_q, 'items': keep[:6]}
        elif prev:
            results[job['key']] = prev  # keep the verified previous entry
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
        for p in s.get('products', []):
            n = (p if isinstance(p, str) else p.get('name','')).strip()
            if not n or n.lower() in seen: continue
            seen.add(n.lower())
            jobs.append({'key': n, 'supplier': s.get('name',''), 'supTokens': toks, 'prev': oldp.get(n)})
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
