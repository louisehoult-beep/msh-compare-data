# Framework coverage findings — 16/09/2026, second run of the day

Picker's list (16.7%–20.8%) checked in order: Insulin Pumps/CGM, Digital Diagnostic
Solutions, Electrodes/Ultrasound Gels and Total Orthopaedic Solutions 3 were all already
worked earlier today (see `framework-coverage-findings-2026-09-16.md` and OUTSTANDING
^o422) — re-confirmed as exhausted rather than re-worked, per the brief's warning that a
low coverage % is frequently "finished", not neglected.

## Ultrasound Scanners and Associated Options and Related Services — new checks

Two of the six `publishedElsewhereNeedingCategory` suppliers hadn't been individually
checked before. Both confirmed genuinely unrelated, not miscategorised:

- **Hologic UK** (95 products crawled 08/09) — entirely mammography, molecular/PCR
  assays, breast biopsy systems and women's health devices. No ultrasound scanner among
  them.
- **Celtic SMR Ltd** (164 products crawled 22/08) — its "Healthcare" division is mobile/
  portable X-ray (DR/CR systems, generators), matching its actual award ("Mobile X-Ray
  Systems"). Not an ultrasound maker.

The remaining three (`BioSpectrum Ltd` — ^o290; `Philips`, `Siemens Healthineers` —
already refused and recorded) and the framework's 2 `needDomain` suppliers (FUJIFILM
Sonosite — ^o363; Hitachi Medical Systems UK — already noted on its own seed record as a
likely Fujifilm Healthcare UK duplicate awaiting a merge ruling) were already flagged.
This framework has no further permitted route today.

## Total Orthopaedic Solutions 3 — domain-proof pattern reconfirmed on 2 more names

Manually checked (not just re-running the automated guesser) two suppliers with existing
Companies House candidate numbers: **Microport Scientific Ltd** (08641910) — microport.uk
states "UK 013158B", not 08641910, no match; **Medartis Ltd** (04604437) — medartis.com's
own Imprint page states only the Swiss parent's CHE number, never the UK number. Same
shape as OUTSTANDING's existing "domain-proof strong bar" note (line ~18): both are real
subsidiary-of-global-parent sites, correctly refused because the site never states the UK
entity's own number. Added to that existing pattern rather than raising a new item.

## Laboratory Diagnostics, Point of Care Testing and Pathology Managed Services — 2 fresh crawls

**QuidelOrtho (Ortho Clinical Diagnostics UK)** — domain `quidelortho.com` already on
file, never crawled. Crawled 322 products across 15 divisions (Microvue Assays, Vitros
Systems, Sofia Platform, Quickvue Rapid Lateral Flow Tests, Solana/Savanna molecular
platforms, Triage Meter Pro, Lyra Assays, D3 Products, etc.).

**PHC Europe / PHCbi** — domain `phchd.com` already on file, never crawled. Crawled 14
products across 3 divisions.

Both are clearly laboratory-diagnostics/POCT companies, but individual division→category
mapping wasn't made here — several of the named platforms (e.g. Sofia, Vitros, Solana)
are recognisable as specific IVD product types, but that's product-line knowledge, not a
primary source read against this file's evidence bar, so the 18 new (supplier, division)
pairs were registered unmapped via `union_differentiator_pairs.py --apply` (`hub: null`),
matching this morning's Salter Labs precedent. Ledger effect: both move from `needDomain`
to `heldOnly` — real progress, no forced categorisation. Queued for a ruling in
OUTSTANDING.

## Recommendation

Laboratory Diagnostics' QuidelOrtho/PHC Europe divisions are ready for the same
product-level mapping pass recommended for Salter Labs/Electro Spyres — plausible mapping,
not made here: Vitros Systems/Nulexa System → pathology:equip; Microvue/Lyra/D3/Thyretain
assays and Readycells → pathology:consum; Quickvue/Sofia/Solana/Savanna/Triage Meter Pro
(point-of-care platforms) → pathology:poct.
