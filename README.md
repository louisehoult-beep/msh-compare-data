# msh-compare-data

Weekly-refreshed "live issues" data (recalls, delistings, supply gaps) for the
Medical Sales Hub **Compare vs Competitors** tab on elevateandthrive.uk
(WP page 1109). The page fetches `data/compare-issues.json` at load time and
falls back to its built-in snapshot if this repo is unreachable.

## The one rule: APPEND-ONLY
Automation only **adds** items (`autoDetected: true`, `use: ""`). It never
edits or removes existing entries. The `use` field - the "what this means for
a rep" tactical line - is **human-curated intelligence and must never be
written by automation**. To add or edit a tactical line, edit
`data/compare-issues.json` here on GitHub and commit.

## Sources
- MHRA medical safety alerts - official GOV.UK search API (FSN round-up detail
  pages are fetched so keyword matching sees the actual notices).
- NHS Supply Chain customer notices - listing scrape of
  supplychain.nhs.uk/product-information/customer-notices/ (no official API;
  if it redesigns, the Actions log names the failure and the site falls back).

New items appear on the Hub marked "NEW - auto-detected, verify at source"
with verbatim titles only. Review cadence: check the tab (or state/last_run.json)
after Monday runs; add tactical lines for anything worth keeping.

## Ops
- Runs Mondays 03:15 UTC via GitHub Actions (manual: Actions tab, "Run workflow").
- `state/last_run.json` records what each run scanned and added.
- Rollback: this is git - revert the commit.
