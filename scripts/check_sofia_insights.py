#!/usr/bin/env python3
"""Gate for data/sofia-insights.json. Exit 1 (nothing publishes) if any item is not verified today,
cites a source outside the official list, lacks a meaning line, or reads as advice.
Usage: python3 scripts/check_sofia_insights.py [file]
"""
import datetime, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.datetime.now(ZoneInfo('Europe/London')).date()
except Exception:  # pragma: no cover
    TODAY = datetime.date.today()
HOSTS = {'www.gov.uk', 'www.legislation.gov.uk', 'www.england.nhs.uk', 'www.nice.org.uk', 'health.ec.europa.eu'}
AREAS = {'Device rules', 'How buyers decide', 'Supplier duties', 'Funding and access'}
ADVICE = re.compile(r"\b(you should|you need to|you must|we recommend|we advise|consider\b|make sure|ensure that|don't|do not forget|advise you)", re.I)
DASH = re.compile('[–—]')


def problems(data):
    bad = []
    today = TODAY.isoformat()
    if data.get('dataAsOf') != today:
        bad.append('dataAsOf is %s, today is %s' % (data.get('dataAsOf'), today))
    items = data.get('items') or []
    if not any(i.get('type') == 'standing' for i in items):
        bad.append('no standing items')
    seen = set()
    for i in items:
        who = i.get('id', '?')
        if who in seen:
            bad.append('%s: duplicate id' % who)
        seen.add(who)
        for k in ('id', 'type', 'area', 'title', 'summary', 'meaning', 'sources', 'verifiedOn'):
            if not i.get(k):
                bad.append('%s: no %s' % (who, k))
        if i.get('verifiedOn') != today:
            bad.append('%s: verified %s, not today' % (who, i.get('verifiedOn')))
        if i.get('area') not in AREAS:
            bad.append('%s: unknown area %s' % (who, i.get('area')))
        for s in i.get('sources') or []:
            u = urllib.parse.urlparse(s.get('url', ''))
            if u.scheme != 'https' or u.netloc not in HOSTS:
                bad.append('%s: source not on the official list: %s' % (who, s.get('url')))
        if i.get('type') == 'new' and (not i.get('date') or i['date'] > today):
            bad.append('%s: new item with no past date' % who)
        # words we wrote; quoted official text (summary of a new item) is left as the owner wrote it
        ours = [i.get('meaning', '')] + ([] if i.get('quoted') else [i.get('title', ''), i.get('summary', '')])
        for text in ours:
            if ADVICE.search(text):
                bad.append('%s: reads as advice: "%s"' % (who, ADVICE.search(text).group(0)))
            if DASH.search(text):
                bad.append('%s: contains a dash character' % who)
    return bad


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'sofia-insights.json')
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        sys.exit('GATE RED: cannot read %s (%s)' % (path, e))
    bad = problems(data)
    if bad:
        print('GATE RED')
        for b in bad:
            print('  ' + b)
        sys.exit(1)
    print('GATE GREEN: %d items, all verified %s' % (len(data['items']), data['dataAsOf']))


if __name__ == '__main__':
    main()
