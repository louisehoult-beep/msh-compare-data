-- Ask the Hub (24/09/2026). Private passage store, per-member daily cap, and
-- the log of questions the Hub could not answer.
--
-- PRIVACY: hub_passages holds the Hub's paid text. Row level security is on
-- with NO policies, and every grant to anon/authenticated is revoked, so the
-- publishable key in any page source reads nothing. Only the service role (held
-- by the ask-the-hub Edge Function and the search-index.yml crawl) can reach it.

create table if not exists public.hub_passages (
  id         bigint generated always as identity primary key,
  build      text        not null,
  page_id    bigint,
  page_title text        not null,
  url        text        not null,
  heading    text        not null,
  body       text        not null,
  kind       text        not null default 'page',
  loaded_at  timestamptz not null default now(),
  fts tsvector generated always as (
    setweight(to_tsvector('english', coalesce(heading, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(page_title, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(body, '')), 'C')
  ) stored
);
create index if not exists hub_passages_fts on public.hub_passages using gin (fts);
create index if not exists hub_passages_build on public.hub_passages (build);

create table if not exists public.ask_usage (
  member text not null,
  day    date not null,
  n      int  not null default 0,
  primary key (member, day)
);

create table if not exists public.ask_gaps (
  id        bigint generated always as identity primary key,
  asked_at  timestamptz not null default now(),
  day       date        not null default (now() at time zone 'Europe/London')::date,
  member    text,
  question  text        not null,
  norm      text        not null,
  emailed   boolean     not null default false,
  unique (day, norm)
);

alter table public.hub_passages enable row level security;
alter table public.ask_usage    enable row level security;
alter table public.ask_gaps     enable row level security;
revoke all on public.hub_passages, public.ask_usage, public.ask_gaps from anon, authenticated;

-- ------------------------------------------------------------------ loading
create or replace function public.ask_stage_passages(p_build text, p_rows jsonb)
returns int language sql as $$
  with ins as (
    insert into public.hub_passages (build, page_id, page_title, url, heading, body, kind)
    select p_build, x.page_id, x.page_title, x.url, x.heading, x.body, coalesce(x.kind, 'page')
    from jsonb_to_recordset(p_rows)
         as x(page_id bigint, page_title text, url text, heading text, body text, kind text)
    returning 1
  )
  select count(*)::int from ins;
$$;

-- Swaps the staged build in, in one transaction. Refuses a build that covers
-- fewer than p_min_pages Hub pages, so a broken crawl cannot empty the store.
create or replace function public.ask_publish_build(p_build text, p_min_pages int)
returns int language plpgsql as $$
declare pages int;
begin
  select count(distinct page_id) into pages
  from public.hub_passages where build = p_build and kind = 'page';
  if pages < p_min_pages then
    delete from public.hub_passages where build = p_build;
    raise exception 'build % covers only % Hub pages (minimum %); kept the previous build',
      p_build, pages, p_min_pages;
  end if;
  delete from public.hub_passages where build <> p_build;
  return (select count(*)::int from public.hub_passages);
end $$;

-- ---------------------------------------------------------------- retrieval
-- OR across the question's own words (after English stemming and stopwords),
-- ranked with headings weighted above body text. Built from the lexemes rather
-- than websearch_to_tsquery because that ANDs every word, and a member's
-- question rarely uses every word the Hub does.
create or replace function public.ask_search(p_q text, p_k int default 12)
returns table (id bigint, page_title text, url text, heading text, body text, kind text, rank real)
language sql stable as $$
  with t as (
    select string_agg(quote_literal(lexeme), ' | ') as terms
    from unnest(to_tsvector('english', p_q))
  ), q as (
    select to_tsquery('simple', terms) as query from t where terms is not null
  )
  select p.id, p.page_title, p.url, p.heading, p.body, p.kind,
         ts_rank(p.fts, q.query) * case when p.kind = 'page' then 1.0 else 0.8 end as rank
  from public.hub_passages p, q
  where p.fts @@ q.query
  order by rank desc
  limit p_k;
$$;

-- ---------------------------------------------------------------------- cap
-- Returns questions left today after this one, -1 when the member's cap is
-- spent, -2 when the whole-Hub daily ceiling is spent. The day is London's.
create or replace function public.ask_take(p_member text, p_cap int, p_global int)
returns int language plpgsql as $$
declare
  today date := (now() at time zone 'Europe/London')::date;
  total int;
  used  int;
begin
  select coalesce(sum(n), 0) into total from public.ask_usage where day = today;
  if total >= p_global then return -2; end if;
  insert into public.ask_usage as u (member, day, n) values (p_member, today, 1)
  on conflict (member, day) do update set n = u.n + 1 where u.n < p_cap
  returning n into used;
  if used is null then return -1; end if;
  return p_cap - used;
end $$;

-- Gives a question back when the answer failed for a reason that was not the
-- member's (the model or the network), so a failure does not cost them a turn.
create or replace function public.ask_refund(p_member text)
returns void language sql as $$
  update public.ask_usage set n = greatest(n - 1, 0)
  where member = p_member and day = (now() at time zone 'Europe/London')::date;
$$;

-- Records a question the Hub could not answer. Returns true only the first
-- time a question is seen today, which is when Lou gets the email.
create or replace function public.ask_log_gap(p_member text, p_question text)
returns boolean language plpgsql as $$
declare
  n text := regexp_replace(lower(p_question), '[^a-z0-9]+', ' ', 'g');
  fresh boolean;
begin
  insert into public.ask_gaps (member, question, norm) values (p_member, p_question, trim(n))
  on conflict (day, norm) do nothing
  returning true into fresh;
  return coalesce(fresh, false);
end $$;

create or replace function public.ask_mark_emailed(p_question text)
returns void language sql as $$
  update public.ask_gaps set emailed = true
  where day = (now() at time zone 'Europe/London')::date
    and norm = trim(regexp_replace(lower(p_question), '[^a-z0-9]+', ' ', 'g'));
$$;

revoke execute on function
  public.ask_stage_passages(text, jsonb), public.ask_publish_build(text, int),
  public.ask_search(text, int), public.ask_take(text, int, int), public.ask_refund(text),
  public.ask_log_gap(text, text), public.ask_mark_emailed(text)
from public, anon, authenticated;
