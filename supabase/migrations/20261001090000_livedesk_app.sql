-- Live Desk app (01/10/2026). Lou: a separate Live Desk app on the App Store
-- and Google Play, free for Hub members, sold separately to everyone else.
--
-- Accounts are Supabase Auth users (email one-time code). Access is one of:
--   * a Hub member link: the app opened the Hub's "Live Desk app" page, the
--     member was logged in, WordPress snippet 4510 issued a member pass, and
--     the Edge Function livedesk-link verified it. Re-checked every
--     HUB_LINK_DAYS: a lapsed membership stops issuing passes, so access ends.
--   * a store subscription (Apple or Google, through RevenueCat), kept current
--     by the livedesk-revenuecat webhook.
--
-- PRIVACY: livedesk_feed holds the paid Live Desk. RLS on with NO policies and
-- every grant revoked: only the service role (go_live.py in the pipeline repo,
-- and the livedesk-feed Edge Function) can touch it. A signed-in user may READ
-- their own livedesk_access row, nothing else; every write goes through an
-- Edge Function.

create table if not exists public.livedesk_feed (
  id           text primary key,
  payload      jsonb       not null,
  published_at timestamptz not null default now()
);

create table if not exists public.livedesk_access (
  user_id          uuid primary key references auth.users (id) on delete cascade,
  hub_member_id    bigint unique,
  hub_verified_at  timestamptz,
  store_product    text,
  store_expires_at timestamptz,
  store_platform   text,
  updated_at       timestamptz not null default now()
);
comment on column public.livedesk_access.hub_member_id is
  'WordPress user id on the Hub. Unique: one Hub membership opens one app account; a new link moves it.';

create table if not exists public.livedesk_devices (
  token        text primary key,
  user_id      uuid not null references auth.users (id) on delete cascade,
  platform     text not null check (platform in ('ios', 'android')),
  specialities text[] not null default '{}',
  updated_at   timestamptz not null default now()
);
create index if not exists livedesk_devices_user on public.livedesk_devices (user_id);

-- The access rule, in ONE place. Edge Functions and the alert sender both use it.
create or replace function public.livedesk_has_access(a public.livedesk_access)
returns boolean language sql stable as $$
  select coalesce(
    (a.hub_member_id is not null and a.hub_verified_at > now() - interval '35 days')
    or (a.store_expires_at > now()), false)
$$;

create or replace view public.livedesk_push_targets as
  select d.token, d.platform, d.specialities
  from public.livedesk_devices d
  join public.livedesk_access a on a.user_id = d.user_id
  where public.livedesk_has_access(a);

alter table public.livedesk_feed    enable row level security;
alter table public.livedesk_access  enable row level security;
alter table public.livedesk_devices enable row level security;
revoke all on public.livedesk_feed, public.livedesk_access, public.livedesk_devices,
              public.livedesk_push_targets from anon, authenticated;

grant select on public.livedesk_access to authenticated;
drop policy if exists "read own access" on public.livedesk_access;
create policy "read own access" on public.livedesk_access
  for select to authenticated using (user_id = auth.uid());
