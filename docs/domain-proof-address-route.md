# A second domain proof: registered office address

Written 08/09/2026 by the `differentiator-framework-coverage` run, working the
Operating Theatres Equipment and Related Accessories and Services framework, and
added to 09/09/2026 by the same routine working Ultrasound Scanners and
Associated Options and Related Services.
**Nothing here has been written to `data/supplier-seed.json`.** It is a proposal
for `scripts/seed_supplier_domains.py`, and it needs Lou's ruling first
(OUTSTANDING ^o363). The 09/09 run wrote two of these proofs into the seed before
reading this file, and reverted both the moment it found them: the route is not
ruled on, and a run quietly crossing a bar Lou has been asked to set would settle
the question by fait accompli. That revert is the reason the Ultrasound Scanners
framework did not move that day.

## The problem it answers

`seed_supplier_domains.py` records a domain on one strong proof: the site prints
a company registration number, next to registration wording, matching the number
already held in `company-financials.json`. That bar exists for a good reason —
the name tier was measured on 14/08/2026 and 124 of 128 domains it had "proved"
were refused on re-examination.

But most UK supplier sites never print their registration number anywhere the
script looks. On this framework, 15 of 43 awarded suppliers have no website
recorded at all, and that — not the crawler — is what caps coverage at 14.0%.

## The proposed route

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
| Ferno (UK) Limited | ferno.com/uk | Ferno (UK) Limited, Ferno House, Stubs Beck Ln, West 26 Industrial Estate, Cleckheaton BD19 4TZ | FERNO (01007475) — Ferno House, Stubs Beck Lane, Cleckheaton, West Yorkshire, BD19 4TZ |
| Fulbourn Medical | fulbournmedical.com | Fulbourn Medical, Unit 1 Falcon Court, Hinchingbrooke Business Park, Huntingdon, Cambridgeshire PE29 6AH | FULBOURN MEDICAL LIMITED (02764966) — Unit 1 Falcon Court Falcon Road, Hinchingbrooke Business Park, Huntingdon, Cambridgeshire, PE29 6AH |
| Ryna Medical Uk Limited | rynamedical.co.uk | RYNA MEDICAL UK LIMITED, Backfield Farm Business Park, Wotton Road, Iron Acton, Bristol BS37 9XD | RYNA MEDICAL UK LIMITED (06800377) — Unit A12 Backfield Farm Business Park Wotton Road, Iron Acton, Bristol, BS37 9XD |
| Soluvos Medical Ltd | soluvos.com | SOLUVOS MEDICAL Ltd., International House, 36-38 Cornhill, City of London EC3V 3NG | SOLUVOS MEDICAL LTD (10982713) — International House, 36-38 Cornhill, London, EC3V 3NG |

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
cosmetic: even if the route is accepted, this domain cannot be crawled. Read
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
