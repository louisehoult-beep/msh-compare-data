#!/usr/bin/env python3
"""Sofia, Insight Analyst: build data/sofia-insights.json from sources read TODAY.

Nothing is carried over from yesterday. An item is written only if its source was fetched in this
run and the check below passed:
  standing item  every quote in config/sofia-standing.json found word for word on its page, and
                 every number and date in the item's own words present in those quotes
  watched page   the owner's own change note, with the owner's own date, from the GOV.UK content API
  new document   the document itself re-opened and its title and date confirmed
Anything that fails is held (state/sofia-held.json) and never shown.

Two machines run this. www.england.nhs.uk answers GitHub's runners with an empty HTTP 202, so
ops/launchagents/sofia-insights-mac.sh reads it from the Mac each morning. A later run that
cannot read that site keeps an item ONLY if it was verified earlier the same London day (and,
for a standing item, its words are unchanged). A page that was read and no longer carries the
quote is held, never kept.

Standard library only, plus the pdftotext command for the one PDF source (poppler-utils).
Usage: python3 scripts/refresh_sofia_insights.py [--out data/sofia-insights.json]
"""
import argparse, datetime, html, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {'User-Agent': 'Mozilla/5.0 (compatible; HubSourceCheck/1.0)'}
GOVUK = 'https://www.gov.uk/'
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('Europe/London')
except Exception:  # pragma: no cover
    TZ = None
NOW = datetime.datetime.now(TZ)
TODAY = NOW.date()

_cache = {}
_unreadable = {}


class Unreadable(Exception):
    """The site did not give this machine the page: not the same as the page having changed."""


def host(url):
    return urllib.parse.urlparse(url).netloc


def fetch(url, binary=False):
    if url in _unreadable:
        raise Unreadable(_unreadable[url])
    if url not in _cache:
        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                    status, body = r.status, r.read()
                if status != 200 or not body:
                    # not retried: do not keep asking a site that is declining this machine
                    _unreadable[url] = 'page not readable from this machine (HTTP %s, %d bytes): %s' % (status, len(body), url)
                    raise Unreadable(_unreadable[url])
                _cache[url] = body
                break
            except Unreadable:
                raise
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise last
    return _cache[url] if binary else _cache[url].decode('utf-8', 'replace')


def norm(s):
    s = html.unescape(s)
    for a, b in (('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('–', '-'),
                 ('—', '-'), ('‑', '-'), ('\xa0', ' '), ('\xad', ''), ('​', '')):
        s = s.replace(a, b)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r' ([,.;:)])', r'\1', s)
    return s.replace('( ', '(').strip()


def strip_tags(s):
    s = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', s)
    s = re.sub(r'(?i)</?(p|li|h\d|tr|div|td|th|br|ul|ol|table|section)\b[^>]*>', ' ', s)
    return html.unescape(re.sub(r'<[^>]+>', '', s))


def content_api(path):
    return json.loads(fetch(GOVUK + 'api/content/' + path))


def page_text(url, pdf=False):
    if pdf:
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(fetch(url, binary=True))
            f.flush()
            out = subprocess.run(['pdftotext', f.name, '-'], capture_output=True, check=True, timeout=60)
        return norm(out.stdout.decode('utf-8', 'replace'))
    if url.startswith(GOVUK):
        j = content_api(url[len(GOVUK):])
        d = j.get('details', {})
        parts = [j.get('title', ''), j.get('description') or '']
        for key in ('body', 'introduction', 'final_outcome_detail'):
            v = d.get(key)
            if isinstance(v, list):
                v = ' '.join(x.get('content', '') for x in v)
            if isinstance(v, str):
                parts.append(v)
        for p in d.get('parts', []) or []:
            v = p.get('body')
            if isinstance(v, list):
                v = ' '.join(x.get('content', '') for x in v)
            parts.append(v or '')
        return norm(strip_tags(' '.join(parts)))
    return norm(strip_tags(fetch(url)))


MONTHS = 'January February March April May June July August September October November December'.split()


def datewords(text):
    """17th May 2026 and 9 June, 2026 read the same as 17 May 2026 and 9 June 2026."""
    m = '|'.join(MONTHS)
    text = re.sub(r'(\d{1,2})(?:st|nd|rd|th)? (%s),? (\d{4})' % m, r'\1 \2 \3', text)
    return text


def figures(text):
    """The numbers and dates an item states, in a comparable form."""
    t = datewords(norm(text)).replace('£1 million', '£1m').replace('£5 million', '£5m').replace(' million', 'm')
    return set(re.findall(r'£\d[\d,.]*m?|\d{1,2} (?:%s) \d{4}|\d{4}/\d{2}|\d+%%' % '|'.join(MONTHS), t))


def check_standing(item):
    quotes, sources = [], []
    for ev in item['evidence']:
        text = page_text(ev['url'], ev.get('pdf', False))
        for q in ev['quotes']:
            if norm(q) not in text:
                raise ValueError('quote not found on %s: %s' % (ev['url'], q[:90]))
            quotes.append(q)
        if ev.get('published'):
            j = content_api(ev['url'][len(GOVUK):])
            stamps = [c['public_timestamp'][:10] for c in j.get('details', {}).get('change_history', [])]
            stamps.append((j.get('first_published_at') or '')[:10])
            if ev['published'] not in stamps:
                raise ValueError('publication date %s not on the owner record of %s' % (ev['published'], ev['url']))
            d = datetime.date.fromisoformat(ev['published'])
            quotes.append('%d %s %d' % (d.day, MONTHS[d.month - 1], d.year))
        sources.append({'name': ev['name'], 'url': ev['url']})
    have = figures(' '.join(quotes))
    said = figures(' '.join([item['title'], item['summary'], item['meaning']]))
    missing = sorted(said - have)
    if missing:
        raise ValueError('stated but not quoted from a source: %s' % ', '.join(missing))
    for key in ('date', 'deadline'):
        if item.get(key):
            d = datetime.date.fromisoformat(item[key])
            full = '%d %s %d' % (d.day, MONTHS[d.month - 1], d.year)
            if not re.search(r'(?<!\d)' + full, datewords(norm(' '.join(quotes)))):
                raise ValueError('%s %s is not in any quote' % (key, full))
    out = {k: item[k] for k in ('id', 'area', 'title', 'summary', 'meaning', 'date', 'deadline', 'deadlineLabel') if item.get(k)}
    out.update(type='standing', sources=sources, verifiedOn=TODAY.isoformat())
    return out


def local_date(stamp):
    d = datetime.datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    return d.astimezone(TZ).date() if TZ else d.date()


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:70]


def plain(s):
    s = norm(s)
    s = re.sub(r'\s+-\s+', ', ', s)
    return s if len(s) <= 320 else s[:317].rsplit(' ', 1)[0] + '...'


MINOR = re.compile(r'(?i)(minor|typo|corrected a (typo|link)|fixed (a )?(broken )?link|added (a )?welsh)')


def watched(cfg, since, held):
    out = []
    for w in cfg['watched']:
        try:
            j = content_api(w['path'])
            notes = [c for c in j.get('details', {}).get('change_history', []) if local_date(c['public_timestamp']) >= since]
            real = []
            for c in sorted(notes, key=lambda c: c['public_timestamp'], reverse=True):
                day = local_date(c['public_timestamp'])
                note = plain(c['note'])
                if day <= TODAY and not MINOR.match(note):
                    real.append((day, note))
            if real:
                day, note = real[0]
                earlier = sorted({d for d, _ in real[1:] if d != day}, reverse=True)
                out.append({'id': 'w-%s-%s' % (slug(w['path'].split('/')[-1]), day.isoformat()), 'type': 'new',
                            'area': w['area'], 'title': plain(j['title']), 'summary': note, 'quoted': True,
                            'meaning': w['meaning'], 'date': day.isoformat(),
                            'earlier': [d.isoformat() for d in earlier],
                            'sources': [{'name': w['name'], 'url': GOVUK + w['path']}], 'verifiedOn': TODAY.isoformat()})
        except Exception as e:
            held.append({'id': w['path'], 'reason': str(e)[:300]})
    return out


def searched(cfg, since, held):
    out, seen = [], set()
    watched_links = {'/' + w['path'] for w in cfg['watched']}
    for s in cfg['govukSearches']:
        url = GOVUK + 'api/search.json?' + urllib.parse.urlencode({
            'q': s['q'], 'filter_organisations': s['org'], 'order': '-public_timestamp', 'count': 40,
            'fields': 'title,link,public_timestamp,content_store_document_type'})
        try:
            results = json.loads(fetch(url))['results']
        except Exception as e:
            held.append({'id': 'search:' + s['q'], 'reason': str(e)[:300]})
            continue
        for r in results:
            link = r.get('link', '')
            if link in seen or link in watched_links or not link.startswith('/'):
                continue
            if r.get('content_store_document_type') in cfg['govukExcludeTypes']:
                continue
            if not r.get('public_timestamp') or local_date(r['public_timestamp']) < since:
                continue
            rule = next((x for x in cfg['govukTitleRules'] if re.search(x['pattern'], r['title'], re.I)), None)
            if not rule or re.search(cfg['govukTitleExclude'], r['title'], re.I):
                continue
            seen.add(link)
            try:
                j = content_api(link[1:])
                if norm(j['title']) != norm(r['title']):
                    raise ValueError('title differs between search and page')
                stamp = j.get('public_updated_at') or j.get('first_published_at')
                day = local_date(stamp)
                if day < since or day > TODAY:
                    continue
                desc, moved = j.get('description') or '', {}
                if local_date(j.get('first_published_at') or stamp) < since:
                    # an older page that moved: show it only with the owner's own note of what changed
                    notes = [c for c in j.get('details', {}).get('change_history', []) if local_date(c['public_timestamp']) == day]
                    if not notes or MINOR.match(norm(notes[-1]['note'])):
                        continue
                    desc, moved = notes[-1]['note'], {'earlier': []}
                if not desc:
                    raise ValueError('no official description to show')
                out.append({'id': 'g-%s' % slug(link.split('/')[-1]), 'type': 'new', 'area': rule['area'],
                            'title': plain(j['title']), 'summary': plain(desc), 'quoted': True, 'meaning': rule['meaning'],
                            'date': day.isoformat(), 'sources': [{'name': 'GOV.UK', 'url': GOVUK + link[1:]}],
                            'verifiedOn': TODAY.isoformat(), **moved})
            except Exception as e:
                held.append({'id': link, 'reason': str(e)[:300]})
    return out


def legislation(cfg, since, held):
    out, seen = [], set()
    for f in cfg['legislationFeeds']:
        url = 'https://www.legislation.gov.uk/uksi/data.feed?' + urllib.parse.urlencode({'title': f['q'], 'sort': 'published'})
        try:
            feed = fetch(url)
        except Exception as e:
            held.append({'id': 'legislation:' + f['q'], 'reason': str(e)[:300]})
            continue
        for entry in re.findall(r'<entry>.*?</entry>', feed, re.S):
            t = re.search(r'<title>(.*?)</title>', entry, re.S)
            i = re.search(r'<id>http://www\.legislation\.gov\.uk/id/(uksi/\d{4}/\d+)</id>', entry)
            p = re.search(r'<published>(.*?)</published>', entry)
            if not (t and i and p):
                continue
            title = norm(t.group(1))
            if i.group(1) in seen or not re.search(f['pattern'], title):
                continue
            day = local_date(p.group(1) if re.search(r'[Z+]', p.group(1)) else p.group(1) + 'Z')
            if day < since or day > TODAY:
                continue
            seen.add(i.group(1))
            link = 'https://www.legislation.gov.uk/%s/made' % i.group(1)
            try:
                if title not in page_text(link):
                    raise ValueError('title not on the instrument page')
                out.append({'id': 'l-' + slug(i.group(1)), 'type': 'new', 'area': f['area'], 'title': title,
                            'summary': 'Statutory instrument published on legislation.gov.uk.', 'meaning': f['meaning'],
                            'date': day.isoformat(), 'sources': [{'name': 'legislation.gov.uk', 'url': link}],
                            'verifiedOn': TODAY.isoformat()})
            except Exception as e:
                held.append({'id': link, 'reason': str(e)[:300]})
    return out


def nhs_feed(cfg, since, held):
    c, out = cfg['nhsFeed'], []
    try:
        feed = fetch(c['url'])
    except Exception as e:
        held.append({'id': c['url'], 'reason': str(e)[:300]})
        return out
    for entry in re.findall(r'<item>.*?</item>', feed, re.S):
        t = re.search(r'<title>(.*?)</title>', entry, re.S)
        l = re.search(r'<link>(.*?)</link>', entry, re.S)
        p = re.search(r'<pubDate>(.*?)</pubDate>', entry)
        if not (t and l and p):
            continue
        title = norm(t.group(1))
        if not re.search(c['pattern'], title, re.I) or re.search(c['exclude'], title, re.I):
            continue
        d = datetime.datetime.strptime(p.group(1).strip(), '%a, %d %b %Y %H:%M:%S %z')
        day = d.astimezone(TZ).date() if TZ else d.date()
        if day < since or day > TODAY:
            continue
        link = l.group(1).strip()
        try:
            if not link.startswith('https://www.england.nhs.uk/'):
                raise ValueError('link is off site')
            if title not in page_text(link):
                raise ValueError('title not on the publication page')
            out.append({'id': 'n-' + slug(link.rstrip('/').split('/')[-1]), 'type': 'new', 'area': c['area'], 'title': title,
                        'summary': 'New publication from NHS England.', 'meaning': c['meaning'], 'date': day.isoformat(),
                        'sources': [{'name': c['name'], 'url': link}], 'verifiedOn': TODAY.isoformat()})
        except Exception as e:
            held.append({'id': link, 'reason': str(e)[:300]})
    return out


def carry_today(previous, standing_cfg, current_ids, unreadable_standing, blocked_hosts):
    """Items verified earlier today that this run could not re-read because their site refused it."""
    today = TODAY.isoformat()
    if not previous or previous.get('dataAsOf') != today:
        return []
    cfg = {i['id']: i for i in standing_cfg}
    kept = []
    for old in previous.get('items') or []:
        urls = [s.get('url', '') for s in old.get('sources') or []]
        if old.get('verifiedOn') != today or old.get('id') in current_ids or not urls:
            continue
        if old.get('type') == 'standing':
            want = cfg.get(old['id'])
            if not want or old['id'] not in unreadable_standing:
                continue
            if any(old.get(k) != want.get(k) for k in ('area', 'title', 'summary', 'meaning', 'date', 'deadline', 'deadlineLabel')):
                continue
            if urls != [ev['url'] for ev in want['evidence']]:
                continue
        elif not all(host(u) in blocked_hosts for u in urls):
            continue
        kept.append(old)
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'sofia-insights.json'))
    ap.add_argument('--held', default=os.path.join(ROOT, 'state', 'sofia-held.json'))
    ap.add_argument('--standing', default=os.path.join(ROOT, 'config', 'sofia-standing.json'))
    a = ap.parse_args()
    cfg = json.load(open(os.path.join(ROOT, 'config', 'sofia-sources.json'), encoding='utf-8'))
    standing_cfg = json.load(open(a.standing, encoding='utf-8'))['items']
    since = TODAY - datetime.timedelta(days=cfg['windowDays'])
    held, standing, unreadable = [], [], set()
    for item in standing_cfg:
        try:
            standing.append(check_standing(item))
        except Exception as e:
            if isinstance(e, Unreadable):
                unreadable.add(item['id'])
            held.append({'id': item['id'], 'reason': str(e)[:300]})
    new = watched(cfg, since, held) + searched(cfg, since, held) + legislation(cfg, since, held) + nhs_feed(cfg, since, held)
    try:
        with open(a.out, encoding='utf-8') as f:
            previous = json.load(f)
    except (OSError, ValueError):
        previous = None
    kept = carry_today(previous, standing_cfg, {i['id'] for i in standing + new}, unreadable,
                       {host(u) for u in _unreadable})
    kept_ids = {i['id'] for i in kept}
    held = [h for h in held if h['id'] not in kept_ids]
    standing += [i for i in kept if i['type'] == 'standing']
    order = [i['id'] for i in standing_cfg]
    standing.sort(key=lambda i: order.index(i['id']))
    new += [i for i in kept if i['type'] != 'standing']
    if kept:
        print('kept %d item(s) verified earlier today that this machine could not re-read: %s' % (len(kept), ', '.join(sorted(kept_ids))))
    new.sort(key=lambda x: (x['date'], x['area'], x['title']), reverse=True)
    if not standing:
        sys.exit('No standing item passed. Nothing written. First reason: %s' % (held[0]['reason'] if held else 'unknown'))
    data = {'_notice': 'Medical Sales Intelligence Hub. Compiled by Elevate and Thrive Limited from named official sources. Members only.',
            'dataAsOf': TODAY.isoformat(), 'checkedAt': NOW.strftime('%H:%M'), 'windowDays': cfg['windowDays'],
            'heldCount': len(held), 'items': new + standing}
    for path, obj in ((a.out, data), (a.held, {'date': TODAY.isoformat(), 'held': held})):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
        os.replace(path + '.tmp', path)
    print('%s: %d standing, %d new in %d days, %d held' % (TODAY, len(standing), len(new), cfg['windowDays'], len(held)))
    for h in held:
        print('  HELD', h['id'], '-', h['reason'])


if __name__ == '__main__':
    main()
