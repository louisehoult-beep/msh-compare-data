"""One-off fixes for the Enteral Feeding, Bile Bags and Associated Products
framework-coverage batch, 16/11/2026.

1. Alias "Ivor Shaw Ltd (t/a Pennine Healthcare)" (the framework brief's own
   wording) onto the existing curated record "Pennine Healthcare (Ivor Shaw
   Ltd)", which already carries "Ivor Shaw Ltd" and "t/a Pennine Healthcare"
   as separate aliases -- same company, just the two tokens in the other
   order. Rule 10: resolve before publish.

2. Merge the duplicate stub record the 15/11/2026 NHSSC backfill created
   under the brief's literal (truncated-parenthesis) text,
   "Enteral Access Technologies Ltd (previously named on the framework as
   Nasogastric Feeding Solutions Ltd", into the existing curated
   "Enteral Access Technologies Ltd" record. That record already carries
   "NASOGASTRIC FEEDING SOLUTIONS LTD" as an alias, sourced from Companies
   House previous_company_names for 11367892 (read 2026-09-03) -- a primary
   source already on file confirming the same company, so this is a rule-10
   resolution, not a merge needing Lou's judgement. The stub carried no
   products and no fact the curated record lacks, so nothing is lost by
   dropping it; the curated record's existing framework note already covers
   this award ("One of 19 awarded suppliers").

3. Record Helapet Ltd's domain. Found via its own homepage, which names the
   company directly ("Welcome to Helapet Limited" / footer "Helapet Ltd") and
   lists an "Enteral Feeding Devices" category (Nutricair(TM) ENFit range) --
   an unambiguous single-entity name match, not a subsidiary/parent case, so
   the domain-proof-tier policy (for attributing a foreign/parent site to a
   UK entity) does not apply here. No on-site company number or matching
   registered-office address was found (the footer address, Houghton Regis,
   is a trading/warehouse address; Companies House 01787363's registered
   office is High Wycombe) so no companyNumberProof is added -- domain only.
"""
import json, io

SEED = 'data/supplier-seed.json'
seed = json.load(open(SEED))
sups = seed['suppliers']

# --- 1. Ivor Shaw / Pennine Healthcare alias ---
pennine = next(s for s in sups if s['name'] == 'Pennine Healthcare (Ivor Shaw Ltd)')
alias = 'Ivor Shaw Ltd (t/a Pennine Healthcare)'
if alias not in pennine['aliases']:
    pennine['aliases'].append(alias)
    print('added alias to Pennine Healthcare (Ivor Shaw Ltd):', alias)
else:
    print('alias already present on Pennine Healthcare (Ivor Shaw Ltd)')

# --- 2. Enteral Access Technologies Ltd duplicate merge ---
eat_good = next(s for s in sups if s['name'] == 'Enteral Access Technologies Ltd')
stub_name = ('Enteral Access Technologies Ltd (previously named on the framework as '
             'Nasogastric Feeding Solutions Ltd')
stub = next((s for s in sups if s['name'] == stub_name), None)
if stub is not None:
    if stub_name not in eat_good['aliases']:
        eat_good['aliases'].append(stub_name)
    sups.remove(stub)
    print('merged duplicate stub into Enteral Access Technologies Ltd, alias added, stub removed')
else:
    print('no duplicate EAT stub found (already merged)')

# --- 3. Helapet Ltd domain ---
helapet = next(s for s in sups if s['name'] == 'Helapet Ltd')
helapet['domain'] = 'helapet.co.uk'
helapet.setdefault('links', [])
if not any(l.get('url') == 'https://www.helapet.co.uk' for l in helapet['links']):
    helapet['links'].append({
        'label': 'Company website',
        'url': 'https://www.helapet.co.uk',
        'source': ('Own homepage names the company directly ("Welcome to Helapet '
                    'Limited"; footer "Helapet Ltd") and lists an Enteral Feeding '
                    'Devices category (Nutricair(TM) ENFit range) matching the '
                    'framework award. No on-site company number or matching '
                    'registered-office address found, so this is a name-match '
                    'confirmation only, not domain-proof-tier (not needed here: '
                    'single UK entity, not a subsidiary/parent ambiguity). '
                    'Checked 2026-11-16.'),
    })
print('set Helapet Ltd domain -> helapet.co.uk')

with io.open(SEED, 'w', encoding='utf-8') as f:
    json.dump(seed, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('wrote', SEED)

# --- 4. company-press.json: same EAT duplicate, caught by verify.py's
#     company-press check (every name it carries press for must resolve to a
#     supplier-seed.json record). Both the stub's and the good record's press
#     entries are empty (items: []); drop the stub's empty entry and add its
#     alias string onto the good record's matchAliases so a press source using
#     that exact brief wording still matches. ---
PRESS = 'data/company-press.json'
press = json.load(open(PRESS))
psups = press['suppliers']
if stub_name in psups:
    stub_press = psups.pop(stub_name)
    good_press = psups.get(eat_good['name'])
    if good_press is not None and not good_press.get('items') and not stub_press.get('items'):
        ci = good_press.setdefault('matchAliases', {}).setdefault('caseInsensitive', [])
        if stub_name not in ci:
            ci.append(stub_name)
        print('removed empty stub press entry, added alias to good EAT press record')
    else:
        print('WARNING: stub or good press entry carries items — not auto-merged, check by hand')
else:
    print('no stub press entry found (already merged)')
# The merge above drops company-press.json from 1289 to 1288 rows -- the
# same -1 the supplier-seed.json merge applies. Update the header counts to
# match this run's real row count (not a stale generation-drift bug: the
# count genuinely changed because of this merge).
actual = len(press['suppliers'])
if press.get('counts', {}).get('suppliers') != actual:
    press['counts']['suppliers'] = actual
    print('updated counts.suppliers ->', actual)
if press.get('rotation', {}).get('seedSuppliers') != actual:
    press['rotation']['seedSuppliers'] = actual
    print('updated rotation.seedSuppliers ->', actual)

with io.open(PRESS, 'w', encoding='utf-8') as f:
    json.dump(press, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('wrote', PRESS)
