"""Merge Rocialle Healthcare's company-awards records into its supplier-index
record. The two pipelines never met: supplier-index awards come only from the
Contracts Finder OCDS scan in build_supplier_index.py, so the record showed 1
award while data/company-awards.json held 25 for the same company, including
the All Wales Standard and Custom Procedure Packs award of 28/05/2026. Every
award written here carries the source, buyer and notice URL from
company-awards.json; nothing is inferred. Awards are append-only in
build_supplier_index.py, so these carry forward on later runs.
"""
import json, io

IDX = 'data/supplier-index.json'
AWD = 'data/company-awards.json'
NAME = 'Rocialle Healthcare'

awd = json.load(open(AWD))['companies'][NAME]
idx = json.load(open(IDX))

def money(a):
    v, c = a.get('valueAmount'), (a.get('valueCurrency') or 'GBP')
    if not v: return ''
    sym = '£' if c == 'GBP' else c + ' '
    return '%s%s' % (sym, format(int(v), ','))

rec = next(s for s in idx['suppliers'] if s.get('name') == NAME)
have = {(a.get('_id') or '').lower() for a in rec['awards']}
have |= {((a.get('title') or '') + '|' + (a.get('date') or '')).lower() for a in rec['awards']}
added = 0
for a in awd:
    key = ((a.get('title') or '') + '|' + (a.get('date') or '')).lower()
    if key in have: continue
    rec['awards'].append({
        '_id': (a.get('title') or '') + '|' + (a.get('date') or ''),
        'title': a.get('title') or '',
        'value': money(a),
        'buyer': a.get('buyer') or '',
        'date': a.get('date') or '',
        'url': a.get('url') or '',
        'source': a.get('source') or '',
        'autoDetected': True,
    })
    have.add(key); added += 1

rec['awards'].sort(key=lambda a: a.get('date') or '', reverse=True)
with io.open(IDX, 'w', encoding='utf-8') as f:
    json.dump(idx, f, ensure_ascii=False, separators=(',', ':'))
print('added %d award(s); Rocialle now holds %d' % (added, len(rec['awards'])))
