#!/usr/bin/env python3
"""Reapplyable data fix for member-visible report text (30/09/2026 QA).

Run from the repo root:  python3 scripts/_report_text_cleanup_0930.py [--dry] [--show]
Edits data/supplier-seed.json, data/supplier-index.json, data/company-awards.json
and scripts/refresh_awards.py. Idempotent. Prints every change.
"""
import json, re, sys

DRY = '--dry' in sys.argv

# 1. Summary (deepDive.lede) advice phrasing -> factual statement. Exact sentence swaps.
LEDE = [
    ("it should not be confused with 'Eakin Ostomy'", "it is distinct from 'Eakin Ostomy'"),
    ("A candidate should treat this as a multi-division company in which ophthalmology is one line of business.",
     "It is a multi-division company in which ophthalmology is one line of business."),
    (" Anyone going into an interview should know which one they are being hired by.", ""),
    ("A candidate should read this as a small UK arm of an Australian family-led group,",
     "It is a small UK arm of an Australian family-led group,"),
    ("Anyone assessing this business for a role should be clear that its UK financial statements disclose",
     "Its UK financial statements disclose"),
    ("is not on the public record and should be asked about directly.", "is not on the public record."),
    ("Immedia and Molift in particular should never be treated as independent competitors to Etac.",
     "Immedia and Molift in particular are not independent competitors to Etac."),
    ("Clement Clarke is the reason a respiratory buyer should be paying attention — it brings",
     "Clement Clarke brings"),
    ("A sales professional should know this is a manufacturing subsidiary", "It is a manufacturing subsidiary"),
    ("A candidate should note the company's own stated objective: to deliver",
     "The company's own stated objective is to deliver"),
    (" A candidate should be able to talk about what that means for a customer-facing conversation, not just recite the framework list.", ""),
    ("A candidate should read this as a large, sales-led UK distribution arm", "It is a large, sales-led UK distribution arm"),
    ("moves so far between the two years that it should not be read as market movement without asking the company what was reclassified.",
     "moves so far between the two years that it does not by itself show market movement, and the accounts do not say what was reclassified."),
    ("If the role touches orthopaedics or sits at the Leeds site, that separation will very likely come up, and you should have a view on it.",
     "The separation bears directly on roles in orthopaedics and at the Leeds site."),
    ("A candidate should note the team is small:", "The team is small:"),
    ("A rep meeting this company should know its NHS-facing brand is younger than its Companies House record by decades, and that its own site states",
     "Its NHS-facing brand is younger than its Companies House record by decades, and its own site states"),
    ("Anyone briefing on this account should treat the wheelchair side as a live watch item, not a settled fact either way.",
     "The wheelchair side is a live watch item, not a settled fact either way."),
    ("A sales professional should be ready to discuss this shift away from lower-margin NHS tender business toward private pay and formulary-listed wound care.",
     "Taken together, the filed accounts and stated priorities describe a shift away from lower-margin NHS tender business toward private pay and formulary-listed wound care."),
    ("A rep selling against or interviewing at this company should expect a lean, founder-run business rather than a corporate group",
     "It is a lean, founder-run business rather than a corporate group"),
    ("Say this plainly before anything else: Schiller UK Ltd", "Schiller UK Ltd"),
    ("genuinely not disclosed, and it should never be estimated.", "genuinely not disclosed, and the Hub does not estimate one."),
    ("Buyers should treat the two as separate: a genuinely old legal entity, but a brand narrative",
     "The two are separate: a genuinely old legal entity, and a brand narrative"),
    ("A candidate should read this as a business where nearly half of revenue (£55.5m of £115.4m) is service, and where new-machine sales arrive",
     "Nearly half of revenue (£55.5m of £115.4m) is service, and new-machine sales arrive"),
    ("A candidate should read this as a group-supplied UK sales company", "It is a group-supplied UK sales company"),
    ("A candidate should understand that this is a distribution and technical-support arm of a US manufacturer, not a UK-run business making its own investment decisions — and that as of August 2026",
     "It is a distribution and technical-support arm of a US manufacturer, not a UK-run business making its own investment decisions, and as of August 2026"),
    ("the 'new cannula entrant 2023' description should be read as most likely describing that sister entity, not this one,",
     "the 'new cannula entrant 2023' description most likely describes that sister entity, not this one,"),
]

# 2. Internal file / script / curator names in rendered deep-dive and background prose.
#    Ordered: specific phrases first, then the general file-name rules.
FILES = [
    (r" \(refresh_companies_house\.py / extract_accounts_figures\.py\)", ""),
    (r", populated by refresh_companies_house\.py / extract_accounts_figures\.py", ""),
    (r"refresh_companies_house\.py anchors", "the Hub's Companies House reader anchors"),
    (r"because extract_accounts_figures\.py reads", "because the Hub's accounts reader reads"),
    (r" — see data/pending-awards\.json\.", "."),
    (r", data/supplier-products\.json,", ","),
    (r"\(Hub copy, data/drug-tariff-part-ix\.json, ", "(Hub copy, "),
    (r"(?:this|the) Hub's (own )?supplier-index\.json and company-financials\.json records",
     r"the Hub's \1supplier index and Companies House records"),
    (r"(?:(?:this|the) (?:Hub|repo)'s (?:own )?)?(?:data/)?company-financials\.json in this Hub",
     "the Hub's Companies House record"),
    (r"(?:(?:this|the) (?:Hub|repo)'s (own )?)?(?:data/)?company-financials\.json",
     r"the Hub's \1Companies House record"),
    (r"(?:(?:this|the) (?:Hub|repo)'s (own )?)?(?:data/)?frameworks\.json",
     r"the Hub's \1framework brief record"),
    (r"(?:(?:this|the) (?:Hub|repo)'s (own )?)?(?:data/)?supplier-index\.json",
     r"the Hub's \1supplier index"),
    (r"in supplier-products\.json", "in the Hub's product crawl record"),
    (r"the Hub's prior curator note", "the Hub's prior record"),
    (r"a carried-forward curator claim", "a carried-forward claim"),
    (r"the curator's (\d\d/\d\d/\d{4}) rename decision", r"the Hub's \1 rename"),
    (r"a curator decision made elsewhere", "an editorial decision made elsewhere"),
]

HARTMANN = "Paul Hartmann (HARTMANN)"


def fix_str(t, rules, regex):
    for a, b in rules:
        t = re.sub(a, b, t) if regex else t.replace(a, b)
    return t


def walk_rendered(s, fn):
    """Apply fn to every rendered prose field of one supplier record."""
    dd = s.get('deepDive')
    if isinstance(dd, dict):
        for k in ('lede', 'sources', 'peopleNote', 'interview', 'tagline'):
            if isinstance(dd.get(k), str):
                dd[k] = fn(dd[k], 'deepDive.' + k)
        for k in ('marketPosition', 'ownership'):
            if isinstance(dd.get(k), list):
                dd[k] = [fn(x, 'deepDive.' + k) if isinstance(x, str) else x for x in dd[k]]
        for st in dd.get('stats') or []:
            if isinstance(st, dict):
                for k in ('n', 'l', 'v'):
                    if isinstance(st.get(k), str):
                        st[k] = fn(st[k], 'deepDive.stats.' + k)
    for b in s.get('background') or []:
        if isinstance(b, dict) and isinstance(b.get('text'), str):
            b['text'] = fn(b['text'], 'background.text')


changes = []


def fix_suppliers(doc, label):
    for s in doc.get('suppliers', []):
        def fn(t, path):
            n = t
            if path == 'deepDive.lede':
                n = fix_str(n, LEDE, False)
            n = fix_str(n, FILES, True)
            if n != t:
                changes.append((label, s['name'], path, t, n))
            return n
        walk_rendered(s, fn)
        # 3. HARTMANN: hartmann.co.uk redirects to www.hartmann.info/en-GB (checked 30/09/2026),
        #    which the record's own Website link already points at. Drop the duplicate.
        if s['name'] == HARTMANN and isinstance(s.get('deepDive'), dict):
            L = s['deepDive'].get('links') or []
            keep = [l for l in L if not (l.get('label') == 'Website' and
                    str(l.get('url', '')).rstrip('/').lower() in ('https://hartmann.co.uk', 'http://hartmann.co.uk'))]
            if len(keep) != len(L):
                s['deepDive']['links'] = keep
                changes.append((label, s['name'], 'deepDive.links', 'Website https://hartmann.co.uk', '(removed)'))


sys.path.insert(0, 'scripts')
from seed_format import write_like


def rw(path, doc, fmt=None):
    if DRY:
        return
    r = write_like(path, doc)
    print('wrote', path, r)


SEED = 'data/supplier-seed.json'
IDX = 'data/supplier-index.json'
AW = 'data/company-awards.json'

seed = json.load(open(SEED, encoding='utf-8'))
fix_suppliers(seed, 'seed')
rw(SEED, seed, dict(ensure_ascii=False, separators=(',', ':')))

idx = json.load(open(IDX, encoding='utf-8'))
fix_suppliers(idx, 'index')
rw(IDX, idx, dict(ensure_ascii=False, indent=1))

# 4. Award method text: name the source, not the file.
HIST_OLD_SRC = "same two feeds held in data/tender-history.json"
HIST_NEW_SRC = "same two feeds, held as the Hub's tender and award history"
HIST_OLD_NOTE = "the award history in data/tender-history.json (data as of"
HIST_NEW_NOTE = "the Hub's tender and award history, drawn from Find a Tender and Contracts Finder (data as of"
aw = json.load(open(AW, encoding='utf-8'))
for k, (a, b) in (('source', (HIST_OLD_SRC, HIST_NEW_SRC)), ('source', ("same two feeds held in the Hub's tender and award history", HIST_NEW_SRC))):
    if a in (aw.get(k) or ''):
        aw[k] = aw[k].replace(a, b); changes.append(('awards', '-', k, a, b))
cov = aw.get('coverage') or {}
if HIST_OLD_NOTE in (cov.get('note') or ''):
    cov['note'] = cov['note'].replace(HIST_OLD_NOTE, HIST_NEW_NOTE)
    changes.append(('awards', '-', 'coverage.note', HIST_OLD_NOTE, HIST_NEW_NOTE))
rw(AW, aw, dict(ensure_ascii=False, indent=1))

RA = 'scripts/refresh_awards.py'
src = open(RA, encoding='utf-8').read()
new = src.replace('"same two feeds held in data/tender-history.json" if history else ""',
                  '"same two feeds, held as the Hub\'s tender and award history" if history else ""')
new = new.replace('"Awards are indexed from (1) the award history in %s (data as of %s), "',
                  '"Awards are indexed from (1) the Hub\'s tender and award history, drawn from "\n'
                  '            "Find a Tender and Contracts Finder (data as of %s), "')
new = new.replace('"same two feeds held in the Hub\'s tender and award history" if history else ""',
                  '"same two feeds, held as the Hub\'s tender and award history" if history else ""')
new = new.replace('% (HISTORY_PATH, history.get("dataAsOf") or "not stated", floor or "not stated",',
                  '% (history.get("dataAsOf") or "not stated", floor or "not stated",')
if new != src:
    changes.append(('refresh_awards.py', '-', 'generator', 'data/tender-history.json in member text', 'plain source'))
    if not DRY:
        open(RA, 'w', encoding='utf-8').write(new)


# 5. Other data the report renders: Companies House "Matched on", the pending-awards
#    rule, and product-range filing notes. Fix the data and the generator together.
def str_sub(obj, pairs, label):
    n = [0]
    def w(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str):
                    nv = v
                    for a, b in pairs:
                        nv = nv.replace(a, b)
                    if nv != v:
                        o[k] = nv; n[0] += 1
                else:
                    w(v)
        elif isinstance(o, list):
            for i2, v in enumerate(o):
                if isinstance(v, str):
                    nv = v
                    for a, b in pairs:
                        nv = nv.replace(a, b)
                    if nv != v:
                        o[i2] = nv; n[0] += 1
                else:
                    w(v)
    w(obj)
    if n[0]:
        changes.append((label, '-', 'strings', '%d' % n[0], ''))
    return n[0]

CH_PAIRS = [
    ("company number recorded by a curator in the supplier's own seed record (alerts, background or note)",
     "company number recorded in the Hub's own supplier record"),
    (" as the wrong company — see data/company-match-overrides.json for the evidence. Nothing is asserted",
     " as the wrong company. Nothing is asserted"),
    ("company number recorded by a curator on 30/09/2026 against two independent sources (see data/company-match-overrides.json).",
     "company number recorded on 30/09/2026 against two independent sources."),
]
PA_PAIRS = [
    ("The moment the matching brief exists in data/frameworks.json, this entry is retired here on this script's next run",
     "The moment the matching brief is captured in the Hub's framework brief record, this entry is retired here at the next refresh"),
]
SP_PAIRS = [
    ("(the same rule build_differentiator.py already applies to NHS Supply Chain rows)",
     "(the same rule the Hub already applies to NHS Supply Chain rows)"),
    ("Deliberate, decided by Lou 20/07/2026.", "Deliberate, decided 20/07/2026."),
    ("Do not list these. Tourniquets confirmed CURRENTLY not a GBUK product by Lou directly (20/07/2026) — she ran this division.",
     "Not listed here. Tourniquets confirmed CURRENTLY not a GBUK product directly (20/07/2026)."),
]
for path, pairs, fmt, tail in (
        ('data/company-financials.json', CH_PAIRS, dict(ensure_ascii=False, indent=2), ''),
        ('data/pending-awards.json', PA_PAIRS, dict(ensure_ascii=False, indent=1), ''),
        ('data/supplier-products.json', SP_PAIRS, dict(ensure_ascii=False, indent=1), '\n')):
    doc = json.load(open(path, encoding='utf-8'))
    if str_sub(doc, pairs, path):
        rw(path, doc)

GEN = [
    ('scripts/refresh_companies_house.py', [
        ('("company number recorded by a curator in the supplier\'s own "\n'
         '                                                "seed record (alerts, background or note)")',
         '("company number recorded in the Hub\'s own supplier record")'),
        ('"as the wrong company — see %s for the evidence. Nothing is asserted here until "',
         '"as the wrong company. Nothing is asserted here until "'),
        ('% (decided_on or "03/09/2026", OVERRIDES)),', '% (decided_on or "03/09/2026",)),'),
    ]),
    ('scripts/refresh_pending_awards.py', [
        ('"brief exists in data/frameworks.json, this entry is retired here on "\n'
         '                "this script\'s next run — the confirmed FRAMEWORKS panel is always "',
         '"brief is captured in the Hub\'s framework brief record, this entry is "\n'
         '                "retired here at the next refresh — the confirmed FRAMEWORKS panel is always "'),
    ]),
    ('scripts/crawl_supplier_site.py', [
        ('"description text (the same rule build_differentiator.py already applies to "',
         '"description text (the same rule the Hub already applies to "'),
    ]),
]
for path, pairs in GEN:
    t = open(path, encoding='utf-8').read(); o = t
    for a, b in pairs:
        t = t.replace(a, b)
    if t != o:
        changes.append((path, '-', 'generator', '', ''))
        if not DRY:
            open(path, 'w', encoding='utf-8').write(t)

import difflib
for c in changes:
    print('[%s] %s :: %s' % c[:3])
    if '--show' in sys.argv and c[0] == 'seed':
        sm = difflib.SequenceMatcher(None, c[3], c[4])
        for op, a1, a2, b1, b2 in sm.get_opcodes():
            if op != 'equal':
                print('    ...%s[-%s-]{+%s+}%s...' % (c[3][max(0,a1-70):a1], c[3][a1:a2], c[4][b1:b2], c[3][a2:a2+50]))
print('changes:', len(changes))
