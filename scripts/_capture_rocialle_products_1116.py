"""Capture Rocialle Healthcare's product range, and clear its refusal.

WHY: data/supplier-products.json held Rocialle under "refusals", checked
05/09/2026, because rociallehealthcare.com exposed no readable catalogue. That
is the group's corporate site. The catalogue lives on the AcuteCare division's
own site, rocialleacutecare.com, which serves a WordPress REST `product` post
type (x-wp-total: 776 on 16/11/2026). Nothing here is inferred: every product
name and category is read from the company's own API this run, and the
grouping mirrors the company's own URL taxonomy (/product/<category>/<slug>).
"""
import json, io, html, re, glob

DOMAIN = 'rocialleacutecare.com'
NAME = 'Rocialle Healthcare'
TODAY = '2026-11-16'
# The API pages were fetched with curl to /tmp/rocfetch/p*.json this run
# (python has no DNS in this sandbox); x-wp-total reported 776.
FETCHED = '/tmp/rocfetch/p*.json'

rows = []
for f in sorted(glob.glob(FETCHED)):
    batch = json.load(open(f))
    if isinstance(batch, list):
        rows += batch
if len(rows) < 700:
    raise SystemExit('only %d rows read from %s — refusing to write a partial range' % (len(rows), FETCHED))

def clean(s):
    s = html.unescape(s or '')
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).replace('–', '-').strip()

def cat(link):
    m = re.search(r'/product/([^/]+)/', link or '')
    if not m: return 'Uncategorised'
    return m.group(1).replace('-', ' ').title()

seen, products = set(), []
for r in rows:
    if r.get('status') != 'publish': continue
    n = clean((r.get('title') or {}).get('rendered'))
    if not n: continue
    c = cat(r.get('link'))
    key = (n.lower(), c.lower())
    if key in seen: continue
    seen.add(key)
    products.append({'n': n, 'division': c, 'category': c})

counts = {}
for p in products: counts[p['category']] = counts.get(p['category'], 0) + 1
divisions = [{'name': k, 'products': v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]

SP = 'data/supplier-products.json'
sp = json.load(open(SP))
sp['refusals'].pop(NAME, None)
sp['suppliers'][NAME] = {
    'domain': DOMAIN,
    'verified': TODAY,
    'source': '%s product catalogue (WordPress REST API), read this run' % DOMAIN,
    'structureFrom': "the company's own product category taxonomy",
    'structure': "The company's own product URL categories on the AcuteCare site.",
    'filingRule': "Grouping MIRRORS the manufacturer's own filing. Where a product sits under a category that reads oddly clinically, that is where the company files it, and a rep searching the company's way will find it there.",
    'note': 'Captured from rocialleacutecare.com, the AcuteCare division site. The corporate site rociallehealthcare.com carries no catalogue, which is why this supplier was previously a refusal.',
    'divisions': divisions,
    'products': products,
}
with io.open(SP, 'w', encoding='utf-8') as f:
    json.dump(sp, f, ensure_ascii=False, separators=(',', ':'))

IDX = 'data/supplier-index.json'
idx = json.load(open(IDX))
rec = next(s for s in idx['suppliers'] if s.get('name') == NAME)
rec['products'] = [p['n'] for p in products]
with io.open(IDX, 'w', encoding='utf-8') as f:
    json.dump(idx, f, ensure_ascii=False, separators=(',', ':'))

print('captured %d published product(s) across %d categories' % (len(products), len(divisions)))
print('top: ' + ', '.join('%s (%d)' % (d['name'], d['products']) for d in divisions[:8]))
