# One list: supplier, product and speciality vocabulary audit

**Run 06/08/2026.** Audit only. No supplier, product or speciality data was
merged, rewritten or deleted — that needs Lou's sign-off and is a separate job.
The durable output is `check_vocab` in `verify.py`, which fails the publish when
this gets worse.

Every count below was computed from the files in this repo on the date above,
not carried forward from an earlier note.

---

## A. Evidence table

### In this repo (`msh-compare-data`)

| File | Holds | Entries (computed) | Who reads it | Written by |
|---|---|---|---|---|
| `data/supplier-seed.json` | Suppliers, with `aliases`, `specialities`, `products`, `frameworks` | **345** suppliers, **662** distinct name+alias keys | `comparison.js`, `meeting-prep.js`, `company-report.js`; `build_supplier_index.py` | **Hand-edited.** Declared human-owned; the daily build never overwrites it |
| `data/supplier-index.json` | Same shape, seed plus auto-detected award winners / recalls / news | **459** suppliers (345 seed + **114** auto), **94** distinct free-text speciality strings | `supplier-search.js`, `comparison.js`, `meeting-prep.js`, `company-report.js`, `build_search_index.py` | **Auto**, daily 03:15 UTC by `build_supplier_index.py` |
| `data/compare-suppliers.json` | Researched supplier sets, one per speciality | **28** specialities, **255** supplier rows, **196** distinct companies | `comptab.js` (Compare tab) | **Hand-edited.** No automation writes it |
| `data/compare-issues.json` | Recalls / delistings / supply gaps | **18** speciality buckets, **33** distinct notice companies | `comptab.js`, `build_supplier_index.py`, `procurement-view.js` | **Auto, append-only** by `fetch_issues.py` |
| `data/products.json` → `SPECS` | Speciality vocabulary (fills the dropdown on page 1109) | **36** ids | `mst-logic.js` (Stakeholder Mapper), `notice_tags.py`, `verify.py`, market-intel build | Hand-edited |
| `data/products.json` → `P` | Product groups per speciality | **210** | `mst-logic.js` | Hand-edited |
| `data/speciality-map.json` | Canonical speciality list + free-text reconciliation map | **34** canonical ids, **62** `supplierSpecialityMap` entries | `meeting-prep.js`, `company-report.js`, `notice_tags.py` | Hand-edited |
| `data/supplier-products.json` | Verified, speciality-tagged full product ranges | **1** supplier (GBUK Group) of 459 | `meeting-prep.js`, `company-report.js` | Hand-built 20/07/2026 |
| `data/prep-config.json` → `specialities` | Free-text speciality labels | **8** | `comparison.js`, `meeting-prep.js` (fallback only) | Hand-edited; `refresh_trusts.py` writes `trusts`, not this |
| `data/nhssc-cache.json` | NHS Supply Chain catalogue lines | **761** products, **181** top-level `supplier` names, **190** catalogue-entity strings inside `items` | `comparison.js`, `company-report.js` | **Auto**, weekly by `refresh_nhssc_cache.py` |
| `app/comptab.js` line 2 (`var D=`) | Baked fallback so the tab is never empty if the fetch fails | **2** specialities, **17** supplier rows, **18** distinct company strings | The Compare tab, when the fetch fails | Hand-edited |
| `scripts/notice_tags.py` → `SPEC_TERMS` | Speciality tagging regexes | **33** keys | `refresh_fts_contacts.py`, `verify.py`, `build_market_intel.py` | Hand-edited |

### Elsewhere under `Hub/` (found by sweep, not in this repo)

| File | Holds | Entries | Status |
|---|---|---|---|
| `Website/mapper-data/supplier-seed.json` | Suppliers | **335** | Stale fork of the live seed, 10 behind |
| `Website/mapper-data/speciality-map.json` | Specialities | 34 canonical / **60** map entries | Stale fork, 2 behind |
| `Website/mapper-data/products.json` | Specialities + products | `SPECS` **33** (3 behind), `P` 210 | Stale fork |
| `Website/supplier-directory.html` | Suppliers + therapy areas + brands, all inline | **108** suppliers, **96** free-text therapy-area strings | Hand-maintained, entirely outside the seed. No fetch, no build script. Also the Hub's ONLY record of framework **SBS10142** (57 mentions, often with the lot) — that ref appears nowhere in the seed or index |
| `Website/distributors.html` | Distributors | **14** | Hand-maintained |
| `Website/market-share.html` | Suppliers named in prose under 5 speciality panels | ~30 | Hand-maintained |
| `Page-681-FULL-READY-TO-APPLY-6e6f.html` (+2 batch files) | A fourth speciality vocabulary | **20** "REP BRIEF" panel names | Hand-maintained, 3 physical copies |
| `Product-Build/market-intelligence/market-intel-data.json` | Suppliers + specialities from award notices | **315** supplier names, **26** speciality ids | **Auto.** The one consumer that does it right: imports `notice_tags` from this repo, invents no second vocabulary |
| `cloud-pipeline/` — `stories.py`, `rank.py`, `awards_fetch.py`, `atamis_fetch.py`, `event_harvester.py`, `girft-intel.json`, `analysis_refresh.py`, `events_watch.py` | 8 further speciality/clinical keyword vocabularies | 50, 51, ~40, ~55, 10, 44, 8, 13 | All hand-edited, mutually unreconciled. None imports `notice_tags.py` |
| `Product-Build/client-keyword-profiles.json` | Per-client brand keywords | 4 clients, 14–25 terms each | Staging, not imported |
| `IP-Evidence/snapshots/2026-07-31` and `2026-08-03` | Frozen copies of 8 canonical files each | — | Deliberate legal evidence. Correct as-is; do not consolidate |

**Total distinct speciality vocabularies across the Hub: 11 outside this repo,
5 inside it. Total distinct supplier lists: 6 outside, 5 inside.**

---

## B. Drift report

### The headline

Of the **196** distinct companies on the Compare tab, measured against
`supplier-index.json` (459 records, name + alias, using this repo's own
`_norm_co` normaliser):

| | Count |
|---|---|
| Resolve to a supplier record | **123** |
| **Reach no record at all** | **73 (37%)** |

Broken down by what kind of failure it is (rule: exact name; then normalised
alias; then canonical-form equality after stripping legal, geographic and
generic tokens; residue hand-checked against the index one by one):

| | Count | Example |
|---|---|---|
| Exact name match | **60** | `Coloplast` |
| Alias match | **25** | `bd / bard` → `BD — Becton, Dickinson` |
| Same company, different spelling | **67** | `Ambu` vs master `Ambu UK`; `Ansell Healthcare` vs `Ansell` |
| Ambiguous, needs a human | **6** | `Storz Medical UK` (Swiss, separate firm) vs `Karl Storz UK` |
| **Genuinely absent from the master** | **38** | `Alpha Laboratories`, `Bunzl Healthcare`, `Rocialle` |

Note: my split differs from the brief's (60 / 77 / 59). Same 60 exact. The
difference is the master used — the brief measured against `supplier-seed.json`
(345), which gives 57 / 47 variants / 68 unresolved. The apps fetch
`supplier-index.json`, so that is what a member actually experiences, and it is
what the numbers above and the gate use.

### What actually happens to a rep — tested, not theorised

I ran all 196 Compare-tab company names through the **live** `find()` function
from `app/supplier-search.js` (verbatim, executed in JavaScriptCore, against the
real 459-record index):

| Result | Count |
|---|---|
| Exact hit (name or alias) | **91** |
| Substring fallback hit | **42** |
| **"No match … not yet indexed"** | **63** |

So a rep who reads a company on the Compare tab and types it into Supplier
Search gets nothing **63 times out of 196**.

**The substring fallback is worse than the miss, because it is silent.** It
returns the *first* filter hit and searches product lists too. Three confirmed
wrong answers on live data:

- `Becton Dickinson UK` → resolves to a record whose entire **name** is
  `"B Braun, Baxter, Becton Dickinson UK Ltd, CODAN, Fannin, GBUK Group Ltd and
  RPG Medical Ltd"`. `build_supplier_index.py` lifted a notice's whole supplier
  field in as one company. A rep searching BD gets a seven-company sentence
  presented as a company. `RPG Medical` hits the same record.
- `KaVo Dental` → **Dentaquip Ltd**, because Dentaquip's product list contains
  the word "KaVo". Wrong company, no warning.
- `FUJIFILM Sonosite` → **Fujifilm Healthcare UK**, even though a separate
  `FUJIFILM SONOSITE LTD` record exists. The fallback picked the wrong entity.

### Per tool

| Tool | How it matches | Reachability of the 196 Compare-tab names |
|---|---|---|
| **Compare tab** (`comptab.js`) | Dropdown built from `compare-suppliers.json` itself | 196/196 — it is the source |
| **Supplier Search** (`supplier-search.js`) | Free text → exact, then substring on name/alias/**products** | 133 hit (42 of them by substring, ≥3 wrong), **63 miss** |
| **Company Report** (`company-report.js`) | Identical `find()`, over index+seed | Same as above |
| **Meeting Prep** (`meeting-prep.js`) | **Dropdown, exact `s.name === value`.** No free text, no alias | **60 selectable, 136 not** |
| **Product Comparison** (`comparison.js`) | **Dropdown, exact.** Built only from suppliers holding ≥1 product | **57 selectable, 139 not**; 114 master records have no products and never appear |
| **Stakeholder Mapper** (`mst-logic.js`) | **Holds no supplier list at all** — speciality-driven, reaches companies only via notice tagging | n/a |

**Worked example — "Ambu".** The Compare tab lists `Ambu` under endoscopy (and
`Ambu UK` under anaesthesia — two spellings in the same file). Supplier Search
returns the right company, but only via the substring fallback. Meeting Prep and
Product Comparison have no `Ambu` in the dropdown; the rep has to guess it is
filed as `Ambu UK`. The Stakeholder Mapper never names it.

**Worked example — "BD".** Nine distinct strings across five files:

| File | Spellings |
|---|---|
| `supplier-seed.json` / `supplier-index.json` | `BD — Becton, Dickinson` (master, with 8 aliases) |
| `compare-suppliers.json` | `BD / Bard`, `Becton Dickinson (BD)`, `Becton Dickinson U.K.`, `Becton Dickinson UK` |
| `compare-issues.json` | `Bard Access Systems / BD`, `Becton Dickinson`, `Becton Dickinson UK Ltd`, the corrupt seven-company record |
| `app/comptab.js` (baked) | `BD / Bard`, `Bard Access Systems / BD`, `Becton Dickinson`, `Becton Dickinson (BD)` |

The seed's alias list is good enough to catch the four baked spellings. It does
**not** carry `Becton Dickinson UK`, which is why that one lands on the corrupt
record.

### Speciality vocabularies

| Source | Count | Consumer |
|---|---|---|
| `products.json` → `SPECS` | **36** | Stakeholder Mapper dropdown, page 1109 |
| `speciality-map.json` → `canonicalSpecialities` | **34** | Meeting Prep, Company Report |
| `notice_tags.py` → `SPEC_TERMS` | **33** | Notice tagging (already gated ⊆ SPECS by `check_tags`) |
| `compare-suppliers.json` keys | **28** | Compare tab |
| `compare-issues.json` keys | **18** | Compare tab notices |
| `prep-config.json` → `specialities` | **8** free text | Fallback only |
| Free-text `supplier.specialities` strings | **94** distinct | Everything |

Concrete consequences:

- `ultrasound`, `endourology`, `pharma` are selectable in the Stakeholder Mapper
  but are **not canonical**, so Meeting Prep and the Company Report cannot
  reconcile any supplier against them.
- `neonatal` is canonical but **not in SPECS**, so nothing can ever select it.
  `notice_tags.py` already documents this and deliberately omits it.
- `skin-prep` is a live Compare-tab speciality with a researched supplier table
  and is in **neither** SPECS nor the canonical list.
- **5** free-text speciality strings resolve to nothing, including two the
  auto-build wrote: `"Product Match"` and `"Matched to a tracked product"`.
  Also `"vascular"` — a raw id used where a label was expected.
- **100 of 459** supplier records resolve to no canonical speciality at all, so
  they are unreachable from any speciality filter.
- **11** companies are spelled two ways *inside `compare-suppliers.json`
  itself*: `ConvaTec`/`Convatec`, `Vygon (UK)`/`Vygon UK`, `KIMAL`/`Kimal PLC`,
  `ZOLL Medical UK`/`Zoll Medical UK`, and 7 more. The Compare tab renders these
  as separate companies.

### One list that is already clean

`nhssc-cache.json`'s top-level `product.supplier` field holds **181** names and
**all 181** resolve to the master. It is written weekly by
`refresh_nhssc_cache.py`, which keys off the seed. This is proof the discipline
works when a list is derived from the master rather than typed beside it.

---

## C. Proposed single-source design

### Canonical files

**`data/supplier-seed.json` becomes the single supplier record.** It already
has the right shape (`name` + `aliases` + `specialities` + `products` +
`frameworks`), it is already declared human-owned and never auto-overwritten,
and it already carries 662 name/alias keys. Nothing new needs inventing.

**`data/products.json` → `SPECS` becomes the single speciality vocabulary.**
Lou already chose the Mapper's list as canonical on 20/07/2026;
`speciality-map.json` says so in its own `_meta`. The fix is to make
`speciality-map.json` stop holding a *second* list and hold only the
reconciliation map — `canonicalSpecialities` should be derived from `SPECS`, not
maintained beside it.

### How each consumer reads it

| Consumer | Change |
|---|---|
| `comptab.js` | Supplier rows carry `co` **plus a new `ref`** — the master `name`. `co` stays as the display string (the Compare tab legitimately shows "Ambu" where NHSSC does). `ref` is what links to every other tool |
| `supplier-search.js`, `company-report.js` | Resolve `ref` first; keep `find()` for free text, but **drop the product-list arm of the substring fallback** — that is what returned Dentaquip for KaVo |
| `meeting-prep.js`, `comparison.js` | Dropdowns keep using master `name`; add an alias-aware deep link so a Compare-tab `ref` selects the right option |
| `mst-logic.js` | Unchanged. It reads `SPECS` already |
| `notice_tags.py` | Unchanged. Already gated against `SPECS` |

### Alias handling

One rule: **a spelling belongs in exactly one record's `aliases`.** "Ambu" and
"Ambu UK" resolve to one record because "ambu" is an alias of `Ambu UK`, not
because any code guesses. Guessing is what produced the three wrong answers
above. `nhssc-cache.json`'s 190 catalogue-entity strings are the best available
alias source and are already fetched weekly — mine them, do not re-type them.

### Adding a speciality, once

Today it is four edits (`products.json`, `speciality-map.json`, optionally
`compare-suppliers.json`, optionally `notice_tags.py`). After: add to `SPECS`;
everything else derives or is gated.

### Migration order — and what breaks if it is done wrong

1. **Add the gate first.** Done — `check_vocab`. Doing this last means the
   backlog is re-created while it is being cleared.
2. **Derive `canonicalSpecialities` from `SPECS`.** Cheap, 4 ids, no member-
   facing change. Do it before any supplier work, because step 4 needs one
   speciality vocabulary to sort into.
3. **Fix the corrupt `supplier-index.json` record**, then add the guard to
   `build_supplier_index.py` that stops it recurring. **Before** any alias work
   — otherwise aliases get attached to a record that is about to be deleted.
4. **Merge the 67 spelling variants into `aliases`.** Needs Lou's sign-off:
   it changes what members read. Do **not** rename the Compare tab's `co`
   strings — several are the procurement record's own wording and the Compare
   tab is right to show them. Add `ref` instead.
5. **Only then** de-duplicate the 11 internal double-spellings and retire the
   stale `mapper-data/` fork and `supplier-directory.html`.
6. **Last:** research the 38 absent companies (below) and add them properly.

Doing 4 before 3 attaches aliases to a record that then disappears. Doing 5
before 4 removes the second spelling before anything records that it existed,
so the alias can never be added. Doing 6 first is the expensive one with the
least benefit.

### The 38 absent companies — research, do not delete

These reach no record in either master. **Nothing here should be deleted.**
Most look like real UK suppliers nobody has indexed yet; several are obviously
real firms (Owen Mumford, Vitalograph, Welch Allyn, Bunzl Healthcare, Rocialle).
Each needs verifying against its own website or Companies House record before
it is added, per the source-discipline rule.

Alpha Laboratories · BK Medical UK · Beaver Visitec International · Bunzl
Healthcare · Butterfly Network · Cod Beck Blenders · Creo Medical Limited ·
D.O.R.C. · DP Medical Systems · Draeger Medical · Draeger Medical UK · Epredia ·
Esaote · GV Health · Hospital Services Limited · Huntleigh Diagnostics ·
Inspiration Healthcare · Leica Microsystems (UK) · LiteOptics · MIS Healthcare ·
Masimo Europe · Medicare Colgate Ltd (Sterifeed) · NISSHA Medical Technologies ·
Natus Nicolet UK · Otodynamics · Owen Mumford · Pari Medical · Pasante
Healthcare · Puretone · RPG Medical · Reliance Medical · Rocialle · Rocket
Medical · Sakura Finetek UK · Summit Medical UK · Supermax Healthcare ·
Vitalograph · Welch Allyn

(`Draeger Medical` and `Draeger Medical UK` are the same firm, so 37 companies.)

Six more need a human decision rather than research, because a plausible match
exists and may be wrong: `Aquilant Endoscopy`, `HARTMANN`, `Medical Imaging
Systems (MIS Healthcare)`, `Olympus KeyMed`, `Siemens Healthcare`, `Storz
Medical UK`. **Storz Medical and Karl Storz are different companies** — do not
let a fuzzy matcher merge them.

---

## D. The gate

`check_vocab` in `verify.py`, wired into `main()`, six invariants.

### What it catches

1. **A new Compare-tab company name that reaches no supplier record.** FAILs by
   name, using `committed()` to diff against `HEAD`. This is the precise catch —
   counts cannot see it, because swapping one offender for another leaves the
   total unchanged.
2. **The unresolved total rising** above its baseline. The backstop for when
   git history is unavailable, and for drift arriving by deletion from the
   master rather than addition to the Compare tab.
3. **The same company spelled two ways inside `compare-suppliers.json`.**
4. **A speciality added to `products.json` but not the canonical map**, or the
   reverse. This is what makes "add a speciality once" enforceable.
5. **A free-text supplier speciality string that resolves to nothing** — catches
   junk like `"Product Match"` at the moment the auto-build writes it.
6. **A supplier record whose name is a list of companies** rather than a
   company.
7. **`comptab.js`'s baked fallback naming a company the master does not hold.**
   **Hard FAIL, no baseline** — it is 16 names, it is clean today, and it is the
   one supplier list with no way to correct it after publication.

### The ratchet, and why

73 of 196 do not resolve today. Failing on that immediately would block every
push including both scheduled refreshes, so invariants 2–6 carry a baseline in
`VOCAB_BASELINE`:

- number **rises** → **FAIL**, listing the offenders
- number **falls** → **WARN**, asking for the baseline to be lowered
- number **unchanged** → **WARN**, so the backlog stays visible

This is a ratchet, not a loosened check: the numbers can only be edited
downwards. Invariant 1 and invariant 7 fail immediately regardless of any
baseline, so new drift is blocked from today.

```
VOCAB_BASELINE = {
    "compare_unresolved":        73,   # of 196 distinct companies
    "compare_internal_dupes":    11,
    "spec_vocab_mismatch":        4,
    "supplier_spec_unresolved":   5,
    "malformed_supplier_names":   1,
}
```

Each number should reach 0. When one does, delete its entry and make it a hard
FAIL.

### What it deliberately does NOT do

- **It does not judge whether a company is real.** It says "this name reaches no
  record", never "delete it". The 38 absent companies are most likely real
  suppliers nobody has indexed.
- **It does not merge, normalise or rewrite anything.** No data was changed.
- **It does not fuzzy-match.** It uses only the repo's existing `_norm_co`
  (lowercase, strip punctuation and legal suffixes). Anything looser starts
  merging Storz Medical into Karl Storz. Aliases are a human decision, recorded
  in the data, not inferred at gate time.
- **It does not gate the lists outside this repo** — `supplier-directory.html`,
  the `mapper-data/` fork, the cloud-pipeline keyword vocabularies. Those need
  their own gates or, better, retiring.
- **It does not check `nhssc-cache.json`'s catalogue-entity strings.** Those are
  NHS Supply Chain's own legal-entity names, a legitimately different namespace,
  and refreshed from source weekly. Forcing them to match the master would be
  overwriting a procurement record with our own spelling.
