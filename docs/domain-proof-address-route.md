# A second domain proof: registered office address

Written 08/09/2026 by the `differentiator-framework-coverage` run, working the
Operating Theatres Equipment and Related Accessories and Services framework.
**Nothing here has been written to `data/supplier-seed.json`.** It is a proposal
for `scripts/seed_supplier_domains.py`, and it needs Lou's ruling first
(OUTSTANDING ^o363).

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
