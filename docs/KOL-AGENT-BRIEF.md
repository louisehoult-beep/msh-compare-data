# KOL research brief (22/10/2026)

Purpose: fill the Key Opinion Leader (KOL) finder behind Build Your Network on medsalesintelligencehub.co.uk. Aneeka Hussain (Ego Pharmaceuticals, market access) wants high-activity clinical leaders per speciality: people on the board or committee of the speciality's professional bodies and people speaking at their main conference. Dermatology is the finished model: read `scripts/build_kol_finder.py` (docstring and the `add(...)` calls) and `data/kol-finder.json` to see the shape and the standard.

## What to do for each speciality you are given
1. Find the 2 to 4 main UK professional bodies or societies for that speciality (royal colleges and specialist societies, plus the nursing/allied health body where one exists), and the main UK conference of the lead body. Use WebSearch to find them, then WebFetch their own pages.
2. Read their leadership, board, council, committee or trustee page, and the conference's keynote/plenary speakers or organising committee page, in THIS session. Never use memory or a search snippet for who sits where.
3. Record only people the page itself names. Name as shown (keep the title, e.g. "Dr", "Professor"), exact public role, organisation only if the page gives it, term only if the page gives it. Skip paid staff (chief executives, administrators). Skip anyone whose role you cannot read. Fewer correct people beats a long list. Aim for the real board/committee plus conference plenary speakers; stop at about 60 people per speciality.
4. Class each person: `board` (board, council, committee, trustee), `speaker` (conference speaker), `evidence` (named guideline chair or author on the page), `editor` (journal editor named on the page). A person can have several.
5. LinkedIn: for each person run a WebSearch such as `"<name>" <speciality or role> linkedin`. Put the profile in `linkedin_url` ONLY when a result gives a `https://www.linkedin.com/in/...` (or uk.linkedin.com/in/...) URL AND the result text shows the same name plus a matching role, employer, trust or speciality. Otherwise `null`. Never guess a URL, never build one from a pattern, never record a profile for a different person with the same name. In `linkedin_basis` write one short sentence saying what matched (e.g. "Snippet: Consultant Dermatologist, Barts Health"). Budget: one or two searches per person, then move on.
6. Privacy (Medical Sales Register rule, public sources only): name, public role, organisation as the body shows it, the page it came from, and the LinkedIn profile URL. No email, phone, address, date of birth or any private detail anywhere in the file.
7. Facts: do not invent. If a body's page is behind a login, blank or lists no one, say so in `not_found` and move on.

## Output: one file per speciality, `data/kol-sources/<speciality-id>.json`
```json
{
  "speciality": "<id from data/speciality-map.json>",
  "checked": "2026-10-22",
  "bodies": [{"id": "RCN", "label": "Royal College of Nursing (RCN)"}],
  "sources": [{"id": "<speciality-id>-<short>", "short": "...", "body": "full body name", "title": "page title", "url": "https://...", "note": "what the page lists"}],
  "people": [{"name": "Dr Jane Smith", "body": "<bodies.id or null>", "role": "President", "organisation": null, "term": null,
              "source": "<sources.id>", "classes": ["board"], "linkedin_url": null, "linkedin_basis": null}],
  "not_found": ["plain sentences about anything you could not read or find"]
}
```
Rules: `bodies.id` is a short upper-case acronym; use the same id as another speciality for the same body. Every person's `source` must be a source id in the same file and every source url must be one you fetched. Valid JSON only; check with `python3 -c "import json;json.load(open('<file>'))"`. Write only your own files under `data/kol-sources/`; touch nothing else in the repo and do not run git.

## Report back (to Lou) in three short lines at most
Result (counts per speciality: people, with LinkedIn), issues hit and how fixed, anything only Lou can do. No narrative.
