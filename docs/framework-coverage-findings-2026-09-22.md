# Framework coverage findings — 22/09/2026

## Picked framework: Ultrasound Scanners → exhausted, moved down the pick list

Ledger's own pick was **Ultrasound Scanners and Associated Options and Related
Services** (23.8%, 6 left) — re-checked all 6 remaining suppliers
independently and reached the exact same conclusion as
`docs/framework-coverage-findings-2026-09-21-ultrasound-scanners.md` did
yesterday: no permitted route left for any of them (BioSpectrum/Hologic UK
crawled with real, genuinely non-ultrasound catalogues; Philips/Siemens
Healthineers/ProSys International Ltd crawl-refused with only unrelated
NHSSC stub products; Celtic SMR Ltd's genuine SonoScape ultrasound range is
trapped in a CMS component-page structure the mapper can't isolate from
marketing junk without a code change). Same result for **CT Scanners**
(25.0%, 3 left) — checked, same shape.

**New this run:** created `docs/framework-coverage-exhausted.json`, the file
the scheduled-task spec (not the brief) asks for, and recorded both
frameworks in it with the suppliers checked and the reason, so the picker
stops re-selecting either until something about them actually changes. This
matches "A LOW COVERAGE % IS NOT EVIDENCE OF NEGLECT" in
`docs/framework-coverage-brief.md` — three runs (21/09, 21/09 parallel run,
22/09) have now independently confirmed zero permitted movement.

## Moved to Laboratory Diagnostics, Point of Care Testing and Pathology Managed Services

Next on the pick list after excluding the two exhausted frameworks (26.2%,
69 left before this run — the framework's own size means "left" is large in
absolute terms even at a similar percentage).

### Domain hunt for the 59 `needDomain` suppliers

Hand-researched candidate domains for 25 of the 59 (global-manufacturer or
well-known-brand names where a domain guess was plausible), probed one
supplier at a time through `scripts/seed_supplier_domains.py --supplier
"<name>" --candidates-file ... --retry-unproven --allow-foreign` (scoping
per-supplier to avoid re-probing the tool's whole 634-name historical
backlog, which a first, wider `--retry-unproven` attempt without a name
filter tried to do and had to be killed after several minutes with zero
suppliers processed).

**24 of 25 failed the proof bar** — every candidate that answered was either
a parked/for-sale domain (Scientific Laboratory Supplies (SLS)) or a real
site that never prints the UK entity's registration number (DiaSorin, DWK
Life Sciences, ELITech UK, Exact Sciences UK, Genetic Signatures, Helena
Biosciences, Immucor (IBG Immucor), LumiraDx, Nova Biomedical, Promega UK,
Revvity, Twist Bioscience, VWR International (Avantor), Medline Scientific,
Launch Diagnostics, Pro-Lab Diagnostics, Sebia UK, Thriva, Oxford
Biosystems, Sterilab Services, Solmedia Laboratory Supplies, Bruker UK,
Diagnostica Stago UK) — the domain-proof-tier policy's SHAPE exactly (a
global-parent .com/.org site with no UK-subsidiary registration number),
but the address-tier proof that policy allows needs a UK-specific contact
page for each, which none of the generic homepages I tried supplied. Not
pursued further this run — a genuine second-tier proof pass on these would
need each company's actual UK-contact/legal page found first, which is more
research than fits one batch.

**1 of 25 proved: Wolf Laboratories → www.wolflabs.co.uk**, by registration
number (03011929, printed on the site's own contact page). Written to
`data/supplier-seed.json`. Crawl attempted immediately —
**robots.txt disallows automated reading.** Real state change even without
a coverage-percentage move (same pattern as Minitouch on 21/09): the
supplier moved from "no domain on record" to "domain proved, genuinely
attempted, cleanly refused," and now correctly sits in the ledger's
`refused` bucket rather than `needDomain` (69 left → 68).

### The `capturedNothingCounted` supplier: Agilent Technologies UK — genuinely new diagnosis

The ledger has labelled Agilent `capturedNothingCounted` for several runs
with no further detail. This run traced why: **its 58 sampled products
already carry correct, previously-decided category mappings** (22 divisions
mapped to `pathology:histo`/`pathology:equip`/`pathology:consum` —
Immunohistochemistry, Digital Pathology, Clinical Flow Cytometry, Dako
Omnis IHC/ISH reagents, etc. — genuinely clinical-pathology lines, not
Agilent's much larger life-science-research range). They are held not
because the mapping is missing but because `build_differentiator.py`
requires a `sources` entry (a manufacturer detail page or an NHSSC catalogue
match) before anything publishes, and Agilent's original capture was a
sitemap-only "representative sample" with no detail pages fetched.
Ran `scripts/crawl_supplier_product_detail.py --supplier "Agilent
Technologies UK" --domain www.agilent.com` to try to close that gap —
**robots.txt disallows automated reading**, so no detail pages are
reachable. Structural block, matching the Altomed (^o458) / QuidelOrtho
(^o570) shape: correctly mapped, no permitted capture route. No data
change made; not re-flagged to OUTSTANDING since it's the same class of
already-logged issue.

### The other `publishedElsewhere` suppliers — checked, no genuine route

- **Pasante Healthcare** (82 "Uncategorised" products) — checked the actual
  names: the entire real catalogue is condoms and personal lubricant. No
  laboratory-diagnostics product anywhere in it. Left as-is.
- **Coolmed** (medical fridges/freezers/vaccine carriers) and **Sychem**
  (washer-disinfectors, sterilisers, decontamination equipment) — both
  genuine ranges, but neither is a laboratory-diagnostics/pathology product
  by the framework's own vocabulary (`consum`/`histo`/`poct`/`equip`); their
  award on this framework likely covers cold-chain/decontamination lots
  this repo doesn't yet distinguish. Not force-mapped — held correctly, per
  the mixed-division-mapping policy's guard against a dominant-speciality
  assumption.
- **A. Menarini Diagnostics Ltd** (glucomen.co.uk, genuinely a POCT glucose
  brand) — already refused 28/08/2026, still inside the 90-day TTL. **Not
  re-crawled**, per the brief's explicit rule against overturning a
  recorded refusal in passing.
- **Abbott Laboratories Limited** — already understood via the Insulin
  Pumps deferral (^o527): this entity is nutrition-only, so a lab-diagnostics
  catalogue on abbott.co.uk was never expected. Not attempted.
- **Greiner Bio-One Ltd, Henry Schein UK Holdings, Haemonetics** — no domain
  on record (Greiner Bio-One, Henry Schein) or only a generic global
  corporate domain (Haemonetics, same shape as the 24 failed candidates
  above). Left for a future domain-hunt pass rather than guessed.

### Not touched: Kimal Renal Care (Maternity framework)

Noticed in passing while cross-referencing supplier-seed for an unrelated
check — Kimal PLC's own seed record already lists "Renal and dialysis" as a
speciality and "Kflow Epic (haemodialysis catheters)" as a product, strongly
suggesting "Kimal Renal Care" (unresolved on the Maternity, Obstetrics,
Gynaecology and Sexual Health framework) is Kimal PLC's renal division, not
a separate company. **Not investigated further or added as an alias** — it
belongs to a different framework than the one this run worked, and the
brief's rule is one framework per run. Left for whoever picks up Maternity
next; not written to OUTSTANDING since it isn't yet confirmed against a
primary source.

## What moved, in one line

Laboratory Diagnostics: 32/122 published, unchanged; Left 69 → 68 (Wolf
Laboratories: needDomain → refused, genuine state change, no coverage %
move). Ultrasound Scanners and CT Scanners: newly recorded exhausted, no
further work expected without a code or ruling change.
