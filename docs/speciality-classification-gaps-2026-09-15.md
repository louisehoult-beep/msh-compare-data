# Speciality classification gaps found 15/09/2026

Found while fixing the Patient Moving and Handling (`therapies-physio-and-ot`) ICES/community
equipment mistagging (commit `bf6e5ae`). A follow-up sweep checked every row of
`data/tender-history.json` and every award in `data/framework-awards.json` against every
speciality's `include` regex in `scripts/build_speciality_panels.py`, looking for genuine
clinical/device awards that match none of the 43 rules. Most of the ~1,900 unmatched rows are
correctly excluded (IT, catering, estates, dental, or genuinely cross-speciality-ambiguous titles
already deliberately left out — this file's own exclusion notes cover them). Three real gaps
survived that check. None have been fixed yet — logged for a future attended session, per Lou's
15/09/2026 instruction to log rather than fix in this session.

## 1. Breast biopsy / localisation devices — claimed by no speciality (8 rows)

- "Breast Biopsy Needle NPM" — Gloucestershire Hospitals NHS Foundation Trust
- "Purchase of Vacuum Assisted Biopsy" — Leeds Teaching Hospitals NHS Trust
- "RFL - NLBSS ECH - Consumable contract for Mammotome Revolve Vacuum Biopsy System" (×2) —
  Royal Free London NHS Foundation Trust
- "Provision of 2 Sentimag System & Supply" — Swansea Bay UHB
- "Sentimag systems consumable contract" — Somerset NHS FT
- "Sentimag Gen 3 system" — Norfolk and Norwich University Hospitals NHS FT
- "National Framework Agreement for Non-Wire Lesion Localisation and Sentinel Lymph Node
  Location Products" — Countess of Chester Hospital NHS FT

Likely home: `radiology-and-imaging` or `oncology-and-sact` — both already discuss and
deliberately reject bare "biopsy"/"breast" as too noisy, but neither carries a qualified term for
these named breast-cancer-specific device classes. Candidate missing terms: `mammotome`,
`sentimag`, `vacuum[- ]assisted biopsy`, `lesion localisation`, `sentinel lymph node`. Needs a
ruling on which speciality claims it (or both, if genuinely shared) before any regex change,
per this file's own rule 14 discipline — every hit must be read and false positives excluded
before the term goes in.

## 2. Ophthalmology's `retinal` term has a silent word-boundary gap

"MEH - PRIMA Subretinal Photovoltaic Implant System" (Moorfields Eye Hospital NHS FT) is not
matched. `ophthalmology`'s include list has `retina|retinal`, wrapped in a leading `\b`, so it
requires a word boundary immediately before "retinal" — "sub**retinal**" has no such boundary
(the match position is mid-word) and fails. Confirmed by direct regex test. Fix is narrow: add
`subretinal` explicitly, or restructure the boundary so `\w*retinal` is admitted without loosening
anything else — needs checking against the rest of the include list for unintended side effects
before landing.

## 3. Hypoglossal nerve stimulation device — no ENT term, and the source title is misspelled

"C461007 - Hyperglossal Nerve Stimulation Device" — Bradford Teaching Hospitals NHS FT.
`pain-management`'s own comments already identify hypoglossal nerve stimulators (Inspire, Nyxoah)
as ENT sleep-apnoea devices, not pain products, but `ent-and-head-and-neck` has no `hypoglossal`
term to catch them. Separately, this specific row's title is misspelled "Hyperglossal" in the
source data (likely an upstream data-entry error at the buyer or portal, not a Hub transcription
error) — adding `hypoglossal` to ENT's include list will not catch this exact row on its own; it
would need either a second variant term or a manual title correction, and the misspelling should
probably be verified against the original notice before deciding which.

## Method, for reproducibility

A throwaway script (not committed) imported `SPECIALITY_RULES` from
`scripts/build_speciality_panels.py`, compiled every `include`/`exclude` regex, and tested every
title in both award feeds against all 43 rules. 896 tender-history rows and 1,037 framework-awards
entries matched no speciality; each clinically-flavoured hit was read individually and checked
against that speciality's existing exclusion reasoning before being ruled in or out as a genuine
gap. Only the three above survived that read.
