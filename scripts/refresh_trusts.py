#!/usr/bin/env python3
"""Weekly refresh of the NHS trust directory in data/prep-config.json.
Source: the official NHS ODS register (public API). Stdlib only.
Preserves everything else in the config (profiled trusts, national info, specialities)."""
import json, re, urllib.request, concurrent.futures, datetime

LIST_URL = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?PrimaryRoleId=RO197&Status=Active&Limit=1000"
CFG_PATH = "data/prep-config.json"

def clean(n):
    n = n.title().replace(' Nhs ', ' NHS ').replace("'S ", "'s ").replace("'S", "'s")
    n = re.sub(r'\bAnd\b', 'and', n); n = re.sub(r'\bOf\b', 'of', n); n = re.sub(r'\bThe\b', 'the', n)
    return n[0].upper() + n[1:]

def kind(name):
    u = name.upper()
    if 'AMBULANCE' in u: return 'Ambulance'
    if 'MENTAL HEALTH' in u or 'PSYCHIAT' in u: return 'Mental health'
    if 'COMMUNITY' in u and 'HOSPITAL' not in u: return 'Community'
    return 'Hospital / acute'

def fetch_detail(o):
    try:
        r = json.loads(urllib.request.urlopen(o['OrgLink'], timeout=30).read())['Organisation']
        town = (r.get('GeoLoc', {}).get('Location', {}) or {}).get('Town', '').title()
    except Exception:
        town = ''
    return {'n': clean(o['Name']), 'code': o['OrgId'], 'town': town,
            'postcode': o.get('PostCode', ''), 'kind': kind(o['Name'])}

def main():
    orgs = json.loads(urllib.request.urlopen(LIST_URL, timeout=60).read())['Organisations']
    if len(orgs) < 150:
        raise SystemExit("ABORT: ODS returned %d trusts (expected ~240+) — refusing to shrink the directory." % len(orgs))
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        entries = list(ex.map(fetch_detail, orgs))
    entries.sort(key=lambda e: (0 if e['kind'] == 'Hospital / acute' else 1, e['n']))
    cfg = json.load(open(CFG_PATH))
    profiled = {t['name'] for t in cfg.get('trusts', [])}
    cfg['trustDirectory'] = [e for e in entries if e['n'] not in profiled]
    cfg['trustDirectoryAsOf'] = datetime.date.today().strftime('%d/%m/%Y') + ' (NHS ODS register)'
    json.dump(cfg, open(CFG_PATH, 'w'), ensure_ascii=False, indent=1)
    print("trust directory refreshed:", len(cfg['trustDirectory']), "entries")

if __name__ == '__main__':
    main()
