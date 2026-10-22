#!/usr/bin/env python3
"""Build the per-company "What you should know" files for My Hub.

A member ticks the companies they work for on My Hub. The page then loads
data/company-key-info/<id>.json for each and shows, for that company: its top
news, the facts that bear on it, and the same for its closest competitors.

EVERY FACT IS DERIVED FROM A FILE THE HUB ALREADY PUBLISHES, never typed in
here, so it carries the same verification as the page it came from:
  data/supplier-index.json      company record: aliases, products, frameworks
  data/company-press.json      news stories attached to a company (5-test rule)
  data/speciality-news/*.json   Live Desk news; used only on a whole-word
                                match of one of the company's own aliases
  data/speciality-panels/*.json market share by brand, Drug Tariff moves,
                                discontinued products still on formularies,
                                local formulary positions (dermatology today;
                                other panels join as they gain those blocks)

Nothing here is confidential: no member data, no call notes, nothing from
outside the public repo's own data. A company with no fact in any source gets
no file and is not offered in the picker (an honest empty beats a thin card).

Competitors:
  * where the company owns a brand in a speciality's market-share table, its
    competitors are the owners of the other top brands (largest share first);
  * otherwise they are the suppliers sharing the most product categories and
    a speciality with it, at least one of each.

Run from the repo root:  python3 scripts/build_company_key_info.py
Tests: test_company_key_info.py
"""
import glob
import json
import os
import re
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'company-key-info')
TODAY = date.fromisoformat(os.environ.get('MSH_TODAY') or date.today().isoformat())

GENERIC = {'ltd', 'limited', 'plc', 'uk', 'the', 'group', 'healthcare', 'medical', 'pharma',
           'pharmaceuticals', 'health', 'international', 'and', 'solutions', 'systems', 'services'}
NEWS_MAX_AGE = 120      # days a news item stays a headline
MAX_HEADLINES = 4
MAX_FACTS = 10
MAX_COMPETITORS = 4
MAX_COMP_FACTS = 3
MIN_COMP_SHARE = 1.0    # a competitor brand must hold at least this % of the market


def load(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return json.load(f)


def slug(s):
    # 80 characters is the longest id a member's account accepts
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:80].rstrip('-')


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip()


def parse_iso(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def parse_end(dates):
    """End date from a printed range such as '12 March 2024 to 11 March 2028'."""
    m = re.search(r'to\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*$', str(dates or ''))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), '%d %B %Y').date()
    except ValueError:
        return None


def fmt(d):
    return d.strftime('%-d %B %Y')


def alias_terms(sup):
    """Whole-word match terms from the company's own recorded aliases."""
    out = set()
    for a in sup.get('aliases') or []:
        n = norm(a)
        if len(n) < 4:
            continue
        if all(w in GENERIC for w in n.split()):
            continue
        out.add(n)
    return out


def mentions(text, terms):
    t = ' ' + norm(text) + ' '
    return any((' ' + term + ' ') in t for term in terms)


def fact(kind, title, text, url=None, source=None, when=None):
    f = {'k': kind, 't': title, 'x': text}
    if url:
        f['u'] = url
    if source:
        f['s'] = source
    if when:
        f['d'] = when
    return f


def build():
    index = load('data/supplier-index.json')['suppliers']
    press = load('data/company-press.json').get('suppliers') or {}
    news = {}
    for p in glob.glob(os.path.join(ROOT, 'data', 'speciality-news', '*.json')):
        d = json.load(open(p, encoding='utf-8'))
        news[os.path.basename(p)[:-5]] = d.get('items') or []
    panels = {}
    for p in glob.glob(os.path.join(ROOT, 'data', 'speciality-panels', '*.json')):
        panels[os.path.basename(p)[:-5]] = json.load(open(p, encoding='utf-8'))

    sups = []
    for s in index:
        sups.append({'id': slug(s['name']), 'name': s['name'], 'rec': s, 'terms': alias_terms(s),
                     'specs': s.get('specialities') or [], 'cats': {x['category'] for x in s.get('productCategories') or [] if isinstance(x, dict) and x.get('category')}})
    seen_ids = {}
    for s in sups:
        n = seen_ids.get(s['id'], 0) + 1
        seen_ids[s['id']] = n
        if n > 1:
            s['id'] = s['id'][:76].rstrip('-') + '-' + str(n)
    by_id = {s['id']: s for s in sups}

    # ---- brand ownership, per market-share table ----
    brand_owner = {}      # (panel, brand) -> company id
    for pid, panel in panels.items():
        for mk in (panel.get('marketShare') or {}).get('markets') or []:
            for b in (mk.get('primary') or {}).get('brands') or []:
                if b.get('generic'):
                    continue
                bn = norm(b['brand'])
                owners = [s for s in sups if bn in s['terms'] or any(norm(p).startswith(bn + ' ') or norm(p) == bn
                                                                      for p in s['rec'].get('products') or [])]
                if len(owners) == 1:
                    brand_owner[(pid, mk['id'], b['brand'])] = owners[0]['id']

    for (pid, mid, brand), owner in brand_owner.items():
        by_id[owner]['terms'].add(norm(brand))
        by_id[owner].setdefault('brands', set()).add(norm(brand))

    def own_facts(s, with_news=True):
        rec, facts = s['rec'], []
        # news attached by the company-press rules
        for it in (press.get(rec['name']) or {}).get('items') or []:
            d = parse_iso(it.get('date'))
            if not d or (TODAY - d).days > NEWS_MAX_AGE:
                continue
            src = (it.get('sources') or [{}])[0]
            if not str(src.get('url', '')).startswith('http'):
                continue
            facts.append(fact('news', it['headline'], 'Reported by ' + (src.get('publisher') or 'the press') + '.',
                              src['url'], src.get('publisher'), d.isoformat()))
        # Live Desk news that names the company by its own alias
        if with_news:
            for pid, items in news.items():
                for it in items:
                    d = parse_iso(it.get('published'))
                    if not d or (TODAY - d).days > NEWS_MAX_AGE or not str(it.get('link', '')).startswith('http'):
                        continue
                    if mentions(it.get('title', '') + ' ' + it.get('summary', ''), s['terms']):
                        facts.append(fact('news', it['title'], it.get('summary', ''), it['link'],
                                          it.get('source'), d.isoformat()))
        # frameworks and their end dates
        for fw in rec.get('frameworks') or []:
            end = parse_end(fw.get('dates'))
            if end and end < TODAY:
                continue
            days = (end - TODAY).days if end else None
            soon = days is not None and days <= 365
            facts.append(fact('framework',
                              ('Framework ending ' + fmt(end) + ': ' if end else 'Framework: ') + fw['name'],
                              fw.get('note', ''), fw.get('url'), 'NHS Supply Chain' if fw.get('source') == 'nhssc-brief' else 'Hub supplier record',
                              end.isoformat() if soon else None))
            facts[-1]['_cat'] = fw.get('category')
        # market share, price moves, discontinued lines, formulary positions
        for pid, panel in panels.items():
            for mk in (panel.get('marketShare') or {}).get('markets') or []:
                pr = mk.get('primary') or {}
                for rank, b in enumerate(pr.get('brands') or [], 1):
                    if brand_owner.get((pid, mk['id'], b['brand'])) != s['id']:
                        continue
                    per = pr.get('latestPeriod', '')
                    when = per[:4] + '-' + per[4:6] + '-01' if len(per) == 6 else None
                    facts.append(fact('share', b['brand'] + ': ' + str(b['share']) + '% of ' + mk['label'].split(':')[0].lower()
                                      + ' prescribing items, England GP' + (', ' + datetime.strptime(per, '%Y%m').strftime('%B %Y') if len(per) == 6 else ''),
                                      'Rank ' + str(rank) + ' of ' + str(pr.get('brandCount')) + ' brands in GP prescribing'
                                      + ('.' if b.get('yoy') is None else '; ' + ('up ' if b['yoy'] >= 0 else 'down ') + str(abs(b['yoy'])) + '% on a year earlier.'),
                                      (panel.get('marketShare') or {}).get('gpSourceUrl'), 'NHSBSA English Prescribing Dataset', when))
                    facts[-1]['_mk'] = (pid, mk['id'])
                    facts[-1]['_sh'] = b['share']
            mv = panel.get('drugTariffMoves') or {}
            mine = [m for m in mv.get('moves') or [] if norm(m['supplier']) in {norm(rec['name'])} or
                    mentions(m['supplier'], s['terms'])]
            if mine:
                ups = sum(1 for m in mine if m['now'] > m['was'])
                facts.append(fact('tariff', str(len(mine)) + ' Drug Tariff price lines moved, ' + datetime.strptime(mv['currentMonth'], '%Y-%m').strftime('%B %Y'),
                                  str(ups) + ' up, ' + str(len(mine) - ups) + ' down, against ' + mv['previousMonth'] + '. '
                                  + mine[0]['product'] + ' ' + mine[0]['qty'] + ' ' + mine[0]['uom'] + ' went from £'
                                  + format(mine[0]['was'], '.2f') + ' to £' + format(mine[0]['now'], '.2f') + '.',
                                  mv.get('sourcePage'), 'NHSBSA Drug Tariff Part IX', mv.get('dataAsOf')))
                facts[-1]['_pid'] = pid
            for dp in (panel.get('discontinuedOnFormulary') or {}).get('products') or []:
                if mentions(dp['name'], s['terms']) or any(norm(dp['name']).startswith(norm(p.split('(')[0]).strip()) for p in rec.get('products') or [] if len(norm(p)) > 5):
                    c = dp.get('counts') or {}
                    facts.append(fact('discontinued', dp['name'] + ' is discontinued but still on ' + str(dp['formularies']) + ' formularies',
                                      str(c.get('recommended', 0)) + ' still recommend it. The NHS Dictionary of Medicines and Devices (dm+d) records it as '
                                      + dp['dmd']['status'].lower() + '.', dp['dmd'].get('url'), 'dm+d browser', dp['dmd'].get('readOn')))
                    facts[-1]['_pid'] = pid
            for li in panel.get('localIntel') or []:
                if li.get('group') == 'formulary' and mentions(li.get('fact', ''), s['terms']) and str(li.get('url', '')).startswith('http'):
                    facts.append(fact('formulary', li['org'] + ': ' + li['title'], li['fact'], li['url'], li['org'], li.get('verifiedOn')))
        return facts

    def rank(f):
        order = {'news': 0, 'tariff': 1, 'discontinued': 2, 'share': 3, 'framework': 4, 'formulary': 5}
        d = parse_iso(f.get('d'))
        return (order.get(f['k'], 9), -(d.toordinal() if d else 0))

    def tidy(facts):
        seen, out = set(), []
        for f in facts:
            key = (f['k'], norm(f['t']))
            if key in seen:
                continue
            seen.add(key)
            if len(f.get('x', '')) > 320:
                cut = f['x'][:320]
                f['x'] = cut[:cut.rfind(' ')].rstrip(' ,;:') + '...'
            out.append(f)
        return out

    def clean(f):
        return {k: v for k, v in f.items() if not k.startswith('_')}

    result, picker = {}, []
    facts_by_id = {s['id']: tidy(own_facts(s)) for s in sups}

    for s in sups:
        f = facts_by_id[s['id']]
        if not f:
            continue
        f.sort(key=rank)
        heads = [x for x in f if x['k'] in ('news', 'tariff', 'discontinued') or (x['k'] == 'framework' and x.get('d'))][:MAX_HEADLINES]
        # competitors
        comps = []
        mine = [(k, v) for k, v in brand_owner.items() if v == s['id']]
        if mine:
            seen = {}
            for (pid, mid, brand), owner in brand_owner.items():
                if owner == s['id'] or owner in seen:
                    continue
                mk = next(m for m in panels[pid]['marketShare']['markets'] if m['id'] == mid)
                brands = {b['brand']: b['share'] for b in mk['primary']['brands']}
                if brands.get(brand, 0) < MIN_COMP_SHARE:
                    continue
                own = [brands[b] for (p2, m2, b), o in mine if p2 == pid and m2 == mid and b in brands]
                if not own:
                    continue
                mybrand = max(own)
                seen[owner] = (-brands[brand], brand, pid)
            for owner, (gap, brand, pid) in sorted(seen.items(), key=lambda kv: kv[1][0]):
                comps.append((owner, 'Owns ' + brand + ', a leading brand in the same market'))
        if len(comps) < MAX_COMPETITORS:
            have = {c[0] for c in comps}
            scored = []
            for o in sups:
                if o['id'] == s['id'] or o['id'] in have or not facts_by_id[o['id']]:
                    continue
                shared_c = len(s['cats'] & o['cats'])
                shared_s = len(set(s['specs']) & set(o['specs']))
                if shared_c and shared_s:
                    scored.append((shared_c * 10 + shared_s, o['id'], shared_c))
            for sc, oid, shared_c in sorted(scored, reverse=True)[:MAX_COMPETITORS - len(comps)]:
                comps.append((oid, 'Supplies ' + str(shared_c) + ' of the same product categor' + ('y' if shared_c == 1 else 'ies')))
        comp_out = []
        own_mk = {(k[0], k[1]) for k, v in mine}
        own_pid = {k[0] for k, v in mine}
        for oid, why in comps[:MAX_COMPETITORS]:
            shared = s['cats'] & by_id[oid]['cats']
            of = [x for x in sorted(facts_by_id[oid], key=rank)
                  if (x['k'] == 'share' and x.get('_sh', 0) >= MIN_COMP_SHARE and (not mine or x.get('_mk') in own_mk))
                  or (x['k'] in ('tariff', 'discontinued') and (not mine or x.get('_pid') in own_pid))
                  or (x['k'] == 'news' and (not mine or mentions(x['t'], by_id[oid].get('brands', set()))))
                  or (x['k'] == 'framework' and x.get('_cat') in shared)][:MAX_COMP_FACTS]
            of = [clean(x) for x in of]
            if of:
                comp_out.append({'id': oid, 'n': by_id[oid]['name'], 'why': why, 'f': of})
        result[s['id']] = {'id': s['id'], 'n': s['name'], 'specs': s['specs'], 'built': TODAY.isoformat(),
                           'head': [clean(x) for x in heads], 'f': [clean(x) for x in f[:MAX_FACTS]], 'comp': comp_out}
        picker.append({'id': s['id'], 'n': s['name'], 'a': sorted(s['terms'])[:4], 'sp': s['specs'][:2]})
    picker.sort(key=lambda p: p['n'].lower())
    return result, picker


def _dump(path, d):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(',', ':'))


def _same_but_built(path, d):
    try:
        with open(path, encoding='utf-8') as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        return None
    a = {k: v for k, v in old.items() if k != 'built'}
    b = {k: v for k, v in d.items() if k != 'built'}
    return old if a == b else None


def write(result, picker):
    """Write only what changed, so the daily rebuild commits real changes, not
    1,200 files re-stamped with a new date."""
    os.makedirs(OUT, exist_ok=True)
    keep = {cid + '.json' for cid in result} | {'index.json'}
    for f in glob.glob(os.path.join(OUT, '*.json')):
        if os.path.basename(f) not in keep:
            os.remove(f)
    for cid, d in result.items():
        path = os.path.join(OUT, cid + '.json')
        old = _same_but_built(path, d)
        if old is not None:
            continue
        _dump(path, d)
    idx = {'built': TODAY.isoformat(), 'companies': picker}
    path = os.path.join(OUT, 'index.json')
    if _same_but_built(path, idx) is None:
        _dump(path, idx)


if __name__ == '__main__':
    r, p = build()
    write(r, p)
    print(len(p), 'companies with content')
    sys.exit(0)
