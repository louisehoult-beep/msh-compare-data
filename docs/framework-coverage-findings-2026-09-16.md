# Framework coverage batch — findings, 16/09/2026

Run of the `differentiator-framework-coverage` scheduled task.

## Frameworks investigated but not worked — already blocked, already logged

Ledger regeneration this run gave the same pick order as recent runs: **Insulin Pumps,
CGM & Hybrid Closed Loop** (16.7%), **Digital Diagnostic Solutions** (18.5%),
**Electrodes, Ultrasound Gels, Defibrillation** (18.9%), **Ultrasound Scanners** (19.0%),
**Total Orthopaedic Solutions 3** (19.8%). Radiotherapy Ancillary Devices is deferred
(`^o411`, unchanged, on the decision queue).

- **Insulin Pumps, CGM & Hybrid Closed Loop**: re-confirmed unchanged from 14/09. The 3
  `Left` suppliers (Abbott Laboratories Limited, Medtronic, Urathon Europe Ltd) still have
  no permitted route — Abbott and Medtronic are correctly refused on their own sites and
  publish only NHSSC-catalogue ranges with nothing from this framework's product class
  (the known `^o469` counting pattern); Urathon's crawled range still shows nothing
  matching its curated CGM note. No new investigation needed.
- **Digital Diagnostic Solutions**: already resolved as structurally blocked (`^o422`).
  No new investigation needed.
- **Electrodes, Ultrasound Gels, Defibrillation**: already logged — Electro Spyres
  (`^o434`), Salter Labs UK Ltd queued at decision-queue item 2 (`^o403`). No new
  investigation needed.

## Framework worked (new): Ultrasound Scanners and Associated Options and Related Services

19.0% coverage (4/21 published), 9 `Left`: 6 `publishedElsewhereNeedingCategory`, 1
`heldNeedingCategory`, 2 `needDomain`. First run to look at this framework specifically.

- **The 1 `heldNeedingCategory` supplier, MIS Healthcare, is not fresh work.** Its
  Ultrasound division (24 products) is already correctly mapped to `ultrasound:cart` /
  `ultrasound:port` and published — under the seed's separate "Medical Imaging Systems
  (MIS Healthcare)" record. The framework award list names the supplier "MIS Healthcare",
  which resolves to a *different*, unmerged seed record on the same domain
  (mishealthcare.co.uk). This is the identity question already on record and awaiting
  Lou's ruling: `^o377` (`identityNote` on the "MIS Healthcare" seed record, written
  09/09/2026 — neither record carries a Companies House number, so Lou's standing merge
  rule, a shared CH number or keep separate, cannot resolve it here). Left untouched, per
  the rule against inventing identity decisions.
- **3 of the 6 `publishedElsewhereNeedingCategory` suppliers are genuine dead ends, not a
  counting artefact.** BioSpectrum Ltd's captured range (29 products) is entirely
  Urology/Gynaecology/ENT/General Surgery; Celtic SMR Ltd's (2 products) is X-ray/
  Veterinary; Hologic UK's (4 products, NHSSC-sourced only) is pathology/women's health.
  None has an own-site ultrasound-scanner range to categorise. The other 3 (Philips,
  ProSys International Ltd, Siemens Healthineers) are the `^o469` refused-and-NHSSC-only
  pattern already named there.
- **The 2 `needDomain` suppliers were investigated this run and found their real
  websites, but both refuse on the strong bar.** Web search (not the scripted guesser)
  found:
  - **FUJIFILM Sonosite Ltd** → `sonosite.com/uk`, FUJIFILM's own point-of-care ultrasound
    marketing site for the UK. Read this run (`--candidates-file`, `--fresh`): the site
    never states a company registration number, so it cannot prove against the recorded
    number (04104159). Correct refusal — parent/global-brand site, not a UK-entity page.
  - **Hitachi Medical Systems UK Ltd** → `hitachi-medical-systems.eu`, the Europe-wide arm
    covering the UK. Read this run: same shape, no registration number stated, and this
    supplier has no UK Companies House number on record to check against in the first
    place (`company-financials.json` carries none), so REGISTRATION proof is impossible
    by construction here regardless of what the site says.

  Framework is at its practical coverage ceiling this run: every remaining `Left` item is
  either a pending identity ruling (`^o377`) or a genuine no-route case.

## Framework worked (continued): Total Orthopaedic Solutions 3

19.8% coverage (20/101 published, unchanged), 57 `Left`, 48 `needDomain` — still the
largest such backlog of any framework. Continuing the 14/09 domain-research session
(15 of the then-52 candidates attempted that day: 1 proven — NSK — 14 refused on the
strong bar).

Researched 5 more candidates this run via web search (not the scripted guesser), all
genuinely fresh (none had been tried with these URLs before — checked
`state/domain-seeding-report.json` first to avoid repeating yesterday's exact guesses):

- **Arthro Dynamik Ltd** → `arthrodynamik.com`, a small UK company's own site (confirmed
  by direct search, not a name guess). Read this run: no registration number anywhere on
  the site (home, about, contact, terms, privacy all checked directly) to match the
  recorded 08479540. Genuine, correct refusal — not every small company's site states its
  number, however common practice makes that.
- **Globus Medical UK Ltd** → `globusmedical.com`, the group's global corporate site.
  Refused: no UK-entity registration number stated (matches the 14/09 pattern — a
  US-headquartered device maker's global site, not a UK subsidiary page).
- **Kaiser Medical Technology Ltd** → `kaisermedicaltech.com`, its own dedicated UK site.
  Refused: read in full, states an address and ISO/NHS Supply Chain claims but no company
  registration number.
- **NuVasive UK Ltd** → `nuvasive.com` returns HTTP 403 to automated readers (confirmed by
  direct curl, not a DNS failure) — the site actively blocks the crawl, so nothing can be
  read from it this way.
- **Ortho Solutions UK Ltd** → `orthosol.com`, its own dedicated site (confirmed live,
  HTTP 200). Refused: read in full, no registration number stated anywhere reachable from
  the homepage.

**Cross-framework observation, not acted on.** All 7 real candidate domains found by
proper web research today (5 above + FUJIFILM Sonosite + Hitachi above) were refused on
the strong bar, and every one is a genuine, correctly-identified company website — not a
wrong guess. The common shape is a subsidiary of a large, unambiguous multinational
device company (or a small UK company) whose public site simply never states a company
registration number. `--allow-foreign` doesn't fit (most of these DO have a UK CH number
on record; the gap is the site not stating it, not the absence of a number to check
against). Whether a named, unambiguous global parent should count as a *weaker* but
distinct proof tier of its own — separate from the discredited NAME-tier — is a real
question, but changing what the pipeline accepts as proof is exactly the kind of
blast-radius decision `^o469`'s own writeup already declined to make unattended. Logged
to OUTSTANDING rather than decided here.

Total Orthopaedic Solutions 3 now has 19 confirmed strong-bar refusals on record (14 from
14/09 + 5 today) out of 48 `needDomain`. 29 candidates remain untried this run's session
(Biedermann Motech, Bioventus, Exactech, Future Health Works, Greenbone Spa, Hospital
Innovations, Ideal Med, Innovate Orthopaedics, Lavender Medical, Leda Orthopaedics, Lima
Orthopaedics, M.D.M Medical [liquidation flag, `^o467`, left untouched], Marquardt UK,
Meril UK, Metaphysis LLP, Microport Scientific, Open Medical, OrthoAccess, Orthopediatrics
EU, Permedica UK, Q Medical Technologies, Sovereign Medical, Surgalign UK, Symbios, United
Orthopaedic Corporation UK, Venturis Medical) — left for a future run, per the brief's own
"do not attempt every uncrawled supplier in one run" instruction.

## Coverage movement

No coverage percentage moved this run on either framework worked — every route checked
was a genuine dead end, correctly refused rather than forced. `state/domain-seeding-report.json`
now carries today's 7 checks (dated 16/09) so a future run does not re-research the same
7 domains from scratch. Real forward motion is in what was ruled out, not in what
published.
