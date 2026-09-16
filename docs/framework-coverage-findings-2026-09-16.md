# Framework coverage findings — 16/09/2026

Framework worked this run: **Electrodes, Ultrasound Gels, Defibrillation and Related
Consumables** (cardiology speciality, catsInScope: cardiology:ecg, cardiology:ctg,
cardiology:defib, cardiology:equip, cardiology:capital, cardiology:gel). Picked as the
lowest-coverage STARTED framework with non-zero Left (18.9%, 11 left) after the two
frameworks ranked lower (Insulin Pumps/CGM 16.7%, Digital Diagnostic Solutions 18.5%)
were checked and found to have zero permitted route left — their entire `Left` count is
`publishedElsewhereNeedingCategory` suppliers whose captured ranges (Abbott's Ensure
nutrition line, Medtronic's Ligasure/Nellcor surgical/monitoring lines, Urathon's mobility
and moving-and-handling range) are genuinely unrelated products, not miscategorised ones,
and every crawlable route for those three is already in `refusedSuppliers`. Nothing
actionable there; not re-raised.

## Salter Labs UK Ltd — domain found and crawled

`data/supplier-seed.json` carried no domain for this supplier (framework's `notCrawled`
list, `needDomain`). Their own letterhead (a Carbon Reduction Plan statement published at
`https://www.myairlife.com/wp-content/uploads/2024/04/AirLife-Carbon-Plan-Statment-Dec-2023.pdf`)
states directly: "AirLife is a trading name of Salter Labs UK Limited. Registered in
England and Wales No. 08927162" — matching the `companyNumberCandidate` already on file.
Website confirmed as `myairlife.com` from this primary source and added to the seed
record's `links`.

Crawled: 409 products across 11 divisions (Emergency, AirLife Secure™ Products, Airway
Management, Home Care, Patient Monitoring, Respiratory, Resuscitation, Anesthesia +
3 small residual buckets). Most of the range is respiratory/anaesthesia equipment — out
of this framework's scope, and presumably relevant to Salter Labs' other award
("Respiratory Solutions", already on their seed record).

**One division is genuinely cardiology-relevant: "Patient Monitoring" (53 products).**
It contains clear ECG/CTG items (ECG Leadwires, Multi-Link X2™ Universal ECG System ×3
variants, ECG Monitoring Accessories, Maternal ECG Cables and Leadwires, Fetal Spiral
Electrode System, Diagnostic Cardiology Paper) mixed with clearly non-cardiology items in
the same division (EtCO2/capnography nasal cannulas, temperature probes and cables,
stethoscopes, a peak flow meter, a muscle stimulator). Mapping the whole division to a
cardiology category (even as Lou's multi-category list) would misfile the capnography and
temperature-monitoring products as cardiology. This needs a **product-level** decision
(the `product-override` mapping tier already exists in `build_differentiator.py` for
exactly this shape of problem — see `data/differentiator-map-parts/README.md`), not a
division-level one, and per this run's brief ("note it rather than inventing a category")
that product-level split is left for a ruling rather than made here.

Left held, unmapped, via `union_differentiator_pairs.py --apply` (which only registers the
new (supplier, division) pairs with `hub: null` — it does not decide anything). Ledger
effect: Salter Labs moves from `needDomain` to `heldOnly` — real progress (a genuine
crawl now exists) without a forced or guessed categorisation.

## Electro Spyres Healthcare Limited — re-examined, same class of gap

Already `heldOnly` from an earlier run. Re-checked rather than re-crawled (its refusal/held
state is current, verified 11/09/2026). Its single "Uncategorised" division (46 products)
has the identical shape of problem as Salter Labs' Patient Monitoring division: genuine
ECG/ultrasound-gel items (vitatrode ECG electrodes, ultragel/electrogel ultrasound and
conductive gels) sit alongside unrelated wound-care dressings (skinresq/dynaderm range)
and electrosurgery accessories (thermoblue patient plates, electrosurgical pencil). Same
fix needed: product-level mapping, not a division-level one. Not re-mapped this run for
the same reason as above.

## Recommendation

Both suppliers are ready for a **product-level category-mapping pass** once someone
reviews the product-override precedent and confirms it's the right route for these two.
That pass would plausibly move: Salter Labs' ECG/CTG items → cardiology:ecg / cardiology:ctg
/ cardiology:equip, and Electro Spyres' vitatrode/ultragel/electrogel items → cardiology:ecg
/ cardiology:gel. Left as a queued decision rather than made here.
