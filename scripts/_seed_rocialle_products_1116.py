"""Put Rocialle's captured product range into the human-owned seed.

16/11/2026. The capture on 16/11 wrote the 758 names straight into
data/supplier-index.json, and that afternoon's "Daily refresh" rebuild
regenerated the index and dropped them back to zero (awards survived only
because the award list is append-only). The durable route for a
human-owned field is data/supplier-seed.json: mergeSuppliers() in
app/company-report.js copies seed `products` over the index copy on every
load, and the nightly rebuild never touches the seed.

Source of the names: data/supplier-products.json, written by
_capture_rocialle_products_1116.py from rocialleacutecare.com's own
WordPress product API. Nothing is inferred here -- this only moves names
already captured and verified into the file that keeps them.
"""
import json

SEED = 'data/supplier-seed.json'
SP = 'data/supplier-products.json'
NAME = 'Rocialle Healthcare'

sp = json.load(open(SP))
entry = sp['suppliers'][NAME]
names = []
seen = set()
for p in entry['products']:
    n = p['n'] if isinstance(p, dict) else p
    k = n.lower()
    if n and k not in seen:
        seen.add(k)
        names.append(n)

if len(names) < 700:
    raise SystemExit('only %d name(s) in %s -- refusing to seed a partial range' % (len(names), SP))

seed = json.load(open(SEED))
rec = next(s for s in seed['suppliers'] if s.get('name') == NAME)
before = len(rec.get('products') or [])
rec['products'] = names

with open(SEED, 'w') as f:
    json.dump(seed, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('seed %s: products %d -> %d' % (NAME, before, len(names)))
