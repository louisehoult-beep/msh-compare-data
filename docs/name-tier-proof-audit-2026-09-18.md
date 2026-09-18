# Name-tier "proven" domains — audit, 18/09/2026 (`^o526`)

Raised 17/09/2026: `scripts/seed_supplier_domains.py --accept-name` "proved"
Promed Limited against `promed.com`, a domain-brokerage for-sale page whose
title merely contained the string "PROMED". That one entry was corrected in
place the same day. The open question was **how many of the script's other
name-tier "proven" entries are similarly wrong.**

Answer: **all 20 of them fail the repo's own proof bar, and 4 are demonstrably
a different company.** None had ever been adjudicated, and the tool that does
the adjudicating would have destroyed the existing adjudication if it had been
run. Both are fixed here.

## What the name tier is

`seed_supplier_domains.py`'s own docstring calls it "the weaker proof", accepted
only with `--accept-name`, and says: "DO NOT TRUST THIS TIER... Treat a name
match as a candidate for verify_name_proofs.py, never as a reason to write."
On 14/08/2026 all 128 name proofs then on record were put through
`verify_name_proofs.py`: 4 stood up to registration proof, 124 were REFUSED.
Those 124 verdicts live in `state/name-proof-verification.json` and are read by
`refused_name_proofs()` before every write, and re-stamped into the report by
`_ensure_refused_rows()` on every `--fresh` sweep.

## Finding 1 — the 20 current name-tier rows had never been adjudicated

`state/domain-seeding-report.json` (generated 17/09/2026) carried 20 rows with
`proof: "name"`. **Not one of them appeared in the verdict file** — the 14/08
adjudication covered a different, earlier batch of 128 names, and every name
proof recorded since has sat unadjudicated. `refused_name_proofs()` is keyed on
name, so the safety net did not cover any of these 20: a
`--accept-name --write` run would have seeded all twenty.

`test_seed_domains.py`'s "no title proof is left replayable" check was already
RED on this, and had been since the 11/09–17/09 sweeps produced the rows.

## Finding 2 — re-running the fix would have destroyed the adjudication

`verify_name_proofs.py:main()` rebuilt the verdict file from whatever the
**current** report carries `proof: "name"` for, and wrote `results: res`
straight over `state/name-proof-verification.json`. Run today, against a report
holding 20 name proofs — none of them among the original 128 — it would have
replaced 128 verdicts with 20 and **silently re-opened all 124 refusals for
writing**, including `www.1stop.com` for "1 Stop Medical Supplies" (an IT and
networking reseller).

That is the documented remedy for Finding 1, so the two faults compounded: the
only sanctioned way to clear the 20 was also the way to lose the 124.

Fixed by `merge_verdicts()`: a verdict is an adjudication, added to or
re-adjudicated by a fresh probe of the same supplier, **never dropped because
this run did not happen to look at it**. Six checks in `test_seed_domains.py`
pin it, including one that reproduces the old overwrite behaviour on a fixture
and shows it losing a verdict. The file's three hardcoded counts (124/4/128)
are now pinned to the original rows by their `checked: "2026-08-14"` date and
asserted as floors, so the totals can only grow.

## Finding 3 — the audit result

All 20 were re-probed for registration proof on 18/09/2026. **0 of 20 were
second-sourced**; all 20 are now REFUSED in the verdict file (148 verdicts, 4
verified) and stamped into the report through the script's own
`_ensure_refused_rows()`. `data/supplier-seed.json` was not touched.

Four are demonstrably the **wrong company**, each verified by reading the live
site on 18/09/2026:

| Awarded supplier | Domain guessed | What the site actually is |
|---|---|---|
| Applied Medical UK Ltd (06126148) | `applied.co.uk` | Applied Industrial Systems — a SCADA / industrial control systems integrator |
| Canonbury Products Limited (01703228) | `www.canonbury.co.uk` | "Canonbury — Building Businesses that Last": a firm that buys UK private businesses |
| Change Healthcare | `www.change.co.uk` | "Change" — an ecommerce mentorship community (reg. 9453125, not this supplier) |
| Clarity Pharma (03657934, SIC 46460 pharmaceutical wholesale) | `www.claritypharmaceuticals.com` | Clarity Pharmaceuticals, a clinical-stage radiopharmaceutical company |

A fifth, **Medevolve Limited** (08022604), was guessed at `medevolve.com` — US
revenue-cycle-management software — while the seed already holds the correct
`medevolve.co.uk`. A sixth, **Bariatric Solutions International**, was guessed
at `www.bariatric.co.uk`, which sells NHS bariatric furniture and toilet lifts
and publishes no legal entity at all; the awarded name matches a bariatric
*surgery* device maker. Name-string overlap only, in both cases.

The remainder are the ordinary unproven shape: the site is plausibly the right
company but never publishes the supplier's registration number, so there is no
evidence beyond a title echoing the name the domain was guessed from
(`CHG Meridian UK Limited` → the global group site, the same strong-bar shape
as `^o487`; `Cosium Healthcare` → the French parent's site; and ten others).

## Blast radius: nil today, and that was luck

Of the 20 guesses, **2 domains do appear in `data/supplier-seed.json`** —
Associated Optical Products and Carleton Medical — and **neither got there via
the name tier**. Carleton Medical was proved on 12/09/2026 by Find a Tender
award notice 027424-2026, which records the contractor's registration number
06614929 alongside its internet address; Associated Optical was confirmed
17/09/2026 from the company's own about page. The name-tier row was a
coincidental duplicate of a separately-earned proof in both cases. Their seed
links are unaffected — a REFUSED verdict blocks future writes, it does not
retract an independently proved domain.

The other 18 never reached the seed, because `acceptedNameProof` was `false` on
every run since 14/08. Nothing published wrongly. The exposure was entirely
forward-looking, and is now closed.

## What changed

- `scripts/verify_name_proofs.py` — new `merge_verdicts()`; `main()` merges
  instead of overwriting, and reports carried-forward vs re-adjudicated counts.
- `state/name-proof-verification.json` — 128 → 148 verdicts (4 VERIFIED, 144
  REFUSED). All 128 original rows are present and unchanged; the list is now
  sorted by name, so their order in the file differs.
- `state/domain-seeding-report.json` — the 20 `proof: "name"` rows re-stamped
  as refused rows by `_ensure_refused_rows()`, the script's own writer.
- `test_seed_domains.py` — the 14/08 counts pinned by check date and asserted
  as floors; six new checks on the merge. 33 checks, exit 0.
- `data/supplier-seed.json` — **unchanged**.
