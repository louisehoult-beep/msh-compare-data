#!/usr/bin/env python3
"""Which of a rep's specialities a procurement notice title is about.

WHY THIS EXISTS
The Stakeholder Mapper holds ~1,400 named NHS contacts harvested from Find a
Tender. Until 27/07/2026 the panel showed the 12 most recent names at the
selected trust, unsorted. Measured across the whole index, roughly one notice
title in eleven is about a clinical or medical product; the rest are IT,
estates, catering, recruitment, legal and so on. So a vascular access rep
opening Somerset was shown the person who ran a datacentre rack tender. The
names were real and the sourcing was sound — they were simply the wrong people.

WHAT THIS DOES, AND THE RULE IT WORKS UNDER (stated here and shipped in the
data file, so a member can judge it — root constitution rule 14)
Each contact carries the title of the notice they were named on. This tags that
TITLE, and nothing else:

  spec : canonical speciality ids whose vocabulary appears in the title
  cls  : 'clinical'    — the title is about a clinical or medical product,
                         service or device
         'nonclinical' — the title is plainly about something else entirely
                         (IT, estates, catering, recruitment, legal, transport)
         'unclear'     — neither vocabulary fires. The honest majority.

⚠️ WHAT A TAG DOES NOT MEAN. It does NOT mean this person buys that category,
holds that remit, or is the right contact for it. Find a Tender carries no
job-title field. All a tag says is: this person was named as the enquiry
contact on a notice whose TITLE matches your area. That is a reason to make
contact, which is all the Hub ever claimed for these names.

⚠️ AND 'unclear' IS NOT 'IRRELEVANT'. Notice titles are short, and many are
internal reference codes ("IT454", "UHL_A_Neurophysiology_2628.V.0.1"). A title
that matches nothing is a limitation of the title, not a verdict on the person.
The UI must never present an untagged contact as "not relevant to you" — it
sorts, it does not hide.

EVIDENCE FLOOR (rule 14c). A speciality tag fires only on a term specific
enough that its presence in a title is not plausibly about something else.
Bare 'care', 'supplies', 'equipment', 'services', 'management' and 'systems'
are deliberately absent: they appear in half the estate's tenders. Where a
term is ambiguous across two specialities it is listed under both rather than
arbitrated — a rep seeing one extra name costs nothing, a rep missing the
right one costs the account.

⚠️ KEYS MUST BE SELECTABLE. Every id below has to exist in products.json →
SPECS, which is what fills the speciality dropdown on page 1109. A tag for a
speciality no member can pick is invisible work. 'neonatal' is deliberately
absent for that reason: it is in speciality-map.json's canonical list but not
in SPECS, so nothing would ever match it. verify.py fails the publish if this
drifts.

Stdlib only. Imported by refresh_fts_contacts.py and by verify.py, so the
vocabulary that tags the data is the same one the gate re-derives it from.
"""
import re

# ---------------------------------------------------------------------------
# SPECIALITY VOCABULARY
# Keys are speciality ids from data/products.json → SPECS (the live dropdown).
# ---------------------------------------------------------------------------
SPEC_TERMS = {
    'vascular': r"vascular access|midline|picc|cannula|venepuncture|central venous|"
                r"\bcvc\b|port-?a-?cath|intravenous cathet|iv cathet|infusion set|"
                r"\bvad\b|arterial line",
    # 'bladder' on its own is not enough — it appears in oncology and genomics
    # notices ("At Home Bladder Cancer Genome Testing") that no continence rep
    # would thank you for.
    'continence': r"continence|urolog|catheter valve|urinary cathet|intermittent cathet|"
                  r"foley|urine drainage|bladder (scan|irrigat|management|care)|incontinence",
    # 'stoma' MUST stay word-bounded: unbounded it matches "stomach", which on
    # 30/07/2026 filed an Allurion gastric balloon safety notice under ostomy.
    # 'ostomy' already covers colostomy / ileostomy / urostomy as substrings.
    'ostomy': r"ostomy|\bstomas?\b|colostomy|ileostomy|urostomy",
    'bloodcoll': r"phlebotomy|blood sampling|blood collection|venous blood|vacutainer|lancet",
    'wound': r"wound care|wound management|wound dressing|\bdressings?\b|tissue viability|"
             r"negative pressure wound|\bnpwt\b|pressure ulcer|wound closure|sutur|"
             r"compression bandag",
    'cardiology': r"cardiolog|cardiac|\becg\b|\becho(cardio)|pacemaker|defibrillat|"
                  r"cath lab|coronary|electrophysiolog|\bicd\b|stent",
    'diabetes': r"diabet|insulin|glucose monitor|\bcgm\b|blood glucose|hba1c",
    'endoscopy': r"endoscop|colonoscop|gastroscop|bronchoscop|cystoscop|scope reprocess",
    'respiratory': r"respirator|ventilat|oxygen therapy|\bcpap\b|\bnippv\b|nebulis|"
                   r"spiromet|humidificat|tracheostom",
    'theatres': r"theatre|surgical instrument|procedure pack|surgical drape|operating table|"
                r"laparoscop|electrosurg|diatherm|surgical consumable|\bsutures?\b",
    'handling': r"moving and handling|patient hoist|\bhoists?\b|patient transfer|"
                r"bariatric equipment|\bmattress(es)?\b|hospital bed|\bbeds? and\b|"
                r"pressure relieving",
    'ent': r"\bent\b|otolaryngo|tympan|audiolog(y|ical) surg|nasal endoscop|laryng",
    'ophthalmology': r"ophthalm|intraocular|cataract|optometr|\bretina|vitreoretin|slit lamp",
    'ortho': r"orthopaed|orthopedic|arthroplast|\bhip and knee\b|knee replacement|"
             r"hip replacement|trauma implant|spinal implant|casting material|\bplaster of paris\b",
    'gastro': r"gastroenterolog|\bcolorectal\b|bowel screening|\bhepatolog",
    'renal': r"\brenal\b|dialys|haemofiltrat|nephrolog",
    'womens': r"maternity|obstetric|gynaecolog|midwif|neonatal screening|contracepti|"
              r"breast screening|cervical screening",
    'neuro': r"neurosurg|neurolog|neurophysiolog|\beeg\b|spinal cord stimul",
    'anaesthesia': r"anaesthe|airway management|laryngoscop|critical care consumable|"
                   r"\bicu\b consumable|intensive care equipment",
    'imaging': r"radiolog|radiograph|\bmri\b|\bct scan|computed tomograph|ultrasound|"
               r"\bx-?ray\b|mammograph|nuclear medicine|contrast media|radiotherap|\bpacs\b",
    'oncology': r"oncolog|chemotherap|cytotoxic|\bhaemato-?oncolog|brachytherap|"
                r"malignant disease",
    'nutrition': r"enteral feed|parenteral nutrition|clinical nutrition|nasogastric|"
                 r"\bpeg\b feed|oral nutritional supplement|\bdietetic",
    'audiology': r"audiolog|hearing aid|cochlear|\baudiometr",
    'dental': r"\bdental\b|maxillofacial|orthodontic|\bdentist",
    # Bare 'decontamination' belongs to sterile services, not infection control,
    # and also catches emergency-preparedness kit ("Decontamination Shelters
    # EPRR") that is neither. Infection fires only on room/surface decon.
    'infection': r"infection prevention|infection control|\bipc\b|"
                 r"(hpv|room|surface|hydrogen peroxide) decontaminat|"
                 r"examination glove|\bppe\b|personal protective equipment|"
                 r"hand hygiene|sterilis(ation|ing) (pouch|wrap|packag)|antimicrobial",
    'pathology': r"patholog|laborator(y|ies)|\bhisto(patholog|log)|cytolog|microbiolog|"
                 r"\breagents?\b|specimen|\bassays?\b|blood science",
    'rehab': r"rehabilitat|physiotherap|occupational therap|wheelchair|walking aid|"
             r"prosthe(tic|sis)|\borthotic",
    'orthotics': r"\borthotic|prosthe(tic|sis)|\bfootwear\b|spinal support|"
                 r"\bbraces\b|(knee|back|spinal|ankle) brace",
    'ssd': r"sterile services|decontamination (unit|service|equipment)|\bssd\b|"
           r"autoclave|washer disinfector|endoscope reprocess",
    'monitoring': r"patient monitor|vital signs|pulse oximet|blood pressure monitor|"
                  r"\bnibp\b|telemetry monitor|cardiac monitor",
    'bloodtx': r"transfusion|blood product|blood bank|\bhaemovigilance",
    'digital': r"electronic patient record|\bepr\b|clinical system|\bpacs\b|"
               r"digital health|patient portal|\bnhs app\b|clinical software",
    'dermatology': r"dermatolog|\bskin (care|health|integrity)|phototherap",
}

# ---------------------------------------------------------------------------
# CLASS VOCABULARY
# 'clinical' fires on a term that only appears when a notice is about care or a
# medical product. 'nonclinical' fires on the estate, back office and corporate
# spend that dominates NHS tendering. Anything matching a speciality above is
# clinical by definition, so this list only has to catch the clinical notices
# that no single speciality claims.
# ---------------------------------------------------------------------------
CLINICAL_TERMS = re.compile(
    r"clinical|medical device|medical equipment|medicines?\b|pharmac|patient|"
    r"nursing|\bnurse|surg|diagnostic|therap|treatment|ward\b|hospital bed|"
    r"consumables? (for|-)|healthcare (product|consumable)|screening programme|"
    r"community health|mental health service|\bgp\b practice|primary care service|"
    r"\bmedical\b|\bhealthcare\b", re.I)

NONCLINICAL_TERMS = re.compile(
    r"datacentre|data centre|\bict\b|\bit\b (service|support|equipment|hardware|"
    r"infrastructure|contract)|software licen|network infrastructure|telephony|"
    r"cyber ?security|\bestates?\b|facilit(y|ies) management|catering|cleaning|"
    r"laundry|linen|portering|security service|car park|\bwaste\b|grounds "
    r"maintenance|landscap|construction|refurbish|\bfire (safety|alarm|door)|"
    r"asbestos|window|roofing|\blifts?\b (maintenance|replacement)|energy|utilit|"
    r"boiler|\bhvac\b|air conditioning|insurance|internal audit|external audit|"
    r"legal service|\bcounsel\b|recruitment|\bagency (staff|worker|nursing)|"
    r"advertis|marketing|translation|interpret(ing|ation)|\btaxi\b|patient transport|"
    r"courier|fleet|vehicle|stationery|print(ing|ed) service|furniture|"
    r"payroll|finance system|\bhr\b (system|service)|occupational health service|"
    r"training (course|provider|programme)|consultancy|architect|quantity survey|"
    r"\bbank\b (staff|account)|uniform|\bsignage\b", re.I)


def tag(title):
    """Tag one notice title. Returns (spec_ids, cls).

    Order matters: a speciality match makes it clinical whatever else the title
    says, because 'Endoscope decontamination unit refurbishment' is a theatre
    rep's notice even though it also mentions building work.
    """
    t = (title or '').strip()
    if not t:
        return [], 'unclear'
    specs = sorted(k for k, pat in SPEC_TERMS.items() if re.search(pat, t, re.I))
    if specs:
        return specs, 'clinical'
    if CLINICAL_TERMS.search(t):
        return [], 'clinical'
    if NONCLINICAL_TERMS.search(t):
        return [], 'nonclinical'
    return [], 'unclear'


# The rule, in the words the Hub shows a member. Shipped in the data file so the
# claim never travels without the basis for it.
RULE = ("Tagged by matching the wording of the notice title against a fixed "
        "vocabulary per speciality. A tag means only that this person was named "
        "as the enquiry contact on a notice whose title matches your area — Find "
        "a Tender carries no job title, so it is not evidence of their remit. "
        "A notice with no tag is usually a short or coded title, not an "
        "irrelevant one.")

if __name__ == '__main__':
    import json, sys, collections
    store = json.load(open('data/trust-contacts.json'))
    counts = collections.Counter()
    spec_counts = collections.Counter()
    samples = collections.defaultdict(list)
    for code, entries in store['trusts'].items():
        for e in entries:
            s, c = tag(e.get('notice'))
            counts[c] += 1
            for x in s:
                spec_counts[x] += 1
                if len(samples[x]) < 4:
                    samples[x].append(e.get('notice'))
    total = sum(counts.values())
    print('%d contacts: %s' % (total, dict(counts)))
    print('\nspeciality hits:')
    for k, v in spec_counts.most_common():
        print('  %-13s %3d   e.g. %s' % (k, v, ' | '.join(x[:52] for x in samples[k][:2])))
    if '-v' in sys.argv:
        for code, entries in store['trusts'].items():
            for e in entries:
                s, c = tag(e.get('notice'))
                if c == 'unclear':
                    print('UNCLEAR:', (e.get('notice') or '')[:100])
