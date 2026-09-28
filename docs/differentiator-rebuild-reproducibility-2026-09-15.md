# Is `build_differentiator.py` reproducible? — tested 15/09/2026 (`^o468`)

`^o468`, raised 14/09/2026, said: "build_differentiator.py loses the same 5 NHSSC-only records
every run on 2 separate fresh clones (ICC/NHSSC join?), unrelated to what changed. Blocks safe
rebuilds."

**It does not reproduce, and the build cannot behave that way.** Tested 15/09/2026 by the
`outstanding-sweep` task. Everything below was run from throwaway clones taken with
`./begin.sh`, never the shared checkout.

## What was run

1. **Fresh clone of `main` (`700d901`), rebuild.** `python3 scripts/build_differentiator.py`
   → 34,858 published / 48,745 held, exactly the committed counts. Compared product by product
   against the committed `data/differentiator.json` on `(supplier, name, division)`: **0 lost,
   0 gained**, and the two `products` lists are identical *as ordered lists*, not merely as
   sets. `held` likewise identical. The only difference in the whole file was `_notice`, which
   the build replaces with its generated placeholder.
2. **Then `python3 scripts/stamp_notice.py`.** `git diff --quiet data/differentiator.json` →
   **byte-for-byte identical to the committed file.** This is exactly the order
   `.github/workflows/differentiator.yml` uses (build → stamp → gate), and the workflow's own
   comment says the build "writes a fresh file every run, so it drops the ownership notice
   every run". Dropping the notice is expected behaviour, caught by `verify.py`'s
   `check_notice()`, whose stated fix is that same stamper.
3. **A second, independent fresh clone**, same two steps: identical to the committed file
   again.
4. **Four commits from 14/09** — `9056306` (the 14/09 rebuild), `5928689`, `b8f3f79`,
   `eda52d3` (that evening's HEAD) — rebuilt at each: 34,617 → 34,617 every time, **0 lost, 0
   gained** at each one. So the symptom does not reproduce even at the state it was reported
   against.
5. **Three different `PYTHONHASHSEED` values** (1, 2, 12345) on current `main`: identical MD5
   all three times. Set iteration order does not reach the output.

## Why it cannot be non-deterministic

`scripts/build_differentiator.py` reads no clock, no randomness and no network: a `grep` for
`date`, `today`, `now()`, `utcnow` and `time.` finds only prose in comments. The workflow
header already describes it as "a PURE DERIVATION" of four files in the repo. Its output is a
function of its inputs, so two runs on the same inputs cannot differ — and three hash seeds
confirm it empirically.

## What a future delta actually means

If a rebuild ever changes the record count again, the correct reading is **the committed file
was stale relative to its inputs** — someone landed a seed, category-map or capture change
without rebuilding — and the rebuild is the fix, not the fault. That is what the build is for.
It is not evidence of a non-deterministic build, and it is not a reason to avoid rebuilding.

The 14/09 observation's own cause could not be reconstructed from the record (no detail file
was written for `^o468`, and the clones it was seen in are gone). Rather than invent one, this
note states what was tested and what it showed.

## A second occurrence, 27/09/2026 (`^o623`)

Moved out of `OUTSTANDING.md` 28/09/2026 (over the 400-char line limit) by
`out-of-hours-backlog-clearer` — content unchanged, just relocated.

A fresh `build_differentiator.py` run (framework-coverage batch, Surgical
Instruments/Decree Thermo, no source-data change intended beyond that supplier's seed
record) dropped 11 NHSSC-catalogue-only product records present in the committed
`data/differentiator.json`, all unrelated to the batch's own edit (BD / LIFESTENT, Cook
Medical / HCTED ZENITH TX2 + CMD, Essity / TENA range x7, Kimal PLC / Altius Pro+ x2).
`land.sh`'s record-level no-loss check caught it and the rebuild was reverted rather than
published — only the seed/refusal fix and a ledger-only regen landed.

This directly contradicts the "cannot be non-deterministic" finding above (no clock, no
randomness, no network read by the build script itself) — unless the true cause is one
step earlier than the build: something the build reads (an NHSSC catalogue cache file,
per this item's own leading suspicion of "a live NHSSC catalogue fetch returning
different rows between runs") changing between the two runs, which `build_differentiator.py`
would then deterministically reflect. Not yet investigated to a conclusion — left open,
not resolved by assumption.

**RECOMMEND:** investigate why two consecutive `build_differentiator.py` runs against the
same committed inputs produced a different NHSSC-catalogue product set, starting from
whether `data/nhssc-cache.json` (or any other input the build reads but does not commit
alongside its own output) actually changed between the two runs.
