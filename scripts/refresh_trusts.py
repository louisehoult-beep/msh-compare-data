#!/usr/bin/env python3
"""Weekly refresh of the NHS trust data behind the Hub's Med Sales Tools.
Source: the official NHS ODS register (public API). Stdlib only.

Writes two files from ONE crawl:
  data/trust-map.json     — every legally-live trust with its commissioning ICB,
                            for the Stakeholder Mapper's trust-level drill-down.
  data/prep-config.json   — trustDirectory (Meeting Prep tool), preserving
                            profiled trusts, national info and specialities.

⚠️ TWO FILTERS THAT MATTER — do not "simplify" either of them away.

1. STATUS IS NOT A LIVENESS TEST. ODS keeps merged and dissolved trusts at
   Status:Active indefinitely. Weston Area Health, Ipswich Hospital, Royal
   Liverpool and Broadgreen and ~30 others all still return Active years after
   they ceased to exist — and until 24/07/2026 every one of them was in this
   tool's trust directory. The reliable signal is a **Legal date carrying an
   End** on the organisation record. Same trap the ICB list hit in 2026 (42 vs
   36): filter on legal end date, never on status.

2. THE ICB LINK comes from the active RE5/RE8 relationship to a target whose
   primary role is RO261 (ICB). As at 24/07/2026 ODS had been updated to the
   post-01/04/2026 map — all 36 current ICB codes appear, none of the 12
   abolished ones do. Do not hardcode a trust→ICB table: re-derive it every
   run, because the proposed April 2027 round will move trusts between ICBs.

Welsh trusts (Velindre, Welsh Ambulance, Public Health Wales) are legally live
but have no ICB — Wales has no ICBs. Kept, tagged nation 'Wales', icb null.
"""
import json, re, urllib.request, concurrent.futures, datetime, sys

LIST_URL = ("https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
            "?PrimaryRoleId=RO197&Status=Active&Limit=1000")
CFG_PATH = "data/prep-config.json"
MAP_PATH = "data/trust-map.json"

# The 36 ICBs effective 01/04/2026 and the NHS England region each sits in.
# Source of truth: Cowork-OS .../Medical Sales Hub/Website/mapper-data/icb-list-2026-04.js
ICB = {
    'QOQ': ('Humber and North Yorkshire', 'North East and Yorkshire'),
    'QHM': ('North East and North Cumbria', 'North East and Yorkshire'),
    'QF7': ('South Yorkshire', 'North East and Yorkshire'),
    'QWO': ('West Yorkshire', 'North East and Yorkshire'),
    'QYG': ('Cheshire and Merseyside', 'North West'),
    'QOP': ('Greater Manchester', 'North West'),
    'QE1': ('Lancashire and South Cumbria', 'North West'),
    'QHL': ('Birmingham and Solihull', 'Midlands'),
    'QUA': ('Black Country', 'Midlands'),
    'QWU': ('Coventry and Warwickshire', 'Midlands'),
    'QJ2': ('Derby and Derbyshire', 'Midlands'),
    'QGH': ('Herefordshire and Worcestershire', 'Midlands'),
    'QK1': ('Leicester, Leicestershire and Rutland', 'Midlands'),
    'QJM': ('Lincolnshire', 'Midlands'),
    'QPM': ('Northamptonshire', 'Midlands'),
    'QT1': ('Nottingham and Nottinghamshire', 'Midlands'),
    'QOC': ('Shropshire, Telford and Wrekin', 'Midlands'),
    'QNC': ('Staffordshire and Stoke-on-Trent', 'Midlands'),
    'S1Y5D': ('Central East', 'East of England'),
    'D7T5G': ('Essex', 'East of England'),
    'T6Y0W': ('Norfolk and Suffolk', 'East of England'),
    'QMF': ('North East London', 'London'),
    'QKK': ('South East London', 'London'),
    'QWE': ('South West London', 'London'),
    'Z9B2Z': ('West and North London', 'London'),
    'QRL': ('Hampshire and Isle of Wight', 'South East'),
    'QKS': ('Kent and Medway', 'South East'),
    'S9B9J': ('Surrey and Sussex', 'South East'),
    'S0E4D': ('Thames Valley', 'South East'),
    'QOX': ('Bath and North East Somerset, Swindon and Wiltshire', 'South West'),
    'QUY': ('Bristol, North Somerset and South Gloucestershire', 'South West'),
    'QT6': ('Cornwall and The Isles of Scilly', 'South West'),
    'QJK': ('Devon', 'South West'),
    'QVV': ('Dorset', 'South West'),
    'QR1': ('Gloucestershire', 'South West'),
    'QSL': ('Somerset', 'South West'),
}
# Board in Common since 20/11/2025 — three legal entities, one executive team.
BUYING_CENTRE = {'QJ2': 'DLN', 'QJM': 'DLN', 'QT1': 'DLN'}


def clean(n):
    n = n.title().replace(' Nhs ', ' NHS ').replace("'S ", "'s ").replace("'S", "'s")
    n = re.sub(r'\bAnd\b', 'and', n)
    n = re.sub(r'\bOf\b', 'of', n)
    n = re.sub(r'\bThe\b', 'the', n)
    return n[0].upper() + n[1:]


def kind(name):
    """Trust sector, derived from the NAME ONLY — and deliberately refusing to
    guess past what the name proves.

    ⚠️ THE OLD VERSION RETURNED 'Hospital / acute' AS A CATCH-ALL AND WAS WRONG
    ABOUT ROUGHLY A FIFTH OF TRUSTS. Nottinghamshire Healthcare, Sussex
    Partnership, Mersey Care and Pennine Care are all mental health trusts, and
    all four were being labelled acute hospitals on the Stakeholder Mapper.

    "Healthcare" and "Partnership" cannot be used as rules: Nottinghamshire
    Healthcare is mental health, Northumbria Healthcare and Imperial College
    Healthcare are acute. There is no keyword that separates them, so the
    ambiguous ones now return None and the UI groups them as "Acute and other
    trusts" rather than asserting a sector nobody verified.

    ODS carries no sector field — checked 24/07/2026 across all 202 live
    trusts, the only active non-primary roles are RO57 (Foundation Trust
    status), RO7 (HOSPICE, plainly legacy noise on 60 trusts) and RO268
    (medicine supplier). A properly evidenced sector would have to come from
    NHS England submission lists (MHSDS for mental health, Ambulance Quality
    Indicators for ambulance), which is a real build and a monthly dependency.
    Until someone does that, None means "not established", not "acute".
    """
    u = name.upper()
    if 'AMBULANCE' in u: return 'Ambulance service'
    if 'MENTAL HEALTH' in u or 'PSYCHIAT' in u: return 'Mental health'
    if 'COMMUNITY' in u and 'HOSPITAL' not in u: return 'Community'
    return None


def fetch_detail(o):
    """Returns None for a trust that has legally ended (see filter 1 above)."""
    try:
        r = json.loads(urllib.request.urlopen(o['OrgLink'], timeout=30).read())['Organisation']
    except Exception:
        return None
    for d in r.get('Date', []):
        if d.get('Type') == 'Legal' and d.get('End'):
            return None                     # merged / dissolved — not a live account
    icb = None
    for rel in r.get('Rels', {}).get('Rel', []):
        if rel.get('Status') != 'Active':
            continue
        t = rel.get('Target', {})
        if t.get('PrimaryRoleId', {}).get('id') == 'RO261':
            icb = t['OrgId']['extension']
            break
    town = (r.get('GeoLoc', {}).get('Location', {}) or {}).get('Town', '').title()
    icb_name, region = ICB.get(icb, (None, None))
    welsh = icb is None
    return {'n': clean(o['Name']), 'code': o['OrgId'], 'town': town,
            'postcode': o.get('PostCode', ''), 'kind': kind(o['Name']),
            'icb': icb, 'icbName': icb_name,
            'region': region or ('Wales' if welsh else None),
            'nation': 'Wales' if welsh else 'England',
            'bc': BUYING_CENTRE.get(icb)}


def main():
    orgs = json.loads(urllib.request.urlopen(LIST_URL, timeout=60).read())['Organisations']
    if len(orgs) < 150:
        raise SystemExit("ABORT: ODS returned %d trusts (expected ~240+) — refusing to shrink." % len(orgs))
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        live = [e for e in ex.map(fetch_detail, orgs) if e]

    if len(live) < 180:
        raise SystemExit("ABORT: only %d legally-live trusts after filtering (expected ~210+) — "
                         "refusing to shrink the directory." % len(live))
    stray = [e['n'] for e in live if e['nation'] == 'Wales' and 'WALES' not in e['n'].upper()
             and 'VELINDRE' not in e['n'].upper()]
    if stray:
        print("WARNING: %d legally-live trusts with no ICB link that are not obviously Welsh — "
              "check before trusting their region: %s" % (len(stray), ', '.join(stray[:10])),
              file=sys.stderr)

    live.sort(key=lambda e: (0 if e['kind'] is None else 1, e['n']))
    today = datetime.date.today().strftime('%d/%m/%Y')

    # ---- data/trust-map.json — the Stakeholder Mapper's trust drill-down ----
    json.dump({'asOf': today,
               'source': 'NHS Organisation Data Service (ODS) ORD API, Open Government Licence v3',
               'sourceUrl': 'https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations',
               'icbEffectiveFrom': '2026-04-01',
               'count': len(live),
               'excludedLegallyEnded': len(orgs) - len(live),
               'trusts': live},
              open(MAP_PATH, 'w'), ensure_ascii=False, indent=1)

    # ---- data/prep-config.json — Meeting Prep trust directory (unprofiled only) ----
    cfg = json.load(open(CFG_PATH))
    profiled = {t['name'] for t in cfg.get('trusts', [])}
    cfg['trustDirectory'] = [{k: e[k] for k in ('n', 'code', 'town', 'postcode', 'kind')}
                             for e in live if e['n'] not in profiled]
    cfg['trustDirectoryAsOf'] = today + ' (NHS ODS register, legally-live trusts only)'
    json.dump(cfg, open(CFG_PATH, 'w'), ensure_ascii=False, indent=1)

    print("trust-map: %d live trusts (%d England / %d Wales); directory: %d entries; "
          "%d legally-ended ODS records excluded"
          % (len(live), sum(1 for e in live if e['nation'] == 'England'),
             sum(1 for e in live if e['nation'] == 'Wales'),
             len(cfg['trustDirectory']), len(orgs) - len(live)))


if __name__ == '__main__':
    main()
