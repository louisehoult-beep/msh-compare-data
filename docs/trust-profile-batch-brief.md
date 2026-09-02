# Trust profile batch — reusable brief for the research step

This is the brief handed to each research pass (one trust each, whether that's a parallel
Sonnet subagent in a local session or a single cloud routine working through its list
sequentially). Read `docs/trust-profile-worklist.md` first for which ten trusts and any
known hints, and `docs/meeting-prep-trust-profiles.md` for the full runbook this brief
summarises. `docs/HUB-VERIFICATION-STANDARD.md` is binding on everything published.

## Per-trust inputs

`scripts/extract_trust_layer1.py --dir tmp/trust-batch <CODE> [<CODE> ...]` writes
`tmp/trust-batch/<CODE>-layer1.json` with three keys:

- `directory`: `n` (exact legal name — use VERBATIM as the `name` field, character for
  character, including "and"/"upon" capitalisation), `code`, `town`, `postcode`, `icb`/
  `icbName`, `region`.
- `pressures`: `wl` (waiting list), `pct18` (% within 18 weeks, standard 92%), `w52`/`w65`/
  `w78` (52/65/78-week waiters), `med` (median wait, weeks), `cqc` (overall CQC rating
  letter/code, or null if CQC holds no overall rating), `seg` (NHS Oversight Framework
  segment 1-4, 4 = most support), `ne` (Never Events), `cdi`/`cdiTotal` (C. difficile),
  `backlogHi`/`backlogTot` (ERIC backlog maintenance, £), `capEq` (capital equipment
  spend, £), `spec` (median wait by speciality).
- `periods`: which month/year each figure is FROM. Cite these.

## Output

Write ONE JSON file per trust to `tmp/trust-batch/<CODE>-profile.json` with EXACTLY this
key order, no more, no fewer keys:

```
name, code, region, context, news, structure, reportFacts, people, voices
```

- **name**: exact `directory.n` string, character for character.
- **code**: the ODS code.
- **region**: from `directory.region`.
- **context**: 4-8 sentences. Must explicitly state the waiting list figure, the 18-week %,
  the median wait, and the oversight segment (or say clearly if segment is absent). State
  figures as layer-1 has them, with their period. Never assert a CQC rating if
  `pressures.cqc` is null — if CQC coverage is found independently on CQC's own site, it may
  be added, sourced and dated, with a sentence making clear layer-1 carries no overall CQC
  rating field (the accepted carve-out, established batch ten and reused batch twelve). End
  with the commercial read for a rep, grounded in the actual figures.
- **news**: recent (~12 months) board/annual-report developments: financial position,
  leadership changes, capital projects, CQC findings, service openings. Read the LIVE board
  page, never a search snippet.
- **structure**: how procurement actually works. Buys for itself, buys through a hosted/
  group function, or hosts buying for others? Check `docs/trust-profile-worklist.md`'s
  cross-reference table for a hint to TEST, never a fact to state. Say plainly what is NOT
  verified rather than guessing.
- **reportFacts**: array of `{fact, figure, source}`, 3-6 items, from the annual report PDF
  or a board paper. `source` is a direct URL to the primary document, never a search result,
  vendor case study, or third-party summary of a trust's own financial facts.
- **people**: array of `{name, role, note, source, linkedin}`, read off the LIVE board page.
  `linkedin` may be `""` if none found; never guess one. A name sourced only from a
  procurement notice gets no `role`, just "named as enquiry contact on notice X".
- **voices**: array (often `[]`) of direct, sourced quotes.

## Hard rules

- UK English. No em dashes (—) anywhere.
- Every fact needs a source URL that actually returns 200. Retry a blocked link with full
  browser headers before giving up; a blocked link is not a dead link. Never cite a Find a
  Tender notice page as a `source` (they 403 to automated fetches).
- A vendor case study or third-party summary is not a primary source for a trust's own
  financial facts. Leadership/appointment news is the one carve-out where trade press is
  legitimate.
- A cross-reference hint is a question to test, never a fact to assert. Write what was
  actually found, including "not established", rather than repeating a hint as fact.
- Publishing nothing beats publishing thin evidence. Drop a figure rather than publish it
  half-sourced.

## Verify, merge, publish

```bash
python3 scripts/verify_trust_profile.py --dir tmp/trust-batch <CODE> [<CODE> ...]
# fix anything it flags, or re-run the research step for that trust, then:
python3 scripts/merge_trust_profiles.py --dir tmp/trust-batch <CODE> [<CODE> ...]
python3 verify.py     # must exit 0 - a push to this repo is a live publish
```

Verify per trust as it's written, not just at the end — cheaper to re-task while still
fresh. A local session lands with `./land.sh "subject" data/prep-config.json` from its own
`./wt.sh <name>` worktree (never the shared checkout). A cloud routine works from its own
isolated clone, so it commits and pushes directly — but still: fetch, rebase onto
`origin/main`, re-run `verify.py`, THEN push, and if the push is rejected by a concurrent
writer, fetch/rebase/re-gate/push again. Never force.

After publishing, update `docs/trust-profile-worklist.md` in the same pass: remove the
completed rows, renumber the remaining table, correct the header counts, add a batch-log
entry, and add any new cross-trust procurement/group links found to the reference table.

## Known recurring obstacles (see the worklist for the live list)

- Royal Free London (RAL): Cloudflare-blocked to all automated fetching, including curl with
  a browser User-Agent. Skip it every batch unless its annual report PDF has been saved by
  hand from a real browser first. Stays at the top of the acute list.
- LinkedIn profile URLs routinely return 999/403 to curl and urllib regardless of validity —
  this is LinkedIn's universal bot-block, not evidence the profile is wrong. A cloud session
  has no interactive browser fallback to confirm one directly; if a LinkedIn URL fails the
  HTTP check and cannot be confirmed another way, note it as unconfirmed rather than drop the
  named person, and do not treat the failed check alone as reason to remove the fact.
- Akamai/Cloudflare 403 to plain curl on some trust sites: retry with a full browser header
  set (User-Agent plus Accept, Accept-Language, Sec-Fetch-*) before concluding a link is
  dead.
- Scanned-image PDFs that `pdftotext` cannot extract: fall back to the prior year's figures
  and say which year they are.
