# My Hub: members choose what's on their page

Added 23/09/2026. Replaces the three-question shortlist on
`/medical-sales-hub/my-hub/` (page 4404, published 21/09/2026).

## What the member gets

Redesigned 24/09/2026 as the page reps work from (Lou: "this will be the
page reps work from"). Full width with side margins, top to bottom:

1. **Key news.** The newest stories across all 31 speciality news feeds. The
   lead story is open on a navy card; the next five are one click from their
   summary; "Show all" drops the rest down. At most two per speciality above
   "Show all", so one busy trade feed can't fill the top. Duplicate headlines
   under two links count once.
2. **The top items from each section**, four each, "Show all" for the rest,
   every panel linking to its full Hub page:
   * Coming up: events and awareness days, next 90 days (`data/hub-calendar.json`, The Calendar).
   * Safety alerts: MHRA device and patient safety alerts (`data/mhra-alerts.json`, MHRA Regulatory Desk).
   * Procurement deadlines: framework and contract dates, next 180 days (`data/hub-calendar.json`, Frameworks and tenders).
   Every row expands in place to show its detail, the rep angle and source links.
3. **Your pages.** The member's chosen tiles, in their order.

A "Your specialities / Whole Hub" switch narrows news, events and procurement
to the specialities the member pinned (remembered per browser). MHRA alerts
are never narrowed: gov.uk's specialism tags do not map to Hub pages, and a
guessed filter could hide a recall. With no speciality pinned the switch is
off and the page says how to turn it on. A feed that fails shows an honest
empty panel.

### Choosing pages (unchanged from 23/09/2026)

* Ticks any of 109 Hub pages, in eight groups: specialities, live desks and
  news, procurement and frameworks, tools and intelligence, NHS know-how,
  career and development, Clinical Hub, help and settings.
* Search box, and an optional starter set per role.
* Reorders their choices, then saves.
* First visit: pre-filled from the role, speciality and setting they gave the
  old My Hub, labelled as a starting point until they save.

## The parts

| Part | Where | Job |
|---|---|---|
| `app/my-hub.js` | This repo | Renders the page and the picker. |
| `hub/my-hub-catalogue.json` | This repo | What can be picked. Published pages only. |
| `hub/wpcode/my-hub-pins.php` | Paste into WPCode on the Hub | `GET/POST /wp-json/msh/v1/my-hub`, user meta `msh_hub_pins`, prints the REST nonce. |
| `hub/pages/my-hub.html` | Paste into page 4404 | Navy masthead, full-width wrap, mount and loader. |
| `test_my_hub_catalogue.py` | Runs in `scripts/run_unit_tests.py` | Catalogue ids, groups, role starters, news flags. |

## Saving

1. Hub account (`msh_hub_pins`). Follows the member across devices.
2. If the account can't be reached: this browser only, and the page says so.

The existing `/wp-json/msh/v1/prefs` endpoint is only read, never written, and
is left as it is.

## Adding a page to the picker

Add an item to `hub/my-hub-catalogue.json` (`id`, `label`, `group`, `url`).
Never rename or reuse an `id`: members' saved pages hold them. A page that is
retired comes out of the catalogue; saved choices for it are hidden, not
deleted, so they come back if the page does.
