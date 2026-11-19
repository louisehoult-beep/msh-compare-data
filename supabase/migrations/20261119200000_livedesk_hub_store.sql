-- Hub membership bought in the Live Desk app (plan step D2, 19/11/2026).
-- One row per app account whose RevenueCat "hub" entitlement has been seen.
-- Written only by the livedesk-revenuecat webhook (service role); read by the
-- livedesk function's "hub-login" action. The WordPress Paid Member
-- Subscriptions record is the membership itself; this is the app's copy of
-- which WordPress user it belongs to and until when.
create table if not exists public.livedesk_hub_store (
  user_id          uuid primary key references auth.users (id) on delete cascade,
  wp_user_id       bigint,
  email            text,
  store_product    text,
  store_expires_at timestamptz,
  store_platform   text,
  updated_at       timestamptz not null default now()
);

alter table public.livedesk_hub_store enable row level security;
-- No policies: only the service role reads or writes it.
