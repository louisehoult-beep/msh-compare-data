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
with verbatim titles only. A daily Cowork task (compare-tab-daily-check) then
DRAFTS the 'use' tactical line for each new item (Claude judgment, sourced,
conservative) and posts them to Lou's dashboard for checking - Lou reviews and
can amend; automation in THIS repo still never writes 'use' lines itself.

## Ops
- Runs daily 03:15 UTC via GitHub Actions (manual: Actions tab, "Run workflow").
- `state/last_run.json` records what each run scanned and added.
- Rollback: this is git - revert the commit.

## app/comptab.js
The Compare tab's full client-side code. The WordPress page (1109, block
MST-COMPARE-LOADER) contains only a tiny loader that fetches and runs this
file, so tab code changes are git commits here - no WordPress editing, no
base64, full history and revert.
