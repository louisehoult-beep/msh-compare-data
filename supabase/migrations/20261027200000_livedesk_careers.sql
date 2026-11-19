-- Live Desk app: Careers tab and new-role alerts (27/10/2026).
-- Devices choose areas and opt in to role alerts. The careers list itself is the
-- livedesk_feed row id='careers', written by scripts/careers_feed.py and read
-- through the livedesk function's 'careers' action (same access check as the Desk).

alter table public.livedesk_devices
  add column if not exists regions     text[]  not null default '{}',
  add column if not exists role_alerts boolean not null default false;

create or replace view public.livedesk_push_targets as
  select d.token, d.platform, d.specialities, d.regions, d.role_alerts
  from public.livedesk_devices d
  join public.livedesk_access a on a.user_id = d.user_id
  where public.livedesk_has_access(a);

revoke all on public.livedesk_push_targets from anon, authenticated;
