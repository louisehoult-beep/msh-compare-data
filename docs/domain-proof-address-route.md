# A second domain proof: registered office address

Written 08/09/2026 by the `differentiator-framework-coverage` run, working the
Operating Theatres Equipment and Related Accessories and Services framework, and
added to 09/09/2026 by the same routine working Ultrasound Scanners and
Associated Options and Related Services.

**RULED IN, 20/09/2026.** The address route is now tier 2 of the identity policy
table's `domain-proof-tier` policy (`data/identity-vocabulary-policy.json`):
below an on-site registration number, above a name match. OUTSTANDING ^o363 is
answered. The proofs below were applied to `data/supplier-seed.json` the same
day, with `"route": "registered-address"` recorded on each accepted link so the
basis of every domain stays auditable.

**Two of the proposals below were REFUSED when the policy was applied**, by the
policy's own guard that a shared serviced-office address is no proof at all.
They are struck through in the tables and the reasons are in
"Refused on applying the policy" at the foot of this document. Read that section
before re-proposing either.

**Exception: Probo Medical's domain WAS added, 10/09/2026, on separate grounds.**
Its `probomedical.co.uk` was not written on this document's address-route
reasoning: the seed record's own `background` section already cited
`probomedical.co.uk / Companies House 03466990 / businesswire.com` as the source
for an identity correction made 20/07/2026, well before this proposal existed, and
the URL was independently confirmed live (HTTP 200) on 10/09/2026. That is
narrower evidence than the address route below.

## The problem it answers

`seed_supplier_domains.py` records a domain on one strong proof: the site prints
a company registration number, next to registration wording, matching the number
already held in `company-financials.json`. That bar exists for a good reason —
the name tier was measured on 14/08/2026 and 124 of 128 domains it had "proved"
were refused on re-examination.

But most UK supplier sites never print their registration number anywhere the
script looks. On this framework, 15 of 43 awarded suppliers have no website
recorded at all, and that — not the crawler — is what caps coverage at 14.0%.

## The route, as ruled

**ADDRESS.** The site publishes a postal address, and that address matches the
registered office Companies House holds for a company whose *exact* registered
name is the awarded supplier name.

It is the same shape of evidence as REGISTRATION — a unique identifier held by
Companies House, found on the company's own site — and it is not circular in the
way the name tier was: nothing about a company's name predicts its street
address, so an address match cannot be manufactured by guessing a domain from a
name. It is not a fuzzy match either; a partial or town-only match is a miss.

Two things it is NOT, and a coded version must enforce both:

- **It is not a proof of the company NUMBER.** Every number below is still a
  `companyNumberCandidate`, unconfirmed under HUB-VERIFICATION-STANDARD rule 11.
  The address proof says "this domain belongs to the company that owns this
  registered office"; it does not upgrade the number.
- **A near-miss is a refusal.** Carleton Medical failed exactly here: its site is
  a surgical-laser company of the right trade and the right name, but the address
  it prints (Newport NP20 2NN) is not the registered office of CARLETON MEDICAL
  LIMITED (Chesham HP5 2BD). Nothing was recorded for it.

## What it proves on this framework

Read 08/09/2026. Companies House pages read from
`find-and-update.company-information.service.gov.uk/company/<number>`.

| Supplier | Domain | Address on the site | Companies House registered office |
|---|---|---|---|
| Brandon Medical Company Ltd | brandon-medical.com | Brandon Medical Co Ltd, Elmfield Road, Morley, Leeds LS27 0EL | BRANDON MEDICAL COMPANY LIMITED (02827189) — Elmfield Road, Morley, Leeds, LS27 0EL |
| Erbe Medical UK Ltd | uk.erbegroup.com | Erbe Medical UK Ltd, The Antler Complex, 1A Bruntcliffe Way, Morley, LS27 0JG, Leeds | ERBE MEDICAL UK LIMITED (03184850) — 1a The Antler Complex, Bruntcliffe Way Morley, Leeds, LS27 0JG |
| Ferno (UK) Limited | ferno.com/uk | Ferno (UK) Limited, Ferno House, Stubs Beck Ln, West 26 Industrial Estate, Cleckheaton BD19 4TZ | FERNO (UK) LIMITED (01007475) — Ferno House, Stubs Beck Lane, Cleckheaton, West Yorkshire, BD19 4TZ |
| Fulbourn Medical | fulbournmedical.com | Fulbourn Medical, Unit 1 Falcon Court, Hinchingbrooke Business Park, Huntingdon, Cambridgeshire PE29 6AH | FULBOURN MEDICAL LIMITED (02764966) — Unit 1 Falcon Court Falcon Road, Hinchingbrooke Business Park, Huntingdon, Cambridgeshire, PE29 6AH |
| Ryna Medical Uk Limited | rynamedical.co.uk | RYNA MEDICAL UK LIMITED, Backfield Farm Business Park, Wotton Road, Iron Acton, Bristol BS37 9XD | RYNA MEDICAL UK LIMITED (06800377) — Unit A12 Backfield Farm Business Park Wotton Road, Iron Acton, Bristol, BS37 9XD |
| ~~Soluvos Medical Ltd~~ REFUSED 20/09 | soluvos.com | SOLUVOS MEDICAL Ltd., International House, 36-38 Cornhill, City of London EC3V 3NG | SOLUVOS MEDICAL LTD (10982713) — International House, 36-38 Cornhill, London, EC3V 3NG |

Ferno carries a caveat of its own even if the route is accepted: `ferno.co.uk`
redirects to the UK section of the group site, so the host a crawler would read
is `ferno.com` and the range it would return is Ferno's global catalogue, not
Ferno (UK) Limited's. Record the domain if you like; do not crawl it without
restricting the path.

## Refused this run, and why

- **Carleton Medical** — address mismatch, above.
- **NJ Devices Ltd t/a Ocean Med** — ocean-med.co.uk is the right trade and prints
  a London W1W 5PF address, but the seed holds no company number for NJ Devices
  Ltd to check it against.
- **Novus Med Ltd**, **Lynton Lasers** — sites answer but publish no address any
  route could read (both render their contact details in script).
- **Promed Limited**, **SRA Developments**, **Newmaw Medical Ltd**, **Ingles Ltd**,
  **Richard Wolf UK** — no candidate domain answered, or the one that did belongs
  to an unrelated business.

## What it proves on Ultrasound Scanners and Associated Options and Related Services

Read 09/09/2026, same method and same bar. This framework has 21 awarded suppliers,
3 publishing, and 4 of the 5 remaining pieces of work on it were "supplier has no
website recorded" — the same cap the Operating Theatres run found.

| Supplier | Domain | Address on the site | Companies House registered office |
|---|---|---|---|
| FUJIFILM Sonosite Ltd | www.sonosite.com | "United Kingdom — FUJIFILM Sonosite Ltd. Fujifilm House Whitbread Way Bedford MK42 0ZE", on the site's own distributor/contact page `/uk/contactus` | FUJIFILM SONOSITE LTD (04104159) — Fujifilm House, Whitbread Way, Bedford, Bedfordshire, England, MK42 0ZE |
| Probo Medical (formerly MIUS) | www.probomedical.co.uk | "Probo Medical Ltd" (privacy policy) and "Mount Court, Edison Close, Waterwells Business Park, Gloucester, Gloucestershire, GL2 2FN" (Get in Touch) | PROBO MEDICAL LTD (03466990) — The Electron Building Mount Court, Edison Close, Waterwells Business Centre, Gloucester, Gloucestershire, England, GL2 2FN |

Probo carries a second, independent confirmation that the other six do not, and it is
worth noting because it is the strongest single piece of identity evidence in this
document. Companies House records 03466990's previous names as MOUNT INTERNATIONAL
UNITED SERVICES LTD (16 Sep 2014 to 01 Nov 2021) and MOUNT INTERNATIONAL ULTRASOUND
SERVICES LTD (17 Nov 1997 to 16 Sep 2014). The Hub's record is canonically named
"Probo Medical (formerly MIUS)" and already carries both of those as aliases, so the
register itself confirms the record's own naming — nothing here rests on the two
names resembling each other.

Sonosite carries a caveat of the same kind as Ferno's, and it is decisive rather than
cosmetic: the route is accepted and the domain IS now recorded, but it cannot be crawled. Read
09/09/2026, `sonosite.com` and `www.sonosite.com` both reset the connection for
`crawl_supplier_site.py` (ConnectionResetError, errno 54) while answering HTTP 200 to
a browser-shaped request, and `robots.txt` allows general crawling — so it is CDN bot
filtering, not a policy refusal and not an unreachable host. Recording the domain
would give this supplier a member-facing website link; it would not give it a product
range. That read outcome is deliberately NOT recorded in
`data/supplier-products.json`: a refusal there suppresses a re-attempt for 90 days, and
if the ADDRESS route is ruled in, the next run should be free to try this site properly
rather than find it pre-refused on a domain the seed never accepted.

### Refused on this framework, and why

- **Imaging First Ltd** — refused, and worth recording so it is not retried. The
  company is real and on the register (IMAGING FIRST LIMITED, 07896665, active, 8
  Charter Gate Clayfield Close, Moulton Park Industrial Estate, Northampton NN3 6QF;
  previous name OPTIVI SCREENING LIMITED, which the seed already carries as an alias).
  `imagingfirst.co.uk` is plainly an ultrasound business of the right trade — "Systems
  and Probes", "Probe Repairs", "QA Testing" — but read in full on 09/09/2026 its
  home, About, Contact and Privacy pages publish NO company registration number, NO
  VAT number and NO registered address: the only postal detail anywhere on the site is
  a PO Box (PO Box 1593, Northampton NN2 1GT), which is not a registered office and
  matches nothing Companies House holds. Its officers do not appear on the site either,
  so there is no person-level cross-check. Neither the REGISTRATION route nor the
  proposed ADDRESS route can reach it, and the only thing linking site to company is
  the name plus the town — which is exactly the circular evidence the name tier was
  refused for on 14/08/2026. Nothing recorded.
- **Hitachi Medical Systems UK Ltd** — not a domain question. The awarded name is the
  former registered name of Companies House 03218117, now FUJIFILM HEALTHCARE UK
  LIMITED, and a Companies House advanced search for company names containing
  "Hitachi" returned no companies at all on 09/09/2026, so no separate entity of this
  name survives on the register. The merge with the Hub's "Fujifilm Healthcare UK"
  record is already raised for Lou's decision (OUTSTANDING ^o376) and the evidence is
  on that record's `companyNumberNote`. Whatever she decides, the entity's site is the
  one already refused as `fujifilm.com` on 05/09/2026, so there is no crawlable route
  to a product range under this name either way.

## What it proves on Minimally Invasive Surgery, Related Equipment and Accessories

Read 13/09/2026 by the `outstanding-sweep` task, working OUTSTANDING ^o463. Same method,
same bar, and again **nothing written to `data/supplier-seed.json`** — the route is still
unruled (^o363).

| Supplier | Domain | Address on the site | Companies House registered office |
|---|---|---|---|
| ~~Minitouch Ltd~~ REFUSED 20/09 | minitouch.eu | "1 Hutton Close, S Church Enterprise Park, Bishop Auckland, DL14 6XG UK", in the footer of the company's own Modern Slavery Statement (`minitouch.eu/Modern Slavery Statement.pdf`), which names "Minitouch LTD" throughout and describes it as selling "medical devices for women's health in the UK and Europe" | MINITOUCH LTD (07933081) — 1 Hutton Close, South Church Enterprise Park, Bishop Auckland, England, DL14 6XG |

**This corrects ^o463's premise, which was wrong.** That finding recorded minitouch.eu
and minitouch.us as sites that "do not clearly belong to this UK company", on the basis
that the Minitouch endometrial ablation device's US PMA applicant is MicroCube LLC. The
register settles it the other way: Companies House records MINITOUCH LTD (07933081) as
**previously MICROCUBE LTD** (02/02/2012 to 15/05/2014), which is the same corporate
lineage, not a coincidence of product naming. `data/company-financials.json` already
holds that previous name on the Minitouch record.

So the identity question ^o463 was raised for is answered, and it was never a decision
for Lou: there is one candidate, not two, and the evidence is primary. What actually
blocks the domain being recorded is the unruled ADDRESS bar above — Minitouch publishes
no registration number anywhere this route can read (home, contacts, Modern Slavery
Statement and Carbon Reduction Plan all read in full on 13/09/2026; the contacts page
gives only "Minitouch, Ltd." and an email address). It is therefore an eighth supplier
waiting on ^o363, not a separate open item.

Two notes for whoever implements the ruling:

- The site is four static HTML pages and three PDFs, with no product catalogue at all.
  Recording the domain would give this supplier a member-facing website link; as with
  Sonosite above, it would not give it a product range. No read outcome has been
  recorded in `data/supplier-products.json`, for the same reason given there.
- The seed record carries the framework award twice (one row with `dates: null` and no
  `source`, one full `nhssc-brief` row, both citing reference 2026/S 000-061906). That
  is the same duplicate-award shape as OUTSTANDING ^o206 and is noted here only so it is
  not mistaken for two separate awards.

## Policy 2 applied to its own worked example, 20/09/2026 evening

The identity-vocabulary-policy table's `domain-proof-tier` policy (`^o487`) named these
four as "the same shape" as FUJIFILM Sonosite. Read against the shared-address guard,
same method, same bar, using Companies House advanced search by exact registered
address (not just postcode) as the count.

| Supplier | Outcome | Domain | Site address | Companies House registered office | Shared-address count |
|---|---|---|---|---|---|
| Globus Medical UK Ltd | Accepted | globusmedical.com | "United Kingdom — 5 Upper Priory Street, Northampton, NN12PT, United Kingdom" (globusmedical.com/about/contact/) | GLOBUS MEDICAL UK LTD (06491893) — 5 Upper Priory Street, Northampton, NN1 2PT | 2 (Globus Medical UK Ltd + NuVasive UK Limited — the 2023 merger, not an agent) |
| NuVasive UK Ltd | Accepted | nuvasive.com/uk-and-ireland/ | Same globusmedical.com contact page (nuvasive.com itself returns HTTP 403 to a plain fetch and forces an interactive Cloudflare human-check in the browser pane, not solved) | NUVASIVE UK LIMITED (05518404) — 5 Upper Priory Street, Northampton, NN1 2PT | 2 (as above) |
| Kaiser Medical Technology Ltd | **Refused** | kaisermedicaltech.com | Site itself gives Brinkworth House Business Centre, Brinkworth, Wiltshire SN15 5DF (read 14/09/2026) | Both KAISER MEDICAL TECHNOLOGY LIMITED (06703471) and KAISER MEDICAL TECHNOLOGY EUROPE LIMITED (12825582) sit at 1 Cricklade Court, Old Town, Swindon SN1 3EY — which does not even match the site's own address | 367 at 1 Cricklade Court, overwhelmingly dissolved — a formation-agent signature |
| Hitachi Medical Systems UK Ltd | **Out of scope** | — | — | — | — |

**Globus and NuVasive share a registered office because they are now the same corporate
group**, not because of a formation agent: Globus Medical completed its acquisition of
NuVasive in 2023, and globusmedical.com's own Contact Us page lists NuVasive Germany
GmbH and Nuvasive Italia srl as its own subsidiaries alongside the same "United Kingdom"
office line. Two companies at one address, both explained by name, is the "handful
sharing a real building" case the guard is written to let through.

**Kaiser fails twice over.** Its registered office is shared with 367 mostly-dissolved
companies — well past the Soluvos/Minitouch bar — and even setting that aside, neither
of the two Companies House candidates is registered at the address the company's own
site prints, so this would have been a near-miss refusal (the Carleton Medical shape)
regardless. Nothing was recorded, and the record's existing companyNumberNote (two
equally plausible companies) still stands unresolved.

**Hitachi Medical Systems UK Ltd has no row this policy can act on.** A Companies House
advanced search for "Hitachi Medical" on 20/09/2026 returns zero results, confirming the
09/09/2026 finding above: the awarded name is the FORMER registered name of company
03218117, now FUJIFILM HEALTHCARE UK LIMITED, and no separate entity survives on the
register to hold a registered office at all. There is nothing for an ADDRESS proof to
match against. The Hub's record for this identity is "Fujifilm Healthcare UK", which
already carries "Hitachi Medical Systems UK Ltd" as an alias; whether that merge is
right is the standing question on `^o376`, not a Policy 2 question, and was not
reopened or touched here.

## A separate finding, not about domains: brand-filed catalogues

Found 09/09/2026 while working Probo Medical, and it will bite again the moment the
ADDRESS route is ruled on, so it is recorded here rather than lost.

`crawl_supplier_site.py`'s WordPress route takes a product's DIVISION from the site's
`product_cat` taxonomy. On a site that files its catalogue by MANUFACTURER rather than
by modality, that division is a brand name, and a brand name can never be mapped to a
Hub category: `data/differentiator-category-map.json` maps "speciality:type", and
"GE HealthCare" is neither.

probomedical.co.uk is the worked example. Its 842 products file under `product_cat`
terms "GE HealthCare" (223), "Philips" (154), "Mindray" (120), "Siemens" (96),
"SonoSite" (50) and so on. But the same site publishes a SECOND product taxonomy,
`prod_type` ("Types"), which is genuinely clinical — Ultrasound Machines (50),
Ultrasound Probes (387), Ultrasound Systems (2), MRI Coils (338), Contrast Injectors
(7), Dental X-ray (7), plus veterinary lines — and nothing reads it.

That matters more than it looks, because the two taxonomies do not agree, so the brand
divisions cannot simply be mapped by hand instead. Crosstabbed from the site's own
WordPress REST API on 09/09/2026, "GE HealthCare" is 120 MRI coils, 89 ultrasound
machines and probes, 7 veterinary ultrasound and 6 veterinary C-arms; "Siemens" is 92
MRI coils and 4 veterinary C-arms with no human ultrasound in it at all; "Mindray"
mixes human ultrasound with veterinary and dental X-ray. Mapping any of those to an
ultrasound category would publish MRI coils and veterinary equipment as ultrasound on
a paid page. Only "Acuson" (36) and "Terason" (10) are single-category on the
company's own filing — both entirely `Ultrasound Probes`, i.e. `ultrasound:trans`.

So for a brand-filing site the honest options are two: read `prod_type` as the
division where a site publishes one, or leave the supplier held. Guessing from the
brand is not a third option. Raised in OUTSTANDING.md on 09/09/2026.

## Refused on applying the policy, 20/09/2026

Both were proposed above as address proofs. Both fail the `domain-proof-tier`
policy's own guard: *"a shared serviced-office address used by many companies …
must be treated as no proof at all."* Companies House advanced search, run on the
registered office string itself on 20/09/2026, is what settles each.

- **Soluvos Medical Ltd** — SOLUVOS MEDICAL LTD (10982713) is registered at
  International House, 36-38 Cornhill, London EC3V 3NG. **998 companies** share
  that registered office. The address therefore says nothing about who owns
  `soluvos.com`. The seed's existing website link for this supplier is unchanged
  and still rests on its weaker 17/09/2026 name self-identification — the address
  route did not strengthen it, and this document no longer claims it does.
- **Minitouch Ltd** — MINITOUCH LTD (07933081) is registered at 1 Hutton Close,
  South Church Enterprise Park, Bishop Auckland DL14 6XG. **~398 companies** share
  that exact address (472 in the postcode), overwhelmingly dissolved, which is the
  signature of a company-formation registered-office service rather than an
  occupied trading address. No domain was recorded for this supplier. The separate
  identity finding on this record — that 07933081 was previously MICROCUBE LTD,
  which settles the ^o463 question — is unaffected and still stands.

**The check is now part of the route, not an afterthought.** Before accepting an
address proof, search Companies House for that registered office. A handful of
companies is a real business park or building; hundreds is a serviced office or a
formation agent, and the proof is refused. The seven accepted proofs were all
re-checked this way on 20/09/2026 and the counts recorded on each seed link:
Brandon 6, Erbe 1 (at unit 1a), Ferno 3, Fulbourn 7, Ryna 10, Sonosite 4.
