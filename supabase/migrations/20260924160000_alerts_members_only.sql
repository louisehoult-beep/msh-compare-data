-- Phone alerts: members only (24/09/2026).
--
-- Lou: only paying members can subscribe. Until now the alerts page inserted
-- into push_subscriptions directly with the public anon key under an
-- "anon may subscribe" policy, so anyone who found the page could sign up.
-- From here the only writer is the Edge Function alerts-subscribe, which
-- checks a member pass from WordPress (service role, bypasses RLS). The anon
-- key can no longer touch this table at all.
--
-- Rows already on file have no member_id. The sender skips them, so those
-- phones get nothing until the member turns alerts on again from the Hub's
-- Phone Alerts page. Nothing is deleted here.

alter table public.push_subscriptions
  add column if not exists member_id   bigint,
  add column if not exists verified_at timestamptz,
  add column if not exists updated_at  timestamptz;

comment on column public.push_subscriptions.member_id is
  'WordPress user id on the Hub whose member pass saved this phone. Null = signed up before the members-only rule; never sent to.';

drop policy if exists "anon may subscribe" on public.push_subscriptions;
revoke all on public.push_subscriptions from anon, authenticated;
