# My Hub: members choose what's on their page

Added 23/09/2026. Replaces the three-question shortlist on
`/medical-sales-hub/my-hub/` (page 4404, published 21/09/2026).

## What the member gets

* Ticks any of 109 Hub pages, in eight groups: specialities, live desks and
  news, procurement and frameworks, tools and intelligence, NHS know-how,
  career and development, Clinical Hub, help and settings.
* Search box, and an optional starter set per role (the same role links the
  old shortlist used).
* Reorders their choices, then saves. The page shows their tiles in that order.
* Every pinned speciality that has a news file brings its latest items into a
  "Latest from your specialities" block (8 items, newest first, source named).
* First visit: pre-filled from the role, speciality and setting they gave the
  old My Hub, labelled as a starting point until they save.

## The parts

| Part | Where | Job |
|---|---|---|
| `app/my-hub.js` | This repo | Renders the page and the picker. |
| `hub/my-hub-catalogue.json` | This repo | What can be picked. Published pages only. |
| `hub/wpcode/my-hub-pins.php` | Paste into WPCode on the Hub | `GET/POST /wp-json/msh/v1/my-hub`, user meta `msh_hub_pins`, prints the REST nonce. |
| `hub/pages/my-hub.html` | Paste into page 4404 | Header, mount and loader. |
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
