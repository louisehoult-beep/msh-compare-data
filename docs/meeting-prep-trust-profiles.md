# Meeting Prep — how a trust gets a profile

Written 14/08/2026. Governs the trust panels in the Hub's Meeting Prep tool
(Med Sales Tools, page 1109), served from `msh-compare-data`.

**Mirrored into this repo 02/09/2026** so the cloud batch routine can read it (cloud
sessions cannot reach OneDrive). The OneDrive original at
`02-Elevate-and-Thrive/Process flows for all brands/meeting-prep-trust-profiles.md` stays
canonical for edits to the method itself — re-copy here after any change there.

## The problem this fixed

Meeting Prep listed 201 trusts and had a real profile for **one** of them
(Frimley Health). Every other trust fell through to a "No deep Hub profile yet"
note and three search links. A paying member picking their own trust got the
national picture and homework.

## The two layers

A trust profile is now built from **two independent layers**. They are separate
on purpose: one can be generated for everybody, the other cannot.

### Layer 1 — the data layer (automatic, all trusts)

Generated, never hand-typed. Three files, all already in `msh-compare-data`:

| File | Gives | Coverage |
|---|---|---|
| `data/prep-config.json` → `trustDirectory` | ODS code, HQ town/postcode, commissioning ICB, region, buying centre | 204 / 204 |
| `data/trust-contacts.json` | named buyers with work emails, the notice each was named on, recency | ~190 |
| `data/trust-pressures.json` | waiting list, % within 18 weeks, 52/65/78-week waits, median wait by speciality, CQC rating, oversight segment, Never Events, C. difficile, ERIC backlog maintenance | 147 |

Rules this layer obeys:

- **Nothing is derived.** Every figure is the publisher's own number, copied
  through unchanged. No rankings, no "the only trust that…", no scores. A
  derived claim would need its rule stated and an evidence floor under root
  rule 14, and none is needed for the tool to be useful.
- **Every figure carries its publisher and its period.** RTT is monthly; a
  waiting list without the month it describes is not a fact.
- **Named contacts are never given a job title.** Each person was published as
  the enquiry contact for the notice shown. That is the whole claim, and the
  panel says so in those words. This is the 145-false-job-changes lesson.
- **Trusts the publishers don't cover get no panel** rather than an empty one.

### Layer 2 — the research layer (by hand, one trust at a time)

Annual-report and board-paper figures with direct source URLs, how their
procurement actually works (team structure, rep booking system), named
executives with verified sources, and what they've said publicly. This is the
Frimley Health profile, and it is **hand research off primary documents** —
about an hour per trust. It cannot be generated and must never be inferred.

Lives in `data/prep-config.json` → `trusts[]`. Each entry needs `name`, `code`
(ODS), `context`, and may carry `news`, `structure`, `reportFacts[]`,
`people[]`, `voices[]`. Every `reportFact` carries `figure`, `source` (a direct
URL) and `where` (which document, which section).

**Where a trust has no layer 2, the tool says so in its own panel** — "What the
Hub hasn't researched here yet". An incomplete profile must never read as the
whole picture.

## Rebuilding

```bash
cd .../Website/msh-compare-data
python3 scripts/build_trust_pressures.py    # monthly, after the RTT release
python3 scripts/refresh_trusts.py           # weekly, runs itself in CI
python3 scripts/stamp_notice.py
python3 verify.py                           # must exit 0 — a push IS a publish
```

`build_trust_pressures.py` reads `analysis-data.json` from **`origin/main` of
the private pipeline repo**, not the local working tree — the local clone sits
on whatever branch someone last worked on. It **cannot run in CI**: the pipeline
repo is private and this repo's Actions runner has no credential for it. So it
is a manual monthly step, and `verify.py` WARNs at six weeks and FAILs at
twelve so the omission surfaces instead of rotting.

## What the gate checks

`verify.py` → `check_trust_pressures()`, with five cases in `test_verify.py`:

- a percentage above 100, a median wait of 900 weeks, a segment outside 1–4 —
  each means an upstream column moved
- figures filed against a trust not in the trust map
- figures nobody has rebuilt for two RTT cycles
- any figure group with no period recorded against it

## Two things found while building this (both fixed 14/08/2026)

1. **Three live NHS foundation trusts were missing from everything.** The ODS
   crawl asked only for primary role RO197 (NHS Trust) and never for RO107
   (Care Trust), so Bradford District Care, Sheffield Health Partnership
   University and Black Country Healthcare appeared in neither the Meeting Prep
   directory nor the Stakeholder Mapper. `refresh_trusts.py` now crawls both.
2. **North Bristol NHS Trust legally ended on 30/06/2026** but still filed
   42,031 waiters in the June RTT return. The builder drops any trust absent
   from `trust-map.json` (which filters on legal end date, not ODS Status) and
   **names what it dropped** rather than trimming silently.

## Ordering the queue — the speciality rule expires after batch two

Batches one and two were picked by ranking trusts on how many of the eight Hub
specialities appear in their own Find a Tender notice titles. **Do not use that
rule for batch three onward.** By then it has stopped discriminating: the top of
the remaining list scores 4 specialities against 7 in batch two, and 81 of the
184 remaining trusts score zero — not because they buy nothing, but because
their notice titles happen not to carry the keywords.

Checked on 14/08/2026, ranking by speciality hits and ranking by waiting-list
size agree on only **5 of their top 20**. The speciality rule defers Manchester
University (166,009 waiting, the largest list in England), Royal Free (139,476),
Northern Care Alliance (133,771), Barts Health (121,464), Oxford University
Hospitals (90,534) and Imperial (83,936) — the largest and most commercially
valuable trusts in the country.

**From batch three, order by waiting-list size within the acute trusts**, then
pick up community, mental health and ambulance trusts afterwards. A keyword in a
notice title was always thin evidence (root rule 14); once it stops separating
the list it is worse than no rule, because it looks like a priority order while
actually being an artefact of how buyers word their titles.

## How a batch is actually run — ten in parallel

**This is the default from batch three onward.** One orchestrator session, ten
subagents, one trust each. A batch of ten takes about eight minutes of wall
clock instead of ten hours, and the orchestrator's context stays small because
agents write files rather than returning prose.

1. **Pick the next ten** off `Hub/trust-profile-worklist.md`, in list order.
2. **Extract layer 1 per trust into the scratchpad** as `<CODE>-layer1.json`
   (directory entry, pressures block, the `periods` map, contacts). The agent
   never has to open the repo for layer 1, so it cannot mis-read it.
3. **Write ONE shared brief** the agents all read, and give each agent only its
   trust, its layer-1 path and its output path. The brief carries the schema,
   the hard rules, the UK-English and no-em-dash rule, the PDF and bot-protection
   recipes, and points at the Hull entry (RWA) as the depth benchmark.
4. **Tell each agent to write a file and return at most 12 lines.** Never let it
   paste the JSON back; that is what fills the orchestrator's context.
5. **Give each agent one trust-specific hint** where you have one, phrased as a
   question to test, never as a fact to write. Batch four's Norfolk hint asserted
   RAAC at NNUH; the agent checked, found none in the annual report, established
   the RAAC is at the two partner trusts and recorded that instead. **A hint you
   state as fact is a hint that gets published.**
6. **Then the orchestrator verifies, and this is not optional:**
   - HTTP-check every `source`, `linkedin` and voice URL in the whole batch,
     concurrently. Retry any non-200 with full browser headers before believing it.
   - Cross-check each profile's `context` against its own layer-1 file: waiting
     list, 18-week %, median wait and segment must all appear, the region must
     match, and no CQC rating may be asserted where layer 1 holds null.
   - Check the schema key order and that no notice-sourced contact carries a job
     title.
7. **Merge, gate, publish** (below).

### Why the agents are worth trusting here

They are only trustworthy because the brief forces primary documents and the
orchestrator re-checks the mechanical claims. In batch four they independently
caught: a CQC "Outstanding" that was published in March 2019 and inherited from
a predecessor organisation; three different Never Event counts for one trust
across three periods, all reported with their periods rather than reconciled;
two trusts whose chair and chief executive had both changed since the annual
report; and a segment 3 that was really a segment 2 pushed down by a financial
override. Every one of those would have published a false claim.

## Runbook — researching one trust

Roughly an hour each. Nothing here is generated; every figure is read off a
primary document. Per trust:

1. **Layer-1 first, from files already in this repo** — `trust-pressures.json`
   for waiting list, 18-week %, 52-week breaches, median wait, CQC, oversight
   segment; `trust-contacts.json` for named buyers and what they were named on.
   That is the `context` paragraph, and it costs nothing.
2. **Find the live board page and read it, never a search snippet.** Search
   results are reliably stale on leadership — batch two caught Leicester still
   being reported with a chief executive who is now a chair elsewhere. Several
   trust sites 404 on guessed paths; search with `allowed_domains` set to the
   trust's own domain to find the real URL.
3. **Get the annual report as a PDF and extract it locally.** WebFetch cannot
   read PDFs. `curl` with a browser User-Agent, then `pdftotext -layout`, then
   grep for `deficit of|surplus of|cost improvement|capital programme|savings`.
   This is the fastest route to the four to six `reportFacts`.
4. **If no current-year report exists, say so.** Eight of batch two's ten had
   published no 2025/26 accounts. Write "Not verified" into the prose and give
   no current-year outturn rather than letting last year's figures read as
   current. A board-meeting update page is often fresher than the accounts and
   is a legitimate source — United Lincolnshire's 07/07/2026 Group Board update
   gave a live month-two position.
5. **Check the procurement page for who actually buys.** The highest-value
   finding in batch two was structural, not financial: Birmingham Community has
   no procurement of its own, and Gloucestershire hosts its county's shared
   service. Always ask whether this trust buys for itself, buys through someone
   else, or buys for others.
6. **Verify every source URL returns 200** before the entry is finished.
7. **Prose carries the caveats.** There is no `notVerified` field — the schema
   is `name, code, region, context, news, structure, reportFacts, people,
   voices, contacts`, and anything unverified goes in the `structure` text.

### Known obstacles

A blocked link and a dead link look identical to a naive check. Tell them apart
before dropping a source.

| Pattern | Seen at | What to do |
|---|---|---|
| Cloudflare, total block | Royal Free London (RAL) | Cannot be automated at all. Needs a human to save the PDF from a real browser. Leave it flagged. |
| Imperva | Bradford | Cannot be read. Source leadership from the annual report and say so in every `people` note. |
| Akamai, 403 to plain curl | `royaldevon.nhs.uk` | Works with a FULL browser header set: User-Agent plus Accept, Accept-Language, Sec-Fetch-Dest/Mode/Site, Upgrade-Insecure-Requests. The links are live. |
| 403 to WebFetch, fine via curl | `uhcw.nhs.uk` | Use curl. |
| 403 to curl | Find a Tender notice pages | Usable as evidence read another way, but never cite one as a `source` URL, because the URL check will fail it. |
| Scanned-image PDF | Royal Wolverhampton 2025/26 financial statements | `pdftotext` extracts nothing. Fall back to the prior year and state which year the figure is. |
| Domain moved | Leicester → `uhleicester.nhs.uk` | Old domain soft-404s every path. |

**Never downgrade a blocked link to "dead" without retrying with full browser
headers.** Batch four's URL sweep initially reported 15 dead sources at Royal
Devon; all 15 returned 200 on retry, including a 2.2MB annual report PDF.

## The directory de-duplicates on ODS code, not name

`refresh_trusts.py` rebuilds `trustDirectory` as "every live trust that has NO
layer-2 profile". Until 28/08/2026 it decided that by matching **names**, and
Newcastle's profile spells it "The Newcastle upon Tyne Hospitals NHS Foundation
Trust" while ODS spells it "Upon". The match failed silently and a fully
profiled trust kept reappearing in Meeting Prep as unresearched, which is the
exact failure this whole project existed to remove.

It now matches on `code`. **When adding a profile, the `name` must still match
the ODS name exactly** for everything else that joins on name, so check it
against `trustDirectory` before merging. Fixing the data alone would have been
reverted by the next weekly refresh, because a generated file always wins.

## Publishing a batch

Draft each trust as its own JSON file, merge, then gate. **A push to this repo
is a live publish** (root rule 13), so `verify.py` must exit 0 first, and the
`pre-push` hook runs it again. **Never use a worktree** — Lou retired them
03/09/2026 after finding several abandoned. Claim the shared checkout with
`./session-lock.sh claim "<what you're doing>"` before editing, work in the
checkout directly, and release with `./session-lock.sh release` when done; if
the lock is held, wait or ask, don't work around it. `land.sh` itself also
refuses to land over a different live session's claim. Expect the first push
to be rejected if a peer pushes mid-operation; re-fetch, replay, re-gate, push
again. Never force. Full method: `msh-compare-data-session-lock.md` in this
folder.
