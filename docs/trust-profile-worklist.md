# Trust profile worklist — every trust still without a layer-2 profile

**Canonical copy as of 04/09/2026 (batch eighteen).** This file now lives in the
`msh-compare-data` repo, not OneDrive, so both local sessions and the cloud batch routine
read and write the same file. The old OneDrive copy at
`02-Elevate-and-Thrive/Hub/trust-profile-worklist.md` carries a pointer to here and must
not be edited — two copies of live batch state is how a batch re-does work or a hint gets
overwritten. Update this file, not that one.

**Batch eighteen (04/09/2026) closed 10 of 10.** Kent and Medway Mental Health (RXY,
renamed 13/10/2025 from Kent and Medway NHS and Social Care Partnership Trust), Leeds and
York Partnership (RGD), Hertfordshire Partnership University (RWR), Norfolk and Suffolk
(RMY), South London and Maudsley (RV5), Surrey and Borders Partnership (RXX), Central
London Community Healthcare (RYX), Lincolnshire Community Health Services (RY5), Cheshire
and Wirral Partnership (RXA), Humber Teaching (RV9). Run out of hours, unattended, same run
as batches sixteen and seventeen. 28 unique source/report URLs checked; 24 returned 200,
4 (all `hpft.nhs.uk`, RWR's own site) returned 403 to the gate's own HTTP check but were
individually confirmed live via WebFetch before merge, same Akamai-class false-negative
pattern as Royal Devon in batch four. One profile (RMY) had em-dashes throughout and was
corrected before merge; one LinkedIn URL (RGD, kept on a single browser-check confidence
the gate itself could not reproduce) was dropped, same standard as batch seventeen.

**Central London Community Healthcare (RYX), the host's own side, fully confirms the NWL
Procurement Service finding RKL and RV3 made in batches sixteen and seventeen** — nine
named partner organisations (CLCH, CNWL, Chelsea and Westminster, Hillingdon Hospitals,
Imperial College Healthcare, London North West University Healthcare, NWL ICB, Royal
Marsden, West London NHS Trust), launched 1 September 2022, governed by a board of partner
CFOs. This closes the "not yet confirmed on the host's own side" caveat both earlier
entries carried.

**A genuine discrepancy, recorded rather than smoothed over: Cheshire and Wirral
Partnership (RXA) does NOT confirm the Health Procurement Liverpool membership Walton
Centre's own annual report asserted for it in batch thirteen.** RXA's own site and annual
report make no mention of HPL, and HPL's own "who we work with" page names only four equal
partners (Alder Hey, Clatterbridge, Liverpool Heart and Chest, Walton Centre) — CWP is not
among them. Both sides are now profiled and disagree; treat the batch-thirteen claim as
unconfirmed on CWP's own account until CWP's side says otherwise, don't repeat it as
settled.

Two further cross-trust threads worth carrying forward: **Lincolnshire Community Health
Services (RY5) runs its own procurement**, named a Trust Head of Procurement, unlike
Lincolnshire Partnership (mental health, no in-house procurement, delivered by ULTH,
established batch fifteen) — the two Lincolnshire trusts share a Group Board with ULTH
since 1 April 2024, but that is governance, not shared buying. **Leeds and York
Partnership (RGD) is integrating by acquisition with Leeds Community Healthcare NHS Trust
(RY6, still on this worklist)**, targeting 1 April 2027, confirmed via the trust's own
leadership blog — worth a specific hint when RY6 comes up.

One leadership-move finding, not a structural one: **South London and Maudsley's (RV5) new
CEO Paul Calaminus is the same person North East London NHS Foundation Trust's (RAT,
profiled batch sixteen) 2025/26 annual report still named as CEO** — RAT's own live board
page had already shown him gone (Jan Ditheridge interim, Edwin Ndlovu MBE announced as
permanent successor). Both facts are independently sourced and correct for their own
trust's current state; recorded here only as a cross-reference, not a correction to either
entry.

Last updated 04/09/2026, after batch eighteen. **21 trusts remain** (1 acute, 20
community/MH/ambulance); **181 now carry a full layer-2 profile** (Velindre and the two
Welsh exclusions still excluded separately).

**Batch seventeen (04/09/2026) closed 10 of 10.** Sussex Partnership (RX2), North London
NHS Foundation Trust (G6V2S), Derbyshire Healthcare (RXM), Mersey Care (RW4), Central and
North West London (RV3), Essex Partnership University (R1L), Greater Manchester Mental
Health (RXV), Yorkshire Ambulance Service (RX8), Leicestershire Partnership (RT5), Avon
and Wiltshire Mental Health Partnership (RVN). Run out of hours, unattended
(`out-of-hours-backlog-clearer`), same run as batch sixteen. All 28 unique source/report
URLs checked 200 by the orchestrator's own sweep. Three schema fixes made before merge,
same class as RWK's in batch sixteen: R1L, RXV and RT5 each asserted a current CQC rating
with no explanation for the null `pressures.cqc`, corrected with the same established form
of words. Seven LinkedIn URLs three agents had kept on the strength of a matching
search-result title (RX2 x3, RXM x3, RXV x1) were dropped instead — none returned 200 on
the gate's own check, and a search-result title match is not the "confirmed live via a
real browser" bar this worklist has required since batch five; kept only what the gate's
own HTTP check could verify.

One structural finding, confirmed directly rather than assumed from the batch-sixteen
hint: **Mersey Care (RW4) is the NHS England Lead Provider for PROSPECT**, the Cheshire and
Merseyside Adult Secure Lead Provider Collaborative (delegated commissioning for adult
low/medium secure mental health, learning disability and autism services), partnered with
Cheshire and Wirral Partnership NHS Foundation Trust and Elysium Health Care. Written as
clinical commissioning, not shared goods/equipment procurement — no evidence found for the
latter.

One hint corrected rather than confirmed: Leicestershire Partnership (RT5) was tested for
a leadership link to University Hospitals of Leicester (RK5) and had none; its actual,
confirmed Group-model link is to **Northamptonshire Healthcare (RP1, profiled batch
sixteen)** — shared Chief Executive (Angela Hillery), CFO, Strategy Director and Chair
since 2019. Worth adding to the group-link table below since both trusts are now profiled.

North London NHS Foundation Trust (G6V2S) confirmed its full merger history directly from
its own site rather than a secondary source: formed 1 November 2024 from Barnet, Enfield
and Haringey Mental Health NHS Trust plus Camden and Islington NHS Foundation Trust, then
acquired The Tavistock and Portman NHS Foundation Trust on 1 April 2026.

**Batch sixteen (04/09/2026) closed 10 of 10 — the first batch of community, mental
health and ambulance trusts.** Dorset HealthCare University (RDY), Northamptonshire
Healthcare (RP1), South Western Ambulance (RYF), Torbay and South Devon (RA9), South East
Coast Ambulance (RYD), South Central Ambulance (RYE), Gloucestershire Health and Care
(RTQ), West London (RKL), North East London NHS Foundation Trust (RAT), East London
(RWK). Run out of hours, unattended (`out-of-hours-backlog-clearer`). All 34 unique
source/report URLs across the batch checked 200 by the orchestrator's own sweep before
merge. No LinkedIn URL was included anywhere in the batch: every candidate profile
returned LinkedIn's HTTP 999 bot-block on direct check and none could be positively
confirmed, so `linkedin` was left empty throughout rather than kept unconfirmed, per the
same rule established in batch thirteen.

Public Health Wales (RYT) was pulled from this batch's queue before dispatch: like
Velindre, it has no ICB and files no RTT return (`nation: Wales` in the directory), so it
needs its own Welsh template, not the English one. Welsh Ambulance Services (RT4) is the
same case and is pulled too. Both moved to the Welsh-exclusion section below rather than
sitting in the numbered queue where the next batch would pick them up and hit the same
problem.

**No RTT/CQC/oversight-segment data exists for any trust in this category** — `trust-pressures.json`
covers acute trusts only, so `verify_trust_profile.py`'s waiting-list/18-week/median/segment
checks are inert here (the layer1 `pressures` key is simply absent, same as null). The `context`
paragraph is instead built from the trust's own published scale, service lines and live
commercial angles (a CIP, an estates programme, a fleet renewal, a merger). Where a trust's own
site independently states a CQC rating with no `pressures.cqc` value to check it against
(true for every trust in this category, not just where CQC's methodology changed), the
now-established form of words is: "this trust type carries no CQC rating in the Hub's
automated pressures dataset, which does not cover community and mental health trusts" —
matches the gate's null-CQC carve-out and is factually accurate (RWK needed this fix
before it passed the gate).

Two structural findings, each independently corroborated from more than one trust's own
side, not asserted from a single document:

- **South Central Ambulance (RYE) and South East Coast Ambulance (RYD) are forming a
  joint Group model**: a shared Group Chair already in post (since spring/June 2026) and a
  shared Group Chief Executive, Simon Ashton, starting autumn 2026 — described by NHS
  England as the first ambulance-trust group of its kind. Confirmed independently from
  both trusts' own board pages and annual reports, with RYD's current CEO recorded as
  Interim (Jennifer Allan) following Simon Weldon's departure 17/04/2026.
- **The North East London Procurement Partnership (NELPP), hosted by Barts Health, live
  from 01/01/2026, now covers four trusts, not just Homerton.** East London NHS Foundation
  Trust (RWK) and North East London NHS Foundation Trust (RAT) were both tested this
  batch. RWK's own site does not yet mention it (sourced from Barts Health's own news page
  instead, flagged as third-party-confirmed-only); RAT's position is the same — confirmed
  only via Barts Health, not yet on RAT's own site or in its own annual report. Recorded as
  prose with that provenance caveat in both entries, not as an equally-weighted fact.

One partial confirmation, recorded with its gap rather than smoothed over: Torbay and
South Devon (RA9) confirmed it has joined a "One Devon Procurement Service" hosted by
University Hospitals Plymouth (both facts stated directly in RA9's own annual report and
its external auditor's report), but neither of RA9's own documents gives the December 2025
formation date, the five-member count or the 44 WTE transfer figure the worklist's earlier
Plymouth-side finding asserted — those details stay attributed to Plymouth's own side only,
not repeated as RA9-confirmed.

**Batch fifteen (03/09/2026, `35b1d0a`) closed 10 of 10**:
Bradford District Care, Oxleas, Cumbria/Northumberland/Tyne and Wear, Berkshire Healthcare,
Cambridgeshire and Peterborough, Herefordshire and Worcestershire, Lincolnshire Partnership,
Nottinghamshire Healthcare, East of England Ambulance, London Ambulance. All 49
source/reportFact/people URLs HTTP-checked 200. Royal Free (RAL) skipped again, still
Cloudflare-blocked — see the standing flag below. Structural findings worth carrying
forward: Oxleas buys through SmartTogether (hosted by Guy's and St Thomas', spanning 5
south London trusts) and is separately the Lead Provider for the Adult Secure Provider
Collaborative; CNTW's procurement sits inside its wholly-owned NTW Solutions Ltd
subsidiary; Berkshire Healthcare hosts the 7-county South East Pharmacy Procurement
Service; Lincolnshire Partnership has no in-house procurement at all, delivered by ULTH.
⚠️ **Bradford District Care's own profile found a Chair-in-Common with Airedale
(substantive Chair, from 1/3/2026) — it did NOT independently confirm the AGH Solutions
shared-procurement link this worklist's own table (below, "Airedale hosts a shared
procurement function...") asserts.** Not a contradiction necessarily — a shared chair and
a shared procurement subsidiary can coexist — but the AGH Solutions claim wasn't
re-verified this batch and needs checking against Bradford District Care's own site before
being repeated as fact.

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

**Batch thirteen (03/09/2026) closed 10 of 10**: The Robert Jones and Agnes Hunt Orthopaedic
Hospital (RL1), Sussex Community (RDR), The Royal Orthopaedic Hospital (RRJ), Isle of Wight
(R1F), The Walton Centre (RET), Gateshead Health (RR7), Liverpool Women's (REP), Sheffield
Children's (RCU), Midlands Partnership University (RRE), Royal National Orthopaedic Hospital
(RAN). Royal Free (RAL) skipped again, still Cloudflare-blocked, per the standing flag below.
Of 41 unique source/linkedin URLs cited across the batch, 38 verified 200 on the orchestrator's
own sweep; 3 LinkedIn profile URLs (Angela Mulholland-Wells at RL1, Doris Olulode at RAN,
Siobhan Melia at RDR) consistently returned LinkedIn's bot-block (999) on repeated curl retries
with full browser headers, on a `uk.linkedin.com` subdomain retry, and via a live Browser-pane
check that redirected to LinkedIn's generic sign-up wall rather than the named profile — a
different and less conclusive signal than the "confirmed live via a real browser" pattern from
batches five and twelve, so all three were dropped from the published entries rather than kept
on trust; two other LinkedIn URLs in the same batch (Mike Jennings at RDR, Matthew Hartland at
RRJ) verified cleanly at 200 and were kept. One name-spelling slip caught and fixed before
merge, the same recurring class of error as batches nine and twelve: an agent wrote "The Robert
Jones And Agnes Hunt..." (capital And); the ODS/trustDirectory name spells it lowercase "and".
A more substantive fix: the orchestrator's own trust-specific hint to the RDR agent wrongly
asserted that a community trust's layer-1 `wl` figure might describe a single service line
rather than the whole trust; `trust-pressures.json`'s own `fieldMeanings` block defines `wl` as
"total incomplete RTT pathways (the waiting list)" for every trust, community or acute, so this
was wrong and the agent's resulting context paragraph incorrectly told readers not to treat
RDR's 13,214 waiting list as trust-wide. Corrected before merge: RDR's context now states the
trust-wide RTT position directly (13,214 total, 56.8% within 18 weeks, 15.3-week median) and
uses the trust's own 2025/26 annual report to explain why it is effectively an MSK number in
practice (almost 80% of patients waiting, and the majority of 52-week-plus waits, referred to
Sussex MSK Health) rather than pretending the trust-wide figure does not exist. **Lesson: a
hint written into the dispatch prompt is exactly as capable of publishing a wrong fact as a
hint an agent invents on its own** — check it against the schema's own field definitions before
handing it to an agent, not just against another trust's profile. Isle of Wight (R1F) confirmed
it is no longer the fully-integrated acute/community/mental-health/ambulance trust the layer-1
directory implies: community, mental health and learning disability services transferred to
Hampshire and Isle of Wight Healthcare NHS FT on 01/05/2024, and its own procurement is hosted
by Portsmouth Hospitals University NHS Trust within a wider IWT/Portsmouth NHS Group. The
Walton Centre (RET) confirmed, refined and extended the Health Procurement Liverpool finding
from Alder Hey's side in batch twelve: HPL covers clinical AND business/corporate spend, not
clinical-only, and Cheshire and Wirral Partnership NHS FT joined HPL in 2025, widening it
beyond the four trusts named in batch twelve's table. Liverpool Women's (REP) tested and
refuted the same HPL hint on its own side: its group arrangement is the separate NHS University
Hospitals of Liverpool Group (with Liverpool University Hospitals, formed 01/11/2026), not HPL,
and its own site (`liverpoolwomens.nhs.uk`, now 301-redirecting into `uhliverpool.nhs.uk`) is
genuinely Cloudflare-blocked, the same total-block pattern as batch five's Liverpool University
Hospitals finding — leadership was sourced from sister-trust Liverpool Heart and Chest's board
page instead. Sheffield Children's (RCU) confirmed it is hosted, not peer-linked, by Sheffield
Teaching Hospitals' own procurement department, per a direct quote on STH's own site. Royal
Orthopaedic Hospital (RRJ) found a genuine discrepancy rather than smoothing it over: Birmingham
Community Healthcare's own procurement page places RRJ inside the BSOL Procurement Collaborative
hosted by University Hospitals Birmingham, but RRJ's own 2024/25 annual report shows its own
CFO holding Board-level accountability for procurement and never mentions the collaborative,
so both are recorded, flagged as unresolved, rather than one silently overwriting the other.
Gateshead (RR7) refuted the orchestrator's North East collaborative-procurement hint outright
(own in-house procurement plus a wholly-owned subsidiary, QE Facilities Ltd) but surfaced an
unhinted finding instead: a shared chair (Sir Paul Ennals) across Gateshead, Newcastle upon
Tyne Hospitals and Northumbria Healthcare since May 2025, plus a joint bowel-screening service
with South Tyneside and Sunderland — governance and clinical links, not a buying one.

**Batch fourteen (03/09/2026) closed 1 of 10, the smallest close on record, because of an
infrastructure failure, not a research one.** The ten trusts taken off the top of the acute
table (in order, after skipping RAL again) were Great Ormond Street (RP4), Shropshire
Community Health (R1D), Royal Papworth (RGM), Liverpool Heart and Chest (RBQ), South West
Yorkshire Partnership (RXG), Lancashire & South Cumbria (RW5), Kent Community Health (RYY),
The Christie (RBV), The Royal Marsden (RPY) and Cornwall Partnership (RJ8). Layer-1 extraction
worked normally for all ten (it reads local repo data, no network needed); the research step
did not. This cloud session's outbound network access was blocked by an organisation-level
egress policy for the whole batch, confirmed session-wide rather than trust-specific: the
agent proxy returned a 403 "policy denial" on every CONNECT attempt, including to neutral
control domains with no NHS connection at all (`example.com`, Wikipedia, Google), not just to
the ten trusts' own sites. This is a different failure class from the Cloudflare/Akamai
per-domain blocks logged below (Royal Free, `uhliverpool.nhs.uk`) and from LinkedIn's bot-block:
those are one domain refusing one client; this was every domain refusing this session.
Nine of the ten research agents correctly could not do primary-source research under that
block. Two (RW5, Lancashire & South Cumbria; RJ8, Cornwall Partnership) wrote no profile file
at all rather than publish anything built from a search-engine summary, the most defensible
response given "publishing nothing beats publishing thin evidence." The other seven (RP4,
R1D, RGM, RBQ, RXG, RYY, RBV) fell back to WebSearch (the only fetch tool still working) to
synthesise facts, disclosed that plainly inside each profile's own `structure` field, and in
RBQ's case additionally left `reportFacts`/`people` empty rather than assert anything from a
snippet. That disclosure is exactly right, but a WebSearch summary is explicitly not a valid
source under HUB-VERIFICATION-STANDARD rule 9 ("a web-search summary is a pointer to a source,
never the source itself") even when the cited URL happens to still resolve, so none of those
seven were merged; all seven stay in the queue, unchanged, for a batch run once egress is
confirmed working, and their draft JSON is kept in `tmp/trust-batch/` (gitignored) rather than
discarded, so the research is not lost. The tenth, Royal Marsden (RPY), is the one genuine
exception: its main domain (`royalmarsden.nhs.uk`) was blocked identically to the others, but
the trust hosts its Annual Report and Board papers as PDFs on its own S3 asset bucket
(`rm-live-drupal-files.s3.eu-west-2.amazonaws.com`), which the egress policy did not catch, so
the agent fetched and read those PDFs directly rather than searching for them. All three
distinct source URLs independently re-checked 200 by the orchestrator. That profile met the
same bar as any other batch's and was merged on its own. Two structural findings worth keeping:
Royal Marsden buys for itself (no host/hosted group relationship found) and runs its own
wholly-owned commercial subsidiary, RM Medicines Limited; and RM Partners, which it hosts, is a
clinical pathway alliance, not a procurement structure, so it should not be read as one.
**Egress was checked before the re-run below and was fine on this machine**, so the block was
specific to that cloud session's organisation policy, not to the trusts or this repo. Keep the
check as a standing first step for any batch: it costs one `curl` against a neutral control
domain plus a trust domain, and it tells you in seconds whether a batch is worth dispatching.

**Batch fourteen, second run (03/09/2026), closed 10 of 10.** Re-ran the nine trusts the blocked
cloud session had returned to the queue, plus Clatterbridge (REN) to make ten: Great Ormond Street
(RP4), Shropshire Community Health (R1D), Royal Papworth (RGM), Liverpool Heart and Chest (RBQ),
South West Yorkshire Partnership (RXG), Lancashire & South Cumbria (RW5), Kent Community Health
(RYY), The Christie (RBV), Cornwall Partnership (RJ8), Clatterbridge (REN). Royal Free (RAL) skipped
again. Egress was confirmed working first (`example.com` plus four trust domains all 200), which is
why this run behaved normally where the previous one could not. **All 26 distinct source URLs
checked 200**, layer-1 cross-checks clean on all ten, and no LinkedIn URL was cited anywhere in the
batch: LinkedIn's HTTP 999 bot-block is unchanged, so `linkedin` was left empty by instruction
rather than each agent rediscovering it.

Structural findings worth carrying forward, several of which close questions left open by earlier
batches:

- **Health Procurement Liverpool is now confirmed from BOTH remaining members' own sides**, not
  just from The Walton Centre's. Liverpool Heart and Chest's own Freedom of Information response
  (ref FOI202526/021, published on `lhch.nhs.uk`) states its scheme of delegation delegates
  procurement and financial approval to Health Procurement Liverpool and that "the staff in these
  terms are hosted by the Walton Centre", with IT procurement staff hosted by Alder Hey instead.
  Clatterbridge's own procurement page states its procurement service is provided by Health
  Procurement Liverpool at The Walton Centre. The IT-at-Alder-Hey split is new and was not visible
  from Walton's side. **For a rep, both trusts are the wrong door for a procurement decision.**
- **Clatterbridge is NOT yet in the NHS University Hospitals of Liverpool Group (UHLG)**, expected
  2027/28 per its own page and Cheshire and Merseyside ICB's own site. HPL and UHLG remain distinct
  structures and must not be conflated, which is the same warning batch thirteen recorded.
- **Lancashire & South Cumbria (RW5) IS a One LSC partner and has transferred procurement staff
  into it** ("we are a One LSC partner... the Trust transferred seven members of staff from the
  Trust's procurement team", its own 2024/25 annual report), so the mental health trust is inside
  the collaboration, not just the acutes. But its own annual report does NOT name a host, so the
  "hosted by East Lancashire" reading still rests only on the other trusts' documents. Recorded as
  partly confirmed rather than resolved.
- **Shropshire Community buys through a consortium, not for itself**: "All consumable goods and most
  contracts are purchased through Shropshire Healthcare Procurement Service (SHPS), a consortium of
  Shropshire healthcare providers, hosted by the Shrewsbury and Telford Hospitals NHS Trust" (its own
  2024/25 annual report). Estates maintenance sits with Midlands Partnership NHS Foundation Trust.
- **Royal Papworth buys for itself.** Campus co-location with Cambridge University Hospitals on the
  Cambridge Biomedical Campus, and genuine joint clinical work including a shared electronic patient
  record procurement, did NOT turn out to be shared buying. This is the co-location version of the
  recurring "shared leadership does not mean shared buying" lesson, and the hint was tested rather
  than assumed.
- **Cornwall Partnership runs its own procurement governance** (its own Standing Financial
  Instructions and Scheme of Delegation, re-approved 2026/27 by its own Board) despite extensive
  shared senior leadership with Royal Cornwall Hospitals. Fourth confirmed instance of shared
  leadership without shared buying.
- **Great Ormond Street buys largely for itself but is a member of the NHS London Procurement
  Partnership**, confirmed on LPP's own member list rather than GOSH's site, and its board approved
  a "hybrid procurement operating model" during 2025/26 alongside a review of rising procurement
  waivers. **Kent Community Health** and **The Christie** both run their own in-house functions,
  The Christie publishing a live procurement pipeline and a contracts-over-£25k register.

**Clatterbridge's own domain is a genuine 403 block to automated clients**, confirmed on the
homepage, board and procurement pages with a full browser header set, not just plain curl. Its
`/application/files/` document path is NOT behind the block, so the annual report PDF was fetched
live at 200; the two remaining page-level sources are Wayback Machine captures of the trust's own
pages, each individually confirmed 200 this session. Add it to the obstacles table below. Note the
archive.org rate limit: three archive URLs returned **429** on the first concurrent sweep and 200
on a serial retry with backoff. **A 429 from archive.org is rate limiting, not a dead link**, and
must be retried serially before a source is dropped, exactly like the Cloudflare/Akamai
false-negatives. One fact originally cited to an archived page was moved onto the live annual report
PDF instead, which states it directly, so the profile leans on the archive less than it did.

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
| Alder Hey Children's (RBS, profiled batch twelve) | The Walton Centre (RET, profiled batch thirteen), Clatterbridge Cancer Centre (REN, not yet profiled), Liverpool Heart and Chest (RBQ, not yet profiled) | Health Procurement Liverpool (HPL), hosted at The Walton Centre. **Confirmed and widened from Walton's own side in batch thirteen**: Walton's own 2025/26 annual report states it "established Health Procurement Liverpool (HPL) three years ago", and covers both clinical AND business/corporate spend, not clinical-only as the batch-twelve framing (from Alder Hey's side) implied. Cheshire and Wirral Partnership NHS FT also joined HPL in 2025, so it now covers more organisations than the four named in the original batch-twelve finding. |
| Airedale (RCF, profiled batch twelve) | Bradford District Care (TAD, not yet profiled) | Airedale hosts a shared procurement function, AGH Solutions Ltd, also covering Bradford District Care and ILS LLP, per Airedale's own "Doing business with us" page (batch twelve). Governance detail on the Bradford District Care/ILS LLP side is not yet established; confirm when Bradford District Care is profiled. |
| Tameside and Glossop (RMP, profiled batch twelve) | Stockport (not yet on this list) | Shares a Chief Medical Officer (Dilraj Sandher) and a Director of Informatics (Peter Nuttall) with Stockport, and is running a parallel/coordinated EPR procurement (Altera, March 2026) alongside Stockport. Procurement itself is not established as joint; Tameside appears to run its own function (own Head of Procurement contact, own tender notices) but no dedicated procurement page was found to confirm it independently. |
| Sheffield Children's (RCU, profiled batch thirteen) | Sheffield Teaching Hospitals (not yet profiled) | Sheffield Children's is HOSTED, not a peer partner: Sheffield Teaching Hospitals' own site states in its own words "Our Procurement Department manages procurement and logistics for both our own hospitals and services, as well as for Sheffield Children's NHS Foundation Trust." Confirmed from the host's own side, batch thirteen. |
| Clatterbridge Cancer Centre (REN), Liverpool Heart and Chest (RBQ) | Liverpool Women's (REP, profiled batch thirteen) | Liverpool Women's is NOT in the Health Procurement Liverpool group above; its own group arrangement is the separate NHS University Hospitals of Liverpool Group (UHLG), formed 1 November 2024 with Liverpool University Hospitals, confirmed via NHS Cheshire and Merseyside's own announcement. Walton Centre is named in UHLG/LAASP integration plans but on a later 2026/27 date, so the two Liverpool group structures (HPL and UHLG) are still distinct as of this batch, not yet merged. Liverpool Women's own site now redirects entirely into `uhliverpool.nhs.uk`, which is genuinely Cloudflare-blocked, the same total-block pattern as batch five. |
| South East Coast Ambulance (RYD, profiled batch sixteen) | South Central Ambulance (RYE, profiled batch sixteen) | Forming a joint Group model: shared Group Chair already in post (since spring/June 2026), shared Group Chief Executive Simon Ashton from autumn 2026. Confirmed independently from both trusts' own board pages and annual reports, the first ambulance-trust group of its kind per NHS England. Not a procurement-only link; both currently still run separate procurement functions. |
| North East London NHS Foundation Trust (RAT, profiled batch sixteen) | Barts Health (RF4, profiled), Homerton (RQX, profiled batch eleven), East London NHS Foundation Trust (RWK, profiled batch sixteen) | North East London Procurement Partnership, hosted by Barts Health, live from 01/01/2026, confirmed to now cover four trusts (Barts, Homerton, ELFT, NELFT). RAT's and RWK's own membership is confirmed only via Barts Health's own news page, not yet stated on either trust's own site or annual report — recorded with that provenance caveat, not as an equally-weighted fact. |
| Torbay and South Devon (RA9, profiled batch sixteen) | Royal Devon (RH8, profiled), University Hospitals Plymouth (RK9, profiled) | One Devon Procurement Service, hosted by Plymouth. RA9's own annual report and its external auditor's report both confirm membership and the Plymouth host directly. The December 2025 formation date, five-member count and 44 WTE transfer figure remain attributed to Plymouth's own side only — RA9's own documents don't repeat those specifics. |
| Leicestershire Partnership (RT5, profiled batch seventeen) | Northamptonshire Healthcare (RP1, profiled batch sixteen) | Group model since 2019: shared Chief Executive (Angela Hillery), shared CFO, Strategy Director and Chair. Confirmed on RT5's own Trust Board page. No leadership link to University Hospitals of Leicester (RK5) despite sharing a city — that was tested and refuted, not assumed. Procurement is NOT shared: RT5 runs its own in-house department, separate from the leadership arrangement. |

## Known fetching obstacles

- **Cloudflare, total block:** Royal Free London. Needs a human with a browser.
- **403 to everything, including a full browser header set:** `clatterbridgecc.nhs.uk` rendered
  pages (homepage, board, procurement). Its `/application/files/` document path is NOT blocked,
  so annual reports and board packs are still fetchable live. Page-level facts need a Wayback
  capture of the trust's own page.
- **archive.org HTTP 429:** rate limiting, NOT a dead link. Seen when a batch sweep checks several
  Wayback URLs concurrently. Retry serially with 25 to 45 seconds of backoff before dropping one.
- **Akamai, 403 to plain curl:** `royaldevon.nhs.uk`. Works with a full browser header set
  (User-Agent plus Accept, Accept-Language, Sec-Fetch-*). Links are live, not dead.
- **403 to WebFetch but fine via curl:** `uhcw.nhs.uk`.
- **403 to plain curl AND to full-browser-header curl/urllib, but fine via WebFetch:**
  `hpft.nhs.uk`, found batch eighteen — the reverse of the Royal Devon pattern above. Four
  URLs on this domain all confirmed genuinely live via WebFetch before merge; the automated
  gate check will keep failing them, so verify manually rather than treating the gate's
  result as final for this domain specifically.
- **403 to curl:** Find a Tender notice pages. Usable as evidence read another way, but do
  not cite one as a `source` URL that will be checked.
- **Scanned-image PDFs that will not extract:** Royal Wolverhampton's 2025/26 financial
  statement pages. Fall back to the prior year and say which year the figure is.
- **LinkedIn's own bot-block (HTTP 999):** seen in batch thirteen on three profile URLs,
  consistent across plain curl, curl with full browser headers, and a `uk.linkedin.com`
  subdomain retry. Unlike the Cloudflare/Akamai/Imperva blocks above, a live Browser-pane
  check of one of these did NOT confirm the named profile — it redirected to LinkedIn's
  generic sign-up wall with no name-identifying content, a materially weaker signal than
  the "confirmed live via a real browser" outcome batches five and twelve got on trust-site
  blocks. Treat a 999 that a real-browser check cannot positively confirm as genuinely
  unverifiable and drop the link, rather than assuming it is the same class of false-negative
  as a Cloudflare-blocked NHS domain.

## Acute and specialist trusts — 1 remaining, by waiting list

| # | Trust | ODS | Waiting list | Seg | Spec hits |
|---|---|---|---|---|---|
| 1 | Royal Free London NHS Foundation Trust | RAL | 139,476 | 3 | 0 |

## Community, mental health and ambulance trusts — 20 remaining

No RTT return and no acute oversight segment, so layer 1 is thinner by design.

| # | Trust | ODS | Spec hits | Named contacts |
|---|---|---|---|---|
| 1 | North Staffordshire Combined Healthcare NHS Trust | RLY | 0 | 4 |
| 2 | Tees, Esk and Wear Valleys NHS Foundation Trust | RX3 | 0 | 4 |
| 3 | Pennine Care NHS Foundation Trust | RT2 | 0 | 3 |
| 4 | Birmingham and Solihull Mental Health NHS Foundation Trust | RXT | 0 | 3 |
| 5 | Derbyshire Community Health Services NHS Foundation Trust | RY8 | 0 | 3 |
| 6 | East Midlands Ambulance Service NHS Trust | RX9 | 0 | 3 |
| 7 | Hertfordshire Community NHS Trust | RY4 | 0 | 3 |
| 8 | North West Ambulance Service NHS Trust | RX7 | 0 | 3 |
| 9 | West Midlands Ambulance Service University NHS Foundation Trust | RYA | 0 | 3 |
| 10 | Devon Partnership NHS Trust | RWV | 0 | 2 |
| 11 | Rotherham Doncaster and South Humber NHS Foundation Trust | RXE | 0 | 2 |
| 12 | East of England Community Health and Care NHS Trust | RY3 | 0 | 2 |
| 13 | Leeds Community Healthcare NHS Trust | RY6 | 0 | 2 |
| 14 | North East Ambulance Service NHS Foundation Trust | RX6 | 0 | 1 |
| 15 | South West London and St George's Mental Health NHS Trust | RQY | 0 | 1 |
| 16 | Wirral Community Health and Care NHS Foundation Trust | RY7 | 0 | 1 |
| 17 | Black Country Healthcare NHS Foundation Trust | TAJ | 0 | 0 |
| 18 | Coventry and Warwickshire Partnership NHS Trust | RYG | 0 | 0 |
| 19 | Sheffield Health Partnership University NHS Foundation Trust | TAH | 0 | 0 |
| 20 | The Online NHS Trust | K0N6A | 0 | 0 |

## Welsh trusts — excluded, need their own template

None of these are English trusts with an ICB; each has `nation: Wales` and `icb: null` in
the directory, files no RTT return, and buys through NHS Wales Shared Services Partnership
rather than an English ICB/framework route. Do not pick any of these up until a Welsh
version of the layer-2 template exists.

| Trust | ODS | Why excluded |
|---|---|---|
| Velindre NHS Trust | RQF | Tops every ranking on 22 specialities and 38 matching notices — deliberately left out since before batch three. |
| Public Health Wales NHS Trust | RYT | A national public-health body, not a hospital/community provider — no waiting list, no ward-based procurement to profile. Pulled from the queue before batch sixteen's dispatch, 04/09/2026. |
| Welsh Ambulance Services NHS Trust | RT4 | Same nation/ICB pattern as the two above. Pulled from the queue before batch sixteen's dispatch, 04/09/2026. |
