# Framework coverage batch brief — for the msh-compare-data repo

Written 03/09/2026, for the recurring framework-coverage cloud routine. Read this in full
before doing anything.

## What "coverage" means

`data/differentiator.json` publishes products by category; `scripts/build_coverage_ledger.py`
(run it fresh each time you start — the ledger goes stale as fast as the differentiator and
the supplier seed do) answers, framework by framework: which awarded suppliers are in the
Hub's supplier index, which of those publish at least one categorised product, which have
products crawled but HELD (uncategorised), and which have nothing crawled at all. A framework
is DONE only when every awarded supplier publishes. **0 of 121 frameworks are done; ~45 are
STARTED (partial coverage); the rest are not started.**

## Your job this run

1. Run `python3 scripts/build_coverage_ledger.py` to regenerate `data/coverage-ledger.json`
   and `docs/COVERAGE-LEDGER.md` fresh.
2. Read `docs/COVERAGE-LEDGER.md`. Pick the framework with the **lowest coverage % that is
   STARTED AND HAS A NON-ZERO `Left` COLUMN** (not zero awarded suppliers, not already DONE).
   `Left` is the ledger's count of work genuinely still available — unresolved names + held
   suppliers + crawlable suppliers + suppliers needing a website. The ledger's tail also
   prints "Lowest-coverage STARTED frameworks that still have work left", which is exactly
   this pick, already made. If everything is DONE, or every remaining framework is NOT_STARTED
   for a structural reason (UNMAPPED — no Hub speciality claims it as a buying route — or
   every awarded supplier forbids crawling), stop and report that rather than picking one.

   **A LOW COVERAGE % IS NOT EVIDENCE OF NEGLECT.** Added 06/09/2026 after a run picked
   Digital Diagnostic Solutions on 11.1% and re-crawled 34 suppliers that had all been read
   and refused the day before. Read the `Refused` column with the coverage: those suppliers
   were answered, and re-crawling them DELETES the recorded reason, because
   crawl_supplier_site.py only applies its refusal TTL on the `--auto` path and not to an
   explicitly named `--supplier` (OUTSTANDING ^o312). The lowest-coverage framework is
   frequently the most finished one — there is simply no permitted route to the rest of it.
3. For that framework, read `data/coverage-ledger.json`'s entry for it: it names every
   awarded supplier and which state each is in (published / held / uncrawled / unresolved /
   not-in-index).
4. Work through its suppliers in this priority order:
   - **Unresolved supplier names first.** A name that won't resolve through
     `company-aliases/company_alias.py` needs a human decision (rule 10 of
     `docs/HUB-VERIFICATION-STANDARD.md`) — do not guess. If you can confirm the real company
     from a primary source (the company's own site, a procurement listing naming the legal
     entity), add the resolution to `company-aliases/alias-overlay.json` in its documented
     format (canonical, variants, reason, evidence, addedOn). If you cannot confirm it, leave
     it unresolved and note it in your report — never fuzzy-match.
   - **Suppliers not yet in `data/supplier-seed.json` at all.** Add a minimal record (name,
     framework award) if you can confirm identity from a primary source; no company number
     unless it comes from a recorded source (rule 11). If identity itself can't be confirmed,
     leave it and note it.
   - **NEVER re-crawl a supplier listed in the framework's `refusedSuppliers`.** That
     supplier was read on the recorded date and refused for the recorded reason; a re-crawl
     silently overwrites that judgement with whatever the site returns today, which is how
     three considered refusals (Clinisys, Hermes Medical Solutions, Magentus) were destroyed
     on 06/09/2026 and had to be reverted. If you genuinely believe a refusal is stale, say so
     in your report and leave it — do not overturn it in passing.
   - **Suppliers in the seed but never crawled**, or with **HELD (uncategorised) products.**
     Run `scripts/crawl_supplier_site.py --supplier "<name>" --domain <domain>` (find the
     domain in `data/supplier-seed.json`) to get their product range, then check whether
     `scripts/build_differentiator.py`'s category mapping picks them up. If a supplier's
     products are held because their division/category isn't mapped in
     `data/differentiator-category-map.json`, that is a genuine unmapped-vocabulary gap, not
     something to force — note it rather than inventing a category.
   - **Do not attempt every unresolved/uncrawled supplier in one run.** Work through as many
     as fit in a reasonable session; leave the rest for the next run (the ledger will show
     the same framework as the lowest-coverage one again next time if it's still worth
     prioritising, or another one will surface).
5. After making changes, run `python3 scripts/build_differentiator.py` to rebuild
   `data/differentiator.json`, then `python3 scripts/stamp_notice.py` (build_differentiator.py
   does not preserve the file's ownership notice — this is a known step, not optional), then
   re-run `python3 scripts/build_coverage_ledger.py` to see the actual coverage change for
   the framework you worked.

## Hard rules, non-negotiable

- **You may propose a finding; you may never invent a decision and attribute it to Lou.**
  If something is a genuine judgement call (an ambiguous company identity, a vocabulary gap
  that needs a ruling, anything you're not certain of), write it into `OUTSTANDING.md` at the
  repo root as a new item, dated, and move on. Do NOT decide it yourself and write it into the
  data as if it were settled, and never claim she made a ruling she did not make. This exact
  failure happened once already in this repo's history (a retired task published a commit
  falsely attributing a vocabulary ruling to Lou) — it is the reason this routine has this
  rule spelled out explicitly rather than assumed.
- **Never fuzzy-match a company name or guess a company number.** Rules 10 and 11 of
  `docs/HUB-VERIFICATION-STANDARD.md` are binding. Publishing nothing (for the specific
  unconfirmed field) beats publishing a wrong company.
- **A slice is not a range.** If a crawl hits a page cap or time budget, say so plainly
  (supplier, how much of the declared total was read) rather than letting it read as complete.
- **Gate before publish.** Run `python3 verify.py` and it must exit 0 before you commit.
- **Start with `./begin.sh "framework-coverage-<short-name>"`**, which hands you your own
  throwaway clone (prints its path) — edit there, never in the shared checkout.
- **Land with `./land.sh "subject" <paths>`** from inside that clone, naming only the files
  you actually changed. It gates, commits, rebases and pushes for you, retrying on its own
  if a peer landed first, and deletes the clone once it has landed.
  If it reports a rejected push, follow its own recovery instructions (fetch, rebase, re-gate,
  push again) — never force push, never hand-resolve a generated JSON file's conflict by hand.
- **Do not touch other suppliers' or frameworks' data** beyond the one framework you picked
  this run — a batch that touches everything touches nothing carefully.

## Stop condition

If `docs/COVERAGE-LEDGER.md` shows all 121 frameworks DONE, or every remaining
non-DONE framework is blocked for a structural reason named in the ledger (UNMAPPED,
every awarded supplier robots.txt-forbidden, etc. — the "honest definition of done" is
"every awarded supplier reachable by a permitted route", not literal 100%), make no
changes and report that framework coverage work is complete or blocked, listing which
frameworks remain and why.
