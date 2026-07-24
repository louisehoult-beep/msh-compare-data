# msh-compare-data

## THE ONE RULE THAT OVERRIDES EVERYTHING: `verify.py` MUST PASS

**A push to this repo is a publish.** The Hub fetches these files directly with
a cache-buster, so whatever lands on `main` is on WP page 1109 in front of
paying members within seconds. There is no staging step. There is no review.

```
python3 verify.py        # exit 0 = safe to push
```

It runs automatically on every push and pull request, and before either refresh
workflow is allowed to commit. Install it locally too — this is what stops a
hand-push, which is how both of the July 2026 incidents got out:

```
git config core.hooksPath hooks
```

**Why this exists — 24/07/2026, two incidents in one afternoon.**

1. The Stakeholder Mapper published **145 job changes about named NHS staff.
   All 145 were false.** Moves were detected by diffing the contact index
   before and after a run, which assumes runs walk forward in time; the
   backfill walked backwards, so every earlier month's names were recorded as
   having "replaced" people they actually preceded. The check that would have
   caught it is one line — a person cannot replace somebody who was still
   signing notices three weeks later — and it had never been written, because
   this repo had no gate at all.
2. `data/trust-contacts.json` and `data/people-moves.json` — real named NHS
   staff and their work emails — were published by accident, swept into a
   commit by `git add -A` before it had been agreed they should be public.

`verify.py` now blocks both classes: impossible chronology, implausible volume,
opt-outs that reappear, dates in the future, retention that has stopped being
enforced, contacts filed against trusts that do not exist, JavaScript that does
not parse, datasets that silently collapse — and it refuses to publish named
personal data at all unless the live privacy notice already carries its Article
14 section with the same retention period the code enforces.

If the gate and the data disagree, **assume the data is wrong.** Loosening a
check to make a push go through is how the next incident happens.

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

## Stakeholder Mapper — trust level (added 24/07/2026)
`app/mst-logic.js` drills below the ICB to the individual trust. It injects its
own trust picker, styles and panels, so nothing on WP page 1109 needs editing.

| File | What it drives |
|---|---|
| `data/trust-map.json` | 202 legally-live NHS trusts, each with the ICB that commissions it (ODS, weekly) |
| `data/trust-contacts.json` | Named contacts on each trust's own Find a Tender notices (daily) |
| `data/people-moves.json` | Observed changes of named contact — evidence, never an inferred appointment |

**The trust list is filtered on legal end date, not status.** ODS keeps merged
and dissolved trusts at `Status:Active` indefinitely — 45 of them as at
24/07/2026, including Weston Area Health (gone 2020) and Ipswich Hospital
(gone 2018). They were all in the Meeting Prep directory until this run. Never
rebuild either list from `Status` alone.

**LinkedIn.** The mapper renders search links the member clicks themselves.
Nothing here fetches, scrapes or pre-loads anything from linkedin.com, and it
must stay that way — automated profile views show up in the target's "who
viewed your profile" feed attributed to *your member*. See `data/whos-who.html`.

**Named contacts are personal data.** OGL covers copyright, not UK GDPR lawful
basis. Lou approved publishing names and work emails on 24/07/2026. Article 14
is discharged in the panel itself: it tells the member to say where the details
came from at first contact, and gives them the sentence. Keep that wording — it
is the compliance, not decoration.

If the two contact files are absent the mapper degrades to an honest empty
state, so **deleting them is a valid way to switch the feature off.** To drop
one person on request, remove their entry from `data/trust-contacts.json` and
add them to the harvester's skip handling — the next run must not re-add them.

## app/comptab.js
The Compare tab's full client-side code. The WordPress page (1109, block
MST-COMPARE-LOADER) contains only a tiny loader that fetches and runs this
file, so tab code changes are git commits here - no WordPress editing, no
base64, full history and revert.
