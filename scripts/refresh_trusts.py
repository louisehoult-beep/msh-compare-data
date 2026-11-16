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

4. WALES BUYS THROUGH HEALTH BOARDS, NOT TRUSTS (added 16/11/2026). Until now
   this crawl asked ODS for RO197 and RO107 only, so the whole of Welsh
   purchasing was represented by three national trusts and the seven Local
   Health Boards that actually buy — Betsi Cadwaladr, Hywel Dda, Swansea Bay,
   Cardiff and Vale, Cwm Taf Morgannwg, Aneurin Bevan and Powys — appeared
   nowhere on the Hub. Their ODS primary role is RO142 (LOCAL HEALTH BOARD),
   now in LIST_URLS.

   NOT RO144 (WELSH LOCAL HEALTH BOARD), which is the role the name suggests and
   is the wrong one: checked 16/11/2026, RO144 returns ZERO active
   organisations. Every live Welsh board is filed under RO142.

5. NATION COMES FROM THE REGISTER, NOT FROM "HAS NO ICB" (changed 16/11/2026).
   This used to read `welsh = icb is None`, which is a guess that happened to
   hold while the only ICB-less rows were Welsh. It printed a warning for
   anything else and would have mislabelled a Scottish or Northern Irish body,
   or an English trust whose ICB relationship lapsed, as Welsh. The ODS record
   carries the answer: GeoLoc.Location.Country, which reads WALES for all ten
   Welsh organisations. The warning below now fires on a row the register calls
   neither England nor Wales, which is a real anomaly rather than a guess.
"""
import json, re, urllib.request, concurrent.futures, datetime, sys

# 3. ONE PRIMARY ROLE IS NOT THE WHOLE SECTOR. RO197 (NHS TRUST) misses every
#    organisation whose PRIMARY role is RO107 (CARE TRUST), and three of those
#    are legally-live NHS foundation trusts a rep can absolutely sell into:
#    Bradford District Care, Sheffield Health Partnership University, and Black
#    Country Healthcare. Until 14/08/2026 none of the three appeared anywhere —
#    not in the Meeting Prep directory, not in the Stakeholder Mapper's trust
#    drill-down — so they read as "does not exist" rather than "not profiled".
#    Found because the trust-pressures gate flagged a trust carrying published
#    RTT figures that the trust map had never heard of. If ODS adds another
#    trust-like primary role, add it here rather than to a second crawl.
LIST_URLS = [("https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
              "?PrimaryRoleId=%s&Status=Active&Limit=1000") % r
             for r in ('RO197', 'RO107', 'RO142')]
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


def kind_for(name, primary_role):
    """A Welsh Local Health Board is a sector in its own right, and it is the one
    sector the ODS register DOES prove: the primary role RO142 says it. Every
    other sector still comes from the name and still refuses to guess. Added
    16/11/2026 with the Welsh boards; app/mst-logic.js groups this label and
    verify.py's KINDS allows it."""
    if primary_role == 'RO142':
        return 'Local Health Board'
    return kind(name)


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
    loc = (r.get('GeoLoc', {}).get('Location', {}) or {})
    town = loc.get('Town', '').title()
    icb_name, region = ICB.get(icb, (None, None))
    # See note 5 in the module docstring: the register's own country field, not
    # "has no ICB link".
    country = (loc.get('Country') or '').strip().upper()
    welsh = country == 'WALES'
    primary = next((x['id'] for x in (r.get('Roles') or {}).get('Role', [])
                    if x.get('primaryRole')), None)
    return {'n': clean(o['Name']), 'code': o['OrgId'], 'town': town,
            'postcode': o.get('PostCode', ''),
            'kind': kind_for(o['Name'], primary),
            'icb': icb, 'icbName': icb_name,
            'region': region or ('Wales' if welsh else None),
            'nation': 'Wales' if welsh else 'England',
            'odsCountry': country or None,
            'bc': BUYING_CENTRE.get(icb)}


def main():
    orgs, seen = [], set()
    for url in LIST_URLS:
        for o in json.loads(urllib.request.urlopen(url, timeout=60).read())['Organisations']:
            if o['OrgId'] not in seen:
                seen.add(o['OrgId'])
                orgs.append(o)
    if len(orgs) < 150:
        raise SystemExit("ABORT: ODS returned %d trusts (expected ~240+) — refusing to shrink." % len(orgs))
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        live = [e for e in ex.map(fetch_detail, orgs) if e]

    if len(live) < 180:
        raise SystemExit("ABORT: only %d legally-live trusts after filtering (expected ~210+) — "
                         "refusing to shrink the directory." % len(live))
    # The register says WALES or it says ENGLAND. Anything else is an anomaly
    # worth a human look, not something to label by guesswork. This replaced a
    # warning that fired on "no ICB link and the name does not say Wales", which
    # was a guess about a guess.
    stray = [(e['n'], e['odsCountry']) for e in live
             if (e['odsCountry'] or '') not in ('ENGLAND', 'WALES')]
    if stray:
        print("WARNING: %d legally-live organisation(s) whose ODS country is neither "
              "ENGLAND nor WALES — they are tagged England by default, so check them "
              "before trusting the nation or region: %s"
              % (len(stray), ', '.join('%s (%r)' % s for s in stray[:10])),
              file=sys.stderr)
    boards = [e for e in live if e['kind'] == 'Local Health Board']
    if len(boards) < 7:
        raise SystemExit("ABORT: only %d Welsh Local Health Board(s) (expected 7). Wales has "
                         "had seven since 01/04/2019; refusing to shrink Wales coverage."
                         % len(boards))

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
    # Match on ODS code, not name. Name matching silently failed on
    # 'The Newcastle Upon Tyne Hospitals NHS Foundation Trust' (ODS) versus
    # '...upon Tyne...' (the trust's own spelling, used in its profile), so a
    # fully profiled trust kept reappearing in the unprofiled directory and
    # Meeting Prep showed it as having no Hub profile. The code is the identity;
    # the display name is not, and it drifts.
    profiled = {t['code'] for t in cfg.get('trusts', [])}
    # icb/icbName/region ride along in the directory itself. They were derived
    # here every run and then thrown away, so Meeting Prep had no ICB for an
    # unprofiled trust and the panel could not say who commissions it. Adding
    # them to the directory rather than to a second file is deliberate: a key
    # this generator does not write is a key this generator DESTROYS on its
    # next run, which is exactly how the supplier index lost its aliases.
    cfg['trustDirectory'] = [{k: e[k] for k in ('n', 'code', 'town', 'postcode', 'kind',
                                                'icb', 'icbName', 'region', 'nation', 'bc')}
                             for e in live if e['code'] not in profiled]
    cfg['trustDirectoryAsOf'] = today + ' (NHS ODS register, legally-live trusts only)'
    json.dump(cfg, open(CFG_PATH, 'w'), ensure_ascii=False, indent=1)

    print("trust-map: %d live trusts (%d England / %d Wales); directory: %d entries; "
          "%d legally-ended ODS records excluded"
          % (len(live), sum(1 for e in live if e['nation'] == 'England'),
             sum(1 for e in live if e['nation'] == 'Wales'),
             len(cfg['trustDirectory']), len(orgs) - len(live)))


if __name__ == '__main__':
    main()
