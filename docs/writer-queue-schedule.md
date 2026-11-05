# Writer queue schedule

Every job in the `msh-compare-data-writer` concurrency group commits to `main`, so they run one at a time. GitHub keeps only **one pending run per group**: when a third job arrives while one is running and one is waiting, the waiting one is cancelled and never starts. Space new jobs so that does not happen.

Rules (staggered 05/11/2026):

- Keep daily writers 25 to 35 minutes apart. A job is only dropped if the running one lasts longer than two gaps.
- Put anything that can run over an hour in the evening (18:30 UTC onwards), away from the daily run.
- GitHub starts this repo's crons hours late (about 4 to 8 hours), so spacing matters more than the exact time.
- Keep the order: `differentiator` after the writers that feed it, `speciality-panels` after every feed, `company-press` after the pipeline's 01:20 `priority-handoff`.

| UTC | Job | When |
|---|---|---|
| 00:40 | atamis-opportunities | daily |
| 01:10 | acquirer-press | daily |
| 01:40 | company-press | daily |
| 02:10 | search-index | daily |
| 02:35 | supplier-capture | daily |
| 03:00 | private-provider-moves | daily |
| 03:25 | mhra-dsu | daily |
| 03:55 | refresh | daily |
| 04:25 | icb-watch | daily |
| 05:00 | differentiator | daily |
| 05:20 | speciality-news | daily |
| 06:00 | framework-awards | daily |
| 06:25 | open-tenders | daily |
| 06:50 | digital-lane | daily |
| 07:15 | drug-tariff | daily |
| 07:45 | speciality-panels | daily |
| 08:20 | gp-prescribing | 15th to 28th |
| 09:30 | icb-pack | 15th to 28th |
| 08:00, 09:00, 11:00, 12:00, 15:00, 16:00 | push-alerts (backup cron) | daily |
| 10:30, 17:00 | differentiator | daily |
| 17:40 | hospital-prescribing | 14th to 28th |
| 18:30 | supplier-product-detail-capture | Saturday |
| 20:45 | weekly-refresh | Saturday |
| 19:00 | company-intelligence | Sunday |
| 19:00 | supplier-careers | Monday |
| 19:00 | nhssc-launch-briefs | Tuesday |
| 19:00 | icc-and-ccf | 3rd of the month |

`mhra-alerts` (02:50) has its own group, `msh-writer-mhra-alerts`, so it is not in this queue.
