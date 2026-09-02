# Trust profile worklist — every trust still without a layer-2 profile

**Canonical copy as of 02/09/2026 (batch twelve).** This file now lives in the
`msh-compare-data` repo, not OneDrive, so both local sessions and the cloud batch routine
read and write the same file. The old OneDrive copy at
`02-Elevate-and-Thrive/Hub/trust-profile-worklist.md` carries a pointer to here and must
not be edited — two copies of live batch state is how a batch re-does work or a hint gets
overwritten. Update this file, not that one.

Last updated 02/09/2026, after batch twelve. **84 trusts remain**; 120 now carry a full
layer-2 profile (Velindre excluded separately).
Ordering rule: acute trusts by waiting-list size, then community/MH/ambulance by speciality
hits. See `../Process flows for all brands/meeting-prep-trust-profiles.md` for why the
speciality-title rule was retired after batch two, and for the per-trust runbook.

**Method: ten trusts researched concurrently by subagents, one trust each, merged and gated
by the orchestrator.** This is the default, not an experiment. Each agent gets the runbook,
the verification standard, its own layer-1 numbers and the Hull entry as the depth benchmark;
it writes one JSON file and returns a short summary, so the orchestrator's context stays
small. A batch of ten takes about eight minutes of wall clock. The orchestrator then
HTTP-checks every source URL, cross-checks each profile's layer-1 figures against
`trust-pressures.json`, merges, and gates.

**Batch three (14/08/2026, `ceaa87a`) closed 9 of 10**: Manchester University, Northern Care
Alliance, Barts Health, Derby and Burton, Oxford University Hospitals, King's College,
Newcastle upon Tyne, Hull University Teaching, Imperial College.

**Batch four (28/08/2026, `4f34fb4`) closed 10 of 10**: East Kent, London North West, Mersey
and West Lancashire, North West Anglia, Royal Devon, Chelsea and Westminster, Coventry and
Warwickshire, Royal Wolverhampton, Norfolk and Norwich, St George's. All 151 source URLs
checked 200.

**Batch five (28/08/2026, `1f60aff`) closed 10 of 10**: University Hospitals Dorset,
Sandwell and West Birmingham, University Hospital Southampton, Liverpool University
Hospitals, Lancashire Teaching Hospitals, South Tyneside and Sunderland, Cambridge
University Hospitals, Worcestershire Acute Hospitals, Portsmouth Hospitals University,
Lewisham and Greenwich. All 35 source/linkedin URLs checked 200 (two Find a Tender
notices needed full browser headers). Liverpool University Hospitals' own site
(`uhliverpool.nhs.uk`) is genuinely Cloudflare-blocked, confirmed with full browser
headers as well as plain curl — same failure mode as Royal Free, but on this trust it
only blocked the board/procurement pages, not the whole profile, so the entry still
published: leadership appointments came from NHS system-body and trade-press coverage
(the standard's event carve-out), and financial reportFacts that only had a vendor case
study or third-party board-paper reporting behind them were dropped rather than published
with a caveat, per HUB-VERIFICATION-STANDARD rule 9.

**Batch six (28/08/2026, `7afb432`) closed 10 of 10**: South Tees Hospitals, Epsom and St
Helier, York and Scarborough, East Sussex Healthcare, Mid Yorkshire Teaching, Doncaster and
Bassetlaw, Ashford and St Peter's, East and North Hertfordshire, County Durham and
Darlington, Maidstone and Tunbridge Wells. All 34 source/linkedin URLs checked 200 (one
Find a Tender notice needed full browser headers; three `ashfordstpeters.nhs.uk` pages
return 202 to every automated client, including curl with full headers, but render
correctly in a real browser — confirmed directly rather than assumed dead). Epsom and St
Helier's gesh-group hint from the table below was confirmed accurate: it still buys for
itself. York and Scarborough's link to Hull's procurement collaborative was confirmed, but
whether it keeps its own clinical sign-off within that collaborative remains genuinely not
verified, same as it was in Hull's own entry.

**Batch seven (28/08/2026, `d53a00b`) closed 10 of 10**: Surrey and Sussex Healthcare,
Bristol NHS Foundation Trust, Hampshire Hospitals, Buckinghamshire Healthcare, University
Hospitals Plymouth, The Dudley Group, East Lancashire Hospitals, Wrightington Wigan and
Leigh, Wirral University Teaching, West Hertfordshire Teaching. All 34 source/linkedin URLs
checked 200. This push was rejected twice by concurrent pushes from other sessions working
the same repo (differentiator/supplier-domains work); each time the fix was fetch, rebase,
re-run `verify.py`, push again, never force. RA7 is now "Bristol NHS Foundation Trust",
formed 1 July 2026 by the North Bristol / UHBW merger; its financial facts are the
predecessor UHBW's last annual report, labelled as such. RXR's own site is
Incapsula-protected; rather than use a third-party (UNISON) deficit figure as a fact, it
stayed in prose only, explicitly disclaimed as unverified, and no financial reportFacts
were written for that trust at all.

**Batch eight (28/08/2026, `09b7fbf`) closed 10 of 10**: Royal Cornwall Hospitals, Great
Western Hospitals, Northern Lincolnshire and Goole, Blackpool Teaching Hospitals, Kingston
and Richmond, Northumbria Healthcare, Northampton General, Royal United Hospitals Bath,
Moorfields Eye Hospital, The Princess Alexandra Hospital. All 31 source/linkedin URLs
checked 200 (four Find a Tender notices needed full browser headers). This push was
rejected four times by a wave of concurrent pushes from other sessions (differentiator,
supplier-domain-seeding and framework-awards work all landing at once); each time the fix
was fetch, rebase, re-run `verify.py`, push again, never force — it landed on the fifth
try. RN3 and RD1 independently confirmed the same BSW Hospitals Group leadership (Group
Chair Paul von der Heyde, CEO Cara Charles-Barks), a clean cross-check between two
different agents. RJL confirmed the Hull/NLaG shared-executive Group model from its own
side, and separately confirmed its Humber and North Yorkshire Procurement Collaborative
membership. RXL confirmed its "One LSC Procurement" membership hosted by East Lancashire.

**Batch nine (28/08/2026, `0681565`) closed 10 of 10**: Bolton, The Shrewsbury and Telford
Hospital, Croydon Health Services, Milton Keynes University Hospital, University Hospitals
of Morecambe Bay, Calderdale and Huddersfield, Royal Berkshire, Medway, North Cheshire and
Mersey, North Cumbria Integrated Care. All 27 source URLs checked 200. Pushed clean on the
first attempt, no rebase conflicts. One name-spelling slip caught and fixed before merge:
an agent wrote "Calderdale And Huddersfield" (capital And); the ODS directory spells it
lowercase "and", matching Newcastle's "Upon"/"upon" trap from earlier batches — the same
class of error keeps recurring and is worth checking every batch, not just when flagged.
The same entry also had seven em-dashes, fixed before merge. The One LSC Procurement hint
tested true for Morecambe Bay (RTX) — its own 2025/26 accounts confirm procurement, finance,
digital and people & culture were TUPE-transferred into the One LSC joint venture hosted by
East Lancashire Hospitals, effective 1 November 2024 — but tested unconfirmed for North
Cumbria Integrated Care (RNN): its own annual report never mentions One LSC, and the one
tender where it appears as a co-buyer names Lancashire Teaching Hospitals as host "on behalf
of ONE LSC partners", not East Lancashire. Recorded as prose, not fact, in both entries; see
the updated group-link table below. North Cheshire and Mersey (RWW, formed 01/04/2026 from
Warrington and Halton Teaching Hospitals' acquisition of Bridgewater Community Healthcare)
correctly used the still-current annual report filed under the legal predecessor name, dated
and flagged rather than presented as an NCM-branded report — the same "trust renamed, report
still under old name" pattern as North Cheshire and Mersey's own build.

**Batch ten (01/09/2026, `cbb242b`) closed 10 of 10**: Stockport, West Suffolk, The
Hillingdon Hospitals, Sherwood Forest, James Paget University, South Warwickshire
University, Royal Surrey, Dartford and Gravesham, Countess of Chester, Salisbury. All 34
source/linkedin URLs checked 200 (one Royal Surrey PDF link needed full browser headers).
Eight of the ten agents were first dispatched on Opus and hit the account's monthly spend
limit mid-run; relaunching the same nine on Sonnet cleared it, and one (Countess of Chester)
returned as "stopped" rather than "completed" from a harness restart but had already
written a complete, valid JSON file, so it was used as-is rather than re-run. Pushed clean
on the first attempt. Two genuine cross-checks resolved as recorded, not smoothed over:
Salisbury confirmed the same BSW Hospitals Group leadership as GWH and RUH, but its own
procurement page shows an unmerged, trust-only team, contradicting an assumption that
procurement itself is group-wide; and Hillingdon's own 2024/25 annual report records
oversight segment 3 as at 31/03/2025 while layer-1's current data shows segment 1, both
kept in the entry with their own dates rather than one overwriting the other. James Paget
sits in oversight segment 4 in layer 1, but every one of its own published board documents
still shows segment 2, so segment 4 could not be explained from a primary source and is
recorded as unexplained rather than invented. Royal Surrey's null CQC value was explained
directly: CQC no longer issues a single overall rating for the trust under its current
assessment approach, and its most recent published domain assessment (Well-led: Outstanding,
13/06/2025) was dated and clearly separated from an overall rating rather than substituted
for one.

**Batch eleven (02/09/2026) closed 10 of 10**: Rotherham, Mid Cheshire, Walsall, Kettering, Chesterfield, Homerton, QEH King's Lynn, North Tees and Hartlepool, Whittington, Wye Valley. All 38 source URLs returned 200. Royal Free (RAL) skipped again, still Cloudflare-blocked, but its procurement route was established indirectly via Whittington. Corrected the NNUH 'host' claim in the table above. Three trusts dropped a figure rather than publish it caveated: Homerton (elective centre build cost), North Tees (rebuild estimate) and Walsall (six-organisation NMBC membership).

**Batch twelve (02/09/2026, `0abd50e`) closed 10 of 10**: Dorset County Hospital, Barnsley
Hospital, Queen Victoria Hospital, Birmingham Women's and Children's, Harrogate and
District, George Eliot Hospital, East Cheshire, Tameside and Glossop, Alder Hey Children's,
Airedale. All source/linkedin URLs checked 200 (two Airedale board/annual-report pages and
one Rotherham-linked LinkedIn profile 403/999'd to curl and urllib but confirmed live via a
real browser, same bot-block pattern as Liverpool University Hospitals in batch five). Every
research agent ran on Sonnet as instructed; six of ten still hit the account's monthly spend
limit mid-run and had to be relaunched, one of them (Alder Hey) twice because the first
failure was missed in the first retry pass and only caught when its file never appeared —
worth a checklist against the dispatch list next time, not just against completion
notifications. Two trusts stated a CQC rating despite a null layer-1 value (East Cheshire,
Alder Hey): both properly caveated as independently sourced from CQC's own site and dated,
matching the Royal Surrey precedent from batch ten, not a violation. Barnsley's
shared-leadership hint with Rotherham tested true on leadership, false on the buying
mechanism: Barnsley runs procurement through its own wholly-owned subsidiary, Barnsley
Facilities Services, not Rotherham's Intend portal. George Eliot's Foundation Group hint
tested only partially true: shared executive oversight is with South Warwickshire
specifically (CFO), not pooled across the wider four-trust group, and day-to-day clinical
supply chain buying is not established as joint. Two new hosting findings not in any prior
hint: Alder Hey's clinical procurement is fully outsourced to Health Procurement Liverpool,
hosted at The Walton Centre, alongside Clatterbridge and Liverpool Heart and Chest; Airedale
hosts a shared procurement function (AGH Solutions) also covering Bradford District Care and
ILS LLP. Dorset County shares CEO, Chair, CFO and Chief People Officer with Dorset HealthCare
under a federated model but keeps separate trust-level procurement, the same
shared-leadership-without-shared-buying pattern as Rotherham/Barnsley. Tameside and Glossop
shares a Chief Medical Officer and a Director of Informatics with Stockport and is running a
parallel EPR procurement (Altera) alongside it, worth testing further if Stockport is
profiled.

⚠️ **Royal Free London (RAL) is blocked and needs a human.** It is behind Cloudflare and
refuses all automated fetching, including `curl` with a browser User-Agent. Its annual
report PDF has to be saved by hand from a real browser before the profile can be researched.
It stays at the top of the acute list until that happens; do not keep re-attempting it.

## Known group and collaborative links inside this list

Batch four's recurring finding was that the buying route is rarely where the org chart puts
it, and several trusts still on this list are partners of trusts already profiled. Read the
profiled partner before researching these, and be precise about which facts are group-level:

| Still on this list | Linked to (already profiled) | Nature of the link |
|---|---|---|
| James Paget (RGP), QEH King's Lynn (RCX) | Norfolk and Norwich (RM1) | Norfolk and Waveney University Hospitals Group, one chair and one chief executive across all three boards, governing via a General Purpose Joint Committee. **Not a host model:** QEH's own 2025/26 annual report never calls NNUH the host, and Group executive costs are split equally 33.3% each (established batch eleven, 02/09/2026). RAAC sits at RGP and RCX, not at NNUH. |
| Walsall Healthcare (RBK) | Royal Wolverhampton (RL4) | Wolverhampton and Walsall Group, shared executive. Procurement sits ABOVE the group with NMBC, hosted by University Hospitals of North Midlands (RJE, already profiled), covering six organisations. |
| Torbay and South Devon (RA9), Devon Partnership (RWV), Livewell South West | Royal Devon (RH8), University Hospitals Plymouth (RK9) | Devon Procurement Service, formed December 2025, five organisations, all non-pay spend. Plymouth appears to be the host (44 WTE procurement staff transferred in March 2025), not just a member. |
| Barnsley Hospital (RFF) | The Rotherham NHS Foundation Trust (RFR, profiled batch eleven) | Joint Chief Executive, Chief Financial Officer and Deputy Chief Executive shared across both trusts. Rotherham still runs its OWN trust-level procurement on its own Intend portal, so shared leadership does NOT mean shared buying. Read Rotherham's entry before profiling Barnsley. |
| Royal Free London (RAL, Cloudflare-blocked) , Moorfields (RP6), North Middlesex (RAP) | Whittington Health (RKE, profiled batch eleven) | Whittington HOSTS the Partners Procurement Service, buying for itself, Moorfields, North Middlesex and Royal Free. This is the procurement route into RAL even though RAL's own site cannot be read. Established from Whittington's own documents, batch eleven. |
| Remaining North East London trusts | Barts Health (RF4, profiled), Homerton (RQX, profiled batch eleven) | North East London Procurement Partnership, hosted by Barts Health, live from 01/01/2026. Homerton buys through it rather than solely on its own account. Expect the same route for other NEL trusts, but verify per trust. |
| George Eliot (RLT) | Wye Valley (RLQ, profiled batch eleven), Worcestershire Acute (RWP), South Warwickshire (RJC) | Foundation Group under one Group Chief Executive (Glen Burley) and one Chair across all four trusts. At least one procurement decision (external audit) is run jointly. Day-to-day clinical supply chain buying is NOT established, so test it rather than assume. |
| Northampton General (RNS) | Kettering General (RNQ, profiled batch eleven) | University Hospitals of Northamptonshire group board and shared executive; further joint Chief Executive/Chair link to Leicester (RK5). Kettering is under NHS England Enforcement Undertakings since October 2023, so approvals run above trust level. |
| Lancashire & South Cumbria (RW5) | East Lancashire Hospitals (RXR), Lancashire Teaching Hospitals (RXN), Blackpool Teaching (RXL), University Hospitals of Morecambe Bay (RTX, profiled batch nine) | One LSC Procurement, hosted by East Lancashire (confirmed via its own live job advert and, independently, Morecambe Bay's own 2025/26 accounts), successor to the older three-trust Lancashire Procurement Cluster. Morecambe Bay's own accounts confirm its procurement, finance, digital and people & culture functions transferred into the joint venture 1 November 2024. **North Cumbria Integrated Care (RNN, profiled batch nine) is NOT a confirmed member** — its own annual report never mentions One LSC; it appears as a co-buyer on one tender hosted by Lancashire Teaching "on behalf of ONE LSC partners", which may mean a wider but looser partner list than the five-trust JV, or a one-off. Worth testing again if RW5 or another Cumbria/Lancashire trust surfaces the same question. |
| Salisbury (RNZ) | Great Western Hospitals (RN3), Royal United Hospitals Bath (RD1) | BSW Hospitals Group, one Group Chair (Paul von der Heyde, from 1 April 2026) and one Group CEO (Cara Charles-Barks) across all three, merged procurement department. Confirmed independently from both RN3's and RD1's own sides. |
| Barnsley Hospital (RFF, profiled batch twelve) | The Rotherham NHS Foundation Trust (RFR, profiled batch eleven) | Shared Chief Executive, CFO and Deputy Chief Executive, confirmed from both sides. Buying is NOT shared: Rotherham runs its own Intend portal, Barnsley routes procurement through its own wholly-owned subsidiary, Barnsley Facilities Services (~£50m/year), confirmed on BFS's own site. Same lesson twice now: shared leadership does not mean shared buying, but the mechanism differs even between the two linked trusts. |
| George Eliot (RLT, profiled batch twelve) | Wye Valley (RLQ, profiled batch eleven), Worcestershire Acute (RWP), South Warwickshire (RJC) | Foundation Group under one Group Chief Executive (Glen Burley) and one Chair. George Eliot's own evidence shows the shared executive link (CFO) is specifically with South Warwickshire, not pooled across all four trusts, and moved to a joint Executive Team and joint statutory Board with South Warwickshire Oct 2025-Apr 2026. Day-to-day clinical supply chain buying is still NOT established as joint for any pairing in this group. |
| Dorset County Hospital (RBD, profiled batch twelve) | Dorset HealthCare (not yet profiled) | Federated model since 2022-24: shared CEO, Chair, CFO and Chief People Officer, confirmed on Dorset County's own site. Procurement is NOT shared: Dorset County runs its own Procurement & Logistics department (~£45m non-pay spend via Atamis) and Dorset HealthCare keeps a separate procurement page/portal. Third confirmed instance of shared leadership without shared buying, after Rotherham/Barnsley. |
| Alder Hey Children's (RBS, profiled batch twelve) | The Walton Centre (RET, not yet profiled), Clatterbridge Cancer Centre (REN, not yet profiled), Liverpool Heart and Chest (RBQ, not yet profiled) | Health Procurement Liverpool, hosted at The Walton Centre, runs Alder Hey's clinical procurement fully outsourced. Established from Alder Hey's own FOI disclosure log (batch twelve). Whether HPL also covers non-clinical/corporate procurement is not established. Worth confirming from The Walton Centre's own side when it is profiled. |
| Airedale (RCF, profiled batch twelve) | Bradford District Care (TAD, not yet profiled) | Airedale hosts a shared procurement function, AGH Solutions Ltd, also covering Bradford District Care and ILS LLP, per Airedale's own "Doing business with us" page (batch twelve). Governance detail on the Bradford District Care/ILS LLP side is not yet established; confirm when Bradford District Care is profiled. |
| Tameside and Glossop (RMP, profiled batch twelve) | Stockport (not yet on this list) | Shares a Chief Medical Officer (Dilraj Sandher) and a Director of Informatics (Peter Nuttall) with Stockport, and is running a parallel/coordinated EPR procurement (Altera, March 2026) alongside Stockport. Procurement itself is not established as joint; Tameside appears to run its own function (own Head of Procurement contact, own tender notices) but no dedicated procurement page was found to confirm it independently. |

## Known fetching obstacles

- **Cloudflare, total block:** Royal Free London. Needs a human with a browser.
- **Akamai, 403 to plain curl:** `royaldevon.nhs.uk`. Works with a full browser header set
  (User-Agent plus Accept, Accept-Language, Sec-Fetch-*). Links are live, not dead.
- **403 to WebFetch but fine via curl:** `uhcw.nhs.uk`.
- **403 to curl:** Find a Tender notice pages. Usable as evidence read another way, but do
  not cite one as a `source` URL that will be checked.
- **Scanned-image PDFs that will not extract:** Royal Wolverhampton's 2025/26 financial
  statement pages. Fall back to the prior year and say which year the figure is.

## Acute and specialist trusts — 29 remaining, by waiting list

| # | Trust | ODS | Waiting list | Seg | Spec hits |
|---|---|---|---|---|---|
| 1 | Royal Free London NHS Foundation Trust | RAL | 139,476 | 3 | 0 |
| 2 | The Robert Jones and Agnes Hunt Orthopaedic Hospital NHS Foundation Trust | RL1 | 13,426 | 1 | 1 |
| 3 | Sussex Community NHS Foundation Trust | RDR | 13,214 | — | 0 |
| 4 | The Royal Orthopaedic Hospital NHS Foundation Trust | RRJ | 13,205 | 1 | 1 |
| 5 | Isle of Wight NHS Trust | R1F | 12,768 | 3 | 0 |
| 6 | The Walton Centre NHS Foundation Trust | RET | 11,785 | 1 | 1 |
| 7 | Gateshead Health NHS Foundation Trust | RR7 | 11,492 | 3 | 1 |
| 8 | Liverpool Women's NHS Foundation Trust | REP | 11,439 | 3 | 1 |
| 9 | Sheffield Children's NHS Foundation Trust | RCU | 11,355 | 3 | 1 |
| 10 | Midlands Partnership University NHS Foundation Trust | RRE | 10,290 | — | 0 |
| 11 | Royal National Orthopaedic Hospital NHS Trust | RAN | 8,790 | 1 | 2 |
| 12 | Great Ormond Street Hospital For Children NHS Foundation Trust | RP4 | 8,368 | 3 | 0 |
| 13 | Shropshire Community Health NHS Trust | R1D | 7,971 | — | 2 |
| 14 | Royal Papworth Hospital NHS Foundation Trust | RGM | 5,670 | 1 | 0 |
| 15 | Liverpool Heart and Chest Hospital NHS Foundation Trust | RBQ | 4,971 | 1 | 1 |
| 16 | South West Yorkshire Partnership Teaching NHS Foundation Trust | RXG | 4,584 | — | 0 |
| 17 | Lancashire & South Cumbria NHS Foundation Trust | RW5 | 4,222 | — | 2 |
| 18 | Kent Community Health NHS Foundation Trust | RYY | 4,203 | — | 2 |
| 19 | The Christie NHS Foundation Trust | RBV | 3,056 | 1 | 0 |
| 20 | The Royal Marsden NHS Foundation Trust | RPY | 1,874 | 1 | 0 |
| 21 | Cornwall Partnership NHS Foundation Trust | RJ8 | 735 | — | 0 |
| 22 | The Clatterbridge Cancer Centre NHS Foundation Trust | REN | 712 | 1 | 1 |
| 23 | Bradford District Care NHS Foundation Trust | TAD | 607 | — | 0 |
| 24 | Oxleas NHS Foundation Trust | RPG | 166 | — | 1 |
| 25 | Cumbria, Northumberland, Tyne and Wear NHS Foundation Trust | RX4 | 153 | — | 0 |
| 26 | Berkshire Healthcare NHS Foundation Trust | RWX | 102 | — | 2 |
| 27 | Cambridgeshire and Peterborough NHS Foundation Trust | RT1 | 84 | — | 1 |
| 28 | Herefordshire and Worcestershire Health and Care NHS Trust | R1A | 31 | — | 0 |
| 29 | Lincolnshire Partnership NHS Foundation Trust | RP7 | 10 | — | 1 |

## Community, mental health and ambulance trusts — 55 remaining

No RTT return and no acute oversight segment, so layer 1 is thinner by design.

| # | Trust | ODS | Spec hits | Named contacts |
|---|---|---|---|---|
| 1 | Nottinghamshire Healthcare NHS Foundation Trust | RHA | 3 | 13 |
| 2 | East of England Ambulance Service NHS Trust | RYC | 3 | 5 |
| 3 | London Ambulance Service NHS Trust | RRU | 3 | 5 |
| 4 | Dorset Healthcare University NHS Foundation Trust | RDY | 2 | 11 |
| 5 | Northamptonshire Healthcare NHS Foundation Trust | RP1 | 2 | 8 |
| 6 | South Western Ambulance Service NHS Foundation Trust | RYF | 2 | 6 |
| 7 | Torbay and South Devon NHS Foundation Trust | RA9 | 2 | 3 |
| 8 | South East Coast Ambulance Service NHS Foundation Trust | RYD | 2 | 3 |
| 9 | South Central Ambulance Service NHS Foundation Trust | RYE | 2 | 1 |
| 10 | Gloucestershire Health and Care NHS Foundation Trust | RTQ | 1 | 14 |
| 11 | West London NHS Trust | RKL | 1 | 14 |
| 12 | North East London NHS Foundation Trust | RAT | 1 | 12 |
| 13 | Public Health Wales NHS Trust | RYT | 1 | 12 |
| 14 | East London NHS Foundation Trust | RWK | 1 | 9 |
| 15 | Sussex Partnership NHS Foundation Trust | RX2 | 1 | 9 |
| 16 | North London NHS Foundation Trust | G6V2S | 1 | 8 |
| 17 | Derbyshire Healthcare NHS Foundation Trust | RXM | 1 | 7 |
| 18 | Mersey Care NHS Foundation Trust | RW4 | 1 | 6 |
| 19 | Central and North West London NHS Foundation Trust | RV3 | 1 | 5 |
| 20 | Essex Partnership University NHS Foundation Trust | R1L | 1 | 5 |
| 21 | Greater Manchester Mental Health NHS Foundation Trust | RXV | 1 | 4 |
| 22 | Yorkshire Ambulance Service NHS Trust | RX8 | 1 | 4 |
| 23 | Leicestershire Partnership NHS Trust | RT5 | 1 | 2 |
| 24 | Avon and Wiltshire Mental Health Partnership NHS Trust | RVN | 1 | 2 |
| 25 | Kent and Medway Mental Health NHS Trust | RXY | 1 | 2 |
| 26 | Leeds and York Partnership NHS Foundation Trust | RGD | 0 | 15 |
| 27 | Hertfordshire Partnership University NHS Foundation Trust | RWR | 0 | 9 |
| 28 | Norfolk and Suffolk NHS Foundation Trust | RMY | 0 | 8 |
| 29 | Welsh Ambulance Services NHS Trust | RT4 | 0 | 8 |
| 30 | South London and Maudsley NHS Foundation Trust | RV5 | 0 | 7 |
| 31 | Surrey and Borders Partnership NHS Foundation Trust | RXX | 0 | 7 |
| 32 | Central London Community Healthcare NHS Trust | RYX | 0 | 7 |
| 33 | Lincolnshire Community Health Services NHS Trust | RY5 | 0 | 7 |
| 34 | Cheshire and Wirral Partnership NHS Foundation Trust | RXA | 0 | 5 |
| 35 | Humber Teaching NHS Foundation Trust | RV9 | 0 | 5 |
| 36 | North Staffordshire Combined Healthcare NHS Trust | RLY | 0 | 4 |
| 37 | Tees, Esk and Wear Valleys NHS Foundation Trust | RX3 | 0 | 4 |
| 38 | Pennine Care NHS Foundation Trust | RT2 | 0 | 3 |
| 39 | Birmingham and Solihull Mental Health NHS Foundation Trust | RXT | 0 | 3 |
| 40 | Derbyshire Community Health Services NHS Foundation Trust | RY8 | 0 | 3 |
| 41 | East Midlands Ambulance Service NHS Trust | RX9 | 0 | 3 |
| 42 | Hertfordshire Community NHS Trust | RY4 | 0 | 3 |
| 43 | North West Ambulance Service NHS Trust | RX7 | 0 | 3 |
| 44 | West Midlands Ambulance Service University NHS Foundation Trust | RYA | 0 | 3 |
| 45 | Devon Partnership NHS Trust | RWV | 0 | 2 |
| 46 | Rotherham Doncaster and South Humber NHS Foundation Trust | RXE | 0 | 2 |
| 47 | East of England Community Health and Care NHS Trust | RY3 | 0 | 2 |
| 48 | Leeds Community Healthcare NHS Trust | RY6 | 0 | 2 |
| 49 | North East Ambulance Service NHS Foundation Trust | RX6 | 0 | 1 |
| 50 | South West London and St George's Mental Health NHS Trust | RQY | 0 | 1 |
| 51 | Wirral Community Health and Care NHS Foundation Trust | RY7 | 0 | 1 |
| 52 | Black Country Healthcare NHS Foundation Trust | TAJ | 0 | 0 |
| 53 | Coventry and Warwickshire Partnership NHS Trust | RYG | 0 | 0 |
| 54 | Sheffield Health Partnership University NHS Foundation Trust | TAH | 0 | 0 |
| 55 | The Online NHS Trust | K0N6A | 0 | 0 |

## Velindre NHS Trust (RQF) — still excluded

Tops every ranking on 22 specialities and 38 matching notices, and is still deliberately
left out: Welsh, no ICB, buys through NHS Wales Shared Services Partnership, files no RTT
return. It needs its own Welsh template before it can be picked up, not the English one.
