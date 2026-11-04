# Weekly briefing (built 22/10/2026, shadow running since 04/11/2026, not live, not advertised)

Aneeka Hussain's request: one Monday email telling a member what changed in THEIR specialities and companies.

- Rep's Briefing (existing): same email to every member group, Monday 09:00. Unchanged.
- Weekly briefing (this): personal, from My Hub choices. `scripts/weekly_briefing.py`, tested by `test_weekly_briefing.py`.
- Opt-in: My Hub "Weekly briefing" box saves `state.briefing` (user meta `msh_hub_state`). On or off, any time.
- Send rule: needs at least one change item (news, awards, safety, company activity) in the last 7 days; otherwise nothing is built.
- MailerLite: one group per distinct speciality set, `Hub briefing - <slug>+<slug>`, one member in one group.

## Shadow run (04/11/2026)
`scripts/personal_alerts_shadow.py` scores the briefing and the phone triggers every Monday on made-up profiles. It sends nothing, reads no member data, and writes outside this public repo. LaunchAgent: `ops/launchagents/personal-alerts-shadow.sh`.

## Not done, needs Lou's approval first
1. Audience export: a WordPress snippet that lists opted-in members' speciality pins and company ids into the generator's members file (opaque keys, no names or emails in the repo).
2. Group sync and a campaign created as a DRAFT in MailerLite, then a launchd or Code routine for Monday.
3. Members who already pressed "Tell me when it starts" have `briefing: true`; treat them as opted in only if Lou agrees.

Dry run: `python3 scripts/weekly_briefing.py --today 2026-10-26 --members members.json --out out/`
